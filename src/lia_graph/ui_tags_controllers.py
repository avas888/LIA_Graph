"""Tag review admin surface — Lia_Graph (ingestionfix_v2 §4 Phase 7a).

Backend endpoints for the ``Tags`` admin tab. The frontend tab itself is
deferred (Phase 7b in ``docs/next/ingestionfix_v2.md``); these endpoints
are fully operable via curl / Postman today, and Phase 7b will wire them
into a proper Ops-shell tab.

Routes::

    GET  /api/tags/review?min_confidence=&reason=&topic=
                                              — list the review queue
    GET  /api/tags/review/{doc_id}            — detail for a single doc
    POST /api/tags/review/{doc_id}/report     — trigger LLM brief
    GET  /api/tags/review/{doc_id}/report/{report_id}
                                              — fetch brief
    POST /api/tags/review/{doc_id}/decision   — persist expert decision

All endpoints require admin role (tenant_admin or platform_admin).

Trace events::

    tags.review.list.served
    tags.review.detail.served
    tags.review.report.requested
    tags.review.report.served
    tags.review.decision.recorded
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from .instrumentation import emit_event
from .platform_auth import PlatformAuthError
from .tag_report_generator import generate_tag_report

_log = logging.getLogger(__name__)


_TAGS_REVIEW_PREFIX = "/api/tags/review"
_VALID_DECISIONS = frozenset(
    {"approve", "override", "promote_new_subtopic", "reject"}
)
_VALID_TRIGGER_REASONS = frozenset(
    {"low_confidence", "requires_review_flag", "new_subtopic_proposed", "manual"}
)
_DOC_ID_RE = re.compile(r"^[A-Za-z0-9_.\-:/]+$")


def _trace(event: str, payload: dict[str, Any]) -> None:
    emit_event(event, payload)
    _log.info("[%s] %s", event, payload)


def _require_admin(handler: Any) -> str:
    auth_context = handler._resolve_auth_context(required=True)
    if auth_context.role not in {"tenant_admin", "platform_admin"}:
        raise PlatformAuthError(
            "Se requiere rol administrativo.",
            code="auth_role_forbidden",
            http_status=403,
        )
    return (
        getattr(auth_context, "email", None)
        or getattr(auth_context, "user_id", None)
        or "admin"
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _respond_json(handler: Any, status: int, body: dict[str, Any]) -> None:
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    for key, value in handler._cors_headers().items():
        handler.send_header(key, value)
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def _parse_json_body(handler: Any) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or 0)
    if length <= 0:
        return {}
    raw = handler.rfile.read(length).decode("utf-8", errors="replace")
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid_json: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("json_body_must_be_object")
    return data


def _valid_doc_id(candidate: str) -> bool:
    return bool(candidate) and bool(_DOC_ID_RE.match(candidate))


# ---------------------------------------------------------------------------
# Supabase adapter — thin wrapper; tests inject a fake client.
# ---------------------------------------------------------------------------


def _supabase_client_from_deps(deps: dict[str, Any]) -> Any:
    """Return a supabase-py client. Deps lets tests inject a fake."""
    client = deps.get("supabase_client")
    if client is not None:
        return client
    from .supabase_client import create_supabase_client_for_target

    target = deps.get("supabase_target") or "production"
    return create_supabase_client_for_target(target)


def _list_review_queue(
    client: Any,
    *,
    min_confidence: float | None,
    trigger_reason: str | None,
    topic: str | None,
) -> list[dict[str, Any]]:
    """Return pending-review rows, joined with snapshot + documents info."""
    query = client.table("document_tag_reviews").select(
        "review_id,doc_id,trigger_reason,snapshot_topic,snapshot_subtopic,"
        "snapshot_confidence,report_id,decision_action,created_at"
    ).is_("decided_at", "null")
    if trigger_reason and trigger_reason in _VALID_TRIGGER_REASONS:
        query = query.eq("trigger_reason", trigger_reason)
    if topic:
        query = query.eq("snapshot_topic", topic)
    response = query.order("created_at", desc=True).limit(500).execute()
    rows = getattr(response, "data", None) or []
    if min_confidence is not None:
        rows = [
            row for row in rows
            if (row.get("snapshot_confidence") or 0.0) <= min_confidence
        ]
    return rows


def _fetch_doc_row(client: Any, doc_id: str) -> dict[str, Any] | None:
    response = (
        client.table("documents")
        .select(
            "doc_id,relative_path,first_heading,topic,tema,subtema,"
            "subtopic_confidence,requires_subtopic_review,knowledge_class,"
            "corpus,authority,source_type"
        )
        .eq("doc_id", doc_id)
        .limit(1)
        .execute()
    )
    rows = getattr(response, "data", None) or []
    return rows[0] if rows else None


def _fetch_review_row(client: Any, doc_id: str, review_id: str | None = None) -> dict[str, Any] | None:
    query = client.table("document_tag_reviews").select("*").eq("doc_id", doc_id)
    if review_id is not None:
        query = query.eq("review_id", review_id)
    response = query.order("created_at", desc=True).limit(1).execute()
    rows = getattr(response, "data", None) or []
    return rows[0] if rows else None


def _fetch_similar_docs_by_tag(
    client: Any, candidate_tags: list[str], *, doc_id: str
) -> dict[str, list[dict[str, Any]]]:
    """For each candidate tag, return up to 3 similar docs sharing that topic.

    Phase 7a uses a simple ``topic`` filter (not vector similarity) so the
    endpoint works even when embeddings haven't finished backfilling. Phase
    7b / future iteration can swap in the ``hybrid_search`` RPC.
    """
    buckets: dict[str, list[dict[str, Any]]] = {}
    for tag in candidate_tags:
        if not tag:
            continue
        try:
            response = (
                client.table("documents")
                .select("doc_id,relative_path,first_heading,topic,subtema")
                .eq("topic", tag)
                .neq("doc_id", doc_id)
                .limit(3)
                .execute()
            )
        except Exception:  # noqa: BLE001 — neighborhood is optional
            buckets[tag] = []
            continue
        buckets[tag] = getattr(response, "data", None) or []
    return buckets


# ---------------------------------------------------------------------------
# GET /api/tags/review
# ---------------------------------------------------------------------------


def _handle_list_queue(handler: Any, parsed: Any, deps: dict[str, Any]) -> None:
    params = parse_qs(parsed.query or "")

    def _first(key: str) -> str | None:
        values = params.get(key)
        if not values:
            return None
        value = values[0].strip()
        return value or None

    min_confidence_raw = _first("min_confidence")
    min_confidence: float | None = None
    if min_confidence_raw is not None:
        try:
            min_confidence = float(min_confidence_raw)
        except ValueError:
            _respond_json(
                handler, HTTPStatus.BAD_REQUEST,
                {"error": "min_confidence must be a float"},
            )
            return

    trigger_reason = _first("reason")
    topic = _first("topic")

    client = _supabase_client_from_deps(deps)
    rows = _list_review_queue(
        client,
        min_confidence=min_confidence,
        trigger_reason=trigger_reason,
        topic=topic,
    )
    _trace(
        "tags.review.list.served",
        {
            "count": len(rows),
            "min_confidence": min_confidence,
            "reason": trigger_reason,
            "topic": topic,
        },
    )
    _respond_json(handler, HTTPStatus.OK, {"reviews": rows, "count": len(rows)})


# ---------------------------------------------------------------------------
# GET /api/tags/review/{doc_id}
# ---------------------------------------------------------------------------


def _handle_detail(handler: Any, doc_id: str, deps: dict[str, Any]) -> None:
    if not _valid_doc_id(doc_id):
        _respond_json(handler, HTTPStatus.BAD_REQUEST, {"error": "invalid doc_id"})
        return
    client = _supabase_client_from_deps(deps)
    doc_row = _fetch_doc_row(client, doc_id)
    if doc_row is None:
        _respond_json(handler, HTTPStatus.NOT_FOUND, {"error": "doc_id_not_found"})
        return

    review_row = _fetch_review_row(client, doc_id)
    # Candidate tags: the doc's current topic + the review snapshot topic
    # + the top-3 classifier alternatives (if the review row carries them).
    candidate_tags = [doc_row.get("topic") or "", (review_row or {}).get("snapshot_topic") or ""]
    candidate_tags = [t for t in candidate_tags if t]
    neighbors = _fetch_similar_docs_by_tag(
        client, candidate_tags, doc_id=doc_id
    )

    _trace("tags.review.detail.served", {"doc_id": doc_id})
    _respond_json(
        handler,
        HTTPStatus.OK,
        {
            "doc": doc_row,
            "review": review_row,
            "neighbors_by_tag": neighbors,
        },
    )


# ---------------------------------------------------------------------------
# POST /api/tags/review/{doc_id}/report
# ---------------------------------------------------------------------------


def _handle_report_post(
    handler: Any, doc_id: str, deps: dict[str, Any]
) -> None:
    if not _valid_doc_id(doc_id):
        _respond_json(handler, HTTPStatus.BAD_REQUEST, {"error": "invalid doc_id"})
        return
    client = _supabase_client_from_deps(deps)
    doc_row = _fetch_doc_row(client, doc_id)
    if doc_row is None:
        _respond_json(handler, HTTPStatus.NOT_FOUND, {"error": "doc_id_not_found"})
        return
    review_row = _fetch_review_row(client, doc_id)
    if review_row is None:
        _respond_json(
            handler, HTTPStatus.NOT_FOUND,
            {"error": "no_open_review_for_doc"},
        )
        return

    # Fetch the full markdown for the brief — documents table stores a
    # preview in ``first_heading`` but the full text lives in chunks.
    # Phase 7a pulls from the first chunk_text when available.
    try:
        chunk_response = (
            client.table("document_chunks")
            .select("chunk_text")
            .eq("doc_id", doc_id)
            .limit(1)
            .execute()
        )
        chunk_rows = getattr(chunk_response, "data", None) or []
        markdown_preview = (chunk_rows[0].get("chunk_text") or "") if chunk_rows else ""
    except Exception:
        markdown_preview = ""

    enriched_doc: dict[str, Any] = dict(doc_row)
    enriched_doc["markdown"] = markdown_preview
    enriched_doc["subtopic_confidence"] = review_row.get("snapshot_confidence")

    alternatives = (
        deps.get("classifier_alternatives_for")(doc_id)
        if callable(deps.get("classifier_alternatives_for"))
        else []
    )
    candidate_tags = [enriched_doc.get("topic") or "", review_row.get("snapshot_topic") or ""]
    candidate_tags = list({t for t in candidate_tags if t})
    neighbors = _fetch_similar_docs_by_tag(
        client, candidate_tags, doc_id=doc_id
    )

    adapter = deps.get("llm_adapter")
    if adapter is None and deps.get("llm_adapter_factory") is not None:
        try:
            adapter, _meta = deps["llm_adapter_factory"]()
        except Exception:  # noqa: BLE001 — LLM polish is optional
            adapter = None

    report_id = f"rpt_{uuid.uuid4().hex[:12]}"
    report = generate_tag_report(
        enriched_doc,
        report_id=report_id,
        classifier_alternatives=alternatives,
        similar_docs_by_tag=neighbors,
        llm_adapter=adapter,
    )

    now = _utc_now_iso()
    client.table("document_tag_reviews").update(
        {
            "report_id": report.report_id,
            "report_markdown": report.markdown,
            "report_generated_at": now,
            "updated_at": now,
        }
    ).eq("review_id", review_row["review_id"]).execute()

    _trace(
        "tags.review.report.requested",
        {
            "doc_id": doc_id,
            "report_id": report.report_id,
            "llm_polished": report.llm_polished,
            "skip_reason": report.skip_reason,
        },
    )
    _respond_json(
        handler,
        HTTPStatus.OK,
        {
            "report_id": report.report_id,
            "markdown": report.markdown,
            "llm_polished": report.llm_polished,
            "skip_reason": report.skip_reason,
        },
    )


# ---------------------------------------------------------------------------
# GET /api/tags/review/{doc_id}/report/{report_id}
# ---------------------------------------------------------------------------


def _handle_report_get(
    handler: Any, doc_id: str, report_id: str, deps: dict[str, Any]
) -> None:
    if not _valid_doc_id(doc_id):
        _respond_json(handler, HTTPStatus.BAD_REQUEST, {"error": "invalid doc_id"})
        return
    client = _supabase_client_from_deps(deps)
    response = (
        client.table("document_tag_reviews")
        .select("review_id,report_id,report_markdown,report_generated_at")
        .eq("doc_id", doc_id)
        .eq("report_id", report_id)
        .limit(1)
        .execute()
    )
    rows = getattr(response, "data", None) or []
    if not rows:
        _respond_json(
            handler, HTTPStatus.NOT_FOUND,
            {"error": "report_not_found"},
        )
        return
    _trace("tags.review.report.served", {"doc_id": doc_id, "report_id": report_id})
    _respond_json(handler, HTTPStatus.OK, rows[0])


# ---------------------------------------------------------------------------
# POST /api/tags/review/{doc_id}/decision
# ---------------------------------------------------------------------------


def _apply_decision_to_documents(
    client: Any, *, doc_id: str, action: str, payload: dict[str, Any], decided_by: str
) -> None:
    """Mirror the expert decision onto the `documents` row when applicable."""
    now = _utc_now_iso()
    if action in ("approve", "override"):
        updates: dict[str, Any] = {
            "requires_subtopic_review": False,
            "updated_at": now,
        }
        new_topic = (payload.get("new_topic") or "").strip() or None
        new_subtopic = (payload.get("new_subtopic") or "").strip() or None
        if action == "override":
            if new_topic:
                updates["topic"] = new_topic
                updates["tema"] = new_topic
            if new_subtopic:
                updates["subtema"] = new_subtopic
        client.table("documents").update(updates).eq("doc_id", doc_id).execute()
    elif action == "reject":
        client.table("documents").update(
            {"requires_subtopic_review": False, "updated_at": now}
        ).eq("doc_id", doc_id).execute()
    # ``promote_new_subtopic`` is handled by the Phase-8 taxonomy-sync
    # pipeline; the decision payload is stored verbatim so the miner
    # can pick it up. No direct documents-row mutation here.


def _handle_decision_post(
    handler: Any, doc_id: str, decided_by: str, deps: dict[str, Any]
) -> None:
    if not _valid_doc_id(doc_id):
        _respond_json(handler, HTTPStatus.BAD_REQUEST, {"error": "invalid doc_id"})
        return
    try:
        body = _parse_json_body(handler)
    except ValueError as exc:
        _respond_json(handler, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        return

    action = str(body.get("action") or "").strip()
    if action not in _VALID_DECISIONS:
        _respond_json(
            handler, HTTPStatus.BAD_REQUEST,
            {"error": f"action must be one of {sorted(_VALID_DECISIONS)}"},
        )
        return

    client = _supabase_client_from_deps(deps)
    review_row = _fetch_review_row(client, doc_id)
    if review_row is None:
        _respond_json(
            handler, HTTPStatus.NOT_FOUND,
            {"error": "no_open_review_for_doc"},
        )
        return

    now = _utc_now_iso()
    client.table("document_tag_reviews").update(
        {
            "decision_action": action,
            "decision_payload": body,
            "decided_by": decided_by,
            "decided_at": now,
            "updated_at": now,
        }
    ).eq("review_id", review_row["review_id"]).execute()

    _apply_decision_to_documents(
        client,
        doc_id=doc_id,
        action=action,
        payload=body,
        decided_by=decided_by,
    )

    _trace(
        "tags.review.decision.recorded",
        {
            "doc_id": doc_id,
            "review_id": review_row["review_id"],
            "action": action,
            "decided_by": decided_by,
        },
    )
    _respond_json(handler, HTTPStatus.OK, {"status": "ok", "action": action})


# ---------------------------------------------------------------------------
# Public dispatchers
# ---------------------------------------------------------------------------

_REVIEW_DETAIL_RE = re.compile(r"^/api/tags/review/([^/]+)$")
_REVIEW_REPORT_POST_RE = re.compile(r"^/api/tags/review/([^/]+)/report$")
_REVIEW_REPORT_GET_RE = re.compile(r"^/api/tags/review/([^/]+)/report/([^/]+)$")
_REVIEW_DECISION_RE = re.compile(r"^/api/tags/review/([^/]+)/decision$")


def handle_tags_get(
    handler: Any,
    path: str,
    parsed: Any,
    *,
    deps: dict[str, Any],
) -> bool:
    if not path.startswith(_TAGS_REVIEW_PREFIX):
        return False
    try:
        _require_admin(handler)
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True

    if path == _TAGS_REVIEW_PREFIX:
        _handle_list_queue(handler, parsed, deps)
        return True

    report_get_match = _REVIEW_REPORT_GET_RE.match(path)
    if report_get_match:
        doc_id, report_id = report_get_match.groups()
        _handle_report_get(handler, doc_id, report_id, deps)
        return True

    detail_match = _REVIEW_DETAIL_RE.match(path)
    if detail_match:
        _handle_detail(handler, detail_match.group(1), deps)
        return True

    return False


def handle_tags_post(
    handler: Any,
    path: str,
    *,
    deps: dict[str, Any],
) -> bool:
    if not path.startswith(_TAGS_REVIEW_PREFIX):
        return False
    try:
        decided_by = _require_admin(handler)
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True

    report_match = _REVIEW_REPORT_POST_RE.match(path)
    if report_match:
        _handle_report_post(handler, report_match.group(1), deps)
        return True

    decision_match = _REVIEW_DECISION_RE.match(path)
    if decision_match:
        _handle_decision_post(handler, decision_match.group(1), decided_by, deps)
        return True

    return False
