"""
Neo4j loader — Intelligence layer nodes.

Reads the four intelligence tables from Postgres and creates / merges the
corresponding Neo4j nodes, then wires them to existing Booth, Scheme, Issue,
Party, and Candidate nodes.

Node relationships created:
  (:Booth)-[:HAS_QUALITY]->(:DataQuality)
  (:Booth)-[:HAS_NARRATIVE]->(:Narrative)-[:ABOUT_ISSUE]->(:Issue)
  (:Narrative)-[:INVOLVES_PARTY]->(:Party)
  (:Narrative)-[:INVOLVES_CANDIDATE]->(:Candidate)
  (:Booth)-[:HAS_SCHEME_GAP]->(:SchemeGap)-[:FOR_SCHEME]->(:Scheme)
  (:SchemeGap)-[:TAGGED_ISSUE]->(:Issue)
  (:Booth)-[:HAS_CONTRADICTION]->(:ContradictionFlag)-[:ABOUT_ENTITY]->(:Party|:Candidate)

Usage:
    python -m graph.loaders.load_quality_narratives
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from neo4j import Session
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# How far back to look when loading intelligence nodes.
# Set large for the initial bulk load; tighten for incremental refreshes.
LOAD_WINDOW_DAYS = 3650  # 10 years — loads all historical data on first run


# ── Helpers ───────────────────────────────────────────────────────────────────

def _neo4j_dt(dt: datetime) -> str:
    """Format datetime for Neo4j datetime() literal."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ── DataQuality nodes ─────────────────────────────────────────────────────────

def load_data_quality(pg_engine: Engine, neo4j_session: Session) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOAD_WINDOW_DAYS)

    with pg_engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT booth_id, computed_at, window_days,
                       total_events, unique_sources,
                       overall_quality_score, quality_label, quality_reasons,
                       source_diversity_score, avg_geo_confidence, avg_nlp_confidence
                FROM data_quality_metrics
                WHERE computed_at >= :cutoff
                ORDER BY computed_at DESC
            """),
            {"cutoff": cutoff},
        ).mappings().fetchall()

    for r in rows:
        reasons = r["quality_reasons"]
        if isinstance(reasons, str):
            reasons = json.loads(reasons)

        neo4j_session.run(
            """
            MATCH (b:Booth {booth_id: $booth_id})
            MERGE (dq:DataQuality {booth_id: $booth_id, computed_at: datetime($computed_at)})
            SET
                dq.window_days           = $window_days,
                dq.total_events          = $total_events,
                dq.unique_sources        = $unique_sources,
                dq.overall_quality_score = $overall_quality_score,
                dq.quality_label         = $quality_label,
                dq.quality_reasons       = $quality_reasons,
                dq.source_diversity      = $source_diversity_score,
                dq.avg_geo_confidence    = $avg_geo_confidence,
                dq.avg_nlp_confidence    = $avg_nlp_confidence
            MERGE (b)-[:HAS_QUALITY]->(dq)
            """,
            {
                "booth_id":             r["booth_id"],
                "computed_at":          _neo4j_dt(r["computed_at"]),
                "window_days":          r["window_days"],
                "total_events":         r["total_events"],
                "unique_sources":       r["unique_sources"],
                "overall_quality_score": float(r["overall_quality_score"] or 0),
                "quality_label":        r["quality_label"],
                "quality_reasons":      reasons,
                "source_diversity_score": float(r["source_diversity_score"] or 0),
                "avg_geo_confidence":   float(r["avg_geo_confidence"] or 0),
                "avg_nlp_confidence":   float(r["avg_nlp_confidence"] or 0),
            },
        )

    logger.info("Loaded %d DataQuality nodes.", len(rows))
    return len(rows)


# ── Narrative nodes ───────────────────────────────────────────────────────────

def load_narratives(pg_engine: Engine, neo4j_session: Session) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOAD_WINDOW_DAYS)

    with pg_engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT booth_id, computed_at, window_days,
                       narrative_type, strength, description,
                       top_issues, top_entities, evidence_count, confidence
                FROM booth_narratives
                WHERE computed_at >= :cutoff
                ORDER BY computed_at DESC
            """),
            {"cutoff": cutoff},
        ).mappings().fetchall()

    for r in rows:
        top_issues   = r["top_issues"]   if isinstance(r["top_issues"],   list) else json.loads(r["top_issues"]   or "[]")
        top_entities = r["top_entities"] if isinstance(r["top_entities"], list) else json.loads(r["top_entities"] or "[]")

        neo4j_session.run(
            """
            MATCH (b:Booth {booth_id: $booth_id})
            MERGE (n:Narrative {
                booth_id:       $booth_id,
                narrative_type: $narrative_type,
                computed_at:    datetime($computed_at)
            })
            SET
                n.window_days    = $window_days,
                n.strength       = $strength,
                n.description    = $description,
                n.top_issues     = $top_issues,
                n.top_entities   = $top_entities,
                n.evidence_count = $evidence_count,
                n.confidence     = $confidence
            MERGE (b)-[:HAS_NARRATIVE]->(n)
            """,
            {
                "booth_id":       r["booth_id"],
                "computed_at":    _neo4j_dt(r["computed_at"]),
                "window_days":    r["window_days"],
                "narrative_type": r["narrative_type"],
                "strength":       float(r["strength"] or 0),
                "description":    r["description"] or "",
                "top_issues":     top_issues,
                "top_entities":   top_entities,
                "evidence_count": r["evidence_count"],
                "confidence":     float(r["confidence"] or 0),
            },
        )

        # Wire Narrative → Issue
        for issue_code in top_issues:
            neo4j_session.run(
                """
                MATCH (n:Narrative {
                    booth_id: $booth_id,
                    narrative_type: $narrative_type,
                    computed_at: datetime($computed_at)
                })
                MERGE (i:Issue {code: $issue_code})
                MERGE (n)-[:ABOUT_ISSUE]->(i)
                """,
                {
                    "booth_id":       r["booth_id"],
                    "narrative_type": r["narrative_type"],
                    "computed_at":    _neo4j_dt(r["computed_at"]),
                    "issue_code":     issue_code,
                },
            )

        # Wire Narrative → Party (for entities that look like parties)
        for entity in top_entities:
            neo4j_session.run(
                """
                MATCH (n:Narrative {
                    booth_id: $booth_id,
                    narrative_type: $narrative_type,
                    computed_at: datetime($computed_at)
                })
                OPTIONAL MATCH (p:Party  {name: $entity})
                OPTIONAL MATCH (c:Candidate {name: $entity})
                FOREACH (_ IN CASE WHEN p IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (n)-[:INVOLVES_PARTY]->(p)
                )
                FOREACH (_ IN CASE WHEN c IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (n)-[:INVOLVES_CANDIDATE]->(c)
                )
                """,
                {
                    "booth_id":       r["booth_id"],
                    "narrative_type": r["narrative_type"],
                    "computed_at":    _neo4j_dt(r["computed_at"]),
                    "entity":         entity,
                },
            )

    logger.info("Loaded %d Narrative nodes.", len(rows))
    return len(rows)


