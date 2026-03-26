"""Hydra network login brute force tool definition"""
import re
from typing import Dict, Any, List

from app.core.tool_engine.base_tool import BaseTool, ToolCategory
from app.core.tool_engine.tool_registry import ToolRegistry


@ToolRegistry.register
class HydraTool(BaseTool):
    name = "hydra"
    category = ToolCategory.BRUTE_FORCE
    binary = "hydra"
    default_timeout = 3600

    SUPPORTED_PROTOCOLS = [
        "ftp", "ssh", "telnet", "smtp", "pop3", "imap", "http-get", "http-post",
        "https-get", "https-post", "smb", "rdp", "vnc", "mysql", "mssql",
        "postgres", "oracle", "ldap", "snmp",
    ]

    PROFILES = {
        "fast":     {"tasks": 16, "timeout": 30},
        "balanced": {"tasks": 8,  "timeout": 60},
        "stealth":  {"tasks": 2,  "timeout": 120},
    }

    def build_command(self, target: str, options: Dict[str, Any]) -> List[str]:
        protocol = options.get("protocol", "ssh")
        if protocol not in self.SUPPORTED_PROTOCOLS:
            protocol = "ssh"

        profile_name = options.get("profile", "balanced")
        profile = self.PROFILES.get(profile_name, self.PROFILES["balanced"])

        cmd = ["hydra"]

        # Credentials
        if options.get("username"):
            cmd += ["-l", options["username"]]
        elif options.get("userlist"):
            cmd += ["-L", options["userlist"]]
        else:
            cmd += ["-l", "admin"]

        if options.get("password"):
            cmd += ["-p", options["password"]]
        elif options.get("passlist"):
            cmd += ["-P", options["passlist"]]
        else:
            cmd += ["-P", "/usr/share/wordlists/rockyou.txt"]

        # Profile settings
        cmd += ["-t", str(options.get("tasks", profile["tasks"]))]
        cmd += ["-w", str(options.get("timeout", profile["timeout"]))]

        # Port override
        if options.get("port"):
            cmd += ["-s", str(options["port"])]

        # Stop on first valid credential
        if options.get("stop_on_success", True):
            cmd += ["-f"]

        # Output
        cmd += ["-o", "/dev/stdout"]

        # Verbose for parsing
        cmd += ["-V"]

        cmd += [target, protocol]

        # Extra module options (e.g. http-post-form path)
        if options.get("module_opts"):
            cmd.append(options["module_opts"])

        return cmd

    def parse_output(self, raw_output: str, exit_code: int) -> Dict[str, Any]:
        credentials: List[Dict[str, str]] = []
        findings: List[Dict] = []

        # [DATA] ... host: x.x.x.x   login: admin   password: password123
        cred_pattern = re.compile(
            r'\[(\d+)\]\[([^\]]+)\]\s+host:\s+(\S+)\s+login:\s+(\S+)\s+password:\s+(\S+)',
            re.IGNORECASE,
        )
        for match in cred_pattern.finditer(raw_output):
            port, service, host, login, password = match.groups()
            entry = {
                "host": host,
                "port": port,
                "service": service,
                "login": login,
                "password": password,
            }
            credentials.append(entry)
            findings.append({
                "severity": "critical",
                "title": f"Valid credentials found for {service}",
                "description": f"Login: {login} / Password: {password} on {host}:{port}",
                "host": host,
                "port": port,
            })

        # Count attempts
        attempt_match = re.search(r'(\d+) of (\d+) target', raw_output)
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
