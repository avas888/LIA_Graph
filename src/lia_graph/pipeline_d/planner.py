from __future__ import annotations

from collections import OrderedDict
from dataclasses import replace
import re
import unicodedata

from ..normative_references import extract_normative_reference_mentions
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
# Query-mode classification extracted during granularize-v2 round 9.
# Re-imported so `from .planner import _looks_like_tax_planning_case`
# style imports in answer_first_bubble / answer_synthesis_helpers /
# answer_support keep working, and so internal call sites in this
# module (below) can reference them without qualification.
from .planner_query_modes import (  # noqa: F401  — re-exported
    _CORRECTION_FIRMNESS_CONTEXT_MARKERS,
    _CORRECTION_FIRMNESS_MARKERS,
    _COMPUTATION_MODE_MARKERS,
    _DEFINITION_MODE_MARKERS,
    _LOSS_COMPENSATION_CONTEXT_MARKERS,
    _LOSS_COMPENSATION_MARKERS,
    _OBLIGATION_MODE_MARKERS,
    _REFORM_MODE_MARKERS,
    _REFUND_BALANCE_CONTEXT_MARKERS,
    _REFUND_BALANCE_MARKERS,
    _TAX_PLANNING_MARKERS,
    _TAX_PLANNING_RISK_MARKERS,
    _TAX_PLANNING_STRATEGY_MARKERS,
    _classify_query_mode,
    _contains_any,
    _count_markers,
    _looks_like_correction_firmness_case,
    _looks_like_loss_compensation_case,
    _looks_like_refund_balance_case,
    _looks_like_tax_planning_case,
    _looks_like_tax_treatment_case,
    _workflow_signal,
)

_ARTICLE_CUE_RE = re.compile(r"(?i)\bart(?:[ií]culo)?s?(?:\.(?=\s|\d|$)|\b)")
_REFORM_RE = re.compile(
    r"(?i)\b(Ley|Decreto|Resoluci[oó]n)\s+(\d+)(?:\s+de\s+(\d{4}))?\b"
)
_AG_YEAR_RE = re.compile(
    r"\b(?:ag|ano\s+gravable|año\s+gravable)\s*[:\-]?\s*(20\d{2})\b",
    re.IGNORECASE,
)
_FOLLOWUP_FOCUS_MARKERS = (
    "cuentame mas",
    "cuentame mejor",
    "hablame mas",
    "explicame",
    "profundiza",
    "desarrolla",
    "amplia esto",
    "amplia ese punto",
    "sobre ese punto",
    "sobre esto",
    "de esto",
    "de eso",
    "ese punto",
    "este punto",
    "a que te refieres",
    "que significa eso",
    "como opera eso",
    "como funciona eso",
)
_FOLLOWUP_VAGUE_MARKERS = (
    "esto",
    "eso",
    "este punto",
    "ese punto",
    "de esto",
    "de eso",
    "sobre esto",
    "sobre eso",
)
_FOLLOWUP_EMBEDDED_ANSWER_STARTERS = (
    "no,",
    "si,",
    "solo cambia",
    "en la practica",
    "en la práctica",
    "recuerda que",
    "ojo con",
    "el limite",
    "el límite",
    "la regla",
)
_FOLLOWUP_EMBEDDED_ANSWER_MARKERS = (
    "solo cambia",
    "en la practica",
    "en la práctica",
    "(art.",
    "(arts.",
    " art. ",
    " arts. ",
)

