"""Controllers for user and tenant management endpoints."""

from __future__ import annotations

import logging
import os
import re
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .platform_auth import AuthContext, PlatformAuthError, issue_access_token
from .runtime_env import is_production_like_env

_USER_ACTION_RE = re.compile(r"^/api/admin/users/([^/]+)/(suspend|reactivate|delete)$")
_SAFE_HOST_RE = re.compile(r"^[A-Za-z0-9.-]+(?::\d+)?$")
_UI_DIR = Path(__file__).resolve().parents[2] / "ui"

_LOGIN_PAGE_HTML = """<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Login — LIA</title></head><body><main><h1>Iniciar sesión</h1></main></body></html>"""
_INVITE_PAGE_HTML = """<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Invite — LIA</title></head><body><main><h1>Aceptar invitación</h1></main></body></html>"""

_log = logging.getLogger(__name__)


def _issue_login_token(*, tenant_id: str, user_id: str, role: str) -> str:
    return issue_access_token(
        AuthContext(
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
            allowed_company_ids=(),
            active_company_id="",
        )
    )


def _resolve_public_base_url(handler: Any) -> str:
    configured = str(os.getenv("LIA_PUBLIC_BASE_URL", "")).strip().rstrip("/")
    if configured:
        parsed = urlparse(configured)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return configured
        raise ValueError("`LIA_PUBLIC_BASE_URL` debe ser un URL http(s) válido.")

    request_origin = str(handler._request_origin() or "").strip().rstrip("/")
    if request_origin:
        parsed = urlparse(request_origin)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return request_origin

    host_header = str(handler.headers.get("Host", "")).strip()
    if not is_production_like_env() and _SAFE_HOST_RE.match(host_header):
        return f"http://{host_header}"

    raise ValueError(
        "Configurar `LIA_PUBLIC_BASE_URL` para generar links de acceso en staging/production."
    )


def _serve_built_html(handler: Any, filename: str, fallback_html: str) -> None:
    built_path = _UI_DIR / filename
    if built_path.is_file():
        try:
            handler._send_bytes(HTTPStatus.OK, built_path.read_bytes(), "text/html; charset=utf-8")
            return
        except OSError:
            pass
    handler._send_bytes(HTTPStatus.OK, fallback_html.encode("utf-8"), "text/html; charset=utf-8")


def handle_user_management_get(handler: Any, path: str, parsed: Any, *, deps: dict[str, Any]) -> bool:
    del deps
    if path in {"/login", "/login.html"}:
        _serve_built_html(handler, "login.html", _LOGIN_PAGE_HTML)
        return True

    if path in {"/invite", "/invite.html"}:
        _serve_built_html(handler, "invite.html", _INVITE_PAGE_HTML)
        return True

    if path == "/api/admin/users":
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

        if not tenant_scope:
            handler._send_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "error": "Se requiere tenant_id."},
            )
            return True

        from . import user_management

        query = parse_qs(parsed.query)
        status_filter = str((query.get("status") or [""])[0]).strip() or None
        users = user_management.list_tenant_users(tenant_scope, status=status_filter)
        handler._send_json(HTTPStatus.OK, {"ok": True, "users": users})
        return True

    if path == "/api/admin/tenants":
        try:
            auth_context = handler._resolve_auth_context(required=True)
            if auth_context.role != "platform_admin":
                raise PlatformAuthError(
                    "Se requiere rol platform_admin.",
                    code="auth_role_forbidden",
                    http_status=403,
                )
        except PlatformAuthError as exc:
            handler._send_auth_error(exc)
            return True

        from . import user_management

        tenants = user_management.list_tenants(include_members=True)
        handler._send_json(HTTPStatus.OK, {"ok": True, "tenants": tenants})
        return True

    if path == "/api/admin/invites":
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

        if not tenant_scope:
            handler._send_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "error": "Se requiere tenant_id."},
            )
            return True

        from . import user_management

        query = parse_qs(parsed.query)
        status_filter = str((query.get("status") or [""])[0]).strip() or None
        invites = user_management.list_invites(tenant_scope, status=status_filter)
        handler._send_json(HTTPStatus.OK, {"ok": True, "invites": invites})
        return True

    return False


