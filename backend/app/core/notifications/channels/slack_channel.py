"""Slack notification channel - Phase 8"""
import json
import urllib.request
import urllib.error
from app.core.notifications.channels.base_channel import BaseChannel, NotificationPayload
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

SEVERITY_COLORS = {
    "critical": "#c0392b",
    "high": "#e67e22",
    "medium": "#f1c40f",
    "low": "#27ae60",
    "info": "#2980b9",
}


class SlackChannel(BaseChannel):
    name = "slack"

    def send(self, config: Dict[str, Any], payload: NotificationPayload) -> bool:
        webhook_url = config.get("webhook_url")
        if not webhook_url:
            logger.warning("Slack channel: no webhook_url configured")
            return False

        color = SEVERITY_COLORS.get(payload.severity.lower(), "#888")
        message = {
            "attachments": [
                {
                    "color": color,
                    "title": f"Red Team Alert: {payload.title}",
                    "text": payload.body,
                    "fields": [
                        {"title": "Severity", "value": payload.severity.upper(), "short": True}
                    ],
                    "footer": "Red Team SaaS",
                }
            ]
        }

        body = json.dumps(message).encode()
        req = urllib.request.Request(
            webhook_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except urllib.error.URLError as e:
            logger.error(f"Slack send failed: {e}")
            return False

    def validate_config(self, config: Dict[str, Any]) -> bool:
        url = config.get("webhook_url", "")
        return "hooks.slack.com" in url or url.startswith("https://")
