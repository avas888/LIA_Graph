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


# --- Asymmetric-retirement safety contract ----------------------------------
# The GUI surface MUST never be a click away from retiring cloud docs. The
# safety lives in `materialize_delta(allow_retirements: bool = False)` and
# the contract is: every GUI callsite passes `allow_retirements=False`
# explicitly (not relying on the default), so a refactor or a copy-paste
# from the CLI surface can't silently flip it.
# See `docs/learnings/ingestion/asymmetric-retirement-safety.md`.


def test_preview_passes_allow_retirements_false_explicitly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lock the GUI preview path's call to `materialize_delta`.

    Captures kwargs and asserts `allow_retirements=False` is passed
    explicitly. Failure modes this guards against: a refactor that drops
    the kwarg (then relies on the default — works today but loses
    grep-greppability), or a copy-paste from the CLI surface that flips
    True.
    """
    captured: dict[str, Any] = {}

    @dataclass
    class _StubReport:
        delta_id: str = "delta_test"
        baseline_generation_id: str = "gen_active_rolling"
        delta_summary: dict = None  # type: ignore[assignment]
        delta_doc_samples: dict = None  # type: ignore[assignment]

        def __post_init__(self) -> None:
            self.delta_summary = {}
            self.delta_doc_samples = {"added": [], "modified": [], "removed": []}

    def _fake_materialize(**kwargs: Any) -> _StubReport:
        captured.update(kwargs)
        return _StubReport()

    monkeypatch.setattr(
        "lia_graph.ui_ingest_delta_controllers.materialize_delta",
        _fake_materialize,
    )

    handler = _FakeHandler(body={"target": "production"})
    handle_ingest_delta_post(
        handler,
        API_PREFIX + "preview",
        _parsed(API_PREFIX + "preview"),
        deps=_deps_for_preview(_FakeClient()),
    )

    assert handler.responses[0]["status"] == HTTPStatus.OK
    # The kwarg must be present AND False — both conditions matter.
    assert "allow_retirements" in captured, (
        "GUI preview must pass allow_retirements explicitly, not rely on "
        "the default. See asymmetric-retirement-safety.md."
    )
    assert captured["allow_retirements"] is False, (
        "GUI preview MUST NEVER pass allow_retirements=True. "
        "Cloud retirement is CLI-explicit only."
    )


def test_worker_passes_allow_retirements_false_explicitly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lock the GUI apply (worker) path's call to `materialize_delta`.

    Same contract as the preview test, applied to `delta_worker._run_delta_worker`
    — the function that actually executes the apply against live Supabase + Falkor.

    Strategy: monkeypatch `materialize_delta` to capture kwargs then raise a
    marker exception so the worker bails before touching Supabase/Falkor IO.
    The test only cares about the kwargs at the call site, not the rest of
    the worker's lifecycle.
    """
    captured: dict[str, Any] = {}

    class _StopHere(Exception):
        pass

    def _fake_materialize(**kwargs: Any) -> None:
        captured.update(kwargs)
        raise _StopHere("captured — abort before live IO")

    monkeypatch.setattr(
        "lia_graph.ingestion.delta_runtime.materialize_delta",
        _fake_materialize,
    )

    from lia_graph.ingestion import delta_worker, delta_job_store as djs

    # No-op the stage updaters + cancel check + heartbeat so the worker
    # gets to the materialize_delta call site quickly.
    monkeypatch.setattr(djs, "update_stage", lambda *a, **k: None)
    monkeypatch.setattr(djs, "finalize", lambda *a, **k: None)
    monkeypatch.setattr(delta_worker, "_check_cancel", lambda *a, **k: False)
    monkeypatch.setattr(
        delta_worker,
        "_heartbeat_every",
        lambda *a, **k: None,
    )

    # Stub the supabase-client resolver so the worker doesn't try to build
    # a real client from env. Returns the fake one.
    monkeypatch.setattr(
        delta_worker, "_resolve_supabase_client", lambda d, t: _FakeClient()
    )

    # The worker raises the marker exception; we expect it to propagate up
    # because we replaced finalize() with a no-op. Catch and assert kwargs.
    try:
        delta_worker._run_delta_worker(
            job_id="job_abc",
            target="production",
            deps={"corpus_dir": "/tmp", "artifacts_dir": "/tmp"},
        )
    except _StopHere:
        pass  # expected — we aborted on purpose after capturing kwargs

    assert "allow_retirements" in captured, (
        "GUI apply (worker) must pass allow_retirements explicitly. "
        "See asymmetric-retirement-safety.md."
    )
    assert captured["allow_retirements"] is False, (
        "GUI apply (worker) MUST NEVER pass allow_retirements=True. "
        "Cloud retirement is CLI-explicit only."
    )


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


