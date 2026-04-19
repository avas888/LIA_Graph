"""Platform/admin read surfaces extracted from ``ui_server.LiaUIHandler``.

HTTP surface handled here (all GET):

* ``/api/me``                              — current auth context
* ``/api/admin/usage``                     — usage summary
* ``/api/admin/public-usage``              — public-surface visitor buckets
* ``/api/admin/reviews``                   — tenant feedback list
* ``/api/admin/activity``                  — recent logins + activity stats
* ``/api/admin/ratings``                   — admin rating query with filters
* ``/api/admin/errors``                    — admin view of user error log
* ``/api/admin/eval/service-accounts``     — eval service accounts
* ``/api/admin/eval/stats``                — eval aggregate stats
* ``/api/admin/eval/logs``                 — eval per-turn logs
* ``/api/jobs/{job_id}``                   — single job read (runtime + corpus)

Optional imports (``login_audit``, ``eval_store``, ``service_account_auth``)
are wrapped in ``try/except ImportError`` so individual endpoints degrade to
empty-result responses if the supporting module is not present in this
deployment. This matches Lia_Graph's lineage split from Lia_contadores: we
preserve contract shape without hard-depending on modules that have not yet
been ported.

See ``docs/next/granularization_v1.md`` §Controller Surface Catalog.
"""

from __future__ import annotations

import json
import logging
import re
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from .platform_auth import PlatformAuthError


_JOBS_ROUTE_RE = re.compile(r"^/api/jobs/([^/]+)$")
_log = logging.getLogger(__name__)


