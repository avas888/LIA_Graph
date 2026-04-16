from __future__ import annotations

from http import HTTPStatus
from typing import Any
from urllib.parse import urlparse

from ._compat import send_not_implemented


def handle_runtime_terms_get(handler: Any, path: str, *args: Any, **kwargs: Any) -> bool:
    if not (
        path.startswith("/api/runtime/terms")
        or path.startswith("/api/terms")
    ):
        return False
    send_not_implemented(handler, feature="Runtime terms GET")
    return True


def handle_orchestration_settings_put(handler: Any, *args: Any, **kwargs: Any) -> None:
    path = (urlparse(getattr(handler, "path", "")).path or "/").rstrip("/") or "/"
    if path != "/api/orchestration/settings":
        handler._send_json(HTTPStatus.NOT_FOUND, {"error": "Endpoint no encontrado."})
        return
    send_not_implemented(handler, feature="Orchestration settings PUT")
