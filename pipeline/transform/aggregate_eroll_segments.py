"""
ETL: Aggregate electoral roll (PoolBoothData) into privacy-safe booth-level
     demographic segments.

Reads all data/processed/pool_booth/part_*.json files.
Each file = one electoral roll part = one polling booth.
Aggregates age/gender counts — NO names, voter IDs, or addresses stored.

Segments produced per booth:
  youth        : age 18-30
  first_voter  : age 18-21  (proxy for first-time voters)
  women        : gender == Female
  elderly      : age > 60
  working_age  : age 25-55

Loads into: booth_demographic_segments table

Run: python -m etl.aggregate_eroll_segments
"""

from __future__ import annotations

import glob
import json
import logging
import os
from pathlib import Path

import sqlalchemy as sa
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parents[1] / "data" / "PoolBoothData_JSON"


def _build_booth_id(ac_number: int, part_number: int) -> str:
    return f"GKP_{ac_number}_{part_number:03d}"


def _aggregate_part(records: list[dict]) -> dict[str, int]:
    """Return segment counts from a list of voter records (no PII retained)."""
    counts: dict[str, int] = {
        "youth": 0,
        "first_voter": 0,
        "women": 0,
        "elderly": 0,
        "working_age": 0,
    }
    for r in records:
        age = r.get("age") or 0
        gender = (r.get("gender") or "").strip().lower()

        if 18 <= age <= 30:
            counts["youth"] += 1
        if 18 <= age <= 21:
            counts["first_voter"] += 1
        if gender == "female":
            counts["women"] += 1
        if age > 60:
            counts["elderly"] += 1
        if 25 <= age <= 55:
            counts["working_age"] += 1

    return counts


def run():
    engine = sa.create_engine(os.environ["POSTGRES_URL"])

    # Load total_voters per booth for pct calculation
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT booth_id, total_voters FROM booth_master WHERE total_voters > 0")
        ).fetchall()
    total_voters_map: dict[str, int] = {r[0]: r[1] for r in rows}

    part_files = sorted(glob.glob(str(DATA_DIR / "part_*.json")))
    if not part_files:
        logger.error("No PoolBoothData files found in %s", DATA_DIR)
        return

    loaded = 0
    skipped = 0

    with engine.begin() as conn:
        for fpath in part_files:
            try:
                data = json.loads(Path(fpath).read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed to read %s: %s", fpath, e)
                continue

            meta = data.get("metadata", {})
            ac_number = meta.get("assembly_constituency", {}).get("number")
            part_number = meta.get("part_number")
            voter_records = data.get("voter_records", [])

            if not ac_number or not part_number:
                skipped += 1
                continue

            booth_id = _build_booth_id(ac_number, part_number)
            total = total_voters_map.get(booth_id) or len(voter_records) or 1

            counts = _aggregate_part(voter_records)

            for segment_type, count in counts.items():
                pct = round(count / total, 4) if total > 0 else None
                conn.execute(
                    text("""
                    INSERT INTO booth_demographic_segments
                        (booth_id, segment_type, count, pct_of_voters)
                    VALUES (:booth_id, :seg, :count, :pct)
                    ON CONFLICT (booth_id, segment_type) DO UPDATE SET
                        count         = EXCLUDED.count,
                        pct_of_voters = EXCLUDED.pct_of_voters,
                        computed_at   = NOW()
                """),
                    {
                        "booth_id": booth_id,
                        "seg": segment_type,
                        "count": count,
                        "pct": pct,
                    },
                )

            loaded += 1
            logger.info("Loaded segments for %s (voters=%d)", booth_id, len(voter_records))

    logger.info("Done — %d booths loaded, %d skipped", loaded, skipped)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run()
