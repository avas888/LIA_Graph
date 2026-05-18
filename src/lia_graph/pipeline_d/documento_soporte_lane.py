"""fix_v25_may.md P12 — documento-soporte lane.

External SME audit Q1 ("documento soporte SAS comprando servicios a persona
natural no obligada") returned a generic costos/deducciones answer polluted
with zona-franca content. The controlling norms are:

  - Art. 771-2 ET — procedencia de costos / deducciones / impuestos
    descontables; requisitos del documento soporte y casos de no obligación
    de factura.
  - Resolución DIAN 000167 de 2021 — implementa el documento soporte en
    adquisiciones efectuadas a sujetos no obligados a expedir factura
    (numeración, requisitos, transmisión electrónica, generación CUDS).
  - Decreto 358 de 2020 — reglamenta la factura electrónica y sus
    documentos equivalentes (incluye documento soporte).
  - Art. 615 ET — obligación de expedir factura.
  - Art. 616-1 ET — sistema de factura electrónica.
  - Art. 617 ET — requisitos formales.

This module detects the documento-soporte context and surfaces a polish-
prompt directive listing these anchors so the answer cannot drift into
unrelated zona-franca or general renta content.

Flag: ``LIA_DOCUMENTO_SOPORTE_LANE={off,shadow,enforce}`` (default
``enforce``).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

__all__ = [
    "DocumentoSoporteHint",
    "canonical_anchors_for",
    "detect_documento_soporte_context",
    "documento_soporte_directive",
    "lane_enabled",
    "lane_mode",
]


_ENV_FLAG = "LIA_DOCUMENTO_SOPORTE_LANE"


def lane_mode() -> str:
    raw = (os.getenv(_ENV_FLAG) or "enforce").strip().lower()
    if raw in {"off", "shadow", "enforce"}:
        return raw
    return "enforce"


def lane_enabled() -> bool:
    return lane_mode() != "off"


@dataclass(frozen=True)
class DocumentoSoporteHint:
    detected: bool
    cues: tuple[str, ...] = field(default_factory=tuple)


# Multi-cue detector: question must mention "documento soporte" (or close
# synonym) AND a no-obligado-a-facturar context — otherwise generic
# questions about facturación electrónica won't trip the lane.
_DOC_SOPORTE_RX = re.compile(
    r"\b(documento\s+soporte|soporte\s+(?:en\s+)?adquisiciones?|"
    r"documento\s+equivalente\s+a\s+factura|adquisici[oó]n\s+(?:efectuada\s+)?"
    r"a\s+sujetos?\s+no\s+obligados?)\b",
    flags=re.IGNORECASE,
)
_NO_OBLIGADO_RX = re.compile(
    r"\b(no\s+obligad[oa]s?\s+(?:a\s+)?(?:expedir|emitir|facturar)|"
    r"sujetos?\s+no\s+obligad[oa]s?|persona\s+natural\s+no\s+obligad|"
    r"no\s+responsable\s+(?:de\s+)?IVA|r[eé]gimen\s+simplificado)\b",
    flags=re.IGNORECASE,
)


_CANONICAL_ANCHORS: tuple[tuple[str, str], ...] = (
    ("et.art.771-2", "Art. 771-2 ET — procedencia de costos, deducciones e impuestos descontables (documento soporte como respaldo cuando no hay obligación de facturar)"),
    ("res_dian.0167.2021", "Resolución DIAN 000167 de 2021 — implementa el documento soporte en adquisiciones efectuadas a sujetos no obligados a expedir factura (numeración autorizada, requisitos, transmisión electrónica, CUDS)"),
    ("decreto.358.2020", "Decreto 358 de 2020 — reglamenta la factura electrónica y los documentos equivalentes / soporte"),
    ("et.art.615", "Art. 615 ET — obligación de expedir factura y casos de no obligación"),
    ("et.art.616-1", "Art. 616-1 ET — sistema de factura electrónica de venta y documentos electrónicos"),
    ("et.art.617", "Art. 617 ET — requisitos formales de la factura"),
)


def detect_documento_soporte_context(question: str) -> DocumentoSoporteHint:
    """Detect "documento soporte" + "no obligado a facturar" context.

    Both cues must fire — keeps the lane narrow so generic FE questions
    don't pick up the documento-soporte directive.
    """
    if not question:
        return DocumentoSoporteHint(detected=False)
    doc_match = _DOC_SOPORTE_RX.search(question)
    no_obl_match = _NO_OBLIGADO_RX.search(question)
    if not (doc_match and no_obl_match):
        return DocumentoSoporteHint(detected=False)
    cues = (doc_match.group(0).strip(), no_obl_match.group(0).strip())
    return DocumentoSoporteHint(detected=True, cues=cues)


def canonical_anchors_for(hint: DocumentoSoporteHint) -> list[tuple[str, str]]:
    if not hint.detected:
        return []
    return list(_CANONICAL_ANCHORS)


def documento_soporte_directive(hint: DocumentoSoporteHint) -> str:
    if not hint.detected:
        return ""
    anchors = canonical_anchors_for(hint)
    lines = [f"  - {label}" for _, label in anchors]
    return (
        "CONTEXTO DETECTADO: documento soporte en adquisiciones a no "
        "obligados a expedir factura. Las normas controlantes son:\n"
        + "\n".join(lines)
        + "\n"
        "Cubrí estos puntos: (a) cuándo procede el documento soporte (no "
        "facturable: PN no comerciantes sin establecimiento; proveedor del "
        "exterior con reglas especiales DSE); (b) requisitos formales "
        "(denominación, nombres y NIT/cédula del vendedor, NIT del "
        "adquirente, fecha, descripción del bien o servicio, valor); "
        "(c) numeración autorizada por la DIAN y transmisión electrónica "
        "con CUDS; (d) manejo de retenciones en la fuente (servicios 4 % / "
        "6 %, honorarios 10 % / 11 %, técnicos 6 % / 10 %; regla 3.300 UVT "
        "para PN no declarante); (e) IVA NO se incluye en la base de "
        "retención. NO menciones zona franca, doble tarifa, Ley 2277/2022 "
        "art. 11, MinCIT ni Art. 240-1 ET — esos temas no son la consulta."
    )
