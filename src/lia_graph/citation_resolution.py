from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

from .normative_references import (
    best_reference_metadata,
    extract_normative_reference_mentions,
    extract_normative_references,
    logical_doc_id,
    reference_identity as normative_reference_identity,
)
from .normative_taxonomy import classify_normative_document
from .practical_doc_indexing import (
    derive_practical_doc_metadata,
    derive_practical_identity_keys,
    is_allowed_practical_identity_key,
    read_referenceable_text,
)

CANONICAL_REFERENCE_RELATION_TYPES = {"canonical_for", "authoritative_variant"}
_FORM_GUIDE_HINT_TOKENS = ("guia", "guía", "instructivo", "diligenciar", "operativa", "manual", "plantilla")


@dataclass(frozen=True, slots=True)
class ReferenceMentionCandidate:
    reference_identity: str
    reference_key: str
    reference_type: str
    reference_text: str
    locator_text: str | None
    locator_kind: str | None
    locator_start: str | None
    locator_end: str | None
    context: str
    start: int
    end: int

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "reference_identity": self.reference_identity,
            "reference_key": self.reference_key,
            "reference_type": self.reference_type,
            "reference_text": self.reference_text,
            "locator_text": self.locator_text,
            "locator_kind": self.locator_kind,
            "locator_start": self.locator_start,
            "locator_end": self.locator_end,
            "context": self.context,
            "start": self.start,
            "end": self.end,
        }


@dataclass(frozen=True, slots=True)
class ReferenceMentionCollection:
    detected_count: int
    mentions: tuple[ReferenceMentionCandidate, ...]

    @property
    def unique_count(self) -> int:
        return len(self.mentions)


def _normalize_string_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",")]
    elif isinstance(value, (list, tuple, set)):
        items = [str(item).strip() for item in value]
    else:
        items = []
    return tuple(item for item in items if item)


def _reference_keys_from_texts(*values: Any) -> set[str]:
    keys: set[str] = set()
    for value in values:
        for reference in extract_normative_references(str(value or "")):
            key = str(reference.get("reference_key") or "").strip()
            if key:
                keys.add(key)
    return keys


def _coerce_reference_mention_candidate(value: Mapping[str, Any] | ReferenceMentionCandidate | None) -> ReferenceMentionCandidate | None:
    if isinstance(value, ReferenceMentionCandidate):
        return value
    if not isinstance(value, Mapping):
        return None
    identity = str(value.get("reference_identity") or normative_reference_identity(dict(value))).strip()
    key = str(value.get("reference_key") or "").strip()
    if not identity or not key:
        return None
    return ReferenceMentionCandidate(
        reference_identity=identity,
        reference_key=key,
        reference_type=str(value.get("reference_type") or "").strip(),
        reference_text=str(value.get("reference_text") or "").strip(),
        locator_text=str(value.get("locator_text") or "").strip() or None,
        locator_kind=str(value.get("locator_kind") or "").strip() or None,
        locator_start=str(value.get("locator_start") or "").strip() or None,
        locator_end=str(value.get("locator_end") or "").strip() or None,
        context=str(value.get("context") or "").strip(),
        start=int(value.get("start") or 0),
        end=int(value.get("end") or 0),
    )


def _build_row_citation(row: Mapping[str, Any]) -> Any | None:
    try:
        from .contracts import Citation, DocumentRecord

        doc = DocumentRecord.from_dict(dict(row))
        return Citation.from_document(doc)
    except Exception:
        return None


def _identity_seed_texts(row: Mapping[str, Any]) -> tuple[str, ...]:
    citation = _build_row_citation(row)
    return (
        str(row.get("title") or ""),
        str(citation.source_label or "") if citation is not None else "",
        str(citation.legal_reference or "") if citation is not None else "",
        str(row.get("notes") or ""),
        str(row.get("subtema") or ""),
    )


