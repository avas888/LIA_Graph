"""Direct-answer matcher — assigns Recomendaciones bullets to sub-questions.

Extracted from ``answer_synthesis_sections.py`` in fix_v16 b3 (2026-05-14)
to keep that file under the 1000-LOC ceiling per the divide-and-conquer
architecture rule.

The matcher walks ``recommendations`` / ``procedure`` / ``precautions`` /
``paperwork`` / ``context_lines`` / ``opportunities`` and assigns each pool
line to the sub-question with the strongest match. Sub-questions that match
nothing fall to ``DIRECT_ANSWER_COVERAGE_PENDING`` so the rendered answer
never shows a silently empty per-question block.

fix_v16 b3 (2026-05-14) added a **structural-match path** for limit-style
questions ("¿Cuál es el tope...?", "¿Qué porcentaje...?") so they no longer
fall to Cobertura pendiente just because their phrasing shares no literal
tokens with the answering bullet — a numeric-range bullet (with UVT / % /
$ / threshold operators) is treated as a soft match at ratio 0.30. Real
literal-overlap matches still win when present.
"""
from __future__ import annotations

import re

from .answer_policy import (
    DIRECT_ANSWER_BULLETS_PER_QUESTION,
    DIRECT_ANSWER_COVERAGE_PENDING,
)
from .answer_shared import anchor_query_tokens, normalize_text


_LIMIT_QUESTION_CUES: tuple[str, ...] = (
    "tope",
    "topes",
    "límite",
    "limites",
    "limite",
    "umbral",
    "umbrales",
    "monto máximo",
    "monto maximo",
    "máximo deducible",
    "maximo deducible",
    "cuánto puedo",
    "cuanto puedo",
    "cuánto se",
    "cuanto se",
    "hasta cuánto",
    "hasta cuanto",
    "hasta qué",
    "hasta que",
    "porcentaje",
    "que porcentaje",
    "qué porcentaje",
    "cual es el porcentaje",
    "cuál es el porcentaje",
    "valor máximo",
    "valor maximo",
)


def _is_limit_style_question(normalized_question: str) -> bool:
    """True when the question asks about a threshold, percentage, or monetary limit.

    Used to enable the structural-match path in :func:`build_direct_answers`.
    """
    if not normalized_question:
        return False
    return any(cue in normalized_question for cue in _LIMIT_QUESTION_CUES)


_NUMERIC_RANGE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\d[\d.,]*\s*%"),                       # 35%, 1,5 %
    re.compile(r"\d[\d.,]*\s*uvt", re.IGNORECASE),      # 3.500 UVT
    re.compile(r"\d[\d.,]*\s*smmlv", re.IGNORECASE),    # 10 SMMLV
    re.compile(r"\$\s*\d"),                             # $4.706.500
    re.compile(r"\bcop\b", re.IGNORECASE),
    re.compile(r"\bhasta\b\s+\d"),                      # "hasta 100 UVT"
    re.compile(r"[<>≤≥]\s*\d"),                         # "< 3.500"
    re.compile(r"\bmenor\s+que\b|\bmayor\s+que\b|\bigual\s+o\s+superior\b"),
    re.compile(r"\bentre\s+\d.+\s+y\s+\d"),             # "entre 1.090 y 3.270 UVT"
    re.compile(r"\btope\s+de\b", re.IGNORECASE),
)


def _bullet_has_numeric_range(line: str) -> bool:
    """True when the bullet carries a numeric threshold or amount.

    Used by the structural-match path to decide whether a limit-style
    question can pair with this bullet absent literal token overlap.
    """
    if not line:
        return False
    text = line.replace("**", "")
    return any(pat.search(text) for pat in _NUMERIC_RANGE_PATTERNS)


def build_direct_answers(
    *,
    sub_questions: tuple[str, ...],
    recommendations: tuple[str, ...],
    procedure: tuple[str, ...],
    paperwork: tuple[str, ...],
    precautions: tuple[str, ...],
    context_lines: tuple[str, ...],
    opportunities: tuple[str, ...],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Map each sub-question to bullets drawn from the already-built sections.

    Each sub-question becomes its own visible block with up to
    ``DIRECT_ANSWER_BULLETS_PER_QUESTION`` bullets selected by keyword overlap
    with the sub-question itself. Sub-questions that match nothing get an
    explicit coverage-pending marker so the reader never sees a silently
    empty block.

    fix_v16 b3 (2026-05-14): limit-style questions (asking about thresholds,
    percentages, or monetary limits) get a structural bonus when paired with
    bullets that carry numeric ranges, even when the bullets don't share
    literal tokens with the question. Real literal-overlap matches still win.
    """
    if len(sub_questions) < 2:
        return ()

    pool: tuple[str, ...] = tuple(
        line
        for bucket in (
            recommendations,
            procedure,
            precautions,
            paperwork,
            context_lines,
            opportunities,
        )
        for line in bucket
        if line
    )
    if not pool:
        return tuple(
            (question, (DIRECT_ANSWER_COVERAGE_PENDING,))
            for question in sub_questions
        )

    question_norms: list[str] = [normalize_text(q) for q in sub_questions]
    question_tokens: list[set[str]] = [
        anchor_query_tokens(q) for q in question_norms
    ]
    question_is_limit: list[bool] = [
        _is_limit_style_question(q) for q in question_norms
    ]
    assignments: list[list[str]] = [[] for _ in sub_questions]
    used_lines: set[str] = set()
    for line in pool:
        if line in used_lines:
            continue
        line_tokens = anchor_query_tokens(normalize_text(line))
        line_has_range = _bullet_has_numeric_range(line)
        best_index = -1
        best_overlap = 0
        best_ratio = 0.0
        for index, tokens in enumerate(question_tokens):
            if not tokens:
                continue
            overlap = len(tokens & line_tokens)
            # fix_v16 b3: limit-style questions accept structural matches.
            # When the question is limit-shaped and the bullet carries a
            # numeric range, treat that as a "soft overlap" of 1 token so
            # the bullet competes even without surface-vocabulary overlap.
            # The literal-overlap path still wins when it produces a real
            # match; structural ratio is discounted (0.30) to ensure that.
            structural_match = (
                overlap < 1 and question_is_limit[index] and line_has_range
            )
            if overlap < 1 and not structural_match:
                continue
            effective_overlap = overlap if overlap >= 1 else 1
            if structural_match:
                ratio = 0.30
            else:
                ratio = effective_overlap / len(tokens)
            if ratio > best_ratio or (ratio == best_ratio and effective_overlap > best_overlap):
                best_ratio = ratio
                best_overlap = effective_overlap
                best_index = index
        if best_index < 0:
            continue
        bucket = assignments[best_index]
        if len(bucket) >= DIRECT_ANSWER_BULLETS_PER_QUESTION:
            continue
        bucket.append(line)
        used_lines.add(line)

    result: list[tuple[str, tuple[str, ...]]] = []
    for question, bullets in zip(sub_questions, assignments):
        if bullets:
            result.append((question, tuple(bullets)))
        else:
            result.append((question, (DIRECT_ANSWER_COVERAGE_PENDING,)))
    return tuple(result)


__all__ = [
    "_LIMIT_QUESTION_CUES",
    "_NUMERIC_RANGE_PATTERNS",
    "_bullet_has_numeric_range",
    "_is_limit_style_question",
    "build_direct_answers",
]
