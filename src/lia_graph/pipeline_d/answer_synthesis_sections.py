from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

from ..pipeline_c.contracts import PipelineCRequest
from .answer_policy import (
    DIRECT_ANSWER_BULLETS_PER_QUESTION,
    DIRECT_ANSWER_COVERAGE_PENDING,
)
from .answer_shared import (
    anchor_query_tokens,
    append_unique,
    extract_change_mentions,
    line_has_legal_reference,
    normalize_text,
    published_context_lines,
    should_surface_change_context,
)
from .answer_synthesis_practica import extend_from_practica_chunks
from .answer_topic_gate import (
    _topic_entry as _legal_anchor_topic_entry,
)
from .answer_anclaje_topic_gate import (
    filter_anclaje_articles as _v23_filter_anclaje_articles,
    gate_mode as _v23_anclaje_gate_mode,
)
from .case_bullets import CASE_REGISTRY
from .contracts import GraphEvidenceItem

if TYPE_CHECKING:
    from ..practica.shared import PracticaChunkRuntime
from .answer_synthesis_helpers import (
    build_followup_focus,
    classify_followup_question_shape,
    clean_title,
    extend_from_guidance,
    extend_from_support_insights,
    fallback_procedure_step,
    fallback_recommendation,
    is_gmf_deduction_case,
    is_ica_deduction_case,
    is_intereses_deduction_case,
    is_leasing_deduction_case,
    is_loss_compensation_case,
    is_predial_deduction_case,
    is_primer_empleo_deduction_case,
    is_refund_balance_case,
    looks_like_tax_treatment_question,
    pepper_legal_anchor_into_procedure,
    should_surface_connected_anchor,
    tax_treatment_subject_label,
)


def build_recommendations(
    *,
    request: PipelineCRequest,
    temporal_context: dict[str, object],
    primary_articles: tuple[GraphEvidenceItem, ...],
    connected_articles: tuple[GraphEvidenceItem, ...],
    practica_chunks: tuple["PracticaChunkRuntime", ...] = (),
) -> tuple[str, ...]:
    lines: list[str] = []
    normalized_message = normalize_text(request.message)
    # fix_v13_may §4 — práctica chunks from the dedicated retrieval
    # lane take precedence at the head of the chain. When the lane
    # surfaces real `knowledge_class='practica_erp'` content, those
    # bullets fill the section before the article-derived fallbacks
    # below run. When the lane returned empty (disabled / RPC error /
    # no candidates), this is a no-op and behavior matches v12.
    extend_from_practica_chunks(lines, practica_chunks)
    extend_from_support_insights(
        lines,
        _build_direct_position_lines(
            request=request,
            temporal_context=temporal_context,
            primary_articles=primary_articles,
        ),
    )
    if is_refund_balance_case(normalized_message):
        append_unique(
            lines,
            "Ordena el caso como devolución / compensación de saldo a favor y no como un problema principal de facturación electrónica.",
        )
    # v16 (2026-05-14) — case-bullet branches replaced by registry walk.
    # Each topic now lives in `pipeline_d/case_bullets/<topic>.py` with its
    # bullets + whitelist + anchor articles + search queries co-located.
    # See `case_bullets/__init__.py` for ordering rationale.
    for spec in CASE_REGISTRY:
        if spec.detector(normalized_message):
            for bullet in spec.bullets:
                append_unique(lines, bullet)
    if is_loss_compensation_case(normalized_message):
        append_unique(
            lines,
            "El régimen base del art. 147 ET es que la sociedad compensa la pérdida fiscal contra la renta líquida ordinaria de años siguientes; no es un trámite de devolución o compensación de saldo a favor ante la DIAN.",
        )
        if any(
            marker in normalized_message
            for marker in (
                "firmeza",
                "termino de firmeza",
                "término de firmeza",
                "termino de revision",
                "término de revisión",
                "revision",
                "revisión",
                "beneficio de auditoria",
                "beneficio de auditoría",
            )
        ):
            append_unique(
                lines,
                "Si la declaración origina o compensa pérdidas, léela con la regla especial de revisión de 6 años y solo después analiza si hay beneficio de auditoría u otra firmeza especial.",
            )
    if bool(temporal_context.get("historical_query_intent")):
        cutoff_date = str(temporal_context.get("cutoff_date") or "").strip()
        if cutoff_date:
            append_unique(
                lines,
                f"Define primero la fecha de análisis: para este caso conviene trabajar con corte {cutoff_date} antes de cerrar una posición para el cliente.",
            )
    extend_from_guidance(lines, "recommendation", primary_articles)
    extend_from_guidance(lines, "recommendation", connected_articles)
    if not lines:
        fallback = fallback_recommendation(
            request=request,
            primary_articles=primary_articles,
        )
        if fallback:
            append_unique(lines, fallback)
    # v15.2 (2026-05-14): tail polish. When a case detector fired (e.g.
    # `is_gmf_deduction_case`), drop bullets that don't touch ANY
    # case-relevant token — these are off-topic chunk leaks from the
    # práctica lane (inventory, year-end calendar, etc.). Then merge
    # adjacent question/answer bullet pairs so the answer reads as one
    # complete thought instead of two split sentences.
    # v15.3 (2026-05-14): same filter pattern for ICA + predial cases.
    # When multiple cases fire on a mixed-topic query, the whitelists
    # union — never narrow.
    case_keywords = _active_case_keywords(normalized_message)
    if case_keywords:
        lines = _filter_offtopic_bullets_for_case(lines, case_keywords=case_keywords)
    lines = _merge_question_answer_pairs(lines)
    return tuple(lines)


