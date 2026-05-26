"""Find duplicate Candidate groups in Neo4j and optionally mark duplicates in Postgres.

Dry-run by default: writes a CSV listing canonical_id and duplicate candidate_ids.
Use --apply to set `is_deprecated = TRUE` on duplicate rows in `candidate_master` (creates a backup table first).

Usage:
  source .venv/bin/activate
  NEO4J_URI=bolt://localhost:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=pass POSTGRES_URL='postgresql://user:pw@host/db' python graph/tools/mark_duplicate_candidates.py [--apply]
"""
from __future__ import annotations

import os
import csv
import argparse
from datetime import datetime
from neo4j import GraphDatabase, basic_auth
import sqlalchemy as sa
from sqlalchemy import text

REPORT_DIR = os.path.join(os.path.dirname(__file__), '..', 'reports')
os.makedirs(REPORT_DIR, exist_ok=True)

DUP_QUERY = """
MATCH (n:Candidate)
WHERE n.candidate_id IS NOT NULL
WITH n.candidate_id AS key, collect(n) AS nodes
WHERE size(nodes) > 1
WITH key, head(nodes) AS canonical, tail(nodes) AS duplicates
UNWIND duplicates AS d
RETURN canonical.candidate_id AS canonical_id, d.candidate_id AS duplicate_id
"""


def backup_postgres(engine: sa.Engine):
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS candidate_master_audit AS TABLE candidate_master WITH NO DATA;"))
        conn.execute(text("INSERT INTO candidate_master_audit SELECT * FROM candidate_master;"))


def ensure_column(engine: sa.Engine):
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE candidate_master ADD COLUMN IF NOT EXISTS is_deprecated BOOLEAN DEFAULT FALSE;"))


def mark_in_postgres(pg_url: str, ids: list[str]):
    engine = sa.create_engine(pg_url)
    ensure_column(engine)
    backup_postgres(engine)
    BATCH = 500
    with engine.connect() as conn:
        for i in range(0, len(ids), BATCH):
            batch = ids[i:i+BATCH]
            conn.execute(text("""
                UPDATE candidate_master
                SET is_deprecated = TRUE
                WHERE candidate_id = ANY(:ids)
            """), {'ids': batch})


def find_duplicates(uri: str, user: str, pw: str) -> dict[str, list[str]]:
    drv = GraphDatabase.driver(uri, auth=basic_auth(user, pw))
    out: dict[str, list[str]] = {}
    with drv.session() as sess:
        res = sess.run(DUP_QUERY)
        for r in res:
            canonical = r['canonical_id']
            dup = r['duplicate_id']
            out.setdefault(canonical, []).append(dup)
    drv.close()
    return out


def write_report(mapping: dict[str, list[str]]) -> str:
    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    out_path = os.path.join(REPORT_DIR, f'duplicate_candidates_{ts}.csv')
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['canonical_id', 'duplicate_ids_pipe'])
        for k, v in mapping.items():
            w.writerow([k, '|'.join(v)])
    return out_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Apply is_deprecated flags to Postgres')
    args = parser.parse_args()

    uri = os.environ.get('NEO4J_URI')
    user = os.environ.get('NEO4J_USER')
    pw = os.environ.get('NEO4J_PASSWORD')
    pg_url = os.environ.get('POSTGRES_URL')
    if not uri or not user or not pw:
        print('Missing Neo4j env vars: NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD')
        return

    mapping = find_duplicates(uri, user, pw)
    report = write_report(mapping)
    total_dupes = sum(len(v) for v in mapping.values())
    print(f'Found {len(mapping)} duplicate groups with {total_dupes} total duplicate nodes. Report: {report}')

    if args.apply:
        if not pg_url:
            print('POSTGRES_URL required to apply changes')
            return
        all_dups = [d for v in mapping.values() for d in v]
        if not all_dups:
            print('No duplicates to apply')
            return
        print('Applying is_deprecated flags to Postgres (backup created)')
        mark_in_postgres(pg_url, all_dups)
        print('Applied flags to Postgres')
    else:
        print('Dry-run only. To apply changes, re-run with --apply and set POSTGRES_URL')


if __name__ == '__main__':
    main()
