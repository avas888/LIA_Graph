from __future__ import annotations

from uuid import uuid4

from .contracts import PipelineCRequest, PipelineCResponse


def generate_llm_strict(*args: object, **kwargs: object) -> dict[str, object]:
    """Compatibility shim that preserves the shared response contract for now."""
    prompt = str(kwargs.get("prompt") or "")
    return {
        "content": prompt.strip(),
        "reasoning_content": None,
        "finish_reason": "compat_stub",
        "usage": None,
    }


def run_pipeline_c(
    request: PipelineCRequest,
    *,
    index_file: object | None = None,
    policy_path: object | None = None,
    runtime_config_path: object | None = None,
    stream_sink: object | None = None,
) -> PipelineCResponse:
    answer = (
        "La capa compartida de LIA_Graph fue restaurada parcialmente y el "
        "orquestador heredado de la aplicacion previa todavia no se ha reincorporado "
        "completo en este repo."
    )
    sink = stream_sink
    if sink is not None:
        status = getattr(sink, "status", None)
        on_llm_delta = getattr(sink, "on_llm_delta", None)
        if callable(status):
            status("pipeline_c", "Resolviendo la ruta baseline compatible...")
        if callable(on_llm_delta):
            on_llm_delta(answer)
    return PipelineCResponse(
        trace_id=str(request.trace_id or uuid4().hex),
        run_id=uuid4().hex,
        answer_markdown=answer,
        answer_concise=answer,
        followup_queries=(),
        citations=(),
        confidence_score=0.05,
        confidence_mode="compat_stub",
        answer_mode="compat_stub",
        compose_quality=0.0,
        fallback_reason="pipeline_c_orchestrator_not_restored",
        evidence_snippets=(),
        diagnostics={
            "compatibility_mode": True,
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
        coverage_notice="Compatibilidad temporal mientras se restaura la capa compartida.",
        pipeline_variant="pipeline_c",
        pipeline_route="pipeline_c",
    )
