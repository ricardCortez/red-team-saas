"""Unit tests for TrendsEngine."""
import pytest
from datetime import datetime, timedelta
from app.core.analytics.trends import TrendsEngine
from app.models.user import User
from app.models.project import Project
from app.models.task import Task, TaskStatusEnum
from app.models.result import Result
from app.models.finding import Finding, Severity, FindingStatus


# ── Helpers ───────────────────────────────────────────────────────────────────

def _user(db, email="tr@m.com", username="tr1"):
    u = User(email=email, username=username, hashed_password="x", is_active=True)
    db.add(u); db.flush(); return u


def _project(db, owner_id):
    p = Project(owner_id=owner_id, name="TP", target="10.0.0.0/8")
    db.add(p); db.flush(); return p


def _task(db, user_id, project_id=None, status=TaskStatusEnum.completed):
    t = Task(user_id=user_id, project_id=project_id, status=status)
    db.add(t); db.flush(); return t


def _result(db, task_id, success=True, risk=4.0):
    r = Result(
        task_id=task_id, tool_name="nmap", target="10.0.0.1",
        success=success, risk_score=risk, duration_seconds=10.0,
        parsed_output={}, findings=[],
    )
    db.add(r); db.flush(); return r


def _finding(db, task_id, project_id, sev=Severity.medium, created_at=None):
    import uuid
    f = Finding(
        task_id=task_id, project_id=project_id,
        title="F", severity=sev,
        host="10.0.0.1", tool_name="nmap",
        fingerprint=str(uuid.uuid4())[:16],
        risk_score=3.0, is_duplicate=False,
    )
    db.add(f)
    db.flush()
    if created_at:
        # Override timestamp after flush
        f.created_at = created_at
        db.flush()
    return f


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_findings_over_time_fills_missing_days(db_session):
    """Result always has exactly `days` entries, even with no data."""
    u = _user(db_session)
    db_session.commit()

    result = TrendsEngine.findings_over_time(db_session, u.id, days=7)

    assert len(result) == 7
    for point in result:
        assert "date" in point
        assert point["total"] == 0
        assert point["critical"] == 0


def test_findings_over_time_filters_by_project(db_session):
    """project_id filter limits findings to that project."""
    u = _user(db_session, "fp2@m.com", "tr2")
    p1 = _project(db_session, u.id)
    p2 = _project(db_session, u.id)
    t1 = _task(db_session, u.id, p1.id)
    t2 = _task(db_session, u.id, p2.id)
    _finding(db_session, t1.id, p1.id, Severity.high)
    _finding(db_session, t2.id, p2.id, Severity.critical)
    db_session.commit()

    result_p1 = TrendsEngine.findings_over_time(db_session, u.id, days=7, project_id=p1.id)
    result_p2 = TrendsEngine.findings_over_time(db_session, u.id, days=7, project_id=p2.id)

    total_p1 = sum(r["total"] for r in result_p1)
    total_p2 = sum(r["total"] for r in result_p2)
    assert total_p1 == 1
    assert total_p2 == 1


def test_risk_score_trend_only_successful_scans(db_session):
    """Failed scans are excluded from risk score trend."""
    u = _user(db_session, "rs@m.com", "tr3")
    t = _task(db_session, u.id)
    _result(db_session, t.id, success=True, risk=8.0)
    _result(db_session, t.id, success=False, risk=99.0)  # must be excluded
    db_session.commit()

    result = TrendsEngine.risk_score_trend(db_session, u.id, days=7)

    total_count = sum(r["scan_count"] for r in result)
    assert total_count == 1  # only successful scan counted

    max_risk = max(r["max_risk"] for r in result)
    assert max_risk == pytest.approx(8.0, abs=0.1)


def test_risk_score_trend_fills_zero_days(db_session):
    """Trend always returns exactly `days` entries."""
    u = _user(db_session, "rz@m.com", "tr4")
    db_session.commit()

    result = TrendsEngine.risk_score_trend(db_session, u.id, days=14)

    assert len(result) == 14
    for point in result:
        assert point["avg_risk"] == 0.0
        assert point["max_risk"] == 0.0
        assert point["scan_count"] == 0


def test_scan_activity_completed_failed_split(db_session):
    """Completed and failed task counts are split correctly."""
    u = _user(db_session, "sa@m.com", "tr5")
    _task(db_session, u.id, status=TaskStatusEnum.completed)
    _task(db_session, u.id, status=TaskStatusEnum.completed)
    _task(db_session, u.id, status=TaskStatusEnum.failed)
    db_session.commit()

    result = TrendsEngine.scan_activity(db_session, u.id, days=7)

    assert len(result) == 7
    total_completed = sum(r["completed"] for r in result)
    total_failed = sum(r["failed"] for r in result)
    total_all = sum(r["total"] for r in result)
    assert total_completed == 2
    assert total_failed == 1
    assert total_all == 3


def test_trends_respects_days_param(db_session):
    """The `days` parameter controls the number of returned data points."""
    u = _user(db_session, "dp@m.com", "tr6")
    db_session.commit()

    for days in (7, 30, 90):
        result = TrendsEngine.scan_activity(db_session, u.id, days=days)
        assert len(result) == days
