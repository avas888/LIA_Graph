from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from typing import Any

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


DEFAULT_CORPUS_DIR = Path("knowledge_base")
DEFAULT_ARTIFACTS_DIR = Path("artifacts")
DEFAULT_PATTERN = "*"
DEFAULT_REVIEW_SUMMARY_LIMIT = 10

INGESTION_DECISION_INCLUDE = "include_corpus"
INGESTION_DECISION_REVISION = "revision_candidate"
INGESTION_DECISION_EXCLUDE = "exclude_internal"

GRAPH_TARGET_FAMILIES = frozenset({"normativa"})
GRAPH_PARSE_STRATEGIES = frozenset({"markdown_graph_parse"})
TEXT_DIRECT_PARSE_EXTENSIONS = frozenset({".md", ".markdown"})
TEXT_INVENTORY_EXTENSIONS = frozenset({".txt", ".csv", ".json", ".yaml", ".yml", ".xml", ".html"})
BINARY_DOCUMENT_EXTENSIONS = frozenset({".pdf", ".doc", ".docx"})
HELPER_CODE_EXTENSIONS = frozenset({".py", ".js", ".ts", ".pyc"})

REVIEW_PRIORITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "none": 4,
}

CRITICAL_RECON_FLAGS = frozenset(
    {
        "family_unknown",
        "knowledge_class_unknown",
        "revision_target_missing",
        "revision_target_not_found",
    }
)
HIGH_RECON_FLAGS = frozenset(
    {
        "source_type_unknown",
        "graph_target_not_parse_ready",
    }
)
MEDIUM_RECON_FLAGS = frozenset(
    {
        "custom_topic_pending_vocab",
        "vocabulary_unassigned",
        "pending_revision_attachment",
    }
)

CORPUS_FAMILY_ALIASES = {
    "normativa": "normativa",
    "normative_base": "normativa",
    "normativa_base": "normativa",
    "doctrina_oficial": "normativa",
    "doctrinaoficial": "normativa",
    "ley": "normativa",
    "leyes": "normativa",
    "decreto": "normativa",
    "decretos": "normativa",
    "resolucion": "normativa",
    "resoluciones": "normativa",
    "estatuto_tributario": "normativa",
    "estatuto": "normativa",
    "et": "normativa",
    "dian": "normativa",
    "concepto": "normativa",
    "conceptos": "normativa",
    "sentencia": "normativa",
    "sentencias": "normativa",
    "interpretacion": "interpretacion",
    "interpretacion_expertos": "interpretacion",
    "interpretative_guidance": "interpretacion",
    "expertos": "interpretacion",
    "experts": "interpretacion",
    "industry_guidance": "interpretacion",
    "analisis": "interpretacion",
    "practica": "practica",
    "practica_loggro": "practica",
    "practical": "practica",
    "practica_erp": "practica",
    "loggro": "practica",
}

KNOWLEDGE_CLASS_BY_FAMILY = {
    "normativa": "normative_base",
    "interpretacion": "interpretative_guidance",
    "practica": "practica_erp",
    "unknown": "unknown",
}

REVISION_FILENAME_MARKERS = ("patch", "upsert", "errata")
REVISION_DIRECTIVE_PATTERNS = (
    re.compile(
        r"(?im)^\s*(?:\*\*?)?(?:insertar en|base doc|documento base|target)(?:\*\*?)?\s*:\s*(.+?)\s*$"
    ),
    re.compile(r"(?im)^\s*(?:aplicar sobre|mergear en)\s+(.+?)\s*$"),
    re.compile(
        r"(?im)^\s*(?:\*\*?)?tipo de documento(?:\*\*?)?\s*:\s*.*?\binserci[oó]n en\s+(.+?)\s*$"
    ),
    re.compile(r"(?im)^\s*#\s*errata\s+[—-]\s+(.+?)\s*$"),
)
REVISION_HEADING_RE = re.compile(r"(?im)^\s*#\s*.+\b(?:patch|upsert|errata)\b")
INTERNAL_README_MARKERS = (
    "next action",
    "checkpoint log",
    "decision log",
    "implementacion",
    "implementation",
    "roadmap",
    "pending",
    "pendiente",
    "working file",
)
INTERNAL_GOVERNANCE_MARKERS = (
    "routing test matrix",
    "panel review",
    "vocabulario canonico",
    "vocabulary sources",
    "proposal flow",
)
PRACTICE_SOURCE_MARKERS = {
    "checklist": "checklist",
    "calendario": "calendario",
    "instructivo": "instructivo",
}
NORMATIVE_SOURCE_MARKERS = (
    ("formulario", "formulario_oficial"),
    ("ley", "ley"),
    ("decreto", "decreto"),
    ("resolucion", "resolucion"),
    ("concepto", "concepto"),
    ("sentencia", "sentencia"),
)


