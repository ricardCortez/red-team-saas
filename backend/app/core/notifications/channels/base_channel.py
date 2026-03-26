"""Base notification channel - Phase 8"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class NotificationPayload:
    title: str
    body: str
    severity: str = "info"
    resource_id: Optional[int] = None
    extra: Optional[Dict[str, Any]] = None


class BaseChannel(ABC):
    name: str

    @abstractmethod
    def send(self, config: Dict[str, Any], payload: NotificationPayload) -> bool:
        """Send notification. Returns True if sent successfully."""
        pass

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Override to validate channel config."""
        return True
