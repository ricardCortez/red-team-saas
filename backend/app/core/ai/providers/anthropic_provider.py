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
