"""Norm-id canonicalizer — fixplan_v3 §0.5.

Takes a free-text mention (from corpus prose, user query, or skill veredicto)
and returns the canonical `norm_id` per the §0.5 grammar, OR refuses with a
structured reason. Refusal is the safe default; we never substring-match a
citation.

The canonicalizer is the single source of truth for `norm_id` formatting.
Every downstream consumer (`norm_history_writer`, `backfill_norm_citations`,
the planner, the retriever) reads through this module — no code path may
invent a `norm_id` format.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Sequence

from lia_graph.vigencia import CanonicalizerRefusal


# Recognized resolución emitters (extendable; canonicalizer keeps a registry).
KNOWN_EMISORES: frozenset[str] = frozenset(
    {
        "dian",
        "mintic",
        "supersociedades",
        "ugpp",
        "minhacienda",
        "mintrabajo",
        "minsalud",
        "banrep",
        "supersolidaria",
    }
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CanonicalMention:
    """A successfully canonicalized mention."""

    norm_id: str
    mention: str
    span: tuple[int, int] | None = None


class InvalidNormIdError(ValueError):
    """Raised when a string fails the §0.5 grammar."""


def canonicalize(mention: str) -> str | None:
    """Return the canonical `norm_id` for `mention`, or None if ambiguous.

    See fixplan_v3 §0.5.4. A successful return is a string matching the §0.5
    grammar; None means "log to refusal queue, never substring-guess."
    """

    text = (mention or "").strip()
    if not text:
        return None

    normalized = _normalize(text)

    # Try each rule in priority order. First match wins.
    for rule in _RULES:
        norm_id = rule(normalized)
        if norm_id is not None:
            return norm_id
    return None


def canonicalize_or_refuse(mention: str, *, context: str | None = None) -> tuple[str | None, CanonicalizerRefusal | None]:
    """Wrap `canonicalize` so the caller gets a structured refusal on miss."""

    norm_id = canonicalize(mention)
    if norm_id is not None:
        return norm_id, None
    reason = _diagnose_refusal(mention)
    return None, CanonicalizerRefusal(mention=mention, reason=reason, context=context)


def is_valid_norm_id(norm_id: str) -> bool:
    """True iff `norm_id` matches the §0.5 grammar."""

    return bool(_NORM_ID_FULL_RE.match(norm_id))


def assert_valid_norm_id(norm_id: str) -> None:
    """Raise InvalidNormIdError if `norm_id` doesn't match the grammar."""

    if not is_valid_norm_id(norm_id):
        raise InvalidNormIdError(f"Invalid norm_id per §0.5 grammar: {norm_id!r}")


def parent_norm_id(norm_id: str) -> str | None:
    """Return the immediate parent of a norm_id, or None for top-level artifacts."""

    assert_valid_norm_id(norm_id)
    # sub-units strip the trailing `.<kind>.<n>` segment
    sub_unit_kinds = ("par.", "inciso.", "num.", "lit.", "art.")
    parts = norm_id.split(".")
    # walk from the end: peel off the last (kind, value) pair
    for kind in sub_unit_kinds:
        head = kind.rstrip(".")
        # find last index where parts[i] == head
        for i in range(len(parts) - 2, -1, -1):
            if parts[i] == head and i + 1 < len(parts):
                return ".".join(parts[:i])
    # No segment found; this is a top-level artifact (e.g. 'et', 'ley.2277.2022')
    return None


def is_sub_unit(norm_id: str) -> bool:
    """True iff `norm_id` represents a sub-article unit (parágrafo, inciso, etc.)."""

    assert_valid_norm_id(norm_id)
    sub_unit_markers = (".par.", ".inciso.", ".num.", ".lit.")
    return any(marker in norm_id for marker in sub_unit_markers)


def sub_unit_kind(norm_id: str) -> str | None:
    """Return 'parágrafo' | 'inciso' | 'numeral' | 'literal' or None."""

    assert_valid_norm_id(norm_id)
    if ".par." in norm_id:
        return "parágrafo"
    if ".inciso." in norm_id:
        return "inciso"
    if ".num." in norm_id:
        return "numeral"
    if ".lit." in norm_id:
        return "literal"
    return None


