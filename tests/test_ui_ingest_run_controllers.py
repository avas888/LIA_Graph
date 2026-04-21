"""Tests for `lia_graph.ui_ingest_run_controllers`.

Covers the four routes the Sesiones admin panel calls:

  * GET  /api/ingest/state
  * GET  /api/ingest/generations
  * GET  /api/ingest/generations/{id}
  * POST /api/ingest/run

Plus the dispatcher's negative path (returns False for unrelated URLs) so
the controller chain in `ui_server.py` stays composable.

All tests stub the Supabase + subprocess seams — there is no live cloud or
``make`` invocation. The trace events emitted by the controller are
captured via monkeypatching the module-level ``_trace`` to keep
``logs/events.jsonl`` clean during tests.
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
    """Minimal handler double mirroring `BaseHTTPRequestHandler` surface."""

    def __init__(
        self,
        *,
        role: str = "platform_admin",
        payload: dict[str, Any] | None = None,
    ) -> None:
        self._auth = _AuthContext(role=role)
        self._payload = payload
        self.sent: list[tuple[int, dict[str, Any]]] = []

    # auth surface
    def _resolve_auth_context(self, *, required: bool = False) -> _AuthContext:  # noqa: ARG002
        return self._auth

    def _send_auth_error(self, exc: PlatformAuthError) -> None:
        self.sent.append((int(getattr(exc, "http_status", 401)), {"error": str(exc)}))

    # body surface
    def _read_json_payload(self, **_kwargs: Any) -> dict[str, Any] | None:
        return self._payload

    def _send_json(self, status: int, body: dict[str, Any], **_kwargs: Any) -> None:
        self.sent.append((int(status), body))


@pytest.fixture(autouse=True)
def _silence_trace(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict[str, Any]]]:
    """Capture trace events without writing to logs/events.jsonl."""
    captured: list[tuple[str, dict[str, Any]]] = []

    def _capture(event: str, payload: dict[str, Any]) -> None:
        captured.append((event, dict(payload)))

    monkeypatch.setattr(ctrl, "_trace", _capture)
    return captured


def _deps(workspace_root: Path) -> dict[str, Any]:
    return {"workspace_root": workspace_root}


# ── Dispatcher composability ──────────────────────────────────


def test_get_returns_false_for_unrelated_path(tmp_path: Path) -> None:
    handler = _FakeHandler()
    assert ctrl.handle_ingest_get(handler, "/api/something-else", urlparse("/api/something-else"), deps=_deps(tmp_path)) is False
    assert handler.sent == []


def test_post_returns_false_for_unrelated_path(tmp_path: Path) -> None:
    handler = _FakeHandler(payload={})
    assert ctrl.handle_ingest_post(handler, "/api/something-else", deps=_deps(tmp_path)) is False
    assert handler.sent == []


# ── Authorization ─────────────────────────────────────────────


def test_get_state_rejects_non_admin(tmp_path: Path) -> None:
    handler = _FakeHandler(role="tenant_user")
    assert ctrl.handle_ingest_get(handler, "/api/ingest/state", urlparse("/api/ingest/state"), deps=_deps(tmp_path)) is True
    status, body = handler.sent[0]
    assert status == 403
    assert "rol administrativo" in body["error"]


def test_post_run_rejects_non_admin(tmp_path: Path) -> None:
    handler = _FakeHandler(role="tenant_user", payload={})
    assert ctrl.handle_ingest_post(handler, "/api/ingest/run", deps=_deps(tmp_path)) is True
    status, body = handler.sent[0]
    assert status == 403


# ── GET /api/ingest/state ─────────────────────────────────────


def _seed_artifacts(tmp_path: Path) -> Path:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "corpus_audit_report.json").write_text(
        json.dumps(
            {
                "scanned_file_count": 1385,
                "decision_counts": {"include_corpus": 1292, "exclude_internal": 93, "revision_candidate": 0},
                "taxonomy_version": "draft_v1_test",
                "source_origin_counts": {"core_ya_arriba": 1255, "to_upload": 64},
                "source_tier_counts": {"normativo": 1044},
                "authority_level_counts": {"primary_legal_authority": 1044},
            }
        )
    )
    (artifacts / "corpus_inventory.json").write_text(
        json.dumps(
            {
                "normativa": {"document_count": 1044},
                "interpretacion": {"document_count": 89},
                "practica": {"document_count": 159},
            }
        )
    )
    (artifacts / "graph_validation_report.json").write_text(
        json.dumps({"ok": True, "node_count": 2617, "edge_count": 20345})
    )
    (artifacts / "revision_candidates.json").write_text(
        json.dumps({"revision_candidates": []})
    )
    return artifacts


def test_get_state_assembles_full_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_artifacts(tmp_path)
    monkeypatch.setattr(
        ctrl,
        "_query_active_generation",
        lambda: {
            "generation_id": "gen_2026_04_19_smoke",
            "activated_at": "2026-04-19T18:20:00+00:00",
            "generated_at": "2026-04-19T18:00:00+00:00",
            "documents": 1246,
            "chunks": 8400,
            "knowledge_class_counts": {"normativa": 1044},
            "countries": ["colombia"],
        },
    )

    handler = _FakeHandler()
    parsed = urlparse("/api/ingest/state")
    assert ctrl.handle_ingest_get(handler, "/api/ingest/state", parsed, deps=_deps(tmp_path)) is True
    status, body = handler.sent[0]
    assert status == HTTPStatus.OK
    assert body["ok"] is True
    assert body["corpus"]["active_generation_id"] == "gen_2026_04_19_smoke"
    assert body["corpus"]["documents"] == 1246
    assert body["audit"]["scanned"] == 1385
    assert body["audit"]["include_corpus"] == 1292
    assert body["audit"]["pending_revisions"] == 0
    assert body["graph"]["nodes"] == 2617
    assert body["graph"]["ok"] is True
    assert body["inventory"]["normativa"] == 1044


def test_get_state_handles_missing_artifacts_gracefully(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ctrl, "_query_active_generation", lambda: None)
    handler = _FakeHandler()
    parsed = urlparse("/api/ingest/state")
    assert ctrl.handle_ingest_get(handler, "/api/ingest/state", parsed, deps=_deps(tmp_path)) is True
    status, body = handler.sent[0]
    assert status == HTTPStatus.OK
    assert body["audit"]["scanned"] == 0
    assert body["corpus"]["documents"] == 0
    assert body["graph"]["ok"] is False


# ── GET /api/ingest/generations ───────────────────────────────


def test_get_generations_list_passes_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured_limits: list[int] = []

    def _fake_query(*, limit: int = 20) -> list[dict[str, Any]]:
        captured_limits.append(limit)
        return [
            {"generation_id": "gen_a", "is_active": True, "documents": 10, "chunks": 30},
            {"generation_id": "gen_b", "is_active": False, "documents": 5, "chunks": 12},
        ]

    monkeypatch.setattr(ctrl, "_query_generations", _fake_query)
    handler = _FakeHandler()
    parsed = urlparse("/api/ingest/generations?limit=5")
    assert (
        ctrl.handle_ingest_get(handler, "/api/ingest/generations", parsed, deps=_deps(tmp_path))
        is True
    )
    status, body = handler.sent[0]
    assert status == HTTPStatus.OK
    assert captured_limits == [5]
    assert len(body["generations"]) == 2


def test_get_generations_list_default_limit_when_invalid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured_limits: list[int] = []

    def _fake_query(*, limit: int = 20) -> list[dict[str, Any]]:
        captured_limits.append(limit)
        return []

    monkeypatch.setattr(ctrl, "_query_generations", _fake_query)
    handler = _FakeHandler()
    parsed = urlparse("/api/ingest/generations?limit=notanumber")
    ctrl.handle_ingest_get(handler, "/api/ingest/generations", parsed, deps=_deps(tmp_path))
    assert captured_limits == [20]


# ── GET /api/ingest/generations/{id} ──────────────────────────


def test_get_generation_detail_returns_404_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ctrl, "_query_generation", lambda generation_id: None)
    handler = _FakeHandler()
    path = "/api/ingest/generations/gen_does_not_exist"
    assert ctrl.handle_ingest_get(handler, path, urlparse(path), deps=_deps(tmp_path)) is True
    status, body = handler.sent[0]
    assert status == HTTPStatus.NOT_FOUND
    assert body["error"] == "generation_not_found"


def test_get_generation_detail_rejects_unsafe_id(tmp_path: Path) -> None:
    handler = _FakeHandler()
    # Slash in the id wouldn't even match the route — pick another bad char.
    path = "/api/ingest/generations/gen with space"
    parsed = urlparse(path.replace(" ", "%20"))
    # The router only matches `[^/]+` so the percent-encoded value still hits;
    # the safe-id regex must reject it.
    handled = ctrl.handle_ingest_get(handler, parsed.path, parsed, deps=_deps(tmp_path))
    assert handled is True
    status, body = handler.sent[0]
    assert status == HTTPStatus.BAD_REQUEST
    assert body["error"] == "invalid_generation_id"


def test_get_generation_detail_returns_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        ctrl,
        "_query_generation",
        lambda generation_id: {"generation_id": generation_id, "documents": 1, "chunks": 3},
    )
    handler = _FakeHandler()
    path = "/api/ingest/generations/gen_alpha"
    assert ctrl.handle_ingest_get(handler, path, urlparse(path), deps=_deps(tmp_path)) is True
    status, body = handler.sent[0]
    assert status == HTTPStatus.OK
    assert body["generation"]["generation_id"] == "gen_alpha"


# ── POST /api/ingest/run ──────────────────────────────────────


def test_run_post_rejects_invalid_target(tmp_path: Path) -> None:
    handler = _FakeHandler(payload={"supabase_target": "garbage"})
    assert ctrl.handle_ingest_post(handler, "/api/ingest/run", deps=_deps(tmp_path)) is True
    status, body = handler.sent[0]
    assert status == HTTPStatus.BAD_REQUEST
    assert body["error"] == "invalid_supabase_target"


def test_run_post_rejects_unsafe_suin_scope(tmp_path: Path) -> None:
    handler = _FakeHandler(payload={"supabase_target": "wip", "suin_scope": "et;rm -rf"})
    assert ctrl.handle_ingest_post(handler, "/api/ingest/run", deps=_deps(tmp_path)) is True
    status, body = handler.sent[0]
    assert status == HTTPStatus.BAD_REQUEST
    assert body["error"] == "invalid_suin_scope"


def test_run_post_dispatches_job_with_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured_kwargs: dict[str, Any] = {}

    def _fake_run_job_async(*, task: Any, **kwargs: Any) -> str:
        captured_kwargs.update(kwargs)
        captured_kwargs["task"] = task
        return "job-fake-1"

    monkeypatch.setattr(ctrl, "run_job_async", _fake_run_job_async)
    handler = _FakeHandler(payload={})
    assert ctrl.handle_ingest_post(handler, "/api/ingest/run", deps=_deps(tmp_path)) is True
    status, body = handler.sent[0]
    assert status == HTTPStatus.OK
    assert body["job_id"] == "job-fake-1"
    assert captured_kwargs["job_type"] == "ingest_run"
    assert captured_kwargs["request_payload"] == {"suin_scope": "", "supabase_target": "wip"}


def test_run_post_accepts_production_target_and_suin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        ctrl,
        "run_job_async",
        lambda *, task, **kwargs: captured.setdefault("kwargs", kwargs) or "job-2",
    )
    handler = _FakeHandler(payload={"supabase_target": "production", "suin_scope": "et"})
    ctrl.handle_ingest_post(handler, "/api/ingest/run", deps=_deps(tmp_path))
    assert captured["kwargs"]["request_payload"] == {
        "suin_scope": "et",
        "supabase_target": "production",
    }


# ── Subprocess wrapper ────────────────────────────────────────


def test_spawn_subprocess_builds_canonical_make_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, Any] = {}

    class _FakeCompletedProcess:
        returncode = 0

    def _fake_run(cmd: list[str], **kwargs: Any) -> Any:
        captured["cmd"] = cmd
        captured["cwd"] = kwargs.get("cwd")
        return _FakeCompletedProcess()

    monkeypatch.setattr(ctrl.subprocess, "run", _fake_run)

    result = ctrl._spawn_ingest_subprocess(
        tmp_path, suin_scope="et", supabase_target="wip"
    )
    assert captured["cmd"][:3] == ["make", "phase2-graph-artifacts-supabase", "PHASE2_SUPABASE_TARGET=wip"]
    assert "INGEST_SUIN=et" in captured["cmd"]
    assert captured["cwd"] == str(tmp_path)
    assert result["exit_code"] == 0
    assert result["supabase_target"] == "wip"
    assert result["suin_scope"] == "et"
    # Log file was created
    log_dir = tmp_path / "artifacts" / "jobs" / "ingest_runs"
    assert log_dir.exists()
    assert any(log_dir.glob("ingest_*.log"))


def test_spawn_subprocess_omits_suin_when_scope_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, Any] = {}

    class _FakeCompletedProcess:
        returncode = 0

    def _fake_run(cmd: list[str], **kwargs: Any) -> Any:  # noqa: ARG001
        captured["cmd"] = cmd
        return _FakeCompletedProcess()

    monkeypatch.setattr(ctrl.subprocess, "run", _fake_run)
    ctrl._spawn_ingest_subprocess(tmp_path, suin_scope="", supabase_target="wip")
    assert not any(arg.startswith("INGEST_SUIN=") for arg in captured["cmd"])
