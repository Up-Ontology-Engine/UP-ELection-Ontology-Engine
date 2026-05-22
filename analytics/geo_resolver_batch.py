"""
Batch geo-resolution for pulse_events — GKP_322.

Reads every pulse_event that has a location_text but no mapped_booth_id,
runs GeoResolver, and writes back:
  - mapped_booth_id  (only when confidence >= BOOTH_THRESHOLD)
  - mapped_ac_id     (always set to GKP_322 for this pilot)
  - geo_level        ('booth' | 'ac')
  - geo_confidence   (fuzzy score 0.0–1.0)
  - geo_method       ('exact_alias' | 'fuzzy_alias' | 'ac_fallback')

Rules enforced:
  - NEVER assign a booth_id when confidence < BOOTH_THRESHOLD (0.75)
  - Events without location_text remain at AC level; never fabricate a booth
  - Events already having mapped_booth_id are skipped

Run:
    python -m analytics.geo_resolver_batch [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

import sqlalchemy as sa
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()

logger = logging.getLogger(__name__)

ALIAS_FILE       = Path(__file__).parents[1] / "data" / "seeds" / "gorakhpur_aliases.json"
BOOTH_THRESHOLD  = 0.75   # minimum geo_confidence to assign mapped_booth_id
PILOT_AC_ID      = "GKP_322"
BATCH_SIZE       = 500


def _load_aliases() -> dict:
    with open(ALIAS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("geo_aliases", {})


def _resolve(location_text: str, aliases: dict, keys: list[str]):
    """
    Returns (mapped_booth_id, mapped_ac_id, geo_level, geo_confidence, geo_method).
    Never returns a booth_id with confidence < BOOTH_THRESHOLD.
    """
    from thefuzz import process as fuzz

    if not location_text or len(location_text.strip()) < 2:
        return None, PILOT_AC_ID, "ac", 0.3, "ac_fallback"

    txt = location_text.strip()

    # Exact match first
    if txt in aliases:
        entry = aliases[txt]
        if entry["type"] == "booth":
            return entry["id"], PILOT_AC_ID, "booth", 1.0, "exact_alias"
        return None, entry["id"], "ac", 1.0, "exact_alias"

    # Fuzzy match
    if not keys:
        return None, PILOT_AC_ID, "ac", 0.3, "ac_fallback"

    match, score = fuzz.extractOne(txt, keys)
    geo_conf = round(score / 100.0, 3)
    entry    = aliases[match]

    if entry["type"] == "booth" and geo_conf >= BOOTH_THRESHOLD:
        return entry["id"], PILOT_AC_ID, "booth", geo_conf, "fuzzy_alias"

    if entry["type"] == "ac" and geo_conf >= BOOTH_THRESHOLD:
        return None, entry["id"], "ac", geo_conf, "fuzzy_alias"

    # Below threshold — keep at AC level
    return None, PILOT_AC_ID, "ac", geo_conf, "ac_fallback"


def run(engine: sa.Engine, dry_run: bool = False) -> dict:
    aliases = _load_aliases()
    keys    = list(aliases.keys())

    # Fetch events that have a location_text but no booth mapping
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id::text AS event_id, location_text
            FROM pulse_events
            WHERE location_text IS NOT NULL
              AND location_text != ''
              AND mapped_booth_id IS NULL
            ORDER BY created_at
        """)).mappings().fetchall()

    if not rows:
        logger.info("No events with unresolved location_text — nothing to do.")
        return {"scanned": 0, "booth_assigned": 0, "ac_level": 0}

    logger.info("Geo-resolving %d events with location_text", len(rows))

    updates: list[dict] = []
    counts  = {"booth_assigned": 0, "ac_level": 0}

    for r in rows:
        booth_id, ac_id, geo_level, geo_conf, geo_method = _resolve(
            r["location_text"], aliases, keys
        )
        updates.append({
            "event_id":       r["event_id"],
            "mapped_booth_id": booth_id,
            "mapped_ac_id":   ac_id,
            "geo_level":      geo_level,
            "geo_confidence": geo_conf,
            "geo_method":     geo_method,
        })
        if booth_id:
            counts["booth_assigned"] += 1
        else:
            counts["ac_level"] += 1

    if dry_run:
        logger.info("[dry-run] Would update %d events: %s", len(updates), counts)
        for u in updates[:10]:
            logger.info("  %s → booth=%s  conf=%.2f  method=%s",
                        u["event_id"][:8], u["mapped_booth_id"], u["geo_confidence"], u["geo_method"])
        return {"scanned": len(rows), **counts, "dry_run": True}

    # Bulk update in batches
    stmt = text("""
        UPDATE pulse_events
        SET mapped_booth_id = :mapped_booth_id,
            mapped_ac_id    = :mapped_ac_id,
            geo_level       = :geo_level,
            geo_confidence  = :geo_confidence
        WHERE id::text = :event_id
    """)

    updated = 0
    with engine.begin() as conn:
        for start in range(0, len(updates), BATCH_SIZE):
            batch = updates[start:start + BATCH_SIZE]
            conn.execute(stmt, batch)
            updated += len(batch)

    logger.info(
        "Geo-resolution done: %d events updated — %d booth-assigned, %d AC-level",
        updated, counts["booth_assigned"], counts["ac_level"],
    )
    return {"scanned": len(rows), "updated": updated, **counts}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    eng = sa.create_engine(os.environ["POSTGRES_URL"])
    result = run(eng, dry_run=args.dry_run)
    print("Result:", result)
