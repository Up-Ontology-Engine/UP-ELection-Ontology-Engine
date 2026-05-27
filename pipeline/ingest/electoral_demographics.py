"""
Scraper: Electoral Demographics — Voter summary stats per constituency

Sources (in order of preference):
  1. Local electoral roll XLSX files (already downloaded)
     → Aggregate Age + Gender per Part No (booth)
  2. NVSP (National Voter Service Portal) summary stats
     → Total voters, male/female breakdown per AC
  3. ECI Election Commission summary reports
  4. CEO UP portal form downloads

What this produces:
  - booth_master: total_voters, male_voters, female_voters per booth
  - New table: ac_demographics (total AC-level voter stats with age bands)

For full booth-level data:
  The electoral roll PDFs in data/data/Raw file/ are image-based (Hindi script)
  and require OCR. We use what we can from the XLSX files and NVSP API.

Run: python -m ingestion.electoral_demographics
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

import pandas as pd
import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    raise ImportError("Run: pip install requests")

DATA_DIR = Path(__file__).parents[2] / "data" / "data"

# All 9 AC numbers + their NVSP state/AC codes
# UP state code on NVSP = S24 (based on file names 2026-EROLLGEN-S24-322...)
NVSP_STATE_CODE = "S24"

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

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


# ── Step 1: Aggregate from local XLSX files ───────────────────────────────────


def aggregate_from_local_xlsx() -> dict[str, dict]:
    """
    Read the electoral roll XLSX files we already have.
    Returns {ac_id: {total, male, female, age_18_25, ...}}

    Note: Part No is missing in the XLSX — we treat all rows as AC 322 (pilot scope).
    """
    rolls = [
        DATA_DIR / "Convert to xcel sheet" / "electoral_roll.xlsx",
        DATA_DIR / "Convert to xcel sheet" / "electoral_roll (1).xlsx",
    ]

    frames = []
    for path in rolls:
        if path.exists():
            wb = __import__("openpyxl").load_workbook(path, read_only=True, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                continue
            header = [str(c) if c else "" for c in rows[0]]
            records = []
            for row in rows[1:]:
                d = dict(zip(header, row))
                records.append(d)
            frames.append(pd.DataFrame(records))
            wb.close()

    if not frames:
        logger.warning("No local XLSX files found")
        return {}

    df = pd.concat(frames, ignore_index=True)
    df.columns = [c.strip() for c in df.columns]
    df["Age"] = pd.to_numeric(df.get("Age", 0), errors="coerce")
    df["Gender"] = df.get("Gender", "").astype(str).str.strip().str.upper()

    # Part No is empty → treat all as GKP_322 aggregate
    agg = {
        "GKP_322": {
            "total_voters": len(df),
            "male_voters": int((df["Gender"] == "MALE").sum()),
            "female_voters": int((df["Gender"] == "FEMALE").sum()),
            "other_voters": int((~df["Gender"].isin(["MALE", "FEMALE"])).sum()),
            "age_18_25": int(((df["Age"] >= 18) & (df["Age"] <= 25)).sum()),
            "age_26_40": int(((df["Age"] >= 26) & (df["Age"] <= 40)).sum()),
            "age_40_60": int(((df["Age"] > 40) & (df["Age"] <= 60)).sum()),
            "age_60_plus": int((df["Age"] > 60).sum()),
            "source": "local_xlsx",
            "note": "Part No missing — these are AC-level aggregates only",
        }
    }

    logger.info(
        "Local XLSX: AC GKP_322 — %d total voters (male=%d, female=%d)",
        agg["GKP_322"]["total_voters"],
        agg["GKP_322"]["male_voters"],
        agg["GKP_322"]["female_voters"],
    )
    return agg


# ── Step 2: Scrape NVSP for AC-level voter stats ─────────────────────────────


def scrape_nvsp_voter_stats(ac_no: int) -> dict | None:
    """
    NVSP summary voter statistics per constituency.
    Returns {total, male, female, third_gender} or None if unavailable.
    """
    # NVSP voter data API (public)
    url = "https://www.nvsp.in/forms/forms/searchepicdata"
    try:
        params = {
            "stateCode": NVSP_STATE_CODE,
            "assemblyCode": str(ac_no),
            "type": "summary",
        }
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        if resp.status_code == 200 and resp.text.strip().startswith("{"):
            data = resp.json()
            return {
                "total_voters": data.get("totalVoters", 0),
                "male_voters": data.get("maleVoters", 0),
                "female_voters": data.get("femaleVoters", 0),
                "other_voters": data.get("thirdGenderVoters", 0),
                "source": "nvsp",
            }
    except Exception as e:
        logger.debug("NVSP failed for AC %d: %s", ac_no, e)

    # Fallback: CEO UP portal
    try:
        ceo_url = f"https://ceouttarpradesh.nic.in/VoterDetail.aspx?ACNo={ac_no}"
        resp = requests.get(ceo_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        # Parse the voter count table
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(resp.text, "html.parser")
        stats = {}
        for row in soup.find_all("tr"):
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cells) >= 2:
                key = cells[0].lower()
                val = int(re.sub(r"\D", "", cells[1] or "0") or 0)
                if "male" in key and "female" not in key:
                    stats["male_voters"] = val
                elif "female" in key:
                    stats["female_voters"] = val
                elif "total" in key:
                    stats["total_voters"] = val
        if stats:
            stats["source"] = "ceoup"
            return stats
    except Exception as e:
        logger.debug("CEO UP voter stats failed for AC %d: %s", ac_no, e)

    return None


# ── Step 3: Load to Postgres ──────────────────────────────────────────────────


def ensure_ac_demographics_table(engine: sa.Engine) -> None:
    with engine.connect() as conn:
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS ac_demographics (
                ac_id           VARCHAR(30) PRIMARY KEY REFERENCES ac_master(ac_id),
                total_voters    INTEGER DEFAULT 0,
                male_voters     INTEGER DEFAULT 0,
                female_voters   INTEGER DEFAULT 0,
                other_voters    INTEGER DEFAULT 0,
                age_18_25       INTEGER DEFAULT 0,
                age_26_40       INTEGER DEFAULT 0,
                age_40_60       INTEGER DEFAULT 0,
                age_60_plus     INTEGER DEFAULT 0,
                data_source     VARCHAR(50),
                last_updated    TIMESTAMPTZ DEFAULT NOW(),
                notes           TEXT
            )
        """)
        )
        conn.commit()


