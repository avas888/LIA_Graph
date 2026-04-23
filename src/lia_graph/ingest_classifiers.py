"""Per-path corpus audit classifier functions.

Extracted from `ingest.py` during granularize-v2 round 14. This module
owns the "decide what kind of corpus document this path is" pipeline:

  * ``_audit_single_file(path)`` — top-level per-file audit, produces
    a ``CorpusAuditRecord``.
  * ``_classify_ingestion_decision(record)`` — returns one of
    ``include_corpus`` / ``revision_candidate`` / ``exclude_internal``.
  * Inference helpers (`_infer_parse_strategy`, `_infer_source_tier`,
    `_infer_authority_level`, `_infer_ambiguity_flags`,
    `_infer_review_priority`, `_infer_source_origin`,
    `_infer_corpus_family`, `_infer_source_type`,
    `_infer_vocabulary_labels`) + the revision-attachment resolver
    family (`_resolve_base_doc_target_hint` et al).

All taxonomy constants live in `ingest_constants`; this module imports
them and declares no module-level state beyond pure functions.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path
from typing import Any

from .ingest_constants import (
    BINARY_DOCUMENT_EXTENSIONS,
    CORPUS_FAMILY_ALIASES,
    CorpusAuditRecord,
    CRITICAL_RECON_FLAGS,
    EXCLUDED_FILENAMES,
    EXCLUDED_PATH_PREFIXES,
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
from .instrumentation import emit_event
from .source_tiers import source_tier_key_for_row
from .topic_taxonomy import (
    iter_ingestion_topic_entries,
    normalize_topic_key,
    topic_taxonomy_version,
)


def _relative_path(path: Path, root: Path) -> str:
    """Return `path` as a string relative to `root`, or absolute str if outside."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


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
    # ingestionfix_v2 §4 Phase 3: path-inferred topic fallback.
    # When the deterministic alias/prefix score yields no topic, use the
    # first segment of the corpus-root-relative path (which is itself a
    # curated folder layout that mirrors topic_taxonomy.json keys).
    # Only overrides when the path segment resolves to a known taxonomy
    # key — unknown folders stay null to avoid false positives.
    if topic_key is None:
        path_inferred = coerce_topic_from_path(relative_path)
        if path_inferred:
            topic_key = path_inferred
            if vocabulary_status in (None, "unassigned"):
                vocabulary_status = "path_inferred_v1"
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
    # C5 admission-gate tighteners — run BEFORE any other heuristic so
    # binary assets / structural manifests / derogated laws never reach
    # the graph-parse cascade. Most-specific reason wins; only one event
    # fires per excluded file (see ``_audit_admission_rejection``).
    admission = _audit_admission_rejection(
        path=path,
        relative_path=relative_path,
        extension=extension,
    )
    if admission is not None:
        return admission

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


def _audit_admission_rejection(
    *,
    path: Path,
    relative_path: str,
    extension: str,
) -> tuple[str, str, str | None, str] | None:
    """Return an ``exclude_internal`` verdict for C5 admission rejects.

    Most-specific reason wins — path-prefix (``derogated_law``) beats
    filename (``structural_manifest``) beats extension
    (``binary_asset``) — and exactly one ``audit.admission.rejected``
    event is emitted per excluded file.

    Returns ``None`` when the file is admissible (the normal heuristic
    cascade will decide).
    """
    normalized_relative = _normalize_relative_path(relative_path)

    for prefix in EXCLUDED_PATH_PREFIXES:
        if _relative_path_matches_prefix(normalized_relative, prefix):
            return _emit_admission_rejection(
                relative_path=relative_path,
                reason="derogated_law",
                document_archetype="derogated_law",
            )

    if path.name in EXCLUDED_FILENAMES:
        return _emit_admission_rejection(
            relative_path=relative_path,
            reason="structural_manifest",
            document_archetype="structural_manifest",
        )

    if extension.lower() in {".svg", ".png", ".jpg", ".jpeg", ".webp"}:
        # PDFs/DOC(X) are legitimate corpus-document formats and keep
        # their existing downstream handling; the C5 tightener is only
        # about image-style binary assets that sit alongside prose.
        return _emit_admission_rejection(
            relative_path=relative_path,
            reason="binary_asset",
            document_archetype="binary_asset",
        )

    return None


def _normalize_relative_path(relative_path: str) -> str:
    """Return a POSIX-style, leading-slash-stripped view of ``relative_path``.

    Tests write paths with forward slashes already, but audit rows built
    on Windows (or from absolute fallbacks) can carry backslashes or a
    leading ``/``. The prefix check is resilient to both.
    """
    normalized = str(relative_path or "").replace("\\", "/")
    return normalized.lstrip("/")


