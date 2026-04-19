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

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
UI_DIR = WORKSPACE_ROOT / "ui"
FRONTEND_DIR = WORKSPACE_ROOT / "frontend"
TERMS_POLICY_PATH = WORKSPACE_ROOT / "config/terms_of_use.json"
TERMS_STATE_PATH = WORKSPACE_ROOT / "artifacts/terms/accepted_terms_state.json"
_runtime_config_env = Path(os.getenv("LIA_LLM_RUNTIME_CONFIG_PATH", "config/llm_runtime.json"))
LLM_RUNTIME_CONFIG_PATH = _runtime_config_env if _runtime_config_env.is_absolute() else (WORKSPACE_ROOT / _runtime_config_env)
ORCHESTRATION_SETTINGS_PATH = WORKSPACE_ROOT / "artifacts/runtime/orchestration_profiles.json"
SUPPORTED_TOPICS = get_supported_topics()
INDEX_FILE_PATH = WORKSPACE_ROOT / "artifacts/document_index.jsonl"
KNOWLEDGE_BASE_ROOT = WORKSPACE_ROOT / "knowledge_base"
INGESTION_RUNTIME = IngestionRuntime(
    workspace_root=WORKSPACE_ROOT,
    knowledge_base_root=KNOWLEDGE_BASE_ROOT,
    manifest_path=WORKSPACE_ROOT / "knowledge_base/manifests/document_manifest.csv",
    index_output_file=WORKSPACE_ROOT / "artifacts/document_index.jsonl",
)
INGESTION_ARTIFACTS_ROOT = WORKSPACE_ROOT / "artifacts" / "ingestion"
INGESTION_PROCESSED_ROOT = INGESTION_ARTIFACTS_ROOT / "processed"
INGESTION_UPLOADS_ROOT = INGESTION_ARTIFACTS_ROOT / "uploads"
VERBOSE_CHAT_LOG_PATH = WORKSPACE_ROOT / "logs" / "chat_verbose.jsonl"
API_AUDIT_LOG_PATH = WORKSPACE_ROOT / "logs" / "api_audit.jsonl"
USER_ERROR_LOG_PATH = WORKSPACE_ROOT / "logs" / "user_errors.jsonl"
CHAT_SESSION_METRICS_PATH = WORKSPACE_ROOT / "artifacts" / "runtime" / "chat_session_metrics.json"
CITATION_GAP_REGISTRY_PATH = WORKSPACE_ROOT / "artifacts" / "runtime" / "citation_gap_registry.json"
FORM_GUIDES_ROOT = WORKSPACE_ROOT / "knowledge_base" / "form_guides"
ACTIVE_INDEX_GENERATION_PATH = WORKSPACE_ROOT / "artifacts" / "runtime" / "active_index_generation.json"
CLARIFICATION_SESSIONS_PATH = WORKSPACE_ROOT / "artifacts" / "runtime" / "clarification_sessions.json"
CONVERSATIONS_PATH = WORKSPACE_ROOT / "artifacts" / "conversations"
FEEDBACK_PATH = WORKSPACE_ROOT / "artifacts" / "feedback"
EXPERT_SUMMARY_OVERRIDES_PATH = WORKSPACE_ROOT / "artifacts" / "expert_summary_overrides"
HOST_INTEGRATIONS_CONFIG_PATH = WORKSPACE_ROOT / "config" / "host_integrations.json"
AUTH_NONCES_PATH = WORKSPACE_ROOT / "artifacts" / "runtime" / "auth_nonces.json"
USAGE_EVENTS_PATH = WORKSPACE_ROOT / "artifacts" / "usage"
JOBS_RUNTIME_PATH = WORKSPACE_ROOT / "artifacts" / "jobs" / "runtime"
CORPUS_JOBS_RUNTIME_PATH = WORKSPACE_ROOT / "artifacts" / "jobs" / "corpus_runtime"
CHAT_RUNS_PATH = WORKSPACE_ROOT / "artifacts" / "runtime" / "chat_runs"
SERVER_STARTED_AT = datetime.now(timezone.utc).isoformat()

_INGESTION_SESSION_ROUTE_RE = re.compile(r"^/api/ingestion/sessions/([^/]+)$")
_INGESTION_FILES_ROUTE_RE = re.compile(r"^/api/ingestion/sessions/([^/]+)/files$")
_INGESTION_PROCESS_ROUTE_RE = re.compile(r"^/api/ingestion/sessions/([^/]+)/process$")
_INGESTION_RETRY_ROUTE_RE = re.compile(r"^/api/ingestion/sessions/([^/]+)/retry$")
_INGESTION_VALIDATE_BATCH_ROUTE_RE = re.compile(r"^/api/ingestion/sessions/([^/]+)/validate-batch$")
_INGESTION_DELETE_FAILED_ROUTE_RE = re.compile(r"^/api/ingestion/sessions/([^/]+)/delete-failed$")
_INGESTION_STOP_ROUTE_RE = re.compile(r"^/api/ingestion/sessions/([^/]+)/stop$")
_INGESTION_CLEAR_BATCH_ROUTE_RE = re.compile(r"^/api/ingestion/sessions/([^/]+)/clear$")
_INGESTION_DELETE_SESSION_ROUTE_RE = re.compile(r"^/api/ingestion/sessions/([^/]+)$")
_OPS_RUN_ROUTE_RE = re.compile(r"^/api/ops/runs/([^/]+)$")
_OPS_RUN_TIMELINE_ROUTE_RE = re.compile(r"^/api/ops/runs/([^/]+)/timeline$")
_CHAT_SESSION_METRICS_ROUTE_RE = re.compile(r"^/api/chat/sessions/([^/]+)/metrics$")
from .rate_limiter import InMemoryRateLimiter, check_and_increment_daily_quota

_RATE_LIMITER = InMemoryRateLimiter()


def _env_truthy(name: str, default: str = "0") -> bool:
    return str(os.getenv(name, default)).strip().lower() in {"1", "true", "yes", "on"}


