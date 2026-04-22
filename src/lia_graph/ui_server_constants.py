"""Module-level constants for `ui_server`.

Extracted during decouplingv1 Phase 1 to unblock the handler-class split.
Split rationale: `ui_server.py`'s 1000+-LOC handler class referenced ~150
module-level names. Lifting those names (paths, flags, regex, frozen data,
rate-limit singleton, suspended-user cache) into a dependency-free sibling
makes the subsequent handler-base/handler-dispatch splits mechanical — each
sibling does `from .ui_server_constants import *` plus its own targeted deps
and no circular import is possible because this module never imports
`ui_server`.

Runtime side effect: the PUBLIC_MODE block may raise RuntimeError at import
time when LIA_PUBLIC_MODE_ENABLED is set without required secrets. That
behavior is preserved verbatim from the original ui_server top-level block.
"""

from __future__ import annotations

import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

from .chat_response_modes import ALLOWED_FIRST_RESPONSE_MODES, ALLOWED_RESPONSE_DEPTHS
from .ingestion_runtime import IngestionRuntime
from .platform_auth import DEFAULT_PUBLIC_TOKEN_TTL_SECONDS
from .rate_limiter import InMemoryRateLimiter
from .runtime_env import is_production_like_env
from .topic_guardrails import get_supported_topics


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


__all__ = [
    # Paths
    "WORKSPACE_ROOT",
    "UI_DIR",
    "FRONTEND_DIR",
    "TERMS_POLICY_PATH",
    "TERMS_STATE_PATH",
    "LLM_RUNTIME_CONFIG_PATH",
    "ORCHESTRATION_SETTINGS_PATH",
    "INDEX_FILE_PATH",
    "KNOWLEDGE_BASE_ROOT",
    "INGESTION_ARTIFACTS_ROOT",
    "INGESTION_PROCESSED_ROOT",
    "INGESTION_UPLOADS_ROOT",
    "VERBOSE_CHAT_LOG_PATH",
    "API_AUDIT_LOG_PATH",
    "USER_ERROR_LOG_PATH",
    "CHAT_SESSION_METRICS_PATH",
    "CITATION_GAP_REGISTRY_PATH",
    "FORM_GUIDES_ROOT",
    "ACTIVE_INDEX_GENERATION_PATH",
    "CLARIFICATION_SESSIONS_PATH",
    "CONVERSATIONS_PATH",
    "FEEDBACK_PATH",
    "EXPERT_SUMMARY_OVERRIDES_PATH",
    "HOST_INTEGRATIONS_CONFIG_PATH",
    "AUTH_NONCES_PATH",
    "USAGE_EVENTS_PATH",
    "JOBS_RUNTIME_PATH",
    "CORPUS_JOBS_RUNTIME_PATH",
    "CHAT_RUNS_PATH",
    # Runtime-ish
    "SUPPORTED_TOPICS",
    "INGESTION_RUNTIME",
    "SERVER_STARTED_AT",
    "_RATE_LIMITER",
    # Regexes
    "_INGESTION_SESSION_ROUTE_RE",
    "_INGESTION_FILES_ROUTE_RE",
    "_INGESTION_PROCESS_ROUTE_RE",
    "_INGESTION_RETRY_ROUTE_RE",
    "_INGESTION_VALIDATE_BATCH_ROUTE_RE",
    "_INGESTION_DELETE_FAILED_ROUTE_RE",
    "_INGESTION_STOP_ROUTE_RE",
    "_INGESTION_CLEAR_BATCH_ROUTE_RE",
    "_INGESTION_DELETE_SESSION_ROUTE_RE",
    "_OPS_RUN_ROUTE_RE",
    "_OPS_RUN_TIMELINE_ROUTE_RE",
    "_CHAT_SESSION_METRICS_ROUTE_RE",
    "_CHAT_RUN_ROUTE_RE",
    "_CHAT_RUN_MILESTONES_ROUTE_RE",
    "_CONVERSATION_SESSION_ROUTE_RE",
    "_JOBS_ROUTE_RE",
    "_DOC_PART_SUFFIX_RE",
    "_NORM_REFERENCE_RE",
    "_ET_ARTICLE_DOC_ID_RE",
    # Helpers + env
    "_env_truthy",
    # Public mode
    "_PUBLIC_RUNTIME_IS_PRODUCTION",
    "PUBLIC_MODE_ENABLED",
    "PUBLIC_TRUST_PROXY",
    "PUBLIC_USER_SALT",
    "PUBLIC_CHAT_BURST_RPM",
    "PUBLIC_CHAT_DAILY_CAP",
    "PUBLIC_TOKEN_TTL_SECONDS",
    "PUBLIC_TURNSTILE_SITE_KEY",
    "PUBLIC_TURNSTILE_SECRET",
    "PUBLIC_CAPTCHA_ENABLED",
    # Suspended cache
    "_SUSPENDED_CACHE",
    "_SUSPENDED_CACHE_TTL",
    "_SUSPENDED_CACHE_LOCK",
    # Frozen data
    "_GENERIC_SOURCE_TITLES",
    "_SUMMARY_RISK_HINTS",
    "_SUMMARY_ACTION_HINTS",
    "_SUMMARY_LOW_RELEVANCE_CONFIDENCE",
    "_EXPERT_SUMMARY_SKIP_EXACT",
    "_DEFAULT_CHAT_LIMITS",
    "_DEFAULT_API_CHAT_TIMEOUT_SECONDS",
    # Allowed sets
    "_ALLOWED_STRICT_SCOPE",
    "_ALLOWED_INTERACTION_MODE",
    "_ALLOWED_REASONING_PROFILE",
    "_ALLOWED_RESPONSE_DEPTH",
    "_ALLOWED_INTENT_HINT",
    "_ALLOWED_FIRST_RESPONSE_MODE",
    "_ALLOWED_LAYER_CASCADE_MODE",
    "_ALLOWED_RESPONSE_SECTION_MODE",
    "_ALLOWED_ENABLE_EMBEDDINGS",
]
