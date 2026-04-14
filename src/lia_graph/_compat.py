from __future__ import annotations

from http import HTTPStatus
from typing import Any


def send_not_implemented(handler: Any, *, feature: str) -> None:
    payload = {
        "ok": False,
        "error": {
            "code": "not_implemented",
            "message": f"{feature} todavía no fue restaurado en LIA_Graph.",
        },
    }
    if hasattr(handler, "_send_json"):
        handler._send_json(HTTPStatus.NOT_IMPLEMENTED, payload)
        return
    raise NotImplementedError(payload["error"]["message"])

