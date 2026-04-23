"""Admin-scope HTTP controllers for the additive-corpus-v1 delta path.

Phase 8 of ``docs/next/additive_corpusv1.md``. Six endpoints under
``/api/ingest/additive/``:

* ``POST /preview`` — synchronous delta plan (no writes). Returns per-bucket
  counts + sample-doc chips.
* ``POST /apply`` — spawns the background worker inside a
  ``held_job_lock``; returns ``{job_id, delta_id, status_url, events_url,
  cancel_url}`` with HTTP 202.
* ``GET /events?job_id=…`` — SSE stream of stage transitions.
* ``GET /status?job_id=…`` — polling fallback (single-snapshot JSON).
* ``POST /cancel?job_id=…`` — flips ``cancel_requested=true`` on the job row.
* ``GET /live?target=production`` — returns the non-terminal job row for a
  target so the UI can reattach on mount.

Every endpoint gates on ``_require_admin`` (same helper used by
``ui_ingest_run_controllers``) and emits the ``ingest.delta.ui.*`` event
namespace per §13 of the plan.
"""

from __future__ import annotations

import json
import time
from http import HTTPStatus
from typing import Any
from urllib.parse import parse_qs

from .instrumentation import emit_event
from .ingestion import delta_job_store
from .ingestion.delta_lock import DeltaLockBusy, acquire_job_lock
from .ingestion.delta_planner import summarize_delta
from .ingestion.delta_runtime import materialize_delta
from .platform_auth import PlatformAuthError


API_PREFIX = "/api/ingest/additive/"


def _require_admin(handler: Any) -> None:
    auth_context = handler._resolve_auth_context(required=True)
    if auth_context.role not in {"tenant_admin", "platform_admin"}:
        raise PlatformAuthError(
            "Se requiere rol administrativo.",
            code="auth_role_forbidden",
            http_status=403,
        )


def _actor_id(handler: Any) -> str:
    try:
        return str(getattr(handler._resolve_auth_context(required=False), "user_id", "") or "anonymous")
    except Exception:  # noqa: BLE001
        return "anonymous"


def _read_json_body(handler: Any) -> dict[str, Any]:
    try:
        raw_len = int(handler.headers.get("Content-Length", "0") or "0")
    except (TypeError, ValueError):
        raw_len = 0
    if raw_len <= 0:
        return {}
    raw = handler.rfile.read(raw_len)
    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError:
        return {}
    if not decoded.strip():
        return {}
    try:
        payload = json.loads(decoded)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _emit_request(endpoint: str, handler: Any, **extra: Any) -> None:
    emit_event(
        "ingest.delta.ui.request",
        {
            "endpoint": endpoint,
            "actor_id": _actor_id(handler),
            **extra,
        },
    )


def _emit_response(endpoint: str, status: int, started: float, **extra: Any) -> None:
    emit_event(
        "ingest.delta.ui.response",
        {
            "endpoint": endpoint,
            "http_status": int(status),
            "elapsed_ms": int((time.monotonic() - started) * 1000),
            **extra,
        },
    )


# ---------------------------------------------------------------------------
# Per-endpoint handlers
# ---------------------------------------------------------------------------


def _handle_preview(handler: Any, deps: dict[str, Any]) -> bool:
    body = _read_json_body(handler)
    target = str(body.get("target") or "production").strip() or "production"
    force_full_classify = bool(body.get("force_full_classify", False))
    _emit_request(
        "preview", handler, target=target, force_full_classify=force_full_classify
    )
    started = time.monotonic()

    try:
        report = materialize_delta(
            corpus_dir=deps["corpus_dir"],
            artifacts_dir=deps["artifacts_dir"],
            pattern=deps.get("pattern", "**/*.md"),
            supabase_target=target,
            generation_id=deps.get("generation_id", "gen_active_rolling"),
            dry_run=True,
            execute_load=False,
            supabase_client=deps.get("supabase_client"),
            graph_client=deps.get("graph_client"),
            skip_llm=bool(deps.get("skip_llm", False)),
            rate_limit_rpm=int(deps.get("rate_limit_rpm", 60)),
            force_full_classify=force_full_classify,
        )
    except Exception as exc:  # noqa: BLE001
        _emit_response("preview", 500, started, error=str(exc))
        handler._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})
        return True

    payload = {
        "ok": True,
        "target": target,
        "delta_id": report.delta_id,
        "baseline_generation_id": report.baseline_generation_id,
        "summary": report.delta_summary,
        "sample_chips": _sample_chips_from_report(report),
    }
    _emit_response("preview", 200, started, delta_id=report.delta_id)
    handler._send_json(HTTPStatus.OK, payload)
    return True


