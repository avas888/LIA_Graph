from __future__ import annotations

import html
import re
from typing import Any

from .contracts import DocumentRecord
from .expert_providers import (
    extract_expert_providers,
    provider_labels as normalize_provider_labels,
    provider_names_from_label,
)

_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]{1,180})\]\((https?://[^)\s]+)\)", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Lazy-import helpers -- functions that still live in ui_server today.
# Using a deferred accessor avoids circular imports and ensures that
# monkeypatch.setattr(ui_server, ...) in tests is honoured.
# ---------------------------------------------------------------------------


def _ui() -> Any:
    """Lazy accessor for lia_graph.ui_server (avoids circular import)."""
    from . import ui_server as _mod
    return _mod


# ---------------------------------------------------------------------------
# Sibling-module accessors (avoid circular import with other extracted
# modules that themselves use _ui() back to ui_server).
# ---------------------------------------------------------------------------

def _ref() -> Any:
    """Lazy accessor for ui_reference_resolvers."""
    from . import ui_reference_resolvers as _mod
    return _mod


def _norm() -> Any:
    """Lazy accessor for ui_normative_processors."""
    from . import ui_normative_processors as _mod
    return _mod


def _svp() -> Any:
    """Lazy accessor for ui_source_view_processors."""
    from . import ui_source_view_processors as _mod
    return _mod


# ---------------------------------------------------------------------------
# Module-level constants (moved from ui_server during granularize-v1 1E)
# ---------------------------------------------------------------------------

_EXPERT_PROVIDER_HEADING_RE = re.compile(r"^\s{0,3}(#{2,6})\s+(.+?)\s*$")
_EXPERT_SUMMARY_LABEL_RE = re.compile(
    r"^(?:enfoque distintivo|valor agregado para el contador|como aplicar|cómo aplicar|advertencia que incluyen)\s*:\s*",
    re.IGNORECASE,
)
_EXPERT_SUMMARY_SKIP_PREFIXES = (
    "corpus:",
    "compilado:",
    "audiencia:",
    "estado normativo:",
    "regla operativa",
    "regla operativa para lia",
    "condiciones de aplicacion",
    "condiciones de aplicación",
    "riesgos de interpretacion",
    "riesgos de interpretación",
    "relaciones normativas",
    "checklist de vigencia",
    "historico de cambios",
    "histórico de cambios",
    "enlace:",
    "identificacion",
    "identificación",
)
_EXPERT_SUMMARY_SKIP_EXACT = {
    "texto base referenciado",
    "texto base referenciado (resumen tecnico)",
    "texto base referenciado (resumen técnico)",
    "fuente primaria de referencia",
    "fuentes consultadas",
    "interpretaciones por fuente",
}


# ---------------------------------------------------------------------------
# Expert extractor functions (extracted from ui_server, Phase 1E)
# ---------------------------------------------------------------------------


def _normalize_query_tokens(text: str) -> list[str]:
    tokens = re.findall(r"[\wáéíóúñü]{4,}", str(text or "").lower())
    return [
        token
        for token in tokens
        if token not in _ui()._SUMMARY_STOPWORDS and token not in {"articulo", "artículos", "articulos", "estatuto", "tributario"}
    ]


def _expert_chunk_candidates(text: str) -> list[str]:
    clean = _ui()._extract_markdown_primary_body_text(text) or _ui()._extract_source_view_usable_text(text)
    if not clean:
        return []
    paragraphs = [
        re.sub(r"\s+", " ", str(paragraph or "")).strip()
        for paragraph in re.split(r"\n{2,}", clean)
        if str(paragraph or "").strip()
    ]
    if not paragraphs:
        return []

    candidates: list[str] = []
    seen: set[str] = set()
    for paragraph in paragraphs:
        if paragraph.lower() not in seen:
            seen.add(paragraph.lower())
            candidates.append(paragraph)
    for idx in range(len(paragraphs) - 1):
        window = f"{paragraphs[idx]}\n\n{paragraphs[idx + 1]}".strip()
        key = window.lower()
        if key not in seen:
            seen.add(key)
            candidates.append(window)
        if len(candidates) >= 240:
            break
    return candidates[:240]


def _expert_chunk_matches_article(chunk_text: str, *, citation: dict[str, Any]) -> bool:
    locator_start = _ref()._citation_et_locator_label(citation)
    if not locator_start:
        return False
    clean = re.sub(r"\s+", " ", html.unescape(str(chunk_text or ""))).strip()
    if not clean:
        return False
    if _norm()._article_heading_pattern(locator_start).search(clean):
        return True
    return False


def _expert_chunk_matches_topic(chunk_text: str, *, question_context: str, row: dict[str, Any]) -> bool:
    tokens = _normalize_query_tokens(question_context)
    if not tokens:
        return True

    haystack = " ".join(
        [
            str(chunk_text or ""),
            str(row.get("title") or ""),
            str(row.get("subtema") or ""),
            str(row.get("notes") or ""),
        ]
    ).lower()
    return any(token in haystack for token in tokens)


def _derive_expert_topic_label(chunk_text: str, *, row: dict[str, Any], question_context: str) -> str:
    lowered = " ".join([str(question_context or ""), str(chunk_text or "")]).lower()
    if "tasa mínima" in lowered or "tasa minima" in lowered or "ttd" in lowered:
        return "Respecto a tasa mínima de tributación"
    if "descuento" in lowered:
        return "Respecto al límite de descuentos tributarios"
    if "impuesto pagado en el exterior" in lowered or "artículo 254" in lowered or "articulo 254" in lowered:
        return "Respecto a descuentos por impuestos pagados en el exterior"
    if "regal" in lowered:
        return "Respecto a regalías"
    source_title = _svp()._resolve_source_display_title(
        row=dict(row),
        doc_id=str(row.get("doc_id") or "").strip(),
        raw_text="",
        public_text="",
    )
    return source_title or "Comentario experto"


# ---------------------------------------------------------------------------
# Expert document metadata extraction — structured fields from body text
# ---------------------------------------------------------------------------

_EXPERT_BOLD_METADATA_RE = re.compile(
    r"\*\*(?P<key>[^*]+)\*\*\s*:\s*(?P<value>.*)",
    re.IGNORECASE,
)

_EXPERT_METADATA_KEYS = {
    "tema principal": "tema_principal",
    "normas base": "normas_base",
    "normas base compiladas": "normas_base",
    "ámbito de aplicación": "ambito_aplicacion",
    "ambito de aplicacion": "ambito_aplicacion",
    "fecha de última verificación": "fecha_verificacion",
    "fecha de ultima verificacion": "fecha_verificacion",
}


def _extract_expert_document_metadata(text: str) -> dict[str, str]:
    """Parse structured metadata fields from expert document body text.

    Returns a dict with normalised keys like ``tema_principal``,
    ``normas_base``, ``ambito_aplicacion``, ``fecha_verificacion``.
    Multi-line values (e.g. bullet-list items following ``**Normas base**:``)
    are collected until the next bold-label line, heading, or ``---`` rule.
    """
    raw = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    if not raw.strip():
        return {}

    result: dict[str, str] = {}
    lines = raw.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        match = _EXPERT_BOLD_METADATA_RE.match(line.strip())
        if not match:
            i += 1
            continue

        raw_key = match.group("key").strip().lower()
        canonical = _EXPERT_METADATA_KEYS.get(raw_key)
        if canonical is None:
            i += 1
            continue

        # Collect the inline value
        value_parts: list[str] = [match.group("value").strip()]

        # Collect continuation lines (bullet items or wrapped text)
        i += 1
        while i < len(lines):
            cont = lines[i]
            cont_stripped = cont.strip()
            # Stop at next bold-label, heading, or horizontal rule
            if _EXPERT_BOLD_METADATA_RE.match(cont_stripped):
                break
            if cont_stripped.startswith("#"):
                break
            if cont_stripped == "---":
                break
            if not cont_stripped:
                i += 1
                continue
            value_parts.append(cont_stripped)
            i += 1

        result[canonical] = "\n".join(value_parts).strip()

    return result


def _find_expert_provider_link(public_text: str) -> dict[str, str] | None:
    providers = _resolve_doc_expert_providers(row=None, text=public_text)
    links = _ui()._filter_provider_links(public_text, providers=providers, max_links=12)
    return links[0] if links else None


def _resolve_doc_expert_providers(
    *,
    row: dict[str, Any] | None,
    text: str,
    authority: str = "",
) -> list[dict[str, str | None]]:
    row_payload = row if isinstance(row, dict) else {}
    providers = extract_expert_providers(
        text,
        stored_providers=row_payload.get("providers"),
        stored_labels=row_payload.get("provider_labels"),
        authority=authority or row_payload.get("authority"),
    )
    return [
        {
            "name": str(item.get("name") or "").strip(),
            "url": str(item.get("url") or "").strip() or None,
        }
        for item in providers
        if str(item.get("name") or "").strip()
    ]


def _canonicalize_expert_panel_ref(value: Any) -> str:
    return re.sub(r"_+", "_", str(value or "").strip().lower().replace(":", "_").replace(".", "_").replace("-", "_")).strip("_")


def _expand_expert_panel_requested_refs(raw_refs: list[Any]) -> set[str]:
    requested: set[str] = set()
    for item in raw_refs:
        normalized = _canonicalize_expert_panel_ref(item)
        if not normalized:
            continue
        requested.add(normalized)
        if normalized.startswith("art_"):
            requested.add(f"et_{normalized}")
        if normalized.startswith("et_art_"):
            requested.add(normalized[3:])
    return requested


def _prioritize_expert_panel_docs(
    docs: list[DocumentRecord],
    *,
    requested_refs: set[str],
) -> list[DocumentRecord]:
    if not requested_refs:
        return list(docs)

    def _matches_requested(doc: DocumentRecord) -> bool:
        refs = {
            _canonicalize_expert_panel_ref(item)
            for item in tuple(doc.normative_refs or ())
            if _canonicalize_expert_panel_ref(item)
        }
        return bool(refs & requested_refs)

    return sorted(
        docs,
        key=lambda doc: (
            not _matches_requested(doc),
            -(float(doc.retrieval_score or 0.0)),
            str(doc.doc_id or ""),
        ),
    )


def _extract_expert_anchor_excerpt(text: str) -> str:
    lines = str(text or "").replace("\r\n", "\n").replace("\r", "\n").splitlines()
    if not lines:
        return ""

    start_idx: int | None = None
    current_heading_level: int | None = None
    for idx, line in enumerate(lines):
        heading_match = _EXPERT_PROVIDER_HEADING_RE.match(line)
        if heading_match:
            heading_text = re.split(r"\s+[—–-]\s+", heading_match.group(2), maxsplit=1)[0]
            heading_text = re.sub(r"^(?:[A-Z]\d+\s+[—-]\s+)?(?:\d+(?:\.\d+){0,4}\.?\s+)+", "", heading_text).strip()
            if provider_names_from_label(heading_text):
                start_idx = idx
                current_heading_level = len(heading_match.group(1))
                break
        bullet_match = re.match(r"^\s*[-*+]?\s*\*\*(.+?)\*\*\s*(?:[—–-]|:)", line)
        if bullet_match and provider_names_from_label(bullet_match.group(1)):
            start_idx = idx
            break
        if any(provider_names_from_label(label) for label, _url in _MARKDOWN_LINK_RE.findall(line)):
            start_idx = idx
            break
        plain_heading = _ui()._clean_markdown_inline(line)
        if re.search(r"\s+[—–-]\s+", plain_heading):
            plain_heading = re.split(r"\s+[—–-]\s+", plain_heading, maxsplit=1)[0]
            plain_heading = re.sub(r"^(?:[A-Z]\d+\s+[—-]\s+)?(?:\d+(?:\.\d+){0,4}\.?\s+)+", "", plain_heading).strip()
        else:
            plain_heading = ""
        if plain_heading and provider_names_from_label(plain_heading):
            start_idx = idx
            break

    if start_idx is None:
        return ""

    picked: list[str] = []
    seen_content = False
    for idx, line in enumerate(lines[start_idx:], start=start_idx):
        clean = str(line or "").rstrip()
        if idx > start_idx and re.match(r"^\s*---+\s*$", clean):
            break
        heading_match = _EXPERT_PROVIDER_HEADING_RE.match(clean)
        if idx > start_idx and heading_match and seen_content:
            next_level = len(heading_match.group(1))
            if current_heading_level is None or next_level <= current_heading_level:
                break
        if idx > start_idx and seen_content:
            plain_heading = _ui()._clean_markdown_inline(clean)
            if re.search(r"\s+[—–-]\s+", plain_heading):
                plain_heading = re.split(r"\s+[—–-]\s+", plain_heading, maxsplit=1)[0]
                plain_heading = re.sub(r"^(?:[A-Z]\d+\s+[—-]\s+)?(?:\d+(?:\.\d+){0,4}\.?\s+)+", "", plain_heading).strip()
            else:
                plain_heading = ""
            if plain_heading and provider_names_from_label(plain_heading):
                break
        if _ui()._SOURCE_INTERNAL_BOUNDARY_RE.match(_ui()._clean_markdown_inline(clean)):
            break
        if clean.strip():
            seen_content = True
        picked.append(clean)
    return "\n".join(picked).strip()


def _clean_expert_summary_paragraph(paragraph: str) -> str:
    clean = re.sub(r"\s+", " ", _ui()._clean_markdown_inline(paragraph)).strip(" -:\n\t")
    clean = re.sub(r"^\s*>+\s*", "", clean).strip()
    embedded_label = re.search(
        r"(enfoque distintivo|valor agregado para el contador|como aplicar|cómo aplicar|advertencia que incluyen)\s*:",
        clean,
        re.IGNORECASE,
    )
    if embedded_label and embedded_label.start() > 0:
        clean = clean[embedded_label.start():].strip()
    clean = clean.replace("**", "").replace("__", "").strip()
    lowered = clean.lower()
    if not clean:
        return ""
    heading_probe = re.split(r"\s+[—–-]\s+", clean, maxsplit=1)[0]
    heading_probe = re.sub(r"^(?:[A-Z]\d+\s+[—-]\s+)?(?:\d+(?:\.\d+){0,4}\.?\s+)+", "", heading_probe).strip()
    if provider_names_from_label(heading_probe) and not re.search(r"[.!?]", clean):
        return ""
    if lowered in _EXPERT_SUMMARY_SKIP_EXACT:
        return ""
    if any(lowered.startswith(prefix) for prefix in _EXPERT_SUMMARY_SKIP_PREFIXES):
        return ""
    if _ui()._SOURCE_METADATA_LINE_RE.match(clean):
        return ""
    clean = _EXPERT_SUMMARY_LABEL_RE.sub("", clean).strip()
    if not clean:
        return ""
    if clean.lower() in _EXPERT_SUMMARY_SKIP_EXACT:
        return ""
    return clean


def _clip_expert_summary(text: str, *, max_chars: int) -> str:
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(clean) <= max_chars:
        return clean
    return f"{clean[: max_chars - 1].rstrip()}…"


def _expert_excerpt_paragraphs(text: str) -> list[str]:
    public_text = _ui()._extract_public_reference_text(str(text or ""))
    anchor_text = _extract_expert_anchor_excerpt(public_text) or public_text
    usable_text = _ui()._extract_source_view_usable_text(anchor_text)
    paragraphs = [
        _clean_expert_summary_paragraph(block)
        for block in re.split(r"\n{2,}", usable_text)
    ]
    paragraphs = [paragraph for paragraph in paragraphs if paragraph]
    if paragraphs:
        return paragraphs
    fallback_lines = [
        _clean_expert_summary_paragraph(line)
        for line in public_text.splitlines()
    ]
    return [line for line in fallback_lines if line]


def _expert_detail_excerpt(text: str, *, max_chars: int = 720) -> str:
    paragraphs = _expert_excerpt_paragraphs(text)
    if not paragraphs:
        return ""
    excerpt = re.sub(r"\s+", " ", " ".join(paragraphs[:2])).strip()
    return _clip_expert_summary(excerpt, max_chars=max_chars)


def _expert_card_summary(text: str, *, max_chars: int = 240) -> str:
    excerpt = _expert_detail_excerpt(text, max_chars=max(max_chars * 3, 480))
    if not excerpt:
        return ""
    sentence = _ui()._first_substantive_sentence(excerpt)
    if not sentence:
        sentence = excerpt
    sentence = sentence if re.search(r"[.!?…]$", sentence) else f"{sentence}."
    return _clip_expert_summary(sentence, max_chars=max_chars)
