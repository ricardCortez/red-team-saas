"""Redis cache decorator for analytics queries."""
import json
import hashlib
import functools
from typing import Callable
from app.core.redis_client import redis_client
import logging

logger = logging.getLogger(__name__)


def cache_result(ttl: int = 300, prefix: str = "analytics"):
    """
    Decorator: caches the return value of a function in Redis.
    Key = prefix:sha256(func_name + args + kwargs)[:16]
    DB sessions (objects with .query) are excluded from the cache key.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            safe_args = [a for a in args if not hasattr(a, "query")]
            raw_key = (
                f"{func.__name__}:"
                f"{json.dumps(safe_args, default=str)}:"
                f"{json.dumps(kwargs, default=str)}"
            )
            key = f"{prefix}:{hashlib.sha256(raw_key.encode()).hexdigest()[:16]}"

            try:
                cached = redis_client.get(key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Cache read failed: {e}")

            result = func(*args, **kwargs)

            try:
                redis_client.setex(key, ttl, json.dumps(result, default=str))
            except Exception as e:
                logger.warning(f"Cache write failed: {e}")

            return result
        return wrapper
    return decorator


def invalidate_cache(prefix: str = "analytics"):
    """Delete all Redis keys matching the given prefix."""
    try:
        keys = redis_client.keys(f"{prefix}:*")
        if keys:
            redis_client.delete(*keys)
    except Exception as e:
        logger.warning(f"Cache invalidation failed: {e}")