def _sample_chips_from_report(report: Any) -> dict[str, list[str]]:
    """Unused in Phase 8 v1 — Phase 9 will populate sample chips once the
    preview path surfaces the per-bucket doc list. Reserved key on the
    response so the UI contract is stable today.
    """
    return {"added": [], "modified": [], "removed": []}


def _handle_apply(handler: Any, deps: dict[str, Any]) -> bool:
    body = _read_json_body(handler)
    target = str(body.get("target") or "production").strip() or "production"
    delta_id = body.get("delta_id") or None
    _emit_request("apply", handler, target=target)
    started = time.monotonic()

    supabase_client = deps.get("supabase_client")
    if supabase_client is None:
        from .supabase_client import create_supabase_client_for_target

        supabase_client = create_supabase_client_for_target(target)

    try:
        lock = acquire_job_lock(
            supabase_client,
            target=target,
            created_by=_actor_id(handler),
            delta_id=str(delta_id) if delta_id else None,
        )
    except DeltaLockBusy as busy:
        _emit_response("apply", 409, started, blocking_job_id=busy.blocking_job_id)
        handler._send_json(
            HTTPStatus.CONFLICT,
            {
                "ok": False,
                "error": "delta_lock_busy",
                "blocking_job_id": busy.blocking_job_id,
                "target": target,
            },
        )
        return True
    except Exception as exc:  # noqa: BLE001
        _emit_response("apply", 500, started, error=str(exc))
        handler._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})
        return True

    # Spawn the worker via the submit callable supplied by the host.
    worker_submitter = deps.get("submit_worker")
    if worker_submitter is None:
        # Without a worker, refuse politely instead of running the apply
        # synchronously — the HTTP response must be fast (202) per the plan.
        lock.finalize(
            stage="failed",
            error_class="worker_unavailable",
            error_message="background_jobs.submit not wired into deps",
        )
        _emit_response("apply", 503, started, reason="worker_unavailable")
        handler._send_json(
            HTTPStatus.SERVICE_UNAVAILABLE,
            {
                "ok": False,
                "error": "worker_unavailable",
                "job_id": lock.job_id,
            },
        )
        return True
    try:
        worker_submitter(job_id=lock.job_id, target=target, deps=deps)
    except Exception as exc:  # noqa: BLE001
        lock.finalize(
            stage="failed",
            error_class=exc.__class__.__name__,
            error_message=str(exc),
        )
        _emit_response("apply", 500, started, error=str(exc))
        handler._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})
        return True

    payload = {
        "ok": True,
        "job_id": lock.job_id,
        "delta_id": lock.delta_id,
        "status_url": f"{API_PREFIX}status?job_id={lock.job_id}",
        "events_url": f"{API_PREFIX}events?job_id={lock.job_id}",
        "cancel_url": f"{API_PREFIX}cancel?job_id={lock.job_id}",
    }
    _emit_response("apply", 202, started, job_id=lock.job_id)
    handler._send_json(HTTPStatus.ACCEPTED, payload)
    return True


