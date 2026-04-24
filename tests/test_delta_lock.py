"""Tests for ``lia_graph.ingestion.delta_lock``."""

from __future__ import annotations

import pytest

from lia_graph.ingestion import delta_lock

# Reuse the fake Supabase client from the job-store test.
from tests.test_delta_job_store import _FakeClient


# (a) first acquire_job_lock inserts the row; stage=queued.
def test_first_acquire_inserts_row() -> None:
    client = _FakeClient()
    lock = delta_lock.acquire_job_lock(
        client, target="production", job_id="job_a"
    )
    assert lock.job_id == "job_a"
    assert lock.target == "production"
    assert len(client.rows) == 1


# (b) second acquire against the same target raises DeltaLockBusy
# with blocking_job_id attached.
def test_second_acquire_raises_busy_with_blocking_job_id() -> None:
    client = _FakeClient()
    delta_lock.acquire_job_lock(
        client, target="production", job_id="job_first"
    )
    with pytest.raises(delta_lock.DeltaLockBusy) as exc_info:
        delta_lock.acquire_job_lock(
            client, target="production", job_id="job_second"
        )
    assert exc_info.value.blocking_job_id == "job_first"
    assert exc_info.value.target == "production"


# (c) finalizing the first job allows a subsequent acquisition.
def test_finalized_job_frees_target() -> None:
    client = _FakeClient()
    lock = delta_lock.acquire_job_lock(
        client, target="production", job_id="job_first"
    )
    lock.finalize(stage="completed")
    # Now a second acquire should succeed.
    lock2 = delta_lock.acquire_job_lock(
        client, target="production", job_id="job_second"
    )
    assert lock2.job_id == "job_second"


# (d) held_job_lock context manager finalizes failed on exception.
def test_held_job_lock_finalizes_failed_on_exception() -> None:
    client = _FakeClient()
    with pytest.raises(RuntimeError):
        with delta_lock.held_job_lock(
            client, target="production", job_id="job_X"
        ) as lock:
            raise RuntimeError("simulated failure")
    # The row should have been marked failed.
    rows = [r for r in client.rows if r["job_id"] == "job_X"]
    assert rows
    assert rows[0]["stage"] == "failed"
    assert rows[0].get("error_class") == "RuntimeError"


# (e) held_job_lock exit without error finalizes completed.
def test_held_job_lock_finalizes_completed_on_success() -> None:
    client = _FakeClient()
    with delta_lock.held_job_lock(
        client, target="production", job_id="job_Y"
    ) as lock:
        # simulate some work; heartbeat, stage advance
        lock.advance_stage("parsing", progress_pct=20)
        lock.heartbeat()
    rows = [r for r in client.rows if r["job_id"] == "job_Y"]
    assert rows[0]["stage"] == "completed"


# (f) cancel_requested surfaces through the JobLock.
def test_cancel_requested_reflects_row_state() -> None:
    client = _FakeClient()
    lock = delta_lock.acquire_job_lock(
        client, target="production", job_id="job_Z"
    )
    assert lock.cancel_requested() is False
    # Flip the flag on the underlying row.
    for r in client.rows:
        if r["job_id"] == "job_Z":
            r["cancel_requested"] = True
    assert lock.cancel_requested() is True
