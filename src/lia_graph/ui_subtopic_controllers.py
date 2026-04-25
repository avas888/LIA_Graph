"""Subtopic curation admin surface — Lia_Graph native.

Exposes the HTTP endpoints the admin "Sub-topics" tab consumes to browse
mining proposals, inspect evidence, record curator decisions, and read
back the currently-curated taxonomy. All endpoints require admin role.

Routes::

    GET  /api/subtopics/proposals?parent_topic=SLUG   — undecided proposals
    GET  /api/subtopics/evidence?proposal_id=ID       — evidence rows for a proposal
    GET  /api/subtopics/taxonomy                      — current curated taxonomy
    POST /api/subtopics/decision                      — append curator decision

Artifacts (contract pinned in docs/done/next/subtopic_generationv1-contracts.md):
    artifacts/subtopic_proposals_<UTC>.json   — mining output (read)
    artifacts/subtopic_candidates/*.jsonl     — collection rows (read for evidence)
    artifacts/subtopic_decisions.jsonl        — curator decisions (append-only)
    config/subtopic_taxonomy.json             — promoted taxonomy (read)

Trace events::

    subtopic.curation.proposals.requested
    subtopic.curation.proposals.served
    subtopic.curation.decision.recorded
    subtopic.curation.decision.rejected_payload
    subtopic.curation.evidence.requested
"""

from __future__ import annotations

import glob
import json
import logging
import re
from datetime import datetime, timezone
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from .instrumentation import emit_event
from .platform_auth import PlatformAuthError

_log = logging.getLogger(__name__)


_VALID_ACTIONS: frozenset[str] = frozenset(
    {"accept", "reject", "merge", "rename", "split"}
)

_SLUG_RE = re.compile(r"^[A-Za-z0-9_.\-:]+$")


def _trace(event: str, payload: dict[str, Any]) -> None:
    emit_event(event, payload)
    _log.info("[%s] %s", event, payload)


def _require_admin(handler: Any) -> None:
    auth_context = handler._resolve_auth_context(required=True)
    if auth_context.role not in {"tenant_admin", "platform_admin"}:
        raise PlatformAuthError(
            "Se requiere rol administrativo.",
            code="auth_role_forbidden",
            http_status=403,
        )


