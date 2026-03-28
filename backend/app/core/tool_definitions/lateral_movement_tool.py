"""Lateral movement tools - PsExec, WMI, SSH, WinRM wrappers

Wraps common lateral movement techniques for authorized red team engagements.
Each technique is executed via its native CLI tool.
"""
import re
from typing import Dict, Any, List

from app.core.tool_engine.base_tool import BaseTool, ToolCategory
from app.core.tool_engine.tool_registry import ToolRegistry


@ToolRegistry.register
class LateralMovementTool(BaseTool):
    name = "lateral_movement"
    category = ToolCategory.EXPLOIT
    binary = "impacket-psexec"  # Default, overridden by technique
    requires_root = True
    default_timeout = 300

    TECHNIQUES = {
        "psexec": "impacket-psexec",
        "wmiexec": "impacket-wmiexec",
        "smbexec": "impacket-smbexec",
        "atexec": "impacket-atexec",
        "dcomexec": "impacket-dcomexec",
        "winrm": "evil-winrm",
        "ssh": "ssh",
        "rdp": "xfreerdp",
    }

    def build_command(self, target: str, options: Dict[str, Any]) -> List[str]:
        technique = options.get("technique", "psexec")
        username = options.get("username", "")
        password = options.get("password", "")
        domain = options.get("domain", "")
        hashes = options.get("hashes", "")  # NTLM hash for pass-the-hash
        command = options.get("command", "whoami")

        if technique in ("psexec", "wmiexec", "smbexec", "atexec", "dcomexec"):
            binary = self.TECHNIQUES[technique]
            cred_string = ""
            if domain and username:
                cred_string = f"{domain}/{username}"
            elif username:
                cred_string = username

            if password:
                cred_string += f":{password}"

            cmd = [binary]
            if cred_string:
                cmd.append(f"{cred_string}@{target}")
            else:
                cmd.append(target)

            if hashes:
                cmd.extend(["-hashes", hashes])

            if command and technique != "psexec":
                cmd.append(command)

            return cmd

        elif technique == "winrm":
            cmd = ["evil-winrm", "-i", target, "-u", username]
            if password:
                cmd.extend(["-p", password])
            if hashes:
                cmd.extend(["-H", hashes])
            if options.get("ssl"):
                cmd.append("-S")
            if command:
                cmd.extend(["-e", command])
            return cmd

        elif technique == "ssh":
            port = str(options.get("port", 22))
            cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-p", port]
            if options.get("key_file"):
                cmd.extend(["-i", options["key_file"]])
            if username:
                cmd.append(f"{username}@{target}")
            else:
                cmd.append(target)
            if command:
                cmd.append(command)
            return cmd

        elif technique == "rdp":
            cmd = ["xfreerdp", f"/v:{target}"]
            if username:
                cmd.append(f"/u:{username}")
            if password:
                cmd.append(f"/p:{password}")
            if domain:
                cmd.append(f"/d:{domain}")
            cmd.append("/cert-ignore")
            return cmd

        return [self.TECHNIQUES.get(technique, "echo"), "unsupported"]

    def parse_output(self, raw_output: str, exit_code: int) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "success": exit_code == 0,
            "technique": "",
            "target": "",
            "command_output": raw_output.strip(),
            "credentials_used": {},
            "access_level": "",
            "findings": [],
            "summary": {},
        }

        lines = raw_output.strip().split("\n")

        for line in lines:
            line_lower = line.lower().strip()

            # Detect admin/system access
            if "nt authority\\system" in line_lower:
                result["access_level"] = "SYSTEM"
            elif "administrator" in line_lower and not result["access_level"]:
                result["access_level"] = "Administrator"

            # Detect successful connection
            if "opening" in line_lower and "shell" in line_lower:
                result["success"] = True
            if "evil-winrm" in line_lower and "shell" in line_lower:
                result["success"] = True

        result["summary"] = {
            "success": result["success"],
            "access_level": result["access_level"],
            "output_lines": len(lines),
        }

        if result["success"]:
            result["findings"].append({
                "title": f"Lateral Movement: Successful access to target",
                "severity": "critical" if result["access_level"] in ("SYSTEM", "Administrator") else "high",
                "description": f"Successfully moved laterally using technique. "
                               f"Access level: {result['access_level'] or 'User'}. "
                               f"Exit code: {exit_code}.",
                "source": "lateral_movement",
            })

        return result
