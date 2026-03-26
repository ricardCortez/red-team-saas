"""Report model - Phase 6 Reporting Engine + Phase 14 Professional Reports"""
import enum
from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, Enum as SAEnum, Float, DateTime,
    Boolean, JSON, LargeBinary,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from app.models.base import BaseModel


class ReportType(str, enum.Enum):
    executive = "executive"
    technical = "technical"
    compliance = "compliance"


class ReportFormat(str, enum.Enum):
    pdf = "pdf"
    html = "html"


class ReportStatus(str, enum.Enum):
    pending = "pending"
    generating = "generating"
    ready = "ready"
    failed = "failed"


class ReportClassification(str, enum.Enum):
    public = "public"
    internal = "internal"
    confidential = "confidential"
    restricted = "restricted"


# ── Phase 14 Enums ─────────────────────────────────────────────────────────────

class ReportTypeV2(str, enum.Enum):
    executive_summary = "executive_summary"
    detailed_findings = "detailed_findings"
    compliance = "compliance"
    risk_assessment = "risk_assessment"
    penetration_test = "penetration_test"
    vulnerability_scan = "vulnerability_scan"
    custom = "custom"


class ReportFormatV2(str, enum.Enum):
    pdf = "pdf"
    html = "html"
    excel = "excel"
    json = "json"


class ReportStatusV2(str, enum.Enum):
    draft = "draft"
    pending_review = "pending_review"
    approved = "approved"
    signed = "signed"
    published = "published"
    archived = "archived"


class Report(Base, BaseModel):
    """Professional pentest report with async generation lifecycle"""

    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    title = Column(String(500), nullable=False)
    report_type = Column(SAEnum(ReportType, name="reporttype"), nullable=False)
    report_format = Column(SAEnum(ReportFormat, name="reportformat"), default=ReportFormat.pdf)
    status = Column(SAEnum(ReportStatus, name="reportstatus"), default=ReportStatus.pending, index=True)
    classification = Column(
        SAEnum(ReportClassification, name="reportclassification"),
        default=ReportClassification.confidential,
    )

    # Scope / narrative fields
    scope_description = Column(Text, nullable=True)
    executive_summary = Column(Text, nullable=True)
    recommendations = Column(Text, nullable=True)

    # Generated file
    file_path = Column(String(1024), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    celery_task_id = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)

    # Stats snapshot at generation time
    total_findings = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)
    overall_risk = Column(Float, default=0.0)

    generated_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    project = relationship("Project", back_populates="reports", foreign_keys=[project_id])
    author = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<Report(id={self.id}, title={self.title!r}, status={self.status})>"


# ── Phase 14 Models ────────────────────────────────────────────────────────────

class ReportTemplate(Base, BaseModel):
    """Customizable report template with Jinja2 HTML and branding — Phase 14"""

    __tablename__ = "report_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    report_type = Column(SAEnum(ReportTypeV2, name="reporttypev2"), nullable=False)

    # Template structure
    header_template = Column(Text, nullable=True)
    sections = Column(JSON, default=list)       # [{name, include_by_default, order}]
    footer_template = Column(Text, nullable=True)
    css_styling = Column(Text, nullable=True)

    # Metadata
    variables = Column(JSON, default=list)      # [{name, type, default_value}]
    branding = Column(JSON, default=dict)        # {logo_url, company_name, colors}

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_user = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<ReportTemplate(id={self.id}, name={self.name!r})>"


