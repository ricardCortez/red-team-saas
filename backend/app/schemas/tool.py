"""Tool configuration schemas"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class ToolCategory(str, Enum):
    recon = "recon"
    scanning = "scanning"
    exploitation = "exploitation"
    post_exploit = "post_exploit"
    reporting = "reporting"
    misc = "misc"


class ToolBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    category: ToolCategory = ToolCategory.misc
    command_template: Optional[str] = None
    default_options: Optional[Dict[str, Any]] = {}
    is_enabled: bool = True


class ToolCreate(ToolBase):
    pass


class ToolUpdate(BaseModel):
    description: Optional[str] = None
    category: Optional[ToolCategory] = None
    command_template: Optional[str] = None
    default_options: Optional[Dict[str, Any]] = None
    is_enabled: Optional[bool] = None


class ToolInDB(ToolBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class ToolResponse(ToolInDB):
    pass


class ToolListResponse(BaseModel):
    items: List[ToolResponse]
    total: int
    skip: int
    limit: int