def display_label(norm_id: str) -> str:
    """Return a human-readable label suitable for the `norms.display_label` column."""

    assert_valid_norm_id(norm_id)
    if norm_id == "et":
        return "Estatuto Tributario"
    if norm_id.startswith("et.art."):
        rest = norm_id[len("et.art.") :]
        return f"Art. {rest.replace('.par.', ' parágrafo ').replace('.inciso.', ' inciso ').replace('.num.', ' numeral ').replace('.lit.', ' literal ')} ET"
    if norm_id.startswith("ley."):
        # ley.NUMBER.YEAR[.art.X]
        parts = norm_id.split(".")
        if len(parts) >= 3:
            base = f"Ley {parts[1]} de {parts[2]}"
            if len(parts) > 3 and parts[3] == "art":
                return f"{base}, Art. {'.'.join(parts[4:])}"
            return base
    if norm_id.startswith("decreto."):
        parts = norm_id.split(".")
        if len(parts) >= 3:
            base = f"Decreto {parts[1]} de {parts[2]}"
            if len(parts) > 3 and parts[3] == "art":
                return f"{base}, Art. {'.'.join(parts[4:])}"
            return base
    if norm_id.startswith("res."):
        parts = norm_id.split(".")
        if len(parts) >= 4:
            return f"Resolución {parts[1].upper()} {parts[2]} de {parts[3]}"
    if norm_id.startswith("concepto."):
        parts = norm_id.split(".")
        if len(parts) >= 3:
            base = f"Concepto {parts[1].upper()} {parts[2]}"
            if len(parts) > 3 and parts[3] == "num":
                return f"{base} numeral {parts[4]}"
            return base
    if norm_id.startswith("sent.cc."):
        return f"Sentencia {norm_id[len('sent.cc.') :]}"
    if norm_id.startswith("sent.ce."):
        return f"Sentencia CE {norm_id[len('sent.ce.') :]}"
    if norm_id.startswith("auto.ce."):
        return f"Auto CE {norm_id[len('auto.ce.') :]}"
    return norm_id


def norm_type(norm_id: str) -> str:
    """Map a canonical norm_id to its `norms.norm_type` value."""

    assert_valid_norm_id(norm_id)
    if norm_id == "et":
        return "estatuto"
    if norm_id.startswith("et.art."):
        return "articulo_et"
    if norm_id.startswith("ley.") and ".art." in norm_id:
        return "ley_articulo"
    if norm_id.startswith("ley."):
        return "ley"
    if norm_id.startswith("decreto.") and ".art." in norm_id:
        return "decreto_articulo"
    if norm_id.startswith("decreto."):
        return "decreto"
    if norm_id.startswith("res.") and ".art." in norm_id:
        return "res_articulo"
    if norm_id.startswith("res."):
        return "resolucion"
    if norm_id.startswith("concepto.") and ".num." in norm_id:
        return "concepto_dian_numeral"
    if norm_id.startswith("concepto."):
        return "concepto_dian"
    if norm_id.startswith("sent.cc."):
        return "sentencia_cc"
    if norm_id.startswith("sent.ce."):
        return "sentencia_ce"
    if norm_id.startswith("auto.ce."):
        return "auto_ce"
    return "unknown"


# ---------------------------------------------------------------------------
# Free-text → norm_id rules (priority-ordered)
# ---------------------------------------------------------------------------

# Helper for sub-unit detection inside a sub-rule.
_SUB_UNIT_RE = re.compile(
    r"\b(?:par(?:agrafo|ágrafo|\.)?|inciso|num(?:eral|\.)?|lit(?:eral|\.)?)\s*"
    r"(?P<n>(?:transitorio|unico|único)|\d+|[a-z])\b",
    re.IGNORECASE,
)


def _emit_sub_unit_segment(text: str) -> str:
    """Return '.par.N' | '.inciso.N' | '.num.N' | '.lit.X' | ''."""

    m = _SUB_UNIT_RE.search(text)
    if not m:
        return ""
    raw = m.group(0).lower()
    n = m.group("n").lower()
    if n in ("unico", "único"):
        n = "unico"
    if raw.startswith("par"):
        return f".par.{n}"
    if raw.startswith("inciso"):
        return f".inciso.{n}"
    if raw.startswith("num"):
        return f".num.{n}"
    if raw.startswith("lit"):
        return f".lit.{n}"
    return ""


# Rule 1 — ET article (with optional sub-unit)
_ET_ARTICLE_RE = re.compile(
    r"\bart(?:[íi]culo|\.)?\s*(?P<num>\d+(?:-\d+)?)\b.{0,40}?"
    r"(?:e\.?\s*t\.?|estatuto\s+tributario)\b",
    re.IGNORECASE,
)

