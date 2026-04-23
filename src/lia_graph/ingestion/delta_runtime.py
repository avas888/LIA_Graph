"""Orchestrator glue for the additive-corpus-v1 delta CLI path.

Phase 6 of ``docs/next/additive_corpusv1.md``. This module owns the
end-to-end wiring between the pure Phase 2-5 components and the
``--additive`` CLI flag in ``ingest.py``. Full rebuild stays in
``materialize_graph_artifacts``; this module is additive-only.

Call flow:

    audit_corpus_documents(root)
        → classify_corpus_documents(...)             # full-corpus, per Decision C1
        → load_baseline_snapshot(supabase_client)    # Phase 2
        → plan_delta(disk_docs, baseline)            # Phase 3
        if dry_run: report + return
        → parse_article_documents(delta_docs)
        → extract_edge_candidates + classify_edge_candidates
        → _merge_suin_scope (when --include-suin)
        → build_graph_delta_plan                     # Phase 5
        → sink.write_delta                           # Phase 4
        → load_graph_plan                            # Falkor
        → emit run summary

Intentionally does NOT rewrite `artifacts/parsed_articles.jsonl` or
`artifacts/typed_edges.jsonl` — Phase 6 v1 skips the bundle rewrite to keep
the delta path fast. Decision E1 says "full rewrite on every applied delta"
but the reviewer added an "skip on empty delta" exception; this v1 extends
the skip to ALL delta runs and leaves a TODO for Phase 9 to measure whether
the rewrite is actually needed (dev-mode artifact reads happen before
delta-mode typically lands in staging).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..instrumentation import emit_event
from .baseline_snapshot import (
    DEFAULT_GENERATION_ID,
    BaselineSnapshot,
    load_baseline_snapshot,
)
from .delta_planner import (
    CorpusDelta,
    DiskDocument,
    plan_delta,
    summarize_delta,
)
from .dangling_store import DanglingStore
from .fingerprint import (
    classifier_output_from_corpus_document,
    compute_doc_fingerprint,
)
from .supabase_sink import SupabaseCorpusSink, SupabaseDeltaResult


@dataclass
class DeltaRunReport:
    """End-to-end summary of a single ``--additive`` CLI invocation."""

    delta_id: str
    target: str
    generation_id: str
    dry_run: bool
    baseline_generation_id: str
    delta_summary: dict[str, Any]
    sink_result: dict[str, Any] | None = None
    falkor_statements: int = 0
    falkor_success: int = 0
    falkor_failure: int = 0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        return out


def _disk_documents_from_corpus(
    corpus_documents: Sequence[Any],
) -> list[DiskDocument]:
    """Build the planner's DiskDocument list from live corpus docs.

    Each CorpusDocument has a ``markdown`` string and a handful of classifier
    attributes. We compute the content_hash inline (same algorithm as
    ``supabase_sink._content_hash``) and project the classifier fields.
    """
    import hashlib

    out: list[DiskDocument] = []
    for doc in corpus_documents:
        relative_path = str(
            getattr(doc, "relative_path", "") or ""
        ).strip()
        if not relative_path:
            continue
        markdown = str(getattr(doc, "markdown", "") or "")
        content_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
        # CorpusDocument exposes getattr-style classifier fields.
        classifier_output = classifier_output_from_corpus_document(
            {
                "topic_key": getattr(doc, "topic_key", None),
                "subtopic_key": getattr(doc, "subtopic_key", None),
                "requires_subtopic_review": getattr(
                    doc, "requires_subtopic_review", False
                ),
                "authority_level": getattr(doc, "authority_level", None),
                "document_archetype": getattr(doc, "document_archetype", None),
                "knowledge_class": getattr(doc, "knowledge_class", None),
                "source_type": getattr(doc, "source_type", None),
            }
        )
        out.append(
            DiskDocument(
                relative_path=relative_path,
                content_hash=content_hash,
                classifier_output=classifier_output,
                source_path=str(getattr(doc, "source_path", "") or "") or None,
            )
        )
    return out


def _fetch_retired_article_keys(
    supabase_client: Any,
    *,
    retired_doc_ids: Sequence[str],
) -> set[str]:
    """Query document_chunks to resolve article keys owned by retired docs."""
    if not retired_doc_ids:
        return set()
    article_keys: set[str] = set()
    for doc_id in retired_doc_ids:
        resp = (
            supabase_client.table("document_chunks")
            .select("chunk_id")
            .eq("doc_id", doc_id)
            .execute()
        )
        for raw in list(getattr(resp, "data", None) or []):
            chunk_id = str(raw.get("chunk_id") or "")
            if "::" in chunk_id:
                _, _, article_key = chunk_id.partition("::")
                if article_key:
                    article_keys.add(article_key)
    return article_keys


def _write_summary_artifact(
    artifacts_dir: Path,
    report: DeltaRunReport,
) -> Path:
    """Persist the run summary to ``artifacts/delta_<delta_id>.json``."""
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    path = artifacts_dir / f"delta_{report.delta_id}.json"
    path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def materialize_delta(
    *,
    corpus_dir: Path | str,
    artifacts_dir: Path | str,
    pattern: str,
    supabase_target: str = "production",
    generation_id: str = DEFAULT_GENERATION_ID,
    delta_id: str | None = None,
    dry_run: bool = False,
    execute_load: bool = False,
    strict_falkordb: bool = False,
    strict_parity: bool = False,
    supabase_client: Any | None = None,
    graph_client: Any | None = None,
    skip_llm: bool = False,
    rate_limit_rpm: int = 60,
    lock_target: str | None = None,
    created_by: str | None = None,
    force_full_classify: bool = False,
) -> DeltaRunReport:
    """Plan + apply a corpus delta against the rolling generation.

    When ``dry_run=True`` the baseline is loaded and the delta is planned
    but no writes hit Supabase or Falkor. Use this for CLI preview +
    Phase 8 ``/api/ingest/additive/preview``.
    """
    # Delayed imports — keep top-level import graph narrow.
    from ..ingest_constants import CorpusDocument, INGESTION_DECISION_INCLUDE
    from ..supabase_client import create_supabase_client_for_target
    from .classifier import classify_edge_candidates
    from .delta_lock import DeltaLockBusy, held_job_lock
    from .linker import extract_edge_candidates
    from .loader import build_graph_delta_plan
    from .parity_check import check_parity
    from .parser import parse_article_documents
    # These helpers live in ingest.py — we import via a narrow interface
    # that doesn't pull the entire CLI stack.
    from ..ingest import audit_corpus_documents

    root = Path(corpus_dir)
    artifacts_root = Path(artifacts_dir)

    if supabase_client is None:
        supabase_client = create_supabase_client_for_target(supabase_target)

    # Phase 7 — parity probe before the delta. Non-blocking unless --strict-parity.
    parity_target = lock_target or supabase_target
    parity_report = None
    if not dry_run:
        parity_report = check_parity(
            supabase_client,
            graph_client,
            generation_id=generation_id,
        )
        if not parity_report.ok and strict_parity:
            from ..instrumentation import emit_event as _emit

            _emit(
                "ingest.delta.cli.done",
                {
                    "delta_id": delta_id or "pre_lock",
                    "outcome": "blocked",
                    "reason": "parity_mismatch_strict",
                },
            )
            raise RuntimeError(
                "parity check failed with --strict-parity — "
                f"mismatches={[m.to_dict() for m in parity_report.mismatches]}"
            )

    # -------- resolve a run id early so every trace + the UI feeler can
    # cross-reference the same delta_id (set here unless the caller pinned
    # one). Used as the shared key for logs/events.jsonl filtering.
    from .delta_planner import _default_delta_id

    run_delta_id = str(
        delta_id or _default_delta_id(generation_id)
    ).strip()
    emit_event(
        "ingest.delta.run.start",
        {
            "delta_id": run_delta_id,
            "target": supabase_target,
            "requested_generation_id": generation_id,
            "dry_run": bool(dry_run),
            "force_full_classify": bool(force_full_classify),
        },
    )

    # -------- audit full corpus --------
    audit_rows = audit_corpus_documents(root, pattern=pattern)
    legacy_docs = tuple(
        CorpusDocument.from_audit_record(row)
        for row in audit_rows
        if row.ingestion_decision == INGESTION_DECISION_INCLUDE
    )
    from ..ingest_subtopic_pass import classify_corpus_documents

    # -------- baseline --------
    # Reviewer-picked semantics for Decision F1: the "rolling generation"
    # dynamically tracks whichever corpus_generations row is currently
    # is_active, not a hardcoded string. If the caller passed the default
    # "gen_active_rolling" and that row is empty but a different row is
    # is_active (e.g. a gen_<UTC> snapshot never promoted yet), use the
    # active one so the shortcut + delta apply land on real data. The
    # caller can still pin a specific generation by passing it explicitly.
    resolved_generation_id = generation_id
    if generation_id == DEFAULT_GENERATION_ID:
        try:
            resp = (
                supabase_client.table("corpus_generations")
                .select("generation_id")
                .eq("is_active", True)
                .limit(1)
                .execute()
            )
            rows = list(getattr(resp, "data", None) or [])
            if rows and rows[0].get("generation_id"):
                resolved_generation_id = str(rows[0]["generation_id"])
        except Exception:  # noqa: BLE001
            pass
    if resolved_generation_id != generation_id:
        emit_event(
            "ingest.delta.generation.resolved",
            {
                "requested": generation_id,
                "resolved_to": resolved_generation_id,
                "reason": "requested_rolling_but_active_is_snapshot",
            },
        )
    baseline: BaselineSnapshot = load_baseline_snapshot(
        supabase_client, generation_id=resolved_generation_id
    )

    # -------- content-hash shortcut (v1.1 optimization) --------
    # If ``force_full_classify`` is False, skip the PASO 4 classifier for
    # every doc whose on-disk bytes match the baseline's stored
    # content_hash. Those docs are byte-identical → their classifier
    # output (and therefore fingerprint) from the last rebuild is still
    # correct. Only truly-new or truly-edited files go through the LLM.
    # For a 1-file delta this drops preview from ~9 min → ~1 sec.
    import hashlib as _hashlib

    prematched_paths: set[str] = set()
    if not force_full_classify:
        for doc in legacy_docs:
            rel_path = str(getattr(doc, "relative_path", "") or "").strip()
            if not rel_path:
                continue
            markdown = str(getattr(doc, "markdown", "") or "")
            disk_hash = _hashlib.sha256(markdown.encode("utf-8")).hexdigest()
            base_doc = baseline.documents_by_relative_path.get(rel_path)
            if (
                base_doc is not None
                and base_doc.content_hash == disk_hash
                and base_doc.doc_fingerprint
                and base_doc.retired_at is None
            ):
                prematched_paths.add(rel_path)

    emit_event(
        "ingest.delta.shortcut.computed",
        {
            "delta_id": run_delta_id,
            "force_full_classify": bool(force_full_classify),
            "legacy_doc_count": len(legacy_docs),
            "prematched_count": len(prematched_paths),
            "classifier_input_count": len(legacy_docs) - len(prematched_paths),
        },
    )

    # -------- classify only the docs that need it --------
    docs_to_classify = tuple(
        d
        for d in legacy_docs
        if str(getattr(d, "relative_path", "") or "").strip() not in prematched_paths
    )
    classified_new = classify_corpus_documents(
        docs_to_classify,
        skip_llm=bool(skip_llm),
        rate_limit_rpm=int(rate_limit_rpm),
    )
    # Merge classified + prematched pass-through. Prematched docs keep
    # their legacy (pre-classification) form — that's safe because the
    # planner will force them into "unchanged" bucket without looking at
    # their classifier output.
    _classified_paths = {
        str(getattr(d, "relative_path", "") or "").strip() for d in classified_new
    }
    pass_through = tuple(
        d
        for d in legacy_docs
        if str(getattr(d, "relative_path", "") or "").strip() in prematched_paths
        and str(getattr(d, "relative_path", "") or "").strip() not in _classified_paths
    )
    corpus_documents = tuple(classified_new) + pass_through

    # -------- plan delta --------
    disk_docs = _disk_documents_from_corpus(corpus_documents)
    delta: CorpusDelta = plan_delta(
        disk_docs=disk_docs,
        baseline=baseline,
        delta_id=run_delta_id,
        prematched_relative_paths=prematched_paths,
    )
    summary = summarize_delta(delta)
    emit_event(
        "ingest.delta.plan.computed",
        {
            **summary,
            "target": supabase_target,
        },
    )

    report = DeltaRunReport(
        delta_id=delta.delta_id,
        target=supabase_target,
        generation_id=resolved_generation_id,
        dry_run=dry_run,
        baseline_generation_id=baseline.generation_id,
        delta_summary=summary,
    )

    if dry_run:
        _write_summary_artifact(artifacts_root, report)
        emit_event(
            "ingest.delta.cli.done",
            {"delta_id": delta.delta_id, "outcome": "dry_run", "elapsed_ms": 0},
        )
        return report

    if delta.is_empty:
        report.warnings.append("Empty delta — no writes performed.")
        _write_summary_artifact(artifacts_root, report)
        emit_event(
            "ingest.delta.cli.done",
            {"delta_id": delta.delta_id, "outcome": "ok_empty", "elapsed_ms": 0},
        )
        return report

    # -------- parse delta docs --------
    delta_paths = {e.relative_path for e in delta.added + delta.modified}
    delta_corpus_docs = tuple(
        d for d in corpus_documents if d.relative_path in delta_paths and d.graph_parse_ready
    )
    delta_graph_documents = tuple(d.markdown_document() for d in delta_corpus_docs)
    if delta_graph_documents:
        delta_articles = parse_article_documents(delta_graph_documents)
        raw_edges = extract_edge_candidates(delta_articles)
        classified_edges = classify_edge_candidates(raw_edges)
    else:
        delta_articles = ()
        classified_edges = ()

    # Precompute modified_article_keys so the Falkor plan can DELETE outbound
    # edges before re-MERGE. The delta_planner dataclass is frozen, so we
    # stash the attribute on the delta via object.__setattr__ — this mirrors
    # Phase 5 test (c)'s approach.
    modified_paths = {e.relative_path for e in delta.modified}
    modified_source_paths = {
        str(d.source_path or "") for d in delta_corpus_docs
        if d.relative_path in modified_paths
    }
    modified_article_keys = tuple(
        sorted(
            {
                a.article_key
                for a in delta_articles
                if str(a.source_path or "") in modified_source_paths
            }
        )
    )
    object.__setattr__(delta, "modified_article_keys", modified_article_keys)

    # -------- Supabase sink --------
    # Use the resolved generation so added/modified docs land on the
    # currently-active row (matches Decision F1 reviewer-pick: rolling
    # pointer follows is_active, doesn't require a dedicated
    # gen_active_rolling row once an operator has promoted a snapshot).
    sink = SupabaseCorpusSink(
        target=supabase_target,
        generation_id=resolved_generation_id,
        client=supabase_client,
    )
    dangling_store = DanglingStore(supabase_client)

    delta_document_payloads = [
        d.to_dict() | {"markdown": d.markdown} for d in delta_corpus_docs
    ]

    sink_result: SupabaseDeltaResult = sink.write_delta(
        delta,
        documents=delta_document_payloads,
        articles=list(delta_articles),
        edges=list(classified_edges),
        dangling_store=dangling_store,
    )
    report.sink_result = sink_result.to_dict()

    # -------- Falkor path --------
    retired_doc_ids = [
        e.baseline.doc_id for e in delta.removed if e.baseline is not None
    ]
    retired_article_keys = _fetch_retired_article_keys(
        supabase_client, retired_doc_ids=retired_doc_ids
    )
    falkor_plan = build_graph_delta_plan(
        delta,
        delta_articles=list(delta_articles),
        delta_edges=list(classified_edges),
        retired_article_keys=retired_article_keys,
        graph_client=graph_client,
    )
    report.falkor_statements = len(falkor_plan.statements)
    emit_event(
        "ingest.delta.falkor.start",
        {"delta_id": delta.delta_id, "statement_count": len(falkor_plan.statements)},
    )
    if execute_load:
        from .loader import load_graph_plan

        execution = load_graph_plan(
            falkor_plan,
            graph_client=graph_client,
            execute=True,
            strict=strict_falkordb,
        )
        for result in execution.results:
            if result.skipped:
                continue
            if result.ok:
                report.falkor_success += 1
            else:
                report.falkor_failure += 1
    emit_event(
        "ingest.delta.falkor.done",
        {
            "delta_id": delta.delta_id,
            "success_count": report.falkor_success,
            "failure_count": report.falkor_failure,
            "elapsed_ms": 0,
        },
    )

    # -------- finalize + persist summary --------
    # Decision E1 (reviewer-revised): skip full artifact bundle rewrite in the
    # v1 delta path. Phase 9 measurement will decide if we need it.
    _write_summary_artifact(artifacts_root, report)
    if report.falkor_failure > 0:
        report.warnings.append(
            f"Falkor had {report.falkor_failure} failed statement(s); check trace events."
        )
    emit_event(
        "ingest.delta.cli.done",
        {
            "delta_id": delta.delta_id,
            "outcome": "ok" if report.falkor_failure == 0 else "partial",
            "elapsed_ms": 0,
        },
    )
    return report


__all__ = [
    "DeltaRunReport",
    "materialize_delta",
]