@dataclass(frozen=True)
class CorpusAuditRecord:
    source_origin: str
    source_path: str
    relative_path: str
    title_hint: str
    extension: str
    text_extractable: bool
    parse_strategy: str
    document_archetype: str
    ingestion_decision: str
    decision_reason: str
    taxonomy_version: str
    family: str | None = None
    knowledge_class: str | None = None
    source_type: str | None = None
    source_tier: str | None = None
    authority_level: str | None = None
    graph_target: bool = False
    graph_parse_ready: bool = False
    topic_key: str | None = None
    subtopic_key: str | None = None
    vocabulary_status: str | None = None
    base_doc_target: str | None = None
    ambiguity_flags: tuple[str, ...] = ()
    review_priority: str = "none"
    needs_manual_review: bool = False
    markdown: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_origin": self.source_origin,
            "source_path": self.source_path,
            "relative_path": self.relative_path,
            "title_hint": self.title_hint,
            "extension": self.extension,
            "text_extractable": self.text_extractable,
            "parse_strategy": self.parse_strategy,
            "document_archetype": self.document_archetype,
            "ingestion_decision": self.ingestion_decision,
            "decision_reason": self.decision_reason,
            "taxonomy_version": self.taxonomy_version,
            "family": self.family,
            "knowledge_class": self.knowledge_class,
            "source_type": self.source_type,
            "source_tier": self.source_tier,
            "authority_level": self.authority_level,
            "graph_target": self.graph_target,
            "graph_parse_ready": self.graph_parse_ready,
            "topic_key": self.topic_key,
            "subtopic_key": self.subtopic_key,
            "vocabulary_status": self.vocabulary_status,
            "base_doc_target": self.base_doc_target,
            "ambiguity_flags": list(self.ambiguity_flags),
            "review_priority": self.review_priority,
            "needs_manual_review": self.needs_manual_review,
        }