def _handle_status(handler: Any, parsed: Any, deps: dict[str, Any]) -> bool:
    query = parse_qs(parsed.query)
    job_id = (query.get("job_id") or [""])[0]
    _emit_request("status", handler, job_id=job_id)
    started = time.monotonic()
    if not job_id:
        _emit_response("status", 400, started, reason="missing_job_id")
        handler._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "missing_job_id"})
        return True
    supabase_client = deps.get("supabase_client") or _default_supabase_client()
    try:
        row = delta_job_store.get_job(supabase_client, job_id=job_id)
    except LookupError:
        _emit_response("status", 404, started, job_id=job_id)
        handler._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "job_not_found"})
        return True
    _emit_response("status", 200, started, job_id=job_id, stage=row.stage)
    handler._send_json(HTTPStatus.OK, {"ok": True, "job": _row_to_dict(row)})
    return True


def _handle_cancel(handler: Any, parsed: Any, deps: dict[str, Any]) -> bool:
    query = parse_qs(parsed.query)
    job_id = (query.get("job_id") or [""])[0]
    _emit_request("cancel", handler, job_id=job_id)
    started = time.monotonic()
    if not job_id:
        _emit_response("cancel", 400, started, reason="missing_job_id")
        handler._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "missing_job_id"})
        return True
    supabase_client = deps.get("supabase_client") or _default_supabase_client()
    try:
        row = delta_job_store.get_job(supabase_client, job_id=job_id)
    except LookupError:
        _emit_response("cancel", 404, started, job_id=job_id)
        handler._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "job_not_found"})
        return True
    if row.is_terminal():
        _emit_response("cancel", 409, started, job_id=job_id, stage=row.stage)
        handler._send_json(
            HTTPStatus.CONFLICT,
            {"ok": False, "error": "job_already_terminal", "stage": row.stage},
        )
        return True
    row = delta_job_store.request_cancel(supabase_client, job_id=job_id)
    emit_event(
        "ingest.delta.ui.cancel_requested",
        {"job_id": job_id, "actor_id": _actor_id(handler)},
    )
    _emit_response("cancel", 200, started, job_id=job_id)
    handler._send_json(HTTPStatus.OK, {"ok": True, "job": _row_to_dict(row)})
    return True


def _handle_live(handler: Any, parsed: Any, deps: dict[str, Any]) -> bool:
    query = parse_qs(parsed.query)
    target = (query.get("target") or ["production"])[0]
    _emit_request("live", handler, target=target)
    started = time.monotonic()
    supabase_client = deps.get("supabase_client") or _default_supabase_client()
    try:
        live = delta_job_store.list_live_jobs_by_target(
            supabase_client, lock_target=target
        )
    except Exception as exc:  # noqa: BLE001
        _emit_response("live", 500, started, error=str(exc))
        handler._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})
        return True
    first = live[0] if live else None
    payload = {
        "ok": True,
        "target": target,
        "job_id": first.job_id if first else None,
        "job": _row_to_dict(first) if first else None,
    }
    _emit_response("live", 200, started, target=target, job_id=payload["job_id"])
    handler._send_json(HTTPStatus.OK, payload)
    return True


def _handle_events(handler: Any, parsed: Any, deps: dict[str, Any]) -> bool:
    """SSE stream for job events.

    v1 ships a minimal "snapshot + keepalive" stream: emit the current row
    once as an SSE event, then short-lived keepalive comments at 5s intervals
    until the job reaches terminal. Real per-event streaming (driven by
    logs/events.jsonl tailing) is a Phase 9 follow-up.
    """
    query = parse_qs(parsed.query)
    job_id = (query.get("job_id") or [""])[0]
    _emit_request("events", handler, job_id=job_id)
    started = time.monotonic()
    if not job_id:
        handler._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "missing_job_id"})
        _emit_response("events", 400, started, reason="missing_job_id")
        return True
    supabase_client = deps.get("supabase_client") or _default_supabase_client()
    try:
        row = delta_job_store.get_job(supabase_client, job_id=job_id)
    except LookupError:
        handler._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "job_not_found"})
        _emit_response("events", 404, started, job_id=job_id)
        return True

    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "keep-alive")
    handler.end_headers()
    snapshot = json.dumps(_row_to_dict(row))
    handler.wfile.write(f"retry: 5000\n\n".encode("utf-8"))
    handler.wfile.write(f"event: snapshot\ndata: {snapshot}\n\n".encode("utf-8"))
    handler.wfile.flush()
    emit_event(
        "ingest.delta.ui.sse.connected",
        {"job_id": job_id},
    )
    _emit_response("events", 200, started, job_id=job_id)
    # Note: v1 does NOT tail events.jsonl — the client is expected to
    # reconnect (and/or fall back to /status polling) for progress updates.
    # Closing the stream here avoids holding the worker thread on the tiny
    # Python HTTPServer. The admin UI's SSE subscriber auto-reconnects.
    emit_event(
        "ingest.delta.ui.sse.disconnected",
        {"job_id": job_id, "reason": "v1_single_snapshot"},
    )
    return True


