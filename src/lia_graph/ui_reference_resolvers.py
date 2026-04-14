from __future__ import annotations

from typing import Any


def _build_normative_helper_citations(*args: Any, **kwargs: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return [], {
        "mentions_detected": 0,
        "mentions_unique": 0,
        "mentions_already_covered": 0,
        "mentions_resolved_to_doc": 0,
        "mentions_unresolved": 0,
        "resolved_reference_keys": [],
        "unresolved_reference_keys": [],
    }


def _citation_targets_et_article(*args: Any, **kwargs: Any) -> list[str]:
    return []


def _merge_citation_payloads(
    payloads: list[dict[str, Any]] | None = None,
    extra_payloads: list[dict[str, Any]] | None = None,
    *args: Any,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for group in (payloads, extra_payloads):
        for item in list(group or []):
            if isinstance(item, dict):
                merged.append(dict(item))
    return merged
