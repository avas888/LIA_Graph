"""Query-mode classification for Pipeline D planning.

Extracted from `pipeline_d/planner.py` during granularize-v2 round 9
because the host module was 1149 LOC and ~290 of them were
self-contained heuristics that answer a single question: **given the
user's normalized message (optionally enriched with article/reform refs
and temporal signals), which planning workflow does this turn belong
to?**

The returned mode feeds `GraphRetrievalPlan.query_mode` and drives
traversal-budget selection in `planner._BUDGETS`. Modes:

  * ``historical_reform_chain`` — user has an article/reform ref AND
    temporal context flagged the turn as historical.
  * ``historical_graph_research`` — temporal signals but no refs.
  * ``article_lookup`` — single article + followup-focused turn.
  * ``strategy_chain`` — tax-planning heuristic fires (planning marker
    plus risk or strategy marker).
  * ``reform_chain`` — explicit reform refs or reform-mode markers.
  * ``definition_chain`` — "qué es", "se entiende por", etc.
  * ``obligation_chain`` — "debe", "requisito", "sanción", etc.
    (also loss-compensation turns with firmeza / riesgo vocabulary.)
  * ``computation_chain`` — computation markers, tax-treatment markers,
    or loss-compensation turns without firmeza context.
  * ``general_graph_research`` — fallback.

Everything here is pure — no I/O, no DB access, no imports of stateful
modules. The host re-imports every name for back-compat so external
consumers (`answer_first_bubble`, `answer_synthesis_helpers`,
`answer_support`) keep working via `from .planner import …`.
"""

from __future__ import annotations

from ..subtopic_taxonomy_loader import (
    SubtopicTaxonomy,
    load_taxonomy as _load_subtopic_taxonomy,
    normalize_alias as _normalize_alias,
)
from .contracts import GraphTemporalContext


_SUBTOPIC_INTENT_CACHE: dict[str, SubtopicTaxonomy | None] = {}


def _get_subtopic_taxonomy() -> SubtopicTaxonomy | None:
    """Return the cached subtopic taxonomy, or None if it can't be loaded."""
    if "default" in _SUBTOPIC_INTENT_CACHE:
        return _SUBTOPIC_INTENT_CACHE["default"]
    try:
        taxonomy = _load_subtopic_taxonomy()
    except (FileNotFoundError, ValueError):
        taxonomy = None
    _SUBTOPIC_INTENT_CACHE["default"] = taxonomy
    return taxonomy


def _detect_sub_topic_intent(
    query_text: str,
    detected_topic: str | None,
    *,
    taxonomy: SubtopicTaxonomy | None = None,
) -> str | None:
    """Lexical subtopic-intent detection (Decision H1 — regex/alias match).

    Scans ``query_text`` against the full alias list of every subtopic
    under ``detected_topic``. Honors Invariant I1 (alias breadth). Ties
    are broken by longest alias first, then lexicographic by key.

    Returns the matched ``sub_topic_key`` or None when no alias fires.
    """
    if not query_text or not detected_topic:
        return None
    tax = taxonomy if taxonomy is not None else _get_subtopic_taxonomy()
    if tax is None:
        return None
    candidates = tax.get_candidates_for(detected_topic)
    if not candidates:
        return None
    normalized_query = _normalize_alias(query_text)
    if not normalized_query:
        return None
    matches: list[tuple[int, str, str]] = []
    for entry in candidates:
        for form in entry.all_surface_forms():
            normalized_form = _normalize_alias(form)
            if not normalized_form:
                continue
            if normalized_form in normalized_query:
                matches.append((len(normalized_form), entry.key, form))
                break
    if not matches:
        return None
    # Longest form wins; ties go to the alphabetically-first key.
    matches.sort(key=lambda item: (-item[0], item[1]))
    winning_key = matches[0][1]
    winning_form = matches[0][2]
    try:
        from ..instrumentation import emit_event as _emit

        _emit(
            "subtopic.retrieval.intent_detected",
            {
                "topic": detected_topic,
                "sub_topic_intent": winning_key,
                "match_via": winning_form,
            },
        )
    except Exception:  # noqa: BLE001 — observability must never block planning
        pass
    return winning_key


