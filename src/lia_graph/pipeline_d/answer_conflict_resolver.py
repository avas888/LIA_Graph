"""fix_v18_may §1.5 Issue E — Conflict resolver for "same predicate,
different value" bullets.

Implements Enfoque A + A1 + A2 fallback per the 2026-05-15 brainstorm:

  * **A (Detector).** Group rendered bullets by normalized predicate
    (text before the first ``:``). Within each group, extract numeric
    values; if two bullets in the same group carry textually different
    values, flag as a conflict.
  * **A1 (Resolution by article match).** For each conflict, check
    each candidate value against the ``primary_articles`` excerpts
    already on hand in the evidence bundle (no new Falkor query). If
    exactly ONE candidate value appears verbatim (or in normalized
    form) in any excerpt, that value wins; the other bullets are
    dropped.
  * **A2 (LLM fallback).** When A1 returns no decision (both values
    match, neither matches, or no excerpts), call the polish-grade
    LLM adapter with the conflicting bullets + excerpts and ask it
    to pick which value applies today.

Modes (read from ``LIA_CONFLICT_RESOLVER_MODE``):

  * ``off`` — function returns the input unchanged.
  * ``shadow`` (default) — detect, run A1 + A2 telemetry, log the
    decision; DO NOT modify the answer markdown.
  * ``enforce`` — detect, resolve, drop the loser bullet lines from
    the markdown.

The §4.1 fixture (``Despido injustificado en AÑO 1: 30 días`` vs
``45 días``) is the canonical regression case. Art. 64 CST excerpt
contains ``30 días``; A1 should resolve in its favor.
"""

from __future__ import annotations

import logging
import os
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable

if TYPE_CHECKING:  # avoid import cycles at module-load
    from .contracts import GraphEvidenceBundle, GraphEvidenceItem


LOGGER = logging.getLogger(__name__)


_MODE_ENV_FLAG = "LIA_CONFLICT_RESOLVER_MODE"


def resolver_mode() -> str:
    """Return ``off | shadow | enforce``. Default ``shadow`` at landing."""
    raw = str(os.getenv(_MODE_ENV_FLAG, "shadow") or "").strip().lower()
    if raw in {"enforce", "on", "1", "true"}:
        return "enforce"
    if raw in {"off", "0", "false", "no", "disabled", "legacy"}:
        return "off"
    return "shadow"


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BulletAssertion:
    """A bullet line that carries a numeric value for a predicate."""

    line_index: int  # 0-based index within the source markdown lines
    raw_line: str  # the full line (with bullet marker + markdown intact)
    predicate: str  # normalized predicate (text before first ``:``)
    value_raw: str  # the numeric value as it appeared, e.g. ``45 días``
    value_norm: str  # normalized form for comparison


@dataclass(frozen=True)
class ConflictGroup:
    """A predicate with ≥ 2 bullets that disagree on the value."""

    predicate: str
    bullets: tuple[BulletAssertion, ...]


@dataclass(frozen=True)
class ConflictResolution:
    """Outcome of attempting to resolve one ConflictGroup."""

    group: ConflictGroup
    winner_line_index: int | None  # None = no decision
    loser_line_indices: tuple[int, ...]
    decision_path: str
    # one of:
    #   "a1_article_match" — A1 found exactly one value in excerpts
    #   "a2_llm_choice"    — A2 LLM picked
    #   "a1_ambiguous"     — both/neither values in excerpts; no A2 ran
    #   "a2_no_adapter"    — A1 ambiguous, A2 couldn't run (no LLM)
    #   "a2_unparseable"   — A2 ran but response unclear
    #   "a2_error"         — A2 raised
    a1_match_count: int  # how many candidate values appeared in excerpts
    a2_response_preview: str | None


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------


# Bullet line shapes we recognize. Conservative; we operate only on
# explicit bulleted lines so prose paragraphs are never touched.
_BULLET_LEAD_RE = re.compile(r"^\s*[\-\*•]\s+")


# Markdown bold around the predicate: **Foo:** value...
_MD_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")