_ET_ARTICLE_REVERSE_RE = re.compile(
    r"\b(?:e\.?\s*t\.?|estatuto\s+tributario)\b[^a-z0-9]{0,30}?"
    r"(?:art(?:[íi]culo|\.)?\s*)(?P<num>\d+(?:-\d+)?)\b",
    re.IGNORECASE,
)


def _rule_et_article(text: str) -> str | None:
    m = _ET_ARTICLE_RE.search(text) or _ET_ARTICLE_REVERSE_RE.search(text)
    if not m:
        return None
    num = m.group("num")
    base = f"et.art.{num}"
    sub = _emit_sub_unit_segment(text)
    return base + sub


# Rule 2 — bare ET reference
def _rule_et_bare(text: str) -> str | None:
    if re.fullmatch(r"\s*(?:e\.?\s*t\.?|estatuto\s+tributario)\s*", text, re.IGNORECASE):
        return "et"
    return None


# Rule 3 — Ley NUMBER de YEAR (with optional Art.)
_LEY_RE = re.compile(
    r"\bley\s*(?P<num>\d+(?:-\d+)?)\s*(?:de|del|/|-|\s)?\s*(?P<year>\d{4})\b",
    re.IGNORECASE,
)
_LEY_ART_RE = re.compile(
    r"\bart(?:[íi]culo|\.)?\s*(?P<art>\d+(?:-\d+)?)\b",
    re.IGNORECASE,
)


def _rule_ley(text: str) -> str | None:
    ley = _LEY_RE.search(text)
    if not ley:
        return None
    num = ley.group("num")
    year = ley.group("year")
    base = f"ley.{num}.{year}"
    art = _LEY_ART_RE.search(text)
    if art:
        # only attach if the Art. mention isn't immediately bound to the ET rule
        # (e.g. "Art. 96 Ley 2277" → ley.2277.YYYY.art.96)
        art_segment = f".art.{art.group('art')}"
        sub = _emit_sub_unit_segment(text)
        return base + art_segment + sub
    return base


# Rule 4 — Decreto NUMBER de YEAR (with optional Art. and DUR-style sub-numbering)
_DECRETO_RE = re.compile(
    r"\bdecreto\s*(?P<num>\d+(?:-\d+)?)\s*(?:de|del|/|-|\s)?\s*(?P<year>\d{4})\b",
    re.IGNORECASE,
)
_DUR_ART_RE = re.compile(
    r"\bart(?:[íi]culo|\.)?\s*(?P<art>\d+(?:\.\d+)*(?:-\d+)?)\b",
    re.IGNORECASE,
)


def _rule_decreto(text: str) -> str | None:
    dec = _DECRETO_RE.search(text)
    if not dec:
        return None
    num = dec.group("num")
    year = dec.group("year")
    base = f"decreto.{num}.{year}"
    art = _DUR_ART_RE.search(text)
    if art:
        art_segment = f".art.{art.group('art')}"
        sub = _emit_sub_unit_segment(text)
        return base + art_segment + sub
    return base


# Rule 5 — Resolución EMISOR NUMBER de YEAR
_RES_RE = re.compile(
    r"\bresoluci[óo]n\s*(?P<emisor>(?:dian|mintic|supersociedades|ugpp|"
    r"minhacienda|mintrabajo|minsalud|banrep|supersolidaria))?\s*"
    r"(?P<num>\d+(?:-\d+)?)\s*(?:de|del|/|-|\s)?\s*(?P<year>\d{4})\b",
    re.IGNORECASE,
)


def _rule_resolucion(text: str) -> str | None:
    res = _RES_RE.search(text)
    if not res:
        return None
    emisor_raw = (res.group("emisor") or "").lower()
    if not emisor_raw:
        # try to find it elsewhere in text
        for candidate in KNOWN_EMISORES:
            if re.search(rf"\b{re.escape(candidate)}\b", text, re.IGNORECASE):
                emisor_raw = candidate
                break
    if not emisor_raw or emisor_raw not in KNOWN_EMISORES:
        return None  # ambiguous — needs emisor
    num = res.group("num")
    year = res.group("year")
    base = f"res.{emisor_raw}.{num}.{year}"
    art = _LEY_ART_RE.search(text)
    if art:
        return base + f".art.{art.group('art')}"
    return base


