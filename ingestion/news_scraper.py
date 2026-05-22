"""
Scrape local Hindi news from Jagran and Amar Ujala — Gorakhpur section.
Usage: python -m ingestion.news_scraper [--validate] [--dry-run] [--json]
"""
from __future__ import annotations
import json, os, time, random, hashlib, logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
import requests
from bs4 import BeautifulSoup
import sqlalchemy as sa
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

_REPO = Path(__file__).resolve().parents[1]
NEWS_RAW_DIR      = _REPO / "data" / "Digital_Dataset" / "newspapers" / "raw"
NEWS_PROC_DIR     = _REPO / "data" / "Digital_Dataset" / "newspapers" / "processed"
NEWS_BY_SRC_DIR   = _REPO / "data" / "Digital_Dataset" / "newspapers" / "by_source"

for _d in (NEWS_RAW_DIR, NEWS_PROC_DIR, NEWS_BY_SRC_DIR):
    _d.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "hi-IN,hi;q=0.9,en-IN;q=0.8",
}

SOURCES: list[dict] = [
    {
        "name": "jagran",
        "url": "https://www.jagran.com/uttar-pradesh/gorakhpur-city.html",
        "article_selector": "div.jagran-story-card",
        "title_selector": "h2",
        "link_selector": "a",
        "date_selector": "span.date",
        "district_hint": "Gorakhpur",
        "ac_hint": "Gorakhpur Urban",
    },
    {
        "name": "amarujala",
        "url": "https://www.amarujala.com/uttar-pradesh/gorakhpur",
        "article_selector": "div.list-item",
        "title_selector": "h2",
        "link_selector": "a",
        "date_selector": "span.date-time",
        "district_hint": "Gorakhpur",
        "ac_hint": "Gorakhpur Urban",
    },
]


@retry(
    retry=retry_if_exception_type(requests.RequestException),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=False,
)
def _fetch(url: str) -> requests.Response:
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r


def _get(url: str) -> BeautifulSoup | None:
    time.sleep(random.uniform(2, 4))
    try:
        r = _fetch(url)
        r.encoding = "utf-8"
        return BeautifulSoup(r.text, "lxml")
    except Exception as e:
        logger.warning(f"GET failed {url}: {e}")
        return None


def _extract_body(url: str) -> str:
    """Try newspaper3k first, fallback to BeautifulSoup."""
    try:
        from newspaper import Article
        art = Article(url, language="hi")
        art.download()
        art.parse()
        if art.text:
            return art.text
    except Exception:
        pass

    soup = _get(url)
    if not soup:
        return ""
    for tag in soup(["script", "style", "nav", "footer", "aside"]):
        tag.decompose()
    paras = soup.find_all("p")
    return " ".join(p.get_text(strip=True) for p in paras)[:5000]


def _absolute_url(href: str, source_name: str) -> str:
    if href.startswith("http"):
        return href
    return f"https://www.{source_name}.com{href}"


def scrape_source(source: dict) -> Iterator[dict]:
    soup = _get(source["url"])
    if not soup:
        return

    for card in soup.select(source["article_selector"])[:30]:
        title_el = card.select_one(source["title_selector"])
        link_el  = card.select_one(source["link_selector"])
        date_el  = card.select_one(source["date_selector"])

        if not title_el or not link_el:
            continue

        title = title_el.get_text(strip=True)
        href  = _absolute_url(link_el.get("href", ""), source["name"])

        body = _extract_body(href)
        yield {
            "source": source["name"],
            "headline": title,
            "body_raw": body,
            "url": href,
            "published_at": date_el.get_text(strip=True) if date_el else None,
            "district_hint": source.get("district_hint", "Gorakhpur"),
            "ac_hint": source.get("ac_hint", "Gorakhpur Urban"),
        }


def load_to_postgres(articles: list[dict], engine: sa.Engine) -> int:
    loaded = 0
    with engine.connect() as conn:
        for a in articles:
            content = f"{a['headline']} {a['body_raw']}"
            h = hashlib.sha256(content.encode()).hexdigest()
            try:
                result = conn.execute(sa.text("""
                    INSERT INTO news_articles
                      (source, headline, body_raw, url, published_at,
                       district_hint, ac_hint, content_hash)
                    VALUES
                      (:src, :hl, :body, :url, :pub, :dist, :ac, :hash)
                    ON CONFLICT (url) DO NOTHING
                """), {
                    "src": a["source"], "hl": a["headline"], "body": a["body_raw"],
                    "url": a["url"], "pub": a.get("published_at"), "hash": h,
                    "dist": a.get("district_hint"), "ac": a.get("ac_hint"),
                })
                loaded += result.rowcount
            except Exception as e:
                logger.debug(f"Skip article: {e}")
        conn.commit()
    return loaded


