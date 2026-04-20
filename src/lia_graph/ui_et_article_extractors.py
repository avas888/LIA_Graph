"""Small pure helpers for extracting ET article quotes from markdown.

The orchestrator ``_extract_et_article_quote_from_markdown`` in
``ui_normative_processors`` used to mix five concerns in a single
76-line function. This module exposes the pure sub-helpers so each
concern is testable independently:

- ``build_article_heading_pattern`` — regex builder for "Artículo N"
- ``is_noisy_source_markup`` — detects HTML/JS leakage that should abort
- ``is_skippable_citation_preamble`` — the "*fuente original compilada:" tail
- ``find_article_start_index`` — locates the heading in a paragraph list

Keeping these pure (no ``_ui()`` reach-back, no side effects) lets tests
pin behaviour without spinning up the full UI server.
"""

from __future__ import annotations

import re
from typing import Sequence


# Tokens that indicate the markdown has picked up chunks of the source
# viewer's HTML scaffolding. Presence of any of these means the whole
# extraction should be aborted — returning a partial quote that includes
# script / bookmark machinery would corrupt the modal.
_NOISE_TOKENS: tuple[str, ...] = ("<option", "</option>", "bookmarkaj", "javascript:insrow")


def build_article_heading_pattern(locator_start: str) -> re.Pattern[str]:
    """Return a case-insensitive regex that matches ``Artículo <locator>``.

    When the locator contains a hyphen (e.g. ``689-3``) no trailing guard
    is needed because the hyphen already anchors the end of the token.
    Otherwise append a negative lookahead for ``-N`` / ``_N`` so the
    regex won't fire on ``689-3`` when the caller is looking for ``689``.
    """
    clean = str(locator_start or "").strip()
    trailing_guard = r"(?![-_]\d)" if "-" not in clean else ""
    return re.compile(
        rf"\bart[íi]culo(?:s)?\s+{re.escape(clean)}{trailing_guard}\b",
        re.IGNORECASE,
    )


def is_noisy_source_markup(lowered_text: str) -> bool:
    """True when the paragraph contains HTML/JS leakage from the source viewer.

    Caller should abort extraction entirely when this returns True — a
    clean prefix followed by script noise is not worth recovering.
    """
    if not lowered_text:
        return False
    return any(token in lowered_text for token in _NOISE_TOKENS)


def is_skippable_citation_preamble(lowered_text: str) -> bool:
    """True for the "*fuente original compilada:" metadata line variants.

    The line appears above the actual article quote in some corpus files
    and belongs to the attribution block, not the vigente text the user
    should see.
    """
    if not lowered_text:
        return False
    return lowered_text.startswith("*fuente original compilada:") or lowered_text.startswith(
        "fuente original compilada:"
    )


def find_article_start_index(
    paragraphs: Sequence[str],
    heading_re: re.Pattern[str],
) -> int:
    """Return the index of the first paragraph that starts the article.

    Returns -1 when no heading match is found; callers usually treat that
    as "start from the top and prepend a synthesized heading".
    """
    for idx, paragraph in enumerate(paragraphs):
        if heading_re.search(paragraph):
            return idx
    return -1


__all__ = [
    "build_article_heading_pattern",
    "find_article_start_index",
    "is_noisy_source_markup",
    "is_skippable_citation_preamble",
]
