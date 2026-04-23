from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Iterable
import json
import os
from pathlib import Path
import re
from typing import Any

from .env_posture import EnvPostureError, assert_local_posture
from .graph import GraphClient, GraphClientError, GraphQueryResult
from .graph.schema import NodeKind
from .ingestion import (
    ClassifiedEdge,
    GraphLoadExecution,
    ParsedArticle,
    SupabaseCorpusSink,
    build_graph_load_plan,
    classify_edge_candidates,
    default_generation_id,
    extract_edge_candidates,
    load_graph_plan,
    normalize_classified_edges,
    parse_article_documents,
)
from .ingestion.suin.bridge import (
    SuinScope,
    build_classified_edges as build_suin_classified_edges,
    build_document_rows as build_suin_document_rows,
    build_parsed_articles as build_suin_parsed_articles,
    build_stub_articles as build_suin_stub_articles,
    build_stub_document_rows as build_suin_stub_document_rows,
)
from .source_tiers import source_tier_key_for_row
from .topic_taxonomy import iter_ingestion_topic_entries, topic_taxonomy_version

# Constants, dataclasses, and classifier/report helpers moved to siblings
# during granularize-v2 round 14. Re-imported here so existing call sites
# in `materialize_graph_artifacts` + `main` keep working unchanged.
from .ingest_constants import (  # noqa: F401
    BINARY_DOCUMENT_EXTENSIONS,
    CORPUS_FAMILY_ALIASES,
    CorpusAuditRecord,
    CorpusDocument,
    CRITICAL_RECON_FLAGS,
    GRAPH_PARSE_STRATEGIES,
    GRAPH_TARGET_FAMILIES,
    HELPER_CODE_EXTENSIONS,
    HIGH_RECON_FLAGS,
    INGESTION_DECISION_EXCLUDE,
    INGESTION_DECISION_INCLUDE,
    INGESTION_DECISION_REVISION,
    INTERNAL_GOVERNANCE_MARKERS,
    INTERNAL_README_MARKERS,
    KNOWLEDGE_CLASS_BY_FAMILY,
    MEDIUM_RECON_FLAGS,
    NORMATIVE_SOURCE_MARKERS,
    PRACTICE_SOURCE_MARKERS,
    REVIEW_PRIORITY_ORDER,
    REVISION_DIRECTIVE_PATTERNS,
    REVISION_FILENAME_MARKERS,
    REVISION_HEADING_RE,
    TEXT_DIRECT_PARSE_EXTENSIONS,
    TEXT_INVENTORY_EXTENSIONS,
)
from .ingest_classifiers import (  # noqa: F401
    _audit_single_file,
    _classify_ingestion_decision,
    _clean_base_doc_target_hint,
    _contains_any,
    _extract_explicit_base_doc_target,
    _infer_ambiguity_flags,
    _infer_authority_level,
    _infer_corpus_family,
    _infer_filename_base_doc_hints,
    _infer_parse_strategy,
    _infer_review_priority,
    _infer_revision_base_doc_target,
    _infer_source_origin,
    _infer_source_tier,
    _infer_source_type,
    _infer_title_hint,
    _infer_vocabulary_labels,
    _is_revision_candidate,
    _is_revision_named_path,
    _is_text_extractable,
    _normalize_search_blob,
    _normalize_token,
    _read_asset_text,
    _resolve_base_doc_target_hint,
    _score_vocabulary_alias_match,
    _score_vocabulary_path_prefix_match,
)
from .ingest_reports import (  # noqa: F401
    _ambiguity_flag_counts,
    _authority_level_counts,
    _build_canonical_corpus_manifest,
    _build_corpus_audit_report,
    _build_corpus_inventory,
    _build_corpus_reconnaissance_report,
    _build_filtered_audit_payload,
    _build_reconnaissance_gate,
    _build_reconnaissance_rows,
    _canonical_blessing_status,
    _decision_counts,
    _document_archetype_counts,
    _extension_counts,
    _family_counts,
    _knowledge_class_counts,
    _max_review_priority,
    _parse_strategy_counts,
    _priority_sort_key,
    _reconnaissance_next_steps,
    _relative_path,
    _review_priority_counts,
    _source_origin_counts,
    _source_tier_counts,
    _source_type_counts,
    _subtopic_key_counts,
    _topic_key_counts,
    _topic_subtopic_coverage,
    _vocabulary_status_counts,
)



