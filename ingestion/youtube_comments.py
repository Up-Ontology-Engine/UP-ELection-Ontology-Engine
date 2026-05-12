"""
YouTube comment ingestion for Gorakhpur political videos (10-year dataset, 831 videos).

Primary engine  : youtube-comment-downloader (pure Python, no API key)
Fallback engine : yt-dlp (if installed)

Priority ordering for scraping:
  P1 — videos with known comment_count > 0       (27 videos)
  P2 — views > 50 000 (high engagement proxies)  (55 videos)
  P3 — views 10 000–50 000                       (141 videos)
  P4 — remaining videos                          (608 videos)

Usage:
    python -m ingestion.youtube_comments                      # all videos, incremental
    python -m ingestion.youtube_comments --max-videos 150     # top-150 by priority
    python -m ingestion.youtube_comments --classify           # fetch + classify
    python -m ingestion.youtube_comments --video URL          # single video
    python -m ingestion.youtube_comments --classify-existing  # classify already-fetched
    python -m ingestion.youtube_comments --stats              # show collection stats
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_REPO = Path(__file__).resolve().parents[1]
CACHE_DIR          = _REPO / "data" / "yt_cache"
COMMENTS_RAW_DIR   = _REPO / "data" / "Digital_Dataset" / "Youtube" / "comments" / "raw"
COMMENTS_PROC_DIR  = _REPO / "data" / "Digital_Dataset" / "Youtube" / "comments" / "processed"
BY_VIDEO_DIR       = _REPO / "data" / "Digital_Dataset" / "Youtube" / "comments" / "by_video"
ANALYSIS_DIR       = _REPO / "data" / "Digital_Dataset" / "Youtube" / "analysis"
VIDEO_INDEX        = _REPO / "data" / "Digital_Dataset" / "Youtube" / "videos" / "metadata" / "video_index.json"

for _d in (CACHE_DIR, COMMENTS_RAW_DIR, COMMENTS_PROC_DIR, BY_VIDEO_DIR, ANALYSIS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


# ── priority-sorted video list ────────────────────────────────────────────────
def load_videos_prioritised() -> list[dict]:
    """Load all 831 videos sorted by scraping priority."""
    if not VIDEO_INDEX.exists():
        logger.warning("video_index.json not found — run youtube_videos.py first")
        return []

    vids: list[dict] = json.loads(VIDEO_INDEX.read_text(encoding="utf-8")).get("videos", [])

    def _priority(v: dict) -> tuple[int, int]:
        cc   = v.get("comment_count") or 0
        views = v.get("views") or 0
        if cc > 0:
            return (0, -cc)           # P1: known comments — highest first
        if views >= 50_000:
            return (1, -views)        # P2: high-view videos
        if views >= 10_000:
            return (2, -views)        # P3: medium-view
        return (3, -views)            # P4: lower-view

    return sorted(vids, key=_priority)


# ── already-scraped check ─────────────────────────────────────────────────────
def _already_scraped(video_id: str) -> bool:
    return (BY_VIDEO_DIR / f"{video_id}_comments.json").exists()


# ── comment normalisation ──────────────────────────────────────────────────────
def _normalise_ycd(comment: dict, video_id: str, video_meta: Optional[dict] = None) -> dict:
    """Convert youtube-comment-downloader dict to our schema."""
    text = (comment.get("text") or "").strip()
    cid  = comment.get("cid") or hashlib.md5(text.encode()).hexdigest()[:12]

    # parse relative time to ISO-ish
    raw_time = comment.get("time") or ""
    pub: Optional[str] = None
    tp = comment.get("time_parsed")
    if tp:
        try:
            pub = datetime.fromtimestamp(float(tp), tz=timezone.utc).isoformat()
        except Exception:
            pass

    return {
        "comment_id":    cid,
        "video_id":      video_id,
        "video_title":   (video_meta or {}).get("title", ""),
        "channel":       (video_meta or {}).get("channel", ""),
        "video_date":    (video_meta or {}).get("upload_date", ""),
        "author":        comment.get("author", ""),
        "author_channel":comment.get("channel", ""),
        "text_raw":      text,
        "like_count":    comment.get("votes") or 0,
        "reply_count":   comment.get("replies") or 0,
        "published_at":  pub,
        "time_relative": raw_time,
        "is_reply":      bool(comment.get("reply")),
        "parent_id":     None,
        "language":      "",
        "content_hash":  hashlib.sha256(f"{video_id}:{cid}:{text}".encode()).hexdigest(),
        "scraped_at":    datetime.now(timezone.utc).isoformat(),
    }


# ── primary fetcher: youtube-comment-downloader ───────────────────────────────
def fetch_comments_ycd(
    video_url: str,
    max_comments: int = 200,
    video_meta: Optional[dict] = None,
) -> list[dict]:
    """Fetch comments using youtube-comment-downloader (no API key, no yt-dlp)."""
    try:
        from youtube_comment_downloader import YoutubeCommentDownloader, SORT_BY_POPULAR
    except ImportError:
        logger.error("youtube-comment-downloader not installed. Run: pip install youtube-comment-downloader")
        return []

    video_id = video_url.split("v=")[-1].split("&")[0]
    cache_file = CACHE_DIR / f"comments_{video_id}.json"
    if cache_file.exists():
        logger.debug(f"Cache hit (comments): {video_id}")
        return json.loads(cache_file.read_text(encoding="utf-8"))

    dl = YoutubeCommentDownloader()
    comments: list[dict] = []
    try:
        import itertools
        gen = dl.get_comments_from_url(video_url, sort_by=SORT_BY_POPULAR)
        raw = list(itertools.islice(gen, max_comments))
        comments = [_normalise_ycd(c, video_id, video_meta) for c in raw if c.get("text")]
    except Exception as exc:
        logger.warning(f"ycd failed [{video_id}]: {exc}")
        return []

    cache_file.write_text(json.dumps(comments, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"  {video_id}: {len(comments)} comments")
    return comments


# ── fallback fetcher: yt-dlp ──────────────────────────────────────────────────
def fetch_comments_ytdlp(
    video_url: str,
    max_comments: int = 200,
    video_meta: Optional[dict] = None,
) -> list[dict]:
    """Fallback comment fetcher using yt-dlp."""
    try:
        import yt_dlp
    except ImportError:
        return []

    video_id = video_url.split("v=")[-1].split("&")[0]
    opts = {
        "writecomments": True,
        "skip_download": True,
        "quiet": True,
        "extractor_args": {"youtube": {"comment_sort": ["top"]}},
        "max_comments": [str(max_comments)],
        "ignoreerrors": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            info = ydl.extract_info(video_url, download=False) or {}
        except Exception as exc:
            logger.warning(f"yt-dlp failed [{video_id}]: {exc}")
            return []

    comments: list[dict] = []
    for c in info.get("comments", []):
        ts  = c.get("timestamp")
        pub = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else None
        text = (c.get("text") or "").strip()
        if not text:
            continue
        cid = c.get("id") or hashlib.md5(text.encode()).hexdigest()[:12]
        comments.append({
            "comment_id":    cid,
            "video_id":      video_id,
            "video_title":   (video_meta or {}).get("title", ""),
            "channel":       (video_meta or {}).get("channel", ""),
            "video_date":    (video_meta or {}).get("upload_date", ""),
            "author":        c.get("author", ""),
            "author_channel":"",
            "text_raw":      text,
            "like_count":    c.get("like_count") or 0,
            "reply_count":   c.get("reply_count") or 0,
            "published_at":  pub,
            "time_relative": "",
            "is_reply":      bool(c.get("parent")),
            "parent_id":     c.get("parent"),
            "language":      "",
            "content_hash":  hashlib.sha256(f"{video_id}:{cid}:{text}".encode()).hexdigest(),
            "scraped_at":    datetime.now(timezone.utc).isoformat(),
        })
    return comments


def fetch_comments(
    video_url: str,
    max_comments: int = 200,
    video_meta: Optional[dict] = None,
) -> list[dict]:
    """Primary: ycd, fallback: yt-dlp."""
    comments = fetch_comments_ycd(video_url, max_comments, video_meta)
    if not comments:
        comments = fetch_comments_ytdlp(video_url, max_comments, video_meta)
    return comments


# ── persistence ───────────────────────────────────────────────────────────────
def save_per_video(video_id: str, comments: list[dict]) -> None:
    out = BY_VIDEO_DIR / f"{video_id}_comments.json"
    out.write_text(
        json.dumps(
            {"video_id": video_id, "total": len(comments), "comments": comments},
            ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )


def append_to_daily_raw(comments: list[dict]) -> Path:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    daily = COMMENTS_RAW_DIR / f"comments_{today}.json"
    existing: list[dict] = []
    if daily.exists():
        try:
            existing = json.loads(daily.read_text(encoding="utf-8")).get("comments", [])
        except Exception:
            pass
    seen = {c["content_hash"] for c in existing}
    new  = [c for c in comments if c["content_hash"] not in seen]
    merged = existing + new
    daily.write_text(
        json.dumps(
            {"scraped_at": datetime.now(timezone.utc).isoformat(),
             "total": len(merged), "comments": merged},
            ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )
    return daily


# ── classification ────────────────────────────────────────────────────────────
def classify_and_save(comments: list[dict]) -> Path:
    from ingestion.classifier import classify_comments
    classified = classify_comments(comments, use_zeroshot=False)
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    out = COMMENTS_PROC_DIR / f"comments_classified_{today}.json"

    existing: list[dict] = []
    if out.exists():
        try:
            existing = json.loads(out.read_text(encoding="utf-8")).get("classified_comments", [])
        except Exception:
            pass
    seen = {c.get("content_hash", c.get("comment_id", "")) for c in existing}
    new  = [c for c in classified
            if c.get("content_hash", c.get("comment_id", "")) not in seen]
    merged = existing + new

    out.write_text(
        json.dumps(
            {
                "classified_at":       datetime.now(timezone.utc).isoformat(),
                "total":               len(merged),
                "classified_comments": merged,
            },
            ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )
    logger.info(f"Classified → {out} ({len(merged)} total, {len(new)} new)")
    return out


def classify_existing() -> Path:
    """Classify all comments already saved to by_video/."""
    all_comments: list[dict] = []
    for f in sorted(BY_VIDEO_DIR.glob("*_comments.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            all_comments.extend(data.get("comments", []))
        except Exception as exc:
            logger.warning(f"Could not read {f}: {exc}")
    logger.info(f"Loaded {len(all_comments)} comments from {len(list(BY_VIDEO_DIR.glob('*_comments.json')))} videos")
    if not all_comments:
        logger.warning("No comments to classify.")
        return COMMENTS_PROC_DIR
    return classify_and_save(all_comments)


# ── analysis stats ────────────────────────────────────────────────────────────
def write_analysis(classified_path: Path) -> None:
    from collections import Counter, defaultdict
    try:
        data = json.loads(classified_path.read_text(encoding="utf-8"))
    except Exception:
        return
    comments = data.get("classified_comments", [])
    if not comments:
        return

    labels   = [c.get("classification", "unknown") for c in comments]
    counts   = Counter(labels)
    total    = len(comments)
    divisor  = max(total, 1)
    by_month: dict = defaultdict(Counter)
    for c in comments:
        ds = (c.get("published_at") or c.get("time_relative") or "")[:7]
        if ds and len(ds) == 7:
            by_month[ds][c.get("classification", "unknown")] += 1

    # pro / anti breakdown
    stats = {
        "generated_at":     datetime.now(timezone.utc).isoformat(),
        "total":            total,
        "pro_bjp_count":    counts.get("pro-BJP",  0),
        "anti_bjp_count":   counts.get("anti-BJP", 0),
        "neutral_count":    counts.get("neutral",  0),
        "pro_bjp_pct":      round(100 * counts.get("pro-BJP",  0) / divisor, 1),
        "anti_bjp_pct":     round(100 * counts.get("anti-BJP", 0) / divisor, 1),
        "neutral_pct":      round(100 * counts.get("neutral",  0) / divisor, 1),
        "by_month":         {k: dict(v) for k, v in sorted(by_month.items())},
        "videos_scraped":   len(list(BY_VIDEO_DIR.glob("*_comments.json"))),
    }

    out = ANALYSIS_DIR / "comment_sentiment_distribution.json"
    out.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Analysis written → {out}")

    # print summary
    logger.info(
        f"Comments: total={total} "
        f"pro-BJP={stats['pro_bjp_count']} ({stats['pro_bjp_pct']}%) "
        f"anti-BJP={stats['anti_bjp_count']} ({stats['anti_bjp_pct']}%) "
        f"neutral={stats['neutral_count']} ({stats['neutral_pct']}%)"
    )


# ── stats display ─────────────────────────────────────────────────────────────
def print_stats() -> None:
    scraped = list(BY_VIDEO_DIR.glob("*_comments.json"))
    total_scraped = len(scraped)
    total_comments = 0
    for f in scraped:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            total_comments += d.get("total", 0)
        except Exception:
            pass

    classified_files = list(COMMENTS_PROC_DIR.glob("comments_classified_*.json"))
    classified_count = 0
    if classified_files:
        try:
            d = json.loads(max(classified_files).read_text(encoding="utf-8"))
            classified_count = d.get("total", 0)
        except Exception:
            pass

    print(f"\n=== Comment Collection Stats ===")
    print(f"  Videos scraped       : {total_scraped} / 831")
    print(f"  Total comments       : {total_comments}")
    print(f"  Classified comments  : {classified_count}")

    analysis = ANALYSIS_DIR / "comment_sentiment_distribution.json"
    if analysis.exists():
        try:
            s = json.loads(analysis.read_text(encoding="utf-8"))
            print(f"\n=== Sentiment (classified comments) ===")
            print(f"  pro-BJP  : {s['pro_bjp_count']:4d} ({s['pro_bjp_pct']}%)")
            print(f"  anti-BJP : {s['anti_bjp_count']:4d} ({s['anti_bjp_pct']}%)")
            print(f"  neutral  : {s['neutral_count']:4d} ({s['neutral_pct']}%)")
        except Exception:
            pass


# ── main orchestrator ──────────────────────────────────────────────────────────
def run(
    video_urls: Optional[list[str]] = None,
    max_videos: int = 831,
    max_per_video: int = 200,
    classify: bool = False,
    delay_min: float = 2.0,
    delay_max: float = 4.0,
    resume: bool = True,
) -> int:
    """
    Scrape comments for up to max_videos videos (priority-ordered).
    Returns total new comments collected.
    """
    if video_urls:
        videos = [{"url": u, "video_id": u.split("v=")[-1].split("&")[0],
                   "title": "", "channel": "", "upload_date": ""}
                  for u in video_urls]
    else:
        videos = load_videos_prioritised()

    # Respect max_videos cap
    videos = videos[:max_videos]
    logger.info(f"Processing {len(videos)} videos (max_per_video={max_per_video})")

    total_new  = 0
    batch_comments: list[dict] = []
    batch_size = 25   # classify + write raw every N videos

    for i, vid in enumerate(videos, 1):
        vid_id = vid.get("video_id") or vid.get("url", "").split("v=")[-1].split("&")[0]
        url    = vid.get("url") or f"https://www.youtube.com/watch?v={vid_id}"

        if resume and _already_scraped(vid_id):
            logger.debug(f"  [{i}/{len(videos)}] SKIP (already scraped): {vid_id}")
            continue

        logger.info(
            f"  [{i}/{len(videos)}] {vid_id} | "
            f"views={vid.get('views',0):,} | {vid.get('title','')[:50]}"
        )

        comments = fetch_comments(url, max_per_video, vid)
        if not comments:
            # save empty file so we skip on resume
            save_per_video(vid_id, [])
            time.sleep(delay_min)
            continue

        save_per_video(vid_id, comments)
        append_to_daily_raw(comments)
        batch_comments.extend(comments)
        total_new += len(comments)

        # classify + flush every batch_size videos
        if classify and len(batch_comments) >= batch_size * max_per_video:
            classify_and_save(batch_comments)
            batch_comments = []

        time.sleep(random.uniform(delay_min, delay_max))

    # classify any remaining batch
    if classify and batch_comments:
        classify_and_save(batch_comments)

    logger.info(f"\nDone. New comments collected: {total_new}")

    if classify:
        classified_path = max(COMMENTS_PROC_DIR.glob("comments_classified_*.json"),
                              default=None)
        if classified_path:
            write_analysis(classified_path)

    return total_new


# ── entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                _REPO / "logs" / "youtube_comments.log",
                encoding="utf-8",
            ),
        ],
    )

    parser = argparse.ArgumentParser(description="Gorakhpur YouTube comment scraper")
    parser.add_argument("--video",     type=str,  default=None,
                        help="Single video URL")
    parser.add_argument("--max-videos", type=int, default=831,
                        help="Max videos to scrape (default: all 831)")
    parser.add_argument("--max-per-video", type=int, default=200,
                        help="Max comments per video (default: 200)")
    parser.add_argument("--classify",  action="store_true",
                        help="Classify comments after fetching")
    parser.add_argument("--classify-existing", action="store_true",
                        help="Classify already-fetched comments without scraping")
    parser.add_argument("--stats",     action="store_true",
                        help="Show collection statistics")
    parser.add_argument("--no-resume", action="store_true",
                        help="Re-scrape even already-scraped videos")
    args = parser.parse_args()

    if args.stats:
        print_stats()

    elif args.classify_existing:
        path = classify_existing()
        write_analysis(path)
        print_stats()

    else:
        urls = [args.video] if args.video else None
        total = run(
            video_urls=urls,
            max_videos=args.max_videos,
            max_per_video=args.max_per_video,
            classify=args.classify,
            resume=not args.no_resume,
        )
        print(f"\nDone. {total} new comments collected.")
        if args.classify:
            print_stats()
