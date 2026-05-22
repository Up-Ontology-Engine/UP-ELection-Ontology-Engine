"""
Fix 1 — Multi-dimensional data quality scoring.

Reads pulse_events for a booth window and produces a data_quality_metrics row
with per-dimension scores and a human-readable quality_reasons list.

Usage:
    from analytics.data_quality import compute_quality_for_booth
    row = compute_quality_for_booth(engine, booth_id="GKP_U_045", window_days=7)
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

# ---------------------------------------------------------------------------
# Source weights (also used in booth_metrics for consistency)
# ---------------------------------------------------------------------------
SOURCE_WEIGHT: dict[str, float] = {
    "survey":     1.0,
    "field_note": 0.9,
    "news":       0.4,
    "youtube":    0.6,
}

# Thresholds for quality label assignment
QUALITY_THRESHOLDS = {
    "HIGH":         0.75,
    "MEDIUM":       0.50,
    "LOW":          0.25,
}

MIN_EVENTS_FOR_ASSESSMENT = 5


def compute_quality_for_booth(
    engine: Engine,
    booth_id: str,
    window_days: int = 7,
    computed_at: Optional[datetime] = None,
) -> dict:
    """
    Returns a dict matching the data_quality_metrics table schema.
    Does NOT write to DB — caller decides whether to upsert.
    """
    if computed_at is None:
        computed_at = datetime.now(timezone.utc)

    cutoff = computed_at - timedelta(days=window_days)

    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    source_type,
                    geo_confidence,
                    mapped_booth_id,
                    mapped_ac_id,
                    final_confidence AS nlp_confidence,
                    extraction_method,
                    entity
                FROM pulse_events
                WHERE mapped_booth_id = :booth_id
                  AND created_at >= :cutoff
                  AND created_at <= :now
            """),
            {"booth_id": booth_id, "cutoff": cutoff, "now": computed_at},
        ).fetchall()

    if not rows:
        return _empty_quality_row(booth_id, window_days, computed_at)

    total = len(rows)
    reasons: list[str] = []

    # ── 1. Volume ──────────────────────────────────────────────────────────
    unique_sources = len({r.source_type for r in rows if r.source_type})

    source_counts: dict[str, int] = {}
    for r in rows:
        src = (r.source_type or "unknown").lower()
        source_counts[src] = source_counts.get(src, 0) + 1

    def pct(src: str) -> float:
        return round(source_counts.get(src, 0) / total * 100, 1)

    youtube_pct = pct("youtube")
    news_pct    = pct("news")
    survey_pct  = pct("survey")
    field_note_pct = pct("field_note")

    # ── 2. Source diversity score ──────────────────────────────────────────
    # Penalise single-source domination using a Herfindahl-style penalty
    shares = [c / total for c in source_counts.values()]
    hhi = sum(s ** 2 for s in shares)            # 1 = monopoly, 1/n = equal
    source_diversity_score = round(1 - hhi, 3)   # higher = more diverse

    dominant_src = max(source_counts, key=source_counts.__getitem__)
    dominant_pct = source_counts[dominant_src] / total * 100
    if dominant_pct >= 80:
        reasons.append(f"Only {dominant_src} data ({dominant_pct:.0f}%)")

    if total < MIN_EVENTS_FOR_ASSESSMENT:
        reasons.append(f"Very few events ({total})")

    # ── 3. Geo resolution quality ──────────────────────────────────────────
    booth_mapped = sum(1 for r in rows if r.mapped_booth_id == booth_id)
    ac_only      = sum(1 for r in rows if r.mapped_booth_id is None and r.mapped_ac_id)
    geo_confs    = [r.geo_confidence for r in rows if r.geo_confidence is not None]

    booth_mapped_pct   = round(booth_mapped / total * 100, 1)
    ac_mapped_pct      = round(ac_only / total * 100, 1)
    avg_geo_confidence = round(sum(geo_confs) / len(geo_confs), 3) if geo_confs else 0.0

    if ac_mapped_pct >= 30:
        reasons.append(f"{ac_mapped_pct:.0f}% events mapped at AC-level only")
    if avg_geo_confidence < 0.5 and geo_confs:
        reasons.append(f"Low geo confidence (avg {avg_geo_confidence:.2f})")

    # ── 4. NLP quality ─────────────────────────────────────────────────────
    nlp_confs = [r.nlp_confidence for r in rows if r.nlp_confidence is not None]
    avg_nlp_confidence = round(sum(nlp_confs) / len(nlp_confs), 3) if nlp_confs else 0.0

    llm_extracted = sum(1 for r in rows if r.extraction_method == "llm")
    llm_extracted_pct = round(llm_extracted / total * 100, 1)

    valid_entity = sum(1 for r in rows if r.entity and r.entity.strip())
    entity_match_rate    = round(valid_entity / total * 100, 1)
    missing_entity_pct   = round(100 - entity_match_rate, 1)

    if avg_nlp_confidence < 0.55 and nlp_confs:
        reasons.append(f"Low NLP confidence (avg {avg_nlp_confidence:.2f})")
    if missing_entity_pct >= 40:
        reasons.append(f"{missing_entity_pct:.0f}% events missing entity")

    # ── 5. Composite quality score (0–1) ───────────────────────────────────
    # Weighted combination of all dimensions
    volume_score    = min(1.0, math.log1p(total) / math.log1p(50))  # saturates at 50 events
    geo_score       = avg_geo_confidence
    nlp_score       = avg_nlp_confidence
    diversity_score = source_diversity_score

    overall_quality_score = round(
        0.25 * volume_score
        + 0.25 * geo_score
        + 0.30 * nlp_score
        + 0.20 * diversity_score,
        3,
    )

    # ── 6. Quality label ───────────────────────────────────────────────────
    if total < MIN_EVENTS_FOR_ASSESSMENT:
        quality_label = "INSUFFICIENT"
    elif overall_quality_score >= QUALITY_THRESHOLDS["HIGH"]:
        quality_label = "HIGH"
    elif overall_quality_score >= QUALITY_THRESHOLDS["MEDIUM"]:
        quality_label = "MEDIUM"
    elif overall_quality_score >= QUALITY_THRESHOLDS["LOW"]:
        quality_label = "LOW"
    else:
        quality_label = "INSUFFICIENT"

    return {
        "booth_id":              booth_id,
        "computed_at":           computed_at,
        "window_days":           window_days,
        "total_events":          total,
        "unique_sources":        unique_sources,
        "youtube_pct":           youtube_pct,
        "news_pct":              news_pct,
        "survey_pct":            survey_pct,
        "field_note_pct":        field_note_pct,
        "booth_mapped_pct":      booth_mapped_pct,
        "ac_mapped_pct":         ac_mapped_pct,
        "avg_geo_confidence":    avg_geo_confidence,
        "avg_nlp_confidence":    avg_nlp_confidence,
        "llm_extracted_pct":     llm_extracted_pct,
        "entity_match_rate":     entity_match_rate,
        "missing_entity_pct":    missing_entity_pct,
        "source_diversity_score": source_diversity_score,
        "overall_quality_score": overall_quality_score,
        "quality_label":         quality_label,
        "quality_reasons":       reasons,
    }


