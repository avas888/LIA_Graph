"""Ingestion-run admin surface — Lia_Graph native.

Surfaces what the Lia_Graph ingestion pipeline actually produces (audit report,
canonical manifest, graph validation, ``corpus_generations`` rows) and lets
admins trigger a fresh run via ``python -m lia_graph.ingest``.

Routes::

    GET  /api/ingest/state                         — corpus + audit + graph snapshot
    GET  /api/ingest/generations                   — recent generations (cloud Supabase)
    GET  /api/ingest/generations/{id}              — single generation detail
    GET  /api/ingest/job/{id}/progress             — per-stage progress (6 stages)
    GET  /api/ingest/job/{id}/log/tail             — cursor-paginated subprocess log tail
    POST /api/ingest/run                           — kick off background ingest job
    POST /api/ingest/intake                        — drag-to-ingest classify + place endpoint
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from http import HTTPStatus
from pathlib import Path
from typing import Any
from uuid import uuid4

from .background_jobs import run_job_async
from .instrumentation import DEFAULT_LOG_PATH, emit_event
from .platform_auth import PlatformAuthError

_log = logging.getLogger(__name__)


def _trace(event: str, payload: dict[str, Any]) -> None:
    """Single funnel for ingest-orchestration trace lines.

    Writes to ``logs/events.jsonl`` via the canonical ``emit_event`` channel
    AND to the module logger so verbose ``-v`` runs see the same data.
    """
    emit_event(event, payload)
    _log.info("[%s] %s", event, payload)

_GENERATION_ROUTE_RE = re.compile(r"^/api/ingest/generations/([^/]+)$")
_GENERATION_ID_SAFE_RE = re.compile(r"^[A-Za-z0-9_.\-]+$")
_JOB_ID_SAFE_RE = re.compile(r"^[A-Za-z0-9_.\-]+$")
_JOB_PROGRESS_ROUTE_RE = re.compile(r"^/api/ingest/job/([^/]+)/progress$")
_JOB_LOG_TAIL_ROUTE_RE = re.compile(r"^/api/ingest/job/([^/]+)/log/tail$")

# 6-stage pipeline the UI timeline renders. Order matters — it is the visible
# timeline order. See docs/next/ingestfixv1.md §5 Phase 3.
INGEST_STAGES: tuple[str, ...] = (
    "coerce",
    "audit",
    "chunk",
    "sink",
    "falkor",
    "embeddings",
)


def _require_admin(handler: Any) -> None:
    auth_context = handler._resolve_auth_context(required=True)
    if auth_context.role not in {"tenant_admin", "platform_admin"}:
        raise PlatformAuthError(
            "Se requiere rol administrativo.",
            code="auth_role_forbidden",
            http_status=403,
        )


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as exc:
        _log.warning("ingest_state: failed to read %s: %s", path, exc)
        return None


def _file_mtime_iso(path: Path) -> str:
    try:
        from datetime import datetime, timezone
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    except OSError:
        return ""


def _query_active_generation() -> dict[str, Any] | None:
    try:
        from .supabase_client import get_supabase_client
        client = get_supabase_client()
        if client is None:
            _trace("ingest.state.supabase_unavailable", {"layer": "active_generation"})
            return None
        result = (
            client.table("corpus_generations")
            .select("*")
            .eq("is_active", True)
            .order("activated_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = list(result.data or [])
        _trace(
            "ingest.state.active_generation_query",
            {"row_count": len(rows), "active_id": rows[0].get("generation_id") if rows else None},
        )
        return rows[0] if rows else None
    except Exception as exc:  # noqa: BLE001
        _log.warning("ingest_state: active generation query failed: %s", exc)
        _trace("ingest.state.query_failed", {"layer": "active_generation", "error": str(exc)})
        return None


def _query_generations(limit: int = 20) -> list[dict[str, Any]]:
    try:
        from .supabase_client import get_supabase_client
        client = get_supabase_client()
        if client is None:
            return []
        result = (
            client.table("corpus_generations")
            .select("generation_id, generated_at, activated_at, documents, chunks, "
                    "knowledge_class_counts, is_active")
            .order("generated_at", desc=True)
            .limit(max(1, min(limit, 100)))
            .execute()
        )
        return list(result.data or [])
    except Exception as exc:  # noqa: BLE001
        _log.warning("ingest_generations: list query failed: %s", exc)
        return []


def _query_generation(generation_id: str) -> dict[str, Any] | None:
    try:
        from .supabase_client import get_supabase_client
        client = get_supabase_client()
        if client is None:
            return None
        result = (
            client.table("corpus_generations")
            .select("*")
            .eq("generation_id", generation_id)
            .limit(1)
            .execute()
        )
        rows = list(result.data or [])
        row = rows[0] if rows else None
        if row is not None:
            row["subtopic_coverage"] = _query_subtopic_coverage(
                client=client, generation_id=generation_id
            )
        return row
    except Exception as exc:  # noqa: BLE001
        _log.warning("ingest_generation: detail query failed: %s", exc)
        return None


def _query_subtopic_coverage(
    *, client: Any, generation_id: str
) -> dict[str, Any]:
    """Aggregate subtopic coverage for a generation — Phase 7 UI metric.

    Best-effort: returns zeros on any query failure so the UI always has a
    shape to render.
    """
    default = {
        "docs_with_subtopic": 0,
        "docs_requiring_review": 0,
        "docs_total": 0,
    }
    try:
        with_subtopic = (
            client.table("documents")
            .select("doc_id", count="exact")
            .eq("sync_generation", generation_id)
            .not_.is_("subtema", None)
            .execute()
        )
        requiring_review = (
            client.table("documents")
            .select("doc_id", count="exact")
            .eq("sync_generation", generation_id)
            .eq("requires_subtopic_review", True)
            .execute()
        )
        total = (
            client.table("documents")
            .select("doc_id", count="exact")
            .eq("sync_generation", generation_id)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        _log.warning("subtopic_coverage aggregate failed: %s", exc)
        return default
    return {
        "docs_with_subtopic": int(getattr(with_subtopic, "count", 0) or 0),
        "docs_requiring_review": int(getattr(requiring_review, "count", 0) or 0),
        "docs_total": int(getattr(total, "count", 0) or 0),
    }


def _build_state_payload(workspace_root: Path) -> dict[str, Any]:
    artifacts = workspace_root / "artifacts"
    audit = _read_json(artifacts / "corpus_audit_report.json") or {}
    inventory = _read_json(artifacts / "corpus_inventory.json") or {}
    graph_validation = _read_json(artifacts / "graph_validation_report.json") or {}
    revisions = _read_json(artifacts / "revision_candidates.json") or {}

    decision_counts = audit.get("decision_counts", {}) or {}
    audit_payload = {
        "scanned": int(audit.get("scanned_file_count", 0) or 0),
        "include_corpus": int(decision_counts.get("include_corpus", 0) or 0),
        "exclude_internal": int(decision_counts.get("exclude_internal", 0) or 0),
        "revision_candidates": int(decision_counts.get("revision_candidate", 0) or 0),
        "scanned_at": _file_mtime_iso(artifacts / "corpus_audit_report.json"),
        "taxonomy_version": str(audit.get("taxonomy_version", "") or ""),
        "source_origin_counts": dict(audit.get("source_origin_counts", {}) or {}),
        "source_tier_counts": dict(audit.get("source_tier_counts", {}) or {}),
        "authority_level_counts": dict(audit.get("authority_level_counts", {}) or {}),
    }

    pending_revisions = 0
    if isinstance(revisions, dict):
        pending = revisions.get("revision_candidates") or revisions.get("entries") or []
        if isinstance(pending, list):
            pending_revisions = len(pending)
    audit_payload["pending_revisions"] = pending_revisions

    active = _query_active_generation() or {}
    corpus_payload: dict[str, Any] = {
        "active_generation_id": str(active.get("generation_id", "") or ""),
        "activated_at": str(active.get("activated_at", "") or ""),
        "generated_at": str(active.get("generated_at", "") or ""),
        "documents": int(active.get("documents", 0) or 0),
        "chunks": int(active.get("chunks", 0) or 0),
        "knowledge_class_counts": dict(active.get("knowledge_class_counts", {}) or {}),
        "countries": list(active.get("countries", []) or []),
    }

    inventory_summary = {}
    if isinstance(inventory, dict):
        for key in ("normativa", "interpretacion", "practica"):
            family = inventory.get(key) or {}
            if isinstance(family, dict):
                inventory_summary[key] = int(family.get("document_count", 0) or 0)

    graph_payload = {
        "ok": bool(graph_validation.get("ok", False)),
        "nodes": int(graph_validation.get("node_count", 0) or 0),
        "edges": int(graph_validation.get("edge_count", 0) or 0),
        "validated_at": _file_mtime_iso(artifacts / "graph_validation_report.json"),
    }

    return {
        "corpus": corpus_payload,
        "audit": audit_payload,
        "inventory": inventory_summary,
        "graph": graph_payload,
    }


def _build_empty_stage_payload() -> dict[str, dict[str, Any]]:
    return {
        name: {
            "status": "pending",
            "started_at": "",
            "finished_at": "",
            "counts": {},
            "error": None,
        }
        for name in INGEST_STAGES
    }


def _aggregate_stage_progress(
    events_path: Path,
    *,
    job_id: str,
) -> dict[str, dict[str, Any]]:
    """Read ``logs/events.jsonl``, filter by ``job_id``, aggregate 6-stage state.

    The aggregator is tolerant of malformed lines — it skips them and continues.
    A stage transitions: pending → running (on ``.start``) → done/failed (on
    ``.done`` / ``.failed``). Counts merge across events (later wins per key).
    """
    stages = _build_empty_stage_payload()
    if not events_path.exists():
        return stages

    try:
        with events_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if not isinstance(event, dict):
                    continue
                event_type = str(event.get("event_type") or "").strip()
                if not event_type.startswith("ingest.run.stage."):
                    continue
                payload = event.get("payload") or {}
                if not isinstance(payload, dict):
                    continue
                if str(payload.get("job_id") or "").strip() != job_id:
                    continue
                # event_type format: ingest.run.stage.<name>.<outcome>
                rest = event_type[len("ingest.run.stage."):]
                if "." not in rest:
                    continue
                stage_name, outcome = rest.rsplit(".", 1)
                if stage_name not in stages:
                    continue
                entry = stages[stage_name]
                ts = str(event.get("ts_utc") or "").strip()
                if outcome == "start":
                    entry["status"] = "running"
                    entry["started_at"] = str(payload.get("started_at") or ts)
                elif outcome == "done":
                    entry["status"] = "done"
                    entry["finished_at"] = str(payload.get("finished_at") or ts)
                    counts = payload.get("counts")
                    if isinstance(counts, dict):
                        entry["counts"] = {**entry["counts"], **counts}
                elif outcome == "failed":
                    entry["status"] = "failed"
                    entry["finished_at"] = str(payload.get("finished_at") or ts)
                    entry["error"] = str(payload.get("error") or "stage_failed")
                    partial = payload.get("partial_counts") or payload.get("counts")
                    if isinstance(partial, dict):
                        entry["counts"] = {**entry["counts"], **partial}
    except OSError as exc:
        _log.warning("ingest.progress: events read failed: %s", exc)
    return stages


def _read_log_tail(
    log_path: Path,
    *,
    cursor: int,
    limit: int,
) -> tuple[list[str], int, int]:
    """Return ``(lines, next_cursor, total_lines)`` for the subprocess log tail.

    ``cursor`` is a zero-based line index into the file. The reader is
    resilient to a missing log file (returns empty with cursor=0) because
    the subprocess may not have written anything yet when the UI first
    polls.
    """
    if not log_path.exists():
        return [], 0, 0

    safe_limit = max(1, min(int(limit), 5000))
    safe_cursor = max(0, int(cursor))

    collected: list[str] = []
    total = 0
    try:
        with log_path.open("r", encoding="utf-8", errors="replace") as handle:
            for idx, raw in enumerate(handle):
                total += 1
                if idx < safe_cursor:
                    continue
                if len(collected) >= safe_limit:
                    continue
                collected.append(raw.rstrip("\n"))
    except OSError as exc:
        _log.warning("ingest.log.tail: read failed: %s", exc)
        return [], safe_cursor, 0

    next_cursor = min(total, safe_cursor + len(collected))
    return collected, next_cursor, total


def _spawn_ingest_subprocess(
    workspace_root: Path,
    *,
    suin_scope: str,
    supabase_target: str,
    job_id: str | None = None,
    auto_embed: bool = False,
    auto_promote: bool = False,
) -> dict[str, Any]:
    """Trigger the ingest pipeline — with optional embedding + promotion chain.

    When ``auto_embed`` or ``auto_promote`` are set, dispatches to
    ``scripts/ingest_run_full.sh`` which orchestrates make → embeddings →
    optional production pass. Otherwise falls back to calling ``make`` directly.
    The split keeps ``embedding_ops.py`` and the make target individually
    invokable while the shell wrapper owns the UI-orchestration concern.

    See ``docs/guide/orchestration.md`` Lane 0 + the change-log entry that
    introduced this UI surface.
    """
    log_dir = workspace_root / "artifacts" / "jobs" / "ingest_runs"
    log_dir.mkdir(parents=True, exist_ok=True)
    from datetime import datetime, timezone
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = log_dir / f"ingest_{stamp}.log"

    chained = auto_embed or auto_promote
    if chained:
        cmd = ["bash", "scripts/ingest_run_full.sh"]
    else:
        cmd = [
            "make",
            "phase2-graph-artifacts-supabase",
            f"PHASE2_SUPABASE_TARGET={supabase_target}",
        ]
        if suin_scope:
            cmd.append(f"INGEST_SUIN={suin_scope}")

    log_relative = str(log_path.relative_to(workspace_root))
    _trace(
        "ingest.run.subprocess.start",
        {
            "command": cmd,
            "cwd": str(workspace_root),
            "log_relative_path": log_relative,
            "supabase_target": supabase_target,
            "suin_scope": suin_scope,
            "auto_embed": auto_embed,
            "auto_promote": auto_promote,
            "job_id": job_id,
        },
    )

    env = os.environ.copy()
    if job_id:
        # `lia_graph.ingest` inspects this to tag stage-marker events so the
        # progress endpoint can aggregate per-run without cross-talk.
        env["LIA_INGEST_JOB_ID"] = job_id
    if chained:
        env["PHASE2_SUPABASE_TARGET"] = supabase_target
        env["INGEST_SUIN"] = suin_scope or ""
        env["INGEST_AUTO_EMBED"] = "1" if auto_embed else "0"
        env["INGEST_AUTO_PROMOTE"] = "1" if auto_promote else "0"

    with log_path.open("w", encoding="utf-8") as log_fh:
        log_fh.write(f"$ {' '.join(cmd)}\n\n")
        log_fh.flush()
        result = subprocess.run(
            cmd,
            cwd=str(workspace_root),
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=60 * 60,  # 1h hard cap
            env=env,
        )

    payload = {
        "exit_code": int(result.returncode),
        "log_relative_path": log_relative,
        "suin_scope": suin_scope,
        "supabase_target": supabase_target,
        "job_id": job_id,
    }
    _trace("ingest.run.subprocess.end", payload)
    return payload


def handle_ingest_get(
    handler: Any,
    path: str,
    parsed: Any,
    *,
    deps: dict[str, Any],
) -> bool:
    if not path.startswith("/api/ingest/"):
        return False

    try:
        _require_admin(handler)
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True

    workspace_root: Path = deps["workspace_root"]

    if path == "/api/ingest/state":
        _trace("ingest.state.requested", {"path": path})
        payload = _build_state_payload(workspace_root)
        _trace(
            "ingest.state.served",
            {
                "active_generation_id": payload["corpus"]["active_generation_id"],
                "documents": payload["corpus"]["documents"],
                "audit_scanned": payload["audit"]["scanned"],
                "graph_ok": payload["graph"]["ok"],
            },
        )
        handler._send_json(HTTPStatus.OK, {"ok": True, **payload})
        return True

    if path == "/api/ingest/generations":
        from urllib.parse import parse_qs
        query = parse_qs(parsed.query)
        limit_raw = str((query.get("limit") or ["20"])[0]).strip() or "20"
        try:
            limit = int(limit_raw)
        except ValueError:
            limit = 20
        _trace("ingest.generations.requested", {"limit": limit})
        generations = _query_generations(limit=limit)
        _trace("ingest.generations.served", {"row_count": len(generations)})
        handler._send_json(HTTPStatus.OK, {"ok": True, "generations": generations})
        return True

    match = _GENERATION_ROUTE_RE.match(path)
    if match:
        generation_id = match.group(1)
        if not _GENERATION_ID_SAFE_RE.match(generation_id):
            _trace("ingest.generation.rejected", {"reason": "invalid_id", "raw": generation_id[:64]})
            handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_generation_id"})
            return True
        _trace("ingest.generation.requested", {"generation_id": generation_id})
        row = _query_generation(generation_id)
        if row is None:
            _trace("ingest.generation.not_found", {"generation_id": generation_id})
            handler._send_json(HTTPStatus.NOT_FOUND, {"error": "generation_not_found"})
            return True
        handler._send_json(HTTPStatus.OK, {"ok": True, "generation": row})
        return True

    match = _JOB_PROGRESS_ROUTE_RE.match(path)
    if match:
        job_id = match.group(1)
        if not _JOB_ID_SAFE_RE.match(job_id):
            handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_job_id"})
            return True
        from .jobs_store import load_job
        record = load_job(job_id, base_dir=workspace_root / "artifacts/jobs/runtime")
        if record is None:
            handler._send_json(HTTPStatus.NOT_FOUND, {"error": "job_not_found"})
            return True
        _trace("ingest.progress.requested", {"job_id": job_id})
        events_path = workspace_root / DEFAULT_LOG_PATH
        stages = _aggregate_stage_progress(events_path, job_id=job_id)
        overall = _derive_overall_status(record, stages)
        handler._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "job_id": job_id,
                "status": overall,
                "stages": stages,
            },
        )
        return True

    match = _JOB_LOG_TAIL_ROUTE_RE.match(path)
    if match:
        job_id = match.group(1)
        if not _JOB_ID_SAFE_RE.match(job_id):
            handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_job_id"})
            return True
        from .jobs_store import load_job
        record = load_job(job_id, base_dir=workspace_root / "artifacts/jobs/runtime")
        if record is None:
            handler._send_json(HTTPStatus.NOT_FOUND, {"error": "job_not_found"})
            return True
        from urllib.parse import parse_qs
        query = parse_qs(parsed.query)
        try:
            cursor = int((query.get("cursor") or ["0"])[0])
        except (TypeError, ValueError):
            cursor = 0
        try:
            limit = int((query.get("limit") or ["200"])[0])
        except (TypeError, ValueError):
            limit = 200
        log_rel = _extract_log_relative_path(record)
        log_path = workspace_root / log_rel if log_rel else None
        if log_path is None:
            handler._send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "job_id": job_id,
                    "lines": [],
                    "next_cursor": cursor,
                    "total_lines": 0,
                    "log_relative_path": None,
                },
            )
            return True
        lines, next_cursor, total = _read_log_tail(log_path, cursor=cursor, limit=limit)
        _trace(
            "ingest.log.tail.served",
            {"job_id": job_id, "returned": len(lines), "cursor": cursor, "next_cursor": next_cursor},
        )
        handler._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "job_id": job_id,
                "lines": lines,
                "next_cursor": next_cursor,
                "total_lines": total,
                "log_relative_path": log_rel,
            },
        )
        return True

    return False


def _extract_log_relative_path(record: Any) -> str | None:
    """Pull ``log_relative_path`` from a job record's result payload.

    ``_spawn_ingest_subprocess`` writes this path into the payload on both
    the normal end event and the result returned to ``run_job_async``.
    """
    payload = getattr(record, "result_payload", None) or {}
    if not isinstance(payload, dict):
        return None
    candidate = payload.get("log_relative_path")
    if isinstance(candidate, str) and candidate.strip():
        return candidate.strip()
    return None


def _derive_overall_status(record: Any, stages: dict[str, dict[str, Any]]) -> str:
    """Collapse the job status + per-stage state into a single enum string.

    The UI only needs one of ``queued | running | completed | failed``;
    ``_aggregate_stage_progress`` already reflects failed stages but we defer
    to the jobs_store as the source of truth when the record carries a
    terminal status.
    """
    job_status = str(getattr(record, "status", "") or "").strip() or "queued"
    if job_status in {"completed", "failed"}:
        return job_status
    # If any stage marks failed, surface failed immediately.
    if any(entry.get("status") == "failed" for entry in stages.values()):
        return "failed"
    if any(entry.get("status") == "running" for entry in stages.values()):
        return "running"
    return job_status


_SUPPORTED_INTAKE_EXTENSIONS = frozenset({".md", ".txt", ".json", ".pdf", ".docx"})
# Hard cap on files per intake batch. Set generously so a full Dropbox
# folder drop (~76 files observed) fits comfortably. The 64 MiB HTTP payload
# cap in ui_server_handler_base._read_json_payload is the other backstop;
# at ~30 KiB/file base64 average, 500 files ≈ 15 MiB — safely under that.
_INTAKE_MAX_FILES = 500
_INTAKE_MAX_BYTES_PER_FILE = 25 * 1024 * 1024  # 25 MiB — matches Lia_contadores
_FILENAME_SAFE_RE = re.compile(r"^[A-Za-z0-9._\- ]+$")
_RELATIVE_PATH_UNSAFE_RE = re.compile(r"(^|/)\.\.(/|$)|^/|\\")


def _safe_topic_dir(topic: str | None) -> str:
    """Return a filesystem-safe topic directory name.

    Falls back to ``general`` when the topic is empty or contains unsafe chars
    so intake never lands files at the corpus root.
    """
    candidate = str(topic or "").strip().lower()
    if not candidate or not re.fullmatch(r"[a-z0-9_\-]+", candidate):
        return "general"
    return candidate


def _validate_intake_filename(filename: str) -> str | None:
    name = str(filename or "").strip()
    if not name:
        return "filename_required"
    if "/" in name or "\\" in name:
        return "filename_traversal"
    if not _FILENAME_SAFE_RE.fullmatch(name):
        return "filename_unsafe_characters"
    if not any(name.lower().endswith(ext) for ext in _SUPPORTED_INTAKE_EXTENSIONS):
        return "unsupported_extension"
    return None


def _validate_relative_path(rel: str | None) -> str | None:
    if not rel:
        return None
    if _RELATIVE_PATH_UNSAFE_RE.search(rel):
        return "relative_path_traversal"
    return None


def _decode_intake_file(raw_b64: str) -> tuple[bytes | None, str | None]:
    try:
        data = base64.b64decode(raw_b64 or "", validate=True)
    except (ValueError, TypeError, base64.binascii.Error):
        return None, "invalid_base64"
    if len(data) > _INTAKE_MAX_BYTES_PER_FILE:
        return None, "file_too_large"
    return data, None


def _checksum_already_ingested(checksum: str) -> dict[str, Any] | None:
    """Supabase check — is this exact byte-content already in the active
    generation? Returns the match row or None. Soft-fails on any error.
    """
    try:
        from .supabase_client import get_supabase_client
        client = get_supabase_client()
        if client is None:
            return None
        result = (
            client.table("documents")
            .select("doc_id,filename,checksum")
            .eq("checksum", checksum)
            .limit(1)
            .execute()
        )
        rows = list(result.data or [])
        return rows[0] if rows else None
    except Exception:  # noqa: BLE001
        return None


def _handle_ingest_intake_post(
    handler: Any,
    *,
    deps: dict[str, Any],
) -> bool:
    """Classify + coerce + validate + place dropped files.

    Wire format (JSON body) — chosen over true multipart/form-data so the
    handler stays robust against the absence of a multipart parser in the
    stdlib and so tests exercise the same bytes the frontend sends:

    ```json
    {
      "batch_id": "optional_id_generated_if_missing",
      "files": [
        {
          "filename": "Resolucion-532-2024.md",
          "content_base64": "...",
          "relative_path": "NORMATIVA/"
        }
      ],
      "options": {
        "mirror_to_dropbox": false,
        "dropbox_root": null
      }
    }
    ```

    Returns:
    ```json
    {
      "ok": true,
      "batch_id": "...",
      "summary": {"received": 3, "placed": 3, "deduped": 0, "rejected": 0},
      "files": [ {filename, placed_path, autogenerar_*, coercion_method, ...} ]
    }
    ```
    """
    try:
        _require_admin(handler)
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True

    workspace_root: Path = deps["workspace_root"]
    # Intake batches carry base64-encoded file contents — ~1.4x the raw
    # size. The default 1 MiB cap in _read_json_payload is appropriate for
    # pure JSON control-plane calls but bombs on a handful of markdown
    # files. 64 MiB comfortably covers ~50 files of 1 MB each post-encode,
    # which matches the UI's drag-drop batch expectations.
    body = handler._read_json_payload(
        object_error="Se requiere un objeto JSON.",
        max_size=64 * 1_048_576,
    ) or {}

    files_raw = body.get("files") or []
    if not isinstance(files_raw, list) or not files_raw:
        handler._send_json(
            HTTPStatus.BAD_REQUEST,
            {"error": "files_required", "details": "Se requiere al menos un archivo."},
        )
        return True
    if len(files_raw) > _INTAKE_MAX_FILES:
        handler._send_json(
            HTTPStatus.BAD_REQUEST,
            {"error": "batch_too_large", "details": f"Max {_INTAKE_MAX_FILES} archivos por lote."},
        )
        return True

    options = body.get("options") or {}
    mirror_to_dropbox = bool(options.get("mirror_to_dropbox", False))
    dropbox_root_raw = str(options.get("dropbox_root") or "").strip()

    batch_id = str(body.get("batch_id") or "").strip() or f"intake_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid4().hex[:8]}"
    if not _GENERATION_ID_SAFE_RE.match(batch_id):
        handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_batch_id"})
        return True

    _trace(
        "ingest.intake.received",
        {"batch_id": batch_id, "file_count": len(files_raw)},
    )

    results: list[dict[str, Any]] = []
    summary = {"received": len(files_raw), "placed": 0, "deduped": 0, "rejected": 0}

    knowledge_base_root = workspace_root / "knowledge_base"
    intake_artifacts_dir = workspace_root / "artifacts/intake"
    intake_artifacts_dir.mkdir(parents=True, exist_ok=True)

    for idx, entry in enumerate(files_raw):
        if not isinstance(entry, dict):
            results.append({"index": idx, "error": "invalid_entry"})
            summary["rejected"] += 1
            continue
        filename = str(entry.get("filename") or "").strip()
        rel_path = str(entry.get("relative_path") or "").strip() or None
        content_b64 = str(entry.get("content_base64") or "")

        err = _validate_intake_filename(filename)
        if err:
            results.append({"filename": filename, "error": err})
            summary["rejected"] += 1
            _trace("ingest.intake.failed", {"batch_id": batch_id, "filename": filename, "error": err})
            continue
        rel_err = _validate_relative_path(rel_path)
        if rel_err:
            results.append({"filename": filename, "error": rel_err})
            summary["rejected"] += 1
            _trace("ingest.intake.failed", {"batch_id": batch_id, "filename": filename, "error": rel_err})
            continue

        data, decode_err = _decode_intake_file(content_b64)
        if decode_err is not None:
            results.append({"filename": filename, "error": decode_err})
            summary["rejected"] += 1
            _trace("ingest.intake.failed", {"batch_id": batch_id, "filename": filename, "error": decode_err})
            continue
        assert data is not None

        checksum = hashlib.sha256(data).hexdigest()
        dedup_row = _checksum_already_ingested(checksum)
        if dedup_row is not None:
            summary["deduped"] += 1
            results.append(
                {
                    "filename": filename,
                    "skipped_duplicate": True,
                    "existing_doc_id": dedup_row.get("doc_id"),
                    "checksum": checksum,
                }
            )
            _trace(
                "ingest.intake.skipped_duplicate",
                {"batch_id": batch_id, "filename": filename, "existing_doc_id": dedup_row.get("doc_id")},
            )
            continue

        # Classify → coerce → validate, then place on disk.
        try:
            from .ingestion_classifier import classify_ingestion_document
            text_preview = data[:2048].decode("utf-8", errors="replace")
            body_text = data.decode("utf-8", errors="replace") if filename.lower().endswith((".md", ".txt", ".json")) else text_preview
            classification = classify_ingestion_document(
                filename=filename,
                body_text=text_preview,
            )
        except Exception as exc:  # noqa: BLE001
            results.append({"filename": filename, "error": f"classify_failed:{exc}"})
            summary["rejected"] += 1
            _trace("ingest.intake.failed", {"batch_id": batch_id, "filename": filename, "error": "classify_failed"})
            continue

        _trace(
            "ingest.intake.classified",
            {
                "batch_id": batch_id,
                "filename": filename,
                "detected_topic": classification.detected_topic,
                "detected_type": classification.detected_type,
                "topic_confidence": classification.topic_confidence,
                "combined_confidence": classification.combined_confidence,
                "is_new_topic": classification.is_new_topic,
                "requires_review": classification.requires_review,
                "subtopic_key": classification.subtopic_key,
                "subtopic_confidence": classification.subtopic_confidence,
                "requires_subtopic_review": classification.requires_subtopic_review,
            },
        )

        # Coerce only text-shaped docs; leave binary docs for downstream parser.
        coercion_payload: dict[str, Any] = {"coercion_method": "skipped_binary"}
        if filename.lower().endswith((".md", ".txt")):
            try:
                from .ingestion_section_coercer import coerce_to_canonical_template
                coerce_result = coerce_to_canonical_template(
                    body_text,
                    identification_hints={
                        "titulo": filename,
                        "ambito_tema": classification.detected_topic or "",
                    },
                    metadata_hints={
                        "coercion_method": "",  # set by coercer
                        "source_relative_path": rel_path or "",
                        "source_tier": "intake",
                        "language": "es",
                    },
                    skip_llm=True,  # intake-time: keep it fast; LLM coerce happens at regrandfather time
                    filename=filename,
                )
                coerced_markdown = coerce_result.coerced_markdown
                coercion_payload = {
                    "coercion_method": coerce_result.coercion_method,
                    "coercion_confidence": coerce_result.confidence,
                    "sections_matched_count": coerce_result.sections_matched_count,
                }
            except Exception as exc:  # noqa: BLE001
                results.append({"filename": filename, "error": f"coerce_failed:{exc}"})
                summary["rejected"] += 1
                _trace("ingest.intake.failed", {"batch_id": batch_id, "filename": filename, "error": "coerce_failed"})
                continue

            # Validate (non-blocking: we still write the doc, but flag the row).
            try:
                from .ingestion_validator import validate_canonical_template
                validation = validate_canonical_template(coerced_markdown, strict=False)
                validation_payload = {
                    "validation_ok": validation.ok,
                    "missing_sections": list(validation.missing_sections),
                    "missing_keys": list(validation.missing_keys),
                }
            except Exception as exc:  # noqa: BLE001
                validation_payload = {"validation_ok": False, "error": str(exc)}
        else:
            coerced_markdown = None
            validation_payload = {"validation_ok": True, "skipped_binary": True}

        topic_dir = _safe_topic_dir(classification.detected_topic)
        target_dir = knowledge_base_root / topic_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / filename

        try:
            write_bytes = (
                coerced_markdown.encode("utf-8")
                if coerced_markdown is not None
                else data
            )
            target_path.write_bytes(write_bytes)
        except OSError as exc:
            results.append({"filename": filename, "error": f"write_failed:{exc}"})
            summary["rejected"] += 1
            _trace("ingest.intake.failed", {"batch_id": batch_id, "filename": filename, "error": "write_failed"})
            continue

        mirror_path: str | None = None
        if mirror_to_dropbox and dropbox_root_raw:
            try:
                dbx_dir = Path(dropbox_root_raw) / "to_upload_graph" / topic_dir
                dbx_dir.mkdir(parents=True, exist_ok=True)
                mirror_target = dbx_dir / filename
                mirror_target.write_bytes(write_bytes)
                mirror_path = str(mirror_target)
            except OSError as exc:
                _log.warning("ingest.intake: dropbox mirror failed for %s: %s", filename, exc)

        summary["placed"] += 1
        row: dict[str, Any] = {
            "filename": filename,
            "checksum": checksum,
            "bytes": len(data),
            "placed_path": str(target_path.relative_to(workspace_root)) if target_path.is_relative_to(workspace_root) else str(target_path),
            "mirror_path": mirror_path,
            "topic_dir": topic_dir,
            "detected_topic": classification.detected_topic,
            "detected_type": classification.detected_type,
            "topic_confidence": classification.topic_confidence,
            "type_confidence": classification.type_confidence,
            "combined_confidence": classification.combined_confidence,
            "classification_source": classification.classification_source,
            "autogenerar_label": classification.generated_label,
            "autogenerar_rationale": classification.rationale,
            "autogenerar_resolved_topic": classification.resolved_to_existing,
            "autogenerar_synonym_confidence": classification.synonym_confidence,
            "autogenerar_is_new": classification.is_new_topic,
            "autogenerar_suggested_key": classification.suggested_key,
            "requires_review": classification.requires_review,
            "subtopic_key": classification.subtopic_key,
            "subtopic_label": classification.subtopic_label,
            "subtopic_confidence": classification.subtopic_confidence,
            "subtopic_is_new": classification.subtopic_is_new,
            "subtopic_suggested_key": classification.subtopic_suggested_key,
            "requires_subtopic_review": classification.requires_subtopic_review,
            **coercion_payload,
            **validation_payload,
        }
        results.append(row)
        _trace(
            "ingest.intake.placed",
            {"batch_id": batch_id, "filename": filename, "placed_path": row["placed_path"]},
        )

    # Sidecar JSONL for audit + replay.
    sidecar_path = intake_artifacts_dir / f"{batch_id}.jsonl"
    try:
        with sidecar_path.open("w", encoding="utf-8") as fh:
            for row in results:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError as exc:
        _log.warning("ingest.intake: sidecar write failed: %s", exc)

    _trace(
        "ingest.intake.summary",
        {"batch_id": batch_id, **summary, "sidecar_path": str(sidecar_path)},
    )

    handler._send_json(
        HTTPStatus.OK,
        {
            "ok": True,
            "batch_id": batch_id,
            "summary": summary,
            "files": results,
            "sidecar_relative_path": str(sidecar_path.relative_to(workspace_root)) if sidecar_path.is_relative_to(workspace_root) else str(sidecar_path),
        },
    )
    return True


def handle_ingest_post(
    handler: Any,
    path: str,
    *,
    deps: dict[str, Any],
) -> bool:
    if path == "/api/ingest/intake":
        return _handle_ingest_intake_post(handler, deps=deps)
    if path != "/api/ingest/run":
        return False

    try:
        _require_admin(handler)
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True

    workspace_root: Path = deps["workspace_root"]
    payload = handler._read_json_payload(object_error="Se requiere un objeto JSON.") or {}

    raw_target = str(payload.get("supabase_target", "wip")).strip().lower()
    if raw_target not in {"wip", "production"}:
        handler._send_json(
            HTTPStatus.BAD_REQUEST,
            {"error": "invalid_supabase_target", "details": "Use 'wip' or 'production'."},
        )
        return True
    raw_scope = str(payload.get("suin_scope", "")).strip().lower()
    if raw_scope and not _GENERATION_ID_SAFE_RE.match(raw_scope):
        handler._send_json(
            HTTPStatus.BAD_REQUEST,
            {"error": "invalid_suin_scope"},
        )
        return True
    auto_embed = bool(payload.get("auto_embed", False))
    auto_promote = bool(payload.get("auto_promote", False))
    batch_id = str(payload.get("batch_id", "")).strip() or None
    if batch_id and not _GENERATION_ID_SAFE_RE.match(batch_id):
        handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_batch_id"})
        return True

    _trace(
        "ingest.run.requested",
        {
            "supabase_target": raw_target,
            "suin_scope": raw_scope or None,
            "auto_embed": auto_embed,
            "auto_promote": auto_promote,
            "batch_id": batch_id,
        },
    )

    def _task(*, job_id: str) -> dict[str, Any]:
        return _spawn_ingest_subprocess(
            workspace_root,
            suin_scope=raw_scope,
            supabase_target=raw_target,
            job_id=job_id,
            auto_embed=auto_embed,
            auto_promote=auto_promote,
        )

    job_id = run_job_async(
        task=_task,
        pass_job_id=True,
        job_type="ingest_run",
        request_payload={
            "suin_scope": raw_scope,
            "supabase_target": raw_target,
            "auto_embed": auto_embed,
            "auto_promote": auto_promote,
            "batch_id": batch_id,
        },
        job_name=f"lia-ingest-{raw_target}-{raw_scope or 'core'}",
    )

    _trace(
        "ingest.run.dispatched",
        {"job_id": job_id, "supabase_target": raw_target, "suin_scope": raw_scope or None},
    )

    handler._send_json(HTTPStatus.OK, {"ok": True, "job_id": job_id})
    return True
