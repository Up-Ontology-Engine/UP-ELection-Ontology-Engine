"""
Direct NLP runner — bypasses Prefect to avoid SQLite telemetry lock.
Calls the same logic as flows/nlp/flow_sentiment.py but without @flow/@task.

Usage:
    python run_nlp_direct.py [--batch 500]
"""
from __future__ import annotations
import argparse, logging, os, json as _json
import sqlalchemy as sa
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def fetch_unprocessed(engine: sa.Engine, limit: int) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id::text AS source_id, source_type, text_raw
            FROM pulse_events_raw
            WHERE processed = FALSE
              AND text_raw IS NOT NULL
              AND LENGTH(TRIM(text_raw)) > 5
            ORDER BY created_at ASC
            LIMIT :limit
        """), {"limit": limit}).mappings().fetchall()
    return [dict(r) for r in rows]


def write_pulse_events(results: list, engine: sa.Engine) -> int:
    if not results:
        return 0
    inserted = 0
    processed_ids: list[str] = []

    for r in results:
        if hasattr(r, "model_dump"):
            r = r.model_dump()
        extraction = r.get("extraction", {})
        if hasattr(extraction, "model_dump"):
            extraction = extraction.model_dump()
        stmts = extraction.get("statements", [])
        geo   = r.get("geo_resolution") or {}
        if hasattr(geo, "model_dump"):
            geo = geo.model_dump()
        source_id = r.get("source_id") or r.get("id")
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO pulse_events (
                        source_type, source_id, text_raw, text_normalized_hi,
                        language_detected, translation_method,
                        extraction_method, llm_output,
                        entity, entity_type, issue, polarity, evidence,
                        final_polarity, final_issue,
                        location_text, mapped_booth_id, mapped_ac_id, geo_level
                    ) VALUES (
                        :source_type, :source_id, :text_raw, :text_hi,
                        :lang, :trans_method,
                        :ext_method, CAST(:llm_output AS jsonb),
                        :entity, :entity_type, :issue, :polarity, :evidence,
                        :final_polarity, :final_issue,
                        :loc_text, :booth_id, :ac_id, :geo_level
                    ) ON CONFLICT DO NOTHING
                """), {
                    "source_type":    r["source_type"],
                    "source_id":      source_id,
                    "text_raw":       r["text_raw"],
                    "text_hi":        r.get("text_normalized_hi"),
                    "lang":           r.get("language_detected", "unknown"),
                    "trans_method":   r.get("translation_method", "none"),
                    "ext_method":     r.get("extraction_method", "unknown"),
                    "llm_output":     _json.dumps(stmts),
                    "entity":         r.get("final_entity"),
                    "entity_type":    stmts[0].get("entity_type") if stmts else None,
                    "issue":          r.get("final_issue"),
                    "polarity":       r.get("final_polarity"),
                    "evidence":       stmts[0].get("evidence") if stmts else None,
                    "final_polarity": r.get("final_polarity"),
                    "final_issue":    r.get("final_issue"),
                    "loc_text":       stmts[0].get("location_mention") if stmts else None,
                    "booth_id":       geo.get("mapped_booth_id"),
                    "ac_id":          geo.get("mapped_ac_id", os.environ.get("PILOT_AC_ID", "GKP_322")),
                    "geo_level":      geo.get("mapped_type"),
                })
            inserted += 1
            processed_ids.append(str(source_id))
        except Exception as e:
            logger.warning("Insert failed for %s: %s", source_id, e)

    if processed_ids:
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE pulse_events_raw SET processed = TRUE
                WHERE id::text = ANY(:ids)
            """), {"ids": processed_ids})

    return inserted


def run(batch_limit: int = 500) -> None:
    from nlp.pipeline import process_batch

    engine = sa.create_engine(os.environ["POSTGRES_URL"])
    rows = fetch_unprocessed(engine, limit=batch_limit)
    if not rows:
        print("No unprocessed rows in pulse_events_raw.")
        return

    print(f"Processing {len(rows)} rows through NLP pipeline...")
    results = process_batch(rows, batch_size=50)
    n = write_pulse_events(results, engine)
    print(f"Done. Inserted {n} pulse_events, marked {len(results)} raw rows as processed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=500)
    args = parser.parse_args()
    run(args.batch)
