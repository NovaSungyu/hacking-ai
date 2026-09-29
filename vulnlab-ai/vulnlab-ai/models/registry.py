"""settings.json 의 provider 설정 → provider 객체. 새 업체/로컬 모델은 여기에 한 줄 추가."""
from typing import Any, Dict

from .anthropic_provider import AnthropicProvider
from .base import LLMProvider
from .mock import MockProvider
from .openai_compat import OpenAICompatProvider


def build_provider(cfg: Dict[str, Any]) -> LLMProvider:
    cfg = dict(cfg)
    kind = cfg.pop("type")
    if kind == "openai_compat":
        return OpenAICompatProvider(**cfg)
    if kind == "anthropic":
        return AnthropicProvider(**cfg)
    if kind == "mock":
        return MockProvider()
    raise ValueError(f"알 수 없는 provider type: {kind}")
