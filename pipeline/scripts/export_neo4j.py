"""
Export selected Neo4j nodes and relationships to CSV files under data/exports.
Usage:
  export POSTGRES_URL=... NEO4J_URI=bolt://localhost:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=...
  .venv/bin/python scripts/export_neo4j.py

Exports:
 - booths: data/exports/booths.csv
 - acs: data/exports/assembly_constituencies.csv
 - candidates: data/exports/candidates.csv
 - youtube_videos: data/exports/youtube_videos.csv
 - relationships: data/exports/relationships.csv (sample)
"""

from __future__ import annotations

import csv
import os

from neo4j import GraphDatabase

EXPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "gorakhpur_neo4j_pass")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

QUERIES = {
    "booths.csv": (
        "MATCH (b:Booth) RETURN b.booth_id AS booth_id, b.name AS name, b.ac_id AS ac_id, b.total_voters AS total_voters, b.male_voters AS male_voters, b.female_voters AS female_voters LIMIT 10000",
        ["booth_id", "name", "ac_id", "total_voters", "male_voters", "female_voters"],
    ),
    "assembly_constituencies.csv": (
        "MATCH (ac:AssemblyConstituency) RETURN ac.ac_id AS ac_id, ac.name AS name, ac.ac_type AS ac_type LIMIT 10000",
        ["ac_id", "name", "ac_type"],
    ),
    "candidates.csv": (
        "MATCH (c:Candidate) RETURN c.candidate_id AS candidate_id, c.name AS name, c.party AS party, c.ac_id AS ac_id LIMIT 10000",
        ["candidate_id", "name", "party", "ac_id"],
    ),
    "youtube_videos.csv": (
        "MATCH (v:YouTubeVideo) RETURN v.video_id AS video_id, v.title AS title, v.views AS views, v.query_source AS query_source LIMIT 10000",
        ["video_id", "title", "views", "query_source"],
    ),
    "relationships.csv": (
        "MATCH (a)-[r]->(b) RETURN id(a) AS a_id, labels(a)[0] AS a_label, type(r) AS rel_type, id(b) AS b_id, labels(b)[0] AS b_label LIMIT 20000",
        ["a_id", "a_label", "rel_type", "b_id", "b_label"],
    ),
}


def run_export():
    with driver.session() as session:
        for fname, (cypher, headers) in QUERIES.items():
            out_path = os.path.join(EXPORT_DIR, fname)
            print("Running:", cypher)
            res = session.run(cypher)
            rows = [dict(record) for record in res]
            with open(out_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                for r in rows:
                    # ensure keys exist
                    out = {h: r.get(h) for h in headers}
                    writer.writerow(out)
            print(f"Wrote {len(rows)} rows to", out_path)


if __name__ == "__main__":
    run_export()
