# AI Integration + Cyberpunk Design — Spec

**Date:** 2026-04-08  
**Status:** Approved  

---

## Overview

Add multi-provider AI support to Red Team SaaS (local + cloud), expose it in Settings, embed it as a floating chat panel and findings analyzer, and restyle the entire frontend with a cyberpunk/hacker aesthetic.

---

## 1. Backend — AI Module

### Structure

```
backend/app/core/ai/
  __init__.py
  providers/
    base.py          # Abstract AIProvider class: test(), chat(), analyze()
    ollama.py        # Ollama / LM Studio / any OpenAI-compatible endpoint
    openai.py
    anthropic.py
    gemini.py
    groq.py
    mistral.py
    custom.py        # Generic OpenAI-compatible with custom base_url

backend/app/models/ai_config.py      # UserAIConfig table (per-user, per-provider)
backend/app/schemas/ai.py            # Pydantic schemas
backend/app/services/ai_service.py   # Orchestrates providers, encrypts keys
backend/app/api/v1/endpoints/ai.py   # Router registered at /api/v1/ai/
```

### Database Model — `user_ai_configs`

| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| user_id | int FK | |
| provider | str | enum: ollama, openai, anthropic, gemini, groq, mistral, custom |
| is_enabled | bool | |
| api_key_encrypted | str nullable | encrypted with ENCRYPTION_KEY |
| base_url | str nullable | for local providers |
| model | str | default model to use |
| created_at / updated_at | datetime | |

### API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | /api/v1/ai/providers | List all supported providers with metadata |
| GET | /api/v1/ai/config | Get current user's AI configs |
| PUT | /api/v1/ai/config/{provider} | Save/update config for a provider |
| POST | /api/v1/ai/test/{provider} | Test provider availability (ping/model list) |
| POST | /api/v1/ai/chat | Send a message, returns streamed or full response |
| POST | /api/v1/ai/analyze/finding/{finding_id} | Analyze a finding with AI |

### Provider Abstraction

```python
class AIProvider(ABC):
    @abstractmethod
    async def test(self) -> bool: ...           # connectivity check
    @abstractmethod
    async def chat(self, messages: list) -> str: ...
    @abstractmethod
    async def analyze_finding(self, finding: dict) -> dict: ...  # {severity, explanation, remediation}
```

- Local providers (Ollama, LM Studio, custom): use `base_url`, no key required
- Cloud providers: require encrypted API key
- All providers list available models via `GET /api/v1/ai/test/{provider}` response

### Security
- API keys encrypted at rest using existing `EncryptionHandler`
- Keys never returned to frontend (masked as `***`)
- Local URLs validated to reject non-HTTP schemes

---

## 2. Frontend — Settings AI Tab

### New tab added to SettingsPage: "AI"

**Local AI section:**
- Cards for: Ollama, LM Studio, Custom OpenAI-compatible
- Fields: Base URL (default `http://localhost:11434`), Model selector (populated after successful test)
- Test button → live indicator: green pulse = online, red = offline, spinner = testing

**Cloud AI section:**
- Cards for: OpenAI, Anthropic, Google Gemini, Groq, Mistral, Custom
- Fields: API Key (masked input), Model selector
- Same test button + live indicator pattern

**New service:** `frontend/src/services/aiService.ts`

---

## 3. Frontend — Floating AI Chat

- Fixed button bottom-right: robot icon with neon green glow
- Slide-up panel (400px wide, 500px tall)
- Shows: provider selector (only enabled providers), message history, input box
- Sends current page context with each message (e.g., "user is on FindingsPage")
- State managed in new Zustand store: `src/store/aiStore.ts`

---

## 4. Frontend — Findings AI Analysis

- "Analyze" button on each finding card/row
- Opens modal with: severity assessment, plain-language explanation, remediation steps
- Calls `POST /api/v1/ai/analyze/finding/{id}`
- Shows which provider was used

---

## 5. Cyberpunk Design Overhaul

### Color palette additions to `index.css`
```css
--color-neon-green: #00ff41;
--color-neon-red: #ff0040;
--color-neon-blue: #00d4ff;
--color-glow-green: 0 0 8px #00ff41, 0 0 20px #00ff4133;
--color-glow-red: 0 0 8px #ff0040, 0 0 20px #ff004033;
```

### Changes
- **Sidebar:** active item glow green, right border neon line, logo accent red
- **Cards:** hover → subtle green border glow
- **Buttons primary:** outline neon style (border neon-green, text neon-green, bg transparent, hover fill)
- **Badges severity:** glow matching severity color (critical=red, high=orange, medium=yellow, low=blue)
- **Inputs focus:** neon green ring instead of indigo
- **Background:** subtle grid pattern overlay on `body`
- **Monospace font:** IPs, hashes, CVE IDs rendered in `font-mono`
- **Status indicators:** pulsing neon dots instead of solid circles
- **Navbar:** bottom border neon green 1px

### Scope
Global changes via `index.css` + updates to: `Sidebar.tsx`, `Card.tsx`, `Navbar.tsx`, `Badge.tsx`, `SettingsPage.tsx`, `FindingsPage.tsx`, `LoginForm.tsx`

---

## 6. New Files Summary

**Backend (new):**
- `app/core/ai/__init__.py`
- `app/core/ai/providers/base.py`
- `app/core/ai/providers/ollama.py`
- `app/core/ai/providers/openai.py`
- `app/core/ai/providers/anthropic.py`
- `app/core/ai/providers/gemini.py`
- `app/core/ai/providers/groq.py`
- `app/core/ai/providers/mistral.py`
- `app/core/ai/providers/custom.py`
- `app/models/ai_config.py`
- `app/schemas/ai.py`
- `app/services/ai_service.py`
- `app/api/v1/endpoints/ai.py`
- `alembic/versions/XXXX_add_user_ai_configs.py`

**Frontend (new):**
- `src/services/aiService.ts`
- `src/store/aiStore.ts`
- `src/components/AI/AIChat.tsx`
- `src/components/AI/AIChatButton.tsx`
- `src/components/AI/AIProviderCard.tsx`
- `src/components/AI/AIAnalysisModal.tsx`

**Frontend (modified):**
- `src/index.css` — cyberpunk variables + grid bg + glow utilities
- `src/pages/SettingsPage.tsx` — add AI tab
- `src/pages/FindingsPage.tsx` — add Analyze button
- `src/components/Common/Sidebar.tsx` — cyberpunk styles
- `src/components/Common/Card.tsx` — hover glow
- `src/components/Common/Navbar.tsx` — neon border
- `src/components/Common/Badge.tsx` — severity glow
- `src/layouts/MainLayout.tsx` — mount AIChat component

---

## Constraints

- No breaking changes to existing API routes
- AI features degrade gracefully when no provider is configured
- Local providers work without internet
- Alembic migration required for new table
