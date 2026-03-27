"""Prometheus metrics middleware for FastAPI"""
from time import time

from prometheus_client import Counter, Gauge, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# HTTP metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

ACTIVE_REQUESTS = Gauge(
    "http_requests_active",
    "Number of active HTTP requests",
)

# Application-level metrics
RATE_LIMIT_EXCEEDED = Counter(
    "rate_limit_exceeded_total",
    "Total rate limit violations",
    ["endpoint"],
)

DB_QUERY_DURATION = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["query_type"],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
)

DB_CONNECTION_POOL_AVAILABLE = Gauge(
    "db_connection_pool_available",
    "Number of available database connections",
)

FINDING_COUNT = Counter(
    "findings_created_total",
    "Total findings created",
    ["severity"],
)

TOOL_EXECUTION_DURATION = Histogram(
    "tool_execution_duration_seconds",
    "Tool execution duration in seconds",
    ["tool_name"],
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0),
)

TOOL_EXECUTION_COUNT = Counter(
    "tool_executions_total",
    "Total tool executions",
    ["tool_name", "status"],
)

REPORT_GENERATION_COUNT = Counter(
    "reports_generated_total",
    "Total reports generated",
    ["format"],
)

AUTH_ATTEMPTS = Counter(
    "auth_attempts_total",
    "Total authentication attempts",
    ["result"],
)

API_KEY_USAGE = Counter(
    "api_key_usage_total",
    "Total API key usage",
    ["key_prefix"],
)

# Endpoints to skip metrics collection (reduce cardinality)
_SKIP_PATHS = {"/metrics", "/health", "/"}


def _normalize_path(path: str) -> str:
    """Normalize path to reduce metric cardinality from UUIDs/IDs."""
    import re

    # Replace UUIDs
    path = re.sub(
        r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        "/{id}",
        path,
    )
    # Replace numeric IDs
    path = re.sub(r"/\d+", "/{id}", path)
    return path


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware that records Prometheus metrics for each HTTP request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        ACTIVE_REQUESTS.inc()
        start_time = time()
        endpoint = _normalize_path(request.url.path)

        try:
            response = await call_next(request)
            status = response.status_code
        except Exception:
            status = 500
            raise
        finally:
            duration = time() - start_time
            ACTIVE_REQUESTS.dec()

            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=endpoint,
                status=str(status),
            ).inc()

            REQUEST_DURATION.labels(
                method=request.method,
                endpoint=endpoint,
            ).observe(duration)

            if status == 429:
                RATE_LIMIT_EXCEEDED.labels(endpoint=endpoint).inc()

        return response
