"""Dataclasses crossing module boundaries inside `rerank/`.

Kept separate from the modules that produce/consume them so signal modules,
the LLM judge, the composer, and the applier all import from one stable place.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..shared import InterpretationDocRuntime


@dataclass(frozen=True)
class CandidateContext:
    """Shrunken view of a runtime that the LLM judge and signals consume.

    `excerpt` is the LLM-facing slice (already clipped per policy). `query_refs`
    is the article-ref set extracted from the user's question — kept here so
    graph proximity does not have to re-parse it per candidate.
    `candidate_refs` is the article refs the candidate document itself
    references; the runner hands these to the graph signal alongside `query_refs`.
    """

    doc_id: str
    runtime: InterpretationDocRuntime
    excerpt: str
    query_refs: tuple[str, ...]
    candidate_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class LLMScoredCandidate:
    """One LLM-scored candidate. `score` is 0..100 from the judge model;
    `summary` is the per-card one-sentence rewrite that replaces the corpus
    head-slice that was causing the bunching."""

    doc_id: str
    score: float
    summary: str


@dataclass(frozen=True)
class RerankResult:
    """Returned by `rerank_runtimes`. The orchestrator uses `ordered_runtimes`
    as the new input to synthesis, then calls `applier.apply_to_surface` with
    `summaries` + `composite_scores` to override card text + group order."""

    ordered_runtimes: tuple[InterpretationDocRuntime, ...]
    summaries: dict[str, str]
    composite_scores: dict[str, float]
    diagnostics: dict[str, Any] = field(default_factory=dict)
