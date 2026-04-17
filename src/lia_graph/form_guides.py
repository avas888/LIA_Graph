from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

FORM_GUIDES_ROOT = Path("knowledge_base/form_guides")
OFFICIAL_FORM_PDF_SOURCE_TYPES = {"formulario_oficial_pdf"}


@dataclass(frozen=True)
class GuideManifest:
    reference_key: str
    title: str
    form_version: str
    profile_id: str
    profile_label: str
    supported_views: tuple[str, ...] = ("structured",)
    last_verified_date: str = ""
    source_bundle_version: str = ""
    disclaimer: str = "Esta guía es pedagógica. No sustituye el criterio profesional del contador."


@dataclass(frozen=True)
class FieldHotspot:
    field_id: str
    label: str
    page: int
    bbox: tuple[float, float, float, float]
    section: str
    marker_bbox: tuple[float, float, float, float] | None = None
    casilla: int = 0
    año_gravable: str = ""
    profiles: tuple[str, ...] = ()
    instruction_md: str = ""
    official_dian_instruction: str = ""
    what_to_review_before_filling: str = ""
    common_errors: str = ""
    warnings: str = ""
    source_ids: tuple[str, ...] = ()
    last_verified_date: str = ""


@dataclass(frozen=True)
class GuideSource:
    source_id: str
    title: str
    url: str = ""
    source_type: str = "primary"
    authority: str = ""
    is_primary: bool = True
    last_checked_date: str = ""
    notes: str = ""


@dataclass(frozen=True)
class StructuredSection:
    section_id: str
    title: str
    purpose: str = ""
    what_to_review: str = ""
    profile_differences: str = ""
    common_errors: str = ""
    warnings: str = ""
    source_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class GuideCitationProfile:
    lead: str = ""
    purpose_text: str = ""
    mandatory_when: str = ""
    latest_identified: str = ""
    professional_impact: str = ""
    supporting_source_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class GuidePackage:
    manifest: GuideManifest
    interactive_map: tuple[FieldHotspot, ...] = ()
    structured_sections: tuple[StructuredSection, ...] = ()
    sources: tuple[GuideSource, ...] = ()
    pages: tuple[str, ...] = ()
    citation_profile: GuideCitationProfile | None = None


@dataclass(frozen=True)
class GuideCatalogEntry:
    reference_key: str
    title: str
    form_version: str
    available_profiles: tuple[dict[str, str], ...]
    supported_views: tuple[str, ...]
    last_verified_date: str
    download_available: bool
    disclaimer: str


@dataclass(frozen=True)
class GuideChatRequest:
    question: str
    reference_key: str | None = None


