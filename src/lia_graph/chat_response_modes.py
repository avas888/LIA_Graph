from __future__ import annotations

from typing import Iterable

DEFAULT_RESPONSE_DEPTH = "auto"
ALLOWED_RESPONSE_DEPTHS = ("auto", "concise", "deep")

FIRST_RESPONSE_MODE_FAST_ACTION = "fast_action"
FIRST_RESPONSE_MODE_BALANCED_ACTION = "balanced_action"
DEFAULT_FIRST_RESPONSE_MODE = FIRST_RESPONSE_MODE_FAST_ACTION
ALLOWED_FIRST_RESPONSE_MODES = (
    FIRST_RESPONSE_MODE_FAST_ACTION,
    FIRST_RESPONSE_MODE_BALANCED_ACTION,
)


def normalize_enum(value: object, *, default: str, allowed: Iterable[str]) -> str:
    normalized = str(value or "").strip().lower() or default
    allowed_set = set(allowed)
    if normalized not in allowed_set:
        return default
    return normalized


def normalize_response_depth(value: object) -> str:
    return normalize_enum(
        value,
        default=DEFAULT_RESPONSE_DEPTH,
        allowed=ALLOWED_RESPONSE_DEPTHS,
    )


def normalize_first_response_mode(value: object) -> str:
    return normalize_enum(
        value,
        default=DEFAULT_FIRST_RESPONSE_MODE,
        allowed=ALLOWED_FIRST_RESPONSE_MODES,
    )


__all__ = [
    "ALLOWED_FIRST_RESPONSE_MODES",
    "ALLOWED_RESPONSE_DEPTHS",
    "DEFAULT_FIRST_RESPONSE_MODE",
    "DEFAULT_RESPONSE_DEPTH",
    "FIRST_RESPONSE_MODE_BALANCED_ACTION",
    "FIRST_RESPONSE_MODE_FAST_ACTION",
    "normalize_first_response_mode",
    "normalize_response_depth",
]
