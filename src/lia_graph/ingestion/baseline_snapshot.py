"""Baseline snapshot reader for the additive-corpus-v1 delta planner.

See ``docs/next/additive_corpusv1.md`` §5 Phase 2.

The baseline snapshot is the in-memory projection of whatever is currently
persisted in Supabase for a given ``generation_id`` (typically the rolling
``gen_active_rolling`` row introduced by the 20260422000000 migration). The
delta planner consumes this snapshot against the on-disk corpus to classify
each document into added / modified / removed / unchanged buckets.

**Purity.** This module performs read-only PostgREST calls via the supplied
Supabase client. No writes, no classifier invocation, no markdown reads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


DEFAULT_GENERATION_ID = "gen_active_rolling"

# PostgREST caps `range()` at 1000 rows by default; we paginate explicitly so
# a 1313-doc corpus (and future 5k-10k) works without server-side tuning.
_PAGE_SIZE = 1000


@dataclass(frozen=True)
class BaselineDocument:
    """Per-document projection used by the planner."""

    doc_id: str
    relative_path: str
    content_hash: str | None
    doc_fingerprint: str | None
    retired_at: str | None
    last_delta_id: str | None
    sync_generation: str | None


@dataclass(frozen=True)
class BaselineSnapshot:
    """In-memory projection of a corpus generation."""

    generation_id: str
    documents_by_relative_path: dict[str, BaselineDocument] = field(default_factory=dict)
    total_docs: int = 0
    total_chunks: int = 0
    total_edges: int = 0
    retired_docs: int = 0

    @property
    def is_empty(self) -> bool:
        return self.total_docs == 0

    def get(self, relative_path: str) -> BaselineDocument | None:
        return self.documents_by_relative_path.get(relative_path)


def _coerce_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _row_to_document(row: Mapping[str, Any]) -> BaselineDocument | None:
    doc_id = _coerce_str(row.get("doc_id"))
    relative_path = _coerce_str(row.get("relative_path"))
    if not doc_id or not relative_path:
        return None
    return BaselineDocument(
        doc_id=doc_id,
        relative_path=relative_path,
        content_hash=_coerce_str(row.get("content_hash")),
        doc_fingerprint=_coerce_str(row.get("doc_fingerprint")),
        retired_at=_coerce_str(row.get("retired_at")),
        last_delta_id=_coerce_str(row.get("last_delta_id")),
        sync_generation=_coerce_str(row.get("sync_generation")),
    )


def _paginate_select(
    client: Any,
    *,
    table: str,
    projection: str,
    generation_id: str,
    page_size: int = _PAGE_SIZE,
) -> list[dict[str, Any]]:
    """Return every row matching ``sync_generation=generation_id``."""
    out: list[dict[str, Any]] = []
    offset = 0
    while True:
        resp = (
            client.table(table)
            .select(projection)
            .eq("sync_generation", generation_id)
            .order("doc_id")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = list(getattr(resp, "data", None) or [])
        if not rows:
            break
        out.extend(rows)
        if len(rows) < page_size:
            break
        offset += len(rows)
    return out


def _count_rows(client: Any, *, table: str, generation_id: str, filters: dict[str, Any] | None = None) -> int:
    """Best-effort count via PostgREST. Returns 0 on any error."""
    try:
        query = client.table(table).select("*", count="exact").eq("sync_generation", generation_id)
        for col, val in (filters or {}).items():
            query = query.eq(col, val)
        # Range(0,0) keeps the response body tiny; we only need count.
        resp = query.range(0, 0).execute()
    except Exception:  # noqa: BLE001
        return 0
    count = getattr(resp, "count", None)
    if count is None:
        return 0
    try:
        return int(count)
    except (TypeError, ValueError):
        return 0


def _count_edges(client: Any, *, generation_id: str) -> int:
    try:
        resp = (
            client.table("normative_edges")
            .select("id", count="exact")
            .eq("generation_id", generation_id)
            .range(0, 0)
            .execute()
        )
    except Exception:  # noqa: BLE001
        return 0
    count = getattr(resp, "count", None)
    if count is None:
        return 0
    try:
        return int(count)
    except (TypeError, ValueError):
        return 0


# Explicit projection so schema drift never silently drops a needed field.
_DOCUMENTS_PROJECTION = (
    "doc_id, relative_path, content_hash, doc_fingerprint, retired_at, "
    "last_delta_id, sync_generation"
)


def load_baseline_snapshot(
    client: Any,
    *,
    generation_id: str = DEFAULT_GENERATION_ID,
) -> BaselineSnapshot:
    """Load the documents + aggregate counts for ``generation_id``.

    Legacy rows missing ``doc_fingerprint`` or ``retired_at`` (pre-Phase-1)
    are returned with those fields set to ``None``. The planner treats
    ``doc_fingerprint IS NULL`` as "needs a fingerprint, treat as modified
    on the first delta" — the backfill script is the recommended remedy.
    """
    gen_id = str(generation_id or DEFAULT_GENERATION_ID).strip() or DEFAULT_GENERATION_ID

    raw_rows = _paginate_select(
        client,
        table="documents",
        projection=_DOCUMENTS_PROJECTION,
        generation_id=gen_id,
    )

    documents_by_relative_path: dict[str, BaselineDocument] = {}
    retired = 0
    for row in raw_rows:
        doc = _row_to_document(row)
        if doc is None:
            continue
        # If two rows share a relative_path (shouldn't happen; upsert is
        # keyed on doc_id), the later row wins — deterministic by the
        # order("doc_id") clause above.
        documents_by_relative_path[doc.relative_path] = doc
        if doc.retired_at:
            retired += 1

    total_chunks = _count_rows(
        client,
        table="document_chunks",
        generation_id=gen_id,
    )
    total_edges = _count_edges(client, generation_id=gen_id)

    return BaselineSnapshot(
        generation_id=gen_id,
        documents_by_relative_path=documents_by_relative_path,
        total_docs=len(documents_by_relative_path),
        total_chunks=total_chunks,
        total_edges=total_edges,
        retired_docs=retired,
    )


__all__ = [
    "BaselineDocument",
    "BaselineSnapshot",
    "DEFAULT_GENERATION_ID",
    "load_baseline_snapshot",
]
