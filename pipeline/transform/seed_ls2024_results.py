"""
Seed 2024 Lok Sabha PC 64 Gorakhpur results into candidate_party_history.

Source: ECI official results (confirmed)
  Winner:     Ravindra Shukla alias Ravi Kishan (BJP) — 5,85,834 votes, 50.75%
  Runner-up:  Kajal Nishad (SP)                       — 4,82,308 votes, 41.78%
  Margin:     1,03,526 votes
  Total valid votes: ~11,54,500

Remaining 10 candidates have no confirmed per-candidate ECI breakdown yet;
their rows are upserted with NULL votes so they can be updated later from ECI.

Fixes the constituency name from the stale "Gorakhpur (LS)" to canonical "GKP_LS64".

Run:
  python -m etl.seed_ls2024_results
"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv

load_dotenv()

import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)

ELECTION_YEAR = 2024
CONSTITUENCY = "GKP_LS64"
VALID_VOTES = 1_154_500  # approximate; update when ECI publishes final count
WINNER_VOTES = 585_834
RUNNER_UP_VOTES = 482_308
VICTORY_MARGIN = WINNER_VOTES - RUNNER_UP_VOTES  # 103,526

# Confirmed per-candidate vote data (ECI 2024, PC 64 Gorakhpur)
# candidate_id → (candidate_name, party_id, votes | None)
# None = exact count not yet confirmed; row is still upserted for FK completeness.
RESULTS: list[dict] = [
    {
        "candidate_id": "RAVINDRA_SHUKLA_ALIAS_RAVI_KISHAN_2024",
        "candidate_name": "RAVINDRA SHUKLA ALIAS RAVI KISHAN",
        "party_id": "BJP",
        "votes": 585_834,
        "rank": 1,
        "result": "won",
        "is_winner": True,
    },
    {
        "candidate_id": "KAJAL_NISHAD_2024",
        "candidate_name": "KAJAL NISHAD",
        "party_id": "SP",
        "votes": 482_308,
        "rank": 2,
        "result": "lost",
        "is_winner": False,
    },
    # Remaining 10 — votes unknown, inserted for FK completeness
    {
        "candidate_id": "JAVED_ASHRAF_ALIAS_JAVED_SIMNANI_2024",
        "candidate_name": "JAVED ASHRAF ALIAS JAVED SIMNANI",
        "party_id": "SP",
        "votes": None,
        "rank": None,
        "result": "lost",
        "is_winner": False,
    },
    {
        "candidate_id": "AMITA_BHARATI_2024",
        "candidate_name": "AMITA BHARATI",
        "party_id": "IND",
        "votes": None,
        "rank": None,
        "result": "lost",
        "is_winner": False,
    },
    {
        "candidate_id": "SUDHANSHU_2024",
        "candidate_name": "Sudhanshu",
        "party_id": "IND",
        "votes": None,
        "rank": None,
        "result": "lost",
        "is_winner": False,
    },
    {
        "candidate_id": "ANAND_KUMAR_YADAV_ALIAS_ANAND_KUMAR_FAUJI_2024",
        "candidate_name": "Anand Kumar Yadav Alias Anand Kumar Fauji",
        "party_id": "BHARATHEEYA JAWAN KI",
        "votes": None,
        "rank": None,
        "result": "lost",
        "is_winner": False,
    },
    {
        "candidate_id": "SONU_RAI_2024",
        "candidate_name": "Sonu Rai",
        "party_id": "MERA ADHIKAAR RASHTR",
        "votes": None,
        "rank": None,
        "result": "lost",
        "is_winner": False,
    },
    {
        "candidate_id": "SHIVSHANKAR_PRAJAPATI_2024",
        "candidate_name": "SHIVSHANKAR PRAJAPATI",
        "party_id": "BHAGIDARI PARTY(P)",
        "votes": None,
        "rank": None,
        "result": "lost",
        "is_winner": False,
    },
    {
        "candidate_id": "PINTU_SAHANI_2024",
        "candidate_name": "Pintu Sahani",
        "party_id": "IND",
        "votes": None,
        "rank": None,
        "result": "lost",
        "is_winner": False,
    },
    {
        "candidate_id": "NAFEES_AKHTAR_2024",
        "candidate_name": "Nafees Akhtar",
        "party_id": "IND",
        "votes": None,
        "rank": None,
        "result": "lost",
        "is_winner": False,
    },
    {
        "candidate_id": "ANKIT_SHAH_2024",
        "candidate_name": "Ankit Shah",
        "party_id": "BHARATIYA YUVA JAN E",
        "votes": None,
        "rank": None,
        "result": "lost",
        "is_winner": False,
    },
    {
        "candidate_id": "SHRIRAM_PRASAD_2024",
        "candidate_name": "Shriram Prasad",
        "party_id": "AL-HIND PARTY",
        "votes": None,
        "rank": None,
        "result": "lost",
        "is_winner": False,
    },
]


def _pos_label(rank: int | None, is_winner: bool) -> str:
    if is_winner:
        return "winner"
    if rank == 2:
        return "runner_up"
    return "other"


def seed(engine: sa.Engine) -> int:
    # Remove stale rows with wrong constituency name
    with engine.connect() as conn:
        deleted = conn.execute(
            text("""
            DELETE FROM candidate_party_history
            WHERE election_year = :yr AND constituency != :con
              AND candidate_id IN (
                  SELECT candidate_id FROM candidate_master WHERE ac_id = :ac
              )
        """),
            {"yr": ELECTION_YEAR, "con": CONSTITUENCY, "ac": "GKP_LS64"},
        ).rowcount
        conn.commit()
    if deleted:
        logger.info("Removed %d stale rows with wrong constituency name", deleted)

    with engine.connect() as conn:
        for row in RESULTS:
            votes = row["votes"]
            vote_share = round(votes / VALID_VOTES * 100, 4) if votes else None
            margin = VICTORY_MARGIN if row["is_winner"] else None
            gap = (WINNER_VOTES - votes) if (votes and not row["is_winner"]) else None

            conn.execute(
                text("""
                INSERT INTO candidate_party_history (
                    candidate_id, candidate_name, party_id,
                    election_year, constituency,
                    votes_received, vote_share, result, margin,
                    rank, is_winner, result_position_label,
                    vote_gap_vs_winner, victory_margin_votes, valid_votes_total,
                    results_source, source_results_url,
                    result_completeness_status
                )
                VALUES (
                    :cid, :name, :party,
                    :year, :con,
                    :votes, :share, :result, :margin,
                    :rank, :is_winner, :pos_label,
                    :gap, :vic_margin, :valid_total,
                    'eci_manual',
                    'https://www.myneta.info/LokSabha2024/index.php?action=show_candidates&constituency_id=520',
                    'winner_runnerup_only'
                )
                ON CONFLICT (candidate_id, election_year, constituency) DO UPDATE SET
                    votes_received       = COALESCE(EXCLUDED.votes_received, candidate_party_history.votes_received),
                    vote_share           = COALESCE(EXCLUDED.vote_share,     candidate_party_history.vote_share),
                    result               = EXCLUDED.result,
                    margin               = COALESCE(EXCLUDED.margin,         candidate_party_history.margin),
                    rank                 = COALESCE(EXCLUDED.rank,           candidate_party_history.rank),
                    is_winner            = EXCLUDED.is_winner,
                    result_position_label = EXCLUDED.result_position_label,
                    vote_gap_vs_winner   = COALESCE(EXCLUDED.vote_gap_vs_winner, candidate_party_history.vote_gap_vs_winner),
                    victory_margin_votes = COALESCE(EXCLUDED.victory_margin_votes, candidate_party_history.victory_margin_votes),
                    valid_votes_total    = COALESCE(EXCLUDED.valid_votes_total, candidate_party_history.valid_votes_total),
                    results_source       = EXCLUDED.results_source,
                    result_completeness_status = EXCLUDED.result_completeness_status
            """),
                {
                    "cid": row["candidate_id"],
                    "name": row["candidate_name"],
                    "party": row["party_id"],
                    "year": ELECTION_YEAR,
                    "con": CONSTITUENCY,
                    "votes": votes,
                    "share": vote_share,
                    "result": row["result"],
                    "margin": margin,
                    "rank": row["rank"],
                    "is_winner": row["is_winner"],
                    "pos_label": _pos_label(row["rank"], row["is_winner"]),
                    "gap": gap,
                    "vic_margin": VICTORY_MARGIN if row["is_winner"] else None,
                    "valid_total": VALID_VOTES,
                },
            )
        conn.commit()

    logger.info("Seeded %d LS 2024 result rows into candidate_party_history", len(RESULTS))
    return len(RESULTS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    engine = sa.create_engine(os.environ["POSTGRES_URL"])
    n = seed(engine)
    print(f"Done — {n} rows upserted")
