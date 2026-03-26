"""Project model"""
import enum
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import BaseModel


class ProjectStatus(str, enum.Enum):
    active    = "active"
    paused    = "paused"
    completed = "completed"
    archived  = "archived"


class ProjectScope(str, enum.Enum):
    internal = "internal"
    external = "external"
    full     = "full"
    web      = "web"
    api      = "api"
    mobile   = "mobile"


class ProjectType(str, enum.Enum):
    pentest              = "pentest"
    red_team             = "red_team"
    vulnerability        = "vulnerability_assessment"
    compliance           = "compliance"


class Project(Base, BaseModel):
    """Project model for red team engagements"""

    __tablename__ = "projects"

    id           = Column(Integer, primary_key=True, index=True)
    owner_id     = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name         = Column(String(100), nullable=False, index=True)
    description  = Column(Text, nullable=True)
    # Legacy single-target field (kept for backward compat); use Target model for scoped targets
    target       = Column(String(255), nullable=True)
    scope        = Column(SQLEnum(ProjectScope), default=ProjectScope.external, nullable=False)
    status       = Column(SQLEnum(ProjectStatus), default=ProjectStatus.active, nullable=False, index=True)
    project_type = Column(SQLEnum(ProjectType), default=ProjectType.pentest, nullable=False)
    client_name  = Column(String(255), nullable=True, index=True)
    start_date   = Column(DateTime(timezone=True), nullable=True)
    end_date     = Column(DateTime(timezone=True), nullable=True)
    tags         = Column(Text, nullable=True)        # JSON array of strings
    compliance   = Column(Text, nullable=True)        # JSON array: ["PCI", "HIPAA", "GDPR"]
    rules_of_engagement = Column(Text, nullable=True)
    is_active    = Column(Boolean, default=True, index=True)
    archived_at  = Column(DateTime(timezone=True), nullable=True)

    owner   = relationship("User")
    scans   = relationship("Scan", back_populates="project", cascade="all, delete-orphan")
    # Phase 9 relationships
    members  = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    targets  = relationship("Target", back_populates="project", cascade="all, delete-orphan")
    tasks    = relationship("Task", back_populates="project")
    findings = relationship("Finding", back_populates="project",
                            foreign_keys="Finding.project_id")
    reports  = relationship("Report", back_populates="project",
                            foreign_keys="Report.project_id")

    def __repr__(self):
        return f"<Project(id={self.id}, name={self.name!r}, status={self.status})>"
