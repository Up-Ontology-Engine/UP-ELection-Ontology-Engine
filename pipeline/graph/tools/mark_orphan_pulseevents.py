"""Find PulseEvent nodes without AT_BOOTH in Neo4j and optionally flag them in Postgres.

Dry-run by default: prints counts and writes a JSON list of orphan event IDs.
Use --apply to write `is_orphan = TRUE` into Postgres (creates a backup table first).

Usage:
  source .venv/bin/activate
  NEO4J_URI=neo4j://localhost:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=pass POSTGRES_URL='postgresql://user:pw@host/db' python graph/tools/mark_orphan_pulseevents.py [--apply]
"""
from __future__ import annotations

import os
import json
import argparse
from datetime import datetime
from neo4j import GraphDatabase, basic_auth
import sqlalchemy as sa
from sqlalchemy import text

OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'reports')
os.makedirs(OUT_DIR, exist_ok=True)

ORPHAN_QUERY = """
MATCH (pe:PulseEvent)
WHERE NOT EXISTS { MATCH (pe)-[r]->(:Booth) WHERE type(r) = 'AT_BOOTH' }
RETURN pe.event_id AS event_id
"""

def get_orphans(uri: str, user: str, pw: str) -> list[str]:
    drv = GraphDatabase.driver(uri, auth=basic_auth(user, pw))
    with drv.session() as sess:
        res = sess.run(ORPHAN_QUERY)
        rows = [r['event_id'] for r in res]
    drv.close()
    return rows

def backup_postgres(pg_engine: sa.Engine):
    with pg_engine.connect() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS pulse_events_audit AS TABLE pulse_events WITH NO DATA;"))
        conn.execute(text("INSERT INTO pulse_events_audit SELECT * FROM pulse_events;"))

def mark_in_postgres(pg_url: str, ids: list[str]):
    engine = sa.create_engine(pg_url)
    backup_postgres(engine)
    BATCH = 500
    with engine.connect() as conn:
        for i in range(0, len(ids), BATCH):
            batch = ids[i:i+BATCH]
            conn.execute(text("""
                UPDATE pulse_events
                SET is_orphan = TRUE
                WHERE id::text = ANY(:ids)
            """), {'ids': batch})

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Apply flags to Postgres')
    args = parser.parse_args()

    uri = os.environ.get('NEO4J_URI')
    user = os.environ.get('NEO4J_USER')
    pw = os.environ.get('NEO4J_PASSWORD')
    pg_url = os.environ.get('POSTGRES_URL')
    if not uri or not user or not pw:
        print('Missing Neo4j env vars: NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD')
        return

    orphans = get_orphans(uri, user, pw)
    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    out_file = os.path.join(OUT_DIR, f'orphan_pulse_events_{ts}.json')
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump({'count': len(orphans), 'ids': orphans}, f, indent=2)
    print(f'Found {len(orphans)} orphan PulseEvent(s). Report written to {out_file}')

    if args.apply:
        if not pg_url:
            print('POSTGRES_URL required to apply changes')
            return
        print('Applying is_orphan flag to Postgres (backup created)')
        mark_in_postgres(pg_url, orphans)
        print('Applied flags to Postgres')
    else:
        print('Dry-run only. To apply changes, re-run with --apply and set POSTGRES_URL')

if __name__ == '__main__':
    main()
