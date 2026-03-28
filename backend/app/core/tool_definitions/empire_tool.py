"""Empire C2 Framework tool definition - post-exploitation C2 management

Wraps the Empire REST API for managing agents, running modules,
and conducting post-exploitation in authorized engagements.
"""
import json
from typing import Dict, Any, List

from app.core.tool_engine.base_tool import BaseTool, ToolCategory
from app.core.tool_engine.tool_registry import ToolRegistry


@ToolRegistry.register
class EmpireTool(BaseTool):
    name = "empire"
    category = ToolCategory.EXPLOIT
    binary = "curl"  # API-based
    default_timeout = 300

    def build_command(self, target: str, options: Dict[str, Any]) -> List[str]:
        api_url = options.get("api_url", "https://localhost:1337")
        token = options.get("token", "")
        mode = options.get("mode", "agents")

        headers = ["-H", f"Authorization: Bearer {token}", "-H", "Content-Type: application/json", "-k"]

        if mode == "agents":
            return ["curl", "-s", f"{api_url}/api/v2/agents"] + headers

        elif mode == "agent_tasks":
            agent_id = options.get("agent_id", "")
            return ["curl", "-s", f"{api_url}/api/v2/agents/{agent_id}/tasks"] + headers

        elif mode == "run_module":
            agent_id = options.get("agent_id", "")
            module = options.get("module", "")
            module_options = options.get("module_options", {})
            body = json.dumps({"module": module, "options": module_options})
            return ["curl", "-s", "-X", "POST", f"{api_url}/api/v2/agents/{agent_id}/tasks/module"] + headers + ["-d", body]

        elif mode == "shell":
            agent_id = options.get("agent_id", "")
            command = options.get("command", "whoami")
            body = json.dumps({"command": command})
            return ["curl", "-s", "-X", "POST", f"{api_url}/api/v2/agents/{agent_id}/tasks/shell"] + headers + ["-d", body]

        elif mode == "listeners":
            return ["curl", "-s", f"{api_url}/api/v2/listeners"] + headers

        elif mode == "stagers":
            return ["curl", "-s", f"{api_url}/api/v2/stagers"] + headers

        elif mode == "credentials":
            return ["curl", "-s", f"{api_url}/api/v2/credentials"] + headers

        else:
            return ["curl", "-s", f"{api_url}/api/v2/agents"] + headers

    def parse_output(self, raw_output: str, exit_code: int) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "agents": [],
            "listeners": [],
            "credentials": [],
            "task_results": [],
            "findings": [],
            "summary": {},
        }

        if exit_code != 0:
            result["error"] = "Empire API call failed"
            return result

        try:
            data = json.loads(raw_output)
        except json.JSONDecodeError:
            result["error"] = "Invalid JSON from Empire API"
            return result

        # Agents
        if "records" in data and isinstance(data["records"], list):
            for agent in data["records"]:
                agent_info = {
                    "id": agent.get("session_id", agent.get("id", "")),
                    "name": agent.get("name", ""),
                    "hostname": agent.get("hostname", ""),
                    "username": agent.get("username", ""),
                    "os": agent.get("os_details", ""),
                    "architecture": agent.get("architecture", ""),
                    "language": agent.get("language", ""),
                    "internal_ip": agent.get("internal_ip", ""),
                    "external_ip": agent.get("external_ip", ""),
                    "process_name": agent.get("process_name", ""),
                    "process_id": agent.get("process_id", ""),
                    "high_integrity": agent.get("high_integrity", False),
                    "stale": agent.get("stale", False),
                }
                result["agents"].append(agent_info)

                result["findings"].append({
                    "title": f"Empire: Active agent on {agent_info['hostname']} ({agent_info['internal_ip']})",
                    "severity": "critical",
                    "description": f"Active C2 agent '{agent_info['name']}' on {agent_info['hostname']}. "
                                   f"User: {agent_info['username']}, OS: {agent_info['os']}, "
                                   f"Elevated: {agent_info['high_integrity']}",
                    "source": "empire",
                })

        # Credentials
        if isinstance(data, list) and len(data) > 0 and "credtype" in data[0]:
            for cred in data:
                result["credentials"].append({
                    "type": cred.get("credtype", ""),
                    "domain": cred.get("domain", ""),
                    "username": cred.get("username", ""),
                    "password": cred.get("password", ""),
                    "host": cred.get("host", ""),
                })

        result["summary"] = {
            "total_agents": len(result["agents"]),
            "active_agents": sum(1 for a in result["agents"] if not a.get("stale")),
            "elevated_agents": sum(1 for a in result["agents"] if a.get("high_integrity")),
            "total_credentials": len(result["credentials"]),
        }

        return result
