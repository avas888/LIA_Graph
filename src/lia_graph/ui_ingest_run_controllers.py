"""Ingestion-run admin surface — Lia_Graph native.

Surfaces what the Lia_Graph ingestion pipeline actually produces (audit report,
canonical manifest, graph validation, ``corpus_generations`` rows) and lets
admins trigger a fresh run via ``python -m lia_graph.ingest``.

Routes::

    GET  /api/ingest/state                  — corpus + audit + graph snapshot
    GET  /api/ingest/generations            — recent generations (cloud Supabase)
    GET  /api/ingest/generations/{id}       — single generation detail
    POST /api/ingest/run                    — kick off background ingest job
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
from http import HTTPStatus
from pathlib import Path
from typing import Any

from .background_jobs import run_job_async
from .instrumentation import emit_event
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
        return rows[0] if rows else None
    except Exception as exc:  # noqa: BLE001
        _log.warning("ingest_generation: detail query failed: %s", exc)
        return None


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


def _spawn_ingest_subprocess(
    workspace_root: Path,
    *,
    suin_scope: str,
    supabase_target: str,
) -> dict[str, Any]:
    """Trigger the canonical ``make phase2-graph-artifacts-supabase`` target.

    Calling ``make`` (vs replicating flags) keeps the orchestration single-source
    in the Makefile — it expands ``PHASE2_SUPABASE_SINK_FLAGS`` (``--supabase-sink
    --supabase-target {wip,production} --execute-load --allow-unblessed-load
    --strict-falkordb``) and ``PHASE2_SUIN_FLAG`` automatically. See
    ``docs/guide/orchestration.md`` Lane 0 + the change-log entry that
    introduced this UI surface.

    Default target is ``wip`` (local docker Supabase + local docker FalkorDB).
    Promoting WIP to cloud Supabase + cloud FalkorDB is owned by the
    Promoción surface (``/api/ops/corpus/rebuild-from-wip``).
    """
    log_dir = workspace_root / "artifacts" / "jobs" / "ingest_runs"
    log_dir.mkdir(parents=True, exist_ok=True)
    from datetime import datetime, timezone
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = log_dir / f"ingest_{stamp}.log"

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
        },
    )

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
        )

    payload = {
        "exit_code": int(result.returncode),
        "log_relative_path": log_relative,
        "suin_scope": suin_scope,
        "supabase_target": supabase_target,
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

    return False


def handle_ingest_post(
    handler: Any,
    path: str,
    *,
    deps: dict[str, Any],
) -> bool:
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

    _trace(
        "ingest.run.requested",
        {"supabase_target": raw_target, "suin_scope": raw_scope or None},
    )

    job_id = run_job_async(
        task=lambda: _spawn_ingest_subprocess(
            workspace_root,
            suin_scope=raw_scope,
            supabase_target=raw_target,
        ),
        job_type="ingest_run",
        request_payload={"suin_scope": raw_scope, "supabase_target": raw_target},
        job_name=f"lia-ingest-{raw_target}-{raw_scope or 'core'}",
    )

    _trace(
        "ingest.run.dispatched",
        {"job_id": job_id, "supabase_target": raw_target, "suin_scope": raw_scope or None},
    )

    handler._send_json(HTTPStatus.OK, {"ok": True, "job_id": job_id})
    return True
