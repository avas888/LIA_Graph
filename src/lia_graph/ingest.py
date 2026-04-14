from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from .ingestion import (
    build_graph_load_plan,
    classify_edge_candidates,
    extract_edge_candidates,
    load_graph_plan,
    parse_article_documents,
)


DEFAULT_CORPUS_DIR = Path("knowledge_base")
DEFAULT_ARTIFACTS_DIR = Path("artifacts")
DEFAULT_PATTERN = "*"

INGESTION_DECISION_INCLUDE = "include_corpus"
INGESTION_DECISION_REVISION = "revision_candidate"
INGESTION_DECISION_EXCLUDE = "exclude_internal"

GRAPH_TARGET_FAMILIES = frozenset({"normativa"})
GRAPH_PARSE_STRATEGIES = frozenset({"markdown_graph_parse"})
TEXT_DIRECT_PARSE_EXTENSIONS = frozenset({".md", ".markdown"})
TEXT_INVENTORY_EXTENSIONS = frozenset({".txt", ".csv", ".json", ".yaml", ".yml", ".xml", ".html"})
BINARY_DOCUMENT_EXTENSIONS = frozenset({".pdf", ".doc", ".docx"})
HELPER_CODE_EXTENSIONS = frozenset({".py", ".js", ".ts", ".pyc"})

CORPUS_FAMILY_ALIASES = {
    "normativa": "normativa",
    "normative_base": "normativa",
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
    "interpretative_guidance": "interpretacion",
    "expertos": "interpretacion",
    "experts": "interpretacion",
    "industry_guidance": "interpretacion",
    "analisis": "interpretacion",
    "practica": "practica",
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

CANONICAL_TOPIC_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "retencion_en_la_fuente",
        (
            "retencion_en_la_fuente",
            "retencion",
            "retenciones",
            "retefuente",
            "retefte",
            "reteiva",
            "autoretencion",
            "autoretenciones",
            "agente_retenedor",
        ),
    ),
    (
        "nomina_y_laboral",
        (
            "nomina_y_laboral",
            "nomina",
            "laboral",
            "seguridad_social",
            "parafiscales",
            "nomina_electronica",
            "prestaciones",
            "contrato_laboral",
        ),
    ),
    (
        "procedimiento_tributario",
        (
            "procedimiento_tributario",
            "rut",
            "sancion",
            "sanciones",
            "devolucion",
            "devoluciones",
            "compensacion",
            "fiscalizacion",
            "plazos",
            "calendario_tributario",
            "correccion",
            "firmeza",
            "recurso",
        ),
    ),
    (
        "niif_y_estados_financieros",
        (
            "niif_y_estados_financieros",
            "niif",
            "ifrs",
            "estados_financieros",
            "contabilidad",
            "ctcp",
            "impuesto_diferido",
            "marco_tecnico",
        ),
    ),
    (
        "declaracion_renta",
        (
            "declaracion_renta",
            "renta",
            "rentas_exentas",
            "ganancia_ocasional",
            "conciliacion_fiscal",
            "beneficio_auditoria",
            "costos_y_deducciones",
            "patrimonio",
        ),
    ),
    (
        "iva",
        (
            "iva",
            "impuesto_a_las_ventas",
            "impuesto_ventas",
            "reteiva",
        ),
    ),
)

CUSTOM_TOPIC_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("regimen_simple", ("regimen_simple", "simple", "rst")),
    (
        "facturacion_electronica",
        ("facturacion_electronica", "factura_electronica", "radian"),
    ),
    (
        "informacion_exogena",
        ("informacion_exogena", "exogena", "medios_magneticos"),
    ),
    ("ica_y_municipales", ("ica_y_municipales", "ica", "reteica", "predial")),
    (
        "precios_de_transferencia",
        ("precios_de_transferencia", "transferencia", "transfer_pricing"),
    ),
    ("cambiario", ("cambiario", "banrep", "inversion_extranjera")),
    (
        "impuesto_patrimonio_personas_naturales",
        ("impuesto_patrimonio", "patrimonio_personas_naturales"),
    ),
)

REVISION_FILENAME_MARKERS = ("patch", "upsert")
REVISION_TEXT_MARKERS = (
    "insertar en",
    "base doc",
    "documento base",
    "aplicar sobre",
    "mergear en",
    "actualizar este documento",
    "upsert",
    "patch",
)
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
    extension: str
    text_extractable: bool
    parse_strategy: str
    document_archetype: str
    ingestion_decision: str
    decision_reason: str
    family: str | None = None
    knowledge_class: str | None = None
    source_type: str | None = None
    graph_target: bool = False
    graph_parse_ready: bool = False
    topic_key: str | None = None
    subtopic_key: str | None = None
    vocabulary_status: str | None = None
    base_doc_target: str | None = None
    markdown: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_origin": self.source_origin,
            "source_path": self.source_path,
            "relative_path": self.relative_path,
            "extension": self.extension,
            "text_extractable": self.text_extractable,
            "parse_strategy": self.parse_strategy,
            "document_archetype": self.document_archetype,
            "ingestion_decision": self.ingestion_decision,
            "decision_reason": self.decision_reason,
            "family": self.family,
            "knowledge_class": self.knowledge_class,
            "source_type": self.source_type,
            "graph_target": self.graph_target,
            "graph_parse_ready": self.graph_parse_ready,
            "topic_key": self.topic_key,
            "subtopic_key": self.subtopic_key,
            "vocabulary_status": self.vocabulary_status,
            "base_doc_target": self.base_doc_target,
        }