# Numeric value patterns inside a bullet. Order matters — longer-form
# units (`días de salario`) are caught before short-form (`días`) by
# regex alternation greediness.
_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Currency: "$2.200.000" / "COP 2.200.000"
    re.compile(r"\$\s*\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?", re.IGNORECASE),
    # UVT: "350 UVT" / "1.000 UVT"
    re.compile(r"\b\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?\s*UVT\b", re.IGNORECASE),
    # SMMLV: "10 SMMLV"
    re.compile(r"\b\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?\s*SMMLV\b", re.IGNORECASE),
    # Percentage: "25 %" / "3,5%"
    re.compile(r"\b\d{1,3}(?:[.,]\d{1,2})?\s*%", re.IGNORECASE),
    # Time unit: "30 días", "12 meses", "4 años"
    re.compile(
        r"\b\d{1,4}(?:[.,]\d+)?\s*(?:d[ií]as?|meses?|a[nñ]os?)\b",
        re.IGNORECASE,
    ),
)


# Tokens to strip when normalizing predicates.
_PREDICATE_STRIP_CHARS = re.compile(r"[^\w\s]+", re.UNICODE)


def _strip_markdown_bold(text: str) -> str:
    return _MD_BOLD_RE.sub(lambda m: m.group(1), text)


def _normalize_predicate(text: str) -> str:
    """Lowercase + strip markdown + collapse whitespace + strip punctuation."""
    cleaned = _strip_markdown_bold(text).lower()
    cleaned = _PREDICATE_STRIP_CHARS.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _strip_accents(text: str) -> str:
    """Strip combining accent marks. `días` → `dias`, `año` → `ano`."""
    nfd = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")


def _normalize_value(raw: str) -> str:
    """Normalize a numeric value for comparison:
      * strip markdown bold
      * lowercase
      * strip accents (`días` ≡ `dias`, `año` ≡ `ano`)
      * unify `,` and `.` (so `3,5%` ≡ `3.5%`)
      * collapse whitespace
    """
    text = _strip_markdown_bold(raw).lower().strip()
    text = _strip_accents(text)
    text = text.replace(",", ".")
    text = re.sub(r"\s+", " ", text)
    return text


def _extract_value(bullet_text: str) -> tuple[str, str] | None:
    """Return ``(raw, normalized)`` of the FIRST numeric value found
    in the bullet body (text after the first ``:``); None if absent.
    """
    body = bullet_text.split(":", 1)[-1] if ":" in bullet_text else bullet_text
    for pattern in _VALUE_PATTERNS:
        match = pattern.search(body)
        if match:
            raw = match.group(0)
            return raw, _normalize_value(raw)
    return None


def _bullet_assertion_from_line(line: str, line_index: int) -> BulletAssertion | None:
    """Build a ``BulletAssertion`` from a markdown bullet line, or None
    if the line isn't a bullet or doesn't carry a colon-led predicate
    + numeric value.
    """
    if not _BULLET_LEAD_RE.match(line):
        return None
    body = _BULLET_LEAD_RE.sub("", line, count=1)
    if ":" not in body:
        return None
    predicate_raw, _ = body.split(":", 1)
    predicate = _normalize_predicate(predicate_raw)
    if not predicate or len(predicate.split()) < 2:
        # Predicates of 0–1 words are too generic; skip to avoid
        # false-positive collisions.
        return None
    value = _extract_value(body)
    if value is None:
        return None
    return BulletAssertion(
        line_index=line_index,
        raw_line=line,
        predicate=predicate,
        value_raw=value[0],
        value_norm=value[1],
    )


def detect_conflicts(answer_markdown: str) -> tuple[ConflictGroup, ...]:
    """Find groups of bullets that share a normalized predicate but
    carry textually different values."""
    if not answer_markdown:
        return ()
    lines = answer_markdown.splitlines()
    by_predicate: dict[str, list[BulletAssertion]] = {}
    for idx, line in enumerate(lines):
        assertion = _bullet_assertion_from_line(line, idx)
        if assertion is None:
            continue
        by_predicate.setdefault(assertion.predicate, []).append(assertion)
    groups: list[ConflictGroup] = []
    for predicate, items in by_predicate.items():
        if len(items) < 2:
            continue
        distinct_values = {item.value_norm for item in items}
        if len(distinct_values) < 2:
            continue
        groups.append(ConflictGroup(predicate=predicate, bullets=tuple(items)))
    return tuple(groups)


# ---------------------------------------------------------------------------
# A1 — article-match resolution
# ---------------------------------------------------------------------------