def _row_to_dict(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "job_id": row.job_id,
        "lock_target": row.lock_target,
        "stage": row.stage,
        "delta_id": row.delta_id,
        "progress_pct": row.progress_pct,
        "started_at": row.started_at,
        "last_heartbeat_at": row.last_heartbeat_at,
        "completed_at": row.completed_at,
        "created_by": row.created_by,
        "cancel_requested": row.cancel_requested,
        "error_class": row.error_class,
        "error_message": row.error_message,
        "report_json": row.report_json,
    }


def _default_supabase_client() -> Any:
    from .supabase_client import get_supabase_client

    return get_supabase_client()


# ---------------------------------------------------------------------------
# Public entry points — match the convention used by ui_ingest_run_controllers.
# ---------------------------------------------------------------------------


def _handle_preview_progress(handler: Any, deps: dict[str, Any]) -> bool:
    """Peek at ``logs/events.jsonl`` to report how far the classifier got.

    The preview path runs the PASO 4 classifier over the full corpus
    (rate-limited at ~1 doc/sec), so a first-run preview takes 20-25 min.
    This endpoint tails the events log, counts classifier events in the
    current run, and returns the latest filename seen so the UI can show
    real "X of ~N — just processed: <filename>" feedback instead of a
    blind spinner.
    """
    from pathlib import Path

    started = time.monotonic()
    _emit_request("preview-progress", handler)
    workspace_root: Path = deps.get("corpus_dir") or Path.cwd()
    # logs/events.jsonl sits next to knowledge_base/ in the repo root.
    if workspace_root.name == "knowledge_base":
        workspace_root = workspace_root.parent
    events_path = workspace_root / "logs" / "events.jsonl"
    if not events_path.exists():
        handler._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "available": False,
                "reason": "events_log_missing",
            },
        )
        _emit_response("preview-progress", 200, started, available=False)
        return True

    # Tail the last ~200 KiB to stay fast even if the log is huge. At
    # ~400 bytes per event that's ~500 events, plenty for any window the
    # UI would want to summarize.
    tail_bytes = 200 * 1024
    classified_since: int = 0
    last_filename: str | None = None
    last_ts: str | None = None
    classifier_input_count: int | None = None
    prematched_count: int | None = None
    delta_id: str | None = None
    try:
        size = events_path.stat().st_size
        offset = max(0, size - tail_bytes)
        with events_path.open("rb") as fh:
            fh.seek(offset)
            raw = fh.read()
        text = raw.decode("utf-8", errors="replace")
        lines = text.splitlines()
        # Skip the first (possibly partial) line.
        if offset > 0 and lines:
            lines = lines[1:]
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            et = ev.get("event_type")
            if et == "ingest.delta.run.start":
                # Each run emits this first. Capture the delta_id so the
                # UI can display it (operator can grep logs by this id).
                payload_ev = ev.get("payload") or {}
                d_id = payload_ev.get("delta_id")
                if isinstance(d_id, str) and d_id:
                    delta_id = d_id
                classified_since = 0
                last_filename = None
                classifier_input_count = None
                prematched_count = None
                last_ts = ev.get("ts_utc") or last_ts
            elif et == "ingest.delta.shortcut.computed":
                # Emits BEFORE the classifier kicks in — resets counters
                # so the UI shows only this run's work, and surfaces the
                # real denominator the feeler should render instead of a
                # hardcoded "~1.300".
                payload_ev = ev.get("payload") or {}
                d_id = payload_ev.get("delta_id")
                if isinstance(d_id, str) and d_id:
                    delta_id = d_id
                classifier_input_count = int(
                    payload_ev.get("classifier_input_count") or 0
                )
                prematched_count = int(payload_ev.get("prematched_count") or 0)
                classified_since = 0
                last_filename = None
                last_ts = ev.get("ts_utc") or last_ts
            elif et == "subtopic.ingest.classified":
                classified_since += 1
                payload_ev = ev.get("payload") or {}
                fname = payload_ev.get("filename")
                if isinstance(fname, str) and fname:
                    last_filename = fname
                last_ts = ev.get("ts_utc") or last_ts
            elif et in {"ingest.delta.plan.computed", "ingest.delta.cli.done"}:
                # A preview/apply completed — reset so the next run
                # starts fresh in our view. Keep delta_id — the operator
                # may still want to look up the completed run's logs.
                classified_since = 0
                last_filename = None
                classifier_input_count = None
                prematched_count = None
                last_ts = ev.get("ts_utc") or last_ts
    except Exception as exc:  # noqa: BLE001
        handler._send_json(
            HTTPStatus.OK,
            {"ok": True, "available": False, "reason": f"read_error:{exc}"},
        )
        _emit_response("preview-progress", 200, started, available=False)
        return True

    payload = {
        "ok": True,
        "available": True,
        "classified_since_last_run_boundary": int(classified_since),
        "last_filename": last_filename,
        "last_ts_utc": last_ts,
        # Real denominator, when the shortcut has fired: the number of
        # docs that ACTUALLY need classifying (not 1.3k). UI should
        # render "N / classifier_input_count" and mention prematched_count
        # as shortcut skips.
        "classifier_input_count": classifier_input_count,
        "prematched_count": prematched_count,
        # Run id — operator can grep logs/events.jsonl by this value to
        # get all trace events for the specific run they're watching.
        "delta_id": delta_id,
    }
    handler._send_json(HTTPStatus.OK, payload)
    _emit_response(
        "preview-progress",
        200,
        started,
        classified=classified_since,
    )
    return True


