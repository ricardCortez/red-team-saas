"""Generic webhook integration — Phase 16"""
from __future__ import annotations

from typing import Any, Dict, Optional

import aiohttp

from app.services.integrations.base_integration import BaseIntegration


class WebhookIntegration(BaseIntegration):
    """Send arbitrary JSON payloads to any HTTP endpoint."""

    async def test_connection(self) -> bool:
        webhook_url = self.config.get("webhook_url", "")
        if not webhook_url:
            return False
        payload = self._format_payload({"test": True, "message": "Connectivity test from Red Team SaaS"})
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=payload,
                    headers=self._headers(),
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    return 200 <= resp.status < 300
        except Exception:
            return False

    async def send_message(self, message: str, **kwargs) -> Dict[str, Any]:
        webhook_url = self.config.get("webhook_url", "")
        if not webhook_url:
            return self._failure("webhook_url not configured", "CONFIG_ERROR")

        payload = self._format_payload({"message": message, "metadata": kwargs})
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=payload,
                    headers=self._headers(),
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    body = await resp.text()
                    if 200 <= resp.status < 300:
                        return {**self._success(external_id=str(resp.status)), "status_code": resp.status}
                    return self._failure(f"HTTP {resp.status}: {body[:200]}", str(resp.status))
        except Exception as exc:
            return self._failure(str(exc))

    async def create_issue(self, title: str, description: str, **kwargs) -> Dict[str, Any]:
        return await self.send_message(f"**{title}**\n{description}", **kwargs)

    async def get_auth_url(self) -> str:
        return "N/A — configure webhook_url directly in the integration config"

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        # Optional bearer auth
        secret = self.config.get("secret") or self.auth_token
        if secret:
            headers["Authorization"] = f"Bearer {secret}"
        return headers
