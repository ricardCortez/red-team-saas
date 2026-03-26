"""Finding model (scan results/vulnerabilities) - Phase 3 + Phase 5"""
import enum
from sqlalchemy import Column, Integer, String, Text, Boolean, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import BaseModel
from app.core.security import EncryptedString


class Severity(str, enum.Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class FindingStatus(str, enum.Enum):
    open = "open"
    confirmed = "confirmed"
    false_positive = "false_positive"
    resolved = "resolved"
    accepted_risk = "accepted_risk"


class Finding(Base, BaseModel):
    """Finding/vulnerability discovered during a scan or tool execution"""

    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)

    # Phase 3: scan-based finding (nullable for Phase 5 compat)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=True, index=True)

    # Phase 5: result/task-based finding
    result_id = Column(Integer, ForeignKey("results.id"), nullable=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)

    # Core finding data
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    severity = Column(SQLEnum(Severity), nullable=False, index=True)

    # Phase 5: lifecycle status
    status = Column(SQLEnum(FindingStatus), default=FindingStatus.open, nullable=False, index=True)
    risk_score = Column(Float, default=0.0)

    # Phase 5: network context (parallel to Phase 3 affected_host/affected_port)
    host = Column(String(255), nullable=True, index=True)
    port = Column(Integer, nullable=True)
    service = Column(String(100), nullable=True)
    tool_name = Column(String(255), nullable=True, index=True)  # Phase 5 alias for tool

    # Phase 3 legacy fields
    tool = Column(String(100), nullable=True, index=True)
    affected_host = Column(String(255), nullable=True, index=True)
    affected_port = Column(Integer, nullable=True)
    raw_output = Column(EncryptedString(65535), nullable=True)
    parsed_data = Column(EncryptedString(65535), nullable=True)
    cve_ids = Column(Text, nullable=True)    # JSON array ["CVE-2021-1234"]
    mitre_ids = Column(Text, nullable=True)  # JSON array ["T1190"]
    remediation = Column(Text, nullable=True)
    verified = Column(Boolean, default=False, index=True)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Phase 3 + Phase 5: false positive handling
    false_positive = Column(Boolean, default=False, index=True)
    false_positive_reason = Column(Text, nullable=True)

    # Phase 5: deduplication
    fingerprint = Column(String(64), nullable=True, index=True)
    is_duplicate = Column(Boolean, default=False, index=True)
    duplicate_of = Column(Integer, ForeignKey("findings.id"), nullable=True)

    # Phase 5: workflow metadata
    notes = Column(Text, nullable=True)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    scan = relationship("Scan", back_populates="findings")
    result = relationship("Result", back_populates="findings_rel", foreign_keys=[result_id])
    task = relationship("Task", foreign_keys=[task_id])
    project = relationship("Project", back_populates="findings", foreign_keys=[project_id])
    verifier = relationship("User", foreign_keys=[verified_by])
    assignee = relationship("User", foreign_keys=[assigned_to])
    duplicate_parent = relationship("Finding", remote_side=[id], foreign_keys=[duplicate_of])

    def __repr__(self):
        return f"<Finding(id={self.id}, severity={self.severity}, title={self.title!r})>"
