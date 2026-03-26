"""Rate limiter for alert rules using Redis - Phase 8"""
import logging
from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)


def is_rate_limited(rule_id: int, rate_limit_minutes: int) -> bool:
    """
    Returns True if the rule is in cooldown (rate limited).
    Key: alert_rate:{rule_id} — expires in rate_limit_minutes * 60 seconds.
    Fail open: if Redis is unavailable, returns False (allow sending).
    """
    if rate_limit_minutes <= 0:
        return False

    key = f"alert_rate:{rule_id}"
    try:
        if redis_client.exists(key):
            return True
        redis_client.setex(key, rate_limit_minutes * 60, "1")
        return False
    except Exception as e:
        logger.warning(f"Rate limiter Redis error (fail open): {e}")
        return False  # fail open


def reset_rate_limit(rule_id: int) -> None:
    """Remove rate limit key for a rule (for testing/manual reset)."""
    try:
        redis_client.delete(f"alert_rate:{rule_id}")
    except Exception:
        pass
