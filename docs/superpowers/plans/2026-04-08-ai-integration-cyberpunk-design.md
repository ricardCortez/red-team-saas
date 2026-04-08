# AI Integration + Cyberpunk Design — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add multi-provider AI support (local + cloud) to Red Team SaaS with chat, findings analysis, and config UI; restyle the frontend with a cyberpunk/hacker aesthetic.

**Architecture:** Backend adds a new `app/core/ai/` module with a provider abstraction, a `user_ai_configs` DB table, and a `/api/v1/ai/` router. Frontend adds an AI settings tab, a floating chat panel, and per-finding analysis—all styled with neon cyberpunk CSS.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, httpx, openai SDK, anthropic SDK, google-generativeai; React 19, TypeScript, Zustand, Tailwind v4, lucide-react

---

## Task 1: Add AI dependencies

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add packages to requirements.txt**

Open `backend/requirements.txt` and append at the end:

```
# AI providers
openai>=1.35.0
anthropic>=0.28.0
google-generativeai>=0.7.0
```

- [ ] **Step 2: Rebuild the API container**

```bash
docker compose build api && docker compose up -d api
```

Expected: build completes, container restarts healthy.

- [ ] **Step 3: Verify packages installed**

```bash
docker exec redteam-api pip show openai anthropic google-generativeai | grep Name
```

Expected output:
```
Name: openai
Name: anthropic
Name: google-generativeai
```

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt
git commit -m "feat(ai): add openai, anthropic, google-generativeai dependencies"
```

---

## Task 2: AI database model + migration

**Files:**
- Create: `backend/app/models/ai_config.py`
- Create: `backend/alembic/versions/0005_add_user_ai_configs.py`
- Modify: `backend/app/models/__init__.py` (add import)

- [ ] **Step 1: Create the model**

Create `backend/app/models/ai_config.py`:

```python
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
```

- [ ] **Step 2: Check existing models __init__**

```bash
cat backend/app/models/__init__.py
```

- [ ] **Step 3: Add import to models __init__**

Open `backend/app/models/__init__.py` and add:
```python
from app.models.ai_config import UserAIConfig, AIProviderEnum  # noqa: F401
```

- [ ] **Step 4: Create Alembic migration**

Create `backend/alembic/versions/0005_add_user_ai_configs.py`:

```python
"""Add user_ai_configs table

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

AI_PROVIDER_ENUM = "aiproviderenum"


def upgrade() -> None:
    sa.Enum(
        "ollama", "lmstudio", "openai_compatible", "openai",
        "anthropic", "gemini", "groq", "mistral", "custom",
        name=AI_PROVIDER_ENUM,
    ).create(op.get_bind(), checkfirst=True)

    op.create_table(
        "user_ai_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.Enum(
            "ollama", "lmstudio", "openai_compatible", "openai",
            "anthropic", "gemini", "groq", "mistral", "custom",
            name=AI_PROVIDER_ENUM, create_type=False,
        ), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("base_url", sa.String(512), nullable=True),
        sa.Column("model", sa.String(255), nullable=False, server_default=""),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("user_id", "provider", name="uq_user_ai_provider"),
    )
    op.create_index("ix_user_ai_configs_user_id", "user_ai_configs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_ai_configs_user_id", "user_ai_configs")
    op.drop_table("user_ai_configs")
    sa.Enum(name=AI_PROVIDER_ENUM).drop(op.get_bind(), checkfirst=True)
```

- [ ] **Step 5: Run migration**

```bash
docker exec redteam-api alembic upgrade head
```

Expected: `Running upgrade 0004 -> 0005, Add user_ai_configs table`

- [ ] **Step 6: Verify table exists**

```bash
docker exec redteam-postgres psql -U redteam -d redteam_db -c "\d user_ai_configs"
```

Expected: table columns listed.

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/ai_config.py backend/app/models/__init__.py backend/alembic/versions/0005_add_user_ai_configs.py
git commit -m "feat(ai): add user_ai_configs model and migration"
```

---

## Task 3: AI provider abstraction + local providers

**Files:**
- Create: `backend/app/core/ai/__init__.py`
- Create: `backend/app/core/ai/providers/__init__.py`
- Create: `backend/app/core/ai/providers/base.py`
- Create: `backend/app/core/ai/providers/ollama.py`
- Create: `backend/app/core/ai/providers/lmstudio.py`
- Create: `backend/app/core/ai/providers/openai_compat.py`

- [ ] **Step 1: Create package init files**

Create `backend/app/core/ai/__init__.py`:
```python
"""AI provider abstraction layer"""
```

Create `backend/app/core/ai/providers/__init__.py`:
```python
"""AI provider implementations"""
```

- [ ] **Step 2: Create base provider**

Create `backend/app/core/ai/providers/base.py`:

```python
"""Abstract base class for all AI providers"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class AIProvider(ABC):
    """Base interface every AI provider must implement."""

    @abstractmethod
    async def test(self) -> Dict[str, Any]:
        """Check provider availability.
        Returns dict: {"available": bool, "models": list[str], "error": str|None}
        """
        ...

    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], model: str) -> str:
        """Send messages and return the assistant reply text."""
        ...

    @abstractmethod
    async def analyze_finding(self, finding: Dict[str, Any], model: str) -> Dict[str, Any]:
        """Analyze a security finding.
        Returns dict: {"severity": str, "explanation": str, "remediation": str}
        """
        ...

    def _finding_prompt(self, finding: Dict[str, Any]) -> str:
        return (
            f"You are a cybersecurity expert. Analyze this security finding and respond with JSON only.\n"
            f"Finding: {finding.get('title', '')}\n"
            f"Description: {finding.get('description', '')}\n"
            f"Host: {finding.get('host', 'unknown')}\n"
            f"Current severity: {finding.get('severity', 'unknown')}\n\n"
            f"Respond with this exact JSON structure:\n"
            f'{{"severity": "critical|high|medium|low|info", '
            f'"explanation": "brief technical explanation", '
            f'"remediation": "step-by-step remediation advice"}}'
        )
```

- [ ] **Step 3: Create Ollama provider**

Create `backend/app/core/ai/providers/ollama.py`:

```python
"""Ollama local AI provider"""
import httpx
from typing import List, Dict, Any
from app.core.ai.providers.base import AIProvider
import json
import logging

logger = logging.getLogger(__name__)


class OllamaProvider(AIProvider):
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")

    async def test(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                r.raise_for_status()
                data = r.json()
                models = [m["name"] for m in data.get("models", [])]
                return {"available": True, "models": models, "error": None}
        except Exception as e:
            return {"available": False, "models": [], "error": str(e)}

    async def chat(self, messages: List[Dict[str, str]], model: str) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                f"{self.base_url}/api/chat",
                json={"model": model, "messages": messages, "stream": False},
            )
            r.raise_for_status()
            return r.json()["message"]["content"]

    async def analyze_finding(self, finding: Dict[str, Any], model: str) -> Dict[str, Any]:
        prompt = self._finding_prompt(finding)
        reply = await self.chat([{"role": "user", "content": prompt}], model)
        try:
            start = reply.find("{")
            end = reply.rfind("}") + 1
            return json.loads(reply[start:end])
        except Exception:
            return {"severity": finding.get("severity", "unknown"), "explanation": reply, "remediation": "See explanation above."}
```

- [ ] **Step 4: Create LM Studio provider**

Create `backend/app/core/ai/providers/lmstudio.py`:

```python
"""LM Studio local AI provider (OpenAI-compatible)"""
from app.core.ai.providers.openai_compat import OpenAICompatProvider


class LMStudioProvider(OpenAICompatProvider):
    """LM Studio exposes an OpenAI-compatible API."""

    def __init__(self, base_url: str = "http://localhost:1234/v1"):
        super().__init__(base_url=base_url, api_key="lm-studio")
```

- [ ] **Step 5: Create OpenAI-compatible provider**

Create `backend/app/core/ai/providers/openai_compat.py`:

```python
"""Generic OpenAI-compatible provider (covers LM Studio, local OpenAI proxies, etc.)"""
import httpx
import json
from typing import List, Dict, Any
from app.core.ai.providers.base import AIProvider
import logging

logger = logging.getLogger(__name__)


