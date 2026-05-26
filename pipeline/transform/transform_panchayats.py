"""
ETL: Panchayats → panchayat_master

Source:
  data/processed/text/egramswaraj_gorakhpur_panchayat_data.json

Block → AC mapping is hardcoded below (20 Gorakhpur blocks → 9 ACs).
Verify and extend if new blocks are found.

Connector key produced:
  panchayat_id = slug(block_name + "_" + gp_name)  e.g. "KHORABAR_ADDA_MOTEERAM"

Run: python -m etl.transform_panchayats
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import text
from etl.constants import BLOCK_TO_AC

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parents[1] / "data" / "data"


def _make_panchayat_id(block: str, gp_name: str) -> str:
    def slug(s: str) -> str:
        return re.sub(r"[^A-Z0-9]+", "_", s.strip().upper()).strip("_")
    return f"{slug(block)}_{slug(gp_name)}"


def load_panchayat_master(engine: sa.Engine) -> int:
    path = DATA_DIR / "text" / "egramswaraj_gorakhpur_panchayat_data.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    overview = data.get("district_overview", {})
    block_counts: dict[str, int] = data.get("block_wise_gram_panchayats", {})
    sample = data.get("sample_panchayat", {})

    rows: list[dict] = []

    # Build one row per panchayat from block_counts
    # We have counts only — individual GP names from sample and egramswaraj
    for block, gp_count in block_counts.items():
        ac_id = BLOCK_TO_AC.get(block, "GKP_UNKNOWN")
        if ac_id == "GKP_UNKNOWN":
            logger.warning("Block '%s' not in BLOCK_TO_AC map — defaulting to GKP_UNKNOWN", block)

        # If this is the sample block, use the real GP name
        if block == sample.get("block"):
            pradhan   = sample.get("pradhan", "")
            members   = sample.get("elected_members", [])
            gp_name   = sample.get("name", f"{block}_GP_001")
            rows.append({
                "panchayat_id": _make_panchayat_id(block, gp_name),
                "gp_name":      gp_name,
                "block_name":   block,
                "ac_id":        ac_id,
                "pradhan_name": pradhan,
                "total_reps":   len(members),
            })
        else:
            # Placeholder row per block (real GPs require full eGramSwaraj scrape)
            rows.append({
                "panchayat_id": _make_panchayat_id(block, "BLOCK_AGGREGATE"),
                "gp_name":      f"{block} (aggregate — {gp_count} GPs)",
                "block_name":   block,
                "ac_id":        ac_id,
                "pradhan_name": "",
                "total_reps":   0,
            })

    with engine.connect() as conn:
        for row in rows:
            conn.execute(
                text("""
                    INSERT INTO panchayat_master
                        (panchayat_id, gp_name, block_name, district_id)
                    VALUES
                        (:panchayat_id, :gp_name, :block_name, 'GKP')
                    ON CONFLICT (panchayat_id) DO UPDATE SET
                        gp_name    = EXCLUDED.gp_name,
                        block_name = EXCLUDED.block_name
                """),
                row,
            )
        conn.commit()

    logger.info("Upserted %d panchayat rows (20 blocks, 1 sample GP)", len(rows))
    logger.info("NOTE: Run ingestion/egramswaraj_schemes.py to load all 1,273 GPs with full detail")
    return len(rows)


def run():
    engine = sa.create_engine(os.environ["POSTGRES_URL"])
    load_panchayat_master(engine)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run()
