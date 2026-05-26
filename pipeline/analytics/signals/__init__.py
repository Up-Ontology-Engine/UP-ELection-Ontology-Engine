"""Canonical signal analytics package."""

from __future__ import annotations

from typing import Any


def compute_quality_for_booth(*args: Any, **kwargs: Any):
    from analytics.data_quality import compute_quality_for_booth as _fn

    return _fn(*args, **kwargs)


def run_data_quality(*args: Any, **kwargs: Any):
    from analytics.data_quality import run_all_booths as _fn

    return _fn(*args, **kwargs)


def detect_contradictions_for_booth(*args: Any, **kwargs: Any):
    from analytics.contradiction_detector import detect_contradictions_for_booth as _fn

    return _fn(*args, **kwargs)


def run_contradiction_detector(*args: Any, **kwargs: Any):
    from analytics.contradiction_detector import run_all_booths as _fn

    return _fn(*args, **kwargs)


def run_conversion_opportunity(*args: Any, **kwargs: Any):
    from analytics.conversion_opportunity import run_all_booths as _fn

    return _fn(*args, **kwargs)


def detect_narratives_for_booth(*args: Any, **kwargs: Any):
    from analytics.narrative_detector import detect_narratives_for_booth as _fn

    return _fn(*args, **kwargs)


def run_narrative_detector(*args: Any, **kwargs: Any):
    from analytics.narrative_detector import run_all_booths as _fn

    return _fn(*args, **kwargs)


def get_scheme_gaps_for_booth(*args: Any, **kwargs: Any):
    from analytics.scheme_gap_analysis import get_scheme_gaps_for_booth as _fn

    return _fn(*args, **kwargs)


def run_scheme_gap_analysis(*args: Any, **kwargs: Any):
    from analytics.scheme_gap_analysis import run_all_booths as _fn

    return _fn(*args, **kwargs)


__all__ = [
    "compute_quality_for_booth",
    "detect_contradictions_for_booth",
    "detect_narratives_for_booth",
    "get_scheme_gaps_for_booth",
    "run_contradiction_detector",
    "run_conversion_opportunity",
    "run_data_quality",
    "run_narrative_detector",
    "run_scheme_gap_analysis",
]
