"""Custom OpenAPI schema configuration — Phase 18"""
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def custom_openapi(app: FastAPI) -> Dict[str, Any]:
    """Generate a customised OpenAPI 3.0 schema for Red Team SaaS."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Red Team SaaS API",
        version="1.0.0",
        description=(
            "Red Team SaaS — automated penetration-testing platform.\n\n"
            "This API provides endpoints for managing projects, executing "
            "security tools, tracking findings, generating compliance reports, "
            "and integrating with third-party services."
        ),
        routes=app.routes,
    )

    # ── Security schemes ────────────────────────────────────────────────
    openapi_schema.setdefault("components", {})
    openapi_schema["components"]["securitySchemes"] = {
        "BearerToken": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT access token obtained via POST /api/v1/auth/login",
        },
        "APIKey": {
            "type": "http",
            "scheme": "bearer",
            "description": (
                "API key (prefixed rtsa_) created via POST /api/v1/security/api-keys"
            ),
        },
        "OAuth2": {
            "type": "oauth2",
            "flows": {
                "authorizationCode": {
                    "authorizationUrl": "/api/v1/security/oauth/authorize",
                    "tokenUrl": "/api/v1/security/oauth/token",
                    "scopes": {
                        "read": "Read access",
                        "write": "Write access",
                        "admin": "Admin access",
                    },
                }
            },
        },
    }

    # Default security requirement
    openapi_schema["security"] = [
        {"BearerToken": []},
        {"APIKey": []},
    ]

    # ── Servers ─────────────────────────────────────────────────────────
    openapi_schema["servers"] = [
        {
            "url": "http://localhost:8000",
            "description": "Development",
        },
        {
            "url": "https://staging-api.redteam-saas.com",
            "description": "Staging",
        },
        {
            "url": "https://api.redteam-saas.com",
            "description": "Production",
        },
    ]

    # ── Tags ────────────────────────────────────────────────────────────
    openapi_schema["tags"] = [
        {"name": "Auth", "description": "Authentication & authorization"},
        {"name": "Projects", "description": "Project management"},
        {"name": "Tools", "description": "Security tool definitions & execution"},
        {"name": "Findings", "description": "Vulnerability findings"},
        {"name": "Compliance", "description": "Compliance frameworks & assessments"},
        {"name": "Reports", "description": "Report generation & download"},
        {"name": "Analytics", "description": "Dashboard, KPIs & trends"},
        {"name": "Integrations", "description": "Third-party integrations (GitHub, Jira, Slack)"},
        {"name": "Security", "description": "API keys, IP whitelist, rate limits, audit logs"},
    ]

    # ── Custom extensions ───────────────────────────────────────────────
    openapi_schema["x-api-id"] = "red-team-saas"
    openapi_schema["x-api-lifecycle"] = "production"
    openapi_schema["x-api-version"] = "1.0.0"

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def setup_openapi(app: FastAPI) -> None:
    """Bind the custom OpenAPI generator to *app*."""
    app.openapi = lambda: custom_openapi(app)
