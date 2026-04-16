from __future__ import annotations

from collections import OrderedDict
from dataclasses import replace
import re
import unicodedata

from ..pipeline_c.contracts import PipelineCRequest
from ..pipeline_c.temporal_intent import detect_historical_intent
from ..topic_guardrails import normalize_topic_key
from ..topic_router import detect_topic_from_text
from .contracts import (
    EvidenceBundleShape,
    GraphTemporalContext,
    GraphRetrievalPlan,
    PlannerEntryPoint,
    TraversalBudget,
)

_ARTICLE_CUE_RE = re.compile(r"(?i)\bart(?:[ií]culo)?s?\.?\b")
_ARTICLE_REF_RE = re.compile(
    r"(?i)\b(?:art(?:[ií]culo)?s?|art\.)\s*(\d+(?:-\d+)?)\b"
)
_ARTICLE_BARE_RE = re.compile(r"\b(\d{1,4}(?:-\d+)?)\b")
_REFORM_RE = re.compile(
    r"(?i)\b(Ley|Decreto|Resoluci[oó]n)\s+(\d+)(?:\s+de\s+(\d{4}))?\b"
)
_AG_YEAR_RE = re.compile(
    r"\b(?:ag|ano\s+gravable|año\s+gravable)\s*[:\-]?\s*(20\d{2})\b",
    re.IGNORECASE,
)

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

_BUDGETS: dict[str, tuple[TraversalBudget, EvidenceBundleShape]] = {
    "article_lookup": (
        TraversalBudget(max_hops=1, max_nodes=6, max_edges=10, max_paths=3, max_support_documents=3),
        EvidenceBundleShape(
            primary_article_limit=2,
            connected_article_limit=3,
            related_reform_limit=2,
            support_document_limit=3,
            snippet_char_limit=220,
        ),
    ),
    "definition_chain": (
        TraversalBudget(max_hops=2, max_nodes=8, max_edges=14, max_paths=4, max_support_documents=4),
        EvidenceBundleShape(
            primary_article_limit=3,
            connected_article_limit=4,
            related_reform_limit=3,
            support_document_limit=4,
            snippet_char_limit=240,
        ),
    ),
    "obligation_chain": (
        TraversalBudget(max_hops=2, max_nodes=10, max_edges=18, max_paths=5, max_support_documents=5),
        EvidenceBundleShape(
            primary_article_limit=5,
            connected_article_limit=5,
            related_reform_limit=4,
            support_document_limit=5,
            snippet_char_limit=240,
        ),
    ),
    "computation_chain": (
        TraversalBudget(max_hops=2, max_nodes=10, max_edges=18, max_paths=5, max_support_documents=5),
        EvidenceBundleShape(
            primary_article_limit=3,
            connected_article_limit=5,
            related_reform_limit=4,
            support_document_limit=5,
            snippet_char_limit=240,
        ),
    ),
    "reform_chain": (
        TraversalBudget(max_hops=2, max_nodes=10, max_edges=18, max_paths=6, max_support_documents=4),
        EvidenceBundleShape(
            primary_article_limit=3,
            connected_article_limit=4,
            related_reform_limit=5,
            support_document_limit=4,
            snippet_char_limit=240,
        ),
    ),
    "historical_reform_chain": (
        TraversalBudget(max_hops=3, max_nodes=12, max_edges=22, max_paths=6, max_support_documents=4),
        EvidenceBundleShape(
            primary_article_limit=3,
            connected_article_limit=2,
            related_reform_limit=5,
            support_document_limit=4,
            snippet_char_limit=280,
        ),
    ),
    "general_graph_research": (
        TraversalBudget(max_hops=2, max_nodes=8, max_edges=14, max_paths=4, max_support_documents=4),
        EvidenceBundleShape(
            primary_article_limit=3,
            connected_article_limit=4,
            related_reform_limit=3,
            support_document_limit=4,
            snippet_char_limit=220,
        ),
    ),
    "historical_graph_research": (
        TraversalBudget(max_hops=3, max_nodes=10, max_edges=18, max_paths=5, max_support_documents=4),
        EvidenceBundleShape(
            primary_article_limit=3,
            connected_article_limit=3,
            related_reform_limit=4,
            support_document_limit=4,
            snippet_char_limit=280,
        ),
    ),
}


