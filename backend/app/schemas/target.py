"""Target schemas"""
from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.models.target import TargetType, TargetStatus


class TargetCreate(BaseModel):
    value:       str
    target_type: TargetType
    status:      Optional[TargetStatus] = TargetStatus.in_scope
    description: Optional[str] = None
    tags:        Optional[str] = None

    @field_validator("value")
    @classmethod
    def strip_value(cls, v: str) -> str:
        return v.strip()


class TargetUpdate(BaseModel):
    status:      Optional[TargetStatus] = None
    description: Optional[str] = None
    tags:        Optional[str] = None
    os_hint:     Optional[str] = None
    tech_stack:  Optional[str] = None


class TargetBulkCreate(BaseModel):
    targets: List[TargetCreate]


class TargetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:          int
    project_id:  int
    value:       str
    target_type: TargetType
    status:      TargetStatus
    description: Optional[str] = None
    tags:        Optional[str] = None
    os_hint:     Optional[str] = None
    tech_stack:  Optional[str] = None
    last_scanned: Optional[datetime] = None
    created_at:  datetime
