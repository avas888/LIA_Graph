from __future__ import annotations

from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d.answer_shared import neutralize_non_imputative_language
from lia_graph.pipeline_d.orchestrator import run_pipeline_d
from lia_graph.pipeline_d.planner import _extract_article_refs, build_graph_retrieval_plan
from lia_graph.pipeline_d.retriever import retrieve_graph_evidence
from lia_graph.topic_router import detect_topic_from_text


def test_phase3_planner_contract_extracts_multi_hop_entry_points() -> None:
    request = PipelineCRequest(
        message=(
            "¿Qué exige el ET entre los artículos 771-2, 616-1 y 617 "
            "para soportar costos y deducciones con factura electrónica?"
        ),
        topic="facturacion_electronica",
        requested_topic="facturacion_electronica",
    )

    plan = build_graph_retrieval_plan(request)

    assert plan.query_mode == "computation_chain"
    assert [entry.lookup_value for entry in plan.entry_points if entry.kind == "article"] == [
        "771-2",
        "616-1",
        "617",
    ]
    assert any(
        entry.kind == "topic" and entry.lookup_value == "facturacion_electronica"
        for entry in plan.entry_points
    )
    assert plan.traversal_budget.max_hops == 2
    assert plan.evidence_bundle_shape.support_document_limit >= 4


def test_phase3_retriever_smoke_uses_real_rub_graph_artifacts() -> None:
    request = PipelineCRequest(
        message=(
            "¿Cómo se conectan los artículos 631-5, 631-6 y 658-3 del ET "
            "para identificar beneficiarios finales y el riesgo sancionatorio del RUB?"
        ),
        topic="beneficiario_final_rub",
        requested_topic="beneficiario_final_rub",
    )

    plan = build_graph_retrieval_plan(request)
    hydrated_plan, evidence = retrieve_graph_evidence(plan)

    assert hydrated_plan.query_mode == "obligation_chain"
    primary_keys = [item.node_key for item in evidence.primary_articles]
    assert "631-5" in primary_keys
    assert "631-6" in primary_keys
    assert "658-3" in primary_keys
    assert evidence.support_documents
    assert any(doc.topic_key == "beneficiario_final_rub" for doc in evidence.support_documents)
    assert evidence.citations
    assert evidence.diagnostics["resolved_entry_count"] >= 3


def test_phase3_planner_historical_query_builds_temporal_context() -> None:
    plan = build_graph_retrieval_plan(
        PipelineCRequest(
            message="¿Qué decía el artículo 115 antes de la Ley 2277 de 2022?",
            topic="declaracion_renta",
            requested_topic="declaracion_renta",
        )
    )

    assert plan.query_mode == "historical_reform_chain"
    assert [entry.lookup_value for entry in plan.entry_points if entry.kind == "article"] == ["115"]
    assert [entry.lookup_value for entry in plan.entry_points if entry.kind == "reform"] == [
        "LEY-2277-2022"
    ]
    assert plan.temporal_context.historical_query_intent is True
    assert plan.temporal_context.cutoff_date == "2021-12-31"
    assert plan.temporal_context.scope_mode == "historical_before_reform"


def test_phase3_retriever_historical_smoke_prefers_requested_reform_context() -> None:
    plan = build_graph_retrieval_plan(
        PipelineCRequest(
            message="¿Qué decía el artículo 115 antes de la Ley 2277 de 2022?",
            topic="declaracion_renta",
            requested_topic="declaracion_renta",
        )
    )

    hydrated_plan, evidence = retrieve_graph_evidence(plan)

    assert hydrated_plan.temporal_context.cutoff_date == "2021-12-31"
    assert evidence.primary_articles
    assert evidence.primary_articles[0].node_key == "115"
    assert "cien por ciento" in evidence.primary_articles[0].excerpt
    assert "Ley 2277 de 2022" in str(evidence.primary_articles[0].why or "")
    assert not evidence.connected_articles
    assert evidence.related_reforms
    assert evidence.related_reforms[0].node_key == "LEY-2277-2022"
    assert evidence.support_documents
    assert all(doc.family == "normativa" for doc in evidence.support_documents)
    assert evidence.diagnostics["temporal_context"]["historical_query_intent"] is True


def test_phase3_pipeline_d_end_to_end_smoke_for_factura_chain() -> None:
    response = run_pipeline_d(
        PipelineCRequest(
            message=(
                "¿Qué exige el ET entre los artículos 771-2, 616-1 y 617 "
                "para soportar costos y deducciones con factura electrónica?"
            ),
            topic="facturacion_electronica",
            requested_topic="facturacion_electronica",
        )
    )

    assert response.answer_mode == "graph_native"
    assert response.fallback_reason is None
    assert response.confidence_mode == "graph_artifact_planner_v1"
    assert "771-2" in response.answer_markdown
    assert "616-1" in response.answer_markdown
    assert "617" in response.answer_markdown
    assert response.citations
    assert response.diagnostics is not None
    assert response.diagnostics["planner"]["query_mode"] == "computation_chain"
    assert response.diagnostics["evidence_bundle"]["primary_articles"]


