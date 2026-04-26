"""Reference extraction scaffolds for shared regulatory graph ingestion."""

from __future__ import annotations

from dataclasses import dataclass
import re

from collections.abc import Mapping

from ..graph.schema import NodeKind
from .parser import ParsedArticle
# `graph_article_key` is imported lazily inside `_extract_article_edges`
# to avoid a circular: linker → loader → classifier → linker.

ARTICLE_REFERENCE_RE = re.compile(
    r"(?i)\b(?:art(?:[ií]culo)?|art\.)\s*(?P<number>\d+(?:-\d+)?)\b"
)
LAW_REFERENCE_RE = re.compile(r"(?i)\bLey\s+(?P<number>\d+)\s+de\s+(?P<year>\d{4})\b")
DECREE_REFERENCE_RE = re.compile(r"(?i)\bDecreto\s+(?P<number>\d+)(?:\s+de\s+(?P<year>\d{4}))?\b")
RESOLUTION_REFERENCE_RE = re.compile(
    r"(?i)\bResoluci[oó]n\s+(?P<number>\d+)(?:\s+de\s+(?P<year>\d{4}))?\b"
)


@dataclass(frozen=True)
class RawEdgeCandidate:
    source_kind: NodeKind
    source_key: str
    target_kind: NodeKind
    target_key: str
    raw_reference: str
    context: str
    relation_hint: str | None = None
    # ingestionfix_v2 §4 Phase 4: which corpus family produced this edge
    # (``normativa`` / ``practica`` / ``interpretacion`` / ``expertos``).
    # Consumed by the classifier to gate the Spanish-taxonomy edge_type.
    source_family: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "source_kind": self.source_kind.value,
            "source_key": self.source_key,
            "target_kind": self.target_kind.value,
            "target_key": self.target_key,
            "raw_reference": self.raw_reference,
            "context": self.context,
            "relation_hint": self.relation_hint,
            "source_family": self.source_family,
        }


def extract_edge_candidates(
    articles: tuple[ParsedArticle, ...] | list[ParsedArticle],
    *,
    family_by_source_path: Mapping[str, str] | None = None,
) -> tuple[RawEdgeCandidate, ...]:
    """Extract raw edge candidates.

    When ``family_by_source_path`` is supplied, each emitted candidate is
    stamped with its origin family (from the parent article's source_path)
    so the classifier can apply the Phase-4 edge-type taxonomy: MODIFICA /
    DEROGA / CITA for normativa sources, PRACTICA_DE for practica,
    INTERPRETA_A for interpretacion / expertos, MENCIONA for casual
    mentions with no known family.
    """
    from dataclasses import replace

    family_lookup: Mapping[str, str] = family_by_source_path or {}
    dedup: dict[tuple[str, str, str, str], RawEdgeCandidate] = {}
    for article in articles:
        family = family_lookup.get(str(article.source_path or "")) or None
        for candidate in _extract_article_edges(article):
            if family is not None:
                candidate = replace(candidate, source_family=family)
            key = (
                candidate.source_key,
                candidate.target_kind.value,
                candidate.target_key,
                candidate.relation_hint or "",
            )
            current = dedup.get(key)
            if current is None or len(candidate.context) > len(current.context):
                dedup[key] = candidate
    return tuple(
        dedup[key]
        for key in sorted(dedup, key=lambda item: (item[0], item[1], item[2], item[3]))
    )


def _extract_article_edges(article: ParsedArticle) -> list[RawEdgeCandidate]:
    # v5 §6.3 — emit the Falkor MERGE form for the source key. For numbered
    # articles `graph_article_key()` returns `article.article_key` unchanged
    # (no behavioral change). For prose-only articles it returns
    # `whole::{source_path}`, matching what `loader.py` actually MERGEs into
    # Falkor — which fixes the 99,1% of bucket-(a) edge loss measured in
    # v5 §6.2 (where source_keys like `'10-fuentes-y-referencias'` failed
    # to MATCH any ArticleNode because the MERGE happened under the
    # `whole::` form). Lazy import — see module-level note.
    from .loader import graph_article_key

    src_key = graph_article_key(article)
    candidates: list[RawEdgeCandidate] = []
    for match in ARTICLE_REFERENCE_RE.finditer(article.full_text):
        target_key = match.group("number").strip()
        if target_key == article.article_key:
            continue
        context = _context_window(article.full_text, match.start(), match.end())
        candidates.append(
            RawEdgeCandidate(
                source_kind=NodeKind.ARTICLE,
                source_key=src_key,
                target_kind=NodeKind.ARTICLE,
                target_key=target_key,
                raw_reference=match.group(0).strip(),
                context=context,
                relation_hint=_infer_relation_hint(context),
            )
        )
    for regex, prefix in (
        (LAW_REFERENCE_RE, "LEY"),
        (DECREE_REFERENCE_RE, "DECRETO"),
        (RESOLUTION_REFERENCE_RE, "RESOLUCION"),
    ):
        for match in regex.finditer(article.full_text):
            context = _context_window(article.full_text, match.start(), match.end())
            target_key = _build_external_key(prefix, match.group("number"), match.groupdict().get("year"))
            candidates.append(
                RawEdgeCandidate(
                    source_kind=NodeKind.ARTICLE,
                    source_key=src_key,
                    target_kind=NodeKind.REFORM,
                    target_key=target_key,
                    raw_reference=match.group(0).strip(),
                    context=context,
                    relation_hint=_infer_relation_hint(context),
                )
            )
    return candidates


def _build_external_key(prefix: str, number: str | None, year: str | None) -> str:
    normalized_number = str(number or "").strip()
    normalized_year = str(year or "s_f").strip()
    return f"{prefix}-{normalized_number}-{normalized_year}"


def _context_window(text: str, start: int, end: int, *, window: int = 120) -> str:
    left = max(0, start - window)
    right = min(len(text), end + window)
    snippet = text[left:right]
    return " ".join(snippet.split())


def _infer_relation_hint(context: str) -> str | None:
    lowered = context.lower()
    if any(keyword in lowered for keyword in ("modific", "adicion", "sustituy", "subrog")):
        return "MODIFIES"
    if any(keyword in lowered for keyword in ("derog", "reemplaz")):
        return "SUPERSEDES"
    if any(keyword in lowered for keyword in ("excepto", "salvo", "no obstante")):
        return "EXCEPTION_TO"
    if any(keyword in lowered for keyword in ("conforme", "calcular", "depende", "base gravable")):
        return "COMPUTATION_DEPENDS_ON"
    if any(keyword in lowered for keyword in ("requiere", "debe", "condicion")):
        return "REQUIRES"
    if any(keyword in lowered for keyword in ("se entiende por", "define", "definicion")):
        return "DEFINES"
    return None
