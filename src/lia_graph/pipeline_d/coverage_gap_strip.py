"""fix_v25_may.md §3.5 P5-T3 — coverage-gap stub stripper.

The v25 P5 polish validator (`_no_coverage_gap_phrase`) rejects polish
when the LLM emits "Cobertura pendiente" / "valida el expediente" /
"no encuentro evidencia" stubs. But when polish rejects, the fallback
path re-uses the SAME synthesis template — and the gap-stub may live in
the template itself, not just the LLM's polish. Audit Q3 surfaced this
exact shape: polish rejected ✅, fallback shows the stub anyway.

This module runs at the assembly layer (alongside ``off_topic_content_strip``):

  - Drops bullets / sub-bullets whose entire content is a canonical gap
    stub.
  - When the stub is the only bullet under a sub-question, the bullet is
    replaced by a compact "[brecha de evidencia]" notice so the
    accountant knows the sub-question wasn't covered.

Flag: ``LIA_COVERAGE_GAP_GATE={off,shadow,enforce}`` (default ``enforce``;
SAME flag as the validator so both sides toggle together).
"""

from __future__ import annotations

import os
import re

__all__ = ["strip_coverage_gap_lines", "strip_enabled", "strip_mode"]


_ENV_FLAG = "LIA_COVERAGE_GAP_GATE"


def strip_mode() -> str:
    raw = (os.getenv(_ENV_FLAG) or "enforce").strip().lower()
    if raw in {"off", "shadow", "enforce"}:
        return raw
    return "enforce"


def strip_enabled() -> bool:
    return strip_mode() != "off"


_GAP_STUB_RX = re.compile(
    r"(?:cobertura\s+pendiente|valida(?:\s+el)?\s+expediente\s+antes|"
    r"no\s+encuentro\s+evidencia\s+(?:para|sobre)|"
    r"sin\s+evidencia\s+suficiente\s+para)",
    flags=re.IGNORECASE,
)

_BULLET_PREFIX_RX = re.compile(r"^(\s*)([-*•]|\d+\.)(\s+)(.*)$", flags=re.DOTALL)
_BRECHA_NOTICE = "[brecha de evidencia]"


def strip_coverage_gap_lines(text: str) -> tuple[str, list[dict]]:
    """Strip lines whose content matches a canonical gap stub.

    Returns ``(cleaned_text, drops)``. ``drops`` is a list of
    ``{"line_preview": str}`` for diagnostics. When a bullet under a
    sub-question becomes empty after stripping (i.e. the stub WAS the
    only content), the bullet is replaced by ``[brecha de evidencia]``
    so the accountant sees that the sub-question wasn't answered — but
    without the apologetic "Cobertura pendiente" wording.
    """
    if not strip_enabled() or not text:
        return text, []

    drops: list[dict] = []
    out_lines: list[str] = []
    for line in text.splitlines():
        if not _GAP_STUB_RX.search(line):
            out_lines.append(line)
            continue
        # If this is a bullet, decide whether to drop or replace.
        match = _BULLET_PREFIX_RX.match(line)
        if match is None:
            # Plain prose line containing the stub — drop entirely.
            drops.append({"line_preview": line.strip()[:120]})
            continue
        # Replace bullet content with a compact notice so the
        # sub-question header above still has something under it.
        indent, marker, sep, _content = match.groups()
        out_lines.append(f"{indent}{marker}{sep}{_BRECHA_NOTICE}")
        drops.append({"line_preview": line.strip()[:120]})
    return "\n".join(out_lines), drops