DEFAULT_CORPUS_DIR = Path("knowledge_base")
DEFAULT_ARTIFACTS_DIR = Path("artifacts")
DEFAULT_PATTERN = "*"
DEFAULT_REVIEW_SUMMARY_LIMIT = 10

def load_active_index_generation(*args: Any, **kwargs: Any) -> dict[str, Any] | None:
    return None


def scaffold_graph_build(
    markdown_documents: Iterable[tuple[str, str]],
) -> dict[str, Any]:
    articles = parse_article_documents(markdown_documents)
    raw_edges = extract_edge_candidates(articles)
    classified_edges = classify_edge_candidates(raw_edges)
    typed_edges = normalize_classified_edges(articles, classified_edges)
    load_plan = build_graph_load_plan(articles, classified_edges)
    return {
        "articles": [article.to_dict() for article in articles],
        "raw_edges": [candidate.to_dict() for candidate in raw_edges],
        "typed_edges": [edge.to_dict() for edge in typed_edges],
        "graph_load_plan": load_plan.to_dict(),
    }


def audit_corpus_documents(
    corpus_dir: Path | str = DEFAULT_CORPUS_DIR,
    *,
    pattern: str = DEFAULT_PATTERN,
) -> tuple[CorpusAuditRecord, ...]:
    root = Path(corpus_dir)
    if not root.exists():
        raise FileNotFoundError(f"Corpus directory does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Corpus path is not a directory: {root}")

    records: list[CorpusAuditRecord] = []
    for path in sorted(root.rglob(pattern)):
        if not path.is_file():
            continue
        records.append(_audit_single_file(path, corpus_root=root))

    if not records:
        raise FileNotFoundError(
            f"No files matching {pattern!r} were found under {root}"
        )
    return tuple(records)


def discover_corpus_documents(
    corpus_dir: Path | str = DEFAULT_CORPUS_DIR,
    *,
    pattern: str = DEFAULT_PATTERN,
) -> tuple[CorpusDocument, ...]:
    audit_rows = audit_corpus_documents(corpus_dir, pattern=pattern)
    documents = tuple(
        CorpusDocument.from_audit_record(row)
        for row in audit_rows
        if row.ingestion_decision == INGESTION_DECISION_INCLUDE
    )
    if not documents:
        raise FileNotFoundError(
            "No corpus documents were admitted by the audit gate. "
            "Phase 2 expects at least one accountant-facing markdown document."
        )
    return documents


def discover_markdown_documents(
    corpus_dir: Path | str = DEFAULT_CORPUS_DIR,
    *,
    pattern: str = DEFAULT_PATTERN,
) -> tuple[tuple[str, str], ...]:
    corpus_documents = discover_corpus_documents(corpus_dir, pattern=pattern)
    documents = tuple(
        document.markdown_document()
        for document in corpus_documents
        if document.graph_parse_ready
    )
    if not documents:
        raise FileNotFoundError(
            "No graph-targeted markdown files were admitted by the audit gate. "
            "Phase 2 expects at least one normativa document in the shared corpus."
        )
    return documents