def validate_scrape(engine: sa.Engine, source: str = "jagran") -> dict:
    """
    Check that recent rows for *source* have non-empty headlines and bodies,
    and that the duplicate-prevention constraint holds.
    Returns a dict with pass/fail flags for each check.
    """
    results: dict = {}
    with engine.connect() as conn:
        # 1. Total row count
        row = conn.execute(sa.text(
            "SELECT COUNT(*) FROM news_articles WHERE source = :src"
        ), {"src": source}).fetchone()
        total = row[0] if row else 0
        results["total_rows"] = total

        # 2. Rows with empty headline or body
        row = conn.execute(sa.text("""
            SELECT COUNT(*) FROM news_articles
            WHERE source = :src
              AND (headline IS NULL OR headline = ''
                   OR body_raw IS NULL OR body_raw = '')
        """), {"src": source}).fetchone()
        empty_count = row[0] if row else 0
        results["empty_content_count"] = empty_count
        results["content_ok"] = (empty_count == 0)

        # 3. URL uniqueness (should always be 0 if constraint holds)
        row = conn.execute(sa.text("""
            SELECT COUNT(*) FROM (
                SELECT url FROM news_articles
                WHERE source = :src
                GROUP BY url HAVING COUNT(*) > 1
            ) dupes
        """), {"src": source}).fetchone()
        dup_urls = row[0] if row else 0
        results["duplicate_urls"] = dup_urls
        results["no_duplicates"] = (dup_urls == 0)

        # 4. Date parse consistency — fraction with parseable published_at
        row = conn.execute(sa.text("""
            SELECT COUNT(*) FROM news_articles
            WHERE source = :src AND published_at IS NOT NULL
        """), {"src": source}).fetchone()
        dated = row[0] if row else 0
        results["rows_with_date"] = dated
        results["date_coverage_pct"] = round(100 * dated / total, 1) if total else 0

    results["all_checks_passed"] = (
        results["content_ok"] and results["no_duplicates"] and total > 0
    )
    return results


def save_articles_json(articles: list[dict]) -> Path:
    """Write raw scraped articles to newspapers/raw/articles_YYYYMMDD.json."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_path = NEWS_RAW_DIR / f"articles_{today}.json"
    existing: list[dict] = []
    if out_path.exists():
        with open(out_path, encoding="utf-8") as f:
            existing = json.load(f).get("articles", [])

    seen_urls = {a["url"] for a in existing}
    merged = existing + [a for a in articles if a["url"] not in seen_urls]
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "total":      len(merged),
                "articles":   merged,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    logger.info(f"Saved {len(merged)} articles → {out_path}")
    return out_path


def classify_and_save_json(articles: list[dict]) -> Path:
    """Classify articles and write to newspapers/processed/articles_classified_YYYYMMDD.json."""
    from ingestion.classifier import classify_articles
    classified = classify_articles(articles, use_zeroshot=False)
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_path = NEWS_PROC_DIR / f"articles_classified_{today}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "classified_at":       datetime.now(timezone.utc).isoformat(),
                "total":               len(classified),
                "classified_articles": classified,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    logger.info(f"Classified {len(classified)} articles → {out_path}")
    return out_path


def run(dry_run: bool = False, validate_only: bool = False,
        save_json: bool = False, classify: bool = False):
    pg_url = os.environ.get("POSTGRES_URL", "")
    engine: sa.Engine | None = None
    if pg_url and not dry_run and not save_json:
        try:
            engine = sa.create_engine(pg_url)
        except Exception as exc:
            logger.warning(f"PostgreSQL not available: {exc}")

    if validate_only:
        if engine is None:
            logger.error("--validate requires POSTGRES_URL")
            return
        for source in SOURCES:
            report = validate_scrape(engine, source["name"])
            logger.info(f"Validation [{source['name']}]: {report}")
        return

    all_articles: list[dict] = []
    for source in SOURCES:
        articles = list(scrape_source(source))
        logger.info(f"{source['name']}: scraped {len(articles)} articles")
        if dry_run:
            for a in articles[:3]:
                logger.info(f"  DRY-RUN sample — {a['headline'][:60]} | {a['url']}")
            continue
        all_articles.extend(articles)

    if dry_run:
        return

    if save_json or classify:
        save_articles_json(all_articles)

    if classify:
        classify_and_save_json(all_articles)

    if engine:
        total = 0
        for a in all_articles:
            total += load_to_postgres([a], engine)
        logger.info(f"News ingestion complete. Total new in DB: {total}")
    elif not save_json and not classify:
        logger.warning("No POSTGRES_URL set and --json not used — articles not saved.")

    logger.info(f"News ingestion complete. Total scraped: {len(all_articles)}")


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Gorakhpur news scraper")
    parser.add_argument("--dry-run",  action="store_true", help="Scrape but do not write")
    parser.add_argument("--validate", action="store_true", help="Run post-scrape validation only")
    parser.add_argument("--json",     action="store_true", help="Save raw articles to newspapers/raw/")
    parser.add_argument("--classify", action="store_true",
                        help="Classify articles and save to newspapers/processed/")
    args = parser.parse_args()
    run(dry_run=args.dry_run, validate_only=args.validate,
        save_json=args.json, classify=args.classify)
