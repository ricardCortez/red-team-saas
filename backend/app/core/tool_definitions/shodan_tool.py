"""Shodan OSINT tool definition - searches Shodan via API"""
import json
from typing import Dict, Any, List

from app.core.tool_engine.base_tool import BaseTool, ToolCategory, ToolResult
from app.core.tool_engine.tool_registry import ToolRegistry


@ToolRegistry.register
class ShodanTool(BaseTool):
    name = "shodan"
    category = ToolCategory.OSINT
    binary = "shodan"  # Shodan CLI
    default_timeout = 120

    def build_command(self, target: str, options: Dict[str, Any]) -> List[str]:
        mode = options.get("mode", "host")

        if mode == "host":
            return ["shodan", "host", target]
        elif mode == "search":
            query = options.get("query", target)
            limit = str(options.get("limit", 20))
            return ["shodan", "search", "--limit", limit, query]
        elif mode == "scan":
            return ["shodan", "scan", "submit", target]
        elif mode == "honeyscore":
            return ["shodan", "honeyscore", target]
        elif mode == "info":
            return ["shodan", "info"]
        else:
            return ["shodan", "host", target]

    def parse_output(self, raw_output: str, exit_code: int) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "hosts": [],
            "ports": [],
            "services": [],
            "vulnerabilities": [],
            "summary": {},
        }

        if exit_code != 0:
            result["error"] = raw_output.strip()
            return result

        # Parse host info output
        lines = raw_output.strip().split("\n")
        current_host: Dict[str, Any] = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if ":" in line and not line.startswith(" "):
                key, _, value = line.partition(":")
                key = key.strip().lower()
                value = value.strip()

                if key == "ip":
                    if current_host:
                        result["hosts"].append(current_host)
                    current_host = {"ip": value, "ports": [], "vulns": []}
                elif key in ("hostnames", "hostname"):
                    current_host["hostnames"] = [h.strip() for h in value.split(",")]
                elif key == "country":
                    current_host["country"] = value
                elif key == "organization" or key == "org":
                    current_host["organization"] = value
                elif key == "os":
                    current_host["os"] = value
                elif key == "ports" or key == "port":
                    ports = [p.strip() for p in value.split(",")]
                    current_host["ports"] = ports
                    result["ports"].extend(ports)
                elif key == "vulns":
                    vulns = [v.strip() for v in value.split(",")]
                    current_host["vulns"] = vulns
                    result["vulnerabilities"].extend(vulns)

            # Service line (port/proto)
            if line and "/" in line and line[0].isdigit():
                parts = line.split()
                service = {"port_proto": parts[0]}
                if len(parts) > 1:
                    service["banner"] = " ".join(parts[1:])
                result["services"].append(service)

        if current_host:
            result["hosts"].append(current_host)

        result["summary"] = {
            "total_hosts": len(result["hosts"]),
            "total_ports": len(set(result["ports"])),
            "total_vulns": len(set(result["vulnerabilities"])),
            "total_services": len(result["services"]),
        }

        # Build findings from vulnerabilities
        for vuln in set(result["vulnerabilities"]):
            result.setdefault("findings_data", []).append({
                "title": f"Shodan: Vulnerability {vuln} detected",
                "severity": "high",
                "description": f"Shodan reported known vulnerability {vuln} on target.",
                "cve_id": vuln if vuln.startswith("CVE-") else None,
                "source": "shodan",
            })

        return result
