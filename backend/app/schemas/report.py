"""Report schemas - Phase 6 + Phase 14"""
from pydantic import BaseModel, field_validator, ConfigDict
from typing import Any, Dict, List, Optional
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


# ── Phase 14 Schemas ───────────────────────────────────────────────────────────

class ReportV2Create(BaseModel):
    """Request body for creating a Phase 14 professional report."""
    project_id: int
    title: str
    report_type: str
    template_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    compliance_mapping_id: Optional[int] = None
    custom_variables: Optional[Dict[str, Any]] = None
    formats: List[str] = ["pdf", "html"]

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()

    @field_validator("formats")
    @classmethod
    def valid_formats(cls, v: List[str]) -> List[str]:
        allowed = {"pdf", "html", "excel", "json"}
        invalid = set(v) - allowed
        if invalid:
            raise ValueError(f"Unsupported format(s): {invalid}")
        return v


class ReportV2Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    report_type: str
    status: str
    generated_at: Optional[datetime] = None
    findings_count: int
    summary_metadata: Optional[Dict[str, Any]] = None
    is_published: bool = False
    signed_at: Optional[datetime] = None
    created_at: datetime


class ReportTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    report_type: str
    sections: Optional[List[Dict[str, Any]]] = None
    css_styling: Optional[str] = None
    branding: Optional[Dict[str, Any]] = None
    variables: Optional[List[Dict[str, Any]]] = None


class ReportTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    report_type: str
    description: Optional[str] = None
    sections: Optional[List[Dict[str, Any]]] = None
    branding: Optional[Dict[str, Any]] = None
    created_at: datetime


class ReportVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_id: int
    version_number: int
    status: Optional[str] = None
    pdf_file_key: Optional[str] = None
    html_file_key: Optional[str] = None
    excel_file_key: Optional[str] = None
    file_size_bytes: Optional[int] = None
    checksum_sha256: Optional[str] = None
    created_at: datetime


class ReportScheduleCreate(BaseModel):
    project_id: int
    report_type: str
    name: str
    cron_expression: str
    template_id: Optional[int] = None
    is_enabled: bool = True
    timezone: str = "UTC"
    recipient_emails: Optional[List[str]] = None
    include_in_dashboard: bool = True


class ReportScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    cron_expression: str
    is_enabled: bool
    timezone: str
    last_generated_at: Optional[datetime] = None
    next_scheduled_at: Optional[datetime] = None
    created_at: datetime


class DigitalSignatureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_id: int
    signer_id: int
    signature_algorithm: str
    signed_content_hash: str
    certificate_issuer: Optional[str] = None
    certificate_subject: Optional[str] = None
    certificate_valid_from: Optional[datetime] = None
    certificate_valid_to: Optional[datetime] = None
    is_valid: bool
    timestamp: Optional[datetime] = None
    verification_result: Optional[Dict[str, Any]] = None


class ReportAuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    action_by: Optional[int] = None
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
