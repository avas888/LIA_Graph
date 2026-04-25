"""Ingestion read + destructive-delete surfaces.

HTTP surface handled here:

* ``GET /api/corpora``                         — corpus catalog
* ``GET /api/ingestion/sessions``              — paginated session list
* ``GET /api/ingestion/sessions/{id}``         — single session read
* ``DELETE /api/ingestion/sessions/{id}``      — eject session (full artifact cleanup)
    with ``?force=true`` to override a processing guard.

State-mutating POSTs for ingestion (upload, classify, process, retry, stop,
auto-process, purge-and-replace) live in ``ui_write_controllers`` and are
filled in B9 of the granularization plan. They are intentionally not in this
module — keep the read/write split to preserve the architecture called out in
``docs/done/next/granularization_v1.md`` §Controller Surface Catalog.

Both the GET and DELETE paths require an admin-scope auth context. Public
visitors never reach these surfaces because ``_resolve_auth_context(required=True)``
is a chokepoint in ``handler``.
"""

from __future__ import annotations

import re
from http import HTTPStatus
from typing import Any
from urllib.parse import parse_qs, urlparse

from ._compat import send_not_implemented
from .platform_auth import PlatformAuthError


_INGESTION_SESSION_ROUTE_RE = re.compile(r"^/api/ingestion/sessions/([^/]+)$")
_INGESTION_DELETE_SESSION_ROUTE_RE = re.compile(r"^/api/ingestion/sessions/([^/]+)$")


def _require_ingestion_admin(handler: Any) -> None:
    auth_context = handler._resolve_auth_context(required=True)
    if auth_context.role not in {"tenant_admin", "platform_admin"}:
        raise PlatformAuthError(
            "Se requiere rol administrativo.",
            code="auth_role_forbidden",
            http_status=403,
        )


def handle_ingestion_get(
    handler: Any,
    path: str,
    parsed: Any,
    *,
    deps: dict[str, Any],
) -> bool:
    """Dispatch GET on ``/api/corpora`` + ``/api/ingestion/sessions*``.

    ``deps`` keys: ``ingestion_runtime``.
    """
    # Early no-match exits (prefix filter) to avoid auth prompts on the wrong surface.
    if not (path == "/api/corpora" or path.startswith("/api/ingestion/")):
        return False

    try:
        _require_ingestion_admin(handler)
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True

    ingestion_runtime = deps["ingestion_runtime"]

    if path == "/api/corpora":
        handler._send_json(
            HTTPStatus.OK,
            {"ok": True, **ingestion_runtime.get_corpora_payload()},
        )
        return True

    if path == "/api/ingestion/sessions":
        query = parse_qs(parsed.query)
        corpus = str((query.get("corpus") or [""])[0]).strip() or None
        limit_raw = str((query.get("limit") or ["20"])[0]).strip() or "20"
        try:
            limit = int(limit_raw)
        except ValueError:
            handler._send_json(
                HTTPStatus.BAD_REQUEST, {"error": "`limit` debe ser entero."}
            )
            return True
        sessions = [
            session.to_dict()
            for session in ingestion_runtime.list_sessions(corpus=corpus, limit=limit)
        ]
        handler._send_json(HTTPStatus.OK, {"ok": True, "sessions": sessions})
        return True

    match_session = _INGESTION_SESSION_ROUTE_RE.match(path)
    if match_session:
        session_id = match_session.group(1)
        try:
            session = ingestion_runtime.get_session(session_id)
        except KeyError:
            handler._send_json(HTTPStatus.NOT_FOUND, {"error": "session_not_found"})
            return True
        handler._send_json(HTTPStatus.OK, {"ok": True, "session": session.to_dict()})
        return True

    return False


def handle_ingestion_post(handler: Any, path: str, *args: Any, **kwargs: Any) -> bool:
    """POSTs flow through ``ui_write_controllers.handle_ingestion_post``.

    This passthrough exists only because ``ui_write_controllers`` currently
    re-delegates here (see L87). B9 will move the real POST logic into
    ``ui_write_controllers`` and collapse this stub. Until then, callers get
    a 501 so it's obvious when the real handler is needed.
    """
    del args, kwargs
    if not path.startswith("/api/ingestion"):
        return False
    try:
        _require_ingestion_admin(handler)
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True
    send_not_implemented(handler, feature="Ingestion POST")
    return True


def handle_ingestion_delete(
    handler: Any,
    path: str,
    *,
    deps: dict[str, Any],
) -> bool:
    """Dispatch DELETE on ``/api/ingestion/sessions/{id}``.

    Uses ``ingestion_runtime.eject_session`` for full corpus artifact cleanup.
    ``?force=true`` overrides the "session is processing" guard.

    ``deps`` keys: ``ingestion_runtime``.
    """
    match_session = _INGESTION_DELETE_SESSION_ROUTE_RE.match(path)
    if not match_session:
        return False

    try:
        _require_ingestion_admin(handler)
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True

    parsed = urlparse(handler.path)
    query = parse_qs(parsed.query)
    force = str((query.get("force") or [""])[0]).strip().lower() in ("true", "1")

    ingestion_runtime = deps["ingestion_runtime"]
    session_id = match_session.group(1)
    try:
        result = ingestion_runtime.eject_session(session_id, force=force)
    except KeyError:
        handler._send_json(HTTPStatus.NOT_FOUND, {"error": "session_not_found"})
        return True
    except RuntimeError as exc:
        if str(exc) == "session_processing":
            handler._send_json(
                HTTPStatus.CONFLICT,
                {
                    "error": "session_processing",
                    "details": (
                        "No se puede eliminar la sesión mientras está en proceso. "
                        "Use ?force=true."
                    ),
                },
            )
            return True
        handler._send_json(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {"error": "eject_session_error", "details": str(exc)},
        )
        return True
    handler._send_json(HTTPStatus.OK, {"ok": True, **result})
    return True