# Rule 6 — Concepto / Oficio DIAN NUMBER (numeral optional; no year)
_CONCEPTO_RE = re.compile(
    r"\b(?:concepto|oficio)(?:\s+unificado)?\s*(?:dian)?\s*"
    r"(?P<num>\d+(?:-\d+)?)\b",
    re.IGNORECASE,
)
_NUMERAL_RE = re.compile(
    r"\bnum(?:eral|\.)?\s*(?P<n>\d+)\b", re.IGNORECASE
)


def _rule_concepto(text: str) -> str | None:
    if not re.search(r"\b(?:concepto|oficio)\b", text, re.IGNORECASE):
        return None
    if not re.search(r"\bdian\b", text, re.IGNORECASE):
        return None
    m = _CONCEPTO_RE.search(text)
    if not m:
        return None
    num = m.group("num")
    base = f"concepto.dian.{num}"
    nm = _NUMERAL_RE.search(text)
    if nm:
        return base + f".num.{nm.group('n')}"
    return base


# Rule 7 — Sentencia C- / T- / SU- / A- (Corte Constitucional)
_CC_RE = re.compile(
    r"\bsentencia\s*(?P<letter>c|t|su|a)-?(?P<num>\d+)\s*(?:de|del|/|-|\s)?\s*(?P<year>\d{4})\b",
    re.IGNORECASE,
)


def _rule_sent_cc(text: str) -> str | None:
    m = _CC_RE.search(text)
    if not m:
        return None
    letter = m.group("letter").upper()
    return f"sent.cc.{letter}-{m.group('num')}.{m.group('year')}"


# Rule 8 — Auto CE (Consejo de Estado) — needs base (number+year) + date.
_SPANISH_MONTHS: dict[str, str] = {
    "enero": "01",
    "febrero": "02",
    "marzo": "03",
    "abril": "04",
    "mayo": "05",
    "junio": "06",
    "julio": "07",
    "agosto": "08",
    "septiembre": "09",
    "setiembre": "09",
    "octubre": "10",
    "noviembre": "11",
    "diciembre": "12",
}

_AUTO_CE_BASE_RE = re.compile(
    r"\bauto\s+(?:de\s+)?(?:la\s+)?(?:CE\s+)?(?:secci[óo]n\s+\w+\s+)?"
    r"(?P<num>\d+)\s*(?:de|del|/|-|\s)\s*(?P<year>\d{4})\b",
    re.IGNORECASE,
)
_SENT_CE_BASE_RE = re.compile(
    r"\bsentencia\s+(?:de\s+)?(?:la\s+)?(?:CE\s+)?"
    r"(?P<num>\d+)\s*(?:de|del|/|-|\s)\s*(?P<year>\d{4})\b",
    re.IGNORECASE,
)
_DATE_SPANISH_RE = re.compile(
    r"(?P<day>\d{1,2})\s+de\s+(?P<month>enero|febrero|marzo|abril|mayo|junio|julio|"
    r"agosto|septiembre|setiembre|octubre|noviembre|diciembre)",
    re.IGNORECASE,
)
_DATE_NUMERIC_FWD_RE = re.compile(
    r"(?P<year>\d{4})[-/](?P<month>\d{2})[-/](?P<day>\d{2})"
)
_DATE_NUMERIC_REV_RE = re.compile(
    r"(?P<day>\d{1,2})[-/](?P<month>\d{2})[-/](?P<year>\d{4})"
)


def _extract_date(text: str, fallback_year: str) -> tuple[str, str, str] | None:
    """Return (year, month, day) zero-padded if a date is present anywhere."""

    m = _DATE_NUMERIC_FWD_RE.search(text)
    if m:
        return (m.group("year"), m.group("month"), m.group("day").rjust(2, "0"))
    m = _DATE_NUMERIC_REV_RE.search(text)
    if m:
        return (m.group("year"), m.group("month"), m.group("day").rjust(2, "0"))
    m = _DATE_SPANISH_RE.search(text)
    if m:
        month_name = m.group("month").lower()
        if month_name in _SPANISH_MONTHS:
            return (fallback_year, _SPANISH_MONTHS[month_name], m.group("day").rjust(2, "0"))
    return None


def _rule_auto_ce(text: str) -> str | None:
    if not re.search(r"\bauto\b", text, re.IGNORECASE):
        return None
    if not re.search(r"\bce\b|consejo\s+de\s+estado|secci[óo]n\s+(?:cuarta|primera|segunda|tercera|quinta)", text, re.IGNORECASE):
        return None
    base = _AUTO_CE_BASE_RE.search(text)
    if not base:
        return None
    num = base.group("num")
    year = base.group("year")
    date_parts = _extract_date(text, year)
    if not date_parts:
        return None
    y, m, d = date_parts
    return f"auto.ce.{num}.{y}.{m}.{d}"


