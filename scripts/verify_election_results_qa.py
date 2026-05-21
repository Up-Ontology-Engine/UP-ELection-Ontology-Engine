"""
QA Verification Script for UP Election Ontology Engine results.

Audits:
1. Winner Uniqueness: Maximum of one winner per election-constituency.
2. Monotonic Vote/Rank Ordering: Candidates ordered descending by votes, rank matches votes.
3. Completeness Null Policy:
   - For 'complete' status: all candidates must have non-null votes and ranks.
   - For 'winner_runnerup_only' status: ranks 1 & 2 must have non-null votes, ranks > 2 must be null.
"""
from __future__ import annotations

import logging
import os
import sys
from dotenv import load_dotenv
load_dotenv()

import sqlalchemy as sa
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("results_qa")


def get_engine() -> sa.Engine:
    url = os.environ.get("POSTGRES_URL")
    if not url:
        logger.error("POSTGRES_URL environment variable is missing!")
        sys.exit(1)
    return sa.create_engine(url)


def audit_winner_uniqueness(conn: sa.Connection) -> bool:
    """Verifies that no election-constituency combination has more than one winner."""
    logger.info("Auditing winner uniqueness...")
    query = text("""
        SELECT election_year, constituency, COUNT(*) as winner_count
        FROM candidate_party_history
        WHERE is_winner = TRUE
        GROUP BY election_year, constituency
        HAVING COUNT(*) > 1
    """)
    rows = conn.execute(query).fetchall()
    if rows:
        logger.error("Winner Uniqueness Violation Found!")
        for r in rows:
            logger.error(f"  Election {r.election_year}, AC/PC {r.constituency} has {r.winner_count} winners declared!")
        return False
    logger.info("✅ Winner Uniqueness audit passed (no duplicate winners).")
    return True


def audit_monotonic_ordering(conn: sa.Connection) -> bool:
    """Verifies that candidate ranks and vote counts are monotonically consistent."""
    logger.info("Auditing monotonic ordering and rank consistency...")
    query = text("""
        SELECT election_year, constituency, rank, candidate_name, votes_received
        FROM candidate_party_history
        WHERE votes_received IS NOT NULL
        ORDER BY election_year, constituency, rank ASC
    """)
    rows = conn.execute(query).fetchall()
    
    violations = 0
    # Group by election and constituency to verify monotonicity
    groups: dict[tuple[int, str], list[tuple[int, str, int]]] = {}
    for r in rows:
        key = (r.election_year, r.constituency)
        groups.setdefault(key, []).append((r.rank, r.candidate_name, r.votes_received))
        
    for key, candidates in groups.items():
        year, ac = key
        # Check ranks are ordered and vote counts are descending
        last_rank = 0
        last_votes = float('inf')
        for rank, name, votes in candidates:
            if rank is None or votes is None:
                continue
            if rank < last_rank:
                logger.error(f"  Violation in {year} {ac}: Rank went backward from {last_rank} to {rank} for {name}")
                violations += 1
            if votes > last_votes:
                logger.error(f"  Violation in {year} {ac}: Votes went upward from {last_votes} to {votes} for rank {rank} ({name})")
                violations += 1
            last_rank = rank
            last_votes = votes
            
    if violations > 0:
        return False
    logger.info("✅ Monotonic ordering audit passed (rank matches votes descending).")
    return True


def audit_completeness_null_policy(conn: sa.Connection) -> bool:
    """Verifies that completeness status column correctly governs null policies."""
    logger.info("Auditing null policy governed by completeness status...")
    query = text("""
        SELECT id, candidate_name, election_year, constituency, rank, votes_received, result_completeness_status
        FROM candidate_party_history
    """)
    rows = conn.execute(query).fetchall()
    
    violations = 0
    for r in rows:
        status = r.result_completeness_status
        rank = r.rank
        votes = r.votes_received
        name = r.candidate_name
        
        if status == 'complete':
            if votes is None or rank is None:
                logger.error(f"  Violation: {name} in {r.election_year} {r.constituency} marked 'complete' but has null votes/rank!")
                violations += 1
        elif status == 'winner_runnerup_only':
            if rank in [1, 2]:
                if votes is None:
                    logger.error(f"  Violation: Winner/Runner-up {name} in {r.election_year} {r.constituency} has null votes but marked 'winner_runnerup_only'!")
                    violations += 1
            else:
                if votes is not None:
                    logger.error(f"  Violation: Non-winner/runner-up {name} in {r.election_year} {r.constituency} has non-null votes ({votes}) but marked 'winner_runnerup_only'!")
                    violations += 1
        elif status == 'partial':
            # Partial status allows any combination of null/non-null votes/ranks.
            pass
        else:
            logger.error(f"  Violation: {name} has invalid completeness status '{status}'!")
            violations += 1
            
    if violations > 0:
        return False
    logger.info("✅ Null policy completeness audit passed.")
    return True


def main():
    engine = get_engine()
    success = True
    
    with engine.connect() as conn:
        if not audit_winner_uniqueness(conn):
            success = False
        if not audit_monotonic_ordering(conn):
            success = False
        if not audit_completeness_null_policy(conn):
            success = False
            
    if not success:
        logger.error("❌ QA Audit Failed with violations!")
        sys.exit(1)
    
    logger.info("🎉 All QA Audits Passed successfully!")
    sys.exit(0)


if __name__ == "__main__":
    main()
