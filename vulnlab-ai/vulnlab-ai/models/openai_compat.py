"""OpenAI 호환 /chat/completions 엔드포인트용 provider.

같은 코드로 다음을 모두 지원한다(base_url 만 바꾸면 됨):
  - OpenAI                    https://api.openai.com/v1
  - Ollama (로컬)              http://localhost:11434/v1
  - vLLM / LM Studio / llama.cpp server 등 로컬 서버
"""
import os
from typing import Optional

import requests

from .base import LLMProvider


class OpenAICompatProvider(LLMProvider):
    name = "openai_compat"

    def __init__(self, base_url: str, model: str, api_key_env: Optional[str] = None,
                 temperature: float = 0.0, timeout_sec: float = 120,
                 max_tokens: Optional[int] = None):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = os.environ.get(api_key_env) if api_key_env else None
        if api_key_env and not self.api_key:
            raise ValueError(f"환경변수 {api_key_env} 가 설정되어 있지 않습니다.")
        self.temperature = temperature
        self.timeout = timeout_sec
        self.max_tokens = max_tokens

    def complete(self, system: str, user: str) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
        }
        if self.max_tokens:
            payload["max_tokens"] = self.max_tokens
        r = requests.post(f"{self.base_url}/chat/completions", headers=headers,
                          json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
