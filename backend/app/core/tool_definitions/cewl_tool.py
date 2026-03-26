"""CeWL custom wordlist generator tool definition"""
import re
from typing import Dict, Any, List

from app.core.tool_engine.base_tool import BaseTool, ToolCategory
from app.core.tool_engine.tool_registry import ToolRegistry


@ToolRegistry.register
class CeWLTool(BaseTool):
    name = "cewl"
    category = ToolCategory.BRUTE_FORCE
    binary = "cewl"
    default_timeout = 600

    def validate_target(self, target: str) -> bool:
        """Target must be a URL."""
        import re as _re
        return bool(_re.match(r'^https?://.+', target))

    def build_command(self, target: str, options: Dict[str, Any]) -> List[str]:
        cmd = ["cewl"]

        # Crawl depth
        depth = options.get("depth", 2)
        cmd += ["-d", str(depth)]

        # Minimum word length
        min_length = options.get("min_length", 5)
        cmd += ["-m", str(min_length)]

        # Include numbers
        if options.get("with_numbers", False):
            cmd += ["-n"]

        # Include email addresses
        if options.get("with_emails", False):
            cmd += ["-e"]

        # Follow offsite links
        if options.get("offsite", False):
            cmd += ["-o"]

        # User agent
        if options.get("user_agent"):
            cmd += ["-a", options["user_agent"]]

        # Output file (optional — we capture stdout)
        if options.get("output_file"):
            cmd += ["-w", options["output_file"]]

        # Lowercase
        if options.get("lowercase", True):
            cmd += ["--lowercase"]

        # Count occurrences
        if options.get("count", False):
            cmd += ["-c"]

        cmd.append(target)
        return cmd

    def parse_output(self, raw_output: str, exit_code: int) -> Dict[str, Any]:
        words: List[str] = []
        findings: List[Dict] = []

        for line in raw_output.splitlines():
            line = line.strip()
            if line and not line.startswith("CeWL") and not line.startswith("Notice"):
                # Strip count if present (e.g. "password, 42")
                word = re.sub(r',\s*\d+$', '', line).strip()
                if word:
                    words.append(word)

        if words:
            findings.append({
                "severity": "info",
                "title": "Custom wordlist generated",
                "description": f"Generated {len(words)} words from target site",
            })

        return {
            "words": words,
            "findings": findings,
            "total_words": len(words),
        }

    def get_risk_score(self, parsed: Dict) -> float:
        total = parsed.get("total_words", 0)
        if total >= 100:
            return 3.0
        elif total >= 10:
            return 1.0
        return 0.0
