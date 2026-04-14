from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GuideChatRequest:
    question: str
    reference_key: str | None = None


def build_guide_markdown_for_pdf(*args: Any, **kwargs: Any) -> str:
    return ""


def find_official_form_pdf_source(*args: Any, **kwargs: Any) -> dict[str, Any] | None:
    return None


def list_available_guides(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    return []


def resolve_guide(*args: Any, **kwargs: Any) -> dict[str, Any] | None:
    return None


def run_guide_chat(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {"ok": False, "error": {"code": "form_guide_unavailable"}}

