"""
ETL: Fix two data quality issues in GKP_322 from JSON files only (no raw PDF/Excel).

Issue 1 — booth_master.polling_station_name is Hindi/Devanagari.
  Source: PoolBoothData_JSON part_*.json → section_name (English transliteration).
  Fallback for unmapped booths: "Polling Station {N} - Gorakhpur Urban"

Issue 2 — booth_results.party has garbage values ('1.0', '2.0', numeric IND serials).
  Root cause: original ingestion parsed row indices as party names.
  Fix: Re-ingest GKP_322 2022 results from Form20_JSON/AC322.json which has
       proper party names per candidate_vote entry (B.J.P, Samajwadi Party, etc.)

Run: python -m etl.fix_booth_names_and_results
"""
from __future__ import annotations

import glob
import json
import logging
import os
from collections import Counter
from pathlib import Path

import sqlalchemy as sa
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()
logger = logging.getLogger(__name__)

DATA_DIR    = Path(__file__).parents[1] / "data"
FORM20_JSON = DATA_DIR / "Form20_JSON" / "AC322.json"
POOL_DIR    = DATA_DIR / "PoolBoothData_JSON"

# Party name → canonical abbreviation
_PARTY_MAP: dict[str, str | None] = {
    "B.J.P":                        "BJP",
    "B.S.P.":                       "BSP",
    "Samajwadi Party":               "SP",
    "Indian National Congress":      "INC",
    "Aam Aadami Party":              "AAP",
    "None Of The Above":             "NOTA",
    "Indpendent":                    "IND",
    "Independent":                   "IND",
    "Aazad Samaj Party (Kashi Ram)": "AZSP",
    "Anarakshit Samaj Party":        "ANARAKSHIT",
    "Bharatiya Jan Jagriti Party":   "BJJP",
    "Janta Rakshak Party":           "JRP",
    "Party Affiliation":             None,   # skip placeholder rows
}

AC_NAME = "Gorakhpur Urban"


# ── Booth name map from PoolBoothData ─────────────────────────────────────────

def _build_name_map() -> dict[int, str]:
    """part_number → dominant English section_name from PoolBoothData JSON."""
    name_map: dict[int, str] = {}
    for fpath in glob.glob(str(POOL_DIR / "part_*.json")):
        try:
            data = json.loads(Path(fpath).read_text(encoding="utf-8"))
        except Exception:
            continue
        meta = data.get("metadata", {})
        part = meta.get("part_number")
        if not part:
            continue
        sections = [
            r.get("section_name", "").strip()
            for r in data.get("voter_records", [])
            if r.get("section_name", "").strip()
        ]
        if sections:
            top = Counter(sections).most_common(1)[0][0]
            # Capitalise words for display
            name_map[int(part)] = top.title()
    return name_map


# ── Fix 1: polling_station_name ───────────────────────────────────────────────

def fix_booth_names(engine: sa.Engine, name_map: dict[int, str]) -> int:
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT booth_id, booth_number FROM booth_master WHERE ac_id = 'GKP_322'"
        )).fetchall()

    updated = 0
    with engine.begin() as conn:
        for booth_id, booth_number in rows:
            english_name = name_map.get(booth_number, f"Polling Station {booth_number} - {AC_NAME}")
            conn.execute(text(
                "UPDATE booth_master SET polling_station_name = :name WHERE booth_id = :bid"
            ), {"name": english_name, "bid": booth_id})
            updated += 1

    logger.info("Updated polling_station_name for %d booths", updated)
    return updated


# ── Fix 2: booth_results from AC322.json ──────────────────────────────────────

def fix_booth_results(engine: sa.Engine) -> dict[str, int]:
    if not FORM20_JSON.exists():
        logger.error("AC322.json not found at %s", FORM20_JSON)
        return {"deleted": 0, "inserted": 0, "skipped": 0}

    data = json.loads(FORM20_JSON.read_text(encoding="utf-8"))
    polling_stations = data["sheets"][0]["polling_stations"]

    rows_to_insert: list[dict] = []
    skipped = 0

    for ps in polling_stations:
        booth_number = ps.get("polling_station_number")
        if not booth_number:
            skipped += 1
            continue

        booth_id = f"GKP_322_{int(booth_number):03d}"
        total_votes = sum(cv.get("votes", 0) or 0 for cv in ps.get("candidate_votes", []))

        # Determine winner (max votes)
        valid_cvs = [
            cv for cv in ps.get("candidate_votes", [])
            if _PARTY_MAP.get(cv.get("party", ""), cv.get("party", "")) is not None
            and cv.get("votes") is not None
        ]
        max_votes = max((cv["votes"] for cv in valid_cvs), default=0)

        for cv in ps.get("candidate_votes", []):
            raw_party = cv.get("party", "") or ""
            canonical = _PARTY_MAP.get(raw_party, raw_party[:30] if raw_party else None)
            if canonical is None:
                skipped += 1
                continue

            votes = cv.get("votes") or 0
            vote_share = round(votes / total_votes * 100, 4) if total_votes > 0 else None
            is_winner = (votes == max_votes and max_votes > 0)

            rows_to_insert.append({
                "booth_id":      booth_id,
                "election_year": 2022,
                "party":         canonical,
                "candidate_name": cv.get("candidate_name", ""),
                "votes":         votes,
                "vote_share":    vote_share,
                "winner_flag":   is_winner,
            })

    # Delete existing 2022 GKP_322 results then re-insert clean ones
    with engine.begin() as conn:
        r = conn.execute(text(
            "DELETE FROM booth_results WHERE election_year = 2022 "
            "AND booth_id LIKE 'GKP_322_%'"
        ))
        deleted = r.rowcount

        if rows_to_insert:
            conn.execute(text("""
                INSERT INTO booth_results
                    (booth_id, election_year, party, votes, vote_share, winner_flag)
                VALUES
                    (:booth_id, :election_year, :party, :votes, :vote_share, :winner_flag)
            """), rows_to_insert)

    logger.info(
        "booth_results: deleted %d stale rows, inserted %d clean rows, skipped %d",
        deleted, len(rows_to_insert), skipped,
    )
    return {"deleted": deleted, "inserted": len(rows_to_insert), "skipped": skipped}


# ── Main ──────────────────────────────────────────────────────────────────────

def run(engine: sa.Engine) -> dict:
    name_map = _build_name_map()
    logger.info("Built name map for %d booths from PoolBoothData", len(name_map))

    names_updated = fix_booth_names(engine, name_map)
    results       = fix_booth_results(engine)

    return {
        "booth_names_updated": names_updated,
        "pool_data_names":     len(name_map),
        "results_deleted":     results["deleted"],
        "results_inserted":    results["inserted"],
        "results_skipped":     results["skipped"],
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    engine = sa.create_engine(os.environ["POSTGRES_URL"])
    result = run(engine)
    print("Done:", result)
