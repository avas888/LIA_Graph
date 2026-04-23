"""Pure delta planner for additive-corpus-v1 (Phase 3).

See ``docs/next/additive_corpusv1.md`` §5 Phase 3.

Consumes ``(on_disk_docs, baseline_snapshot)`` and emits a
``CorpusDelta`` bucketing every doc into added / modified / removed /
unchanged. No I/O, no side effects: same inputs produce the same output.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

from .baseline_snapshot import BaselineDocument, BaselineSnapshot
from .fingerprint import compute_doc_fingerprint


@dataclass(frozen=True)
class DiskDocument:
    """A document as observed on disk + classified for this ingest.

    Callers supply the same fields the sink consumes during a full rebuild
    (``content_hash`` + classifier output shape, from Decision C1). Not every
    attribute of a ``CorpusDocument`` is needed here — just enough to build
    the fingerprint and locate the doc by relative_path.
    """

    relative_path: str
    content_hash: str
    classifier_output: Mapping[str, object] = field(default_factory=dict)
    source_path: str | None = None
    doc_id_hint: str | None = None

    @property
    def fingerprint(self) -> str:
        return compute_doc_fingerprint(
            content_hash=self.content_hash,
            classifier_output=self.classifier_output,
        )


@dataclass(frozen=True)
class DeltaEntry:
    """A single classified doc inside a ``CorpusDelta`` bucket."""

    relative_path: str
    disk: DiskDocument | None
    baseline: BaselineDocument | None

    @property
    def doc_id(self) -> str | None:
        if self.baseline is not None:
            return self.baseline.doc_id
        if self.disk is not None and self.disk.doc_id_hint:
            return self.disk.doc_id_hint
        return None


@dataclass(frozen=True)
class CorpusDelta:
    """Bucketed outcome of ``plan_delta``."""

    delta_id: str
    baseline_generation_id: str
    added: tuple[DeltaEntry, ...]
    modified: tuple[DeltaEntry, ...]
    removed: tuple[DeltaEntry, ...]
    unchanged: tuple[DeltaEntry, ...]

    @property
    def is_empty(self) -> bool:
        return not self.added and not self.modified and not self.removed

    @property
    def touched_relative_paths(self) -> tuple[str, ...]:
        """added + modified + removed, in a stable order."""
        out: list[str] = []
        for bucket in (self.added, self.modified, self.removed):
            for entry in bucket:
                out.append(entry.relative_path)
        return tuple(out)


def _default_delta_id(baseline_generation_id: str) -> str:
    """Generate a time-ordered delta_id that is unique to the second."""
    stamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    suffix = hashlib.sha1(
        f"{baseline_generation_id}|{stamp}|{time.time()}".encode("utf-8"),
        usedforsecurity=False,
    ).hexdigest()[:6]
    return f"delta_{stamp}_{suffix}"


def plan_delta(
    disk_docs: Iterable[DiskDocument],
    baseline: BaselineSnapshot,
    *,
    delta_id: str | None = None,
    prematched_relative_paths: set[str] | None = None,
) -> CorpusDelta:
    """Classify each doc in (disk ∪ baseline) into exactly one bucket.

    Rules:
    * a doc present only on disk → ``added``.
    * a doc present only in baseline → ``removed`` (soft-retire per B1).
    * a doc present in both with matching fingerprint → ``unchanged``.
    * a doc present in both with different fingerprint → ``modified``.
    * a baseline doc that is already retired but re-appears on disk →
      ``added`` (retirement gets cleared by the write path; the delta
      planner simply sees the doc as "back"). Same fingerprint semantics
      as a new arrival.

    Every path in ``(disk ∪ baseline)`` appears in exactly one bucket.

    ``prematched_relative_paths`` (optional): fast path for the content-hash
    shortcut in ``delta_runtime``. When a disk doc's path is in this set,
    the planner forces it into the ``unchanged`` bucket without computing
    or comparing fingerprints — the caller has already proven (via
    ``sha256(markdown_bytes) == baseline.content_hash``) that the file is
    byte-identical to the baseline, so classifying it would be wasted work.
    Retired-reintroduction and legacy-null-fingerprint rules are NOT
    bypassed — prematched paths whose baseline row is retired still route
    to ``added`` so the write path re-upserts.
    """
    prematched = prematched_relative_paths or set()
    resolved_delta_id = str(
        delta_id or _default_delta_id(baseline.generation_id)
    ).strip()

    disk_by_path: dict[str, DiskDocument] = {}
    for doc in disk_docs:
        path = str(doc.relative_path or "").strip()
        if not path:
            continue
        # Stable last-wins for duplicates — shouldn't happen, but be explicit.
        disk_by_path[path] = doc

    added: list[DeltaEntry] = []
    modified: list[DeltaEntry] = []
    removed: list[DeltaEntry] = []
    unchanged: list[DeltaEntry] = []

    baseline_paths = set(baseline.documents_by_relative_path.keys())
    disk_paths = set(disk_by_path.keys())

    # Added: on disk, not in baseline — OR in baseline but retired_at set.
    for path in disk_paths - baseline_paths:
        added.append(DeltaEntry(
            relative_path=path,
            disk=disk_by_path[path],
            baseline=None,
        ))

    # Intersection: existed before. Dispatch by retired_at + fingerprint.
    for path in disk_paths & baseline_paths:
        disk_doc = disk_by_path[path]
        base_doc = baseline.documents_by_relative_path[path]
        if base_doc.retired_at:
            # Re-introduction: treat like added. Fingerprint comparison is
            # irrelevant because the write path must clear retired_at and
            # re-upsert chunks/edges in full.
            added.append(DeltaEntry(path, disk_doc, base_doc))
            continue
        # Fast path: caller already proved byte-identical content to the
        # baseline (content_hash match). Skip classifier + fingerprint
        # comparison, bucket as unchanged. Legacy rows with no fingerprint
        # are still routed through the classifier path below — the
        # shortcut only fires when both content_hash AND doc_fingerprint
        # are present in baseline, and the caller keeps that invariant.
        if path in prematched and base_doc.doc_fingerprint:
            unchanged.append(DeltaEntry(path, disk_doc, base_doc))
            continue
        # Legacy rows with no fingerprint on file: force through the modified
        # path so the next run persists a fingerprint + rewrites chunks. A
        # legacy row with a matching content_hash wouldn't hit ``modified``
        # in a fingerprint-to-fingerprint comparison but we can't be sure the
        # classifier output hasn't drifted either — safer to treat as dirty.
        if not base_doc.doc_fingerprint:
            modified.append(DeltaEntry(path, disk_doc, base_doc))
            continue
        if disk_doc.fingerprint == base_doc.doc_fingerprint:
            unchanged.append(DeltaEntry(path, disk_doc, base_doc))
        else:
            modified.append(DeltaEntry(path, disk_doc, base_doc))

    # Removed: in baseline, not on disk. Excludes already-retired docs (they
    # are not "newly removed" by this delta; they were removed in an earlier
    # one). An already-retired doc that stays off disk is a no-op.
    for path in baseline_paths - disk_paths:
        base_doc = baseline.documents_by_relative_path[path]
        if base_doc.retired_at:
            continue
        removed.append(DeltaEntry(
            relative_path=path,
            disk=None,
            baseline=base_doc,
        ))

    return CorpusDelta(
        delta_id=resolved_delta_id,
        baseline_generation_id=baseline.generation_id,
        added=tuple(sorted(added, key=lambda e: e.relative_path)),
        modified=tuple(sorted(modified, key=lambda e: e.relative_path)),
        removed=tuple(sorted(removed, key=lambda e: e.relative_path)),
        unchanged=tuple(sorted(unchanged, key=lambda e: e.relative_path)),
    )


def summarize_delta(delta: CorpusDelta) -> dict[str, object]:
    """Return a JSON-friendly summary suitable for trace/report payloads."""
    return {
        "delta_id": delta.delta_id,
        "baseline_generation_id": delta.baseline_generation_id,
        "added": len(delta.added),
        "modified": len(delta.modified),
        "removed": len(delta.removed),
        "unchanged": len(delta.unchanged),
        "touched_total": len(delta.added) + len(delta.modified) + len(delta.removed),
        "is_empty": delta.is_empty,
    }


__all__ = [
    "CorpusDelta",
    "DeltaEntry",
    "DiskDocument",
    "plan_delta",
    "summarize_delta",
]
