"""Compatibility shim: moved into analytics.signals.contradiction_detector."""

from __future__ import annotations

from analytics.signals.contradiction_detector import *  # noqa: F401,F403

__all__ = [
    "detect_contradictions_for_booth",
    "upsert_contradiction_rows",
    "update_booth_metrics_consistency",
    "run_all_booths",
]
