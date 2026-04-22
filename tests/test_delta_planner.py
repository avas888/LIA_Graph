"""Tests for the pure delta planner (Phase 3)."""

from __future__ import annotations

from typing import Any

from lia_graph.ingestion.baseline_snapshot import (
    BaselineDocument,
    BaselineSnapshot,
    DEFAULT_GENERATION_ID,
)
from lia_graph.ingestion.delta_planner import (
    CorpusDelta,
    DeltaEntry,
    DiskDocument,
    plan_delta,
    summarize_delta,
)


def _baseline(docs: list[BaselineDocument]) -> BaselineSnapshot:
    return BaselineSnapshot(
        generation_id=DEFAULT_GENERATION_ID,
        documents_by_relative_path={d.relative_path: d for d in docs},
        total_docs=len(docs),
        total_chunks=0,
        total_edges=0,
        retired_docs=sum(1 for d in docs if d.retired_at),
    )


def _baseline_doc(
    *,
    relative_path: str,
    doc_id: str | None = None,
    fingerprint: str | None = "fp1",
    retired_at: str | None = None,
) -> BaselineDocument:
    return BaselineDocument(
        doc_id=doc_id or relative_path.replace("/", "_"),
        relative_path=relative_path,
        content_hash="stored_hash",
        doc_fingerprint=fingerprint,
        retired_at=retired_at,
        last_delta_id=None,
        sync_generation=DEFAULT_GENERATION_ID,
    )


def _disk_doc(relative_path: str, classifier_output: dict[str, Any] | None = None, content_hash: str = "h") -> DiskDocument:
    return DiskDocument(
        relative_path=relative_path,
        content_hash=content_hash,
        classifier_output=classifier_output or {"topic_key": "iva"},
    )


# (a) both empty → empty delta.
def test_plan_delta_both_empty_is_empty_delta() -> None:
    delta = plan_delta(disk_docs=[], baseline=_baseline([]))
    assert delta.is_empty is True
    assert delta.added == delta.modified == delta.removed == ()
    assert delta.unchanged == ()
    assert delta.baseline_generation_id == DEFAULT_GENERATION_ID


# (b) 3 on disk, 0 in baseline → all added.
def test_plan_delta_three_disk_zero_baseline_all_added() -> None:
    disk = [_disk_doc(f"a/{i}.md") for i in range(3)]
    delta = plan_delta(disk_docs=disk, baseline=_baseline([]))
    assert len(delta.added) == 3
    assert delta.modified == ()
    assert delta.removed == ()
    assert delta.unchanged == ()


# (c) 0 on disk, 3 in baseline → all removed.
def test_plan_delta_zero_disk_three_baseline_all_removed() -> None:
    baseline_docs = [_baseline_doc(relative_path=f"a/{i}.md") for i in range(3)]
    delta = plan_delta(disk_docs=[], baseline=_baseline(baseline_docs))
    assert delta.added == ()
    assert delta.modified == ()
    assert len(delta.removed) == 3
    assert delta.unchanged == ()


# (d) 3 identical (same fingerprint) → all unchanged.
def test_plan_delta_identical_fingerprints_all_unchanged() -> None:
    disk = [_disk_doc(f"a/{i}.md") for i in range(3)]
    # Pre-compute each fingerprint so the baseline matches byte-for-byte.
    baseline_docs = [
        _baseline_doc(relative_path=doc.relative_path, fingerprint=doc.fingerprint)
        for doc in disk
    ]
    delta = plan_delta(disk_docs=disk, baseline=_baseline(baseline_docs))
    assert len(delta.unchanged) == 3
    assert delta.added == delta.modified == delta.removed == ()


# (e) 1 on disk with different fingerprint → 1 modified.
def test_plan_delta_fingerprint_drift_is_modified() -> None:
    disk = [_disk_doc("a/x.md")]
    baseline_docs = [
        _baseline_doc(relative_path="a/x.md", fingerprint="differs_from_disk")
    ]
    delta = plan_delta(disk_docs=disk, baseline=_baseline(baseline_docs))
    assert len(delta.modified) == 1
    assert delta.modified[0].relative_path == "a/x.md"
    assert delta.added == delta.removed == delta.unchanged == ()


