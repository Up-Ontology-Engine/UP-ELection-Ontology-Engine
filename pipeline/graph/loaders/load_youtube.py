"""
Neo4j loader — YouTubeVideo nodes

Reads yt_videos from Postgres and creates:
  (:YouTubeVideo)-[:ABOUT_AC]->(:AssemblyConstituency)
  (:YouTubeVideo)-[:FROM_CHANNEL]->(:Channel)

Also creates (:Channel) nodes for each unique channel.

Run: python -m graph.loaders.load_youtube
"""
from __future__ import annotations

import logging

from neo4j import Session
import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)

BATCH_SIZE = 200

# Keyword → issue code mapping for video title tagging
_ISSUE_KEYWORDS = {
    "water":        "water",  "jal":     "water",   "पानी":   "water",
    "road":         "roads",  "sadak":   "roads",   "सड़क":   "roads",
    "bijli":        "electricity", "power": "electricity", "बिजली": "electricity",
    "job":          "jobs",   "rojgar":  "jobs",    "रोजगार": "jobs",
    "kisan":        "farmer", "farmer":  "farmer",  "किसान":  "farmer",
    "health":       "health", "hospital":"health",  "स्वास्थ्य":"health",
    "education":    "education", "school":"education","शिक्षा":"education",
    "corruption":   "corruption", "bhrashtachar":"corruption",
    "housing":      "housing", "pmay":   "housing",  "घर":    "housing",
    "महंगाई":      "price_rise", "mehangai":"price_rise",
}


def _detect_issues(title: str) -> list[str]:
    lower = title.lower()
    found = set()
    for kw, code in _ISSUE_KEYWORDS.items():
        if kw in lower:
            found.add(code)
    return list(found)


def load_channels(pg_engine: sa.Engine, session: Session) -> int:
    with pg_engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT channel_id, channel_name FROM yt_channels
        """)).mappings().fetchall()

    for r in rows:
        session.run("""
            MERGE (ch:Channel {channel_id: $cid})
            SET ch.name = $name,
                ch.type = 'youtube'
        """, {"cid": r["channel_id"], "name": r["channel_name"] or r["channel_id"]})

    logger.info("Merged %d Channel nodes", len(rows))
    return len(rows)


def load_videos(pg_engine: sa.Engine, session: Session) -> int:
    with pg_engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT v.video_id, v.title, v.channel_id, v.view_count,
                   v.url, v.query_source, v.duration_secs,
                   ch.channel_name
            FROM yt_videos v
            LEFT JOIN yt_channels ch USING (channel_id)
            ORDER BY v.view_count DESC NULLS LAST
        """)).mappings().fetchall()

    if not rows:
        logger.info("No YouTube videos in Postgres — run etl.ingest_youtube_videos first")
        return 0

    loaded = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i: i + BATCH_SIZE]

        # Build row dicts with precomputed issue list
        batch_data = []
        for r in batch:
            batch_data.append({
                "video_id":    r["video_id"],
                "title":       r["title"] or "",
                "channel_id":  r["channel_id"] or "",
                "channel_name":r["channel_name"] or r["channel_id"] or "",
                "views":       int(r["view_count"] or 0),
                "url":         r["url"] or "",
                "query_source":r["query_source"] or "",
                "issues":      _detect_issues(r["title"] or ""),
            })

        # Create video nodes + FROM_CHANNEL edge
        session.run("""
            UNWIND $rows AS r
            MERGE (v:YouTubeVideo {video_id: r.video_id})
            SET v.title        = r.title,
                v.views        = r.views,
                v.url          = r.url,
                v.query_source = r.query_source,
                v.channel_name = r.channel_name
            WITH v, r
            MATCH (ch:Channel {channel_id: r.channel_id})
            MERGE (v)-[:FROM_CHANNEL]->(ch)
        """, {"rows": batch_data})

        # Wire to AC — default GKP_322 (Gorakhpur Urban), can be refined later
        session.run("""
            UNWIND $rows AS r
            MATCH (v:YouTubeVideo {video_id: r.video_id})
            MATCH (ac:AssemblyConstituency {ac_id: 'GKP_322'})
            MERGE (v)-[:ABOUT_AC]->(ac)
        """, {"rows": batch_data})

        # Wire to Issue nodes based on title keywords
        issue_rows = [{"video_id": r["video_id"], "issue": iss}
                      for r in batch_data for iss in r["issues"]]
        if issue_rows:
            session.run("""
                UNWIND $rows AS r
                MATCH (v:YouTubeVideo {video_id: r.video_id})
                MERGE (i:Issue {code: r.issue})
                MERGE (v)-[:MENTIONS_ISSUE]->(i)
            """, {"rows": issue_rows})

        loaded += len(batch)

    logger.info("Merged %d YouTubeVideo nodes", loaded)
    return loaded


def load_all(pg_engine: sa.Engine, session: Session) -> dict[str, int]:
    return {
        "channels": load_channels(pg_engine, session),
        "videos":   load_videos(pg_engine, session),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from backend.db import get_pg_engine, get_neo4j_session
    pg = get_pg_engine()
    with get_neo4j_session() as s:
        print(load_all(pg, s))
