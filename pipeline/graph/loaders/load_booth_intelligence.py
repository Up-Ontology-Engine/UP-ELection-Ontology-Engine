"""
Neo4j loader — Enrich Booth nodes with intelligence from Postgres.

Sets properties directly on Booth nodes from:
  booth_metrics        → bjp_pulse_score, opp_pulse_score, digital_lean,
                         digital_lean_label, data_confidence
  conversion_opportunity → overall_conversion_score, recommended_action,
                           persuasion_room_score, beneficiary_density_score,
                           turnout_mobilization_score, service_risk_score

Run: python -m graph.loaders.load_booth_intelligence
"""

from __future__ import annotations

import logging

import sqlalchemy as sa
from neo4j import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


def load_booth_metrics(pg_engine: sa.Engine, session: Session) -> int:
    with pg_engine.connect() as conn:
        rows = (
            conn.execute(
                text("""
            SELECT DISTINCT ON (booth_id)
                booth_id, bjp_pulse_score, opp_pulse_score,
                digital_lean, digital_lean_label, data_confidence
            FROM booth_metrics
            ORDER BY booth_id, window_start DESC
        """)
            )
            .mappings()
            .fetchall()
        )

    count = 0
    BATCH = 500
    data = [dict(r) for r in rows]
    for i in range(0, len(data), BATCH):
        batch = data[i : i + BATCH]
        session.run(
            """
            UNWIND $rows AS r
            MATCH (b:Booth {booth_id: r.booth_id})
            SET b.bjp_pulse_score    = r.bjp_pulse_score,
                b.opp_pulse_score    = r.opp_pulse_score,
                b.digital_lean       = r.digital_lean,
                b.digital_lean_label = r.digital_lean_label,
                b.data_confidence    = r.data_confidence
        """,
            {"rows": batch},
        )
        count += len(batch)

    logger.info("Enriched %d Booth nodes with election metrics", count)
    return count


def load_conversion_scores(pg_engine: sa.Engine, session: Session) -> int:
    try:
        with pg_engine.connect() as conn:
            rows = (
                conn.execute(
                    text("""
                SELECT booth_id, overall_conversion_score, recommended_action,
                       persuasion_room_score, beneficiary_density_score,
                       turnout_mobilization_score, service_risk_score
                FROM conversion_opportunity
            """)
                )
                .mappings()
                .fetchall()
            )
    except Exception:
        logger.warning("conversion_opportunity table not found — skipping conversion scores")
        return 0

    count = 0
    BATCH = 500
    data = [dict(r) for r in rows]
    for i in range(0, len(data), BATCH):
        batch = data[i : i + BATCH]
        session.run(
            """
            UNWIND $rows AS r
            MATCH (b:Booth {booth_id: r.booth_id})
            SET b.overall_conversion_score     = r.overall_conversion_score,
                b.recommended_action           = r.recommended_action,
                b.persuasion_room_score        = r.persuasion_room_score,
                b.beneficiary_density_score    = r.beneficiary_density_score,
                b.turnout_mobilization_score   = r.turnout_mobilization_score,
                b.service_risk_score           = r.service_risk_score
        """,
            {"rows": batch},
        )
        count += len(batch)

    logger.info("Enriched %d Booth nodes with conversion scores", count)
    return count


def load_all(pg_engine: sa.Engine, session: Session) -> dict[str, int]:
    return {
        "booth_metrics": load_booth_metrics(pg_engine, session),
        "conversion_scores": load_conversion_scores(pg_engine, session),
    }


if __name__ == "__main__":
    import logging as _log

    _log.basicConfig(level=_log.INFO, format="%(levelname)s %(message)s")
    from dotenv import load_dotenv

    load_dotenv()
    from backend.db import get_neo4j_session, get_pg_engine

    pg = get_pg_engine()
    with get_neo4j_session() as s:
        print(load_all(pg, s))
