"""Tests for the Phase 6 auto-chain dispatch in ``_spawn_ingest_subprocess``.

We don't actually invoke ``make`` or ``bash scripts/ingest_run_full.sh`` here —
``subprocess.run`` is monkeypatched. The tests lock down the routing decision
(make vs bash wrapper), env-var handoff, and trace-event emission.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from lia_graph import ui_ingest_run_controllers as ctrl


@dataclass
class _FakeCompleted:
    returncode: int = 0


@pytest.fixture
def _captured_subprocess(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def _run(cmd, **kwargs):  # noqa: ANN001
        calls.append(
            {
                "cmd": list(cmd),
                "env": dict(kwargs.get("env") or {}),
                "cwd": kwargs.get("cwd"),
            }
        )
        return _FakeCompleted(returncode=0)

    monkeypatch.setattr(subprocess, "run", _run)
    return calls


@pytest.fixture(autouse=True)
def _silence_trace(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict[str, Any]]]:
    captured: list[tuple[str, dict[str, Any]]] = []

    def _capture(event: str, payload: dict[str, Any]) -> None:
        captured.append((event, dict(payload)))

    monkeypatch.setattr(ctrl, "_trace", _capture)
    return captured


def test_default_path_uses_make_directly(
    tmp_path: Path, _captured_subprocess: list[dict[str, Any]]
) -> None:
    ctrl._spawn_ingest_subprocess(
        tmp_path,
        suin_scope="",
        supabase_target="wip",
        job_id="job-001",
        auto_embed=False,
        auto_promote=False,
    )
    assert len(_captured_subprocess) == 1
    cmd = _captured_subprocess[0]["cmd"]
    assert cmd[0] == "make"
    assert "phase2-graph-artifacts-supabase" in cmd


def test_auto_embed_flag_dispatches_bash_wrapper(
    tmp_path: Path, _captured_subprocess: list[dict[str, Any]]
) -> None:
    ctrl._spawn_ingest_subprocess(
        tmp_path,
        suin_scope="tributario",
        supabase_target="wip",
        job_id="job-002",
        auto_embed=True,
        auto_promote=False,
    )
    cmd = _captured_subprocess[0]["cmd"]
    assert cmd[:2] == ["bash", "scripts/ingest_run_full.sh"]
    env = _captured_subprocess[0]["env"]
    assert env["PHASE2_SUPABASE_TARGET"] == "wip"
    assert env["INGEST_SUIN"] == "tributario"
    assert env["INGEST_AUTO_EMBED"] == "1"
    assert env["INGEST_AUTO_PROMOTE"] == "0"
    assert env["LIA_INGEST_JOB_ID"] == "job-002"


def test_auto_promote_flag_dispatches_bash_wrapper(
    tmp_path: Path, _captured_subprocess: list[dict[str, Any]]
) -> None:
    ctrl._spawn_ingest_subprocess(
        tmp_path,
        suin_scope="",
        supabase_target="wip",
        job_id="job-003",
        auto_embed=True,
        auto_promote=True,
    )
    cmd = _captured_subprocess[0]["cmd"]
    assert cmd[:2] == ["bash", "scripts/ingest_run_full.sh"]
    env = _captured_subprocess[0]["env"]
    assert env["INGEST_AUTO_PROMOTE"] == "1"


def test_trace_payload_includes_auto_chain_flags(
    tmp_path: Path,
    _captured_subprocess: list[dict[str, Any]],
    _silence_trace: list[tuple[str, dict[str, Any]]],
) -> None:
    ctrl._spawn_ingest_subprocess(
        tmp_path,
        suin_scope="",
        supabase_target="wip",
        job_id="job-004",
        auto_embed=True,
        auto_promote=False,
    )
    start_events = [p for name, p in _silence_trace if name == "ingest.run.subprocess.start"]
    assert start_events, "expected subprocess.start trace event"
    payload = start_events[0]
    assert payload["auto_embed"] is True
    assert payload["auto_promote"] is False
    assert payload["job_id"] == "job-004"


def test_end_payload_carries_exit_code_and_log_path(
    tmp_path: Path,
    _captured_subprocess: list[dict[str, Any]],
    _silence_trace: list[tuple[str, dict[str, Any]]],
) -> None:
    result = ctrl._spawn_ingest_subprocess(
        tmp_path,
        suin_scope="",
        supabase_target="wip",
        job_id="job-005",
    )
    assert result["exit_code"] == 0
    assert result["log_relative_path"].startswith("artifacts/jobs/ingest_runs/")
    # end trace fires with the same payload shape
    end = [p for name, p in _silence_trace if name == "ingest.run.subprocess.end"]
    assert end and end[0]["exit_code"] == 0


def test_log_file_is_written_even_when_subprocess_short_circuits(
    tmp_path: Path, _captured_subprocess: list[dict[str, Any]]
) -> None:
    ctrl._spawn_ingest_subprocess(
        tmp_path,
        suin_scope="",
        supabase_target="wip",
        job_id="job-006",
    )
    log_dir = tmp_path / "artifacts/jobs/ingest_runs"
    assert log_dir.exists()
    log_files = list(log_dir.glob("ingest_*.log"))
    assert log_files, "expected an ingest log file to be written"
    contents = log_files[0].read_text(encoding="utf-8")
    assert contents.startswith("$ ")
