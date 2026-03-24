"""Unit tests for app.crud.finding (Phase 5)"""
import pytest

from app.crud.finding import crud_finding
from app.models.finding import Finding, Severity, FindingStatus
from app.schemas.finding import FindingFilter, FindingUpdate


def _create_finding(db, **kwargs) -> Finding:
    defaults = dict(
        title="Test Finding",
        severity=Severity.high,
        status=FindingStatus.open,
        host="10.0.0.1",
        tool_name="nmap",
        fingerprint="abc123def456abcd",
        is_duplicate=False,
        risk_score=5.0,
        project_id=1,
        result_id=None,
        task_id=None,
    )
    defaults.update(kwargs)
    f = Finding(**defaults)
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


class TestGetMultiFiltered:

    def test_filter_by_severity(self, db_session):
        _create_finding(db_session, title="Critical One", severity=Severity.critical, fingerprint="fp1")
        _create_finding(db_session, title="Low One", severity=Severity.low, fingerprint="fp2")
        filters = FindingFilter(severity=Severity.critical)
        items, total = crud_finding.get_multi_filtered(db_session, filters=filters)
        assert total == 1
        assert items[0].title == "Critical One"

    def test_filter_by_status(self, db_session):
        _create_finding(db_session, title="Open", status=FindingStatus.open, fingerprint="fp1")
        _create_finding(db_session, title="Resolved", status=FindingStatus.resolved, fingerprint="fp2")
        filters = FindingFilter(status=FindingStatus.resolved)
        items, total = crud_finding.get_multi_filtered(db_session, filters=filters)
        assert total == 1
        assert items[0].title == "Resolved"

    def test_filter_exclude_duplicates_default(self, db_session):
        _create_finding(db_session, title="Original", is_duplicate=False, fingerprint="fp1")
        _create_finding(db_session, title="Dup", is_duplicate=True, fingerprint="fp1")
        # Default excludes duplicates
        filters = FindingFilter()
        items, total = crud_finding.get_multi_filtered(db_session, filters=filters)
        assert total == 1
        assert items[0].title == "Original"

    def test_filter_include_duplicates(self, db_session):
        _create_finding(db_session, title="Original", is_duplicate=False, fingerprint="fp1")
        _create_finding(db_session, title="Dup", is_duplicate=True, fingerprint="fp1")
        filters = FindingFilter(exclude_duplicates=False)
        _, total = crud_finding.get_multi_filtered(db_session, filters=filters)
        assert total == 2

    def test_filter_by_host(self, db_session):
        _create_finding(db_session, host="192.168.1.1", fingerprint="fp1")
        _create_finding(db_session, host="10.0.0.1", fingerprint="fp2")
        filters = FindingFilter(host="192.168")
        items, total = crud_finding.get_multi_filtered(db_session, filters=filters)
        assert total == 1
        assert "192.168" in items[0].host

    def test_filter_by_tool_name(self, db_session):
        _create_finding(db_session, tool_name="nmap", fingerprint="fp1")
        _create_finding(db_session, tool_name="nikto", fingerprint="fp2")
        filters = FindingFilter(tool_name="nmap")
        items, total = crud_finding.get_multi_filtered(db_session, filters=filters)
        assert total == 1
        assert items[0].tool_name == "nmap"

    def test_filter_by_min_risk_score(self, db_session):
        _create_finding(db_session, risk_score=2.0, fingerprint="fp1")
        _create_finding(db_session, risk_score=8.0, fingerprint="fp2")
        filters = FindingFilter(min_risk_score=5.0)
        items, total = crud_finding.get_multi_filtered(db_session, filters=filters)
        assert total == 1
        assert items[0].risk_score == 8.0

    def test_filter_by_project_id(self, db_session):
        _create_finding(db_session, project_id=1, fingerprint="fp1")
        _create_finding(db_session, project_id=2, fingerprint="fp2")
        filters = FindingFilter(project_id=1)
        items, total = crud_finding.get_multi_filtered(db_session, filters=filters)
        assert total == 1

    def test_pagination(self, db_session):
        for i in range(5):
            _create_finding(db_session, title=f"Finding {i}", fingerprint=f"fp{i}")
        _, total = crud_finding.get_multi_filtered(db_session, filters=FindingFilter(), limit=100)
        assert total == 5
        items, _ = crud_finding.get_multi_filtered(db_session, filters=FindingFilter(), skip=0, limit=2)
        assert len(items) == 2


class TestUpdateStatus:

    def test_update_status(self, db_session):
        f = _create_finding(db_session, status=FindingStatus.open, fingerprint="fp1")
        update = FindingUpdate(status=FindingStatus.confirmed)
        updated = crud_finding.update_status(db_session, f.id, update, user_id=1)
        assert updated.status == FindingStatus.confirmed

    def test_update_severity(self, db_session):
        f = _create_finding(db_session, severity=Severity.low, fingerprint="fp1")
        update = FindingUpdate(severity=Severity.critical)
        updated = crud_finding.update_status(db_session, f.id, update, user_id=1)
        assert updated.severity == Severity.critical

    def test_update_notes(self, db_session):
        f = _create_finding(db_session, fingerprint="fp1")
        update = FindingUpdate(notes="Needs immediate attention")
        updated = crud_finding.update_status(db_session, f.id, update, user_id=1)
        assert updated.notes == "Needs immediate attention"

    def test_mark_false_positive_sets_status(self, db_session):
        f = _create_finding(db_session, fingerprint="fp1")
        update = FindingUpdate(
            status=FindingStatus.false_positive,
            false_positive_reason="Confirmed safe in staging env",
        )
        updated = crud_finding.update_status(db_session, f.id, update, user_id=1)
        assert updated.status == FindingStatus.false_positive
        assert updated.false_positive is True
        assert updated.false_positive_reason == "Confirmed safe in staging env"

    def test_not_found_raises_value_error(self, db_session):
        with pytest.raises(ValueError, match="999"):
            crud_finding.update_status(db_session, 999, FindingUpdate(), user_id=1)


class TestGetStatsBySeverity:

    def test_stats_by_severity(self, db_session):
        _create_finding(db_session, severity=Severity.critical, fingerprint="fp1", project_id=10)
        _create_finding(db_session, severity=Severity.critical, fingerprint="fp2", project_id=10)
        _create_finding(db_session, severity=Severity.high, fingerprint="fp3", project_id=10)
        stats = crud_finding.get_stats_by_severity(db_session, project_id=10)
        assert stats.get("critical") == 2
        assert stats.get("high") == 1

    def test_excludes_false_positives(self, db_session):
        _create_finding(db_session, severity=Severity.high, fingerprint="fp1", project_id=20)
        _create_finding(
            db_session, severity=Severity.high, fingerprint="fp2", project_id=20,
            status=FindingStatus.false_positive,
        )
        stats = crud_finding.get_stats_by_severity(db_session, project_id=20)
        assert stats.get("high", 0) == 1

    def test_excludes_duplicates_in_stats(self, db_session):
        _create_finding(db_session, severity=Severity.medium, fingerprint="fp1", project_id=30, is_duplicate=False)
        _create_finding(db_session, severity=Severity.medium, fingerprint="fp1", project_id=30, is_duplicate=True)
        stats = crud_finding.get_stats_by_severity(db_session, project_id=30)
        assert stats.get("medium", 0) == 1
