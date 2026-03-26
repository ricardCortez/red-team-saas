"""Target model – authorised scope entries per project"""
import enum
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, Enum as SQLEnum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from app.models.base import BaseModel


class TargetType(str, enum.Enum):
    ip       = "ip"
    cidr     = "cidr"
    hostname = "hostname"
    url      = "url"
    ip_range = "ip_range"


class TargetStatus(str, enum.Enum):
    in_scope     = "in_scope"
    out_of_scope = "out_of_scope"


class Target(Base, BaseModel):
    """A scoped target (host/IP/CIDR/URL) belonging to a project."""

    __tablename__ = "targets"

    id          = Column(Integer, primary_key=True, index=True)
    project_id  = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    added_by    = Column(Integer, ForeignKey("users.id"), nullable=False)

    value       = Column(String(512), nullable=False)   # IP, CIDR, hostname, URL
    target_type = Column(SQLEnum(TargetType), nullable=False)
    status      = Column(SQLEnum(TargetStatus), default=TargetStatus.in_scope, nullable=False)
    description = Column(Text, nullable=True)
    tags        = Column(String(512), nullable=True)    # CSV: "web,critical,dmz"

    # Populated by scans
    os_hint      = Column(String(255), nullable=True)
    tech_stack   = Column(String(255), nullable=True)
    last_scanned = Column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", back_populates="targets")
    adder   = relationship("User", foreign_keys=[added_by])

    def __repr__(self):
        return f"<Target(id={self.id}, value={self.value!r}, type={self.target_type})>"