def test_phase3_retriever_filters_noisy_reference_neighbors_for_factura_chain() -> None:
    plan = build_graph_retrieval_plan(
        PipelineCRequest(
            message=(
                "¿Qué exige el ET entre los artículos 771-2, 616-1 y 617 "
                "para soportar costos y deducciones con factura electrónica?"
            ),
            topic="facturacion_electronica",
            requested_topic="facturacion_electronica",
        )
    )

    _, evidence = retrieve_graph_evidence(plan)

    connected_keys = [item.node_key for item in evidence.connected_articles]
    support_titles = [item.title_hint for item in evidence.support_documents]

    assert "743" in connected_keys
    assert "1" not in connected_keys
    assert "2" not in connected_keys
    assert "25" not in connected_keys
    assert "27" not in connected_keys
    assert "CAM-N01 — Declaración de Cambio: Marco Legal y Formularios Banco de la República" not in support_titles
    assert "NOM-N01 — Nómina Electrónica: Novedades Operativas — Marco Legal" not in support_titles
    assert "SOC-N02 — Matrícula Mercantil: Marco Legal Compilado" not in support_titles


def test_phase3_retriever_support_docs_keep_practical_or_expert_context_when_available() -> None:
    plan = build_graph_retrieval_plan(
        PipelineCRequest(
            message=(
                "Mi cliente tiene saldo a favor en renta del AG 2025. "
                "¿Cuáles son los requisitos y el procedimiento para solicitar la devolución ante la DIAN? "
                "¿En qué plazos debe radicarse? ¿El trámite cambia si el contribuyente tiene "
                "facturación electrónica al día?"
            ),
            topic="procedimiento_tributario",
            requested_topic="procedimiento_tributario",
        )
    )

    _, evidence = retrieve_graph_evidence(plan)

    support_families = [item.family for item in evidence.support_documents]
    support_pairs = [(item.family, item.topic_key) for item in evidence.support_documents]

    assert "practica" in support_families or "interpretacion" in support_families
    assert ("practica", "procedimiento_tributario") in support_pairs
    assert ("interpretacion", "procedimiento_tributario") in support_pairs


def test_phase3_pipeline_d_end_to_end_smoke_for_historical_reform_query() -> None:
    response = run_pipeline_d(
        PipelineCRequest(
            message="¿Qué decía el artículo 115 antes de la Ley 2277 de 2022?",
            topic="declaracion_renta",
            requested_topic="declaracion_renta",
        )
    )

    assert response.answer_mode == "graph_native"
    assert response.fallback_reason is None
    assert "Recap histórico" in response.answer_markdown
    assert "2021-12-31" in response.answer_markdown
    assert "Ley 2277 de 2022" in response.answer_markdown
    assert "certificación ESAL" not in response.answer_markdown
    assert "Formulario 110" not in response.answer_markdown
    assert response.diagnostics is not None
    assert response.diagnostics["planner"]["query_mode"] == "historical_reform_chain"
    assert response.diagnostics["planner"]["temporal_context"]["cutoff_date"] == "2021-12-31"


def test_phase3_topic_router_prefers_refund_procedure_for_accountant_style_prompt() -> None:
    detection = detect_topic_from_text(
        "Mi cliente tiene saldo a favor en renta del AG 2025. "
        "¿Cuáles son los requisitos y el procedimiento para solicitar la devolución ante la DIAN? "
        "¿En qué plazos debe radicarse? ¿El trámite cambia si el contribuyente tiene "
        "facturación electrónica al día?"
    )

    assert detection.topic == "procedimiento_tributario"
    assert detection.scores["procedimiento_tributario"] > detection.scores["facturacion_electronica"]


def test_phase3_topic_router_detects_planeacion_tributaria_as_renta() -> None:
    detection = detect_topic_from_text(
        "¿Qué estrategias de planeación tributaria legítima puedo implementar para una SAS "
        "sin que la DIAN lo considere abuso en materia tributaria o elusión?"
    )

    assert detection.topic == "declaracion_renta"
    assert detection.scores["declaracion_renta"] >= 3.0


def test_phase3_planner_anchors_tax_planning_prompt_on_antiabuse_articles() -> None:
    plan = build_graph_retrieval_plan(
        PipelineCRequest(
            message=(
                "Cuáles son las estrategias de planeación tributaria legítima que puedo "
                "implementar para un cliente SAS antes del cierre del AG 2026 sin que la "
                "DIAN lo considere abuso del derecho o simulación? ¿Qué criterios ha "
                "definido la jurisprudencia para distinguir planeación legítima de elusión?"
            ),
            topic="declaracion_renta",
            requested_topic="declaracion_renta",
        )
    )

    assert plan.query_mode == "strategy_chain"
    assert "procedimiento_tributario" in plan.topic_hints
    anchored_articles = [entry.lookup_value for entry in plan.entry_points if entry.source == "tax_planning_anchor"]
    assert anchored_articles[:3] == ["869", "869-1", "869-2"]
    article_searches = [entry.lookup_value for entry in plan.entry_points if entry.kind == "article_search"]
    assert any("abuso en materia tributaria" in query for query in article_searches)


