from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

# Filesystem artifacts remain only for non-product dev/tests when Supabase is disabled.
_RUNTIME_DIR = Path("artifacts/runtime")
_RUNS_FILE = _RUNTIME_DIR / "pipeline_c_runs.jsonl"
_TIMELINE_DIR = _RUNTIME_DIR / "pipeline_c_timelines"

_LOCK = threading.RLock()
_RUNS: dict[str, dict[str, Any]] = {}
_TIMELINES: dict[str, list[dict[str, Any]]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _use_supabase() -> bool:
    from ..supabase_client import is_supabase_enabled

    return is_supabase_enabled()


def _normalize_supabase_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(row)
    for field in ("started_at", "ended_at", "created_at"):
        value = normalized.get(field)
        if hasattr(value, "isoformat"):
            normalized[field] = value.isoformat()
    return normalized


def _sb_upsert_run(row: dict[str, Any]) -> None:
    from ..supabase_client import get_supabase_client

    payload = {
        "run_id": row.get("run_id"),
        "trace_id": row.get("trace_id", ""),
        "chat_run_id": row.get("chat_run_id"),
        "status": row.get("status", "running"),
        "started_at": row.get("started_at"),
        "ended_at": row.get("ended_at"),
        "request_snapshot": row.get("request_snapshot") or {},
        "summary": row.get("summary") or {},
    }
    client = get_supabase_client()
    client.table("pipeline_c_runs").upsert(payload, on_conflict="run_id").execute()


def _sb_insert_timeline_event(run_id: str, event_index: int, event: dict[str, Any]) -> None:
    from ..supabase_client import get_supabase_client

    client = get_supabase_client()
    client.table("pipeline_c_run_events").upsert(
        {
            "run_id": run_id,
            "event_index": event_index,
            "event_payload": event,
        },
        on_conflict="run_id,event_index",
    ).execute()


def _sb_list_runs(limit: int) -> list[dict[str, Any]]:
    from ..supabase_client import get_supabase_client

    client = get_supabase_client()
    result = (
        client.table("pipeline_c_runs")
        .select("*")
        .order("started_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [_normalize_supabase_row(dict(row)) for row in list(result.data or [])]


def _sb_get_run(run_id: str) -> dict[str, Any] | None:
    from ..supabase_client import get_supabase_client

    client = get_supabase_client()
    result = (
        client.table("pipeline_c_runs")
        .select("*")
        .eq("run_id", run_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    return _normalize_supabase_row(dict(result.data[0]))


def _sb_get_timeline(run_id: str) -> list[dict[str, Any]]:
    from ..supabase_client import get_supabase_client

    client = get_supabase_client()
    result = (
        client.table("pipeline_c_run_events")
        .select("event_payload, event_index")
        .eq("run_id", run_id)
        .order("event_index")
        .execute()
    )
    events: list[dict[str, Any]] = []
    for row in list(result.data or []):
        payload = dict(row.get("event_payload") or {})
        if payload:
            events.append(payload)
    return events


def _append_run_row(row: dict[str, Any]) -> None:
    if _use_supabase():
        _sb_upsert_run(row)
        return
    _RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    with _RUNS_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _save_timeline(run_id: str, events: list[dict[str, Any]]) -> None:
    if _use_supabase():
        if not events:
            return
        _sb_insert_timeline_event(run_id, len(events) - 1, events[-1])
        return
    _TIMELINE_DIR.mkdir(parents=True, exist_ok=True)
    (_TIMELINE_DIR / f"{run_id}.json").write_text(
        json.dumps({"run_id": run_id, "events": events}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def start_run(*, trace_id: str, request_snapshot: dict[str, Any], chat_run_id: str | None = None) -> str:
    run_id = f"pc_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
    row = {
        "run_id": run_id,
        "trace_id": trace_id,
        "chat_run_id": str(chat_run_id or "").strip() or None,
        "status": "running",
        "started_at": _now_iso(),
        "ended_at": None,
        "request_snapshot": dict(request_snapshot),
        "summary": {},
    }
    with _LOCK:
        _RUNS[run_id] = row
        _TIMELINES[run_id] = []
    _append_run_row({**row, "event": "started"})
    return run_id


def record_stage(
    run_id: str,
    *,
    stage: str,
    status: str,
    details: dict[str, Any] | None = None,
    duration_ms: float | None = None,
) -> None:
    event = {
        "at": _now_iso(),
        "stage": stage,
        "status": status,
        "details": dict(details or {}),
        "duration_ms": round(float(duration_ms or 0.0), 2),
    }
    with _LOCK:
        _TIMELINES.setdefault(run_id, []).append(event)
        events = list(_TIMELINES.get(run_id, []))
    _save_timeline(run_id, events)


def finish_run(
    run_id: str,
    *,
    status: str,
    summary: dict[str, Any],
) -> None:
    with _LOCK:
        row = _RUNS.get(run_id)
        if row is None:
            return
        row["status"] = status
        row["ended_at"] = _now_iso()
        row["summary"] = dict(summary)
        snapshot = dict(row)
        timeline = list(_TIMELINES.get(run_id, []))
    _append_run_row({**snapshot, "event": "finished"})
    _save_timeline(run_id, timeline)


def list_runs(*, limit: int = 50) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 200))
    if _use_supabase():
        return _sb_list_runs(limit)
    with _LOCK:
        rows = list(_RUNS.values())
    rows.sort(key=lambda item: str(item.get("started_at", "")), reverse=True)
    return [dict(item) for item in rows[:limit]]


def get_run(run_id: str) -> dict[str, Any] | None:
    if _use_supabase():
        return _sb_get_run(run_id)
    with _LOCK:
        row = _RUNS.get(run_id)
    if row is None:
        return None
    return dict(row)


def get_timeline(run_id: str) -> list[dict[str, Any]]:
    if _use_supabase():
        return _sb_get_timeline(run_id)
    with _LOCK:
        events = list(_TIMELINES.get(run_id, []))
    if events:
        return events
    path = _TIMELINE_DIR / f"{run_id}.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    rows = payload.get("events", [])
    if not isinstance(rows, list):
        return []
    return [dict(item) for item in rows if isinstance(item, dict)]