def load_demographics(stats: dict[str, dict], engine: sa.Engine) -> int:
    ensure_ac_demographics_table(engine)
    count = 0
    with engine.connect() as conn:
        for ac_id, d in stats.items():
            conn.execute(
                text("""
                INSERT INTO ac_demographics
                    (ac_id, total_voters, male_voters, female_voters, other_voters,
                     age_18_25, age_26_40, age_40_60, age_60_plus, data_source, notes)
                VALUES
                    (:ac_id, :total, :male, :female, :other,
                     :a18, :a26, :a40, :a60, :src, :notes)
                ON CONFLICT (ac_id) DO UPDATE SET
                    total_voters  = EXCLUDED.total_voters,
                    male_voters   = EXCLUDED.male_voters,
                    female_voters = EXCLUDED.female_voters,
                    other_voters  = EXCLUDED.other_voters,
                    age_18_25     = EXCLUDED.age_18_25,
                    age_26_40     = EXCLUDED.age_26_40,
                    age_40_60     = EXCLUDED.age_40_60,
                    age_60_plus   = EXCLUDED.age_60_plus,
                    data_source   = EXCLUDED.data_source,
                    last_updated  = NOW()
            """),
                {
                    "ac_id": ac_id,
                    "total": d.get("total_voters", 0),
                    "male": d.get("male_voters", 0),
                    "female": d.get("female_voters", 0),
                    "other": d.get("other_voters", 0),
                    "a18": d.get("age_18_25", 0),
                    "a26": d.get("age_26_40", 0),
                    "a40": d.get("age_40_60", 0),
                    "a60": d.get("age_60_plus", 0),
                    "src": d.get("source", "unknown"),
                    "notes": d.get("note", ""),
                },
            )
            count += 1
        conn.commit()
    return count


def run():
    engine = sa.create_engine(os.environ["POSTGRES_URL"])

    # Step 1: aggregate from local files
    stats = aggregate_from_local_xlsx()

    # Step 2: try NVSP for all 9 ACs
    for ac_no, ac_id in TARGET_ACS.items():
        if ac_id in stats:
            continue  # already have from local
        nvsp = scrape_nvsp_voter_stats(ac_no)
        if nvsp:
            stats[ac_id] = nvsp
            logger.info("NVSP AC %d (%s): total=%d", ac_no, ac_id, nvsp.get("total_voters", 0))
        else:
            logger.warning("No voter stats for AC %d (%s) — will show zeros", ac_no, ac_id)
            stats[ac_id] = {
                "total_voters": 0,
                "male_voters": 0,
                "female_voters": 0,
                "other_voters": 0,
                "source": "unavailable",
            }

    n = load_demographics(stats, engine)
    logger.info("Loaded demographics for %d ACs", n)

    # Print summary
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT ac_id, total_voters, male_voters, female_voters, data_source FROM ac_demographics ORDER BY ac_id"
            )
        ).fetchall()
    for r in rows:
        logger.info("  %s: total=%d male=%d female=%d [%s]", *r)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run()
