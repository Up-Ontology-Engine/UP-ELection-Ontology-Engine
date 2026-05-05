"""
Stage yt_comments + news_articles → pulse_events_raw.
Run: python -m etl.pulse_event_prep
"""
from __future__ import annotations
import os, logging
import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)


def stage_youtube_comments(engine: sa.Engine) -> int:
    with engine.connect() as conn:
        result = conn.execute(text("""
            INSERT INTO pulse_events_raw (source_type, source_id, text_raw)
            SELECT 'youtube', comment_id, text_raw
            FROM yt_comments
            WHERE text_raw IS NOT NULL AND length(trim(text_raw)) > 10
            ON CONFLICT DO NOTHING
        """))
        conn.commit()
        return result.rowcount


def stage_news_articles(engine: sa.Engine) -> int:
    with engine.connect() as conn:
        result = conn.execute(text("""
            INSERT INTO pulse_events_raw (source_type, source_id, text_raw)
            SELECT 'news', article_id::text,
                   headline || ' ' || coalesce(body_raw, '')
            FROM news_articles
            WHERE headline IS NOT NULL AND length(trim(headline)) > 10
            ON CONFLICT DO NOTHING
        """))
        conn.commit()
        return result.rowcount


def run():
    engine = sa.create_engine(os.environ["POSTGRES_URL"])
    yt_n = stage_youtube_comments(engine)
    news_n = stage_news_articles(engine)
    logger.info(f"Staged: {yt_n} YouTube comments, {news_n} news articles → pulse_events_raw")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
