"""Passive DNS OSINT tool definition - DNS history & enumeration

Uses multiple DNS reconnaissance techniques: dig for zone transfer attempts,
host lookups, and dnsrecon for comprehensive DNS enumeration.
"""
import re
from typing import Dict, Any, List

from app.core.tool_engine.base_tool import BaseTool, ToolCategory
from app.core.tool_engine.tool_registry import ToolRegistry


@ToolRegistry.register
class PassiveDNSTool(BaseTool):
    name = "passive_dns"
    category = ToolCategory.OSINT
    binary = "dnsrecon"
    default_timeout = 300

    SCAN_TYPES = {
        "standard": "std",
        "zone_transfer": "axfr",
        "brute": "brt",
        "reverse": "rvl",
        "cache_snoop": "snoop",
        "zone_walk": "zonewalk",
        "google": "goo",
    }

    def build_command(self, target: str, options: Dict[str, Any]) -> List[str]:
        mode = options.get("mode", "standard")
        scan_type = self.SCAN_TYPES.get(mode, "std")

        cmd = ["dnsrecon", "-d", target, "-t", scan_type]

        if options.get("nameserver"):
            cmd.extend(["-n", options["nameserver"]])
        if options.get("dictionary") and mode == "brute":
            cmd.extend(["-D", options["dictionary"]])
        if options.get("threads"):
            cmd.extend(["--threads", str(options["threads"])])
        if options.get("lifetime"):
            cmd.extend(["--lifetime", str(options["lifetime"])])
        if options.get("json_output"):
            cmd.extend(["-j", options["json_output"]])
        if options.get("xml_output"):
            cmd.extend(["--xml", options["xml_output"]])

        return cmd

    def parse_output(self, raw_output: str, exit_code: int) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "records": {
                "A": [],
                "AAAA": [],
                "CNAME": [],
                "MX": [],
                "NS": [],
                "TXT": [],
                "SOA": [],
                "SRV": [],
                "PTR": [],
            },
            "subdomains": [],
            "nameservers": [],
            "mail_servers": [],
            "zone_transfer": False,
            "findings": [],
            "summary": {},
        }

        if exit_code != 0 and not raw_output.strip():
            result["error"] = "DNS reconnaissance failed"
            return result

        lines = raw_output.strip().split("\n")

        ip_re = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
        domain_re = re.compile(r'\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b')

        for line in lines:
            line = line.strip()
            if not line or line.startswith("[*]") and "performing" in line.lower():
                continue

            # Parse [*] TYPE domain IP
            match = re.match(r'\[\*\]\s+(\w+)\s+([\w.-]+)\s+([\d.]+)?', line)
            if match:
                record_type = match.group(1).upper()
                name = match.group(2)
                ip = match.group(3) or ""

                record = {"name": name, "ip": ip}

                if record_type in result["records"]:
                    result["records"][record_type].append(record)

                if record_type in ("A", "AAAA", "CNAME"):
                    result["subdomains"].append(name)
                elif record_type == "NS":
                    result["nameservers"].append(name)
                elif record_type == "MX":
                    result["mail_servers"].append(name)
                continue

            # Zone transfer detection
            if "zone transfer" in line.lower() and "success" in line.lower():
                result["zone_transfer"] = True
                result["findings"].append({
                    "title": "DNS Zone Transfer Allowed",
                    "severity": "high",
                    "description": f"Zone transfer (AXFR) is permitted, exposing internal DNS records.",
                    "source": "passive_dns",
                })

            # SPF / DMARC / DKIM detection in TXT records
            if "TXT" in line:
                txt_match = re.search(r'"([^"]*)"', line)
                if txt_match:
                    txt_value = txt_match.group(1)
                    result["records"]["TXT"].append({"value": txt_value})
                    if "v=spf1" in txt_value:
                        result["findings"].append({
                            "title": "SPF Record Found",
                            "severity": "info",
                            "description": f"SPF: {txt_value}",
                            "source": "passive_dns",
                        })

        # Deduplicate
        result["subdomains"] = sorted(set(result["subdomains"]))
        result["nameservers"] = sorted(set(result["nameservers"]))
        result["mail_servers"] = sorted(set(result["mail_servers"]))

        total_records = sum(len(v) for v in result["records"].values())
        result["summary"] = {
            "total_records": total_records,
            "total_subdomains": len(result["subdomains"]),
            "total_nameservers": len(result["nameservers"]),
            "total_mail_servers": len(result["mail_servers"]),
            "zone_transfer_allowed": result["zone_transfer"],
        }

        return result
