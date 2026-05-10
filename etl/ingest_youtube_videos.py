"""
ETL: Load YouTube video index → yt_channels + yt_videos + pulse_events_raw

Reads  data/Digital_Dataset/Youtube/videos/metadata/video_index.json  (831 videos)
Writes yt_channels, yt_videos, pulse_events_raw (for NLP processing).

Run: python -m etl.ingest_youtube_videos
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_REPO = Path(__file__).resolve().parents[1]
VIDEO_INDEX = _REPO / "data" / "Digital_Dataset" / "Youtube" / "videos" / "metadata" / "video_index.json"

# GKP AC mapping from query_source keywords
_QUERY_TO_AC = {
    "गोरखपुर":       "GKP_322",
    "gorakhpur":     "GKP_322",
    "rural":         "GKP_323",
    "ग्रामीण":       "GKP_323",
    "urban":         "GKP_322",
    "shahar":        "GKP_322",
}


def _guess_ac(query_source: str) -> str:
    qs = (query_source or "").lower()
    for kw, ac in _QUERY_TO_AC.items():
        if kw in qs:
            return ac
    return "GKP_322"   # default: Gorakhpur Urban


def _title_hash(title: str, video_id: str) -> str:
    return hashlib.sha256(f"{video_id}:{title}".encode()).hexdigest()


def run() -> None:
    if not VIDEO_INDEX.exists():
        logger.error("video_index.json not found at %s", VIDEO_INDEX)
        return

    engine = sa.create_engine(
        os.environ.get("POSTGRES_URL", "postgresql://postgres:postgres@localhost:5432/gorakhpur_db")
    )

    data = json.loads(VIDEO_INDEX.read_text(encoding="utf-8"))
    videos: list[dict] = data.get("videos", [])
    logger.info("Loaded %d videos from index", len(videos))

    # ── 1. Deduplicate channels ───────────────────────────────────────────────
    channels: dict[str, str] = {}   # channel_id → channel_name
    for v in videos:
        cid  = v.get("channel_id", "").strip()
        name = v.get("channel", "").strip()
        if cid:
            channels[cid] = name

    # ── 2. DB writes ──────────────────────────────────────────────────────────
    with engine.connect() as conn:

        # channels
        for cid, cname in channels.items():
            conn.execute(text("""
                INSERT INTO yt_channels (channel_id, channel_name, relevance_tag)
                VALUES (:cid, :name, 'gorakhpur_election')
                ON CONFLICT (channel_id) DO UPDATE SET channel_name = EXCLUDED.channel_name
            """), {"cid": cid, "name": cname})
        logger.info("Upserted %d channels", len(channels))

        # videos
        vid_count = 0
        raw_count = 0
        for v in videos:
            video_id    = v.get("video_id", "").strip()
            channel_id  = v.get("channel_id", "").strip() or None
            title       = v.get("title", "").strip()
            description = v.get("description", "").strip()
            url         = v.get("url", "")
            views       = v.get("views") or 0
            likes       = v.get("likes") or 0
            comment_cnt = v.get("comment_count") or 0
            duration    = v.get("duration")
            query_src   = v.get("query_source", "")
            scraped_at  = v.get("scraped_at")
            # Always derive hash from video_id so it's unique-safe
            content_hash = _title_hash(title, video_id)

            if not video_id or not title:
                continue

            # ensure channel row exists (some videos may have channel not in deduplicated set)
            if channel_id and channel_id not in channels:
                conn.execute(text("""
                    INSERT INTO yt_channels (channel_id, channel_name, relevance_tag)
                    VALUES (:cid, :name, 'gorakhpur_election')
                    ON CONFLICT (channel_id) DO NOTHING
                """), {"cid": channel_id, "name": channel_id})

            try:
                conn.execute(text("""
                    INSERT INTO yt_videos
                        (video_id, channel_id, title, description, view_count, like_count,
                         comment_count, url, content_hash, query_source, duration_secs, created_at)
                    VALUES
                        (:vid, :cid, :title, :desc, :views, :likes,
                         :comments, :url, :hash, :qs, :dur,
                         COALESCE(CAST(:scraped AS timestamptz), NOW()))
                    ON CONFLICT (video_id) DO UPDATE SET
                        view_count    = EXCLUDED.view_count,
                        like_count    = EXCLUDED.like_count,
                        comment_count = EXCLUDED.comment_count,
                        content_hash  = EXCLUDED.content_hash
                """), {
                    "vid":     video_id,
                    "cid":     channel_id,
                    "title":   title,
                    "desc":    description[:1000],
                    "views":   views,
                    "likes":   likes,
                    "comments": comment_cnt,
                    "url":     url,
                    "hash":    content_hash,
                    "qs":      query_src,
                    "dur":     duration,
                    "scraped": scraped_at,
                })
                vid_count += 1
            except Exception as e:
                logger.warning("Skipping video %s: %s", video_id, e)
                conn.rollback()
                continue

            # pulse_events_raw — title + first 300 chars of description
            raw_text = title
            if description:
                raw_text += " " + description[:300]

            conn.execute(text("""
                INSERT INTO pulse_events_raw (source_type, source_id, text_raw, processed, video_id)
                VALUES ('youtube', :vid, :text, FALSE, :vid)
                ON CONFLICT DO NOTHING
            """), {"vid": video_id, "text": raw_text.strip()})
            raw_count += 1

        conn.commit()

    logger.info("Inserted/updated %d videos, %d pulse_events_raw entries", vid_count, raw_count)
    logger.info("Done. Run NLP pipeline next: python -m flows.nlp.flow_sentiment")


if __name__ == "__main__":
    run()
