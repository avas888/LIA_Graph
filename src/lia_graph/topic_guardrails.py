from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping

from .scope_guardrails import build_country_scope_prompt_block, is_document_in_country_scope


@dataclass(frozen=True)
class TopicScope:
    key: str
    label: str
    allowed_topics: frozenset[str]
    allowed_path_prefixes: tuple[str, ...]


_TOPIC_SCOPES: dict[str, TopicScope] = {
    "declaracion_renta": TopicScope(
        key="declaracion_renta",
        label="Declaración de Renta",
        allowed_topics=frozenset({"renta", "renta_parametros"}),
        allowed_path_prefixes=(
            "normativa/renta/",
            "templates/renta_case_intake_template.md",
        ),
    ),
    "iva": TopicScope(
        key="iva",
        label="IVA (incluyendo bimestral)",
        allowed_topics=frozenset({"iva"}),
        allowed_path_prefixes=(
            "normativa/iva/",
            "industry_guidance/iva/",
            "templates/iva/",
        ),
    ),
    "ica": TopicScope(
        key="ica",
        label="ICA",
        allowed_topics=frozenset({"ica"}),
        allowed_path_prefixes=(
            "normativa/ica/",
            "templates/ica/",
        ),
    ),
    "estados_financieros_niif": TopicScope(
        key="estados_financieros_niif",
        label="Estados financieros bajo NIIF",
        allowed_topics=frozenset({"niif"}),
        allowed_path_prefixes=(
            "normativa/niif/",
            "industry_guidance/niif/",
            "templates/niif/",
        ),
    ),
    "laboral": TopicScope(
        key="laboral",
        label="Laboral y nómina",
        allowed_topics=frozenset({"laboral"}),
        allowed_path_prefixes=(
            "normativa/laboral/",
            "industry_guidance/laboral/",
            "templates/laboral/",
            "laboral/",
        ),
    ),
    "calendario_obligaciones": TopicScope(
        key="calendario_obligaciones",
        label="Calendario y obligaciones recurrentes",
        allowed_topics=frozenset({"calendarios", "renta", "renta_parametros"}),
        allowed_path_prefixes=("calendarios/",),
    ),
    "facturacion_electronica": TopicScope(
        key="facturacion_electronica",
        label="Facturación Electrónica",
        allowed_topics=frozenset({"facturacion_electronica"}),
        allowed_path_prefixes=(
            "normativa/facturacion_electronica/",
            "industry_guidance/facturacion_electronica/",
            "templates/facturacion_electronica/",
        ),
    ),
}

_TOPIC_ALIASES = {
    "declaracion_renta": "declaracion_renta",
    "renta": "declaracion_renta",
    "iva": "iva",
    "iva_bimestral": "iva",
    "ica": "ica",
    "estados_financieros_niif": "estados_financieros_niif",
    "niif": "estados_financieros_niif",
    "ifrs": "estados_financieros_niif",
    "estados_financieros": "estados_financieros_niif",
    "laboral": "laboral",
    "nomina": "laboral",
    "nómina": "laboral",
    "calendario_obligaciones": "calendario_obligaciones",
    "obligaciones_recurrentes": "calendario_obligaciones",
    "calendario": "calendario_obligaciones",
    "calendario_tributario": "calendario_obligaciones",
    "facturacion_electronica": "facturacion_electronica",
    "facturacion": "facturacion_electronica",
    # --- aliases for new custom corpora (bootstrap adds topic→topic, these add shorthands) ---
    "reforma_laboral": "reforma_laboral_2466",
    "ley_2466": "reforma_laboral_2466",
    "ibua": "impuestos_saludables",
    "icui": "impuestos_saludables",
    "impuestos_saludables": "impuestos_saludables",
    "prestaciones_niif": "prestaciones_sociales_niif_fiscal",
    "prestaciones_fiscal": "prestaciones_sociales_niif_fiscal",
    "depreciacion_niif": "depreciacion_fiscal_niif",
    "depreciacion_fiscal": "depreciacion_fiscal_niif",
    "amortizacion_fiscal": "depreciacion_fiscal_niif",
    "amortizacion_niif": "depreciacion_fiscal_niif",
    "cambio_doctrinal": "cambio_doctrinal_dian",
    "dsno": "cambio_doctrinal_dian",
    "nomina_electronica": "laboral",
}


def register_topic_scope(scope: TopicScope) -> None:
    """Register a custom TopicScope at runtime (for user-created corpus categories)."""
    _TOPIC_SCOPES[scope.key] = scope


def register_topic_alias(alias: str, canonical_key: str) -> None:
    """Register a topic alias at runtime (e.g. slug → canonical key)."""
    _TOPIC_ALIASES[alias] = canonical_key


