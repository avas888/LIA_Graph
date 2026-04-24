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
from .answer_synthesis import build_graph_native_answer_parts
from .contracts import GraphEvidenceBundle, GraphRetrievalPlan
from .planner import build_graph_retrieval_plan
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
from .topic_safety import (
    abstention_text_for_misalignment,
    abstention_text_for_router_silent,
    detect_router_silent_failure,
    detect_topic_misalignment,
    should_promote_misalignment_to_abstention,
)


_CORPUS_SOURCE_ENV = "LIA_CORPUS_SOURCE"
_GRAPH_MODE_ENV = "LIA_GRAPH_MODE"
_VALID_CORPUS_SOURCES = {"artifacts", "supabase"}
_VALID_GRAPH_MODES = {"artifacts", "falkor_live"}


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
    return GraphEvidenceBundle(
        primary_articles=primary,
        connected_articles=connected,
        related_reforms=related,
        support_documents=chunk_evidence.support_documents,
        citations=chunk_evidence.citations,
        diagnostics=diagnostics,
    )


def _compose_graph_native_answer(
    *,
    request: PipelineCRequest,
    answer_mode: str,
    planner_query_mode: str,
    temporal_context: dict[str, object],
    evidence: GraphEvidenceBundle,
    sub_questions: tuple[str, ...] = (),
) -> str:
    answer_parts = build_graph_native_answer_parts(
        request=request,
        answer_mode=answer_mode,
        planner_query_mode=planner_query_mode,
        temporal_context=temporal_context,
        evidence=evidence,
        sub_questions=sub_questions,
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
        return answer
    if answer_mode == "graph_native_partial":
        return (
            "Usa esta salida solo como orientación inicial y confirma el expediente antes de convertirla en instrucción cerrada para el cliente."
        )
    return "Con la evidencia disponible todavía no alcanzo una recomendación operativa suficientemente confiable."


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
            "topic_safety": topic_safety,
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

    # SAFETY CHECK 1: router silent-failure.
    # If the upstream topic router returned no topic with effectively zero
    # confidence, refuse to synthesize from whatever grab-bag articles
    # fall out of general_graph_research retrieval. See topic_safety.py
    # and `docs/next/structuralwork_v1_SEENOW.md` v5.3 landed-state.
    silent_failure = detect_router_silent_failure(request)
    if silent_failure is not None:
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
        )

    decomposer_diag: dict[str, Any] = {"enabled": _decompose_enabled(), "sub_queries": []}
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

        if sub_queries:
            from ..topic_router import resolve_chat_topic as _resolve

            per_bundles: list[Any] = []
            provenance: list[dict[str, Any]] = []
            plan = None
            for sq in sub_queries:
                sq_routing = _resolve(message=sq, requested_topic=None, pais=request.pais)
                sq_request = build_sub_query_request(
                    parent_request=request,
                    sub_query=sq,
                    resolved_topic=sq_routing.effective_topic,
                    secondary_topics=sq_routing.secondary_topics,
                    topic_confidence=sq_routing.confidence,
                )
                sq_plan = build_graph_retrieval_plan(sq_request)
                sq_plan, sq_evidence, sq_backend = _retrieve_evidence(
                    sq_plan, artifacts_dir=artifacts_dir
                )
                per_bundles.append(sq_evidence)
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
            plan, evidence, backend_diagnostics = _retrieve_evidence(
                plan, artifacts_dir=artifacts_dir
            )
            decomposer_diag["fanout_count"] = 0

        evidence, reranker_diagnostics = rerank_evidence_bundle(
            query=request.message,
            evidence=evidence,
        )
    except FileNotFoundError:
        answer = (
            "Pipeline D no encontro los artifacts graph-native esperados en disco, "
            "asi que no pudo ejecutar la ruta Phase 3 todavia."
        )
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
    if should_promote_misalignment_to_abstention(request, misalignment):
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
        )

    # SAFETY CHECK 3 (v6 phase 3): evidence-topic coherence gate.
    # topic_safety short-circuits on empty primary_articles — that is the
    # exact window the Q16 biofuel contamination slipped through. The
    # coherence gate scores support_documents when primary is empty and
    # refuses when no support doc matches the router topic. Flag-gated;
    # default is ``shadow`` so the diagnostic is observed before enforced.
    coherence_gate_mode = _coherence_mode()
    coherence = detect_evidence_coherence(request, evidence, misalignment)
    if coherence_gate_mode == "enforce" and _coherence_should_refuse(
        coherence, coherence_gate_mode
    ):
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

    answer = _compose_graph_native_answer(
        request=request,
        answer_mode=answer_mode,
        planner_query_mode=plan.query_mode,
        temporal_context=plan.temporal_context.to_dict(),
        evidence=evidence,
        sub_questions=plan.sub_questions,
    )
    polished_answer, llm_runtime_diag = polish_graph_native_answer(
        request=request,
        template_answer=answer,
        evidence=evidence,
        runtime_config_path=runtime_config_path,
    )
    answer = polished_answer
    if callable(on_llm_delta):
        on_llm_delta(answer)

    return PipelineCResponse(
        trace_id=str(request.trace_id or uuid4().hex),
        run_id=f"pd_{uuid4().hex}",
        answer_markdown=answer,
        answer_concise=answer,
        followup_queries=(
            "¿Quieres que traduzca esta ruta en una checklist operativa para el contador?",
            "¿Quieres que priorice solo cambios de vigencia o solo requisitos probatorios?",
        ),
        citations=evidence.citations,
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
