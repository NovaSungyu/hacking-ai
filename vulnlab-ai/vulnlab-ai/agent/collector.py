"""HTTP 요청/응답 수집기. 시나리오에 적힌 '정상적인 요청'만 보내고 결과를 기록한다.

이 모듈은 페이로드를 생성하지 않는다. 어떤 입력값을 보낼지는 config/scenarios.json 에
사람이 직접 적는다. 모든 요청은 보내기 전에 safety.assert_allowed 를 통과해야 하고,
리다이렉트는 따라가지 않는다(허용 목록 밖으로 새는 것을 방지).
"""
import time
from typing import Any, Dict, Iterable, Optional

import requests

from analyzer.schema import HttpExchange
from .safety import assert_allowed


class Collector:
    def __init__(self, base_url: str, extra_allowed_hosts: Iterable[str] = (),
                 timeout_sec: float = 5.0, max_body_chars: int = 20000):
        self.base_url = base_url.rstrip("/")
        self.extra_hosts = list(extra_allowed_hosts)
        self.timeout = timeout_sec
        self.max_body = max_body_chars
        assert_allowed(self.base_url, self.extra_hosts)  # 생성 시점에도 검사
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "vulnlab-ai-collector/0.1 (local-lab-only)"

    def fetch(self, method: str, path: str, params: Optional[Dict[str, Any]] = None,
              data: Optional[Dict[str, Any]] = None,
              headers: Optional[Dict[str, str]] = None) -> HttpExchange:
        url = self.base_url + (path if path.startswith("/") else "/" + path)
        assert_allowed(url, self.extra_hosts)
        self.session.cookies.clear()  # 요청 간 상태 공유 방지
        t0 = time.perf_counter()
        resp = self.session.request(
            method.upper(), url, params=params, data=data, headers=headers,
            timeout=self.timeout, allow_redirects=False,
        )
        elapsed = (time.perf_counter() - t0) * 1000

        resp_headers: Dict[str, Any] = {k: v for k, v in resp.headers.items()
                                        if k.lower() != "set-cookie"}
        raw = getattr(resp.raw, "headers", None)
        cookies = raw.getlist("Set-Cookie") if raw is not None and hasattr(raw, "getlist") else []
        if cookies:
            resp_headers["Set-Cookie"] = cookies

        sent = params if method.upper() == "GET" else data
        return HttpExchange(
            method=method.upper(),
            url=resp.request.url,
            status_code=resp.status_code,
            response_headers=resp_headers,
            response_body=resp.text[: self.max_body],
            inputs={k: str(v) for k, v in (sent or {}).items()},
            request_headers=dict(resp.request.headers),
            request_body=resp.request.body if isinstance(resp.request.body, str) else None,
            elapsed_ms=round(elapsed, 2),
        )
