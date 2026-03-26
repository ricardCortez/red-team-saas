"""Jira integration — Phase 16"""
from __future__ import annotations

import base64
from typing import Any, Dict, List, Optional

import aiohttp

from app.services.integrations.base_integration import BaseIntegration

_PRIORITY_MAP: Dict[str, str] = {
    "CRITICAL": "Highest",
    "HIGH":     "High",
    "MEDIUM":   "Medium",
    "LOW":      "Low",
}


class JiraIntegration(BaseIntegration):
    """Create Jira issues via the REST API v3 (Atlassian Cloud)."""

    async def test_connection(self) -> bool:
        jira_url = self.config.get("jira_url", "")
        if not jira_url:
            return False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{jira_url}/rest/api/3/myself",
                    headers=self._headers(),
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    return resp.status == 200
        except Exception:
            return False

    async def send_message(self, message: str, **kwargs) -> Dict[str, Any]:
        """Jira has no direct messaging channel; returns unsupported."""
        return self._failure("send_message not supported for Jira; use create_issue", "NOT_SUPPORTED")

    async def create_issue(
        self,
        title: str,
        description: str,
        severity: Optional[str] = None,
        cve_id: Optional[str] = None,
        assignee: Optional[str] = None,
        issue_type: str = "Bug",
        **kwargs,
    ) -> Dict[str, Any]:
        jira_url    = self.config.get("jira_url", "")
        project_key = self.config.get("project_key", "")
        if not jira_url or not project_key:
            return self._failure("jira_url and project_key must be set in config", "CONFIG_ERROR")

        labels: List[str] = ["red-team-findings"]
        if cve_id:
            labels.append(f"cve:{cve_id}")

        payload: Dict[str, Any] = {
            "fields": {
                "project":     {"key": project_key},
                "issuetype":   {"name": issue_type},
                "summary":     title,
                "description": {
                    "version": 3,
                    "type":    "doc",
                    "content": [
                        {
                            "type":    "paragraph",
                            "content": [{"type": "text", "text": description}],
                        }
                    ],
                },
                "priority": {"name": _PRIORITY_MAP.get(severity or "", "Medium")},
                "labels":   labels,
            }
        }

        if assignee:
            payload["fields"]["assignee"] = {"name": assignee}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{jira_url}/rest/api/3/issue",
                    json=payload,
                    headers=self._headers(),
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    data = await resp.json()
                    if resp.status == 201:
                        key = data.get("key", "")
                        return self._success(
                            external_id=key,
                            external_url=f"{jira_url}/browse/{key}",
                        )
                    errors = data.get("errorMessages") or data.get("errors") or {}
                    return self._failure(str(errors), str(resp.status))
        except Exception as exc:
            return self._failure(str(exc))

    async def get_auth_url(self) -> str:
        return "https://auth.atlassian.com/authorize?audience=api.atlassian.com&scope=read:jira-work+write:jira-work"

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _headers(self) -> Dict[str, str]:
        email = self.config.get("email", "")
        credential = base64.b64encode(f"{email}:{self.auth_token}".encode()).decode()
        return {
            "Authorization": f"Basic {credential}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        }
