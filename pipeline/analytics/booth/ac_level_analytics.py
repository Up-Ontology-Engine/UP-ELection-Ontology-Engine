"""
AC-level analytics for GKP_322.

Computes constituency-wide intelligence from ALL pulse_events
(including events with no booth attribution).  Results are stored
using the AC_ID as the key so the API can serve them clearly labeled
as AC-level intelligence rather than pretending they are booth-level.

Tables written to:
  - data_quality_metrics  WHERE booth_id = 'GKP_322'
  - booth_narratives       WHERE booth_id = 'GKP_322'
  - contradiction_flags    WHERE booth_id = 'GKP_322'
  - booth_metrics          WHERE booth_id = 'GKP_322'

All existing analytics modules (data_quality, narrative_detector,
contradiction_detector) already accept any "booth_id" string.  This
module reuses them with the AC_ID as the booth key, passing the correct
SQL filter (mapped_ac_id = 'GKP_322') via a thin adapter.

Usage:
    python -m analytics.ac_level_analytics [--window 365]
"""
from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import datetime, timezone

import sqlalchemy as sa
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()

logger = logging.getLogger(__name__)

AC_ID     = "GKP_322"
AC_PSEUDO_BOOTH_ID = "GKP_322"   # stored as booth_id in analytics tables


def _compute_ac_quality(engine: sa.Engine, window_days: int, computed_at: datetime) -> dict:
    """
    data_quality_metrics computed over all GKP_322 pulse_events
    (not just booth-mapped ones).
    """
    import math
    from datetime import timedelta
    cutoff = computed_at - timedelta(days=window_days)

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                source_type,
                geo_confidence,
                mapped_booth_id,
                mapped_ac_id,
                final_confidence AS nlp_confidence,
                extraction_method,
                entity
            FROM pulse_events
            WHERE mapped_ac_id = :ac
              AND created_at >= :cutoff
              AND created_at <= :now
        """), {"ac": AC_ID, "cutoff": cutoff, "now": computed_at}).fetchall()

    if not rows:
        return {
            "booth_id": AC_PSEUDO_BOOTH_ID,
            "computed_at": computed_at,
            "window_days": window_days,
            "total_events": 0,
            "unique_sources": 0,
            "youtube_pct": 0.0,
            "news_pct": 0.0,
            "survey_pct": 0.0,
            "field_note_pct": 0.0,
            "booth_mapped_pct": 0.0,
            "ac_mapped_pct": 100.0,
            "avg_geo_confidence": 0.0,
            "avg_nlp_confidence": 0.0,
            "llm_extracted_pct": 0.0,
            "entity_match_rate": 0.0,
            "missing_entity_pct": 0.0,
            "source_diversity_score": 0.0,
            "overall_quality_score": 0.0,
            "quality_label": "INSUFFICIENT",
            "quality_reasons": ["No events in window"],
        }

    total = len(rows)
    source_counts: dict[str, int] = {}
    for r in rows:
        src = (r.source_type or "unknown").lower()
        source_counts[src] = source_counts.get(src, 0) + 1

    def pct(src: str) -> float:
        return round(source_counts.get(src, 0) / total * 100, 1)

    shares = [c / total for c in source_counts.values()]
    hhi = sum(s ** 2 for s in shares)
    source_diversity_score = round(1 - hhi, 3)

    booth_mapped = sum(1 for r in rows if r.mapped_booth_id)
    geo_confs  = [r.geo_confidence for r in rows if r.geo_confidence is not None]
    nlp_confs  = [r.nlp_confidence for r in rows if r.nlp_confidence is not None]
    llm_count  = sum(1 for r in rows if r.extraction_method == "llm")
    valid_ent  = sum(1 for r in rows if r.entity and r.entity.strip())

    avg_geo = round(sum(geo_confs) / len(geo_confs), 3) if geo_confs else 0.0
    avg_nlp = round(sum(nlp_confs) / len(nlp_confs), 3) if nlp_confs else 0.0

    volume_score    = min(1.0, math.log1p(total) / math.log1p(200))
    overall = round(
        0.25 * volume_score
        + 0.25 * avg_geo
        + 0.30 * avg_nlp
        + 0.20 * source_diversity_score,
        3,
    )

    reasons: list[str] = []
    if total < 10:
        reasons.append(f"Very few events ({total})")
    dominant = max(source_counts, key=source_counts.__getitem__)
    if source_counts[dominant] / total >= 0.80:
        reasons.append(f"Dominated by {dominant} ({source_counts[dominant]/total*100:.0f}%)")
    if avg_nlp < 0.55 and nlp_confs:
        reasons.append(f"Low NLP confidence (avg {avg_nlp:.2f})")
    if booth_mapped == 0:
        reasons.append("No booth-level geo attribution — all AC-level")

    if overall >= 0.75:
        label = "HIGH"
    elif overall >= 0.50:
        label = "MEDIUM"
    elif overall >= 0.25:
        label = "LOW"
    else:
        label = "INSUFFICIENT"

    return {
        "booth_id": AC_PSEUDO_BOOTH_ID,
        "computed_at": computed_at,
        "window_days": window_days,
        "total_events": total,
        "unique_sources": len(source_counts),
        "youtube_pct": pct("youtube"),
        "news_pct": pct("news"),
        "survey_pct": pct("survey"),
        "field_note_pct": pct("field_note"),
        "booth_mapped_pct": round(booth_mapped / total * 100, 1),
        "ac_mapped_pct": round((total - booth_mapped) / total * 100, 1),
        "avg_geo_confidence": avg_geo,
        "avg_nlp_confidence": avg_nlp,
        "llm_extracted_pct": round(llm_count / total * 100, 1),
        "entity_match_rate": round(valid_ent / total * 100, 1),
        "missing_entity_pct": round((total - valid_ent) / total * 100, 1),
        "source_diversity_score": source_diversity_score,
        "overall_quality_score": overall,
        "quality_label": label,
        "quality_reasons": reasons,
    }


def _compute_ac_booth_metrics(engine: sa.Engine, window_days: int, computed_at: datetime) -> None:
    """
    Compute and upsert booth_metrics for the AC as a whole (booth_id = 'GKP_322').
    Uses weighted polarity across all AC-level pulse_events.
    """
    from datetime import timedelta
    cutoff = computed_at - timedelta(days=window_days)

    with engine.connect() as conn:
        r = conn.execute(text("""
            SELECT
                SUM(CASE WHEN entity ILIKE 'BJP%' THEN final_polarity * final_confidence * source_weight END) /
                    NULLIF(SUM(CASE WHEN entity ILIKE 'BJP%' THEN final_confidence * source_weight END), 0)
                    AS bjp_pulse,
                SUM(CASE WHEN entity IN ('SP','INC','BSP','AAP','AIMIM')
                          THEN final_polarity * final_confidence * source_weight END) /
                    NULLIF(SUM(CASE WHEN entity IN ('SP','INC','BSP','AAP','AIMIM')
                               THEN final_confidence * source_weight END), 0)
                    AS opp_pulse,
                COUNT(*) AS event_count,
                AVG(final_confidence) AS avg_conf
            FROM pulse_events
            WHERE mapped_ac_id = :ac
              AND created_at >= :cutoff
              AND created_at <= :now
              AND final_polarity IS NOT NULL
        """), {"ac": AC_ID, "cutoff": cutoff, "now": computed_at}).mappings().fetchone()

        # Issue breakdown
        issues = conn.execute(text("""
            SELECT final_issue AS issue, COUNT(*) AS n
            FROM pulse_events
            WHERE mapped_ac_id = :ac
              AND created_at >= :cutoff
              AND final_issue IS NOT NULL
            GROUP BY final_issue
            ORDER BY n DESC
        """), {"ac": AC_ID, "cutoff": cutoff}).fetchall()

    bjp_pulse  = round(float(r["bjp_pulse"] or 0), 3)
    opp_pulse  = round(float(r["opp_pulse"] or 0), 3)
    lean       = round(bjp_pulse - opp_pulse, 3)
    events     = int(r["event_count"] or 0)
    conf       = round(float(r["avg_conf"] or 0), 3)

    if lean > 0.15:
        lean_label = "Lean BJP"
    elif lean < -0.15:
        lean_label = "Lean Opposition"
    else:
        lean_label = "Contested"

    issue_counts = {row[0]: int(row[1]) for row in issues}
    top_issue = max(issue_counts, key=issue_counts.__getitem__) if issue_counts else None

    conf_label = (
        "HIGH" if conf >= 0.75 and events >= 50
        else "MEDIUM" if conf >= 0.55 and events >= 20
        else "LOW"
    )

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO booth_metrics (
                booth_id, window_start, window_end,
                bjp_pulse_score, opp_pulse_score, digital_lean, digital_lean_label,
                top_issue, issue_breakdown,
                event_count, data_confidence, confidence_label
            ) VALUES (
                :bid, :ws, :we,
                :bjp, :opp, :lean, :lean_label,
                :top_issue, :issues,
                :events, :conf, :conf_label
            )
            ON CONFLICT (booth_id, window_start) DO UPDATE SET
                bjp_pulse_score   = EXCLUDED.bjp_pulse_score,
                opp_pulse_score   = EXCLUDED.opp_pulse_score,
                digital_lean      = EXCLUDED.digital_lean,
                digital_lean_label = EXCLUDED.digital_lean_label,
                top_issue         = EXCLUDED.top_issue,
                issue_breakdown   = EXCLUDED.issue_breakdown,
                event_count       = EXCLUDED.event_count,
                data_confidence   = EXCLUDED.data_confidence,
                confidence_label  = EXCLUDED.confidence_label
        """), {
            "bid":        AC_PSEUDO_BOOTH_ID,
            "ws":         computed_at,
            "we":         computed_at,
            "bjp":        bjp_pulse,
            "opp":        opp_pulse,
            "lean":       lean,
            "lean_label": lean_label,
            "top_issue":  top_issue,
            "issues":     json.dumps(issue_counts),
            "events":     events,
            "conf":       conf,
            "conf_label": conf_label,
        })

    logger.info(
        "AC-level booth_metrics: BJP=%.3f OPP=%.3f lean=%s events=%d",
        bjp_pulse, opp_pulse, lean_label, events,
    )


