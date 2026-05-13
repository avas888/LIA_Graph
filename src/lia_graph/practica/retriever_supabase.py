"""fix_v13_may — Supabase-backed dedicated retrieval lane for
`knowledge_class='practica_erp'` chunks.

Mirrors `interpretacion/retriever_supabase.py` but with three deliberate
differences:

1. **Hard `filter_knowledge_class='practica_erp'`** (not a soft boost).
   The dedicated lane's whole point is that its slots are reserved
   for práctica chunks. The unified retrieval lane keeps the v12
   `knowledge_class_boost` parameter wired as a rollback path.
2. **No `knowledge_class_boost` parameter.** The pool is already
   filtered to a single class; the boost would be a no-op.
3. **Trimmed grouping.** No trust-tier weighting (Phase 11A showed
   the layer was wrong when the section assembler is the bottleneck);
   no article-ref lexical boost (práctica chunks don't carry the same
   article-anchor index the interpretation corpus does).

Contract — mirrors the interpretation lane's duck-typed bundle so the
orchestrator dispatcher can swap implementations:

    fetch_practica_candidates(
        *, query_seed: str, topic: str | None, pais: str,
        top_k: int, client: Any | None = None,
    ) -> PracticaKnowledgeBundle

Errors propagate. The orchestrator dispatcher decides fallback; this
module never silently degrades to filesystem (per CLAUDE.md "Falkor
adapter must propagate cloud outages — no silent artifact fallback").
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any, Callable

from ..supabase_client import get_supabase_client
from .policy import (
    DEFAULT_TOPIC_BOOST,
    MATCH_COUNT_MULTIPLIER,
    MIN_MATCH_COUNT,
)
from .shared import PracticaChunkRuntime, PracticaKnowledgeBundle


LOGGER = logging.getLogger(__name__)


def _trace_step(name: str, **payload: Any) -> None:
    """Best-effort pipeline-trace emission. The trace module may not be
    importable from every entry point (notably tests that stub the
    Supabase client). When unavailable, the structured log line still
    captures everything diagnostic-side."""
    try:
        from tracers_and_logs import pipeline_trace as _trace
    except Exception:  # pragma: no cover — defensive
        return
    try:
        _trace.step(name, **payload)
    except Exception:  # pragma: no cover — never break retrieval on trace failure
        LOGGER.debug("practica trace step %s failed", name, exc_info=True)


_FTS_TOKEN_RE = re.compile(r"[A-Za-zÁÉÍÓÚáéíóúñÑ0-9_-]{2,}")
_FTS_STOPWORDS = frozenset(
    {
        "el", "la", "los", "las", "de", "del", "y", "o", "u",
        "en", "a", "al", "por", "para", "con", "sin", "su", "sus",
        "que", "qué", "como", "cómo", "es", "son", "se", "lo", "le",
        "un", "una", "unos", "unas", "mi", "tu", "te", "me", "ya",
        "art", "et", "tr",
    }
)


def _normalize_pais(pais: str | None) -> str:
    return (str(pais or "colombia").strip().lower()) or "colombia"


def _build_fts_query(query_seed: str) -> str | None:
    """OR-tokenized tsquery from the user's question. No article-ref
    prepend (cf. interpretacion lane): práctica chunks index against
    operational keywords, not article numbers."""
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in _FTS_TOKEN_RE.findall(str(query_seed or "")):
        token = raw.lower().strip("-")
        if len(token) < 2 or token in _FTS_STOPWORDS or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    if not ordered:
        return None
    return " | ".join(ordered)


def _hybrid_search_payload(
    *,
    query_embedding: tuple[float, ...] | list[float] | None,
    fts_query: str | None,
    topic: str | None,
    pais: str,
    match_count: int,
    topic_boost: float = DEFAULT_TOPIC_BOOST,
) -> dict[str, Any]:
    """Construct the RPC payload. Hard-filters on `practica_erp`;
    topic stays as a ranking signal (boost_topic), never a WHERE
    filter (chat-path invariant from fix_v7 §3a)."""
    payload: dict[str, Any] = {
        "query_embedding": list(query_embedding) if query_embedding else None,
        "query_text": fts_query or "",
        "filter_topic": None,
        "filter_pais": pais,
        "match_count": match_count,
        "filter_knowledge_class": "practica_erp",
        "filter_sync_generation": None,
        "fts_query": fts_query,
        "filter_effective_date_max": None,
    }
    if topic and topic_boost > 1.0:
        payload["boost_topic"] = topic
        payload["filter_topic_boost"] = topic_boost
    return payload


def _call_hybrid_search(
    client: Any, payload: dict[str, Any]
) -> list[dict[str, Any]]:
    """Call the RPC with the older-deploy fallback ladder. Strip
    `boost_topic` + `filter_topic_boost` for pre-2026-05-12 deploys
    that don't have migration 20260512000000 applied."""
    try:
        resp = client.rpc("hybrid_search", payload).execute()
    except Exception:
        retry = dict(payload)
        retry.pop("boost_topic", None)
        retry.pop("filter_topic_boost", None)
        resp = client.rpc("hybrid_search", retry).execute()
    rows = list(getattr(resp, "data", None) or [])
    return [dict(r) for r in rows if isinstance(r, dict)]