def _load_json(path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to load %s: %s", path, exc)
        return None


def _reference_key_to_dir_name(reference_key: str) -> str:
    return str(reference_key or "").strip().replace(":", "_")


def _parse_manifest(data: dict[str, Any]) -> GuideManifest:
    return GuideManifest(
        reference_key=str(data.get("reference_key") or "").strip(),
        title=str(data.get("title") or "").strip(),
        form_version=str(data.get("form_version") or "").strip(),
        profile_id=str(data.get("profile_id") or "").strip(),
        profile_label=str(data.get("profile_label") or "").strip(),
        supported_views=tuple(str(item).strip() for item in data.get("supported_views", ("structured",)) if str(item).strip()),
        last_verified_date=str(data.get("last_verified_date") or "").strip(),
        source_bundle_version=str(data.get("source_bundle_version") or "").strip(),
        disclaimer=str(
            data.get(
                "disclaimer",
                "Esta guía es pedagógica. No sustituye el criterio profesional del contador.",
            )
            or ""
        ).strip(),
    )


def _parse_field_hotspot(data: dict[str, Any]) -> FieldHotspot:
    raw_bbox = data.get("bbox") or (0.0, 0.0, 0.0, 0.0)
    bbox = tuple(float(value) for value in raw_bbox) if isinstance(raw_bbox, (list, tuple)) else (0.0, 0.0, 0.0, 0.0)
    if len(bbox) != 4:
        bbox = (0.0, 0.0, 0.0, 0.0)
    raw_marker_bbox = data.get("marker_bbox")
    marker_bbox: tuple[float, float, float, float] | None = None
    if isinstance(raw_marker_bbox, (list, tuple)):
        parsed_marker_bbox = tuple(float(value) for value in raw_marker_bbox)
        if len(parsed_marker_bbox) == 4:
            marker_bbox = parsed_marker_bbox
    return FieldHotspot(
        field_id=str(data.get("field_id") or "").strip(),
        label=str(data.get("label") or "").strip(),
        page=int(data.get("page") or 0),
        bbox=bbox,
        section=str(data.get("section") or "").strip(),
        marker_bbox=marker_bbox,
        casilla=int(data.get("casilla") or 0),
        año_gravable=str(data.get("año_gravable") or "").strip(),
        profiles=tuple(str(item).strip() for item in data.get("profiles", ()) if str(item).strip()),
        instruction_md=str(data.get("instruction_md") or "").strip(),
        official_dian_instruction=str(data.get("official_dian_instruction") or "").strip(),
        what_to_review_before_filling=str(data.get("what_to_review_before_filling") or "").strip(),
        common_errors=str(data.get("common_errors") or "").strip(),
        warnings=str(data.get("warnings") or "").strip(),
        source_ids=tuple(str(item).strip() for item in data.get("source_ids", ()) if str(item).strip()),
        last_verified_date=str(data.get("last_verified_date") or "").strip(),
    )


def _parse_source(data: dict[str, Any]) -> GuideSource:
    return GuideSource(
        source_id=str(data.get("source_id") or "").strip(),
        title=str(data.get("title") or "").strip(),
        url=str(data.get("url") or "").strip(),
        source_type=str(data.get("source_type") or "primary").strip(),
        authority=str(data.get("authority") or "").strip(),
        is_primary=bool(data.get("is_primary", True)),
        last_checked_date=str(data.get("last_checked_date") or "").strip(),
        notes=str(data.get("notes") or "").strip(),
    )


def _parse_structured_section(data: dict[str, Any]) -> StructuredSection:
    return StructuredSection(
        section_id=str(data.get("section_id") or "").strip(),
        title=str(data.get("title") or "").strip(),
        purpose=str(data.get("purpose") or "").strip(),
        what_to_review=str(data.get("what_to_review") or "").strip(),
        profile_differences=str(data.get("profile_differences") or "").strip(),
        common_errors=str(data.get("common_errors") or "").strip(),
        warnings=str(data.get("warnings") or "").strip(),
        source_ids=tuple(str(item).strip() for item in data.get("source_ids", ()) if str(item).strip()),
    )


def _parse_citation_profile(data: dict[str, Any]) -> GuideCitationProfile:
    return GuideCitationProfile(
        lead=str(data.get("lead") or "").strip(),
        purpose_text=str(data.get("purpose_text") or "").strip(),
        mandatory_when=str(data.get("mandatory_when") or "").strip(),
        latest_identified=str(data.get("latest_identified") or "").strip(),
        professional_impact=str(data.get("professional_impact") or "").strip(),
        supporting_source_ids=tuple(
            str(item).strip() for item in data.get("supporting_source_ids", ()) if str(item).strip()
        ),
    )


def _discover_page_images(guide_dir: Path) -> tuple[str, ...]:
    assets_dir = guide_dir / "assets"
    if not assets_dir.is_dir():
        return ()
    supported_extensions = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
    pages = sorted(
        path.name
        for path in assets_dir.iterdir()
        if path.is_file() and path.suffix.lower() in supported_extensions
    )
    return tuple(pages)


def load_guide_manifest(guide_dir: Path) -> GuideManifest | None:
    data = _load_json(guide_dir / "guide_manifest.json")
    if not isinstance(data, dict):
        return None
    return _parse_manifest(data)


def load_guide_package(guide_dir: Path) -> GuidePackage | None:
    manifest = load_guide_manifest(guide_dir)
    if manifest is None:
        return None

    interactive_data = _load_json(guide_dir / "interactive_map.json")
    interactive_map: tuple[FieldHotspot, ...] = ()
    if isinstance(interactive_data, list):
        interactive_map = tuple(_parse_field_hotspot(item) for item in interactive_data if isinstance(item, dict))
    elif isinstance(interactive_data, dict):
        raw_fields = interactive_data.get("fields", [])
        if isinstance(raw_fields, list):
            interactive_map = tuple(_parse_field_hotspot(item) for item in raw_fields if isinstance(item, dict))

    structured_data = _load_json(guide_dir / "structured_guide.json")
    structured_sections: tuple[StructuredSection, ...] = ()
    if isinstance(structured_data, list):
        structured_sections = tuple(_parse_structured_section(item) for item in structured_data if isinstance(item, dict))
    elif isinstance(structured_data, dict):
        raw_sections = structured_data.get("sections", [])
        if isinstance(raw_sections, list):
            structured_sections = tuple(_parse_structured_section(item) for item in raw_sections if isinstance(item, dict))

    sources_data = _load_json(guide_dir / "sources.json")
    sources: tuple[GuideSource, ...] = ()
    if isinstance(sources_data, list):
        sources = tuple(_parse_source(item) for item in sources_data if isinstance(item, dict))
    elif isinstance(sources_data, dict):
        raw_sources = sources_data.get("sources", [])
        if isinstance(raw_sources, list):
            sources = tuple(_parse_source(item) for item in raw_sources if isinstance(item, dict))

    citation_profile_data = _load_json(guide_dir / "citation_profile.json")
    citation_profile = _parse_citation_profile(citation_profile_data) if isinstance(citation_profile_data, dict) else None

    return GuidePackage(
        manifest=manifest,
        interactive_map=interactive_map,
        structured_sections=structured_sections,
        sources=sources,
        pages=_discover_page_images(guide_dir),
        citation_profile=citation_profile,
    )


def list_available_guides(root: Path = FORM_GUIDES_ROOT) -> list[GuideCatalogEntry]:
    if not root.is_dir():
        return []

    entries_by_key: dict[str, dict[str, Any]] = {}
    for form_dir in sorted(root.iterdir()):
        if not form_dir.is_dir():
            continue
        for profile_dir in sorted(form_dir.iterdir()):
            if not profile_dir.is_dir():
                continue
            manifest = load_guide_manifest(profile_dir)
            if manifest is None or not manifest.reference_key:
                continue
            entry = entries_by_key.setdefault(
                manifest.reference_key,
                {
                    "reference_key": manifest.reference_key,
                    "title": manifest.title,
                    "form_version": manifest.form_version,
                    "available_profiles": [],
                    "supported_views": manifest.supported_views,
                    "last_verified_date": manifest.last_verified_date,
                    "disclaimer": manifest.disclaimer,
                },
            )
            entry["available_profiles"].append(
                {
                    "profile_id": manifest.profile_id,
                    "profile_label": manifest.profile_label,
                }
            )

    return [
        GuideCatalogEntry(
            reference_key=str(entry["reference_key"]),
            title=str(entry["title"]),
            form_version=str(entry["form_version"]),
            available_profiles=tuple(entry["available_profiles"]),
            supported_views=tuple(entry["supported_views"]),
            last_verified_date=str(entry["last_verified_date"]),
            download_available=True,
            disclaimer=str(entry["disclaimer"]),
        )
        for entry in entries_by_key.values()
    ]


def resolve_guide(
    reference_key: str,
    profile: str | None = None,
    root: Path = FORM_GUIDES_ROOT,
) -> GuidePackage | None:
    form_dir = root / _reference_key_to_dir_name(reference_key)
    if not form_dir.is_dir():
        return None

    profile_dirs = [path for path in sorted(form_dir.iterdir()) if path.is_dir()]
    if not profile_dirs:
        return None

    if profile is not None:
        target_dir = form_dir / profile
        return load_guide_package(target_dir) if target_dir.is_dir() else None

    if len(profile_dirs) == 1:
        return load_guide_package(profile_dirs[0])
    return None


def find_official_form_pdf_source(package: GuidePackage | None) -> GuideSource | None:
    if package is None:
        return None

    fallback: GuideSource | None = None
    for source in tuple(package.sources or ()):
        url = str(source.url or "").strip()
        if not url:
            continue
        if fallback is None and source.is_primary:
            fallback = source
        if str(source.source_type or "").strip().lower() in OFFICIAL_FORM_PDF_SOURCE_TYPES:
            return source
    return fallback


def build_guide_markdown_for_pdf(package: GuidePackage) -> str:
    manifest = package.manifest
    lines: list[str] = [
        f"# {manifest.title}",
        "",
        f"**Versión del formulario:** {manifest.form_version}",
        f"**Perfil:** {manifest.profile_label}",
    ]
    if manifest.last_verified_date:
        lines.append(f"**Última verificación:** {manifest.last_verified_date}")
    lines.extend(
        [
            "",
            f"*{manifest.disclaimer}*",
            "",
        ]
    )

    for section in package.structured_sections:
        lines.extend([f"## {section.title}", ""])
        if section.purpose:
            lines.extend([f"**Propósito:** {section.purpose}", ""])
        if section.what_to_review:
            lines.extend([f"**Qué revisar:** {section.what_to_review}", ""])
        if section.profile_differences:
            lines.extend([f"**Diferencias según perfil:** {section.profile_differences}", ""])
        if section.common_errors:
            lines.extend([f"**Errores frecuentes:** {section.common_errors}", ""])
        if section.warnings:
            lines.extend([f"**Advertencias:** {section.warnings}", ""])

    if package.sources:
        lines.extend(["## Fuentes", ""])
        for source in package.sources:
            line = f"- **{source.title}**"
            if source.authority:
                line += f" ({source.authority})"
            if source.url:
                line += f" — {source.url}"
            lines.append(line)
        lines.append("")

    return "\n".join(lines)


def run_guide_chat(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {"ok": False, "error": {"code": "form_guide_unavailable"}}
