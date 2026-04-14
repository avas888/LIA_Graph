from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from ..legal_query_planner import plan_legal_query
from ..procedural_query_planner import plan_procedural_query
from .norm_topic_index import resolve_secondary_topics_from_norms
from .requested_period import RequestedPeriodContext


_HIGH_RISK_KEYWORDS = {
    "sancion",
    "multa",
    "inexactitud",
    "extemporaneidad",
    "plazo",
    "vencimiento",
    "umbral",
    "excepcion",
    "firmeza",
    "requerimiento",
    "fiscalizacion",
    "reconsideracion",
}

_LEGAL_DEPTH_KEYWORDS = {
    "articulo",
    "ley",
    "decreto",
    "concepto",
    "oficio",
    "jurisprudencia",
    "base legal",
    "norma",
    "dian",
    "et",
}

# Intent keywords signal the user explicitly wants a side-by-side comparison
_COMPARATIVE_INTENT_KEYWORDS = {
    "conviene",
    "vs",
    "versus",
    "comparar",
    "comparativo",
    "migrar",
    "pasarse",
    "quedarse",
    "se queda",
}
# Mention keywords name a regime but do NOT alone trigger comparative mode
_COMPARATIVE_MENTION_KEYWORDS = {
    "rst",
    "regimen simple",
    "regimen ordinario",
}

# Optimization intent: signals the user wants tax planning/reduction strategies.
# Triggers comparative_decision profile to escalate top_k and cascade_mode.
_OPTIMIZATION_INTENT_KEYWORDS = {
    "pague menos",
    "pagar menos",
    "reducir impuesto",
    "ahorrar impuesto",
    "optimizar",
    "optimizacion",
    "estrategia tributaria",
    "planeacion tributaria",
    "recomendaciones para",
    "como pagar menos",
}

_FOLLOW_UP_CONTINUITY_MARKERS = (
    "de lo que mencionas",
    "sobre ese punto",
    "en ese caso",
    "si finalmente",
    "si el cliente",
    "si decido",
    "supongamos",
    "mientras tanto",
    "y si",
    "que pasa si",
    "qué pasa si",
)


# ---------------------------------------------------------------------------
# vigencia v1.1 Phase 6 — historical intent detection
# ---------------------------------------------------------------------------
#
# Detects queries like "qué decía el Art. 188 antes de Ley 2277/2022" so that:
#  1. The intake flow can infer a heuristic `consulta_date` to propagate to
#     the retriever BEFORE it filters by `max_effective_date`.
#  2. The legal planner can set `historical_query_intent=True` on the plan,
#     which the composer reads to render a "historical narrative" block.
#
# Detection is belt-and-suspenders: intake detects first, then the planner
# re-evaluates independently in case intake missed (e.g. if the planner is
# called directly from tests or a non-intake path).

_HISTORICAL_PHRASE_RE = re.compile(
    r"\b(antes de|previo a|antes del?|originalmente|en su versión original|"
    r"en su version original|versión anterior|version anterior|"
    r"qué decía|que decia|cómo era|como era|"
    r"hace cuánto|hace cuanto|antes que|histórico|historico)\b",
    re.IGNORECASE,
)
_YEAR_ANCHOR_RE = re.compile(r"\b(19[89]\d|20[0-3]\d)\b")
_LEY_REFORMA_RE = re.compile(
    r"\bley\s*(\d{3,4})(?:\s*de\s*(\d{4}))?",
    re.IGNORECASE,
)
_REFORMA_YEAR_RE = re.compile(
    r"\breforma\s*(?:tributaria\s*)?(?:de\s*)?(\d{4})",
    re.IGNORECASE,
)


