from __future__ import annotations

from typing import Any

from ._compat import send_not_implemented


def handle_platform_get(handler: Any, path: str, *args: Any, **kwargs: Any) -> bool:
    if not (path.startswith("/api/platform") or path.startswith("/api/admin")):
        return False
    send_not_implemented(handler, feature="Platform GET")
    return True
