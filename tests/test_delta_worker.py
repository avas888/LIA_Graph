"""Tests for the Phase 8 background worker ``delta_worker``."""

from __future__ import annotations

import threading
import time
from typing import Any
from unittest.mock import patch

import pytest

from lia_graph.ingestion import delta_job_store, delta_worker
from lia_graph.ingestion.delta_runtime import DeltaRunReport

# Reuse the fake Supabase client from the job-store test.
from tests.test_delta_job_store import _FakeClient


def _seed_job(client: Any, *, job_id: str, target: str = "production") -> None:
    delta_job_store.create_job(
        client, job_id=job_id, lock_target=target, stage="queued"
    )


def _join_or_timeout(thread: threading.Thread, *, timeout: float = 3.0) -> None:
    thread.join(timeout=timeout)
    if thread.is_alive():
        pytest.fail("delta_worker thread did not complete within timeout")


# ---- Fake materialize_delta ---------------------------------------------


def _fake_materialize(target: str = "ok", empty: bool = False, raise_exc: Exception | None = None):
    def _do(**kwargs: Any) -> DeltaRunReport:
        if raise_exc is not None:
            raise raise_exc
        return DeltaRunReport(
            delta_id="delta_fake_test",
            target=kwargs.get("supabase_target", target),
            generation_id=kwargs.get("generation_id", "gen_active_rolling"),
            dry_run=False,
            baseline_generation_id="gen_active_rolling",
            delta_summary={
                "delta_id": "delta_fake_test",
                "baseline_generation_id": "gen_active_rolling",
                "added": 0 if empty else 2,
                "modified": 0,
                "removed": 0,
                "unchanged": 0,
                "touched_total": 0 if empty else 2,
                "is_empty": empty,
            },
        )

    return _do


# ---- Tests --------------------------------------------------------------


# (a) Happy path — job transitions queued → parsing → supabase → falkor →
# finalize → completed. Report payload survives.
def test_worker_happy_path_finalizes_completed(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeClient()
    _seed_job(client, job_id="j_ok")
    monkeypatch.setattr(
        "lia_graph.ingestion.delta_worker._resolve_supabase_client",
        lambda deps, target: client,
    )
    monkeypatch.setattr(
        "lia_graph.ingestion.delta_runtime.materialize_delta",
        _fake_materialize(),
    )
    thread = delta_worker.submit_ingest_delta_worker(
        job_id="j_ok", target="production", deps={"corpus_dir": "/tmp", "artifacts_dir": "/tmp"}
    )
    _join_or_timeout(thread)
    row = delta_job_store.get_job(client, job_id="j_ok")
    assert row.is_terminal()
    assert row.stage == "completed"
    assert row.report_json is not None
    assert row.report_json.get("delta_id") == "delta_fake_test"


# (b) cancel_requested=true before parsing → stage=cancelled, no materialize call.
def test_worker_honors_cancel_before_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeClient()
    _seed_job(client, job_id="j_cancel")
    # Flip cancel_requested on the fresh row.
    for r in client.rows:
        if r["job_id"] == "j_cancel":
            r["cancel_requested"] = True
    monkeypatch.setattr(
        "lia_graph.ingestion.delta_worker._resolve_supabase_client",
        lambda deps, target: client,
    )
    called: list[int] = []

    def _fake_with_call(**kwargs: Any) -> DeltaRunReport:
        called.append(1)
        return _fake_materialize()(**kwargs)

    monkeypatch.setattr(
        "lia_graph.ingestion.delta_runtime.materialize_delta", _fake_with_call
    )
    thread = delta_worker.submit_ingest_delta_worker(
        job_id="j_cancel", target="production", deps={}
    )
    _join_or_timeout(thread)
    row = delta_job_store.get_job(client, job_id="j_cancel")
    assert row.stage == "cancelled"
    assert not called


# (c) Worker exception → job transitions to failed with error_class preserved.
def test_worker_finalizes_failed_on_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeClient()
    _seed_job(client, job_id="j_boom")
    monkeypatch.setattr(
        "lia_graph.ingestion.delta_worker._resolve_supabase_client",
        lambda deps, target: client,
    )
    monkeypatch.setattr(
        "lia_graph.ingestion.delta_runtime.materialize_delta",
        _fake_materialize(raise_exc=RuntimeError("simulated supabase 503")),
    )
    thread = delta_worker.submit_ingest_delta_worker(
        job_id="j_boom", target="production", deps={}
    )
    _join_or_timeout(thread)
    row = delta_job_store.get_job(client, job_id="j_boom")
    assert row.stage == "failed"
    assert row.error_class == "RuntimeError"
    assert row.error_message == "simulated supabase 503"


# (d) Worker never leaves the row in a non-terminal stage (guarantee).
def test_worker_never_leaves_nonterminal_stage(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeClient()
    _seed_job(client, job_id="j_always_terminal")
    monkeypatch.setattr(
        "lia_graph.ingestion.delta_worker._resolve_supabase_client",
        lambda deps, target: client,
    )
    monkeypatch.setattr(
        "lia_graph.ingestion.delta_runtime.materialize_delta",
        _fake_materialize(),
    )
    thread = delta_worker.submit_ingest_delta_worker(
        job_id="j_always_terminal", target="production", deps={}
    )
    _join_or_timeout(thread)
    row = delta_job_store.get_job(client, job_id="j_always_terminal")
    assert row.is_terminal()
