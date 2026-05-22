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
import re
from collections import defaultdict

from neo4j import Session
import sqlalchemy as sa
from sqlalchemy import text
from etl.constants import normalise_party

_INVALID_PARTY   = re.compile(r"^(\d+\.?\d*|nan|none|n/a|n\.a\.?)$", re.I)
_SYMBOL_ONLY     = re.compile(r"^[^A-Za-z0-9]+$")


def _clean_party(raw: str) -> str | None:
    """Normalize raw party string to canonical id; return None to skip the row."""
    raw = raw.strip()
    if not raw or _INVALID_PARTY.match(raw) or _SYMBOL_ONLY.match(raw):
        return None
    # First attempt: direct normalization
    canonical = normalise_party(raw, fallback="")
    if canonical:
        return canonical
    # Second attempt: collapse spaces (handles OCR artifacts "B A S P" → "BASP")
    collapsed = raw.replace(" ", "")
    if collapsed != raw:
        canonical = normalise_party(collapsed, fallback="")
        if canonical:
            return canonical
    # Accept the raw value for real minor parties (cap at 30 chars)
    return raw[:30]

logger = logging.getLogger(__name__)


def load_ac_results(pg_engine: sa.Engine, session: Session) -> int:
    """
    Load AC-level candidate results for GKP_322 from candidate_party_history.
    Creates WON_SEAT edges for winners; ELECTION_RESULT rels are handled by
    load_candidates.load_election_results() — this function only adds WON_SEAT.
    """
    with pg_engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                cph.candidate_id,
                cph.election_year,
                cph.constituency    AS ac_id,
                cph.votes_received  AS votes,
                cph.vote_share,
                cph.is_winner       AS winner_flag,
                cph.valid_votes_total,
                cm.name             AS candidate_name
            FROM candidate_party_history cph
            JOIN candidate_master cm ON cm.candidate_id = cph.candidate_id
            WHERE cph.constituency = 'GKP_322'
              AND cph.votes_received IS NOT NULL
            ORDER BY cph.election_year, cph.votes_received DESC
        """)).mappings().fetchall()

    if not rows:
        logger.warning("No AC-level election results found in candidate_party_history for GKP_322")
        return 0

    row_dicts = [dict(r) for r in rows]

    # Store total-votes as a property on the AC node (per year)
    ac_totals: dict = defaultdict(int)
    for r in row_dicts:
        if r.get("valid_votes_total"):
            ac_totals[(r["ac_id"], r["election_year"])] = r["valid_votes_total"]

    for (ac_id, year), total in ac_totals.items():
        session.run("""
            MATCH (ac:AssemblyConstituency {ac_id: $ac_id})
            SET ac += $props
        """, {
            "ac_id": ac_id,
            "props": {f"total_votes_{year}": total},
        })

    # WON_SEAT edges for winners only
    winners = [r for r in row_dicts if r.get("winner_flag")]
    if winners:
        session.run("""
            UNWIND $rows AS r
            MATCH (c:Candidate {candidate_id: r.candidate_id})
            MATCH (ac:AssemblyConstituency {ac_id: r.ac_id})
            MERGE (c)-[:WON_SEAT {election_year: r.election_year}]->(ac)
        """, {"rows": winners})

    logger.info(
        "Loaded AC results for GKP_322: %d rows, %d WON_SEAT edges",
        len(row_dicts), len(winners),
    )
    return len(row_dicts)


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
            JOIN booth_master bm ON bm.booth_id = br.booth_id
            WHERE bm.ac_id = 'GKP_322'
              AND br.booth_id NOT LIKE '%_TOTAL'
            ORDER BY br.booth_id, br.votes DESC
        """)).mappings().fetchall()

    if not rows:
        logger.info("No booth-level Form-20 results yet — skipping booth result edges")
        return 0

    # Normalize parties and drop rows with invalid/junk party values
    clean: list[dict] = []
    skipped = 0
    for r in rows:
        canonical = _clean_party(r["party"] or "")
        if canonical is None:
            skipped += 1
            continue
        d = dict(r)
        d["party"] = canonical
        clean.append(d)

    if skipped:
        logger.info("Skipped %d booth result rows with invalid/empty party values", skipped)

    loaded = 0
    BATCH = 500
    for i in range(0, len(clean), BATCH):
        batch = clean[i:i + BATCH]
        session.run("""
            UNWIND $rows AS r
            MATCH (b:Booth {booth_id: r.booth_id})
            MERGE (p:Party {party_id: r.party})
            ON CREATE SET p.name = r.party
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
