"""Custom OpenAI-compatible provider with user-defined base_url"""
from app.core.ai.providers.openai_compat import OpenAICompatProvider


class CustomProvider(OpenAICompatProvider):
    def __init__(self, base_url: str, api_key: str = ""):
        super().__init__(base_url=base_url, api_key=api_key)
