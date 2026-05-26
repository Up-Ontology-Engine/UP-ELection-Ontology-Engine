"""
Ingest Form-20 election results → booth_metrics lean labels.

Reads AC322.json (2022 UP Vidhan Sabha results), computes per-booth
BJP / SP / BSP vote shares, derives digital_lean_label, and inserts a
fresh booth_metrics row for every booth so the dashboard shows real data.

Run:
  python -m ingestion.ingest_form20_lean
  python -m ingestion.ingest_form20_lean --dry-run
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT       = Path(__file__).parents[1]
FORM20_JSON = ROOT / "data" / "Form20_JSON" / "AC322.json"
AC_ID      = "GKP_322"
AC_NO      = 322

BJP_ALIASES  = {"B.J.P", "BJP", "B.J.P."}
SP_ALIASES   = {"Samajwadi Party", "S.P.", "SP"}
BSP_ALIASES  = {"B.S.P.", "BSP", "B.S.P"}


def party_tag(raw: str) -> str:
    r = (raw or "").strip()
    for a in BJP_ALIASES:
        if a in r:
            return "BJP"
    for a in SP_ALIASES:
        if a in r:
            return "SP"
    for a in BSP_ALIASES:
        if a in r:
            return "BSP"
    return "OTHER"


def compute_lean(bjp: int, sp: int, bsp: int, total_valid: int) -> tuple[str, float, float]:
    """Return (lean_label, bjp_pulse_score, opp_pulse_score)."""
    if total_valid == 0:
        return "NEUTRAL", 0.0, 0.0

    bjp_share    = bjp / total_valid
    sp_bsp_share = (sp + bsp) / total_valid

    # bjp_pulse_score: normalised advantage, centred at 0
    # +1 = all votes for BJP, -1 = all for others
    bjp_pulse  = round(bjp_share * 2 - 1, 4)
    opp_pulse  = round(sp_bsp_share * 2 - 1, 4)

    margin = bjp_share - sp_bsp_share

    if bjp_share >= 0.55:
        label = "STRONG_BJP"
    elif bjp_share >= 0.45:
        label = "LEAN_BJP"
    elif margin >= -0.05:        # within 5% — call it neutral
        label = "NEUTRAL"
    elif sp_bsp_share - bjp_share < 0.15:
        label = "LEAN_OPP"
    else:
        label = "STRONG_OPP"

    return label, bjp_pulse, opp_pulse


def load_form20() -> dict[int, dict]:
    """Parse AC322.json and return mapping ps_number → vote data."""
    raw = json.loads(FORM20_JSON.read_text(encoding="utf-8"))
    stations = raw["sheets"][0]["polling_stations"]
    result: dict[int, dict] = {}

    for s in stations:
        ps_num = s["polling_station_number"]
        bjp = sp = bsp = total = 0
        for cv in s.get("candidate_votes", []):
            v = cv.get("votes") or 0
            tag = party_tag(cv.get("party", ""))
            total += v
            if tag == "BJP":  bjp  += v
            elif tag == "SP": sp   += v
            elif tag == "BSP":bsp  += v

        result[ps_num] = {
            "ps_num":   ps_num,
            "electors": s.get("total_electors", 0) or 0,
            "turnout":  s.get("turnout_total", 0)  or 0,
            "bjp":      bjp,
            "sp":       sp,
            "bsp":      bsp,
            "total":    total,
        }
    return result


def run(dry_run: bool = False) -> None:
    import os
    sys.path.insert(0, str(ROOT))
    from dotenv import load_dotenv
    load_dotenv()
    from sqlalchemy import create_engine, text

    form20 = load_form20()
    logger.info("Loaded %d polling stations from Form-20", len(form20))

    rows = []
    now  = datetime.now(timezone.utc)

    engine = create_engine(os.environ["POSTGRES_URL"])
    with engine.connect() as conn:
        db_booths = conn.execute(text(
            "SELECT booth_id, booth_number FROM booth_master ORDER BY booth_number"
        )).fetchall()

    for row in db_booths:
        booth_id  = row[0]
        booth_num = row[1]
        data      = form20.get(booth_num)

        if data is None:
            logger.warning("No Form-20 data for booth %d — skipping", booth_num)
            continue

        label, bjp_pulse, opp_pulse = compute_lean(
            data["bjp"], data["sp"], data["bsp"], data["total"]
        )
        digital_lean = round(bjp_pulse - opp_pulse, 4)

        # Confidence: HIGH if turnout > 0, MEDIUM if electors known, LOW otherwise
        if data["turnout"] > 0:
            conf = "HIGH"
        elif data["electors"] > 0:
            conf = "MEDIUM"
        else:
            conf = "LOW"

        rows.append({
            "booth_id":         booth_id,
            "window_start":     now,
            "window_end":       now,
            "bjp_pulse_score":  bjp_pulse,
            "opp_pulse_score":  opp_pulse,
            "digital_lean":     digital_lean,
            "digital_lean_label": label,
            "confidence_label": conf,
            "event_count":      data["turnout"],
            "top_issue":        None,
        })

    # Print preview
    from collections import Counter
    label_counts = Counter(r["digital_lean_label"] for r in rows)
    logger.info("Lean distribution preview:")
    for lbl, cnt in sorted(label_counts.items(), key=lambda x: -x[1]):
        logger.info("  %-15s %3d booths", lbl, cnt)

    if dry_run:
        logger.info("Dry-run — no writes.")
        return
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO booth_metrics
                (booth_id, window_start, window_end,
                 bjp_pulse_score, opp_pulse_score, digital_lean, digital_lean_label,
                 confidence_label, event_count, top_issue)
            VALUES
                (:booth_id, :window_start, :window_end,
                 :bjp_pulse_score, :opp_pulse_score, :digital_lean, :digital_lean_label,
                 :confidence_label, :event_count, :top_issue)
            ON CONFLICT (booth_id, window_start) DO UPDATE
                SET opp_pulse_score   = EXCLUDED.opp_pulse_score,
                    bjp_pulse_score   = EXCLUDED.bjp_pulse_score,
                    digital_lean      = EXCLUDED.digital_lean,
                    digital_lean_label= EXCLUDED.digital_lean_label,
                    confidence_label  = EXCLUDED.confidence_label,
                    event_count       = EXCLUDED.event_count
        """), rows)

    logger.info("Inserted %d rows into booth_metrics", len(rows))

    # Verify distribution
    with engine.connect() as conn:
        dist = conn.execute(text("""
            SELECT digital_lean_label, COUNT(*) AS n
            FROM (
                SELECT DISTINCT ON (booth_id) booth_id, digital_lean_label
                FROM booth_metrics
                ORDER BY booth_id, window_start DESC
            ) latest
            GROUP BY digital_lean_label
            ORDER BY n DESC
        """)).fetchall()
        logger.info("Live dashboard distribution (latest per booth):")
        for row in dist:
            logger.info("  %-15s %3d", row[0], row[1])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
