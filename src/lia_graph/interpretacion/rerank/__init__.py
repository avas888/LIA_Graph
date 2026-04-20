"""Question-aware re-ranking for the expert interpretation panel.

Public surface kept narrow on purpose — the orchestrator only needs the runner
entry point and the result type. Everything else (signals, judge, composer,
applier) is an internal collaborator.
"""

from .contracts import LLMScoredCandidate, RerankResult
from .runner import rerank_runtimes

__all__ = ["LLMScoredCandidate", "RerankResult", "rerank_runtimes"]
