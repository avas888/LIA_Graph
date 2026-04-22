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



from .ui_server_handler_dispatch import LiaUIHandler  # noqa: F401, E402

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