def test_phase3_planner_adds_practical_refund_searches_for_accountant_prompt() -> None:
    plan = build_graph_retrieval_plan(
        PipelineCRequest(
            message=(
                "Mi cliente tiene saldo a favor en renta del AG 2025. "
                "¿Cuáles son los requisitos y el procedimiento para solicitar la devolución ante la DIAN? "
                "¿En qué plazos debe radicarse? ¿El trámite cambia si el contribuyente tiene "
                "facturación electrónica al día?"
            ),
            topic="procedimiento_tributario",
            requested_topic="procedimiento_tributario",
        )
    )

    assert plan.query_mode == "obligation_chain"
    assert "procedimiento_tributario" in plan.topic_hints
    assert "calendario_obligaciones" in plan.topic_hints
    assert "declaracion_renta" in plan.topic_hints
    article_searches = [entry.lookup_value for entry in plan.entry_points if entry.kind == "article_search"]
    assert "devolucion saldo a favor requisitos procedimiento dian" in article_searches
    assert "termino solicitar devolucion saldo a favor plazos radicacion" in article_searches
    assert plan.temporal_context.requested_period_label == "AG 2025"


def test_phase3_planner_keeps_loss_compensation_prompt_out_of_saldo_a_favor_workflow() -> None:
    plan = build_graph_retrieval_plan(
        PipelineCRequest(
            message=(
                "Mi cliente acumuló pérdidas fiscales en años anteriores y en AG 2025 tiene renta líquida positiva. "
                "¿Cuál es el régimen legal de compensación de pérdidas fiscales? ¿Hay límite anual? "
                "¿Cómo afecta la compensación al término de firmeza de la declaración y qué precauciones debo tomar?"
            ),
            topic="declaracion_renta",
            requested_topic="declaracion_renta",
        )
    )

    article_searches = [entry.lookup_value for entry in plan.entry_points if entry.kind == "article_search"]
    anchored_articles = [entry.lookup_value for entry in plan.entry_points if entry.source == "loss_compensation_anchor"]

    assert plan.query_mode == "obligation_chain"
    assert anchored_articles == ["147"]
    assert "compensacion de perdidas fiscales renta liquida limite anual art 147" in article_searches
    assert "compensacion de perdidas fiscales firmeza declaracion termino de revision art 147 714 689-3" in article_searches
    assert "correccion declaracion renta saldo a favor plazo un ano firmeza" not in article_searches
    assert "devolucion saldo a favor requisitos procedimiento dian" not in article_searches


def test_phase3_pipeline_d_end_to_end_smoke_for_accountant_style_refund_prompt() -> None:
    response = run_pipeline_d(
        PipelineCRequest(
            message=(
                "Mi cliente tiene saldo a favor en renta del AG 2025. "
                "¿Cuáles son los requisitos y el procedimiento para solicitar la devolución ante la DIAN? "
                "¿En qué plazos debe radicarse? ¿El trámite cambia si el contribuyente tiene "
                "facturación electrónica al día?"
            ),
            topic="procedimiento_tributario",
            requested_topic="procedimiento_tributario",
        )
    )

    assert response.answer_mode == "graph_native"
    assert response.fallback_reason is None
    assert "Ruta sugerida" in response.answer_markdown
    assert "Riesgos y condiciones" in response.answer_markdown
    assert "Soportes clave" in response.answer_markdown
    assert "Anclaje Legal" not in response.answer_markdown
    assert "Recap histórico" not in response.answer_markdown
    assert "(art." in response.answer_markdown or "(arts." in response.answer_markdown
    assert "50, 30 o 20 días hábiles" in response.answer_markdown
    assert "850" in response.answer_markdown
    assert "589" in response.answer_markdown
    assert response.diagnostics is not None
    assert response.diagnostics["planner"]["topic_hints"][0] == "procedimiento_tributario"


