from __future__ import annotations

import threading
import time
from http import HTTPStatus
from typing import Any

from .pipeline_c.streaming import markdowns_equivalent
from .ui_chat_context import (
    _ChatStreamSink,
    _optional_text,
)
from .ui_chat_payload import (
    _build_semantic_clarification_payload,
    _send_existing_chat_run_response,
    apply_api_chat_clarification,
    build_api_chat_success_payload,
    finalize_api_chat_response,
    parse_api_chat_request,
)
from .ui_chat_persistence import (
    _build_pipeline_request,
    _ensure_conversation_session_loaded,
    ensure_chat_run_context,
    initialize_chat_request_context,
)


def handle_api_chat_post(handler: Any, *, deps: dict[str, Any]) -> None:
    t_api_chat = time.monotonic()
    request_context = parse_api_chat_request(handler, t_api_chat=t_api_chat, deps=deps)
    if request_context is None:
        return
    try:
        auth_context = handler._resolve_auth_context(required=False, allow_public=True)
    except deps["platform_auth_error_cls"] as exc:
        handler._send_auth_error(exc)
        return
    request_context["is_public_visitor"] = bool(
        auth_context is not None
        and auth_context.role == deps.get("public_visitor_role", "public_visitor")
    )
    initialize_chat_request_context(
        request_context=request_context,
        auth_context=auth_context,
        channel="chat",
        deps=deps,
    )
    chat_run_state = ensure_chat_run_context(request_context=request_context, deps=deps)
    existing_run = chat_run_state["record"]
    chat_run_id = str(existing_run.chat_run_id)
    if not bool(chat_run_state["is_owner"]):
        if existing_run.status == "completed" and isinstance(existing_run.response_payload, dict) and existing_run.response_payload:
            _send_existing_chat_run_response(handler, dict(existing_run.response_payload))
            deps["chat_run_coordinator"].mark_response_sent(chat_run_id, base_dir=deps["chat_runs_path"])
            return
        if existing_run.status == "failed" and isinstance(existing_run.error_payload, dict) and existing_run.error_payload:
            _send_existing_chat_run_response(handler, dict(existing_run.error_payload))
            deps["chat_run_coordinator"].mark_response_sent(chat_run_id, base_dir=deps["chat_runs_path"])
            return
        status, payload = deps["chat_run_coordinator"].wait_for_terminal(
            chat_run_id=chat_run_id,
            timeout_seconds=45.0,
            base_dir=deps["chat_runs_path"],
        )
        if status in {"completed", "failed"} and isinstance(payload, dict):
            _send_existing_chat_run_response(handler, payload)
            deps["chat_run_coordinator"].mark_response_sent(chat_run_id, base_dir=deps["chat_runs_path"])
            return
        handler._send_json(
            HTTPStatus.ACCEPTED,
            {"ok": False, "status": "in_progress", "chat_run_id": chat_run_id, "session_id": str(request_context["session_id"])},
        )
        return
    if apply_api_chat_clarification(handler, request_context=request_context, t_api_chat=t_api_chat, deps=deps):
        return

    trace_id = str(request_context["trace_id"])
    session_id = str(request_context["session_id"])
    clarification_session_id = str(request_context.get("clarification_session_id") or session_id)
    message = str(request_context["message"])
    normalized_pais = str(request_context["normalized_pais"])
    topic = _optional_text(request_context.get("effective_topic") or request_context.get("topic"))
    requested_topic = _optional_text(request_context.get("requested_topic"))
    primary_scope_mode = str(request_context["primary_scope_mode"])
    pipeline_response_route = str(request_context["pipeline_response_route"])
    clarification_state = request_context.get("clarification_state")

    deps["emit_reasoning_event"](
        trace_id=trace_id,
        phase="api",
        category="api_call",
        step="ui_server.api_chat.pipeline_c.inbound",
        message="Request /api/chat recibido en Pipeline C.",
        dependency="/api/chat",
        token_usage=deps["estimate_token_usage_from_text"](input_text=message),
        details={
            "topic": topic,
            "requested_topic": requested_topic,
            "pais": normalized_pais,
            "primary_scope_mode": primary_scope_mode,
            "response_route": pipeline_response_route,
            "debug": bool(request_context["debug_mode"]),
        },
    )
    deps["chat_run_coordinator"].mark_pipeline_started(chat_run_id, base_dir=deps["chat_runs_path"])

    try:
        response = deps["run_pipeline_c"](
            _build_pipeline_request(request_context, deps),
            index_file=deps["index_file_path"],
            policy_path=deps["credibility_policy_path"],
            runtime_config_path=deps["llm_runtime_config_path"],
        )
        deps["chat_run_coordinator"].set_pipeline_run_id(
            chat_run_id,
            str(getattr(response, "run_id", "") or ""),
            base_dir=deps["chat_runs_path"],
        )
        deps["chat_run_coordinator"].mark_pipeline_completed(chat_run_id, base_dir=deps["chat_runs_path"])
    except deps["pipeline_c_strict_error_cls"] as exc:
        duration_ms = round((time.monotonic() - t_api_chat) * 1000, 2)
        llm_runtime = dict((exc.details or {}).get("llm_runtime") or {})
        timing = {
            "pipeline_total_ms": duration_ms,
            "stages_ms": dict((exc.details or {}).get("stages_ms") or {}),
        }
        diagnostics = {
            "endpoint": "/api/chat",
            "error_details": dict(exc.details or {}),
            "request": {
                "topic": topic,
                "requested_topic": requested_topic,
                "pais": normalized_pais,
                "primary_scope_mode": primary_scope_mode,
                "response_route": pipeline_response_route,
            },
        }
        public_error = deps["as_public_error"](
            exc,
            trace_id=trace_id,
            run_id=str((exc.details or {}).get("run_id") or "").strip() or None,
            llm_runtime=llm_runtime,
            timing=timing,
            diagnostics=diagnostics,
        )
        if isinstance(public_error, dict):
            public_error["chat_run_id"] = chat_run_id
        if deps["is_semantic_422_error"](exc.code):
            payload_out, public_error, interaction = _build_semantic_clarification_payload(
                exc=exc,
                request_context=request_context,
                message=message,
                session_id=session_id,
                clarification_session_id=clarification_session_id,
                clarification_state=clarification_state,
                trace_id=trace_id,
                endpoint="/api/chat",
                duration_ms=duration_ms,
                deps=deps,
            )
            payload_out["chat_run_id"] = chat_run_id
            deps["emit_reasoning_event"](
                trace_id=trace_id,
                phase="api",
                category="api_reply",
                step="ui_server.api_chat.pipeline_c.reply",
                message="Request /api/chat redirigido a flujo de clarificacion 422.",
                status="error",
                dependency="/api/chat",
                token_usage=deps["estimate_token_usage_from_text"](input_text=message),
                duration_ms=duration_ms,
                details={
                    "error_code": public_error.get("code"),
                    "error_stage": public_error.get("stage"),
                    "route": str(((payload_out.get("interaction") or {}).get("route") or "")),
                    "clarification_state_version": deps["clarification_state_version"],
                    "duration_ms": duration_ms,
                },
            )
            deps["emit_chat_verbose_event"](
                "conversation.chat.reply",
                {
                    "trace_id": trace_id,
                    "session_id": session_id,
                    "status": "error_clarification",
                    "http_status": int(HTTPStatus.UNPROCESSABLE_ENTITY),
                    "duration_ms": duration_ms,
                    "error_code": public_error.get("code"),
                    "interaction": interaction,
                },
            )
            handler._send_json(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                payload_out,
                extra_headers={"X-LIA-Error-Code": str(public_error.get("code") or exc.code)},
            )
            deps["chat_run_coordinator"].fail(chat_run_id, payload_out, base_dir=deps["chat_runs_path"])
            deps["chat_run_coordinator"].mark_response_sent(chat_run_id, base_dir=deps["chat_runs_path"])
            return
        deps["emit_reasoning_event"](
            trace_id=trace_id,
            phase="api",
            category="api_reply",
            step="ui_server.api_chat.pipeline_c.reply",
            message="Request /api/chat finalizó con error estricto Pipeline C.",
            status="error",
            dependency="/api/chat",
            token_usage=deps["estimate_token_usage_from_text"](input_text=message),
            duration_ms=duration_ms,
            details={
                "error_code": public_error.get("code"),
                "error_stage": public_error.get("stage"),
                "duration_ms": duration_ms,
            },
        )
        deps["emit_chat_verbose_event"](
            "conversation.chat.reply",
            {
                "trace_id": trace_id,
                "session_id": session_id,
                "status": "error",
                "http_status": int(exc.http_status),
                "duration_ms": duration_ms,
                "error_code": public_error.get("code"),
                "error": public_error.get("message"),
                "llm_runtime": public_error.get("llm"),
            },
        )
        deps["emit_user_error_event"]({
            "trace_id": trace_id,
            "session_id": session_id,
            "tenant_id": getattr(auth_context, "tenant_id", None),
            "user_id": getattr(auth_context, "user_id", None),
            "error_code": public_error.get("code"),
            "error_message": public_error.get("message"),
            "error_stage": public_error.get("stage"),
            "http_status": int(exc.http_status),
            "duration_ms": duration_ms,
            "question_preview": (message or "")[:200],
            "llm_provider": (public_error.get("llm") or {}).get("selected_provider"),
        })
        error_payload = {"ok": False, "error": public_error, "session_id": session_id, "chat_run_id": chat_run_id}
        handler._send_json(
            HTTPStatus(int(exc.http_status)),
            error_payload,
            extra_headers={"X-LIA-Error-Code": str(public_error.get("code") or exc.code)},
        )
        deps["chat_run_coordinator"].fail(chat_run_id, error_payload, base_dir=deps["chat_runs_path"])
        deps["chat_run_coordinator"].mark_response_sent(chat_run_id, base_dir=deps["chat_runs_path"])
        return
    except Exception as exc:  # noqa: BLE001
        duration_ms = round((time.monotonic() - t_api_chat) * 1000, 2)
        wrapped = deps["pipeline_c_internal_error_cls"](
            message="Error interno al ejecutar Pipeline C.",
            details={
                "endpoint": "/api/chat",
                "error": str(exc),
                "error_type": exc.__class__.__name__,
            },
        )
        public_error = deps["as_public_error"](
            wrapped,
            trace_id=trace_id,
            run_id=None,
            llm_runtime={},
            timing={"pipeline_total_ms": duration_ms, "stages_ms": {}},
            diagnostics={"endpoint": "/api/chat"},
        )
        if isinstance(public_error, dict):
            public_error["chat_run_id"] = chat_run_id
        deps["emit_reasoning_event"](
            trace_id=trace_id,
            phase="api",
            category="api_reply",
            step="ui_server.api_chat.pipeline_c.reply",
            message="Request /api/chat fallo por error interno en Pipeline C.",
            status="error",
            dependency="/api/chat",
            token_usage=deps["estimate_token_usage_from_text"](input_text=message),
            duration_ms=duration_ms,
            details={
                "error_code": public_error.get("code"),
                "error": public_error.get("message"),
                "duration_ms": duration_ms,
            },
        )
        deps["emit_chat_verbose_event"](
            "conversation.chat.reply",
            {
                "trace_id": trace_id,
                "session_id": session_id,
                "status": "error",
                "http_status": int(HTTPStatus.INTERNAL_SERVER_ERROR),
                "duration_ms": duration_ms,
                "error_code": public_error.get("code"),
                "error": public_error.get("message"),
            },
        )
        deps["emit_user_error_event"]({
            "trace_id": trace_id,
            "session_id": session_id,
            "tenant_id": getattr(auth_context, "tenant_id", None),
            "user_id": getattr(auth_context, "user_id", None),
            "error_code": public_error.get("code"),
            "error_message": public_error.get("message"),
            "error_stage": public_error.get("stage"),
            "http_status": int(HTTPStatus.INTERNAL_SERVER_ERROR),
            "duration_ms": duration_ms,
            "question_preview": (message or "")[:200],
            "llm_provider": (public_error.get("llm") or {}).get("selected_provider"),
        })
        error_payload = {"ok": False, "error": public_error, "session_id": session_id, "chat_run_id": chat_run_id}
        handler._send_json(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            error_payload,
            extra_headers={"X-LIA-Error-Code": str(public_error.get("code") or wrapped.code)},
        )
        deps["chat_run_coordinator"].fail(chat_run_id, error_payload, base_dir=deps["chat_runs_path"])
        deps["chat_run_coordinator"].mark_response_sent(chat_run_id, base_dir=deps["chat_runs_path"])
        return

    finalize_api_chat_response(
        handler,
        request_context=request_context,
        response=response,
        t_api_chat=t_api_chat,
        deps=deps,
    )


