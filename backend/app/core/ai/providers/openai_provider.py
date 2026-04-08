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
