"""Task model"""
from sqlalchemy import Column, Integer, String, ForeignKey, Enum as SQLEnum, Text, JSON
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import BaseModel
from app.core.constants import TaskStatus
from app.core.security import EncryptedString
import enum


class TaskStatusEnum(str, enum.Enum):
    pending = TaskStatus.PENDING
    running = TaskStatus.RUNNING
    completed = TaskStatus.COMPLETED
    failed = TaskStatus.FAILED
    cancelled = TaskStatus.CANCELLED
    retrying = TaskStatus.RETRYING


class Task(Base, BaseModel):
    """Task model"""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(500), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    status = Column(SQLEnum(TaskStatusEnum), default=TaskStatusEnum.pending, index=True)
    tool_name = Column(String(255), nullable=True)
    target = Column(String(1024), nullable=True)
    options = Column(JSON, default=dict)
    parameters = Column(EncryptedString(4096), nullable=True)  # legacy encrypted params
    celery_task_id = Column(String(255), nullable=True, index=True)
    error_message = Column(Text, nullable=True)

    user = relationship("User", back_populates="tasks")
    workspace = relationship("Workspace", back_populates="tasks")
    results = relationship("Result", back_populates="task", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Task(id={self.id}, status={self.status}, tool={self.tool_name})>"
