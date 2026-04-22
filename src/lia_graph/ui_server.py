"""HTTP front-door for Lia Graph.

READ THIS BEFORE EDITING: `docs/next/granularization_v1.md` §"Controller Surface Catalog"
is the authoritative index of every domain controller, its dep-injection helper,
and its HTTP surface. It also lists the recipe for adding new endpoints.

Architecture in one paragraph:
    This file owns ONE `BaseHTTPRequestHandler` subclass (`LiaUIHandler`) plus the
    module-level `_<domain>_controller_deps()` helpers (search for `def _*_controller_deps`).
    Every `_handle_*` method on the class is a 5–15 line DELEGATE that builds a
    fresh `deps={…}` dict and calls `handle_<domain>_<verb>(handler, …, deps=…)`
    in a sibling `ui_<domain>_controllers.py` module. Domain logic does NOT live
    here — only dispatch, auth, rate limiting, response helpers (`_send_json`,
    `_send_bytes`), and dep wiring.

Where each surface lives (see the catalog for the authoritative list):
    - `ui_frontend_compat_controllers.py` — `/api/llm/status`, `/api/feedback*`, milestones
    - `ui_public_session_controllers.py`  — `/api/public/session`, `/public`
    - `ui_chat_controller.py`             — `/api/chat`, `/api/chat/stream`
    - `ui_route_controllers.py`           — form-guides, ops, source-view, analysis
    - `ui_citation_controllers.py`        — `/api/citations/*`
    - `ui_user_management_controllers.py` — admin + invite flows
    - `ui_eval_controllers.py`            — eval surface
    - `ui_write_controllers.py`           — state-mutating writes (501-stubs, filling in B9)
    - `ui_conversation_controllers.py`    — history (501-stub, filling in B4)
    - `ui_admin_controllers.py`           — platform/admin (501-stub, filling in B5)
    - `ui_runtime_controllers.py`         — runtime terms / orchestration settings (501-stub, B6)
    - `ui_reasoning_controllers.py`       — reasoning SSE (501-stub, B7)
    - `ui_ingestion_controllers.py`       — ingestion (501-stub, B8)

If you are about to inline domain logic in this file: DO NOT. Extract to the matching
controller and wire a delegate. See the "How to add a new endpoint" recipe in the
catalog. Adding inline logic here causes the monolith-regrowth problem the
granularization v1 refactor was undertaken to fix.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import mimetypes
import os
import re
import subprocess
import threading
import time
from datetime import datetime, timezone
from dataclasses import fields
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from .chat_response_modes import ALLOWED_FIRST_RESPONSE_MODES, ALLOWED_RESPONSE_DEPTHS
from .contracts import (
    ALLOWED_CLIENT_MODES,
    ALLOWED_FOLLOWUP_ACTIONS,
    ALLOWED_KNOWLEDGE_LAYER_FILTERS,
    ALLOWED_PAIN_HINTS,
    ALLOWED_RETRIEVAL_PROFILES,
    ALLOWED_RESPONSE_GOALS,
    AccessContext,
    Citation,
    CompanyContext,
    ConversationTurn,
    DocumentRecord,
)
from .pipeline_c import get_run as get_pipeline_c_run
from .pipeline_c import get_timeline as get_pipeline_c_timeline
from .pipeline_c import list_runs as list_pipeline_c_runs
from .pipeline_c import run_pipeline_c
from .pipeline_c.contracts import PipelineCRequest
from .pipeline_d import run_pipeline_d
from .pipeline_c.errors import (
    LLMOutputQualityError,
    PipelineCInternalError,
    PipelineCStrictError,
    as_public_error,
)
from .pipeline_c.orchestrator import generate_llm_strict
from .pipeline_c.output_cleaning import strip_inline_evidence_annotations
from .pipeline_router import DEFAULT_PIPELINE_VARIANT, execute_routed_pipeline, resolve_pipeline_route
from .chat_run_runtime import get_chat_run_coordinator
from .chat_runs_store import get_chat_run_events, load_chat_run, record_chat_run_event_once, summarize_chat_run_metrics
from .chat_session_metrics import get_chat_session_metrics, update_chat_session_metrics
from .citation_resolution import (
    CANONICAL_REFERENCE_RELATION_TYPES,
    build_identity_reference_keys,
    build_mentioned_reference_keys,
    collapse_citation_payloads,
    document_reference_semantics,
    resolve_normative_mentions,
)
from .citation_gap_registry import list_citation_gaps, register_citation_gaps
from .interpretation_relevance import (
    build_decision_frame,
    build_interpretation_candidate,
    select_interpretation_candidates,
    serialize_ranked_interpretation,
)
from .clarification_orchestrator import (
    COMPARATIVE_FIELD_QUESTIONS,
    CLARIFICATION_STATE_VERSION,
    advance_state as advance_clarification_state,
    build_requirements_for_error,
    build_interaction_payload as build_clarification_interaction_payload,
    build_user_message_for_question,
    is_semantic_422_error,
    refresh_state_from_semantic_error,
    should_intercept_state as should_intercept_clarification_state,
    _llm_dynamic_clarification_decider,
    _llm_semantic_requirements_decider,
    _resolve_guided_clarification_requirements,
    _build_clarification_error_payload,
)
from .clarification_session_store import (
    clear_session_state as clear_clarification_session_state,
    get_session_state as get_clarification_session_state,
    upsert_session_state as upsert_clarification_session_state,
)
from .ui_citation_controllers import (
    _build_citation_usage_payload,
    _build_extractive_interpretation_summary,
    _build_interpretation_query_seed,
    _build_public_citation_from_row,
    _enrich_citation_payloads_with_usage_context,
    _extract_usage_context_from_answer,
    _extract_usage_context_from_diagnostics,
    _hydrate_citation_download_urls,
    _load_doc_corpus_text,
    _load_doc_index_row,
)
from .contributions import (
    Contribution,
    approve_contribution,
    list_contributions,
    reject_contribution,
    save_contribution,
)
from .feedback import FeedbackRecord, list_feedback, list_feedback_for_admin, load_feedback, save_feedback, update_feedback_comment
from .conversation_store import (
    ConversationTurn as StoredConversationTurn,
    append_turn,
    ensure_session,
    ensure_session_shell,
    list_distinct_topics,
    list_sessions,
    load_session,
    public_captcha_pass_exists,
    public_captcha_pass_record,
    update_session_metadata,
)
from .turnstile import verify_turnstile
from .jobs_store import load_job
from .platform_auth import (
    AuthContext,
    DEFAULT_PUBLIC_TOKEN_TTL_SECONDS,
    PUBLIC_TENANT_ID,
    PUBLIC_VISITOR_ROLE,
    PlatformAuthError,
    authenticate_access_token,
    exchange_host_grant,
    issue_public_visitor_token,
    load_host_integrations,
    read_bearer_token,
    switch_active_company,
)
from .runtime_env import is_production_like_env
from .expert_providers import (
    canonical_provider_name,
    extract_expert_providers,
    provider_from_domain,
    provider_labels as normalize_provider_labels,
    provider_names_from_label,
)
from .source_tiers import (
    DEFAULT_SOURCE_TIER_LABEL,
    SOURCE_TIER_KEY_EXPERTOS,
    SOURCE_TIER_KEY_NORMATIVO,
    is_practical_override_source,
    source_tier_key_for_row,
    source_tier_label_for_key,
)
from .llm_runtime import LLMRuntimeConfigInvalidError, resolve_llm_adapter
from .orchestration_settings import (
    OrchestrationSettingsInvalidError,
    load_orchestration_settings,
    update_orchestration_settings,
)
from .topic_router import resolve_chat_topic
from .ingestion_runtime import IngestionRuntime
from .instrumentation import (
    emit_event,
    emit_reasoning_event,
    estimate_token_usage_from_text,
    list_reasoning_events,
    normalize_token_usage,
    wait_reasoning_events,
)
from .normative_references import (
    extract_normative_reference_mentions,
    logical_doc_id as _shared_logical_doc_id,
    reference_identity as _reference_detail_identity,
)
from .form_guides import (
    GuideChatRequest,
    build_guide_markdown_for_pdf as _build_guide_markdown_for_pdf,
    find_official_form_pdf_source,
    list_available_guides,
    resolve_guide,
    run_guide_chat,
)
from .scope_guardrails import normalize_pais
from .terms import accept_terms, get_terms_status, read_terms_text
from .topic_guardrails import get_supported_topics, normalize_topic_key
from .ui_analysis_controllers import handle_analysis_post
from .ui_chat_context import build_clarification_scope_key, build_memory_summary
from .ui_chat_controller import (
    handle_api_chat_post,
    handle_api_chat_stream_post,
)
from .ui_chat_payload import (
    _build_public_api_error,
    _load_runtime_orchestration_settings,
    apply_api_chat_clarification,
    build_api_chat_success_payload,
    finalize_api_chat_response,
    parse_api_chat_request,
    send_api_chat_error,
)
from .ui_chat_persistence import (
    initialize_chat_request_context,
    persist_assistant_turn,
    persist_usage_events,
    persist_user_turn,
)
from .ui_route_controllers import handle_form_guides_get, handle_ops_get, handle_source_get
from .ui_write_controllers import (
    handle_chat_run_post,
    handle_corpus_operation_post,
    handle_corpus_sync_to_wip_post,
    handle_contributions_post,
    handle_embedding_operation_post,
    handle_form_guides_post,
    handle_ingestion_post,
    handle_platform_post,
    handle_promote_post,
    handle_reindex_operation_post,
    handle_reindex_post,
    handle_rollback_post,
    handle_terms_feedback_post,
)
from .usage_ledger import UsageEvent, save_usage_event, summarize_usage
from .rate_limiter import check_and_increment_daily_quota

# Module-level constants, paths, flags, regex, frozen data, public-mode config,
# `_SUSPENDED_CACHE`, and `_RATE_LIMITER` — extracted during decouplingv1 Phase 1
# to keep the handler-class split mechanical. Wildcard imports honor each
# sibling's `__all__`, so underscore-prefixed names (`_RATE_LIMITER`,
# `_SUSPENDED_CACHE`, `_NORM_REFERENCE_RE`, etc.) remain accessible to the
# handler methods below.
from .ui_server_constants import *  # noqa: F401, F403
from .ui_server_helpers import *  # noqa: F401, F403
from .ui_server_handler_base import LiaUIHandlerBase




# --- eager imports: names used in handler deps dicts (48 names) ---
from .ui_citation_profile_builders import (  # noqa: E402
    _collect_citation_profile_context, _collect_citation_profile_context_by_reference_key,
    _build_fallback_citation_profile_payload,
    _apply_citation_profile_request_context, _should_skip_citation_profile_llm,
    _llm_citation_profile_payload, _build_citation_profile_lead, _build_citation_profile_facts,
    _build_citation_profile_sections, _render_citation_profile_payload, _build_structured_vigencia_detail,
)
from .ui_source_view_processors import (  # noqa: E402
    _build_et_article_source_view_markdown, _build_source_download_filename,
    _build_source_view_href, _build_source_view_html, _build_source_view_summary_markdown,
    _build_user_source_profile, _pick_source_display_title, _render_source_view_markdown_html,
    _resolve_source_display_title, _resolve_source_view_material, _classify_provider,
    _filter_provider_links, _summarize_snippet, _dedupe_interpretation_docs,
)
from .ui_normative_processors import _render_normative_analysis_payload, _summarize_vigencia_llm  # noqa: E402
from .normative_analysis import build_normative_analysis_payload  # noqa: E402
from .ui_reference_resolvers import (  # noqa: E402
    _citation_targets_et_article, _build_normative_helper_citations, _merge_citation_payloads,
)
from .ui_expert_extractors import (  # noqa: E402
    _resolve_doc_expert_providers, _expert_card_summary, _expert_extended_excerpt,
    _expand_expert_panel_requested_refs, _prioritize_expert_panel_docs,
)
from .ui_text_utilities import (  # noqa: E402
    _build_clean_guide_markdown, _build_pdf_from_markdown, _coerce_http_url, _coerce_optional_text,
    _sanitize_question_context, _json_bytes, _safe_json_obj, _find_document_index_row,
    _load_index_rows_by_doc_id, _clip_session_content, _first_substantive_sentence,
    _logical_doc_id, _warn_missing_active_index_generation, _build_download_href,
)
from .ui_form_guide_helpers import (  # noqa: E402
    _serialize_guide_catalog_entry, _find_catalog_entry_by_reference_key, _build_form_guide_page_assets,
)
from .ui_validation_helpers import _validate_pipeline_c_payload  # noqa: E402

# --- lazy re-exports for backward compat (175 names, resolved via __getattr__) ---
_REEXPORT_SOURCES: dict[str, str] = {}
for _mod, _names in {
    "ui_citation_profile_builders": "_normalize_citation_profile_text _collect_citation_profile_texts _find_grounded_profile_sentence _classify_document_family _format_citation_profile_date _latest_identified_citation_profile_date _extract_normative_year _official_publish_date_or_year _resolve_superseded_label _build_citation_profile_prompt _append_citation_profile_fact _resolve_companion_action _resolve_analysis_action _resolve_source_action _citation_profile_display_title _citation_locator_reference_keys _citation_profile_analysis_candidates _extract_locator_excerpt_from_text _summarize_analysis_excerpt _build_citation_profile_original_text_section _build_citation_profile_expert_section _build_structured_original_text _build_structured_expert_comment",
    "ui_form_citation_profile": "_row_looks_like_guide _extract_citation_profile_form_number _spanish_title_case _format_form_reference_title _resolve_form_guide_package_for_context _deterministic_form_citation_profile",
    "ui_source_view_processors": "_guide_primary_source_payload _source_view_provenance_uri _collect_source_view_candidate_rows _load_source_text _pick_local_source_file _build_source_view_candidate_analysis _build_source_query_profile _extract_source_chunks _normalize_source_view_field_value _infer_source_reference_anchor _text_refers_to_source_document _anchor_source_view_text _anchor_source_view_summary_payload _build_source_view_summary_prompt _llm_source_view_summary_payload _render_source_view_summary_markdown _build_source_view_summary_markdown _extract_outbound_links",
    "ui_source_view_html": "_sanitize_source_view_href _render_source_view_inline_markdown _render_source_view_markdown_html _build_source_view_html _build_source_view_href",
    "ui_source_view_noise_filter": "_SOURCE_VIEW_CONTENT_MARKERS _SOURCE_VIEW_NON_USABLE_HINTS _SOURCE_VIEW_HTML_NOISE_HINTS _SOURCE_VIEW_USEFUL_HINT_RE _trim_source_view_content_markers _is_source_view_noise_text _extract_source_view_usable_text",
    "ui_source_title_resolver": "_SOURCE_FORM_REFERENCE_RE _SOURCE_ARTICLE_ID_LINE_RE _SOURCE_HEADING_LINE_RE _TECHNICAL_PREFIX_TOKEN_RE _source_url_label_for_filename _build_source_download_filename _is_generic_source_title _extract_source_title_from_raw_text _infer_source_title_from_url_or_path _resolve_source_display_title _title_from_normative_identity _pick_source_display_title _looks_like_technical_title _humanize_technical_title _normalize_source_reference_text",
    "ui_normative_processors": "ET_ARTICLE_ADDITIONAL_DEPTH_PATH _is_broad_normative_reference_title _resolve_et_locator_row _resolve_et_locator_analysis _article_heading_pattern _extract_et_article_quote_from_markdown _extract_et_article_metadata _extract_et_article_summary _build_et_article_vigencia_detail _load_et_article_additional_depth _et_article_additional_depth_for_doc_id _resolve_et_additional_depth_sections _resolve_ley_additional_depth_sections _interpretive_display_label _build_structured_additional_depth_sections _clean_practica_label _best_practica_display_label",
    "ui_reference_resolvers": "_NORMATIVE_HELPER_KNOWLEDGE_CLASSES _NORMATIVO_HELPER_SOURCE_TYPES _STRICT_NORMATIVO_HELPER_SOURCE_TYPES _MENTION_KEY_PREFIX_TO_ALLOWED_FAMILIES _reference_label_from_key _find_reference_doc_id _extract_reference_identities_from_citation_payload _extract_reference_identities_from_text _extract_reference_keys_from_text _citation_matches_reference_mentions _document_family_from_row _is_cross_type_mention_mismatch _resolve_mention_citations _select_reference_detail_identity_for_citation _build_reference_detail_title _build_reference_detail_resolution_text _drop_base_citations_shadowed_by_locators _apply_reference_detail_to_citation _is_normative_helper_normativo_citation _filter_normative_helper_citations _citation_targets_ley _citation_et_locator_key _citation_et_locator_label",
    "ui_expert_extractors": "_normalize_query_tokens _expert_chunk_candidates _expert_chunk_matches_article _expert_chunk_matches_topic _derive_expert_topic_label _find_expert_provider_link _canonicalize_expert_panel_ref _extract_expert_anchor_excerpt _clean_expert_summary_paragraph _clip_expert_summary _expert_excerpt_paragraphs _expert_detail_excerpt",
    "ui_text_utilities": "_MARKDOWN_BULLET_KV_RE _LOCAL_UPLOAD_URL_RE _NORMALIZED_INGEST_DOC_ID_RE _URL_TRAILING_PUNCT _sb_find_document_row _prefer_normograma_mintic_mirror _index_file_signature _load_index_rows_by_doc_id_cached _looks_like_html_document _resolve_knowledge_file _parse_local_upload_url _derive_ingestion_upload_doc_id _resolve_local_upload_artifact _slugify_filename_part _sanitize_url_candidate _clean_markdown_inline _parse_markdown_sections _markdown_section_map _extract_markdown_bullet_metadata _extract_markdown_primary_body_text _reference_doc_catalog _row_is_active_or_canonical _extract_reference_keys_from_citation_payload _reference_base_text_for_request_context _extract_public_reference_text _extract_visible_text_from_html _row_lifecycle_rank _row_curation_rank _extract_named_plain_section_body _SOURCE_BASE_SUMMARY_HEADING_RE _SOURCE_INTERNAL_BOUNDARY_RE _SOURCE_METADATA_LINE_RE",
    "ui_chunk_relevance": "_SUMMARY_STOPWORDS _SUMMARY_INTENT_KEYWORDS _SENTENCE_ABBREVIATION_RE _SENTENCE_ABBR_PLACEHOLDER _CITATION_TAIL_RE _CITATION_HEAD_RE _extract_candidate_paragraphs _sanitize_question_context _tokenize_relevance_text _detect_intent_tags _score_chunk_relevance _looks_like_reference_list _split_sentences _pick_summary_sentences _select_diverse_chunks _first_substantive_sentence _flatten_markdown_to_text",
    "ui_chunk_assembly": "_CHUNK_CONTEXT_PREFIX_RE _MAX_HEADING_LINE_CHARS _strip_chunk_context_prefix _match_heading_label _reconstruct_chunk_markdown _sb_query_document_chunks _sb_assemble_document_markdown _sb_assemble_document_markdown_cached",
    "ui_form_guide_helpers": "_extract_form_guide_page_number _build_form_guide_asset_href",
    "ui_validation_helpers": "_validate_chat_payload _reject_unknown_keys _normalize_csv_like_tuple _validate_optional_enum_value _validate_chat_top_level_fields _validate_access_context_payload _validate_company_context_payload _validate_chat_optional_fields _coerce_limit_int _coerce_limit_float _resolve_chat_limits _validate_chat_payload_with_limits _parse_access_context _parse_company_context _parse_conversation",
    "clarification_orchestrator": "_llm_dynamic_clarification_decider _llm_semantic_requirements_decider _resolve_guided_clarification_requirements _build_clarification_error_payload",
    "ui_chat_payload": "_build_public_api_error _load_runtime_orchestration_settings",
}.items():
    for _n in _names.split():
        _REEXPORT_SOURCES[_n] = _mod


def __getattr__(name: str) -> Any:
    mod_name = _REEXPORT_SOURCES.get(name)
    if mod_name is not None:
        import importlib
        mod = importlib.import_module(f".{mod_name}", __package__)
        val = getattr(mod, name)
        globals()[name] = val
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# _extract_usage_context_from_diagnostics, _extract_usage_context_from_answer,
# _build_citation_usage_payload, _enrich_citation_payloads_with_usage_context,
# _load_doc_index_row, _load_doc_corpus_text, _build_public_citation_from_row,
# _hydrate_citation_download_urls, _build_interpretation_query_seed,
# _build_extractive_interpretation_summary
# → moved to ui_citation_controllers.py (Phase 1 decouple-v1)



# Controller-dependency factories extracted to `ui_server_deps.py` during
# granularize-v2 round 20. Re-imported for back-compat so the handler's
# `write_deps = _write_controller_deps()` style call sites continue to work.
from .ui_server_deps import (  # noqa: F401,E402
    _analysis_controller_deps,
    _chat_controller_deps,
    _frontend_compat_controller_deps,
    _public_session_controller_deps,
    _write_controller_deps,
)



class LiaUIHandler(LiaUIHandlerBase):
    def do_GET(self) -> None:  # noqa: N802
        self._start_api_request_log("GET")
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/health":
            self._send_json(
                HTTPStatus.OK,
                {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()},
            )
            return

        # Public visitor entry point — `/public` and `/public.html` always go
        # through the dedicated handler so we can inject the per-IP token meta.
        if path in ("/public", "/public.html"):
            self._serve_public_page()
            return

        if self._handle_chat_frontend_compat_get(path, parsed):
            return

        if self._resolve_ui_asset_path(path) is not None:
            self._serve_ui_asset(path)
            return

        # User management admin + invite acceptance
        from .ui_user_management_controllers import handle_user_management_get
        if handle_user_management_get(self, path, parsed, deps={}):
            return

        # Eval API (robot / admin)
        if path.startswith("/api/eval/"):
            from .ui_eval_controllers import handle_eval_get
            if handle_eval_get(self, path, parsed, deps={}):
                return

        if self._handle_platform_get(path, parsed):
            return
        if self._handle_ops_get(path, parsed):
            return
        if self._handle_reasoning_get(path, parsed):
            return
        if self._handle_ingestion_get(path, parsed):
            return
        if self._handle_ingest_run_get(path, parsed):
            return
        if self._handle_runtime_terms_get(path):
            return
        if self._handle_citation_get(path, parsed):
            return
        if self._handle_source_get(path, parsed):
            return
        if self._handle_history_get(path, parsed):
            return
        if self._handle_form_guides_get(path, parsed):
            return

        from .ui_subtopic_controllers import handle_subtopic_get
        if handle_subtopic_get(self, path, parsed, deps={"workspace_root": WORKSPACE_ROOT}):
            return

        self._serve_ui_asset(path)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._start_api_request_log("OPTIONS")
        self.send_response(HTTPStatus.NO_CONTENT)
        for key, value in self._cors_headers().items():
            self.send_header(key, value)
        self.send_header("Content-Length", "0")
        self.end_headers()
        self._log_api_response(status=HTTPStatus.NO_CONTENT, content_type=None)

    def _handle_ops_get(self, path: str, parsed: Any) -> bool:
        return handle_ops_get(
            self,
            path,
            parsed,
            deps={
                "build_info_payload": _build_info_payload,
                "chat_run_route_re": _CHAT_RUN_ROUTE_RE,
                "chat_runs_path": CHAT_RUNS_PATH,
                "chat_session_metrics_path": CHAT_SESSION_METRICS_PATH,
                "chat_session_metrics_route_re": _CHAT_SESSION_METRICS_ROUTE_RE,
                "citation_gap_registry_path": CITATION_GAP_REGISTRY_PATH,
                "get_chat_run": load_chat_run,
                "get_chat_run_coordinator": get_chat_run_coordinator,
                "get_chat_run_events": get_chat_run_events,
                "get_chat_session_metrics": get_chat_session_metrics,
                "get_pipeline_c_run": get_pipeline_c_run,
                "get_pipeline_c_timeline": get_pipeline_c_timeline,
                "jobs_path": JOBS_RUNTIME_PATH,
                "list_citation_gaps": list_citation_gaps,
                "list_pipeline_c_runs": list_pipeline_c_runs,
                "load_runtime_orchestration_settings": _load_runtime_orchestration_settings,
                "ops_run_route_re": _OPS_RUN_ROUTE_RE,
                "ops_run_timeline_route_re": _OPS_RUN_TIMELINE_ROUTE_RE,
                "orchestration_settings_invalid_error": OrchestrationSettingsInvalidError,
                "summarize_chat_run_metrics": summarize_chat_run_metrics,
                "workspace_root": WORKSPACE_ROOT,
            },
        )

    def _handle_reasoning_get(self, path: str, parsed: Any) -> bool:
        from .ui_reasoning_controllers import handle_reasoning_get
        return handle_reasoning_get(self, path, parsed, deps={
            "list_reasoning_events": list_reasoning_events,
            "wait_reasoning_events": wait_reasoning_events,
        })

    def _handle_ingestion_get(self, path: str, parsed: Any) -> bool:
        from .ui_ingestion_controllers import handle_ingestion_get
        return handle_ingestion_get(self, path, parsed, deps={"ingestion_runtime": INGESTION_RUNTIME})

    def _handle_ingest_run_get(self, path: str, parsed: Any) -> bool:
        from .ui_ingest_run_controllers import handle_ingest_get
        return handle_ingest_get(self, path, parsed, deps={"workspace_root": WORKSPACE_ROOT})

    def _handle_runtime_terms_get(self, path: str) -> bool:
        from .ui_runtime_controllers import handle_runtime_terms_get
        return handle_runtime_terms_get(self, path, deps={
            "resolve_llm_adapter": resolve_llm_adapter,
            "LLMRuntimeConfigInvalidError": LLMRuntimeConfigInvalidError,
            "emit_event": emit_event,
            "get_terms_status": get_terms_status,
            "read_terms_text": read_terms_text,
            "llm_runtime_config_path": LLM_RUNTIME_CONFIG_PATH,
            "terms_policy_path": TERMS_POLICY_PATH,
            "terms_state_path": TERMS_STATE_PATH,
        })

    def _handle_citation_get(self, path: str, parsed: Any) -> bool:
        from .ui_citation_controllers import handle_citation_get
        return handle_citation_get(self, path, parsed, deps={
            "collect_citation_profile_context": _collect_citation_profile_context,
            "collect_citation_profile_context_by_reference_key": _collect_citation_profile_context_by_reference_key,
            "build_fallback_citation_profile_payload": _build_fallback_citation_profile_payload,
            "apply_citation_profile_request_context": _apply_citation_profile_request_context,
            "should_skip_citation_profile_llm": _should_skip_citation_profile_llm,
            "llm_citation_profile_payload": _llm_citation_profile_payload,
            "build_citation_profile_lead": _build_citation_profile_lead,
            "build_citation_profile_facts": _build_citation_profile_facts,
            "build_citation_profile_sections": _build_citation_profile_sections,
            "render_citation_profile_payload": _render_citation_profile_payload,
            "render_normative_analysis_payload": _render_normative_analysis_payload,
            "build_structured_vigencia_detail": _build_structured_vigencia_detail,
            "summarize_vigencia_llm": _summarize_vigencia_llm,
            "citation_targets_et_article": _citation_targets_et_article,
            "index_file_path": INDEX_FILE_PATH,
        })

    def _handle_source_get(self, path: str, parsed: Any) -> bool:
        return handle_source_get(
            self,
            path,
            parsed,
            deps={
                "build_clean_guide_markdown": _build_clean_guide_markdown,
                "build_et_article_source_view_markdown": _build_et_article_source_view_markdown,
                "build_pdf_from_markdown": _build_pdf_from_markdown,
                "build_source_download_filename": _build_source_download_filename,
                "build_source_view_href": _build_source_view_href,
                "build_source_view_html": _build_source_view_html,
                "build_source_view_summary_markdown": _build_source_view_summary_markdown,
                "build_user_source_profile": _build_user_source_profile,
                "coerce_http_url": _coerce_http_url,
                "coerce_optional_text": _coerce_optional_text,
                "pick_source_display_title": _pick_source_display_title,
                "render_source_view_markdown_html": _render_source_view_markdown_html,
                "resolve_source_display_title": _resolve_source_display_title,
                "resolve_source_view_material": _resolve_source_view_material,
                "is_et_article_doc_id": lambda doc_id: bool(_ET_ARTICLE_DOC_ID_RE.match(str(doc_id or "").strip())),
                "sanitize_question_context": _sanitize_question_context,
            },
        )

    def _handle_platform_get(self, path: str, parsed: Any) -> bool:
        from .conversation_store import summarize_public_usage
        from .ui_admin_controllers import handle_platform_get
        return handle_platform_get(self, path, parsed, deps={
            "summarize_usage": summarize_usage,
            "summarize_public_usage": summarize_public_usage,
            "list_feedback": list_feedback,
            "list_feedback_for_admin": list_feedback_for_admin,
            "load_job": load_job,
            "usage_events_path": USAGE_EVENTS_PATH,
            "feedback_path": FEEDBACK_PATH,
            "jobs_runtime_path": JOBS_RUNTIME_PATH,
            "corpus_jobs_runtime_path": CORPUS_JOBS_RUNTIME_PATH,
            "user_errors_path": USER_ERROR_LOG_PATH,
        })

    def _handle_history_get(self, path: str, parsed: Any) -> bool:
        from .ui_conversation_controllers import handle_history_get
        return handle_history_get(self, path, parsed, deps={
            "load_feedback": load_feedback,
            "load_session": load_session,
            "list_sessions": list_sessions,
            "list_distinct_topics": list_distinct_topics,
            "list_contributions": list_contributions,
            "conversations_path": CONVERSATIONS_PATH,
            "feedback_path": FEEDBACK_PATH,
            "workspace_root": WORKSPACE_ROOT,
        })

    def _handle_form_guides_get(self, path: str, parsed: Any) -> bool:
        return handle_form_guides_get(
            self,
            path,
            parsed,
            form_guides_root=FORM_GUIDES_ROOT,
            deps={
                "build_form_guide_page_assets": _build_form_guide_page_assets,
                "build_guide_markdown_for_pdf": _build_guide_markdown_for_pdf,
                "coerce_http_url": _coerce_http_url,
                "find_catalog_entry_by_reference_key": _find_catalog_entry_by_reference_key,
                "find_official_form_pdf_source": find_official_form_pdf_source,
                "list_available_guides": list_available_guides,
                "resolve_guide": resolve_guide,
                "serialize_guide_catalog_entry": _serialize_guide_catalog_entry,
            },
        )

    def _resolve_ui_asset_path(self, path: str) -> Path | None:
        if path in {"/", "/index.html"}:
            file_path = UI_DIR / "index.html"
        elif path in {"/login", "/login.html"}:
            file_path = UI_DIR / "login.html"
        elif path in {"/invite", "/invite.html"}:
            file_path = UI_DIR / "invite.html"
        elif path in {"/ops", "/ops.html"}:
            file_path = UI_DIR / "ops.html"
        elif path in {"/embed", "/embed.html"}:
            file_path = UI_DIR / "embed.html"
        elif path in {"/admin", "/admin.html"}:
            file_path = UI_DIR / "admin.html"
        elif path in {"/form-guide", "/form-guide.html"}:
            file_path = UI_DIR / "form-guide.html"
        elif path in {"/normative-analysis", "/normative-analysis.html"}:
            file_path = UI_DIR / "normative-analysis.html"
        elif path in {"/orchestration", "/orchestration.html"}:
            file_path = UI_DIR / "orchestration.html"
        else:
            rel = path.lstrip("/")
            file_path = UI_DIR / rel

        ui_root = UI_DIR.resolve()
        try:
            resolved_path = file_path.resolve()
        except OSError:
            return None
        if not resolved_path.exists() or not resolved_path.is_file() or ui_root not in resolved_path.parents:
            return None
        return resolved_path

    def _serve_ui_asset(self, path: str) -> None:
        file_path = self._resolve_ui_asset_path(path)
        if file_path is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Recurso no encontrado."})
            return

        content_type, _ = mimetypes.guess_type(str(file_path))
        body = file_path.read_bytes()
        # Vite hashed assets (ui/assets/*) are immutable — cache aggressively.
        # HTML files must always be re-validated to pick up new asset hashes.
        is_hashed_asset = "/assets/" in path and any(path.endswith(ext) for ext in (".js", ".css"))
        if is_hashed_asset:
            extra_headers = {"Cache-Control": "public, max-age=31536000, immutable"}
        else:
            extra_headers = {
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            }
        if path in {"/embed", "/embed.html"}:
            extra_headers.update(self._embed_security_headers())
        self._send_bytes(
            HTTPStatus.OK,
            body,
            f"{content_type or 'application/octet-stream'}; charset=utf-8",
            extra_headers=extra_headers,
        )

    def do_PUT(self) -> None:  # noqa: N802
        self._start_api_request_log("PUT")
        from .ui_runtime_controllers import handle_orchestration_settings_put
        handle_orchestration_settings_put(self, deps={
            "update_orchestration_settings": update_orchestration_settings,
            "orchestration_settings_path": ORCHESTRATION_SETTINGS_PATH,
        })

    def do_POST(self) -> None:  # noqa: N802
        self._start_api_request_log("POST")
        parsed = urlparse(self.path)
        path = (parsed.path or "/").rstrip("/") or "/"

        # Public visitor session minting — handled before any other dispatch.
        # This route is opt-in via `LIA_PUBLIC_MODE_ENABLED` and rate-limited
        # to 5 req/min/IP so an attacker cannot drain the captcha verifier.
        if path == "/api/public/session":
            if self._check_rate_limit("public_session", 5, 60):
                return
            self._handle_public_session_post()
            return

        # Rate limiting on sensitive endpoints
        if path in ("/api/embed/exchange", "/api/auth/exchange"):
            if self._check_rate_limit("auth_exchange", 10, 60):
                return
        elif path == "/api/auth/login":
            if self._check_rate_limit("auth_login", 10, 60):
                return
        elif path in ("/api/chat", "/api/chat/stream"):
            # Public visitors get a stricter burst + persistent daily quota
            # and skip the authenticated 30/60 ceiling. Authenticated users
            # follow the historical limit unchanged.
            if self._is_public_visitor_request():
                if self._check_rate_limit("public_chat_burst", PUBLIC_CHAT_BURST_RPM, 60):
                    return
                pub_user_id = self._hash_public_user_id(self._get_trusted_client_ip())
                if self._check_public_daily_quota(pub_user_id):
                    return
            else:
                if self._check_rate_limit("chat", 30, 60):
                    return
        elif path in {"/api/invite/accept", "/api/auth/accept-invite"}:
            if self._check_rate_limit("invite_accept", 10, 60):
                return
        elif path.startswith("/api/eval/"):
            # Per-endpoint eval rate limits
            if path == "/api/eval/ask":
                if self._check_rate_limit("eval_ask", 300, 60):
                    return
            elif path == "/api/eval/ask/batch":
                if self._check_rate_limit("eval_ask_batch", 10, 60):
                    return
            elif path == "/api/eval/service-accounts" or path.startswith("/api/eval/service-accounts/"):
                if self._check_rate_limit("eval_svc_accounts", 30, 60):
                    return
            elif path in ("/api/eval/reviews", "/api/eval/rankings", "/api/eval/diagnoses"):
                if self._check_rate_limit("eval_judgments", 600, 60):
                    return
            else:
                if self._check_rate_limit("eval_runs", 120, 60):
                    return

        if path == "/api/chat/stream":
            handle_api_chat_stream_post(self, deps=_chat_controller_deps())
            return

        if path == "/api/chat":
            handle_api_chat_post(self, deps=_chat_controller_deps())
            return

        if self._handle_chat_frontend_compat_post(path):
            return

        write_deps = _write_controller_deps()

        # User management admin endpoints
        from .ui_user_management_controllers import handle_user_management_post
        if handle_user_management_post(self, path, deps=write_deps):
            return

        if handle_platform_post(self, path, deps=write_deps):
            return
        if handle_chat_run_post(self, path, deps=write_deps):
            return
        if handle_form_guides_post(self, path, deps=write_deps):
            return
        if handle_terms_feedback_post(self, path, deps=write_deps):
            return
        if handle_contributions_post(self, path, deps=write_deps):
            return
        if handle_ingestion_post(self, path, deps=write_deps):
            return
        from .ui_ingest_run_controllers import handle_ingest_post as _handle_ingest_run_post
        if _handle_ingest_run_post(self, path, deps={"workspace_root": WORKSPACE_ROOT}):
            return
        from .ui_subtopic_controllers import handle_subtopic_post
        if handle_subtopic_post(self, path, deps={"workspace_root": WORKSPACE_ROOT}):
            return
        if handle_reindex_post(self, path, deps=write_deps):
            return
        if handle_corpus_sync_to_wip_post(self, path, deps=write_deps):
            return
        if handle_corpus_operation_post(self, path, deps=write_deps):
            return
        if handle_embedding_operation_post(self, path, deps=write_deps):
            return
        if handle_reindex_operation_post(self, path, deps=write_deps):
            return
        if handle_promote_post(self, path, deps=write_deps):
            return
        if handle_rollback_post(self, path, deps=write_deps):
            return

        if handle_analysis_post(self, path, deps=_analysis_controller_deps()):
            return

        # Eval API (robot / admin)
        if path.startswith("/api/eval/"):
            from .ui_eval_controllers import handle_eval_post
            if handle_eval_post(self, path, deps=_chat_controller_deps()):
                return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Endpoint no encontrado."})

    def do_PATCH(self) -> None:  # noqa: N802
        """Enruta PATCH como POST para endpoints de ingestion y eval que usan PATCH semantico."""
        self._start_api_request_log("PATCH")
        parsed = urlparse(self.path)
        path = (parsed.path or "/").rstrip("/") or "/"

        # Eval PATCH (run status updates)
        if path.startswith("/api/eval/"):
            from .ui_eval_controllers import handle_eval_patch
            if handle_eval_patch(self, path, deps={}):
                return

        write_deps = _write_controller_deps()
        if handle_ingestion_post(self, path, deps=write_deps):
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Endpoint no encontrado."})

    def do_DELETE(self) -> None:  # noqa: N802
        self._start_api_request_log("DELETE")
        parsed = urlparse(self.path)
        path = (parsed.path or "/").rstrip("/") or "/"

        # Eval DELETE (revoke service account)
        if path.startswith("/api/eval/"):
            from .ui_eval_controllers import handle_eval_delete
            if handle_eval_delete(self, path, deps={}):
                return

        from .ui_ingestion_controllers import handle_ingestion_delete
        if handle_ingestion_delete(self, path, deps={"ingestion_runtime": INGESTION_RUNTIME}):
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Endpoint no encontrado."})

    def _send_api_chat_error(
        self,
        *,
        t_api_chat: float,
        trace_id: str | None,
        status: HTTPStatus,
        code: str,
        message: str,
        stage: str,
        remediation: list[str] | tuple[str, ...],
        diagnostics: dict[str, Any] | None = None,
        llm_runtime: dict[str, Any] | None = None,
        run_id: str | None = None,
    ) -> None:
        send_api_chat_error(
            self,
            t_api_chat=t_api_chat,
            trace_id=trace_id,
            status=status,
            code=code,
            message=message,
            stage=stage,
            remediation=remediation,
            diagnostics=diagnostics,
            llm_runtime=llm_runtime,
            run_id=run_id,
            deps=_chat_controller_deps(),
        )

    def _parse_api_chat_request(self, *, t_api_chat: float) -> dict[str, Any] | None:
        return parse_api_chat_request(self, t_api_chat=t_api_chat, deps=_chat_controller_deps())

    def _apply_api_chat_clarification(
        self,
        *,
        request_context: dict[str, Any],
        t_api_chat: float,
    ) -> bool:
        return apply_api_chat_clarification(
            self,
            request_context=request_context,
            t_api_chat=t_api_chat,
            deps=_chat_controller_deps(),
        )

    def _build_api_chat_success_payload(
        self,
        *,
        request_context: dict[str, Any],
        response: Any,
        t_api_chat: float,
    ) -> dict[str, Any]:
        return build_api_chat_success_payload(
            request_context=request_context,
            response=response,
            t_api_chat=t_api_chat,
            deps=_chat_controller_deps(),
        )

    def _finalize_api_chat_response(
        self,
        *,
        request_context: dict[str, Any],
        response: Any,
        t_api_chat: float,
    ) -> None:
        finalize_api_chat_response(
            self,
            request_context=request_context,
            response=response,
            t_api_chat=t_api_chat,
            deps=_chat_controller_deps(),
        )

    def _handle_api_chat_post(self) -> None:
        handle_api_chat_post(self, deps=_chat_controller_deps())

    def _handle_api_chat_stream_post(self) -> None:
        handle_api_chat_stream_post(self, deps=_chat_controller_deps())


def run_server(
    host: str = "127.0.0.1",
    port: int = 8787,
    *,
    reload: bool = False,
    reload_interval_seconds: float = 1.0,
) -> int:
    server = ThreadingHTTPServer((host, port), LiaUIHandler)
    stop_event: threading.Event | None = None
    reload_event: threading.Event | None = None
    watcher: threading.Thread | None = None
    if reload:
        watch_roots = (
            WORKSPACE_ROOT / "src" / "lia_graph",
            WORKSPACE_ROOT / "ui",
        )
        stop_event, reload_event, watcher = _start_reload_watcher(
            server=server,
            watch_roots=watch_roots,
            interval_seconds=max(0.2, float(reload_interval_seconds)),
        )
    print(f"LIA UI disponible en http://{host}:{port}")
    if reload:
        print("Modo reload activo: el servidor se detiene cuando detecta cambios de código.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if stop_event is not None:
            stop_event.set()
        if watcher is not None:
            watcher.join(timeout=1.0)
        server.server_close()
    if reload and reload_event is not None and reload_event.is_set():
        print("Cambio detectado. Saliendo con código 3 para reinicio automático.")
        return 3
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Servidor local de UI para chat con LIA")
    p.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.getenv("PORT", "8787")))
    p.add_argument("--reload", action="store_true", help="Auto-detener servidor al detectar cambios en src/ui.")
    p.add_argument(
        "--reload-interval-seconds",
        type=float,
        default=1.0,
        help="Frecuencia de sondeo para modo reload (segundos).",
    )
    return p


def main() -> int:
    from .env_loader import load_dotenv_if_present
    load_dotenv_if_present()
    args = parser().parse_args()
    reload_enabled = bool(getattr(args, "reload", False))
    reload_interval = float(getattr(args, "reload_interval_seconds", 1.0))
    try:
        outcome = run_server(
            host=args.host,
            port=args.port,
            reload=reload_enabled,
            reload_interval_seconds=reload_interval,
        )
        return int(outcome) if isinstance(outcome, int) else 0
    except TypeError as exc:
        if "unexpected keyword argument 'reload'" not in str(exc):
            raise
        legacy_outcome = run_server(host=args.host, port=args.port)  # type: ignore[misc]
        return int(legacy_outcome) if isinstance(legacy_outcome, int) else 0


if __name__ == "__main__":
    raise SystemExit(main())
