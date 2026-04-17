from __future__ import annotations

from http import HTTPStatus
from typing import Any
from unittest.mock import patch
from urllib.parse import urlparse

import pytest

import lia_graph.user_management as _um_mod
from lia_graph.platform_auth import AuthContext, PlatformAuthError
from lia_graph.ui_user_management_controllers import (
    _resolve_public_base_url,
    handle_user_management_get,
    handle_user_management_post,
)


class _FakeHandler:
    def __init__(
        self,
        *,
        headers: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
        auth_context: AuthContext | None = None,
        auth_error: PlatformAuthError | None = None,
        request_origin: str | None = None,
    ) -> None:
        self.headers = headers or {}
        self.sent_json: list[tuple[int, dict[str, Any]]] = []
        self.sent_bytes: list[tuple[int, bytes, str]] = []
        self._payload = payload
        self._auth_context = auth_context
        self._auth_error = auth_error
        self._request_origin_value = request_origin

    def _send_json(
        self,
        status: int | HTTPStatus,
        payload: dict[str, Any],
        *,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        del extra_headers
        self.sent_json.append((int(status), payload))

    def _send_bytes(
        self,
        status: int | HTTPStatus,
        data: bytes,
        content_type: str,
        *,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        del extra_headers
        self.sent_bytes.append((int(status), data, content_type))

    def _read_json_payload(self, *, object_error: str | None = None, **_: Any) -> dict[str, Any] | None:
        del object_error
        return self._payload

    def _resolve_auth_context(self, *, required: bool = False, allow_public: bool = False) -> AuthContext:
        del required, allow_public
        if self._auth_error is not None:
            raise self._auth_error
        if self._auth_context is None:
            raise PlatformAuthError("Authorization Bearer requerido.", code="auth_required", http_status=401)
        return self._auth_context

    def _send_auth_error(self, exc: PlatformAuthError) -> None:
        self.sent_json.append(
            (
                exc.http_status,
                {
                    "ok": False,
                    "error": {
                        "code": exc.code,
                        "message": str(exc),
                    },
                },
            )
        )

    def _admin_tenant_scope(self, auth_context: AuthContext, requested_tenant_id: str | None = None) -> str | None:
        if auth_context.role not in {"tenant_admin", "platform_admin"}:
            raise PlatformAuthError(
                "Se requiere rol administrativo.",
                code="auth_role_forbidden",
                http_status=403,
            )
        if auth_context.role == "platform_admin":
            tenant_id = str(requested_tenant_id or "").strip()
            return tenant_id or None
        return auth_context.tenant_id

    def _request_origin(self) -> str | None:
        return self._request_origin_value


def _ctx(*, tenant_id: str = "tenant-dev", user_id: str = "usr_admin", role: str = "tenant_admin") -> AuthContext:
    return AuthContext(
        tenant_id=tenant_id,
        user_id=user_id,
        role=role,
        allowed_company_ids=(),
        active_company_id="",
    )


@pytest.fixture(autouse=True)
def _auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_PLATFORM_SIGNING_SECRET", "platform-secret")
    monkeypatch.delenv("LIA_PUBLIC_BASE_URL", raising=False)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)


def test_resolve_public_base_url_uses_dev_host_header() -> None:
    handler = _FakeHandler(headers={"Host": "localhost:8787"})
    assert _resolve_public_base_url(handler) == "http://localhost:8787"


def test_get_admin_users_lists_current_tenant_users() -> None:
    handler = _FakeHandler(auth_context=_ctx(role="tenant_admin", tenant_id="tenant-alpha"))
    with patch.object(_um_mod, "list_tenant_users", return_value=[{"user_id": "u1"}]) as mock_fn:
        handled = handle_user_management_get(
            handler,
            "/api/admin/users",
            urlparse("/api/admin/users?status=active"),
            deps={},
        )

    assert handled is True
    mock_fn.assert_called_once_with("tenant-alpha", status="active")
    assert handler.sent_json == [(HTTPStatus.OK, {"ok": True, "users": [{"user_id": "u1"}]})]


def test_get_admin_tenants_requires_platform_admin() -> None:
    handler = _FakeHandler(auth_context=_ctx(role="tenant_admin"))

    handled = handle_user_management_get(
        handler,
        "/api/admin/tenants",
        urlparse("/api/admin/tenants"),
        deps={},
    )

    assert handled is True
    status, payload = handler.sent_json[0]
    assert status == HTTPStatus.FORBIDDEN
    assert payload["error"]["code"] == "auth_role_forbidden"


def test_post_login_returns_access_token() -> None:
    handler = _FakeHandler(payload={"email": "admin@lia.dev", "password": "AlphaTemp#2026"})
    with patch.object(
        _um_mod,
        "authenticate_user",
        return_value={
            "requires_tenant_selection": False,
            "tenant_id": "tenant-dev",
            "user_id": "usr_admin_001",
            "role": "platform_admin",
            "email": "admin@lia.dev",
            "display_name": "Admin LIA",
        },
    ):
        handled = handle_user_management_post(handler, "/api/auth/login", deps={})

    assert handled is True
    status, payload = handler.sent_json[0]
    assert status == HTTPStatus.OK
    assert payload["ok"] is True
    assert payload["me"]["role"] == "platform_admin"
    assert isinstance(payload["access_token"], str)
    assert payload["access_token"]


def test_post_login_requires_tenant_selection_when_membership_is_ambiguous() -> None:
    handler = _FakeHandler(payload={"email": "usuario1@lia.dev", "password": "AlphaTemp#2026"})
    with patch.object(
        _um_mod,
        "authenticate_user",
        return_value={
            "requires_tenant_selection": True,
            "tenants": [
                {"tenant_id": "tenant-alpha", "display_name": "Alpha", "role": "tenant_user"},
                {"tenant_id": "tenant-beta", "display_name": "Beta", "role": "tenant_admin"},
            ],
        },
    ):
        handled = handle_user_management_post(handler, "/api/auth/login", deps={})

    assert handled is True
    status, payload = handler.sent_json[0]
    assert status == HTTPStatus.CONFLICT
    assert payload["code"] == "auth_tenant_selection_required"
    assert len(payload["tenants"]) == 2


def test_post_accept_invite_supports_auth_alias_and_token_field() -> None:
    handler = _FakeHandler(
        payload={
            "token": "invite_abc",
            "display_name": "Ana Garcia",
            "password": "StrongP@ssword123",
        }
    )
    with patch.object(
        _um_mod,
        "accept_invite",
        return_value={
            "tenant_id": "tenant-alpha",
            "user_id": "usr_usuario1",
            "role": "tenant_user",
            "display_name": "Ana Garcia",
            "email": "usuario1@lia.dev",
        },
    ) as mock_fn:
        handled = handle_user_management_post(handler, "/api/auth/accept-invite", deps={})

    assert handled is True
    mock_fn.assert_called_once_with("invite_abc", "Ana Garcia", password="StrongP@ssword123")
    status, payload = handler.sent_json[0]
    assert status == HTTPStatus.OK
    assert payload["ok"] is True
    assert payload["me"]["email"] == "usuario1@lia.dev"


def test_post_admin_invite_builds_invite_url_for_tenant_admin() -> None:
    handler = _FakeHandler(
        auth_context=_ctx(role="tenant_admin", tenant_id="tenant-dev", user_id="usr_admin_001"),
        payload={"email": "usuario10@lia.dev", "role": "tenant_user"},
    )
    with patch.object(
        _um_mod,
        "invite_user",
        return_value={
            "token_id": "invite_xyz",
            "email": "usuario10@lia.dev",
            "role": "tenant_user",
            "expires_at": "2026-04-17T00:00:00+00:00",
            "user_id": "usr_usuario10",
        },
    ) as mock_fn:
        with patch("lia_graph.ui_user_management_controllers._resolve_public_base_url", return_value="https://app.lia.dev"):
            handled = handle_user_management_post(handler, "/api/admin/users/invite", deps={})

    assert handled is True
    mock_fn.assert_called_once_with(
        "tenant-dev",
        "usuario10@lia.dev",
        role="tenant_user",
        invited_by="usr_admin_001",
    )
    status, payload = handler.sent_json[0]
    assert status == HTTPStatus.OK
    assert payload["invite"]["invite_url"] == "https://app.lia.dev/invite?token=invite_xyz"


def test_post_admin_invite_requires_tenant_scope_for_platform_admin() -> None:
    handler = _FakeHandler(
        auth_context=_ctx(role="platform_admin", tenant_id="tenant-dev"),
        payload={"email": "nuevo@lia.dev", "role": "tenant_user"},
    )

    handled = handle_user_management_post(handler, "/api/admin/users/invite", deps={})

    assert handled is True
    assert handler.sent_json[0][0] == HTTPStatus.BAD_REQUEST
    assert "tenant_id" in handler.sent_json[0][1]["error"]


def test_post_user_action_blocks_self_suspension() -> None:
    handler = _FakeHandler(auth_context=_ctx(user_id="usr_admin_001"))

    handled = handle_user_management_post(handler, "/api/admin/users/usr_admin_001/suspend", deps={})

    assert handled is True
    status, payload = handler.sent_json[0]
    assert status == HTTPStatus.FORBIDDEN
    assert "propia cuenta" in payload["error"]
