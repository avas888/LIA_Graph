from __future__ import annotations

import json
import logging
import threading
from typing import Any

from .background_jobs import run_job_async
from .chat_run_runtime import build_chat_run_fingerprint
from .ui_chat_context import (
    ChatRequestContext,
    _build_turn_metadata,
    _extract_conversation_state,
    _extract_conversation_context,
    _optional_text,
    build_clarification_scope_key,
    build_memory_summary,
)

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Chat-run context
# ---------------------------------------------------------------------------


def ensure_chat_run_context(*, request_context: ChatRequestContext, deps: dict[str, Any]) -> dict[str, Any]:
    payload = dict(request_context.get("payload") or {})
    client_turn_id = str(payload.get("client_turn_id", "")).strip()
    if not client_turn_id:
        client_turn_id = str(deps["uuid4"]())
    resolved_pipeline_route = request_context.get("resolved_pipeline_route")
    if resolved_pipeline_route is None:
        resolved_pipeline_route = deps["resolve_pipeline_route"](
            request_override=request_context.get("pipeline_route_override"),
            default_variant=deps.get("default_pipeline_variant"),
        )
        request_context["resolved_pipeline_route"] = resolved_pipeline_route
        request_context["requested_pipeline_variant"] = str(
            getattr(resolved_pipeline_route, "route", "") or "pipeline_c"
        )
        request_context["pipeline_variant"] = str(
            getattr(resolved_pipeline_route, "pipeline_variant", "") or "pipeline_c"
        )
        request_context["shadow_pipeline_variant"] = (
            str(getattr(resolved_pipeline_route, "shadow_pipeline_variant", "")).strip() or None
        )
        request_context["pipeline_route_source"] = str(
            getattr(resolved_pipeline_route, "source", "") or "config_default"
        )
    request_fingerprint = build_chat_run_fingerprint(
        session_id=str(request_context["session_id"]),
        client_turn_id=client_turn_id,
        message=str(request_context["message"]),
        topic=_optional_text(request_context.get("effective_topic") or request_context.get("topic")),
        pais=str(request_context["normalized_pais"]),
        primary_scope_mode=str(request_context["primary_scope_mode"]),
        response_route=str(request_context["pipeline_response_route"]),
        retrieval_profile=str(request_context.get("retrieval_profile") or "hybrid_rerank"),
        response_depth=str(request_context.get("response_depth") or "auto"),
        first_response_mode=str(request_context.get("first_response_mode") or "fast_action"),
        engine_version=str(request_context.get("pipeline_variant") or "pipeline_c"),
    )
    payload["client_turn_id"] = client_turn_id
    request_context["payload"] = payload
    request_context["client_turn_id"] = client_turn_id
    request_context["request_fingerprint"] = request_fingerprint
    record, is_owner = deps["chat_run_coordinator"].acquire(
        trace_id=str(request_context["trace_id"]),
        session_id=str(request_context["session_id"]),
        client_turn_id=client_turn_id,
        request_fingerprint=request_fingerprint,
        endpoint=str(request_context.get("endpoint") or "/api/chat"),
        request_payload={
            "message": str(request_context["message"]),
            "topic": _optional_text(request_context.get("effective_topic") or request_context.get("topic")),
            "requested_topic": _optional_text(request_context.get("requested_topic")),
            "effective_topic": _optional_text(request_context.get("effective_topic") or request_context.get("topic")),
            "secondary_topics": list(request_context.get("secondary_topics") or ()),
            "topic_adjusted": bool(request_context.get("topic_adjusted", False)),
            "topic_notice": str(request_context.get("topic_notice") or "") or None,
            "topic_adjustment_reason": str(request_context.get("topic_adjustment_reason") or "") or None,
            "pais": str(request_context["normalized_pais"]),
            "primary_scope_mode": str(request_context["primary_scope_mode"]),
            "response_route": str(request_context["pipeline_response_route"]),
            "retrieval_profile": str(request_context.get("retrieval_profile") or "hybrid_rerank"),
            "response_depth": str(request_context.get("response_depth") or "auto"),
            "first_response_mode": str(request_context.get("first_response_mode") or "fast_action"),
            "pipeline_route": str(request_context.get("requested_pipeline_variant") or "pipeline_c"),
            "pipeline_variant": str(request_context.get("pipeline_variant") or "pipeline_c"),
            "shadow_pipeline_variant": (
                str(request_context.get("shadow_pipeline_variant") or "").strip() or None
            ),
            "pipeline_route_source": str(request_context.get("pipeline_route_source") or "config_default"),
            "debug": bool(request_context["debug_mode"]),
        },
        tenant_id=str(request_context.get("tenant_id") or ""),
        user_id=str(request_context.get("user_id") or ""),
        company_id=str(request_context.get("company_id") or ""),
        chat_run_id=str(payload.get("chat_run_id", "")).strip() or None,
        base_dir=deps["chat_runs_path"],
    )
    request_context["chat_run_id"] = record.chat_run_id
    request_context["chat_run_owner"] = bool(is_owner)
    return {
        "record": record,
        "is_owner": bool(is_owner),
    }


