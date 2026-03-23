"""Tool endpoints - varies by architecture option"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.tool_manager import tool_manager
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/available")
async def get_available_tools(db: Session = Depends(get_db)):
    """Get list of available tools for current architecture"""
    tools = tool_manager.get_available_tools()
    return {
        "architecture_option": settings.ARCHITECTURE_OPTION,
        "total_tools": tool_manager.get_total_tool_count(),
        "tools": tools,
        "features": {
            "generic_executor": tool_manager.supports_generic_executor(),
            "plugin_system": tool_manager.supports_plugin_system(),
            "api_gateway": tool_manager.supports_api_gateway(),
        },
    }


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
