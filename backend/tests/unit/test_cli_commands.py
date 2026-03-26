"""Unit tests for CLI commands using typer.testing.CliRunner"""
import pytest
from typer.testing import CliRunner
from unittest.mock import MagicMock, patch
from pathlib import Path

runner = CliRunner()


@pytest.fixture
def tmp_config_env(tmp_path, monkeypatch):
    """Redirect config file to a temporary directory."""
    config_dir = tmp_path / ".redteam"
    config_file = config_dir / "config.json"
    monkeypatch.setattr("cli.config.CONFIG_DIR", config_dir)
    monkeypatch.setattr("cli.config.CONFIG_FILE", config_file)
    return config_dir, config_file


def _make_mock_client(**methods):
    """Create a MagicMock APIClient with preset return values."""
    mock = MagicMock()
    for method, retval in methods.items():
        getattr(mock, method).return_value = retval
    return mock


# ──────────────────────────────────────────────
# Auth commands
# ──────────────────────────────────────────────

class TestAuthCommands:
    def test_auth_login_success(self, tmp_config_env):
        from cli.main import app
        with patch("cli.client.APIClient.post") as mock_post:
            mock_post.return_value = {
                "access_token": "tok_abc",
                "refresh_token": "ref_abc",
            }
            result = runner.invoke(
                app,
                ["auth", "login", "--user", "admin", "--pass", "pass123"],
            )
        assert result.exit_code == 0
        assert "Logged in" in result.output

    def test_auth_login_stores_token(self, tmp_config_env):
        config_dir, config_file = tmp_config_env
        from cli.main import app
        with patch("cli.client.APIClient.post") as mock_post:
            mock_post.return_value = {"access_token": "tok123", "refresh_token": "r123"}
            runner.invoke(app, ["auth", "login", "--user", "admin", "--pass", "secret"])
        assert config_file.exists()
        import json
        data = json.loads(config_file.read_text())
        assert data["access_token"] == "tok123"

    def test_auth_logout_clears_config(self, tmp_config_env):
        config_dir, config_file = tmp_config_env
        from cli.config import CLIConfig
        cfg = CLIConfig(access_token="tok", username="user")
        cfg.save()

        from cli.main import app
        result = runner.invoke(app, ["auth", "logout"])
        assert result.exit_code == 0
        assert "Logged out" in result.output
        loaded = CLIConfig.load()
        assert loaded.access_token is None

    def test_auth_whoami_shows_user_info(self, tmp_config_env):
        from cli.main import app
        from cli.config import CLIConfig
        CLIConfig(access_token="tok").save()
        with patch("cli.commands.auth.get_client") as mock_get:
            mock_client = _make_mock_client(
                get={"username": "admin", "email": "admin@test.com", "role": "admin"}
            )
            mock_get.return_value = mock_client
            result = runner.invoke(app, ["auth", "whoami"])
        assert result.exit_code == 0
        assert "admin" in result.output

    def test_auth_config_sets_url(self, tmp_config_env):
        from cli.main import app
        result = runner.invoke(
            app, ["auth", "config", "--url", "http://custom.api/v1"]
        )
        assert result.exit_code == 0
        from cli.config import CLIConfig
        cfg = CLIConfig.load()
        assert cfg.api_url == "http://custom.api/v1"

    def test_auth_config_sets_format(self, tmp_config_env):
        from cli.main import app
        result = runner.invoke(app, ["auth", "config", "--format", "json"])
        assert result.exit_code == 0
        from cli.config import CLIConfig
        cfg = CLIConfig.load()
        assert cfg.output_format == "json"

    def test_auth_config_invalid_format_exits(self, tmp_config_env):
        from cli.main import app
        result = runner.invoke(app, ["auth", "config", "--format", "xml"])
        assert result.exit_code != 0


# ──────────────────────────────────────────────
# Project commands
# ──────────────────────────────────────────────

