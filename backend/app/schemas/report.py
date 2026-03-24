"""Report schemas - Phase 6"""
from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.report import ReportType, ReportFormat, ReportStatus, ReportClassification


class ReportCreate(BaseModel):
    project_id: int
    title: str
    report_type: ReportType
    report_format: Optional[ReportFormat] = ReportFormat.pdf
    classification: Optional[ReportClassification] = ReportClassification.confidential
    scope_description: Optional[str] = None
    executive_summary: Optional[str] = None
    recommendations: Optional[str] = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    created_by: int
    title: str
    report_type: ReportType
    report_format: ReportFormat
    status: ReportStatus
    classification: ReportClassification
    scope_description: Optional[str] = None
    executive_summary: Optional[str] = None
    recommendations: Optional[str] = None
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    overall_risk: float
    file_size_bytes: Optional[int] = None
    celery_task_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    generated_at: Optional[datetime] = None
