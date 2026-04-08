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
