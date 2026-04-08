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
