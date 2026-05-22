"""Run the duplicate-report Cypher queries and export results.

Usage:
  source .venv/bin/activate
  NEO4J_URI=neo4j://localhost:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=pass python graph/tools/run_duplicate_report.py

Generates: graph/reports/duplicate_report_<timestamp>.json
"""
from __future__ import annotations

import os
import json
from datetime import datetime
from neo4j import GraphDatabase, basic_auth

REPORT_DIR = os.path.join(os.path.dirname(__file__), '..', 'reports')
os.makedirs(REPORT_DIR, exist_ok=True)

def read_queries(path: str) -> list[str]:
    s = open(path, 'r', encoding='utf-8').read()
    # split on semicolons but keep queries simple — the file uses separate RETURN blocks
    parts = [p for p in s.split(';') if p.strip()]
    queries = []
    for p in parts:
        # remove single-line comments starting with // and blank lines
        lines = [ln for ln in p.splitlines() if not ln.strip().startswith('//')]
        cleaned = '\n'.join(lines).strip()
        if cleaned:
            queries.append(cleaned)
    return queries

def run(uri: str, user: str, password: str) -> dict:
    drv = GraphDatabase.driver(uri, auth=basic_auth(user, password))
    qfile = os.path.join(os.path.dirname(__file__), '..', 'fixes', 'duplicate_report.cypher')
    queries = read_queries(qfile)
    out = {}
    with drv.session() as sess:
        for i, q in enumerate(queries, start=1):
            try:
                res = sess.run(q)
                rows = [dict(r) for r in res]
                out[f'query_{i}'] = rows
            except Exception as e:
                out[f'query_{i}'] = {'error': str(e)}
    drv.close()
    return out

def main():
    uri = os.environ.get('NEO4J_URI')
    user = os.environ.get('NEO4J_USER')
    pw = os.environ.get('NEO4J_PASSWORD')
    if not uri or not user or not pw:
        print('Missing NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD environment variables')
        return
    print('Running duplicate report against', uri)
    res = run(uri, user, pw)
    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    out_path = os.path.join(REPORT_DIR, f'duplicate_report_{ts}.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    print('Wrote report to', out_path)

if __name__ == '__main__':
    main()
