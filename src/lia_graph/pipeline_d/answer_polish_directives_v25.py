"""fix_v25_may.md — polish-prompt directive builders for v25 phases.

Granularized per operator directive 2026-05-17 PM: "granuralize polish.py
if over 1000 loc per artifact". `answer_llm_polish.py` was at 1694 LOC
before v25; this sibling collects the v25 directive-building helpers so
the polish file does not grow further.

Each `build_*` function returns a single string (empty when the directive
does not apply). Each respects its own kill-switch env flag and the
detection helpers live in their dedicated modules.
"""

from __future__ import annotations

from ..year_facts import build_deadline_directive
from .accounting_framework import (
    awareness_enabled as framework_enabled,
    detect_framework_hint,
    framework_directive,
)
from .cross_border_lane import (
    cross_border_directive,
    detect_cross_border_context,
    lane_enabled as cross_border_enabled,
)
from .documento_soporte_lane import (
    detect_documento_soporte_context,
    documento_soporte_directive,
    lane_enabled as documento_soporte_enabled,
)
from .enum_list_extractor import (
    build_enum_list_directive,
)
from .municipal_tax_routing import (
    detect_municipal_context,
    municipal_directive,
    routing_enabled as municipal_enabled,
)
from .norm_keyed_boost import (
    boost_enabled as norm_keyed_enabled,
    extract_named_norms,
    norm_keyed_directive,
)

__all__ = [
    "build_norm_keyed_block",
    "build_cross_border_block",
    "build_municipal_block",
    "build_framework_block",
    "build_deadline_block",
    "build_documento_soporte_block",
    "build_enum_list_block",
    "build_v25_polish_blocks",
]


def build_enum_list_block(question: str | None) -> str:
    """P15 — empty when LIA_ENUM_LIST_EXTRACTION=off or no enum list found."""
    return build_enum_list_directive(question)


def build_documento_soporte_block(question: str | None) -> str:
    """P12 / Fix 2 — empty when LIA_DOCUMENTO_SOPORTE_LANE=off or no cues."""
    if not documento_soporte_enabled():
        return ""
    hint = detect_documento_soporte_context(question or "")
    return documento_soporte_directive(hint)


def build_framework_block(question: str | None) -> str:
    """P4 / G11 — empty when LIA_FRAMEWORK_AWARENESS=off or framework=none."""
    if not framework_enabled():
        return ""
    hint = detect_framework_hint(question or "")
    return framework_directive(hint)


def build_deadline_block(topic: str | None) -> str:
    """P6 / G13 — empty when LIA_DEADLINE_REGISTRY_INJECTION=off or no deadlines for topic."""
    if not topic:
        return ""
    block = build_deadline_directive(topic)
    return block or ""


def build_norm_keyed_block(question: str | None) -> str:
    """P1 / G8 — empty when LIA_NORM_KEYED_BOOST=off or no norms named."""
    if not norm_keyed_enabled():
        return ""
    refs = extract_named_norms(question or "")
    return norm_keyed_directive(refs)


def build_cross_border_block(question: str | None) -> str:
    """P2 / G9 — empty when LIA_CROSS_BORDER_LANE=off or no foreign cue."""
    if not cross_border_enabled():
        return ""
    hint = detect_cross_border_context(question or "")
    return cross_border_directive(hint)


def build_municipal_block(question: str | None) -> str:
    """P3 / G10 — empty when LIA_MUNICIPAL_TAX_ROUTING=off or no municipal cue."""
    if not municipal_enabled():
        return ""
    hint = detect_municipal_context(question or "")
    return municipal_directive(hint)


def build_v25_polish_blocks(
    question: str | None,
    *,
    topic: str | None = None,
) -> dict[str, str]:
    """Return all v25 directive blocks for ``question`` + ``topic``.

    Mapping: directive_id → text (may be empty). Caller wraps with surrounding
    whitespace as needed.
    """
    return {
        "norm_keyed": build_norm_keyed_block(question),
        "cross_border": build_cross_border_block(question),
        "municipal": build_municipal_block(question),
        "framework": build_framework_block(question),
        "deadlines": build_deadline_block(topic),
        "documento_soporte": build_documento_soporte_block(question),
        "enum_list": build_enum_list_block(question),
    }