class TestProjectCommands:
    def _mock_authenticated(self, tmp_config_env):
        from cli.config import CLIConfig
        CLIConfig(access_token="tok").save()

    def test_projects_list(self, tmp_config_env):
        self._mock_authenticated(tmp_config_env)
        from cli.main import app
        with patch("cli.commands.projects.get_client") as mock_get:
            mock_client = _make_mock_client(
                get={"items": [{"id": 1, "name": "Proj1", "status": "active",
                                "member_count": 2, "target_count": 3,
                                "created_at": "2024-01-01T00:00:00"}],
                     "total": 1}
            )
            mock_get.return_value = mock_client
            result = runner.invoke(app, ["projects", "list"])
        assert result.exit_code == 0

    def test_projects_create(self, tmp_config_env):
        self._mock_authenticated(tmp_config_env)
        from cli.main import app
        with patch("cli.commands.projects.get_client") as mock_get:
            mock_client = _make_mock_client(
                post={"id": 5, "name": "New Project", "status": "active"}
            )
            mock_get.return_value = mock_client
            result = runner.invoke(app, ["projects", "create", "New Project"])
        assert result.exit_code == 0
        assert "5" in result.output

    def test_projects_use_sets_default(self, tmp_config_env):
        self._mock_authenticated(tmp_config_env)
        from cli.main import app
        result = runner.invoke(app, ["projects", "use", "42"])
        assert result.exit_code == 0
        from cli.config import CLIConfig
        cfg = CLIConfig.load()
        assert cfg.default_project_id == 42

    def test_projects_archive(self, tmp_config_env):
        self._mock_authenticated(tmp_config_env)
        from cli.main import app
        with patch("cli.commands.projects.get_client") as mock_get:
            mock_client = _make_mock_client(post={"id": 3, "status": "archived"})
            mock_get.return_value = mock_client
            result = runner.invoke(app, ["projects", "archive", "3"])
        assert result.exit_code == 0
        assert "archived" in result.output.lower()


# ──────────────────────────────────────────────
# Target commands
# ──────────────────────────────────────────────

class TestTargetCommands:
    def _setup(self, tmp_config_env):
        from cli.config import CLIConfig
        CLIConfig(access_token="tok", default_project_id=1).save()

    def test_targets_list(self, tmp_config_env):
        self._setup(tmp_config_env)
        from cli.main import app
        with patch("cli.commands.targets.get_client") as mock_get:
            mock_client = _make_mock_client(
                get={"items": [{"id": 1, "value": "192.168.1.0/24", "target_type": "cidr",
                                "status": "in_scope", "tags": None}]}
            )
            mock_get.return_value = mock_client
            result = runner.invoke(app, ["targets", "list"])
        assert result.exit_code == 0

    def test_targets_add(self, tmp_config_env):
        self._setup(tmp_config_env)
        from cli.main import app
        with patch("cli.commands.targets.get_client") as mock_get:
            mock_client = _make_mock_client(
                post={"id": 10, "value": "192.168.1.1", "target_type": "ip"}
            )
            mock_get.return_value = mock_client
            result = runner.invoke(app, ["targets", "add", "192.168.1.1", "--type", "ip"])
        assert result.exit_code == 0
        assert "192.168.1.1" in result.output

    def test_targets_validate_in_scope(self, tmp_config_env):
        self._setup(tmp_config_env)
        from cli.main import app
        with patch("cli.commands.targets.get_client") as mock_get:
            mock_client = _make_mock_client(
                post={"in_scope": True, "target": "192.168.1.5"}
            )
            mock_get.return_value = mock_client
            result = runner.invoke(app, ["targets", "validate", "192.168.1.5"])
        assert result.exit_code == 0
        assert "IN SCOPE" in result.output

    def test_targets_validate_out_of_scope_exits_1(self, tmp_config_env):
        self._setup(tmp_config_env)
        from cli.main import app
        with patch("cli.commands.targets.get_client") as mock_get:
            mock_client = _make_mock_client(
                post={"in_scope": False, "target": "8.8.8.8"}
            )
            mock_get.return_value = mock_client
            result = runner.invoke(app, ["targets", "validate", "8.8.8.8"])
        assert result.exit_code == 1
        assert "OUT OF SCOPE" in result.output


# ──────────────────────────────────────────────
# Scan commands
# ──────────────────────────────────────────────

class TestScanCommands:
    def _setup(self, tmp_config_env):
        from cli.config import CLIConfig
        CLIConfig(access_token="tok").save()

    def test_scan_run_launches_task(self, tmp_config_env):
        self._setup(tmp_config_env)
        from cli.main import app
        with patch("cli.commands.scan.get_client") as mock_get:
            mock_client = _make_mock_client(
                post={"id": 99, "status": "pending"}
            )
            mock_get.return_value = mock_client
            result = runner.invoke(app, ["scan", "run", "nmap", "192.168.1.1"])
        assert result.exit_code == 0
        assert "99" in result.output

    def test_scan_status(self, tmp_config_env):
        self._setup(tmp_config_env)
        from cli.main import app
        with patch("cli.commands.scan.get_client") as mock_get:
            mock_client = _make_mock_client(
                get={"task_id": 99, "status": "completed", "celery_state": "SUCCESS"}
            )
            mock_get.return_value = mock_client
            result = runner.invoke(app, ["scan", "status", "99"])
        assert result.exit_code == 0
        assert "completed" in result.output.lower()

    def test_scan_cancel(self, tmp_config_env):
        self._setup(tmp_config_env)
        from cli.main import app
        with patch("cli.commands.scan.get_client") as mock_get:
            mock_client = _make_mock_client(delete=None)
            mock_get.return_value = mock_client
            result = runner.invoke(app, ["scan", "cancel", "99"])
        assert result.exit_code == 0
        assert "cancelled" in result.output.lower()

    def test_scan_list(self, tmp_config_env):
        self._setup(tmp_config_env)
        from cli.main import app
        with patch("cli.commands.scan.get_client") as mock_get:
            mock_client = _make_mock_client(
                get={"items": [{"id": 1, "tool_name": "nmap", "target": "10.0.0.1",
                                "status": "completed", "created_at": "2024-01-01T00:00:00"}]}
            )
            mock_get.return_value = mock_client
            result = runner.invoke(app, ["scan", "list"])
        assert result.exit_code == 0


