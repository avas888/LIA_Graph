"""Tests for `lia_graph.ui_subtopic_controllers`.

Covers the four routes the "Sub-topics" admin tab calls:

  * GET  /api/subtopics/proposals?parent_topic=SLUG
  * GET  /api/subtopics/evidence?proposal_id=ID
  * GET  /api/subtopics/taxonomy
  * POST /api/subtopics/decision

All tests stub the auth layer via a fake handler and capture trace events
via monkeypatching `_trace`. No cloud, no filesystem outside `tmp_path`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pytest

from lia_graph import ui_subtopic_controllers as ctrl
from lia_graph.platform_auth import PlatformAuthError


@dataclass
class _AuthContext:
    role: str = "platform_admin"
    user_id: str = "admin@lia.dev"
    email: str = "admin@lia.dev"
    tenant_id: str = "tenant-test"


class _FakeHandler:
    def __init__(
        self,
        *,
        role: str = "platform_admin",
        payload: dict[str, Any] | None = None,
        email: str = "admin@lia.dev",
    ) -> None:
        self._auth = _AuthContext(role=role, user_id=email, email=email)
        self._payload = payload
        self.sent: list[tuple[int, dict[str, Any]]] = []

    def _resolve_auth_context(self, *, required: bool = False) -> _AuthContext:  # noqa: ARG002
        return self._auth

    def _send_auth_error(self, exc: PlatformAuthError) -> None:
        self.sent.append((int(getattr(exc, "http_status", 401)), {"error": str(exc)}))

    def _read_json_payload(self, **_kwargs: Any) -> dict[str, Any] | None:
        return self._payload

    def _send_json(self, status: int, body: dict[str, Any], **_kwargs: Any) -> None:
        self.sent.append((int(status), body))


@pytest.fixture(autouse=True)
def _silence_trace(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict[str, Any]]]:
    captured: list[tuple[str, dict[str, Any]]] = []

    def _capture(event: str, payload: dict[str, Any]) -> None:
        captured.append((event, dict(payload)))

    monkeypatch.setattr(ctrl, "_trace", _capture)
    return captured


def _write_proposals(
    workspace_root: Path,
    proposals_by_parent: dict[str, list[dict[str, Any]]],
    *,
    ts: str = "20260421T143000Z",
) -> Path:
    artifacts_dir = workspace_root / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    path = artifacts_dir / f"subtopic_proposals_{ts}.json"
    payload = {
        "version": "2026-04-21-v1",
        "generated_at": "2026-04-21T14:30:00Z",
        "source_collection_paths": [
            "artifacts/subtopic_candidates/collection_20260421T142200Z.jsonl"
        ],
        "cluster_threshold": 0.78,
        "min_cluster_size": 3,
        "proposals": proposals_by_parent,
        "singletons": {},
        "summary": {
            "total_proposals": sum(len(v) for v in proposals_by_parent.values()),
            "total_singletons": 0,
            "parent_topics_with_proposals": len(proposals_by_parent),
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _write_collection(
    workspace_root: Path, rows: list[dict[str, Any]], *, ts: str = "20260421T142200Z"
) -> Path:
    col_dir = workspace_root / "artifacts" / "subtopic_candidates"
    col_dir.mkdir(parents=True, exist_ok=True)
    path = col_dir / f"collection_{ts}.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


# ---------------------------------------------------------------------------
# (a) 403 for non-admin on all endpoints
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method,path,parsed_query",
    [
        ("GET", "/api/subtopics/proposals", ""),
        ("GET", "/api/subtopics/evidence", "proposal_id=laboral::001"),
        ("GET", "/api/subtopics/taxonomy", ""),
    ],
)
def test_get_endpoints_require_admin(
    method: str,
    path: str,
    parsed_query: str,
    tmp_path: Path,
) -> None:
    handler = _FakeHandler(role="tenant_user")
    parsed = urlparse(f"{path}?{parsed_query}" if parsed_query else path)
    matched = ctrl.handle_subtopic_get(
        handler, path, parsed, deps={"workspace_root": tmp_path}
    )
    assert matched is True
    status, _body = handler.sent[-1]
    assert status == 403


def test_decision_post_requires_admin(tmp_path: Path) -> None:
    handler = _FakeHandler(role="tenant_user", payload={"proposal_id": "x", "action": "accept"})
    matched = ctrl.handle_subtopic_post(
        handler, "/api/subtopics/decision", deps={"workspace_root": tmp_path}
    )
    assert matched is True
    status, _ = handler.sent[-1]
    assert status == 403


# ---------------------------------------------------------------------------
# (b) GET /proposals returns [] when no file exists
# ---------------------------------------------------------------------------


def test_proposals_empty_when_no_file(tmp_path: Path) -> None:
    handler = _FakeHandler()
    parsed = urlparse("/api/subtopics/proposals")
    ctrl.handle_subtopic_get(
        handler,
        "/api/subtopics/proposals",
        parsed,
        deps={"workspace_root": tmp_path},
    )
    status, body = handler.sent[-1]
    assert status == 200
    assert body["proposals"] == []
    assert body["source_path"] is None


# ---------------------------------------------------------------------------
# (c) GET /proposals filters by parent_topic
# ---------------------------------------------------------------------------


def test_proposals_filter_by_parent_topic(tmp_path: Path) -> None:
    _write_proposals(
        tmp_path,
        {
            "laboral": [
                {
                    "proposal_id": "laboral::001",
                    "proposed_key": "aportes_parafiscales",
                    "proposed_label": "Aportes parafiscales",
                    "candidate_labels": ["aportes_parafiscales"],
                    "evidence_doc_ids": ["sha256:abc"],
                    "evidence_count": 5,
                    "intra_similarity_min": 0.9,
                    "intra_similarity_max": 0.95,
                }
            ],
            "iva": [
                {
                    "proposal_id": "iva::001",
                    "proposed_key": "iva_exento",
                    "proposed_label": "IVA exento",
                    "candidate_labels": ["iva_exento"],
                    "evidence_doc_ids": ["sha256:def"],
                    "evidence_count": 3,
                    "intra_similarity_min": 1.0,
                    "intra_similarity_max": 1.0,
                }
            ],
        },
    )
    handler = _FakeHandler()
    parsed = urlparse("/api/subtopics/proposals?parent_topic=laboral")
    ctrl.handle_subtopic_get(
        handler,
        "/api/subtopics/proposals",
        parsed,
        deps={"workspace_root": tmp_path},
    )
    status, body = handler.sent[-1]
    assert status == 200
    assert len(body["proposals"]) == 1
    assert body["proposals"][0]["parent_topic"] == "laboral"
    assert body["proposals"][0]["decided"] is False


# ---------------------------------------------------------------------------
# (d) POST /decision accept appends row
# ---------------------------------------------------------------------------


def test_decision_accept_appends_row(tmp_path: Path) -> None:
    _write_proposals(
        tmp_path,
        {
            "laboral": [
                {
                    "proposal_id": "laboral::001",
                    "proposed_key": "aportes_parafiscales",
                    "proposed_label": "Aportes parafiscales",
                    "candidate_labels": ["aportes_parafiscales"],
                    "evidence_doc_ids": [],
                    "evidence_count": 5,
                    "intra_similarity_min": 0.9,
                    "intra_similarity_max": 0.95,
                }
            ]
        },
    )
    handler = _FakeHandler(
        payload={
            "proposal_id": "laboral::001",
            "action": "accept",
            "final_key": "aportes_parafiscales",
            "final_label": "Aportes parafiscales",
            "aliases": ["parafiscales"],
        }
    )
    ctrl.handle_subtopic_post(
        handler, "/api/subtopics/decision", deps={"workspace_root": tmp_path}
    )
    status, body = handler.sent[-1]
    assert status == 200
    assert body["ok"] is True
    assert body["decision"]["action"] == "accept"
    assert body["decision"]["evidence_count"] == 5
    assert body["decision"]["curator"] == "admin@lia.dev"

    # File appended
    decisions_file = tmp_path / "artifacts" / "subtopic_decisions.jsonl"
    assert decisions_file.exists()
    rows = [json.loads(line) for line in decisions_file.read_text().splitlines() if line]
    assert len(rows) == 1
    assert rows[0]["proposal_id"] == "laboral::001"
    assert rows[0]["aliases"] == ["parafiscales"]


# ---------------------------------------------------------------------------
# (e) POST /decision merge validates merged_into exists and same parent
# ---------------------------------------------------------------------------


def test_decision_merge_validates_target_exists(tmp_path: Path) -> None:
    _write_proposals(
        tmp_path,
        {
            "laboral": [
                {
                    "proposal_id": "laboral::001",
                    "proposed_key": "a",
                    "proposed_label": "A",
                    "candidate_labels": ["a"],
                    "evidence_doc_ids": [],
                    "evidence_count": 2,
                    "intra_similarity_min": 1.0,
                    "intra_similarity_max": 1.0,
                },
                {
                    "proposal_id": "laboral::002",
                    "proposed_key": "b",
                    "proposed_label": "B",
                    "candidate_labels": ["b"],
                    "evidence_doc_ids": [],
                    "evidence_count": 3,
                    "intra_similarity_min": 1.0,
                    "intra_similarity_max": 1.0,
                },
            ],
            "iva": [
                {
                    "proposal_id": "iva::001",
                    "proposed_key": "c",
                    "proposed_label": "C",
                    "candidate_labels": ["c"],
                    "evidence_doc_ids": [],
                    "evidence_count": 1,
                    "intra_similarity_min": 1.0,
                    "intra_similarity_max": 1.0,
                }
            ],
        },
    )

    # Merge into a non-existent target → 400.
    handler = _FakeHandler(
        payload={
            "proposal_id": "laboral::001",
            "action": "merge",
            "merged_into": "laboral::999",
        }
    )
    ctrl.handle_subtopic_post(
        handler, "/api/subtopics/decision", deps={"workspace_root": tmp_path}
    )
    status, body = handler.sent[-1]
    assert status == 400
    assert body["reason"] == "merged_into_not_found"

    # Merge into different parent → 400.
    handler2 = _FakeHandler(
        payload={
            "proposal_id": "laboral::001",
            "action": "merge",
            "merged_into": "iva::001",
        }
    )
    ctrl.handle_subtopic_post(
        handler2, "/api/subtopics/decision", deps={"workspace_root": tmp_path}
    )
    status2, body2 = handler2.sent[-1]
    assert status2 == 400
    assert body2["reason"] == "merged_into_parent_mismatch"

    # Valid merge → 200.
    handler3 = _FakeHandler(
        payload={
            "proposal_id": "laboral::001",
            "action": "merge",
            "merged_into": "laboral::002",
        }
    )
    ctrl.handle_subtopic_post(
        handler3, "/api/subtopics/decision", deps={"workspace_root": tmp_path}
    )
    status3, body3 = handler3.sent[-1]
    assert status3 == 200
    assert body3["decision"]["merged_into"] == "laboral::002"


# ---------------------------------------------------------------------------
# (f) POST /decision reject requires reason
# ---------------------------------------------------------------------------


def test_decision_reject_requires_reason(tmp_path: Path) -> None:
    _write_proposals(
        tmp_path,
        {
            "laboral": [
                {
                    "proposal_id": "laboral::001",
                    "proposed_key": "x",
                    "proposed_label": "X",
                    "candidate_labels": ["x"],
                    "evidence_doc_ids": [],
                    "evidence_count": 1,
                    "intra_similarity_min": 1.0,
                    "intra_similarity_max": 1.0,
                }
            ]
        },
    )
    handler = _FakeHandler(
        payload={"proposal_id": "laboral::001", "action": "reject"}
    )
    ctrl.handle_subtopic_post(
        handler, "/api/subtopics/decision", deps={"workspace_root": tmp_path}
    )
    status, body = handler.sent[-1]
    assert status == 400
    assert body["reason"] == "reject_requires_reason"

    handler2 = _FakeHandler(
        payload={
            "proposal_id": "laboral::001",
            "action": "reject",
            "reason": "duplicate of another parent's topic",
        }
    )
    ctrl.handle_subtopic_post(
        handler2, "/api/subtopics/decision", deps={"workspace_root": tmp_path}
    )
    status2, body2 = handler2.sent[-1]
    assert status2 == 200
    assert body2["decision"]["reason"].startswith("duplicate")


# ---------------------------------------------------------------------------
# (g) POST /decision is idempotent via append-only (last-write-wins downstream)
# ---------------------------------------------------------------------------


def test_decision_append_is_idempotent_audit(tmp_path: Path) -> None:
    _write_proposals(
        tmp_path,
        {
            "laboral": [
                {
                    "proposal_id": "laboral::001",
                    "proposed_key": "x",
                    "proposed_label": "X",
                    "candidate_labels": ["x"],
                    "evidence_doc_ids": [],
                    "evidence_count": 4,
                    "intra_similarity_min": 1.0,
                    "intra_similarity_max": 1.0,
                }
            ]
        },
    )
    for label in ("Old Label", "New Label"):
        handler = _FakeHandler(
            payload={
                "proposal_id": "laboral::001",
                "action": "accept",
                "final_key": "x",
                "final_label": label,
            }
        )
        ctrl.handle_subtopic_post(
            handler, "/api/subtopics/decision", deps={"workspace_root": tmp_path}
        )
        status, _ = handler.sent[-1]
        assert status == 200

    decisions_file = tmp_path / "artifacts" / "subtopic_decisions.jsonl"
    rows = [json.loads(line) for line in decisions_file.read_text().splitlines() if line]
    assert len(rows) == 2
    assert rows[0]["final_label"] == "Old Label"
    assert rows[1]["final_label"] == "New Label"


# ---------------------------------------------------------------------------
# (h) GET /taxonomy
# ---------------------------------------------------------------------------


def test_taxonomy_empty_skeleton_when_not_promoted(tmp_path: Path) -> None:
    handler = _FakeHandler()
    parsed = urlparse("/api/subtopics/taxonomy")
    ctrl.handle_subtopic_get(
        handler,
        "/api/subtopics/taxonomy",
        parsed,
        deps={"workspace_root": tmp_path},
    )
    status, body = handler.sent[-1]
    assert status == 200
    assert body["exists"] is False
    assert body["taxonomy"]["subtopics"] == {}


def test_taxonomy_serves_existing_file(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "subtopic_taxonomy.json").write_text(
        json.dumps(
            {
                "version": "2026-04-21-v1",
                "generated_from": "artifacts/subtopic_decisions.jsonl",
                "generated_at": "2026-04-21T15:00:00Z",
                "subtopics": {
                    "laboral": [
                        {
                            "key": "aportes_parafiscales",
                            "label": "Aportes parafiscales",
                            "aliases": [],
                            "evidence_count": 5,
                            "curated_at": "2026-04-21T14:50:00Z",
                            "curator": "admin@lia.dev",
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    handler = _FakeHandler()
    parsed = urlparse("/api/subtopics/taxonomy")
    ctrl.handle_subtopic_get(
        handler,
        "/api/subtopics/taxonomy",
        parsed,
        deps={"workspace_root": tmp_path},
    )
    status, body = handler.sent[-1]
    assert status == 200
    assert body["exists"] is True
    assert body["taxonomy"]["subtopics"]["laboral"][0]["key"] == "aportes_parafiscales"


# ---------------------------------------------------------------------------
# (i) GET /evidence returns rows from collection JSONL
# ---------------------------------------------------------------------------


def test_evidence_returns_collection_rows(tmp_path: Path) -> None:
    _write_proposals(
        tmp_path,
        {
            "laboral": [
                {
                    "proposal_id": "laboral::001",
                    "proposed_key": "x",
                    "proposed_label": "X",
                    "candidate_labels": ["x"],
                    "evidence_doc_ids": ["sha256:aaa", "sha256:bbb"],
                    "evidence_count": 2,
                    "intra_similarity_min": 0.9,
                    "intra_similarity_max": 0.95,
                }
            ]
        },
    )
    _write_collection(
        tmp_path,
        [
            {
                "doc_id": "sha256:aaa",
                "filename": "doc_a.md",
                "corpus_relative_path": "laboral/doc_a.md",
                "autogenerar_label": "label a",
                "autogenerar_rationale": "rationale a",
                "parent_topic": "laboral",
            },
            {
                "doc_id": "sha256:bbb",
                "filename": "doc_b.md",
                "corpus_relative_path": "laboral/doc_b.md",
                "autogenerar_label": "label b",
                "autogenerar_rationale": "rationale b",
                "parent_topic": "laboral",
            },
            {
                "doc_id": "sha256:ccc",
                "filename": "doc_c.md",
                "corpus_relative_path": "laboral/doc_c.md",
                "autogenerar_label": "label c",
                "autogenerar_rationale": "rationale c",
                "parent_topic": "laboral",
            },
        ],
    )

    handler = _FakeHandler()
    parsed = urlparse("/api/subtopics/evidence?proposal_id=laboral::001")
    ctrl.handle_subtopic_get(
        handler,
        "/api/subtopics/evidence",
        parsed,
        deps={"workspace_root": tmp_path},
    )
    status, body = handler.sent[-1]
    assert status == 200
    doc_ids = {row["doc_id"] for row in body["evidence"]}
    assert doc_ids == {"sha256:aaa", "sha256:bbb"}


# ---------------------------------------------------------------------------
# (j) trace events fire in expected order
# ---------------------------------------------------------------------------


def test_trace_events_on_decision_flow(
    tmp_path: Path,
    _silence_trace: list[tuple[str, dict[str, Any]]],
) -> None:
    _write_proposals(
        tmp_path,
        {
            "laboral": [
                {
                    "proposal_id": "laboral::001",
                    "proposed_key": "x",
                    "proposed_label": "X",
                    "candidate_labels": ["x"],
                    "evidence_doc_ids": [],
                    "evidence_count": 1,
                    "intra_similarity_min": 1.0,
                    "intra_similarity_max": 1.0,
                }
            ]
        },
    )
    # 1. list proposals
    handler1 = _FakeHandler()
    parsed1 = urlparse("/api/subtopics/proposals")
    ctrl.handle_subtopic_get(
        handler1,
        "/api/subtopics/proposals",
        parsed1,
        deps={"workspace_root": tmp_path},
    )
    # 2. accept one
    handler2 = _FakeHandler(
        payload={
            "proposal_id": "laboral::001",
            "action": "accept",
            "final_key": "x",
            "final_label": "X",
        }
    )
    ctrl.handle_subtopic_post(
        handler2, "/api/subtopics/decision", deps={"workspace_root": tmp_path}
    )
    # 3. bad payload
    handler3 = _FakeHandler(payload={"proposal_id": "", "action": "accept"})
    ctrl.handle_subtopic_post(
        handler3, "/api/subtopics/decision", deps={"workspace_root": tmp_path}
    )

    events = [e[0] for e in _silence_trace]
    assert "subtopic.curation.proposals.requested" in events
    assert "subtopic.curation.proposals.served" in events
    assert "subtopic.curation.decision.recorded" in events
    assert "subtopic.curation.decision.rejected_payload" in events


# ---------------------------------------------------------------------------
# Negative: unrelated URL returns False (keeps dispatch chain composable)
# ---------------------------------------------------------------------------


def test_get_dispatch_returns_false_for_unrelated_url(tmp_path: Path) -> None:
    handler = _FakeHandler()
    parsed = urlparse("/api/other/endpoint")
    matched = ctrl.handle_subtopic_get(
        handler, "/api/other/endpoint", parsed, deps={"workspace_root": tmp_path}
    )
    assert matched is False
    assert handler.sent == []


def test_post_dispatch_returns_false_for_unrelated_url(tmp_path: Path) -> None:
    handler = _FakeHandler(payload={"proposal_id": "x", "action": "accept"})
    matched = ctrl.handle_subtopic_post(
        handler, "/api/other/endpoint", deps={"workspace_root": tmp_path}
    )
    assert matched is False
    assert handler.sent == []
