from __future__ import annotations

from pathlib import Path
import re
import unicodedata
from uuid import uuid4

from ..pipeline_c.contracts import PipelineCRequest, PipelineCResponse
from .answer_support import (
    clean_support_line_for_answer,
    extract_article_insights,
    extract_support_doc_insights,
)
from .contracts import GraphEvidenceBundle, GraphEvidenceItem, GraphSupportDocument
from .planner import _looks_like_refund_balance_case, build_graph_retrieval_plan
from .retriever import retrieve_graph_evidence
_NORMATIVE_CHANGE_RE = re.compile(
    r"\b(?:Ley|Decreto|Resoluci[oó]n)\s+\d+\s+de\s+\d{4}\b",
    re.IGNORECASE,
)
_ARTICLE_GUIDANCE: dict[str, dict[str, tuple[str, ...]]] = {
    "850": {
        "recommendation": (
            "Toma el caso como una devolución de saldo a favor y valida primero que el saldo esté bien determinado en la declaración base.",
        ),
        "procedure": (
            "Antes de radicar, revisa la declaración que origina el saldo a favor y alinea soportes, anexos y datos del contribuyente.",
            "Si el expediente está completo, usa los términos de 50, 30 o 20 días hábiles como referencia operativa según el soporte con el que se presente la solicitud.",
        ),
        "precaution": (
            "No conviene radicar con cifras o soportes inconsistentes porque eso puede abrir inadmisiones o revisiones posteriores.",
        ),
        "opportunity": (
            "Si el cliente necesita caja, esta es la base para pedir reintegro del saldo a favor.",
        ),
    },
    "589": {
        "recommendation": (
            "Si el saldo a favor cambia por ajustes, corrige primero la declaración antes de mover el trámite frente a la DIAN.",
        ),
        "procedure": (
            "Ordena la secuencia así: corrección si aplica, luego devolución o compensación.",
            "Confirma si todavía estás dentro del año siguiente al vencimiento para corregir a favor del contribuyente.",
        ),
        "precaution": (
            "No mezcles una devolución con una declaración todavía inconsistente o pendiente de corregir.",
            "Recuerda que una corrección a favor reinicia el término de revisión de la DIAN desde la fecha de la corrección.",
        ),
    },
    "815": {
        "recommendation": (
            "Define si al cliente le conviene más devolución en efectivo o compensación contra otras obligaciones.",
        ),
        "procedure": (
            "Revisa las deudas tributarias vigentes del cliente antes de decidir si pides dinero o compensas saldos.",
        ),
        "opportunity": (
            "La compensación puede proteger caja y acelerar el beneficio económico si el cliente ya tiene obligaciones por pagar.",
        ),
    },
    "854": {
        "procedure": (
            "Controla el término para pedir la devolución; el calendario del trámite es parte del análisis, no un detalle posterior.",
        ),
        "precaution": (
            "No confundas el plazo del trámite con el año gravable que originó el saldo a favor.",
        ),
    },
    "855": {
        "procedure": (
            "Si la DIAN inadmite, corrige rápidamente el faltante formal dentro del término y vuelve a radicar con trazabilidad completa.",
        ),
        "precaution": (
            "Un trámite incompleto puede devolver al cliente al inicio del proceso.",
        ),
    },
    "857": {
        "precaution": (
            "La devolución o compensación puede caerse si faltan requisitos formales o el expediente no está bien soportado.",
        ),
    },
    "860": {
        "precaution": (
            "Una devolución improcedente expone al cliente a reintegro y sanciones, así que la revisión previa debe ser conservadora.",
        ),
        "opportunity": (
            "Si el caso permite garantía, evalúa si mejora la velocidad del trámite sin aumentar demasiado el costo del cliente.",
        ),
    },
    "588": {
        "recommendation": (
            "Antes de corregir, define si el ajuste aumenta el impuesto o reduce el saldo a favor, porque eso cambia el mecanismo, el plazo y la sanción.",
        ),
        "procedure": (
            "Si la corrección va en contra del contribuyente, valida primero si sigues dentro de los 3 años y si ya existe un emplazamiento o requerimiento especial.",
        ),
        "precaution": (
            "No uses la lógica del art. 588 cuando en realidad la corrección aumenta el saldo a favor o disminuye el valor a pagar.",
        ),
    },
    "670": {
        "precaution": (
            "Si ya hubo devolución o compensación y luego corriges reduciendo el saldo, evalúa de inmediato el riesgo de improcedencia y reintegro.",
        ),
    },
    "689-3": {
        "recommendation": (
            "Si el cliente está usando beneficio de auditoría, mide ese impacto antes de firmar cualquier corrección.",
        ),
        "procedure": (
            "Simula si la corrección mantiene o destruye la firmeza acelerada de 6 o 12 meses antes de presentarla.",
        ),
        "precaution": (
            "Una corrección que baja el incremento exigido puede hacer que el cliente pierda el beneficio de auditoría y vuelva a una firmeza más larga.",
        ),
    },
    "714": {
        "recommendation": (
            "Calcula la firmeza como una decisión del caso, no como una nota final de compliance.",
        ),
        "procedure": (
            "Define si aplicas la regla general de 3 años, la especial de 5 años o una firmeza acelerada por beneficio de auditoría antes de aconsejar al cliente.",
        ),
        "precaution": (
            "No confundas plazo para corregir con término de firmeza: que la declaración siga abierta a revisión no siempre significa que todavía puedas corregir voluntariamente.",
        ),
    },
    "771-2": {
        "recommendation": (
            "No tomes el costo, la deducción o el IVA descontable hasta validar que el soporte fiscal sí aguanta una revisión.",
        ),
        "procedure": (
            "Arma el expediente del gasto con factura o documento soporte y con evidencia adicional del hecho económico.",
        ),
        "precaution": (
            "Si el soporte es débil, la DIAN puede rechazar costo, deducción o impuesto descontable.",
        ),
    },
    "616-1": {
        "recommendation": (
            "Verifica si el emisor estaba obligado a facturar electrónicamente y si hubo contingencia válida antes de aceptar el soporte.",
        ),
        "procedure": (
            "Si hubo contingencia, deja evidencia del evento y de la normalización posterior de la factura.",
        ),
        "precaution": (
            "No sustituyas la factura electrónica por cualquier soporte cuando la obligación sí existía.",
        ),
    },
    "617": {
        "recommendation": (
            "Revisa los requisitos formales de la factura antes de usarla en renta o IVA.",
        ),
        "procedure": (
            "Haz una revisión mínima de numeración, identificación y datos obligatorios antes del cierre tributario.",
        ),
        "precaution": (
            "Una factura sin requisitos reduce la defensa del cliente si la DIAN cuestiona el soporte.",
        ),
    },
    "743": {
        "precaution": (
            "Conserva medios de prueba adicionales porque la factura sola no siempre agota la carga probatoria.",
        ),
    },
    "115": {
        "recommendation": (
            "Toma como punto de partida el texto vigente hoy del art. 115 ET para definir el tratamiento en renta del impuesto pagado.",
        ),
        "procedure": (
            "Verifica si el valor efectivamente pagado puede tratarse como descuento tributario sin duplicarlo como costo o gasto.",
        ),
        "precaution": (
            "No dupliques el mismo valor como descuento tributario y como costo o gasto dentro de la misma declaración.",
        ),
    },
}
_TITLE_GUIDANCE: tuple[tuple[tuple[str, ...], dict[str, tuple[str, ...]]], ...] = (
    (
        ("devolucion", "saldo a favor"),
        {
            "recommendation": (
                "Trata el asunto como un flujo de recuperación o aplicación del saldo a favor, no solo como una consulta normativa abstracta.",
            ),
        },
    ),
    (
        ("correccion", "saldo a favor"),
        {
            "procedure": (
                "Valida si el saldo a favor necesita corrección previa antes de presentar cualquier solicitud frente a la DIAN.",
            ),
        },
    ),
    (
        ("compensacion",),
        {
            "opportunity": (
                "Revisa si la compensación resuelve mejor la posición de caja o de pasivos del cliente que una espera por devolución.",
            ),
        },
    ),
    (
        ("factura",),
        {
            "recommendation": (
                "Haz una revisión operativa del soporte antes de defenderlo fiscalmente.",
            ),
        },
    ),
    (
        ("requisitos", "factura"),
        {
            "procedure": (
                "Revisa el check mínimo de requisitos antes de incorporar el documento al cierre tributario del cliente.",
            ),
        },
    ),
    (
        ("prueba",),
        {
            "precaution": (
                "Fortalece el expediente con pruebas del negocio real, no solo con el documento principal.",
            ),
        },
    ),
)