def build_graph_retrieval_plan(request: PipelineCRequest) -> GraphRetrievalPlan:
    message = str(request.message or "").strip()
    normalized_message = _normalize_text(message)
    requested_topic = normalize_topic_key(request.topic or request.requested_topic)
    topic_detection = detect_topic_from_text(message)
    detected_topic = normalize_topic_key(topic_detection.topic)
    reform_refs = _extract_reform_refs(message)
    article_refs = _extract_article_refs(message)
    requested_period_label, requested_period_source = _resolve_requested_period_summary(
        request=request,
        message=message,
    )
    supplemental_topic_hints = _infer_supplemental_topic_hints(
        normalized_message=normalized_message,
        requested_period_label=requested_period_label,
        topic_scores=topic_detection.scores,
        primary_topics=(requested_topic, detected_topic),
    )
    topic_hints = tuple(
        OrderedDict.fromkeys(
            topic
            for topic in (
                requested_topic,
                detected_topic,
                *supplemental_topic_hints,
            )
            if str(topic or "").strip()
        )
    )

    historical_intent, inferred_consulta = detect_historical_intent(message)
    temporal_context = _build_temporal_context(
        request=request,
        reform_refs=reform_refs,
        requested_period_label=requested_period_label,
        requested_period_source=requested_period_source,
        historical_intent=historical_intent,
        inferred_consulta=inferred_consulta,
    )
    query_mode = _classify_query_mode(
        normalized_message=normalized_message,
        article_refs=article_refs,
        reform_refs=reform_refs,
        temporal_context=temporal_context,
    )
    traversal_budget, evidence_shape = _BUDGETS[query_mode]

    entry_points: list[PlannerEntryPoint] = []
    for article_ref in article_refs:
        entry_points.append(
            PlannerEntryPoint(
                kind="article",
                lookup_value=article_ref,
                source="explicit_article_reference",
                confidence=0.98,
                label=f"Art. {article_ref}",
                resolved_key=article_ref,
            )
        )
    for reform_key, label in reform_refs:
        entry_points.append(
            PlannerEntryPoint(
                kind="reform",
                lookup_value=reform_key,
                source="explicit_reform_reference",
                confidence=0.96,
                label=label,
                resolved_key=reform_key,
            )
        )
    for topic_hint in topic_hints:
        entry_points.append(
            PlannerEntryPoint(
                kind="topic",
                lookup_value=topic_hint,
                source="topic_hint",
                confidence=0.72,
                label=topic_hint,
                resolved_key=topic_hint,
            )
        )

    if not article_refs and not reform_refs:
        for article_search in _build_article_search_queries(
            message=message,
            normalized_message=normalized_message,
            requested_period_label=requested_period_label,
        ):
            entry_points.append(
                PlannerEntryPoint(
                    kind="article_search",
                    lookup_value=article_search,
                    source="graph_lexical_search",
                    confidence=0.55,
                    label="lexical graph search",
                )
            )

    if not entry_points:
        entry_points.append(
            PlannerEntryPoint(
                kind="article_search",
                lookup_value=message,
                source="graph_lexical_search",
                confidence=0.45,
                label="lexical graph search",
            )
        )

    planner_notes: list[str] = []
    if requested_topic and requested_topic != detected_topic and detected_topic is not None:
        planner_notes.append(
            f"Requested topic {requested_topic} retained with auto-detected graph hint {detected_topic}."
        )
    if temporal_context.historical_query_intent:
        planner_notes.append(
            f"Historical/vigencia handling enabled with scope `{temporal_context.scope_mode}`."
        )
    elif temporal_context.cutoff_date:
        planner_notes.append(
            f"Temporal weighting enabled with cutoff date {temporal_context.cutoff_date}."
        )
    if article_refs:
        planner_notes.append(
            "Planner anchored the retrieval path on explicit article references."
        )
    elif reform_refs:
        planner_notes.append(
            "Planner anchored the retrieval path on explicit reform references."
        )
    else:
        planner_notes.append(
            "Planner will resolve entry points by lexical matching over graph article text."
        )
    if supplemental_topic_hints:
        planner_notes.append(
            "Planner added practical support topics inferred from accountant-style workflow language."
        )

    return GraphRetrievalPlan(
        query_mode=query_mode,
        entry_points=tuple(entry_points),
        traversal_budget=traversal_budget,
        evidence_bundle_shape=evidence_shape,
        temporal_context=temporal_context,
        topic_hints=topic_hints,
        planner_notes=tuple(planner_notes),
    )


def with_resolved_entry_points(
    plan: GraphRetrievalPlan,
    entry_points: tuple[PlannerEntryPoint, ...],
) -> GraphRetrievalPlan:
    return replace(plan, entry_points=entry_points)


