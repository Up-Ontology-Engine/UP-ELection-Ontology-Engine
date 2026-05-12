"""
Scraper: UP Jansunwai (CM Helpline 1076) public grievance data

Portal: jansunwai.up.nic.in
- Public search: constituency-wise grievance status (no login required)
- Data: complaint category, date, status (pending/disposed), district/tehsil

Strategy:
  1. POST to the public grievance search API with district=Gorakhpur
  2. Parse response (HTML table or JSON)
  3. Insert into pulse_events_raw as source_type='grievance'
     so the NLP pipeline can extract issue + polarity from complaint text

Alternative if API blocks: download CSV exports from the portal's
"Report" section → drop at data/raw/grievances/ → run with --csv FILE

Run:
    python -m ingestion.grievance_scraper              # live scrape
    python -m ingestion.grievance_scraper --csv FILE   # parse downloaded CSV
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import logging
import os
import time
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)

DISTRICT = "Gorakhpur"
AC_NAME  = "Gorakhpur Urban"

# Known grievance categories → issue tags matching our IssueType enum
CATEGORY_TO_ISSUE: dict[str, str] = {
    "पेयजल":          "water",
    "पानी":            "water",
    "water":           "water",
    "सड़क":            "roads",
    "road":            "roads",
    "बिजली":           "electricity",
    "electricity":     "electricity",
    "रोजगार":          "jobs",
    "employment":      "jobs",
    "कानून व्यवस्था":  "law_order",
    "crime":           "law_order",
    "महिला सुरक्षा":   "women_safety",
    "women":           "women_safety",
    "स्वास्थ्य":       "health",
    "hospital":        "health",
    "शिक्षा":          "education",
    "school":          "education",
    "भ्रष्टाचार":      "corruption",
    "corruption":      "corruption",
    "किसान":           "farmer",
    "farmer":          "farmer",
    "महंगाई":          "price_rise",
    "inflation":       "price_rise",
    "आवास":            "housing",
    "housing":         "housing",
    "pmay":            "housing",
}


def _issue_from_category(category: str) -> str:
    cat_lower = category.lower().strip()
    for kw, issue in CATEGORY_TO_ISSUE.items():
        if kw.lower() in cat_lower:
            return issue
    return "other"


def _content_hash(text_raw: str) -> str:
    return hashlib.sha256(text_raw.encode()).hexdigest()[:64]


# ── Live scraper (portal may change — verify URL before running) ───────────────

def scrape_live(engine: sa.Engine, max_pages: int = 20) -> int:
    """
    Attempt to fetch grievances from Jansunwai public search.
    The portal is rate-limited; use politely with delays.
    Returns number of rows inserted.
    """
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        raise ImportError("pip install requests beautifulsoup4")

    BASE_URL = "https://jansunwai.up.nic.in/CMHELPLINE/GrievanceSearch"
    headers  = {
        "User-Agent": "Mozilla/5.0 (research bot — public data only)",
        "Referer": BASE_URL,
    }
    session = requests.Session()

    inserted = 0
    for page in range(1, max_pages + 1):
        try:
            resp = session.post(BASE_URL, data={
                "district":    DISTRICT,
                "ac_name":     AC_NAME,
                "page":        page,
                "status":      "all",
            }, headers=headers, timeout=20)
            resp.raise_for_status()
        except Exception as e:
            logger.warning("Page %d fetch failed: %s", page, e)
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.select("table.grievance-table tr")
        if not rows or len(rows) <= 1:
            logger.info("No more rows at page %d", page)
            break

        for tr in rows[1:]:
            cells = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(cells) < 4:
                continue

            complaint_no = cells[0]
            category     = cells[1] if len(cells) > 1 else ""
            status       = cells[2] if len(cells) > 2 else ""
            date_str     = cells[3] if len(cells) > 3 else ""
            detail       = cells[4] if len(cells) > 4 else category

            issue    = _issue_from_category(category)
            text_raw = f"[{category}] {detail} (Status: {status}, Date: {date_str})"

            n = _insert_grievance(engine, complaint_no, text_raw, issue, date_str)
            inserted += n

        time.sleep(2)

    logger.info("Scraped %d grievance events", inserted)
    return inserted


# ── CSV fallback ──────────────────────────────────────────────────────────────

def load_from_csv(csv_path: Path, engine: sa.Engine) -> int:
    """
    Parse a manually downloaded Jansunwai CSV export.

    Expected columns (any order):
      Complaint No, Category / Grievance Type, Status, Date, Description / Detail
    """
    inserted = 0
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            complaint_no = (
                row.get("Complaint No") or row.get("Registration No") or ""
            ).strip()
            category = (
                row.get("Category") or row.get("Grievance Type") or
                row.get("श्रेणी") or ""
            ).strip()
            status   = (row.get("Status") or row.get("स्थिति") or "").strip()
            date_str = (row.get("Date") or row.get("दिनांक") or "").strip()
            detail   = (
                row.get("Description") or row.get("Detail") or
                row.get("विवरण") or category
            ).strip()

            issue    = _issue_from_category(category)
            text_raw = f"[{category}] {detail} (Status: {status}, Date: {date_str})"

            inserted += _insert_grievance(engine, complaint_no, text_raw, issue, date_str)

    logger.info("Loaded %d grievance events from %s", inserted, csv_path.name)
    return inserted


# ── Shared DB insert ──────────────────────────────────────────────────────────

def _insert_grievance(
    engine: sa.Engine,
    source_id: str,
    text_raw: str,
    issue: str,
    date_str: str,
) -> int:
    source_id = source_id or _content_hash(text_raw)
    with engine.connect() as conn:
        result = conn.execute(text("""
            INSERT INTO pulse_events_raw (source_type, source_id, text_raw)
            VALUES ('grievance', :sid, :txt)
            ON CONFLICT DO NOTHING
            RETURNING id
        """), {"sid": source_id, "txt": text_raw})
        conn.commit()
        return result.rowcount


# ── CLI ───────────────────────────────────────────────────────────────────────

def run(csv_path: Path | None = None) -> None:
    engine = sa.create_engine(os.environ["POSTGRES_URL"])
    if csv_path:
        n = load_from_csv(csv_path, engine)
    else:
        logger.info(
            "Attempting live scrape from jansunwai.up.nic.in — "
            "if this fails, download CSV from the portal and run with --csv FILE"
        )
        n = scrape_live(engine)
    print(f"Inserted {n} grievance event(s) into pulse_events_raw.")
    if n > 0:
        print("Run next: python -m flows.nlp.flow_sentiment")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Ingest UP Jansunwai grievance data")
    parser.add_argument("--csv", type=Path, default=None,
                        help="Path to manually downloaded Jansunwai CSV export")
    args = parser.parse_args()
    run(args.csv)
