"""Report model - Phase 6 Reporting Engine"""
import enum
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum as SAEnum, Float, DateTime
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
