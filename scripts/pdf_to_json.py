#!/usr/bin/env python3
"""
Convert UP Election PoolBoothData PDFs to structured JSON in English.

Each PDF is an electoral roll part (भाग) containing scanned voter cards in Hindi.
Pipeline: PyMuPDF → 3-column image crops → Tesseract OCR → regex parse → JSON

Output: data/PoolBoothData_JSON/<stem>.json
"""

import os
import re
import json
import time
import logging
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

import fitz
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'

BASE_DIR = Path('/Users/aryansingh/Documents/UP-ELection-Ontology-Engine')
INPUT_DIR = BASE_DIR / 'data' / 'PoolBoothData'
OUTPUT_DIR = BASE_DIR / 'data' / 'PoolBoothData_JSON'
LOG_FILE = BASE_DIR / 'scripts' / 'pdf_to_json.log'

DPI_FULL = 200
DPI_PREVIEW = 120  # for quick photo-page detection + part number

# ── logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# ── Translation helpers ──────────────────────────────────────────────────────

GENDER_MAP = {'पुरुष': 'Male', 'महिला': 'Female'}

RESERVATION_MAP = {
    'सामान्य': 'General',
    'अनुसूचित जाति': 'Scheduled Caste',
    'अनुसूचित जनजाति': 'Scheduled Tribe',
    'अन्य पिछड़ा वर्ग': 'Other Backward Class',
}

KNOWN_PLACES = {
    'गोरखपुर': 'Gorakhpur',
    'गोरखपुर शहर': 'Gorakhpur City',
    'उत्तर प्रदेश': 'Uttar Pradesh',
    'गोरखपुर ग्रामीण': 'Gorakhpur Rural',
}


# OCR artifacts that appear at the end of names when card labels bleed in
# (e.g. transliterated "नाम" → "Na", "पिता" → "Pi", etc.)
_NAME_LABEL_ARTIFACT_RE = re.compile(
    r'\s+(?:Na|Naa|Pi|Pii|Rpa|Rp|Ha|Pita|Pati|Neem|Makan)\s*$',
    re.IGNORECASE,
)


def transliterate_name(text: str) -> str:
    """Convert Hindi proper nouns (voter names) to Roman script without API calls."""
    text = text.strip()
    if not text:
        return text
    # If already mostly ASCII, keep as-is
    if sum(1 for c in text if ord(c) < 128) / max(len(text), 1) > 0.75:
        # Still strip label artifacts that are already in ASCII form
        return _NAME_LABEL_ARTIFACT_RE.sub('', text).strip()
    try:
        from indic_transliteration import sanscript
        roman = sanscript.transliterate(text, sanscript.DEVANAGARI, sanscript.OPTITRANS)
        # Normalize doubled vowels created by OPTITRANS long-vowel encoding
        roman = re.sub(r'aa', 'a', roman)
        roman = re.sub(r'ii', 'i', roman)
        roman = re.sub(r'uu', 'u', roman)
        roman = roman.strip()
        roman = _NAME_LABEL_ARTIFACT_RE.sub('', roman).strip()
        return ' '.join(w.capitalize() for w in roman.split()) if roman else text
    except Exception:
        return text


# Persistent translation cache shared across all PDFs
_PLACE_CACHE_FILE = BASE_DIR / 'scripts' / 'translation_cache.json'
_place_cache: dict = {}


def _load_place_cache() -> None:
    global _place_cache
    if _PLACE_CACHE_FILE.exists():
        with open(_PLACE_CACHE_FILE, encoding='utf-8') as f:
            _place_cache = json.load(f)


