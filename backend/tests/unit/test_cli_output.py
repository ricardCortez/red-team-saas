"""Unit tests for cli/output.py"""
import pytest
from io import StringIO
from rich.text import Text


class TestSeverityText:
    def test_critical_is_bold_red(self):
        from cli.output import severity_text
        t = severity_text("critical")
        assert isinstance(t, Text)
        assert "critical" in str(t).lower() or "CRITICAL" in str(t)
        assert "red" in t.style

    def test_high_is_red(self):
        from cli.output import severity_text
        t = severity_text("high")
        assert t.style == "red"

    def test_medium_is_yellow(self):
        from cli.output import severity_text
        t = severity_text("medium")
        assert t.style == "yellow"

    def test_low_is_green(self):
        from cli.output import severity_text
        t = severity_text("low")
        assert t.style == "green"

    def test_info_is_blue(self):
        from cli.output import severity_text
        t = severity_text("info")
        assert t.style == "blue"

    def test_unknown_severity_defaults_to_white(self):
        from cli.output import severity_text
        t = severity_text("unknown_sev")
        assert t.style == "white"

    def test_case_insensitive(self):
        from cli.output import severity_text
        t = severity_text("CRITICAL")
        assert "red" in t.style


class TestStatusText:
    def test_running_is_cyan(self):
        from cli.output import status_text
        t = status_text("running")
        assert t.style == "cyan"

    def test_completed_is_green(self):
        from cli.output import status_text
        t = status_text("completed")
        assert t.style == "green"

    def test_failed_is_red(self):
        from cli.output import status_text
        t = status_text("failed")
        assert t.style == "red"

    def test_pending_is_yellow(self):
        from cli.output import status_text
        t = status_text("pending")
        assert t.style == "yellow"

    def test_unknown_status_defaults_to_white(self):
        from cli.output import status_text
        t = status_text("whatever")
        assert t.style == "white"


class TestPrintJSON:
    def test_print_json_outputs_valid_json(self, capsys):
        from cli.output import print_json
        print_json({"key": "value", "num": 42})
        captured = capsys.readouterr()
        import json
        parsed = json.loads(captured.out)
        assert parsed["key"] == "value"
        assert parsed["num"] == 42

    def test_print_json_handles_none_values(self, capsys):
        from cli.output import print_json
        print_json({"value": None})
        captured = capsys.readouterr()
        assert "null" in captured.out


class TestPrintFindings:
    def test_print_findings_json_format(self, capsys):
        from cli.output import print_findings
        findings = [{"id": 1, "severity": "high", "title": "XSS", "host": "10.0.0.1",
                     "tool_name": "nmap", "risk_score": 7.5}]
        print_findings(findings, fmt="json")
        captured = capsys.readouterr()
        import json
        data = json.loads(captured.out)
        assert data[0]["id"] == 1

    def test_print_findings_table_format_no_error(self):
        from cli.output import print_findings
        findings = [{"id": 1, "severity": "critical", "title": "RCE",
                     "host": "192.168.1.1", "tool_name": "metasploit", "risk_score": 10}]
        # Should not raise
        print_findings(findings, fmt="table")

    def test_print_findings_empty_list(self):
        from cli.output import print_findings
        print_findings([], fmt="table")


class TestPrintProjects:
    def test_print_projects_json_format(self, capsys):
        from cli.output import print_projects
        projects = [{"id": 1, "name": "Test Project", "status": "active",
                     "member_count": 3, "target_count": 5, "created_at": "2024-01-01T00:00:00"}]
        print_projects(projects, fmt="json")
        captured = capsys.readouterr()
        import json
        data = json.loads(captured.out)
        assert data[0]["name"] == "Test Project"

    def test_print_projects_table_format_no_error(self):
        from cli.output import print_projects
        projects = [{"id": 1, "name": "Test", "status": "active",
                     "member_count": 1, "target_count": 2, "created_at": "2024-01-01"}]
        print_projects(projects, fmt="table")

    def test_print_projects_handles_missing_created_at(self):
        from cli.output import print_projects
        projects = [{"id": 1, "name": "Test", "status": "active",
                     "member_count": 0, "target_count": 0}]
        # Should not raise
        print_projects(projects, fmt="table")
