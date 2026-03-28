"""Splunk SIEM integration - sends findings and events to Splunk HEC"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

import aiohttp

from app.services.integrations.base_integration import BaseIntegration

logger = logging.getLogger(__name__)


class SplunkIntegration(BaseIntegration):
    """Push events and findings to Splunk via HTTP Event Collector (HEC)."""

    def __init__(self, auth_token: str, config: Dict[str, Any]) -> None:
        super().__init__(auth_token, config)
        self.hec_url = config.get("hec_url", "https://localhost:8088/services/collector/event")
        self.index = config.get("index", "redteam")
        self.source = config.get("source", "redteam-saas")
        self.sourcetype = config.get("sourcetype", "_json")
        self.verify_ssl = config.get("verify_ssl", False)

    async def test_connection(self) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Splunk {self.auth_token}"}
                payload = {"event": {"test": True, "source": "redteam-saas"}}
                async with session.post(
                    self.hec_url, headers=headers, json=payload,
                    ssl=self.verify_ssl,
                ) as resp:
                    return resp.status == 200
        except Exception as exc:
            logger.error(f"Splunk connection test failed: {exc}")
            return False

    async def send_message(self, message: str, **kwargs) -> Dict[str, Any]:
        return await self._send_event({
            "message": message,
            "severity": kwargs.get("severity", "info"),
            "event_type": "notification",
            **kwargs,
        })

    async def create_issue(self, title: str, description: str, **kwargs) -> Dict[str, Any]:
        return await self._send_event({
            "event_type": "finding",
            "title": title,
            "description": description,
            "severity": kwargs.get("severity", "medium"),
            "cve_id": kwargs.get("cve_id"),
            "cvss_score": kwargs.get("cvss_score"),
            "scan_id": kwargs.get("scan_id"),
            **kwargs,
        })

    async def sync_findings(self, findings: list, **kwargs) -> Dict[str, Any]:
        results = []
        for finding in findings:
            result = await self._send_event({
                "event_type": "finding",
                "title": finding.get("title", ""),
                "description": finding.get("description", ""),
                "severity": finding.get("severity", "info"),
                "cve_id": finding.get("cve_id"),
                "cvss_score": finding.get("cvss_score"),
                "source_tool": finding.get("source", ""),
            })
            results.append(result)
        return {"sent": len(results), "results": results}

    async def _send_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        event_data["timestamp"] = datetime.now(timezone.utc).isoformat()
        payload = {
            "event": event_data,
            "index": self.index,
            "source": self.source,
            "sourcetype": self.sourcetype,
        }

        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Splunk {self.auth_token}"}
                async with session.post(
                    self.hec_url, headers=headers, json=payload,
                    ssl=self.verify_ssl,
                ) as resp:
                    body = await resp.text()
                    return {"status": resp.status, "response": body}
        except Exception as exc:
            logger.error(f"Splunk event send failed: {exc}")
            return {"status": 500, "error": str(exc)}
