"""
Neo4j loader — PulseEvent nodes

Reads pulse_events from Postgres (post-NLP) and creates:
  (:PulseEvent)-[:AT_BOOTH]->(:Booth)      when mapped_booth_id is set (genuine geo)
  (:PulseEvent)-[:AT_AC]->(:AssemblyConstituency)  for AC-level events
  (:PulseEvent)-[:MENTIONS_PARTY]->(:Party)
  (:PulseEvent)-[:TAGGED_ISSUE]->(:Issue)

Requires Booth, Party, Issue, AssemblyConstituency nodes to exist.
Uses a 10-year window so historical pulse data is included.

Run: python -m graph.loaders.load_pulse_events
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from neo4j import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

LOAD_WINDOW_DAYS = 3650  # 10 years — include all historical pulse events
BATCH_SIZE = 200


def load_pulse_events(pg_engine: sa.Engine, session: Session) -> dict[str, int]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOAD_WINDOW_DAYS)

    with pg_engine.connect() as conn:
        rows = (
            conn.execute(
                text("""
            SELECT id::text       AS event_id,
                   source_type,
                   source_id,
                   text_raw,
                   language_detected,
                   entity,
                   entity_type,
                   final_issue     AS issue,
                   final_polarity,
                   final_confidence,
                   source_weight,
                   mapped_booth_id,
                   mapped_ac_id,
                   geo_level,
                   geo_confidence,
                   created_at
            FROM pulse_events
            WHERE created_at >= :cutoff
              AND mapped_ac_id IS NOT NULL
            ORDER BY created_at DESC
        """),
                {"cutoff": cutoff},
            )
            .mappings()
            .fetchall()
        )

    if not rows:
        logger.info("No pulse events to load (window=%d days)", LOAD_WINDOW_DAYS)
        return {"booth_linked": 0, "ac_linked": 0}

    booth_rows = [r for r in rows if r["mapped_booth_id"]]
    ac_rows = [r for r in rows if not r["mapped_booth_id"] and r["mapped_ac_id"]]

    logger.info(
        "Loading %d PulseEvent nodes: %d booth-linked, %d AC-level",
        len(rows),
        len(booth_rows),
        len(ac_rows),
    )

    def _to_params(r: dict) -> dict:
        return {
            "event_id": r["event_id"],
            "source_type": r["source_type"] or "",
            "source_id": r["source_id"] or "",
            "text_raw": (r["text_raw"] or "")[:500],
            "language": r["language_detected"] or "unknown",
            "entity": r["entity"] or "",
            "entity_type": r["entity_type"] or "",
            "issue": r["issue"] or "",
            "polarity": int(r["final_polarity"] or 0),
            "confidence": float(r["final_confidence"] or 0),
            "source_weight": float(r["source_weight"] or 0.6),
            "booth_id": r["mapped_booth_id"] or "",
            "ac_id": r["mapped_ac_id"] or "",
            "geo_level": r["geo_level"] or "ac",
            "geo_confidence": float(r["geo_confidence"] or 0.0),
            "published_at": r["created_at"].strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    # ── 1. Booth-linked events ──────────────────────────────────────────────
    for i in range(0, len(booth_rows), BATCH_SIZE):
        batch = [_to_params(dict(r)) for r in booth_rows[i : i + BATCH_SIZE]]

        session.run(
            """
            UNWIND $rows AS r
            MERGE (pe:PulseEvent {event_id: r.event_id})
            SET pe.source_type    = r.source_type,
                pe.text_raw       = r.text_raw,
                pe.language       = r.language,
                pe.polarity       = r.polarity,
                pe.confidence     = r.confidence,
                pe.source_weight  = r.source_weight,
                pe.entity         = r.entity,
                pe.issue          = r.issue,
                pe.geo_level      = r.geo_level,
                pe.geo_confidence = r.geo_confidence,
                pe.published_at   = datetime(r.published_at)
            WITH pe, r
            MATCH (b:Booth {booth_id: r.booth_id})
            MERGE (pe)-[:AT_BOOTH]->(b)
        """,
            {"rows": batch},
        )

    # ── 2. AC-level events (no booth attribution) ───────────────────────────
    for i in range(0, len(ac_rows), BATCH_SIZE):
        batch = [_to_params(dict(r)) for r in ac_rows[i : i + BATCH_SIZE]]

        session.run(
            """
            UNWIND $rows AS r
            MERGE (pe:PulseEvent {event_id: r.event_id})
            SET pe.source_type    = r.source_type,
                pe.text_raw       = r.text_raw,
                pe.language       = r.language,
                pe.polarity       = r.polarity,
                pe.confidence     = r.confidence,
                pe.source_weight  = r.source_weight,
                pe.entity         = r.entity,
                pe.issue          = r.issue,
                pe.geo_level      = 'ac',
                pe.geo_confidence = r.geo_confidence,
                pe.published_at   = datetime(r.published_at)
            WITH pe, r
            MATCH (a:AssemblyConstituency {ac_id: r.ac_id})
            MERGE (pe)-[:AT_AC]->(a)
        """,
            {"rows": batch},
        )

    # ── 3. Party + Issue wiring (all events) ────────────────────────────────
    all_params = [_to_params(dict(r)) for r in rows]

    party_rows = [r for r in all_params if r["entity_type"] == "party" and r["entity"]]
    if party_rows:
        for i in range(0, len(party_rows), BATCH_SIZE):
            session.run(
                """
                UNWIND $rows AS r
                MATCH (pe:PulseEvent {event_id: r.event_id})
                OPTIONAL MATCH (p1:Party {party_id: r.entity})
                OPTIONAL MATCH (p2:Party {name: r.entity})
                WITH pe, coalesce(p1, p2) AS p
                WHERE p IS NOT NULL
                MERGE (pe)-[:MENTIONS_PARTY]->(p)
            """,
                {"rows": party_rows[i : i + BATCH_SIZE]},
            )

    issue_rows = [r for r in all_params if r["issue"]]
    if issue_rows:
        for i in range(0, len(issue_rows), BATCH_SIZE):
            session.run(
                """
                UNWIND $rows AS r
                MATCH (pe:PulseEvent {event_id: r.event_id})
                MERGE (i:Issue {code: r.issue})
                MERGE (pe)-[:TAGGED_ISSUE]->(i)
            """,
                {"rows": issue_rows[i : i + BATCH_SIZE]},
            )

    logger.info(
        "PulseEvent load done — %d booth-linked, %d AC-level",
        len(booth_rows),
        len(ac_rows),
    )
    return {"booth_linked": len(booth_rows), "ac_linked": len(ac_rows)}


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from backend.db import get_neo4j_session, get_pg_engine

    pg = get_pg_engine()
    with get_neo4j_session() as s:
        result = load_pulse_events(pg, s)
        print("Done:", result)
