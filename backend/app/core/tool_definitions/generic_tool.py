"""Generic tool for running arbitrary binaries without a specific parser."""
from typing import Dict, Any, List

from app.core.tool_engine.base_tool import BaseTool, ToolCategory


class GenericTool(BaseTool):
    """
    Run any binary with custom args. NOT registered in ToolRegistry —
    instantiate directly when needed.
    """
    category = ToolCategory.NETWORK
    default_timeout = 300

    def __init__(
        self,
        tool_name: str,
        binary: str,
        category: ToolCategory = ToolCategory.NETWORK,
    ):
        self.name = tool_name
        self.binary = binary
        self.category = category

    def build_command(self, target: str, options: Dict[str, Any]) -> List[str]:
        cmd = [self.binary]
        if "args" in options:
            args = options["args"]
            if isinstance(args, list):
                cmd.extend(args)
            elif isinstance(args, str):
                cmd.extend(args.split())
        cmd.append(target)
        return cmd

    def parse_output(self, raw_output: str, exit_code: int) -> Dict[str, Any]:
        return {
            "raw": raw_output,
            "exit_code": exit_code,
            "findings": [],
            "lines": raw_output.splitlines(),
        }