_REFORM_MODE_MARKERS = (
    "modific",
    "reforma",
    "vigencia",
    "vigente",
    "hist",
    "ley ",
    "decreto ",
    "resolucion ",
    "resolución ",
)
_DEFINITION_MODE_MARKERS = (
    "defin",
    "que es",
    "qué es",
    "se entiende por",
    "concepto de",
)
_OBLIGATION_MODE_MARKERS = (
    "obliga",
    "debe",
    "requisito",
    "registro",
    "actualiz",
    "sancion",
    "sanción",
    "riesgo",
    "incumpl",
    "firmeza",
    "emplazamiento",
    "requerimiento especial",
    "beneficio de auditoria",
    "beneficio de auditoría",
)
_COMPUTATION_MODE_MARKERS = (
    "calcular",
    "calculo",
    "cálculo",
    "procedencia",
    "procedente",
    "deducci",
    "deducir",
    "deducible",
    "deducibles",
    "factura",
    "retencion",
    "retención",
    "contingencia",
    "soporte",
    "costos",
    "impuesto pagado",
    "impuestos pagados",
    "impuesto descontable",
    "descuento tributario",
    "costo o gasto",
    "costo y gasto",
)
_TAX_PLANNING_MARKERS = (
    "planeacion tributaria",
    "planeacion fiscal",
    "economia de opcion",
    "estrategias de planeacion",
    "estrategias legitimas",
    "estrategia legitima",
    "planeacion legitima",
    "planeacion licita",
)
_TAX_PLANNING_RISK_MARKERS = (
    "abuso en materia tributaria",
    "abuso del derecho",
    "simulacion",
    "elusion",
    "jurisprudencia",
    "fraude a la ley",
    "proposito comercial",
    "proposito economico",
    "recaracterizar",
    "reconfigurar",
)
_TAX_PLANNING_STRATEGY_MARKERS = (
    "cierre",
    "rst",
    "ordinario",
    "perdidas fiscales",
    "beneficio de auditoria",
    "factura electronica",
    "timing",
    "deduccion",
    "descuento tributario",
    "donacion",
    "donaciones",
    "dividendos",
    "leasing",
    "nomina",
    "remuneracion",
    "compensacion",
)
_LOSS_COMPENSATION_MARKERS = (
    "compensacion de perdidas",
    "compensar perdidas",
    "perdida fiscal",
    "perdidas fiscales",
)
_LOSS_COMPENSATION_CONTEXT_MARKERS = (
    "compensacion",
    "renta liquida",
    "renta positiva",
    "anos anteriores",
    "ano gravable",
    "ag ",
    "limite anual",
    "declaracion",
    "firmeza",
)
_REFUND_BALANCE_MARKERS = (
    "devolucion",
    "compensacion",
    "auto inadmisorio",
    "devolucion improcedente",
    "devolucion con garantia",
)
_REFUND_BALANCE_CONTEXT_MARKERS = (
    "saldo a favor",
    "procedimiento",
    "requisito",
    "requisitos",
    "radic",
    "plazo",
    "plazos",
    "tramite",
    "solicitar",
    "solicitud",
    "garantia",
    "inadmis",
)
_CORRECTION_FIRMNESS_MARKERS = (
    "corregir",
    "correccion",
    "firmeza",
    "emplazamiento",
    "requerimiento especial",
    "liquidacion oficial",
    "beneficio de auditoria",
)
_CORRECTION_FIRMNESS_CONTEXT_MARKERS = (
    "declaracion",
    "renta",
    "impuesto",
    "saldo a favor",
    "revision",
)


def _contains_any(message: str, markers: tuple[str, ...]) -> bool:
    return any(marker in message for marker in markers)


def _count_markers(normalized_message: str, markers: tuple[str, ...]) -> int:
    return sum(1 for marker in markers if marker in normalized_message)


def _workflow_signal(
    *,
    normalized_message: str,
    primary_markers: tuple[str, ...],
    context_markers: tuple[str, ...],
) -> int:
    primary_hits = _count_markers(normalized_message, primary_markers)
    context_hits = _count_markers(normalized_message, context_markers)
    return (primary_hits * 2) + context_hits


def _looks_like_tax_treatment_case(normalized_message: str) -> bool:
    treatment_markers = (
        "puedo deducir",
        "se puede deducir",
        "es deducible",
        "es procedente",
        "procedencia",
        "procedente",
        "deducir",
        "deducible",
        "deduccion",
        "deducción",
        "impuesto pagado",
        "impuestos pagados",
        "descuento tributario",
        "costo o gasto",
        "costo y gasto",
    )
    return any(marker in normalized_message for marker in treatment_markers)


