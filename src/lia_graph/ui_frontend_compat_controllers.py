"""Frontend-compat HTTP handlers extracted from ``ui_server.LiaUIHandler``.

These endpoints are legacy shims the frontend still calls by fixed path. The
real runtime lives elsewhere (LLM status is reported by the chat controller,
feedback is persisted via ``conversation_store``). We keep them here so that
``ui_server.py`` is not the hidden home of unrelated surfaces.

Conventions mirror ``ui_route_controllers.handle_form_guides_get``:

* ``handler`` is the live ``BaseHTTPRequestHandler`` subclass — we call
  ``handler._send_json`` etc. as methods.
* ``deps`` carries every stateful or monkeypatch-sensitive collaborator so
  tests that ``monkeypatch.setattr(ui_server, "FEEDBACK_PATH", ...)`` continue
  to work.
"""

from __future__ import annotations

import re
from http import HTTPStatus
from typing import Any
from urllib.parse import parse_qs


_UI_MILESTONE_EVENT_TYPES: dict[str, str] = {
    "main_chat_displayed": "chat_run.ui.main_chat_displayed",
    "response_bubble_highlighted": "chat_run.ui.response_bubble_highlighted",
    "normative_displayed": "chat_run.ui.normative_displayed",
    "expert_panel_displayed": "chat_run.ui.expert_panel_displayed",
}


def handle_chat_frontend_compat_get(
    handler: Any,
    path: str,
    parsed: Any,
    *,
    deps: dict[str, Any],
) -> bool:
    if path == "/api/llm/status":
        handler._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "llm_runtime": {
                    "selected_provider": None,
                    "selected_type": None,
                    "selected_transport": None,
                    "adapter_class": None,
                    "model": None,
                    "runtime_config_path": None,
                    "attempts": [],
                },
            },
        )
        return True

    if path == "/api/feedback":
        load_feedback = deps["load_feedback"]
        feedback_path = deps["feedback_path"]
        trace_id = str(parse_qs(parsed.query or "").get("trace_id", [""])[0] or "").strip()
        feedback_record = (
            load_feedback(trace_id, base_dir=feedback_path) if trace_id else None
        )
        payload = {
            "ok": True,
            "feedback": (
                {
                    "trace_id": feedback_record.trace_id,
                    "rating": feedback_record.rating,
                    "vote": feedback_record.vote,
                    "comment": feedback_record.comment,
                }
                if feedback_record is not None
                else None
            ),
        }
        handler._send_json(HTTPStatus.OK, payload)
        return True

    return False


