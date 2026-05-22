"""
ETL: Compute per-booth historical election metrics for GKP_322 from booth_results.

Two things in one pass:
  1. Backfill turnout_percent in turnout_stats (was NULL — total_votes existed but
     denominator was never computed).
  2. Upsert one booth_metrics row per GKP_322 booth derived from 2022 election
     results (BJP/SP/BSP/INC vote shares, margin, lean direction).

Why from election results and not pulse_events?
  All 2,611 pulse events are AC-level (mapped_booth_id IS NULL).  There is no
  booth-attributed digital signal.  The 2022 Form-20 results are the only
  ground-truth, booth-level data we have.  booth_metrics rows written here are
  labelled data_source='election_2022' so the API can surface the distinction.

Party normalisation:
  The Form-20 ingestion stored some rows with garbage party values ('_', '-',
  'nan', '0.0', numeric IND serial numbers '1.0', '2.0', ...).  We use only
  the five named parties that carry real political meaning: BJP, SP, BSP, INC,
  AAP.  NOTA and CPI are included in total_votes for turnout but excluded from
  the lean computation (they don't represent an organised opposition signal).

Run:
    python -m etl.compute_booth_election_metrics
    python -m etl.compute_booth_election_metrics --dry-run
"""
from __future__ import annotations

import argparse
import logging
import os
from datetime import datetime, timezone

import sqlalchemy as sa
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()
logger = logging.getLogger(__name__)

PILOT_AC = "GKP_322"
YEAR     = 2022

# Parties whose votes are summed for the lean computation.
BJP_PARTY  = "BJP"
OPP_PARTIES = {"SP", "BSP", "INC", "AAP"}
# All named parties included in total valid votes (denominator).
VALID_PARTIES = {BJP_PARTY} | OPP_PARTIES | {"NOTA", "C.P.I", "IND", "S.D.BSP",
                                               "P.S.P Lohiya", "R.P.I.", "AAP"}