def _extract_article_refs(message: str) -> tuple[str, ...]:
    article_cue_present = bool(_ARTICLE_CUE_RE.search(message))
    explicit = [match.group(1).strip() for match in _ARTICLE_REF_RE.finditer(message)]
    reform_spans = tuple(match.span() for match in _REFORM_RE.finditer(message))

    hits: list[str] = list(explicit)
    bare_hits: list[str] = []
    for match in _ARTICLE_BARE_RE.finditer(message):
        token = match.group(1).strip()
        if any(start <= match.start() < end for start, end in reform_spans):
            continue
        if token.isdigit():
            value = int(token)
            if 1900 <= value <= 2039:
                continue
        if "-" not in token and not article_cue_present:
            continue
        bare_hits.append(token)
    hits.extend(bare_hits)
    return tuple(OrderedDict.fromkeys(hits))


def _extract_reform_refs(message: str) -> tuple[tuple[str, str], ...]:
    refs: list[tuple[str, str]] = []
    for match in _REFORM_RE.finditer(message):
        label = match.group(0).strip()
        refs.append((_normalize_reform_key(label), label))
    dedup = OrderedDict()
    for key, label in refs:
        dedup[key] = label
    return tuple((key, label) for key, label in dedup.items())


def _classify_query_mode(
    *,
    normalized_message: str,
    article_refs: tuple[str, ...],
    reform_refs: tuple[tuple[str, str], ...],
    temporal_context: GraphTemporalContext,
) -> str:
    if temporal_context.historical_query_intent and (reform_refs or article_refs):
        return "historical_reform_chain"
    if temporal_context.historical_query_intent:
        return "historical_graph_research"
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


def _contains_any(message: str, markers: tuple[str, ...]) -> bool:
    return any(marker in message for marker in markers)


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


def _infer_supplemental_topic_hints(
    *,
    normalized_message: str,
    requested_period_label: str | None,
    topic_scores: dict[str, float] | None,
    primary_topics: tuple[str | None, ...],
) -> tuple[str, ...]:
    hints: list[str] = []
    if _looks_like_correction_firmness_case(normalized_message):
        hints.append("procedimiento_tributario")
        hints.append("declaracion_renta")
    if _looks_like_refund_balance_case(normalized_message):
        hints.append("procedimiento_tributario")
        hints.append("calendario_obligaciones")
        if "renta" in normalized_message or requested_period_label:
            hints.append("declaracion_renta")
        elif "iva" in normalized_message:
            hints.append("iva")
    hints.extend(
        _secondary_topic_hints_from_scores(
            topic_scores=topic_scores,
            primary_topics=primary_topics,
        )
    )
    return tuple(OrderedDict.fromkeys(hints))


def _build_article_search_queries(
    *,
    message: str,
    normalized_message: str,
    requested_period_label: str | None,
) -> tuple[str, ...]:
    queries: list[str] = []
    if _looks_like_correction_firmness_case(normalized_message):
        queries.extend(
            (
                "correcciones que disminuyan el valor a pagar o aumenten el saldo a favor",
                "correcciones que aumentan el impuesto o disminuyen el saldo a favor",
                "correccion declaracion renta saldo a favor plazo un ano firmeza",
                "firmeza declaraciones saldo a favor correccion termino de revision",
                "beneficio auditoria correccion declaracion renta firmeza acelerada",
            )
        )
    if _looks_like_refund_balance_case(normalized_message):
        queries.extend(
            (
                "devolucion saldo a favor requisitos procedimiento dian",
                "termino solicitar devolucion saldo a favor plazos radicacion",
                "auto inadmisorio devolucion compensacion devolucion con garantia",
                "compensacion saldo a favor obligaciones tributarias deudas del contribuyente",
            )
        )
        if "renta" in normalized_message or "declaracion" in normalized_message or requested_period_label:
            queries.extend(
                (
                    "correcciones que disminuyan el valor a pagar o aumenten el saldo a favor",
                    "firmeza declaraciones saldo a favor termino de revision",
                )
            )
            queries.append("devolucion saldo a favor renta correccion firmeza declaracion")
        elif "iva" in normalized_message:
            queries.append("devolucion saldo a favor iva plazos compensacion")
    queries.append(message)
    return tuple(
        OrderedDict.fromkeys(query.strip() for query in queries if str(query or "").strip())
    )


def _looks_like_refund_balance_case(normalized_message: str) -> bool:
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


