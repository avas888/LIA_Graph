from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .instrumentation import normalize_token_usage

DEFAULT_CHAT_SESSION_METRICS_PATH = Path("artifacts/runtime/chat_session_metrics.json")
_LOCK = threading.RLock()
_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_.:\-]{1,128}$")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _empty_usage() -> dict[str, int]:
    return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}


def _sanitize_session_id(session_id: str) -> str:
    value = str(session_id or "").strip()
    if not value:
        raise ValueError("`session_id` es requerido.")
    if not _SESSION_ID_RE.match(value):
        raise ValueError("`session_id` invalido.")
    return value


def _use_supabase(path: Path) -> bool:
    from .supabase_client import is_supabase_enabled, matches_default_storage_path

    if not matches_default_storage_path(path, DEFAULT_CHAT_SESSION_METRICS_PATH):
        return False
    return is_supabase_enabled()


def _coerce_usage(usage: dict[str, Any] | None) -> dict[str, int]:
    normalized = normalize_token_usage(usage)
    return {
        "input_tokens": max(0, int(normalized.get("input_tokens") or 0)),
        "output_tokens": max(0, int(normalized.get("output_tokens") or 0)),
        "total_tokens": max(0, int(normalized.get("total_tokens") or 0)),
    }


def _read_store(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": "2026-03-04.1", "updated_at": None, "sessions": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": "2026-03-04.1", "updated_at": None, "sessions": {}}
    if not isinstance(payload, dict):
        return {"version": "2026-03-04.1", "updated_at": None, "sessions": {}}
    sessions = payload.get("sessions")
    if not isinstance(sessions, dict):
        sessions = {}
    return {
        "version": str(payload.get("version", "2026-03-04.1")),
        "updated_at": payload.get("updated_at"),
        "sessions": sessions,
    }


def _write_store(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def _default_session_row(session_id: str) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "turn_count": 0,
        "token_usage_total": _empty_usage(),
        "llm_token_usage_total": _empty_usage(),
        "last_trace_id": None,
        "last_run_id": None,
        "updated_at": None,
    }


def _session_snapshot(row: dict[str, Any], session_id: str) -> dict[str, Any]:
    usage_total = _coerce_usage(dict(row.get("token_usage_total") or {}))
    llm_usage_total = _coerce_usage(dict(row.get("llm_token_usage_total") or {}))
    return {
        "session_id": session_id,
        "turn_count": max(0, int(row.get("turn_count") or 0)),
        "token_usage_total": usage_total,
        "llm_token_usage_total": llm_usage_total,
        "last_trace_id": row.get("last_trace_id"),
        "last_run_id": row.get("last_run_id"),
        "updated_at": row.get("updated_at"),
    }


def _normalize_db_row(row: dict[str, Any], session_id: str) -> dict[str, Any]:
    updated_at = row.get("updated_at")
    if hasattr(updated_at, "isoformat"):
        updated_at = updated_at.isoformat()
    return _session_snapshot(
        {
            "turn_count": row.get("turn_count", 0),
            "token_usage_total": row.get("token_usage_total") or {},
            "llm_token_usage_total": row.get("llm_token_usage_total") or {},
            "last_trace_id": row.get("last_trace_id"),
            "last_run_id": row.get("last_run_id"),
            "updated_at": updated_at,
        },
        session_id,
    )


def _sb_get_or_create_session_metrics(session_id: str) -> dict[str, Any]:
    from .supabase_client import get_supabase_client

    client = get_supabase_client()
    result = (
        client.table("chat_session_metrics")
        .select("*")
        .eq("session_id", session_id)
        .limit(1)
        .execute()
    )
    if result.data:
        return _normalize_db_row(dict(result.data[0]), session_id)

    row = _default_session_row(session_id)
    client.table("chat_session_metrics").upsert(
        {
            "session_id": session_id,
            "turn_count": row["turn_count"],
            "token_usage_total": row["token_usage_total"],
            "llm_token_usage_total": row["llm_token_usage_total"],
            "last_trace_id": row["last_trace_id"],
            "last_run_id": row["last_run_id"],
        },
        on_conflict="session_id",
    ).execute()
    return _session_snapshot(row, session_id)


