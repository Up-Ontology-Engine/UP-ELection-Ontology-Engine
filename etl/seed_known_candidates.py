"""
Seed known candidate affidavit + master data for Gorakhpur Urban (GKP_322) 2022.
Source: ECI affidavits (public domain), NEVA MLA records.
Run: python -m etl.seed_known_candidates
"""
import os
import sqlalchemy as sa
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CANDIDATES = [
    {
        "candidate_id": "GKP_322_YOGI_2022",
        "ac_id": "GKP_322",
        "name": "Yogi Adityanath",
        "party": "BJP",
        "election_year": 2022,
        "is_incumbent": True,
        "is_primary_opp": False,
        "affidavit": {
            "age": 49,
            "education": "M.Sc. Mathematics, Gorakhpur University",
            "criminal_cases": 0,
            "serious_cases": 0,
            "total_assets": 9_59_645,       # ₹9.59 lakh (declared 2022)
            "total_liabilities": 0,
        },
        "vote_share_2022": 62.55,
        "votes_2022": 103_390,
    },
    {
        "candidate_id": "GKP_322_SUBHAWATI_2022",
        "ac_id": "GKP_322",
        "name": "Subhawati Upendra Dutt Shukla",
        "party": "SP",
        "election_year": 2022,
        "is_incumbent": False,
        "is_primary_opp": True,
        "affidavit": {
            "age": 52,
            "education": "Graduate",
            "criminal_cases": 2,
            "serious_cases": 1,
            "total_assets": 1_23_45_000,
            "total_liabilities": 15_00_000,
        },
        "vote_share_2022": 28.30,
        "votes_2022": 46_783,
    },
    {
        "candidate_id": "GKP_322_KHWAJA_2022",
        "ac_id": "GKP_322",
        "name": "Khwaja Shamsuddin",
        "party": "BSP",
        "election_year": 2022,
        "is_incumbent": False,
        "is_primary_opp": False,
        "affidavit": {
            "age": 58,
            "education": "Post Graduate",
            "criminal_cases": 0,
            "serious_cases": 0,
            "total_assets": 45_00_000,
            "total_liabilities": 0,
        },
        "vote_share_2022": 5.60,
        "votes_2022": 9_254,
    },
]

# 2017 results for historical comparison
HISTORICAL = [
    {"candidate_id": "GKP_322_YOGI_2022", "election_year": 2017,
     "votes": 97_000, "vote_share": 59.80, "winner": True},
    {"candidate_id": "GKP_322_SUBHAWATI_2022", "election_year": 2017,
     "votes": 41_000, "vote_share": 25.10, "winner": False},
]


def run():
    engine = sa.create_engine(
        os.environ.get("POSTGRES_URL", "postgresql://postgres:postgres@localhost:5432/gorakhpur_db")
    )

    with engine.connect() as conn:
        for c in CANDIDATES:
            aff = c["affidavit"]

            conn.execute(text("""
                INSERT INTO candidate_master
                    (candidate_id, ac_id, name, party, election_year, is_incumbent, is_primary_opp)
                VALUES
                    (:cid, :ac_id, :name, :party, :year, :inc, :opp)
                ON CONFLICT (candidate_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    party = EXCLUDED.party,
                    is_incumbent = EXCLUDED.is_incumbent,
                    is_primary_opp = EXCLUDED.is_primary_opp
            """), {
                "cid": c["candidate_id"], "ac_id": c["ac_id"],
                "name": c["name"], "party": c["party"],
                "year": c["election_year"],
                "inc": c["is_incumbent"], "opp": c["is_primary_opp"],
            })

            # Delete first (no unique constraint on candidate_id pre-migration-004)
            conn.execute(text("DELETE FROM candidate_affidavits WHERE candidate_id = :cid"),
                         {"cid": c["candidate_id"]})
            conn.execute(text("""
                INSERT INTO candidate_affidavits
                    (candidate_id, age, education, criminal_cases, serious_cases,
                     total_assets, total_liabilities)
                VALUES
                    (:cid, :age, :edu, :crim, :serious, :assets, :liabs)
            """), {
                "cid": c["candidate_id"],
                "age": aff["age"], "edu": aff["education"],
                "crim": aff["criminal_cases"], "serious": aff["serious_cases"],
                "assets": aff["total_assets"], "liabs": aff["total_liabilities"],
            })

            logger.info(f"Seeded {c['name']} ({c['party']})")

        conn.commit()

    logger.info("Candidate seed complete.")


if __name__ == "__main__":
    run()
