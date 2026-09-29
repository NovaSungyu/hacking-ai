"""규칙 기반 탐지기. LLM 없이 동작하는 '기준선(baseline)'이자 라벨링 힌트 제공용.

LLM 성능을 평가할 때 이 기준선보다 나은지 비교하는 것이 중요하다.
"""
import re
from typing import List

from .schema import HttpExchange, Prediction

SQL_ERROR_PATTERNS = [
    r"sqlite3?\.(Operational|Programming|Integrity)Error",
    r"no such (column|table)",
    r"You have an error in your SQL syntax",
    r"SQL syntax.*MySQL",
    r"unclosed quotation mark",
    r"quoted string not properly terminated",
    r"ORA-\d{5}",
    r"SQLSTATE\[\w+\]",
    r"PostgreSQL.*ERROR",
    r"psycopg2\.\w+Error",
    r"near \".*\": syntax error",
]

DEBUG_PATTERNS = [
    r"Traceback \(most recent call last\)",
    r"File \".+\", line \d+",
    r"at [\w.$]+\([\w]+\.java:\d+\)",
    r"Werkzeug Debugger",
    r"System\.\w+Exception",
    r"Fatal error:.*on line \d+",
    r"Stack trace:",
]

SECURITY_HEADERS = ["content-security-policy", "x-content-type-options", "x-frame-options"]


def _find(patterns: List[str], text: str) -> List[str]:
    hits = []
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            hits.append(m.group(0)[:120])
    return hits


class RuleDetector:
    name = "rules"

    def predict(self, ex: HttpExchange) -> Prediction:
        body = ex.response_body or ""

        hits = _find(SQL_ERROR_PATTERNS, body)
        if hits:
            return Prediction("sql_error_leak", 0.9, [f"SQL error text: {h}" for h in hits],
                              "Response body contains a database error message.")

        hits = _find(DEBUG_PATTERNS, body)
        if hits:
            return Prediction("info_disclosure", 0.9, [f"Debug/stack trace text: {h}" for h in hits],
                              "Response body exposes a stack trace or debug output.")

        if "html" in ex.content_type():
            for name, value in ex.inputs.items():
                if len(value) >= 3 and any(c in value for c in "<>") and value in body:
                    return Prediction("xss_reflected", 0.85,
                                      [f"Input '{name}'={value!r} appears unencoded in HTML body"],
                                      "Special characters from the input were reflected without encoding.")

        evidence = []
        if "html" in ex.content_type():
            present = {k.lower() for k in ex.response_headers}
            missing = [h for h in SECURITY_HEADERS if h not in present]
            if len(missing) >= 2:
                evidence.append("Missing security headers: " + ", ".join(missing))
        for c in ex.set_cookies():
            if "httponly" not in c.lower():
                evidence.append("Cookie without HttpOnly: " + c.split(";")[0].split("=")[0])
        if evidence:
            return Prediction("insecure_headers", 0.8, evidence, "Weak header/cookie configuration.")

        return Prediction("none", 0.8, [], "No known vulnerability pattern found.")