class OpenAICompatProvider(AIProvider):
    def __init__(self, base_url: str, api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    async def test(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.base_url}/models", headers=self._headers())
                r.raise_for_status()
                data = r.json()
                models = [m["id"] for m in data.get("data", [])]
                return {"available": True, "models": models, "error": None}
        except Exception as e:
            return {"available": False, "models": [], "error": str(e)}

    async def chat(self, messages: List[Dict[str, str]], model: str) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={"model": model, "messages": messages},
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]

    async def analyze_finding(self, finding: Dict[str, Any], model: str) -> Dict[str, Any]:
        prompt = self._finding_prompt(finding)
        reply = await self.chat([{"role": "user", "content": prompt}], model)
        try:
            start = reply.find("{")
            end = reply.rfind("}") + 1
            return json.loads(reply[start:end])
        except Exception:
            return {"severity": finding.get("severity", "unknown"), "explanation": reply, "remediation": "See explanation above."}
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/ai/
git commit -m "feat(ai): add provider base + Ollama + LM Studio + OpenAI-compat providers"
```

---

## Task 4: Cloud AI providers

**Files:**
- Create: `backend/app/core/ai/providers/openai_provider.py`
- Create: `backend/app/core/ai/providers/anthropic_provider.py`
- Create: `backend/app/core/ai/providers/gemini_provider.py`
- Create: `backend/app/core/ai/providers/groq_provider.py`
- Create: `backend/app/core/ai/providers/mistral_provider.py`
- Create: `backend/app/core/ai/providers/custom_provider.py`

- [ ] **Step 1: OpenAI provider**

Create `backend/app/core/ai/providers/openai_provider.py`:

```python
"""OpenAI provider"""
import json
from typing import List, Dict, Any
from openai import AsyncOpenAI
from app.core.ai.providers.base import AIProvider


class OpenAIProvider(AIProvider):
    MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]

    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def test(self) -> Dict[str, Any]:
        try:
            models = await self.client.models.list()
            names = [m.id for m in models.data if "gpt" in m.id][:10]
            return {"available": True, "models": names or self.MODELS, "error": None}
        except Exception as e:
            return {"available": False, "models": [], "error": str(e)}

    async def chat(self, messages: List[Dict[str, str]], model: str) -> str:
        resp = await self.client.chat.completions.create(model=model, messages=messages)
        return resp.choices[0].message.content

    async def analyze_finding(self, finding: Dict[str, Any], model: str) -> Dict[str, Any]:
        prompt = self._finding_prompt(finding)
        reply = await self.chat([{"role": "user", "content": prompt}], model)
        try:
            start = reply.find("{")
            end = reply.rfind("}") + 1
            return json.loads(reply[start:end])
        except Exception:
            return {"severity": finding.get("severity", "unknown"), "explanation": reply, "remediation": "See explanation above."}
```

- [ ] **Step 2: Anthropic provider**

Create `backend/app/core/ai/providers/anthropic_provider.py`:

```python
"""Anthropic Claude provider"""
import json
from typing import List, Dict, Any
import anthropic
from app.core.ai.providers.base import AIProvider


class AnthropicProvider(AIProvider):
    MODELS = ["claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-5-20251001"]

    def __init__(self, api_key: str):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    async def test(self) -> Dict[str, Any]:
        try:
            # Anthropic has no list-models endpoint — do a minimal message
            await self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}],
            )
            return {"available": True, "models": self.MODELS, "error": None}
        except Exception as e:
            return {"available": False, "models": [], "error": str(e)}

    async def chat(self, messages: List[Dict[str, str]], model: str) -> str:
        resp = await self.client.messages.create(
            model=model, max_tokens=4096, messages=messages
        )
        return resp.content[0].text

    async def analyze_finding(self, finding: Dict[str, Any], model: str) -> Dict[str, Any]:
        prompt = self._finding_prompt(finding)
        reply = await self.chat([{"role": "user", "content": prompt}], model)
        try:
            start = reply.find("{")
            end = reply.rfind("}") + 1
            return json.loads(reply[start:end])
        except Exception:
            return {"severity": finding.get("severity", "unknown"), "explanation": reply, "remediation": "See explanation above."}
```

- [ ] **Step 3: Gemini provider**

Create `backend/app/core/ai/providers/gemini_provider.py`:

```python
"""Google Gemini provider"""
import json
from typing import List, Dict, Any
import google.generativeai as genai
from app.core.ai.providers.base import AIProvider


class GeminiProvider(AIProvider):
    MODELS = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"]

    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)

    async def test(self) -> Dict[str, Any]:
        try:
            models = [m.name for m in genai.list_models() if "generateContent" in m.supported_generation_methods]
            return {"available": True, "models": models or self.MODELS, "error": None}
        except Exception as e:
            return {"available": False, "models": [], "error": str(e)}

    async def chat(self, messages: List[Dict[str, str]], model: str) -> str:
        m = genai.GenerativeModel(model_name=model)
        history = []
        for msg in messages[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            history.append({"role": role, "parts": [msg["content"]]})
        chat = m.start_chat(history=history)
        resp = chat.send_message(messages[-1]["content"])
        return resp.text

    async def analyze_finding(self, finding: Dict[str, Any], model: str) -> Dict[str, Any]:
        prompt = self._finding_prompt(finding)
        reply = await self.chat([{"role": "user", "content": prompt}], model)
        try:
            start = reply.find("{")
            end = reply.rfind("}") + 1
            return json.loads(reply[start:end])
        except Exception:
            return {"severity": finding.get("severity", "unknown"), "explanation": reply, "remediation": "See explanation above."}
```

- [ ] **Step 4: Groq provider**

Create `backend/app/core/ai/providers/groq_provider.py`:

```python
"""Groq provider (OpenAI-compatible API)"""
from app.core.ai.providers.openai_compat import OpenAICompatProvider


class GroqProvider(OpenAICompatProvider):
    MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]

    def __init__(self, api_key: str):
        super().__init__(base_url="https://api.groq.com/openai/v1", api_key=api_key)

    async def test(self):
        result = await super().test()
        if result["available"] and not result["models"]:
            result["models"] = self.MODELS
        return result
```

- [ ] **Step 5: Mistral provider**

Create `backend/app/core/ai/providers/mistral_provider.py`:

```python
"""Mistral provider (OpenAI-compatible API)"""
from app.core.ai.providers.openai_compat import OpenAICompatProvider


class MistralProvider(OpenAICompatProvider):
    MODELS = ["mistral-large-latest", "mistral-small-latest", "open-mistral-7b"]

    def __init__(self, api_key: str):
        super().__init__(base_url="https://api.mistral.ai/v1", api_key=api_key)

    async def test(self):
        result = await super().test()
        if result["available"] and not result["models"]:
            result["models"] = self.MODELS
        return result
```

- [ ] **Step 6: Custom provider**

Create `backend/app/core/ai/providers/custom_provider.py`:

```python
"""Custom OpenAI-compatible provider with user-defined base_url"""
from app.core.ai.providers.openai_compat import OpenAICompatProvider


class CustomProvider(OpenAICompatProvider):
    def __init__(self, base_url: str, api_key: str = ""):
        super().__init__(base_url=base_url, api_key=api_key)
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/core/ai/providers/
git commit -m "feat(ai): add OpenAI, Anthropic, Gemini, Groq, Mistral, Custom providers"
```

---

## Task 5: AI service + schemas

**Files:**
- Create: `backend/app/schemas/ai.py`
- Create: `backend/app/services/ai_service.py`

- [ ] **Step 1: Create schemas**

Create `backend/app/schemas/ai.py`:

```python
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
```

- [ ] **Step 2: Create AI service**

Create `backend/app/services/ai_service.py`:

```python
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
        return OllamaProvider(base_url=url or "http://localhost:11434")
    if p == AIProviderEnum.lmstudio:
        from app.core.ai.providers.lmstudio import LMStudioProvider
        return LMStudioProvider(base_url=url or "http://localhost:1234/v1")
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
    # pick first enabled provider if not specified
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
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/ai.py backend/app/services/ai_service.py
git commit -m "feat(ai): add AI schemas and service layer"
```

---

## Task 6: AI API endpoints + register router

**Files:**
- Create: `backend/app/api/v1/endpoints/ai.py`
- Modify: `backend/app/api/v1/router.py`

- [ ] **Step 1: Create endpoints**

Create `backend/app/api/v1/endpoints/ai.py`:

```python
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
```

- [ ] **Step 2: Register router**

Open `backend/app/api/v1/router.py` and add after the last import:

```python
from app.api.v1.endpoints import ai as ai_endpoints
```

And add after the last `include_router` call:

```python
# AI Integration
api_router.include_router(ai_endpoints.router, tags=["AI"])
```

- [ ] **Step 3: Restart API and verify routes**

```bash
docker compose restart api
sleep 3
curl -s http://localhost:8000/api/v1/ai/providers | python -m json.tool | head -20
```

Expected: JSON list of 9 providers.

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/endpoints/ai.py backend/app/api/v1/router.py
git commit -m "feat(ai): add AI endpoints and register router"
```

