"""fix_v25_may.md §3.7 — Phase 7 / G14: user-numerics capture.

Pre-extracts peso amounts, UVT counts, and percentages from the user's
question so downstream consumers can verify or echo them verbatim even when
polish rejects the LLM rewrite.

Public API:
  - ``UserNumericsExtract`` dataclass.
  - ``extract_user_numerics(question)`` → UserNumericsExtract.
  - ``format_datos_del_caso(extract)`` → markdown block string. Empty when no
    numerics were captured.
  - ``echo_enabled()`` reads ``LIA_FALLBACK_NUMERIC_ECHO``.

The audit Q10 surfaced the mutation: user said COP 3,000,000, polish
re-wrote as COP 2,000,000. v23 P5 rejects polish on mutation; v25 P7
guarantees the user's amount lands in the fallback output regardless.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

__all__ = [
    "UserNumericsExtract",
    "echo_enabled",
    "echo_mode",
    "extract_user_numerics",
    "format_datos_del_caso",
]


_ENV_FLAG = "LIA_FALLBACK_NUMERIC_ECHO"


def echo_mode() -> str:
    raw = (os.getenv(_ENV_FLAG) or "enforce").strip().lower()
    if raw in {"off", "shadow", "enforce"}:
        return raw
    return "enforce"


def echo_enabled() -> bool:
    return echo_mode() != "off"


@dataclass(frozen=True)
class UserNumericsExtract:
    amounts: tuple[str, ...] = field(default_factory=tuple)
    uvt_counts: tuple[str, ...] = field(default_factory=tuple)
    percentages: tuple[str, ...] = field(default_factory=tuple)

    @property
    def empty(self) -> bool:
        return not (self.amounts or self.uvt_counts or self.percentages)


_AMOUNT_RX = re.compile(
    r"\$\s*\d{1,3}(?:[.,]\d{3}){1,5}(?:[.,]\d+)?(?:\s*(?:M|MM|millones))?"
    r"|\d{1,3}(?:[.,]\d{3}){2,5}(?:[.,]\d+)?(?:\s*(?:M|MM|millones))?"
    r"|\d{1,4}(?:[.,]\d+)?\s*(?:millones|MM|M)\b",
    flags=re.IGNORECASE,
)
_UVT_RX = re.compile(r"\b\d{1,6}(?:[.,]\d{3})*\s*UVT\b", flags=re.IGNORECASE)
_PERCENTAGE_RX = re.compile(r"\b\d{1,3}(?:[.,]\d+)?\s*%")


def _dedupe(seq) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for item in seq:
        norm = item.strip()
        if not norm:
            continue
        key = re.sub(r"\s+", " ", norm).lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(norm)
    return tuple(out)


def extract_user_numerics(question: str | None) -> UserNumericsExtract:
    if not question:
        return UserNumericsExtract()
    amounts = _dedupe(m.group(0) for m in _AMOUNT_RX.finditer(question))
    uvt_counts = _dedupe(m.group(0) for m in _UVT_RX.finditer(question))
    percentages = _dedupe(m.group(0) for m in _PERCENTAGE_RX.finditer(question))
    return UserNumericsExtract(
        amounts=amounts,
        uvt_counts=uvt_counts,
        percentages=percentages,
    )


def format_datos_del_caso(extract: UserNumericsExtract) -> str:
    """Markdown block to prepend to fallback output. Empty when nothing to echo."""
    if extract.empty:
        return ""
    parts: list[str] = []
    if extract.amounts:
        parts.append("- Montos: " + ", ".join(extract.amounts))
    if extract.uvt_counts:
        parts.append("- UVT: " + ", ".join(extract.uvt_counts))
    if extract.percentages:
        parts.append("- Porcentajes: " + ", ".join(extract.percentages))
    body = "\n".join(parts)
    # Cap to 240 chars per fix_v25_may.md §3.7 risk note.
    if len(body) > 240:
        body = body[:237].rstrip() + "..."
    return "**Datos del caso (verbatim del usuario):**\n" + body
