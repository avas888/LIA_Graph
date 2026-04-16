from __future__ import annotations

from typing import Any

from ._compat import send_not_implemented


def handle_ingestion_get(handler: Any, path: str, *args: Any, **kwargs: Any) -> bool:
    if not path.startswith("/api/ingestion"):
        return False
    send_not_implemented(handler, feature="Ingestion GET")
    return True


def handle_ingestion_delete(handler: Any, path: str, *args: Any, **kwargs: Any) -> bool:
    if not path.startswith("/api/ingestion"):
        return False
    send_not_implemented(handler, feature="Ingestion DELETE")
    return True