def run(engine: sa.Engine, window_days: int = 365) -> dict:
    """
    Run all AC-level analytics for GKP_322.
    Returns a summary dict.
    """
    from analytics.data_quality import upsert_quality_row
    from analytics.narrative_detector import (
        detect_narratives_for_booth, upsert_narrative_rows,
        update_booth_metrics_narrative,
    )
    from analytics.contradiction_detector import (
        detect_contradictions_for_booth, upsert_contradiction_rows,
        update_booth_metrics_consistency,
    )

    computed_at = datetime.now(timezone.utc)
    results: dict = {}

    # 1. Data quality at AC level
    quality = _compute_ac_quality(engine, window_days, computed_at)
    upsert_quality_row(engine, quality)
    results["quality_label"] = quality["quality_label"]
    results["total_events"]  = quality["total_events"]
    logger.info("AC quality: %s (%d events)", quality["quality_label"], quality["total_events"])

    # 2. Booth metrics at AC level (uses pulse_events.mapped_ac_id)
    _compute_ac_booth_metrics(engine, window_days, computed_at)

    # 3. Narratives — detect_narratives_for_booth accepts any "booth_id" string.
    #    We pass the AC_ID; internally it queries WHERE mapped_booth_id = :booth_id
    #    which returns 0 rows.  So we patch in a direct AC-level query instead.
    narratives = _detect_ac_narratives(engine, window_days, computed_at)
    upsert_narrative_rows(engine, narratives)
    update_booth_metrics_narrative(engine, AC_PSEUDO_BOOTH_ID, computed_at)
    results["narratives"] = len(narratives)
    logger.info("AC narratives detected: %d", len(narratives))

    # 4. Contradictions at AC level
    contradictions = _detect_ac_contradictions(engine, window_days, computed_at)
    upsert_contradiction_rows(engine, contradictions)
    update_booth_metrics_consistency(engine, AC_PSEUDO_BOOTH_ID, computed_at)
    results["contradictions"] = len(contradictions)
    logger.info("AC contradictions detected: %d", len(contradictions))

    return results


