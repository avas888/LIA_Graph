"""fix_v25_may.md §3.9 — Phase 9 / G16: counterfactual-example detector.

The external SME audit caught the LLM inserting named persons, companies,
and monetary facts that exist in NEITHER the user's question NOR the
retrieved evidence:

  - Q8 RUB: invented person "Carlos Moreno Pérez".
  - Q16 transfer pricing: injected Panama 1,930M (user's facts were
    6,000M operations + 18,000M patrimonio).
  - Q17 tax losses: invented company "InnovaLab".

This module scans polished answers for entity-shaped tokens (proper-name
triples, corporate-suffix tokens, large peso amounts) and flags every
token that does not appear in the question or evidence. A stop-list of
legitimate institutional names (DIAN, UGPP, MinHacienda, Concejo Nacional)
prevents false positives.

Flag: ``LIA_COUNTERFACTUAL_DETECTOR={off,shadow,enforce}`` (default
``enforce``).
"""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass

__all__ = [
    "CounterfactualEntity",
    "detect_counterfactual_entities",
    "detector_enabled",
    "detector_mode",
]


_ENV_FLAG = "LIA_COUNTERFACTUAL_DETECTOR"


def detector_mode() -> str:
    raw = (os.getenv(_ENV_FLAG) or "enforce").strip().lower()
    if raw in {"off", "shadow", "enforce"}:
        return raw
    return "enforce"


def detector_enabled() -> bool:
    return detector_mode() != "off"


@dataclass(frozen=True)
class CounterfactualEntity:
    kind: str  # person_name | company_name | monetary_fact
    surface: str


# Person-name pattern — two or three capitalised tokens with Spanish accents.
_PERSON_NAME_RX = re.compile(
    r"\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,2})\b"
)
# Company-name pattern — capitalised words ending in a Colombian corporate
# suffix (SAS, S.A.S., LTDA, S.A.).
_COMPANY_NAME_RX = re.compile(
    r"\b([A-Z][A-Za-z0-9ÁÉÍÓÚÑáéíóúñ\-]+(?:\s+[A-Za-zÁÉÍÓÚÑáéíóúñ\-]+){0,4}"
    r"\s+(?:SAS|S\.A\.S\.|LTDA|S\.A\.))\b"
)
# Monetary-fact pattern — amounts of at least 4 digits OR an "M / millones / MM" suffix.
_MONETARY_RX = re.compile(
    r"\$?\s*\d{1,3}(?:[.,]\d{3}){1,5}(?:[.,]\d+)?(?:\s*(?:M|MM|millones))?",
    flags=re.IGNORECASE,
)


# Institutional stop-list. These match by lowercase comparison so accents and
# casing don't trip us. Add new ones case-by-case rather than relaxing the
# regex.
_SPANISH_LEADING_NOISE = frozenset(
    {
        "la",
        "el",
        "los",
        "las",
        "un",
        "una",
        "unos",
        "unas",
        "este",
        "esta",
        "esos",
        "esas",
        "su",
        "sus",
        "nuestro",
        "nuestra",
        "para",
        "por",
        "de",
        "del",
        "al",
        "con",
        "sin",
    }
)

_LEGAL_DOMAIN_NOUNS = frozenset(
    {
        "ley",
        "leyes",
        "decreto",
        "decretos",
        "resolucion",
        "resolución",
        "resoluciones",
        "concepto",
        "conceptos",
        "circular",
        "circulares",
        "acuerdo",
        "acuerdos",
        "sentencia",
        "sentencias",
        "oficio",
        "oficios",
        "auto",
        "autos",
        "estatuto",
        "código",
        "codigo",
        "sección",
        "seccion",
        "art",
        "art.",
        "artículo",
        "articulo",
        "art°",
    }
)

_INSTITUTIONAL_STOPLIST = frozenset(
    name.lower()
    for name in (
        "DIAN",
        "UGPP",
        "MinHacienda",
        "Ministerio de Hacienda",
        "Ministerio del Trabajo",
        "MinTrabajo",
        "Banco de la República",
        "Superintendencia de Sociedades",
        "Supersociedades",
        "Supersolidaria",
        "Superfinanciera",
        "Superintendencia Financiera",
        "Consejo Nacional",
        "Corte Constitucional",
        "Corte Suprema",
        "Consejo de Estado",
        "Junta Central de Contadores",
        "JCC",
        "Concejo de Bogotá",
        "Concejo Distrital",
        "SHD",
        "Secretaría de Hacienda",
        "Cámara de Comercio",
        "Confecámaras",
        "Bogotá D.C.",
        "Bogotá",
        "Medellín",
        "Cali",
        "Barranquilla",
        "Cartagena",
        "Bucaramanga",
        "Pereira",
        "Manizales",
        "Sección 20",
        "Sección 11",
        "Sección 29",
        "Estatuto Tributario",
        "Código Sustantivo del Trabajo",
        "Código de Comercio",
        "Régimen Tributario Especial",
        "Régimen Simple",
        "República de Colombia",
    )
)


