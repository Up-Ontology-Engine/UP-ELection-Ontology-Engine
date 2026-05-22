"""
Seed script: upsert rows from data/seeds/booth_master_gorakhpur_urban.csv into booth_master
Run: .venv/bin/python scripts/seed_booth_master.py
"""
import os
import csv
import sqlalchemy as sa
from sqlalchemy import text

DATA_CSV = os.path.join(os.path.dirname(__file__), '..', 'data', 'seeds', 'booth_master_gorakhpur_urban.csv')

def upsert(csv_path: str):
    url = os.environ.get('POSTGRES_URL')
    if not url:
        raise SystemExit('Set POSTGRES_URL environment variable')
    engine = sa.create_engine(url)
    inserted = 0
    with engine.begin() as conn:
        with open(csv_path, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    conn.execute(text("""
                        INSERT INTO booth_master (booth_id, ac_id, booth_number, polling_station_name, address, locality_hint, male_voters, female_voters, other_voters, total_voters)
                        VALUES (:booth_id, :ac_id, :booth_number, :polling_station_name, :address, :locality_hint, :male_voters, :female_voters, :other_voters, :total_voters)
                        ON CONFLICT (booth_id) DO UPDATE SET
                            ac_id = EXCLUDED.ac_id,
                            booth_number = EXCLUDED.booth_number,
                            polling_station_name = EXCLUDED.polling_station_name,
                            address = EXCLUDED.address,
                            locality_hint = EXCLUDED.locality_hint,
                            male_voters = EXCLUDED.male_voters,
                            female_voters = EXCLUDED.female_voters,
                            other_voters = EXCLUDED.other_voters,
                            total_voters = EXCLUDED.total_voters,
                            updated_at = NOW()
                    """), {
                        'booth_id': row['booth_id'],
                        'ac_id': row['ac_id'],
                        'booth_number': int(row['booth_number']) if row.get('booth_number') else None,
                        'polling_station_name': row.get('polling_station_name'),
                        'address': row.get('address'),
                        'locality_hint': row.get('locality_hint'),
                        'male_voters': int(row.get('male_voters') or 0),
                        'female_voters': int(row.get('female_voters') or 0),
                        'other_voters': int(row.get('other_voters') or 0),
                        'total_voters': int(row.get('total_voters') or 0),
                    })
                    inserted += 1
                except Exception as e:
                    print('Skip', row.get('booth_id'), e)
    print('Upserted', inserted, 'rows into booth_master')

if __name__ == '__main__':
    upsert(DATA_CSV)
