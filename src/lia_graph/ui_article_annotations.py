"""Parser for ET article inline annotations.

Extracted from `ui_citation_profile_builders.py` during granularize-v1 because
the host module crossed 2k LOC. This module owns the pure, side-effect-free
logic that turns the raw markdown body of a parsed ET article into:

* a clean body (annotations removed) for the quote block
* a list of structured annotations — one per `**Label:**` marker — each
  carrying both a plain-text `body` (for legacy consumers) and a
  `items: list[{text, href}]` list (so the frontend can render bullets as
  `<a>` when the corpus provides a URL and plain text when it doesn't).

The input shape is the markdown that `ingestion/parser.py` emits into
`artifacts/parsed_articles.jsonl`, e.g.::

    **Doctrina Concordante:**
    > * [Oficio DIAN 635 de 2019](https://normograma.dian.gov.co/.../0635_2019.htm)
    > * [Concepto DIAN 14396 de 2025](https://normograma.dian.gov.co/.../14396_2025.htm)

    **Concordancias:**
    > * [Decreto 2235 de 2017](https://normograma.dian.gov.co/.../2235_2017.htm)

No I/O, no network, no dependencies on the rest of the ui_server stack —
this module is safe to import from anywhere and to unit-test in isolation.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any


# Labels that appear inline inside the raw `full_text` of parsed ET articles
# as `**Label:**` bold markers and precede the actual article body's trailing
# metadata. Kept in display order so the resulting tab strip reads from most
# to least relevant for an accountant.
ANNOTATION_LABELS: tuple[str, ...] = (
    "Notas de Vigencia",
    "Concordancias",
    "Jurisprudencia",
    "Doctrina Concordante",
    "Legislación Anterior",
)

# Corpus-observed variants (case-insensitive, accent-folded, paren-suffixes
# stripped) mapped to one of the four canonical tabs. Any bold header whose
# normalized form isn't here is left in the article body — we match on a loose
# `**...:**` pattern, so this alias map is the sole gate preventing random
# inline bold from creating phantom tabs.
_LABEL_ALIASES: dict[str, str] = {
    # Notas de Vigencia
    "notas de vigencia": "Notas de Vigencia",
    "nota de vigencia": "Notas de Vigencia",
    # Concordancias
    "concordancias": "Concordancias",
    "concordancia": "Concordancias",
    "concordancias transversales": "Concordancias",
    # Jurisprudencia — merge every subtype into one tab so courts land as
    # individual bullets rather than a single concatenated paragraph.
    "jurisprudencia": "Jurisprudencia",
    "jurisprudencia concordante": "Jurisprudencia",
    "jurisprudencia vigencia": "Jurisprudencia",
    "jurisprudencia unificacion": "Jurisprudencia",
    "jurisprudencia relevante": "Jurisprudencia",
    "jurisprudencia disponible": "Jurisprudencia",
    "jurisprucdencia concordante": "Jurisprudencia",  # corpus typo (4 occurrences)
    # Doctrina Concordante
    "doctrina concordante": "Doctrina Concordante",
    "doctrina dian": "Doctrina Concordante",
    "doctrina": "Doctrina Concordante",
    # Legislación Anterior — historical text of the article as modified by
    # prior laws. Each `> *` bullet is usually a heading ("Texto modificado
    # por la Ley X:") followed by a paragraph-length quoted passage. The
    # frontend is responsible for rendering long anchor text as prose rather
    # than as a single underlined link.
    "legislacion anterior": "Legislación Anterior",
}

_ANNOTATION_PATTERN = re.compile(r"\*\*\s*([^*\n]{3,80}?)\s*:\s*\*\*")
_ORPHAN_BOLD_HEADER_RE = re.compile(r"^\*\*\s*[^*\n]{3,80}\s*:\s*\*\*$")
_EDITOR_NOTE_SENTINEL_RE = re.compile(r"^\s*En\s+criterio\s+del\s+editor\b", re.IGNORECASE)
_PAREN_SUFFIX_RE = re.compile(r"\s*\([^)]*\)\s*")
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BULLET_PREFIX_RE = re.compile(r"^\s*(?:>\s*)*(?:[*\-•]\s+)?")
_LEADING_DASH_RE = re.compile(r"^\s*[-–—•*]\s+")
_INLINE_BOLD_RE = re.compile(r"\*\*([^*\n]+)\*\*")
_INLINE_ITALIC_RE = re.compile(r"(?<!\*)\*([^*\n]+)\*")
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_HEADING_RE = re.compile(r"^\s*#{1,6}\s*", flags=re.MULTILINE)
_SAFE_HREF_SCHEMES = ("http://", "https://", "/")


def _normalize_label(raw: str) -> str:
    """Fold a raw `**Label:**` header to the key used in `_LABEL_ALIASES`.

    Lowercases, strips parenthetical suffixes like `(DIAN)`, removes accents,
    and collapses internal whitespace so the alias map only needs plain-ASCII
    lowercase keys. Returns "" when the input carries no recognizable word
    content.
    """
    if not raw:
        return ""
    without_parens = _PAREN_SUFFIX_RE.sub(" ", raw)
    folded = unicodedata.normalize("NFKD", without_parens)
    ascii_only = folded.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_only.lower()).strip()


def _sanitize_href(raw: Any) -> str:
    """Return `raw` if it's an http(s) or root-relative URL, else empty."""
    value = str(raw or "").strip()
    if not value:
        return ""
    lowered = value.lower()
    if lowered.startswith("http://") or lowered.startswith("https://"):
        return value
    if value.startswith("/"):
        return value
    return ""


