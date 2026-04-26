"""Supabase-backed replacement for `retriever.retrieve_graph_evidence`.

Same public signature as `retriever.retrieve_graph_evidence(plan, artifacts_dir=None)`.
Orchestrator dispatches based on `LIA_CORPUS_SOURCE`:

- `artifacts` (dev default) -> `retriever.retrieve_graph_evidence`
- `supabase` (staging default) -> this module

The contract is the same `(hydrated_plan, GraphEvidenceBundle)` tuple so
downstream synthesis/assembly stay untouched.

This adapter is deliberately narrow:

- resolves `documents` rows for the plan's entry-point candidates via REST.
- expands chunks via the `hybrid_search` RPC with the plan's query and
  filters (topic + effective-date + sync_generation).
- returns an `EvidenceBundle` assembled from the Supabase rows.

It does not replace the graph traversal; that stays with `retriever_falkor`
(or the artifact retriever when the graph backend is still on artifacts).
"""

from __future__ import annotations

import os
from pathlib import Path
import re
from typing import Any

from ..contracts import Citation, DocumentRecord
from ..supabase_client import get_supabase_client
from .contracts import (
    GraphEvidenceBundle,
    GraphEvidenceItem,
    GraphRetrievalPlan,
    GraphSupportDocument,
    PlannerEntryPoint,
)
from .planner import with_resolved_entry_points
from .retrieval_support import derive_authority, manifest_doc_id


_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
_ARTICLE_NUMBER_RE = re.compile(r"(?i)^(art(?:[ií]culo)?|art\.)\s*(?P<number>\d+(?:-\d+)?)")


def retrieve_graph_evidence(
    plan: GraphRetrievalPlan,
    *,
    artifacts_dir: Path | str | None = None,  # compatibility with retriever.py signature
    client: Any | None = None,
) -> tuple[GraphRetrievalPlan, GraphEvidenceBundle]:
    del artifacts_dir  # Supabase does not read artifacts — kept for signature parity.
    db = client if client is not None else get_supabase_client()

    query_text = _build_query_text(plan)
    chunk_rows = _hybrid_search(db, plan=plan, query_text=query_text)
    # FTS ranking alone cannot guarantee that the planner's explicit anchor
    # articles appear in top-N — broad OR queries often let generic chunks
    # outrank the real anchor. Fetch each explicit article directly by its
    # `chunk_id` pattern and merge, so primary_articles promotion does not
    # depend on luck of the ranker.
    anchor_rows = _fetch_anchor_article_rows(db, plan)
    chunk_rows = _merge_rows_prefer_anchors(anchor_rows, chunk_rows)
    # v5 §1.B — supplementary topic-filtered fetch was attempted here on
    # 2026-04-26 evening. Empirically regressed 2 topics
    # (impuesto_patrimonio_pn + conciliacion_fiscal) from `chunks_off_topic`
    # to `pipeline_d_no_graph_primary_articles` because the supplementary
    # chunks crowded out the anchor-rows that were providing primary
    # articles, even with anchor-prefix ordering. Removed the call until
    # the proper fix lands at `_collect_support` level (reserve slots for
    # router-topic docs without disrupting primary classification).
    # Helper `_augment_with_topic_supplementary` kept in this file for
    # reference + unit tests; not invoked. See
    # `docs/learnings/ingestion/coherence-gate-thin-corpus-diagnostic-
    # 2026-04-26.md` L8 for the open issue.

    documents_by_doc_id = _load_documents_for_rows(db, chunk_rows)

    primary_articles, connected_articles, resolved_entries = _classify_article_rows(
        plan=plan,
        chunk_rows=chunk_rows,
        documents_by_doc_id=documents_by_doc_id,
    )
    related_reforms = _collect_reforms(plan, chunk_rows)
    support_documents, citations = _collect_support(
        plan=plan,
        documents_by_doc_id=documents_by_doc_id,
        chunk_rows=chunk_rows,
    )
    hydrated_plan = with_resolved_entry_points(plan, tuple(resolved_entries))
    diagnostics = {
        "retrieval_backend": "supabase",
        "artifacts_dir": None,
        "resolved_entry_count": sum(1 for entry in resolved_entries if entry.resolved_key),
        "chunk_row_count": len(chunk_rows),
        "document_row_count": len(documents_by_doc_id),
        "planner_query_mode": plan.query_mode,
        "temporal_context": plan.temporal_context.to_dict(),
        "retrieval_sub_topic_intent": getattr(plan, "sub_topic_intent", None),
    }
    if not chunk_rows:
        diagnostics.update(_diagnose_empty_chunks(db))
    else:
        diagnostics["empty_reason"] = "ok"
    evidence = GraphEvidenceBundle(
        primary_articles=primary_articles,
        connected_articles=connected_articles,
        related_reforms=related_reforms,
        support_documents=support_documents,
        citations=citations,
        diagnostics=diagnostics,
    )
    return hydrated_plan, evidence


