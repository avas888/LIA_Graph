"""SUIN-Juriscol ingestion package.

Public entry points:

- `SuinFetcher` — resumable HTTP client with robots.txt + rate limit + disk cache.
- `parse_document` — extract `SuinDocument` + `SuinArticle` + `SuinEdge` from
  SUIN HTML.
- `harvest` CLI — invoked as `uv run python -m lia_graph.ingestion.suin.harvest`.

All three write into `artifacts/suin/<scope>/{documents,articles,edges}.jsonl`
and `cache/suin/*.html`. The bridge in `lia_graph.ingestion.suin.bridge`
converts those JSONL files into the `ParsedArticle`/`ClassifiedEdge` rows the
existing pipeline already knows how to write to Supabase + Falkor.
"""

from __future__ import annotations

from .fetcher import SITEMAPS, SuinFetcher, SuinFetchError
from .parser import (
    CANONICAL_VERBS,
    SuinArticle,
    SuinDocument,
    SuinEdge,
    UnknownVerb,
    normalize_article_key,
    normalize_doc_id,
    normalize_verb,
    parse_document,
)

__all__ = [
    "CANONICAL_VERBS",
    "SITEMAPS",
    "SuinArticle",
    "SuinDocument",
    "SuinEdge",
    "SuinFetchError",
    "SuinFetcher",
    "UnknownVerb",
    "normalize_article_key",
    "normalize_doc_id",
    "normalize_verb",
    "parse_document",
]
