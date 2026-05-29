#!/usr/bin/env python3
"""
Facebook scraper — Gorakhpur election & politics (2016–2026, 10 years)

Three modes (tried in order):
  1. Graph API  — set FACEBOOK_ACCESS_TOKEN in .env  (most reliable)
  2. Playwright — set FB_EMAIL + FB_PASSWORD in .env  (browser login)
  3. Archive    — searches Wayback Machine & Google cache (no auth needed)

Output:
  data/Digital_Dataset/meta/facebook_posts.json   ← master store
  data/Digital_Dataset/meta/by_page/<page>.json   ← per-page files
  data/Digital_Dataset/meta/manifest.json         ← run log

Run:
  python scripts/facebook_gorakhpur_scraper.py
  python scripts/facebook_gorakhpur_scraper.py --mode graph
  python scripts/facebook_gorakhpur_scraper.py --mode playwright
  python scripts/facebook_gorakhpur_scraper.py --mode archive
  python scripts/facebook_gorakhpur_scraper.py --limit 200
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT    = Path(__file__).parents[1]
OUT_DIR = ROOT / "data" / "Digital_Dataset" / "meta"
OUT_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "by_page").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(OUT_DIR / "scraper.log", mode="a", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

# ── .env loader ───────────────────────────────────────────────────────────────
def _load_env() -> None:
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"\''))
_load_env()

FB_TOKEN   = os.environ.get("FACEBOOK_ACCESS_TOKEN", "")
FB_EMAIL   = os.environ.get("FB_EMAIL", "")
FB_PASSWORD= os.environ.get("FB_PASSWORD", "")

# ── Target pages ──────────────────────────────────────────────────────────────
TARGET_PAGES = [
    # (fb_page_slug,             graph_api_id,     display_name)
    ("myogiadityanath",    "myogiadityanath",  "Yogi Adityanath"),
    ("BJP4UP",             "BJP4UP",           "BJP Uttar Pradesh"),
    ("AkhileshYadav",      "AkhileshYadav",    "Akhilesh Yadav"),
    ("SamajwadiParty",     "SamajwadiParty",   "Samajwadi Party"),
    ("uptak",              "uptak",            "UP Tak"),
    ("ABPGanga",           "ABPGanga",         "ABP Ganga"),
    ("ddnewsup",           "ddnewsup",         "DD News UP"),
    ("aajtak",             "aajtak",           "Aaj Tak"),
    ("ndtvindia",          "ndtvindia",        "NDTV India"),
]

# ── Gorakhpur relevance ───────────────────────────────────────────────────────
_KW = [
    "gorakhpur","gorakhnath","yogi adityanath","ravi kishan","bjp gorakhpur",
    "sp gorakhpur","bsp gorakhpur","gorakhpur constituency","gorakhpur seat",
    "gorakhpur mla","up election","vidhan sabha","lok sabha",
    "गोरखपुर","गोरखनाथ","योगी","रवि किशन","यूपी चुनाव","गोरखपुर शहर",
]

def _gorakhpur(text: str) -> tuple[bool, list[str]]:
    if not text:
        return False, []
    t = text.lower()
    hit = [k for k in _KW if k.lower() in t]
    return bool(hit), hit

# ── Normalise post ────────────────────────────────────────────────────────────
def _norm(raw: dict, page_slug: str, page_name: str, source: str) -> dict:
    text = (raw.get("text") or raw.get("message") or raw.get("story") or "").strip()
    rel, kws = _gorakhpur(text)
    dt = raw.get("time") or raw.get("created_time") or raw.get("date")
    if hasattr(dt, "isoformat"):
        dt = dt.isoformat()
    return {
        "post_id":           raw.get("post_id") or raw.get("id"),
        "page_id":           page_slug,
        "page_name":         page_name,
        "text":              text,
        "time":              dt,
        "likes":             raw.get("likes") or raw.get("like_count") or 0,
        "comments":          raw.get("comments") or raw.get("comments_count") or 0,
        "shares":            raw.get("shares") or raw.get("share_count") or 0,
        "reactions":         raw.get("reactions"),
        "image_url":         raw.get("image") or raw.get("full_picture"),
        "video_url":         raw.get("video") or raw.get("video_url"),
        "post_url":          raw.get("post_url") or raw.get("permalink_url"),
        "language_hint":     "hi" if re.search(r"[ऀ-ॿ]", text) else "en",
        "gorakhpur_relevant":rel,
        "matched_keywords":  kws,
        "source_mode":       source,
        "scraped_at":        datetime.now(timezone.utc).isoformat(),
    }

# ─────────────────────────────────────────────────────────────────────────────
# MODE 1: Facebook Graph API
# ─────────────────────────────────────────────────────────────────────────────

def scrape_graph(page_id: str, page_name: str, limit: int, since_year: int) -> list[dict]:
    """Use Graph API — requires FACEBOOK_ACCESS_TOKEN in .env"""
    import requests
    posts: list[dict] = []
    since_ts = int(datetime(since_year, 1, 1, tzinfo=timezone.utc).timestamp())
    url = f"https://graph.facebook.com/v19.0/{page_id}/posts"
    params = {
        "access_token": FB_TOKEN,
        "fields":       "id,message,story,created_time,likes.summary(true),comments.summary(true),shares,full_picture,permalink_url",
        "limit":        100,
        "since":        since_ts,
    }
    while url and len(posts) < limit:
        try:
            r = requests.get(url, params=params, timeout=20)
            data = r.json()
        except Exception as e:
            log.warning("Graph API error for %s: %s", page_id, e)
            break

        if "error" in data:
            log.warning("Graph API error: %s", data["error"].get("message"))
            break

        for item in data.get("data", []):
            posts.append(_norm(item, page_id, page_name, "graph_api"))
            if len(posts) >= limit:
                break

        url    = data.get("paging", {}).get("next")
        params = {}  # next URL already includes all params
        time.sleep(0.5)

    log.info("  graph: %s → %d posts", page_id, len(posts))
    return posts


# ─────────────────────────────────────────────────────────────────────────────
# MODE 2: Playwright browser login
# ─────────────────────────────────────────────────────────────────────────────

def scrape_playwright(page_slug: str, page_name: str, limit: int, since_year: int) -> list[dict]:
    """Login to Facebook and scrape timeline — requires FB_EMAIL + FB_PASSWORD in .env"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.warning("playwright not installed: pip install playwright && python -m playwright install chromium")
        return []

    posts: list[dict] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        page = ctx.new_page()

        # Login
        try:
            log.info("  Playwright: logging in as %s …", FB_EMAIL[:4] + "****")
            page.goto("https://www.facebook.com/login", timeout=30000)
            page.fill("#email", FB_EMAIL)
            page.fill("#pass", FB_PASSWORD)
            page.click('[name="login"]')
            page.wait_for_load_state("networkidle", timeout=20000)

            if "checkpoint" in page.url or "two_step" in page.url:
                log.warning("  2FA required — cannot continue automatically")
                browser.close()
                return []
        except Exception as e:
            log.warning("  Login failed: %s", e)
            browser.close()
            return []

        # Navigate to page timeline
        try:
            log.info("  Navigating to page: %s", page_slug)
            page.goto(f"https://www.facebook.com/{page_slug}", timeout=30000)
            page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception as e:
            log.warning("  Failed to navigate to %s: %s", page_slug, e)
            browser.close()
            return []

        # Scroll and extract posts
        seen_ids: set[str] = set()
        stale_rounds = 0

        while len(posts) < limit and stale_rounds < 5:
            # Extract visible posts
            items = page.query_selector_all('[data-ad-preview="message"], [data-pagelet*="FeedUnit"]')
            if not items:
                # Fallback: grab all role="article" elements
                items = page.query_selector_all('[role="article"]')

            before = len(posts)
            for item in items:
                try:
                    raw_text = item.inner_text()
                    if not raw_text.strip():
                        continue

                    # Try to extract a stable ID from the element
                    link_el = item.query_selector('a[href*="/posts/"], a[href*="story_fbid"]')
                    post_url = link_el.get_attribute("href") if link_el else None
                    post_id  = re.search(r"(\d{10,})", post_url or "")
                    post_id  = post_id.group(1) if post_id else f"pw_{hash(raw_text[:80])}"

                    if post_id in seen_ids:
                        continue
                    seen_ids.add(post_id)

                    posts.append(_norm({
                        "post_id":  post_id,
                        "text":     raw_text,
                        "post_url": post_url,
                    }, page_slug, page_name, "playwright"))

                    if len(posts) >= limit:
                        break
                except Exception:
                    continue

            if len(posts) == before:
                stale_rounds += 1
            else:
                stale_rounds = 0

            # Scroll for more
            page.evaluate("window.scrollBy(0, 2000)")
            time.sleep(1.5)

        browser.close()

    log.info("  playwright: %s → %d posts", page_slug, len(posts))
    return posts


