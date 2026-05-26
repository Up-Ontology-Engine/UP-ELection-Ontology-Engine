"""Compatibility shim: moved into analytics.booth.booth_attribution_report."""

from __future__ import annotations

from analytics.booth.booth_attribution_report import *  # noqa: F401,F403

__all__ = [name for name in dir() if not name.startswith("_")]