# ── Public visitor mode ──────────────────────────────────────────────
# Master kill switch + supporting config for the no-login `/public` chat URL.
# When `PUBLIC_MODE_ENABLED` is False, every public surface returns 503 and
# `_resolve_auth_context` actively rejects public_visitor JWTs even if signed.
_PUBLIC_RUNTIME_IS_PRODUCTION = is_production_like_env()
PUBLIC_MODE_ENABLED = _env_truthy("LIA_PUBLIC_MODE_ENABLED", "0" if _PUBLIC_RUNTIME_IS_PRODUCTION else "1")
PUBLIC_TRUST_PROXY = _env_truthy("LIA_TRUST_PROXY", "0")
PUBLIC_USER_SALT = str(os.getenv("LIA_PUBLIC_USER_SALT", "")).strip()
if PUBLIC_MODE_ENABLED and not PUBLIC_USER_SALT and not _PUBLIC_RUNTIME_IS_PRODUCTION:
    PUBLIC_USER_SALT = "lia-public-dev-salt"
PUBLIC_CHAT_BURST_RPM = int(str(os.getenv("LIA_PUBLIC_CHAT_BURST_RPM", "10")).strip() or "10")
PUBLIC_CHAT_DAILY_CAP = int(str(os.getenv("LIA_PUBLIC_CHAT_DAILY_CAP", "100")).strip() or "100")
PUBLIC_TOKEN_TTL_SECONDS = int(
    str(os.getenv("LIA_PUBLIC_TOKEN_TTL_SECONDS", str(DEFAULT_PUBLIC_TOKEN_TTL_SECONDS))).strip()
    or str(DEFAULT_PUBLIC_TOKEN_TTL_SECONDS)
)
PUBLIC_TURNSTILE_SITE_KEY = str(os.getenv("LIA_PUBLIC_TURNSTILE_SITE_KEY", "")).strip()
PUBLIC_TURNSTILE_SECRET = str(os.getenv("LIA_PUBLIC_TURNSTILE_SECRET_KEY", "")).strip()
PUBLIC_CAPTCHA_ENABLED = PUBLIC_MODE_ENABLED and _PUBLIC_RUNTIME_IS_PRODUCTION

if PUBLIC_MODE_ENABLED:
    if not PUBLIC_USER_SALT:
        raise RuntimeError(
            "LIA_PUBLIC_MODE_ENABLED=true requires LIA_PUBLIC_USER_SALT (32+ byte secret)."
        )
    if PUBLIC_CAPTCHA_ENABLED and not PUBLIC_TURNSTILE_SITE_KEY:
        raise RuntimeError(
            "LIA_PUBLIC_MODE_ENABLED=true in production-like env requires LIA_PUBLIC_TURNSTILE_SITE_KEY."
        )
    if PUBLIC_CAPTCHA_ENABLED and not PUBLIC_TURNSTILE_SECRET:
        raise RuntimeError(
            "LIA_PUBLIC_MODE_ENABLED=true requires LIA_PUBLIC_TURNSTILE_SECRET_KEY."
        )

# Suspended-user cache: {(tenant_id, user_id): (is_suspended, check_time)}
_SUSPENDED_CACHE: dict[tuple[str, str], tuple[bool, float]] = {}
_SUSPENDED_CACHE_TTL = 60.0  # seconds
_SUSPENDED_CACHE_LOCK = threading.Lock()

_CHAT_RUN_ROUTE_RE = re.compile(r"^/api/chat/runs/([^/]+)$")
_CHAT_RUN_MILESTONES_ROUTE_RE = re.compile(r"^/api/chat/runs/([^/]+)/milestones$")
_CONVERSATION_SESSION_ROUTE_RE = re.compile(r"^/api/conversation/([^/]+)$")
_JOBS_ROUTE_RE = re.compile(r"^/api/jobs/([^/]+)$")
_DOC_PART_SUFFIX_RE = re.compile(r"_part_[0-9]+$", re.IGNORECASE)
_GENERIC_SOURCE_TITLES = {"dian", "suin", "minhacienda", "fuente", "documento", "norma", "estatuto tributario"}
_SUMMARY_RISK_HINTS = (
    "riesgo",
    "sancion",
    "sanción",
    "rechazo",
    "rechazar",
    "error",
    "incumpl",
    "contingencia",
)
_SUMMARY_ACTION_HINTS = (
    "verificar",
    "validar",
    "document",
    "soporte",
    "revisar",
    "aplicar",
    "conservar",
    "contrastar",
)
_SUMMARY_LOW_RELEVANCE_CONFIDENCE = 0.45
_NORM_REFERENCE_RE = re.compile(
    r"\b("
    r"art(?:[íi]culos?|s?)?\.?\s*\d+(?:[.\-]\d+)*(?:\s*(?:a|al|hasta|–)\s*\d+(?:[.\-]\d+)*)?(?:\s*(?:ET|estatuto\s+tributario|DUR\s*1625|decreto\s+[uú]nico\s+reglamentario\s+1625(?:\s+de\s+2016)?))?"
    r"|(?:estatuto\s+tributario(?:\s*\(ET\))?|ET)(?:\s*:?\s*art(?:[íi]culos?|s?)?\.?\s*\d+(?:[.\-]\d+)*(?:\s*(?:a|al|hasta|–)\s*\d+(?:[.\-]\d+)*)?)?"
    r"|(?:decreto\s+[uú]nico\s+reglamentario\s+1625(?:\s+de\s+2016)?(?:\s*\(DUR\s*1625\))?|DUR\s*1625(?:\s+de\s+2016)?)(?:\s*:\s*(?:parte|t[íi]tulo|cap[íi]tulo|libro|secci[oó]n)[^.;\n]{0,120})?"
    r"|ley\s*\d+(?:/\d{4}| de \d{4})"
    r"|decreto(?!\s+[uú]nico\s+reglamentario)\s*\d+(?:/\d{4}| de \d{4})"
    r"|resoluci[oó]n(?:\s*DIAN)?\s*\d+(?:/\d{4}| de \d{4})"
    r"|concepto(?:\s*DIAN)?\s*\d+(?:/\d{4}| de \d{4})"
    r"|(?:formulario|formato|f)\.?\s*\d{2,6}(?![\.\-\/]\d)"
    r")\b",
    re.IGNORECASE,
)
_ET_ARTICLE_DOC_ID_RE = re.compile(r"^renta_corpus_a_et_art_(\d+(?:_\d+)*)$", re.IGNORECASE)
# _EXPERT_PROVIDER_HEADING_RE, _EXPERT_SUMMARY_LABEL_RE, _EXPERT_SUMMARY_SKIP_PREFIXES
# → moved to ui_expert_extractors.py (Phase 1E)
_EXPERT_SUMMARY_SKIP_EXACT = {
    "texto base referenciado",
    "texto base referenciado (resumen tecnico)",
    "texto base referenciado (resumen técnico)",
    "fuente primaria de referencia",
    "fuentes consultadas",
    "interpretaciones por fuente",
}

