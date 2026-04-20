"""Controller-dependency factories for `ui_server.py`.

Extracted from `ui_server.py` during granularize-v2 round 20 (Section B
sub-round 1). These factories build the ``deps`` dicts passed to the
write/analysis/chat/frontend-compat/public-session controllers at
request time. Each factory references 20-60 names that live on the
host module; rather than duplicate those imports here, we resolve them
via a lazy ``_host()`` accessor so circular imports stay at load time
are impossible.

The host calls ``_write_controller_deps()`` etc. at every HTTP request,
so the extra attribute lookups per call are negligible compared to the
JSON serialization that follows.
"""

from __future__ import annotations

import os
from typing import Any


def _host() -> Any:
    """Lazy accessor for `lia_graph.ui_server` (avoids circular import)."""
    from . import ui_server as _mod
    return _mod


def _write_controller_deps() -> dict[str, Any]:
    h = _host()
    return {
        "accept_terms": h.accept_terms,
        "approve_contribution": h.approve_contribution,
        "auth_nonces_path": h.AUTH_NONCES_PATH,
        "auth_nonce_path": h.AUTH_NONCES_PATH,
        "contribution_cls": h.Contribution,
        "contributions_path": h.WORKSPACE_ROOT / "artifacts" / "contributions",
        "emit_audit_event": h._emit_audit_event,
        "exchange_host_grant": h.exchange_host_grant,
        "feedback_path": h.FEEDBACK_PATH,
        "feedback_record_cls": h.FeedbackRecord,
        "form_guides_root": h.FORM_GUIDES_ROOT,
        "guide_chat_request_cls": h.GuideChatRequest,
        "host_integrations_config_path": h.HOST_INTEGRATIONS_CONFIG_PATH,
        "index_file_path": h.INDEX_FILE_PATH,
        "chat_run_milestones_route_re": h._CHAT_RUN_MILESTONES_ROUTE_RE,
        "chat_runs_path": h.CHAT_RUNS_PATH,
        "get_chat_run": h.load_chat_run,
        "ingestion_clear_batch_route_re": h._INGESTION_CLEAR_BATCH_ROUTE_RE,
        "ingestion_delete_failed_route_re": h._INGESTION_DELETE_FAILED_ROUTE_RE,
        "ingestion_files_route_re": h._INGESTION_FILES_ROUTE_RE,
        "ingestion_process_route_re": h._INGESTION_PROCESS_ROUTE_RE,
        "ingestion_retry_route_re": h._INGESTION_RETRY_ROUTE_RE,
        "ingestion_validate_batch_route_re": h._INGESTION_VALIDATE_BATCH_ROUTE_RE,
        "ingestion_runtime": h.INGESTION_RUNTIME,
        "ingestion_stop_route_re": h._INGESTION_STOP_ROUTE_RE,
        "llm_runtime_config_path": h.LLM_RUNTIME_CONFIG_PATH,
        "platform_auth_error_cls": h.PlatformAuthError,
        "record_chat_run_event_once": h.record_chat_run_event_once,
        "reject_contribution": h.reject_contribution,
        "resolve_guide": h.resolve_guide,
        "run_guide_chat": h.run_guide_chat,
        "save_contribution": h.save_contribution,
        "save_feedback": h.save_feedback,
        "update_feedback_comment": h.update_feedback_comment,
        "switch_active_company": h.switch_active_company,
        "terms_policy_path": h.TERMS_POLICY_PATH,
        "terms_state_path": h.TERMS_STATE_PATH,
        "jobs_path": h.JOBS_RUNTIME_PATH,
        "workspace_root": h.WORKSPACE_ROOT,
    }


