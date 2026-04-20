"""Pure text-formatting helpers shared across normativa UI surfaces.

Each function has a single concern so the larger orchestrators in
``ui_normative_processors`` can compose them without repeating regex or
constant definitions. No I/O, no cross-module imports.

Extracted during normativa granularization pass (phase 2 follow-up).
"""

from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Spanish title-case
# ---------------------------------------------------------------------------

SPANISH_SMALL_WORDS = frozenset(
    {
        "a", "al", "con", "de", "del", "desde", "e", "el", "en",
        "la", "las", "los", "o", "para", "por", "sin", "u", "un", "una", "y",
    }
)


def spanish_title_case_label(text: str) -> str:
    """Capitalize each word except Spanish connectors mid-sentence.

    The first word is always capitalized (a connector at position 0 would
    otherwise look broken — "de Pérdidas Fiscales" is preferable to
    "de pérdidas fiscales").
    """
    value = str(text or "")
    words = value.split()
    if not words:
        return value
    result: list[str] = []
    for i, word in enumerate(words):
        if i == 0 or word.lower() not in SPANISH_SMALL_WORDS:
            result.append(word.capitalize())
        else:
            result.append(word.lower())
    return " ".join(result)


# ---------------------------------------------------------------------------
# Label dedup key (entity-type + year collapsed)
# ---------------------------------------------------------------------------

_LABEL_DEDUP_ENTITY_RE = re.compile(
    r"\b(?:personas?\s+(?:jur[ií]dicas?|naturales?)|grandes?\s+contribuyentes?"
    r"|jur[ií]dicas?|naturales?|gc|pj|pn|rst|pes)\b",
    re.IGNORECASE,
)
_LABEL_DEDUP_YEAR_RE = re.compile(r"\b\d{4}\b")


def label_dedup_key(label: str) -> str:
    """Collapse entity-type variants and 4-digit years into a single key.

    Used to detect that "Ley 1943 de 2018 — Personas Jurídicas" and
    "Ley 1943 — Naturales" should be treated as the same underlying item
    when deduplicating badge lists.
    """
    key = _LABEL_DEDUP_ENTITY_RE.sub("", str(label or "").lower())
    key = _LABEL_DEDUP_YEAR_RE.sub("", key)
    return re.sub(r"\s+", " ", key).strip()


# ---------------------------------------------------------------------------
# Práctica label cleanup
# ---------------------------------------------------------------------------

_PRACTICA_CODE_PREFIX_RE = re.compile(r"^[a-z]{1,6}\s+[a-z]?\w{1,6}\s*[—–\-]\s*", re.IGNORECASE)
_PRACTICA_UNKNOWN_PREFIX_RE = re.compile(r"^unknown\s*[:—–\-]\s*", re.IGNORECASE)
_PRACTICA_NUM_PREFIX_RE = re.compile(r"^\d{1,3}\s*[—–\-]\s*", re.IGNORECASE)
_PRACTICA_EXT_SUFFIX_RE = re.compile(r"\.(?:md|txt|json|html?)$", re.IGNORECASE)


def clean_practica_label(raw: str) -> str:
    """Strip code / unknown / numeric prefixes and file-extension suffixes.

    Returns the cleaned label; falls back to the original ``raw`` value when
    all content is stripped so callers always get a non-empty string.
    """
    value = str(raw or "")
    label = _PRACTICA_CODE_PREFIX_RE.sub("", value).strip()
    label = _PRACTICA_UNKNOWN_PREFIX_RE.sub("", label).strip()
    label = _PRACTICA_NUM_PREFIX_RE.sub("", label).strip()
    label = _PRACTICA_EXT_SUFFIX_RE.sub("", label).strip()
    label = label.replace("_", " ")
    label = re.sub(r"\s+", " ", label).strip()
    return label or value


__all__ = [
    "SPANISH_SMALL_WORDS",
    "clean_practica_label",
    "label_dedup_key",
    "spanish_title_case_label",
]
