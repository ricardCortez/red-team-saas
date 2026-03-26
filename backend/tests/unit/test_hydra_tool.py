"""Unit tests for HydraTool"""
import pytest
from app.core.tool_definitions.hydra_tool import HydraTool
from app.core.tool_engine.tool_registry import ToolRegistry


class TestHydraToolRegistration:
    def test_registered_in_registry(self):
        assert "hydra" in ToolRegistry._tools

    def test_category_is_brute_force(self):
        tool = HydraTool()
        from app.core.tool_engine.base_tool import ToolCategory
        assert tool.category == ToolCategory.BRUTE_FORCE

    def test_name(self):
        assert HydraTool.name == "hydra"

    def test_binary(self):
        assert HydraTool.binary == "hydra"


class TestHydraToolBuildCommand:
    def setup_method(self):
        self.tool = HydraTool()

    def test_default_ssh_command(self):
        cmd = self.tool.build_command("192.168.1.1", {})
        assert "hydra" in cmd
        assert "192.168.1.1" in cmd
        assert "ssh" in cmd

    def test_protocol_selection(self):
        cmd = self.tool.build_command("192.168.1.1", {"protocol": "ftp"})
        assert "ftp" in cmd

    def test_invalid_protocol_defaults_to_ssh(self):
        cmd = self.tool.build_command("192.168.1.1", {"protocol": "invalid_proto"})
        assert "ssh" in cmd

    def test_username_flag(self):
        cmd = self.tool.build_command("192.168.1.1", {"username": "admin"})
        assert "-l" in cmd
        assert "admin" in cmd

    def test_userlist_flag(self):
        cmd = self.tool.build_command("192.168.1.1", {"userlist": "/tmp/users.txt"})
        assert "-L" in cmd
        assert "/tmp/users.txt" in cmd

    def test_password_flag(self):
        cmd = self.tool.build_command("192.168.1.1", {"password": "pass123"})
        assert "-p" in cmd
        assert "pass123" in cmd

    def test_passlist_flag(self):
        cmd = self.tool.build_command("192.168.1.1", {"passlist": "/tmp/pass.txt"})
        assert "-P" in cmd
        assert "/tmp/pass.txt" in cmd

    def test_fast_profile(self):
        cmd = self.tool.build_command("192.168.1.1", {"profile": "fast"})
        assert "-t" in cmd
        idx = cmd.index("-t")
        assert cmd[idx + 1] == "16"

    def test_stealth_profile(self):
        cmd = self.tool.build_command("192.168.1.1", {"profile": "stealth"})
        idx = cmd.index("-t")
        assert cmd[idx + 1] == "2"

    def test_port_override(self):
        cmd = self.tool.build_command("192.168.1.1", {"port": 2222})
        assert "-s" in cmd
        assert "2222" in cmd

    def test_stop_on_success_flag(self):
        cmd = self.tool.build_command("192.168.1.1", {"stop_on_success": True})
        assert "-f" in cmd

    def test_no_stop_on_success(self):
        cmd = self.tool.build_command("192.168.1.1", {"stop_on_success": False})
        assert "-f" not in cmd

    def test_all_supported_protocols(self):
        for proto in HydraTool.SUPPORTED_PROTOCOLS:
            cmd = self.tool.build_command("192.168.1.1", {"protocol": proto})
            assert proto in cmd


class TestHydraToolParseOutput:
    def setup_method(self):
        self.tool = HydraTool()

    def test_parse_credential_found(self):
        output = "[22][ssh] host: 192.168.1.1   login: admin   password: password123"
        result = self.tool.parse_output(output, 0)
        assert result["total_credentials"] == 1
        cred = result["credentials"][0]
        assert cred["login"] == "admin"
        assert cred["password"] == "password123"
        assert cred["host"] == "192.168.1.1"

    def test_parse_no_credentials(self):
        output = "Hydra v9.1 starting...\n0 of 1 target completed"
        result = self.tool.parse_output(output, 1)
        assert result["total_credentials"] == 0
        assert result["credentials"] == []

    def test_parse_multiple_credentials(self):
        output = (
            "[21][ftp] host: 10.0.0.1   login: user1   password: pass1\n"
            "[21][ftp] host: 10.0.0.1   login: user2   password: pass2"
        )
        result = self.tool.parse_output(output, 0)
        assert result["total_credentials"] == 2

    def test_findings_severity_critical(self):
        output = "[22][ssh] host: 192.168.1.1   login: root   password: toor"
        result = self.tool.parse_output(output, 0)
        assert result["findings"][0]["severity"] == "critical"


class TestHydraToolRiskScore:
    def setup_method(self):
        self.tool = HydraTool()

    def test_no_credentials_score_zero(self):
        parsed = {"total_credentials": 0}
        assert self.tool.get_risk_score(parsed) == 0.0

    def test_one_credential_score_eight(self):
        parsed = {"total_credentials": 1}
        assert self.tool.get_risk_score(parsed) == 8.0

    def test_multiple_credentials_score_ten(self):
        parsed = {"total_credentials": 3}
        assert self.tool.get_risk_score(parsed) == 10.0
