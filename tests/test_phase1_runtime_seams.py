from __future__ import annotations

from dataclasses import dataclass, field

from lia_graph.chat_runs_store import create_chat_run, summarize_chat_run_metrics
from lia_graph.pipeline_c.contracts import PipelineCRequest, PipelineCResponse
from lia_graph.pipeline_c.orchestrator import run_pipeline_c
from lia_graph.pipeline_router import DEFAULT_PIPELINE_VARIANT, execute_routed_pipeline, resolve_pipeline_route


@dataclass
class _StreamProbe:
    statuses: list[tuple[str, str]] = field(default_factory=list)
    deltas: list[str] = field(default_factory=list)

    def status(self, stage: str, message: str) -> None:
        self.statuses.append((stage, message))

    def on_llm_delta(self, delta: str) -> None:
        self.deltas.append(delta)


def test_resolve_pipeline_route_defaults_to_pipeline_d() -> None:
    route = resolve_pipeline_route(default_variant=DEFAULT_PIPELINE_VARIANT)
    assert route.route == "pipeline_d"
    assert route.pipeline_variant == "pipeline_d"
    assert route.shadow_pipeline_variant is None
    assert route.source == "config_default"


def test_resolve_pipeline_route_honors_request_override() -> None:
    route = resolve_pipeline_route(
        request_override="graph",
        default_variant="pipeline_c",
    )
    assert route.route == "pipeline_d"
    assert route.pipeline_variant == "pipeline_d"
    assert route.shadow_pipeline_variant is None
    assert route.source == "request_override"


def test_resolve_pipeline_route_maps_dual_run_to_primary_and_shadow() -> None:
    route = resolve_pipeline_route(
        request_override="dual-run",
        default_variant="pipeline_c",
    )
    assert route.route == "dual_run"
    assert route.pipeline_variant == "pipeline_d"
    assert route.shadow_pipeline_variant == "pipeline_c"


def test_execute_routed_pipeline_uses_selected_runner_and_keeps_contract_shape() -> None:
    request = PipelineCRequest(message="hola", trace_id="trace_1")
    route = resolve_pipeline_route(request_override="pipeline_d", default_variant="pipeline_c")

    def _baseline_runner(
        _: PipelineCRequest,
        *,
        index_file: object | None = None,
        policy_path: object | None = None,
        runtime_config_path: object | None = None,
        stream_sink: object | None = None,
    ) -> PipelineCResponse:
        return PipelineCResponse(
            trace_id="trace_1",
            run_id="pc_run",
            answer_markdown="baseline",
            answer_concise="baseline",
            followup_queries=(),
            citations=(),
            confidence_score=0.1,
            confidence_mode="stub",
        )

    def _graph_runner(
        _: PipelineCRequest,
        *,
        index_file: object | None = None,
        policy_path: object | None = None,
        runtime_config_path: object | None = None,
        stream_sink: object | None = None,
    ) -> PipelineCResponse:
        return PipelineCResponse(
            trace_id="trace_1",
            run_id="pd_run",
            answer_markdown="graph",
            answer_concise="graph",
            followup_queries=(),
            citations=(),
            confidence_score=0.2,
            confidence_mode="stub",
        )

    execution = execute_routed_pipeline(
        request,
        route=route,
        pipeline_c_runner=_baseline_runner,
        pipeline_d_runner=_graph_runner,
    )

    assert execution.response.run_id == "pd_run"
    assert execution.response.pipeline_variant == "pipeline_d"
    assert execution.response.pipeline_route == "pipeline_d"
    assert execution.response.shadow_pipeline_variant is None
    assert "pipeline_variant" not in execution.response.to_dict()
    assert "pipeline_route" not in execution.response.to_dict()
    assert "shadow_pipeline_variant" not in execution.response.to_dict()


def test_chat_run_metrics_group_pipeline_variants(tmp_path) -> None:
    create_chat_run(
        trace_id="trace_c",
        session_id="session_1",
        client_turn_id="turn_1",
        request_fingerprint="fp_c",
        endpoint="/api/chat",
        request_payload={"pipeline_variant": "pipeline_c"},
        base_dir=tmp_path,
    )
    create_chat_run(
        trace_id="trace_d",
        session_id="session_1",
        client_turn_id="turn_2",
        request_fingerprint="fp_d",
        endpoint="/api/chat",
        request_payload={"pipeline_variant": "pipeline_d"},
        base_dir=tmp_path,
    )

    summary = summarize_chat_run_metrics(base_dir=tmp_path)

    assert summary["sample_size"] == 2
    assert summary["pipeline_variants"] == {"pipeline_c": 1, "pipeline_d": 1}


def test_pipeline_c_compat_runner_supports_stream_sink() -> None:
    probe = _StreamProbe()

    response = run_pipeline_c(
        PipelineCRequest(message="hola", trace_id="trace_stream"),
        stream_sink=probe,
    )

    assert response.pipeline_variant == "pipeline_c"
    assert probe.statuses
    assert probe.deltas
