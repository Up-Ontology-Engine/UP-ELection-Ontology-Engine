"""Compatibility shim: moved into analytics.signals.narrative_detector."""

from __future__ import annotations

from analytics.signals.narrative_detector import *  # noqa: F401,F403

__all__ = ["detect_narratives_for_booth", "upsert_narrative_rows", "run_all_booths", "update_booth_metrics_narrative"]
