"""Unit tests for the tool engine (Phase 4)"""
import pytest
from unittest.mock import MagicMock, patch


# ── ToolRegistry ─────────────────────────────────────────────────────────────

class TestToolRegistry:
    def test_register_and_get(self):
        from app.core.tool_engine.tool_registry import ToolRegistry
        from app.core.tool_engine.base_tool import BaseTool, ToolCategory

        class FakeTool(BaseTool):
            name = "fake_test_tool_xyz"
            category = ToolCategory.NETWORK
            binary = "fake_bin_xyz"

            def build_command(self, target, options):
                return [self.binary, target]

            def parse_output(self, raw_output, exit_code):
                return {"raw": raw_output, "findings": []}

        ToolRegistry.register(FakeTool)
        retrieved = ToolRegistry.get("fake_test_tool_xyz")
        assert retrieved is FakeTool

    def test_get_unknown_raises(self):
        from app.core.tool_engine.tool_registry import ToolRegistry
        with pytest.raises(ValueError, match="not registered"):
            ToolRegistry.get("__this_does_not_exist__")

    def test_is_available_false_for_nonexistent_binary(self):
        from app.core.tool_engine.tool_registry import ToolRegistry
        from app.core.tool_engine.base_tool import BaseTool, ToolCategory

        class NoSuchBinaryTool(BaseTool):
            name = "tool_with_missing_binary_xyz"
            category = ToolCategory.NETWORK
            binary = "definitely_not_installed_xyz_abc"

            def build_command(self, t, o):
                return [self.binary, t]

            def parse_output(self, r, e):
                return {"findings": []}

        ToolRegistry.register(NoSuchBinaryTool)
        assert ToolRegistry.is_available("tool_with_missing_binary_xyz") is False

    def test_list_tools_returns_dict(self):
        from app.core.tool_engine.tool_registry import ToolRegistry
        import app.core.tool_definitions  # noqa triggers nmap/nikto/gobuster registration
        tools = ToolRegistry.list_tools()
        assert isinstance(tools, dict)
        assert "nmap" in tools
        assert "nikto" in tools
        assert "gobuster" in tools


# ── NmapTool ─────────────────────────────────────────────────────────────────

class TestNmapTool:
    @pytest.fixture(autouse=True)
    def _load(self):
        import app.core.tool_definitions  # noqa

    def _tool(self):
        from app.core.tool_definitions.nmap_tool import NmapTool
        return NmapTool()

    def test_build_command_quick_profile(self):
        tool = self._tool()
        cmd = tool.build_command("192.168.1.1", {"profile": "quick"})
        assert "nmap" in cmd
        assert "-T4" in cmd
        assert "-F" in cmd
        assert "192.168.1.1" in cmd

    def test_build_command_standard_profile(self):
        tool = self._tool()
        cmd = tool.build_command("10.0.0.1", {"profile": "standard"})
        assert "-sV" in cmd
        assert "-oX" in cmd

    def test_build_command_with_ports(self):
        tool = self._tool()
        cmd = tool.build_command("10.0.0.1", {"ports": "80,443"})
        assert "-p" in cmd
        assert "80,443" in cmd

    def test_parse_output_xml(self):
        tool = self._tool()
        xml = """<?xml version="1.0"?>
<nmaprun>
  <host>
    <status state="up"/>
    <address addr="192.168.1.1" addrtype="ipv4"/>
    <ports>
      <port portid="80" protocol="tcp">
        <state state="open"/>
        <service name="http" product="Apache"/>
      </port>
    </ports>
  </host>
</nmaprun>"""
        result = tool.parse_output(xml, 0)
        assert result["total_open_ports"] == 1
        assert len(result["hosts"]) == 1
        assert len(result["findings"]) == 1
        assert result["findings"][0]["title"] == "Open port 80/tcp"

    def test_parse_output_no_xml(self):
        tool = self._tool()
        result = tool.parse_output("some non-xml output", 0)
        assert result["total_open_ports"] == 0
        assert result["findings"] == []

    def test_risk_score_zero_ports(self):
        tool = self._tool()
        assert tool.get_risk_score({"total_open_ports": 0}) == 0.0

    def test_risk_score_few_ports(self):
        tool = self._tool()
        assert tool.get_risk_score({"total_open_ports": 3}) == 2.0

    def test_risk_score_many_ports(self):
        tool = self._tool()
        assert tool.get_risk_score({"total_open_ports": 60}) == 8.0