def handle_user_management_post(handler: Any, path: str, *, deps: dict[str, Any]) -> bool:
    del deps
    if path == "/api/auth/login":
        payload = handler._read_json_payload(object_error="Se requiere un objeto JSON.")
        if payload is None:
            return True

        email = str(payload.get("email", "")).strip().lower()
        password = str(payload.get("password", ""))
        tenant_id = str(payload.get("tenant_id", "")).strip() or None
        if not email or "@" not in email:
            handler._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "Correo inválido."})
            return True
        if not password:
            handler._send_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "error": "Se requiere contraseña."},
            )
            return True

        client_ip = str(getattr(handler, "client_address", ("",))[0] or "").strip()
        client_ua = str(handler.headers.get("User-Agent", "")) if hasattr(handler, "headers") else ""
        from .login_audit import record_login_event

        try:
            from . import user_management

            auth_result = user_management.authenticate_user(email, password, tenant_id=tenant_id)
            if auth_result.get("requires_tenant_selection"):
                handler._send_json(
                    HTTPStatus.CONFLICT,
                    {
                        "ok": False,
                        "code": "auth_tenant_selection_required",
                        "error": "Este correo pertenece a múltiples tenants. Seleccione el tenant para continuar.",
                        "tenants": auth_result.get("tenants", []),
                    },
                )
                return True

            access_token = _issue_login_token(
                tenant_id=str(auth_result["tenant_id"]),
                user_id=str(auth_result["user_id"]),
                role=str(auth_result["role"]),
            )

            record_login_event(
                email=email,
                status="success",
                user_id=str(auth_result["user_id"]),
                tenant_id=str(auth_result["tenant_id"]),
                ip_address=client_ip,
                user_agent=client_ua,
            )

            handler._send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "access_token": access_token,
                    "me": {
                        "tenant_id": auth_result["tenant_id"],
                        "user_id": auth_result["user_id"],
                        "role": auth_result["role"],
                        "display_name": auth_result.get("display_name", ""),
                        "email": auth_result.get("email", email),
                    },
                },
            )
        except ValueError as exc:
            record_login_event(
                email=email,
                status="failure",
                failure_reason=str(exc),
                ip_address=client_ip,
                user_agent=client_ua,
            )
            handler._send_json(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": str(exc)})
        except PlatformAuthError as exc:
            handler._send_json(exc.http_status, {"ok": False, "error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            _log.exception("Login failed: %s", exc)
            handler._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": "Error interno."})
        return True

    if path in {"/api/invite/accept", "/api/auth/accept-invite"}:
        payload = handler._read_json_payload(object_error="Se requiere un objeto JSON.")
        if payload is None:
            return True

        token_id = str(payload.get("token") or payload.get("token_id") or "").strip()
        display_name = str(payload.get("display_name", "")).strip()
        password = str(payload.get("password", ""))
        if not token_id:
            handler._send_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "error": "Se requiere token_id."},
            )
            return True
        if not password:
            handler._send_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "error": "Se requiere contraseña."},
            )
            return True

        from . import user_management

        try:
            result = user_management.accept_invite(token_id, display_name, password=password)
        except ValueError as exc:
            handler._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
            return True
        except Exception:  # noqa: BLE001
            handler._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"ok": False, "error": "Error interno al aceptar invitación."},
            )
            return True

        try:
            access_token = _issue_login_token(
                tenant_id=str(result["tenant_id"]),
                user_id=str(result["user_id"]),
                role=str(result["role"]),
            )
        except PlatformAuthError as exc:
            handler._send_json(exc.http_status, {"ok": False, "error": str(exc)})
            return True

        handler._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "access_token": access_token,
                "me": {
                    "tenant_id": result["tenant_id"],
                    "user_id": result["user_id"],
                    "role": result["role"],
                    "display_name": result.get("display_name", ""),
                    "email": result.get("email", ""),
                },
                "message": "Acceso activado. Redireccionando...",
            },
        )
        return True

    if path == "/api/admin/users/invite":
        try:
            auth_context = handler._resolve_auth_context(required=True)
            tenant_scope = handler._admin_tenant_scope(auth_context)
        except PlatformAuthError as exc:
            handler._send_auth_error(exc)
            return True

        payload = handler._read_json_payload(object_error="Se requiere un objeto JSON.")
        if payload is None:
            return True

        email = str(payload.get("email", "")).strip().lower()
        role = str(payload.get("role", "tenant_user")).strip() or "tenant_user"
        target_tenant = str(payload.get("tenant_id", "")).strip() or tenant_scope
        if auth_context.role != "platform_admin":
            target_tenant = tenant_scope
        if not target_tenant:
            handler._send_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "error": "Se requiere tenant_id."},
            )
            return True
        if not email or "@" not in email:
            handler._send_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "error": "Se requiere un correo electrónico válido."},
            )
            return True

        from . import user_management

        try:
            invite = user_management.invite_user(
                target_tenant,
                email,
                role=role,
                invited_by=auth_context.user_id,
            )
            base_url = _resolve_public_base_url(handler)
        except ValueError as exc:
            handler._send_json(HTTPStatus.CONFLICT, {"ok": False, "error": str(exc)})
            return True
        except Exception as exc:  # noqa: BLE001
            _log.exception("Failed to create invite: %s", exc)
            handler._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"ok": False, "error": "Error al crear invitación."},
            )
            return True

        invite_url = f"{base_url}/invite?token={invite['token_id']}"
        handler._send_json(HTTPStatus.OK, {"ok": True, "invite": {**invite, "invite_url": invite_url}})
        return True

    match = _USER_ACTION_RE.match(path)
    if match:
        user_id = match.group(1)
        action = match.group(2)
        try:
            auth_context = handler._resolve_auth_context(required=True)
            tenant_scope = handler._admin_tenant_scope(auth_context)
        except PlatformAuthError as exc:
            handler._send_auth_error(exc)
            return True

        if not tenant_scope:
            handler._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "Se requiere tenant_id."})
            return True
        if user_id == auth_context.user_id:
            handler._send_json(
                HTTPStatus.FORBIDDEN,
                {"ok": False, "error": "No puede realizar esta acción sobre su propia cuenta."},
            )
            return True

        from . import user_management

        try:
            if action == "suspend":
                result = user_management.suspend_user(tenant_scope, user_id)
            elif action == "reactivate":
                result = user_management.reactivate_user(tenant_scope, user_id)
            else:
                payload = handler._read_json_payload(object_error="Se requiere un objeto JSON.")
                if payload is None:
                    return True
                if not payload.get("confirm"):
                    handler._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {"ok": False, "error": "Se requiere confirmación (confirm: true)."},
                    )
                    return True
                result = user_management.delete_user_from_tenant(tenant_scope, user_id)
        except ValueError as exc:
            handler._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
            return True
        except Exception:  # noqa: BLE001
            handler._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"ok": False, "error": f"Error al {action} usuario."},
            )
            return True

        handler._send_json(HTTPStatus.OK, {"ok": True, **result})
        return True

    if path == "/api/admin/tenants":
        try:
            auth_context = handler._resolve_auth_context(required=True)
            if auth_context.role != "platform_admin":
                raise PlatformAuthError(
                    "Se requiere rol platform_admin.",
                    code="auth_role_forbidden",
                    http_status=403,
                )
        except PlatformAuthError as exc:
            handler._send_auth_error(exc)
            return True

        payload = handler._read_json_payload(object_error="Se requiere un objeto JSON.")
        if payload is None:
            return True

        display_name = str(payload.get("display_name", "")).strip()
        if not display_name:
            handler._send_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "error": "Se requiere display_name."},
            )
            return True

        from . import user_management

        try:
            tenant = user_management.create_tenant(display_name, metadata=payload.get("metadata"))
        except Exception:  # noqa: BLE001
            handler._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"ok": False, "error": "Error al crear tenant."},
            )
            return True

        handler._send_json(HTTPStatus.OK, {"ok": True, "tenant": tenant})
        return True

    return False
