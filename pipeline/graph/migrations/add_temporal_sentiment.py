"""
Neo4j temporal sentiment migration — adds valid_from / valid_to / sentiment_trend
to existing HAS_NARRATIVE relationships and introduces SentimentSnapshot nodes.

Temporal model:
  (:Booth)-[:HAS_NARRATIVE {valid_from, valid_to, election_year, sentiment_trend}]->(:Narrative)
  (:Booth)-[:HAS_SENTIMENT_SNAPSHOT]->(:SentimentSnapshot {
      booth_id, snapshot_at, election_year,
      issue, entity, polarity, confidence, source_count
  })

SentimentSnapshot nodes capture a point-in-time reading so time-series queries
can show how booth sentiment evolved over weeks/months.

Run:
    python -m graph.migrations.add_temporal_sentiment [--dry-run]
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


# ── Cypher DDL ────────────────────────────────────────────────────────────────

# 1. Add temporal metadata to all existing HAS_NARRATIVE edges that lack it.
#    valid_from = computed_at of the target Narrative node (already stored).
#    valid_to   = NULL signals "still current".
_BACKFILL_HAS_NARRATIVE = """
MATCH (b:Booth)-[r:HAS_NARRATIVE]->(n:Narrative)
WHERE r.valid_from IS NULL
SET
    r.valid_from     = COALESCE(n.computed_at, datetime()),
    r.valid_to       = null,
    r.election_year  = COALESCE(n.election_year, 2022),
    r.sentiment_trend = []
RETURN count(r) AS updated
"""

# 2. Constraint for SentimentSnapshot uniqueness.
_SNAPSHOT_CONSTRAINT = """
CREATE CONSTRAINT unique_sentiment_snapshot IF NOT EXISTS
FOR (s:SentimentSnapshot)
REQUIRE (s.snapshot_id) IS UNIQUE
"""

# 3. Index for time-range queries on SentimentSnapshot.
_SNAPSHOT_INDEX = """
CREATE INDEX snapshot_booth_time IF NOT EXISTS
FOR (s:SentimentSnapshot)
ON (s.booth_id, s.snapshot_at)
"""

# 4. Index for HAS_NARRATIVE temporal filtering.
_NARRATIVE_EDGE_INDEX = """
CREATE INDEX narrative_valid_from IF NOT EXISTS
FOR ()-[r:HAS_NARRATIVE]-()
ON (r.valid_from)
"""


def _run_migration(session, dry_run: bool) -> dict:
    results = {}

    # Create constraints and indexes
    if not dry_run:
        for stmt, name in [
            (_SNAPSHOT_CONSTRAINT, "snapshot_constraint"),
            (_SNAPSHOT_INDEX, "snapshot_index"),
            (_NARRATIVE_EDGE_INDEX, "narrative_edge_index"),
        ]:
            try:
                session.run(stmt)
                logger.info("[temporal] ✓ %s", name)
                results[name] = "created"
            except Exception as exc:
                logger.warning("[temporal] %s already exists or skipped: %s", name, exc)
                results[name] = "skipped"

        # Backfill valid_from on existing HAS_NARRATIVE edges
        r = session.run(_BACKFILL_HAS_NARRATIVE).single()
        updated = int(r["updated"]) if r else 0
        logger.info("[temporal] Backfilled valid_from on %d HAS_NARRATIVE edges.", updated)
        results["edges_backfilled"] = updated
    else:
        logger.info(
            "[temporal] dry_run=True — would run: snapshot_constraint, snapshot_index, backfill"
        )
        results["dry_run"] = True

    return results


def ingest_sentiment_snapshots(
    pg_engine,
    neo4j_session,
    window_days: int = 30,
) -> int:
    """
    Read pulse_events from PostgreSQL grouped by booth+issue and create
    SentimentSnapshot nodes in Neo4j, providing a queryable time-series.

    Returns count of snapshots created.
    """
    import hashlib
    from datetime import timezone as tz

    from sqlalchemy import text

    cutoff = datetime.now(tz.utc) - timedelta(days=window_days)

    with pg_engine.connect() as conn:
        rows = (
            conn.execute(
                text("""
            SELECT
                mapped_booth_id                        AS booth_id,
                issue,
                entity,
                DATE_TRUNC('day', created_at)          AS snapshot_at,
                election_year,
                AVG(final_polarity)::numeric(4,3)      AS polarity,
                AVG(confidence)::numeric(4,3)          AS confidence,
                COUNT(*)                               AS source_count
            FROM pulse_events
            WHERE mapped_booth_id IS NOT NULL
              AND created_at >= :cutoff
            GROUP BY mapped_booth_id, issue, entity,
                     DATE_TRUNC('day', created_at), election_year
            ORDER BY snapshot_at DESC
        """),
                {"cutoff": cutoff},
            )
            .mappings()
            .fetchall()
        )

    count = 0
    for r in rows:
        # Stable unique ID for deduplication
        raw_id = f"{r['booth_id']}|{r['issue']}|{r['entity']}|{r['snapshot_at']}"
        snap_id = hashlib.sha256(raw_id.encode()).hexdigest()[:16]
        snap_at_str = r["snapshot_at"].strftime("%Y-%m-%dT%H:%M:%SZ") if r["snapshot_at"] else None
        if not snap_at_str:
            continue

        neo4j_session.run(
            """
            MATCH (b:Booth {booth_id: $booth_id})
            MERGE (ss:SentimentSnapshot {snapshot_id: $snap_id})
            SET
                ss.booth_id     = $booth_id,
                ss.issue        = $issue,
                ss.entity       = $entity,
                ss.snapshot_at  = datetime($snapshot_at),
                ss.election_year = $election_year,
                ss.polarity     = $polarity,
                ss.confidence   = $confidence,
                ss.source_count = $source_count
            MERGE (b)-[:HAS_SENTIMENT_SNAPSHOT]->(ss)
            """,
            {
                "booth_id": r["booth_id"],
                "snap_id": snap_id,
                "issue": r["issue"] or "other",
                "entity": r["entity"] or "",
                "snapshot_at": snap_at_str,
                "election_year": int(r["election_year"] or 2022),
                "polarity": float(r["polarity"] or 0),
                "confidence": float(r["confidence"] or 0),
                "source_count": int(r["source_count"] or 0),
            },
        )
        count += 1

    logger.info("[temporal] Created/merged %d SentimentSnapshot nodes.", count)

    # Update sentiment_trend arrays on HAS_NARRATIVE edges for the affected booths
    if count > 0:
        neo4j_session.run("""
            MATCH (b:Booth)-[r:HAS_NARRATIVE]->(n:Narrative)
            WHERE r.valid_from IS NOT NULL
            WITH b, r, n
            MATCH (b)-[:HAS_SENTIMENT_SNAPSHOT]->(ss:SentimentSnapshot)
            WHERE ss.snapshot_at >= r.valid_from
            WITH r, collect(ss.polarity) AS trend
            SET r.sentiment_trend = trend
        """)
        logger.info("[temporal] Updated sentiment_trend arrays on HAS_NARRATIVE edges.")

    return count


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Add temporal sentiment properties to Neo4j")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done without writing"
    )
    args = parser.parse_args()

    from backend.db import get_neo4j_session

    with get_neo4j_session() as session:
        result = _run_migration(session, dry_run=args.dry_run)

    import json

    print("\n=== Temporal Sentiment Migration Results ===")
    print(json.dumps(result, indent=2, default=str))