def _evidence_excerpt_text(primary_articles: Iterable["GraphEvidenceItem"]) -> str:
    """Concatenate title + excerpt of every primary article into a single
    normalized blob for membership testing."""
    pieces: list[str] = []
    for item in primary_articles:
        title = str(getattr(item, "title", "") or "")
        excerpt = str(getattr(item, "excerpt", "") or "")
        pieces.append(title)
        pieces.append(excerpt)
    blob = "\n".join(pieces)
    return _normalize_value(blob)


def resolve_via_a1(
    group: ConflictGroup,
    excerpts_blob_normalized: str,
) -> ConflictResolution:
    """Return a resolution where the winner is the bullet whose value
    appears in the article excerpts AND no other bullet's value does.

    Outcomes:
      * Exactly one bullet value found in excerpts → that bullet wins.
      * 0 found OR > 1 found → ``a1_ambiguous`` (caller may try A2).
    """
    distinct_values: dict[str, list[BulletAssertion]] = {}
    for bullet in group.bullets:
        distinct_values.setdefault(bullet.value_norm, []).append(bullet)
    matched_values: list[str] = []
    for value_norm in distinct_values.keys():
        if value_norm and value_norm in excerpts_blob_normalized:
            matched_values.append(value_norm)
    if len(matched_values) == 1:
        winner_value = matched_values[0]
        winner = distinct_values[winner_value][0]
        losers = tuple(
            sorted(
                {
                    b.line_index
                    for vn, blist in distinct_values.items()
                    if vn != winner_value
                    for b in blist
                }
            )
        )
        return ConflictResolution(
            group=group,
            winner_line_index=winner.line_index,
            loser_line_indices=losers,
            decision_path="a1_article_match",
            a1_match_count=1,
            a2_response_preview=None,
        )
    return ConflictResolution(
        group=group,
        winner_line_index=None,
        loser_line_indices=(),
        decision_path="a1_ambiguous",
        a1_match_count=len(matched_values),
        a2_response_preview=None,
    )


# ---------------------------------------------------------------------------
# A2 — LLM fallback
# ---------------------------------------------------------------------------


_A2_PROMPT_TEMPLATE = """Estás resolviendo una contradicción entre dos afirmaciones \
sobre la misma regla de derecho colombiano. Tu único trabajo es decidir cuál de \
las dos afirmaciones describe la regla VIGENTE HOY.

CONCEPTO: {predicate}

OPCIÓN A: {option_a}

OPCIÓN B: {option_b}

EXCERPTS DE LA NORMA (estas son las fuentes autoritativas que debés consultar):

{excerpts}

Reglas de decisión:
1. Elegí la opción cuya cifra/valor aparezca en los excerpts como la regla actual.
2. Si los excerpts muestran que una opción era válida en el pasado pero fue \
modificada o derogada, esa opción NO es la vigente.
3. Si los excerpts no permiten decidir, respondé "NINGUNA".

Respondé con UNA sola palabra: "A", "B" o "NINGUNA" (sin explicación, sin \
puntuación adicional)."""


def _build_a2_prompt(
    group: ConflictGroup,
    primary_articles: Iterable["GraphEvidenceItem"],
) -> tuple[str, BulletAssertion, BulletAssertion]:
    """Build the A2 prompt. Picks two representative bullets (one per
    distinct value). Returns ``(prompt, option_a_bullet, option_b_bullet)``."""
    seen_values: dict[str, BulletAssertion] = {}
    for bullet in group.bullets:
        seen_values.setdefault(bullet.value_norm, bullet)
    items = list(seen_values.values())
    a = items[0]
    b = items[1]
    excerpts: list[str] = []
    for art in primary_articles:
        title = str(getattr(art, "title", "") or "").strip()
        excerpt = str(getattr(art, "excerpt", "") or "").strip()
        if not excerpt and not title:
            continue
        excerpts.append(f"[{title}]\n{excerpt}".strip())
        if len(excerpts) >= 3:
            break
    excerpts_text = "\n\n".join(excerpts) if excerpts else "(sin excerpts disponibles)"
    prompt = _A2_PROMPT_TEMPLATE.format(
        predicate=group.predicate,
        option_a=a.raw_line.strip(),
        option_b=b.raw_line.strip(),
        excerpts=excerpts_text,
    )
    return prompt, a, b


