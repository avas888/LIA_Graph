"""Conversation + history read surfaces extracted from ``ui_server.LiaUIHandler``.

HTTP surface handled here:

* ``GET /api/conversation/{session_id}``    — single session read
* ``GET /api/conversations/topics``         — distinct topics per tenant/user
* ``GET /api/conversations``                — paginated session listing with admin
                                              enrichment (display names)
* ``GET /api/contributions/pending``        — admin queue of pending contributions

NOTE: ``GET /api/feedback`` is NOT handled here. In Lia_Graph it is served by
``ui_frontend_compat_controllers.handle_chat_frontend_compat_get`` earlier in the
dispatch chain (``ui_server.do_GET``). Do not re-add it here without also
updating the dispatcher ordering or the frontend contract.

All dep-injected collaborators flow through ``deps``; auth resolution and error
mapping live on the ``handler`` (``_resolve_auth_context``, ``_send_auth_error``,
``_admin_tenant_scope``). See ``docs/done/next/granularization_v1.md`` §Controller
Surface Catalog for the architecture rules.
"""

from __future__ import annotations

import re
from http import HTTPStatus
from typing import Any
from urllib.parse import parse_qs

from .platform_auth import PlatformAuthError


_CONVERSATION_SESSION_ROUTE_RE = re.compile(r"^/api/conversation/([^/]+)$")


def handle_history_get(
    handler: Any,
    path: str,
    parsed: Any,
    *,
    deps: dict[str, Any],
) -> bool:
    """Dispatch GET requests on ``/api/conversation*`` and ``/api/contributions/pending``.

    ``deps`` keys: ``load_session``, ``list_sessions``, ``list_distinct_topics``,
    ``list_contributions``, ``conversations_path``, ``workspace_root``.
    (``load_feedback`` and ``feedback_path`` are passed by the dispatcher for
    backwards-compat but not consumed here — see module docstring.)
    """
    conv_match = _CONVERSATION_SESSION_ROUTE_RE.match(path)
    if conv_match:
        return _handle_conversation_get(handler, conv_match.group(1), parsed, deps)

    if path == "/api/conversations/topics":
        return _handle_conversations_topics_get(handler, parsed, deps)

    if path == "/api/conversations":
        return _handle_conversations_list_get(handler, parsed, deps)

    if path == "/api/contributions/pending":
        return _handle_contributions_pending_get(handler, parsed, deps)

    return False


def _handle_conversation_get(
    handler: Any,
    session_id: str,
    parsed: Any,
    deps: dict[str, Any],
) -> bool:
    query = parse_qs(parsed.query)
    try:
        auth_context = handler._resolve_auth_context(required=False)
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True
    if auth_context is None:
        handler._send_json(HTTPStatus.UNAUTHORIZED, {"error": "Autenticacion requerida."})
        return True
    query_tenant = str((query.get("tenant_id") or [""])[0]).strip()
    is_platform_admin = auth_context.role == "platform_admin"
    tenant_id = (
        (query_tenant if is_platform_admin and query_tenant else None)
        or auth_context.tenant_id
    )
    if not tenant_id:
        handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "`tenant_id` requerido."})
        return True
    is_admin = auth_context.role in ("platform_admin", "tenant_admin")
    session = deps["load_session"](
        tenant_id=tenant_id,
        session_id=session_id,
        user_id=None if is_admin else auth_context.user_id,
        company_id=None if is_admin else auth_context.active_company_id,
        base_dir=deps["conversations_path"],
    )
    if session is None:
        handler._send_json(HTTPStatus.NOT_FOUND, {"error": "session_not_found"})
        return True
    handler._send_json(HTTPStatus.OK, {"ok": True, "session": session.to_dict()})
    return True


def _handle_conversations_topics_get(
    handler: Any,
    parsed: Any,
    deps: dict[str, Any],
) -> bool:
    query = parse_qs(parsed.query)
    try:
        auth_context = handler._resolve_auth_context(required=False)
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True
    if auth_context is None:
        handler._send_json(HTTPStatus.UNAUTHORIZED, {"error": "Autenticacion requerida."})
        return True
    query_tenant = str((query.get("tenant_id") or [""])[0]).strip()
    is_platform_admin = auth_context.role == "platform_admin"
    all_tenants_topics = is_platform_admin and query_tenant == "__all__"
    tenant_id = (
        None
        if all_tenants_topics
        else (query_tenant if is_platform_admin and query_tenant else None)
        or auth_context.tenant_id
    )
    if not tenant_id and not all_tenants_topics:
        handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "`tenant_id` requerido."})
        return True
    status_filter = str((query.get("status") or [""])[0]).strip() or None
    is_admin = auth_context.role in ("platform_admin", "tenant_admin")
    topics = deps["list_distinct_topics"](
        tenant_id=tenant_id,
        user_id=None if is_admin else auth_context.user_id,
        company_id=None if is_admin else auth_context.active_company_id,
        status=status_filter,
        base_dir=deps["conversations_path"],
    )
    handler._send_json(HTTPStatus.OK, {"ok": True, "topics": topics})
    return True


