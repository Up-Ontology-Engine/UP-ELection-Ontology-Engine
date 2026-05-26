"""Canonical ETL ingestion package."""

from __future__ import annotations

from typing import Any


def ingest_eroll_data(*args: Any, **kwargs: Any):
    from etl.ingest_eroll_data import ingest as _fn

    return _fn(*args, **kwargs)


def run_ingest_political_data(*args: Any, **kwargs: Any):
    from etl.ingest_political_data import run as _fn

    return _fn(*args, **kwargs)


def run_ingest_tcpd_voteshare(*args: Any, **kwargs: Any):
    from etl.ingest_tcpd_voteshare import run as _fn

    return _fn(*args, **kwargs)


def run_ingest_youtube_videos(*args: Any, **kwargs: Any):
    from etl.ingest_youtube_videos import run as _fn

    return _fn(*args, **kwargs)


def parse_form20_xls(*args: Any, **kwargs: Any):
    from etl.parse_form20_xls import parse_form20_xls as _fn

    return _fn(*args, **kwargs)


def parse_myneta_affidavit(*args: Any, **kwargs: Any):
    from etl.parse_myneta_affidavits import parse_file as _fn

    return _fn(*args, **kwargs)


def run_process_youtube_signals(*args: Any, **kwargs: Any):
    from etl.process_youtube_signals import run as _fn

    return _fn(*args, **kwargs)


def run_pulse_event_prep(*args: Any, **kwargs: Any):
    from etl.pulse_event_prep import run as _fn

    return _fn(*args, **kwargs)


def run_stage_news_to_pulse(*args: Any, **kwargs: Any):
    from etl.stage_news_to_pulse import run as _fn

    return _fn(*args, **kwargs)


def run_stage_youtube_to_pulse(*args: Any, **kwargs: Any):
    from etl.stage_youtube_to_pulse import run as _fn

    return _fn(*args, **kwargs)


__all__ = [
    "ingest_eroll_data",
    "parse_form20_xls",
    "parse_myneta_affidavit",
    "run_ingest_political_data",
    "run_ingest_tcpd_voteshare",
    "run_ingest_youtube_videos",
    "run_process_youtube_signals",
    "run_pulse_event_prep",
    "run_stage_news_to_pulse",
    "run_stage_youtube_to_pulse",
]
