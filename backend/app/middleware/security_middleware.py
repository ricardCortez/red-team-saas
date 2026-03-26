"""Security middleware: rate limiting, IP validation, API key auth, audit logging.

Phase 17 — applied per-request via FastAPI/Starlette middleware.
"""
import time

from fastapi import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.services.rate_limiter import RateLimiter
from app.services.ip_validator import IPValidator
from app.services.api_key_service import APIKeyService
from app.crud.security import SecurityCRUD
from app.database import SessionLocal

# Paths that bypass all security checks (health, docs, auth)
_OPEN_PATHS = {
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/security/oauth",
}


def _is_open_path(path: str) -> bool:
    if path in _OPEN_PATHS:
        return True
    for open_path in _OPEN_PATHS:
        if path.startswith(open_path):
            return True
    return False


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Per-request security layer:

    1. Skip open paths (auth, docs, health).
    2. Extract identity from API key or JWT (already set on request.state by
       the auth dependency).
    3. Validate IP against user's whitelist / blacklist.
    4. Enforce token-bucket rate limits.
    5. Append RateLimit-* response headers.
    6. Write a SecurityAuditLog entry for every handled request.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if _is_open_path(request.url.path):
            return await call_next(request)

        db = SessionLocal()
        try:
            client_ip = (request.client.host if request.client else "unknown")
            user_agent = request.headers.get("user-agent", "")

            # --- Resolve user identity ------------------------------------------
            auth_header = request.headers.get("authorization", "")
            api_key_raw: str = None
            api_key_info: dict = None

            if auth_header.startswith("Bearer rtsa_"):
                api_key_raw = auth_header[len("Bearer "):]
                api_key_info = APIKeyService.validate_api_key(api_key_raw, db)

            user_id: int = None
            if api_key_info and api_key_info.get("valid"):
                user_id = api_key_info["user_id"]
                request.state.user_id = user_id
                request.state.scopes = api_key_info.get("scopes", [])
            else:
                user_id = getattr(request.state, "user_id", None)

            # No identity → let the endpoint handle auth (e.g. 401)
            if user_id is None:
                return await call_next(request)

            endpoint = request.url.path

            # --- IP validation ---------------------------------------------------
            ip_allowed, ip_reason = IPValidator.is_ip_allowed(user_id, client_ip, db)
            if not ip_allowed:
                SecurityCRUD.log_security_event(
                    db,
                    user_id=user_id,
                    method=request.method,
                    endpoint=endpoint,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    ip_blocked=True,
                    error_message=ip_reason,
                )
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": f"Access denied: {ip_reason}"},
                )

            # --- Rate limiting ---------------------------------------------------
            allowed, remaining, retry_after = RateLimiter(db).check_rate_limit(
                user_id, endpoint
            )
            if not allowed:
                SecurityCRUD.log_security_event(
                    db,
                    user_id=user_id,
                    method=request.method,
                    endpoint=endpoint,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    rate_limit_exceeded=True,
                    error_message=f"Rate limit exceeded, retry after {retry_after}s",
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Rate limit exceeded"},
                    headers={"Retry-After": str(retry_after)},
                )

            # --- Execute request -------------------------------------------------
            start = time.perf_counter()
            response = await call_next(request)
            response_time_ms = int((time.perf_counter() - start) * 1000)

            # --- Audit log -------------------------------------------------------
            SecurityCRUD.log_security_event(
                db,
                user_id=user_id,
                method=request.method,
                endpoint=endpoint,
                status_code=response.status_code,
                ip_address=client_ip,
                user_agent=user_agent,
                api_key_prefix=api_key_raw[:20] if api_key_raw else None,
                response_time_ms=response_time_ms,
            )

            # --- Rate limit headers ----------------------------------------------
            rl_headers = RateLimiter(db).get_rate_limit_headers(user_id, endpoint)
            for header, value in rl_headers.items():
                response.headers[header] = value

            return response

        except Exception as exc:  # pragma: no cover — unexpected errors
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error"},
            )
        finally:
            db.close()
