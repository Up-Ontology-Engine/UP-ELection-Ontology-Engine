import pandas as pd
import sqlalchemy as sa
from sqlalchemy import text
import os
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

def ingest():
    engine = sa.create_engine(os.environ.get("POSTGRES_URL", "postgresql://postgres:postgres@localhost:5432/gorakhpur_db"))
    
    with engine.connect() as conn:
        # 1. Ensure AC 64 exists for the sample data
        logger.info("Ensuring AC 64 exists...")
        conn.execute(text("""
            INSERT INTO ac_master (ac_id, ac_name, ac_type, district_name, state)
            VALUES ('GKP_64', 'Sikandrabad', 'Assembly', 'Bulandshahr', 'Uttar Pradesh')
            ON CONFLICT (ac_id) DO NOTHING
        """))
        
        # 2. Ingest existing Excel files (Sikandrabad sample)
        # Note: electoral_roll (1).xlsx matches AC 64 Part 1 based on metadata
        excel_files = [
            ('data/processed/Convert to xcel sheet/electoral_roll (1).xlsx', 'GKP_64', 1),
            ('data/processed/Convert to xcel sheet/electoral_roll.xlsx', 'GKP_322', 2) # Based on metadata showing 322
        ]
        
        for file_path, ac_id, part_no in excel_files:
            if not os.path.exists(file_path):
                logger.warning(f"File {file_path} not found")
                continue
            
            logger.info(f"Ingesting {file_path} for {ac_id} Part {part_no}")
            df = pd.read_excel(file_path)
            
            # Demographic stats
            total = len(df)
            male = len(df[df['Gender'].astype(str).str.strip().str.lower() == 'male'])
            female = len(df[df['Gender'].astype(str).str.strip().str.lower() == 'female'])
            others = total - male - female
            
            booth_id = f"{ac_id}_{part_no:03d}"
            
            # Ensure booth exists in booth_master if not already there
            conn.execute(text("""
                INSERT INTO booth_master (booth_id, ac_id, booth_number, polling_station_name)
                VALUES (:booth_id, :ac_id, :booth_number, :ps_name)
                ON CONFLICT (booth_id) DO NOTHING
            """), {"booth_id": booth_id, "ac_id": ac_id, "booth_number": part_no, "ps_name": f"Part {part_no} (Extracted)"})
            
            # Update demographic counts
            conn.execute(text("""
                UPDATE booth_master 
                SET male_voters = :male, female_voters = :female, other_voters = :others, total_voters = :total
                WHERE booth_id = :booth_id
            """), {"male": male, "female": female, "others": others, "total": total, "booth_id": booth_id})
            
            logger.info(f"  Updated {booth_id}: Total={total}, M={male}, F={female}")

        # 3. Ingest pipeline output (AC 322 Part 2 or similar)
        output_dir = 'data/processed/Outputs of pipline/eroll_322_part2'
        records_path = os.path.join(output_dir, 'electoral_roll_records_english.jsonl')
        if os.path.exists(records_path):
            logger.info(f"Ingesting pipeline output from {records_path}")
            records = []
            with open(records_path, 'r', encoding='utf-8') as f:
                for line in f:
                    records.append(json.loads(line))
            
            if records:
                df_p = pd.DataFrame(records)
                total = len(df_p)
                male = len(df_p[df_p['gender'].astype(str).str.strip().str.lower() == 'male'])
                female = len(df_p[df_p['gender'].astype(str).str.strip().str.lower() == 'female'])
                others = total - male - female
                
                # We assume this is Part 2 based on filename "HIN-2"
                ac_id = 'GKP_322'
                part_no = 2
                booth_id = f"{ac_id}_{part_no:03d}"
                
                conn.execute(text("""
                    UPDATE booth_master 
                    SET male_voters = :male, female_voters = :female, other_voters = :others, total_voters = :total
                    WHERE booth_id = :booth_id
                """), {"male": male, "female": female, "others": others, "total": total, "booth_id": booth_id})
                
                logger.info(f"  Updated {booth_id} from pipeline: Total={total}, M={male}, F={female}")

        conn.commit()
    logger.info("Ingestion complete.")

if __name__ == "__main__":
    ingest()
