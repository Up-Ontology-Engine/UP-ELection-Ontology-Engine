# ruff: noqa: E402, F401, F404, F405, F841, F811
"""Compatibility shim: moved into analytics.signals.contradiction_detector."""

from __future__ import annotations

from analytics.signals.contradiction_detector import *  # noqa: F401,F403

__all__ = [
    "detect_contradictions_for_booth",
    "upsert_contradiction_rows",
    "update_booth_metrics_consistency",
    "run_all_booths",
]
