from __future__ import annotations

import json
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

from .citation_resolution import (
    CANONICAL_REFERENCE_RELATION_TYPES,
    document_reference_semantics,
)
from .form_guides import resolve_guide
from .normative_taxonomy import classify_normative_document
from .pipeline_c.orchestrator import generate_llm_strict
from .ui_article_annotations import (
    ANNOTATION_LABELS as _ARTICLE_ANNOTATION_LABELS,
    clean_annotation_body as _clean_article_annotation_body,
    split_article_annotations as _split_article_annotations,
)
from .ui_expert_extractors import _extract_expert_document_metadata
from .ui_form_citation_profile import (
    _deterministic_form_citation_profile,
    _extract_citation_profile_form_number,
    _format_form_reference_title,
    _resolve_form_guide_package_for_context,
    _row_looks_like_guide,
    _spanish_title_case,
)
from .ui_citation_profile_actions import (  # noqa: F401  — re-exported
    _CITATION_PROFILE_GUIDE_PROMPT,
    _CITATION_PROFILE_GUIDE_UNAVAILABLE,
    _CITATION_PROFILE_ORIGINAL_DOWNLOAD_HELPER,
    _CITATION_PROFILE_ORIGINAL_FALLBACK_HELPER,
    _CITATION_PROFILE_ORIGINAL_LABEL,
    _load_decreto_official_urls,
    _lookup_decreto_official_url,
    _resolve_analysis_action,
    _resolve_companion_action,
    _resolve_source_action,
    _synthesize_ley_official_url,
)
from .ui_citation_profile_context import (  # noqa: F401  — re-exported
    _collect_citation_profile_context,
    _collect_citation_profile_context_by_reference_key,
)
from .ui_citation_profile_llm import (  # noqa: F401  — re-exported
    _append_citation_profile_fact,
    _build_citation_profile_facts,
    _build_citation_profile_prompt,
    _llm_citation_profile_payload,
    _should_skip_citation_profile_llm,
)
from .ui_citation_profile_sections import (  # noqa: F401  — re-exported
    _build_citation_profile_expert_section,
    _build_citation_profile_original_text_section,
    _build_citation_profile_sections,
    _citation_profile_analysis_candidates,
    _extract_locator_excerpt_from_text,
    _summarize_analysis_excerpt,
)

# ---------------------------------------------------------------------------
# Module-level constants (moved from ui_server during granularize-v1 1A)
# ---------------------------------------------------------------------------

_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
_PARSED_ARTICLES_PATH = _WORKSPACE_ROOT / "artifacts" / "parsed_articles.jsonl"

# parsed_articles.jsonl aggregates articles from every corpus file — Ley 80,
# Ley 100, CST, ET Libros, etc. — all keyed by bare `article_number`. The ET
# lookup must restrict to ET-corpus source files or it will first-write-wins
# into an unrelated law (e.g. ET Art 1 collided with Ley 80 Art 1 about
# "contratos que celebren las entidades estatales").
_ET_CORPUS_SOURCE_MARKER = "RENTA/NORMATIVA/Normativa/"
_MONTHS_ES = (
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
)
_CITATION_PROFILE_BANNED_HINTS = (
    "doc_id",
    "checksum",
    "storage_partition",
    "pipeline",
    "metadata interna",
    "source_tier",
    "provider",
)

# Spanish stop-words that, if left dangling at the end of a truncated string,
# make the result look broken (e.g. "…de la Ley." or "…del 26 de."). These are
# peeled off during `_tidy_truncated_citation_text` before an ellipsis is added.
_CITATION_PROFILE_TRAILING_STOPWORDS = frozenset({
    "a", "al", "ante", "bajo", "con", "contra", "de", "del", "desde",
    "durante", "e", "el", "en", "entre", "hacia", "hasta", "la", "las",
    "lo", "los", "mediante", "o", "para", "por", "pues", "que", "segun",
    "según", "si", "sin", "so", "sobre", "su", "sus", "tras", "u", "un",
    "una", "unas", "unos", "y", "ya",
})
_CITATION_PROFILE_TRAILING_TRIM_CHARS = " \t\n,;:.-—–"

