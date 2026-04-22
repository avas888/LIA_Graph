"""Structural tests for `LiaUIHandler` after the Phase 3 dispatch split.

The class now lives in `ui_server_handler_dispatch` and is re-exported from
`ui_server` for back-compat with every downstream consumer (CLI, tests,
monkeypatching fixtures).
"""

from __future__ import annotations

from lia_graph import ui_server
from lia_graph.ui_server_handler_base import LiaUIHandlerBase
from lia_graph.ui_server_handler_dispatch import LiaUIHandler


def test_dispatch_class_is_reexported_from_ui_server():
    assert ui_server.LiaUIHandler is LiaUIHandler


def test_dispatch_class_inherits_from_base():
    assert issubclass(LiaUIHandler, LiaUIHandlerBase)
    mro = [c.__name__ for c in LiaUIHandler.__mro__]
    assert mro[0] == "LiaUIHandler"
    assert mro[1] == "LiaUIHandlerBase"


def test_verb_dispatchers_present():
    for name in ("do_GET", "do_OPTIONS", "do_POST", "do_PUT", "do_PATCH", "do_DELETE"):
        assert callable(getattr(LiaUIHandler, name, None)), name


def test_get_route_handlers_present():
    for name in (
        "_handle_ops_get",
        "_handle_reasoning_get",
        "_handle_ingestion_get",
        "_handle_ingest_run_get",
        "_handle_runtime_terms_get",
        "_handle_citation_get",
        "_handle_source_get",
        "_handle_platform_get",
        "_handle_history_get",
        "_handle_form_guides_get",
        "_resolve_ui_asset_path",
        "_serve_ui_asset",
    ):
        assert callable(getattr(LiaUIHandler, name, None)), name


def test_chat_payload_wrappers_present():
    for name in (
        "_send_api_chat_error",
        "_parse_api_chat_request",
        "_apply_api_chat_clarification",
        "_build_api_chat_success_payload",
        "_finalize_api_chat_response",
        "_handle_api_chat_post",
        "_handle_api_chat_stream_post",
    ):
        assert callable(getattr(LiaUIHandler, name, None)), name


def test_base_methods_resolved_via_mro():
    # Sanity check: inherited methods remain callable on the dispatch subclass.
    for name in (
        "_send_json",
        "_send_bytes",
        "_resolve_auth_context",
        "_check_rate_limit",
        "_is_user_suspended",
    ):
        assert callable(getattr(LiaUIHandler, name, None)), name