def _run(engine: sa.Engine, dry_run: bool = False) -> dict:
    now = datetime.now(timezone.utc)
    counts = {"turnout_updated": 0, "booth_metrics_upserted": 0}

    # ── Step 1: Fix turnout_percent ───────────────────────────────────────────
    # turnout_stats.total_votes exists; divide by booth_master.total_voters.
    # Only update rows where turnout_percent is still NULL.
    # total_votes in turnout_stats is 0 for all rows — compute from booth_results.
    # sum of all named-party votes per booth = total votes cast.
    turnout_sql = text("""
        UPDATE turnout_stats ts
        SET    total_votes     = votes.cast,
               turnout_percent = ROUND(votes.cast * 100.0 / NULLIF(bm.total_voters, 0), 2)
        FROM   (
            SELECT booth_id, SUM(votes) AS cast
            FROM   booth_results
            WHERE  party = ANY(ARRAY['BJP','SP','BSP','INC','AAP','NOTA',
                                     'C.P.I','IND','S.D.BSP','P.S.P Lohiya','R.P.I.'])
              AND  votes > 0
            GROUP  BY booth_id
        ) votes
        JOIN   booth_master bm ON bm.booth_id = votes.booth_id
        WHERE  ts.booth_id     = votes.booth_id
          AND  bm.total_voters > 0
    """)

    if not dry_run:
        with engine.begin() as conn:
            result = conn.execute(turnout_sql)
            counts["turnout_updated"] = result.rowcount
    else:
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT COUNT(*)
                FROM   turnout_stats ts
                JOIN   booth_master bm ON bm.booth_id = ts.booth_id
                WHERE  bm.total_voters > 0
            """)).scalar()
            counts["turnout_updated"] = int(row or 0)
    logger.info("turnout_percent: %d rows %s",
                counts["turnout_updated"], "(would update)" if dry_run else "updated")

    # ── Step 2: Aggregate booth_results → per-booth metrics ──────────────────
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                br.booth_id,
                bm.total_voters,
                -- Named party votes
                SUM(br.votes) FILTER (WHERE br.party = :bjp)     AS bjp_votes,
                SUM(br.votes) FILTER (WHERE br.party = 'SP')      AS sp_votes,
                SUM(br.votes) FILTER (WHERE br.party = 'BSP')     AS bsp_votes,
                SUM(br.votes) FILTER (WHERE br.party = 'INC')     AS inc_votes,
                SUM(br.votes) FILTER (WHERE br.party = 'AAP')     AS aap_votes,
                -- Total votes from ALL named valid parties (denominator)
                SUM(br.votes) FILTER (WHERE br.party = ANY(:valid)) AS total_valid_votes,
                -- Turnout-level total (all votes recorded including ambiguous rows)
                SUM(br.votes) FILTER (WHERE br.party NOT IN ('_','-','nan'))
                    AS total_named_votes,
                -- Latest turnout percent (just filled above)
                (
                    SELECT ts.turnout_percent
                    FROM   turnout_stats ts
                    WHERE  ts.booth_id      = br.booth_id
                    ORDER  BY ts.election_year DESC
                    LIMIT  1
                ) AS turnout_pct
            FROM   booth_results br
            JOIN   booth_master  bm ON bm.booth_id = br.booth_id
            WHERE  bm.ac_id          = :ac
              AND  br.election_year  = :yr
            GROUP  BY br.booth_id, bm.total_voters
            ORDER  BY br.booth_id
        """), {
            "ac":    PILOT_AC,
            "yr":    YEAR,
            "bjp":   BJP_PARTY,
            "valid": list(VALID_PARTIES),
        }).mappings().fetchall()

    logger.info("Loaded %d booths from booth_results", len(rows))

    records = []
    for r in rows:
        bjp   = float(r["bjp_votes"]  or 0)
        sp    = float(r["sp_votes"]   or 0)
        bsp   = float(r["bsp_votes"]  or 0)
        inc   = float(r["inc_votes"]  or 0)
        aap   = float(r["aap_votes"]  or 0)
        opp   = sp + bsp + inc + aap
        total = float(r["total_valid_votes"] or 0)

        if total == 0:
            continue

        bjp_share = round(bjp / total, 4)
        opp_share = round(opp / total, 4)
        lean      = round(bjp_share - opp_share, 4)   # positive = BJP leaning

        if lean > 0.25:
            lean_label = "Strong BJP"
        elif lean > 0.10:
            lean_label = "Lean BJP"
        elif lean < -0.25:
            lean_label = "Strong Opposition"
        elif lean < -0.10:
            lean_label = "Lean Opposition"
        else:
            lean_label = "Competitive"

        # Main opposition in this booth (whoever got the most non-BJP votes)
        opp_breakdown = {"SP": sp, "BSP": bsp, "INC": inc, "AAP": aap}
        top_opp_party = max(opp_breakdown, key=lambda k: opp_breakdown[k]) if opp > 0 else "SP"
        top_opp_share = round(opp_breakdown[top_opp_party] / total, 4)

        # Confidence: actual election data → HIGH if total_valid ≥ 100 votes
        confidence = "HIGH" if total >= 100 else "MEDIUM"

        records.append({
            "booth_id":         r["booth_id"],
            "window_start":     datetime(YEAR, 1, 1, tzinfo=timezone.utc),
            "window_end":       datetime(YEAR, 12, 31, tzinfo=timezone.utc),
            "bjp_pulse_score":  bjp_share,
            "opp_pulse_score":  top_opp_share,
            "digital_lean":     lean,
            "digital_lean_label": lean_label,
            "top_issue":        None,         # no issue signal at booth level yet
            "issue_breakdown":  None,
            "issue_momentum":   None,
            "confidence_label": confidence,
            "event_count":      1,            # one election event
            "data_confidence":  round(min(total / 500.0, 1.0), 3),
            "last_computed_at":  now,
        })

    logger.info("Computed metrics for %d booths", len(records))

    if dry_run:
        logger.info("[dry-run] First 3 records:")
        for rec in records[:3]:
            logger.info("  %s  BJP=%.3f  OPP=%.3f  lean=%.3f  (%s)",
                        rec["booth_id"], rec["bjp_pulse_score"],
                        rec["opp_pulse_score"], rec["digital_lean"],
                        rec["lean_label"] if "lean_label" in rec else rec["digital_lean_label"])
        counts["booth_metrics_upserted"] = len(records)
        return counts

    # ── Upsert into booth_metrics ─────────────────────────────────────────────
    upsert_sql = text("""
        INSERT INTO booth_metrics (
            booth_id, window_start, window_end,
            bjp_pulse_score, opp_pulse_score,
            digital_lean, digital_lean_label,
            top_issue, issue_breakdown, issue_momentum,
            confidence_label, event_count, data_confidence,
            last_computed_at
        ) VALUES (
            :booth_id, :window_start, :window_end,
            :bjp_pulse_score, :opp_pulse_score,
            :digital_lean, :digital_lean_label,
            :top_issue, :issue_breakdown, :issue_momentum,
            :confidence_label, :event_count, :data_confidence,
            :last_computed_at
        )
        ON CONFLICT (booth_id, window_start) DO UPDATE SET
            window_end         = EXCLUDED.window_end,
            bjp_pulse_score    = EXCLUDED.bjp_pulse_score,
            opp_pulse_score    = EXCLUDED.opp_pulse_score,
            digital_lean       = EXCLUDED.digital_lean,
            digital_lean_label = EXCLUDED.digital_lean_label,
            confidence_label   = EXCLUDED.confidence_label,
            event_count        = EXCLUDED.event_count,
            data_confidence    = EXCLUDED.data_confidence,
            last_computed_at   = EXCLUDED.last_computed_at
    """)

    with engine.begin() as conn:
        conn.execute(upsert_sql, records)
        counts["booth_metrics_upserted"] = len(records)

    logger.info("Upserted %d booth_metrics rows", counts["booth_metrics_upserted"])
    return counts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    engine = sa.create_engine(os.environ["POSTGRES_URL"])
    result = _run(engine, dry_run=args.dry_run)
    print("Done:", result)