def materialize_graph_artifacts(
    *,
    corpus_dir: Path | str = DEFAULT_CORPUS_DIR,
    artifacts_dir: Path | str = DEFAULT_ARTIFACTS_DIR,
    pattern: str = DEFAULT_PATTERN,
    execute_load: bool = False,
    strict_falkordb: bool = False,
    allow_unblessed_load: bool = False,
    review_summary_limit: int = DEFAULT_REVIEW_SUMMARY_LIMIT,
    graph_client: GraphClient | None = None,
    supabase_sink: bool = False,
    supabase_target: str = "production",
    supabase_generation_id: str | None = None,
    supabase_activate: bool = True,
    supabase_sink_factory: Any | None = None,
    include_suin: str | Path | None = None,
    suin_artifacts_root: Path | str = "artifacts/suin",
    skip_llm: bool = False,
    rate_limit_rpm: int = 60,
) -> dict[str, Any]:
    root = Path(corpus_dir)
    artifacts_root = Path(artifacts_dir)
    artifacts_root.mkdir(parents=True, exist_ok=True)

    audit_rows = audit_corpus_documents(root, pattern=pattern)
    legacy_corpus_documents = tuple(
        CorpusDocument.from_audit_record(row)
        for row in audit_rows
        if row.ingestion_decision == INGESTION_DECISION_INCLUDE
    )
    # Phase A4: run PASO 4 classifier over every included doc before the
    # Supabase sink + graph load, so subtema / requires_subtopic_review are
    # populated in one pass. `--skip-llm` returns the legacy tuple unchanged.
    from .ingest_subtopic_pass import classify_corpus_documents

    corpus_documents = classify_corpus_documents(
        legacy_corpus_documents,
        skip_llm=bool(skip_llm),
        rate_limit_rpm=int(rate_limit_rpm),
    )

    corpus_audit_report_path = artifacts_root / "corpus_audit_report.json"
    corpus_reconnaissance_report_path = artifacts_root / "corpus_reconnaissance_report.json"
    revision_candidates_path = artifacts_root / "revision_candidates.json"
    excluded_files_path = artifacts_root / "excluded_files.json"
    canonical_manifest_path = artifacts_root / "canonical_corpus_manifest.json"
    corpus_inventory_path = artifacts_root / "corpus_inventory.json"
    reconnaissance_report = _build_corpus_reconnaissance_report(
        corpus_dir=root,
        documents=corpus_documents,
        rows=audit_rows,
    )

    _write_json(
        corpus_audit_report_path,
        _build_corpus_audit_report(corpus_dir=root, rows=audit_rows),
    )
    _write_json(
        corpus_reconnaissance_report_path,
        reconnaissance_report,
    )
    _write_json(
        revision_candidates_path,
        _build_filtered_audit_payload(
            corpus_dir=root,
            rows=audit_rows,
            decision=INGESTION_DECISION_REVISION,
        ),
    )
    _write_json(
        excluded_files_path,
        _build_filtered_audit_payload(
            corpus_dir=root,
            rows=audit_rows,
            decision=INGESTION_DECISION_EXCLUDE,
        ),
    )
    _write_json(
        canonical_manifest_path,
        _build_canonical_corpus_manifest(corpus_dir=root, documents=corpus_documents, rows=audit_rows),
    )
    _write_json(
        corpus_inventory_path,
        _build_corpus_inventory(corpus_dir=root, documents=corpus_documents, rows=audit_rows),
    )
    manual_review_queue = reconnaissance_report["manual_review_queue"]

    graph_documents = tuple(
        document.markdown_document()
        for document in corpus_documents
        if document.graph_parse_ready
    )
    if not graph_documents:
        raise FileNotFoundError(
            "Audit completed, but no graph-parse-ready normative documents were admitted. "
            "Phase 2 expects at least one normativa document in the shared corpus."
        )

    articles_base = parse_article_documents(graph_documents)
    # ingestionfix_v2 §4 Phase 4: thread origin family into edge extraction
    # so the classifier emits the Spanish-taxonomy edge_type + weight.
    family_by_source_path = {
        document.source_path: document.family
        for document in corpus_documents
        if document.graph_parse_ready
    }
    raw_edges = extract_edge_candidates(
        articles_base, family_by_source_path=family_by_source_path
    )
    classified_edges_base = classify_edge_candidates(raw_edges)

    # Phase B: SUIN merge (two-pass). See docs/next/ingestion_suin.md step #13.
    (
        articles,
        classified_edges,
        suin_document_rows,
        suin_merge_report,
    ) = _merge_suin_scope(
        articles_base=articles_base,
        classified_edges_base=classified_edges_base,
        include_suin=include_suin,
        suin_artifacts_root=Path(suin_artifacts_root),
    )

    typed_edges = normalize_classified_edges(articles, classified_edges)
    plan_graph_client = graph_client or (GraphClient.from_env() if execute_load else None)
    # Phase A5: correlate classified docs → articles → curated taxonomy so the
    # loader emits SubTopicNode + HAS_SUBTOPIC during the same pass as the
    # article/reform load (no separate Falkor-sync step required).
    from .ingest_subtopic_pass import build_article_subtopic_bindings

    article_subtopics = build_article_subtopic_bindings(
        classified_documents=corpus_documents,
        articles=articles,
    )
    load_plan = build_graph_load_plan(
        articles,
        classified_edges,
        graph_client=plan_graph_client,
        article_subtopics=article_subtopics,
    )
    runtime_graph_client = plan_graph_client or (
        GraphClient.from_env(schema=load_plan.schema)
        if execute_load
        else GraphClient(schema=load_plan.schema)
    )

    gate = reconnaissance_report["quality_gate"]
    if execute_load and gate["status"] != "ready_for_canonical_blessing" and not allow_unblessed_load:
        load_execution_model = _skip_graph_load_execution(
            plan=load_plan,
            graph_client=runtime_graph_client,
            reason="reconnaissance_gate_not_ready",
            diagnostics={
                "reconnaissance_gate_status": gate["status"],
                "blockers": list(gate["blockers"]),
                "manual_review_count": gate["manual_review_count"],
            },
        )
    else:
        load_execution_model = load_graph_plan(
            load_plan,
            graph_client=runtime_graph_client,
            execute=execute_load,
            strict=strict_falkordb,
        )
    load_execution = load_execution_model.to_dict()

    parsed_articles_path = artifacts_root / "parsed_articles.jsonl"
    raw_edges_path = artifacts_root / "raw_edges.jsonl"
    typed_edges_path = artifacts_root / "typed_edges.jsonl"
    graph_load_report_path = artifacts_root / "graph_load_report.json"
    graph_validation_report_path = artifacts_root / "graph_validation_report.json"

    _write_jsonl(parsed_articles_path, [article.to_dict() for article in articles])
    _write_jsonl(raw_edges_path, [candidate.to_dict() for candidate in raw_edges])
    _write_jsonl(typed_edges_path, [edge.to_dict() for edge in typed_edges])
    _write_json(graph_load_report_path, load_execution)
    _write_json(graph_validation_report_path, load_plan.validation.to_dict())

    supabase_sink_report: dict[str, Any] | None = None
    if supabase_sink:
        generation_id = str(supabase_generation_id or default_generation_id()).strip()
        if supabase_sink_factory is not None:
            sink = supabase_sink_factory(
                target=supabase_target,
                generation_id=generation_id,
            )
        else:
            sink = SupabaseCorpusSink(
                target=supabase_target,
                generation_id=generation_id,
            )
        knowledge_class_counts = _knowledge_class_counts(corpus_documents)
        sink.write_generation(
            documents=len(corpus_documents),
            chunks=len(articles),
            countries=("colombia",),
            files=[doc.relative_path for doc in corpus_documents],
            knowledge_class_counts=knowledge_class_counts,
            index_dir=str(artifacts_root),
        )
        corpus_document_rows = [
            doc.to_dict() | {"markdown": doc.markdown} for doc in corpus_documents
        ]
        all_document_rows = corpus_document_rows + suin_document_rows
        doc_id_by_source_path, documents_written = sink.write_documents(
            all_document_rows
        )
        chunks_written = sink.write_chunks(
            articles,
            doc_id_by_source_path=doc_id_by_source_path,
        )
        edges_written = sink.write_normative_edges(classified_edges)
        sink_result = sink.finalize(activate=bool(supabase_activate))
        supabase_sink_report = sink_result.to_dict() | {
            "documents_in_corpus": len(corpus_documents),
            "articles_in_corpus": len(articles),
            "typed_edges_in_corpus": len(typed_edges),
            "documents_written_this_run": int(documents_written),
            "chunks_written_this_run": int(chunks_written),
            "edges_written_this_run": int(edges_written),
            "suin_document_rows": len(suin_document_rows),
            "suin_merge": suin_merge_report,
        }

    return {
        "ok": True,
        "corpus_dir": str(root),
        "artifacts_dir": str(artifacts_root),
        "pattern": pattern,
        "taxonomy_version": topic_taxonomy_version(),
        "scanned_file_count": len(audit_rows),
        "decision_counts": _decision_counts(audit_rows),
        "document_count": len(corpus_documents),
        "document_family_counts": _family_counts(corpus_documents),
        "knowledge_class_counts": _knowledge_class_counts(corpus_documents),
        "source_type_counts": _source_type_counts(corpus_documents),
        "extension_counts": _extension_counts(audit_rows),
        "parse_strategy_counts": _parse_strategy_counts(audit_rows),
        "document_archetype_counts": _document_archetype_counts(audit_rows),
        "source_tier_counts": _source_tier_counts(audit_rows),
        "authority_level_counts": _authority_level_counts(audit_rows),
        "review_priority_counts": _review_priority_counts(audit_rows),
        "ambiguity_flag_counts": _ambiguity_flag_counts(audit_rows),
        "topic_key_counts": _topic_key_counts(corpus_documents),
        "subtopic_key_counts": _subtopic_key_counts(corpus_documents),
        "topic_subtopic_coverage": _topic_subtopic_coverage(corpus_documents),
        "reconnaissance_quality_gate": reconnaissance_report["quality_gate"],
        "manual_review_queue_count": reconnaissance_report["manual_review_queue_count"],
        "manual_review_queue_preview": _manual_review_preview(
            manual_review_queue,
            limit=review_summary_limit,
        ),
        "graph_target_families": sorted(GRAPH_TARGET_FAMILIES),
        "graph_target_document_count": sum(1 for doc in corpus_documents if doc.graph_target),
        "graph_parse_ready_document_count": len(graph_documents),
        "article_count": len(articles),
        "raw_edge_count": len(raw_edges),
        "typed_edge_count": len(typed_edges),
        "files": {
            "corpus_audit_report": str(corpus_audit_report_path),
            "corpus_reconnaissance_report": str(corpus_reconnaissance_report_path),
            "revision_candidates": str(revision_candidates_path),
            "excluded_files": str(excluded_files_path),
            "canonical_corpus_manifest": str(canonical_manifest_path),
            "corpus_inventory": str(corpus_inventory_path),
            "parsed_articles": str(parsed_articles_path),
            "raw_edges": str(raw_edges_path),
            "typed_edges": str(typed_edges_path),
            "graph_load_report": str(graph_load_report_path),
            "graph_validation_report": str(graph_validation_report_path),
        },
        "graph_load_report": load_execution,
        "supabase_sink_report": supabase_sink_report,
        "suin_merge_report": suin_merge_report,
    }