_BUDGETS: dict[str, tuple[TraversalBudget, EvidenceBundleShape]] = {
    "article_lookup": (
        TraversalBudget(max_hops=1, max_nodes=6, max_edges=10, max_paths=3, max_support_documents=3),
        EvidenceBundleShape(
            primary_article_limit=3,
            connected_article_limit=3,
            related_reform_limit=2,
            support_document_limit=4,
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
    "strategy_chain": (
        TraversalBudget(max_hops=2, max_nodes=12, max_edges=20, max_paths=6, max_support_documents=6),
        EvidenceBundleShape(
            primary_article_limit=5,
            connected_article_limit=5,
            related_reform_limit=4,
            support_document_limit=6,
            snippet_char_limit=260,
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
    focus_message = _planner_followup_focus_text(message)
    normalized_focus_message = _normalize_text(focus_message or message)
    requested_topic = normalize_topic_key(request.topic or request.requested_topic)
    topic_detection = detect_topic_from_text(message)
    detected_topic = normalize_topic_key(topic_detection.topic)
    reform_refs = _extract_reform_refs(message)
    article_refs = _extract_article_refs(message)
    followup_focus = _looks_like_followup_focus_request(
        request=request,
        normalized_message=normalized_focus_message,
        article_refs=article_refs,
        reform_refs=reform_refs,
    )
    carried_article_refs = _conversation_state_article_refs(request)
    if followup_focus and not reform_refs:
        if not article_refs:
            article_refs = tuple(
                OrderedDict.fromkeys(
                    (
                        *article_refs,
                        *carried_article_refs[:3],
                    )
                )
            )
        elif len(article_refs) <= 1 and _looks_like_vague_followup_reference(normalized_focus_message):
            article_refs = tuple(
                OrderedDict.fromkeys(
                    (
                        *article_refs,
                        *carried_article_refs[:3],
                    )
                )
            )
        if carried_article_refs:
            carried_article_refs = tuple(
                ref for ref in carried_article_refs if ref in article_refs
            )
    requested_period_label, requested_period_source = _resolve_requested_period_summary(
        request=request,
        message=message,
    )
    if not requested_period_label:
        requested_period_label, requested_period_source = _carry_forward_requested_period_summary(
            request=request,
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
        followup_focus=followup_focus,
    )
    traversal_budget, evidence_shape = _BUDGETS[query_mode]

    entry_points: list[PlannerEntryPoint] = []
    for article_ref in article_refs:
        entry_points.append(
            PlannerEntryPoint(
                kind="article",
                lookup_value=article_ref,
                source=(
                    "conversation_state_anchor"
                    if article_ref in carried_article_refs
                    else "explicit_article_reference"
                ),
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
    if not article_refs and not reform_refs and _looks_like_loss_compensation_case(normalized_message):
        entry_points.append(
            PlannerEntryPoint(
                kind="article",
                lookup_value="147",
                source="loss_compensation_anchor",
                confidence=0.92,
                label="Art. 147",
                resolved_key="147",
            )
        )
    if not article_refs and not reform_refs and _looks_like_tax_planning_case(normalized_message):
        for article_key in ("869", "869-1", "869-2"):
            entry_points.append(
                PlannerEntryPoint(
                    kind="article",
                    lookup_value=article_key,
                    source="tax_planning_anchor",
                    confidence=0.9,
                    label=f"Art. {article_key}",
                    resolved_key=article_key,
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
    if followup_focus:
        planner_notes.append(
            "Planner treated the turn as a focused follow-up and tightened continuity against the active case context."
        )
    if carried_article_refs:
        planner_notes.append(
            "Planner carried forward previously cited norm anchors because the follow-up asked to double-click into a prior point."
        )
    if _looks_like_tax_planning_case(normalized_message):
        planner_notes.append(
            "Planner activated tax-planning advisory anchoring to pull anti-abuse, jurisprudence, and practical strategy evidence together."
        )
    if _looks_like_loss_compensation_case(normalized_message):
        planner_notes.append(
            "Planner treated the case as loss-compensation in renta instead of a saldo-a-favor refund/correction workflow."
        )

    sub_questions = _extract_user_sub_questions(message)

    # ingestfix-v2 Phase 6: lexical subtopic-intent detection.
    from .planner_query_modes import _detect_sub_topic_intent as _detect_intent

    sub_topic_intent = _detect_intent(
        message if isinstance(message, str) else str(message or ""),
        detected_topic,
    )

    return GraphRetrievalPlan(
        query_mode=query_mode,
        entry_points=tuple(entry_points),
        traversal_budget=traversal_budget,
        evidence_bundle_shape=evidence_shape,
        temporal_context=temporal_context,
        topic_hints=topic_hints,
        planner_notes=tuple(planner_notes),
        sub_questions=sub_questions,
        sub_topic_intent=sub_topic_intent,
    )


_SUB_QUESTION_INVERTED_RE = re.compile(r"¿([^¿?]+)\?")
_SUB_QUESTION_MIN_CHARS = 12
_SUB_QUESTION_LIMIT = 4


def _extract_user_sub_questions(message: str) -> tuple[str, ...]:
    """Return user-facing sub-questions when the consulta has 2+ of them.

    Prefers inverted-mark spans (``¿…?``) so we don't drag in preceding context;
    falls back to splitting on ``?`` when the user omitted inverted marks. Returns
    ``()`` for single-question or empty inputs so downstream shape logic can skip
    the Respuestas directas block without a separate flag.
    """
    text = str(message or "").strip()
    if not text:
        return ()
    questions: list[str] = []
    for match in _SUB_QUESTION_INVERTED_RE.finditer(text):
        body = match.group(1).strip(" .;:-—\n\t")
        if len(body) >= _SUB_QUESTION_MIN_CHARS:
            questions.append(f"¿{body}?")
    if len(questions) < 2:
        questions = []
        for segment in text.split("?"):
            trimmed = segment.strip(" .;:-—\n\t")
            if len(trimmed) < _SUB_QUESTION_MIN_CHARS:
                continue
            questions.append(trimmed + "?")
    if len(questions) < 2:
        return ()
    return tuple(OrderedDict.fromkeys(questions))[:_SUB_QUESTION_LIMIT]


def with_resolved_entry_points(
    plan: GraphRetrievalPlan,
    entry_points: tuple[PlannerEntryPoint, ...],
) -> GraphRetrievalPlan:
    return replace(plan, entry_points=entry_points)


def _extract_article_refs(message: str) -> tuple[str, ...]:
    reform_spans = tuple(match.span() for match in _REFORM_RE.finditer(message))
    hits: list[str] = []
    for reference in extract_normative_reference_mentions(message):
        locator_kind = str(reference.get("locator_kind") or "").strip().lower()
        locator_start = str(reference.get("locator_start") or "").strip()
        start = int(reference.get("start") or 0)
        if locator_kind != "articles" or not locator_start:
            continue
        if any(span_start <= start < span_end for span_start, span_end in reform_spans):
            continue
        hits.append(locator_start)
        locator_end = str(reference.get("locator_end") or "").strip()
        if locator_end:
            hits.append(locator_end)
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


def _infer_supplemental_topic_hints(
    *,
    normalized_message: str,
    requested_period_label: str | None,
    topic_scores: dict[str, float] | None,
    primary_topics: tuple[str | None, ...],
) -> tuple[str, ...]:
    hints: list[str] = []
    if _looks_like_tax_planning_case(normalized_message):
        hints.append("procedimiento_tributario")
        hints.append("declaracion_renta")
    if _looks_like_loss_compensation_case(normalized_message):
        hints.append("declaracion_renta")
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
    if _looks_like_tax_planning_case(normalized_message):
        queries.extend(
            (
                "abuso en materia tributaria proposito economico comercial simulacion fraude a la ley art 869 869-1 869-2",
                "planeacion tributaria legitima economia de opcion jurisprudencia consejo de estado art 869 869-1",
                "planeacion tributaria rst ordinario perdidas fiscales beneficio de auditoria arts 903 908 147 689-3",
                "planeacion tributaria deduccion factura electronica primer empleo donaciones ttd art 108-5 ley 2277 art 257 art 240",
                "timing de ingresos y gastos antes del cierre art 27 28 107 planeacion tributaria legitima",
            )
        )
    if _looks_like_loss_compensation_case(normalized_message):
        queries.extend(
            (
                "compensacion de perdidas fiscales renta liquida limite anual art 147",
                "perdidas fiscales compensables renta liquida ordinaria art 147",
            )
        )
        if any(
            marker in normalized_message
            for marker in (
                "firmeza",
                "termino de revision",
                "termino de firmeza",
                "beneficio de auditoria",
            )
        ):
            queries.append(
                "compensacion de perdidas fiscales firmeza declaracion termino de revision art 147 714 689-3"
            )
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


def _looks_like_followup_focus_request(
    *,
    request: PipelineCRequest,
    normalized_message: str,
    article_refs: tuple[str, ...],
    reform_refs: tuple[tuple[str, str], ...],
) -> bool:
    if not _is_followup_turn(request):
        return False
    if any(marker in normalized_message for marker in _FOLLOWUP_FOCUS_MARKERS):
        return True
    token_count = len([token for token in normalized_message.split() if token])
    if ":" in str(request.message or "") and token_count <= 40:
        return True
    if article_refs or reform_refs:
        return token_count <= 28
    return token_count <= 18


def _planner_followup_focus_text(raw_message: str) -> str:
    text = re.sub(r"\s+", " ", str(raw_message or "")).strip()
    if not text:
        return ""
    question_split = _split_question_from_embedded_followup_answer(text)
    if question_split is not None:
        return question_split[0]
    newline_split = _split_first_line_from_embedded_followup_answer(raw_message)
    if newline_split is not None:
        return newline_split[0]
    return text


def _split_question_from_embedded_followup_answer(text: str) -> tuple[str, str] | None:
    question_mark_index = text.find("?")
    if question_mark_index == -1:
        return None
    head = text[: question_mark_index + 1].strip(" :-")
    tail = text[question_mark_index + 1 :].strip(" :-")
    if not head or not tail:
        return None
    if not _looks_like_embedded_followup_answer_text(tail):
        return None
    return head, tail


def _split_first_line_from_embedded_followup_answer(raw_message: str) -> tuple[str, str] | None:
    lines = [str(line or "").strip() for line in str(raw_message or "").splitlines() if str(line or "").strip()]
    if len(lines) < 2:
        return None
    head = lines[0]
    tail = " ".join(lines[1:]).strip()
    if not head or not tail:
        return None
    if "?" not in head and len(head.split()) > 14:
        return None
    if not _looks_like_embedded_followup_answer_text(tail):
        return None
    return head, tail


def _looks_like_embedded_followup_answer_text(text: str) -> bool:
    raw = re.sub(r"\s+", " ", str(text or "")).strip()
    normalized = _normalize_text(raw)
    if not raw or len(normalized.split()) < 8:
        return False
    score = 0
    if any(normalized.startswith(marker) for marker in _FOLLOWUP_EMBEDDED_ANSWER_STARTERS):
        score += 2
    if any(marker in normalized for marker in _FOLLOWUP_EMBEDDED_ANSWER_MARKERS):
        score += 2
    if raw.count(".") >= 1 or raw.count("\n") >= 1:
        score += 1
    if _ARTICLE_CUE_RE.search(raw):
        score += 1
    return score >= 3


def _looks_like_vague_followup_reference(normalized_message: str) -> bool:
    return any(marker in normalized_message for marker in _FOLLOWUP_VAGUE_MARKERS)


def _is_followup_turn(request: PipelineCRequest) -> bool:
    state = request.conversation_state
    if isinstance(state, dict) and int(state.get("turn_count") or 0) > 0:
        return True
    return bool(str(request.conversation_context or "").strip())


def _conversation_state_article_refs(request: PipelineCRequest) -> tuple[str, ...]:
    state = request.conversation_state if isinstance(request.conversation_state, dict) else {}
    anchors = tuple(
        str(item or "").strip()
        for item in list(state.get("normative_anchors") or ())
        if str(item or "").strip()
    )
    refs: list[str] = []
    for anchor in anchors:
        refs.extend(_extract_article_refs(anchor))
    return tuple(OrderedDict.fromkeys(refs))


def _carry_forward_requested_period_summary(
    *,
    request: PipelineCRequest,
) -> tuple[str | None, str | None]:
    state = request.conversation_state if isinstance(request.conversation_state, dict) else {}
    for item in list(state.get("carry_forward_facts") or ()):
        label = _requested_period_label_from_text(str(item or ""))
        if label:
            return label, "conversation_state_fact"
    context = str(request.conversation_context or "").strip()
    if context:
        label = _requested_period_label_from_text(context)
        if label:
            return label, "conversation_context"
    return None, None


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
    label = _requested_period_label_from_text(message)
    if label is not None:
        return label, "message_ag"
    company_context = dict(request.company_context or {})
    fiscal_year = str(company_context.get("fiscal_year") or "").strip()
    if fiscal_year.isdigit() and len(fiscal_year) == 4:
        return f"AG {fiscal_year}", "company_context_fiscal_year"
    return None, None


def _requested_period_label_from_text(value: str) -> str | None:
    ag_match = _AG_YEAR_RE.search(str(value or ""))
    if ag_match is None:
        return None
    return f"AG {ag_match.group(1)}"


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