# ─────────────────────────────────────────────────────────────────────────────
# MODE 3: Archive / public cache fallback
# ─────────────────────────────────────────────────────────────────────────────

ARCHIVE_QUERIES = [
    "site:facebook.com gorakhpur election",
    "site:facebook.com गोरखपुर चुनाव",
    "site:facebook.com yogi adityanath gorakhpur",
    "site:facebook.com gorakhpur vidhan sabha",
    "site:facebook.com gorakhpur BJP election",
    "site:facebook.com gorakhpur SP election",
    "site:facebook.com gorakhpur 2022 election",
    "site:facebook.com gorakhpur 2017 election",
    "site:facebook.com gorakhpur lok sabha 2024",
    "site:facebook.com ravi kishan gorakhpur",
]

def scrape_archive(limit: int, since_year: int) -> list[dict]:
    """
    Harvest Gorakhpur-relevant Facebook posts from Wayback Machine CDX API
    and DuckDuckGo search (public, no auth required).
    """
    import requests
    posts: list[dict] = []

    # ── Wayback Machine CDX API ────────────────────────────────────────────
    log.info("  Archive: querying Wayback Machine CDX API …")
    cdx_urls = [
        "https://web.archive.org/cdx/search/cdx?url=facebook.com/myogiadityanath/posts/*&output=json&limit=100&from=20160101&to=20261231&fl=original,timestamp,statuscode&filter=statuscode:200",
        "https://web.archive.org/cdx/search/cdx?url=facebook.com/BJP4UP/posts/*&output=json&limit=100&from=20160101&to=20261231&fl=original,timestamp,statuscode&filter=statuscode:200",
        "https://web.archive.org/cdx/search/cdx?url=facebook.com/AkhileshYadav/posts/*&output=json&limit=100&from=20160101&to=20261231&fl=original,timestamp,statuscode&filter=statuscode:200",
    ]

    seen_urls: set[str] = set()
    for cdx_url in cdx_urls:
        try:
            r = requests.get(cdx_url, timeout=20)
            rows = r.json()
            if not rows or len(rows) < 2:
                continue
            # rows[0] is headers: [original, timestamp, statuscode]
            for row in rows[1:]:
                orig_url, ts, _ = row[0], row[1], row[2]
                if orig_url in seen_urls:
                    continue
                seen_urls.add(orig_url)

                # Parse timestamp YYYYMMDDHHMMSS → ISO
                try:
                    dt = datetime.strptime(ts[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
                    if not (since_year <= dt.year <= 2026):
                        continue
                    dt_iso = dt.isoformat()
                except Exception:
                    dt_iso = None

                # Extract page name from URL
                m = re.search(r"facebook\.com/([^/]+)/posts/(\d+)", orig_url)
                if not m:
                    continue
                pg, post_num = m.group(1), m.group(2)
                page_name = next((n for s,_,n in TARGET_PAGES if s.lower() == pg.lower()), pg)

                post = {
                    "post_id":           f"wb_{pg}_{post_num}",
                    "page_id":           pg,
                    "page_name":         page_name,
                    "text":              "",          # no content without fetching each URL
                    "time":              dt_iso,
                    "likes":             0,
                    "comments":          0,
                    "shares":            0,
                    "reactions":         None,
                    "image_url":         None,
                    "video_url":         None,
                    "post_url":          f"https://www.facebook.com/{pg}/posts/{post_num}",
                    "wayback_url":       f"https://web.archive.org/web/{ts}/{orig_url}",
                    "language_hint":     "hi",
                    "gorakhpur_relevant":True,  # assumed relevant (scraped from targeted pages)
                    "matched_keywords":  ["gorakhpur"],
                    "source_mode":       "wayback_cdx",
                    "scraped_at":        datetime.now(timezone.utc).isoformat(),
                }
                posts.append(post)

                if len(posts) >= limit // 2:
                    break

        except Exception as e:
            log.warning("  CDX query failed: %s", e)
        time.sleep(1)

    log.info("  Archive (CDX): %d post URLs found", len(posts))

    # ── Fetch Wayback-cached content for top posts ─────────────────────────
    fetched = 0
    for post in posts[:50]:  # Fetch text for up to 50 archived snapshots
        wb_url = post.get("wayback_url")
        if not wb_url:
            continue
        try:
            r = requests.get(wb_url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.text, "html.parser")
            # Try to extract post text from archived HTML
            for sel in ['[data-testid="post_message"]', 'div[dir="auto"]',
                        '.userContent', 'p', 'span']:
                els = soup.select(sel)
                texts = [e.get_text(" ", strip=True) for e in els if len(e.get_text(strip=True)) > 30]
                if texts:
                    combined = " | ".join(texts[:3])
                    post["text"] = combined[:500]
                    rel, kws = _gorakhpur(combined)
                    post["gorakhpur_relevant"] = rel or post["gorakhpur_relevant"]
                    post["matched_keywords"]   = list(set(post["matched_keywords"] + kws))
                    fetched += 1
                    break
        except Exception:
            pass
        time.sleep(0.5)

    log.info("  Archive (CDX fetch): content retrieved for %d posts", fetched)

    # ── DuckDuckGo HTML search for additional references ──────────────────
    log.info("  Archive: searching DuckDuckGo for Facebook content …")
    try:
        import requests
        from bs4 import BeautifulSoup

        ddg_queries = [
            "site:facebook.com gorakhpur election yogi 2022",
            "site:facebook.com gorakhpur BJP SP election 2017 2022",
        ]
        for q in ddg_queries:
            if len(posts) >= limit:
                break
            try:
                r = requests.get(
                    "https://html.duckduckgo.com/html/",
                    params={"q": q, "kl": "in-en"},
                    headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US"},
                    timeout=15,
                )
                soup = BeautifulSoup(r.text, "html.parser")
                for result in soup.select(".result__body")[:20]:
                    link_el  = result.select_one(".result__url")
                    snip_el  = result.select_one(".result__snippet")
                    title_el = result.select_one(".result__title")
                    url_raw  = link_el.text.strip() if link_el else ""
                    snippet  = snip_el.text.strip() if snip_el else ""
                    title    = title_el.text.strip() if title_el else ""

                    if "facebook.com" not in url_raw.lower():
                        continue

                    text = f"{title}. {snippet}".strip()
                    rel, kws = _gorakhpur(text)

                    post_id = f"ddg_{abs(hash(url_raw))}"
                    if any(p["post_id"] == post_id for p in posts):
                        continue

                    posts.append({
                        "post_id":           post_id,
                        "page_id":           re.search(r"facebook\.com/([^/?]+)", url_raw or "").group(1) if re.search(r"facebook\.com/([^/?]+)", url_raw or "") else "unknown",
                        "page_name":         "Facebook (search result)",
                        "text":              text,
                        "time":              None,
                        "likes":             0, "comments": 0, "shares": 0,
                        "reactions":         None,
                        "image_url":         None, "video_url": None,
                        "post_url":          url_raw,
                        "language_hint":     "hi" if re.search(r"[ऀ-ॿ]", text) else "en",
                        "gorakhpur_relevant": rel,
                        "matched_keywords":  kws,
                        "source_mode":       "ddg_search",
                        "scraped_at":        datetime.now(timezone.utc).isoformat(),
                    })

            except Exception as e:
                log.warning("  DuckDuckGo query failed: %s", e)
            time.sleep(1.5)

    except Exception as e:
        log.warning("  DuckDuckGo search failed: %s", e)

    log.info("  Archive total: %d records", len(posts))
    return posts


# ── Save helpers ──────────────────────────────────────────────────────────────
def _save_page_file(page_id: str, posts: list[dict]) -> None:
    path = OUT_DIR / "by_page" / f"{page_id}_posts.json"
    path.write_text(
        json.dumps({"page_id": page_id, "count": len(posts), "posts": posts},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _merge_master(new_posts: list[dict]) -> int:
    master = OUT_DIR / "facebook_posts.json"
    existing: dict[str, dict] = {}
    if master.exists():
        try:
            d = json.loads(master.read_text(encoding="utf-8"))
            for p in (d if isinstance(d, list) else d.get("posts", [])):
                if p.get("post_id"):
                    existing[p["post_id"]] = p
        except Exception:
            pass

    for p in new_posts:
        if p.get("post_id"):
            existing[p["post_id"]] = p

    merged = sorted(existing.values(), key=lambda p: p.get("time") or "", reverse=True)

    master.write_text(
        json.dumps({
            "_schema_version": "1.1",
            "dataset":         "gorakhpur_facebook_posts",
            "description":     "Facebook posts related to Gorakhpur elections & politics (2016–2026)",
            "year_range":      [2016, 2026],
            "total_posts":     len(merged),
            "gorakhpur_relevant_posts": sum(1 for p in merged if p.get("gorakhpur_relevant")),
            "sources_used":    list({p.get("source_mode","unknown") for p in merged}),
            "last_updated":    datetime.now(timezone.utc).isoformat(),
            "posts":           merged,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return len(merged)


def _save_manifest(entries: list[dict]) -> None:
    path = OUT_DIR / "manifest.json"
    hist: list[dict] = []
    if path.exists():
        try:
            hist = json.loads(path.read_text())
        except Exception:
            pass
    hist.extend(entries)
    path.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode",   choices=["graph", "playwright", "archive", "auto"],
                        default="auto", help="Scrape mode (default: auto-detect)")
    parser.add_argument("--pages",  nargs="+", help="Restrict to specific page slugs")
    parser.add_argument("--limit",  type=int,  default=300, help="Max posts per page")
    parser.add_argument("--since",  type=int,  default=2016, help="Earliest year")
    parser.add_argument("--all",    action="store_true",
                        help="Keep all posts, not just Gorakhpur-relevant")
    args = parser.parse_args()

    # Detect best available mode
    mode = args.mode
    if mode == "auto":
        if FB_TOKEN:
            mode = "graph"
            log.info("Mode: graph (FACEBOOK_ACCESS_TOKEN detected)")
        elif FB_EMAIL and FB_PASSWORD:
            mode = "playwright"
            log.info("Mode: playwright (FB_EMAIL + FB_PASSWORD detected)")
        else:
            mode = "archive"
            log.info("Mode: archive (no credentials found — using Wayback Machine + search)")

    pages = TARGET_PAGES
    if args.pages:
        pages = [(s, g, n) for s, g, n in TARGET_PAGES if s in args.pages]
        if not pages:
            pages = [(p, p, p) for p in args.pages]

    all_posts: list[dict] = []
    run_log:   list[dict] = []

    if mode == "graph":
        for slug, graph_id, name in pages:
            t0 = time.time()
            posts = scrape_graph(graph_id, name, args.limit, args.since)
            if not args.all:
                posts = [p for p in posts if p["gorakhpur_relevant"]]
            _save_page_file(slug, posts)
            all_posts.extend(posts)
            run_log.append({"page": slug, "mode": "graph", "count": len(posts),
                             "elapsed_s": round(time.time() - t0, 1),
                             "at": datetime.now(timezone.utc).isoformat()})
            time.sleep(1)

    elif mode == "playwright":
        for slug, _, name in pages:
            t0 = time.time()
            posts = scrape_playwright(slug, name, args.limit, args.since)
            if not args.all:
                posts = [p for p in posts if p["gorakhpur_relevant"]]
            _save_page_file(slug, posts)
            all_posts.extend(posts)
            run_log.append({"page": slug, "mode": "playwright", "count": len(posts),
                             "elapsed_s": round(time.time() - t0, 1),
                             "at": datetime.now(timezone.utc).isoformat()})
            time.sleep(2)

    elif mode == "archive":
        t0 = time.time()
        posts = scrape_archive(args.limit * len(pages), args.since)
        if not args.all:
            posts = [p for p in posts if p["gorakhpur_relevant"]]
        _save_page_file("archive", posts)
        all_posts.extend(posts)
        run_log.append({"page": "archive", "mode": "archive", "count": len(posts),
                         "elapsed_s": round(time.time() - t0, 1),
                         "at": datetime.now(timezone.utc).isoformat()})

    total = _merge_master(all_posts)
    _save_manifest(run_log)

    log.info("═" * 60)
    log.info("Saved %d posts → %s/facebook_posts.json", total, OUT_DIR)

    # Print summary
    by_mode: dict[str, int] = {}
    for p in all_posts:
        m = p.get("source_mode", "?")
        by_mode[m] = by_mode.get(m, 0) + 1
    for m, c in sorted(by_mode.items()):
        log.info("  %-18s %d posts", m, c)
    log.info("  %-18s %d Gorakhpur-relevant",
             "→ relevant:", sum(1 for p in all_posts if p.get("gorakhpur_relevant")))

    if mode == "archive" and not all_posts:
        log.warning("")
        log.warning("No posts collected. To get full data, add to .env:")
        log.warning("  FACEBOOK_ACCESS_TOKEN=<your_token>  # https://developers.facebook.com")
        log.warning("  # OR")
        log.warning("  FB_EMAIL=your@email.com")
        log.warning("  FB_PASSWORD=yourpassword")


if __name__ == "__main__":
    main()
