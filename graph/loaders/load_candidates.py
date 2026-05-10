"""
Neo4j loader — Candidate + Party nodes

Reads candidate_master from Postgres and creates:
  (:Candidate)-[:REPRESENTS]->(:Party)
  (:Candidate)-[:CONTESTED_IN]->(:AssemblyConstituency)

Requires AssemblyConstituency nodes to exist (run load_structure.py first).

Run: python -m graph.loaders.load_candidates
"""
from __future__ import annotations

import logging
import os

from neo4j import Session
import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)

PARTY_COLORS: dict[str, str] = {
    "BJP":      "#FF9933",
    "SP":       "#FF0000",
    "BSP":      "#0000FF",
    "INC":      "#00BFFF",
    "CONGRESS": "#00BFFF",
    "AAP":      "#0040C0",
    "AIMIM":    "#006400",
}


def load_parties(pg_engine: sa.Engine, session: Session) -> int:
    with pg_engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT DISTINCT party FROM candidate_master WHERE party IS NOT NULL"
        )).fetchall()

    parties = [r[0] for r in rows]
    for p in parties:
        session.run("""
            MERGE (party:Party {party_id: $party_id})
            SET party.name  = $party_id,
                party.color = $color
        """, {
            "party_id": p,
            "color":    PARTY_COLORS.get(p, "#888888"),
        })

    logger.info("Merged %d Party nodes", len(parties))
    return len(parties)


def load_candidates(pg_engine: sa.Engine, session: Session) -> int:
    with pg_engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT candidate_id, name, party, ac_id, election_year,
                   is_incumbent, is_primary_opp
            FROM candidate_master
        """)).mappings().fetchall()

    for r in rows:
        session.run("""
            MERGE (c:Candidate {candidate_id: $candidate_id})
            SET c.name           = $name,
                c.party_id       = $party,
                c.election_year  = $election_year,
                c.is_incumbent   = $is_incumbent,
                c.is_primary_opp = $is_primary_opp
            WITH c
            MATCH (p:Party {party_id: $party})
            MERGE (c)-[:REPRESENTS]->(p)
            WITH c
            OPTIONAL MATCH (ac:AssemblyConstituency {ac_id: $ac_id})
            FOREACH (_ IN CASE WHEN ac IS NOT NULL THEN [1] ELSE [] END |
                MERGE (c)-[:CONTESTED_IN]->(ac)
            )
        """, {
            "candidate_id": r["candidate_id"],
            "name":         r["name"],
            "party":        r["party"],
            "ac_id":        r["ac_id"],
            "election_year":r["election_year"],
            "is_incumbent": bool(r["is_incumbent"]),
            "is_primary_opp": bool(r["is_primary_opp"]),
        })

    logger.info("Merged %d Candidate nodes", len(rows))
    return len(rows)


def load_all(pg_engine: sa.Engine, session: Session) -> dict[str, int]:
    return {
        "parties":    load_parties(pg_engine, session),
        "candidates": load_candidates(pg_engine, session),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from api.db import get_pg_engine, get_neo4j_session
    pg = get_pg_engine()
    with get_neo4j_session() as s:
        print(load_all(pg, s))
