from __future__ import annotations

import threading
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from lia_graph.background_jobs import run_job_async
from lia_graph.jobs_store import JobRecord, load_job


def _wait_for_terminal_job(job_id: str, *, base_dir: Path, timeout_seconds: float = 2.0) -> JobRecord:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        record = load_job(job_id, base_dir=base_dir)
        if record is not None and record.status in {"completed", "failed", "cancelled"}:
            return record
        time.sleep(0.02)
    raise AssertionError(f"Job {job_id} did not reach a terminal state within {timeout_seconds:.1f}s")


def test_run_job_async_keeps_fire_and_forget_contract() -> None:
    seen: dict[str, str] = {}
    done = threading.Event()

    def _task(label: str, *, answer: str) -> None:
        seen["value"] = f"{label}:{answer}"
        done.set()

    thread = run_job_async(_task, "probe", answer="ok", job_name="lia-bg-test")

    assert isinstance(thread, threading.Thread)
    thread.join(timeout=1.0)
    assert done.is_set()
    assert seen == {"value": "probe:ok"}


def test_run_job_async_tracks_persisted_job_completion() -> None:
    with TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        job_id = run_job_async(
            job_type="chat_persistence",
            tenant_id="tenant_1",
            user_id="user_1",
            company_id="company_1",
            request_payload={"chat_run_id": "chat_run_1"},
            task=lambda: {"chat_run_id": "chat_run_1", "turn_count": 2},
            base_dir=base_dir,
        )

        assert isinstance(job_id, str)
        assert job_id

        record = _wait_for_terminal_job(job_id, base_dir=base_dir)

        assert record.status == "completed"
        assert record.request_payload == {"chat_run_id": "chat_run_1"}
        assert record.result_payload == {"chat_run_id": "chat_run_1", "turn_count": 2}
        assert record.attempts == 1
        assert record.completed_at


def test_run_job_async_tracks_persisted_job_failure() -> None:
    with TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)

        def _task() -> None:
            raise RuntimeError("boom")

        job_id = run_job_async(
            job_type="chat_persistence",
            request_payload={"chat_run_id": "chat_run_2"},
            task=_task,
            base_dir=base_dir,
        )

        assert isinstance(job_id, str)
        assert job_id

        record = _wait_for_terminal_job(job_id, base_dir=base_dir)

        assert record.status == "failed"
        assert record.result_payload == {}
        assert "boom" in record.error
        assert record.attempts == 1
        assert record.completed_at