def _looks_like_tax_planning_case(normalized_message: str) -> bool:
    has_planning_marker = any(marker in normalized_message for marker in _TAX_PLANNING_MARKERS)
    has_risk_marker = any(marker in normalized_message for marker in _TAX_PLANNING_RISK_MARKERS)
    has_strategy_marker = any(marker in normalized_message for marker in _TAX_PLANNING_STRATEGY_MARKERS)
    if has_planning_marker and has_risk_marker:
        return True
    if has_planning_marker and has_strategy_marker:
        return True
    return has_risk_marker and "planeacion" in normalized_message


def _looks_like_loss_compensation_case(normalized_message: str) -> bool:
    loss_primary_hits = _count_markers(normalized_message, _LOSS_COMPENSATION_MARKERS)
    if loss_primary_hits == 0:
        return False
    loss_score = _workflow_signal(
        normalized_message=normalized_message,
        primary_markers=_LOSS_COMPENSATION_MARKERS,
        context_markers=_LOSS_COMPENSATION_CONTEXT_MARKERS,
    )
    refund_score = _workflow_signal(
        normalized_message=normalized_message,
        primary_markers=_REFUND_BALANCE_MARKERS,
        context_markers=_REFUND_BALANCE_CONTEXT_MARKERS,
    )
    correction_score = _workflow_signal(
        normalized_message=normalized_message,
        primary_markers=_CORRECTION_FIRMNESS_MARKERS,
        context_markers=_CORRECTION_FIRMNESS_CONTEXT_MARKERS,
    )
    return loss_score >= 4 and loss_score >= refund_score and loss_score >= correction_score


def _looks_like_refund_balance_case(normalized_message: str) -> bool:
    if _looks_like_loss_compensation_case(normalized_message):
        return False
    refund_primary_hits = _count_markers(normalized_message, _REFUND_BALANCE_MARKERS)
    if refund_primary_hits == 0:
        return False
    refund_score = _workflow_signal(
        normalized_message=normalized_message,
        primary_markers=_REFUND_BALANCE_MARKERS,
        context_markers=_REFUND_BALANCE_CONTEXT_MARKERS,
    )
    correction_score = _workflow_signal(
        normalized_message=normalized_message,
        primary_markers=_CORRECTION_FIRMNESS_MARKERS,
        context_markers=_CORRECTION_FIRMNESS_CONTEXT_MARKERS,
    )
    return refund_score >= 4 and refund_score > correction_score


def _looks_like_correction_firmness_case(normalized_message: str) -> bool:
    if _looks_like_loss_compensation_case(normalized_message):
        return False
    correction_primary_hits = _count_markers(
        normalized_message,
        _CORRECTION_FIRMNESS_MARKERS,
    )
    if correction_primary_hits == 0:
        return False
    correction_score = _workflow_signal(
        normalized_message=normalized_message,
        primary_markers=_CORRECTION_FIRMNESS_MARKERS,
        context_markers=_CORRECTION_FIRMNESS_CONTEXT_MARKERS,
    )
    refund_score = _workflow_signal(
        normalized_message=normalized_message,
        primary_markers=_REFUND_BALANCE_MARKERS,
        context_markers=_REFUND_BALANCE_CONTEXT_MARKERS,
    )
    return correction_score >= 4 and correction_score >= refund_score


def _classify_query_mode(
    *,
    normalized_message: str,
    article_refs: tuple[str, ...],
    reform_refs: tuple[tuple[str, str], ...],
    temporal_context: GraphTemporalContext,
    followup_focus: bool,
) -> str:
    if temporal_context.historical_query_intent and (reform_refs or article_refs):
        return "historical_reform_chain"
    if temporal_context.historical_query_intent:
        return "historical_graph_research"
    if followup_focus and article_refs and not reform_refs:
        return "article_lookup"
    if _looks_like_tax_planning_case(normalized_message):
        return "strategy_chain"
    if _looks_like_loss_compensation_case(normalized_message):
        if any(
            marker in normalized_message
            for marker in (
                "firmeza",
                "regimen legal",
                "precaucion",
                "precauciones",
                "riesgo",
                "declaracion",
            )
        ):
            return "obligation_chain"
        return "computation_chain"
    if reform_refs or _contains_any(normalized_message, _REFORM_MODE_MARKERS):
        return "reform_chain"
    if _contains_any(normalized_message, _DEFINITION_MODE_MARKERS):
        return "definition_chain"
    if _contains_any(normalized_message, _OBLIGATION_MODE_MARKERS):
        return "obligation_chain"
    if _looks_like_tax_treatment_case(normalized_message):
        return "computation_chain"
    if _contains_any(normalized_message, _COMPUTATION_MODE_MARKERS):
        return "computation_chain"
    if len(article_refs) == 1:
        return "article_lookup"
    return "general_graph_research"
