"""Registry pattern for tool classes"""
import shutil
from typing import Dict, Type
from app.core.tool_engine.base_tool import BaseTool


class ToolRegistry:
    _tools: Dict[str, Type[BaseTool]] = {}

    @classmethod
    def register(cls, tool_class: Type[BaseTool]):
        """Decorator to register a tool class."""
        cls._tools[tool_class.name] = tool_class
        return tool_class

    @classmethod
    def get(cls, name: str) -> Type[BaseTool]:
        tool = cls._tools.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not registered")
        return tool

    @classmethod
    def list_tools(cls) -> Dict[str, Dict]:
        return {
            name: {
                "name": name,
                "category": t.category,
                "binary": t.binary,
                "requires_root": t.requires_root,
                "default_timeout": t.default_timeout,
            }
            for name, t in cls._tools.items()
        }

    @classmethod
    def is_available(cls, name: str) -> bool:
        """Check if the tool's binary is installed on the system."""
        tool = cls._tools.get(name)
        if not tool:
            return False
        return shutil.which(tool.binary) is not None

    @classmethod
    def all_names(cls) -> list:
        return list(cls._tools.keys())
