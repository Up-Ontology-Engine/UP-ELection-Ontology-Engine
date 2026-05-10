"""
Neo4j loader — PulseEvent nodes

Reads pulse_events from Postgres (post-NLP) and creates:
  (:PulseEvent)-[:AT_BOOTH]->(:Booth)
  (:PulseEvent)-[:MENTIONS_PARTY]->(:Party)
  (:PulseEvent)-[:TAGGED_ISSUE]->(:Issue)

Requires Booth, Party, Issue nodes to exist.
Only loads events from the last LOAD_WINDOW_DAYS to avoid stale node explosion.

Run: python -m graph.loaders.load_pulse_events
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone

from neo4j import Session
import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)

LOAD_WINDOW_DAYS = 7   # load last 7 days of pulse events
BATCH_SIZE       = 200


def load_pulse_events(pg_engine: sa.Engine, session: Session) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOAD_WINDOW_DAYS)

    with pg_engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id::text       AS event_id,
                   source_type,
                   source_id,
                   text_raw,
                   language_detected,
                   entity,
                   entity_type,
                   issue,
                   final_polarity,
                   final_confidence,
                   source_weight,
                   mapped_booth_id,
                   mapped_ac_id,
                   created_at
            FROM pulse_events
            WHERE created_at >= :cutoff
              AND mapped_booth_id IS NOT NULL
            ORDER BY created_at DESC
        """), {"cutoff": cutoff}).mappings().fetchall()

    if not rows:
        logger.info("No new pulse events to load (window=%d days)", LOAD_WINDOW_DAYS)
        return 0

    loaded = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = [
            {
                "event_id":       r["event_id"],
                "source_type":    r["source_type"],
                "source_id":      r["source_id"],
                "text_raw":       (r["text_raw"] or "")[:500],  # cap length
                "language":       r["language_detected"] or "unknown",
                "entity":         r["entity"] or "",
                "entity_type":    r["entity_type"] or "",
                "issue":          r["issue"] or "",
                "polarity":       int(r["final_polarity"] or 0),
                "confidence":     float(r["final_confidence"] or 0),
                "source_weight":  float(r["source_weight"] or 0.6),
                "booth_id":       r["mapped_booth_id"],
                "ac_id":          r["mapped_ac_id"] or "",
                "published_at":   r["created_at"].strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            for r in rows[i:i + BATCH_SIZE]
        ]

        # Create PulseEvent nodes + AT_BOOTH edge
        session.run("""
            UNWIND $rows AS r
            MERGE (pe:PulseEvent {event_id: r.event_id})
            SET pe.source_type   = r.source_type,
                pe.text_raw      = r.text_raw,
                pe.language      = r.language,
                pe.polarity      = r.polarity,
                pe.confidence    = r.confidence,
                pe.source_weight = r.source_weight,
                pe.entity        = r.entity,
                pe.issue         = r.issue,
                pe.published_at  = datetime(r.published_at)
            WITH pe, r
            MATCH (b:Booth {booth_id: r.booth_id})
            MERGE (pe)-[:AT_BOOTH]->(b)
        """, {"rows": batch})

        # Wire to Party if entity_type = party
        party_rows = [r for r in batch if r["entity_type"] == "party" and r["entity"]]
        if party_rows:
            session.run("""
                UNWIND $rows AS r
                MATCH (pe:PulseEvent {event_id: r.event_id})
                MATCH (p:Party {party_id: r.entity})
                MERGE (pe)-[:MENTIONS_PARTY]->(p)
            """, {"rows": party_rows})

        # Wire to Issue
        issue_rows = [r for r in batch if r["issue"]]
        if issue_rows:
            session.run("""
                UNWIND $rows AS r
                MATCH (pe:PulseEvent {event_id: r.event_id})
                MERGE (i:Issue {code: r.issue})
                MERGE (pe)-[:TAGGED_ISSUE]->(i)
            """, {"rows": issue_rows})

        loaded += len(batch)

    logger.info("Loaded %d PulseEvent nodes (window=%d days)", loaded, LOAD_WINDOW_DAYS)
    return loaded


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from api.db import get_pg_engine, get_neo4j_session
    pg = get_pg_engine()
    with get_neo4j_session() as s:
        print(load_pulse_events(pg, s))
