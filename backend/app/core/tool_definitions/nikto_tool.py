"""Nikto web vulnerability scanner tool definition"""
import re
from typing import Dict, Any, List

from app.core.tool_engine.base_tool import BaseTool, ToolCategory
from app.core.tool_engine.tool_registry import ToolRegistry


@ToolRegistry.register
class NiktoTool(BaseTool):
    name = "nikto"
    category = ToolCategory.WEB
    binary = "nikto"
    default_timeout = 600

    def build_command(self, target: str, options: Dict[str, Any]) -> List[str]:
        cmd = ["nikto", "-h", target, "-Format", "txt"]

        if options.get("port"):
            cmd += ["-p", str(options["port"])]
        if options.get("ssl") or target.startswith("https://"):
            cmd += ["-ssl"]
        if options.get("tuning"):
            cmd += ["-Tuning", str(options["tuning"])]
        if options.get("output"):
            cmd += ["-o", options["output"]]

        return cmd

    def parse_output(self, raw_output: str, exit_code: int) -> Dict[str, Any]:
        findings: List[Dict] = []
        vulnerabilities: List[str] = []

        for line in raw_output.splitlines():
            if line.startswith("+ ") and "OSVDB" not in line and "Server:" not in line:
                findings.append({
                    "severity": "medium",
                    "title": "Nikto finding",
                    "description": line.lstrip("+ "),
                })
            if "OSVDB-" in line:
                osvdb_match = re.search(r'OSVDB-(\d+)', line)
                if osvdb_match:
                    vulnerabilities.append(f"OSVDB-{osvdb_match.group(1)}: {line}")
                    findings.append({
                        "severity": "high",
                        "title": f"OSVDB-{osvdb_match.group(1)}",
                        "description": line,
                    })

        return {
            "findings": findings,
            "vulnerabilities": vulnerabilities,
            "total_findings": len(findings),
        }

    def get_risk_score(self, parsed: Dict) -> float:
        total = parsed.get("total_findings", 0)
        vulns = len(parsed.get("vulnerabilities", []))
        if vulns > 5:
            return 8.0
        elif vulns > 0:
            return 6.0
        elif total > 10:
            return 4.0
        elif total > 0:
            return 2.0
        return 0.0