def _parse_a2_response(response: str) -> str | None:
    """Return ``"A"``, ``"B"``, ``"NONE"`` (NINGUNA) or ``None`` for
    unparseable."""
    if not response:
        return None
    cleaned = response.strip().upper()
    cleaned = re.sub(r"[^A-ZÑ]", "", cleaned)
    if cleaned.startswith("NINGUNA"):
        return "NONE"
    if cleaned == "A":
        return "A"
    if cleaned == "B":
        return "B"
    # Tolerate "OPTION A" / "OPCION A" by taking the first letter from
    # the alphabet character set.
    first = cleaned[:1]
    if first in {"A", "B"}:
        return first
    return None


def resolve_via_a2(
    group: ConflictGroup,
    primary_articles: Iterable["GraphEvidenceItem"],
    adapter: Any,
) -> ConflictResolution:
    """Run the A2 LLM disambiguation. ``adapter`` must expose
    ``.generate(prompt: str) -> str``. Wraps every error as
    ``a2_error`` so the caller never crashes the pipeline."""
    prompt, option_a, option_b = _build_a2_prompt(group, primary_articles)
    try:
        response = adapter.generate(prompt)
    except Exception as exc:  # noqa: BLE001 — never crash the pipeline
        return ConflictResolution(
            group=group,
            winner_line_index=None,
            loser_line_indices=(),
            decision_path="a2_error",
            a1_match_count=0,
            a2_response_preview=str(exc)[:120],
        )
    parsed = _parse_a2_response(response)
    if parsed is None or parsed == "NONE":
        return ConflictResolution(
            group=group,
            winner_line_index=None,
            loser_line_indices=(),
            decision_path="a2_unparseable" if parsed is None else "a2_no_decision",
            a1_match_count=0,
            a2_response_preview=str(response)[:120],
        )
    winner = option_a if parsed == "A" else option_b
    losers = tuple(
        sorted({b.line_index for b in group.bullets if b.line_index != winner.line_index})
    )
    return ConflictResolution(
        group=group,
        winner_line_index=winner.line_index,
        loser_line_indices=losers,
        decision_path="a2_llm_choice",
        a1_match_count=0,
        a2_response_preview=str(response)[:120],
    )


# ---------------------------------------------------------------------------
# Apply resolutions to the markdown
# ---------------------------------------------------------------------------


def apply_resolutions(
    answer_markdown: str,
    resolutions: Iterable[ConflictResolution],
) -> str:
    """Drop the ``loser_line_indices`` from the markdown. Preserves
    blank lines and section headers; only bullet lines whose index is
    in the loser set are removed."""
    to_drop: set[int] = set()
    for res in resolutions:
        if res.winner_line_index is None:
            continue
        to_drop.update(res.loser_line_indices)
    if not to_drop:
        return answer_markdown
    lines = answer_markdown.splitlines()
    kept = [line for idx, line in enumerate(lines) if idx not in to_drop]
    # Preserve trailing newline if the input had one.
    suffix = "\n" if answer_markdown.endswith("\n") else ""
    return "\n".join(kept) + suffix


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def _trace_step(name: str, **payload: object) -> None:
    """Best-effort trace emit. Mirrors retriever/synthesis pattern."""
    try:
        from tracers_and_logs import pipeline_trace as _trace
    except Exception:  # pragma: no cover
        return
    try:
        _trace.step(name, **payload)
    except Exception:  # pragma: no cover
        LOGGER.debug("conflict_resolver trace %s failed", name, exc_info=True)


def _resolve_llm_adapter_safe(runtime_config_path: Path | None) -> Any:
    """Return an LLM adapter or None. Never raises."""
    try:
        from ..llm_runtime import DEFAULT_RUNTIME_CONFIG_PATH, resolve_llm_adapter

        cfg_path = runtime_config_path or DEFAULT_RUNTIME_CONFIG_PATH
        adapter, _resolution = resolve_llm_adapter(runtime_config_path=cfg_path)
        return adapter
    except Exception:  # noqa: BLE001
        return None


