"""Module-level helper functions for `ui_server`.

Extracted during decouplingv1 Phase 1 alongside `ui_server_constants`.
Holds the small set of helpers that wrap `instrumentation.emit_event` with
our audit-log paths, plus the dev-reload watcher shim that delegates into
`ui_dev_reload`.

No circular-import risk: this module imports from `ui_server_constants`
and `instrumentation` only, never from `ui_server` itself.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import ui_dev_reload as _ui_dev_reload
from .instrumentation import emit_event

from .ui_server_constants import (
    API_AUDIT_LOG_PATH,
    FRONTEND_DIR,
    SERVER_STARTED_AT,
    UI_DIR,
    VERBOSE_CHAT_LOG_PATH,
    WORKSPACE_ROOT,
)


def _emit_audit_event(event_type: str, payload: dict[str, Any]) -> None:
    emit_event(event_type, payload)
    emit_event(event_type, payload, log_path=API_AUDIT_LOG_PATH)


def _emit_chat_verbose_event(event_type: str, payload: dict[str, Any]) -> None:
    _emit_audit_event(event_type, payload)
    emit_event(event_type, payload, log_path=VERBOSE_CHAT_LOG_PATH)


def _best_effort_git_commit() -> str:
    return _ui_dev_reload._best_effort_git_commit(WORKSPACE_ROOT)


def _build_info_payload() -> dict[str, Any]:
    return _ui_dev_reload._build_info_payload(
        server_started_at=SERVER_STARTED_AT,
        workspace_root=WORKSPACE_ROOT,
        ui_dir=UI_DIR,
        frontend_dir=FRONTEND_DIR,
    )


def _build_reload_snapshot(roots: tuple[Path, ...]) -> tuple[tuple[str, int, int], ...]:
    return _ui_dev_reload._build_reload_snapshot(roots)


def _start_reload_watcher(
    *,
    server,
    watch_roots: tuple[Path, ...],
    interval_seconds: float,
):
    return _ui_dev_reload._start_reload_watcher(
        server=server,
        watch_roots=watch_roots,
        interval_seconds=interval_seconds,
        emit_audit_event=_emit_audit_event,
    )


__all__ = [
    "_emit_audit_event",
    "_emit_chat_verbose_event",
    "_best_effort_git_commit",
    "_build_info_payload",
    "_build_reload_snapshot",
    "_start_reload_watcher",
]