def _read_user_errors(
    *,
    log_path: Path | None,
    tenant_id: str | None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Read user error entries from the JSONL log, most recent first."""
    if log_path is None or not Path(log_path).exists():
        return {"items": [], "total": 0}
    entries: list[dict[str, Any]] = []
    try:
        with open(log_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = record.get("payload") if isinstance(record, dict) else None
                if not isinstance(payload, dict):
                    continue
                if tenant_id and str(payload.get("tenant_id") or "").strip() != tenant_id:
                    continue
                entries.append({"ts_utc": record.get("ts_utc"), **payload})
    except OSError:
        _log.warning("Could not read user errors log at %s", log_path, exc_info=True)
        return {"items": [], "total": 0}
    entries.reverse()
    total = len(entries)
    return {"items": entries[offset: offset + limit], "total": total}


def handle_platform_get(
    handler: Any,
    path: str,
    parsed: Any,
    *,
    deps: dict[str, Any],
) -> bool:
    """Dispatch GET requests on /api/me, /api/admin/*, /api/jobs/{id}.

    ``deps`` keys: ``summarize_usage``, ``summarize_public_usage``, ``list_feedback``,
    ``list_feedback_for_admin``, ``load_job``, ``usage_events_path``,
    ``feedback_path``, ``jobs_runtime_path``, ``corpus_jobs_runtime_path``,
    ``user_errors_path``.
    """
    if path == "/api/me":
        return _handle_me_get(handler)
    if path == "/api/admin/usage":
        return _handle_admin_usage_get(handler, parsed, deps)
    if path == "/api/admin/public-usage":
        return _handle_admin_public_usage_get(handler, parsed, deps)
    if path == "/api/admin/reviews":
        return _handle_admin_reviews_get(handler, parsed, deps)
    if path == "/api/admin/activity":
        return _handle_admin_activity_get(handler, parsed)
    if path == "/api/admin/ratings":
        return _handle_admin_ratings_get(handler, parsed, deps)
    if path == "/api/admin/errors":
        return _handle_admin_errors_get(handler, parsed, deps)
    if path == "/api/admin/eval/service-accounts":
        return _handle_admin_eval_service_accounts_get(handler, parsed)
    if path == "/api/admin/eval/stats":
        return _handle_admin_eval_stats_get(handler, parsed)
    if path == "/api/admin/eval/logs":
        return _handle_admin_eval_logs_get(handler, parsed)
    job_match = _JOBS_ROUTE_RE.match(path)
    if job_match:
        return _handle_job_get(handler, job_match.group(1), deps)
    return False


def _handle_me_get(handler: Any) -> bool:
    try:
        auth_context = handler._resolve_auth_context(required=True)
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True
    handler._send_json(HTTPStatus.OK, {"ok": True, "me": auth_context.to_public_dict()})
    return True


def _handle_admin_usage_get(handler: Any, parsed: Any, deps: dict[str, Any]) -> bool:
    try:
        auth_context = handler._resolve_auth_context(required=True)
        query = parse_qs(parsed.query)
        tenant_scope = handler._admin_tenant_scope(
            auth_context,
            requested_tenant_id=str((query.get("tenant_id") or [""])[0]).strip() or None,
        )
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True
    query = parse_qs(parsed.query)
    user_id = str((query.get("user_id") or [""])[0]).strip() or None
    company_id = str((query.get("company_id") or [""])[0]).strip() or None
    group_by = str((query.get("group_by") or ["tenant_id"])[0]).strip() or "tenant_id"
    limit_raw = str((query.get("limit") or ["500"])[0]).strip() or "500"
    try:
        limit = max(1, min(int(limit_raw), 2000))
    except ValueError:
        limit = 500
    summary = deps["summarize_usage"](
        base_dir=deps["usage_events_path"],
        tenant_id=tenant_scope,
        user_id=user_id,
        company_id=company_id,
        group_by=group_by,
        limit=limit,
    )
    handler._send_json(HTTPStatus.OK, {"ok": True, "summary": summary})
    return True


def _handle_admin_public_usage_get(handler: Any, parsed: Any, deps: dict[str, Any]) -> bool:
    try:
        auth_context = handler._resolve_auth_context(required=True)
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True
    if auth_context.role not in {"tenant_admin", "platform_admin"}:
        handler._send_auth_error(
            PlatformAuthError(
                "Se requiere rol administrativo.",
                code="auth_role_forbidden",
                http_status=403,
            )
        )
        return True
    query = parse_qs(parsed.query)
    days_raw = str((query.get("days") or ["30"])[0]).strip() or "30"
    try:
        days = max(1, min(int(days_raw), 365))
    except ValueError:
        days = 30
    summarize_public_usage = deps.get("summarize_public_usage")
    rows: list[dict[str, Any]] = []
    if callable(summarize_public_usage):
        rows = summarize_public_usage(days=days)
    handler._send_json(HTTPStatus.OK, {"ok": True, "rows": rows})
    return True


def _handle_admin_reviews_get(handler: Any, parsed: Any, deps: dict[str, Any]) -> bool:
    try:
        auth_context = handler._resolve_auth_context(required=True)
        query = parse_qs(parsed.query)
        tenant_scope = handler._admin_tenant_scope(
            auth_context,
            requested_tenant_id=str((query.get("tenant_id") or [""])[0]).strip() or None,
        )
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True
    query = parse_qs(parsed.query)
    user_id = str((query.get("user_id") or [""])[0]).strip() or None
    company_id = str((query.get("company_id") or [""])[0]).strip() or None
    limit_raw = str((query.get("limit") or ["100"])[0]).strip() or "100"
    try:
        limit = max(1, min(int(limit_raw), 200))
    except ValueError:
        limit = 100
    records = deps["list_feedback"](
        base_dir=deps["feedback_path"],
        tenant_id=tenant_scope,
        user_id=user_id,
        company_id=company_id,
        limit=limit,
    )
    handler._send_json(HTTPStatus.OK, {"ok": True, "reviews": records})
    return True


def _handle_admin_activity_get(handler: Any, parsed: Any) -> bool:
    try:
        auth_context = handler._resolve_auth_context(required=True)
        query = parse_qs(parsed.query)
        tenant_scope = handler._admin_tenant_scope(
            auth_context,
            requested_tenant_id=str((query.get("tenant_id") or [""])[0]).strip() or None,
        )
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True
    query = parse_qs(parsed.query)
    limit_raw = str((query.get("limit") or ["100"])[0]).strip() or "100"
    try:
        limit = max(1, min(int(limit_raw), 500))
    except ValueError:
        limit = 100

    try:
        from .login_audit import query_recent_logins, query_user_activity_stats
    except ImportError:
        handler._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "activity": {
                    "recent_logins": [],
                    "total_logins": 0,
                    "unique_users": 0,
                },
            },
        )
        return True

    recent_logins = query_recent_logins(tenant_id=tenant_scope, limit=limit)

    user_ids = {str(r.get("user_id", "") or "").strip() for r in recent_logins if r.get("user_id")}
    display_map: dict[str, str] = {}
    if user_ids:
        try:
            from .supabase_client import get_supabase_client

            client = get_supabase_client()
            if client:
                users_res = (
                    client.table("users")
                    .select("user_id, display_name")
                    .in_("user_id", list(user_ids))
                    .execute()
                )
                for u in (users_res.data or []):
                    display_map[str(u.get("user_id", ""))] = str(u.get("display_name", "") or "")
        except Exception:
            pass

    enriched_logins = []
    for row in recent_logins:
        uid = str(row.get("user_id", "") or "").strip()
        enriched_logins.append(
            {
                "email": row.get("email", ""),
                "display_name": display_map.get(uid, ""),
                "status": row.get("status", ""),
                "ip_address": row.get("ip_address", ""),
                "created_at": row.get("created_at", ""),
                "failure_reason": row.get("failure_reason"),
            }
        )

    stats = query_user_activity_stats(tenant_id=tenant_scope)
    stats["recent_logins"] = enriched_logins

    handler._send_json(HTTPStatus.OK, {"ok": True, "activity": stats})
    return True


def _handle_admin_ratings_get(handler: Any, parsed: Any, deps: dict[str, Any]) -> bool:
    try:
        auth_context = handler._resolve_auth_context(required=True)
        query = parse_qs(parsed.query)
        tenant_scope = handler._admin_tenant_scope(
            auth_context,
            requested_tenant_id=str((query.get("tenant_id") or [""])[0]).strip() or None,
        )
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True
    query = parse_qs(parsed.query)
    user_id = str((query.get("user_id") or [""])[0]).strip() or None
    limit_raw = str((query.get("limit") or ["50"])[0]).strip() or "50"
    offset_raw = str((query.get("offset") or ["0"])[0]).strip() or "0"
    rating_min_raw = str((query.get("rating_min") or [""])[0]).strip()
    rating_max_raw = str((query.get("rating_max") or [""])[0]).strip()
    try:
        limit = max(1, min(int(limit_raw), 200))
    except ValueError:
        limit = 50
    try:
        offset = max(0, int(offset_raw))
    except ValueError:
        offset = 0
    rating_min: int | None = None
    rating_max: int | None = None
    if rating_min_raw:
        try:
            rating_min = max(1, min(int(rating_min_raw), 5))
        except ValueError:
            pass
    if rating_max_raw:
        try:
            rating_max = max(1, min(int(rating_max_raw), 5))
        except ValueError:
            pass
    since = str((query.get("since") or [""])[0]).strip() or None
    try:
        records = deps["list_feedback_for_admin"](
            base_dir=deps["feedback_path"],
            tenant_id=tenant_scope,
            user_id=user_id,
            rating_min=rating_min,
            rating_max=rating_max,
            limit=limit,
            offset=offset,
            since=since,
        )
    except Exception as exc:
        _log.error("list_feedback_for_admin failed: %s", exc, exc_info=True)
        handler._send_json(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {
                "ok": False,
                "error": f"Error al consultar calificaciones: {exc}",
                "ratings": [],
            },
        )
        return True
    handler._send_json(HTTPStatus.OK, {"ok": True, "ratings": records})
    return True


def _handle_admin_errors_get(handler: Any, parsed: Any, deps: dict[str, Any]) -> bool:
    try:
        auth_context = handler._resolve_auth_context(required=True)
        query = parse_qs(parsed.query)
        tenant_scope = handler._admin_tenant_scope(
            auth_context,
            requested_tenant_id=str((query.get("tenant_id") or [""])[0]).strip() or None,
        )
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True
    query = parse_qs(parsed.query)
    limit_raw = str((query.get("limit") or ["50"])[0]).strip() or "50"
    offset_raw = str((query.get("offset") or ["0"])[0]).strip() or "0"
    try:
        limit = max(1, min(int(limit_raw), 200))
    except ValueError:
        limit = 50
    try:
        offset = max(0, int(offset_raw))
    except ValueError:
        offset = 0
    errors = _read_user_errors(
        log_path=deps.get("user_errors_path"),
        tenant_id=tenant_scope,
        limit=limit,
        offset=offset,
    )
    handler._send_json(
        HTTPStatus.OK,
        {"ok": True, "errors": errors["items"], "total": errors["total"]},
    )
    return True


def _handle_admin_eval_service_accounts_get(handler: Any, parsed: Any) -> bool:
    try:
        auth_context = handler._resolve_auth_context(required=True)
        query = parse_qs(parsed.query)
        tenant_scope = handler._admin_tenant_scope(
            auth_context,
            requested_tenant_id=str((query.get("tenant_id") or [""])[0]).strip() or None,
        )
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True
    try:
        from .service_account_auth import list_service_accounts

        accounts = list_service_accounts(tenant_id=tenant_scope or auth_context.tenant_id)
    except ImportError:
        accounts = []
    handler._send_json(HTTPStatus.OK, {"ok": True, "service_accounts": accounts})
    return True


def _handle_admin_eval_stats_get(handler: Any, parsed: Any) -> bool:
    try:
        auth_context = handler._resolve_auth_context(required=True)
        query = parse_qs(parsed.query)
        tenant_scope = handler._admin_tenant_scope(
            auth_context,
            requested_tenant_id=str((query.get("tenant_id") or [""])[0]).strip() or None,
        )
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True
    _tenant = tenant_scope or auth_context.tenant_id
    try:
        from .eval_store import list_eval_runs, list_eval_turns
    except ImportError:
        handler._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "stats": {
                    "total_requests": 0,
                    "total_errors": 0,
                    "error_rate": 0,
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "total_tokens": 0,
                    "latency_p50_ms": 0,
                    "latency_p95_ms": 0,
                    "by_endpoint": [],
                },
            },
        )
        return True

    runs = list_eval_runs(tenant_id=_tenant)
    all_turns: list[dict[str, Any]] = []
    for r in runs:
        all_turns.extend(list_eval_turns(eval_run_id=r["eval_run_id"]))

    total_requests = len(all_turns)
    errors = [t for t in all_turns if t.get("status") == "error"]
    latencies = sorted([t["latency_ms"] for t in all_turns if t.get("latency_ms") is not None])
    total_input = sum(
        (t.get("response") or {}).get("token_usage", {}).get("turn", {}).get("input_tokens", 0)
        for t in all_turns
    )
    total_output = sum(
        (t.get("response") or {}).get("token_usage", {}).get("turn", {}).get("output_tokens", 0)
        for t in all_turns
    )
    endpoint_counts: dict[str, dict[str, int]] = {}
    for t in all_turns:
        ep = "/api/eval/ask"
        bucket = endpoint_counts.setdefault(ep, {"requests": 0, "errors": 0})
        bucket["requests"] += 1
        if t.get("status") == "error":
            bucket["errors"] += 1
    stats: dict[str, Any] = {
        "total_requests": total_requests,
        "total_errors": len(errors),
        "error_rate": round(len(errors) / max(total_requests, 1), 4),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_tokens": total_input + total_output,
        "latency_p50_ms": round(latencies[len(latencies) // 2], 1) if latencies else 0,
        "latency_p95_ms": (
            round(latencies[int(len(latencies) * 0.95)], 1)
            if len(latencies) >= 2
            else (round(latencies[-1], 1) if latencies else 0)
        ),
        "by_endpoint": [
            {"endpoint": ep, **counts} for ep, counts in endpoint_counts.items()
        ],
    }
    handler._send_json(HTTPStatus.OK, {"ok": True, "stats": stats})
    return True


def _handle_admin_eval_logs_get(handler: Any, parsed: Any) -> bool:
    try:
        auth_context = handler._resolve_auth_context(required=True)
        query = parse_qs(parsed.query)
        tenant_scope = handler._admin_tenant_scope(
            auth_context,
            requested_tenant_id=str((query.get("tenant_id") or [""])[0]).strip() or None,
        )
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True
    query = parse_qs(parsed.query)
    limit_raw = str((query.get("limit") or ["20"])[0]).strip() or "20"
    offset_raw = str((query.get("offset") or ["0"])[0]).strip() or "0"
    try:
        limit = max(1, min(int(limit_raw), 100))
    except ValueError:
        limit = 20
    try:
        offset = max(0, int(offset_raw))
    except ValueError:
        offset = 0
    _tenant = tenant_scope or auth_context.tenant_id
    try:
        from .eval_store import list_eval_runs, list_eval_turns
    except ImportError:
        handler._send_json(
            HTTPStatus.OK,
            {"ok": True, "logs": [], "total": 0, "limit": limit, "offset": offset},
        )
        return True

    runs = list_eval_runs(tenant_id=_tenant)
    all_turns: list[dict[str, Any]] = []
    for r in runs:
        all_turns.extend(list_eval_turns(eval_run_id=r["eval_run_id"]))
    all_turns.sort(key=lambda t: t.get("created_at", ""), reverse=True)
    total = len(all_turns)
    page = all_turns[offset: offset + limit]
    logs = []
    for t in page:
        resp = t.get("response") or {}
        logs.append(
            {
                "log_id": t.get("eval_turn_id", ""),
                "endpoint": "/api/eval/ask",
                "method": "POST",
                "status_code": 200 if t.get("status") == "completed" else 500,
                "latency_ms": t.get("latency_ms"),
                "input_tokens": resp.get("token_usage", {}).get("turn", {}).get("input_tokens", 0),
                "output_tokens": resp.get("token_usage", {}).get("turn", {}).get("output_tokens", 0),
                "created_at": t.get("created_at", ""),
                "service_account_id": "",
                "eval_run_id": t.get("eval_run_id", ""),
                "eval_turn_id": t.get("eval_turn_id", ""),
                "request_body": {
                    "message": t.get("message", ""),
                    "topic": t.get("topic", ""),
                    "pais": t.get("pais", ""),
                    "question_id": t.get("question_id", ""),
                },
                "response_summary": {
                    "answer_length_chars": len(str(resp.get("answer_markdown", ""))),
                    "citations_count": len(resp.get("citations", [])),
                    "confidence_score": (resp.get("confidence") or {}).get("score"),
                    "retrieval_top_score": (resp.get("diagnostics") or {}).get("retrieval", {}).get("top_score"),
                    "pipeline_total_ms": t.get("latency_ms"),
                },
                "error": t.get("error") or None,
            }
        )
    handler._send_json(
        HTTPStatus.OK,
        {"ok": True, "logs": logs, "total": total, "limit": limit, "offset": offset},
    )
    return True


def _handle_job_get(handler: Any, job_id: str, deps: dict[str, Any]) -> bool:
    try:
        auth_context = handler._resolve_auth_context(required=True)
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True
    load_job = deps["load_job"]
    job = load_job(job_id, base_dir=deps["jobs_runtime_path"])
    if job is None:
        job = load_job(job_id, base_dir=deps["corpus_jobs_runtime_path"])
    if job is None:
        handler._send_json(HTTPStatus.NOT_FOUND, {"error": "job_not_found"})
        return True
    if (
        auth_context.role != "platform_admin"
        and str(job.tenant_id or "").strip() != auth_context.tenant_id
    ):
        handler._send_json(HTTPStatus.NOT_FOUND, {"error": "job_not_found"})
        return True
    handler._send_json(HTTPStatus.OK, {"ok": True, "job": job.to_dict()})
    return True
