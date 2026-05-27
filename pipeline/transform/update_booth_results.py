import logging
import os

import pandas as pd
import sqlalchemy as sa
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def update_booth_results():
    engine = sa.create_engine(
        os.environ.get("POSTGRES_URL", "postgresql://postgres:postgres@localhost:5432/gorakhpur_db")
    )

    with engine.connect() as conn:
        logger.info("Fetching all booth results...")
        df = pd.read_sql(
            text("SELECT id, booth_id, election_year, party, votes FROM booth_results"), conn
        )

        if df.empty:
            logger.warning("No booth results found.")
            return

        logger.info("Calculating winner flags and vote shares...")
        # Calculate total votes per booth/year
        totals = df.groupby(["booth_id", "election_year"])["votes"].sum().reset_index()
        totals.rename(columns={"votes": "total_votes"}, inplace=True)

        df = df.merge(totals, on=["booth_id", "election_year"])
        df["vote_share"] = (df["votes"] / df["total_votes"]) * 100

        # Find max votes per booth/year
        max_votes = df.groupby(["booth_id", "election_year"])["votes"].transform(max)
        df["winner_flag"] = df["votes"] == max_votes

        # Note: If there's a tie, multiple winners will have True.

        logger.info(f"Updating {len(df)} rows in booth_results...")
        for i, row in df.iterrows():
            conn.execute(
                text("""
                UPDATE booth_results
                SET vote_share = :vs, winner_flag = :wf
                WHERE id = :id
            """),
                {"vs": float(row["vote_share"]), "wf": bool(row["winner_flag"]), "id": row["id"]},
            )

        conn.commit()
    logger.info("booth_results update complete.")


if __name__ == "__main__":
    update_booth_results()
