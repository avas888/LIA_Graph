"""Tests for the Phase 8 additive-delta HTTP controllers."""

from __future__ import annotations

import io
import json
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any
from urllib.parse import urlparse

import pytest

from lia_graph.ingestion import delta_job_store
from lia_graph.ui_ingest_delta_controllers import (
    API_PREFIX,
    handle_ingest_delta_get,
    handle_ingest_delta_post,
)


# Reuse fake client from test_delta_job_store to avoid re-writing it.
from tests.test_delta_job_store import _FakeClient


# ---- Fake auth / handler -----------------------------------------------


@dataclass
class _AuthCtx:
    role: str = "platform_admin"
    user_id: str = "admin@lia.dev"


class _AuthError(Exception):
    pass


class _FakeHandler:
    """Minimal stand-in for the BaseHTTPRequestHandler surface the
    controller talks to."""

    def __init__(
        self,
        *,
        role: str = "platform_admin",
        body: dict | None = None,
    ) -> None:
        self._auth = _AuthCtx(role=role)
        self._body = (json.dumps(body) if body is not None else "").encode("utf-8")
        self.rfile = io.BytesIO(self._body)
        self.headers = {"Content-Length": str(len(self._body))}
        self.responses: list[dict[str, Any]] = []
        # for SSE:
        self.wfile = io.BytesIO()
        self.sent_status: int | None = None
        self.sent_headers: list[tuple[str, str]] = []

    # --- auth contract ---

    def _resolve_auth_context(self, *, required: bool = False) -> _AuthCtx:
        return self._auth

    def _send_auth_error(self, exc: Any) -> None:
        self.responses.append(
            {"status": HTTPStatus.FORBIDDEN, "body": {"ok": False, "error": "auth"}}
        )

    # --- response contract ---

    def _send_json(self, status: int, body: dict) -> None:
        self.responses.append({"status": status, "body": body})

    def send_response(self, status: int) -> None:
        self.sent_status = status

    def send_header(self, name: str, value: str) -> None:
        self.sent_headers.append((name, value))

    def end_headers(self) -> None:
        pass


# ---- Fake worker submitter --------------------------------------------


def _never_submit(**kwargs: Any) -> None:
    """Worker submitter that the backend will wire up in production.

    Tests either pass this (noop) or an explicit counter so we can assert
    the submit was invoked with the expected payload.
    """
    pass


# ---- Helpers ----------------------------------------------------------


def _parsed(url: str) -> Any:
    return urlparse(url)


