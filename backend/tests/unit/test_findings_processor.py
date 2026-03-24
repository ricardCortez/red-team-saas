"""Unit tests for app.core.findings_processor (Phase 5)"""
import pytest
from unittest.mock import MagicMock, patch

from app.core.findings_processor import compute_fingerprint, process_result_findings
from app.models.finding import Finding, Severity, FindingStatus


# ── compute_fingerprint ────────────────────────────────────────────────────────

class TestComputeFingerprint:

    def test_consistent_same_inputs(self):
        fp1 = compute_fingerprint("SQL Injection", "192.168.1.1", 80)
        fp2 = compute_fingerprint("SQL Injection", "192.168.1.1", 80)
        assert fp1 == fp2

    def test_16_char_hex(self):
        fp = compute_fingerprint("XSS", "example.com")
        assert len(fp) == 16
        assert all(c in "0123456789abcdef" for c in fp)

    def test_case_insensitive_title(self):
        fp1 = compute_fingerprint("SQL Injection", "host.com")
        fp2 = compute_fingerprint("sql injection", "host.com")
        assert fp1 == fp2

    def test_different_hosts_differ(self):
        fp1 = compute_fingerprint("Open Port", "10.0.0.1")
        fp2 = compute_fingerprint("Open Port", "10.0.0.2")
        assert fp1 != fp2

    def test_different_ports_differ(self):
        fp1 = compute_fingerprint("Service", "host.com", 80)
        fp2 = compute_fingerprint("Service", "host.com", 443)
        assert fp1 != fp2

    def test_none_port_handled(self):
        fp = compute_fingerprint("Finding", "host.com", None)
        assert len(fp) == 16


# ── process_result_findings ────────────────────────────────────────────────────

def _make_result(findings=None, task_project_id=None, result_id=1, task_id=1):
    """Build a mock Result with minimal attributes."""
    task = MagicMock()
    task.project_id = task_project_id

    result = MagicMock()
    result.id = result_id
    result.task_id = task_id
    result.task = task
    result.target = "192.168.1.100"
    result.tool_name = "nmap"
    result.tool = "nmap"
    result.findings = findings or []
    return result


class TestProcessResultFindings:

    def test_empty_findings_returns_empty(self, db_session):
        result = _make_result(findings=[])
        created = process_result_findings(db_session, result)
        assert created == []

    def test_creates_finding_rows(self, db_session):
        findings_data = [
            {"title": "Open SSH", "severity": "high", "host": "10.0.0.1", "port": 22},
            {"title": "HTTP Info", "severity": "info", "host": "10.0.0.1", "port": 80},
        ]
        result = _make_result(findings=findings_data)
        created = process_result_findings(db_session, result)
        assert len(created) == 2
        # Rows actually persisted
        assert db_session.query(Finding).count() == 2

    def test_severity_mapping(self, db_session):
        findings_data = [
            {"title": "Critical Bug", "severity": "CRITICAL", "host": "host.com"},
        ]
        result = _make_result(findings=findings_data)
        created = process_result_findings(db_session, result)
        assert created[0].severity == Severity.critical

    def test_unknown_severity_defaults_to_info(self, db_session):
        findings_data = [{"title": "Weird", "severity": "unknown_xyz", "host": "h.com"}]
        result = _make_result(findings=findings_data)
        created = process_result_findings(db_session, result)
        assert created[0].severity == Severity.info

    def test_fingerprint_is_set(self, db_session):
        findings_data = [{"title": "XSS", "severity": "medium", "host": "example.com"}]
        result = _make_result(findings=findings_data)
        created = process_result_findings(db_session, result)
        assert created[0].fingerprint is not None
        assert len(created[0].fingerprint) == 16

    def test_duplicate_detection_same_project(self, db_session):
        """Second call with same fingerprint/project marks it as duplicate."""
        project_id = 42
        findings_data = [{"title": "SQL Injection", "severity": "high", "host": "app.com"}]

        # First result
        result1 = _make_result(findings=findings_data, task_project_id=project_id, result_id=1, task_id=1)
        created1 = process_result_findings(db_session, result1)
        assert created1[0].is_duplicate is False

        # Second result, same project, same finding
        result2 = _make_result(findings=findings_data, task_project_id=project_id, result_id=2, task_id=2)
        created2 = process_result_findings(db_session, result2)
        assert created2[0].is_duplicate is True
        assert created2[0].duplicate_of == created1[0].id

    def test_no_duplicate_without_project(self, db_session):
        """Without project_id, duplicate detection is skipped."""
        findings_data = [{"title": "Open Port", "severity": "low", "host": "server.com"}]
        result1 = _make_result(findings=findings_data, task_project_id=None, result_id=1)
        result2 = _make_result(findings=findings_data, task_project_id=None, result_id=2)
        created1 = process_result_findings(db_session, result1)
        created2 = process_result_findings(db_session, result2)
        assert created1[0].is_duplicate is False
        assert created2[0].is_duplicate is False

    def test_uses_result_target_as_default_host(self, db_session):
        """If 'host' is missing from finding JSON, result.target is used."""
        findings_data = [{"title": "No Host", "severity": "low"}]
        result = _make_result(findings=findings_data)
        result.target = "fallback.host"
        created = process_result_findings(db_session, result)
        assert created[0].host == "fallback.host"

    def test_status_defaults_to_open(self, db_session):
        findings_data = [{"title": "Finding", "severity": "medium", "host": "h.com"}]
        result = _make_result(findings=findings_data)
        created = process_result_findings(db_session, result)
        assert created[0].status == FindingStatus.open
