"""
Bridge: yt_comments → pulse_events_raw

Reads comments from yt_comments that haven't been staged for NLP yet
and inserts them into pulse_events_raw (source_type='youtube').

Run AFTER ingestion/ingest_youtube_videos.py has fetched comments:
    python -m etl.stage_youtube_to_pulse
    python -m flows.nlp.flow_sentiment
"""

from __future__ import annotations

import logging
import os

import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)


def stage_youtube_comments(engine: sa.Engine) -> int:
    with engine.connect() as conn:
        rows = (
            conn.execute(
                text("""
            SELECT
                yc.comment_id           AS source_id,
                yc.text_raw,
                yc.video_id
            FROM yt_comments yc
            WHERE yc.text_raw IS NOT NULL
              AND LENGTH(TRIM(yc.text_raw)) > 10
              AND NOT EXISTS (
                  SELECT 1 FROM pulse_events_raw per
                  WHERE per.source_id = yc.comment_id
                    AND per.source_type = 'youtube'
              )
            ORDER BY yc.published_at ASC NULLS LAST
        """)
            )
            .mappings()
            .fetchall()
        )

        if not rows:
            logger.info("No new YouTube comments to stage.")
            return 0

        inserted = 0
        for row in rows:
            conn.execute(
                text("""
                INSERT INTO pulse_events_raw
                    (source_type, source_id, text_raw, video_id)
                VALUES
                    ('youtube', :source_id, :text_raw, :video_id)
                ON CONFLICT DO NOTHING
            """),
                {
                    "source_id": row["source_id"],
                    "text_raw": row["text_raw"],
                    "video_id": row["video_id"],
                },
            )
            inserted += 1

        conn.commit()

    logger.info("Staged %d YouTube comments into pulse_events_raw.", inserted)
    return inserted


def run() -> None:
    engine = sa.create_engine(os.environ["POSTGRES_URL"])
    n = stage_youtube_comments(engine)
    print(f"Staged {n} YouTube comment(s) for NLP processing.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run()