def _curator_email(handler: Any) -> str:
    auth_context = handler._resolve_auth_context(required=True)
    return (
        getattr(auth_context, "email", None)
        or getattr(auth_context, "user_id", None)
        or "admin"
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _proposals_path(workspace_root: Path) -> Path | None:
    """Return the newest ``artifacts/subtopic_proposals_*.json`` or None."""
    artifacts_dir = workspace_root / "artifacts"
    if not artifacts_dir.is_dir():
        return None
    matches = sorted(
        artifacts_dir.glob("subtopic_proposals_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return matches[0] if matches else None


def _decisions_path(workspace_root: Path) -> Path:
    return workspace_root / "artifacts" / "subtopic_decisions.jsonl"


def _taxonomy_path(workspace_root: Path) -> Path:
    return workspace_root / "config" / "subtopic_taxonomy.json"


def _collection_glob(workspace_root: Path) -> str:
    return str(workspace_root / "artifacts" / "subtopic_candidates" / "collection_*.jsonl")


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as exc:
        _log.warning("ui_subtopic_controllers: failed to read %s: %s", path, exc)
        return None


def _iter_jsonl(path: Path):
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        return


def _load_latest_decisions_by_proposal(
    decisions_path: Path,
) -> dict[str, dict[str, Any]]:
    """Last-write-wins snapshot of decisions keyed by proposal_id."""
    latest: dict[str, dict[str, Any]] = {}
    for row in _iter_jsonl(decisions_path):
        pid = row.get("proposal_id")
        if not isinstance(pid, str) or not pid:
            continue
        latest[pid] = row
    return latest


# ---------------------------------------------------------------------------
# GET /api/subtopics/proposals
# ---------------------------------------------------------------------------


def _handle_proposals_get(handler: Any, parsed: Any, workspace_root: Path) -> None:
    query = parse_qs(parsed.query or "")
    parent_topic_raw = str((query.get("parent_topic") or [""])[0]).strip()
    _trace(
        "subtopic.curation.proposals.requested",
        {"parent_topic": parent_topic_raw or None},
    )
    proposals_file = _proposals_path(workspace_root)
    if proposals_file is None:
        _trace(
            "subtopic.curation.proposals.served",
            {"parent_topic": parent_topic_raw or None, "row_count": 0, "source": None},
        )
        handler._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "source_path": None,
                "proposals": [],
                "decided_count": 0,
            },
        )
        return

    data = _load_json(proposals_file) or {}
    all_proposals: dict[str, list[dict[str, Any]]] = (
        data.get("proposals") or {}
    )
    decisions_by_pid = _load_latest_decisions_by_proposal(
        _decisions_path(workspace_root)
    )

    # Collect rows filtered by parent_topic (if given) and undecided state.
    rows: list[dict[str, Any]] = []
    for parent, proposals in all_proposals.items():
        if parent_topic_raw and parent != parent_topic_raw:
            continue
        for proposal in proposals or []:
            pid = proposal.get("proposal_id")
            if not isinstance(pid, str):
                continue
            prior_decision = decisions_by_pid.get(pid)
            enriched = dict(proposal)
            enriched["parent_topic"] = parent
            enriched["decided"] = prior_decision is not None
            enriched["latest_decision"] = prior_decision
            rows.append(enriched)

    _trace(
        "subtopic.curation.proposals.served",
        {
            "parent_topic": parent_topic_raw or None,
            "row_count": len(rows),
            "source": str(proposals_file.relative_to(workspace_root)),
        },
    )
    handler._send_json(
        HTTPStatus.OK,
        {
            "ok": True,
            "source_path": str(proposals_file.relative_to(workspace_root)),
            "proposals": rows,
            "decided_count": sum(1 for r in rows if r.get("decided")),
        },
    )


# ---------------------------------------------------------------------------
# GET /api/subtopics/evidence
# ---------------------------------------------------------------------------


def _handle_evidence_get(handler: Any, parsed: Any, workspace_root: Path) -> None:
    query = parse_qs(parsed.query or "")
    proposal_id = str((query.get("proposal_id") or [""])[0]).strip()
    if not proposal_id or not _SLUG_RE.match(proposal_id):
        handler._send_json(
            HTTPStatus.BAD_REQUEST,
            {"error": "invalid_proposal_id"},
        )
        return

    proposals_file = _proposals_path(workspace_root)
    if proposals_file is None:
        handler._send_json(HTTPStatus.NOT_FOUND, {"error": "no_proposals_file"})
        return

    data = _load_json(proposals_file) or {}
    target: dict[str, Any] | None = None
    target_parent: str | None = None
    for parent, proposals in (data.get("proposals") or {}).items():
        for proposal in proposals or []:
            if proposal.get("proposal_id") == proposal_id:
                target = proposal
                target_parent = parent
                break
        if target is not None:
            break

    if target is None:
        handler._send_json(HTTPStatus.NOT_FOUND, {"error": "proposal_not_found"})
        return

    evidence_doc_ids = set(target.get("evidence_doc_ids") or [])
    _trace(
        "subtopic.curation.evidence.requested",
        {"proposal_id": proposal_id, "doc_count": len(evidence_doc_ids)},
    )

    rows: list[dict[str, Any]] = []
    for path_str in sorted(glob.glob(_collection_glob(workspace_root))):
        for row in _iter_jsonl(Path(path_str)):
            if row.get("doc_id") in evidence_doc_ids:
                rows.append(
                    {
                        "doc_id": row.get("doc_id"),
                        "filename": row.get("filename"),
                        "corpus_relative_path": row.get("corpus_relative_path"),
                        "autogenerar_label": row.get("autogenerar_label"),
                        "autogenerar_rationale": row.get("autogenerar_rationale"),
                        "parent_topic": row.get("parent_topic"),
                    }
                )

    handler._send_json(
        HTTPStatus.OK,
        {
            "ok": True,
            "proposal_id": proposal_id,
            "parent_topic": target_parent,
            "proposed_label": target.get("proposed_label"),
            "evidence": rows,
        },
    )


# ---------------------------------------------------------------------------
# GET /api/subtopics/taxonomy
# ---------------------------------------------------------------------------


def _handle_taxonomy_get(handler: Any, workspace_root: Path) -> None:
    path = _taxonomy_path(workspace_root)
    data = _load_json(path)
    if data is None:
        # Return an empty skeleton when no taxonomy has been promoted yet.
        handler._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "taxonomy": {
                    "version": None,
                    "generated_from": None,
                    "generated_at": None,
                    "subtopics": {},
                },
                "exists": False,
            },
        )
        return
    handler._send_json(
        HTTPStatus.OK,
        {"ok": True, "taxonomy": data, "exists": True},
    )


# ---------------------------------------------------------------------------
# POST /api/subtopics/decision
# ---------------------------------------------------------------------------


def _reject_payload(handler: Any, *, reason: str, field: str | None = None) -> None:
    _trace(
        "subtopic.curation.decision.rejected_payload",
        {"reason": reason, "field": field},
    )
    body: dict[str, Any] = {"error": "invalid_payload", "reason": reason}
    if field:
        body["field"] = field
    handler._send_json(HTTPStatus.BAD_REQUEST, body)


def _load_proposal_index(
    workspace_root: Path,
) -> dict[str, tuple[str, dict[str, Any]]]:
    """Map proposal_id → (parent_topic, proposal_dict) from the latest file."""
    proposals_file = _proposals_path(workspace_root)
    if proposals_file is None:
        return {}
    data = _load_json(proposals_file) or {}
    index: dict[str, tuple[str, dict[str, Any]]] = {}
    for parent, proposals in (data.get("proposals") or {}).items():
        for proposal in proposals or []:
            pid = proposal.get("proposal_id")
            if isinstance(pid, str):
                index[pid] = (parent, proposal)
    return index


