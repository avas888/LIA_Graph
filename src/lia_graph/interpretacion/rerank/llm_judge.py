"""Calls Claude (via the existing `generate_llm_strict` dep) to score and
re-summarize candidates.

This module owns one concern: prompt → JSON → list[LLMScoredCandidate]. It
does not blend signals, mutate runtimes, or know about the surface. On any
error the caller gets an empty list, never an exception — fallback to
lexical-only is the runner's responsibility.
"""

from __future__ import annotations

import json
from typing import Any, Iterable

from ..policy import (
    EXPERT_RERANK_CANDIDATE_EXCERPT_CHARS,
    EXPERT_RERANK_SUMMARY_MAX_CHARS,
)
from .contracts import CandidateContext, LLMScoredCandidate
from .prompts import build_rerank_prompt, format_candidate_block


def judge_candidates(
    *,
    candidates: Iterable[CandidateContext],
    question: str,
    assistant_answer: str,
    trace_id: str,
    deps: dict[str, Any],
) -> tuple[tuple[LLMScoredCandidate, ...], dict[str, Any]]:
    """One LLM call for the whole batch. Returns scored candidates + diag.

    Diag is always populated even on failure so the runner can attach it to
    the panel's `retrieval_diagnostics` for observability.
    """
    candidate_list = [item for item in candidates if item.doc_id]
    if not candidate_list:
        return (), {"mode": "skipped", "reason": "no_candidates"}

    blocks = "\n\n".join(
        format_candidate_block(
            index=index,
            doc_id=ctx.doc_id,
            article_refs=ctx.query_refs,
            excerpt=ctx.excerpt[:EXPERT_RERANK_CANDIDATE_EXCERPT_CHARS],
        )
        for index, ctx in enumerate(candidate_list, start=1)
    )
    prompt = build_rerank_prompt(
        question=question,
        assistant_answer=assistant_answer,
        candidate_blocks=blocks,
        summary_max_chars=EXPERT_RERANK_SUMMARY_MAX_CHARS,
    )

    try:
        llm_text, llm_diag = deps["generate_llm_strict"](
            prompt,
            runtime_config_path=deps["llm_runtime_config_path"],
            trace_id=f"{trace_id}:expert-rerank",
        )
    except Exception as exc:  # noqa: BLE001 — judge must never raise to runner
        return (), {"mode": "llm_error", "reason": str(exc)}

    parsed = _parse_json_payload(str(llm_text or ""))
    if not parsed:
        return (), {"mode": "llm_unparseable", "raw_chars": len(str(llm_text or ""))}

    valid_doc_ids = {ctx.doc_id for ctx in candidate_list}
    scored = tuple(_coerce_scored(item) for item in parsed if _is_known(item, valid_doc_ids))
    scored = tuple(item for item in scored if item is not None)

    diagnostics = {
        "mode": "llm",
        "model": (llm_diag or {}).get("selected_model"),
        "token_usage": dict((llm_diag or {}).get("token_usage") or {}),
        "scored_count": len(scored),
        "candidate_count": len(candidate_list),
    }
    return scored, diagnostics


# --- internal helpers -------------------------------------------------------


def _parse_json_payload(raw: str) -> list[dict[str, Any]]:
    """Tolerant JSON extraction: strips ``` fences and accepts a single object."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")
        if first_newline != -1:
            cleaned = cleaned[first_newline + 1 :]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    if not cleaned:
        return []
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        return []
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _is_known(item: dict[str, Any], valid_doc_ids: set[str]) -> bool:
    return str(item.get("doc_id") or "").strip() in valid_doc_ids


def _coerce_scored(item: dict[str, Any]) -> LLMScoredCandidate | None:
    doc_id = str(item.get("doc_id") or "").strip()
    if not doc_id:
        return None
    raw_score = item.get("score", 0)
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        score = 0.0
    score = max(0.0, min(100.0, score))
    summary = str(item.get("summary") or "").strip()
    return LLMScoredCandidate(doc_id=doc_id, score=score, summary=summary)
