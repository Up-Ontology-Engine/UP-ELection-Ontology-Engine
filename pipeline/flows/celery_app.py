"""
Celery Beat scheduler — automated ETL and analytics tasks.
"""

from __future__ import annotations

import logging
import os

from celery import Celery
from celery.schedules import crontab

logger = logging.getLogger(__name__)

_BROKER = os.environ.get("REDIS_URL", "redis://redis:6379/0")
app = Celery("gorakhpur_kg", broker=_BROKER, backend=_BROKER, include=["pipeline.flows.celery_app"])

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_concurrency=int(os.environ.get("CELERY_CONCURRENCY", 4)),
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    beat_schedule={
        "scrape-news-2h": {
            "task": "pipeline.flows.celery_app.task_scrape_news",
            "schedule": crontab(minute=0, hour="*/2"),
        },
        "analytics-6h": {
            "task": "pipeline.flows.celery_app.task_recompute_analytics",
            "schedule": crontab(minute=30, hour="*/6"),
        },
        "gds-influence-daily": {
            "task": "pipeline.flows.celery_app.task_gds_influence",
            "schedule": crontab(minute=0, hour=2),
        },
        "schema-drift-daily": {
            "task": "pipeline.flows.celery_app.task_schema_drift",
            "schedule": crontab(minute=0, hour=3),
        },
        "contradiction-weekly": {
            "task": "pipeline.flows.celery_app.task_contradiction_recompute",
            "schedule": crontab(minute=0, hour=1, day_of_week="sunday"),
        },
    },
)


@app.task(
    name="pipeline.flows.celery_app.task_scrape_news",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    queue="scraper",
)
def task_scrape_news(self):
    try:
        from pipeline.ingest.multi_news_scraper import run as scraper_run

        scraper_run(incremental=True)
        return {"status": "ok"}
    except Exception as exc:
        raise self.retry(exc=exc)


@app.task(
    name="pipeline.flows.celery_app.task_recompute_analytics",
    bind=True,
    max_retries=2,
    queue="analytics",
    soft_time_limit=18000,
)
def task_recompute_analytics(self):
    try:
        from dotenv import load_dotenv

        load_dotenv()
        from pipeline.analytics.booth_metrics import run_all

        run_all()
        from pipeline.analytics.narrative_detector import run_all

        run_all()
        from pipeline.analytics.scheme_gap_analysis import run_all

        run_all()
        return {"status": "ok"}
    except Exception as exc:
        raise self.retry(exc=exc)


@app.task(
    name="pipeline.flows.celery_app.task_gds_influence",
    bind=True,
    max_retries=1,
    queue="analytics",
    soft_time_limit=7200,
)
def task_gds_influence(self):
    try:
        from dotenv import load_dotenv

        load_dotenv()
        from pipeline.graph.analytics.gds_booth_influence import run_influence_pipeline

        return run_influence_pipeline()
    except Exception as exc:
        raise self.retry(exc=exc)


@app.task(
    name="pipeline.flows.celery_app.task_schema_drift", bind=True, max_retries=2, queue="default"
)
def task_schema_drift(self):
    try:
        from pipeline.ingest.schema_drift_detector import run_drift_check

        report = run_drift_check(ac_no=322, election_year=2022)
        if report.get("drift_detected"):
            logger.critical("[celery] SCHEMA DRIFT DETECTED: %s", report)
        return report
    except Exception as exc:
        raise self.retry(exc=exc)


@app.task(
    name="pipeline.flows.celery_app.task_contradiction_recompute",
    bind=True,
    max_retries=1,
    queue="analytics",
    soft_time_limit=3600,
)
def task_contradiction_recompute(self):
    try:
        from dotenv import load_dotenv

        load_dotenv()
        from pipeline.analytics.contradiction_detector import run_all

        run_all()
        return {"status": "ok"}
    except Exception as exc:
        raise self.retry(exc=exc)