def _path_identity_seed_texts(row: Mapping[str, Any]) -> tuple[str, ...]:
    relative_path = str(row.get("relative_path") or "").strip()
    doc_id = str(row.get("doc_id") or "").strip()
    path_stem = Path(relative_path).stem.replace("_", " ") if relative_path else ""
    doc_hint = doc_id.replace("_", " ") if doc_id else ""
    return (path_stem, doc_hint)


def _document_family(row: Mapping[str, Any]) -> str:
    citation = _build_row_citation(row)
    profile = classify_normative_document(
        citation.to_public_dict() if hasattr(citation, "to_public_dict") else {},
        dict(row),
    )
    return str(profile.document_family or "").strip().lower()


def _row_haystack(row: Mapping[str, Any]) -> str:
    return " ".join(
        [
            str(row.get("title") or ""),
            str(row.get("notes") or ""),
            str(row.get("subtema") or ""),
            str(row.get("relative_path") or ""),
            str(row.get("doc_id") or ""),
            str(row.get("tipo_de_documento") or ""),
        ]
    ).strip().lower()


def _form_identity_seed_texts(row: Mapping[str, Any]) -> tuple[str, ...]:
    citation = _build_row_citation(row)
    return (
        str(row.get("title") or ""),
        str(citation.source_label or "") if citation is not None else "",
        str(citation.legal_reference or "") if citation is not None else "",
        str(row.get("notes") or ""),
    )


def _looks_like_form_identity_text(value: Any) -> bool:
    text = str(value or "").strip().lower()
    if "formulario" not in text and "formato" not in text:
        return False
    if any(token in text for token in _FORM_GUIDE_HINT_TOKENS):
        return False
    return any(key.startswith("formulario:") for key in _reference_keys_from_texts(text))


def _has_authoritative_form_identity(row: Mapping[str, Any]) -> bool:
    return any(_looks_like_form_identity_text(value) for value in _form_identity_seed_texts(row))


def _looks_like_exact_form_document(row: Mapping[str, Any]) -> bool:
    if _has_authoritative_form_identity(row):
        return True

    relative_path = str(row.get("relative_path") or "").strip()
    path_stem = Path(relative_path).stem.replace("_", " ").lower() if relative_path else ""
    if "formulario" not in path_stem and "formato" not in path_stem:
        return False
    return not any(token in path_stem for token in _FORM_GUIDE_HINT_TOKENS)


def _infer_relation_type(
    row: Mapping[str, Any],
    *,
    entity_type: str,
    identity_keys: set[str],
    mentioned_keys: set[str],
) -> str:
    explicit = str(row.get("relation_type") or "").strip().lower()
    if explicit:
        return explicit

    knowledge_class = str(row.get("knowledge_class") or "").strip().lower()
    if not identity_keys:
        if knowledge_class == "practica_erp":
            return "implements"
        return "mentions" if mentioned_keys else ""

    relative_path = str(row.get("relative_path") or "").strip().lower()
    source_type = str(row.get("source_type") or "").strip().lower()
    haystack = _row_haystack(row)
    authoritative_form_identity = _has_authoritative_form_identity(row)
    package_like = relative_path.startswith("form_guides/") or "/form_guides/" in relative_path
    path_stem = Path(relative_path).stem.replace("_", " ").lower() if relative_path else ""
    classification_haystack = " ".join(
        [
            str(row.get("title") or ""),
            str(row.get("notes") or ""),
            str(row.get("subtema") or ""),
            str(row.get("doc_id") or ""),
            path_stem,
        ]
    ).strip().lower()
    guide_like = any(
        token in classification_haystack
        for token in ("guia", "guía", "instructivo", "diligenciar", "llenarlo")
    )
    procedural_like = any(
        token in classification_haystack
        for token in ("checklist", "manual", "plantilla", "operacion", "operación", "bloque", "seccion", "sección")
    )

    if entity_type == "formulario":
        if package_like:
            return "companion_to"
        if guide_like and not _looks_like_exact_form_document(row):
            if (
                source_type.startswith("official")
                and knowledge_class == "normative_base"
                and authoritative_form_identity
            ):
                return "authoritative_variant"
            return "companion_to"
        if source_type.startswith("official") and knowledge_class == "normative_base" and authoritative_form_identity:
            if source_type == "official_secondary" or procedural_like:
                return "authoritative_variant"
            return "canonical_for"
        if procedural_like or knowledge_class == "practica_erp":
            return "implements"
        if source_type == "official_secondary":
            return "authoritative_variant"
        return "canonical_for"

    if knowledge_class == "practica_erp":
        return "implements"
    if knowledge_class == "interpretative_guidance":
        return "interprets"

    if package_like or guide_like:
        return "authoritative_variant"
    if source_type == "official_secondary":
        return "authoritative_variant"
    return "canonical_for"


