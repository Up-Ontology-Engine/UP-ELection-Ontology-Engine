"""
YouTube comment ingestion using yt-dlp (no API key needed).
Saves comments as JSON files per the Digital_Dataset directory structure.
Optionally loads into PostgreSQL if POSTGRES_URL env var is set.

Usage:
    python -m ingestion.youtube_comments                   # from video_index
    python -m ingestion.youtube_comments --classify        # classify after fetch
    python -m ingestion.youtube_comments --video URL       # single video
"""
from __future__ import annotations
import os, json, time, random, hashlib, logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import sqlalchemy as sa

logger = logging.getLogger(__name__)

_REPO = Path(__file__).resolve().parents[1]
CACHE_DIR          = _REPO / "data" / "yt_cache"
COMMENTS_RAW_DIR   = _REPO / "data" / "Digital_Dataset" / "Youtube" / "comments" / "raw"
COMMENTS_PROC_DIR  = _REPO / "data" / "Digital_Dataset" / "Youtube" / "comments" / "processed"
BY_VIDEO_DIR       = _REPO / "data" / "Digital_Dataset" / "Youtube" / "comments" / "by_video"
VIDEO_INDEX        = _REPO / "data" / "Digital_Dataset" / "Youtube" / "videos" / "metadata" / "video_index.json"
SEEDS_FILE         = _REPO / "data" / "seeds" / "yt_video_seeds.json"

