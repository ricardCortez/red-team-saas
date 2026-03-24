"""Report model - pentest reports with digital signatures"""
import enum
import hashlib
import json
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum as SQLEnum, DateTime
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import BaseModel


class ReportStatus(str, enum.Enum):
    draft = "draft"
    review = "review"
    final = "final"
    archived = "archived"


class Report(Base, BaseModel):
    """Pentest report with digital signature support"""

    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    title = Column(String(500), nullable=False)
    executive_summary = Column(Text, nullable=True)
    findings = Column(Text, nullable=True)        # JSON list of findings
    recommendations = Column(Text, nullable=True)
    status = Column(SQLEnum(ReportStatus), default=ReportStatus.draft, nullable=False, index=True)
    signature_hash = Column(String(64), nullable=True)   # SHA-256 hex digest
    signed_at = Column(DateTime(timezone=True), nullable=True)

    author = relationship("User")
    workspace = relationship("Workspace", back_populates="reports")

    def compute_signature(self) -> str:
        """Compute SHA-256 signature of report content"""
        payload = json.dumps(
            {
                "title": self.title,
                "executive_summary": self.executive_summary,
                "findings": self.findings,
                "recommendations": self.recommendations,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def __repr__(self):
        return f"<Report(id={self.id}, title={self.title!r}, status={self.status})>"
