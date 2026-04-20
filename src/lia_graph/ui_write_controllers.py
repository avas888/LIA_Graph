"""State-mutating POST surfaces for platform, form-guides, chat runs, terms,
contributions, corpus ops, embedding ops, reindex, rollback, promote.

This module is the designated home for write endpoints that do not belong
to a narrower domain controller (auth → ``ui_route_controllers`` /
``ui_user_management_controllers``, reads → domain-specific
``ui_*_controllers``). The ``handle_*_post`` functions below are wired as
a group in ``do_POST`` via ``_write_controller_deps()`` on the handler.

The ingestion POST surface (``/api/ingestion/*`` + ``/api/corpora``) was
extracted during granularize-v2 to `ui_ingestion_write_controllers.py`
because that single handler was 849 LOC — half of this module. It is
re-imported below so ``from .ui_write_controllers import handle_ingestion_post``
keeps working for `ui_server.py`'s eager import block.

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

import json
import logging
from http import HTTPStatus
from pathlib import Path
from typing import Any

from .ui_ingestion_write_controllers import (  # noqa: F401  — re-exported
    handle_ingestion_post,
)


_log = logging.getLogger(__name__)


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