def _artifacts_dir_from_index_file(index_file: object | None) -> Path | None:
    if index_file is None:
        return None
    path = Path(str(index_file))
    if path.name == "canonical_corpus_manifest.json":
        return path.parent
    return None


def _compose_graph_native_answer(
    *,
    request: PipelineCRequest,
    answer_mode: str,
    planner_query_mode: str,
    temporal_context: dict[str, object],
    evidence: GraphEvidenceBundle,
) -> str:
    sections: list[str] = []
    support_insights = extract_support_doc_insights(
        request=request,
        support_documents=evidence.support_documents,
    )
    article_insights = extract_article_insights(
        request=request,
        temporal_context=temporal_context,
        primary_articles=evidence.primary_articles,
        connected_articles=evidence.connected_articles,
    )
    recommendations = _build_recommendations(
        request=request,
        temporal_context=temporal_context,
        primary_articles=evidence.primary_articles,
        connected_articles=evidence.connected_articles,
    )
    procedure = _build_procedure_steps(
        request=request,
        temporal_context=temporal_context,
        primary_articles=evidence.primary_articles,
        article_insights=article_insights,
        support_insights=support_insights,
    )
    paperwork = _build_paperwork_lines(
        article_insights=article_insights,
        support_insights=support_insights,
    )
    legal_anchor = _build_legal_anchor_lines(
        request=request,
        primary_articles=evidence.primary_articles,
        connected_articles=evidence.connected_articles,
    )
    context_lines = _build_context_lines(
        request=request,
        temporal_context=temporal_context,
        planner_query_mode=planner_query_mode,
        primary_articles=evidence.primary_articles,
        reforms=evidence.related_reforms,
        article_insights=article_insights,
        support_insights=support_insights,
    )
    precautions = _build_precautions(
        request=request,
        temporal_context=temporal_context,
        primary_articles=evidence.primary_articles,
        connected_articles=evidence.connected_articles,
        answer_mode=answer_mode,
        article_insights=article_insights,
        support_insights=support_insights,
    )
    opportunities = _build_opportunities(
        request=request,
        primary_articles=evidence.primary_articles,
        support_documents=evidence.support_documents,
    )

    if recommendations:
        sections.append(_render_bullet_section("Qué Haría Primero", recommendations))
    if procedure:
        sections.append(_render_numbered_section("Procedimiento Sugerido", procedure))
    if paperwork:
        sections.append(_render_bullet_section("Soportes y Papeles de Trabajo", paperwork))
    if legal_anchor:
        sections.append(_render_bullet_section("Anclaje Legal", legal_anchor))
    if precautions:
        sections.append(_render_bullet_section("Precauciones", precautions))
    if opportunities:
        sections.append(_render_bullet_section("Oportunidades", opportunities))
    if context_lines:
        sections.append(_render_bullet_section("Cambios y Contexto Legal", context_lines))

    if not sections:
        lead = "Con la evidencia disponible todavía no alcanzo una recomendación operativa suficientemente confiable."
        if answer_mode == "graph_native_partial":
            lead = (
                "Usa esta salida solo como orientación inicial y confirma el expediente antes de convertirla en instrucción cerrada para el cliente."
            )
        sections.append(lead)
    return "\n\n".join(section for section in sections if section.strip())