_DEFAULT_CHAT_LIMITS = {
    "message_min_chars": 1,
    "top_k_min": 1,
    "top_k_max": 50,
    "conversation_max_turns": 40,
    "conversation_turn_max_chars": 6000,
    "trace_id_max_chars": 256,
}
_DEFAULT_API_CHAT_TIMEOUT_SECONDS = 25.0

_ALLOWED_STRICT_SCOPE = {"renta_only", "default"}
_ALLOWED_INTERACTION_MODE = {"auto", "narrowing", "direct"}
_ALLOWED_REASONING_PROFILE = {"balanced", "deep"}
_ALLOWED_RESPONSE_DEPTH = set(ALLOWED_RESPONSE_DEPTHS)
_ALLOWED_INTENT_HINT = {"procedimiento", "calculo", "ambas"}
_ALLOWED_FIRST_RESPONSE_MODE = set(ALLOWED_FIRST_RESPONSE_MODES)
_ALLOWED_LAYER_CASCADE_MODE = {"auto", "practica_first", "all_layers", "normativa_only", "practica_first_deferred_normative"}
_ALLOWED_RESPONSE_SECTION_MODE = {"auto", "custom"}
_ALLOWED_ENABLE_EMBEDDINGS = {"off", "on"}
_RELOAD_WATCH_SUFFIXES = {".py", ".html", ".js", ".css"}


def _emit_audit_event(event_type: str, payload: dict[str, Any]) -> None:
    emit_event(event_type, payload)
    emit_event(event_type, payload, log_path=API_AUDIT_LOG_PATH)


def _emit_chat_verbose_event(event_type: str, payload: dict[str, Any]) -> None:
    _emit_audit_event(event_type, payload)
    emit_event(event_type, payload, log_path=VERBOSE_CHAT_LOG_PATH)


def _best_effort_git_commit() -> str:
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=WORKSPACE_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:  # noqa: BLE001
        return "unknown"
    return str(output or "").strip() or "unknown"


def _build_info_payload() -> dict[str, Any]:
    ui_asset_mtime = ""
    latest_mtime = 0.0
    candidate_roots = (UI_DIR, FRONTEND_DIR)
    for root in candidate_roots:
        if not root.exists() or not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".html", ".css", ".js", ".ts", ".json"}:
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            latest_mtime = max(latest_mtime, stat.st_mtime)
    if latest_mtime > 0:
        ui_asset_mtime = datetime.fromtimestamp(latest_mtime, tz=timezone.utc).isoformat()
    reset_chat_on_dev_boot = str(os.environ.get("LIA_RESET_CHAT_ON_DEV_BOOT") or "").strip() == "1"
    dev_boot_nonce = str(os.environ.get("LIA_DEV_BOOT_NONCE") or "").strip()
    return {
        "server_started_at": SERVER_STARTED_AT,
        "git_commit": _best_effort_git_commit(),
        "app_version": "lia-ui-1",
        "ui_asset_mtime": ui_asset_mtime,
        "reset_chat_on_dev_boot": reset_chat_on_dev_boot,
        "dev_boot_nonce": dev_boot_nonce,
    }


def _build_reload_snapshot(roots: tuple[Path, ...]) -> tuple[tuple[str, int, int], ...]:
    rows: list[tuple[str, int, int]] = []
    for root in roots:
        if not root.exists() or not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in _RELOAD_WATCH_SUFFIXES:
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            rows.append((str(path), int(stat.st_mtime_ns), int(stat.st_size)))
    rows.sort()
    return tuple(rows)


