"""Hybrid-search RPC + embedding + boosts carve-out from
``retriever_supabase.py`` (fix_v16 b5 — keep no file ≥ 1000 LOC).

Owns three responsibilities the staging chat path depends on but that
were bloating the main retriever module:

1. **Boost-factor env resolution** (subtopic / topic / practica)
2. **FTS OR-query builder** (`to_tsquery`-friendly tokens)
3. **`hybrid_search` RPC call** (with the two-stage param-recovery
   fallback for older deploys without the `boost_topic` /
   `boost_knowledge_class` migrations)
4. **Query embedding** (`gemini-embedding-001`, with env kill-switch
   and zero-vector safety net)
5. **Client-side subtopic boost** (post-RPC reranking)

The main module imports each of these by name. No behavioral changes
were made during the carve-out — same defaults, same env flags, same
fallback ladder.
"""
from __future__ import annotations

import os
import re
from typing import Any

from .contracts import GraphRetrievalPlan

_QUERY_EMBED_DIM = 768
_QUERY_EMBED_ENV_FLAG = "LIA_QUERY_EMBEDDINGS_ENABLED"

_FTS_TOKEN_RE = re.compile(r"[a-záéíóúñ0-9][-a-záéíóúñ0-9]*", re.IGNORECASE)
# Spanish stopwords that would either be dropped by to_tsquery or hurt recall
# if kept. Kept short on purpose — aggressive filtering is handled by the
# RPC's `to_tsquery('spanish', ...)` which applies the Spanish dictionary.
_FTS_STOPWORDS = frozenset(
    {
        "a", "al", "de", "del", "en", "la", "el", "los", "las", "un", "una",
        "unos", "unas", "o", "u", "y", "e", "que", "para", "por", "con", "sin",
        "sobre", "se", "su", "sus", "mi", "mis", "tu", "tus", "lo", "le", "les",
        "como", "si", "no", "ni", "es", "son", "ser", "ha", "he", "han", "haya",
    }
)


# --- boost-factor resolvers -------------------------------------------------


def _resolve_subtopic_boost_factor() -> float:
    """Read ``LIA_SUBTOPIC_BOOST_FACTOR`` env; default 1.5 (Decision G1+G3).

    Coerces to float and floors at 1.0 so the boost can never penalize
    (Invariant I5).
    """
    raw = os.getenv("LIA_SUBTOPIC_BOOST_FACTOR")
    if raw is None or not str(raw).strip():
        return 1.5
    try:
        parsed = float(raw)
    except (TypeError, ValueError):
        return 1.5
    return max(parsed, 1.0)


def _resolve_topic_boost_factor() -> float:
    """v5 §1.D — Read ``LIA_TOPIC_BOOST_FACTOR`` env; default 1.5.

    Mirrors `_resolve_subtopic_boost_factor` shape but applies to the
    chunk-level topic match (not subtopic). Floors at 1.0 (Invariant I5,
    never penalize). When the value is exactly 1.0, the boost is OFF and
    `filter_topic` stays None in the RPC payload — preserving pre-§1.D
    behavior. Set to 1.5+ to enable the boost.
    """
    raw = os.getenv("LIA_TOPIC_BOOST_FACTOR")
    if raw is None or not str(raw).strip():
        return 1.5
    try:
        parsed = float(raw)
    except (TypeError, ValueError):
        return 1.5
    return max(parsed, 1.0)


def _resolve_practica_boost_factor() -> float:
    """fix_v12 §2.C — Read ``LIA_PRACTICA_BOOST_FACTOR`` env; default 1.5."""
    raw = os.getenv("LIA_PRACTICA_BOOST_FACTOR")
    if raw is None or not str(raw).strip():
        return 1.5
    try:
        parsed = float(raw)
    except (TypeError, ValueError):
        return 1.5
    return max(parsed, 1.0)


# --- FTS query builder ------------------------------------------------------


def _build_fts_or_query(query_text: str) -> str | None:
    """Turn the planner's concatenated `query_text` into an OR-connected
    `to_tsquery` expression so FTS recall is not gated by term-AND.

    Returns `None` when no usable tokens remain, which makes the RPC fall
    back to its `plainto_tsquery(query_text)` default.
    """
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in _FTS_TOKEN_RE.findall(query_text or ""):
        token = raw.lower().strip("-")
        if len(token) < 2:
            continue
        if token in _FTS_STOPWORDS:
            continue
        if token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    if not ordered:
        return None
    return " | ".join(ordered)


# --- embedding helpers ------------------------------------------------------


