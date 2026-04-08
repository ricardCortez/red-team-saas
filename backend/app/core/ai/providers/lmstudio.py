"""LM Studio local AI provider (OpenAI-compatible)"""
from app.core.ai.providers.openai_compat import OpenAICompatProvider


class LMStudioProvider(OpenAICompatProvider):
    """LM Studio exposes an OpenAI-compatible API."""

    def __init__(self, base_url: str = "http://localhost:1234/v1"):
        super().__init__(base_url=base_url, api_key="lm-studio")
