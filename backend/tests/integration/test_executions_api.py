"""Integration tests for the executions API (Phase 4)"""
import pytest
from unittest.mock import patch, MagicMock


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def auth_headers(client, test_user_data, registered_user, auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def _register_mock_tool():
    """Register a mock tool in ToolRegistry for testing."""
    from app.core.tool_engine.tool_registry import ToolRegistry
    from app.core.tool_engine.base_tool import BaseTool, ToolCategory

    class TestExecTool(BaseTool):
        name = "test_exec_tool"
        category = ToolCategory.NETWORK
        binary = "test_exec_bin"
        def build_command(self, t, o): return ["echo", t]
        def parse_output(self, r, e): return {"findings": [], "raw": r}

    ToolRegistry.register(TestExecTool)
    # Patch is_available to return True for this tool
    original = ToolRegistry.is_available.__func__ if hasattr(ToolRegistry.is_available, '__func__') else None
    yield
    # Cleanup: remove from registry if needed
    ToolRegistry._tools.pop("test_exec_tool", None)


# ── POST /executions ──────────────────────────────────────────────────────────

class TestCreateExecution:
    def test_create_execution_unregistered_tool_returns_400(self, client, auth_headers):
        resp = client.post(
            "/api/v1/executions",
            json={"tool_name": "completely_unknown_xyz", "target": "192.168.1.1"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_create_execution_requires_auth(self, client):
        resp = client.post(
            "/api/v1/executions",
            json={"tool_name": "nmap", "target": "192.168.1.1"},
        )
        assert resp.status_code in (401, 403)

    def test_create_execution_success(self, client, auth_headers, _register_mock_tool):
        with patch("app.core.tool_engine.tool_registry.ToolRegistry.is_available", return_value=True):
            with patch("app.tasks.tool_executor.execute_tool.apply_async") as mock_async:
                mock_job = MagicMock()
                mock_job.id = "celery-job-id-123"
                mock_async.return_value = mock_job

                resp = client.post(
                    "/api/v1/executions",
                    json={
                        "tool_name": "test_exec_tool",
                        "target": "192.168.1.1",
                        "options": {"profile": "quick"},
                    },
                    headers=auth_headers,
                )
        assert resp.status_code == 202
        data = resp.json()
        assert data["tool_name"] == "test_exec_tool"
        assert data["target"] == "192.168.1.1"
        assert data["status"] == "pending"

    def test_create_execution_invalid_priority(self, client, auth_headers, _register_mock_tool):
        with patch("app.core.tool_engine.tool_registry.ToolRegistry.is_available", return_value=True):
            resp = client.post(
                "/api/v1/executions",
                json={
                    "tool_name": "test_exec_tool",
                    "target": "192.168.1.1",
                    "priority": 99,
                },
                headers=auth_headers,
            )
        assert resp.status_code == 422


# ── GET /executions/{task_id}/status ─────────────────────────────────────────

class TestGetExecutionStatus:
    def _create_task(self, db_session, user_id):
        from app.models.task import Task, TaskStatusEnum
        task = Task(
            name="nmap -> localhost",
            tool_name="nmap",
            target="localhost",
            options={},
            status=TaskStatusEnum.pending,
            user_id=user_id,
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        return task

    def test_get_status_not_found(self, client, auth_headers):
        resp = client.get("/api/v1/executions/99999/status", headers=auth_headers)
        assert resp.status_code == 404

    def test_get_status_success(self, client, auth_headers, auth_token, db_session):
        from app.core.security import JWTHandler
        payload = JWTHandler.verify_token(auth_token)
        user_id = int(payload["sub"])
        task = self._create_task(db_session, user_id)

        resp = client.get(f"/api/v1/executions/{task.id}/status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == task.id
        assert data["status"] == "pending"

    def test_get_status_requires_auth(self, client):
        resp = client.get("/api/v1/executions/1/status")
        assert resp.status_code in (401, 403)


# ── DELETE /executions/{task_id} ──────────────────────────────────────────────

class TestCancelExecution:
    def _create_task(self, db_session, user_id, status="pending"):
        from app.models.task import Task, TaskStatusEnum
        status_map = {
            "pending": TaskStatusEnum.pending,
            "running": TaskStatusEnum.running,
            "completed": TaskStatusEnum.completed,
        }
        task = Task(
            name="nmap -> localhost",
            tool_name="nmap",
            target="localhost",
            options={},
            status=status_map[status],
            user_id=user_id,
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        return task

    def test_cancel_pending_task_success(self, client, auth_headers, auth_token, db_session):
        from app.core.security import JWTHandler
        payload = JWTHandler.verify_token(auth_token)
        user_id = int(payload["sub"])
        task = self._create_task(db_session, user_id, "pending")

        resp = client.delete(f"/api/v1/executions/{task.id}", headers=auth_headers)
        assert resp.status_code == 204

        db_session.refresh(task)
        from app.models.task import TaskStatusEnum
        assert task.status == TaskStatusEnum.cancelled

    def test_cancel_completed_task_returns_400(self, client, auth_headers, auth_token, db_session):
        from app.core.security import JWTHandler
        payload = JWTHandler.verify_token(auth_token)
        user_id = int(payload["sub"])
        task = self._create_task(db_session, user_id, "completed")

        resp = client.delete(f"/api/v1/executions/{task.id}", headers=auth_headers)
        assert resp.status_code == 400

    def test_cancel_not_found(self, client, auth_headers):
        resp = client.delete("/api/v1/executions/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_cancel_requires_auth(self, client):
        resp = client.delete("/api/v1/executions/1")
        assert resp.status_code in (401, 403)


# ── GET /executions (list tools) ─────────────────────────────────────────────

class TestListTools:
    def test_list_tools_returns_list(self, client, auth_headers):
        import app.core.tool_definitions  # noqa
        resp = client.get("/api/v1/executions", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        names = [t["name"] for t in data]
        assert "nmap" in names

    def test_list_tools_includes_availability(self, client, auth_headers):
        import app.core.tool_definitions  # noqa
        resp = client.get("/api/v1/executions", headers=auth_headers)
        assert resp.status_code == 200
        for tool in resp.json():
            assert "available" in tool

    def test_list_tools_requires_auth(self, client):
        resp = client.get("/api/v1/executions")
        assert resp.status_code in (401, 403)


# ── SSE stream endpoint ───────────────────────────────────────────────────────

class TestStreamEndpoint:
    def test_stream_not_found(self, client, auth_headers):
        resp = client.get("/api/v1/executions/99999/stream", headers=auth_headers)
        assert resp.status_code == 404

    def test_stream_returns_sse_media_type(self, client, auth_headers, auth_token, db_session):
        from app.core.security import JWTHandler
        from app.models.task import Task, TaskStatusEnum
        payload = JWTHandler.verify_token(auth_token)
        user_id = int(payload["sub"])

        task = Task(
            name="nmap -> localhost",
            tool_name="nmap",
            target="localhost",
            options={},
            status=TaskStatusEnum.completed,  # completed so stream ends immediately
            user_id=user_id,
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        import app.core.redis_client as _redis_mod
        from unittest.mock import MagicMock as _MM
        mock_redis = _MM()
        mock_pubsub = _MM()
        mock_pubsub.get_message.return_value = None
        mock_redis.pubsub.return_value = mock_pubsub

        with patch.object(_redis_mod, "redis_client", mock_redis):
            resp = client.get(
                f"/api/v1/executions/{task.id}/stream",
                headers=auth_headers,
            )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

    def test_stream_requires_auth(self, client):
        resp = client.get("/api/v1/executions/1/stream")
        assert resp.status_code in (401, 403)
