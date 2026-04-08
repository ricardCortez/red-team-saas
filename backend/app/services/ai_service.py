"""AI service — resolves provider from user config and delegates calls"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.ai_config import UserAIConfig, AIProviderEnum
from app.core.security import EncryptionHandler
from app.core.ai.providers.base import AIProvider


def _build_provider(config: UserAIConfig) -> AIProvider:
    """Instantiate the correct provider class from a UserAIConfig row."""
    key = EncryptionHandler.decrypt(config.api_key_encrypted) if config.api_key_encrypted else ""
    url = config.base_url or ""
    p = config.provider

    if p == AIProviderEnum.ollama:
        from app.core.ai.providers.ollama import OllamaProvider
        return OllamaProvider(base_url=url or "http://host.docker.internal:11434")
    if p == AIProviderEnum.lmstudio:
        from app.core.ai.providers.lmstudio import LMStudioProvider
        return LMStudioProvider(base_url=url or "http://host.docker.internal:1234/v1")
    if p == AIProviderEnum.openai_compatible:
        from app.core.ai.providers.openai_compat import OpenAICompatProvider
        return OpenAICompatProvider(base_url=url, api_key=key)
    if p == AIProviderEnum.openai:
        from app.core.ai.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=key)
    if p == AIProviderEnum.anthropic:
        from app.core.ai.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider(api_key=key)
    if p == AIProviderEnum.gemini:
        from app.core.ai.providers.gemini_provider import GeminiProvider
        return GeminiProvider(api_key=key)
    if p == AIProviderEnum.groq:
        from app.core.ai.providers.groq_provider import GroqProvider
        return GroqProvider(api_key=key)
    if p == AIProviderEnum.mistral:
        from app.core.ai.providers.mistral_provider import MistralProvider
        return MistralProvider(api_key=key)
    # custom
    from app.core.ai.providers.custom_provider import CustomProvider
    return CustomProvider(base_url=url, api_key=key)


def get_user_configs(db: Session, user_id: int) -> List[UserAIConfig]:
    return db.query(UserAIConfig).filter(UserAIConfig.user_id == user_id).all()


def get_or_create_config(db: Session, user_id: int, provider: AIProviderEnum) -> UserAIConfig:
    cfg = db.query(UserAIConfig).filter(
        UserAIConfig.user_id == user_id,
        UserAIConfig.provider == provider,
    ).first()
    if not cfg:
        cfg = UserAIConfig(user_id=user_id, provider=provider)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def upsert_config(db: Session, user_id: int, provider: AIProviderEnum, data: dict) -> UserAIConfig:
    cfg = get_or_create_config(db, user_id, provider)
    if "api_key" in data and data["api_key"]:
        cfg.api_key_encrypted = EncryptionHandler.encrypt(data["api_key"])
    if "base_url" in data:
        cfg.base_url = data["base_url"]
    if "model" in data:
        cfg.model = data["model"]
    if "is_enabled" in data:
        cfg.is_enabled = data["is_enabled"]
    if "label" in data:
        cfg.label = data["label"]
    db.commit()
    db.refresh(cfg)
    return cfg


async def test_provider(db: Session, user_id: int, provider: AIProviderEnum) -> Dict[str, Any]:
    cfg = get_or_create_config(db, user_id, provider)
    p = _build_provider(cfg)
    return await p.test()


async def chat(db: Session, user_id: int, messages: List[Dict[str, str]],
               provider: Optional[AIProviderEnum], model: Optional[str]) -> Dict[str, Any]:
    if provider is None:
        cfg = db.query(UserAIConfig).filter(
            UserAIConfig.user_id == user_id, UserAIConfig.is_enabled == True
        ).first()
        if not cfg:
            raise ValueError("No AI provider configured and enabled.")
    else:
        cfg = get_or_create_config(db, user_id, provider)

    p = _build_provider(cfg)
    used_model = model or cfg.model or "default"
    reply = await p.chat(messages, used_model)
    return {"reply": reply, "provider": cfg.provider, "model": used_model}


async def analyze_finding(db: Session, user_id: int, finding: Dict[str, Any]) -> Dict[str, Any]:
    cfg = db.query(UserAIConfig).filter(
        UserAIConfig.user_id == user_id, UserAIConfig.is_enabled == True
    ).first()
    if not cfg:
        raise ValueError("No AI provider configured and enabled.")
    p = _build_provider(cfg)
    result = await p.analyze_finding(finding, cfg.model or "default")
    result["provider"] = cfg.provider
    result["model"] = cfg.model
    return result