@dataclass(frozen=True)
class CorpusDocument:
    source_origin: str
    source_path: str
    relative_path: str
    title_hint: str
    extension: str
    text_extractable: bool
    parse_strategy: str
    document_archetype: str
    taxonomy_version: str
    family: str
    knowledge_class: str
    source_type: str
    source_tier: str
    authority_level: str
    graph_target: bool
    graph_parse_ready: bool
    topic_key: str | None
    subtopic_key: str | None
    vocabulary_status: str
    ambiguity_flags: tuple[str, ...]
    review_priority: str
    needs_manual_review: bool
    markdown: str

    @classmethod
    def from_audit_record(cls, record: CorpusAuditRecord) -> "CorpusDocument":
        return cls(
            source_origin=record.source_origin,
            source_path=record.source_path,
            relative_path=record.relative_path,
            title_hint=record.title_hint,
            extension=record.extension,
            text_extractable=record.text_extractable,
            parse_strategy=record.parse_strategy,
            document_archetype=record.document_archetype,
            taxonomy_version=record.taxonomy_version,
            family=record.family or "unknown",
            knowledge_class=record.knowledge_class or "unknown",
            source_type=record.source_type or "unknown",
            source_tier=record.source_tier or "unknown",
            authority_level=record.authority_level or "unknown",
            graph_target=record.graph_target,
            graph_parse_ready=record.graph_parse_ready,
            topic_key=record.topic_key,
            subtopic_key=record.subtopic_key,
            vocabulary_status=record.vocabulary_status or "unassigned",
            ambiguity_flags=record.ambiguity_flags,
            review_priority=record.review_priority,
            needs_manual_review=record.needs_manual_review,
            markdown=record.markdown or "",
        )

    def markdown_document(self) -> tuple[str, str]:
        return (self.source_path, self.markdown)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_origin": self.source_origin,
            "source_path": self.source_path,
            "relative_path": self.relative_path,
            "title_hint": self.title_hint,
            "extension": self.extension,
            "text_extractable": self.text_extractable,
            "parse_strategy": self.parse_strategy,
            "document_archetype": self.document_archetype,
            "taxonomy_version": self.taxonomy_version,
            "family": self.family,
            "knowledge_class": self.knowledge_class,
            "source_type": self.source_type,
            "source_tier": self.source_tier,
            "authority_level": self.authority_level,
            "graph_target": self.graph_target,
            "graph_parse_ready": self.graph_parse_ready,
            "topic_key": self.topic_key,
            "subtopic_key": self.subtopic_key,
            "vocabulary_status": self.vocabulary_status,
            "ambiguity_flags": list(self.ambiguity_flags),
            "review_priority": self.review_priority,
            "needs_manual_review": self.needs_manual_review,
        }


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
) -> dict[str, Any]:
    root = Path(corpus_dir)
    artifacts_root = Path(artifacts_dir)
    artifacts_root.mkdir(parents=True, exist_ok=True)

    audit_rows = audit_corpus_documents(root, pattern=pattern)
    corpus_documents = tuple(
        CorpusDocument.from_audit_record(row)
        for row in audit_rows
        if row.ingestion_decision == INGESTION_DECISION_INCLUDE
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
    raw_edges = extract_edge_candidates(articles_base)
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
    load_plan = build_graph_load_plan(
        articles,
        classified_edges,
        graph_client=plan_graph_client,
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
    cli.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return cli


def _env_bool(name: str, default: bool) -> bool:
    value = str(os.environ.get(name, "") or "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
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


def _audit_single_file(path: Path, *, corpus_root: Path) -> CorpusAuditRecord:
    relative_path = _relative_path(path, corpus_root)
    source_origin = _infer_source_origin(path, corpus_root)
    extension = path.suffix.lower()
    text_extractable = _is_text_extractable(path, extension=extension)
    markdown = _read_asset_text(path) if text_extractable else ""
    title_hint = _infer_title_hint(path, markdown=markdown)
    ingestion_decision, decision_reason, base_doc_target, document_archetype = _classify_ingestion_decision(
        path=path,
        relative_path=relative_path,
        markdown=markdown,
        extension=extension,
        text_extractable=text_extractable,
        corpus_root=corpus_root,
    )

    family = _infer_corpus_family(path, markdown=markdown, corpus_root=corpus_root)
    knowledge_class = KNOWLEDGE_CLASS_BY_FAMILY.get(family, "unknown")
    source_type = _infer_source_type(path, markdown=markdown, family=family)
    topic_key, subtopic_key, vocabulary_status, taxonomy_version = _infer_vocabulary_labels(
        path,
        markdown=markdown,
    )
    graph_target = (
        ingestion_decision == INGESTION_DECISION_INCLUDE
        and family in GRAPH_TARGET_FAMILIES
    )
    parse_strategy = _infer_parse_strategy(
        decision=ingestion_decision,
        family=family,
        extension=extension,
        text_extractable=text_extractable,
        document_archetype=document_archetype,
    )
    source_tier = _infer_source_tier(
        decision=ingestion_decision,
        knowledge_class=knowledge_class,
        source_type=source_type,
    )
    authority_level = _infer_authority_level(
        decision=ingestion_decision,
        family=family,
        source_type=source_type,
    )
    graph_parse_ready = graph_target and parse_strategy in GRAPH_PARSE_STRATEGIES
    ambiguity_flags = _infer_ambiguity_flags(
        decision=ingestion_decision,
        family=family,
        knowledge_class=knowledge_class,
        source_type=source_type,
        graph_target=graph_target,
        graph_parse_ready=graph_parse_ready,
        vocabulary_status=vocabulary_status,
        base_doc_target=base_doc_target,
    )
    review_priority = _infer_review_priority(
        decision=ingestion_decision,
        ambiguity_flags=ambiguity_flags,
    )
    needs_manual_review = review_priority != "none"

    if ingestion_decision != INGESTION_DECISION_INCLUDE:
        source_type = None
        graph_target = False
        graph_parse_ready = False
        if ingestion_decision == INGESTION_DECISION_EXCLUDE:
            topic_key = None
            subtopic_key = None
            vocabulary_status = None

    return CorpusAuditRecord(
        source_origin=source_origin,
        source_path=str(path),
        relative_path=relative_path,
        title_hint=title_hint,
        extension=extension,
        text_extractable=text_extractable,
        parse_strategy=parse_strategy,
        document_archetype=document_archetype,
        ingestion_decision=ingestion_decision,
        decision_reason=decision_reason,
        taxonomy_version=taxonomy_version,
        family=family,
        knowledge_class=knowledge_class,
        source_type=source_type,
        source_tier=source_tier,
        authority_level=authority_level,
        graph_target=graph_target,
        graph_parse_ready=graph_parse_ready,
        topic_key=topic_key,
        subtopic_key=subtopic_key,
        vocabulary_status=vocabulary_status,
        base_doc_target=base_doc_target,
        ambiguity_flags=ambiguity_flags,
        review_priority=review_priority,
        needs_manual_review=needs_manual_review,
        markdown=markdown,
    )


def _classify_ingestion_decision(
    *,
    path: Path,
    relative_path: str,
    markdown: str,
    extension: str,
    text_extractable: bool,
    corpus_root: Path,
) -> tuple[str, str, str | None, str]:
    file_name_norm = _normalize_token(path.name)
    stem_norm = _normalize_token(path.stem)
    content_norm = _normalize_search_blob(markdown)
    path_parts = tuple(_normalize_token(part) for part in Path(relative_path).parts)

    if path.name.lower() == "state.md" or stem_norm.endswith("_state"):
        return (
            INGESTION_DECISION_EXCLUDE,
            "Excluded working state file.",
            None,
            "working_note",
        )
    if path.name.lower() in {"claude.md", "updator.md"}:
        return (
            INGESTION_DECISION_EXCLUDE,
            "Excluded implementation-control or operator instruction file.",
            None,
            "governance_doc",
        )
    if path.name.lower() == "readme.md" or (
        file_name_norm.startswith("readme_")
        and _contains_any(content_norm, INTERNAL_README_MARKERS)
    ):
        return (
            INGESTION_DECISION_EXCLUDE,
            "Excluded working README or implementation note.",
            None,
            "working_note",
        )
    if any(part in {"self_improvement", "improvement_corpus"} for part in path_parts):
        return (
            INGESTION_DECISION_EXCLUDE,
            "Excluded evaluation, self-improvement, or corpus-improvement working material.",
            None,
            "working_note",
        )
    if "documents_to_branch_and_improve" in path_parts and "to_upload" in path_parts:
        return (
            INGESTION_DECISION_EXCLUDE,
            "Excluded branch-staging fragment pending consolidation into accountant-facing documents.",
            None,
            "working_note",
        )
    if any(part == "deprecated" for part in path_parts):
        return (
            INGESTION_DECISION_EXCLUDE,
            "Excluded deprecated mirror or archive material.",
            None,
            "deprecated_copy",
        )
    if file_name_norm.startswith(("review_", "plan_")) or "wisdom_pills" in file_name_norm:
        return (
            INGESTION_DECISION_EXCLUDE,
            "Excluded review, roadmap, or ideation working material.",
            None,
            "working_note",
        )
    if "analisis_gap" in stem_norm or "gap_analysis" in stem_norm:
        return (
            INGESTION_DECISION_EXCLUDE,
            "Excluded gap-analysis or audit-analysis working material.",
            None,
            "gap_analysis",
        )
    if _contains_any(content_norm, ("gap", "audit gap", "gap analysis", "analisis gap")):
        return (
            INGESTION_DECISION_EXCLUDE,
            "Excluded gap-analysis or audit-analysis working material.",
            None,
            "gap_analysis",
        )
    if stem_norm.endswith("_fuente") and _contains_any(
        content_norm,
        ("gestor normativo", "mapa completo de decretos referenciados"),
    ):
        return (
            INGESTION_DECISION_EXCLUDE,
            "Excluded generated source-map or reference-catalog helper document.",
            None,
            "helper_asset",
        )
    if _contains_any(content_norm, INTERNAL_GOVERNANCE_MARKERS):
        return (
            INGESTION_DECISION_EXCLUDE,
            "Excluded governance or taxonomy-control document.",
            None,
            "governance_doc",
        )
    if "errata" in file_name_norm:
        revision_hint = _infer_revision_base_doc_target(
            path=path,
            markdown=markdown,
            corpus_root=corpus_root,
        )
        return (
            INGESTION_DECISION_REVISION,
            "Classified as errata or correction material that should merge into a base document first.",
            revision_hint,
            "errata",
        )
    if _is_revision_candidate(path=path, markdown=markdown):
        revision_hint = _infer_revision_base_doc_target(
            path=path,
            markdown=markdown,
            corpus_root=corpus_root,
        )
        return (
            INGESTION_DECISION_REVISION,
            "Classified as patch/update material that should merge into a base document first.",
            revision_hint,
            "revision_patch",
        )
    if extension in HELPER_CODE_EXTENSIONS or any(
        part in {"crawler", "crawlers", "helper", "helpers", "scripts"} for part in path_parts
    ):
        return (
            INGESTION_DECISION_EXCLUDE,
            "Excluded helper or crawler artifact.",
            None,
            "helper_asset",
        )
    if extension == ".txt" and any(marker in file_name_norm for marker in ("resumen", "summary")):
        return (
            INGESTION_DECISION_EXCLUDE,
            "Excluded working summary note.",
            None,
            "working_note",
        )
    if not text_extractable and extension not in BINARY_DOCUMENT_EXTENSIONS:
        return (
            INGESTION_DECISION_EXCLUDE,
            "Excluded non-text helper or binary asset that is not a corpus document format.",
            None,
            "binary_asset",
        )

    return (
        INGESTION_DECISION_INCLUDE,
        "Admitted as accountant-facing corpus document.",
        None,
        "base_doc",
    )


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


def _normalize_token(value: str) -> str:
    normalized = str(value).strip().lower()
    normalized = (
        normalized.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ü", "u")
    )
    normalized = normalized.replace("-", "_").replace("/", "_")
    normalized = re.sub(r"[^a-z0-9_]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized


def _normalize_search_blob(value: str) -> str:
    normalized = _normalize_token(value)
    return normalized.replace("_", " ")


def _is_text_extractable(path: Path, *, extension: str) -> bool:
    if extension in TEXT_DIRECT_PARSE_EXTENSIONS or extension in TEXT_INVENTORY_EXTENSIONS:
        return True
    if extension in BINARY_DOCUMENT_EXTENSIONS:
        return False
    sample = path.read_bytes()[:4096]
    if not sample:
        return True
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def _read_asset_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _infer_title_hint(path: Path, *, markdown: str) -> str:
    for raw_line in markdown.splitlines():
        line = raw_line.strip().lstrip("#>").strip()
        if line:
            return line[:160]
    return path.stem.replace("_", " ").strip()[:160] or path.name


def _contains_any(text: str, markers: Iterable[str]) -> bool:
    return any(_normalize_search_blob(marker) in text for marker in markers)


def _infer_parse_strategy(
    *,
    decision: str,
    family: str,
    extension: str,
    text_extractable: bool,
    document_archetype: str,
) -> str:
    if decision == INGESTION_DECISION_EXCLUDE:
        return "excluded_internal"
    if decision == INGESTION_DECISION_REVISION:
        return "revision_merge_candidate"
    if document_archetype != "base_doc":
        return "inventory_only"
    if family in GRAPH_TARGET_FAMILIES and extension in TEXT_DIRECT_PARSE_EXTENSIONS:
        return "markdown_graph_parse"
    if extension in TEXT_DIRECT_PARSE_EXTENSIONS:
        return "markdown_inventory_only"
    if text_extractable and extension in TEXT_INVENTORY_EXTENSIONS:
        return "text_inventory_only"
    if text_extractable:
        return "text_inventory_only"
    return "binary_inventory_only"


def _infer_source_tier(
    *,
    decision: str,
    knowledge_class: str,
    source_type: str | None,
) -> str:
    if decision == INGESTION_DECISION_EXCLUDE or knowledge_class in {"", "unknown"}:
        return "unknown"
    return source_tier_key_for_row(
        knowledge_class=knowledge_class,
        source_type=source_type,
    )


def _infer_authority_level(
    *,
    decision: str,
    family: str,
    source_type: str | None,
) -> str:
    source_type_key = str(source_type or "").strip().lower()
    if decision == INGESTION_DECISION_EXCLUDE:
        return "not_applicable"
    if decision == INGESTION_DECISION_REVISION:
        return "revision_instruction"
    if family == "normativa":
        if source_type_key in {
            "ley",
            "decreto",
            "resolucion",
            "concepto",
            "sentencia",
            "formulario_oficial",
            "formulario_oficial_pdf",
            "official_primary",
        }:
            return "primary_legal_authority"
        return "normative_authority_unknown_shape"
    if family == "interpretacion":
        if source_type_key == "official_secondary":
            return "secondary_official_authority"
        if source_type_key in {"analysis", "commentary"}:
            return "expert_interpretive_authority"
        return "interpretive_authority_unknown_shape"
    if family == "practica":
        return "operational_practice_authority"
    return "authority_unknown"


def _infer_ambiguity_flags(
    *,
    decision: str,
    family: str,
    knowledge_class: str,
    source_type: str | None,
    graph_target: bool,
    graph_parse_ready: bool,
    vocabulary_status: str | None,
    base_doc_target: str | None,
) -> tuple[str, ...]:
    flags: list[str] = []
    if decision == INGESTION_DECISION_INCLUDE:
        if family == "unknown":
            flags.append("family_unknown")
        if knowledge_class == "unknown":
            flags.append("knowledge_class_unknown")
        if str(source_type or "").strip().lower() in {"", "unknown"}:
            flags.append("source_type_unknown")
        if vocabulary_status == "custom_topic_pending_vocab":
            flags.append("custom_topic_pending_vocab")
        elif vocabulary_status == "unassigned":
            flags.append("vocabulary_unassigned")
        if graph_target and not graph_parse_ready:
            flags.append("graph_target_not_parse_ready")
    elif decision == INGESTION_DECISION_REVISION:
        flags.append("revision_candidate_requires_merge_review")
        if not (base_doc_target or "").strip():
            flags.append("revision_target_missing")
    return tuple(flags)


def _infer_review_priority(
    *,
    decision: str,
    ambiguity_flags: Iterable[str],
) -> str:
    if decision == INGESTION_DECISION_EXCLUDE:
        return "none"
    flags = set(ambiguity_flags)
    if flags & CRITICAL_RECON_FLAGS:
        return "critical"
    if decision == INGESTION_DECISION_REVISION or flags & HIGH_RECON_FLAGS:
        return "high"
    if flags & MEDIUM_RECON_FLAGS:
        return "medium"
    return "none"


def _infer_source_origin(path: Path, corpus_root: Path) -> str:
    relative_parts = Path(_relative_path(path, corpus_root)).parts
    if not relative_parts:
        return _normalize_token(corpus_root.name)
    first_part = _normalize_token(relative_parts[0])
    if first_part in CORPUS_FAMILY_ALIASES:
        return _normalize_token(corpus_root.name)
    return first_part


def _infer_corpus_family(path: Path, *, markdown: str, corpus_root: Path) -> str:
    relative_path = _relative_path(path, corpus_root)
    candidate_parts = [corpus_root.name, *Path(relative_path).parts[:-1], path.stem]
    for part in candidate_parts:
        alias = CORPUS_FAMILY_ALIASES.get(_normalize_token(part))
        if alias:
            return alias

    content_norm = _normalize_search_blob(markdown[:4000])
    if _contains_any(
        content_norm,
        ("estatuto tributario", "articulo", "ley ", "decreto ", "resolucion ", "concepto dian"),
    ):
        return "normativa"
    if _contains_any(
        content_norm,
        ("paso a paso", "checklist", "guia operativa", "en loggro", "calendario operativo"),
    ):
        return "practica"
    if _contains_any(
        content_norm,
        ("analisis", "comentario", "experto", "guia profesional"),
    ):
        return "interpretacion"
    return "unknown"


def _infer_source_type(path: Path, *, markdown: str, family: str) -> str:
    path_norm = _normalize_token(str(path))
    content_norm = _normalize_search_blob(markdown[:2000])

    if family == "normativa":
        for marker, source_type in NORMATIVE_SOURCE_MARKERS:
            marker_norm = _normalize_token(marker)
            if marker_norm in path_norm or _normalize_search_blob(marker) in content_norm:
                return source_type
        return "official_primary"

    if family == "interpretacion":
        if "analisis" in path_norm or "analisis" in content_norm:
            return "analysis"
        if "comentario" in path_norm or "comentario" in content_norm:
            return "commentary"
        return "official_secondary"

    if family == "practica":
        for marker, source_type in PRACTICE_SOURCE_MARKERS.items():
            marker_norm = _normalize_token(marker)
            if marker_norm in path_norm or _normalize_search_blob(marker) in content_norm:
                return source_type
        return "guia_operativa"

    return "unknown"


def _infer_vocabulary_labels(
    path: Path,
    *,
    markdown: str,
) -> tuple[str | None, str | None, str, str]:
    taxonomy_version = topic_taxonomy_version()
    normalized_path = _normalize_token(str(path))
    normalized_stem = _normalize_token(path.stem)
    normalized_title = _normalize_token(_infer_title_hint(path, markdown=markdown))
    token_set = {
        token
        for token in (normalized_path + "_" + normalized_title).split("_")
        if token
    }

    best_match = None
    best_score = 0
    for entry in iter_ingestion_topic_entries():
        alias_score = max(
            _score_vocabulary_alias_match(
                alias,
                token_set=token_set,
                normalized_path=normalized_path,
                normalized_stem=normalized_stem,
                normalized_title=normalized_title,
            )
            for alias in entry.all_ingestion_aliases()
        )
        path_prefix_score = max(
            (
                _score_vocabulary_path_prefix_match(
                    prefix,
                    normalized_path=normalized_path,
                )
                for prefix in entry.allowed_path_prefixes
            ),
            default=0,
        )
        score = max(alias_score, path_prefix_score)
        if score > best_score:
            best_match = entry
            best_score = score

    if best_match is None:
        return None, None, "unassigned", taxonomy_version
    if best_match.parent_key:
        return (
            best_match.parent_key,
            best_match.key,
            best_match.vocabulary_status,
            taxonomy_version,
        )
    return best_match.key, None, best_match.vocabulary_status, taxonomy_version


def _is_revision_candidate(*, path: Path, markdown: str) -> bool:
    file_name_norm = _normalize_token(path.name)
    if any(marker in file_name_norm for marker in REVISION_FILENAME_MARKERS):
        return True
    header = "\n".join(markdown.splitlines()[:40])
    if REVISION_HEADING_RE.search(header):
        return True
    return any(pattern.search(header) for pattern in REVISION_DIRECTIVE_PATTERNS)


def _infer_revision_base_doc_target(
    *,
    path: Path,
    markdown: str,
    corpus_root: Path,
) -> str | None:
    hints: list[str] = []
    explicit_hint = _extract_explicit_base_doc_target(markdown)
    if explicit_hint:
        hints.append(explicit_hint)
    hints.extend(_infer_filename_base_doc_hints(path))

    for hint in hints:
        resolved = _resolve_base_doc_target_hint(
            hint,
            source_path=path,
            corpus_root=corpus_root,
        )
        if resolved:
            return resolved
    return explicit_hint


def _extract_explicit_base_doc_target(markdown: str) -> str | None:
    header = "\n".join(markdown.splitlines()[:40])
    for pattern in REVISION_DIRECTIVE_PATTERNS:
        match = pattern.search(header)
        if not match:
            continue
        cleaned = _clean_base_doc_target_hint(match.group(1))
        if cleaned:
            return cleaned
    return None


def _infer_filename_base_doc_hints(path: Path) -> list[str]:
    stem = path.stem
    hints: list[str] = []
    for pattern in (
        r"(?i)(?P<hint>seccion-\d+)[-_](?:patch|upsert)\b",
        r"(?i)(?:^|[_-])(?:patch|upsert)[-_: ]+(?P<hint>seccion-\d+)\b",
        r"(?i)(?P<hint>[A-Z]{2,}-[NEL]\d{2}|[A-Z]{2,}-L\d{2}|[A-Z]-CRI|T-[A-Z])[-_](?:patch|upsert)\b",
        r"(?i)(?:^|[_-])(?:patch|upsert)[-_: ]+(?P<hint>[A-Z]{2,}-[NEL]\d{2}|[A-Z]{2,}-L\d{2}|[A-Z]-CRI|T-[A-Z])\b",
    ):
        match = re.search(pattern, stem)
        if match:
            hint = match.group("hint").strip()
            if hint and hint not in hints:
                hints.append(hint)

    stripped_stem = re.sub(r"(?i)(?:^|[_-])(?:patch|upsert|errata)(?:[_-]|$)", "-", stem)
    stripped_stem = re.sub(r"(?i)^[A-Z]-\d+[_-]", "", stripped_stem)
    stripped_stem = stripped_stem.strip(" _-:")
    if stripped_stem and stripped_stem != stem and stripped_stem not in hints:
        hints.append(stripped_stem)
    return hints


def _resolve_base_doc_target_hint(
    hint: str,
    *,
    source_path: Path,
    corpus_root: Path,
) -> str | None:
    cleaned = _clean_base_doc_target_hint(hint)
    if not cleaned:
        return None

    direct_path = corpus_root / cleaned
    if direct_path.is_file() and direct_path != source_path:
        return _relative_path(direct_path, corpus_root)

    sibling_path = source_path.parent / cleaned
    if sibling_path.is_file() and sibling_path != source_path:
        return _relative_path(sibling_path, corpus_root)

    basename = Path(cleaned).name
    normalized_hint = _normalize_token(Path(cleaned).stem or cleaned)
    hint_tokens = {token for token in normalized_hint.split("_") if len(token) > 1}
    candidates: list[tuple[int, str]] = []

    for candidate in corpus_root.rglob("*.md"):
        if candidate == source_path:
            continue
        if _is_revision_named_path(candidate):
            continue
        if "deprecated" in {_normalize_token(part) for part in candidate.parts}:
            continue

        relative = _relative_path(candidate, corpus_root)
        normalized_relative = _normalize_token(relative)
        normalized_name = _normalize_token(candidate.stem)
        candidate_tokens = {token for token in normalized_relative.split("_") if len(token) > 1}
        score = 0
        if basename and candidate.name.lower() == basename.lower():
            score += 120
        if normalized_name == normalized_hint:
            score += 80
        if normalized_hint and normalized_hint in normalized_relative:
            score += 50
        score += 10 * len(hint_tokens & candidate_tokens)
        if score:
            candidates.append((score, relative))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (-item[0], item[1]))
    best_score, best_relative = candidates[0]
    if len(candidates) == 1 or best_score > candidates[1][0]:
        return best_relative
    return None


def _clean_base_doc_target_hint(value: str) -> str:
    cleaned = str(value or "").strip().strip("*`\"' ")
    match = re.search(r"([^()\n]+?\.md)\b", cleaned, re.IGNORECASE)
    if match:
        cleaned = match.group(1).strip()
    cleaned = cleaned.removeprefix("knowledge_base/").strip()
    cleaned = cleaned.lstrip("./")
    return cleaned


def _is_revision_named_path(path: Path) -> bool:
    return any(marker in _normalize_token(path.name) for marker in REVISION_FILENAME_MARKERS)


def _score_vocabulary_alias_match(
    alias: str,
    token_set: set[str],
    normalized_path: str,
    normalized_stem: str,
    normalized_title: str,
) -> int:
    alias_norm = _normalize_token(alias)
    alias_tokens = tuple(token for token in alias_norm.split("_") if len(token) > 1)
    if not alias_tokens:
        return 0
    if normalized_stem == alias_norm:
        return 5
    if alias_norm in normalized_stem:
        return 4
    if alias_norm in normalized_path:
        return 3
    if alias_norm in normalized_title:
        return 2
    if len(alias_tokens) == 1:
        return 1 if alias_tokens[0] in token_set else 0
    return 1 if all(token in token_set for token in alias_tokens) else 0


def _score_vocabulary_path_prefix_match(
    prefix: str,
    *,
    normalized_path: str,
) -> int:
    prefix_norm = _normalize_token(prefix)
    if not prefix_norm:
        return 0
    if prefix_norm in normalized_path:
        return 6 + min(len(prefix_norm.split("_")), 3)
    return 0


def _relative_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


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
