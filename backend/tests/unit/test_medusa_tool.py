"""Unit tests for MedusaTool"""
import pytest
from app.core.tool_definitions.medusa_tool import MedusaTool
from app.core.tool_engine.tool_registry import ToolRegistry


class TestMedusaToolRegistration:
    def test_registered_in_registry(self):
        assert "medusa" in ToolRegistry._tools

    def test_category_is_brute_force(self):
        tool = MedusaTool()
        from app.core.tool_engine.base_tool import ToolCategory
        assert tool.category == ToolCategory.BRUTE_FORCE

    def test_name(self):
        assert MedusaTool.name == "medusa"


class TestMedusaToolBuildCommand:
    def setup_method(self):
        self.tool = MedusaTool()

    def test_default_ssh_command(self):
        cmd = self.tool.build_command("192.168.1.1", {})
        assert "medusa" in cmd
        assert "-h" in cmd
        assert "192.168.1.1" in cmd
        assert "-M" in cmd
        assert "ssh" in cmd

    def test_module_selection(self):
        cmd = self.tool.build_command("192.168.1.1", {"module": "ftp"})
        idx = cmd.index("-M")
        assert cmd[idx + 1] == "ftp"

    def test_invalid_module_defaults_to_ssh(self):
        cmd = self.tool.build_command("192.168.1.1", {"module": "invalid"})
        idx = cmd.index("-M")
        assert cmd[idx + 1] == "ssh"

    def test_username_flag(self):
        cmd = self.tool.build_command("192.168.1.1", {"username": "root"})
        assert "-u" in cmd
        idx = cmd.index("-u")
        assert cmd[idx + 1] == "root"

    def test_userlist_flag(self):
        cmd = self.tool.build_command("192.168.1.1", {"userlist": "/tmp/users.txt"})
        assert "-U" in cmd

    def test_passlist_flag(self):
        cmd = self.tool.build_command("192.168.1.1", {"passlist": "/tmp/pass.txt"})
        assert "-P" in cmd

    def test_port_flag(self):
        cmd = self.tool.build_command("192.168.1.1", {"port": 2222})
        assert "-n" in cmd
        idx = cmd.index("-n")
        assert cmd[idx + 1] == "2222"

    def test_threads_flag(self):
        cmd = self.tool.build_command("192.168.1.1", {"threads": 8})
        idx = cmd.index("-t")
        assert cmd[idx + 1] == "8"

    def test_stop_on_success(self):
        cmd = self.tool.build_command("192.168.1.1", {"stop_on_success": True})
        assert "-f" in cmd

    def test_all_supported_modules(self):
        for mod in MedusaTool.SUPPORTED_MODULES:
            cmd = self.tool.build_command("192.168.1.1", {"module": mod})
            idx = cmd.index("-M")
            assert cmd[idx + 1] == mod


class TestMedusaToolParseOutput:
    def setup_method(self):
        self.tool = MedusaTool()

    def test_parse_account_found(self):
        output = "ACCOUNT FOUND: [ssh] Host: 192.168.1.1 User: admin Password: password123 [SUCCESS]"
        result = self.tool.parse_output(output, 0)
        assert result["total_credentials"] == 1
        cred = result["credentials"][0]
        assert cred["user"] == "admin"
        assert cred["password"] == "password123"
        assert cred["host"] == "192.168.1.1"

    def test_parse_no_credentials(self):
        output = "Medusa v2.2 starting...\nERROR: All passwords tested"
        result = self.tool.parse_output(output, 1)
        assert result["total_credentials"] == 0

    def test_findings_severity_critical(self):
        output = "ACCOUNT FOUND: [ftp] Host: 10.0.0.1 User: ftp Password: anonymous [SUCCESS]"
        result = self.tool.parse_output(output, 0)
        assert result["findings"][0]["severity"] == "critical"

    def test_multiple_accounts_found(self):
        output = (
            "ACCOUNT FOUND: [ssh] Host: 10.0.0.1 User: user1 Password: pass1 [SUCCESS]\n"
            "ACCOUNT FOUND: [ssh] Host: 10.0.0.1 User: user2 Password: pass2 [SUCCESS]"
        )
        result = self.tool.parse_output(output, 0)
        assert result["total_credentials"] == 2


class TestMedusaToolRiskScore:
    def setup_method(self):
        self.tool = MedusaTool()

    def test_no_creds_zero_score(self):
        assert self.tool.get_risk_score({"total_credentials": 0}) == 0.0

    def test_one_cred_eight_score(self):
        assert self.tool.get_risk_score({"total_credentials": 1}) == 8.0

    def test_multiple_creds_ten_score(self):
        assert self.tool.get_risk_score({"total_credentials": 5}) == 10.0
