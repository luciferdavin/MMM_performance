"""LLM provider abstraction — Ollama default, pluggable Claude/OpenAI."""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

from mmm.config import get_settings

logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    @abstractmethod
    def chat(self, system: str, user: str, *, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        pass
    def chat_json(self, system: str, user: str, **kw) -> dict[str, Any]:
        raw = self.chat(system, user, **kw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw, "_parse_error": True}

class OllamaProvider(LLMProvider):
    def __init__(self) -> None:
        s = get_settings()
        self.base_url = s.ollama_base_url.rstrip("/")
        self.model = s.ollama_model
    def chat(self, system: str, user: str, *, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        with httpx.Client(timeout=120) as c:
            r = c.post(f"{self.base_url}/api/chat", json={
                "model": self.model, "stream": False, "format": "json",
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            }); r.raise_for_status()
            return r.json().get("message", {}).get("content", "")

class AnthropicProvider(LLMProvider):
    def __init__(self) -> None:
        s = get_settings()
        self.api_key = s.anthropic_api_key
        self.model = s.anthropic_model
    def chat(self, system: str, user: str, *, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        try:
            import anthropic
        except ImportError:
            raise ImportError("pip install anthropic")
        client = anthropic.Anthropic(api_key=self.api_key)
        msg = client.messages.create(model=self.model, max_tokens=max_tokens, temperature=temperature,
            system=system, messages=[{"role": "user", "content": user}])
        return msg.content[0].text

class OpenAIProvider(LLMProvider):
    def __init__(self) -> None:
        s = get_settings()
        self.api_key = s.openai_api_key
        self.model = s.openai_model
    def chat(self, system: str, user: str, *, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        try:
            import openai
        except ImportError:
            raise ImportError("pip install openai")
        client = openai.OpenAI(api_key=self.api_key)
        r = client.chat.completions.create(model=self.model, temperature=temperature, max_tokens=max_tokens,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
        return r.choices[0].message.content or ""

def get_llm_provider(name: str | None = None) -> LLMProvider:
    name = name or get_settings().llm_provider
    return {"ollama": OllamaProvider, "anthropic": AnthropicProvider, "openai": OpenAIProvider}[name]()
