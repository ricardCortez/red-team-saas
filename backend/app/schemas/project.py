"""Project schemas"""
import json
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ProjectStatus(str, Enum):
    active = "active"
    paused = "paused"
    completed = "completed"
    archived = "archived"


class ProjectScope(str, Enum):
    internal = "internal"
    external = "external"
    full = "full"
    web = "web"
    api = "api"
    mobile = "mobile"


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)
    target: str = Field(..., description="IP, domain, or CIDR range")
    scope: ProjectScope = ProjectScope.external
    status: ProjectStatus = ProjectStatus.active
    client_name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    tags: Optional[List[str]] = []
    compliance: Optional[List[str]] = []


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = None
    target: Optional[str] = None
    scope: Optional[ProjectScope] = None
    status: Optional[ProjectStatus] = None
    client_name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    tags: Optional[List[str]] = None
    compliance: Optional[List[str]] = None


class ProjectInDB(ProjectBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    owner_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("tags", "compliance", mode="before")
    @classmethod
    def _parse_json_list(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return []
        return v if v is not None else []


class ProjectResponse(ProjectInDB):
    pass


class ProjectListResponse(BaseModel):
    items: List[ProjectResponse]
    total: int
    skip: int
    limit: int