def _strip_inline_markdown(text: str) -> str:
    value = _INLINE_CODE_RE.sub(r"\1", text)
    value = _INLINE_BOLD_RE.sub(r"\1", value)
    value = _INLINE_ITALIC_RE.sub(r"\1", value)
    return value.strip()


def clean_annotation_body(text: Any) -> str:
    """Flatten a raw annotation block to human-readable plain text.

    Preserves line breaks so list-style annotations stay readable, but strips
    markdown links, bold/italic markers, backticks, and headings that would
    otherwise surface as literal noise in the rendered tab panel. This is the
    back-compat path for consumers that want a single string body.
    """
    value = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not value:
        return ""
    value = _MD_LINK_RE.sub(r"\1", value)
    value = _INLINE_CODE_RE.sub(r"\1", value)
    value = _INLINE_BOLD_RE.sub(r"\1", value)
    value = _INLINE_ITALIC_RE.sub(r"\1", value)
    value = _HEADING_RE.sub("", value)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    value = re.sub(r"\s*---+\s*$", "", value).strip()
    return value


def parse_annotation_items(text: Any) -> list[dict[str, str]]:
    """Parse an annotation block into bullet items with optional hrefs.

    Each returned item is `{"text": str, "href": str}` where `href` is
    empty when the source line has no markdown link. The caller decides
    whether to render as `<a>` or plain text. Non-bullet paragraphs are
    emitted as single items with the full paragraph text. When a block mixes
    bullets with a stray bold header (e.g. `**Notas del Editor:**` leaking
    into an adjacent segment), the bullets are emitted individually and the
    orphan header is dropped — preserving per-bullet structure and URLs
    rather than collapsing the block into a single run-on paragraph.
    """
    raw = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not raw:
        return []
    items: list[dict[str, str]] = []
    for block in re.split(r"\n{2,}", raw):
        lines = [line for line in block.split("\n") if line.strip()]
        if not lines:
            continue
        bullet_like = [bool(re.match(r"^\s*(?:>\s*)*[*\-•]\s+", line)) for line in lines]
        if bullet_like and all(bullet_like):
            for line in lines:
                body = _BULLET_PREFIX_RE.sub("", line).strip()
                if not body:
                    continue
                item = _extract_linked_item(body)
                if item["text"] or item["href"]:
                    items.append(item)
        elif any(bullet_like):
            for line, is_bullet in zip(lines, bullet_like):
                stripped = line.strip()
                if _ORPHAN_BOLD_HEADER_RE.match(stripped):
                    continue
                body = _BULLET_PREFIX_RE.sub("", line).strip() if is_bullet else stripped
                if not body:
                    continue
                item = _extract_linked_item(body)
                if item["text"] or item["href"]:
                    items.append(item)
        else:
            joined = " ".join(_BULLET_PREFIX_RE.sub("", line).strip() for line in lines)
            item = _extract_linked_item(joined)
            if item["text"] or item["href"]:
                items.append(item)
    return items


