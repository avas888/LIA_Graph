from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .citation_resolution import (
    collect_reference_mentions,
    collapse_citation_payloads,
    extract_reference_identities_from_citation_payload as _shared_extract_reference_identities_from_citation_payload,
    extract_reference_identities_from_text as _shared_extract_reference_identities_from_text,
    extract_reference_keys_from_text as _shared_extract_reference_keys_from_text,
    extract_reference_keys_from_citation_payload as _shared_extract_reference_keys_from_citation_payload,
    reference_detail_resolution_text as _shared_reference_detail_resolution_text,
    reference_detail_title as _shared_reference_detail_title,
    resolve_normative_mentions,
)
from .normative_references import reference_identity as _reference_detail_identity
from .normative_taxonomy import classify_normative_document


# ---------------------------------------------------------------------------
# Lazy-import helpers -- functions that still live in ui_server today.
# Using a deferred accessor avoids circular imports and ensures that
# monkeypatch.setattr(ui_server, ...) in tests is honoured.
# ---------------------------------------------------------------------------


def _ui() -> Any:
    """Lazy accessor for lia_graph.ui_server (avoids circular import)."""
    from . import ui_server as _mod
    return _mod


# ---------------------------------------------------------------------------
# Module-level constants (moved from ui_server during granularize-v1 1D)
# ---------------------------------------------------------------------------

_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
INDEX_FILE_PATH = _WORKSPACE_ROOT / "artifacts/document_index.jsonl"

_NORMATIVE_HELPER_KNOWLEDGE_CLASSES = {"normative_base"}
_NORMATIVO_HELPER_SOURCE_TYPES = {"official_primary", "official_secondary", "norma"}
_STRICT_NORMATIVO_HELPER_SOURCE_TYPES = {"official_primary", "norma"}

_MENTION_KEY_PREFIX_TO_ALLOWED_FAMILIES: dict[str, frozenset[str]] = {
    "ley:": frozenset({"ley"}),
    "decreto:": frozenset({"decreto"}),
    "formulario:": frozenset({"formulario"}),
}


# ---------------------------------------------------------------------------
# Reference resolver functions (extracted from ui_server, Phase 1D)
# ---------------------------------------------------------------------------


def _reference_label_from_key(reference_key: str) -> str:
    normalized = str(reference_key or "").strip().lower()
    if normalized.startswith("formulario:"):
        number = normalized.split(":", 1)[1].strip()
        if number:
            return f"Formulario {number.upper()}"
    return str(reference_key or "").strip()


def _find_reference_doc_id(reference_key: str, *, index_file: Path = INDEX_FILE_PATH) -> str:
    normalized = str(reference_key or "").strip()
    if not normalized:
        return ""
    catalog = _ui()._reference_doc_catalog(index_file)
    for candidate_doc_id in catalog.get(normalized, ()):
        row = _ui()._find_document_index_row(candidate_doc_id, index_file=index_file)
        if isinstance(row, dict) and _ui()._row_is_active_or_canonical(row):
            return str(candidate_doc_id).strip()
    # Fallback: ley:NUMBER:YEAR → ley:NUMBER for laws ingested without year
    # in their reference_identity_keys.
    if normalized.startswith("ley:") and normalized.count(":") == 2:
        short_key = ":".join(normalized.split(":")[:2])
        for candidate_doc_id in catalog.get(short_key, ()):
            row = _ui()._find_document_index_row(candidate_doc_id, index_file=index_file)
            if isinstance(row, dict) and _ui()._row_is_active_or_canonical(row):
                return str(candidate_doc_id).strip()
    return ""


def _extract_reference_identities_from_citation_payload(citation: dict[str, Any]) -> set[str]:
    return _shared_extract_reference_identities_from_citation_payload(citation)


def _extract_reference_identities_from_text(text: str) -> set[str]:
    return _shared_extract_reference_identities_from_text(text)


# ---------------------------------------------------------------------------
# Internal helpers (only used by the functions in this module)
# ---------------------------------------------------------------------------


def _extract_reference_keys_from_citation_payload(citation: dict[str, Any]) -> set[str]:
    return _shared_extract_reference_keys_from_citation_payload(citation)


def _extract_reference_keys_from_text(text: str) -> set[str]:
    return _shared_extract_reference_keys_from_text(text)


def _document_family_from_row(row: dict[str, Any]) -> str:
    """Lightweight family classification from a raw index row."""
    try:
        citation_payload = _ui()._build_public_citation_from_row(row)
        profile = classify_normative_document(citation_payload, row)
        return str(profile.document_family or "").strip().lower()
    except Exception:
        return ""


