"""GoPhish phishing framework tool definition - phishing campaign management"""
import json
from typing import Dict, Any, List

from app.core.tool_engine.base_tool import BaseTool, ToolCategory
from app.core.tool_engine.tool_registry import ToolRegistry


@ToolRegistry.register
class GoPhishTool(BaseTool):
    name = "gophish"
    category = ToolCategory.EXPLOIT
    binary = "curl"  # API-based
    default_timeout = 120

    def build_command(self, target: str, options: Dict[str, Any]) -> List[str]:
        api_url = options.get("api_url", "http://localhost:3333")
        api_key = options.get("api_key", "")
        mode = options.get("mode", "campaigns")

        headers = ["-H", f"Authorization: Bearer {api_key}", "-H", "Content-Type: application/json"]

        if mode == "campaigns":
            return ["curl", "-s", f"{api_url}/api/campaigns/"] + headers

        elif mode == "campaign_results":
            campaign_id = options.get("campaign_id", "")
            return ["curl", "-s", f"{api_url}/api/campaigns/{campaign_id}/results"] + headers

        elif mode == "create_campaign":
            body = json.dumps({
                "name": options.get("campaign_name", f"Campaign - {target}"),
                "template": {"name": options.get("template", "Default")},
                "page": {"name": options.get("landing_page", "Default Landing")},
                "smtp": {"name": options.get("smtp_profile", "Default SMTP")},
                "groups": [{"name": options.get("target_group", "Default Group")}],
                "url": options.get("phishing_url", target),
                "launch_date": options.get("launch_date", ""),
            })
            return ["curl", "-s", "-X", "POST", f"{api_url}/api/campaigns/"] + headers + ["-d", body]

        elif mode == "groups":
            return ["curl", "-s", f"{api_url}/api/groups/"] + headers

        elif mode == "templates":
            return ["curl", "-s", f"{api_url}/api/templates/"] + headers

        elif mode == "summary":
            return ["curl", "-s", f"{api_url}/api/campaigns/summary"] + headers

        else:
            return ["curl", "-s", f"{api_url}/api/campaigns/"] + headers

    def parse_output(self, raw_output: str, exit_code: int) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "campaigns": [],
            "results": [],
            "stats": {},
            "findings": [],
            "summary": {},
        }

        if exit_code != 0:
            result["error"] = "GoPhish API call failed"
            return result

        try:
            data = json.loads(raw_output)
        except json.JSONDecodeError:
            result["error"] = "Invalid JSON from GoPhish"
            return result

        if isinstance(data, list):
            for campaign in data:
                camp = {
                    "id": campaign.get("id"),
                    "name": campaign.get("name", ""),
                    "status": campaign.get("status", ""),
                    "created_date": campaign.get("created_date", ""),
                    "launch_date": campaign.get("launch_date", ""),
                    "stats": campaign.get("stats", {}),
                }
                result["campaigns"].append(camp)

                stats = campaign.get("stats", {})
                if stats.get("clicked", 0) > 0:
                    click_rate = round(stats["clicked"] / max(stats.get("total", 1), 1) * 100, 1)
                    result["findings"].append({
                        "title": f"Phishing: Campaign '{camp['name']}' - {click_rate}% click rate",
                        "severity": "high" if click_rate > 30 else "medium",
                        "description": f"Campaign '{camp['name']}' achieved {click_rate}% click rate. "
                                       f"Sent: {stats.get('total', 0)}, Opened: {stats.get('opened', 0)}, "
                                       f"Clicked: {stats.get('clicked', 0)}, Submitted: {stats.get('submitted_data', 0)}",
                        "source": "gophish",
                    })

        elif isinstance(data, dict):
            if "results" in data:
                for r in data["results"]:
                    result["results"].append({
                        "email": r.get("email", ""),
                        "status": r.get("status", ""),
                        "ip": r.get("ip", ""),
                        "latitude": r.get("latitude"),
                        "longitude": r.get("longitude"),
                    })

        total_sent = sum(c.get("stats", {}).get("total", 0) for c in result["campaigns"])
        total_clicked = sum(c.get("stats", {}).get("clicked", 0) for c in result["campaigns"])

        result["summary"] = {
            "total_campaigns": len(result["campaigns"]),
            "total_sent": total_sent,
            "total_clicked": total_clicked,
            "click_rate": round(total_clicked / max(total_sent, 1) * 100, 1),
            "total_results": len(result["results"]),
        }

        return result
