"""Section-type-aware chunker (Phase 1.6 of ingestfixv1).

Consumes canonical-template markdown (the output of
:mod:`lia_graph.ingestion_section_coercer`) and splits it into
section-typed :class:`Chunk` objects. Each chunk is tagged with one of
five ``section_type`` values so downstream stores (Supabase
``document_chunks.chunk_section_type``, FalkorDB nodes, the retriever's
hybrid search) can surface the right context per question:

- ``vigente``     — the operative legal text we cite as authoritative.
- ``historical``  — superseded / derogated / change-log content.
- ``operational`` — how-to / conditions / interpretation risk.
- ``metadata``    — identification, cross-references, vigencia checks,
  and the ``## Metadata v2`` block.
- ``general``     — reserved for off-template sections that ever escape
  the coercer.

The canonical 8 H2 headings (see
:data:`lia_graph.ingestion_section_coercer.CANONICAL_SECTIONS`) each map
to one of the five types via :data:`_SECTION_TYPE_MAP`. Any unknown
section -- including the ``## Metadata v2`` block -- falls back to
``metadata``. Content above the first H2 (front matter / preamble) is
also treated as ``metadata``.

Phase 2 and Phase 5b plug this module into
:class:`lia_graph.ingestion.supabase_sink.SupabaseCorpusSink`; the sink
today still chunks from ``ParsedArticle``, so this file only exposes a
pure, side-effect-free helper plus two optional trace events
(``ingest.chunk.start`` / ``ingest.chunk.done``) that are OFF by default
so unit tests don't pollute ``logs/events.jsonl``.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from .instrumentation import emit_event

__all__ = [
    "Chunk",
    "_SECTION_TYPE_MAP",
    "chunk_canonical_markdown",
    "section_type_distribution",
]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Default max chars per chunk before we split on blank-line boundaries.
_SOFT_MAX_CHARS = 1600

#: Placeholder emitted by the coercer for empty canonical sections.
_PLACEHOLDER = "(sin datos)"

#: Canonical section heading (normalized, lowercase + accent-folded) →
#: chunk ``section_type``. Keys MUST be normalized via
#: :func:`_normalize_heading` before lookup.
_SECTION_TYPE_MAP: dict[str, str] = {
    "identificacion": "metadata",
    "texto base referenciado (resumen tecnico)": "vigente",
    "regla operativa para lia": "operational",
    "condiciones de aplicacion": "operational",
    "riesgos de interpretacion": "operational",
    "relaciones normativas": "metadata",
    "checklist de vigencia": "metadata",
    "historico de cambios": "historical",
    # The coercer always emits a ``## Metadata v2`` block at the top of
    # the canonical document; it is an implicit metadata section.
    "metadata v2": "metadata",
}


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Chunk:
    """A single, section-typed slice of a canonical document."""

    text: str
    section_heading: str
    section_type: str
    position: int


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def chunk_canonical_markdown(
    markdown: str,
    *,
    min_chars: int = 80,
    filename: str | None = None,
    emit_events: bool = False,
) -> list[Chunk]:
    """Split canonical-template ``markdown`` into section-typed chunks.

    The input is expected to come from
    :func:`lia_graph.ingestion_section_coercer.coerce_to_canonical_template`
    but we defensively handle any markdown with H2 headings.

    Rules
    -----
    - Split on ``^## `` H2 headings. Headings are matched
      accent/case-insensitively against :data:`_SECTION_TYPE_MAP`.
    - One chunk per section, unless the body exceeds ~1600 chars — then
      split on double-newline boundaries; each piece keeps the same
      ``section_type`` and ``section_heading``.
    - Sections whose body is empty or just ``(sin datos)`` (shorter than
      ``min_chars``) are skipped entirely.
    - Preamble (content above the first H2) becomes one ``metadata``
      chunk with ``section_heading=""``.
    - ``position`` is a 0-based, strictly increasing index across the
      entire document.

    Parameters
    ----------
    markdown:
        The canonical markdown body. May be empty (returns ``[]``).
    min_chars:
        Minimum body length to emit a chunk; ``(sin datos)`` placeholder
        sections drop out naturally because their stripped length (9)
        is well below the default 80.
    filename:
        Optional filename included in trace event payloads.
    emit_events:
        When ``True``, emit ``ingest.chunk.start`` / ``ingest.chunk.done``
        via :func:`lia_graph.instrumentation.emit_event`. Defaults to
        ``False`` so unit tests stay silent.
    """

    filename_value = filename or ""
    raw = markdown or ""

    if emit_events:
        _emit("ingest.chunk.start", {"filename": filename_value, "char_count": len(raw)})

    chunks: list[Chunk] = []

    if not raw.strip():
        if emit_events:
            _emit(
                "ingest.chunk.done",
                {
                    "filename": filename_value,
                    "chunk_count": 0,
                    "section_type_distribution": {},
                },
            )
        return chunks

    # Normalize line endings so offset math below is stable across
    # Windows-authored docs.
    text = raw.replace("\r\n", "\n").replace("\r", "\n")

    position = 0
    for heading, body in _iter_sections(text):
        canonical_heading, section_type = _resolve_section(heading)
        for piece in _split_long_section(body, _SOFT_MAX_CHARS):
            stripped = piece.strip()
            if len(stripped) < min_chars:
                continue
            chunks.append(
                Chunk(
                    text=stripped,
                    section_heading=canonical_heading,
                    section_type=section_type,
                    position=position,
                )
            )
            position += 1

    if emit_events:
        _emit(
            "ingest.chunk.done",
            {
                "filename": filename_value,
                "chunk_count": len(chunks),
                "section_type_distribution": section_type_distribution(chunks),
            },
        )

    return chunks


def section_type_distribution(chunks: Iterable[Chunk]) -> dict[str, int]:
    """Return a ``{section_type: count}`` map for ``chunks``.

    Used by the trace-event payload so we can watch corpus rebuilds
    shift the mix of ``vigente`` vs ``historical`` content over time.
    """
    counter: Counter[str] = Counter(chunk.section_type for chunk in chunks)
    return dict(counter)


# ---------------------------------------------------------------------------
# Parsing helpers (private)
# ---------------------------------------------------------------------------


_HEADING_RE = re.compile(r"^##[ \t]+(.+?)\s*$", re.MULTILINE)


def _iter_sections(text: str) -> Iterable[tuple[str, str]]:
    """Yield ``(heading, body)`` pairs for every H2 block in ``text``.

    The preamble (content above the first H2) is yielded first as a
    pair with ``heading=""`` so callers can treat it as a metadata
    chunk. Sections with no body still yield an empty-body pair; the
    caller is responsible for skipping empties via ``min_chars``.
    """
    matches = list(_HEADING_RE.finditer(text))
    if not matches:
        preamble = text.strip()
        if preamble:
            yield "", preamble
        return

    preamble = text[: matches[0].start()].strip()
    if preamble:
        yield "", preamble

    for idx, match in enumerate(matches):
        heading = match.group(1).strip()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = text[start:end].strip("\n").rstrip()
        yield heading, body


def _normalize_heading(raw: str) -> str:
    """Lowercase + NFKD accent-fold + collapse whitespace.

    Mirrors the helper used by the section coercer so downstream lookups
    against :data:`_SECTION_TYPE_MAP` are stable across inputs that
    differ only in diacritics or spacing.
    """
    text = unicodedata.normalize("NFKD", raw or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _resolve_section(heading: str) -> tuple[str, str]:
    """Resolve a raw heading to ``(canonical_heading, section_type)``.

    - Empty heading ⇒ preamble ⇒ ``metadata``.
    - Known canonical heading (accent/case insensitive) ⇒ its mapped
      type; canonical heading echoes the input (stripped).
    - Any other heading ⇒ ``metadata`` default.
    """
    if not heading:
        return "", "metadata"
    normalized = _normalize_heading(heading)
    section_type = _SECTION_TYPE_MAP.get(normalized, "metadata")
    return heading.strip(), section_type


def _split_long_section(body: str, soft_max: int) -> list[str]:
    """Break ``body`` on double-newline boundaries when it is too long.

    Short bodies pass through unchanged as a single-element list so the
    caller can iterate uniformly. Splits greedily: we accumulate
    paragraphs separated by blank lines until the running piece would
    exceed ``soft_max``, then start a new piece. A single paragraph
    longer than ``soft_max`` is emitted whole — we never slice inside a
    paragraph, because legal text depends on clause cohesion.
    """
    if not body:
        return [""]
    if len(body) <= soft_max:
        return [body]

    paragraphs = re.split(r"\n[ \t]*\n", body)
    pieces: list[str] = []
    current = ""
    for paragraph in paragraphs:
        paragraph = paragraph.strip("\n")
        if not paragraph.strip():
            continue
        if not current:
            current = paragraph
            continue
        candidate = f"{current}\n\n{paragraph}"
        if len(candidate) > soft_max:
            pieces.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        pieces.append(current)

    return pieces or [body]


def _emit(event_type: str, payload: dict[str, object]) -> None:
    """Thin wrapper so tests can monkeypatch
    ``lia_graph.ingestion_chunker.emit_event`` directly.

    We resolve ``emit_event`` from the module ``globals()`` on every
    call rather than closing over the imported reference so that
    ``monkeypatch.setattr(ingestion_chunker, "emit_event", ...)`` in
    tests takes effect without a reload.
    """
    globals()["emit_event"](event_type, payload)