def _resolve_suin_scope_path(
    include_suin: str | Path,
    suin_artifacts_root: Path,
) -> Path:
    """Accept either a direct path or a short scope name like `et`."""
    include_path = Path(str(include_suin))
    if include_path.exists() and include_path.is_dir():
        return include_path
    candidate = suin_artifacts_root / str(include_suin)
    if candidate.is_dir():
        return candidate
    raise FileNotFoundError(
        f"--include-suin target not found: {include_suin!r} "
        f"(tried {include_path} and {candidate})"
    )


def _merge_suin_scope(
    *,
    articles_base: tuple[ParsedArticle, ...],
    classified_edges_base: tuple[ClassifiedEdge, ...],
    include_suin: str | Path | None,
    suin_artifacts_root: Path,
) -> tuple[
    tuple[ParsedArticle, ...],
    tuple[ClassifiedEdge, ...],
    list[dict[str, Any]],
    dict[str, Any] | None,
]:
    """Two-pass SUIN merge (see docs/next/ingestion_suin.md Phase B step #13).

    Pass 1: materialize SUIN articles + stub articles for any edge target that
    is not already present. Pass 2: the subsequent `normalize_classified_edges`
    call now sees resolved targets for everything SUIN discovered.

    Returns `(articles_out, classified_edges_out, suin_document_rows, report)`.
    When `include_suin` is falsy, the base inputs pass through untouched.
    """
    if not include_suin:
        return tuple(articles_base), tuple(classified_edges_base), [], None

    scope_path = _resolve_suin_scope_path(include_suin, suin_artifacts_root)
    scope = SuinScope.load(scope_path)

    # Pass 1: concrete SUIN articles + stub articles for targets we do not know yet.
    suin_articles = build_suin_parsed_articles(scope)
    resolved_keys = {a.article_key for a in articles_base} | {
        a.article_key for a in suin_articles
    }
    stub_articles, unresolved_doc_ids = build_suin_stub_articles(
        scope, resolved_article_keys=resolved_keys
    )
    suin_classified = build_suin_classified_edges(scope)

    # SUIN-aware documents + stubs (for Supabase FK integrity).
    suin_document_rows = build_suin_document_rows(scope) + build_suin_stub_document_rows(
        unresolved_doc_ids
    )

    # Pass 1 completes — now we have resolved keys for every SUIN target article.
    articles_out = tuple(articles_base) + tuple(suin_articles) + tuple(stub_articles)
    classified_out = tuple(classified_edges_base) + tuple(suin_classified)

    final_article_keys = {a.article_key for a in articles_out}
    unresolved_after_stub = sum(
        1
        for edge in suin_classified
        if edge.record.target_kind is NodeKind.ARTICLE
        and edge.record.target_key not in final_article_keys
    )

    report: dict[str, Any] = {
        "scope_path": str(scope_path),
        "suin_documents_in": len(scope.documents),
        "suin_articles_in": len(scope.articles),
        "suin_edges_in": len(scope.edges),
        "suin_articles_added": len(suin_articles),
        "stub_articles_created": len(stub_articles),
        "stub_documents_created": len(unresolved_doc_ids),
        "unresolved_after_stub": unresolved_after_stub,
        "verb_counts": dict(scope.manifest.get("verb_counts") or {}),
    }
    return articles_out, classified_out, suin_document_rows, report


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(
        description=(
            "Materialize Phase 2 audit-first shared-corpus inventory and shared-graph "
            "scaffold artifacts in one pass. The runner audits files first, keeps "
            "normativa, interpretacion, and practica visible, then graphizes "
            "normativa first."
        )
    )
    cli.add_argument("--corpus-dir", default=str(DEFAULT_CORPUS_DIR))
    cli.add_argument("--artifacts-dir", default=str(DEFAULT_ARTIFACTS_DIR))
    cli.add_argument(
        "--pattern",
        default=DEFAULT_PATTERN,
        help="Glob pattern used when scanning corpus files.",
    )
    cli.add_argument(
        "--execute-load",
        action="store_true",
        help="Execute the staged graph load against FalkorDB after the reconnaissance gate clears.",
    )
    cli.add_argument(
        "--strict-falkordb",
        action="store_true",
        help="Fail instead of skipping when live FalkorDB execution is unavailable or a statement errors.",
    )
    cli.add_argument(
        "--allow-unblessed-load",
        action="store_true",
        help="Allow live FalkorDB execution even when the reconnaissance gate is not ready_for_canonical_blessing.",
    )
    cli.add_argument(
        "--review-summary-limit",
        type=int,
        default=DEFAULT_REVIEW_SUMMARY_LIMIT,
        help="Maximum number of manual-review queue rows to surface in the run summary.",
    )
    cli.add_argument(
        "--supabase-sink",
        action=argparse.BooleanOptionalAction,
        default=_env_bool("LIA_INGEST_SUPABASE", False),
        help=(
            "Also write documents/document_chunks/corpus_generations/normative_edges "
            "rows into Supabase after the artifact bundle is materialized."
        ),
    )
    cli.add_argument(
        "--supabase-target",
        default=os.environ.get("LIA_INGEST_SUPABASE_TARGET", "production"),
        choices=["production", "wip"],
        help="Supabase target for the corpus sink. Defaults to production.",
    )
    cli.add_argument(
        "--supabase-generation-id",
        default=None,
        help=(
            "Override the generation_id tag used for this sink run. "
            "Defaults to gen_<UTC timestamp>."
        ),
    )
    cli.add_argument(
        "--no-supabase-activate",
        dest="supabase_activate",
        action="store_false",
        help="Write rows but leave is_active=false on corpus_generations.",
    )
    cli.set_defaults(supabase_activate=True)
    cli.add_argument(
        "--include-suin",
        default=None,
        help=(
            "Scope name (e.g. `et`) under `artifacts/suin/` OR a direct path to "
            "a SUIN harvest directory. When set, the SUIN JSONL rows are merged "
            "into parsed_articles + classified_edges before the Supabase sink "
            "+ Falkor load run."
        ),
    )
    cli.add_argument(
        "--suin-artifacts-root",
        default="artifacts/suin",
        help="Base directory that --include-suin scope names resolve against.",
    )
    cli.add_argument(
        "--allow-non-local-env",
        action="store_true",
        help=(
            "Skip the local-env posture guard. Required when intentionally "
            "running against cloud Supabase / cloud FalkorDB. See "
            "src/lia_graph/env_posture.py."
        ),
    )
    cli.add_argument(
        "--skip-llm",
        action="store_true",
        help=(
            "Skip the PASO 4 classifier pass during the audit. Legacy "
            "_infer_vocabulary_labels verdict stays authoritative — no "
            "subtema population, no Falkor SubTopic structure. Intended "
            "for fast dev-loop and CI smoke tests."
        ),
    )
    cli.add_argument(
        "--rate-limit-rpm",
        type=int,
        default=int(os.environ.get("LIA_INGEST_CLASSIFIER_RPM", "60")),
        help=(
            "Upper bound on PASO 4 classifier calls per minute. Default 60 "
            "(≈22 min for a 1300-doc corpus). Gemini Flash paid tier "
            "tolerates ~1000 rpm."
        ),
    )
    cli.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    # Additive-corpus-v1 Phase 6 — delta-path flags.
    cli.add_argument(
        "--additive",
        action="store_true",
        help=(
            "Run the additive-corpus-v1 delta path: compare the on-disk "
            "corpus against the current rolling Supabase baseline and apply "
            "only the diff (added + modified + removed docs). Requires "
            "--supabase-sink; --supabase-generation-id defaults to "
            "'gen_active_rolling'. See docs/next/additive_corpusv1.md."
        ),
    )
    cli.add_argument(
        "--delta-id",
        default=None,
        help=(
            "Override the auto-generated delta_id (format "
            "'delta_YYYYMMDD_HHMMSS_xxxxxx'). Useful for replay / testing."
        ),
    )
    cli.add_argument(
        "--dry-run-delta",
        action="store_true",
        help=(
            "Plan the delta + print the summary but do NOT write to Supabase "
            "or Falkor. Only meaningful with --additive."
        ),
    )
    cli.add_argument(
        "--strict-parity",
        action="store_true",
        help=(
            "Escalate any Supabase<->Falkor parity-check mismatch to a hard "
            "block before the delta is applied. Without this flag, mismatches "
            "beyond the default tolerance emit a warning and proceed. "
            "(Parity check lands in Phase 7; flag is already reserved here "
            "so Phase 8 UI can bind to it.)"
        ),
    )
    return cli


