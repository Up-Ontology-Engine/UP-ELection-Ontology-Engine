"""Scheme gap analysis moved into analytics.signals."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

HIGH_BENEFICIARY_THRESHOLD = 50
MIN_SENTIMENT_EVENTS = 3


def _classify_gap(
    status: str,
    beneficiary_count: int,
    positive_events: int,
    negative_events: int,
    total_events: int,
) -> tuple[str, str, str]:
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
        return ("performing_well", "Scheme completed and community response is positive.", "LOW")
    high_reach = beneficiary_count >= HIGH_BENEFICIARY_THRESHOLD
    if avg_sentiment < -0.1 and high_reach:
        return (
            "execution_gap",
            "Scheme completed and reached {beneficiary_count} beneficiaries but negative sentiment persists — quality or last-mile execution issue.",
            "HIGH",
        )
    if avg_sentiment < -0.1 and not high_reach:
        return (
            "reach_gap",
            "Scheme completed but beneficiary count is low and sentiment is negative — scheme may not be reaching intended recipients.",
            "HIGH",
        )
    if high_reach:
        return (
            "awareness_gap",
            "Scheme completed, reached beneficiaries, but no positive credit signal — awareness / communication gap.",
            "MEDIUM",
        )
    return (
        "reach_gap",
        "Scheme completed but low reach with neutral sentiment — coverage may be insufficient.",
        "MEDIUM",
    )


def get_scheme_gaps_for_booth(
    engine: Engine, booth_id: str, window_days: int = 30, computed_at: Optional[datetime] = None
) -> list[dict]:
    if computed_at is None:
        computed_at = datetime.now(timezone.utc)

    with engine.connect() as conn:
        rows = (
            conn.execute(
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
                    "booth_id": booth_id,
                    "cutoff": computed_at - __import__("datetime").timedelta(days=window_days),
                    "now": computed_at,
                },
            )
            .mappings()
            .fetchall()
        )

    results = []
    for r in rows:
        status = r["completion_status"] or "planned"
        benef = r["beneficiary_count"] or 0
        pos_ev = r["positive_events"] or 0
        neg_ev = r["negative_events"] or 0
        total_ev = r["total_events"] or 0
        avg_sent = float(r["avg_sentiment"] or 0)

        gap_type, gap_label, priority = _classify_gap(status, benef, pos_ev, neg_ev, total_ev)

        results.append(
            {
                "booth_id": booth_id,
                "panchayat_id": r["panchayat_id"],
                "scheme_name": r["scheme_name"],
                "issue_tag": r["issue_tag"],
                "computed_at": computed_at,
                "beneficiary_count": benef,
                "completion_status": status,
                "positive_events": pos_ev,
                "negative_events": neg_ev,
                "total_events": total_ev,
                "avg_sentiment": round(avg_sent, 3),
                "gap_type": gap_type,
                "gap_label": gap_label,
                "priority": priority,
            }
        )

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
                        :gap_type, :gap_label, :priority
                    )
                    ON CONFLICT (booth_id, scheme_name, computed_at) DO UPDATE SET
                        beneficiary_count  = EXCLUDED.beneficiary_count,
                        completion_status  = EXCLUDED.completion_status,
                        positive_events    = EXCLUDED.positive_events,
                        negative_events    = EXCLUDED.negative_events,
                        total_events       = EXCLUDED.total_events,
                        avg_sentiment      = EXCLUDED.avg_sentiment,
                        gap_type           = EXCLUDED.gap_type,
                        gap_label          = EXCLUDED.gap_label,
                        priority           = EXCLUDED.priority
                """),
                row,
            )


def run_all_booths(engine: Engine, window_days: int = 30) -> int:
    with engine.connect() as conn:
        booth_ids = [
            r[0]
            for r in conn.execute(
                text(
                    "SELECT DISTINCT bpm.booth_id FROM booth_panchayat_mapping bpm JOIN scheme_activity sa ON sa.panchayat_id = bpm.panchayat_id"
                )
            ).fetchall()
        ]

    computed_at = datetime.now(timezone.utc)
    for booth_id in booth_ids:
        rows = get_scheme_gaps_for_booth(engine, booth_id, window_days, computed_at)
        upsert_gap_rows(engine, rows)

    return len(booth_ids)
