"""Unit tests for Celery tasks (Phase 4)"""
import pytest
from unittest.mock import MagicMock, patch


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_task(db, user_id: int, tool_name: str = "nmap", target: str = "localhost"):
    from app.models.task import Task, TaskStatusEnum
    task = Task(
        name=f"{tool_name} -> {target}",
        tool_name=tool_name,
        target=target,
        options={},
        status=TaskStatusEnum.pending,
        user_id=user_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def _make_user(db):
    from app.models.user import User
    from app.core.security import PasswordHandler
    user = User(
        email="worker@example.com",
        username="workeruser",
        hashed_password=PasswordHandler.hash_password("Pass123!"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ── BaseRedTeamTask ───────────────────────────────────────────────────────────

class TestBaseRedTeamTask:
    def test_update_task_status_not_found_is_silent(self, db_session):
        """_update_task_status with unknown celery_task_id should not raise."""
        from app.tasks.base_task import BaseRedTeamTask
        from app.models.task import TaskStatusEnum
        task_obj = BaseRedTeamTask()
        # Should not raise even if task not found
        task_obj._update_task_status("non-existent-celery-id", TaskStatusEnum.completed)


# ── execute_tool task ─────────────────────────────────────────────────────────

class TestExecuteToolTask:
    def test_execute_tool_success(self, db_session, celery_eager):
        """Task completes and creates a Result record."""
        import app.core.tool_definitions  # noqa
        from app.core.tool_engine.tool_registry import ToolRegistry
        from app.core.tool_engine.base_tool import BaseTool, ToolCategory, ToolResult
        from app.tasks.tool_executor import execute_tool
        from app.models.task import TaskStatusEnum
        from app.models.result import Result

        user = _make_user(db_session)
        task = _make_task(db_session, user.id)

        # Register a fast mock tool
        class MockTool(BaseTool):
            name = "mock_success_tool"
            category = ToolCategory.NETWORK
            binary = "mock_bin"
            def build_command(self, t, o): return ["echo", t]
            def parse_output(self, r, e): return {"findings": [], "raw": r}

        ToolRegistry.register(MockTool)

        with patch("app.core.tool_engine.executor.subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            lines = iter(["scan output\n", ""])
            mock_process.stdout.readline = lambda: next(lines)
            mock_process.returncode = 0
            mock_process.pid = 1
            mock_popen.return_value = mock_process

            result = execute_tool(
                task.id, "mock_success_tool", "localhost", {}, user.id
            )

        db_session.refresh(task)
        assert task.status == TaskStatusEnum.completed
        results = db_session.query(Result).filter(Result.task_id == task.id).all()
        assert len(results) == 1
        assert result["success"] is True

    def test_execute_tool_failure_on_unknown_tool(self, db_session, celery_eager):
        """Task fails if tool is not registered."""
        from app.tasks.tool_executor import execute_tool
        from app.models.task import TaskStatusEnum

        user = _make_user(db_session)
        task = _make_task(db_session, user.id, tool_name="not_a_real_tool")

        with pytest.raises(Exception):
            execute_tool(task.id, "not_a_real_tool", "localhost", {}, user.id)

        db_session.refresh(task)
        assert task.status == TaskStatusEnum.failed

    def test_task_status_update_on_success(self, db_session, celery_eager):
        """Task status transitions PENDING -> RUNNING -> COMPLETED."""
        import app.core.tool_definitions  # noqa
        from app.core.tool_engine.tool_registry import ToolRegistry
        from app.core.tool_engine.base_tool import BaseTool, ToolCategory
        from app.tasks.tool_executor import execute_tool
        from app.models.task import TaskStatusEnum

        class StatusTool(BaseTool):
            name = "status_check_tool"
            category = ToolCategory.NETWORK
            binary = "status_bin"
            def build_command(self, t, o): return ["echo", t]
            def parse_output(self, r, e): return {"findings": []}

        ToolRegistry.register(StatusTool)

        user = _make_user(db_session)
        task = _make_task(db_session, user.id)

        with patch("app.core.tool_engine.executor.subprocess.Popen") as mock_popen:
            mp = MagicMock()
            lines = iter(["ok\n", ""])
            mp.stdout.readline = lambda: next(lines)
            mp.returncode = 0
            mp.pid = 2
            mock_popen.return_value = mp
            execute_tool(task.id, "status_check_tool", "localhost", {}, user.id)

        db_session.refresh(task)
        assert task.status == TaskStatusEnum.completed

    def test_task_status_update_on_failure(self, db_session, celery_eager):
        """Task status becomes FAILED when tool binary is not found."""
        import app.core.tool_definitions  # noqa
        from app.core.tool_engine.tool_registry import ToolRegistry
        from app.core.tool_engine.base_tool import BaseTool, ToolCategory
        from app.tasks.tool_executor import execute_tool
        from app.models.task import TaskStatusEnum

        class FailTool(BaseTool):
            name = "always_fail_tool"
            category = ToolCategory.NETWORK
            binary = "ghost_binary_xyz"
            def build_command(self, t, o): return [self.binary, t]
            def parse_output(self, r, e): return {"findings": []}

        ToolRegistry.register(FailTool)
        user = _make_user(db_session)
        task = _make_task(db_session, user.id)

        with patch("app.core.tool_engine.executor.subprocess.Popen") as mock_popen:
            mock_popen.side_effect = FileNotFoundError("ghost_binary_xyz not found")
            # Executor catches FileNotFoundError and returns a failed ToolResult — no raise
            result = execute_tool(task.id, "always_fail_tool", "localhost", {}, user.id)

        assert result["success"] is False
        db_session.refresh(task)
        assert task.status == TaskStatusEnum.failed

    def test_audit_log_created_on_success(self, db_session, celery_eager):
        """AuditLog entry is created when tool execution completes."""
        import app.core.tool_definitions  # noqa
        from app.core.tool_engine.tool_registry import ToolRegistry
        from app.core.tool_engine.base_tool import BaseTool, ToolCategory
        from app.tasks.tool_executor import execute_tool
        from app.models.audit_log import AuditLog

        class AuditTool(BaseTool):
            name = "audit_test_tool"
            category = ToolCategory.NETWORK
            binary = "audit_bin"
            def build_command(self, t, o): return ["echo", t]
            def parse_output(self, r, e): return {"findings": []}

        ToolRegistry.register(AuditTool)
        user = _make_user(db_session)
        task = _make_task(db_session, user.id)

        with patch("app.core.tool_engine.executor.subprocess.Popen") as mock_popen:
            mp = MagicMock()
            lines = iter(["out\n", ""])
            mp.stdout.readline = lambda: next(lines)
            mp.returncode = 0
            mp.pid = 3
            mock_popen.return_value = mp
            execute_tool(task.id, "audit_test_tool", "localhost", {}, user.id)

        logs = (
            db_session.query(AuditLog)
            .filter(AuditLog.action == "tool_execution_completed")
            .all()
        )
        assert len(logs) >= 1


# ── Cleanup tasks ─────────────────────────────────────────────────────────────

class TestCleanupTasks:
    def test_cleanup_expired_results_returns_dict(self, db_session):
        from app.tasks.cleanup_tasks import cleanup_expired_results
        result = cleanup_expired_results()
        assert "deleted" in result

    def test_health_check_returns_ok(self, db_session):
        from app.tasks.cleanup_tasks import health_check
        result = health_check()
        assert result["db"] == "ok"
