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
from ..ingestion.fingerprint import (
    classifier_output_from_corpus_document,
    compute_doc_fingerprint,
)
from ..ingestion.parser import ParsedArticle
from ..supabase_client import create_supabase_client_for_target

_log = logging.getLogger(__name__)

_BATCH_SIZE = 500

# Map of internal `EdgeKind` values onto the set allowed by the
# `normative_edges_relation_check` constraint in the baseline schema.
# The constraint allows exactly:
#   references | modifies | complements | exception_for | derogates
#   | supersedes | suspends | struck_down_by | revokes | cross_domain
_RELATION_MAP: dict[str, str] = {
    EdgeKind.REFERENCES.value: "references",
    EdgeKind.MODIFIES.value: "modifies",
    EdgeKind.SUPERSEDES.value: "supersedes",
    EdgeKind.EXCEPTION_TO.value: "exception_for",
    # Gap #1 resolution (docs/next/ingestion_suin.md): REQUIRES and
    # COMPUTATION_DEPENDS_ON previously got silently dropped. Map them onto
    # `references` so the downstream retriever at least sees the link — the
    # graph still carries the finer-grained EdgeKind for Falkor traversal.
    EdgeKind.REQUIRES.value: "references",
    EdgeKind.COMPUTATION_DEPENDS_ON.value: "references",
    # SUIN-derived kinds (Phase B mapping table).
    EdgeKind.DEROGATES.value: "derogates",
    EdgeKind.REGLAMENTA.value: "complements",
    EdgeKind.SUSPENDS.value: "suspends",
    EdgeKind.ANULA.value: "revokes",
    EdgeKind.DECLARES_EXEQUIBLE.value: "references",
    EdgeKind.STRUCK_DOWN_BY.value: "struck_down_by",
}