def _infer_admissible_surfaces(*, entity_type: str, relation_type: str) -> tuple[str, ...]:
    if relation_type in CANONICAL_REFERENCE_RELATION_TYPES:
        if entity_type == "formulario":
            return ("canonical_card", "analytical_qa")
        return ("canonical_card", "analytical_qa")
    if relation_type == "companion_to":
        return ("interactive_guide", "analytical_qa")
    if relation_type in {"interprets", "implements", "mentions"}:
        return ("analytical_qa",)
    return ()


def _infer_supports_fields(*, entity_type: str, relation_type: str) -> tuple[str, ...]:
    if entity_type == "formulario" and relation_type in CANONICAL_REFERENCE_RELATION_TYPES:
        return (
            "lead",
            "purpose_text",
            "mandatory_when",
            "latest_identified",
            "professional_impact",
        )
    if relation_type == "companion_to":
        return ("guide_steps", "guide_sections", "field_hotspots", "review_controls")
    if relation_type in {"interprets", "implements"}:
        return ("analysis_context", "operational_controls")
    return ()


def _index_file_signature(index_file: Path) -> str:
    try:
        stat = index_file.stat()
    except OSError:
        return "missing"
    return f"{int(stat.st_mtime_ns)}:{int(stat.st_size)}"


@lru_cache(maxsize=8)
def _load_index_rows_by_doc_id_cached(index_path: str, signature: str) -> dict[str, dict[str, Any]]:
    del signature
    from .pipeline_c.retrieval_scoring import load_index

    index_file = Path(index_path)
    rows_by_doc_id: dict[str, dict[str, Any]] = {}
    for row in load_index(index_file=index_file):
        if not isinstance(row, dict):
            continue
        doc_id = str(row.get("doc_id", "")).strip()
        if not doc_id:
            continue
        rows_by_doc_id[doc_id] = dict(row)
    return rows_by_doc_id


def load_index_rows_by_doc_id(index_file: Path) -> dict[str, dict[str, Any]]:
    signature = _index_file_signature(index_file)
    return dict(_load_index_rows_by_doc_id_cached(str(index_file.resolve()), signature))


def _extract_doc_body_reference_keys(row: Mapping[str, Any], *, max_chars: int = 80_000) -> set[str]:
    raw_path = str(row.get("absolute_path") or "").strip()
    if not raw_path:
        return set()

    path = Path(raw_path)
    if not path.exists() or not path.is_file():
        return set()
    if path.suffix.lower() not in {".md", ".txt", ".json", ".html", ".htm"}:
        return set()

    body = read_referenceable_text(path, max_chars=max_chars)
    if not body:
        return set()

    knowledge_class = str(row.get("knowledge_class") or "").strip().lower()
    if knowledge_class == "practica_erp":
        metadata = derive_practical_doc_metadata(
            doc=row,
            body_text=body,
            manifest_normative_refs=_normalize_string_tuple(row.get("normative_refs")),
        )
        return set(metadata.mentioned_reference_keys)

    keys: set[str] = set()
    for ref in extract_normative_references(body):
        key = str(ref.get("reference_key", "")).strip()
        if key:
            keys.add(key)
    return keys


