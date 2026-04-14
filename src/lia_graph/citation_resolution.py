from __future__ import annotations

from typing import Any

CANONICAL_REFERENCE_RELATION_TYPES = frozenset({"mentions", "supports", "interprets"})


def extract_reference_keys_from_citation_payload(payload: dict[str, Any] | None) -> list[str]:
    if not isinstance(payload, dict):
        return []
    key = str(payload.get("reference_key") or "").strip()
    return [key] if key else []


def build_identity_reference_keys(*args: Any, **kwargs: Any) -> list[str]:
    return []


def build_mentioned_reference_keys(*args: Any, **kwargs: Any) -> list[str]:
    return []


def collapse_citation_payloads(payloads: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return list(payloads or [])


def document_reference_semantics(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {"reference_keys": [], "relations": []}


def resolve_normative_mentions(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    return []


def reference_doc_catalog(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {}

