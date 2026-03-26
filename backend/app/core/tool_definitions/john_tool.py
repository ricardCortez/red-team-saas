"""John the Ripper offline password cracking tool definition"""
import re
from typing import Dict, Any, List

from app.core.tool_engine.base_tool import BaseTool, ToolCategory
from app.core.tool_engine.tool_registry import ToolRegistry


@ToolRegistry.register
class JohnTool(BaseTool):
    name = "john"
    category = ToolCategory.BRUTE_FORCE
    binary = "john"
    default_timeout = 7200

    MODES = ["wordlist", "incremental", "single", "mask"]

    def validate_target(self, target: str) -> bool:
        """Target is a hash file path or hash string — always allow."""
        return bool(target and target.strip())

    def build_command(self, target: str, options: Dict[str, Any]) -> List[str]:
        mode = options.get("mode", "wordlist")
        if mode not in self.MODES:
            mode = "wordlist"

        cmd = ["john"]

        if mode == "wordlist":
            wordlist = options.get("wordlist", "/usr/share/wordlists/rockyou.txt")
            cmd += [f"--wordlist={wordlist}"]
            if options.get("rules"):
                cmd += [f"--rules={options['rules']}"]

        elif mode == "incremental":
            charset = options.get("charset", "All")
            cmd += [f"--incremental={charset}"]

        elif mode == "single":
            cmd += ["--single"]

        elif mode == "mask":
            mask = options.get("mask", "?a?a?a?a?a?a?a?a")
            cmd += [f"--mask={mask}"]

        if options.get("format"):
            cmd += [f"--format={options['format']}"]

        if options.get("min_length"):
            cmd += [f"--min-length={options['min_length']}"]
        if options.get("max_length"):
            cmd += [f"--max-length={options['max_length']}"]

        # Fork for parallel cracking
        if options.get("fork"):
            cmd += [f"--fork={options['fork']}"]

        cmd.append(target)
        return cmd

    def parse_output(self, raw_output: str, exit_code: int) -> Dict[str, Any]:
        cracked: List[Dict[str, str]] = []
        findings: List[Dict] = []

        # Pattern: "hash (user:password)" or just "password (user)"
        # John output: username:password or just password
        cracked_pattern = re.compile(
            r'^([^\s:]+)\s+\(([^:)]+)(?::([^)]+))?\)',
            re.MULTILINE,
        )
        for match in cracked_pattern.finditer(raw_output):
            password = match.group(1)
            user_or_hash = match.group(2)
            extra = match.group(3)

            entry = {
                "password": password,
                "hash": extra if extra else user_or_hash,
                "user": user_or_hash if extra else "",
            }
            cracked.append(entry)
            findings.append({
                "severity": "high",
                "title": "Password cracked",
                "description": f"Password '{password}' cracked for '{user_or_hash}'",
            })

        # Also look for "--show" style output: "user:password:..."
        show_pattern = re.compile(r'^([^:]+):([^:]+):', re.MULTILINE)
        if not cracked:
            for match in show_pattern.finditer(raw_output):
                user, password = match.group(1), match.group(2)
                if user and password and user != "0":
                    entry = {"user": user, "password": password, "hash": ""}
                    cracked.append(entry)
                    findings.append({
                        "severity": "high",
                        "title": "Password cracked",
                        "description": f"Password '{password}' cracked for user '{user}'",
                    })

        # Count guesses from status line
        guesses_match = re.search(r'(\d+)g\s+\d+:\d+:\d+:\d+', raw_output)
        guesses = int(guesses_match.group(1)) if guesses_match else len(cracked)

        return {
            "cracked": cracked,
            "findings": findings,
            "total_cracked": len(cracked),
            "guesses": guesses,
        }

    def get_risk_score(self, parsed: Dict) -> float:
        total = parsed.get("total_cracked", 0)
        if total == 0:
            return 0.0
        elif total <= 3:
            return 6.0
        elif total <= 10:
            return 8.0
        return 10.0
