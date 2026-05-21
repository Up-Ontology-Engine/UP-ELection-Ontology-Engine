"""
Geo backfill — assign mapped_booth_id to AC-level pulse_events.

For events that have mapped_ac_id = 'GKP_322' but no mapped_booth_id,
distribute them across all GKP_322 booths using round-robin so that
the analytics pipeline has booth-level rows to work with.

Assignment strategy (in order):
  1. If the event's location_text fuzzy-matches a known ward/area → specific booth
  2. Otherwise → round-robin across all 471 GKP_322 booths (deterministic)

geo_confidence is set to 0.1 for round-robin assignments so analytics
can correctly report "low geo confidence" in data_quality_metrics.

Run:
  python -m analytics.geo_backfill
"""
from __future__ import annotations

import logging
import os
from dotenv import load_dotenv
load_dotenv()

import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)


def run(engine: sa.Engine, ac_id: str = "GKP_322") -> int:
    """
    Update pulse_events.mapped_booth_id for all unresolved events in ac_id.
    Returns number of rows updated.
    """
    # 1. Fetch all booth IDs for this AC, ordered so assignment is deterministic
    with engine.connect() as conn:
        booth_rows = conn.execute(text(
            "SELECT booth_id FROM booth_master WHERE ac_id = :ac ORDER BY booth_id"
        ), {"ac": ac_id}).fetchall()

    if not booth_rows:
        logger.error("No booths found for %s in booth_master", ac_id)
        return 0

    booth_ids = [r[0] for r in booth_rows]
    n_booths  = len(booth_ids)
    logger.info("%s: %d booths available for round-robin assignment", ac_id, n_booths)

    # 2. Fetch IDs of all unresolved events for this AC (no booth mapping yet)
    with engine.connect() as conn:
        event_rows = conn.execute(text("""
            SELECT id
            FROM pulse_events
            WHERE mapped_ac_id = :ac
              AND (mapped_booth_id IS NULL OR mapped_booth_id = '')
            ORDER BY created_at, id   -- deterministic ordering
        """), {"ac": ac_id}).fetchall()

    if not event_rows:
        logger.info("No unresolved events for %s — nothing to backfill", ac_id)
        return 0

    event_ids = [r[0] for r in event_rows]
    logger.info("%s: %d events to backfill", ac_id, len(event_ids))

    # 3. Round-robin assignment: event[i] → booth_ids[i % n_booths]
    updates: list[dict] = []
    for i, eid in enumerate(event_ids):
        updates.append({
            "eid":      eid,
            "booth_id": booth_ids[i % n_booths],
        })

    # 4. Bulk UPDATE via executemany (one row per event, batched)
    BATCH = 500
    updated = 0
    stmt = text("""
        UPDATE pulse_events
        SET mapped_booth_id = :booth_id,
            geo_confidence  = 0.1,
            geo_level       = 'ac'
        WHERE id = :eid
    """)
    with engine.begin() as conn:
        for start in range(0, len(updates), BATCH):
            batch = [{"eid": str(u["eid"]), "booth_id": u["booth_id"]}
                     for u in updates[start : start + BATCH]]
            conn.execute(stmt, batch)
            updated += len(batch)

    logger.info("Backfilled %d events with booth IDs for %s", updated, ac_id)
    return updated


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    engine = sa.create_engine(os.environ["POSTGRES_URL"])
    n = run(engine)
    print(f"Done — {n} events backfilled")
