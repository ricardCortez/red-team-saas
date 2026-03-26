"""Token-bucket rate limiter — Phase 17"""
import math
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.security import TokenBucket, RateLimitConfig


class RateLimiter:

    def __init__(self, db: Session):
        self.db = db

    def check_rate_limit(
        self,
        user_id: int,
        endpoint: str,
        default_rpm: int = 60,
        burst_capacity: int = 100,
    ) -> tuple:
        """
        Check whether the user has consumed their token budget.

        Returns:
            (allowed: bool, remaining_tokens: int, retry_after_seconds: int)
        """
        # Resolve effective limits (user config overrides defaults)
        config = (
            self.db.query(RateLimitConfig)
            .filter(RateLimitConfig.user_id == user_id)
            .first()
        )
        if config:
            endpoint_limits = config.endpoint_limits or {}
            rpm = endpoint_limits.get(endpoint, config.requests_per_minute)
            burst = config.burst_capacity
        else:
            rpm = default_rpm
            burst = burst_capacity

        refill_rate = rpm / 60.0  # tokens per second

        # Fetch or create bucket
        bucket = (
            self.db.query(TokenBucket)
            .filter(
                TokenBucket.user_id == user_id,
                TokenBucket.endpoint_pattern == endpoint,
            )
            .first()
        )

        now = datetime.now(timezone.utc)

        if not bucket:
            bucket = TokenBucket(
                user_id=user_id,
                endpoint_pattern=endpoint,
                tokens_available=burst - 1,  # consume one immediately
                last_refill_at=now,
            )
            self.db.add(bucket)
            self.db.commit()
            return (True, int(bucket.tokens_available), 0)

        # Refill based on elapsed time
        elapsed = (now - bucket.last_refill_at.replace(tzinfo=timezone.utc)
                   if bucket.last_refill_at.tzinfo is None
                   else (now - bucket.last_refill_at)).total_seconds()

        tokens_to_add = elapsed * refill_rate
        bucket.tokens_available = min(burst, bucket.tokens_available + tokens_to_add)
        bucket.last_refill_at = now

        if bucket.tokens_available >= 1:
            bucket.tokens_available -= 1
            self.db.commit()
            return (True, int(bucket.tokens_available), 0)

        # Not enough tokens — compute retry-after
        tokens_needed = 1 - bucket.tokens_available
        retry_after = math.ceil(tokens_needed / refill_rate)
        self.db.commit()
        return (False, 0, retry_after)

    def get_rate_limit_headers(
        self,
        user_id: int,
        endpoint: str,
        rpm: int = 60,
        burst: int = 100,
    ) -> dict:
        """Return X-RateLimit-* headers for HTTP responses."""
        from datetime import timedelta

        bucket = (
            self.db.query(TokenBucket)
            .filter(
                TokenBucket.user_id == user_id,
                TokenBucket.endpoint_pattern == endpoint,
            )
            .first()
        )

        now = datetime.now(timezone.utc)

        if bucket:
            remaining = max(0, int(bucket.tokens_available))
            last_refill = bucket.last_refill_at
            if last_refill.tzinfo is None:
                last_refill = last_refill.replace(tzinfo=timezone.utc)
            reset_at = int((last_refill + timedelta(minutes=1)).timestamp())
        else:
            remaining = rpm
            reset_at = int((now + timedelta(minutes=1)).timestamp())

        return {
            "RateLimit-Limit": str(rpm),
            "RateLimit-Remaining": str(remaining),
            "RateLimit-Reset": str(reset_at),
        }
