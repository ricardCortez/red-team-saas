"""HTTP client wrapper around httpx for the Red Team SaaS API"""
import json as _json
from typing import Any, Dict, Optional

import httpx
import typer

from cli.config import CLIConfig, get_config


class APIClient:
    def __init__(self, config: Optional[CLIConfig] = None):
        self.config = config or get_config()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.config.access_token:
            headers["Authorization"] = f"Bearer {self.config.access_token}"
        return headers

    def _url(self, path: str) -> str:
        base = self.config.api_url.rstrip("/")
        return f"{base}/{path.lstrip('/')}"

    def _handle_response(self, resp: httpx.Response) -> Any:
        if resp.status_code == 401:
            if self._refresh_token():
                return None  # caller should retry
            typer.echo("Session expired. Run: redteam auth login", err=True)
            raise typer.Exit(1)
        if resp.status_code == 403:
            try:
                detail = resp.json().get("detail", "")
            except Exception:
                detail = resp.text
            typer.echo(f"Permission denied: {detail}", err=True)
            raise typer.Exit(1)
        if resp.status_code == 404:
            try:
                detail = resp.json().get("detail", "")
            except Exception:
                detail = resp.text
            typer.echo(f"Not found: {detail}", err=True)
            raise typer.Exit(1)
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            typer.echo(f"Error {resp.status_code}: {detail}", err=True)
            raise typer.Exit(1)
        if resp.status_code == 204:
            return None
        return resp.json()

    def _refresh_token(self) -> bool:
        if not self.config.refresh_token:
            return False
        try:
            resp = httpx.post(
                self._url("/auth/refresh"),
                json={"refresh_token": self.config.refresh_token},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                self.config.access_token = data["access_token"]
                self.config.refresh_token = data.get(
                    "refresh_token", self.config.refresh_token
                )
                self.config.save()
                return True
        except Exception:
            pass
        return False

    # ------------------------------------------------------------------
    # HTTP verbs
    # ------------------------------------------------------------------

    def get(self, path: str, params: Optional[Dict] = None) -> Any:
        resp = httpx.get(
            self._url(path), headers=self._headers(), params=params, timeout=30
        )
        return self._handle_response(resp)

    def post(self, path: str, data: Optional[Dict] = None) -> Any:
        resp = httpx.post(
            self._url(path), headers=self._headers(), json=data, timeout=30
        )
        return self._handle_response(resp)

    def patch(self, path: str, data: Optional[Dict] = None) -> Any:
        resp = httpx.patch(
            self._url(path), headers=self._headers(), json=data, timeout=30
        )
        return self._handle_response(resp)

    def delete(self, path: str) -> Any:
        resp = httpx.delete(self._url(path), headers=self._headers(), timeout=30)
        return self._handle_response(resp)

    def download(self, path: str, dest: str) -> int:
        """Download a file to *dest*. Returns bytes written."""
        with httpx.stream(
            "GET", self._url(path), headers=self._headers(), timeout=60
        ) as resp:
            if resp.status_code >= 400:
                typer.echo(f"Download failed: {resp.status_code}", err=True)
                raise typer.Exit(1)
            total = 0
            with open(dest, "wb") as fh:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    fh.write(chunk)
                    total += len(chunk)
        return total

    def stream_sse(self, path: str):
        """Yield parsed JSON objects from an SSE endpoint."""
        with httpx.stream(
            "GET", self._url(path), headers=self._headers(), timeout=None
        ) as resp:
            for line in resp.iter_lines():
                if line.startswith("data:"):
                    raw = line[5:].strip()
                    try:
                        yield _json.loads(raw)
                    except Exception:
                        yield {"line": raw}


def get_client() -> APIClient:
    """Return an authenticated APIClient or exit with an error."""
    config = get_config()
    if not config.access_token:
        typer.echo("Not authenticated. Run: redteam auth login", err=True)
        raise typer.Exit(1)
    return APIClient(config)
