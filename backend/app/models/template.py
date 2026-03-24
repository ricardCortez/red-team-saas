"""Template model - reusable tool configurations"""
import enum
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import BaseModel


class TemplateCategory(str, enum.Enum):
    brute_force = "brute_force"
    osint = "osint"
    enumeration = "enumeration"
    exploitation = "exploitation"
    post_exploitation = "post_exploitation"
    phishing = "phishing"
    network = "network"
    custom = "custom"


class Template(Base, BaseModel):
    """Reusable template for tool configurations"""

    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(SQLEnum(TemplateCategory), nullable=False, index=True)
    tool_configs = Column(Text, nullable=True)  # JSON - tool configuration payload
    is_public = Column(Boolean, default=False, index=True)
    usage_count = Column(Integer, default=0)

    creator = relationship("User")

    def __repr__(self):
        return f"<Template(id={self.id}, name={self.name}, category={self.category})>"
