"""LLM polish step for Pipeline D's graph-native answers.

Sits between the template-driven composer and the streaming sink: the
composer already wires inline legal anchors and picks the right sections
for the case. The polish step takes that skeleton plus retrieved evidence
and asks the LLM to rewrite the prose in senior-accountant voice while
preserving every legal anchor verbatim — including the code suffix
(`ET` / `CST` / etc.) exactly as the BORRADOR writes it. Lia answers tax
AND labor: the Estatuto Tributario governs `(art. N ET)` and the Código
Sustantivo del Trabajo governs `(art. N CST)` — they are different codes
and must never be swapped.

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
            "Preservá TODAS las referencias inline a artículos normativos con su SUFIJO DE CÓDIGO "
            "exactamente como aparece en el BORRADOR. Dos códigos co-existen: `(art. N ET)` / "
            "`(arts. N y M ET)` para el Estatuto Tributario (impuestos: renta, IVA, retención) y "
            "`(art. N CST)` / `(arts. N y M CST)` para el Código Sustantivo del Trabajo (laboral: "
            "contrato, salarios, prestaciones, indemnización, terminación). REGLA INVIOLABLE: NUNCA "
            "reescribás `(art. N CST)` como `(art. N ET)` ni `(art. N ET)` como `(art. N CST)` — son "
            "códigos legales distintos. Tampoco inventés ni borrés referencias existentes. Si el "
            "BORRADOR escribe `(CST art. 64)` o `art. 65 CST` o `art. 401-3 ET`, preservalo letra por "
            "letra. Si dudás del código, preferí dejarlo tal cual aparece en el BORRADOR."
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
            "y TODAS las referencias inline a artículos (`(art. N ET)`, `(art. N CST)`, etc.) con su sufijo de código intacto. No inventés normas, artículos, ni cifras que no estén en la "
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
            "completa que explique POR QUÉ se cita ese artículo. Formas aceptables (donde "
            "`CÓDIGO` es el sufijo legal real del BORRADOR — `ET` para Estatuto Tributario, "
            "`CST` para Código Sustantivo del Trabajo, etc.): "
            "`Art. N CÓDIGO — <qué regula el artículo>.` (preservando el encabezado del "
            "BORRADOR) o en prosa `<Qué regula el artículo> en el (art. N CÓDIGO).` "
            "Ejemplos válidos: `La definición de salario se encuentra en los (arts. 127-132 ET).`; "
            "`La indemnización por despido sin justa causa se regula en el (art. 64 CST).`. "
            "NUNCA dejes una viñeta como sólo `(art. N CÓDIGO)` ni como sólo `Art. N CÓDIGO` sin "
            "descripción al lado — la sección entera deja de tener sentido. NUNCA cambies el "
            "sufijo (`ET` por `CST` o viceversa). Tomá la descripción del encabezado del artículo "
            "en ARTÍCULOS ANCLA DEL GRAFO o del EXCERPT; no inventes contenido fuera de la "
            "evidencia. Si el BORRADOR ya trae el encabezado en cada viñeta (`Art. N CÓDIGO — "
            "<heading>.`), preservalo o reescribilo en prosa, pero no lo borres ni le cambies el código."
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
            "legales inline — `(art. 147 ET)`, `(arts. 147 y 290 ET)`, `(art. 64 CST)`, "
            "`(arts. 186 a 197 CST)`, `(art. 401-3 ET)`, `(Decreto 624 de 1989)`, `(Ley 1819 de 2016)`, "
            "`(Ley 50 de 1990 art. 99)`, `(numeral 3 del art. 26 ET)` se preservan letra por letra como "
            "están en el borrador, incluyendo el sufijo de código (ET / CST / etc.). La negrita aplica "
            "a la cifra en prosa, no a la cita normativa."
        ),
        post_apply=format_numbers_with_bold,
        surfaces=("main_chat", "normativa"),
    ),
    PromptRule(
        id="no_invented_article_descriptions",
        category="semantic",
        prompt_text=(
            "No inventés descripciones cortas para los artículos citados (e.g., 'Art. 290 ET: Régimen de transición para X', "
            "'Art. 64 CST: Indemnización por despido'). Los artículos del ET y del CST tienen múltiples numerales con temas "
            "distintos; describir el artículo entero con una frase desde tu memoria casi siempre se equivoca de numeral. Si "
            "necesitás caracterizar un artículo en una línea, usá literalmente el encabezado del artículo tal como aparece "
            "en ARTÍCULOS ANCLA DEL GRAFO, o citá el numeral específico que aplica según el borrador. Cuando dudés, dejá la "
            "cita sola — `(art. 290 ET)` o `(art. 64 CST)` sin descripción es preferible a una descripción inventada."
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
        validate=lambda template, polished, evidence=None: _no_invented_norm_lineage(
            template, polished, evidence
        ),
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
        validate=lambda template, polished, evidence=None: _no_invented_periods(
            template, polished, evidence
        ),
        rejection_reason="invented_periods",
    ),
    # v23 P7 — Anclaje Legal source-code coherence directive. Prevents the
    # REGLA DE EXPANSIÓN from inflating Anclaje with off-topic source-code
    # articles (e.g. ET articles in a CST-rooted labor answer). Mirrors the
    # synthesis-time `answer_anclaje_topic_gate.filter_anclaje_articles`
    # rule at the polish layer so LLM expansion stays family-coherent.
    PromptRule(
        id="anclaje_source_code_coherence",
        category="semantic",
        prompt_text=(
            "ANCLAJE LEGAL — coherencia de código por familia: si el "
            "BORRADOR cita en su mayoría artículos `CST` (familia laboral), "
            "el bloque **Anclaje Legal** del resultado SOLO puede listar "
            "artículos `CST` o `Ley` laboral (Ley 50/1990, Ley 789/2002, "
            "Ley 2466). PROHIBIDO añadir artículos `ET` al Anclaje en una "
            "respuesta laboral, aunque aparezcan en ARTÍCULOS ADYACENTES. "
            "Lo simétrico aplica a respuestas tributarias: si el BORRADOR "
            "cita en su mayoría `ET`, el Anclaje NO puede incluir "
            "artículos `CST`. Si un artículo adyacente tiene un código "
            "incompatible con la familia dominante del BORRADOR, déjalo "
            "fuera del Anclaje — incluso si la REGLA DE EXPANSIÓN te "
            "invita a llenar la sección. El usuario prefiere un Anclaje "
            "breve y coherente a un Anclaje extenso con artículos "
            "off-topic."
        ),
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
    # v23 P5 — preserve user-stated numerics through polish (G5 / audit Q10).
    PromptRule(
        id="preserves_user_numerics",
        category="semantic",
        prompt_text=(
            "PRESERVÁ las cifras (montos en pesos, conteos en UVT, "
            "porcentajes) que el usuario mencione literalmente en su "
            "pregunta. Si la pregunta dice `$3.000.000`, tu respuesta no "
            "puede decir `$2.000.000` ni `tres millones quinientos mil`. "
            "El usuario describió SU caso con SUS números — no los "
            "reescribas."
        ),
        validate=lambda template, polished, evidence=None, question=None: _preserves_user_numerics(
            template, polished, evidence, question
        ),
        rejection_reason="mutated_user_numerics",
    ),
    # v23 P5 — same-answer year-constant contradiction (G5 / audit Q10).
    PromptRule(
        id="no_inconsistent_year_constants",
        category="semantic",
        prompt_text=(
            "NO mezclés constantes de años distintos en la misma respuesta "
            "(UVT 2024 = $47.065 vs UVT 2025 = $49.799 vs UVT 2026 = "
            "$52.374). Determiná de qué año gravable habla el usuario y "
            "usá SOLO las cifras de ese año. La excepción es una pregunta "
            "explícitamente comparativa (`comparación AG 2025 vs AG "
            "2026`); ahí podés mostrar ambos."
        ),
        validate=lambda template, polished, evidence=None, question=None: _no_inconsistent_year_constants(
            template, polished, evidence, question
        ),
        rejection_reason="mixed_year_constants",
    ),
    # v23 P6 — Colombian-Spanish style (G6 / audit Q7).
    PromptRule(
        id="locale_style_colombian",
        category="tonal",
        prompt_text=(
            "DIRECTIVA DE ESTILO COLOMBIANO: Usá español neutro colombiano "
            "en forma `usted` para verbos imperativos profesionales: "
            "`verifique`, `tenga presente`, `controle`, `revise`, "
            "`recuerde`, `cumpla`. PROHIBIDO voseo (forma `vos`): "
            "`verificá`, `tené`, `andá`, `mirá`, `decidí`, `pensá`, "
            "`salí`, `pedí`, `seguí`. Suena foráneo al contador "
            "colombiano y reduce la credibilidad del consejo."
        ),
        validate=lambda template, polished, evidence=None, question=None: _no_voseo(
            template, polished, evidence, question
        ),
        rejection_reason="voseo_detected",
    ),
    # v25 P4 — Framework coherence (G11 / audit Q19). Reject NIIF 16 /
    # IFRS 16 / right-of-use leakage into a NIIF-Pymes question. Validator
    # body lives in answer_polish_validators_v25.py per granularization.
    PromptRule(
        id="framework_coherence",
        category="semantic",
        prompt_text=(
            "Si la pregunta menciona NIIF para las Pymes, NO uses NIIF 16, "
            "IFRS 16 ni el modelo right-of-use; aplica Sección 20 de NIIF "
            "para Pymes para arrendamientos."
        ),
        validate=lambda template, polished, evidence=None, question=None: (
            __import__(
                "lia_graph.pipeline_d.answer_polish_validators_v25",
                fromlist=["framework_coherence"],
            ).framework_coherence(template, polished, evidence, question)
        ),
        rejection_reason="framework_mismatch",
    ),
    # v25 P5 — Coverage-gap stub gate (G12 / audit Q3+Q12). Reject "Cobertura
    # pendiente"-style non-answers from polished output.
    PromptRule(
        id="no_coverage_gap_phrase",
        category="semantic",
        prompt_text=(
            "Si una sub-pregunta no se puede responder con la evidencia, "
            "OMÍTELA en silencio. NO escribas `Cobertura pendiente`, "
            "`valida el expediente`, ni frases equivalentes — al contador le "
            "molesta más una respuesta con huecos visibles que una respuesta "
            "corta y completa."
        ),
        validate=lambda template, polished, evidence=None, question=None: (
            __import__(
                "lia_graph.pipeline_d.answer_polish_validators_v25",
                fromlist=["no_coverage_gap_phrase"],
            ).no_coverage_gap_phrase(template, polished, evidence, question)
        ),
        rejection_reason="coverage_gap_phrase",
    ),
    # v25 P9 — Counterfactual-entity gate (G16 / audit Q8, Q16, Q17). Reject
    # polished output that introduces named persons, companies, or monetary
    # facts not present in the question or evidence.
    PromptRule(
        id="no_counterfactual_entities",
        category="semantic",
        prompt_text=(
            "NO inventes nombres propios de personas, razones sociales (SAS, "
            "LTDA, S.A.) ni cifras grandes en pesos (≥ COP 1.000.000) que no "
            "estén en la PREGUNTA o en los EXCERPTS de la evidencia. Tu "
            "ejemplo no puede tener `Carlos Pérez`, `Empresa XYZ SAS` ni "
            "`$5.000 millones` si esos tokens no están en lo que el usuario "
            "te dio."
        ),
        validate=lambda template, polished, evidence=None, question=None: (
            __import__(
                "lia_graph.pipeline_d.answer_polish_validators_v25",
                fromlist=["no_counterfactual_entities"],
            ).no_counterfactual_entities(template, polished, evidence, question)
        ),
        rejection_reason="counterfactual_entity",
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
    ) or "(ninguno — no cites artículos del ET ni del CST en la reescritura)"
    allowed_reforms = (
        " | ".join(reform_labels)
        or "(ninguna — no introduzcas Leyes, Decretos, Resoluciones, Sentencias o Conceptos)"
    )

    numeric_directive = _build_numeric_directive(request.message or "")

    # v23 P2 — year-constants directive. When a fiscal year is detected in
    # the question (or set on conversation_state), prepend a block naming
    # the verified canonical UVT/SMLMV/auxilio for that year so the LLM
    # cannot quote stale evidence. Skipped silently when no year detected
    # or no verified facts for that year (per D10 — never inject default
    # current-year on a generic question).
    from ..year_facts import build_directive_block as _yc_block
    from ..year_facts import extract_fiscal_year as _yc_extract
    _detected_year = _yc_extract(
        request.message,
        planner_intent=None,
        conversation_state=(getattr(request, "conversation_state", None) or {}),
    )
    year_constants_directive = (
        _yc_block(_detected_year) if _detected_year is not None else None
    )

    # v25 directive builders extracted to sibling per
    # `feedback_granular_edits` + operator directive 2026-05-17 PM
    # ("granularize polish.py if over 1000 LOC per artifact"). Each builder
    # respects its own kill-switch flag and returns "" when not applicable.
    from .answer_polish_directives_v25 import build_v25_polish_blocks
    _v25_blocks = build_v25_polish_blocks(request.message or "")
    norm_keyed_block = _v25_blocks["norm_keyed"]
    cross_border_block = _v25_blocks["cross_border"]
    municipal_block = _v25_blocks["municipal"]
    framework_block = _v25_blocks["framework"]

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
        "2) NO cites artículos cuyo número no aparezca en la lista "
        "ARTÍCULOS PERMITIDOS abajo. Citar `(art. N ET)`, `(art. N CST)` o "
        "cualquier referencia inline con un número fuera de esa lista es "
        "invención y será rechazado. PRESERVÁ el sufijo de código (ET / CST / "
        "etc.) tal cual aparece en el BORRADOR — nunca lo cambies.\n"
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

    year_block = (
        f"\n{year_constants_directive}\n" if year_constants_directive else ""
    )
    norm_keyed_block_wrapped = (
        f"\n{norm_keyed_block}\n" if norm_keyed_block else ""
    )
    cross_border_wrapped = (
        f"\n{cross_border_block}\n" if cross_border_block else ""
    )
    municipal_wrapped = (
        f"\n{municipal_block}\n" if municipal_block else ""
    )
    framework_wrapped = (
        f"\n{framework_block}\n" if framework_block else ""
    )

    return (
        "Actuás como un contador colombiano senior revisando la respuesta "
        "de un colega junior. Tu trabajo es reescribir la respuesta "
        "borrador para que suene como un contador senior guiando a otro: "
        "claro, operativo, sin relleno académico, sin disclaimers "
        "genéricos.\n"
        "\n"
        f"{primary_directive}\n"
        f"{year_block}"
        f"{norm_keyed_block_wrapped}"
        f"{cross_border_wrapped}"
        f"{municipal_wrapped}"
        f"{framework_wrapped}"
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
