"""Deterministic substantive answer when polish was rejected.

fix_v8 §3a — when ``polish_graph_native_answer`` rejects the Gemini
output (typically ``invented_norm_lineage``, ``invented_periods``,
``anchors_stripped``, or ``empty_llm_output``), returning the bare
first-bubble question-echo template strands the user with ~120 chars of
visible content. This composer assembles a richer markdown answer from
``GraphNativeAnswerParts`` — recommendations / procedure / paperwork /
legal_anchor / precautions — so the user gets substance even when polish
is unsafe.

fix_v14_may §6 (A4) — the fallback now filters every bullet through the
A2 chunk-quality heuristics and the A1 topic-allowlist before rendering,
omits sections whose surviving tuple is empty, and emits an honest
abstention text when the surviving evidence does not reach
``_MIN_EVIDENCE_CHARS``. Mode is controlled by
``LIA_POLISH_REJECTED_FALLBACK_FILTER ∈ {clean, legacy}`` (default
``clean``). ``legacy`` preserves the v13/fix_v8 behavior for rollback.

Design properties
-----------------
* Deterministic. Same inputs → same output. No LLM call. The fallback's
  whole reason for existing is to skip the LLM surface where the
  confabulation came from in the first place.
* Sourced from ``GraphNativeAnswerParts`` which itself comes from the
  evidence bundle, so every claim is grounded.
* Inherits the existing ``filter_published_lines`` / ``take_new_lines``
  hygiene the parts already passed through during synthesis — we then
  ADD a second pass that drops chunk-artifact bullets (A2 patterns) and
  off-topic-anchor bullets (A1 allowlist) before rendering.
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
import re
from typing import Any

from ..pipeline_c.contracts import PipelineCRequest
from .answer_shared import render_bullet_section
from .answer_synthesis import GraphNativeAnswerParts
from .answer_topic_gate import _bullet_passes, _topic_entry
from .chunk_quality_heuristics import heuristic_mode, score_chunk_quality


_FALLBACK_ENV_FLAG = "LIA_POLISH_REJECTED_FALLBACK_MODE"
_FILTER_ENV_FLAG = "LIA_POLISH_REJECTED_FALLBACK_FILTER"

_MIN_EVIDENCE_CHARS = 300
_HONEST_ABSTENTION_TEXT = (
    "Tengo evidencia parcial sobre este tema pero no alcanzó para una "
    "respuesta operativa confiable. Valida el expediente manualmente o "
    "reformula la consulta con un caso más específico."
)

# Markdown markup that should NOT count toward "substantive evidence
# chars": bullet markers, bold/italic markers, headers, separators,
# whitespace. Anything else (letters, digits, punctuation, parentheses)
# counts. We strip BEFORE counting; we never strip when rendering.
_MARKDOWN_NOISE_RE = re.compile(r"[\*\#\-\_\>`]|\n|\s")


def fallback_enabled() -> bool:
    """``LIA_POLISH_REJECTED_FALLBACK_MODE=off`` reverts to the legacy
    thin-template behavior for incident rollback only."""
    raw = str(os.getenv(_FALLBACK_ENV_FLAG, "enforce") or "").strip().lower()
    return raw not in {"off", "0", "false", "no", "disabled"}


def fallback_filter_mode() -> str:
    """Return the bullet-filter mode for the polish-rejected fallback.

    Values:
      * ``clean``  — A2 chunk-quality heuristics + A1 topic-allowlist
                     filter every bullet; empty sections are omitted;
                     evidence < ``_MIN_EVIDENCE_CHARS`` triggers an
                     honest abstention text. Default at landing.
      * ``legacy`` — fix_v8 §3a behavior: render every bullet, no
                     pre-filter. Rollback path; used only when
                     ``clean`` mode regresses a turn we cannot fix.
    """
    raw = str(os.getenv(_FILTER_ENV_FLAG, "clean") or "").strip().lower()
    if raw in {"legacy", "off", "0", "false", "no", "disabled"}:
        return "legacy"
    return "clean"


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
    del polish_skip_reason  # reserved for future per-skip-reason routing

    # v25 P7 — user-numerics echo (G14). Pre-extract peso amounts / UVT
    # counts / percentages from the question so the fallback path cannot
    # silently drop the user's facts (audit Q10 surfaced COP 3,000,000 →
    # 2,000,000 mutation surviving into fallback).
    datos_block = ""
    try:
        from .user_numerics_capture import (
            echo_enabled as _un_enabled,
            extract_user_numerics as _un_extract,
            format_datos_del_caso as _un_format,
        )
        if _un_enabled():
            datos_block = _un_format(
                _un_extract(getattr(request, "message", "") if request is not None else None)
            )
    except Exception:  # noqa: BLE001 - echo must never break fallback
        datos_block = ""

    if _answer_parts_empty(answer_parts):
        if datos_block:
            return f"{datos_block}\n\n{template_answer}".strip()
        return template_answer

    filter_mode = fallback_filter_mode()
    if filter_mode == "legacy":
        legacy_out = _compose_legacy(template_answer=template_answer, answer_parts=answer_parts)
        if datos_block:
            return f"{datos_block}\n\n{legacy_out}".strip()
        return legacy_out

    topic = getattr(request, "topic", None) if request is not None else None
    routed_topic = topic.strip() if isinstance(topic, str) and topic.strip() else None
    allowed_prefixes = _topic_allowed_prefixes(routed_topic)
    heuristics_on = heuristic_mode() != "off"

    diag: dict[str, Any] = {
        "filter_mode": filter_mode,
        "routed_topic": routed_topic,
        "allowed_prefix_count": len(allowed_prefixes),
        "heuristics_on": heuristics_on,
        "sections_dropped_empty": [],
        "bullets_dropped_total": 0,
        "drop_reasons": {},
    }

    def _filter(section_name: str, bullets: tuple[str, ...]) -> tuple[str, ...]:
        kept, drop_reasons = _filter_bullets(
            bullets,
            routed_topic=routed_topic,
            allowed_prefixes=allowed_prefixes,
            heuristics_on=heuristics_on,
        )
        if drop_reasons:
            diag["bullets_dropped_total"] += sum(drop_reasons.values())
            for reason, count in drop_reasons.items():
                diag["drop_reasons"][reason] = diag["drop_reasons"].get(reason, 0) + count
        if not kept and bullets:
            diag["sections_dropped_empty"].append(section_name)
        return kept

    # Step 1+2 — filter each section's bullets; omit when filtered empty.
    recommendations = _filter("recommendations", answer_parts.recommendations)
    procedure = _filter("procedure", answer_parts.procedure)
    paperwork = _filter("paperwork", answer_parts.paperwork)
    legal_anchor = _filter("legal_anchor", answer_parts.legal_anchor)
    precautions = _filter("precautions", answer_parts.precautions)

    sections: list[str] = []
    base = (template_answer or "").strip()
    if base:
        sections.append(base)

    # v15.1 (2026-05-14): when polish is rejected on a first-bubble
    # template (which already carries Recomendaciones/Riesgos/Soportes/
    # Anclaje as a *complete* answer), naive appending here produced two
    # of every section in the GMF-4×1000 panel turn. Detect each section
    # heading inside the template and skip the append when it's already
    # there. The bare-echo case (template is just the question, no
    # sections) is unaffected — none of the headings are present, so
    # every fallback section appends as before.
    appended_sections: list[str] = []
    diag["sections_skipped_duplicate"] = []

    def _template_has_section(title: str) -> bool:
        return bool(base) and f"**{title}**" in base

    def _consider(title: str, content: str) -> None:
        if _template_has_section(title):
            diag["sections_skipped_duplicate"].append(title)
            return
        appended_sections.append(content)

    if recommendations:
        _consider(
            "Recomendaciones Prácticas",
            render_bullet_section("Recomendaciones Prácticas", recommendations),
        )
    elif procedure:
        _consider(
            "Procedimiento sugerido",
            render_bullet_section("Procedimiento sugerido", procedure),
        )
    if precautions:
        _consider(
            "Riesgos y condiciones",
            render_bullet_section("Riesgos y condiciones", precautions),
        )
    if paperwork:
        _consider(
            "Soportes clave",
            render_bullet_section("Soportes clave", paperwork),
        )
    if legal_anchor:
        _consider(
            "Anclaje legal",
            render_bullet_section("Anclaje legal", legal_anchor),
        )

    # Step 3 — measure substantive evidence chars across appended sections
    # only (the question-echo template is the QUESTION, not evidence).
    evidence_chars = sum(_count_substantive_chars(s) for s in appended_sections)
    diag["evidence_chars"] = evidence_chars
    diag["min_evidence_chars"] = _MIN_EVIDENCE_CHARS

    # v15.1 (2026-05-14): when the template is a first-bubble answer
    # (not a bare question echo), it already carries substantive content
    # under at least one canonical heading — detectable via
    # `sections_skipped_duplicate`. In that case the template IS the
    # answer; never drop to honest-abstention, and skip the
    # evidence-chars gate which would otherwise discard real content
    # whenever the leftover appendage alone is small.
    template_is_substantive = bool(diag["sections_skipped_duplicate"])
    if template_is_substantive:
        diag["outcome"] = (
            "template_already_substantive"
            if not appended_sections
            else "substantive_fallback"
        )
        diag["sections_rendered"] = len(appended_sections)
        _emit_trace(diag)
        sections.extend(appended_sections)
        combined = "\n\n".join(s for s in sections if s)
        if datos_block:
            return f"{datos_block}\n\n{combined}".strip()
        return combined

    if evidence_chars < _MIN_EVIDENCE_CHARS:
        diag["outcome"] = "honest_abstention"
        _emit_trace(diag)
        if base:
            out = f"{base}\n\n{_HONEST_ABSTENTION_TEXT}"
        else:
            out = _HONEST_ABSTENTION_TEXT
        if datos_block:
            return f"{datos_block}\n\n{out}".strip()
        return out

    diag["outcome"] = "substantive_fallback"
    diag["sections_rendered"] = len(appended_sections)
    _emit_trace(diag)
    sections.extend(appended_sections)
    combined = "\n\n".join(s for s in sections if s)
    if datos_block:
        return f"{datos_block}\n\n{combined}".strip()
    return combined


def _compose_legacy(
    *,
    template_answer: str,
    answer_parts: GraphNativeAnswerParts,
) -> str:
    """fix_v8 §3a behavior preserved verbatim for the ``legacy`` rollback."""
    sections: list[str] = []
    base = (template_answer or "").strip()
    if base:
        sections.append(base)

    if answer_parts.recommendations:
        sections.append(
            render_bullet_section("Recomendaciones Prácticas", answer_parts.recommendations)
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


def _filter_bullets(
    bullets: tuple[str, ...],
    *,
    routed_topic: str | None,
    allowed_prefixes: tuple[str, ...],
    heuristics_on: bool,
) -> tuple[tuple[str, ...], dict[str, int]]:
    """Apply A2 chunk-quality + A1 topic-allowlist filters to bullet strings.

    Returns ``(kept_bullets, drop_reason_counts)``. A bullet is dropped if
    EITHER filter rejects it; the reason recorded is the first to fire
    (chunk-quality reason wins when both fire, since chunk-artifact text
    is the more dominant signal in the v14.1 telemetry).
    """
    kept: list[str] = []
    drop_counts: dict[str, int] = {}
    for bullet in bullets:
        if not bullet or not isinstance(bullet, str):
            continue
        drop_reason = _classify_drop_reason(
            bullet,
            routed_topic=routed_topic,
            allowed_prefixes=allowed_prefixes,
            heuristics_on=heuristics_on,
        )
        if drop_reason is None:
            kept.append(bullet)
        else:
            drop_counts[drop_reason] = drop_counts.get(drop_reason, 0) + 1
    return tuple(kept), drop_counts


def _classify_drop_reason(
    bullet: str,
    *,
    routed_topic: str | None,
    allowed_prefixes: tuple[str, ...],
    heuristics_on: bool,
) -> str | None:
    """Return the drop reason string, or ``None`` if the bullet passes."""
    if heuristics_on:
        _, chunk_reason = score_chunk_quality(
            {"chunk_text": bullet},
            routed_topic=routed_topic,
        )
        if chunk_reason is not None:
            return f"chunk_quality:{chunk_reason}"
    if allowed_prefixes and not _bullet_passes(bullet, allowed_prefixes):
        return "topic_allowlist"
    return None


def _topic_allowed_prefixes(routed_topic: str | None) -> tuple[str, ...]:
    """Resolve ``allowed_prefixes`` for ``routed_topic`` from the
    `config/topic_norm_allowlist.json` catalog. Returns ``()`` when the
    topic has no curated allowlist (noop, safe-by-default — Invariant I5).
    """
    if not routed_topic:
        return ()
    entry = _topic_entry(routed_topic)
    if not isinstance(entry, dict):
        return ()
    prefixes = entry.get("allowed_prefixes") or ()
    return tuple(p for p in prefixes if isinstance(p, str) and p)


def _count_substantive_chars(text: str) -> int:
    """Count chars that contribute substantive evidence content.

    Strips markdown markup (`*`, `#`, `-`, `_`, `>`, `` ` ``), all
    whitespace, and newlines. The remainder — letters, digits,
    punctuation, parentheses — is what a reader actually parses as
    evidence. Used to decide when the fallback's appended sections are
    too thin to surface (the < 500-char honest-abstention threshold).
    """
    if not text:
        return 0
    return len(_MARKDOWN_NOISE_RE.sub("", text))


def _emit_trace(diag: dict[str, Any]) -> None:
    """Best-effort trace emission; never break the pipeline on a trace
    failure (the tracer is a context-local collector and may be absent
    in unit-test imports)."""
    try:
        from tracers_and_logs import pipeline_trace as _trace
        _trace.step(
            "polish.rejected.fallback_filter",
            status="ok",
            **diag,
        )
    except Exception:  # pragma: no cover — never break on trace failure
        pass


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


__all__ = [
    "compose_polish_rejected_fallback",
    "fallback_enabled",
    "fallback_filter_mode",
]
