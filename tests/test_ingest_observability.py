"""Phase 7 smoke: every documented trace event fires at the documented seam.

This test walks the documented §13 trace schema of ``docs/next/ingestfixv1.md``
and asserts the corresponding code path actually emits the event. The goal is
to stop silent regressions where an endpoint is refactored and its trace
payload quietly vanishes.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pytest

from lia_graph import ui_ingest_run_controllers as ctrl
from lia_graph.platform_auth import PlatformAuthError


@dataclass
class _AuthContext:
    role: str = "platform_admin"
    user_id: str = "usr_admin_test"
    tenant_id: str = "tenant-test"


class _FakeHandler:
    def __init__(self, *, role: str = "platform_admin", payload: dict[str, Any] | None = None) -> None:
        self._auth = _AuthContext(role=role)
        self._payload = payload
        self.sent: list[tuple[int, dict[str, Any]]] = []

    def _resolve_auth_context(self, *, required: bool = False) -> _AuthContext:  # noqa: ARG002
        return self._auth

    def _send_auth_error(self, exc: PlatformAuthError) -> None:
        self.sent.append((int(getattr(exc, "http_status", 401)), {"error": str(exc)}))

    def _read_json_payload(self, **_kwargs: Any) -> dict[str, Any] | None:
        return self._payload

    def _send_json(self, status: int, body: dict[str, Any], **_kwargs: Any) -> None:
        self.sent.append((int(status), body))


@pytest.fixture
def _captured_trace(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict[str, Any]]]:
    captured: list[tuple[str, dict[str, Any]]] = []

    def _capture(event: str, payload: dict[str, Any]) -> None:
        captured.append((event, dict(payload)))

    monkeypatch.setattr(ctrl, "_trace", _capture)
    return captured


@pytest.fixture(autouse=True)
def _stub_supabase(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ctrl, "_checksum_already_ingested", lambda checksum: None)
    monkeypatch.setattr(ctrl, "_query_active_generation", lambda: None)
    monkeypatch.setattr(ctrl, "_query_generations", lambda limit=20: [])


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _deps(tmp: Path) -> dict[str, Any]:
    return {"workspace_root": tmp}


def test_get_state_emits_requested_and_served(
    tmp_path: Path, _captured_trace: list[tuple[str, dict[str, Any]]]
) -> None:
    handler = _FakeHandler()
    parsed = urlparse("/api/ingest/state")
    ctrl.handle_ingest_get(handler, "/api/ingest/state", parsed, deps=_deps(tmp_path))
    events = [name for name, _ in _captured_trace]
    assert "ingest.state.requested" in events
    assert "ingest.state.served" in events


def test_post_run_emits_requested_and_dispatched(
    tmp_path: Path,
    _captured_trace: list[tuple[str, dict[str, Any]]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ctrl, "run_job_async", lambda *, task, **kw: "job-fake")  # noqa: ARG005
    handler = _FakeHandler(payload={"supabase_target": "wip"})
    ctrl.handle_ingest_post(handler, "/api/ingest/run", deps=_deps(tmp_path))
    events = [name for name, _ in _captured_trace]
    assert "ingest.run.requested" in events
    assert "ingest.run.dispatched" in events


def test_intake_emits_canonical_event_trail(
    tmp_path: Path, _captured_trace: list[tuple[str, dict[str, Any]]]
) -> None:
    handler = _FakeHandler(
        payload={
            "batch_id": "trace-test",
            "files": [{"filename": "NOM-x.md", "content_base64": _b64("# doc\n\nUGPP body")}],
        }
    )
    ctrl.handle_ingest_post(handler, "/api/ingest/intake", deps=_deps(tmp_path))
    events = [name for name, _ in _captured_trace]
    assert events[0] == "ingest.intake.received"
    assert "ingest.intake.classified" in events
    assert "ingest.intake.placed" in events
    assert events[-1] == "ingest.intake.summary"


def test_progress_endpoint_emits_request_event(
    tmp_path: Path,
    _captured_trace: list[tuple[str, dict[str, Any]]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from lia_graph import jobs_store as js

    jobs_dir = tmp_path / "artifacts/jobs/runtime"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    (jobs_dir / "progjob.json").write_text(
        '{"job_id": "progjob", "job_type": "ingest_run", "status": "running", '
        '"request_payload": {}, "result_payload": {}, "error": "", "attempts": 1, '
        '"created_at": "2026-04-20T00:00:00Z", "updated_at": "2026-04-20T00:00:00Z"}',
        encoding="utf-8",
    )
    handler = _FakeHandler()
    path = "/api/ingest/job/progjob/progress"
    ctrl.handle_ingest_get(handler, path, urlparse(path), deps=_deps(tmp_path))
    events = [name for name, _ in _captured_trace]
    assert "ingest.progress.requested" in events


def test_log_tail_emits_served_event(
    tmp_path: Path,
    _captured_trace: list[tuple[str, dict[str, Any]]],
) -> None:
    jobs_dir = tmp_path / "artifacts/jobs/runtime"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    (jobs_dir / "tailjob.json").write_text(
        '{"job_id": "tailjob", "job_type": "ingest_run", "status": "running", '
        '"request_payload": {}, "result_payload": {"log_relative_path": '
        '"artifacts/jobs/ingest_runs/t.log"}, "error": "", "attempts": 1, '
        '"created_at": "2026-04-20T00:00:00Z", "updated_at": "2026-04-20T00:00:00Z"}',
        encoding="utf-8",
    )
    log_path = tmp_path / "artifacts/jobs/ingest_runs/t.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("hello\nworld\n", encoding="utf-8")
    handler = _FakeHandler()
    path = "/api/ingest/job/tailjob/log/tail"
    ctrl.handle_ingest_get(handler, path, urlparse(path), deps=_deps(tmp_path))
    events = [name for name, _ in _captured_trace]
    assert "ingest.log.tail.served" in events


def test_intake_failure_path_emits_failed_event(
    tmp_path: Path, _captured_trace: list[tuple[str, dict[str, Any]]]
) -> None:
    handler = _FakeHandler(
        payload={"files": [{"filename": "bad.exe", "content_base64": _b64("x")}]}
    )
    ctrl.handle_ingest_post(handler, "/api/ingest/intake", deps=_deps(tmp_path))
    failed = [p for name, p in _captured_trace if name == "ingest.intake.failed"]
    assert failed, "expected ingest.intake.failed for unsupported extension"
    assert failed[0]["error"] == "unsupported_extension"
