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


# --- Structured extractor for the per-expert detail view --------------------
# The expert corpus markdown has rich structure (## H2 sections, ### H3
# subsections, **Provider:** intros, a)/b)/c) lettered lists, **🔗 Fuentes
# directas:** link blocks). The legacy `_expert_excerpt_paragraphs` path
# flattens all of it via `re.sub(r"\s+", " ", ...)` in
# `_clean_expert_summary_paragraph`, which is fine for a one-line card preview
# but turns the per-expert detail view into a wall of text.
#
# `_expert_extended_excerpt` walks the raw markdown lines and emits a clean
# subset (`### `, `- `, `**bold**`) that the frontend renders semantically,
# while stripping plumbing the accountant doesn't need.

_EXPERT_PROVIDERS_RE_FRAGMENT = (
    r"Gerencie\.com|Gerencie|Actualícese|Actualicese|Deloitte|EY|KPMG|PwC|BDO|"
    r"Grant\s+Thornton|Crowe|Baker\s+Tilly|CR\s+Consultores|"
    r"Consultor\s+Contable\s+Alegra|DIAN|Legis|Vértice|Vertice|Consultorcontable"
)

_EXPERT_ATTRIB_PROVIDER_RE = re.compile(
    rf"^(?:{_EXPERT_PROVIDERS_RE_FRAGMENT})\s+",
    re.IGNORECASE,
)
_EXPERT_ATTRIB_VERB_RE = re.compile(
    r"^(?:documenta|detalla|publica|analiza|presenta|indica|enfatiza|"
    r"señala|senala|explica|destaca|sostiene|argumenta|considera|observa|"
    r"menciona|aclara|advierte|recomienda|describe|expone|comenta|interpreta|"
    r"reitera|aborda|trata|enseña|ensena|sugiere|propone|resalta|recoge|aporta)\s+",
    re.IGNORECASE,
)
_EXPERT_ATTRIB_BRIDGE_RE = re.compile(
    r"^(?:que|los|las|una|un|el|la|en|este|esta|estos|estas|sobre|para|"
    r"cuando|cómo|como|cuáles|cuales|qué|cualquier|todos|todas|si)\s+",
    re.IGNORECASE,
)

_FUENTES_DIRECTAS_HEADER_RE = re.compile(
    r"^\s*\*\*\s*(?:🔗\s*)?Fuentes\s+directas\s*:?\s*\*\*\s*$",
    re.IGNORECASE,
)
_PROVIDER_BOLD_HEADER_RE = re.compile(
    rf"^\s*\*\*\s*(?:{_EXPERT_PROVIDERS_RE_FRAGMENT})\s*:?\s*\*\*\s*$",
    re.IGNORECASE,
)
_LETTERED_ITEM_RE = re.compile(r"^\s*([a-z])\)\s+(.+)$", re.IGNORECASE)
_BULLET_ITEM_RE = re.compile(r"^\s*[-*]\s+(.+)$")
_HEADING_RE = re.compile(r"^(#{1,5})\s+(.+)$")
_HORIZONTAL_RULE_RE = re.compile(r"^\s*-{3,}\s*$")
_MARKDOWN_LINK_LINE_RE = re.compile(r"^\s*-\s+\[.+\]\(https?://[^\s)]+\).*$")
_TABLE_ROW_RE = re.compile(r"^\s*\|.+\|\s*$")
_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|[\s:|-]+\|\s*$")


def _strip_attribution_prefix(text: str) -> str:
    """Strip leading "Gerencie documenta que ..." patterns.

    The expert is already identified by the chip badge; restating the
    provider name on every sentence is noise. This recognises three
    components in sequence — provider name + reporting verb + (optional)
    bridge word — and drops them, capitalising the first remaining char.
    """
    m = _EXPERT_ATTRIB_PROVIDER_RE.match(text)
    if not m:
        return text
    rest = text[m.end():]
    m2 = _EXPERT_ATTRIB_VERB_RE.match(rest)
    if not m2:
        return text
    rest = rest[m2.end():]
    m3 = _EXPERT_ATTRIB_BRIDGE_RE.match(rest)
    if m3:
        rest = rest[m3.end():]
    rest = rest.lstrip()
    if not rest:
        return text
    return rest[0].upper() + rest[1:]


