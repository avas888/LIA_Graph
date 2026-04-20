"""API-chat clarification flow.

Extracted from `ui_chat_payload.py` during granularize-v2 round 10 to
graduate the host below 1000 LOC. The cluster has a self-contained
identity: **handle the `/api/chat` clarification loop** — intercept the
incoming message, check if the session is already in a guided
clarification state, and either dispatch a follow-up question (ask /
limit-reached) or let the request fall through to the pipeline.

Two entry points:

  * ``apply_api_chat_clarification`` — the gate called at the top of the
    chat controller. Returns ``True`` when a clarification response was
    already sent (the controller should early-return); ``False`` when
    the request should continue to the pipeline.
  * ``_build_semantic_clarification_payload`` — invoked downstream by
    the chat controller when the pipeline itself raises a
    ``PipelineSemanticError``. Converts the error into a clarification
    payload using the same interaction/persistence scaffolding.

All collaborators flow through the ``deps`` dict (clarification state
storage, LLM deciders, interaction payload builders, chat-run
coordinator). Host re-imports both names so existing consumers
(`ui_chat_controller`, `ui_server`) keep working unchanged.
"""

from __future__ import annotations

import time
from http import HTTPStatus
from typing import Any

from .ui_chat_context import ChatRequestContext, _optional_text
from .ui_chat_persistence import persist_assistant_turn, persist_user_turn


def apply_api_chat_clarification(
    handler: Any,
    *,
    request_context: ChatRequestContext,
    t_api_chat: float,
    deps: dict[str, Any],
) -> bool:
    trace_id = str(request_context["trace_id"])
    chat_run_id = str(request_context.get("chat_run_id") or "")
    session_id = str(request_context["session_id"])
    clarification_session_id = str(request_context.get("clarification_session_id") or session_id)
    message = str(request_context["message"])
    response_route = str(request_context["response_route"])

    try:
        clarification_state = deps["get_clarification_session_state"](
            session_id=clarification_session_id,
            path=deps["clarification_sessions_path"],
        )
    except ValueError:
        clarification_state = None

    request_context["clarification_state"] = clarification_state
    request_context["pipeline_message"] = message
    request_context["pipeline_response_route"] = response_route
    request_context["clear_clarification_on_success"] = False

    if response_route != "decision" or not isinstance(clarification_state, dict):
        return False
    if not deps["should_intercept_clarification_state"](clarification_state, user_message=message):
        return False

    updated_state, directive = deps["advance_clarification_state"](
        clarification_state,
        user_message=message,
        llm_decider=lambda current_state, current_user_message: deps["llm_dynamic_clarification_decider"](
            state=current_state,
            user_message=current_user_message,
            trace_id=trace_id,
        ),
    )
    directive_type = str(directive.get("type") or "").strip().lower()
    if directive_type == "pass_through":
        request_context["clarification_state"] = updated_state
        return False

    if directive_type == "limit_reached":
        deps["clear_clarification_session_state"](
            session_id=clarification_session_id,
            path=deps["clarification_sessions_path"],
        )
        error_code = str(updated_state.get("active_error_code") or "PC_COMPARATIVE_DATA_MISSING")
        public_error = deps["build_public_api_error"](
            code=error_code,
            message="Se requiere informacion adicional para continuar.",
            stage="clarification",
            http_status=int(HTTPStatus.UNPROCESSABLE_ENTITY),
            trace_id=trace_id,
            run_id=None,
            remediation=(),
            llm_runtime={},
            timing={"pipeline_total_ms": round((time.monotonic() - t_api_chat) * 1000, 2), "stages_ms": {}},
            diagnostics={"endpoint": "/api/chat", "clarification": dict(updated_state)},
        )
        question = str(directive.get("question") or "").strip()
        interaction = deps["build_clarification_interaction_payload"](
            state=updated_state,
            question=question,
        )
        payload_out = deps["build_clarification_error_payload"](
            public_error=public_error,
            user_message=deps["build_user_message_for_question"](
                question=question,
                include_intro=False,
                invalid_input=False,
            ),
            interaction=interaction,
            session_id=session_id,
        )
        payload_out["chat_run_id"] = chat_run_id
        persist_user_turn(request_context=request_context, deps=deps)
        persist_assistant_turn(
            request_context=request_context,
            content=str(payload_out.get("user_message") or "Se requiere informacion adicional para continuar."),
            trace_id=trace_id,
            deps=deps,
        )
        handler._send_json(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            payload_out,
            extra_headers={"X-LIA-Error-Code": error_code},
        )
        deps["chat_run_coordinator"].fail(chat_run_id, payload_out, base_dir=deps["chat_runs_path"])
        deps["chat_run_coordinator"].mark_response_sent(chat_run_id, base_dir=deps["chat_runs_path"])
        return True

    if directive_type == "ask":
        clarification_state = deps["upsert_clarification_session_state"](
            session_id=clarification_session_id,
            state=updated_state,
            path=deps["clarification_sessions_path"],
            ttl_hours=24,
        )
        request_context["clarification_state"] = clarification_state
        error_code = str(updated_state.get("active_error_code") or "PC_COMPARATIVE_DATA_MISSING")
        question = str(directive.get("question") or "").strip()
        include_intro = int(updated_state.get("turn_count") or 0) <= 1
        invalid_input = bool(directive.get("invalid_input"))
        public_error = deps["build_public_api_error"](
            code=error_code,
            message="Se requiere informacion adicional para continuar.",
            stage="clarification",
            http_status=int(HTTPStatus.UNPROCESSABLE_ENTITY),
            trace_id=trace_id,
            run_id=None,
            remediation=(),
            llm_runtime={},
            timing={"pipeline_total_ms": round((time.monotonic() - t_api_chat) * 1000, 2), "stages_ms": {}},
            diagnostics={"endpoint": "/api/chat", "clarification": dict(clarification_state)},
        )
        requirements: list[str] = []
        if include_intro:
            requirements = deps["resolve_guided_clarification_requirements"](
                state=clarification_state,
                error_code=error_code,
                trace_id=trace_id,
            )
        interaction = deps["build_clarification_interaction_payload"](
            state=clarification_state,
            question=question,
            requirements=requirements,
        )
        user_message = deps["build_user_message_for_question"](
            question=question,
            include_intro=include_intro,
            invalid_input=invalid_input,
            requirements=requirements,
        )
        payload_out = deps["build_clarification_error_payload"](
            public_error=public_error,
            user_message=user_message,
            interaction=interaction,
            session_id=session_id,
        )
        payload_out["chat_run_id"] = chat_run_id
        persist_user_turn(request_context=request_context, deps=deps)
        persist_assistant_turn(
            request_context=request_context,
            content=user_message,
            trace_id=trace_id,
            deps=deps,
        )
        handler._send_json(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            payload_out,
            extra_headers={"X-LIA-Error-Code": error_code},
        )
        deps["chat_run_coordinator"].fail(chat_run_id, payload_out, base_dir=deps["chat_runs_path"])
        deps["chat_run_coordinator"].mark_response_sent(chat_run_id, base_dir=deps["chat_runs_path"])
        return True

    if directive_type == "run_pipeline":
        clarification_state = deps["upsert_clarification_session_state"](
            session_id=clarification_session_id,
            state=updated_state,
            path=deps["clarification_sessions_path"],
            ttl_hours=24,
        )
        request_context["clarification_state"] = clarification_state
        pipeline_message = str(directive.get("message") or message).strip() or message
        pipeline_response_route = str(directive.get("route") or "decision").strip().lower() or "decision"
        request_context["pipeline_message"] = pipeline_message
        request_context["pipeline_response_route"] = pipeline_response_route
        request_context["clear_clarification_on_success"] = pipeline_response_route == "decision"
        return False

    request_context["clarification_state"] = updated_state
    return False


