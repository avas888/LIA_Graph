"""Noise detection and content-marker trimming for scraped source text.

Extracted from `ui_source_view_processors.py` during granularize-v2
round 8 to graduate the host file below 1000 LOC. The cluster has a
single self-contained identity: **given raw text scraped from an HTML
document (typically normograma DIAN pages), strip UI chrome and
metadata scaffolding so downstream readers see only usable prose**.

The three canonical hint sets describe what we drop:

  * `_SOURCE_VIEW_CONTENT_MARKERS` — article-body-start markers
    ("contenido principal", etc). Everything before the marker is
    trimmed off.
  * `_SOURCE_VIEW_NON_USABLE_HINTS` — scaffolding phrases that flag a
    "seed" document or internal template (dropped wholesale when seen).
  * `_SOURCE_VIEW_HTML_NOISE_HINTS` — DIAN-portal-specific chrome
    ("icono twitter", "portal dian", "active javascript", ...).
  * `_SOURCE_VIEW_USEFUL_HINT_RE` — rescue regex: if a paragraph
    contains tax-relevant terms (formulario / declaración / renta /
    etc.) we keep it even when short.

Public surface is four names: the three constants plus
`_SOURCE_VIEW_USEFUL_HINT_RE`, and the three functions
`_trim_source_view_content_markers`, `_is_source_view_noise_text`,
`_extract_source_view_usable_text`. `ui_source_view_processors.py`
re-imports all of them so eager callers keep working; the ui_server
lazy registry points lookups at this module.
"""

from __future__ import annotations

import html
import re
from typing import Any


_SOURCE_VIEW_CONTENT_MARKERS = (
    "contenido de la página",
    "contenido principal",
)
_SOURCE_VIEW_NON_USABLE_HINTS = (
    "resumen tecnico inicial para seed documental",
    "este scaffold debe evolucionar",
    "claim en construccion",
    "claim en construcción",
    "regla operativa para lia",
    "condiciones de aplicacion",
    "condiciones de aplicación",
    "riesgos de interpretacion",
    "riesgos de interpretación",
    "relaciones normativas",
    "checklist de vigencia",
    "historico de cambios",
    "histórico de cambios",
    "ambito:",
    "ámbito:",
    "uso permitido:",
    "fuente principal enlazada:",
    "migrado desde",
)
_SOURCE_VIEW_HTML_NOISE_HINTS = (
    "¿sabes que es gov.co?",
    "conócelo aquí",
    "icono twitter",
    "icono youtube",
    "icono linkedin",
    "icono facebook",
    "icono instagram",
    "icono tiktok",
    "parece que el explorador no tiene javascript habilitado",
    "active javascript e inténtelo de nuevo",
    "active javascript e intentelo de nuevo",
    "icono cambio de idioma",
    "icono aumento de tamaño de texto",
    "icono aumento de tamano de texto",
    "icono tamaño de texto normal",
    "icono tamano de texto normal",
    "icono disminución del tamaño de texto",
    "icono disminucion del tamano de texto",
    "alto contraste",
    "portal dian",
    "actualmente seleccionado",
    "atención y servicios a la ciudadanía",
    "atencion y servicios a la ciudadania",
    "la ubicación de esta página es",
    "la ubicacion de esta pagina es",
    "<option value=",
    "</option>",
    "bookmarkaj",
    "javascript:insrow",
    "concordancias",
    "doctrina concordante",
    "legislación anterior",
    "legislacion anterior",
    "jurisprudencia vigencia",
    "notas de vigencia",
)
_SOURCE_VIEW_USEFUL_HINT_RE = re.compile(
    r"\b(formulario|declaraci[oó]n|renta|impuesto|impuestos|diligenciar|presentar|pagar|"
    r"persona(?:s)?\s+jur[ií]dica(?:s)?|no\s+residentes|ingresos\s+y\s+patrimonio|"
    r"resoluci[oó]n|obligaciones?\s+tributarias?)\b",
    re.IGNORECASE,
)


def _ui() -> Any:
    """Lazy accessor for `lia_graph.ui_server` (avoids circular import)."""
    from . import ui_server as _mod
    return _mod


def _trim_source_view_content_markers(text: str) -> str:
    clean = str(text or "").strip()
    if not clean:
        return ""
    lowered = clean.lower()
    for marker in _SOURCE_VIEW_CONTENT_MARKERS:
        idx = lowered.find(marker)
        if idx >= 0:
            trimmed = clean[idx + len(marker) :].strip(" :.-\n")
            if trimmed:
                clean = trimmed
                lowered = clean.lower()
                break
    return clean


def _is_source_view_noise_text(text: str) -> bool:
    lowered = re.sub(r"\s+", " ", str(text or "").lower()).strip()
    if not lowered:
        return True
    if any(hint in lowered for hint in _SOURCE_VIEW_NON_USABLE_HINTS):
        return True
    if any(hint in lowered for hint in _SOURCE_VIEW_HTML_NOISE_HINTS):
        return True
    if lowered.count("icono ") >= 2:
        return True
    if "portal dian" in lowered and not _SOURCE_VIEW_USEFUL_HINT_RE.search(lowered):
        return True
    return False


def _extract_source_view_usable_text(public_text: str) -> str:
    normalized = str(public_text or "").replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.strip():
        return ""

    if _ui()._looks_like_html_document(normalized):
        normalized = _ui()._extract_visible_text_from_html(normalized)

    normalized = html.unescape(normalized).replace("\xa0", " ")
    normalized = _trim_source_view_content_markers(normalized)
    paragraphs: list[str] = []
    seen: set[str] = set()

    for block in re.split(r"\n{2,}", normalized):
        clean = _ui()._clean_markdown_inline(_trim_source_view_content_markers(block))
        clean = re.sub(r"\s+", " ", clean).strip(" -:\n\t")
        if not clean:
            continue
        if _ui()._SOURCE_METADATA_LINE_RE.match(clean):
            continue
        if _ui()._SOURCE_INTERNAL_BOUNDARY_RE.match(clean):
            break
        if _is_source_view_noise_text(clean):
            continue
        if len(clean) < 30 and not _SOURCE_VIEW_USEFUL_HINT_RE.search(clean):
            continue
        key = clean.lower()
        if key in seen:
            continue
        seen.add(key)
        paragraphs.append(clean)
        if len(paragraphs) >= 12:
            break

    if not paragraphs:
        sentence_candidates = re.split(r"(?<=[\.\!\?])\s+", normalized)
        for sentence in sentence_candidates:
            clean = _ui()._clean_markdown_inline(_trim_source_view_content_markers(sentence))
            clean = re.sub(r"\s+", " ", clean).strip(" -:\n\t")
            if not clean or _is_source_view_noise_text(clean):
                continue
            if len(clean) < 24 and not _SOURCE_VIEW_USEFUL_HINT_RE.search(clean):
                continue
            key = clean.lower()
            if key in seen:
                continue
            seen.add(key)
            paragraphs.append(clean)
            if len(paragraphs) >= 12:
                break

    return "\n\n".join(paragraphs).strip()