def _start_reload_watcher(
    *,
    server: ThreadingHTTPServer,
    watch_roots: tuple[Path, ...],
    interval_seconds: float,
) -> tuple[threading.Event, threading.Event, threading.Thread]:
    stop_event = threading.Event()
    reload_event = threading.Event()
    baseline = _build_reload_snapshot(watch_roots)

    def _watch_loop() -> None:
        nonlocal baseline
        while not stop_event.wait(interval_seconds):
            current = _build_reload_snapshot(watch_roots)
            if current == baseline:
                continue
            reload_event.set()
            _emit_audit_event(
                "ui_server.reload_requested",
                {
                    "watch_roots": [str(root) for root in watch_roots],
                    "interval_seconds": interval_seconds,
                },
            )
            try:
                server.shutdown()
            except OSError:
                pass
            return

    watcher = threading.Thread(target=_watch_loop, name="lia-ui-reloader", daemon=True)
    watcher.start()
    return stop_event, reload_event, watcher


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
    _resolve_doc_expert_providers, _expert_card_summary, _expand_expert_panel_requested_refs,
    _prioritize_expert_panel_docs,
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
    "ui_citation_profile_builders": "_normalize_citation_profile_text _collect_citation_profile_texts _find_grounded_profile_sentence _classify_document_family _format_citation_profile_date _latest_identified_citation_profile_date _extract_normative_year _official_publish_date_or_year _resolve_superseded_label _build_citation_profile_prompt _append_citation_profile_fact _row_looks_like_guide _extract_citation_profile_form_number _spanish_title_case _format_form_reference_title _resolve_form_guide_package_for_context _deterministic_form_citation_profile _resolve_companion_action _resolve_analysis_action _resolve_source_action _citation_profile_display_title _citation_locator_reference_keys _citation_profile_analysis_candidates _extract_locator_excerpt_from_text _summarize_analysis_excerpt _build_citation_profile_original_text_section _build_citation_profile_expert_section _build_structured_original_text _build_structured_expert_comment",
    "ui_source_view_processors": "_guide_primary_source_payload _source_view_provenance_uri _collect_source_view_candidate_rows _load_source_text _pick_local_source_file _source_url_label_for_filename _is_generic_source_title _extract_source_title_from_raw_text _infer_source_title_from_url_or_path _trim_source_view_content_markers _is_source_view_noise_text _extract_source_view_usable_text _build_source_view_candidate_analysis _build_source_query_profile _extract_source_chunks _normalize_source_view_field_value _normalize_source_reference_text _infer_source_reference_anchor _text_refers_to_source_document _anchor_source_view_text _anchor_source_view_summary_payload _build_source_view_summary_prompt _llm_source_view_summary_payload _render_source_view_summary_markdown _build_source_view_summary_markdown _sanitize_source_view_href _render_source_view_inline_markdown _build_source_view_html _extract_outbound_links",
    "ui_normative_processors": "ET_ARTICLE_ADDITIONAL_DEPTH_PATH _is_broad_normative_reference_title _resolve_et_locator_row _resolve_et_locator_analysis _article_heading_pattern _extract_et_article_quote_from_markdown _extract_et_article_metadata _extract_et_article_summary _build_et_article_vigencia_detail _load_et_article_additional_depth _et_article_additional_depth_for_doc_id _resolve_et_additional_depth_sections _resolve_ley_additional_depth_sections _interpretive_display_label _build_structured_additional_depth_sections _clean_practica_label _best_practica_display_label",
    "ui_reference_resolvers": "_NORMATIVE_HELPER_KNOWLEDGE_CLASSES _NORMATIVO_HELPER_SOURCE_TYPES _STRICT_NORMATIVO_HELPER_SOURCE_TYPES _MENTION_KEY_PREFIX_TO_ALLOWED_FAMILIES _reference_label_from_key _find_reference_doc_id _extract_reference_identities_from_citation_payload _extract_reference_identities_from_text _extract_reference_keys_from_text _citation_matches_reference_mentions _document_family_from_row _is_cross_type_mention_mismatch _resolve_mention_citations _select_reference_detail_identity_for_citation _build_reference_detail_title _build_reference_detail_resolution_text _drop_base_citations_shadowed_by_locators _apply_reference_detail_to_citation _is_normative_helper_normativo_citation _filter_normative_helper_citations _citation_targets_ley _citation_et_locator_key _citation_et_locator_label",
    "ui_expert_extractors": "_normalize_query_tokens _expert_chunk_candidates _expert_chunk_matches_article _expert_chunk_matches_topic _derive_expert_topic_label _find_expert_provider_link _canonicalize_expert_panel_ref _extract_expert_anchor_excerpt _clean_expert_summary_paragraph _clip_expert_summary _expert_excerpt_paragraphs _expert_detail_excerpt",
    "ui_text_utilities": "_SUMMARY_STOPWORDS _SUMMARY_INTENT_KEYWORDS _SENTENCE_ABBREVIATION_RE _SENTENCE_ABBR_PLACEHOLDER _CITATION_TAIL_RE _CITATION_HEAD_RE _MARKDOWN_BULLET_KV_RE _LOCAL_UPLOAD_URL_RE _NORMALIZED_INGEST_DOC_ID_RE _URL_TRAILING_PUNCT _sb_find_document_row _sb_assemble_document_markdown _sb_assemble_document_markdown_cached _strip_chunk_context_prefix _reconstruct_chunk_markdown _prefer_normograma_mintic_mirror _index_file_signature _load_index_rows_by_doc_id_cached _looks_like_html_document _resolve_knowledge_file _parse_local_upload_url _derive_ingestion_upload_doc_id _resolve_local_upload_artifact _slugify_filename_part _sanitize_url_candidate _clean_markdown_inline _parse_markdown_sections _markdown_section_map _extract_markdown_bullet_metadata _extract_markdown_primary_body_text _extract_candidate_paragraphs _tokenize_relevance_text _detect_intent_tags _score_chunk_relevance _looks_like_reference_list _split_sentences _pick_summary_sentences _select_diverse_chunks _flatten_markdown_to_text _reference_doc_catalog _row_is_active_or_canonical _extract_reference_keys_from_citation_payload _reference_base_text_for_request_context _extract_public_reference_text _extract_visible_text_from_html _row_lifecycle_rank _row_curation_rank _extract_named_plain_section_body _SOURCE_BASE_SUMMARY_HEADING_RE _SOURCE_INTERNAL_BOUNDARY_RE _SOURCE_METADATA_LINE_RE",
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


def _write_controller_deps() -> dict[str, Any]:
    return {
        "accept_terms": accept_terms,
        "approve_contribution": approve_contribution,
        "auth_nonces_path": AUTH_NONCES_PATH,
        "auth_nonce_path": AUTH_NONCES_PATH,
        "contribution_cls": Contribution,
        "contributions_path": WORKSPACE_ROOT / "artifacts" / "contributions",
        "emit_audit_event": _emit_audit_event,
        "exchange_host_grant": exchange_host_grant,
        "feedback_path": FEEDBACK_PATH,
        "feedback_record_cls": FeedbackRecord,
        "form_guides_root": FORM_GUIDES_ROOT,
        "guide_chat_request_cls": GuideChatRequest,
        "host_integrations_config_path": HOST_INTEGRATIONS_CONFIG_PATH,
        "index_file_path": INDEX_FILE_PATH,
        "chat_run_milestones_route_re": _CHAT_RUN_MILESTONES_ROUTE_RE,
        "chat_runs_path": CHAT_RUNS_PATH,
        "get_chat_run": load_chat_run,
        "ingestion_clear_batch_route_re": _INGESTION_CLEAR_BATCH_ROUTE_RE,
        "ingestion_delete_failed_route_re": _INGESTION_DELETE_FAILED_ROUTE_RE,
        "ingestion_files_route_re": _INGESTION_FILES_ROUTE_RE,
        "ingestion_process_route_re": _INGESTION_PROCESS_ROUTE_RE,
        "ingestion_retry_route_re": _INGESTION_RETRY_ROUTE_RE,
        "ingestion_validate_batch_route_re": _INGESTION_VALIDATE_BATCH_ROUTE_RE,
        "ingestion_runtime": INGESTION_RUNTIME,
        "ingestion_stop_route_re": _INGESTION_STOP_ROUTE_RE,
        "llm_runtime_config_path": LLM_RUNTIME_CONFIG_PATH,
        "platform_auth_error_cls": PlatformAuthError,
        "record_chat_run_event_once": record_chat_run_event_once,
        "reject_contribution": reject_contribution,
        "resolve_guide": resolve_guide,
        "run_guide_chat": run_guide_chat,
        "save_contribution": save_contribution,
        "save_feedback": save_feedback,
        "update_feedback_comment": update_feedback_comment,
        "switch_active_company": switch_active_company,
        "terms_policy_path": TERMS_POLICY_PATH,
        "terms_state_path": TERMS_STATE_PATH,
        "jobs_path": JOBS_RUNTIME_PATH,
        "workspace_root": WORKSPACE_ROOT,
    }