def extend_topic_scope_allowed_topics(key: str, extra_topics: frozenset[str]) -> None:
    """Add extra allowed_topics to an existing TopicScope (creates updated copy)."""
    scope = _TOPIC_SCOPES.get(key)
    if scope is None:
        return
    merged = scope.allowed_topics | extra_topics
    if merged != scope.allowed_topics:
        _TOPIC_SCOPES[key] = replace(scope, allowed_topics=merged)


def normalize_topic_key(topic: str | None) -> str | None:
    if topic is None:
        return None
    candidate = topic.strip().lower()
    if not candidate:
        return None
    return _TOPIC_ALIASES.get(candidate)


def get_topic_scope(topic: str | None) -> TopicScope | None:
    normalized = normalize_topic_key(topic)
    if normalized is None:
        return None
    return _TOPIC_SCOPES.get(normalized)


def get_supported_topics() -> set[str]:
    return set(_TOPIC_SCOPES.keys())


def get_topic_label(topic: str | None) -> str:
    scope = get_topic_scope(topic)
    if scope is None:
        return "General"
    return scope.label


def _extract_doc_fields(doc: Mapping[str, Any]) -> tuple[str, str]:
    doc_topic = str(doc.get("topic", "")).strip().lower()
    rel_path = str(doc.get("relative_path", "")).strip().lower()
    return doc_topic, rel_path


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "si"}


def is_document_in_topic_scope(
    doc: Mapping[str, Any],
    topic: str | None,
    pais: str | None = None,
    primary_scope_mode: str = "global_overlay",
) -> bool:
    if not is_document_in_country_scope(doc, pais=pais):
        return False

    scope = get_topic_scope(topic)
    if scope is None:
        return True

    mode = str(primary_scope_mode or "global_overlay").strip().lower() or "global_overlay"
    doc_topic, rel_path = _extract_doc_fields(doc)
    if doc_topic in scope.allowed_topics:
        return True
    if any(rel_path.startswith(prefix) for prefix in scope.allowed_path_prefixes):
        return True
    if mode == "global_overlay":
        cross_topic = _coerce_bool(doc.get("cross_topic"))
        knowledge_class = str(doc.get("knowledge_class", "")).strip().lower()
        if cross_topic and knowledge_class == "normative_base":
            return True
    return False



def build_topic_scope_prompt_block(topic: str | None, pais: str | None = None) -> str:
    country_block = build_country_scope_prompt_block(pais)
    scope = get_topic_scope(topic)
    if scope is None:
        return (
            f"{country_block}\n\n"
            "No hay tema seleccionado. Limita la respuesta estrictamente a los documentos de soporte provistos y "
            "si faltan evidencias responde con preguntas de aclaracion."
        )

    repos = "\n".join(f"- {prefix}" for prefix in scope.allowed_path_prefixes)
    topics = ", ".join(sorted(scope.allowed_topics))
    return (
        f"{country_block}\n\n"
        f"Tema seleccionado: {scope.label} ({scope.key}).\n"
        "Regla obligatoria de alcance:\n"
        f"- Solo usar conocimiento recuperado desde estos repositorios/rutas:\n{repos}\n"
        f"- Solo usar documentos con topic metadata en: {topics}\n"
        "- No introducir normativa, criterios o ejemplos fuera de ese alcance.\n"
        "- Si la evidencia recuperada no alcanza, responder con faltantes y preguntas de aclaracion, sin extrapolar."
    )


def contains_out_of_scope_repository_reference(answer_markdown: str, topic: str | None) -> bool:
    scope = get_topic_scope(topic)
    if scope is None:
        return False

    text = answer_markdown.lower()
    own_prefixes = set(scope.allowed_path_prefixes)
    other_prefixes: list[str] = []
    for candidate in _TOPIC_SCOPES.values():
        if candidate.key == scope.key:
            continue
        # Skip prefixes shared with current scope (parent/child inheritance)
        for prefix in candidate.allowed_path_prefixes:
            if prefix not in own_prefixes:
                other_prefixes.append(prefix)

    return any(prefix in text for prefix in other_prefixes)


def build_topic_scope_refusal(topic: str | None, reason: str, pais: str | None = None) -> str:
    label = get_topic_label(topic)
    return (
        "1) Resumen ejecutivo\n"
        f"La respuesta fue bloqueada por guardrail de alcance para el tema {label}"
        f"{f' en {pais}' if pais else ''}.\n\n"
        "2) Motivo de bloqueo\n"
        f"{reason}\n\n"
        "3) Siguiente paso\n"
        "Reformular o ampliar la consulta manteniendola dentro de los repositorios del tema seleccionado."
    )


