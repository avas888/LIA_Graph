from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .env_loader import load_dotenv_if_present


_HTTP_TIMEOUT_SECONDS = 12
_SOCKET_TIMEOUT_SECONDS = 8


@dataclass
class CheckResult:
    name: str
    ok: bool
    status: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)


def _mask_secret(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if len(raw) <= 8:
        return "*" * len(raw)
    return f"{raw[:4]}...{raw[-4:]}"


def _redact_url(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return raw
    auth = ""
    if parsed.username:
        auth = parsed.username
        if parsed.password:
            auth += ":***"
        auth += "@"
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    path = parsed.path or ""
    return f"{parsed.scheme}://{auth}{host}{port}{path}"


def _http_probe(url: str, *, headers: dict[str, str] | None = None) -> tuple[int | None, str]:
    request = Request(url, headers=headers or {}, method="GET")
    try:
        with urlopen(request, timeout=_HTTP_TIMEOUT_SECONDS) as response:
            body = response.read(512).decode("utf-8", errors="replace")
            return int(response.getcode()), body
    except HTTPError as exc:
        body = exc.read(512).decode("utf-8", errors="replace")
        return int(exc.code), body
    except URLError as exc:
        return None, str(exc.reason)
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def _resp_encode(*parts: str) -> bytes:
    payload = [f"*{len(parts)}\r\n".encode("utf-8")]
    for part in parts:
        encoded = str(part).encode("utf-8")
        payload.append(f"${len(encoded)}\r\n".encode("utf-8"))
        payload.append(encoded)
        payload.append(b"\r\n")
    return b"".join(payload)


def _read_exact(sock: socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise RuntimeError("Connection closed while reading response.")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _read_line(sock: socket.socket) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk = sock.recv(1)
        if not chunk:
            raise RuntimeError("Connection closed while reading line.")
        chunks.append(chunk)
        if len(chunks) >= 2 and chunks[-2] == b"\r" and chunks[-1] == b"\n":
            return b"".join(chunks[:-2])


def _read_resp(sock: socket.socket) -> Any:
    prefix = _read_exact(sock, 1)
    if prefix == b"+":
        return _read_line(sock).decode("utf-8", errors="replace")
    if prefix == b"-":
        return {"error": _read_line(sock).decode("utf-8", errors="replace")}
    if prefix == b":":
        return int(_read_line(sock).decode("utf-8", errors="replace"))
    if prefix == b"$":
        length = int(_read_line(sock).decode("utf-8", errors="replace"))
        if length < 0:
            return None
        value = _read_exact(sock, length)
        _read_exact(sock, 2)
        return value.decode("utf-8", errors="replace")
    if prefix == b"*":
        count = int(_read_line(sock).decode("utf-8", errors="replace"))
        if count < 0:
            return None
        return [_read_resp(sock) for _ in range(count)]
    raise RuntimeError(f"Unsupported RESP prefix: {prefix!r}")


def _check_supabase() -> CheckResult:
    url = str(os.getenv("SUPABASE_URL", "") or "").strip()
    anon_key = str(os.getenv("SUPABASE_ANON_KEY", "") or "").strip()
    service_key = str(os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or "").strip()
    details = {
        "url": _redact_url(url),
        "anon_key_present": bool(anon_key),
        "service_role_present": bool(service_key),
    }
    if not url:
        return CheckResult(
            name="supabase",
            ok=False,
            status="missing",
            summary="Missing SUPABASE_URL.",
            details=details,
        )
    if not anon_key and not service_key:
        return CheckResult(
            name="supabase",
            ok=False,
            status="missing",
            summary="Need SUPABASE_ANON_KEY or SUPABASE_SERVICE_ROLE_KEY.",
            details=details,
        )

    health_status, health_body = _http_probe(f"{url.rstrip('/')}/auth/v1/health")
    key_checks: list[dict[str, Any]] = []
    auth_ok = False
    for label, key in (("anon", anon_key), ("service_role", service_key)):
        if not key:
            continue
        status, body = _http_probe(
            f"{url.rstrip('/')}/rest/v1/",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
            },
        )
        accepted = status in {200, 404, 406}
        auth_ok = auth_ok or accepted
        key_checks.append(
            {
                "label": label,
                "status_code": status,
                "accepted": accepted,
                "body_preview": (body or "")[:120],
                "masked_key": _mask_secret(key),
            }
        )

    details["auth_health_status"] = health_status
    details["auth_health_preview"] = (health_body or "")[:120]
    details["key_checks"] = key_checks
    if health_status == 200 and auth_ok:
        return CheckResult(
            name="supabase",
            ok=True,
            status="ok",
            summary="Supabase URL is reachable and at least one API key was accepted by PostgREST.",
            details=details,
        )
    if auth_ok:
        return CheckResult(
            name="supabase",
            ok=True,
            status="partial",
            summary="Supabase key probe succeeded, but auth health endpoint did not return 200.",
            details=details,
        )
    return CheckResult(
        name="supabase",
        ok=False,
        status="auth_error",
        summary="Supabase was reachable, but the provided key(s) were not accepted.",
        details=details,
    )


def _check_gemini() -> CheckResult:
    api_key = str(os.getenv("GEMINI_API_KEY", "") or "").strip()
    details = {"key_present": bool(api_key), "masked_key": _mask_secret(api_key)}
    if not api_key:
        return CheckResult(
            name="gemini",
            ok=False,
            status="missing",
            summary="Missing GEMINI_API_KEY.",
            details=details,
        )
    probe_url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-embedding-001:embedContent?key="
        f"{api_key}"
    )
    payload = json.dumps(
        {
            "model": "models/gemini-embedding-001",
            "content": {"parts": [{"text": "test de conectividad para LIA_Graph"}]},
        }
    ).encode("utf-8")
    request = Request(
        probe_url,
        method="POST",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=_HTTP_TIMEOUT_SECONDS) as response:
            body = response.read(512).decode("utf-8", errors="replace")
            status = int(response.getcode())
    except HTTPError as exc:
        status = int(exc.code)
        body = exc.read(512).decode("utf-8", errors="replace")
    except URLError as exc:
        status = None
        body = str(exc.reason)
    except Exception as exc:  # noqa: BLE001
        status = None
        body = str(exc)

    details["status_code"] = status
    details["body_preview"] = (body or "")[:160]
    if status == 200:
        return CheckResult(
            name="gemini",
            ok=True,
            status="ok",
            summary="Gemini API key was accepted by the embedding endpoint.",
            details=details,
        )
    return CheckResult(
        name="gemini",
        ok=False,
        status="auth_error",
        summary="Gemini probe failed.",
        details=details,
    )


def _check_falkordb() -> CheckResult:
    raw_url = str(os.getenv("FALKORDB_URL", "") or "").strip()
    details = {"url": _redact_url(raw_url)}
    if not raw_url:
        return CheckResult(
            name="falkordb",
            ok=False,
            status="missing",
            summary="Missing FALKORDB_URL.",
            details=details,
        )

    parsed = urlparse(raw_url)
    host = parsed.hostname
    port = int(parsed.port or 6379)
    if not host:
        return CheckResult(
            name="falkordb",
            ok=False,
            status="config_error",
            summary="FALKORDB_URL is not parseable.",
            details=details,
        )

    try:
        base_socket = socket.create_connection((host, port), timeout=_SOCKET_TIMEOUT_SECONDS)
        base_socket.settimeout(_SOCKET_TIMEOUT_SECONDS)
        if parsed.scheme == "rediss":
            context = ssl.create_default_context()
            sock: socket.socket = context.wrap_socket(base_socket, server_hostname=host)
        else:
            sock = base_socket
        with sock:
            if parsed.password:
                if parsed.username:
                    sock.sendall(_resp_encode("AUTH", parsed.username, parsed.password))
                else:
                    sock.sendall(_resp_encode("AUTH", parsed.password))
                auth_response = _read_resp(sock)
                details["auth_response"] = auth_response
                if isinstance(auth_response, dict) and auth_response.get("error"):
                    return CheckResult(
                        name="falkordb",
                        ok=False,
                        status="auth_error",
                        summary="Connected to FalkorDB host, but AUTH failed.",
                        details=details,
                    )

            sock.sendall(_resp_encode("PING"))
            ping_response = _read_resp(sock)
            details["ping_response"] = ping_response
            if ping_response != "PONG":
                return CheckResult(
                    name="falkordb",
                    ok=False,
                    status="protocol_error",
                    summary="Connected to FalkorDB host, but PING did not return PONG.",
                    details=details,
                )

            sock.sendall(_resp_encode("GRAPH.LIST"))
            graph_list_response = _read_resp(sock)
            details["graph_list_response"] = graph_list_response
    except Exception as exc:  # noqa: BLE001
        details["error"] = str(exc)
        return CheckResult(
            name="falkordb",
            ok=False,
            status="connection_error",
            summary="FalkorDB connection probe failed.",
            details=details,
        )

    return CheckResult(
        name="falkordb",
        ok=True,
        status="ok",
        summary="FalkorDB accepted the connection and responded to PING/GRAPH.LIST.",
        details=details,
    )


def _check_railway() -> CheckResult:
    cli_path = shutil.which("railway")
    public_domain = str(os.getenv("RAILWAY_PUBLIC_DOMAIN", "") or "").strip()
    health_url = str(os.getenv("RAILWAY_HEALTH_URL", "") or "").strip()
    if not health_url and public_domain:
        health_url = f"https://{public_domain.strip('/')}/api/health"
    details: dict[str, Any] = {
        "cli_path": cli_path,
        "public_domain": public_domain,
        "health_url": health_url,
    }

    cli_ok = False
    if cli_path:
        try:
            proc = subprocess.run(
                [cli_path, "whoami"],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
            details["cli_returncode"] = proc.returncode
            details["cli_stdout"] = proc.stdout.strip()
            details["cli_stderr"] = proc.stderr.strip()
            cli_ok = proc.returncode == 0
        except Exception as exc:  # noqa: BLE001
            details["cli_error"] = str(exc)

    health_ok = False
    if health_url:
        status, body = _http_probe(health_url)
        details["health_status"] = status
        details["health_body_preview"] = (body or "")[:160]
        health_ok = status == 200

    if cli_ok and health_ok:
        return CheckResult(
            name="railway",
            ok=True,
            status="ok",
            summary="Railway CLI is authenticated and the deployed health endpoint responded.",
            details=details,
        )
    if cli_ok:
        return CheckResult(
            name="railway",
            ok=True,
            status="partial",
            summary="Railway CLI is authenticated, but no healthy deployment endpoint was verified yet.",
            details=details,
        )
    if health_ok:
        return CheckResult(
            name="railway",
            ok=True,
            status="partial",
            summary="Railway deployment health endpoint responded, but CLI auth was not verified.",
            details=details,
        )
    return CheckResult(
        name="railway",
        ok=False,
        status="missing",
        summary="Need Railway CLI auth and/or a Railway health URL to verify the deploy.",
        details=details,
    )


_CHECKS = {
    "supabase": _check_supabase,
    "falkordb": _check_falkordb,
    "gemini": _check_gemini,
    "railway": _check_railway,
}


def _print_human(results: list[CheckResult]) -> None:
    print("LIA_Graph dependency smoke")
    for result in results:
        icon = "OK" if result.ok else "!!"
        print(f"- [{icon}] {result.name}: {result.summary}")
        for key, value in result.details.items():
            if value in ("", None, [], {}):
                continue
            rendered = json.dumps(value, ensure_ascii=True) if isinstance(value, (dict, list)) else str(value)
            print(f"    {key}: {rendered}")


def _run(selected: list[str]) -> list[CheckResult]:
    load_dotenv_if_present()
    return [_CHECKS[name]() for name in selected]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dependency smoke checks for LIA_Graph.")
    parser.add_argument(
        "--only",
        action="append",
        choices=sorted(_CHECKS),
        help="Run only the named check. Can be passed multiple times.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args(argv)

    selected = args.only or list(_CHECKS)
    results = _run(selected)
    if args.json:
        print(json.dumps([asdict(result) for result in results], ensure_ascii=True, indent=2))
    else:
        _print_human(results)

    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