# (f) mixed delta.
def test_plan_delta_mixed_buckets() -> None:
    disk_kept_same = _disk_doc("kept/a.md")
    disk_kept_same2 = _disk_doc("kept/b.md")
    disk_modified = _disk_doc("modified/a.md")
    disk_new = _disk_doc("new/a.md")
    baseline_docs = [
        _baseline_doc(relative_path="kept/a.md", fingerprint=disk_kept_same.fingerprint),
        _baseline_doc(relative_path="kept/b.md", fingerprint=disk_kept_same2.fingerprint),
        _baseline_doc(relative_path="modified/a.md", fingerprint="stale_fingerprint"),
        _baseline_doc(relative_path="gone/a.md"),
    ]
    delta = plan_delta(
        disk_docs=[disk_kept_same, disk_kept_same2, disk_modified, disk_new],
        baseline=_baseline(baseline_docs),
    )
    assert {e.relative_path for e in delta.added} == {"new/a.md"}
    assert {e.relative_path for e in delta.modified} == {"modified/a.md"}
    assert {e.relative_path for e in delta.removed} == {"gone/a.md"}
    assert {e.relative_path for e in delta.unchanged} == {"kept/a.md", "kept/b.md"}


# (g) retired baseline re-appearing same fingerprint → added.
def test_plan_delta_retired_reintroduction_same_fingerprint_is_added() -> None:
    disk = [_disk_doc("a/was_retired.md")]
    baseline_docs = [
        _baseline_doc(
            relative_path="a/was_retired.md",
            fingerprint=disk[0].fingerprint,
            retired_at="2026-04-20T10:00:00+00:00",
        )
    ]
    delta = plan_delta(disk_docs=disk, baseline=_baseline(baseline_docs))
    assert len(delta.added) == 1
    assert delta.added[0].baseline is not None
    assert delta.added[0].baseline.retired_at is not None
    assert delta.modified == delta.removed == delta.unchanged == ()


# (h) retired baseline re-appearing different fingerprint → added.
def test_plan_delta_retired_reintroduction_different_fingerprint_is_added() -> None:
    disk = [_disk_doc("a/was_retired.md")]
    baseline_docs = [
        _baseline_doc(
            relative_path="a/was_retired.md",
            fingerprint="stale_fingerprint",
            retired_at="2026-04-20T10:00:00+00:00",
        )
    ]
    delta = plan_delta(disk_docs=disk, baseline=_baseline(baseline_docs))
    assert len(delta.added) == 1
    assert delta.modified == delta.removed == delta.unchanged == ()


# (i) delta_id auto-generated when None, deterministic when supplied.
def test_plan_delta_delta_id_is_used_when_supplied() -> None:
    delta_auto = plan_delta(disk_docs=[], baseline=_baseline([]))
    assert delta_auto.delta_id.startswith("delta_")
    delta_fixed = plan_delta(
        disk_docs=[],
        baseline=_baseline([]),
        delta_id="delta_fixture_001",
    )
    assert delta_fixed.delta_id == "delta_fixture_001"


# (j) delta planning is pure — same inputs produce the same output.
def test_plan_delta_is_pure() -> None:
    disk = [_disk_doc("a/x.md"), _disk_doc("b/y.md")]
    baseline = _baseline([
        _baseline_doc(relative_path="a/x.md", fingerprint="stale"),
        _baseline_doc(relative_path="gone.md"),
    ])
    delta1 = plan_delta(disk_docs=disk, baseline=baseline, delta_id="delta_X")
    delta2 = plan_delta(disk_docs=disk, baseline=baseline, delta_id="delta_X")
    assert summarize_delta(delta1) == summarize_delta(delta2)
    assert [e.relative_path for e in delta1.modified] == [e.relative_path for e in delta2.modified]
    assert [e.relative_path for e in delta1.removed] == [e.relative_path for e in delta2.removed]


