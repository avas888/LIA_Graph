"""LLM-assisted query decomposition for pipeline_d.

Structural backlog v2 item V2-2. Splits a multi-`¿…?` query into atomic
sub-queries, each of which routes + plans + retrieves independently;
the orchestrator then merges the per-sub-query evidence bundles before
handing them to synthesis.

Why this exists
---------------
Today a question like "¿cómo calculo la TTD? ¿qué pasa si el resultado
queda por debajo del 15%? ¿en qué renglón del formulario 110?" routes
as one string to one topic. The answer the user sees is grounded in the
evidence of whichever sub-intent dominated the routing — the other
sub-intents get shallow coverage at best. The alignment harness
quantifies the effect: ``body_vs_expected_alignment`` is 0.560 at the
current baseline, and most of the misses are multi-intent queries
where the accountant asked three things and got one answer well.

v1 scope
--------
- Regex-first splitter reusing ``planner._extract_user_sub_questions``.
  80% of gold M-type queries work with this alone.
- Env-gated behind ``LIA_QUERY_DECOMPOSE=off|on`` — default ``off``.
  Flip to ``on`` in ``dev:staging`` after the alignment harness shows
  a sustained ≥5pp lift on ``body_vs_expected_alignment`` with no
  regression on precision/recall of the other two harnesses.
- LLM disambiguation pass is a seam (``_llm_refine_sub_queries``)
  left stubbed; production v1 is pure regex. Adding the LLM pass in
  v2 is a matter of wiring a sidecar call + JSON-schema return.

Evidence merging
----------------
The merged ``GraphEvidenceBundle`` follows these rules:
- ``primary_articles``: union across sub-queries, deduped by ``node_key``,
  preserving the order articles were discovered (earlier sub-queries'
  hits come first).
- ``connected_articles``: union, deduped by ``node_key``, excluding
  any key that already appears in merged primary (to avoid double-cite).
- ``related_reforms``, ``support_documents``, ``citations``: union
  with dedup.
- ``diagnostics``: merged via shallow update, with a new
  ``sub_query_retrieval: [{sub_query, router_topic, primary_count,
  connected_count}]`` entry capturing per-sub-query provenance.
"""

from __future__ import annotations

import os
from typing import Any, Sequence

from ..contracts import Citation
from ..pipeline_c.contracts import PipelineCRequest
from .contracts import GraphEvidenceBundle, GraphEvidenceItem, GraphSupportDocument


VALID_MODES: frozenset[str] = frozenset({"off", "on"})
_MODE_ENV = "LIA_QUERY_DECOMPOSE"

# Queries with fewer distinct sub-questions than this stay on the
# single-query path. Decomposing a "single-¿…?" query adds no value
# and costs a routing + retrieval pass.
_MIN_SUB_QUERIES_TO_DECOMPOSE = 2

# Upper bound. A query with 10+ ¿…? is almost certainly either
# parsing noise or a question we shouldn't try to fan out in one
# turn; fall back to the single-query path with a diagnostic.
_MAX_SUB_QUERIES_SUPPORTED = 5


def is_enabled() -> bool:
    raw = str(os.getenv(_MODE_ENV, "off") or "").strip().lower()
    return raw == "on"


def current_mode() -> str:
    raw = str(os.getenv(_MODE_ENV, "off") or "").strip().lower()
    return raw if raw in VALID_MODES else "off"


def decompose_query(message: str) -> tuple[str, ...]:
    """Return atomic sub-queries (``¿…?`` each), or ``()`` for single-intent.

    Reuses the planner's existing inverted-mark splitter. Returns empty
    tuple when the query has fewer than ``_MIN_SUB_QUERIES_TO_DECOMPOSE``
    distinct sub-questions OR more than ``_MAX_SUB_QUERIES_SUPPORTED``
    (upper bound prevents pathological fan-out on noisy input).
    """
    from .planner import _extract_user_sub_questions

    sub_questions = _extract_user_sub_questions(message)
    if len(sub_questions) < _MIN_SUB_QUERIES_TO_DECOMPOSE:
        return ()
    if len(sub_questions) > _MAX_SUB_QUERIES_SUPPORTED:
        return ()
    return sub_questions