def _render_bullet_section(title: str, lines: tuple[str, ...]) -> str:
    return f"**{title}**\n" + "\n".join(f"- {line}" for line in lines if line)


def _render_numbered_section(title: str, lines: tuple[str, ...]) -> str:
    return f"**{title}**\n" + "\n".join(f"{idx}. {line}" for idx, line in enumerate(lines, start=1) if line)


def _build_recommendations(
    *,
    request: PipelineCRequest,
    temporal_context: dict[str, object],
    primary_articles: tuple[GraphEvidenceItem, ...],
    connected_articles: tuple[GraphEvidenceItem, ...],
) -> tuple[str, ...]:
    lines: list[str] = []
    normalized_message = _normalize_text(request.message)
    _extend_from_support_insights(
        lines,
        _build_direct_position_lines(
            request=request,
            temporal_context=temporal_context,
            primary_articles=primary_articles,
        ),
    )
    if _is_refund_balance_case(normalized_message):
        _append_unique(
            lines,
            "Ordena el caso como devolución / compensación de saldo a favor y no como un problema principal de facturación electrónica.",
        )
    if bool(temporal_context.get("historical_query_intent")):
        cutoff_date = str(temporal_context.get("cutoff_date") or "").strip()
        if cutoff_date:
            _append_unique(
                lines,
                f"Define primero la fecha de análisis: para este caso conviene trabajar con corte {cutoff_date} antes de cerrar una posición para el cliente.",
            )
    _extend_from_guidance(lines, "recommendation", primary_articles)
    _extend_from_guidance(lines, "recommendation", connected_articles)
    if not lines and primary_articles:
        _append_unique(
            lines,
            "Empieza por las normas principales de este caso y valida su aplicación al hecho económico concreto del cliente antes de pasar al detalle legal fino.",
        )
    return tuple(lines[:3])


