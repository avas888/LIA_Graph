from __future__ import annotations

import re

_HISTORICAL_PHRASE_RE = re.compile(
    r"\b(originalmente|en su versión original|"
    r"en su version original|versión anterior|version anterior|"
    r"qué decía|que decia|cómo era|como era|"
    r"hace cuánto|hace cuanto|antes que|histórico|historico|"
    r"vigencia|vigente para|vigente en|a corte de)\b",
    re.IGNORECASE,
)
_ANCHORED_RELATIVE_TIME_RE = re.compile(
    r"\b(?:antes de|previo a|despu[eé]s de)\s+"
    r"(?:(?:la|el)\s+)?(?:ley|decreto|resoluci[oó]n|reforma|art(?:[ií]culo)?)\b",
    re.IGNORECASE,
)
_YEAR_ANCHOR_RE = re.compile(r"\b(19[89]\d|20[0-3]\d)\b")
_LEY_REFORMA_RE = re.compile(
    r"\bley\s*(\d{3,4})(?:\s*de\s*(\d{4}))?",
    re.IGNORECASE,
)
_REFORMA_YEAR_RE = re.compile(
    r"\breforma\s*(?:tributaria\s*)?(?:de\s*)?(\d{4})",
    re.IGNORECASE,
)


def detect_historical_intent(query: str) -> tuple[bool, str | None]:
    """Detect historical temporal intent and infer a coarse consulta date."""
    text = str(query or "")
    if not text:
        return False, None

    has_phrase = bool(_HISTORICAL_PHRASE_RE.search(text)) or bool(
        _ANCHORED_RELATIVE_TIME_RE.search(text)
    )
    if not has_phrase:
        return False, None

    year: int | None = None

    reforma_match = _REFORMA_YEAR_RE.search(text)
    if reforma_match:
        try:
            year = int(reforma_match.group(1))
        except (TypeError, ValueError):
            year = None

    if year is None:
        ley_match = _LEY_REFORMA_RE.search(text)
        if ley_match:
            year_group = ley_match.group(2)
            if year_group:
                try:
                    year = int(year_group)
                except (TypeError, ValueError):
                    year = None

    if year is None:
        year_match = _YEAR_ANCHOR_RE.search(text)
        if year_match:
            try:
                year = int(year_match.group(1))
            except (TypeError, ValueError):
                year = None

    if year is None or year < 1990 or year > 2039:
        return True, None

    return True, f"{year - 1:04d}-12-31"


__all__ = ["detect_historical_intent"]