def handle_ingest_delta_get(
    handler: Any,
    path: str,
    parsed: Any,
    *,
    deps: dict[str, Any],
) -> bool:
    if not path.startswith(API_PREFIX):
        return False
    try:
        _require_admin(handler)
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True

    if path == API_PREFIX + "status":
        return _handle_status(handler, parsed, deps)
    if path == API_PREFIX + "events":
        return _handle_events(handler, parsed, deps)
    if path == API_PREFIX + "live":
        return _handle_live(handler, parsed, deps)
    if path == API_PREFIX + "preview-progress":
        return _handle_preview_progress(handler, deps)
    handler._send_json(HTTPStatus.NOT_FOUND, {"error": "unknown_additive_route"})
    return True


def handle_ingest_delta_post(
    handler: Any,
    path: str,
    parsed: Any,
    *,
    deps: dict[str, Any],
) -> bool:
    if not path.startswith(API_PREFIX):
        return False
    try:
        _require_admin(handler)
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True

    if path == API_PREFIX + "preview":
        return _handle_preview(handler, deps)
    if path == API_PREFIX + "apply":
        return _handle_apply(handler, deps)
    if path == API_PREFIX + "cancel":
        return _handle_cancel(handler, parsed, deps)
    handler._send_json(HTTPStatus.NOT_FOUND, {"error": "unknown_additive_route"})
    return True


__all__ = [
    "API_PREFIX",
    "handle_ingest_delta_get",
    "handle_ingest_delta_post",
]
