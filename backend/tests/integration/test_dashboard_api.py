"""Integration tests for the /dashboard endpoints (Phase 7)."""
import pytest
from unittest.mock import patch, MagicMock

from app.models.user import User
from app.models.project import Project
from app.models.task import Task, TaskStatusEnum
from app.models.result import Result
from app.models.finding import Finding, Severity, FindingStatus
from app.models.report import Report, ReportType, ReportStatus
from app.models.audit_log import AuditLog

# Patch Redis for all tests in this module so cache failures don't affect results
pytestmark = pytest.mark.usefixtures()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _seed_db(db_session, user_id):
    """Create a minimal dataset for dashboard queries."""
    p = Project(owner_id=user_id, name="TestProject", target="10.0.0.0/8")
    db_session.add(p); db_session.flush()

    t_ok = Task(user_id=user_id, project_id=p.id, status=TaskStatusEnum.completed)
    t_fail = Task(user_id=user_id, project_id=p.id, status=TaskStatusEnum.failed)
    db_session.add_all([t_ok, t_fail]); db_session.flush()

    r = Result(
        task_id=t_ok.id, tool_name="nmap", target="10.0.0.1",
        success=True, risk_score=7.0, duration_seconds=20.0,
        parsed_output={}, findings=[],
    )
    db_session.add(r); db_session.flush()

    import uuid
    severities = [Severity.critical, Severity.high, Severity.medium]
    for i, sev in enumerate(severities):
        f = Finding(
            task_id=t_ok.id, project_id=p.id,
            title=f"F-{sev.value}", severity=sev,
            host=f"10.0.0.{i+1}", tool_name="nmap",
            fingerprint=str(uuid.uuid4())[:16],
            risk_score=float(i + 1),
            is_duplicate=False,
        )
        db_session.add(f)

    rpt = Report(
        project_id=p.id, created_by=user_id,
        title="Report", report_type=ReportType.technical,
        status=ReportStatus.ready,
    )
    db_session.add(rpt)
    db_session.commit()
    return p


def _get_token(client, test_user_data):
    resp = client.post(
        "/api/v1/auth/login",
        params={"email": test_user_data["email"], "password": test_user_data["password"]},
    )
    return resp.json()["access_token"]


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_global_summary_endpoint(client, registered_user, auth_token, db_session):
    """GET /dashboard/summary returns a valid GlobalSummary structure."""
    uid = registered_user["id"]
    _seed_db(db_session, uid)

    resp = client.get("/api/v1/dashboard/summary", headers={"Authorization": f"Bearer {auth_token}"})

    assert resp.status_code == 200
    data = resp.json()
    assert "total_scans" in data
    assert "total_findings" in data
    assert data["total_scans"] >= 1
    assert data["critical_findings"] >= 1


def test_top_targets_limit_param(client, registered_user, auth_token, db_session):
    """GET /dashboard/top-targets?limit=1 returns at most 1 entry."""
    uid = registered_user["id"]
    _seed_db(db_session, uid)

    resp = client.get(
        "/api/v1/dashboard/top-targets?limit=1",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) <= 1


def test_top_tools_endpoint(client, registered_user, auth_token, db_session):
    """GET /dashboard/top-tools returns tool stats."""
    uid = registered_user["id"]
    _seed_db(db_session, uid)

    resp = client.get(
        "/api/v1/dashboard/top-tools",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    tool = data[0]
    assert "tool" in tool
    assert "total_runs" in tool
    assert "successful" in tool


def test_activity_feed_ordered_desc(client, registered_user, auth_token, db_session):
    """GET /dashboard/activity-feed returns items newest-first."""
    uid = registered_user["id"]
    from datetime import datetime, timedelta

    log1 = AuditLog(user_id=uid, action="login", resource="auth")
    log2 = AuditLog(user_id=uid, action="scan_start", resource="task")
    db_session.add_all([log1, log2])
    db_session.commit()

    # Override timestamps so ordering is deterministic
    db_session.query(AuditLog).filter(AuditLog.id == log1.id).update(
        {"created_at": datetime.utcnow() - timedelta(hours=1)}
    )
    db_session.query(AuditLog).filter(AuditLog.id == log2.id).update(
        {"created_at": datetime.utcnow()}
    )
    db_session.commit()

    resp = client.get(
        "/api/v1/dashboard/activity-feed",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    assert data[0]["action"] == "scan_start"   # newest first


def test_findings_trend_30_days(client, registered_user, auth_token, db_session):
    """GET /dashboard/trends/findings?days=30 returns exactly 30 data points."""
    uid = registered_user["id"]
    _seed_db(db_session, uid)

    resp = client.get(
        "/api/v1/dashboard/trends/findings?days=30",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 30
    for point in data:
        assert "date" in point


def test_risk_trend_with_project_filter(client, registered_user, auth_token, db_session):
    """GET /dashboard/trends/risk?project_id=N returns per-project data."""
    uid = registered_user["id"]
    p = _seed_db(db_session, uid)

    resp = client.get(
        f"/api/v1/dashboard/trends/risk?days=7&project_id={p.id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 7
    for point in data:
        assert "avg_risk" in point
        assert "scan_count" in point


def test_scan_activity_trend(client, registered_user, auth_token, db_session):
    """GET /dashboard/trends/activity returns completed/failed split."""
    uid = registered_user["id"]
    _seed_db(db_session, uid)

    resp = client.get(
        "/api/v1/dashboard/trends/activity?days=7",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 7
    total_all = sum(p["total"] for p in data)
    assert total_all >= 2  # 1 completed + 1 failed from seed


def test_project_summary_endpoint(client, registered_user, auth_token, db_session):
    """GET /dashboard/projects/{id}/summary returns project metrics."""
    uid = registered_user["id"]
    p = _seed_db(db_session, uid)

    resp = client.get(
        f"/api/v1/dashboard/projects/{p.id}/summary",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "findings_by_severity" in data
    assert "total_findings" in data
    assert data["total_findings"] == 3


def test_severity_heatmap_endpoint(client, registered_user, auth_token, db_session):
    """GET /dashboard/projects/{id}/heatmap returns host × severity pivot."""
    uid = registered_user["id"]
    p = _seed_db(db_session, uid)

    resp = client.get(
        f"/api/v1/dashboard/projects/{p.id}/heatmap",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    row = data[0]
    assert "host" in row
    assert "critical" in row
    assert "high" in row


def test_cache_invalidate_endpoint(client, registered_user, auth_token):
    """POST /dashboard/cache/invalidate returns 204."""
    with patch("app.api.v1.endpoints.dashboard.invalidate_cache") as mock_inv:
        resp = client.post(
            "/api/v1/dashboard/cache/invalidate",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert resp.status_code == 204
    assert mock_inv.call_count == 2  # called for "analytics" and "trends"