def resolve_answer_conflicts(
    answer_markdown: str,
    *,
    evidence: "GraphEvidenceBundle | None" = None,
    runtime_config_path: Path | None = None,
    adapter: Any | None = None,
) -> tuple[str, dict[str, Any]]:
    """Top-level: detect conflicts, run A1, fall back to A2, optionally
    apply resolutions.

    Returns ``(possibly_modified_markdown, diagnostics_dict)``.

    ``adapter`` is exposed for tests; production callers pass
    ``runtime_config_path`` and the function resolves the polish-grade
    adapter via the standard ``resolve_llm_adapter`` path.
    """
    mode = resolver_mode()
    diag: dict[str, Any] = {
        "mode": mode,
        "groups_detected": 0,
        "groups_resolved_a1": 0,
        "groups_resolved_a2": 0,
        "groups_unresolved": 0,
        "lines_dropped": 0,
        "decisions": [],
    }
    if mode == "off":
        _trace_step(
            "synthesis.conflict_resolver.applied",
            mode=mode,
            outcome="off",
        )
        return answer_markdown, diag
    if not answer_markdown:
        _trace_step(
            "synthesis.conflict_resolver.applied",
            mode=mode,
            outcome="noop_empty_input",
        )
        return answer_markdown, diag

    groups = detect_conflicts(answer_markdown)
    diag["groups_detected"] = len(groups)
    if not groups:
        _trace_step(
            "synthesis.conflict_resolver.applied",
            mode=mode,
            outcome="no_conflicts",
        )
        return answer_markdown, diag

    primary_articles = (
        tuple(getattr(evidence, "primary_articles", ()) or ()) if evidence else ()
    )
    excerpts_blob = _evidence_excerpt_text(primary_articles) if primary_articles else ""

    # Resolve each conflict.
    resolutions: list[ConflictResolution] = []
    adapter_obj = adapter
    for group in groups:
        a1 = resolve_via_a1(group, excerpts_blob)
        if a1.winner_line_index is not None:
            resolutions.append(a1)
            diag["groups_resolved_a1"] += 1
            diag["decisions"].append(
                {
                    "predicate": group.predicate,
                    "path": a1.decision_path,
                    "winner_line_index": a1.winner_line_index,
                    "loser_count": len(a1.loser_line_indices),
                }
            )
            continue
        # A1 ambiguous → try A2.
        if adapter_obj is None:
            adapter_obj = _resolve_llm_adapter_safe(runtime_config_path)
        if adapter_obj is None:
            no_adapter = ConflictResolution(
                group=group,
                winner_line_index=None,
                loser_line_indices=(),
                decision_path="a2_no_adapter",
                a1_match_count=a1.a1_match_count,
                a2_response_preview=None,
            )
            resolutions.append(no_adapter)
            diag["groups_unresolved"] += 1
            diag["decisions"].append(
                {
                    "predicate": group.predicate,
                    "path": "a2_no_adapter",
                    "winner_line_index": None,
                    "loser_count": 0,
                }
            )
            continue
        a2 = resolve_via_a2(group, primary_articles, adapter_obj)
        resolutions.append(a2)
        if a2.winner_line_index is not None:
            diag["groups_resolved_a2"] += 1
        else:
            diag["groups_unresolved"] += 1
        diag["decisions"].append(
            {
                "predicate": group.predicate,
                "path": a2.decision_path,
                "winner_line_index": a2.winner_line_index,
                "loser_count": len(a2.loser_line_indices),
                "a2_response_preview": a2.a2_response_preview,
            }
        )

    # Apply, only in enforce mode.
    output_markdown = answer_markdown
    if mode == "enforce":
        output_markdown = apply_resolutions(answer_markdown, resolutions)
        diag["lines_dropped"] = answer_markdown.count("\n") - output_markdown.count("\n")

    outcome: str
    if diag["groups_unresolved"] == len(groups):
        outcome = "unresolved"
    elif mode == "shadow":
        outcome = "shadow_hit"
    else:
        outcome = "applied" if diag["lines_dropped"] > 0 else "applied_no_drops"

    _trace_step(
        "synthesis.conflict_resolver.applied",
        mode=mode,
        outcome=outcome,
        groups_detected=diag["groups_detected"],
        groups_resolved_a1=diag["groups_resolved_a1"],
        groups_resolved_a2=diag["groups_resolved_a2"],
        groups_unresolved=diag["groups_unresolved"],
        lines_dropped=diag["lines_dropped"],
        decisions=diag["decisions"],
    )
    return output_markdown, diag


__all__ = [
    "BulletAssertion",
    "ConflictGroup",
    "ConflictResolution",
    "apply_resolutions",
    "detect_conflicts",
    "resolver_mode",
    "resolve_answer_conflicts",
    "resolve_via_a1",
    "resolve_via_a2",
]
