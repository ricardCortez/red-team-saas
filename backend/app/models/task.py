"""Task model"""
from sqlalchemy import Column, Integer, String, ForeignKey, Enum as SQLEnum
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


class Task(Base, BaseModel):
    """Task model"""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    status = Column(SQLEnum(TaskStatusEnum), default=TaskStatusEnum.pending, index=True)
    tool_name = Column(String(255), nullable=True)
    parameters = Column(EncryptedString(4096), nullable=True)  # AES-256 Fernet encrypted

    user = relationship("User", back_populates="tasks")
    workspace = relationship("Workspace", back_populates="tasks")
    results = relationship("Result", back_populates="task", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Task(id={self.id}, status={self.status}, tool={self.tool_name})>"
