"""fix_v11_may Phase 11B — InterpretationNode + INTERPRETS + COVERS_TOPIC loader.

Exercises article-number extraction, the manifest scan, MERGE statement
shape, idempotency, and the eligible-key filters. Does NOT touch
FalkorDB — assembles a `GraphClient` with no executor so statements
are staged but never executed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from lia_graph.graph.client import GraphClient
from lia_graph.graph.interpretation_loader import (
    build_interpretation_load_plan,
    build_interpretation_load_plan_from_supabase,
    extract_article_numbers,
    interpretation_loader_enabled,
)
from lia_graph.graph.schema import EdgeKind, NodeKind, default_graph_schema


# ---------------------------------------------------------------------------
# extract_article_numbers — superset of synthesis_helpers.extract_article_refs
# ---------------------------------------------------------------------------


def test_extract_catches_plain_article_references() -> None:
    text = "El Art. 115 ET regula la deducción. Ver también artículo 124-2 ET."
    assert extract_article_numbers(text) == ("115", "124-2")


def test_extract_normalizes_decimal_subarticle_to_dash() -> None:
    """`Art. 240.1` and `Art. 240-1` should map to the same canonical
    `240-1` form so `INTERPRETS` edges target a single ArticleNode."""
    text = "El Art. 240.1 ET y el Art. 240-1 ET son la misma norma."
    assert extract_article_numbers(text) == ("240-1",)


def test_extract_catches_paragraph_references() -> None:
    text = "El parágrafo 6 del Art. 240 ET aplica a TTD."
    assert extract_article_numbers(text) == ("240",)


def test_extract_catches_numeral_references() -> None:
    text = "Ver numeral 3 del artículo 689-3 ET."
    assert extract_article_numbers(text) == ("689-3",)


def test_extract_dedupes_in_first_occurrence_order() -> None:
    text = "Art. 115 y Art. 124-2 y otra vez Art. 115 y Art. 240-1."
    assert extract_article_numbers(text) == ("115", "124-2", "240-1")


def test_extract_returns_empty_on_no_matches() -> None:
    assert extract_article_numbers("") == ()
    assert extract_article_numbers("texto genérico sin referencias") == ()


def test_extract_handles_en_dash_subarticle() -> None:
    """Unicode en-dash `–` in `Art. 124–2` must normalize to ASCII `-`."""
    text = "El Art. 124–2 ET regula pagos al exterior."
    assert extract_article_numbers(text) == ("124-2",)


def test_extract_ignores_random_long_numbers() -> None:
    """Five-digit numbers (likely IDs / years out of range) are dropped."""
    text = "Decreto 12345 de 2026 modifica..."
    # `12345` is not a valid article number (>4 digits) — filtered
    assert extract_article_numbers(text) == ()


# ---------------------------------------------------------------------------
# build_interpretation_load_plan — manifest scan + node/edge emission
# ---------------------------------------------------------------------------


def _write_manifest(tmp_path: Path, entries: list[dict]) -> Path:
    manifest_path = tmp_path / "canonical_corpus_manifest.json"
    manifest_path.write_text(
        json.dumps({"documents": entries}, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest_path


def _write_markdown(kb_root: Path, relative: str, content: str) -> Path:
    file_path = kb_root / relative
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return file_path


def test_loader_returns_empty_plan_when_manifest_missing(tmp_path: Path) -> None:
    plan = build_interpretation_load_plan(
        manifest_path=tmp_path / "does-not-exist.json",
        knowledge_base_root=tmp_path,
    )
    assert plan.nodes == ()
    assert plan.interprets_edges == ()
    assert plan.covers_topic_edges == ()
    assert plan.statements == ()
    assert plan.diagnostics["interpretation_docs_seen"] == 0


def test_loader_skips_non_interpretation_docs(tmp_path: Path) -> None:
    manifest_path = _write_manifest(
        tmp_path,
        [
            {
                "relative_path": "normativa/et_art_115.md",
                "knowledge_class": "normative_base",  # NOT interpretative
                "topic_key": "declaracion_renta",
            },
            {
                "relative_path": "interpretacion/crowe_art_115.md",
                "knowledge_class": "interpretative_guidance",
                "topic_key": "declaracion_renta",
            },
        ],
    )
    _write_markdown(tmp_path, "interpretacion/crowe_art_115.md", "Art. 115 ET")
    plan = build_interpretation_load_plan(
        manifest_path=manifest_path,
        knowledge_base_root=tmp_path,
    )
    assert plan.diagnostics["interpretation_docs_seen"] == 1
    # Only the interpretation doc gets a node
    assert len(plan.nodes) == 1
    assert plan.nodes[0].key == "interpretacion_crowe_art_115.md"


def test_loader_emits_node_with_required_fields_only(tmp_path: Path) -> None:
    manifest_path = _write_manifest(
        tmp_path,
        [
            {
                "relative_path": "exp/foo.md",
                "knowledge_class": "interpretative_guidance",
                "topic_key": "iva",
                "title_hint": "IVA en zonas francas",
                "authority_level": "high",
            },
        ],
    )
    _write_markdown(tmp_path, "exp/foo.md", "Art. 420 ET trata IVA.")
    plan = build_interpretation_load_plan(
        manifest_path=manifest_path,
        knowledge_base_root=tmp_path,
    )
    [node] = plan.nodes
    assert node.kind is NodeKind.INTERPRETATION
    assert node.key == "exp_foo.md"
    # Required InterpretationNode fields per schema
    assert node.properties["doc_id"] == "exp_foo.md"
    assert node.properties["source_label"] == "IVA en zonas francas"
    # Optional but populated
    assert node.properties["relative_path"] == "exp/foo.md"
    assert node.properties["topic_key"] == "iva"
    assert node.properties["authority"] == "high"
    assert node.properties["pais"] == "colombia"
    # Default trust_tier so a Cypher consumer never reads None
    assert node.properties["trust_tier"] == "medium"


def test_loader_emits_interprets_edges_per_article_number(tmp_path: Path) -> None:
    manifest_path = _write_manifest(
        tmp_path,
        [
            {
                "relative_path": "exp/multi.md",
                "knowledge_class": "interpretative_guidance",
                "topic_key": "declaracion_renta",
            },
        ],
    )
    _write_markdown(
        tmp_path,
        "exp/multi.md",
        "Análisis de Art. 115 ET y Art. 124-2 ET y Art. 689-3 ET.",
    )
    plan = build_interpretation_load_plan(
        manifest_path=manifest_path,
        knowledge_base_root=tmp_path,
    )
    targets = sorted(edge.target_key for edge in plan.interprets_edges)
    assert targets == ["115", "124-2", "689-3"]
    # All INTERPRETS edges point INTERPRETATION → ARTICLE
    for edge in plan.interprets_edges:
        assert edge.kind is EdgeKind.INTERPRETS
        assert edge.source_kind is NodeKind.INTERPRETATION
        assert edge.target_kind is NodeKind.ARTICLE
        assert edge.source_key == "exp_multi.md"


def test_loader_emits_covers_topic_edge_when_topic_present(tmp_path: Path) -> None:
    manifest_path = _write_manifest(
        tmp_path,
        [
            {
                "relative_path": "exp/with-topic.md",
                "knowledge_class": "interpretative_guidance",
                "topic_key": "iva",
            },
            {
                "relative_path": "exp/no-topic.md",
                "knowledge_class": "interpretative_guidance",
                # no topic_key
            },
        ],
    )
    _write_markdown(tmp_path, "exp/with-topic.md", "no article refs here")
    _write_markdown(tmp_path, "exp/no-topic.md", "no article refs here")
    plan = build_interpretation_load_plan(
        manifest_path=manifest_path,
        knowledge_base_root=tmp_path,
    )
    assert len(plan.covers_topic_edges) == 1
    edge = plan.covers_topic_edges[0]
    assert edge.kind is EdgeKind.COVERS_TOPIC
    assert edge.source_key == "exp_with-topic.md"
    assert edge.target_key == "iva"


def test_loader_eligible_article_filter_drops_unknown_targets(tmp_path: Path) -> None:
    manifest_path = _write_manifest(
        tmp_path,
        [
            {
                "relative_path": "exp/mixed.md",
                "knowledge_class": "interpretative_guidance",
            },
        ],
    )
    _write_markdown(tmp_path, "exp/mixed.md", "Art. 115 ET y Art. 9999 ET.")
    plan = build_interpretation_load_plan(
        manifest_path=manifest_path,
        knowledge_base_root=tmp_path,
        eligible_article_ids={"115"},
    )
    targets = [edge.target_key for edge in plan.interprets_edges]
    assert targets == ["115"]
    assert plan.diagnostics["interprets_edges_dropped_unknown_article"] == 1


def test_loader_eligible_topic_filter_drops_unknown_topic_edges(tmp_path: Path) -> None:
    manifest_path = _write_manifest(
        tmp_path,
        [
            {
                "relative_path": "exp/orphan-topic.md",
                "knowledge_class": "interpretative_guidance",
                "topic_key": "topic_that_doesnt_exist",
            },
        ],
    )
    _write_markdown(tmp_path, "exp/orphan-topic.md", "no article refs")
    plan = build_interpretation_load_plan(
        manifest_path=manifest_path,
        knowledge_base_root=tmp_path,
        eligible_topic_keys={"iva", "declaracion_renta"},
    )
    assert plan.covers_topic_edges == ()
    # Node still landed
    assert len(plan.nodes) == 1


def test_loader_handles_missing_markdown_file_gracefully(tmp_path: Path) -> None:
    """The manifest may list a doc whose markdown isn't on disk in
    this run (e.g. partial Dropbox sync). Loader emits the node + any
    topic edge but no INTERPRETS edges, and surfaces the gap as a
    diagnostic count."""
    manifest_path = _write_manifest(
        tmp_path,
        [
            {
                "relative_path": "exp/missing.md",
                "knowledge_class": "interpretative_guidance",
                "topic_key": "iva",
            },
        ],
    )
    # NOTE: markdown file deliberately NOT written
    plan = build_interpretation_load_plan(
        manifest_path=manifest_path,
        knowledge_base_root=tmp_path,
    )
    assert len(plan.nodes) == 1
    assert plan.interprets_edges == ()
    assert plan.diagnostics["interpretation_docs_with_unreadable_markdown"] == 1


def test_loader_statements_are_batched_unwind(tmp_path: Path) -> None:
    """The loader emits batched UNWIND statements (same shape as
    ingestion/loader._build_batched_statements), not one statement
    per node. Confirms the descriptions carry the BatchUpsert /
    BatchEdge prefix."""
    manifest_path = _write_manifest(
        tmp_path,
        [
            {
                "relative_path": f"exp/doc{i}.md",
                "knowledge_class": "interpretative_guidance",
                "topic_key": "iva",
            }
            for i in range(3)
        ],
    )
    for i in range(3):
        _write_markdown(tmp_path, f"exp/doc{i}.md", f"Art. {100 + i} ET")
    plan = build_interpretation_load_plan(
        manifest_path=manifest_path,
        knowledge_base_root=tmp_path,
    )
    descriptions = [s.description for s in plan.statements]
    # One BatchUpsert for nodes, one BatchEdge for INTERPRETS, one for
    # COVERS_TOPIC. Three statements total at batch sizes well above 3.
    assert sum("BatchUpsert InterpretationNode" in d for d in descriptions) == 1
    assert sum("BatchEdge INTERPRETS" in d for d in descriptions) == 1
    assert sum("BatchEdge COVERS_TOPIC" in d for d in descriptions) == 1


def test_loader_is_idempotent_on_doc_id(tmp_path: Path) -> None:
    """Running the loader twice over the same manifest produces the
    same node + edge counts. MERGE on doc_id means the second run
    is a no-op for already-loaded docs."""
    manifest_path = _write_manifest(
        tmp_path,
        [
            {
                "relative_path": "exp/idempotent.md",
                "knowledge_class": "interpretative_guidance",
                "topic_key": "iva",
            },
        ],
    )
    _write_markdown(tmp_path, "exp/idempotent.md", "Art. 420 ET")
    plan1 = build_interpretation_load_plan(
        manifest_path=manifest_path,
        knowledge_base_root=tmp_path,
    )
    plan2 = build_interpretation_load_plan(
        manifest_path=manifest_path,
        knowledge_base_root=tmp_path,
    )
    assert len(plan1.nodes) == len(plan2.nodes) == 1
    assert len(plan1.interprets_edges) == len(plan2.interprets_edges) == 1
    assert len(plan1.covers_topic_edges) == len(plan2.covers_topic_edges) == 1
    # Same MERGE keys → same Cypher semantics second time around
    assert plan1.nodes[0].key == plan2.nodes[0].key


def test_loader_emitted_nodes_validate_against_schema(tmp_path: Path) -> None:
    """Every emitted node must pass `GraphSchema.validate_node_record` —
    catches missing required_fields drift if the schema changes."""
    manifest_path = _write_manifest(
        tmp_path,
        [
            {
                "relative_path": "exp/validates.md",
                "knowledge_class": "interpretative_guidance",
                "topic_key": "iva",
                "title_hint": "Some heading",
            },
        ],
    )
    _write_markdown(tmp_path, "exp/validates.md", "Art. 420 ET")
    plan = build_interpretation_load_plan(
        manifest_path=manifest_path,
        knowledge_base_root=tmp_path,
    )
    schema = default_graph_schema()
    for node in plan.nodes:
        schema.validate_node_record(node)
    for edge in plan.interprets_edges:
        schema.validate_edge_record(edge)
    for edge in plan.covers_topic_edges:
        schema.validate_edge_record(edge)


# ---------------------------------------------------------------------------
# Env flag
# ---------------------------------------------------------------------------


def test_loader_flag_default_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LIA_INGEST_INTERPRETATION_NODES", raising=False)
    assert interpretation_loader_enabled() is True


def test_loader_flag_off_disables(monkeypatch: pytest.MonkeyPatch) -> None:
    for value in ("off", "0", "false", "no"):
        monkeypatch.setenv("LIA_INGEST_INTERPRETATION_NODES", value)
        assert interpretation_loader_enabled() is False
    monkeypatch.setenv("LIA_INGEST_INTERPRETATION_NODES", "enforce")
    assert interpretation_loader_enabled() is True


# ---------------------------------------------------------------------------
# build_interpretation_load_plan_from_supabase — cloud-corpus-aligned path
# ---------------------------------------------------------------------------


@dataclass
class _FakeSupaResp:
    data: list[dict]


class _FakeSupaQuery:
    def __init__(self, client: "_FakeSupaClient", table: str) -> None:
        self._client = client
        self._table = table
        self._filters: list[tuple[str, str, object]] = []

    def select(self, cols: str) -> "_FakeSupaQuery":
        return self

    def eq(self, col: str, val: object) -> "_FakeSupaQuery":
        self._filters.append(("eq", col, val))
        return self

    def in_(self, col: str, values: list) -> "_FakeSupaQuery":
        self._filters.append(("in_", col, list(values)))
        return self

    def execute(self) -> _FakeSupaResp:
        if self._table == "documents":
            data = [
                row for row in self._client.canned_documents
                if all(
                    (op == "eq" and row.get(col) == val)
                    or (op == "in_" and row.get(col) in val)
                    for op, col, val in self._filters
                )
            ]
            return _FakeSupaResp(data=data)
        if self._table == "document_chunks":
            data = [
                row for row in self._client.canned_chunks
                if all(
                    (op == "eq" and row.get(col) == val)
                    or (op == "in_" and row.get(col) in val)
                    for op, col, val in self._filters
                )
            ]
            return _FakeSupaResp(data=data)
        return _FakeSupaResp(data=[])


@dataclass
class _FakeSupaTable:
    client: "_FakeSupaClient"
    name: str

    def select(self, cols: str) -> _FakeSupaQuery:
        return _FakeSupaQuery(self.client, self.name).select(cols)


@dataclass
class _FakeSupaClient:
    canned_documents: list = field(default_factory=list)
    canned_chunks: list = field(default_factory=list)

    def table(self, name: str) -> _FakeSupaTable:
        return _FakeSupaTable(self, name)


def test_supabase_loader_reads_doc_ids_from_documents_table() -> None:
    """The cloud-aligned loader pulls doc_ids from `documents`
    (filtered to interpretative_guidance), not from a local manifest.
    Confirms the InterpretationNode keys match the cloud doc_id values
    byte-for-byte."""
    supa = _FakeSupaClient(
        canned_documents=[
            {
                "doc_id": "cloud_doc_a",
                "relative_path": "interpretacion/a.md",
                "topic": "iva",
                "authority": "Crowe",
                "pais": "colombia",
                "knowledge_class": "interpretative_guidance",
            },
            {
                "doc_id": "cloud_doc_b",
                "relative_path": "interpretacion/b.md",
                "topic": "declaracion_renta",
                "authority": "EY",
                "pais": "colombia",
                "knowledge_class": "interpretative_guidance",
            },
        ],
        canned_chunks=[
            {
                "doc_id": "cloud_doc_a",
                "chunk_text": "Art. 420 ET regula IVA.",
                "knowledge_class": "interpretative_guidance",
            },
            {
                "doc_id": "cloud_doc_b",
                "chunk_text": "Art. 115 ET y Art. 124-2 ET analizan deducción.",
                "knowledge_class": "interpretative_guidance",
            },
        ],
    )
    plan = build_interpretation_load_plan_from_supabase(supabase_client=supa)
    # Node keys = cloud doc_ids, NOT local-disk sanitized paths
    node_keys = sorted(n.key for n in plan.nodes)
    assert node_keys == ["cloud_doc_a", "cloud_doc_b"]
    # INTERPRETS edges target the bare article_number
    a_targets = sorted(
        e.target_key for e in plan.interprets_edges if e.source_key == "cloud_doc_a"
    )
    b_targets = sorted(
        e.target_key for e in plan.interprets_edges if e.source_key == "cloud_doc_b"
    )
    assert a_targets == ["420"]
    assert b_targets == ["115", "124-2"]
    # COVERS_TOPIC from the documents.topic column
    topic_edges = {(e.source_key, e.target_key) for e in plan.covers_topic_edges}
    assert ("cloud_doc_a", "iva") in topic_edges
    assert ("cloud_doc_b", "declaracion_renta") in topic_edges
    # Source diagnostic identifies the cloud-supabase path
    assert plan.diagnostics["source"] == "supabase_documents_plus_chunks"


def test_supabase_loader_returns_empty_when_no_interpretation_docs() -> None:
    supa = _FakeSupaClient(canned_documents=[], canned_chunks=[])
    plan = build_interpretation_load_plan_from_supabase(supabase_client=supa)
    assert plan.nodes == ()
    assert plan.interprets_edges == ()
    assert plan.covers_topic_edges == ()
    assert plan.statements == ()
    assert plan.diagnostics["interpretation_docs_seen"] == 0


def test_supabase_loader_concatenates_chunks_per_doc() -> None:
    """Multi-chunk docs concatenate ALL their chunk_text before article
    extraction, so a doc whose Art. 115 mention lives in chunk #3 still
    gets the INTERPRETS edge."""
    supa = _FakeSupaClient(
        canned_documents=[
            {
                "doc_id": "multi_chunk_doc",
                "relative_path": "x/multi.md",
                "topic": "iva",
                "knowledge_class": "interpretative_guidance",
            },
        ],
        canned_chunks=[
            {"doc_id": "multi_chunk_doc", "chunk_text": "Intro sin refs.", "knowledge_class": "interpretative_guidance"},
            {"doc_id": "multi_chunk_doc", "chunk_text": "Cuerpo sin refs.", "knowledge_class": "interpretative_guidance"},
            {"doc_id": "multi_chunk_doc", "chunk_text": "Conclusión: Art. 115 ET aplica.", "knowledge_class": "interpretative_guidance"},
        ],
    )
    plan = build_interpretation_load_plan_from_supabase(supabase_client=supa)
    assert len(plan.interprets_edges) == 1
    assert plan.interprets_edges[0].target_key == "115"


def test_supabase_loader_respects_eligible_article_ids_filter() -> None:
    """Edges whose target isn't in the eligible set are dropped; the
    diagnostic counts them so cloud-Falkor-vs-cloud-Supabase drift is
    visible."""
    supa = _FakeSupaClient(
        canned_documents=[
            {"doc_id": "d1", "relative_path": "x/d1.md", "topic": "iva", "knowledge_class": "interpretative_guidance"},
        ],
        canned_chunks=[
            {"doc_id": "d1", "chunk_text": "Art. 115 ET y Art. 9999 ET.", "knowledge_class": "interpretative_guidance"},
        ],
    )
    plan = build_interpretation_load_plan_from_supabase(
        supabase_client=supa,
        eligible_article_ids={"115"},
    )
    targets = [e.target_key for e in plan.interprets_edges]
    assert targets == ["115"]
    assert plan.diagnostics["interprets_edges_dropped_unknown_article"] == 1


def test_loader_uses_unconfigured_client_safely(tmp_path: Path) -> None:
    """When a GraphClient with no executor + no URL is supplied, the
    plan still builds — statements are staged but never executed.
    Lets the loader run in test contexts that don't have a live
    Falkor."""
    manifest_path = _write_manifest(
        tmp_path,
        [
            {
                "relative_path": "exp/safe.md",
                "knowledge_class": "interpretative_guidance",
            },
        ],
    )
    _write_markdown(tmp_path, "exp/safe.md", "Art. 1 ET")
    unconfigured = GraphClient()  # no config, no executor
    plan = build_interpretation_load_plan(
        manifest_path=manifest_path,
        knowledge_base_root=tmp_path,
        graph_client=unconfigured,
    )
    assert len(plan.statements) > 0
