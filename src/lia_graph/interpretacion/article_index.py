"""fix_v10_may Phase 10C — Article → Interpretation-doc anchor index.

Builds an in-memory map `{normalized_article_key: {sanitized_doc_id, ...}}`
so the expert-panel retriever can route directly to the interpretation
docs that analyze a given article when the planner has resolved an
`art_115_et` (or similar) reference.

Canonical Phase 10C §3.C shipping path is via a FalkorDB
`InterpretationNode`-[:INTERPRETS]->ArticleNode subgraph, populated by a
loader at ingest time. This module is the **pragmatic v0** of that idea:
same data model, served from Python memory by reading the
already-on-disk corpus manifest + interpretation markdown files (via
`catalog.list_local_interpretation_rows`). Promoting to the Falkor
loader + a Cypher planner anchor is tracked as a v10.1 task; the
schema scaffold for `InterpretationNode` / `INTERPRETS` /
`COVERS_TOPIC` already landed in `graph/schema.py` so v10.1 only
needs to write the loader, not the contract.

Why this delivers the Phase 10C benefit without the Cypher round-trip:

* For every interpretation doc, `list_local_interpretation_rows()`
  already extracts `normative_refs` from the doc's markdown via
  `extract_article_refs(preview_text)`. The refs come out in the
  canonical `et_art_<N>` form that matches what
  `extract_article_refs(query)` produces inside the retriever
  dispatcher.
* The retriever's `fetch_interpretation_candidates` already receives
  `article_refs` from the planner. With this index it can convert
  those refs into a **doc-id whitelist** and post-filter the
  `hybrid_search` chunk set to only chunks whose parent doc actually
  interprets the article.
* This breaks the lexical-disambiguation ceiling the §5.2 gate-6
  levers (a) + (b) could not (43 % accept@top3 on the 21-Q mini-panel
  on 2026-05-11 PM) by replacing "chunk text mentions the article"
  with "doc has been observed to interpret the article".
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from .catalog import list_local_interpretation_rows
from .synthesis_helpers import extract_article_refs


_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
_MANIFEST_PATH = _WORKSPACE_ROOT / "artifacts" / "canonical_corpus_manifest.json"
_KNOWLEDGE_BASE_ROOT = _WORKSPACE_ROOT / "knowledge_base"


_ARTICLE_KEY_NORMALIZE_RE = re.compile(r"[^a-z0-9_]+")


_DOC_ID_SANITIZER_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def _sanitize_doc_id(relative_path: str) -> str:
    """Mirror `lia_graph.ingestion.supabase_sink._sanitize_doc_id`
    BYTE-FOR-BYTE.

    The cloud sink preserves dashes AND dots in the doc_id
    (regex `[^A-Za-z0-9_.-]+`) so a path like
    `T-B-costos-deducciones-fuentes-secundarias.md` becomes
    `T-B-costos-deducciones-fuentes-secundarias.md` (slashes/spaces
    only collapse to `_`). An earlier version of this function used
    `[^A-Za-z0-9_]+` which mangled dashes/dots into underscores —
    breaking doc_id parity with cloud Supabase rows and silently
    filtering every interpretation chunk OUT of the anchor whitelist.
    Re-implemented here to avoid pulling the entire ingestion package
    into the request-path import graph (the sink imports supabase-py
    + classifier modules + ~1500 LOC of write-side machinery; the
    retriever should not depend on any of that).
    """
    return _DOC_ID_SANITIZER_RE.sub("_", str(relative_path or "").strip()).strip("_")


def normalize_article_key(ref: str) -> str:
    """Canonicalize an article reference to a single comparable key.

    Accepts shapes the codebase produces from various paths:
      * `et_art_115`         — `extract_article_refs` (catalog + dispatcher)
      * `et_art_115_2`       — sub-article (e.g. Art. 115-2)
      * `art_115_et`         — chunk concept_tags style (parser output)
      * `art_124_2_et`       — sub-article variant
      * `Art. 115 ET`        — raw text occasionally bleeds through

    Output: lowercase, underscore-separated, leading `et_art_` stripped,
    trailing `_et` stripped. Examples:
      `et_art_115`    → `art_115`
      `art_115_et`    → `art_115`
      `et_art_124_2`  → `art_124_2`
      `art_124_2_et`  → `art_124_2`
    """
    s = str(ref or "").strip().lower()
    if not s:
        return ""
    # Replace any non [a-z0-9_] with `_`, collapse runs.
    s = _ARTICLE_KEY_NORMALIZE_RE.sub("_", s).strip("_")
    s = re.sub(r"_+", "_", s)
    # Strip alternate prefix/suffix decorations.
    if s.startswith("et_"):
        s = s[3:]
    if s.endswith("_et"):
        s = s[:-3]
    return s


def _iter_interpretation_manifest_entries() -> list[dict]:
    """Read raw manifest entries (no catalog 12K preview cap).

    The catalog's row builder bounds preview text to 12,000 chars,
    which silently drops `Art. NN` mentions deeper in long expert
    briefs (T-B-costos-deducciones is ~25 KiB and its first article-115
    mention is past the cap). For the index we read the full markdown
    so the article→doc mapping is complete.
    """
    if not _MANIFEST_PATH.exists():
        return []
    manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for item in manifest.get("documents", ()) or ():
        if str(item.get("knowledge_class") or "").strip().lower() != "interpretative_guidance":
            continue
        relative_path = str(item.get("relative_path") or item.get("source_path") or "").strip()
        if not relative_path:
            continue
        rows.append({"relative_path": relative_path, "manifest_entry": item})
    return rows


def _full_markdown_text(relative_path: str) -> str:
    """Read the FULL markdown file. Unbounded; expert briefs cap out
    around 30-40 KiB so the memory cost is bounded by corpus size
    (~3 MB across all 105 docs)."""
    absolute = (_KNOWLEDGE_BASE_ROOT / relative_path).resolve()
    if not absolute.exists():
        return ""
    try:
        return absolute.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


@lru_cache(maxsize=1)
def article_to_doc_ids() -> dict[str, frozenset[str]]:
    """Build the index once per process. Returns
    `{normalized_article_key: frozenset({sanitized_doc_id, ...})}`.

    Reads the full markdown for each interpretation doc (not the
    catalog's 12K preview), so refs deep in the file are captured.
    The catalog stays untouched — its preview-cap is the right design
    for the panel's runtime read path; for the article→doc index we
    explicitly want full coverage.
    """
    result: dict[str, set[str]] = {}
    for entry in _iter_interpretation_manifest_entries():
        rel = entry["relative_path"]
        doc_id = _sanitize_doc_id(rel)
        if not doc_id:
            continue
        full_text = _full_markdown_text(rel)
        if not full_text:
            continue
        refs = extract_article_refs(full_text)
        for ref in refs:
            key = normalize_article_key(ref)
            if not key:
                continue
            result.setdefault(key, set()).add(doc_id)
    return {key: frozenset(values) for key, values in result.items()}


def doc_ids_for_article_refs(
    article_refs: Iterable[str],
) -> frozenset[str]:
    """Union of doc_ids that interpret any of the given article refs."""
    index = article_to_doc_ids()
    out: set[str] = set()
    for ref in article_refs:
        key = normalize_article_key(ref)
        if not key:
            continue
        out.update(index.get(key, frozenset()))
    return frozenset(out)


def reset_cache() -> None:
    """For tests + ingest-refresh: drop the memoized index."""
    article_to_doc_ids.cache_clear()


__all__ = [
    "article_to_doc_ids",
    "doc_ids_for_article_refs",
    "normalize_article_key",
    "reset_cache",
]
