from __future__ import annotations

import re


BULLET_PREFIX = "- "
NESTED_BULLET_PREFIX = "  - "
NUMBERED_PREFIX_FORMAT = "{idx}. "
BOLD_MARK = "**"

# v17 follow-up (2026-05-15) — Sub-bullet sentinel.
#
# Problem: `answer_shared.append_unique` and `neutralize_non_imputative_language`
# both call `re.sub(r"\s+", " ", ...)` on every bullet before it reaches
# the renderer. Embedded "\n  - " in a SPEC bullet gets squashed into a
# single space, killing any author-authored nested markdown.
#
# Fix: SPEC authors mark sub-bullet boundaries with `SUB_BULLET_TOKEN`
# (a sequence of non-whitespace characters, so the whitespace collapse
# leaves it intact). At final render time, `expand_sub_bullets` rewrites
# the token into proper nested-bullet markdown ("\n  - "). The token is
# chosen to be a sequence no real Spanish / legal text would type: a
# U+23F5 right-pointing triangle wrapped in pipe characters.
SUB_BULLET_TOKEN = "|⏵|"


def bullet(line: str) -> str:
    return f"{BULLET_PREFIX}{line}"


def nested_bullet(line: str) -> str:
    return f"{NESTED_BULLET_PREFIX}{line}"


def numbered(idx: int, line: str) -> str:
    return f"{NUMBERED_PREFIX_FORMAT.format(idx=idx)}{line}"


def bold(text: str) -> str:
    return f"{BOLD_MARK}{text}{BOLD_MARK}"


def section_heading(title: str) -> str:
    return bold(title)


def with_sub_bullets(lead: str, items: tuple[str, ...]) -> str:
    """Compose a single-string bullet that the renderer will expand to a
    parent line plus nested-bullet children.

    The output is one string with `SUB_BULLET_TOKEN` separating the lead
    from each sub-bullet. The token survives every whitespace-collapse
    in the synthesis pipeline because it contains no whitespace; the
    renderer's `expand_sub_bullets` step swaps it for real markdown.

    Example:
        with_sub_bullets(
            "**Recargos (CST 159, 168, 179):**",
            ("nocturno **+ 35 %**", "extra diurna **+ 25 %**"),
        )
        # ->
        # "**Recargos (CST 159, 168, 179):**|⏵|nocturno **+ 35 %**|⏵|extra diurna **+ 25 %**"

    After expansion in `render_bullet_section`:

        - **Recargos (CST 159, 168, 179):**
          - nocturno **+ 35 %**
          - extra diurna **+ 25 %**
    """
    if not items:
        return lead
    return lead + "".join(f"{SUB_BULLET_TOKEN}{item}" for item in items if item)


def expand_sub_bullets(line: str) -> str:
    """Replace every `SUB_BULLET_TOKEN` in a rendered bullet line with a
    newline + nested-bullet prefix so markdown shows nested sub-bullets.

    Idempotent: a line that has no token is returned unchanged.
    """
    if SUB_BULLET_TOKEN not in line:
        return line
    return line.replace(SUB_BULLET_TOKEN, f"\n{NESTED_BULLET_PREFIX}")


def render_bullet_section(title: str, lines: tuple[str, ...]) -> str:
    body = "\n".join(expand_sub_bullets(bullet(line)) for line in lines if line)
    return f"{section_heading(title)}\n{body}"


def render_numbered_section(title: str, lines: tuple[str, ...]) -> str:
    body = "\n".join(numbered(idx, line) for idx, line in enumerate(lines, start=1) if line)
    return f"{section_heading(title)}\n{body}"


# Numeric formatting — every quantitative value renders as digits + bold so
# the accountant's eye lands on the number first. The LLM polish prompt asks
# for this, but the post-hoc transformer below is the hard enforcer: it runs
# whether or not polish was applied, and survives an LLM that ignored the
# instruction.

# Match a digit run with optional `$` prefix, optional thousands/decimal
# separators (only when followed by more digits), optional `%` suffix.
# Examples matched: 12, 2025, 25%, 1.000.000, $1.000.000, 12,5
# Crucially does NOT match a trailing sentence period: "año 2025." → "2025"
# only, leaving the period as sentence punctuation outside the bold span.
_NUMERIC_RE = re.compile(r"\$?\d+(?:[.,]\d+)*%?")

# Legal anchors whose internal numbers must NOT be bolded. The polish
# anchor-preservation check (`_preserves_required_anchors`) normalizes by
# lowercasing and stripping parens — bolding inside would break the match.
# No `\b` after the keyword: `art.` ends in a non-word char so a word-boundary
# assertion would fail to fire after the period.
_LEGAL_ANCHOR_RE = re.compile(
    r"\((?:arts?\.?|decreto|ley|resoluci[oó]n|numeral|num\.?|literal|inciso|par[aá]grafo|sentencia|concepto)[^)]*\)",
    re.IGNORECASE,
)