# ---------------------------------------------------------------------------
# Fase C: SSE tail of events.jsonl
# ---------------------------------------------------------------------------


def _seed_job_row(client: _FakeClient, *, job_id: str, delta_id: str) -> None:
    """Plant an in-progress job row so `_handle_events` resolves it."""
    delta_job_store.create_job(
        client,
        job_id=job_id,
        lock_target="production",
        delta_id=delta_id,
        created_by="test",
    )


def _write_events_jsonl(path: Any, events: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")


def _read_sse_messages(handler: _FakeHandler) -> list[tuple[str, dict]]:
    """Parse the SSE bytes the handler wrote into (event_type, payload)
    tuples. Comments (`: keepalive`) and `retry:` directives are dropped.
    """
    raw = handler.wfile.getvalue().decode("utf-8")
    messages: list[tuple[str, dict]] = []
    current_event: str | None = None
    for line in raw.split("\n"):
        if line.startswith("event: "):
            current_event = line[len("event: ") :].strip()
        elif line.startswith("data: "):
            payload_str = line[len("data: ") :]
            try:
                payload = json.loads(payload_str)
            except json.JSONDecodeError:
                payload = {"__raw__": payload_str}
            messages.append((current_event or "message", payload))
            current_event = None
    return messages


def test_sse_handler_sends_initial_snapshot_then_streams_matching_events(
    tmp_path: Any,
) -> None:
    """The 2026-04-26 incident: SSE closed after the first snapshot. Now
    it tails events.jsonl and forwards events tagged with this job_id /
    delta_id until a terminal event lands."""
    client = _FakeClient()
    _seed_job_row(client, job_id="job_sse_001", delta_id="delta_xyz")

    events_path = tmp_path / "logs" / "events.jsonl"
    _write_events_jsonl(
        events_path,
        [
            # Pre-existing event (before we tail): seek-to-end skips this.
            {
                "ts_utc": "2026-04-26T15:00:00+00:00",
                "event_type": "ingest.delta.run.start",
                "payload": {"delta_id": "delta_other", "target": "production"},
            },
        ],
    )

    deps = {
        "supabase_client": client,
        "events_log_path": events_path,
        "sse_sleep_fn": lambda _: None,
        "sse_max_iterations": 50,
        "sse_max_duration_s": 5,
        "sse_keepalive_interval_s": 100,  # don't fire keepalive in test
        "sse_poll_interval_s": 0,
        # Tests pre-write events; flip the seek so the handler reads them
        # instead of starting from end-of-file. Production stays seek-to-end.
        "sse_seek_to_end": False,
    }

    handler = _FakeHandler()

    def append_after_snapshot() -> None:
        # Append events AFTER the handler started tailing. This simulates
        # the worker emitting events in real time.
        with events_path.open("a", encoding="utf-8") as fh:
            for ev in [
                # Cross-job event: should be filtered out.
                {
                    "ts_utc": "2026-04-26T15:00:01+00:00",
                    "event_type": "ingest.delta.worker.stage",
                    "payload": {"job_id": "different_job", "stage": "parsing"},
                },
                # Matches job_id.
                {
                    "ts_utc": "2026-04-26T15:00:02+00:00",
                    "event_type": "ingest.delta.worker.stage",
                    "payload": {"job_id": "job_sse_001", "stage": "supabase"},
                },
                # Matches delta_id.
                {
                    "ts_utc": "2026-04-26T15:00:03+00:00",
                    "event_type": "ingest.delta.parity.check.done",
                    "payload": {"delta_id": "delta_xyz", "ok": True},
                },
                # Global pass-through (no job_id/delta_id tag).
                {
                    "ts_utc": "2026-04-26T15:00:04+00:00",
                    "event_type": "subtopic.ingest.classified",
                    "payload": {"filename": "Resolucion-532.md", "topic_key": "iva"},
                },
                # Terminal — closes the stream.
                {
                    "ts_utc": "2026-04-26T15:00:05+00:00",
                    "event_type": "ingest.delta.worker.done",
                    "payload": {"job_id": "job_sse_001", "outcome": "completed"},
                },
            ]:
                fh.write(json.dumps(ev, ensure_ascii=False) + "\n")

    # Append events BEFORE handler runs since our test loop is synchronous.
    # The handler seeks to end then reads new lines on each iteration —
    # we pre-write so the handler's readline picks them up.
    append_after_snapshot()

    handled = handle_ingest_delta_get(
        handler,
        API_PREFIX + "events",
        _parsed(f"{API_PREFIX}events?job_id=job_sse_001"),
        deps=deps,
    )
    assert handled is True

    messages = _read_sse_messages(handler)
    event_types = [m[0] for m in messages]

    # Initial snapshot must be the first message.
    assert event_types[0] == "snapshot"
    snapshot_payload = messages[0][1]
    assert snapshot_payload["job_id"] == "job_sse_001"

    # Cross-job event was filtered out.
    job_stage_events = [
        p for et, p in messages if et == "ingest.delta.worker.stage"
    ]
    assert all(p["payload"]["job_id"] == "job_sse_001" for p in job_stage_events)

    # Matched events flowed through.
    assert "ingest.delta.parity.check.done" in event_types
    assert "subtopic.ingest.classified" in event_types
    assert "ingest.delta.worker.done" in event_types

    # Stream closed on terminal — no more events after worker.done.
    done_idx = event_types.index("ingest.delta.worker.done")
    assert done_idx == len(event_types) - 1, (
        f"Events after terminal: {event_types[done_idx:]}"
    )


def test_sse_handler_lifts_token_query_param_into_authorization_header(
    tmp_path: Any,
) -> None:
    """EventSource can't send headers; the SSE caller passes the bearer
    via `?token=...`. The dispatch must lift it into `Authorization`
    BEFORE `_require_admin` runs so the standard auth flow validates it.
    """
    client = _FakeClient()
    _seed_job_row(client, job_id="job_sse_002", delta_id="delta_a")
    events_path = tmp_path / "logs" / "events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text("", encoding="utf-8")

    handler = _FakeHandler()
    # Critical: NO Authorization header set on the handler initially.
    assert "Authorization" not in handler.headers

    deps = {
        "supabase_client": client,
        "events_log_path": events_path,
        "sse_sleep_fn": lambda _: None,
        "sse_max_iterations": 1,
        "sse_max_duration_s": 1,
        "sse_keepalive_interval_s": 100,
        "sse_poll_interval_s": 0,
    }
    handle_ingest_delta_get(
        handler,
        API_PREFIX + "events",
        _parsed(
            f"{API_PREFIX}events?job_id=job_sse_002&token=abc.def.ghi"
        ),
        deps=deps,
    )

    # The query-param token was lifted into the header so `_require_admin`
    # could validate it via the existing flow.
    assert handler.headers.get("Authorization") == "Bearer abc.def.ghi"
    # And the SSE response started.
    assert handler.sent_status == HTTPStatus.OK


def test_sse_handler_returns_404_for_unknown_job(tmp_path: Any) -> None:
    client = _FakeClient()  # no row planted
    events_path = tmp_path / "logs" / "events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text("", encoding="utf-8")

    handler = _FakeHandler()
    deps = {
        "supabase_client": client,
        "events_log_path": events_path,
        "sse_sleep_fn": lambda _: None,
    }
    handle_ingest_delta_get(
        handler,
        API_PREFIX + "events",
        _parsed(f"{API_PREFIX}events?job_id=ghost"),
        deps=deps,
    )
    assert handler.responses[0]["status"] == HTTPStatus.NOT_FOUND


def test_sse_handler_emits_error_event_when_log_missing(tmp_path: Any) -> None:
    client = _FakeClient()
    _seed_job_row(client, job_id="job_sse_003", delta_id="delta_z")
    events_path = tmp_path / "logs" / "events.jsonl"
    # Intentionally do NOT create the file.

    handler = _FakeHandler()
    deps = {
        "supabase_client": client,
        "events_log_path": events_path,
        "sse_sleep_fn": lambda _: None,
    }
    handle_ingest_delta_get(
        handler,
        API_PREFIX + "events",
        _parsed(f"{API_PREFIX}events?job_id=job_sse_003"),
        deps=deps,
    )

    messages = _read_sse_messages(handler)
    event_types = [m[0] for m in messages]
    # snapshot fires first, then an error event with the missing-log reason.
    assert event_types[0] == "snapshot"
    assert "error" in event_types
    err_payload = next(p for et, p in messages if et == "error")
    assert err_payload["reason"] == "events_log_missing"
