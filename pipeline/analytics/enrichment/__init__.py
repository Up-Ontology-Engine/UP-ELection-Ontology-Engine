"""Canonical enrichment package for MyNeta-style candidate processing."""

from __future__ import annotations

from typing import Any


def run_myneta_enrichment(*args: Any, **kwargs: Any):
    from analytics.myneta_enrichment import run as _fn

    return _fn(*args, **kwargs)


def run_full_myneta_enrichment(*args: Any, **kwargs: Any):
    from analytics.myneta_complete_enrichment import run as _fn

    return _fn(*args, **kwargs)


def build_myneta_graph(*args: Any, **kwargs: Any):
    from analytics.myneta_graph import run as _fn

    return _fn(*args, **kwargs)


__all__ = [
    "build_myneta_graph",
    "run_full_myneta_enrichment",
    "run_myneta_enrichment",
]
