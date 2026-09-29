from typing import Any, Dict, Optional

from models.registry import build_provider
from .llm_detector import LLMDetector
from .rules import RuleDetector


def build_detector(settings: Dict[str, Any], detector_type: Optional[str] = None,
                   provider_name: Optional[str] = None):
    dcfg = settings.get("detector", {})
    kind = detector_type or dcfg.get("type", "rules")
    if kind == "rules":
        return RuleDetector()
    if kind == "llm":
        name = provider_name or dcfg["provider"]
        provider = build_provider(settings["providers"][name])
        return LLMDetector(provider, dcfg.get("max_body_chars", 3000))
    raise ValueError(f"unknown detector type: {kind}")