---

## Task 7: Cyberpunk CSS + core component updates

**Files:**
- Modify: `frontend/src/index.css`
- Modify: `frontend/src/components/Common/Card.tsx`
- Modify: `frontend/src/components/Common/Navbar.tsx`
- Modify: `frontend/src/components/Common/Badge.tsx`
- Modify: `frontend/src/components/Common/Sidebar.tsx`
- Modify: `frontend/src/utils/cn.ts`

- [ ] **Step 1: Update index.css with cyberpunk theme**

Replace the entire content of `frontend/src/index.css` with:

```css
@import "tailwindcss";

@layer base {
  :root {
    --color-primary: #6366f1;
    --color-primary-dark: #4f46e5;
    --color-danger: #ef4444;
    --color-warning: #f59e0b;
    --color-success: #10b981;
    --color-info: #3b82f6;
    --color-bg: #0a0f1e;
    --color-bg-secondary: #0d1526;
    --color-bg-tertiary: #162035;
    --color-text: #e2e8f0;
    --color-text-secondary: #64748b;
    --color-border: #1e2d45;
    /* Neon accents */
    --neon-green: #00ff41;
    --neon-red: #ff0040;
    --neon-blue: #00d4ff;
    --neon-purple: #bf00ff;
    --glow-green: 0 0 8px #00ff41, 0 0 20px #00ff4122;
    --glow-red: 0 0 8px #ff0040, 0 0 20px #ff004022;
    --glow-blue: 0 0 8px #00d4ff, 0 0 20px #00d4ff22;
  }
}

body {
  margin: 0;
  background-color: var(--color-bg);
  color: var(--color-text);
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  background-image:
    linear-gradient(rgba(0, 255, 65, 0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 255, 65, 0.02) 1px, transparent 1px);
  background-size: 40px 40px;
}

#root { min-height: 100vh; }

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--color-bg-secondary); }
::-webkit-scrollbar-thumb { background: var(--neon-green); border-radius: 2px; opacity: 0.3; }

/* Severity */
.severity-critical { color: #ff0040; text-shadow: 0 0 8px #ff004066; }
.severity-high     { color: #ff6b00; text-shadow: 0 0 8px #ff6b0066; }
.severity-medium   { color: #ffd000; text-shadow: 0 0 8px #ffd00066; }
.severity-low      { color: #00d4ff; text-shadow: 0 0 8px #00d4ff66; }
.severity-info     { color: #64748b; }

/* Neon pulse animation */
@keyframes neon-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
.neon-pulse { animation: neon-pulse 2s ease-in-out infinite; }

/* Neon glow utilities */
.glow-green { box-shadow: var(--glow-green); border-color: var(--neon-green) !important; }
.glow-red   { box-shadow: var(--glow-red);   border-color: var(--neon-red)   !important; }
.glow-blue  { box-shadow: var(--glow-blue);  border-color: var(--neon-blue)  !important; }

/* Neon button style */
.btn-neon {
  border: 1px solid var(--neon-green);
  color: var(--neon-green);
  background: transparent;
  transition: all 0.2s;
}
.btn-neon:hover {
  background: var(--neon-green);
  color: #0a0f1e;
  box-shadow: var(--glow-green);
}

/* Scanline overlay on cards */
.scanline::before {
  content: '';
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0, 255, 65, 0.01) 2px,
    rgba(0, 255, 65, 0.01) 4px
  );
  pointer-events: none;
  border-radius: inherit;
}
```

- [ ] **Step 2: Update Card.tsx with cyberpunk style**

Replace the entire content of `frontend/src/components/Common/Card.tsx`:

```tsx
import { cn } from '../../utils/cn'
import type { ReactNode } from 'react'

interface CardProps {
  title?: string
  children: ReactNode
  className?: string
  action?: ReactNode
  glow?: 'green' | 'red' | 'blue' | false
}

export default function Card({ title, children, className, action, glow = false }: CardProps) {
  return (
    <div className={cn(
      'relative bg-[var(--color-bg-secondary)] rounded-xl border border-[var(--color-border)] overflow-hidden transition-all duration-300',
      'hover:border-[var(--neon-green)]/30',
      glow === 'green' && 'glow-green',
      glow === 'red' && 'glow-red',
      glow === 'blue' && 'glow-blue',
      className,
    )}>
      {title && (
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--color-border)]">
          <h3 className="text-sm font-semibold text-white tracking-wide uppercase">{title}</h3>
          {action}
        </div>
      )}
      <div className="p-6">{children}</div>
    </div>
  )
}
```

- [ ] **Step 3: Update Badge.tsx with neon severity glow**

Replace `frontend/src/components/Common/Badge.tsx`:

```tsx
import { cn, severityColor, statusColor } from '../../utils/cn'

interface BadgeProps {
  text: string
  variant?: 'severity' | 'status' | 'default'
  className?: string
}

export default function Badge({ text, variant = 'default', className }: BadgeProps) {
  const colorClass =
    variant === 'severity'
      ? severityColor(text)
      : variant === 'status'
        ? statusColor(text)
        : 'text-gray-300 bg-gray-500/10 border border-gray-500/20'

  return (
    <span className={cn(
      'inline-flex items-center px-2.5 py-0.5 rounded-sm text-xs font-mono font-medium capitalize border',
      colorClass,
      className,
    )}>
      {text}
    </span>
  )
}
```

- [ ] **Step 4: Update cn.ts with cyberpunk severity colors**

Replace `frontend/src/utils/cn.ts`:

```ts
import { clsx, type ClassValue } from 'clsx'

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs)
}

export function severityColor(severity: string): string {
  const colors: Record<string, string> = {
    critical: 'text-[#ff0040] bg-[#ff0040]/10 border-[#ff0040]/30',
    high:     'text-[#ff6b00] bg-[#ff6b00]/10 border-[#ff6b00]/30',
    medium:   'text-[#ffd000] bg-[#ffd000]/10 border-[#ffd000]/30',
    low:      'text-[#00d4ff] bg-[#00d4ff]/10 border-[#00d4ff]/30',
    info:     'text-gray-400  bg-gray-400/10  border-gray-400/20',
  }
  return colors[severity] || colors.info
}

export function statusColor(status: string): string {
  const colors: Record<string, string> = {
    running:   'text-[#00d4ff] bg-[#00d4ff]/10 border-[#00d4ff]/30',
    completed: 'text-[#00ff41] bg-[#00ff41]/10 border-[#00ff41]/30',
    failed:    'text-[#ff0040] bg-[#ff0040]/10 border-[#ff0040]/30',
    pending:   'text-[#ffd000] bg-[#ffd000]/10 border-[#ffd000]/30',
    cancelled: 'text-gray-400  bg-gray-400/10  border-gray-400/20',
  }
  return colors[status] || colors.pending
}

export function formatDate(date: string | null): string {
  if (!date) return '-'
  return new Date(date).toLocaleString()
}
```

- [ ] **Step 5: Update Sidebar.tsx with cyberpunk style**

Replace `frontend/src/components/Common/Sidebar.tsx`:

