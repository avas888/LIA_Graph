"""Supabase corpus sink.

Writes the same rows `materialize_graph_artifacts` already emits to
`artifacts/*.jsonl` and FalkorDB into the cloud Supabase schema so the Phase B
retriever can serve them back. Strictly additive: the artifact bundle + local
Falkor write stay authoritative for local dev.

Idempotency:

- `documents` upserts on `doc_id` (natural key).
- `document_chunks` upserts on `chunk_id` (unique column in the baseline
  schema). Rows carry `chunk_sha256` so downstream consumers can detect
  chunker drift across generations.
- `corpus_generations` upserts on `generation_id`; `finalize(activate=True)`
  performs a two-step active flip so the partial unique index
  `idx_corpus_generations_single_active` is never violated.
- `normative_edges` upserts on `(source_key, target_key, relation, generation_id)`
  via the `normative_edges_idempotency` index added in migration
  `20260418000000_normative_edges_unique.sql`.

The sink does NOT populate embeddings — `embedding_ops.py` fills them on a
follow-up run.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import logging
import re
from typing import Any

from ..graph.schema import EdgeKind, NodeKind
from ..ingestion.classifier import ClassifiedEdge
from ..ingestion.parser import ParsedArticle
from ..supabase_client import create_supabase_client_for_target

_log = logging.getLogger(__name__)

_BATCH_SIZE = 500

# Map of internal `EdgeKind` values onto the set allowed by the
# `normative_edges_relation_check` constraint in the baseline schema.
# The constraint allows exactly:
#   references | modifies | complements | exception_for | derogates
#   | supersedes | suspends | struck_down_by | revokes | cross_domain
# `REQUIRES`, `COMPUTATION_DEPENDS_ON`, `DEFINES`, `PART_OF` are graph-only
# concepts not represented in the Postgres normative_edges table — we skip
# those rows on purpose rather than map them to an unrelated relation.
_RELATION_MAP: dict[str, str] = {
    EdgeKind.REFERENCES.value: "references",
    EdgeKind.MODIFIES.value: "modifies",
    EdgeKind.SUPERSEDES.value: "supersedes",
    EdgeKind.EXCEPTION_TO.value: "exception_for",
}

_RELATION_DROP = frozenset(
    {
        EdgeKind.REQUIRES.value,
        EdgeKind.COMPUTATION_DEPENDS_ON.value,
        EdgeKind.DEFINES.value,
        EdgeKind.PART_OF.value,
    }
)

_ALLOWED_RELATIONS = frozenset(
    {
        "references",
        "modifies",
        "complements",
        "exception_for",
        "derogates",
        "supersedes",
        "suspends",
        "struck_down_by",
        "revokes",
        "cross_domain",
    }
)

_DOC_ID_SANITIZER = re.compile(r"[^A-Za-z0-9_.-]+")


def default_generation_id() -> str:
    return f"gen_{datetime.now(tz=timezone.utc).strftime('%Y%m%d%H%M%S')}"


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _iter_batches(rows: Sequence[dict[str, Any]], batch_size: int = _BATCH_SIZE) -> Iterable[list[dict[str, Any]]]:
    if not rows:
        return
    for start in range(0, len(rows), batch_size):
        yield list(rows[start : start + batch_size])


def _sanitize_doc_id(relative_path: str) -> str:
    stem = str(relative_path or "").strip().strip("/")
    if not stem:
        raise ValueError("cannot derive doc_id from empty relative_path")
    return _DOC_ID_SANITIZER.sub("_", stem).strip("_")


def _content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _chunk_sha(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _chunk_id(doc_id: str, article_key: str) -> str:
    return f"{doc_id}::{article_key}"


@dataclass(frozen=True)
class SupabaseSinkResult:
    generation_id: str
    target: str
    documents_written: int
    chunks_written: int
    edges_written: int
    edges_skipped_relation: int
    activated: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation_id": self.generation_id,
            "target": self.target,
            "documents_written": int(self.documents_written),
            "chunks_written": int(self.chunks_written),
            "edges_written": int(self.edges_written),
            "edges_skipped_relation": int(self.edges_skipped_relation),
            "activated": bool(self.activated),
        }


class SupabaseCorpusSink:
    """Writes corpus snapshot rows into the Supabase schema."""

    def __init__(
        self,
        *,
        target: str = "production",
        generation_id: str | None = None,
        client: Any | None = None,
    ) -> None:
        self.target = str(target or "production").strip().lower() or "production"
        self.generation_id = str(generation_id or default_generation_id()).strip()
        if not self.generation_id:
            raise ValueError("generation_id cannot be empty")
        self._client = client if client is not None else create_supabase_client_for_target(self.target)
        self._documents_written = 0
        self._chunks_written = 0
        self._edges_written = 0
        self._edges_skipped_relation = 0
        self._generation_row_written = False
        self._file_list: list[str] = []
        self._activated = False

    @property
    def client(self) -> Any:
        return self._client

    def write_generation(
        self,
        *,
        documents: int,
        chunks: int,
        countries: Sequence[str] = ("colombia",),
        files: Sequence[str] = (),
        knowledge_class_counts: dict[str, int] | None = None,
        index_dir: str = "",
    ) -> None:
        now = _now_iso()
        payload = {
            "generation_id": self.generation_id,
            "generated_at": now,
            "activated_at": now,
            "documents": int(documents),
            "chunks": int(chunks),
            "countries": [str(c) for c in countries if str(c or "").strip()],
            "files": [str(f) for f in files if str(f or "").strip()],
            "knowledge_class_counts": dict(knowledge_class_counts or {}),
            "index_dir": str(index_dir or ""),
            "is_active": False,
            "created_at": now,
            "updated_at": now,
        }
        self._client.table("corpus_generations").upsert(
            payload, on_conflict="generation_id"
        ).execute()
        self._file_list = list(payload["files"])
        self._generation_row_written = True

    def write_documents(
        self,
        documents: Sequence[dict[str, Any]],
    ) -> tuple[dict[str, str], int]:
        """Return `(doc_id_by_source_path, written_count)`."""
        rows: list[dict[str, Any]] = []
        doc_id_by_source_path: dict[str, str] = {}
        now = _now_iso()
        seen_doc_ids: set[str] = set()
        for document in documents:
            source_path = str(document.get("source_path") or "").strip()
            relative_path = str(document.get("relative_path") or source_path).strip()
            if not relative_path:
                continue
            doc_id = _sanitize_doc_id(relative_path)
            if not doc_id or doc_id in seen_doc_ids:
                continue
            seen_doc_ids.add(doc_id)
            if source_path:
                doc_id_by_source_path[source_path] = doc_id
            markdown = str(document.get("markdown") or "")
            row = {
                "doc_id": doc_id,
                "relative_path": relative_path,
                "source_type": str(document.get("source_type") or document.get("document_archetype") or "unknown"),
                "topic": str(document.get("topic_key") or "unknown"),
                "authority": str(document.get("authority_level") or "unknown"),
                "pais": str(document.get("pais") or "colombia"),
                "knowledge_class": str(document.get("knowledge_class") or "unknown"),
                "tema": document.get("topic_key"),
                "subtema": document.get("subtopic_key"),
                "tipo_de_documento": document.get("document_archetype"),
                "corpus": document.get("family"),
                "content_hash": _content_hash(markdown),
                "filename_normalized": relative_path,
                "first_heading": str(document.get("title_hint") or "")[:500],
                "curation_status": "raw",
                "sync_generation": self.generation_id,
                "created_at": now,
                "updated_at": now,
            }
            rows.append(row)

        written = 0
        for batch in _iter_batches(rows):
            self._client.table("documents").upsert(batch, on_conflict="doc_id").execute()
            written += len(batch)
        self._documents_written += written
        return doc_id_by_source_path, written

    def write_chunks(
        self,
        articles: Sequence[ParsedArticle],
        *,
        doc_id_by_source_path: dict[str, str],
    ) -> int:
        rows: list[dict[str, Any]] = []
        now = _now_iso()
        seen_chunk_ids: set[str] = set()
        for article in articles:
            source_path = str(article.source_path or "").strip()
            doc_id = doc_id_by_source_path.get(source_path)
            if not doc_id:
                continue
            chunk_id = _chunk_id(doc_id, article.article_key)
            if chunk_id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(chunk_id)
            chunk_text = article.full_text or article.body or article.heading or ""
            row = {
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "chunk_text": chunk_text,
                "summary": article.heading or None,
                "concept_tags": list(article.reform_references),
                "chunk_sha256": _chunk_sha(chunk_text),
                "source_type": "article",
                "curation_status": "raw",
                "topic": None,
                "pais": "colombia",
                "authority": None,
                "vigencia": "vigente" if article.status != "derogado" else "derogada",
                "retrieval_visibility": "primary",
                "relative_path": None,
                "knowledge_class": "normative_base",
                "sync_generation": self.generation_id,
                "chunk_section_type": "vigente" if article.status != "derogado" else "historical",
                "created_at": now,
            }
            rows.append(row)

        written = 0
        for batch in _iter_batches(rows):
            self._client.table("document_chunks").upsert(
                batch, on_conflict="chunk_id"
            ).execute()
            written += len(batch)
        self._chunks_written += written
        return written

    def write_normative_edges(
        self,
        edges: Sequence[ClassifiedEdge],
    ) -> int:
        rows: list[dict[str, Any]] = []
        now = _now_iso()
        seen: set[tuple[str, str, str]] = set()
        for edge in edges:
            kind_value = edge.record.kind.value
            if kind_value in _RELATION_DROP:
                self._edges_skipped_relation += 1
                continue
            relation = _RELATION_MAP.get(kind_value)
            assert relation is not None and relation in _ALLOWED_RELATIONS, (
                f"Unknown ClassifiedEdge.kind={kind_value!r} — update _RELATION_MAP "
                "or _RELATION_DROP before writing to normative_edges."
            )
            source_key = str(edge.record.source_key or "").strip()
            target_key = str(edge.record.target_key or "").strip()
            if not source_key or not target_key:
                continue
            dedup_key = (source_key, target_key, relation)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            basis_text = str(edge.record.properties.get("raw_reference") or "") or None
            rows.append(
                {
                    "source_key": source_key,
                    "target_key": target_key,
                    "relation": relation,
                    "confidence": float(edge.confidence or 0.0),
                    "generation_id": self.generation_id,
                    "created_at": now,
                    "basis_text": basis_text,
                }
            )

        written = 0
        for batch in _iter_batches(rows):
            self._client.table("normative_edges").upsert(
                batch, on_conflict="source_key,target_key,relation,generation_id"
            ).execute()
            written += len(batch)
        self._edges_written += written
        return written

    def finalize(self, *, activate: bool) -> SupabaseSinkResult:
        if activate:
            self._activate_generation()
            self._activated = True
        return SupabaseSinkResult(
            generation_id=self.generation_id,
            target=self.target,
            documents_written=self._documents_written,
            chunks_written=self._chunks_written,
            edges_written=self._edges_written,
            edges_skipped_relation=self._edges_skipped_relation,
            activated=self._activated,
        )

    def _activate_generation(self) -> None:
        """Two-step active flip to honor `idx_corpus_generations_single_active`.

        1. Deactivate every existing row where `is_active = true`.
        2. Activate this generation.

        The partial unique index only allows one row with `is_active = true`,
        so we must clear all prior actives before setting this generation
        active. Supabase PostgREST does not expose MVCC transactions, but the
        partial unique index ensures at-most-one active row even when the
        two steps interleave.
        """
        if not self._generation_row_written:
            raise RuntimeError(
                "finalize(activate=True) requires a prior write_generation() call."
            )
        now = _now_iso()
        deactivate_payload = {"is_active": False, "updated_at": now}
        self._client.table("corpus_generations").update(deactivate_payload).neq(
            "generation_id", self.generation_id
        ).eq("is_active", True).execute()
        activate_payload = {
            "is_active": True,
            "activated_at": now,
            "updated_at": now,
        }
        self._client.table("corpus_generations").update(activate_payload).eq(
            "generation_id", self.generation_id
        ).execute()


__all__ = [
    "SupabaseCorpusSink",
    "SupabaseSinkResult",
    "default_generation_id",
]
