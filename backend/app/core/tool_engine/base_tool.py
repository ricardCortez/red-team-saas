"""Abstract base class for all red team tools"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum


class ToolCategory(str, Enum):
    RECON = "recon"
    SCAN = "scan"
    EXPLOIT = "exploit"
    BRUTE_FORCE = "brute_force"
    WEB = "web"
    NETWORK = "network"
    OSINT = "osint"


@dataclass
class ToolResult:
    success: bool
    raw_output: str
    parsed_output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    exit_code: int = 0
    duration_seconds: float = 0.0
    findings: List[Dict] = field(default_factory=list)
    risk_score: float = 0.0


class BaseTool(ABC):
    name: str
    category: ToolCategory
    binary: str
    requires_root: bool = False
    default_timeout: int = 300

    @abstractmethod
    def build_command(self, target: str, options: Dict[str, Any]) -> List[str]:
        """Build command as a list of strings."""
        pass

    @abstractmethod
    def parse_output(self, raw_output: str, exit_code: int) -> Dict[str, Any]:
        """Parse raw output into a structured dict."""
        pass

    def validate_target(self, target: str) -> bool:
        """Validate the target string. Override for custom validation."""
        import re
        patterns = [
            r'^(\d{1,3}\.){3}\d{1,3}(/\d{1,2})?$',
            r'^[a-zA-Z0-9][a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}$',
            r'^https?://.+',
            r'^localhost$',
            r'^(\d{1,3}\.){3}\d{1,3}$',
        ]
        return any(re.match(p, target) for p in patterns)

    def get_risk_score(self, parsed: Dict) -> float:
        """Calculate risk score 0-10. Override for custom scoring."""
        return 0.0
