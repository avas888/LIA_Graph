from __future__ import annotations

from typing import Any

COMPARATIVE_FIELD_QUESTIONS: tuple[str, ...] = ()
CLARIFICATION_STATE_VERSION = 1


def advance_state(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return dict(kwargs.get("state") or {})


def build_requirements_for_error(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    return []


def build_interaction_payload(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {"route": "none", "questions": []}


def build_user_message_for_question(*args: Any, **kwargs: Any) -> str:
    return ""


def is_semantic_422_error(code: str | None) -> bool:
    return str(code or "").strip().lower().startswith("semantic_422")


def refresh_state_from_semantic_error(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return dict(kwargs.get("state") or {})


def should_intercept_state(*args: Any, **kwargs: Any) -> bool:
    return False


def _llm_dynamic_clarification_decider(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {"should_clarify": False}


def _llm_semantic_requirements_decider(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    return []


def _resolve_guided_clarification_requirements(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    return []


def _build_clarification_error_payload(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {"ok": False, "error": {"code": "clarification_unavailable"}}

