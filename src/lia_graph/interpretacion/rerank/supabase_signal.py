"""Supabase hybrid_search relevance signal for rerank.

Only active when `LIA_CORPUS_SOURCE=supabase` (staging / production). In dev
(`artifacts` source) this is a no-op — returns 0.0 for every candidate so the
composer's weight on this signal collapses to nothing without any error.

The query path mirrors `pipeline_d/retriever_supabase._hybrid_search`: same
RPC, same OR-FTS query construction. The difference is what we *do* with the
result — here we only need a per-doc_id score, not chunk content.
"""

from __future__ import annotations

import os
import re
from typing import Any, Iterable

# Reuse the FTS OR-query builder so signals stay consistent with the
# read-path retriever. Importing from pipeline_d is acceptable because
# rerank is conceptually a sibling of retrieval, not synthesis.
from ...pipeline_d.retriever_supabase import _build_fts_or_query, _zero_embedding


_CORPUS_SOURCE_ENV = "LIA_CORPUS_SOURCE"
_FTS_TOKEN_RE = re.compile(r"[a-záéíóúñ0-9][-a-záéíóúñ0-9]*", re.IGNORECASE)


def is_active() -> bool:
    """True only when the runtime is reading the corpus from Supabase.

    The composer asks before calling so dev mode never imports the supabase
    SDK or pays a network roundtrip.
    """
    raw = str(os.getenv(_CORPUS_SOURCE_ENV, "") or "").strip().lower()
    return raw == "supabase"


def score_candidates(
    *,
    query_text: str,
    candidate_doc_ids: Iterable[str],
) -> tuple[dict[str, float], dict[str, Any]]:
    """Returns (per-doc_id score in 0..1, diagnostics).

    Score is the candidate's max `rrf_score` across any chunk hit; missing
    candidates get 0.0. Caller blends via composer weights.
    """
    doc_ids = [doc for doc in (str(item).strip() for item in candidate_doc_ids) if doc]
    if not doc_ids:
        return {}, {"mode": "skipped", "reason": "no_candidates"}

    if not is_active():
        return {doc: 0.0 for doc in doc_ids}, {"mode": "skipped", "reason": "not_supabase_mode"}

    try:
        from ...supabase_client import get_supabase_client

        db = get_supabase_client()
    except Exception as exc:  # noqa: BLE001 — signal must never raise to runner
        return {doc: 0.0 for doc in doc_ids}, {"mode": "client_error", "reason": str(exc)}

    payload = {
        "query_embedding": _zero_embedding(),
        "query_text": query_text,
        "filter_topic": None,
        "filter_pais": "colombia",
        "match_count": max(len(doc_ids) * 4, 24),
        "filter_knowledge_class": None,
        "filter_sync_generation": None,
        "fts_query": _build_fts_or_query(query_text),
        "filter_effective_date_max": None,
    }
    try:
        response = db.rpc("hybrid_search", payload).execute()
    except Exception as exc:  # noqa: BLE001
        return {doc: 0.0 for doc in doc_ids}, {"mode": "rpc_error", "reason": str(exc)}

    rows = getattr(response, "data", None) or []
    raw_by_doc: dict[str, float] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        doc_id = str(row.get("doc_id") or "").strip()
        if not doc_id:
            continue
        score = _coerce_score(row)
        existing = raw_by_doc.get(doc_id, 0.0)
        if score > existing:
            raw_by_doc[doc_id] = score

    normalized = _normalize_scores(raw_by_doc)
    return (
        {doc: normalized.get(doc, 0.0) for doc in doc_ids},
        {
            "mode": "supabase_hybrid_search",
            "rows_returned": len(rows),
            "candidates_matched": sum(1 for doc in doc_ids if doc in raw_by_doc),
        },
    )


def _coerce_score(row: dict[str, Any]) -> float:
    for key in ("rrf_score", "fts_rank", "score"):
        value = row.get(key)
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return 0.0


def _normalize_scores(raw: dict[str, float]) -> dict[str, float]:
    if not raw:
        return {}
    peak = max(raw.values())
    if peak <= 0:
        return {doc: 0.0 for doc in raw}
    return {doc: max(0.0, min(1.0, score / peak)) for doc, score in raw.items()}
