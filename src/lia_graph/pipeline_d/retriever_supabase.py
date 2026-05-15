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
from typing import Any, Mapping

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
from .retriever_supabase_search import (  # fix_v16 b5 carve-out — re-exported for tests
    _QUERY_EMBED_DIM,
    _QUERY_EMBED_ENV_FLAG,
    _apply_client_side_subtopic_boost,
    _build_fts_or_query,
    _hybrid_search as _hybrid_search_impl,
    _query_embedding,
    _query_embeddings_enabled,
    _resolve_practica_boost_factor,
    _resolve_subtopic_boost_factor,
    _resolve_topic_boost_factor,
    _zero_embedding,
)

# fix_v1.md hand-off — deep-trace collector. No-op when no active trace.
try:
    from tracers_and_logs import pipeline_trace as _trace
except ImportError:  # pragma: no cover - tracer always present in served runtime
    _trace = None  # type: ignore[assignment]


def _trace_step(step_name: str, *, status: str = "ok", message: str | None = None, **details: Any) -> None:
    if _trace is None:
        return
    _trace.step(step_name, status=status, message=message, **details)


_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
_ARTICLE_NUMBER_RE = re.compile(r"(?i)^(art(?:[ií]culo)?|art\.)\s*(?P<number>\d+(?:-\d+)?)")


# fix_v2.md §A — Cached map from article_id → set of topic_keys it serves
# under (primary_topic + secondary_topics) per
# `config/article_secondary_topics.json`. Used by `_classify_article_rows`
# to promote chunks to `primary` when the planner has no explicit
# anchor but the chunk's article_id is curated as serving the router
# topic. Solves the case where SUIN-scrape ET-article chunks have
# `topic=NULL` at both chunk + doc level (so router-topic match on
# `chunk.topic` fails) but the article semantically serves the router
# topic via the SME-curated rescue config.
_ARTICLE_TOPICS_CACHE: dict[str, frozenset[str]] | None = None


def _load_article_topic_index() -> dict[str, frozenset[str]]:
    global _ARTICLE_TOPICS_CACHE
    if _ARTICLE_TOPICS_CACHE is not None:
        return _ARTICLE_TOPICS_CACHE
    import json as _json
    cfg_path = _WORKSPACE_ROOT / "config" / "article_secondary_topics.json"
    index: dict[str, frozenset[str]] = {}
    try:
        raw = _json.loads(cfg_path.read_text())
        for entry in raw.get("articles", ()) or ():
            aid = str(entry.get("article_id") or "").strip()
            if not aid:
                continue
            topics: set[str] = set()
            primary = (entry.get("primary_topic") or "").strip()
            if primary:
                topics.add(primary)
            for t in entry.get("secondary_topics") or ():
                ts = str(t or "").strip()
                if ts:
                    topics.add(ts)
            if topics:
                index[aid] = frozenset(topics)
    except (OSError, ValueError):
        pass
    _ARTICLE_TOPICS_CACHE = index
    return index