def _active_case_keywords(normalized_message: str) -> tuple[str, ...]:
    """Union the whitelists of every case detector that fired.

    A query that mentions both GMF and ICA gets the union of both
    whitelists, so neither case's substantive bullets are dropped by
    the off-topic filter when the other case fires.

    fix_v16 — refactored to walk ``CASE_REGISTRY`` instead of an
    if-chain. Adding a topic = adding a row in ``case_bullets/``;
    this function does not change.
    """
    keywords: list[str] = []
    for spec in CASE_REGISTRY:
        if spec.detector(normalized_message):
            keywords.extend(spec.keywords)
    return tuple(keywords)


def _filter_offtopic_bullets_for_case(
    lines: list[str],
    *,
    case_keywords: tuple[str, ...],
) -> list[str]:
    if not case_keywords:
        return list(lines)
    kept: list[str] = []
    for bullet in lines:
        normalized = bullet.lower()
        if any(kw in normalized for kw in case_keywords):
            kept.append(bullet)
    return kept


# A bullet ends in a question — optionally followed by an inline anchor
# in parens and/or a trailing period — when the trailing text matches
# this pattern. Used to detect Q/A bullet pairs to merge.
_QUESTION_END_RE = re.compile(r"\?(?:\s*\([^)]+\))?\s*\.?\s*$")


# A bullet is a new top-level item — NOT an answer to the prior
# question — when it starts with one of these subtitle markers
# (with or without surrounding markdown bold).
_SUBTITLE_PREFIX_RE = re.compile(
    r"^\s*\*{0,2}"
    r"(?:tip\b|soporte\b|razón conceptual|problema práctico|nota\b|ejemplo\b|"
    r"importante\b|calcula\b|registra\b|verifica\b|identifica\b|toma\b|"
    r"el \d|debito\b|débito\b|credito\b|crédito\b|art\.\s*\d)",
    re.IGNORECASE,
)


def _merge_question_answer_pairs(lines: list[str]) -> list[str]:
    """Collapse a Q-bullet followed by its A-bullet into one bullet.

    Example: "Problema práctico: ... ¿se causa o se paga?" +
    "La caja (dinero saliendo) es irrelevante..." →
    "Problema práctico: ... ¿se causa o se paga? La caja ...
    es irrelevante...".

    Guardrails: only merges when the next bullet does NOT open a new
    subtitle (Tip, Soporte, Razón, etc.) — those are independent items.
    """
    if len(lines) < 2:
        return list(lines)
    merged: list[str] = []
    i = 0
    while i < len(lines):
        current = lines[i]
        if i + 1 < len(lines):
            nxt = lines[i + 1]
            if _QUESTION_END_RE.search(current) and not _SUBTITLE_PREFIX_RE.match(nxt):
                merged.append(_merge_two_bullets(current, nxt))
                i += 2
                continue
        merged.append(current)
        i += 1
    return merged


def _merge_two_bullets(first: str, second: str) -> str:
    """Join two bullets with a single space.

    Keeps both inline anchors if present. Strips the trailing period
    of the first (the question mark already terminates the clause).
    """
    first_clean = first.rstrip(". ")
    second_clean = second.strip()
    return f"{first_clean} {second_clean}"


