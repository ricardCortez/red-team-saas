"""AI integration schemas"""
from pydantic import BaseModel, Field
from typing import Optional, List
from app.models.ai_config import AIProviderEnum


class AIConfigUpdate(BaseModel):
    is_enabled: bool = False
    api_key: Optional[str] = Field(None, description="Plain text key — will be encrypted")
    base_url: Optional[str] = None
    model: str = ""
    label: Optional[str] = None


class AIConfigResponse(BaseModel):
    provider: AIProviderEnum
    is_enabled: bool
    has_api_key: bool
    base_url: Optional[str]
    model: str
    label: Optional[str]

    class Config:
        from_attributes = True


class AITestResponse(BaseModel):
    provider: AIProviderEnum
    available: bool
    models: List[str]
    error: Optional[str]


class AIChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class AIChatRequest(BaseModel):
    messages: List[AIChatMessage]
    provider: Optional[AIProviderEnum] = None
    model: Optional[str] = None


class AIChatResponse(BaseModel):
    reply: str
    provider: AIProviderEnum
    model: str


class AIFindingAnalysis(BaseModel):
    severity: str
    explanation: str
    remediation: str
    provider: AIProviderEnum
    model: str