def retrieve_graph_evidence(
    plan: GraphRetrievalPlan,
    *,
    artifacts_dir: Path | str | None = None,  # compatibility with retriever.py signature
    client: Any | None = None,
) -> tuple[GraphRetrievalPlan, GraphEvidenceBundle]:
    del artifacts_dir  # Supabase does not read artifacts — kept for signature parity.
    db = client if client is not None else get_supabase_client()

    query_text = _build_query_text(plan)
    _trace_step(
        "retriever.supabase.entry",
        status="info",
        plan_query_mode=getattr(plan, "query_mode", None),
        anchor_article_count=len(getattr(plan, "anchor_articles", ()) or ()),
        topic=getattr(plan, "topic", None),
        sub_topic_intent=getattr(plan, "sub_topic_intent", None),
        query_text_preview=query_text[:240],
        query_text_chars=len(query_text or ""),
    )
    chunk_rows = _hybrid_search_impl(
        db, plan=plan, query_text=query_text, trace_step=_trace_step
    )
    _trace_step(
        "retriever.hybrid_search.out",
        status="ok" if chunk_rows else "fallback",
        message="hybrid_search returned 0 rows" if not chunk_rows else None,
        row_count=len(chunk_rows),
        top_chunk_ids=[(r.get("chunk_id") or r.get("id"))[:80] for r in chunk_rows[:10] if isinstance(r, dict)],
        # fix_v12 §2.C — surface knowledge_class per top chunk so the
        # `LIA_PRACTICA_BOOST_FACTOR` A/B preflight is observable
        # directly in the trace.
        top_chunk_classes=[r.get("knowledge_class") for r in chunk_rows[:10] if isinstance(r, dict)],
        practica_count_in_top_20=sum(
            1
            for r in chunk_rows[:20]
            if isinstance(r, dict) and r.get("knowledge_class") == "practica_erp"
        ),
    )
    # FTS ranking alone cannot guarantee that the planner's explicit anchor
    # articles appear in top-N — broad OR queries often let generic chunks
    # outrank the real anchor. Fetch each explicit article directly by its
    # `chunk_id` pattern and merge, so primary_articles promotion does not
    # depend on luck of the ranker.
    anchor_rows = _fetch_anchor_article_rows(db, plan)
    _trace_step(
        "retriever.anchor_articles",
        status="ok",
        anchor_row_count=len(anchor_rows),
        anchor_article_keys=[r.get("article_key") for r in anchor_rows[:20] if isinstance(r, dict)],
    )
    chunk_rows_before_merge = len(chunk_rows)
    chunk_rows = _merge_rows_prefer_anchors(anchor_rows, chunk_rows)
    _trace_step(
        "retriever.merge_anchors",
        status="ok",
        before=chunk_rows_before_merge,
        after=len(chunk_rows),
        delta=len(chunk_rows) - chunk_rows_before_merge,
    )

    # fix_v14_may §4 (A2) — chunk-quality heuristics. Demote rows
    # carrying corpus-build artifacts (portal-login boilerplate,
    # cross-topic operational leaks, chunk captions, section-numeral
    # headings, question-dominant text). Shadow by default at landing
    # — emits diagnostic but does NOT alter rrf_score; flip
    # `LIA_CHUNK_QUALITY_HEURISTIC_MODE=enforce` after panel-judge
    # INCLUDE per fix_v14_may §4 decision rule.
    from .chunk_quality_heuristics import apply_heuristics as _apply_cq_heuristics
    _routed_topic = next(iter(getattr(plan, "topic_hints", ()) or ()), None)
    _cq_rows_in = len(chunk_rows)
    chunk_rows, _cq_diag = _apply_cq_heuristics(
        chunk_rows, routed_topic=_routed_topic
    )
    _trace_step(
        "retriever.chunk_quality_heuristics.applied",
        status="ok",
        gate_mode=_cq_diag.get("gate_mode"),
        rows_in=_cq_rows_in,
        rows_out=len(chunk_rows),
        rows_demoted=_cq_diag.get("rows_demoted"),
        reasons=_cq_diag.get("reasons"),
        samples=_cq_diag.get("samples"),
        routed_topic=_routed_topic,
    )

    # fixplan_v3 sub-fix 1B-ε — apply the v3 vigencia gate as a post-pass.
    # Drops chunks whose anchor citation is in {DE,SP,IE,VL}; demotes
    # contested-DT (factor 0.3); annotates kept chunks with `vigencia_v3`
    # so the chat-response payload can render the chip. No-op when
    # `norm_citations` is empty for the chunk set.
    _rows_in_v3 = len(chunk_rows)
    chunk_rows, demotion_diagnostics = _apply_v3_vigencia_demotion(db, plan, chunk_rows)
    _v3_status = (demotion_diagnostics or {}).get("status")
    _trace_step(
        "retriever.vigencia_v3.applied",
        status="ok" if _v3_status == "ok" else "skipped",
        message=f"vigencia_v3 status={_v3_status}",
        rows_in=_rows_in_v3,
        rows_out=len(chunk_rows),
        rpc_kind=(demotion_diagnostics or {}).get("rpc_kind"),
        rpc_payload=(demotion_diagnostics or {}).get("rpc_payload"),
        chunks_seen=(demotion_diagnostics or {}).get("chunks_seen"),
        chunks_kept=(demotion_diagnostics or {}).get("chunks_kept"),
        chunks_dropped=(demotion_diagnostics or {}).get("chunks_dropped"),
        chunks_demoted=(demotion_diagnostics or {}).get("chunks_demoted"),
        full_demotion_diagnostics=dict(demotion_diagnostics or {}),
    )
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
        "vigencia_v3_demotion": demotion_diagnostics,
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


