"""Whois OSINT tool definition - domain/IP registration info"""
import re
from typing import Dict, Any, List

from app.core.tool_engine.base_tool import BaseTool, ToolCategory
from app.core.tool_engine.tool_registry import ToolRegistry


@ToolRegistry.register
class WhoisTool(BaseTool):
    name = "whois"
    category = ToolCategory.OSINT
    binary = "whois"
    default_timeout = 60

    def build_command(self, target: str, options: Dict[str, Any]) -> List[str]:
        cmd = ["whois"]

        server = options.get("server")
        if server:
            cmd.extend(["-h", server])

        if options.get("no_redirect"):
            cmd.append("-r")

        cmd.append(target)
        return cmd

    def parse_output(self, raw_output: str, exit_code: int) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "domain_info": {},
            "registrar": {},
            "registrant": {},
            "dates": {},
            "nameservers": [],
            "status": [],
            "raw_fields": {},
            "summary": {},
        }

        if exit_code != 0 and not raw_output.strip():
            result["error"] = "Whois lookup failed"
            return result

        lines = raw_output.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line or line.startswith("%") or line.startswith("#"):
                continue

            if ":" not in line:
                continue

            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip()

            if not value:
                continue

            result["raw_fields"][key] = value

            # Domain info
            if key in ("domain name", "domain"):
                result["domain_info"]["name"] = value
            elif key in ("registry domain id",):
                result["domain_info"]["registry_id"] = value

            # Registrar
            elif key in ("registrar",):
                result["registrar"]["name"] = value
            elif key in ("registrar url",):
                result["registrar"]["url"] = value
            elif key in ("registrar abuse contact email",):
                result["registrar"]["abuse_email"] = value

            # Registrant
            elif key in ("registrant name",):
                result["registrant"]["name"] = value
            elif key in ("registrant organization", "registrant org"):
                result["registrant"]["organization"] = value
            elif key in ("registrant country",):
                result["registrant"]["country"] = value
            elif key in ("registrant email",):
                result["registrant"]["email"] = value

            # Dates
            elif "creation" in key or "created" in key:
                result["dates"]["created"] = value
            elif "expir" in key:
                result["dates"]["expires"] = value
            elif "updated" in key or "modified" in key:
                result["dates"]["updated"] = value

            # Nameservers
            elif key in ("name server", "nserver", "nameserver"):
                result["nameservers"].append(value.lower())

            # Status
            elif key in ("domain status", "status"):
                result["status"].append(value)

        result["nameservers"] = sorted(set(result["nameservers"]))
        result["summary"] = {
            "domain": result["domain_info"].get("name", ""),
            "registrar": result["registrar"].get("name", "Unknown"),
            "created": result["dates"].get("created", "Unknown"),
            "expires": result["dates"].get("expires", "Unknown"),
            "nameserver_count": len(result["nameservers"]),
        }

        return result