def handle_chat_frontend_compat_post(
    handler: Any,
    path: str,
    *,
    deps: dict[str, Any],
) -> bool:
    milestone_route_re = deps["chat_run_milestones_route_re"]
    milestone_match = milestone_route_re.match(path)
    if milestone_match:
        payload = handler._read_json_payload(object_error="Se requiere un objeto JSON.")
        if payload is None:
            return True
        chat_run_id = str(milestone_match.group(1) or "").strip()
        milestone = str(payload.get("milestone") or "").strip()
        if not chat_run_id or not milestone:
            handler._send_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "error": "chat_run_id y milestone son obligatorios."},
            )
            return True

        elapsed_raw = payload.get("elapsed_ms")
        elapsed_ms = None
        if isinstance(elapsed_raw, (int, float)):
            elapsed_ms = round(float(elapsed_raw), 2)
        details = payload.get("details")
        event_payload = {
            "milestone": milestone,
            "elapsed_ms": elapsed_ms,
            "source": str(payload.get("source") or "").strip() or None,
            "status": str(payload.get("status") or "").strip() or "ok",
            "details": dict(details) if isinstance(details, dict) else {},
        }
        event_type = _UI_MILESTONE_EVENT_TYPES.get(
            milestone,
            f"chat_run.ui.{re.sub(r'[^a-z0-9_]+', '_', milestone.lower()).strip('_') or 'unknown'}",
        )
        record_chat_run_event_once = deps["record_chat_run_event_once"]
        recorded = record_chat_run_event_once(
            chat_run_id,
            event_type=event_type,
            payload=event_payload,
            base_dir=deps["chat_runs_path"],
        )
        handler._send_json(
            HTTPStatus.OK,
            {"ok": True, "chat_run_id": chat_run_id, "recorded": bool(recorded)},
        )
        return True

    if path == "/api/feedback":
        payload = handler._read_json_payload(object_error="Se requiere un objeto JSON.")
        if payload is None:
            return True
        trace_id = str(payload.get("trace_id") or "").strip()
        rating = handler._resolve_feedback_rating(payload)
        if not trace_id or rating is None:
            handler._send_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "error": "trace_id y rating valido son obligatorios."},
            )
            return True

        auth_context = handler._resolve_auth_context(required=False, allow_public=True)
        docs_used = payload.get("docs_used")
        layer_contributions = payload.get("layer_contributions")
        feedback_record_cls = deps["feedback_record_cls"]
        record = feedback_record_cls(
            trace_id=trace_id,
            session_id=str(payload.get("session_id") or "").strip() or None,
            rating=rating,
            tenant_id=getattr(auth_context, "tenant_id", "") or "",
            user_id=getattr(auth_context, "user_id", "") or "",
            company_id=getattr(auth_context, "company_id", "") or "",
            integration_id=getattr(auth_context, "integration_id", "") or "",
            tags=[
                str(tag).strip()
                for tag in (payload.get("tags") or [])
                if str(tag).strip()
            ],
            comment=str(payload.get("comment") or "").strip(),
            vote=str(payload.get("vote") or payload.get("thumb") or "").strip().lower(),
            source="api",
            created_by=getattr(auth_context, "user_id", "") or "",
            docs_used=[
                str(item).strip()
                for item in (docs_used or [])
                if str(item).strip()
            ]
            if isinstance(docs_used, list)
            else [],
            layer_contributions=(
                {str(key): int(value) for key, value in layer_contributions.items()}
                if isinstance(layer_contributions, dict)
                else {}
            ),
            pain_detected=str(payload.get("pain_detected") or "").strip(),
            task_detected=str(payload.get("task_detected") or "").strip(),
            question_text=str(payload.get("question_text") or "").strip(),
            answer_text=str(payload.get("answer_text") or "").strip(),
        )
        save_feedback = deps["save_feedback"]
        save_feedback(record, base_dir=deps["feedback_path"])
        handler._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "feedback": {
                    "trace_id": record.trace_id,
                    "rating": record.rating,
                    "vote": record.vote,
                    "comment": record.comment,
                },
            },
        )
        return True

    if path == "/api/feedback/comment":
        payload = handler._read_json_payload(object_error="Se requiere un objeto JSON.")
        if payload is None:
            return True
        trace_id = str(payload.get("trace_id") or "").strip()
        comment = str(payload.get("comment") or "").strip()
        if not trace_id or not comment:
            handler._send_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "error": "trace_id y comment son obligatorios."},
            )
            return True
        auth_context = handler._resolve_auth_context(required=False, allow_public=True)
        update_feedback_comment = deps["update_feedback_comment"]
        updated = update_feedback_comment(
            trace_id,
            comment,
            tenant_id=getattr(auth_context, "tenant_id", "") or deps["public_tenant_id"],
            base_dir=deps["feedback_path"],
        )
        handler._send_json(HTTPStatus.OK, {"ok": bool(updated)})
        return True

    if path == "/api/normative-support":
        payload = handler._read_json_payload(object_error="Se requiere un objeto JSON.")
        if payload is None:
            return True
        handler._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "trace_id": str(payload.get("trace_id") or "").strip() or None,
                "normative_citations": [],
            },
        )
        return True

    return False
