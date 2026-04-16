from __future__ import annotations

from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d.orchestrator import run_pipeline_d
from lia_graph.pipeline_d.planner import build_graph_retrieval_plan
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
    assert "histórica" in response.answer_markdown
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
    assert "Qué Haría Primero" in response.answer_markdown
    assert "Procedimiento Sugerido" in response.answer_markdown
    assert "Anclaje Legal" in response.answer_markdown
    assert "Precauciones" in response.answer_markdown
    assert "50, 30 o 20 días hábiles" in response.answer_markdown
    assert "850" in response.answer_markdown
    assert "589" in response.answer_markdown
    assert "815" in response.answer_markdown
    assert response.answer_markdown.index("**Oportunidades**") < response.answer_markdown.index(
        "**Cambios y Contexto Legal**"
    )
    assert response.diagnostics is not None
    assert response.diagnostics["planner"]["topic_hints"][0] == "procedimiento_tributario"


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
