from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from ..pipeline_c.contracts import PipelineCRequest, PipelineCResponse
from .answer_assembly import (
    compose_main_chat_answer as _compose_main_chat_answer,
)
from .answer_synthesis import build_graph_native_answer_parts
from .contracts import GraphEvidenceBundle
from .planner import build_graph_retrieval_plan
from .retriever import retrieve_graph_evidence


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
    answer_parts = build_graph_native_answer_parts(
        request=request,
        answer_mode=answer_mode,
        planner_query_mode=planner_query_mode,
        temporal_context=temporal_context,
        evidence=evidence,
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
