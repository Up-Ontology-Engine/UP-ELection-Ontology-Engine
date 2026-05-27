"""
Bridge: news_articles → pulse_events_raw

Reads articles from news_articles that haven't been staged yet and inserts
them into pulse_events_raw so the NLP flow (flows.nlp.flow_sentiment) can
pick them up.

Run AFTER etl.transform_news:
    python -m etl.transform_news        # load CSV → news_articles
    python -m etl.stage_news_to_pulse   # news_articles → pulse_events_raw
    python -m flows.nlp.flow_sentiment  # pulse_events_raw → pulse_events
"""

from __future__ import annotations

import logging
import os

import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)


def stage_news(engine: sa.Engine) -> int:
    with engine.connect() as conn:
        rows = (
            conn.execute(
                text("""
            SELECT
                na.article_id::text        AS source_id,
                COALESCE(na.body_raw, na.headline) AS text_raw
            FROM news_articles na
            WHERE COALESCE(na.body_raw, na.headline) IS NOT NULL
              AND NOT EXISTS (
                SELECT 1 FROM pulse_events_raw per
                WHERE per.source_id = na.article_id::text
                  AND per.source_type = 'news'
              )
            ORDER BY na.published_at ASC NULLS LAST
        """)
            )
            .mappings()
            .fetchall()
        )

        if not rows:
            logger.info("No new articles to stage — all already in pulse_events_raw.")
            return 0

        inserted = 0
        for row in rows:
            conn.execute(
                text("""
                INSERT INTO pulse_events_raw (source_type, source_id, text_raw)
                VALUES ('news', :source_id, :text_raw)
                ON CONFLICT DO NOTHING
            """),
                {"source_id": row["source_id"], "text_raw": row["text_raw"]},
            )
            inserted += 1

        conn.commit()

    logger.info("Staged %d news articles into pulse_events_raw.", inserted)
    return inserted


def run() -> None:
    engine = sa.create_engine(os.environ["POSTGRES_URL"])
    n = stage_news(engine)
    print(f"Staged {n} article(s) for NLP processing.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run()
