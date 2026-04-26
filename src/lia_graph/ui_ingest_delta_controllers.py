"""Admin-scope HTTP controllers for the additive-corpus-v1 delta path.

Phase 8 of ``docs/done/next/additive_corpusv1.md``. Six endpoints under
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


def _maybe_inject_token_from_query(handler: Any, parsed: Any) -> None:
    """EventSource cannot send `Authorization` headers, so the SSE caller
    passes the bearer via `?token=...`. If the header is absent, lift the
    query-param token into the header so the existing `_require_admin`
    flow validates it normally — no parallel auth path to maintain.
    """
    existing = (handler.headers.get("Authorization") or "").strip()
    if existing:
        return
    query = parse_qs(parsed.query)
    token = (query.get("token") or [""])[0].strip()
    if not token:
        return
    handler.headers["Authorization"] = f"Bearer {token}"


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
            rate_limit_rpm=int(deps.get("rate_limit_rpm", 300)),
            classifier_workers=deps.get("classifier_workers"),
            supabase_workers=deps.get("supabase_workers"),
            force_full_classify=force_full_classify,
            # Asymmetric-retirement safety — GUI flow is structurally
            # incapable of retiring cloud docs. See
            # `docs/learnings/ingestion/asymmetric-retirement-safety.md`.
            # Explicit-False (not relying on the default) makes the contract
            # self-evident at this call site and grep-greppable.
            allow_retirements=False,
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
    """Read per-bucket filename samples from the delta report.

    Populated via `DeltaRunReport.delta_doc_samples` (capped at 6 per bucket
    in `materialize_delta`). Closes the operator's "RETIRADOS=5, what 5?"
    trap by surfacing the actual filenames in the preview banner.
    """
    samples = getattr(report, "delta_doc_samples", None) or {}
    return {
        "added": list(samples.get("added") or []),
        "modified": list(samples.get("modified") or []),
        "removed": list(samples.get("removed") or []),
    }


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


_SSE_TAIL_MAX_DURATION_S = 1800  # 30 min hard cap per connection
_SSE_TAIL_KEEPALIVE_S = 15
_SSE_TAIL_POLL_INTERVAL_S = 0.5
_SSE_TERMINAL_EVENT_TYPES = frozenset(
    {
        "ingest.delta.worker.done",
        "ingest.delta.worker.failed",
        "ingest.delta.cli.done",
    }
)
# Event types the SSE stream forwards even when they don't carry a job_id
# or delta_id payload tag (the classifier emits per-doc events without a
# delta tag because it predates the additive runtime). The lock prevents
# concurrent jobs against the same target so the cross-job confusion risk
# is bounded.
_SSE_GLOBAL_PASSTHROUGH_EVENT_TYPES = frozenset(
    {
        "subtopic.ingest.classified",
        "subtopic.graph.binding_built",
        "subtopic.graph.bindings_summary",
        "ingest.delta.classifier.summary",
        "ingest.delta.parity.check.start",
        "ingest.delta.parity.check.done",
        "ingest.delta.parity.check.mismatch",
        "ingest.delta.falkor.indexes_verified",
        "ingest.delta.falkor.indexes_skipped",
    }
)
# Event-type prefixes considered "ingest progress." Anything else is
# filtered out so the consumer doesn't see chat / API noise mixed into the
# delta progress stream.
_SSE_RELEVANT_EVENT_PREFIXES = ("ingest.delta.", "subtopic.")


def _events_jsonl_path(deps: dict[str, Any]) -> Any:
    """Resolve the canonical events.jsonl path. Mirrors the heuristic in
    `_handle_preview_progress`: corpus_dir's parent (so that running with
    corpus_dir=knowledge_base/ still finds logs/events.jsonl in the repo
    root). Tests inject `events_log_path` directly.
    """
    from pathlib import Path

    explicit = deps.get("events_log_path")
    if explicit is not None:
        return Path(explicit)
    workspace_root = deps.get("corpus_dir") or Path.cwd()
    if hasattr(workspace_root, "name") and workspace_root.name == "knowledge_base":
        workspace_root = workspace_root.parent
    return Path(workspace_root) / "logs" / "events.jsonl"


def _sse_event_matches_job(
    event_type: str,
    payload: dict[str, Any],
    *,
    job_id: str,
    delta_id: str,
) -> bool:
    """Filter rule for the SSE tail.

    - Worker events carry `job_id` → must match.
    - Runtime events carry `delta_id` → must match.
    - Global pass-through events (per-doc classifier emissions without a
      delta tag) flow through whenever the job is active.
    - Anything else with neither tag is dropped.
    """
    if not any(event_type.startswith(p) for p in _SSE_RELEVANT_EVENT_PREFIXES):
        return False
    event_job_id = str(payload.get("job_id") or "")
    if event_job_id:
        return event_job_id == job_id
    event_delta_id = str(payload.get("delta_id") or "")
    if event_delta_id:
        return event_delta_id == delta_id
    return event_type in _SSE_GLOBAL_PASSTHROUGH_EVENT_TYPES


def _handle_events(handler: Any, parsed: Any, deps: dict[str, Any]) -> bool:
    """SSE stream for a delta job — Fase C (real-time).

    Sends the initial row snapshot, then tails `logs/events.jsonl` and
    forwards every event tagged with this `job_id` / `delta_id` plus a
    bounded set of per-doc classifier events. Closes when a terminal worker
    event lands, when the client disconnects (broken pipe), or after a
    30-minute hard cap.

    Auth: EventSource cannot send `Authorization` headers, so the caller
    may pass the bearer via `?token=...`. The query-param shim lifts it
    into the header before `_require_admin` validates.
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

    delta_id = str(getattr(row, "delta_id", "") or "")

    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "keep-alive")
    handler.send_header("X-Accel-Buffering", "no")  # disable nginx buffering
    handler.end_headers()
    snapshot = json.dumps(_row_to_dict(row), ensure_ascii=False)
    try:
        handler.wfile.write(b"retry: 5000\n\n")
        handler.wfile.write(f"event: snapshot\ndata: {snapshot}\n\n".encode("utf-8"))
        handler.wfile.flush()
    except (BrokenPipeError, ConnectionResetError):
        emit_event(
            "ingest.delta.ui.sse.disconnected",
            {"job_id": job_id, "reason": "client_gone_before_snapshot"},
        )
        return True

    emit_event(
        "ingest.delta.ui.sse.connected",
        {"job_id": job_id, "delta_id": delta_id, "mode": "tail"},
    )
    _emit_response("events", 200, started, job_id=job_id, mode="tail")

    events_path = _events_jsonl_path(deps)
    if not events_path.exists():
        try:
            err = json.dumps({"reason": "events_log_missing"}, ensure_ascii=False)
            handler.wfile.write(f"event: error\ndata: {err}\n\n".encode("utf-8"))
            handler.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        emit_event(
            "ingest.delta.ui.sse.disconnected",
            {"job_id": job_id, "reason": "events_log_missing"},
        )
        return True

    last_keepalive = time.monotonic()
    terminal_seen = False
    disconnect_reason = "timeout"
    sleep_fn = deps.get("sse_sleep_fn") or time.sleep
    max_duration_s = float(deps.get("sse_max_duration_s") or _SSE_TAIL_MAX_DURATION_S)
    keepalive_interval_s = float(
        deps.get("sse_keepalive_interval_s") or _SSE_TAIL_KEEPALIVE_S
    )
    poll_interval_s = float(
        deps.get("sse_poll_interval_s") or _SSE_TAIL_POLL_INTERVAL_S
    )
    max_iterations = deps.get("sse_max_iterations")  # test-only escape hatch

    iteration = 0
    seek_to_end = bool(deps.get("sse_seek_to_end", True))
    try:
        with events_path.open("rb") as fh:
            if seek_to_end:
                fh.seek(0, 2)  # tail from end — we already sent the snapshot
            while not terminal_seen and (time.monotonic() - started) < max_duration_s:
                iteration += 1
                if max_iterations is not None and iteration > int(max_iterations):
                    disconnect_reason = "max_iterations_test_only"
                    break
                line = fh.readline()
                if not line:
                    if time.monotonic() - last_keepalive > keepalive_interval_s:
                        try:
                            handler.wfile.write(b": keepalive\n\n")
                            handler.wfile.flush()
                            last_keepalive = time.monotonic()
                        except (BrokenPipeError, ConnectionResetError):
                            disconnect_reason = "client_gone"
                            break
                    sleep_fn(poll_interval_s)
                    continue
                try:
                    ev = json.loads(line.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                event_type = str(ev.get("event_type") or "")
                payload = ev.get("payload") or {}
                if not isinstance(payload, dict):
                    continue
                if not _sse_event_matches_job(
                    event_type, payload, job_id=job_id, delta_id=delta_id
                ):
                    continue
                data = json.dumps(ev, ensure_ascii=False)
                try:
                    handler.wfile.write(
                        f"event: {event_type}\ndata: {data}\n\n".encode("utf-8")
                    )
                    handler.wfile.flush()
                    last_keepalive = time.monotonic()
                except (BrokenPipeError, ConnectionResetError):
                    disconnect_reason = "client_gone"
                    break
                if event_type in _SSE_TERMINAL_EVENT_TYPES:
                    terminal_seen = True
                    disconnect_reason = "terminal"
    finally:
        emit_event(
            "ingest.delta.ui.sse.disconnected",
            {"job_id": job_id, "reason": disconnect_reason},
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
    # The SSE /events endpoint is consumed via EventSource which cannot
    # send Authorization headers; lift `?token=...` into the header BEFORE
    # the auth gate runs so the standard validation handles it.
    if path == API_PREFIX + "events":
        _maybe_inject_token_from_query(handler, parsed)
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
