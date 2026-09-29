"""공통 데이터 구조. 모든 모듈이 이 스키마만 주고받는다."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

# 라벨은 "이 HTTP 교환(요청+응답) 안에 보이는 증거"를 기준으로 붙인다.
LABELS = ["none", "xss_reflected", "sql_error_leak", "info_disclosure", "insecure_headers"]

LABEL_DESCRIPTIONS = {
    "none": "No vulnerability evidence is visible in this exchange.",
    "xss_reflected": "A submitted input value is reflected in an HTML response without output encoding.",
    "sql_error_leak": "The response exposes a database/SQL error message (indicates unsafe query handling).",
    "info_disclosure": "The response exposes stack traces, debug output, or internal file paths.",
    "insecure_headers": "HTML response lacks key security headers, or cookies lack HttpOnly.",
}


@dataclass
class HttpExchange:
    method: str
    url: str
    status_code: int
    response_headers: Dict[str, Any]
    response_body: str
    inputs: Dict[str, str] = field(default_factory=dict)
    request_headers: Dict[str, str] = field(default_factory=dict)
    request_body: Optional[str] = None
    elapsed_ms: float = 0.0

    def header(self, name: str) -> Optional[str]:
        for k, v in self.response_headers.items():
            if k.lower() == name.lower():
                return v if isinstance(v, str) else ", ".join(v)
        return None

    def content_type(self) -> str:
        return (self.header("content-type") or "").lower()

    def set_cookies(self) -> List[str]:
        for k, v in self.response_headers.items():
            if k.lower() == "set-cookie":
                return list(v) if isinstance(v, list) else [v]
        return []


@dataclass
class Sample:
    id: str
    scenario: str
    label: str
    label_source: str  # lab_design | manual
    exchange: HttpExchange
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Sample":
        return cls(
            id=d["id"],
            scenario=d["scenario"],
            label=d["label"],
            label_source=d.get("label_source", "unknown"),
            exchange=HttpExchange(**d["exchange"]),
            notes=d.get("notes", ""),
        )


@dataclass
class Prediction:
    label: str
    confidence: float = 1.0
    evidence: List[str] = field(default_factory=list)
    reasoning: str = ""
    error: Optional[str] = None  # LLM 호출/파싱 실패 시 메시지
    raw_output: Optional[str] = None
