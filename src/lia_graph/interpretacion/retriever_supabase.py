"""fix_v10_may Phase 10B — Supabase-backed retriever for the
Interpretación de Expertos panel.

Routes the expert-panel side-bar through the same `hybrid_search`
RPC the chat already uses, instead of `interpretacion/catalog.py`'s
linear scan of `artifacts/canonical_corpus_manifest.json` followed
by a per-request markdown read off disk.

Contract (matches `orchestrator._retrieve_interpretation_docs`'s
return shape so the dispatcher can swap implementations without
touching downstream code):

    fetch_interpretation_candidates(
        *, query_seed: str, article_refs: tuple[str, ...],
        topic: str | None, pais: str, top_k: int,
        client: Any | None = None,
    ) -> InterpretationKnowledgeBundle

Where ``InterpretationKnowledgeBundle`` is the ad-hoc duck-typed
object the catalog path produces: ``docs_selected`` (tuple of
``DocumentRecord``) + ``retrieval_diagnostics`` (dict).

Errors propagate. Per CLAUDE.md, the Supabase adapter must never
silently fall back to artifacts on staging — the dispatcher in
``orchestrator._retrieve_interpretation_docs`` is the only place
that may pick the filesystem fallback, and only when
``LIA_INTERPRETATION_SOURCE != 'supabase'``.
"""

from __future__ import annotations

import os
import re
from typing import Any

from ..contracts.document import DocumentRecord
from ..supabase_client import get_supabase_client


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


def _build_fts_query(query_seed: str, article_refs: tuple[str, ...]) -> str | None:
    """OR-tokenized tsquery that always carries the article refs.

    Strategy: §3.B of the canonical doc wants article refs treated as
    "required" so the lexical-precision intent of the legacy
    `2.5*ref_hits` scoring is preserved. Since the RPC concatenates
    fts_query into a single tsquery applied with OR semantics, we
    can't make refs strictly required without changing the SQL. We
    do the next-best thing: include both the refs AND the seed
    tokens; rerank handles final ordering. RRF's `fts_rank` will
    still bump rows that contain refs because every ref appears as
    a positive-weight token in the tsquery.
    """
    seen: set[str] = set()
    ordered: list[str] = []
    # article_refs first so they appear early in the tsquery (Postgres
    # weights position somewhat) and so they're never dropped by the
    # dedup-then-truncate flow.
    for ref in article_refs:
        token = str(ref or "").strip().lower()
        if not token or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
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
) -> dict[str, Any]:
    """Construct the RPC payload. Matches the chat-path conventions:
    `filter_topic=None` (topic is a ranking signal, not a WHERE
    filter), boost via `boost_topic` if a topic was resolved.
    """
    payload: dict[str, Any] = {
        "query_embedding": list(query_embedding) if query_embedding else None,
        "query_text": fts_query or "",
        "filter_topic": None,
        "filter_pais": pais,
        "match_count": match_count,
        # The keystone — only interpretation chunks come back. Phase 10A
        # backfill made this filter actually work; pre-10A it would have
        # returned 0 rows.
        "filter_knowledge_class": "interpretative_guidance",
        "filter_sync_generation": None,
        "fts_query": fts_query,
        "filter_effective_date_max": None,
    }
    if topic:
        payload["boost_topic"] = topic
        # fix_v10_may §5.2 gate-6 lever (a) — interpretation corpus is
        # smaller and topic-coherent at the doc level; stronger boost
        # (2.5 vs the chat path's 1.5) pushes topic-matched expert docs
        # past topic-adjacent ones without affecting recall (boost is a
        # multiplier on the RRF score, not a WHERE filter). Bumped after
        # the first 21-Q mini-panel run scored 33% accept@top3 because
        # RENTA-class questions surfaced ZOMAC / IVA-proporcionalidad /
        # Reforma-Laboral cards above the on-topic Crowe analyses.
        payload["filter_topic_boost"] = 2.5
    return payload


