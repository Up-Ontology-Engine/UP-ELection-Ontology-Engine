"""
Direct NLP runner — bypasses Prefect to avoid SQLite telemetry lock.
Calls the same logic as flows/nlp/flow_sentiment.py but without @flow/@task.

Usage:
    python run_nlp_direct.py [--batch 500]
"""

import sys
from pathlib import Path

# ── Bootstrap: load .env and setup sys.path before any imports ────────────────
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "pipeline"))

try:
    from dotenv import load_dotenv

    load_dotenv(_REPO_ROOT / ".env")
except ImportError:
    pass

import argparse
import json as _json
import logging
import os
from typing import Any

import sqlalchemy as sa
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _to_dict(obj: Any) -> Any:
    """Convert Pydantic models to dicts; pass through dicts unchanged."""
    if callable(getattr(obj, "model_dump", None)):
        return obj.model_dump()
    return obj


def fetch_unprocessed(engine: sa.Engine, limit: int) -> list[dict]:
    with engine.connect() as conn:
        rows = (
            conn.execute(
                text("""
            SELECT id::text AS source_id, source_type, text_raw
            FROM pulse_events_raw
            WHERE processed = FALSE
              AND text_raw IS NOT NULL
              AND LENGTH(TRIM(text_raw)) > 5
            ORDER BY created_at ASC
            LIMIT :limit
        """),
                {"limit": limit},
            )
            .mappings()
            .fetchall()
        )
    return [dict(r) for r in rows]


def write_pulse_events(results: list, engine: sa.Engine) -> int:
    if not results:
        return 0
    inserted = 0
    processed_ids: list[str] = []

    for r in results:
        # Convert Pydantic models to dicts if needed
        r = _to_dict(r)

        extraction = _to_dict(r.get("extraction", {}))
        stmts = extraction.get("statements", [])
        geo = _to_dict(r.get("geo_resolution") or {})
        source_id = r.get("source_id") or r.get("id")
        try:
            with engine.begin() as conn:
                conn.execute(
                    text("""
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
                """),
                    {
                        "source_type": r["source_type"],
                        "source_id": source_id,
                        "text_raw": r["text_raw"],
                        "text_hi": r.get("text_normalized_hi"),
                        "lang": r.get("language_detected", "unknown"),
                        "trans_method": r.get("translation_method", "none"),
                        "ext_method": r.get("extraction_method", "unknown"),
                        "llm_output": _json.dumps(stmts),
                        "entity": r.get("final_entity"),
                        "entity_type": stmts[0].get("entity_type") if stmts else None,
                        "issue": r.get("final_issue"),
                        "polarity": r.get("final_polarity"),
                        "evidence": stmts[0].get("evidence") if stmts else None,
                        "final_polarity": r.get("final_polarity"),
                        "final_issue": r.get("final_issue"),
                        "loc_text": stmts[0].get("location_mention") if stmts else None,
                        "booth_id": geo.get("mapped_booth_id"),
                        "ac_id": geo.get("mapped_ac_id", os.environ.get("PILOT_AC_ID", "GKP_322")),
                        "geo_level": geo.get("mapped_type"),
                    },
                )
            inserted += 1
            processed_ids.append(str(source_id))
        except Exception as e:
            logger.warning("Insert failed for %s: %s", source_id, e)

    if processed_ids:
        with engine.begin() as conn:
            conn.execute(
                text("""
                UPDATE pulse_events_raw SET processed = TRUE
                WHERE id::text = ANY(:ids)
            """),
                {"ids": processed_ids},
            )

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
