from __future__ import annotations

from typing import Any


def _build_citation_usage_payload(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {}


def _build_extractive_interpretation_summary(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {}


def _build_interpretation_query_seed(*args: Any, **kwargs: Any) -> str:
    return ""


def _build_public_citation_from_row(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {}


def _enrich_citation_payloads_with_usage_context(
    payloads: list[dict[str, Any]] | None = None,
    *args: Any,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    resolved = payloads
    if resolved is None:
        resolved = kwargs.get("citations_payload")
    return list(resolved or [])


def _extract_usage_context_from_answer(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {}


def _extract_usage_context_from_diagnostics(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {}


def _hydrate_citation_download_urls(payloads: list[dict[str, Any]] | None, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    return list(payloads or [])


def _load_doc_corpus_text(*args: Any, **kwargs: Any) -> str:
    return ""


def _load_doc_index_row(*args: Any, **kwargs: Any) -> dict[str, Any] | None:
    return None
