"""Compatibility shim: `analytics.booth_metrics` moved to `analytics.booth.booth_metrics`.

This module re-exports the original public API for compatibility during migration.
"""

from __future__ import annotations

from analytics.booth.booth_metrics import *  # noqa: F401,F403

__all__ = ["compute_booth_metrics", "_lean_label", "_confidence_label"]