for _d in (CACHE_DIR, COMMENTS_RAW_DIR, COMMENTS_PROC_DIR, BY_VIDEO_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def fetch_comments_ytdlp(video_url: str, max_comments: int = 500) -> list[dict]:
    """Download comments for a single video using yt-dlp. Returns list of comment dicts."""
    try:
        import yt_dlp
    except ImportError:
        logger.error("yt-dlp not installed. Run: pip install yt-dlp")
        return []

    video_id = video_url.split("v=")[-1].split("&")[0]
    cache_file = CACHE_DIR / f"comments_{video_id}.json"

    if cache_file.exists():
        logger.info(f"Cache hit (comments): {video_id}")
        with open(cache_file, encoding="utf-8") as f:
            return json.load(f)

    ydl_opts = {
        "writecomments": True,
        "skip_download": True,
        "quiet": True,
        "extractor_args": {"youtube": {"comment_sort": ["top"]}},
        "max_comments": [str(max_comments)],
        "ignoreerrors": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(video_url, download=False)
        except Exception as e:
            logger.error(f"yt-dlp failed for {video_url}: {e}")
            return []

    comments: list[dict] = []
    for c in (info or {}).get("comments", []):
        ts = c.get("timestamp")
        pub = (datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
               if ts else None)
        text = c.get("text", "").strip()
        comments.append({
            "comment_id":   c.get("id", hashlib.md5(text.encode()).hexdigest()[:12]),
            "video_id":     video_id,
            "author":       c.get("author", ""),
            "author_id":    c.get("author_id", ""),
            "text_raw":     text,
            "like_count":   c.get("like_count", 0),
            "reply_count":  c.get("reply_count", 0),
            "published_at": pub,
            "parent_id":    c.get("parent", None),
            "is_reply":     bool(c.get("parent")),
            "language":     "",   # filled by classifier if needed
        })

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(comments, f, ensure_ascii=False, indent=2)

    logger.info(f"Fetched {len(comments)} comments from {video_id}")
    time.sleep(random.uniform(3, 6))
    return comments


def save_comments_json(video_id: str, comments: list[dict]) -> None:
    """Save per-video comments to by_video/ and append to raw daily file."""
    # per-video file
    per_vid = BY_VIDEO_DIR / f"{video_id}_comments.json"
    per_vid.write_text(
        json.dumps({"video_id": video_id, "total": len(comments), "comments": comments},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # daily raw file
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    daily = COMMENTS_RAW_DIR / f"comments_{today}.json"
    existing: list[dict] = []
    if daily.exists():
        try:
            existing = json.loads(daily.read_text(encoding="utf-8")).get("comments", [])
        except Exception:
            pass
    merged = existing + comments
    daily.write_text(
        json.dumps({"scraped_at": datetime.now(timezone.utc).isoformat(),
                    "total": len(merged), "comments": merged},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


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
                    "cid":    c.get("comment_id") or content_hash[:20],
                    "vid":    c.get("video_id"),
                    "author": c.get("author", ""),
                    "text":   text,
                    "likes":  c.get("like_count", 0),
                    "pub":    c.get("published_at"),
                    "hash":   content_hash,
                })
                loaded += 1
            except Exception as e:
                logger.debug(f"Skip comment: {e}")
        conn.commit()
    return loaded


def _load_video_urls() -> list[str]:
    """Load video URLs from video_index.json or seeds file."""
    if VIDEO_INDEX.exists():
        try:
            data = json.loads(VIDEO_INDEX.read_text(encoding="utf-8"))
            urls = [v["url"] for v in data.get("videos", []) if v.get("url")]
            if urls:
                logger.info(f"Loaded {len(urls)} video URLs from index.")
                return urls
        except Exception as exc:
            logger.warning(f"Could not read video index: {exc}")

    if SEEDS_FILE.exists():
        try:
            urls = json.loads(SEEDS_FILE.read_text(encoding="utf-8"))
            logger.info(f"Loaded {len(urls)} seed URLs.")
            return urls
        except Exception:
            pass

    logger.warning("No video URLs found. Run youtube_videos.py first, or add seeds.")
    return []


def run(video_urls: Optional[list[str]] = None, classify: bool = False,
        use_postgres: bool = False) -> int:
    urls = video_urls or _load_video_urls()
    if not urls:
        return 0

    engine: Optional[sa.Engine] = None
    if use_postgres and os.environ.get("POSTGRES_URL"):
        engine = sa.create_engine(os.environ["POSTGRES_URL"])

    total_comments = 0
    all_comments: list[dict] = []

    for url in urls:
        comments = fetch_comments_ytdlp(url)
        if not comments:
            continue

        vid_id = url.split("v=")[-1].split("&")[0]
        save_comments_json(vid_id, comments)
        all_comments.extend(comments)

        if engine:
            n = load_to_postgres(comments, engine)
            logger.info(f"DB: loaded {n} new comments from {vid_id}")

        total_comments += len(comments)

    logger.info(f"Total comments collected: {total_comments}")

    if classify and all_comments:
        try:
            from ingestion.classifier import classify_comments
            classified = classify_comments(all_comments)
            today = datetime.now(timezone.utc).strftime("%Y%m%d")
            out = COMMENTS_PROC_DIR / f"comments_classified_{today}.json"
            out.write_text(
                json.dumps({"classified_at": datetime.now(timezone.utc).isoformat(),
                            "total": len(classified),
                            "classified_comments": classified},
                           ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info(f"Classified {len(classified)} comments → {out}")
        except Exception as exc:
            logger.warning(f"Classification skipped: {exc}")

    return total_comments


if __name__ == "__main__":
    import argparse
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                Path(__file__).resolve().parents[1] / "logs" / "youtube_comments.log",
                encoding="utf-8",
            ),
        ],
    )
    parser = argparse.ArgumentParser(description="Gorakhpur YouTube comment scraper")
    parser.add_argument("--video",    type=str, default=None,
                        help="Single video URL to fetch comments for")
    parser.add_argument("--classify", action="store_true",
                        help="Run BJP/neutral/anti-BJP classification after fetching")
    parser.add_argument("--postgres", action="store_true",
                        help="Also write to PostgreSQL (requires POSTGRES_URL env var)")
    args = parser.parse_args()

    urls = [args.video] if args.video else None
    total = run(video_urls=urls, classify=args.classify, use_postgres=args.postgres)
    print(f"\nDone. {total} comments collected.")