# ──────────────────────────────────────────────
# Findings commands
# ──────────────────────────────────────────────

class TestFindingsCommands:
    def _setup(self, tmp_config_env):
        from cli.config import CLIConfig
        CLIConfig(access_token="tok").save()

    def test_findings_list(self, tmp_config_env):
        self._setup(tmp_config_env)
        from cli.main import app
        with patch("cli.commands.findings.get_client") as mock_get:
            mock_client = _make_mock_client(
                get={"items": [{"id": 1, "severity": "high", "title": "XSS",
                                "host": "10.0.0.1", "tool_name": "nikto",
                                "risk_score": 7}], "total": 1}
            )
            mock_get.return_value = mock_client
            result = runner.invoke(app, ["findings", "list"])
        assert result.exit_code == 0

    def test_findings_update(self, tmp_config_env):
        self._setup(tmp_config_env)
        from cli.main import app
        with patch("cli.commands.findings.get_client") as mock_get:
            mock_client = _make_mock_client(patch={"id": 1, "status": "resolved"})
            mock_get.return_value = mock_client
            result = runner.invoke(app, ["findings", "update", "1", "--status", "resolved"])
        assert result.exit_code == 0
        assert "updated" in result.output.lower()

    def test_findings_mark_fp(self, tmp_config_env):
        self._setup(tmp_config_env)
        from cli.main import app
        with patch("cli.commands.findings.get_client") as mock_get:
            mock_client = _make_mock_client(post={"id": 1})
            mock_get.return_value = mock_client
            result = runner.invoke(app, ["findings", "fp", "1", "Test reason"])
        assert result.exit_code == 0


# ──────────────────────────────────────────────
# Reports commands
# ──────────────────────────────────────────────

class TestReportsCommands:
    def _setup(self, tmp_config_env):
        from cli.config import CLIConfig
        CLIConfig(access_token="tok").save()

    def test_reports_create(self, tmp_config_env):
        self._setup(tmp_config_env)
        from cli.main import app
        with patch("cli.commands.reports.get_client") as mock_get:
            mock_client = _make_mock_client(
                post={"id": 7, "status": "pending", "title": "Test Report"}
            )
            mock_get.return_value = mock_client
            result = runner.invoke(
                app,
                ["reports", "create", "1", "--title", "Test Report"],
            )
        assert result.exit_code == 0
        assert "7" in result.output

    def test_reports_list(self, tmp_config_env):
        self._setup(tmp_config_env)
        from cli.main import app
        with patch("cli.commands.reports.get_client") as mock_get:
            mock_client = _make_mock_client(
                get={"items": [{"id": 1, "title": "Report 1", "report_type": "technical",
                                "status": "ready", "overall_risk": 5, "total_findings": 10}]}
            )
            mock_get.return_value = mock_client
            result = runner.invoke(app, ["reports", "list"])
        assert result.exit_code == 0

    def test_reports_download(self, tmp_config_env, tmp_path):
        self._setup(tmp_config_env)
        from cli.main import app
        with patch("cli.commands.reports.get_client") as mock_get:
            mock_client = MagicMock()
            mock_client.get.return_value = {
                "id": 1, "status": "ready", "report_format": "pdf"
            }
            mock_client.download.return_value = 5120
            mock_get.return_value = mock_client
            result = runner.invoke(
                app,
                ["reports", "download", "1", "--output", str(tmp_path)],
            )
        assert result.exit_code == 0
        assert "Downloaded" in result.output


# ──────────────────────────────────────────────
# Version flag
# ──────────────────────────────────────────────

class TestVersionFlag:
    def test_version_flag(self, tmp_config_env):
        from cli.main import app
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "v1.0.0" in result.output