def handle_api_chat_stream_post(handler: Any, *, deps: dict[str, Any]) -> None:
    t_api_chat = time.monotonic()
    request_context = parse_api_chat_request(handler, t_api_chat=t_api_chat, deps=deps)
    if request_context is None:
        return
    try:
        auth_context = handler._resolve_auth_context(required=False, allow_public=True)
    except deps["platform_auth_error_cls"] as exc:
        handler._send_auth_error(exc)
        return
    request_context["is_public_visitor"] = bool(
        auth_context is not None
        and auth_context.role == deps.get("public_visitor_role", "public_visitor")
    )
    initialize_chat_request_context(
        request_context=request_context,
        auth_context=auth_context,
        channel="chat_stream",
        deps=deps,
    )
    chat_run_state = ensure_chat_run_context(request_context=request_context, deps=deps)
    existing_run = chat_run_state["record"]
    chat_run_id = str(existing_run.chat_run_id)
    if apply_api_chat_clarification(handler, request_context=request_context, t_api_chat=t_api_chat, deps=deps):
        return

    trace_id = str(request_context["trace_id"])
    session_id = str(request_context["session_id"])
    clarification_session_id = str(request_context.get("clarification_session_id") or session_id)
    message = str(request_context["message"])
    normalized_pais = str(request_context["normalized_pais"])
    topic = _optional_text(request_context.get("effective_topic") or request_context.get("topic"))
    requested_topic = _optional_text(request_context.get("requested_topic"))
    primary_scope_mode = str(request_context["primary_scope_mode"])
    pipeline_response_route = str(request_context["pipeline_response_route"])
    clarification_state = request_context.get("clarification_state")
    stream_sink: _ChatStreamSink | None = None
    keepalive_stop = threading.Event()
    stream_client_connected = True

    def _safe_write_event(event_name: str, payload: dict[str, Any]) -> bool:
        nonlocal stream_client_connected
        if not stream_client_connected:
            return False
        try:
            handler._write_sse_event(event_name, payload)
        except (BrokenPipeError, ConnectionResetError, OSError):
            stream_client_connected = False
            return False
        return True

    def _mark_response_sent_if_connected() -> None:
        if stream_client_connected:
            deps["chat_run_coordinator"].mark_response_sent(chat_run_id, base_dir=deps["chat_runs_path"])

    def _keepalive_loop() -> None:
        while not keepalive_stop.wait(8.0):
            _safe_write_event(
                "status",
                {
                    "stage": "keepalive",
                    "message": "Procesando respuesta...",
                },
            )

    try:
        handler._send_event_stream_headers()
        _safe_write_event(
            "meta",
            {
                "chat_run_id": chat_run_id,
                "trace_id": trace_id,
                "session_id": session_id,
                "client_turn_id": str(request_context.get("client_turn_id") or ""),
                "response_route": pipeline_response_route,
                "topic": topic,
                "requested_topic": requested_topic,
                "resume_supported": True,
            },
        )
        threading.Thread(target=_keepalive_loop, name=f"lia-chat-keepalive-{chat_run_id[:8]}", daemon=True).start()
        if not bool(chat_run_state["is_owner"]):
            if existing_run.status == "completed" and isinstance(existing_run.response_payload, dict) and existing_run.response_payload:
                _safe_write_event("final", dict(existing_run.response_payload))
                _mark_response_sent_if_connected()
                return
            if existing_run.status == "failed" and isinstance(existing_run.error_payload, dict) and existing_run.error_payload:
                _safe_write_event("error", dict(existing_run.error_payload))
                _mark_response_sent_if_connected()
                return
            _safe_write_event("status", {"stage": "join", "message": "Reanudando respuesta en curso..."})
            status, payload = deps["chat_run_coordinator"].wait_for_terminal(
                chat_run_id=chat_run_id,
                timeout_seconds=45.0,
                base_dir=deps["chat_runs_path"],
            )
            if status == "completed" and isinstance(payload, dict):
                _safe_write_event("final", payload)
            elif status == "failed" and isinstance(payload, dict):
                _safe_write_event("error", payload)
            else:
                _safe_write_event(
                    "error",
                    {
                        "ok": False,
                        "chat_run_id": chat_run_id,
                        "session_id": session_id,
                        "error": {"code": "CHAT_RUN_TIMEOUT", "message": "La ejecución sigue en curso. Usa el endpoint de resume."},
                    },
                )
            _mark_response_sent_if_connected()
            return
        stream_sink = _ChatStreamSink(handler, request_context=request_context, deps=deps)
        deps["emit_reasoning_event"](
            trace_id=trace_id,
            phase="api",
            category="api_call",
            step="ui_server.api_chat_stream.pipeline_c.inbound",
            message="Request /api/chat/stream recibido en Pipeline C.",
            dependency="/api/chat/stream",
            token_usage=deps["estimate_token_usage_from_text"](input_text=message),
            details={
                "topic": topic,
                "requested_topic": requested_topic,
                "pais": normalized_pais,
                "primary_scope_mode": primary_scope_mode,
                "response_route": pipeline_response_route,
                "debug": bool(request_context["debug_mode"]),
            },
        )
        deps["chat_run_coordinator"].mark_pipeline_started(chat_run_id, base_dir=deps["chat_runs_path"])
        response = deps["run_pipeline_c"](
            _build_pipeline_request(request_context, deps),
            index_file=deps["index_file_path"],
            policy_path=deps["credibility_policy_path"],
            runtime_config_path=deps["llm_runtime_config_path"],
            stream_sink=stream_sink,
        )
        deps["chat_run_coordinator"].set_pipeline_run_id(
            chat_run_id,
            str(getattr(response, "run_id", "") or ""),
            base_dir=deps["chat_runs_path"],
        )
        deps["chat_run_coordinator"].mark_pipeline_completed(chat_run_id, base_dir=deps["chat_runs_path"])
        finish_reason = None
        if isinstance(getattr(response, "llm_runtime", None), dict):
            finish_reason = str(response.llm_runtime.get("finish_reason") or "").strip() or None
        stream_sink.finalize_draft(finish_reason=finish_reason)
        _safe_write_event(
            "status",
            {"stage": "finalize", "message": "Preparando respuesta final..."},
        )
        response_payload = build_api_chat_success_payload(
            request_context=request_context,
            response=response,
            t_api_chat=t_api_chat,
            deps=deps,
        )
        deps["chat_run_coordinator"].mark_final_payload_ready(chat_run_id, base_dir=deps["chat_runs_path"])
        deps["chat_run_coordinator"].complete(chat_run_id, response_payload, base_dir=deps["chat_runs_path"])
        final_markdown = str(response_payload.get("answer_markdown") or "").strip()
        if stream_sink.rendered_markdown and not markdowns_equivalent(stream_sink.rendered_markdown, final_markdown):
            _safe_write_event("answer_replace", {"html": "", "markdown": final_markdown})
        _safe_write_event("final", response_payload)
        _mark_response_sent_if_connected()
    except deps["pipeline_c_strict_error_cls"] as exc:
        duration_ms = round((time.monotonic() - t_api_chat) * 1000, 2)
        llm_runtime = dict((exc.details or {}).get("llm_runtime") or {})
        timing = {
            "pipeline_total_ms": duration_ms,
            "stages_ms": dict((exc.details or {}).get("stages_ms") or {}),
        }
        diagnostics = {
            "endpoint": "/api/chat/stream",
            "error_details": dict(exc.details or {}),
            "request": {
                "topic": topic,
                "pais": normalized_pais,
                "primary_scope_mode": primary_scope_mode,
                "response_route": pipeline_response_route,
            },
        }
        public_error = deps["as_public_error"](
            exc,
            trace_id=trace_id,
            run_id=str((exc.details or {}).get("run_id") or "").strip() or None,
            llm_runtime=llm_runtime,
            timing=timing,
            diagnostics=diagnostics,
        )
        if isinstance(public_error, dict):
            public_error["chat_run_id"] = chat_run_id
        if deps["is_semantic_422_error"](exc.code):
            payload_out, _public_error, _interaction = _build_semantic_clarification_payload(
                exc=exc,
                request_context=request_context,
                message=message,
                session_id=session_id,
                clarification_session_id=clarification_session_id,
                clarification_state=clarification_state,
                trace_id=trace_id,
                endpoint="/api/chat/stream",
                duration_ms=duration_ms,
                deps=deps,
            )
            payload_out["chat_run_id"] = chat_run_id
            deps["chat_run_coordinator"].fail(chat_run_id, payload_out, base_dir=deps["chat_runs_path"])
            _safe_write_event("error", payload_out)
            _mark_response_sent_if_connected()
            return
        deps["emit_user_error_event"]({
            "trace_id": trace_id,
            "session_id": session_id,
            "tenant_id": getattr(auth_context, "tenant_id", None),
            "user_id": getattr(auth_context, "user_id", None),
            "error_code": public_error.get("code"),
            "error_message": public_error.get("message"),
            "error_stage": public_error.get("stage"),
            "http_status": int(exc.http_status),
            "duration_ms": duration_ms,
            "question_preview": (message or "")[:200],
            "llm_provider": (public_error.get("llm") or {}).get("selected_provider"),
        })
        error_payload = {"ok": False, "error": public_error, "session_id": session_id, "chat_run_id": chat_run_id}
        deps["chat_run_coordinator"].fail(chat_run_id, error_payload, base_dir=deps["chat_runs_path"])
        _safe_write_event("error", error_payload)
        _mark_response_sent_if_connected()
    except (BrokenPipeError, ConnectionResetError, OSError) as exc:
        _conn_error_payload = {
            "ok": False,
            "error": {
                "code": "PC_CLIENT_DISCONNECTED",
                "message": "La conexion del cliente se cerro durante el procesamiento.",
            },
            "session_id": session_id,
            "chat_run_id": chat_run_id,
        }
        try:
            deps["chat_run_coordinator"].fail(chat_run_id, _conn_error_payload, base_dir=deps["chat_runs_path"])
        except Exception:  # noqa: BLE001
            pass
        return
    except Exception as exc:  # noqa: BLE001
        duration_ms = round((time.monotonic() - t_api_chat) * 1000, 2)
        wrapped = deps["pipeline_c_internal_error_cls"](
            message="Error interno al ejecutar Pipeline C.",
            details={
                "endpoint": "/api/chat/stream",
                "error": str(exc),
                "error_type": exc.__class__.__name__,
            },
        )
        public_error = deps["as_public_error"](
            wrapped,
            trace_id=trace_id,
            run_id=None,
            llm_runtime={},
            timing={"pipeline_total_ms": duration_ms, "stages_ms": {}},
            diagnostics={"endpoint": "/api/chat/stream"},
        )
        if isinstance(public_error, dict):
            public_error["chat_run_id"] = chat_run_id
        deps["emit_user_error_event"]({
            "trace_id": trace_id,
            "session_id": session_id,
            "tenant_id": getattr(auth_context, "tenant_id", None),
            "user_id": getattr(auth_context, "user_id", None),
            "error_code": public_error.get("code"),
            "error_message": public_error.get("message"),
            "error_stage": public_error.get("stage"),
            "http_status": 500,
            "duration_ms": duration_ms,
            "question_preview": (message or "")[:200],
            "llm_provider": (public_error.get("llm") or {}).get("selected_provider"),
        })
        error_payload = {"ok": False, "error": public_error, "session_id": session_id, "chat_run_id": chat_run_id}
        deps["chat_run_coordinator"].fail(chat_run_id, error_payload, base_dir=deps["chat_runs_path"])
        _safe_write_event("error", error_payload)
        _mark_response_sent_if_connected()
    finally:
        keepalive_stop.set()