def _save_place_cache() -> None:
    with open(_PLACE_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(_place_cache, f, ensure_ascii=False, indent=2)


def translate_place(text: str) -> str:
    """Translate a Hindi place / section name to English (Google Translate + persistent cache).
    Falls back to local transliteration if the API call exceeds 5 seconds."""
    text = text.strip()
    if not text:
        return text
    if text in _place_cache:
        return _place_cache[text]
    if sum(1 for c in text if ord(c) < 128) / max(len(text), 1) > 0.75:
        _place_cache[text] = text
        return text
    if text in KNOWN_PLACES:
        _place_cache[text] = KNOWN_PLACES[text]
        return KNOWN_PLACES[text]

    result = transliterate_name(text)  # default: fast local transliteration
    try:
        import concurrent.futures as _cf
        def _call_api():
            from deep_translator import GoogleTranslator
            return GoogleTranslator(source='hi', target='en').translate(text)
        with _cf.ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(_call_api)
            try:
                api_result = future.result(timeout=5)
                if api_result:
                    result = api_result
            except _cf.TimeoutError:
                pass  # keep local transliteration result
    except Exception:
        pass  # keep local transliteration result

    _place_cache[text] = result
    _save_place_cache()
    return result


# ── OCR helpers ──────────────────────────────────────────────────────────────

def render_page_image(page, dpi: int) -> Image.Image:
    pix = page.get_pixmap(dpi=dpi)
    return Image.frombytes('RGB', [pix.width, pix.height], pix.samples)


def ocr_image(img: Image.Image) -> str:
    return pytesseract.image_to_string(img, lang='hin+eng', config='--psm 6')


def ocr_columns(img: Image.Image) -> tuple[str, str, str]:
    """Split image into 3 vertical strips and OCR each separately."""
    w, h = img.width, img.height
    overlap = 20  # pixels of horizontal overlap to avoid cutting words
    texts = []
    for i in range(3):
        left = max(0, i * w // 3 - overlap)
        right = min(w, (i + 1) * w // 3 + overlap)
        strip = img.crop((left, 0, right, h))
        texts.append(ocr_image(strip))
    return texts[0], texts[1], texts[2]


def is_photo_page(text: str) -> bool:
    """Return True if the page is a map/photo page with no voter data."""
    return not (VOTER_ID_RE.search(text) and 'नाम' in text and 'आयु' in text)


# ── Voter record patterns ────────────────────────────────────────────────────

# Voter IDs: 2-4 letters + 6-9 digits (OCR may produce lowercase)
VOTER_ID_RE = re.compile(r'\b([A-Za-z]{2,4}\d{6,9})\b')

NAME_RE = re.compile(r'नाम\s*[:।]\s*(.+?)(?=\n|पिता|पति|मकान|आयु|लिंग|$)')
FATHER_RE = re.compile(r'पिता का नाम\s*[:।]\s*(.+?)(?=\n|मकान|आयु|लिंग|$)')
HUSBAND_RE = re.compile(r'पति का नाम\s*[:।]\s*(.+?)(?=\n|मकान|आयु|लिंग|$)')
HOUSE_RE = re.compile(
    r'मकान संख्या\s*[:।]\s*([^\n]+?)(?:\s*(?:फोटो|उपलब्ध|है|a\b|धर\b|om\b|\[|]|-{2})|\n|$)'
)
AGE_RE = re.compile(r'आयु\s*[:।]?\s*(\d{1,3})')
GENDER_RE = re.compile(r'लिंग\s*[:।]\s*(पुरुष|महिला)')

# Header patterns
PART_RE = re.compile(r'भाग संख्या[\s:]+(\d+)')
SECTION_RE = re.compile(r'अनुभाग संख्या और नाम\s*:\s*(\d+)-(.+?)(?:\n|$)')
ASSEMBLY_RE = re.compile(r'(\d{2,3})\s*-\s*([ऀ-ॿa-zA-Z ]+?)\s*(?:\(|भाग)')
PARLIA_RE = re.compile(
    r'संसदीय.+?:\s*(\d+)\s*-\s*([ऀ-ॿa-zA-Z ]+?)(?:\(|$|\n)'
)
PUB_DATE_RE = re.compile(r'प्रकाशन की तिथि\s*[:।]\s*([\d\-/]+)')
REVISION_RE = re.compile(r'पुनरीक्षण का प्रकार\s*[:।]\s*(.+?)(?:\n|$)')
RESERVATION_RE = re.compile(r'\((सामान्य|अनुसूचित जाति|अनुसूचित जनजाति|अन्य पिछड़ा वर्ग)\)')


def normalize_voter_id(raw: str) -> str:
    """Normalize a voter ID: uppercase and fix common OCR digit/letter swaps."""
    return raw.upper()


OCR_NOISE_RE = re.compile(
    r'\b(a|om|धर|T|M|J|La|PP|है।|हि|हु|फ़|[|]+)\b|\[.*?\]'
)
# Trailing noise in house numbers (+-०, —, धर, etc.)
HOUSE_TRAIL_RE = re.compile(r'[\s\+\-\–\—\|०।]+$')


def clean(s: str) -> str:
    s = OCR_NOISE_RE.sub(' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def clean_house(s: str) -> str:
    s = HOUSE_TRAIL_RE.sub('', s.strip())
    return re.sub(r'\s+', ' ', s).strip()


# ── Parse a single voter column text ─────────────────────────────────────────

def parse_column(col_text: str, part_num: int, section_info: dict) -> list[dict]:
    """Extract voter records from one column's OCR text."""
    records = []
    # Split on voter ID as anchor
    parts = VOTER_ID_RE.split(col_text)
    i = 1  # parts[0] is pre-ID text, then alternates ID / body
    while i < len(parts):
        raw_id = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ''
        i += 2

        voter_id = normalize_voter_id(raw_id)

        name_m = NAME_RE.search(body)
        father_m = FATHER_RE.search(body)
        husband_m = HUSBAND_RE.search(body)
        house_m = HOUSE_RE.search(body)
        age_m = AGE_RE.search(body)
        gender_m = GENDER_RE.search(body)

        voter: dict = {
            'voter_id': voter_id,
            'part_number': part_num,
        }
        voter.update(section_info)

        if name_m:
            voter['name'] = transliterate_name(clean(name_m.group(1)))
        if father_m:
            voter['relation_type'] = 'Father'
            voter['relation_name'] = transliterate_name(clean(father_m.group(1)))
        elif husband_m:
            voter['relation_type'] = 'Husband'
            voter['relation_name'] = transliterate_name(clean(husband_m.group(1)))
        if house_m:
            voter['house_number'] = clean_house(house_m.group(1))
        if age_m:
            voter['age'] = int(age_m.group(1))
        if gender_m:
            voter['gender'] = GENDER_MAP.get(gender_m.group(1), gender_m.group(1))
        voter['photo_available'] = 'फोटो उपलब्ध है' in body

        records.append(voter)

    return records


# ── Parse header (page 0) ─────────────────────────────────────────────────────

def parse_header(text: str) -> dict:
    meta = {'state': 'Uttar Pradesh', 'year': 2026}

    # Part number (from "भाग संख्या : : 7" in the header)
    pm = PART_RE.search(text)
    if pm:
        meta['part_number'] = int(pm.group(1))

    # Assembly constituency
    asm = ASSEMBLY_RE.search(text)
    if asm:
        num = int(asm.group(1))
        name_hi = asm.group(2).strip()
        name_en = KNOWN_PLACES.get(name_hi) or translate_place(name_hi)
        res_m = RESERVATION_RE.search(text[max(0, asm.start()-5):asm.start()+150])
        meta['assembly_constituency'] = {
            'number': num,
            'name': name_en,
            'reservation': RESERVATION_MAP.get(res_m.group(1), 'General') if res_m else 'General',
        }

    # Parliamentary constituency
    par = PARLIA_RE.search(text)
    if par:
        name_hi = par.group(2).strip()
        meta['parliamentary_constituency'] = {
            'number': int(par.group(1)),
            'name': KNOWN_PLACES.get(name_hi) or translate_place(name_hi),
        }

    # Publication date
    pub = PUB_DATE_RE.search(text)
    if pub:
        meta['publication_date'] = pub.group(1).strip()

    # Revision type
    rev = REVISION_RE.search(text)
    if rev:
        meta['revision_type'] = translate_place(rev.group(1).strip())

    return meta


# ── Process one PDF ───────────────────────────────────────────────────────────

def process_pdf(pdf_path: Path) -> dict:
    log.info(f'Processing {pdf_path.name}')
    t_start = time.time()
    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)

    metadata: dict = {
        'source_file': pdf_path.name,
        'total_pages': total_pages,
        'state': 'Uttar Pradesh',
        'year': 2026,
    }
    records: list[dict] = []
    current_part = 0      # will be set from header page
    current_section: dict = {}

    for pnum in range(total_pages):
        try:
            # Quick preview at low DPI to detect photo pages cheaply
            preview = render_page_image(doc[pnum], DPI_PREVIEW)
            preview_text = ocr_image(preview)

            # First page: extract document metadata
            if pnum == 0:
                img_full = render_page_image(doc[pnum], DPI_FULL)
                full_text = ocr_image(img_full)
                meta = parse_header(full_text)
                metadata.update(meta)
                # Use part number from header for all subsequent pages
                current_part = meta.get('part_number', 0)
                continue

            # Skip photo/map pages
            if is_photo_page(preview_text):
                continue

            # Full-resolution OCR in 3 columns
            img_full = render_page_image(doc[pnum], DPI_FULL)
            col1, col2, col3 = ocr_columns(img_full)

            # Update section info from full-res column text
            for col in (col1, col2, col3):
                sm = SECTION_RE.search(col)
                if sm:
                    sec_num = int(sm.group(1))
                    sec_name_hi = sm.group(2).strip()
                    # Section numbers typically 1-20; clamp OCR errors
                    if sec_num > 50:
                        sec_num = 1
                    current_section = {
                        'section_number': sec_num,
                        'section_name': translate_place(sec_name_hi),
                    }
                    break

            # Extract voters from each column
            for col_text in (col1, col2, col3):
                voters = parse_column(col_text, current_part, current_section)
                records.extend(voters)

            if (pnum + 1) % 10 == 0:
                log.info(f'  {pdf_path.name}: page {pnum+1}/{total_pages}, '
                         f'{len(records)} voters so far')

        except Exception as exc:
            log.warning(f'  {pdf_path.name} page {pnum+1} error: {exc}')

    elapsed = time.time() - t_start
    log.info(f'Done {pdf_path.name}: {len(records)} voters in {elapsed:.0f}s')

    return {
        'metadata': metadata,
        'total_voter_records': len(records),
        'voter_records': records,
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def process_and_save(pdf_path: Path) -> str:
    """Worker: process one PDF and save JSON. Safe for multiprocessing."""
    # Each worker re-initialises pytesseract (needed after fork)
    pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'
    out_path = OUTPUT_DIR / (pdf_path.stem + '.json')
    if out_path.exists():
        return f'SKIP {pdf_path.name}'
    try:
        result = process_pdf(pdf_path)
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return f'OK {pdf_path.name} ({result["total_voter_records"]} voters)'
    except Exception as exc:
        return f'FAIL {pdf_path.name}: {exc}'


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _load_place_cache()  # load persisted translations from previous runs
    pdf_files = sorted(INPUT_DIR.glob('*.pdf'))
    pending = [p for p in pdf_files if not (OUTPUT_DIR / (p.stem + '.json')).exists()]
    log.info(f'Found {len(pdf_files)} PDFs, {len(pending)} need processing')

    max_workers = 3  # 3 parallel PDFs; tesseract is already multi-threaded
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(process_and_save, p): p for p in pending}
        for i, fut in enumerate(as_completed(futures), 1):
            msg = fut.result()
            log.info(f'[{i}/{len(pending)}] {msg}')


if __name__ == '__main__':
    main()
