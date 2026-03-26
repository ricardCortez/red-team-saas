"""Unit tests for cli/config.py"""
import json
import sys
import pytest
from pathlib import Path


@pytest.fixture
def tmp_config(tmp_path, monkeypatch):
    """Patch CONFIG_DIR and CONFIG_FILE to use a temp directory."""
    config_dir = tmp_path / ".redteam"
    config_file = config_dir / "config.json"
    monkeypatch.setattr("cli.config.CONFIG_DIR", config_dir)
    monkeypatch.setattr("cli.config.CONFIG_FILE", config_file)
    return config_dir, config_file


class TestCLIConfigDefaults:
    def test_default_api_url(self, tmp_config):
        from cli.config import CLIConfig
        cfg = CLIConfig()
        assert cfg.api_url == "http://localhost:8000/api/v1"

    def test_default_output_format_is_table(self, tmp_config):
        from cli.config import CLIConfig
        cfg = CLIConfig()
        assert cfg.output_format == "table"

    def test_default_tokens_are_none(self, tmp_config):
        from cli.config import CLIConfig
        cfg = CLIConfig()
        assert cfg.access_token is None
        assert cfg.refresh_token is None
        assert cfg.username is None

    def test_default_project_id_is_none(self, tmp_config):
        from cli.config import CLIConfig
        cfg = CLIConfig()
        assert cfg.default_project_id is None


class TestCLIConfigSaveLoad:
    def test_save_creates_file(self, tmp_config):
        config_dir, config_file = tmp_config
        from cli.config import CLIConfig
        cfg = CLIConfig(access_token="tok123", username="admin")
        cfg.save()
        assert config_file.exists()

    def test_save_load_roundtrip(self, tmp_config):
        config_dir, config_file = tmp_config
        from cli.config import CLIConfig
        original = CLIConfig(
            api_url="http://api.example.com",
            access_token="tok_abc",
            refresh_token="ref_abc",
            username="testuser",
            default_project_id=42,
            output_format="json",
        )
        original.save()
        loaded = CLIConfig.load()
        assert loaded.api_url == original.api_url
        assert loaded.access_token == original.access_token
        assert loaded.refresh_token == original.refresh_token
        assert loaded.username == original.username
        assert loaded.default_project_id == original.default_project_id
        assert loaded.output_format == original.output_format

    def test_load_nonexistent_returns_defaults(self, tmp_config):
        from cli.config import CLIConfig
        cfg = CLIConfig.load()
        assert cfg.api_url == "http://localhost:8000/api/v1"

    def test_load_corrupted_file_returns_defaults(self, tmp_config):
        config_dir, config_file = tmp_config
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file.write_text("not valid json {{{{")
        from cli.config import CLIConfig
        cfg = CLIConfig.load()
        assert cfg.api_url == "http://localhost:8000/api/v1"

    def test_save_creates_config_dir_if_missing(self, tmp_config):
        config_dir, config_file = tmp_config
        assert not config_dir.exists()
        from cli.config import CLIConfig
        CLIConfig().save()
        assert config_dir.exists()

    @pytest.mark.skipif(sys.platform == "win32", reason="chmod not applicable on Windows")
    def test_config_file_permissions_600(self, tmp_config):
        from cli.config import CLIConfig
        CLIConfig(access_token="secret").save()
        config_dir, config_file = tmp_config
        mode = oct(config_file.stat().st_mode)[-3:]
        assert mode == "600"


class TestCLIConfigClearAuth:
    def test_clear_auth_removes_tokens_and_username(self, tmp_config):
        from cli.config import CLIConfig
        cfg = CLIConfig(
            access_token="tok",
            refresh_token="ref",
            username="user",
        )
        cfg.save()
        cfg.clear_auth()
        loaded = CLIConfig.load()
        assert loaded.access_token is None
        assert loaded.refresh_token is None
        assert loaded.username is None

    def test_clear_auth_preserves_api_url(self, tmp_config):
        from cli.config import CLIConfig
        cfg = CLIConfig(api_url="http://custom.api", access_token="tok")
        cfg.save()
        cfg.clear_auth()
        loaded = CLIConfig.load()
        assert loaded.api_url == "http://custom.api"

    def test_clear_auth_preserves_output_format(self, tmp_config):
        from cli.config import CLIConfig
        cfg = CLIConfig(output_format="json", access_token="tok")
        cfg.save()
        cfg.clear_auth()
        loaded = CLIConfig.load()
        assert loaded.output_format == "json"


class TestGetConfig:
    def test_get_config_returns_cli_config_instance(self, tmp_config):
        from cli.config import CLIConfig, get_config
        cfg = get_config()
        assert isinstance(cfg, CLIConfig)