def _fetch_anchor_article_rows(
    db: Any,
    plan: GraphRetrievalPlan,
) -> list[dict[str, Any]]:
    """Fetch chunks for every explicit `article` anchor in the plan.

    The `chunk_id` convention from the sink is `doc_id::<article_key>`, so
    `chunk_id LIKE '%::<key>'` matches every chunk for that article across all
    documents that contain it. This bypasses FTS entirely so planner anchors
    never go missing because the rank spread them below the match_count cap.

    fix_v2 phase 3 (2026-04-29) — when the planner produces NO explicit
    anchors but a router topic is set, also fetch every article that the
    SME-curated rescue config (`config/article_secondary_topics.json`)
    declares as serving the router topic. Without this the retriever
    misses art 689-3 for `beneficio_auditoria`, art 240/241/256/257 for
    `tarifas_renta_y_ttd`/`descuentos_tributarios_renta`, etc. — because
    FTS+vector ranking buries them below umbrella-topic chunks. Rescue
    rows get a synthetic rrf_score of 0.95 (below explicit-anchor 1.0,
    above pure-FTS) so explicit anchors still take ranking priority.
    Capped at 10 articles per call to keep the round trip bounded.
    """
    anchor_keys = [
        str(entry.lookup_value).strip()
        for entry in plan.entry_points
        if entry.kind == "article" and entry.lookup_value
    ]
    anchor_keys = [k for k in dict.fromkeys(anchor_keys) if k]
    rescue_keys: list[str] = []
    rescue_score = 0.95
    if not anchor_keys:
        router_topic = (
            next(iter(plan.topic_hints), None) if plan.topic_hints else None
        )
        router_topic = router_topic.strip() if isinstance(router_topic, str) else None
        if router_topic:
            index = _load_article_topic_index()
            rescue_keys = [
                aid for aid, topics in index.items() if router_topic in topics
            ][:10]
    if not anchor_keys and not rescue_keys:
        return []
    rows: list[dict[str, Any]] = []
    for kind, keys, score in (
        ("anchor", anchor_keys, 1.0),
        ("rescue", rescue_keys, rescue_score),
    ):
        for key in keys:
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
            except Exception:  # noqa: BLE001 - anchor/rescue fetch is best-effort
                continue
            for row in getattr(response, "data", None) or []:
                if not isinstance(row, dict):
                    continue
                row = dict(row)
                # Tag with a synthetic rank so classification preserves
                # anchor priority when the two sets merge. Rescue rows
                # sort below explicit anchors but above raw FTS results.
                row.setdefault("rrf_score", score)
                row.setdefault("fts_rank", score)
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

    # Supplementary fetch — widen the router-topic doc footprint to satisfy
    # the coherence-gate ≥2-doc threshold. fix_v7 §3a: this fetch INTENTIONALLY
    # uses `filter_topic` as a hard filter — the whole point of the
    # supplementary fetch is to add router-topic chunks that the main
    # hybrid_search (run with filter_topic=None) may not have surfaced
    # enough of. Cross-topic reachability is the main fetch's job; this is
    # a topic-pinned supplement on top of it.
    query_embedding, _embedding_diag = _query_embedding(query_text)
    payload: dict[str, Any] = {
        "query_embedding": query_embedding,
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


def _apply_v3_vigencia_demotion(
    db: Any,
    plan: GraphRetrievalPlan,
    chunk_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """fixplan_v3 sub-fix 1B-ε — gate retrieval results through the v3
    norm-keyed vigencia layer.

    Calls `chunk_vigencia_gate_at_date` (or `_for_period`) with the chunk_ids
    + the planner's vigencia query payload, then multiplies each chunk's
    `rrf_score` by the anchor's `demotion_factor` and drops chunks whose
    anchor returns 0.0 (DE / SP / IE / VL / DI-expired).

    The pass is best-effort: if the RPC is unavailable (env without v3
    schema) it returns the input untouched plus a `disabled` diagnostic.
    """

    if not chunk_rows:
        return chunk_rows, {"status": "no_chunks", "kept": 0, "dropped": 0}

    try:
        from lia_graph.pipeline_d.vigencia_demotion import (
            apply_demotion as _apply,
            run_demotion_pass as _run_pass,
        )
    except Exception as err:  # pragma: no cover
        return chunk_rows, {"status": "import_error", "error": str(err)}

    chunk_ids = [str(row.get("chunk_id") or "") for row in chunk_rows if row.get("chunk_id")]
    if not chunk_ids:
        return chunk_rows, {"status": "no_chunk_ids", "kept": len(chunk_rows), "dropped": 0}

    def _at_date(ids: list[str], as_of: str):
        try:
            resp = db.rpc(
                "chunk_vigencia_gate_at_date",
                {"chunk_ids": ids, "as_of_date": as_of},
            ).execute()
        except Exception:  # pragma: no cover — env-dependent
            return []
        return getattr(resp, "data", None) or []

    def _for_period(ids: list[str], impuesto: str, periodo_year: int, periodo_label: Any):
        try:
            resp = db.rpc(
                "chunk_vigencia_gate_for_period",
                {
                    "chunk_ids": ids,
                    "impuesto": impuesto,
                    "periodo_year": int(periodo_year),
                    "periodo_label": periodo_label,
                },
            ).execute()
        except Exception:  # pragma: no cover
            return []
        return getattr(resp, "data", None) or []

    try:
        result = _run_pass(
            plan=plan,
            chunk_ids=chunk_ids,
            rpc_at_date_fn=_at_date,
            rpc_for_period_fn=_for_period,
        )
    except Exception as err:  # pragma: no cover
        return chunk_rows, {"status": "pass_error", "error": str(err)}

    new_rows = _apply(chunk_rows, result)
    return new_rows, {
        "status": "ok",
        "rpc_kind": result.rpc_kind,
        "rpc_payload": dict(result.rpc_payload or {}),
        "chunks_seen": result.chunks_seen,
        "chunks_kept": result.chunks_kept,
        "chunks_dropped": result.chunks_dropped,
        "chunks_demoted": result.chunks_demoted,
    }


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
    # fix_v2 phase 3 (2026-04-29) — generalize "primary evidence" beyond
    # the planner's explicit-anchor-only contract. The original code
    # only marked a chunk as `primary` when `article_key ∈ explicit_set`.
    # For any "broad" question (planner mode `general_graph_research`,
    # `plan_anchor_count=0`), `primary_count` was structurally always 0,
    # and the v6 coherence-gate then refused with
    # `zero_evidence_for_router_topic` — even when 23 of 24 retrieved
    # chunks were on-topic by every other structural signal. This is a
    # bug class, not a §1.G-specific patch: it affects every topic with
    # broad-style profiles across the whole 89-topic taxonomy.
    #
    # The corrected, generalizable definition: a retrieved chunk is
    # primary evidence for `router_topic` if ANY of these structural
    # signals fires (each is SME-curated, none is heuristic):
    #
    #   (1) Planner anchor — `article_key ∈ explicit_set`. Unchanged.
    #   (2) Chunk-level topic — `chunk.topic == router_topic`. Direct
    #       metadata claim; weak only because chunk.topic is often NULL
    #       (e.g. SUIN ET-article scrape).
    #   (3) Document-level topic — `document.topic == router_topic`.
    #       The strongest universal signal: every document in the corpus
    #       is tagged at the file level, regardless of whether the
    #       chunk-level enrichment ran.
    #   (4) Compatible-doc-topics — `document.topic ∈
    #       compatible_doc_topics[router_topic]` (per
    #       `config/compatible_doc_topics.json`, SME-curated narrow→broad
    #       topical adjacency map). Already used by the gate at the
    #       support-document layer; mirrored here at the primary layer.
    #   (5) Article rescue config — `article_id ∈
    #       rescue_index[router_topic]` (per
    #       `config/article_secondary_topics.json`, SME-curated per-article
    #       multi-topic registry). Already used by the misalignment
    #       detector; mirrored here at the classification layer.
    #
    # Items promoted by signals (2)–(5) carry `secondary_topics=(router_topic,)`
    # so the misalignment detector's `secondary_topic_match` short-circuit
    # accepts them without falling back to lexical scoring (which can give
    # false-positive misalignment between sibling sub-topics like
    # `tarifas_renta_y_ttd` vs `declaracion_renta`).
    #
    # Recall side (when the retriever didn't surface the relevant
    # rescue-config articles at all) is handled by
    # `_fetch_anchor_article_rows`, which fetches rescue-config articles
    # by `chunk_id LIKE '%::<key>'` when no explicit anchors exist.
    from .compatible_doc_topics import get_compatible_topics
    router_topic = (
        next(iter(plan.topic_hints), None) if plan.topic_hints else None
    )
    router_topic = router_topic.strip() if isinstance(router_topic, str) else None
    article_topic_index = _load_article_topic_index() if router_topic else {}
    compatible_doc_topics: frozenset[str] = (
        get_compatible_topics(router_topic) if router_topic else frozenset()
    )
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
        # fixplan_v3 sub-fix 1B-ε — propagate the v3 vigencia annotation
        # attached during _apply_v3_vigencia_demotion. None when chunk has
        # no anchor citation (passthrough).
        vigencia_v3_payload = row.get("vigencia_v3")
        chunk_topic_raw = row.get("topic")
        chunk_topic = chunk_topic_raw.strip() if isinstance(chunk_topic_raw, str) else ""
        doc_topic_raw = document_row.get("topic")
        doc_topic = doc_topic_raw.strip() if isinstance(doc_topic_raw, str) else ""
        is_explicit_anchor = article_key in explicit_set
        # Signals (2)–(5). Evaluated only when router_topic is present.
        signals_router_topic = bool(router_topic) and (
            chunk_topic == router_topic
            or doc_topic == router_topic
            or (doc_topic != "" and doc_topic in compatible_doc_topics)
            or router_topic in article_topic_index.get(article_key, frozenset())
        )
        # fix_v16 b5 (2026-05-14) — explicit anchors also need
        # secondary_topics populated when the rescue config declares the
        # article serves the router_topic. Without this, cross-domain
        # anchors (e.g. art. 869 in renta, router=procedimiento_tributario)
        # land in primary[] with empty secondary_topics, the misalignment
        # detector falls through to lexical scoring against the article's
        # canonical (renta) topic, and coherence-gate abstains. Pre-v16
        # behavior preserved for non-anchor rows.
        article_serves_router = bool(router_topic) and (
            router_topic in article_topic_index.get(article_key, frozenset())
        )
        if signals_router_topic and router_topic and (
            not is_explicit_anchor or article_serves_router
        ):
            secondary_topics_for_item: tuple[str, ...] = (router_topic,)
        else:
            secondary_topics_for_item = ()
        item = GraphEvidenceItem(
            node_kind="ArticleNode",
            node_key=article_key,
            title=str(row.get("summary") or article_key),
            excerpt=snippet,
            source_path=relative_path or None,
            score=float(row.get("rrf_score") or row.get("fts_rank") or 0.0),
            hop_distance=0 if is_explicit_anchor else 1,
            why=None,
            relation_path=(),
            secondary_topics=secondary_topics_for_item,
            vigencia_v3=dict(vigencia_v3_payload) if isinstance(vigencia_v3_payload, dict) else None,
        )
        if is_explicit_anchor or signals_router_topic:
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
    # fixplan_v3 sub-fix 1B-ε — aggregate the most-restrictive vigencia_v3
    # annotation per doc_id (across that doc's chunks). Chip rendering on
    # the citation list reads from this map.
    vigencia_v3_by_doc: dict[str, dict[str, Any]] = {}
    for row in chunk_rows:
        doc_id = str(row.get("doc_id") or "")
        if not doc_id:
            continue
        v3_payload = row.get("vigencia_v3")
        if isinstance(v3_payload, dict):
            existing = vigencia_v3_by_doc.get(doc_id)
            if existing is None or _v3_more_restrictive(v3_payload, existing):
                vigencia_v3_by_doc[doc_id] = dict(v3_payload)
        if doc_id in seen:
            continue
        if doc_id not in documents_by_doc_id:
            continue
        seen.add(doc_id)
        ordered_doc_ids.append(doc_id)
        if len(ordered_doc_ids) >= limit:
            # Note: don't break — continue iterating to finish the v3
            # aggregation across all chunks (cheap; no extra IO).
            pass

    # Re-trim ordered_doc_ids to the limit
    ordered_doc_ids = ordered_doc_ids[:limit]

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
        citation = Citation.from_document(_document_record_from_row(row))
        # Replace with the v3 vigencia annotation if any of this doc's chunks
        # produced one (frozen-dataclass-safe via dataclasses.replace).
        v3 = vigencia_v3_by_doc.get(doc_id)
        if v3 is not None:
            from dataclasses import replace as _replace
            citation = _replace(citation, vigencia_v3=v3)
        citations.append(citation)
    return tuple(supports), tuple(citations)


# Lower demotion_factor → more restrictive. Tie-break on state ordering.
_V3_STATE_RANK = {
    "DE": 0, "SP": 0, "IE": 0, "VL": 0,
    "DI": 1, "DT": 1,
    "VC": 2, "EC": 2,
    "VM": 3, "RV": 3,
    "V": 4,
}


def _v3_more_restrictive(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    """True iff `a` represents a more restrictive vigencia state than `b`."""

    fa = float(a.get("demotion_factor") if a.get("demotion_factor") is not None else 1.0)
    fb = float(b.get("demotion_factor") if b.get("demotion_factor") is not None else 1.0)
    if fa != fb:
        return fa < fb
    ra = _V3_STATE_RANK.get(str(a.get("anchor_state") or ""), 5)
    rb = _V3_STATE_RANK.get(str(b.get("anchor_state") or ""), 5)
    return ra < rb


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
