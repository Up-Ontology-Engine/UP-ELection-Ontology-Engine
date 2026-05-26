"""Canonical ETL loader package."""

from __future__ import annotations

from typing import Any


def run_gorakhpur_baseline(*args: Any, **kwargs: Any):
    from etl.load_gorakhpur_baseline import run as _fn

    return _fn(*args, **kwargs)


def run_real_schemes(*args: Any, **kwargs: Any):
    from etl.load_real_schemes import run as _fn

    return _fn(*args, **kwargs)


__all__ = ["run_gorakhpur_baseline", "run_real_schemes"]
