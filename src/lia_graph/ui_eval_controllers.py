from __future__ import annotations

from typing import Any

from ._compat import send_not_implemented


def handle_eval_get(handler: Any, *args: Any, **kwargs: Any) -> None:
    send_not_implemented(handler, feature="Eval GET")


def handle_eval_post(handler: Any, *args: Any, **kwargs: Any) -> None:
    send_not_implemented(handler, feature="Eval POST")


def handle_eval_patch(handler: Any, *args: Any, **kwargs: Any) -> None:
    send_not_implemented(handler, feature="Eval PATCH")


def handle_eval_delete(handler: Any, *args: Any, **kwargs: Any) -> None:
    send_not_implemented(handler, feature="Eval DELETE")

