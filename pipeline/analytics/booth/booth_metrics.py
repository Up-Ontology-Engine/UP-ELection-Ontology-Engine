"""Booth metrics (moved from analytics/booth_metrics.py)
"""
from __future__ import annotations
import os, json, logging
from datetime import datetime, timedelta, timezone
import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)

SOURCE_WEIGHTS = {"survey": 1.0, "field_note": 0.9, "youtube": 0.6, "news": 0.4}


def _lean_label(diff: float) -> str:
    if diff > 0.15:   return "Lean BJP"
    if diff < -0.15:  return "Lean Opposition"
    if diff > 0.05:   return "Slightly BJP"
    if diff < -0.05:  return "Slightly Opp"
    return "Contested"


def _confidence_label(score: float, events: int) -> str:
    if events >= 100 and score >= 0.65: return "HIGH"
    if events >= 30  and score >= 0.50: return "MEDIUM"
    if events >= 10:                    return "LOW"
    return "INSUFFICIENT"


def compute_booth_metrics(engine: sa.Engine, window_days: int = 7):
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=window_days)
    prev_start   = window_start - timedelta(days=window_days)

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT mapped_booth_id, entity, issue,
                   final_polarity, final_confidence, source_type, geo_confidence
            FROM pulse_events
            WHERE mapped_booth_id IS NOT NULL
              AND created_at >= :start
              AND final_polarity IS NOT NULL
        """), {"start": window_start}).mappings().fetchall()

        if not rows:
            logger.warning("No pulse events found for window.")
            return

        prev_rows = conn.execute(text("""
            SELECT mapped_booth_id, issue, final_polarity, final_confidence, source_type
            FROM pulse_events
            WHERE mapped_booth_id IS NOT NULL
              AND created_at >= :start AND created_at < :end
              AND final_polarity IS NOT NULL
        """), {"start": prev_start, "end": window_start}).mappings().fetchall()

        from collections import defaultdict
        booth_events: dict[str, list] = defaultdict(list)
        for r in rows:
            booth_events[r["mapped_booth_id"]].append(dict(r))

        prev_booth_events: dict[str, list] = defaultdict(list)
        for r in prev_rows:
            prev_booth_events[r["mapped_booth_id"]].append(dict(r))

        metrics_rows = []
        for booth_id, events in booth_events.items():
            sw = lambda e: SOURCE_WEIGHTS.get(e["source_type"], 0.5)

            bjp_weighted = sum(e["final_polarity"] * e["final_confidence"] * sw(e)
                               for e in events if e["entity"] in ("BJP","Yogi Adityanath","Narendra Modi"))
            bjp_weight   = sum(e["final_confidence"] * sw(e)
                               for e in events if e["entity"] in ("BJP","Yogi Adityanath","Narendra Modi"))

            opp_weighted = sum(e["final_polarity"] * e["final_confidence"] * sw(e)
                               for e in events if e["entity"] in ("SP","BSP","Congress","Akhilesh Yadav","Mayawati"))
            opp_weight   = sum(e["final_confidence"] * sw(e)
                               for e in events if e["entity"] in ("SP","BSP","Congress","Akhilesh Yadav","Mayawati"))

            bjp_pulse = round(bjp_weighted / bjp_weight, 4) if bjp_weight else 0.0
            opp_pulse = round(opp_weighted / opp_weight, 4) if opp_weight else 0.0
            lean      = round(bjp_pulse - opp_pulse, 4)

            issue_counts: dict[str, int] = defaultdict(int)
            for e in events:
                if e["issue"]:
                    issue_counts[e["issue"]] += 1
            total_with_issue = sum(issue_counts.values()) or 1
            issue_breakdown = {k: round(v/total_with_issue, 3) for k, v in
                               sorted(issue_counts.items(), key=lambda x: -x[1])}
            top_issue = max(issue_counts, key=issue_counts.get) if issue_counts else None

            prev_events = prev_booth_events.get(booth_id, [])
            prev_issue_counts: dict[str, int] = defaultdict(int)
            for e in prev_events:
                if e["issue"]:
                    prev_issue_counts[e["issue"]] += 1
            prev_total = sum(prev_issue_counts.values()) or 1

            momentum: dict[str, float] = {}
            for issue, cnt in issue_counts.items():
                curr_share = cnt / total_with_issue
                prev_share = prev_issue_counts.get(issue, 0) / prev_total
                if prev_share > 0:
                    momentum[issue] = round((curr_share - prev_share) / prev_share, 3)
                else:
                    momentum[issue] = 1.0 if curr_share > 0 else 0.0

            data_conf = sum(e["final_confidence"] * e.get("geo_confidence", 0.5)
                            for e in events) / len(events)

            metrics_rows.append({
                "booth_id": booth_id,
                "window_start": window_start,
                "window_end": now,
                "bjp_pulse_score": bjp_pulse,
                "opp_pulse_score": opp_pulse,
                "digital_lean": lean,
                "digital_lean_label": _lean_label(lean),
                "top_issue": top_issue,
                "issue_breakdown": json.dumps(issue_breakdown),
                "issue_momentum": json.dumps(momentum),
                "scheme_gap_issues": json.dumps([]),
                "event_count": len(events),
                "data_confidence": round(data_conf, 3),
                "confidence_label": _confidence_label(data_conf, len(events)),
            })

        for row in metrics_rows:
            conn.execute(text("""
                INSERT INTO booth_metrics
                  (booth_id, window_start, window_end,
                   bjp_pulse_score, opp_pulse_score, digital_lean, digital_lean_label,
                   top_issue, issue_breakdown, issue_momentum, scheme_gap_issues,
                   event_count, data_confidence, confidence_label)
                VALUES
                  (:booth_id, :window_start, :window_end,
                   :bjp_pulse_score, :opp_pulse_score, :digital_lean, :digital_lean_label,
                   :top_issue, :issue_breakdown::jsonb, :issue_momentum::jsonb,
                   :scheme_gap_issues::jsonb,
                   :event_count, :data_confidence, :confidence_label)
                ON CONFLICT (booth_id, window_start)
                DO UPDATE SET
                   bjp_pulse_score  = EXCLUDED.bjp_pulse_score,
                   opp_pulse_score  = EXCLUDED.opp_pulse_score,
                   digital_lean     = EXCLUDED.digital_lean,
                   digital_lean_label = EXCLUDED.digital_lean_label,
                   top_issue        = EXCLUDED.top_issue,
                   issue_breakdown  = EXCLUDED.issue_breakdown,
                   issue_momentum   = EXCLUDED.issue_momentum,
                   event_count      = EXCLUDED.event_count,
                   data_confidence  = EXCLUDED.data_confidence,
                   confidence_label = EXCLUDED.confidence_label,
                   last_computed_at = NOW()
            """), row)
        conn.commit()
        logger.info(f"booth_metrics: upserted {len(metrics_rows)} rows")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    eng = sa.create_engine(os.environ["POSTGRES_URL"])
    compute_booth_metrics(eng)
