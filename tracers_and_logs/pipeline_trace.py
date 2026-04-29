"""Pipeline trace — single source of truth for retrieval-stage instrumentation.

The trace is a list of step entries plus a few invariants (trace_id, qid_hint,
start time). Each step entry carries:

* ``step``       — dotted name, e.g. ``topic_router.llm_attempt``.
* ``status``     — ``ok`` | ``fallback`` | ``error`` | ``skipped`` | ``info``.
* ``elapsed_ms`` — milliseconds since the trace started (cheap clock).
* ``details``    — arbitrary JSON-safe payload bounded by
  ``_MAX_DETAIL_CHARS``; oversize values are truncated, not dropped.

Every ``step`` call also writes one JSON line to
``tracers_and_logs/logs/pipeline_trace.jsonl`` so an operator can ``tail``
the file in real time. The same payload is attached to
``response.diagnostics["pipeline_trace"]`` at the end of the request so the
eval harness picks it up too.

The collector is contextvars-based: each request thread (or asyncio task)
gets its own active trace, never bleeding into siblings under concurrency.
"""

from __future__ import annotations

import contextvars
import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# Module-level configuration
# ---------------------------------------------------------------------------

_PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_LOG_PATH = _PACKAGE_ROOT / "logs" / "pipeline_trace.jsonl"

# Each step's ``details`` payload is bounded so a single anomalous step
# (e.g. a 300-row chunk dump) cannot evict the rest of the trace from the
# operator's screen. Oversize string/list values are truncated with a
# ``[truncated:<N>]`` marker so the operator can see *that* the cap fired.
_MAX_DETAIL_CHARS = 4000
_MAX_LIST_ITEMS = 80

_STATUS_VALUES = {"ok", "fallback", "error", "skipped", "info"}

_active_trace: contextvars.ContextVar["PipelineTrace | None"] = contextvars.ContextVar(
    "active_pipeline_trace", default=None
)

_log_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _truncate(value: Any, depth: int = 0) -> Any:
    if depth > 6:
        return "[truncated:depth]"
    if isinstance(value, dict):
        return {str(k): _truncate(v, depth + 1) for k, v in list(value.items())[:_MAX_LIST_ITEMS]}
    if isinstance(value, (list, tuple)):
        items = [_truncate(item, depth + 1) for item in list(value)[:_MAX_LIST_ITEMS]]
        if len(value) > _MAX_LIST_ITEMS:
            items.append(f"[truncated:{len(value) - _MAX_LIST_ITEMS} more]")
        return items
    if isinstance(value, str):
        if len(value) > _MAX_DETAIL_CHARS:
            return value[:_MAX_DETAIL_CHARS] + f"[truncated:{len(value) - _MAX_DETAIL_CHARS}]"
        return value
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    # Fall back to repr for unknown types — keeps the trace readable.
    rendered = repr(value)
    if len(rendered) > _MAX_DETAIL_CHARS:
        return rendered[:_MAX_DETAIL_CHARS] + f"[truncated:{len(rendered) - _MAX_DETAIL_CHARS}]"
    return rendered


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=False, default=str)
    with _log_lock:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


# ---------------------------------------------------------------------------
# PipelineTrace — the per-request collector
# ---------------------------------------------------------------------------


class PipelineTrace:
    """Per-request collector. Append-only; never mutate prior entries.

    The collector is opaque outside this module — callers reach it through
    :func:`step` / :func:`snapshot`, never by holding the instance.
    """

    __slots__ = (
        "trace_id",
        "qid_hint",
        "session_id",
        "started_utc",
        "_t0",
        "_steps",
        "_lock",
        "_log_path",
    )

    def __init__(
        self,
        *,
        trace_id: str | None,
        qid_hint: str | None = None,
        session_id: str | None = None,
        log_path: Path | None = None,
    ) -> None:
        self.trace_id = (str(trace_id).strip() or None) if trace_id else None
        self.qid_hint = (str(qid_hint).strip() or None) if qid_hint else None
        self.session_id = (str(session_id).strip() or None) if session_id else None
        self.started_utc = _utc_now_iso()
        self._t0 = time.monotonic()
        self._steps: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._log_path = Path(log_path) if log_path else DEFAULT_LOG_PATH

    # -- internal -----------------------------------------------------------

    def _record(self, entry: dict[str, Any]) -> None:
        with self._lock:
            self._steps.append(entry)

    # -- public API --------------------------------------------------------

    def step(
        self,
        step_name: str,
        *,
        status: str = "ok",
        message: str | None = None,
        **details: Any,
    ) -> dict[str, Any]:
        normalized_status = str(status or "").strip().lower() or "ok"
        if normalized_status not in _STATUS_VALUES:
            normalized_status = "info"
        elapsed_ms = round((time.monotonic() - self._t0) * 1000.0, 2)
        truncated_details = {k: _truncate(v) for k, v in details.items()}
        entry: dict[str, Any] = {
            "ts_utc": _utc_now_iso(),
            "trace_id": self.trace_id,
            "qid_hint": self.qid_hint,
            "session_id": self.session_id,
            "step": str(step_name).strip() or "unknown_step",
            "status": normalized_status,
            "elapsed_ms": elapsed_ms,
            "message": (str(message).strip()[:400] if message else None),
            "details": truncated_details,
        }
        self._record(entry)
        try:
            _append_jsonl(self._log_path, entry)
        except OSError:
            # Logging must never break the request path; swallow the IO error.
            pass
        return entry

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            steps_copy = [dict(s) for s in self._steps]
        return {
            "trace_id": self.trace_id,
            "qid_hint": self.qid_hint,
            "session_id": self.session_id,
            "started_utc": self.started_utc,
            "total_ms": round((time.monotonic() - self._t0) * 1000.0, 2),
            "step_count": len(steps_copy),
            "steps": steps_copy,
            "log_path": str(self._log_path),
        }


