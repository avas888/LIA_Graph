"""Shared source-tier labeling helpers."""

from __future__ import annotations

SOURCE_TIER_KEY_NORMATIVO = "normativo"
SOURCE_TIER_KEY_EXPERTOS = "expertos"
SOURCE_TIER_KEY_LOGGRO = "loggro"
DEFAULT_SOURCE_TIER_LABEL = "Fuente"


def source_tier_key_for_row(
    *,
    knowledge_class: str | None = None,
    source_type: str | None = None,
    source_url: str | None = None,
) -> str:
    klass = str(knowledge_class or "").strip().lower()
    stype = str(source_type or "").strip().lower()
    url = str(source_url or "").strip().lower()
    if klass == "practica_erp":
        return SOURCE_TIER_KEY_LOGGRO
    if klass == "interpretative_guidance":
        return SOURCE_TIER_KEY_EXPERTOS
    if "normograma" in url or klass == "normative_base" or stype in {"ley", "decreto", "resolucion", "concepto"}:
        return SOURCE_TIER_KEY_NORMATIVO
    return SOURCE_TIER_KEY_NORMATIVO


def source_tier_label_for_key(key: str | None) -> str:
    normalized = str(key or "").strip().lower()
    if normalized == SOURCE_TIER_KEY_NORMATIVO:
        return "Fuente Normativa"
    if normalized == SOURCE_TIER_KEY_EXPERTOS:
        return "Fuente Expertos"
    if normalized == SOURCE_TIER_KEY_LOGGRO:
        return "Fuente Loggro"
    return DEFAULT_SOURCE_TIER_LABEL


def source_tier_label_for_row(
    *,
    knowledge_class: str | None = None,
    source_type: str | None = None,
    source_url: str | None = None,
) -> str:
    return source_tier_label_for_key(
        source_tier_key_for_row(
            knowledge_class=knowledge_class,
            source_type=source_type,
            source_url=source_url,
        )
    )


def is_practical_override_source(
    *,
    knowledge_class: str | None = None,
    source_type: str | None = None,
    source_url: str | None = None,
) -> bool:
    return (
        source_tier_key_for_row(
            knowledge_class=knowledge_class,
            source_type=source_type,
            source_url=source_url,
        )
        == SOURCE_TIER_KEY_LOGGRO
    )
