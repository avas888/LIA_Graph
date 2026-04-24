"""Tests for ``scripts/monitoring/ingest_heartbeat.py``.

Focused on the pieces that matter for correctness:

- ``ChainState.from_file`` — robust parse of ``artifacts/backfill_state.json``
  (v3 Phase 2 adds the chain-mode heartbeat).
- ``render()`` — when ``chain=`` is supplied, the output prepends two rows
  (Chain progress + Total ETA) so the operator sees chain state at a glance.

We deliberately skip the cloud-probe helpers (``supabase_counts``,
``falkor_counts``) — they're integration points tested by hand at the cron
level. These pure-function tests fence the ingestionfix_v3 §5 Phase 2
acceptance on the chain-state-enrichment surface.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "monitoring"
    / "ingest_heartbeat.py"
)
_spec = importlib.util.spec_from_file_location("ingest_heartbeat", _SCRIPT)
assert _spec is not None and _spec.loader is not None
heartbeat = importlib.util.module_from_spec(_spec)
sys.modules["ingest_heartbeat"] = heartbeat
_spec.loader.exec_module(heartbeat)  # type: ignore[union-attr]


# ── ChainState parse ─────────────────────────────────────────────────


def test_chain_state_missing_file_returns_none(tmp_path: Path) -> None:
    assert heartbeat.ChainState.from_file(tmp_path / "does_not_exist.json") is None


def test_chain_state_malformed_json_returns_none(tmp_path: Path) -> None:
    p = tmp_path / "backfill_state.json"
    p.write_text("{not: json", encoding="utf-8")
    assert heartbeat.ChainState.from_file(p) is None


def test_chain_state_parses_done_and_current(tmp_path: Path) -> None:
    p = tmp_path / "backfill_state.json"
    p.write_text(
        json.dumps(
            {
                "batches_planned": 8,
                "done_batches_log": [
                    {"batch": 1, "wall_minutes": 10.0, "status": "ok"},
                    {"batch": 2, "wall_minutes": 12.0, "status": "ok"},
                    {"batch": 3, "wall_minutes": 14.0, "status": "ok"},
                ],
                "current_batch": {
                    "batch": 4,
                    "started_at": "2026-04-23T20:15:00Z",
                },
            }
        ),
        encoding="utf-8",
    )
    state = heartbeat.ChainState.from_file(p)
    assert state is not None
    assert state.batches_planned == 8
    assert state.done_count == 3
    assert state.done_wall_minutes == 36.0
    assert state.current_batch == 4
    assert state.current_started_at == "2026-04-23T20:15:00Z"
    # avg = 36 / 3 = 12; remaining = 8 - 3 = 5; est = 60
    assert state.avg_wall_minutes == 12.0
    assert state.est_remaining_minutes == 60.0


def test_chain_state_empty_log_yields_zero_eta(tmp_path: Path) -> None:
    p = tmp_path / "backfill_state.json"
    p.write_text(
        json.dumps({"batches_planned": 8, "done_batches_log": []}),
        encoding="utf-8",
    )
    state = heartbeat.ChainState.from_file(p)
    assert state is not None
    assert state.done_count == 0
    assert state.avg_wall_minutes == 0.0
    assert state.est_remaining_minutes == 0.0


# ── Render enrichment ────────────────────────────────────────────────


def _stub_stats() -> "heartbeat.EventStats":
    return heartbeat.EventStats(done=5, last_ts="2026-04-23T20:10:00Z")


def _stub_process() -> "heartbeat.ProcessInfo":
    return heartbeat.ProcessInfo(pid="12345", etime="00:05:00", etime_seconds=300)


def test_render_without_chain_has_no_chain_rows() -> None:
    out = heartbeat.render(
        title="Test",
        delta_id="delta_x",
        total=10,
        stats=_stub_stats(),
        process=_stub_process(),
        phase="classifying",
        supa=None,
        falk=None,
        base_supa_docs=0,
        base_supa_chunks=0,
        base_falk_article=0,
        base_falk_topic=0,
        base_falk_tema=0,
        base_falk_practica=0,
    )
    assert "Chain progress" not in out
    assert "Total ETA" not in out


def test_render_with_chain_state_prepends_chain_rows() -> None:
    chain = heartbeat.ChainState(
        batches_planned=8,
        done_count=3,
        done_wall_minutes=36.0,
        current_batch=4,
        current_started_at="2026-04-23T20:15:00Z",
        avg_wall_minutes=12.0,
        est_remaining_minutes=60.0,
    )
    out = heartbeat.render(
        title="Test",
        delta_id="delta_x",
        total=10,
        stats=_stub_stats(),
        process=_stub_process(),
        phase="classifying",
        supa=None,
        falk=None,
        base_supa_docs=0,
        base_supa_chunks=0,
        base_falk_article=0,
        base_falk_topic=0,
        base_falk_tema=0,
        base_falk_practica=0,
        chain=chain,
    )
    assert "Chain progress" in out
    assert "3 / 8" in out
    assert "batch 4" in out
    assert "12.0 min/batch" in out
    assert "Total ETA" in out
    assert "60.0 min" in out


def test_render_with_chain_state_empty_log_shows_dash_eta() -> None:
    chain = heartbeat.ChainState(
        batches_planned=8,
        done_count=0,
        done_wall_minutes=0.0,
        current_batch=1,
        current_started_at="2026-04-23T20:15:00Z",
        avg_wall_minutes=0.0,
        est_remaining_minutes=0.0,
    )
    out = heartbeat.render(
        title="Test",
        delta_id="delta_x",
        total=10,
        stats=_stub_stats(),
        process=_stub_process(),
        phase="classifying",
        supa=None,
        falk=None,
        base_supa_docs=0,
        base_supa_chunks=0,
        base_falk_article=0,
        base_falk_topic=0,
        base_falk_tema=0,
        base_falk_practica=0,
        chain=chain,
    )
    assert "0 / 8" in out
    # Total ETA row is still rendered, but shows a dash instead of a number.
    assert "Total ETA" in out
    assert "no completed batches yet" in out