def _metadata_reference_keys(row: Mapping[str, Any]) -> dict[str, int]:
    origins: dict[str, int] = {}

    def _record(candidate: str, rank: int) -> None:
        for reference in extract_normative_references(candidate):
            key = str(reference.get("reference_key") or "").strip()
            if not key:
                continue
            current = origins.get(key)
            if current is None or rank < current:
                origins[key] = rank

    try:
        from .contracts import Citation, DocumentRecord

        doc = DocumentRecord.from_dict(dict(row))
        citation = Citation.from_document(doc)
    except Exception:
        citation = None

    for candidate in (
        str(row.get("title") or ""),
        str(citation.source_label or "") if citation is not None else "",
        str(citation.legal_reference or "") if citation is not None else "",
    ):
        _record(candidate, 0)

    for candidate in (
        str(row.get("notes") or ""),
        str(row.get("subtema") or ""),
        str(row.get("relative_path") or ""),
        str(row.get("doc_id") or ""),
        str(row.get("url") or ""),
        str(row.get("authority") or ""),
    ):
        _record(candidate, 1)

    for key in _extract_doc_body_reference_keys(row):
        current = origins.get(key)
        if current is None:
            origins[key] = 2
    return origins


def build_doc_reference_keys(row: Mapping[str, Any]) -> set[str]:
    return set(_metadata_reference_keys(row))


def build_identity_reference_keys(row: Mapping[str, Any]) -> set[str]:
    knowledge_class = str(row.get("knowledge_class") or "").strip().lower()
    explicit = set(_normalize_string_tuple(row.get("reference_identity_keys")))
    if knowledge_class == "practica_erp":
        explicit = {item for item in explicit if is_allowed_practical_identity_key(item)}
        if explicit:
            return explicit
        return set(derive_practical_identity_keys(row))
    if explicit:
        return explicit

    keys: set[str] = set()
    explicit_key = str(row.get("reference_key") or "").strip()
    if explicit_key:
        keys.add(explicit_key)

    seed_texts = _identity_seed_texts(row)
    keys.update(_reference_keys_from_texts(*seed_texts[:3]))
    if not keys:
        keys.update(_reference_keys_from_texts(*seed_texts[3:]))
    if not keys:
        best = best_reference_metadata(*seed_texts)
        if best and str(best.get("reference_key") or "").strip():
            keys.add(str(best.get("reference_key")).strip())
    if not keys:
        keys.update(_reference_keys_from_texts(*_path_identity_seed_texts(row)))
    return keys


def build_mentioned_reference_keys(row: Mapping[str, Any]) -> set[str]:
    knowledge_class = str(row.get("knowledge_class") or "").strip().lower()
    explicit = set(_normalize_string_tuple(row.get("mentioned_reference_keys")))
    if explicit:
        return explicit

    if knowledge_class == "practica_erp":
        return _extract_doc_body_reference_keys(row)

    mentioned = _reference_keys_from_texts(
        str(row.get("notes") or ""),
        str(row.get("subtema") or ""),
        str(row.get("relative_path") or ""),
        str(row.get("doc_id") or ""),
        str(row.get("url") or ""),
    )
    mentioned.update(_extract_doc_body_reference_keys(row))
    mentioned.difference_update(build_identity_reference_keys(row))
    return mentioned


