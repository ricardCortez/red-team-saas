"""Abstract base renderer for report generation"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseRenderer(ABC):

    @abstractmethod
    def render(self, data: Dict[str, Any], report) -> bytes:
        """Return report content as bytes."""

    @abstractmethod
    def content_type(self) -> str:
        """MIME type for the generated content."""

    @abstractmethod
    def extension(self) -> str:
        """File extension without the leading dot."""
