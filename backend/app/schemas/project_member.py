"""ProjectMember schemas"""
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.models.project_member import ProjectRole


class MemberAdd(BaseModel):
    user_id: int
    role: ProjectRole = ProjectRole.viewer


class MemberUpdate(BaseModel):
    role: ProjectRole


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:         int
    project_id: int
    user_id:    int
    role:       ProjectRole
    added_at:   datetime
    added_by:   int | None = None