def _handle_decision_post(handler: Any, workspace_root: Path) -> None:
    body = handler._read_json_payload(object_error="Se requiere un objeto JSON.")
    if body is None or not isinstance(body, dict):
        _reject_payload(handler, reason="body_must_be_object")
        return

    proposal_id = str(body.get("proposal_id") or "").strip()
    action = str(body.get("action") or "").strip().lower()
    if not proposal_id or not _SLUG_RE.match(proposal_id):
        _reject_payload(handler, reason="invalid_proposal_id", field="proposal_id")
        return
    if action not in _VALID_ACTIONS:
        _reject_payload(handler, reason="invalid_action", field="action")
        return

    # Resolve parent_topic + the known proposal (for evidence_count default).
    index = _load_proposal_index(workspace_root)
    if proposal_id not in index:
        _reject_payload(handler, reason="proposal_not_found", field="proposal_id")
        return
    parent_topic, known_proposal = index[proposal_id]

    final_key_raw = body.get("final_key")
    final_label_raw = body.get("final_label")
    merged_into_raw = body.get("merged_into")
    reason_raw = body.get("reason")
    aliases_raw = body.get("aliases")

    final_key = str(final_key_raw).strip() if final_key_raw else None
    final_label = str(final_label_raw).strip() if final_label_raw else None
    merged_into = str(merged_into_raw).strip() if merged_into_raw else None
    reason = str(reason_raw).strip() if reason_raw else None
    aliases: list[str] | None = None
    if aliases_raw is not None:
        if not isinstance(aliases_raw, list):
            _reject_payload(handler, reason="aliases_must_be_list", field="aliases")
            return
        aliases = [str(a).strip() for a in aliases_raw if str(a).strip()]

    # Per-action validation (contract docs/done/next/subtopic_generationv1-contracts.md).
    if action == "accept":
        if not final_key or not final_label:
            _reject_payload(
                handler, reason="accept_requires_final_key_and_label", field="final_key"
            )
            return
    elif action == "reject":
        if not reason:
            _reject_payload(handler, reason="reject_requires_reason", field="reason")
            return
    elif action == "merge":
        if not merged_into:
            _reject_payload(
                handler, reason="merge_requires_merged_into", field="merged_into"
            )
            return
        if merged_into not in index:
            _reject_payload(
                handler, reason="merged_into_not_found", field="merged_into"
            )
            return
        if index[merged_into][0] != parent_topic:
            _reject_payload(
                handler,
                reason="merged_into_parent_mismatch",
                field="merged_into",
            )
            return
    elif action == "rename":
        if not final_label:
            _reject_payload(
                handler, reason="rename_requires_final_label", field="final_label"
            )
            return
    elif action == "split":
        if not aliases or len(aliases) < 2:
            _reject_payload(
                handler, reason="split_requires_two_or_more_aliases", field="aliases"
            )
            return

    curator = _curator_email(handler)
    ts = _utc_now_iso()

    row: dict[str, Any] = {
        "ts": ts,
        "curator": curator,
        "parent_topic": parent_topic,
        "proposal_id": proposal_id,
        "action": action,
        "final_key": final_key,
        "final_label": final_label,
        "aliases": aliases or [],
        "merged_into": merged_into,
        "reason": reason,
        "evidence_count": int(known_proposal.get("evidence_count") or 0),
    }

    # Append to the decisions JSONL (create parent dir if missing).
    decisions_file = _decisions_path(workspace_root)
    decisions_file.parent.mkdir(parents=True, exist_ok=True)
    with decisions_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    _trace(
        "subtopic.curation.decision.recorded",
        {
            "proposal_id": proposal_id,
            "action": action,
            "curator": curator,
            "final_key": final_key,
            "merged_into": merged_into,
            "parent_topic": parent_topic,
        },
    )

    handler._send_json(HTTPStatus.OK, {"ok": True, "decision": row})


# ---------------------------------------------------------------------------
# Public dispatcher
# ---------------------------------------------------------------------------


def handle_subtopic_get(
    handler: Any,
    path: str,
    parsed: Any,
    *,
    deps: dict[str, Any],
) -> bool:
    if not path.startswith("/api/subtopics/"):
        return False
    try:
        _require_admin(handler)
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True

    workspace_root: Path = deps["workspace_root"]

    if path == "/api/subtopics/proposals":
        _handle_proposals_get(handler, parsed, workspace_root)
        return True
    if path == "/api/subtopics/evidence":
        _handle_evidence_get(handler, parsed, workspace_root)
        return True
    if path == "/api/subtopics/taxonomy":
        _handle_taxonomy_get(handler, workspace_root)
        return True

    return False


def handle_subtopic_post(
    handler: Any,
    path: str,
    *,
    deps: dict[str, Any],
) -> bool:
    if path != "/api/subtopics/decision":
        return False
    try:
        _require_admin(handler)
    except PlatformAuthError as exc:
        handler._send_auth_error(exc)
        return True

    workspace_root: Path = deps["workspace_root"]
    _handle_decision_post(handler, workspace_root)
    return True
