"""Deterministic substantive answer when polish was rejected.

fix_v8 §3a — when ``polish_graph_native_answer`` rejects the Gemini
output (typically ``invented_norm_lineage``, ``invented_periods``,
``anchors_stripped``, or ``empty_llm_output``), returning the bare
first-bubble question-echo template strands the user with ~120 chars of
visible content. This composer assembles a richer markdown answer from
``GraphNativeAnswerParts`` — recommendations / procedure / paperwork /
legal_anchor / precautions — so the user gets substance even when polish
is unsafe.

Design properties
-----------------
* Deterministic. Same inputs → same output. No LLM call. The fallback's
  whole reason for existing is to skip the LLM surface where the
  confabulation came from in the first place.
* Sourced from ``GraphNativeAnswerParts`` which itself comes from the
  evidence bundle, so every claim is grounded.
* Inherits the existing ``filter_published_lines`` / ``take_new_lines``
  hygiene the parts already passed through during synthesis — we render
  them verbatim, not re-filter.
* Safety net: returns the input ``template_answer`` unchanged when
  ``GraphNativeAnswerParts`` is empty. The fallback can never make
  answers WORSE than today's polish-rejected behavior.

Wired into ``orchestrator.run_pipeline_d`` immediately after the
``polish.applied`` trace step when ``llm_runtime_diag["mode"] ==
"rejected"``. The orchestrator then re-runs the cross-topic gate
(``answer_topic_gate.filter_template_bullets``) on the fallback's output
so the §6.6c invariant ("off-topic norms never reach the user") holds
for both polish-success and polish-rejected paths.
"""

from __future__ import annotations

import os

from ..pipeline_c.contracts import PipelineCRequest
from .answer_shared import render_bullet_section
from .answer_synthesis import GraphNativeAnswerParts


_FALLBACK_ENV_FLAG = "LIA_POLISH_REJECTED_FALLBACK_MODE"


def fallback_enabled() -> bool:
    """``LIA_POLISH_REJECTED_FALLBACK_MODE=off`` reverts to the legacy
    thin-template behavior for incident rollback only."""
    raw = str(os.getenv(_FALLBACK_ENV_FLAG, "enforce") or "").strip().lower()
    return raw not in {"off", "0", "false", "no", "disabled"}


def compose_polish_rejected_fallback(
    *,
    request: PipelineCRequest,
    template_answer: str,
    answer_parts: GraphNativeAnswerParts,
    polish_skip_reason: str | None = None,
) -> str:
    """Render a substantive fallback from ``GraphNativeAnswerParts``.

    When polish was rejected and ``answer_parts`` carries real content,
    this composer assembles the standard first-bubble section shape from
    the same deterministic builders synthesis already used. When
    ``answer_parts`` is empty, returns ``template_answer`` unchanged
    (preserves the safety net).
    """
    del request, polish_skip_reason  # reserved for future per-skip-reason routing
    if _answer_parts_empty(answer_parts):
        return template_answer

    sections: list[str] = []
    base = (template_answer or "").strip()
    if base:
        sections.append(base)

    if answer_parts.recommendations:
        sections.append(
            render_bullet_section("Ruta sugerida", answer_parts.recommendations)
        )
    elif answer_parts.procedure:
        sections.append(
            render_bullet_section("Procedimiento sugerido", answer_parts.procedure)
        )

    if answer_parts.precautions:
        sections.append(
            render_bullet_section("Riesgos y condiciones", answer_parts.precautions)
        )

    if answer_parts.paperwork:
        sections.append(
            render_bullet_section("Soportes clave", answer_parts.paperwork)
        )

    if answer_parts.legal_anchor:
        sections.append(
            render_bullet_section("Anclaje legal", answer_parts.legal_anchor)
        )

    return "\n\n".join(s for s in sections if s)


def _answer_parts_empty(parts: GraphNativeAnswerParts) -> bool:
    return not any(
        (
            parts.recommendations,
            parts.procedure,
            parts.paperwork,
            parts.legal_anchor,
            parts.context_lines,
            parts.precautions,
            parts.opportunities,
        )
    )


__all__ = ["compose_polish_rejected_fallback", "fallback_enabled"]