def test_phase3_pipeline_d_loss_compensation_prompt_surfaces_art_147_instead_of_saldo_a_favor_route() -> None:
    response = run_pipeline_d(
        PipelineCRequest(
            message=(
                "Mi cliente acumuló pérdidas fiscales en años anteriores y en AG 2025 tiene renta líquida positiva. "
                "¿Cuál es el régimen legal de compensación de pérdidas fiscales? ¿Hay límite anual? "
                "¿Cómo afecta la compensación al término de firmeza de la declaración y qué precauciones debo tomar?"
            ),
            topic="declaracion_renta",
            requested_topic="declaracion_renta",
        )
    )

    assert response.answer_mode == "graph_native"
    assert response.fallback_reason is None
    assert "147" in response.answer_markdown
    assert "pérdidas fiscales" in response.answer_markdown.lower()
    assert "50, 30 o 20 días hábiles" not in response.answer_markdown
    assert response.diagnostics is not None
    assert response.diagnostics["planner"]["query_mode"] == "obligation_chain"


def test_phase3_planner_routes_ica_deduction_prompt_to_computation_chain() -> None:
    plan = build_graph_retrieval_plan(
        PipelineCRequest(
            message="¿Puedo deducir el ICA pagado en mi declaración de renta de persona jurídica?",
            topic="declaracion_renta",
            requested_topic="declaracion_renta",
        )
    )

    assert plan.query_mode == "computation_chain"
    assert "ica" in plan.topic_hints
    assert any(entry.kind == "article_search" for entry in plan.entry_points)


def test_phase3_pipeline_d_recovers_art_115_for_ica_deduction_prompt() -> None:
    request = PipelineCRequest(
        message="¿Puedo deducir el ICA pagado en mi declaración de renta de persona jurídica?",
        topic="declaracion_renta",
        requested_topic="declaracion_renta",
    )

    plan = build_graph_retrieval_plan(request)
    _, evidence = retrieve_graph_evidence(plan)
    response = run_pipeline_d(request)

    assert evidence.primary_articles
    assert evidence.primary_articles[0].node_key == "115"
    assert any(doc.family in {"practica", "interpretacion"} for doc in evidence.support_documents)
    assert response.answer_mode == "graph_native"
    assert "115" in response.answer_markdown
    assert "ICA" in response.answer_markdown
    assert "descuento tributario" in response.answer_markdown
    assert "costo o gasto" in response.answer_markdown
    assert "235-2" not in response.answer_markdown
    assert "Antes de recomendar algo al cliente" not in response.answer_markdown
    assert "Si la consulta es por el tratamiento en renta" not in response.answer_markdown
    assert "versión histórica" not in response.answer_markdown
    assert "Ley 2277 de 2022" not in response.answer_markdown
    assert "Ley 1430 de 2010" not in response.answer_markdown
    assert response.diagnostics["evidence_bundle"]["primary_articles"]


def test_phase3_pipeline_d_anticipo_prompt_does_not_leak_meta_starter_lines() -> None:
    response = run_pipeline_d(
        PipelineCRequest(
            message=(
                "Cuál es el procedimiento para determinar el anticipo de renta del año siguiente "
                "dentro de la declaración del AG 2025? ¿Qué porcentaje aplica según la antigüedad "
                "del contribuyente, sobre qué base se liquida, y en qué casos puedo solicitar "
                "reducción del anticipo ante la DIAN?"
            ),
            topic="declaracion_renta",
            requested_topic="declaracion_renta",
        )
    )

    assert "Empieza por las normas principales de este caso" not in response.answer_markdown
    assert "Toma las normas principales del caso" not in response.answer_markdown
    assert "Antes de recomendar algo al cliente" not in response.answer_markdown
    assert "Si quieres bajar esto a operación" not in response.answer_markdown
    assert "Hay espacio para volver esto más eficiente" not in response.answer_markdown
    assert "Nuestra evaluación:" not in response.answer_markdown
    assert (
        "Define primero cuál es el impuesto neto de renta que sirve de base del anticipo"
        in response.answer_markdown
    )


def test_phase3_pipeline_d_old_ag_prompt_does_not_auto_surface_change_history() -> None:
    response = run_pipeline_d(
        PipelineCRequest(
            message="Para AG 2022, ¿cómo determino el anticipo de renta del año siguiente dentro de la declaración?",
            topic="declaracion_renta",
            requested_topic="declaracion_renta",
        )
    )

    assert "AG 2022" in response.answer_markdown
    assert "Recap histórico" not in response.answer_markdown
    assert "Las normas principales de este tema muestran cambios o reformas relevantes en:" not in response.answer_markdown
    assert "Resolución 000081" not in response.answer_markdown


def test_phase3_pipeline_d_explicit_change_question_still_surfaces_change_history() -> None:
    response = run_pipeline_d(
        PipelineCRequest(
            message="¿Qué ha modificado la Ley 788 de 2002 frente al anticipo de renta?",
            topic="declaracion_renta",
            requested_topic="declaracion_renta",
        )
    )

    assert "Recap histórico" in response.answer_markdown
    assert "Ley 788 de 2002" in response.answer_markdown


