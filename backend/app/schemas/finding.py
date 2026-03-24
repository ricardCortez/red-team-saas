"""Phase 5 Finding schemas"""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.finding import Severity, FindingStatus


class FindingBase(BaseModel):
    title: str
    description: Optional[str] = None
    severity: Severity
    status: FindingStatus = FindingStatus.open
    host: Optional[str] = None
    port: Optional[int] = None
    service: Optional[str] = None
    risk_score: float = 0.0


class FindingResponse(FindingBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    result_id: Optional[int] = None
    task_id: Optional[int] = None
    project_id: Optional[int] = None
    tool_name: Optional[str] = None
    fingerprint: Optional[str] = None
    is_duplicate: bool = False
    duplicate_of: Optional[int] = None
    false_positive: bool = False
    false_positive_reason: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class FindingUpdate(BaseModel):
    status: Optional[FindingStatus] = None
    severity: Optional[Severity] = None
    notes: Optional[str] = None
    assigned_to: Optional[int] = None
    false_positive_reason: Optional[str] = None


class FindingFilter(BaseModel):
    project_id: Optional[int] = None
    result_id: Optional[int] = None
    severity: Optional[Severity] = None
    status: Optional[FindingStatus] = None
    host: Optional[str] = None
    tool_name: Optional[str] = None
    min_risk_score: Optional[float] = None
    exclude_duplicates: bool = True


class FindingListResponse(BaseModel):
    items: list[FindingResponse]
    total: int
    skip: int
    limit: int
