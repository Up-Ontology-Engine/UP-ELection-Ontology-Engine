"""
Fix 2 — Scheme gap analysis: 4-way classification replacing naive has_gap boolean.

Gap taxonomy:
  execution_gap   — completed + high beneficiaries + negative sentiment
                    (reached people but they're still unhappy)
  reach_gap       — completed + low beneficiaries + negative sentiment
                    (scheme not reaching people)
  awareness_gap   — completed + high beneficiaries + neutral/no sentiment
                    (reached people but they don't know / credit not captured)
  performing_well — completed + positive sentiment
  in_progress     — status != completed
  no_data         — no sentiment events to judge

Usage:
    from analytics.scheme_gap_analysis import run_all_booths, get_scheme_gaps_for_booth
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# Minimum beneficiary count to count as "high reach"
HIGH_BENEFICIARY_THRESHOLD = 50
# Minimum events required before sentiment judgement
MIN_SENTIMENT_EVENTS = 3


def _classify_gap(
    status: str,
    beneficiary_count: int,
    positive_events: int,
    negative_events: int,
    total_events: int,
) -> tuple[str, str, str]:
    """
    Returns (gap_type, gap_label, priority).
    """
    if status != "completed":
        return (
            "in_progress",
            "Scheme is still in progress — outcome cannot be assessed yet.",
            "LOW",
        )

    if total_events < MIN_SENTIMENT_EVENTS:
        return (
            "no_data",
            "No sentiment signal found for this scheme. Consider targeted field surveys.",
            "LOW",
        )

    avg_sentiment = (positive_events - negative_events) / total_events

    if avg_sentiment >= 0.2:
        return (
            "performing_well",
            "Scheme completed and community response is positive.",
            "LOW",
        )

    high_reach = beneficiary_count >= HIGH_BENEFICIARY_THRESHOLD

    if avg_sentiment < -0.1 and high_reach:
        return (
            "execution_gap",
            (
                f"Scheme completed and reached {beneficiary_count} beneficiaries "
                "but negative sentiment persists — quality or last-mile execution issue."
            ),
            "HIGH",
        )

    if avg_sentiment < -0.1 and not high_reach:
        return (
            "reach_gap",
            (
                f"Scheme completed but beneficiary count is low ({beneficiary_count}) "
                "and sentiment is negative — scheme may not be reaching intended recipients."
            ),
            "HIGH",
        )

    # Neutral sentiment territory
    if high_reach:
        return (
            "awareness_gap",
            (
                f"Scheme completed, reached {beneficiary_count} beneficiaries, "
                "but no positive credit signal — awareness / communication gap."
            ),
            "MEDIUM",
        )

    return (
        "reach_gap",
        (
            f"Scheme completed but low reach ({beneficiary_count} beneficiaries) "
            "with neutral sentiment — coverage may be insufficient."
        ),
        "MEDIUM",
    )


def get_scheme_gaps_for_booth(
    engine: Engine,
    booth_id: str,
    window_days: int = 30,
    computed_at: Optional[datetime] = None,
) -> list[dict]:
    """
    Returns a list of gap-analysis dicts for every scheme linked to this booth's panchayat.
    Does NOT write to DB.
    """
    if computed_at is None:
        computed_at = datetime.now(timezone.utc)

    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    sa.scheme_name,
                    sa.issue_tag,
                    sa.status          AS completion_status,
                    sa.beneficiary_count,
                    sa.panchayat_id,
                    COUNT(pe.id)
                        FILTER (WHERE pe.final_polarity = 1)  AS positive_events,
                    COUNT(pe.id)
                        FILTER (WHERE pe.final_polarity = -1) AS negative_events,
                    COUNT(pe.id)                               AS total_events,
                    AVG(pe.final_polarity)                     AS avg_sentiment
                FROM scheme_activity sa
                JOIN booth_panchayat_mapping bpm ON bpm.panchayat_id = sa.panchayat_id
                LEFT JOIN pulse_events pe
                    ON pe.mapped_booth_id = bpm.booth_id
                   AND pe.final_issue = sa.issue_tag
                   AND pe.created_at >= :cutoff
                   AND pe.created_at <= :now
                WHERE bpm.booth_id = :booth_id
                GROUP BY
                    sa.scheme_name, sa.issue_tag, sa.status,
                    sa.beneficiary_count, sa.panchayat_id
                ORDER BY negative_events DESC NULLS LAST
            """),
            {
                "booth_id":  booth_id,
                "cutoff":    computed_at - __import__("datetime").timedelta(days=window_days),
                "now":       computed_at,
            },
        ).mappings().fetchall()

    results = []
    for r in rows:
        status        = r["completion_status"] or "planned"
        benef         = r["beneficiary_count"] or 0
        pos_ev        = r["positive_events"] or 0
        neg_ev        = r["negative_events"] or 0
        total_ev      = r["total_events"] or 0
        avg_sent      = float(r["avg_sentiment"] or 0)

        gap_type, gap_label, priority = _classify_gap(
            status, benef, pos_ev, neg_ev, total_ev
        )

        results.append({
            "booth_id":          booth_id,
            "panchayat_id":      r["panchayat_id"],
            "scheme_name":       r["scheme_name"],
            "issue_tag":         r["issue_tag"],
            "computed_at":       computed_at,
            "beneficiary_count": benef,
            "completion_status": status,
            "positive_events":   pos_ev,
            "negative_events":   neg_ev,
            "total_events":      total_ev,
            "avg_sentiment":     round(avg_sent, 3),
            "gap_type":          gap_type,
            "gap_label":         gap_label,
            "priority":          priority,
        })

    return results


def upsert_gap_rows(engine: Engine, rows: list[dict]) -> None:
    if not rows:
        return
    with engine.begin() as conn:
        for row in rows:
            conn.execute(
                text("""
                    INSERT INTO scheme_gap_analysis (
                        booth_id, panchayat_id, scheme_name, issue_tag, computed_at,
                        beneficiary_count, completion_status,
                        positive_events, negative_events, total_events, avg_sentiment,
                        gap_type, gap_label, priority
                    ) VALUES (
                        :booth_id, :panchayat_id, :scheme_name, :issue_tag, :computed_at,
                        :beneficiary_count, :completion_status,
                        :positive_events, :negative_events, :total_events, :avg_sentiment,
                        """Compatibility shim: moved into analytics.signals.scheme_gap_analysis."""

                        from __future__ import annotations

                        from analytics.signals.scheme_gap_analysis import *  # noqa: F401,F403

                        __all__ = ["get_scheme_gaps_for_booth", "upsert_gap_rows"]
                        total_events       = EXCLUDED.total_events,