class ReportV2(Base, BaseModel):
    """Enhanced report with multi-format, signatures, S3 storage — Phase 14"""

    __tablename__ = "reports_v2"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    project = relationship("Project", foreign_keys=[project_id])

    template_id = Column(Integer, ForeignKey("report_templates.id"), nullable=True)
    template = relationship("ReportTemplate")

    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    report_type = Column(SAEnum(ReportTypeV2, name="reporttypev2_report"), nullable=False)

    # Generation metadata
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    generated_by_user = relationship("User", foreign_keys=[generated_by])

    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)

    # Scope & findings summary
    findings_count = Column(Integer, default=0)
    compliance_mapping_id = Column(Integer, ForeignKey("compliance_mapping_results.id"), nullable=True)
    compliance_mapping = relationship("ComplianceMappingResult")

    summary_metadata = Column(JSON, default=dict)   # {total_findings, critical, high, medium, low}
    included_sections = Column(JSON, default=list)  # [{section_name, items_count}]

    # Status & review
    status = Column(SAEnum(ReportStatusV2, name="reportstatusv2"), default=ReportStatusV2.draft, index=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_by_user = relationship("User", foreign_keys=[reviewed_by])
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)

    # Digital signature
    signed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    signed_by_user = relationship("User", foreign_keys=[signed_by])
    signed_at = Column(DateTime(timezone=True), nullable=True)
    signature_certificate_fingerprint = Column(String(255), nullable=True)
    signature_metadata = Column(JSON, nullable=True)

    # Distribution
    is_published = Column(Boolean, default=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    published_to = Column(JSON, default=list)   # [{email, sent_at}]

    versions = relationship("ReportVersion", back_populates="report", cascade="all, delete-orphan")
    audit_logs = relationship("ReportAuditLog", back_populates="report", cascade="all, delete-orphan")
    signatures = relationship("DigitalSignature", back_populates="report", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ReportV2(id={self.id}, title={self.title!r}, status={self.status})>"


class ReportVersion(Base):
    """Immutable snapshot of a report at a given version — Phase 14"""

    __tablename__ = "report_versions"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports_v2.id"), nullable=False, index=True)
    report = relationship("ReportV2", back_populates="versions")

    version_number = Column(Integer, nullable=False)
    status = Column(SAEnum(ReportStatusV2, name="reportstatusv2_ver"), nullable=True)

    # S3 file keys
    pdf_file_key = Column(String(500), nullable=True)
    html_file_key = Column(String(500), nullable=True)
    excel_file_key = Column(String(500), nullable=True)

    file_size_bytes = Column(Integer, nullable=True)
    checksum_sha256 = Column(String(64), nullable=True)
    change_log = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<ReportVersion(report_id={self.report_id}, v={self.version_number})>"


class ReportSchedule(Base, BaseModel):
    """Cron-based schedule for automated report generation — Phase 14"""

    __tablename__ = "report_schedules"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    project = relationship("Project")

    template_id = Column(Integer, ForeignKey("report_templates.id"), nullable=True)
    template = relationship("ReportTemplate")

    report_type = Column(SAEnum(ReportTypeV2, name="reporttypev2_sched"), nullable=False)
    name = Column(String(200), nullable=False)

    cron_expression = Column(String(100), nullable=False)   # "0 0 * * 0" = weekly Sunday
    is_enabled = Column(Boolean, default=True)
    timezone = Column(String(50), default="UTC")

    recipient_emails = Column(JSON, default=list)
    include_in_dashboard = Column(Boolean, default=True)

    last_generated_at = Column(DateTime(timezone=True), nullable=True)
    next_scheduled_at = Column(DateTime(timezone=True), nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_user = relationship("User")

    def __repr__(self):
        return f"<ReportSchedule(id={self.id}, name={self.name!r}, cron={self.cron_expression!r})>"


class ReportAuditLog(Base):
    """Immutable audit trail entry for report lifecycle events — Phase 14"""

    __tablename__ = "report_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports_v2.id"), nullable=False, index=True)
    report = relationship("ReportV2", back_populates="audit_logs")

    action = Column(String(50), nullable=False)     # CREATED, SIGNED, PUBLISHED, VIEWED, DOWNLOADED
    action_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    action_by_user = relationship("User")

    details = Column(JSON, default=dict)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    previous_state = Column(JSON, nullable=True)
    new_state = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<ReportAuditLog(report_id={self.report_id}, action={self.action!r})>"


class DigitalSignature(Base):
    """X.509 digital signature attached to a report — Phase 14"""

    __tablename__ = "digital_signatures"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports_v2.id"), nullable=False, index=True)
    report = relationship("ReportV2", back_populates="signatures")

    signer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    signer = relationship("User")

    # Certificate info
    certificate_pem = Column(LargeBinary, nullable=False)
    certificate_issuer = Column(String(500), nullable=True)
    certificate_subject = Column(String(500), nullable=True)
    certificate_valid_from = Column(DateTime(timezone=True), nullable=True)
    certificate_valid_to = Column(DateTime(timezone=True), nullable=True)

    # Signature
    signature_algorithm = Column(String(50), default="RSA-SHA256")
    signature_value = Column(LargeBinary, nullable=False)
    signed_content_hash = Column(String(64), nullable=False)

    timestamp_authority = Column(String(200), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    is_valid = Column(Boolean, default=True)
    verification_result = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<DigitalSignature(id={self.id}, report_id={self.report_id}, valid={self.is_valid})>"
