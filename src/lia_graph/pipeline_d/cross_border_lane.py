"""fix_v25_may.md §3.2 — Phase 2 / G9: cross-border / pagos al exterior lane.

External SME audit Q14 ("software cloud sin domicilio en Colombia") was
answered as if the supplier were domestic (ET 392 withholding, factura
electrónica de venta, etc.). The controlling ET articles for cross-border
payments are 408 (retención sobre pagos al exterior), 410 (intereses
exterior), 414-1 (transporte internacional), 420 par. 3 (IVA servicios
desde el exterior), 437-2 lit. e (retención IVA a no domiciliados),
124-1 / 124-2 (no deducibilidad pagos exterior sin retención).

This module detects foreign-payment context and exposes:

  - ``detect_cross_border_context(question)`` → CrossBorderHint
  - ``canonical_articles_for(hint)`` → list of canonical ET article keys to
    surface in the polish prompt.
  - ``cross_border_directive(hint)`` → polish-prompt block. Empty when not
    detected.

Flag: ``LIA_CROSS_BORDER_LANE={off,shadow,enforce}`` (default ``enforce``).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

__all__ = [
    "CrossBorderHint",
    "canonical_articles_for",
    "cross_border_directive",
    "detect_cross_border_context",
    "lane_enabled",
    "lane_mode",
]


_ENV_FLAG = "LIA_CROSS_BORDER_LANE"


def lane_mode() -> str:
    raw = (os.getenv(_ENV_FLAG) or "enforce").strip().lower()
    if raw in {"off", "shadow", "enforce"}:
        return raw
    return "enforce"


def lane_enabled() -> bool:
    return lane_mode() != "off"


@dataclass(frozen=True)
class CrossBorderHint:
    """Detection result for cross-border context.

    ``detected`` False → no foreign-payment cue found.
    ``kind`` ∈ {services_from_abroad, royalty, technical_service,
    nonresident_dividend, cloud_software, generic_payment_abroad, unknown}.
    ``cues`` is the list of literal trigger phrases captured (de-duplicated).
    """

    detected: bool
    kind: str = "unknown"
    cues: tuple[str, ...] = field(default_factory=tuple)


# Cue families. Each is a (regex, kind_when_only_match) tuple. Order matters:
# more specific kinds first so we don't overwrite cloud_software with generic.
_CUE_FAMILIES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"\b(?:software\s+(?:en\s+la\s+)?nube|cloud(?:\s+software)?|saas|"
            r"suscripci[oó]n\s+(?:de\s+)?software)\b.*?\b(?:exterior|extranjer|"
            r"sin\s+domicilio|abroad|no\s+domiciliad)",
            flags=re.IGNORECASE | re.DOTALL,
        ),
        "cloud_software",
    ),
    (
        re.compile(
            r"\b(?:regal[ií]a|royalty|royalties|licencia\s+de\s+software|"
            r"derechos\s+de\s+autor.*exterior)\b",
            flags=re.IGNORECASE,
        ),
        "royalty",
    ),
    (
        re.compile(
            r"\b(?:servicios?\s+t[eé]cnicos?|asistencia\s+t[eé]cnica|consultor[ií]a)"
            r"\b.*?\b(?:exterior|extranjer|sin\s+domicilio|no\s+domiciliad)",
            flags=re.IGNORECASE | re.DOTALL,
        ),
        "technical_service",
    ),
    (
        re.compile(
            r"\b(?:dividendos?|utilidades?)\b.*?\b(?:no\s+residente|extranjer|"
            r"socio\s+extranjer|accionista\s+extranjer)",
            flags=re.IGNORECASE | re.DOTALL,
        ),
        "nonresident_dividend",
    ),
    (
        re.compile(
            r"\b(?:servicios?\s+desde\s+el\s+exterior|servicios?\s+prestados?\s+"
            r"desde\s+el\s+exterior|servicios?\s+importados?)\b",
            flags=re.IGNORECASE,
        ),
        "services_from_abroad",
    ),
    (
        re.compile(
            r"\b(?:pago\s+al\s+exterior|pagos?\s+al\s+exterior|remesa\s+al\s+"
            r"exterior|gir(?:o|ar)\s+al\s+exterior|proveedor\s+(?:extranjer|"
            r"sin\s+domicilio|no\s+domiciliad)|sin\s+establecimiento\s+permanente|"
            r"treaty|convenio\s+(?:de\s+)?doble\s+tributaci[oó]n|cdi\b)",
            flags=re.IGNORECASE,
        ),
        "generic_payment_abroad",
    ),
)


# Canonical ET article keys per kind. These are the articles the LLM should
# anchor on; the polish directive lists them by surface label and the
# retriever wiring (P2-T3) can use the keys to pin chunks.
_CANONICAL_ARTICLES: dict[str, tuple[tuple[str, str], ...]] = {
    "cloud_software": (
        ("et.art.420.par.3", "Art. 420 par. 3 ET — IVA servicios desde el exterior"),
        ("et.art.437-2", "Art. 437-2 ET — agentes retenedores IVA (no domiciliados)"),
        ("et.art.408", "Art. 408 ET — retención en la fuente sobre pagos al exterior"),
        ("et.art.124-1", "Art. 124-1 ET — limitación a deducción de pagos al exterior"),
        ("et.art.124-2", "Art. 124-2 ET — paraísos fiscales / no cooperantes"),
    ),
    "royalty": (
        ("et.art.408", "Art. 408 ET — retención sobre pagos al exterior"),
        ("et.art.124-1", "Art. 124-1 ET — limitación a deducción"),
        ("et.art.124-2", "Art. 124-2 ET — paraísos fiscales / no cooperantes"),
    ),
    "technical_service": (
        ("et.art.408", "Art. 408 ET — retención sobre pagos al exterior"),
        ("et.art.420.par.3", "Art. 420 par. 3 ET — IVA servicios desde el exterior"),
        ("et.art.437-2", "Art. 437-2 ET — agentes retenedores IVA"),
    ),
    "nonresident_dividend": (
        ("et.art.245", "Art. 245 ET — tarifa dividendos no residentes"),
        ("et.art.408", "Art. 408 ET — retención sobre pagos al exterior"),
        ("et.art.49", "Art. 49 ET — depuración dividendos gravados/no gravados"),
    ),
    "services_from_abroad": (
        ("et.art.420.par.3", "Art. 420 par. 3 ET — IVA servicios desde el exterior"),
        ("et.art.437-2", "Art. 437-2 ET — retención IVA a no domiciliados"),
        ("et.art.408", "Art. 408 ET — retención fuente pagos al exterior"),
    ),
    "generic_payment_abroad": (
        ("et.art.408", "Art. 408 ET — retención sobre pagos al exterior"),
        ("et.art.420.par.3", "Art. 420 par. 3 ET — IVA servicios desde el exterior"),
        ("et.art.437-2", "Art. 437-2 ET — retención IVA no domiciliados"),
        ("et.art.124-1", "Art. 124-1 ET — limitación a deducción de pagos al exterior"),
    ),
}


def detect_cross_border_context(question: str) -> CrossBorderHint:
    """Inspect ``question`` and return the strongest matching cross-border kind."""
    if not question:
        return CrossBorderHint(detected=False)

    matched_cues: list[str] = []
    matched_kind: str | None = None
    for rx, kind in _CUE_FAMILIES:
        match = rx.search(question)
        if match:
            matched_cues.append(match.group(0)[:80])
            if matched_kind is None:
                matched_kind = kind

    if matched_kind is None:
        return CrossBorderHint(detected=False)

    # De-dup cues while preserving order.
    seen: set[str] = set()
    unique_cues = []
    for c in matched_cues:
        norm = c.strip().lower()
        if norm in seen:
            continue
        seen.add(norm)
        unique_cues.append(c.strip())
    return CrossBorderHint(detected=True, kind=matched_kind, cues=tuple(unique_cues))


def canonical_articles_for(hint: CrossBorderHint) -> list[tuple[str, str]]:
    """Return the (article_key, surface_label) tuples for ``hint.kind``.

    Falls back to ``generic_payment_abroad`` when the kind is unknown.
    """
    if not hint.detected:
        return []
    return list(_CANONICAL_ARTICLES.get(hint.kind, _CANONICAL_ARTICLES["generic_payment_abroad"]))


def cross_border_directive(hint: CrossBorderHint) -> str:
    """Polish-prompt block. Empty when ``hint`` is not detected."""
    if not hint.detected:
        return ""

    articles = canonical_articles_for(hint)
    lines = [f"  - {label}" for _, label in articles]
    return (
        "CONTEXTO TRANSFRONTERIZO DETECTADO — "
        f"tipo: `{hint.kind}`. La pregunta opera sobre un pago / servicio "
        "CON el exterior. NO uses por defecto retención doméstica "
        "(art. 392 ET) ni Factura Electrónica de Venta. Las normas "
        "controlantes son:\n"
        + "\n".join(lines)
        + "\n"
        "Cubrí estos puntos: (a) clasificación del pago (servicio técnico, "
        "asistencia técnica, regalía, dividendo a no residente, software/SaaS, "
        "consultoría); (b) retención en la fuente sobre pago al exterior "
        "(tarifa según concepto); (c) IVA por servicios desde el exterior — "
        "responsabilidad del usuario en Colombia vía art. 437-2; (d) revisión "
        "de Convenio de Doble Tributación (CDI) y certificado de residencia "
        "fiscal cuando aplique; (e) documento soporte y deducibilidad bajo "
        "arts. 124-1 / 124-2 ET. NO inventes tarifas — si la evidencia no "
        "trae la tarifa específica, dí al contador que la verifique."
    )
