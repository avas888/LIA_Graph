from __future__ import annotations

import json
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from http.server import ThreadingHTTPServer
from http import HTTPStatus
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from lia_graph.pipeline_c.contracts import PipelineCRequest, PipelineCResponse
import lia_graph.ui_server as ui_server


def _http_json(method: str, url: str, payload: dict[str, object] | None = None, headers: dict[str, str] | None = None) -> tuple[int, dict[str, object]]:
    body = None
    req_headers = dict(headers or {})
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    request = Request(url, data=body, headers=req_headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _http_text(url: str) -> tuple[int, str, str]:
    try:
        with urlopen(url, timeout=10) as response:
            return response.status, response.headers.get_content_type(), response.read().decode("utf-8")
    except HTTPError as exc:
        return exc.code, exc.headers.get_content_type(), exc.read().decode("utf-8")


def _stub_pipeline(
    request: PipelineCRequest,
    *,
    index_file: object | None = None,
    policy_path: object | None = None,
    runtime_config_path: object | None = None,
    stream_sink: object | None = None,
) -> PipelineCResponse:
    answer = f"Smoke answer for: {request.message}"
    if stream_sink is not None:
        status = getattr(stream_sink, "status", None)
        on_llm_delta = getattr(stream_sink, "on_llm_delta", None)
        if callable(status):
            status("retrieval", "Smoke retrieval running...")
        if callable(on_llm_delta):
            on_llm_delta(answer)
    return PipelineCResponse(
        trace_id=str(request.trace_id or "trace_smoke"),
        run_id="run_smoke",
        answer_markdown=answer,
        answer_concise=answer,
        followup_queries=(),
        citations=(),
        confidence_score=0.5,
        confidence_mode="smoke",
        answer_mode="graph_native",
        fallback_reason=None,
        diagnostics={"smoke": True},
    )


@dataclass
class _ServerHandle:
    server: ThreadingHTTPServer
    thread: threading.Thread
    base_url: str


@contextmanager
def _serve_smoke_server(monkeypatch):
    monkeypatch.setattr(ui_server, "PUBLIC_MODE_ENABLED", True)
    monkeypatch.setattr(ui_server, "PUBLIC_CAPTCHA_ENABLED", False)
    monkeypatch.setattr(ui_server, "run_pipeline_d", _stub_pipeline)
    monkeypatch.setattr(ui_server, "run_pipeline_c", _stub_pipeline)

    server = ThreadingHTTPServer(("127.0.0.1", 0), ui_server.LiaUIHandler)
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield _ServerHandle(server=server, thread=thread, base_url=f"http://{host}:{port}")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_ui_server_serves_core_html_surfaces(monkeypatch) -> None:
    with _serve_smoke_server(monkeypatch) as handle:
        time.sleep(0.1)

        for path, expected_text in (
            ("/", "Redirigiendo a LIA"),
            ("/public", "LIA"),
            ("/ops", "<!doctype html>"),
            ("/admin", "<!doctype html>"),
            ("/orchestration", "<!doctype html>"),
            ("/form-guide", "<!doctype html>"),
            ("/normative-analysis", "<!doctype html>"),
            ("/login", "<!doctype html>"),
            ("/invite", "<!doctype html>"),
            ("/embed", "<!doctype html>"),
        ):
            status, content_type, body = _http_text(f"{handle.base_url}{path}")
            assert status == HTTPStatus.OK
            assert content_type == "text/html"
            assert expected_text in body

        status, payload = _http_json("GET", f"{handle.base_url}/api/health")
        assert status == HTTPStatus.OK
        assert payload["status"] == "ok"

        status, payload = _http_json("GET", f"{handle.base_url}/api/build-info")
        assert status == HTTPStatus.OK
        assert payload["ok"] is True


def test_ui_server_public_session_and_chat_routes(monkeypatch) -> None:
    with _serve_smoke_server(monkeypatch) as handle:
        time.sleep(0.1)

        status, session_payload = _http_json("POST", f"{handle.base_url}/api/public/session", {})
        assert status == HTTPStatus.OK
        assert session_payload["ok"] is True
        token = str(session_payload["token"]).strip()
        assert token

        auth_headers = {"Authorization": f"Bearer {token}"}
        status, chat_payload = _http_json(
            "POST",
            f"{handle.base_url}/api/chat",
            {"message": "Pregunta de humo", "pais": "colombia"},
            headers=auth_headers,
        )
        assert status == HTTPStatus.OK
        assert chat_payload["answer_markdown"] == "Smoke answer for: Pregunta de humo"
        assert chat_payload["answer_mode"] == "graph_native"

        request = Request(
            f"{handle.base_url}/api/chat/stream",
            data=json.dumps({"message": "Pregunta stream", "pais": "colombia"}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            assert response.status == HTTPStatus.OK
            assert "text/event-stream" in response.headers.get("Content-Type", "")
            chunks: list[str] = []
            deadline = time.time() + 10
            while time.time() < deadline:
                line = response.readline().decode("utf-8")
                if not line:
                    break
                chunks.append(line)
                body = "".join(chunks)
                if "event: final" in body and "Smoke answer for: Pregunta stream" in body:
                    break
            body = "".join(chunks)
            assert "event: final" in body
            assert "Smoke answer for: Pregunta stream" in body
