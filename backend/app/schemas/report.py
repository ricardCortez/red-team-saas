"""Report schemas"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ReportStatus(str, Enum):
    draft = "draft"
    review = "review"
    final = "final"
    archived = "archived"


class ReportBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    executive_summary: Optional[str] = None
    findings: Optional[str] = None      # JSON string of findings list
    recommendations: Optional[str] = None
    workspace_id: Optional[int] = None


class ReportCreate(ReportBase):
    pass


class ReportUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=500)
    executive_summary: Optional[str] = None
    findings: Optional[str] = None
    recommendations: Optional[str] = None
    status: Optional[ReportStatus] = None


class ReportInDB(ReportBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    author_id: int
    status: ReportStatus
    signature_hash: Optional[str] = None
    signed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ReportResponse(ReportInDB):
    pass


class ReportListResponse(BaseModel):
    items: List[ReportResponse]
    total: int
    skip: int
    limit: int
