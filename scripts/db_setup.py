"""
db_setup.py
============
One-shot database initialisation + full ETL runner.

Diagnosis:
  - booth_master: 0 rows  ← this is why "No booth data available" 
  - booth_results: 0 rows ← no election results loaded
  - All other dynamic tables also empty (pulse, news, youtube etc.)
  - ac_master: 10 rows ✓ (already seeded)
  - candidate_master: 25 rows ✓ (already seeded)

This script runs ALL ETL steps in the correct order using the venv Python.

Run:
  .\\venv\\Scripts\\python.exe scripts\\db_setup.py
"""

from __future__ import annotations
import logging
import os
import sys
from pathlib import Path

# Ensure project root is on path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

import sqlalchemy as sa

def get_engine():
    url = os.environ.get("POSTGRES_URL")
    if not url:
        raise RuntimeError("POSTGRES_URL not set in .env")
    return sa.create_engine(url, pool_pre_ping=True)


def check_row_counts(engine):
    key_tables = [
        "ac_master", "booth_master", "booth_results",
        "candidate_master", "pulse_events", "news_articles",
        "scheme_gap_analysis", "turnout_stats",
    ]
    log.info("── Current table state ──────────────────────────")
    with engine.connect() as conn:
        for t in key_tables:
            try:
                n = conn.execute(sa.text(f'SELECT COUNT(*) FROM "{t}"')).scalar()
                status = "✓" if n > 0 else "✗ EMPTY"
                log.info("  %-30s %6d rows  %s", t, n, status)
            except Exception as e:
                log.warning("  %-30s  ERROR: %s", t, e)


def step1_geography(engine):
    log.info("STEP 1 — Geography: ac_master + booth_master")
    from etl.transform_geography import load_ac_master, load_booth_master, validate
    load_ac_master(engine)
    n = load_booth_master(engine)
    validate(engine)
    log.info("✓ Step 1 done: %d booths loaded", n)
    return n


def step2_candidates(engine):
    log.info("STEP 2 — Candidates: transform + seed affidavits")
    try:
        from etl.transform_candidates import run as cand_run
        cand_run()
        log.info("✓ transform_candidates done")
    except Exception as e:
        log.warning("transform_candidates skipped: %s", e)

    try:
        from etl.seed_known_candidates import run as seed_run
        seed_run()
        log.info("✓ seed_known_candidates done")
    except Exception as e:
        log.warning("seed_known_candidates skipped: %s", e)


def step3_booth_results(engine):
    log.info("STEP 3 — Booth election results from Form20 XLS/JSON")
    try:
        from etl.parse_form20_xls import run as parse_xls_run
        parse_xls_run()
        log.info("✓ parse_form20_xls done")
    except Exception as e:
        log.warning("parse_form20_xls skipped: %s", e)

    try:
        from etl.aggregate_form20_results import run as f20_run
        f20_run()
        log.info("✓ aggregate_form20_results done")
    except Exception as e:
        log.warning("aggregate_form20_results skipped: %s", e)

    # Compute booth election metrics from results
    try:
        from etl.compute_booth_election_metrics import run as bem_run
        bem_run()
        log.info("✓ compute_booth_election_metrics done")
    except Exception as e:
        log.warning("compute_booth_election_metrics skipped: %s", e)

    # Baseline loader for party normalisation and turnout stats
    try:
        from etl.load_gorakhpur_baseline import run as baseline_run
        baseline_run()
        log.info("✓ load_gorakhpur_baseline done")
    except Exception as e:
        log.warning("load_gorakhpur_baseline skipped: %s", e)


def step4_schemes(engine):
    log.info("STEP 4 — Schemes")
    try:
        from etl.transform_schemes import run as scheme_run
        scheme_run()
        log.info("✓ transform_schemes done")
    except Exception as e:
        log.warning("transform_schemes skipped: %s", e)

    try:
        from etl.load_real_schemes import run as real_run
        real_run()
        log.info("✓ load_real_schemes done")
    except Exception as e:
        log.warning("load_real_schemes skipped: %s", e)


def step5_panchayats(engine):
    log.info("STEP 5 — Panchayats")
    try:
        from etl.transform_panchayats import run as pan_run
        pan_run()
        log.info("✓ transform_panchayats done")
    except Exception as e:
        log.warning("transform_panchayats skipped: %s", e)


def step6_news(engine):
    log.info("STEP 6 — News")
    try:
        from etl.transform_news import run as news_run
        news_run()
        log.info("✓ transform_news done")
    except Exception as e:
        log.warning("transform_news skipped: %s", e)


def step7_youtube(engine):
    log.info("STEP 7 — YouTube")
    try:
        from etl.ingest_youtube_videos import run as yt_run
        yt_run()
        log.info("✓ ingest_youtube_videos done")
    except Exception as e:
        log.warning("ingest_youtube_videos skipped: %s", e)


def step8_electoral_roll_segments(engine):
    log.info("STEP 8 — Electoral roll segments (booth demographics)")
    try:
        from etl.aggregate_eroll_segments import run as eroll_run
        eroll_run()
        log.info("✓ aggregate_eroll_segments done")
    except Exception as e:
        log.warning("aggregate_eroll_segments skipped: %s", e)


def step9_booth_metrics(engine):
    log.info("STEP 9 — Booth metrics + data quality")
    try:
        from etl.compute_booth_metrics import run as bm_run
        bm_run()
        log.info("✓ compute_booth_metrics done")
    except Exception as e:
        log.warning("compute_booth_metrics skipped: %s", e)


def main():
    log.info("=" * 60)
    log.info("GORAKHPUR KG — DB Setup & ETL Runner")
    log.info("=" * 60)

    engine = get_engine()
    log.info("PostgreSQL connected: %s", engine.url.render_as_string(hide_password=True))

    log.info("\n[BEFORE]")
    check_row_counts(engine)

    step1_geography(engine)
    step2_candidates(engine)
    step3_booth_results(engine)
    step4_schemes(engine)
    step5_panchayats(engine)
    step6_news(engine)
    step7_youtube(engine)
    step8_electoral_roll_segments(engine)
    step9_booth_metrics(engine)

    log.info("\n[AFTER]")
    check_row_counts(engine)

    log.info("=" * 60)
    log.info("ETL complete — API should now serve booth data")
    log.info("Next: .\\venv\\Scripts\\python.exe -m uvicorn api.main:app --reload")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
