from __future__ import annotations

import json
import logging
import threading
import time
from http import HTTPStatus
from typing import Any
from uuid import uuid4

from .chat_response_modes import (
    DEFAULT_FIRST_RESPONSE_MODE,
    DEFAULT_RESPONSE_DEPTH,
    normalize_first_response_mode,
    normalize_response_depth,
)
from .ui_chat_context import (
    ChatRequestContext,
    _default_session_payload,
    _optional_text,
)
from .ui_chat_persistence import (
    _schedule_success_persistence,
    persist_assistant_turn,
    persist_user_turn,
)

_log = logging.getLogger(__name__)


def filter_diagnostics_for_public_response(
    orchestrator_diagnostics: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Strip diagnostics for non-debug users but keep `retrieval_health`.

    `retrieval_health` is the minimal, PII-free observability contract we
    guarantee in every environment: operators reading production traces need
    to be able to tell schema-drift, unseeded-corpus, and planner-miss apart
    on `graph_native_partial` turns without waiting for a debug-mode repro.
    Everything else in the orchestrator's diagnostics (planner plan,
    evidence_bundle, etc.) stays hidden.
    """
    if not isinstance(orchestrator_diagnostics, dict):
        return None
    retrieval_health = orchestrator_diagnostics.get("retrieval_health")
    if isinstance(retrieval_health, dict) and retrieval_health:
        return {"retrieval_health": dict(retrieval_health)}
    return None


# ---------------------------------------------------------------------------
# Lazy-import helpers
# ---------------------------------------------------------------------------


def _ui() -> Any:
    """Lazy accessor for lia_graph.ui_server (avoids circular import)."""
    from . import ui_server as _mod
    return _mod


# ---------------------------------------------------------------------------
# Error helpers
# ---------------------------------------------------------------------------


def _build_public_api_error(
    *,
    code: str,
    message: str,
    stage: str,
    http_status: int,
    trace_id: str | None = None,
    run_id: str | None = None,
    remediation: list[str] | tuple[str, ...] | None = None,
    llm_runtime: dict[str, Any] | None = None,
    timing: dict[str, Any] | None = None,
    diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    llm = dict(llm_runtime or {})
    return {
        "code": str(code).strip() or "PC_INTERNAL_ERROR",
        "message": str(message).strip() or "Error de ejecución.",
        "stage": str(stage).strip() or "api",
        "trace_id": str(trace_id or "").strip() or None,
        "run_id": str(run_id or "").strip() or None,
        "http_status": int(http_status),
        "remediation": [str(item) for item in list(remediation or [])],
        "llm": {
            "selected_provider": llm.get("selected_provider"),
            "selected_type": llm.get("selected_type"),
            "model": llm.get("model") or llm.get("selected_model"),
            "attempts": list(llm.get("attempts") or []),
        },
        "timing": {
            "pipeline_total_ms": float((timing or {}).get("pipeline_total_ms") or 0.0),
            "stages_ms": dict((timing or {}).get("stages_ms") or {}),
        },
        "diagnostics": dict(diagnostics or {}),
    }


def _http_status_from_error_payload(payload: dict[str, Any]) -> HTTPStatus:
    error = payload.get("error")
    if isinstance(error, dict):
        try:
            return HTTPStatus(int(error.get("http_status") or HTTPStatus.INTERNAL_SERVER_ERROR))
        except ValueError:
            return HTTPStatus.INTERNAL_SERVER_ERROR
    return HTTPStatus.INTERNAL_SERVER_ERROR


# ---------------------------------------------------------------------------
# Request sending helpers
# ---------------------------------------------------------------------------


def send_api_chat_error(
    handler: Any,
    *,
    t_api_chat: float,
    trace_id: str | None,
    status: HTTPStatus,
    code: str,
    message: str,
    stage: str,
    remediation: list[str] | tuple[str, ...],
    deps: dict[str, Any],
    diagnostics: dict[str, Any] | None = None,
    llm_runtime: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> None:
    error_payload = deps["build_public_api_error"](
        code=code,
        message=message,
        stage=stage,
        http_status=int(status),
        trace_id=trace_id,
        run_id=run_id,
        remediation=remediation,
        llm_runtime=llm_runtime,
        timing={"pipeline_total_ms": round((time.monotonic() - t_api_chat) * 1000, 2), "stages_ms": {}},
        diagnostics=diagnostics,
    )
    handler._send_json(
        status,
        {"ok": False, "error": error_payload},
        extra_headers={"X-LIA-Error-Code": str(error_payload.get("code") or code)},
    )


def _send_existing_chat_run_response(handler: Any, payload: dict[str, Any]) -> None:
    if bool(payload.get("ok", True)):
        handler._send_json(HTTPStatus.OK, payload)
        return
    status = _http_status_from_error_payload(payload)
    error = payload.get("error")
    extra_headers = None
    if isinstance(error, dict):
        extra_headers = {"X-LIA-Error-Code": str(error.get("code") or "CHAT_RUN_FAILED")}
    handler._send_json(status, payload, extra_headers=extra_headers)


# ---------------------------------------------------------------------------
# Request parsing
# ---------------------------------------------------------------------------


def parse_api_chat_request(handler: Any, *, t_api_chat: float, deps: dict[str, Any]) -> ChatRequestContext | None:
    uuid_factory = deps.get("uuid4", uuid4)
    length_raw = handler.headers.get("Content-Length", "0")
    try:
        length = int(length_raw)
    except ValueError:
        deps["emit_chat_verbose_event"](
            "conversation.chat.invalid_request",
            {"error": "content_length_invalid", "content_length": length_raw},
        )
        send_api_chat_error(
            handler,
            t_api_chat=t_api_chat,
            trace_id=None,
            status=HTTPStatus.BAD_REQUEST,
            code="PC_PAYLOAD_CONTENT_LENGTH_INVALID",
            message="Content-Length inválido en request /api/chat.",
            stage="api",
            remediation=(
                "Enviar header Content-Length con valor entero.",
                "Reintentar con payload JSON válido.",
            ),
            diagnostics={"content_length": length_raw},
            deps=deps,
        )
        return None

    raw = handler.rfile.read(length)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        body_preview = raw.decode("utf-8", errors="replace")[:500]
        deps["emit_chat_verbose_event"](
            "conversation.chat.invalid_request",
            {"error": "json_invalid", "body_preview": body_preview},
        )
        send_api_chat_error(
            handler,
            t_api_chat=t_api_chat,
            trace_id=None,
            status=HTTPStatus.BAD_REQUEST,
            code="PC_PAYLOAD_JSON_INVALID",
            message="El body de /api/chat no es JSON válido.",
            stage="api",
            remediation=(
                "Corregir serialización JSON del cliente.",
                "Validar UTF-8 y formato antes de reenviar.",
            ),
            diagnostics={"body_preview": body_preview},
            deps=deps,
        )
        return None
    if not isinstance(payload, dict):
        deps["emit_chat_verbose_event"](
            "conversation.chat.invalid_request",
            {"error": "payload_not_object", "payload_type": type(payload).__name__},
        )
        send_api_chat_error(
            handler,
            t_api_chat=t_api_chat,
            trace_id=None,
            status=HTTPStatus.BAD_REQUEST,
            code="PC_PAYLOAD_NOT_OBJECT",
            message="Payload debe ser un objeto JSON para /api/chat.",
            stage="api",
            remediation=(
                "Enviar objeto JSON con claves válidas del contrato.",
                "Evitar arrays o literales como body raíz.",
            ),
            diagnostics={"payload_type": type(payload).__name__},
            deps=deps,
        )
        return None

    # Probe auth early so we can apply public-mode input caps during validation.
    # The chat controllers re-resolve auth right after parsing — this probe is
    # a cheap JWT verify that doesn't conflict with the later resolution.
    is_public_request = False
    public_visitor_role = deps.get("public_visitor_role")
    if public_visitor_role:
        try:
            probe_ctx = handler._resolve_auth_context(required=False, allow_public=True)
        except Exception:
            probe_ctx = None
        is_public_request = bool(
            probe_ctx is not None and probe_ctx.role == public_visitor_role
        )

    try:
        ok, error = deps["validate_pipeline_c_payload"](payload, is_public=is_public_request)
    except TypeError:
        # Legacy validators without the kwarg — fall back to default limits.
        ok, error = deps["validate_pipeline_c_payload"](payload)
    if not ok:
        deps["emit_chat_verbose_event"](
            "conversation.chat.invalid_request",
            {"error": str(error), "payload": payload},
        )
        send_api_chat_error(
            handler,
            t_api_chat=t_api_chat,
            trace_id=None,
            status=HTTPStatus.BAD_REQUEST,
            code="PC_PAYLOAD_VALIDATION_ERROR",
            message=str(error or "Payload inválido."),
            stage="api",
            remediation=(
                "Alinear request con el contrato `docs/api/pipeline_c_contract.md`.",
                "Corregir los campos inválidos y reintentar.",
            ),
            diagnostics={"validation_error": str(error), "payload_keys": sorted(payload.keys())},
            deps=deps,
        )
        return None

    trace_id = str(payload.get("trace_id", "")).strip() or str(uuid_factory())
    client_turn_id = str(payload.get("client_turn_id", "")).strip() or str(uuid_factory())
    chat_run_id = str(payload.get("chat_run_id", "")).strip() or None
    pipeline_route_override = (
        str(handler.headers.get("X-LIA-Pipeline-Route", "")).strip()
        or str(handler.headers.get("X-LIA-Pipeline-Variant", "")).strip()
        or None
    )
    raw_session_id = str(payload.get("session_id", "")).strip()
    if raw_session_id:
        session_id = raw_session_id
    else:
        generated = uuid_factory()
        seed = getattr(generated, "hex", str(generated).replace("-", ""))
        session_id = f"chat_{str(seed)[:12]}"
    message = str(payload.get("message", "")).strip()
    normalized_pais = deps["normalize_pais"](payload.get("pais")) or "colombia"
    requested_topic_raw = deps["normalize_topic_key"](payload.get("topic"))
    topic_routing = deps["resolve_chat_topic"](
        message=message,
        requested_topic=requested_topic_raw,
        pais=normalized_pais,
        runtime_config_path=deps.get("llm_runtime_config_path"),
        preserve_requested_topic_as_secondary=requested_topic_raw is not None,
    )
    effective_topic = deps["normalize_topic_key"](getattr(topic_routing, "effective_topic", requested_topic_raw)) or requested_topic_raw
    secondary_topics = tuple(getattr(topic_routing, "secondary_topics", ()) or ())
    topic_adjusted = bool(getattr(topic_routing, "topic_adjusted", False))
    topic_notice = str(getattr(topic_routing, "topic_notice", "") or "").strip() or None
    topic_adjustment_reason = str(getattr(topic_routing, "reason", "") or "").strip()
    topic_router_mode = str(getattr(topic_routing, "mode", "") or "").strip() or "fallback"
    try:
        topic_router_confidence = float(getattr(topic_routing, "confidence", 0.0) or 0.0)
    except (TypeError, ValueError):
        topic_router_confidence = 0.0
    payload = dict(payload)
    payload["requested_topic"] = requested_topic_raw
    payload["effective_topic"] = effective_topic
    payload["secondary_topics"] = list(secondary_topics)
    payload["topic_adjusted"] = topic_adjusted
    primary_scope_mode = str(payload.get("primary_scope_mode", "global_overlay")).strip().lower() or "global_overlay"
    if primary_scope_mode not in {"global_overlay", "strict_topic"}:
        primary_scope_mode = "global_overlay"
    response_route = str(payload.get("response_route", "decision")).strip().lower() or "decision"
    if response_route not in {"decision", "theoretical_normative"}:
        response_route = "decision"
    retrieval_profile = str(payload.get("retrieval_profile", "hybrid_rerank")).strip().lower() or "hybrid_rerank"
    response_depth = normalize_response_depth(payload.get("response_depth", DEFAULT_RESPONSE_DEPTH))
    first_response_mode = normalize_first_response_mode(
        payload.get("first_response_mode", DEFAULT_FIRST_RESPONSE_MODE)
    )
    debug_mode = bool(payload.get("debug", False))
    operation_date = payload.get("operation_date")
    company_context_payload = payload.get("company_context")
    deps["emit_chat_verbose_event"](
        "conversation.chat.request",
        {
            "trace_id": trace_id,
            "session_id": session_id,
            "path": "/api/chat",
            "payload": {
                "message": message,
                "pais": normalized_pais,
                "topic": effective_topic,
                "requested_topic": requested_topic_raw,
                "effective_topic": effective_topic,
                "secondary_topics": list(secondary_topics),
                "topic_adjusted": topic_adjusted,
                "topic_notice": topic_notice,
                "topic_adjustment_reason": topic_adjustment_reason,
                "topic_router_confidence": round(topic_router_confidence, 4),
                "topic_router_mode": topic_router_mode,
                "primary_scope_mode": primary_scope_mode,
                "response_route": response_route,
                "retrieval_profile": retrieval_profile,
                "response_depth": response_depth,
                "first_response_mode": first_response_mode,
                "debug": debug_mode,
                "pipeline_route_override": pipeline_route_override,
                "client_turn_id": client_turn_id,
                "chat_run_id": chat_run_id,
                "operation_date": str(operation_date).strip() if operation_date else None,
                "company_context": company_context_payload if isinstance(company_context_payload, dict) else None,
            },
        },
    )
    return {
        "payload": payload,
        "trace_id": trace_id,
        "client_turn_id": client_turn_id,
        "chat_run_id": chat_run_id,
        "session_id": session_id,
        "message": message,
        "normalized_pais": normalized_pais,
        "topic": effective_topic,
        "requested_topic": requested_topic_raw,
        "effective_topic": effective_topic,
        "secondary_topics": secondary_topics,
        "topic_adjusted": topic_adjusted,
        "topic_notice": topic_notice,
        "topic_adjustment_reason": topic_adjustment_reason,
        "topic_router_confidence": topic_router_confidence,
        "topic_router_mode": topic_router_mode,
        "primary_scope_mode": primary_scope_mode,
        "response_route": response_route,
        "retrieval_profile": retrieval_profile,
        "response_depth": response_depth,
        "first_response_mode": first_response_mode,
        "pipeline_message": message,
        "pipeline_response_route": response_route,
        "pipeline_route_override": pipeline_route_override,
        "debug_mode": debug_mode,
        "operation_date": operation_date,
        "company_context_payload": company_context_payload,
        "clarification_state": None,
        "clear_clarification_on_success": False,
    }


# Clarification flow moved to `ui_chat_clarification.py` during
# granularize-v2 round 10. Re-imported so eager `from .ui_chat_payload
# import apply_api_chat_clarification` in ui_chat_controller.py and
# ui_server.py keeps working.
from .ui_chat_clarification import (  # noqa: F401  — re-exported
    _build_semantic_clarification_payload,
    apply_api_chat_clarification,
)

# ---------------------------------------------------------------------------
# Success payload builder
# ---------------------------------------------------------------------------


def build_api_chat_success_payload(
    *,
    request_context: ChatRequestContext,
    response: Any,
    t_api_chat: float,
    deps: dict[str, Any],
) -> dict[str, Any]:
    session_id = str(request_context["session_id"])
    message = str(request_context["message"])
    topic = _optional_text(request_context.get("effective_topic") or request_context.get("topic"))
    requested_topic = _optional_text(request_context.get("requested_topic"))
    effective_topic = _optional_text(request_context.get("effective_topic") or request_context.get("topic"))
    secondary_topics = [str(item) for item in list(request_context.get("secondary_topics") or ()) if str(item).strip()]
    topic_adjusted = bool(request_context.get("topic_adjusted", False))
    topic_notice = str(request_context.get("topic_notice") or "").strip() or None
    topic_adjustment_reason = str(request_context.get("topic_adjustment_reason") or "").strip() or None
    topic_router_mode = str(request_context.get("topic_router_mode") or "").strip() or "fallback"
    try:
        topic_router_confidence = float(request_context.get("topic_router_confidence") or 0.0)
    except (TypeError, ValueError):
        topic_router_confidence = 0.0
    normalized_pais = str(request_context["normalized_pais"])
    primary_scope_mode = str(request_context["primary_scope_mode"])
    debug_mode = bool(request_context["debug_mode"])
    trace_id = str(request_context["trace_id"])
    clarification_session_id = str(request_context.get("clarification_session_id") or session_id)
    auth_context = request_context.get("auth_context")
    pipeline_variant = str(
        getattr(response, "pipeline_variant", None)
        or request_context.get("pipeline_variant")
        or "pipeline_c"
    ).strip() or "pipeline_c"
    pipeline_route = str(
        getattr(response, "pipeline_route", None)
        or request_context.get("requested_pipeline_variant")
        or pipeline_variant
    ).strip() or pipeline_variant
    shadow_pipeline_variant = str(
        getattr(response, "shadow_pipeline_variant", None)
        or request_context.get("shadow_pipeline_variant")
        or ""
    ).strip() or None

    if bool(request_context["clear_clarification_on_success"]):
        deps["clear_clarification_session_state"](
            session_id=clarification_session_id,
            path=deps["clarification_sessions_path"],
        )

    response_payload = response.to_dict()
    raw_answer_markdown = str(response_payload.get("answer_markdown") or response.answer_markdown or "").strip()
    raw_answer_concise = str(response_payload.get("answer_concise") or response.answer_concise or "").strip()
    response_payload["answer_markdown"] = raw_answer_markdown
    response_payload["answer_concise"] = raw_answer_concise
    response_payload["topic"] = effective_topic
    response_payload["pais"] = normalized_pais
    response_payload["requested_topic"] = requested_topic
    response_payload["effective_topic"] = effective_topic
    response_payload["secondary_topics"] = list(secondary_topics)
    response_payload["topic_adjusted"] = topic_adjusted
    response_payload["topic_notice"] = topic_notice
    response_payload["topic_adjustment_reason"] = topic_adjustment_reason
    response_payload["pipeline_variant"] = pipeline_variant
    response_payload["pipeline_route"] = pipeline_route
    response_payload["shadow_pipeline_variant"] = shadow_pipeline_variant
    payload_diagnostics = (
        dict(response_payload.get("diagnostics") or {})
        if isinstance(response_payload.get("diagnostics"), dict)
        else (dict(response.diagnostics or {}) if isinstance(response.diagnostics, dict) else None)
    )
    citations_payload = response_payload.get("citations")
    normalized_citations_payload = [
        dict(item) for item in citations_payload if isinstance(item, dict)
    ] if isinstance(citations_payload, list) else []
    response_payload["citations"] = deps["merge_citation_payloads"](
        deps["enrich_citation_payloads_with_usage_context"](
            citations_payload=normalized_citations_payload,
            answer_text=str(response_payload.get("answer_markdown") or response_payload.get("answer_concise") or ""),
            diagnostics=payload_diagnostics,
        ),
        [],
    )
    answer_text = str(response_payload.get("answer_concise") or response_payload.get("answer_markdown") or "").strip()
    answer_markdown_text = str(response_payload.get("answer_markdown") or answer_text).strip()
    answer_visible_text = deps["strip_inline_evidence_annotations"](answer_markdown_text).strip() or answer_text
    response_payload["support_citations"] = []
    mention_resolution_metrics: dict[str, Any] = {
        "mentions_detected": 0,
        "mentions_unique": 0,
        "mentions_already_covered": 0,
        "mentions_resolved_to_doc": 0,
        "mentions_unresolved": 0,
        "resolved_reference_keys": [],
        "unresolved_reference_keys": [],
    }
    combined_reference_text = "\n".join(part for part in (message, answer_visible_text) if str(part).strip())
    _t_normative_start = time.monotonic()
    support_citations, mention_resolution_metrics = deps["build_normative_helper_citations"](
        citations_payload=[dict(item) for item in response_payload.get("citations") if isinstance(item, dict)],
        reference_text=combined_reference_text,
        index_file=deps["index_file_path"],
        max_resolved=8,
    )
    _t_normative_ms = (time.monotonic() - _t_normative_start) * 1000
    mention_resolution_metrics["normative_scaffolding_ms"] = round(_t_normative_ms, 1)
    response_payload["support_citations"] = support_citations
    citation_gaps_capture: dict[str, Any] = {
        "user": {"captured_count": 0, "captured_by_type": {}},
        "assistant": {"captured_count": 0, "captured_by_type": {}},
    }

    def _deferred_citation_gaps() -> None:
        for origin, text_value in (("user", message), ("assistant", answer_visible_text)):
            if not str(text_value or "").strip():
                continue
            try:
                capture_result = deps["register_citation_gaps"](
                    text=str(text_value),
                    origin=origin,
                    trace_id=trace_id,
                    session_id=session_id,
                    topic=topic,
                    pais=normalized_pais,
                    index_file=deps["index_file_path"],
                    path=deps["citation_gap_registry_path"],
                ) or {}
                deps["emit_event"](
                    "citation_gap_registry.updated",
                    {
                        "trace_id": trace_id,
                        "session_id": session_id,
                        "origin": origin,
                        "captured_count": int(capture_result.get("captured_count") or 0),
                        "captured_by_type": dict(capture_result.get("captured_by_type") or {}),
                    },
                )
            except Exception as exc:  # noqa: BLE001
                deps["emit_event"](
                    "citation_gap_registry.error",
                    {
                        "trace_id": trace_id,
                        "session_id": session_id,
                        "origin": origin,
                        "error": str(exc),
                    },
                )

    threading.Thread(target=_deferred_citation_gaps, daemon=True).start()
    # Force diagnostics for eval robots regardless of debug_mode flag
    _include_diagnostics = debug_mode or (auth_context is not None and getattr(auth_context, "is_robot", False))
    orchestrator_diagnostics = (
        dict(response_payload.get("diagnostics") or {})
        if isinstance(response_payload.get("diagnostics"), dict)
        else {}
    )
    if _include_diagnostics:
        diagnostics_payload = orchestrator_diagnostics
        diagnostics_payload["citation_gaps_captured"] = citation_gaps_capture
        diagnostics_payload["mention_resolution"] = dict(mention_resolution_metrics)
        diagnostics_payload["primary_scope_mode"] = primary_scope_mode
        diagnostics_payload["topic_routing"] = {
            "requested_topic": requested_topic,
            "effective_topic": effective_topic,
            "secondary_topics": list(secondary_topics),
            "topic_adjusted": topic_adjusted,
            "topic_notice": topic_notice,
            "reason": topic_adjustment_reason,
            "confidence": round(topic_router_confidence, 4),
            "mode": topic_router_mode,
        }
        diagnostics_payload["pipeline"] = {
            "route": pipeline_route,
            "variant": pipeline_variant,
            "shadow_variant": shadow_pipeline_variant,
            "source": str(request_context.get("pipeline_route_source") or "unknown"),
        }
        response_payload["diagnostics"] = diagnostics_payload
    else:
        response_payload["diagnostics"] = filter_diagnostics_for_public_response(
            orchestrator_diagnostics
        )
    turn_token_usage = deps["normalize_token_usage"](
        deps["estimate_token_usage_from_text"](
            input_text=message,
            output_text=answer_text,
        )
    )
    payload_token_usage = response_payload.get("token_usage")
    if not isinstance(payload_token_usage, dict):
        payload_token_usage = {"turn": dict(turn_token_usage), "llm": deps["normalize_token_usage"](None)}
    else:
        payload_token_usage = {
            "turn": deps["normalize_token_usage"](payload_token_usage.get("turn")),
            "llm": deps["normalize_token_usage"](payload_token_usage.get("llm")),
        }
    response_payload["token_usage"] = payload_token_usage

    payload_llm_runtime = response_payload.get("llm_runtime")
    if not isinstance(payload_llm_runtime, dict):
        payload_llm_runtime = {}
    selected_provider = str(payload_llm_runtime.get("selected_provider") or "").strip() or None
    selected_type = str(payload_llm_runtime.get("selected_type") or "").strip() or None
    selected_transport = str(payload_llm_runtime.get("selected_transport") or "").strip() or None
    adapter_class = str(payload_llm_runtime.get("adapter_class") or "").strip() or None
    selected_model = str(payload_llm_runtime.get("model") or "").strip() or None
    runtime_config_path = str(payload_llm_runtime.get("runtime_config_path") or "").strip() or None
    response_payload["llm_runtime"] = {
        "selected_provider": selected_provider,
        "selected_type": selected_type,
        "selected_transport": selected_transport,
        "adapter_class": adapter_class,
        "model": selected_model,
        "runtime_config_path": runtime_config_path,
        "attempts": list(payload_llm_runtime.get("attempts") or []),
    }

    payload_timing = response_payload.get("timing")
    if not isinstance(payload_timing, dict):
        payload_timing = {}
    response_payload["timing"] = payload_timing

    auth_context_cls = deps.get("auth_context_cls")
    response_payload["actor_context"] = (
        auth_context.to_public_dict()
        if auth_context_cls is not None and isinstance(auth_context, auth_context_cls)
        else {
            "tenant_id": str(request_context.get("tenant_id") or "public"),
            "user_id": str(request_context.get("user_id") or "") or None,
            "active_company_id": str(request_context.get("company_id") or "") or None,
            "integration_id": str(request_context.get("integration_id") or "") or None,
            "claims_source": "anonymous",
        }
    )
    response_payload["billing_context"] = {
        "tenant_id": str(request_context.get("tenant_id") or "public"),
        "user_id": str(request_context.get("user_id") or "") or None,
        "company_id": str(request_context.get("company_id") or "") or None,
        "integration_id": str(request_context.get("integration_id") or "") or None,
        "endpoint": str(request_context.get("endpoint") or "/api/chat"),
        "billable": str(((payload_token_usage.get("llm") or {}).get("source") or "")).strip() == "provider",
    }

    def _project_usage_total(current: dict[str, Any] | None, delta: dict[str, Any] | None) -> dict[str, int]:
        current_payload = dict(current or {})
        delta_payload = dict(delta or {})
        return {
            "input_tokens": int(current_payload.get("input_tokens") or 0) + int(delta_payload.get("input_tokens") or 0),
            "output_tokens": int(current_payload.get("output_tokens") or 0) + int(delta_payload.get("output_tokens") or 0),
            "total_tokens": int(current_payload.get("total_tokens") or 0) + int(delta_payload.get("total_tokens") or 0),
        }

    session_metrics: dict[str, Any]
    get_session_metrics = deps.get("get_chat_session_metrics")
    if callable(get_session_metrics):
        try:
            current_session_metrics = get_session_metrics(
                session_id=session_id,
                path=deps["chat_session_metrics_path"],
            )
        except Exception:  # noqa: BLE001
            current_session_metrics = None
        if isinstance(current_session_metrics, dict):
            session_metrics = {
                "session_id": session_id,
                "turn_count": int(current_session_metrics.get("turn_count") or 0) + 1,
                "token_usage_total": _project_usage_total(
                    dict(current_session_metrics.get("token_usage_total") or {}),
                    dict(payload_token_usage.get("turn") or {}),
                ),
                "llm_token_usage_total": _project_usage_total(
                    dict(current_session_metrics.get("llm_token_usage_total") or {}),
                    dict(payload_token_usage.get("llm") or {}),
                ),
                "last_trace_id": str(response.trace_id or trace_id) or None,
                "last_run_id": str(response_payload.get("run_id", "")).strip() or None,
                "updated_at": current_session_metrics.get("updated_at"),
                "pending": True,
            }
        else:
            session_metrics = _default_session_payload(
                session_id=session_id,
                trace_id=str(response.trace_id or trace_id),
                run_id=str(response_payload.get("run_id", "")).strip() or None,
            )
            session_metrics["token_usage_total"] = dict(payload_token_usage.get("turn") or {})
            session_metrics["llm_token_usage_total"] = dict(payload_token_usage.get("llm") or {})
            session_metrics["turn_count"] = 1
    else:
        session_metrics = _default_session_payload(
            session_id=session_id,
            trace_id=str(response.trace_id or trace_id),
            run_id=str(response_payload.get("run_id", "")).strip() or None,
        )
        session_metrics["token_usage_total"] = dict(payload_token_usage.get("turn") or {})
        session_metrics["llm_token_usage_total"] = dict(payload_token_usage.get("llm") or {})
        session_metrics["turn_count"] = 1

    response_payload["session"] = session_metrics
    response_payload["session_id"] = str(session_metrics.get("session_id") or session_id)
    response_payload["chat_run_id"] = str(request_context.get("chat_run_id") or "")

    latency_ms = round((time.monotonic() - t_api_chat) * 1000, 2)
    response_payload["metrics"] = {
        "latency_ms": latency_ms,
        "llm_runtime": dict(response_payload.get("llm_runtime") or {}),
        "token_usage": dict(response_payload.get("token_usage") or {}),
        "timing": dict(response_payload.get("timing") or {}),
        "answer_mode": str(response_payload.get("answer_mode") or ""),
        "compose_quality": response_payload.get("compose_quality"),
        "fallback_reason": response_payload.get("fallback_reason"),
        "pipeline_variant": pipeline_variant,
        "pipeline_route": pipeline_route,
        "shadow_pipeline_variant": shadow_pipeline_variant,
        "conversation": dict(session_metrics),
        "mention_resolution": dict(mention_resolution_metrics),
        "primary_scope_mode": primary_scope_mode,
        "primary_overlay": dict(((response_payload.get("diagnostics") or {}).get("retrieval") or {}).get("primary_overlay") or {}),
        "topic_routing": {
            "requested_topic": requested_topic,
            "effective_topic": effective_topic,
            "secondary_topics": list(secondary_topics),
            "topic_adjusted": topic_adjusted,
        },
    }
    try:
        persistence_job_id = _schedule_success_persistence(
            request_context=request_context,
            response_payload=response_payload,
            answer_visible_text=answer_visible_text,
            deps=deps,
        )
        if str(persistence_job_id or "").strip():
            response_payload["persistence_job_id"] = str(persistence_job_id)
    except Exception as exc:  # noqa: BLE001
        deps["emit_event"](
            "platform.persistence.warning",
            {"trace_id": trace_id, "session_id": session_id, "error": str(exc)},
        )

    deps["emit_reasoning_event"](
        trace_id=response.trace_id,
        phase="api",
        category="api_reply",
        step="ui_server.api_chat.pipeline_c.reply",
        message="Request /api/chat completado en la ruta de respuesta activa.",
        dependency="/api/chat",
        duration_ms=latency_ms,
        token_usage=dict(payload_token_usage.get("turn") or {}),
        details={
            "confidence_mode": response.confidence_mode,
            "confidence_score": round(float(response.confidence_score), 4),
            "requested_topic": requested_topic,
            "effective_topic": effective_topic,
            "secondary_topics": list(secondary_topics),
            "topic_adjusted": topic_adjusted,
            "answer_mode": str(response_payload.get("answer_mode") or ""),
            "compose_quality": response_payload.get("compose_quality"),
            "fallback_reason": response_payload.get("fallback_reason"),
            "pipeline_variant": pipeline_variant,
            "pipeline_route": pipeline_route,
            "shadow_pipeline_variant": shadow_pipeline_variant,
            "llm_runtime": dict(response_payload.get("llm_runtime") or {}),
            "timing": dict(response_payload.get("timing") or {}),
        },
    )
    deps["emit_chat_verbose_event"](
        "conversation.chat.reply",
        {
            "trace_id": response.trace_id,
            "chat_run_id": str(request_context.get("chat_run_id") or ""),
            "session_id": str(session_metrics.get("session_id") or session_id),
            "status": "ok",
            "http_status": int(HTTPStatus.OK),
            "duration_ms": latency_ms,
            "llm_runtime": dict(response_payload.get("llm_runtime") or {}),
            "token_usage": dict(response_payload.get("token_usage") or {}),
            "timing": dict(response_payload.get("timing") or {}),
            "conversation": dict(session_metrics),
            "confidence": dict(response_payload.get("confidence") or {}),
            "requested_topic": requested_topic,
            "effective_topic": effective_topic,
            "secondary_topics": list(secondary_topics),
            "topic_adjusted": topic_adjusted,
            "answer_mode": str(response_payload.get("answer_mode") or ""),
            "compose_quality": response_payload.get("compose_quality"),
            "fallback_reason": response_payload.get("fallback_reason"),
            "pipeline_variant": pipeline_variant,
            "pipeline_route": pipeline_route,
            "shadow_pipeline_variant": shadow_pipeline_variant,
            "run_id": response_payload.get("run_id"),
            "answer_preview": answer_text[:800],
            "citations_count": len(response_payload.get("citations") or []),
        },
    )
    return response_payload


# ---------------------------------------------------------------------------
# Response finalization
# ---------------------------------------------------------------------------


def finalize_api_chat_response(
    handler: Any,
    *,
    request_context: ChatRequestContext,
    response: Any,
    t_api_chat: float,
    deps: dict[str, Any],
) -> None:
    response_payload = build_api_chat_success_payload(
        request_context=request_context,
        response=response,
        t_api_chat=t_api_chat,
        deps=deps,
    )
    chat_run_id = str(request_context.get("chat_run_id") or "")
    deps["chat_run_coordinator"].mark_final_payload_ready(chat_run_id, base_dir=deps["chat_runs_path"])
    deps["chat_run_coordinator"].complete(chat_run_id, response_payload, base_dir=deps["chat_runs_path"])
    handler._send_json(HTTPStatus.OK, response_payload)
    deps["chat_run_coordinator"].mark_response_sent(chat_run_id, base_dir=deps["chat_runs_path"])


# ---------------------------------------------------------------------------
# Runtime orchestration settings loader
# ---------------------------------------------------------------------------


def _load_runtime_orchestration_settings() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    from .instrumentation import emit_event
    from .orchestration_settings import (
        OrchestrationSettingsInvalidError,
        load_orchestration_settings,
    )

    try:
        settings = load_orchestration_settings(path=_ui().ORCHESTRATION_SETTINGS_PATH)
    except OrchestrationSettingsInvalidError as exc:
        from .supabase_client import get_storage_backend

        storage_backend = str(get_storage_backend() or "").strip().lower() or "supabase"
        emit_event(
            "orchestration_settings_invalid",
            {
                "storage_backend": storage_backend,
                "location": (
                    "supabase://orchestration_settings?scope=global_admin"
                    if storage_backend == "supabase"
                    else str(_ui().ORCHESTRATION_SETTINGS_PATH)
                ),
                "error": str(exc),
            },
        )
        raise
    effective_orchestration = dict(settings.get("effective_orchestration") or {})
    effective_limits = dict(settings.get("effective_limits") or {})
    return settings, effective_orchestration, effective_limits
