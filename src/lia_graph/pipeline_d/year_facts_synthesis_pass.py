"""fix_v25_may.md P14 — synthesis-layer year_facts rewrite.

v23 P2 injected canonical UVT/SMLMV/auxilio into the **polish prompt** and
added a polish validator (``_no_invented_uvt_ranges``). When the polish
LLM produced stale UVT values the validator rejected polish — but the
*synthesis template*, composed from the same polluted chunk text, fell
through unchanged. Result: audit Q2 saw the polluted template directly
("AG 2026 UVT $49.799" — that's the 2025 UVT mislabeled as 2026).

This module runs **before polish** at the assembly layer. It scans the
composed template for:

  1. Standalone canonical-UVT mentions: ``UVT $XX.XXX`` near an ``AG YYYY``
     or "año gravable YYYY" cue.
  2. Multi-UVT precomputed mentions: ``N UVT = $YY.YYY`` near a year cue.

When a stale value is detected, it is rewritten in place with the
canonical value from ``year_facts``. The rewrite is conservative — only
fires when (a) the year is present in context, (b) the year has
verified canonical UVT, and (c) the stale value is within ±20 % of the
canonical (so we don't rewrite genuine unrelated amounts).

Flag: ``LIA_YEAR_FACTS_SYNTHESIS_REWRITE={off,shadow,enforce}``
(default ``enforce``).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from ..year_facts import get_year_facts, multi_uvt

__all__ = [
    "RewriteResult",
    "rewrite_year_constants",
    "rewrite_enabled",
    "rewrite_mode",
]


_ENV_FLAG = "LIA_YEAR_FACTS_SYNTHESIS_REWRITE"


def rewrite_mode() -> str:
    raw = (os.getenv(_ENV_FLAG) or "enforce").strip().lower()
    if raw in {"off", "shadow", "enforce"}:
        return raw
    return "enforce"


def rewrite_enabled() -> bool:
    return rewrite_mode() != "off"


@dataclass(frozen=True)
class RewriteResult:
    text: str
    rewrites: tuple[dict, ...]


# Year cue — matches "AG 2026", "año gravable 2026", "AG2026" within a window.
_YEAR_CUE_RX = re.compile(
    r"\b(?:AG|a[ñn]o\s+gravable|para\s+(?:el\s+)?(?:AG\s*)?)\s*(20\d{2})\b",
    flags=re.IGNORECASE,
)
# Standalone UVT mention: `UVT $52.374` or `UVT $52,374` or `UVT 52374`.
_UVT_VALUE_RX = re.compile(
    r"\bUVT\b\s*\$?\s*(\d{2,3}(?:[.,]\d{3})+|\d{4,6})\b",
)
# Multi-UVT computation: `4 UVT = $209.496`, `4 UVT: $209.496`, `27 UVT — $1.414.098`.
_MULTI_UVT_RX = re.compile(
    r"(\d{1,5})\s*UVT\b[^\d$\n]{0,15}\$?\s*(\d{1,3}(?:[.,]\d{3})+|\d{4,10})\b",
)


def _amount_to_int(token: str) -> int:
    digits = re.sub(r"[^\d]", "", token)
    if not digits:
        return 0
    return int(digits)


def _within_tolerance(actual: int, target: int, *, tolerance_pct: float = 0.20) -> bool:
    if target <= 0:
        return False
    delta = abs(actual - target) / target
    return delta <= tolerance_pct


def _format_amount(value: int) -> str:
    """Render `52374` as `$52.374` (Colombian thousands-dot convention)."""
    return "$" + f"{int(value):,}".replace(",", ".")


def _windows_with_year(text: str):
    """Yield (start, end, year) windows centered around year-cue matches.

    Each window spans the entire surrounding paragraph (split on blank
    lines) so a single year cue applies to all UVT mentions in that
    paragraph. This matches how the chunk corpus actually writes things —
    a heading like 'Bases AG 2025' followed by 3-4 numeric lines.
    """
    # Split by blank lines into paragraphs; track absolute offsets.
    para_starts = [0]
    for m in re.finditer(r"\n\s*\n", text):
        para_starts.append(m.end())
    para_starts.append(len(text))

    for i in range(len(para_starts) - 1):
        start, end = para_starts[i], para_starts[i + 1]
        chunk = text[start:end]
        years = [int(m.group(1)) for m in _YEAR_CUE_RX.finditer(chunk)]
        if not years:
            continue
        # If multiple years appear in the same paragraph (e.g. "AG 2025 vs AG
        # 2026 comparison"), skip the rewrite — too risky to know which UVT
        # mention belongs to which year.
        if len(set(years)) > 1:
            continue
        yield start, end, years[0]


def rewrite_year_constants(text: str) -> RewriteResult:
    """Rewrite stale UVT values in ``text`` against the canonical registry.

    Returns ``(new_text, rewrites_log)``. ``rewrites_log`` is a tuple of
    dicts with keys ``kind`` (``"uvt"`` / ``"multi_uvt"``), ``year``,
    ``old``, ``new``, ``n_uvt`` (only for multi_uvt).

    When the flag is off or ``text`` is empty, returns text unchanged.
    """
    if not rewrite_enabled() or not text:
        return RewriteResult(text=text, rewrites=())

    rewrites: list[dict] = []
    out = text

    for win_start, win_end, year in _windows_with_year(text):
        facts = get_year_facts(year)
        if facts is None or facts.uvt is None or not facts.uvt.verified:
            continue
        canonical_uvt = int(facts.uvt.value_cop or 0)
        if canonical_uvt <= 0:
            continue
        canonical_uvt_str = _format_amount(canonical_uvt)
        # Window slice (use current out, recompute offsets carefully).
        # NOTE: rewrites preserve length only when the new amount has the
        # same digit-grouping; we accept that downstream offsets may shift,
        # and process the entire text in one pass below.

    # Single pass with per-paragraph context. When a paragraph contains
    # multiple year cues (e.g. "AG 2025... AG 2026..."), split it at each
    # cue boundary so each segment has a single-year context — that's the
    # audit Q2 shape and we must rewrite both halves correctly.
    new_chunks: list[str] = []
    paragraphs: list[tuple[int, int]] = []
    para_starts = [0]
    for m in re.finditer(r"\n\s*\n", text):
        para_starts.append(m.end())
    para_starts.append(len(text))
    for i in range(len(para_starts) - 1):
        paragraphs.append((para_starts[i], para_starts[i + 1]))

    def _segments_with_year(para_text: str):
        """Yield (segment_text, year) tuples. When ``para_text`` has
        multiple year cues, slice at each cue boundary so each segment
        carries its own year."""
        cues = list(_YEAR_CUE_RX.finditer(para_text))
        if not cues:
            yield para_text, None
            return
        if len(cues) == 1:
            yield para_text, int(cues[0].group(1))
            return
        # Multi-cue: each segment runs from the cue start up to the next
        # cue start (or end of paragraph). Any leading text before the
        # first cue is emitted with year=None (untouched).
        if cues[0].start() > 0:
            yield para_text[: cues[0].start()], None
        for i, cue in enumerate(cues):
            seg_start = cue.start()
            seg_end = cues[i + 1].start() if i + 1 < len(cues) else len(para_text)
            yield para_text[seg_start:seg_end], int(cue.group(1))

    for start, end in paragraphs:
        para = text[start:end]
        rebuilt: list[str] = []
        for segment, year in _segments_with_year(para):
            if year is None:
                rebuilt.append(segment)
                continue
            facts = get_year_facts(year)
            if facts is None or facts.uvt is None or not facts.uvt.verified:
                rebuilt.append(segment)
                continue
            canonical_uvt = int(facts.uvt.value_cop or 0)
            if canonical_uvt <= 0:
                rebuilt.append(segment)
                continue
            rebuilt.append(_apply_rewrites(segment, year, canonical_uvt, rewrites))
        new_chunks.append("".join(rebuilt))

    return RewriteResult(text="".join(new_chunks), rewrites=tuple(rewrites))


def _apply_rewrites(
    segment: str,
    year: int,
    canonical_uvt: int,
    rewrites: list[dict],
) -> str:
    """Apply UVT + multi-UVT rewrites to a single-year segment."""
    canonical_uvt_str = _format_amount(canonical_uvt)

    def _rewrite_uvt(match: re.Match) -> str:
        raw_amount = match.group(1)
        actual = _amount_to_int(raw_amount)
        if actual == canonical_uvt:
            return match.group(0)
        if not _within_tolerance(actual, canonical_uvt, tolerance_pct=0.20):
            return match.group(0)
        rewrites.append(
            {"kind": "uvt", "year": year, "old": raw_amount, "new": canonical_uvt_str}
        )
        # In-place substitution at the amount span only — preserve "UVT"
        # prefix, any markdown emphasis, and any "$" already in the text.
        original = match.group(0)
        new_amount_digits = canonical_uvt_str.lstrip("$")
        match_start = match.start()
        rel_start = match.start(1) - match_start
        rel_end = match.end(1) - match_start
        return original[:rel_start] + new_amount_digits + original[rel_end:]

    segment = _UVT_VALUE_RX.sub(_rewrite_uvt, segment)

    def _rewrite_multi(match: re.Match) -> str:
        n_uvt = int(match.group(1))
        raw_amount = match.group(2)
        actual = _amount_to_int(raw_amount)
        canonical_multi = multi_uvt(n_uvt, year)
        if canonical_multi is None or canonical_multi <= 0:
            return match.group(0)
        if actual == canonical_multi:
            return match.group(0)
        if not _within_tolerance(actual, canonical_multi, tolerance_pct=0.20):
            return match.group(0)
        rewrites.append(
            {
                "kind": "multi_uvt",
                "year": year,
                "n_uvt": n_uvt,
                "old": raw_amount,
                "new": _format_amount(canonical_multi),
            }
        )
        # In-place amount substitution: replace ONLY the digit run, leave
        # every other character (including the "UVT", "=", "$", "**"
        # markdown) untouched. The original logic rebuilt a prefix and
        # produced "4 UVT UVT = $$199.196" duplicates.
        original = match.group(0)
        # `_format_amount` returns "$XX.XXX"; strip the "$" so we don't
        # double-add it when the original already has one.
        new_amount_digits = _format_amount(canonical_multi).lstrip("$")
        amount_span = match.span(2)
        # Substring inside `original` corresponding to the amount group.
        match_start = match.start()
        rel_start = amount_span[0] - match_start
        rel_end = amount_span[1] - match_start
        return original[:rel_start] + new_amount_digits + original[rel_end:]

    return _MULTI_UVT_RX.sub(_rewrite_multi, segment)