def _analysis_controller_deps() -> dict[str, Any]:
    return {
        "as_public_error": as_public_error,
        "axis_labels": {},
        "build_extractive_interpretation_summary": _build_extractive_interpretation_summary,
        "build_decision_frame": build_decision_frame,
        "build_interpretation_candidate": build_interpretation_candidate,
        "build_interpretation_query_seed": _build_interpretation_query_seed,
        "build_normative_helper_citations": _build_normative_helper_citations,
        "build_public_citation_from_row": _build_public_citation_from_row,
        "citation_cls": Citation,
        "classify_provider": _classify_provider,
        "clip_session_content": _clip_session_content,
        "dedupe_interpretation_docs": _dedupe_interpretation_docs,
        "expand_expert_panel_requested_refs": _expand_expert_panel_requested_refs,
        "expert_card_summary": _expert_card_summary,
        "expert_summary_overrides_path": EXPERT_SUMMARY_OVERRIDES_PATH,
        "filter_provider_links": _filter_provider_links,
        "find_document_index_row": _find_document_index_row,
        "first_substantive_sentence": _first_substantive_sentence,
        "generate_llm_strict": generate_llm_strict,
        "index_file_path": INDEX_FILE_PATH,
        "llm_output_quality_error_cls": LLMOutputQualityError,
        "llm_runtime_config_path": LLM_RUNTIME_CONFIG_PATH,
        "load_doc_corpus_text": _load_doc_corpus_text,
        "logical_doc_id": _logical_doc_id,
        "normalize_pais": normalize_pais,
        "normalize_provider_labels": normalize_provider_labels,
        "normalize_topic_key": normalize_topic_key,
        "pipeline_c_internal_error_cls": PipelineCInternalError,
        "pipeline_c_strict_error_cls": PipelineCStrictError,
        "prioritize_expert_panel_docs": _prioritize_expert_panel_docs,
        "resolve_doc_expert_providers": _resolve_doc_expert_providers,
        "select_interpretation_candidates": select_interpretation_candidates,
        "serialize_ranked_interpretation": serialize_ranked_interpretation,
        "summarize_snippet": _summarize_snippet,
        "supported_topics": SUPPORTED_TOPICS,
        "warn_missing_active_index_generation": _warn_missing_active_index_generation,
    }


def _chat_controller_deps() -> dict[str, Any]:
    return {
        "advance_clarification_state": advance_clarification_state,
        "append_turn": append_turn,
        "as_public_error": as_public_error,
        "auth_context_cls": AuthContext,
        "build_clarification_error_payload": _build_clarification_error_payload,
        "build_clarification_interaction_payload": build_clarification_interaction_payload,
        "build_normative_helper_citations": _build_normative_helper_citations,
        "build_public_api_error": _build_public_api_error,
        "chat_run_coordinator": get_chat_run_coordinator(),
        "chat_runs_path": CHAT_RUNS_PATH,
        "chat_session_metrics_path": CHAT_SESSION_METRICS_PATH,
        "citation_gap_registry_path": CITATION_GAP_REGISTRY_PATH,
        "clarification_sessions_path": CLARIFICATION_SESSIONS_PATH,
        "clarification_state_version": CLARIFICATION_STATE_VERSION,
        "clear_clarification_session_state": clear_clarification_session_state,
        "comparative_field_questions": COMPARATIVE_FIELD_QUESTIONS,
        "conversations_path": CONVERSATIONS_PATH,
        "credibility_policy_path": WORKSPACE_ROOT / "config" / "credibility_policy.json",
        "emit_chat_verbose_event": _emit_chat_verbose_event,
        "emit_user_error_event": lambda payload: emit_event("user.chat.error", payload, log_path=USER_ERROR_LOG_PATH),
        "emit_event": emit_event,
        "emit_reasoning_event": emit_reasoning_event,
        "ensure_session": ensure_session,
        "ensure_session_shell": ensure_session_shell,
        "enrich_citation_payloads_with_usage_context": _enrich_citation_payloads_with_usage_context,
        "estimate_token_usage_from_text": estimate_token_usage_from_text,
        "get_clarification_session_state": get_clarification_session_state,
        "get_chat_session_metrics": get_chat_session_metrics,
        "index_file_path": INDEX_FILE_PATH,
        "is_semantic_422_error": is_semantic_422_error,
        "jobs_path": JOBS_RUNTIME_PATH,
        "llm_dynamic_clarification_decider": _llm_dynamic_clarification_decider,
        "llm_runtime_config_path": LLM_RUNTIME_CONFIG_PATH,
        "load_session": load_session,
        "merge_citation_payloads": _merge_citation_payloads,
        "normalize_pais": normalize_pais,
        "normalize_token_usage": normalize_token_usage,
        "normalize_topic_key": normalize_topic_key,
        "pipeline_c_internal_error_cls": PipelineCInternalError,
        "pipeline_c_request_cls": PipelineCRequest,
        "pipeline_c_strict_error_cls": PipelineCStrictError,
        "default_pipeline_variant": str(
            os.getenv("LIA_PIPELINE_VARIANT", DEFAULT_PIPELINE_VARIANT)
        ).strip() or DEFAULT_PIPELINE_VARIANT,
        "execute_routed_pipeline": lambda request, **kwargs: execute_routed_pipeline(
            request,
            pipeline_c_runner=run_pipeline_c,
            pipeline_d_runner=run_pipeline_d,
            **kwargs,
        ),
        "platform_auth_error_cls": PlatformAuthError,
        "public_visitor_role": PUBLIC_VISITOR_ROLE,
        "public_tenant_id": PUBLIC_TENANT_ID,
        "public_max_output_tokens": int(
            str(os.getenv("LIA_PUBLIC_MAX_OUTPUT_TOKENS", "2048")).strip() or "2048"
        ),
        "refresh_state_from_semantic_error": refresh_state_from_semantic_error,
        "register_citation_gaps": register_citation_gaps,
        "resolve_chat_topic": resolve_chat_topic,
        "resolve_pipeline_route": resolve_pipeline_route,
        "resolve_guided_clarification_requirements": _resolve_guided_clarification_requirements,
        "save_usage_event": save_usage_event,
        "should_intercept_clarification_state": should_intercept_clarification_state,
        "stored_conversation_turn_cls": StoredConversationTurn,
        "strip_inline_evidence_annotations": strip_inline_evidence_annotations,
        "update_chat_session_metrics": update_chat_session_metrics,
        "update_session_metadata": update_session_metadata,
        "upsert_clarification_session_state": upsert_clarification_session_state,
        "usage_event_cls": UsageEvent,
        "usage_events_path": USAGE_EVENTS_PATH,
        "validate_pipeline_c_payload": _validate_pipeline_c_payload,
        "build_user_message_for_question": build_user_message_for_question,
        "uuid4": uuid4,
    }


