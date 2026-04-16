from __future__ import annotations

from typing import Any

from ._compat import send_not_implemented


def handle_user_management_get(handler: Any, path: str, *args: Any, **kwargs: Any) -> bool:
    if not (
        path == "/api/admin/users"
        or path == "/api/admin/tenants"
        or path.startswith("/api/admin/users/")
    ):
        return False
    send_not_implemented(handler, feature="User management GET")
    return True


def handle_user_management_post(handler: Any, path: str, *args: Any, **kwargs: Any) -> bool:
    if not (
        path in {"/api/auth/accept-invite", "/api/invite/accept", "/api/admin/users/invite"}
        or path.startswith("/api/admin/users/")
    ):
        return False
    send_not_implemented(handler, feature="User management POST")
    return True
