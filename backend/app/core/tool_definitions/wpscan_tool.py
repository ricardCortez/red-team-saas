"""WPScan WordPress vulnerability scanner and brute force tool definition"""
import json
import re
from typing import Dict, Any, List

from app.core.tool_engine.base_tool import BaseTool, ToolCategory
from app.core.tool_engine.tool_registry import ToolRegistry


@ToolRegistry.register
class WPScanTool(BaseTool):
    name = "wpscan"
    category = ToolCategory.BRUTE_FORCE
    binary = "wpscan"
    default_timeout = 1800

    SCAN_TYPES = ["passive", "mixed", "aggressive", "brute"]

    def validate_target(self, target: str) -> bool:
        """Target must be an HTTP/HTTPS URL."""
        import re as _re
        return bool(_re.match(r'^https?://.+', target))

    def build_command(self, target: str, options: Dict[str, Any]) -> List[str]:
        scan_type = options.get("scan_type", "mixed")
        if scan_type not in self.SCAN_TYPES:
            scan_type = "mixed"

        cmd = ["wpscan", "--url", target, "--format", "json", "--no-banner"]

        if scan_type == "passive":
            cmd += ["--detection-mode", "passive"]
        elif scan_type == "aggressive":
            cmd += ["--detection-mode", "aggressive"]
        elif scan_type == "mixed":
            cmd += ["--detection-mode", "mixed"]
        elif scan_type == "brute":
            cmd += ["--detection-mode", "mixed"]
            if options.get("userlist"):
                cmd += ["--usernames", options["userlist"]]
            elif options.get("username"):
                cmd += ["--usernames", options["username"]]
            if options.get("passlist"):
                cmd += ["--passwords", options["passlist"]]
            elif options.get("password"):
                cmd += ["--passwords", options["password"]]
            cmd += ["--password-attack", "xmlrpc"]

        # Enumerate options
        enumerate_opts = []
        if options.get("enumerate_plugins", True):
            enumerate_opts.append("ap")
        if options.get("enumerate_themes", False):
            enumerate_opts.append("at")
        if options.get("enumerate_users", True):
            enumerate_opts.append("u")
        if options.get("enumerate_timthumbs", False):
            enumerate_opts.append("tt")
        if enumerate_opts:
            cmd += ["--enumerate", ",".join(enumerate_opts)]

        # API token for vulnerability data
        if options.get("api_token"):
            cmd += ["--api-token", options["api_token"]]

        # Throttle requests (ms between requests)
        if options.get("throttle"):
            cmd += ["--throttle", str(options["throttle"])]

        # Threads
        if options.get("threads"):
            cmd += ["--max-threads", str(options["threads"])]

        return cmd

    def parse_output(self, raw_output: str, exit_code: int) -> Dict[str, Any]:
        findings: List[Dict] = []
        result: Dict[str, Any] = {
            "findings": findings,
            "version": None,
            "vulnerabilities": [],
            "plugins": [],
            "users": [],
            "credentials": [],
            "is_wordpress": False,
        }

        # Extract JSON block from output
        json_match = re.search(r'\{.*\}', raw_output, re.DOTALL)
        if not json_match:
            return result

        try:
            data = json.loads(json_match.group())
        except (json.JSONDecodeError, ValueError):
            return result

        result["is_wordpress"] = True

        # Version
        version_info = data.get("version", {})
        if version_info:
            ver = version_info.get("number")
            result["version"] = ver
            vulns = version_info.get("vulnerabilities", [])
            for vuln in vulns:
                title = vuln.get("title", "Unknown vulnerability")
                cvss = vuln.get("cvss", {})
                score = cvss.get("score", 5.0) if cvss else 5.0
                severity = "critical" if score >= 9 else "high" if score >= 7 else "medium" if score >= 4 else "low"
                v = {
                    "title": title,
                    "version": ver,
                    "references": vuln.get("references", {}),
                    "cvss_score": score,
                }
                result["vulnerabilities"].append(v)
                findings.append({
                    "severity": severity,
                    "title": f"WordPress {ver} vulnerability: {title}",
                    "description": title,
                    "cvss_score": score,
                })

        # Plugins
        plugins_data = data.get("plugins", {})
        for plugin_slug, plugin_info in plugins_data.items():
            plugin_entry = {
                "slug": plugin_slug,
                "version": plugin_info.get("version", {}).get("number"),
                "vulnerabilities": [],
            }
            for vuln in plugin_info.get("vulnerabilities", []):
                title = vuln.get("title", "Unknown")
                plugin_entry["vulnerabilities"].append(title)
                findings.append({
                    "severity": "high",
                    "title": f"Plugin vulnerability: {title}",
                    "description": f"Plugin: {plugin_slug} - {title}",
                    "plugin": plugin_slug,
                })
            result["plugins"].append(plugin_entry)

        # Users
        users_data = data.get("users", {})
        for username, user_info in users_data.items():
            result["users"].append(username)
            findings.append({
                "severity": "medium",
                "title": f"WordPress user enumerated: {username}",
                "description": f"User ID: {user_info.get('id', 'unknown')}",
            })

        # Brute force credentials
        passwords_data = data.get("passwords", [])
        for entry in passwords_data:
            user = entry.get("username", "")
            password = entry.get("password", "")
            if user and password:
                result["credentials"].append({"username": user, "password": password})
                findings.append({
                    "severity": "critical",
                    "title": f"WordPress credential found: {user}",
                    "description": f"Username: {user} / Password: {password}",
                })

        return result

    def get_risk_score(self, parsed: Dict) -> float:
        score = 0.0
        if parsed.get("credentials"):
            score = max(score, 10.0)
        if parsed.get("vulnerabilities"):
            score = max(score, 7.0)
        if parsed.get("users"):
            score = max(score, 4.0)
        if parsed.get("plugins"):
            score = max(score, 2.0)
        return score
