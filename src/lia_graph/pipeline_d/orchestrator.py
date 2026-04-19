from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from ..pipeline_c.contracts import PipelineCRequest, PipelineCResponse
from .answer_assembly import (
    compose_main_chat_answer as _compose_main_chat_answer,
)
from .answer_llm_polish import polish_graph_native_answer
from .answer_synthesis import build_graph_native_answer_parts
from .contracts import GraphEvidenceBundle, GraphRetrievalPlan
from .planner import build_graph_retrieval_plan
from .retriever import retrieve_graph_evidence as _retrieve_artifacts


_CORPUS_SOURCE_ENV = "LIA_CORPUS_SOURCE"
_GRAPH_MODE_ENV = "LIA_GRAPH_MODE"
_VALID_CORPUS_SOURCES = {"artifacts", "supabase"}
_VALID_GRAPH_MODES = {"artifacts", "falkor_live"}


def _current_corpus_source() -> str:
    raw = str(os.getenv(_CORPUS_SOURCE_ENV, "artifacts") or "").strip().lower()
    return raw if raw in _VALID_CORPUS_SOURCES else "artifacts"


def _current_graph_mode() -> str:
    raw = str(os.getenv(_GRAPH_MODE_ENV, "artifacts") or "").strip().lower()
    return raw if raw in _VALID_GRAPH_MODES else "artifacts"


def _artifacts_dir_from_index_file(index_file: object | None) -> Path | None:
    if index_file is None:
        return None
    path = Path(str(index_file))
    if path.name == "canonical_corpus_manifest.json":
        return path.parent
    return None


def _retrieve_evidence(
    plan: GraphRetrievalPlan,
    *,
    artifacts_dir: Path | None,
) -> tuple[GraphRetrievalPlan, GraphEvidenceBundle, dict[str, str]]:
    corpus_source = _current_corpus_source()
    graph_mode = _current_graph_mode()
    backend_diagnostics = {
        "retrieval_backend": corpus_source,
        "graph_backend": graph_mode,
    }

    if corpus_source == "artifacts" and graph_mode == "artifacts":
        hydrated_plan, evidence = _retrieve_artifacts(plan, artifacts_dir=artifacts_dir)
        return hydrated_plan, _attach_backend_diagnostics(evidence, backend_diagnostics), backend_diagnostics

    # Import lazily so dev mode never pulls the Supabase/Falkor modules unless
    # the caller opted into cloud-live retrieval.
    if corpus_source == "supabase":
        from .retriever_supabase import retrieve_graph_evidence as _retrieve_supabase
        supabase_plan, supabase_evidence = _retrieve_supabase(plan, artifacts_dir=artifacts_dir)
    else:
        supabase_plan, supabase_evidence = _retrieve_artifacts(plan, artifacts_dir=artifacts_dir)

    if graph_mode == "falkor_live":
        from .retriever_falkor import retrieve_graph_evidence as _retrieve_falkor
        falkor_plan, falkor_evidence = _retrieve_falkor(plan, artifacts_dir=artifacts_dir)
        merged_plan = falkor_plan
        merged_evidence = _merge_graph_and_chunk_evidence(
            graph_evidence=falkor_evidence,
            chunk_evidence=supabase_evidence,
            backend_diagnostics=backend_diagnostics,
        )
        return merged_plan, merged_evidence, backend_diagnostics

    # Supabase for chunks, artifacts for graph (fallback combination).
    return supabase_plan, _attach_backend_diagnostics(supabase_evidence, backend_diagnostics), backend_diagnostics


def _attach_backend_diagnostics(
    evidence: GraphEvidenceBundle,
    backend_diagnostics: dict[str, str],
) -> GraphEvidenceBundle:
    diagnostics = dict(evidence.diagnostics)
    diagnostics.update(backend_diagnostics)
    return GraphEvidenceBundle(
        primary_articles=evidence.primary_articles,
        connected_articles=evidence.connected_articles,
        related_reforms=evidence.related_reforms,
        support_documents=evidence.support_documents,
        citations=evidence.citations,
        diagnostics=diagnostics,
    )