# ---------------------------------------------------------------------------
# Request-context initialization
# ---------------------------------------------------------------------------


def initialize_chat_request_context(
    *,
    request_context: ChatRequestContext,
    auth_context: Any,
    channel: str,
    deps: dict[str, Any],
) -> None:
    payload = dict(request_context.get("payload") or {})
    public_visitor_role = deps.get("public_visitor_role", "public_visitor")
    public_tenant_id = deps.get("public_tenant_id", "public_anon")
    is_public_visitor = bool(
        auth_context is not None and auth_context.role == public_visitor_role
    )
    if is_public_visitor:
        # Public visitors live in their own reserved tenant. Every per-IP
        # synthetic identifier (`pub_<hash>`) is treated as a distinct user
        # for analytics, but they share the `public_anon` tenant namespace
        # so retrieval falls back to shared corpora identically to today's
        # anonymous path.
        tenant_id = public_tenant_id
        user_id = auth_context.user_id
        company_id = ""
        integration_id = "lia_public"
        host_session_id = ""
        accountant_id = user_id
    else:
        tenant_id = auth_context.tenant_id if auth_context is not None else str(payload.get("tenant_id", "")).strip() or "public"
        user_id = auth_context.user_id if auth_context is not None else str(payload.get("user_id", "")).strip()
        company_id = auth_context.active_company_id if auth_context is not None else str(payload.get("company_id", "")).strip()
        integration_id = auth_context.integration_id if auth_context is not None else str(payload.get("integration_id", "")).strip()
        host_session_id = auth_context.host_session_id if auth_context is not None else str(payload.get("host_session_id", "")).strip()
        accountant_id = user_id or str(payload.get("accountant_id", "")).strip() or "ui_user"
    session_id = str(request_context["session_id"])
    request_context.update(
        {
            "auth_context": auth_context,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "company_id": company_id,
            "integration_id": integration_id,
            "host_session_id": host_session_id,
            "accountant_id": accountant_id,
            "is_public_visitor": is_public_visitor,
            "endpoint": "/api/chat/stream" if channel == "chat_stream" else "/api/chat",
            "clarification_session_id": build_clarification_scope_key(
                {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "company_id": company_id,
                    "session_id": session_id,
                }
            ),
            "conversation_session": None,
        }
    )


# ---------------------------------------------------------------------------
# Turn persistence
# ---------------------------------------------------------------------------


def persist_user_turn(*, request_context: ChatRequestContext, deps: dict[str, Any]) -> None:
    if bool(request_context.get("user_turn_persisted")):
        return
    deps["ensure_session_shell"](
        tenant_id=str(request_context.get("tenant_id") or "public"),
        session_id=str(request_context["session_id"]),
        accountant_id=str(request_context.get("accountant_id") or "ui_user"),
        topic=str(request_context.get("topic") or "").strip() or None,
        pais=str(request_context.get("normalized_pais") or "colombia").strip() or "colombia",
        user_id=str(request_context.get("user_id") or ""),
        company_id=str(request_context.get("company_id") or ""),
        integration_id=str(request_context.get("integration_id") or ""),
        host_session_id=str(request_context.get("host_session_id") or ""),
        channel="chat_stream" if str(request_context.get("endpoint") or "").endswith("/stream") else "chat",
        base_dir=deps["conversations_path"],
    )
    deps["append_turn"](
        tenant_id=str(request_context.get("tenant_id") or "public"),
        session_id=str(request_context["session_id"]),
        user_id=str(request_context.get("user_id") or "") or None,
        company_id=str(request_context.get("company_id") or "") or None,
        turn=deps["stored_conversation_turn_cls"](
            role="user",
            content=str(request_context.get("message") or "").strip(),
            trace_id=str(request_context.get("trace_id") or "").strip() or None,
        ),
        base_dir=deps["conversations_path"],
    )
    request_context["user_turn_persisted"] = True