@dataclass(frozen=True)
class CorpusDocument:
    source_origin: str
    source_path: str
    relative_path: str
    extension: str
    text_extractable: bool
    parse_strategy: str
    document_archetype: str
    family: str
    knowledge_class: str
    source_type: str
    graph_target: bool
    graph_parse_ready: bool
    topic_key: str | None
    subtopic_key: str | None
    vocabulary_status: str
    markdown: str

    @classmethod
    def from_audit_record(cls, record: CorpusAuditRecord) -> "CorpusDocument":
        return cls(
            source_origin=record.source_origin,
            source_path=record.source_path,
            relative_path=record.relative_path,
            extension=record.extension,
            text_extractable=record.text_extractable,
            parse_strategy=record.parse_strategy,
            document_archetype=record.document_archetype,
            family=record.family or "unknown",
            knowledge_class=record.knowledge_class or "unknown",
            source_type=record.source_type or "unknown",
            graph_target=record.graph_target,
            graph_parse_ready=record.graph_parse_ready,
            topic_key=record.topic_key,
            subtopic_key=record.subtopic_key,
            vocabulary_status=record.vocabulary_status or "unassigned",
            markdown=record.markdown or "",
        )

    def markdown_document(self) -> tuple[str, str]:
        return (self.source_path, self.markdown)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_origin": self.source_origin,
            "source_path": self.source_path,
            "relative_path": self.relative_path,
            "extension": self.extension,
            "text_extractable": self.text_extractable,
            "parse_strategy": self.parse_strategy,
            "document_archetype": self.document_archetype,
            "family": self.family,
            "knowledge_class": self.knowledge_class,
            "source_type": self.source_type,
            "graph_target": self.graph_target,
            "graph_parse_ready": self.graph_parse_ready,
            "topic_key": self.topic_key,
            "subtopic_key": self.subtopic_key,
            "vocabulary_status": self.vocabulary_status,
        }


def load_active_index_generation(*args: Any, **kwargs: Any) -> dict[str, Any] | None:
    return None


