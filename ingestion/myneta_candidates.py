"""
Scraper: MyNeta / ADR — Full candidate affidavit details

Scrapes myneta.info for every candidate in the 9 Gorakhpur ACs:
  - Education qualification
  - Age, profession
  - Total assets & liabilities (net worth)
  - Criminal cases (total and serious)
  - Source PDF URL

Loads into: candidate_master + candidate_affidavits tables

Sources:
  https://myneta.info/upvid2022/?constituency_no={no}   (UP Assembly 2022)
  https://myneta.info/loksabha2024/?constituency_no=64  (Lok Sabha 2024)

Run: python -m ingestion.myneta_candidates
"""
from __future__ import annotations

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

# Gorakhpur ACs with their MyNeta constituency numbers (UP Assembly 2022)
ASSEMBLY_CONSTITUENCIES = {
    320: ("GKP_320", "Caimpiyarganj"),
    321: ("GKP_321", "Pipraich"),
    322: ("GKP_322", "Gorakhpur Urban"),
    323: ("GKP_323", "Gorakhpur Rural"),
    324: ("GKP_324", "Sahajanwa"),
    325: ("GKP_325", "Khajani"),
    326: ("GKP_326", "Chauri-Chaura"),
    327: ("GKP_327", "Bansgaon"),
    328: ("GKP_328", "Chillupar"),
}

LOK_SABHA = {64: ("GKP_LS64", "Gorakhpur")}

EDUCATION_RANK = {
    "10th pass": 1, "12th pass": 2, "graduate": 3,
    "post graduate": 4, "doctorate": 5, "literate": 0,
}


def _parse_amount(text: str) -> int:
    """'Rs 1,23,45,678' → 12345678"""
    digits = re.sub(r"[^\d]", "", text or "")
    return int(digits) if digits else 0


def _slugify(name: str, year: int) -> str:
    slug = re.sub(r"[^A-Z0-9]+", "_", name.strip().upper()).strip("_")
    return f"{slug}_{year}"


def scrape_constituency_list(constituency_no: int, election: str = "upvid2022") -> list[dict]:
    """Scrape candidate list page for one constituency."""
    url = f"https://myneta.info/{election}/?constituency_no={constituency_no}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        logger.error("Failed to fetch %s: %s", url, e)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    candidates: list[dict] = []

    # MyNeta table: columns vary by election, find the results table
    table = soup.find("table", {"class": re.compile(r"table")})
    if not table:
        table = soup.find("table")
    if not table:
        logger.warning("No table found at %s", url)
        return []

    rows = table.find_all("tr")
    header_row = rows[0] if rows else None
    if not header_row:
        return []

    headers = [th.get_text(strip=True).lower() for th in header_row.find_all(["th", "td"])]
    logger.debug("MyNeta headers: %s", headers)

    for row in rows[1:]:
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        row_data = [c.get_text(strip=True) for c in cells]
        detail_link = None
        for c in cells:
            a = c.find("a", href=True)
            if a and "candidate" in a["href"].lower():
                detail_link = "https://myneta.info" + a["href"] if a["href"].startswith("/") else a["href"]
                break

        # Try to extract from table columns
        name        = _safe_get(row_data, headers, "candidate")
        party       = _safe_get(row_data, headers, "party")
        education   = _safe_get(row_data, headers, "education")
        age_str     = _safe_get(row_data, headers, "age")
        criminal    = _safe_get(row_data, headers, "criminal")
        assets_str  = _safe_get(row_data, headers, "total assets")
        liab_str    = _safe_get(row_data, headers, "liabilities")

        if not name:
            continue

        candidates.append({
            "name":             name,
            "party_raw":        party,
            "education":        education,
            "age":              int(re.sub(r"\D", "", age_str or "0") or 0) or None,
            "criminal_cases":   int(re.sub(r"\D", "", criminal or "0") or 0),
            "total_assets":     _parse_amount(assets_str),
            "liabilities":      _parse_amount(liab_str),
            "detail_url":       detail_link,
        })

    logger.info("AC %d: found %d candidates", constituency_no, len(candidates))
    return candidates


def _safe_get(row: list[str], headers: list[str], keyword: str) -> str:
    """Find a cell by matching keyword in header."""
    for i, h in enumerate(headers):
        if keyword in h and i < len(row):
            return row[i].strip()
    return ""