# --- hybrid_search RPC ------------------------------------------------------


def _build_query_text(plan: GraphRetrievalPlan) -> str:
    """Best-effort reconstruct a retrieval query from the plan."""
    parts: list[str] = []
    for entry in plan.entry_points:
        if entry.kind == "article_search" and entry.lookup_value:
            parts.append(str(entry.lookup_value))
        elif entry.kind == "article" and entry.lookup_value:
            parts.append(f"Articulo {entry.lookup_value}")
        elif entry.kind == "topic" and entry.lookup_value:
            parts.append(str(entry.lookup_value))
        elif entry.kind == "reform" and entry.label:
            parts.append(str(entry.label))
    if not parts:
        parts.extend(plan.topic_hints or ())
    return " ".join(dict.fromkeys(parts)).strip() or plan.query_mode


def _hybrid_search(
    db: Any,
    *,
    plan: GraphRetrievalPlan,
    query_text: str,
) -> list[dict[str, Any]]:
    effective_date = plan.temporal_context.cutoff_date or None
    match_count = max(
        plan.evidence_bundle_shape.primary_article_limit
        + plan.evidence_bundle_shape.connected_article_limit
        + plan.evidence_bundle_shape.support_document_limit,
        24,
    )
    # Topic is a planner-side signal, not a recall predicate. Cross-topic
    # anchors (e.g. Art. 147 ET catalogued under IVA but load-bearing for a
    # declaracion_renta query) must stay reachable — topic only shapes ranking
    # via `query_text` terms, never the WHERE clause.
    #
    # The RPC defaults to `plainto_tsquery` on `query_text`, which builds an
    # AND across every term. Our `query_text` concatenates ~50 planner tokens
    # (topic hints + article numbers + lexical searches + raw message), so an
    # AND never matches anything. Build an explicit OR `fts_query` to force
    # OR semantics; FTS ranking still prefers chunks that hit more terms.
    sub_topic_intent = getattr(plan, "sub_topic_intent", None)
    subtopic_boost = _resolve_subtopic_boost_factor()
    payload: dict[str, Any] = {
        "query_embedding": _zero_embedding(),
        "query_text": query_text,
        "filter_topic": None,
        "filter_pais": "colombia",
        "match_count": match_count,
        "filter_knowledge_class": None,
        "filter_sync_generation": None,
        "fts_query": _build_fts_or_query(query_text),
        "filter_effective_date_max": effective_date,
    }
    # ingestfix-v2 Phase 6: pass subtopic filter so the RPC can apply the
    # server-side boost directly. The client-side fallback below covers
    # older DBs that haven't applied the migration yet (Invariant I5 —
    # NULL subtemas never penalized).
    if sub_topic_intent:
        payload["filter_subtopic"] = sub_topic_intent
        payload["subtopic_boost"] = subtopic_boost
    try:
        response = db.rpc("hybrid_search", payload).execute()
    except Exception:
        # Older DBs reject unknown params. Retry without the subtopic args
        # and apply the boost client-side so retrieval still responds.
        if sub_topic_intent:
            payload.pop("filter_subtopic", None)
            payload.pop("subtopic_boost", None)
            response = db.rpc("hybrid_search", payload).execute()
        else:
            raise
    rows = getattr(response, "data", None) or []
    if not isinstance(rows, list):
        return []
    typed_rows = [row for row in rows if isinstance(row, dict)]
    return _apply_client_side_subtopic_boost(
        typed_rows,
        sub_topic_intent=sub_topic_intent,
        boost=subtopic_boost,
    )


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


