"""Compatibility shim: moved from analytics/booth_metrics.py into analytics/booth module.
This file re-exports the original public API to keep imports working during migration.
"""
from __future__ import annotations

from analytics.booth_metrics import compute_booth_metrics, _lean_label, _confidence_label

__all__ = ["compute_booth_metrics", "_lean_label", "_confidence_label"]
