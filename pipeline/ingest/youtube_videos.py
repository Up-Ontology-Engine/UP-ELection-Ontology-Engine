"""
YouTube video metadata scraper for Gorakhpur political content — last 10 years.

Uses yt-dlp (no API key required) as primary method.
Falls back to YouTube Data API v3 if YOUTUBE_API_KEY env var is set.

Usage:
    python -m ingestion.youtube_videos                  # scrape + save JSON
    python -m ingestion.youtube_videos --dry-run        # print sample, no save
    python -m ingestion.youtube_videos --classify       # scrape + classify
    python -m ingestion.youtube_videos --years 5        # last 5 years instead of 10
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

logger = logging.getLogger(__name__)

# ── directories (resolved relative to repo root) ─────────────────────────────
_BASE = Path(__file__).resolve().parents[1] / "data" / "Digital_Dataset" / "Youtube"
VIDEOS_RAW_DIR = _BASE / "videos" / "raw"
VIDEOS_PROC_DIR = _BASE / "videos" / "processed"
VIDEOS_META_DIR = _BASE / "videos" / "metadata"
COMMENTS_RAW_DIR = _BASE / "comments" / "raw"
COMMENTS_PROC_DIR = _BASE / "comments" / "processed"
COMMENTS_BY_VID_DIR = _BASE / "comments" / "by_video"
ANALYSIS_DIR = _BASE / "analysis"
CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "yt_cache"

for _d in (
    VIDEOS_RAW_DIR,
    VIDEOS_PROC_DIR,
    VIDEOS_META_DIR,
    COMMENTS_RAW_DIR,
    COMMENTS_PROC_DIR,
    COMMENTS_BY_VID_DIR,
    ANALYSIS_DIR,
    CACHE_DIR,
):
    _d.mkdir(parents=True, exist_ok=True)

# ── search configuration ──────────────────────────────────────────────────────
SEARCH_QUERIES: list[str] = [
    # Hindi queries
    "गोरखपुर चुनाव",
    "गोरखपुर विधानसभा",
    "गोरखपुर BJP",
    "गोरखपुर समाजवादी पार्टी",
    "गोरखपुर राजनीति",
    "गोरखपुर विकास",
    "गोरखपुर news",
    "गोरखपुर election 2022",
    "गोरखपुर election 2017",
    "योगी आदित्यनाथ गोरखपुर",
    # English queries
    "Gorakhpur election news",
    "Gorakhpur BJP SP news",
    "Gorakhpur Urban Assembly election",
    "Gorakhpur politics",
    "Gorakhpur development BJP",
    "Gorakhpur Yogi Adityanath",
    "Gorakhpur Vidhan Sabha",
    "Gorakhpur UP election 2022",
    "Gorakhpur UP election 2017",
    "Gorakhpur news Hindi",
]


# Map of year → published_after for yt-dlp date filters
def _date_filter(years_back: int) -> str:
    """Return yt-dlp dateafter string (YYYYMMDD) for N years ago."""
    from datetime import date

    cutoff = date.today().replace(year=date.today().year - years_back)
    return cutoff.strftime("%Y%m%d")


# ── yt-dlp helpers ────────────────────────────────────────────────────────────
def _build_ydl_opts(query: str, dateafter: str, max_results: int = 50) -> dict:
    return {
        "quiet": True,
        "no_warnings": True,
        # Do NOT use extract_flat — we need upload_date from per-video metadata.
        # yt-dlp fetches each search result individually which is slower but gives
        # complete metadata (upload_date, view_count, like_count, tags, etc.).
        "skip_download": True,
        "playlistend": max_results,
        "dateafter": dateafter,
        "default_search": f"ytsearch{max_results}",
        "ignoreerrors": True,
        "writethumbnail": False,
        "writesubtitles": False,
        "writeautomaticsub": False,
    }


def _extract_video_meta(entry: dict) -> dict | None:
    """Normalise a yt-dlp flat-playlist entry into our schema."""
    vid_id = entry.get("id") or entry.get("url", "").split("v=")[-1].split("&")[0]
    if not vid_id:
        return None

    upload_raw = entry.get("upload_date") or ""  # "YYYYMMDD" or ""
    published_at: str | None = None
    if len(upload_raw) == 8:
        try:
            dt = datetime.strptime(upload_raw, "%Y%m%d").replace(tzinfo=timezone.utc)
            published_at = dt.isoformat()
        except ValueError:
            pass

    content = f"{entry.get('title', '')} {entry.get('description', '')}"
    content_hash = hashlib.sha256(content.encode()).hexdigest()

    return {
        "video_id": vid_id,
        "title": entry.get("title", ""),
        "description": (entry.get("description") or "")[:2000],
        "channel": entry.get("uploader") or entry.get("channel", ""),
        "channel_id": entry.get("uploader_id") or entry.get("channel_id", ""),
        "upload_date": published_at,
        "views": entry.get("view_count") or 0,
        "likes": entry.get("like_count") or 0,
        "comment_count": entry.get("comment_count") or 0,
        "duration": entry.get("duration") or 0,
        "url": f"https://www.youtube.com/watch?v={vid_id}",
        "thumbnail": entry.get("thumbnail", ""),
        "tags": entry.get("tags") or [],
        "category": entry.get("categories", [""])[0] if entry.get("categories") else "",
        "transcript": "",  # filled in full-fetch mode
        "content_hash": content_hash,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "query_source": entry.get("_query", ""),
    }


def search_videos_ytdlp(query: str, dateafter: str, max_results: int = 50) -> list[dict]:
    """Search YouTube for *query* using yt-dlp and return normalised video dicts."""
    try:
        import yt_dlp
    except ImportError:
        logger.error("yt-dlp not installed. Run: pip install yt-dlp")
        return []

    cache_key = hashlib.md5(f"{query}|{dateafter}|{max_results}".encode()).hexdigest()
    cache_file = CACHE_DIR / f"search_{cache_key}.json"
    if cache_file.exists():
        logger.info(f"Cache hit for query: {query!r}")
        with open(cache_file, encoding="utf-8") as f:
            return json.load(f)

    opts = _build_ydl_opts(query, dateafter, max_results)
    videos: list[dict] = []

    logger.info(f"Searching: {query!r}  (after {dateafter})")
    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            result = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
        except Exception as exc:
            logger.warning(f"yt-dlp search failed [{query!r}]: {exc}")
            return []

    entries = result.get("entries") or []
    for entry in entries:
        if not entry:
            continue
        entry["_query"] = query
        meta = _extract_video_meta(entry)
        if meta:
            videos.append(meta)

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)

    logger.info(f"  → {len(videos)} videos found")
    time.sleep(random.uniform(2, 5))
    return videos


def fetch_full_video_meta(video_id: str) -> dict | None:
    """Fetch full metadata (description, transcript) for a single video."""
    try:
        import yt_dlp
    except ImportError:
        return None

    cache_file = CACHE_DIR / f"video_{video_id}.json"
    if cache_file.exists():
        with open(cache_file, encoding="utf-8") as f:
            return json.load(f)

    opts = {
        "quiet": True,
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["hi", "en"],
        "ignoreerrors": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
        except Exception as exc:
            logger.warning(f"Full fetch failed [{video_id}]: {exc}")
            return None

    if not info:
        return None

    # Try to pull auto-generated transcript text
    transcript = ""
    subs = info.get("subtitles") or {}
    auto_subs = info.get("automatic_captions") or {}
    for lang in ("hi", "en"):
        for sub_dict in (subs, auto_subs):
            if lang in sub_dict:
                for fmt in sub_dict[lang]:
                    if fmt.get("ext") in ("vtt", "json3", "srv3"):
                        transcript = fmt.get("url", "")
                        break
            if transcript:
                break
        if transcript:
            break

    info["_query"] = info.get("_query", "")
    meta = _extract_video_meta(info)
    if meta:
        meta["transcript"] = transcript

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    time.sleep(random.uniform(1, 3))
    return meta


# ── YouTube Data API v3 fallback ──────────────────────────────────────────────
def search_videos_api(
    query: str, published_after: str, api_key: str, max_results: int = 50
) -> list[dict]:
    """Search using YouTube Data API v3. published_after in RFC-3339 format."""
    import requests

    base = "https://www.googleapis.com/youtube/v3/search"
    videos: list[dict] = []
    page_token: str | None = None

    while len(videos) < max_results:
        params: dict = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": min(50, max_results - len(videos)),
            "publishedAfter": published_after,
            "relevanceLanguage": "hi",
            "key": api_key,
        }
        if page_token:
            params["pageToken"] = page_token

        try:
            resp = requests.get(base, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning(f"API search failed [{query!r}]: {exc}")
            break

        for item in data.get("items", []):
            vid_id = item["id"].get("videoId", "")
            snip = item.get("snippet", {})
            pub = snip.get("publishedAt", "")
            videos.append(
                {
                    "video_id": vid_id,
                    "title": snip.get("title", ""),
                    "description": snip.get("description", "")[:2000],
                    "channel": snip.get("channelTitle", ""),
                    "channel_id": snip.get("channelId", ""),
                    "upload_date": pub,
                    "views": 0,
                    "likes": 0,
                    "comment_count": 0,
                    "duration": 0,
                    "url": f"https://www.youtube.com/watch?v={vid_id}",
                    "thumbnail": snip.get("thumbnails", {}).get("high", {}).get("url", ""),
                    "tags": [],
                    "category": "",
                    "transcript": "",
                    "content_hash": hashlib.sha256(f"{snip.get('title','')}".encode()).hexdigest(),
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                    "query_source": query,
                }
            )

        page_token = data.get("nextPageToken")
        if not page_token:
            break
        time.sleep(random.uniform(1, 2))

    logger.info(f"API search [{query!r}]: {len(videos)} videos")
    return videos


# ── deduplication ─────────────────────────────────────────────────────────────
def _dedup(videos: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for v in videos:
        vid_id = v.get("video_id", "")
        if vid_id and vid_id not in seen:
            seen.add(vid_id)
            out.append(v)
    return out


# ── main scrape orchestrator ──────────────────────────────────────────────────
def scrape_all_videos(
    years_back: int = 10, max_per_query: int = 50, dry_run: bool = False
) -> list[dict]:
    """
    Search all SEARCH_QUERIES for videos published in the last *years_back* years.
    Returns deduplicated list of video metadata dicts.
    """
    api_key = os.environ.get("YOUTUBE_API_KEY", "")
    dateafter = _date_filter(years_back)

    # RFC-3339 for API path
    cutoff_dt = datetime.strptime(dateafter, "%Y%m%d").replace(tzinfo=timezone.utc)
    published_after_rfc = cutoff_dt.isoformat()

    all_videos: list[dict] = []

    for query in SEARCH_QUERIES:
        if api_key:
            results = search_videos_api(query, published_after_rfc, api_key, max_per_query)
        else:
            results = search_videos_ytdlp(query, dateafter, max_per_query)

        all_videos.extend(results)

        if dry_run and len(all_videos) >= 5:
            logger.info("Dry-run: stopping after first batch sample.")
            break

    deduped = _dedup(all_videos)
    logger.info(f"Total unique videos collected: {len(deduped)}")
    return deduped


# ── persistence ───────────────────────────────────────────────────────────────
def save_raw(videos: list[dict]) -> Path:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_path = VIDEOS_RAW_DIR / f"videos_{today}.json"

    existing: list[dict] = []
    if out_path.exists():
        with open(out_path, encoding="utf-8") as f:
            existing = json.load(f).get("videos", [])

    merged = _dedup(existing + videos)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "total": len(merged),
                "videos": merged,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    logger.info(f"Saved {len(merged)} videos → {out_path}")
    return out_path


def update_index(videos: list[dict]) -> Path:
    """Maintain a persistent video_index.json with all-time deduplicated records."""
    index_path = VIDEOS_META_DIR / "video_index.json"
    existing: list[dict] = []
    if index_path.exists():
        with open(index_path, encoding="utf-8") as f:
            existing = json.load(f).get("videos", [])

    merged = _dedup(existing + videos)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "total": len(merged),
                "videos": merged,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    logger.info(f"Index updated → {index_path}  ({len(merged)} total)")
    return index_path


# ── classify existing raw data (no re-scrape) ────────────────────────────────
def classify_existing_raw(dry_run: bool = False) -> list[dict]:
    """
    Read all videos from VIDEOS_RAW_DIR JSON files and classify them,
    saving output to VIDEOS_PROC_DIR. No network calls.
    """
    all_videos: list[dict] = []
    for f in sorted(VIDEOS_RAW_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            all_videos.extend(data.get("videos", []))
        except Exception as exc:
            logger.warning(f"Could not read {f}: {exc}")

    videos = _dedup(all_videos)
    logger.info(f"Loaded {len(videos)} unique videos from raw files")

    if dry_run:
        for v in videos[:3]:
            logger.info(f"  DRY-RUN: {v['title'][:70]}")
        return videos

    try:
        from ingestion.classifier import classify_videos

        processed = classify_videos(videos, use_zeroshot=False)
    except Exception as exc:
        logger.error(f"Classification failed: {exc}")
        return []

    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_path = VIDEOS_PROC_DIR / f"videos_classified_{today}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "classified_at": datetime.now(timezone.utc).isoformat(),
                "total": len(processed),
                "videos": processed,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    logger.info(f"Classified {len(processed)} videos → {out_path}")
    return processed


# ── entry point ───────────────────────────────────────────────────────────────
def run(
    years_back: int = 10, max_per_query: int = 50, dry_run: bool = False, classify: bool = False
) -> list[dict]:
    videos = scrape_all_videos(years_back=years_back, max_per_query=max_per_query, dry_run=dry_run)
    if dry_run:
        for v in videos[:3]:
            logger.info(f"  DRY-RUN sample: [{v['upload_date']}] {v['title'][:70]}")
        return videos

    save_raw(videos)
    update_index(videos)

    if classify:
        try:
            from ingestion.classifier import classify_videos

            processed = classify_videos(videos)
            today = datetime.now(timezone.utc).strftime("%Y%m%d")
            out_path = VIDEOS_PROC_DIR / f"videos_classified_{today}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "classified_at": datetime.now(timezone.utc).isoformat(),
                        "total": len(processed),
                        "videos": processed,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            logger.info(f"Classified {len(processed)} videos → {out_path}")
        except Exception as exc:
            logger.warning(f"Classification skipped: {exc}")

    return videos


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                Path(__file__).resolve().parents[1] / "logs" / "youtube_videos.log",
                encoding="utf-8",
            ),
        ],
    )
    parser = argparse.ArgumentParser(description="Gorakhpur YouTube video scraper")
    parser.add_argument(
        "--years", type=int, default=10, help="How many years back to scrape (default: 10)"
    )
    parser.add_argument(
        "--max", type=int, default=50, help="Max results per search query (default: 50)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Scrape one batch but do not save files"
    )
    parser.add_argument(
        "--classify",
        action="store_true",
        help="Run BJP/neutral/anti-BJP classification after scraping",
    )
    parser.add_argument(
        "--classify-existing",
        action="store_true",
        help="Classify already-scraped raw videos without re-scraping",
    )
    args = parser.parse_args()

    if args.classify_existing:
        results = classify_existing_raw(dry_run=args.dry_run)
        print(f"\nDone. {len(results)} videos classified.")
    else:
        results = run(
            years_back=args.years,
            max_per_query=args.max,
            dry_run=args.dry_run,
            classify=args.classify,
        )
        print(f"\nDone. {len(results)} unique videos collected.")
