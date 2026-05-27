"""
Ingestion: Candidate Affidavit PDFs → candidate_affidavits (via digital-democracy-pipeline)

Uses the digital-democracy-pipeline (ddp) package to:
  1. Run Sarvam OCR on image-based affidavit PDFs (English + Hindi mix)
  2. Extract: assets, liabilities, criminal cases, education, profession, age
  3. Fuzzy-match the OCR'd name to candidate_master (pg_trgm similarity)
  4. Upsert into candidate_affidavits table

Source PDFs (8 ECI Form-26 affidavits):
  data/data/Affidavit-1778167961.pdf  ...  Affidavit-1778170807.pdf

Requires:
  SARVAM_API_KEY env var  (OCR, ~₹1.50/page, one-time per PDF)
  pip install -e 'digital-democracy-pipeline/[sarvam]'

Run:
  python -m ingestion.ddp_affidavits
  python -m ingestion.ddp_affidavits --pdf data/data/Affidavit-1778167961.pdf
  python -m ingestion.ddp_affidavits --dry-run
"""

from __future__ import annotations

import argparse
import logging
import os
import re
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parents[1] / "data" / "data"

AFFIDAVIT_PDFS = sorted(DATA_DIR.glob("Affidavit-*.pdf"))

_DIGITS_RE = re.compile(r"\d+")
_RS_RE = re.compile(r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d+)?)", re.IGNORECASE)

EDUCATION_KEYWORDS = [
    "doctorate",
    "phd",
    "post graduate",
    "post-graduate",
    "b.tech",
    "m.tech",
    "b.e",
    "m.e",
    "graduate",
    "b.a",
    "b.sc",
    "b.com",
    "m.a",
    "m.sc",
    "m.com",
    "diploma",
    "12th",
    "10th",
    "literate",
    "illiterate",
]


def _parse_amount(raw: str) -> int:
    m = _RS_RE.search(raw or "")
    if m:
        return int(re.sub(r"\D", "", m.group(1)) or 0)
    digits = re.sub(r"[^\d]", "", raw or "")
    return int(digits) if digits else 0


def _parse_education(text: str) -> str:
    lower = text.lower()
    for kw in EDUCATION_KEYWORDS:
        if kw in lower:
            return kw
    return ""


def ocr_pdf(pdf_path: Path) -> str:
    """Run Sarvam OCR; return full concatenated text from all pages."""
    from digital_democracy_pipeline.sarvam import SarvamDocumentIntelligenceExtractor

    api_key = os.environ.get("SARVAM_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "SARVAM_API_KEY not set.\n" "Get a key at https://dashboard.sarvam.ai"
        )

    extractor = SarvamDocumentIntelligenceExtractor(
        api_key=api_key,
        language="en-IN",  # affidavits are mostly English
        output_format="md",
    )
    pages = extractor.extract_pages(pdf_path)
    pages.sort(key=lambda p: p.get("page_number", 0))
    full_text = "\n\n".join(
        str(p.get("text") or p.get("markdown") or p.get("content") or "") for p in pages
    )
    logger.info("OCR'd %s: %d pages, %d chars", pdf_path.name, len(pages), len(full_text))
    return full_text


def extract_fields(full_text: str) -> dict:
    """
    Extract key fields from OCR'd ECI Form-26 affidavit text.
    Returns dict: name, criminal_cases, serious_cases, total_assets,
                  total_liabilities, education, profession, age.
    """
    lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]
    result: dict = {
        "name": "",
        "criminal_cases": 0,
        "serious_cases": 0,
        "total_assets": 0,
        "total_liabilities": 0,
        "education": "",
        "profession": "",
        "age": None,
    }

    for i, ln in enumerate(lines):
        ll = ln.lower()

        # Criminal / pending cases
        if ("criminal case" in ll or "pending case" in ll or "fir" in ll) and "no" not in ll[:15]:
            nums = _DIGITS_RE.findall(ln)
            if nums:
                result["criminal_cases"] = max(result["criminal_cases"], int(nums[0]))
        if "ipc" in ll or "heinous" in ll or "serious" in ll:
            nums = _DIGITS_RE.findall(ln)
            if nums:
                result["serious_cases"] = max(result["serious_cases"], int(nums[0]))

        # Assets
        if "total asset" in ll or "net worth" in ll:
            amt = _parse_amount(ln)
            if amt == 0 and i + 1 < len(lines):
                amt = _parse_amount(lines[i + 1])
            if amt:
                result["total_assets"] = amt

        # Liabilities
        if "total liabilit" in ll:
            amt = _parse_amount(ln)
            if amt == 0 and i + 1 < len(lines):
                amt = _parse_amount(lines[i + 1])
            if amt:
                result["total_liabilities"] = amt

        # Education (first match wins — keywords sorted most→least qualified)
        if not result["education"]:
            edu = _parse_education(ln)
            if edu:
                result["education"] = edu

        # Profession / occupation
        if not result["profession"] and ("occupation" in ll or "profession" in ll):
            parts = re.split(r"[:—–]", ln, maxsplit=1)
            if len(parts) >= 2 and parts[-1].strip():
                result["profession"] = parts[-1].strip()[:100]

        # Age (look for a 2–3 digit number on a line that mentions "age" or "dob")
        if result["age"] is None and ("age" in ll or "date of birth" in ll or "dob" in ll):
            for n in _DIGITS_RE.findall(ln):
                age = int(n)
                if 20 <= age <= 95:
                    result["age"] = age
                    break

    # Candidate name — first "Name:" occurrence or first non-trivial line
    for ln in lines[:25]:
        if re.match(r"(?i)name\s*[:—–]", ln):
            name_part = re.split(r"[:—–]", ln, maxsplit=1)[-1].strip()
            if len(name_part) > 2:
                result["name"] = name_part[:200]
                break
    if not result["name"] and lines:
        result["name"] = lines[0][:200]

    return result