def _detect_ac_narratives(engine: sa.Engine, window_days: int, computed_at: datetime) -> list[dict]:
    """
    Narrative detection scoped to mapped_ac_id = 'GKP_322'
    (all events, not just booth-mapped).
    """
    from datetime import timedelta
    from analytics.narrative_detector import (
        NARRATIVE_ISSUE_MAP, RULING_PARTY, MIN_STRENGTH,
        _weighted_sentiment, _build_narrative,
    )

    cutoff = computed_at - timedelta(days=window_days)

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                final_issue    AS issue,
                entity,
                entity_type,
                final_polarity  AS final_polarity,
                final_confidence AS nlp_confidence,
                source_type
            FROM pulse_events
            WHERE mapped_ac_id = :ac
              AND created_at >= :cutoff
              AND created_at <= :now
              AND final_polarity IS NOT NULL
        """), {"ac": AC_ID, "cutoff": cutoff, "now": computed_at}).mappings().fetchall()

    if not rows:
        return []

    rows = [dict(r) for r in rows]

    def top_items(field: str, limit: int = 5) -> list[str]:
        counts: dict[str, int] = {}
        for r in rows:
            val = r.get(field)
            if val:
                counts[val] = counts.get(val, 0) + 1
        return [k for k, _ in sorted(counts.items(), key=lambda x: -x[1])[:limit]]

    narratives: list[dict] = []
    bid = AC_PSEUDO_BOOTH_ID

    for narrative_type, issues in NARRATIVE_ISSUE_MAP.items():
        if narrative_type in ("anti_incumbency", "swing_possible"):
            continue
        if not issues:
            continue
        nr = [r for r in rows if r.get("issue") in issues]
        pol, count = _weighted_sentiment(nr)
        threshold = 0.2 if narrative_type in ("development_positive", "scheme_success") else None
        min_count = 3 if narrative_type == "development_positive" else 2

        if threshold is not None:
            ok = count >= min_count and pol >= threshold
        else:
            ok = count >= min_count

        if ok:
            strength = round(pol if pol > 0 else count / max(len(rows), 1), 3)
            narratives.append(_build_narrative(
                bid, narrative_type, computed_at, window_days,
                strength=strength,
                description=f"[AC-level] {narrative_type.replace('_', ' ').title()} — {count} events.",
                top_issues=[r["issue"] for r in nr if r.get("issue")],
                top_entities=[r["entity"] for r in nr if r.get("entity")],
                evidence_count=count,
                confidence=min(1.0, count / 20),
            ))

    # Anti-incumbency
    ruling_rows = [r for r in rows if (r.get("entity") or "").upper() == RULING_PARTY]
    anti_pol, anti_count = _weighted_sentiment(ruling_rows)
    if anti_count >= 3 and anti_pol <= -0.2:
        narratives.append(_build_narrative(
            bid, "anti_incumbency", computed_at, window_days,
            strength=round(abs(anti_pol), 3),
            description=f"[AC-level] Anti-incumbency — {RULING_PARTY} negative across {anti_count} events.",
            top_issues=top_items("issue"),
            top_entities=[RULING_PARTY],
            evidence_count=anti_count,
            confidence=min(1.0, anti_count / 20),
        ))

    return sorted(
        [n for n in narratives if n["strength"] >= MIN_STRENGTH],
        key=lambda x: -x["strength"],
    )


def _detect_ac_contradictions(engine: sa.Engine, window_days: int, computed_at: datetime) -> list[dict]:
    """
    Cross-source contradiction detection scoped to mapped_ac_id = 'GKP_322'.
    """
    import itertools
    from datetime import timedelta
    from analytics.contradiction_detector import (
        MIXED_SIGNALS_DELTA, SWING_INDICATOR_DELTA, MIN_EVENTS_PER_SOURCE,
    )

    cutoff = computed_at - timedelta(days=window_days)

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                entity,
                final_issue         AS issue,
                source_type,
                AVG(final_polarity) AS avg_polarity,
                COUNT(*)            AS event_count
            FROM pulse_events
            WHERE mapped_ac_id = :ac
              AND created_at >= :cutoff
              AND created_at <= :now
              AND entity IS NOT NULL
              AND entity != ''
              AND final_polarity IS NOT NULL
            GROUP BY entity, final_issue, source_type
            HAVING COUNT(*) >= :min_events
        """), {"ac": AC_ID, "cutoff": cutoff, "now": computed_at, "min_events": MIN_EVENTS_PER_SOURCE}).mappings().fetchall()

    grouped: dict[tuple, dict[str, tuple]] = {}
    for r in rows:
        key = (r["entity"], r["issue"])
        grouped.setdefault(key, {})[r["source_type"]] = (float(r["avg_polarity"]), int(r["event_count"]))

    flags: list[dict] = []
    for (entity, issue), source_stats in grouped.items():
        sources = list(source_stats.keys())
        if len(sources) < 2:
            continue
        for src_a, src_b in itertools.combinations(sorted(sources), 2):
            pol_a, cnt_a = source_stats[src_a]
            pol_b, cnt_b = source_stats[src_b]
            delta = abs(pol_a - pol_b)
            if delta < 0.15:
                continue
            if delta >= MIXED_SIGNALS_DELTA:
                flag_label = "MIXED_SIGNALS"
            elif delta >= SWING_INDICATOR_DELTA:
                flag_label = "SWING_INDICATOR"
            else:
                flag_label = "MINOR_DIVERGENCE"

            flags.append({
                "booth_id":          AC_PSEUDO_BOOTH_ID,
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
                "consistency_score": round(1 - (delta / 2), 3),
                "flag_label":        flag_label,
            })

    return sorted(flags, key=lambda x: -x["delta"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--window", type=int, default=365)
    args = parser.parse_args()

    eng = sa.create_engine(os.environ["POSTGRES_URL"])
    result = run(eng, window_days=args.window)
    print("AC-level analytics done:", result)
