"""Webhook notification channel - Phase 8"""
import hmac
import hashlib
import json
import urllib.request
import urllib.error
from app.core.notifications.channels.base_channel import BaseChannel, NotificationPayload
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class WebhookChannel(BaseChannel):
    name = "webhook"

    def send(self, config: Dict[str, Any], payload: NotificationPayload) -> bool:
        url = config.get("url")
        secret = config.get("secret", "")
        method = config.get("method", "POST").upper()

        if not url:
            logger.warning("Webhook channel: no URL configured")
            return False

        body = json.dumps({
            "title": payload.title,
            "body": payload.body,
            "severity": payload.severity,
            "resource_id": payload.resource_id,
            "extra": payload.extra or {},
        }).encode()

        headers = {"Content-Type": "application/json"}

        # HMAC signature if secret provided
        if secret:
            sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
            headers["X-RedTeam-Signature"] = f"sha256={sig}"

        try:
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=10) as resp:
                return 200 <= resp.status < 300
        except urllib.error.URLError as e:
            logger.error(f"Webhook failed [{url}]: {e}")
            return False

    def validate_config(self, config: Dict[str, Any]) -> bool:
        url = config.get("url", "")
        return url.startswith("http://") or url.startswith("https://")