def _is_cross_type_mention_mismatch(detail_key: str, resolved_row: dict[str, Any]) -> bool:
    """Return True if the resolved row's document family contradicts the mention type."""
    allowed: frozenset[str] | None = None
    for prefix, families in _MENTION_KEY_PREFIX_TO_ALLOWED_FAMILIES.items():
        if detail_key.startswith(prefix):
            allowed = families
            break
    if allowed is None:
        return False
    family = _document_family_from_row(resolved_row)
    return bool(family) and family not in allowed


# ---------------------------------------------------------------------------
# Core reference resolver functions
# ---------------------------------------------------------------------------


def _citation_matches_reference_mentions(
    citation: dict[str, Any],
    *,
    reference_identities: set[str],
    reference_keys: set[str],
) -> bool:
    if not isinstance(citation, dict):
        return False
    citation_identities = _extract_reference_identities_from_citation_payload(citation)
    citation_locator_identities = {identity for identity in citation_identities if "::" in identity}
    if citation_locator_identities:
        return bool(citation_locator_identities.intersection(reference_identities))
    citation_keys = _extract_reference_keys_from_citation_payload(citation)
    if citation_keys:
        return bool(citation_keys.intersection(reference_keys))
    return bool(str(citation.get("usage_context") or "").strip())


def _merge_citation_payloads(
    primary: list[dict[str, Any]],
    secondary: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged = collapse_citation_payloads(primary, secondary)
    for citation in merged:
        citation.pop("__identity", None)
    return merged


def _resolve_mention_citations(
    *,
    text: str,
    citations_payload: list[dict[str, Any]],
    index_file: Path = INDEX_FILE_PATH,
    max_resolved: int = 8,
    allowed_knowledge_classes: tuple[str, ...] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    mention_collection = collect_reference_mentions(text)
    reference_details = [item.to_public_dict() for item in mention_collection.mentions]
    reference_details_by_identity = {
        str(item.get("reference_identity") or _reference_detail_identity(item)).strip(): dict(item)
        for item in reference_details
        if str(item.get("reference_identity") or _reference_detail_identity(item)).strip()
    }
    existing: list[dict[str, Any]] = []
    for item in citations_payload:
        if not isinstance(item, dict):
            continue
        cloned = dict(item)
        detail_identity = _select_reference_detail_identity_for_citation(
            cloned,
            reference_details_by_identity=reference_details_by_identity,
        )
        if detail_identity:
            detail = reference_details_by_identity.get(detail_identity)
            # ── Cross-type guard: don't let ET citations claim ley mentions ──
            detail_key = str(detail.get("reference_key") or "").strip().lower() if detail else ""
            if detail_key and _is_cross_type_mention_mismatch(detail_key, cloned):
                detail_identity = ""
                detail = None
            # ── End cross-type guard ──
            if detail_identity and detail and str(detail.get("reference_key") or "").strip():
                cloned.setdefault("reference_key", str(detail.get("reference_key") or "").strip())
            if detail_identity:
                cloned = _apply_reference_detail_to_citation(
                    cloned,
                    reference_detail=detail,
                )
        existing.append(cloned)
    covered_identities: set[str] = set()
    for citation in existing:
        covered_identities.update(_extract_reference_identities_from_citation_payload(citation))
    initially_covered_identities = set(covered_identities)

    resolved: list[dict[str, Any]] = []
    resolved_keys: list[str] = []
    unresolved_references: list[dict[str, Any]] = []
    resolved_count = 0
    for detail in reference_details:
        detail_identity = str(detail.get("reference_identity") or _reference_detail_identity(detail)).strip()
        if not detail_identity:
            continue
        if detail_identity in covered_identities:
            continue
        if resolved_count >= max(1, int(max_resolved)):
            unresolved_references.append(dict(detail))
            continue
        resolution = resolve_normative_mentions(
            text=_build_reference_detail_resolution_text(detail),
            existing_doc_ids=(),
            existing_reference_keys=(),
            index_file=index_file,
            max_resolved=1,
            allowed_knowledge_classes=allowed_knowledge_classes,
        )
        resolved_rows = list(resolution.get("resolved_rows") or [])
        if not resolved_rows:
            unresolved_references.append(dict(detail))
            continue

        # ── Cross-type guard: ley mentions must not resolve to ET docs ──
        detail_key = str(detail.get("reference_key") or "").strip().lower()
        if detail_key and _is_cross_type_mention_mismatch(detail_key, dict(resolved_rows[0])):
            unresolved_references.append(dict(detail))
            continue
        # ── End cross-type guard ──

        citation_payload = _ui()._build_public_citation_from_row(dict(resolved_rows[0]))
        key = str(detail.get("reference_key") or citation_payload.get("reference_key") or "").strip()
        if key:
            citation_payload["reference_key"] = key
        citation_payload = _apply_reference_detail_to_citation(
            citation_payload,
            reference_detail=detail,
        )
        citation_payload["usage_context"] = citation_payload.get("usage_context") or f"Referencia detectada: {key}"
        resolved.append(citation_payload)
        covered_identities.add(detail_identity)
        resolved_keys.append(key)
        resolved_count += 1

    merged = _drop_base_citations_shadowed_by_locators(_merge_citation_payloads(existing, resolved))
    return merged, {
        "mentions_detected": mention_collection.detected_count,
        "mentions_unique": len(reference_details_by_identity),
        "mentions_already_covered": sum(
            1
            for detail in reference_details
            if str(detail.get("reference_identity") or _reference_detail_identity(detail)).strip() in initially_covered_identities
        ),
        "mentions_resolved_to_doc": len(resolved),
        "mentions_unresolved": len(unresolved_references),
        "resolved_reference_keys": resolved_keys,
        "unresolved_reference_keys": [
            str(item.get("reference_key") or "").strip()
            for item in unresolved_references
            if str(item.get("reference_key") or "").strip()
        ],
    }


def _select_reference_detail_identity_for_citation(
    citation: dict[str, Any],
    *,
    reference_details_by_identity: dict[str, dict[str, Any]],
) -> str:
    explicit_identity = _reference_detail_identity(
        {
            "reference_key": citation.get("reference_key"),
            "locator_text": citation.get("locator_text"),
            "locator_kind": citation.get("locator_kind"),
            "locator_start": citation.get("locator_start"),
            "locator_end": citation.get("locator_end"),
        }
    )
    if explicit_identity and explicit_identity in reference_details_by_identity:
        return explicit_identity
    for identity in sorted(_extract_reference_identities_from_citation_payload(citation)):
        if identity in reference_details_by_identity:
            return identity
    return ""


def _build_reference_detail_title(reference_detail: dict[str, Any] | None) -> str:
    if not isinstance(reference_detail, dict):
        return ""
    shared_title = _shared_reference_detail_title(reference_detail)
    if not shared_title:
        return ""
    reference_text, _, locator_text = shared_title.partition(", ")
    reference_text = _ui()._clean_markdown_inline(reference_text.strip())
    locator_text = _ui()._clean_markdown_inline(locator_text.strip())
    if reference_text and locator_text:
        return f"{reference_text}, {locator_text}"
    return reference_text or locator_text


def _build_reference_detail_resolution_text(reference_detail: dict[str, Any] | None) -> str:
    raw = _shared_reference_detail_resolution_text(reference_detail)
    if not raw:
        return ""
    return _ui()._clean_markdown_inline(raw)


def _drop_base_citations_shadowed_by_locators(citations_payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
    locator_keys = {
        str(item.get("reference_key") or "").strip().lower()
        for item in citations_payload
        if isinstance(item, dict)
        and str(item.get("reference_key") or "").strip()
        and any(
            str(item.get(field) or "").strip()
            for field in ("locator_text", "locator_kind", "locator_start", "locator_end")
        )
    }
    if not locator_keys:
        return citations_payload
    filtered: list[dict[str, Any]] = []
    for item in citations_payload:
        if not isinstance(item, dict):
            continue
        key = str(item.get("reference_key") or "").strip().lower()
        has_locator = any(
            str(item.get(field) or "").strip()
            for field in ("locator_text", "locator_kind", "locator_start", "locator_end")
        )
        if key in locator_keys and not has_locator:
            continue
        filtered.append(item)
    return filtered


def _apply_reference_detail_to_citation(
    citation: dict[str, Any],
    *,
    reference_detail: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(citation, dict):
        return {}
    if not isinstance(reference_detail, dict):
        return dict(citation)

    enriched = dict(citation)
    for field in ("locator_text", "locator_kind", "locator_start", "locator_end"):
        value = reference_detail.get(field)
        if value:
            enriched[field] = value

    detail_title = _build_reference_detail_title(reference_detail)
    detail_identity = str(reference_detail.get("reference_identity") or _reference_detail_identity(reference_detail)).strip()
    detail_key = str(reference_detail.get("reference_key") or "").strip()
    reference_text = _ui()._clean_markdown_inline(str(reference_detail.get("reference_text") or "").strip())
    locator_text = _ui()._clean_markdown_inline(str(reference_detail.get("locator_text") or "").strip())
    normalized_reference = _ui()._normalize_source_reference_text(reference_text)
    normalized_locator = _ui()._normalize_source_reference_text(locator_text)

    for field in ("source_label", "legal_reference"):
        current = _ui()._clean_markdown_inline(str(enriched.get(field) or "").strip())
        normalized_current = _ui()._normalize_source_reference_text(current)
        if not current:
            if detail_title:
                enriched[field] = detail_title
            continue
        current_reference_identities = {
            str(item.get("reference_identity") or _reference_detail_identity(item)).strip()
            for item in extract_normative_reference_mentions(current)
            if str(item.get("reference_key") or "").strip() == detail_key
            and str(item.get("reference_identity") or _reference_detail_identity(item)).strip()
        }
        if detail_title and detail_identity and current_reference_identities and detail_identity not in current_reference_identities:
            enriched[field] = detail_title
            continue
        if normalized_locator and normalized_locator in normalized_current:
            continue
        if normalized_reference and normalized_reference in normalized_current and detail_title:
            enriched[field] = detail_title
    return enriched


def _is_normative_helper_normativo_citation(citation: dict[str, Any]) -> bool:
    if not isinstance(citation, dict):
        return False
    knowledge_class = str(citation.get("knowledge_class") or "").strip().lower()
    source_type = str(citation.get("source_type") or "").strip().lower()
    source_tier = str(citation.get("source_tier") or "").strip().lower()
    is_normative_tier = source_tier.startswith("fuente normativa")
    if knowledge_class == "normative_base":
        if source_type in _STRICT_NORMATIVO_HELPER_SOURCE_TYPES:
            return True
        if source_type == "official_secondary":
            return not source_tier or is_normative_tier
        return is_normative_tier
    if knowledge_class:
        return False
    if source_type in _STRICT_NORMATIVO_HELPER_SOURCE_TYPES:
        return True
    if source_type == "official_secondary":
        return not source_tier or is_normative_tier
    return is_normative_tier


def _filter_normative_helper_citations(
    citations_payload: list[dict[str, Any]],
    *,
    reference_text: str = "",
) -> list[dict[str, Any]]:
    normativo_rows = [
        dict(item)
        for item in citations_payload
        if isinstance(item, dict) and _is_normative_helper_normativo_citation(item)
    ]
    normalized_reference_text = str(reference_text or "").strip()
    if normalized_reference_text:
        reference_identities = _extract_reference_identities_from_text(normalized_reference_text)
        reference_keys = _extract_reference_keys_from_text(normalized_reference_text)
        if reference_identities or reference_keys:
            normativo_rows = [
                dict(item)
                for item in normativo_rows
                if _citation_matches_reference_mentions(
                    item,
                    reference_identities=reference_identities,
                    reference_keys=reference_keys,
                )
            ]
    return _merge_citation_payloads(normativo_rows, [])


def _build_normative_helper_citations(
    *,
    citations_payload: list[dict[str, Any]],
    reference_text: str,
    index_file: Path = INDEX_FILE_PATH,
    max_resolved: int = 8,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    filtered = _filter_normative_helper_citations(citations_payload, reference_text=reference_text)
    curated, mention_metrics = _resolve_mention_citations(
        text=reference_text,
        citations_payload=filtered,
        index_file=index_file,
        max_resolved=max_resolved,
        allowed_knowledge_classes=tuple(sorted(_NORMATIVE_HELPER_KNOWLEDGE_CLASSES)),
    )
    # Ensure all citations have usage_context so the frontend filterCitedOnly() keeps them
    for citation in curated:
        if not citation.get("usage_context"):
            citation["usage_context"] = "Referencia normativa de soporte"
    return _ui()._hydrate_citation_download_urls(curated), mention_metrics


# ---------------------------------------------------------------------------
# ET / Ley citation target helpers
# ---------------------------------------------------------------------------


def _citation_targets_et_article(citation: dict[str, Any]) -> bool:
    return (
        str(citation.get("reference_key") or "").strip().lower() == "et"
        and bool(str(citation.get("locator_start") or "").strip())
    )


def _citation_targets_ley(citation: dict[str, Any]) -> bool:
    return str(citation.get("reference_key") or "").strip().lower().startswith("ley:")


def _citation_et_locator_key(citation: dict[str, Any]) -> str:
    locator_start = str(citation.get("locator_start") or "").strip()
    if not _citation_targets_et_article(citation) or not locator_start:
        return ""
    return re.sub(r"[_\-.]+", "_", locator_start).strip("_")


def _citation_et_locator_label(citation: dict[str, Any]) -> str:
    locator_start = str(citation.get("locator_start") or "").strip()
    if not locator_start:
        return ""
    return locator_start