def _env_bool(name: str, default: bool) -> bool:
    value = str(os.environ.get(name, "") or "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if not args.allow_non_local_env:
        try:
            assert_local_posture(
                require_supabase=bool(args.supabase_sink),
                require_falkor=bool(args.execute_load),
            )
        except EnvPostureError as exc:
            payload = {"ok": False, "error": "env_posture", "message": str(exc)}
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(f"Phase 2 ingest aborted: {exc}")
            return 4

    # Additive-corpus-v1 Phase 6 delta path.
    if getattr(args, "additive", False):
        if not args.supabase_sink:
            msg = (
                "--additive requires --supabase-sink; the delta path reads the "
                "current baseline from Supabase and has nothing to do without it."
            )
            payload = {"ok": False, "error": "additive_requires_supabase", "message": msg}
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(msg)
            return 2
        from .ingestion.delta_runtime import materialize_delta

        generation_id = str(
            args.supabase_generation_id or "gen_active_rolling"
        ).strip() or "gen_active_rolling"
        try:
            report = materialize_delta(
                corpus_dir=Path(args.corpus_dir),
                artifacts_dir=Path(args.artifacts_dir),
                pattern=args.pattern,
                supabase_target=str(args.supabase_target),
                generation_id=generation_id,
                delta_id=args.delta_id,
                dry_run=bool(args.dry_run_delta),
                execute_load=bool(args.execute_load),
                strict_falkordb=bool(args.strict_falkordb),
                strict_parity=bool(args.strict_parity),
                skip_llm=bool(args.skip_llm),
                rate_limit_rpm=int(args.rate_limit_rpm),
            )
        except (FileNotFoundError, NotADirectoryError) as exc:
            payload = {
                "ok": False,
                "error": "corpus_unavailable",
                "message": str(exc),
            }
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(f"Additive delta aborted: {exc}")
            return 2
        except GraphClientError as exc:
            payload = {
                "ok": False,
                "error": "graph_load_failed",
                "message": str(exc),
            }
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(f"Additive delta Falkor load failed: {exc}")
            return 3
        result = {"ok": True, "delta_run": report.to_dict()}
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            summary = report.delta_summary
            mode = "dry-run" if report.dry_run else "applied"
            print(
                f"[additive {mode}] delta_id={report.delta_id} "
                f"added={summary['added']} modified={summary['modified']} "
                f"removed={summary['removed']} unchanged={summary['unchanged']}"
            )
            if report.warnings:
                for w in report.warnings:
                    print(f"  warn: {w}")
        return 0

    try:
        result = materialize_graph_artifacts(
            corpus_dir=Path(args.corpus_dir),
            artifacts_dir=Path(args.artifacts_dir),
            pattern=args.pattern,
            execute_load=args.execute_load,
            strict_falkordb=args.strict_falkordb,
            allow_unblessed_load=args.allow_unblessed_load,
            review_summary_limit=max(args.review_summary_limit, 0),
            supabase_sink=bool(args.supabase_sink),
            supabase_target=str(args.supabase_target),
            supabase_generation_id=args.supabase_generation_id,
            supabase_activate=bool(args.supabase_activate),
            include_suin=args.include_suin,
            suin_artifacts_root=Path(args.suin_artifacts_root),
            skip_llm=bool(args.skip_llm),
            rate_limit_rpm=int(args.rate_limit_rpm),
        )
    except (FileNotFoundError, NotADirectoryError) as exc:
        payload = {"ok": False, "error": "corpus_unavailable", "message": str(exc)}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"Phase 2 graph artifact materialization failed: {exc}")
        return 2
    except GraphClientError as exc:
        payload = {"ok": False, "error": "graph_load_failed", "message": str(exc)}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"Phase 2 graph load failed: {exc}")
        return 3

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_human(result)
    return 0


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _skip_graph_load_execution(
    *,
    plan: Any,
    graph_client: GraphClient,
    reason: str,
    diagnostics: dict[str, object],
) -> GraphLoadExecution:
    results = tuple(
        GraphQueryResult(
            description=statement.description,
            query=statement.query,
            parameters=statement.parameters,
            skipped=True,
            diagnostics={"reason": reason, **diagnostics},
        )
        for statement in plan.statements
    )
    return GraphLoadExecution(
        requested_execution=True,
        executed=False,
        results=results,
        plan=plan,
        connection=graph_client.config.to_dict(),
    )


