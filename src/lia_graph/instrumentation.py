from __future__ import annotations

import json
import re
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_LOG_PATH = Path("logs/events.jsonl")
DEFAULT_REASONING_LOG_PATH = Path("logs/reasoning_events.jsonl")
MAX_REASONING_EVENTS = 8000

ALLOWED_REASONING_CATEGORIES = {
    "instruction",
    "restriction",
    "file_access",
    "api_call",
    "api_reply",
    "dependency_call",
    "dependency_reply",
    "logic",
}
_REDACTED_KEYS = {"api_key", "authorization", "token", "secret", "password"}
_FORBIDDEN_DETAIL_KEYS = {"answer_markdown", "prompt_full", "raw_prompt", "full_document_text"}
_WHITESPACE_RE = re.compile(r"\S+")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def estimate_tokens_whitespace(text: str | None) -> int:
    if not text:
        return 0
    return len(_WHITESPACE_RE.findall(str(text)))


def estimate_token_usage_from_text(
    *,
    input_text: str | None = None,
    output_text: str | None = None,
) -> dict[str, Any]:
    input_tokens = estimate_tokens_whitespace(input_text)
    output_tokens = estimate_tokens_whitespace(output_text)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "source": "estimated",
        "estimator": "whitespace_v1",
        "raw_usage": None,
    }


def build_provider_token_usage(raw_usage: dict[str, Any] | None) -> dict[str, Any]:
    usage = dict(raw_usage or {})
    input_tokens = int(
        usage.get("prompt_tokens")
        or usage.get("input_tokens")
        or usage.get("input")
        or 0
    )
    output_tokens = int(
        usage.get("completion_tokens")
        or usage.get("output_tokens")
        or usage.get("output")
        or 0
    )
    total_tokens = int(usage.get("total_tokens") or (input_tokens + output_tokens))
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "source": "provider",
        "estimator": None,
        "raw_usage": usage,
    }


def normalize_token_usage(payload: dict[str, Any] | None) -> dict[str, Any]:
    raw = dict(payload or {})
    source = str(raw.get("source", "none")).strip().lower() or "none"
    if source not in {"provider", "estimated", "none"}:
        source = "none"
    input_tokens = int(raw.get("input_tokens") or 0)
    output_tokens = int(raw.get("output_tokens") or 0)
    total_tokens = int(raw.get("total_tokens") or (input_tokens + output_tokens))
    estimator = raw.get("estimator")
    if estimator is not None:
        estimator = str(estimator).strip() or None
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "source": source,
        "estimator": estimator,
        "raw_usage": raw.get("raw_usage"),
    }


def _sanitize_value(value: Any, depth: int = 0) -> Any:
    if depth > 4:
        return "[truncated]"
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, inner in value.items():
            lowered = str(key).strip().lower()
            if lowered in _FORBIDDEN_DETAIL_KEYS:
                continue
            if lowered in _REDACTED_KEYS:
                out[key] = "[redacted]"
                continue
            out[key] = _sanitize_value(inner, depth + 1)
        return out
    if isinstance(value, list):
        return [_sanitize_value(item, depth + 1) for item in value[:50]]
    if isinstance(value, tuple):
        return [_sanitize_value(item, depth + 1) for item in value[:50]]
    if isinstance(value, str):
        if len(value) > 1800:
            return value[:1800] + "...[truncated]"
        return value
    return value


class _ReasoningEventStore:
    def __init__(self, max_items: int = MAX_REASONING_EVENTS) -> None:
        self._max_items = max_items
        self._events: deque[dict[str, Any]] = deque(maxlen=max_items)
        self._next_seq = 0
        self._cv = threading.Condition()

    def append(self, event: dict[str, Any]) -> dict[str, Any]:
        with self._cv:
            self._next_seq += 1
            payload = dict(event)
            payload["seq"] = self._next_seq
            self._events.append(payload)
            self._cv.notify_all()
            return dict(payload)

    def list(
        self,
        *,
        trace_id: str | None,
        cursor: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int, int]:
        with self._cv:
            return self._list_unlocked(trace_id=trace_id, cursor=cursor, limit=limit)

    def wait_for(
        self,
        *,
        trace_id: str | None,
        cursor: int,
        timeout_seconds: float,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int, int]:
        deadline = time.monotonic() + max(0.0, timeout_seconds)
        with self._cv:
            while True:
                rows, next_cursor, latest_seq = self._list_unlocked(
                    trace_id=trace_id,
                    cursor=cursor,
                    limit=limit,
                )
                if rows:
                    return rows, next_cursor, latest_seq
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return [], cursor, self._next_seq
                self._cv.wait(remaining)

    def snapshot(self, *, trace_id: str | None = None) -> list[dict[str, Any]]:
        with self._cv:
            rows = list(self._events)
        if trace_id:
            return [dict(row) for row in rows if str(row.get("trace_id", "")) == trace_id]
        return [dict(row) for row in rows]

    def _list_unlocked(
        self,
        *,
        trace_id: str | None,
        cursor: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int, int]:
        rows: list[dict[str, Any]] = []
        for row in self._events:
            seq = int(row.get("seq", 0) or 0)
            if seq <= cursor:
                continue
            if trace_id and str(row.get("trace_id", "")) != trace_id:
                continue
            rows.append(dict(row))
            if len(rows) >= limit:
                break
        next_cursor = int(rows[-1]["seq"]) if rows else int(cursor)
        return rows, next_cursor, self._next_seq


