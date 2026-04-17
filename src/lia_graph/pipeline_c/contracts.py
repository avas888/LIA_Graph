from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from ..contracts import Citation, DocumentRecord
from ..chat_response_modes import DEFAULT_FIRST_RESPONSE_MODE, DEFAULT_RESPONSE_DEPTH


def _validate_iso_date(value: str | None) -> None:
    """Validate that an ISO-8601 YYYY-MM-DD date string parses.

    Raises ValueError when the value is non-None but unparseable. Used by
    `PipelineCRequest.__post_init__` to enforce the `consulta_date` contract.
    Accepts `None` as a no-op (the field is optional).
    """
    if value is None:
        return
    if not isinstance(value, str):
        raise ValueError(f"consulta_date must be a string or None, got {type(value).__name__}")
    stripped = value.strip()
    if not stripped:
        raise ValueError("consulta_date must be a non-empty ISO date when provided")
    try:
        date.fromisoformat(stripped[:10])
    except ValueError as exc:
        raise ValueError(
            f"consulta_date must be a valid ISO date (YYYY-MM-DD), got {value!r}"
        ) from exc


@dataclass(frozen=True)
class PipelineCRequest:
    message: str
    pais: str = "colombia"
    session_id: str | None = None
    topic: str | None = None
    requested_topic: str | None = None
    secondary_topics: tuple[str, ...] = ()
    topic_adjusted: bool = False
    topic_notice: str | None = None
    topic_adjustment_reason: str | None = None
    topic_router_confidence: float = 0.0
    operation_date: str | None = None
    trace_id: str | None = None
    chat_run_id: str | None = None
    company_context: dict[str, Any] | None = None
    primary_scope_mode: str = "global_overlay"
    response_route: str = "decision"
    retrieval_profile: str = "hybrid_rerank"
    response_depth: str = DEFAULT_RESPONSE_DEPTH
    first_response_mode: str = DEFAULT_FIRST_RESPONSE_MODE
    conversation_context: str | None = None
    conversation_state: dict[str, Any] | None = None
    debug: bool = False
    # No-login `/public` visitor flag. When True, the orchestrator caps LLM
    # output tokens via `LIA_PUBLIC_MAX_OUTPUT_TOKENS` to keep cost bounded.
    is_public_visitor: bool = False
    public_max_output_tokens: int | None = None
    # Optional caller-supplied consultation date kept for compatibility.
    # When present, downstream compatibility retrieval can use the ISO date
    # as a temporal hint. Graph-native retrieval may interpret the same hint
    # as one input among others rather than as a fixed filtering contract.
    consulta_date: str | None = None

    def __post_init__(self) -> None:
        _validate_iso_date(self.consulta_date)


@dataclass(frozen=True)
class RetrievalPlan:
    top_k: int
    cascade_mode: str
    tier_sequence: tuple[str, ...]
    reason: str
    allow_legal_depth_only: bool
    response_profile: str = "general"
    retrieval_profile: str = "hybrid_rerank"
    secondary_top_k: int = 0
    secondary_topics: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidencePack:
    docs_selected: tuple[DocumentRecord, ...]
    citations: tuple[Citation, ...]
    retrieval_diagnostics: dict[str, Any]
    confidence_score: float
    topic_attribution: dict[str, list[str]] | None = None


@dataclass(frozen=True)
class VerifierDecision:
    mode: str
    blocked: bool
    confidence_score: float
    flags: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    checks: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunTelemetry:
    run_id: str
    trace_id: str
    started_at: str
    ended_at: str | None = None
    status: str = "running"
    pipeline_variant: str = "pipeline_c"
    pipeline_route: str = "pipeline_c"
    shadow_pipeline_variant: str | None = None
    request_snapshot: dict[str, Any] = field(default_factory=dict)
    stage_timeline: tuple[dict[str, Any], ...] = ()
    summary: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PipelineCResponse:
    trace_id: str
    run_id: str
    answer_markdown: str
    answer_concise: str
    followup_queries: tuple[str, str]
    citations: tuple[Citation, ...]
    confidence_score: float
    confidence_mode: str
    answer_mode: str = "llm"
    compose_quality: float | None = None
    fallback_reason: str | None = None
    evidence_snippets: tuple[str, ...] = ()
    diagnostics: dict[str, Any] | None = None
    llm_runtime: dict[str, Any] | None = None
    token_usage: dict[str, Any] | None = None
    timing: dict[str, Any] | None = None
    requested_topic: str | None = None
    effective_topic: str | None = None
    secondary_topics: tuple[str, ...] = ()
    topic_adjusted: bool = False
    topic_notice: str | None = None
    topic_adjustment_reason: str | None = None
    coverage_notice: str | None = None
    pipeline_variant: str = "pipeline_c"
    pipeline_route: str = "pipeline_c"
    shadow_pipeline_variant: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "answer_markdown": self.answer_markdown,
            "answer_concise": self.answer_concise,
            "followup_queries": [str(item) for item in self.followup_queries],
            "citations": [c.to_public_dict() for c in self.citations],
            "confidence": {
                "score": round(float(self.confidence_score), 4),
                "mode": self.confidence_mode,
            },
            "answer_mode": self.answer_mode,
            "compose_quality": (
                round(float(self.compose_quality), 4)
                if self.compose_quality is not None
                else None
            ),
            "fallback_reason": self.fallback_reason,
            "evidence_snippets": [str(item) for item in self.evidence_snippets],
            "diagnostics": dict(self.diagnostics or {}) if self.diagnostics is not None else None,
            "llm_runtime": dict(self.llm_runtime or {}) if self.llm_runtime is not None else None,
            "token_usage": dict(self.token_usage or {}) if self.token_usage is not None else None,
            "timing": dict(self.timing or {}) if self.timing is not None else None,
            "requested_topic": str(self.requested_topic or "").strip() or None,
            "effective_topic": str(self.effective_topic or "").strip() or None,
            "secondary_topics": [str(item) for item in self.secondary_topics],
            "topic_adjusted": bool(self.topic_adjusted),
            "topic_notice": self.topic_notice,
            "topic_adjustment_reason": self.topic_adjustment_reason,
            "coverage_notice": self.coverage_notice,
        }