def persist_assistant_turn(
    *,
    request_context: ChatRequestContext,
    content: str,
    trace_id: str | None,
    deps: dict[str, Any],
    layer_contributions: dict[str, int] | None = None,
    turn_metadata: dict[str, Any] | None = None,
) -> None:
    deps["ensure_session_shell"](
        tenant_id=str(request_context.get("tenant_id") or "public"),
        session_id=str(request_context["session_id"]),
        accountant_id=str(request_context.get("accountant_id") or "ui_user"),
        topic=str(request_context.get("topic") or "").strip() or None,
        pais=str(request_context.get("normalized_pais") or "colombia").strip() or "colombia",
        user_id=str(request_context.get("user_id") or ""),
        company_id=str(request_context.get("company_id") or ""),
        integration_id=str(request_context.get("integration_id") or ""),
        host_session_id=str(request_context.get("host_session_id") or ""),
        channel="chat_stream" if str(request_context.get("endpoint") or "").endswith("/stream") else "chat",
        base_dir=deps["conversations_path"],
    )
    updated = deps["append_turn"](
        tenant_id=str(request_context.get("tenant_id") or "public"),
        session_id=str(request_context["session_id"]),
        user_id=str(request_context.get("user_id") or "") or None,
        company_id=str(request_context.get("company_id") or "") or None,
        turn=deps["stored_conversation_turn_cls"](
            role="assistant",
            content=str(content or "").strip(),
            layer_contributions=dict(layer_contributions or {}) or None,
            trace_id=str(trace_id or "").strip() or None,
            turn_metadata=turn_metadata,
        ),
        base_dir=deps["conversations_path"],
    )
    if updated is None:
        return
    memory_summary = build_memory_summary(updated)
    refreshed = deps["update_session_metadata"](
        tenant_id=str(request_context.get("tenant_id") or "public"),
        session_id=str(request_context["session_id"]),
        user_id=str(request_context.get("user_id") or "") or None,
        company_id=str(request_context.get("company_id") or "") or None,
        memory_summary=memory_summary,
        base_dir=deps["conversations_path"],
    )
    request_context["conversation_session"] = refreshed or updated


def persist_usage_events(
    *,
    request_context: ChatRequestContext,
    response_payload: dict[str, Any],
    deps: dict[str, Any],
) -> None:
    token_usage = dict(response_payload.get("token_usage") or {})
    llm_runtime = dict(response_payload.get("llm_runtime") or {})
    for event_type in ("turn", "llm"):
        usage_payload = dict(token_usage.get(event_type) or {})
        deps["save_usage_event"](
            deps["usage_event_cls"](
                event_id="",
                event_type=f"{event_type}_usage",
                endpoint=str(request_context.get("endpoint") or "/api/chat"),
                tenant_id=str(request_context.get("tenant_id") or "public"),
                user_id=str(request_context.get("user_id") or ""),
                company_id=str(request_context.get("company_id") or ""),
                session_id=str(request_context.get("session_id") or ""),
                trace_id=str(response_payload.get("trace_id") or request_context.get("trace_id") or ""),
                run_id=str(response_payload.get("run_id") or ""),
                integration_id=str(request_context.get("integration_id") or ""),
                provider=str(llm_runtime.get("selected_provider") or ""),
                model=str(llm_runtime.get("model") or ""),
                usage_source=str(usage_payload.get("source") or "none"),
                billable=event_type == "llm" and str(usage_payload.get("source") or "").strip() == "provider",
                input_tokens=int(usage_payload.get("input_tokens") or 0),
                output_tokens=int(usage_payload.get("output_tokens") or 0),
                total_tokens=int(usage_payload.get("total_tokens") or 0),
                metadata={
                    "response_route": request_context.get("pipeline_response_route"),
                    "primary_scope_mode": request_context.get("primary_scope_mode"),
                },
            ),
            base_dir=deps["usage_events_path"],
        )


# ---------------------------------------------------------------------------
# Scheduled persistence (background job)
# ---------------------------------------------------------------------------


