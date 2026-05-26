"""Canonical ETL seeder package."""

from __future__ import annotations

from typing import Any


def run_seed_known_candidates(*args: Any, **kwargs: Any):
    from etl.seed_known_candidates import run as _fn

    return _fn(*args, **kwargs)


def seed_ls2024_results(*args: Any, **kwargs: Any):
    from etl.seed_ls2024_results import seed as _fn

    return _fn(*args, **kwargs)


__all__ = ["run_seed_known_candidates", "seed_ls2024_results"]
