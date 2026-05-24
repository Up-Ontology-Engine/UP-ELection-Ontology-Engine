import os
import glob
import pandas as pd
import sqlalchemy as sa
from sqlalchemy import text
from pathlib import Path
import logging
import sys

# Add current directory to path so we can import our utility
sys.path.append(os.path.dirname(__file__))
from kruti_to_unicode import kruti_to_unicode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_form20_xls(file_path):
    # Determine AC number from filename
    try:
        ac_num = "".join(filter(str.isdigit, os.path.basename(file_path)))
        if not ac_num: ac_num = "322"
    except:
        ac_num = "322"

    df = pd.read_excel(file_path, skiprows=6, header=None)
    
    booth_master_data = []
    booth_results_data = []
    
    # Candidate names are in row 4 (index 3)
    header_row = pd.read_excel(file_path, skiprows=3, nrows=1, header=None).iloc[0]
    
    for _, row in df.iterrows():
        part_no_raw = row[1]
        if pd.isna(part_no_raw) or not str(part_no_raw).replace('.','').isdigit():
            continue
        
        part_no = int(float(part_no_raw))
        booth_name_raw = str(row[2])
        booth_name = kruti_to_unicode(booth_name_raw)
        
        booth_id = f"GKP_{ac_num}_{part_no:03d}"
        ac_id = f"GKP_{ac_num}"
        
        # Turnout stats (XLS columns: 3=Total Electors, 4=Male, 5=Female, 6=Other)
        total_electors = 0
        male_voters = 0
        female_voters = 0
        
        try:
            total_electors = int(float(row[3]))
            male_voters = int(float(row[4]))
            female_voters = int(float(row[5]))
        except:
            pass

        booth_master_data.append({
            "booth_id": booth_id,
            "ac_id": ac_id,
            "booth_number": part_no,
            "polling_station_name": booth_name,
            "total_voters": total_electors,
            "male_voters": male_voters,
            "female_voters": female_voters
        })
        
        # Candidate results
        party_map = {
            "B.J.P": "BJP",
            "SP": "SP",
            "B.S.P": "BSP",
            "INC": "INC",
            "AAP": "AAP",
            "AD": "AD",
            "NISHAD": "NISHAD"
        }
        
        # Results start at index 11
        for i in range(11, len(row) - 1, 2):
            party_raw = str(row[i])
            votes_raw = row[i+1]
            
            if "Total" in party_raw or "NOTA" in party_raw:
                continue
                
            try:
                votes = int(float(votes_raw))
            except:
                votes = 0
                
            party = party_map.get(party_raw.strip(), party_raw.strip())
            
            booth_results_data.append({
                "booth_id": booth_id,
                "election_year": 2022,
                "party": party,
                "votes": votes,
                "winner_flag": False
            })

    # Mark winners
    max_votes = {}
    for r in booth_results_data:
        max_votes[r["booth_id"]] = max(max_votes.get(r["booth_id"], -1), r["votes"])
        
    for r in booth_results_data:
        r["winner_flag"] = r["votes"] == max_votes[r["booth_id"]] and r["votes"] > 0

    return booth_master_data, booth_results_data

def run():
    from dotenv import load_dotenv; load_dotenv()
    engine = sa.create_engine(os.environ["POSTGRES_URL"])
    
    files = glob.glob(str(Path(__file__).parents[1] / "data" / "Form 20 Gorakhpur Data" / "*.xls"))
    files = list(set(files))
    
    for f in files:
        if "BlockWise" in f or "DistrictWise" in f or "Census" in f:
            continue
        logger.info(f"Processing {f}")
        try:
            all_booths, all_results = parse_form20_xls(f)
            
            with engine.connect() as conn:
                # Insert booths first
                for b in all_booths:
                    conn.execute(text("""
                        INSERT INTO booth_master
                            (booth_id, ac_id, booth_number, polling_station_name, total_voters, male_voters, female_voters)
                        VALUES
                            (:booth_id, :ac_id, :booth_number, :polling_station_name, :total_voters, :male_voters, :female_voters)
                        ON CONFLICT (booth_id) DO UPDATE SET
                            total_voters = EXCLUDED.total_voters,
                            male_voters = EXCLUDED.male_voters,
                            female_voters = EXCLUDED.female_voters,
                            polling_station_name = EXCLUDED.polling_station_name
                    """), b)
                
                # Insert results
                for r in all_results:
                    conn.execute(text("""
                        INSERT INTO booth_results
                            (booth_id, election_year, party, votes, winner_flag)
                        VALUES
                            (:booth_id, :election_year, :party, :votes, :winner_flag)
                        ON CONFLICT DO NOTHING
                    """), r)
                
                conn.commit()
            logger.info(f"Finished {f}")
        except Exception as e:
            logger.error(f"Failed to process {f}: {e}")
            
    # Final cleanup (Deduplication)
    logger.info("Running final deduplication...")
    with engine.connect() as conn:
        conn.execute(text("""
            DELETE FROM booth_results a USING booth_results b
            WHERE a.id < b.id
            AND a.booth_id = b.booth_id
            AND a.election_year = b.election_year
            AND a.party = b.party
        """))
        conn.commit()
    logger.info("Ingestion complete.")

if __name__ == "__main__":
    run()