def _sb_update_session_metrics(
    *,
    session_id: str,
    turn_usage: dict[str, Any] | None,
    llm_usage: dict[str, Any] | None,
    trace_id: str | None,
    run_id: str | None,
) -> dict[str, Any]:
    from .supabase_client import get_supabase_client

    current = _sb_get_or_create_session_metrics(session_id)
    turn = _coerce_usage(turn_usage)
    llm = _coerce_usage(llm_usage)
    payload = {
        "session_id": session_id,
        "turn_count": max(0, int(current.get("turn_count") or 0)) + 1,
        "token_usage_total": {
            "input_tokens": int((current.get("token_usage_total") or {}).get("input_tokens") or 0) + turn["input_tokens"],
            "output_tokens": int((current.get("token_usage_total") or {}).get("output_tokens") or 0) + turn["output_tokens"],
            "total_tokens": int((current.get("token_usage_total") or {}).get("total_tokens") or 0) + turn["total_tokens"],
        },
        "llm_token_usage_total": {
            "input_tokens": int((current.get("llm_token_usage_total") or {}).get("input_tokens") or 0) + llm["input_tokens"],
            "output_tokens": int((current.get("llm_token_usage_total") or {}).get("output_tokens") or 0) + llm["output_tokens"],
            "total_tokens": int((current.get("llm_token_usage_total") or {}).get("total_tokens") or 0) + llm["total_tokens"],
        },
        "last_trace_id": str(trace_id).strip() if trace_id else current.get("last_trace_id"),
        "last_run_id": str(run_id).strip() if run_id else current.get("last_run_id"),
        "updated_at": _utc_now_iso(),
    }
    client = get_supabase_client()
    client.table("chat_session_metrics").upsert(payload, on_conflict="session_id").execute()
    return _session_snapshot(payload, session_id)


def get_chat_session_metrics(*, session_id: str, path: Path = DEFAULT_CHAT_SESSION_METRICS_PATH) -> dict[str, Any]:
    safe_session_id = _sanitize_session_id(session_id)
    if _use_supabase(path):
        return _sb_get_or_create_session_metrics(safe_session_id)
    with _LOCK:
        store = _read_store(path)
        sessions = dict(store.get("sessions") or {})
        row = sessions.get(safe_session_id)
        if not isinstance(row, dict):
            row = _default_session_row(safe_session_id)
            sessions[safe_session_id] = row
            store["sessions"] = sessions
            store["updated_at"] = _utc_now_iso()
            _write_store(path, store)
        return _session_snapshot(row, safe_session_id)


def update_chat_session_metrics(
    *,
    session_id: str,
    turn_usage: dict[str, Any] | None,
    llm_usage: dict[str, Any] | None,
    trace_id: str | None = None,
    run_id: str | None = None,
    path: Path = DEFAULT_CHAT_SESSION_METRICS_PATH,
) -> dict[str, Any]:
    safe_session_id = _sanitize_session_id(session_id)
    if _use_supabase(path):
        return _sb_update_session_metrics(
            session_id=safe_session_id,
            turn_usage=turn_usage,
            llm_usage=llm_usage,
            trace_id=trace_id,
            run_id=run_id,
        )
    turn = _coerce_usage(turn_usage)
    llm = _coerce_usage(llm_usage)
    with _LOCK:
        store = _read_store(path)
        sessions = dict(store.get("sessions") or {})
        row = sessions.get(safe_session_id)
        if not isinstance(row, dict):
            row = _default_session_row(safe_session_id)

        current_turn = _coerce_usage(dict(row.get("token_usage_total") or {}))
        current_llm = _coerce_usage(dict(row.get("llm_token_usage_total") or {}))

        row["turn_count"] = max(0, int(row.get("turn_count") or 0)) + 1
        row["token_usage_total"] = {
            "input_tokens": current_turn["input_tokens"] + turn["input_tokens"],
            "output_tokens": current_turn["output_tokens"] + turn["output_tokens"],
            "total_tokens": current_turn["total_tokens"] + turn["total_tokens"],
        }
        row["llm_token_usage_total"] = {
            "input_tokens": current_llm["input_tokens"] + llm["input_tokens"],
            "output_tokens": current_llm["output_tokens"] + llm["output_tokens"],
            "total_tokens": current_llm["total_tokens"] + llm["total_tokens"],
        }
        row["last_trace_id"] = str(trace_id).strip() if trace_id else row.get("last_trace_id")
        row["last_run_id"] = str(run_id).strip() if run_id else row.get("last_run_id")
        row["updated_at"] = _utc_now_iso()
        sessions[safe_session_id] = row
        store["sessions"] = sessions
        store["updated_at"] = row["updated_at"]
        _write_store(path, store)
        return _session_snapshot(row, safe_session_id)
