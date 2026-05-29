"""
Scraper: MyNeta / ADR — Candidate affidavit + expense detail

Three-pass scraper for AC 322 (Gorakhpur Urban) and all Gorakhpur ACs:

  Pass 1 (list):   Constituency list page → seed candidate_master + basic affidavits
  Pass 2 (detail): Individual affidavit page per candidate → enrich candidate_affidavits
                   (profession, voter enrollment, ITR, movable/immovable assets, liabilities)
  Pass 3 (expense): Expense affidavit page per candidate → candidate_expense_detail
                   (optional — pipeline continues if expense page unavailable)

Confirmed URLs (verified 2026-05-21):
  List:    https://www.myneta.info/uttarpradesh2022/index.php?action=show_candidates&constituency_id=186
  Detail:  https://www.myneta.info/uttarpradesh2022/candidate.php?candidate_id=3801
  Expense: https://www.myneta.info/uttarpradesh2022/expense.php?candidate_id=3801

MyNeta constituency_id mapping (NOT the same as AC number):
  AC 322 Gorakhpur Urban → constituency_id = 186

Loads into:
  candidate_master           (name, party, age, education, source_candidate_id, profession)
  candidate_affidavits       (assets, liabilities, criminal cases, detail sections)
  candidate_expense_detail   (campaign expenditure — optional)

Run:
  python -m ingestion.myneta_candidates --ac 322 --pass list
  python -m ingestion.myneta_candidates --ac 322 --pass detail
  python -m ingestion.myneta_candidates --ac 322 --pass expense
  python -m ingestion.myneta_candidates --ac 322   # runs all three passes
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    raise ImportError("Run: pip install requests beautifulsoup4")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

BASE_URL = "https://www.myneta.info"

# MyNeta constituency_id (NOT the AC number — confirmed from live page 2026-05-21)
# Format: (ac_number, election_year) → (canonical_ac_id, ac_name, election_folder, constituency_id | None)
# None = constituency_id not yet verified, skip until confirmed
ASSEMBLY_CONSTITUENCIES: dict[tuple[int, int], tuple[str, str, str, int | None]] = {
    # ── 2022 Vidhan Sabha ──────────────────────────────────────────────────────
    (322, 2022): ("GKP_322", "Gorakhpur Urban", "uttarpradesh2022", 186),
    (320, 2022): ("GKP_320", "Caimpiyarganj", "uttarpradesh2022", 184),
    (321, 2022): ("GKP_321", "Pipraich",       "uttarpradesh2022", 185),
    (323, 2022): ("GKP_323", "Gorakhpur Rural","uttarpradesh2022", 187),
    (324, 2022): ("GKP_324", "Sahajanwa",       "uttarpradesh2022", 188),
    (325, 2022): ("GKP_325", "Khajani",         "uttarpradesh2022", 189),
    (326, 2022): ("GKP_326", "Chauri-Chaura",   "uttarpradesh2022", 190),
    (327, 2022): ("GKP_327", "Bansgaon",        "uttarpradesh2022", 191),
    (328, 2022): ("GKP_328", "Chillupar",       "uttarpradesh2022", 192),
    # ── 2017 Vidhan Sabha — constituency_id confirmed 2026-05-21 ──────────────
    (322, 2017): ("GKP_322", "Gorakhpur Urban", "uttarpradesh2017", 362),
}

LOK_SABHA: dict[int, tuple[str, str, str, int | None]] = {
    520: ("GKP_LS64", "Gorakhpur", "LokSabha2024", 520),
}

# Raw snapshot storage for debugging failed parses
HTML_SNAPSHOT_DIR = Path(__file__).parents[2] / "data" / "raw" / "myneta_html"

EDUCATION_RANK = {
    "10th pass": 1,
    "12th pass": 2,
    "graduate": 3,
    "post graduate": 4,
    "doctorate": 5,
    "literate": 0,
}


# ── Helpers ────────────────────────────────────────────────────────────────────


def _parse_amount(raw: str) -> int:
    """Parse MyNeta amount strings to int.
    Handles: 'Rs 1,23,45,678', '45,000 45 Thou+', '6,88,000 6 Lacs+', 'Nil', 'None'.
    Takes only the FIRST whitespace-separated token to avoid consuming the suffix number.
    """
    text = re.sub(r"Rs\s*", "", (raw or "").replace("\xa0", " "), flags=re.I).strip()
    first = text.split()[0] if text.split() else ""
    digits = re.sub(r"[^\d]", "", first)
    return int(digits) if digits else 0


def _slugify(name: str, year: int) -> str:
    slug = re.sub(r"[^A-Z0-9]+", "_", name.strip().upper()).strip("_")
    return f"{slug}_{year}"


def _safe_get(row: list[str], headers: list[str], keyword: str) -> str:
    for i, h in enumerate(headers):
        if keyword in h and i < len(row):
            return row[i].strip()
    return ""


def _normalise_party(raw: str) -> str:
    raw = (raw or "").strip().upper()
    for abbrev in ["BJP", "SP", "BSP", "INC", "AAP", "AIMIM", "RLD", "SBSP"]:
        if abbrev in raw:
            return abbrev
    m = re.search(r"\(([A-Z]{2,8})\)", raw)
    if m:
        return m.group(1)
    return raw[:20]


def _save_html_snapshot(html: str, folder: str, candidate_id: int, page: str) -> str:
    """Persist raw HTML for debugging. Returns the path string."""
    out_dir = HTML_SNAPSHOT_DIR / folder
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{candidate_id}_{page}.html"
    path.write_text(html, encoding="utf-8")
    return str(path)


def _get(url: str, delay: float = 0.5) -> requests.Response | None:
    time.sleep(delay)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=25)
        resp.raise_for_status()
        return resp
    except Exception as e:
        logger.error("GET failed %s: %s", url, e)
        return None


# ── Pass 1: constituency list ──────────────────────────────────────────────────


def scrape_constituency_list(constituency_id: int, election_folder: str) -> list[dict]:
    """
    Scrape the candidate roster for one constituency.
    Uses the confirmed URL format: index.php?action=show_candidates&constituency_id={id}
    Returns list of basic candidate dicts including the detail page URL.
    """
    url = f"{BASE_URL}/{election_folder}/index.php?action=show_candidates&constituency_id={constituency_id}"
    resp = _get(url)
    if resp is None:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    candidates: list[dict] = []

    table = soup.find("table", {"class": re.compile(r"table")}) or soup.find("table")
    if not table:
        logger.warning("No candidate table found at %s", url)
        return []

    rows = table.find_all("tr")
    if not rows:
        return []

    headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(["th", "td"])]
    logger.debug("List page headers: %s", headers)

    for row in rows[1:]:
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        row_data = [c.get_text(strip=True) for c in cells]

        # Extract detail URL and source_candidate_id from the link
        detail_url = None
        source_cand_id = None
        for c in cells:
            a = c.find("a", href=True)
            if a and "candidate.php" in str(a["href"]):
                href = str(a["href"])
                detail_url = f"{BASE_URL}{href}" if href.startswith("/") else href
                m = re.search(r"candidate_id=(\d+)", href)
                if m:
                    source_cand_id = int(m.group(1))
                break

        # Strip winner/loser annotations MyNeta appends to the name cell.
        # Handles both "(Winner)" with parens and "Winner" concatenated directly.
        raw_name = _safe_get(row_data, headers, "candidate")
        name = re.sub(r"[\s(]*winner[\s)]*$", "", raw_name, flags=re.IGNORECASE).strip()
        party = _safe_get(row_data, headers, "party")
        education = _safe_get(row_data, headers, "education")
        age_str = _safe_get(row_data, headers, "age")
        criminal = _safe_get(row_data, headers, "criminal")
        assets = _safe_get(row_data, headers, "total assets")
        liab = _safe_get(row_data, headers, "liabilities")

        if not name:
            continue

        candidates.append(
            {
                "name": name,
                "party_raw": party,
                "education": education,
                "age": int(re.sub(r"\D", "", age_str or "0") or 0) or None,
                "criminal_cases": int(re.sub(r"\D", "", criminal or "0") or 0),
                "total_assets": _parse_amount(assets),
                "liabilities": _parse_amount(liab),
                "detail_url": detail_url,
                "source_candidate_id": source_cand_id,
            }
        )

    logger.info("constituency_id=%d: found %d candidates", constituency_id, len(candidates))
    return candidates


# ── Pass 2: affidavit detail ───────────────────────────────────────────────────


def _section_table(soup, heading_pattern: str):
    """Return the first <table> following a <h3> that matches heading_pattern."""
    h3 = soup.find("h3", string=re.compile(heading_pattern, re.I))
    return h3.find_next("table") if h3 else None


def _parse_asset_table(section_soup) -> list[dict]:
    """
    Extract [{item, total_rs, self_rs}] from a MyNeta asset/liability section table.

    MyNeta column layout: Sr No | Description | self | spouse | huf | dep1 | dep2 | dep3
    Description is cells[1]; value columns start at cells[2].
    Sums all value columns for total_rs; cells[2] is self_rs.

    Uses separator=" " in get_text() so that "45,000<span>45 Thou+</span>"
    becomes "45,000 45 Thou+" rather than "45,00045 Thou+".
    """
    items = []
    for row in section_soup.find_all("tr"):
        cells = row.find_all("td")
        # Expect: Sr No | Description | self | ... | [row total]
        # Data rows have 9 cells: last cell is the MyNeta-added row total.
        # Header rows have 8 cells — the item check below skips them.
        if len(cells) < 3:
            continue
        item = cells[1].get_text(" ", strip=True)
        label0 = cells[0].get_text(" ", strip=True).lower()
        if not item or item.lower() in ("description", "sr no", "s.no"):
            continue
        # Skip "Gross Total" rows — they use colspan=2 so cells[0]="Gross Total"
        # and cells[1] ends up being the self-amount value, not a description.
        if "total" in label0 or "grand" in label0:
            continue
        # Skip misidentified Gross Total rows where cells[1] is a money value
        # (starts with a digit, "Rs", or ₹ — but NOT a description word like "Residential")
        if re.match(r"^(\d|Rs\.?\s*\d|₹)", item, re.I):
            continue

        # cells[-1] is the row total (present on all 9-cell data rows)
        total_rs = _parse_amount(cells[-1].get_text(" ", strip=True))
        self_rs = _parse_amount(cells[2].get_text(" ", strip=True)) if len(cells) > 2 else 0
        items.append({"item": item, "total_rs": total_rs, "self_rs": self_rs})
    return items


def _parse_liabilities_table(tbl) -> list[dict]:
    """
    Parse MyNeta liabilities section table.
    Layout: Description | Amount  (2 columns — no Sr No column unlike asset tables).
    """
    items = []
    for row in tbl.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        label = cells[0].get_text(" ", strip=True)
        if not label or label.lower() in ("description", "particulars", "sr no", "s.no"):
            continue
        if "total" in label.lower() or "grand" in label.lower():
            continue
        if re.match(r"^(\d|Rs\.?\s*\d|₹)", label, re.I):
            continue
        amount = _parse_amount(cells[-1].get_text(" ", strip=True))
        items.append({"item": label, "total_rs": amount})
    return items


def _parse_itr_table(itr_tbl) -> list[dict]:
    """
    Parse MyNeta ITR table where one row = one person and all years are packed
    into cells[3] as '2019 - 2020 ** Rs 3,75,000 ~ ... 2018 - 2019 ** Rs ...'
    Returns [{relation, year, total_income_rs}, ...].
    """
    rows_out: list[dict] = []
    for row in itr_tbl.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue
        relation = cells[0].get_text(strip=True).lower()
        if relation in ("relation type", ""):
            continue
        packed = cells[3].get_text(" ", strip=True).replace("\xa0", " ")
        for m in re.finditer(r"(20\d{2}\s*[-–]\s*\d{2,4})\s*\*\*\s*Rs\s*([\d,]+)", packed):
            rows_out.append(
                {
                    "relation": relation,
                    "year": re.sub(r"\s+", "", m.group(1)),
                    "total_income_rs": _parse_amount(m.group(2)),
                }
            )
    return rows_out


def scrape_affidavit_detail(candidate_id: int, election_folder: str) -> dict:
    """
    Scrape the full affidavit detail page for one candidate.

    Extracts: voter enrollment, profession, ITR income (5 years),
    movable assets (itemised), immovable assets (itemised), liabilities (itemised),
    criminal case details, and computes movable_assets_rs + immovable_assets_rs totals.

    Returns a dict ready for upsert into candidate_affidavits (007 columns).
    Returns {'parse_status': 'failed'} on network/parse error.
    """
    url = f"{BASE_URL}/{election_folder}/candidate.php?candidate_id={candidate_id}"
    resp = _get(url, delay=0.8)
    if resp is None:
        return {
            "parse_status": "failed",
            "parse_error": "network error",
            "source_affidavit_url": url,
        }

    html = resp.text
    snapshot_path = _save_html_snapshot(html, election_folder, candidate_id, "affidavit")
    soup = BeautifulSoup(html, "html.parser")

    result: dict = {
        "source_affidavit_url": url,
        "html_snapshot_path": snapshot_path,
        "parse_status": "scraped",
        "parse_error": None,
    }

    # Walk all label-value table rows
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        key = cells[0].get_text(" ", strip=True).lower()
        val = cells[1].get_text(" ", strip=True).strip()

        if "profession" in key and "self" in key:
            result["self_profession"] = val
        elif "profession" in key and ("spouse" in key or "wife" in key or "husband" in key):
            result["spouse_profession"] = val
        elif "name of spouse" in key or "spouse name" in key:
            result["spouse_name"] = val
        elif "enrolled as voter" in key or "voter in" in key:
            result["voter_enrolled_ac_name"] = val
        elif "education" in key and "self" in key:
            result["education_detail"] = val

    # ITR — section table found via h3 heading; packed multi-year format per person
    itr_tbl = _section_table(soup, r"pan and status")
    if itr_tbl:
        itr_rows = _parse_itr_table(itr_tbl)
        if itr_rows:
            result["itr_income_json"] = itr_rows

    # Criminal cases
    criminal_section = soup.find(string=re.compile(r"criminal case", re.I))
    if criminal_section:
        parent = criminal_section.find_parent("table") or criminal_section.find_parent("div")
        if parent:
            page_text = parent.get_text(" ", strip=True)
            if "no criminal" in page_text.lower():
                result["criminal_case_details_json"] = []
            else:
                cases: list[dict] = []
                for row in parent.find_all("tr"):
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        label = cells[0].get_text(" ", strip=True).lower()
                        val = cells[1].get_text(" ", strip=True)
                        if label in ("s.no", "serial no", "no.", ""):
                            continue
                        if not cases or any(
                            kw in label
                            for kw in ("what", "section", "ipc", "court", "case no", "offence")
                        ):
                            if not cases or "section" in label or "what" in label:
                                cases.append({})
                            cases[-1][label[:40]] = val[:200]
                if not cases:
                    cases = [{"raw_text": page_text[:2000]}]
                result["criminal_case_details_json"] = cases

    # Asset sections — find tables via h3 headings (h3.find_next("table"))
    movable_tbl = _section_table(soup, r"movable asset")
    immovable_tbl = _section_table(soup, r"immovable asset")
    liab_tbl = _section_table(soup, r"liabilit")

    movable_items = _parse_asset_table(movable_tbl) if movable_tbl else []
    immovable_items = _parse_asset_table(immovable_tbl) if immovable_tbl else []
    liab_items = _parse_liabilities_table(liab_tbl) if liab_tbl else []

    if movable_items:
        result["movable_assets_json"] = movable_items
        result["movable_assets_rs"] = sum(
            i["total_rs"] for i in movable_items if "total" not in i["item"].lower()
        )
    if immovable_items:
        result["immovable_assets_json"] = immovable_items
        result["immovable_assets_rs"] = sum(
            i["total_rs"] for i in immovable_items if "total" not in i["item"].lower()
        )
    if liab_items:
        result["liabilities_json"] = liab_items

    # Recompute total_assets from detail page (overrides buggy list-page total
    # where old _parse_amount appended the suffix digit to the number)
    mov = result.get("movable_assets_rs")
    imm = result.get("immovable_assets_rs")
    if mov is not None or imm is not None:
        result["total_assets_detail"] = (mov or 0) + (imm or 0)

    return result


# ── Pass 3: expense affidavit (optional) ──────────────────────────────────────


def scrape_expense_page(candidate_id: int, election_folder: str) -> dict:
    """
    Scrape campaign expenditure page.
    Returns {'expense_scrape_status': 'not_available'} if page absent or empty.
    """
    url = f"{BASE_URL}/{election_folder}/expense.php?candidate_id={candidate_id}"
    resp = _get(url, delay=0.5)
    if resp is None:
        return {
            "expense_scrape_status": "failed",
            "parse_error": "network error",
            "source_expense_url": url,
        }

    html = resp.text
    soup = BeautifulSoup(html, "html.parser")

    # Detect "no data" pages
    page_text = soup.get_text(" ", strip=True).lower()
    if "no expense" in page_text or "not filed" in page_text or len(page_text) < 200:
        return {"expense_scrape_status": "not_available", "source_expense_url": url}

    result: dict = {
        "source_expense_url": url,
        "expense_scrape_status": "scraped",
        "parse_error": None,
    }

    breakdown: list[dict] = []

    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        key = cells[0].get_text(" ", strip=True).lower()
        val = cells[-1].get_text(strip=True)

        if "total" in key and "expense" in key:
            result["total_election_expense_rs"] = _parse_amount(val)
        elif "own fund" in key or "self fund" in key:
            result["own_funds_rs"] = _parse_amount(val)
        elif "party fund" in key:
            result["party_funds_rs"] = _parse_amount(val)
        elif "donation" in key or "loan" in key or "gift" in key or "contribution" in key:
            result["external_funds_rs"] = _parse_amount(val)
        elif val and _parse_amount(val) > 0:
            breakdown.append(
                {"category": cells[0].get_text(strip=True), "amount_rs": _parse_amount(val)}
            )

    if breakdown:
        result["expense_breakdown_json"] = breakdown

    # Data quality note (sometimes printed at top of page)
    quality_note = soup.find(string=re.compile(r"data quality|affidavit quality", re.I))
    if quality_note:
        result["expense_data_quality"] = quality_note.strip()[:100]

    return result


# ── DB loaders ─────────────────────────────────────────────────────────────────


def load_to_postgres(
    cands: list[dict],
    ac_id: str,
    election_year: int,
    engine: sa.Engine,
) -> int:
    """Upsert list-page candidates into candidate_master + candidate_affidavits."""
    with engine.connect() as conn:
        for c in cands:
            cid = _slugify(c["name"], election_year)
            party = _normalise_party(c.get("party_raw", ""))

            conn.execute(
                text("""
                INSERT INTO candidate_master
                    (candidate_id, name, party, ac_id, election_year,
                     source_candidate_id, source_system, election_slug)
                VALUES (:cid, :name, :party, :ac_id, :year,
                        :src_id, 'myneta', :slug)
                ON CONFLICT (candidate_id) DO UPDATE SET
                    party              = EXCLUDED.party,
                    source_candidate_id = COALESCE(EXCLUDED.source_candidate_id,
                                                   candidate_master.source_candidate_id)
            """),
                {
                    "cid": cid,
                    "name": c["name"],
                    "party": party,
                    "ac_id": ac_id,
                    "year": election_year,
                    "src_id": str(c.get("source_candidate_id") or ""),
                    "slug": (
                        f"UP_LS_{election_year}"
                        if election_year >= 2024 and ac_id.startswith("GKP_LS")
                        else f"UP_VSA_{election_year}"
                    ),
                },
            )

            conn.execute(
                text("""
                INSERT INTO candidate_affidavits
                    (candidate_id, election_year, criminal_cases, serious_cases,
                     total_assets, total_liabilities, education, profession, age, pdf_url,
                     parse_status)
                VALUES (:cid, :year, :criminal, :serious,
                        :assets, :liab, :edu, :prof, :age, :pdf,
                        'list_only')
                ON CONFLICT DO NOTHING
            """),
                {
                    "cid": cid,
                    "year": election_year,
                    "criminal": c.get("criminal_cases", 0),
                    "serious": c.get("serious_cases", 0),
                    "assets": c.get("total_assets", 0),
                    "liab": c.get("liabilities", 0),
                    "edu": c.get("education", ""),
                    "prof": c.get("profession", ""),
                    "age": c.get("age"),
                    "pdf": c.get("pdf_url", ""),
                },
            )
        conn.commit()
    return len(cands)


def load_affidavit_detail(candidate_id: str, detail: dict, engine: sa.Engine) -> None:
    """Upsert enriched affidavit fields (from detail page) into candidate_affidavits."""
    if not detail or detail.get("parse_status") == "failed":
        return

    # Push profession/enrollment back to candidate_master
    master_updates = {
        k: detail.get(k)
        for k in ("self_profession", "spouse_name", "spouse_profession", "voter_enrolled_ac_name")
        if detail.get(k)
    }
    if master_updates:
        sets = ", ".join(f"{k} = :{k}" for k in master_updates)
        master_updates["cid"] = candidate_id
        with engine.connect() as conn:
            conn.execute(
                text(f"UPDATE candidate_master SET {sets} WHERE candidate_id = :cid"),
                master_updates,
            )
            conn.commit()

    # Serialise JSONB fields
    jsonb_fields = (
        "movable_assets_json",
        "immovable_assets_json",
        "liabilities_json",
        "criminal_case_details_json",
        "itr_income_json",
    )
    params: dict = {"cid": candidate_id}
    for f in jsonb_fields:
        v = detail.get(f)
        params[f] = json.dumps(v, ensure_ascii=False) if v is not None else None

    params.update(
        {
            "movable_assets_rs": detail.get("movable_assets_rs"),
            "immovable_assets_rs": detail.get("immovable_assets_rs"),
            "total_assets_detail": detail.get("total_assets_detail"),
            "source_affidavit_url": detail.get("source_affidavit_url"),
            "html_snapshot_path": detail.get("html_snapshot_path"),
            "parse_status": detail.get("parse_status", "scraped"),
            "parse_error": detail.get("parse_error"),
        }
    )

    with engine.connect() as conn:
        conn.execute(
            text("""
            UPDATE candidate_affidavits SET
                movable_assets_rs          = COALESCE(:movable_assets_rs, movable_assets_rs),
                immovable_assets_rs        = COALESCE(:immovable_assets_rs, immovable_assets_rs),
                total_assets               = COALESCE(:total_assets_detail, total_assets),
                movable_assets_json        = COALESCE(CAST(:movable_assets_json   AS jsonb), movable_assets_json),
                immovable_assets_json      = COALESCE(CAST(:immovable_assets_json AS jsonb), immovable_assets_json),
                liabilities_json           = COALESCE(CAST(:liabilities_json      AS jsonb), liabilities_json),
                criminal_case_details_json = COALESCE(CAST(:criminal_case_details_json AS jsonb), criminal_case_details_json),
                itr_income_json            = COALESCE(CAST(:itr_income_json AS jsonb), itr_income_json),
                source_affidavit_url       = COALESCE(:source_affidavit_url, source_affidavit_url),
                html_snapshot_path         = COALESCE(:html_snapshot_path, html_snapshot_path),
                parse_status               = :parse_status,
                parse_error                = :parse_error,
                scraped_at                 = NOW()
            WHERE candidate_id = :cid
        """),
            params,
        )
        conn.commit()


def load_expense_detail(
    candidate_id: str, election_year: int, expense: dict, engine: sa.Engine
) -> None:
    """Upsert expense affidavit data into candidate_expense_detail."""
    if not expense:
        return

    breakdown = expense.get("expense_breakdown_json")
    params = {
        "cid": candidate_id,
        "year": election_year,
        "total": expense.get("total_election_expense_rs"),
        "own": expense.get("own_funds_rs"),
        "party": expense.get("party_funds_rs"),
        "external": expense.get("external_funds_rs"),
        "breakdown": json.dumps(breakdown, ensure_ascii=False) if breakdown else None,
        "quality": expense.get("expense_data_quality"),
        "status": expense.get("expense_scrape_status", "scraped"),
        "url": expense.get("source_expense_url"),
        "error": expense.get("parse_error"),
    }

    with engine.connect() as conn:
        conn.execute(
            text("""
            INSERT INTO candidate_expense_detail
                (candidate_id, election_year,
                 total_election_expense_rs, own_funds_rs, party_funds_rs, external_funds_rs,
                 expense_breakdown_json, expense_data_quality,
                 expense_scrape_status, expense_scraped_at, source_expense_url, parse_error)
            VALUES
                (:cid, :year,
                 :total, :own, :party, :external,
                 CAST(:breakdown AS jsonb), :quality,
                 :status, NOW(), :url, :error)
            ON CONFLICT (candidate_id, election_year) DO UPDATE SET
                total_election_expense_rs = COALESCE(EXCLUDED.total_election_expense_rs,
                                                     candidate_expense_detail.total_election_expense_rs),
                own_funds_rs              = COALESCE(EXCLUDED.own_funds_rs,
                                                     candidate_expense_detail.own_funds_rs),
                party_funds_rs            = COALESCE(EXCLUDED.party_funds_rs,
                                                     candidate_expense_detail.party_funds_rs),
                external_funds_rs         = COALESCE(EXCLUDED.external_funds_rs,
                                                     candidate_expense_detail.external_funds_rs),
                expense_breakdown_json    = COALESCE(EXCLUDED.expense_breakdown_json,
                                                     candidate_expense_detail.expense_breakdown_json),
                expense_data_quality      = COALESCE(EXCLUDED.expense_data_quality,
                                                     candidate_expense_detail.expense_data_quality),
                expense_scrape_status     = EXCLUDED.expense_scrape_status,
                expense_scraped_at        = NOW(),
                parse_error               = EXCLUDED.parse_error
        """),
            params,
        )
        conn.commit()


# ── Generic pass helpers (shared by VS and LS orchestrators) ──────────────────


def _run_list_pass(
    ac_id: str, election_folder: str, constituency_id: int, election_year: int, engine: sa.Engine
) -> int:
    cands = scrape_constituency_list(constituency_id, election_folder)
    return load_to_postgres(cands, ac_id, election_year, engine)


def _run_detail_pass(
    ac_id: str, election_folder: str, engine: sa.Engine, force_rescrape: bool = False
) -> int:
    """Enrich affidavits for all candidates whose parse_status is pending/list_only."""
    status_filter = (
        "TRUE"
        if force_rescrape
        else "(ca.parse_status IS NULL OR ca.parse_status IN ('pending', 'list_only'))"
    )

    with engine.connect() as conn:
        rows = (
            conn.execute(
                text(f"""
            SELECT cm.candidate_id, cm.source_candidate_id
            FROM candidate_master cm
            LEFT JOIN candidate_affidavits ca USING (candidate_id)
            WHERE cm.ac_id = :ac_id
              AND {status_filter}
              AND cm.source_candidate_id IS NOT NULL
              AND cm.source_candidate_id != ''
        """),
                {"ac_id": ac_id},
            )
            .mappings()
            .fetchall()
        )

    logger.info("Detail pass: %d candidates to enrich for %s", len(rows), ac_id)
    count = 0
    for row in rows:
        src_id = row["source_candidate_id"]
        if not src_id:
            continue
        detail = scrape_affidavit_detail(int(src_id), election_folder)
        load_affidavit_detail(row["candidate_id"], detail, engine)
        count += 1
        time.sleep(0.8)
    return count


def _run_expense_pass(
    ac_id: str, election_folder: str, election_year: int, engine: sa.Engine
) -> int:
    with engine.connect() as conn:
        rows = (
            conn.execute(
                text("""
            SELECT cm.candidate_id, cm.source_candidate_id
            FROM candidate_master cm
            LEFT JOIN candidate_expense_detail ced
                ON ced.candidate_id = cm.candidate_id AND ced.election_year = :year
            WHERE cm.ac_id = :ac_id
              AND cm.election_year = :year
              AND cm.source_candidate_id IS NOT NULL
              AND cm.source_candidate_id != ''
              AND (ced.candidate_id IS NULL OR ced.expense_scrape_status = 'pending')
        """),
                {"ac_id": ac_id, "year": election_year},
            )
            .mappings()
            .fetchall()
        )

    logger.info("Expense pass: %d candidates for %s %d", len(rows), ac_id, election_year)
    count = 0
    for row in rows:
        src_id = row["source_candidate_id"]
        if not src_id:
            continue
        try:
            expense = scrape_expense_page(int(src_id), election_folder)
            load_expense_detail(row["candidate_id"], election_year, expense, engine)
            count += 1
        except Exception as e:
            logger.warning("Expense scrape failed for %s: %s", row["candidate_id"], e)
        time.sleep(0.5)
    return count


# ── VS orchestrators ───────────────────────────────────────────────────────────


def run_list_pass(ac_no: int, engine: sa.Engine, year: int = 2022) -> int:
    key = (ac_no, year)
    if key not in ASSEMBLY_CONSTITUENCIES:
        raise ValueError(f"AC ({ac_no}, {year}) not in ASSEMBLY_CONSTITUENCIES")
    ac_id, ac_name, election_folder, constituency_id = ASSEMBLY_CONSTITUENCIES[key]
    if constituency_id is None:
        logger.warning("AC %d/%d (%s): constituency_id not verified — skip", ac_no, year, ac_name)
        return 0
    logger.info(
        "VS list pass: AC %d/%d %s (constituency_id=%d)", ac_no, year, ac_name, constituency_id
    )
    return _run_list_pass(ac_id, election_folder, constituency_id, year, engine)


def run_detail_pass(
    ac_no: int, engine: sa.Engine, year: int = 2022, force_rescrape: bool = False
) -> int:
    key = (ac_no, year)
    if key not in ASSEMBLY_CONSTITUENCIES:
        raise ValueError(f"AC ({ac_no}, {year}) not in ASSEMBLY_CONSTITUENCIES")
    ac_id, _ac_name, election_folder, _cid = ASSEMBLY_CONSTITUENCIES[key]
    return _run_detail_pass(ac_id, election_folder, engine, force_rescrape=force_rescrape)


def run_expense_pass(ac_no: int, engine: sa.Engine, year: int = 2022) -> int:
    key = (ac_no, year)
    if key not in ASSEMBLY_CONSTITUENCIES:
        raise ValueError(f"AC ({ac_no}, {year}) not in ASSEMBLY_CONSTITUENCIES")
    ac_id, _ac_name, election_folder, _cid = ASSEMBLY_CONSTITUENCIES[key]
    return _run_expense_pass(ac_id, election_folder, year, engine)


# ── LS orchestrators ───────────────────────────────────────────────────────────


def _ls_year(election_folder: str) -> int:
    m = re.search(r"20\d{2}", election_folder)
    if not m:
        raise ValueError(f"Cannot extract year from election_folder: {election_folder!r}")
    return int(m.group())


def run_ls_list_pass(ls_no: int, engine: sa.Engine) -> int:
    """Pass 1 for a Lok Sabha constituency (uses LOK_SABHA dict).
    ls_no is the MyNeta constituency_id (e.g. 520 for Gorakhpur LS 2024).
    """
    if ls_no not in LOK_SABHA:
        raise ValueError(f"LS constituency_id {ls_no} not in LOK_SABHA map")
    ac_id, name, election_folder, constituency_id = LOK_SABHA[ls_no]
    if constituency_id is None:
        raise ValueError(f"constituency_id not set for LS entry {ls_no}")
    election_year = _ls_year(election_folder)
    logger.info(
        "LS list pass: %s (constituency_id=%d, year=%d)", name, constituency_id, election_year
    )
    return _run_list_pass(ac_id, election_folder, constituency_id, election_year, engine)


def run_ls_detail_pass(ls_no: int, engine: sa.Engine, force_rescrape: bool = False) -> int:
    """Pass 2 — enrich affidavits for all LS candidates."""
    if ls_no not in LOK_SABHA:
        raise ValueError(f"LS constituency_id {ls_no} not in LOK_SABHA map")
    ac_id, _name, election_folder, _cid = LOK_SABHA[ls_no]
    return _run_detail_pass(ac_id, election_folder, engine, force_rescrape=force_rescrape)


def run_ls_expense_pass(ls_no: int, engine: sa.Engine) -> int:
    """Pass 3 — expense affidavits for LS candidates."""
    if ls_no not in LOK_SABHA:
        raise ValueError(f"LS constituency_id {ls_no} not in LOK_SABHA map")
    ac_id, _name, election_folder, _cid = LOK_SABHA[ls_no]
    return _run_expense_pass(ac_id, election_folder, _ls_year(election_folder), engine)


# ── CLI entry point ────────────────────────────────────────────────────────────


def run(
    ac_no: int = 322,
    passes: list[str] | None = None,
    election_year: int = 2022,
    ls_no: int | None = None,
    force_rescrape: bool = False,
):
    passes = passes or ["list", "detail", "expense"]
    engine = sa.create_engine(os.environ["POSTGRES_URL"])

    if ls_no is not None:
        # Lok Sabha mode
        if "list" in passes:
            n = run_ls_list_pass(ls_no, engine)
            logger.info("LS list pass complete: %d candidates loaded", n)
        if "detail" in passes:
            n = run_ls_detail_pass(ls_no, engine, force_rescrape=force_rescrape)
            logger.info("LS detail pass complete: %d candidates enriched", n)
        if "expense" in passes:
            n = run_ls_expense_pass(ls_no, engine)
            logger.info("LS expense pass complete: %d candidates processed", n)
    else:
        # Vidhan Sabha mode
        if (ac_no, election_year) not in ASSEMBLY_CONSTITUENCIES:
            raise ValueError(f"AC ({ac_no}, {election_year}) not in ASSEMBLY_CONSTITUENCIES")
        if "list" in passes:
            n = run_list_pass(ac_no, engine, year=election_year)
            logger.info("List pass complete: %d candidates loaded", n)
        if "detail" in passes:
            n = run_detail_pass(ac_no, engine, year=election_year, force_rescrape=force_rescrape)
            logger.info("Detail pass complete: %d candidates enriched", n)
        if "expense" in passes:
            n = run_expense_pass(ac_no, engine, year=election_year)
            logger.info("Expense pass complete: %d candidates processed", n)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    import argparse

    p = argparse.ArgumentParser(description="MyNeta scraper — list / detail / expense passes")
    p.add_argument("--ac", type=int, default=322, help="Vidhan Sabha AC number (default: 322)")
    p.add_argument(
        "--ls",
        type=int,
        default=None,
        help="Lok Sabha constituency_id from LOK_SABHA map (e.g. 520 for Gorakhpur 2024)",
    )
    p.add_argument(
        "--pass",
        dest="passes",
        action="append",
        choices=["list", "detail", "expense"],
        help="Which pass(es) to run (default: all three)",
    )
    p.add_argument(
        "--year", type=int, default=2022, help="Election year for expense pass (default: 2022)"
    )
    p.add_argument(
        "--force-rescrape",
        action="store_true",
        help="Re-scrape detail pages even for already-scraped candidates",
    )
    args = p.parse_args()
    run(
        ac_no=args.ac,
        passes=args.passes,
        election_year=args.year,
        ls_no=args.ls,
        force_rescrape=args.force_rescrape,
    )