# Inline citations without parens — `Ley 2277 de 2022`, `Decreto 624 de 1989`,
# `Resolución 0078 de 2020`. These are semantic units, not quantitative
# values, and must not be split into bolded fragments.
_INLINE_LAW_REF_RE = re.compile(
    r"\b(?:Ley|Decreto|Resoluci[oó]n|Sentencia|Concepto|Auto|Circular)\s+\d+\s+de\s+\d{4}\b",
    re.IGNORECASE,
)

# Dates as a single unit: ISO `2026-04-29`, Latin `29/04/2026`, `29-04-2026`,
# and Spanish-month abbreviations `31-dic-2016`.
_SPANISH_MONTHS = r"ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic"
_DATE_RE = re.compile(
    r"\b\d{4}-\d{1,2}-\d{1,2}\b"
    r"|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"
    rf"|\b\d{{1,2}}-(?:{_SPANISH_MONTHS})-\d{{2,4}}\b",
    re.IGNORECASE,
)

# Inline ET article citations without parens — `art. 290`, `arts. 147 y 290`,
# `art. 290 #5 ET`, `numeral 3 del art. 26`. These reference legal positions
# (not quantities) so the digits must not be bolded.
_INLINE_ARTICLE_REF_RE = re.compile(
    r"\barts?\.?\s+\d+[A-Za-z\-]*(?:\s+y\s+\d+[A-Za-z\-]*)*"
    r"(?:\s+#\s*\d+|\s+numeral\s+\d+|\s+num\.?\s+\d+|\s+inciso\s+\d+|\s+par[aá]grafo\s+\d+)*"
    r"(?:\s+ET\b)?",
    re.IGNORECASE,
)

# Temporal-adjective prefixes that pin a year to a regime ("pre-2017",
# "post-2025"). The year is a discriminator inside a compound word, not a
# standalone quantity — bolding it splits the word visually.
_TEMPORAL_PREFIX_RE = re.compile(r"\b(?:pre|post|anti|pro)-\d{4}\b", re.IGNORECASE)

# Colombian tax-period abbreviations: `AG 2022` (Año Gravable), `PA 2023`
# (Período de Ajuste). These are citations to a specific fiscal cycle — the
# year is identity, not quantity.
_FISCAL_PERIOD_RE = re.compile(r"\b(?:AG|PA|EFR)\s+\d{4}\b")

# Already-bolded numbers (idempotency) — `**12**`, `**$1.000.000**`, `**25%**`.
_BOLDED_NUMERIC_RE = re.compile(r"\*\*\$?\d+(?:[.,]\d+)*%?\*\*")

# A numbered-list marker at the start of a (possibly indented) line — `1. `,
# `  2. `. The number here is a list ordinal, not a quantitative value, and
# bolding it (`**1.**`) breaks Markdown list rendering.
_LIST_MARKER_RE = re.compile(r"^(\s*\d+\.\s+)")

def _merge_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not spans:
        return []
    spans.sort()
    merged: list[tuple[int, int]] = [spans[0]]
    for start, end in spans[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def _bold_in_segment(segment: str) -> str:
    protected: list[tuple[int, int]] = []
    for pattern in (
        _LEGAL_ANCHOR_RE,
        _INLINE_LAW_REF_RE,
        _INLINE_ARTICLE_REF_RE,
        _DATE_RE,
        _TEMPORAL_PREFIX_RE,
        _FISCAL_PERIOD_RE,
        _BOLDED_NUMERIC_RE,
    ):
        for match in pattern.finditer(segment):
            protected.append((match.start(), match.end()))
    protected = _merge_spans(protected)

    pieces: list[str] = []
    cursor = 0
    for start, end in protected:
        if cursor < start:
            pieces.append(_NUMERIC_RE.sub(lambda m: bold(m.group(0)), segment[cursor:start]))
        pieces.append(segment[start:end])
        cursor = end
    if cursor < len(segment):
        pieces.append(_NUMERIC_RE.sub(lambda m: bold(m.group(0)), segment[cursor:]))
    return "".join(pieces)


def format_numbers_with_bold(text: str) -> str:
    """Wrap every standalone numeric value in **bold**, line by line.

    Skips numbers inside legal-anchor parens — `(art. 147 ET)` is preserved
    letter-for-letter so the polish anchor-preservation check still matches.
    Skips the leading `N. ` of a numbered list line so Markdown rendering
    is not broken. Idempotent: already-bolded numbers are not double-wrapped.
    """
    if not text:
        return text
    out: list[str] = []
    for line in text.split("\n"):
        marker = _LIST_MARKER_RE.match(line)
        if marker:
            prefix_len = marker.end()
            out.append(line[:prefix_len] + _bold_in_segment(line[prefix_len:]))
        else:
            out.append(_bold_in_segment(line))
    return "\n".join(out)


__all__ = [
    "BULLET_PREFIX",
    "NESTED_BULLET_PREFIX",
    "NUMBERED_PREFIX_FORMAT",
    "BOLD_MARK",
    "SUB_BULLET_TOKEN",
    "bullet",
    "nested_bullet",
    "numbered",
    "bold",
    "section_heading",
    "with_sub_bullets",
    "expand_sub_bullets",
    "render_bullet_section",
    "render_numbered_section",
    "format_numbers_with_bold",
]
