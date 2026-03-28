"""Burp Suite Professional API integration - web vulnerability scanning"""
import json
from typing import Dict, Any, List

from app.core.tool_engine.base_tool import BaseTool, ToolCategory
from app.core.tool_engine.tool_registry import ToolRegistry


@ToolRegistry.register
class BurpSuiteTool(BaseTool):
    name = "burpsuite"
    category = ToolCategory.EXPLOIT
    binary = "curl"  # API-based via REST
    default_timeout = 1800  # Scans can take a while

    def build_command(self, target: str, options: Dict[str, Any]) -> List[str]:
        api_url = options.get("api_url", "http://localhost:1337")
        api_key = options.get("api_key", "")
        mode = options.get("mode", "scan")

        headers = ["-H", "Content-Type: application/json"]
        if api_key:
            headers.extend(["-H", f"Authorization: {api_key}"])

        if mode == "scan":
            # Launch a scan via Burp REST API
            scan_config = options.get("scan_config", "Crawl and Audit - Balanced")
            body = json.dumps({
                "scan_configurations": [{"name": scan_config, "type": "NamedConfiguration"}],
                "scope": {"include": [{"rule": target, "type": "SimpleScopeDef"}]},
                "urls": [target],
            })
            return ["curl", "-s", "-X", "POST", f"{api_url}/v0.1/scan"] + headers + ["-d", body]

        elif mode == "status":
            scan_id = options.get("scan_id", "")
            return ["curl", "-s", f"{api_url}/v0.1/scan/{scan_id}"] + headers

        elif mode == "issues":
            scan_id = options.get("scan_id", "")
            return ["curl", "-s", f"{api_url}/v0.1/scan/{scan_id}"] + headers

        else:
            return ["curl", "-s", f"{api_url}/v0.1/scan"] + headers

    def parse_output(self, raw_output: str, exit_code: int) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "scan_id": "",
            "status": "",
            "issues": [],
            "findings": [],
            "summary": {},
        }

        if exit_code != 0:
            result["error"] = "Burp Suite API call failed"
            return result

        try:
            data = json.loads(raw_output)
        except json.JSONDecodeError:
            # Might be scan ID only (plain text response)
            result["scan_id"] = raw_output.strip()
            return result

        if isinstance(data, dict):
            result["scan_id"] = str(data.get("task_id", data.get("scan_id", "")))
            result["status"] = data.get("scan_status", data.get("status", ""))

            # Parse issues
            for issue in data.get("issue_events", data.get("issues", [])):
                iss = issue.get("issue", issue)
                parsed_issue = {
                    "name": iss.get("name", ""),
                    "severity": iss.get("severity", "info").lower(),
                    "confidence": iss.get("confidence", ""),
                    "path": iss.get("path", iss.get("origin", "")),
                    "description": iss.get("issueDetail", iss.get("description", "")),
                    "remediation": iss.get("remediationDetail", iss.get("remediation", "")),
                    "references": iss.get("references", ""),
                    "type_index": iss.get("type_index", 0),
                }
                result["issues"].append(parsed_issue)

                result["findings"].append({
                    "title": f"Burp: {parsed_issue['name']}",
                    "severity": parsed_issue["severity"],
                    "description": f"{parsed_issue['description'][:500]}\nPath: {parsed_issue['path']}",
                    "remediation": parsed_issue["remediation"][:500] if parsed_issue["remediation"] else None,
                    "source": "burpsuite",
                })

        result["summary"] = {
            "scan_id": result["scan_id"],
            "status": result["status"],
            "total_issues": len(result["issues"]),
            "by_severity": {},
        }
        for iss in result["issues"]:
            sev = iss["severity"]
            result["summary"]["by_severity"][sev] = result["summary"]["by_severity"].get(sev, 0) + 1

        return result
