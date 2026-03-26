"""Real-time Metrics Service — Phase 15

Wraps the existing redis_client for project-scoped metric counters
with TTL management. Uses Redis incr/expire for O(1) updates.
"""
import logging
from typing import Dict, List, Optional

from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)

_DEFAULT_TTL = 86400   # 24 h


class RealtimeMetricsService:
    """Project-scoped metric counters backed by Redis."""

    def __init__(self):
        self.redis = redis_client

    # ── Write ────────────────────────────────────────────────────────────────

    def increment_metric(
        self,
        project_id: str,
        metric_type: str,
        value: int = 1,
        ttl_seconds: int = _DEFAULT_TTL,
    ) -> None:
        """Atomically increment a project metric counter."""
        key = self._key(project_id, metric_type)
        try:
            self.redis.incrby(key, value)
            self.redis.expire(key, ttl_seconds)
        except Exception as exc:
            logger.warning("RealtimeMetrics.increment failed [%s]: %s", key, exc)

    def increment_tool_metric(
        self,
        project_id: str,
        tool_name: str,
        metric_type: str,
        value: int = 1,
        ttl_seconds: int = _DEFAULT_TTL,
    ) -> None:
        """Atomically increment a tool-specific counter."""
        key = self._tool_key(project_id, tool_name, metric_type)
        try:
            self.redis.incrby(key, value)
            self.redis.expire(key, ttl_seconds)
        except Exception as exc:
            logger.warning("RealtimeMetrics.increment_tool failed [%s]: %s", key, exc)

    def set_gauge(
        self,
        project_id: str,
        metric_type: str,
        value: float,
        ttl_seconds: int = _DEFAULT_TTL,
    ) -> None:
        """Set an absolute gauge value (e.g. current risk score)."""
        key = self._key(project_id, f"gauge:{metric_type}")
        try:
            self.redis.set(key, str(value), ex=ttl_seconds)
        except Exception as exc:
            logger.warning("RealtimeMetrics.set_gauge failed [%s]: %s", key, exc)

    # ── Read ─────────────────────────────────────────────────────────────────

    def get_metric(self, project_id: str, metric_type: str) -> int:
        """Return current integer value of a project metric (0 if absent)."""
        try:
            val = self.redis.get(self._key(project_id, metric_type))
            return int(val) if val else 0
        except Exception as exc:
            logger.warning("RealtimeMetrics.get_metric failed: %s", exc)
            return 0

    def get_gauge(self, project_id: str, metric_type: str) -> float:
        """Return current float gauge value (0.0 if absent)."""
        try:
            val = self.redis.get(self._key(project_id, f"gauge:{metric_type}"))
            return float(val) if val else 0.0
        except Exception as exc:
            logger.warning("RealtimeMetrics.get_gauge failed: %s", exc)
            return 0.0

    def get_current_metrics(self, project_id: str) -> Dict[str, int]:
        """Return all current counters for a project as {metric_type: count}."""
        pattern = f"metrics:{project_id}:*"
        metrics: Dict[str, int] = {}
        try:
            keys = self.redis.keys(pattern)
            if not keys:
                return metrics
            values = self.redis.mget(*keys)
            for key, val in zip(keys, values):
                short = key.replace(f"metrics:{project_id}:", "")
                metrics[short] = int(val) if val else 0
        except Exception as exc:
            logger.warning("RealtimeMetrics.get_current_metrics failed: %s", exc)
        return metrics

    def get_tool_metrics(self, project_id: str, tool_name: str) -> Dict[str, int]:
        """Return all counters for a specific tool."""
        pattern = self._tool_key(project_id, tool_name, "*")
        metrics: Dict[str, int] = {}
        try:
            keys = self.redis.keys(pattern)
            if not keys:
                return metrics
            values = self.redis.mget(*keys)
            prefix = self._tool_key(project_id, tool_name, "")
            for key, val in zip(keys, values):
                short = key.replace(prefix, "")
                metrics[short] = int(val) if val else 0
        except Exception as exc:
            logger.warning("RealtimeMetrics.get_tool_metrics failed: %s", exc)
        return metrics

    # ── Management ───────────────────────────────────────────────────────────

    def reset_project_metrics(self, project_id: str) -> int:
        """Delete all metric keys for a project. Returns count deleted."""
        pattern = f"metrics:{project_id}:*"
        try:
            keys = self.redis.keys(pattern)
            if keys:
                self.redis.delete(*keys)
            return len(keys) if keys else 0
        except Exception as exc:
            logger.warning("RealtimeMetrics.reset failed: %s", exc)
            return 0

    def health_check(self) -> bool:
        """Verify Redis connectivity."""
        try:
            return self.redis.ping()
        except Exception:
            return False

    # ── Private ──────────────────────────────────────────────────────────────

    @staticmethod
    def _key(project_id: str, metric_type: str) -> str:
        return f"metrics:{project_id}:{metric_type}"

    @staticmethod
    def _tool_key(project_id: str, tool_name: str, metric_type: str) -> str:
        return f"metrics:{project_id}:tool:{tool_name}:{metric_type}"