# (k) summarize_delta returns counts + delta_id + baseline_generation_id.
def test_summarize_delta_shape() -> None:
    disk = [_disk_doc("a/x.md")]
    baseline = _baseline([_baseline_doc(relative_path="gone.md")])
    delta = plan_delta(disk_docs=disk, baseline=baseline, delta_id="delta_fixture")
    summary = summarize_delta(delta)
    assert summary["delta_id"] == "delta_fixture"
    assert summary["baseline_generation_id"] == DEFAULT_GENERATION_ID
    assert summary["added"] == 1
    assert summary["removed"] == 1
    assert summary["modified"] == 0
    assert summary["unchanged"] == 0
    assert summary["touched_total"] == 2
    assert summary["is_empty"] is False


# (l) SUIN-style re-import fixture — docs owned by a SUIN scope classify
# correctly. SUIN docs look identical to any other doc as far as the planner
# is concerned; re-import that changes the SUIN-sourced content_hash produces
# a modified bucket as expected.
def test_plan_delta_suin_reimport_classifies_correctly() -> None:
    # Simulated SUIN fixture: three docs, two were re-fetched from SUIN with
    # fresh content, one was a stub already in baseline with matching hash.
    suin_stub = _disk_doc(
        "suin/stub.md", classifier_output={"topic_key": "suin"}
    )
    suin_refresh_a = _disk_doc(
        "suin/ruling_a.md", classifier_output={"topic_key": "suin"}, content_hash="new_hash_a"
    )
    suin_refresh_b = _disk_doc(
        "suin/ruling_b.md", classifier_output={"topic_key": "suin"}, content_hash="new_hash_b"
    )
    baseline = _baseline([
        _baseline_doc(relative_path="suin/stub.md", fingerprint=suin_stub.fingerprint),
        _baseline_doc(
            relative_path="suin/ruling_a.md",
            fingerprint="stale_ruling_a_fingerprint",
        ),
        _baseline_doc(
            relative_path="suin/ruling_b.md",
            fingerprint="stale_ruling_b_fingerprint",
        ),
    ])
    delta = plan_delta(
        disk_docs=[suin_stub, suin_refresh_a, suin_refresh_b],
        baseline=baseline,
    )
    assert {e.relative_path for e in delta.unchanged} == {"suin/stub.md"}
    assert {e.relative_path for e in delta.modified} == {"suin/ruling_a.md", "suin/ruling_b.md"}
    assert delta.added == delta.removed == ()


# Extra: legacy baseline rows missing a fingerprint flow through modified.
def test_plan_delta_legacy_missing_fingerprint_is_modified() -> None:
    disk = [_disk_doc("legacy.md")]
    baseline = _baseline([
        _baseline_doc(relative_path="legacy.md", fingerprint=None),
    ])
    delta = plan_delta(disk_docs=disk, baseline=baseline)
    assert {e.relative_path for e in delta.modified} == {"legacy.md"}
    assert delta.added == delta.removed == delta.unchanged == ()


# Extra: retired doc that stays off disk is NOT removed again.
def test_plan_delta_already_retired_stays_off_disk_is_noop() -> None:
    baseline = _baseline([
        _baseline_doc(
            relative_path="retired/a.md",
            retired_at="2026-04-10T00:00:00+00:00",
        )
    ])
    delta = plan_delta(disk_docs=[], baseline=baseline)
    assert delta.added == delta.modified == delta.removed == delta.unchanged == ()


# Extra: empty relative_path on disk is ignored.
def test_plan_delta_ignores_disk_doc_with_empty_path() -> None:
    disk = [DiskDocument(relative_path="", content_hash="h")]
    delta = plan_delta(disk_docs=disk, baseline=_baseline([]))
    assert delta.added == delta.modified == delta.removed == delta.unchanged == ()