def test_phase3_retriever_definition_queries_reserve_practical_support_docs() -> None:
    plan = build_graph_retrieval_plan(
        PipelineCRequest(
            message=(
                "Cuáles son las estrategias de planeación tributaria legítima que puedo "
                "implementar para un cliente SAS antes del cierre del AG 2026 sin que la "
                "DIAN lo considere abuso del derecho o simulación? ¿Qué criterios ha "
                "definido la jurisprudencia para distinguir planeación legítima de elusión?"
            ),
            topic="declaracion_renta",
            requested_topic="declaracion_renta",
        )
    )

    _, evidence = retrieve_graph_evidence(plan)

    families = {str(doc.family or "") for doc in evidence.support_documents}
    titles = " ".join(str(doc.title_hint or "") for doc in evidence.support_documents)

    assert "interpretacion" in families
    assert "practica" in families
    assert "Planeación Tributaria" in titles or "Planeacion Tributaria" in titles


def test_phase3_answer_publication_policy_neutralizes_imputative_or_colloquial_advisory_language() -> None:
    line = (
        "Usa timing solo cuando el hecho económico manda la fecha: puedes acelerar algo ya "
        "ejecutado o diferir algo que realmente ocurrirá después, pero no inventarte entregas, "
        "notas crédito o contratos de papel para mover la base. El cierre sano se juega revisando "
        "contratos y hitos reales en noviembre y diciembre, no maquillando enero desde contabilidad."
    )

    rewritten = neutralize_non_imputative_language(line)

    assert "inventarte" not in rewritten
    assert "contratos de papel" not in rewritten
    assert "maquillando enero" not in rewritten
    assert "contratos sin soporte suficiente" in rewritten
    assert "sin trasladar a diciembre hechos económicos" in rewritten


def test_phase3_pipeline_d_tax_planning_prompt_uses_rich_advisory_first_bubble() -> None:
    request = PipelineCRequest(
        message=(
            "Cuáles son las estrategias de planeación tributaria legítima que puedo "
            "implementar para un cliente SAS antes del cierre del AG 2026 sin que la "
            "DIAN lo considere abuso del derecho o simulación? ¿Qué criterios ha "
            "definido la jurisprudencia para distinguir planeación legítima de elusión?"
        ),
        topic="declaracion_renta",
        requested_topic="declaracion_renta",
    )

    plan = build_graph_retrieval_plan(request)
    _, evidence = retrieve_graph_evidence(plan)
    response = run_pipeline_d(request)

    primary_keys = {item.node_key for item in evidence.primary_articles}

    assert {"869", "869-1", "869-2"}.issubset(primary_keys)
    assert response.diagnostics is not None
    assert response.diagnostics["planner"]["query_mode"] == "strategy_chain"
    assert "Cómo La Trabajaría" in response.answer_markdown
    assert "Estrategias Legítimas A Modelar" in response.answer_markdown
    assert "Qué Mira DIAN Y La Jurisprudencia" in response.answer_markdown
    assert "Papeles De Trabajo" in response.answer_markdown
    assert "Ruta sugerida" not in response.answer_markdown
    assert "economía de opción" in response.answer_markdown or "economia de opcion" in response.answer_markdown
    assert "RST" in response.answer_markdown or "ordinario" in response.answer_markdown
    assert "Exp. 27693" in response.answer_markdown
    assert "Ley 1607 de 2012" in response.answer_markdown
    assert "(art." in response.answer_markdown or "(arts." in response.answer_markdown
    assert "maquillando" not in response.answer_markdown
    assert "inventarte" not in response.answer_markdown
    assert "tramp" not in response.answer_markdown.lower()
    assert "atajo" not in response.answer_markdown.lower()
    assert "presentar inexactitudes contables" in response.answer_markdown or (
        "sin soporte suficiente" in response.answer_markdown
    )


def test_phase3_pipeline_d_does_not_promote_truncated_normative_excerpts_to_answer() -> None:
    response = run_pipeline_d(
        PipelineCRequest(
            message=(
                "Cuáles son las estrategias de planeación tributaria legítima que puedo "
                "implementar para un cliente SAS antes del cierre del AG 2026 sin que la "
                "DIAN lo considere abuso del derecho o simulación? ¿Qué criterios ha "
                "definido la jurisprudencia para distinguir planeación legítima de elusión?"
            ),
            topic="declaracion_renta",
            requested_topic="declaracion_renta",
        )
    )

    assert "activ..." not in response.answer_markdown
    assert "Son deducibles las expensas realizadas durante el año o período gravable" not in response.answer_markdown


def test_phase3_planner_does_not_misclassify_procedural_before_phrase_as_historical() -> None:
    plan = build_graph_retrieval_plan(
        PipelineCRequest(
            message=(
                "Mi cliente quiere corregir una declaración de renta que aumenta el saldo a favor. "
                "¿Todavía está a tiempo, cómo cambia la firmeza y qué debo revisar antes de pedir "
                "devolución o compensación?"
            ),
            topic="procedimiento_tributario",
            requested_topic="procedimiento_tributario",
        )
    )

    assert plan.query_mode == "obligation_chain"
    assert plan.temporal_context.historical_query_intent is False
    article_searches = [entry.lookup_value for entry in plan.entry_points if entry.kind == "article_search"]
    assert "correccion declaracion renta saldo a favor plazo un ano firmeza" in article_searches
    assert "firmeza declaraciones saldo a favor correccion termino de revision" in article_searches