def _fetch_anchor_article_rows(
    db: Any,
    plan: GraphRetrievalPlan,
) -> list[dict[str, Any]]:
    """Fetch chunks for every explicit `article` anchor in the plan.

    The `chunk_id` convention from the sink is `doc_id::<article_key>`, so
    `chunk_id LIKE '%::<key>'` matches every chunk for that article across all
    documents that contain it. This bypasses FTS entirely so planner anchors
    never go missing because the rank spread them below the match_count cap.
    """
    anchor_keys = [
        str(entry.lookup_value).strip()
        for entry in plan.entry_points
        if entry.kind == "article" and entry.lookup_value
    ]
    anchor_keys = [k for k in dict.fromkeys(anchor_keys) if k]
    if not anchor_keys:
        return []
    rows: list[dict[str, Any]] = []
    for key in anchor_keys:
        try:
            response = (
                db.table("document_chunks")
                .select(
                    "chunk_id, doc_id, chunk_text, summary, topic, "
                    "knowledge_class, concept_tags, relative_path"
                )
                .like("chunk_id", f"%::{key}")
                .limit(8)
                .execute()
            )
        except Exception:  # noqa: BLE001 - anchor fetch is best-effort
            continue
        for row in getattr(response, "data", None) or []:
            if not isinstance(row, dict):
                continue
            row = dict(row)
            # Tag with a synthetic rank that sorts above any FTS result so
            # classification preserves anchor priority when the two sets merge.
            row.setdefault("rrf_score", 1.0)
            row.setdefault("fts_rank", 1.0)
            rows.append(row)
    return rows


