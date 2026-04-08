"""Abstract base class for all AI providers"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class AIProvider(ABC):
    """Base interface every AI provider must implement."""

    @abstractmethod
    async def test(self) -> Dict[str, Any]:
        """Check provider availability.
        Returns dict: {"available": bool, "models": list[str], "error": str|None}
        """
        ...

    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], model: str) -> str:
        """Send messages and return the assistant reply text."""
        ...

    @abstractmethod
    async def analyze_finding(self, finding: Dict[str, Any], model: str) -> Dict[str, Any]:
        """Analyze a security finding.
        Returns dict: {"severity": str, "explanation": str, "remediation": str}
        """
        ...

    def _finding_prompt(self, finding: Dict[str, Any]) -> str:
        return (
            f"You are a cybersecurity expert. Analyze this security finding and respond with JSON only.\n"
            f"Finding: {finding.get('title', '')}\n"
            f"Description: {finding.get('description', '')}\n"
            f"Host: {finding.get('host', 'unknown')}\n"
            f"Current severity: {finding.get('severity', 'unknown')}\n\n"
            f"Respond with this exact JSON structure:\n"
            f'{{"severity": "critical|high|medium|low|info", '
            f'"explanation": "brief technical explanation", '
            f'"remediation": "step-by-step remediation advice"}}'
        )
