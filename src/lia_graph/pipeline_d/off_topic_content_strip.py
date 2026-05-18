"""fix_v25_may.md P13 — post-template off-topic content strip.

After P11+P12 land, the audit Q1 re-probe still showed zona-franca content
in body bullets. The pollution comes from the *práctica* retrieval lane,
which has no topic_key on its chunks and so bypasses the P11 evidence
filter. The clean long-term fix is to tag práctica chunks with topic_key
at ingest; the short-term fix lives here.

This module runs as a post-template strip in ``answer_assembly``: when a
question is NOT about a given topic-family (zona franca, dividendos,
arrendamiento, etc.), drop bullets that anchor exclusively on that
family's normative landmarks. Anchored on conservative regex patterns so
generic accountant prose is unaffected.

Flag: ``LIA_OFFTOPIC_CONTENT_STRIP={off,shadow,enforce}`` (default
``enforce``).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

__all__ = [
    "OffTopicFamily",
    "strip_off_topic_bullets",
    "strip_enabled",
    "strip_mode",
]


_ENV_FLAG = "LIA_OFFTOPIC_CONTENT_STRIP"


def strip_mode() -> str:
    raw = (os.getenv(_ENV_FLAG) or "enforce").strip().lower()
    if raw in {"off", "shadow", "enforce"}:
        return raw
    return "enforce"


def strip_enabled() -> bool:
    return strip_mode() != "off"


@dataclass(frozen=True)
class OffTopicFamily:
    """A normative landmark family + the question cues that justify keeping it."""

    name: str
    pattern: re.Pattern[str]
    question_cues: tuple[re.Pattern[str], ...]


_FAMILIES: tuple[OffTopicFamily, ...] = (
    OffTopicFamily(
        name="zona_franca",
        pattern=re.compile(
            r"\b(zona\s+franca|UIB\s*/?\s*UIS|usuari[oa]s?\s+industriales?|"
            r"plan\s+de\s+internacionalizaci[oó]n|MinCIT|Decreto\s+0?049/?2024|"
            r"Ley\s+2277/?2022\s+art\.\s*11|art\.\s*240-1\s+ET|"
            r"doble\s+tarifa\s+(?:en\s+)?zona|exportaciones?\s+atribuibles?)\b",
            flags=re.IGNORECASE,
        ),
        question_cues=(
            re.compile(r"\b(zona\s+franca|UIB|UIS|MinCIT|240-1)\b", re.IGNORECASE),
        ),
    ),
    OffTopicFamily(
        name="incrngo_donaciones",
        pattern=re.compile(
            r"\b(INCRNGO\s+por\s+donac|art\.\s*125\s+ET|donac(?:i[oó]n|iones)\s+"
            r"deducibles?|fundaci[oó]n\s+sin\s+[aá]nimo\s+de\s+lucro\s+donat|"
            r"l[ií]mite\s+del?\s+25\s*%?\s+(?:de\s+la\s+)?renta\s+l[ií]quida)\b",
            flags=re.IGNORECASE,
        ),
        question_cues=(
            re.compile(r"\b(donac(?:i[oó]n|iones)|INCRNGO|RTE\s+donat)\b", re.IGNORECASE),
        ),
    ),
    OffTopicFamily(
        name="dividendos",
        pattern=re.compile(
            r"\b(dividendos?\s+(?:gravad|no\s+gravad|exent)|art\.\s*49\s+ET|"
            r"art\.\s*242(?:-1)?\s+ET|art\.\s*245\s+ET\s+dividendos?\s+no\s+residente)\b",
            flags=re.IGNORECASE,
        ),
        question_cues=(
            re.compile(r"\bdividendos?\b", re.IGNORECASE),
        ),
    ),
    OffTopicFamily(
        name="inc_vehiculos",
        pattern=re.compile(
            r"\bart\.\s*512-(?:3|4|5)\s+ET\b|\bIN[CO]\s+(?:de\s+)?veh[ií]culos?",
            flags=re.IGNORECASE,
        ),
        question_cues=(
            re.compile(r"\b(veh[ií]culo|automotor|moto)", re.IGNORECASE),
        ),
    ),
)


def _question_mentions_family(question: str, family: OffTopicFamily) -> bool:
    if not question:
        return False
    return any(cue.search(question) for cue in family.question_cues)


_NUMBERED_BULLET_RX = re.compile(r"^\s*\d+\.\s+")


def _bullet_iter(text: str):
    """Yield (line, is_bullet) tuples preserving original order.

    Catches three bullet shapes: dashed (``- foo``), starred (``* foo``,
    ``• foo``), and **numbered** (``5. foo``). Práctica synthesis renders
    Recomendaciones Prácticas as a numbered list; if we only matched
    dashes we'd silently let off-topic numbered bullets through.
    """
    for line in text.splitlines():
        stripped = line.lstrip()
        is_dash = (
            bool(stripped) and stripped[0] in "-*•" and stripped[1:2] == " "
        )
        is_numbered = bool(_NUMBERED_BULLET_RX.match(line))
        yield line, is_dash or is_numbered


def strip_off_topic_bullets(text: str, question: str) -> tuple[str, list[dict]]:
    """Return ``(cleaned_text, drop_log)``.

    A bullet is dropped when its content matches an off-topic family's
    pattern AND the question does NOT mention that family. The function is
    bullet-scoped: section headers, plain prose, and headings are untouched.

    drop_log entries: ``{"family": str, "line_preview": str}``.
    """
    if not strip_enabled() or not text or not question:
        return text, []

    active_families = [f for f in _FAMILIES if not _question_mentions_family(question, f)]
    if not active_families:
        return text, []

    out_lines: list[str] = []
    drops: list[dict] = []
    for line, is_bullet in _bullet_iter(text):
        if not is_bullet:
            out_lines.append(line)
            continue
        dropped = False
        for fam in active_families:
            if fam.pattern.search(line):
                drops.append({"family": fam.name, "line_preview": line.strip()[:120]})
                dropped = True
                break
        if not dropped:
            out_lines.append(line)
    return "\n".join(out_lines), drops
