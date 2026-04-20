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
)
_ANNOTATION_CANONICAL: dict[str, str] = {label.lower(): label for label in ANNOTATION_LABELS}
_ANNOTATION_PATTERN = re.compile(
    r"\*\*\s*(Notas\s+de\s+Vigencia|Concordancias|Jurisprudencia|Doctrina\s+Concordante)\s*:?\s*\*\*",
    re.IGNORECASE,
)
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BULLET_PREFIX_RE = re.compile(r"^\s*(?:>\s*)*(?:[*\-•]\s+)?")
_INLINE_BOLD_RE = re.compile(r"\*\*([^*\n]+)\*\*")
_INLINE_ITALIC_RE = re.compile(r"(?<!\*)\*([^*\n]+)\*")
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_HEADING_RE = re.compile(r"^\s*#{1,6}\s*", flags=re.MULTILINE)
_SAFE_HREF_SCHEMES = ("http://", "https://", "/")


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
    emitted as single items with the full paragraph text.
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
        else:
            joined = " ".join(_BULLET_PREFIX_RE.sub("", line).strip() for line in lines)
            item = _extract_linked_item(joined)
            if item["text"] or item["href"]:
                items.append(item)
    return items


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
        return {"text": _strip_inline_markdown(stripped), "href": ""}
    href = _sanitize_href(match.group(2))
    anchor_text = match.group(1).strip()
    before = stripped[: match.start()].strip(" \t:;,.-—–")
    after = stripped[match.end():].strip(" \t:;,.-—–")
    if not before and not after:
        return {"text": _strip_inline_markdown(anchor_text), "href": href}
    flattened = _MD_LINK_RE.sub(lambda m: m.group(1), stripped)
    return {"text": _strip_inline_markdown(flattened), "href": href}


def split_article_annotations(raw_text: Any) -> tuple[str, list[dict[str, Any]]]:
    """Separate an article's body from its inline `**Label:**` annotations.

    Returns `(body, annotations)` where each annotation is a dict with:
      - `label`: canonical label (one of ANNOTATION_LABELS)
      - `body`:  plain-text flattened block (back-compat)
      - `items`: list of {text, href} — href may be empty for text-only lines

    Annotations preserve the discovery order of the labels in the original
    text. Used by the ET citation profile so the modal can render the body
    cleanly and surface Notas de Vigencia / Concordancias / Jurisprudencia /
    Doctrina in a dedicated tab strip with clickable references where the
    corpus carries them.
    """
    raw = str(raw_text or "")
    if not raw.strip():
        return "", []
    matches = list(_ANNOTATION_PATTERN.finditer(raw))
    if not matches:
        return raw, []
    body = raw[: matches[0].start()].rstrip()
    annotations: list[dict[str, Any]] = []
    seen_labels: set[str] = set()
    for idx, match in enumerate(matches):
        label_raw = " ".join(match.group(1).split())
        label = _ANNOTATION_CANONICAL.get(label_raw.lower(), label_raw)
        if label in seen_labels:
            continue
        seen_labels.add(label)
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(raw)
        segment = raw[match.end():end]
        body_text = clean_annotation_body(segment)
        items = parse_annotation_items(segment)
        if body_text or items:
            annotations.append({"label": label, "body": body_text, "items": items})
    return body, annotations
