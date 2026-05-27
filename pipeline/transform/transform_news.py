"""
ETL: News articles CSV → news_articles table (pre-NLP staging)

Source:
  data/processed/Convert to xcel sheet/results-20260508043736 (3).csv
  Columns: URL, MobileURL, Date, Title

What happens here:
  1. Read CSV
  2. Normalise source name from URL domain
  3. Compute content_hash for dedup
  4. Insert into news_articles (body_raw = Title until full scrape adds it)
  5. Mark nlp_processed = False (NLP pipeline reads this later)

Run: python -m etl.transform_news
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "data"

CSV_PATH = DATA_DIR / "Convert to xcel sheet" / "results-20260508043736 (3).csv"

DOMAIN_TO_SOURCE: dict[str, str] = {
    "bhaskar.com": "dainik_bhaskar",
    "navbharattimes.indiatimes.com": "navbharat_times",
    "timesofindia.indiatimes.com": "times_of_india",
    "aninews.in": "ani",
    "indianexpress.com": "indian_express",
    "khaskhabar.com": "khas_khabar",
    "palpalindia.com": "palpal_india",
    "jagran.com": "jagran",
    "amarujala.com": "amar_ujala",
    "livehindustan.com": "live_hindustan",
    "ndtv.com": "ndtv",
    "thehindu.com": "the_hindu",
}

DEFAULT_SOURCE_WEIGHT: dict[str, float] = {
    "jagran": 0.8,
    "amar_ujala": 0.8,
    "navbharat_times": 0.75,
    "times_of_india": 0.75,
    "dainik_bhaskar": 0.7,
    "ndtv": 0.75,
    "ani": 0.7,
}


def _domain_to_source(url: str) -> str:
    try:
        host = urlparse(url).hostname or ""
        host = host.removeprefix("www.")
        for domain, name in DOMAIN_TO_SOURCE.items():
            if domain in host:
                return name
        return host.split(".")[0] if host else "unknown"
    except Exception:
        return "unknown"


def load_news_articles(engine: sa.Engine) -> int:
    if not CSV_PATH.exists():
        raise FileNotFoundError(str(CSV_PATH))

    df = pd.read_csv(CSV_PATH, dtype=str)
    df.columns = [c.strip() for c in df.columns]

    # Normalise
    df["URL"] = df["URL"].fillna("").str.strip()
    df["Title"] = df["Title"].fillna("").str.strip()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df[df["URL"].str.startswith("http") & (df["Title"].str.len() > 5)]

    inserted = 0
    with engine.connect() as conn:
        for _, row in df.iterrows():
            url = row["URL"]
            title = row["Title"]
            source = _domain_to_source(url)
            published = row["Date"] if pd.notna(row["Date"]) else None
            content_hash = hashlib.sha256((url + title).encode()).hexdigest()[:64]
            DEFAULT_SOURCE_WEIGHT.get(source, 0.6)

            try:
                conn.execute(
                    text("""
                        INSERT INTO news_articles
                            (source, headline, body_raw, url, published_at,
                             district_hint, ac_hint, content_hash)
                        VALUES
                            (:source, :headline, :body_raw, :url, :published_at,
                             'Gorakhpur', 'Gorakhpur Urban', :content_hash)
                        ON CONFLICT (url) DO NOTHING
                    """),
                    {
                        "source": source,
                        "headline": title,
                        "body_raw": title,  # body = title until full scrape enriches it
                        "url": url,
                        "published_at": published,
                        "content_hash": content_hash,
                    },
                )
                inserted += 1
            except Exception as e:
                logger.debug("Skipped %s: %s", url[:60], e)

        conn.commit()

    logger.info(
        "Inserted %d news articles into news_articles (from %d CSV rows)", inserted, len(df)
    )
    return inserted


def run():
    engine = sa.create_engine(os.environ["POSTGRES_URL"])
    load_news_articles(engine)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run()