# ── SchemeGap nodes ───────────────────────────────────────────────────────────

def load_scheme_gaps(pg_engine: Engine, neo4j_session: Session) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOAD_WINDOW_DAYS)

    with pg_engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT booth_id, panchayat_id, scheme_name, issue_tag, computed_at,
                       beneficiary_count, completion_status,
                       positive_events, negative_events, total_events, avg_sentiment,
                       gap_type, gap_label, priority
                FROM scheme_gap_analysis
                WHERE computed_at >= :cutoff
                ORDER BY computed_at DESC
            """),
            {"cutoff": cutoff},
        ).mappings().fetchall()

    for r in rows:
        neo4j_session.run(
            """
            MATCH (b:Booth {booth_id: $booth_id})
            MERGE (sg:SchemeGap {
                booth_id:    $booth_id,
                scheme_name: $scheme_name,
                computed_at: datetime($computed_at)
            })
            SET
                sg.panchayat_id       = $panchayat_id,
                sg.issue_tag          = $issue_tag,
                sg.beneficiary_count  = $beneficiary_count,
                sg.completion_status  = $completion_status,
                sg.positive_events    = $positive_events,
                sg.negative_events    = $negative_events,
                sg.total_events       = $total_events,
                sg.avg_sentiment      = $avg_sentiment,
                sg.gap_type           = $gap_type,
                sg.gap_label          = $gap_label,
                sg.priority           = $priority
            MERGE (b)-[:HAS_SCHEME_GAP]->(sg)
            WITH sg
            MERGE (sc:Scheme {name: $scheme_name})
            MERGE (sg)-[:FOR_SCHEME]->(sc)
            """,
            {
                "booth_id":          r["booth_id"],
                "computed_at":       _neo4j_dt(r["computed_at"]),
                "panchayat_id":      r["panchayat_id"],
                "scheme_name":       r["scheme_name"],
                "issue_tag":         r["issue_tag"] or "",
                "beneficiary_count": r["beneficiary_count"] or 0,
                "completion_status": r["completion_status"] or "",
                "positive_events":   r["positive_events"] or 0,
                "negative_events":   r["negative_events"] or 0,
                "total_events":      r["total_events"] or 0,
                "avg_sentiment":     float(r["avg_sentiment"] or 0),
                "gap_type":          r["gap_type"] or "",
                "gap_label":         r["gap_label"] or "",
                "priority":          r["priority"] or "LOW",
            },
        )

        # Wire SchemeGap → Issue
        if r["issue_tag"]:
            neo4j_session.run(
                """
                MATCH (sg:SchemeGap {
                    booth_id: $booth_id,
                    scheme_name: $scheme_name,
                    computed_at: datetime($computed_at)
                })
                MERGE (i:Issue {code: $issue_tag})
                MERGE (sg)-[:TAGGED_ISSUE]->(i)
                """,
                {
                    "booth_id":    r["booth_id"],
                    "scheme_name": r["scheme_name"],
                    "computed_at": _neo4j_dt(r["computed_at"]),
                    "issue_tag":   r["issue_tag"],
                },
            )

    logger.info("Loaded %d SchemeGap nodes.", len(rows))
    return len(rows)


# ── ContradictionFlag nodes ───────────────────────────────────────────────────

def load_contradiction_flags(pg_engine: Engine, neo4j_session: Session) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOAD_WINDOW_DAYS)

    with pg_engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT booth_id, entity, issue, computed_at, window_days,
                       source_a, source_b,
                       polarity_a, polarity_b, delta,
                       events_a, events_b,
                       consistency_score, flag_label
                FROM contradiction_flags
                WHERE computed_at >= :cutoff
                ORDER BY computed_at DESC
            """),
            {"cutoff": cutoff},
        ).mappings().fetchall()

    for r in rows:
        neo4j_session.run(
            """
            MATCH (b:Booth {booth_id: $booth_id})
            MERGE (cf:ContradictionFlag {
                booth_id:    $booth_id,
                entity:      $entity,
                source_a:    $source_a,
                source_b:    $source_b,
                computed_at: datetime($computed_at)
            })
            SET
                cf.issue             = $issue,
                cf.window_days       = $window_days,
                cf.polarity_a        = $polarity_a,
                cf.polarity_b        = $polarity_b,
                cf.delta             = $delta,
                cf.events_a          = $events_a,
                cf.events_b          = $events_b,
                cf.consistency_score = $consistency_score,
                cf.flag_label        = $flag_label
            MERGE (b)-[:HAS_CONTRADICTION]->(cf)
            WITH cf
            OPTIONAL MATCH (p:Party     {name: $entity})
            OPTIONAL MATCH (c:Candidate {name: $entity})
            FOREACH (_ IN CASE WHEN p IS NOT NULL THEN [1] ELSE [] END |
                MERGE (cf)-[:ABOUT_ENTITY]->(p)
            )
            FOREACH (_ IN CASE WHEN c IS NOT NULL THEN [1] ELSE [] END |
                MERGE (cf)-[:ABOUT_ENTITY]->(c)
            )
            """,
            {
                "booth_id":          r["booth_id"],
                "entity":            r["entity"],
                "issue":             r["issue"] or "",
                "computed_at":       _neo4j_dt(r["computed_at"]),
                "window_days":       r["window_days"] or 7,
                "source_a":          r["source_a"],
                "source_b":          r["source_b"],
                "polarity_a":        float(r["polarity_a"] or 0),
                "polarity_b":        float(r["polarity_b"] or 0),
                "delta":             float(r["delta"] or 0),
                "events_a":          r["events_a"] or 0,
                "events_b":          r["events_b"] or 0,
                "consistency_score": float(r["consistency_score"] or 0),
                "flag_label":        r["flag_label"] or "",
            },
        )

    logger.info("Loaded %d ContradictionFlag nodes.", len(rows))
    return len(rows)


# ── Orchestrator ──────────────────────────────────────────────────────────────

def load_all(pg_engine: Engine, neo4j_session: Session) -> dict[str, int]:
    counts = {
        "data_quality":        load_data_quality(pg_engine, neo4j_session),
        "narratives":          load_narratives(pg_engine, neo4j_session),
        "scheme_gaps":         load_scheme_gaps(pg_engine, neo4j_session),
        "contradiction_flags": load_contradiction_flags(pg_engine, neo4j_session),
    }
    logger.info("Intelligence layer loaded: %s", counts)
    return counts


if __name__ == "__main__":
    from dotenv import load_dotenv; load_dotenv()
    from api.db import get_pg_engine, get_neo4j_session
    pg  = get_pg_engine()
    with get_neo4j_session() as session:
        counts = load_all(pg, session)
    print("Loaded:", counts)
