from __future__ import annotations

from http import HTTPStatus
from typing import Any, Callable

from .interpretacion import (
    run_citation_interpretations_request,
    run_expert_panel_enhance_request,
    run_expert_panel_explore_request,
    run_expert_panel_request,
    run_interpretation_summary_request,
)

_AnalysisRunner = Callable[[dict[str, Any]], tuple[int, dict[str, Any], Any]]

_ANALYSIS_POST_RUNNERS: dict[str, _AnalysisRunner] = {
    "/api/expert-panel": run_expert_panel_request,
    "/api/expert-panel/enhance": run_expert_panel_enhance_request,
    "/api/expert-panel/explore": run_expert_panel_explore_request,
    "/api/citation-interpretations": run_citation_interpretations_request,
    "/api/interpretation-summary": run_interpretation_summary_request,
}


def _read_object_payload(handler: Any) -> dict[str, Any] | None:
    payload = handler._read_json_payload(object_error="Se requiere un objeto JSON.")
    if payload is None:
        return None
    return payload if isinstance(payload, dict) else {}


def handle_analysis_post(handler: Any, path: str, *, deps: dict[str, Any]) -> bool:
    """Dispatch Interpretación/Expertos POST routes to the dedicated surface package.

    This controller deliberately stays thin. Main chat owns the answer bubble,
    `Normativa` owns its own deterministic-plus-graph path, and `Interpretación`
    runs as its own surface track after the chat turn publishes. The shared
    kernel is the turn context, not a blocking dependency on `Normativa`.
    """

    runner = _ANALYSIS_POST_RUNNERS.get(path)
    if runner is None:
        return False

    payload = _read_object_payload(handler)
    if payload is None:
        return True

    try:
        status, response_payload, _ = runner(payload, deps=deps)
    except Exception as exc:  # noqa: BLE001
        handler._send_json(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {
                "error": "analysis_request_failed",
                "details": str(exc),
                "path": path,
            },
        )
        return True

    handler._send_json(status, response_payload)
    return True
