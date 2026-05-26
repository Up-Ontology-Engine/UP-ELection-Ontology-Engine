"""Canonical booth analytics package."""

from __future__ import annotations

from typing import Any


def compute_booth_metrics(*args: Any, **kwargs: Any):
    from analytics.booth_metrics import compute_booth_metrics as _fn

    return _fn(*args, **kwargs)


def run_booth_metrics(*args: Any, **kwargs: Any):
    return compute_booth_metrics(*args, **kwargs)


def get_vote_share_trend(*args: Any, **kwargs: Any):
    from analytics.historical_analysis import get_vote_share_trend as _fn

    return _fn(*args, **kwargs)


def get_bjp_trend_summary(*args: Any, **kwargs: Any):
    from analytics.historical_analysis import get_bjp_trend_summary as _fn

    return _fn(*args, **kwargs)


def run_ac_level_analytics(*args: Any, **kwargs: Any):
    from analytics.ac_level_analytics import run as _fn

    return _fn(*args, **kwargs)


def run_booth_attribution_report(*args: Any, **kwargs: Any):
    from analytics.booth_attribution_report import run as _fn

    return _fn(*args, **kwargs)


__all__ = [
    "compute_booth_metrics",
    "get_bjp_trend_summary",
    "get_vote_share_trend",
    "run_ac_level_analytics",
    "run_booth_attribution_report",
    "run_booth_metrics",
]
