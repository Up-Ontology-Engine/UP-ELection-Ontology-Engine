"""Redis-backed cache helpers for FastAPI route results.

Usage:
    from .cache import cached, cache_get, cache_set, cache_delete

    @cached("key:{ac_id}", ttl=60)
    def my_func(ac_id: str) -> dict: ...

Falls back silently to no-cache if Redis is unavailable.
"""
from __future__ import annotations

import functools
import json
import logging
from typing import Any, Callable, TypeVar

_log = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

_MISS = object()  # sentinel


def _get_redis():
    """Lazy import to avoid circular deps."""
    from .db import get_redis_client
    return get_redis_client()


def cache_get(key: str) -> Any:
    """Return cached value or _MISS sentinel if not found / Redis unavailable."""
    try:
        r = _get_redis()
        if r is None:
            return _MISS
        raw = r.get(key)
        if raw is None:
            return _MISS
        return json.loads(raw)
    except Exception as exc:
        _log.debug("cache_get miss (error): key=%s err=%s", key, exc)
        return _MISS


def cache_set(key: str, value: Any, ttl: int = 60) -> None:
    """Store value as JSON in Redis with given TTL (seconds). Fails silently."""
    try:
        r = _get_redis()
        if r is None:
            return
        r.setex(key, ttl, json.dumps(value, default=str))
    except Exception as exc:
        _log.debug("cache_set failed: key=%s err=%s", key, exc)


def cache_delete(key: str) -> None:
    """Invalidate a cache key. Fails silently."""
    try:
        r = _get_redis()
        if r:
            r.delete(key)
    except Exception:
        pass


def clear_api_cache() -> None:
    """Invalidate all Redis-cached API responses (cache:* prefix)."""
    try:
        r = _get_redis()
        if r:
            keys = r.keys("cache:*")
            if keys:
                r.delete(*keys)
                _log.info("Cache invalidated", extra={"keys_cleared": len(keys)})
    except Exception as exc:
        _log.warning("Cache invalidation failed: %s", exc)


def cached(key_template: str, ttl: int = 60) -> Callable[[F], F]:
    """Decorator: cache function result in Redis with given TTL.

    key_template uses Python str.format() with the function's arguments.
    Example:
        @cached("cache:intel:{ac_id}", ttl=60)
        def get_ac_intel_summary(ac_id: str) -> dict: ...
    """
    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            # Map positional args to parameter names
            varnames = fn.__code__.co_varnames[: fn.__code__.co_argcount]
            all_kwargs = {**kwargs}
            for i, val in enumerate(args):
                if i < len(varnames):
                    all_kwargs.setdefault(varnames[i], val)

            try:
                cache_key = key_template.format(**all_kwargs)
            except (KeyError, IndexError):
                cache_key = key_template

            hit = cache_get(cache_key)
            if hit is not _MISS:
                _log.debug("cache HIT: %s", cache_key)
                return hit

            result = fn(*args, **kwargs)
            cache_set(cache_key, result, ttl=ttl)
            return result

        return wrapper  # type: ignore[return-value]

    return decorator
