"""Verb-dispatch class for the Lia UI HTTP handler.

Phase 3 of the decouplingv1 plan moves the HTTP verb dispatchers
(`do_GET`, `do_OPTIONS`, `do_POST`, `do_PATCH`, `do_DELETE`, `do_PUT`),
the route-delegate methods they call, the UI-asset serving helpers, and
the chat-payload wrappers off `ui_server.LiaUIHandler` into this module.

The class here (`LiaUIHandler`) is the canonical export. `ui_server.py`
re-imports it via ``from .ui_server_handler_dispatch import LiaUIHandler``
so every existing consumer (tests, CLI entry point, wsgi harnesses)
continues to resolve the same type.

MRO: ``[LiaUIHandler, LiaUIHandlerBase, BaseHTTPRequestHandler, ...]``.
"""

from __future__ import annotations

import mimetypes
from datetime import datetime, timezone
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# Base class + wildcard constants/helpers: same pattern ui_server.py uses.
from .ui_server_constants import *  # noqa: F401, F403
from .ui_server_helpers import *  # noqa: F401, F403
from .ui_server_handler_base import LiaUIHandlerBase

# Domain controllers + dep-factory helpers consumed by the dispatch methods.
# Imported eagerly (not lazily) wherever ui_server.py itself imports them
# eagerly, and lazily inside methods for the controllers that ui_server.py
# also imports lazily. This mirrors the historical import pattern exactly.
from .chat_run_runtime import get_chat_run_coordinator
from .chat_runs_store import get_chat_run_events, load_chat_run, summarize_chat_run_metrics
from .chat_session_metrics import get_chat_session_metrics
from .citation_gap_registry import list_citation_gaps
from .contributions import list_contributions
from .conversation_store import list_distinct_topics, list_sessions, load_session
from .feedback import list_feedback, list_feedback_for_admin, load_feedback
from .form_guides import (
    build_guide_markdown_for_pdf as _build_guide_markdown_for_pdf,
    find_official_form_pdf_source,
    list_available_guides,
    resolve_guide,
)
from .instrumentation import emit_event, list_reasoning_events, wait_reasoning_events
from .jobs_store import load_job
from .llm_runtime import LLMRuntimeConfigInvalidError, resolve_llm_adapter
from .orchestration_settings import OrchestrationSettingsInvalidError, update_orchestration_settings
from .pipeline_c import get_run as get_pipeline_c_run
from .pipeline_c import get_timeline as get_pipeline_c_timeline
from .pipeline_c import list_runs as list_pipeline_c_runs
from .terms import get_terms_status, read_terms_text
# Note: `handle_analysis_post` is intentionally *not* imported at module
# level. Tests monkeypatch `ui_server.handle_analysis_post` to swap in a
# fake, so the dispatch method looks the name up lazily through the
# `ui_server` module at call time (see `do_POST`). Doing the import lazily
# also dodges a circular-import shape that surfaces under
# `python -m lia_graph.ui_server`.
from .ui_chat_controller import handle_api_chat_post, handle_api_chat_stream_post
from .ui_chat_payload import (
    _load_runtime_orchestration_settings,
    apply_api_chat_clarification,
    build_api_chat_success_payload,
    finalize_api_chat_response,
    parse_api_chat_request,
    send_api_chat_error,
)
from .ui_citation_profile_builders import (
    _apply_citation_profile_request_context,
    _build_citation_profile_facts,
    _build_citation_profile_lead,
    _build_citation_profile_sections,
    _build_fallback_citation_profile_payload,
    _build_structured_vigencia_detail,
    _collect_citation_profile_context,
    _collect_citation_profile_context_by_reference_key,
    _llm_citation_profile_payload,
    _render_citation_profile_payload,
    _should_skip_citation_profile_llm,
)
from .ui_form_guide_helpers import (
    _build_form_guide_page_assets,
    _find_catalog_entry_by_reference_key,
    _serialize_guide_catalog_entry,
)
from .ui_normative_processors import _render_normative_analysis_payload, _summarize_vigencia_llm
from .ui_reference_resolvers import _citation_targets_et_article
from .ui_route_controllers import handle_form_guides_get, handle_ops_get, handle_source_get
from .ui_server_deps import (
    _analysis_controller_deps,
    _chat_controller_deps,
    _write_controller_deps,
)
from .ui_source_view_processors import (
    _build_et_article_source_view_markdown,
    _build_source_download_filename,
    _build_source_view_href,
    _build_source_view_html,
    _build_source_view_summary_markdown,
    _build_user_source_profile,
    _pick_source_display_title,
    _render_source_view_markdown_html,
    _resolve_source_display_title,
    _resolve_source_view_material,
)
from .ui_text_utilities import (
    _build_clean_guide_markdown,
    _build_pdf_from_markdown,
    _coerce_http_url,
    _coerce_optional_text,
    _sanitize_question_context,
)
from .ui_write_controllers import (
    handle_chat_run_post,
    handle_contributions_post,
    handle_corpus_operation_post,
    handle_corpus_sync_to_wip_post,
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
from .usage_ledger import summarize_usage


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
        if self._handle_ingest_delta_get(path, parsed):
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

    def _handle_ingest_delta_get(self, path: str, parsed: Any) -> bool:
        from .ui_ingest_delta_controllers import handle_ingest_delta_get
        return handle_ingest_delta_get(
            self,
            path,
            parsed,
            deps={"corpus_dir": WORKSPACE_ROOT / "knowledge_base"},
        )

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
        from .ui_ingest_delta_controllers import handle_ingest_delta_post as _handle_ingest_delta_post
        if _handle_ingest_delta_post(
            self,
            path,
            parsed,
            deps={
                "corpus_dir": WORKSPACE_ROOT / "knowledge_base",
                "artifacts_dir": WORKSPACE_ROOT / "artifacts",
                "pattern": "**/*.md",
                "generation_id": "gen_active_rolling",
                "submit_worker": None,
            },
        ):
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

        from . import ui_server as _ui_server
        if _ui_server.handle_analysis_post(self, path, deps=_analysis_controller_deps()):
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
