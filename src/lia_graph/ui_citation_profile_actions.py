"""Action resolvers for the citation-profile modal.

Extracted from `ui_citation_profile_builders.py` during granularize-v2
round 12. The host was 1986 LOC; this cluster is ~200 LOC of
self-contained "decide what each action button does" logic:

  * `_resolve_companion_action` — the "¿Quieres una guía sobre cómo
    llenarlo?" button for formulario citations. Links to the
    interactive form-guide page when one exists, else reports
    `not_applicable`.
  * `_resolve_analysis_action` — the "Abrir análisis normativo" button
    that opens `/normative-analysis?doc_id=…` when the document's UI
    surface profile says `deep_analysis`.
  * `_resolve_source_action` — the "Ir a documento original" button.
    Prefers the MinTIC normograma mirror (fragment-anchor-safe), falls
    back to official URLs synthesized from `ley:`/`decreto:` reference
    keys, and finally to downloadable originals.
  * `_load_decreto_official_urls` / `_lookup_decreto_official_url` —
    cached read of `config/decreto_official_urls.json`.
  * `_synthesize_ley_official_url` — Secretaría del Senado URL builder
    from `ley:NUMBER:YEAR` reference keys.

The 4 user-facing label/helper strings (`_CITATION_PROFILE_GUIDE_PROMPT`
etc.) moved here too because they are only used by these resolvers and
the fallback payload builder that re-imports them. The host re-imports
every name for back-compat and the ui_server lazy registry picks
them up unchanged.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

from .form_guides import resolve_guide


_CITATION_PROFILE_GUIDE_PROMPT = "¿Quieres una guía sobre cómo llenarlo?"
_CITATION_PROFILE_GUIDE_UNAVAILABLE = "Esta guía aún no está disponible"
_CITATION_PROFILE_ORIGINAL_LABEL = "Ir a documento original"
_CITATION_PROFILE_ORIGINAL_DOWNLOAD_HELPER = "Se descargará el archivo fuente original disponible en el repositorio."
_CITATION_PROFILE_ORIGINAL_FALLBACK_HELPER = "No se encontró el original; se abrirá el PDF normalizado disponible en LIA."


def _ui() -> Any:
    """Lazy accessor for `lia_graph.ui_server` (avoids circular import)."""
    from . import ui_server as _mod
    return _mod


def _resolve_companion_action(context: dict[str, Any]) -> dict[str, Any]:
    family = str(context.get("document_family") or "").strip()
    label = _CITATION_PROFILE_GUIDE_PROMPT
    if family != "formulario":
        return {"label": label, "state": "not_applicable", "url": None, "helper_text": None}

    row = dict(context.get("requested_row") or {})
    citation = dict(context.get("citation") or {})
    if _ui()._row_looks_like_guide(row):
        # The document IS a guide — link to the interactive form-guide page if available
        form_number = _ui()._extract_citation_profile_form_number(
            citation.get("reference_key"),
            citation.get("source_label"),
            citation.get("legal_reference"),
            row.get("relative_path"),
            row.get("notes"),
        )
        guide_reference_key = f"formulario:{form_number}" if form_number else ""
        guide_package = resolve_guide(guide_reference_key, root=_ui().FORM_GUIDES_ROOT) if guide_reference_key else None
        if guide_package is not None:
            guide_url = f"/form-guide?reference_key={quote(guide_reference_key, safe='')}"
            return {
                "label": "Ver guía interactiva",
                "state": "available",
                "url": guide_url,
                "helper_text": None,
            }
        return {"label": label, "state": "not_applicable", "url": None, "helper_text": None}

    requested_key = str(citation.get("reference_key", "")).strip()
    form_number = _ui()._extract_citation_profile_form_number(
        citation.get("reference_key"),
        citation.get("source_label"),
        citation.get("legal_reference"),
        row.get("relative_path"),
        row.get("notes"),
    )
    guide_reference_key = f"formulario:{form_number}" if form_number else requested_key
    direct_package = resolve_guide(guide_reference_key, root=_ui().FORM_GUIDES_ROOT) if guide_reference_key else None
    if direct_package is not None:
        guide_url = f"/form-guide?reference_key={quote(guide_reference_key, safe='')}"
        return {
            "label": label,
            "state": "available",
            "url": guide_url,
            "helper_text": None,
        }
    return {
        "label": label,
        "state": "not_applicable",
        "url": None,
        "helper_text": None,
    }


def _resolve_analysis_action(context: dict[str, Any]) -> dict[str, Any]:
    profile_payload = dict(context.get("document_profile") or {})
    ui_surface = str(profile_payload.get("ui_surface") or "").strip().lower()
    family = str(context.get("document_family") or "").strip().lower()
    if not ui_surface:
        ui_surface = "form_guide" if family == "formulario" else "deep_analysis"
    doc_id = str(context.get("doc_id") or "").strip()
    if not doc_id or ui_surface != "deep_analysis":
        return {
            "label": "Abrir análisis normativo",
            "state": "not_applicable",
            "url": None,
            "helper_text": None,
        }
    params = {"doc_id": doc_id}
    citation = dict(context.get("citation") or {})
    for field in ("locator_text", "locator_kind", "locator_start", "locator_end"):
        value = str(citation.get(field) or "").strip()
        if value:
            params[field] = value
    return {
        "label": "Abrir análisis normativo",
        "state": "available",
        "url": f"/normative-analysis?{urlencode(params)}",
        "helper_text": None,
    }


_decreto_official_urls: dict[str, str] | None = None


def _load_decreto_official_urls() -> dict[str, str]:
    """Load decreto number:year -> official URL mapping, caching after first read."""
    global _decreto_official_urls
    if _decreto_official_urls is not None:
        return _decreto_official_urls
    cfg_path = Path(__file__).resolve().parents[2] / "config" / "decreto_official_urls.json"
    if cfg_path.exists():
        try:
            raw = json.loads(cfg_path.read_text(encoding="utf-8"))
            _decreto_official_urls = {k: v for k, v in raw.items() if not k.startswith("_")}
        except Exception:
            _decreto_official_urls = {}
    else:
        _decreto_official_urls = {}
    return _decreto_official_urls


def _lookup_decreto_official_url(context: dict[str, Any]) -> str:
    """Look up the official Función Pública URL for a decreto-family document.

    Returns an empty string if the decree number+year cannot be extracted
    or no mapping exists in config/decreto_official_urls.json.
    """
    citation = dict(context.get("citation") or {})
    ref_key = str(citation.get("reference_key") or "").strip().lower()
    m = re.match(r"^decreto:(\d+):(\d{4})$", ref_key)
    if not m:
        doc_id = str(context.get("doc_id") or citation.get("doc_id") or "").strip().lower()
        m = re.search(r"decreto_0*(\d+)_(\d{4})", doc_id)
    if not m:
        return ""
    number, year = m.group(1).lstrip("0") or "0", m.group(2)
    return _load_decreto_official_urls().get(f"{number}:{year}", "")


def _synthesize_ley_official_url(context: dict[str, Any]) -> str:
    """Construct a Secretaría del Senado URL for ley-family documents.

    Returns an empty string if the reference_key or doc_id doesn't contain
    enough info to build a reliable URL.  Pattern:
    https://www.secretariasenado.gov.co/senado/basedoc/ley_NUMBER_YEAR.html
    """
    citation = dict(context.get("citation") or {})
    ref_key = str(citation.get("reference_key") or "").strip().lower()
    # Try reference_key first (ley:NUMBER:YEAR)
    m = re.match(r"^ley:(\d+):(\d{4})$", ref_key)
    if not m:
        # Fallback: extract from doc_id (e.g. …ley_1819_2016…)
        doc_id = str(context.get("doc_id") or citation.get("doc_id") or "").strip().lower()
        m = re.search(r"ley_(\d+)_(\d{4})", doc_id)
    if not m:
        return ""
    number, year = m.group(1), m.group(2)
    # Secretaría del Senado zero-pads law numbers shorter than 4 digits
    padded = number.zfill(4)
    return f"https://www.secretariasenado.gov.co/senado/basedoc/ley_{padded}_{year}.html"


def _resolve_source_action(context: dict[str, Any]) -> dict[str, Any]:
    citation = dict(context.get("citation") or {})
    family = str(context.get("document_family") or "").strip().lower()
    official_url = _ui()._coerce_http_url(citation.get("official_url"))
    # Prefer MinTIC mirror for DIAN Normograma URLs: the DIAN host does not
    # honor article fragment anchors like #807 on the compiled ET page, but
    # the MinTIC mirror at normograma.mintic.gov.co/mintic/compilacion/docs
    # hosts identical content with working anchors. No-op for non-Normograma
    # URLs. See docs/next/retriever_plusv5.md Part E·3 for context.
    if official_url:
        official_url = _ui()._prefer_normograma_mintic_mirror(official_url)
    # For ET articles, ensure the fragment anchor matches the locator_start
    # (the specific article being viewed). The official_url in the citation
    # may carry a stale or missing anchor when material resolution or data
    # propagation resolved to a different row's URL.
    if official_url and _ui()._citation_targets_et_article(citation):
        _locator = _ui()._citation_et_locator_label(citation)
        if _locator:
            official_url = official_url.split("#")[0] + f"#{_locator}"
    # For ley-family documents without an official_url in the corpus,
    # synthesize one from the reference_key / doc_id pointing to the
    # Secretaría del Senado (the legislature's canonical repository).
    if not official_url and family == "ley":
        official_url = _synthesize_ley_official_url(context)
    if not official_url and family == "decreto":
        official_url = _lookup_decreto_official_url(context)
    download_original_url = _ui()._sanitize_url_candidate(str(citation.get("download_original_url") or "").strip())
    download_url = _ui()._sanitize_url_candidate(str(citation.get("download_url") or "").strip())

    if family == "ley":
        label = "Ver ley original"
    elif family == "decreto":
        label = "Ver decreto original"
    else:
        label = _CITATION_PROFILE_ORIGINAL_LABEL

    if official_url:
        return {
            "label": label,
            "url": official_url,
            "mode": "official_link",
            "helper_text": None,
        }
    if download_original_url:
        return {
            "label": label,
            "url": download_original_url,
            "mode": "original_download",
            "helper_text": _CITATION_PROFILE_ORIGINAL_DOWNLOAD_HELPER,
        }
    return {
        "label": label,
        "url": download_url,
        "mode": "normalized_pdf_fallback",
        "helper_text": _CITATION_PROFILE_ORIGINAL_FALLBACK_HELPER if download_url else None,
    }