def build_procedure_steps(
    *,
    request: PipelineCRequest,
    temporal_context: dict[str, object],
    primary_articles: tuple[GraphEvidenceItem, ...],
    article_insights: dict[str, tuple[str, ...]],
    support_insights: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    steps: list[str] = []
    normalized_message = normalize_text(request.message)
    if is_loss_compensation_case(normalized_message):
        append_unique(
            steps,
            "Para pérdidas sujetas al régimen vigente, la regla operativa es 12 períodos gravables y sin tope porcentual anual; revisa el art. 290 ET solo si el saldo viene de años anteriores bajo régimen de transición.",
        )
        append_unique(
            steps,
            "Arma un cuadro por año de origen, régimen aplicable, fecha de expiración, saldo pendiente y renta líquida ordinaria disponible antes de decidir cuánto absorber.",
        )
        append_unique(
            steps,
            "Compensa solo contra renta líquida ordinaria del período; lo que no uses en ese año se sigue arrastrando hasta el vencimiento de su propio término.",
        )
    extend_from_guidance(steps, "procedure", primary_articles)
    extend_from_support_insights(steps, article_insights.get("procedure", ()))
    extend_from_support_insights(steps, support_insights.get("procedure", ()))
    if bool(temporal_context.get("historical_query_intent")):
        cutoff_date = str(temporal_context.get("cutoff_date") or "").strip()
        if cutoff_date:
            append_unique(
                steps,
                f"Separa en tu análisis la versión vigente hasta {cutoff_date} de cualquier cambio posterior para no mezclar reglas.",
            )
    if not steps:
        fallback = fallback_procedure_step(
            request=request,
            primary_articles=primary_articles,
        )
        if fallback:
            append_unique(steps, fallback)
    anchored_steps = pepper_legal_anchor_into_procedure(steps, primary_articles)
    return tuple(anchored_steps[:6])


def build_paperwork_lines(
    *,
    request: PipelineCRequest,
    article_insights: dict[str, tuple[str, ...]],
    support_insights: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    lines: list[str] = []
    normalized_message = normalize_text(request.message)
    if is_loss_compensation_case(normalized_message):
        append_unique(
            lines,
            "Deja un papel de trabajo por vigencia con saldo inicial de la pérdida, compensación usada en el año y saldo final arrastrable.",
        )
        append_unique(
            lines,
            "Conserva por al menos 6 años la declaración de origen, F.110, F.2516, conciliación fiscal y soportes que expliquen el nacimiento de la pérdida.",
        )
    extend_from_support_insights(lines, article_insights.get("paperwork", ()))
    extend_from_support_insights(lines, support_insights.get("paperwork", ()))
    return tuple(lines[:4])


_LEGAL_ANCHOR_GATE_ENV = "LIA_LEGAL_ANCHOR_GATE_MODE"


def _legal_anchor_gate_mode() -> str:
    """fix_v14_may §3 — operator-controlled mode for the topic-allowlist
    filter on legal-anchor rendering.

    Values:
      * ``off``      — gate disabled, identical to v13 behavior.
      * ``shadow``   — gate runs and reports dropped keys via the trace
                       step but does NOT filter the rendered output.
                       Default at landing (safe-by-default).
      * ``enforce``  — gate filters items whose ``art:<num>`` form is
                       not allowed by the topic's allowed_prefixes.

    Promotion path: ship in shadow, measure per-turn `legal_anchor_gate`
    diagnostic across the 42-turn panel-judge, then flip to enforce per
    the INCLUDE / REVERT rules in fix_v14_may §3.
    """
    raw = str(os.getenv(_LEGAL_ANCHOR_GATE_ENV, "shadow") or "").strip().lower()
    if raw in {"enforce", "on", "1", "true"}:
        return "enforce"
    if raw in {"off", "0", "false", "no", "disabled"}:
        return "off"
    return "shadow"


def _legal_anchor_node_key_passes(
    node_key: str,
    allowed_prefixes: tuple[str, ...],
) -> bool:
    """Decide whether a legal-anchor item (identified by `node_key` like
    `"147"`, `"260-5"`, `"260-par-6"`, `"107A"`) is allowed by the
    topic's `allowed_prefixes`.

    The structured `node_key` from `GraphEvidenceItem` is the canonical
    article reference and is normalized to `art:<lowercased-node_key>`.
    Each prefix in `allowed_prefixes` is matched either as an exact
    equality or as a startswith — same semantics as
    `answer_topic_gate._bullet_passes` but operating on the structured
    field rather than regex-parsing the rendered text.

    Empty `allowed_prefixes` → pass everything (noop, safe-by-default
    for topics without curation; Invariant I5).
    Empty `node_key` → pass (defensive — we never drop an item we can't
    classify).
    """
    if not allowed_prefixes:
        return True
    key_clean = str(node_key or "").strip().lower()
    if not key_clean:
        return True
    article_key = f"art:{key_clean}"
    return any(
        article_key.startswith(prefix) or article_key == prefix
        for prefix in allowed_prefixes
    )


def _legal_anchor_topic_for_request(request: PipelineCRequest) -> str | None:
    """Resolve the primary topic for allowlist lookup.

    Mirrors `answer_topic_gate.filter_template_bullets`'s expectation
    that the topic comes from `request.topic` (the router's effective
    topic). Returns None when the request has no resolved topic — gate
    becomes noop in that case.
    """
    topic = getattr(request, "topic", None)
    if isinstance(topic, str) and topic.strip():
        return topic.strip()
    return None


def _format_anchor_line(item: GraphEvidenceItem) -> str:
    """Render one Anclaje Legal bullet as an explanatory sentence.

    Pre-fix output was `Art. {N} — {HEADING}`. Polish often collapsed
    this to a bare `(art. N ET)` because the heading looked like a
    titlecard rather than a sentence, so the LLM treated it as
    droppable noise. New deterministic form is a full sentence:
    `Art. {N} ET — {heading}.` so:

    - it reads as a complete one-line description even when polish
      is bypassed (rejected fallback, polish disabled);
    - the trailing period plus `ET` suffix matches the prose pattern
      polish prefers when it does enrich the line (cesantías-style:
      `La definición de salario se encuentra en los (arts. 127-132
      ET).`), making it less likely to be stripped.

    Tests assert substrings like `"Art. 100"` / `"Art. 260-5"`,
    which remain present after this change.
    """
    title = clean_title(item.title)
    if not title:
        return f"Art. {item.node_key} ET."
    return f"Art. {item.node_key} ET — {title}."


def build_legal_anchor_lines(
    *,
    request: PipelineCRequest,
    primary_articles: tuple[GraphEvidenceItem, ...],
    connected_articles: tuple[GraphEvidenceItem, ...],
) -> tuple[str, ...]:
    """Render the legal-anchor block; optionally filter by topic-allowlist.

    fix_v14_may §3 — `LIA_LEGAL_ANCHOR_GATE_MODE` (shadow|enforce|off)
    controls a topic-aware filter that drops items whose `node_key`
    falls outside the primary topic's `allowed_prefixes` in
    `config/topic_norm_allowlist.json`. Shadow mode emits diagnostics
    via the existing trace step but does not reorder; enforce filters
    before render. Both modes are noop for topics without an allowlist
    entry (safe-by-default; Invariant I5).
    """
    lines: list[str] = []
    normalized_message = normalize_text(request.message)
    query_tokens = anchor_query_tokens(normalized_message)

    # fix_v14_may §3 — resolve gate mode + topic-allowlist entry once.
    gate_mode = _legal_anchor_gate_mode()
    primary_topic = _legal_anchor_topic_for_request(request)
    topic_entry = (
        _legal_anchor_topic_entry(primary_topic)
        if (gate_mode != "off" and primary_topic)
        else None
    )
    allowed_prefixes: tuple[str, ...] = ()
    if topic_entry is not None:
        allowed_prefixes = tuple(topic_entry.get("allowed_prefixes") or ())

    dropped_in_shadow: list[str] = []
    kept_count = 0
    dropped_count = 0

    def _gate_decision(item: GraphEvidenceItem) -> bool:
        """Return True to keep the item, False to drop. Always True when
        the gate is disabled or the topic has no allowlist (noop).
        Records into the shadow / counters in the enclosing scope.
        """
        nonlocal kept_count, dropped_count
        if gate_mode == "off" or not allowed_prefixes:
            kept_count += 1
            return True
        if _legal_anchor_node_key_passes(str(item.node_key), allowed_prefixes):
            kept_count += 1
            return True
        dropped_count += 1
        # Cap the shadow sample to keep diagnostics PII-safe and bounded.
        if len(dropped_in_shadow) < 8:
            dropped_in_shadow.append(
                f"{item.node_key} — {clean_title(item.title)[:80]}"
            )
        # In shadow mode we record but do NOT actually drop.
        return gate_mode != "enforce"

    # v23 P7 — topic-aware Anclaje gate. Filter connected_articles against
    # the active topic's compatibility allowlist (config/compatible_doc_topics.json)
    # BEFORE the existing v14 norm-allowlist + content-overlap filters run.
    # This drops off-topic ET expansions from a CST-rooted Anclaje (v22 P3
    # probe surfaced this: CST 64 question, Anclaje surfaced Art. 102 / 102-2
    # / 103 ET as "connected"). Body bullets and other sections are UNTOUCHED
    # — this only narrows what feeds the Anclaje section.
    _v23_effective_topic = (primary_topic or "").strip() or _legal_anchor_topic_for_request(request)
    _v23_kept_connected, _v23_dropped_connected = _v23_filter_anclaje_articles(
        connected_articles, _v23_effective_topic or ""
    )
    if _v23_anclaje_gate_mode() == "enforce":
        connected_for_anclaje = _v23_kept_connected
    else:
        connected_for_anclaje = connected_articles
    # Also gate primary_articles, but only for genuinely off-topic ones —
    # the same secondary_topics check. Primary articles with no secondary
    # topics are kept (graph gap → preserve evidence).
    _v23_kept_primary, _v23_dropped_primary = _v23_filter_anclaje_articles(
        primary_articles, _v23_effective_topic or ""
    )
    if _v23_anclaje_gate_mode() == "enforce":
        primary_for_anclaje = _v23_kept_primary
    else:
        primary_for_anclaje = primary_articles

    for item in primary_for_anclaje[:5]:
        if not _gate_decision(item):
            continue
        append_unique(lines, _format_anchor_line(item))
    for item in connected_for_anclaje[:2]:
        if not should_surface_connected_anchor(
            title=item.title,
            normalized_message=normalized_message,
            query_tokens=query_tokens,
        ):
            continue
        if not _gate_decision(item):
            continue
        append_unique(lines, _format_anchor_line(item))

    # Best-effort trace emission — falls back to silent no-op if the
    # tracer is unavailable in the current import context.
    try:
        from tracers_and_logs import pipeline_trace as _trace
        _trace.step(
            "synthesis.legal_anchor_gate.applied",
            status="ok",
            gate_mode=gate_mode,
            primary_topic=primary_topic,
            allowed_prefix_count=len(allowed_prefixes),
            kept_count=kept_count,
            dropped_count=dropped_count,
            dropped_keys_sample=dropped_in_shadow,
        )
    except Exception:  # pragma: no cover — never break synthesis on trace failure
        pass

    return tuple(lines)


def build_context_lines(
    *,
    request: PipelineCRequest,
    temporal_context: dict[str, object],
    planner_query_mode: str,
    primary_articles: tuple[GraphEvidenceItem, ...],
    reforms: tuple[GraphEvidenceItem, ...],
    article_insights: dict[str, tuple[str, ...]],
    support_insights: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    lines: list[str] = []
    cutoff_date = str(temporal_context.get("cutoff_date") or "").strip()
    requested_period_label = str(temporal_context.get("requested_period_label") or "").strip()
    allow_change_context = should_surface_change_context(
        normalized_message=normalize_text(request.message),
        temporal_context=temporal_context,
        planner_query_mode=planner_query_mode,
        requested_period_label=requested_period_label,
    )
    anchor_labels = tuple(
        str(item)
        for item in (temporal_context.get("anchor_reform_labels") or ())
        if str(item).strip()
    )
    if cutoff_date:
        if anchor_labels:
            append_unique(
                lines,
                f"Para este análisis conviene tomar como referencia temporal {cutoff_date} con apoyo en {anchor_labels[0]}.",
            )
        else:
            append_unique(
                lines,
                f"Para este análisis conviene trabajar con corte temporal {cutoff_date}.",
            )
    elif requested_period_label:
        append_unique(
            lines,
            f"El caso viene planteado para {requested_period_label}; valida que plazos, declaración base y soportes correspondan exactamente a ese período.",
        )
    modifications = extract_change_mentions(primary_articles, reforms)
    if modifications and allow_change_context:
        append_unique(
            lines,
            "Las normas principales de este tema muestran cambios o reformas relevantes en: "
            + ", ".join(modifications[:3])
            + ".",
        )
    extend_from_support_insights(
        lines,
        published_context_lines(
            article_insights.get("context", ()),
            allow_change_context=allow_change_context,
        ),
    )
    extend_from_support_insights(
        lines,
        published_context_lines(
            support_insights.get("context", ()),
            allow_change_context=allow_change_context,
        ),
    )
    if planner_query_mode == "historical_reform_chain":
        append_unique(
            lines,
            "La lectura histórica debe hacerse sobre el texto previo a la reforma y no sobre la versión vigente hoy.",
        )
    return tuple(lines[:4])


def build_precautions(
    *,
    request: PipelineCRequest,
    temporal_context: dict[str, object],
    primary_articles: tuple[GraphEvidenceItem, ...],
    connected_articles: tuple[GraphEvidenceItem, ...],
    answer_mode: str,
    article_insights: dict[str, tuple[str, ...]],
    support_insights: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    lines: list[str] = []
    extend_from_guidance(lines, "precaution", primary_articles)
    extend_from_guidance(lines, "precaution", connected_articles)
    extend_from_support_insights(lines, article_insights.get("precaution", ()))
    extend_from_support_insights(lines, support_insights.get("precaution", ()))
    normalized_message = normalize_text(request.message)
    if is_refund_balance_case(normalized_message):
        append_unique(
            lines,
            "Que el cliente esté al día en facturación electrónica no cambia por sí solo la naturaleza del trámite de devolución; úsalo solo como condición de cumplimiento complementaria.",
        )
    if is_loss_compensation_case(normalized_message):
        append_unique(
            lines,
            "No mezcles compensación de pérdidas fiscales con compensación de saldos a favor: comparten la palabra 'compensación', pero jurídicamente no son el mismo problema del cliente.",
        )
    if bool(temporal_context.get("historical_query_intent")):
        append_unique(
            lines,
            "Si vas a usar esta respuesta para un cierre actual, confirma que el caso no haya quedado bajo una versión normativa posterior.",
        )
    if answer_mode == "graph_native_partial":
        append_unique(
            lines,
            "La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.",
        )
    return tuple(lines[:4])


def build_opportunities(
    *,
    request: PipelineCRequest,
    primary_articles: tuple[GraphEvidenceItem, ...],
) -> tuple[str, ...]:
    lines: list[str] = []
    extend_from_guidance(lines, "opportunity", primary_articles)
    normalized_message = normalize_text(request.message)
    if is_refund_balance_case(normalized_message):
        append_unique(
            lines,
            "Si el cliente tiene obligaciones pendientes, compara devolución frente a compensación con apoyo en el art. 815 ET antes de definir la salida de caja.",
        )
    return tuple(lines[:2])


def build_followup_resolution(
    *,
    request: PipelineCRequest,
    recommendations: tuple[str, ...],
    procedure: tuple[str, ...],
    paperwork: tuple[str, ...],
    precautions: tuple[str, ...],
    opportunities: tuple[str, ...],
    context_lines: tuple[str, ...],
) -> tuple[str, str, str]:
    followup_focus = build_followup_focus(request.message)
    normalized_shape_message = normalize_text(followup_focus.shape_text)
    normalized_ranking_message = normalize_text(followup_focus.ranking_text or followup_focus.shape_text)
    question_shape = classify_followup_question_shape(normalized_shape_message)
    direct_answer = _select_followup_direct_answer(
        question_shape=question_shape,
        normalized_message=normalized_ranking_message,
        raw_message=request.message,
        avoid_echoed_lines=followup_focus.has_embedded_answer_echo,
        recommendations=recommendations,
        procedure=procedure,
        precautions=precautions,
        opportunities=opportunities,
        context_lines=context_lines,
    )
    seen = {normalize_text(direct_answer)} if direct_answer else set()
    main_exception = _select_followup_main_exception(
        question_shape=question_shape,
        normalized_message=normalized_ranking_message,
        raw_message=request.message,
        avoid_echoed_lines=followup_focus.has_embedded_answer_echo,
        procedure=procedure,
        precautions=precautions,
        context_lines=context_lines,
        recommendations=recommendations,
        seen=seen,
    )
    if main_exception:
        seen.add(normalize_text(main_exception))
    practical_next_step = _select_followup_next_step(
        normalized_message=normalized_shape_message,
        raw_message=request.message,
        avoid_echoed_lines=followup_focus.has_embedded_answer_echo,
        procedure=procedure,
        paperwork=paperwork,
        recommendations=recommendations,
        seen=seen,
    )
    return direct_answer, main_exception, practical_next_step


def _build_direct_position_lines(
    *,
    request: PipelineCRequest,
    temporal_context: dict[str, object],
    primary_articles: tuple[GraphEvidenceItem, ...],
) -> tuple[str, ...]:
    if bool(temporal_context.get("historical_query_intent")):
        return ()
    normalized_message = normalize_text(request.message)
    primary_keys = {
        str(item.node_key).strip()
        for item in primary_articles
        if str(item.node_key or "").strip()
    }
    lines: list[str] = []
    if "115" in primary_keys and looks_like_tax_treatment_question(normalized_message):
        subject = tax_treatment_subject_label(normalized_message)
        append_unique(
            lines,
            f"Para el tratamiento en renta de {subject}, revísalo primero bajo el art. 115 ET: no lo lleves como una deducción genérica y evita tomar el mismo valor simultáneamente como descuento tributario y como costo o gasto.",
        )
    return tuple(lines[:2])


def _select_followup_direct_answer(
    *,
    question_shape: str,
    normalized_message: str,
    raw_message: str,
    avoid_echoed_lines: bool,
    recommendations: tuple[str, ...],
    procedure: tuple[str, ...],
    precautions: tuple[str, ...],
    opportunities: tuple[str, ...],
    context_lines: tuple[str, ...],
) -> str:
    ranked: list[tuple[float, str]] = []
    ranked.extend(
        _score_followup_resolution_lines(
            question_shape=question_shape,
            normalized_message=normalized_message,
            lines=recommendations,
            source="recommendation",
        )
    )
    ranked.extend(
        _score_followup_resolution_lines(
            question_shape=question_shape,
            normalized_message=normalized_message,
            lines=procedure,
            source="procedure",
        )
    )
    ranked.extend(
        _score_followup_resolution_lines(
            question_shape=question_shape,
            normalized_message=normalized_message,
            lines=opportunities,
            source="opportunity",
        )
    )
    ranked.extend(
        _score_followup_resolution_lines(
            question_shape=question_shape,
            normalized_message=normalized_message,
            lines=precautions,
            source="precaution",
        )
    )
    ranked.extend(
        _score_followup_resolution_lines(
            question_shape=question_shape,
            normalized_message=normalized_message,
            lines=context_lines,
            source="context",
        )
    )
    if not ranked:
        return ""
    sorted_ranked = sorted(ranked, key=lambda item: (-item[0], item[1]))
    for _score, line in sorted_ranked:
        if avoid_echoed_lines and _line_is_echoed_in_message(line, raw_message):
            continue
        return line
    return sorted_ranked[0][1]


def _select_followup_main_exception(
    *,
    question_shape: str,
    normalized_message: str,
    raw_message: str,
    avoid_echoed_lines: bool,
    procedure: tuple[str, ...],
    precautions: tuple[str, ...],
    context_lines: tuple[str, ...],
    recommendations: tuple[str, ...],
    seen: set[str],
) -> str:
    ranked: list[tuple[float, str]] = []
    for source, lines, base in (
        ("procedure", procedure, 4.1),
        ("precaution", precautions, 4.0),
        ("context", context_lines, 3.6),
        ("recommendation", recommendations, 3.2),
    ):
        for index, raw_line in enumerate(lines):
            line = str(raw_line or "").strip()
            normalized_line = normalize_text(line)
            if not line or normalized_line in seen:
                continue
            if avoid_echoed_lines and _line_is_echoed_in_message(line, raw_message):
                continue
            score = base - (index * 0.12)
            if _looks_like_exception_line(normalized_line):
                score += 2.2
            if question_shape == "exception":
                score += 0.9
            if any(token in normalized_line for token in ("transicion", "histor", "vigencia", "reforma")):
                score += 0.45
            if source == "context" and question_shape not in {"deadline", "amount_limit", "exception"}:
                score -= 0.35
            ranked.append((score, line))
    if not ranked:
        return ""
    best_score, best_line = max(ranked, key=lambda item: (item[0], item[1]))
    return best_line if best_score >= 4.2 else ""


def _select_followup_next_step(
    *,
    normalized_message: str,
    raw_message: str,
    avoid_echoed_lines: bool,
    procedure: tuple[str, ...],
    paperwork: tuple[str, ...],
    recommendations: tuple[str, ...],
    seen: set[str],
) -> str:
    ranked: list[tuple[float, str]] = []
    for source, lines, base in (
        ("procedure", procedure, 4.2),
        ("paperwork", paperwork, 4.0),
        ("recommendation", recommendations, 2.9),
    ):
        for index, raw_line in enumerate(lines):
            line = str(raw_line or "").strip()
            normalized_line = normalize_text(line)
            if not line or normalized_line in seen:
                continue
            if avoid_echoed_lines and _line_is_echoed_in_message(line, raw_message):
                continue
            score = base - (index * 0.12)
            if _looks_like_action_step(normalized_line):
                score += 1.9
            if any(marker in normalized_message for marker in ("que hago", "que reviso", "checklist", "requisito")):
                score += 0.5
            ranked.append((score, line))
    if not ranked:
        return ""
    return max(ranked, key=lambda item: (item[0], item[1]))[1]


def _score_followup_resolution_lines(
    *,
    question_shape: str,
    normalized_message: str,
    lines: tuple[str, ...],
    source: str,
) -> list[tuple[float, str]]:
    base_weight = {
        "recommendation": 4.2,
        "procedure": 4.0,
        "opportunity": 3.0,
        "precaution": 2.8,
        "context": 2.4,
    }.get(source, 2.5)
    query_tokens = anchor_query_tokens(normalized_message)
    ranked: list[tuple[float, str]] = []
    for index, raw_line in enumerate(lines):
        line = str(raw_line or "").strip()
        if not line:
            continue
        normalized_line = normalize_text(line)
        score = base_weight - (index * 0.14)
        overlap = len(query_tokens.intersection(anchor_query_tokens(normalized_line)))
        score += float(overlap) * 1.4
        if question_shape == "amount_limit":
            if any(marker in normalized_line for marker in ("limite", "tope", "maximo", "porcentaje", "anual", "periodo", "ano", "anos", "mes", "dia", "plazo")):
                score += 2.1
            if any(marker in normalized_line for marker in ("sin tope", "sin limite", "sin tope porcentual", "sin tope anual")):
                score += 1.1
        elif question_shape == "deadline":
            if any(marker in normalized_line for marker in ("plazo", "termino", "dias", "meses", "anos", "antes de", "dentro de", "venc")):
                score += 2.0
        elif question_shape == "categorical":
            if any(marker in normalized_line for marker in ("no ", "sin ", "si ", "procede", "aplica", "puede", "corresponde")):
                score += 1.2
        elif question_shape == "exception":
            if _looks_like_exception_line(normalized_line):
                score += 1.7
        if _looks_like_exception_line(normalized_line) and question_shape in {"categorical", "amount_limit", "deadline"}:
            score -= 1.1
        if source == "precaution" and question_shape in {"categorical", "amount_limit", "deadline"}:
            score -= 0.45
        if line_has_legal_reference(line):
            score += 0.2
        ranked.append((score, line))
    return ranked


def _looks_like_exception_line(normalized_line: str) -> bool:
    text = str(normalized_line or "")
    return text.startswith(("si ", "solo si", "excepto", "salvo", "cuando ", "bajo ")) or any(
        marker in text
        for marker in (
            " regimen de transicion",
            " regimen congelado",
            " si el ",
            " si la ",
            " si viene ",
            " siempre que ",
        )
    )


def _looks_like_action_step(normalized_line: str) -> bool:
    text = str(normalized_line or "")
    return text.startswith(
        (
            "arma ",
            "haz ",
            "define ",
            "revisa ",
            "valida ",
            "confirma ",
            "separa ",
            "ordena ",
            "conserva ",
            "controla ",
            "liquida ",
            "compensa ",
            "deja ",
        )
    )


def _line_is_echoed_in_message(line: str, raw_message: str) -> bool:
    normalized_line = normalize_text(
        re.sub(
            r"\s+\(arts?\.[^)]+\)\.?$",
            "",
            str(line or ""),
            flags=re.IGNORECASE,
        )
    ).strip(" .")
    normalized_message = normalize_text(raw_message)
    if not normalized_line or len(normalized_line.split()) < 6:
        return False
    return normalized_line in normalized_message


# v16 b3 (2026-05-14) — direct-answer matcher (including the limit-style /
# numeric-range hot path) extracted to `answer_direct_answers.py` to keep
# this module under the 1000-LOC ceiling per the divide-and-conquer rule.
# The names are re-exported here so existing call sites continue to import
# `build_direct_answers` from `answer_synthesis_sections`.
from .answer_direct_answers import (  # noqa: F401  — re-exports
    _bullet_has_numeric_range,
    _is_limit_style_question,
    build_direct_answers,
)


__all__ = [
    "build_context_lines",
    "build_direct_answers",
    "build_followup_resolution",
    "build_legal_anchor_lines",
    "build_opportunities",
    "build_paperwork_lines",
    "build_precautions",
    "build_procedure_steps",
    "build_recommendations",
]
