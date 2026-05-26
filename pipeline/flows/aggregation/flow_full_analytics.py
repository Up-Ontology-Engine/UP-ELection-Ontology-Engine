"""
Prefect flow — Full analytics pipeline.

Runs all 5 analytics stages in dependency order:
  1. booth_metrics          (base pulse + lean scores)
  2. data_quality           (requires pulse_events)
  3. contradiction_detector (requires pulse_events, multi-source)
  4. scheme_gap_analysis    (requires scheme_activity + pulse_events)
  5. narrative_detector     (requires pulse_events + contradiction_flags)
  6. load_quality_narratives (pushes results to Neo4j)

Schedule: every 6 hours via Prefect Cloud, or call run() directly.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from prefect import flow, task, get_run_logger

logger = logging.getLogger(__name__)


# ── Tasks ─────────────────────────────────────────────────────────────────────

@task(name="compute-booth-metrics", retries=2, retry_delay_seconds=30)
def task_booth_metrics() -> int:
    from analytics.booth import run_booth_metrics
    from backend.db import get_pg_engine
    engine = get_pg_engine()
    n = run_booth_metrics(engine)
    get_run_logger().info("booth_metrics: %d booths processed", n)
    return n


@task(name="compute-data-quality", retries=2, retry_delay_seconds=30)
def task_data_quality(window_days: int = 7) -> int:
    from analytics.signals import run_data_quality as run_all_booths
    from backend.db import get_pg_engine
    n = run_all_booths(get_pg_engine(), window_days=window_days)
    get_run_logger().info("data_quality: %d booths scored", n)
    return n


@task(name="detect-contradictions", retries=2, retry_delay_seconds=30)
def task_contradictions(window_days: int = 7) -> int:
    from analytics.signals import run_contradiction_detector as run_all_booths
    from backend.db import get_pg_engine
    n = run_all_booths(get_pg_engine(), window_days=window_days)
    get_run_logger().info("contradiction_detector: %d booths processed", n)
    return n


@task(name="analyze-scheme-gaps", retries=2, retry_delay_seconds=30)
def task_scheme_gaps(window_days: int = 30) -> int:
    from analytics.signals import run_scheme_gap_analysis as run_all_booths
    from backend.db import get_pg_engine
    n = run_all_booths(get_pg_engine(), window_days=window_days)
    get_run_logger().info("scheme_gap_analysis: %d booths analyzed", n)
    return n


@task(name="detect-narratives", retries=2, retry_delay_seconds=30)
def task_narratives(window_days: int = 7) -> int:
    from analytics.signals import run_narrative_detector as run_all_booths
    from backend.db import get_pg_engine
    n = run_all_booths(get_pg_engine(), window_days=window_days)
    get_run_logger().info("narrative_detector: %d booths processed", n)
    return n


@task(name="load-intelligence-to-neo4j", retries=1, retry_delay_seconds=60)
def task_load_neo4j() -> dict:
    from graph.loaders.load_quality_narratives import load_all
    from backend.db import get_pg_engine, get_neo4j_session
    pg = get_pg_engine()
    with get_neo4j_session() as session:
        counts = load_all(pg, session)
    get_run_logger().info("Neo4j intelligence layer: %s", counts)
    return counts


# ── Flow ──────────────────────────────────────────────────────────────────────

@flow(
    name="full-analytics-pipeline",
    description="Runs all 5 analytics stages then syncs results to Neo4j.",
)
def run(window_days_pulse: int = 7, window_days_schemes: int = 30) -> dict:
    log = get_run_logger()
    started_at = datetime.now(timezone.utc)

    log.info("Starting full analytics pipeline at %s", started_at.isoformat())

    # Stage 1 — base metrics (no dependencies)
    n_metrics = task_booth_metrics()

    # Stage 2+3 — independent, can run in parallel after stage 1
    n_quality   = task_data_quality(window_days=window_days_pulse,
                                    wait_for=[n_metrics])
    n_contra    = task_contradictions(window_days=window_days_pulse,
                                      wait_for=[n_metrics])
    n_scheme    = task_scheme_gaps(window_days=window_days_schemes,
                                   wait_for=[n_metrics])

    # Stage 4 — narrative detection reads contradiction_flags, must run after stage 3
    n_narrative = task_narratives(window_days=window_days_pulse,
                                  wait_for=[n_contra])

    # Stage 5 — Neo4j sync, must run after all compute stages
    neo4j_counts = task_load_neo4j(
        wait_for=[n_quality, n_contra, n_scheme, n_narrative]
    )

    elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
    summary = {
        "booth_metrics":         n_metrics,
        "data_quality":          n_quality,
        "contradictions":        n_contra,
        "scheme_gaps":           n_scheme,
        "narratives":            n_narrative,
        "neo4j":                 neo4j_counts,
        "elapsed_seconds":       round(elapsed, 1),
    }
    log.info("Pipeline complete: %s", summary)
    return summary


if __name__ == "__main__":
    result = run()
    print("Pipeline result:", result)
