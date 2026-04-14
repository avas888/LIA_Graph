from __future__ import annotations

from typing import Any

from ._compat import send_not_implemented


def handle_user_management_get(handler: Any, *args: Any, **kwargs: Any) -> None:
    send_not_implemented(handler, feature="User management GET")


def handle_user_management_post(handler: Any, *args: Any, **kwargs: Any) -> None:
    send_not_implemented(handler, feature="User management POST")

