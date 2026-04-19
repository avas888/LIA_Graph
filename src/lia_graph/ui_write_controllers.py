"""State-mutating POST surfaces for platform, form-guides, chat runs, terms,
contributions, ingestion, corpus ops, embedding ops, reindex, rollback, promote.

This module is the designated home for every write endpoint that does not
belong to a narrower domain controller (auth → ``ui_route_controllers`` /
``ui_user_management_controllers``, reads → domain-specific
``ui_*_controllers``). The 14 ``handle_*_post`` functions below are wired as
a group in ``do_POST`` via ``_write_controller_deps()`` on the handler.

Architecture rules (see ``docs/next/granularization_v1.md`` §Controller
Surface Catalog):

* Every handler takes ``(handler, path, *, deps)`` and returns ``bool``.
* ``False`` means "my URL didn't match, try the next one"; ``True`` means
  "request fully handled (response already sent)".
* Collaborators flow through ``deps``; stdlib + pure helpers are imported
  directly; dataclass constructors and stateful services (``ingestion_runtime``,
  ``ingest``, ``corpus_ops``, ``embedding_ops``, ``reindex_ops``) are injected.
* Fast path first: a lightweight prefix/exact match at the top of each
  handler lets the dispatcher short-circuit non-matching URLs without
  reading the request body.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from http import HTTPStatus
from pathlib import Path
from typing import Any


_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers para ingestion kanban (Phase 4)
# ---------------------------------------------------------------------------

_TYPE_LABELS = {
    "normative_base": "Normativa",
    "interpretative_guidance": "Interpretacion",
    "practica_erp": "Practica",
}

_TOPIC_LABELS = {
    "declaracion_renta": "Renta",
    "iva": "IVA",
    "laboral": "Laboral",
    "facturacion_electronica": "Facturacion",
    "estados_financieros_niif": "NIIF",
    "ica": "ICA",
    "calendario_obligaciones": "Calendarios",
}


def _type_label(t: str | None) -> str:
    return _TYPE_LABELS.get(t or "", t or "?")


def _topic_label(t: str | None) -> str:
    return _TOPIC_LABELS.get(t or "", t or "?")


def _find_doc(docs: list[dict[str, Any]], doc_id: str) -> dict[str, Any] | None:
    return next((d for d in docs if d.get("doc_id") == doc_id), None)


# Regex para rutas de ingestion Phase 4
_INGESTION_CLASSIFY_DOC_RE = re.compile(
    r"^/api/ingestion/sessions/([^/]+)/documents/([^/]+)/classify$"
)
_INGESTION_RESOLVE_DUPLICATE_RE = re.compile(
    r"^/api/ingestion/sessions/([^/]+)/documents/([^/]+)/resolve-duplicate$"
)
_INGESTION_ACCEPT_AUTOGENERAR_RE = re.compile(
    r"^/api/ingestion/sessions/([^/]+)/documents/([^/]+)/accept-autogenerar$"
)
_INGESTION_DOC_RETRY_RE = re.compile(
    r"^/api/ingestion/sessions/([^/]+)/documents/([^/]+)/retry$"
)
_INGESTION_AUTO_PROCESS_RE = re.compile(
    r"^/api/ingestion/sessions/([^/]+)/auto-process$"
)
_INGESTION_PURGE_AND_REPLACE_RE = re.compile(
    r"^/api/ingestion/sessions/([^/]+)/purge-and-replace$"
)


def handle_platform_post(handler: Any, path: str, *, deps: dict[str, Any]) -> bool:
    if path == "/api/embed/exchange":
        payload = handler._read_json_payload(object_error="Payload debe ser objeto JSON.")
        if payload is None:
            return True
        grant = str(payload.get("grant") or payload.get("host_grant") or "").strip()
        if not grant:
            handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "`grant` requerido."})
            return True
        try:
            exchanged = deps["exchange_host_grant"](
                grant,
                origin=handler._request_origin(),
                config_path=deps["host_integrations_config_path"],
                nonce_path=deps["auth_nonces_path"],
            )
        except deps["platform_auth_error_cls"] as exc:
            handler._send_auth_error(exc)
            return True
        deps["emit_audit_event"](
            "auth.embed.exchange",
            {
                "integration_id": ((exchanged.get("integration") or {}).get("integration_id")),
                "origin": handler._request_origin(),
                "tenant_id": ((exchanged.get("me") or {}).get("tenant_id")),
                "user_id": ((exchanged.get("me") or {}).get("user_id")),
            },
        )
        handler._send_json(HTTPStatus.OK, {"ok": True, **exchanged})
        return True

    if path == "/api/context/switch-company":
        payload = handler._read_json_payload(object_error="Payload debe ser objeto JSON.")
        if payload is None:
            return True
        try:
            auth_context = handler._resolve_auth_context(required=True)
            switched = deps["switch_active_company"](
                auth_context, str(payload.get("company_id", "")).strip()
            )
        except deps["platform_auth_error_cls"] as exc:
            handler._send_auth_error(exc)
            return True
        deps["emit_audit_event"](
            "auth.context.switch_company",
            {
                "tenant_id": auth_context.tenant_id,
                "user_id": auth_context.user_id,
                "from_company_id": auth_context.active_company_id,
                "to_company_id": str((switched.get("me") or {}).get("active_company_id") or ""),
            },
        )
        handler._send_json(HTTPStatus.OK, {"ok": True, **switched})
        return True

    return False


def handle_form_guides_post(handler: Any, path: str, *, deps: dict[str, Any]) -> bool:
    if path != "/api/form-guides/chat":
        return False

    payload = handler._read_json_payload()
    if payload is None:
        return True

    message = str(payload.get("message", "")).strip()
    if not message:
        handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "`message` requerido."})
        return True
    reference_key = str(payload.get("reference_key", "")).strip()
    if not reference_key:
        handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "`reference_key` requerido."})
        return True
    profile = str(payload.get("profile", "")).strip() or None
    package = deps["resolve_guide"](
        reference_key, profile=profile, root=deps["form_guides_root"]
    )
    if package is None:
        handler._send_json(HTTPStatus.NOT_FOUND, {"error": "guide_not_found"})
        return True
    chat_request = deps["guide_chat_request_cls"](
        message=message,
        reference_key=reference_key,
        profile=package.manifest.profile_id,
        selected_field_id=str(payload.get("selected_field_id", "")).strip() or None,
        active_section=str(payload.get("active_section", "")).strip() or None,
    )
    response = deps["run_guide_chat"](
        chat_request,
        package=package,
        runtime_config_path=deps["llm_runtime_config_path"],
    )
    handler._send_json(
        HTTPStatus.OK,
        {
            "ok": True,
            "answer_markdown": response.answer_markdown,
            "answer_mode": response.answer_mode,
            "grounding": response.grounding,
            "suggested_followups": list(response.suggested_followups),
        },
    )
    return True


def handle_chat_run_post(handler: Any, path: str, *, deps: dict[str, Any]) -> bool:
    match = deps["chat_run_milestones_route_re"].match(path)
    if not match:
        return False

    chat_run_id = str(match.group(1) or "").strip()
    if not chat_run_id:
        handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "`chat_run_id` requerido."})
        return True

    record = deps["get_chat_run"](chat_run_id, base_dir=deps["chat_runs_path"])
    if record is None:
        handler._send_json(
            HTTPStatus.NOT_FOUND,
            {"error": "chat_run_not_found", "chat_run_id": chat_run_id},
        )
        return True

    payload = handler._read_json_payload(object_error="Payload debe ser objeto JSON.")
    if payload is None:
        return True

    milestone = str(payload.get("milestone") or "").strip().lower()
    event_type_map = {
        "response_bubble_highlighted": "chat_run.ui.response_bubble_highlighted",
        "main_chat_displayed": "chat_run.ui.main_chat_displayed",
        "normative_displayed": "chat_run.ui.normative_displayed",
        "expert_panel_displayed": "chat_run.ui.expert_panel_displayed",
    }
    event_type = event_type_map.get(milestone)
    if event_type is None:
        handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "`milestone` invalido."})
        return True

    elapsed_ms = payload.get("elapsed_ms")
    try:
        normalized_elapsed_ms = round(max(0.0, float(elapsed_ms or 0.0)), 2)
    except (TypeError, ValueError):
        handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "`elapsed_ms` debe ser numerico."})
        return True

    details = payload.get("details")
    if details is not None and not isinstance(details, dict):
        handler._send_json(
            HTTPStatus.BAD_REQUEST, {"error": "`details` debe ser objeto si se envia."}
        )
        return True

    recorded = deps["record_chat_run_event_once"](
        chat_run_id,
        event_type=event_type,
        payload={
            "elapsed_ms": normalized_elapsed_ms,
            "source": str(payload.get("source") or "").strip() or None,
            "status": str(payload.get("status") or "").strip() or None,
            "details": dict(details or {}),
        },
        base_dir=deps["chat_runs_path"],
    )
    handler._send_json(
        HTTPStatus.OK,
        {
            "ok": True,
            "chat_run_id": chat_run_id,
            "milestone": milestone,
            "recorded": recorded,
        },
    )
    return True


def handle_terms_feedback_post(handler: Any, path: str, *, deps: dict[str, Any]) -> bool:
    if path == "/api/terms/accept":
        payload = handler._read_json_payload()
        if payload is None:
            return True

        accepted_by = str(payload.get("accepted_by", "ui_user")).strip() or "ui_user"
        status = deps["accept_terms"](
            accepted_by=accepted_by,
            policy_path=deps["terms_policy_path"],
            state_path=deps["terms_state_path"],
        )
        handler._send_json(HTTPStatus.OK, {"accepted": True, "status": status})
        return True

    if path == "/api/feedback":
        payload = handler._read_json_payload()
        if payload is None:
            return True
        try:
            auth_context = handler._resolve_auth_context(required=True)
        except deps["platform_auth_error_cls"] as exc:
            handler._send_auth_error(exc)
            return True

        trace_id = str(payload.get("trace_id", "")).strip()
        if not trace_id:
            handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "`trace_id` requerido."})
            return True
        rating = handler._resolve_feedback_rating(payload)
        if rating is None:
            handler._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "`rating` debe ser entero 1-5 o `vote` debe ser up|down|neutral."},
            )
            return True
        record = deps["feedback_record_cls"](
            trace_id=trace_id,
            session_id=payload.get("session_id"),
            rating=int(rating),
            tenant_id=auth_context.tenant_id,
            user_id=auth_context.user_id,
            company_id=auth_context.active_company_id,
            integration_id=auth_context.integration_id,
            tags=list(payload.get("tags", [])),
            comment=str(payload.get("comment", ""))[:500],
            vote=str(payload.get("vote") or payload.get("thumb") or "").strip().lower(),
            source="api",
            created_by=auth_context.user_id,
            docs_used=list(payload.get("docs_used", [])),
            layer_contributions=dict(payload.get("layer_contributions", {})),
            pain_detected=str(payload.get("pain_detected", "")),
            task_detected=str(payload.get("task_detected", "")),
            question_text=str(payload.get("question_text", ""))[:2000],
            answer_text=str(payload.get("answer_text", ""))[:5000],
        )
        try:
            deps["save_feedback"](record, base_dir=deps["feedback_path"])
        except Exception as exc:
            _log.error("feedback save failed: %s", exc, exc_info=True)
            handler._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": f"No se pudo guardar feedback: {exc}"},
            )
            return True
        handler._send_json(
            HTTPStatus.OK,
            {"ok": True, "trace_id": trace_id, "feedback": record.to_dict()},
        )
        return True

    if path == "/api/feedback/comment":
        payload = handler._read_json_payload()
        if payload is None:
            return True
        try:
            auth_context = handler._resolve_auth_context(required=True)
        except deps["platform_auth_error_cls"] as exc:
            handler._send_auth_error(exc)
            return True

        trace_id = str(payload.get("trace_id", "")).strip()
        if not trace_id:
            handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "`trace_id` requerido."})
            return True
        comment = str(payload.get("comment", "")).strip()[:500]
        deps["update_feedback_comment"](
            trace_id,
            comment,
            tenant_id=auth_context.tenant_id,
            base_dir=deps["feedback_path"],
        )
        handler._send_json(HTTPStatus.OK, {"ok": True, "trace_id": trace_id})
        return True

    return False


def handle_contributions_post(handler: Any, path: str, *, deps: dict[str, Any]) -> bool:
    if path == "/api/contributions":
        payload = handler._read_json_payload()
        if payload is None:
            return True
        try:
            auth_context = handler._resolve_auth_context(required=True)
        except deps["platform_auth_error_cls"] as exc:
            handler._send_auth_error(exc)
            return True

        topic = str(payload.get("topic", "")).strip()
        content_md = str(payload.get("content_markdown", "")).strip()
        if not topic or not content_md:
            handler._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "`topic` y `content_markdown` requeridos."},
            )
            return True
        contribution = deps["contribution_cls"](
            contribution_id="",
            topic=topic,
            content_markdown=content_md[:5000],
            authority_claim=str(payload.get("authority_claim", ""))[:200],
            submitter_id=auth_context.user_id[:100],
            tenant_id=auth_context.tenant_id[:100],
        )
        deps["save_contribution"](contribution, base_dir=deps["contributions_path"])
        handler._send_json(
            HTTPStatus.OK,
            {"ok": True, "contribution_id": contribution.contribution_id},
        )
        return True

    if path.startswith("/api/contributions/") and path.endswith("/approve"):
        parts = path.split("/")
        contribution_id = parts[3] if len(parts) >= 5 else ""
        payload = handler._read_json_payload()
        if payload is None:
            return True
        try:
            auth_context = handler._resolve_auth_context(required=True)
            tenant_scope = handler._admin_tenant_scope(auth_context)
        except deps["platform_auth_error_cls"] as exc:
            handler._send_auth_error(exc)
            return True

        result = deps["approve_contribution"](
            contribution_id,
            review_comment=str(payload.get("review_comment", ""))[:500],
            base_dir=deps["contributions_path"],
            tenant_id=tenant_scope,
        )
        if result is None:
            handler._send_json(
                HTTPStatus.NOT_FOUND, {"error": "Contribucion no encontrada."}
            )
            return True
        handler._send_json(
            HTTPStatus.OK, {"ok": True, "contribution": result.to_dict()}
        )
        return True

    if path.startswith("/api/contributions/") and path.endswith("/reject"):
        parts = path.split("/")
        contribution_id = parts[3] if len(parts) >= 5 else ""
        payload = handler._read_json_payload()
        if payload is None:
            return True
        try:
            auth_context = handler._resolve_auth_context(required=True)
            tenant_scope = handler._admin_tenant_scope(auth_context)
        except deps["platform_auth_error_cls"] as exc:
            handler._send_auth_error(exc)
            return True

        result = deps["reject_contribution"](
            contribution_id,
            review_comment=str(payload.get("review_comment", ""))[:500],
            base_dir=deps["contributions_path"],
            tenant_id=tenant_scope,
        )
        if result is None:
            handler._send_json(
                HTTPStatus.NOT_FOUND, {"error": "Contribucion no encontrada."}
            )
            return True
        handler._send_json(
            HTTPStatus.OK, {"ok": True, "contribution": result.to_dict()}
        )
        return True

    return False


def handle_ingestion_post(handler: Any, path: str, *, deps: dict[str, Any]) -> bool:
    if not path.startswith("/api/ingestion") and path != "/api/corpora":
        return False

    ingestion_runtime = deps["ingestion_runtime"]

    if path == "/api/corpora":
        payload = handler._read_json_payload()
        if payload is None:
            return True
        label = str(payload.get("label", "")).strip()
        if not label:
            handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "`label` es obligatorio."})
            return True
        slug = str(payload.get("slug", "")).strip() or None
        keywords_strong = payload.get("keywords_strong") or []
        keywords_weak = payload.get("keywords_weak") or []
        if not isinstance(keywords_strong, list):
            keywords_strong = [str(keywords_strong)]
        if not isinstance(keywords_weak, list):
            keywords_weak = [str(keywords_weak)]
        try:
            entry = ingestion_runtime.register_corpus(
                label=label,
                slug=slug,
                keywords_strong=[str(k).strip() for k in keywords_strong if str(k).strip()],
                keywords_weak=[str(k).strip() for k in keywords_weak if str(k).strip()],
            )
        except ValueError as exc:
            error = str(exc)
            if error == "duplicate_key":
                handler._send_json(
                    HTTPStatus.CONFLICT,
                    {"error": "Ya existe una categoría con esa clave."},
                )
                return True
            handler._send_json(HTTPStatus.BAD_REQUEST, {"error": error})
            return True
        handler._send_json(HTTPStatus.CREATED, {"ok": True, "corpus": entry})
        return True

    if path == "/api/ingestion/sessions":
        payload = handler._read_json_payload()
        if payload is None:
            return True

        corpus = str(payload.get("corpus", "")).strip()
        if not corpus:
            handler._send_json(
                HTTPStatus.BAD_REQUEST, {"error": "`corpus` es obligatorio."}
            )
            return True

        # ingestion_fixv1 Phase 2: preflight gate. Refuse to start a new session
        # when WIP corpus_generations is empty AND we are running on the Supabase
        # backend. Local-fs backend (tests) skips this check.
        try:
            from .supabase_client import get_storage_backend

            if (get_storage_backend() or "").strip().lower() == "supabase":
                from .ingest import (
                    WipNoActiveGenerationError,
                    _assert_wip_has_active_generation,
                )

                try:
                    _assert_wip_has_active_generation()
                except WipNoActiveGenerationError as gen_exc:
                    handler._send_json(
                        HTTPStatus.CONFLICT,
                        {
                            "error": "wip_no_active_generation",
                            "details": str(gen_exc),
                        },
                    )
                    return True
        except Exception:  # noqa: BLE001
            pass

        try:
            session = ingestion_runtime.create_session(corpus)
        except ValueError as exc:
            error = str(exc)
            if error == "corpus_inactive":
                handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "corpus_inactive"})
                return True
            handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "unknown_corpus"})
            return True
        handler._send_json(HTTPStatus.OK, {"ok": True, "session": session.to_dict()})
        return True

    if path == "/api/ingestion/classify":
        payload = handler._read_json_payload()
        if payload is None:
            return True
        filename = str(payload.get("filename", "")).strip()
        body_preview = str(payload.get("body_preview", ""))
        if not filename:
            handler._send_json(
                HTTPStatus.BAD_REQUEST, {"error": "`filename` es obligatorio."}
            )
            return True
        try:
            from .ingestion_classifier import classify_upload

            result = classify_upload(filename, body_preview.encode("utf-8"))
            suggestion = None
            if result.is_raw and result.suggestion_topic:
                suggestion = (
                    f"Sugerimos: {_topic_label(result.suggestion_topic)} "
                    f"· {_type_label(result.suggestion_type)} "
                    f"({int(result.combined_confidence * 100)}%)"
                )
            handler._send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "detected_topic": result.detected_topic,
                    "topic_confidence": result.topic_confidence,
                    "topic_source": result.topic_source,
                    "detected_type": result.detected_type,
                    "type_confidence": result.type_confidence,
                    "type_source": result.type_source,
                    "combined_confidence": result.combined_confidence,
                    "llm_invoked": result.llm_invoked,
                    "is_raw": result.is_raw,
                    "suggestion": suggestion,
                },
            )
        except Exception as exc:  # noqa: BLE001
            handler._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "classify_failed", "details": str(exc)},
            )
        return True

    match_classify_doc = _INGESTION_CLASSIFY_DOC_RE.match(path)
    if match_classify_doc:
        session_id = match_classify_doc.group(1)
        doc_id = match_classify_doc.group(2)
        payload = handler._read_json_payload()
        if payload is None:
            return True
        batch_type = payload.get("batch_type")
        topic = payload.get("topic")
        with ingestion_runtime._lock:
            session = ingestion_runtime._sessions.get(session_id)
            if session is None:
                handler._send_json(
                    HTTPStatus.NOT_FOUND, {"error": "session_not_found"}
                )
                return True
            doc = _find_doc(session.get("documents", []), doc_id)
            if doc is None:
                handler._send_json(
                    HTTPStatus.NOT_FOUND, {"error": "document_not_found"}
                )
                return True
            if batch_type:
                doc["batch_type"] = str(batch_type)
                doc["detected_type"] = str(batch_type)
            if topic:
                doc["detected_topic"] = str(topic)
            doc["combined_confidence"] = 1.0
            doc["classification_source"] = "manual"
            doc["is_raw"] = False
            doc["status"] = "queued"
            doc["updated_at"] = (
                ingestion_runtime._materialize_document(doc).updated_at or ""
            )
            from datetime import datetime, timezone

            doc["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            ingestion_runtime._save_session_locked(session)
        handler._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "document": {
                    "doc_id": doc_id,
                    "status": "queued",
                    "batch_type": doc.get("batch_type"),
                    "detected_type": doc.get("detected_type"),
                    "detected_topic": doc.get("detected_topic"),
                    "combined_confidence": 1.0,
                    "classification_source": "manual",
                    "is_raw": False,
                },
            },
        )
        return True

    match_accept_ag = _INGESTION_ACCEPT_AUTOGENERAR_RE.match(path)
    if match_accept_ag:
        session_id = match_accept_ag.group(1)
        doc_id = match_accept_ag.group(2)
        payload = handler._read_json_payload()
        if payload is None:
            return True
        action = str(payload.get("action", "")).strip()
        if action not in ("accept_synonym", "accept_new_topic"):
            handler._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "action debe ser 'accept_synonym' o 'accept_new_topic'"},
            )
            return True
        with ingestion_runtime._lock:
            session = ingestion_runtime._sessions.get(session_id)
            if session is None:
                handler._send_json(
                    HTTPStatus.NOT_FOUND, {"error": "session_not_found"}
                )
                return True
            doc = _find_doc(session.get("documents", []), doc_id)
            if doc is None:
                handler._send_json(
                    HTTPStatus.NOT_FOUND, {"error": "document_not_found"}
                )
                return True

            batch_type = str(
                payload.get("type") or doc.get("batch_type") or "normative_base"
            )

            if action == "accept_synonym":
                resolved_topic = doc.get("autogenerar_resolved_topic")
                if not resolved_topic:
                    handler._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {"error": "no hay tema existente sugerido"},
                    )
                    return True
                doc["detected_topic"] = resolved_topic
                doc["batch_type"] = batch_type
                doc["detected_type"] = batch_type
                doc["combined_confidence"] = 0.95
                doc["classification_source"] = "autogenerar"
                doc["is_raw"] = False
                doc["status"] = "queued"
                doc["stage"] = "queued"
                from datetime import datetime, timezone

                doc["updated_at"] = (
                    datetime.now(timezone.utc).replace(microsecond=0).isoformat()
                )
                ingestion_runtime._save_session_locked(session)
                handler._send_json(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "document": {
                            "doc_id": doc_id,
                            "status": "queued",
                            "batch_type": batch_type,
                            "detected_topic": resolved_topic,
                            "combined_confidence": 0.95,
                            "classification_source": "autogenerar",
                            "is_raw": False,
                        },
                    },
                )
                return True

            edited_label = str(
                payload.get("edited_label") or doc.get("autogenerar_label") or ""
            ).strip()
            if not edited_label or len(edited_label) < 3:
                handler._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "label demasiado corto (min 3 caracteres)"},
                )
                return True

        try:
            ag_label = doc.get("autogenerar_label") or edited_label
            new_entry = ingestion_runtime.register_corpus(
                label=edited_label,
                keywords_strong=[ag_label] if ag_label != edited_label else [edited_label],
            )
            new_topic_key = new_entry["key"]
        except ValueError as exc:
            if str(exc) == "duplicate_key":
                from .ingestion_runtime import _slugify_key

                new_topic_key = _slugify_key(edited_label)
            else:
                handler._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return True

        with ingestion_runtime._lock:
            session = ingestion_runtime._sessions.get(session_id)
            if session:
                doc = _find_doc(session.get("documents", []), doc_id)
                if doc:
                    doc["detected_topic"] = new_topic_key
                    doc["batch_type"] = batch_type
                    doc["detected_type"] = batch_type
                    doc["combined_confidence"] = 1.0
                    doc["classification_source"] = "autogenerar"
                    doc["is_raw"] = False
                    doc["status"] = "queued"
                    doc["stage"] = "queued"
                    from datetime import datetime, timezone

                    doc["updated_at"] = (
                        datetime.now(timezone.utc).replace(microsecond=0).isoformat()
                    )
                    ingestion_runtime._save_session_locked(session)
        handler._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "new_topic": new_topic_key,
                "document": {
                    "doc_id": doc_id,
                    "status": "queued",
                    "batch_type": batch_type,
                    "detected_topic": new_topic_key,
                    "combined_confidence": 1.0,
                    "classification_source": "autogenerar",
                    "is_raw": False,
                },
            },
        )
        return True

    match_resolve_dup = _INGESTION_RESOLVE_DUPLICATE_RE.match(path)
    if match_resolve_dup:
        session_id = match_resolve_dup.group(1)
        doc_id = match_resolve_dup.group(2)
        payload = handler._read_json_payload()
        if payload is None:
            return True
        action = str(payload.get("action", "")).strip()
        if action not in {"replace", "add_new", "discard"}:
            handler._send_json(
                HTTPStatus.BAD_REQUEST, {"error": f"action invalido: {action}"}
            )
            return True
        with ingestion_runtime._lock:
            session = ingestion_runtime._sessions.get(session_id)
            if session is None:
                handler._send_json(
                    HTTPStatus.NOT_FOUND, {"error": "session_not_found"}
                )
                return True
            doc = _find_doc(session.get("documents", []), doc_id)
            if doc is None:
                handler._send_json(
                    HTTPStatus.NOT_FOUND, {"error": "document_not_found"}
                )
                return True

            if action == "replace":
                existing_doc_id = doc.get("dedup_existing_doc_id")
                purged = 0
                if existing_doc_id:
                    try:
                        from .ingestion_dedup import purge_document
                        from .supabase_client import get_supabase_client as get_client

                        client = get_client()
                        purged = purge_document(
                            existing_doc_id, session.get("corpus", ""), client
                        )
                    except Exception:  # noqa: BLE001
                        pass
                    doc["replaced_doc_id"] = existing_doc_id
                    doc["doc_id"] = existing_doc_id
                doc["status"] = "queued"
                doc["dedup_match_type"] = None
                ingestion_runtime._save_session_locked(session)
                handler._send_json(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "document": {
                            "doc_id": doc["doc_id"],
                            "status": "queued",
                            "purged_chunks": purged,
                        },
                    },
                )
            elif action == "add_new":
                doc["status"] = "queued"
                doc["dedup_match_type"] = None
                ingestion_runtime._save_session_locked(session)
                handler._send_json(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "document": {"doc_id": doc["doc_id"], "status": "queued"},
                    },
                )
            else:  # discard
                session["documents"] = [
                    d for d in session.get("documents", []) if d.get("doc_id") != doc_id
                ]
                ingestion_runtime._save_session_locked(session)
                handler._send_json(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "document": {"doc_id": doc_id, "status": "discarded"},
                    },
                )
        return True

    match_auto = _INGESTION_AUTO_PROCESS_RE.match(path)
    if match_auto:
        session_id = match_auto.group(1)
        payload = handler._read_json_payload()
        if payload is None:
            return True
        max_concurrency = int(payload.get("max_concurrency", 5))
        auto_accept_threshold = float(payload.get("auto_accept_threshold", 0.95))
        with ingestion_runtime._lock:
            session = ingestion_runtime._sessions.get(session_id)
            if session is None:
                handler._send_json(
                    HTTPStatus.NOT_FOUND, {"error": "session_not_found"}
                )
                return True
            queued = 0
            auto_queued = 0
            raw_blocked = 0
            from datetime import datetime, timezone

            now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            force_queue = auto_accept_threshold <= 0.0
            for doc in session.get("documents", []):
                status = doc.get("status", "")
                if status == "queued":
                    queued += 1
                elif status in ("raw", "needs_classification"):
                    conf = float(doc.get("combined_confidence", 0) or 0)
                    has_topic = bool(doc.get("detected_topic"))
                    has_type = bool(doc.get("detected_type"))
                    if force_queue or (
                        conf >= auto_accept_threshold and has_topic and has_type
                    ):
                        doc["status"] = "queued"
                        doc["stage"] = "queued"
                        doc["is_raw"] = False
                        doc["classification_source"] = (
                            doc.get("classification_source") or "auto_accepted"
                        )
                        doc["updated_at"] = now_iso
                        auto_queued += 1
                        queued += 1
                    else:
                        raw_blocked += 1
            session["auto_processing"] = True
            ingestion_runtime._save_session_locked(session)
        handler._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "session_id": session_id,
                "auto_processing": True,
                "queued": queued,
                "auto_queued": auto_queued,
                "raw_blocked": raw_blocked,
                "active_slots": 0,
                "max_concurrency": max_concurrency,
            },
        )
        return True

    match_files = deps["ingestion_files_route_re"].match(path)
    if match_files:
        session_id = match_files.group(1)
        filename = str(handler.headers.get("X-Upload-Filename", "")).strip()
        mime = (
            str(handler.headers.get("X-Upload-Mime", "")).strip()
            or "application/octet-stream"
        )
        if not filename:
            handler._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "`X-Upload-Filename` es obligatorio."},
            )
            return True

        length_raw = handler.headers.get("Content-Length", "0")
        try:
            length = int(length_raw)
        except ValueError:
            handler._send_json(
                HTTPStatus.BAD_REQUEST, {"error": "Content-Length invalido."}
            )
            return True
        if length <= 0:
            handler._send_json(
                HTTPStatus.BAD_REQUEST, {"error": "Body vacio en upload."}
            )
            return True

        batch_type = (
            str(handler.headers.get("X-Upload-Batch-Type", "")).strip()
            or "normative_base"
        )
        source_relative_path = (
            str(handler.headers.get("X-Upload-Relative-Path", "")).strip() or None
        )
        autodetect = batch_type in ("autogenerar", "autodetectar")
        if not autodetect and batch_type not in {
            "normative_base",
            "interpretative_guidance",
            "practica_erp",
        }:
            handler._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": f"batch_type invalido: {batch_type}"},
            )
            return True

        content = handler.rfile.read(length)

        content_hash = hashlib.sha256(content).hexdigest()
        dedup_info: dict[str, Any] = {}
        try:
            from .ingestion_dedup import check_duplicate
            from .supabase_client import get_supabase_client as get_client

            client = get_client()
            body_preview_text = content[:5120].decode("utf-8", errors="replace")
            with ingestion_runtime._lock:
                sess = ingestion_runtime._sessions.get(session_id)
            corpus = str((sess or {}).get("corpus", "")) if sess else ""
            dedup_result = check_duplicate(
                filename, content_hash, body_preview_text, corpus, client
            )
            if dedup_result.is_duplicate:
                dedup_info = {
                    "dedup_match_type": dedup_result.match_type,
                    "dedup_match_reason": dedup_result.match_reason,
                    "dedup_existing_doc_id": dedup_result.existing_doc_id,
                    "dedup_existing_filename": dedup_result.existing_filename,
                }
        except Exception:  # noqa: BLE001
            pass

        classify_info: dict[str, Any] = {}
        effective_batch_type = "normative_base" if autodetect else batch_type
        if autodetect:
            try:
                from .ingestion_classifier import classify_upload

                cls_result = classify_upload(filename, content)
                classify_info = {
                    "detected_topic": cls_result.detected_topic,
                    "topic_confidence": cls_result.topic_confidence,
                    "detected_type": cls_result.detected_type,
                    "type_confidence": cls_result.type_confidence,
                    "combined_confidence": cls_result.combined_confidence,
                    "classification_source": cls_result.topic_source or "keywords",
                    "is_raw": cls_result.is_raw,
                    "suggestion_topic": cls_result.suggestion_topic,
                    "suggestion_type": cls_result.suggestion_type,
                }
                if cls_result.detected_type and not cls_result.is_raw:
                    effective_batch_type = cls_result.detected_type
            except Exception:  # noqa: BLE001
                pass

        try:
            document = ingestion_runtime.add_file(
                session_id,
                filename=filename,
                mime=mime,
                content=content,
                batch_type=effective_batch_type,
            )
        except KeyError:
            handler._send_json(HTTPStatus.NOT_FOUND, {"error": "session_not_found"})
            return True
        except RuntimeError as exc:
            if str(exc) == "session_processing":
                handler._send_json(
                    HTTPStatus.CONFLICT,
                    {
                        "error": "session_processing",
                        "details": "No se pueden agregar archivos mientras el lote está en proceso.",
                    },
                )
                return True
            handler._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "upload_failed", "details": str(exc)},
            )
            return True

        if (dedup_info or classify_info or source_relative_path) and document.status != "bounced":
            with ingestion_runtime._lock:
                sess_data = ingestion_runtime._sessions.get(session_id)
                if sess_data:
                    doc_internal = _find_doc(sess_data.get("documents", []), document.doc_id)
                    if doc_internal and str(doc_internal.get("status")) != "bounced":
                        doc_internal.update(classify_info)
                        doc_internal.update(dedup_info)
                        if source_relative_path:
                            doc_internal["source_relative_path"] = source_relative_path
                        dedup_type = dedup_info.get("dedup_match_type")
                        if dedup_type == "exact_duplicate":
                            doc_internal["status"] = "skipped_duplicate"
                            doc_internal["stage"] = "skipped_duplicate"
                        elif dedup_type in ("near_duplicate", "revision"):
                            doc_internal["status"] = "pending_dedup"
                            doc_internal["stage"] = "pending_dedup"
                            doc_internal["duplicate_of"] = dedup_info.get(
                                "dedup_existing_doc_id"
                            )
                        elif classify_info.get("is_raw"):
                            doc_internal["status"] = "raw"
                            doc_internal["stage"] = "raw"
                        ingestion_runtime._save_session_locked(sess_data)
                    if doc_internal:
                        document = ingestion_runtime._materialize_document(doc_internal)

        handler._send_json(HTTPStatus.OK, {"ok": True, "document": document.to_dict()})
        return True

    match_process = deps["ingestion_process_route_re"].match(path)
    if match_process:
        session_id = match_process.group(1)
        try:
            result = ingestion_runtime.start_processing(session_id)
        except KeyError:
            handler._send_json(HTTPStatus.NOT_FOUND, {"error": "session_not_found"})
            return True
        handler._send_json(HTTPStatus.OK, {"ok": True, **result})
        return True

    match_retry = deps["ingestion_retry_route_re"].match(path)
    if match_retry:
        session_id = match_retry.group(1)
        try:
            result = ingestion_runtime.retry(session_id)
        except KeyError:
            handler._send_json(HTTPStatus.NOT_FOUND, {"error": "session_not_found"})
            return True
        handler._send_json(HTTPStatus.OK, {"ok": True, **result})
        return True

    match_validate = deps["ingestion_validate_batch_route_re"].match(path)
    if match_validate:
        session_id = match_validate.group(1)
        try:
            result = ingestion_runtime.start_processing(
                session_id, retry_failed=False, gate_only=True
            )
        except KeyError:
            handler._send_json(HTTPStatus.NOT_FOUND, {"error": "session_not_found"})
            return True
        except RuntimeError as exc:
            if str(exc) == "session_processing":
                handler._send_json(
                    HTTPStatus.CONFLICT,
                    {"error": "session_processing", "details": "Sesión en proceso."},
                )
                return True
            raise
        handler._send_json(HTTPStatus.OK, {"ok": True, **result})
        return True

    match_delete_failed = deps["ingestion_delete_failed_route_re"].match(path)
    if match_delete_failed:
        session_id = match_delete_failed.group(1)
        try:
            result = ingestion_runtime.delete_failed(session_id)
        except KeyError:
            handler._send_json(HTTPStatus.NOT_FOUND, {"error": "session_not_found"})
            return True
        except RuntimeError as exc:
            if str(exc) == "session_processing":
                handler._send_json(
                    HTTPStatus.CONFLICT,
                    {
                        "error": "session_processing",
                        "details": "No se pueden eliminar fallidos mientras el lote está en proceso.",
                    },
                )
                return True
            handler._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "delete_failed_error", "details": str(exc)},
            )
            return True
        handler._send_json(HTTPStatus.OK, {"ok": True, **result})
        return True

    match_stop = deps["ingestion_stop_route_re"].match(path)
    if match_stop:
        session_id = match_stop.group(1)
        try:
            result = ingestion_runtime.stop_processing(session_id)
        except KeyError:
            handler._send_json(HTTPStatus.NOT_FOUND, {"error": "session_not_found"})
            return True
        except Exception as exc:  # noqa: BLE001
            handler._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "stop_error", "details": str(exc)},
            )
            return True
        handler._send_json(HTTPStatus.OK, {"ok": True, **result})
        return True

    match_clear = deps["ingestion_clear_batch_route_re"].match(path)
    if match_clear:
        session_id = match_clear.group(1)
        try:
            result = ingestion_runtime.clear_batch(session_id)
        except KeyError:
            handler._send_json(HTTPStatus.NOT_FOUND, {"error": "session_not_found"})
            return True
        except RuntimeError as exc:
            if str(exc) == "session_processing":
                handler._send_json(
                    HTTPStatus.CONFLICT,
                    {
                        "error": "session_processing",
                        "details": "No se puede limpiar el lote mientras está en proceso.",
                    },
                )
                return True
            handler._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "clear_batch_error", "details": str(exc)},
            )
            return True
        handler._send_json(HTTPStatus.OK, {"ok": True, **result})
        return True

    if path == "/api/ingestion/preflight":
        payload = handler._read_json_payload()
        if payload is None:
            return True
        files_raw = payload.get("files")
        if not isinstance(files_raw, list) or not files_raw:
            handler._send_json(
                HTTPStatus.BAD_REQUEST, {"error": "`files` debe ser una lista no vacia."}
            )
            return True
        corpus = str(payload.get("corpus", "autogenerar")).strip()
        try:
            from .ingestion_preflight import run_preflight, manifest_to_dict

            client = None
            try:
                from .supabase_client import get_supabase_client

                client = get_supabase_client()
            except Exception:  # noqa: BLE001
                pass
            ledger = None
            try:
                ledger_path = (
                    ingestion_runtime.workspace_root
                    / "artifacts"
                    / "ingestion"
                    / "ledger.json"
                )
                if ledger_path.exists():
                    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                pass
            wip_checksums: dict[str, dict[str, str]] = {}
            try:
                for session in ingestion_runtime._sessions.values():
                    for doc in session.get("documents", []):
                        cs = str(doc.get("checksum", "")).strip()
                        if cs and doc.get("status") not in ("failed", "skipped_duplicate"):
                            wip_checksums[cs] = {
                                "doc_id": str(doc.get("doc_id", "")),
                                "session_id": str(session.get("session_id", "")),
                            }
            except Exception:  # noqa: BLE001
                pass
            manifest = run_preflight(
                files_raw, corpus, client, ledger=ledger, wip_checksums=wip_checksums
            )
            handler._send_json(
                HTTPStatus.OK, {"ok": True, "manifest": manifest_to_dict(manifest)}
            )
        except Exception as exc:  # noqa: BLE001
            handler._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "preflight_failed", "details": str(exc)},
            )
        return True

    match_purge = _INGESTION_PURGE_AND_REPLACE_RE.match(path)
    if match_purge:
        session_id = match_purge.group(1)
        payload = handler._read_json_payload()
        if payload is None:
            return True
        doc_ids = payload.get("doc_ids")
        if not isinstance(doc_ids, list) or not doc_ids:
            handler._send_json(
                HTTPStatus.BAD_REQUEST, {"error": "`doc_ids` debe ser una lista no vacia."}
            )
            return True
        corpus = str(payload.get("corpus", "")).strip()
        if not corpus:
            with ingestion_runtime._lock:
                sess = ingestion_runtime._sessions.get(session_id)
            if sess:
                corpus = str(sess.get("corpus", ""))
        if not corpus:
            handler._send_json(
                HTTPStatus.BAD_REQUEST, {"error": "`corpus` es obligatorio."}
            )
            return True
        try:
            from .ingestion_dedup import purge_document
            from .supabase_client import get_supabase_client as get_client

            client = get_client()
            details = []
            total_chunks = 0
            for doc_id in doc_ids:
                doc_id = str(doc_id).strip()
                if not doc_id:
                    continue
                chunks_deleted = purge_document(doc_id, corpus, client)
                total_chunks += chunks_deleted
                details.append({"doc_id": doc_id, "chunks_deleted": chunks_deleted})
            handler._send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "purged": len(details),
                    "chunks_deleted": total_chunks,
                    "details": details,
                },
            )
        except Exception as exc:  # noqa: BLE001
            handler._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "purge_failed", "details": str(exc)},
            )
        return True

    return False


def handle_corpus_sync_to_wip_post(handler: Any, path: str, *, deps: dict[str, Any]) -> bool:
    """Sync already-built JSONL indexes to local Supabase WIP (no reindex)."""
    if path != "/api/ops/corpus/sync-to-wip":
        return False

    index_path = deps.get("index_file_path", Path("artifacts/document_index.jsonl"))
    chunk_path = index_path.parent / "document_chunk_index.jsonl"

    if not index_path.exists() or not chunk_path.exists():
        handler._send_json(
            HTTPStatus.BAD_REQUEST,
            {"error": "JSONL indexes not found. Run reindex first."},
        )
        return True

    try:
        docs: list[dict[str, Any]] = []
        with open(index_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    docs.append(json.loads(line))

        chunks: list[dict[str, Any]] = []
        with open(chunk_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    chunks.append(json.loads(line))

        from .ingest import (
            WipNoActiveGenerationError,
            _assert_wip_has_active_generation,
            sync_to_supabase_targets,
        )

        try:
            wip_generation: str | None = _assert_wip_has_active_generation()
        except WipNoActiveGenerationError as gen_exc:
            _log.warning("sync-to-wip refused: %s", gen_exc)
            handler._send_json(
                HTTPStatus.CONFLICT,
                {"error": "wip_no_active_generation", "details": str(gen_exc)},
            )
            return True

        result = sync_to_supabase_targets(
            docs, chunks, target="wip", sync_generation=wip_generation
        )
        _log.info("sync-to-wip completed: %d docs, %d chunks", len(docs), len(chunks))
        handler._send_json(
            HTTPStatus.OK,
            {
                "synced": True,
                "documents": len(docs),
                "chunks": len(chunks),
                "detail": result,
            },
        )
    except Exception as exc:
        _log.exception("sync-to-wip failed")
        handler._send_json(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {"error": f"sync_to_wip_failed: {exc}"},
        )
    return True


def handle_corpus_operation_post(handler: Any, path: str, *, deps: dict[str, Any]) -> bool:
    if path not in {
        "/api/ops/corpus/rebuild-from-wip",
        "/api/ops/corpus/rebuild-from-wip/resume",
        "/api/ops/corpus/rebuild-from-wip/restart",
        "/api/ops/corpus/rollback",
        "/api/ops/corpus/wip-audit",
    }:
        return False

    payload = handler._read_json_payload(object_error="Payload debe ser objeto JSON.")
    if payload is None:
        payload = {}

    try:
        from .corpus_ops import (
            resume_rebuild_from_wip_job,
            restart_rebuild_from_wip_job,
            start_rebuild_from_wip_job,
            start_rollback_job,
            start_wip_audit_job,
        )

        if path == "/api/ops/corpus/rebuild-from-wip":
            mode = str(payload.get("mode", "promote")).strip().lower() or "promote"
            force_full_upsert = bool(payload.get("force_full_upsert", False))
            job = start_rebuild_from_wip_job(
                mode=mode,
                base_dir=deps["jobs_path"],
                workspace_root=deps["workspace_root"],
                force_full_upsert=force_full_upsert,
            )
        elif path == "/api/ops/corpus/rebuild-from-wip/resume":
            job = resume_rebuild_from_wip_job(
                job_id=str(payload.get("job_id", "")).strip() or None,
                base_dir=deps["jobs_path"],
                workspace_root=deps["workspace_root"],
            )
        elif path == "/api/ops/corpus/rebuild-from-wip/restart":
            job = restart_rebuild_from_wip_job(
                base_dir=deps["jobs_path"],
                workspace_root=deps["workspace_root"],
            )
        elif path == "/api/ops/corpus/wip-audit":
            job = start_wip_audit_job(
                base_dir=deps["jobs_path"],
                workspace_root=deps["workspace_root"],
            )
        else:
            generation_id = str(payload.get("generation_id", "")).strip() or None
            job = start_rollback_job(
                generation_id=generation_id,
                base_dir=deps["jobs_path"],
            )
    except RuntimeError as exc:
        handler._send_json(
            HTTPStatus.CONFLICT, {"status": "failed", "error": str(exc)}
        )
        return True
    except Exception as exc:  # noqa: BLE001
        handler._send_json(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {"status": "failed", "error": str(exc)},
        )
        return True

    handler._send_json(
        HTTPStatus.ACCEPTED,
        {
            "ok": True,
            "job_id": job.job_id,
            "status": job.status,
            "job_type": job.job_type,
        },
    )
    return True


def handle_embedding_operation_post(handler: Any, path: str, *, deps: dict[str, Any]) -> bool:
    if path not in {
        "/api/ops/embedding/start",
        "/api/ops/embedding/stop",
        "/api/ops/embedding/resume",
    }:
        return False

    payload = handler._read_json_payload(object_error="Payload debe ser objeto JSON.")
    if payload is None:
        payload = {}

    try:
        from .embedding_ops import (
            resume_embedding_job,
            start_embedding_job,
            stop_embedding_job,
        )

        if path == "/api/ops/embedding/start":
            force = bool(payload.get("force", False))
            job = start_embedding_job(target="wip", force=force)
            handler._send_json(
                HTTPStatus.ACCEPTED,
                {"ok": True, "job_id": job.job_id, "status": job.status},
            )
        elif path == "/api/ops/embedding/stop":
            job_id = str(payload.get("job_id", "")).strip()
            if not job_id:
                handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "job_id requerido"})
                return True
            result = stop_embedding_job(job_id)
            handler._send_json(HTTPStatus.OK, result)
        elif path == "/api/ops/embedding/resume":
            job_id = str(payload.get("job_id", "")).strip()
            if not job_id:
                handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "job_id requerido"})
                return True
            job = resume_embedding_job(job_id)
            handler._send_json(
                HTTPStatus.ACCEPTED,
                {"ok": True, "job_id": job.job_id, "status": job.status},
            )
        else:
            return False
    except RuntimeError as exc:
        handler._send_json(
            HTTPStatus.CONFLICT, {"status": "failed", "error": str(exc)}
        )
    except Exception as exc:  # noqa: BLE001
        handler._send_json(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {"status": "failed", "error": str(exc)},
        )
    return True


def handle_reindex_operation_post(handler: Any, path: str, *, deps: dict[str, Any]) -> bool:
    if path not in {"/api/ops/reindex/start", "/api/ops/reindex/stop"}:
        return False

    payload = handler._read_json_payload(object_error="Payload debe ser objeto JSON.")
    if payload is None:
        payload = {}

    try:
        from .reindex_ops import start_reindex_job, stop_reindex_job

        if path == "/api/ops/reindex/start":
            mode = str(payload.get("mode", "from_source")).strip() or "from_source"
            job = start_reindex_job(mode=mode)
            handler._send_json(
                HTTPStatus.ACCEPTED,
                {"ok": True, "job_id": job.job_id, "status": job.status},
            )
        elif path == "/api/ops/reindex/stop":
            job_id = str(payload.get("job_id", "")).strip()
            if not job_id:
                handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "job_id requerido"})
                return True
            result = stop_reindex_job(job_id)
            handler._send_json(HTTPStatus.OK, result)
        else:
            return False
    except RuntimeError as exc:
        handler._send_json(
            HTTPStatus.CONFLICT, {"status": "failed", "error": str(exc)}
        )
    except Exception as exc:  # noqa: BLE001
        handler._send_json(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {"status": "failed", "error": str(exc)},
        )
    return True


def handle_rollback_post(handler: Any, path: str, *, deps: dict[str, Any]) -> bool:
    if path != "/api/ops/rollback":
        return False

    payload = handler._read_json_payload(object_error="Payload debe ser objeto JSON.")
    if payload is None:
        payload = {}

    generation_id = str(payload.get("generation_id", "")).strip() or None
    target = str(payload.get("target", "production")).strip().lower() or "production"

    try:
        from .ingest import rollback_generation

        result = rollback_generation(
            generation_id=generation_id,
            supabase_sync_target=target,
        )
    except Exception as exc:  # noqa: BLE001
        handler._send_json(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {"status": "failed", "error": str(exc)},
        )
        return True

    handler._send_json(HTTPStatus.OK, result)
    return True


def handle_promote_post(handler: Any, path: str, *, deps: dict[str, Any]) -> bool:
    if path != "/api/ops/promote":
        return False

    try:
        from .ingest import promote_generation

        result = promote_generation()
    except Exception as exc:  # noqa: BLE001
        handler._send_json(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {
                "status": "failed",
                "error": str(exc),
                "production_unchanged": True,
            },
        )
        return True

    handler._send_json(HTTPStatus.OK, result)
    return True


def handle_reindex_post(handler: Any, path: str, *, deps: dict[str, Any]) -> bool:
    if path not in {"/api/admin/reindex", "/api/ops/reindex"}:
        return False

    payload = handler._read_json_payload(object_error="Payload debe ser objeto JSON.")
    if payload is None:
        return True

    mode = str(payload.get("mode", "from_source")).strip().lower() or "from_source"
    missing_source_policy = (
        str(payload.get("missing_source_policy", "warn_continue")).strip().lower()
        or "warn_continue"
    )
    if mode not in {"from_source", "index_only"}:
        handler._send_json(
            HTTPStatus.BAD_REQUEST, {"error": "`mode` debe ser from_source|index_only."}
        )
        return True
    if missing_source_policy not in {"warn_continue", "skip_document", "fail_fast"}:
        handler._send_json(
            HTTPStatus.BAD_REQUEST,
            {
                "error": "`missing_source_policy` debe ser warn_continue|skip_document|fail_fast."
            },
        )
        return True
    skip_checksum_dedupe_raw = payload.get("skip_checksum_dedupe", True)
    if not isinstance(skip_checksum_dedupe_raw, bool):
        handler._send_json(
            HTTPStatus.BAD_REQUEST,
            {"error": "`skip_checksum_dedupe` debe ser booleano."},
        )
        return True

    replay_kwargs: dict[str, Any] = {
        "mode": mode,
        "missing_source_policy": missing_source_policy,
        "skip_checksum_dedupe": skip_checksum_dedupe_raw,
    }
    if path == "/api/ops/reindex":
        replay_kwargs["supabase_sync_target"] = "wip"
        replay_kwargs["auto_activate"] = True
    else:
        replay_kwargs["supabase_sync_target"] = "production"
        replay_kwargs["auto_activate"] = True

    try:
        result = deps["ingestion_runtime"].replay_reindex(**replay_kwargs)
    except Exception as exc:  # noqa: BLE001
        handler._send_json(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {"error": f"reindex_failed: {exc}"},
        )
        return True

    total = int(((result.get("index") or {}).get("documents_indexed") or 0))
    if path == "/api/admin/reindex":
        from .ingest import load_active_index_generation as _load_active_generation

        active_generation = (
            _load_active_generation(output_dir=deps["index_file_path"].parent) or {}
        )
        class_counts = dict(active_generation.get("knowledge_class_counts") or {})
        normative = int(class_counts.get("normative_base") or 0)
        interpretative = int(class_counts.get("interpretative_guidance") or 0)
        practica = int(class_counts.get("practica_erp") or 0)
        handler._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "mode": mode,
                "missing_source_policy": missing_source_policy,
                "documents": total,
                "normative": normative,
                "interpretative": interpretative,
                "practica": practica,
                "generation_id": active_generation.get("generation_id"),
                "generation_files": list(active_generation.get("files") or []),
                "source_integrity": result.get("source_integrity"),
                "replay": result.get("replay"),
                "index": {
                    **dict(result.get("index") or {}),
                    "normative": normative,
                    "interpretative": interpretative,
                    "practica": practica,
                    "generation_id": active_generation.get("generation_id"),
                    "generation_files": list(active_generation.get("files") or []),
                },
            },
        )
        return True

    handler._send_json(
        HTTPStatus.OK,
        {
            "ok": True,
            "mode": mode,
            "missing_source_policy": missing_source_policy,
            "documents": total,
            "source_integrity": result.get("source_integrity"),
            "replay": result.get("replay"),
            "index": result.get("index"),
        },
    )
    return True
