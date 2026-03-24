"""Integration tests for Phase 5: /exec-results and /findings endpoints"""
import pytest

from tests.conftest import TestingSessionLocal
from app.models.user import User, UserRoleEnum
from app.models.task import Task, TaskStatusEnum
from app.models.result import Result
from app.models.finding import Finding, Severity, FindingStatus
from app.core.security import PasswordHandler, JWTHandler


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_token(role: UserRoleEnum = UserRoleEnum.pentester, superuser: bool = False) -> str:
    db = TestingSessionLocal()
    try:
        suffix = role.value
        user = User(
            email=f"{suffix}@phase5.test",
            username=f"{suffix}_p5",
            hashed_password=PasswordHandler.hash_password("Pass123!"),
            role=role,
            is_active=True,
            is_superuser=superuser,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return JWTHandler.create_access_token({"sub": str(user.id), "email": user.email})
    finally:
        db.close()


def _make_viewer_token() -> str:
    return _make_token(UserRoleEnum.viewer)


def _make_pentester_token() -> str:
    return _make_token(UserRoleEnum.pentester)


def _seed_result(user_id: int, project_id: int = None, tool_name: str = "nmap",
                 risk_score: float = 5.0, success: bool = True,
                 findings_json: list = None) -> int:
    """Insert a Task + Result and return the Result id."""
    db = TestingSessionLocal()
    try:
        task = Task(
            user_id=user_id,
            status=TaskStatusEnum.completed,
            tool_name=tool_name,
            target="192.168.1.1",
            project_id=project_id,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        result = Result(
            task_id=task.id,
            tool_name=tool_name,
            target="192.168.1.1",
            success=success,
            risk_score=risk_score,
            exit_code=0,
            duration_seconds=1.5,
            findings=findings_json or [],
            parsed_output={},
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        return result.id, task.user_id
    finally:
        db.close()


def _get_user_id_from_token(token: str) -> int:
    payload = JWTHandler.verify_token(token)
    return int(payload["sub"])


def _seed_finding(project_id: int, result_id: int = None, severity: Severity = Severity.high,
                  status: FindingStatus = FindingStatus.open, is_duplicate: bool = False,
                  tool_name: str = "nmap") -> int:
    db = TestingSessionLocal()
    try:
        f = Finding(
            title="Test Finding",
            severity=severity,
            status=status,
            host="10.0.0.1",
            tool_name=tool_name,
            fingerprint=f"fp{project_id}{severity.value}{is_duplicate}",
            is_duplicate=is_duplicate,
            risk_score=6.0,
            project_id=project_id,
            result_id=result_id,
        )
        db.add(f)
        db.commit()
        db.refresh(f)
        return f.id
    finally:
        db.close()


# ── /exec-results ──────────────────────────────────────────────────────────────

class TestListExecResults:

    def test_list_results_paginated(self, client):
        token = _make_pentester_token()
        user_id = _get_user_id_from_token(token)
        for _ in range(3):
            _seed_result(user_id)

        resp = client.get(
            "/api/v1/exec-results/?skip=0&limit=2",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2

    def test_filter_by_tool(self, client):
        token = _make_pentester_token()
        user_id = _get_user_id_from_token(token)
        _seed_result(user_id, tool_name="nmap")
        _seed_result(user_id, tool_name="nikto")

        resp = client.get(
            "/api/v1/exec-results/?tool_name=nmap",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_filter_by_success(self, client):
        token = _make_pentester_token()
        user_id = _get_user_id_from_token(token)
        _seed_result(user_id, success=True)
        _seed_result(user_id, success=False)

        resp = client.get(
            "/api/v1/exec-results/?success=false",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_requires_auth(self, client):
        resp = client.get("/api/v1/exec-results/")
        assert resp.status_code in (401, 403)


class TestGetExecResult:

    def test_get_result_detail(self, client):
        token = _make_pentester_token()
        user_id = _get_user_id_from_token(token)
        result_id, _ = _seed_result(user_id)

        resp = client.get(
            f"/api/v1/exec-results/{result_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == result_id
        assert "raw_output" not in data

    def test_get_result_raw_output_viewer_forbidden(self, client):
        viewer_token = _make_viewer_token()
        pentester_token = _make_pentester_token()
        user_id = _get_user_id_from_token(pentester_token)
        result_id, _ = _seed_result(user_id)

        resp = client.get(
            f"/api/v1/exec-results/{result_id}?include_raw=true",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403

    def test_get_result_not_found(self, client):
        token = _make_pentester_token()
        resp = client.get(
            "/api/v1/exec-results/99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


class TestExportResult:

    def test_export_result_json(self, client):
        token = _make_pentester_token()
        user_id = _get_user_id_from_token(token)
        result_id, _ = _seed_result(user_id)

        resp = client.get(
            f"/api/v1/exec-results/{result_id}/export?format=json",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/json"
        assert f"result_{result_id}.json" in resp.headers.get("content-disposition", "")

    def test_export_result_csv(self, client):
        token = _make_pentester_token()
        user_id = _get_user_id_from_token(token)
        result_id, _ = _seed_result(
            user_id,
            findings_json=[{"severity": "high", "title": "SQL Injection", "description": "...", "host": "app.com"}],
        )

        resp = client.get(
            f"/api/v1/exec-results/{result_id}/export?format=csv",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        content = resp.text
        assert "severity" in content
        assert "SQL Injection" in content

    def test_export_invalid_format_rejected(self, client):
        token = _make_pentester_token()
        user_id = _get_user_id_from_token(token)
        result_id, _ = _seed_result(user_id)

        resp = client.get(
            f"/api/v1/exec-results/{result_id}/export?format=xml",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422


class TestProjectSummaryEndpoint:

    def test_project_summary_endpoint(self, client):
        token = _make_pentester_token()
        user_id = _get_user_id_from_token(token)
        _seed_result(user_id, project_id=55, success=True)
        _seed_result(user_id, project_id=55, success=False)

        resp = client.get(
            "/api/v1/exec-results/summary/55",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert "findings" in data
        assert data["results"]["total_scans"] == 2


# ── /findings ──────────────────────────────────────────────────────────────────

class TestListFindings:

    def test_list_findings_filtered_by_severity(self, client):
        token = _make_pentester_token()
        _seed_finding(project_id=100, severity=Severity.critical)
        _seed_finding(project_id=100, severity=Severity.low)

        resp = client.get(
            "/api/v1/findings/?project_id=100&severity=critical",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["severity"] == "critical"

    def test_list_findings_excludes_duplicates_by_default(self, client):
        token = _make_pentester_token()
        _seed_finding(project_id=200, is_duplicate=False)
        _seed_finding(project_id=200, is_duplicate=True)

        resp = client.get(
            "/api/v1/findings/?project_id=200",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_findings_requires_auth(self, client):
        resp = client.get("/api/v1/findings/")
        assert resp.status_code in (401, 403)


class TestUpdateFinding:

    def test_update_finding_status(self, client):
        token = _make_pentester_token()
        finding_id = _seed_finding(project_id=300)

        resp = client.patch(
            f"/api/v1/findings/{finding_id}",
            json={"status": "confirmed"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"

    def test_viewer_cannot_update_finding(self, client):
        viewer_token = _make_viewer_token()
        finding_id = _seed_finding(project_id=400)

        resp = client.patch(
            f"/api/v1/findings/{finding_id}",
            json={"status": "confirmed"},
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403

    def test_update_finding_not_found(self, client):
        token = _make_pentester_token()
        resp = client.patch(
            "/api/v1/findings/99999",
            json={"status": "resolved"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


class TestMarkFalsePositive:

    def test_mark_false_positive_endpoint(self, client):
        token = _make_pentester_token()
        finding_id = _seed_finding(project_id=500)

        resp = client.post(
            f"/api/v1/findings/{finding_id}/false-positive?reason=Not+applicable+in+this+env",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "false_positive"
        assert data["false_positive"] is True

    def test_viewer_cannot_mark_false_positive(self, client):
        viewer_token = _make_viewer_token()
        finding_id = _seed_finding(project_id=600)

        resp = client.post(
            f"/api/v1/findings/{finding_id}/false-positive?reason=test",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403


class TestFindingsStats:

    def test_findings_stats_endpoint(self, client):
        token = _make_pentester_token()
        _seed_finding(project_id=700, severity=Severity.critical)
        _seed_finding(project_id=700, severity=Severity.critical)
        _seed_finding(project_id=700, severity=Severity.high)

        resp = client.get(
            "/api/v1/findings/stats/700",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["by_severity"]["critical"] == 2
        assert data["by_severity"]["high"] == 1
        assert data["total"] == 3
        assert "total_open" in data
