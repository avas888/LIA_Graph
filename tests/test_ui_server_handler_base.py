"""Structural tests for `LiaUIHandlerBase`.

Phase 2 of the decouplingv1 plan extracts plumbing, auth, response helpers,
rate-limit gating, and the suspended-user cache into a base class. These
tests verify the class is importable, correctly positioned in the MRO, and
carries the methods we moved.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler

from lia_graph import ui_server
from lia_graph.ui_server_handler_base import LiaUIHandlerBase


def test_base_class_subclasses_base_http_request_handler():
    assert issubclass(LiaUIHandlerBase, BaseHTTPRequestHandler)


def test_concrete_handler_inherits_from_base():
    assert issubclass(ui_server.LiaUIHandler, LiaUIHandlerBase)
    mro_names = [c.__name__ for c in ui_server.LiaUIHandler.__mro__]
    assert mro_names[0] == "LiaUIHandler"
    assert mro_names[1] == "LiaUIHandlerBase"
    assert "BaseHTTPRequestHandler" in mro_names


def test_server_version_preserved_on_base():
    assert LiaUIHandlerBase.server_version == "LIAUI/0.1"
    # Inherited via MRO.
    assert ui_server.LiaUIHandler.server_version == "LIAUI/0.1"


def test_plumbing_methods_present():
    for name in (
        "_request_origin",
        "_allowed_cors_origin",
        "_cors_headers",
        "_embed_security_headers",
        "_start_api_request_log",
        "_log_api_response",
        "log_message",
    ):
        assert callable(getattr(LiaUIHandlerBase, name, None)), name


def test_auth_methods_present():
    for name in (
        "_send_auth_error",
        "_resolve_auth_context",
        "_admin_tenant_scope",
        "_resolve_feedback_rating",
        "_clarification_scope_key",
        "_build_memory_summary",
        "_is_user_suspended",
    ):
        assert callable(getattr(LiaUIHandlerBase, name, None)), name


def test_response_primitives_present():
    for name in (
        "_base_security_headers",
        "_send_bytes",
        "_send_json",
        "_send_event_stream_headers",
        "_write_sse_event",
        "_read_json_payload",
    ):
        assert callable(getattr(LiaUIHandlerBase, name, None)), name


def test_base_security_headers_is_staticmethod():
    # On the class dict, a @staticmethod appears as a staticmethod object.
    assert isinstance(LiaUIHandlerBase.__dict__["_base_security_headers"], staticmethod)


def test_rate_limit_and_public_gate_methods_present():
    for name in (
        "_check_rate_limit",
        "_get_trusted_client_ip",
        "_hash_public_user_id",
        "_check_public_daily_quota",
        "_is_public_visitor_request",
        "_handle_public_session_post",
        "_serve_public_page",
    ):
        assert callable(getattr(LiaUIHandlerBase, name, None)), name


def test_chat_lifecycle_methods_present():
    for name in (
        "_handle_chat_frontend_compat_get",
        "_handle_chat_frontend_compat_post",
        "_initialize_chat_request_context",
        "_persist_user_turn",
        "_persist_assistant_turn",
        "_persist_usage_events",
    ):
        assert callable(getattr(LiaUIHandlerBase, name, None)), name