# Inline ET-article annotation parsing (labels, regex, splitter) lives in
# `ui_article_annotations.py` — pure, side-effect-free, reusable. The names
# are imported above for back-compat with the callers below and with tests
# that referenced the underscored symbols before the granularize extraction.

# ---------------------------------------------------------------------------
# Lazy-import helpers -- these functions live in ui_server today and will
# migrate to their own modules in later granularize phases (1B-1F).
# Using a deferred accessor keeps this module free of circular imports.
# ---------------------------------------------------------------------------

def _ui() -> Any:
    """Lazy accessor for lia_graph.ui_server (avoids circular import)."""
    from . import ui_server as _mod
    return _mod


def _artifact_file_signature(path: Path) -> str:
    try:
        stat = path.stat()
    except OSError:
        return "missing"
    return f"{int(stat.st_mtime_ns)}:{int(stat.st_size)}"


def _normalize_et_article_lookup_key(value: Any) -> str:
    clean = re.sub(r"\s+", "", str(value or "")).strip(" ,:;")
    if not clean:
        return ""
    return clean.replace(".", "-").replace("_", "-")


@lru_cache(maxsize=4)
def _load_parsed_articles_by_key_cached(path_str: str, signature: str) -> dict[str, dict[str, Any]]:
    del signature
    path = Path(path_str)
    rows_by_key: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return rows_by_key
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(row, dict):
                    continue
                # ET-only filter: the sole caller (`_lookup_parsed_et_article`)
                # resolves ET article references. Without this, the bare article
                # numbers collide across laws and first-write-wins returns the
                # wrong source (see `_ET_CORPUS_SOURCE_MARKER` comment above).
                if _ET_CORPUS_SOURCE_MARKER not in str(row.get("source_path", "")):
                    continue
                for candidate in (row.get("article_key"), row.get("article_number")):
                    key = _normalize_et_article_lookup_key(candidate)
                    if key and key not in rows_by_key:
                        rows_by_key[key] = dict(row)
    except OSError:
        return {}
    return rows_by_key


def _load_parsed_articles_by_key(path: Path = _PARSED_ARTICLES_PATH) -> dict[str, dict[str, Any]]:
    return dict(_load_parsed_articles_by_key_cached(str(path.resolve()), _artifact_file_signature(path)))


def _lookup_parsed_et_article(locator_start: str) -> dict[str, Any] | None:
    key = _normalize_et_article_lookup_key(locator_start)
    if not key:
        return None
    row = _load_parsed_articles_by_key().get(key)
    return dict(row) if isinstance(row, dict) else None


def _tidy_truncated_citation_text(original: str, truncated: str) -> str:
    """Polish a clipped citation-profile string.

    When `_clip_session_content` had to shorten the text, its boundary-detection
    can still leave dangling short words (e.g. `…de la Ley.` or `…del 26 de.`)
    that make the modal look broken. This helper drops trailing Spanish
    stop-words that survive a clip and appends a single ellipsis so the reader
    sees an explicit truncation marker instead of a fragment. If the clipped
    text already ends on legitimate punctuation or a substantive word, it is
    returned unchanged.
    """
    if not truncated:
        return ""
    if len(truncated) >= len(original):
        return truncated
    polished = truncated.rstrip(_CITATION_PROFILE_TRAILING_TRIM_CHARS)
    # Peel off dangling stop-words one at a time (bounded loop so a pathological
    # all-stop-words fragment does not run away).
    for _ in range(8):
        match = re.search(r"(?:^|\s)(\S+)$", polished)
        if not match:
            break
        token = match.group(1).strip(_CITATION_PROFILE_TRAILING_TRIM_CHARS).lower()
        if not token or token not in _CITATION_PROFILE_TRAILING_STOPWORDS:
            break
        polished = polished[: match.start()].rstrip(_CITATION_PROFILE_TRAILING_TRIM_CHARS)
        if not polished:
            break
    if not polished:
        return ""
    if not polished.endswith(("…", "...", ".", "!", "?")):
        polished = f"{polished}…"
    return polished


