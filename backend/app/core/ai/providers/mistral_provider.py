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