def document_reference_semantics(row: Mapping[str, Any]) -> dict[str, Any]:
    identity_keys = build_identity_reference_keys(row)
    mentioned_keys = build_mentioned_reference_keys(row)
    family = _document_family(row)
    entity_type = str(row.get("entity_type") or "").strip().lower() or family or "generic"
    relation_type = _infer_relation_type(
        row,
        entity_type=entity_type,
        identity_keys=identity_keys,
        mentioned_keys=mentioned_keys,
    )
    entity_id = str(row.get("entity_id") or "").strip()
    if not entity_id:
        if identity_keys:
            entity_id = sorted(identity_keys)[0]
        else:
            entity_id = logical_doc_id(str(row.get("doc_id", "")).strip())

    admissible_surfaces = _normalize_string_tuple(row.get("admissible_surfaces")) or _infer_admissible_surfaces(
        entity_type=entity_type,
        relation_type=relation_type,
    )
    supports_fields = _normalize_string_tuple(row.get("supports_fields")) or _infer_supports_fields(
        entity_type=entity_type,
        relation_type=relation_type,
    )

    return {
        "entity_id": entity_id,
        "entity_type": entity_type,
        "relation_type": relation_type,
        "reference_identity_keys": tuple(sorted(identity_keys)),
        "mentioned_reference_keys": tuple(sorted(mentioned_keys)),
        "admissible_surfaces": tuple(admissible_surfaces),
        "supports_fields": tuple(supports_fields),
    }


def _is_canonical_primary_norm_doc(row: Mapping[str, Any]) -> bool:
    doc_id = str(row.get("doc_id", "")).strip().lower()
    rel = str(row.get("relative_path", "")).strip().lower()
    return any(
        token in doc_id or token in rel
        for token in ("co_et_suin_1705747", "co_dur_1625_2016")
    )


def _reference_candidate_priority(row: Mapping[str, Any]) -> tuple[int, int, int, int, str, str]:
    knowledge_class = str(row.get("knowledge_class", "")).strip().lower()
    source_type = str(row.get("source_type", "")).strip().lower()
    layer_rank = {
        "normative_base": 0,
        "interpretative_guidance": 1,
        "practica_erp": 2,
    }.get(knowledge_class, 3)
    source_rank = {
        "official_primary": 0,
        "official_secondary": 1,
        "operational_checklist": 2,
    }.get(source_type, 3)
    canonical_rank = 0 if _is_canonical_primary_norm_doc(row) else 1
    relation_type = str(row.get("relation_type", "")).strip().lower()
    relation_rank = {
        "canonical_for": 0,
        "authoritative_variant": 1,
    }.get(relation_type, 2)
    relative_path = str(row.get("relative_path", "")).strip().lower()
    doc_id = str(row.get("doc_id", "")).strip().lower()
    return (relation_rank, layer_rank, source_rank, canonical_rank, relative_path, doc_id)


@lru_cache(maxsize=8)
def _reference_doc_catalog_cached(index_path: str, signature: str) -> dict[str, tuple[str, ...]]:
    rows_by_doc_id = _load_index_rows_by_doc_id_cached(index_path, signature)
    candidates_by_key: dict[str, list[tuple[tuple[int, int, int, int, str, str], str]]] = {}
    for doc_id, row in rows_by_doc_id.items():
        semantics = document_reference_semantics(row)
        relation_type = str(semantics.get("relation_type") or "").strip().lower()
        if relation_type not in CANONICAL_REFERENCE_RELATION_TYPES:
            continue
        reference_origins = {
            key: 0 for key in list(semantics.get("reference_identity_keys") or [])
            if str(key).strip()
        }
        if not reference_origins:
            continue
        row = dict(row) | {
            "relation_type": relation_type,
            "entity_id": semantics.get("entity_id"),
            "entity_type": semantics.get("entity_type"),
        }
        base_priority = _reference_candidate_priority(row)
        for key, origin_rank in reference_origins.items():
            priority = (origin_rank, *base_priority)
            candidates_by_key.setdefault(key, []).append((priority, doc_id))
    catalog: dict[str, tuple[str, ...]] = {}
    for key, candidates in candidates_by_key.items():
        sorted_candidates = sorted(candidates, key=lambda item: item[0])
        catalog[key] = tuple(doc_id for _, doc_id in sorted_candidates)
    return catalog


def reference_doc_catalog(index_file: Path) -> dict[str, tuple[str, ...]]:
    signature = _index_file_signature(index_file)
    return dict(_reference_doc_catalog_cached(str(index_file.resolve()), signature))