def _call_hybrid_search(
    client: Any, payload: dict[str, Any]
) -> list[dict[str, Any]]:
    """Call the RPC with the older-deploy fallback ladder used by the
    chat retriever. Strip `boost_topic` / `filter_topic_boost` if the
    RPC rejects them (pre-2026-05-12 deploys).
    """
    try:
        resp = client.rpc("hybrid_search", payload).execute()
    except Exception:
        retry = dict(payload)
        retry.pop("boost_topic", None)
        retry.pop("filter_topic_boost", None)
        resp = client.rpc("hybrid_search", retry).execute()
    rows = list(getattr(resp, "data", None) or [])
    return [dict(r) for r in rows if isinstance(r, dict)]


_ARTICLE_REF_TOKEN_RE = __import__("re").compile(
    r"\b(?:art(?:[íi]culo)?\.?|art_)\s*(\d+(?:[\-\.]\d+)?)",
    __import__("re").IGNORECASE,
)


def _chunk_article_ref_hits(text: str, article_refs: tuple[str, ...]) -> int:
    """Count how many article refs appear as `art. N` / `art_N` / etc
    in the chunk text. Used by lever (b) — strengthen lexical precision
    on top of RRF without changing the SQL layer."""
    if not text or not article_refs:
        return 0
    # Build a normalized set of expected article numbers from the
    # canonical refs ("art_115_et" → "115", "art_124_2_et" → "124_2" → "124-2"/"124.2").
    want: set[str] = set()
    for ref in article_refs:
        s = str(ref or "").strip().lower()
        # Strip leading "art_"/"et_art_" then take first numeric run
        m = __import__("re").match(r"(?:et_)?art_(\d+(?:[\-_\.]\d+)?)", s)
        if m:
            num = m.group(1).replace("_", "-")
            want.add(num)
            want.add(num.replace("-", "."))
            want.add(num.replace("-", ""))
    if not want:
        return 0
    hits = 0
    for m in _ARTICLE_REF_TOKEN_RE.finditer(text):
        num = m.group(1).lower()
        if num in want:
            hits += 1
    return hits


def _group_chunks_by_doc(
    chunk_rows: list[dict[str, Any]],
    *,
    top_k: int,
    article_refs: tuple[str, ...] = (),
    lexical_ref_boost: float = 0.25,
) -> list[tuple[str, dict[str, Any], float]]:
    """Pick one representative chunk per doc (the highest-scoring),
    return them ordered by score descending and truncated to `top_k`.

    Each tuple is `(doc_id, chunk_row, score)`. The score prefers
    `rrf_score` (when present from hybrid_search), falling back to
    `fts_rank` or 0.0.

    fix_v10_may §5.2 gate-6 lever (b) — when `article_refs` is
    non-empty, each chunk's score is multiplied by
    `(1.0 + lexical_ref_boost * hits)` where `hits` is the count of
    those refs appearing inline in the chunk text. Restores the
    lexical-precision intent of the legacy catalog's `2.5 * ref_hits`
    scoring without requiring SQL-level changes. Default boost
    (0.25) was tuned to push T-B-costos-deducciones above
    ZOMAC/IVA-proporcionalidad cards on the ICA-deduccion-in-renta
    query without over-boosting article-mention-heavy normative
    fragments that happen to land in interpretation docs.
    """
    best: dict[str, tuple[float, dict[str, Any]]] = {}
    for row in chunk_rows:
        doc_id = str(row.get("doc_id") or "").strip()
        if not doc_id:
            continue
        base = float(row.get("rrf_score") or row.get("fts_rank") or 0.0)
        if article_refs:
            hits = _chunk_article_ref_hits(
                str(row.get("chunk_text") or ""), article_refs
            )
            score = base * (1.0 + lexical_ref_boost * hits)
        else:
            score = base
        prev = best.get(doc_id)
        if prev is None or score > prev[0]:
            best[doc_id] = (score, row)
    ordered = sorted(
        best.items(), key=lambda kv: kv[1][0], reverse=True
    )
    return [(doc_id, row, score) for doc_id, (score, row) in ordered[:top_k]]