def upsert_quality_row(engine: Engine, row: dict) -> None:
    """Insert or replace the quality metrics row for a booth+window."""
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO data_quality_metrics (
                    booth_id, computed_at, window_days, total_events, unique_sources,
                    youtube_pct, news_pct, survey_pct, field_note_pct,
                    booth_mapped_pct, ac_mapped_pct, avg_geo_confidence,
                    avg_nlp_confidence, llm_extracted_pct, entity_match_rate,
                    missing_entity_pct, source_diversity_score,
                    overall_quality_score, quality_label, quality_reasons
                ) VALUES (
                    :booth_id, :computed_at, :window_days, :total_events, :unique_sources,
                    :youtube_pct, :news_pct, :survey_pct, :field_note_pct,
                    :booth_mapped_pct, :ac_mapped_pct, :avg_geo_confidence,
                    :avg_nlp_confidence, :llm_extracted_pct, :entity_match_rate,
                    :missing_entity_pct, :source_diversity_score,
                    :overall_quality_score, :quality_label, :quality_reasons
                )
                ON CONFLICT (booth_id, computed_at) DO UPDATE SET
                    total_events          = EXCLUDED.total_events,
                    unique_sources        = EXCLUDED.unique_sources,
                    youtube_pct           = EXCLUDED.youtube_pct,
                    news_pct              = EXCLUDED.news_pct,
                    survey_pct            = EXCLUDED.survey_pct,
                    field_note_pct        = EXCLUDED.field_note_pct,
                    booth_mapped_pct      = EXCLUDED.booth_mapped_pct,
                    ac_mapped_pct         = EXCLUDED.ac_mapped_pct,
                    avg_geo_confidence    = EXCLUDED.avg_geo_confidence,
                    avg_nlp_confidence    = EXCLUDED.avg_nlp_confidence,
                    llm_extracted_pct     = EXCLUDED.llm_extracted_pct,
                    entity_match_rate     = EXCLUDED.entity_match_rate,
                    missing_entity_pct    = EXCLUDED.missing_entity_pct,
                    source_diversity_score = EXCLUDED.source_diversity_score,
                    overall_quality_score = EXCLUDED.overall_quality_score,
                    quality_label         = EXCLUDED.quality_label,
                    quality_reasons       = EXCLUDED.quality_reasons
            """),
            {**row, "quality_reasons": json.dumps(row["quality_reasons"])},
        )


def run_all_booths(engine: Engine, window_days: int = 7) -> int:
    """Compute and upsert quality metrics for every booth that has events."""
    with engine.connect() as conn:
        booth_ids = [
            r[0]
            for r in conn.execute(
                text("SELECT DISTINCT mapped_booth_id FROM pulse_events WHERE mapped_booth_id IS NOT NULL")
            ).fetchall()
        ]

    computed_at = datetime.now(timezone.utc)
    for booth_id in booth_ids:
        row = compute_quality_for_booth(engine, booth_id, window_days, computed_at)
        upsert_quality_row(engine, row)

    return len(booth_ids)


def _empty_quality_row(booth_id: str, window_days: int, computed_at: datetime) -> dict:
    return {
        "booth_id":              booth_id,
        "computed_at":           computed_at,
        "window_days":           window_days,
        "total_events":          0,
        "unique_sources":        0,
        "youtube_pct":           0.0,
        "news_pct":              0.0,
        "survey_pct":            0.0,
        "field_note_pct":        0.0,
        "booth_mapped_pct":      0.0,
        "ac_mapped_pct":         0.0,
        "avg_geo_confidence":    0.0,
        "avg_nlp_confidence":    0.0,
        "llm_extracted_pct":     0.0,
        "entity_match_rate":     0.0,
        "missing_entity_pct":    0.0,
        "source_diversity_score": 0.0,
        "overall_quality_score": 0.0,
        "quality_label":         "INSUFFICIENT",
        "quality_reasons":       ["No events in window"],
    }


if __name__ == "__main__":
    from dotenv import load_dotenv; load_dotenv()
    from api.db import get_pg_engine
    eng = get_pg_engine()
    n = run_all_booths(eng)
    print(f"Quality metrics computed for {n} booths.")
