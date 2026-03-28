"""TheHarvester OSINT tool definition - email/subdomain harvesting"""
import re
from typing import Dict, Any, List

from app.core.tool_engine.base_tool import BaseTool, ToolCategory
from app.core.tool_engine.tool_registry import ToolRegistry


@ToolRegistry.register
class TheHarvesterTool(BaseTool):
    name = "theharvester"
    category = ToolCategory.OSINT
    binary = "theHarvester"
    default_timeout = 300

    SOURCES = [
        "anubis", "baidu", "bevigil", "binaryedge", "bing", "bingapi",
        "bufferoverun", "censys", "certspotter", "crtsh", "dnsdumpster",
        "duckduckgo", "fullhunt", "github-code", "hackertarget", "hunter",
        "hunterhow", "intelx", "otx", "pentesttools", "projectdiscovery",
        "rapiddns", "rocketreach", "securityTrails", "shodan", "sitedossier",
        "subdomaincenter", "subdomainfinderc99", "threatminer", "urlscan",
        "virustotal", "yahoo", "zoomeye",
    ]

    def build_command(self, target: str, options: Dict[str, Any]) -> List[str]:
        source = options.get("source", "crtsh,dnsdumpster,hackertarget,rapiddns")
        limit = str(options.get("limit", 500))
        start = str(options.get("start", 0))

        cmd = [
            "theHarvester",
            "-d", target,
            "-b", source,
            "-l", limit,
            "-S", start,
        ]

        if options.get("dns_brute"):
            cmd.append("-c")
        if options.get("dns_lookup"):
            cmd.append("-n")
        if options.get("take_over"):
            cmd.append("-t")
        if options.get("virtual_host"):
            cmd.append("-v")
        if options.get("filename"):
            cmd.extend(["-f", options["filename"]])

        return cmd

    def parse_output(self, raw_output: str, exit_code: int) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "emails": [],
            "hosts": [],
            "ips": [],
            "subdomains": [],
            "urls": [],
            "asns": [],
            "summary": {},
        }

        if exit_code != 0 and not raw_output.strip():
            result["error"] = "TheHarvester execution failed"
            return result

        lines = raw_output.strip().split("\n")
        section = None

        email_re = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
        ip_re = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
        domain_re = re.compile(r'\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b')

        for line in lines:
            line_stripped = line.strip()
            lower = line_stripped.lower()

            # Section headers
            if "emails found" in lower or "[*] emails" in lower:
                section = "emails"
                continue
            elif "hosts found" in lower or "[*] hosts" in lower:
                section = "hosts"
                continue
            elif "ips found" in lower or "[*] ips" in lower:
                section = "ips"
                continue
            elif "[*] virtual hosts" in lower:
                section = "vhosts"
                continue
            elif lower.startswith("[*]") or lower.startswith("---"):
                section = None
                continue

            if not line_stripped or line_stripped.startswith("[") or line_stripped.startswith("*"):
                continue

            if section == "emails":
                emails = email_re.findall(line_stripped)
                result["emails"].extend(emails)
            elif section == "hosts":
                ips = ip_re.findall(line_stripped)
                result["ips"].extend(ips)
                domains = domain_re.findall(line_stripped)
                for d in domains:
                    result["hosts"].append(d)
                    result["subdomains"].append(d)
            elif section == "ips":
                ips = ip_re.findall(line_stripped)
                result["ips"].extend(ips)

        # Deduplicate
        result["emails"] = sorted(set(result["emails"]))
        result["hosts"] = sorted(set(result["hosts"]))
        result["ips"] = sorted(set(result["ips"]))
        result["subdomains"] = sorted(set(result["subdomains"]))

        result["summary"] = {
            "total_emails": len(result["emails"]),
            "total_hosts": len(result["hosts"]),
            "total_ips": len(result["ips"]),
            "total_subdomains": len(result["subdomains"]),
        }

        return result
