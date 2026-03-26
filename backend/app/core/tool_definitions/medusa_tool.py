"""Medusa parallel network login brute force tool definition"""
import re
from typing import Dict, Any, List

from app.core.tool_engine.base_tool import BaseTool, ToolCategory
from app.core.tool_engine.tool_registry import ToolRegistry


@ToolRegistry.register
class MedusaTool(BaseTool):
    name = "medusa"
    category = ToolCategory.BRUTE_FORCE
    binary = "medusa"
    default_timeout = 3600

    SUPPORTED_MODULES = [
        "ftp", "ssh", "telnet", "smtp", "pop3", "imap", "http",
        "https", "smb", "rdp", "vnc", "mysql", "mssql",
    ]

    def build_command(self, target: str, options: Dict[str, Any]) -> List[str]:
        module = options.get("module", "ssh")
        if module not in self.SUPPORTED_MODULES:
            module = "ssh"

        cmd = ["medusa", "-h", target, "-M", module]

        # Credentials
        if options.get("username"):
            cmd += ["-u", options["username"]]
        elif options.get("userlist"):
            cmd += ["-U", options["userlist"]]
        else:
            cmd += ["-u", "admin"]

        if options.get("password"):
            cmd += ["-p", options["password"]]
        elif options.get("passlist"):
            cmd += ["-P", options["passlist"]]
        else:
            cmd += ["-P", "/usr/share/wordlists/rockyou.txt"]

        # Port override
        if options.get("port"):
            cmd += ["-n", str(options["port"])]

        # Threads
        threads = options.get("threads", 4)
        cmd += ["-t", str(threads)]

        # Stop on first valid credential
        if options.get("stop_on_success", True):
            cmd += ["-f"]

        # Verbose output for parsing
        cmd += ["-v", "6"]

        return cmd

    def parse_output(self, raw_output: str, exit_code: int) -> Dict[str, Any]:
        credentials: List[Dict[str, str]] = []
        findings: List[Dict] = []

        # ACCOUNT FOUND: [ssh] Host: 192.168.1.1 User: admin Password: password123 [SUCCESS]
        account_pattern = re.compile(
            r'ACCOUNT FOUND:\s+\[([^\]]+)\]\s+Host:\s+(\S+)\s+User:\s+(\S+)\s+Password:\s+(\S+)',
            re.IGNORECASE,
        )
        for match in account_pattern.finditer(raw_output):
            module, host, user, password = match.groups()
            entry = {
                "module": module,
                "host": host,
                "user": user,
                "password": password,
            }
            credentials.append(entry)
            findings.append({
                "severity": "critical",
                "title": f"Valid credentials found via {module}",
                "description": f"User: {user} / Password: {password} on {host}",
                "host": host,
            })

        # Count total attempts
        attempt_match = re.search(r'ACCOUNT CHECK:\s+.*?(\d+)\s+of\s+(\d+)', raw_output)
        attempts = int(attempt_match.group(1)) if attempt_match else 0

        return {
            "credentials": credentials,
            "findings": findings,
            "total_credentials": len(credentials),
            "attempts": attempts,
        }

    def get_risk_score(self, parsed: Dict) -> float:
        total = parsed.get("total_credentials", 0)
        if total == 0:
            return 0.0
        elif total == 1:
            return 8.0
        return 10.0
