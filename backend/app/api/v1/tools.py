"""Tool endpoints - varies by architecture option"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.tool_manager import tool_manager
from app.core.config import settings
from app.core.tool_engine.tool_registry import ToolRegistry
import app.core.tool_definitions  # noqa: F401 — triggers registration
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/available")
async def get_available_tools(db: Session = Depends(get_db)):
    """Get list of available tools as array for frontend consumption."""
    tools_dict = ToolRegistry.list_tools()
    tools_list = []
    for name, info in tools_dict.items():
        category_val = info.get("category", "")
        if hasattr(category_val, "value"):
            category_val = category_val.value
        tools_list.append({
            "name": name,
            "category": category_val,
            "description": f"{name.replace('_', ' ').title()} security tool",
            "binary": info.get("binary", name),
            "requires_root": info.get("requires_root", False),
            "default_timeout": info.get("default_timeout", 300),
            "available": ToolRegistry.is_available(name),
            "parameters": [],
        })
    return tools_list


@router.get("/info")
async def get_tools_info(db: Session = Depends(get_db)):
    """Get detailed tools information"""
    return {
        "option": settings.ARCHITECTURE_OPTION,
        "total_tools": tool_manager.get_total_tool_count(),
        "categories": tool_manager.get_available_tools().get("categories", {}),
        "supports": {
            "generic_executor": tool_manager.supports_generic_executor(),
            "plugin_system": tool_manager.supports_plugin_system(),
            "api_gateway": tool_manager.supports_api_gateway(),
        },
    }
