"""fix_v11_may Phase 11B — InterpretationNode + INTERPRETS + COVERS_TOPIC loader.

Promotes the Python-side `interpretacion/article_index.py` index out of
in-process memory into FalkorDB nodes/edges, so the expert-panel
dispatcher can anchor candidate doc_ids on graph traversal
(`MATCH (a:ArticleNode {article_id:$art})<-[:INTERPRETS]-(i:InterpretationNode)
RETURN i.doc_id ORDER BY i.trust_tier DESC LIMIT 8`) instead of the
word-shape Python helper.

The schema scaffold (`InterpretationNode` + `INTERPRETS` + `COVERS_TOPIC`)
already landed in `graph/schema.py` during Phase 10C. This module is the
loader against that scaffold — emits `GraphNodeRecord` / `GraphEdgeRecord`
via the existing `GraphClient.stage_node_batch` / `.stage_edge_batch`
helpers, executed by ``materialize_graph_artifacts`` after the article
+ reform + concept passes (those must run first so the INTERPRETS
endpoint MATCHes resolve).

Idempotent:
- Nodes MERGE on ``doc_id`` (the cloud Supabase `documents.doc_id`).
- INTERPRETS edges MERGE on ``(InterpretationNode.doc_id,
  ArticleNode.article_id)``.
- COVERS_TOPIC edges MERGE on ``(InterpretationNode.doc_id,
  TopicNode.topic_key)``.

Article-ref extraction is intentionally a superset of
`interpretacion/synthesis_helpers.extract_article_refs`:
- catches ``Art. 115``, ``art. 124-2``, ``artículo 689-3``
- catches ``parágrafo N del Art. M`` shapes
- catches ``numeral N del Art. M`` shapes
- catches decreto-introduced article references (``Decreto 1474, Art. 5``)
- decimal forms ``Art. 240.1`` are normalized to dash form (``240-1``)
  to align with how `ArticleNode.article_id` is keyed
  (`_graph_article_key` returns the bare article_number which uses dash
  for sub-articles).
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping

from .client import GraphClient, GraphQueryResult, GraphWriteStatement
from .schema import (
    EdgeKind,
    GraphEdgeRecord,
    GraphNodeRecord,
    NodeKind,
    default_graph_schema,
)


# ---------------------------------------------------------------------------
# Manifest + markdown reading. Mirrors the layout interpretacion/article_index
# uses so the two stay byte-identical on what they consider an interpretation
# doc.
# ---------------------------------------------------------------------------


_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_MANIFEST_PATH = _WORKSPACE_ROOT / "artifacts" / "canonical_corpus_manifest.json"
_DEFAULT_KNOWLEDGE_BASE_ROOT = _WORKSPACE_ROOT / "knowledge_base"


_DOC_ID_SANITIZER_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def _sanitize_doc_id(relative_path: str) -> str:
    """Byte-identical to `ingestion/supabase_sink._sanitize_doc_id` and
    `interpretacion/article_index._sanitize_doc_id`. Re-implemented here
    to avoid pulling the sink or the interpretacion package into the
    graph-loader import graph."""
    return _DOC_ID_SANITIZER_RE.sub("_", str(relative_path or "").strip()).strip("_")


# ---------------------------------------------------------------------------
# Article-ref extraction. Superset of the request-path regex; the loader
# runs once per ingest so a richer pass here pays off forever.
# ---------------------------------------------------------------------------


_ARTICLE_REF_RE = re.compile(
    r"(?ix)"
    r"\b(?:art(?:[íi]culo)?)\.?\s*"
    r"(?P<num>\d{1,4}(?:\s*[.\-–]\s*\d{1,4})?)\b"
)
_PARAGRAPH_REF_RE = re.compile(
    r"(?ix)"
    r"\b(?:par[áa]grafo|numeral)\s+\d+\s+(?:del?\s+)?"
    r"(?:art(?:[íi]culo)?)\.?\s*(?P<num>\d{1,4}(?:\s*[.\-–]\s*\d{1,4})?)\b"
)


def _normalize_article_number(raw: str) -> str:
    """Canonicalize a raw article number capture to the form
    `ArticleNode.article_id` uses for numbered articles.

    Behavior:
    * Strips whitespace inside the dash/dot separator (`240 - 1` → `240-1`).
    * Normalizes Unicode en-dash (`–`) → ASCII dash (`-`).
    * Normalizes decimal sub-article form (`240.1` → `240-1`) so loader
      output matches `ArticleNode.article_id` regardless of which form
      appeared in the markdown.
    * Returns `""` if the capture is empty / malformed.
    """
    s = str(raw or "").strip()
    if not s:
        return ""
    s = s.replace("–", "-").replace(" ", "")
    s = s.replace(".", "-")
    if not re.fullmatch(r"\d{1,4}(?:-\d{1,4})?", s):
        return ""
    return s


def extract_article_numbers(text: str) -> tuple[str, ...]:
    """Extract every article number cited in `text`, deduped, in
    first-occurrence order. Returned values match
    `ArticleNode.article_id` for numbered articles (bare number, dash
    for sub-articles).

    Catches the request-path shape (`Art. 115`, `art. 124-2`) plus
    `parágrafo N del Art. M` / `numeral N del Art. M` (returns `M`,
    since the paragraph/numeral doesn't currently get its own ArticleNode
    — promoting paragraphs to first-class nodes is a separate scope).
    """
    if not text:
        return ()
    seen: set[str] = set()
    out: list[str] = []
    for match in _ARTICLE_REF_RE.finditer(text):
        number = _normalize_article_number(match.group("num"))
        if not number or number in seen:
            continue
        seen.add(number)
        out.append(number)
    for match in _PARAGRAPH_REF_RE.finditer(text):
        number = _normalize_article_number(match.group("num"))
        if not number or number in seen:
            continue
        seen.add(number)
        out.append(number)
    return tuple(out)


# ---------------------------------------------------------------------------
# Manifest scan + loader assembly.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InterpretationLoadPlan:
    """Outcome of `build_interpretation_load_plan`. Mirrors the shape of
    `ingestion.loader.GraphLoadPlan` so the ingest orchestrator can
    treat it the same way (statements + count diagnostics)."""

    nodes: tuple[GraphNodeRecord, ...]
    interprets_edges: tuple[GraphEdgeRecord, ...]
    covers_topic_edges: tuple[GraphEdgeRecord, ...]
    statements: tuple[GraphWriteStatement, ...]
    diagnostics: Mapping[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "interpretation_nodes": len(self.nodes),
            "interprets_edges": len(self.interprets_edges),
            "covers_topic_edges": len(self.covers_topic_edges),
            "statement_count": len(self.statements),
            "diagnostics": dict(self.diagnostics),
        }


def _iter_interpretation_entries(
    manifest_path: Path,
) -> list[dict[str, object]]:
    """Read the canonical_corpus_manifest and yield raw entries whose
    `knowledge_class == 'interpretative_guidance'`. Returns `[]` if the
    manifest doesn't exist yet (e.g. first-run ingest before the audit
    has written it)."""
    if not manifest_path.exists():
        return []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    out: list[dict[str, object]] = []
    for entry in manifest.get("documents", ()) or ():
        if str(entry.get("knowledge_class") or "").strip().lower() != "interpretative_guidance":
            continue
        relative_path = str(entry.get("relative_path") or entry.get("source_path") or "").strip()
        if not relative_path:
            continue
        out.append({"relative_path": relative_path, "manifest_entry": entry})
    return out


def _read_full_markdown(
    knowledge_base_root: Path, relative_path: str
) -> str:
    absolute = (knowledge_base_root / relative_path).resolve()
    if not absolute.exists():
        return ""
    try:
        return absolute.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _build_covers_topic_edge(
    *,
    doc_id: str,
    topic_key: str,
    eligible_topic_keys: frozenset[str] | None,
) -> GraphEdgeRecord | None:
    if not topic_key:
        return None
    if eligible_topic_keys is not None and topic_key not in eligible_topic_keys:
        return None
    return GraphEdgeRecord(
        kind=EdgeKind.COVERS_TOPIC,
        source_kind=NodeKind.INTERPRETATION,
        source_key=doc_id,
        target_kind=NodeKind.TOPIC,
        target_key=topic_key,
        properties={},
    )


@dataclass(frozen=True)
class _InterpretationDocInput:
    """Internal — the per-doc tuple `_assemble_plan` consumes. Produced
    either by `_iter_interpretation_entries` (manifest+disk) or by
    `_iter_supabase_interpretation_docs` (cloud Supabase).

    `text_for_extraction` is whatever string the article-ref regex
    should run over: the FULL markdown when reading from disk, the
    concatenated chunk_text when reading from cloud Supabase.
    """

    doc_id: str
    relative_path: str
    topic_key: str
    authority: str
    pais: str
    source_label: str
    text_for_extraction: str
    text_available: bool


def _manifest_entry_to_doc_input(entry: Mapping[str, object], full_markdown: str) -> _InterpretationDocInput:
    relative_path = str(entry.get("relative_path") or entry.get("source_path") or "").strip()
    doc_id = _sanitize_doc_id(relative_path)
    source_label = str(entry.get("title_hint") or "").strip() or Path(relative_path).stem
    return _InterpretationDocInput(
        doc_id=doc_id,
        relative_path=relative_path,
        topic_key=str(entry.get("topic_key") or "").strip().lower(),
        authority=str(entry.get("authority_level") or "").strip(),
        pais=str(entry.get("pais") or "colombia").strip().lower() or "colombia",
        source_label=source_label,
        text_for_extraction=full_markdown,
        text_available=bool(full_markdown),
    )


def _iter_supabase_interpretation_docs(client: object) -> list[_InterpretationDocInput]:
    """Read every cloud `documents` row with
    `knowledge_class='interpretative_guidance'`, then for each one read
    every `document_chunks` row's `chunk_text` and concatenate. The
    concatenated text becomes the input to `extract_article_numbers`.

    The cloud `documents.doc_id` is the source of truth — this is the
    same doc_id the panel retriever returns from `hybrid_search`, so
    the InterpretationNode's `doc_id` property MATCHes the chunk_row's
    `doc_id` byte-for-byte at request time.
    """
    docs_resp = (
        client.table("documents")  # type: ignore[attr-defined]
        .select("doc_id,relative_path,topic,authority,pais")
        .eq("knowledge_class", "interpretative_guidance")
        .execute()
    )
    docs_rows = list(getattr(docs_resp, "data", None) or [])
    docs_by_id: dict[str, dict[str, object]] = {
        str(row.get("doc_id") or "").strip(): dict(row)
        for row in docs_rows
        if str(row.get("doc_id") or "").strip()
    }
    if not docs_by_id:
        return []

    # Read chunk_text for every doc; batch by 100 ids per IN to keep the
    # request size sane. concept_tags / other fields are NOT needed for
    # the loader (extract_article_numbers operates on the raw text).
    chunks_by_doc: dict[str, list[str]] = {doc_id: [] for doc_id in docs_by_id}
    doc_ids = list(docs_by_id.keys())
    batch = 100
    for start in range(0, len(doc_ids), batch):
        chunk_ids = doc_ids[start : start + batch]
        resp = (
            client.table("document_chunks")  # type: ignore[attr-defined]
            .select("doc_id,chunk_text")
            .in_("doc_id", chunk_ids)
            .eq("knowledge_class", "interpretative_guidance")
            .execute()
        )
        for row in getattr(resp, "data", None) or []:
            doc_id = str(row.get("doc_id") or "").strip()
            text = str(row.get("chunk_text") or "")
            if doc_id in chunks_by_doc and text:
                chunks_by_doc[doc_id].append(text)

    out: list[_InterpretationDocInput] = []
    for doc_id, doc_row in docs_by_id.items():
        chunk_texts = chunks_by_doc.get(doc_id, [])
        concatenated = "\n\n".join(chunk_texts)
        relative_path = str(doc_row.get("relative_path") or "").strip() or doc_id
        out.append(
            _InterpretationDocInput(
                doc_id=doc_id,
                relative_path=relative_path,
                topic_key=str(doc_row.get("topic") or "").strip().lower(),
                authority=str(doc_row.get("authority") or "").strip(),
                pais=str(doc_row.get("pais") or "colombia").strip().lower() or "colombia",
                source_label=Path(relative_path).stem or doc_id,
                text_for_extraction=concatenated,
                text_available=bool(concatenated),
            )
        )
    return out


def _assemble_plan(
    *,
    doc_inputs: list[_InterpretationDocInput],
    graph_client: GraphClient | None,
    eligible_article_set: frozenset[str] | None,
    eligible_topic_set: frozenset[str] | None,
    source_description: Mapping[str, object],
) -> InterpretationLoadPlan:
    """Shared core. Builds nodes + edges + batched statements from the
    pre-resolved per-doc tuple list."""
    client = graph_client or GraphClient(schema=default_graph_schema())
    nodes: list[GraphNodeRecord] = []
    interprets: list[GraphEdgeRecord] = []
    covers_topic: list[GraphEdgeRecord] = []
    docs_seen = 0
    docs_with_zero_articles = 0
    docs_with_unreadable_text = 0
    interprets_dropped_unknown_article = 0

    for doc in doc_inputs:
        docs_seen += 1
        if not doc.doc_id:
            continue
        if not doc.text_available:
            docs_with_unreadable_text += 1
        properties: dict[str, object] = {
            "doc_id": doc.doc_id,
            "source_label": doc.source_label or doc.doc_id,
            "relative_path": doc.relative_path,
            "pais": doc.pais,
            "trust_tier": "medium",
        }
        if doc.topic_key:
            properties["topic_key"] = doc.topic_key
        if doc.authority:
            properties["authority"] = doc.authority
        nodes.append(
            GraphNodeRecord(
                kind=NodeKind.INTERPRETATION,
                key=doc.doc_id,
                properties=properties,
            )
        )
        article_numbers = extract_article_numbers(doc.text_for_extraction)
        if not article_numbers:
            docs_with_zero_articles += 1
        for number in article_numbers:
            if eligible_article_set is not None and number not in eligible_article_set:
                interprets_dropped_unknown_article += 1
                continue
            interprets.append(
                GraphEdgeRecord(
                    kind=EdgeKind.INTERPRETS,
                    source_kind=NodeKind.INTERPRETATION,
                    source_key=doc.doc_id,
                    target_kind=NodeKind.ARTICLE,
                    target_key=number,
                    properties={},
                )
            )
        edge = _build_covers_topic_edge(
            doc_id=doc.doc_id,
            topic_key=doc.topic_key,
            eligible_topic_keys=eligible_topic_set,
        )
        if edge is not None:
            covers_topic.append(edge)

    statements = _build_statements(
        client=client,
        nodes=nodes,
        interprets_edges=interprets,
        covers_topic_edges=covers_topic,
    )
    diagnostics: dict[str, object] = {
        "interpretation_docs_seen": docs_seen,
        "interpretation_docs_with_unreadable_markdown": docs_with_unreadable_text,
        "interpretation_docs_with_zero_articles": docs_with_zero_articles,
        "interprets_edges_dropped_unknown_article": interprets_dropped_unknown_article,
    }
    diagnostics.update(dict(source_description))
    return InterpretationLoadPlan(
        nodes=tuple(nodes),
        interprets_edges=tuple(interprets),
        covers_topic_edges=tuple(covers_topic),
        statements=statements,
        diagnostics=diagnostics,
    )


def build_interpretation_load_plan(
    *,
    manifest_path: Path | str | None = None,
    knowledge_base_root: Path | str | None = None,
    graph_client: GraphClient | None = None,
    eligible_article_ids: Iterable[str] | None = None,
    eligible_topic_keys: Iterable[str] | None = None,
) -> InterpretationLoadPlan:
    """Build the InterpretationNode + INTERPRETS + COVERS_TOPIC load plan
    from the local manifest + knowledge_base.

    Use this from `materialize_graph_artifacts` (local-ingest path) and
    from operator scripts that target local Falkor for preflight. For
    cloud Falkor runs, prefer
    `build_interpretation_load_plan_from_supabase` so the InterpretationNode
    `doc_id` set is byte-identical to what the panel retriever returns
    from cloud `hybrid_search`.

    `eligible_article_ids` / `eligible_topic_keys` are populated by the
    caller (ingest.py) from the already-built article + topic load plan,
    so the loader only emits edges whose endpoints will actually exist.
    Passing `None` for either disables filtering (use with care — the
    MATCH-semantics no-op is silent in Cypher).
    """
    manifest = Path(manifest_path) if manifest_path is not None else _DEFAULT_MANIFEST_PATH
    kb_root = Path(knowledge_base_root) if knowledge_base_root is not None else _DEFAULT_KNOWLEDGE_BASE_ROOT
    eligible_article_set = (
        frozenset(str(a).strip() for a in eligible_article_ids if str(a).strip())
        if eligible_article_ids is not None
        else None
    )
    eligible_topic_set = (
        frozenset(str(t).strip().lower() for t in eligible_topic_keys if str(t).strip())
        if eligible_topic_keys is not None
        else None
    )
    doc_inputs: list[_InterpretationDocInput] = []
    for entry in _iter_interpretation_entries(manifest):
        relative_path = str(entry["relative_path"])
        manifest_entry = entry["manifest_entry"]
        if not isinstance(manifest_entry, Mapping):
            manifest_entry = {}
        full_markdown = _read_full_markdown(kb_root, relative_path)
        doc_inputs.append(_manifest_entry_to_doc_input(manifest_entry, full_markdown))
    return _assemble_plan(
        doc_inputs=doc_inputs,
        graph_client=graph_client,
        eligible_article_set=eligible_article_set,
        eligible_topic_set=eligible_topic_set,
        source_description={
            "source": "manifest_plus_local_markdown",
            "manifest_path": str(manifest),
            "knowledge_base_root": str(kb_root),
        },
    )


def build_interpretation_load_plan_from_supabase(
    *,
    supabase_client: object,
    graph_client: GraphClient | None = None,
    eligible_article_ids: Iterable[str] | None = None,
    eligible_topic_keys: Iterable[str] | None = None,
) -> InterpretationLoadPlan:
    """Cloud-corpus-aligned variant. Reads the interpretation doc list
    from `documents` (filter `knowledge_class='interpretative_guidance'`)
    and the article-ref source text from `document_chunks` — both
    against the supplied Supabase client.

    Use this for the operator-targeted cloud Falkor loader run. The
    `documents.doc_id` value is the source of truth: it's the same
    doc_id the panel retriever returns from `hybrid_search` at request
    time, so the InterpretationNode key MATCHes the chunk_row's doc_id
    byte-for-byte and the anchor resolver's Cypher returns a value that
    the retriever can actually pin its ×4 boost on.

    If `documents` is empty (no interpretation_guidance rows in this
    Supabase instance), the returned plan has zero nodes / zero edges /
    zero statements — caller can short-circuit on `plan.nodes == ()`.
    """
    eligible_article_set = (
        frozenset(str(a).strip() for a in eligible_article_ids if str(a).strip())
        if eligible_article_ids is not None
        else None
    )
    eligible_topic_set = (
        frozenset(str(t).strip().lower() for t in eligible_topic_keys if str(t).strip())
        if eligible_topic_keys is not None
        else None
    )
    doc_inputs = _iter_supabase_interpretation_docs(supabase_client)
    return _assemble_plan(
        doc_inputs=doc_inputs,
        graph_client=graph_client,
        eligible_article_set=eligible_article_set,
        eligible_topic_set=eligible_topic_set,
        source_description={
            "source": "supabase_documents_plus_chunks",
        },
    )


def _build_statements(
    *,
    client: GraphClient,
    nodes: list[GraphNodeRecord],
    interprets_edges: list[GraphEdgeRecord],
    covers_topic_edges: list[GraphEdgeRecord],
) -> tuple[GraphWriteStatement, ...]:
    """Batched UNWIND statements for the InterpretationNode load — same
    shape as `ingestion/loader._build_batched_statements`. Splits each
    list into chunks of `client.config.batch_size_nodes` /
    `batch_size_edges` so a single UNWIND payload doesn't exceed the
    Falkor batch ceiling.
    """
    statements: list[GraphWriteStatement] = []
    batch_nodes = max(1, int(client.config.batch_size_nodes))
    batch_edges = max(1, int(client.config.batch_size_edges))

    for chunk in _chunked(nodes, batch_nodes):
        rows = [
            {"key": record.key, "properties": dict(record.properties)}
            for record in chunk
        ]
        statements.append(
            client.stage_node_batch(NodeKind.INTERPRETATION, rows)
        )

    for chunk in _chunked(interprets_edges, batch_edges):
        rows = [
            {
                "source_key": edge.source_key,
                "target_key": edge.target_key,
                "properties": dict(edge.properties),
            }
            for edge in chunk
        ]
        statements.append(
            client.stage_edge_batch(
                edge_kind=EdgeKind.INTERPRETS,
                source_kind=NodeKind.INTERPRETATION,
                target_kind=NodeKind.ARTICLE,
                rows=rows,
            )
        )

    for chunk in _chunked(covers_topic_edges, batch_edges):
        rows = [
            {
                "source_key": edge.source_key,
                "target_key": edge.target_key,
                "properties": dict(edge.properties),
            }
            for edge in chunk
        ]
        statements.append(
            client.stage_edge_batch(
                edge_kind=EdgeKind.COVERS_TOPIC,
                source_kind=NodeKind.INTERPRETATION,
                target_kind=NodeKind.TOPIC,
                rows=rows,
            )
        )

    return tuple(statements)


def _chunked(items: list, size: int) -> Iterable[list]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


# ---------------------------------------------------------------------------
# Execution wrapper. Callers (ingest.py + the operator-targeted CLI) hand
# in a configured GraphClient and we just execute_many. Errors propagate
# per CLAUDE.md's "no silent fallback" rule when `strict=True`.
# ---------------------------------------------------------------------------


def execute_interpretation_load_plan(
    plan: InterpretationLoadPlan,
    *,
    graph_client: GraphClient,
    strict: bool = False,
) -> tuple[GraphQueryResult, ...]:
    if not plan.statements:
        return ()
    return graph_client.execute_many(plan.statements, strict=strict)


# ---------------------------------------------------------------------------
# Public env knob — kept here (vs. a global config module) so the loader
# is self-contained for tests.
# ---------------------------------------------------------------------------


def interpretation_loader_enabled(environ: Mapping[str, str] | None = None) -> bool:
    """Honor `LIA_INGEST_INTERPRETATION_NODES`. Default `enforce` (on).
    Set to `off` (or `0`, `false`, `no`) to skip the loader during
    `materialize_graph_artifacts`."""
    env = os.environ if environ is None else environ
    raw = str(env.get("LIA_INGEST_INTERPRETATION_NODES", "enforce") or "enforce").strip().lower()
    return raw not in {"off", "0", "false", "no"}


__all__ = [
    "InterpretationLoadPlan",
    "build_interpretation_load_plan",
    "build_interpretation_load_plan_from_supabase",
    "execute_interpretation_load_plan",
    "extract_article_numbers",
    "interpretation_loader_enabled",
]