def test_phase3_pipeline_d_end_to_end_smoke_for_correction_and_firmness_prompt() -> None:
    response = run_pipeline_d(
        PipelineCRequest(
            message=(
                "Mi cliente quiere corregir una declaración de renta que aumenta el saldo a favor. "
                "¿Todavía está a tiempo, cómo cambia la firmeza y qué debo revisar antes de pedir "
                "devolución o compensación?"
            ),
            topic="procedimiento_tributario",
            requested_topic="procedimiento_tributario",
        )
    )

    assert response.answer_mode == "graph_native"
    assert response.fallback_reason is None
    assert "588" in response.answer_markdown
    assert "589" in response.answer_markdown
    assert "714" in response.answer_markdown
    assert response.diagnostics is not None
    assert response.diagnostics["planner"]["query_mode"] == "obligation_chain"
    assert response.diagnostics["planner"]["temporal_context"]["historical_query_intent"] is False


def test_phase3_pipeline_d_later_turn_keeps_broad_sectioned_format() -> None:
    response = run_pipeline_d(
        PipelineCRequest(
            message=(
                "Mi cliente tiene saldo a favor en renta del AG 2025. "
                "¿Cuáles son los requisitos y el procedimiento para solicitar la devolución ante la DIAN? "
                "¿En qué plazos debe radicarse? ¿El trámite cambia si el contribuyente tiene "
                "facturación electrónica al día?"
            ),
            topic="procedimiento_tributario",
            requested_topic="procedimiento_tributario",
            conversation_state={"turn_count": 2},
        )
    )

    assert "Procedimiento Sugerido" in response.answer_markdown
    assert "Anclaje Legal" in response.answer_markdown
    assert "Ruta sugerida" not in response.answer_markdown


def test_phase3_planner_carries_forward_norm_anchors_for_focused_followup() -> None:
    plan = build_graph_retrieval_plan(
        PipelineCRequest(
            message="Cuéntame más de eso y cómo afecta la firmeza.",
            conversation_context=(
                "Objetivo vigente: Mi cliente acumuló pérdidas fiscales en años anteriores y en AG 2025 "
                "tiene renta líquida positiva. ¿Cuál es el régimen legal de compensación de pérdidas "
                "fiscales? ¿Hay límite anual? ¿Cómo afecta la compensación al término de firmeza de la "
                "declaración y qué precauciones debo tomar?"
            ),
            conversation_state={
                "turn_count": 2,
                "normative_anchors": ["Art. 589 ET", "Art. 714 ET"],
                "carry_forward_facts": ["AG 2025"],
            },
        )
    )

    article_entries = [entry for entry in plan.entry_points if entry.kind == "article"]

    assert plan.query_mode == "article_lookup"
    assert [entry.lookup_value for entry in article_entries] == ["589", "714"]
    assert all(entry.source == "conversation_state_anchor" for entry in article_entries)
    assert plan.temporal_context.requested_period_label == "AG 2025"


def test_phase3_retriever_followup_anchor_lookup_avoids_noisy_topic_expansion() -> None:
    plan = build_graph_retrieval_plan(
        PipelineCRequest(
            message=(
                "cuéntame más de esto: Recuerda que una corrección a favor reinicia el término de "
                "revisión de la DIAN desde la fecha de la corrección (arts. 589 y 714 ET)."
            ),
            conversation_context=(
                "Objetivo vigente: Mi cliente acumuló pérdidas fiscales en años anteriores y en AG 2025 "
                "tiene renta líquida positiva. ¿Cuál es el régimen legal de compensación de pérdidas "
                "fiscales? ¿Hay límite anual? ¿Cómo afecta la compensación al término de firmeza de la "
                "declaración y qué precauciones debo tomar?"
            ),
            conversation_state={
                "turn_count": 1,
                "normative_anchors": ["Art. 589 ET", "Art. 714 ET"],
            },
        )
    )

    _, evidence = retrieve_graph_evidence(plan)

    assert evidence.support_documents
    assert all(item.family == "normativa" for item in evidence.support_documents)
    assert all("FE_OPERATIVA" not in item.relative_path for item in evidence.support_documents)


