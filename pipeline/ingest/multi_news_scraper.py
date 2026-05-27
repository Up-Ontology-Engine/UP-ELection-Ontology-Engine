"""
Multi-source Gorakhpur newspaper scraper — 12 sources, stdlib only.

Sources covered:
  Direct RSS  : Amar Ujala, News18 UP, Prabhat Khabar (Gorakhpur-specific)
  HTML+JSON   : Dainik Jagran, Live Hindustan (via __NEXT_DATA__)
  HTML scrape : Patrika Gorakhpur
  Google News : aggregates Bhaskar, Jagran, Hindustan, Amar Ujala, etc.
                (6 query variants covering general, election, BJP, development,
                 politics, Hindi)

Usage:
    python -m ingestion.multi_news_scraper              # scrape + save
    python -m ingestion.multi_news_scraper --classify   # scrape + classify
    python -m ingestion.multi_news_scraper --dry-run    # print sample only
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
import re
import time
import urllib.error
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── directory setup ───────────────────────────────────────────────────────────
_REPO = Path(__file__).resolve().parents[1]
NEWS_RAW_DIR = _REPO / "data" / "Digital_Dataset" / "newspapers" / "raw"
NEWS_PROC_DIR = _REPO / "data" / "Digital_Dataset" / "newspapers" / "processed"
NEWS_BY_SRC_DIR = _REPO / "data" / "Digital_Dataset" / "newspapers" / "by_source"
for _d in (NEWS_RAW_DIR, NEWS_PROC_DIR, NEWS_BY_SRC_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── source registry ───────────────────────────────────────────────────────────
SOURCES: list[dict] = [
    # ── Direct Gorakhpur RSS feeds ────────────────────────────────────────────
    {
        "id": "amarujala_gorakhpur",
        "display": "Amar Ujala — Gorakhpur",
        "type": "rss",
        "url": "https://www.amarujala.com/rss/gorakhpur.xml",
        "language": "hi",
        "bias_score": 0.1,
        "credibility": 0.8,
    },
    {
        "id": "news18_gorakhpur",
        "display": "News18 UP — Gorakhpur",
        "type": "rss",
        "url": "https://hindi.news18.com/commonfeeds/v1/hin/rss/uttarpradesh/gorakhpur.xml",
        "language": "hi",
        "bias_score": 0.2,
        "credibility": 0.75,
    },
    {
        "id": "prabhatkhabar_gorakhpur",
        "display": "Prabhat Khabar — Gorakhpur",
        "type": "rss",
        "url": "https://www.prabhatkhabar.com/state/uttar-pradesh/gorakhpur/feed",
        "language": "hi",
        "bias_score": 0.15,
        "credibility": 0.72,
    },
    # ── HTML / __NEXT_DATA__ sources ──────────────────────────────────────────
    {
        "id": "jagran_gorakhpur",
        "display": "Dainik Jagran — Gorakhpur",
        "type": "next_json",
        "url": "https://www.jagran.com/uttar-pradesh/gorakhpur",
        "language": "hi",
        "bias_score": 0.15,
        "credibility": 0.8,
        "article_key": "ARTICLE_LISTING_DATA",
        "title_field": "headline",
        "body_field": "summary",
        "date_field": "modDate",
        "url_template": "https://www.jagran.com/{category}/{subcategory}-gorakhpur-{webTitleUrl}-{id}.html",
    },
    {
        "id": "livehindustan_gorakhpur",
        "display": "Live Hindustan — Gorakhpur",
        "type": "next_json",
        "url": "https://www.livehindustan.com/uttar-pradesh/gorakhpur",
        "language": "hi",
        "bias_score": 0.1,
        "credibility": 0.78,
        "article_key": None,  # deep search
        "title_field": "headline",
        "body_field": "quickReadSummary",
        "date_field": "firstPublishedDate",
    },
    # ── HTML scrape ───────────────────────────────────────────────────────────
    {
        "id": "patrika_gorakhpur",
        "display": "Patrika — Gorakhpur",
        "type": "html",
        "url": "https://www.patrika.com/gorakhpur-news",
        "language": "hi",
        "bias_score": 0.1,
        "credibility": 0.7,
    },
    # ── Google News aggregated (multiple queries) ─────────────────────────────
    {
        "id": "google_news_general",
        "display": "Google News — Gorakhpur (general)",
        "type": "rss",
        "url": "https://news.google.com/rss/search?q=gorakhpur+news&hl=hi&gl=IN&ceid=IN:hi",
        "language": "hi",
        "bias_score": 0.0,
        "credibility": 0.9,
        "is_aggregator": True,
    },
    {
        "id": "google_news_election",
        "display": "Google News — Gorakhpur Election",
        "type": "rss",
        "url": "https://news.google.com/rss/search?q=gorakhpur+election+vidhansabha&hl=hi&gl=IN&ceid=IN:hi",
        "language": "hi",
        "bias_score": 0.0,
        "credibility": 0.9,
        "is_aggregator": True,
    },
    {
        "id": "google_news_bjp_sp",
        "display": "Google News — Gorakhpur BJP/SP",
        "type": "rss",
        "url": "https://news.google.com/rss/search?q=gorakhpur+BJP+SP+samajwadi&hl=hi&gl=IN&ceid=IN:hi",
        "language": "hi",
        "bias_score": 0.0,
        "credibility": 0.9,
        "is_aggregator": True,
    },
    {
        "id": "google_news_development",
        "display": "Google News — Gorakhpur Development",
        "type": "rss",
        "url": "https://news.google.com/rss/search?q=gorakhpur+vikas+yojana&hl=hi&gl=IN&ceid=IN:hi",
        "language": "hi",
        "bias_score": 0.0,
        "credibility": 0.9,
        "is_aggregator": True,
    },
    {
        "id": "google_news_politics",
        "display": "Google News — Gorakhpur Politics",
        "type": "rss",
        "url": "https://news.google.com/rss/search?q=gorakhpur+chunav+rajneeti&hl=hi&gl=IN&ceid=IN:hi",
        "language": "hi",
        "bias_score": 0.0,
        "credibility": 0.9,
        "is_aggregator": True,
    },
    {
        "id": "google_news_hindi",
        "display": "Google News — गोरखपुर समाचार (Hindi query)",
        "type": "rss",
        "url": "https://news.google.com/rss/search?q=%E0%A4%97%E0%A5%8B%E0%A4%B0%E0%A4%96%E0%A4%AA%E0%A5%81%E0%A4%B0+%E0%A4%B8%E0%A4%AE%E0%A4%BE%E0%A4%9A%E0%A4%BE%E0%A4%B0&hl=hi&gl=IN&ceid=IN:hi",
        "language": "hi",
        "bias_score": 0.0,
        "credibility": 0.9,
        "is_aggregator": True,
    },
]


# ── HTTP helper — stealth session with UA rotation ─────────────────────────────
# Uses scraper_stealth.StealthSession for rotating user-agents, randomised
# browser headers, jitter delays, and automatic 429/5xx retry.
try:
    from ingestion.scraper_stealth import StealthSession as _StealthSession

    _SESSION = _StealthSession(base_delay=1.5, jitter=0.8, max_retries=3)
    logger.info("[scraper] StealthSession loaded — UA rotation enabled.")
except ImportError:
    _SESSION = None
    logger.warning("[scraper] scraper_stealth not available — falling back to urllib.")


def _fetch_text(url: str, timeout: int = 15) -> str:
    """Fetch URL with stealth headers; falls back to plain urllib if unavailable."""
    if _SESSION:
        result = _SESSION.get(url, timeout=timeout)
        if result is not None:
            return result

    # Plain urllib fallback

    _FALLBACK_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "hi-IN,hi;q=0.9,en-IN;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    req = urllib.request.Request(url, headers=_FALLBACK_HEADERS)
    opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
    with opener.open(req, timeout=timeout) as resp:
        raw = resp.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


# ── CDATA / HTML entity cleanup ───────────────────────────────────────────────
def _clean(text: str) -> str:
    text = re.sub(r"<!\[CDATA\[|\]\]>", "", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


# ── article content hash ──────────────────────────────────────────────────────
def _content_hash(title: str, url: str) -> str:
    return hashlib.sha256(f"{title}|{url}".encode()).hexdigest()


# ── RSS parser ────────────────────────────────────────────────────────────────
def _parse_rss(xml_text: str, source: dict) -> list[dict]:
    items_raw = re.findall(r"<item>(.*?)</item>", xml_text, re.S)
    articles: list[dict] = []

    for raw in items_raw:

        def _tag(name: str) -> str:
            m = re.search(rf"<{name}[^>]*>(.*?)</{name}>", raw, re.S)
            return _clean(m.group(1)) if m else ""

        title = _tag("title")
        link = _tag("link") or _tag("guid")
        description = _tag("description")
        pub_date = _tag("pubDate")
        author = _tag("dc:creator") or _tag("author")
        category = _tag("category")

        # Google News source attribution
        src_m = re.search(r'<source[^>]+url="([^"]+)"[^>]*>(.*?)</source>', raw, re.S)
        publisher = _clean(src_m.group(2)) if src_m else source["display"]

        if not title or not link:
            continue
        if not link.startswith("http"):
            continue

        articles.append(
            {
                "source_id": source["id"],
                "source_name": publisher,
                "headline": title,
                "body_raw": description,
                "url": link,
                "published_at": pub_date,
                "author": author,
                "category": category,
                "language": source["language"],
                "district_hint": "Gorakhpur",
                "ac_hint": "Gorakhpur Urban",
                "credibility": source["credibility"],
                "bias_score": source["bias_score"],
                "content_hash": _content_hash(title, link),
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    return articles


# ── __NEXT_DATA__ parser (Jagran / Live Hindustan) ────────────────────────────
def _find_articles_in_json(obj: Any, depth: int = 0) -> list[dict]:
    if depth > 10:
        return []
    if isinstance(obj, list):
        results = []
        for item in obj:
            results.extend(_find_articles_in_json(item, depth + 1))
        return results
    if isinstance(obj, dict):
        headline = obj.get("headline") or obj.get("title")
        if (
            headline
            and isinstance(headline, str)
            and len(headline) > 8
            and obj.get("type") not in ("placeholder", "element", "ad")
        ):
            return [obj]
        results = []
        for v in obj.values():
            results.extend(_find_articles_in_json(v, depth + 1))
        return results
    return []


def _parse_next_json(html_text: str, source: dict) -> list[dict]:
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html_text, re.S
    )
    if not m:
        logger.warning(f"[{source['id']}] No __NEXT_DATA__ found")
        return []

    try:
        page_data = json.loads(m.group(1))
    except json.JSONDecodeError as exc:
        logger.warning(f"[{source['id']}] JSON parse error: {exc}")
        return []

    # Extract article URLs from <a> tags for URL reconstruction
    href_pattern = re.compile(
        r'href="(https?://(?:www\.jagran\.com|www\.livehindustan\.com)[^"]{15,200})"'
    )
    all_hrefs: set[str] = set(href_pattern.findall(html_text))

    raw_articles = _find_articles_in_json(page_data)
    articles: list[dict] = []
    seen_headlines: set[str] = set()

    for art in raw_articles:
        headline = art.get("headline") or art.get("title", "")
        if not headline or headline in seen_headlines:
            continue
        seen_headlines.add(headline)

        # Build URL for Jagran
        url = ""
        if source["id"] == "jagran_gorakhpur":
            slug = art.get("webTitleUrl", "")
            aid = art.get("id", "")
            cat = art.get("category", "news")
            subcat = art.get("subcategory", "state")
            if slug and aid:
                url = f"https://www.jagran.com/{cat}/{subcat}-gorakhpur-{slug}-{aid}.html"

        # For Hindustan, match headline substring against known hrefs
        if source["id"] == "livehindustan_gorakhpur" and not url:
            for href in all_hrefs:
                if "story-" in href and "gorakhpur" in href:
                    url = href
                    all_hrefs.discard(href)
                    break

        if not url:
            url = source["url"]

        body = art.get("summary") or art.get("quickReadSummary") or art.get("description", "")
        pub = art.get("firstPublishedDate") or art.get("modDate") or art.get("lastModifiedDate", "")
        city = art.get("city", "gorakhpur")

        # Only include Gorakhpur-tagged or Gorakhpur-mentioning articles
        combined = f"{headline} {body} {city}".lower()
        if "gorakhpur" not in combined and "गोरखपुर" not in combined:
            continue

        articles.append(
            {
                "source_id": source["id"],
                "source_name": source["display"],
                "headline": headline,
                "body_raw": _clean(str(body)) if body else "",
                "url": url,
                "published_at": pub,
                "author": "",
                "category": art.get("category", ""),
                "language": source["language"],
                "district_hint": "Gorakhpur",
                "ac_hint": "Gorakhpur Urban",
                "credibility": source["credibility"],
                "bias_score": source["bias_score"],
                "content_hash": _content_hash(headline, url),
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    return articles


# ── HTML scraper (Patrika) ────────────────────────────────────────────────────
def _parse_html(html_text: str, source: dict) -> list[dict]:
    articles: list[dict] = []

    # Strategy 1: h2/h3 tags with sibling links
    card_pattern = re.compile(
        r'<a[^>]+href="(https?://www\.patrika\.com/[^"]{15,200})"[^>]*>'
        r"[\s\S]{0,50}?<h[23][^>]*>([\s\S]{10,200}?)</h[23]>",
        re.S,
    )
    for m in card_pattern.finditer(html_text):
        link = m.group(1)
        title = _clean(m.group(2))
        if not title or len(title) < 8:
            continue
        articles.append(_make_article(source, title, "", link, ""))

    # Strategy 2: h2/h3 tags alone
    if not articles:
        for m in re.finditer(r"<h[23][^>]*>([\s\S]{10,200}?)</h[23]>", html_text, re.S):
            title = _clean(m.group(1))
            if title and len(title) > 8:
                articles.append(_make_article(source, title, "", source["url"], ""))

    # Deduplicate by headline
    seen: set[str] = set()
    unique = []
    for a in articles:
        key = a["headline"][:50]
        if key not in seen:
            seen.add(key)
            unique.append(a)

    return unique


def _make_article(source: dict, headline: str, body: str, url: str, pub: str) -> dict:
    return {
        "source_id": source["id"],
        "source_name": source["display"],
        "headline": headline,
        "body_raw": body,
        "url": url,
        "published_at": pub,
        "author": "",
        "category": "",
        "language": source["language"],
        "district_hint": "Gorakhpur",
        "ac_hint": "Gorakhpur Urban",
        "credibility": source["credibility"],
        "bias_score": source["bias_score"],
        "content_hash": _content_hash(headline, url),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


# ── per-source dispatcher ─────────────────────────────────────────────────────
def scrape_source(source: dict) -> list[dict]:
    logger.info(f"Scraping: {source['display']} ({source['type']}) ...")
    try:
        html = _fetch_text(source["url"])
    except Exception as exc:
        logger.warning(f"  FETCH FAILED [{source['id']}]: {exc}")
        return []

    if source["type"] == "rss":
        arts = _parse_rss(html, source)
    elif source["type"] == "next_json":
        arts = _parse_next_json(html, source)
    elif source["type"] == "html":
        arts = _parse_html(html, source)
    else:
        logger.warning(f"  Unknown type: {source['type']}")
        return []

    logger.info(f"  → {len(arts)} articles")
    return arts


# ── deduplication ─────────────────────────────────────────────────────────────
def _dedup(articles: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for a in articles:
        # prefer content_hash (title+url) as dedup key so listing-page URLs don't collapse everything
        key = a.get("content_hash") or a.get("url", "")
        if key and key not in seen:
            seen.add(key)
            out.append(a)
    return out


# ── save helpers ──────────────────────────────────────────────────────────────
def save_by_source(articles: list[dict]) -> None:
    by_src: dict[str, list[dict]] = {}
    for a in articles:
        by_src.setdefault(a["source_id"], []).append(a)

    for src_id, arts in by_src.items():
        out = NEWS_BY_SRC_DIR / f"{src_id}.json"
        existing: list[dict] = []
        if out.exists():
            try:
                existing = json.loads(out.read_text(encoding="utf-8")).get("articles", [])
            except Exception:
                pass
        merged = _dedup(existing + arts)
        out.write_text(
            json.dumps(
                {"source_id": src_id, "total": len(merged), "articles": merged},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        logger.info(f"  by_source/{src_id}.json → {len(merged)} articles")


def save_raw_combined(articles: list[dict]) -> Path:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_path = NEWS_RAW_DIR / f"articles_{today}.json"
    existing: list[dict] = []
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8")).get("articles", [])
        except Exception:
            pass
    merged = _dedup(existing + articles)
    out_path.write_text(
        json.dumps(
            {
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "total": len(merged),
                "sources_run": list({a["source_id"] for a in articles}),
                "articles": merged,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    logger.info(f"Combined raw: {out_path} ({len(merged)} articles)")
    return out_path


def classify_and_save(articles: list[dict]) -> Path:
    from ingestion.classifier import classify_articles

    classified = classify_articles(articles, use_zeroshot=False)
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_path = NEWS_PROC_DIR / f"articles_classified_{today}.json"
    out_path.write_text(
        json.dumps(
            {
                "classified_at": datetime.now(timezone.utc).isoformat(),
                "total": len(classified),
                "classified_articles": classified,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    logger.info(f"Classified: {out_path} ({len(classified)} articles)")
    return out_path


# ── orchestrator ──────────────────────────────────────────────────────────────
def run(
    dry_run: bool = False,
    classify: bool = False,
    sources: list[str] | None = None,
    delay: float = 1.5,
    incremental: bool = True,
) -> list[dict]:
    """
    Scrape all configured sources and persist new articles.

    Args:
        dry_run:     If True, print samples without saving or updating watermarks.
        classify:    If True, run NLP classifier after scraping.
        sources:     List of source IDs to restrict the run (default: all).
        delay:       Seconds to sleep between sources (politeness).
        incremental: If True (default), skip articles already ingested in a
                     previous run using the ingestion watermark from PostgreSQL.
    """
    # Import tracker lazily so the scraper still works without a DB connection.
    _tracker = None
    if incremental and not dry_run:
        try:
            from ingestion.ingestion_tracker import (
                filter_new_articles,
                init_ingestion_track_table,
                update_watermark,
            )

            init_ingestion_track_table()
            _tracker = (filter_new_articles, update_watermark)
        except Exception as exc:
            logger.warning(
                "[scraper] Incremental tracker unavailable (%s); doing full scrape.", exc
            )

    active_sources = [s for s in SOURCES if (sources is None or s["id"] in sources)]

    all_articles: list[dict] = []
    source_max_dts: dict[str, Any] = {}

    for i, source in enumerate(active_sources):
        arts = scrape_source(source)

        # ── incremental filter ──────────────────────────────────────────────
        if _tracker and arts:
            filter_fn, _ = _tracker
            arts, max_dt = filter_fn(source["id"], arts, dt_field="published_at")
            source_max_dts[source["id"]] = max_dt

        all_articles.extend(arts)
        if i < len(active_sources) - 1:
            time.sleep(delay)

    deduped = _dedup(all_articles)
    logger.info(f"\nTotal unique *new* articles: {len(deduped)}")

    if dry_run:
        for a in deduped[:6]:
            print(f"  [{a['source_name']}] {a['headline'][:80]}")
            print(f"    {a['url'][:90]}")
        return deduped

    save_by_source(deduped)
    save_raw_combined(deduped)

    # ── advance watermarks ──────────────────────────────────────────────────
    if _tracker:
        _, update_fn = _tracker
        # Group by source_id for count tracking
        by_src: dict[str, int] = {}
        for a in deduped:
            by_src[a["source_id"]] = by_src.get(a["source_id"], 0) + 1
        for src in active_sources:
            sid = src["id"]
            update_fn(
                sid,
                latest_article_at=source_max_dts.get(sid),
                ingested_count=by_src.get(sid, 0),
            )

    if classify:
        classify_and_save(deduped)

    return deduped


# ── entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
        handlers=[logging.StreamHandler()],
    )
    parser = argparse.ArgumentParser(description="Gorakhpur multi-source news scraper")
    parser.add_argument("--dry-run", action="store_true", help="Scrape but do not save")
    parser.add_argument("--classify", action="store_true", help="Classify after scraping")
    parser.add_argument("--sources", nargs="+", help="Source IDs to run (default: all)")
    parser.add_argument("--delay", type=float, default=1.5, help="Seconds between sources")
    parser.add_argument(
        "--no-incremental",
        action="store_true",
        help="Disable incremental mode and re-ingest all articles",
    )
    args = parser.parse_args()

    articles = run(
        dry_run=args.dry_run,
        classify=args.classify,
        sources=args.sources,
        delay=args.delay,
        incremental=not args.no_incremental,
    )
    print(f"\nDone. {len(articles)} unique new articles collected.")
    if articles:
        src_counts: dict[str, int] = {}
        for a in articles:
            src_counts[a["source_name"]] = src_counts.get(a["source_name"], 0) + 1
        print("\nBreakdown by source:")
        for src, cnt in sorted(src_counts.items(), key=lambda x: -x[1])[:15]:
            print(f"  {cnt:4d}  {src}")
