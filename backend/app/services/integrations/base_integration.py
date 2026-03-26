"""Base integration interface — Phase 16"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional


class BaseIntegration(ABC):
    """Abstract base class for every external integration."""

    def __init__(self, auth_token: str, config: Dict[str, Any]) -> None:
        self.auth_token = auth_token
        self.config = config or {}

    # ── Interface ─────────────────────────────────────────────────────────────

    @abstractmethod
    async def test_connection(self) -> bool:
        """Verify connectivity with the external service."""

    @abstractmethod
    async def send_message(self, message: str, **kwargs) -> Dict[str, Any]:
        """Send a notification message."""

    @abstractmethod
    async def create_issue(self, title: str, description: str, **kwargs) -> Dict[str, Any]:
        """Create a ticket / issue / thread in the external service."""

    @abstractmethod
    async def get_auth_url(self) -> str:
        """Return the OAuth authorisation URL (if applicable)."""

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _format_payload(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Attach common metadata to every outbound payload."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "source": "red_team_saas",
            **data,
        }

    def _success(self, external_id: Optional[str] = None,
                 external_url: Optional[str] = None) -> Dict[str, Any]:
        result: Dict[str, Any] = {"success": True}
        if external_id:
            result["external_id"] = external_id
        if external_url:
            result["external_url"] = external_url
        return result

    def _failure(self, error: str, code: Optional[str] = None) -> Dict[str, Any]:
        result: Dict[str, Any] = {"success": False, "error": error}
        if code:
            result["error_code"] = code
        return result