def _detect_historical_intent(query: str) -> tuple[bool, str | None]:
    """Detect whether the query carries historical temporal intent.

    Returns a tuple ``(detected, inferred_consulta_date_iso)``:
      * ``detected`` — True when any historical phrase matches. Year anchors
        alone do NOT trigger the flag (too ambiguous — could be the date of
        an ongoing transaction, not a backward-looking request).
      * ``inferred_consulta_date_iso`` — a heuristic ISO-8601 date (YYYY-12-31
        of the prior year) when both a historical phrase AND a year anchor
        are present. None otherwise.

    Heuristics:
      * "antes de YYYY" / "previo a YYYY"     → (YYYY-1)-12-31
      * "antes de Ley NNNN de YYYY"           → (YYYY-1)-12-31 (coarse)
      * "antes de la reforma YYYY"            → (YYYY-1)-12-31
      * phrase only (no year)                 → (True, None)
      * year only (no phrase)                 → (False, None)

    TODO (v2): when only a "Ley NNNN/YYYY" anchor is present, look up the
    law's actual `effective_date` in the `documents` table and subtract one
    day. For v1 we use the coarse `YYYY-1-12-31` heuristic.
    """
    text = str(query or "")
    if not text:
        return False, None

    has_phrase = bool(_HISTORICAL_PHRASE_RE.search(text))
    if not has_phrase:
        return False, None

    # Look for explicit reforma year first (most specific), then Ley N de YYYY,
    # then a bare year anchor inside the query. All produce a YYYY-1-12-31 cut.
    year: int | None = None

    reforma_match = _REFORMA_YEAR_RE.search(text)
    if reforma_match:
        try:
            year = int(reforma_match.group(1))
        except (TypeError, ValueError):
            year = None

    if year is None:
        ley_match = _LEY_REFORMA_RE.search(text)
        if ley_match:
            # Prefer the "de YYYY" group; if absent, treat the first number as
            # the law number and skip (too ambiguous on its own).
            year_group = ley_match.group(2)
            if year_group:
                try:
                    year = int(year_group)
                except (TypeError, ValueError):
                    year = None

    if year is None:
        year_match = _YEAR_ANCHOR_RE.search(text)
        if year_match:
            try:
                year = int(year_match.group(1))
            except (TypeError, ValueError):
                year = None

    if year is None or year < 1990 or year > 2039:
        return True, None

    # Coarse heuristic: "antes de 2022" → 2021-12-31
    inferred = f"{year - 1:04d}-12-31"
    return True, inferred

