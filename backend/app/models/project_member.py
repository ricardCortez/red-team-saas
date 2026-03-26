"""ProjectMember model – per-project roles"""
import enum
from sqlalchemy import Column, Integer, ForeignKey, Enum as SQLEnum, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from app.models.base import BaseModel


class ProjectRole(str, enum.Enum):
    lead     = "lead"       # full access within the project
    operator = "operator"   # can execute scans
    viewer   = "viewer"     # read-only


class ProjectMember(Base, BaseModel):
    """Membership record linking a user to a project with a specific role."""

    __tablename__ = "project_members"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_user"),
    )

    id         = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role       = Column(SQLEnum(ProjectRole), default=ProjectRole.viewer, nullable=False)
    added_at   = Column(DateTime(timezone=True), server_default=func.now())
    added_by   = Column(Integer, ForeignKey("users.id"), nullable=True)

    project = relationship("Project", back_populates="members")
    user    = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<ProjectMember(project={self.project_id}, user={self.user_id}, role={self.role})>"
