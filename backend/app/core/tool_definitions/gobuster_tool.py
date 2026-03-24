"""Gobuster directory/file brute-force tool definition"""
import re
from typing import Dict, Any, List

from app.core.tool_engine.base_tool import BaseTool, ToolCategory
from app.core.tool_engine.tool_registry import ToolRegistry


@ToolRegistry.register
class GobusterTool(BaseTool):
    name = "gobuster"
    category = ToolCategory.WEB
    binary = "gobuster"
    default_timeout = 600

    def build_command(self, target: str, options: Dict[str, Any]) -> List[str]:
        mode = options.get("mode", "dir")
        wordlist = options.get("wordlist", "/usr/share/wordlists/dirb/common.txt")

        cmd = ["gobuster", mode, "-u", target, "-w", wordlist, "-q"]

        if options.get("extensions"):
            exts = options["extensions"]
            if isinstance(exts, list):
                exts = ",".join(exts)
            cmd += ["-x", exts]
        if options.get("threads"):
            cmd += ["-t", str(options["threads"])]
        if options.get("status_codes"):
            cmd += ["-s", str(options["status_codes"])]
        if options.get("no_tls_validation"):
            cmd += ["-k"]

        return cmd

    def parse_output(self, raw_output: str, exit_code: int) -> Dict[str, Any]:
        findings: List[Dict] = []
        discovered_paths: List[str] = []

        pattern = re.compile(r'^(/[^\s]*)\s+\(Status:\s*(\d+)\)', re.MULTILINE)
        for match in pattern.finditer(raw_output):
            path = match.group(1)
            status = int(match.group(2))
            discovered_paths.append(path)

            severity = "info"
            if status in (200, 204):
                severity = "low"
            elif status in (301, 302):
                severity = "info"
            elif status == 403:
                severity = "medium"

            findings.append({
                "severity": severity,
                "title": f"Path discovered: {path}",
                "description": f"HTTP {status} at {path}",
            })

        return {
            "findings": findings,
            "discovered_paths": discovered_paths,
            "total_paths": len(discovered_paths),
        }

    def get_risk_score(self, parsed: Dict) -> float:
        total = parsed.get("total_paths", 0)
        if total > 50:
            return 6.0
        elif total > 10:
            return 4.0
        elif total > 0:
            return 2.0
        return 0.0