def _frontend_compat_controller_deps() -> dict[str, Any]:
    return {
        "chat_run_milestones_route_re": _CHAT_RUN_MILESTONES_ROUTE_RE,
        "chat_runs_path": CHAT_RUNS_PATH,
        "feedback_path": FEEDBACK_PATH,
        "feedback_record_cls": FeedbackRecord,
        "load_feedback": load_feedback,
        "public_tenant_id": PUBLIC_TENANT_ID,
        "record_chat_run_event_once": record_chat_run_event_once,
        "save_feedback": save_feedback,
        "update_feedback_comment": update_feedback_comment,
    }


def _public_session_controller_deps() -> dict[str, Any]:
    return {
        "issue_public_visitor_token": issue_public_visitor_token,
        "public_captcha_enabled": PUBLIC_CAPTCHA_ENABLED,
        "public_captcha_pass_exists": public_captcha_pass_exists,
        "public_captcha_pass_record": public_captcha_pass_record,
        "public_mode_enabled": PUBLIC_MODE_ENABLED,
        "public_token_ttl_seconds": PUBLIC_TOKEN_TTL_SECONDS,
        "public_turnstile_site_key": PUBLIC_TURNSTILE_SITE_KEY,
        "ui_dir": UI_DIR,
        "verify_turnstile": verify_turnstile,
    }


