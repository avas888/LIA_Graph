"""Phase 7 smoke test — end-to-end trace audit for subtopic_generationv1.

Runs a small fixture through collect → mine → curate → promote and asserts
every `event_type` documented in §13 of `docs/next/subtopic_generationv1.md`
fires at least once in the captured events log.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace

import pytest

from lia_graph import ingestion_classifier as classifier_module
from lia_graph import subtopic_miner
from lia_graph import subtopic_taxonomy_builder
from lia_graph import ui_subtopic_controllers as ctrl


def _load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


REPO_ROOT = Path(__file__).resolve().parent.parent
COLLECT_SCRIPT = _load_script(
    "collect_subtopic_candidates_probe",
    REPO_ROOT / "scripts" / "collect_subtopic_candidates.py",
)
MINE_SCRIPT = _load_script(
    "mine_subtopic_candidates_probe",
    REPO_ROOT / "scripts" / "mine_subtopic_candidates.py",
)
PROMOTE_SCRIPT = _load_script(
    "promote_subtopic_decisions_probe",
    REPO_ROOT / "scripts" / "promote_subtopic_decisions.py",
)


# All event types the §13 schema documents.
DOCUMENTED_EVENTS = {
    "subtopic.collect.start",
    "subtopic.collect.doc.processed",
    "subtopic.collect.done",
    "subtopic.mine.start",
    "subtopic.mine.cluster.formed",
    "subtopic.mine.done",
    "subtopic.curation.proposals.requested",
    "subtopic.curation.proposals.served",
    "subtopic.curation.evidence.requested",
    "subtopic.curation.decision.recorded",
    "subtopic.promote.start",
    "subtopic.promote.done",
    # `merge_resolved` is covered by a dedicated case below — it only fires
    # when a decision with action="merge" exists in the ledger.
}


class _EventSink:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def record(self, event: str, payload: dict) -> None:
        self.events.append((event, dict(payload)))

    def types(self) -> set[str]:
        return {e for e, _ in self.events}


@pytest.fixture
def event_sink(monkeypatch: pytest.MonkeyPatch) -> _EventSink:
    sink = _EventSink()
    # Patch emit_event in every module that emits.
    import lia_graph.instrumentation as instrumentation

    monkeypatch.setattr(instrumentation, "emit_event", sink.record)
    # Each script imports emit_event at the top of its module scope; rebind
    # the local reference so tracing stays captured.
    for module in (COLLECT_SCRIPT, MINE_SCRIPT, PROMOTE_SCRIPT):
        if hasattr(module, "emit_event"):
            monkeypatch.setattr(module, "emit_event", sink.record)
    monkeypatch.setattr(ctrl, "_trace", lambda e, p: sink.record(e, p))
    monkeypatch.setattr(subtopic_taxonomy_builder, "emit_event", sink.record)
    return sink


def _stub_classifier(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the classifier call in the collection script with a stub
    that returns a minimal AutogenerarResult shape so we don't need an LLM."""
    def _fake(*, filename: str, body_text: str, **_kwargs):
        return SimpleNamespace(
            generated_label=f"label_{Path(filename).stem}",
            rationale="fixture rationale",
            resolved_to_existing=None,
            synonym_confidence=0.0,
            is_new_topic=False,
            suggested_key=None,
            detected_type="normative_base",
            detected_topic=None,
            topic_confidence=0.95,
            type_confidence=0.95,
            combined_confidence=0.95,
            classification_source="filename",
            is_raw=False,
            requires_review=False,
        )

    monkeypatch.setattr(COLLECT_SCRIPT, "classify_ingestion_document", _fake)
    # Also block real resolution in case a deeper path is reached.
    monkeypatch.setattr(
        classifier_module, "_resolve_adapter", lambda adapter: None
    )


def _fake_embed(texts: list[str]) -> list[list[float] | None]:
    """Orthogonal one-hot per distinct input so similar labels cluster."""
    seen: dict[str, int] = {}
    for t in texts:
        seen.setdefault(t, len(seen))
    dim = len(seen)
    out: list[list[float] | None] = []
    for t in texts:
        vec = [0.0] * dim
        vec[seen[t]] = 1.0
        out.append(vec)
    return out


class _AuthContext:
    def __init__(self, role: str = "platform_admin", email: str = "admin@lia.dev") -> None:
        self.role = role
        self.user_id = email
        self.email = email
        self.tenant_id = "tenant-test"


class _FakeHandler:
    def __init__(self, payload: dict | None = None) -> None:
        self._auth = _AuthContext()
        self._payload = payload
        self.sent: list[tuple[int, dict]] = []

    def _resolve_auth_context(self, *, required: bool = False):  # noqa: ARG002
        return self._auth

    def _send_auth_error(self, exc) -> None:
        self.sent.append((getattr(exc, "http_status", 401), {"error": str(exc)}))

    def _read_json_payload(self, **_kwargs):
        return self._payload

    def _send_json(self, status: int, body: dict, **_kwargs) -> None:
        self.sent.append((int(status), body))


