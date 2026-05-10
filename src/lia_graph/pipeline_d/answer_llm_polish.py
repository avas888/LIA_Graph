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
    validate: Callable[[str, str], bool] | None = None
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
            "Mantené la estructura por secciones del borrador (Respuestas directas / Ruta sugerida / "
            "Riesgos y condiciones / Soportes clave) y NO elimines secciones. Podés reformular cada bullet existente. "
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
) -> tuple[bool, str | None]:
    """Run every rule's ``validate`` predicate. Returns ``(ok, reason)``.

    ``ok`` is False if any rule rejected the polished text. ``reason``
    is the failed rule's ``rejection_reason`` (or a generic
    ``rule_violated:<id>`` if the rule didn't declare one).
    """
    for rule in POLISH_RULES:
        if rule.validate is None or surface not in rule.surfaces:
            continue
        if not rule.validate(template, polished):
            return False, rule.rejection_reason or f"rule_violated:{rule.id}"
    return True, None


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

    ok, reason = _validate_against_rules(template_answer, polished)
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


def _build_polish_prompt(
    *,
    request: PipelineCRequest,
    template_answer: str,
    evidence: GraphEvidenceBundle,
) -> str:
    primary_lines: list[str] = []
    for item in evidence.primary_articles[:4]:
        excerpt = (item.excerpt or "").strip().replace("\n", " ")
        if len(excerpt) > 600:
            excerpt = excerpt[:600] + "…"
        primary_lines.append(
            f"- Art. {item.node_key} — {item.title}: {excerpt}"
        )
    connected_lines: list[str] = []
    for item in evidence.connected_articles[:6]:
        connected_lines.append(f"- Art. {item.node_key} — {item.title}")
    support_lines: list[str] = []
    for doc in evidence.support_documents[:4]:
        support_lines.append(f"- {doc.title_hint} (family={doc.family})")

    primary_block = "\n".join(primary_lines) or "(sin artículos ancla retornados por el grafo)"
    connected_block = "\n".join(connected_lines) or "(sin artículos adyacentes)"
    support_block = "\n".join(support_lines) or "(sin documentos de soporte)"

    return (
        "Actuás como un contador colombiano senior revisando la respuesta de un colega junior. "
        "Tu trabajo es reescribir la respuesta borrador para que suene como un contador senior "
        "guiando a otro: claro, operativo, sin relleno académico, sin disclaimers genéricos. "
        "\n\n"
        f"{_rules_block()}\n"
        "\n"
        f"PREGUNTA DEL USUARIO:\n{request.message}\n"
        "\n"
        f"ARTÍCULOS ANCLA DEL GRAFO:\n{primary_block}\n"
        "\n"
        f"ARTÍCULOS ADYACENTES (referencia opcional):\n{connected_block}\n"
        "\n"
        f"DOCUMENTOS DE SOPORTE:\n{support_block}\n"
        "\n"
        "BORRADOR A REESCRIBIR (mantené estructura + todos los anchors inline):\n"
        f"{template_answer}\n"
        "\n"
        "Devolvé SOLO el texto reescrito en Markdown, sin explicación previa ni posterior."
    )


__all__ = [
    "POLISH_RULES",
    "PromptRule",
    "polish_graph_native_answer",
]