_CROSS_DOMAIN_RELATIONS: tuple[tuple[str, str, frozenset[str]], ...] = (
    # ── From declaracion_renta ──────────────────────────────────────────
    (
        "declaracion_renta",
        "facturacion_electronica",
        frozenset({
            "factura electronica", "factura electrónica",
            "facturacion electronica", "facturación electrónica",
            "soporte fiscal", "documento equivalente",
            "factura de venta", "requisitos de la factura",
            "771-2", "616-1", "617", "art. 771", "art. 616", "art. 617",
            # R-01: DSNOF keywords
            "dsnof", "documento soporte", "doc soporte",
            "no obligado a facturar", "no obligados a facturar",
            "documento soporte de pago",
            # R-15: Fiscalización keywords
            "fiscalizacion factura", "fiscalización factura",
            "soporte electronico", "soporte electrónico",
        }),
    ),
    (
        "declaracion_renta",
        "regimen_sancionatorio",
        frozenset({
            "sancion", "sanción", "multa", "inexactitud", "extemporaneidad",
            "sancion por no declarar", "sanción por no declarar",
            "articulo 641", "artículo 641", "articulo 647", "artículo 647",
            "regimen sancionatorio", "régimen sancionatorio",
        }),
    ),
    (
        "declaracion_renta",
        "retencion_en_la_fuente",
        frozenset({
            "retencion en la fuente", "retención en la fuente",
            "agente retenedor", "agente de retencion", "agente de retención",
            "retefuente", "retencion renta", "retención renta",
            "tabla de retencion", "tabla de retención",
        }),
    ),
    (
        "declaracion_renta",
        "informacion_exogena",
        frozenset({
            "exogena", "exógena", "informacion exogena", "información exógena",
            "medios magneticos", "medios magnéticos",
            "formato 1001", "formato 1003", "formato 1005",
            "reportes a la dian",
        }),
    ),
    (
        "declaracion_renta",
        "gravamen_movimiento_financiero_4x1000",
        frozenset({
            "4x1000", "cuatro por mil", "gmf",
            "gravamen movimiento financiero",
            "gravamen a los movimientos financieros",
        }),
    ),
    # ── R-02: renta → laboral (costos laborales, nómina electrónica) ──
    (
        "declaracion_renta",
        "laboral",
        frozenset({
            "costos laborales", "costo laboral", "gastos laborales",
            "nómina electrónica", "nomina electronica",
            "dsne", "documento soporte de nómina", "documento soporte de nomina",
            "art. 108", "artículo 108", "articulo 108",
            "deducción nómina", "deduccion nomina",
        }),
    ),
    # ── R-03: renta → NIIF (conciliación fiscal) ─────────────────────
    (
        "declaracion_renta",
        "estados_financieros_niif",
        frozenset({
            "niif fiscal", "conciliación fiscal", "conciliacion fiscal",
            "f2516", "f2517", "formato 2516", "formato 2517",
            "partidas conciliatorias", "diferencia fiscal contable",
            "diferencia niif fiscal",
        }),
    ),
    # ── R-21: renta → NIIF (descuentos, inventarios, costo adquisición) ──
    (
        "declaracion_renta",
        "estados_financieros_niif",
        frozenset({
            "descuento pronto pago", "descuento comercial", "descuento condicionado",
            "menor valor inventario", "costo adquisicion", "costo de adquisicion",
            "nic 2", "seccion 13 niif", "sección 13 niif",
            "bonificacion volumen", "bonificación volumen",
            "rebaja proveedor", "descuento compra",
        }),
    ),
    # ── From iva ────────────────────────────────────────────────────────
    (
        "iva",
        "regimen_sancionatorio",
        frozenset({
            "sancion iva", "sanción iva", "sancion por no declarar iva",
            "multa iva", "inexactitud iva",
        }),
    ),
    (
        "iva",
        "retencion_en_la_fuente",
        frozenset({
            "reteiva", "retencion iva", "retención iva",
            "retencion de iva", "retención de iva",
        }),
    ),
    (
        "iva",
        "facturacion_electronica",
        frozenset({
            "factura electronica", "factura electrónica",
            "facturacion electronica", "facturación electrónica",
            "documento equivalente", "nota credito", "nota crédito",
            # R-12+13: IVA descontable + DSNOF IVA
            "soporte iva", "dsnof iva", "no obligados iva",
            "compras no obligados", "iva descontable factura", "doc soporte iva",
        }),
    ),
    # ── From laboral ────────────────────────────────────────────────────
    (
        "laboral",
        "regimen_sancionatorio",
        frozenset({
            "sancion laboral", "sanción laboral", "multa laboral",
            "sancion por no pagar", "sanción por no pagar",
            "ugpp sancion", "ugpp sanción",
        }),
    ),
    (
        "laboral",
        "retencion_en_la_fuente",
        frozenset({
            "retencion salarios", "retención salarios",
            "retencion laboral", "retención laboral",
            "retencion nomina", "retención nómina",
        }),
    ),
    (
        "laboral",
        "contratacion_estatal",
        frozenset({
            "contratacion estatal", "contratación estatal",
            "contrato estatal", "licitacion", "licitación",
        }),
    ),
    # ── From facturacion_electronica ────────────────────────────────────
    (
        "facturacion_electronica",
        "regimen_sancionatorio",
        frozenset({
            "sancion por no facturar", "sanción por no facturar",
            "sancion facturacion", "sanción facturación",
            "multa factura", "clausura establecimiento",
            # R-09: article-based sanctions
            "art. 652", "art. 657", "652", "657",
        }),
    ),
    (
        "facturacion_electronica",
        "iva",
        frozenset({
            "iva", "impuesto a las ventas", "iva factura",
            "base gravable", "tarifa iva",
        }),
    ),
    # ── From regimen_sancionatorio (reverse) ────────────────────────────
    (
        "regimen_sancionatorio",
        "declaracion_renta",
        frozenset({
            "renta", "declaracion de renta", "declaración de renta",
            "formulario 110", "formulario 210",
        }),
    ),
    (
        "regimen_sancionatorio",
        "iva",
        frozenset({
            "iva", "declaracion de iva", "declaración de iva",
        }),
    ),
    (
        "regimen_sancionatorio",
        "facturacion_electronica",
        frozenset({
            "factura", "facturacion", "facturación",
            "factura electronica", "factura electrónica",
            # R-10: article-based FE context
            "art. 617", "requisitos factura", "art. 616-1",
        }),
    ),
    (
        "regimen_sancionatorio",
        "laboral",
        frozenset({
            "laboral", "nomina", "nómina", "ugpp",
            "seguridad social", "aportes",
            # R-11: nómina electrónica sanción
            "nómina electrónica", "nomina electronica",
            "dsne", "sanción nómina", "sancion nomina",
        }),
    ),
    # ── From retencion_fuente (reverse) ─────────────────────────────────
    (
        "retencion_en_la_fuente",
        "declaracion_renta",
        frozenset({
            "renta", "declaracion de renta", "declaración de renta",
            "depuracion", "depuración",
        }),
    ),
    (
        "retencion_en_la_fuente",
        "iva",
        frozenset({
            "iva", "reteiva", "impuesto a las ventas",
        }),
    ),
    (
        "retencion_en_la_fuente",
        "laboral",
        frozenset({
            "laboral", "salarios", "nomina", "nómina",
            # R-06: enhanced keywords
            "nómina electrónica", "nomina electronica",
            "dsne", "retención sobre salarios", "retencion sobre salarios",
            "retención salarios", "retencion salarios",
        }),
    ),
    # ── R-05: retención → RST ────────────────────────────────────────
    (
        "retencion_en_la_fuente",
        "rst_regimen_simple",
        frozenset({
            "régimen simple", "regimen simple", "rst",
            "art. 911", "artículo 911", "articulo 911",
            "contribuyente rst", "regimen simple tributacion",
            "régimen simple tributación",
        }),
    ),
    # ── R-08: retención → facturación electrónica ────────────────────
    (
        "retencion_en_la_fuente",
        "facturacion_electronica",
        frozenset({
            "factura retención", "factura retencion",
            "soporte retención", "soporte retencion",
            "factura electrónica retención", "factura electronica retencion",
            "factura electronica", "factura electrónica",
            "documento soporte retención", "documento soporte retencion",
        }),
    ),
    # ── From informacion_exogena (reverse) ──────────────────────────────
    (
        "informacion_exogena",
        "declaracion_renta",
        frozenset({
            "renta", "declaracion de renta", "declaración de renta",
        }),
    ),
    (
        "informacion_exogena",
        "facturacion_electronica",
        frozenset({
            "factura", "facturacion", "facturación",
            # R-19: cruce facturación
            "cruce facturación", "cruce facturacion",
            "factura electrónica", "factura electronica",
            "art. 616-1",
        }),
    ),
    # ── R-20: exógena → laboral (nómina electrónica) ─────────────────
    (
        "informacion_exogena",
        "laboral",
        frozenset({
            "nómina exógena", "nomina exogena",
            "cruce dsne", "cruce nómina", "cruce nomina",
            "nómina electrónica exógena", "nomina electronica exogena",
            "nómina electrónica", "nomina electronica",
        }),
    ),
    # ── R-18: GMF → renta (GMF deducción) ──────────────────────────────
    (
        "gravamen_movimiento_financiero_4x1000",
        "declaracion_renta",
        frozenset({
            "gmf deducción renta", "gmf deduccion renta",
            "deducción gmf", "deduccion gmf",
            "ttd", "tasa tributación depurada", "tasa tributacion depurada",
            "gmf renta", "4x1000 renta", "4x1000 deducción", "4x1000 deduccion",
        }),
    ),
    # ── From estados_financieros_niif ───────────────────────────────────
    (
        "estados_financieros_niif",
        "declaracion_renta",
        frozenset({
            "renta", "impuesto diferido", "conciliacion fiscal",
            "conciliación fiscal", "formato 2516", "formato 2517",
        }),
    ),
    # ── R-23: NIIF → renta (inventario fiscal, deterioro deducible) ──────
    (
        "estados_financieros_niif",
        "declaracion_renta",
        frozenset({
            "costo fiscal inventario", "inventario fiscal",
            "deterioro inventario deducible", "nic 2 fiscal",
            "medicion inventario efecto tributario",
        }),
    ),
    # ── From impuestos_saludables ─────────────────────────────────────
    (
        "impuestos_saludables",
        "iva",
        frozenset({
            "iva", "impuesto al valor agregado", "base gravable",
            "hecho generador", "tarifa",
        }),
    ),
    (
        "impuestos_saludables",
        "facturacion_electronica",
        frozenset({
            "factura", "facturación", "factura electronica",
            "factura electrónica", "documento soporte",
        }),
    ),
    (
        "impuestos_saludables",
        "regimen_sancionatorio",
        frozenset({
            "sancion", "sanción", "multa", "sanción ibua",
            "sanción icui", "clausura",
        }),
    ),
    # ── From iva → impuestos_saludables (reverse) ────────────────────
    (
        "iva",
        "impuestos_saludables",
        frozenset({
            "ibua", "icui", "bebidas azucaradas", "ultraprocesados",
            "impuestos saludables", "impuesto saludable",
        }),
    ),
    # ── From laboral → estados_financieros_niif ──────────────────────
    (
        "laboral",
        "estados_financieros_niif",
        frozenset({
            "niif", "nic 19", "beneficios empleados niif",
            "pasivo laboral niif", "prestaciones niif",
            "provisiones laborales niif",
        }),
    ),
    # ── From laboral → facturacion_electronica (nómina electrónica) ──
    (
        "laboral",
        "facturacion_electronica",
        frozenset({
            "nomina electronica", "nómina electrónica",
            "documento soporte nomina", "documento soporte nómina",
            "nota ajuste nomina", "nota ajuste nómina",
            "error nomina electronica", "error nómina electrónica",
        }),
    ),
    # ── From depreciacion_fiscal_niif ─────────────────────────────────
    (
        "depreciacion_fiscal_niif",
        "declaracion_renta",
        frozenset({
            "renta", "gasto depreciación", "deducción depreciación",
            "artículo 137", "artículo 142", "depreciación fiscal",
        }),
    ),
    (
        "depreciacion_fiscal_niif",
        "estados_financieros_niif",
        frozenset({
            "niif", "nic 16", "propiedad planta equipo",
            "valor razonable", "vida útil niif", "deterioro",
        }),
    ),
    # ── From prestaciones_sociales_niif_fiscal ────────────────────────
    (
        "prestaciones_sociales_niif_fiscal",
        "estados_financieros_niif",
        frozenset({
            "niif", "nic 19", "beneficios empleados",
            "pasivo laboral niif", "provisión niif",
        }),
    ),
    (
        "prestaciones_sociales_niif_fiscal",
        "declaracion_renta",
        frozenset({
            "renta", "deducción prestaciones", "gasto laboral renta",
            "deducción nómina", "deduccion nomina",
        }),
    ),
    # ── From cambio_doctrinal_dian (cross-cutting) ────────────────────
    (
        "cambio_doctrinal_dian",
        "declaracion_renta",
        frozenset({
            "renta", "declaración de renta", "declaracion de renta",
        }),
    ),
    (
        "cambio_doctrinal_dian",
        "iva",
        frozenset({
            "iva", "impuesto al valor agregado",
            "declaración de iva", "declaracion de iva",
        }),
    ),
    (
        "cambio_doctrinal_dian",
        "facturacion_electronica",
        frozenset({
            "factura", "facturación", "facturacion",
            "factura electrónica", "factura electronica",
        }),
    ),
    (
        "cambio_doctrinal_dian",
        "regimen_sancionatorio",
        frozenset({
            "sancion", "sanción", "régimen sancionatorio",
            "regimen sancionatorio",
        }),
    ),
    # ── Reverse: core topics → cambio_doctrinal_dian ──────────────────
    (
        "declaracion_renta",
        "cambio_doctrinal_dian",
        frozenset({
            "cambio doctrinal", "concepto unificado", "dsno",
            "cambio de criterio dian", "revocatoria concepto",
        }),
    ),
    (
        "iva",
        "cambio_doctrinal_dian",
        frozenset({
            "cambio doctrinal", "concepto unificado iva",
            "cambio de criterio dian", "dsno",
        }),
    ),
    # ── From reforma_laboral_2466 ─────────────────────────────────────
    (
        "reforma_laboral_2466",
        "regimen_sancionatorio",
        frozenset({
            "sancion", "sanción", "multa laboral",
            "sanción laboral reforma",
        }),
    ),
    (
        "reforma_laboral_2466",
        "calendario_obligaciones",
        frozenset({
            "vencimiento", "plazo", "fecha limite",
            "fecha límite", "implementación reforma",
        }),
    ),
    # ── R-CDV-01: renta → calendario (devolución / plazos) ───────────
    (
        "declaracion_renta",
        "calendario_obligaciones",
        frozenset({
            "plazo", "plazos", "vencimiento", "vencimientos",
            "calendario", "fecha limite", "fecha límite",
            "devolucion", "devolución", "saldo a favor",
            "compensacion", "compensación",
        }),
    ),
    # ── R-CDV-02: iva → calendario (devolución IVA / plazos) ─────────
    (
        "iva",
        "calendario_obligaciones",
        frozenset({
            "devolucion", "devolución", "saldo a favor",
            "compensacion", "compensación",
            "plazo", "plazos", "vencimiento", "vencimientos",
            "exportadores", "devolución iva",
        }),
    ),
    # ── R-CDV-03: renta → devoluciones (saldo a favor / compensación) ─
    (
        "declaracion_renta",
        "devoluciones_saldos_favor",
        frozenset({
            "devolucion", "devolución", "saldo a favor",
            "compensacion", "compensación",
            "formulario 1220", "artículo 850", "articulo 850",
            "reintegro",
        }),
    ),
    # ── R-CDV-04: iva → devoluciones (exportadores / saldo a favor IVA)
    (
        "iva",
        "devoluciones_saldos_favor",
        frozenset({
            "devolucion", "devolución", "saldo a favor",
            "compensacion", "compensación",
            "exportadores", "devolución iva", "devolucion iva",
            "formulario 1220", "reintegro",
        }),
    ),
    # ── R-SAG-01: renta → sagrilaft_ptee (compliance prevención lavado) ──
    (
        "declaracion_renta",
        "sagrilaft_ptee",
        frozenset({
            "sagrilaft", "ptee", "lavado de activos",
            "prevencion lavado", "prevención lavado",
            "uiaf", "ros", "reporte operacion sospechosa",
            "reporte operación sospechosa",
            "oficial de cumplimiento", "sarlaft",
            "matrices de riesgo", "debida diligencia",
            "financiacion del terrorismo", "financiación del terrorismo",
            "la/ft", "circular 100-000016",
        }),
    ),
    # ── R-SAG-02: sagrilaft_ptee → regimen_sancionatorio (sanciones SAGRILAFT)
    (
        "sagrilaft_ptee",
        "regimen_sancionatorio",
        frozenset({
            "sancion", "sanción", "multa",
            "incumplimiento sagrilaft", "supersociedades sancion",
            "supersociedades sanción", "responsabilidad oficial cumplimiento",
        }),
    ),
)


