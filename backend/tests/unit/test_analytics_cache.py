"""Unit tests for the analytics cache decorator and invalidation helper."""
import json
import pytest
from unittest.mock import MagicMock, patch


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_redis_mock(cached_value=None):
    """Return a MagicMock Redis client."""
    mock = MagicMock()
    mock.get.return_value = json.dumps(cached_value) if cached_value is not None else None
    mock.keys.return_value = []
    return mock


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_cache_decorator_stores_result():
    """On cache miss the result is written to Redis with the correct TTL."""
    mock_redis = _make_redis_mock(cached_value=None)

    with patch("app.core.analytics.cache.redis_client", mock_redis):
        from app.core.analytics.cache import cache_result

        @cache_result(ttl=60, prefix="test")
        def compute():
            return {"value": 42}

        result = compute()

    assert result == {"value": 42}
    assert mock_redis.setex.called
    call_args = mock_redis.setex.call_args
    ttl_arg = call_args[0][1]
    assert ttl_arg == 60


def test_cache_decorator_returns_cached():
    """On cache hit the function body is NOT called and cached data is returned."""
    cached_data = {"value": 99}
    mock_redis = _make_redis_mock(cached_value=cached_data)

    call_count = 0

    with patch("app.core.analytics.cache.redis_client", mock_redis):
        from app.core.analytics.cache import cache_result

        @cache_result(ttl=300, prefix="test")
        def expensive():
            nonlocal call_count
            call_count += 1
            return {"value": 0}

        result = expensive()

    assert result == cached_data
    assert call_count == 0  # function body never executed


def test_cache_invalidate_clears_keys():
    """invalidate_cache deletes all keys matching the prefix."""
    mock_redis = MagicMock()
    mock_redis.keys.return_value = ["analytics:aaa", "analytics:bbb"]

    with patch("app.core.analytics.cache.redis_client", mock_redis):
        from app.core.analytics.cache import invalidate_cache
        invalidate_cache("analytics")

    mock_redis.keys.assert_called_once_with("analytics:*")
    mock_redis.delete.assert_called_once_with("analytics:aaa", "analytics:bbb")


def test_cache_failure_does_not_break_function():
    """Redis errors are swallowed; the decorated function still returns its value."""
    mock_redis = MagicMock()
    mock_redis.get.side_effect = ConnectionError("Redis down")
    mock_redis.setex.side_effect = ConnectionError("Redis down")

    with patch("app.core.analytics.cache.redis_client", mock_redis):
        from app.core.analytics.cache import cache_result

        @cache_result(ttl=300, prefix="test")
        def safe_fn():
            return {"ok": True}

        result = safe_fn()

    assert result == {"ok": True}
