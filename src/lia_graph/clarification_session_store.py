from __future__ import annotations

from pathlib import Path
from typing import Any

_STORE: dict[str, dict[str, Any]] = {}


def get_session_state(session_id: str, path: Path | None = None) -> dict[str, Any] | None:
    return dict(_STORE.get(str(session_id), {})) or None


def upsert_session_state(
    session_id: str,
    payload: dict[str, Any],
    path: Path | None = None,
) -> dict[str, Any]:
    _STORE[str(session_id)] = dict(payload or {})
    return dict(_STORE[str(session_id)])


def clear_session_state(session_id: str, path: Path | None = None) -> None:
    _STORE.pop(str(session_id), None)