def _normalize_citation_profile_text(value: Any, *, max_chars: int = 280) -> str:
    prepared = _ui()._clean_markdown_inline(str(value or "").strip())
    clean = _ui()._clip_session_content(prepared, max_chars=max_chars)
    if not clean:
        return ""
    lowered = clean.lower()
    if any(hint in lowered for hint in _CITATION_PROFILE_BANNED_HINTS):
        return ""
    if re.search(r"\bpart[_\s-]?\d+\b", lowered):
        return ""
    if re.search(r"\b[0-9a-f]{8}\b", lowered):
        return ""
    return _tidy_truncated_citation_text(prepared, clean)


def _extract_expert_body_metadata(context: dict[str, Any]) -> dict[str, str]:
    """Extract structured metadata from expert document body text in the context."""
    material = context.get("material") or {}
    for candidate in (
        str(material.get("public_text") or ""),
        str(material.get("usable_text") or ""),
        str(material.get("raw_text") or ""),
    ):
        if not candidate.strip():
            continue
        meta = _extract_expert_document_metadata(candidate)
        if meta:
            return meta
    return {}


def _collect_citation_profile_texts(context: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    material = context.get("material") or {}
    for candidate in (
        str(material.get("usable_text") or ""),
        str(material.get("public_text") or ""),
    ):
        clean = _ui()._extract_source_view_usable_text(candidate) or _ui()._normalize_citation_profile_text(candidate, max_chars=7000)
        if clean:
            texts.append(clean)
    # Supplement with structured sections from RAG-ready markdown when
    # the primary sources yielded thin text (decreto/resolucion docs).
    # Prefer requested_raw_text (the actual document) over material raw_text
    # which may be from a different document due to provenance_uri collisions.
    if all(len(t) < 200 for t in texts):
        raw_text = str(context.get("requested_raw_text") or "") or str(material.get("raw_text") or "")
        if raw_text:
            section_map = _ui()._markdown_section_map(raw_text)
            for section_key in (
                "texto base referenciado (resumen tecnico)",
                "texto base referenciado (resumen técnico)",
                "condiciones de aplicacion",
                "condiciones de aplicación",
                "riesgos de interpretacion",
                "riesgos de interpretación",
                "regla operativa para lia",
            ):
                section_text = section_map.get(section_key, "")
                # Skip scaffold placeholder text
                if "scaffold debe evolucionar" in section_text.lower():
                    continue
                clean = _ui()._normalize_citation_profile_text(section_text, max_chars=2000)
                if clean:
                    texts.append(clean)
    for analysis in list(context.get("related_analyses") or []):
        clean = _ui()._extract_source_view_usable_text(str(analysis.get("public_text") or "")) or str(analysis.get("usable_text") or "").strip()
        if clean:
            texts.append(clean)
    return texts


def _find_grounded_profile_sentence(
    texts: list[str],
    *,
    keywords: tuple[str, ...],
    max_chars: int = 240,
) -> str:
    best_sentence = ""
    best_score = 0
    for text in texts:
        for sentence in _ui()._split_sentences(text):
            lowered = sentence.lower()
            score = sum(1 for keyword in keywords if keyword in lowered)
            if score > best_score:
                best_score = score
                best_sentence = sentence
    if best_score <= 0:
        return ""
    return _ui()._normalize_citation_profile_text(best_sentence, max_chars=max_chars)


def _classify_document_family(citation: dict[str, Any], row: dict[str, Any] | None = None) -> str:
    return classify_normative_document(
        citation if isinstance(citation, dict) else {},
        row if isinstance(row, dict) else {},
    ).document_family


def _format_citation_profile_date(value: Any) -> str:
    clean = str(value or "").strip()
    if not clean:
        return ""
    try:
        parsed = datetime.fromisoformat(clean)
    except ValueError:
        return clean
    d = parsed.date()
    return f"{_MONTHS_ES[d.month - 1]} {d.day}, {d.year}"


def _latest_identified_citation_profile_date(rows: list[dict[str, Any]]) -> str:
    iso_dates = []
    for row in rows:
        for field in ("publish_date", "effective_date"):
            raw = str(row.get(field) or "").strip()
            if not raw:
                continue
            try:
                iso_dates.append(datetime.fromisoformat(raw).date().isoformat())
            except ValueError:
                pass
    return _ui()._format_citation_profile_date(max(iso_dates)) if iso_dates else ""


_LEY_YEAR_RE = re.compile(r"(?:ley|decreto|resolucion|circular)[:\s_]+\d+[:\s_]+(\d{4})", re.IGNORECASE)
_LEY_TITLE_YEAR_RE = re.compile(r"(?:Ley|Decreto|Resolución|Circular)\s+\d+\s+de\s+(\d{4})", re.IGNORECASE)
_DOC_ID_YEAR_RE = re.compile(r"co_(?:ley|decreto|resolucion|circular)_\d+_(\d{4})")


def _extract_normative_year(context: dict[str, Any]) -> str:
    """Extract the official year of a normative document from reference_key, doc_id, or title.

    Returns a 4-digit year string or "" if not determinable.
    """
    citation = dict(context.get("citation") or {})
    for source in (
        str(citation.get("reference_key") or ""),
        str(context.get("doc_id") or citation.get("doc_id") or ""),
    ):
        m = _LEY_YEAR_RE.search(source)
        if m:
            return m.group(1)
        m = _DOC_ID_YEAR_RE.search(source)
        if m:
            return m.group(1)
    for source in (
        str(context.get("title") or ""),
        str(dict(context.get("requested_row") or {}).get("notes") or ""),
    ):
        m = _LEY_TITLE_YEAR_RE.search(source)
        if m:
            return m.group(1)
    return ""


def _official_publish_date_or_year(publish_date_raw: str, normative_year: str) -> str:
    """Return the formatted publish_date if its year matches the normative year.

    When the publish_date year doesn't match (i.e. it's the ingestion date, not
    the law's real date), fall back to "Año {year}".  Returns "" if neither is
    available.
    """
    clean = str(publish_date_raw or "").strip()
    if clean and normative_year:
        try:
            pd_year = str(datetime.fromisoformat(clean).year)
        except ValueError:
            pd_year = ""
        if pd_year == normative_year:
            return _ui()._format_citation_profile_date(clean)
        return f"Año {normative_year}"
    if clean:
        return _ui()._format_citation_profile_date(clean)
    if normative_year:
        return f"Año {normative_year}"
    return ""


def _resolve_superseded_label(row: dict[str, Any], rows_by_doc_id: dict[str, dict[str, Any]]) -> str:
    superseded_by = str(row.get("superseded_by", "")).strip()
    if not superseded_by:
        return ""
    replacement = rows_by_doc_id.get(superseded_by)
    if not replacement:
        return "Tiene reemplazo registrado."
    replacement_material = _ui()._resolve_source_view_material(doc_id=superseded_by, view="normalized")
    if replacement_material:
        return _ui()._pick_source_display_title(
            requested_row=replacement,
            resolved_row=dict(replacement_material.get("resolved_row") or replacement),
            doc_id=superseded_by,
            raw_text=str(replacement_material.get("raw_text") or ""),
            public_text=str(replacement_material.get("public_text") or ""),
        )
    return _ui()._normalize_citation_profile_text(str(replacement.get("notes") or replacement.get("title") or "").strip(), max_chars=120)



def _build_fallback_citation_profile_payload(
    *,
    doc_id: str = "",
    reference_key: str = "",
    message_context: str = "",
    locator_text: str = "",
    locator_kind: str = "",
    locator_start: str = "",
    locator_end: str = "",
) -> dict[str, Any]:
    del doc_id, message_context, locator_text, locator_kind, locator_end

    normalized_reference_key = str(reference_key or "").strip().lower()
    locator_display = _normalize_et_article_lookup_key(locator_start)
    if normalized_reference_key != "et" or not locator_display:
        return {}

    citation = {
        "reference_key": "et",
        "reference_type": "et",
        "locator_start": locator_display,
        "locator_text": f"Artículo {locator_display}",
        "source_label": "Estatuto Tributario",
        "legal_reference": "Estatuto Tributario",
    }
    document_profile = classify_normative_document(citation, {}).to_public_dict()

    parsed_article = _lookup_parsed_et_article(locator_display)
    heading = _normalize_citation_profile_text((parsed_article or {}).get("heading"), max_chars=180).rstrip(".")
    if heading:
        lead = _normalize_citation_profile_text(
            f"El Artículo {locator_display} del Estatuto Tributario regula {heading.lower()}.",
            max_chars=320,
        )
    else:
        lead = _normalize_citation_profile_text(
            f"Revisa el Artículo {locator_display} del Estatuto Tributario como referencia normativa base para esta consulta.",
            max_chars=320,
        )

    facts = [
        {
            "label": "Artículo consultado",
            "value": f"ET Artículo {locator_display}" + (f". {heading}." if heading else ""),
        }
    ]

    original_text: dict[str, Any] | None = None
    raw_quote = str((parsed_article or {}).get("full_text") or (parsed_article or {}).get("body") or "").strip()
    if raw_quote:
        raw_quote = raw_quote.split("\n---\n", 1)[0].strip()
        raw_body, annotations = _split_article_annotations(raw_quote)
        cleaned_body = _ui()._clean_markdown_inline(raw_body)
        clipped_body = _ui()._clip_session_content(cleaned_body, max_chars=1100)
        quote = _tidy_truncated_citation_text(cleaned_body, clipped_body)
        if quote:
            original_text = {
                "title": "Texto Normativo",
                "quote": quote,
                "annotations": annotations,
                "source_url": _ui()._prefer_normograma_mintic_mirror(
                    f"https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm#{locator_display}"
                ),
                "evidence_status": "verified",
            }

    source_url = _ui()._prefer_normograma_mintic_mirror(
        f"https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm#{locator_display}"
    )
    source_action = {
        "label": _CITATION_PROFILE_ORIGINAL_LABEL,
        "state": "available",
        "url": source_url,
        "helper_text": None,
    }

    corpus_gap = original_text is None
    caution_banner: dict[str, Any] | None = dict(document_profile.get("caution_banner") or {}) or None
    if corpus_gap:
        lead = _normalize_citation_profile_text(
            f"No tenemos el texto del Artículo {locator_display} del Estatuto Tributario en el corpus "
            "local. Consulta la fuente oficial para el contenido verbatim.",
            max_chars=320,
        )
        caution_banner = {
            "title": "Texto no disponible en el corpus",
            "body": (
                f"El texto del Artículo {locator_display} del Estatuto Tributario no está en el "
                "corpus local de Lia. Puedes abrirlo en la fuente oficial (DIAN / Normograma) con "
                "el botón «Ir a documento original»."
            ),
            "tone": "warning",
        }

    return {
        "title": f"Estatuto Tributario, Artículo {locator_display}",
        "document_family": str(document_profile.get("document_family") or "et_dur").strip(),
        "family_subtype": str(document_profile.get("family_subtype") or "").strip(),
        "hierarchy_tier": str(document_profile.get("hierarchy_tier") or "").strip(),
        "binding_force": str(document_profile.get("binding_force") or "").strip(),
        "binding_force_rank": int(document_profile.get("binding_force_rank") or 0),
        "analysis_template_id": str(document_profile.get("analysis_template_id") or "").strip(),
        "ui_surface": str(document_profile.get("ui_surface") or "").strip(),
        "allowed_secondary_overlays": list(document_profile.get("allowed_secondary_overlays") or []),
        "lead": lead,
        "facts": facts,
        "sections": [],
        "original_text": original_text,
        "vigencia_detail": None,
        "expert_comment": None,
        "additional_depth_sections": None,
        "caution_banner": caution_banner,
        "corpus_gap": corpus_gap,
        "analysis_action": {
            "label": "Abrir análisis normativo",
            "state": "not_applicable",
            "url": None,
            "helper_text": None,
        },
        "companion_action": {
            "label": _CITATION_PROFILE_GUIDE_PROMPT,
            "state": "not_applicable",
            "url": None,
            "helper_text": None,
        },
        "source_action": source_action,
    }



def _build_citation_profile_lead(context: dict[str, Any], llm_payload: dict[str, str] | None = None) -> str:
    payload = dict(llm_payload or {})
    family = str(context.get("document_family") or "generic").strip()
    title = _ui()._normalize_citation_profile_text(context.get("title"), max_chars=140) or "El documento seleccionado"
    citation = dict(context.get("citation") or {})
    # For ET articles, prefer the deterministic lead (based on locator
    # resolution) over the LLM lead.  The LLM prompt receives `material`
    # text which may come from a different ET row due to provenance-URI
    # collisions, producing a lead about the wrong article.  The locator
    # analysis resolves by doc_id + locator_start and always finds the
    # correct article text.
    if _ui()._citation_targets_et_article(citation):
        analysis = _ui()._resolve_et_locator_analysis(context)
        raw_text = str((analysis or {}).get("raw_text") or "")
        metadata = _ui()._extract_et_article_metadata(raw_text) if analysis else {}
        article_display = str(metadata.get("article_number_display") or _ui()._citation_et_locator_label(citation)).strip()
        summary_text = _ui()._extract_et_article_summary(raw_text) if raw_text else ""
        if article_display:
            if summary_text:
                clean_summary = summary_text.strip().rstrip(".")
                if clean_summary:
                    normalized_summary = (
                        f"{clean_summary[:1].lower()}{clean_summary[1:]}"
                        if clean_summary[:1].isupper()
                        else clean_summary
                    )
                    return f"El Artículo {article_display} del Estatuto Tributario establece que {normalized_summary}."
            return f"El Artículo {article_display} del Estatuto Tributario es la referencia normativa consultada."

    lead = _ui()._normalize_citation_profile_text(payload.get("lead"), max_chars=320)
    if lead:
        return lead
    # For decreto/ley/resolucion: try extracting the "resumen tecnico" summary
    # from the RAG-ready markdown, which is a curated one-liner about
    # what the document does — much better than generic sentence grounding.
    if family in {"decreto", "ley", "resolucion"}:
        raw_text = str(context.get("requested_raw_text") or "") or str((context.get("material") or {}).get("raw_text") or "")
        if raw_text:
            section_map = _ui()._markdown_section_map(raw_text)
            resumen = (
                section_map.get("texto base referenciado (resumen tecnico)")
                or section_map.get("texto base referenciado (resumen técnico)")
                or ""
            )
            if resumen and "scaffold debe evolucionar" not in resumen.lower():
                # Extract a clean summary sentence from the resumen section
                resumen_lead = _ui()._find_grounded_profile_sentence(
                    [resumen],
                    keywords=("establece", "reglamenta", "modifica", "fija", "plazos", "obligación", "obligacion", "define"),
                    max_chars=320,
                )
                if resumen_lead:
                    return resumen_lead

    texts = _ui()._collect_citation_profile_texts(context)
    keywords_by_family = {
        "formulario": ("sirve", "utiliza", "diligenciar", "presentar", "declaración", "declaracion", "formulario"),
        "constitucion": ("constitución", "constitucion", "principio", "garantiza", "reserva", "debido proceso"),
        "ley": ("regula", "establece", "define", "dispone", "objeto"),
        "decreto": ("regula", "establece", "define", "dispone", "objeto"),
        "resolucion": ("establece", "define", "regula", "fija", "dispone"),
        "et_dur": ("regula", "establece", "define", "compila", "dispone"),
        "concepto": ("criterio", "aclara", "precisa", "interpreta", "indica"),
        "circular": ("lineamiento", "instruye", "indica", "establece"),
        "jurisprudencia": ("problema", "controversia", "resolv", "decid", "analiza"),
        "generic": ("establece", "define", "explica", "sirve"),
    }
    grounded = _ui()._find_grounded_profile_sentence(texts, keywords=keywords_by_family.get(family, ("establece", "sirve")))
    if grounded:
        return grounded

    fallback_by_family = {
        "formulario": f"{title} es el formulario seleccionado para esta consulta tributaria.",
        "constitucion": f"{title} es la referencia constitucional seleccionada para revisar el marco superior aplicable.",
        "ley": f"{title} es la ley seleccionada para revisar el marco aplicable a esta consulta.",
        "decreto": f"{title} es el decreto seleccionado para revisar el marco aplicable a esta consulta.",
        "resolucion": f"{title} es la resolución seleccionada para revisar el marco aplicable a esta consulta.",
        "et_dur": f"{title} es la referencia normativa seleccionada para revisar el marco aplicable a esta consulta.",
        "concepto": f"{title} es el criterio administrativo seleccionado para esta consulta.",
        "circular": f"{title} es la circular seleccionada como soporte para esta consulta.",
        "jurisprudencia": f"{title} es la decisión judicial seleccionada como soporte.",
        "generic": f"{title} es el documento seleccionado como soporte de esta consulta.",
    }
    return fallback_by_family.get(family, fallback_by_family["generic"])


def _citation_profile_display_title(context: dict[str, Any]) -> str:
    citation = dict(context.get("citation") or {})
    citation_title = _ui()._normalize_citation_profile_text(
        citation.get("legal_reference") or citation.get("source_label") or context.get("title"),
        max_chars=180,
    )
    context_title = _ui()._normalize_citation_profile_text(context.get("title"), max_chars=180)
    base_title = citation_title
    if context_title and _ui()._is_broad_normative_reference_title(citation_title):
        base_title = context_title
    locator_text = _ui()._normalize_citation_profile_text(citation.get("locator_text"), max_chars=80)
    if base_title and locator_text and locator_text.lower() not in base_title.lower():
        return f"{base_title}, {locator_text}"
    if base_title:
        return base_title
    # Fallback: extract "Tema principal" from expert document body text
    expert_meta = _extract_expert_body_metadata(context)
    tema = expert_meta.get("tema_principal", "").strip()
    if tema:
        return tema[:180] if len(tema) > 180 else tema
    # Last resort: humanize the technical context title
    raw_title = str(context.get("title") or "").strip()
    if raw_title:
        humanized = _ui()._humanize_technical_title(raw_title)
        if humanized:
            return humanized
    return "Documento"


def _citation_locator_reference_keys(citation: dict[str, Any]) -> tuple[str, ...]:
    reference_key = str(citation.get("reference_key") or "").strip().lower()
    locator_start = str(citation.get("locator_start") or "").strip().lower()
    if reference_key.startswith("ley:"):
        return (reference_key,)
    if reference_key != "et" or not locator_start:
        return ()

    variants: list[str] = []
    canonical = re.sub(r"[_\-.]+", "_", locator_start).strip("_")
    for candidate in (
        f"et_art_{canonical}",
        f"et_art_{locator_start}",
        f"et_art_{locator_start.replace('-', '.')}",
    ):
        clean = candidate.strip()
        if clean and clean not in variants:
            variants.append(clean)
    return tuple(variants)



def _build_structured_original_text(context: dict[str, Any]) -> dict[str, Any] | None:
    citation = dict(context.get("citation") or {})
    if not _ui()._citation_targets_et_article(citation) and not _ui()._citation_targets_ley(citation):
        return None
    section = _ui()._build_citation_profile_original_text_section(context)
    if section is None:
        return None
    raw_body = str(section.get("body") or "").strip()
    body_text, annotations = _split_article_annotations(raw_body)
    quote = body_text.strip() if body_text else raw_body
    return {
        "title": "Texto Normativo",
        "quote": quote,
        "annotations": annotations,
        "source_url": str(section.get("source_url") or "").strip() or None,
        "evidence_status": str(section.get("evidence_status") or "missing").strip() or "missing",
    }


def _build_structured_vigencia_detail(context: dict[str, Any]) -> dict[str, Any] | None:
    citation = dict(context.get("citation") or {})
    if _ui()._citation_targets_et_article(citation):
        detail = _ui()._build_et_article_vigencia_detail(context)
        return {
            "label": str(detail.get("label") or "Vigencia específica").strip(),
            "basis": str(detail.get("basis") or "").strip(),
            "notes": str(detail.get("notes") or "").strip(),
            "last_verified_date": str(detail.get("last_verified_date") or "").strip(),
            "evidence_status": str(detail.get("evidence_status") or "missing").strip() or "missing",
        }
    if _ui()._citation_targets_ley(citation):
        return None
    return None


def _build_structured_expert_comment(context: dict[str, Any]) -> dict[str, Any] | None:
    citation = dict(context.get("citation") or {})
    if not _ui()._citation_targets_et_article(citation) and not _ui()._citation_targets_ley(citation):
        return None
    section = _ui()._build_citation_profile_expert_section(context)
    if section is None:
        return None
    return {
        "topic_label": str(section.get("topic_label") or section.get("source_label") or section.get("title") or "").strip(),
        "body": str(section.get("body") or "").strip(),
        "source_label": str(section.get("source_label") or "").strip() or None,
        "source_url": str(section.get("source_url") or "").strip() or None,
        "accordion_default": str(section.get("accordion_default") or "closed").strip() or "closed",
        "evidence_status": str(section.get("evidence_status") or "missing").strip() or "missing",
    }


def _apply_citation_profile_request_context(
    context: dict[str, Any],
    *,
    message_context: str = "",
    locator_text: str = "",
    locator_kind: str = "",
    locator_start: str = "",
    locator_end: str = "",
) -> dict[str, Any]:
    updated = dict(context)
    citation = dict(updated.get("citation") or {})
    reference_detail = {
        "reference_text": _ui()._reference_base_text_for_request_context(citation),
        "locator_text": locator_text,
        "locator_kind": locator_kind,
        "locator_start": locator_start,
        "locator_end": locator_end,
    }
    if any(str(reference_detail.get(field) or "").strip() for field in ("locator_text", "locator_kind", "locator_start", "locator_end")):
        citation = _ui()._apply_reference_detail_to_citation(citation, reference_detail=reference_detail)
        updated["title"] = _ui()._citation_profile_display_title({"citation": citation, "title": updated.get("title")})
    updated["citation"] = citation
    updated["message_context"] = _ui()._sanitize_question_context(message_context, max_chars=320)
    return updated


def _render_citation_profile_payload(context: dict[str, Any], llm_payload: dict[str, str] | None = None) -> dict[str, Any]:
    document_profile = dict(context.get("document_profile") or {})
    if not document_profile:
        seed_citation = dict(context.get("citation") or {})
        if not str(seed_citation.get("reference_type") or "").strip():
            seed_citation["reference_type"] = str(context.get("document_family") or "").strip()
        document_profile = classify_normative_document(
            seed_citation,
            dict(context.get("requested_row") or {}),
        ).to_public_dict()

    deterministic_form = _ui()._deterministic_form_citation_profile(context)
    if deterministic_form is not None:
        lead = str(deterministic_form.get("lead") or "").strip()
        facts = list(deterministic_form.get("facts") or [])
        sections = list(deterministic_form.get("sections") or [])
        title = str(deterministic_form.get("title") or context.get("title") or "Documento").strip()
        supporting_source_ids = list(deterministic_form.get("supporting_source_ids") or [])
    else:
        lead = _ui()._build_citation_profile_lead(context, llm_payload=llm_payload)
        facts = _ui()._build_citation_profile_facts(context, llm_payload=llm_payload)
        sections = _ui()._build_citation_profile_sections(context, llm_payload=llm_payload)
        title = _ui()._citation_profile_display_title(context)
        supporting_source_ids = []
    original_text = _ui()._build_structured_original_text(context)
    vigencia_detail = _ui()._build_structured_vigencia_detail(context)
    expert_comment = _ui()._build_structured_expert_comment(context)
    additional_depth_sections = _ui()._build_structured_additional_depth_sections(context)
    return {
        "title": title,
        "document_family": str(context.get("document_family") or "generic").strip(),
        "family_subtype": str(document_profile.get("family_subtype") or "").strip(),
        "hierarchy_tier": str(document_profile.get("hierarchy_tier") or "").strip(),
        "binding_force": str(document_profile.get("binding_force") or "").strip(),
        "binding_force_rank": int(document_profile.get("binding_force_rank") or 0),
        "analysis_template_id": str(document_profile.get("analysis_template_id") or "").strip(),
        "ui_surface": str(document_profile.get("ui_surface") or "").strip(),
        "allowed_secondary_overlays": list(document_profile.get("allowed_secondary_overlays") or []),
        "lead": lead,
        "facts": facts,
        "sections": sections,
        "original_text": original_text,
        "vigencia_detail": vigencia_detail,
        "expert_comment": expert_comment,
        "additional_depth_sections": additional_depth_sections,
        "supporting_source_ids": supporting_source_ids or None,
        "caution_banner": dict(document_profile.get("caution_banner") or {}) or None,
        "analysis_action": _ui()._resolve_analysis_action(context),
        "companion_action": _ui()._resolve_companion_action(context),
        "source_action": _ui()._resolve_source_action(context),
    }
