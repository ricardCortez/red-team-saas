"""AI integration endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.ai_config import AIProviderEnum
from app.schemas.ai import (
    AIConfigUpdate, AIConfigResponse, AITestResponse,
    AIChatRequest, AIChatResponse, AIFindingAnalysis,
)
from app.services import ai_service
from app.models.finding import Finding

router = APIRouter(prefix="/ai", tags=["AI"])

PROVIDER_META = {
    AIProviderEnum.ollama: {"label": "Ollama", "type": "local", "default_url": "http://localhost:11434"},
    AIProviderEnum.lmstudio: {"label": "LM Studio", "type": "local", "default_url": "http://localhost:1234/v1"},
    AIProviderEnum.openai_compatible: {"label": "OpenAI Compatible", "type": "local", "default_url": "http://localhost:8080/v1"},
    AIProviderEnum.openai: {"label": "OpenAI", "type": "cloud", "default_url": None},
    AIProviderEnum.anthropic: {"label": "Anthropic (Claude)", "type": "cloud", "default_url": None},
    AIProviderEnum.gemini: {"label": "Google Gemini", "type": "cloud", "default_url": None},
    AIProviderEnum.groq: {"label": "Groq", "type": "cloud", "default_url": None},
    AIProviderEnum.mistral: {"label": "Mistral", "type": "cloud", "default_url": None},
    AIProviderEnum.custom: {"label": "Custom", "type": "custom", "default_url": None},
}


@router.get("/providers")
def list_providers():
    return [{"provider": p.value, **meta} for p, meta in PROVIDER_META.items()]


@router.get("/config", response_model=List[AIConfigResponse])
def get_configs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    configs = ai_service.get_user_configs(db, current_user.id)
    return [
        AIConfigResponse(
            provider=c.provider,
            is_enabled=c.is_enabled,
            has_api_key=bool(c.api_key_encrypted),
            base_url=c.base_url,
            model=c.model,
            label=c.label,
        )
        for c in configs
    ]


@router.put("/config/{provider}", response_model=AIConfigResponse)
def update_config(
    provider: AIProviderEnum,
    body: AIConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cfg = ai_service.upsert_config(db, current_user.id, provider, body.model_dump())
    return AIConfigResponse(
        provider=cfg.provider,
        is_enabled=cfg.is_enabled,
        has_api_key=bool(cfg.api_key_encrypted),
        base_url=cfg.base_url,
        model=cfg.model,
        label=cfg.label,
    )


@router.post("/test/{provider}", response_model=AITestResponse)
async def test_provider(
    provider: AIProviderEnum,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await ai_service.test_provider(db, current_user.id, provider)
    return AITestResponse(provider=provider, **result)


@router.post("/chat", response_model=AIChatResponse)
async def chat(
    body: AIChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await ai_service.chat(
            db, current_user.id,
            [m.model_dump() for m in body.messages],
            body.provider, body.model,
        )
        return AIChatResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/analyze/finding/{finding_id}", response_model=AIFindingAnalysis)
async def analyze_finding(
    finding_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    try:
        result = await ai_service.analyze_finding(
            db, current_user.id,
            {"title": finding.title, "description": finding.description,
             "host": finding.host, "severity": str(finding.severity)},
        )
        return AIFindingAnalysis(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
