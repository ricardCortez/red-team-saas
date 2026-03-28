"""Hunter.io OSINT tool definition - email finder via API

This tool wraps the Hunter.io API for email discovery and verification.
It uses curl to call the API since there's no dedicated CLI binary.
The HUNTER_API_KEY env var must be set.
"""
import json
import os
from typing import Dict, Any, List

from app.core.tool_engine.base_tool import BaseTool, ToolCategory
from app.core.tool_engine.tool_registry import ToolRegistry


@ToolRegistry.register
class HunterIOTool(BaseTool):
    name = "hunter_io"
    category = ToolCategory.OSINT
    binary = "curl"  # Uses API via curl
    default_timeout = 60

    API_BASE = "https://api.hunter.io/v2"

    def build_command(self, target: str, options: Dict[str, Any]) -> List[str]:
        api_key = options.get("api_key") or os.environ.get("HUNTER_API_KEY", "")
        mode = options.get("mode", "domain-search")

        if mode == "domain-search":
            limit = str(options.get("limit", 20))
            department = options.get("department", "")
            url = f"{self.API_BASE}/domain-search?domain={target}&limit={limit}&api_key={api_key}"
            if department:
                url += f"&department={department}"
        elif mode == "email-finder":
            first_name = options.get("first_name", "")
            last_name = options.get("last_name", "")
            url = f"{self.API_BASE}/email-finder?domain={target}&first_name={first_name}&last_name={last_name}&api_key={api_key}"
        elif mode == "email-verifier":
            url = f"{self.API_BASE}/email-verifier?email={target}&api_key={api_key}"
        elif mode == "email-count":
            url = f"{self.API_BASE}/email-count?domain={target}"
        else:
            url = f"{self.API_BASE}/domain-search?domain={target}&api_key={api_key}"

        return ["curl", "-s", "-H", "Accept: application/json", url]

    def parse_output(self, raw_output: str, exit_code: int) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "emails": [],
            "patterns": [],
            "organization": "",
            "stats": {},
            "summary": {},
        }

        if exit_code != 0:
            result["error"] = "Hunter.io API call failed"
            return result

        try:
            data = json.loads(raw_output)
        except json.JSONDecodeError:
            result["error"] = "Invalid JSON from Hunter.io"
            return result

        if "errors" in data:
            result["error"] = str(data["errors"])
            return result

        api_data = data.get("data", data)

        # Domain search results
        if "emails" in api_data:
            for entry in api_data["emails"]:
                email_info = {
                    "email": entry.get("value", ""),
                    "type": entry.get("type", ""),
                    "confidence": entry.get("confidence", 0),
                    "first_name": entry.get("first_name", ""),
                    "last_name": entry.get("last_name", ""),
                    "position": entry.get("position", ""),
                    "department": entry.get("department", ""),
                    "sources_count": len(entry.get("sources", [])),
                }
                result["emails"].append(email_info)

        if "organization" in api_data:
            result["organization"] = api_data["organization"]
        if "pattern" in api_data:
            result["patterns"].append(api_data["pattern"])

        # Email verifier
        if "status" in api_data and "email" in api_data:
            result["verification"] = {
                "email": api_data.get("email", ""),
                "status": api_data.get("status", ""),
                "score": api_data.get("score", 0),
                "disposable": api_data.get("disposable", False),
                "webmail": api_data.get("webmail", False),
                "mx_records": api_data.get("mx_records", False),
                "smtp_server": api_data.get("smtp_server", False),
                "smtp_check": api_data.get("smtp_check", False),
            }

        result["summary"] = {
            "total_emails": len(result["emails"]),
            "organization": result["organization"],
            "pattern": result["patterns"][0] if result["patterns"] else "",
        }

        return result
