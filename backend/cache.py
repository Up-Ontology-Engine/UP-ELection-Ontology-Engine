from __future__ import annotations
import logging

_log = logging.getLogger(__name__)

def clear_api_cache() -> None:
    """Invalidate all Redis-cached API responses."""
    try:
        from .db import get_redis_client
        redis_client = get_redis_client()
        if redis_client:
            keys = redis_client.keys("cache:*")
            if keys:
                redis_client.delete(*keys)
                _log.info("Cache invalidated", extra={"keys_cleared": len(keys)})
    except Exception as exc:
        _log.warning("Cache invalidation failed: %s", exc)
