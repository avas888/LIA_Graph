"""Identity + re-export tests for `ui_server_constants` / `ui_server_helpers`.

Ensures the Phase 1 extraction preserves the public surface downstream
consumers rely on (``from lia_graph.ui_server import WORKSPACE_ROOT`` etc.).
"""

from __future__ import annotations

import re
from pathlib import Path

from lia_graph import ui_server, ui_server_constants, ui_server_helpers


def test_workspace_root_is_path():
    assert isinstance(ui_server_constants.WORKSPACE_ROOT, Path)


def test_key_path_constants_are_paths():
    for name in (
        "UI_DIR",
        "FRONTEND_DIR",
        "TERMS_POLICY_PATH",
        "INDEX_FILE_PATH",
        "FORM_GUIDES_ROOT",
        "CONVERSATIONS_PATH",
        "FEEDBACK_PATH",
        "API_AUDIT_LOG_PATH",
        "VERBOSE_CHAT_LOG_PATH",
        "CHAT_RUNS_PATH",
    ):
        assert isinstance(getattr(ui_server_constants, name), Path), name


def test_route_regexes_are_compiled_patterns():
    for name in (
        "_CHAT_RUN_ROUTE_RE",
        "_CHAT_SESSION_METRICS_ROUTE_RE",
        "_INGESTION_SESSION_ROUTE_RE",
        "_OPS_RUN_ROUTE_RE",
        "_NORM_REFERENCE_RE",
        "_ET_ARTICLE_DOC_ID_RE",
    ):
        assert isinstance(getattr(ui_server_constants, name), re.Pattern), name


def test_public_mode_flags_present():
    for name in (
        "PUBLIC_MODE_ENABLED",
        "PUBLIC_TRUST_PROXY",
        "PUBLIC_CHAT_BURST_RPM",
        "PUBLIC_CHAT_DAILY_CAP",
        "PUBLIC_TOKEN_TTL_SECONDS",
        "PUBLIC_CAPTCHA_ENABLED",
    ):
        assert hasattr(ui_server_constants, name), name


def test_frozen_data_shapes():
    assert isinstance(ui_server_constants._GENERIC_SOURCE_TITLES, set)
    assert isinstance(ui_server_constants._SUMMARY_RISK_HINTS, tuple)
    assert isinstance(ui_server_constants._SUMMARY_ACTION_HINTS, tuple)
    assert isinstance(ui_server_constants._EXPERT_SUMMARY_SKIP_EXACT, set)
    assert isinstance(ui_server_constants._DEFAULT_CHAT_LIMITS, dict)
    # _ALLOWED_* sets
    for name in (
        "_ALLOWED_STRICT_SCOPE",
        "_ALLOWED_INTERACTION_MODE",
        "_ALLOWED_REASONING_PROFILE",
        "_ALLOWED_RESPONSE_DEPTH",
        "_ALLOWED_INTENT_HINT",
        "_ALLOWED_FIRST_RESPONSE_MODE",
        "_ALLOWED_LAYER_CASCADE_MODE",
        "_ALLOWED_RESPONSE_SECTION_MODE",
        "_ALLOWED_ENABLE_EMBEDDINGS",
    ):
        assert isinstance(getattr(ui_server_constants, name), set), name


def test_rate_limiter_singleton_present():
    from lia_graph.rate_limiter import InMemoryRateLimiter

    assert isinstance(ui_server_constants._RATE_LIMITER, InMemoryRateLimiter)


def test_suspended_cache_objects_present():
    import threading

    assert isinstance(ui_server_constants._SUSPENDED_CACHE, dict)
    assert isinstance(ui_server_constants._SUSPENDED_CACHE_LOCK, threading.Lock().__class__)
    assert ui_server_constants._SUSPENDED_CACHE_TTL > 0


def test_helpers_exported():
    for name in (
        "_emit_audit_event",
        "_emit_chat_verbose_event",
        "_best_effort_git_commit",
        "_build_info_payload",
        "_build_reload_snapshot",
        "_start_reload_watcher",
    ):
        assert callable(getattr(ui_server_helpers, name)), name


def test_ui_server_reexports_constants_and_helpers():
    # Downstream code (and legacy tests) import these from ui_server directly.
    for name in (
        "WORKSPACE_ROOT",
        "UI_DIR",
        "FRONTEND_DIR",
        "API_AUDIT_LOG_PATH",
        "_RATE_LIMITER",
        "_SUSPENDED_CACHE",
        "_NORM_REFERENCE_RE",
        "PUBLIC_MODE_ENABLED",
        "_DEFAULT_CHAT_LIMITS",
        "_emit_audit_event",
        "_emit_chat_verbose_event",
        "_best_effort_git_commit",
        "_build_info_payload",
    ):
        assert hasattr(ui_server, name), f"ui_server missing re-exported name {name!r}"


def test_reexported_identity_matches_source_module():
    # Same object, not a copy.
    assert ui_server.WORKSPACE_ROOT is ui_server_constants.WORKSPACE_ROOT
    assert ui_server._RATE_LIMITER is ui_server_constants._RATE_LIMITER
    assert ui_server._SUSPENDED_CACHE is ui_server_constants._SUSPENDED_CACHE
    assert ui_server._emit_audit_event is ui_server_helpers._emit_audit_event
    assert ui_server._build_info_payload is ui_server_helpers._build_info_payload