def _handle_conversations_list_get(
    handler: Any,
    parsed: Any,
    deps: dict[str, Any],
) -> bool:
    query = parse_qs(parsed.query)
    try:
        auth_context = handler._resolve_auth_context(required=False)
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True
    if auth_context is None:
        handler._send_json(HTTPStatus.UNAUTHORIZED, {"error": "Autenticacion requerida."})
        return True
    query_tenant = str((query.get("tenant_id") or [""])[0]).strip()
    is_platform_admin = auth_context.role == "platform_admin"
    # platform_admin can query any tenant via ?tenant_id= override; special value
    # "__all__" queries across all tenants.
    all_tenants = is_platform_admin and query_tenant == "__all__"
    tenant_id = (
        None
        if all_tenants
        else (query_tenant if is_platform_admin and query_tenant else None)
        or auth_context.tenant_id
    )
    if not tenant_id and not all_tenants:
        handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "`tenant_id` requerido."})
        return True
    limit_raw = str((query.get("limit") or ["10"])[0]).strip()
    try:
        limit = min(int(limit_raw), 50)
    except ValueError:
        limit = 10
    offset_raw = str((query.get("offset") or ["0"])[0]).strip()
    try:
        offset = max(int(offset_raw), 0)
    except ValueError:
        offset = 0
    topic_filter = str((query.get("topic") or [""])[0]).strip() or None
    status_filter = str((query.get("status") or [""])[0]).strip() or None
    is_admin = auth_context.role in ("platform_admin", "tenant_admin")
    query_user_id = str((query.get("user_id") or [""])[0]).strip() or None
    effective_user_id = (
        query_user_id
        if is_admin and query_user_id
        else (None if is_admin else auth_context.user_id)
    )
    sessions = deps["list_sessions"](
        tenant_id=tenant_id,
        user_id=effective_user_id,
        company_id=None if is_admin else auth_context.active_company_id,
        base_dir=deps["conversations_path"],
        limit=limit,
        topic=topic_filter,
        offset=offset,
        status=status_filter,
    )
    if is_admin and sessions:
        try:
            from .user_management import list_tenant_users

            if all_tenants:
                seen_tenants: set[str] = {s.get("tenant_id", "") for s in sessions}
                name_map: dict[str, str] = {}
                for tid in seen_tenants:
                    if tid:
                        for u in list_tenant_users(tid):
                            name_map[u["user_id"]] = (
                                u.get("display_name") or u.get("email", "")
                            )
            else:
                users = list_tenant_users(tenant_id)  # type: ignore[arg-type]
                name_map = {
                    u["user_id"]: u.get("display_name") or u.get("email", "")
                    for u in users
                }
            for s in sessions:
                uid = s.get("user_id", "")
                if uid and uid in name_map:
                    s["user_display_name"] = name_map[uid]
        except Exception:
            # Graceful fallback: cards show user_id raw.
            pass
    handler._send_json(HTTPStatus.OK, {"ok": True, "sessions": sessions})
    return True


def _handle_contributions_pending_get(
    handler: Any,
    parsed: Any,
    deps: dict[str, Any],
) -> bool:
    try:
        auth_context = handler._resolve_auth_context(required=True)
        query = parse_qs(parsed.query)
        tenant_scope = handler._admin_tenant_scope(
            auth_context,
            requested_tenant_id=str((query.get("tenant_id") or [""])[0]).strip() or None,
        )
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True
    query = parse_qs(parsed.query)
    limit_raw = str((query.get("limit") or ["50"])[0]).strip()
    try:
        limit = min(int(limit_raw), 100)
    except ValueError:
        limit = 50
    records = deps["list_contributions"](
        status="pending",
        base_dir=deps["workspace_root"] / "artifacts" / "contributions",
        limit=limit,
        tenant_id=tenant_scope,
    )
    handler._send_json(HTTPStatus.OK, {"ok": True, "contributions": records})
    return True
