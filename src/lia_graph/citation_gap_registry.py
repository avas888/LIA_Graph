from __future__ import annotations

from typing import Any


def list_citation_gaps(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    return []


def register_citation_gaps(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {"captured_count": 0, "captured_by_type": {}}

