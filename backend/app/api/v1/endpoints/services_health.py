"""Services health check — proxies connectivity checks for internal services.

All checks run from inside the Docker network so browser cert/CORS issues don't matter.
"""
import asyncio
from typing import Dict, Any
import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User

router = APIRouter()

_TIMEOUT = 4.0


async def _ping_http(url: str, verify_ssl: bool = True) -> bool:
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=_TIMEOUT) as client:
            r = await client.get(url)
            return r.status_code < 500
    except Exception:
        return False


def _check_postgres(db: Session) -> bool:
    try:
        db.execute(__import__('sqlalchemy').text("SELECT 1"))
        return True
    except Exception:
        return False


async def _check_redis() -> bool:
    try:
        import redis as redis_sync
        r = redis_sync.Redis(host="redis", port=6379, socket_connect_timeout=3)
        r.ping()
        r.close()
        return True
    except Exception:
        return False


@router.get("/services/health")
async def services_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Check connectivity to all platform services from the backend container."""

    http_checks = {
        "API": _ping_http("http://localhost:8000/"),
        "GoPhish": _ping_http("https://gophish:3333", verify_ssl=False),
        "Grafana": _ping_http("http://grafana:3000"),
        "Prometheus": _ping_http("http://prometheus:9090/-/healthy"),
        "Flower": _ping_http("http://flower:5555"),
        "Redis": _check_redis(),
    }

    results = await asyncio.gather(*http_checks.values(), return_exceptions=True)
    statuses: Dict[str, str] = {}
    for name, result in zip(http_checks.keys(), results):
        statuses[name] = "online" if (not isinstance(result, Exception) and result) else "offline"

    # PostgreSQL: synchronous check via existing SQLAlchemy session
    statuses["PostgreSQL"] = "online" if _check_postgres(db) else "offline"

    return {"services": statuses}
