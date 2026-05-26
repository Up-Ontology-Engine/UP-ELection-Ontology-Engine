"""Compatibility shim: moved into analytics.utils.geo_backfill."""

from __future__ import annotations

from analytics.utils.geo_backfill import *  # noqa: F401,F403

__all__ = [name for name in dir() if not name.startswith("_")]