def _relative_path_matches_prefix(normalized_relative: str, prefix: str) -> bool:
    """Return True iff ``prefix`` appears as a path-segment slice.

    The match is segment-aware: ``LEYES/DEROGADAS/`` matches
    ``CORE ya Arriba/LEYES/DEROGADAS/foo.md`` at the segment boundary
    but NOT ``CORE ya Arriba/LEYES/DEROGADAS_foo/bar.md``. Prefixes
    are expected to be trailing-slash terminated (see
    ``EXCLUDED_PATH_PREFIXES``).
    """
    prefix_clean = (prefix or "").replace("\\", "/").lstrip("/")
    if not prefix_clean:
        return False
    if normalized_relative.startswith(prefix_clean):
        return True
    # Segment-aware search — match only after a ``/`` boundary so a
    # prefix never lands inside a directory name.
    return ("/" + prefix_clean) in ("/" + normalized_relative)


def _emit_admission_rejection(
    *,
    relative_path: str,
    reason: str,
    document_archetype: str,
) -> tuple[str, str, str | None, str]:
    """Emit the ``audit.admission.rejected`` trace + build the exclude tuple.

    ``decision_reason`` is deliberately the short machine-readable tag
    (``binary_asset`` / ``structural_manifest`` / ``derogated_law``) —
    downstream audit-report consumers pivot on it (spec C5).
    """
    try:
        emit_event(
            "audit.admission.rejected",
            {"relative_path": relative_path, "reason": reason},
        )
    except Exception:
        # Instrumentation must never break ingestion.
        pass
    return (
        INGESTION_DECISION_EXCLUDE,
        reason,
        None,
        document_archetype,
    )


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


_PREFIX_PARENT_TOPIC_MAP_PATH = Path("config/prefix_parent_topic_map.json")


@lru_cache(maxsize=1)
def _load_prefix_parent_topic_map() -> tuple[tuple[str, str], ...]:
    """Load the filename-prefix -> parent_topic_key lookup table.

    Sorted longest-prefix-first so that ``RET-`` wins over ``RE-`` when both
    exist. Returns prefixes in lowercase (the lookup is case-insensitive).
    Returns an empty tuple if the config file is missing or malformed — the
    classifier falls through to the existing heuristics in that case.
    """
    candidates = [_PREFIX_PARENT_TOPIC_MAP_PATH]
    repo_root = Path(__file__).resolve().parents[2]
    candidates.append(repo_root / _PREFIX_PARENT_TOPIC_MAP_PATH)
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return ()
        raw_mappings = payload.get("mappings") or {}
        if not isinstance(raw_mappings, dict):
            return ()
        pairs: list[tuple[str, str]] = []
        for prefix, parent_topic in raw_mappings.items():
            if not isinstance(prefix, str) or not isinstance(parent_topic, str):
                continue
            norm_prefix = prefix.strip().lower()
            norm_parent = parent_topic.strip().lower()
            if not norm_prefix or not norm_parent:
                continue
            pairs.append((norm_prefix, norm_parent))
        # Longest prefix first so "RET-" beats "RE-" on lookup.
        pairs.sort(key=lambda item: (-len(item[0]), item[0]))
        return tuple(pairs)
    return ()


def _lookup_parent_topic_by_filename_prefix(filename: str) -> str | None:
    """Return the parent_topic_key mapped by the filename prefix, if any.

    Case-insensitive. Uses longest-prefix-wins semantics. Returns ``None``
    when no prefix in the lookup matches the filename.
    """
    if not filename:
        return None
    name = filename.strip().lower()
    for prefix, parent_topic in _load_prefix_parent_topic_map():
        if name.startswith(prefix):
            return parent_topic
    return None


def coerce_topic_from_path(relative_path: str | Path) -> str | None:
    """Infer a taxonomy topic_key from the first segment of ``relative_path``.

    Used as a post-classifier fallback (ingestionfix_v2 §4 Phase 3): when the
    deterministic regex pass and the PASO 4 LLM both return ``topic_key=None``,
    the corpus folder layout (e.g. ``retencion_en_la_fuente/X.md`` or
    ``declaracion_renta/...``) is itself a strong signal.

    Returns the canonical ``topic_key`` when the first path segment resolves
    to a known taxonomy key (directly or via any alias); otherwise ``None``.
    This guarantees the hook never invents a topic — unknown top-level
    folders stay null rather than getting a false-positive assignment.
    """
    if not relative_path:
        return None
    try:
        parts = Path(str(relative_path)).parts
    except (TypeError, ValueError):
        return None
    if not parts:
        return None
    first_part = parts[0].strip()
    if not first_part:
        return None
    return normalize_topic_key(first_part)


def _infer_vocabulary_labels(
    path: Path,
    *,
    markdown: str,
) -> tuple[str | None, str | None, str, str]:
    taxonomy_version = topic_taxonomy_version()

    # Static prefix lookup — takes precedence over the alias-score heuristic
    # below, which otherwise confuses numeric substrings in the path with
    # parent_topic keywords (e.g. "II-1429-2010" routed to "iva"). Rationale:
    # scripts/curator-decisions-abril-2026/strategy-memo.md §2.2.
    prefix_match = _lookup_parent_topic_by_filename_prefix(path.name)
    if prefix_match:
        return prefix_match, None, "ratified_v1_2", taxonomy_version

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
