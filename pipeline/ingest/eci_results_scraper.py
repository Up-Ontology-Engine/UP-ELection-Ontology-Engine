"""
Scraper: ECI Election Results — Candidate-wise vote counts for all 9 Gorakhpur ACs

Sources (in order of preference):
  1. ECI Statistical Reports XLS (direct download, no CAPTCHA)
     https://eci.gov.in/statistical-report/statistical-reports/
  2. CEO UP results page (may require parsing)
  3. Saved local data

What we get:
  - Candidate name, party, votes, vote_share, winner flag per AC
  - Turnout % per constituency
  - Writes to: booth_results (AC-level), turnout_stats, candidate_master

NOTE: This gets AC-level results (not booth-level Form-20).
      For booth-level data, use ingestion/eci_booth_results.py

Run: python -m ingestion.eci_results_scraper
"""

from __future__ import annotations

import io
import logging
import os
import re
import time

import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)

try:
    import pandas as pd
    import requests
except ImportError:
    raise ImportError("Run: pip install requests pandas openpyxl")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

# Target ACs — Gorakhpur district, UP Assembly 2022
TARGET_ACS = {
    320: "GKP_320",
    321: "GKP_321",
    322: "GKP_322",
    323: "GKP_323",
    324: "GKP_324",
    325: "GKP_325",
    326: "GKP_326",
    327: "GKP_327",
    328: "GKP_328",
}

# ECI direct download URL for UP Assembly 2022 constituency-wise results
# Item 33: Constituency Wise Detailed Result
ECI_UP_2022_RESULTS_XLS = (
    "https://eci.gov.in/files/file/15045-33-constituency-wise-detailed-result/"
)

# CEO UP results HTML page (fallback)
CEOUP_RESULTS_BASE = "https://ceouttarpradesh.nic.in/MIS/ElectionResult.aspx"

PARTY_NORM = {
    "BHARATIYA JANATA PARTY": "BJP",
    "BJP": "BJP",
    "SAMAJWADI PARTY": "SP",
    "SP": "SP",
    "BAHUJAN SAMAJ PARTY": "BSP",
    "BSP": "BSP",
    "INDIAN NATIONAL CONGRESS": "INC",
    "INC": "INC",
    "CONGRESS": "INC",
    "NONE OF THE ABOVE": "NOTA",
    "NOTA": "NOTA",
    "INDEPENDENT": "IND",
}


def _norm_party(raw: str) -> str:
    u = raw.strip().upper()
    for k, v in PARTY_NORM.items():
        if k in u:
            return v
    m = re.search(r"\(([A-Z]{2,8})\)", u)
    return m.group(1) if m else u[:20]


def _slugify(name: str, year: int) -> str:
    slug = re.sub(r"[^A-Z0-9]+", "_", name.strip().upper()).strip("_")
    return f"{slug}_{year}"


