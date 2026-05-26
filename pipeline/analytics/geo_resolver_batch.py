"""Compatibility shim: moved into analytics.utils.geo_resolver_batch."""

from __future__ import annotations

from analytics.utils.geo_resolver_batch import *  # noqa: F401,F403

__all__ = [name for name in dir() if not name.startswith("_")]
