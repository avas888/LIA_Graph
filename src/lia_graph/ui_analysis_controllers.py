from __future__ import annotations

from typing import Any

from ._compat import send_not_implemented


def handle_analysis_post(handler: Any, *args: Any, **kwargs: Any) -> None:
    send_not_implemented(handler, feature="Análisis")