def _normalise_text(text: str) -> str:
    """Lower-case and ASCII-fold a string for haystack comparison."""
    folded = unicodedata.normalize("NFKD", text)
    return "".join(c for c in folded if not unicodedata.combining(c)).lower()


def _is_stoplist(surface: str) -> bool:
    norm = surface.strip().lower()
    if norm in _INSTITUTIONAL_STOPLIST:
        return True
    # Allow generic prefixes like "Resolución DIAN" or "Decreto Distrital".
    legal_prefixes = (
        "art.",
        "art ",
        "artículo",
        "ley",
        "decreto",
        "resolución",
        "resolucion",
        "concepto",
        "circular",
        "acuerdo",
        "sentencia",
    )
    if any(norm.startswith(p) for p in legal_prefixes):
        return True
    return False


def _present_in(haystack_norm: str, surface: str) -> bool:
    return _normalise_text(surface) in haystack_norm


def _normalise_amount(token: str) -> str:
    """Strip thousands separators / whitespace; preserve sign of mantissa."""
    return re.sub(r"[^\d]", "", token)


def detect_counterfactual_entities(
    question: str,
    evidence_text: str,
    polished: str,
    *,
    template: str | None = None,
) -> list[CounterfactualEntity]:
    """Return entities surfaced in ``polished`` but absent from question +
    evidence (+ optional template).

    Each finding is unique on ``surface``. Stop-list tokens are skipped.
    """
    if not polished:
        return []

    haystack_raw = " ".join(part for part in (question or "", evidence_text or "", template or "") if part)
    haystack_norm = _normalise_text(haystack_raw)

    findings: list[CounterfactualEntity] = []
    seen_surfaces: set[str] = set()

    # Person names.
    for match in _PERSON_NAME_RX.finditer(polished):
        surface = match.group(1).strip()
        if surface in seen_surfaces or _is_stoplist(surface):
            continue
        tokens = surface.split()
        if all(len(t) <= 2 for t in tokens):
            continue
        # Spanish leading determiners + sentence-starting noise. "La Ley",
        # "El Decreto", "Una Resolución" should not be flagged as a person
        # name regardless of haystack presence.
        if tokens[0].lower() in _SPANISH_LEADING_NOISE:
            continue
        # If any token is itself a legal-domain noun (Ley, Decreto, etc.),
        # the span is a norm reference, not a person.
        if any(t.lower() in _LEGAL_DOMAIN_NOUNS for t in tokens):
            continue
        if _present_in(haystack_norm, surface):
            continue
        findings.append(CounterfactualEntity(kind="person_name", surface=surface))
        seen_surfaces.add(surface)

    # Company names.
    for match in _COMPANY_NAME_RX.finditer(polished):
        surface = match.group(1).strip()
        if surface in seen_surfaces or _is_stoplist(surface):
            continue
        if _present_in(haystack_norm, surface):
            continue
        findings.append(CounterfactualEntity(kind="company_name", surface=surface))
        seen_surfaces.add(surface)

    # Monetary facts. Flag amounts ≥ 1,000,000 in pesos. Treat any amount
    # carrying a "millones"/"MM"/"M" suffix as already in the millions bracket
    # so "1.930 millones" (= COP 1.93 billion) is captured even when its bare
    # digit count is only 4.
    haystack_amounts: set[str] = {
        _normalise_amount(m.group(0)) for m in _MONETARY_RX.finditer(haystack_raw)
    }
    for match in _MONETARY_RX.finditer(polished):
        surface = match.group(0).strip()
        normalised = _normalise_amount(surface)
        if not normalised:
            continue
        has_millones_suffix = bool(
            re.search(r"\b(?:M|MM|millones)\b", surface, flags=re.IGNORECASE)
        )
        if not has_millones_suffix and len(normalised) < 7:
            continue
        if normalised in haystack_amounts:
            continue
        if surface in seen_surfaces:
            continue
        findings.append(CounterfactualEntity(kind="monetary_fact", surface=surface))
        seen_surfaces.add(surface)

    return findings
