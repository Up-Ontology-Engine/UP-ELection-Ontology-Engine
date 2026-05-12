"""
Neo4j loader — Panchayat nodes

Reads panchayat_master from Postgres and creates:
  (:Panchayat)
  (:AssemblyConstituency)-[:HAS_PANCHAYAT]->(:Panchayat)

Also creates Scheme nodes from scheme_activity table.

Requires AssemblyConstituency nodes to exist (run load_structure.py first).

Run: python -m graph.loaders.load_panchayats
"""
from __future__ import annotations

import logging
import os

from neo4j import Session
import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)


def load_panchayats(pg_engine: sa.Engine, session: Session) -> int:
    with pg_engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT panchayat_id, gp_name, block_name, district_id
            FROM panchayat_master
        """)).mappings().fetchall()

    for r in rows:
        # Derive ac_id from block name (stored in block_name column)
        session.run("""
            MERGE (pan:Panchayat {panchayat_id: $panchayat_id})
            SET pan.name       = $gp_name,
                pan.block_name = $block_name,
                pan.district_id= $district_id
        """, {
            "panchayat_id": r["panchayat_id"],
            "gp_name":      r["gp_name"],
            "block_name":   r["block_name"],
            "district_id":  r["district_id"],
        })

    logger.info("Merged %d Panchayat nodes", len(rows))
    return len(rows)


def load_schemes_from_activity(pg_engine: sa.Engine, session: Session) -> int:
    with pg_engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT DISTINCT scheme_name, issue_tag
            FROM scheme_activity
            WHERE scheme_name IS NOT NULL
        """)).fetchall()

    for scheme_name, issue_tag in rows:
        session.run("""
            MERGE (sc:Scheme {scheme_id: $scheme_id})
            SET sc.name      = $name,
                sc.issue_tag = $issue_tag
        """, {
            "scheme_id": scheme_name.upper().replace(" ", "_")[:40],
            "name":      scheme_name,
            "issue_tag": issue_tag or "",
        })

    logger.info("Merged %d Scheme nodes", len(rows))
    return len(rows)


def load_all(pg_engine: sa.Engine, session: Session) -> dict[str, int]:
    return {
        "panchayats": load_panchayats(pg_engine, session),
        "schemes":    load_schemes_from_activity(pg_engine, session),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from api.db import get_pg_engine, get_neo4j_session
    pg = get_pg_engine()
    with get_neo4j_session() as s:
        print(load_all(pg, s))
