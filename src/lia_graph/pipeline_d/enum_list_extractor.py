"""fix_v25_may.md P15 — enum-list decomposition.

Many audit questions enumerate items inside a single sub-question:

  - Q2: "retencion en la fuente por pagos de **servicios, honorarios y
    compras a terceros**" — 3 items.
  - Q4: "El auxilio entra en la base de prima, cesantias, intereses de
    cesantias, vacaciones, **salud, pension y parafiscales**" — 3 items.
  - Q6: "frente al **SIMPLE, IVA o INC, ICA, anticipos bimestrales,
    declaracion anual y retenciones**" — 6 items.
  - Q15: "**documentos societarios y fiscales**" — 2 items.
  - Q16: "**informe local, informe maestro o pais por pais**" — 3 items.

The single-question sub-question splitter
(``planner._extract_user_sub_questions``) only splits on ``?`` marks, so
these lists are invisible to the rest of the pipeline. Synthesis composes
one bullet per `?`-bounded sub-question and routinely drops the second /
third enum item — Q2's `compras` is the canonical case.

This module extracts enum lists from a question and surfaces them as
``must-cover items``. Two consumers:

  1. A polish-prompt directive ("address EACH of: A, B, C") that the LLM
     follows when re-shaping the template.
  2. A diagnostic field that downstream synthesis can use to assert
     each item appears in the answer (future work; not wired yet).

Flag: ``LIA_ENUM_LIST_EXTRACTION={off,shadow,enforce}`` (default
``enforce``).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

__all__ = [
    "EnumList",
    "extract_enum_lists",
    "build_enum_list_directive",
    "extraction_enabled",
    "extraction_mode",
]


_ENV_FLAG = "LIA_ENUM_LIST_EXTRACTION"


def extraction_mode() -> str:
    raw = (os.getenv(_ENV_FLAG) or "enforce").strip().lower()
    if raw in {"off", "shadow", "enforce"}:
        return raw
    return "enforce"


def extraction_enabled() -> bool:
    return extraction_mode() != "off"


@dataclass(frozen=True)
class EnumList:
    """One enumerated list captured from the question.

    ``items`` is the ordered tuple of literal item surfaces (lowercased
    and trimmed). ``raw`` is the captured surface span for diagnostics.
    """

    items: tuple[str, ...]
    raw: str = ""


# An enum list is a comma-separated sequence of nominal tokens terminated
# by `y` (and) / `o` (or). Examples we MUST match:
#   - "servicios, honorarios y compras a terceros"
#   - "SIMPLE, IVA o INC, ICA, anticipos bimestrales, declaracion anual y retenciones"
#   - "salud, pension y parafiscales"
#   - "informe local, informe maestro o pais por pais"
#   - "documentos societarios y fiscales"  (2-item: "A y B" with no comma)
#
# We DON'T want to match:
#   - Generic prose "vendí y compré" (verb conjugation)
#   - Numeric ranges "2024, 2025 y 2026" (year enumeration — usually fine
#     but not a must-cover list)
#   - Two-letter junk
#
# Strategy:
#   - Capture commas-separated noun phrases (each 2-40 chars, mostly letters)
#     followed by `\s+(?:y|o)\s+` + a final noun phrase.
#   - Require at least 2 items total (the `y/o` form) OR at least 3 items
#     (the comma-plus-comma form without `y/o`).
#   - Items shorter than 3 chars are dropped (avoids "y", "a", etc.).
_NP_TOKEN = r"[A-Za-zÁÉÍÓÚÑáéíóúñ][\wáéíóúñÁÉÍÓÚÑ\-\./]{1,40}(?:\s+[A-Za-zÁÉÍÓÚÑáéíóúñ][\wáéíóúñÁÉÍÓÚÑ\-\./]{0,40}){0,3}"
_ENUM_LIST_RX = re.compile(
    rf"\b({_NP_TOKEN}(?:\s*,\s*{_NP_TOKEN}){{1,8}}\s+(?:y|o)\s+{_NP_TOKEN})\b",
    flags=re.IGNORECASE,
)
_TWO_ITEM_RX = re.compile(
    rf"\b({_NP_TOKEN}\s+(?:y|o)\s+{_NP_TOKEN})\b",
    flags=re.IGNORECASE,
)


# Stop-list for items that the extractor would surface but a senior
# accountant would NEVER call "an enumerated topic". Trimmed conservative.
_ITEM_STOP_LOWER = frozenset(
    {
        # Connectors / glue
        "y", "o", "a", "al", "de", "del", "la", "el", "los", "las",
        "un", "una", "unos", "unas", "con", "sin", "para", "por", "que",
        "como", "cual", "cuales",
        # Generic verbs that the regex sometimes catches
        "es", "son", "ser", "estar", "haber",
        # Single-digit / single-letter
        "1", "2", "3", "4", "5",
    }
)


# Leading prepositions / connector phrases that the regex sometimes
# slurps into the first item. STRICTLY function words (preps, determiners,
# interrogatives). Content nouns like "informe" / "obligaciones" must NOT
# be stripped — they're part of the user's topic.
_LEADING_PREP_TOKENS = frozenset(
    {
        "por", "pagos", "pago", "de", "del", "la", "el", "los", "las",
        "frente", "al", "a", "con", "sin", "para", "en", "sobre",
        "que", "qué", "cual", "cuáles", "cuales", "como", "cómo",
        # Generic question-asking verbs that the regex sometimes slurps
        # into item[0] before the actual topic noun ("Que obligaciones
        # tiene frente al SIMPLE..." → "SIMPLE"). These are function-like
        # in question context; content verbs in answer context.
        "tiene", "tienen", "puede", "pueden", "debe", "deben",
        "aplica", "aplican", "obligaciones", "obligación",
    }
)


def _clean_item(item: str) -> str:
    s = item.strip().strip(".,;:")
    # Strip leading prepositional / verb-of-question tokens until the
    # remaining tokens look like a real topic phrase.
    tokens = s.split()
    while tokens and tokens[0].lower() in _LEADING_PREP_TOKENS:
        tokens = tokens[1:]
    s = " ".join(tokens)
    # Trailing stop-words too (e.g. "pais por pais debe" → "pais por pais").
    tokens = s.split()
    _TRAILING_STOP = {"debe", "deben", "revisar", "tiene", "aplica", "aplican"}
    while tokens and tokens[-1].lower() in _TRAILING_STOP:
        tokens = tokens[:-1]
    return " ".join(tokens)


def _is_valid_item(item: str) -> bool:
    cleaned = _clean_item(item)
    if len(cleaned) < 3:
        return False
    if cleaned.lower() in _ITEM_STOP_LOWER:
        return False
    # Reject pure numeric / year-shaped items.
    if re.fullmatch(r"\d{1,4}", cleaned):
        return False
    return True


def _split_enum(raw: str) -> tuple[str, ...]:
    """Parse the enum span into ordered items."""
    # Replace " y " / " o " (case-insensitive) with a comma so we can split
    # uniformly.
    normalised = re.sub(r"\s+(?:y|o)\s+", ", ", raw, flags=re.IGNORECASE)
    items = [_clean_item(t) for t in normalised.split(",")]
    items = [t for t in items if _is_valid_item(t)]
    return tuple(items)


def extract_enum_lists(question: str) -> list[EnumList]:
    """Return one ``EnumList`` per captured enum span in ``question``.

    De-dupes overlapping captures (keeps the longest). Empty list when
    the question has no qualifying enum.
    """
    if not question:
        return []
    out: list[EnumList] = []
    seen_spans: list[tuple[int, int]] = []

    def _add(match: re.Match) -> None:
        span = match.span(1)
        raw = match.group(1)
        # Skip if a previously kept span contains this one entirely (overlap).
        for prev_start, prev_end in seen_spans:
            if prev_start <= span[0] and prev_end >= span[1]:
                return
        items = _split_enum(raw)
        if len(items) < 2:
            return
        out.append(EnumList(items=items, raw=raw))
        seen_spans.append(span)

    # Longer (≥3 items, mandatory `y`/`o`) first.
    for m in _ENUM_LIST_RX.finditer(question):
        _add(m)
    # Then 2-item "A y B" form. Only when not contained in a longer
    # capture.
    for m in _TWO_ITEM_RX.finditer(question):
        _add(m)

    return out


def build_enum_list_directive(question: str | None) -> str:
    """Return a polish-prompt block enumerating the must-cover items.

    Empty string when extraction is disabled OR no qualifying lists.
    """
    if not extraction_enabled():
        return ""
    lists = extract_enum_lists(question or "")
    if not lists:
        return ""
    body_lines = []
    for el in lists:
        body_lines.append("  - " + " | ".join(el.items))
    return (
        "ÍTEMS QUE EL USUARIO ENUMERÓ EN SU PREGUNTA — debes responder "
        "CADA uno de ellos en `Respuestas directas` (una sub-viñeta "
        "por ítem; NO omitas ninguno):\n"
        + "\n".join(body_lines)
    )
