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


def parse_articles(markdown: str, *, source_path: str | None = None) -> tuple[ParsedArticle, ...]:
    matches = list(ARTICLE_HEADER_RE.finditer(markdown))
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