def _build_semantic_clarification_payload(
    *,
    exc: Any,
    request_context: ChatRequestContext,
    message: str,
    session_id: str,
    clarification_session_id: str,
    clarification_state: Any,
    trace_id: str,
    endpoint: str,
    duration_ms: float,
    deps: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    public_error = deps["as_public_error"](
        exc,
        trace_id=trace_id,
        run_id=str((exc.details or {}).get("run_id") or "").strip() or None,
        llm_runtime=dict((exc.details or {}).get("llm_runtime") or {}),
        timing={
            "pipeline_total_ms": duration_ms,
            "stages_ms": dict((exc.details or {}).get("stages_ms") or {}),
        },
        diagnostics={
            "endpoint": endpoint,
            "error_details": dict(exc.details or {}),
            "request": {
                "topic": _optional_text(request_context.get("effective_topic") or request_context.get("topic")),
                "pais": str(request_context["normalized_pais"]),
                "primary_scope_mode": str(request_context["primary_scope_mode"]),
                "response_route": str(request_context["pipeline_response_route"]),
            },
        },
    )
    refreshed_state = deps["refresh_state_from_semantic_error"](
        state=clarification_state if isinstance(clarification_state, dict) else None,
        session_id=session_id,
        error_code=exc.code,
        original_question=message,
        error_details=dict(exc.details or {}),
    )
    route = str(refreshed_state.get("route") or "decision").strip()
    include_intro = int(refreshed_state.get("turn_count") or 0) == 0
    invalid_input = False
    question = ""
    if route == "decision" and str(exc.code).strip().upper() == "PC_COMPARATIVE_DATA_MISSING":
        pending_fields = list(refreshed_state.get("pending_fields") or [])
        next_field = str(pending_fields[0]).strip() if pending_fields else ""
        question = deps["comparative_field_questions"].get(next_field) or (
            "¿Puedes compartir los datos exactos que faltan para cerrar el comparativo?"
        )
    else:
        question = str(refreshed_state.get("last_question") or "").strip()
        if not question:
            llm_hint = deps["llm_dynamic_clarification_decider"](
                state=refreshed_state,
                user_message=message,
                trace_id=trace_id,
            )
            question = str(llm_hint.get("next_question") or "").strip()
        if not question:
            question = "¿Que dato puntual necesitas confirmar para que la respuesta sea util y verificable?"
    refreshed_state["status"] = "active"
    refreshed_state["last_question"] = question
    refreshed_state = deps["upsert_clarification_session_state"](
        session_id=clarification_session_id,
        state=refreshed_state,
        path=deps["clarification_sessions_path"],
        ttl_hours=24,
    )
    requirements: list[str] = []
    if include_intro:
        requirements = deps["resolve_guided_clarification_requirements"](
            state=refreshed_state,
            error_code=str(exc.code),
            trace_id=trace_id,
        )
    interaction = deps["build_clarification_interaction_payload"](
        state=refreshed_state,
        question=question,
        requirements=requirements,
    )
    user_message = deps["build_user_message_for_question"](
        question=question,
        include_intro=include_intro,
        invalid_input=invalid_input,
        requirements=requirements,
    )
    payload_out = deps["build_clarification_error_payload"](
        public_error=public_error,
        user_message=user_message,
        interaction=interaction,
        session_id=session_id,
    )
    persist_user_turn(request_context=request_context, deps=deps)
    persist_assistant_turn(
        request_context=request_context,
        content=user_message,
        trace_id=trace_id,
        deps=deps,
    )
    return payload_out, public_error, interaction
