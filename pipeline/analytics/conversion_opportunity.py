"""Compatibility shim: moved into analytics.booth.conversion_opportunity."""

from __future__ import annotations

from analytics.booth.conversion_opportunity import *  # noqa: F401,F403

__all__ = [name for name in dir() if not name.startswith("_")]
