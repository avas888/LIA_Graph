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
from pathlib import Path
from typing import Any

from ..llm_runtime import DEFAULT_RUNTIME_CONFIG_PATH, resolve_llm_adapter
from ..pipeline_c.contracts import PipelineCRequest
from .contracts import GraphEvidenceBundle

_POLISH_FLAG_ENV = "LIA_LLM_POLISH_ENABLED"


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
        return template_answer, base_diag

    if not _polish_enabled():
        base_diag["skip_reason"] = "polish_disabled_by_env"
        return template_answer, base_diag

    config_path = _resolve_config_path(runtime_config_path)
    try:
        adapter, resolution = resolve_llm_adapter(runtime_config_path=config_path)
    except Exception as exc:  # noqa: BLE001 - polish must never raise
        base_diag["skip_reason"] = f"resolver_error:{type(exc).__name__}"
        return template_answer, base_diag

    if adapter is None:
        base_diag["skip_reason"] = "no_adapter_available"
        base_diag["fallback_skipped"] = resolution.get("fallback_skipped", []) if isinstance(resolution, dict) else []
        return template_answer, base_diag

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
        return template_answer, base_diag

    if not polished:
        base_diag.update(_runtime_diag_from_resolution(resolution))
        base_diag["mode"] = "failed"
        base_diag["skip_reason"] = "empty_llm_output"
        return template_answer, base_diag

    if not _preserves_required_anchors(template_answer, polished):
        base_diag.update(_runtime_diag_from_resolution(resolution))
        base_diag["mode"] = "rejected"
        base_diag["skip_reason"] = "anchors_stripped"
        return template_answer, base_diag

    base_diag.update(_runtime_diag_from_resolution(resolution))
    base_diag["mode"] = "llm"
    base_diag["skip_reason"] = None
    return polished, base_diag


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
        "REGLAS INVIOLABLES:\n"
        "- Preservá TODAS las referencias inline al Estatuto Tributario con la forma (art. X ET) o (arts. X y Y ET). "
        "No inventés nuevas; no borrés las existentes.\n"
        "- No agregues saludos, disclaimers, ni frases como \"espero que esto ayude\".\n"
        "- Mantené la estructura por secciones del borrador (Respuestas directas / Ruta sugerida / "
        "Riesgos y condiciones / Soportes clave). Podés reformular cada bullet pero no reordenes ni elimines secciones.\n"
        "- Si el borrador contiene una tabla markdown (líneas que empiezan con `|` y la línea separadora `|---|...`), "
        "preservala letra por letra. No la reformules en prosa, no fusiones celdas, no agregues ni elimines filas o columnas. "
        "El comparativo en tabla es la forma exacta en la que el contador necesita ver pre/post; reflowarlo destruye la "
        "información estructural.\n"
        "- Si el borrador trae una sección \"Respuestas directas\", conservá cada sub-pregunta como un bullet en negrita "
        "con sus bullets hijos intactos; no fusiones sub-preguntas ni muevas respuestas entre ellas. Si un sub-bloque "
        "dice \"Cobertura pendiente para esta sub-pregunta\", mantené esa advertencia explícita para esa pregunta.\n"
        "- Si el borrador dice \"la cobertura quedó parcial\", mantené esa advertencia.\n"
        "- No inventes cifras, topes, porcentajes ni artículos que no estén en el borrador o en la evidencia abajo.\n"
        "- No inventés descripciones cortas para los artículos citados (e.g., 'Art. 290 ET: Régimen de transición para X'). "
        "Los artículos del ET tienen múltiples numerales con temas distintos; describir el artículo entero con una frase desde "
        "tu memoria casi siempre se equivoca de numeral. Si necesitás caracterizar un artículo en una línea, usá literalmente "
        "el encabezado del artículo tal como aparece en ARTÍCULOS ANCLA DEL GRAFO, o citá el numeral específico que aplica "
        "según el borrador. Cuando dudés, dejá la cita sola — `(art. 290 ET)` sin descripción es preferible a una descripción inventada.\n"
        "- Respondé en español neutro profesional, sin muletillas.\n"
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


__all__ = ["polish_graph_native_answer"]
