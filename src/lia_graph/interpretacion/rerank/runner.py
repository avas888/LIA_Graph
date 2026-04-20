"""Top-level rerank entry point.

Single function (`rerank_runtimes`) that the orchestrator calls. Each step
delegates to a focused module: signal collection, LLM judging, score
composition. This module's only job is sequencing and packaging the result.
"""

from __future__ import annotations

from typing import Any, Iterable

from ..policy import EXPERT_RERANK_FALLBACK_MODE, EXPERT_RERANK_TOP_N
from ..shared import InterpretationDocRuntime
from ..synthesis_helpers import extract_article_refs
from . import graph_signal, supabase_signal
from .composer import compose_scores, order_by_composite
from .contracts import CandidateContext, RerankResult
from .llm_judge import judge_candidates


def rerank_runtimes(
    *,
    runtimes: Iterable[InterpretationDocRuntime],
    question: str,
    assistant_answer: str,
    expert_query_seed: str,
    trace_id: str,
    deps: dict[str, Any],
) -> RerankResult:
    """Runs the LLM judge + graph + supabase signals over the top-N runtimes,
    blends them, and returns a reordered runtime list plus per-doc summaries
    and composite scores for the applier.

    On any unexpected failure inside collaborators, this function still
    returns a valid `RerankResult` — just one whose `summaries` is empty and
    `ordered_runtimes` matches the input order. The orchestrator never has
    to handle exceptions from rerank.
    """
    runtime_list = [runtime for runtime in runtimes if runtime is not None]
    if not runtime_list:
        return _empty_result(runtime_list, mode="skipped", reason="no_runtimes")

    head = runtime_list[:EXPERT_RERANK_TOP_N]
    tail = runtime_list[EXPERT_RERANK_TOP_N:]

    query_refs = extract_article_refs(f"{question}\n{expert_query_seed}")
    contexts = tuple(_build_context(runtime, query_refs=query_refs, deps=deps) for runtime in head)
    candidate_doc_ids = tuple(ctx.doc_id for ctx in contexts if ctx.doc_id)
    if not candidate_doc_ids:
        return _empty_result(runtime_list, mode="skipped", reason="no_doc_ids")

    scored, judge_diag = judge_candidates(
        candidates=contexts,
        question=question,
        assistant_answer=assistant_answer,
        trace_id=trace_id,
        deps=deps,
    )

    candidate_refs_by_doc = {ctx.doc_id: ctx.candidate_refs for ctx in contexts}
    graph_scores = graph_signal.score_candidates(
        query_refs=query_refs,
        candidate_refs_by_doc=candidate_refs_by_doc,
    )
    supabase_scores, supabase_diag = supabase_signal.score_candidates(
        query_text=expert_query_seed or question,
        candidate_doc_ids=candidate_doc_ids,
    )
    lexical_scores = {
        ctx.doc_id: float(getattr(ctx.runtime.doc, "retrieval_score", 0.0) or 0.0) for ctx in contexts
    }

    composite_scores = compose_scores(
        doc_ids=candidate_doc_ids,
        llm_scored=scored,
        graph_scores=graph_scores,
        supabase_scores=supabase_scores,
        lexical_scores=lexical_scores,
    )
    summaries = {item.doc_id: item.summary for item in scored if item.summary}

    if not scored:
        # LLM judge failed — preserve original order, no summaries to apply.
        return RerankResult(
            ordered_runtimes=tuple(runtime_list),
            summaries={},
            composite_scores={},
            diagnostics={
                "mode": EXPERT_RERANK_FALLBACK_MODE,
                "judge": judge_diag,
                "supabase": supabase_diag,
                "graph_scored_count": sum(1 for value in graph_scores.values() if value > 0),
            },
        )

    ordered_doc_ids = order_by_composite(doc_ids=candidate_doc_ids, composite_scores=composite_scores)
    runtime_by_doc = {ctx.doc_id: ctx.runtime for ctx in contexts}
    ordered_head = tuple(runtime_by_doc[doc_id] for doc_id in ordered_doc_ids if doc_id in runtime_by_doc)
    ordered_runtimes = ordered_head + tuple(tail)

    return RerankResult(
        ordered_runtimes=ordered_runtimes,
        summaries=summaries,
        composite_scores=composite_scores,
        diagnostics={
            "mode": "rerank",
            "judge": judge_diag,
            "supabase": supabase_diag,
            "graph_scored_count": sum(1 for value in graph_scores.values() if value > 0),
            "candidate_count": len(candidate_doc_ids),
            "summarized_count": len(summaries),
        },
    )


# --- internal helpers -------------------------------------------------------


def _build_context(
    runtime: InterpretationDocRuntime,
    *,
    query_refs: tuple[str, ...],
    deps: dict[str, Any],
) -> CandidateContext:
    """Pull the candidate's article refs and a corpus excerpt suitable for the
    LLM prompt. Re-uses the orchestrator-side `clip_session_content` so we
    inherit the same truncation behavior as other LLM call sites."""
    doc_id = str(getattr(runtime.doc, "doc_id", "") or "").strip()
    excerpt_clipper = deps.get("clip_session_content") if isinstance(deps, dict) else None
    raw_text = runtime.corpus_text or ""
    excerpt = excerpt_clipper(raw_text, max_chars=720) if callable(excerpt_clipper) else raw_text[:720]
    candidate_refs = extract_article_refs(raw_text)
    return CandidateContext(
        doc_id=doc_id,
        runtime=runtime,
        excerpt=str(excerpt or "").strip(),
        query_refs=query_refs,
        candidate_refs=candidate_refs,
    )


def _empty_result(
    runtimes: list[InterpretationDocRuntime],
    *,
    mode: str,
    reason: str,
) -> RerankResult:
    return RerankResult(
        ordered_runtimes=tuple(runtimes),
        summaries={},
        composite_scores={},
        diagnostics={"mode": mode, "reason": reason},
    )