def _rule_sent_ce(text: str) -> str | None:
    if not re.search(r"\bsentencia\b", text, re.IGNORECASE):
        return None
    if not re.search(r"\bce\b|consejo\s+de\s+estado|secci[óo]n\s+(?:cuarta|primera|segunda|tercera|quinta)", text, re.IGNORECASE):
        return None
    # Don't double-trigger on CC sentencias
    if re.search(r"\bsentencia\s+(?:c|t|su|a)-?\d+", text, re.IGNORECASE):
        return None
    base = _SENT_CE_BASE_RE.search(text)
    if not base:
        return None
    num = base.group("num")
    year = base.group("year")
    date_parts = _extract_date(text, year)
    if not date_parts:
        return None
    y, m, d = date_parts
    return f"sent.ce.{num}.{y}.{m}.{d}"


# Rule 10 — already-canonical norm_id (idempotency)
def _rule_idempotent(text: str) -> str | None:
    if _NORM_ID_FULL_RE.match(text):
        return text
    return None


_RULES: tuple = (
    _rule_idempotent,
    _rule_sent_cc,
    _rule_auto_ce,
    _rule_sent_ce,
    _rule_concepto,
    _rule_resolucion,
    _rule_decreto,
    _rule_ley,
    _rule_et_article,
    _rule_et_bare,
)


# ---------------------------------------------------------------------------
# Refusal diagnostics
# ---------------------------------------------------------------------------


def _diagnose_refusal(mention: str) -> str:
    text = (mention or "").strip().lower()
    if not text:
        return "empty"
    # Decreto / Ley present but the full "<keyword> N de YYYY" form not found
    if re.search(r"\b(decreto|ley)\b", text):
        if not (_DECRETO_RE.search(text) or _LEY_RE.search(text)):
            return "missing_year"
    # Article number without ET context
    if re.fullmatch(r"art(?:[íi]culo|\.)?\s*\d+(?:-\d+)?", text):
        return "no_law_prefix"
    # DIAN-flavored claim without concepto/oficio number
    if "dian" in text and not _CONCEPTO_RE.search(text):
        return "no_concept_number"
    # Sentencia mention missing CC letter prefix or CE date
    if "sentencia" in text and not (
        re.search(r"\bc-|\bt-|\bsu-|\ba-", text)
        or _SENT_CE_BASE_RE.search(text)
    ):
        return "no_court_or_letter_prefix"
    return "not_a_citation"


# ---------------------------------------------------------------------------
# Norm-id grammar (compiled regex)
# ---------------------------------------------------------------------------

# year: 4 digits
# number: digits possibly with one dash (handles ET 689-3, concepto 100208192-202)
# article number: same shape
# DUR sub-numbering: digits with internal dots (decreto.1625.2016.art.1.2.1.2.1)
# sub-unit kinds: par|inciso|num|lit
# sub-unit values: digits | 'transitorio' | 'unico' | a-z (literal)
_SUB_UNIT_PART = (
    r"(?:\.(?:par|inciso|num|lit)\."
    r"(?:transitorio|unico|[0-9]+|[a-z]))"
)

_NORM_ID_PATTERNS = (
    # ET
    rf"^et(?:\.art\.[0-9]+(?:-[0-9]+)?{_SUB_UNIT_PART}*)?$",
    # Ley
    rf"^ley\.[0-9]+(?:-[0-9]+)?\.[0-9]{{4}}(?:\.art\.[0-9]+(?:-[0-9]+)?{_SUB_UNIT_PART}*)?$",
    # Decreto (DUR allows dotted article numbers)
    rf"^decreto\.[0-9]+(?:-[0-9]+)?\.[0-9]{{4}}(?:\.art\.[0-9]+(?:[\.\-][0-9]+)*"
    rf"{_SUB_UNIT_PART}*)?$",
    # Resolución
    rf"^res\.[a-z][a-z0-9_]*\.[0-9]+(?:-[0-9]+)?\.[0-9]{{4}}"
    rf"(?:\.art\.[0-9]+(?:-[0-9]+)?{_SUB_UNIT_PART}*)?$",
    # Concepto / Oficio DIAN
    r"^concepto\.[a-z][a-z0-9_]*\.[0-9]+(?:-[0-9]+)?(?:\.num\.[0-9]+)?$",
    # Sentencia CC
    r"^sent\.cc\.(?:C|T|SU|A)-[0-9]+\.[0-9]{4}$",
    # Sentencia CE
    r"^sent\.ce\.[0-9]+\.[0-9]{4}\.[0-9]{2}\.[0-9]{2}$",
    # Auto CE
    r"^auto\.ce\.[0-9]+\.[0-9]{4}\.[0-9]{2}\.[0-9]{2}$",
)