class LiaUIHandler(BaseHTTPRequestHandler):
    server_version = "LIAUI/0.1"

    def _request_origin(self) -> str | None:
        origin = str(self.headers.get("Origin", "")).strip()
        if origin:
            return origin
        referer = str(self.headers.get("Referer", "")).strip()
        if not referer:
            return None
        parsed = urlparse(referer)
        if not parsed.scheme or not parsed.netloc:
            return None
        return f"{parsed.scheme}://{parsed.netloc}"

    def _allowed_cors_origin(self) -> str | None:
        origin = self._request_origin()
        if not origin:
            return None
        # Only allow localhost origins in non-production environments
        if not is_production_like_env():
            if origin.startswith("http://127.0.0.1:") or origin.startswith("http://localhost:"):
                return origin
        integrations = load_host_integrations(config_path=HOST_INTEGRATIONS_CONFIG_PATH)
        for integration in integrations.values():
            if integration.allows_origin(origin):
                return origin
        return None

    def _cors_headers(self) -> dict[str, str]:
        headers = {"Vary": "Origin"}
        allowed_origin = self._allowed_cors_origin()
        if allowed_origin:
            headers.update(
                {
                    "Access-Control-Allow-Origin": allowed_origin,
                    "Access-Control-Allow-Headers": "Authorization, Content-Type",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                }
            )
        return headers

    def _embed_security_headers(self) -> dict[str, str]:
        allowed_origins = sorted(
            {
                origin
                for integration in load_host_integrations(config_path=HOST_INTEGRATIONS_CONFIG_PATH).values()
                for origin in integration.allowed_origins
                if str(origin).strip()
            }
        )
        frame_ancestors = " ".join(["'self'", *allowed_origins]).strip() or "'self'"
        return {
            "Content-Security-Policy": f"frame-ancestors {frame_ancestors};",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }

    def _send_auth_error(self, exc: PlatformAuthError) -> None:
        self._send_json(
            HTTPStatus(int(exc.http_status)),
            {
                "ok": False,
                "error": {
                    "code": exc.code,
                    "message": str(exc),
                },
            },
            extra_headers={"X-LIA-Error-Code": exc.code},
        )

    def _resolve_auth_context(
        self,
        *,
        required: bool = False,
        allow_public: bool = False,
    ) -> AuthContext | None:
        """Resolve the request's auth context.

        `allow_public` is the single chokepoint that protects every non-chat
        handler from the no-login `/public` visitor. Default `False` means a
        valid `public_visitor` JWT is *rejected with 403* — the caller must
        opt in explicitly. Only `/api/chat` and `/api/chat/stream` (and the
        public route serving) are allowed to set `allow_public=True`.
        """
        authorization_header = self.headers.get("Authorization")
        try:
            token = read_bearer_token(authorization_header)
        except PlatformAuthError:
            if required:
                raise
            return None
        if not token:
            if required:
                raise PlatformAuthError(
                    "Authorization Bearer requerido.",
                    code="auth_required",
                    http_status=401,
                )
            return None

        # Service account API key (lia_eval_ prefix) — bypass JWT flow
        if token.startswith("lia_eval_"):
            try:
                from .service_account_auth import authenticate_service_account
                return authenticate_service_account(token)
            except PlatformAuthError:
                if required:
                    raise
                return None

        try:
            context = authenticate_access_token(token)
        except PlatformAuthError:
            if required:
                raise
            return None
        if context.role == PUBLIC_VISITOR_ROLE:
            # Master kill switch: even a perfectly-signed public token is
            # rejected when public mode is off, so flipping the env flag
            # ages out the entire surface instantly.
            if not PUBLIC_MODE_ENABLED:
                raise PlatformAuthError(
                    "Public mode disabled.",
                    code="public_mode_disabled",
                    http_status=503,
                )
            if not allow_public:
                raise PlatformAuthError(
                    "Acceso público no permitido en esta ruta.",
                    code="auth_public_forbidden",
                    http_status=403,
                )
            # Public visitors live in their own reserved tenant; the suspension
            # cache cannot match them, so skip that check.
            return context
        if self._is_user_suspended(context.tenant_id, context.user_id):
            raise PlatformAuthError(
                "Su cuenta está suspendida.",
                code="auth_user_suspended",
                http_status=403,
            )
        return context

    def _admin_tenant_scope(self, auth_context: AuthContext, requested_tenant_id: str | None = None) -> str | None:
        if auth_context.role not in {"tenant_admin", "platform_admin"}:
            raise PlatformAuthError(
                "Se requiere rol administrativo.",
                code="auth_role_forbidden",
                http_status=403,
            )
        if auth_context.role == "platform_admin":
            tenant_id = str(requested_tenant_id or "").strip()
            return tenant_id or None
        return auth_context.tenant_id

    def _resolve_feedback_rating(self, payload: dict[str, Any]) -> int | None:
        vote = str(payload.get("vote") or payload.get("thumb") or "").strip().lower()
        rating_raw = payload.get("rating")
        if isinstance(rating_raw, (int, float)):
            rating = int(rating_raw)
        elif vote in {"up", "down", "neutral"}:
            rating = {"up": 5, "down": 1, "neutral": 3}[vote]
        else:
            return None
        if 1 <= rating <= 5:
            return rating
        return None

    def _clarification_scope_key(self, request_context: dict[str, Any]) -> str:
        return build_clarification_scope_key(request_context)

    def _build_memory_summary(self, session: Any) -> str:
        return build_memory_summary(session)

    def _handle_chat_frontend_compat_get(self, path: str, parsed: Any) -> bool:
        from .ui_frontend_compat_controllers import handle_chat_frontend_compat_get
        return handle_chat_frontend_compat_get(
            self,
            path,
            parsed,
            deps=_frontend_compat_controller_deps(),
        )

    def _handle_chat_frontend_compat_post(self, path: str) -> bool:
        from .ui_frontend_compat_controllers import handle_chat_frontend_compat_post
        return handle_chat_frontend_compat_post(
            self,
            path,
            deps=_frontend_compat_controller_deps(),
        )

    def _initialize_chat_request_context(
        self,
        *,
        request_context: dict[str, Any],
        auth_context: AuthContext | None,
        channel: str,
    ) -> None:
        initialize_chat_request_context(
            request_context=request_context,
            auth_context=auth_context,
            channel=channel,
            deps=_chat_controller_deps(),
        )

    def _persist_user_turn(self, request_context: dict[str, Any]) -> None:
        persist_user_turn(request_context=request_context, deps=_chat_controller_deps())

    def _persist_assistant_turn(
        self,
        *,
        request_context: dict[str, Any],
        content: str,
        trace_id: str | None,
        layer_contributions: dict[str, int] | None = None,
    ) -> None:
        persist_assistant_turn(
            request_context=request_context,
            content=content,
            trace_id=trace_id,
            layer_contributions=layer_contributions,
            deps=_chat_controller_deps(),
        )

    def _persist_usage_events(
        self,
        *,
        request_context: dict[str, Any],
        response_payload: dict[str, Any],
    ) -> None:
        persist_usage_events(
            request_context=request_context,
            response_payload=response_payload,
            deps=_chat_controller_deps(),
        )

    def _start_api_request_log(self, method: str) -> None:
        self._api_log_response_emitted = False
        self._api_log_started_monotonic = time.monotonic()
        self._api_log_method = method
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            return
        _emit_audit_event(
            "api.http.request",
            {
                "method": method,
                "path": parsed.path,
                "query": parsed.query,
                "client_address": getattr(self, "client_address", None),
            },
        )

    def _log_api_response(self, *, status: int, content_type: str | None) -> None:
        if getattr(self, "_api_log_response_emitted", False):
            return
        raw_path = getattr(self, "path", "")
        if not isinstance(raw_path, str) or not raw_path:
            return
        parsed = urlparse(raw_path)
        if not parsed.path.startswith("/api/"):
            return
        started = getattr(self, "_api_log_started_monotonic", None)
        duration_ms = None
        if isinstance(started, (int, float)):
            duration_ms = round((time.monotonic() - float(started)) * 1000, 2)
        _emit_audit_event(
            "api.http.reply",
            {
                "method": str(getattr(self, "_api_log_method", "") or "UNKNOWN"),
                "path": parsed.path,
                "status": int(status),
                "content_type": content_type,
                "duration_ms": duration_ms,
            },
        )
        self._api_log_response_emitted = True

    @staticmethod
    def _base_security_headers() -> dict[str, str]:
        headers: dict[str, str] = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }
        if is_production_like_env():
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return headers

    def _send_bytes(
        self,
        status: int,
        body: bytes,
        content_type: str,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        for key, value in self._base_security_headers().items():
            self.send_header(key, value)
        if str(getattr(self, "path", "") or "").startswith("/api/"):
            for key, value in self._cors_headers().items():
                self.send_header(key, value)
        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(str(key), str(value))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        self._log_api_response(status=status, content_type=content_type)

    def _send_json(
        self,
        status: int,
        payload: dict[str, Any],
        *,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self._send_bytes(
            status,
            _json_bytes(payload),
            "application/json; charset=utf-8",
            extra_headers=extra_headers,
        )

    def _send_event_stream_headers(self, *, status: HTTPStatus = HTTPStatus.OK) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("X-Accel-Buffering", "no")
        for key, value in self._cors_headers().items():
            self.send_header(key, value)
        self.end_headers()
        self.close_connection = True
        self._log_api_response(status=status, content_type="text/event-stream; charset=utf-8")

    def _write_sse_event(
        self,
        event_name: str,
        payload: dict[str, Any],
        *,
        event_id: str | int | None = None,
    ) -> None:
        packet_parts: list[str] = []
        if event_id is not None:
            packet_parts.append(f"id: {event_id}")
        packet_parts.append(f"event: {str(event_name or 'message').strip() or 'message'}")
        packet_parts.append(f"data: {json.dumps(payload, ensure_ascii=False)}")
        packet = "\n".join(packet_parts) + "\n\n"
        self.wfile.write(packet.encode("utf-8"))
        self.wfile.flush()

    def _read_json_payload(
        self,
        *,
        empty_body: bytes = b"{}",
        object_error: str | None = None,
        max_size: int = 1_048_576,
    ) -> Any | None:
        length_raw = self.headers.get("Content-Length", "0")
        try:
            length = int(length_raw)
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Content-Length invalido."})
            return None

        if length > max_size:
            self._send_json(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                {"error": f"Payload excede el tamaño maximo ({max_size} bytes)."},
            )
            return None

        raw = self.rfile.read(length) if length > 0 else empty_body
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "JSON invalido."})
            return None

        if object_error is not None and not isinstance(payload, dict):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": object_error})
            return None
        return payload

    def _check_rate_limit(self, endpoint_key: str, max_requests: int, window_seconds: int) -> bool:
        """Return True if rate limit is exceeded (request should be blocked)."""
        client_ip = self._get_trusted_client_ip()
        key = f"{endpoint_key}:{client_ip}"
        if not _RATE_LIMITER.is_allowed(key, max_requests, window_seconds):
            self._send_json(
                HTTPStatus.TOO_MANY_REQUESTS,
                {"error": "Demasiadas solicitudes. Intente de nuevo en unos segundos."},
                extra_headers={"Retry-After": str(window_seconds)},
            )
            return True
        return False

    def _get_trusted_client_ip(self) -> str:
        """Return the client IP, honoring `X-Forwarded-For` only when trusted.

        Behind Railway / any reverse proxy, `self.client_address` is the proxy
        IP, not the real client. We honor `X-Forwarded-For` (leftmost entry)
        only when `LIA_TRUST_PROXY=1`. We also reject pathologically long XFF
        chains (>10 hops) as untrusted, since they are typical of spoofed
        requests originating outside the trusted ingress.
        """
        if PUBLIC_TRUST_PROXY:
            xff = str(self.headers.get("X-Forwarded-For") or "").strip()
            if xff:
                parts = [item.strip() for item in xff.split(",") if item.strip()]
                if 1 <= len(parts) <= 10:
                    return parts[0]
            real_ip = str(self.headers.get("X-Real-IP") or "").strip()
            if real_ip:
                return real_ip
        return getattr(self, "client_address", ("unknown",))[0]

    def _hash_public_user_id(self, ip: str) -> str:
        """Return the synthetic, deterministic public visitor identifier.

        `pub_<sha256(ip + LIA_PUBLIC_USER_SALT)[:16]>`.

        Raw IPs are never persisted; only this hash is. The salt is a Railway
        secret so the hash space cannot be precomputed by an attacker.
        """
        salt = PUBLIC_USER_SALT or ""
        digest = hashlib.sha256(f"{ip}{salt}".encode("utf-8")).hexdigest()[:16]
        return f"pub_{digest}"

    def _check_public_daily_quota(self, pub_user_id: str) -> bool:
        """Return True if the daily quota is exceeded (request blocked).

        Mirrors the contract of `_check_rate_limit`: True means the response
        has already been sent (429) and the caller should `return`.
        """
        if not is_production_like_env():
            return False
        try:
            from .supabase_client import get_supabase_client
            client = get_supabase_client()
        except Exception:
            client = None
        allowed, _count = check_and_increment_daily_quota(
            ip_hash=pub_user_id,
            cap=PUBLIC_CHAT_DAILY_CAP,
            supabase_client=client,
        )
        if not allowed:
            self._send_json(
                HTTPStatus.TOO_MANY_REQUESTS,
                {
                    "error": {
                        "code": "public_daily_quota_exceeded",
                        "message": "Has alcanzado el límite diario de mensajes en modo público.",
                    }
                },
                extra_headers={"Retry-After": "86400"},
            )
            return True
        return False

    def _is_public_visitor_request(self) -> bool:
        """Probe whether the current request carries a `public_visitor` JWT.

        Returns False (without raising) when no token is present or the token
        is for a normal authenticated user. Used by the `/api/chat` rate-limit
        branch to choose between the public and the authenticated tier.
        """
        try:
            ctx = self._resolve_auth_context(required=False, allow_public=True)
        except PlatformAuthError:
            return False
        return bool(ctx is not None and ctx.role == PUBLIC_VISITOR_ROLE)

    def _handle_public_session_post(self) -> None:
        from .ui_public_session_controllers import handle_public_session_post
        handle_public_session_post(self, deps=_public_session_controller_deps())

    def _serve_public_page(self) -> None:
        from .ui_public_session_controllers import handle_public_page_get
        handle_public_page_get(self, deps=_public_session_controller_deps())

    def _is_user_suspended(self, tenant_id: str, user_id: str) -> bool:
        """Check if user is suspended (cached, best-effort)."""
        if not user_id:
            return False
        cache_key = (tenant_id, user_id)
        now = time.monotonic()
        with _SUSPENDED_CACHE_LOCK:
            cached = _SUSPENDED_CACHE.get(cache_key)
            if cached is not None:
                is_suspended, check_time = cached
                if now - check_time < _SUSPENDED_CACHE_TTL:
                    return is_suspended
        # Best-effort DB check
        try:
            from .supabase_client import get_supabase_client
            client = get_supabase_client()
            if client is None:
                return False
            result = client.table("users").select("status").eq("user_id", user_id).maybe_single().execute()
            is_suspended = bool(result and result.data and result.data.get("status") == "suspended")
            with _SUSPENDED_CACHE_LOCK:
                _SUSPENDED_CACHE[cache_key] = (is_suspended, now)
            return is_suspended
        except Exception:
            return False

    def log_message(self, format: str, *args: object) -> None:
        # Evita ruido en stdout por cada request.
        return

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