# ── GenericTool ──────────────────────────────────────────────────────────────

class TestGenericTool:
    def test_build_command_string_args(self):
        from app.core.tool_definitions.generic_tool import GenericTool
        tool = GenericTool("mytool", "mybinary")
        cmd = tool.build_command("192.168.1.1", {"args": "-v -n"})
        assert cmd == ["mybinary", "-v", "-n", "192.168.1.1"]

    def test_build_command_list_args(self):
        from app.core.tool_definitions.generic_tool import GenericTool
        tool = GenericTool("mytool", "mybinary")
        cmd = tool.build_command("target.com", {"args": ["-a", "-b"]})
        assert cmd == ["mybinary", "-a", "-b", "target.com"]

    def test_build_command_no_args(self):
        from app.core.tool_definitions.generic_tool import GenericTool
        tool = GenericTool("mytool", "mybinary")
        cmd = tool.build_command("target.com", {})
        assert cmd == ["mybinary", "target.com"]

    def test_parse_output(self):
        from app.core.tool_definitions.generic_tool import GenericTool
        tool = GenericTool("mytool", "mybinary")
        result = tool.parse_output("line1\nline2\n", 0)
        assert result["exit_code"] == 0
        assert "line1" in result["lines"]
        assert result["findings"] == []


# ── SubprocessExecutor ───────────────────────────────────────────────────────

class TestSubprocessExecutor:
    def test_executor_binary_not_found(self):
        from app.core.tool_engine.executor import SubprocessExecutor
        from app.core.tool_definitions.generic_tool import GenericTool

        with patch("app.core.tool_engine.executor.subprocess.Popen") as mock_popen:
            mock_popen.side_effect = FileNotFoundError("No such file")
            tool = GenericTool("missing", "definitely_not_installed_xyz")
            executor = SubprocessExecutor()
            result = executor.execute(tool, "localhost", {})
            assert result.success is False
            assert "not found" in result.error.lower()

    def test_executor_timeout(self):
        from app.core.tool_engine.executor import SubprocessExecutor
        from app.core.tool_definitions.generic_tool import GenericTool
        import time

        with patch("app.core.tool_engine.executor.subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            # Simulate infinite output to trigger timeout
            call_count = [0]
            def slow_readline():
                call_count[0] += 1
                time.sleep(0.2)
                return "line\n"
            mock_process.stdout.readline = slow_readline
            mock_process.returncode = 0
            mock_process.pid = 999
            mock_popen.return_value = mock_process

            tool = GenericTool("slow", "slowtool")
            executor = SubprocessExecutor(timeout=0)  # 0 second timeout
            result = executor.execute(tool, "localhost", {"timeout": 0})
            assert result.success is False
            assert "Timeout" in result.error or result.exit_code == -9

    def test_executor_success(self):
        from app.core.tool_engine.executor import SubprocessExecutor
        from app.core.tool_definitions.generic_tool import GenericTool

        with patch("app.core.tool_engine.executor.subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            lines_iter = iter(["output line 1\n", "output line 2\n", ""])
            mock_process.stdout.readline = lambda: next(lines_iter)
            mock_process.returncode = 0
            mock_process.pid = 123
            mock_popen.return_value = mock_process

            tool = GenericTool("test", "testbin")
            executor = SubprocessExecutor()
            result = executor.execute(tool, "localhost", {})
            assert result.success is True
            assert "output line 1" in result.raw_output

    def test_executor_invalid_target(self):
        from app.core.tool_engine.executor import SubprocessExecutor
        from app.core.tool_definitions.nmap_tool import NmapTool
        import app.core.tool_definitions  # noqa

        tool = NmapTool()
        executor = SubprocessExecutor()
        result = executor.execute(tool, "invalid target!!@@", {})
        assert result.success is False
        assert "Invalid target" in result.error
