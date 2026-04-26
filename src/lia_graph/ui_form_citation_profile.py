"""Citation profile builder for *formulario* references.

Extracted from `ui_citation_profile_builders.py` during granularize-v1
because the host module crossed 2k LOC and this cluster has a self-contained
identity: given a context whose `document_family == "formulario"`, resolve
the matching form-guide package and render a deterministic citation profile
(title, lead, facts, sections) without reaching for the LLM.

Scope:
  * form-number extraction from citation metadata / document rows
  * Spanish-title-casing suited to "Formulario N: Subtítulo"
  * pretty-printing `Formulario / Formato` titles with descriptor fusion
  * row-looks-like-guide heuristic (ops flag used by the companion-action
    resolver in the main builder)
  * the deterministic profile itself

Non-goals: companion/analysis/source-action resolvers — those remain in the
main builder because they compose multiple document families.

Cross-module calls into the main builder (`_normalize_citation_profile_text`,
`_append_citation_profile_fact`) are routed through `_ui()` so the lazy
re-export registry in `ui_server.py` stays the single source of truth.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from .form_guides import resolve_guide

logger = logging.getLogger(__name__)


_CITATION_PROFILE_FORM_RE = re.compile(
    r"\b(?:formulario|formato|f)\.?\s*(\d{2,6})\b", re.IGNORECASE
)

_FORM_TITLE_SMALL_WORDS = {
    "a", "al", "con", "contra", "de", "del", "desde",
    "e", "el", "en",
    "la", "las", "los",
    "o", "para", "por", "sin",
    "u", "un", "una", "y",
}


def _ui() -> Any:
    """Lazy accessor for `lia_graph.ui_server` (avoids circular import)."""
    from . import ui_server as _mod
    return _mod


def _row_looks_like_guide(row: dict[str, Any]) -> bool:
    tipo_documento = str(row.get("tipo_de_documento", "")).strip().lower()
    haystack = " ".join(
        [
            str(row.get("relative_path") or ""),
            str(row.get("notes") or ""),
            str(row.get("title") or ""),
            str(row.get("subtema") or ""),
        ]
    ).lower()
    return (
        tipo_documento == "guia_operativa"
        or "guia" in haystack
        or "guía" in haystack
        or "como diligenciar" in haystack
    )


def _extract_citation_profile_form_number(*values: Any) -> str:
    for value in values:
        match = _CITATION_PROFILE_FORM_RE.search(str(value or ""))
        if match:
            return str(int(match.group(1)))
    return ""


def _spanish_title_case(text: Any) -> str:
    words = re.split(r"(\s+)", str(text or "").strip().lower())
    if not words:
        return ""
    rendered: list[str] = []
    is_first_word = True
    for token in words:
        if not token or token.isspace():
            rendered.append(token)
            continue
        if not is_first_word and token in _FORM_TITLE_SMALL_WORDS:
            rendered.append(token)
        else:
            rendered.append(token[:1].upper() + token[1:])
        is_first_word = False
    return "".join(rendered).strip()


def _format_form_reference_title(base_title: Any, descriptor: Any = "") -> str:
    clean_title = re.sub(r"\s+", " ", str(base_title or "")).strip()
    if not clean_title:
        return ""
    match = re.match(r"^(Formulario|Formato)\s+(\d{2,6})(.*)$", clean_title, re.IGNORECASE)
    if not match:
        return clean_title

    kind = match.group(1).capitalize()
    number = match.group(2)
    title_suffix = re.sub(r"^[\s:,\-–]+", "", str(match.group(3) or "")).strip()
    raw_descriptor = re.sub(r"^[\s:,\-–]+", "", re.sub(r"\s+", " ", str(descriptor or "")).strip())
    descriptor_suffix = raw_descriptor
    descriptor_match = re.match(r"^(Formulario|Formato)\s+(\d{2,6})(.*)$", raw_descriptor, re.IGNORECASE)
    if descriptor_match and descriptor_match.group(2) == number:
        kind = descriptor_match.group(1).capitalize()
        descriptor_suffix = re.sub(r"^[\s:,\-–]+", "", str(descriptor_match.group(3) or "")).strip()
    if descriptor_suffix:
        descriptor_suffix = re.sub(
            rf"^(?:formulario|formato)\s+{re.escape(number)}\b[\s:,\-–]*",
            "",
            descriptor_suffix,
            flags=re.IGNORECASE,
        ).strip()
    suffix = title_suffix or descriptor_suffix
    if not suffix:
        return f"{kind} {number}"
    return f"{kind} {number}: {_spanish_title_case(suffix)}"


def _resolve_form_guide_package_for_context(context: dict[str, Any]) -> Any | None:
    if str(context.get("document_family") or "").strip().lower() != "formulario":
        return None
    citation = dict(context.get("citation") or {})
    row = dict(context.get("requested_row") or {})
    reference_key = str(citation.get("reference_key") or "").strip()
    if not reference_key:
        form_number = _extract_citation_profile_form_number(
            citation.get("source_label"),
            citation.get("legal_reference"),
            row.get("title"),
            row.get("notes"),
            row.get("relative_path"),
            row.get("doc_id"),
        )
        reference_key = f"formulario:{form_number}" if form_number else ""
    if not reference_key:
        return None
    return resolve_guide(reference_key, root=_ui().FORM_GUIDES_ROOT)


def _deterministic_form_citation_profile(context: dict[str, Any]) -> dict[str, Any] | None:
    guide_package = _resolve_form_guide_package_for_context(context)
    citation_profile = (
        getattr(guide_package, "citation_profile", None) if guide_package is not None else None
    )
    if citation_profile is None:
        if str(context.get("document_family") or "").strip().lower() == "formulario":
            citation = dict(context.get("citation") or {})
            reference_key = str(citation.get("reference_key") or "").strip()
            reason = (
                "guide_package_missing"
                if guide_package is None
                else "citation_profile_json_missing"
            )
            logger.warning(
                "formulario citation modal will render empty body: reference_key=%r reason=%s "
                "(expected knowledge_base/form_guides/<dir>/<profile>/citation_profile.json + guide_manifest.json)",
                reference_key,
                reason,
            )
        return None

    title = _ui()._normalize_citation_profile_text(context.get("title"), max_chars=160)
    if not title:
        manifest_title = _ui()._normalize_citation_profile_text(
            getattr(getattr(guide_package, "manifest", None), "title", ""),
            max_chars=160,
        )
        title = _format_form_reference_title(manifest_title) if manifest_title else "Formulario"

    lead = _ui()._normalize_citation_profile_text(citation_profile.lead, max_chars=320)
    if not lead:
        lead = f"{title} es el formulario prescrito para esta obligación tributaria."

    facts: list[dict[str, str]] = []
    _ui()._append_citation_profile_fact(facts, "Para qué sirve", citation_profile.purpose_text)
    _ui()._append_citation_profile_fact(facts, "Desde cuándo es obligatorio", citation_profile.mandatory_when)
    _ui()._append_citation_profile_fact(facts, "Última actualización identificada", citation_profile.latest_identified)

    sections: list[dict[str, str]] = []
    impact = _ui()._normalize_citation_profile_text(citation_profile.professional_impact, max_chars=320)
    if impact:
        sections.append(
            {
                "id": "impacto_profesional",
                "title": "Cómo impacta la labor contable",
                "body": impact,
            }
        )

    return {
        "title": title,
        "lead": lead,
        "facts": facts,
        "sections": sections,
        "supporting_source_ids": [
            str(item).strip()
            for item in list(citation_profile.supporting_source_ids or ())
            if str(item).strip()
        ],
    }
