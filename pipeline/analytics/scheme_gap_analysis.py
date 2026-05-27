# ruff: noqa: F401, F403, F405
"""Compatibility shim: moved into analytics.signals.scheme_gap_analysis."""

from __future__ import annotations

from pipeline.analytics.signals.scheme_gap_analysis import *  # noqa: F401,F403

__all__ = ["get_scheme_gaps_for_booth", "upsert_gap_rows"]
