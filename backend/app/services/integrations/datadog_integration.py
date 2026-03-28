"""Datadog integration - metrics and events for observability"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict

import aiohttp

from app.services.integrations.base_integration import BaseIntegration

logger = logging.getLogger(__name__)


class DatadogIntegration(BaseIntegration):
    """Send metrics, events, and findings to Datadog."""

    def __init__(self, auth_token: str, config: Dict[str, Any]) -> None:
        super().__init__(auth_token, config)
        self.api_key = auth_token
        self.app_key = config.get("app_key", "")
        self.site = config.get("site", "datadoghq.com")
        self.base_url = f"https://api.{self.site}"
        self.tags = config.get("tags", ["service:redteam-saas"])

    def _headers(self) -> Dict[str, str]:
        return {
            "DD-API-KEY": self.api_key,
            "DD-APPLICATION-KEY": self.app_key,
            "Content-Type": "application/json",
        }

    async def test_connection(self) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/validate",
                    headers=self._headers(),
                ) as resp:
                    return resp.status == 200
        except Exception as exc:
            logger.error(f"Datadog test failed: {exc}")
            return False

    async def send_message(self, message: str, **kwargs) -> Dict[str, Any]:
        return await self._post_event(
            title=kwargs.get("title", "Red Team Alert"),
            text=message,
            alert_type=self._map_severity(kwargs.get("severity", "info")),
            tags=self.tags,
        )

    async def create_issue(self, title: str, description: str, **kwargs) -> Dict[str, Any]:
        return await self._post_event(
            title=title,
            text=description,
            alert_type=self._map_severity(kwargs.get("severity", "medium")),
            tags=self.tags + [
                f"severity:{kwargs.get('severity', 'medium')}",
                f"cve:{kwargs.get('cve_id', 'none')}",
            ],
        )

    async def sync_findings(self, findings: list, **kwargs) -> Dict[str, Any]:
        results = []
        for finding in findings:
            result = await self.create_issue(
                title=finding.get("title", ""),
                description=finding.get("description", ""),
                severity=finding.get("severity", "info"),
                cve_id=finding.get("cve_id"),
            )
            results.append(result)
        # Also send aggregate metric
        await self._post_metric("redteam.findings.count", len(findings))
        return {"sent": len(results)}

    async def send_metric(self, metric_name: str, value: float, tags: list | None = None) -> Dict[str, Any]:
        return await self._post_metric(metric_name, value, tags)

    async def _post_event(self, title: str, text: str, alert_type: str = "info", tags: list | None = None) -> Dict[str, Any]:
        payload = {
            "title": title,
            "text": text,
            "alert_type": alert_type,
            "tags": tags or self.tags,
            "source_type_name": "redteam-saas",
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/v1/events",
                    headers=self._headers(),
                    json=payload,
                ) as resp:
                    return await resp.json()
        except Exception as exc:
            logger.error(f"Datadog event failed: {exc}")
            return {"error": str(exc)}

    async def _post_metric(self, name: str, value: float, tags: list | None = None) -> Dict[str, Any]:
        now = int(time.time())
        payload = {
            "series": [{
                "metric": name,
                "type": 1,  # gauge
                "points": [[now, value]],
                "tags": tags or self.tags,
            }],
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/v1/series",
                    headers=self._headers(),
                    json=payload,
                ) as resp:
                    return await resp.json()
        except Exception as exc:
            logger.error(f"Datadog metric failed: {exc}")
            return {"error": str(exc)}

    @staticmethod
    def _map_severity(severity: str) -> str:
        return {"critical": "error", "high": "error", "medium": "warning", "low": "info", "info": "info"}.get(severity, "info")
