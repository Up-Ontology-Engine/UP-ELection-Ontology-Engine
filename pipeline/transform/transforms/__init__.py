"""Canonical ETL transform package."""

from __future__ import annotations

from typing import Any


def compute_metrics(*args: Any, **kwargs: Any):
    from etl.compute_booth_metrics import compute_metrics as _fn

    return _fn(*args, **kwargs)


def enrich_profiles_voteshare(*args: Any, **kwargs: Any):
    from etl.enrich_profiles_voteshare import main as _fn

    return _fn(*args, **kwargs)


def expand_aliases(*args: Any, **kwargs: Any):
    from etl.expand_aliases import expand_aliases as _fn

    return _fn(*args, **kwargs)


def geocode_booths(*args: Any, **kwargs: Any):
    from etl.geocode_booths import geocode_booths as _fn

    return _fn(*args, **kwargs)


def run_aggregate_eroll_segments(*args: Any, **kwargs: Any):
    from etl.aggregate_eroll_segments import run as _fn

    return _fn(*args, **kwargs)


def run_aggregate_form20_results(*args: Any, **kwargs: Any):
    from etl.aggregate_form20_results import run as _fn

    return _fn(*args, **kwargs)


def run_compute_booth_election_metrics(*args: Any, **kwargs: Any):
    from etl.compute_booth_election_metrics import _run as _fn

    return _fn(*args, **kwargs)


def run_fix_booth_names_and_results(*args: Any, **kwargs: Any):
    from etl.fix_booth_names_and_results import run as _fn

    return _fn(*args, **kwargs)


def run_transform_candidates(*args: Any, **kwargs: Any):
    from etl.transform_candidates import run as _fn

    return _fn(*args, **kwargs)


def run_transform_census(*args: Any, **kwargs: Any):
    from etl.transform_census import run as _fn

    return _fn(*args, **kwargs)


def run_transform_geography(*args: Any, **kwargs: Any):
    from etl.transform_geography import run as _fn

    return _fn(*args, **kwargs)


def run_transform_news(*args: Any, **kwargs: Any):
    from etl.transform_news import run as _fn

    return _fn(*args, **kwargs)


def run_transform_panchayats(*args: Any, **kwargs: Any):
    from etl.transform_panchayats import run as _fn

    return _fn(*args, **kwargs)


def run_transform_schemes(*args: Any, **kwargs: Any):
    from etl.transform_schemes import run as _fn

    return _fn(*args, **kwargs)


__all__ = [
    "compute_metrics",
    "enrich_profiles_voteshare",
    "expand_aliases",
    "geocode_booths",
    "run_aggregate_eroll_segments",
    "run_aggregate_form20_results",
    "run_compute_booth_election_metrics",
    "run_fix_booth_names_and_results",
    "run_transform_candidates",
    "run_transform_census",
    "run_transform_geography",
    "run_transform_news",
    "run_transform_panchayats",
    "run_transform_schemes",
]
