"""Result model"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import BaseModel
from app.core.security import EncryptedString


class Result(Base, BaseModel):
    """Result model"""

    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    tool = Column(String(255), nullable=False)
    output = Column(EncryptedString(65535), nullable=True)  # AES-256 Fernet encrypted
    parsed_data = Column(EncryptedString(65535), nullable=True)  # AES-256 Fernet encrypted

    task = relationship("Task", back_populates="results")

    def __repr__(self):
        return f"<Result(id={self.id}, task_id={self.task_id}, tool={self.tool})>"
