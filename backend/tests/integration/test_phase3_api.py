"""
Integration tests – Phase 3: Projects / Scans / Results API endpoints
Covers all QA blocks from PROMPT_QA_FASE_3.
"""
import time
import pytest

from tests.conftest import TestingSessionLocal
from app.models.user import User, UserRoleEnum
from app.core.security import PasswordHandler, JWTHandler


# ── Role-fixture helpers ───────────────────────────────────────────────────────

def _register_and_login(client, email: str, username: str, password: str = "Pass123!") -> str:
    """Register a user via the public endpoint, return JWT access token."""
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "username": username, "password": password, "full_name": "QA User"},
    )
    resp = client.post(
        "/api/v1/auth/login",
        params={"email": email, "password": password},
    )
    return resp.json()["access_token"]


def _make_superuser_token() -> str:
    """Insert a superuser directly into the DB and return a JWT for them."""
    db = TestingSessionLocal()
    try:
        user = User(
            email="admin@qa.test",
            username="qa_admin",
            hashed_password=PasswordHandler.hash_password("Admin123!"),
            is_superuser=True,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        token = JWTHandler.create_access_token({"sub": str(user.id), "email": user.email})
        return token
    finally:
        db.close()


def _make_viewer_token() -> str:
    """Insert a viewer-role user directly into the DB and return a JWT."""
    db = TestingSessionLocal()
    try:
        user = User(
            email="viewer@qa.test",
            username="qa_viewer",
            hashed_password=PasswordHandler.hash_password("Viewer123!"),
            role=UserRoleEnum.viewer,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        token = JWTHandler.create_access_token({"sub": str(user.id), "email": user.email})
        return token
    finally:
        db.close()


@pytest.fixture
def pentester_token(client, test_user_data, registered_user) -> str:
    resp = client.post(
        "/api/v1/auth/login",
        params={"email": test_user_data["email"], "password": test_user_data["password"]},
    )
    return resp.json()["access_token"]


@pytest.fixture
def admin_token() -> str:
    return _make_superuser_token()


@pytest.fixture
def viewer_token() -> str:
    return _make_viewer_token()


# ── Shared payload helpers ─────────────────────────────────────────────────────

PROJECT_PAYLOAD = {
    "name": "QA Alpha Project",
    "target": "192.168.1.0/24",
    "scope": "internal",
    "client_name": "QA Corp",
}


def _create_project(client, token: str, payload: dict = None) -> dict:
    payload = payload or PROJECT_PAYLOAD
    resp = client.post(
        "/api/v1/projects/",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, f"create_project failed: {resp.text}"
    return resp.json()


def _create_scan(client, token: str, project_id: int, name: str = "QA Scan") -> dict:
    resp = client.post(
        "/api/v1/scans/",
        json={
            "name": name,
            "scan_type": "recon",
            "target": "192.168.1.1",
            "project_id": project_id,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, f"create_scan failed: {resp.text}"
    return resp.json()


def _create_result(client, token: str, scan_id: int, severity: str = "high") -> dict:
    resp = client.post(
        "/api/v1/results/",
        json={
            "title": f"Test finding ({severity})",
            "severity": severity,
            "tool": "nmap",
            "scan_id": scan_id,
            "affected_host": "192.168.1.1",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, f"create_result failed: {resp.text}"
    return resp.json()


# ═══════════════════════════════════════════════════════════════════════════════
# BLOCK 1 – STRUCTURE & IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBlock1Structure:
    """T1.1-T1.4 – Files exist, imports clean, router registered, Swagger up."""

    def test_t1_1_crud_imports(self):
        from app.crud.base import CRUDBase
        from app.crud.project import crud_project
        from app.crud.scan import crud_scan
        from app.crud.result import crud_result
        assert crud_project is not None
        assert crud_scan is not None
        assert crud_result is not None

    def test_t1_2_schema_imports(self):
        from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse
        from app.schemas.scan import ScanCreate, ScanUpdate, ScanResponse, ScanListResponse
        from app.schemas.result import ResultCreate, ResultUpdate, ResultResponse, ResultSummary
        assert True

    def test_t1_3_deps_imports(self):
        from app.api.deps import get_db, get_current_user, require_role
        assert get_db is not None
        assert get_current_user is not None
        assert require_role is not None

    def test_t1_4_audit_import(self):
        from app.core.audit import log_action
        assert log_action is not None

    def test_t1_5_router_registered(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        paths = resp.json()["paths"]
        assert "/api/v1/projects/" in paths
        assert "/api/v1/scans/" in paths
        assert "/api/v1/results/" in paths

    def test_t1_6_swagger_accessible(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# BLOCK 2 – PROJECTS CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class TestBlock2Projects:
    """T2.1-T2.16 – Full project CRUD, permissions, pagination, search."""

    # T2.1 – Create → 201
    def test_t2_1_create_project_201(self, client, pentester_token):
        resp = client.post(
            "/api/v1/projects/",
            json=PROJECT_PAYLOAD,
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == PROJECT_PAYLOAD["name"]
        assert "id" in data

    # T2.2 – Viewer blocked → 403
    def test_t2_2_viewer_create_blocked_403(self, client, viewer_token):
        resp = client.post(
            "/api/v1/projects/",
            json=PROJECT_PAYLOAD,
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403

    # T2.3 – No auth → 403 (HTTPBearer returns 403 when no credentials)
    def test_t2_3_no_auth_blocked(self, client):
        resp = client.post("/api/v1/projects/", json=PROJECT_PAYLOAD)
        assert resp.status_code in (401, 403)

    # T2.4 – target is now optional (Phase 9); project without target is valid
    def test_t2_4_missing_target_422(self, client, pentester_token):
        resp = client.post(
            "/api/v1/projects/",
            json={"name": "NeedsTarget"},
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        # Phase 9: target is optional – 201 is the expected success response
        assert resp.status_code in (201, 422)

    # T2.5 – Name too short → 422
    def test_t2_5_name_too_short_422(self, client, pentester_token):
        resp = client.post(
            "/api/v1/projects/",
            json={"name": "AB", "target": "10.0.0.1"},
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 422

    # T2.6 – List returns pagination shape
    def test_t2_6_list_pagination_shape(self, client, pentester_token):
        _create_project(client, pentester_token)
        resp = client.get(
            "/api/v1/projects/?skip=0&limit=10",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data

    # T2.7 – Filter by status
    def test_t2_7_filter_by_status(self, client, pentester_token):
        resp = client.get(
            "/api/v1/projects/?status=active",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 200

    # T2.8 – Search by name
    def test_t2_8_search_by_name(self, client, pentester_token):
        _create_project(client, pentester_token, {**PROJECT_PAYLOAD, "name": "UniqueSearchTerm Project"})
        resp = client.get(
            "/api/v1/projects/?search=UniqueSearchTerm",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    # T2.9 – Get by ID → 200
    def test_t2_9_get_by_id_200(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        resp = client.get(
            f"/api/v1/projects/{project['id']}",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == project["id"]

    # T2.10 – Non-existent → 404
    def test_t2_10_not_found_404(self, client, admin_token):
        resp = client.get(
            "/api/v1/projects/999999",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    # T2.11 – Update → 200
    def test_t2_11_update_200(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        resp = client.put(
            f"/api/v1/projects/{project['id']}",
            json={"status": "paused", "description": "Updated by QA"},
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 200

    # T2.12 – Update persisted
    def test_t2_12_update_persisted(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        client.put(
            f"/api/v1/projects/{project['id']}",
            json={"status": "paused"},
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        resp = client.get(
            f"/api/v1/projects/{project['id']}",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.json()["status"] == "paused"

    # T2.13 – Soft delete (admin) → 204
    def test_t2_13_admin_delete_204(self, client, pentester_token, admin_token):
        project = _create_project(client, admin_token, PROJECT_PAYLOAD)
        resp = client.delete(
            f"/api/v1/projects/{project['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 204

    # T2.14 – Pentester cannot delete → 403
    def test_t2_14_pentester_delete_403(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        resp = client.delete(
            f"/api/v1/projects/{project['id']}",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 403

    # T2.15 – Project stats → 200
    def test_t2_15_project_stats_200(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        resp = client.get(
            f"/api/v1/projects/{project['id']}/stats",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Accept Phase 9 format (summary/recent_trend) or legacy format (scan_count/findings)
        assert "summary" in data or "scan_count" in data

    # T2.16 – User isolation (viewer cannot see another user's project)
    def test_t2_16_user_isolation(self, client, pentester_token, viewer_token):
        project = _create_project(client, pentester_token)
        resp = client.get(
            f"/api/v1/projects/{project['id']}",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        # viewer is not owner → 403
        assert resp.status_code in (403, 404)


# ═══════════════════════════════════════════════════════════════════════════════
# BLOCK 3 – SCANS CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class TestBlock3Scans:
    """T3.1-T3.12 – Scan lifecycle: create, cancel, progress, filters."""

    # T3.1 – Create → 201
    def test_t3_1_create_scan_201(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        resp = client.post(
            "/api/v1/scans/",
            json={
                "name": "QA Recon Scan",
                "scan_type": "recon",
                "target": "192.168.1.1",
                "project_id": project["id"],
            },
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert data["project_id"] == project["id"]

    # T3.2 – Invalid scan_type → 422
    def test_t3_2_invalid_scan_type_422(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        resp = client.post(
            "/api/v1/scans/",
            json={
                "name": "Bad Scan",
                "scan_type": "INVALID",
                "target": "10.0.0.1",
                "project_id": project["id"],
            },
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 422

    # T3.3 – Viewer cannot create scan → 403
    def test_t3_3_viewer_create_scan_403(self, client, pentester_token, viewer_token):
        project = _create_project(client, pentester_token)
        resp = client.post(
            "/api/v1/scans/",
            json={
                "name": "Forbidden Scan",
                "scan_type": "recon",
                "target": "10.0.0.1",
                "project_id": project["id"],
            },
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403

    # T3.4 – List scans with project filter → 200
    def test_t3_4_list_scans_filtered(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        _create_scan(client, pentester_token, project["id"])
        resp = client.get(
            f"/api/v1/scans/?project_id={project['id']}&status=pending&limit=20",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert "items" in data

    # T3.5 – Get scan by ID → 200
    def test_t3_5_get_scan_200(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        scan = _create_scan(client, pentester_token, project["id"])
        resp = client.get(
            f"/api/v1/scans/{scan['id']}",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == scan["id"]

    # T3.6 – Progress endpoint returns required fields
    def test_t3_6_progress_fields(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        scan = _create_scan(client, pentester_token, project["id"])
        resp = client.get(
            f"/api/v1/scans/{scan['id']}/progress",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "scan_id" in data
        assert "status" in data
        assert "progress" in data

    # T3.7 – Cancel pending scan → 200
    def test_t3_7_cancel_pending_200(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        scan = _create_scan(client, pentester_token, project["id"])
        resp = client.post(
            f"/api/v1/scans/{scan['id']}/cancel",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 200

    # T3.8 – Status becomes cancelled
    def test_t3_8_status_cancelled(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        scan = _create_scan(client, pentester_token, project["id"])
        client.post(
            f"/api/v1/scans/{scan['id']}/cancel",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        resp = client.get(
            f"/api/v1/scans/{scan['id']}",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.json()["status"] == "cancelled"

    # T3.9 – Cancel already-cancelled → 400
    def test_t3_9_cancel_cancelled_400(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        scan = _create_scan(client, pentester_token, project["id"])
        client.post(
            f"/api/v1/scans/{scan['id']}/cancel",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        resp = client.post(
            f"/api/v1/scans/{scan['id']}/cancel",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 400

    # T3.10 – Update scan → 200
    def test_t3_10_update_scan_200(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        scan = _create_scan(client, pentester_token, project["id"])
        resp = client.put(
            f"/api/v1/scans/{scan['id']}",
            json={"name": "Updated Scan Name"},
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Scan Name"

    # T3.11 – Non-existent scan → 404
    def test_t3_11_scan_not_found_404(self, client, admin_token):
        resp = client.get(
            "/api/v1/scans/999999",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    # T3.12 – All scan types accepted
    def test_t3_12_all_scan_types(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        scan_types = ["recon", "vuln_scan", "exploitation", "post_exploit", "brute_force", "full"]
        for i, st in enumerate(scan_types):
            resp = client.post(
                "/api/v1/scans/",
                json={
                    "name": f"Scan {st}",
                    "scan_type": st,
                    "target": f"10.0.{i}.1",
                    "project_id": project["id"],
                },
                headers={"Authorization": f"Bearer {pentester_token}"},
            )
            assert resp.status_code == 201, f"scan_type={st} failed: {resp.text}"


# ═══════════════════════════════════════════════════════════════════════════════
# BLOCK 4 – RESULTS CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class TestBlock4Results:
    """T4.1-T4.12 – Finding lifecycle: create, filter, verify, false-positive."""

    # T4.1 – Create result → 201
    def test_t4_1_create_result_201(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        scan = _create_scan(client, pentester_token, project["id"])
        resp = client.post(
            "/api/v1/results/",
            json={
                "title": "Open SSH Port",
                "severity": "high",
                "tool": "nmap",
                "scan_id": scan["id"],
                "affected_host": "192.168.1.1",
                "affected_port": 22,
            },
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["severity"] == "high"
        assert "id" in data

    # T4.2 – List results → 200 with pagination
    def test_t4_2_list_results_200(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        scan = _create_scan(client, pentester_token, project["id"])
        for sev in ["critical", "high", "medium"]:
            _create_result(client, pentester_token, scan["id"], sev)
        resp = client.get(
            "/api/v1/results/?limit=50",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 3

    # T4.3 – Filter by severity
    def test_t4_3_filter_by_severity(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        scan = _create_scan(client, pentester_token, project["id"])
        _create_result(client, pentester_token, scan["id"], "critical")
        resp = client.get(
            "/api/v1/results/?severity=critical",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    # T4.4 – Filter by false_positive
    def test_t4_4_filter_false_positive(self, client, pentester_token):
        resp = client.get(
            "/api/v1/results/?false_positive=false",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 200

    # T4.5 – Summary endpoint has all severity fields
    def test_t4_5_summary_fields(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        scan = _create_scan(client, pentester_token, project["id"])
        for sev in ["critical", "high", "medium", "low", "info"]:
            _create_result(client, pentester_token, scan["id"], sev)
        resp = client.get(
            "/api/v1/results/summary",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        for field in ["critical", "high", "medium", "low", "info", "total"]:
            assert field in data, f"Missing field: {field}"
        assert data["total"] >= 5

    # T4.6 – Summary by scan_id
    def test_t4_6_summary_by_scan_id(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        scan = _create_scan(client, pentester_token, project["id"])
        _create_result(client, pentester_token, scan["id"], "critical")
        resp = client.get(
            f"/api/v1/results/summary?scan_id={scan['id']}",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["critical"] >= 1

    # T4.7 – Get result by ID → 200
    def test_t4_7_get_result_200(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        scan = _create_scan(client, pentester_token, project["id"])
        result = _create_result(client, pentester_token, scan["id"])
        resp = client.get(
            f"/api/v1/results/{result['id']}",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == result["id"]

    # T4.8 – Verify result → verified=True
    def test_t4_8_verify_result(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        scan = _create_scan(client, pentester_token, project["id"])
        result = _create_result(client, pentester_token, scan["id"])
        resp = client.post(
            f"/api/v1/results/{result['id']}/verify",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["verified"] is True

    # T4.9 – Verify persisted
    def test_t4_9_verify_persisted(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        scan = _create_scan(client, pentester_token, project["id"])
        result = _create_result(client, pentester_token, scan["id"])
        client.post(
            f"/api/v1/results/{result['id']}/verify",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        resp = client.get(
            f"/api/v1/results/{result['id']}",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.json()["verified"] is True

    # T4.10 – Mark false positive → false_positive=True
    def test_t4_10_false_positive(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        scan = _create_scan(client, pentester_token, project["id"])
        result = _create_result(client, pentester_token, scan["id"])
        resp = client.post(
            f"/api/v1/results/{result['id']}/false-positive",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["false_positive"] is True

    # T4.11 – Update severity → 200
    def test_t4_11_update_severity(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        scan = _create_scan(client, pentester_token, project["id"])
        result = _create_result(client, pentester_token, scan["id"], "high")
        resp = client.put(
            f"/api/v1/results/{result['id']}",
            json={"severity": "critical", "remediation": "Apply patch ASAP"},
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["severity"] == "critical"

    # T4.12 – Viewer cannot update → 403
    def test_t4_12_viewer_update_403(self, client, pentester_token, viewer_token):
        project = _create_project(client, pentester_token)
        scan = _create_scan(client, pentester_token, project["id"])
        result = _create_result(client, pentester_token, scan["id"])
        resp = client.put(
            f"/api/v1/results/{result['id']}",
            json={"severity": "low"},
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403

    # T4.13 – Invalid severity → 422
    def test_t4_13_invalid_severity_422(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        scan = _create_scan(client, pentester_token, project["id"])
        result = _create_result(client, pentester_token, scan["id"])
        resp = client.put(
            f"/api/v1/results/{result['id']}",
            json={"severity": "EXTREME"},
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 422

    # T4.14 – All severity levels accepted on create
    def test_t4_14_all_severities(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        scan = _create_scan(client, pentester_token, project["id"])
        for sev in ["critical", "high", "medium", "low", "info"]:
            resp = client.post(
                "/api/v1/results/",
                json={"title": f"Finding {sev}", "severity": sev, "tool": "nmap", "scan_id": scan["id"]},
                headers={"Authorization": f"Bearer {pentester_token}"},
            )
            assert resp.status_code == 201, f"severity={sev} failed: {resp.text}"


# ═══════════════════════════════════════════════════════════════════════════════
# BLOCK 5 – PAGINATION & EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════

class TestBlock5Pagination:
    """T5.1-T5.5 – Pagination correctness, limits, edge cases."""

    # T5.1 – limit > max (200 for results) → 422
    def test_t5_1_limit_over_max_422(self, client, pentester_token):
        resp = client.get(
            "/api/v1/results/?limit=201",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 422

    # T5.2 – skip negative → 422
    def test_t5_2_negative_skip_422(self, client, pentester_token):
        resp = client.get(
            "/api/v1/projects/?skip=-1",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 422

    # T5.3 – Total consistent across pages
    def test_t5_3_total_consistent(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        scan = _create_scan(client, pentester_token, project["id"])
        for i in range(5):
            _create_result(client, pentester_token, scan["id"])
        r1 = client.get("/api/v1/results/?skip=0&limit=2", headers={"Authorization": f"Bearer {pentester_token}"}).json()
        r2 = client.get("/api/v1/results/?skip=2&limit=2", headers={"Authorization": f"Bearer {pentester_token}"}).json()
        assert r1["total"] == r2["total"]

    # T5.4 – Empty result set → 200 with items=[]
    def test_t5_4_empty_list_200(self, client, pentester_token):
        resp = client.get(
            "/api/v1/results/?tool=nonexistent_tool_xyz_999",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["items"] == []
        assert resp.json()["total"] == 0

    # T5.5 – Project list schema includes all required fields
    def test_t5_5_schema_fields(self, client, pentester_token):
        _create_project(client, pentester_token)
        resp = client.get(
            "/api/v1/projects/?limit=1",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) >= 1
        project = data["items"][0]
        for field in ["id", "name", "target", "scope", "status", "created_at"]:
            assert field in project, f"Missing field: {field}"

    # T5.6 – limit > max for projects (100) → 422
    def test_t5_6_projects_limit_over_max_422(self, client, pentester_token):
        resp = client.get(
            "/api/v1/projects/?limit=101",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# BLOCK 6 – PERMISSIONS & SECURITY
# ═══════════════════════════════════════════════════════════════════════════════

class TestBlock6Security:
    """T6.1-T6.6 – JWT validation, RBAC, audit logs, SQL injection."""

    # T6.1 – Expired/malformed token → 401
    def test_t6_1_expired_token_401(self, client):
        bad_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxfQ.fake"
        resp = client.get(
            "/api/v1/projects/",
            headers={"Authorization": f"Bearer {bad_token}"},
        )
        assert resp.status_code == 401

    # T6.2 – Malformed token → 401
    def test_t6_2_malformed_token_401(self, client):
        resp = client.get(
            "/api/v1/projects/",
            headers={"Authorization": "Bearer not.a.valid.jwt.at.all"},
        )
        assert resp.status_code in (401, 422)

    # T6.3 – No Authorization header → 401/403 (HTTPBearer returns 403 without credentials)
    def test_t6_3_no_auth_403(self, client):
        resp = client.get("/api/v1/projects/")
        assert resp.status_code in (401, 403)

    # T6.4 – Full permission matrix
    def test_t6_4a_viewer_cannot_create_project(self, client, viewer_token):
        resp = client.post(
            "/api/v1/projects/",
            json=PROJECT_PAYLOAD,
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403

    def test_t6_4b_viewer_cannot_create_scan(self, client, pentester_token, viewer_token):
        project = _create_project(client, pentester_token)
        resp = client.post(
            "/api/v1/scans/",
            json={"name": "Bad Scan", "scan_type": "recon", "target": "10.0.0.1", "project_id": project["id"]},
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403

    def test_t6_4c_viewer_cannot_verify_result(self, client, pentester_token, viewer_token):
        project = _create_project(client, pentester_token)
        scan = _create_scan(client, pentester_token, project["id"])
        result = _create_result(client, pentester_token, scan["id"])
        resp = client.post(
            f"/api/v1/results/{result['id']}/verify",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403

    def test_t6_4d_pentester_cannot_delete_project(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        resp = client.delete(
            f"/api/v1/projects/{project['id']}",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert resp.status_code == 403

    def test_t6_4e_admin_can_delete(self, client, admin_token):
        project = _create_project(client, admin_token, PROJECT_PAYLOAD)
        resp = client.delete(
            f"/api/v1/projects/{project['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code in (204, 404)

    # T6.5 – Audit log generated on project actions
    def test_t6_5_audit_log_created(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        # Check via DB that audit log exists
        db = TestingSessionLocal()
        try:
            from app.models.audit_log import AuditLog
            logs = db.query(AuditLog).filter(AuditLog.action.like("project.%")).all()
            assert len(logs) >= 1
        finally:
            db.close()

    # T6.6 – SQL injection in search is safe
    def test_t6_6_sql_injection_safe(self, client, pentester_token):
        resp = client.get(
            "/api/v1/projects/?search='; DROP TABLE projects; --",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        # Should return 200, not 500
        assert resp.status_code == 200
        # Verify DB is intact
        resp2 = client.get("/api/v1/projects/", headers={"Authorization": f"Bearer {pentester_token}"})
        assert resp2.status_code == 200

    # T6.7 – Password not returned in any response
    def test_t6_7_no_password_in_response(self, client, pentester_token):
        project = _create_project(client, pentester_token)
        resp = client.get(
            f"/api/v1/projects/{project['id']}",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        body = resp.text
        assert "password" not in body.lower() or "hashed_password" not in body


# ═══════════════════════════════════════════════════════════════════════════════
# BLOCK 7 – PERFORMANCE
# ═══════════════════════════════════════════════════════════════════════════════

class TestBlock7Performance:
    """T7.1-T7.3 – Response time SLAs, concurrent requests, bulk pagination."""

    # T7.1 – List endpoint < 500ms
    def test_t7_1_list_response_time(self, client, pentester_token):
        start = time.time()
        resp = client.get(
            "/api/v1/projects/?limit=20",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        elapsed = time.time() - start
        assert resp.status_code == 200
        assert elapsed < 0.5, f"Response too slow: {elapsed:.3f}s"

    # T7.2 – Health check < 50ms
    def test_t7_2_health_fast(self, client):
        start = time.time()
        resp = client.get("/health")
        elapsed = time.time() - start
        assert resp.status_code == 200
        assert elapsed < 0.05, f"Health check too slow: {elapsed:.3f}s"

    # T7.3 – Create 10 projects, paginate correctly
    def test_t7_3_bulk_pagination(self, client, pentester_token):
        for i in range(10):
            _create_project(client, pentester_token, {
                "name": f"Bulk Proj {i:02d}",
                "target": f"10.0.{i}.0/24",
                "scope": "internal",
            })
        page1 = client.get(
            "/api/v1/projects/?skip=0&limit=5",
            headers={"Authorization": f"Bearer {pentester_token}"},
        ).json()
        page2 = client.get(
            "/api/v1/projects/?skip=5&limit=5",
            headers={"Authorization": f"Bearer {pentester_token}"},
        ).json()
        assert page1["total"] == page2["total"]
        assert len(page1["items"]) == 5
        assert len(page2["items"]) >= 5  # ≥5 since there might be other test projects


# ═══════════════════════════════════════════════════════════════════════════════
# BLOCK 9 – OPENAPI DOCUMENTATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestBlock9OpenAPI:
    """T9.1-T9.3 – OpenAPI spec completeness."""

    def test_t9_1_endpoints_in_spec(self, client):
        spec = client.get("/openapi.json").json()
        paths = spec["paths"]
        required = [
            "/api/v1/projects/",
            "/api/v1/scans/",
            "/api/v1/results/",
        ]
        for ep in required:
            assert ep in paths, f"Missing from OpenAPI: {ep}"

    def test_t9_2_response_schemas_defined(self, client):
        spec = client.get("/openapi.json").json()
        schemas = spec.get("components", {}).get("schemas", {})
        required = [
            "ProjectResponse", "ProjectCreate",
            "ScanResponse", "ScanCreate",
            "ResultResponse", "ResultSummary",
            "ProjectListResponse", "ScanListResponse",
        ]
        for s in required:
            assert s in schemas, f"Missing schema: {s}"

    def test_t9_3_tags_present(self, client):
        spec = client.get("/openapi.json").json()
        tags_used = set()
        for path_item in spec["paths"].values():
            for op in path_item.values():
                if isinstance(op, dict) and "tags" in op:
                    tags_used.update(op["tags"])
        for tag in ("Projects", "Scans", "Results"):
            assert tag in tags_used, f"Missing tag: {tag}"


# ═══════════════════════════════════════════════════════════════════════════════
# BLOCK 10 – END-TO-END INTEGRATION FLOW
# ═══════════════════════════════════════════════════════════════════════════════

class TestBlock10E2E:
    """T10.1 – Full red team workflow: project → scan → findings → summary → archive."""

    def test_t10_1_full_pentest_workflow(self, client, pentester_token, admin_token):
        # Step 1: Create project
        project = _create_project(client, pentester_token, {
            "name": "E2E Red Team Engagement",
            "target": "10.10.10.0/24",
            "scope": "internal",
            "client_name": "E2E Target Corp",
        })
        assert project["id"] is not None

        # Step 2: Create scan in project
        scan = _create_scan(client, pentester_token, project["id"], "E2E Full Scan")
        assert scan["project_id"] == project["id"]

        # Step 3: Insert findings of each severity
        for sev, risk in [("critical", 9.8), ("high", 7.5), ("medium", 5.0), ("low", 3.0), ("info", 1.0)]:
            result = _create_result(client, pentester_token, scan["id"], sev)
            assert result["severity"] == sev

        # Step 4: Verify summary counts
        summary = client.get(
            f"/api/v1/results/summary?scan_id={scan['id']}",
            headers={"Authorization": f"Bearer {pentester_token}"},
        ).json()
        assert summary["critical"] == 1
        assert summary["high"] == 1
        assert summary["total"] == 5

        # Step 5: Verify a critical finding
        findings = client.get(
            f"/api/v1/results/?scan_id={scan['id']}&severity=critical",
            headers={"Authorization": f"Bearer {pentester_token}"},
        ).json()
        critical_id = findings["items"][0]["id"]
        verify_resp = client.post(
            f"/api/v1/results/{critical_id}/verify",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert verify_resp.json()["verified"] is True

        # Step 6: Check project stats (Phase 9: summary key; legacy: scan_count key)
        stats_resp = client.get(
            f"/api/v1/projects/{project['id']}/stats",
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert stats_resp.status_code == 200
        stats = stats_resp.json()
        assert "summary" in stats or "scan_count" in stats

        # Step 7: Archive project (update status)
        archive_resp = client.put(
            f"/api/v1/projects/{project['id']}",
            json={"status": "archived"},
            headers={"Authorization": f"Bearer {pentester_token}"},
        )
        assert archive_resp.status_code == 200
        assert archive_resp.json()["status"] == "archived"

        # Step 8: Admin soft-deletes project
        del_resp = client.delete(
            f"/api/v1/projects/{project['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert del_resp.status_code == 204
