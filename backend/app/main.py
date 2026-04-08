"""Main FastAPI application"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.executor_types import TOOLS_BY_OPTION
from app.core.openapi import setup_openapi
from app.core.sentry_config import init_sentry
from app.database import init_db
from app.logging_config import logger
from app.middleware.metrics_middleware import MetricsMiddleware
from app.middleware.security_middleware import SecurityMiddleware
from app.api.v1 import auth, tools
from app.api.v1.router import api_router
from app.api.v1.websocket_endpoints import router as ws_router
# Import all models so SQLAlchemy creates their tables
import app.models  # noqa: F401


init_sentry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan"""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.PROJECT_VERSION}")
    init_db()
    logger.info("Database initialized")

    # Start WebSocket Redis broadcaster
    from app.websocket.broadcaster import broadcaster
    from app.websocket.manager import ws_manager
    await broadcaster.start(settings.REDIS_URL, ws_manager.broadcast)
    logger.info("WebSocket broadcaster started")

    yield

    await broadcaster.stop()
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

setup_openapi(app)

app.add_middleware(MetricsMiddleware)
app.add_middleware(SecurityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=settings.ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["auth"])
app.include_router(tools.router, prefix=settings.API_V1_STR, tags=["tools"])
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(ws_router)  # WebSocket endpoints (no prefix, ws:// root)


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint"""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "status": "ok",
        "architecture": settings.ARCHITECTURE_OPTION,
        "total_tools": TOOLS_BY_OPTION[settings.ARCHITECTURE_OPTION].get("total", 0),
        "docs": {
            "swagger_ui": "/api/docs",
            "redoc": "/api/redoc",
            "openapi_json": "/api/openapi.json",
        },
    }


@app.get("/health", tags=["Health"])
async def health():
    """Health check"""
    return {"status": "ok"}


@app.get("/metrics", tags=["Monitoring"], include_in_schema=False)
async def metrics():
    """Prometheus metrics endpoint"""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