def _expert_extended_excerpt_legacy(text: str, *, max_chars: int) -> str:
    paragraphs = _expert_excerpt_paragraphs(text)
    if not paragraphs:
        return ""
    kept: list[str] = []
    running = 0
    for paragraph in paragraphs:
        if not paragraph:
            continue
        projected = running + len(paragraph) + (2 if kept else 0)
        if projected > max_chars and kept:
            break
        if len(paragraph) > max_chars:
            paragraph = _clip_expert_summary(paragraph, max_chars=max_chars - running - (2 if kept else 0))
            if paragraph:
                kept.append(paragraph)
            break
        kept.append(paragraph)
        running = projected
    return "\n\n".join(kept).strip()


def _drop_expert_metadata_header(text: str) -> list[str] | None:
    """Return raw lines from the first ``## `` heading onward.

    Everything above the first H2 is plumbing (title, "Tipo de corpus",
    "Fecha de última verificación", "Normas base", etc.). Returns ``None``
    when no H2 exists, signalling that the caller should fall back.
    """
    raw_lines = str(text or "").splitlines()
    for idx, line in enumerate(raw_lines):
        m = _HEADING_RE.match(line)
        if m and len(m.group(1)) >= 2:
            return raw_lines[idx:]
    return None


def _classify_expert_line(stripped: str) -> tuple[str, str | None]:
    """Classify one stripped corpus line into ('kind', payload-or-None).

    Pure function. The caller owns state (Fuentes-block flag, paragraph
    buffer) and translates classifications into emitted markdown blocks.
    """
    if not stripped:
        return ("blank", None)
    if _FUENTES_DIRECTAS_HEADER_RE.match(stripped):
        return ("fuentes_header", None)
    if _HORIZONTAL_RULE_RE.match(stripped):
        return ("hr", None)
    if _PROVIDER_BOLD_HEADER_RE.match(stripped):
        return ("provider_header", None)
    if _MARKDOWN_LINK_LINE_RE.match(stripped):
        return ("link_line", None)
    # Table separator (|---|---|) is a structural marker we drop. Order
    # matters: must check before the more permissive _TABLE_ROW_RE.
    if _TABLE_SEPARATOR_RE.match(stripped):
        return ("table_separator", None)
    if _TABLE_ROW_RE.match(stripped):
        return ("table_row", stripped)
    heading = _HEADING_RE.match(stripped)
    if heading:
        level = len(heading.group(1))
        text = heading.group(2).strip().rstrip(":")
        return ("heading", f"{level}|{text}") if text else ("blank", None)
    lettered = _LETTERED_ITEM_RE.match(stripped)
    if lettered:
        return ("bullet", lettered.group(2).strip()) if lettered.group(2).strip() else ("blank", None)
    bullet = _BULLET_ITEM_RE.match(stripped)
    if bullet:
        return ("bullet", bullet.group(1).strip()) if bullet.group(1).strip() else ("blank", None)
    return ("text", stripped)


def _format_expert_heading(payload: str) -> str:
    """Emit a markdown heading, demoted one level so ``## H2`` renders as
    ``### H3`` inside the modal (which already owns the higher levels)."""
    level_str, _, text = payload.partition("|")
    demoted = min(int(level_str) + 1, 5)
    return f"{'#' * demoted} {text}"