def _dedup_evidence_items(
    groups: Sequence[Sequence[GraphEvidenceItem]],
    *,
    exclude_keys: set[str] | None = None,
) -> tuple[GraphEvidenceItem, ...]:
    """Union + dedup preserving first-seen order. Optional exclusion set
    lets callers filter out keys already captured upstream (so a
    connected article doesn't show up twice after a primary match in an
    earlier sub-query).
    """
    seen: set[str] = set(exclude_keys or ())
    out: list[GraphEvidenceItem] = []
    for group in groups:
        for item in group:
            key = str(item.node_key or "").strip()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(item)
    return tuple(out)


def _dedup_support_docs(
    groups: Sequence[Sequence[GraphSupportDocument]],
) -> tuple[GraphSupportDocument, ...]:
    seen: set[str] = set()
    out: list[GraphSupportDocument] = []
    for group in groups:
        for doc in group:
            key = f"{doc.relative_path}|{doc.source_path}"
            if key in seen:
                continue
            seen.add(key)
            out.append(doc)
    return tuple(out)


def _dedup_citations(groups: Sequence[Sequence[Citation]]) -> tuple[Citation, ...]:
    seen: set[str] = set()
    out: list[Citation] = []
    for group in groups:
        for cite in group:
            key = str(getattr(cite, "doc_id", "") or getattr(cite, "relative_path", "") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(cite)
    return tuple(out)


def merge_evidence_bundles(
    bundles: Sequence[GraphEvidenceBundle],
    *,
    per_sub_query_provenance: list[dict[str, Any]] | None = None,
) -> GraphEvidenceBundle:
    """Union + dedup across per-sub-query evidence bundles.

    ``per_sub_query_provenance`` — if provided, appended under
    ``diagnostics["sub_query_retrieval"]`` so the alignment harness and
    operators can trace which sub-query produced which article.
    """
    if not bundles:
        return GraphEvidenceBundle(
            primary_articles=(),
            connected_articles=(),
            related_reforms=(),
            support_documents=(),
            citations=(),
            diagnostics={},
        )
    if len(bundles) == 1:
        return bundles[0]

    merged_primary = _dedup_evidence_items([b.primary_articles for b in bundles])
    merged_primary_keys = {str(item.node_key or "").strip() for item in merged_primary}
    merged_connected = _dedup_evidence_items(
        [b.connected_articles for b in bundles],
        exclude_keys=merged_primary_keys,
    )
    merged_reforms = _dedup_evidence_items([b.related_reforms for b in bundles])
    merged_support = _dedup_support_docs([b.support_documents for b in bundles])
    merged_cites = _dedup_citations([b.citations for b in bundles])

    merged_diag: dict[str, Any] = {}
    for b in bundles:
        merged_diag.update(dict(b.diagnostics or {}))
    if per_sub_query_provenance is not None:
        merged_diag["sub_query_retrieval"] = list(per_sub_query_provenance)
    merged_diag["decomposer_merged_bundle_counts"] = {
        "primary": len(merged_primary),
        "connected": len(merged_connected),
        "related_reforms": len(merged_reforms),
        "support_documents": len(merged_support),
        "citations": len(merged_cites),
    }

    return GraphEvidenceBundle(
        primary_articles=merged_primary,
        connected_articles=merged_connected,
        related_reforms=merged_reforms,
        support_documents=merged_support,
        citations=merged_cites,
        diagnostics=merged_diag,
    )


def build_sub_query_request(
    *,
    parent_request: PipelineCRequest,
    sub_query: str,
    resolved_topic: str | None,
    secondary_topics: tuple[str, ...],
    topic_confidence: float,
) -> PipelineCRequest:
    """Construct a per-sub-query ``PipelineCRequest`` preserving parent
    context (session_id, trace_id, operation_date) while rewriting the
    message and the routing fields.

    We replace ``message`` with the sub-query (so retrieval lexical
    signal is clean) but keep the parent's ``conversation_context`` so
    any inline article refs from previous turns still resolve.
    """
    from dataclasses import replace

    return replace(
        parent_request,
        message=sub_query,
        topic=resolved_topic,
        requested_topic=resolved_topic,
        secondary_topics=secondary_topics,
        topic_router_confidence=topic_confidence,
        topic_adjusted=False,
        topic_notice=None,
        topic_adjustment_reason=None,
    )


__all__ = [
    "VALID_MODES",
    "build_sub_query_request",
    "current_mode",
    "decompose_query",
    "is_enabled",
    "merge_evidence_bundles",
]