def _analysis_controller_deps() -> dict[str, Any]:
    h = _host()
    return {
        "as_public_error": h.as_public_error,
        "axis_labels": {},
        "build_extractive_interpretation_summary": h._build_extractive_interpretation_summary,
        "build_decision_frame": h.build_decision_frame,
        "build_interpretation_candidate": h.build_interpretation_candidate,
        "build_interpretation_query_seed": h._build_interpretation_query_seed,
        "build_normative_helper_citations": h._build_normative_helper_citations,
        "build_public_citation_from_row": h._build_public_citation_from_row,
        "citation_cls": h.Citation,
        "classify_provider": h._classify_provider,
        "clip_session_content": h._clip_session_content,
        "dedupe_interpretation_docs": h._dedupe_interpretation_docs,
        "expand_expert_panel_requested_refs": h._expand_expert_panel_requested_refs,
        "expert_card_summary": h._expert_card_summary,
        "expert_summary_overrides_path": h.EXPERT_SUMMARY_OVERRIDES_PATH,
        "filter_provider_links": h._filter_provider_links,
        "find_document_index_row": h._find_document_index_row,
        "first_substantive_sentence": h._first_substantive_sentence,
        "generate_llm_strict": h.generate_llm_strict,
        "index_file_path": h.INDEX_FILE_PATH,
        "llm_output_quality_error_cls": h.LLMOutputQualityError,
        "llm_runtime_config_path": h.LLM_RUNTIME_CONFIG_PATH,
        "load_doc_corpus_text": h._load_doc_corpus_text,
        "logical_doc_id": h._logical_doc_id,
        "normalize_pais": h.normalize_pais,
        "normalize_provider_labels": h.normalize_provider_labels,
        "normalize_topic_key": h.normalize_topic_key,
        "pipeline_c_internal_error_cls": h.PipelineCInternalError,
        "pipeline_c_strict_error_cls": h.PipelineCStrictError,
        "prioritize_expert_panel_docs": h._prioritize_expert_panel_docs,
        "resolve_doc_expert_providers": h._resolve_doc_expert_providers,
        "select_interpretation_candidates": h.select_interpretation_candidates,
        "serialize_ranked_interpretation": h.serialize_ranked_interpretation,
        "summarize_snippet": h._summarize_snippet,
        "extended_excerpt": h._expert_extended_excerpt,
        "supported_topics": h.SUPPORTED_TOPICS,
        "warn_missing_active_index_generation": h._warn_missing_active_index_generation,
    }


