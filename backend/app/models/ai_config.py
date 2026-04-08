"""User AI provider configuration model"""
import enum
from sqlalchemy import Column, Integer, String, Boolean, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import BaseModel


class AIProviderEnum(str, enum.Enum):
    ollama = "ollama"
    lmstudio = "lmstudio"
    openai_compatible = "openai_compatible"
    openai = "openai"
    anthropic = "anthropic"
    gemini = "gemini"
    groq = "groq"
    mistral = "mistral"
    custom = "custom"


class UserAIConfig(Base, BaseModel):
    __tablename__ = "user_ai_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(SQLEnum(AIProviderEnum), nullable=False)
    is_enabled = Column(Boolean, default=False, nullable=False)
    api_key_encrypted = Column(Text, nullable=True)
    base_url = Column(String(512), nullable=True)
    model = Column(String(255), nullable=False, default="")
    label = Column(String(255), nullable=True)

    user = relationship("User", backref="ai_configs")
