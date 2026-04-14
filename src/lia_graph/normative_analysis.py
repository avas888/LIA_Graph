from __future__ import annotations

from typing import Any


def build_normative_analysis_payload(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {"ok": False, "error": {"code": "normative_analysis_unavailable"}}