def _schedule_success_persistence(
    *,
    request_context: ChatRequestContext,
    response_payload: dict[str, Any],
    answer_visible_text: str,
    deps: dict[str, Any],
) -> str:
    request_snapshot = dict(request_context)
    response_snapshot = json.loads(json.dumps(response_payload))
    answer_snapshot = str(answer_visible_text or "")
    layer_contributions = (
        dict(response_snapshot.get("layer_contributions") or {})
        if isinstance(response_snapshot.get("layer_contributions"), dict)
        else None
    )
    turn_metadata = _build_turn_metadata(response_snapshot)
    chat_run_id = str(request_context.get("chat_run_id") or "")

    def _emit_persistence_warning(
        dependency: str,
        *,
        stage: str,
        error: Exception,
    ) -> dict[str, str]:
        warning = {
            "dependency": str(dependency or "").strip() or "unknown",
            "stage": str(stage or "").strip() or "unknown",
            "error": str(error),
            "error_type": error.__class__.__name__,
        }
        _log.warning(
            "chat_persistence: degraded dependency during %s (%s). chat_run_id=%s error=%s",
            warning["stage"],
            warning["dependency"],
            chat_run_id,
            warning["error"],
        )
        try:
            deps["emit_event"](
                "platform.persistence.warning",
                {
                    "trace_id": str(response_snapshot.get("trace_id") or request_snapshot.get("trace_id") or ""),
                    "session_id": str(request_snapshot.get("session_id") or ""),
                    "chat_run_id": chat_run_id or None,
                    **warning,
                },
            )
        except Exception:  # noqa: BLE001
            pass
        return warning

    def _task() -> dict[str, Any]:
        warnings: list[dict[str, str]] = []
        session_metrics: dict[str, Any] = {
            "session_id": str(request_snapshot.get("session_id") or ""),
            "turn_count": 0,
        }
        try:
            deps["ensure_session_shell"](
                tenant_id=str(request_snapshot.get("tenant_id") or "public"),
                session_id=str(request_snapshot.get("session_id") or ""),
                accountant_id=str(request_snapshot.get("accountant_id") or "ui_user"),
                topic=str(request_snapshot.get("topic") or "").strip() or None,
                pais=str(request_snapshot.get("normalized_pais") or "colombia"),
                user_id=str(request_snapshot.get("user_id") or ""),
                company_id=str(request_snapshot.get("company_id") or ""),
                integration_id=str(request_snapshot.get("integration_id") or ""),
                host_session_id=str(request_snapshot.get("host_session_id") or ""),
                channel="chat_stream" if str(request_snapshot.get("endpoint") or "").endswith("/stream") else "chat",
                base_dir=deps["conversations_path"],
            )
            persist_user_turn(request_context=request_snapshot, deps=deps)
            persist_assistant_turn(
                request_context=request_snapshot,
                content=answer_snapshot,
                trace_id=str(response_snapshot.get("trace_id") or request_snapshot.get("trace_id") or ""),
                deps=deps,
                layer_contributions=layer_contributions,
                turn_metadata=turn_metadata,
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(_emit_persistence_warning("conversation_store", stage="turn_persistence", error=exc))
        try:
            session_metrics = deps["update_chat_session_metrics"](
                session_id=str(request_snapshot.get("session_id") or ""),
                turn_usage=dict((response_snapshot.get("token_usage") or {}).get("turn") or {}),
                llm_usage=dict((response_snapshot.get("token_usage") or {}).get("llm") or {}),
                trace_id=str(response_snapshot.get("trace_id") or request_snapshot.get("trace_id") or ""),
                run_id=str(response_snapshot.get("run_id") or "").strip() or None,
                path=deps["chat_session_metrics_path"],
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(_emit_persistence_warning("chat_session_metrics", stage="session_metrics", error=exc))
        try:
            persist_usage_events(request_context=request_snapshot, response_payload=response_snapshot, deps=deps)
        except Exception as exc:  # noqa: BLE001
            warnings.append(_emit_persistence_warning("usage_ledger", stage="usage_events", error=exc))
        try:
            deps["chat_run_coordinator"].mark_async_persistence_done(chat_run_id, base_dir=deps["chat_runs_path"])
        except Exception as exc:  # noqa: BLE001
            warnings.append(_emit_persistence_warning("chat_run_store", stage="mark_async_persistence_done", error=exc))
        result = {
            "session_id": str(session_metrics.get("session_id") or request_snapshot.get("session_id") or ""),
            "turn_count": int(session_metrics.get("turn_count") or 0),
            "chat_run_id": chat_run_id,
        }
        if warnings:
            result["warnings"] = warnings
        return result

    def _run_without_job_tracking() -> None:
        try:
            _task()
        except Exception as exc:  # noqa: BLE001
            _emit_persistence_warning("background_jobs", stage="raw_fallback", error=exc)

    try:
        return run_job_async(
            job_type="chat_persistence",
            tenant_id=str(request_context.get("tenant_id") or ""),
            user_id=str(request_context.get("user_id") or ""),
            company_id=str(request_context.get("company_id") or ""),
            request_payload={
                "chat_run_id": chat_run_id,
                "session_id": str(request_context.get("session_id") or ""),
                "trace_id": str(request_context.get("trace_id") or ""),
            },
            task=_task,
            base_dir=deps["jobs_path"],
        )
    except Exception as exc:  # noqa: BLE001
        _emit_persistence_warning("jobs_store", stage="schedule_job", error=exc)
        threading.Thread(
            target=_run_without_job_tracking,
            name=f"lia-chat-persist-fallback-{chat_run_id[:8] or 'anon'}",
            daemon=True,
        ).start()
        return ""


# ---------------------------------------------------------------------------
# Session loading and pipeline-request building
# ---------------------------------------------------------------------------


def _ensure_conversation_session_loaded(request_context: ChatRequestContext, deps: dict[str, Any]) -> None:
    """Load the conversation session from the store if not already present.

    Persistence runs in a background thread, so conversation_session is typically
    None when the next turn arrives.  Loading it here ensures
    _extract_conversation_context() has access to prior turns for semantic memory.
    """
    if request_context.get("conversation_session") is not None:
        return
    load_fn = deps.get("load_session")
    if load_fn is None:
        return
    session_id = str(request_context.get("session_id") or "").strip()
    if not session_id:
        return
    try:
        session = load_fn(
            tenant_id=str(request_context.get("tenant_id") or "public"),
            session_id=session_id,
            user_id=str(request_context.get("user_id") or "") or None,
            company_id=str(request_context.get("company_id") or "") or None,
            base_dir=deps["conversations_path"],
        )
        if session is not None:
            request_context["conversation_session"] = session
    except Exception:  # noqa: BLE001
        pass  # best-effort — pipeline can still run without context


def _build_pipeline_request(request_context: ChatRequestContext, deps: dict[str, Any]) -> Any:
    _ensure_conversation_session_loaded(request_context, deps)
    operation_date = request_context.get("operation_date")
    company_context_payload = request_context.get("company_context_payload")
    conversation_state = _extract_conversation_state(request_context)
    return deps["pipeline_c_request_cls"](
        message=str(request_context["pipeline_message"]),
        trace_id=str(request_context["trace_id"]),
        chat_run_id=str(request_context.get("chat_run_id") or "").strip() or None,
        session_id=str(request_context.get("session_id") or "").strip() or None,
        pais=str(request_context["normalized_pais"]),
        topic=_optional_text(request_context.get("effective_topic") or request_context.get("topic")),
        requested_topic=_optional_text(request_context.get("requested_topic")),
        secondary_topics=tuple(request_context.get("secondary_topics") or ()),
        topic_adjusted=bool(request_context.get("topic_adjusted", False)),
        topic_notice=str(request_context.get("topic_notice") or "").strip() or None,
        topic_adjustment_reason=str(request_context.get("topic_adjustment_reason") or "").strip() or None,
        topic_router_confidence=float(request_context.get("topic_router_confidence") or 0.0),
        operation_date=str(operation_date).strip() if operation_date else None,
        company_context=company_context_payload if isinstance(company_context_payload, dict) else None,
        primary_scope_mode=str(request_context["primary_scope_mode"]),
        response_route=str(request_context["pipeline_response_route"]),
        retrieval_profile=str(request_context.get("retrieval_profile") or "hybrid_rerank"),
        response_depth=str(request_context.get("response_depth") or "auto"),
        first_response_mode=str(request_context.get("first_response_mode") or "fast_action"),
        conversation_context=_extract_conversation_context(request_context),
        conversation_state=conversation_state,
        debug=bool(request_context["debug_mode"]),
        is_public_visitor=bool(request_context.get("is_public_visitor", False)),
        public_max_output_tokens=int(deps.get("public_max_output_tokens") or 0) or None,
    )
