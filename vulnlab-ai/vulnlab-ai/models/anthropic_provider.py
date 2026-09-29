"""Anthropic Messages API provider."""
import os

import requests

from .base import LLMProvider


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, model: str, api_key_env: str = "ANTHROPIC_API_KEY",
                 max_tokens: int = 1024, temperature: float = 0.0,
                 timeout_sec: float = 120, base_url: str = "https://api.anthropic.com"):
        self.api_key = os.environ.get(api_key_env)
        if not self.api_key:
            raise ValueError(f"환경변수 {api_key_env} 가 설정되어 있지 않습니다.")
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout_sec
        self.base_url = base_url.rstrip("/")

    def complete(self, system: str, user: str) -> str:
        r = requests.post(
            f"{self.base_url}/v1/messages",
            headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": self.model, "max_tokens": self.max_tokens,
                  "temperature": self.temperature, "system": system,
                  "messages": [{"role": "user", "content": user}]},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text")
