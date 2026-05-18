"""fix_v25_may.md (post-P15 granularization) — legacy polish validators.

Extracted from ``answer_llm_polish.py`` when that module crossed the
1000-LOC budget set by ``feedback_granular_edits``. The validator bodies
moved here are loaded by ``POLISH_RULES`` in the parent module via
re-imports kept at the top of this file's consumers.

Public surface (re-exported by ``answer_llm_polish``):

  - ``_preserves_required_anchors``
  - ``_no_invented_norm_lineage``
  - ``_no_invented_periods``
  - ``_no_invented_uvt_ranges``
  - ``_preserves_user_numerics``
  - ``_no_inconsistent_year_constants``
  - ``filter_polished_anclaje_section``
  - ``_no_voseo``

Plus a handful of helper-only symbols (``_ANCHOR_RE`` etc.) that the
parent module still references through this sibling. The contract is
identical to the in-place implementations — no signatures changed.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from .case_bullets import CASE_REGISTRY
from .contracts import GraphEvidenceBundle


LOGGER = logging.getLogger(__name__)


# Anchor RE — also lives in answer_llm_polish for the entry-point's anchor
# preservation check. Duplicated intentionally; both spellings stay in sync
# via a unit test if drift becomes a concern.
_ANCHOR_RE = re.compile(r"\(arts?\.[^)]{0,120}\)", re.IGNORECASE)


def _preserves_required_anchors(template: str, polished: str) -> bool:
    template_anchors = _ANCHOR_RE.findall(template or "")
    if not template_anchors:
        # Nothing to preserve, polish freely.
        return True
    polished_anchors = _ANCHOR_RE.findall(polished or "")
    if not polished_anchors:
        return False
    # Require at least one anchor and that the distinct count does not
    # collapse below half of what the template carried — the LLM is free
    # to consolidate `(art. 147 ET) / (art. 147 ET)` but not erase the
    # whole set of legal references.
    distinct_template = {_normalize_anchor(a) for a in template_anchors}
    distinct_polished = {_normalize_anchor(a) for a in polished_anchors}
    if not distinct_polished:
        return False
    return len(distinct_polished & distinct_template) >= max(1, len(distinct_template) // 2)


def _normalize_anchor(anchor: str) -> str:
    return " ".join(anchor.lower().replace("(", "").replace(")", "").split())


# Matches Ley/Decreto/Resolución/Sentencia tokens with a number — the kinds
# of "outer" norm references (NOT `(art. X ET)` anchors, which are governed
# by `_preserves_required_anchors`). Number capture tolerates Sentencia
# radicado-style prefixes (`C-`, `T-`, `SU-`) and slash/dash separators.
_NORM_LINEAGE_RE = re.compile(
    r"(?ix)"
    r"\b(ley|decreto|resoluci[oó]n|sentencia)\b"
    r"\s+(?:n[°º]\s*|nro\.?\s*|del?\s+)?"
    r"\*{0,2}([CTSU]{0,2}-?\d+(?:[-/]\d+)?)\*{0,2}"
)


def _no_invented_norm_lineage(
    template: str,
    polished: str,
    evidence: "GraphEvidenceBundle | None" = None,
) -> bool:
    """Reject polish that introduces a Ley/Decreto/Resolución/Sentencia
    reference not present in the template OR in the evidence excerpts
    the polish prompt rendered.

    Comparison is on `(kind, number)` pairs and strips `**bold**` markers
    so `"Ley **1819** de 2016"` matches `"Ley 1819 de 2016"`. The year is
    intentionally NOT part of the key — the year-of-norm tag almost always
    travels with the number, and matching on number alone keeps the
    validator robust to bolding around the year. Per-year invention is
    caught by `_no_invented_periods` instead.

    fix_v21_may §3.2 P2-T1: ``evidence`` is honored when supplied. The
    LLM is explicitly invited to cite the EXCERPTS / REFORMAS block via
    the polish prompt — refs that appear in any evidence field (titles
    and excerpts across primary_articles / connected_articles /
    related_reforms / support_documents) count as grounded. This closes
    the v20-q01 over-rejection where ``Ley 50 de 1990`` and ``Ley 2466
    de 2025`` were dropped despite being primary citations on the
    labor-article answer.
    """

    def _refs(text: str) -> set[tuple[str, str]]:
        if not text:
            return set()
        cleaned = text.replace("**", "")
        return {
            (m.group(1).lower(), m.group(2))
            for m in _NORM_LINEAGE_RE.finditer(cleaned)
        }

    allowed = _refs(template) | _refs_from_evidence(evidence)
    invented = _refs(polished) - allowed
    return not invented


def _refs_from_evidence(
    evidence: "GraphEvidenceBundle | None",
) -> set[tuple[str, str]]:
    """Collect Ley/Decreto/Resolución/Sentencia refs from every evidence
    field the polish prompt renders. Mirrors ``_build_polish_prompt``'s
    iteration so the validator's "allowed" set matches what the LLM
    actually saw."""

    if evidence is None:
        return set()

    def _refs(text: str) -> set[tuple[str, str]]:
        if not text:
            return set()
        cleaned = str(text).replace("**", "")
        return {
            (m.group(1).lower(), m.group(2))
            for m in _NORM_LINEAGE_RE.finditer(cleaned)
        }

    found: set[tuple[str, str]] = set()
    for item in (
        list(getattr(evidence, "primary_articles", ()) or ())
        + list(getattr(evidence, "connected_articles", ()) or ())
        + list(getattr(evidence, "related_reforms", ()) or ())
    ):
        found |= _refs(getattr(item, "title", ""))
        found |= _refs(getattr(item, "excerpt", ""))
    for doc in getattr(evidence, "support_documents", ()) or ():
        found |= _refs(getattr(doc, "title_hint", ""))
    return found


# Years 1900-2099. Polish hallucinations mostly invent the *recent* span
# (2020-2030), but we cast wider to be conservative.
_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")


def _no_invented_periods(
    template: str,
    polished: str,
    evidence: "GraphEvidenceBundle | None" = None,
) -> bool:
    """Reject polish that introduces a 4-digit year not present in the
    template OR in the evidence excerpts the polish prompt rendered.

    Strips `**bold**` markers so `"**2025**"` matches `"2025"`. The
    template is the authoritative source for which periods the answer
    is allowed to assert. If synthesis didn't put a year in the
    template, polish must not introduce one — that's how the engine
    ends up saying "AG 2024, 2025, 2026" for a benefit that only
    applied to AG 2022 and 2023.

    fix_v21_may §3.2 P2-T1: ``evidence`` is honored when supplied. Year
    tags travel with norm references (``Ley 50 de 1990``); the polish
    prompt's REFORMAS / EXCERPTS block already carries those years, so
    accepting them from evidence aligns the validator with what the LLM
    was invited to cite. Pure year invention with no anchor — the
    behavior this guard was built for — still rejects.
    """

    def _years(text: str) -> set[str]:
        if not text:
            return set()
        cleaned = str(text).replace("**", "")
        return set(_YEAR_RE.findall(cleaned))

    allowed = _years(template) | _years_from_evidence(evidence)
    invented = _years(polished) - allowed
    return not invented


def _years_from_evidence(
    evidence: "GraphEvidenceBundle | None",
) -> set[str]:
    """Collect 4-digit years from every evidence field the polish prompt
    renders. Mirrors ``_build_polish_prompt`` field iteration."""

    if evidence is None:
        return set()
    found: set[str] = set()
    for item in (
        list(getattr(evidence, "primary_articles", ()) or ())
        + list(getattr(evidence, "connected_articles", ()) or ())
        + list(getattr(evidence, "related_reforms", ()) or ())
    ):
        for field_name in ("title", "excerpt"):
            text = getattr(item, field_name, "")
            if text:
                found |= set(_YEAR_RE.findall(str(text).replace("**", "")))
    for doc in getattr(evidence, "support_documents", ()) or ():
        text = getattr(doc, "title_hint", "")
        if text:
            found |= set(_YEAR_RE.findall(str(text).replace("**", "")))
    return found


# ---------------------------------------------------------------------------
# fix_v15_may §3 — UVT/% invention validator.
#
# Closes the gap fix_v14_may §17 surfaced: the LLM can hallucinate
# specific UVT ranges, tarifa percentages, and Grupo-1 rates inside
# polished answers and neither `_no_invented_norm_lineage` nor
# `_no_invented_periods` catches them. The validator scans tarifa-shaped
# numeric values in the polished output and rejects polish when at least
# one is NOT present (verbatim or normalized) in the template or in the
# evidence excerpts the polish prompt rendered. Cue-gated: only fires on
# answers anchored to Art. 240 / 241 / 242 / 383 / 908 ET or that mention
# a UVT-shaped tabla/tarifa — outside that context the validator is a
# noop (passes) to avoid blocking polish on plain monetary mentions.
# ---------------------------------------------------------------------------

# Percentage value: "3,5 %" / "3.5%" / "35 %" / "0,5 %". Always with %.
_UVT_PERCENTAGE_RE = re.compile(
    r"(?<![\w.,])\d{1,2}(?:[.,]\d{1,2})?\s*%",
)

# UVT-range expression: "1090 UVT", "1.090 UVT", "95 UVT".
_UVT_VALUE_RE = re.compile(
    r"(?<![\w.,])\d{1,3}(?:[.,]\d{3})*\s*UVT\b",
    re.IGNORECASE,
)

# Tarifa-context anchor: fire the validator when the polished text
# references either:
#   - a tarifa-progressive ET article from the original v15 cue list
#     (240/241/242/383/908), OR
#   - any case-anchor ET article registered in ``CASE_REGISTRY`` — every
#     playbook with concrete numerics (tasas, topes, porcentajes, UVT)
#     should be guarded against polish hallucination, OR
#   - a "tarifa especial/progresiva/marginal" / "tabla de retención"
#     phrase the LLM tends to attach invented numbers to.
#
# fix_v16 (2026-05-14): widened from the original v15 5-article list to
# include all v16 case-anchor articles after q05_pagos_efectivo fabricated
# "80% / 100.000 UVT" for Art. 771-5 (real norm: 35% / 40% / 100 UVT).
# The 771-5 cue wasn't in the v15 list so the validator was noop'd. Auto-
# derive from CASE_REGISTRY so future case-anchored topics inherit the
# guard without manual cue-list edits.
_HISTORICAL_TARIFA_CUE_ARTICLES: tuple[str, ...] = (
    "240", "241", "242", "383", "908",
)


def _build_tarifa_context_regex() -> re.Pattern[str]:
    case_anchor_articles: set[str] = set(_HISTORICAL_TARIFA_CUE_ARTICLES)
    for spec in CASE_REGISTRY:
        for anchor in spec.anchor_articles:
            article = str(anchor or "").strip()
            if article:
                case_anchor_articles.add(article)
    # Sort longest-first so multi-character article keys ("115-1", "118-1",
    # "771-5") match before their numeric prefixes ("115", "118", "771").
    sorted_articles = sorted(
        case_anchor_articles,
        key=lambda value: (-len(value), value),
    )
    article_alternation = "|".join(re.escape(a) for a in sorted_articles)
    pattern = (
        r"\b(?:art(?:[ií]culo)?\.?\s*(?:" + article_alternation + r")"
        r"|tarifa\s+(?:especial|progresiva|marginal|del?)"
        r"|tabla\s+de\s+retenci[oó]n)\b"
    )
    return re.compile(pattern, re.IGNORECASE)


_TARIFA_CONTEXT_RE = _build_tarifa_context_regex()


_UVT_VALIDATOR_ENV = "LIA_POLISH_UVT_VALIDATOR"


def _uvt_validator_mode() -> str:
    """fix_v15_may §3.6 — ``enforce | shadow | off``.

    * ``enforce`` — validator failure routes to fallback (production safety).
    * ``shadow``  — validator runs and emits a diagnostic but does NOT
                    fail the polish (calibration mode, default at landing).
    * ``off``     — validator is a noop.
    """
    raw = str(os.getenv(_UVT_VALIDATOR_ENV, "shadow") or "").strip().lower()
    if raw in {"enforce", "on", "1", "true"}:
        return "enforce"
    if raw in {"off", "0", "false", "no", "disabled"}:
        return "off"
    return "shadow"


# Trace seam — no-op when the tracer isn't loaded (e.g. unit-test harness).
try:
    from tracers_and_logs import pipeline_trace as _trace  # type: ignore
except ImportError:  # pragma: no cover - tracer always present in served runtime
    _trace = None  # type: ignore[assignment]


def _trace_step(step_name: str, *, status: str = "ok", **details: Any) -> None:
    if _trace is None:
        return
    try:
        _trace.step(step_name, status=status, **details)
    except Exception:  # noqa: BLE001 - trace failures must never break polish
        return


def _normalize_uvt_token(token: str) -> str:
    """Normalize a UVT/% match so "3,5 %", "3.5%", "3,5%" all collapse to
    the same canonical key. Strips whitespace, swaps `,` → `.` decimal
    separator, lowercases."""
    cleaned = token.strip().lower().replace(" ", "")
    # Treat `,` and `.` as interchangeable decimal separators — Spanish
    # uses comma, English uses dot, and excerpts mix the two.
    cleaned = cleaned.replace(",", ".")
    return cleaned


def _extract_uvt_tokens(text: str) -> set[str]:
    if not text:
        return set()
    cleaned = text.replace("**", "")
    out: set[str] = set()
    for m in _UVT_PERCENTAGE_RE.finditer(cleaned):
        out.add(_normalize_uvt_token(m.group(0)))
    for m in _UVT_VALUE_RE.finditer(cleaned):
        out.add(_normalize_uvt_token(m.group(0)))
    return out


def _no_invented_uvt_ranges(
    template: str,
    polished: str,
    evidence: GraphEvidenceBundle | None = None,
    question: str | None = None,
) -> bool:
    """Reject polish that introduces a specific numeric tarifa or UVT
    range value not present in the template, in the evidence excerpts
    the polish prompt rendered, OR in the user's question text.

    Cue-gated: only runs when the polished answer contains
    ``_TARIFA_CONTEXT_RE`` (Art. 240/241/242/383/908 or a tarifa/UVT
    table reference). Outside those contexts the validator is a noop.

    Behavior is env-gated via ``LIA_POLISH_UVT_VALIDATOR``:

    * ``enforce`` — returns False on at least one invented value.
    * ``shadow``  — emits a ``polish.uvt_validator.applied`` trace step
                    with ``outcome="fail_shadow"`` but still returns True.
    * ``off``     — function is a noop (always returns True).

    Question text is part of the allowed set per fix_v15_may §3.4 — when
    a user asks "exencion 350 UVT" or "deducción 50 % Art. 115 ET", a
    polished answer that echoes those values is grounded in user input,
    not invented from LLM memory. This was missed in the initial v15
    landing and surfaced as a false positive on
    ``ep_gmf_exencion_350uvt_v1`` in the first shadow-panel run.
    """
    mode = _uvt_validator_mode()
    if mode == "off":
        _trace_step(
            "polish.uvt_validator.applied",
            mode=mode,
            cue_matched=False,
            polished_value_count=0,
            allowed_value_count=0,
            invented_values=[],
            outcome="noop_off",
        )
        return True

    polished_text = polished or ""
    if _TARIFA_CONTEXT_RE.search(polished_text) is None:
        _trace_step(
            "polish.uvt_validator.applied",
            mode=mode,
            cue_matched=False,
            polished_value_count=0,
            allowed_value_count=0,
            invented_values=[],
            outcome="noop_no_cue",
        )
        return True

    allowed: set[str] = _extract_uvt_tokens(template or "")
    allowed |= _extract_uvt_tokens(question or "")

    # v23 P2 — seed allowed set from year_facts registry when a fiscal year
    # is detected. UVT 2026 (52,374) must be allowed even when not present
    # in the (stale) evidence so the year-directive's corrective effect
    # isn't validated away. Verified-only — unverified registry rows do
    # not relax the validator.
    try:
        from ..year_facts import extract_fiscal_year as _yc_extract
        from ..year_facts import get_year_facts as _yc_facts

        _detected_year = _yc_extract(question or "")
        if _detected_year is not None:
            _facts = _yc_facts(_detected_year)
            if _facts is not None:
                allowed |= _facts.allowed_tokens()
    except Exception:  # noqa: BLE001 — defensive; bad registry should not break polish
        pass

    if evidence is not None:
        for bucket in (
            evidence.primary_articles,
            evidence.connected_articles,
            evidence.related_reforms,
        ):
            for item in bucket or ():
                allowed |= _extract_uvt_tokens(item.excerpt or "")
                allowed |= _extract_uvt_tokens(item.title or "")
    # fix_v16 (2026-05-14) — also seed the allowed set from every
    # CASE_REGISTRY spec whose detector fires on the question. v16.2
    # probe surfaced a false-positive on q09_beneficio_auditoria: our
    # playbook bullet 1 carries "≥ 35 %" and "≥ 25 %", polish included
    # "35%" in its output, but the validator's `template` argument
    # didn't reflect the case-bullet content at the call site (the
    # rendered Recomendaciones Prácticas section composes lazily and
    # didn't reach this code path with the case bullets present).
    # Seeding directly from the registry guarantees that any numeric
    # value declared in a playbook's bullet text is trusted when its
    # detector fires — same source of truth the synthesis layer uses.
    if question:
        normalized_question = question.lower()
        for spec in CASE_REGISTRY:
            try:
                fires = bool(spec.detector(normalized_question))
            except Exception:  # noqa: BLE001 — defensive; bad detector shouldn't break polish
                fires = False
            if not fires:
                continue
            for bullet in spec.bullets:
                allowed |= _extract_uvt_tokens(bullet)

    polished_values = _extract_uvt_tokens(polished_text)
    invented = sorted(polished_values - allowed)

    if not invented:
        _trace_step(
            "polish.uvt_validator.applied",
            mode=mode,
            cue_matched=True,
            polished_value_count=len(polished_values),
            allowed_value_count=len(allowed),
            invented_values=[],
            outcome="pass",
        )
        return True

    capped = invented[:6]
    if mode == "shadow":
        _trace_step(
            "polish.uvt_validator.applied",
            mode=mode,
            cue_matched=True,
            polished_value_count=len(polished_values),
            allowed_value_count=len(allowed),
            invented_values=capped,
            outcome="fail_shadow",
        )
        return True

    _trace_step(
        "polish.uvt_validator.applied",
        mode=mode,
        cue_matched=True,
        polished_value_count=len(polished_values),
        allowed_value_count=len(allowed),
        invented_values=capped,
        outcome="fail_enforce",
    )
    return False


# ---------------------------------------------------------------------------
# v23 P5 — Numeric-Input Preservation (G5).
# ---------------------------------------------------------------------------


def _input_preservation_mode() -> str:
    raw = (os.getenv("LIA_POLISH_INPUT_PRESERVATION") or "enforce").strip().lower()
    return raw if raw in ("off", "shadow", "enforce") else "enforce"


_PESO_AMOUNT_RE = re.compile(
    r"\$\s*\d[\d.,]*(?:\s*(?:millones?|mill?|MM|M|mil))?",
    re.IGNORECASE,
)
_BARE_PESO_AMOUNT_RE = re.compile(
    r"\b\d{1,3}(?:[.,]\d{3}){1,}(?:\s*(?:pesos|COP))?\b",
    re.IGNORECASE,
)
_UVT_COUNT_RE = re.compile(r"\b(\d+(?:[.,]\d+)?)\s*UVT\b", re.IGNORECASE)
_PERCENT_RE = re.compile(r"\b\d+(?:[.,]\d+)?\s*%")
_SPELLED_AMOUNT_HINTS = (
    ("tres millones", ("3.000.000", "3000000", "3,000,000", "3 millones", "$3")),
    ("dos millones", ("2.000.000", "2000000", "2,000,000", "2 millones", "$2")),
    ("un millón", ("1.000.000", "1000000", "1,000,000", "1 millón", "$1")),
    ("cinco millones", ("5.000.000", "5000000", "5,000,000", "5 millones", "$5")),
    ("diez millones", ("10.000.000", "10000000", "10,000,000", "10 millones", "$10")),
)


def _normalize_amount(token: str) -> set[str]:
    """Build the equivalence set of an amount token for cross-form matching."""
    t = token.strip().replace(" ", "")
    forms = {t}
    digits = re.sub(r"[^\d]", "", t)
    if digits:
        forms.add(digits)
        if len(digits) >= 4:
            # Add dotted (Latin) and comma (US) grouping
            try:
                v = int(digits)
                forms.add(f"{v:,}".replace(",", "."))
                forms.add(f"{v:,}")
            except ValueError:
                pass
        # Short-hand M / millones
        try:
            v = int(digits)
            if v >= 1_000_000 and v % 1_000_000 == 0:
                m = v // 1_000_000
                forms.add(f"{m}M")
                forms.add(f"${m}M")
                forms.add(f"{m} millones")
                forms.add(f"{m} millón")
        except ValueError:
            pass
    return forms


def _extract_user_amounts(question: str) -> list[set[str]]:
    """Return a list of equivalence-sets, one per amount detected in the
    question. Spelled-out amounts (`tres millones`) are mapped through a
    small hint table (avoids dependency on a full Spanish numeric parser).
    """
    out: list[set[str]] = []
    q = (question or "").lower()
    for token in _PESO_AMOUNT_RE.findall(question or ""):
        out.append(_normalize_amount(token))
    for token in _BARE_PESO_AMOUNT_RE.findall(question or ""):
        out.append(_normalize_amount(token))
    for spelled, forms in _SPELLED_AMOUNT_HINTS:
        if spelled in q:
            base = set(forms)
            base.add(spelled)
            out.append(base)
    return out


def _preserves_user_numerics(
    template: str,
    polished: str,
    evidence: GraphEvidenceBundle | None = None,
    question: str | None = None,
) -> bool:
    """v23 P5 — every peso amount / UVT count / percentage the user mentioned
    must survive in the polished output (in any normalized form).

    The audit's Q10 mutated `$3.000.000` → `$2.000.000` during polish; this
    validator rejects such mutations. Cue-gated to questions that actually
    contain a numeric the user authored.
    """
    mode = _input_preservation_mode()
    if mode == "off":
        _trace_step(
            "polish.input_preservation.applied",
            mode=mode,
            outcome="noop_off",
        )
        return True
    if not question or not polished:
        _trace_step(
            "polish.input_preservation.applied",
            mode=mode,
            outcome="noop_no_input",
        )
        return True

    amount_sets = _extract_user_amounts(question)
    if not amount_sets:
        _trace_step(
            "polish.input_preservation.applied",
            mode=mode,
            outcome="noop_no_amount",
        )
        return True

    polished_lower = polished.lower()
    polished_compact = polished_lower.replace(".", "").replace(",", "").replace(" ", "")
    missing: list[list[str]] = []
    for eq in amount_sets:
        survived = False
        for form in eq:
            f = form.lower()
            if f in polished_lower:
                survived = True
                break
            f_compact = f.replace(".", "").replace(",", "").replace(" ", "")
            if f_compact and f_compact in polished_compact:
                survived = True
                break
        if not survived:
            missing.append(sorted(eq))

    if not missing:
        _trace_step(
            "polish.input_preservation.applied",
            mode=mode,
            outcome="pass",
            amounts_checked=len(amount_sets),
        )
        return True

    capped = missing[:4]
    if mode == "shadow":
        _trace_step(
            "polish.input_preservation.applied",
            mode=mode,
            outcome="fail_shadow",
            missing_amount_sets=capped,
        )
        return True
    _trace_step(
        "polish.input_preservation.applied",
        mode=mode,
        outcome="fail_enforce",
        missing_amount_sets=capped,
    )
    return False


_MULTI_YEAR_CUE_RE = re.compile(r"\bAG\s*(20\d{2})\b", re.IGNORECASE)


def _no_inconsistent_year_constants(
    template: str,
    polished: str,
    evidence: GraphEvidenceBundle | None = None,
    question: str | None = None,
) -> bool:
    """v23 P5 — when the polished answer mentions UVT (or SMLMV), it must
    NOT mix two different year constants within ±5% of each other unless an
    explicit AG-year comparison is signalled by two or more `AG 20XX`
    mentions.

    Audit Q10 had `$47.065` (2024 UVT) and `$49.799` (2025 UVT) coexisting
    in the same answer. This validator catches that pattern.
    """
    mode = _input_preservation_mode()
    if mode == "off" or not polished:
        return True
    if "UVT" not in polished:
        return True
    # Distinct UVT-shaped values in polished. Heuristic: 4-6-digit
    # currency values clearly in the COP UVT range (40,000-60,000).
    values: set[int] = set()
    for m in re.finditer(r"\$?\s*(\d{2}[.,]\d{3})\b", polished):
        try:
            v = int(m.group(1).replace(".", "").replace(",", ""))
        except ValueError:
            continue
        if 40_000 <= v <= 65_000:
            values.add(v)
    if len(values) < 2:
        return True

    years_signalled = len(set(_MULTI_YEAR_CUE_RE.findall(polished)))
    if years_signalled >= 2:
        # Explicit multi-year comparison — both UVT values are allowed.
        _trace_step(
            "polish.year_consistency.applied",
            mode=mode,
            outcome="pass_multi_year",
            distinct_uvt_values=sorted(values),
            years_signalled=years_signalled,
        )
        return True

    if mode == "shadow":
        _trace_step(
            "polish.year_consistency.applied",
            mode=mode,
            outcome="fail_shadow",
            distinct_uvt_values=sorted(values),
        )
        return True
    _trace_step(
        "polish.year_consistency.applied",
        mode=mode,
        outcome="fail_enforce",
        distinct_uvt_values=sorted(values),
    )
    return False


# ---------------------------------------------------------------------------
# v23 P6 — Colombian-Spanish style validator (G6 — voseo rejection).
# ---------------------------------------------------------------------------


def _anclaje_post_polish_filter_mode() -> str:
    """v23 P7 — post-polish Anclaje filter. Default `enforce` per beta stance."""
    raw = (os.getenv("LIA_ANCLAJE_TOPIC_GATE") or "enforce").strip().lower()
    return raw if raw in ("off", "shadow", "enforce") else "enforce"


_ANCLAJE_HEADING_RE = re.compile(
    r"(?im)^[\s*#]*\*?\*?Anclaje\s+Legal\*?\*?[\s:*]*$"
)
_NEXT_HEADING_RE = re.compile(r"(?m)^[\s*#]*\*?\*?[A-ZÁ][^*\n]{0,80}\*?\*?\s*$")
_BULLET_CITATION_RE = re.compile(
    r"\(art(?:[ií]culo?)?\.?\s*[\d-]+\s*(ET|CST|C\.Co\.|Ley\s*\d+(?:/\d+)?|Res\.?\s*DIAN[^)]*|Decreto[^)]*)\)",
    re.IGNORECASE,
)


def filter_polished_anclaje_section(polished: str) -> str:
    """v23 P7 — deterministic post-polish Anclaje filter.

    Locates the **Anclaje Legal** block in the polished markdown. For each
    bullet line, checks the cited article's source code; drops the bullet
    when its code is incompatible with the family dominant elsewhere in
    the polished answer.

    Family detection (heuristic): count `(art. N CST)` vs `(art. N ET)`
    style citations in the rest of the polished text. Whichever has more
    is the dominant family; the Anclaje keeps only bullets whose citation
    matches that family.
    """
    if _anclaje_post_polish_filter_mode() == "off" or not polished:
        return polished

    heading_match = _ANCLAJE_HEADING_RE.search(polished)
    if heading_match is None:
        return polished

    body_before = polished[: heading_match.start()]
    cst_hits = len(re.findall(r"\(art(?:[ií]culo?)?\.?\s*[\d-]+\s*CST\)", body_before, re.IGNORECASE))
    et_hits = len(re.findall(r"\(art(?:[ií]culo?)?\.?\s*[\d-]+\s*ET\)", body_before, re.IGNORECASE))
    if cst_hits == 0 and et_hits == 0:
        return polished  # No signal — leave Anclaje alone.

    dominant = "CST" if cst_hits > et_hits else "ET" if et_hits > cst_hits else None
    if dominant is None:
        return polished

    section_start = heading_match.end()
    next_heading = _NEXT_HEADING_RE.search(polished, pos=section_start)
    section_end = next_heading.start() if next_heading else len(polished)
    section = polished[section_start:section_end]

    kept_lines: list[str] = []
    for line in section.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            kept_lines.append(line)
            continue
        if not (stripped.startswith("*") or stripped.startswith("-")):
            kept_lines.append(line)
            continue
        # Bullet line — extract first citation.
        cit = _BULLET_CITATION_RE.search(line)
        if cit is None:
            # Bullet with no citation — keep.
            kept_lines.append(line)
            continue
        code = cit.group(1).strip().upper().replace(".", "").replace(" ", "")
        if dominant == "CST":
            keep = code.startswith("CST") or code.startswith("LEY")
        else:  # dominant == "ET"
            keep = code.startswith("ET") or code.startswith("LEY") or code.startswith("RES") or code.startswith("DECRETO") or code.startswith("CCO")
        if keep:
            kept_lines.append(line)
        # else: drop silently.

    new_section = "\n".join(kept_lines)
    return polished[:section_start] + new_section + polished[section_end:]


def _locale_style_mode() -> str:
    raw = (os.getenv("LIA_POLISH_LOCALE_STYLE_COLOMBIAN") or "enforce").strip().lower()
    return raw if raw in ("off", "shadow", "enforce") else "enforce"


_VOSEO_VERBS_RE = re.compile(
    r"\b("
    r"verific[aá]|ten[eé]|and[aá]|mir[aá]|decid[ií]|pens[aá]|sal[ií]|"
    r"ped[ií]|segu[ií]|eleg[ií]|escrib[ií]|habl[aá]|tom[aá]|hac[eé]|pon[eé]|"
    r"sab[eé]|comprend[eé]|recordá|controlá|pagá|cumplí|llevá|guardá|enviá"
    r")\b",
    re.IGNORECASE,
)
_VOSEO_PRONOUN_RE = re.compile(r"\bvos\b", re.IGNORECASE)


def _no_voseo(
    template: str,
    polished: str,
    evidence: GraphEvidenceBundle | None = None,
    question: str | None = None,
) -> bool:
    """v23 P6 — reject voseo Spanish in polished output. Audit's Q7 surfaced
    `"Verifica"` and `"Tene"` in production answers — voseo is regional
    Argentine/Uruguayan and reads as foreign to Colombian accountants who
    use form-`usted` in professional writing.
    """
    mode = _locale_style_mode()
    if mode == "off" or not polished:
        return True
    matches: list[str] = []
    for m in _VOSEO_VERBS_RE.finditer(polished):
        token = m.group(0)
        # Skip if the token is inside a known proper noun / legal name
        # (e.g. an article title). Conservative — these would have already
        # been preserved by anchor_preserve.
        matches.append(token)
        if len(matches) >= 6:
            break
    if _VOSEO_PRONOUN_RE.search(polished):
        matches.append("vos")
    if not matches:
        _trace_step(
            "polish.locale_style.applied",
            mode=mode,
            outcome="pass",
        )
        return True
    if mode == "shadow":
        _trace_step(
            "polish.locale_style.applied",
            mode=mode,
            outcome="fail_shadow",
            voseo_tokens=matches,
        )
        return True
    _trace_step(
        "polish.locale_style.applied",
        mode=mode,
        outcome="fail_enforce",
        voseo_tokens=matches,
    )
    return False

