from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """모든 LLM 백엔드가 구현해야 하는 최소 인터페이스.

    분석기(analyzer)는 이 인터페이스만 알고, 어떤 업체/로컬 모델인지 모른다.
    """
    name = "base"

    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """system/user 프롬프트를 받아 모델의 텍스트 응답을 반환."""