```tsx
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Scan, Bug, FileText, FolderOpen, Crosshair,
  Shield, Bell, Settings, Wrench, Globe, LogOut, Mail, Bot,
} from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import { cn } from '../../utils/cn'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/projects', icon: FolderOpen, label: 'Projects' },
  { to: '/targets', icon: Crosshair, label: 'Targets' },
  { to: '/scans', icon: Scan, label: 'Scans' },
  { to: '/phishing', icon: Mail, label: 'Phishing' },
  { to: '/findings', icon: Bug, label: 'Findings' },
  { to: '/reports', icon: FileText, label: 'Reports' },
  { to: '/tools', icon: Wrench, label: 'Tools' },
  { to: '/compliance', icon: Shield, label: 'Compliance' },
  { to: '/threat-intel', icon: Globe, label: 'Threat Intel' },
  { to: '/notifications', icon: Bell, label: 'Notifications' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Sidebar() {
  const { user, logout } = useAuthStore()

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-[var(--color-bg-secondary)] flex flex-col z-40"
      style={{ borderRight: '1px solid var(--neon-green)', boxShadow: '2px 0 16px #00ff4111' }}>
      {/* Logo */}
      <div className="px-6 py-5 border-b border-[var(--color-border)]">
        <h1 className="text-xl font-bold text-white flex items-center gap-2 font-mono">
          <Shield className="w-6 h-6" style={{ color: 'var(--neon-red)', filter: 'drop-shadow(0 0 6px var(--neon-red))' }} />
          <span style={{ color: 'var(--neon-green)', textShadow: 'var(--glow-green)' }}>RED</span>
          <span className="text-white">TEAM</span>
        </h1>
        <p className="text-xs mt-1 font-mono" style={{ color: 'var(--neon-green)', opacity: 0.6 }}>// Security Operations</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-4 px-3">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm mb-1 transition-all duration-200 font-mono',
                isActive
                  ? 'text-[var(--neon-green)] font-medium'
                  : 'text-[var(--color-text-secondary)] hover:text-white hover:bg-[var(--color-bg-tertiary)]',
              )
            }
            style={({ isActive }) => isActive ? {
              background: 'rgba(0,255,65,0.07)',
              borderLeft: '2px solid var(--neon-green)',
              boxShadow: 'inset 0 0 12px rgba(0,255,65,0.05)',
            } : { borderLeft: '2px solid transparent' }}
          >
            <Icon className="w-4 h-4 flex-shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User */}
      <div className="border-t border-[var(--color-border)] p-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-sm flex items-center justify-center text-sm font-bold font-mono"
            style={{ background: 'rgba(0,255,65,0.1)', border: '1px solid var(--neon-green)', color: 'var(--neon-green)' }}>
            {(user?.full_name?.[0] || user?.username?.[0] || '?').toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate font-mono">{user?.full_name || user?.username}</p>
            <p className="text-xs capitalize font-mono" style={{ color: 'var(--neon-green)', opacity: 0.7 }}>{user?.role}</p>
          </div>
          <button onClick={logout} className="text-[var(--color-text-secondary)] hover:text-[var(--neon-red)] transition-colors">
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  )
}
```

- [ ] **Step 6: Update Navbar.tsx with neon border**

Replace `frontend/src/components/Common/Navbar.tsx`:

```tsx
import { Bell, Search, Terminal } from 'lucide-react'
import { useState } from 'react'
import { useNotificationStore } from '../../store/notificationStore'

interface NavbarProps {
  title: string
}

export default function Navbar({ title }: NavbarProps) {
  const { unreadCount } = useNotificationStore()
  const [search, setSearch] = useState('')

  return (
    <header className="h-16 bg-[var(--color-bg-secondary)]/90 backdrop-blur-sm flex items-center justify-between px-6 sticky top-0 z-30"
      style={{ borderBottom: '1px solid var(--neon-green)', boxShadow: '0 1px 16px #00ff4111' }}>
      <div className="flex items-center gap-3">
        <Terminal className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--neon-green)' }} />
        <h2 className="text-lg font-semibold text-white font-mono tracking-wide">{title}</h2>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'var(--neon-green)', opacity: 0.6 }} />
          <input
            type="text"
            placeholder="Search..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 pr-4 py-2 bg-[var(--color-bg-tertiary)] rounded-sm text-sm text-white placeholder-[var(--color-text-secondary)] focus:outline-none w-56 font-mono"
            style={{ border: '1px solid var(--color-border)', transition: 'border-color 0.2s' }}
            onFocus={(e) => e.target.style.borderColor = 'var(--neon-green)'}
            onBlur={(e) => e.target.style.borderColor = 'var(--color-border)'}
          />
        </div>

        <button className="relative p-2 text-[var(--color-text-secondary)] hover:text-[var(--neon-green)] transition-colors">
          <Bell className="w-5 h-5" />
          {unreadCount > 0 && (
            <span className="absolute top-1 right-1 w-4 h-4 text-[#0a0f1e] text-[10px] font-bold flex items-center justify-center rounded-full"
              style={{ background: 'var(--neon-red)', boxShadow: 'var(--glow-red)' }}>
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </button>
      </div>
    </header>
  )
}
```

- [ ] **Step 7: Verify frontend compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors (or only pre-existing ones).

- [ ] **Step 8: Commit**

```bash
git add frontend/src/index.css frontend/src/components/Common/ frontend/src/utils/cn.ts
git commit -m "feat(design): apply cyberpunk theme — neon green/red, grid bg, glow components"
```

---

## Task 8: Frontend AI service + Zustand store

**Files:**
- Create: `frontend/src/services/aiService.ts`
- Create: `frontend/src/store/aiStore.ts`

- [ ] **Step 1: Create AI service**

Create `frontend/src/services/aiService.ts`:

```ts
import api from './api'

export interface AIProviderMeta {
  provider: string
  label: string
  type: 'local' | 'cloud' | 'custom'
  default_url: string | null
}

export interface AIConfig {
  provider: string
  is_enabled: boolean
  has_api_key: boolean
  base_url: string | null
  model: string
  label: string | null
}

export interface AIConfigUpdate {
  is_enabled: boolean
  api_key?: string
  base_url?: string
  model: string
  label?: string
}

export interface AITestResult {
  provider: string
  available: boolean
  models: string[]
  error: string | null
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatResponse {
  reply: string
  provider: string
  model: string
}

export interface FindingAnalysis {
  severity: string
  explanation: string
  remediation: string
  provider: string
  model: string
}

export const aiService = {
  getProviders: () =>
    api.get<AIProviderMeta[]>('/ai/providers').then((r) => r.data),

  getConfigs: () =>
    api.get<AIConfig[]>('/ai/config').then((r) => r.data),

  updateConfig: (provider: string, data: AIConfigUpdate) =>
    api.put<AIConfig>(`/ai/config/${provider}`, data).then((r) => r.data),

  testProvider: (provider: string) =>
    api.post<AITestResult>(`/ai/test/${provider}`).then((r) => r.data),

  chat: (messages: ChatMessage[], provider?: string, model?: string) =>
    api.post<ChatResponse>('/ai/chat', { messages, provider, model }).then((r) => r.data),

  analyzeFinding: (findingId: number) =>
    api.post<FindingAnalysis>(`/ai/analyze/finding/${findingId}`).then((r) => r.data),
}
```

- [ ] **Step 2: Create AI Zustand store**

Create `frontend/src/store/aiStore.ts`:

```ts
import { create } from 'zustand'
import type { ChatMessage } from '../services/aiService'

interface AIState {
  isOpen: boolean
  messages: ChatMessage[]
  isLoading: boolean
  activeProvider: string | null
  pageContext: string
  toggleChat: () => void
  openChat: () => void
  closeChat: () => void
  addMessage: (msg: ChatMessage) => void
  setLoading: (v: boolean) => void
  setActiveProvider: (p: string | null) => void
  setPageContext: (ctx: string) => void
  clearMessages: () => void
}

export const useAIStore = create<AIState>((set) => ({
  isOpen: false,
  messages: [],
  isLoading: false,
  activeProvider: null,
  pageContext: '',

  toggleChat: () => set((s) => ({ isOpen: !s.isOpen })),
  openChat: () => set({ isOpen: true }),
  closeChat: () => set({ isOpen: false }),
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  setLoading: (v) => set({ isLoading: v }),
  setActiveProvider: (p) => set({ activeProvider: p }),
  setPageContext: (ctx) => set({ pageContext: ctx }),
  clearMessages: () => set({ messages: [] }),
}))
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/aiService.ts frontend/src/store/aiStore.ts
git commit -m "feat(ai): add AI service and Zustand store"
```

---

## Task 9: Settings AI tab

**Files:**
- Create: `frontend/src/components/AI/AIProviderCard.tsx`
- Modify: `frontend/src/pages/SettingsPage.tsx`

- [ ] **Step 1: Create AIProviderCard component**

Create `frontend/src/components/AI/AIProviderCard.tsx`:

