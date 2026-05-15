"""LLM polish step for Pipeline D's graph-native answers.

Sits between the template-driven composer and the streaming sink: the
composer already wires inline legal anchors and picks the right sections
for the case. The polish step takes that skeleton plus retrieved evidence
and asks the LLM to rewrite the prose in senior-accountant voice while
preserving every `(art. X ET)` anchor.

Fails loudly in diagnostics, silently in output: if no adapter resolves
(no API keys, no config, timeout), the template answer is returned
unchanged so the chat never loses its safety net.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from ..llm_runtime import DEFAULT_RUNTIME_CONFIG_PATH, resolve_llm_adapter
from ..pipeline_c.contracts import PipelineCRequest
from .case_bullets import CASE_REGISTRY
from .contracts import GraphEvidenceBundle
from .presentation import format_numbers_with_bold

_POLISH_FLAG_ENV = "LIA_LLM_POLISH_ENABLED"


@dataclass(frozen=True)
class PromptRule:
    """One polish-time rule.

    - ``post_apply``: transformer run after the LLM (or on the template
      when polish was skipped). Enforces the rule deterministically.
    - ``validate``: predicate ``(template, polished) -> bool`` that
      rejects an LLM output when it violated the rule — caller falls
      back to the template. Used for invariants like "every anchor that
      was in the draft is still in the polished version."
    - ``rejection_reason``: short diagnostic label surfaced in the
      polish ``skip_reason`` when ``validate`` returns False. Falls
      back to ``f"rule_violated:{id}"`` if not set.
    """

    id: str
    category: str  # "structural" | "semantic" | "presentational" | "tonal"
    prompt_text: str
    post_apply: Callable[[str], str] | None = None
    # fix_v15_may §3.5 — validators may optionally read the evidence
    # bundle the polish prompt rendered. Existing validators ignore the
    # third arg; `_no_invented_uvt_ranges` uses it to build its allowed
    # set from real excerpts.
    validate: Callable[..., bool] | None = None
    rejection_reason: str | None = None
    surfaces: tuple[str, ...] = field(default=("main_chat",))


POLISH_RULES: tuple[PromptRule, ...] = (
    PromptRule(
        id="anchor_preserve",
        category="semantic",
        prompt_text=(
            "Preservá TODAS las referencias inline al Estatuto Tributario con la forma "
            "(art. X ET) o (arts. X y Y ET). No inventés nuevas; no borrés las existentes."
        ),
        validate=lambda template, polished: _preserves_required_anchors(template, polished),
        rejection_reason="anchors_stripped",
    ),
    PromptRule(
        id="no_disclaimers",
        category="tonal",
        prompt_text=(
            "No agregues saludos, disclaimers, ni frases como \"espero que esto ayude\"."
        ),
    ),
    PromptRule(
        id="section_structure",
        category="structural",
        prompt_text=(
            "Aplicá el orden obligatorio de la DIRECTIVA PRIMARIA punto 0. Si el borrador difiere, reordená. "
            "NO elimines secciones. Podés reformular cada bullet existente. "
            "REGLA DE EXPANSIÓN: si CUALQUIER sección tiene un solo bullet (o un bullet muy corto, tipo encabezado de "
            "una guía práctica) Y hay al menos 2 ARTÍCULOS ANCLA o 3 DOCUMENTOS DE SOPORTE en la evidencia abajo, "
            "AMPLIÁ esa sección a 2-3 bullets adicionales construidos desde la evidencia. Preservá el bullet original "
            "y TODAS las referencias inline al ET. No inventés normas, artículos, ni cifras que no estén en la "
            "evidencia abajo o en el borrador. Si la evidencia no alcanza para 2-3 bullets reales, dejá el bullet "
            "original solo — preferible una sección breve verdadera que una expandida con relleno."
        ),
    ),
    PromptRule(
        id="markdown_table_preserve",
        category="structural",
        prompt_text=(
            "Si el borrador contiene una tabla markdown (líneas que empiezan con `|` y la línea separadora `|---|...`), "
            "preservala letra por letra. No la reformules en prosa, no fusiones celdas, no agregues ni elimines filas o columnas. "
            "El comparativo en tabla es la forma exacta en la que el contador necesita ver pre/post; reflowarlo destruye la "
            "información estructural."
        ),
    ),
    PromptRule(
        id="direct_answers_preserve",
        category="structural",
        prompt_text=(
            "Si el borrador trae una sección \"Respuestas directas\", conservá cada sub-pregunta como un bullet en negrita "
            "con sus bullets hijos intactos; no fusiones sub-preguntas ni muevas respuestas entre ellas. Si un sub-bloque "
            "dice \"Cobertura pendiente para esta sub-pregunta\", mantené esa advertencia explícita para esa pregunta."
        ),
    ),
    PromptRule(
        id="anclaje_legal_explanatory_lines",
        category="structural",
        prompt_text=(
            "EN EL BLOQUE **Anclaje Legal**: cada viñeta debe quedar como una oración "
            "completa que explique POR QUÉ se cita ese artículo. Formas aceptables: "
            "`Art. N ET — <qué regula el artículo>.` (preservando el encabezado del "
            "BORRADOR) o en prosa `<Qué regula el artículo> en el (art. N ET).` "
            "(por ej.: `La definición de salario se encuentra en los (arts. 127-132 ET).`). "
            "NUNCA dejes una viñeta como sólo `(art. N ET)` ni como sólo `Art. N ET` sin "
            "descripción al lado — la sección entera deja de tener sentido. Tomá la "
            "descripción del encabezado del artículo en ARTÍCULOS ANCLA DEL GRAFO o del "
            "EXCERPT; no inventes contenido fuera de la evidencia. Si el BORRADOR ya "
            "trae el encabezado en cada viñeta (`Art. N ET — <heading>.`), preservalo "
            "o reescribilo en prosa, pero no lo borres."
        ),
    ),
    PromptRule(
        id="partial_coverage_warning_preserve",
        category="semantic",
        prompt_text=(
            "Si el borrador dice \"la cobertura quedó parcial\", mantené esa advertencia."
        ),
    ),
    PromptRule(
        id="no_invented_numbers",
        category="semantic",
        prompt_text=(
            "No inventes cifras, topes, porcentajes ni artículos que no estén en el borrador o en la evidencia abajo."
        ),
    ),
    PromptRule(
        id="numeric_format_bold",
        category="presentational",
        prompt_text=(
            "FORMATO NUMÉRICO: cualquier valor cuantitativo del borrador va en DÍGITOS, nunca deletreado, "
            "y envuelto en negrita Markdown — los números deben saltar a la vista del contador. Aplica a "
            "conteos (\"**12** períodos\" no \"doce períodos\"), plazos (\"**6** años\" no \"seis años\"), "
            "porcentajes (**25%**), montos en pesos (**$1.000.000**), años (**2025**) y ordinales numéricos. "
            "EXCEPCIÓN ESTRICTA: NO modifiqués ni envolvás en negrita los números dentro de referencias "
            "legales inline — `(art. 147 ET)`, `(arts. 147 y 290 ET)`, `(Decreto 624 de 1989)`, "
            "`(Ley 1819 de 2016)`, `(numeral 3 del art. 26 ET)` se preservan letra por letra como están en "
            "el borrador. La negrita aplica a la cifra en prosa, no a la cita normativa."
        ),
        post_apply=format_numbers_with_bold,
        surfaces=("main_chat", "normativa"),
    ),
    PromptRule(
        id="no_invented_article_descriptions",
        category="semantic",
        prompt_text=(
            "No inventés descripciones cortas para los artículos citados (e.g., 'Art. 290 ET: Régimen de transición para X'). "
            "Los artículos del ET tienen múltiples numerales con temas distintos; describir el artículo entero con una frase desde "
            "tu memoria casi siempre se equivoca de numeral. Si necesitás caracterizar un artículo en una línea, usá literalmente "
            "el encabezado del artículo tal como aparece en ARTÍCULOS ANCLA DEL GRAFO, o citá el numeral específico que aplica "
            "según el borrador. Cuando dudés, dejá la cita sola — `(art. 290 ET)` sin descripción es preferible a una descripción inventada."
        ),
    ),
    PromptRule(
        id="no_invented_norm_lineage",
        category="semantic",
        prompt_text=(
            "No introduzcas referencias a leyes, decretos, resoluciones o sentencias "
            "(p. ej., 'Ley 1819 de 2016', 'Decreto 624 de 1989', 'Sentencia C-606 de 1997') "
            "que no aparezcan literalmente en el borrador. NUNCA inventes la genealogía "
            "normativa: si el borrador no afirma 'la Ley X modificó el artículo Y', vos "
            "tampoco lo afirmes — no traigas esa relación desde tu memoria. Cuando dudés, "
            "omití la cita histórica. El contador prefiere una respuesta breve y exacta "
            "a una extensa con genealogía inventada."
        ),
        validate=lambda template, polished: _no_invented_norm_lineage(template, polished),
        rejection_reason="invented_norm_lineage",
    ),
    PromptRule(
        id="no_invented_periods",
        category="semantic",
        prompt_text=(
            "No introduzcas años, períodos gravables, ni rangos temporales (p. ej., "
            "'AG 2024', '2022 y 2023', 'para los años 2025-2026') que no aparezcan "
            "literalmente en el borrador. Si el borrador no menciona un año específico, "
            "no lo agregues. Inventar un período es uno de los peores errores que puede "
            "cometer la respuesta: el contador podría aplicar la regla en un año en que "
            "no aplica."
        ),
        validate=lambda template, polished: _no_invented_periods(template, polished),
        rejection_reason="invented_periods",
    ),
    PromptRule(
        # fix_v15_may §3 — UVT/% invention validator. Closes the gap
        # fix_v14_may §17 surfaced (LLM cited "3,5 %" for Art. 908 ET
        # Grupo 1; not in the article). Cue-gated to tarifa-anchored
        # articles + UVT references; env-gated via
        # `LIA_POLISH_UVT_VALIDATOR` (`shadow` default at landing).
        id="no_invented_uvt_ranges",
        category="semantic",
        prompt_text=(
            "No inventés porcentajes ni rangos UVT específicos para artículos con "
            "tarifa (Art. 240 / 241 / 242 / 383 / 908 ET). Si la cifra exacta no "
            "está en el BORRADOR o en los EXCERPTS, no la nombres."
        ),
        validate=lambda template, polished, evidence=None, question=None: _no_invented_uvt_ranges(
            template, polished, evidence, question
        ),
        rejection_reason="invented_uvt_ranges",
    ),
    PromptRule(
        id="neutral_spanish",
        category="tonal",
        prompt_text="Respondé en español neutro profesional, sin muletillas.",
    ),
)


def _rules_block(surface: str = "main_chat") -> str:
    bullets = [f"- {rule.prompt_text}" for rule in POLISH_RULES if surface in rule.surfaces]
    return "REGLAS INVIOLABLES:\n" + "\n".join(bullets)


def _apply_post_hoc_transformers(text: str, *, surface: str = "main_chat") -> str:
    """Run every rule's ``post_apply`` over ``text`` in registry order.

    Called whether the LLM polished successfully OR the template fell
    through unchanged — presentational invariants like numeric bolding
    must hold deterministically, not on LLM cooperation.
    """
    for rule in POLISH_RULES:
        if rule.post_apply is None or surface not in rule.surfaces:
            continue
        text = rule.post_apply(text)
    return text


def _validate_against_rules(
    template: str,
    polished: str,
    *,
    surface: str = "main_chat",
    evidence: GraphEvidenceBundle | None = None,
    question: str | None = None,
) -> tuple[bool, str | None]:
    """Run every rule's ``validate`` predicate. Returns ``(ok, reason)``.

    ``ok`` is False if any rule rejected the polished text. ``reason``
    is the failed rule's ``rejection_reason`` (or a generic
    ``rule_violated:<id>`` if the rule didn't declare one).

    fix_v15_may §3.5 — validators may opt into reading the evidence
    bundle the polish prompt rendered AND the user's question text.
    The dispatcher tries the widest signature
    ``(template, polished, evidence, question)`` first and falls back
    to narrower signatures so existing 2-arg lambdas keep functioning
    unchanged.
    """
    for rule in POLISH_RULES:
        if rule.validate is None or surface not in rule.surfaces:
            continue
        ok = _invoke_validator(rule.validate, template, polished, evidence, question)
        if not ok:
            return False, rule.rejection_reason or f"rule_violated:{rule.id}"
    return True, None


def _invoke_validator(
    fn: Callable[..., bool],
    template: str,
    polished: str,
    evidence: GraphEvidenceBundle | None,
    question: str | None,
) -> bool:
    """Try the widest validator signature first, narrow on TypeError.

    Order: ``(t, p, ev, q)`` → ``(t, p, ev)`` → ``(t, p)``. Existing
    norm-lineage / period validators take the 2-arg form; the v15 UVT
    validator takes the 4-arg form.
    """
    for args in (
        (template, polished, evidence, question),
        (template, polished, evidence),
        (template, polished),
    ):
        try:
            return fn(*args)
        except TypeError:
            continue
    return fn(template, polished)


def _polish_enabled() -> bool:
    """Polish is opt-in so tests and offline dev stay deterministic.

    Set `LIA_LLM_POLISH_ENABLED=1` (or `true`/`yes`/`on`) in the env that
    runs the server — typically via the dev launcher or Railway config.
    Unset / `0` / empty / anything else keeps polish disabled and the
    template answer is returned as-is.
    """
    raw = str(os.getenv(_POLISH_FLAG_ENV, "") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


# The anchor pattern the first-bubble composer emits. If any expected
# anchor is absent from the polished text, we fall back — the LLM is not
# allowed to strip legal references the retriever worked for.
_ANCHOR_RE = re.compile(r"\(arts?\.[^)]{0,120}\)", re.IGNORECASE)


def polish_graph_native_answer(
    *,
    request: PipelineCRequest,
    template_answer: str,
    evidence: GraphEvidenceBundle,
    runtime_config_path: object | None = None,
) -> tuple[str, dict[str, Any]]:
    """Return `(answer, llm_runtime_diagnostics)`.

    Never raises. On any failure — no adapter, no API key, transport
    error, anchors stripped by the model — returns the template answer
    unchanged and a diagnostics block explaining why.
    """
    base_diag: dict[str, Any] = {
        "selected_provider": None,
        "selected_type": None,
        "selected_transport": None,
        "adapter_class": None,
        "model": None,
        "runtime_config_path": str(runtime_config_path) if runtime_config_path else None,
        "mode": "skipped",
        "skip_reason": None,
        "attempts": [],
    }
    if not template_answer or not template_answer.strip():
        base_diag["skip_reason"] = "empty_template"
        return _apply_post_hoc_transformers(template_answer), base_diag

    if not _polish_enabled():
        base_diag["skip_reason"] = "polish_disabled_by_env"
        return _apply_post_hoc_transformers(template_answer), base_diag

    config_path = _resolve_config_path(runtime_config_path)
    try:
        adapter, resolution = resolve_llm_adapter(runtime_config_path=config_path)
    except Exception as exc:  # noqa: BLE001 - polish must never raise
        base_diag["skip_reason"] = f"resolver_error:{type(exc).__name__}"
        return _apply_post_hoc_transformers(template_answer), base_diag

    if adapter is None:
        base_diag["skip_reason"] = "no_adapter_available"
        base_diag["fallback_skipped"] = resolution.get("fallback_skipped", []) if isinstance(resolution, dict) else []
        return _apply_post_hoc_transformers(template_answer), base_diag

    prompt = _build_polish_prompt(
        request=request,
        template_answer=template_answer,
        evidence=evidence,
    )
    try:
        polished = adapter.generate(prompt).strip()
    except Exception as exc:  # noqa: BLE001 - adapter failures are diagnostic data
        base_diag.update(_runtime_diag_from_resolution(resolution))
        base_diag["mode"] = "failed"
        base_diag["skip_reason"] = f"adapter_error:{type(exc).__name__}"
        # Truncated message is safe — HTTP bodies from upstream APIs often
        # contain the true cause (model name wrong, quota, auth). Clip so we
        # never leak long secrets or blow up the diagnostic blob.
        message = str(exc).strip()
        if message:
            base_diag["error_message"] = message[:400]
        return _apply_post_hoc_transformers(template_answer), base_diag

    if not polished:
        base_diag.update(_runtime_diag_from_resolution(resolution))
        base_diag["mode"] = "failed"
        base_diag["skip_reason"] = "empty_llm_output"
        return _apply_post_hoc_transformers(template_answer), base_diag

    ok, reason = _validate_against_rules(
        template_answer,
        polished,
        evidence=evidence,
        question=request.message if request else None,
    )
    if not ok:
        base_diag.update(_runtime_diag_from_resolution(resolution))
        base_diag["mode"] = "rejected"
        base_diag["skip_reason"] = reason
        return _apply_post_hoc_transformers(template_answer), base_diag

    base_diag.update(_runtime_diag_from_resolution(resolution))
    base_diag["mode"] = "llm"
    base_diag["skip_reason"] = None
    return _apply_post_hoc_transformers(polished), base_diag


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _resolve_config_path(path_like: object | None) -> Path:
    if path_like is None:
        return DEFAULT_RUNTIME_CONFIG_PATH
    if isinstance(path_like, Path):
        return path_like
    return Path(str(path_like))


def _runtime_diag_from_resolution(resolution: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(resolution, dict):
        return {}
    keep = (
        "selected_provider",
        "selected_type",
        "selected_transport",
        "adapter_class",
        "model",
        "strategy",
        "resolution_mode",
        "runtime_config_path",
    )
    return {k: resolution[k] for k in keep if k in resolution}


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


def _no_invented_norm_lineage(template: str, polished: str) -> bool:
    """Reject polish that introduces a Ley/Decreto/Resolución/Sentencia
    reference not present in the template.

    Comparison is on `(kind, number)` pairs and strips `**bold**` markers
    so `"Ley **1819** de 2016"` matches `"Ley 1819 de 2016"`. The year is
    intentionally NOT part of the key — the year-of-norm tag almost always
    travels with the number, and matching on number alone keeps the
    validator robust to bolding around the year. Per-year invention is
    caught by `_no_invented_periods` instead.
    """

    def _refs(text: str) -> set[tuple[str, str]]:
        if not text:
            return set()
        cleaned = text.replace("**", "")
        return {
            (m.group(1).lower(), m.group(2))
            for m in _NORM_LINEAGE_RE.finditer(cleaned)
        }

    invented = _refs(polished) - _refs(template)
    return not invented


# Years 1900-2099. Polish hallucinations mostly invent the *recent* span
# (2020-2030), but we cast wider to be conservative.
_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")


def _no_invented_periods(template: str, polished: str) -> bool:
    """Reject polish that introduces a 4-digit year not present in the
    template.

    Strips `**bold**` markers so `"**2025**"` matches `"2025"`. The
    template is the authoritative source for which periods the answer
    is allowed to assert. If synthesis didn't put a year in the
    template, polish must not introduce one — that's how the engine
    ends up saying "AG 2024, 2025, 2026" for a benefit that only
    applied to AG 2022 and 2023.
    """

    def _years(text: str) -> set[str]:
        if not text:
            return set()
        cleaned = text.replace("**", "")
        return set(_YEAR_RE.findall(cleaned))

    invented = _years(polished) - _years(template)
    return not invented


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


# fix_v14_may §5 + §16 (A3) — DIRECTIVA NUMÉRICA.
#
# REVERTED 2026-05-13 per fix_v14_may §17 (judge panel result):
#   * 42-turn judge measured strict pass 38.1 % → 26.2 % (−11.9 pp).
#   * Five class regressions (4 × ACCEPTABLE→BORDERLINE, 1 × STRONG→BORDERLINE).
#   * One HARD HALLUCINATION introduced (pr_rst_anticipo_bimestral):
#     A3 fired on Art. 908 cue, LLM gave "3.5 %" tarifa for Grupo 1
#     which does not exist in the article (real rates 1.2/2.8/4.4/5.4 %).
#     Polish validators don't catch invented UVT/% — only invented years.
#   * Operator-amended decision rule says new hallucination is hard fail.
#
# Helper code retained behind kill switch for future A/B against the
# validator-based approach planned in fix_v15_may.md. Default OFF.
# Re-enable for diagnostic A/B only via
# `LIA_POLISH_NUMERIC_DIRECTIVE=on` AND only after the
# `_no_invented_uvt_ranges` validator from fix_v15 lands and catches
# the failure mode A3 introduces structurally.
_NUMERIC_MONEY_RE = re.compile(
    r"(?:\$\s*\d|\d[\d.,]*\s*(?:millones?|m\b|MM\b|UVT))",
    re.IGNORECASE,
)
_NUMERIC_PERCENTAGE_RE = re.compile(r"\d+(?:[.,]\d+)?\s*%")
_NUMERIC_CONTEXT_RE = re.compile(
    r"\b(?:salario|ingresos?|antig[uü]edad|honorarios|patrimonio|utilidad|"
    r"dividendos?|aportes?|comisi[oó]n)\b.{0,40}\d",
    re.IGNORECASE,
)
_TARIFA_PROGRESSIVE_ARTICLES = (
    re.compile(r"\bart(?:[ií]culo?)?\.?\s*242\b", re.IGNORECASE),   # dividendos
    re.compile(r"\bart(?:[ií]culo?)?\.?\s*383\b", re.IGNORECASE),   # retención laboral
    re.compile(r"\bart(?:[ií]culo?)?\.?\s*908\b", re.IGNORECASE),   # RST tarifas
    re.compile(r"\bart(?:[ií]culo?)?\.?\s*241\b", re.IGNORECASE),   # tabla renta natural
)
_NIT_BY_DIGIT_RE = re.compile(
    r"NIT(?:\s+(?:terminado|acabado))?\s+(?:en|que\s+termina\s+en)\s+\d",
    re.IGNORECASE,
)


_NUMERIC_DIRECTIVE_ENV = "LIA_POLISH_NUMERIC_DIRECTIVE"


def _numeric_directive_enabled() -> bool:
    """Kill switch for the A3 DIRECTIVA NUMÉRICA. Default OFF after the
    2026-05-13 judge panel showed A3 introduces invented UVT/% values
    that the polish validators don't catch (fix_v14_may §17). Re-enable
    only for diagnostic A/B once a `_no_invented_uvt_ranges` validator
    lands per fix_v15_may.md."""
    raw = str(os.getenv(_NUMERIC_DIRECTIVE_ENV, "off") or "").strip().lower()
    return raw in {"on", "1", "true", "yes", "enforce"}


def _build_numeric_directive(question_text: str) -> str:
    """Return the DIRECTIVA NUMÉRICA block to splice into the primary
    directive, or empty string when (a) the kill switch is OFF (default
    after fix_v14_may §17 revert), or (b) no numeric cue is present in
    the question.
    """
    if not _numeric_directive_enabled():
        return ""
    if not question_text:
        return ""
    cues: list[str] = []
    if _NUMERIC_MONEY_RE.search(question_text) or _NUMERIC_CONTEXT_RE.search(question_text):
        cues.append("cifras del cliente")
    if _NUMERIC_PERCENTAGE_RE.search(question_text):
        cues.append("porcentaje en la pregunta")
    if any(rx.search(question_text) for rx in _TARIFA_PROGRESSIVE_ARTICLES):
        cues.append("artículo con tarifa progresiva")
    if _NIT_BY_DIGIT_RE.search(question_text):
        cues.append("calendario DIAN por dígito de NIT")
    if not cues:
        return ""
    return (
        "\n"
        "0.5) DIRECTIVA NUMÉRICA — la pregunta del usuario anclá "
        "cues numéricos (" + ", ".join(cues) + "). Obedecé esto:\n"
        "   * Si la pregunta menciona una cifra del cliente (monto en "
        "pesos, porcentaje, salario, ingresos, antigüedad), presentá "
        "el cálculo numérico explícito que conteste la pregunta. "
        "USÁ ÚNICAMENTE las cifras que ya están en la PREGUNTA o en "
        "los EXCERPTS — no inventes UVT, años, ni montos de afuera.\n"
        "   * Si la pregunta menciona un artículo con tarifas "
        "progresivas (Art. 242 ET dividendos, Art. 383 ET retención "
        "laboral, Art. 908 ET RST, Art. 241 ET tabla renta natural), "
        "nombrá los rangos UVT y los porcentajes concretos que estén "
        "en los EXCERPTS de ese artículo — no parafrasees \"según la "
        "tarifa\".\n"
        "   * Si la pregunta pide plazos por dígito de NIT, dá los "
        "días específicos por dígito SI el calendario está en los "
        "EXCERPTS; si no está, decí \"consulta el calendario DIAN "
        "vigente\" en vez de inventar fechas.\n"
    )


def _build_polish_prompt(
    *,
    request: PipelineCRequest,
    template_answer: str,
    evidence: GraphEvidenceBundle,
) -> str:
    # fix_v8 §3e — richer evidence inlining + a leading Primary Directive
    # that names the exact failure modes the validator rejects. Goal:
    # keep the LLM's tone-polish value-add while collapsing the
    # `invented_norm_lineage` / `invented_periods` rejection rate. The
    # registered rules block is still appended verbatim so existing
    # validators don't drift.
    primary_lines: list[str] = []
    primary_keys: list[str] = []
    for item in evidence.primary_articles[:6]:
        excerpt = (item.excerpt or "").strip().replace("\n", " ")
        if len(excerpt) > 900:
            excerpt = excerpt[:900] + "…"
        primary_lines.append(
            f"- Art. {item.node_key} — {item.title}\n  {excerpt}" if excerpt
            else f"- Art. {item.node_key} — {item.title}"
        )
        primary_keys.append(str(item.node_key))

    connected_lines: list[str] = []
    connected_keys: list[str] = []
    for item in evidence.connected_articles[:8]:
        excerpt = (item.excerpt or "").strip().replace("\n", " ")
        if len(excerpt) > 300:
            excerpt = excerpt[:300] + "…"
        connected_lines.append(
            f"- Art. {item.node_key} — {item.title}\n  {excerpt}" if excerpt
            else f"- Art. {item.node_key} — {item.title}"
        )
        connected_keys.append(str(item.node_key))

    reform_lines: list[str] = []
    reform_labels: list[str] = []
    for item in evidence.related_reforms[:6]:
        excerpt = (item.excerpt or "").strip().replace("\n", " ")
        if len(excerpt) > 240:
            excerpt = excerpt[:240] + "…"
        label = (item.title or item.node_key or "").strip()
        reform_lines.append(
            f"- {label}\n  {excerpt}" if excerpt else f"- {label}"
        )
        if label:
            reform_labels.append(label)

    support_lines: list[str] = []
    for doc in evidence.support_documents[:4]:
        support_lines.append(f"- {doc.title_hint} (family={doc.family})")

    primary_block = (
        "\n".join(primary_lines)
        or "(sin artículos ancla retornados por el grafo)"
    )
    connected_block = (
        "\n".join(connected_lines) or "(sin artículos adyacentes)"
    )
    reform_block = "\n".join(reform_lines) or "(sin reformas relacionadas)"
    support_block = (
        "\n".join(support_lines) or "(sin documentos de soporte)"
    )

    # Explicit allowlist the LLM can scan in one second. Anything outside
    # these lists is forbidden — this is the bright line the rejection
    # validators enforce.
    allowed_articles = ", ".join(
        f"Art. {k}" for k in (primary_keys + connected_keys) if k
    ) or "(ninguno — no cites artículos del ET en la reescritura)"
    allowed_reforms = (
        " | ".join(reform_labels)
        or "(ninguna — no introduzcas Leyes, Decretos, Resoluciones, Sentencias o Conceptos)"
    )

    numeric_directive = _build_numeric_directive(request.message or "")

    primary_directive = (
        "DIRECTIVA PRIMARIA — leé esto antes de las reglas, y obedecela "
        "por encima de cualquier otra cosa:\n"
        "\n"
        "Podés reescribir la prosa del BORRADOR para que suene como un "
        "contador colombiano senior — claro, operativo, sin relleno, sin "
        "disclaimers. Lo que NO podés hacer es inventar contenido. "
        "Específicamente:\n"
        f"{numeric_directive}"
        "\n"
        "0) ORDEN OBLIGATORIO de las secciones — exactamente este, de "
        "arriba hacia abajo:\n"
        "   1. **Recomendaciones Prácticas** (qué hacer concretamente, "
        "pasos, plazos, riesgos)\n"
        "   2. **Procedimiento Sugerido** (si el borrador lo trae)\n"
        "   3. **Precauciones** / **Riesgos y condiciones**\n"
        "   4. **Soportes** (si el borrador lo trae)\n"
        "   5. **Anclaje Legal** SIEMPRE AL FINAL\n"
        "Si el borrador trae las secciones en otro orden, REORDENALAS. "
        "NO renombres secciones. NO inventes secciones nuevas.\n"
        "\n"
        "1) NO introduzcas referencias a leyes, decretos, resoluciones, "
        "conceptos DIAN, sentencias, autos, circulares o cualquier otra "
        "norma cuyo identificador no aparezca literalmente en la lista "
        "REFORMAS Y NORMAS PERMITIDAS abajo. Si la norma no está listada, "
        "NO existe para esta respuesta — aunque la tengas memorizada.\n"
        "\n"
        "2) NO cites artículos del ET cuyo número no aparezca en la lista "
        "ARTÍCULOS PERMITIDOS abajo. Citar `(art. N ET)` con N fuera de "
        "esa lista es invención y será rechazado.\n"
        "\n"
        "3) NO introduzcas años, períodos gravables ni rangos temporales "
        "(\"AG 2024\", \"2022 y 2023\", \"ejercicio 2025\") que no aparezcan "
        "en el BORRADOR.\n"
        "\n"
        "4) NO inventes cifras, plazos, topes ni porcentajes que no estén "
        "en el BORRADOR o en los EXCERPTS de la evidencia abajo.\n"
        "\n"
        "5) PRESERVÁ la estructura de listas anidadas tal cual aparezca "
        "en el BORRADOR. Si una viñeta contiene sub-viñetas indentadas "
        "(líneas que empiezan con dos espacios + `- `), mantenelas como "
        "sub-viñetas — no las concatenes en un solo párrafo, no las "
        "promovas a viñetas de nivel superior, no cambies su indentación. "
        "Podés reescribir el texto DE cada sub-viñeta, pero no su "
        "jerarquía visual.\n"
        "\n"
        "Consecuencia: tu salida pasa por un validador automático. Si "
        "violás cualquiera de los puntos 1–4, tu reescritura se descarta "
        "y al usuario le mostramos un fallback determinista más breve. "
        "Para que tu trabajo cuente, quedate dentro de la evidencia."
    )

    allowlist_block = (
        "ARTÍCULOS PERMITIDOS PARA CITAR (origen: ARTÍCULOS ANCLA + "
        "ADYACENTES):\n"
        f"{allowed_articles}\n"
        "\n"
        "REFORMAS Y NORMAS PERMITIDAS (Leyes, Decretos, Resoluciones, "
        "Sentencias, Conceptos — origen: REFORMAS RELACIONADAS):\n"
        f"{allowed_reforms}"
    )

    return (
        "Actuás como un contador colombiano senior revisando la respuesta "
        "de un colega junior. Tu trabajo es reescribir la respuesta "
        "borrador para que suene como un contador senior guiando a otro: "
        "claro, operativo, sin relleno académico, sin disclaimers "
        "genéricos.\n"
        "\n"
        f"{primary_directive}\n"
        "\n"
        f"{allowlist_block}\n"
        "\n"
        f"{_rules_block()}\n"
        "\n"
        f"PREGUNTA DEL USUARIO:\n{request.message}\n"
        "\n"
        f"ARTÍCULOS ANCLA DEL GRAFO (con extractos para fundamentar la "
        f"reescritura):\n{primary_block}\n"
        "\n"
        f"ARTÍCULOS ADYACENTES (referencia opcional, con extractos "
        f"breves):\n{connected_block}\n"
        "\n"
        f"REFORMAS RELACIONADAS (las ÚNICAS leyes/decretos/sentencias que "
        f"podés citar):\n{reform_block}\n"
        "\n"
        f"DOCUMENTOS DE SOPORTE:\n{support_block}\n"
        "\n"
        "BORRADOR A REESCRIBIR (mantené estructura + todos los anchors "
        "inline):\n"
        f"{template_answer}\n"
        "\n"
        "Devolvé SOLO el texto reescrito en Markdown, sin explicación "
        "previa ni posterior."
    )


__all__ = [
    "POLISH_RULES",
    "PromptRule",
    "polish_graph_native_answer",
]
