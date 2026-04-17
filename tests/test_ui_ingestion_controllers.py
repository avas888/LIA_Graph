from __future__ import annotations

from http import HTTPStatus
from typing import Any

from lia_graph.platform_auth import AuthContext, PlatformAuthError
from lia_graph.ui_ingestion_controllers import handle_ingestion_get, handle_ingestion_post


class _FakeHandler:
    def __init__(self, auth_context: AuthContext | None = None, auth_error: PlatformAuthError | None = None) -> None:
        self._auth_context = auth_context
        self._auth_error = auth_error
        self.sent_json: list[tuple[int, dict[str, Any]]] = []

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

    def _send_json(
        self,
        status: int | HTTPStatus,
        payload: dict[str, Any],
        *,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        del extra_headers
        self.sent_json.append((int(status), payload))


def _ctx(role: str) -> AuthContext:
    return AuthContext(
        tenant_id="tenant-dev",
        user_id="usr_test",
        role=role,
        allowed_company_ids=(),
        active_company_id="",
    )


def test_ingestion_routes_require_admin_authentication() -> None:
    handler = _FakeHandler()

    handled = handle_ingestion_get(handler, "/api/ingestion/sessions")

    assert handled is True
    status, payload = handler.sent_json[0]
    assert status == HTTPStatus.UNAUTHORIZED
    assert payload["error"]["code"] == "auth_required"


def test_ingestion_routes_reject_tenant_users_but_allow_admin_stub_response() -> None:
    tenant_user_handler = _FakeHandler(auth_context=_ctx("tenant_user"))
    tenant_admin_handler = _FakeHandler(auth_context=_ctx("tenant_admin"))

    tenant_user_handled = handle_ingestion_post(tenant_user_handler, "/api/ingestion/preflight")
    tenant_admin_handled = handle_ingestion_post(tenant_admin_handler, "/api/ingestion/preflight")

    assert tenant_user_handled is True
    assert tenant_admin_handled is True
    assert tenant_user_handler.sent_json[0][0] == HTTPStatus.FORBIDDEN
    assert tenant_user_handler.sent_json[0][1]["error"]["code"] == "auth_role_forbidden"
    assert tenant_admin_handler.sent_json[0][0] == HTTPStatus.NOT_IMPLEMENTED
    assert tenant_admin_handler.sent_json[0][1]["error"]["code"] == "not_implemented"
