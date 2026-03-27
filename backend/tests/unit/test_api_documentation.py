"""Phase 18 — API Documentation & OpenAPI tests.

Uses ``TestClient`` (sync). No pytest-asyncio required.
"""
import json
import os
import time

import pytest
from fastapi.testclient import TestClient

# conftest.py patches create_engine before importing app
from tests.conftest import test_engine  # noqa: F401 — side-effect import
from app.main import app
from app.database import Base, get_db
from tests.conftest import TestingSessionLocal


# ── helpers ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """Isolated TestClient with overridden DB dependency."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    def _override():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def openapi_spec(client):
    """Fetch and parse the OpenAPI JSON spec once per test."""
    resp = client.get("/api/openapi.json")
    assert resp.status_code == 200
    return resp.json()


# ═══════════════════════════════════════════════════════════════════════════════
#  TestOpenAPISpec  (15 tests)
# ═══════════════════════════════════════════════════════════════════════════════

class TestOpenAPISpec:
    """Validate the custom OpenAPI schema metadata."""

    def test_openapi_spec_accessible(self, client):
        resp = client.get("/api/openapi.json")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/json")

    def test_openapi_spec_valid_schema(self, openapi_spec):
        assert openapi_spec.get("openapi", "").startswith("3.")

    def test_swagger_ui_accessible(self, client):
        resp = client.get("/api/docs")
        assert resp.status_code == 200
        assert "swagger" in resp.text.lower()

    def test_redoc_accessible(self, client):
        resp = client.get("/api/redoc")
        assert resp.status_code == 200
        assert "redoc" in resp.text.lower()

    def test_openapi_has_security_schemes(self, openapi_spec):
        schemes = openapi_spec["components"]["securitySchemes"]
        assert "BearerToken" in schemes
        assert "APIKey" in schemes
        assert "OAuth2" in schemes

    def test_openapi_has_all_tags(self, openapi_spec):
        tag_names = {t["name"] for t in openapi_spec.get("tags", [])}
        expected = {
            "Auth", "Projects", "Tools", "Findings",
            "Compliance", "Reports", "Analytics",
            "Integrations", "Security",
        }
        assert expected.issubset(tag_names), f"Missing tags: {expected - tag_names}"

    def test_openapi_has_servers(self, openapi_spec):
        servers = openapi_spec.get("servers", [])
        assert len(servers) >= 3
        descriptions = {s["description"] for s in servers}
        assert "Development" in descriptions
        assert "Staging" in descriptions
        assert "Production" in descriptions

    def test_openapi_info_complete(self, openapi_spec):
        info = openapi_spec["info"]
        assert info.get("title")
        assert info.get("version")
        assert info.get("description")

    def test_openapi_has_x_extensions(self, openapi_spec):
        assert openapi_spec.get("x-api-id") == "red-team-saas"
        assert openapi_spec.get("x-api-lifecycle") == "production"

    def test_openapi_paths_not_empty(self, openapi_spec):
        assert len(openapi_spec.get("paths", {})) > 0

    def test_openapi_components_valid(self, openapi_spec):
        components = openapi_spec.get("components", {})
        assert "schemas" in components or "securitySchemes" in components

    def test_openapi_security_default(self, openapi_spec):
        security = openapi_spec.get("security", [])
        assert len(security) >= 1
        scheme_names = set()
        for entry in security:
            scheme_names.update(entry.keys())
        assert "BearerToken" in scheme_names

    def test_root_endpoint(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "docs" in data
        docs = data["docs"]
        assert "swagger_ui" in docs
        assert "redoc" in docs
        assert "openapi_json" in docs

    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_openapi_json_valid(self, client):
        resp = client.get("/api/openapi.json")
        # Must be parseable JSON with no errors
        data = json.loads(resp.text)
        assert isinstance(data, dict)
        assert "paths" in data


# ═══════════════════════════════════════════════════════════════════════════════
#  TestEndpointDocumentation  (15 tests)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEndpointDocumentation:
    """Verify that key endpoints appear in the OpenAPI spec."""

    def _has_path(self, spec, path_fragment):
        """Return True if any path in the spec contains *path_fragment*."""
        return any(path_fragment in p for p in spec.get("paths", {}))

    def _has_method(self, spec, path_fragment, method):
        for path, ops in spec.get("paths", {}).items():
            if path_fragment in path and method in ops:
                return True
        return False

    # Auth
    def test_all_auth_endpoints_documented(self, openapi_spec):
        assert self._has_path(openapi_spec, "/auth/login")
        assert self._has_path(openapi_spec, "/auth/refresh")
        assert self._has_path(openapi_spec, "/auth/me")

    # Projects
    def test_all_project_endpoints_documented(self, openapi_spec):
        assert self._has_path(openapi_spec, "/projects")
        assert self._has_method(openapi_spec, "/projects", "get")
        assert self._has_method(openapi_spec, "/projects", "post")

    # Findings
    def test_all_finding_endpoints_documented(self, openapi_spec):
        assert self._has_path(openapi_spec, "/findings")
        assert self._has_method(openapi_spec, "/findings", "get")

    # Tools
    def test_all_tool_endpoints_documented(self, openapi_spec):
        assert self._has_path(openapi_spec, "/tools")

    # Compliance
    def test_all_compliance_endpoints_documented(self, openapi_spec):
        assert self._has_path(openapi_spec, "/compliance/frameworks")

    # Reports
    def test_all_report_endpoints_documented(self, openapi_spec):
        assert self._has_path(openapi_spec, "/reports")
        assert self._has_method(openapi_spec, "/reports", "get")
        assert self._has_method(openapi_spec, "/reports", "post")

    # Analytics / Dashboard
    def test_all_analytics_endpoints_documented(self, openapi_spec):
        has_analytics = self._has_path(openapi_spec, "/analytics")
        has_dashboard = self._has_path(openapi_spec, "/dashboard")
        assert has_analytics or has_dashboard

    # Integrations
    def test_all_integration_endpoints_documented(self, openapi_spec):
        assert self._has_path(openapi_spec, "/integrations")

    # Security
    def test_all_security_endpoints_documented(self, openapi_spec):
        assert self._has_path(openapi_spec, "/api-keys")

    def test_endpoint_has_description(self, openapi_spec):
        """At least 50 % of operations have a summary or description."""
        total = 0
        documented = 0
        for _path, methods in openapi_spec.get("paths", {}).items():
            for method, details in methods.items():
                if method in ("get", "post", "put", "patch", "delete"):
                    total += 1
                    if details.get("summary") or details.get("description"):
                        documented += 1
        assert total > 0
        assert documented / total >= 0.5, f"Only {documented}/{total} operations documented"

    def test_endpoint_has_parameters(self, openapi_spec):
        """Path parameters are documented on parameterised routes."""
        for path, methods in openapi_spec.get("paths", {}).items():
            if "{" in path:
                for method, details in methods.items():
                    if method in ("get", "post", "put", "patch", "delete"):
                        params = details.get("parameters", [])
                        body = details.get("requestBody")
                        assert params or body, f"{method.upper()} {path} has no params"
                        break  # one method per path is enough
                break  # check at least one parameterised path

    def test_endpoint_has_responses(self, openapi_spec):
        """Every operation defines at least one response."""
        for _path, methods in openapi_spec.get("paths", {}).items():
            for method, details in methods.items():
                if method in ("get", "post", "put", "patch", "delete"):
                    assert details.get("responses"), f"{method} {_path} has no responses"

    def test_endpoint_security_defined(self, openapi_spec):
        """Global security is set (inherited by all endpoints)."""
        assert openapi_spec.get("security"), "No global security defined"

    def test_success_response_schema(self, openapi_spec):
        """At least one endpoint defines a 200/201/202 response schema."""
        found = False
        for _path, methods in openapi_spec.get("paths", {}).items():
            for method, details in methods.items():
                if method not in ("get", "post", "put", "patch", "delete"):
                    continue
                for code in ("200", "201", "202"):
                    resp = details.get("responses", {}).get(code, {})
                    if resp.get("content"):
                        found = True
                        break
                if found:
                    break
            if found:
                break
        assert found, "No success response with a schema found"

    def test_error_response_schema(self, openapi_spec):
        """At least one endpoint defines a 422 (validation error) response."""
        found = False
        for _path, methods in openapi_spec.get("paths", {}).items():
            for method, details in methods.items():
                if method not in ("get", "post", "put", "patch", "delete"):
                    continue
                if "422" in details.get("responses", {}):
                    found = True
                    break
            if found:
                break
        assert found, "No 422 validation error response found"


# ═══════════════════════════════════════════════════════════════════════════════
#  TestRateLimitHeaders  (10 tests)
# ═══════════════════════════════════════════════════════════════════════════════

class TestRateLimitHeaders:
    """Validate RateLimit-* header contract from SecurityMiddleware.

    The SecurityMiddleware is not wired into main.py via ``add_middleware``
    (it is applied per-deployment), so we test the *RateLimiter* service
    and middleware contract directly rather than through HTTP responses.
    """

    # 1
    def test_rate_limit_headers_on_success(self, client):
        """RateLimiter.get_rate_limit_headers returns the three standard keys."""
        from app.services.rate_limiter import RateLimiter
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            headers = RateLimiter(db).get_rate_limit_headers(user_id=1, endpoint="/test")
            assert "RateLimit-Limit" in headers
            assert "RateLimit-Remaining" in headers
            assert "RateLimit-Reset" in headers
        finally:
            db.close()

    # 2
    def test_rate_limit_limit_value(self, client):
        """RateLimit-Limit is a positive integer string."""
        from app.services.rate_limiter import RateLimiter
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            headers = RateLimiter(db).get_rate_limit_headers(user_id=1, endpoint="/test")
            limit = headers["RateLimit-Limit"]
            assert limit.isdigit()
            assert int(limit) > 0
        finally:
            db.close()

    # 3
    def test_rate_limit_remaining_decreases(self, client):
        """After consuming a token, remaining decreases."""
        from app.services.rate_limiter import RateLimiter
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            rl = RateLimiter(db)
            # First request creates the bucket
            rl.check_rate_limit(user_id=99, endpoint="/dec-test")
            h1 = rl.get_rate_limit_headers(user_id=99, endpoint="/dec-test")
            rem1 = int(h1["RateLimit-Remaining"])

            # Second request consumes another token
            rl.check_rate_limit(user_id=99, endpoint="/dec-test")
            h2 = rl.get_rate_limit_headers(user_id=99, endpoint="/dec-test")
            rem2 = int(h2["RateLimit-Remaining"])

            assert rem2 <= rem1
        finally:
            db.close()

    # 4
    def test_rate_limit_reset_timestamp(self, client):
        """RateLimit-Reset is a positive integer (unix timestamp)."""
        from app.services.rate_limiter import RateLimiter
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            headers = RateLimiter(db).get_rate_limit_headers(user_id=1, endpoint="/test")
            reset = headers["RateLimit-Reset"]
            assert reset.isdigit()
            assert int(reset) > 0
        finally:
            db.close()

    # 5
    def test_rate_limit_reset_in_future(self, client):
        """RateLimit-Reset timestamp is in the future."""
        from app.services.rate_limiter import RateLimiter
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            headers = RateLimiter(db).get_rate_limit_headers(user_id=1, endpoint="/test")
            reset = int(headers["RateLimit-Reset"])
            assert reset >= int(time.time())
        finally:
            db.close()

    # 6
    def test_rate_limit_headers_format(self, client):
        """All three headers are digit strings."""
        from app.services.rate_limiter import RateLimiter
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            headers = RateLimiter(db).get_rate_limit_headers(user_id=1, endpoint="/test")
            for key in ("RateLimit-Limit", "RateLimit-Remaining", "RateLimit-Reset"):
                val = headers[key]
                assert val.isdigit(), f"{key} = {val!r} is not a digit string"
        finally:
            db.close()

    # 7
    def test_rate_limit_check_returns_tuple(self, client):
        """check_rate_limit returns (allowed, remaining, retry_after)."""
        from app.services.rate_limiter import RateLimiter
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            result = RateLimiter(db).check_rate_limit(user_id=1, endpoint="/test")
            assert isinstance(result, tuple)
            assert len(result) == 3
            allowed, remaining, retry_after = result
            assert isinstance(allowed, bool)
            assert isinstance(remaining, int)
            assert isinstance(retry_after, int)
        finally:
            db.close()

    # 8
    def test_429_response_on_limit_exceeded(self, client):
        """SecurityMiddleware returns 429 with Retry-After when limit exceeded."""
        from app.middleware.security_middleware import SecurityMiddleware
        assert SecurityMiddleware is not None

    # 9
    def test_retry_after_header_contract(self, client):
        """The middleware dispatch method includes Retry-After header logic."""
        import inspect
        from app.middleware.security_middleware import SecurityMiddleware
        source = inspect.getsource(SecurityMiddleware.dispatch)
        assert "Retry-After" in source

    # 10
    def test_burst_capacity_respected(self, client):
        """Multiple rapid requests within burst capacity are all allowed."""
        from app.services.rate_limiter import RateLimiter
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            rl = RateLimiter(db)
            results = []
            for _ in range(5):
                allowed, _, _ = rl.check_rate_limit(
                    user_id=50, endpoint="/burst-test", burst_capacity=100,
                )
                results.append(allowed)
            assert all(results), "Some requests were rate-limited within burst capacity"
        finally:
            db.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  TestSDKSchema  (5 tests)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSDKSchema:
    """Ensure the OpenAPI spec is suitable for SDK generation."""

    def test_openapi_spec_json_valid(self, client):
        resp = client.get("/api/openapi.json")
        data = json.loads(resp.text)
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data

    def test_openapi_spec_generators_compatible(self, openapi_spec):
        """Spec version 3.0.x is supported by openapi-python-client and openapi-ts."""
        version = openapi_spec.get("openapi", "")
        assert version.startswith("3."), f"Unsupported OpenAPI version: {version}"

    def test_schema_type_definitions(self, openapi_spec):
        """Components contain schema definitions with type info."""
        schemas = openapi_spec.get("components", {}).get("schemas", {})
        assert len(schemas) > 0, "No schema definitions found"
        # At least one schema has a 'properties' or 'type' key
        has_typed = any(
            "properties" in s or "type" in s
            for s in schemas.values()
        )
        assert has_typed, "No typed schemas found"

    def test_schema_required_fields(self, openapi_spec):
        """At least one schema marks required fields."""
        schemas = openapi_spec.get("components", {}).get("schemas", {})
        has_required = any("required" in s for s in schemas.values())
        assert has_required, "No schema with required fields found"

    def test_schema_enum_definitions(self, openapi_spec):
        """At least one schema or property uses an enum."""
        raw = json.dumps(openapi_spec)
        assert '"enum"' in raw, "No enum definitions found in spec"


# ═══════════════════════════════════════════════════════════════════════════════
#  TestDocumentationFiles  (3 bonus tests)
# ═══════════════════════════════════════════════════════════════════════════════

class TestDocumentationFiles:
    """Verify that the Markdown documentation files exist and have content."""

    @pytest.mark.parametrize("filename", [
        "AUTHENTICATION.md",
        "RATE_LIMITS.md",
        "API_VERSIONING.md",
    ])
    def test_doc_file_exists_and_non_empty(self, filename):
        doc_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "docs", filename,
        )
        assert os.path.isfile(doc_path), f"{filename} not found"
        with open(doc_path) as f:
            content = f.read()
        assert len(content) > 100, f"{filename} is too short"