def collect_reference_mentions(text: str) -> ReferenceMentionCollection:
    extracted = extract_normative_reference_mentions(str(text or ""))
    mentions: list[ReferenceMentionCandidate] = []
    seen_reference_identities: set[str] = set()
    for item in extracted:
        candidate = _coerce_reference_mention_candidate(item)
        if candidate is None or candidate.reference_identity in seen_reference_identities:
            continue
        seen_reference_identities.add(candidate.reference_identity)
        mentions.append(candidate)
    return ReferenceMentionCollection(
        detected_count=len(extracted),
        mentions=tuple(mentions),
    )


def extract_reference_identities_from_text(text: str) -> set[str]:
    return {
        candidate.reference_identity
        for candidate in collect_reference_mentions(text).mentions
        if candidate.reference_identity
    }


def extract_reference_keys_from_text(text: str) -> set[str]:
    return {
        candidate.reference_key
        for candidate in collect_reference_mentions(text).mentions
        if candidate.reference_key
    }


def extract_reference_keys_from_citation_payload(citation: Mapping[str, Any]) -> set[str]:
    keys: set[str] = set()
    if not isinstance(citation, Mapping):
        return keys
    explicit_key = str(citation.get("reference_key", "")).strip()
    if explicit_key:
        keys.add(explicit_key)
    for field in ("source_label", "legal_reference", "doc_id", "relative_path"):
        for reference in extract_normative_references(str(citation.get(field, "")).strip()):
            key = str(reference.get("reference_key") or "").strip()
            if key:
                keys.add(key)
    return keys


def extract_reference_identities_from_citation_payload(citation: Mapping[str, Any]) -> set[str]:
    identities: set[str] = set()
    if not isinstance(citation, Mapping):
        return identities

    explicit_identity = normative_reference_identity(
        {
            "reference_key": citation.get("reference_key"),
            "locator_text": citation.get("locator_text"),
            "locator_kind": citation.get("locator_kind"),
            "locator_start": citation.get("locator_start"),
            "locator_end": citation.get("locator_end"),
        }
    )
    if explicit_identity:
        identities.add(explicit_identity)

    for field in ("source_label", "legal_reference", "doc_id", "relative_path"):
        identities.update(extract_reference_identities_from_text(str(citation.get(field, "")).strip()))
    return identities


def reference_detail_title(reference_detail: Mapping[str, Any] | ReferenceMentionCandidate | None) -> str:
    candidate = _coerce_reference_mention_candidate(reference_detail)
    if candidate is None:
        return ""
    if candidate.reference_text and candidate.locator_text:
        return f"{candidate.reference_text}, {candidate.locator_text}"
    return candidate.reference_text or candidate.locator_text or ""


def reference_detail_resolution_text(reference_detail: Mapping[str, Any] | ReferenceMentionCandidate | None) -> str:
    candidate = _coerce_reference_mention_candidate(reference_detail)
    if candidate is None:
        return ""
    title = reference_detail_title(candidate)
    if title:
        return title
    return " ".join(
        part
        for part in (candidate.reference_text, candidate.locator_text)
        if str(part or "").strip()
    ).strip()


def extract_reference_keys_from_citation(citation: Any) -> set[str]:
    keys: set[str] = set()
    explicit_key = str(getattr(citation, "reference_key", "") or "").strip()
    if explicit_key:
        keys.add(explicit_key)
    for field in ("source_label", "legal_reference", "doc_id", "relative_path"):
        for reference in extract_normative_references(str(getattr(citation, field, "") or "").strip()):
            key = str(reference.get("reference_key") or "").strip()
            if key:
                keys.add(key)
    return keys


