"""테스트/파이프라인 점검용 가짜 provider. 미리 정한 응답을 순환해서 돌려준다."""
from typing import List, Optional

from .base import LLMProvider


class MockProvider(LLMProvider):
    name = "mock"

    def __init__(self, responses: Optional[List[str]] = None):
        self.responses = responses or ['{"label": "none", "confidence": 0.5, "evidence": [], "reasoning": "mock"}']
        self._i = 0

    def complete(self, system: str, user: str) -> str:
        out = self.responses[self._i % len(self.responses)]
        self._i += 1
        return out
