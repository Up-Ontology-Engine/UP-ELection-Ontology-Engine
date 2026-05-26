"""Compatibility shim: moved into analytics.signals.data_quality."""

from __future__ import annotations

from analytics.signals.data_quality import *  # noqa: F401,F403

__all__ = ["compute_quality_for_booth", "upsert_quality_row", "run_all_booths"]
