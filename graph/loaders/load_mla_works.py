"""
Neo4j loader — MLA Work Done

Reads mla_work + candidate_master from Postgres and creates:
  (:Candidate)-[:DID_WORK]->(:WorkItem)-[:ADDRESSES]->(:Issue)
  (:WorkItem)-[:IN_AC]->(:AssemblyConstituency)

Work types:
  development → links to relevant Issue node if title contains issue keywords
  question    → tagged as governance
  bills       → tagged as governance
  scheme      → links to matching Issue node

Run: python -m graph.loaders.load_mla_works
"""
from __future__ import annotations

import logging

from neo4j import Session
import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Map keywords in work title/description → issue codes
WORK_ISSUE_MAP = {
    "water": "water", "jal": "water", "jeevan": "water",
    "road": "roads", "expressway": "roads", "sadak": "roads",
    "electricity": "electricity", "bijli": "electricity", "power": "electricity",
    "job": "jobs", "employ": "jobs", "rozgar": "jobs", "mgnrega": "jobs",
    "health": "health", "hospital": "health", "aiims": "health", "medical": "health",
    "education": "education", "school": "education", "college": "education",
    "housing": "housing", "awas": "housing", "pmay": "housing",
    "farmer": "farmer", "kisan": "farmer", "fertilizer": "farmer",
    "sanitation": "governance", "swachh": "governance",
    "corruption": "corruption",
    "women": "women_safety",
}


def _infer_issue(title: str, desc: str) -> str:
    combined = (title + " " + (desc or "")).lower()
    for keyword, issue in WORK_ISSUE_MAP.items():
        if keyword in combined:
            return issue
    return "governance"


def load_mla_work_nodes(pg_engine: sa.Engine, session: Session) -> int:
    with pg_engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                mw.id::TEXT        AS work_id,
                mw.candidate_id,
                mw.ac_id,
                mw.work_type,
                mw.title,
                mw.description,
                mw.session_year,
                cm.name            AS candidate_name,
                cm.party
            FROM mla_work mw
            LEFT JOIN candidate_master cm ON cm.candidate_id = mw.candidate_id
            ORDER BY mw.ac_id, mw.work_type
        """)).mappings().fetchall()

    if not rows:
        logger.info("No MLA work records in mla_work table yet")
        return 0

    # Enrich with issue inference
    row_dicts = []
    for r in rows:
        d = dict(r)
        d["issue_code"] = _infer_issue(d.get("title") or "", d.get("description") or "")
        row_dicts.append(d)

    loaded = 0
    BATCH = 200
    for i in range(0, len(row_dicts), BATCH):
        batch = row_dicts[i:i + BATCH]
        session.run("""
            UNWIND $rows AS r
            MERGE (c:Candidate {candidate_id: r.candidate_id})
            SET c.name = r.candidate_name
            MERGE (w:WorkItem {work_id: r.work_id})
            SET w.title        = r.title,
                w.description  = r.description,
                w.work_type    = r.work_type,
                w.session_year = r.session_year,
                w.ac_id        = r.ac_id
            MERGE (c)-[:DID_WORK]->(w)
            WITH w, r
            MATCH (ac:AssemblyConstituency {ac_id: r.ac_id})
            MERGE (w)-[:IN_AC]->(ac)
            WITH w, r
            MATCH (i:Issue {code: r.issue_code})
            MERGE (w)-[:ADDRESSES]->(i)
        """, {"rows": batch})
        loaded += len(batch)

    logger.info("Loaded %d WorkItem nodes + DID_WORK + ADDRESSES edges", loaded)
    return loaded


def load_candidate_work_summary(pg_engine: sa.Engine, session: Session) -> int:
    """
    Set summary properties on Candidate nodes: questions_count, bills_count,
    dev_works_count, attendance_pct.
    """
    with pg_engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT candidate_id, name, questions_count, bills_count,
                   dev_works_count, attendance_pct
            FROM candidate_master
            WHERE questions_count > 0 OR bills_count > 0 OR dev_works_count > 0
        """)).mappings().fetchall()

    if not rows:
        return 0

    session.run("""
        UNWIND $rows AS r
        MERGE (c:Candidate {candidate_id: r.candidate_id})
        SET c.questions_count = r.questions_count,
            c.bills_count     = r.bills_count,
            c.dev_works_count = r.dev_works_count,
            c.attendance_pct  = r.attendance_pct
    """, {"rows": [dict(r) for r in rows]})

    logger.info("Updated work summary on %d Candidate nodes", len(rows))
    return len(rows)


def load_all(pg_engine: sa.Engine, session: Session) -> dict[str, int]:
    return {
        "work_items": load_mla_work_nodes(pg_engine, session),
        "summaries":  load_candidate_work_summary(pg_engine, session),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from api.db import get_pg_engine, get_neo4j_session
    pg = get_pg_engine()
    with get_neo4j_session() as s:
        load_all(pg, s)
