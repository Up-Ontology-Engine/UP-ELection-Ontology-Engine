"""
Unit tests for the Jagran Gorakhpur news scraper.
Uses a static HTML fixture so no network calls are made.
"""

from __future__ import annotations

import hashlib
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup

from pipeline.ingest.news_scraper import (
    SOURCES,
    _absolute_url,
    scrape_source,
)

# ---------------------------------------------------------------------------
# Fixture — minimal Jagran listing page HTML
# ---------------------------------------------------------------------------

JAGRAN_LISTING_HTML = """
<html>
<body>
  <div class="jagran-story-card">
    <h2>गोरखपुर में सड़क निर्माण कार्य शुरू</h2>
    <a href="/uttar-pradesh/gorakhpur-city/news-gorakhpur-road-123.html">पढ़ें</a>
    <span class="date">06 मई 2026</span>
  </div>
  <div class="jagran-story-card">
    <h2>विधायक ने की बैठक, लोगों की सुनी समस्याएं</h2>
    <a href="https://www.jagran.com/uttar-pradesh/gorakhpur-city/news-mla-456.html">पढ़ें</a>
    <span class="date">05 मई 2026</span>
  </div>
  <div class="jagran-story-card">
    <!-- malformed card — no title or link -->
  </div>
</body>
</html>
"""

ARTICLE_BODY_HTML = """
<html>
<body>
  <script>var x = 1;</script>
  <nav>Navigation</nav>
  <p>गोरखपुर में सड़क निर्माण का काम तेज़ी से चल रहा है।</p>
  <p>जिलाधिकारी ने बताया कि परियोजना अगले माह पूरी होगी।</p>
  <footer>Footer content</footer>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_get(url: str) -> BeautifulSoup | None:
    if "gorakhpur-city.html" in url:
        return BeautifulSoup(JAGRAN_LISTING_HTML, "html.parser")
    return BeautifulSoup(ARTICLE_BODY_HTML, "html.parser")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_absolute_url_relative():
    assert _absolute_url("/foo/bar.html", "jagran") == "https://www.jagran.com/foo/bar.html"


def test_absolute_url_already_absolute():
    url = "https://www.jagran.com/foo/bar.html"
    assert _absolute_url(url, "jagran") == url


def test_jagran_source_config():
    jagran = next(s for s in SOURCES if s["name"] == "jagran")
    assert "gorakhpur-city" in jagran["url"]
    assert jagran["district_hint"] == "Gorakhpur"
    assert jagran["ac_hint"] == "Gorakhpur Urban"


def test_scrape_source_yields_articles():
    jagran = next(s for s in SOURCES if s["name"] == "jagran")

    with (
        patch("ingestion.news_scraper._get", side_effect=_fake_get),
        patch("ingestion.news_scraper._extract_body", return_value="sample body text"),
    ):
        articles = list(scrape_source(jagran))

    assert len(articles) == 2, "Should yield 2 valid cards (malformed card skipped)"


def test_scraped_article_fields():
    jagran = next(s for s in SOURCES if s["name"] == "jagran")

    with (
        patch("ingestion.news_scraper._get", side_effect=_fake_get),
        patch("ingestion.news_scraper._extract_body", return_value="sample body text"),
    ):
        articles = list(scrape_source(jagran))

    a = articles[0]
    assert a["source"] == "jagran"
    assert a["headline"] == "गोरखपुर में सड़क निर्माण कार्य शुरू"
    assert a["published_at"] == "06 मई 2026"
    assert a["district_hint"] == "Gorakhpur"
    assert a["ac_hint"] == "Gorakhpur Urban"
    assert a["url"].startswith("https://")


def test_content_hash_uniqueness():
    """Two different articles must produce different hashes."""
    bodies = [("headline A", "body A"), ("headline B", "body B")]
    hashes = {hashlib.sha256(f"{h} {b}".encode()).hexdigest() for h, b in bodies}
    assert len(hashes) == 2


def test_duplicate_run_does_not_double_insert():
    """load_to_postgres ON CONFLICT DO NOTHING — rowcount=0 on dupe."""
    from pipeline.ingest.news_scraper import load_to_postgres

    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
    engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    # Simulate DB returning rowcount=0 (conflict, no insert)
    execute_result = MagicMock()
    execute_result.rowcount = 0
    conn.execute.return_value = execute_result

    articles = [
        {
            "source": "jagran",
            "headline": "Test",
            "body_raw": "body",
            "url": "https://example.com/1",
            "published_at": None,
            "district_hint": "Gorakhpur",
            "ac_hint": "Gorakhpur Urban",
        }
    ]

    n = load_to_postgres(articles, engine)
    assert n == 0, "Duplicate insert should report 0 new rows"
