from __future__ import annotations

from typing import Any, Mapping

_SUPPORTED_PAISES = {
    "colombia": "es-CO",
    "peru": "es-PE",
    "mexico": "es-MX",
}

_PAIS_ALIASES = {
    "co": "colombia",
    "col": "colombia",
    "colombia": "colombia",
    "pe": "peru",
    "per": "peru",
    "peru": "peru",
    "mx": "mexico",
    "mex": "mexico",
    "mexico": "mexico",
}


def normalize_pais(pais: str | None = None) -> str | None:
    candidate = (pais or "").strip().lower()
    if not candidate:
        return None
    return _PAIS_ALIASES.get(candidate)


def get_supported_paises() -> set[str]:
    return set(_SUPPORTED_PAISES.keys())


def default_locale_for_pais(pais: str) -> str:
    return _SUPPORTED_PAISES.get(pais, "es-CO")


def is_document_in_country_scope(doc: Mapping[str, Any], pais: str | None) -> bool:
    if pais is None:
        return True
    doc_pais = str(doc.get("pais", "")).strip().lower() or "colombia"
    return doc_pais == pais


def build_country_scope_prompt_block(pais: str | None) -> str:
    if pais is None:
        return "No hay pais seleccionado. No se puede garantizar muralla de conocimiento por jurisdiccion."
    return (
        f"Pais seleccionado: {pais}.\\n"
        "Guardrail supra obligatorio:\\n"
        "- Usar solo conocimiento legal del pais seleccionado.\\n"
        "- No mezclar normativa ni doctrina de otros paises.\\n"
        "- Si falta evidencia local, pedir aclaraciones en vez de extrapolar jurisdicciones."
    )


def build_country_scope_refusal(pais: str | None, reason: str) -> str:
    label = pais or "desconocido"
    return (
        "1) Resumen ejecutivo\\n"
        f"La respuesta fue bloqueada por muralla supra de pais ({label}).\\n\\n"
        "2) Motivo de bloqueo\\n"
        f"{reason}\\n\\n"
        "3) Siguiente paso\\n"
        "Reenviar la consulta con pais valido y evidencia del mismo pais."
    )
