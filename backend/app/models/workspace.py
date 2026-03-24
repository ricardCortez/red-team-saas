"""Workspace model - project/client isolation"""
import enum
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import BaseModel


class Workspace(Base, BaseModel):
    """Workspace model for isolating projects and clients"""

    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    client_name = Column(String(255), nullable=True, index=True)
    scope = Column(Text, nullable=True)  # JSON: list of IPs/domains in scope
    is_active = Column(Boolean, default=True, index=True)

    owner = relationship("User")
    tasks = relationship("Task", back_populates="workspace", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Workspace(id={self.id}, name={self.name}, client={self.client_name})>"
