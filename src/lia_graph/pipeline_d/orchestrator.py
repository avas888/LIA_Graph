from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from ..pipeline_c.contracts import PipelineCRequest, PipelineCResponse
from .answer_assembly import (
    compose_main_chat_answer as _compose_main_chat_answer,
)
from .answer_llm_polish import polish_graph_native_answer
from .answer_polish_rejected_fallback import (
    compose_polish_rejected_fallback as _compose_polish_rejected_fallback,
    fallback_enabled as _fallback_enabled,
)
from .answer_synthesis import build_graph_native_answer_parts
from .answer_topic_gate import filter_template_bullets as _filter_template_bullets
from .contracts import GraphEvidenceBundle, GraphEvidenceItem, GraphRetrievalPlan
from .planner import build_graph_retrieval_plan
from .answer_comparative_regime import (
    detect_comparative_regime_cue as _detect_comparative_regime_cue,
    match_regime_pair_for_request as _match_regime_pair_for_request,
)
from .query_decomposer import (
    build_sub_query_request,
    decompose_query,
    is_enabled as _decompose_enabled,
    merge_evidence_bundles,
)
from .reranker import rerank_evidence_bundle
from .retriever import retrieve_graph_evidence as _retrieve_artifacts
from ._coherence_gate import (
    coherence_mode as _coherence_mode,
    detect_evidence_coherence,
    refusal_text as _coherence_refusal_text,
    should_refuse as _coherence_should_refuse,
)
from .answer_topic_decomposition import (
    decomposition_mode as _decomp_mode,
    diagnostics_payload as _decomp_diagnostics,
    framing_line as _decomp_framing_line,
    should_decompose as _decomp_should_decompose,
)
from .answer_policy import citation_allowlist_mode, filter_citations_by_allowlist
from .topic_safety import (
    abstention_text_for_misalignment,
    abstention_text_for_router_silent,
    detect_router_silent_failure,
    detect_topic_misalignment,
    should_promote_misalignment_to_abstention,
)

# fix_v1.md hand-off — deep-trace collector for retrieval-stage instrumentation.
# Lives in tracers_and_logs/ at repo root so the package is colocated with
# its log destination (tracers_and_logs/logs/pipeline_trace.jsonl).
from tracers_and_logs import pipeline_trace as _trace


_CORPUS_SOURCE_ENV = "LIA_CORPUS_SOURCE"
_GRAPH_MODE_ENV = "LIA_GRAPH_MODE"
_VALID_CORPUS_SOURCES = {"artifacts", "supabase"}
_VALID_GRAPH_MODES = {"artifacts", "falkor_live"}

# fix_v13_may — dedicated práctica lane env knob.
_PRACTICA_SOURCE_ENV = "LIA_PRACTICA_SOURCE"
_VALID_PRACTICA_SOURCES = {"supabase", "disabled", "filesystem"}


def _current_practica_source() -> str:
    """`supabase` for staging/production, `disabled` for offline dev,
    `filesystem` reserved for a future offline fallback (fix_v13_may §7)."""
    raw = str(os.getenv(_PRACTICA_SOURCE_ENV, "supabase") or "").strip().lower()
    return raw if raw in _VALID_PRACTICA_SOURCES else "supabase"


import logging as _logging
_PRACTICA_LOGGER = _logging.getLogger("lia_graph.pipeline_d.orchestrator.practica")
LOGGER = _logging.getLogger("lia_graph.pipeline_d.orchestrator")