def _reference_locator_variants(reference_key: str, locator_start: str) -> tuple[str, ...]:
    normalized_key = str(reference_key or "").strip().lower()
    normalized_locator = str(locator_start or "").strip().lower()
    if normalized_key not in {"et", "dur:1625:2016"} or not normalized_locator:
        return ()

    normalized_token = re.sub(r"[_\-.]+", "_", normalized_locator).strip("_")
    if not normalized_token:
        return ()

    variants: list[str] = []
    if normalized_key == "et":
        prefix = "et_art_"
        display_variants = (
            normalized_locator,
            normalized_locator.replace("_", "-"),
            normalized_locator.replace("_", "."),
        )
    else:
        prefix = "dur_1625_art_"
        display_variants = (
            normalized_locator,
            normalized_locator.replace("_", "."),
            normalized_locator.replace("_", "-"),
        )

    for candidate in (
        f"{prefix}{normalized_token}",
        *[f"{prefix}{variant}" for variant in display_variants],
    ):
        clean = candidate.strip()
        if clean and clean not in variants:
            variants.append(clean)
    return tuple(variants)


def _matches_reference_variant(candidate: str, variants: tuple[str, ...]) -> bool:
    normalized_candidate = str(candidate or "").strip().lower()
    if not normalized_candidate or not variants:
        return False
    return any(variant and variant == normalized_candidate for variant in variants)


def _resolve_locator_specific_rows(
    *,
    reference_detail: ReferenceMentionCandidate,
    rows_by_doc_id: Mapping[str, Mapping[str, Any]],
    seen_doc_ids: set[str],
    allowed_classes: set[str] | None,
) -> list[dict[str, Any]]:
    base_key = str(reference_detail.reference_key or "").strip()
    locator_start = str(reference_detail.locator_start or "").strip()
    variants = _reference_locator_variants(base_key, locator_start)
    if not variants:
        return []

    candidates: list[tuple[tuple[int, int, int, int, str, str], dict[str, Any]]] = []
    for doc_id, row in rows_by_doc_id.items():
        clean_doc_id = str(doc_id).strip()
        if not clean_doc_id or clean_doc_id in seen_doc_ids:
            continue
        candidate = dict(row)
        if allowed_classes is not None:
            candidate_class = str(candidate.get("knowledge_class") or "").strip().lower()
            if candidate_class not in allowed_classes:
                continue

        reference_pool = [
            *[str(item).strip() for item in list(candidate.get("normative_refs") or []) if str(item).strip()],
            *[str(item).strip() for item in list(candidate.get("reference_identity_keys") or []) if str(item).strip()],
            *[str(item).strip() for item in list(candidate.get("mentioned_reference_keys") or []) if str(item).strip()],
            clean_doc_id,
            str(candidate.get("relative_path") or "").strip(),
        ]
        if not any(_matches_reference_variant(item, variants) for item in reference_pool):
            continue

        semantics = document_reference_semantics(candidate)
        ranked_candidate = dict(candidate) | {
            "relation_type": str(semantics.get("relation_type") or "").strip().lower(),
            "entity_id": semantics.get("entity_id"),
            "entity_type": semantics.get("entity_type"),
        }
        candidates.append((_reference_candidate_priority(ranked_candidate), candidate))

    candidates.sort(key=lambda item: item[0])
    return [candidate for _, candidate in candidates]