```tsx
import { useState } from 'react'
import { Wifi, WifiOff, Loader2, ChevronDown, ChevronUp } from 'lucide-react'
import { aiService, type AIConfig, type AIConfigUpdate, type AIProviderMeta, type AITestResult } from '../../services/aiService'

interface AIProviderCardProps {
  meta: AIProviderMeta
  config?: AIConfig
  onSaved: (cfg: AIConfig) => void
}

export default function AIProviderCard({ meta, config, onSaved }: AIProviderCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [apiKey, setApiKey] = useState('')
  const [baseUrl, setBaseUrl] = useState(config?.base_url || meta.default_url || '')
  const [model, setModel] = useState(config?.model || '')
  const [enabled, setEnabled] = useState(config?.is_enabled ?? false)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<AITestResult | null>(null)
  const [availableModels, setAvailableModels] = useState<string[]>([])

  const isLocal = meta.type === 'local'

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const result = await aiService.testProvider(meta.provider)
      setTestResult(result)
      if (result.models.length > 0) setAvailableModels(result.models)
    } catch {
      setTestResult({ provider: meta.provider, available: false, models: [], error: 'Request failed' })
    } finally {
      setTesting(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const payload: AIConfigUpdate = { is_enabled: enabled, model, base_url: baseUrl || undefined }
      if (apiKey) payload.api_key = apiKey
      const saved = await aiService.updateConfig(meta.provider, payload)
      onSaved(saved)
      setApiKey('')
    } finally {
      setSaving(false)
    }
  }

  const statusColor = testResult === null ? 'var(--color-text-secondary)'
    : testResult.available ? 'var(--neon-green)' : 'var(--neon-red)'

  return (
    <div className="rounded-lg overflow-hidden transition-all duration-200"
      style={{ border: `1px solid ${enabled ? 'var(--neon-green)' : 'var(--color-border)'}`, background: 'var(--color-bg-tertiary)' }}>

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <div className="flex items-center gap-3">
          {/* Status dot */}
          {testResult !== null ? (
            testResult.available
              ? <Wifi className="w-4 h-4 neon-pulse" style={{ color: 'var(--neon-green)' }} />
              : <WifiOff className="w-4 h-4" style={{ color: 'var(--neon-red)' }} />
          ) : (
            <div className="w-2 h-2 rounded-full" style={{ background: enabled ? 'var(--neon-green)' : 'var(--color-text-secondary)' }} />
          )}
          <span className="text-white font-mono text-sm font-medium">{meta.label}</span>
          <span className="text-xs font-mono px-2 py-0.5 rounded-sm"
            style={{ background: 'rgba(0,255,65,0.08)', color: 'var(--neon-green)', border: '1px solid rgba(0,255,65,0.2)' }}>
            {meta.type}
          </span>
          {config?.has_api_key && (
            <span className="text-xs font-mono px-2 py-0.5 rounded-sm"
              style={{ background: 'rgba(0,212,255,0.08)', color: 'var(--neon-blue)', border: '1px solid rgba(0,212,255,0.2)' }}>
              key saved
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 cursor-pointer" onClick={(e) => e.stopPropagation()}>
            <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} className="w-4 h-4" />
            <span className="text-xs font-mono" style={{ color: enabled ? 'var(--neon-green)' : 'var(--color-text-secondary)' }}>
              {enabled ? 'enabled' : 'disabled'}
            </span>
          </label>
          {expanded ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
        </div>
      </div>

      {/* Expanded form */}
      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-[var(--color-border)]">
          <div className="pt-3" />

          {/* Base URL (local providers) */}
          {(isLocal || meta.type === 'custom') && (
            <div>
              <label className="block text-xs font-mono text-[var(--color-text-secondary)] mb-1">Base URL</label>
              <input
                type="text" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)}
                placeholder={meta.default_url || 'http://localhost:11434'}
                className="w-full px-3 py-2 rounded-sm text-sm font-mono text-white focus:outline-none"
                style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }}
                onFocus={(e) => e.target.style.borderColor = 'var(--neon-green)'}
                onBlur={(e) => e.target.style.borderColor = 'var(--color-border)'}
              />
            </div>
          )}

          {/* API Key (cloud providers) */}
          {!isLocal && (
            <div>
              <label className="block text-xs font-mono text-[var(--color-text-secondary)] mb-1">
                API Key {config?.has_api_key && <span style={{ color: 'var(--neon-green)' }}>(saved — enter new to replace)</span>}
              </label>
              <input
                type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)}
                placeholder={config?.has_api_key ? '••••••••••••••••' : 'sk-...'}
                className="w-full px-3 py-2 rounded-sm text-sm font-mono text-white focus:outline-none"
                style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }}
                onFocus={(e) => e.target.style.borderColor = 'var(--neon-green)'}
                onBlur={(e) => e.target.style.borderColor = 'var(--color-border)'}
              />
            </div>
          )}

          {/* Model */}
          <div>
            <label className="block text-xs font-mono text-[var(--color-text-secondary)] mb-1">Model</label>
            {availableModels.length > 0 ? (
              <select value={model} onChange={(e) => setModel(e.target.value)}
                className="w-full px-3 py-2 rounded-sm text-sm font-mono text-white focus:outline-none"
                style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }}>
                <option value="">-- select model --</option>
                {availableModels.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            ) : (
              <input
                type="text" value={model} onChange={(e) => setModel(e.target.value)}
                placeholder="e.g. llama3.2, gpt-4o, claude-sonnet-4-6"
                className="w-full px-3 py-2 rounded-sm text-sm font-mono text-white focus:outline-none"
                style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }}
                onFocus={(e) => e.target.style.borderColor = 'var(--neon-green)'}
                onBlur={(e) => e.target.style.borderColor = 'var(--color-border)'}
              />
            )}
          </div>

          {/* Test result */}
          {testResult && (
            <div className="text-xs font-mono p-2 rounded-sm" style={{
              background: testResult.available ? 'rgba(0,255,65,0.05)' : 'rgba(255,0,64,0.05)',
              border: `1px solid ${testResult.available ? 'var(--neon-green)' : 'var(--neon-red)'}`,
              color: statusColor,
            }}>
              {testResult.available ? `✓ Connected — ${testResult.models.length} model(s) available` : `✗ ${testResult.error}`}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2 pt-1">
            <button onClick={handleTest} disabled={testing}
              className="px-3 py-1.5 rounded-sm text-xs font-mono transition-all flex items-center gap-1.5"
              style={{ border: '1px solid var(--neon-blue)', color: 'var(--neon-blue)', background: 'transparent' }}>
              {testing ? <Loader2 className="w-3 h-3 animate-spin" /> : null}
              {testing ? 'testing...' : 'test connection'}
            </button>
            <button onClick={handleSave} disabled={saving}
              className="px-3 py-1.5 rounded-sm text-xs font-mono btn-neon flex items-center gap-1.5">
              {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : null}
              {saving ? 'saving...' : 'save'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Update SettingsPage with AI tab**

Open `frontend/src/pages/SettingsPage.tsx` and replace the entire file:

```tsx
import { useState, useEffect } from 'react'
import { useAuthStore } from '../store/authStore'
import { authService } from '../services/authService'
import { aiService, type AIConfig, type AIProviderMeta } from '../services/aiService'
import Card from '../components/Common/Card'
import AIProviderCard from '../components/AI/AIProviderCard'

