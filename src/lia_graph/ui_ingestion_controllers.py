from __future__ import annotations

from typing import Any

from ._compat import send_not_implemented
from .platform_auth import PlatformAuthError


def _require_ingestion_admin(handler: Any) -> None:
    auth_context = handler._resolve_auth_context(required=True)
    if auth_context.role not in {"tenant_admin", "platform_admin"}:
        raise PlatformAuthError(
            "Se requiere rol administrativo.",
            code="auth_role_forbidden",
            http_status=403,
        )


def _handle_ingestion_stub(handler: Any, path: str, *, feature: str) -> bool:
    if not path.startswith("/api/ingestion"):
        return False
    try:
        _require_ingestion_admin(handler)
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True
    send_not_implemented(handler, feature=feature)
    return True


def handle_ingestion_get(handler: Any, path: str, *args: Any, **kwargs: Any) -> bool:
    del args, kwargs
    return _handle_ingestion_stub(handler, path, feature="Ingestion GET")


def handle_ingestion_post(handler: Any, path: str, *args: Any, **kwargs: Any) -> bool:
    del args, kwargs
    return _handle_ingestion_stub(handler, path, feature="Ingestion")


def handle_ingestion_delete(handler: Any, path: str, *args: Any, **kwargs: Any) -> bool:
    del args, kwargs
    return _handle_ingestion_stub(handler, path, feature="Ingestion DELETE")