# Lightweight detector: does the question carry ANY fiscal numeric data?
# Matches: currency ($200, $200.000.000), millions (200 millones), UVT (3000 uvt), CIIU codes,
# and explicit cost/retention/loss keywords paired with numbers.
_COMPARATIVE_NUMERIC_RE = re.compile(
    r"\$\s*\d[\d.,]*"           # currency amounts
    r"|\d[\d.,]*\s*(?:millones|m(?:illones)?|mm)\b"   # million mentions
    r"|\d[\d.,]*\s*uvt\b"      # UVT amounts
    r"|\bciiu\b"               # CIIU activity code
    , re.IGNORECASE,
)

# Criteria-seeking patterns: the user asks *what to evaluate* or *what differs*
# between regimes rather than requesting a numeric comparison for a specific client.
# When present, the question is conceptual even if it includes context numbers.
_CRITERIA_SEEKING_KEYWORDS = {
    "criterios",
    "que debo evaluar",
    "qué debo evaluar",
    "que factores",
    "qué factores",
    "que diferencias",
    "qué diferencias",
    "que obligaciones",
    "qué obligaciones",
    "que actividades",
    "qué actividades",
    "cuales son los criterios",
    "cuáles son los criterios",
    "que cambia entre",
    "qué cambia entre",
    "que requisitos",
    "qué requisitos",
    "que reglas",
    "qué reglas",
    "que procedimiento",
    "qué procedimiento",
    "que proceso",
    "qué proceso",
    "como se debe calcular",
    "cómo se debe calcular",
    "como se calcula",
    "cómo se calcula",
}


