"""Reassemble full document markdown from Supabase `document_chunks` rows.

Extracted from `ui_text_utilities.py` during granularize-v2 (2026-04-20).
The host module was 1200 LOC of mixed concerns; this cluster has a single
self-contained identity: **given a `doc_id`, reconstruct the original
document markdown from the chunks the ingestion pipeline wrote to the
`document_chunks` table**, working around two non-obvious quirks of the
chunker's stored format:

  1. Every stored chunk starts with a `[authority | topic | path]`
     context-prefix decoration line added by ingestion. That line must be
     stripped before reassembly or it contaminates the rendered modal.

  2. The ingestion segmenter strips `##` markdown heading markers and
     inlines the bare heading text as a prefix before every following
     segment::

        Texto normativo vigente
        <paragraph 1>
        Texto normativo vigente
        <paragraph 2>

     The read path must re-emit `## Heading` so downstream section
     parsers (`_parse_markdown_sections`) locate named sections like
     "Texto normativo vigente" correctly.

The citation-profile modal's "Texto Vigente del Artículo" section depends
on this reconstruction being correct — in dev / staging / prod the
`documents.absolute_path` column is NULL (the knowledge_base files live on
the ingestion host, not the serving host), so Supabase chunks are the
**only** source of the original document text.

Follow-up tracked in `docs/next/citation_modal_read_path_followups.md`:
stop stripping `##` during ingestion so future document segments are
self-describing and this helper can become a passthrough.

Cross-module dependencies kept minimal:
  * `from .ingestion_chunker import _SECTION_TYPE_MAP` — late-imported
    inside `_reconstruct_chunk_markdown` to avoid loading the chunker for
    modules that only need, e.g., `_strip_chunk_context_prefix`.
  * `from .supabase_client import get_supabase_client` — late-imported
    inside `_sb_query_document_chunks`.
  * `from .pipeline_c.supabase_fetch import _resolve_sync_generation` —
    late-imported inside `_sb_assemble_document_markdown` so the cache key
    invalidates automatically across corpus generations.
  * `_ui()` for the event bus (`emit_event`) and `INDEX_FILE_PATH` — kept
    as a lazy accessor so the event sink stays monkeypatch-friendly for
    tests.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any


# Line-anchored regex for the ingestion context-prefix decoration, exactly
# as emitted by `ingestion_chunker._build_chunk_records` (see ingestion
# module for the producer side). The decoration is always the first line of
# the stored chunk_text.
_CHUNK_CONTEXT_PREFIX_RE = re.compile(r"^\[[^\]]*\|[^\]]*\|[^\]]*\]\s*$")

# Heuristic guard for `_match_heading_label`: a real section label is
# almost always < 120 chars. Body paragraphs that happen to begin with a
# label-matching prefix are long enough to fail this test.
_MAX_HEADING_LINE_CHARS = 120


def _ui() -> Any:
    """Lazy accessor for `lia_graph.ui_server` (avoids circular import)."""
    from . import ui_server as _mod
    return _mod


def _strip_chunk_context_prefix(chunk_text: str) -> str:
    """Drop the chunker's `[authority | topic | path]` decoration line.

    The decoration is always the first line of the stored chunk_text (see
    `ingestion_chunker._build_chunk_records`). If the first line does
    not match the pattern, pass the chunk through unchanged.
    """
    raw = str(chunk_text or "")
    if not raw:
        return ""
    lines = raw.split("\n", 1)
    first = lines[0].rstrip()
    if _CHUNK_CONTEXT_PREFIX_RE.match(first):
        return lines[1] if len(lines) > 1 else ""
    return raw


def _match_heading_label(line_lc: str, heading_labels: tuple[str, ...]) -> str | None:
    """Return the matching heading label if `line_lc` is one, else None.

    The chunker's `_semantic_segments` strips `##` markers and leaves the
    bare heading text on its own line. Headings in the corpus sometimes
    carry a parenthetical suffix (e.g. "Texto base referenciado (resumen
    tecnico)"), so we accept either an exact match or a `startswith` match
    on a short heading-shaped line. The short-line guard
    (`_MAX_HEADING_LINE_CHARS`) and the no-sentence-terminator guard avoid
    false positives on body paragraphs that happen to begin with a label.
    """
    if not line_lc or len(line_lc) > _MAX_HEADING_LINE_CHARS:
        return None
    if line_lc[-1] in ".!?;:":
        return None
    for label in heading_labels:
        if line_lc == label or line_lc.startswith(label + " ") or line_lc.startswith(label + "("):
            return label
    return None


def _reconstruct_chunk_markdown(chunk_bodies: list[str]) -> str:
    """Rebuild `## Heading` markdown from chunk bodies with inlined headings.

    Walks the concatenated chunk bodies line by line, collecting body lines
    into paragraph buffers that are flushed on blank lines or section
    transitions. When a line matches a known section label from
    `ingestion_chunker._SECTION_TYPE_MAP`, emit it as `## <Heading>` on
    first appearance and collapse subsequent consecutive occurrences of
    the same heading (the chunker inlines the heading before every
    paragraph).

    Adjacent identical paragraphs are deduplicated — the chunker uses
    `overlap_segments=1` so the last segment of chunk N is repeated as the
    first segment of chunk N+1; without paragraph-level dedup, reassembled
    text contains duplicate blocks at every chunk boundary.

    Unknown heading-shaped lines pass through as body text.
    """
    # Late import to avoid loading ingestion_chunker unless this fallback
    # is actually used at serve time.
    from .ingestion_chunker import _SECTION_TYPE_MAP

    heading_labels = tuple(
        sorted(
            {label.strip().lower() for label, _ in _SECTION_TYPE_MAP if label},
            key=len,
            reverse=True,  # longest prefix wins (e.g. "histórico de cambios" before "historico")
        )
    )
    if not heading_labels:
        return "\n\n".join(body.strip() for body in chunk_bodies if body.strip())

    output: list[str] = []
    current_section_label: str | None = None
    paragraph_buffer: list[str] = []
    last_emitted_paragraph: str | None = None

    def _flush_paragraph() -> None:
        nonlocal paragraph_buffer, last_emitted_paragraph
        if not paragraph_buffer:
            return
        paragraph_text = "\n".join(paragraph_buffer).strip()
        paragraph_buffer = []
        if not paragraph_text:
            return
        if paragraph_text == last_emitted_paragraph:
            # Chunk-overlap duplicate → drop
            return
        if output and output[-1] != "":
            output.append("")
        output.append(paragraph_text)
        last_emitted_paragraph = paragraph_text

    def _emit_heading(display_text: str) -> None:
        if output and output[-1] != "":
            output.append("")
        output.append(f"## {display_text}")
        output.append("")
        # A heading boundary also breaks paragraph-dedup state so that an
        # unrelated paragraph below a new heading can never collide with a
        # paragraph emitted under the previous heading.
        nonlocal last_emitted_paragraph
        last_emitted_paragraph = None

    for body in chunk_bodies:
        if not body:
            continue
        for raw_line in body.splitlines():
            line = raw_line.rstrip()
            stripped = line.strip()
            if not stripped:
                _flush_paragraph()
                continue
            matched_label = _match_heading_label(stripped.lower(), heading_labels)
            if matched_label is not None:
                _flush_paragraph()
                if matched_label == current_section_label:
                    # Repeated inline heading inside the same section → drop
                    continue
                _emit_heading(stripped)
                current_section_label = matched_label
                continue
            paragraph_buffer.append(line)

    _flush_paragraph()
    return "\n".join(output).strip()


def _sb_query_document_chunks(doc_id: str) -> list[dict[str, Any]]:
    """Query all chunk rows for a doc_id from Supabase, ordered by chunk_id."""
    from .supabase_client import get_supabase_client

    client = get_supabase_client()
    result = (
        client.table("document_chunks")
        .select("chunk_id, chunk_text")
        .eq("doc_id", doc_id)
        .order("chunk_id")
        .limit(200)
        .execute()
    )
    return list(result.data or [])


@lru_cache(maxsize=128)
def _sb_assemble_document_markdown_cached(doc_id: str, sync_generation: str) -> str:
    """Cached inner for `_sb_assemble_document_markdown`.

    The `sync_generation` parameter is part of the cache key so a reindex
    automatically invalidates cached text without needing to clear the
    cache explicitly. It is otherwise unused by the body.
    """
    del sync_generation  # signature-only cache key
    try:
        rows = _sb_query_document_chunks(doc_id)
    except Exception as exc:  # noqa: BLE001  — propagate via event, return empty
        try:
            _ui().emit_event(
                "citation_profile.supabase_fallback.failed",
                {
                    "doc_id": doc_id,
                    "error": f"{type(exc).__name__}: {exc}",
                    "stage": "query",
                },
            )
        except Exception:  # noqa: BLE001  — event bus must never crash the read path
            pass
        return ""

    chunk_bodies: list[str] = []
    for row in rows:
        chunk_text = str(row.get("chunk_text") or "")
        if not chunk_text.strip():
            continue
        chunk_bodies.append(_strip_chunk_context_prefix(chunk_text))

    if not chunk_bodies:
        return ""
    return _reconstruct_chunk_markdown(chunk_bodies)


def _sb_assemble_document_markdown(doc_id: str) -> str:
    """Reassemble full document markdown from Supabase `document_chunks`.

    Strips the chunker's context-prefix decoration and reconstructs `##`
    markdown headings from the bare-heading-prefix pattern so downstream
    parsers (e.g. `_parse_markdown_sections`) can locate named sections
    like "Texto normativo vigente". Returns an empty string on any error.

    Results are cached by `(doc_id, sync_generation)` — a new corpus
    generation invalidates all cached entries automatically.
    """
    clean = str(doc_id or "").strip()
    if not clean:
        return ""
    # Late import to avoid a module-load-time dependency on pipeline_c.
    try:
        from .pipeline_c.supabase_fetch import _resolve_sync_generation

        sync_generation = _resolve_sync_generation(_ui().INDEX_FILE_PATH) or ""
    except Exception:  # noqa: BLE001
        sync_generation = ""
    return _sb_assemble_document_markdown_cached(clean, sync_generation)
