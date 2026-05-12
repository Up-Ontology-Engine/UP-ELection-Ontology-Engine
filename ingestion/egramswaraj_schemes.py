"""
Scraper: eGramSwaraj — Scheme activity with beneficiary counts per panchayat

Sources:
  https://egramswaraj.gov.in/reportPlanActivityReport.do
  State: Uttar Pradesh (code 9)
  District: Gorakhpur (code 188)

What we get per panchayat per scheme:
  - Scheme name, financial year
  - Sanctioned amount, expenditure
  - Beneficiary count
  - Completion status (completed/in_progress)
  - Activity description

Loads into: scheme_activity table
  panchayat_id, scheme_name, issue_tag, beneficiary_count, status, financial_year

Scheme → Issue tag mapping:
  Jal Jeevan Mission         → water
  PMAY (Rural/Urban)         → housing
  MGNREGA                    → jobs
  PMGSY (road)               → roads
  PM Ujjwala                 → electricity
  Swachh Bharat              → sanitation

Run: python -m ingestion.egramswaraj_schemes
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

# eGramSwaraj state/district codes
STATE_CODE    = "9"    # Uttar Pradesh
DISTRICT_CODE = "188"  # Gorakhpur
DISTRICT_ID   = "GKP"

# Scheme name → issue tag
SCHEME_TO_ISSUE: dict[str, str] = {
    "jal jeevan":        "water",
    "jjm":               "water",
    "har ghar jal":      "water",
    "pmay":              "housing",
    "pradhan mantri awas": "housing",
    "mgnrega":           "jobs",
    "mahatma gandhi":    "jobs",
    "nrega":             "jobs",
    "pmgsy":             "roads",
    "pradhan mantri gram sadak": "roads",
    "ujjwala":           "electricity",
    "pm ujjwala":        "electricity",
    "saubhagya":         "electricity",
    "swachh bharat":     "sanitation",
    "odf":               "sanitation",
    "mdm":               "education",
    "mid day meal":      "education",
    "pm kisan":          "farmer",
    "kisan":             "farmer",
    "pension":           "welfare",
    "ayushman":          "health",
    "pmjay":             "health",
    "insurance":         "welfare",
}

BASE_URL = "https://egramswaraj.gov.in"
PLAN_REPORT_URL = f"{BASE_URL}/reportPlanActivityReport.do"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": BASE_URL,
}

SEEDS_DIR = Path(__file__).parents[1] / "data" / "seeds"


def _issue_tag(scheme_name: str) -> str:
    lower = scheme_name.lower()
    for keyword, tag in SCHEME_TO_ISSUE.items():
        if keyword in lower:
            return tag
    return "governance"


def _parse_amount(text: str) -> int:
    digits = re.sub(r"[^\d.]", "", text or "")
    try:
        return int(float(digits) * 100)  # store paise to preserve precision
    except ValueError:
        return 0


def _make_panchayat_id(block: str, gp: str) -> str:
    def slug(s: str) -> str:
        return re.sub(r"[^A-Z0-9]+", "_", s.strip().upper()).strip("_")
    return f"{slug(block)}_{slug(gp)}"


def scrape_gp_list(block_code: str, block_name: str) -> list[dict]:
    """Get all gram panchayats for a block."""
    try:
        params = {
            "stateCode": STATE_CODE,
            "districtCode": DISTRICT_CODE,
            "blockCode": block_code,
        }
        resp = requests.get(
            f"{BASE_URL}/getGramPanchayatList.do",
            params=params, headers=HEADERS, timeout=20
        )
        resp.raise_for_status()
        data = resp.json()
        gps = []
        for item in data if isinstance(data, list) else data.get("data", []):
            gps.append({
                "gp_code": str(item.get("gpCode") or item.get("code", "")),
                "gp_name": str(item.get("gpName") or item.get("name", "")),
                "block_name": block_name,
            })
        logger.info("Block %s: %d GPs", block_name, len(gps))
        return gps
    except Exception as e:
        logger.warning("GP list failed for block %s: %s", block_name, e)
        return []


def scrape_gp_schemes(gp_code: str, gp_name: str, block_name: str) -> list[dict]:
    """Get scheme activity for one GP."""
    try:
        params = {
            "stateCode":    STATE_CODE,
            "districtCode": DISTRICT_CODE,
            "gpCode":       gp_code,
            "finYear":      "2024-2025",
        }
        resp = requests.get(PLAN_REPORT_URL, params=params, headers=HEADERS, timeout=20)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        rows_data = []
        table = soup.find("table", id=re.compile(r"report|data|plan", re.I)) or soup.find("table")
        if not table:
            return []

        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        panchayat_id = _make_panchayat_id(block_name, gp_name)

        for row in table.find_all("tr")[1:]:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cells) < 3:
                continue

            scheme_name = _safe_col(cells, headers, "scheme") or cells[0]
            if not scheme_name or scheme_name.lower() in ("s.no", "sr.no", "#"):
                continue

            rows_data.append({
                "panchayat_id":    panchayat_id,
                "gp_name":         gp_name,
                "block_name":      block_name,
                "scheme_name":     scheme_name,
                "issue_tag":       _issue_tag(scheme_name),
                "activity_desc":   _safe_col(cells, headers, "activity") or "",
                "beneficiary_count": int(re.sub(r"\D", "", _safe_col(cells, headers, "beneficiar") or "0") or 0),
                "sanctioned_amount": _parse_amount(_safe_col(cells, headers, "sanction") or "0"),
                "expenditure":     _parse_amount(_safe_col(cells, headers, "expenditure") or "0"),
                "status":          _safe_col(cells, headers, "status") or "completed",
                "financial_year":  "2024-2025",
            })

        return rows_data
    except Exception as e:
        logger.debug("Scheme scrape failed for GP %s: %s", gp_name, e)
        return []


def _safe_col(cells: list[str], headers: list[str], keyword: str) -> str:
    for i, h in enumerate(headers):
        if keyword in h and i < len(cells):
            return cells[i]
    return ""


def scrape_blocks() -> list[dict]:
    """Get block list for Gorakhpur district."""
    try:
        params = {"stateCode": STATE_CODE, "districtCode": DISTRICT_CODE}
        resp = requests.get(
            f"{BASE_URL}/getBlockList.do",
            params=params, headers=HEADERS, timeout=20
        )
        resp.raise_for_status()
        data = resp.json()
        blocks = []
        for item in data if isinstance(data, list) else data.get("data", []):
            blocks.append({
                "block_code": str(item.get("blockCode") or item.get("code", "")),
                "block_name": str(item.get("blockName") or item.get("name", "")),
            })
        logger.info("District Gorakhpur: %d blocks", len(blocks))
        return blocks
    except Exception as e:
        logger.warning("Block list failed: %s", e)
        # Fallback to known block names
        return [
            {"block_code": "0001", "block_name": "Khorabar"},
            {"block_code": "0002", "block_name": "Campierganj"},
            {"block_code": "0003", "block_name": "Pipraich"},
            {"block_code": "0004", "block_name": "Sahjanawa"},
            {"block_code": "0005", "block_name": "Khajni"},
            {"block_code": "0006", "block_name": "Barhalganj"},
            {"block_code": "0007", "block_name": "Bansgaon"},
            {"block_code": "0008", "block_name": "Belghat"},
            {"block_code": "0009", "block_name": "Gagaha"},
            {"block_code": "0010", "block_name": "Gola"},
            {"block_code": "0011", "block_name": "Kauri Ram"},
            {"block_code": "0012", "block_name": "Pali"},
            {"block_code": "0013", "block_name": "Brahmpur"},
            {"block_code": "0014", "block_name": "Uruwa"},
            {"block_code": "0015", "block_name": "Bhathat"},
            {"block_code": "0016", "block_name": "Bharohiya"},
            {"block_code": "0017", "block_name": "Sardarnagar"},
            {"block_code": "0018", "block_name": "Chargawan"},
            {"block_code": "0019", "block_name": "Piprauli"},
            {"block_code": "0020", "block_name": "Jangal Kaudia"},
        ]


def load_to_postgres(rows: list[dict], engine: sa.Engine) -> int:
    if not rows:
        return 0

    with engine.connect() as conn:
        # Ensure panchayat exists before inserting scheme_activity
        for r in rows:
            conn.execute(text("""
                INSERT INTO panchayat_master (panchayat_id, gp_name, block_name, district_id)
                VALUES (:pid, :gp, :block, 'GKP')
                ON CONFLICT (panchayat_id) DO UPDATE SET gp_name = EXCLUDED.gp_name
            """), {"pid": r["panchayat_id"], "gp": r["gp_name"], "block": r["block_name"]})

        for r in rows:
            conn.execute(text("""
                INSERT INTO scheme_activity
                    (panchayat_id, scheme_name, issue_tag, activity_desc,
                     beneficiary_count, status, financial_year)
                VALUES
                    (:pid, :scheme, :issue, :desc,
                     :bcount, :status, :fy)
                ON CONFLICT DO NOTHING
            """), {
                "pid":    r["panchayat_id"],
                "scheme": r["scheme_name"],
                "issue":  r["issue_tag"],
                "desc":   r.get("activity_desc", ""),
                "bcount": r.get("beneficiary_count", 0),
                "status": r.get("status", "completed"),
                "fy":     r.get("financial_year", "2024-2025"),
            })

        conn.commit()
    return len(rows)


def run(block_filter: str | None = None, max_gps: int = 50):
    """
    Args:
        block_filter: Only scrape this block name (e.g. 'Khorabar')
        max_gps: Max GPs per block (to avoid rate limiting on first run)
    """
    engine = sa.create_engine(os.environ["POSTGRES_URL"])

    blocks = scrape_blocks()
    total_rows = 0

    for block in blocks:
        if block_filter and block["block_name"].lower() != block_filter.lower():
            continue

        gps = scrape_gp_list(block["block_code"], block["block_name"])
        gps = gps[:max_gps]

        for gp in gps:
            rows = scrape_gp_schemes(gp["gp_code"], gp["gp_name"], block["block_name"])
            n = load_to_postgres(rows, engine)
            total_rows += n
            time.sleep(0.5)

        time.sleep(1.0)

    logger.info("eGramSwaraj scrape complete: %d scheme rows loaded", total_rows)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--block", default=None, help="Scrape only this block name")
    p.add_argument("--max-gps", type=int, default=50, help="Max GPs per block")
    args = p.parse_args()
    run(block_filter=args.block, max_gps=args.max_gps)