def _deps_for_preview(supabase_client: Any) -> dict[str, Any]:
    """Deps dict that forces the preview path to skip heavy work by
    redirecting the `materialize_delta` call through a fake."""
    return {
        "corpus_dir": "/tmp",
        "artifacts_dir": "/tmp",
        "pattern": "**/*.md",
        "generation_id": "gen_active_rolling",
        "supabase_client": supabase_client,
        "graph_client": None,
        "skip_llm": True,
        "rate_limit_rpm": 1,
        "submit_worker": _never_submit,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


# (a) non-admin hitting /apply → 403 via auth gate.
def test_apply_requires_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    handler = _FakeHandler(role="user")
    # Replace _require_admin to raise PlatformAuthError.
    from lia_graph.platform_auth import PlatformAuthError

    def _boom(h: Any) -> None:
        raise PlatformAuthError("nope", code="auth_role_forbidden", http_status=403)

    monkeypatch.setattr(
        "lia_graph.ui_ingest_delta_controllers._require_admin", _boom
    )
    result = handle_ingest_delta_post(
        handler,
        API_PREFIX + "apply",
        _parsed(API_PREFIX + "apply"),
        deps=_deps_for_preview(_FakeClient()),
    )
    assert result is True
    assert handler.responses[0]["status"] == HTTPStatus.FORBIDDEN


# (b) Apply returns 202 + job_id on happy path.
def test_apply_returns_202_with_job_id(monkeypatch: pytest.MonkeyPatch) -> None:
    handler = _FakeHandler(body={"target": "production"})
    client = _FakeClient()
    submitted: list[dict[str, Any]] = []

    def _submit(**kwargs: Any) -> None:
        submitted.append(kwargs)

    deps = _deps_for_preview(client) | {"submit_worker": _submit}
    result = handle_ingest_delta_post(
        handler,
        API_PREFIX + "apply",
        _parsed(API_PREFIX + "apply"),
        deps=deps,
    )
    assert result is True
    resp = handler.responses[0]
    assert resp["status"] == HTTPStatus.ACCEPTED
    assert "job_id" in resp["body"]
    assert resp["body"]["events_url"].startswith(API_PREFIX + "events?job_id=")
    assert len(submitted) == 1


# (c) Second /apply against the same target → 409 with blocking_job_id.
def test_second_apply_returns_409_with_blocking_job_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeClient()
    deps = _deps_for_preview(client)

    # First apply succeeds.
    h1 = _FakeHandler(body={"target": "production"})
    handle_ingest_delta_post(
        h1, API_PREFIX + "apply", _parsed(API_PREFIX + "apply"), deps=deps
    )
    first_job_id = h1.responses[0]["body"]["job_id"]

    # Second apply against the same target — expect 409.
    h2 = _FakeHandler(body={"target": "production"})
    handle_ingest_delta_post(
        h2, API_PREFIX + "apply", _parsed(API_PREFIX + "apply"), deps=deps
    )
    resp = h2.responses[0]
    assert resp["status"] == HTTPStatus.CONFLICT
    assert resp["body"]["error"] == "delta_lock_busy"
    assert resp["body"]["blocking_job_id"] == first_job_id


# (d) Status round-trips for an existing job.
def test_status_returns_job_snapshot() -> None:
    client = _FakeClient()
    delta_job_store.create_job(
        client, job_id="j_abc", lock_target="production", stage="queued"
    )
    handler = _FakeHandler()
    deps = {"supabase_client": client}
    result = handle_ingest_delta_get(
        handler,
        API_PREFIX + "status",
        _parsed(f"{API_PREFIX}status?job_id=j_abc"),
        deps=deps,
    )
    assert result is True
    resp = handler.responses[0]
    assert resp["status"] == HTTPStatus.OK
    assert resp["body"]["job"]["job_id"] == "j_abc"


# (e) Status for a missing job → 404.
def test_status_missing_job_returns_404() -> None:
    client = _FakeClient()
    handler = _FakeHandler()
    deps = {"supabase_client": client}
    handle_ingest_delta_get(
        handler,
        API_PREFIX + "status",
        _parsed(f"{API_PREFIX}status?job_id=does_not_exist"),
        deps=deps,
    )
    assert handler.responses[0]["status"] == HTTPStatus.NOT_FOUND


# (f) Cancel flips cancel_requested=true.
def test_cancel_flips_flag() -> None:
    client = _FakeClient()
    delta_job_store.create_job(
        client, job_id="j_cancel", lock_target="production", stage="parsing"
    )
    handler = _FakeHandler()
    deps = {"supabase_client": client}
    handle_ingest_delta_post(
        handler,
        API_PREFIX + "cancel",
        _parsed(f"{API_PREFIX}cancel?job_id=j_cancel"),
        deps=deps,
    )
    assert handler.responses[0]["status"] == HTTPStatus.OK
    assert handler.responses[0]["body"]["job"]["cancel_requested"] is True


# (g) Cancel a terminal job → 409.
def test_cancel_terminal_job_returns_409() -> None:
    client = _FakeClient()
    delta_job_store.create_job(
        client, job_id="j_done", lock_target="production", stage="queued"
    )
    delta_job_store.finalize(
        client, job_id="j_done", stage="completed"
    )
    handler = _FakeHandler()
    deps = {"supabase_client": client}
    handle_ingest_delta_post(
        handler,
        API_PREFIX + "cancel",
        _parsed(f"{API_PREFIX}cancel?job_id=j_done"),
        deps=deps,
    )
    assert handler.responses[0]["status"] == HTTPStatus.CONFLICT
    assert handler.responses[0]["body"]["error"] == "job_already_terminal"


# (h) Live returns the live job for reattach.
def test_live_returns_nontermal_job() -> None:
    client = _FakeClient()
    delta_job_store.create_job(
        client, job_id="j_live", lock_target="production", stage="parsing"
    )
    handler = _FakeHandler()
    handle_ingest_delta_get(
        handler,
        API_PREFIX + "live",
        _parsed(f"{API_PREFIX}live?target=production"),
        deps={"supabase_client": client},
    )
    resp = handler.responses[0]
    assert resp["status"] == HTTPStatus.OK
    assert resp["body"]["job_id"] == "j_live"


# (i) Live returns None when no live job.
def test_live_returns_none_when_idle() -> None:
    client = _FakeClient()
    handler = _FakeHandler()
    handle_ingest_delta_get(
        handler,
        API_PREFIX + "live",
        _parsed(f"{API_PREFIX}live?target=production"),
        deps={"supabase_client": client},
    )
    assert handler.responses[0]["body"]["job_id"] is None


# (j) Unknown POST route under /api/ingest/additive/ → 404.
def test_unknown_additive_post_route_returns_404() -> None:
    handler = _FakeHandler()
    handled = handle_ingest_delta_post(
        handler,
        API_PREFIX + "bogus",
        _parsed(API_PREFIX + "bogus"),
        deps={"supabase_client": _FakeClient(), "submit_worker": _never_submit},
    )
    assert handled is True
    assert handler.responses[0]["status"] == HTTPStatus.NOT_FOUND