def group_editor_notes(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fold `En criterio del editor` sentinel items into parent+sub_items.

    The ET corpus packs editor commentary into `Notas del Editor` blocks
    where each distinct note starts with the sentence `En criterio del editor
    …`, followed by continuation bullets (quoted norms, parenthetical
    clarifications). This helper walks a flat items list and groups every
    continuation under its preceding sentinel item, so the renderer can show
    one parent bullet per note with the continuation fragments as indented
    sub-bullets. No-op when no item matches the sentinel.
    """
    if not items:
        return []
    has_sentinel = any(_EDITOR_NOTE_SENTINEL_RE.match(i.get("text", "") or "") for i in items)
    if not has_sentinel:
        return list(items)
    grouped: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for item in items:
        text = item.get("text", "") or ""
        if _EDITOR_NOTE_SENTINEL_RE.match(text):
            if current is not None:
                grouped.append(current)
            current = {"text": text, "href": item.get("href", "") or "", "sub_items": []}
        elif current is not None:
            current["sub_items"].append(
                {"text": text, "href": item.get("href", "") or ""}
            )
        else:
            grouped.append(item)
    if current is not None:
        grouped.append(current)
    return grouped


def _extract_linked_item(line: str) -> dict[str, str]:
    """Pull the first markdown link out of `line`, return {text, href}.

    If the line is *exactly* a markdown link (with optional surrounding
    punctuation), the link's anchor text becomes the item text. Otherwise
    the full line with markdown stripped is the text, and the first link's
    URL (if any) is attached as `href`.
    """
    stripped = line.strip()
    if not stripped:
        return {"text": "", "href": ""}
    match = _MD_LINK_RE.search(stripped)
    if match is None:
        return {"text": _LEADING_DASH_RE.sub("", _strip_inline_markdown(stripped)), "href": ""}
    href = _sanitize_href(match.group(2))
    anchor_text = match.group(1).strip()
    before = stripped[: match.start()].strip(" \t:;,.-—–")
    after = stripped[match.end():].strip(" \t:;,.-—–")
    if not before and not after:
        clean = _LEADING_DASH_RE.sub("", _strip_inline_markdown(anchor_text))
        return {"text": clean, "href": href}
    flattened = _MD_LINK_RE.sub(lambda m: m.group(1), stripped)
    return {"text": _LEADING_DASH_RE.sub("", _strip_inline_markdown(flattened)), "href": href}


def split_article_annotations(raw_text: Any) -> tuple[str, list[dict[str, Any]]]:
    """Separate an article's body from its inline `**Label:**` annotations.

    Returns `(body, annotations)` where each annotation is a dict with:
      - `label`: canonical label (one of ANNOTATION_LABELS)
      - `body`:  plain-text flattened block (back-compat)
      - `items`: list of {text, href} — href may be empty for text-only lines

    Annotations preserve the discovery order of the first match for each
    canonical label. Corpus variants of the same concept (e.g. `Jurisprudencia
    Concordante` and `Jurisprudencia Vigencia`) collapse into a single tab
    with items concatenated, so each cited court decision surfaces as its own
    bullet rather than a run-on paragraph.
    """
    raw = str(raw_text or "")
    if not raw.strip():
        return "", []
    recognized: list[tuple[re.Match[str], str]] = []
    for match in _ANNOTATION_PATTERN.finditer(raw):
        canonical = _LABEL_ALIASES.get(_normalize_label(match.group(1)))
        if canonical:
            recognized.append((match, canonical))
    if not recognized:
        return raw, []
    body = raw[: recognized[0][0].start()].rstrip()
    by_label: dict[str, dict[str, Any]] = {}
    for idx, (match, label) in enumerate(recognized):
        end = recognized[idx + 1][0].start() if idx + 1 < len(recognized) else len(raw)
        segment = raw[match.end():end]
        body_text = clean_annotation_body(segment)
        items = parse_annotation_items(segment)
        if not (body_text or items):
            continue
        if label in by_label:
            existing = by_label[label]
            if body_text:
                existing["body"] = (
                    f"{existing['body']}\n\n{body_text}".strip()
                    if existing["body"]
                    else body_text
                )
            existing["items"].extend(items)
        else:
            by_label[label] = {"label": label, "body": body_text, "items": list(items)}
    for entry in by_label.values():
        entry["items"] = group_editor_notes(entry["items"])
    return body, list(by_label.values())