def _augment_with_topic_supplementary(
    db: Any,
    plan: GraphRetrievalPlan,
    query_text: str,
    chunk_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """v5 §1.B — guarantee router-topic representation in chunk_rows.

    For thin-corpus topics, hybrid_search ranks narrow-topic docs below
    umbrella-topic chunks despite the corpus containing relevant content.
    This pulls a small supplementary set (filter_topic=router_topic) and
    appends any chunks not already present, so support_documents has the
    chance to include 2+ router-topic docs (the coherence-gate threshold).

    No-op when:
      * the plan has no router topic (plan.topic_hints is empty);
      * the router topic already has ≥ 2 unique docs in chunk_rows
        (threshold already satisfiable from hybrid_search alone).
    """
    router_topic = next(iter(plan.topic_hints), None) if plan.topic_hints else None
    if not router_topic:
        return chunk_rows
    # Count distinct doc_ids tagged with router_topic in current rows.
    existing_router_doc_ids = {
        str(row.get("doc_id") or "")
        for row in chunk_rows
        if (row.get("topic") or "").strip() == router_topic and row.get("doc_id")
    }
    if len(existing_router_doc_ids) >= 2:
        return chunk_rows  # threshold already satisfiable.

    # Supplementary fetch with topic filter.
    payload: dict[str, Any] = {
        "query_embedding": _zero_embedding(),
        "query_text": query_text,
        "filter_topic": router_topic,
        "filter_pais": "colombia",
        "match_count": 12,  # small set; we only need 1-2 more docs.
        "filter_knowledge_class": None,
        "filter_sync_generation": None,
        "fts_query": _build_fts_or_query(query_text),
        "filter_effective_date_max": plan.temporal_context.cutoff_date or None,
    }
    try:
        response = db.rpc("hybrid_search", payload).execute()
    except Exception:  # noqa: BLE001 — supplementary fetch is best-effort.
        return chunk_rows
    raw = getattr(response, "data", None) or []
    if not isinstance(raw, list):
        return chunk_rows

    existing_chunk_ids = {
        str(row.get("chunk_id") or "") for row in chunk_rows if row.get("chunk_id")
    }
    supplementary: list[dict[str, Any]] = []
    seen_doc_ids: set[str] = set()
    for row in raw:
        if not isinstance(row, dict):
            continue
        cid = str(row.get("chunk_id") or "")
        did = str(row.get("doc_id") or "")
        if not cid or cid in existing_chunk_ids:
            continue
        if did in seen_doc_ids:
            # 1 chunk per doc is enough — we want doc-level coverage,
            # not chunk flooding. Hybrid_search rows downstream will
            # provide more chunks per doc if relevant.
            continue
        # Tag with synthetic rrf_score below anchor priority but above
        # any hybrid_search result that might tie at zero — this keeps
        # the supplementary docs near the front when ranked.
        clone = dict(row)
        clone.setdefault("rrf_score", 0.95)
        clone.setdefault("fts_rank", 0.95)
        supplementary.append(clone)
        existing_chunk_ids.add(cid)
        seen_doc_ids.add(did)
        if len(supplementary) >= 3:
            break
    if not supplementary:
        return chunk_rows
    # Insert supplementary AFTER any anchor rows (rrf_score == 1.0 from
    # `_fetch_anchor_article_rows`) but BEFORE hybrid_search rows. Anchors
    # must keep priority for primary_articles classification; supplementary
    # is only meant to widen support_documents coverage.
    anchor_prefix: list[dict[str, Any]] = []
    rest: list[dict[str, Any]] = []
    for row in chunk_rows:
        # Anchors are tagged with rrf_score=1.0 (line 350 in
        # `_fetch_anchor_article_rows`). FTS rows have lower rrf_score
        # (typically << 1.0 from the RRF formula). 0.99+ is anchor-band.
        if float(row.get("rrf_score") or 0) >= 0.99:
            anchor_prefix.append(row)
        else:
            rest.append(row)
    return anchor_prefix + supplementary + rest


def _merge_rows_prefer_anchors(
    anchor_rows: list[dict[str, Any]],
    fts_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Anchor rows first (they are the planner's explicit primaries), then
    append FTS rows that aren't already present by chunk_id."""
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for row in anchor_rows + fts_rows:
        chunk_id = str(row.get("chunk_id") or "")
        if not chunk_id or chunk_id in seen:
            continue
        seen.add(chunk_id)
        merged.append(row)
    return merged


def _diagnose_empty_chunks(db: Any) -> dict[str, Any]:
    """Classify why `hybrid_search` came back empty.

    Distinguishes an unseeded corpus ("no chunks exist anywhere") from a
    routing miss ("chunks exist but none matched this query"). Operators
    reading `empty_reason=corpus_not_seeded` know the action is
    `make phase2-graph-artifacts-supabase`; anything else points at
    retrieval shape rather than ingestion.
    """
    try:
        response = (
            db.table("document_chunks")
            .select("chunk_id", count="exact")
            .limit(1)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001 - diagnostics must never raise
        return {
            "empty_reason": "chunks_probe_failed",
            "chunks_probe_error": str(exc),
        }
    total = getattr(response, "count", None)
    probe: dict[str, Any] = {"document_chunks_total": total}
    if total is None:
        probe["empty_reason"] = "chunks_probe_unknown_count"
    elif total == 0:
        probe["empty_reason"] = "corpus_not_seeded"
    else:
        probe["empty_reason"] = "no_lexical_or_vector_hits"
    return probe


def _zero_embedding() -> list[float]:
    # `hybrid_search` needs a 768-dim vector. Until the embedding worker
    # catches up, pass zeros so the FTS half of the RRF still dominates.
    return [0.0] * 768


# --- document + chunk -> evidence -------------------------------------------


def _load_documents_for_rows(
    db: Any,
    chunk_rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    doc_ids = sorted(
        {
            str(row.get("doc_id") or "").strip()
            for row in chunk_rows
            if str(row.get("doc_id") or "").strip()
        }
    )
    if not doc_ids:
        return {}
    response = (
        db.table("documents")
        .select(
            "doc_id,relative_path,source_type,topic,authority,pais,"
            "knowledge_class,tema,subtema,tipo_de_documento,curation_status,"
            "vigencia,corpus,first_heading,url"
        )
        .in_("doc_id", doc_ids)
        .execute()
    )
    rows = getattr(response, "data", None) or []
    return {str(row.get("doc_id") or ""): row for row in rows if isinstance(row, dict) and row.get("doc_id")}


def _classify_article_rows(
    *,
    plan: GraphRetrievalPlan,
    chunk_rows: list[dict[str, Any]],
    documents_by_doc_id: dict[str, dict[str, Any]],
) -> tuple[tuple[GraphEvidenceItem, ...], tuple[GraphEvidenceItem, ...], list[PlannerEntryPoint]]:
    explicit_articles: list[str] = [
        str(entry.lookup_value)
        for entry in plan.entry_points
        if entry.kind == "article" and entry.lookup_value
    ]
    explicit_set = {value for value in explicit_articles if value}
    primary: list[GraphEvidenceItem] = []
    connected: list[GraphEvidenceItem] = []
    seen_article_keys: set[str] = set()

    for row in chunk_rows:
        article_key = _derive_article_key(row)
        if not article_key or article_key in seen_article_keys:
            continue
        seen_article_keys.add(article_key)
        doc_id = str(row.get("doc_id") or "")
        document_row = documents_by_doc_id.get(doc_id, {})
        relative_path = str(document_row.get("relative_path") or row.get("relative_path") or "")
        chunk_text = str(row.get("chunk_text") or row.get("summary") or "")
        snippet = chunk_text[: plan.evidence_bundle_shape.snippet_char_limit]
        item = GraphEvidenceItem(
            node_kind="ArticleNode",
            node_key=article_key,
            title=str(row.get("summary") or article_key),
            excerpt=snippet,
            source_path=relative_path or None,
            score=float(row.get("rrf_score") or row.get("fts_rank") or 0.0),
            hop_distance=0 if article_key in explicit_set else 1,
            why=None,
            relation_path=(),
        )
        if article_key in explicit_set:
            primary.append(item)
        else:
            connected.append(item)

    primary = primary[: plan.evidence_bundle_shape.primary_article_limit]
    connected = connected[: plan.evidence_bundle_shape.connected_article_limit]

    resolved_entries: list[PlannerEntryPoint] = []
    for entry in plan.entry_points:
        if entry.kind == "article" and entry.lookup_value:
            resolved_key = entry.lookup_value if any(
                item.node_key == entry.lookup_value for item in primary
            ) else None
            resolved_entries.append(
                PlannerEntryPoint(
                    kind=entry.kind,
                    lookup_value=entry.lookup_value,
                    source=entry.source,
                    confidence=entry.confidence,
                    label=entry.label,
                    resolved_key=resolved_key,
                )
            )
        else:
            resolved_entries.append(entry)
    return tuple(primary), tuple(connected), resolved_entries


def _derive_article_key(row: dict[str, Any]) -> str:
    chunk_id = str(row.get("chunk_id") or "")
    if "::" in chunk_id:
        tail = chunk_id.rsplit("::", maxsplit=1)[1].strip()
        if tail:
            return tail
    summary = str(row.get("summary") or "")
    match = _ARTICLE_NUMBER_RE.search(summary)
    if match:
        return match.group("number")
    return chunk_id


def _collect_reforms(
    plan: GraphRetrievalPlan,
    chunk_rows: list[dict[str, Any]],
) -> tuple[GraphEvidenceItem, ...]:
    reforms: dict[str, GraphEvidenceItem] = {}
    for entry in plan.entry_points:
        if entry.kind != "reform" or not entry.lookup_value:
            continue
        key = entry.lookup_value
        if key in reforms:
            continue
        reforms[key] = GraphEvidenceItem(
            node_kind="ReformNode",
            node_key=key,
            title=str(entry.label or key),
            excerpt="Reforma referenciada en el plan de recuperación.",
            source_path=None,
            score=float(entry.confidence or 0.0),
            hop_distance=0,
            why=None,
            relation_path=(),
        )
        if len(reforms) >= plan.evidence_bundle_shape.related_reform_limit:
            break
    return tuple(reforms.values())


def _collect_support(
    *,
    plan: GraphRetrievalPlan,
    documents_by_doc_id: dict[str, dict[str, Any]],
    chunk_rows: list[dict[str, Any]],
) -> tuple[tuple[GraphSupportDocument, ...], tuple[Citation, ...]]:
    limit = plan.evidence_bundle_shape.support_document_limit
    if limit <= 0 or not documents_by_doc_id:
        return (), ()
    # Preserve the order chunks arrived in (ranked by hybrid_search).
    ordered_doc_ids: list[str] = []
    seen: set[str] = set()
    for row in chunk_rows:
        doc_id = str(row.get("doc_id") or "")
        if not doc_id or doc_id in seen:
            continue
        if doc_id not in documents_by_doc_id:
            continue
        seen.add(doc_id)
        ordered_doc_ids.append(doc_id)
        if len(ordered_doc_ids) >= limit:
            break

    supports: list[GraphSupportDocument] = []
    citations: list[Citation] = []
    for doc_id in ordered_doc_ids:
        row = documents_by_doc_id[doc_id]
        family = str(row.get("corpus") or row.get("topic") or "").strip() or None
        supports.append(
            GraphSupportDocument(
                relative_path=str(row.get("relative_path") or ""),
                source_path=str(row.get("relative_path") or ""),
                title_hint=str(row.get("first_heading") or row.get("relative_path") or ""),
                family=family,
                knowledge_class=str(row.get("knowledge_class") or "") or None,
                topic_key=str(row.get("topic") or "") or None,
                subtopic_key=str(row.get("subtema") or "") or None,
                canonical_blessing_status=str(row.get("curation_status") or "") or None,
                graph_target=(family == "normativa"),
                reason="supabase_hybrid_search_hit",
            )
        )
        citations.append(Citation.from_document(_document_record_from_row(row)))
    return tuple(supports), tuple(citations)


def _document_record_from_row(row: dict[str, Any]) -> DocumentRecord:
    authority = derive_authority(
        {
            "source_type": row.get("source_type"),
            "knowledge_class": row.get("knowledge_class"),
        }
    )
    payload = {
        "doc_id": str(row.get("doc_id") or manifest_doc_id(row)),
        "relative_path": str(row.get("relative_path") or ""),
        "absolute_path": "",
        "category": str(row.get("corpus") or row.get("topic") or "unknown"),
        "source_type": str(row.get("source_type") or "unknown"),
        "curation_status": str(row.get("curation_status") or ""),
        "knowledge_class": str(row.get("knowledge_class") or ""),
        "topic": str(row.get("topic") or "unknown"),
        "authority": authority,
        "pais": str(row.get("pais") or "colombia"),
        "tema": str(row.get("tema") or ""),
        "subtema": str(row.get("subtema") or ""),
        "primary_role": str(row.get("corpus") or ""),
        "notes": str(row.get("first_heading") or ""),
        "tipo_de_documento": str(row.get("tipo_de_documento") or "") or None,
        "url": row.get("url"),
    }
    return DocumentRecord.from_dict(payload)


__all__ = ["retrieve_graph_evidence"]
