from __future__ import annotations


def canonical_provider_name(value: str | None) -> str:
    return str(value or "").strip()


def extract_expert_providers(*args: object, **kwargs: object) -> list[str]:
    return []


def provider_from_domain(domain: str | None) -> str | None:
    value = str(domain or "").strip().lower()
    return value or None


def provider_labels(*args: object, **kwargs: object) -> dict[str, str]:
    return {}


def provider_names_from_label(label: str | None) -> list[str]:
    value = str(label or "").strip()
    return [value] if value else []

