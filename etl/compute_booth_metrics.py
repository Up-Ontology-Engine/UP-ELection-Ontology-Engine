import sqlalchemy as sa
from sqlalchemy import text
import os
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

def compute_metrics():
    engine = sa.create_engine(os.environ.get("POSTGRES_URL", "postgresql://postgres:postgres@localhost:5432/gorakhpur_db"))
    
    with engine.connect() as conn:
        # 1. Create table booth_election_metrics if it doesn't exist
        logger.info("Ensuring booth_election_metrics table exists...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS booth_election_metrics (
                booth_id TEXT PRIMARY KEY REFERENCES booth_master(booth_id),
                election_year INTEGER NOT NULL,
                winner_party TEXT,
                runner_up_party TEXT,
                winner_votes INTEGER,
                runner_up_votes INTEGER,
                margin_votes INTEGER,
                margin_pct NUMERIC,
                bjp_votes INTEGER DEFAULT 0,
                sp_votes INTEGER DEFAULT 0,
                bsp_votes INTEGER DEFAULT 0,
                inc_votes INTEGER DEFAULT 0,
                total_votes INTEGER,
                turnout_pct NUMERIC,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # 2. Get all booth results for 2022
        logger.info("Fetching 2022 booth results...")
        query = text("""
            SELECT booth_id, party, votes, election_year
            FROM booth_results
            WHERE election_year = 2022
        """)
        df = pd.read_sql(query, conn)
        
        if df.empty:
            logger.warning("No booth results found for 2022.")
            return
            
        # 3. Compute metrics per booth
        logger.info("Computing metrics per booth...")
        booths = df.groupby('booth_id')
        
        metrics_data = []
        for booth_id, group in booths:
            sorted_votes = group.sort_values('votes', ascending=False)
            total_votes = group['votes'].sum()
            
            if total_votes == 0:
                continue
                
            winner = sorted_votes.iloc[0]
            runner_up = sorted_votes.iloc[1] if len(sorted_votes) > 1 else None
            
            margin_votes = winner['votes'] - (runner_up['votes'] if runner_up is not None else 0)
            margin_pct = (margin_votes / total_votes) * 100
            
            party_votes = group.set_index('party')['votes'].to_dict()
            
            metrics_data.append({
                "booth_id": booth_id,
                "election_year": 2022,
                "winner_party": winner['party'],
                "runner_up_party": runner_up['party'] if runner_up is not None else None,
                "winner_votes": int(winner['votes']),
                "runner_up_votes": int(runner_up['votes']) if runner_up is not None else 0,
                "margin_votes": int(margin_votes),
                "margin_pct": float(margin_pct),
                "bjp_votes": int(party_votes.get('BJP', 0)),
                "sp_votes": int(party_votes.get('SP', 0)),
                "bsp_votes": int(party_votes.get('BSP', 0)),
                "inc_votes": int(party_votes.get('INC', 0)),
                "total_votes": int(total_votes)
            })
            
        # 4. Upsert metrics
        logger.info(f"Upserting metrics for {len(metrics_data)} booths...")
        for m in metrics_data:
            conn.execute(text("""
                INSERT INTO booth_election_metrics 
                    (booth_id, election_year, winner_party, runner_up_party, winner_votes, runner_up_votes, 
                     margin_votes, margin_pct, bjp_votes, sp_votes, bsp_votes, inc_votes, total_votes)
                VALUES 
                    (:booth_id, :election_year, :winner_party, :runner_up_party, :winner_votes, :runner_up_votes, 
                     :margin_votes, :margin_pct, :bjp_votes, :sp_votes, :bsp_votes, :inc_votes, :total_votes)
                ON CONFLICT (booth_id) DO UPDATE SET
                    election_year = EXCLUDED.election_year,
                    winner_party = EXCLUDED.winner_party,
                    runner_up_party = EXCLUDED.runner_up_party,
                    winner_votes = EXCLUDED.winner_votes,
                    runner_up_votes = EXCLUDED.runner_up_votes,
                    margin_votes = EXCLUDED.margin_votes,
                    margin_pct = EXCLUDED.margin_pct,
                    bjp_votes = EXCLUDED.bjp_votes,
                    sp_votes = EXCLUDED.sp_votes,
                    bsp_votes = EXCLUDED.bsp_votes,
                    inc_votes = EXCLUDED.inc_votes,
                    total_votes = EXCLUDED.total_votes,
                    updated_at = CURRENT_TIMESTAMP
            """), m)
            
        conn.commit()
    logger.info("Metrics computation complete.")

if __name__ == "__main__":
    compute_metrics()