def _merge_graph_and_chunk_evidence(
    *,
    graph_evidence: GraphEvidenceBundle,
    chunk_evidence: GraphEvidenceBundle,
    backend_diagnostics: dict[str, str],
) -> GraphEvidenceBundle:
    diagnostics = dict(chunk_evidence.diagnostics)
    diagnostics.update(graph_evidence.diagnostics)
    diagnostics.update(backend_diagnostics)
    # Preserve each half's `empty_reason` separately so an operator can still
    # see e.g. `chunks_empty_reason=corpus_not_seeded` even when the graph
    # half saved the turn. Otherwise the winning half's reason masks a real
    # ingestion gap on the losing half.
    chunks_reason = chunk_evidence.diagnostics.get("empty_reason")
    graph_reason = graph_evidence.diagnostics.get("empty_reason")
    if isinstance(chunks_reason, str):
        diagnostics["chunks_empty_reason"] = chunks_reason
    if isinstance(graph_reason, str):
        diagnostics["graph_empty_reason"] = graph_reason
    primary = graph_evidence.primary_articles or chunk_evidence.primary_articles
    connected = graph_evidence.connected_articles or chunk_evidence.connected_articles
    related = graph_evidence.related_reforms or chunk_evidence.related_reforms
    return GraphEvidenceBundle(
        primary_articles=primary,
        connected_articles=connected,
        related_reforms=related,
        support_documents=chunk_evidence.support_documents,
        citations=chunk_evidence.citations,
        diagnostics=diagnostics,
    )


def _compose_graph_native_answer(
    *,
    request: PipelineCRequest,
    answer_mode: str,
    planner_query_mode: str,
    temporal_context: dict[str, object],
    evidence: GraphEvidenceBundle,
    sub_questions: tuple[str, ...] = (),
) -> str:
    answer_parts = build_graph_native_answer_parts(
        request=request,
        answer_mode=answer_mode,
        planner_query_mode=planner_query_mode,
        temporal_context=temporal_context,
        evidence=evidence,
        sub_questions=sub_questions,
    )
    answer = _compose_main_chat_answer(
        request=request,
        answer_mode=answer_mode,
        planner_query_mode=planner_query_mode,
        temporal_context=temporal_context,
        evidence=evidence,
        answer_parts=answer_parts,
    )
    if answer:
        return answer
    if answer_mode == "graph_native_partial":
        return (
            "Usa esta salida solo como orientación inicial y confirma el expediente antes de convertirla en instrucción cerrada para el cliente."
        )
    return "Con la evidencia disponible todavía no alcanzo una recomendación operativa suficientemente confiable."


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

    backend_diagnostics = {
        "retrieval_backend": _current_corpus_source(),
        "graph_backend": _current_graph_mode(),
    }
    try:
        plan = build_graph_retrieval_plan(request)
        artifacts_dir = _artifacts_dir_from_index_file(index_file)
        if sink is not None and callable(status):
            status("pipeline_d", "Recuperando evidencia desde graph artifacts y canonical manifest...")
        plan, evidence, backend_diagnostics = _retrieve_evidence(plan, artifacts_dir=artifacts_dir)
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
                "retrieval_backend": backend_diagnostics.get("retrieval_backend"),
                "graph_backend": backend_diagnostics.get("graph_backend"),
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
    retrieval_health = _build_retrieval_health(
        evidence=evidence,
        backend_diagnostics=backend_diagnostics,
    )
    if not evidence.primary_articles:
        answer_mode = "graph_native_partial"
        fallback_reason = "pipeline_d_no_graph_primary_articles"
        coverage_notice = _compose_partial_coverage_notice(retrieval_health)

    answer = _compose_graph_native_answer(
        request=request,
        answer_mode=answer_mode,
        planner_query_mode=plan.query_mode,
        temporal_context=plan.temporal_context.to_dict(),
        evidence=evidence,
        sub_questions=plan.sub_questions,
    )
    polished_answer, llm_runtime_diag = polish_graph_native_answer(
        request=request,
        template_answer=answer,
        evidence=evidence,
        runtime_config_path=runtime_config_path,
    )
    answer = polished_answer
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
            "retrieval_backend": backend_diagnostics.get("retrieval_backend"),
            "graph_backend": backend_diagnostics.get("graph_backend"),
            "retrieval_health": retrieval_health,
        },
        llm_runtime=dict(llm_runtime_diag),
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


