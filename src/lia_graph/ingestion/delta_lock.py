"""Concurrency guard for the additive-corpus-v1 delta path.

See ``docs/next/additive_corpusv1.md`` §4 Decision J (reviewer-revised:
J1 RPC + J2 row-based-lock hybrid). The row in ``ingest_delta_jobs`` is
the primary guard for long-running Python workers (which span many
PostgREST HTTP calls and therefore cannot hold a session-level advisory
lock). The xact-scoped RPC `acquire_ingest_delta_lock(text)` wraps
single-transaction ops like `promote_generation`.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

from ..instrumentation import emit_event
from . import delta_job_store


class DeltaLockBusy(RuntimeError):
    """Raised when another live job already holds the target lock.

    Carries the ``blocking_job_id`` so the admin UI (Phase 8) can offer a
    reattach action.
    """

    def __init__(self, *, target: str, blocking_job_id: str | None) -> None:
        super().__init__(
            f"lock target {target!r} busy (blocking job_id={blocking_job_id!r})"
        )
        self.target = target
        self.blocking_job_id = blocking_job_id


@dataclass
class JobLock:
    """A handle on an ``ingest_delta_jobs`` row held by the current worker."""

    client: Any
    job_id: str
    target: str
    delta_id: str | None = None
    _finalized: bool = False

    def heartbeat(self) -> None:
        delta_job_store.heartbeat(self.client, job_id=self.job_id)
        emit_event(
            "ingest.lock.job.heartbeat",
            {"job_id": self.job_id, "target": self.target},
        )

    def advance_stage(self, stage: str, progress_pct: int | None = None) -> None:
        delta_job_store.update_stage(
            self.client,
            job_id=self.job_id,
            stage=stage,
            progress_pct=progress_pct,
        )

    def cancel_requested(self) -> bool:
        row = delta_job_store.get_job(self.client, job_id=self.job_id)
        return bool(row.cancel_requested)

    def finalize(
        self,
        *,
        stage: str,
        error_class: str | None = None,
        error_message: str | None = None,
        report: dict | None = None,
    ) -> None:
        if self._finalized:
            return
        delta_job_store.finalize(
            self.client,
            job_id=self.job_id,
            stage=stage,
            error_class=error_class,
            error_message=error_message,
            report=report,
        )
        self._finalized = True
        emit_event(
            "ingest.lock.job.released",
            {
                "job_id": self.job_id,
                "target": self.target,
                "final_stage": stage,
            },
        )


def _is_unique_violation(exc: BaseException) -> bool:
    msg = str(exc)
    # supabase-py surfaces as a generic Exception; postgrest errors include
    # '23505' (unique_violation) or the index name. Be lax — any of these is
    # evidence we lost the race.
    markers = (
        "23505",
        "duplicate key",
        "idx_ingest_delta_jobs_live_target",
        "unique constraint",
    )
    return any(m in msg for m in markers)


def _find_blocking_job(client: Any, *, target: str) -> str | None:
    try:
        live = delta_job_store.list_live_jobs_by_target(client, lock_target=target)
    except Exception:  # noqa: BLE001
        return None
    if not live:
        return None
    return live[0].job_id


def acquire_job_lock(
    client: Any,
    *,
    target: str,
    job_id: str | None = None,
    created_by: str | None = None,
    delta_id: str | None = None,
) -> JobLock:
    """Attempt to acquire the row-based delta lock.

    Raises ``DeltaLockBusy`` (with blocking job_id attached) when another
    non-terminal row already holds ``target``. Returns a ``JobLock`` handle
    otherwise.
    """
    resolved_job_id = str(job_id or f"job_{uuid.uuid4().hex[:12]}").strip()
    if not resolved_job_id:
        raise ValueError("acquire_job_lock: job_id cannot be empty")
    try:
        delta_job_store.create_job(
            client,
            job_id=resolved_job_id,
            lock_target=target,
            stage="queued",
            delta_id=delta_id,
            created_by=created_by,
        )
    except Exception as exc:  # noqa: BLE001
        if _is_unique_violation(exc):
            blocking = _find_blocking_job(client, target=target)
            emit_event(
                "ingest.lock.job.busy",
                {"target": target, "blocking_job_id": blocking},
            )
            raise DeltaLockBusy(target=target, blocking_job_id=blocking) from exc
        raise
    emit_event(
        "ingest.lock.job.acquired",
        {
            "job_id": resolved_job_id,
            "target": target,
            "created_by": created_by,
            "delta_id": delta_id,
        },
    )
    return JobLock(
        client=client,
        job_id=resolved_job_id,
        target=target,
        delta_id=delta_id,
    )


@contextmanager
def held_job_lock(
    client: Any,
    *,
    target: str,
    job_id: str | None = None,
    created_by: str | None = None,
    delta_id: str | None = None,
) -> Iterator[JobLock]:
    """Context manager: acquire, yield, finalize (failed on exception)."""
    lock = acquire_job_lock(
        client,
        target=target,
        job_id=job_id,
        created_by=created_by,
        delta_id=delta_id,
    )
    try:
        yield lock
    except Exception as exc:  # noqa: BLE001
        if not lock._finalized:
            lock.finalize(
                stage="failed",
                error_class=exc.__class__.__name__,
                error_message=str(exc),
            )
        raise
    else:
        if not lock._finalized:
            lock.finalize(stage="completed")


def with_xact_lock(
    client: Any,
    *,
    target: str,
    rpc_name: str,
    params: dict,
) -> Any:
    """J1 helper — call an RPC that acquires ``pg_try_advisory_xact_lock``.

    The acquire helper is ``acquire_ingest_delta_lock(lock_target)`` from the
    Phase 1 migration; it's meant to be called inside another RPC body (e.g.
    ``promote_generation``). This wrapper just calls the named RPC and
    surfaces the result; the lock acquisition happens inside the RPC's
    transaction.
    """
    emit_event(
        "ingest.lock.xact.acquired",
        {"rpc_name": rpc_name, "lock_target": target},
    )
    try:
        resp = client.rpc(rpc_name, params or {}).execute()
        return getattr(resp, "data", None)
    except Exception as exc:  # noqa: BLE001
        emit_event(
            "ingest.lock.xact.busy",
            {"rpc_name": rpc_name, "lock_target": target, "error": str(exc)},
        )
        raise


def reap_stalled_jobs(
    client: Any,
    *,
    stall_window_minutes: int = 5,
) -> list[delta_job_store.DeltaJobRow]:
    """Re-export of the job-store janitor with a lock-facing trace emission."""
    reaped = delta_job_store.reap_stalled_jobs(
        client, stall_window_minutes=stall_window_minutes
    )
    for row in reaped:
        emit_event(
            "ingest.lock.job.reaped",
            {
                "job_id": row.job_id,
                "target": row.lock_target,
                "reason": "heartbeat_timeout",
            },
        )
    return reaped


__all__ = [
    "DeltaLockBusy",
    "JobLock",
    "acquire_job_lock",
    "held_job_lock",
    "reap_stalled_jobs",
    "with_xact_lock",
]