def scrape_candidate_detail(detail_url: str) -> dict:
    """Scrape individual candidate affidavit detail page."""
    if not detail_url:
        return {}
    try:
        time.sleep(0.5)
        resp = requests.get(detail_url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        detail: dict = {}
        # Look for structured affidavit table
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                key   = cells[0].get_text(strip=True).lower()
                value = cells[1].get_text(strip=True)
                if "education" in key:
                    detail["education"] = value
                elif "profession" in key:
                    detail["profession"] = value
                elif "criminal" in key and "total" in key:
                    detail["criminal_cases"] = int(re.sub(r"\D", "", value) or "0")
                elif "serious" in key:
                    detail["serious_cases"] = int(re.sub(r"\D", "", value) or "0")
                elif "total asset" in key:
                    detail["total_assets"] = _parse_amount(value)
                elif "liabilit" in key:
                    detail["liabilities"] = _parse_amount(value)
                elif "age" == key.strip():
                    detail["age"] = int(re.sub(r"\D", "", value) or "0") or None

        # PDF affidavit link
        pdf_link = soup.find("a", href=re.compile(r"\.pdf", re.I))
        if pdf_link:
            detail["pdf_url"] = pdf_link["href"]

        return detail
    except Exception as e:
        logger.debug("Detail scrape failed %s: %s", detail_url, e)
        return {}


def _normalise_party(raw: str) -> str:
    raw = raw.strip().upper()
    for abbrev in ["BJP", "SP", "BSP", "INC", "AAP", "AIMIM", "RLD", "SBSP"]:
        if abbrev in raw:
            return abbrev
    m = re.search(r"\(([A-Z]{2,8})\)", raw)
    if m:
        return m.group(1)
    return raw[:20]


def load_to_postgres(
    cands: list[dict],
    ac_id: str,
    election_year: int,
    engine: sa.Engine,
) -> int:
    with engine.connect() as conn:
        for c in cands:
            cid = _slugify(c["name"], election_year)
            party = _normalise_party(c.get("party_raw", ""))

            # Upsert candidate_master
            conn.execute(text("""
                INSERT INTO candidate_master
                    (candidate_id, name, party, ac_id, election_year)
                VALUES (:cid, :name, :party, :ac_id, :year)
                ON CONFLICT (candidate_id) DO UPDATE
                  SET party = EXCLUDED.party
            """), {"cid": cid, "name": c["name"], "party": party,
                   "ac_id": ac_id, "year": election_year})

            # Insert candidate_affidavits
            conn.execute(text("""
                INSERT INTO candidate_affidavits
                    (candidate_id, election_year, criminal_cases, serious_cases,
                     total_assets, total_liabilities, education, profession, age, pdf_url)
                VALUES (:cid, :year, :criminal, :serious,
                        :assets, :liab, :edu, :prof, :age, :pdf)
                ON CONFLICT DO NOTHING
            """), {
                "cid":      cid,
                "year":     election_year,
                "criminal": c.get("criminal_cases", 0),
                "serious":  c.get("serious_cases", 0),
                "assets":   c.get("total_assets", 0),
                "liab":     c.get("liabilities", 0),
                "edu":      c.get("education", ""),
                "prof":     c.get("profession", ""),
                "age":      c.get("age"),
                "pdf":      c.get("pdf_url", ""),
            })

        conn.commit()
    return len(cands)


def run(ac_filter: int | None = None, scrape_detail: bool = True):
    engine = sa.create_engine(os.environ["POSTGRES_URL"])

    for ac_no, (ac_id, ac_name) in ASSEMBLY_CONSTITUENCIES.items():
        if ac_filter and ac_no != ac_filter:
            continue

        logger.info("Scraping AC %d — %s", ac_no, ac_name)
        cands = scrape_constituency_list(ac_no, "upvid2022")

        if scrape_detail:
            for c in cands:
                if c.get("detail_url"):
                    detail = scrape_candidate_detail(c["detail_url"])
                    c.update(detail)
                time.sleep(0.3)

        n = load_to_postgres(cands, ac_id, 2022, engine)
        logger.info("AC %d: loaded %d candidates", ac_no, n)
        time.sleep(1.0)

    # Lok Sabha 2024
    for ls_no, (ac_id, ac_name) in LOK_SABHA.items():
        if ac_filter:
            continue
        logger.info("Scraping Lok Sabha %d — %s", ls_no, ac_name)
        cands = scrape_constituency_list(ls_no, "loksabha2024")
        n = load_to_postgres(cands, ac_id, 2024, engine)
        logger.info("LS %d: loaded %d candidates", ls_no, n)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--ac", type=int, default=None, help="Single AC number to scrape (e.g. 322)")
    p.add_argument("--no-detail", action="store_true", help="Skip individual affidavit detail pages")
    args = p.parse_args()
    run(ac_filter=args.ac, scrape_detail=not args.no_detail)
