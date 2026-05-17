"""fix_v25_may.md §3.3 — Phase 3 / G10: municipal tax routing.

External SME Q11 ("ICA Bogotá territorialidad") returned national TTD/RST
content (ET 115 deducción ICA en renta, ET 240 tarifa renta, Form 2593 RST)
instead of Bogotá SHD compilación (Acuerdo 65/2002 + Decreto Distrital
352/2002). The Lia Graph corpus does not currently ingest SHD compilación
content; v25 cannot wait on a corpus run. Instead this module:

  - detects municipal / district context in the user question;
  - surfaces a deterministic canonical pointer block in the answer so the
    accountant knows WHERE to look even when the corpus is silent;
  - emits a polish directive that warns the LLM against drifting to
    national articles when the question is about territorialidad/reteICA.

Flag: ``LIA_MUNICIPAL_TAX_ROUTING={off,shadow,enforce}`` (default
``enforce``).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

__all__ = [
    "MunicipalHint",
    "detect_municipal_context",
    "municipal_pointer_block",
    "municipal_directive",
    "routing_enabled",
    "routing_mode",
]


_ENV_FLAG = "LIA_MUNICIPAL_TAX_ROUTING"


def routing_mode() -> str:
    raw = (os.getenv(_ENV_FLAG) or "enforce").strip().lower()
    if raw in {"off", "shadow", "enforce"}:
        return raw
    return "enforce"


def routing_enabled() -> bool:
    return routing_mode() != "off"


@dataclass(frozen=True)
class MunicipalHint:
    """Detection result for municipal-tax context."""

    detected: bool
    city: str | None = None
    has_territoriality: bool = False
    has_reteica: bool = False


_CITY_RX = re.compile(
    r"\b(Bogot[aá]|Medell[ií]n|Cali|Barranquilla|Bucaramanga|Cartagena|"
    r"Pereira|Manizales|Ibagu[eé]|Pasto|Santa\s+Marta|Villavicencio|"
    r"C[uú]cuta|Armenia|Neiva|Popay[aá]n|Sincelejo|Riohacha|Tunja|Mont[eé]r[ií]a|"
    r"Florencia|Yopal|Quibd[oó]|San\s+Andr[eé]s|Le[tt]icia|Aren[aa]l|Soledad)\b",
    flags=re.IGNORECASE,
)
_TERRITORIAL_RX = re.compile(
    r"\b(territorialidad|jurisdicci[oó]n\s+municipal|donde\s+se\s+ejecuta|"
    r"municipio\s+de\s+ejecuci[oó]n|actividad\s+(?:gravada\s+)?en\s+\w+|"
    r"municipal\s+donde|gravada\s+con\s+ICA\s+en)\b",
    flags=re.IGNORECASE,
)
_RETEICA_RX = re.compile(r"\b(reteICA|retenci[oó]n\s+(?:de\s+)?ICA)\b", flags=re.IGNORECASE)
_ICA_RX = re.compile(r"\b(ICA|impuesto\s+de\s+industria\s+y\s+comercio)\b", flags=re.IGNORECASE)


_CITY_NORMALISER: dict[str, str] = {
    "bogota": "Bogotá",
    "bogotá": "Bogotá",
    "medellin": "Medellín",
    "medellín": "Medellín",
    "ibague": "Ibagué",
    "ibagué": "Ibagué",
    "cucuta": "Cúcuta",
    "cúcuta": "Cúcuta",
    "monteria": "Montería",
    "montería": "Montería",
    "quibdo": "Quibdó",
    "quibdó": "Quibdó",
    "leticia": "Leticia",
    "popayan": "Popayán",
    "popayán": "Popayán",
    "san andres": "San Andrés",
    "san andrés": "San Andrés",
    "santa marta": "Santa Marta",
    "pasto": "Pasto",
    "pereira": "Pereira",
    "manizales": "Manizales",
    "tunja": "Tunja",
}


def _normalise_city(raw: str) -> str:
    return _CITY_NORMALISER.get(raw.strip().lower(), raw.strip().title())


def detect_municipal_context(question: str) -> MunicipalHint:
    if not question:
        return MunicipalHint(detected=False)

    has_ica = bool(_ICA_RX.search(question))
    has_reteica = bool(_RETEICA_RX.search(question))
    has_territoriality = bool(_TERRITORIAL_RX.search(question))
    city_match = _CITY_RX.search(question)
    city = _normalise_city(city_match.group(0)) if city_match else None

    detected = (has_ica or has_reteica) and (
        has_territoriality or has_reteica or city is not None
    )
    return MunicipalHint(
        detected=detected,
        city=city,
        has_territoriality=has_territoriality,
        has_reteica=has_reteica,
    )


_CITY_LOCAL_NORMS: dict[str, tuple[str, ...]] = {
    "Bogotá": (
        "Acuerdo Distrital 65 de 2002 (Concejo de Bogotá) — base normativa ICA",
        "Decreto Distrital 352 de 2002 — reglamentación ICA y reteICA",
        "Resoluciones SHD vigentes para tarifas por código CIIU y reteICA",
    ),
    "Medellín": (
        "Acuerdo 64 de 2012 y modificatorios (Concejo de Medellín)",
        "Decreto reglamentario municipal vigente para ICA",
    ),
    "Cali": (
        "Acuerdo 0357 de 2013 y modificatorios (Concejo de Cali)",
        "Decreto reglamentario municipal vigente para ICA",
    ),
}


def municipal_pointer_block(hint: MunicipalHint) -> str:
    """Markdown block to prepend to the answer when ``hint.detected``."""
    if not hint.detected:
        return ""

    city = hint.city or "el municipio donde se ejecuta la actividad"
    norms = _CITY_LOCAL_NORMS.get(hint.city or "", ())
    norm_lines = "\n".join(f"  - {n}" for n in norms) if norms else (
        "  - Acuerdo del Concejo Municipal vigente sobre ICA\n"
        "  - Decreto reglamentario municipal vigente"
    )

    return (
        "**Consulta normativa local.** ICA y reteICA son tributos municipales; "
        f"el alcance territorial en **{city}** se rige por normativa distrital/"
        "municipal, NO por el Estatuto Tributario nacional. Consulte además:\n"
        f"{norm_lines}\n"
        "Mantenga soporte de: contrato u orden de compra, evidencia del lugar "
        "de ejecución del servicio, factura, registro tributario municipal "
        "(RIT/RITI), certificado de reteICA practicado por el agente, "
        "y allocación contable por municipio si la actividad es "
        "multi-jurisdiccional."
    )


def municipal_directive(hint: MunicipalHint) -> str:
    """Polish-prompt directive to keep the LLM in municipal-tax mode."""
    if not hint.detected:
        return ""
    city = hint.city or "el municipio"
    return (
        "CONTEXTO MUNICIPAL DETECTADO — la pregunta es sobre ICA / reteICA "
        f"en {city}. NO contestés con artículos del Estatuto Tributario "
        "nacional (ET 115, ET 115-1, ET 240, Régimen Simple Form 2593) "
        "como si fueran la regla controlante: el ICA es municipal. "
        "Si la evidencia disponible no trae normativa distrital/municipal, "
        "señala al contador qué Acuerdo/Decreto consultar (Acuerdo del "
        "Concejo + Decreto reglamentario), describe la mecánica general "
        "(actividad gravada donde se ejecuta el servicio; reteICA practicada "
        "por el agente con cédula RIT en la jurisdicción) y deja la tarifa "
        "exacta por código CIIU como ítem a verificar — no la inventes."
    )
