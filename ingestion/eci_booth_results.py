"""
Scraper: ECI Form-20 — Booth-level vote counts

What Form-20 contains:
  Booth number, Party name, Candidate name, Votes polled, Total votes, Turnout %
  For each polling station in the constituency.

Source:
  CEO UP: ceouttarpradesh.nic.in → Election Results → Assembly Election 2022 → Form-20
  ECI:    results.eci.gov.in (may redirect — check current URL)

Strategy:
  1. Download the Form-20 PDF for AC 322 (Gorakhpur Urban) from CEO UP
  2. Parse the PDF table using pdfplumber
  3. Insert into booth_results + turnout_stats tables

IMPORTANT: The portal often requires manual download due to CAPTCHA.
If scraping fails, download the PDF manually and run:
  python -m ingestion.eci_booth_results --pdf path/to/form20_322.pdf

Requires: pip install pdfplumber requests

Run:
  python -m ingestion.eci_booth_results               # attempt auto-scrape
  python -m ingestion.eci_booth_results --pdf FILE    # parse local PDF
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import time
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import text
from etl.constants import normalise_party as _normalise_party

logger = logging.getLogger(__name__)

# Gorakhpur Urban AC 322 pilot scope
AC_NUMBER = 322
AC_ID     = "GKP_322"

# CEO UP Form-20 URL pattern (verify this is still valid before running)
FORM20_URL_2022 = (
    "https://ceouttarpradesh.nic.in/FORM20/{ac_number}/form20_{ac_number}.pdf"
)
FORM20_URL_2024_LS = (
    "https://ceouttarpradesh.nic.in/LokSabha2024/Form20/Form20_{ls_number}.pdf"
)


def _make_booth_id(part_no: int) -> str:
    return f"GKP_{AC_NUMBER}_{part_no:03d}"


# ── PDF Parser ────────────────────────────────────────────────────────────────

def parse_form20_pdf(pdf_path: Path) -> list[dict]:
    """
    Parse Form-20 PDF and extract booth-wise vote counts.

    Expected table structure in PDF:
    | Serial No | Polling Station | Candidate | Party | Votes |
    or
    | Part No | Station Name | BJP | SP | BSP | INC | NOTA | Total | Turnout% |

    Returns list of dicts ready for booth_results table.
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("Run: pip install pdfplumber")

    rows: list[dict] = []

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            tables = page.extract_tables()
            if not tables:
                logger.debug("No tables on page %d", page_num)
                continue

            for table in tables:
                if not table or len(table) < 2:
                    continue
                headers = [str(c or "").upper().strip() for c in table[0]]

                for data_row in table[1:]:
                    if not data_row or not any(data_row):
                        continue
                    row_text = [str(c or "").strip() for c in data_row]

                    # Try to find Part No (first numeric column)
                    part_no = None
                    for cell in row_text[:3]:
                        m = re.match(r"^(\d+)$", cell)
                        if m:
                            part_no = int(m.group(1))
                            break

                    if part_no is None:
                        continue

                    booth_id = _make_booth_id(part_no)

                    # Try party-column format (BJP, SP, BSP in separate columns)
                    if len(headers) >= 5:
                        for j, header in enumerate(headers):
                            party = _normalise_party(header)
                            if party in ["BJP", "SP", "BSP", "INC", "NOTA"] and j < len(row_text):
                                try:
                                    votes = int(re.sub(r"[^\d]", "", row_text[j]) or 0)
                                except ValueError:
                                    continue
                                if votes > 0:
                                    rows.append({
                                        "booth_id":     booth_id,
                                        "election_year":2022,
                                        "party":        party,
                                        "votes":        votes,
                                        "winner_flag":  False,
                                    })

    logger.info("Parsed %d vote rows from %s", len(rows), pdf_path.name)
    return rows


# ── Auto-scrape ───────────────────────────────────────────────────────────────

def attempt_auto_download(save_path: Path) -> bool:
    """
    Attempt to download Form-20 PDF from CEO UP.
    Returns True if successful. Many portals block bots — manual download likely needed.
    """
    try:
        import requests
    except ImportError:
        logger.error("pip install requests")
        return False

    url = FORM20_URL_2022.format(ac_number=AC_NUMBER)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/pdf,*/*",
    }

    try:
        logger.info("Attempting download: %s", url)
        resp = requests.get(url, headers=headers, timeout=30, stream=True)
        resp.raise_for_status()
        if "pdf" not in resp.headers.get("Content-Type", "").lower():
            logger.warning("Response is not PDF — CAPTCHA or redirect likely")
            return False
        save_path.write_bytes(resp.content)
        logger.info("Downloaded Form-20 to %s (%d KB)", save_path, len(resp.content) // 1024)
        return True
    except Exception as e:
        logger.warning("Auto-download failed: %s", e)
        return False


# ── Postgres Loader ───────────────────────────────────────────────────────────

def load_booth_results(rows: list[dict], engine: sa.Engine) -> int:
    if not rows:
        return 0

    # Mark winners (max votes per booth)
    from collections import defaultdict
    max_votes: dict[str, int] = defaultdict(int)
    for r in rows:
        max_votes[r["booth_id"]] = max(max_votes[r["booth_id"]], r["votes"])
    for r in rows:
        r["winner_flag"] = r["votes"] == max_votes[r["booth_id"]]

    with engine.connect() as conn:
        for r in rows:
            conn.execute(text("""
                INSERT INTO booth_results
                    (booth_id, election_year, party, votes, winner_flag)
                VALUES
                    (:booth_id, :election_year, :party, :votes, :winner_flag)
                ON CONFLICT DO NOTHING
            """), r)
        conn.commit()

    logger.info("Inserted %d booth_results rows", len(rows))
    return len(rows)


# ── CLI ───────────────────────────────────────────────────────────────────────

def run(pdf_path: Path | None = None):
    engine = sa.create_engine(os.environ["POSTGRES_URL"])

    if pdf_path is None:
        save_path = Path("data/data") / f"form20_ac{AC_NUMBER}_2022.pdf"
        success = attempt_auto_download(save_path)
        if not success:
            logger.error(
                "\n"
                "Auto-download failed (CAPTCHA likely).\n"
                "Manual steps:\n"
                "  1. Open: ceouttarpradesh.nic.in → Election Results → Assembly 2022 → Form-20\n"
                "  2. Select AC: 322 (Gorakhpur Urban)\n"
                "  3. Download PDF → save as: data/data/form20_ac322_2022.pdf\n"
                "  4. Run: python -m ingestion.eci_booth_results --pdf data/data/form20_ac322_2022.pdf\n"
            )
            return
        pdf_path = save_path

    rows = parse_form20_pdf(pdf_path)
    if not rows:
        logger.warning("No data extracted from PDF. Check PDF structure.")
        return

    n = load_booth_results(rows, engine)
    logger.info("Form-20 ingestion complete: %d rows into booth_results", n)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Ingest ECI Form-20 booth vote data")
    parser.add_argument("--pdf", type=Path, default=None,
                        help="Path to manually downloaded Form-20 PDF")
    args = parser.parse_args()
    run(args.pdf)
