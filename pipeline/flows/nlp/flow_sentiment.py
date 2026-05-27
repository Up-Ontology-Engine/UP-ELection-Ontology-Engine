"""
Prefect flow: process pulse_events_raw → pulse_events.
Run: python -m flows.nlp.flow_sentiment
"""

from __future__ import annotations

import logging
import os

import sqlalchemy as sa
from dotenv import load_dotenv
from prefect import flow, task
from sqlalchemy import text

load_dotenv()
logger = logging.getLogger(__name__)


@task(retries=2, retry_delay_seconds=10)
def fetch_unprocessed(engine: sa.Engine, limit: int = 500) -> list[dict]:
    with engine.connect() as conn:
        rows = (
            conn.execute(
                text("""
            SELECT id::text AS source_id, source_type, text_raw
            FROM pulse_events_raw
            WHERE processed = FALSE
            ORDER BY created_at ASC
            LIMIT :limit
        """),
                {"limit": limit},
            )
            .mappings()
            .fetchall()
        )
    return [dict(r) for r in rows]


@task
def run_nlp_pipeline(rows: list[dict]) -> list[dict]:
    from nlp.pipeline import process_batch

    results = process_batch(rows, batch_size=50)
    return [r.model_dump() for r in results]


@task
def write_pulse_events(results: list[dict], engine: sa.Engine):
    if not results:
        return
    with engine.connect() as conn:
        for r in results:
            extraction = r.get("extraction", {})
            stmts = extraction.get("statements", [])
            geo = r.get("geo_resolution") or {}
            conn.execute(
                text("""
                INSERT INTO pulse_events (
                    source_type, source_id, text_raw, text_normalized_hi,
                    language_detected, translation_method,
                    extraction_method, llm_output,
                    entity, entity_type, issue, polarity, confidence, evidence,
                    final_polarity, final_issue, final_confidence,
                    location_text, mapped_booth_id, mapped_ac_id, geo_level, geo_confidence,
                    source_weight
                ) VALUES (
                    :source_type, :source_id, :text_raw, :text_hi,
                    :lang, :trans_method,
                    :ext_method, :llm_output::jsonb,
                    :entity, :entity_type, :issue, :polarity, :conf, :evidence,
                    :final_polarity, :final_issue, :final_conf,
                    :loc_text, :booth_id, :ac_id, :geo_level, :geo_conf,
                    :src_weight
                )
            """),
                {
                    "source_type": r["source_type"],
                    "source_id": r["source_id"],
                    "text_raw": r["text_raw"],
                    "text_hi": r.get("text_normalized_hi"),
                    "lang": r.get("language_detected", "unknown"),
                    "trans_method": r.get("translation_method", "none"),
                    "ext_method": r.get("extraction_method", "unknown"),
                    "llm_output": str(stmts),
                    "entity": r.get("final_entity"),
                    "entity_type": stmts[0].get("entity_type") if stmts else None,
                    "issue": r.get("final_issue"),
                    "polarity": r.get("final_polarity"),
                    "conf": r.get("final_confidence", 0),
                    "evidence": stmts[0].get("evidence") if stmts else None,
                    "final_polarity": r.get("final_polarity"),
                    "final_issue": r.get("final_issue"),
                    "final_conf": r.get("final_confidence", 0),
                    "loc_text": stmts[0].get("location_mention") if stmts else None,
                    "booth_id": geo.get("mapped_booth_id"),
                    "ac_id": geo.get("mapped_ac_id", os.environ.get("PILOT_AC_ID", "GKP_322")),
                    "geo_level": geo.get("mapped_type"),
                    "geo_conf": geo.get("geo_confidence", 0.0),
                    "src_weight": {"youtube": 0.6, "news": 0.4, "survey": 1.0}.get(
                        r["source_type"], 0.5
                    ),
                },
            )

        # Mark processed
        source_ids = [r["source_id"] for r in results]
        conn.execute(
            text("""
            UPDATE pulse_events_raw SET processed = TRUE
            WHERE id::text = ANY(:ids)
        """),
            {"ids": source_ids},
        )
        conn.commit()
    logger.info(f"Wrote {len(results)} pulse events")


@flow(name="sentiment-pipeline", log_prints=True)
def sentiment_flow(batch_limit: int = 500):
    engine = sa.create_engine(os.environ["POSTGRES_URL"])
    rows = fetch_unprocessed(engine, limit=batch_limit)
    if not rows:
        print("No unprocessed rows.")
        return
    print(f"Processing {len(rows)} rows...")
    results = run_nlp_pipeline(rows)
    write_pulse_events(results, engine)
    print(f"Done. Processed {len(results)} events.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sentiment_flow()