def test_phase3_pipeline_d_followup_drilldown_stays_on_double_clicked_point() -> None:
    response = run_pipeline_d(
        PipelineCRequest(
            message=(
                "cuéntame más de esto: Recuerda que una corrección a favor reinicia el término de "
                "revisión de la DIAN desde la fecha de la corrección (arts. 589 y 714 ET)."
            ),
            conversation_context=(
                "Objetivo vigente: Mi cliente acumuló pérdidas fiscales en años anteriores y en AG 2025 "
                "tiene renta líquida positiva. ¿Cuál es el régimen legal de compensación de pérdidas "
                "fiscales? ¿Hay límite anual? ¿Cómo afecta la compensación al término de firmeza de la "
                "declaración y qué precauciones debo tomar?"
            ),
            conversation_state={
                "turn_count": 1,
                "normative_anchors": ["Art. 589 ET", "Art. 714 ET"],
                "carry_forward_facts": ["AG 2025"],
            },
        )
    )

    assert "**En concreto**" in response.answer_markdown
    assert "**Anclaje Legal**" in response.answer_markdown
    assert "Procedimiento Sugerido" not in response.answer_markdown
    assert "Factuning" not in response.answer_markdown
    assert "Portal MUISCA" not in response.answer_markdown
    assert "Habilitación inicial" not in response.answer_markdown


def test_phase3_pipeline_d_categorical_followup_answers_with_verdict_before_sections() -> None:
    response = run_pipeline_d(
        PipelineCRequest(
            message="¿Existe algún límite anual dentro de los 12 años para compensar la pérdida?",
            topic="declaracion_renta",
            requested_topic="declaracion_renta",
            conversation_context=(
                "Objetivo vigente: Mi cliente acumuló pérdidas fiscales en años anteriores y en AG 2025 "
                "tiene renta líquida positiva. ¿Cuál es el régimen legal de compensación de pérdidas "
                "fiscales? ¿Hay límite anual? ¿Cómo afecta la compensación al término de firmeza de la "
                "declaración y qué precauciones debo tomar?"
            ),
            conversation_state={
                "turn_count": 1,
                "normative_anchors": ["Art. 147 ET", "Art. 290 ET"],
                "carry_forward_facts": ["AG 2025"],
            },
        )
    )

    assert response.answer_markdown.startswith("No, no hay un tope o porcentaje anual adicional;")
    assert "doce períodos gravables" in response.answer_markdown or "12 períodos gravables" in response.answer_markdown
    assert "Solo cambia si" in response.answer_markdown
    assert "En la práctica," in response.answer_markdown
    assert "**En concreto**" not in response.answer_markdown
    assert "**Anclaje Legal**" not in response.answer_markdown


def test_phase3_planner_followup_with_numeric_period_echo_keeps_case_anchors() -> None:
    plan = build_graph_retrieval_plan(
        PipelineCRequest(
            message=(
                "cuanto cambia esto? Solo cambia si el saldo viene de años pre-2017, "
                "valida primero el régimen congelado del art. 290 ET antes de aplicar la "
                "regla de 12 años."
            ),
            conversation_context=(
                "Objetivo vigente: Mi cliente acumuló pérdidas fiscales en años anteriores y en AG 2025 "
                "tiene renta líquida positiva. ¿Cuál es el régimen legal de compensación de pérdidas "
                "fiscales? ¿Hay límite anual? ¿Cómo afecta la compensación al término de firmeza de la "
                "declaración y qué precauciones debo tomar?"
            ),
            conversation_state={
                "turn_count": 2,
                "normative_anchors": ["Art. 147 ET", "Art. 290 ET"],
                "carry_forward_facts": ["AG 2025"],
            },
        )
    )

    anchored_articles = [entry.lookup_value for entry in plan.entry_points if entry.kind == "article"]

    assert plan.query_mode == "article_lookup"
    assert "147" in anchored_articles
    assert "290" in anchored_articles
    assert "12" not in anchored_articles


def test_phase3_planner_article_list_ignores_duration_suffix_numbers() -> None:
    refs = _extract_article_refs("arts. 147, 290 y 12 años")

    assert refs == ("147", "290")


def test_phase3_planner_article_list_ignores_amount_suffix_numbers() -> None:
    refs = _extract_article_refs("arts. 147 y 290 con limite de 50 UVT")

    assert refs == ("147", "290")


def test_phase3_pipeline_d_followup_with_embedded_prior_answer_drills_into_new_point_instead_of_repeating() -> None:
    response = run_pipeline_d(
        PipelineCRequest(
            message=(
                "como cambiaría si viene de antes? No, no hay un tope o porcentaje anual adicional; "
                "el límite es temporal: doce períodos gravables siguientes y sin tope porcentual anual "
                "(arts. 147 y 290 ET)."
            ),
            topic="declaracion_renta",
            requested_topic="declaracion_renta",
            conversation_context=(
                "Objetivo vigente: Mi cliente acumuló pérdidas fiscales en años anteriores y en AG 2025 "
                "tiene renta líquida positiva. ¿Cuál es el régimen legal de compensación de pérdidas "
                "fiscales? ¿Hay límite anual? ¿Cómo afecta la compensación al término de firmeza de la "
                "declaración y qué precauciones debo tomar?"
            ),
            conversation_state={
                "turn_count": 2,
                "normative_anchors": ["Art. 147 ET", "Art. 290 ET"],
                "carry_forward_facts": ["AG 2025"],
            },
        )
    )

    assert not response.answer_markdown.startswith("No, no hay un tope o porcentaje anual adicional;")
    assert "pre-2017" in response.answer_markdown or "régimen congelado" in response.answer_markdown
    assert "Solo cambia si" in response.answer_markdown or "Sí cambia si" in response.answer_markdown
    assert "En la práctica," in response.answer_markdown


