"""Corpus audit reports + manifest builders.

Extracted from `ingest.py` during granularize-v2 round 14. Given a list
of `CorpusAuditRecord` / `CorpusDocument` rows, produces:

  * audit report (counts + priority rollups)
  * filtered audit payload
  * corpus inventory (active-by-family summary)
  * corpus reconnaissance report (gate + rows + next steps)
  * canonical corpus manifest (per-family blessing status)

Pure functions — no I/O, no global state. Host re-imports every name.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .ingest_constants import (
    CorpusAuditRecord,
    CorpusDocument,
    GRAPH_PARSE_STRATEGIES,
    GRAPH_TARGET_FAMILIES,
    INGESTION_DECISION_EXCLUDE,
    INGESTION_DECISION_INCLUDE,
    INGESTION_DECISION_REVISION,
    REVIEW_PRIORITY_ORDER,
)
from .ingest_classifiers import _relative_path
from .topic_taxonomy import iter_ingestion_topic_entries, topic_taxonomy_version



def _decision_counts(rows: Iterable[CorpusAuditRecord]) -> dict[str, int]:
    counter = Counter(row.ingestion_decision for row in rows)
    return {decision: counter[decision] for decision in sorted(counter)}


def _family_counts(documents: Iterable[CorpusDocument]) -> dict[str, int]:
    counter = Counter(document.family for document in documents)
    return {family: counter[family] for family in sorted(counter)}


def _extension_counts(rows: Iterable[CorpusAuditRecord]) -> dict[str, int]:
    counter = Counter(row.extension or "[no_ext]" for row in rows)
    return {key: counter[key] for key in sorted(counter)}


def _knowledge_class_counts(documents: Iterable[CorpusDocument]) -> dict[str, int]:
    counter = Counter(document.knowledge_class for document in documents)
    return {key: counter[key] for key in sorted(counter)}


def _source_type_counts(documents: Iterable[CorpusDocument]) -> dict[str, int]:
    counter = Counter(document.source_type for document in documents)
    return {key: counter[key] for key in sorted(counter)}


def _parse_strategy_counts(rows: Iterable[CorpusAuditRecord]) -> dict[str, int]:
    counter = Counter(row.parse_strategy for row in rows)
    return {key: counter[key] for key in sorted(counter)}


def _document_archetype_counts(rows: Iterable[CorpusAuditRecord]) -> dict[str, int]:
    counter = Counter(row.document_archetype for row in rows)
    return {key: counter[key] for key in sorted(counter)}


def _source_origin_counts(rows: Iterable[CorpusAuditRecord]) -> dict[str, int]:
    counter = Counter(row.source_origin for row in rows)
    return {origin: counter[origin] for origin in sorted(counter)}


def _source_tier_counts(rows: Iterable[CorpusAuditRecord]) -> dict[str, int]:
    counter = Counter((row.source_tier or "unknown") for row in rows)
    return {tier: counter[tier] for tier in sorted(counter)}


def _authority_level_counts(rows: Iterable[CorpusAuditRecord]) -> dict[str, int]:
    counter = Counter((row.authority_level or "unknown") for row in rows)
    return {level: counter[level] for level in sorted(counter)}


def _review_priority_counts(rows: Iterable[CorpusAuditRecord]) -> dict[str, int]:
    counter = Counter(row.review_priority for row in rows)
    return {priority: counter[priority] for priority in sorted(counter, key=_priority_sort_key)}


def _ambiguity_flag_counts(rows: Iterable[CorpusAuditRecord]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        counter.update(row.ambiguity_flags)
    return {flag: counter[flag] for flag in sorted(counter)}


def _vocabulary_status_counts(documents: Iterable[CorpusDocument]) -> dict[str, int]:
    counter = Counter(document.vocabulary_status for document in documents)
    return {key: counter[key] for key in sorted(counter)}


def _topic_key_counts(rows: Iterable[Any]) -> dict[str, int]:
    counter = Counter((getattr(row, "topic_key", None) or "[none]") for row in rows)
    return {key: counter[key] for key in sorted(counter)}


def _subtopic_key_counts(rows: Iterable[Any]) -> dict[str, int]:
    counter = Counter((getattr(row, "subtopic_key", None) or "[none]") for row in rows)
    return {key: counter[key] for key in sorted(counter)}


def _topic_subtopic_coverage(rows: Iterable[Any]) -> dict[str, Any]:
    coverage: dict[str, dict[str, Any]] = {}
    for row in rows:
        topic_key = getattr(row, "topic_key", None)
        if not topic_key:
            continue
        parent_bucket = coverage.setdefault(
            topic_key,
            {
                "direct_document_count": 0,
                "subtopic_document_count": 0,
                "subtopic_counts": {},
            },
        )
        subtopic_key = getattr(row, "subtopic_key", None)
        if subtopic_key:
            parent_bucket["subtopic_document_count"] += 1
            subtopic_counts = parent_bucket["subtopic_counts"]
            subtopic_counts[subtopic_key] = subtopic_counts.get(subtopic_key, 0) + 1
            continue
        parent_bucket["direct_document_count"] += 1

    return {
        topic_key: {
            "direct_document_count": bucket["direct_document_count"],
            "subtopic_document_count": bucket["subtopic_document_count"],
            "subtopic_counts": {
                subtopic_key: bucket["subtopic_counts"][subtopic_key]
                for subtopic_key in sorted(bucket["subtopic_counts"])
            },
        }
        for topic_key, bucket in sorted(coverage.items())
    }


def _build_corpus_audit_report(
    *,
    corpus_dir: Path,
    rows: Iterable[CorpusAuditRecord],
) -> dict[str, Any]:
    audit_rows = tuple(rows)
    return {
        "corpus_dir": str(corpus_dir),
        "taxonomy_version": topic_taxonomy_version(),
        "scanned_file_count": len(audit_rows),
        "decision_counts": _decision_counts(audit_rows),
        "source_origin_counts": _source_origin_counts(audit_rows),
        "extension_counts": _extension_counts(audit_rows),
        "parse_strategy_counts": _parse_strategy_counts(audit_rows),
        "document_archetype_counts": _document_archetype_counts(audit_rows),
        "source_tier_counts": _source_tier_counts(audit_rows),
        "authority_level_counts": _authority_level_counts(audit_rows),
        "review_priority_counts": _review_priority_counts(audit_rows),
        "ambiguity_flag_counts": _ambiguity_flag_counts(audit_rows),
        "topic_key_counts": _topic_key_counts(audit_rows),
        "subtopic_key_counts": _subtopic_key_counts(audit_rows),
        "topic_subtopic_coverage": _topic_subtopic_coverage(audit_rows),
        "rows": [row.to_dict() for row in audit_rows],
    }


def _build_filtered_audit_payload(
    *,
    corpus_dir: Path,
    rows: Iterable[CorpusAuditRecord],
    decision: str,
) -> dict[str, Any]:
    selected_rows = tuple(row for row in rows if row.ingestion_decision == decision)
    return {
        "corpus_dir": str(corpus_dir),
        "taxonomy_version": topic_taxonomy_version(),
        "decision": decision,
        "count": len(selected_rows),
        "topic_key_counts": _topic_key_counts(selected_rows),
        "subtopic_key_counts": _subtopic_key_counts(selected_rows),
        "topic_subtopic_coverage": _topic_subtopic_coverage(selected_rows),
        "rows": [row.to_dict() for row in selected_rows],
    }


def _build_corpus_inventory(
    *,
    corpus_dir: Path,
    documents: Iterable[CorpusDocument],
    rows: Iterable[CorpusAuditRecord],
) -> dict[str, Any]:
    included_rows = tuple(documents)
    audit_rows = tuple(rows)
    return {
        "corpus_dir": str(corpus_dir),
        "taxonomy_version": topic_taxonomy_version(),
        "scanned_file_count": len(audit_rows),
        "decision_counts": _decision_counts(audit_rows),
        "extension_counts": _extension_counts(audit_rows),
        "parse_strategy_counts": _parse_strategy_counts(audit_rows),
        "document_archetype_counts": _document_archetype_counts(audit_rows),
        "document_count": len(included_rows),
        "family_counts": _family_counts(included_rows),
        "knowledge_class_counts": _knowledge_class_counts(included_rows),
        "source_type_counts": _source_type_counts(included_rows),
        "source_tier_counts": _source_tier_counts(included_rows),
        "authority_level_counts": _authority_level_counts(included_rows),
        "graph_parse_ready_document_count": sum(1 for row in included_rows if row.graph_parse_ready),
        "vocabulary_status_counts": _vocabulary_status_counts(included_rows),
        "review_priority_counts": _review_priority_counts(included_rows),
        "ambiguity_flag_counts": _ambiguity_flag_counts(included_rows),
        "topic_key_counts": _topic_key_counts(included_rows),
        "subtopic_key_counts": _subtopic_key_counts(included_rows),
        "topic_subtopic_coverage": _topic_subtopic_coverage(included_rows),
        "graph_target_families": sorted(GRAPH_TARGET_FAMILIES),
        "graph_target_document_count": sum(1 for row in included_rows if row.graph_target),
        "documents": [row.to_dict() for row in included_rows],
    }


def _build_corpus_reconnaissance_report(
    *,
    corpus_dir: Path,
    documents: Iterable[CorpusDocument],
    rows: Iterable[CorpusAuditRecord],
) -> dict[str, Any]:
    audit_rows = tuple(rows)
    included_rows = tuple(documents)
    recon_rows = _build_reconnaissance_rows(documents=included_rows, rows=audit_rows)
    manual_review_queue = [
        row for row in recon_rows if row["needs_manual_review"] and row["ingestion_decision"] != INGESTION_DECISION_EXCLUDE
    ]
    blessing_counts = Counter(row["canonical_blessing_status"] for row in recon_rows)
    revision_linkage_counts = Counter(row["revision_linkage_status"] for row in recon_rows)
    review_priority_counts = Counter(row["review_priority"] for row in recon_rows)
    gate = _build_reconnaissance_gate(
        blessing_counts=blessing_counts,
        revision_linkage_counts=revision_linkage_counts,
        manual_review_count=len(manual_review_queue),
    )
    return {
        "corpus_dir": str(corpus_dir),
        "taxonomy_version": topic_taxonomy_version(),
        "quality_gate": gate,
        "scanned_file_count": len(audit_rows),
        "decision_counts": _decision_counts(audit_rows),
        "document_archetype_counts": _document_archetype_counts(audit_rows),
        "family_counts": _family_counts(included_rows),
        "source_tier_counts": _source_tier_counts(audit_rows),
        "authority_level_counts": _authority_level_counts(audit_rows),
        "review_priority_counts": {
            priority: review_priority_counts[priority]
            for priority in sorted(review_priority_counts, key=_priority_sort_key)
        },
        "ambiguity_flag_counts": _ambiguity_flag_counts(audit_rows),
        "topic_key_counts": _topic_key_counts(included_rows),
        "subtopic_key_counts": _subtopic_key_counts(included_rows),
        "topic_subtopic_coverage": _topic_subtopic_coverage(included_rows),
        "revision_linkage_status_counts": {
            key: revision_linkage_counts[key] for key in sorted(revision_linkage_counts)
        },
        "canonical_blessing_status_counts": {
            key: blessing_counts[key] for key in sorted(blessing_counts)
        },
        "manual_review_queue_count": len(manual_review_queue),
        "manual_review_queue": manual_review_queue,
        "rows": recon_rows,
    }


def _build_canonical_corpus_manifest(
    *,
    corpus_dir: Path,
    documents: Iterable[CorpusDocument],
    rows: Iterable[CorpusAuditRecord],
) -> dict[str, Any]:
    included_rows = tuple(documents)
    recon_rows = _build_reconnaissance_rows(documents=included_rows, rows=tuple(rows))
    document_rows = [row for row in recon_rows if row["ingestion_decision"] == INGESTION_DECISION_INCLUDE]
    unresolved_revisions = [
        row
        for row in recon_rows
        if row["ingestion_decision"] == INGESTION_DECISION_REVISION
        and row["revision_linkage_status"] != "attached_to_base_doc"
    ]
    documents_payload: list[dict[str, Any]] = []
    for doc in document_rows:
        documents_payload.append(
            {
                **doc,
                "pending_revision_count": doc["attached_revision_count"],
                "canonical_ready": doc["canonical_blessing_status"] == "ready",
            }
        )
    blessing_counts = Counter(row["canonical_blessing_status"] for row in document_rows)

    return {
        "corpus_dir": str(corpus_dir),
        "taxonomy_version": topic_taxonomy_version(),
        "document_count": len(included_rows),
        "canonical_ready_count": blessing_counts.get("ready", 0),
        "review_required_count": blessing_counts.get("review_required", 0),
        "blocked_count": blessing_counts.get("blocked", 0),
        "documents_with_pending_revisions": sum(
            1 for row in documents_payload if row["has_pending_revisions"]
        ),
        "unresolved_revision_candidate_count": len(unresolved_revisions),
        "canonical_blessing_status_counts": {
            key: blessing_counts[key] for key in sorted(blessing_counts)
        },
        "topic_key_counts": _topic_key_counts(included_rows),
        "subtopic_key_counts": _subtopic_key_counts(included_rows),
        "topic_subtopic_coverage": _topic_subtopic_coverage(included_rows),
        "documents": documents_payload,
        "unresolved_revision_candidates": unresolved_revisions,
    }


def _build_reconnaissance_rows(
    *,
    documents: Iterable[CorpusDocument],
    rows: Iterable[CorpusAuditRecord],
) -> list[dict[str, Any]]:
    audit_rows = tuple(rows)
    included_docs = tuple(documents)
    docs_by_relative = {doc.relative_path: doc for doc in included_docs}
    docs_by_source = {doc.source_path: doc for doc in included_docs}
    attached_revisions_by_doc: dict[str, list[CorpusAuditRecord]] = defaultdict(list)
    revision_linkage_by_source: dict[str, str] = {}

    for row in audit_rows:
        if row.ingestion_decision != INGESTION_DECISION_REVISION:
            continue
        target = (row.base_doc_target or "").strip()
        if not target:
            revision_linkage_by_source[row.source_path] = "missing_base_doc_target"
            continue
        target_doc = docs_by_relative.get(target) or docs_by_source.get(target)
        if target_doc is None:
            revision_linkage_by_source[row.source_path] = "target_not_found"
            continue
        revision_linkage_by_source[row.source_path] = "attached_to_base_doc"
        attached_revisions_by_doc[target_doc.relative_path].append(row)

    recon_rows: list[dict[str, Any]] = []
    for row in audit_rows:
        attached_revisions = attached_revisions_by_doc.get(row.relative_path, [])
        revision_linkage_status = revision_linkage_by_source.get(row.source_path, "not_applicable")
        review_reasons = list(row.ambiguity_flags)
        review_priority = row.review_priority
        if revision_linkage_status == "target_not_found":
            review_reasons.append("revision_target_not_found")
            review_priority = _max_review_priority(review_priority, "critical")
        if attached_revisions:
            review_reasons.append("pending_revision_attachment")
            review_priority = _max_review_priority(review_priority, "medium")
        canonical_blessing_status = _canonical_blessing_status(
            row=row,
            review_priority=review_priority,
            revision_linkage_status=revision_linkage_status,
            has_pending_revisions=bool(attached_revisions),
        )
        needs_manual_review = review_priority != "none"
        recon_rows.append(
            {
                **row.to_dict(),
                "review_priority": review_priority,
                "needs_manual_review": needs_manual_review,
                "review_reasons": review_reasons,
                "revision_linkage_status": revision_linkage_status,
                "attached_revision_count": len(attached_revisions),
                "has_pending_revisions": bool(attached_revisions),
                "attached_revision_candidates": [item.to_dict() for item in attached_revisions],
                "canonical_blessing_status": canonical_blessing_status,
            }
        )

    recon_rows.sort(
        key=lambda row: (
            _priority_sort_key(row["review_priority"]),
            row["ingestion_decision"],
            row["relative_path"],
        )
    )
    return recon_rows


def _build_reconnaissance_gate(
    *,
    blessing_counts: Counter[str],
    revision_linkage_counts: Counter[str],
    manual_review_count: int,
) -> dict[str, Any]:
    blockers: list[str] = []
    if blessing_counts.get("blocked", 0):
        blockers.append("At least one corpus file is blocked from canonical blessing.")
    if revision_linkage_counts.get("missing_base_doc_target", 0):
        blockers.append("At least one revision candidate is missing a base document target.")
    if revision_linkage_counts.get("target_not_found", 0):
        blockers.append("At least one revision candidate points to a base document that was not admitted.")

    if blockers:
        status = "blocked"
    elif manual_review_count:
        status = "review_required"
    else:
        status = "ready_for_canonical_blessing"

    return {
        "status": status,
        "canonical_blessing_allowed": status == "ready_for_canonical_blessing",
        "blocker_count": len(blockers),
        "manual_review_count": manual_review_count,
        "blockers": blockers,
        "next_review_steps": _reconnaissance_next_steps(status=status),
    }


def _canonical_blessing_status(
    *,
    row: CorpusAuditRecord,
    review_priority: str,
    revision_linkage_status: str,
    has_pending_revisions: bool,
) -> str:
    if row.ingestion_decision == INGESTION_DECISION_EXCLUDE:
        return "excluded"
    if row.ingestion_decision == INGESTION_DECISION_REVISION:
        if revision_linkage_status in {"missing_base_doc_target", "target_not_found"}:
            return "blocked"
        return "pending_merge_review"
    if review_priority == "critical":
        return "blocked"
    if has_pending_revisions or review_priority in {"high", "medium", "low"}:
        return "review_required"
    return "ready"


def _max_review_priority(*priorities: str) -> str:
    normalized = [priority for priority in priorities if priority]
    if not normalized:
        return "none"
    return min(normalized, key=_priority_sort_key)


def _priority_sort_key(priority: str) -> int:
    return REVIEW_PRIORITY_ORDER.get(priority, len(REVIEW_PRIORITY_ORDER))


def _reconnaissance_next_steps(*, status: str) -> list[str]:
    if status == "blocked":
        return [
            "Resolve missing or unlinked revision targets before blessing the canonical manifest.",
            "Review blocked corpus files with unknown family or authority shape.",
            "Re-run the audit-first runner after correcting corpus structure or target paths.",
        ]
    if status == "review_required":
        return [
            "Review the manual-review queue before treating the canonical manifest as durable.",
            "Confirm authority shape, vocabulary fit, and pending revision attachment decisions.",
            "Bless the canonical manifest only after the review queue is intentionally accepted.",
        ]
    return [
        "The reconnaissance gate is clear; the canonical manifest can be blessed for this run.",
        "Proceed to normative graph materialization and later live FalkorDB validation.",
    ]


if __name__ == "__main__":
    raise SystemExit(main())
