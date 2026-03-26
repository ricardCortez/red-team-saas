"""Unit tests for CeWLTool"""
import pytest
from app.core.tool_definitions.cewl_tool import CeWLTool
from app.core.tool_engine.tool_registry import ToolRegistry


class TestCeWLToolRegistration:
    def test_registered_in_registry(self):
        assert "cewl" in ToolRegistry._tools

    def test_category_is_brute_force(self):
        tool = CeWLTool()
        from app.core.tool_engine.base_tool import ToolCategory
        assert tool.category == ToolCategory.BRUTE_FORCE

    def test_name(self):
        assert CeWLTool.name == "cewl"


class TestCeWLToolValidateTarget:
    def setup_method(self):
        self.tool = CeWLTool()

    def test_valid_http_url(self):
        assert self.tool.validate_target("http://example.com") is True

    def test_valid_https_url(self):
        assert self.tool.validate_target("https://example.com") is True

    def test_ip_address_invalid(self):
        assert self.tool.validate_target("192.168.1.1") is False

    def test_hostname_without_scheme_invalid(self):
        assert self.tool.validate_target("example.com") is False


class TestCeWLToolBuildCommand:
    def setup_method(self):
        self.tool = CeWLTool()

    def test_default_command(self):
        cmd = self.tool.build_command("http://example.com", {})
        assert "cewl" in cmd
        assert "http://example.com" in cmd
        assert "-d" in cmd
        assert "-m" in cmd

    def test_depth_option(self):
        cmd = self.tool.build_command("http://example.com", {"depth": 5})
        idx = cmd.index("-d")
        assert cmd[idx + 1] == "5"

    def test_min_length_option(self):
        cmd = self.tool.build_command("http://example.com", {"min_length": 8})
        idx = cmd.index("-m")
        assert cmd[idx + 1] == "8"

    def test_with_numbers(self):
        cmd = self.tool.build_command("http://example.com", {"with_numbers": True})
        assert "-n" in cmd

    def test_without_numbers(self):
        cmd = self.tool.build_command("http://example.com", {"with_numbers": False})
        assert "-n" not in cmd

    def test_with_emails(self):
        cmd = self.tool.build_command("http://example.com", {"with_emails": True})
        assert "-e" in cmd

    def test_output_file(self):
        cmd = self.tool.build_command("http://example.com", {"output_file": "/tmp/words.txt"})
        assert "-w" in cmd
        assert "/tmp/words.txt" in cmd

    def test_lowercase_default(self):
        cmd = self.tool.build_command("http://example.com", {})
        assert "--lowercase" in cmd

    def test_user_agent(self):
        cmd = self.tool.build_command("http://example.com", {"user_agent": "Mozilla/5.0"})
        assert "-a" in cmd


class TestCeWLToolParseOutput:
    def setup_method(self):
        self.tool = CeWLTool()

    def test_parse_words(self):
        output = "password\nadministrator\nnetwork\nsecurity\nlogin"
        result = self.tool.parse_output(output, 0)
        assert result["total_words"] == 5
        assert "password" in result["words"]
        assert "administrator" in result["words"]

    def test_parse_empty_output(self):
        result = self.tool.parse_output("", 0)
        assert result["total_words"] == 0
        assert result["words"] == []

    def test_skip_cewl_header_lines(self):
        output = "CeWL 5.5.2 (Grouping) Robin Wood (robin@digi.ninja)\npassword\nlogin"
        result = self.tool.parse_output(output, 0)
        assert "password" in result["words"]
        assert not any("CeWL" in w for w in result["words"])

    def test_strip_count_notation(self):
        output = "password, 42\nadministrator, 15"
        result = self.tool.parse_output(output, 0)
        assert "password" in result["words"]
        assert "administrator" in result["words"]

    def test_finding_created_when_words_found(self):
        output = "secret\npassword\nlogin"
        result = self.tool.parse_output(output, 0)
        assert len(result["findings"]) > 0


class TestCeWLToolRiskScore:
    def setup_method(self):
        self.tool = CeWLTool()

    def test_no_words_zero_score(self):
        assert self.tool.get_risk_score({"total_words": 0}) == 0.0

    def test_few_words_low_score(self):
        assert self.tool.get_risk_score({"total_words": 50}) == 1.0

    def test_many_words_medium_score(self):
        assert self.tool.get_risk_score({"total_words": 200}) == 3.0
