"""Compatibility shim: moved into analytics.booth.ac_level_analytics."""

from __future__ import annotations

from analytics.booth.ac_level_analytics import *  # noqa: F401,F403

__all__ = [name for name in dir() if not name.startswith("_")]