def _manual_review_preview(
    rows: list[dict[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    return [
        {
            "relative_path": row["relative_path"],
            "review_priority": row["review_priority"],
            "canonical_blessing_status": row["canonical_blessing_status"],
            "revision_linkage_status": row["revision_linkage_status"],
            "review_reasons": list(row["review_reasons"]),
        }
        for row in rows[:limit]
    ]


def _print_human(result: dict[str, Any]) -> None:
    print("Phase 2 audit-first shared-corpus inventory + shared-graph scaffold artifacts")
    print(f"- corpus_dir: {result['corpus_dir']}")
    print(f"- scanned_files: {result['scanned_file_count']}")
    print(f"- decisions: {result['decision_counts']}")
    print(f"- included_documents: {result['document_count']}")
    print(f"- families: {result['document_family_counts']}")
    print(f"- knowledge_classes: {result['knowledge_class_counts']}")
    print(f"- source_types: {result['source_type_counts']}")
    print(f"- extensions: {result['extension_counts']}")
    print(f"- parse_strategies: {result['parse_strategy_counts']}")
    print(f"- document_archetypes: {result['document_archetype_counts']}")
    print(f"- reconnaissance_gate: {result['reconnaissance_quality_gate']}")
    print(f"- manual_review_queue_count: {result['manual_review_queue_count']}")
    for row in result["manual_review_queue_preview"]:
        reasons = ", ".join(row["review_reasons"]) if row["review_reasons"] else "none"
        print(
            f"- manual_review_preview: {row['review_priority']} {row['relative_path']} "
            f"({row['canonical_blessing_status']}; {row['revision_linkage_status']}; {reasons})"
        )
    print(f"- graph_target_families: {', '.join(result['graph_target_families'])}")
    print(f"- graph_target_documents: {result['graph_target_document_count']}")
    print(f"- graph_parse_ready_documents: {result['graph_parse_ready_document_count']}")
    print(f"- articles: {result['article_count']}")
    print(f"- raw_edges: {result['raw_edge_count']}")
    print(f"- typed_edges: {result['typed_edge_count']}")
    load_report = result["graph_load_report"]
    print(f"- load_requested: {load_report['requested_execution']}")
    print(f"- load_executed: {load_report['executed']}")
    print(f"- load_success_count: {load_report['success_count']}")
    print(f"- load_failure_count: {load_report['failure_count']}")
    print(f"- load_skipped_count: {load_report['skipped_count']}")
    print(f"- load_connection: {load_report['connection']}")
    for label, path in result["files"].items():
        print(f"- {label}: {path}")



if __name__ == "__main__":
    import sys as _sys
    _sys.exit(main())