export default function SettingsPage() {
  const { user, setUser } = useAuthStore()
  const [activeTab, setActiveTab] = useState('profile')
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [profileMsg, setProfileMsg] = useState<{ text: string; ok: boolean } | null>(null)
  const [currentPwd, setCurrentPwd] = useState('')
  const [newPwd, setNewPwd] = useState('')
  const [pwdMsg, setPwdMsg] = useState<{ text: string; ok: boolean } | null>(null)
  const [saving, setSaving] = useState(false)
  const [providers, setProviders] = useState<AIProviderMeta[]>([])
  const [configs, setConfigs] = useState<AIConfig[]>([])

  const tabs = [
    { id: 'profile', label: 'Profile' },
    { id: 'security', label: 'Security' },
    { id: 'notifications', label: 'Notifications' },
    { id: 'ai', label: 'AI' },
    { id: 'api', label: 'API Keys' },
  ]

  useEffect(() => {
    if (activeTab === 'ai') {
      aiService.getProviders().then(setProviders).catch(() => {})
      aiService.getConfigs().then(setConfigs).catch(() => {})
    }
  }, [activeTab])

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setProfileMsg(null)
    try {
      const updated = await authService.updateProfile({ full_name: fullName })
      setUser(updated)
      setProfileMsg({ text: 'Profile updated.', ok: true })
    } catch {
      setProfileMsg({ text: 'Failed to update profile.', ok: false })
    } finally {
      setSaving(false)
    }
  }

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!currentPwd || !newPwd) return
    setSaving(true)
    setPwdMsg(null)
    try {
      await authService.changePassword(currentPwd, newPwd)
      setCurrentPwd('')
      setNewPwd('')
      setPwdMsg({ text: 'Password updated.', ok: true })
    } catch (err: any) {
      setPwdMsg({ text: err?.response?.data?.detail || 'Failed to change password.', ok: false })
    } finally {
      setSaving(false)
    }
  }

  const inputClass = "w-full px-4 py-2 rounded-sm text-white focus:outline-none font-mono text-sm"
  const inputStyle = { background: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)' }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-white font-mono tracking-wide">
        <span style={{ color: 'var(--neon-green)' }}>{'>'}</span> Settings
      </h2>

      <div className="flex gap-1 rounded-sm p-1 w-fit"
        style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }}>
        {tabs.map((t) => (
          <button key={t.id} onClick={() => setActiveTab(t.id)}
            className="px-4 py-2 rounded-sm text-sm font-mono transition-all"
            style={activeTab === t.id
              ? { background: 'rgba(0,255,65,0.1)', color: 'var(--neon-green)', border: '1px solid var(--neon-green)' }
              : { color: 'var(--color-text-secondary)', border: '1px solid transparent' }}>
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === 'profile' && (
        <Card title="Profile Information">
          <form onSubmit={handleSaveProfile} className="space-y-4 max-w-lg">
            <div>
              <label className="block text-xs font-mono text-[var(--color-text-secondary)] mb-1">Full Name</label>
              <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)}
                className={inputClass} style={inputStyle}
                onFocus={(e) => e.target.style.borderColor = 'var(--neon-green)'}
                onBlur={(e) => e.target.style.borderColor = 'var(--color-border)'} />
            </div>
            <div>
              <label className="block text-xs font-mono text-[var(--color-text-secondary)] mb-1">Email</label>
              <input type="email" defaultValue={user?.email || ''} disabled
                className={inputClass + ' cursor-not-allowed opacity-50'} style={inputStyle} />
            </div>
            <div>
              <label className="block text-xs font-mono text-[var(--color-text-secondary)] mb-1">Role</label>
              <input type="text" defaultValue={user?.role || ''} disabled
                className={inputClass + ' cursor-not-allowed opacity-50'} style={inputStyle} />
            </div>
            {profileMsg && (
              <p className="text-xs font-mono" style={{ color: profileMsg.ok ? 'var(--neon-green)' : 'var(--neon-red)' }}>
                {profileMsg.ok ? '✓' : '✗'} {profileMsg.text}
              </p>
            )}
            <button type="submit" disabled={saving} className="px-4 py-2 rounded-sm text-sm font-mono btn-neon disabled:opacity-50">
              {saving ? 'saving...' : 'save changes'}
            </button>
          </form>
        </Card>
      )}

      {activeTab === 'security' && (
        <Card title="Change Password">
          <form onSubmit={handleChangePassword} className="space-y-4 max-w-lg">
            <div>
              <label className="block text-xs font-mono text-[var(--color-text-secondary)] mb-1">Current Password</label>
              <input type="password" value={currentPwd} onChange={(e) => setCurrentPwd(e.target.value)} required
                className={inputClass} style={inputStyle}
                onFocus={(e) => e.target.style.borderColor = 'var(--neon-green)'}
                onBlur={(e) => e.target.style.borderColor = 'var(--color-border)'} />
            </div>
            <div>
              <label className="block text-xs font-mono text-[var(--color-text-secondary)] mb-1">New Password</label>
              <input type="password" value={newPwd} onChange={(e) => setNewPwd(e.target.value)} required minLength={8}
                className={inputClass} style={inputStyle}
                onFocus={(e) => e.target.style.borderColor = 'var(--neon-green)'}
                onBlur={(e) => e.target.style.borderColor = 'var(--color-border)'} />
            </div>
            {pwdMsg && (
              <p className="text-xs font-mono" style={{ color: pwdMsg.ok ? 'var(--neon-green)' : 'var(--neon-red)' }}>
                {pwdMsg.ok ? '✓' : '✗'} {pwdMsg.text}
              </p>
            )}
            <button type="submit" disabled={saving} className="px-4 py-2 rounded-sm text-sm font-mono btn-neon disabled:opacity-50">
              {saving ? 'updating...' : 'update password'}
            </button>
          </form>
        </Card>
      )}

      {activeTab === 'notifications' && (
        <Card title="Notification Preferences">
          <div className="space-y-3 max-w-lg">
            {['Email alerts', 'Slack notifications', 'Webhook alerts', 'Critical findings only'].map((label) => (
              <label key={label} className="flex items-center justify-between py-2 border-b border-[var(--color-border)]">
                <span className="text-sm font-mono text-white">{label}</span>
                <input type="checkbox" defaultChecked className="w-4 h-4 accent-[var(--neon-green)]" />
              </label>
            ))}
          </div>
        </Card>
      )}

      {activeTab === 'ai' && (
        <div className="space-y-4">
          <div>
            <h3 className="text-sm font-mono font-semibold mb-3" style={{ color: 'var(--neon-green)' }}>
              // Local AI Providers
            </h3>
            <div className="space-y-2">
              {providers.filter((p) => p.type === 'local').map((meta) => (
                <AIProviderCard
                  key={meta.provider}
                  meta={meta}
                  config={configs.find((c) => c.provider === meta.provider)}
                  onSaved={(cfg) => setConfigs((prev) => {
                    const idx = prev.findIndex((c) => c.provider === cfg.provider)
                    if (idx >= 0) { const next = [...prev]; next[idx] = cfg; return next }
                    return [...prev, cfg]
                  })}
                />
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-mono font-semibold mb-3" style={{ color: 'var(--neon-blue)' }}>
              // Cloud AI Providers
            </h3>
            <div className="space-y-2">
              {providers.filter((p) => p.type === 'cloud').map((meta) => (
                <AIProviderCard
                  key={meta.provider}
                  meta={meta}
                  config={configs.find((c) => c.provider === meta.provider)}
                  onSaved={(cfg) => setConfigs((prev) => {
                    const idx = prev.findIndex((c) => c.provider === cfg.provider)
                    if (idx >= 0) { const next = [...prev]; next[idx] = cfg; return next }
                    return [...prev, cfg]
                  })}
                />
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-mono font-semibold mb-3" style={{ color: 'var(--neon-purple)' }}>
              // Custom Provider
            </h3>
            <div className="space-y-2">
              {providers.filter((p) => p.type === 'custom').map((meta) => (
                <AIProviderCard
                  key={meta.provider}
                  meta={meta}
                  config={configs.find((c) => c.provider === meta.provider)}
                  onSaved={(cfg) => setConfigs((prev) => {
                    const idx = prev.findIndex((c) => c.provider === cfg.provider)
                    if (idx >= 0) { const next = [...prev]; next[idx] = cfg; return next }
                    return [...prev, cfg]
                  })}
                />
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'api' && (
        <Card title="API Keys">
          <p className="text-sm font-mono text-[var(--color-text-secondary)] mb-4">
            Manage API keys for programmatic access.
          </p>
          <button className="px-4 py-2 rounded-sm text-sm font-mono btn-neon">generate new key</button>
        </Card>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/AI/AIProviderCard.tsx frontend/src/pages/SettingsPage.tsx
git commit -m "feat(ai): add AI settings tab with provider cards and test/save UI"
```

---

## Task 10: Floating AI chat panel

**Files:**
- Create: `frontend/src/components/AI/AIChatButton.tsx`
- Create: `frontend/src/components/AI/AIChat.tsx`
- Modify: `frontend/src/layouts/MainLayout.tsx`

- [ ] **Step 1: Create AIChatButton**

Create `frontend/src/components/AI/AIChatButton.tsx`:

```tsx
import { Bot } from 'lucide-react'
import { useAIStore } from '../../store/aiStore'

export default function AIChatButton() {
  const { toggleChat, isOpen } = useAIStore()

  return (
    <button
      onClick={toggleChat}
      className="fixed bottom-6 right-6 w-12 h-12 rounded-sm flex items-center justify-center transition-all duration-200 z-50"
      style={{
        background: isOpen ? 'var(--neon-green)' : 'var(--color-bg-secondary)',
        border: '1px solid var(--neon-green)',
        boxShadow: isOpen ? 'var(--glow-green)' : '0 0 12px rgba(0,255,65,0.3)',
        color: isOpen ? '#0a0f1e' : 'var(--neon-green)',
      }}
      title="AI Assistant"
    >
      <Bot className="w-5 h-5" />
    </button>
  )
}
```

- [ ] **Step 2: Create AIChat panel**

Create `frontend/src/components/AI/AIChat.tsx`:

```tsx
import { useState, useRef, useEffect } from 'react'
import { X, Send, Trash2, Loader2 } from 'lucide-react'
import { useAIStore } from '../../store/aiStore'
import { aiService } from '../../services/aiService'

export default function AIChat() {
  const { isOpen, messages, isLoading, addMessage, setLoading, clearMessages, closeChat, pageContext } = useAIStore()
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async () => {
    const text = input.trim()
    if (!text || isLoading) return
    setInput('')

    const userMsg = { role: 'user' as const, content: text }
    addMessage(userMsg)
    setLoading(true)

    try {
      const allMessages = [...messages, userMsg]
      const contextMsg = pageContext
        ? [{ role: 'system' as const, content: `Context: user is on the ${pageContext} page of a Red Team SaaS security platform.` }, ...allMessages]
        : allMessages
      const resp = await aiService.chat(contextMsg)
      addMessage({ role: 'assistant', content: resp.reply })
    } catch (err: any) {
      addMessage({ role: 'assistant', content: `✗ Error: ${err?.response?.data?.detail || 'No AI provider configured or request failed.'}` })
    } finally {
      setLoading(false)
    }
  }

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  if (!isOpen) return null

  return (
    <div className="fixed bottom-22 right-6 w-96 rounded-sm flex flex-col z-50 overflow-hidden"
      style={{ height: '500px', background: 'var(--color-bg-secondary)', border: '1px solid var(--neon-green)', boxShadow: 'var(--glow-green)' }}>

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full neon-pulse" style={{ background: 'var(--neon-green)' }} />
          <span className="text-sm font-mono font-semibold" style={{ color: 'var(--neon-green)' }}>AI Assistant</span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={clearMessages} className="text-[var(--color-text-secondary)] hover:text-[var(--neon-red)] transition-colors">
            <Trash2 className="w-3.5 h-3.5" />
          </button>
          <button onClick={closeChat} className="text-[var(--color-text-secondary)] hover:text-[var(--neon-red)] transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-center text-xs font-mono text-[var(--color-text-secondary)] mt-8">
            <p style={{ color: 'var(--neon-green)' }}>// AI Assistant ready</p>
            <p className="mt-1">Ask about security findings, request analysis,<br />or get remediation advice.</p>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className="max-w-[80%] px-3 py-2 rounded-sm text-xs font-mono whitespace-pre-wrap"
              style={m.role === 'user'
                ? { background: 'rgba(0,255,65,0.1)', border: '1px solid rgba(0,255,65,0.3)', color: 'var(--neon-green)' }
                : { background: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)', color: 'var(--color-text)' }}>
              {m.content}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="px-3 py-2 rounded-sm text-xs font-mono flex items-center gap-2"
              style={{ background: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)', color: 'var(--color-text-secondary)' }}>
              <Loader2 className="w-3 h-3 animate-spin" style={{ color: 'var(--neon-green)' }} />
              processing...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-[var(--color-border)]">
        <div className="flex gap-2">
          <textarea
            value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKey}
            placeholder="// type your message..."
            rows={2}
            className="flex-1 px-3 py-2 rounded-sm text-xs font-mono text-white resize-none focus:outline-none"
            style={{ background: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)' }}
            onFocus={(e) => e.target.style.borderColor = 'var(--neon-green)'}
            onBlur={(e) => e.target.style.borderColor = 'var(--color-border)'}
          />
          <button onClick={send} disabled={isLoading || !input.trim()}
            className="px-3 rounded-sm transition-all flex items-center disabled:opacity-40"
            style={{ background: 'rgba(0,255,65,0.1)', border: '1px solid var(--neon-green)', color: 'var(--neon-green)' }}>
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Wire into MainLayout**

Replace `frontend/src/layouts/MainLayout.tsx`:

```tsx
import { Outlet, useLocation } from 'react-router-dom'
import Sidebar from '../components/Common/Sidebar'
import Navbar from '../components/Common/Navbar'
import { useWebSocket } from '../hooks/useWebSocket'
import AIChatButton from '../components/AI/AIChatButton'
import AIChat from '../components/AI/AIChat'
import { useAIStore } from '../store/aiStore'
import { useEffect } from 'react'

const pageTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/projects': 'Projects',
  '/targets': 'Targets',
  '/scans': 'Scans',
  '/findings': 'Findings',
  '/reports': 'Reports',
  '/tools': 'Tools',
  '/compliance': 'Compliance',
  '/threat-intel': 'Threat Intelligence',
  '/notifications': 'Notifications',
  '/settings': 'Settings',
  '/phishing': 'Phishing',
}

export default function MainLayout() {
  const location = useLocation()
  const title = pageTitles[location.pathname] || 'Red Team SaaS'
  const { setPageContext } = useAIStore()

  useWebSocket()

  useEffect(() => {
    setPageContext(title)
  }, [title, setPageContext])

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 ml-64">
        <Navbar title={title} />
        <main className="p-6">
          <Outlet />
        </main>
      </div>
      <AIChatButton />
      <AIChat />
    </div>
  )
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/AI/AIChatButton.tsx frontend/src/components/AI/AIChat.tsx frontend/src/layouts/MainLayout.tsx
git commit -m "feat(ai): add floating AI chat panel with page context"
```

---

## Task 11: Findings AI analysis modal

**Files:**
- Create: `frontend/src/components/AI/AIAnalysisModal.tsx`
- Modify: `frontend/src/pages/FindingsPage.tsx`

- [ ] **Step 1: Create AIAnalysisModal**

Create `frontend/src/components/AI/AIAnalysisModal.tsx`:

```tsx
import { useEffect, useState } from 'react'
import { X, Loader2, Bot } from 'lucide-react'
import { aiService, type FindingAnalysis } from '../../services/aiService'

interface AIAnalysisModalProps {
  findingId: number
  findingTitle: string
  onClose: () => void
}

export default function AIAnalysisModal({ findingId, findingTitle, onClose }: AIAnalysisModalProps) {
  const [analysis, setAnalysis] = useState<FindingAnalysis | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    aiService.analyzeFinding(findingId)
      .then(setAnalysis)
      .catch((err) => setError(err?.response?.data?.detail || 'Analysis failed. Is an AI provider enabled?'))
      .finally(() => setLoading(false))
  }, [findingId])

  const severityColor: Record<string, string> = {
    critical: 'var(--neon-red)',
    high: '#ff6b00',
    medium: '#ffd000',
    low: 'var(--neon-blue)',
    info: 'var(--color-text-secondary)',
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.8)' }} onClick={onClose}>
      <div className="w-full max-w-lg rounded-sm overflow-hidden"
        style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--neon-green)', boxShadow: 'var(--glow-green)' }}
        onClick={(e) => e.stopPropagation()}>

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--color-border)]">
          <div className="flex items-center gap-2">
            <Bot className="w-4 h-4" style={{ color: 'var(--neon-green)' }} />
            <span className="text-sm font-mono font-semibold" style={{ color: 'var(--neon-green)' }}>AI Analysis</span>
          </div>
          <button onClick={onClose} className="text-[var(--color-text-secondary)] hover:text-[var(--neon-red)] transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5">
          <p className="text-xs font-mono text-[var(--color-text-secondary)] mb-4 truncate">{findingTitle}</p>

          {loading && (
            <div className="flex items-center gap-3 text-sm font-mono" style={{ color: 'var(--neon-green)' }}>
              <Loader2 className="w-4 h-4 animate-spin" />
              Analyzing with AI...
            </div>
          )}

          {error && (
            <div className="text-xs font-mono p-3 rounded-sm"
              style={{ background: 'rgba(255,0,64,0.05)', border: '1px solid var(--neon-red)', color: 'var(--neon-red)' }}>
              ✗ {error}
            </div>
          )}

          {analysis && (
            <div className="space-y-4">
              {/* Severity */}
              <div className="flex items-center gap-3 p-3 rounded-sm"
                style={{ background: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)' }}>
                <span className="text-xs font-mono text-[var(--color-text-secondary)]">Severity:</span>
                <span className="text-sm font-mono font-bold capitalize"
                  style={{ color: severityColor[analysis.severity] || 'var(--color-text)' }}>
                  {analysis.severity}
                </span>
                <span className="ml-auto text-xs font-mono text-[var(--color-text-secondary)]">
                  via {analysis.provider} / {analysis.model}
                </span>
              </div>

              {/* Explanation */}
              <div>
                <p className="text-xs font-mono mb-2" style={{ color: 'var(--neon-blue)' }}>// Explanation</p>
                <p className="text-xs font-mono text-[var(--color-text)] leading-relaxed whitespace-pre-wrap p-3 rounded-sm"
                  style={{ background: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)' }}>
                  {analysis.explanation}
                </p>
              </div>

              {/* Remediation */}
              <div>
                <p className="text-xs font-mono mb-2" style={{ color: 'var(--neon-green)' }}>// Remediation</p>
                <p className="text-xs font-mono text-[var(--color-text)] leading-relaxed whitespace-pre-wrap p-3 rounded-sm"
                  style={{ background: 'var(--color-bg-tertiary)', border: '1px solid rgba(0,255,65,0.2)' }}>
                  {analysis.remediation}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Update FindingsPage to add Analyze button**

Replace the full content of `frontend/src/pages/FindingsPage.tsx`:

```tsx
import { useEffect, useState } from 'react'
import { RefreshCw, Filter, Bot } from 'lucide-react'
import { findingsService } from '../services/findingsService'
import type { Finding, Severity } from '../types'
import Card from '../components/Common/Card'
import Badge from '../components/Common/Badge'
import Loading from '../components/Common/Loading'
import EmptyState from '../components/Common/EmptyState'
import AIAnalysisModal from '../components/AI/AIAnalysisModal'
import { formatDate } from '../utils/cn'

const SEVERITIES: Severity[] = ['critical', 'high', 'medium', 'low', 'info']

export default function FindingsPage() {
  const [findings, setFindings] = useState<Finding[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('all')
  const [analyzingId, setAnalyzingId] = useState<number | null>(null)
  const [analyzingTitle, setAnalyzingTitle] = useState('')

  const load = () => {
    setLoading(true)
    findingsService.list().then(setFindings).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const filtered = filter === 'all' ? findings : findings.filter((f) => f.severity === filter)

  if (loading) return <Loading text="Loading findings..." />

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white font-mono">
            <span style={{ color: 'var(--neon-red)' }}>{'>'}</span> Findings
          </h2>
          <p className="text-sm font-mono text-[var(--color-text-secondary)]">{findings.length} total findings</p>
        </div>
        <div className="flex gap-2">
          <div className="flex items-center gap-1 rounded-sm p-1"
            style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }}>
            <button onClick={() => setFilter('all')}
              className="px-3 py-1.5 rounded-sm text-xs font-mono transition-all"
              style={filter === 'all'
                ? { background: 'rgba(0,255,65,0.1)', color: 'var(--neon-green)', border: '1px solid var(--neon-green)' }
                : { color: 'var(--color-text-secondary)', border: '1px solid transparent' }}>
              all
            </button>
            {SEVERITIES.map((s) => (
              <button key={s} onClick={() => setFilter(s)}
                className="px-3 py-1.5 rounded-sm text-xs font-mono capitalize transition-all"
                style={filter === s
                  ? { background: 'rgba(0,255,65,0.1)', color: 'var(--neon-green)', border: '1px solid var(--neon-green)' }
                  : { color: 'var(--color-text-secondary)', border: '1px solid transparent' }}>
                {s}
              </button>
            ))}
          </div>
          <button onClick={load} className="px-3 py-2 rounded-sm text-white flex items-center gap-2 transition-colors"
            style={{ background: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)' }}>
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-5 gap-3">
        {SEVERITIES.map((s) => {
          const count = findings.filter((f) => f.severity === s).length
          const colors: Record<string, string> = {
            critical: 'var(--neon-red)', high: '#ff6b00', medium: '#ffd000',
            low: 'var(--neon-blue)', info: 'var(--color-text-secondary)',
          }
          return (
            <div key={s} className="rounded-sm p-3 text-center cursor-pointer transition-all"
              onClick={() => setFilter(s)}
              style={{ background: 'var(--color-bg-secondary)', border: `1px solid ${filter === s ? colors[s] : 'var(--color-border)'}` }}>
              <p className="text-2xl font-bold font-mono" style={{ color: colors[s] }}>{count}</p>
              <p className="text-xs font-mono capitalize text-[var(--color-text-secondary)]">{s}</p>
            </div>
          )
        })}
      </div>

      {filtered.length === 0 ? (
        <EmptyState icon={<Filter className="w-12 h-12" />} title="No findings"
          description={filter !== 'all' ? `No ${filter} findings found.` : 'No findings detected yet.'} />
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[var(--color-text-secondary)] border-b border-[var(--color-border)]">
                  <th className="pb-3 font-mono text-xs">Title</th>
                  <th className="pb-3 font-mono text-xs">Severity</th>
                  <th className="pb-3 font-mono text-xs">Host</th>
                  <th className="pb-3 font-mono text-xs">Risk</th>
                  <th className="pb-3 font-mono text-xs">Status</th>
                  <th className="pb-3 font-mono text-xs">Date</th>
                  <th className="pb-3 font-mono text-xs">AI</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border)]">
                {filtered.map((f) => (
                  <tr key={f.id} className="hover:bg-[var(--color-bg-tertiary)]/30 transition-colors">
                    <td className="py-3">
                      <p className="text-white font-medium font-mono text-xs">{f.title}</p>
                      <p className="text-xs text-[var(--color-text-secondary)] line-clamp-1 mt-0.5 font-mono">{f.description}</p>
                    </td>
                    <td className="py-3"><Badge text={f.severity} variant="severity" /></td>
                    <td className="py-3 text-[var(--color-text-secondary)] font-mono text-xs">{f.host || '-'}</td>
                    <td className="py-3 text-white font-mono text-xs">{f.risk_score?.toFixed(1) ?? '-'}</td>
                    <td className="py-3"><Badge text={f.status} variant="status" /></td>
                    <td className="py-3 text-[var(--color-text-secondary)] font-mono text-xs">{formatDate(f.created_at)}</td>
                    <td className="py-3">
                      <button
                        onClick={() => { setAnalyzingId(f.id); setAnalyzingTitle(f.title) }}
                        className="flex items-center gap-1 px-2 py-1 rounded-sm text-xs font-mono transition-all"
                        style={{ border: '1px solid rgba(0,255,65,0.3)', color: 'var(--neon-green)', background: 'rgba(0,255,65,0.05)' }}
                        title="Analyze with AI">
                        <Bot className="w-3 h-3" />
                        analyze
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {analyzingId !== null && (
        <AIAnalysisModal
          findingId={analyzingId}
          findingTitle={analyzingTitle}
          onClose={() => setAnalyzingId(null)}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 3: TypeCheck**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: no new errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/AI/AIAnalysisModal.tsx frontend/src/pages/FindingsPage.tsx
git commit -m "feat(ai): add AI analysis button and modal to findings"
```

---

## Task 12: Final verification

- [ ] **Step 1: Verify all containers healthy**

```bash
docker compose ps
```

Expected: all services `healthy` or `running`.

- [ ] **Step 2: Verify AI endpoints accessible**

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@redteam.dev","password":"RedTeam@2024!"}' | python -m json.tool | grep access_token | cut -d'"' -f4)

curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/ai/providers | python -m json.tool | head -15
```

Expected: JSON list of providers.

- [ ] **Step 3: Verify frontend loads**

Open http://localhost:5173, login, go to Settings → AI tab — provider cards visible.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete AI integration + cyberpunk design overhaul"
```