def _chat_controller_deps() -> dict[str, Any]:
    h = _host()
    return {
        "advance_clarification_state": h.advance_clarification_state,
        "append_turn": h.append_turn,
        "as_public_error": h.as_public_error,
        "auth_context_cls": h.AuthContext,
        "build_clarification_error_payload": h._build_clarification_error_payload,
        "build_clarification_interaction_payload": h.build_clarification_interaction_payload,
        "build_normative_helper_citations": h._build_normative_helper_citations,
        "build_public_api_error": h._build_public_api_error,
        "chat_run_coordinator": h.get_chat_run_coordinator(),
        "chat_runs_path": h.CHAT_RUNS_PATH,
        "chat_session_metrics_path": h.CHAT_SESSION_METRICS_PATH,
        "citation_gap_registry_path": h.CITATION_GAP_REGISTRY_PATH,
        "clarification_sessions_path": h.CLARIFICATION_SESSIONS_PATH,
        "clarification_state_version": h.CLARIFICATION_STATE_VERSION,
        "clear_clarification_session_state": h.clear_clarification_session_state,
        "comparative_field_questions": h.COMPARATIVE_FIELD_QUESTIONS,
        "conversations_path": h.CONVERSATIONS_PATH,
        "credibility_policy_path": h.WORKSPACE_ROOT / "config" / "credibility_policy.json",
        "emit_chat_verbose_event": h._emit_chat_verbose_event,
        "emit_user_error_event": lambda payload: h.emit_event("user.chat.error", payload, log_path=h.USER_ERROR_LOG_PATH),
        "emit_event": h.emit_event,
        "emit_reasoning_event": h.emit_reasoning_event,
        "ensure_session": h.ensure_session,
        "ensure_session_shell": h.ensure_session_shell,
        "enrich_citation_payloads_with_usage_context": h._enrich_citation_payloads_with_usage_context,
        "estimate_token_usage_from_text": h.estimate_token_usage_from_text,
        "get_clarification_session_state": h.get_clarification_session_state,
        "get_chat_session_metrics": h.get_chat_session_metrics,
        "index_file_path": h.INDEX_FILE_PATH,
        "is_semantic_422_error": h.is_semantic_422_error,
        "jobs_path": h.JOBS_RUNTIME_PATH,
        "llm_dynamic_clarification_decider": h._llm_dynamic_clarification_decider,
        "llm_runtime_config_path": h.LLM_RUNTIME_CONFIG_PATH,
        "load_session": h.load_session,
        "merge_citation_payloads": h._merge_citation_payloads,
        "normalize_pais": h.normalize_pais,
        "normalize_token_usage": h.normalize_token_usage,
        "normalize_topic_key": h.normalize_topic_key,
        "pipeline_c_internal_error_cls": h.PipelineCInternalError,
        "pipeline_c_request_cls": h.PipelineCRequest,
        "pipeline_c_strict_error_cls": h.PipelineCStrictError,
        "default_pipeline_variant": str(
            os.getenv("LIA_PIPELINE_VARIANT", h.DEFAULT_PIPELINE_VARIANT)
        ).strip() or h.DEFAULT_PIPELINE_VARIANT,
        "execute_routed_pipeline": lambda request, **kwargs: h.execute_routed_pipeline(
            request,
            pipeline_c_runner=h.run_pipeline_c,
            pipeline_d_runner=h.run_pipeline_d,
            **kwargs,
        ),
        "platform_auth_error_cls": h.PlatformAuthError,
        "public_visitor_role": h.PUBLIC_VISITOR_ROLE,
        "public_tenant_id": h.PUBLIC_TENANT_ID,
        "public_max_output_tokens": int(
            str(os.getenv("LIA_PUBLIC_MAX_OUTPUT_TOKENS", "2048")).strip() or "2048"
        ),
        "refresh_state_from_semantic_error": h.refresh_state_from_semantic_error,
        "register_citation_gaps": h.register_citation_gaps,
        "resolve_chat_topic": h.resolve_chat_topic,
        "resolve_pipeline_route": h.resolve_pipeline_route,
        "resolve_guided_clarification_requirements": h._resolve_guided_clarification_requirements,
        "save_usage_event": h.save_usage_event,
        "should_intercept_clarification_state": h.should_intercept_clarification_state,
        "stored_conversation_turn_cls": h.StoredConversationTurn,
        "strip_inline_evidence_annotations": h.strip_inline_evidence_annotations,
        "update_chat_session_metrics": h.update_chat_session_metrics,
        "update_session_metadata": h.update_session_metadata,
        "upsert_clarification_session_state": h.upsert_clarification_session_state,
        "usage_event_cls": h.UsageEvent,
        "usage_events_path": h.USAGE_EVENTS_PATH,
        "validate_pipeline_c_payload": h._validate_pipeline_c_payload,
        "build_user_message_for_question": h.build_user_message_for_question,
        "uuid4": h.uuid4,
    }


def _frontend_compat_controller_deps() -> dict[str, Any]:
    h = _host()
    return {
        "chat_run_milestones_route_re": h._CHAT_RUN_MILESTONES_ROUTE_RE,
        "chat_runs_path": h.CHAT_RUNS_PATH,
        "feedback_path": h.FEEDBACK_PATH,
        "feedback_record_cls": h.FeedbackRecord,
        "load_feedback": h.load_feedback,
        "public_tenant_id": h.PUBLIC_TENANT_ID,
        "record_chat_run_event_once": h.record_chat_run_event_once,
        "save_feedback": h.save_feedback,
        "update_feedback_comment": h.update_feedback_comment,
    }


def _public_session_controller_deps() -> dict[str, Any]:
    h = _host()
    return {
        "issue_public_visitor_token": h.issue_public_visitor_token,
        "public_captcha_enabled": h.PUBLIC_CAPTCHA_ENABLED,
        "public_captcha_pass_exists": h.public_captcha_pass_exists,
        "public_captcha_pass_record": h.public_captcha_pass_record,
        "public_mode_enabled": h.PUBLIC_MODE_ENABLED,
        "public_token_ttl_seconds": h.PUBLIC_TOKEN_TTL_SECONDS,
        "public_turnstile_site_key": h.PUBLIC_TURNSTILE_SITE_KEY,
        "ui_dir": h.UI_DIR,
        "verify_turnstile": h.verify_turnstile,
    }
