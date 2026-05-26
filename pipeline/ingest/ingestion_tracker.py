"""
Incremental ingestion tracker — prevents re-processing already-ingested articles.

Maintains a PostgreSQL table `ingestion_track` that records the latest article
timestamp seen per source.  Scrapers read this watermark before each run and
skip articles published at or before it, then update the watermark at the end.

Usage in a scraper:
    from ingestion.ingestion_tracker import get_watermark, update_watermark
    from datetime import timezone

    wm = get_watermark("jagran_gorakhpur")          # datetime | None
    articles = [a for a in all_articles
                if _parse_dt(a["published_at"]) > wm]  # filter old
    update_watermark("jagran_gorakhpur", max_dt)    # advance cursor
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Ensure project root is on sys.path when invoked directly
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


# ── DDL ──────────────────────────────────────────────────────────────────────

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS ingestion_track (
    source_id        TEXT        PRIMARY KEY,
    last_scraped_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_article_at  TIMESTAMPTZ,          -- latest article timestamp seen
    total_ingested   BIGINT      NOT NULL DEFAULT 0,
    notes            TEXT
);
"""


def init_ingestion_track_table() -> None:
    """Create the ingestion_track table if it doesn't exist."""
    from backend.db import get_pg_engine
    import sqlalchemy as sa

    try:
        engine = get_pg_engine()
        with engine.begin() as conn:
            conn.execute(sa.text(_CREATE_TABLE))
        logger.info("[ingestion_tracker] ingestion_track table ready.")
    except Exception as exc:
        logger.error("[ingestion_tracker] Failed to initialise table: %s", exc)


# ── Read watermark ────────────────────────────────────────────────────────────

def get_watermark(source_id: str) -> Optional[datetime]:
    """
    Return the timestamp of the most recently ingested article for *source_id*,
    or None if this source has never been tracked (= full scrape needed).
    """
    from backend.db import get_pg_engine
    import sqlalchemy as sa

    try:
        engine = get_pg_engine()
        with engine.connect() as conn:
            row = conn.execute(
                sa.text(
                    "SELECT last_article_at FROM ingestion_track WHERE source_id = :sid"
                ),
                {"sid": source_id},
            ).fetchone()
        if row and row[0]:
            ts = row[0]
            # Ensure timezone-aware
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            return ts
    except Exception as exc:
        logger.warning("[ingestion_tracker] get_watermark failed for %s: %s", source_id, exc)
    return None


# ── Update watermark ──────────────────────────────────────────────────────────

def update_watermark(
    source_id: str,
    latest_article_at: Optional[datetime],
    ingested_count: int = 0,
    notes: str | None = None,
) -> None:
    """
    Upsert the ingestion_track row for *source_id*.

    Args:
        source_id:         Unique source identifier (e.g. 'jagran_gorakhpur').
        latest_article_at: Timestamp of the newest article in this batch (UTC).
        ingested_count:    Number of new articles ingested this run.
        notes:             Optional free-text note (e.g. error details).
    """
    from backend.db import get_pg_engine
    import sqlalchemy as sa

    try:
        engine = get_pg_engine()
        with engine.begin() as conn:
            conn.execute(
                sa.text("""
                    INSERT INTO ingestion_track (source_id, last_scraped_at, last_article_at, total_ingested, notes)
                    VALUES (:sid, now(), :lat, :cnt, :notes)
                    ON CONFLICT (source_id) DO UPDATE SET
                        last_scraped_at  = now(),
                        last_article_at  = GREATEST(ingestion_track.last_article_at, EXCLUDED.last_article_at),
                        total_ingested   = ingestion_track.total_ingested + EXCLUDED.total_ingested,
                        notes            = EXCLUDED.notes
                """),
                {
                    "sid":   source_id,
                    "lat":   latest_article_at,
                    "cnt":   ingested_count,
                    "notes": notes,
                },
            )
        logger.info(
            "[ingestion_tracker] %s → watermark=%s (+%d articles)",
            source_id, latest_article_at, ingested_count,
        )
    except Exception as exc:
        logger.error("[ingestion_tracker] update_watermark failed for %s: %s", source_id, exc)


# ── Article datetime parser ───────────────────────────────────────────────────

def parse_article_dt(raw: str | None) -> Optional[datetime]:
    """
    Best-effort parse of the published_at field from various scrapers.
    Returns a timezone-aware datetime or None.
    """
    if not raw:
        return None
    from email.utils import parsedate_to_datetime
    from datetime import timezone as tz

    # Try RFC 2822 (RSS pubDate)
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz.utc)
        return dt
    except Exception:
        pass

    # Try ISO 8601 variants
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(raw[:len(fmt)], fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz.utc)
            return dt
        except ValueError:
            continue

    # Epoch milliseconds (some JSON APIs return this)
    try:
        epoch_ms = int(raw)
        return datetime.fromtimestamp(epoch_ms / 1000, tz=tz.utc)
    except (ValueError, OSError):
        pass

    return None


# ── Convenience: filter articles newer than watermark ────────────────────────

def filter_new_articles(
    source_id: str,
    articles: list[dict],
    dt_field: str = "published_at",
) -> tuple[list[dict], Optional[datetime]]:
    """
    Given a raw list of scraped articles, return only those newer than the
    stored watermark for *source_id*, plus the max datetime found in *articles*.

    Returns:
        (new_articles, max_dt)  — max_dt is None if no parseable timestamps.
    """
    watermark = get_watermark(source_id)

    max_dt: Optional[datetime] = watermark
    new_articles: list[dict] = []

    for art in articles:
        dt = parse_article_dt(art.get(dt_field))
        if dt is None:
            # No timestamp → include conservatively (can't tell if new)
            new_articles.append(art)
            continue
        if watermark and dt <= watermark:
            # Already ingested
            continue
        new_articles.append(art)
        if max_dt is None or dt > max_dt:
            max_dt = dt

    skipped = len(articles) - len(new_articles)
    if skipped:
        logger.info(
            "[ingestion_tracker] %s: skipped %d already-ingested articles (watermark=%s)",
            source_id, skipped, watermark,
        )

    return new_articles, max_dt


if __name__ == "__main__":
    """Quick smoke-test: initialise table and print all watermarks."""
    import json
    from dotenv import load_dotenv
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    init_ingestion_track_table()
    from backend.db import get_pg_engine
    import sqlalchemy as sa
    engine = get_pg_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("SELECT source_id, last_article_at, total_ingested FROM ingestion_track ORDER BY source_id")
        ).fetchall()
    if rows:
        print("\n=== Ingestion Watermarks ===")
        for r in rows:
            print(f"  {r[0]:<35} last_article={r[1]}  total={r[2]}")
    else:
        print("No watermarks yet (table is empty — first run will do a full scrape).")