def _group_chunks_by_doc(
    chunk_rows: list[dict[str, Any]],
    *,
    top_k: int,
) -> list[tuple[str, dict[str, Any], float]]:
    """Pick one representative chunk per doc (the highest-scoring),
    return them ordered by score descending and truncated to `top_k`.

    Trimmed vs the interpretacion lane: no trust-tier multiplier
    (Phase 11A SME panel moved 0pt with that lever at this layer),
    no article-ref lexical boost (práctica chunks don't carry an
    article-anchor index).
    """
    best: dict[str, tuple[float, dict[str, Any]]] = {}
    for row in chunk_rows:
        doc_id = str(row.get("doc_id") or "").strip()
        if not doc_id:
            continue
        score = float(row.get("rrf_score") or row.get("fts_rank") or 0.0)
        prev = best.get(doc_id)
        if prev is None or score > prev[0]:
            best[doc_id] = (score, row)
    ordered = sorted(best.items(), key=lambda kv: kv[1][0], reverse=True)
    return [(doc_id, row, score) for doc_id, (score, row) in ordered[:top_k]]


def _fetch_doc_metadata(
    client: Any, doc_ids: list[str]
) -> dict[str, dict[str, Any]]:
    """One batched lookup: doc_id → {authority, provider_labels}.

    Práctica chunks need a source label to render; the chunk row
    carries `summary` but the human-readable authority lives on
    `documents.authority`.
    """
    if not doc_ids:
        return {}
    out: dict[str, dict[str, Any]] = {}
    batch = 100
    for start in range(0, len(doc_ids), batch):
        chunk = doc_ids[start : start + batch]
        resp = (
            client.table("documents")
            .select("doc_id,authority,provider_labels")
            .in_("doc_id", chunk)
            .execute()
        )
        for row in getattr(resp, "data", None) or []:
            doc_id = str(row.get("doc_id") or "")
            if not doc_id:
                continue
            out[doc_id] = {
                "authority": str(row.get("authority") or "").strip(),
                "provider_labels": [
                    str(p)
                    for p in (row.get("provider_labels") or [])
                    if str(p).strip()
                ],
                # `source_label` is derived from the chunk row's `summary`
                # downstream in `_row_to_runtime`; the documents table
                # doesn't carry a `source_label` column in this schema.
                "source_label": "",
            }
    return out