_NORM_ID_FULL_RE = re.compile("|".join(_NORM_ID_PATTERNS))


def _normalize(text: str) -> str:
    # strip accents from common Spanish article names and keep digits/letters
    nfkd = unicodedata.normalize("NFKD", text)
    no_accents = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    # collapse whitespace
    return re.sub(r"\s+", " ", no_accents).strip()


# ---------------------------------------------------------------------------
# Helpers for callers that walk corpus prose
# ---------------------------------------------------------------------------


_MENTION_FINDERS: tuple[re.Pattern[str], ...] = (
    re.compile(r"art(?:[íi]culo|\.)?\s*\d+(?:-\d+)?\s*[^.\n]{0,40}?(?:e\.?t\.?|estatuto)", re.IGNORECASE),
    re.compile(r"(?:e\.?t\.?|estatuto\s+tributario)[^a-z0-9]{0,30}art(?:[íi]culo|\.)?\s*\d+(?:-\d+)?", re.IGNORECASE),
    re.compile(r"ley\s+\d+(?:\s*(?:de|del|/|-)?\s*\d{4})?(?:[^.\n]{0,40}?art(?:[íi]culo|\.)?\s*\d+(?:-\d+)?)?", re.IGNORECASE),
    re.compile(r"decreto\s+\d+(?:\s*(?:de|del|/|-)?\s*\d{4})?", re.IGNORECASE),
    re.compile(r"resoluci[óo]n\s+\w*\s*\d+(?:\s*(?:de|del|/|-)?\s*\d{4})?", re.IGNORECASE),
    re.compile(r"(?:concepto|oficio)(?:\s+unificado)?\s+(?:dian\s+)?\d+(?:-\d+)?(?:\s+num(?:eral|\.)?\s*\d+)?", re.IGNORECASE),
    re.compile(r"sentencia\s+(?:c|t|su|a)-?\d+\s*(?:de|del|/|-)\s*\d{4}", re.IGNORECASE),
    re.compile(r"auto\s+\d+\s*(?:de|del|/|-)?\s*\d{4}", re.IGNORECASE),
)


def _dedupe_overlapping(mentions: "list[CorpusMention]") -> "list[CorpusMention]":
    """Drop mentions whose span is fully contained inside another mention.

    Keeps the longest match; tie broken by earliest start.
    """

    if not mentions:
        return []
    sorted_ms = sorted(mentions, key=lambda m: (m.span[0], -(m.span[1] - m.span[0])))
    kept: list[CorpusMention] = []
    for m in sorted_ms:
        contained_in_existing = False
        for k in kept:
            if k.span[0] <= m.span[0] and m.span[1] <= k.span[1] and k.span != m.span:
                contained_in_existing = True
                break
        if contained_in_existing:
            continue
        kept.append(m)
    return kept


@dataclass(frozen=True)
class CorpusMention:
    """A located mention in a chunk of text — span + raw text."""

    text: str
    span: tuple[int, int]


def find_mentions(chunk_text: str) -> list[CorpusMention]:
    """Locate candidate norm mentions in arbitrary corpus prose.

    Used by the 1B-δ backfill loop. Each mention is then run through
    `canonicalize_or_refuse` independently — the refusal queue captures
    ambiguous ones.
    """

    out: list[CorpusMention] = []
    seen: set[tuple[int, int]] = set()
    for finder in _MENTION_FINDERS:
        for m in finder.finditer(chunk_text):
            span = m.span()
            if span in seen:
                continue
            seen.add(span)
            out.append(CorpusMention(text=m.group(0), span=span))
    out = _dedupe_overlapping(out)
    # sort by start offset
    out.sort(key=lambda x: x.span[0])
    return out


__all__ = [
    "CanonicalMention",
    "CorpusMention",
    "InvalidNormIdError",
    "KNOWN_EMISORES",
    "assert_valid_norm_id",
    "canonicalize",
    "canonicalize_or_refuse",
    "display_label",
    "find_mentions",
    "is_sub_unit",
    "is_valid_norm_id",
    "norm_type",
    "parent_norm_id",
    "sub_unit_kind",
]
