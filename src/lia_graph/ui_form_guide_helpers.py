from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlencode


_FORM_GUIDE_PAGE_RE = re.compile(r"(?:page|pagina|p[aá]gina)[^0-9]*([0-9]+)", re.IGNORECASE)


def _serialize_guide_catalog_entry(entry: Any) -> dict[str, Any]:
    return {
        "reference_key": entry.reference_key,
        "title": entry.title,
        "form_version": entry.form_version,
        "available_profiles": list(entry.available_profiles),
        "supported_views": list(entry.supported_views),
        "last_verified_date": entry.last_verified_date,
        "download_available": entry.download_available,
        "disclaimer": entry.disclaimer,
    }


def _find_catalog_entry_by_reference_key(
    entries: list[Any],
    reference_key: str,
) -> dict[str, Any] | None:
    normalized = str(reference_key or "").strip()
    if not normalized:
        return None
    for entry in entries:
        if str(getattr(entry, "reference_key", "")).strip() == normalized:
            return _serialize_guide_catalog_entry(entry)
    return None


def _extract_form_guide_page_number(name: str, *, fallback: int) -> int:
    match = _FORM_GUIDE_PAGE_RE.search(str(name or ""))
    if match is None:
        return fallback
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return fallback


def _build_form_guide_asset_href(
    *,
    reference_key: str,
    profile: str,
    asset_name: str,
) -> str:
    query = urlencode(
        {
            "reference_key": reference_key,
            "profile": profile,
            "name": asset_name,
        }
    )
    return f"/api/form-guides/asset?{query}"


def _build_form_guide_page_assets(package: Any) -> list[dict[str, Any]]:
    profile_id = str(package.manifest.profile_id or "").strip()
    reference_key = str(package.manifest.reference_key or "").strip()
    assets_by_page: dict[int, tuple[int, dict[str, Any]]] = {}
    for index, page_name in enumerate(package.pages, start=1):
        page_number = _extract_form_guide_page_number(page_name, fallback=index)
        suffix = Path(page_name).suffix.lower()
        priority = 0 if suffix in {".png", ".jpg", ".jpeg", ".webp"} else 1
        payload = {
            "name": page_name,
            "page": page_number,
            "url": _build_form_guide_asset_href(
                reference_key=reference_key,
                profile=profile_id,
                asset_name=page_name,
            ),
        }
        current = assets_by_page.get(page_number)
        if current is None or priority < current[0]:
            assets_by_page[page_number] = (priority, payload)
    return [
        payload
        for _, payload in sorted(
            assets_by_page.values(),
            key=lambda row: (int(row[1].get("page") or 0), str(row[1].get("name") or "")),
        )
    ]
