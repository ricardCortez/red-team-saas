"""PagerDuty integration - incident management for critical findings"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict

import aiohttp

from app.services.integrations.base_integration import BaseIntegration

logger = logging.getLogger(__name__)

PAGERDUTY_EVENTS_URL = "https://events.pagerduty.com/v2/enqueue"

SEVERITY_MAP = {
    "critical": "critical",
    "high": "error",
    "medium": "warning",
    "low": "info",
    "info": "info",
}


class PagerDutyIntegration(BaseIntegration):
    """Create PagerDuty incidents from critical security findings."""

    def __init__(self, auth_token: str, config: Dict[str, Any]) -> None:
        super().__init__(auth_token, config)
        # auth_token is the PagerDuty Events API v2 routing key
        self.routing_key = auth_token
        self.source = config.get("source", "redteam-saas")

    async def test_connection(self) -> bool:
        try:
            result = await self._send_event(
                summary="Red Team SaaS - Connection Test",
                severity="info",
                event_action="trigger",
                dedup_key="redteam-saas-test",
            )
            # Resolve the test incident immediately
            if result.get("status") == "success":
                await self._send_event(
                    summary="Red Team SaaS - Test resolved",
                    severity="info",
                    event_action="resolve",
                    dedup_key="redteam-saas-test",
                )
            return result.get("status") == "success"
        except Exception as exc:
            logger.error(f"PagerDuty test failed: {exc}")
            return False

    async def send_message(self, message: str, **kwargs) -> Dict[str, Any]:
        severity = kwargs.get("severity", "info")
        return await self._send_event(
            summary=message,
            severity=severity,
            event_action="trigger",
            dedup_key=kwargs.get("dedup_key"),
            custom_details=kwargs,
        )

    async def create_issue(self, title: str, description: str, **kwargs) -> Dict[str, Any]:
        severity = kwargs.get("severity", "medium")
        return await self._send_event(
            summary=title,
            severity=severity,
            event_action="trigger",
            dedup_key=kwargs.get("dedup_key"),
            custom_details={
                "description": description,
                "cve_id": kwargs.get("cve_id"),
                "cvss_score": kwargs.get("cvss_score"),
                "scan_id": kwargs.get("scan_id"),
                "remediation": kwargs.get("remediation"),
            },
        )

    async def sync_findings(self, findings: list, **kwargs) -> Dict[str, Any]:
        results = []
        for finding in findings:
            if finding.get("severity") in ("critical", "high"):
                result = await self.create_issue(
                    title=finding.get("title", ""),
                    description=finding.get("description", ""),
                    severity=finding.get("severity", "high"),
                    cve_id=finding.get("cve_id"),
                    dedup_key=f"redteam-finding-{finding.get('id', '')}",
                )
                results.append(result)
        return {"sent": len(results), "results": results}

    async def _send_event(
        self, summary: str, severity: str, event_action: str = "trigger",
        dedup_key: str | None = None, custom_details: Dict | None = None,
    ) -> Dict[str, Any]:
        payload = {
            "routing_key": self.routing_key,
            "event_action": event_action,
            "dedup_key": dedup_key or f"redteam-{datetime.now(timezone.utc).timestamp()}",
            "payload": {
                "summary": summary[:1024],
                "severity": SEVERITY_MAP.get(severity, "info"),
                "source": self.source,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "custom_details": custom_details or {},
            },
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(PAGERDUTY_EVENTS_URL, json=payload) as resp:
                    body = await resp.json()
                    return body
        except Exception as exc:
            logger.error(f"PagerDuty event failed: {exc}")
            return {"status": "error", "message": str(exc)}
