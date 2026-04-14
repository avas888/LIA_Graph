"""Durable chat-run state for end-to-end chat lifecycle telemetry and resume."""

from __future__ import annotations

import json
import logging
import math
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar
from uuid import uuid4

from .pipeline_router import DEFAULT_PIPELINE_VARIANT

DEFAULT_CHAT_RUNS_DIR = Path("artifacts/runtime/chat_runs")

_LOCK = threading.RLock()
_log = logging.getLogger(__name__)
_MEMORY_RECORDS: dict[str, dict[str, "ChatRunRecord"]] = {}
_MEMORY_FINGERPRINTS: dict[str, dict[str, str]] = {}
_MEMORY_EVENTS: dict[str, dict[str, list[dict[str, Any]]]] = {}
_SUPABASE_RETRY_DELAYS = (0.2, 0.5)
_T = TypeVar("_T")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _use_supabase(base_dir: Path) -> bool:
    from lia_contador.supabase_client import is_supabase_enabled, matches_default_storage_path

    if not matches_default_storage_path(base_dir, DEFAULT_CHAT_RUNS_DIR):
        return False
    return is_supabase_enabled()


@dataclass
class ChatRunRecord:
    chat_run_id: str
    trace_id: str
    session_id: str
    client_turn_id: str
    request_fingerprint: str
    endpoint: str = "/api/chat"
    tenant_id: str = ""
    user_id: str = ""
    company_id: str = ""
    status: str = "running"
    pipeline_run_id: str | None = None
    request_payload: dict[str, Any] = field(default_factory=dict)
    response_payload: dict[str, Any] = field(default_factory=dict)
    error_payload: dict[str, Any] = field(default_factory=dict)
    request_received_at: str = ""
    pipeline_started_at: str = ""
    first_model_delta_at: str = ""
    first_visible_answer_at: str = ""
    pipeline_completed_at: str = ""
    final_payload_ready_at: str = ""
    response_sent_at: str = ""
    async_persistence_done_at: str = ""
    completed_at: str = ""
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        now = _utc_now_iso()
        if not self.chat_run_id:
            self.chat_run_id = f"cr_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = self.created_at
        if not self.request_received_at:
            self.request_received_at = self.created_at
        self.trace_id = str(self.trace_id or "").strip()
        self.session_id = str(self.session_id or "").strip()
        self.client_turn_id = str(self.client_turn_id or "").strip()
        self.request_fingerprint = str(self.request_fingerprint or "").strip()
        self.endpoint = str(self.endpoint or "/api/chat").strip() or "/api/chat"
        self.tenant_id = str(self.tenant_id or "").strip()
        self.user_id = str(self.user_id or "").strip()
        self.company_id = str(self.company_id or "").strip()
        self.status = str(self.status or "running").strip() or "running"
        self.pipeline_run_id = str(self.pipeline_run_id or "").strip() or None
        self.request_payload = dict(self.request_payload or {})
        self.response_payload = dict(self.response_payload or {})
        self.error_payload = dict(self.error_payload or {})
        self.pipeline_started_at = str(self.pipeline_started_at or "").strip()
        self.first_model_delta_at = str(self.first_model_delta_at or "").strip()
        self.first_visible_answer_at = str(self.first_visible_answer_at or "").strip()
        self.pipeline_completed_at = str(self.pipeline_completed_at or "").strip()
        self.final_payload_ready_at = str(self.final_payload_ready_at or "").strip()
        self.response_sent_at = str(self.response_sent_at or "").strip()
        self.async_persistence_done_at = str(self.async_persistence_done_at or "").strip()
        self.completed_at = str(self.completed_at or "").strip()

    def to_dict(self) -> dict[str, Any]:
        return {
            "chat_run_id": self.chat_run_id,
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "client_turn_id": self.client_turn_id,
            "request_fingerprint": self.request_fingerprint,
            "endpoint": self.endpoint,
            "tenant_id": self.tenant_id or None,
            "user_id": self.user_id or None,
            "company_id": self.company_id or None,
            "status": self.status,
            "pipeline_run_id": self.pipeline_run_id,
            "request_payload": dict(self.request_payload),
            "response_payload": dict(self.response_payload),
            "error_payload": dict(self.error_payload),
            "request_received_at": self.request_received_at or None,
            "pipeline_started_at": self.pipeline_started_at or None,
            "first_model_delta_at": self.first_model_delta_at or None,
            "first_visible_answer_at": self.first_visible_answer_at or None,
            "pipeline_completed_at": self.pipeline_completed_at or None,
            "final_payload_ready_at": self.final_payload_ready_at or None,
            "response_sent_at": self.response_sent_at or None,
            "async_persistence_done_at": self.async_persistence_done_at or None,
            "completed_at": self.completed_at or None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ChatRunRecord":
        return cls(
            chat_run_id=_coerce_text(payload.get("chat_run_id")),
            trace_id=_coerce_text(payload.get("trace_id")),
            session_id=_coerce_text(payload.get("session_id")),
            client_turn_id=_coerce_text(payload.get("client_turn_id")),
            request_fingerprint=_coerce_text(payload.get("request_fingerprint")),
            endpoint=_coerce_text(payload.get("endpoint")),
            tenant_id=_coerce_text(payload.get("tenant_id")),
            user_id=_coerce_text(payload.get("user_id")),
            company_id=_coerce_text(payload.get("company_id")),
            status=_coerce_text(payload.get("status")),
            pipeline_run_id=_coerce_text(payload.get("pipeline_run_id")),
            request_payload=dict(payload.get("request_payload") or {}),
            response_payload=dict(payload.get("response_payload") or {}),
            error_payload=dict(payload.get("error_payload") or {}),
            request_received_at=_coerce_text(payload.get("request_received_at")),
            pipeline_started_at=_coerce_text(payload.get("pipeline_started_at")),
            first_model_delta_at=_coerce_text(payload.get("first_model_delta_at")),
            first_visible_answer_at=_coerce_text(payload.get("first_visible_answer_at")),
            pipeline_completed_at=_coerce_text(payload.get("pipeline_completed_at")),
            final_payload_ready_at=_coerce_text(payload.get("final_payload_ready_at")),
            response_sent_at=_coerce_text(payload.get("response_sent_at")),
            async_persistence_done_at=_coerce_text(payload.get("async_persistence_done_at")),
            completed_at=_coerce_text(payload.get("completed_at")),
            created_at=_coerce_text(payload.get("created_at")),
            updated_at=_coerce_text(payload.get("updated_at")),
        )


def _normalize_db_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(row)
    for field in (
        "request_received_at",
        "pipeline_started_at",
        "first_model_delta_at",
        "first_visible_answer_at",
        "pipeline_completed_at",
        "final_payload_ready_at",
        "response_sent_at",
        "async_persistence_done_at",
        "completed_at",
        "created_at",
        "updated_at",
    ):
        value = normalized.get(field)
        if hasattr(value, "isoformat"):
            normalized[field] = value.isoformat()
    return normalized


def _record_path(base_dir: Path, chat_run_id: str) -> Path:
    safe_id = str(chat_run_id or "").strip().replace("/", "_").replace("..", "_")[:160]
    return base_dir / f"{safe_id}.json"


def _events_path(base_dir: Path, chat_run_id: str) -> Path:
    safe_id = str(chat_run_id or "").strip().replace("/", "_").replace("..", "_")[:160]
    return base_dir / "events" / f"{safe_id}.jsonl"


def _fs_save_record(record: ChatRunRecord, *, base_dir: Path) -> None:
    path = _record_path(base_dir, record.chat_run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def _fs_load_record(chat_run_id: str, *, base_dir: Path) -> ChatRunRecord | None:
    path = _record_path(base_dir, chat_run_id)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return ChatRunRecord.from_dict(payload)


def _fs_find_by_fingerprint(request_fingerprint: str, *, base_dir: Path) -> ChatRunRecord | None:
    for path in sorted(base_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        if str(payload.get("request_fingerprint", "")).strip() != str(request_fingerprint or "").strip():
            continue
        return ChatRunRecord.from_dict(payload)
    return None


def _fs_append_event(chat_run_id: str, event: dict[str, Any], *, base_dir: Path) -> None:
    path = _events_path(base_dir, chat_run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def _fs_get_events(chat_run_id: str, *, base_dir: Path) -> list[dict[str, Any]]:
    path = _events_path(base_dir, chat_run_id)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _sb_upsert_record(record: ChatRunRecord) -> None:
    from lia_contador.supabase_client import get_supabase_client

    client = get_supabase_client()
    client.table("chat_runs").upsert(record.to_dict(), on_conflict="chat_run_id").execute()


def _sb_load_record(chat_run_id: str) -> ChatRunRecord | None:
    from lia_contador.supabase_client import get_supabase_client

    client = get_supabase_client()
    result = client.table("chat_runs").select("*").eq("chat_run_id", chat_run_id).limit(1).execute()
    if not result.data:
        return None
    return ChatRunRecord.from_dict(_normalize_db_row(dict(result.data[0])))


def _sb_find_by_fingerprint(request_fingerprint: str) -> ChatRunRecord | None:
    from lia_contador.supabase_client import get_supabase_client

    client = get_supabase_client()
    result = (
        client.table("chat_runs")
        .select("*")
        .eq("request_fingerprint", str(request_fingerprint or "").strip())
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    return ChatRunRecord.from_dict(_normalize_db_row(dict(result.data[0])))


def _sb_append_event(chat_run_id: str, event: dict[str, Any]) -> None:
    from lia_contador.supabase_client import get_supabase_client

    client = get_supabase_client()
    result = (
        client.table("chat_run_events")
        .select("event_index")
        .eq("chat_run_id", chat_run_id)
        .order("event_index", desc=True)
        .limit(1)
        .execute()
    )
    next_index = 0
    if result.data:
        next_index = int(result.data[0].get("event_index") or 0) + 1
    client.table("chat_run_events").insert(
        {
            "chat_run_id": chat_run_id,
            "event_index": next_index,
            "event_payload": event,
        }
    ).execute()


def _sb_get_events(chat_run_id: str) -> list[dict[str, Any]]:
    from lia_contador.supabase_client import get_supabase_client

    client = get_supabase_client()
    result = (
        client.table("chat_run_events")
        .select("event_index,event_payload")
        .eq("chat_run_id", chat_run_id)
        .order("event_index")
        .execute()
    )
    rows: list[dict[str, Any]] = []
    for row in result.data or []:
        payload = dict(row.get("event_payload") or {})
        if payload:
            rows.append(payload)
    return rows


def _warn_backend_fallback(backend: str, operation: str, exc: Exception) -> None:
    _log.warning(
        "chat_runs_store: %s %s failed; using in-memory degraded state. error=%s",
        backend,
        operation,
        exc,
    )


def _memory_scope(base_dir: Path) -> str:
    return str(Path(base_dir).expanduser())


def _cache_record(record: ChatRunRecord, *, base_dir: Path) -> None:
    scope = _memory_scope(base_dir)
    records = _MEMORY_RECORDS.setdefault(scope, {})
    fingerprints = _MEMORY_FINGERPRINTS.setdefault(scope, {})
    records[record.chat_run_id] = ChatRunRecord.from_dict(record.to_dict())
    if record.request_fingerprint:
        fingerprints[record.request_fingerprint] = record.chat_run_id


def _cache_load_record(chat_run_id: str, *, base_dir: Path) -> ChatRunRecord | None:
    scope = _memory_scope(base_dir)
    record = _MEMORY_RECORDS.get(scope, {}).get(chat_run_id)
    if record is None:
        return None
    return ChatRunRecord.from_dict(record.to_dict())


def _cache_find_by_fingerprint(request_fingerprint: str, *, base_dir: Path) -> ChatRunRecord | None:
    scope = _memory_scope(base_dir)
    chat_run_id = _MEMORY_FINGERPRINTS.get(scope, {}).get(str(request_fingerprint or "").strip())
    if not chat_run_id:
        return None
    return _cache_load_record(chat_run_id, base_dir=base_dir)


def _cache_append_event(chat_run_id: str, event: dict[str, Any], *, base_dir: Path) -> None:
    scope = _memory_scope(base_dir)
    scoped_events = _MEMORY_EVENTS.setdefault(scope, {})
    scoped_events.setdefault(chat_run_id, []).append(dict(event or {}))


def _cache_get_events(chat_run_id: str, *, base_dir: Path) -> list[dict[str, Any]]:
    scope = _memory_scope(base_dir)
    return [dict(item) for item in _MEMORY_EVENTS.get(scope, {}).get(chat_run_id, [])]


def _supabase_retry(operation: str, action: Callable[[], _T]) -> _T:
    last_exc: Exception | None = None
    total_attempts = len(_SUPABASE_RETRY_DELAYS) + 1
    for attempt in range(1, total_attempts + 1):
        if attempt > 1:
            time.sleep(_SUPABASE_RETRY_DELAYS[attempt - 2])
        try:
            return action()
        except Exception as exc:
            last_exc = exc
            if attempt >= total_attempts:
                break
            _log.warning(
                "chat_runs_store: Supabase %s failed on attempt %s/%s; retrying. error=%s",
                operation,
                attempt,
                total_attempts,
                exc,
            )
    assert last_exc is not None
    raise last_exc


def save_chat_run(record: ChatRunRecord, *, base_dir: Path = DEFAULT_CHAT_RUNS_DIR) -> ChatRunRecord:
    record.updated_at = _utc_now_iso()
    with _LOCK:
        _cache_record(record, base_dir=base_dir)
        if _use_supabase(base_dir):
            try:
                _supabase_retry("upsert", lambda: _sb_upsert_record(record))
            except Exception as exc:
                _warn_backend_fallback("Supabase", "upsert", exc)
        else:
            try:
                _fs_save_record(record, base_dir=base_dir)
            except Exception as exc:
                _warn_backend_fallback("filesystem", "save", exc)
    return record


def create_chat_run(
    *,
    trace_id: str,
    session_id: str,
    client_turn_id: str,
    request_fingerprint: str,
    endpoint: str,
    tenant_id: str = "",
    user_id: str = "",
    company_id: str = "",
    request_payload: dict[str, Any] | None = None,
    base_dir: Path = DEFAULT_CHAT_RUNS_DIR,
) -> ChatRunRecord:
    record = ChatRunRecord(
        chat_run_id="",
        trace_id=trace_id,
        session_id=session_id,
        client_turn_id=client_turn_id,
        request_fingerprint=request_fingerprint,
        endpoint=endpoint,
        tenant_id=tenant_id,
        user_id=user_id,
        company_id=company_id,
        status="running",
        request_payload=dict(request_payload or {}),
    )
    save_chat_run(record, base_dir=base_dir)
    return record


def load_chat_run(chat_run_id: str, *, base_dir: Path = DEFAULT_CHAT_RUNS_DIR) -> ChatRunRecord | None:
    with _LOCK:
        if _use_supabase(base_dir):
            try:
                record = _supabase_retry("load", lambda: _sb_load_record(chat_run_id))
            except Exception as exc:
                _warn_backend_fallback("Supabase", "load", exc)
                record = None
            if record is not None:
                _cache_record(record, base_dir=base_dir)
                return record
            return _cache_load_record(chat_run_id, base_dir=base_dir)
        try:
            record = _fs_load_record(chat_run_id, base_dir=base_dir)
        except Exception as exc:
            _warn_backend_fallback("filesystem", "load", exc)
            record = None
        if record is not None:
            _cache_record(record, base_dir=base_dir)
            return record
        return _cache_load_record(chat_run_id, base_dir=base_dir)


def find_chat_run_by_fingerprint(
    request_fingerprint: str,
    *,
    base_dir: Path = DEFAULT_CHAT_RUNS_DIR,
) -> ChatRunRecord | None:
    with _LOCK:
        if _use_supabase(base_dir):
            try:
                record = _supabase_retry(
                    "find_by_fingerprint",
                    lambda: _sb_find_by_fingerprint(request_fingerprint),
                )
            except Exception as exc:
                _warn_backend_fallback("Supabase", "find_by_fingerprint", exc)
                record = None
            if record is not None:
                _cache_record(record, base_dir=base_dir)
                return record
            return _cache_find_by_fingerprint(request_fingerprint, base_dir=base_dir)
        try:
            record = _fs_find_by_fingerprint(request_fingerprint, base_dir=base_dir)
        except Exception as exc:
            _warn_backend_fallback("filesystem", "find_by_fingerprint", exc)
            record = None
        if record is not None:
            _cache_record(record, base_dir=base_dir)
            return record
        return _cache_find_by_fingerprint(request_fingerprint, base_dir=base_dir)


def update_chat_run(
    chat_run_id: str,
    *,
    base_dir: Path = DEFAULT_CHAT_RUNS_DIR,
    **patch: Any,
) -> ChatRunRecord | None:
    record = load_chat_run(chat_run_id, base_dir=base_dir)
    if record is None:
        return None
    for key, value in patch.items():
        if not hasattr(record, key):
            continue
        setattr(record, key, value)
    if record.status in {"completed", "failed"} and not record.completed_at:
        record.completed_at = _utc_now_iso()
    save_chat_run(record, base_dir=base_dir)
    return record


def record_chat_run_event(
    chat_run_id: str,
    *,
    event_type: str,
    payload: dict[str, Any] | None = None,
    base_dir: Path = DEFAULT_CHAT_RUNS_DIR,
) -> None:
    event = {
        "at": _utc_now_iso(),
        "event_type": str(event_type or "").strip() or "unknown",
        "payload": dict(payload or {}),
    }
    with _LOCK:
        _cache_append_event(chat_run_id, event, base_dir=base_dir)
        if _use_supabase(base_dir):
            try:
                _sb_append_event(chat_run_id, event)
            except Exception as exc:
                _warn_backend_fallback("Supabase", "append_event", exc)
        else:
            try:
                _fs_append_event(chat_run_id, event, base_dir=base_dir)
            except Exception as exc:
                _warn_backend_fallback("filesystem", "append_event", exc)


def record_chat_run_event_once(
    chat_run_id: str,
    *,
    event_type: str,
    payload: dict[str, Any] | None = None,
    base_dir: Path = DEFAULT_CHAT_RUNS_DIR,
) -> bool:
    normalized_event_type = str(event_type or "").strip() or "unknown"
    with _LOCK:
        existing_events = get_chat_run_events(chat_run_id, base_dir=base_dir)
        if any(str(item.get("event_type") or "").strip() == normalized_event_type for item in existing_events):
            return False
        event = {
            "at": _utc_now_iso(),
            "event_type": normalized_event_type,
            "payload": dict(payload or {}),
        }
        _cache_append_event(chat_run_id, event, base_dir=base_dir)
        if _use_supabase(base_dir):
            try:
                _sb_append_event(chat_run_id, event)
            except Exception as exc:
                _warn_backend_fallback("Supabase", "append_event_once", exc)
        else:
            try:
                _fs_append_event(chat_run_id, event, base_dir=base_dir)
            except Exception as exc:
                _warn_backend_fallback("filesystem", "append_event_once", exc)
    return True


def get_chat_run_events(chat_run_id: str, *, base_dir: Path = DEFAULT_CHAT_RUNS_DIR) -> list[dict[str, Any]]:
    with _LOCK:
        if _use_supabase(base_dir):
            try:
                rows = _sb_get_events(chat_run_id)
            except Exception as exc:
                _warn_backend_fallback("Supabase", "get_events", exc)
                rows = []
            if rows:
                _MEMORY_EVENTS.setdefault(_memory_scope(base_dir), {})[chat_run_id] = [dict(item) for item in rows]
            return rows or _cache_get_events(chat_run_id, base_dir=base_dir)
        try:
            rows = _fs_get_events(chat_run_id, base_dir=base_dir)
        except Exception as exc:
            _warn_backend_fallback("filesystem", "get_events", exc)
            rows = []
        if rows:
            _MEMORY_EVENTS.setdefault(_memory_scope(base_dir), {})[chat_run_id] = [dict(item) for item in rows]
            return rows
        return _cache_get_events(chat_run_id, base_dir=base_dir)


def _first_event_elapsed_ms(
    *,
    events: list[dict[str, Any]],
    event_type: str,
    request_received_at: str,
) -> float | None:
    matching_event = next((item for item in events if str(item.get("event_type") or "").strip() == event_type), None)
    if matching_event is None:
        return None
    payload = dict(matching_event.get("payload") or {})
    elapsed_ms = _coerce_ms(payload.get("elapsed_ms"))
    if elapsed_ms is not None:
        return elapsed_ms
    return _duration_ms(request_received_at, str(matching_event.get("at") or ""))


def _record_pipeline_variant(row: ChatRunRecord) -> str:
    response_payload = dict(row.response_payload or {})
    request_payload = dict(row.request_payload or {})
    for candidate in (
        response_payload.get("pipeline_variant"),
        ((response_payload.get("metrics") or {}).get("pipeline_variant") if isinstance(response_payload.get("metrics"), dict) else None),
        request_payload.get("pipeline_variant"),
    ):
        value = _coerce_text(candidate)
        if value:
            return value
    return DEFAULT_PIPELINE_VARIANT


def summarize_chat_run_metrics(
    *,
    base_dir: Path = DEFAULT_CHAT_RUNS_DIR,
    limit: int = 200,
) -> dict[str, Any]:
    rows: list[ChatRunRecord] = []
    if _use_supabase(base_dir):
        from lia_contador.supabase_client import get_supabase_client

        try:
            client = get_supabase_client()
            result = _supabase_retry(
                "summarize_metrics",
                lambda: client.table("chat_runs").select("*").order("created_at", desc=True).limit(limit).execute(),
            )
            rows = [ChatRunRecord.from_dict(_normalize_db_row(dict(item))) for item in (result.data or [])]
        except Exception as exc:
            _warn_backend_fallback("Supabase", "summarize_metrics", exc)
    else:
        try:
            for path in sorted(base_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)[:limit]:
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if isinstance(payload, dict):
                    rows.append(ChatRunRecord.from_dict(payload))
        except Exception as exc:
            _warn_backend_fallback("filesystem", "summarize_metrics", exc)
    if not rows:
        rows = sorted(
            (
                ChatRunRecord.from_dict(record.to_dict())
                for record in _MEMORY_RECORDS.get(_memory_scope(base_dir), {}).values()
            ),
            key=lambda item: item.updated_at,
            reverse=True,
        )[:limit]
    if not rows and not _use_supabase(base_dir):
        for path in sorted(base_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)[:limit]:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                rows.append(ChatRunRecord.from_dict(payload))

    first_visible_ms: list[float] = []
    response_bubble_highlighted_ms: list[float] = []
    final_sent_ms: list[float] = []
    pipeline_variants: dict[str, int] = {}
    for row in rows:
        events = get_chat_run_events(row.chat_run_id, base_dir=base_dir)
        bubble_ms = _first_event_elapsed_ms(
            events=events,
            event_type="chat_run.ui.response_bubble_highlighted",
            request_received_at=row.request_received_at,
        )
        first_ms = _duration_ms(row.request_received_at, row.first_visible_answer_at)
        final_ms = _duration_ms(row.request_received_at, row.response_sent_at)
        pipeline_variant = _record_pipeline_variant(row)
        pipeline_variants[pipeline_variant] = pipeline_variants.get(pipeline_variant, 0) + 1
        if bubble_ms is not None:
            response_bubble_highlighted_ms.append(bubble_ms)
        if first_ms is not None:
            first_visible_ms.append(first_ms)
        if final_ms is not None:
            final_sent_ms.append(final_ms)
    return {
        "sample_size": len(rows),
        "pipeline_variants": dict(sorted(pipeline_variants.items())),
        "response_bubble_highlighted_ms": _percentiles(response_bubble_highlighted_ms),
        "first_visible_answer_ms": _percentiles(first_visible_ms),
        "final_answer_sent_ms": _percentiles(final_sent_ms),
    }


def _duration_ms(start_iso: str, end_iso: str) -> float | None:
    if not start_iso or not end_iso:
        return None
    try:
        start = datetime.fromisoformat(str(start_iso).replace("Z", "+00:00"))
        end = datetime.fromisoformat(str(end_iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    return max(0.0, (end - start).total_seconds() * 1000)


def _coerce_ms(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return 0.0
    return round(parsed, 2)


def _percentiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"p50": None, "p95": None}
    ordered = sorted(values)
    return {
        "p50": round(_percentile(ordered, 0.50), 2),
        "p95": round(_percentile(ordered, 0.95), 2),
    }


def _percentile(values: list[float], ratio: float) -> float:
    if not values:
        return math.nan
    if len(values) == 1:
        return values[0]
    idx = max(0.0, min(float(len(values) - 1), (len(values) - 1) * ratio))
    lower = int(math.floor(idx))
    upper = int(math.ceil(idx))
    if lower == upper:
        return values[lower]
    weight = idx - lower
    return values[lower] + (values[upper] - values[lower]) * weight


__all__ = [
    "DEFAULT_CHAT_RUNS_DIR",
    "ChatRunRecord",
    "create_chat_run",
    "find_chat_run_by_fingerprint",
    "get_chat_run_events",
    "load_chat_run",
    "record_chat_run_event",
    "record_chat_run_event_once",
    "save_chat_run",
    "summarize_chat_run_metrics",
    "update_chat_run",
]
