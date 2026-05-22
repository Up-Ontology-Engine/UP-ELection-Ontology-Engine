"""
Analytics: Booth-level conversion opportunity scoring.

Computes 4 scores per booth from existing tables (no new data sources needed):

  persuasion_room_score     — how much swing potential exists
                              = f(last election margin, digital lean divergence)
  beneficiary_density_score — welfare scheme coverage relative to voters
                              = sum(beneficiary_count) / total_voters
  turnout_mobilization_score— supportive lean + below-AC-average historical turnout
  service_risk_score        — execution_gap schemes weighted by negative sentiment

  overall_conversion_score  — weighted composite of the above
  recommended_action        — awareness | grievance_redress | mobilization |
                              consolidation | maintain

Run: python -m analytics.conversion_opportunity
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Score weights for the composite
_W_PERSUASION   = 0.35
_W_BENEFICIARY  = 0.25
_W_TURNOUT      = 0.20
_W_SERVICE_RISK = 0.20   # service risk is inverse — high risk = low opportunity


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def _compute_scores(
    total_voters: int,
    last_margin: int | None,
    digital_lean: float | None,
    bjp_pulse: float | None,
    opp_pulse: float | None,
    total_beneficiaries: int,
    ac_avg_turnout: float,
    booth_turnout: float | None,
    execution_gap_count: int,
    total_negative_events: int,
) -> dict:
    # ── Persuasion room ───────────────────────────────────────────────────────
    # Small margin → more persuadable. Digital divergence between sources → swing indicator.
    if last_margin is not None and total_voters and total_voters > 0:
        margin_pct = abs(last_margin) / total_voters
        margin_score = _clamp(1.0 - margin_pct * 4)   # 25%+ margin → 0
    else:
        margin_score = 0.3   # unknown → neutral

    lean_divergence = abs((bjp_pulse or 0) - (opp_pulse or 0))
    divergence_score = _clamp(1.0 - lean_divergence * 2)  # high divergence → contested

    persuasion_room = _clamp((margin_score * 0.6) + (divergence_score * 0.4))

    # ── Beneficiary density ───────────────────────────────────────────────────
    if total_voters and total_voters > 0:
        raw_density = total_beneficiaries / total_voters
        beneficiary_density = _clamp(raw_density * 2)   # 50% coverage → score 1.0
    else:
        beneficiary_density = 0.0

    # ── Turnout mobilization ──────────────────────────────────────────────────
    # Low historical turnout + BJP-leaning (or neutral) booth = mobilization opportunity
    if booth_turnout is not None and ac_avg_turnout > 0:
        turnout_gap = max(0, ac_avg_turnout - booth_turnout)
        turnout_score = _clamp(turnout_gap / 30.0)   # 30-point gap → score 1.0
    else:
        turnout_score = 0.2

    # Only applies if booth is not strongly opposition-leaning
    is_hostile = (digital_lean is not None and digital_lean < -0.3)
    turnout_mobilization = 0.0 if is_hostile else turnout_score

    # ── Service risk ──────────────────────────────────────────────────────────
    risk_base = execution_gap_count * 0.2 + (total_negative_events / 50.0)
    service_risk = _clamp(risk_base)

    # ── Composite ─────────────────────────────────────────────────────────────
    overall = _clamp(
        _W_PERSUASION   * persuasion_room
        + _W_BENEFICIARY  * beneficiary_density
        + _W_TURNOUT      * turnout_mobilization
        + _W_SERVICE_RISK * (1.0 - service_risk)   # invert: low risk → better
    )

    return {
        "persuasion_room_score":       round(persuasion_room, 3),
        "beneficiary_density_score":   round(beneficiary_density, 3),
        "turnout_mobilization_score":  round(turnout_mobilization, 3),
        "service_risk_score":          round(service_risk, 3),
        "overall_conversion_score":    round(overall, 3),
    }


def _recommend(scores: dict, digital_lean: float | None) -> tuple[str, str]:
    prs  = scores["persuasion_room_score"]
    bds  = scores["beneficiary_density_score"]
    tms  = scores["turnout_mobilization_score"]
    srs  = scores["service_risk_score"]

    if srs > 0.6:
        return (
            "grievance_redress",
            "High service risk detected — execution gaps dominate. "
            "Fix last-mile delivery before campaigning; unresolved grievances cancel welfare credit.",
        )
    if bds > 0.4 and prs > 0.4:
        return (
            "awareness",
            "Strong welfare presence but credit not captured. "
            "Run beneficiary outreach camps; connect delivery to political narrative.",
        )
    if tms > 0.5:
        return (
            "mobilization",
            "Below-average historical turnout with convertible base. "
            "Focus on voter mobilization, booth-agent activation, and transport support.",
        )
    if prs > 0.5:
        return (
            "consolidation",
            "Thin margin and swing signals detected. "
            "Deploy direct contact for undecided voters; reinforce local candidate presence.",
        )
    return (
        "maintain",
        "Booth appears stable. Maintain current ground presence and monitor for shifts.",
    )


def run_all_booths(engine: sa.Engine) -> int:
    now = datetime.now(timezone.utc)

    with engine.connect() as conn:
        # AC-average turnout for relative scoring
        ac_avg_row = conn.execute(text("""
            SELECT COALESCE(AVG(ts.turnout_percent), 60.0) AS ac_avg_turnout
            FROM turnout_stats ts
            WHERE ts.election_year = (SELECT MAX(election_year) FROM turnout_stats)
        """)).fetchone()
        ac_avg_turnout = float(ac_avg_row[0]) if ac_avg_row else 60.0

        # Per-booth input data
        rows = conn.execute(text("""
            SELECT
                b.booth_id,
                b.total_voters,
                bm.digital_lean,
                bm.bjp_pulse_score,
                bm.opp_pulse_score,
                -- Last election margin (winner votes - runner-up votes)
                (
                    SELECT br1.votes - br2.votes
                    FROM booth_results br1
                    JOIN booth_results br2
                      ON br2.booth_id = br1.booth_id
                     AND br2.election_year = br1.election_year
                     AND br2.winner_flag = FALSE
                    WHERE br1.booth_id = b.booth_id
                      AND br1.winner_flag = TRUE
                    ORDER BY br1.election_year DESC
                    LIMIT 1
                ) AS last_margin,
                -- Total beneficiaries from scheme activity near booth
                COALESCE((
                    SELECT SUM(sga.beneficiary_count)
                    FROM scheme_gap_analysis sga
                    WHERE sga.booth_id = b.booth_id
                ), 0) AS total_beneficiaries,
                -- Execution gap count
                COALESCE((
                    SELECT COUNT(*)
                    FROM scheme_gap_analysis sga
                    WHERE sga.booth_id = b.booth_id
                      AND sga.gap_type = 'execution_gap'
                ), 0) AS execution_gap_count,
                -- Negative sentiment events
                COALESCE((
                    SELECT COUNT(*)
                    FROM pulse_events pe
                    WHERE pe.mapped_booth_id = b.booth_id
                      AND pe.final_polarity = -1
                ), 0) AS total_negative_events,
                -- Latest turnout
                (
                    SELECT ts.turnout_percent
                    FROM turnout_stats ts
                    WHERE ts.booth_id = b.booth_id
                    ORDER BY ts.election_year DESC
                    LIMIT 1
                ) AS booth_turnout
            FROM booth_master b
            LEFT JOIN LATERAL (
                SELECT bjp_pulse_score, opp_pulse_score, digital_lean
                FROM booth_metrics
                WHERE booth_id = b.booth_id
                ORDER BY window_start DESC LIMIT 1
            ) bm ON TRUE
            WHERE b.booth_id NOT LIKE '%_TOTAL'
        """)).mappings().fetchall()

    upserted = 0
    with engine.begin() as conn:
        for r in rows:
            scores = _compute_scores(
                total_voters        = int(r["total_voters"] or 0),
                last_margin         = r["last_margin"],
                digital_lean        = r["digital_lean"],
                bjp_pulse           = r["bjp_pulse_score"],
                opp_pulse           = r["opp_pulse_score"],
                total_beneficiaries = int(r["total_beneficiaries"] or 0),
                ac_avg_turnout      = ac_avg_turnout,
                booth_turnout       = r["booth_turnout"],
                execution_gap_count = int(r["execution_gap_count"] or 0),
                total_negative_events = int(r["total_negative_events"] or 0),
            )
            action, reason = _recommend(scores, r["digital_lean"])

            conn.execute(text("""
                INSERT INTO conversion_opportunity (
                    booth_id, persuasion_room_score, beneficiary_density_score,
                    turnout_mobilization_score, service_risk_score,
                    overall_conversion_score, recommended_action, action_reason,
                    computed_at
                ) VALUES (
                    :booth_id, :persuasion_room_score, :beneficiary_density_score,
                    :turnout_mobilization_score, :service_risk_score,
                    :overall_conversion_score, :recommended_action, :action_reason,
                    :computed_at
                )
                ON CONFLICT (booth_id) DO UPDATE SET
                    persuasion_room_score      = EXCLUDED.persuasion_room_score,
                    beneficiary_density_score  = EXCLUDED.beneficiary_density_score,
                    turnout_mobilization_score = EXCLUDED.turnout_mobilization_score,
                    service_risk_score         = EXCLUDED.service_risk_score,
                    overall_conversion_score   = EXCLUDED.overall_conversion_score,
                    recommended_action         = EXCLUDED.recommended_action,
                    action_reason              = EXCLUDED.action_reason,
                    computed_at                = EXCLUDED.computed_at
            """), {**scores, "booth_id": r["booth_id"],
                   "recommended_action": action, "action_reason": reason,
                   "computed_at": now})
            upserted += 1

    logger.info("Conversion opportunity computed for %d booths", upserted)
    return upserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    engine = sa.create_engine(os.environ["POSTGRES_URL"])
    n = run_all_booths(engine)
    print(f"Done — {n} booths scored")