def _retrieve_practica_chunks(
    *,
    query: str,
    topic: str | None,
    pais: str,
    plan: GraphRetrievalPlan,
):
    """fix_v13_may §4 — dispatcher for the dedicated práctica lane.

    Mirrors `interpretacion._retrieve_interpretation_docs`'s contract:
    returns a bundle with `chunks_selected` + `retrieval_diagnostics`.

    Behavior:
      * `supabase` (default for staging + production) — call the dedicated
        RPC adapter; errors propagate per the no-silent-fallback rule.
      * `disabled` (default for `npm run dev`) — return an empty bundle.
      * `filesystem` — explicitly deferred (fix_v13_may §7); raise so an
        operator that flips this on without shipping the fallback finds
        out immediately instead of getting silent degradation.

    The vigencia v3 demotion is applied row-level through a closure so
    chunks tied to inexequible / derogated / suspended anchors drop to
    score 0.0 → filtered out before they reach `build_recommendations`.
    Topic-gate + citation-allow-list run downstream during template
    assembly (`answer_assembly.filter_template_bullets`) so any práctica
    bullet that cites an off-topic norm is gated alongside the unified
    pool's bullets.
    """
    from ..practica.policy import resolve_reserved_slots
    from ..practica.shared import PracticaKnowledgeBundle

    source = _current_practica_source()
    top_k = resolve_reserved_slots()

    _PRACTICA_LOGGER.info(
        "practica.dispatcher.entry source=%s top_k=%d topic=%s query_chars=%d",
        source,
        top_k,
        topic,
        len(query or ""),
    )

    if source == "disabled" or top_k <= 0:
        reason = "source_disabled" if source == "disabled" else "top_k_zero"
        _PRACTICA_LOGGER.info(
            "practica.dispatcher.skip reason=%s source=%s top_k=%d",
            reason,
            source,
            top_k,
        )
        return PracticaKnowledgeBundle(
            chunks_selected=(),
            retrieval_diagnostics={
                "practica_backend": "disabled",
                "selected_chunks": 0,
                "reason": reason,
            },
        )
    if source == "filesystem":
        # fix_v13_may §7 — deferred fallback. Per the no-silent-fallback
        # invariant, surface a hard error instead of degrading to empty.
        _PRACTICA_LOGGER.error(
            "practica.dispatcher.unsupported_source filesystem fallback not shipped"
        )
        raise NotImplementedError(
            "LIA_PRACTICA_SOURCE='filesystem' is reserved for a future"
            " offline fallback (fix_v13_may §7); ship the adapter before"
            " enabling this flag."
        )

    # source == "supabase"
    from ..practica.retriever_supabase import fetch_practica_candidates
    from ..supabase_client import get_supabase_client

    db = get_supabase_client()

    def _vigencia_filter(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Apply the v3 vigencia gate. Wraps the chat-retriever's helper
        so práctica chunks pinned to inexequible / derogated / suspended
        anchors drop before grouping. Returns the input unchanged on
        RPC error so a vigencia outage cannot block the new lane."""
        from .retriever_supabase import _apply_v3_vigencia_demotion as _v3
        filtered, gate_diag = _v3(db, plan, rows)
        _PRACTICA_LOGGER.info(
            "practica.vigencia_gate status=%s chunks_in=%d chunks_kept=%s chunks_dropped=%s chunks_demoted=%s",
            gate_diag.get("status"),
            len(rows),
            gate_diag.get("chunks_kept"),
            gate_diag.get("chunks_dropped"),
            gate_diag.get("chunks_demoted"),
        )
        _trace.step(
            "practica.vigencia_gate.applied",
            status="ok" if gate_diag.get("status") == "ok" else "skipped",
            chunks_in=len(rows),
            chunks_out=len(filtered),
            rpc_kind=gate_diag.get("rpc_kind"),
            chunks_seen=gate_diag.get("chunks_seen"),
            chunks_kept=gate_diag.get("chunks_kept"),
            chunks_dropped=gate_diag.get("chunks_dropped"),
            chunks_demoted=gate_diag.get("chunks_demoted"),
            gate_status=gate_diag.get("status"),
        )
        return filtered

    try:
        bundle = fetch_practica_candidates(
            query_seed=query,
            topic=topic,
            pais=pais,
            top_k=top_k,
            client=db,
            chunk_filter=_vigencia_filter,
        )
    except Exception as exc:  # propagate as observable "error" backend
        _PRACTICA_LOGGER.warning(
            "practica.dispatcher.error kind=%s msg=%s",
            type(exc).__name__,
            repr(exc)[:240],
            exc_info=True,
        )
        _trace.step(
            "practica.dispatcher.error",
            status="error",
            error_kind=type(exc).__name__,
            error=repr(exc)[:240],
        )
        return PracticaKnowledgeBundle(
            chunks_selected=(),
            retrieval_diagnostics={
                "practica_backend": "error",
                "practica_error_kind": type(exc).__name__,
                "selected_chunks": 0,
            },
        )
    diag = dict(getattr(bundle, "retrieval_diagnostics", {}) or {})
    _PRACTICA_LOGGER.info(
        "practica.dispatcher.exit backend=%s selected=%d candidate=%s gate_dropped=%s elapsed_ms=%s",
        diag.get("practica_backend"),
        len(getattr(bundle, "chunks_selected", ()) or ()),
        diag.get("candidate_rows"),
        diag.get("gate_dropped"),
        diag.get("total_elapsed_ms"),
    )
    return bundle


def _current_corpus_source() -> str:
    raw = str(os.getenv(_CORPUS_SOURCE_ENV, "artifacts") or "").strip().lower()
    return raw if raw in _VALID_CORPUS_SOURCES else "artifacts"


def _current_graph_mode() -> str:
    raw = str(os.getenv(_GRAPH_MODE_ENV, "artifacts") or "").strip().lower()
    return raw if raw in _VALID_GRAPH_MODES else "artifacts"


def _artifacts_dir_from_index_file(index_file: object | None) -> Path | None:
    if index_file is None:
        return None
    path = Path(str(index_file))
    if path.name == "canonical_corpus_manifest.json":
        return path.parent
    return None


def _retrieve_evidence(
    plan: GraphRetrievalPlan,
    *,
    artifacts_dir: Path | None,
) -> tuple[GraphRetrievalPlan, GraphEvidenceBundle, dict[str, str]]:
    corpus_source = _current_corpus_source()
    graph_mode = _current_graph_mode()
    backend_diagnostics = {
        "retrieval_backend": corpus_source,
        "graph_backend": graph_mode,
    }

    if corpus_source == "artifacts" and graph_mode == "artifacts":
        hydrated_plan, evidence = _retrieve_artifacts(plan, artifacts_dir=artifacts_dir)
        return hydrated_plan, _attach_backend_diagnostics(evidence, backend_diagnostics), backend_diagnostics

    # Import lazily so dev mode never pulls the Supabase/Falkor modules unless
    # the caller opted into cloud-live retrieval.
    if corpus_source == "supabase":
        from .retriever_supabase import retrieve_graph_evidence as _retrieve_supabase
        supabase_plan, supabase_evidence = _retrieve_supabase(plan, artifacts_dir=artifacts_dir)
    else:
        supabase_plan, supabase_evidence = _retrieve_artifacts(plan, artifacts_dir=artifacts_dir)

    if graph_mode == "falkor_live":
        from .retriever_falkor import retrieve_graph_evidence as _retrieve_falkor
        falkor_plan, falkor_evidence = _retrieve_falkor(plan, artifacts_dir=artifacts_dir)
        merged_plan = falkor_plan
        merged_evidence = _merge_graph_and_chunk_evidence(
            graph_evidence=falkor_evidence,
            chunk_evidence=supabase_evidence,
            backend_diagnostics=backend_diagnostics,
        )
        return merged_plan, merged_evidence, backend_diagnostics

    # Supabase for chunks, artifacts for graph (fallback combination).
    return supabase_plan, _attach_backend_diagnostics(supabase_evidence, backend_diagnostics), backend_diagnostics


def _attach_backend_diagnostics(
    evidence: GraphEvidenceBundle,
    backend_diagnostics: dict[str, str],
) -> GraphEvidenceBundle:
    diagnostics = dict(evidence.diagnostics)
    diagnostics.update(backend_diagnostics)
    return GraphEvidenceBundle(
        primary_articles=evidence.primary_articles,
        connected_articles=evidence.connected_articles,
        related_reforms=evidence.related_reforms,
        support_documents=evidence.support_documents,
        citations=evidence.citations,
        diagnostics=diagnostics,
    )


def _merge_graph_and_chunk_evidence(
    *,
    graph_evidence: GraphEvidenceBundle,
    chunk_evidence: GraphEvidenceBundle,
    backend_diagnostics: dict[str, str],
) -> GraphEvidenceBundle:
    diagnostics = dict(chunk_evidence.diagnostics)
    diagnostics.update(graph_evidence.diagnostics)
    diagnostics.update(backend_diagnostics)
    # Preserve each half's `empty_reason` separately so an operator can still
    # see e.g. `chunks_empty_reason=corpus_not_seeded` even when the graph
    # half saved the turn. Otherwise the winning half's reason masks a real
    # ingestion gap on the losing half.
    chunks_reason = chunk_evidence.diagnostics.get("empty_reason")
    graph_reason = graph_evidence.diagnostics.get("empty_reason")
    if isinstance(chunks_reason, str):
        diagnostics["chunks_empty_reason"] = chunks_reason
    if isinstance(graph_reason, str):
        diagnostics["graph_empty_reason"] = graph_reason
    primary = graph_evidence.primary_articles or chunk_evidence.primary_articles
    connected = graph_evidence.connected_articles or chunk_evidence.connected_articles
    related = graph_evidence.related_reforms or chunk_evidence.related_reforms
    # fix_v16 b5 (2026-05-14) — Falkor's `secondary_topics` is loaded at
    # ingest from `config/article_secondary_topics.json`; live edits to the
    # JSON don't reach Falkor until re-ingest. Supabase's retriever reads
    # the same JSON at request time. To keep the JSON authoritative for
    # the coherence-gate's secondary-topic short-circuit (topic_safety.py
    # line 145–157) without forcing a full Falkor re-ingest on every
    # rescue-config update, augment the winning primary_articles with the
    # JSON view here at the merge boundary.
    primary = _augment_secondary_topics_from_json(primary)
    connected = _augment_secondary_topics_from_json(connected)
    return GraphEvidenceBundle(
        primary_articles=primary,
        connected_articles=connected,
        related_reforms=related,
        support_documents=chunk_evidence.support_documents,
        citations=chunk_evidence.citations,
        diagnostics=diagnostics,
    )


def _augment_secondary_topics_from_json(
    items: tuple[GraphEvidenceItem, ...],
) -> tuple[GraphEvidenceItem, ...]:
    if not items:
        return items
    from .retriever_supabase import _load_article_topic_index
    import dataclasses
    index = _load_article_topic_index()
    if not index:
        return items
    augmented: list[GraphEvidenceItem] = []
    for it in items:
        json_topics = index.get(str(it.node_key or ""), frozenset())
        if not json_topics:
            augmented.append(it)
            continue
        existing = tuple(it.secondary_topics or ())
        # Union; preserve item topics first so any item-specific tags survive.
        merged = tuple(dict.fromkeys((*existing, *json_topics)))
        augmented.append(dataclasses.replace(it, secondary_topics=merged))
    return tuple(augmented)


def _compose_graph_native_answer(
    *,
    request: PipelineCRequest,
    answer_mode: str,
    planner_query_mode: str,
    temporal_context: dict[str, object],
    evidence: GraphEvidenceBundle,
    sub_questions: tuple[str, ...] = (),
    practica_chunks: tuple = (),
):
    """Return ``(answer_markdown, answer_parts)``.

    fix_v8 §3a — ``answer_parts`` is surfaced back to the caller so the
    polish-rejected fallback can re-render a substantive answer from the
    same deterministic parts when ``polish_graph_native_answer`` rejects.

    fix_v13_may §4 — ``practica_chunks`` from the dedicated lane is
    threaded into ``build_graph_native_answer_parts`` so the
    `**Recomendaciones Prácticas**` section is fed by real
    `knowledge_class='practica_erp'` content before falling through to
    article-derived bullets.
    """
    answer_parts = build_graph_native_answer_parts(
        request=request,
        answer_mode=answer_mode,
        planner_query_mode=planner_query_mode,
        temporal_context=temporal_context,
        evidence=evidence,
        sub_questions=sub_questions,
        practica_chunks=practica_chunks,
    )
    answer = _compose_main_chat_answer(
        request=request,
        answer_mode=answer_mode,
        planner_query_mode=planner_query_mode,
        temporal_context=temporal_context,
        evidence=evidence,
        answer_parts=answer_parts,
    )
    if answer:
        return answer, answer_parts
    if answer_mode == "graph_native_partial":
        return (
            "Usa esta salida solo como orientación inicial y confirma el expediente antes de convertirla en instrucción cerrada para el cliente.",
            answer_parts,
        )
    return (
        "Con la evidencia disponible todavía no alcanzo una recomendación operativa suficientemente confiable.",
        answer_parts,
    )


def _compose_topic_safety_abstention(
    *,
    request: PipelineCRequest,
    index_file: object | None,
    policy_path: object | None,
    runtime_config_path: object | None,
    answer_text: str,
    fallback_reason: str,
    confidence_mode: str,
    topic_safety: dict[str, object],
    backend_diagnostics: dict[str, str],
    on_llm_delta: object | None,
    pipeline_trace: dict[str, Any] | None = None,
) -> PipelineCResponse:
    """Shared short-circuit response for router-safety abstentions.

    Mirrors the FileNotFoundError branch's shape so downstream consumers
    (UI, diagnostics, tests) see a well-formed PipelineCResponse with a
    clear fallback_reason + topic_safety block.
    """
    if callable(on_llm_delta):
        on_llm_delta(answer_text)
    return PipelineCResponse(
        trace_id=str(request.trace_id or uuid4().hex),
        run_id=f"pd_{uuid4().hex}",
        answer_markdown=answer_text,
        answer_concise=answer_text,
        followup_queries=(),
        citations=(),
        confidence_score=0.05,
        confidence_mode=confidence_mode,
        answer_mode="topic_safety_abstention",
        compose_quality=0.0,
        fallback_reason=fallback_reason,
        evidence_snippets=(),
        diagnostics={
            "compatibility_mode": False,
            "pipeline_family": "pipeline_d",
            "index_file": str(index_file) if index_file is not None else None,
            "policy_path": str(policy_path) if policy_path is not None else None,
            "runtime_config_path": (
                str(runtime_config_path) if runtime_config_path is not None else None
            ),
            "retrieval_backend": backend_diagnostics.get("retrieval_backend"),
            "graph_backend": backend_diagnostics.get("graph_backend"),
            # fix_v8 §3b — abstention path never invokes polish, but the
            # diagnostic surface must be present on every served chat so
            # downstream consumers (SME report, probe digest) can read it
            # unconditionally.
            "polish_mode": "skipped",
            "polish_skip_reason": "topic_safety_abstention",
            "topic_safety": topic_safety,
            "pipeline_trace": pipeline_trace,
        },
        llm_runtime=None,
        token_usage=None,
        timing=None,
        requested_topic=request.requested_topic,
        effective_topic=request.topic,
        secondary_topics=request.secondary_topics,
        topic_adjusted=request.topic_adjusted,
        topic_notice=request.topic_notice,
        topic_adjustment_reason=request.topic_adjustment_reason,
        coverage_notice=answer_text,
        pipeline_variant="pipeline_d",
        pipeline_route="pipeline_d",
    )


def run_pipeline_d(
    request: PipelineCRequest,
    *,
    index_file: object | None = None,
    policy_path: object | None = None,
    runtime_config_path: object | None = None,
    stream_sink: object | None = None,
) -> PipelineCResponse:
    sink = stream_sink
    if sink is not None:
        status = getattr(sink, "status", None)
        on_llm_delta = getattr(sink, "on_llm_delta", None)
        if callable(status):
            status("pipeline_d", "Planificando anclajes graph-native sobre el grafo validado...")
    else:
        on_llm_delta = None

    backend_diagnostics = {
        "retrieval_backend": _current_corpus_source(),
        "graph_backend": _current_graph_mode(),
    }

    # fix_v1.md — install a per-request deep trace. The chat-payload module
    # may have already started one (so topic_router events land in the same
    # trace); reuse if so, else install our own. ``_trace_token is None``
    # signals "owned by an outer scope; do not finish here".
    _trace_active, _trace_token = _trace.start_or_reuse(
        trace_id=str(request.trace_id or ""),
        qid_hint=getattr(request, "qid_hint", None),
        session_id=getattr(request, "session_id", None),
    )
    _trace.step(
        "orchestrator.entry",
        status="info",
        retrieval_backend=backend_diagnostics["retrieval_backend"],
        graph_backend=backend_diagnostics["graph_backend"],
        requested_topic=request.requested_topic,
        effective_topic=request.topic,
        secondary_topics=list(request.secondary_topics or ()),
        topic_adjusted=bool(getattr(request, "topic_adjusted", False)),
        topic_adjustment_reason=getattr(request, "topic_adjustment_reason", None),
        topic_notice=getattr(request, "topic_notice", None),
        message_preview=str(request.message)[:240],
        message_chars=len(request.message or ""),
    )

    # SAFETY CHECK 1: router silent-failure.
    # If the upstream topic router returned no topic with effectively zero
    # confidence, refuse to synthesize from whatever grab-bag articles
    # fall out of general_graph_research retrieval. See topic_safety.py
    # and `docs/done/next/structuralwork_v1_SEENOW.md` v5.3 landed-state.
    silent_failure = detect_router_silent_failure(request)
    if silent_failure is not None:
        _trace.step(
            "safety.router_silent_failure",
            status="fallback",
            message="Topic router returned no topic with effectively zero confidence; abstaining.",
            silent_failure=silent_failure,
        )
        _snap = _trace.snapshot()
        _trace.finish(_trace_token)
        return _compose_topic_safety_abstention(
            request=request,
            index_file=index_file,
            policy_path=policy_path,
            runtime_config_path=runtime_config_path,
            answer_text=abstention_text_for_router_silent(),
            fallback_reason="pipeline_d_router_silent_failure",
            confidence_mode="router_silent_failure",
            topic_safety={"router_silent": silent_failure, "misalignment": None},
            backend_diagnostics=backend_diagnostics,
            on_llm_delta=on_llm_delta,
            pipeline_trace=_snap,
        )

    decomposer_diag: dict[str, Any] = {"enabled": _decompose_enabled(), "sub_queries": []}
    # Per-sub-query (request, bundle) pairs feed the multi-question safety
    # path: the coherence gate must evaluate each sub-bundle against its OWN
    # routed topic. Evaluating the merged bundle against the parent topic is
    # a guaranteed false positive whenever sub-questions span topics.
    per_sq_for_safety: list[tuple[PipelineCRequest, GraphEvidenceBundle]] = []
    try:
        artifacts_dir = _artifacts_dir_from_index_file(index_file)
        if sink is not None and callable(status):
            status("pipeline_d", "Recuperando evidencia desde graph artifacts y canonical manifest...")

        # V2-2: if query decomposition is enabled and the query has
        # multiple ¿…? sub-questions, route + plan + retrieve per
        # sub-query and merge the evidence bundles before synthesis.
        # Otherwise, single-query path (today's behavior).
        sub_queries: tuple[str, ...] = ()
        if _decompose_enabled():
            sub_queries = decompose_query(request.message)
            decomposer_diag["sub_queries"] = list(sub_queries)

        # next_v4 §5 — skip fan-out when the parent message itself is a
        # comparative-regime query. The decomposer naively splits things
        # like "cuanto cambia esto? Solo cambia si pre-2017..." into two
        # sub-queries where only the SECOND carries the cue, so the first
        # sub-query's plan (article_lookup) ends up dominating downstream
        # and the comparative table is never rendered. When the parent
        # matches comparative-regime AND a config pair matches, the single
        # comparative answer is strictly better than a fanned-out one.
        if sub_queries:
            parent_cue, _ = _detect_comparative_regime_cue(request.message)
            if parent_cue and _match_regime_pair_for_request(request) is not None:
                sub_queries = ()
                decomposer_diag["sub_queries"] = []
                decomposer_diag["fanout_suppressed_reason"] = "comparative_regime_parent"

        if sub_queries:
            from ..topic_router import (
                resolve_chat_topic as _resolve,
                TopicRoutingResult,
                normalize_topic_key,
            )

            _trace.step(
                "decomposer.fanout",
                status="info",
                fanout_count=len(sub_queries),
                sub_queries=list(sub_queries),
            )
            per_bundles: list[Any] = []
            provenance: list[dict[str, Any]] = []
            plan = None
            parent_topic = normalize_topic_key(request.topic)
            for _sq_idx, sq in enumerate(sub_queries):
                sq_routing = _resolve(message=sq, requested_topic=None, pais=request.pais)
                # fix_v5 phase 6b (Q1) — sub-Q topic carry-over from parent.
                # Short sub-Qs ("¿eso cambia algo?") often miss the rule-route
                # AND the LLM path is skipped at this site (no
                # runtime_config_path), so the keyword fallback either picks
                # the wrong topic (incidental keywords → factura_electronica
                # drift) or hits nothing. When the parent's resolved topic is
                # available AND the sub-Q result is in fallback mode AND it
                # disagrees with the parent, inherit the parent's topic. A
                # confident rule-route hit on a different topic stays
                # respected (multi-domain integrity, fix_v5.md §4 #16).
                # fix_v22 §9c P2-T-Orphan-1 (orig L14) — canonical-shape escape
                # hatch BEFORE the inherited-parent override. When the sub-Q
                # matches a curated canonical shape, its keyword-fallback
                # result is real (the shape vouches for the topic) and must
                # NOT be steamrolled by the parent topic. Empty config = noop.
                if getattr(sq_routing, "mode", None) == "fallback":
                    try:
                        from ..canonical_question_shapes import match_canonical_shape
                        _sq_shape = match_canonical_shape(
                            sq, classified_topic=sq_routing.effective_topic
                        )
                    except Exception:  # noqa: BLE001 — defensive; config errors must not block routing
                        _sq_shape = None
                    if _sq_shape is not None and _sq_shape.topic:
                        _trace.step(
                            "topic_router.subquery_canonical_shape",
                            status="ok",
                            sub_query_index=_sq_idx,
                            sub_query=sq,
                            shape_id=_sq_shape.id,
                            shape_topic=_sq_shape.topic,
                        )
                        sq_routing = TopicRoutingResult(
                            requested_topic=None,
                            effective_topic=_sq_shape.topic,
                            secondary_topics=tuple(_sq_shape.secondary_topics or ()),
                            topic_adjusted=False,
                            confidence=0.75,
                            reason=f"fix_v22_orphan_L14:canonical_shape:{_sq_shape.id}",
                            topic_notice=None,
                            mode="canonical_shape",
                        )

                if (
                    parent_topic
                    and getattr(sq_routing, "mode", None) == "fallback"
                    and sq_routing.effective_topic != parent_topic
                ):
                    _trace.step(
                        "topic_router.subquery_inherited_parent",
                        status="fallback",
                        sub_query_index=_sq_idx,
                        sub_query=sq,
                        original_effective_topic=sq_routing.effective_topic,
                        original_mode=getattr(sq_routing, "mode", None),
                        original_confidence=round(float(sq_routing.confidence or 0.0), 3),
                        parent_topic=parent_topic,
                    )
                    sq_routing = TopicRoutingResult(
                        requested_topic=None,
                        effective_topic=parent_topic,
                        secondary_topics=tuple(request.secondary_topics or ()),
                        topic_adjusted=False,
                        confidence=0.6,
                        reason="fix_v5_phase6b:subquery_inherited_parent",
                        topic_notice=None,
                        mode="subquery_parent_inheritance",
                    )
                _trace.step(
                    "topic_router.subquery_resolved",
                    status="ok",
                    sub_query_index=_sq_idx,
                    sub_query=sq,
                    effective_topic=sq_routing.effective_topic,
                    secondary_topics=list(sq_routing.secondary_topics or ()),
                    confidence=round(float(sq_routing.confidence or 0.0), 3),
                    mode=getattr(sq_routing, "mode", None),
                    reason=getattr(sq_routing, "reason", None),
                    topic_adjusted=getattr(sq_routing, "topic_adjusted", None),
                )
                sq_request = build_sub_query_request(
                    parent_request=request,
                    sub_query=sq,
                    resolved_topic=sq_routing.effective_topic,
                    secondary_topics=sq_routing.secondary_topics,
                    topic_confidence=sq_routing.confidence,
                )
                sq_plan = build_graph_retrieval_plan(sq_request)
                _trace.step(
                    "planner.subquery_built",
                    status="ok",
                    sub_query_index=_sq_idx,
                    plan_query_mode=getattr(sq_plan, "query_mode", None),
                    plan_anchor_count=len(getattr(sq_plan, "anchor_articles", ()) or ()),
                    plan_subtopic_intent=getattr(sq_plan, "sub_topic_intent", None),
                )
                sq_plan, sq_evidence, sq_backend = _retrieve_evidence(
                    sq_plan, artifacts_dir=artifacts_dir
                )
                _trace.step(
                    "retriever.subquery_evidence",
                    status="ok",
                    sub_query_index=_sq_idx,
                    primary_count=len(sq_evidence.primary_articles),
                    connected_count=len(sq_evidence.connected_articles),
                    support_count=len(sq_evidence.support_documents),
                    backend_diagnostics=dict(sq_backend or {}),
                    evidence_diagnostics_keys=sorted((sq_evidence.diagnostics or {}).keys()),
                    empty_reason=(sq_evidence.diagnostics or {}).get("empty_reason"),
                    vigencia_v3_demotion=(sq_evidence.diagnostics or {}).get(
                        "vigencia_v3_demotion"
                    ),
                )
                per_bundles.append(sq_evidence)
                per_sq_for_safety.append((sq_request, sq_evidence))
                provenance.append(
                    {
                        "sub_query": sq,
                        "router_topic": sq_routing.effective_topic,
                        "router_confidence": round(float(sq_routing.confidence or 0.0), 3),
                        "primary_count": len(sq_evidence.primary_articles),
                        "connected_count": len(sq_evidence.connected_articles),
                    }
                )
                # Keep the first plan for downstream consumers that still
                # expect a single `plan.to_dict()` in diagnostics; the
                # sub-query provenance block surfaces the full fan-out.
                if plan is None:
                    plan = sq_plan
                backend_diagnostics = sq_backend

            evidence = merge_evidence_bundles(
                per_bundles, per_sub_query_provenance=provenance
            )
            # If fan-out happened but the primary plan is somehow None
            # (empty sub_queries race), fall through to single-query.
            if plan is None:
                plan = build_graph_retrieval_plan(request)
                plan, evidence, backend_diagnostics = _retrieve_evidence(
                    plan, artifacts_dir=artifacts_dir
                )
            decomposer_diag["fanout_count"] = len(sub_queries)
        else:
            plan = build_graph_retrieval_plan(request)
            _trace.step(
                "planner.built",
                status="ok",
                plan_query_mode=getattr(plan, "query_mode", None),
                plan_anchor_count=len(getattr(plan, "anchor_articles", ()) or ()),
                plan_subtopic_intent=getattr(plan, "sub_topic_intent", None),
                plan_temporal_context=getattr(plan, "temporal_context", None).to_dict()
                    if hasattr(getattr(plan, "temporal_context", None), "to_dict") else None,
            )
            plan, evidence, backend_diagnostics = _retrieve_evidence(
                plan, artifacts_dir=artifacts_dir
            )
            _trace.step(
                "retriever.evidence",
                status="ok",
                primary_count=len(evidence.primary_articles),
                connected_count=len(evidence.connected_articles),
                support_count=len(evidence.support_documents),
                backend_diagnostics=dict(backend_diagnostics or {}),
                evidence_diagnostics_keys=sorted((evidence.diagnostics or {}).keys()),
                empty_reason=(evidence.diagnostics or {}).get("empty_reason"),
                vigencia_v3_demotion=(evidence.diagnostics or {}).get("vigencia_v3_demotion"),
                seed_article_keys=(evidence.diagnostics or {}).get("seed_article_keys"),
                tema_first_topic_key=(evidence.diagnostics or {}).get("tema_first_topic_key"),
                planner_query_mode=(evidence.diagnostics or {}).get("planner_query_mode"),
            )
            decomposer_diag["fanout_count"] = 0

        _evidence_before_rerank = (
            len(evidence.primary_articles),
            len(evidence.connected_articles),
            len(evidence.support_documents),
        )
        evidence, reranker_diagnostics = rerank_evidence_bundle(
            query=request.message,
            evidence=evidence,
        )
        _trace.step(
            "rerank.applied",
            status="ok",
            mode=(reranker_diagnostics or {}).get("mode"),
            adapter=(reranker_diagnostics or {}).get("adapter"),
            before=list(_evidence_before_rerank),
            after=[
                len(evidence.primary_articles),
                len(evidence.connected_articles),
                len(evidence.support_documents),
            ],
            reranker_diagnostics=dict(reranker_diagnostics or {}),
        )
    except FileNotFoundError:
        answer = (
            "Pipeline D no encontro los artifacts graph-native esperados en disco, "
            "asi que no pudo ejecutar la ruta Phase 3 todavia."
        )
        _trace.step(
            "orchestrator.artifacts_missing",
            status="error",
            message="FileNotFoundError caught — artifacts dir missing on disk.",
        )
        _snap_artifacts = _trace.snapshot()
        _trace.finish(_trace_token)
        if callable(on_llm_delta):
            on_llm_delta(answer)
        return PipelineCResponse(
            trace_id=str(request.trace_id or uuid4().hex),
            run_id=f"pd_{uuid4().hex}",
            answer_markdown=answer,
            answer_concise=answer,
            followup_queries=(),
            citations=(),
            confidence_score=0.05,
            confidence_mode="graph_artifacts_missing",
            answer_mode="compat_stub",
            compose_quality=0.0,
            fallback_reason="pipeline_d_graph_artifacts_missing",
            evidence_snippets=(),
            diagnostics={
                "compatibility_mode": True,
                "pipeline_family": "pipeline_d",
                "index_file": str(index_file) if index_file is not None else None,
                "policy_path": str(policy_path) if policy_path is not None else None,
                "runtime_config_path": (
                    str(runtime_config_path) if runtime_config_path is not None else None
                ),
                "retrieval_backend": backend_diagnostics.get("retrieval_backend"),
                "graph_backend": backend_diagnostics.get("graph_backend"),
                "pipeline_trace": _snap_artifacts,
            },
            llm_runtime=None,
            token_usage=None,
            timing=None,
            requested_topic=request.requested_topic,
            effective_topic=request.topic,
            secondary_topics=request.secondary_topics,
            topic_adjusted=request.topic_adjusted,
            topic_notice=request.topic_notice,
            topic_adjustment_reason=request.topic_adjustment_reason,
            coverage_notice="Artifacts graph-native faltantes para la ruta Phase 3.",
            pipeline_variant="pipeline_d",
            pipeline_route="pipeline_d",
        )

    # SAFETY CHECK 2: router↔retrieval misalignment.
    # The router may have picked a topic (so check 1 didn't fire) but the
    # primary articles the retriever found don't lexically belong to that
    # topic. This is the Q1 / Q26-class failure. If the router's own
    # confidence was already borderline, promote to abstention; otherwise
    # stash the signal in diagnostics so the alignment harness catches it.
    misalignment = detect_topic_misalignment(request, evidence)
    _trace.step(
        "safety.misalignment.detect",
        status="ok",
        misaligned=bool(misalignment.get("misaligned")),
        kind=misalignment.get("kind"),
        router_topic=misalignment.get("router_topic"),
        evidence_topic=misalignment.get("evidence_topic"),
        details=dict(misalignment),
    )
    if should_promote_misalignment_to_abstention(request, misalignment):
        _trace.step(
            "safety.misalignment.abstention",
            status="fallback",
            message="Promoting topic misalignment to abstention (borderline confidence).",
        )
        _snap_misal = _trace.snapshot()
        _trace.finish(_trace_token)
        return _compose_topic_safety_abstention(
            request=request,
            index_file=index_file,
            policy_path=policy_path,
            runtime_config_path=runtime_config_path,
            answer_text=abstention_text_for_misalignment(misalignment),
            fallback_reason="pipeline_d_topic_misalignment_borderline_confidence",
            confidence_mode="topic_misalignment",
            topic_safety={
                "router_silent": None,
                "misalignment": {"kind": "topic_misalignment", **misalignment},
            },
            backend_diagnostics=backend_diagnostics,
            on_llm_delta=on_llm_delta,
            pipeline_trace=_snap_misal,
        )

    # SAFETY CHECK 3 (v6 phase 3): evidence-topic coherence gate.
    # topic_safety short-circuits on empty primary_articles — that is the
    # exact window the Q16 biofuel contamination slipped through. The
    # coherence gate scores support_documents when primary is empty and
    # refuses when no support doc matches the router topic. Flag-gated;
    # default is ``shadow`` so the diagnostic is observed before enforced.
    coherence_gate_mode = _coherence_mode()
    if per_sq_for_safety:
        # Multi-question fan-out: each sub-query was routed and retrieved
        # against its OWN topic. The gate is globally coherent if ANY
        # sub-question is coherent with its own topic; the merged bundle
        # vs. the parent topic would always misfire on legitimate
        # multi-topic queries (e.g. pérdidas fiscales + firmeza).
        sub_coherences: list[dict[str, Any]] = []
        for sq_request, sq_bundle in per_sq_for_safety:
            sq_misalign = detect_topic_misalignment(sq_request, sq_bundle)
            sub_coherences.append(
                detect_evidence_coherence(sq_request, sq_bundle, sq_misalign)
            )
        any_coherent = any(not c.get("misaligned") for c in sub_coherences)
        representative = next(
            (c for c in sub_coherences if not c.get("misaligned")),
            sub_coherences[0],
        )
        coherence = {
            **representative,
            "fanout_evaluated": True,
            "fanout_any_coherent": any_coherent,
            "sub_coherences": sub_coherences,
        }
        if any_coherent:
            coherence["misaligned"] = False
    else:
        coherence = detect_evidence_coherence(request, evidence, misalignment)
        # Follow-up turns anchored on conversation_state.normative_anchors
        # are retrieved by the planner against those anchors, not against
        # the (often diluted) router topic. Treating the router topic as
        # ground truth here misfires whenever the accountant drills into a
        # specific aspect of the prior turn ("¿hay límite anual?", "¿cuánto
        # cambia?"). Mirror the bypass already present in
        # detect_router_silent_failure: register the diagnostic but do not
        # refuse when the conversation has already established anchors.
        state = request.conversation_state or {}
        anchors = state.get("normative_anchors") if isinstance(state, dict) else None
        has_conversation_anchors = isinstance(anchors, (list, tuple)) and any(
            isinstance(a, str) and a.strip() for a in anchors
        )
        if has_conversation_anchors and coherence.get("misaligned"):
            coherence = {
                **coherence,
                "bypass_reason": "conversation_state_anchored",
                "router_topic_observed": coherence.get("router_topic"),
                "misaligned": False,
            }
    _trace.step(
        "coherence.detect",
        status="ok",
        mode=coherence_gate_mode,
        misaligned=bool(coherence.get("misaligned")),
        reason=coherence.get("reason"),
        source=coherence.get("source"),
        router_topic=coherence.get("router_topic"),
        evidence_topic_distribution=coherence.get("evidence_topic_distribution"),
        bypass_reason=coherence.get("bypass_reason"),
        fanout_evaluated=coherence.get("fanout_evaluated"),
        fanout_any_coherent=coherence.get("fanout_any_coherent"),
    )
    # v23 P1 — Topic-Gate Decomposition (G1). When the gate would refuse on
    # a multi-domain question (router topic disagrees with retrieved articles'
    # dominant topic), bypass the refusal so synthesis+polish produce a
    # substantive answer with a framing line prepended after polish. The
    # audit (2026-05-17) showed Q1/Q3/Q6/Q8 = 4 of 10 refused as topic
    # mismatch when the retrieved evidence was real and accountant-useful.
    # Flag-gated; `LIA_TOPIC_DECOMPOSITION_MODE=off` keeps v22 refusal.
    _decomposition_state: dict[str, Any] = {"applied": False}
    if (
        coherence_gate_mode == "enforce"
        and _coherence_should_refuse(coherence, coherence_gate_mode)
        and _decomp_should_decompose(
            coherence, evidence, (request.topic or "").strip()
        )
    ):
        _decomposition_state = {
            "applied": True,
            "framing_line": _decomp_framing_line(
                coherence, evidence, (request.topic or "").strip()
            ),
            "diagnostics": _decomp_diagnostics(
                coherence, evidence, (request.topic or "").strip(), applied=True
            ),
        }
        coherence = {
            **coherence,
            "bypass_reason": "topic_decomposition_v23",
            "router_topic_observed": coherence.get("router_topic"),
            "misaligned": False,
        }
        _trace.step(
            "coherence.decomposition_bypass",
            status="ok",
            mode=_decomp_mode(),
            router_topic=(request.topic or "").strip(),
            section_count=_decomposition_state["diagnostics"][
                "topic_decomposition_section_count"
            ],
        )
    if coherence_gate_mode == "enforce" and _coherence_should_refuse(
        coherence, coherence_gate_mode
    ):
        _trace.step(
            "coherence.abstention",
            status="fallback",
            message="Evidence-coherence gate refused (enforce mode).",
            refusal_reason=coherence.get("reason"),
            refusal_source=coherence.get("source"),
        )
        _snap_coh = _trace.snapshot()
        _trace.finish(_trace_token)
        return _compose_topic_safety_abstention(
            request=request,
            index_file=index_file,
            policy_path=policy_path,
            runtime_config_path=runtime_config_path,
            answer_text=_coherence_refusal_text(coherence),
            fallback_reason=f"pipeline_d_coherence_{coherence.get('reason', 'misaligned')}",
            confidence_mode="evidence_coherence_refusal",
            topic_safety={
                "router_silent": None,
                "misalignment": misalignment,
                "coherence": {"mode": coherence_gate_mode, **coherence},
                "refusal_reason": coherence.get("reason"),
                "refusal_source": coherence.get("source"),
            },
            backend_diagnostics=backend_diagnostics,
            on_llm_delta=on_llm_delta,
            pipeline_trace=_snap_coh,
        )

    topic_safety_diag = {
        "router_silent": None,
        "misalignment": misalignment,
        "coherence": {"mode": coherence_gate_mode, **coherence},
    }

    answer_mode = "graph_native"
    fallback_reason = None
    confidence = 0.82 if evidence.primary_articles else 0.42
    confidence_mode = "graph_artifact_planner_v1"
    coverage_notice = None
    retrieval_health = _build_retrieval_health(
        evidence=evidence,
        backend_diagnostics=backend_diagnostics,
    )
    if not evidence.primary_articles:
        answer_mode = "graph_native_partial"
        fallback_reason = "pipeline_d_no_graph_primary_articles"
        coverage_notice = _compose_partial_coverage_notice(retrieval_health)
    elif misalignment.get("misaligned"):
        # Confident-enough router but misaligned evidence — serve the
        # answer with a hedged confidence band instead of abstaining,
        # since the accountant may still want to see the evidence.
        confidence = min(confidence, 0.55)
        confidence_mode = "topic_misalignment_hedged"

    # Fan-out path: the parent's sub-questions (sub_queries) drive the
    # multi-question answer shape. plan is the FIRST sub-query's plan and
    # its sub_questions tuple is empty (atomic sub-queries have no further
    # ¿…? splits), so reusing it would suppress the Respuestas directas
    # section that build_direct_answers needs len(sub_questions) >= 2 to emit.
    effective_sub_questions = sub_queries if sub_queries else plan.sub_questions

    # fix_v13_may §4 — dedicated práctica retrieval lane. Fetches
    # `knowledge_class='practica_erp'` chunks into a reserved-slot
    # budget that feeds `build_recommendations` ahead of the
    # article-derived fallbacks. Errors degrade to `practica_backend=
    # "error"` (the section falls through to v12 behavior); never
    # silently masks as filesystem.
    _trace.step(
        "practica_retrieve.in",
        status="info",
        query_preview=str(request.message)[:160],
        topic=request.topic,
        source=_current_practica_source(),
    )
    practica_bundle = _retrieve_practica_chunks(
        query=request.message,
        topic=request.topic,
        pais=request.pais,
        plan=plan,
    )
    practica_chunks = tuple(getattr(practica_bundle, "chunks_selected", ()) or ())
    practica_retrieval_diag = dict(
        getattr(practica_bundle, "retrieval_diagnostics", {}) or {}
    )
    _trace.step(
        "practica_retrieve.out",
        status="ok",
        practica_backend=practica_retrieval_diag.get("practica_backend"),
        candidate_rows=practica_retrieval_diag.get("candidate_rows"),
        selected_chunks=practica_retrieval_diag.get("selected_chunks"),
        embedding_mode=practica_retrieval_diag.get("embedding_mode"),
    )
    _trace.step(
        "practica_quality_gate",
        status="ok",
        gate_dropped=practica_retrieval_diag.get("gate_dropped"),
        candidate_rows=practica_retrieval_diag.get("candidate_rows"),
        candidate_rows_after_gate=practica_retrieval_diag.get(
            "candidate_rows_after_gate"
        ),
    )
    _trace.step(
        "practica_merge",
        status="ok",
        reserved_count=len(practica_chunks),
    )

    _trace.step(
        "synthesis.compose_template",
        status="ok",
        answer_mode=answer_mode,
        planner_query_mode=plan.query_mode,
        sub_question_count=len(effective_sub_questions or ()),
        practica_reserved_count=len(practica_chunks),
    )
    answer, answer_parts = _compose_graph_native_answer(
        request=request,
        answer_mode=answer_mode,
        planner_query_mode=plan.query_mode,
        temporal_context=plan.temporal_context.to_dict(),
        evidence=evidence,
        sub_questions=effective_sub_questions,
        practica_chunks=practica_chunks,
    )
    _trace.step(
        "synthesis.template_built",
        status="ok",
        template_chars=len(answer or ""),
    )
    polished_answer, llm_runtime_diag = polish_graph_native_answer(
        request=request,
        template_answer=answer,
        evidence=evidence,
        runtime_config_path=runtime_config_path,
    )
    # fix_v8 §3b — surface `mode` + `skip_reason` so silent polish
    # rejections become observable. `mode` ∈ {llm, skipped, rejected,
    # failed, unknown}; `skip_reason` is one of the enumerated values in
    # answer_llm_polish.py (e.g. invented_norm_lineage, invented_periods,
    # anchors_stripped, empty_llm_output, adapter_error:<Type>,
    # no_adapter_available, polish_disabled_by_env, empty_template,
    # resolver_error:<Type>).
    _polish_diag = llm_runtime_diag or {}
    _polish_mode = _polish_diag.get("mode") or "unknown"
    # v23 P2 — surface detected fiscal year + whether the year-constants
    # directive was injected. Defaults to None / off when the question
    # carries no year signal.
    try:
        from ..year_facts import extract_fiscal_year as _yc_extract
        from ..year_facts import get_year_facts as _yc_facts
        from ..year_facts import injection_mode as _yc_mode
        _v23_fiscal_year = _yc_extract(
            request.message,
            planner_intent=None,
            conversation_state=(getattr(request, "conversation_state", None) or {}),
        )
        _v23_year_injected = (
            _yc_mode() != "off"
            and _v23_fiscal_year is not None
            and _yc_facts(_v23_fiscal_year) is not None
        )
    except Exception:  # noqa: BLE001
        _v23_fiscal_year = None
        _v23_year_injected = False
    _polish_skip = _polish_diag.get("skip_reason")
    _trace.step(
        "polish.applied",
        status="ok" if _polish_mode in {"llm", "skipped"} else "warn",
        mode=_polish_mode,
        skip_reason=_polish_skip,
        adapter_class=_polish_diag.get("adapter_class"),
        model=_polish_diag.get("model"),
        selected_provider=_polish_diag.get("selected_provider"),
        selected_type=_polish_diag.get("selected_type"),
        selected_transport=_polish_diag.get("selected_transport"),
        attempts_count=len(_polish_diag.get("attempts") or []),
        polished_chars=len(polished_answer or ""),
        polish_changed=bool((polished_answer or "") != (answer or "")),
    )
    answer = polished_answer

    # v23 P1 — prepend framing line so the reader knows the answer spans
    # multiple domains (topic-decomposition bypass fired earlier).
    if _decomposition_state.get("applied") and answer:
        _framing = _decomposition_state.get("framing_line") or ""
        if _framing and not answer.lstrip().startswith(_framing[:40]):
            answer = _framing + answer

    # fix_v8 §3a — substantive fallback when polish was rejected.
    # Without this, polish-rejected turns return the bare first-bubble
    # template (question echo only, ~120 chars). With this, we assemble
    # the standard section shape from GraphNativeAnswerParts so the user
    # gets the deterministic answer the engine already has — minus only
    # the tone-polished prose. The cross-topic gate is then applied to
    # the fallback's output so the §6.6c invariant holds for the
    # polish-rejected path too. Operator override:
    # `LIA_POLISH_REJECTED_FALLBACK_MODE=off` reverts to the legacy
    # thin-template behavior for incident rollback only.
    if _polish_mode == "rejected" and _fallback_enabled():
        fallback = _compose_polish_rejected_fallback(
            request=request,
            template_answer=answer,
            answer_parts=answer_parts,
            polish_skip_reason=_polish_skip,
        )
        _trace.step(
            "polish.rejected.fallback_composed",
            status="ok",
            polish_skip_reason=_polish_skip,
            template_chars=len(answer or ""),
            fallback_chars=len(fallback or ""),
            fallback_changed=bool(fallback != answer),
        )
        if fallback and fallback != answer:
            filtered_fallback, _gate_diag = _filter_template_bullets(
                fallback,
                primary_topic=request.topic,
                secondary_topics=tuple(request.secondary_topics or ()),
            )
            _trace.step(
                "polish.rejected.gate_applied",
                status="ok",
                primary_topic=request.topic,
                gate_mode=_gate_diag.get("gate_mode"),
                dropped_count=_gate_diag.get("dropped_count"),
                kept_count=_gate_diag.get("kept_count"),
            )
            answer = filtered_fallback

    # fix_v18_may §1.5 Issue E — conflict resolver (refined wiring per
    # b2.1, 2026-05-15). Detects bullets that share a normalized
    # predicate but disagree on numeric value (e.g. "30 días" vs
    # "45 días" for despido sin justa causa AÑO 1 captured at the §4.1
    # fixture). A1 resolves by matching candidate values against
    # `primary_articles` excerpts already on hand; A2 falls back to the
    # polish-grade LLM when A1 is ambiguous. Mode
    # `LIA_CONFLICT_RESOLVER_MODE` defaults `shadow` — telemetry on,
    # output unchanged — until operator promotes via the standard
    # shadow→enforce ramp.
    #
    # Wiring is POST-polish (was pre-polish in b2): polish itself
    # normalizes predicate phrasing across two differently-shaped
    # template bullets, so contradictions only converge to identical
    # predicates after rendering. Running pre-polish missed the §4.1
    # case in shadow (`no_conflicts` despite visible 30-vs-45-días
    # bullets in the served answer). See `fix_v18_may.md §7.5`.
    try:
        from .answer_conflict_resolver import resolve_answer_conflicts

        answer, _conflict_diag = resolve_answer_conflicts(
            answer or "",
            evidence=evidence,
            runtime_config_path=runtime_config_path,
        )
    except Exception:  # noqa: BLE001 — never block the pipeline on the resolver
        LOGGER.exception("conflict_resolver crashed; continuing without modification")

    if callable(on_llm_delta):
        on_llm_delta(answer)

    # v6 phase 4 — defensive per-topic citation allow-list. In enforce mode,
    # citations whose ET article number / family isn't allow-listed for the
    # current topic are treated as retrieval leakage and dropped. Default
    # mode is ``off`` so rollout is gated per-environment.
    citation_allow_mode = citation_allowlist_mode()
    _citations_in = len(evidence.citations or ())
    filtered_citations, dropped_by_allowlist = filter_citations_by_allowlist(
        evidence.citations, request.topic, citation_allow_mode
    )
    _trace.step(
        "citations.allowlist",
        status="ok",
        mode=citation_allow_mode,
        topic=request.topic,
        citations_in=_citations_in,
        citations_out=len(filtered_citations or ()),
        dropped_count=len(dropped_by_allowlist or ()),
        dropped_by_allowlist=list(dropped_by_allowlist or ())[:20],
    )
    _trace.step(
        "orchestrator.exit",
        status="ok",
        answer_mode=answer_mode,
        confidence_mode=confidence_mode,
        confidence=round(float(confidence or 0.0), 4),
        primary_articles=len(evidence.primary_articles),
        citations_emitted=len(filtered_citations or ()),
    )
    _pipeline_trace_snapshot = _trace.snapshot()
    _trace.finish(_trace_token)

    return PipelineCResponse(
        trace_id=str(request.trace_id or uuid4().hex),
        run_id=f"pd_{uuid4().hex}",
        answer_markdown=answer,
        answer_concise=answer,
        followup_queries=(
            "¿Quieres que traduzca esta ruta en una checklist operativa para el contador?",
            "¿Quieres que priorice solo cambios de vigencia o solo requisitos probatorios?",
        ),
        citations=filtered_citations,
        confidence_score=confidence,
        confidence_mode=confidence_mode,
        answer_mode=answer_mode,
        compose_quality=0.82 if evidence.primary_articles else 0.45,
        fallback_reason=fallback_reason,
        evidence_snippets=tuple(item.excerpt for item in evidence.primary_articles[:3]),
        diagnostics={
            "compatibility_mode": False,
            "pipeline_family": "pipeline_d_phase3",
            "index_file": str(index_file) if index_file is not None else None,
            "policy_path": str(policy_path) if policy_path is not None else None,
            "runtime_config_path": (
                str(runtime_config_path) if runtime_config_path is not None else None
            ),
            "planner": plan.to_dict(),
            "evidence_bundle": evidence.to_dict(),
            "retrieval_backend": backend_diagnostics.get("retrieval_backend"),
            "graph_backend": backend_diagnostics.get("graph_backend"),
            # fix_v8 §3b — surface polish outcome at the top of diagnostics
            # so the SME report's `_build_retrieval_signal_check` and the
            # probe-skill's digest can both read it without walking the trace.
            "polish_mode": _polish_mode,
            "polish_skip_reason": _polish_skip,
            "retrieval_health": retrieval_health,
            # v6 phase 1 — lift retrieval diagnostics to top-level so the A/B
            # harness and panel renderers don't have to drill into
            # evidence_bundle.diagnostics. Values source from evidence.diagnostics
            # when the retriever produced them, else None. The counts of primary
            # / connected articles fall back to len(evidence.*) so artifact-mode
            # runs (which don't populate the retriever-diag keys) still report
            # a real number instead of None.
            "primary_article_count": (
                (evidence.diagnostics or {}).get("primary_article_count")
                if (evidence.diagnostics or {}).get("primary_article_count") is not None
                else len(evidence.primary_articles)
            ),
            "connected_article_count": (
                (evidence.diagnostics or {}).get("connected_article_count")
                if (evidence.diagnostics or {}).get("connected_article_count") is not None
                else len(evidence.connected_articles)
            ),
            "related_reform_count": (
                (evidence.diagnostics or {}).get("related_reform_count")
                if (evidence.diagnostics or {}).get("related_reform_count") is not None
                else len(evidence.related_reforms)
            ),
            "seed_article_keys": (evidence.diagnostics or {}).get("seed_article_keys"),
            "planner_query_mode": (
                (evidence.diagnostics or {}).get("planner_query_mode") or plan.query_mode
            ),
            "tema_first_mode": (evidence.diagnostics or {}).get("tema_first_mode"),
            "tema_first_topic_key": (evidence.diagnostics or {}).get("tema_first_topic_key"),
            "tema_first_anchor_count": (evidence.diagnostics or {}).get(
                "tema_first_anchor_count"
            ),
            "retrieval_sub_topic_intent": (evidence.diagnostics or {}).get(
                "retrieval_sub_topic_intent"
            ),
            "subtopic_anchor_keys": (evidence.diagnostics or {}).get("subtopic_anchor_keys"),
            "reranker": reranker_diagnostics,
            "topic_safety": topic_safety_diag,
            "decomposer": decomposer_diag,
            # v23 P1 — topic-decomposition bypass diagnostics.
            **(
                _decomposition_state.get("diagnostics") or {}
            ),
            # v23 P2 — year-constants injection diagnostics.
            "fiscal_year_detected": _v23_fiscal_year,
            "year_constants_injected": bool(_v23_year_injected),
            # v23 P3 — citation source-code awareness mode.
            "citation_source_code_mode": os.getenv(
                "LIA_CITATION_SOURCE_CODE_AWARENESS", "enforce"
            ).strip().lower(),
            # v23 P5 — input-preservation + year-constant consistency mode.
            "input_preservation_mode": os.getenv(
                "LIA_POLISH_INPUT_PRESERVATION", "enforce"
            ).strip().lower(),
            # v23 P6 — Colombian-Spanish style enforcement.
            "locale_style_mode": os.getenv(
                "LIA_POLISH_LOCALE_STYLE_COLOMBIAN", "enforce"
            ).strip().lower(),
            # v23 P4 — entity-leak filter mode (shadow by default).
            "chunk_entity_filter_mode": os.getenv(
                "LIA_CHUNK_QUALITY_ENTITY_FILTER", "shadow"
            ).strip().lower(),
            # v6 phase 4 — per-topic citation allow-list drops surfaced for
            # the panel; empty list in ``off`` mode.
            "citation_allowlist_mode": citation_allow_mode,
            "dropped_by_allowlist": dropped_by_allowlist,
            # fix_v13_may §5 — dedicated práctica lane visibility. These
            # four keys let an operator confirm at trace-inspection time
            # that the `**Recomendaciones Prácticas**` section was fed by
            # real `practica_erp` chunks (backend=supabase,
            # reserved_count>=1) vs the article-derived fallback (any
            # other combination).
            "practica_backend": practica_retrieval_diag.get(
                "practica_backend"
            ),
            "practica_candidate_count": practica_retrieval_diag.get(
                "candidate_rows"
            ),
            "practica_reserved_count": len(practica_chunks),
            "practica_error_kind": practica_retrieval_diag.get(
                "practica_error_kind"
            ),
            # fix_v1.md hand-off — full deep trace of every retrieval-stage
            # decision. Survives the public-response strip via the
            # whitelist in ui_chat_payload.filter_diagnostics_for_public_response.
            "pipeline_trace": _pipeline_trace_snapshot,
        },
        llm_runtime=dict(llm_runtime_diag),
        token_usage=None,
        timing=None,
        requested_topic=request.requested_topic,
        effective_topic=request.topic,
        secondary_topics=request.secondary_topics,
        topic_adjusted=request.topic_adjusted,
        topic_notice=request.topic_notice,
        topic_adjustment_reason=request.topic_adjustment_reason,
        coverage_notice=coverage_notice,
        pipeline_variant="pipeline_d",
        pipeline_route="pipeline_d",
    )


_EMPTY_REASON_HINTS: dict[str, str] = {
    "no_explicit_article_keys_in_plan": (
        "el planner no pudo anclar articulos explicitos para esta consulta"
    ),
    "graph_not_seeded": (
        "el grafo normativo aun no esta sembrado en este entorno; hay que correr la ingesta"
    ),
    "schema_drift:retriever_expects_article_number_but_data_uses_article_key": (
        "los nodos del grafo exponen 'article_key' pero el retriever consulta 'article_number' — desalineacion de esquema"
    ),
    "no_matching_article_numbers": (
        "los anclajes del planner no existen como nodos en el grafo"
    ),
    "primary_fetch_zero_despite_canonical_matches": (
        "los nodos matchean la propiedad canonica pero el fetch principal los devuelve vacios — revisar aliasing"
    ),
    "graph_probe_failed": "el grafo no respondio la sonda de diagnostico",
    "corpus_not_seeded": (
        "el corpus Supabase aun no esta sembrado en este entorno; hay que correr el sink"
    ),
    "no_lexical_or_vector_hits": (
        "Supabase tiene chunks pero ninguno matcheo la query — revisar ranking o reformulacion"
    ),
    "chunks_probe_unknown_count": "Supabase no reporto conteo al sondeo",
    "chunks_probe_failed": "fallo la sonda de diagnostico sobre Supabase",
}


def _build_retrieval_health(
    *,
    evidence: GraphEvidenceBundle,
    backend_diagnostics: dict[str, str],
) -> dict[str, object]:
    """Flatten retriever diagnostics into a production-safe health block.

    This block is always surfaced in `response.diagnostics.retrieval_health`
    regardless of debug mode — it contains no PII and it is the only thing that
    lets operators tell schema-drift, unseeded corpus, and planner misses
    apart in partial-mode traces.
    """
    diag = dict(evidence.diagnostics or {})
    keys_of_interest = (
        "empty_reason",
        "chunks_empty_reason",
        "graph_empty_reason",
        "article_node_total",
        "article_node_matches_by_article_number",
        "article_node_matches_by_article_key",
        "seed_article_keys",
        "chunk_row_count",
        "document_row_count",
        "document_chunks_total",
        "chunks_probe_error",
        "primary_article_count",
        "connected_article_count",
        "related_reform_count",
        "graph_name",
        "planner_query_mode",
    )
    health: dict[str, object] = {
        "retrieval_backend": backend_diagnostics.get("retrieval_backend"),
        "graph_backend": backend_diagnostics.get("graph_backend"),
        "primary_article_count": len(evidence.primary_articles),
        "connected_article_count": len(evidence.connected_articles),
        "support_document_count": len(evidence.support_documents),
    }
    for key in keys_of_interest:
        if key in diag:
            health[key] = diag[key]
    empty_reason = health.get("empty_reason")
    if isinstance(empty_reason, str) and empty_reason != "ok":
        health["empty_reason_hint"] = _EMPTY_REASON_HINTS.get(
            empty_reason,
            "razon de vacio no reconocida — revisar retriever",
        )
    return health


def _compose_partial_coverage_notice(retrieval_health: dict[str, object]) -> str:
    """Coverage notice that names the real reason, not a boilerplate."""
    reason = retrieval_health.get("empty_reason")
    hint = retrieval_health.get("empty_reason_hint")
    base = (
        "La ruta graph-native no encontro articulos ancla suficientes; "
        "se devolvio la mejor evidencia parcial disponible."
    )
    if isinstance(reason, str) and isinstance(hint, str):
        return f"{base} Causa: {hint} (empty_reason={reason})."
    return base


__all__ = [
    "run_pipeline_d",
]
