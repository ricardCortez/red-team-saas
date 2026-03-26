"""Unit tests for MetricsEngine."""
import pytest
from app.core.analytics.metrics import MetricsEngine
from app.models.user import User
from app.models.project import Project
from app.models.task import Task, TaskStatusEnum
from app.models.result import Result
from app.models.finding import Finding, Severity, FindingStatus
from app.models.report import Report, ReportType, ReportStatus


# ── Helpers ───────────────────────────────────────────────────────────────────

def _user(db, email="u@m.com", username="u1"):
    u = User(email=email, username=username, hashed_password="x", is_active=True)
    db.add(u); db.flush(); return u


def _project(db, owner_id):
    p = Project(owner_id=owner_id, name="P", target="10.0.0.0/8")
    db.add(p); db.flush(); return p


def _task(db, user_id, project_id=None, status=TaskStatusEnum.completed):
    t = Task(user_id=user_id, project_id=project_id, status=status)
    db.add(t); db.flush(); return t


def _result(db, task_id, tool_name="nmap", success=True, risk=5.0, dur=30.0):
    r = Result(
        task_id=task_id, tool_name=tool_name, target="10.0.0.1",
        success=success, risk_score=risk, duration_seconds=dur,
        parsed_output={}, findings=[],
    )
    db.add(r); db.flush(); return r


def _finding(db, task_id, project_id, sev=Severity.medium,
             host="10.0.0.1", status=FindingStatus.open, is_dup=False):
    import uuid
    f = Finding(
        task_id=task_id, project_id=project_id,
        title=f"F-{sev.value}", severity=sev,
        host=host, tool_name="nmap",
        fingerprint=str(uuid.uuid4())[:16],
        risk_score=5.0, is_duplicate=is_dup, status=status,
    )
    db.add(f); db.flush(); return f


def _report(db, project_id, user_id, status=ReportStatus.ready):
    r = Report(
        project_id=project_id, created_by=user_id,
        title="Report", report_type=ReportType.technical,
        status=status,
    )
    db.add(r); db.flush(); return r


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_global_summary_counts(db_session):
    u = _user(db_session)
    p = _project(db_session, u.id)
    t = _task(db_session, u.id, p.id)
    _finding(db_session, t.id, p.id, Severity.critical)
    _finding(db_session, t.id, p.id, Severity.high)
    _report(db_session, p.id, u.id, ReportStatus.ready)
    db_session.commit()

    s = MetricsEngine.global_summary(db_session, u.id)

    assert s["total_scans"] == 1
    assert s["total_findings"] == 2
    assert s["critical_findings"] == 1
    assert s["high_findings"] == 1
    assert s["total_reports"] == 1
    assert s["reports_ready"] == 1


def test_global_summary_running_scans(db_session):
    u = _user(db_session, "r@m.com", "u2")
    _task(db_session, u.id, status=TaskStatusEnum.running)
    _task(db_session, u.id, status=TaskStatusEnum.running)
    _task(db_session, u.id, status=TaskStatusEnum.completed)
    db_session.commit()

    s = MetricsEngine.global_summary(db_session, u.id)

    assert s["scans_running"] == 2
    assert s["scans_completed"] == 1
    assert s["total_scans"] == 3


def test_project_summary_by_severity(db_session):
    u = _user(db_session, "ps@m.com", "u3")
    p = _project(db_session, u.id)
    t = _task(db_session, u.id, p.id)
    _finding(db_session, t.id, p.id, Severity.critical)
    _finding(db_session, t.id, p.id, Severity.critical)
    _finding(db_session, t.id, p.id, Severity.high)
    db_session.commit()

    s = MetricsEngine.project_summary(db_session, p.id)

    assert s["findings_by_severity"]["critical"] == 2
    assert s["findings_by_severity"]["high"] == 1
    assert s["findings_by_severity"]["medium"] == 0
    assert s["total_findings"] == 3


def test_project_summary_excludes_false_positives(db_session):
    u = _user(db_session, "fp@m.com", "u4")
    p = _project(db_session, u.id)
    t = _task(db_session, u.id, p.id)
    _finding(db_session, t.id, p.id, Severity.high)
    _finding(db_session, t.id, p.id, Severity.high, status=FindingStatus.false_positive)
    db_session.commit()

    s = MetricsEngine.project_summary(db_session, p.id)

    # total_findings excludes duplicates but NOT FP (FP is a separate counter)
    # false_positives counter should be 1
    assert s["false_positives"] == 1
    # total_findings = non-duplicate findings (both are non-duplicate)
    assert s["total_findings"] == 2


def test_top_targets_ordered_by_count(db_session):
    u = _user(db_session, "tt@m.com", "u5")
    p = _project(db_session, u.id)
    t = _task(db_session, u.id, p.id)
    # host A: 3 findings, host B: 1 finding
    for _ in range(3):
        _finding(db_session, t.id, p.id, Severity.medium, host="10.0.0.1")
    _finding(db_session, t.id, p.id, Severity.medium, host="10.0.0.2")
    db_session.commit()

    results = MetricsEngine.top_targets(db_session, u.id)

    assert len(results) == 2
    assert results[0]["host"] == "10.0.0.1"
    assert results[0]["findings"] == 3
    assert results[1]["host"] == "10.0.0.2"
    assert results[1]["findings"] == 1


def test_top_targets_excludes_null_host(db_session):
    u = _user(db_session, "nh@m.com", "u6")
    p = _project(db_session, u.id)
    t = _task(db_session, u.id, p.id)
    _finding(db_session, t.id, p.id, Severity.high, host=None)
    _finding(db_session, t.id, p.id, Severity.high, host="10.0.0.1")
    db_session.commit()

    results = MetricsEngine.top_targets(db_session, u.id)

    assert len(results) == 1
    assert results[0]["host"] == "10.0.0.1"


def test_top_tools_success_rate(db_session):
    u = _user(db_session, "tl@m.com", "u7")
    t = _task(db_session, u.id)
    _result(db_session, t.id, tool_name="nmap", success=True)
    _result(db_session, t.id, tool_name="nmap", success=True)
    _result(db_session, t.id, tool_name="nmap", success=False)
    db_session.commit()

    results = MetricsEngine.top_tools(db_session, u.id)

    assert len(results) == 1
    nmap = results[0]
    assert nmap["tool"] == "nmap"
    assert nmap["total_runs"] == 3
    assert nmap["successful"] == 2


def test_severity_heatmap_pivot(db_session):
    u = _user(db_session, "hm@m.com", "u8")
    p = _project(db_session, u.id)
    t = _task(db_session, u.id, p.id)
    _finding(db_session, t.id, p.id, Severity.critical, host="10.0.0.1")
    _finding(db_session, t.id, p.id, Severity.high, host="10.0.0.1")
    _finding(db_session, t.id, p.id, Severity.medium, host="10.0.0.2")
    db_session.commit()

    rows = MetricsEngine.severity_heatmap(db_session, p.id)

    assert len(rows) == 2
    host1 = next(r for r in rows if r["host"] == "10.0.0.1")
    assert host1["critical"] == 1
    assert host1["high"] == 1
    host2 = next(r for r in rows if r["host"] == "10.0.0.2")
    assert host2["medium"] == 1
    assert host2["critical"] == 0
