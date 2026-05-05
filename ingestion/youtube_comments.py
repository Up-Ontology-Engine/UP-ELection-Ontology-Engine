"""
YouTube comment ingestion using yt-dlp (no API key needed).
Optionally falls back to YouTube Data API v3 for paginated access.

Usage:
    python -m ingestion.youtube_comments
"""
from __future__ import annotations
import os, json, time, random, hashlib, logging
from pathlib import Path
from datetime import datetime
import sqlalchemy as sa

logger = logging.getLogger(__name__)

# Seed video list — override or expand in data/seeds/yt_video_seeds.json
DEFAULT_SEARCH_TERMS = [
    "गोरखपुर चुनाव BJP SP",
    "gorakhpur election news",
    "Gorakhpur Urban BJP",
    "गोरखपुर विधानसभा",
]

CACHE_DIR = Path("data/yt_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def fetch_comments_ytdlp(video_url: str) -> list[dict]:
    """Download comments for a single video using yt-dlp."""
    import yt_dlp

    video_id = video_url.split("v=")[-1].split("&")[0]
    cache_file = CACHE_DIR / f"{video_id}.json"

    if cache_file.exists():
        logger.info(f"Cache hit: {video_id}")
        with open(cache_file) as f:
            return json.load(f)

    ydl_opts = {
        "writecomments": True,
        "skip_download": True,
        "quiet": True,
        "extractor_args": {"youtube": {"comment_sort": ["top"]}},
        "max_comments": ["500"],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(video_url, download=False)
        except Exception as e:
            logger.error(f"yt-dlp failed for {video_url}: {e}")
            return []

    comments = []
    for c in info.get("comments", []):
        comments.append({
            "comment_id": c.get("id", ""),
            "video_id": video_id,
            "author": c.get("author", ""),
            "text_raw": c.get("text", ""),
            "like_count": c.get("like_count", 0),
            "published_at": c.get("timestamp"),
        })

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(comments, f, ensure_ascii=False, indent=2)

    logger.info(f"Fetched {len(comments)} comments from {video_id}")
    time.sleep(random.uniform(3, 6))   # polite delay
    return comments


def load_to_postgres(comments: list[dict], engine: sa.Engine) -> int:
    if not comments:
        return 0
    loaded = 0
    with engine.connect() as conn:
        for c in comments:
            text = c.get("text_raw", "").strip()
            if not text:
                continue
            content_hash = hashlib.sha256(text.encode()).hexdigest()
            try:
                conn.execute(sa.text("""
                    INSERT INTO yt_comments
                      (comment_id, video_id, author, text_raw, like_count,
                       published_at, content_hash)
                    VALUES
                      (:cid, :vid, :author, :text, :likes, :pub, :hash)
                    ON CONFLICT (content_hash) DO NOTHING
                """), {
                    "cid": c.get("comment_id") or content_hash[:20],
                    "vid": c.get("video_id"),
                    "author": c.get("author", ""),
                    "text": text,
                    "likes": c.get("like_count", 0),
                    "pub": datetime.fromtimestamp(c["published_at"]) if c.get("published_at") else None,
                    "hash": content_hash,
                })
                loaded += 1
            except Exception as e:
                logger.debug(f"Skip comment: {e}")
        conn.commit()
    return loaded


def run(video_urls: list[str] | None = None):
    engine = sa.create_engine(os.environ["POSTGRES_URL"])

    seeds_file = Path("data/seeds/yt_video_seeds.json")
    if video_urls is None:
        if seeds_file.exists():
            video_urls = json.loads(seeds_file.read_text())
        else:
            logger.warning("No video seeds found. Add URLs to data/seeds/yt_video_seeds.json")
            return

    total = 0
    for url in video_urls:
        comments = fetch_comments_ytdlp(url)
        n = load_to_postgres(comments, engine)
        total += n
        logger.info(f"Loaded {n} new comments from {url}")

    logger.info(f"YouTube ingestion complete. Total new rows: {total}")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    run()
