from __future__ import annotations

from uuid import uuid4

from ..pipeline_c.contracts import PipelineCRequest, PipelineCResponse


def run_pipeline_d(
    request: PipelineCRequest,
    *,
    index_file: object | None = None,
    policy_path: object | None = None,
    runtime_config_path: object | None = None,
    stream_sink: object | None = None,
) -> PipelineCResponse:
    answer = (
        "Pipeline D quedo cableado detras del runtime seam de LIA, "
        "pero el planner y la recuperacion graph-native todavia no estan "
        "implementados en esta fase."
    )
    sink = stream_sink
    if sink is not None:
        status = getattr(sink, "status", None)
        on_llm_delta = getattr(sink, "on_llm_delta", None)
        if callable(status):
            status("pipeline_d", "Resolviendo la ruta graph-native compatible...")
        if callable(on_llm_delta):
            on_llm_delta(answer)

    return PipelineCResponse(
        trace_id=str(request.trace_id or uuid4().hex),
        run_id=f"pd_{uuid4().hex}",
        answer_markdown=answer,
        answer_concise=answer,
        followup_queries=(),
        citations=(),
        confidence_score=0.1,
        confidence_mode="compat_stub",
        answer_mode="compat_stub",
        compose_quality=0.0,
        fallback_reason="pipeline_d_planner_not_implemented",
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
        coverage_notice="Compatibilidad temporal mientras se construye el motor graph-native.",
        pipeline_variant="pipeline_d",
        pipeline_route="pipeline_d",
    )
