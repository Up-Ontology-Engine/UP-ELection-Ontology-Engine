"""
Fix 4 — Cross-source contradiction detection.

For each (booth, entity) pair, compare the average polarity coming from
different source types (youtube vs news, survey vs youtube, etc.).

A large polarity delta between sources can mean:
  - MIXED_SIGNALS    — one source strongly positive, another strongly negative
  - SWING_INDICATOR  — moderate divergence, worth watching
  - MINOR_DIVERGENCE — small gap, normal noise

Results are written to contradiction_flags table and also denormalized into
booth_metrics.signal_consistency_score + has_contradiction.

Usage:
    python -m analytics.contradiction_detector
"""

from __future__ import annotations

import itertools
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# Thresholds for flag labels
MIXED_SIGNALS_DELTA    = 0.6   # |polarity_a - polarity_b| >= 0.6
SWING_INDICATOR_DELTA  = 0.35  # >= 0.35
# Minimum events per source to be included
MIN_EVENTS_PER_SOURCE  = 3


def detect_contradictions_for_booth(
    engine: Engine,
    booth_id: str,
    window_days: int = 7,
    computed_at: Optional[datetime] = None,
) -> list[dict]:
    """
    Returns a list of contradiction flag dicts for the booth.
    Does NOT write to DB.
    """
    if computed_at is None:
        computed_at = datetime.now(timezone.utc)
    cutoff = computed_at - timedelta(days=window_days)

    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    entity,
                    final_issue         AS issue,
                    source_type,
                    AVG(final_polarity) AS avg_polarity,
                    COUNT(*)            AS event_count
                FROM pulse_events
                WHERE mapped_booth_id = :booth_id
                  AND created_at >= :cutoff
                  AND created_at <= :now
                  AND entity IS NOT NULL
                  AND entity != ''
                  AND final_polarity IS NOT NULL
                GROUP BY entity, final_issue, source_type
                HAVING COUNT(*) >= :min_events
            """),
            {
                "booth_id":   booth_id,
                "cutoff":     cutoff,
                "now":        computed_at,
                "min_events": MIN_EVENTS_PER_SOURCE,
            },
        ).mappings().fetchall()

    # Group by (entity, issue) → {source_type: (avg_polarity, count)}
    grouped: dict[tuple, dict[str, tuple]] = {}
    for r in rows:
        key = (r["entity"], r["issue"])
        grouped.setdefault(key, {})[r["source_type"]] = (
            float(r["avg_polarity"]),
            int(r["event_count"]),
        )

    flags = []
    for (entity, issue), source_stats in grouped.items():
        sources = list(source_stats.keys())
        if len(sources) < 2:
            continue

        for src_a, src_b in itertools.combinations(sorted(sources), 2):
            pol_a, cnt_a = source_stats[src_a]
            pol_b, cnt_b = source_stats[src_b]
            delta = abs(pol_a - pol_b)

            if delta < 0.15:
                continue  # No meaningful divergence

            if delta >= MIXED_SIGNALS_DELTA:
                flag_label = "MIXED_SIGNALS"
            elif delta >= SWING_INDICATOR_DELTA:
                flag_label = "SWING_INDICATOR"
            else:
                flag_label = "MINOR_DIVERGENCE"

            # consistency_score: 1 = perfectly consistent, 0 = completely contradictory
            consistency_score = round(1 - (delta / 2), 3)

            flags.append({
                "booth_id":          booth_id,
                "entity":            entity,
                "issue":             issue,
                "computed_at":       computed_at,
                "window_days":       window_days,
                "source_a":          src_a,
                "source_b":          src_b,
                "polarity_a":        round(pol_a, 3),
                "polarity_b":        round(pol_b, 3),
                "delta":             round(delta, 3),
                "events_a":          cnt_a,
                "events_b":          cnt_b,
                "consistency_score": consistency_score,
                "flag_label":        flag_label,
            })

    return sorted(flags, key=lambda x: -x["delta"])


def upsert_contradiction_rows(engine: Engine, rows: list[dict]) -> None:
    if not rows:
        return
    with engine.begin() as conn:
        for row in rows:
            conn.execute(
                text("""
                    INSERT INTO contradiction_flags (
                        booth_id, entity, issue, computed_at, window_days,
                        source_a, source_b,
                        polarity_a, polarity_b, delta,
                        events_a, events_b,
                        consistency_score, flag_label
                    ) VALUES (
                        :booth_id, :entity, :issue, :computed_at, :window_days,
                        :source_a, :source_b,
                        :polarity_a, :polarity_b, :delta,
                        :events_a, :events_b,
                        :consistency_score, :flag_label
                    )
                    ON CONFLICT (booth_id, entity, source_a, source_b, computed_at)
                    DO UPDATE SET
                        polarity_a        = EXCLUDED.polarity_a,
                        polarity_b        = EXCLUDED.polarity_b,
                        delta             = EXCLUDED.delta,
                        events_a          = EXCLUDED.events_a,
                        events_b          = EXCLUDED.events_b,
                        consistency_score = EXCLUDED.consistency_score,
                        flag_label        = EXCLUDED.flag_label
                """),
                row,
            )


def update_booth_metrics_consistency(engine: Engine, booth_id: str, computed_at: datetime) -> None:
    """
    Denormalize the worst-case consistency score and contradiction flag into booth_metrics.
    """
    with engine.begin() as conn:
        result = conn.execute(
            text("""
                SELECT
                    MIN(consistency_score) AS worst_score,
                    COUNT(*) FILTER (WHERE flag_label = 'MIXED_SIGNALS') AS mixed_count
                FROM contradiction_flags
                WHERE booth_id = :booth_id
                  AND computed_at = :computed_at
            """),
            {"booth_id": booth_id, "computed_at": computed_at},
        ).fetchone()

        if result and result[0] is not None:
            conn.execute(
                text("""
                    UPDATE booth_metrics
                    SET
                        signal_consistency_score = :score,
                        has_contradiction        = :has_contra
                    WHERE booth_id = :booth_id
                """),
                {
                    "booth_id":    booth_id,
                    "score":       float(result[0]),
                    "has_contra":  (result[1] or 0) > 0,
                },
            )


def run_all_booths(engine: Engine, window_days: int = 7) -> int:
    with engine.connect() as conn:
        booth_ids = [
            r[0]
            for r in conn.execute(
                text(
                    "SELECT DISTINCT mapped_booth_id FROM pulse_events "
                    "WHERE mapped_booth_id IS NOT NULL"
                )
            ).fetchall()
        ]

    computed_at = datetime.now(timezone.utc)
    for booth_id in booth_ids:
        flags = detect_contradictions_for_booth(engine, booth_id, window_days, computed_at)
        upsert_contradiction_rows(engine, flags)
        update_booth_metrics_consistency(engine, booth_id, computed_at)

    return len(booth_ids)


if __name__ == "__main__":
    from dotenv import load_dotenv; load_dotenv()
    from api.db import get_pg_engine
    eng = get_pg_engine()
    n = run_all_booths(eng)
    print(f"Contradiction detection done for {n} booths.")
