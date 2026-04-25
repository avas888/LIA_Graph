"""Background worker that applies an additive-corpus-v1 delta.

Phase 8 §8.B of ``docs/done/next/additive_corpusv1.md``. Reads the
``ingest_delta_jobs`` row the HTTP controller created, runs the full
``materialize_delta`` pass against live Supabase + Falkor, heartbeats the
row every stage boundary, respects ``cancel_requested``, and finalizes
the row to a terminal stage no matter what path execution takes.

Integration:

    from .ingestion.delta_worker import submit_ingest_delta_worker

    def submit_worker(*, job_id, target, deps):
        submit_ingest_delta_worker(job_id=job_id, target=target, deps=deps)

    dispatch_deps["submit_worker"] = submit_worker

The worker is a ``threading.Thread`` daemon — appropriate for the
single-process CLI + UI server topology. For Railway / horizontal scale
it would become a tasks-queue consumer instead; that is a separate
follow-up, out of scope for v1.
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any

from ..instrumentation import emit_event
from . import delta_job_store


_log = logging.getLogger(__name__)


def _heartbeat_every(stop_event: threading.Event, job_id: str, client: Any, interval: float = 15.0) -> None:
    while not stop_event.wait(interval):
        try:
            delta_job_store.heartbeat(client, job_id=job_id)
            emit_event(
                "ingest.delta.worker.heartbeat",
                {"job_id": job_id},
            )
        except Exception:  # noqa: BLE001 — never let the heartbeat loop crash the worker
            _log.debug("delta_worker: heartbeat failed for job %s", job_id, exc_info=True)


def _check_cancel(client: Any, *, job_id: str, at_stage: str) -> bool:
    try:
        row = delta_job_store.get_job(client, job_id=job_id)
    except Exception:  # noqa: BLE001
        return False
    if row.cancel_requested:
        emit_event(
            "ingest.delta.worker.cancel_observed",
            {"job_id": job_id, "at_stage": at_stage},
        )
        return True
    return False


def _resolve_supabase_client(deps: dict[str, Any], target: str) -> Any:
    client = deps.get("supabase_client")
    if client is not None:
        return client
    from ..supabase_client import create_supabase_client_for_target

    return create_supabase_client_for_target(target)


def _run_delta_worker(
    *,
    job_id: str,
    target: str,
    deps: dict[str, Any],
) -> None:
    """Worker body. Runs on a daemon thread."""
    client = _resolve_supabase_client(deps, target)
    emit_event(
        "ingest.delta.worker.start",
        {"job_id": job_id, "target": target},
    )

    # Stage transition: queued → parsing. If the user cancelled already, finalize
    # immediately.
    if _check_cancel(client, job_id=job_id, at_stage="queued"):
        delta_job_store.finalize(
            client,
            job_id=job_id,
            stage="cancelled",
            error_message="cancel requested before parsing started",
        )
        emit_event("ingest.delta.worker.done", {"job_id": job_id, "outcome": "cancelled"})
        return

    stop_heartbeat = threading.Event()
    hb_thread = threading.Thread(
        target=_heartbeat_every,
        args=(stop_heartbeat, job_id, client),
        name=f"delta-worker-heartbeat-{job_id}",
        daemon=True,
    )
    hb_thread.start()

    try:
        # Stage: parsing.
        delta_job_store.update_stage(client, job_id=job_id, stage="parsing", progress_pct=10)
        emit_event("ingest.delta.worker.stage", {"job_id": job_id, "stage": "parsing"})

        if _check_cancel(client, job_id=job_id, at_stage="parsing"):
            delta_job_store.finalize(
                client, job_id=job_id, stage="cancelled",
                error_message="cancel requested at parsing boundary",
            )
            emit_event("ingest.delta.worker.done", {"job_id": job_id, "outcome": "cancelled"})
            return

        # The rest of the pipeline is inside `materialize_delta`. We drive
        # it synchronously and advance stage markers around it.
        from .delta_runtime import materialize_delta

        t0 = time.monotonic()
        delta_job_store.update_stage(client, job_id=job_id, stage="supabase", progress_pct=40)
        emit_event("ingest.delta.worker.stage", {"job_id": job_id, "stage": "supabase"})

        report = materialize_delta(
            corpus_dir=deps.get("corpus_dir") or Path("knowledge_base"),
            artifacts_dir=deps.get("artifacts_dir") or Path("artifacts"),
            pattern=str(deps.get("pattern") or "**/*.md"),
            supabase_target=target,
            generation_id=str(deps.get("generation_id") or "gen_active_rolling"),
            delta_id=None,
            dry_run=False,
            execute_load=bool(deps.get("execute_load", True)),
            strict_falkordb=bool(deps.get("strict_falkordb", False)),
            strict_parity=bool(deps.get("strict_parity", False)),
            supabase_client=client,
            graph_client=deps.get("graph_client"),
            skip_llm=bool(deps.get("skip_llm", False)),
            rate_limit_rpm=int(deps.get("rate_limit_rpm", 300)),
            classifier_workers=deps.get("classifier_workers"),
        )

        if _check_cancel(client, job_id=job_id, at_stage="finalize"):
            delta_job_store.finalize(
                client, job_id=job_id, stage="cancelled",
                error_message="cancel requested between apply and finalize",
                report=report.to_dict(),
            )
            emit_event("ingest.delta.worker.done", {"job_id": job_id, "outcome": "cancelled"})
            return

        delta_job_store.update_stage(client, job_id=job_id, stage="falkor", progress_pct=80)
        emit_event("ingest.delta.worker.stage", {"job_id": job_id, "stage": "falkor"})

        # Final transition to completed.
        delta_job_store.update_stage(client, job_id=job_id, stage="finalize", progress_pct=95)
        emit_event("ingest.delta.worker.stage", {"job_id": job_id, "stage": "finalize"})
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        delta_job_store.finalize(
            client,
            job_id=job_id,
            stage="completed",
            report=report.to_dict() | {"elapsed_ms": elapsed_ms},
        )
        emit_event(
            "ingest.delta.worker.done",
            {"job_id": job_id, "outcome": "completed", "elapsed_ms": elapsed_ms},
        )
    except Exception as exc:  # noqa: BLE001
        _log.exception("delta_worker job_id=%s failed", job_id)
        try:
            delta_job_store.finalize(
                client,
                job_id=job_id,
                stage="failed",
                error_class=exc.__class__.__name__,
                error_message=str(exc),
            )
        except Exception:  # noqa: BLE001
            _log.exception("delta_worker: finalize-on-failure also failed for %s", job_id)
        emit_event(
            "ingest.delta.worker.failed",
            {
                "job_id": job_id,
                "error_class": exc.__class__.__name__,
                "error_message": str(exc),
            },
        )
    finally:
        stop_heartbeat.set()


def submit_ingest_delta_worker(
    *,
    job_id: str,
    target: str,
    deps: dict[str, Any],
) -> threading.Thread:
    """Spawn the worker on a daemon thread. Returns the thread so tests can join."""
    thread = threading.Thread(
        target=_run_delta_worker,
        kwargs={"job_id": job_id, "target": target, "deps": dict(deps)},
        name=f"lia-ingest-delta-{job_id}",
        daemon=True,
    )
    thread.start()
    return thread


__all__ = [
    "submit_ingest_delta_worker",
]
