"""Unit tests for alert rate limiter - Phase 8"""
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_redis():
    return MagicMock()


def test_first_call_not_limited(mock_redis):
    """First call for a rule should NOT be rate limited, key should be set."""
    mock_redis.exists.return_value = 0  # key doesn't exist

    with patch("app.core.notifications.rate_limiter.redis_client", mock_redis):
        from app.core.notifications.rate_limiter import is_rate_limited
        result = is_rate_limited(rule_id=1, rate_limit_minutes=60)

    assert result is False
    mock_redis.setex.assert_called_once_with("alert_rate:1", 3600, "1")


def test_second_call_is_limited(mock_redis):
    """Second call within cooldown window should be rate limited."""
    mock_redis.exists.return_value = 1  # key exists (within cooldown)

    with patch("app.core.notifications.rate_limiter.redis_client", mock_redis):
        from app.core.notifications.rate_limiter import is_rate_limited
        result = is_rate_limited(rule_id=2, rate_limit_minutes=60)

    assert result is True
    mock_redis.setex.assert_not_called()


def test_rate_limit_zero_always_passes(mock_redis):
    """rate_limit_minutes=0 means no limiting, never blocked."""
    with patch("app.core.notifications.rate_limiter.redis_client", mock_redis):
        from app.core.notifications.rate_limiter import is_rate_limited
        result = is_rate_limited(rule_id=3, rate_limit_minutes=0)

    assert result is False
    mock_redis.exists.assert_not_called()
    mock_redis.setex.assert_not_called()


def test_reset_clears_limit(mock_redis):
    """reset_rate_limit should delete the rate limit key."""
    with patch("app.core.notifications.rate_limiter.redis_client", mock_redis):
        from app.core.notifications.rate_limiter import reset_rate_limit
        reset_rate_limit(rule_id=4)

    mock_redis.delete.assert_called_once_with("alert_rate:4")


def test_rate_limit_minutes_used_as_ttl(mock_redis):
    """The TTL set in Redis should be rate_limit_minutes * 60."""
    mock_redis.exists.return_value = 0

    with patch("app.core.notifications.rate_limiter.redis_client", mock_redis):
        from app.core.notifications.rate_limiter import is_rate_limited
        is_rate_limited(rule_id=5, rate_limit_minutes=30)

    mock_redis.setex.assert_called_once_with("alert_rate:5", 1800, "1")


def test_redis_error_fails_open(mock_redis):
    """If Redis raises an exception, rate limiter should fail open (return False)."""
    mock_redis.exists.side_effect = ConnectionError("Redis down")

    with patch("app.core.notifications.rate_limiter.redis_client", mock_redis):
        from app.core.notifications.rate_limiter import is_rate_limited
        result = is_rate_limited(rule_id=6, rate_limit_minutes=60)

    assert result is False  # fail open


def test_reset_redis_error_silently_ignored(mock_redis):
    """reset_rate_limit should not raise even if Redis fails."""
    mock_redis.delete.side_effect = ConnectionError("Redis down")

    with patch("app.core.notifications.rate_limiter.redis_client", mock_redis):
        from app.core.notifications.rate_limiter import reset_rate_limit
        reset_rate_limit(rule_id=7)  # should not raise
