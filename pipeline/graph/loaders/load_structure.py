"""
Neo4j loader — Geographic hierarchy + Booth nodes

Reads ac_master + booth_master from Postgres and creates:
  (:State)-[:HAS_DISTRICT]->(:District)-[:HAS_AC]->(:AssemblyConstituency)-[:HAS_BOOTH]->(:Booth)

Also seeds Issue nodes from the issues table (or seed list).

Constraints required (run graph/constraints.cypher first):
  CREATE CONSTRAINT IF NOT EXISTS FOR (s:State)  REQUIRE s.state_id IS UNIQUE;
  CREATE CONSTRAINT IF NOT EXISTS FOR (d:District) REQUIRE d.district_id IS UNIQUE;
  CREATE CONSTRAINT IF NOT EXISTS FOR (ac:AssemblyConstituency) REQUIRE ac.ac_id IS UNIQUE;
  CREATE CONSTRAINT IF NOT EXISTS FOR (b:Booth)  REQUIRE b.booth_id IS UNIQUE;
  CREATE CONSTRAINT IF NOT EXISTS FOR (i:Issue)  REQUIRE i.code IS UNIQUE;

Run: python -m graph.loaders.load_structure
"""
from __future__ import annotations

import logging
import os

from neo4j import Session
import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)

ISSUE_SEEDS = [
    {"code": "water",       "label": "Water / Jal Jeevan",   "category": "infrastructure"},
    {"code": "roads",       "label": "Roads / Connectivity",  "category": "infrastructure"},
    {"code": "electricity", "label": "Power / Bijli",         "category": "infrastructure"},
    {"code": "jobs",        "label": "Employment / Rojgar",   "category": "economy"},
    {"code": "price_rise",  "label": "Inflation / Mehangai",  "category": "economy"},
    {"code": "farmer",      "label": "Farmer / Kisaan",       "category": "economy"},
    {"code": "women_safety","label": "Women Safety",          "category": "social"},
    {"code": "health",      "label": "Health / Swasthya",     "category": "social"},
    {"code": "education",   "label": "Education / Shiksha",   "category": "social"},
    {"code": "corruption",  "label": "Corruption / Bhrashtachar","category": "governance"},
    {"code": "law_order",   "label": "Law & Order",           "category": "governance"},
    {"code": "governance",  "label": "Panchayat Governance",  "category": "governance"},
    {"code": "housing",     "label": "Housing / PMAY",        "category": "infrastructure"},
]


def load_state_district(session: Session) -> None:
    session.run("""
        MERGE (s:State {state_id: 'UP'})
        SET s.name = 'Uttar Pradesh'
        MERGE (d:District {district_id: 'GKP'})
        SET d.name = 'Gorakhpur', d.state_id = 'UP'
        MERGE (s)-[:HAS_DISTRICT]->(d)
    """)
    logger.info("Merged State(UP) → District(GKP)")


def load_assembly_constituencies(pg_engine: sa.Engine, session: Session) -> int:
    with pg_engine.connect() as conn:
        rows = conn.execute(text("SELECT ac_id, ac_name, ac_type FROM ac_master")).mappings().fetchall()

    for r in rows:
        session.run("""
            MATCH (d:District {district_id: 'GKP'})
            MERGE (ac:AssemblyConstituency {ac_id: $ac_id})
            SET ac.name    = $ac_name,
                ac.ac_type = $ac_type,
                ac.district_id = 'GKP'
            MERGE (d)-[:HAS_AC]->(ac)
        """, {"ac_id": r["ac_id"], "ac_name": r["ac_name"], "ac_type": r["ac_type"]})

    logger.info("Merged %d AssemblyConstituency nodes", len(rows))
    return len(rows)


def load_booths(pg_engine: sa.Engine, session: Session) -> int:
    with pg_engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT booth_id, ac_id, booth_number, polling_station_name,
                   male_voters, female_voters, other_voters, total_voters,
                   census_total_pop, census_sc_pop, census_literate_pct
            FROM booth_master
        """)).mappings().fetchall()

    # Batch in groups of 500 for performance
    BATCH = 500
    loaded = 0
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i + BATCH]
        session.run("""
            UNWIND $rows AS r
            MATCH (ac:AssemblyConstituency {ac_id: r.ac_id})
            MERGE (b:Booth {booth_id: r.booth_id})
            SET b.booth_number   = r.booth_number,
                b.name           = r.polling_station_name,
                b.ac_id          = r.ac_id,
                b.total_voters   = r.total_voters,
                b.male_voters    = r.male_voters,
                b.female_voters  = r.female_voters,
                b.other_voters   = r.other_voters,
                b.census_total_pop   = r.census_total_pop,
                b.census_sc_pop      = r.census_sc_pop,
                b.census_literate_pct= r.census_literate_pct
            MERGE (ac)-[:HAS_BOOTH]->(b)
        """, {"rows": [dict(r) for r in batch]})
        loaded += len(batch)

    logger.info("Merged %d Booth nodes", loaded)
    return loaded


def load_issues(session: Session) -> int:
    for issue in ISSUE_SEEDS:
        session.run("""
            MERGE (i:Issue {code: $code})
            SET i.label    = $label,
                i.category = $category
        """, issue)
    logger.info("Seeded %d Issue nodes", len(ISSUE_SEEDS))
    return len(ISSUE_SEEDS)


def load_all(pg_engine: sa.Engine, session: Session) -> dict[str, int]:
    load_state_district(session)
    counts = {
        "acs":    load_assembly_constituencies(pg_engine, session),
        "booths": load_booths(pg_engine, session),
        "issues": load_issues(session),
    }
    logger.info("Structure load complete: %s", counts)
    return counts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from backend.db import get_pg_engine, get_neo4j_session
    pg = get_pg_engine()
    with get_neo4j_session() as s:
        load_all(pg, s)
