"""Result model"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, Float, Boolean
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import BaseModel
from app.core.security import EncryptedString


class Result(Base, BaseModel):
    """Result model"""

    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    # Legacy fields (kept for backwards compat)
    tool = Column(String(255), nullable=True)
    output = Column(EncryptedString(65535), nullable=True)   # AES-256 Fernet encrypted
    parsed_data = Column(EncryptedString(65535), nullable=True)  # AES-256 Fernet encrypted
    # Phase 4 fields
    tool_name = Column(String(255), nullable=True)
    target = Column(String(1024), nullable=True)
    raw_output = Column(Text, nullable=True)       # stored encrypted via EncryptionHandler
    parsed_output = Column(JSON, default=dict)
    findings = Column(JSON, default=list)
    risk_score = Column(Float, default=0.0)
    exit_code = Column(Integer, default=0)
    duration_seconds = Column(Float, default=0.0)
    success = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)

    task = relationship("Task", back_populates="results")
    findings_rel = relationship("Finding", back_populates="result", foreign_keys="Finding.result_id")

    def __repr__(self):
        return f"<Result(id={self.id}, task_id={self.task_id}, tool={self.tool_name or self.tool})>"
