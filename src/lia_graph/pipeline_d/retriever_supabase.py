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
    }
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
    payload = {
        "query_embedding": _zero_embedding(),
        "query_text": query_text,
        "filter_topic": None,
        "filter_pais": "colombia",
        "match_count": match_count,
        "filter_knowledge_class": None,
        "filter_sync_generation": None,
        "fts_query": None,
        "filter_effective_date_max": effective_date,
    }
    response = db.rpc("hybrid_search", payload).execute()
    rows = getattr(response, "data", None) or []
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


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