def test_phase3_pipeline_d_followup_with_numeric_period_echo_stays_on_loss_compensation_case() -> None:
    response = run_pipeline_d(
        PipelineCRequest(
            message=(
                "cuanto cambia esto? Solo cambia si el saldo viene de años pre-2017, "
                "valida primero el régimen congelado del art. 290 ET antes de aplicar la "
                "regla de 12 años."
            ),
            conversation_context=(
                "Objetivo vigente: Mi cliente acumuló pérdidas fiscales en años anteriores y en AG 2025 "
                "tiene renta líquida positiva. ¿Cuál es el régimen legal de compensación de pérdidas "
                "fiscales? ¿Hay límite anual? ¿Cómo afecta la compensación al término de firmeza de la "
                "declaración y qué precauciones debo tomar?"
            ),
            conversation_state={
                "turn_count": 2,
                "normative_anchors": ["Art. 147 ET", "Art. 290 ET"],
                "carry_forward_facts": ["AG 2025"],
            },
        )
    )

    assert "pre-2017" in response.answer_markdown or "régimen congelado" in response.answer_markdown
    assert "Solo cambia si" in response.answer_markdown or "Sí cambia si" in response.answer_markdown
    assert "En la práctica," in response.answer_markdown
    assert "aportes en especie" not in response.answer_markdown.lower()
    assert "patrimonio relevante" not in response.answer_markdown.lower()


def test_phase3_orchestrator_default_mode_reports_artifact_diagnostics(monkeypatch) -> None:
    monkeypatch.delenv("LIA_CORPUS_SOURCE", raising=False)
    monkeypatch.delenv("LIA_GRAPH_MODE", raising=False)

    response = run_pipeline_d(
        PipelineCRequest(
            message="¿Qué dice el ET sobre el artículo 617 y la factura electrónica?",
            topic="facturacion_electronica",
            requested_topic="facturacion_electronica",
        )
    )

    assert response.diagnostics is not None
    assert response.diagnostics.get("retrieval_backend") == "artifacts"
    assert response.diagnostics.get("graph_backend") == "artifacts"


def test_phase3_orchestrator_staging_flags_dispatch_to_cloud_adapters(monkeypatch) -> None:
    from lia_graph.pipeline_d import orchestrator as orchestrator_mod

    captured: dict[str, int] = {"supabase": 0, "falkor": 0}

    def fake_supabase_retrieve(plan, *, artifacts_dir=None, client=None):
        captured["supabase"] += 1
        from lia_graph.pipeline_d.contracts import GraphEvidenceBundle
        return plan, GraphEvidenceBundle(
            primary_articles=(),
            connected_articles=(),
            related_reforms=(),
            support_documents=(),
            citations=(),
            diagnostics={"retrieval_backend": "supabase", "chunk_row_count": 0},
        )

    def fake_falkor_retrieve(plan, *, artifacts_dir=None, graph_client=None):
        captured["falkor"] += 1
        from lia_graph.pipeline_d.contracts import GraphEvidenceBundle
        return plan, GraphEvidenceBundle(
            primary_articles=(),
            connected_articles=(),
            related_reforms=(),
            support_documents=(),
            citations=(),
            diagnostics={"graph_backend": "falkor_live"},
        )

    from lia_graph.pipeline_d import retriever_supabase as retriever_supabase_mod
    from lia_graph.pipeline_d import retriever_falkor as retriever_falkor_mod
    monkeypatch.setattr(retriever_supabase_mod, "retrieve_graph_evidence", fake_supabase_retrieve)
    monkeypatch.setattr(retriever_falkor_mod, "retrieve_graph_evidence", fake_falkor_retrieve)
    monkeypatch.setenv("LIA_CORPUS_SOURCE", "supabase")
    monkeypatch.setenv("LIA_GRAPH_MODE", "falkor_live")

    response = run_pipeline_d(
        PipelineCRequest(
            message="consulta",
            topic="facturacion_electronica",
            requested_topic="facturacion_electronica",
        )
    )

    assert captured["supabase"] == 1
    assert captured["falkor"] == 1
    assert response.diagnostics is not None
    assert response.diagnostics.get("retrieval_backend") == "supabase"
    assert response.diagnostics.get("graph_backend") == "falkor_live"
