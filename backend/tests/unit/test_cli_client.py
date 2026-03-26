"""Unit tests for cli/client.py"""
import pytest
from unittest.mock import MagicMock, patch, mock_open
import httpx
import typer


@pytest.fixture
def cfg():
    from cli.config import CLIConfig
    return CLIConfig(
        api_url="http://test.local/api/v1",
        access_token="test_token",
        refresh_token="refresh_token",
        username="testuser",
    )


@pytest.fixture
def client(cfg):
    from cli.client import APIClient
    return APIClient(config=cfg)


class TestAPIClientHeaders:
    def test_bearer_token_in_headers(self, client):
        headers = client._headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_token"

    def test_content_type_in_headers(self, client):
        headers = client._headers()
        assert headers["Content-Type"] == "application/json"

    def test_no_auth_header_when_no_token(self, cfg):
        cfg.access_token = None
        from cli.client import APIClient
        c = APIClient(config=cfg)
        headers = c._headers()
        assert "Authorization" not in headers


class TestAPIClientURL:
    def test_url_construction(self, client):
        assert client._url("/projects") == "http://test.local/api/v1/projects"

    def test_url_strips_leading_slash(self, client):
        assert client._url("projects") == "http://test.local/api/v1/projects"

    def test_url_strips_trailing_slash_from_base(self, cfg):
        cfg.api_url = "http://test.local/api/v1/"
        from cli.client import APIClient
        c = APIClient(config=cfg)
        assert c._url("/projects") == "http://test.local/api/v1/projects"


class TestAPIClientHandleResponse:
    def test_401_triggers_refresh(self, client, monkeypatch):
        monkeypatch.setattr(client, "_refresh_token", lambda: True)
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        result = client._handle_response(mock_resp)
        assert result is None  # caller should retry

    def test_401_without_refresh_exits(self, client, monkeypatch):
        monkeypatch.setattr(client, "_refresh_token", lambda: False)
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        with pytest.raises(typer.Exit):
            client._handle_response(mock_resp)

    def test_403_exits(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.json.return_value = {"detail": "Forbidden"}
        with pytest.raises(typer.Exit):
            client._handle_response(mock_resp)

    def test_404_exits(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {"detail": "Not found"}
        with pytest.raises(typer.Exit):
            client._handle_response(mock_resp)

    def test_500_exits(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.json.return_value = {"detail": "Internal error"}
        with pytest.raises(typer.Exit):
            client._handle_response(mock_resp)

    def test_200_returns_json(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": 1, "name": "test"}
        result = client._handle_response(mock_resp)
        assert result == {"id": 1, "name": "test"}

    def test_204_returns_none(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        result = client._handle_response(mock_resp)
        assert result is None


class TestAPIClientRefreshToken:
    def test_refresh_success_updates_config(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "access_token": "new_token",
            "refresh_token": "new_refresh",
        }
        with patch("httpx.post", return_value=mock_resp):
            with patch.object(client.config, "save"):
                result = client._refresh_token()
        assert result is True
        assert client.config.access_token == "new_token"

    def test_refresh_fails_returns_false(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        with patch("httpx.post", return_value=mock_resp):
            result = client._refresh_token()
        assert result is False

    def test_refresh_no_token_returns_false(self, cfg):
        cfg.refresh_token = None
        from cli.client import APIClient
        c = APIClient(config=cfg)
        assert c._refresh_token() is False


class TestAPIClientHTTPMethods:
    def test_get_calls_httpx_get(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"items": []}
        with patch("httpx.get", return_value=mock_resp) as mock_get:
            result = client.get("/projects")
        mock_get.assert_called_once()
        assert result == {"items": []}

    def test_post_calls_httpx_post(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"id": 1}
        with patch("httpx.post", return_value=mock_resp) as mock_post:
            result = client.post("/projects", {"name": "Test"})
        mock_post.assert_called_once()
        assert result["id"] == 1

    def test_patch_calls_httpx_patch(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": 1}
        with patch("httpx.patch", return_value=mock_resp):
            result = client.patch("/findings/1", {"status": "open"})
        assert result["id"] == 1

    def test_delete_204_returns_none(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        with patch("httpx.delete", return_value=mock_resp):
            result = client.delete("/executions/1")
        assert result is None


class TestGetClientHelper:
    def test_get_client_no_token_exits(self, tmp_path, monkeypatch):
        monkeypatch.setattr("cli.config.CONFIG_DIR", tmp_path / ".redteam")
        monkeypatch.setattr("cli.config.CONFIG_FILE", tmp_path / ".redteam" / "config.json")
        from cli.client import get_client
        with pytest.raises(typer.Exit):
            get_client()

    def test_get_client_with_token_returns_client(self, monkeypatch):
        from cli.config import CLIConfig
        mock_cfg = CLIConfig(access_token="token123")
        monkeypatch.setattr("cli.client.get_config", lambda: mock_cfg)
        from cli.client import APIClient, get_client
        c = get_client()
        assert isinstance(c, APIClient)
        assert c.config.access_token == "token123"


class TestAPIClientDownload:
    def test_download_writes_file(self, client, tmp_path):
        dest = str(tmp_path / "report.pdf")
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_context)
        mock_context.__exit__ = MagicMock(return_value=False)
        mock_context.status_code = 200
        mock_context.iter_bytes.return_value = [b"chunk1", b"chunk2"]
        with patch("httpx.stream", return_value=mock_context):
            size = client.download("/reports/1/download", dest)
        assert size == len(b"chunk1") + len(b"chunk2")
