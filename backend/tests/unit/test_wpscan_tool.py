"""Unit tests for WPScanTool"""
import json
import pytest
from app.core.tool_definitions.wpscan_tool import WPScanTool
from app.core.tool_engine.tool_registry import ToolRegistry


class TestWPScanToolRegistration:
    def test_registered_in_registry(self):
        assert "wpscan" in ToolRegistry._tools

    def test_category_is_brute_force(self):
        tool = WPScanTool()
        from app.core.tool_engine.base_tool import ToolCategory
        assert tool.category == ToolCategory.BRUTE_FORCE

    def test_name(self):
        assert WPScanTool.name == "wpscan"


class TestWPScanToolValidateTarget:
    def setup_method(self):
        self.tool = WPScanTool()

    def test_valid_http_url(self):
        assert self.tool.validate_target("http://wp.example.com") is True

    def test_valid_https_url(self):
        assert self.tool.validate_target("https://blog.example.com") is True

    def test_ip_without_scheme_invalid(self):
        assert self.tool.validate_target("192.168.1.1") is False


class TestWPScanToolBuildCommand:
    def setup_method(self):
        self.tool = WPScanTool()

    def test_default_command(self):
        cmd = self.tool.build_command("http://wp.example.com", {})
        assert "wpscan" in cmd
        assert "--url" in cmd
        assert "http://wp.example.com" in cmd
        assert "--format" in cmd
        assert "json" in cmd

    def test_passive_scan_type(self):
        cmd = self.tool.build_command("http://wp.example.com", {"scan_type": "passive"})
        assert "--detection-mode" in cmd
        idx = cmd.index("--detection-mode")
        assert cmd[idx + 1] == "passive"

    def test_aggressive_scan_type(self):
        cmd = self.tool.build_command("http://wp.example.com", {"scan_type": "aggressive"})
        idx = cmd.index("--detection-mode")
        assert cmd[idx + 1] == "aggressive"

    def test_brute_scan_type_with_credentials(self):
        cmd = self.tool.build_command("http://wp.example.com", {
            "scan_type": "brute",
            "username": "admin",
            "passlist": "/tmp/pass.txt",
        })
        assert "--usernames" in cmd
        assert "--passwords" in cmd

    def test_invalid_scan_type_defaults_to_mixed(self):
        cmd = self.tool.build_command("http://wp.example.com", {"scan_type": "invalid"})
        idx = cmd.index("--detection-mode")
        assert cmd[idx + 1] == "mixed"

    def test_api_token(self):
        cmd = self.tool.build_command("http://wp.example.com", {"api_token": "abc123"})
        assert "--api-token" in cmd
        idx = cmd.index("--api-token")
        assert cmd[idx + 1] == "abc123"

    def test_throttle_option(self):
        cmd = self.tool.build_command("http://wp.example.com", {"throttle": 500})
        assert "--throttle" in cmd

    def test_enumerate_users_default(self):
        cmd = self.tool.build_command("http://wp.example.com", {})
        assert "--enumerate" in cmd

    def test_all_scan_types_valid(self):
        for scan_type in WPScanTool.SCAN_TYPES:
            cmd = self.tool.build_command("http://wp.example.com", {"scan_type": scan_type})
            assert "wpscan" in cmd


class TestWPScanToolParseOutput:
    def setup_method(self):
        self.tool = WPScanTool()

    def test_parse_empty_output(self):
        result = self.tool.parse_output("", 0)
        assert result["is_wordpress"] is False

    def test_parse_invalid_json(self):
        result = self.tool.parse_output("not json output", 1)
        assert result["is_wordpress"] is False

    def test_parse_version(self):
        data = {"version": {"number": "5.9.1", "vulnerabilities": []}}
        result = self.tool.parse_output(json.dumps(data), 0)
        assert result["version"] == "5.9.1"
        assert result["is_wordpress"] is True

    def test_parse_version_vulnerabilities(self):
        data = {
            "version": {
                "number": "5.8.0",
                "vulnerabilities": [
                    {
                        "title": "XSS in post title",
                        "cvss": {"score": 6.1},
                        "references": {},
                    }
                ],
            }
        }
        result = self.tool.parse_output(json.dumps(data), 0)
        assert len(result["vulnerabilities"]) == 1
        assert len(result["findings"]) >= 1

    def test_parse_users(self):
        data = {"users": {"admin": {"id": 1}, "editor": {"id": 2}}}
        result = self.tool.parse_output(json.dumps(data), 0)
        assert "admin" in result["users"]
        assert "editor" in result["users"]

    def test_parse_plugins(self):
        data = {
            "plugins": {
                "contact-form-7": {
                    "version": {"number": "5.5.6"},
                    "vulnerabilities": [{"title": "SQL Injection"}],
                }
            }
        }
        result = self.tool.parse_output(json.dumps(data), 0)
        assert len(result["plugins"]) == 1
        assert result["plugins"][0]["slug"] == "contact-form-7"

    def test_parse_credentials(self):
        data = {
            "passwords": [
                {"username": "admin", "password": "password123"},
            ]
        }
        result = self.tool.parse_output(json.dumps(data), 0)
        assert len(result["credentials"]) == 1
        assert result["credentials"][0]["username"] == "admin"


class TestWPScanToolRiskScore:
    def setup_method(self):
        self.tool = WPScanTool()

    def test_no_findings_zero_score(self):
        parsed = {"credentials": [], "vulnerabilities": [], "users": [], "plugins": []}
        assert self.tool.get_risk_score(parsed) == 0.0

    def test_credentials_found_max_score(self):
        parsed = {"credentials": [{"username": "admin", "password": "test"}],
                  "vulnerabilities": [], "users": [], "plugins": []}
        assert self.tool.get_risk_score(parsed) == 10.0

    def test_vulnerabilities_high_score(self):
        parsed = {"credentials": [], "vulnerabilities": [{"title": "XSS"}],
                  "users": [], "plugins": []}
        assert self.tool.get_risk_score(parsed) == 7.0

    def test_users_enumerated_medium_score(self):
        parsed = {"credentials": [], "vulnerabilities": [],
                  "users": ["admin"], "plugins": []}
        assert self.tool.get_risk_score(parsed) == 4.0
