"""Markdown article parser scaffolds for the shared regulatory graph."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

ARTICLE_HEADER_RE = re.compile(
    r"^(?P<prefix>#{1,6})\s*(?:art(?:[ií]culo)?|art\.)\s+"
    r"(?P<number>\d+(?:-\d+)?)"
    r"(?:\s*[oº°])?"
    r"(?:\s*[\.\-:]\s*(?P<title>.*))?$",
    re.IGNORECASE | re.MULTILINE,
)
PARAGRAPH_MARKER_RE = re.compile(
    r"(?im)^\s*(par[aá]grafo(?:\s+transitorio|\s+\d+)?)\b"
)
REFORM_REFERENCE_RE = re.compile(
    r"(?i)\b(?:Ley|Decreto|Resoluci[oó]n)\s+\d+(?:\s+de\s+\d{4})?"
)
ANNOTATION_RE = re.compile(r"(?im)^\s*(?:nota|observaci[oó]n|modificado|derogado)[^\n]*$")
DEROGATED_RE = re.compile(r"(?i)\bderogad[oa]\b")

# Fallback keys for docs without `## Artículo N` headers — the intake
# v2 template (Metadata / Identificacion / Regla operativa …) and práctica /
# interpretación docs are the common cases. Section-level chunking keeps
# retrieval granular; full-doc is the last-resort fallback.
WHOLE_DOC_ARTICLE_KEY = "doc"
_V2_TITLE_RE = re.compile(r"(?im)^\s*-?\s*titulo\s*:\s*([^\n]+)")
_H1_RE = re.compile(r"(?m)^#\s+([^\n]+)")
H2_HEADER_RE = re.compile(r"(?m)^##\s+(?!art(?:[ií]culo)?\b|art\.)\s*([^\n]+)$", re.IGNORECASE)
_METADATA_HEADINGS = ("metadata v2", "metadata")
_EMPTY_MARKER_RE = re.compile(r"\(sin\s+datos\)", re.IGNORECASE)
_METADATA_LINE_RE = re.compile(r"^\s*-?\s*[a-z_][a-z0-9_\s]*:\s*$", re.IGNORECASE)
_SLUG_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class ParsedArticle:
    article_key: str
    article_number: str
    heading: str
    body: str
    full_text: str
    status: str
    source_path: str | None = None
    paragraph_markers: tuple[str, ...] = ()
    reform_references: tuple[str, ...] = ()
    annotations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "article_key": self.article_key,
            "article_number": self.article_number,
            "heading": self.heading,
            "body": self.body,
            "full_text": self.full_text,
            "status": self.status,
            "source_path": self.source_path,
            "paragraph_markers": list(self.paragraph_markers),
            "reform_references": list(self.reform_references),
            "annotations": list(self.annotations),
        }


def _extract_heading_hint(markdown: str, source_path: str | None) -> str:
    m = _V2_TITLE_RE.search(markdown)
    if m:
        candidate = m.group(1).strip()
        if candidate and candidate != "(sin datos)":
            return candidate
    m = _H1_RE.search(markdown)
    if m:
        return m.group(1).strip()
    if source_path:
        from pathlib import PurePosixPath

        stem = PurePosixPath(source_path).stem
        if stem:
            return stem
    return "Documento completo"


def _slugify_section_key(heading: str) -> str:
    slug = _SLUG_RE.sub("-", heading.strip().lower()).strip("-")
    return (slug or "section")[:80]


def _section_is_effectively_empty(body: str) -> bool:
    stripped = body.strip()
    if not stripped:
        return True
    lowered = stripped.lower()
    if lowered in {"(sin datos)", "- (sin datos)"}:
        return True
    meaningful_lines = [
        line
        for line in stripped.split("\n")
        if line.strip()
        and not _EMPTY_MARKER_RE.search(line)
        and not _METADATA_LINE_RE.match(line)
    ]
    return not meaningful_lines


def _section_fallback(
    markdown: str,
    *,
    source_path: str | None,
) -> tuple[ParsedArticle, ...]:
    matches = list(H2_HEADER_RE.finditer(markdown))
    if not matches:
        return _whole_document_fallback(markdown, source_path=source_path)
    articles: list[ParsedArticle] = []
    seen_keys: set[str] = set()
    for index, match in enumerate(matches):
        next_start = (
            matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        )
        heading = match.group(1).strip()
        heading_lower = heading.lower()
        if any(heading_lower.startswith(marker) for marker in _METADATA_HEADINGS):
            continue
        body = markdown[match.end() : next_start].strip()
        if _section_is_effectively_empty(body):
            continue
        base_key = _slugify_section_key(heading)
        article_key = base_key
        bump = 1
        while article_key in seen_keys:
            article_key = f"{base_key}-{bump}"
            bump += 1
        seen_keys.add(article_key)
        full_text = f"## {heading}\n{body}".strip()
        paragraph_markers = tuple(
            marker.group(1).strip() for marker in PARAGRAPH_MARKER_RE.finditer(body)
        )
        reform_references = tuple(
            dict.fromkeys(
                reference.group(0).strip()
                for reference in REFORM_REFERENCE_RE.finditer(full_text)
            )
        )
        annotations = tuple(
            dict.fromkeys(
                annotation.group(0).strip()
                for annotation in ANNOTATION_RE.finditer(full_text)
            )
        )
        status = "derogado" if DEROGATED_RE.search(full_text) else "vigente"
        articles.append(
            ParsedArticle(
                article_key=article_key,
                article_number="",
                heading=heading,
                body=body,
                full_text=full_text,
                status=status,
                source_path=source_path,
                paragraph_markers=paragraph_markers,
                reform_references=reform_references,
                annotations=annotations,
            )
        )
    if not articles:
        return _whole_document_fallback(markdown, source_path=source_path)
    return tuple(articles)


def _whole_document_fallback(
    markdown: str,
    *,
    source_path: str | None,
) -> tuple[ParsedArticle, ...]:
    body = markdown.strip()
    if not body:
        return ()
    heading = _extract_heading_hint(markdown, source_path)
    full_text = body
    paragraph_markers = tuple(
        marker.group(1).strip() for marker in PARAGRAPH_MARKER_RE.finditer(body)
    )
    reform_references = tuple(
        dict.fromkeys(
            reference.group(0).strip()
            for reference in REFORM_REFERENCE_RE.finditer(full_text)
        )
    )
    annotations = tuple(
        dict.fromkeys(
            annotation.group(0).strip()
            for annotation in ANNOTATION_RE.finditer(full_text)
        )
    )
    status = "derogado" if DEROGATED_RE.search(full_text) else "vigente"
    return (
        ParsedArticle(
            article_key=WHOLE_DOC_ARTICLE_KEY,
            article_number="",
            heading=heading,
            body=body,
            full_text=full_text,
            status=status,
            source_path=source_path,
            paragraph_markers=paragraph_markers,
            reform_references=reform_references,
            annotations=annotations,
        ),
    )


def parse_articles(markdown: str, *, source_path: str | None = None) -> tuple[ParsedArticle, ...]:
    matches = list(ARTICLE_HEADER_RE.finditer(markdown))
    if not matches:
        return _section_fallback(markdown, source_path=source_path)
    articles: list[ParsedArticle] = []
    for index, match in enumerate(matches):
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        header = match.group(0).strip()
        body = markdown[match.end() : next_start].strip()
        article_number = match.group("number").strip()
        heading = (match.group("title") or "").strip() or f"Articulo {article_number}"
        full_text = f"{header}\n{body}".strip()
        paragraph_markers = tuple(
            marker.group(1).strip() for marker in PARAGRAPH_MARKER_RE.finditer(body)
        )
        reform_references = tuple(
            dict.fromkeys(reference.group(0).strip() for reference in REFORM_REFERENCE_RE.finditer(full_text))
        )
        annotations = tuple(
            dict.fromkeys(annotation.group(0).strip() for annotation in ANNOTATION_RE.finditer(full_text))
        )
        status = "derogado" if DEROGATED_RE.search(full_text) else "vigente"
        articles.append(
            ParsedArticle(
                article_key=article_number,
                article_number=article_number,
                heading=heading,
                body=body,
                full_text=full_text,
                status=status,
                source_path=source_path,
                paragraph_markers=paragraph_markers,
                reform_references=reform_references,
                annotations=annotations,
            )
        )
    return tuple(articles)


def parse_article_documents(
    documents: Iterable[tuple[str, str]],
) -> tuple[ParsedArticle, ...]:
    articles: list[ParsedArticle] = []
    for source_path, markdown in documents:
        articles.extend(parse_articles(markdown, source_path=source_path))
    return tuple(articles)