def _query_embeddings_enabled() -> bool:
    raw = str(os.getenv(_QUERY_EMBED_ENV_FLAG, "1") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _zero_embedding() -> list[float]:
    """Safety-net 768-dim zero vector.

    Returned when the real query embedding is unavailable. Callers should
    go through `_query_embedding(query_text)` so the zero-vector path is
    reserved for genuine failure modes (no API key, disabled by env,
    dimension mismatch, exception). When this fires the FTS half of RRF
    dominates ranking. fix_v7 §3b for full context.
    """
    return [0.0] * _QUERY_EMBED_DIM


def _query_embedding(query_text: str) -> tuple[list[float], dict[str, Any]]:
    """Return ``(embedding, diag)`` for the chat query.

    fix_v7 §3b — replaces the static `_zero_embedding()` payload that
    silently disabled the vector half of hybrid_search. Reuses the
    existing `lia_graph.embeddings.get_query_embedding` helper.

    Fallback contract: ANY failure (env-disabled, empty query, missing
    key, exception inside Gemini call) returns the 768-dim zero vector
    so retrieval keeps serving. The returned ``diag`` dict carries
    the outcome (``embedding_mode``) for trace surfacing.
    """
    if not _query_embeddings_enabled():
        return _zero_embedding(), {"embedding_mode": "disabled_by_env"}
    text = (query_text or "").strip()
    if not text:
        return _zero_embedding(), {"embedding_mode": "empty_query"}
    try:
        from ..embeddings import get_query_embedding as _get_query_embedding
    except Exception as exc:  # pragma: no cover — embeddings module always present
        return _zero_embedding(), {
            "embedding_mode": "import_error",
            "error_kind": type(exc).__name__,
            "error_message": str(exc)[:200],
        }
    try:
        vec = _get_query_embedding(text)
    except Exception as exc:  # noqa: BLE001
        return _zero_embedding(), {
            "embedding_mode": "error",
            "error_kind": type(exc).__name__,
            "error_message": str(exc)[:200],
        }
    if vec is None:
        return _zero_embedding(), {"embedding_mode": "unavailable"}
    materialized = list(vec)
    if len(materialized) != _QUERY_EMBED_DIM:
        return _zero_embedding(), {
            "embedding_mode": "dimension_mismatch",
            "got_dim": len(materialized),
            "expected_dim": _QUERY_EMBED_DIM,
        }
    return materialized, {
        "embedding_mode": "ok",
        "model": "gemini-embedding-001",
        "dim": _QUERY_EMBED_DIM,
    }


# --- client-side post-rerank boost ------------------------------------------


def _apply_client_side_subtopic_boost(
    rows: list[dict[str, Any]],
    *,
    sub_topic_intent: str | None,
    boost: float,
) -> list[dict[str, Any]]:
    """Client-side post-rerank boost (complements the server-side boost).

    Safe to run when the RPC already applied the boost — a chunk whose
    ``subtema`` matches ``sub_topic_intent`` simply gets multiplied once
    more; for correctness we only apply client-side when the RPC does
    NOT advertise it via the implicit contract (boost factor == 1.0
    means "no client-side boost needed"). But since we cannot detect
    which side applied, we trust ``boost > 1.0`` to mean "I want this
    boost" and apply once client-side, then re-sort. The server-side
    boost is designed to be idempotent with client-side reordering — the
    absolute rrf_score magnitude does not matter, only the ranking.
    """
    if not sub_topic_intent or boost <= 1.0 or not rows:
        return rows

    boosted: list[tuple[float, dict[str, Any]]] = []
    for row in rows:
        score_raw = row.get("rrf_score", 0.0)
        try:
            score = float(score_raw or 0.0)
        except (TypeError, ValueError):
            score = 0.0
        subtema = row.get("subtema")
        applied_boost = 1.0
        if subtema and subtema == sub_topic_intent:
            applied_boost = boost
        updated = dict(row)
        updated["rrf_score"] = score * applied_boost
        if applied_boost != 1.0:
            try:
                from ..instrumentation import emit_event as _emit

                _emit(
                    "subtopic.retrieval.boost_applied",
                    {
                        "chunk_id": row.get("chunk_id"),
                        "sub_topic_intent": sub_topic_intent,
                        "boost_factor": applied_boost,
                        "original_rrf": score,
                        "boosted_rrf": score * applied_boost,
                    },
                )
            except Exception:  # noqa: BLE001 — observability never blocks
                pass
        boosted.append((score * applied_boost, updated))
    boosted.sort(key=lambda item: item[0], reverse=True)
    return [row for _score, row in boosted]


# --- hybrid_search RPC ------------------------------------------------------


def _hybrid_search(
    db: Any,
    *,
    plan: GraphRetrievalPlan,
    query_text: str,
    trace_step: Any,
) -> list[dict[str, Any]]:
    """Call the `hybrid_search` RPC with the plan's boosts + FTS query.

    `trace_step` is the caller's bound `_trace_step` callable — passed in
    explicitly to avoid circular imports between the carve-out and the
    main module's trace decorator.
    """
    effective_date = plan.temporal_context.cutoff_date or None
    match_count = max(
        plan.evidence_bundle_shape.primary_article_limit
        + plan.evidence_bundle_shape.connected_article_limit
        + plan.evidence_bundle_shape.support_document_limit,
        24,
    )
    # fix_v7 §3a — Topic is a ranking signal, NEVER a WHERE filter for the
    # chat path. See `docs/orchestration/orchestration.md` §4.1 invariant
    # ("Topic is ranking signal, not WHERE filter").
    sub_topic_intent = getattr(plan, "sub_topic_intent", None)
    subtopic_boost = _resolve_subtopic_boost_factor()
    router_topic = next(iter(plan.topic_hints), None) if plan.topic_hints else None
    topic_boost = _resolve_topic_boost_factor()
    practica_boost = _resolve_practica_boost_factor()
    query_embedding, embedding_diag = _query_embedding(query_text)
    payload: dict[str, Any] = {
        "query_embedding": query_embedding,
        "query_text": query_text,
        "filter_topic": None,
        "filter_pais": "colombia",
        "match_count": match_count,
        "filter_knowledge_class": None,
        "filter_sync_generation": None,
        "fts_query": _build_fts_or_query(query_text),
        "filter_effective_date_max": effective_date,
    }
    if sub_topic_intent:
        payload["filter_subtopic"] = sub_topic_intent
        payload["subtopic_boost"] = subtopic_boost
    if router_topic and topic_boost > 1.0:
        payload["boost_topic"] = router_topic
        payload["filter_topic_boost"] = topic_boost
    if practica_boost > 1.0:
        payload["boost_knowledge_class"] = "practica_erp"
        payload["knowledge_class_boost"] = practica_boost
    trace_step(
        "retriever.hybrid_search.in",
        status="info",
        match_count=match_count,
        filter_topic=payload.get("filter_topic"),
        boost_topic=payload.get("boost_topic"),
        filter_topic_boost=payload.get("filter_topic_boost"),
        boost_knowledge_class=payload.get("boost_knowledge_class"),
        knowledge_class_boost=payload.get("knowledge_class_boost"),
        filter_subtopic=payload.get("filter_subtopic"),
        subtopic_boost=payload.get("subtopic_boost"),
        filter_effective_date_max=str(payload.get("filter_effective_date_max")) if payload.get("filter_effective_date_max") else None,
        fts_query_present=bool(payload.get("fts_query")),
        sub_topic_intent=sub_topic_intent,
        router_topic=router_topic,
        embedding_mode=embedding_diag.get("embedding_mode"),
        embedding_model=embedding_diag.get("model"),
    )
    _hybrid_recovery: str | None = None
    try:
        response = db.rpc("hybrid_search", payload).execute()
    except Exception as exc:
        # Older DBs reject unknown params. fix_v7 §3a adds `boost_topic`;
        # 0427 added `filter_topic_boost`; pre-0427 deploys reject both.
        # Strip them in order, then fall back to dropping the subtopic
        # filter as a last resort.
        recovered = False
        trace_step(
            "retriever.hybrid_search.first_attempt_error",
            status="error",
            error=repr(exc)[:240],
        )
        if (
            "boost_topic" in payload
            or "filter_topic_boost" in payload
            or "boost_knowledge_class" in payload
            or "knowledge_class_boost" in payload
        ):
            payload.pop("boost_topic", None)
            payload.pop("filter_topic_boost", None)
            payload.pop("boost_knowledge_class", None)
            payload.pop("knowledge_class_boost", None)
            try:
                response = db.rpc("hybrid_search", payload).execute()
                recovered = True
                _hybrid_recovery = "dropped_topic_and_class_boost_params"
            except Exception:
                pass
        if not recovered and sub_topic_intent:
            payload.pop("filter_subtopic", None)
            payload.pop("subtopic_boost", None)
            response = db.rpc("hybrid_search", payload).execute()
            _hybrid_recovery = "dropped_subtopic_filter"
        elif not recovered:
            raise
    if _hybrid_recovery:
        trace_step(
            "retriever.hybrid_search.recovered",
            status="fallback",
            recovery=_hybrid_recovery,
        )
    rows = getattr(response, "data", None) or []
    if not isinstance(rows, list):
        trace_step(
            "retriever.hybrid_search.malformed_response",
            status="error",
            response_type=type(rows).__name__,
        )
        return []
    typed_rows = [row for row in rows if isinstance(row, dict)]
    boosted = _apply_client_side_subtopic_boost(
        typed_rows,
        sub_topic_intent=sub_topic_intent,
        boost=subtopic_boost,
    )
    if sub_topic_intent and len(typed_rows) != len(boosted):
        trace_step(
            "retriever.subtopic_boost.applied",
            status="ok",
            sub_topic_intent=sub_topic_intent,
            boost=subtopic_boost,
            rows_before=len(typed_rows),
            rows_after=len(boosted),
        )
    return boosted


__all__ = [
    "_QUERY_EMBED_DIM",
    "_QUERY_EMBED_ENV_FLAG",
    "_apply_client_side_subtopic_boost",
    "_build_fts_or_query",
    "_hybrid_search",
    "_query_embedding",
    "_query_embeddings_enabled",
    "_resolve_practica_boost_factor",
    "_resolve_subtopic_boost_factor",
    "_resolve_topic_boost_factor",
    "_zero_embedding",
]
