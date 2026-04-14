from __future__ import annotations

import os
from dataclasses import dataclass, replace
from typing import Any, Protocol

from .pipeline_c.contracts import PipelineCRequest, PipelineCResponse

DEFAULT_PIPELINE_VARIANT = "pipeline_c"
_PIPELINE_VARIANT_ENV = "LIA_PIPELINE_VARIANT"
_DUAL_RUN_PRIMARY_ENV = "LIA_PIPELINE_DUAL_RUN_PRIMARY"

_PIPELINE_VARIANT_ALIASES = {
    "baseline": "pipeline_c",
    "compat": "pipeline_c",
    "compat_stub": "pipeline_c",
    "graph": "pipeline_d",
    "graphrag": "pipeline_d",
    "pipeline-c": "pipeline_c",
    "pipeline-d": "pipeline_d",
    "dual": "dual_run",
    "dual-run": "dual_run",
}


class PipelineRunner(Protocol):
    def __call__(
        self,
        request: PipelineCRequest,
        *,
        index_file: object | None = None,
        policy_path: object | None = None,
        runtime_config_path: object | None = None,
        stream_sink: Any | None = None,
    ) -> PipelineCResponse: ...


@dataclass(frozen=True)
class ResolvedPipelineRoute:
    route: str
    pipeline_variant: str
    source: str
    shadow_pipeline_variant: str | None = None


@dataclass(frozen=True)
class PipelineExecutionResult:
    route: ResolvedPipelineRoute
    response: PipelineCResponse


def normalize_pipeline_variant(
    value: str | None,
    *,
    allow_dual_run: bool = True,
    default: str = DEFAULT_PIPELINE_VARIANT,
) -> str:
    raw = str(value or "").strip().lower()
    normalized = _PIPELINE_VARIANT_ALIASES.get(raw, raw)
    if normalized not in {"pipeline_c", "pipeline_d", "dual_run"}:
        return default
    if normalized == "dual_run" and not allow_dual_run:
        return default
    return normalized


def resolve_pipeline_route(
    *,
    request_override: str | None = None,
    default_variant: str | None = None,
) -> ResolvedPipelineRoute:
    override = str(request_override or "").strip()
    if override:
        route = normalize_pipeline_variant(override)
        source = "request_override"
    else:
        configured_default = (
            str(default_variant or "").strip()
            or str(os.getenv(_PIPELINE_VARIANT_ENV, DEFAULT_PIPELINE_VARIANT)).strip()
        )
        route = normalize_pipeline_variant(configured_default)
        source = "config_default"

    if route != "dual_run":
        return ResolvedPipelineRoute(
            route=route,
            pipeline_variant=route,
            source=source,
            shadow_pipeline_variant=None,
        )

    primary = normalize_pipeline_variant(
        os.getenv(_DUAL_RUN_PRIMARY_ENV, DEFAULT_PIPELINE_VARIANT),
        allow_dual_run=False,
    )
    shadow = "pipeline_d" if primary == "pipeline_c" else "pipeline_c"
    return ResolvedPipelineRoute(
        route="dual_run",
        pipeline_variant=primary,
        source=source,
        shadow_pipeline_variant=shadow,
    )


def execute_routed_pipeline(
    request: PipelineCRequest,
    *,
    route: ResolvedPipelineRoute,
    pipeline_c_runner: PipelineRunner,
    pipeline_d_runner: PipelineRunner,
    index_file: object | None = None,
    policy_path: object | None = None,
    runtime_config_path: object | None = None,
    stream_sink: Any | None = None,
) -> PipelineExecutionResult:
    runner: PipelineRunner
    if route.pipeline_variant == "pipeline_d":
        runner = pipeline_d_runner
    else:
        runner = pipeline_c_runner

    response = runner(
        request,
        index_file=index_file,
        policy_path=policy_path,
        runtime_config_path=runtime_config_path,
        stream_sink=stream_sink,
    )
    response_with_route = replace(
        response,
        pipeline_variant=route.pipeline_variant,
        pipeline_route=route.route,
        shadow_pipeline_variant=route.shadow_pipeline_variant,
    )
    return PipelineExecutionResult(route=route, response=response_with_route)


__all__ = [
    "DEFAULT_PIPELINE_VARIANT",
    "PipelineExecutionResult",
    "PipelineRunner",
    "ResolvedPipelineRoute",
    "execute_routed_pipeline",
    "normalize_pipeline_variant",
    "resolve_pipeline_route",
]