def _expert_extended_excerpt(text: str, *, max_chars: int = 5000) -> str:
    """Walk the corpus markdown and emit a clean, structured subset.

    Drops the front-matter metadata, drops ``**🔗 Fuentes directas:**``
    link blocks (until the next heading or HR), drops ``---`` rules and
    standalone ``**Provider:**`` headers, strips self-referential
    attribution prefixes, and preserves ``## H2`` / ``### H3`` headings,
    ``- `` bullets, and ``a) b) c)`` lettered items (rewritten to ``- ``).
    The frontend renders this minimal markdown subset semantically.
    """
    lines = _drop_expert_metadata_header(text)
    if lines is None:
        return _expert_extended_excerpt_legacy(text, max_chars=max_chars)

    builder = _ExtendedExcerptBuilder(max_chars=max_chars)
    in_fuentes = False
    for line in lines:
        if builder.is_full():
            break
        stripped = line.strip()

        if in_fuentes:
            kind, _ = _classify_expert_line(stripped)
            if kind in ("heading", "hr"):
                in_fuentes = False  # fall through to process this line
            else:
                continue

        kind, payload = _classify_expert_line(stripped)
        # Table rows accumulate on their own buffer; any other kind flushes
        # the table first so we don't merge a table into surrounding prose.
        if kind == "table_row" and payload:
            builder.flush_paragraph()
            builder.add_table_row(payload)
            continue
        if kind == "table_separator":
            continue  # structural marker; the row layout is enough to render
        builder.flush_table()

        if kind == "fuentes_header":
            builder.flush_paragraph()
            in_fuentes = True
        elif kind == "hr" or kind == "provider_header":
            builder.flush_paragraph()
        elif kind == "link_line":
            continue
        elif kind == "heading" and payload:
            builder.flush_paragraph()
            builder.append_block(_format_expert_heading(payload))
        elif kind == "bullet" and payload:
            builder.flush_paragraph()
            builder.append_block(f"- {payload}")
        elif kind == "blank":
            builder.flush_paragraph()
        elif kind == "text" and payload:
            builder.add_paragraph_line(payload)

    builder.flush_paragraph()
    builder.flush_table()
    result = builder.render()
    if not result:
        return _expert_extended_excerpt_legacy(text, max_chars=max_chars)
    return result


class _ExtendedExcerptBuilder:
    """Accumulates clean markdown blocks under a char budget.

    Holds the small bit of mutable state (paragraph buffer, emitted
    blocks, char counter, overflow flag) that `_expert_extended_excerpt`
    threads through the line walk. Extracted so the orchestrator stays
    declarative and the budget bookkeeping has one home.
    """

    def __init__(self, *, max_chars: int) -> None:
        self._max_chars = max_chars
        self._blocks: list[str] = []
        self._paragraph_buf: list[str] = []
        self._table_buf: list[str] = []
        self._running = 0
        self._overflow = False

    def is_full(self) -> bool:
        return self._overflow

    def add_paragraph_line(self, line: str) -> None:
        self._paragraph_buf.append(line)

    def add_table_row(self, line: str) -> None:
        self._table_buf.append(line)

    def flush_paragraph(self) -> None:
        if not self._paragraph_buf:
            return
        joined = _strip_attribution_prefix(" ".join(self._paragraph_buf).strip())
        self._paragraph_buf.clear()
        if not joined:
            return
        if not self._fits(joined):
            if not self._blocks:
                joined = _clip_expert_summary(joined, max_chars=self._max_chars)
                self._blocks.append(joined)
                self._running = len(joined)
            self._overflow = True
            return
        self._commit(joined)

    def flush_table(self) -> None:
        if not self._table_buf:
            return
        joined = "\n".join(self._table_buf).strip()
        self._table_buf.clear()
        if not joined:
            return
        if not self._fits(joined):
            self._overflow = True
            return
        self._commit(joined)

    def append_block(self, block: str) -> bool:
        if not self._fits(block):
            self._overflow = True
            return False
        self._commit(block)
        return True

    def render(self) -> str:
        # Drop trailing heading blocks that have no content below them. An
        # orphan heading appears when the source section is genuinely empty
        # or when the char budget overflowed right after committing the
        # heading — rendering "3. Divergencias …" with nothing underneath
        # is worse than omitting the section entirely.
        blocks = list(self._blocks)
        while blocks and _HEADING_RE.match(blocks[-1]):
            blocks.pop()
        return "\n\n".join(blocks).strip()

    def _block_cost(self, block: str) -> int:
        return len(block) + (2 if self._blocks else 0)

    def _fits(self, block: str) -> bool:
        return self._running + self._block_cost(block) <= self._max_chars

    def _commit(self, block: str) -> None:
        self._running += self._block_cost(block)
        self._blocks.append(block)
