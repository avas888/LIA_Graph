"""Small async helpers for post-response background work."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .jobs_store import DEFAULT_JOBS_DIR, create_job, update_job

_log = logging.getLogger(__name__)


def _normalize_result_payload(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        return dict(result)
    if result is None:
        return {}
    return {"value": result}


def _start_daemon_thread(*, target: Callable[[], None], job_name: str) -> threading.Thread:
    thread = threading.Thread(
        target=target,
        name=job_name,
        daemon=True,
    )
    thread.start()
    return thread


def run_job_async(
    func: Callable[..., Any] | None = None,
    /,
    *args: Any,
    job_name: str | None = None,
    **kwargs: Any,
) -> threading.Thread | str:
    """Run a background job on a daemon thread.

    Supports both the legacy fire-and-forget form and the persisted job form
    used by chat persistence scheduling.
    """

    tracked_task = kwargs.pop("task", None)
    if func is not None and tracked_task is not None:
        raise TypeError("run_job_async() received both `func` and `task`")
    if func is None and tracked_task is None:
        raise TypeError("run_job_async() missing required callable")

    if tracked_task is not None:
        if args:
            raise TypeError("run_job_async() tracked job mode does not accept positional args")
        if not callable(tracked_task):
            raise TypeError("run_job_async() `task` must be callable")
        job_type = str(kwargs.pop("job_type", "")).strip() or "generic"
        tenant_id = str(kwargs.pop("tenant_id", "")).strip()
        user_id = str(kwargs.pop("user_id", "")).strip()
        company_id = str(kwargs.pop("company_id", "")).strip()
        request_payload = dict(kwargs.pop("request_payload", {}) or {})
        base_dir = Path(kwargs.pop("base_dir", DEFAULT_JOBS_DIR))
        tracked_job_name = str(kwargs.pop("job_name", job_name) or f"lia-bg-{job_type}")
        pass_job_id = bool(kwargs.pop("pass_job_id", False))
        if kwargs:
            unexpected = ", ".join(sorted(kwargs))
            raise TypeError(f"run_job_async() got unexpected keyword arguments: {unexpected}")

        record = create_job(
            job_type=job_type,
            tenant_id=tenant_id,
            user_id=user_id,
            company_id=company_id,
            request_payload=request_payload,
            base_dir=base_dir,
        )

        def _tracked_runner() -> None:
            update_job(
                record.job_id,
                status="running",
                attempts=1,
                base_dir=base_dir,
            )
            try:
                if pass_job_id:
                    result = tracked_task(job_id=record.job_id)
                else:
                    result = tracked_task()
            except Exception as exc:  # noqa: BLE001
                update_job(
                    record.job_id,
                    status="failed",
                    error=str(exc),
                    attempts=1,
                    base_dir=base_dir,
                )
                _log.exception("Background job failed: %s", tracked_job_name)
                return
            update_job(
                record.job_id,
                status="completed",
                result_payload=_normalize_result_payload(result),
                attempts=1,
                base_dir=base_dir,
            )

        try:
            _start_daemon_thread(target=_tracked_runner, job_name=tracked_job_name)
        except Exception:
            update_job(
                record.job_id,
                status="failed",
                error="Failed to start background job thread",
                attempts=1,
                base_dir=base_dir,
            )
            raise
        return record.job_id

    def _runner() -> None:
        try:
            func(*args, **kwargs)
        except Exception:  # noqa: BLE001
            _log.exception("Background job failed: %s", job_name or getattr(func, "__name__", "job"))

    return _start_daemon_thread(
        target=_runner,
        job_name=job_name or f"lia-bg-{getattr(func, '__name__', 'job')}",
    )
