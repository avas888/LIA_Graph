"""fix_v25_may.md §3.1 — Phase 1 / G8: norm-keyed retrieval boost.

Detects explicit Resolución / Decreto / Ley / Acuerdo / Concepto references
in a user question and exposes:

  - ``extract_named_norms(question)`` → list[NormRef]
  - ``norm_keyed_directive(refs)`` → polish-prompt block (empty when refs is
    empty) that nudges the LLM to cite the named norm directly in Anclaje
    Legal when the evidence carries it.
  - ``boost_chunks_by_norm_id(chunks, refs, factor=1.5)`` → optional
    rerank-time hook. Multiplies a chunk's score when its ``norm_id`` matches
    a named reference. Callers pass an iterable of mappings with ``norm_id``
    and ``score`` fields and receive a new sorted list. Safe to call with an
    empty ``refs`` (returns ``list(chunks)`` unchanged).

Flag: ``LIA_NORM_KEYED_BOOST={off,shadow,enforce}`` (default ``enforce``).

Audit Qs targeted: Q1 (Res. DIAN 000167/2021), Q7 (Res. DIAN 000233/2025),
Q8 (Res. DIAN 000164/2021), Q18 (Res. DIAN 000165/2023). The detector also
covers Acuerdo / Decreto / Ley patterns so future municipal SHD work and
labor-law citations benefit without churn.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

__all__ = [
    "NormRef",
    "extract_named_norms",
    "boost_chunks_by_norm_id",
    "norm_keyed_directive",
    "boost_enabled",
    "boost_mode",
]


_ENV_FLAG = "LIA_NORM_KEYED_BOOST"


def boost_mode() -> str:
    raw = (os.getenv(_ENV_FLAG) or "enforce").strip().lower()
    if raw in {"off", "shadow", "enforce"}:
        return raw
    return "enforce"


def boost_enabled() -> bool:
    return boost_mode() != "off"


@dataclass(frozen=True)
class NormRef:
    """A normative reference named verbatim in the user question.

    ``kind`` ∈ {res_dian, acuerdo, decreto, ley, circular, concepto, sentencia}.
    ``number`` is the zero-stripped numeric id (``"000167"`` → ``"167"``).
    ``year`` is the 4-digit issuance year when present.
    ``raw`` is the original surface span (useful for diagnostics).
    """

    kind: str
    number: str
    year: int | None
    raw: str

    def matches_norm_id(self, norm_id: str | None) -> bool:
        """True when ``norm_id`` slug points at this reference.

        Examples of accepted norm_id shapes:
            ``res_dian.0167.2021`` / ``res_dian.167.2021`` / ``resolucion_dian.167.2021``
            ``acuerdo.65.2002`` / ``decreto.352.2002`` / ``ley.43.1990``
            ``concepto_dian.191.2025`` / ``sentencia_c.123.2024``

        Norm_id forms are not yet uniform across the corpus; the matcher is
        deliberately lenient on separators and zero-padding while strict on
        kind + number + year.
        """
        if not norm_id:
            return False
        slug = norm_id.strip().lower().replace("-", "_")
        kind_aliases = _KIND_ALIASES.get(self.kind, (self.kind,))
        if not any(slug.startswith(alias) or f".{alias}." in slug for alias in kind_aliases):
            return False
        number_norm = self.number.lstrip("0") or "0"
        if number_norm not in slug.replace(".", " ").split():
            padded = f"{number_norm.zfill(4)}"
            if padded not in slug:
                return False
        if self.year is not None and str(self.year) not in slug:
            return False
        return True


_KIND_ALIASES: dict[str, tuple[str, ...]] = {
    "res_dian": ("res_dian", "resolucion_dian", "res_d", "resolucion"),
    "acuerdo": ("acuerdo", "acuerdo_distrital", "acuerdo_municipal"),
    "decreto": ("decreto", "decreto_distrital", "decreto_unico"),
    "ley": ("ley",),
    "circular": ("circular", "circular_dian"),
    "concepto": ("concepto", "concepto_dian", "oficio_dian"),
    "sentencia": ("sentencia", "sentencia_c", "sentencia_cc"),
}


# Patterns are designed to:
#   - tolerate Spanish punctuation/spacing: "Resolución DIAN N° 000167 de 2021"
#     "Resolucion 167/2021", "Res. DIAN 233 del 30 de octubre de 2025".
#   - require a 4-digit year cue so we don't match unrelated digit runs.
_RES_DIAN_RX = re.compile(
    r"\bres(?:olución|olucion|\.)?\s*(?:dian\s*)?(?:n[º°ºo]\s*)?(?:0*)(\d{1,6})"
    r"\s*(?:de|del|/)\s*(\d{4})\b",
    flags=re.IGNORECASE,
)
_DECRETO_RX = re.compile(
    r"\bdecreto\s*(?:distrital\s*|único\s*reglamentario\s*|unico\s*reglamentario\s*)?"
    r"(?:n[º°ºo]\s*)?(?:0*)(\d{1,6})\s*(?:de|del|/)\s*(\d{4})\b",
    flags=re.IGNORECASE,
)
_LEY_RX = re.compile(
    r"\bley\s*(?:n[º°ºo]\s*)?(?:0*)(\d{1,6})\s*(?:de|del|/)\s*(\d{4})\b",
    flags=re.IGNORECASE,
)
_ACUERDO_RX = re.compile(
    r"\bacuerdo\s*(?:distrital\s*|municipal\s*)?(?:n[º°ºo]\s*)?(?:0*)(\d{1,6})"
    r"\s*(?:de|del|/)\s*(\d{4})\b",
    flags=re.IGNORECASE,
)
_CIRCULAR_RX = re.compile(
    r"\bcircular\s*(?:dian\s*)?(?:n[º°ºo]\s*)?(?:0*)(\d{1,6})"
    r"\s*(?:de|del|/)\s*(\d{4})\b",
    flags=re.IGNORECASE,
)
_CONCEPTO_RX = re.compile(
    r"\b(?:concepto|oficio)\s*(?:dian\s*)?(?:n[º°ºo]\s*)?(?:0*)(\d{1,6})"
    r"\s*(?:de|del|/)\s*(\d{4})\b",
    flags=re.IGNORECASE,
)
_SENTENCIA_RX = re.compile(
    r"\bsentencia\s*(?:c\-|cc\-)?(?:0*)(\d{1,6})\s*(?:de|del|/)\s*(\d{4})\b",
    flags=re.IGNORECASE,
)


_RX_KIND_MAP: tuple[tuple[re.Pattern[str], str], ...] = (
    (_RES_DIAN_RX, "res_dian"),
    (_DECRETO_RX, "decreto"),
    (_LEY_RX, "ley"),
    (_ACUERDO_RX, "acuerdo"),
    (_CIRCULAR_RX, "circular"),
    (_CONCEPTO_RX, "concepto"),
    (_SENTENCIA_RX, "sentencia"),
)


def extract_named_norms(question: str) -> list[NormRef]:
    """Return all explicit normative references named in ``question``.

    De-duplicates on ``(kind, number, year)``. Preserves first-seen order so
    diagnostics surface the order the user mentioned them.
    """
    if not question:
        return []

    seen: set[tuple[str, str, int | None]] = set()
    refs: list[NormRef] = []
    for rx, kind in _RX_KIND_MAP:
        for match in rx.finditer(question):
            number = match.group(1)
            try:
                year = int(match.group(2))
            except (ValueError, IndexError):
                year = None
            key = (kind, number, year)
            if key in seen:
                continue
            seen.add(key)
            refs.append(NormRef(kind=kind, number=number, year=year, raw=match.group(0)))
    return refs


def norm_keyed_directive(refs: list[NormRef]) -> str:
    """Build a polish-prompt block nudging the LLM to cite the named norm.

    Empty when ``refs`` is empty (caller can append unconditionally).
    """
    if not refs:
        return ""

    label_for = {
        "res_dian": "Resolución DIAN",
        "decreto": "Decreto",
        "ley": "Ley",
        "acuerdo": "Acuerdo",
        "circular": "Circular DIAN",
        "concepto": "Concepto DIAN",
        "sentencia": "Sentencia",
    }
    lines = [
        f"- {label_for.get(r.kind, r.kind)} {r.number}"
        + (f" de {r.year}" if r.year is not None else "")
        for r in refs
    ]
    return (
        "NORMAS NOMBRADAS POR EL USUARIO: el contador citó explícitamente las "
        "siguientes normas. Si la evidencia las contiene, cítalas en Anclaje "
        "Legal con su número/año exacto. NO uses 'art. X ET' como sustituto "
        "cuando la norma aplicable es una Resolución/Acuerdo/Decreto.\n"
        + "\n".join(lines)
    )


def boost_chunks_by_norm_id(
    chunks,
    refs: list[NormRef],
    *,
    factor: float = 1.5,
):
    """Re-score ``chunks`` by multiplying score on norm_id matches.

    Each chunk must support either attribute or item access on ``norm_id``
    and ``score``. Returns a NEW list sorted by adjusted score descending.

    Safe to call with empty ``refs`` (returns ``list(chunks)`` unchanged) and
    safe to call when ``boost_enabled()`` is False (caller should still
    short-circuit at the call site to avoid wasted reads).

    ``factor`` is multiplicative; pass 1.0 to disable while keeping
    diagnostics. Mode ``shadow`` does not modify scores — caller should call
    this only when ``boost_mode() == 'enforce'``.
    """
    if not refs:
        return list(chunks)

    def _get(item, name, default=None):
        if isinstance(item, dict):
            return item.get(name, default)
        return getattr(item, name, default)

    def _set_score(item, value):
        if isinstance(item, dict):
            item["score"] = value
            return item
        try:
            setattr(item, "score", value)
        except (AttributeError, TypeError):
            pass
        return item

    rescored = []
    for chunk in chunks:
        score = float(_get(chunk, "score", 0.0) or 0.0)
        norm_id = _get(chunk, "norm_id")
        if norm_id and any(ref.matches_norm_id(norm_id) for ref in refs):
            score *= factor
        rescored.append(_set_score(chunk, score))

    rescored.sort(key=lambda c: float(_get(c, "score", 0.0) or 0.0), reverse=True)
    return rescored
