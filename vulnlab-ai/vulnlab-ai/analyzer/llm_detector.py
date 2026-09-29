"""LLM 기반 탐지기. provider 는 주입받으므로 API/로컬 모델 교체가 자유롭다."""
import json
import re
from typing import Any, Dict

from models.base import LLMProvider
from .schema import LABEL_DESCRIPTIONS, LABELS, HttpExchange, Prediction

SYSTEM_PROMPT = (
    "You are a web security analyst helping with an educational research project. "
    "You analyze HTTP request/response pairs captured from a LOCAL practice lab and classify "
    "whether the exchange shows evidence of a vulnerability.\n\n"
    "Allowed labels:\n"
    + "\n".join(f"- {k}: {v}" for k, v in LABEL_DESCRIPTIONS.items())
    + "\n\nRules:\n"
    "- Judge ONLY from evidence visible in this exchange. If the endpoint might be vulnerable "
    "but this exchange shows no evidence, answer 'none'.\n"
    "- Pick exactly one label.\n"
    "- Respond with ONLY a JSON object: "
    '{"label": "<label>", "confidence": <0.0-1.0>, "evidence": ["<short quote/observation>"], '
    '"reasoning": "<one or two sentences>"}'
)


def build_user_prompt(ex: HttpExchange, max_body_chars: int = 3000) -> str:
    headers = "\n".join(f"{k}: {v}" for k, v in ex.response_headers.items())
    body = ex.response_body or ""
    truncated = " [...truncated]" if len(body) > max_body_chars else ""
    return (
        f"REQUEST: {ex.method} {ex.url}\n"
        f"SUBMITTED INPUTS: {json.dumps(ex.inputs, ensure_ascii=False)}\n\n"
        f"RESPONSE STATUS: {ex.status_code}\n"
        f"RESPONSE HEADERS:\n{headers}\n\n"
        f"RESPONSE BODY:\n{body[:max_body_chars]}{truncated}"
    )


def parse_llm_output(text: str) -> Dict[str, Any]:
    m = re.search(r"\{.*\}", text, re.DOTALL)  # ```json 펜스/앞뒤 잡담 제거
    if not m:
        raise ValueError("no JSON object in model output")
    data = json.loads(m.group(0))
    if data.get("label") not in LABELS:
        raise ValueError(f"invalid label: {data.get('label')!r}")
    return data


class LLMDetector:
    def __init__(self, provider: LLMProvider, max_body_chars: int = 3000):
        self.provider = provider
        self.max_body_chars = max_body_chars
        self.name = f"llm:{provider.name}"

    def predict(self, ex: HttpExchange) -> Prediction:
        raw = None
        try:
            raw = self.provider.complete(SYSTEM_PROMPT, build_user_prompt(ex, self.max_body_chars))
            d = parse_llm_output(raw)
            return Prediction(
                label=d["label"],
                confidence=float(d.get("confidence", 0.0)),
                evidence=[str(e) for e in d.get("evidence", [])],
                reasoning=str(d.get("reasoning", "")),
                raw_output=raw,
            )
        except Exception as e:  # 호출 실패/파싱 실패는 별도 집계(parse_failures)
            return Prediction("none", 0.0, [], "", error=f"{type(e).__name__}: {e}", raw_output=raw)