def _fetch_provider_labels(
    client: Any, doc_ids: list[str]
) -> dict[str, list[str]]:
    """One batched lookup: doc_id → provider_labels.

    Phase 10B reads providers off the new `documents.provider_labels`
    column (migration 20260513000000). For docs with no providers the
    column carries `[]`; for normative_base docs it's also `[]`.
    """
    if not doc_ids:
        return {}
    out: dict[str, list[str]] = {}
    batch = 100
    for start in range(0, len(doc_ids), batch):
        chunk = doc_ids[start : start + batch]
        resp = (
            client.table("documents")
            .select("doc_id,provider_labels,authority")
            .in_("doc_id", chunk)
            .execute()
        )
        for row in getattr(resp, "data", None) or []:
            doc_id = str(row.get("doc_id") or "")
            labels = row.get("provider_labels") or []
            if not isinstance(labels, list):
                labels = []
            out[doc_id] = [str(p) for p in labels if str(p).strip()]
    return out


def _row_to_document_record(
    *,
    doc_id: str,
    chunk_row: dict[str, Any],
    raw_score: float,
    max_score: float,
    provider_labels: list[str],
) -> DocumentRecord:
    """Build the `DocumentRecord` the orchestrator's downstream
    runtime builders expect (`_build_runtime_for_doc` at
    orchestrator.py:87-133).
    """
    relative_path = str(chunk_row.get("relative_path") or "")
    heading = str(chunk_row.get("summary") or "").strip() or doc_id
    authority = str(chunk_row.get("authority") or "").strip()
    if not authority and provider_labels:
        authority = provider_labels[0]
    payload: dict[str, Any] = {
        "doc_id": doc_id,
        "absolute_path": "",  # Supabase-served — no filesystem path
        "relative_path": relative_path,
        "source_label": heading,
        "legal_reference": heading,
        "authority": authority or "Fuente profesional",
        "provider_labels": list(provider_labels),
        "providers": [{"name": p} for p in provider_labels],
        "normative_refs": list(chunk_row.get("concept_tags") or []),
        "topic": str(chunk_row.get("topic") or "unknown") or "unknown",
        "subtema": str(chunk_row.get("subtema") or "").strip(),
        "source_type": str(chunk_row.get("source_type") or "markdown"),
        "category": "interpretative_guidance",
        "knowledge_class": "interpretative_guidance",
        "pais": str(chunk_row.get("pais") or "colombia"),
        "trust_tier": str(chunk_row.get("trust_tier") or "medium")
            .strip() or "medium",
        "retrieval_score": round(
            min(1.0, float(raw_score) / float(max_score or 1.0)), 4
        ),
        # The catalog-path returns a `__catalog_preview` from a disk read.
        # We pack the chunk_text here so downstream synthesis has SOME
        # body text to summarize without re-reading the .md.
        "__catalog_preview": str(chunk_row.get("chunk_text") or ""),
    }
    return DocumentRecord.from_dict(payload)