def _is_criteria_seeking(message: str) -> bool:
    """Return True if the question asks about decision criteria or regime differences."""
    return _contains_keyword(message, _CRITERIA_SEEKING_KEYWORDS)


def _has_comparative_numeric_data(message: str) -> bool:
    """Return True if the message contains ANY fiscal numeric signals."""
    return bool(_COMPARATIVE_NUMERIC_RE.search(str(message or "")))


@dataclass(frozen=True)
class IntakeContext:
    risk_level: str
    needs_legal_depth: bool
    verifier_mode: str
    is_comparative_decision: bool
    response_profile: str
    is_conceptual_comparative: bool = False
    substantive_normative: bool = False
    query_nature_override: str | None = None
    accountant_need: str | None = None
    inferred_norm_candidates: tuple[str, ...] = ()
    complementary_norms: tuple[str, ...] = ()
    refined_query: str | None = None
    search_keywords: tuple[str, ...] = ()
    preferred_doc_ids: tuple[str, ...] = ()
    legal_query_diagnostics: dict[str, Any] | None = None
    procedural_query_diagnostics: dict[str, Any] | None = None
    detected_secondary_topics: tuple[str, ...] = ()
    router_secondary_topics: tuple[str, ...] = ()
    cross_domain_secondary_topics: tuple[str, ...] = ()
    cross_domain_reason: str = ""
    requested_period: RequestedPeriodContext | None = None
    message: str = ""
    # vigencia v1.1 Phase 6 — historical intent signal. The planner re-reads
    # the same regex so both sides agree even if intake is bypassed.
    historical_query_intent: bool = False
    # vigencia v1.1 Phase 6 — heuristic ISO date inferred from "antes de YYYY",
    # "antes de Ley NNNN/YYYY" or "reforma YYYY". The orchestrator threads this
    # into `PipelineCRequest.consulta_date` if the caller did not already set
    # one, so the retriever filters docs by `max_effective_date`.
    inferred_consulta_date: str | None = None