def test_end_to_end_trace_trail_fires_every_documented_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    event_sink: _EventSink,
) -> None:
    """Canonical smoke test — five docs across two parent topics, curate
    one proposal, promote the taxonomy. Assert every §13 event fires."""
    # 1. Stage a fake corpus with 3 laboral docs + 2 iva docs.
    kb = tmp_path / "knowledge_base"
    (kb / "laboral").mkdir(parents=True)
    (kb / "iva").mkdir(parents=True)
    for idx in range(3):
        (kb / "laboral" / f"doc_{idx}.md").write_text(
            f"# Laboral {idx}\n\ntexto laboral {idx}", encoding="utf-8"
        )
    for idx in range(2):
        (kb / "iva" / f"doc_{idx}.md").write_text(
            f"# IVA {idx}\n\ntexto iva {idx}", encoding="utf-8"
        )

    artifacts = tmp_path / "artifacts"

    # 2. Run collect with stubbed classifier + --skip-llm so rate limiter is neutral.
    _stub_classifier(monkeypatch)
    batch_id = "collection_probe20260421T000000Z"
    exit_code = COLLECT_SCRIPT.main(
        [
            "--commit",
            "--knowledge-base",
            str(kb),
            "--artifacts-dir",
            str(artifacts),
            "--batch-id",
            batch_id,
            "--skip-llm",
            "--rate-limit-rpm",
            "6000",  # effectively no sleep
        ]
    )
    assert exit_code == 0
    collection_path = artifacts / "subtopic_candidates" / f"{batch_id}.jsonl"
    assert collection_path.exists()
    assert sum(1 for line in collection_path.read_text().splitlines() if line) == 5

    # 3. Run mine with --skip-embed so each distinct label becomes its own
    #    cluster; min_cluster_size=1 so singletons become proposals too.
    mine_output = artifacts / "subtopic_proposals_probe.json"
    mine_exit = MINE_SCRIPT.main(
        [
            "--input",
            str(collection_path),
            "--output",
            str(mine_output),
            "--min-cluster-size",
            "1",
            "--skip-embed",
        ]
    )
    assert mine_exit == 0
    assert mine_output.exists()
    proposals = json.loads(mine_output.read_text())
    assert proposals["proposals"], "mining must produce at least one proposal"

    # 4. Exercise the curation backend: list, evidence, decision.
    # Rename the proposals file to the canonical discover-latest pattern.
    canonical = artifacts / "subtopic_proposals_20260421T000000Z.json"
    mine_output.rename(canonical)

    # Fake workspace root points at tmp_path so the controller finds our artifacts.
    workspace = tmp_path

    # GET /proposals
    from urllib.parse import urlparse
    ctrl.handle_subtopic_get(
        _FakeHandler(),
        "/api/subtopics/proposals",
        urlparse("/api/subtopics/proposals"),
        deps={"workspace_root": workspace},
    )

    # Pick the first proposal id to exercise evidence + decision.
    first_parent = next(iter(proposals["proposals"]))
    first_proposal = proposals["proposals"][first_parent][0]
    first_pid = first_proposal["proposal_id"]

    # GET /evidence
    ctrl.handle_subtopic_get(
        _FakeHandler(),
        "/api/subtopics/evidence",
        urlparse(f"/api/subtopics/evidence?proposal_id={first_pid}"),
        deps={"workspace_root": workspace},
    )

    # POST /decision — accept one so we have an accept row for promotion.
    accept_handler = _FakeHandler(
        payload={
            "proposal_id": first_pid,
            "action": "accept",
            "final_key": first_proposal["proposed_key"],
            "final_label": first_proposal["proposed_label"],
        }
    )
    ctrl.handle_subtopic_post(
        accept_handler,
        "/api/subtopics/decision",
        deps={"workspace_root": workspace},
    )
    assert accept_handler.sent[-1][0] == HTTPStatus.OK

    decisions_path = workspace / "artifacts" / "subtopic_decisions.jsonl"
    assert decisions_path.exists()

    # 5. Promote
    taxonomy_path = workspace / "config" / "subtopic_taxonomy.json"
    promote_exit = PROMOTE_SCRIPT.main(
        [
            "--decisions",
            str(decisions_path),
            "--output",
            str(taxonomy_path),
            "--version",
            "2026-04-21-v1",
        ]
    )
    assert promote_exit == 0
    assert taxonomy_path.exists()

    # 6. Assert every documented event type fired.
    fired = event_sink.types()
    missing = DOCUMENTED_EVENTS - fired
    assert not missing, (
        f"Events documented in §13 but never fired in the canonical flow: {missing}"
    )