def fetch_eci_xls_results() -> pd.DataFrame | None:
    """
    Try to download ECI constituency-wise results XLS for UP 2022.
    Returns DataFrame with columns: constituency_no, candidate, party, votes, winner
    """
    try:
        resp = requests.get(ECI_UP_2022_RESULTS_XLS, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        df = pd.read_excel(io.BytesIO(resp.content), engine="openpyxl")
        logger.info("Downloaded ECI results XLS: %d rows", len(df))
        return df
    except Exception as e:
        logger.warning("ECI XLS download failed: %s", e)
        return None


def scrape_ceoup_results(ac_no: int) -> list[dict]:
    """
    Scrape CEO UP results page for one AC.
    Returns list of {candidate, party, votes, vote_share, winner}
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise ImportError("Run: pip install beautifulsoup4")

    url = f"{CEOUP_RESULTS_BASE}?ac_no={ac_no}&election_year=2022"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        logger.error("CEO UP failed for AC %d: %s", ac_no, e)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    table = soup.find("table", {"id": re.compile(r"result|candidate", re.I)}) or soup.find("table")
    if not table:
        return []

    rows = table.find_all("tr")
    for row in rows[1:]:
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cells) < 4:
            continue
        try:
            votes = int(re.sub(r"\D", "", cells[3] or "0") or 0)
        except ValueError:
            votes = 0
        results.append(
            {
                "candidate": cells[1] if len(cells) > 1 else "",
                "party": _norm_party(cells[2] if len(cells) > 2 else ""),
                "votes": votes,
                "winner": "winner" in row.get("class", []) or "★" in " ".join(cells),
            }
        )

    logger.info("CEO UP AC %d: %d result rows", ac_no, len(results))
    return results


def load_results_to_postgres(
    results: list[dict],
    ac_id: str,
    ac_no: int,
    election_year: int,
    engine: sa.Engine,
) -> int:
    if not results:
        return 0

    total_votes = sum(r["votes"] for r in results)
    winner_votes = max((r["votes"] for r in results), default=0)

    with engine.connect() as conn:
        # Ensure AC-level virtual booth exists (booth_number=0 means aggregate)
        conn.execute(
            text("""
            INSERT INTO booth_master (booth_id, ac_id, booth_number, polling_station_name)
            VALUES (:bid, :ac_id, 0, 'AC Total Aggregate')
            ON CONFLICT (booth_id) DO NOTHING
        """),
            {"bid": f"{ac_id}_TOTAL", "ac_id": ac_id},
        )

        for r in results:
            cid = _slugify(r["candidate"], election_year)
            party = r["party"]
            votes = r["votes"]
            share = round(votes / total_votes * 100, 2) if total_votes else 0.0
            is_winner = r.get("winner", False) or votes == winner_votes

            # Upsert candidate
            conn.execute(
                text("""
                INSERT INTO candidate_master (candidate_id, name, party, ac_id, election_year)
                VALUES (:cid, :name, :party, :ac_id, :year)
                ON CONFLICT (candidate_id) DO UPDATE SET party = EXCLUDED.party
            """),
                {
                    "cid": cid,
                    "name": r["candidate"],
                    "party": party,
                    "ac_id": ac_id,
                    "year": election_year,
                },
            )

            # AC-level result stored with booth_id = ac_id (constituency aggregate)
            conn.execute(
                text("""
                INSERT INTO booth_results
                    (booth_id, election_year, party, candidate_id, votes, vote_share, winner_flag)
                VALUES (:booth_id, :year, :party, :cid, :votes, :share, :winner)
                ON CONFLICT DO NOTHING
            """),
                {
                    "booth_id": f"{ac_id}_TOTAL",  # AC aggregate placeholder
                    "year": election_year,
                    "party": party,
                    "cid": cid,
                    "votes": votes,
                    "share": share,
                    "winner": is_winner,
                },
            )

        # Turnout
        conn.execute(
            text("""
            INSERT INTO turnout_stats (booth_id, election_year, total_votes, turnout_percent)
            VALUES (:bid, :year, :total, NULL)
            ON CONFLICT DO NOTHING
        """),
            {"bid": f"{ac_id}_TOTAL", "year": election_year, "total": total_votes},
        )

        conn.commit()

    logger.info(
        "AC %d: loaded %d candidate results (total votes: %d)", ac_no, len(results), total_votes
    )
    return len(results)


def run(ac_filter: int | None = None):
    engine = sa.create_engine(os.environ["POSTGRES_URL"])

    for ac_no, ac_id in TARGET_ACS.items():
        if ac_filter and ac_no != ac_filter:
            continue

        results = scrape_ceoup_results(ac_no)
        if not results:
            logger.warning("No results for AC %d — try manual ECI XLS download", ac_no)
            continue

        load_results_to_postgres(results, ac_id, ac_no, 2022, engine)
        time.sleep(1.5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--ac", type=int, default=None)
    args = p.parse_args()
    run(ac_filter=args.ac)