def match_candidate(name: str, engine: sa.Engine) -> str | None:
    """Fuzzy-match extracted name to candidate_master using pg_trgm similarity."""
    if not name:
        return None
    with engine.connect() as conn:
        row = (
            conn.execute(
                text("""
            SELECT candidate_id, name,
                   similarity(LOWER(name), LOWER(:name)) AS sim
            FROM candidate_master
            WHERE similarity(LOWER(name), LOWER(:name)) > 0.3
            ORDER BY sim DESC
            LIMIT 1
        """),
                {"name": name[:200]},
            )
            .mappings()
            .fetchone()
        )
    if row:
        logger.info("Matched '%s' → '%s' (sim=%.2f)", name[:60], row["name"], row["sim"])
        return str(row["candidate_id"])
    logger.warning("No candidate match for '%s'", name[:60])
    return None


def upsert_affidavit(
    candidate_id: str, fields: dict, pdf_path: Path, engine: sa.Engine, year: int = 2022
) -> None:
    with engine.connect() as conn:
        conn.execute(
            text("""
            INSERT INTO candidate_affidavits
                (candidate_id, election_year, criminal_cases, serious_cases,
                 total_assets, total_liabilities, education, profession, age, pdf_url)
            VALUES
                (:cid, :year, :criminal, :serious,
                 :assets, :liab, :edu, :prof, :age, :pdf)
            ON CONFLICT DO NOTHING
        """),
            {
                "cid": candidate_id,
                "year": year,
                "criminal": fields.get("criminal_cases", 0),
                "serious": fields.get("serious_cases", 0),
                "assets": fields.get("total_assets", 0),
                "liab": fields.get("total_liabilities", 0),
                "edu": fields.get("education", ""),
                "prof": fields.get("profession", ""),
                "age": fields.get("age"),
                "pdf": str(pdf_path),
            },
        )
        conn.commit()


def process_pdf(pdf_path: Path, engine: sa.Engine | None, dry_run: bool = False) -> dict:
    full_text = ocr_pdf(pdf_path)
    fields = extract_fields(full_text)
    logger.info(
        "Extracted fields from %s: assets=₹%d criminal=%d edu='%s'",
        pdf_path.name,
        fields.get("total_assets", 0),
        fields.get("criminal_cases", 0),
        fields.get("education", ""),
    )

    if dry_run:
        logger.info("[DRY RUN] Detected name: '%s'", fields.get("name"))
        return fields

    if not engine:
        return fields

    cid = match_candidate(fields.get("name", ""), engine)
    if cid:
        upsert_affidavit(cid, fields, pdf_path, engine)
        logger.info("Loaded affidavit → candidate_id=%s", cid)
    else:
        logger.warning("Skipped %s — no candidate_master match", pdf_path.name)

    return fields


def run(pdf_paths: list[Path] | None = None, dry_run: bool = False) -> None:
    engine = None if dry_run else sa.create_engine(os.environ["POSTGRES_URL"])
    targets = pdf_paths or AFFIDAVIT_PDFS

    if not targets:
        logger.error("No Affidavit-*.pdf files found in %s", DATA_DIR)
        return

    logger.info("Processing %d affidavit PDFs...", len(targets))
    for pdf in targets:
        if not pdf.exists():
            logger.warning("Not found: %s", pdf)
            continue
        try:
            process_pdf(pdf, engine, dry_run=dry_run)
        except Exception as exc:
            logger.error("Failed %s: %s", pdf.name, exc)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="OCR + extract candidate affidavit PDFs")
    p.add_argument("--pdf", default=None, help="Path to single affidavit PDF")
    p.add_argument("--dry-run", action="store_true", help="OCR + extract only, no DB write")
    args = p.parse_args()

    if args.pdf:
        run([Path(args.pdf)], dry_run=args.dry_run)
    else:
        run(dry_run=args.dry_run)