def scaffold_graph_build(
    markdown_documents: Iterable[tuple[str, str]],
) -> dict[str, Any]:
    articles = parse_article_documents(markdown_documents)
    raw_edges = extract_edge_candidates(articles)
    typed_edges = classify_edge_candidates(raw_edges)
    load_plan = build_graph_load_plan(articles, typed_edges)
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
    revision_candidates_path = artifacts_root / "revision_candidates.json"
    excluded_files_path = artifacts_root / "excluded_files.json"
    canonical_manifest_path = artifacts_root / "canonical_corpus_manifest.json"
    corpus_inventory_path = artifacts_root / "corpus_inventory.json"

    _write_json(
        corpus_audit_report_path,
        _build_corpus_audit_report(corpus_dir=root, rows=audit_rows),
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

    articles = parse_article_documents(graph_documents)
    raw_edges = extract_edge_candidates(articles)
    typed_edges = classify_edge_candidates(raw_edges)
    load_plan = build_graph_load_plan(articles, typed_edges)
    load_execution = load_graph_plan(load_plan).to_dict()

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

    return {
        "ok": True,
        "corpus_dir": str(root),
        "artifacts_dir": str(artifacts_root),
        "pattern": pattern,
        "scanned_file_count": len(audit_rows),
        "decision_counts": _decision_counts(audit_rows),
        "document_count": len(corpus_documents),
        "document_family_counts": _family_counts(corpus_documents),
        "knowledge_class_counts": _knowledge_class_counts(corpus_documents),
        "source_type_counts": _source_type_counts(corpus_documents),
        "extension_counts": _extension_counts(audit_rows),
        "parse_strategy_counts": _parse_strategy_counts(audit_rows),
        "document_archetype_counts": _document_archetype_counts(audit_rows),
        "graph_target_families": sorted(GRAPH_TARGET_FAMILIES),
        "graph_target_document_count": sum(1 for doc in corpus_documents if doc.graph_target),
        "graph_parse_ready_document_count": len(graph_documents),
        "article_count": len(articles),
        "raw_edge_count": len(raw_edges),
        "typed_edge_count": len(typed_edges),
        "files": {
            "corpus_audit_report": str(corpus_audit_report_path),
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
    }


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
    cli.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return cli


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = materialize_graph_artifacts(
            corpus_dir=Path(args.corpus_dir),
            artifacts_dir=Path(args.artifacts_dir),
            pattern=args.pattern,
        )
    except (FileNotFoundError, NotADirectoryError) as exc:
        payload = {"ok": False, "error": "corpus_unavailable", "message": str(exc)}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"Phase 2 graph artifact materialization failed: {exc}")
        return 2

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
    ingestion_decision, decision_reason, base_doc_target, document_archetype = _classify_ingestion_decision(
        path=path,
        relative_path=relative_path,
        markdown=markdown,
        extension=extension,
        text_extractable=text_extractable,
    )

    family = _infer_corpus_family(path, markdown=markdown, corpus_root=corpus_root)
    knowledge_class = KNOWLEDGE_CLASS_BY_FAMILY.get(family, "unknown")
    source_type = _infer_source_type(path, markdown=markdown, family=family)
    topic_key, subtopic_key, vocabulary_status = _infer_vocabulary_labels(
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
    graph_parse_ready = graph_target and parse_strategy in GRAPH_PARSE_STRATEGIES

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
        extension=extension,
        text_extractable=text_extractable,
        parse_strategy=parse_strategy,
        document_archetype=document_archetype,
        ingestion_decision=ingestion_decision,
        decision_reason=decision_reason,
        family=family,
        knowledge_class=knowledge_class,
        source_type=source_type,
        graph_target=graph_target,
        graph_parse_ready=graph_parse_ready,
        topic_key=topic_key,
        subtopic_key=subtopic_key,
        vocabulary_status=vocabulary_status,
        base_doc_target=base_doc_target,
        markdown=markdown,
    )


def _classify_ingestion_decision(
    *,
    path: Path,
    relative_path: str,
    markdown: str,
    extension: str,
    text_extractable: bool,
) -> tuple[str, str, str | None, str]:
    file_name_norm = _normalize_token(path.name)
    content_norm = _normalize_search_blob(markdown)
    path_parts = tuple(_normalize_token(part) for part in Path(relative_path).parts)

    if path.name.lower() == "state.md":
        return (
            INGESTION_DECISION_EXCLUDE,
            "Excluded working state file.",
            None,
            "working_note",
        )
    if path.name.lower() == "readme.md":
        return (
            INGESTION_DECISION_EXCLUDE,
            "Excluded working README or implementation note.",
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
    if _contains_any(content_norm, ("gap", "audit gap", "gap analysis", "analisis gap")):
        return (
            INGESTION_DECISION_EXCLUDE,
            "Excluded gap-analysis or audit-analysis working material.",
            None,
            "gap_analysis",
        )
    if _contains_any(content_norm, INTERNAL_GOVERNANCE_MARKERS):
        return (
            INGESTION_DECISION_EXCLUDE,
            "Excluded governance or taxonomy-control document.",
            None,
            "governance_doc",
        )
    if "errata" in file_name_norm:
        return (
            INGESTION_DECISION_REVISION,
            "Classified as errata or correction material that should merge into a base document first.",
            _extract_base_doc_target(markdown),
            "errata",
        )
    if any(marker in file_name_norm for marker in REVISION_FILENAME_MARKERS) or _contains_any(
        content_norm,
        REVISION_TEXT_MARKERS,
    ):
        return (
            INGESTION_DECISION_REVISION,
            "Classified as patch/update material that should merge into a base document first.",
            _extract_base_doc_target(markdown),
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
    print(f"- graph_target_families: {', '.join(result['graph_target_families'])}")
    print(f"- graph_target_documents: {result['graph_target_document_count']}")
    print(f"- graph_parse_ready_documents: {result['graph_parse_ready_document_count']}")
    print(f"- articles: {result['article_count']}")
    print(f"- raw_edges: {result['raw_edge_count']}")
    print(f"- typed_edges: {result['typed_edge_count']}")
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


def _infer_vocabulary_labels(path: Path, *, markdown: str) -> tuple[str | None, str | None, str]:
    normalized_path = _normalize_token(str(path))
    normalized_title = _normalize_token(markdown.splitlines()[0] if markdown.splitlines() else "")
    token_set = {
        token
        for token in (normalized_path + "_" + normalized_title).split("_")
        if token
    }

    for topic_key, aliases in CANONICAL_TOPIC_ALIASES:
        if any(_matches_vocabulary_alias(alias, token_set, normalized_path, normalized_title) for alias in aliases):
            return topic_key, None, "ratified_v1_2"

    for topic_key, aliases in CUSTOM_TOPIC_ALIASES:
        if any(_matches_vocabulary_alias(alias, token_set, normalized_path, normalized_title) for alias in aliases):
            return topic_key, None, "custom_topic_pending_vocab"

    return None, None, "unassigned"


def _extract_base_doc_target(markdown: str) -> str | None:
    for pattern in (
        r"(?im)^\s*(?:insertar en|base doc|documento base|target)\s*:\s*(.+?)\s*$",
        r"(?im)^\s*(?:aplicar sobre)\s+(.+?)\s*$",
    ):
        match = re.search(pattern, markdown)
        if match:
            return match.group(1).strip()
    return None


def _matches_vocabulary_alias(
    alias: str,
    token_set: set[str],
    normalized_path: str,
    normalized_title: str,
) -> bool:
    alias_norm = _normalize_token(alias)
    alias_tokens = tuple(token for token in alias_norm.split("_") if token)
    if not alias_tokens:
        return False
    if len(alias_tokens) == 1:
        return alias_tokens[0] in token_set
    return alias_norm in normalized_path or alias_norm in normalized_title


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


def _vocabulary_status_counts(documents: Iterable[CorpusDocument]) -> dict[str, int]:
    counter = Counter(document.vocabulary_status for document in documents)
    return {key: counter[key] for key in sorted(counter)}


def _build_corpus_audit_report(
    *,
    corpus_dir: Path,
    rows: Iterable[CorpusAuditRecord],
) -> dict[str, Any]:
    audit_rows = tuple(rows)
    return {
        "corpus_dir": str(corpus_dir),
        "scanned_file_count": len(audit_rows),
        "decision_counts": _decision_counts(audit_rows),
        "source_origin_counts": _source_origin_counts(audit_rows),
        "extension_counts": _extension_counts(audit_rows),
        "parse_strategy_counts": _parse_strategy_counts(audit_rows),
        "document_archetype_counts": _document_archetype_counts(audit_rows),
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
        "decision": decision,
        "count": len(selected_rows),
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
        "scanned_file_count": len(audit_rows),
        "decision_counts": _decision_counts(audit_rows),
        "extension_counts": _extension_counts(audit_rows),
        "parse_strategy_counts": _parse_strategy_counts(audit_rows),
        "document_archetype_counts": _document_archetype_counts(audit_rows),
        "document_count": len(included_rows),
        "family_counts": _family_counts(included_rows),
        "knowledge_class_counts": _knowledge_class_counts(included_rows),
        "source_type_counts": _source_type_counts(included_rows),
        "graph_parse_ready_document_count": sum(1 for row in included_rows if row.graph_parse_ready),
        "vocabulary_status_counts": _vocabulary_status_counts(included_rows),
        "graph_target_families": sorted(GRAPH_TARGET_FAMILIES),
        "graph_target_document_count": sum(1 for row in included_rows if row.graph_target),
        "documents": [row.to_dict() for row in included_rows],
    }


def _build_canonical_corpus_manifest(
    *,
    corpus_dir: Path,
    documents: Iterable[CorpusDocument],
    rows: Iterable[CorpusAuditRecord],
) -> dict[str, Any]:
    included_rows = tuple(documents)
    revision_rows = tuple(
        row for row in rows if row.ingestion_decision == INGESTION_DECISION_REVISION
    )
    revisions_by_target: dict[str, list[CorpusAuditRecord]] = defaultdict(list)
    unresolved_revisions: list[CorpusAuditRecord] = []
    docs_by_relative = {doc.relative_path: doc for doc in included_rows}
    docs_by_source = {doc.source_path: doc for doc in included_rows}

    for row in revision_rows:
        target = (row.base_doc_target or "").strip()
        if not target:
            unresolved_revisions.append(row)
            continue
        if target in docs_by_relative or target in docs_by_source:
            revisions_by_target[target].append(row)
            continue
        unresolved_revisions.append(row)

    documents_payload: list[dict[str, Any]] = []
    for doc in included_rows:
        attached_revisions = revisions_by_target.get(doc.relative_path) or revisions_by_target.get(
            doc.source_path
        ) or []
        documents_payload.append(
            {
                **doc.to_dict(),
                "canonical_ready": True,
                "pending_revision_count": len(attached_revisions),
                "has_pending_revisions": bool(attached_revisions),
                "attached_revision_candidates": [row.to_dict() for row in attached_revisions],
            }
        )

    return {
        "corpus_dir": str(corpus_dir),
        "document_count": len(included_rows),
        "canonical_ready_count": len(included_rows),
        "documents_with_pending_revisions": sum(
            1 for row in documents_payload if row["has_pending_revisions"]
        ),
        "unresolved_revision_candidate_count": len(unresolved_revisions),
        "documents": documents_payload,
        "unresolved_revision_candidates": [row.to_dict() for row in unresolved_revisions],
    }


if __name__ == "__main__":
    raise SystemExit(main())