def resolve_normative_mentions(
    *,
    text: str,
    existing_doc_ids: Iterable[str] = (),
    existing_reference_keys: Iterable[str] = (),
    index_file: Path,
    max_resolved: int = 8,
    allowed_knowledge_classes: Iterable[str] | None = None,
) -> dict[str, Any]:
    mention_collection = collect_reference_mentions(text)
    unique_references = list(mention_collection.mentions)

    covered_keys = {str(key).strip() for key in existing_reference_keys if str(key).strip()}
    target_references = [
        item for item in unique_references if str(item.reference_key or "").strip() not in covered_keys
    ]
    if not target_references:
        return {
            "resolved_rows": [],
            "metrics": {
                "mentions_detected": mention_collection.detected_count,
                "mentions_unique": mention_collection.unique_count,
                "mentions_already_covered": len(unique_references),
                "mentions_resolved_to_doc": 0,
                "mentions_unresolved": 0,
                "resolved_reference_keys": [],
                "unresolved_reference_keys": [],
            },
            "unresolved_references": [],
        }

    rows_by_doc_id = load_index_rows_by_doc_id(index_file=index_file)
    catalog = reference_doc_catalog(index_file=index_file)
    seen_doc_ids = {str(doc_id).strip() for doc_id in existing_doc_ids if str(doc_id).strip()}
    allowed_classes = (
        {str(item).strip().lower() for item in allowed_knowledge_classes if str(item).strip()}
        if allowed_knowledge_classes is not None
        else None
    )
    resolved_rows: list[dict[str, Any]] = []
    resolved_keys: list[str] = []
    unresolved_references: list[dict[str, Any]] = []
    limit = max(1, int(max_resolved))

    for item in target_references:
        if len(resolved_rows) >= limit:
            unresolved_references.append(item.to_public_dict())
            continue
        key = str(item.reference_key or "").strip()
        resolved_row: dict[str, Any] | None = None
        for candidate in _resolve_locator_specific_rows(
            reference_detail=item,
            rows_by_doc_id=rows_by_doc_id,
            seen_doc_ids=seen_doc_ids,
            allowed_classes=allowed_classes,
        ):
            resolved_row = dict(candidate)
            seen_doc_ids.add(str(candidate.get("doc_id") or "").strip())
            break
        if resolved_row is not None:
            resolved_rows.append(resolved_row)
            resolved_keys.append(key)
            continue
        for doc_id in catalog.get(key, ()):
            if doc_id in seen_doc_ids:
                continue
            candidate = rows_by_doc_id.get(doc_id)
            if candidate is None:
                continue
            if allowed_classes is not None:
                candidate_class = str(candidate.get("knowledge_class") or "").strip().lower()
                if candidate_class not in allowed_classes:
                    continue
            resolved_row = dict(candidate)
            seen_doc_ids.add(doc_id)
            break
        if resolved_row is None:
            unresolved_references.append(item.to_public_dict())
            continue
        resolved_rows.append(resolved_row)
        resolved_keys.append(key)

    unresolved_keys = [
        str(item.get("reference_key", "")).strip()
        for item in unresolved_references
        if str(item.get("reference_key", "")).strip()
    ]
    return {
        "resolved_rows": resolved_rows,
        "metrics": {
            "mentions_detected": mention_collection.detected_count,
            "mentions_unique": mention_collection.unique_count,
            "mentions_already_covered": max(0, len(unique_references) - len(target_references)),
            "mentions_resolved_to_doc": len(resolved_keys),
            "mentions_unresolved": len(unresolved_keys),
            "resolved_reference_keys": resolved_keys,
            "unresolved_reference_keys": unresolved_keys,
        },
        "unresolved_references": unresolved_references,
    }


def citation_identity(citation: Mapping[str, Any]) -> str:
    if not isinstance(citation, Mapping):
        return ""
    locator_identity = normative_reference_identity(dict(citation))
    if locator_identity and "::" in locator_identity:
        return f"locator:{locator_identity}"
    logical = str(citation.get("logical_doc_id", "")).strip().lower()
    if logical:
        return f"logical:{logical}"
    doc_id = str(citation.get("doc_id", "")).strip().lower()
    if doc_id:
        return f"doc:{doc_id}"
    key = str(citation.get("reference_key", "")).strip().lower()
    if key:
        return f"key:{key}"
    label = str(citation.get("legal_reference") or citation.get("source_label") or "").strip().lower()
    if label:
        return f"label:{label}"
    return ""


def collapse_citation_payloads(
    primary: list[dict[str, Any]],
    secondary: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source in (primary, secondary):
        for citation in source:
            if not isinstance(citation, dict):
                continue
            item = dict(citation)
            if not str(item.get("logical_doc_id", "")).strip():
                item["logical_doc_id"] = logical_doc_id(str(item.get("doc_id", "")).strip())
            identity = citation_identity(item)
            if identity and identity in seen:
                continue
            if identity:
                seen.add(identity)
            merged.append(item)
    return merged
