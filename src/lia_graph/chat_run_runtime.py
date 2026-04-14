"""In-process coordination for logical chat runs."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .chat_runs_store import (
    DEFAULT_CHAT_RUNS_DIR,
    ChatRunRecord,
    create_chat_run,
    find_chat_run_by_fingerprint,
    load_chat_run,
    record_chat_run_event,
    update_chat_run,
)


def build_chat_run_fingerprint(
    *,
    session_id: str,
    client_turn_id: str,
    message: str,
    topic: str | None,
    pais: str,
    primary_scope_mode: str,
    response_route: str,
    retrieval_profile: str = "hybrid_rerank",
    response_depth: str = "auto",
    first_response_mode: str = "fast_action",
    engine_version: str | None = None,
) -> str:
    normalized = {
        "session_id": str(session_id or "").strip(),
        "client_turn_id": str(client_turn_id or "").strip(),
        "message": " ".join(str(message or "").split()).strip().lower(),
        "topic": str(topic or "").strip().lower(),
        "pais": str(pais or "").strip().lower(),
        "primary_scope_mode": str(primary_scope_mode or "").strip().lower(),
        "response_route": str(response_route or "").strip().lower(),
        "retrieval_profile": str(retrieval_profile or "").strip().lower(),
        "response_depth": str(response_depth or "").strip().lower(),
        "first_response_mode": str(first_response_mode or "").strip().lower(),
        "engine_version": str(engine_version or "").strip().lower(),
    }
    return hashlib.sha256(json.dumps(normalized, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


@dataclass
class _InFlightRun:
    chat_run_id: str
    request_fingerprint: str
    created_at_monotonic: float = field(default_factory=time.monotonic)
    condition: threading.Condition = field(default_factory=threading.Condition)
    terminal_payload: dict[str, Any] | None = None
    terminal_error: dict[str, Any] | None = None
    status: str = "running"


class ChatRunCoordinator:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._active_by_run_id: dict[str, _InFlightRun] = {}
        self._active_by_fingerprint: dict[str, _InFlightRun] = {}

    def acquire(
        self,
        *,
        trace_id: str,
        session_id: str,
        client_turn_id: str,
        request_fingerprint: str,
        endpoint: str,
        request_payload: dict[str, Any],
        tenant_id: str = "",
        user_id: str = "",
        company_id: str = "",
        chat_run_id: str | None = None,
        base_dir: Path = DEFAULT_CHAT_RUNS_DIR,
    ) -> tuple[ChatRunRecord, bool]:
        provided_chat_run_id = str(chat_run_id or "").strip()
        with self._lock:
            if provided_chat_run_id and provided_chat_run_id in self._active_by_run_id:
                active = self._active_by_run_id[provided_chat_run_id]
                record = load_chat_run(active.chat_run_id, base_dir=base_dir)
                if record is not None:
                    return record, False
            if request_fingerprint in self._active_by_fingerprint:
                active = self._active_by_fingerprint[request_fingerprint]
                record = load_chat_run(active.chat_run_id, base_dir=base_dir)
                if record is not None:
                    return record, False

        if provided_chat_run_id:
            existing = load_chat_run(provided_chat_run_id, base_dir=base_dir)
            if existing is not None:
                if existing.status == "running":
                    self._register_active(existing.chat_run_id, request_fingerprint)
                return existing, False

        existing = find_chat_run_by_fingerprint(request_fingerprint, base_dir=base_dir)
        if existing is not None:
            if existing.status == "running":
                self._register_active(existing.chat_run_id, request_fingerprint)
            return existing, False

        record = create_chat_run(
            trace_id=trace_id,
            session_id=session_id,
            client_turn_id=client_turn_id,
            request_fingerprint=request_fingerprint,
            endpoint=endpoint,
            tenant_id=tenant_id,
            user_id=user_id,
            company_id=company_id,
            request_payload=request_payload,
            base_dir=base_dir,
        )
        record_chat_run_event(
            record.chat_run_id,
            event_type="chat_run.created",
            payload={
                "endpoint": endpoint,
                "session_id": session_id,
                "pipeline_route": (request_payload or {}).get("pipeline_route"),
                "pipeline_variant": (request_payload or {}).get("pipeline_variant"),
                "shadow_pipeline_variant": (request_payload or {}).get("shadow_pipeline_variant"),
            },
            base_dir=base_dir,
        )
        self._register_active(record.chat_run_id, request_fingerprint)
        return record, True

    def _register_active(self, chat_run_id: str, request_fingerprint: str) -> _InFlightRun:
        with self._lock:
            active = self._active_by_run_id.get(chat_run_id)
            if active is None:
                active = _InFlightRun(chat_run_id=chat_run_id, request_fingerprint=request_fingerprint)
                self._active_by_run_id[chat_run_id] = active
                self._active_by_fingerprint[request_fingerprint] = active
            return active

    def wait_for_terminal(
        self,
        *,
        chat_run_id: str,
        timeout_seconds: float = 30.0,
        base_dir: Path = DEFAULT_CHAT_RUNS_DIR,
    ) -> tuple[str, dict[str, Any] | None]:
        deadline = time.monotonic() + max(0.1, float(timeout_seconds))
        while time.monotonic() < deadline:
            with self._lock:
                active = self._active_by_run_id.get(chat_run_id)
            if active is not None:
                with active.condition:
                    remaining = max(0.05, deadline - time.monotonic())
                    active.condition.wait(timeout=remaining)
                    if active.status == "completed":
                        return "completed", dict(active.terminal_payload or {})
                    if active.status == "failed":
                        return "failed", dict(active.terminal_error or {})
            record = load_chat_run(chat_run_id, base_dir=base_dir)
            if record is None:
                time.sleep(0.05)
                continue
            if record.status == "completed":
                return "completed", dict(record.response_payload or {})
            if record.status == "failed":
                return "failed", dict(record.error_payload or {})
            time.sleep(0.05)
        record = load_chat_run(chat_run_id, base_dir=base_dir)
        if record is not None:
            if record.status == "completed":
                return "completed", dict(record.response_payload or {})
            if record.status == "failed":
                return "failed", dict(record.error_payload or {})
        return "timeout", None

    def mark_pipeline_started(self, chat_run_id: str, *, base_dir: Path = DEFAULT_CHAT_RUNS_DIR) -> None:
        _mark_timestamp_once(chat_run_id, "pipeline_started_at", "chat_run.pipeline_started", base_dir=base_dir)

    def set_pipeline_run_id(
        self,
        chat_run_id: str,
        pipeline_run_id: str,
        *,
        pipeline_variant: str | None = None,
        pipeline_route: str | None = None,
        shadow_pipeline_variant: str | None = None,
        base_dir: Path = DEFAULT_CHAT_RUNS_DIR,
    ) -> None:
        update_chat_run(chat_run_id, base_dir=base_dir, pipeline_run_id=str(pipeline_run_id or "").strip() or None)
        payload = {"pipeline_run_id": pipeline_run_id}
        if str(pipeline_variant or "").strip():
            payload["pipeline_variant"] = str(pipeline_variant).strip()
        if str(pipeline_route or "").strip():
            payload["pipeline_route"] = str(pipeline_route).strip()
        if str(shadow_pipeline_variant or "").strip():
            payload["shadow_pipeline_variant"] = str(shadow_pipeline_variant).strip()
        record_chat_run_event(
            chat_run_id,
            event_type="chat_run.pipeline_linked",
            payload=payload,
            base_dir=base_dir,
        )

    def mark_first_model_delta(self, chat_run_id: str, *, base_dir: Path = DEFAULT_CHAT_RUNS_DIR) -> None:
        _mark_timestamp_once(chat_run_id, "first_model_delta_at", "chat_run.first_model_delta", base_dir=base_dir)

    def mark_first_visible_answer(self, chat_run_id: str, *, base_dir: Path = DEFAULT_CHAT_RUNS_DIR) -> None:
        _mark_timestamp_once(chat_run_id, "first_visible_answer_at", "chat_run.first_visible_answer", base_dir=base_dir)

    def mark_pipeline_completed(self, chat_run_id: str, *, base_dir: Path = DEFAULT_CHAT_RUNS_DIR) -> None:
        _mark_timestamp_once(chat_run_id, "pipeline_completed_at", "chat_run.pipeline_completed", base_dir=base_dir)

    def mark_final_payload_ready(self, chat_run_id: str, *, base_dir: Path = DEFAULT_CHAT_RUNS_DIR) -> None:
        _mark_timestamp_once(chat_run_id, "final_payload_ready_at", "chat_run.final_payload_ready", base_dir=base_dir)

    def mark_response_sent(self, chat_run_id: str, *, base_dir: Path = DEFAULT_CHAT_RUNS_DIR) -> None:
        _mark_timestamp_once(chat_run_id, "response_sent_at", "chat_run.response_sent", base_dir=base_dir)

    def mark_async_persistence_done(self, chat_run_id: str, *, base_dir: Path = DEFAULT_CHAT_RUNS_DIR) -> None:
        _mark_timestamp_once(chat_run_id, "async_persistence_done_at", "chat_run.async_persistence_done", base_dir=base_dir)

    def complete(
        self,
        chat_run_id: str,
        payload: dict[str, Any],
        *,
        base_dir: Path = DEFAULT_CHAT_RUNS_DIR,
    ) -> None:
        update_chat_run(
            chat_run_id,
            base_dir=base_dir,
            status="completed",
            response_payload=dict(payload or {}),
            completed_at=_timestamp(),
        )
        record_chat_run_event(chat_run_id, event_type="chat_run.completed", base_dir=base_dir)
        self._notify_terminal(chat_run_id, status="completed", payload=dict(payload or {}), base_dir=base_dir)

    def fail(
        self,
        chat_run_id: str,
        payload: dict[str, Any],
        *,
        base_dir: Path = DEFAULT_CHAT_RUNS_DIR,
    ) -> None:
        update_chat_run(
            chat_run_id,
            base_dir=base_dir,
            status="failed",
            error_payload=dict(payload or {}),
            completed_at=_timestamp(),
        )
        record_chat_run_event(chat_run_id, event_type="chat_run.failed", payload={"error": dict(payload or {})}, base_dir=base_dir)
        self._notify_terminal(chat_run_id, status="failed", payload=dict(payload or {}), base_dir=base_dir)

    def _notify_terminal(
        self,
        chat_run_id: str,
        *,
        status: str,
        payload: dict[str, Any],
        base_dir: Path,
    ) -> None:
        with self._lock:
            active = self._active_by_run_id.pop(chat_run_id, None)
            if active is not None:
                self._active_by_fingerprint.pop(active.request_fingerprint, None)
        if active is None:
            return
        with active.condition:
            active.status = status
            if status == "completed":
                active.terminal_payload = dict(payload)
            else:
                active.terminal_error = dict(payload)
            active.condition.notify_all()


def _timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _now_once(chat_run_id: str, field_name: str, base_dir: Path) -> str:
    record = load_chat_run(chat_run_id, base_dir=base_dir)
    if record is None:
        return _timestamp()
    existing = str(getattr(record, field_name, "") or "").strip()
    return existing or _timestamp()


def _mark_timestamp_once(
    chat_run_id: str,
    field_name: str,
    event_type: str,
    *,
    base_dir: Path,
) -> None:
    existing_record = load_chat_run(chat_run_id, base_dir=base_dir)
    if existing_record is None:
        return
    already_set = str(getattr(existing_record, field_name, "") or "").strip()
    timestamp = already_set or _timestamp()
    record = update_chat_run(chat_run_id, base_dir=base_dir, **{field_name: timestamp})
    if record is None:
        return
    if already_set:
        return
    record_chat_run_event(chat_run_id, event_type=event_type, base_dir=base_dir)


_shared_coordinator: ChatRunCoordinator | None = None
_shared_lock = threading.Lock()


def get_chat_run_coordinator() -> ChatRunCoordinator:
    global _shared_coordinator
    if _shared_coordinator is None:
        with _shared_lock:
            if _shared_coordinator is None:
                _shared_coordinator = ChatRunCoordinator()
    return _shared_coordinator


__all__ = [
    "ChatRunCoordinator",
    "build_chat_run_fingerprint",
    "get_chat_run_coordinator",
]
