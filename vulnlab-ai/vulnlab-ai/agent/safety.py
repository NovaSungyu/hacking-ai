"""안전장치: 허용된 로컬/실습 호스트가 아니면 요청 자체를 만들지 않는다.

- 기본 허용: localhost, 루프백 IP(127.0.0.0/8, ::1)
- 추가 허용: settings.json 의 lab.extra_allowed_hosts 에 '직접' 적은 호스트 이름
  (예: docker-compose 서비스명). 단, DNS 해석 결과가 공인(global) IP면 여전히 차단.
"""
import ipaddress
import socket
from typing import Iterable
from urllib.parse import urlparse

LOOPBACK_NAMES = {"localhost"}


class TargetNotAllowed(Exception):
    """허용되지 않은 대상에 요청하려 할 때 발생."""


def assert_allowed(url: str, extra_hosts: Iterable[str] = ()) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise TargetNotAllowed(f"scheme not allowed: {parsed.scheme!r}")
    host = (parsed.hostname or "").lower()
    if not host:
        raise TargetNotAllowed("empty host")
    extra = {h.lower() for h in extra_hosts}

    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None

    if literal is not None:  # IP 리터럴
        if literal.is_loopback:
            return
        if host in extra and not literal.is_global:
            return
        raise TargetNotAllowed(f"IP not allowed: {host}")

    if host not in LOOPBACK_NAMES and host not in extra:
        raise TargetNotAllowed(f"host not in allowlist: {host}")

    try:  # 이름이 실제로 공인 IP를 가리키면 차단
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise TargetNotAllowed(f"cannot resolve {host}: {e}")
    for info in infos:
        addr = ipaddress.ip_address(info[4][0].split("%")[0])
        if addr.is_global:
            raise TargetNotAllowed(f"{host} resolves to a public address ({addr})")
