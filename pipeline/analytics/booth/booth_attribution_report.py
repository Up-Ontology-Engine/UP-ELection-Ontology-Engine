"""
Booth attribution validation report — GKP_322.

Produces an honest audit of what fraction of pulse_events are genuinely
booth-attributed vs AC-level, detects synthetic cloning patterns, and
lists top unresolved locality mentions for human alias review.

Output: prints a formatted report + optionally writes JSON to --out file.

Usage:
    python -m analytics.booth_attribution_report
    python -m analytics.booth_attribution_report --out report.json
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

CLONE_SCORE_TOLERANCE = 0.001  # booth pulse scores within this range flagged as clone suspects
MIN_BOOTHS_FOR_CLONE_CHECK = 3


def run(engine: sa.Engine) -> dict:
    report: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ac_id": "GKP_322",
    }

    with engine.connect() as conn:
        # ── 1. Overall attribution breakdown ─────────────────────────────
        agg = (
            conn.execute(
                text("""
            SELECT
                COUNT(*)                                    AS total,
                COUNT(*) FILTER (WHERE mapped_booth_id IS NOT NULL
                                   AND geo_confidence >= 0.75)  AS booth_high_conf,
                COUNT(*) FILTER (WHERE mapped_booth_id IS NOT NULL
                                   AND geo_confidence < 0.75)   AS booth_low_conf,
                COUNT(*) FILTER (WHERE mapped_booth_id IS NULL
                                   AND mapped_ac_id IS NOT NULL) AS ac_level,
                COUNT(*) FILTER (WHERE mapped_booth_id IS NULL
                                   AND mapped_ac_id IS NULL)     AS unresolved,
                AVG(geo_confidence) FILTER (WHERE geo_confidence IS NOT NULL) AS avg_geo_conf
            FROM pulse_events
            WHERE mapped_ac_id = 'GKP_322'
        """)
            )
            .mappings()
            .fetchone()
        )

        r = dict(agg) if agg else {}
        total = int(r.get("total") or 0)
        report["totals"] = {
            "total_events": total,
            "booth_high_conf": int(r.get("booth_high_conf") or 0),
            "booth_low_conf": int(r.get("booth_low_conf") or 0),
            "ac_level": int(r.get("ac_level") or 0),
            "unresolved": int(r.get("unresolved") or 0),
            "avg_geo_confidence": round(float(r.get("avg_geo_conf") or 0), 3),
        }
        if total > 0:
            report["totals"]["pct_booth_attributed"] = round(
                100 * report["totals"]["booth_high_conf"] / total, 1
            )
            report["totals"]["pct_ac_level"] = round(
                100 * (report["totals"]["ac_level"] + report["totals"]["booth_low_conf"]) / total, 1
            )

        # ── 2. Booth-level distribution ───────────────────────────────────
        booth_dist = (
            conn.execute(
                text("""
            SELECT mapped_booth_id, COUNT(*) AS n,
                   AVG(geo_confidence) AS avg_conf,
                   COUNT(DISTINCT source_type) AS source_types
            FROM pulse_events
            WHERE mapped_booth_id IS NOT NULL
              AND mapped_ac_id = 'GKP_322'
            GROUP BY mapped_booth_id
            ORDER BY n DESC
        """)
            )
            .mappings()
            .fetchall()
        )

        report["booth_distribution"] = [
            {
                "booth_id": r["mapped_booth_id"],
                "event_count": int(r["n"]),
                "avg_geo_conf": round(float(r["avg_conf"]), 3),
                "source_types": int(r["source_types"]),
            }
            for r in booth_dist
        ]

        # ── 3. Top unresolved location_text values ────────────────────────
        unresolved_locs = conn.execute(
            text("""
            SELECT location_text, COUNT(*) AS n
            FROM pulse_events
            WHERE location_text IS NOT NULL
              AND location_text != ''
              AND mapped_booth_id IS NULL
              AND mapped_ac_id = 'GKP_322'
            GROUP BY location_text
            ORDER BY n DESC
            LIMIT 30
        """)
        ).fetchall()

        report["top_unresolved_localities"] = [
            {"location_text": r[0], "count": int(r[1])} for r in unresolved_locs
        ]

        # ── 4. Source type breakdown ──────────────────────────────────────
        source_dist = (
            conn.execute(
                text("""
            SELECT source_type, geo_level, COUNT(*) AS n
            FROM pulse_events
            WHERE mapped_ac_id = 'GKP_322'
            GROUP BY source_type, geo_level
            ORDER BY source_type, geo_level
        """)
            )
            .mappings()
            .fetchall()
        )

        report["source_geo_breakdown"] = [
            {"source": r["source_type"], "geo_level": r["geo_level"], "count": int(r["n"])}
            for r in source_dist
        ]

        # ── 5. Synthetic clone detection ──────────────────────────────────
        # Flag if multiple booths have identical bjp_pulse_score or opp_pulse_score
        clone_check = (
            conn.execute(
                text("""
            SELECT bjp_pulse_score, opp_pulse_score, COUNT(*) AS booth_count
            FROM booth_metrics
            WHERE booth_id LIKE 'GKP_322_%'
            GROUP BY bjp_pulse_score, opp_pulse_score
            HAVING COUNT(*) >= :min_booths
               AND bjp_pulse_score IS NOT NULL
            ORDER BY booth_count DESC
        """),
                {"min_booths": MIN_BOOTHS_FOR_CLONE_CHECK},
            )
            .mappings()
            .fetchall()
        )

        clone_suspects = [
            {
                "bjp_pulse_score": r["bjp_pulse_score"],
                "opp_pulse_score": r["opp_pulse_score"],
                "booth_count": int(r["booth_count"]),
                "flag": "SYNTHETIC_CLONE_SUSPECT",
            }
            for r in clone_check
        ]
        report["clone_suspects"] = clone_suspects
        report["has_clone_suspect"] = len(clone_suspects) > 0

        # ── 6. Recommended alias additions ───────────────────────────────
        # Top location_texts that appear 3+ times but aren't booth-mapped
        alias_candidates = [loc for loc in report["top_unresolved_localities"] if loc["count"] >= 3]
        report["recommended_alias_additions"] = alias_candidates

    return report


def _print_report(r: dict) -> None:
    t = r["totals"]
    print(f"\n{'='*60}")
    print(f"  BOOTH ATTRIBUTION REPORT — {r['ac_id']}")
    print(f"  Generated: {r['generated_at']}")
    print(f"{'='*60}")
    print(f"\n  Total pulse events:       {t['total_events']}")
    print(
        f"  Booth-attributed (>=0.75): {t['booth_high_conf']}  ({t.get('pct_booth_attributed', 0):.1f}%)"
    )
    print(f"  AC-level only:            {t['ac_level']}  ({t.get('pct_ac_level', 0):.1f}%)")
    print(f"  Unresolved:               {t['unresolved']}")
    print(f"  Avg geo confidence:       {t['avg_geo_confidence']:.3f}")

    if r["booth_distribution"]:
        print(f"\n  Booth distribution ({len(r['booth_distribution'])} booths with events):")
        for b in r["booth_distribution"][:10]:
            print(
                f"    {b['booth_id']}  events={b['event_count']}  "
                f"avg_conf={b['avg_geo_conf']:.2f}  sources={b['source_types']}"
            )

    if r["top_unresolved_localities"]:
        print("\n  Top unresolved locality mentions:")
        for loc in r["top_unresolved_localities"][:10]:
            print(f"    {loc['location_text']!r:<35}  count={loc['count']}")

    if r["clone_suspects"]:
        print(
            f"\n  ⚠  CLONE SUSPECTS ({len(r['clone_suspects'])} score groups with {MIN_BOOTHS_FOR_CLONE_CHECK}+ identical booths):"
        )
        for c in r["clone_suspects"][:5]:
            print(
                f"    BJP={c['bjp_pulse_score']} OPP={c['opp_pulse_score']}  "
                f"across {c['booth_count']} booths — likely synthetic"
            )
    else:
        print("\n  ✓  No synthetic clone patterns detected.")

    if r["recommended_alias_additions"]:
        print("\n  Recommended alias additions (appear 3+ times, unmapped):")
        for loc in r["recommended_alias_additions"]:
            print(f"    {loc['location_text']!r}  (count={loc['count']})")
    print()


if __name__ == "__main__":
    import io
    import sys

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", help="Write JSON report to file")
    args = parser.parse_args()

    eng = sa.create_engine(os.environ["POSTGRES_URL"])
    report = run(eng)
    _print_report(report)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        print(f"Report written to {args.out}")
