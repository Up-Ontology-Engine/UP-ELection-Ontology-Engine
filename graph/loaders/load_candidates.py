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

from neo4j import Session
import sqlalchemy as sa
from sqlalchemy import text
from etl.constants import normalise_party

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
            "SELECT DISTINCT party FROM candidate_master "
            "WHERE party IS NOT NULL AND ac_id = 'GKP_322'"
        )).fetchall()

    parties = [normalise_party(r[0]) for r in rows]
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
    """
    Merge Candidate nodes with enriched summary properties (from affidavit + migration 007).
    Keeps election-specific metrics off the node — those live on ELECTION_RESULT relationships.
    """
    with pg_engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                cm.candidate_id, cm.name, cm.party, cm.ac_id, cm.election_year,
                cm.is_incumbent, cm.is_primary_opp, cm.net_worth_rs,
                cm.self_profession, cm.voter_enrolled_ac_name,
                ca.criminal_cases, ca.total_assets AS total_assets_rs
            FROM candidate_master cm
            LEFT JOIN candidate_affidavits ca USING (candidate_id)
            WHERE cm.ac_id = 'GKP_322'
        """)).mappings().fetchall()

    for r in rows:
        canonical_party = normalise_party(r["party"]) if r["party"] else "IND"
        session.run("""
            MERGE (c:Candidate {candidate_id: $candidate_id})
            SET c.name              = $name,
                c.party_id          = $party,
                c.election_year     = $election_year,
                c.is_incumbent      = $is_incumbent,
                c.is_primary_opp    = $is_primary_opp,
                c.criminal_case_count = $criminal_case_count,
                c.total_assets_rs   = $total_assets_rs,
                c.net_worth_rs      = $net_worth_rs,
                c.self_profession   = $self_profession,
                c.voter_enrolled_ac_name = $voter_enrolled_ac_name
            WITH c
            MATCH (p:Party {party_id: $party})
            MERGE (c)-[:REPRESENTS]->(p)
            WITH c
            OPTIONAL MATCH (ac:AssemblyConstituency {ac_id: $ac_id})
            FOREACH (_ IN CASE WHEN ac IS NOT NULL THEN [1] ELSE [] END |
                MERGE (c)-[:CONTESTED_IN]->(ac)
            )
        """, {
            "candidate_id":       r["candidate_id"],
            "name":               r["name"],
            "party":              canonical_party,
            "ac_id":              r["ac_id"],
            "election_year":      r["election_year"],
            "is_incumbent":       bool(r["is_incumbent"]),
            "is_primary_opp":     bool(r["is_primary_opp"]),
            "criminal_case_count": r["criminal_cases"] or 0,
            "total_assets_rs":    r["total_assets_rs"],
            "net_worth_rs":       r["net_worth_rs"],
            "self_profession":    r["self_profession"],
            "voter_enrolled_ac_name": r["voter_enrolled_ac_name"],
        })

    logger.info("Merged %d Candidate nodes", len(rows))
    return len(rows)


def load_election_results(pg_engine: sa.Engine, session: Session) -> int:
    """
    Create ELECTION_RESULT relationships from candidate_party_history.

    Election-specific metrics (votes, rank, margin) live on this relationship,
    not duplicated on the Candidate node — keeps nodes lightweight and queryable.

    Enables queries like:
      MATCH (c:Candidate)-[r:ELECTION_RESULT]->(ac:AssemblyConstituency {ac_id:'GKP_322'})
      RETURN c.name, r.vote_share_pct, r.rank ORDER BY r.rank
    """
    with pg_engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                cph.candidate_id, cph.election_year, cph.constituency AS ac_id,
                cph.votes_received  AS total_votes,
                cph.vote_share      AS vote_share_pct,
                cph.rank,
                cph.is_winner,
                cph.result_position_label,
                cph.victory_margin_votes,
                cph.results_source  AS result,
                cph.result_completeness_status,
                ced.total_election_expense_rs,
                ced.own_funds_rs,
                ced.party_funds_rs
            FROM candidate_party_history cph
            LEFT JOIN candidate_expense_detail ced
                ON ced.candidate_id = cph.candidate_id
               AND ced.election_year = cph.election_year
        """)).mappings().fetchall()

    count = 0
    for r in rows:
        session.run("""
            MATCH (c:Candidate {candidate_id: $candidate_id})
            MATCH (ac:AssemblyConstituency {ac_id: $ac_id})
            MERGE (c)-[rel:ELECTION_RESULT {year: $year, ac_id: $ac_id}]->(ac)
            SET rel.total_votes           = $total_votes,
                rel.vote_share_pct        = $vote_share_pct,
                rel.rank                  = $rank,
                rel.is_winner             = $is_winner,
                rel.result_position_label = $result_position_label,
                rel.victory_margin_votes  = $victory_margin_votes,
                rel.result                = $result,
                rel.result_completeness   = $result_completeness,
                rel.total_expense_rs      = $total_expense_rs,
                rel.own_funds_rs          = $own_funds_rs,
                rel.party_funds_rs        = $party_funds_rs
        """, {
            "candidate_id":          r["candidate_id"],
            "ac_id":                 r["ac_id"],
            "year":                  r["election_year"],
            "total_votes":           r["total_votes"],
            "vote_share_pct":        r["vote_share_pct"],
            "rank":                  r["rank"],
            "is_winner":             bool(r["is_winner"]) if r["is_winner"] is not None else False,
            "result_position_label": r["result_position_label"],
            "victory_margin_votes":  r["victory_margin_votes"],
            "result":                r["result"],
            "result_completeness":   r["result_completeness_status"],
            "total_expense_rs":      r["total_election_expense_rs"],
            "own_funds_rs":          r["own_funds_rs"],
            "party_funds_rs":        r["party_funds_rs"],
        })
        count += 1

    logger.info("Merged %d ELECTION_RESULT relationships", count)
    return count


def load_all(pg_engine: sa.Engine, session: Session) -> dict[str, int]:
    return {
        "parties":          load_parties(pg_engine, session),
        "candidates":       load_candidates(pg_engine, session),
        "election_results": load_election_results(pg_engine, session),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from dotenv import load_dotenv
    load_dotenv()
    from api.db import get_pg_engine, get_neo4j_session
    pg = get_pg_engine()
    with get_neo4j_session() as s:
        print(load_all(pg, s))
