from __future__ import annotations

from typing import Any

_SETTINGS: dict[str, Any] = {}


class OrchestrationSettingsInvalidError(ValueError):
    pass


def load_orchestration_settings(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return dict(_SETTINGS)


def update_orchestration_settings(payload: dict[str, Any] | None = None, *args: Any, **kwargs: Any) -> dict[str, Any]:
    if payload is not None and not isinstance(payload, dict):
        raise OrchestrationSettingsInvalidError("Settings payload must be a dict.")
    if payload:
        _SETTINGS.update(payload)
    return dict(_SETTINGS)

