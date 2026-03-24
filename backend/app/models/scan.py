"""Scan model"""
import enum
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import BaseModel
from app.core.security import EncryptedString


class ScanStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ScanType(str, enum.Enum):
    recon = "recon"
    vuln_scan = "vuln_scan"
    exploitation = "exploitation"
    post_exploit = "post_exploit"
    brute_force = "brute_force"
    full = "full"


class Scan(Base, BaseModel):
    """Scan model for red team operations"""

    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    scan_type = Column(SQLEnum(ScanType), nullable=False, index=True)
    target = Column(String(255), nullable=False)
    options = Column(EncryptedString(4096), nullable=True)   # AES-256 encrypted JSON
    tools = Column(Text, nullable=True)                      # JSON array of tool names
    status = Column(SQLEnum(ScanStatus), default=ScanStatus.pending, nullable=False, index=True)
    progress = Column(Integer, default=0)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    celery_task_id = Column(String(255), nullable=True)

    project = relationship("Project", back_populates="scans")
    creator = relationship("User")
    findings = relationship("Finding", back_populates="scan", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Scan(id={self.id}, name={self.name!r}, status={self.status})>"