def test_merge_resolved_fires_on_merge_chain(
    tmp_path: Path,
    event_sink: _EventSink,
) -> None:
    """Focused case: a merge decision triggers `subtopic.promote.merge_resolved`."""
    decisions_path = tmp_path / "decisions.jsonl"
    decisions_path.write_text(
        "\n".join(
            [
                json.dumps({
                    "ts": "2026-04-21T14:50:00Z",
                    "curator": "admin@lia.dev",
                    "parent_topic": "laboral",
                    "proposal_id": "laboral::001",
                    "action": "merge",
                    "final_key": None,
                    "final_label": None,
                    "aliases": [],
                    "merged_into": "laboral::002",
                    "reason": None,
                    "evidence_count": 2,
                }),
                json.dumps({
                    "ts": "2026-04-21T14:51:00Z",
                    "curator": "admin@lia.dev",
                    "parent_topic": "laboral",
                    "proposal_id": "laboral::002",
                    "action": "accept",
                    "final_key": "target_key",
                    "final_label": "Target",
                    "aliases": [],
                    "merged_into": None,
                    "reason": None,
                    "evidence_count": 3,
                }),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    output_path = tmp_path / "taxonomy.json"
    exit_code = PROMOTE_SCRIPT.main(
        [
            "--decisions",
            str(decisions_path),
            "--output",
            str(output_path),
            "--version",
            "2026-04-21-v1",
        ]
    )
    assert exit_code == 0
    assert "subtopic.promote.merge_resolved" in event_sink.types()


def test_decision_rejected_payload_fires(
    tmp_path: Path,
    event_sink: _EventSink,
) -> None:
    """Bad payload triggers `subtopic.curation.decision.rejected_payload`."""
    # Seed a proposals file so the controller can resolve proposal_id index.
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "subtopic_proposals_probe.json").write_text(
        json.dumps(
            {
                "version": "x",
                "generated_at": "2026-04-21T00:00:00Z",
                "source_collection_paths": [],
                "cluster_threshold": 0.78,
                "min_cluster_size": 3,
                "proposals": {},
                "singletons": {},
                "summary": {
                    "total_proposals": 0,
                    "total_singletons": 0,
                    "parent_topics_with_proposals": 0,
                },
            }
        ),
        encoding="utf-8",
    )

    handler = _FakeHandler(payload={"proposal_id": "", "action": "accept"})
    ctrl.handle_subtopic_post(
        handler, "/api/subtopics/decision", deps={"workspace_root": tmp_path}
    )
    assert handler.sent[-1][0] == HTTPStatus.BAD_REQUEST
    assert "subtopic.curation.decision.rejected_payload" in event_sink.types()


def test_collect_doc_failed_fires_on_read_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    event_sink: _EventSink,
) -> None:
    """Classifier failure on a single doc → `subtopic.collect.doc.failed`."""
    kb = tmp_path / "knowledge_base"
    (kb / "laboral").mkdir(parents=True)
    (kb / "laboral" / "doc_0.md").write_text("# x", encoding="utf-8")

    def _boom(**_kwargs):
        raise RuntimeError("classifier exploded")

    monkeypatch.setattr(COLLECT_SCRIPT, "classify_ingestion_document", _boom)
    monkeypatch.setattr(
        classifier_module, "_resolve_adapter", lambda adapter: None
    )

    artifacts = tmp_path / "artifacts"
    COLLECT_SCRIPT.main(
        [
            "--commit",
            "--knowledge-base",
            str(kb),
            "--artifacts-dir",
            str(artifacts),
            "--skip-llm",
            "--rate-limit-rpm",
            "6000",
        ]
    )
    assert "subtopic.collect.doc.failed" in event_sink.types()


def test_all_fired_events_are_documented_in_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    event_sink: _EventSink,
) -> None:
    """Strict the other direction — every event we see fire must appear
    in the §13 table (whitelist including the conditional merge_resolved)."""
    allowlist = DOCUMENTED_EVENTS | {
        "subtopic.promote.merge_resolved",
        "subtopic.curation.decision.rejected_payload",
        "subtopic.collect.doc.failed",
    }

    # Re-run the canonical flow quickly.
    kb = tmp_path / "knowledge_base"
    (kb / "laboral").mkdir(parents=True)
    (kb / "laboral" / "doc_0.md").write_text("# x", encoding="utf-8")
    _stub_classifier(monkeypatch)
    artifacts = tmp_path / "artifacts"
    COLLECT_SCRIPT.main(
        [
            "--commit",
            "--knowledge-base",
            str(kb),
            "--artifacts-dir",
            str(artifacts),
            "--skip-llm",
            "--rate-limit-rpm",
            "6000",
        ]
    )
    fired = event_sink.types()
    subtopic_only = {e for e in fired if e.startswith("subtopic.")}
    unknown = subtopic_only - allowlist
    assert not unknown, f"Fired events not in §13 schema: {unknown}"