_REASONING_STORE = _ReasoningEventStore()


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def emit_event(event_type: str, payload: dict[str, Any], log_path: Path = DEFAULT_LOG_PATH) -> None:
    """Agregar evento JSON liviano para auditoria y debugging."""
    event = {
        "ts_utc": _utc_now_iso(),
        "event_type": event_type,
        "payload": payload,
    }
    _append_jsonl(log_path, event)


def emit_reasoning_event(
    *,
    trace_id: str | None,
    phase: str,
    category: str,
    step: str,
    message: str,
    status: str = "ok",
    dependency: str | None = None,
    duration_ms: float | None = None,
    token_usage: dict[str, Any] | None = None,
    details: dict[str, Any] | None = None,
    log_path: Path = DEFAULT_REASONING_LOG_PATH,
) -> dict[str, Any]:
    normalized_category = str(category or "").strip().lower() or "logic"
    if normalized_category not in ALLOWED_REASONING_CATEGORIES:
        normalized_category = "logic"

    event = {
        "ts_utc": _utc_now_iso(),
        "trace_id": str(trace_id).strip() if trace_id else None,
        "phase": str(phase or "").strip() or "orchestration",
        "category": normalized_category,
        "step": str(step or "").strip() or "unknown_step",
        "message": str(message or "").strip()[:400],
        "status": str(status or "").strip() or "ok",
        "dependency": str(dependency).strip() if dependency else None,
        "duration_ms": float(duration_ms) if duration_ms is not None else None,
        "token_usage": normalize_token_usage(token_usage),
        "details": _sanitize_value(details or {}),
    }

    appended = _REASONING_STORE.append(event)
    _append_jsonl(log_path, appended)
    _append_jsonl(
        DEFAULT_LOG_PATH,
        {
            "ts_utc": appended["ts_utc"],
            "event_type": "reasoning.window.event",
            "payload": appended,
        },
    )
    return appended


def list_reasoning_events(
    *,
    trace_id: str | None = None,
    cursor: int = 0,
    limit: int = 200,
) -> tuple[list[dict[str, Any]], int, int]:
    safe_limit = max(1, min(int(limit), 500))
    safe_cursor = max(0, int(cursor))
    safe_trace_id = str(trace_id).strip() if trace_id else None
    return _REASONING_STORE.list(trace_id=safe_trace_id, cursor=safe_cursor, limit=safe_limit)


def wait_reasoning_events(
    *,
    trace_id: str | None = None,
    cursor: int = 0,
    timeout_seconds: float = 12.0,
    limit: int = 200,
) -> tuple[list[dict[str, Any]], int, int]:
    safe_limit = max(1, min(int(limit), 500))
    safe_cursor = max(0, int(cursor))
    safe_trace_id = str(trace_id).strip() if trace_id else None
    return _REASONING_STORE.wait_for(
        trace_id=safe_trace_id,
        cursor=safe_cursor,
        timeout_seconds=max(0.1, float(timeout_seconds)),
        limit=safe_limit,
    )


def summarize_trace_tokens(trace_id: str) -> dict[str, Any]:
    trace = str(trace_id or "").strip()
    if not trace:
        return {"total_tokens": 0, "by_dependency": {}}

    by_dependency: dict[str, dict[str, int]] = {}
    total_tokens = 0
    for event in _REASONING_STORE.snapshot(trace_id=trace):
        usage = normalize_token_usage(dict(event.get("token_usage") or {}))
        tokens = int(usage.get("total_tokens") or 0)
        if tokens <= 0:
            continue
        dependency = str(event.get("dependency") or "unknown")
        row = by_dependency.setdefault(
            dependency,
            {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        )
        row["input_tokens"] += int(usage.get("input_tokens") or 0)
        row["output_tokens"] += int(usage.get("output_tokens") or 0)
        row["total_tokens"] += tokens
        total_tokens += tokens
    return {"total_tokens": total_tokens, "by_dependency": by_dependency}