# ---------------------------------------------------------------------------
# Module-level facade — what callers import
# ---------------------------------------------------------------------------


def start(
    *,
    trace_id: str | None,
    qid_hint: str | None = None,
    session_id: str | None = None,
    log_path: Path | None = None,
) -> tuple[PipelineTrace, contextvars.Token]:
    """Install a fresh PipelineTrace as the active context-local."""
    trace = PipelineTrace(
        trace_id=trace_id,
        qid_hint=qid_hint,
        session_id=session_id,
        log_path=log_path,
    )
    token = _active_trace.set(trace)
    trace.step(
        "trace.start",
        status="info",
        started_utc=trace.started_utc,
        log_path=str(trace._log_path),
    )
    return trace, token


def start_or_reuse(
    *,
    trace_id: str | None,
    qid_hint: str | None = None,
    session_id: str | None = None,
    log_path: Path | None = None,
) -> tuple[PipelineTrace, contextvars.Token | None]:
    """Reuse the active trace if one is installed; else install a fresh one.

    Lets a deeper module (e.g. the orchestrator) participate in a trace that
    a higher layer (e.g. the chat-payload module that runs the topic
    resolver) already started — without losing entries when no such layer
    exists, e.g. when ``run_pipeline_d`` is invoked from a unit test.

    Returns ``(trace, token)`` where ``token`` is ``None`` when reusing —
    indicating the caller does NOT own teardown (the higher layer does).
    """
    existing = _active_trace.get()
    if existing is not None:
        existing.step(
            "trace.reuse",
            status="info",
            owner_trace_id=existing.trace_id,
            requested_trace_id=trace_id,
        )
        return existing, None
    return start(
        trace_id=trace_id,
        qid_hint=qid_hint,
        session_id=session_id,
        log_path=log_path,
    )


def finish(token: contextvars.Token | None) -> None:
    """Clear the active trace; safe to call with ``None``.

    A ``None`` token means the caller is reusing an outer trace — they
    should NOT clear it. The outer trace.finish call will handle teardown.
    """
    if token is None:
        return
    trace = _active_trace.get()
    if trace is not None:
        trace.step("trace.finish", status="info", total_ms=round((time.monotonic() - trace._t0) * 1000.0, 2))
    try:
        _active_trace.reset(token)
    except (ValueError, LookupError):
        # Token from a different context — set explicit None instead.
        _active_trace.set(None)


def active() -> PipelineTrace | None:
    return _active_trace.get()


def step(
    step_name: str,
    *,
    status: str = "ok",
    message: str | None = None,
    **details: Any,
) -> None:
    """Append one entry to the active trace; no-op if none installed.

    This is the workhorse all instrumented modules call. It's intentionally
    cheap when no trace is active so non-eval traffic pays nothing.
    """
    trace = _active_trace.get()
    if trace is None:
        return
    trace.step(step_name, status=status, message=message, **details)


def snapshot() -> dict[str, Any] | None:
    trace = _active_trace.get()
    if trace is None:
        return None
    return trace.snapshot()


# ---------------------------------------------------------------------------
# Forced-on switch for environments where the eval harness can't reach
# the auth_context.is_robot path. Setting LIA_PIPELINE_TRACE=1 in the env
# lets the orchestrator install a trace unconditionally.
# ---------------------------------------------------------------------------


def force_enabled() -> bool:
    return str(os.environ.get("LIA_PIPELINE_TRACE", "")).strip().lower() in {"1", "on", "true", "yes"}


__all__ = [
    "PipelineTrace",
    "DEFAULT_LOG_PATH",
    "start",
    "finish",
    "active",
    "step",
    "snapshot",
    "force_enabled",
]
