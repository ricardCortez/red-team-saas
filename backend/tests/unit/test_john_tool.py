"""Unit tests for JohnTool"""
import pytest
from app.core.tool_definitions.john_tool import JohnTool
from app.core.tool_engine.tool_registry import ToolRegistry


class TestJohnToolRegistration:
    def test_registered_in_registry(self):
        assert "john" in ToolRegistry._tools

    def test_category_is_brute_force(self):
        tool = JohnTool()
        from app.core.tool_engine.base_tool import ToolCategory
        assert tool.category == ToolCategory.BRUTE_FORCE

    def test_name(self):
        assert JohnTool.name == "john"


class TestJohnToolValidateTarget:
    def setup_method(self):
        self.tool = JohnTool()

    def test_valid_file_path(self):
        assert self.tool.validate_target("/tmp/hashes.txt") is True

    def test_valid_hash_string(self):
        assert self.tool.validate_target("5f4dcc3b5aa765d61d8327deb882cf99") is True

    def test_empty_string_invalid(self):
        assert self.tool.validate_target("") is False

    def test_whitespace_invalid(self):
        assert self.tool.validate_target("   ") is False


class TestJohnToolBuildCommand:
    def setup_method(self):
        self.tool = JohnTool()

    def test_wordlist_mode_default(self):
        cmd = self.tool.build_command("/tmp/hashes.txt", {})
        assert "john" in cmd
        assert any("--wordlist" in c for c in cmd)
        assert "/tmp/hashes.txt" in cmd

    def test_custom_wordlist(self):
        cmd = self.tool.build_command("/tmp/hashes.txt", {"wordlist": "/tmp/custom.txt"})
        assert "--wordlist=/tmp/custom.txt" in cmd

    def test_incremental_mode(self):
        cmd = self.tool.build_command("/tmp/hashes.txt", {"mode": "incremental"})
        assert any("--incremental" in c for c in cmd)

    def test_single_mode(self):
        cmd = self.tool.build_command("/tmp/hashes.txt", {"mode": "single"})
        assert "--single" in cmd

    def test_mask_mode(self):
        cmd = self.tool.build_command("/tmp/hashes.txt", {"mode": "mask", "mask": "?d?d?d?d"})
        assert "--mask=?d?d?d?d" in cmd

    def test_invalid_mode_defaults_to_wordlist(self):
        cmd = self.tool.build_command("/tmp/hashes.txt", {"mode": "unknown"})
        assert any("--wordlist" in c for c in cmd)

    def test_format_flag(self):
        cmd = self.tool.build_command("/tmp/hashes.txt", {"format": "md5"})
        assert "--format=md5" in cmd

    def test_min_max_length(self):
        cmd = self.tool.build_command("/tmp/hashes.txt", {"min_length": 6, "max_length": 12})
        assert "--min-length=6" in cmd
        assert "--max-length=12" in cmd

    def test_fork_flag(self):
        cmd = self.tool.build_command("/tmp/hashes.txt", {"fork": 4})
        assert "--fork=4" in cmd

    def test_rules_in_wordlist_mode(self):
        cmd = self.tool.build_command("/tmp/hashes.txt", {"mode": "wordlist", "rules": "best64"})
        assert "--rules=best64" in cmd


class TestJohnToolParseOutput:
    def setup_method(self):
        self.tool = JohnTool()

    def test_parse_cracked_password(self):
        output = "password123     (admin)"
        result = self.tool.parse_output(output, 0)
        assert result["total_cracked"] == 1
        assert result["cracked"][0]["password"] == "password123"

    def test_parse_no_cracked(self):
        output = "No password hashes loaded\nSession completed"
        result = self.tool.parse_output(output, 1)
        assert result["total_cracked"] == 0

    def test_findings_severity_high(self):
        output = "secret     (john)"
        result = self.tool.parse_output(output, 0)
        if result["total_cracked"] > 0:
            assert result["findings"][0]["severity"] == "high"


class TestJohnToolRiskScore:
    def setup_method(self):
        self.tool = JohnTool()

    def test_zero_cracked(self):
        assert self.tool.get_risk_score({"total_cracked": 0}) == 0.0

    def test_one_cracked(self):
        assert self.tool.get_risk_score({"total_cracked": 1}) == 6.0

    def test_few_cracked(self):
        assert self.tool.get_risk_score({"total_cracked": 5}) == 8.0

    def test_many_cracked(self):
        assert self.tool.get_risk_score({"total_cracked": 15}) == 10.0