def _row_to_runtime(
    *,
    doc_id: str,
    chunk_row: dict[str, Any],
    raw_score: float,
    max_score: float,
    metadata: dict[str, Any],
) -> PracticaChunkRuntime:
    relative_path = str(chunk_row.get("relative_path") or "")
    heading = (
        metadata.get("source_label")
        or str(chunk_row.get("summary") or "").strip()
        or doc_id
    )
    authority = metadata.get("authority") or ""
    if not authority:
        provider_labels = metadata.get("provider_labels") or []
        if provider_labels:
            authority = str(provider_labels[0])
    if not authority:
        authority = "Guía práctica"
    normalized_score = round(
        min(1.0, float(raw_score) / float(max_score or 1.0)), 4
    )
    normative_refs = tuple(
        str(item).strip()
        for item in (chunk_row.get("concept_tags") or ())
        if str(item).strip()
    )
    return PracticaChunkRuntime(
        doc_id=doc_id,
        relative_path=relative_path,
        source_label=heading,
        authority=authority,
        chunk_text=str(chunk_row.get("chunk_text") or ""),
        retrieval_score=normalized_score,
        knowledge_class="practica_erp",
        normative_refs=normative_refs,
    )


def fetch_practica_candidates(
    *,
    query_seed: str,
    topic: str | None = None,
    pais: str = "colombia",
    top_k: int = 3,
    client: Any | None = None,
    chunk_filter: Callable[[list[dict[str, Any]]], list[dict[str, Any]]] | None = None,
) -> PracticaKnowledgeBundle:
    """Dedicated práctica retrieval lane. Returns a
    `PracticaKnowledgeBundle` with `chunks_selected` + diagnostics.

    Errors from the RPC propagate to the caller (the orchestrator
    dispatcher). Per CLAUDE.md, the Supabase adapter never silently
    falls back to filesystem on staging; that decision lives one
    layer up.
    """
    t_start = time.perf_counter()
    db = client if client is not None else get_supabase_client()
    pais_clean = _normalize_pais(pais)
    fts_query = _build_fts_query(query_seed)
    _trace_step(
        "practica.retriever.entry",
        status="info",
        query_chars=len(query_seed or ""),
        query_preview=str(query_seed or "")[:160],
        topic=topic,
        pais=pais_clean,
        top_k=top_k,
        fts_query=fts_query[:200] if fts_query else None,
        fts_query_token_count=len((fts_query or "").split("|"))
            if fts_query else 0,
        chunk_filter_present=chunk_filter is not None,
    )
    LOGGER.info(
        "practica.retriever.entry topic=%s top_k=%d fts_tokens=%d filter=%s",
        topic,
        top_k,
        len((fts_query or "").split("|")) if fts_query else 0,
        bool(chunk_filter is not None),
    )
    # Lazy import — embeddings module pulls in HTTP deps we don't
    # want at module-load time for unit tests that stub the client.
    try:
        from ..embeddings import get_query_embedding
    except Exception:  # pragma: no cover — defensive
        get_query_embedding = None  # type: ignore[assignment]
    query_embedding: tuple[float, ...] | None = None
    embedding_mode = "skipped"
    if get_query_embedding is not None and os.environ.get(
        "LIA_QUERY_EMBEDDINGS_ENABLED", "1"
    ) != "0":
        try:
            embedded = get_query_embedding(query_seed)
            if embedded:
                query_embedding = tuple(embedded)
                embedding_mode = "ok"
        except Exception:  # pragma: no cover — degrade gracefully
            embedding_mode = "error"

    match_count = max(top_k * MATCH_COUNT_MULTIPLIER, MIN_MATCH_COUNT)
    payload = _hybrid_search_payload(
        query_embedding=query_embedding,
        fts_query=fts_query,
        topic=topic,
        pais=pais_clean,
        match_count=match_count,
    )
    _trace_step(
        "practica.retriever.hybrid_search.in",
        status="info",
        match_count=match_count,
        filter_knowledge_class=payload.get("filter_knowledge_class"),
        filter_topic=payload.get("filter_topic"),
        boost_topic=payload.get("boost_topic"),
        filter_topic_boost=payload.get("filter_topic_boost"),
        fts_query_present=bool(payload.get("fts_query")),
        embedding_mode=embedding_mode,
        embedding_dim=len(query_embedding) if query_embedding else 0,
    )
    t_rpc = time.perf_counter()
    try:
        chunk_rows = _call_hybrid_search(db, payload)
    except Exception as exc:
        rpc_elapsed_ms = round((time.perf_counter() - t_rpc) * 1000.0, 2)
        _trace_step(
            "practica.retriever.hybrid_search.error",
            status="error",
            error_kind=type(exc).__name__,
            error=repr(exc)[:240],
            elapsed_ms=rpc_elapsed_ms,
        )
        LOGGER.warning(
            "practica.retriever.hybrid_search.error kind=%s elapsed_ms=%.1f",
            type(exc).__name__,
            rpc_elapsed_ms,
        )
        raise
    rpc_elapsed_ms = round((time.perf_counter() - t_rpc) * 1000.0, 2)
    raw_rows = len(chunk_rows)
    top_doc_ids_pre_gate = [
        str(r.get("doc_id"))
        for r in chunk_rows[:8]
        if isinstance(r, dict) and r.get("doc_id")
    ]
    top_classes_pre_gate = [
        str(r.get("knowledge_class") or "")
        for r in chunk_rows[:8]
        if isinstance(r, dict)
    ]
    _trace_step(
        "practica.retriever.hybrid_search.out",
        status="ok" if chunk_rows else "fallback",
        row_count=raw_rows,
        elapsed_ms=rpc_elapsed_ms,
        top_doc_ids=top_doc_ids_pre_gate,
        top_knowledge_classes=top_classes_pre_gate,
        non_practica_top=sum(
            1
            for r in chunk_rows[:8]
            if isinstance(r, dict)
            and r.get("knowledge_class") not in (None, "practica_erp")
        ),
    )
    LOGGER.info(
        "practica.retriever.hybrid_search.out rows=%d elapsed_ms=%.1f",
        raw_rows,
        rpc_elapsed_ms,
    )

    gate_dropped = 0
    gate_elapsed_ms = 0.0
    gate_error_kind: str | None = None
    if chunk_filter is not None:
        t_gate = time.perf_counter()
        try:
            filtered_rows = list(chunk_filter(chunk_rows))
        except Exception as exc:  # pragma: no cover — gate must never break retrieval
            gate_error_kind = type(exc).__name__
            LOGGER.warning(
                "practica.retriever.quality_gate.error kind=%s",
                gate_error_kind,
                exc_info=True,
            )
            filtered_rows = chunk_rows
        gate_elapsed_ms = round((time.perf_counter() - t_gate) * 1000.0, 2)
        gate_dropped = max(0, raw_rows - len(filtered_rows))
        dropped_doc_ids = sorted(
            {str(r.get("doc_id")) for r in chunk_rows if isinstance(r, dict)}
            - {str(r.get("doc_id")) for r in filtered_rows if isinstance(r, dict)}
        )[:8]
        _trace_step(
            "practica.retriever.quality_gate",
            status="ok" if gate_error_kind is None else "error",
            rows_in=raw_rows,
            rows_out=len(filtered_rows),
            dropped_count=gate_dropped,
            elapsed_ms=gate_elapsed_ms,
            error_kind=gate_error_kind,
            dropped_doc_id_sample=dropped_doc_ids,
        )
        LOGGER.info(
            "practica.retriever.quality_gate rows_in=%d rows_out=%d dropped=%d elapsed_ms=%.1f",
            raw_rows,
            len(filtered_rows),
            gate_dropped,
            gate_elapsed_ms,
        )
        chunk_rows = filtered_rows

    grouped = _group_chunks_by_doc(chunk_rows, top_k=top_k)
    _trace_step(
        "practica.retriever.group",
        status="ok",
        rows_in=len(chunk_rows),
        groups_out=len(grouped),
        top_k=top_k,
        top_groups=[
            {
                "doc_id": doc_id,
                "score": round(float(score), 6),
            }
            for doc_id, _row, score in grouped[:5]
        ],
    )
    if not grouped:
        total_elapsed_ms = round((time.perf_counter() - t_start) * 1000.0, 2)
        _trace_step(
            "practica.retriever.exit",
            status="empty",
            selected_chunks=0,
            elapsed_ms=total_elapsed_ms,
        )
        LOGGER.info(
            "practica.retriever.exit selected=0 elapsed_ms=%.1f",
            total_elapsed_ms,
        )
        return PracticaKnowledgeBundle(
            chunks_selected=(),
            retrieval_diagnostics={
                "practica_backend": "supabase",
                "mode": "supabase_hybrid_search",
                "candidate_rows": raw_rows,
                "candidate_rows_after_gate": len(chunk_rows),
                "gate_dropped": gate_dropped,
                "gate_elapsed_ms": gate_elapsed_ms,
                "gate_error_kind": gate_error_kind,
                "selected_chunks": 0,
                "embedding_mode": embedding_mode,
                "fts_query_present": bool(fts_query),
                "topic_boost": topic if topic else None,
                "hybrid_search_elapsed_ms": rpc_elapsed_ms,
                "total_elapsed_ms": total_elapsed_ms,
            },
        )

    doc_ids = [doc_id for doc_id, _row, _score in grouped]
    metadata_by_doc = _fetch_doc_metadata(db, doc_ids)
    max_score = max((score for _id, _row, score in grouped), default=1.0) or 1.0
    runtimes = tuple(
        _row_to_runtime(
            doc_id=doc_id,
            chunk_row=row,
            raw_score=score,
            max_score=max_score,
            metadata=metadata_by_doc.get(doc_id, {}),
        )
        for doc_id, row, score in grouped
    )

    total_elapsed_ms = round((time.perf_counter() - t_start) * 1000.0, 2)
    diagnostics = {
        "practica_backend": "supabase",
        "mode": "supabase_hybrid_search",
        "candidate_rows": raw_rows,
        "candidate_rows_after_gate": len(chunk_rows),
        "gate_dropped": gate_dropped,
        "gate_elapsed_ms": gate_elapsed_ms,
        "gate_error_kind": gate_error_kind,
        "selected_chunks": len(runtimes),
        "embedding_mode": embedding_mode,
        "fts_query_present": bool(fts_query),
        "topic_boost": topic if topic else None,
        "hybrid_search_elapsed_ms": rpc_elapsed_ms,
        "total_elapsed_ms": total_elapsed_ms,
        "selected_doc_ids": [r.doc_id for r in runtimes],
        "selected_authorities": [r.authority for r in runtimes],
        "selected_score_range": {
            "min": min((r.retrieval_score for r in runtimes), default=0.0),
            "max": max((r.retrieval_score for r in runtimes), default=0.0),
        },
    }
    _trace_step(
        "practica.retriever.exit",
        status="ok",
        selected_chunks=len(runtimes),
        elapsed_ms=total_elapsed_ms,
        selected_doc_ids=diagnostics["selected_doc_ids"],
        selected_authorities=diagnostics["selected_authorities"],
    )
    LOGGER.info(
        "practica.retriever.exit selected=%d elapsed_ms=%.1f doc_ids=%s",
        len(runtimes),
        total_elapsed_ms,
        diagnostics["selected_doc_ids"],
    )
    return PracticaKnowledgeBundle(
        chunks_selected=runtimes,
        retrieval_diagnostics=diagnostics,
    )


__all__ = [
    "fetch_practica_candidates",
    "_build_fts_query",
    "_hybrid_search_payload",
    "_group_chunks_by_doc",
]
