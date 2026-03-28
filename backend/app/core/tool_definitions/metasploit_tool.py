"""Metasploit Framework tool definition - exploitation via msfconsole/msfrpc"""
import re
from typing import Dict, Any, List

from app.core.tool_engine.base_tool import BaseTool, ToolCategory
from app.core.tool_engine.tool_registry import ToolRegistry


@ToolRegistry.register
class MetasploitTool(BaseTool):
    name = "metasploit"
    category = ToolCategory.EXPLOIT
    binary = "msfconsole"
    requires_root = True
    default_timeout = 900

    def build_command(self, target: str, options: Dict[str, Any]) -> List[str]:
        mode = options.get("mode", "exploit")

        if mode == "scan":
            module = options.get("module", "auxiliary/scanner/portscan/tcp")
            resource_cmds = [
                f"use {module}",
                f"set RHOSTS {target}",
            ]
            if options.get("ports"):
                resource_cmds.append(f"set PORTS {options['ports']}")
            if options.get("threads"):
                resource_cmds.append(f"set THREADS {options['threads']}")
            resource_cmds.append("run")
            resource_cmds.append("exit")

        elif mode == "exploit":
            module = options.get("module", "")
            payload = options.get("payload", "")
            resource_cmds = [f"use {module}"]
            resource_cmds.append(f"set RHOSTS {target}")
            if options.get("rport"):
                resource_cmds.append(f"set RPORT {options['rport']}")
            if payload:
                resource_cmds.append(f"set PAYLOAD {payload}")
            if options.get("lhost"):
                resource_cmds.append(f"set LHOST {options['lhost']}")
            if options.get("lport"):
                resource_cmds.append(f"set LPORT {options['lport']}")
            # Custom options
            for key, val in options.get("extra_options", {}).items():
                resource_cmds.append(f"set {key} {val}")
            resource_cmds.append("exploit -z")
            resource_cmds.append("exit")

        elif mode == "search":
            query = options.get("query", target)
            resource_cmds = [f"search {query}", "exit"]

        elif mode == "vuln_scan":
            resource_cmds = [
                f"db_nmap -sV -sC {target}",
                "vulns",
                "exit",
            ]

        else:
            resource_cmds = [f"nmap {target}", "exit"]

        # Build resource script inline via -x
        inline_script = "; ".join(resource_cmds)
        return ["msfconsole", "-q", "-x", inline_script]

    def parse_output(self, raw_output: str, exit_code: int) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "sessions": [],
            "exploits_attempted": [],
            "vulnerabilities": [],
            "modules_found": [],
            "hosts": [],
            "loot": [],
            "findings": [],
            "summary": {},
        }

        lines = raw_output.strip().split("\n")

        for line in lines:
            line = line.strip()

            # Session opened
            session_match = re.search(
                r"(Meterpreter|shell|vnc)\s+session\s+(\d+)\s+opened\s+\((\S+)\s*->\s*(\S+)\)",
                line, re.IGNORECASE,
            )
            if session_match:
                result["sessions"].append({
                    "type": session_match.group(1),
                    "id": int(session_match.group(2)),
                    "local": session_match.group(3),
                    "remote": session_match.group(4),
                })

            # Exploit completed
            if "exploit completed" in line.lower():
                result["exploits_attempted"].append({"status": "completed", "raw": line})

            # Module search results
            module_match = re.match(r"\s*\d+\s+(exploit|auxiliary|post|payload)/(\S+)", line)
            if module_match:
                result["modules_found"].append({
                    "type": module_match.group(1),
                    "path": f"{module_match.group(1)}/{module_match.group(2)}",
                })

            # Vulnerability found
            if "[+]" in line:
                result["vulnerabilities"].append(line.replace("[+]", "").strip())

            # Host discovered
            host_match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+-\s+(.+)", line)
            if host_match and "[*]" in line:
                result["hosts"].append({
                    "ip": host_match.group(1),
                    "info": host_match.group(2).strip(),
                })

        result["summary"] = {
            "sessions_opened": len(result["sessions"]),
            "exploits_attempted": len(result["exploits_attempted"]),
            "vulnerabilities_found": len(result["vulnerabilities"]),
            "modules_found": len(result["modules_found"]),
            "hosts_discovered": len(result["hosts"]),
        }

        # Build findings
        for session in result["sessions"]:
            result["findings"].append({
                "title": f"Metasploit: {session['type']} session opened to {session['remote']}",
                "severity": "critical",
                "description": f"A {session['type']} session (ID: {session['id']}) was successfully opened from {session['local']} to {session['remote']}.",
                "source": "metasploit",
            })

        for vuln in result["vulnerabilities"]:
            result["findings"].append({
                "title": f"Metasploit: {vuln[:80]}",
                "severity": "high",
                "description": vuln,
                "source": "metasploit",
            })

        return result