def _secondary_topic_hints_from_scores(
    *,
    topic_scores: dict[str, float] | None,
    primary_topics: tuple[str | None, ...],
) -> tuple[str, ...]:
    if not topic_scores:
        return ()
    normalized_primary_topics = {
        normalize_topic_key(topic)
        for topic in primary_topics
        if str(topic or "").strip()
    }
    ordered_scores = sorted(
        (
            (normalize_topic_key(topic), float(score))
            for topic, score in topic_scores.items()
            if str(topic or "").strip()
        ),
        key=lambda item: (-item[1], item[0]),
    )
    if not ordered_scores:
        return ()
    top_score = ordered_scores[0][1]
    hints: list[str] = []
    for topic, score in ordered_scores:
        if not topic or topic in normalized_primary_topics:
            continue
        if score < 3.0:
            continue
        if top_score > 0 and (score / top_score) < 0.4:
            continue
        hints.append(topic)
        if len(hints) >= 2:
            break
    return tuple(hints)


def _looks_like_correction_firmness_case(normalized_message: str) -> bool:
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


def _workflow_signal(
    *,
    normalized_message: str,
    primary_markers: tuple[str, ...],
    context_markers: tuple[str, ...],
) -> int:
    primary_hits = _count_markers(normalized_message, primary_markers)
    context_hits = _count_markers(normalized_message, context_markers)
    return (primary_hits * 2) + context_hits


def _count_markers(normalized_message: str, markers: tuple[str, ...]) -> int:
    return sum(1 for marker in markers if marker in normalized_message)


def _build_temporal_context(
    *,
    request: PipelineCRequest,
    reform_refs: tuple[tuple[str, str], ...],
    requested_period_label: str | None,
    requested_period_source: str | None,
    historical_intent: bool,
    inferred_consulta: str | None,
) -> GraphTemporalContext:
    consulta_date = str(request.consulta_date or "").strip() or None
    operation_date = str(request.operation_date or "").strip() or None
    cutoff_date = consulta_date or inferred_consulta or operation_date
    cutoff_source = None
    if consulta_date:
        cutoff_source = "request_consulta_date"
    elif inferred_consulta:
        cutoff_source = "historical_intent_inference"
    elif operation_date:
        cutoff_source = "request_operation_date"

    scope_mode = "current"
    if historical_intent and reform_refs:
        scope_mode = "historical_before_reform"
    elif historical_intent and cutoff_date:
        scope_mode = "historical_as_of_date"
    elif historical_intent:
        scope_mode = "historical_open"
    elif consulta_date:
        scope_mode = "consulta_as_of_date"
    elif operation_date:
        scope_mode = "operation_as_of_date"

    notes: list[str] = []
    if historical_intent and inferred_consulta and not consulta_date:
        notes.append(
            f"Planner inferred consulta_date {inferred_consulta} from historical query wording."
        )
    if requested_period_label and requested_period_source:
        notes.append(
            f"Requested period resolved as {requested_period_label} via {requested_period_source}."
        )
    elif operation_date:
        notes.append(
            f"Operation date {operation_date} is available for temporal weighting."
        )

    return GraphTemporalContext(
        consulta_date=consulta_date,
        operation_date=operation_date,
        cutoff_date=cutoff_date,
        cutoff_source=cutoff_source,
        scope_mode=scope_mode,
        historical_query_intent=bool(historical_intent),
        requested_period_label=requested_period_label,
        requested_period_source=requested_period_source,
        anchor_reform_keys=tuple(key for key, _ in reform_refs),
        anchor_reform_labels=tuple(label for _, label in reform_refs),
        notes=tuple(notes),
    )


def _resolve_requested_period_summary(
    *,
    request: PipelineCRequest,
    message: str,
) -> tuple[str | None, str | None]:
    ag_match = _AG_YEAR_RE.search(message)
    if ag_match is not None:
        return f"AG {ag_match.group(1)}", "message_ag"
    company_context = dict(request.company_context or {})
    fiscal_year = str(company_context.get("fiscal_year") or "").strip()
    if fiscal_year.isdigit() and len(fiscal_year) == 4:
        return f"AG {fiscal_year}", "company_context_fiscal_year"
    return None, None


def _normalize_reform_key(citation: str) -> str:
    match = _REFORM_RE.search(citation)
    if match is None:
        compact = "-".join(part for part in citation.upper().replace(".", " ").split())
        return compact.replace("Ó", "O")
    prefix = _normalize_text(match.group(1)).upper()
    number = match.group(2)
    year = match.group(3) or "s_f"
    return f"{prefix}-{number}-{year}"


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text).strip().lower()


__all__ = [
    "build_graph_retrieval_plan",
    "with_resolved_entry_points",
]
