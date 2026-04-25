"""CRUD helpers for the ``ingest_delta_jobs`` table.

See ``docs/done/next/additive_corpusv1.md`` §4 Decision J2 + §5 Phase 7. The table
itself is the lock (partial-unique-index on live rows); this module is the
Python-side projection of that lock + the surface the Phase 8 admin UI
reads to render progress.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping


TABLE_NAME = "ingest_delta_jobs"

LIVE_STAGES = frozenset({"queued", "preview", "parsing", "supabase", "falkor", "finalize"})
TERMINAL_STAGES = frozenset({"completed", "failed", "cancelled"})
ALL_STAGES = LIVE_STAGES | TERMINAL_STAGES


@dataclass(frozen=True)
class DeltaJobRow:
    job_id: str
    lock_target: str
    stage: str
    delta_id: str | None
    progress_pct: int
    started_at: str | None
    last_heartbeat_at: str | None
    completed_at: str | None
    created_by: str | None
    cancel_requested: bool
    error_class: str | None
    error_message: str | None
    report_json: Mapping[str, Any] | None

    def is_terminal(self) -> bool:
        return self.stage in TERMINAL_STAGES


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _row_to_dataclass(row: Mapping[str, Any]) -> DeltaJobRow:
    return DeltaJobRow(
        job_id=str(row.get("job_id") or ""),
        lock_target=str(row.get("lock_target") or ""),
        stage=str(row.get("stage") or ""),
        delta_id=_optional_str(row.get("delta_id")),
        progress_pct=int(row.get("progress_pct") or 0),
        started_at=_optional_str(row.get("started_at")),
        last_heartbeat_at=_optional_str(row.get("last_heartbeat_at")),
        completed_at=_optional_str(row.get("completed_at")),
        created_by=_optional_str(row.get("created_by")),
        cancel_requested=bool(row.get("cancel_requested") or False),
        error_class=_optional_str(row.get("error_class")),
        error_message=_optional_str(row.get("error_message")),
        report_json=row.get("report_json") if isinstance(row.get("report_json"), Mapping) else None,
    )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def create_job(
    client: Any,
    *,
    job_id: str,
    lock_target: str,
    stage: str = "queued",
    delta_id: str | None = None,
    created_by: str | None = None,
) -> DeltaJobRow:
    """Insert a new ingest_delta_jobs row.

    Raises whatever the underlying PostgREST client raises on unique-index
    violations (partial unique index on `lock_target` where stage non-terminal
    is what makes this function the J2 lock).
    """
    if stage not in ALL_STAGES:
        raise ValueError(f"stage={stage!r} not in allowed stages {sorted(ALL_STAGES)}")
    payload = {
        "job_id": job_id,
        "lock_target": lock_target,
        "stage": stage,
        "delta_id": delta_id,
        "created_by": created_by,
        "progress_pct": 0,
        "cancel_requested": False,
        "started_at": _now_iso(),
        "last_heartbeat_at": _now_iso(),
    }
    client.table(TABLE_NAME).insert(payload).execute()
    return get_job(client, job_id=job_id)


def get_job(client: Any, *, job_id: str) -> DeltaJobRow:
    resp = (
        client.table(TABLE_NAME)
        .select("*")
        .eq("job_id", job_id)
        .limit(1)
        .execute()
    )
    rows = list(getattr(resp, "data", None) or [])
    if not rows:
        raise LookupError(f"ingest_delta_jobs row not found: job_id={job_id!r}")
    return _row_to_dataclass(rows[0])


def list_live_jobs_by_target(
    client: Any,
    *,
    lock_target: str,
) -> list[DeltaJobRow]:
    """Return non-terminal rows for a lock_target."""
    resp = (
        client.table(TABLE_NAME)
        .select("*")
        .eq("lock_target", lock_target)
        .not_.in_("stage", list(TERMINAL_STAGES))
        .order("started_at")
        .execute()
    )
    rows = list(getattr(resp, "data", None) or [])
    return [_row_to_dataclass(r) for r in rows]


def request_cancel(client: Any, *, job_id: str) -> DeltaJobRow:
    client.table(TABLE_NAME).update(
        {"cancel_requested": True}
    ).eq("job_id", job_id).execute()
    return get_job(client, job_id=job_id)


def update_stage(
    client: Any,
    *,
    job_id: str,
    stage: str,
    progress_pct: int | None = None,
    heartbeat: bool = True,
) -> DeltaJobRow:
    if stage not in ALL_STAGES:
        raise ValueError(f"stage={stage!r} not in allowed stages")
    payload: dict[str, Any] = {"stage": stage}
    if progress_pct is not None:
        payload["progress_pct"] = int(progress_pct)
    if heartbeat:
        payload["last_heartbeat_at"] = _now_iso()
    if stage in TERMINAL_STAGES:
        payload["completed_at"] = _now_iso()
    client.table(TABLE_NAME).update(payload).eq("job_id", job_id).execute()
    return get_job(client, job_id=job_id)


def heartbeat(client: Any, *, job_id: str) -> None:
    client.table(TABLE_NAME).update(
        {"last_heartbeat_at": _now_iso()}
    ).eq("job_id", job_id).execute()


def finalize(
    client: Any,
    *,
    job_id: str,
    stage: str,
    error_class: str | None = None,
    error_message: str | None = None,
    report: Mapping[str, Any] | None = None,
) -> DeltaJobRow:
    if stage not in TERMINAL_STAGES:
        raise ValueError(
            f"finalize stage={stage!r} must be terminal ({sorted(TERMINAL_STAGES)})"
        )
    payload: dict[str, Any] = {
        "stage": stage,
        "completed_at": _now_iso(),
        "last_heartbeat_at": _now_iso(),
    }
    if error_class is not None:
        payload["error_class"] = str(error_class)
    if error_message is not None:
        payload["error_message"] = str(error_message)
    if report is not None:
        payload["report_json"] = dict(report)
    client.table(TABLE_NAME).update(payload).eq("job_id", job_id).execute()
    return get_job(client, job_id=job_id)


def reap_stalled_jobs(
    client: Any,
    *,
    stall_window_minutes: int = 5,
) -> list[DeltaJobRow]:
    """Flip live rows whose heartbeat is older than the window to failed.

    Returns the rows that were flipped.
    """
    # PostgREST uses ISO-8601; compute the cutoff client-side.
    from datetime import timedelta

    cutoff = datetime.now(tz=timezone.utc) - timedelta(minutes=stall_window_minutes)
    cutoff_iso = cutoff.isoformat()
    # Fetch candidates first so we can return them.
    resp = (
        client.table(TABLE_NAME)
        .select("*")
        .not_.in_("stage", list(TERMINAL_STAGES))
        .lt("last_heartbeat_at", cutoff_iso)
        .execute()
    )
    stalled = list(getattr(resp, "data", None) or [])
    if not stalled:
        return []
    reaped: list[DeltaJobRow] = []
    for raw in stalled:
        job_id = str(raw.get("job_id") or "")
        if not job_id:
            continue
        client.table(TABLE_NAME).update(
            {
                "stage": "failed",
                "error_class": "heartbeat_timeout",
                "error_message": (
                    f"No heartbeat for >{stall_window_minutes} minutes."
                ),
                "completed_at": _now_iso(),
            }
        ).eq("job_id", job_id).execute()
        reaped.append(_row_to_dataclass(raw))
    return reaped


__all__ = [
    "ALL_STAGES",
    "DeltaJobRow",
    "LIVE_STAGES",
    "TABLE_NAME",
    "TERMINAL_STAGES",
    "create_job",
    "finalize",
    "get_job",
    "heartbeat",
    "list_live_jobs_by_target",
    "reap_stalled_jobs",
    "request_cancel",
    "update_stage",
]
