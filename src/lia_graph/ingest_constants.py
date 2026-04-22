"""Shared taxonomy constants + audit-record dataclasses for ingest.py.

Extracted during granularize-v2 round 14. Both `ingest_classifiers` and
`ingest_reports` import from here to stay decoupled from the host
ingest.py entrypoint (which re-imports everything for back-compat).

No functions — purely declarative data: decision values, family/source/
extension taxonomies, revision markers, internal README/governance
hints, review-priority order, reconnaissance-flag tiers, plus the
`CorpusAuditRecord` and `CorpusDocument` dataclasses.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


INGESTION_DECISION_INCLUDE = "include_corpus"
INGESTION_DECISION_REVISION = "revision_candidate"
INGESTION_DECISION_EXCLUDE = "exclude_internal"

GRAPH_TARGET_FAMILIES = frozenset({"normativa"})
GRAPH_PARSE_STRATEGIES = frozenset({"markdown_graph_parse"})
TEXT_DIRECT_PARSE_EXTENSIONS = frozenset({".md", ".markdown"})
TEXT_INVENTORY_EXTENSIONS = frozenset({".txt", ".csv", ".json", ".yaml", ".yml", ".xml", ".html"})
BINARY_DOCUMENT_EXTENSIONS = frozenset(
    {".pdf", ".doc", ".docx", ".svg", ".png", ".jpg", ".jpeg", ".webp"}
)
HELPER_CODE_EXTENSIONS = frozenset({".py", ".js", ".ts", ".pyc"})

# C5 — audit-admission tighteners.
#
# ``EXCLUDED_FILENAMES`` is a basename allow-list of structural manifest
# JSONs that live alongside `form_guides/` prose but carry no
# accountant-facing content on their own (they are indexes/pointers
# regenerated from the prose). They must never enter graph-parse.
EXCLUDED_FILENAMES: frozenset[str] = frozenset(
    {
        "guide_manifest.json",
        "structured_guide.json",
        "sources.json",
        "interactive_map.json",
        "citation_profile.json",
    }
)

# ``EXCLUDED_PATH_PREFIXES`` is compared against the audit row's
# ``relative_path`` (POSIX-style, corpus-root-relative, no leading
# slash — see ``_relative_path`` in ``ingest_classifiers``). Entries
# here represent whole corpus subtrees that must be withheld from
# ingestion (e.g. derogated laws retained only for historical context).
# Keep prefixes trailing-slash terminated so they never match a
# sibling directory by accident (``LEYES/DEROGADAS/`` vs.
# ``LEYES/DEROGADAS_foo/``).
EXCLUDED_PATH_PREFIXES: tuple[str, ...] = (
    "LEYES/DEROGADAS/",
)

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
    requires_subtopic_review: bool = False

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
            requires_subtopic_review=False,
        )

    def markdown_document(self) -> tuple[str, str]:
        return (self.source_path, self.markdown)

    def with_subtopic(
        self,
        *,
        subtopic_key: str | None,
        requires_subtopic_review: bool,
        topic_key: str | None = None,
    ) -> "CorpusDocument":
        """Return a copy with the subtopic verdict replaced (frozen dataclass).

        If ``topic_key`` is provided and non-empty, overrides the legacy
        topic_key too — needed when the PASO 4 classifier's
        ``detected_topic`` is more specific than the regex legacy pass
        (common for interpretacion / practica / sectoral docs).
        """
        from dataclasses import replace

        overrides: dict[str, Any] = {
            "subtopic_key": subtopic_key,
            "requires_subtopic_review": bool(requires_subtopic_review),
        }
        if topic_key:
            overrides["topic_key"] = topic_key
        return replace(self, **overrides)

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
            "requires_subtopic_review": self.requires_subtopic_review,
        }
