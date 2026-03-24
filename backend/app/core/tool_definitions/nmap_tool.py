"""Nmap tool definition"""
import re
import xml.etree.ElementTree as ET
from typing import Dict, Any, List

from app.core.tool_engine.base_tool import BaseTool, ToolCategory
from app.core.tool_engine.tool_registry import ToolRegistry


@ToolRegistry.register
class NmapTool(BaseTool):
    name = "nmap"
    category = ToolCategory.SCAN
    binary = "nmap"
    default_timeout = 600

    SCAN_PROFILES = {
        "quick":    ["-T4", "-F"],
        "standard": ["-T4", "-sV", "-sC", "-O"],
        "full":     ["-T4", "-sV", "-sC", "-O", "-p-"],
        "stealth":  ["-T2", "-sS", "-sV"],
        "udp":      ["-sU", "--top-ports", "100"],
    }

    def build_command(self, target: str, options: Dict[str, Any]) -> List[str]:
        profile = options.get("profile", "standard")
        flags = self.SCAN_PROFILES.get(profile, self.SCAN_PROFILES["standard"])
        cmd = ["nmap"] + flags + ["-oX", "-"]

        if options.get("ports"):
            cmd += ["-p", str(options["ports"])]
        if options.get("scripts"):
            cmd += ["--script", ",".join(options["scripts"])]
        if options.get("exclude_ports"):
            cmd += ["--exclude-ports", str(options["exclude_ports"])]

        cmd.append(target)
        return cmd

    def parse_output(self, raw_output: str, exit_code: int) -> Dict[str, Any]:
        findings: List[Dict] = []
        hosts: List[Dict] = []

        try:
            xml_match = re.search(r'<\?xml.*</nmaprun>', raw_output, re.DOTALL)
            if not xml_match:
                return {"raw": raw_output, "findings": [], "hosts": [], "total_open_ports": 0}

            root = ET.fromstring(xml_match.group())

            for host in root.findall("host"):
                host_data: Dict[str, Any] = {"ports": [], "os": None, "state": "unknown"}

                status = host.find("status")
                if status is not None:
                    host_data["state"] = status.get("state", "unknown")

                host_ip = "unknown"
                for addr in host.findall("address"):
                    if addr.get("addrtype") == "ipv4":
                        host_ip = addr.get("addr", "unknown")
                        host_data["ip"] = host_ip

                ports_elem = host.find("ports")
                if ports_elem:
                    for port in ports_elem.findall("port"):
                        state_elem = port.find("state")
                        service_elem = port.find("service")
                        if state_elem is not None and state_elem.get("state") == "open":
                            port_info = {
                                "port": port.get("portid"),
                                "protocol": port.get("protocol"),
                                "service": service_elem.get("name", "unknown") if service_elem else "unknown",
                                "version": service_elem.get("product", "") if service_elem else "",
                            }
                            host_data["ports"].append(port_info)
                            findings.append({
                                "severity": "info",
                                "title": f"Open port {port_info['port']}/{port_info['protocol']}",
                                "description": f"Service: {port_info['service']} {port_info['version']}",
                                "host": host_ip,
                            })

                os_elem = host.find("os")
                if os_elem:
                    osmatch = os_elem.find("osmatch")
                    if osmatch is not None:
                        host_data["os"] = {
                            "name": osmatch.get("name"),
                            "accuracy": osmatch.get("accuracy"),
                        }

                hosts.append(host_data)

        except ET.ParseError:
            pass

        return {
            "hosts": hosts,
            "findings": findings,
            "total_open_ports": sum(len(h.get("ports", [])) for h in hosts),
        }

    def get_risk_score(self, parsed: Dict) -> float:
        open_ports = parsed.get("total_open_ports", 0)
        if open_ports == 0:
            return 0.0
        elif open_ports <= 5:
            return 2.0
        elif open_ports <= 20:
            return 4.0
        elif open_ports <= 50:
            return 6.0
        return 8.0