# Graph-only concepts with no Postgres analogue — persisted in Falkor but not
# in normative_edges. DEFINES is a vocabulary relation and PART_OF is purely
# structural; promoting either to `references` would mislead consumers.
_RELATION_DROP = frozenset(
    {
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


def _derive_source_type(article_key: str, article_number: str) -> str:
    """Map parsed-article shape → chunk source_type.

    - numeric statutory article (e.g. "512-1"): "article"
    - whole-document fallback (article_key == "doc"): "document"
    - section slug under v2-template / práctica / interpretación fallback: "section"
    """
    if article_number and article_key == article_number:
        return "article"
    if article_key == "doc":
        return "document"
    return "section"


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


@dataclass(frozen=True)
class SupabaseDeltaResult:
    """Per-bucket row-count report returned by ``write_delta``.

    Additive-corpus-v1 Phase 4 — see ``docs/next/additive_corpusv1.md`` §5.
    """

    generation_id: str
    target: str
    delta_id: str
    documents_added: int
    documents_modified: int
    documents_retired: int
    chunks_written: int
    chunks_deleted: int
    edges_written: int
    edges_deleted: int
    dangling_upserted: int
    dangling_promoted: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation_id": self.generation_id,
            "target": self.target,
            "delta_id": self.delta_id,
            "documents_added": int(self.documents_added),
            "documents_modified": int(self.documents_modified),
            "documents_retired": int(self.documents_retired),
            "chunks_written": int(self.chunks_written),
            "chunks_deleted": int(self.chunks_deleted),
            "edges_written": int(self.edges_written),
            "edges_deleted": int(self.edges_deleted),
            "dangling_upserted": int(self.dangling_upserted),
            "dangling_promoted": int(self.dangling_promoted),
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
        # subtopic wire-up (ingestfix-v2 Phase 4): write_documents populates
        # these so write_chunks can inherit subtema per-parent without an
        # extra round-trip to Supabase.
        self._subtema_by_doc_id: dict[str, str] = {}
        self._topic_by_doc_id: dict[str, str] = {}
        self._docs_with_subtopic = 0
        self._docs_requiring_subtopic_review = 0
        # ingestionfix_v2 §4 Phase 7a: tag-review skeleton rows buffered
        # during write_documents and flushed after the documents upsert.
        self._pending_tag_review_rows: list[dict[str, Any]] = []

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
            subtopic_key = document.get("subtopic_key")
            subtopic_key_clean: str | None = None
            if isinstance(subtopic_key, str):
                stripped = subtopic_key.strip()
                if stripped:
                    subtopic_key_clean = stripped
            requires_subtopic_review = bool(
                document.get("requires_subtopic_review") or False
            )
            topic_key = str(document.get("topic_key") or "unknown")
            content_hash = _content_hash(markdown)
            # ingestionfix_v2 §4 Phase 6: compute doc_fingerprint inline at
            # write-time so future deltas can use the content-hash shortcut
            # without a separate backfill pass. The helper picks the same
            # subset of classifier fields that the backfill path does (see
            # tests/test_fingerprint.py case (f) for the parity assertion).
            doc_fingerprint = compute_doc_fingerprint(
                content_hash=content_hash,
                classifier_output=classifier_output_from_corpus_document(document),
            )
            row = {
                "doc_id": doc_id,
                "relative_path": relative_path,
                "source_type": str(document.get("source_type") or document.get("document_archetype") or "unknown"),
                "topic": topic_key,
                "authority": str(document.get("authority_level") or "unknown"),
                "pais": str(document.get("pais") or "colombia"),
                "knowledge_class": str(document.get("knowledge_class") or "unknown"),
                "tema": document.get("topic_key"),
                "subtema": subtopic_key_clean,
                "tipo_de_documento": document.get("document_archetype"),
                "corpus": document.get("family"),
                "content_hash": content_hash,
                "doc_fingerprint": doc_fingerprint,
                "filename_normalized": relative_path,
                "first_heading": str(document.get("title_hint") or "")[:500],
                "curation_status": "raw",
                "sync_generation": self.generation_id,
                "requires_subtopic_review": requires_subtopic_review,
                "created_at": now,
                "updated_at": now,
            }
            if subtopic_key_clean:
                self._subtema_by_doc_id[doc_id] = subtopic_key_clean
                self._docs_with_subtopic += 1
            if requires_subtopic_review:
                self._docs_requiring_subtopic_review += 1
            if topic_key and topic_key != "unknown":
                self._topic_by_doc_id[doc_id] = topic_key
            rows.append(row)

            # ingestionfix_v2 §4 Phase 7a — tag-review skeleton row.
            # Insert one open review row per doc whose classification needs
            # an expert to look at it. The `/api/tags/review` endpoints
            # surface these for curation.
            if requires_subtopic_review:
                self._pending_tag_review_rows.append(
                    {
                        "review_id": f"rev_{doc_id}_{int(datetime.now(timezone.utc).timestamp())}",
                        "doc_id": doc_id,
                        "trigger_reason": "requires_review_flag",
                        "snapshot_topic": topic_key if topic_key != "unknown" else None,
                        "snapshot_subtopic": subtopic_key_clean,
                        "snapshot_confidence": None,
                        "created_at": now,
                        "updated_at": now,
                    }
                )

        written = 0
        for batch in _iter_batches(rows):
            self._client.table("documents").upsert(batch, on_conflict="doc_id").execute()
            written += len(batch)
        self._documents_written += written

        # Phase 7a: flush tag-review skeleton rows after documents land so
        # the FK constraint on document_tag_reviews.doc_id is satisfied.
        # ON CONFLICT DO NOTHING on the partial unique index so re-ingesting
        # a doc that's still under open review doesn't dup the queue.
        if self._pending_tag_review_rows:
            try:
                for batch in _iter_batches(self._pending_tag_review_rows):
                    self._client.table("document_tag_reviews").upsert(
                        batch,
                        on_conflict="review_id",
                    ).execute()
            except Exception as exc:  # noqa: BLE001 — review queue is best-effort
                _log.warning(
                    "tag_review_skeleton_flush_failed", extra={"err": str(exc)}
                )
            self._pending_tag_review_rows.clear()

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
            inherited_subtema = self._subtema_by_doc_id.get(doc_id)
            inherited_topic = self._topic_by_doc_id.get(doc_id)
            row = {
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "chunk_text": chunk_text,
                "summary": article.heading or None,
                "concept_tags": list(article.reform_references),
                "chunk_sha256": _chunk_sha(chunk_text),
                "source_type": _derive_source_type(article.article_key, article.article_number),
                "curation_status": "raw",
                "topic": inherited_topic,
                "pais": "colombia",
                "authority": None,
                "vigencia": "vigente" if article.status != "derogado" else "derogada",
                "retrieval_visibility": "primary",
                "relative_path": None,
                "tema": inherited_topic,
                "subtema": inherited_subtema,
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
                    # ingestionfix_v2 §4 Phase 4 — Spanish-taxonomy typing +
                    # authority weight. Both nullable at the DB level so
                    # pre-Phase-4 rows remain valid.
                    "edge_type": edge.edge_type,
                    "weight": float(edge.weight) if edge.weight is not None else 1.0,
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

    # -----------------------------------------------------------------
    # Additive-corpus-v1 Phase 4 — write_delta
    # -----------------------------------------------------------------

    def write_delta(
        self,
        delta: Any,  # CorpusDelta (importing delta_planner here would be circular-ish)
        *,
        documents: Sequence[dict[str, Any]],
        articles: Sequence[ParsedArticle],
        edges: Sequence[ClassifiedEdge],
        dangling_store: Any,
    ) -> SupabaseDeltaResult:
        """Apply a planned ``CorpusDelta`` to the rolling generation.

        * ``documents`` — full doc-payload dicts (same shape ``write_documents``
          expects) for every doc in ``delta.added`` ∪ ``delta.modified``.
        * ``articles`` — parsed articles belonging to delta docs (added/modified).
        * ``edges`` — classified edges extracted from the delta articles.
        * ``dangling_store`` — persistent store for unresolved ARTICLE targets.

        See ``docs/next/additive_corpusv1.md`` §5 Phase 4 for the per-bucket
        semantics. This method does NOT flip ``corpus_generations.is_active``;
        the caller owns activation (``finalize(activate=True)`` or the Phase 6
        orchestrator path).
        """
        from ..instrumentation import emit_event as _emit

        delta_id = str(getattr(delta, "delta_id", "") or "").strip()
        _emit(
            "ingest.delta.sink.start",
            {
                "delta_id": delta_id,
                "target": self.target,
                "generation_id": self.generation_id,
                "added": len(getattr(delta, "added", ())),
                "modified": len(getattr(delta, "modified", ())),
                "removed": len(getattr(delta, "removed", ())),
            },
        )

        added_entries = list(getattr(delta, "added", ()) or ())
        modified_entries = list(getattr(delta, "modified", ()) or ())
        removed_entries = list(getattr(delta, "removed", ()) or ())

        # Short-circuit on empty delta (per Decision E1 reviewer amendment:
        # empty deltas skip downstream work altogether).
        if not added_entries and not modified_entries and not removed_entries:
            _emit(
                "ingest.delta.sink.done",
                {
                    "delta_id": delta_id,
                    "target": self.target,
                    "documents_added": 0,
                    "documents_modified": 0,
                    "documents_retired": 0,
                    "chunks_written": 0,
                    "chunks_deleted": 0,
                    "edges_written": 0,
                    "edges_deleted": 0,
                },
            )
            return SupabaseDeltaResult(
                generation_id=self.generation_id,
                target=self.target,
                delta_id=delta_id,
                documents_added=0,
                documents_modified=0,
                documents_retired=0,
                chunks_written=0,
                chunks_deleted=0,
                edges_written=0,
                edges_deleted=0,
                dangling_upserted=0,
                dangling_promoted=0,
            )

        # -------- Pass 1: upsert added + modified docs + chunks -------------
        # Preserve _subtema_by_doc_id / _topic_by_doc_id coupling (§3.9):
        # write_documents populates them, write_chunks consumes them.
        doc_id_by_source_path: dict[str, str] = {}
        if documents:
            doc_id_by_source_path, _ = self.write_documents(documents)

        # Tag added/modified docs with last_delta_id so diagnostics can trace
        # which delta touched each row. write_documents already set
        # sync_generation to self.generation_id; we patch last_delta_id via an
        # update keyed on the written doc_ids.
        touched_doc_ids = list(doc_id_by_source_path.values())
        for chunk_batch in _iter_batches(
            [{"doc_id": d, "last_delta_id": delta_id} for d in touched_doc_ids]
        ):
            if not chunk_batch:
                continue
            for item in chunk_batch:
                self._client.table("documents").update(
                    {"last_delta_id": item["last_delta_id"]}
                ).eq("doc_id", item["doc_id"]).execute()

        # For modified docs we must also remove chunks whose article_key is no
        # longer present in the fresh parse. Compute current chunk_id set,
        # diff against the just-written set, hard-delete the stragglers.
        modified_doc_ids = {
            entry.doc_id
            for entry in modified_entries
            if entry.doc_id
        }
        chunks_deleted = 0
        if modified_doc_ids:
            written_chunk_ids = {
                _chunk_id(doc_id_by_source_path.get(str(a.source_path or ""), ""), a.article_key)
                for a in articles
                if doc_id_by_source_path.get(str(a.source_path or "")) in modified_doc_ids
            }
            for doc_id in modified_doc_ids:
                resp = (
                    self._client.table("document_chunks")
                    .select("chunk_id")
                    .eq("doc_id", doc_id)
                    .execute()
                )
                current_ids = {
                    str(r.get("chunk_id") or "")
                    for r in list(getattr(resp, "data", None) or [])
                }
                stale = current_ids - written_chunk_ids
                for stale_id in stale:
                    if not stale_id:
                        continue
                    self._client.table("document_chunks").delete().eq(
                        "chunk_id", stale_id
                    ).execute()
                    chunks_deleted += 1

        # Write the fresh chunk set (idempotent upsert on chunk_id).
        chunks_written = 0
        if articles and doc_id_by_source_path:
            chunks_written = self.write_chunks(
                articles, doc_id_by_source_path=doc_id_by_source_path
            )

        # -------- Pass 2: retire removed docs --------------------------------
        chunks_deleted_retired = 0
        edges_deleted = 0
        retired_doc_ids: list[str] = []
        retired_article_keys: set[str] = set()
        for entry in removed_entries:
            baseline = entry.baseline
            if baseline is None or not baseline.doc_id:
                continue
            retired_doc_ids.append(baseline.doc_id)

        if retired_doc_ids:
            # Find article keys owned by retired docs via chunk_id prefix.
            for doc_id in retired_doc_ids:
                resp = (
                    self._client.table("document_chunks")
                    .select("chunk_id")
                    .eq("doc_id", doc_id)
                    .execute()
                )
                for raw in list(getattr(resp, "data", None) or []):
                    chunk_id = str(raw.get("chunk_id") or "")
                    if "::" in chunk_id:
                        _, _, article_key = chunk_id.partition("::")
                        if article_key:
                            retired_article_keys.add(article_key)
                # Hard-delete chunks for the retired doc.
                del_resp = (
                    self._client.table("document_chunks")
                    .delete()
                    .eq("doc_id", doc_id)
                    .execute()
                )
                chunks_deleted_retired += len(
                    list(getattr(del_resp, "data", None) or [])
                )
                # Mark doc retired + tag with delta_id.
                self._client.table("documents").update(
                    {
                        "retired_at": _now_iso(),
                        "last_delta_id": delta_id,
                    }
                ).eq("doc_id", doc_id).execute()

            # Delete outbound edges sourced at retired article keys on the
            # rolling generation. Rows with other generation_ids (snapshot
            # history) stay untouched.
            for article_key in retired_article_keys:
                del_resp = (
                    self._client.table("normative_edges")
                    .delete()
                    .eq("source_key", article_key)
                    .eq("generation_id", self.generation_id)
                    .execute()
                )
                edges_deleted += len(list(getattr(del_resp, "data", None) or []))

        # Similarly: for modified docs, wipe prior outbound edges on the
        # rolling row before writing the fresh set. Determine their article
        # keys from the freshly-parsed articles.
        modified_article_keys: set[str] = set()
        for article in articles:
            dest_doc = doc_id_by_source_path.get(str(article.source_path or ""))
            if dest_doc and dest_doc in modified_doc_ids:
                modified_article_keys.add(article.article_key)
        for article_key in modified_article_keys:
            del_resp = (
                self._client.table("normative_edges")
                .delete()
                .eq("source_key", article_key)
                .eq("generation_id", self.generation_id)
                .execute()
            )
            edges_deleted += len(list(getattr(del_resp, "data", None) or []))

        # -------- Pass 3: edges (Pass A + B promotion + C) -------------------
        # Pass A: write the delta's new edges (idempotent on rolling key).
        edges_written = 0
        if edges:
            edges_written += self._write_rolling_edges(edges, delta_id=delta_id)

        # Pass B: promote dangling candidates whose target arrived in this delta.
        new_article_keys = {a.article_key for a in articles}
        dangling_promoted = 0
        if new_article_keys and dangling_store is not None:
            grouped = dangling_store.load_for_target_keys(new_article_keys)
            promoted = []
            for key, rows in grouped.items():
                for dang in rows:
                    promoted.append(dang)
            if promoted:
                dangling_promoted = self._promote_dangling(
                    promoted, delta_id=delta_id
                )
                # Remove promoted rows from the store.
                from .dangling_store import DanglingCandidate

                dangling_store.delete_promoted(
                    [
                        DanglingCandidate(
                            source_key=r.source_key,
                            target_key=r.target_key,
                            relation=r.relation,
                        )
                        for r in promoted
                    ]
                )

        # Pass C: record new dangling candidates — edges whose target_key is
        # unknown after the delta's article set has been considered.
        dangling_upserted = 0
        if edges and dangling_store is not None:
            candidates = self._classify_dangling_candidates(
                edges,
                known_article_keys=new_article_keys,
            )
            if candidates:
                dangling_upserted = dangling_store.upsert_candidates(
                    candidates, delta_id=delta_id
                )

        # -------- Done -------------------------------------------------------
        result = SupabaseDeltaResult(
            generation_id=self.generation_id,
            target=self.target,
            delta_id=delta_id,
            documents_added=len(added_entries),
            documents_modified=len(modified_entries),
            documents_retired=len(retired_doc_ids),
            chunks_written=chunks_written,
            chunks_deleted=chunks_deleted + chunks_deleted_retired,
            edges_written=edges_written + dangling_promoted,
            edges_deleted=edges_deleted,
            dangling_upserted=dangling_upserted,
            dangling_promoted=dangling_promoted,
        )
        _emit("ingest.delta.sink.done", result.to_dict())
        return result

    def _write_rolling_edges(
        self,
        edges: Sequence[ClassifiedEdge],
        *,
        delta_id: str,
    ) -> int:
        """Upsert edges onto ``generation_id=self.generation_id`` with ``last_seen_delta_id``."""
        rows: list[dict[str, Any]] = []
        now = _now_iso()
        seen: set[tuple[str, str, str]] = set()
        for edge in edges:
            kind_value = edge.record.kind.value
            if kind_value in _RELATION_DROP:
                self._edges_skipped_relation += 1
                continue
            relation = _RELATION_MAP.get(kind_value)
            if relation is None or relation not in _ALLOWED_RELATIONS:
                continue
            source_key = str(edge.record.source_key or "").strip()
            target_key = str(edge.record.target_key or "").strip()
            if not source_key or not target_key:
                continue
            dedup = (source_key, target_key, relation)
            if dedup in seen:
                continue
            seen.add(dedup)
            basis_text = str(edge.record.properties.get("raw_reference") or "") or None
            rows.append(
                {
                    "source_key": source_key,
                    "target_key": target_key,
                    "relation": relation,
                    "confidence": float(edge.confidence or 0.0),
                    "generation_id": self.generation_id,
                    "last_seen_delta_id": delta_id,
                    "created_at": now,
                    "basis_text": basis_text,
                }
            )
        written = 0
        for batch in _iter_batches(rows):
            # When the generation is gen_active_rolling, the partial unique
            # index `normative_edges_rolling_idempotency` enforces the
            # 3-column uniqueness; the 4-column (with generation_id) unique
            # index still dedups for snapshot generations. Upsert on the
            # 4-column key remains correct for both paths.
            self._client.table("normative_edges").upsert(
                batch, on_conflict="source_key,target_key,relation,generation_id"
            ).execute()
            written += len(batch)
        self._edges_written += written
        return written

    def _classify_dangling_candidates(
        self,
        edges: Sequence[ClassifiedEdge],
        *,
        known_article_keys: set[str],
    ) -> list[Any]:
        """Return DanglingCandidate instances for edges with unresolved ARTICLE targets.

        Mirrors the §3.5 constraint: ARTICLE targets only. Other target kinds
        are either always-present (subtopic) or minted inline elsewhere.
        """
        from .dangling_store import DanglingCandidate

        out: list[DanglingCandidate] = []
        for edge in edges:
            kind_value = edge.record.kind.value
            if kind_value in _RELATION_DROP:
                continue
            target_kind = edge.record.target_kind
            # Only ARTICLE-target edges enter the dangling store.
            if target_kind is not NodeKind.ARTICLE:
                continue
            target_key = str(edge.record.target_key or "").strip()
            source_key = str(edge.record.source_key or "").strip()
            if not target_key or not source_key:
                continue
            if target_key in known_article_keys:
                continue
            relation = _RELATION_MAP.get(kind_value)
            if relation is None or relation not in _ALLOWED_RELATIONS:
                continue
            out.append(
                DanglingCandidate(
                    source_key=source_key,
                    target_key=target_key,
                    relation=relation,
                    source_doc_id=str(edge.record.properties.get("source_doc_id") or "") or None,
                    raw_reference=str(edge.record.properties.get("raw_reference") or "") or None,
                )
            )
        return out

    def _promote_dangling(
        self,
        rows: Sequence[Any],
        *,
        delta_id: str,
    ) -> int:
        """Promote DanglingRow instances into ``normative_edges``."""
        now = _now_iso()
        payloads: list[dict[str, Any]] = []
        for r in rows:
            if not r.source_key or not r.target_key or not r.relation:
                continue
            payloads.append(
                {
                    "source_key": r.source_key,
                    "target_key": r.target_key,
                    "relation": r.relation,
                    "confidence": 1.0,
                    "generation_id": self.generation_id,
                    "last_seen_delta_id": delta_id,
                    "created_at": now,
                    "basis_text": r.raw_reference,
                }
            )
        if not payloads:
            return 0
        written = 0
        for batch in _iter_batches(payloads):
            self._client.table("normative_edges").upsert(
                batch, on_conflict="source_key,target_key,relation,generation_id"
            ).execute()
            written += len(batch)
        return written

    # -----------------------------------------------------------------

    def finalize(self, *, activate: bool) -> SupabaseSinkResult:
        if activate:
            self._activate_generation()
            self._activated = True
        try:
            from ..instrumentation import emit_event as _emit

            _emit(
                "subtopic.ingest.sunk",
                {
                    "generation_id": self.generation_id,
                    "target": self.target,
                    "docs_written": self._documents_written,
                    "docs_with_subtopic": self._docs_with_subtopic,
                    "docs_requiring_subtopic_review": self._docs_requiring_subtopic_review,
                },
            )
        except Exception:  # noqa: BLE001 — observability never blocks
            pass
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
    "SupabaseDeltaResult",
    "SupabaseSinkResult",
    "default_generation_id",
]
