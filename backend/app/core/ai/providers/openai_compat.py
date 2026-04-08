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