def _build_direct_position_lines(
    *,
    request: PipelineCRequest,
    temporal_context: dict[str, object],
    primary_articles: tuple[GraphEvidenceItem, ...],
) -> tuple[str, ...]:
    if bool(temporal_context.get("historical_query_intent")):
        return ()
    normalized_message = _normalize_text(request.message)
    primary_keys = {
        str(item.node_key).strip()
        for item in primary_articles
        if str(item.node_key or "").strip()
    }
    lines: list[str] = []
    if "115" in primary_keys and _looks_like_tax_treatment_question(normalized_message):
        subject = _tax_treatment_subject_label(normalized_message)
        _append_unique(
            lines,
            f"Para el tratamiento en renta de {subject}, revísalo primero bajo el art. 115 ET: no lo lleves como una deducción genérica y evita tomar el mismo valor simultáneamente como descuento tributario y como costo o gasto.",
        )
    return tuple(lines[:2])


def _build_procedure_steps(
    *,
    request: PipelineCRequest,
    temporal_context: dict[str, object],
    primary_articles: tuple[GraphEvidenceItem, ...],
    article_insights: dict[str, tuple[str, ...]],
    support_insights: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    steps: list[str] = []
    _extend_from_guidance(steps, "procedure", primary_articles)
    _extend_from_support_insights(steps, article_insights.get("procedure", ()))
    _extend_from_support_insights(steps, support_insights.get("procedure", ()))
    if bool(temporal_context.get("historical_query_intent")):
        cutoff_date = str(temporal_context.get("cutoff_date") or "").strip()
        if cutoff_date:
            _append_unique(
                steps,
                f"Separa en tu análisis la versión vigente hasta {cutoff_date} de cualquier cambio posterior para no mezclar reglas.",
            )
    if not steps and primary_articles:
        _append_unique(
            steps,
            "Toma las normas principales del caso, ordénalas por secuencia operativa y conviértelas en checklist antes de radicar o cerrar la declaración.",
        )
    anchored_steps = _pepper_legal_anchor_into_procedure(steps, primary_articles)
    return tuple(anchored_steps[:6])


def _build_paperwork_lines(
    *,
    article_insights: dict[str, tuple[str, ...]],
    support_insights: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    lines: list[str] = []
    _extend_from_support_insights(lines, article_insights.get("paperwork", ()))
    _extend_from_support_insights(lines, support_insights.get("paperwork", ()))
    return tuple(lines[:4])


def _build_legal_anchor_lines(
    *,
    request: PipelineCRequest,
    primary_articles: tuple[GraphEvidenceItem, ...],
    connected_articles: tuple[GraphEvidenceItem, ...],
) -> tuple[str, ...]:
    lines: list[str] = []
    normalized_message = _normalize_text(request.message)
    query_tokens = _anchor_query_tokens(normalized_message)
    for item in primary_articles[:5]:
        _append_unique(lines, f"Art. {item.node_key} — {_clean_title(item.title)}")
    for item in connected_articles[:2]:
        if not _should_surface_connected_anchor(
            title=item.title,
            normalized_message=normalized_message,
            query_tokens=query_tokens,
        ):
            continue
        _append_unique(lines, f"Art. {item.node_key} — {_clean_title(item.title)}")
    return tuple(lines)


def _build_context_lines(
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
    anchor_labels = tuple(str(item) for item in (temporal_context.get("anchor_reform_labels") or ()) if str(item).strip())
    if cutoff_date:
        if anchor_labels:
            _append_unique(
                lines,
                f"Para este análisis conviene tomar como referencia temporal {cutoff_date} con apoyo en {anchor_labels[0]}.",
            )
        else:
            _append_unique(
                lines,
                f"Para este análisis conviene trabajar con corte temporal {cutoff_date}.",
            )
    elif requested_period_label:
        _append_unique(
            lines,
            f"El caso viene planteado para {requested_period_label}; valida que plazos, declaración base y soportes correspondan exactamente a ese período.",
        )
    modifications = _extract_change_mentions(primary_articles, reforms)
    if modifications and _should_surface_change_context(
        normalized_message=_normalize_text(request.message),
        temporal_context=temporal_context,
        planner_query_mode=planner_query_mode,
        requested_period_label=requested_period_label,
    ):
        _append_unique(
            lines,
            "Las normas principales de este tema muestran cambios o reformas relevantes en: " + ", ".join(modifications[:3]) + ".",
        )
    _extend_from_support_insights(lines, article_insights.get("context", ()))
    _extend_from_support_insights(lines, support_insights.get("context", ()))
    if planner_query_mode == "historical_reform_chain":
        _append_unique(
            lines,
            "La lectura histórica debe hacerse sobre el texto previo a la reforma y no sobre la versión vigente hoy.",
        )
    return tuple(lines[:4])


def _should_surface_change_context(
    *,
    normalized_message: str,
    temporal_context: dict[str, object],
    planner_query_mode: str,
    requested_period_label: str,
) -> bool:
    if bool(temporal_context.get("historical_query_intent")):
        return True
    if planner_query_mode == "historical_reform_chain":
        return True
    if requested_period_label:
        return True
    return any(
        marker in normalized_message
        for marker in (
            "vigencia",
            "vigente",
            "reforma",
            "reformo",
            "reformó",
            "modifico",
            "modificó",
            "modificacion",
            "modificación",
            "antes de la ley",
            "despues de la ley",
            "después de la ley",
            "historic",
            "que decia",
            "qué decía",
            "version anterior",
            "versión anterior",
        )
    )


def _build_precautions(
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
    _extend_from_guidance(lines, "precaution", primary_articles)
    _extend_from_guidance(lines, "precaution", connected_articles)
    _extend_from_support_insights(lines, article_insights.get("precaution", ()))
    _extend_from_support_insights(lines, support_insights.get("precaution", ()))
    normalized_message = _normalize_text(request.message)
    if _is_refund_balance_case(normalized_message):
        _append_unique(
            lines,
            "Que el cliente esté al día en facturación electrónica no cambia por sí solo la naturaleza del trámite de devolución; úsalo solo como condición de cumplimiento complementaria.",
        )
    if bool(temporal_context.get("historical_query_intent")):
        _append_unique(
            lines,
            "Si vas a usar esta respuesta para un cierre actual, confirma que el caso no haya quedado bajo una versión normativa posterior.",
        )
    if answer_mode == "graph_native_partial":
        _append_unique(
            lines,
            "La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.",
        )
    return tuple(lines[:4])


def _build_opportunities(
    *,
    request: PipelineCRequest,
    primary_articles: tuple[GraphEvidenceItem, ...],
    support_documents: tuple[GraphSupportDocument, ...],
) -> tuple[str, ...]:
    lines: list[str] = []
    _extend_from_guidance(lines, "opportunity", primary_articles)
    normalized_message = _normalize_text(request.message)
    if _is_refund_balance_case(normalized_message):
        _append_unique(
            lines,
            "Si el cliente tiene obligaciones pendientes, compara devolución frente a compensación con apoyo en el art. 815 ET antes de definir la salida de caja.",
        )
    if not lines:
        practical_docs = [doc for doc in support_documents if str(doc.family or "") == "practica"]
        if practical_docs:
            _append_unique(
                lines,
                "Hay espacio para volver esto más eficiente con una guía práctica del tema, sin salir del marco legal que soporta la recomendación.",
            )
    return tuple(lines[:2])


def _extend_from_support_insights(
    bucket: list[str],
    lines: tuple[str, ...],
) -> None:
    for line in lines:
        cleaned = clean_support_line_for_answer(line)
        if cleaned:
            _append_unique(bucket, cleaned)


def _pepper_legal_anchor_into_procedure(
    steps: list[str],
    primary_articles: tuple[GraphEvidenceItem, ...],
) -> tuple[str, ...]:
    anchor_tail = _procedure_anchor_tail(primary_articles)
    if not anchor_tail:
        return tuple(steps)
    enriched: list[str] = []
    tail_used = False
    for step in steps:
        current = str(step or "").strip()
        if current and not tail_used and not _line_has_legal_reference(current):
            current = current.rstrip(".") + f" {anchor_tail}"
            tail_used = True
        enriched.append(current)
    return tuple(enriched)


def _procedure_anchor_tail(primary_articles: tuple[GraphEvidenceItem, ...]) -> str:
    article_keys = [item.node_key for item in primary_articles[:5] if str(item.node_key or "").strip()]
    if not article_keys:
        return ""
    if len(article_keys) == 1:
        joined = article_keys[0]
    elif len(article_keys) == 2:
        joined = f"{article_keys[0]} y {article_keys[1]}"
    else:
        joined = ", ".join(article_keys[:-1]) + f" y {article_keys[-1]}"
    return f"Apóyate aquí en los arts. {joined} ET."


def _anchor_query_tokens(normalized_message: str) -> set[str]:
    return {
        token
        for token in re.split(r"[^a-z0-9]+", normalized_message)
        if len(token) >= 3
        and token
        not in {
            "que",
            "como",
            "para",
            "con",
            "sin",
            "del",
            "las",
            "los",
            "una",
            "uno",
            "unos",
            "unas",
            "declaracion",
            "renta",
            "persona",
            "juridica",
            "pagado",
            "pagados",
            "impuesto",
            "impuestos",
        }
    }


def _should_surface_connected_anchor(
    *,
    title: str,
    normalized_message: str,
    query_tokens: set[str],
) -> bool:
    normalized_title = _normalize_text(title)
    title_tokens = {
        token
        for token in re.split(r"[^a-z0-9]+", normalized_title)
        if len(token) >= 3
    }
    if query_tokens.intersection(title_tokens):
        return True
    if _looks_like_tax_treatment_question(normalized_message):
        return any(
            marker in normalized_title
            for marker in (
                "descuento",
                "costo",
                "gasto",
                "descontable",
                "iva",
            )
        )
    return False


def _line_has_legal_reference(value: str) -> bool:
    normalized = _normalize_text(value)
    return any(
        marker in normalized
        for marker in (
            "art.",
            "art ",
            "articulo",
            "et ",
            "ley ",
            "decreto ",
            "dur ",
            "resolucion ",
            "resolucion",
        )
    )


def _extend_from_guidance(
    bucket: list[str],
    field: str,
    items: tuple[GraphEvidenceItem, ...],
) -> None:
    for item in items:
        guidance = _guidance_for_item(item)
        for line in guidance.get(field, ()):
            _append_unique(bucket, line)


def _guidance_for_item(item: GraphEvidenceItem) -> dict[str, tuple[str, ...]]:
    merged: dict[str, list[str]] = {}
    title = _normalize_text(item.title)
    for source in (_ARTICLE_GUIDANCE.get(item.node_key, {}), *_matched_title_guidance(title)):
        for field, lines in source.items():
            merged.setdefault(field, [])
            for line in lines:
                if line not in merged[field]:
                    merged[field].append(line)
    return {field: tuple(lines) for field, lines in merged.items()}


def _matched_title_guidance(title: str) -> tuple[dict[str, tuple[str, ...]], ...]:
    matches: list[dict[str, tuple[str, ...]]] = []
    for markers, payload in _TITLE_GUIDANCE:
        if all(marker in title for marker in markers):
            matches.append(payload)
    return tuple(matches)


def _extract_change_mentions(
    primary_articles: tuple[GraphEvidenceItem, ...],
    reforms: tuple[GraphEvidenceItem, ...],
) -> tuple[str, ...]:
    mentions: list[str] = []
    for reform in reforms:
        _append_unique(mentions, reform.title)
    for item in primary_articles:
        for match in _NORMATIVE_CHANGE_RE.findall(str(item.excerpt or "")):
            _append_unique(mentions, match)
    return tuple(mentions)


def _append_unique(bucket: list[str], line: str) -> None:
    value = re.sub(r"\s+", " ", str(line or "")).strip()
    if not value:
        return
    if value not in bucket:
        bucket.append(value)


def _clean_title(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip(" .")


def _is_refund_balance_case(normalized_message: str) -> bool:
    return _looks_like_refund_balance_case(normalized_message)


def _looks_like_tax_treatment_question(normalized_message: str) -> bool:
    has_treatment = any(
        marker in normalized_message
        for marker in (
            "deducir",
            "deducible",
            "procedente",
            "procedencia",
            "descuento tributario",
            "costo o gasto",
            "impuesto pagado",
            "impuestos pagados",
        )
    )
    has_tax_subject = any(
        marker in normalized_message
        for marker in (
            "ica",
            "industria y comercio",
            "avisos y tableros",
            "gmf",
            "gravamen a los movimientos financieros",
            "movimientos financieros",
            "4x1000",
            "cuatro por mil",
            "impuesto",
            "impuestos",
        )
    )
    return has_treatment and has_tax_subject


def _tax_treatment_subject_label(normalized_message: str) -> str:
    if any(
        marker in normalized_message
        for marker in (
            "ica",
            "industria y comercio",
            "avisos y tableros",
        )
    ):
        return "ese impuesto pagado, incluido ICA"
    if any(
        marker in normalized_message
        for marker in (
            "gmf",
            "gravamen a los movimientos financieros",
            "movimientos financieros",
            "4x1000",
            "cuatro por mil",
        )
    ):
        return "ese impuesto pagado, incluido GMF"
    return "ese impuesto pagado"


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text).strip().lower()


def run_pipeline_d(
    request: PipelineCRequest,
    *,
    index_file: object | None = None,
    policy_path: object | None = None,
    runtime_config_path: object | None = None,
    stream_sink: object | None = None,
) -> PipelineCResponse:
    sink = stream_sink
    if sink is not None:
        status = getattr(sink, "status", None)
        on_llm_delta = getattr(sink, "on_llm_delta", None)
        if callable(status):
            status("pipeline_d", "Planificando anclajes graph-native sobre el grafo validado...")
    else:
        on_llm_delta = None

    try:
        plan = build_graph_retrieval_plan(request)
        artifacts_dir = _artifacts_dir_from_index_file(index_file)
        if sink is not None and callable(status):
            status("pipeline_d", "Recuperando evidencia desde graph artifacts y canonical manifest...")
        plan, evidence = retrieve_graph_evidence(plan, artifacts_dir=artifacts_dir)
    except FileNotFoundError:
        answer = (
            "Pipeline D no encontro los artifacts graph-native esperados en disco, "
            "asi que no pudo ejecutar la ruta Phase 3 todavia."
        )
        if callable(on_llm_delta):
            on_llm_delta(answer)
        return PipelineCResponse(
            trace_id=str(request.trace_id or uuid4().hex),
            run_id=f"pd_{uuid4().hex}",
            answer_markdown=answer,
            answer_concise=answer,
            followup_queries=(),
            citations=(),
            confidence_score=0.05,
            confidence_mode="graph_artifacts_missing",
            answer_mode="compat_stub",
            compose_quality=0.0,
            fallback_reason="pipeline_d_graph_artifacts_missing",
            evidence_snippets=(),
            diagnostics={
                "compatibility_mode": True,
                "pipeline_family": "pipeline_d",
                "index_file": str(index_file) if index_file is not None else None,
                "policy_path": str(policy_path) if policy_path is not None else None,
                "runtime_config_path": (
                    str(runtime_config_path) if runtime_config_path is not None else None
                ),
            },
            llm_runtime=None,
            token_usage=None,
            timing=None,
            requested_topic=request.requested_topic,
            effective_topic=request.topic,
            secondary_topics=request.secondary_topics,
            topic_adjusted=request.topic_adjusted,
            topic_notice=request.topic_notice,
            topic_adjustment_reason=request.topic_adjustment_reason,
            coverage_notice="Artifacts graph-native faltantes para la ruta Phase 3.",
            pipeline_variant="pipeline_d",
            pipeline_route="pipeline_d",
        )

    answer_mode = "graph_native"
    fallback_reason = None
    confidence = 0.82 if evidence.primary_articles else 0.42
    confidence_mode = "graph_artifact_planner_v1"
    coverage_notice = None
    if not evidence.primary_articles:
        answer_mode = "graph_native_partial"
        fallback_reason = "pipeline_d_no_graph_primary_articles"
        coverage_notice = (
            "La ruta graph-native no encontro articulos ancla suficientes; "
            "se devolvio la mejor evidencia parcial disponible."
        )

    answer = _compose_graph_native_answer(
        request=request,
        answer_mode=answer_mode,
        planner_query_mode=plan.query_mode,
        temporal_context=plan.temporal_context.to_dict(),
        evidence=evidence,
    )
    if callable(on_llm_delta):
        on_llm_delta(answer)

    return PipelineCResponse(
        trace_id=str(request.trace_id or uuid4().hex),
        run_id=f"pd_{uuid4().hex}",
        answer_markdown=answer,
        answer_concise=answer,
        followup_queries=(
            "¿Quieres que traduzca esta ruta en una checklist operativa para el contador?",
            "¿Quieres que priorice solo cambios de vigencia o solo requisitos probatorios?",
        ),
        citations=evidence.citations,
        confidence_score=confidence,
        confidence_mode=confidence_mode,
        answer_mode=answer_mode,
        compose_quality=0.82 if evidence.primary_articles else 0.45,
        fallback_reason=fallback_reason,
        evidence_snippets=tuple(item.excerpt for item in evidence.primary_articles[:3]),
        diagnostics={
            "compatibility_mode": False,
            "pipeline_family": "pipeline_d_phase3",
            "index_file": str(index_file) if index_file is not None else None,
            "policy_path": str(policy_path) if policy_path is not None else None,
            "runtime_config_path": (
                str(runtime_config_path) if runtime_config_path is not None else None
            ),
            "planner": plan.to_dict(),
            "evidence_bundle": evidence.to_dict(),
        },
        llm_runtime=None,
        token_usage=None,
        timing=None,
        requested_topic=request.requested_topic,
        effective_topic=request.topic,
        secondary_topics=request.secondary_topics,
        topic_adjusted=request.topic_adjusted,
        topic_notice=request.topic_notice,
        topic_adjustment_reason=request.topic_adjustment_reason,
        coverage_notice=coverage_notice,
        pipeline_variant="pipeline_d",
        pipeline_route="pipeline_d",
    )