def fetch_interpretation_candidates(
    *,
    query_seed: str,
    article_refs: tuple[str, ...] = (),
    topic: str | None = None,
    pais: str = "colombia",
    top_k: int = 8,
    client: Any | None = None,
) -> Any:
    """Supabase-backed counterpart to
    `orchestrator._retrieve_interpretation_docs`.

    Returns a duck-typed `InterpretationKnowledgeBundle` with
    `docs_selected` + `retrieval_diagnostics`. The diagnostic carries
    `interpretation_backend = 'supabase'` so callers can confirm
    which path served the panel (parallels the chat retriever's
    `retrieval_backend`).
    """
    db = client if client is not None else get_supabase_client()
    pais_clean = _normalize_pais(pais)
    fts_query = _build_fts_query(query_seed, tuple(article_refs))
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
    payload = _hybrid_search_payload(
        query_embedding=query_embedding,
        fts_query=fts_query,
        topic=topic,
        pais=pais_clean,
        match_count=max(top_k * 4, 32),
    )
    chunk_rows = _call_hybrid_search(db, payload)

    # fix_v10_may Phase 10C — anchor BOOST (not filter). When the
    # planner has resolved article refs, consult the article→doc index;
    # chunks whose parent doc actually interprets one of those articles
    # get a multiplicative score boost. We deliberately do NOT
    # hard-filter the candidate set: an earlier hard-filter version
    # regressed the mini-panel from 43 % → 28 % because (a) the index
    # only knows what the corpus's `extract_article_refs` regex caught,
    # and (b) some questions have right answers under article numbers
    # the regex missed (e.g. `art_124_2` for Panama-deducibilidad
    # questions, where the corpus uses `art_260-1/2/5` instead).
    # Boost-only keeps recall intact — when the index has hits the right
    # doc rises, when it doesn't we degrade to lever (a)+(b) behavior.
    anchor_boosted_count = 0
    anchor_eligible_doc_ids: frozenset[str] = frozenset()
    if article_refs:
        try:
            from .article_index import doc_ids_for_article_refs
            anchor_eligible_doc_ids = doc_ids_for_article_refs(article_refs)
        except Exception:  # pragma: no cover — never break retrieval
            anchor_eligible_doc_ids = frozenset()
    if anchor_eligible_doc_ids:
        for row in chunk_rows:
            doc_id = str(row.get("doc_id") or "").strip()
            if doc_id in anchor_eligible_doc_ids:
                base = float(row.get("rrf_score") or row.get("fts_rank") or 0.0)
                row["rrf_score"] = base * 4.0
                anchor_boosted_count += 1

    grouped = _group_chunks_by_doc(
        chunk_rows, top_k=top_k, article_refs=tuple(article_refs)
    )
    if not grouped:
        bundle_docs: list[DocumentRecord] = []
        diagnostics = {
            "mode": "supabase_hybrid_search",
            "interpretation_backend": "supabase",
            "candidate_rows": len(chunk_rows),
            "selected_docs": 0,
            "embedding_mode": embedding_mode,
            "fts_query_present": bool(fts_query),
            "topic_boost": topic if topic else None,
            "interpretation_anchor_eligible_docs": len(anchor_eligible_doc_ids),
            "interpretation_anchor_boosted_chunks": anchor_boosted_count,
        }
    else:
        doc_ids = [doc_id for doc_id, _row, _score in grouped]
        providers_by_doc = _fetch_provider_labels(db, doc_ids)
        max_score = max((score for _id, _row, score in grouped), default=1.0) or 1.0
        bundle_docs = [
            _row_to_document_record(
                doc_id=doc_id,
                chunk_row=row,
                raw_score=score,
                max_score=max_score,
                provider_labels=providers_by_doc.get(doc_id, []),
            )
            for doc_id, row, score in grouped
        ]
        diagnostics = {
            "mode": "supabase_hybrid_search",
            "interpretation_backend": "supabase",
            "candidate_rows": len(chunk_rows),
            "selected_docs": len(bundle_docs),
            "embedding_mode": embedding_mode,
            "fts_query_present": bool(fts_query),
            "topic_boost": topic if topic else None,
            "interpretation_anchor_eligible_docs": len(anchor_eligible_doc_ids),
            "interpretation_anchor_boosted_chunks": anchor_boosted_count,
        }
    return type(
        "InterpretationKnowledgeBundle",
        (),
        {
            "docs_selected": tuple(bundle_docs),
            "retrieval_diagnostics": diagnostics,
        },
    )()


__all__ = ["fetch_interpretation_candidates"]
