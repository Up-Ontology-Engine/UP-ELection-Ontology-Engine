"""
Neo4j loader — Election Results

Reads booth_results + candidate_master from Postgres and creates:
  (:Candidate)-[:CONTESTED_IN {votes, vote_share, winner}]->(:AssemblyConstituency)
  (:Candidate)-[:WON_SEAT]->(:AssemblyConstituency)   (winner only)
  (:Party)-[:CONTESTED_AC]->(:AssemblyConstituency)
  (:AssemblyConstituency)-[:HAD_TURNOUT {total_votes, turnout_pct}]->()  (on the AC node)

AC-level totals are stored as properties on AssemblyConstituency nodes.
Booth-level Form-20 data (if available) creates Booth-level result edges.

Run: python -m graph.loaders.load_results
"""
from __future__ import annotations

import logging
from collections import defaultdict

from neo4j import Session
import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)


def load_ac_results(pg_engine: sa.Engine, session: Session) -> int:
    """
    Load AC-level candidate results.
    Creates CONTESTED_IN edges and WON_SEAT edges from Candidate → AC.
    """
    with pg_engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                br.candidate_id,
                br.booth_id,
                br.election_year,
                br.party,
                br.votes,
                br.vote_share,
                br.winner_flag,
                cm.name        AS candidate_name,
                cm.ac_id
            FROM booth_results br
            JOIN candidate_master cm ON cm.candidate_id = br.candidate_id
            WHERE br.booth_id LIKE '%_TOTAL'   -- AC-level aggregates only
            ORDER BY br.election_year, cm.ac_id, br.votes DESC
        """)).mappings().fetchall()

    if not rows:
        logger.warning("No AC-level election results found in booth_results")
        return 0

    # Group by AC to get total votes for turnout
    ac_totals: dict[str, dict] = defaultdict(lambda: {"total_votes": 0, "year": 0})
    for r in rows:
        key = (r["ac_id"], r["election_year"])
        ac_totals[key]["total_votes"] += r["votes"] or 0
        ac_totals[key]["year"] = r["election_year"]

    loaded = 0
    BATCH = 200
    row_dicts = [dict(r) for r in rows]

    for i in range(0, len(row_dicts), BATCH):
        batch = row_dicts[i:i + BATCH]
        session.run("""
            UNWIND $rows AS r
            MATCH (ac:AssemblyConstituency {ac_id: r.ac_id})
            MERGE (c:Candidate {candidate_id: r.candidate_id})
            SET c.name = r.candidate_name
            MERGE (p:Party {party_id: r.party})
            MERGE (c)-[:BELONGS_TO]->(p)
            MERGE (c)-[cr:CONTESTED_IN {election_year: r.election_year}]->(ac)
            SET cr.votes      = r.votes,
                cr.vote_share = r.vote_share,
                cr.winner     = r.winner_flag,
                cr.party      = r.party
        """, {"rows": batch})
        loaded += len(batch)

    # WON_SEAT edges for winners
    winners = [r for r in row_dicts if r.get("winner_flag")]
    if winners:
        session.run("""
            UNWIND $rows AS r
            MATCH (c:Candidate {candidate_id: r.candidate_id})
            MATCH (ac:AssemblyConstituency {ac_id: r.ac_id})
            MERGE (c)-[:WON_SEAT {election_year: r.election_year}]->(ac)
        """, {"rows": winners})

    # Store turnout totals on AssemblyConstituency nodes
    for (ac_id, year), totals in ac_totals.items():
        session.run("""
            MATCH (ac:AssemblyConstituency {ac_id: $ac_id})
            SET ac.total_votes_2022 = $total_votes
        """, {"ac_id": ac_id, "total_votes": totals["total_votes"]})

    logger.info("Loaded %d AC-level result edges (%d winners)", loaded, len(winners))
    return loaded


def load_booth_results(pg_engine: sa.Engine, session: Session) -> int:
    """
    Load booth-level Form-20 results (if available).
    Creates Booth-level VOTED edges showing per-booth party tallies.
    """
    with pg_engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                br.booth_id,
                br.election_year,
                br.party,
                br.candidate_id,
                br.votes,
                br.vote_share,
                br.winner_flag
            FROM booth_results br
            WHERE br.booth_id NOT LIKE '%_TOTAL'  -- real booths only
            ORDER BY br.booth_id, br.votes DESC
        """)).mappings().fetchall()

    if not rows:
        logger.info("No booth-level Form-20 results yet — skipping booth result edges")
        return 0

    loaded = 0
    BATCH = 500
    row_dicts = [dict(r) for r in rows]

    for i in range(0, len(row_dicts), BATCH):
        batch = row_dicts[i:i + BATCH]
        session.run("""
            UNWIND $rows AS r
            MATCH (b:Booth {booth_id: r.booth_id})
            MERGE (p:Party {party_id: r.party})
            MERGE (p)-[rv:RECEIVED_VOTES_AT {election_year: r.election_year}]->(b)
            SET rv.votes      = r.votes,
                rv.vote_share = r.vote_share,
                rv.winner     = r.winner_flag
        """, {"rows": batch})
        loaded += len(batch)

    logger.info("Loaded %d booth-level result edges", loaded)
    return loaded


def load_all(pg_engine: sa.Engine, session: Session) -> dict[str, int]:
    return {
        "ac_results":    load_ac_results(pg_engine, session),
        "booth_results": load_booth_results(pg_engine, session),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from dotenv import load_dotenv
    load_dotenv()
    from api.db import get_pg_engine, get_neo4j_session
    pg = get_pg_engine()
    with get_neo4j_session() as s:
        load_all(pg, s)