def _merge_secondary_topics(*topic_groups: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    ordered: list[str] = []
    for group in topic_groups:
        for topic in list(group or ()):
            value = str(topic or "").strip().lower()
            if not value or value in ordered:
                continue
            ordered.append(value)
    return tuple(ordered)


def _strip_accents(value: str) -> str:
    """NFKD normalize + strip combining marks for accent-insensitive matching."""
    normalized = unicodedata.normalize("NFKD", value.lower())
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _contains_keyword(text: str, words: set[str]) -> bool:
    normalized = _strip_accents((text or "").strip())
    if not normalized:
        return False
    for word in words:
        if word in normalized:
            return True
    return False


def _detect_cross_domain(message: str, primary_topic: str | None) -> tuple[tuple[str, ...], str]:
    """Detect cross-domain signals from the query text.

    Returns (secondary_topics, reason_string).
    """
    normalized = _strip_accents((message or "").strip())
    if not normalized:
        return (), ""
    hits: list[tuple[str, str]] = []
    seen_secondary: set[str] = set()
    for source_topic, secondary_topic, keywords in _CROSS_DOMAIN_RELATIONS:
        if primary_topic is not None and source_topic != primary_topic:
            continue
        if secondary_topic in seen_secondary:
            continue
        for kw in keywords:
            if _strip_accents(kw) in normalized:
                hits.append((secondary_topic, kw))
                seen_secondary.add(secondary_topic)
                break  # one match per secondary topic is enough
    if not hits:
        return (), ""
    topics = tuple(sec for sec, _ in hits)
    matched = ", ".join(f"{sec}({kw})" for sec, kw in hits)
    return topics, f"cross_domain_detected: {matched}"


def analyze_intake(
    *,
    message: str,
    response_route: str = "decision",
    topic: str | None = None,
    forced_secondary_topics: tuple[str, ...] | list[str] | None = None,
    requested_period: RequestedPeriodContext | None = None,
    conversation_state: dict[str, Any] | None = None,
) -> IntakeContext:
    route = (response_route or "decision").strip().lower() or "decision"
    legal_plan = plan_legal_query(message)
    procedural_plan = plan_procedural_query(message)
    high_risk = _contains_keyword(message, _HIGH_RISK_KEYWORDS)
    legal_signal = _contains_keyword(message, _LEGAL_DEPTH_KEYWORDS)
    has_intent = _contains_keyword(message, _COMPARATIVE_INTENT_KEYWORDS)
    has_mention = _contains_keyword(message, _COMPARATIVE_MENTION_KEYWORDS)
    optimization_signal = _contains_keyword(message, _OPTIMIZATION_INTENT_KEYWORDS)
    # Optimization intent alone is NOT comparative — it must also mention a regime
    # (RST, ordinario, etc.) to be a regime comparison.  Without a mention,
    # "optimizar la carga fiscal" is a general tax planning question.
    comparative_signal = (has_intent or optimization_signal) and has_mention
    theoretical_normative = route == "theoretical_normative"
    substantive_normative = bool(legal_plan.is_substantive_normative)
    state_payload = dict(conversation_state or {})
    state_norms = tuple(str(item or "").strip() for item in list(state_payload.get("normative_anchors") or []) if str(item or "").strip())
    state_open_subquestions = tuple(str(item or "").strip() for item in list(state_payload.get("open_subquestions") or []) if str(item or "").strip())
    continuity_followup = (
        bool(state_payload)
        and (
            any(marker in _strip_accents(message or "") for marker in _FOLLOW_UP_CONTINUITY_MARKERS)
            or (len((message or "").split()) <= 18 and bool(state_open_subquestions or state_norms))
        )
    )
    needs_legal_depth = theoretical_normative or legal_signal or substantive_normative
    if continuity_followup and state_norms:
        needs_legal_depth = True

    if high_risk and needs_legal_depth:
        verifier_mode = "strict"
    elif high_risk or needs_legal_depth:
        verifier_mode = "guided"
    else:
        verifier_mode = "fast"

    if high_risk:
        risk_level = "high"
    elif theoretical_normative or substantive_normative or legal_signal or (continuity_followup and state_norms):
        risk_level = "medium"
    else:
        risk_level = "low"

    # Conceptual comparative: comparative markers present but zero numeric data,
    # OR the user asks about criteria/differences (conceptual even with context numbers).
    criteria_seeking = _is_criteria_seeking(message)
    conceptual_comparative = comparative_signal and (
        not _has_comparative_numeric_data(message) or criteria_seeking
    )

    if theoretical_normative:
        response_profile = "theoretical_normative"
    elif substantive_normative:
        response_profile = "substantive_normative"
    elif conceptual_comparative:
        response_profile = "conceptual_comparative"
    else:
        response_profile = "comparative_decision" if comparative_signal else "procedural"

    cross_domain_secondary_topics, cross_domain_reason = _detect_cross_domain(message, topic)

    # Norm-based cross-domain detection: resolve inferred + complementary norms to topics
    all_norm_candidates = tuple(legal_plan.inferred_norm_candidates) + tuple(legal_plan.complementary_norms)
    norm_secondary_topics, norm_reason = resolve_secondary_topics_from_norms(
        all_norm_candidates, topic,
    )
    if norm_reason and cross_domain_reason:
        cross_domain_reason = f"{cross_domain_reason}; {norm_reason}"
    elif norm_reason:
        cross_domain_reason = norm_reason

    # Graph walk cross-domain detection (W8 gated, graph_edges_v1)
    graph_walk_secondary: tuple[str, ...] = ()
    graph_walk_secondary = tuple(getattr(legal_plan, "graph_walk_secondary", ()) or ())
    graph_walk_reason = str(
        (legal_plan.diagnostics.get("graph_walk") or {}).get("reason") or ""
    )
    if graph_walk_reason and cross_domain_reason:
        cross_domain_reason = f"{cross_domain_reason}; {graph_walk_reason}"
    elif graph_walk_reason:
        cross_domain_reason = graph_walk_reason

    router_secondary_topics = _merge_secondary_topics(forced_secondary_topics)
    cross_domain_secondary_topics = _merge_secondary_topics(cross_domain_secondary_topics, norm_secondary_topics, graph_walk_secondary)
    secondary_topics = _merge_secondary_topics(router_secondary_topics, cross_domain_secondary_topics)

    # vigencia v1.1 Phase 6 — detect historical intent. Produces a (flag,
    # inferred_date) pair; both are additive fields on IntakeContext. The
    # orchestrator promotes `inferred_consulta_date` into the request's
    # `consulta_date` only when the caller did not already supply one.
    historical_intent, inferred_consulta = _detect_historical_intent(message)

    return IntakeContext(
        risk_level=risk_level,
        needs_legal_depth=needs_legal_depth,
        verifier_mode=verifier_mode,
        is_comparative_decision=comparative_signal,
        is_conceptual_comparative=conceptual_comparative,
        response_profile=response_profile,
        substantive_normative=substantive_normative,
        query_nature_override=legal_plan.query_nature or procedural_plan.query_nature,
        accountant_need=(
            legal_plan.accountant_need
            or procedural_plan.accountant_need
            or ("continuity_followup" if continuity_followup else None)
        ),
        inferred_norm_candidates=tuple(legal_plan.inferred_norm_candidates),
        complementary_norms=tuple(legal_plan.complementary_norms),
        refined_query=(
            legal_plan.refined_query
            if legal_plan.refined_query and legal_plan.is_substantive_normative
            else (procedural_plan.refined_query or legal_plan.refined_query)
        ),
        search_keywords=(
            tuple(legal_plan.search_keywords)
            if legal_plan.search_keywords and legal_plan.is_substantive_normative
            else tuple(procedural_plan.search_keywords or legal_plan.search_keywords)
        ),
        preferred_doc_ids=tuple(procedural_plan.preferred_doc_ids),
        legal_query_diagnostics=legal_plan.to_dict(),
        procedural_query_diagnostics=procedural_plan.to_dict(),
        detected_secondary_topics=secondary_topics,
        router_secondary_topics=router_secondary_topics,
        cross_domain_secondary_topics=cross_domain_secondary_topics,
        cross_domain_reason=cross_domain_reason,
        requested_period=requested_period,
        message=str(message or "").strip(),
        historical_query_intent=historical_intent,
        inferred_consulta_date=inferred_consulta,
    )