_EMPTY_REASON_HINTS: dict[str, str] = {
    "no_explicit_article_keys_in_plan": (
        "el planner no pudo anclar articulos explicitos para esta consulta"
    ),
    "graph_not_seeded": (
        "el grafo normativo aun no esta sembrado en este entorno; hay que correr la ingesta"
    ),
    "schema_drift:retriever_expects_article_number_but_data_uses_article_key": (
        "los nodos del grafo exponen 'article_key' pero el retriever consulta 'article_number' — desalineacion de esquema"
    ),
    "no_matching_article_numbers": (
        "los anclajes del planner no existen como nodos en el grafo"
    ),
    "primary_fetch_zero_despite_canonical_matches": (
        "los nodos matchean la propiedad canonica pero el fetch principal los devuelve vacios — revisar aliasing"
    ),
    "graph_probe_failed": "el grafo no respondio la sonda de diagnostico",
    "corpus_not_seeded": (
        "el corpus Supabase aun no esta sembrado en este entorno; hay que correr el sink"
    ),
    "no_lexical_or_vector_hits": (
        "Supabase tiene chunks pero ninguno matcheo la query — revisar ranking o reformulacion"
    ),
    "chunks_probe_unknown_count": "Supabase no reporto conteo al sondeo",
    "chunks_probe_failed": "fallo la sonda de diagnostico sobre Supabase",
}


def _build_retrieval_health(
    *,
    evidence: GraphEvidenceBundle,
    backend_diagnostics: dict[str, str],
) -> dict[str, object]:
    """Flatten retriever diagnostics into a production-safe health block.

    This block is always surfaced in `response.diagnostics.retrieval_health`
    regardless of debug mode — it contains no PII and it is the only thing that
    lets operators tell schema-drift, unseeded corpus, and planner misses
    apart in partial-mode traces.
    """
    diag = dict(evidence.diagnostics or {})
    keys_of_interest = (
        "empty_reason",
        "chunks_empty_reason",
        "graph_empty_reason",
        "article_node_total",
        "article_node_matches_by_article_number",
        "article_node_matches_by_article_key",
        "seed_article_keys",
        "chunk_row_count",
        "document_row_count",
        "document_chunks_total",
        "chunks_probe_error",
        "primary_article_count",
        "connected_article_count",
        "related_reform_count",
        "graph_name",
        "planner_query_mode",
    )
    health: dict[str, object] = {
        "retrieval_backend": backend_diagnostics.get("retrieval_backend"),
        "graph_backend": backend_diagnostics.get("graph_backend"),
        "primary_article_count": len(evidence.primary_articles),
        "connected_article_count": len(evidence.connected_articles),
        "support_document_count": len(evidence.support_documents),
    }
    for key in keys_of_interest:
        if key in diag:
            health[key] = diag[key]
    empty_reason = health.get("empty_reason")
    if isinstance(empty_reason, str) and empty_reason != "ok":
        health["empty_reason_hint"] = _EMPTY_REASON_HINTS.get(
            empty_reason,
            "razon de vacio no reconocida — revisar retriever",
        )
    return health


def _compose_partial_coverage_notice(retrieval_health: dict[str, object]) -> str:
    """Coverage notice that names the real reason, not a boilerplate."""
    reason = retrieval_health.get("empty_reason")
    hint = retrieval_health.get("empty_reason_hint")
    base = (
        "La ruta graph-native no encontro articulos ancla suficientes; "
        "se devolvio la mejor evidencia parcial disponible."
    )
    if isinstance(reason, str) and isinstance(hint, str):
        return f"{base} Causa: {hint} (empty_reason={reason})."
    return base


__all__ = [
    "run_pipeline_d",
]
