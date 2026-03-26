"""Slack integration — Phase 16"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import aiohttp

from app.services.integrations.base_integration import BaseIntegration

_SLACK_API = "https://slack.com/api"

_SEVERITY_COLORS: Dict[str, str] = {
    "CRITICAL": "#FF0000",
    "HIGH":     "#FF6600",
    "MEDIUM":   "#FFCC00",
    "LOW":      "#00CC00",
}


class SlackIntegration(BaseIntegration):
    """Send messages / threads to Slack via the Web API (OAuth Bot token)."""

    async def test_connection(self) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{_SLACK_API}/auth.test",
                    headers=self._headers(),
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    data = await resp.json()
                    return bool(data.get("ok"))
        except Exception:
            return False

    async def send_message(
        self,
        message: str,
        channel: Optional[str] = None,
        severity: Optional[str] = None,
        blocks: Optional[List[Dict]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        target = channel or self.config.get("default_channel", "#findings")
        payload: Dict[str, Any] = {"channel": target, "text": message}

        if blocks:
            payload["blocks"] = blocks
        elif severity:
            payload["blocks"] = self._severity_blocks(message, severity)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{_SLACK_API}/chat.postMessage",
                    json=payload,
                    headers=self._headers(),
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    data = await resp.json()
                    if data.get("ok"):
                        return self._success(
                            external_id=data.get("ts"),
                            external_url=f"https://slack.com/archives/{target}/p{data.get('ts', '').replace('.', '')}",
                        )
                    return self._failure(data.get("error", "unknown_error"))
        except Exception as exc:
            return self._failure(str(exc))

    async def create_issue(
        self,
        title: str,
        description: str,
        severity: Optional[str] = None,
        cve_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """In Slack, an 'issue' becomes a rich message thread in the findings channel."""
        parts = [f":rotating_light: *{title}*", description]
        if cve_id:
            parts.append(f"CVE: `{cve_id}`")
        message = "\n".join(parts)
        return await self.send_message(message, severity=severity)

    async def get_auth_url(self) -> str:
        client_id = self.config.get("client_id", "YOUR_CLIENT_ID")
        return (
            f"https://slack.com/oauth/v2/authorize"
            f"?client_id={client_id}"
            f"&scope=chat:write,channels:read"
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
        }

    def _severity_blocks(self, message: str, severity: str) -> List[Dict]:
        color = _SEVERITY_COLORS.get(severity.upper(), "#808080")
        return [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": message},
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View Details"},
                    "action_id": "view_finding",
                    "style": "danger" if severity.upper() in ("CRITICAL", "HIGH") else "primary",
                },
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"Severity: *{severity}*  |  color: {color}"}
                ],
            },
        ]
