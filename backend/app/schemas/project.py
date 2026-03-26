"""Project schemas"""
import json
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ProjectStatus(str, Enum):
    active    = "active"
    paused    = "paused"
    completed = "completed"
    archived  = "archived"


class ProjectScope(str, Enum):
    internal = "internal"
    external = "external"
    full     = "full"
    web      = "web"
    api      = "api"
    mobile   = "mobile"


class ProjectType(str, Enum):
    pentest       = "pentest"
    red_team      = "red_team"
    vulnerability = "vulnerability_assessment"
    compliance    = "compliance"


class ProjectBase(BaseModel):
    name:        str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)
    # Legacy single-target; optional – use Target model for scoped entries
    target:      Optional[str] = Field(None, description="IP, domain, or CIDR range (legacy)")
    scope:       ProjectScope = ProjectScope.external
    status:      ProjectStatus = ProjectStatus.active
    project_type: ProjectType = ProjectType.pentest
    client_name: Optional[str] = None
    start_date:  Optional[datetime] = None
    end_date:    Optional[datetime] = None
    tags:        Optional[List[str]] = []
    compliance:  Optional[List[str]] = []
    rules_of_engagement: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name:        Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = None
    target:      Optional[str] = None
    scope:       Optional[ProjectScope] = None
    status:      Optional[ProjectStatus] = None
    project_type: Optional[ProjectType] = None
    client_name: Optional[str] = None
    start_date:  Optional[datetime] = None
    end_date:    Optional[datetime] = None
    tags:        Optional[List[str]] = None
    compliance:  Optional[List[str]] = None
    rules_of_engagement: Optional[str] = None


class ProjectInDB(ProjectBase):
    model_config = ConfigDict(from_attributes=True)
    id:          int
    owner_id:    int
    is_active:   bool
    created_at:  datetime
    updated_at:  datetime
    archived_at: Optional[datetime] = None
    member_count: Optional[int] = 0
    target_count: Optional[int] = 0

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
    skip:  int
    limit: int
