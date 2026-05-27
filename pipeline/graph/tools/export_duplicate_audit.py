"""Export canonical -> duplicates audit CSV for selected labels.

Usage:
  source .venv/bin/activate
  NEO4J_URI=bolt://localhost:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=gorakhpur_neo4j_pass python graph/tools/export_duplicate_audit.py

This connects to Neo4j, runs a per-label query to find duplicate groups, and writes
`graph/reports/duplicate_audit_<ts>.csv` with columns: label, key_value, canonical_id, duplicate_ids
"""

from __future__ import annotations

import csv
import os
from datetime import datetime

from neo4j import GraphDatabase, basic_auth

REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

LABELS = [
    ("Candidate", "candidate_id"),
    ("Party", "party_id"),
    ("Booth", "booth_id"),
    ("PulseEvent", "event_id"),
]

QUERY = """
MATCH (n:%s)
WHERE n.%s IS NOT NULL
WITH n.%s AS key, collect(n) AS nodes
WHERE size(nodes) > 1
WITH key, head(nodes) AS canonical, [x IN tail(nodes) | id(x)] AS duplicates
RETURN key AS key_value, id(canonical) AS canonical_id, duplicates
"""


def run(uri: str, user: str, pw: str) -> str:
    drv = GraphDatabase.driver(uri, auth=basic_auth(user, pw))
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_path = os.path.join(REPORT_DIR, f"duplicate_audit_{ts}.csv")
    with drv.session() as sess, open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["label", "key_value", "canonical_id", "duplicate_ids"])
        total = 0
        for label, prop in LABELS:
            q = QUERY % (label, prop, prop)
            res = sess.run(q)
            for r in res:
                key = r["key_value"]
                canonical = r["canonical_id"]
                dups = r["duplicates"]
                writer.writerow([label, key, canonical, "|".join([str(x) for x in dups])])
                total += 1
    drv.close()
    return out_path


def main():
    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USER")
    pw = os.environ.get("NEO4J_PASSWORD")
    if not uri or not user or not pw:
        print("Missing Neo4j env vars")
        return
    print("Exporting duplicate audit CSV...")
    path = run(uri, user, pw)
    print("Wrote", path)


if __name__ == "__main__":
    main()
