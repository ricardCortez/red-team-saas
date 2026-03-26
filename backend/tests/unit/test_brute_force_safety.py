"""Unit tests for brute force safety check in SubprocessExecutor"""
import pytest
from unittest.mock import MagicMock, patch
from app.core.tool_engine.executor import SubprocessExecutor
from app.core.tool_engine.base_tool import ToolCategory
from app.core.tool_definitions.hydra_tool import HydraTool
from app.core.tool_definitions.medusa_tool import MedusaTool
from app.core.tool_definitions.john_tool import JohnTool
from app.core.tool_definitions.nmap_tool import NmapTool


class TestBruteForceMaxAttemptsSafetyCheck:
    def setup_method(self):
        self.executor = SubprocessExecutor()

    def test_hydra_blocked_over_10000_attempts(self):
        tool = HydraTool()
        result = self.executor.execute(
            tool, "192.168.1.1", {"max_attempts": 10001}
        )
        assert result.success is False
        assert "10000" in result.error

    def test_hydra_allowed_under_10000_attempts(self):
        tool = HydraTool()
        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.stdout = iter(["Hydra output"])
            mock_proc.returncode = 0
            mock_proc.wait.return_value = None
            mock_popen.return_value.__enter__ = lambda s: mock_proc
            mock_popen.return_value = mock_proc
            result = self.executor.execute(
                tool, "192.168.1.1", {"max_attempts": 5000}
            )
            # Should not be blocked by safety check (may fail for other reasons)
            assert "10000" not in (result.error or "")

    def test_medusa_blocked_over_10000_attempts(self):
        tool = MedusaTool()
        result = self.executor.execute(
            tool, "192.168.1.1", {"max_attempts": 99999}
        )
        assert result.success is False
        assert "safety limit" in result.error.lower() or "10000" in result.error

    def test_john_blocked_over_10000_attempts(self):
        tool = JohnTool()
        result = self.executor.execute(
            tool, "/tmp/hashes.txt", {"max_attempts": 50000}
        )
        assert result.success is False
        assert "10000" in result.error

    def test_exactly_10000_not_blocked(self):
        tool = HydraTool()
        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.stdout = iter([])
            mock_proc.returncode = 1
            mock_proc.wait.return_value = None
            mock_popen.return_value = mock_proc
            result = self.executor.execute(
                tool, "192.168.1.1", {"max_attempts": 10000}
            )
            assert "safety limit" not in (result.error or "")
            assert "10000 exceeds" not in (result.error or "")

    def test_non_brute_force_tool_not_affected(self):
        tool = NmapTool()
        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.stdout = iter([])
            mock_proc.returncode = 0
            mock_proc.wait.return_value = None
            mock_popen.return_value = mock_proc
            result = self.executor.execute(
                tool, "192.168.1.1", {"max_attempts": 999999}
            )
            # Should not be blocked — nmap is SCAN not BRUTE_FORCE
            assert "safety limit" not in (result.error or "")
            assert "exceeds" not in (result.error or "")

    def test_brute_force_without_max_attempts_not_blocked(self):
        tool = HydraTool()
        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.stdout = iter([])
            mock_proc.returncode = 1
            mock_proc.wait.return_value = None
            mock_popen.return_value = mock_proc
            result = self.executor.execute(tool, "192.168.1.1", {})
            assert "safety limit" not in (result.error or "")


class TestBruteForceToolCategory:
    def test_hydra_is_brute_force(self):
        assert HydraTool.category == ToolCategory.BRUTE_FORCE

    def test_medusa_is_brute_force(self):
        assert MedusaTool.category == ToolCategory.BRUTE_FORCE

    def test_john_is_brute_force(self):
        assert JohnTool.category == ToolCategory.BRUTE_FORCE

    def test_nmap_is_not_brute_force(self):
        assert NmapTool.category != ToolCategory.BRUTE_FORCE
