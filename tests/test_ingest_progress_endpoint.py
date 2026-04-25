"""Tests for `GET /api/ingest/job/{id}/progress` and `/log/tail`.

Both endpoints live in `lia_graph.ui_ingest_run_controllers` and are consumed
by the Sesiones organisms `runProgressTimeline` + `runLogConsole`. These tests
lock down the contract they rely on:

* 6 stages emitted in order (``coerce, audit, chunk, sink, falkor, embeddings``)
* events in ``logs/events.jsonl`` are filtered by ``job_id``
* ``log/tail`` cursor pagination works across multiple polls
* invalid / unknown / unauthorized requests fail cleanly
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from http import HTTPStatus
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
    def __init__(
        self,
        *,
        role: str = "platform_admin",
        payload: dict[str, Any] | None = None,
    ) -> None:
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


@pytest.fixture(autouse=True)
def _silence_trace(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict[str, Any]]]:
    captured: list[tuple[str, dict[str, Any]]] = []

    def _capture(event: str, payload: dict[str, Any]) -> None:
        captured.append((event, dict(payload)))

    monkeypatch.setattr(ctrl, "_trace", _capture)
    return captured


def _deps(workspace_root: Path) -> dict[str, Any]:
    return {"workspace_root": workspace_root}


# ── helpers ───────────────────────────────────────────────────


def _write_events(
    events_path: Path,
    rows: list[dict[str, Any]],
) -> None:
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _seed_job(
    tmp_path: Path,
    *,
    job_id: str = "job-test-123",
    status: str = "running",
    log_rel: str | None = None,
) -> None:
    jobs_dir = tmp_path / "artifacts/jobs/runtime"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "job_id": job_id,
        "job_type": "ingest_run",
        "status": status,
        "request_payload": {},
        "result_payload": {"log_relative_path": log_rel} if log_rel else {},
        "error": "",
        "attempts": 1,
        "created_at": "2026-04-20T00:00:00Z",
        "updated_at": "2026-04-20T00:00:00Z",
        "completed_at": None,
    }
    (jobs_dir / f"{job_id}.json").write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture
def _redirect_jobs_dir(tmp_path: Path) -> Path:
    # Controller reads jobs under `workspace_root / "artifacts/jobs/runtime"`.
    # _seed_job writes there; nothing else to monkeypatch.
    return tmp_path / "artifacts/jobs/runtime"


# ── progress endpoint ─────────────────────────────────────────


def test_progress_skeleton_returned_when_no_events(
    tmp_path: Path, _redirect_jobs_dir: Path
) -> None:
    _seed_job(tmp_path)
    handler = _FakeHandler()
    path = "/api/ingest/job/job-test-123/progress"
    assert ctrl.handle_ingest_get(handler, path, urlparse(path), deps=_deps(tmp_path)) is True
    status, body = handler.sent[0]
    assert status == HTTPStatus.OK
    assert body["ok"] is True
    assert set(body["stages"].keys()) == set(ctrl.INGEST_STAGES)
    for stage_name in ctrl.INGEST_STAGES:
        assert body["stages"][stage_name]["status"] == "pending"


def test_progress_aggregates_stage_transitions(
    tmp_path: Path, _redirect_jobs_dir: Path
) -> None:
    _seed_job(tmp_path)
    events_path = tmp_path / "logs/events.jsonl"
    _write_events(
        events_path,
        [
            {
                "ts_utc": "2026-04-20T00:00:01Z",
                "event_type": "ingest.run.stage.coerce.start",
                "payload": {"job_id": "job-test-123"},
            },
            {
                "ts_utc": "2026-04-20T00:00:02Z",
                "event_type": "ingest.run.stage.coerce.done",
                "payload": {"job_id": "job-test-123", "counts": {"docs": 3}},
            },
            {
                "ts_utc": "2026-04-20T00:00:03Z",
                "event_type": "ingest.run.stage.audit.start",
                "payload": {"job_id": "job-test-123"},
            },
        ],
    )
    handler = _FakeHandler()
    path = "/api/ingest/job/job-test-123/progress"
    ctrl.handle_ingest_get(handler, path, urlparse(path), deps=_deps(tmp_path))
    _status, body = handler.sent[0]
    assert body["stages"]["coerce"]["status"] == "done"
    assert body["stages"]["coerce"]["counts"] == {"docs": 3}
    assert body["stages"]["audit"]["status"] == "running"
    assert body["stages"]["chunk"]["status"] == "pending"


def test_progress_surfaces_failed_stage(
    tmp_path: Path, _redirect_jobs_dir: Path
) -> None:
    _seed_job(tmp_path)
    events_path = tmp_path / "logs/events.jsonl"
    _write_events(
        events_path,
        [
            {
                "ts_utc": "2026-04-20T00:00:01Z",
                "event_type": "ingest.run.stage.sink.start",
                "payload": {"job_id": "job-test-123"},
            },
            {
                "ts_utc": "2026-04-20T00:00:02Z",
                "event_type": "ingest.run.stage.sink.failed",
                "payload": {
                    "job_id": "job-test-123",
                    "error": "supabase_unavailable",
                    "partial_counts": {"chunks_written": 17},
                },
            },
        ],
    )
    handler = _FakeHandler()
    path = "/api/ingest/job/job-test-123/progress"
    ctrl.handle_ingest_get(handler, path, urlparse(path), deps=_deps(tmp_path))
    _status, body = handler.sent[0]
    assert body["stages"]["sink"]["status"] == "failed"
    assert body["stages"]["sink"]["error"] == "supabase_unavailable"
    assert body["stages"]["sink"]["counts"]["chunks_written"] == 17
    assert body["status"] == "failed"


def test_progress_filters_events_by_job_id(
    tmp_path: Path, _redirect_jobs_dir: Path
) -> None:
    _seed_job(tmp_path)
    events_path = tmp_path / "logs/events.jsonl"
    _write_events(
        events_path,
        [
            {
                "ts_utc": "2026-04-20T00:00:01Z",
                "event_type": "ingest.run.stage.coerce.done",
                "payload": {"job_id": "other-job", "counts": {"docs": 99}},
            },
            {
                "ts_utc": "2026-04-20T00:00:02Z",
                "event_type": "ingest.run.stage.coerce.done",
                "payload": {"job_id": "job-test-123", "counts": {"docs": 3}},
            },
        ],
    )
    handler = _FakeHandler()
    path = "/api/ingest/job/job-test-123/progress"
    ctrl.handle_ingest_get(handler, path, urlparse(path), deps=_deps(tmp_path))
    _status, body = handler.sent[0]
    assert body["stages"]["coerce"]["counts"] == {"docs": 3}


def test_progress_tolerates_malformed_event_lines(
    tmp_path: Path, _redirect_jobs_dir: Path
) -> None:
    _seed_job(tmp_path)
    events_path = tmp_path / "logs/events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text(
        "not json\n"
        "{\"event_type\": \"ingest.run.stage.coerce.done\", \"payload\": {\"job_id\": \"job-test-123\"}}\n"
        "\n"
        "{\"bad\": \"yes\"\n",
        encoding="utf-8",
    )
    handler = _FakeHandler()
    path = "/api/ingest/job/job-test-123/progress"
    ctrl.handle_ingest_get(handler, path, urlparse(path), deps=_deps(tmp_path))
    _status, body = handler.sent[0]
    assert body["stages"]["coerce"]["status"] == "done"


def test_progress_404_on_unknown_job(
    tmp_path: Path, _redirect_jobs_dir: Path
) -> None:
    handler = _FakeHandler()
    path = "/api/ingest/job/does-not-exist/progress"
    ctrl.handle_ingest_get(handler, path, urlparse(path), deps=_deps(tmp_path))
    status, body = handler.sent[0]
    assert status == HTTPStatus.NOT_FOUND
    assert body["error"] == "job_not_found"


def test_progress_403_for_non_admin(
    tmp_path: Path, _redirect_jobs_dir: Path
) -> None:
    _seed_job(tmp_path)
    handler = _FakeHandler(role="tenant_user")
    path = "/api/ingest/job/job-test-123/progress"
    ctrl.handle_ingest_get(handler, path, urlparse(path), deps=_deps(tmp_path))
    status, _body = handler.sent[0]
    assert status == 403


# ── log/tail endpoint ─────────────────────────────────────────


def test_log_tail_returns_lines_and_cursor(
    tmp_path: Path, _redirect_jobs_dir: Path
) -> None:
    log_rel = "artifacts/jobs/ingest_runs/ingest_20260420T000000Z.log"
    log_path = tmp_path / log_rel
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("line 1\nline 2\nline 3\nline 4\nline 5\n", encoding="utf-8")
    _seed_job(tmp_path, log_rel=log_rel)

    handler = _FakeHandler()
    path = "/api/ingest/job/job-test-123/log/tail?cursor=0&limit=2"
    ctrl.handle_ingest_get(handler, "/api/ingest/job/job-test-123/log/tail", urlparse(path), deps=_deps(tmp_path))
    _status, body = handler.sent[0]
    assert body["lines"] == ["line 1", "line 2"]
    assert body["next_cursor"] == 2
    assert body["total_lines"] == 5


def test_log_tail_cursor_pagination(
    tmp_path: Path, _redirect_jobs_dir: Path
) -> None:
    log_rel = "artifacts/jobs/ingest_runs/ingest_paging.log"
    log_path = tmp_path / log_rel
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("\n".join(f"line {i}" for i in range(1, 11)) + "\n", encoding="utf-8")
    _seed_job(tmp_path, log_rel=log_rel)

    handler = _FakeHandler()
    path = "/api/ingest/job/job-test-123/log/tail?cursor=7&limit=5"
    ctrl.handle_ingest_get(handler, "/api/ingest/job/job-test-123/log/tail", urlparse(path), deps=_deps(tmp_path))
    _status, body = handler.sent[0]
    assert body["lines"] == ["line 8", "line 9", "line 10"]
    assert body["next_cursor"] == 10


def test_log_tail_missing_log_file_returns_empty(
    tmp_path: Path, _redirect_jobs_dir: Path
) -> None:
    _seed_job(tmp_path, log_rel="artifacts/jobs/ingest_runs/does_not_exist.log")
    handler = _FakeHandler()
    path = "/api/ingest/job/job-test-123/log/tail"
    ctrl.handle_ingest_get(handler, path, urlparse(path), deps=_deps(tmp_path))
    _status, body = handler.sent[0]
    assert body["lines"] == []
    assert body["total_lines"] == 0
    assert body["next_cursor"] == 0


def test_log_tail_job_without_log_path_returns_empty(
    tmp_path: Path, _redirect_jobs_dir: Path
) -> None:
    _seed_job(tmp_path, log_rel=None)
    handler = _FakeHandler()
    path = "/api/ingest/job/job-test-123/log/tail?cursor=0"
    ctrl.handle_ingest_get(handler, "/api/ingest/job/job-test-123/log/tail", urlparse(path), deps=_deps(tmp_path))
    _status, body = handler.sent[0]
    assert body["lines"] == []
    assert body["log_relative_path"] is None


def test_log_tail_403_for_non_admin(
    tmp_path: Path, _redirect_jobs_dir: Path
) -> None:
    _seed_job(tmp_path)
    handler = _FakeHandler(role="tenant_user")
    path = "/api/ingest/job/job-test-123/log/tail"
    ctrl.handle_ingest_get(handler, path, urlparse(path), deps=_deps(tmp_path))
    status, _body = handler.sent[0]
    assert status == 403


def test_log_tail_invalid_job_id_rejected(
    tmp_path: Path, _redirect_jobs_dir: Path
) -> None:
    # Control: a slash would break routing so pick a char the safe regex blocks.
    path = "/api/ingest/job/a%20b/log/tail"
    handler = _FakeHandler()
    parsed = urlparse(path)
    ctrl.handle_ingest_get(handler, parsed.path, parsed, deps=_deps(tmp_path))
    status, body = handler.sent[0]
    assert status == HTTPStatus.BAD_REQUEST
    assert body["error"] == "invalid_job_id"


# ── phase_signals (next_v1 step 05) ───────────────────────────


def test_progress_phase_signals_present_with_empty_events(
    tmp_path: Path, _redirect_jobs_dir: Path
) -> None:
    _seed_job(tmp_path)
    handler = _FakeHandler()
    path = "/api/ingest/job/job-test-123/progress"
    ctrl.handle_ingest_get(handler, path, urlparse(path), deps=_deps(tmp_path))
    _status, body = handler.sent[0]
    sig = body["phase_signals"]
    assert sig["classifier"]["classified"] == 0
    assert sig["classifier"]["degraded_n1_only"] == 0
    assert sig["falkor"]["batch_events"] == 0
    assert sig["sink"] is None
    assert sig["events_stale_seconds"] is None


def test_progress_phase_signals_aggregates_classifier_and_degradation(
    tmp_path: Path, _redirect_jobs_dir: Path
) -> None:
    _seed_job(tmp_path)
    events_path = tmp_path / "logs/events.jsonl"
    _write_events(
        events_path,
        [
            {
                "ts_utc": "2026-04-20T00:00:01Z",
                "event_type": "subtopic.ingest.classified",
                "payload": {"doc_id": "d1", "requires_subtopic_review": False},
            },
            {
                "ts_utc": "2026-04-20T00:00:02Z",
                "event_type": "subtopic.ingest.classified",
                "payload": {"doc_id": "d2", "requires_subtopic_review": True},
            },
            {
                "ts_utc": "2026-04-20T00:00:03Z",
                "event_type": "subtopic.ingest.classified",
                "payload": {"doc_id": "d3", "requires_subtopic_review": True},
            },
            {
                "ts_utc": "2026-04-20T00:00:04Z",
                "event_type": "corpus.sink_summary",
                "payload": {"documents": 3, "chunks": 12, "edges": 45},
            },
            {
                "ts_utc": "2026-04-20T00:00:05Z",
                "event_type": "graph.batch_written",
                "payload": {"kind": "TEMA", "count": 7, "elapsed_ms": 120},
            },
            {
                "ts_utc": "2026-04-20T00:00:06Z",
                "event_type": "graph.batch_written",
                "payload": {"kind": "ArticleNode", "count": 0, "elapsed_ms": 45},
            },
        ],
    )
    handler = _FakeHandler()
    path = "/api/ingest/job/job-test-123/progress"
    ctrl.handle_ingest_get(handler, path, urlparse(path), deps=_deps(tmp_path))
    _status, body = handler.sent[0]
    sig = body["phase_signals"]
    assert sig["classifier"]["classified"] == 3
    assert sig["classifier"]["degraded_n1_only"] == 2
    assert sig["sink"] == {"documents": 3, "chunks": 12, "edges": 45}
    assert sig["falkor"]["batch_events"] == 2
    assert sig["last_event_ts_utc"] == "2026-04-20T00:00:06Z"
    # events_stale_seconds is computed vs now() so must be a non-negative float
    assert isinstance(sig["events_stale_seconds"], float)
    assert sig["events_stale_seconds"] >= 0
