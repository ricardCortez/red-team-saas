"""SQLmap exploitation tool definition - SQL injection detection & exploitation"""
import re
from typing import Dict, Any, List

from app.core.tool_engine.base_tool import BaseTool, ToolCategory
from app.core.tool_engine.tool_registry import ToolRegistry


@ToolRegistry.register
class SQLmapTool(BaseTool):
    name = "sqlmap"
    category = ToolCategory.EXPLOIT
    binary = "sqlmap"
    default_timeout = 600

    RISK_LEVELS = {"1": "safe", "2": "moderate", "3": "aggressive"}
    LEVELS = {"1": "basic", "2": "extended", "3": "advanced", "4": "heavy", "5": "max"}

    def build_command(self, target: str, options: Dict[str, Any]) -> List[str]:
        cmd = ["sqlmap", "--batch", "--random-agent"]

        # Target specification
        if options.get("request_file"):
            cmd.extend(["-r", options["request_file"]])
        elif options.get("method", "GET").upper() == "POST":
            cmd.extend(["-u", target])
            if options.get("data"):
                cmd.extend(["--data", options["data"]])
        else:
            cmd.extend(["-u", target])

        # Parameter to test
        if options.get("param"):
            cmd.extend(["-p", options["param"]])

        # Level & risk
        level = str(options.get("level", 1))
        risk = str(options.get("risk", 1))
        cmd.extend(["--level", level, "--risk", risk])

        # Technique
        if options.get("technique"):
            cmd.extend(["--technique", options["technique"]])

        # Database enumeration
        if options.get("dbs"):
            cmd.append("--dbs")
        if options.get("tables"):
            cmd.append("--tables")
        if options.get("dump"):
            cmd.append("--dump")
        if options.get("current_db"):
            cmd.append("--current-db")
        if options.get("current_user"):
            cmd.append("--current-user")
        if options.get("is_dba"):
            cmd.append("--is-dba")
        if options.get("db"):
            cmd.extend(["-D", options["db"]])
        if options.get("table"):
            cmd.extend(["-T", options["table"]])

        # DBMS specification
        if options.get("dbms"):
            cmd.extend(["--dbms", options["dbms"]])

        # Tamper scripts
        if options.get("tamper"):
            cmd.extend(["--tamper", options["tamper"]])

        # Cookie / Headers
        if options.get("cookie"):
            cmd.extend(["--cookie", options["cookie"]])
        if options.get("headers"):
            for header in options["headers"]:
                cmd.extend(["-H", header])

        # Proxy
        if options.get("proxy"):
            cmd.extend(["--proxy", options["proxy"]])
        if options.get("tor"):
            cmd.append("--tor")

        # Output
        cmd.extend(["--output-dir", "/tmp/sqlmap_output"])

        # Threads
        threads = str(options.get("threads", 1))
        cmd.extend(["--threads", threads])

        return cmd

    def parse_output(self, raw_output: str, exit_code: int) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "injectable": False,
            "injection_points": [],
            "databases": [],
            "tables": [],
            "data": [],
            "dbms": "",
            "current_db": "",
            "current_user": "",
            "is_dba": False,
            "techniques": [],
            "findings": [],
            "summary": {},
        }

        lines = raw_output.strip().split("\n")

        for line in lines:
            line = line.strip()

            # Injection detection
            if "is vulnerable" in line.lower() or "injectable" in line.lower():
                result["injectable"] = True

            # Parameter injection point
            param_match = re.search(r"Parameter:\s+(\S+)\s+\((.+?)\)", line)
            if param_match:
                result["injection_points"].append({
                    "parameter": param_match.group(1),
                    "type": param_match.group(2),
                })

            # Technique
            tech_match = re.search(r"Type:\s+(.+)", line)
            if tech_match:
                result["techniques"].append(tech_match.group(1).strip())

            # DBMS
            dbms_match = re.search(r"back-end DBMS:\s+(.+)", line)
            if dbms_match:
                result["dbms"] = dbms_match.group(1).strip()

            # Current DB
            if "current database:" in line.lower():
                parts = line.split(":", 1)
                if len(parts) > 1:
                    result["current_db"] = parts[1].strip().strip("'\"")

            # Current user
            if "current user:" in line.lower():
                parts = line.split(":", 1)
                if len(parts) > 1:
                    result["current_user"] = parts[1].strip().strip("'\"")

            # DBA check
            if "current user is DBA:" in line:
                result["is_dba"] = "True" in line

            # Database names
            db_match = re.match(r"\[\*\]\s+(\S+)", line)
            if db_match and "available databases" not in line.lower():
                result["databases"].append(db_match.group(1))

        result["techniques"] = list(set(result["techniques"]))
        result["summary"] = {
            "injectable": result["injectable"],
            "injection_points": len(result["injection_points"]),
            "dbms": result["dbms"],
            "databases_found": len(result["databases"]),
            "techniques_count": len(result["techniques"]),
            "is_dba": result["is_dba"],
        }

        # Build findings
        if result["injectable"]:
            for point in result["injection_points"]:
                result["findings"].append({
                    "title": f"SQL Injection: {point['parameter']} ({point['type']})",
                    "severity": "critical",
                    "description": f"Parameter '{point['parameter']}' is vulnerable to {point['type']} SQL injection. DBMS: {result['dbms']}",
                    "source": "sqlmap",
                })

        if result["is_dba"]:
            result["findings"].append({
                "title": "Database Admin Privileges Accessible",
                "severity": "critical",
                "description": f"Current user '{result['current_user']}' has DBA privileges on {result['dbms']}.",
                "source": "sqlmap",
            })

        return result
