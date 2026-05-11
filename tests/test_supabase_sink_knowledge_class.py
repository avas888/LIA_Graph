"""fix_v10_may Phase 10A — supabase_sink chunk-level knowledge_class wire-up.

Verifies that ``write_chunks`` stamps each chunk row with the
``knowledge_class`` of its parent document (captured during
``write_documents``) instead of the historic hardcoded
``"normative_base"`` default. Without this, the Interpretación de
Expertos panel's future Supabase retriever cannot use
``hybrid_search(filter_knowledge_class='interpretative_guidance')``
to isolate the expert corpus.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from lia_graph.ingestion.parser import ParsedArticle
from lia_graph.ingestion.supabase_sink import SupabaseCorpusSink


@dataclass
class _TableCall:
    table: str
    op: str
    payload: Any
    on_conflict: str | None = None


class _FakeExecute:
    def __init__(self) -> None:
        self.data: list[dict[str, Any]] = []


class _FakeQuery:
    def __init__(
        self,
        parent: "_FakeTable",
        op: str,
        payload: Any,
        on_conflict: str | None = None,
    ) -> None:
        self._parent = parent
        self._op = op
        self._payload = payload
        self._on_conflict = on_conflict

    def eq(self, *_args: Any, **_kwargs: Any) -> "_FakeQuery":
        return self

    def neq(self, *_args: Any, **_kwargs: Any) -> "_FakeQuery":
        return self

    def execute(self) -> _FakeExecute:
        self._parent.calls.append(
            _TableCall(
                table=self._parent.name,
                op=self._op,
                payload=self._payload,
                on_conflict=self._on_conflict,
            )
        )
        return _FakeExecute()


class _FakeTable:
    def __init__(self, name: str, calls: list[_TableCall]) -> None:
        self.name = name
        self.calls = calls

    def upsert(
        self, rows: Any, on_conflict: str | None = None
    ) -> _FakeQuery:
        payload = list(rows) if isinstance(rows, list) else [rows]
        return _FakeQuery(self, "upsert", payload, on_conflict=on_conflict)

    def update(self, payload: Any) -> _FakeQuery:
        return _FakeQuery(self, "update", payload)


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[_TableCall] = []

    def table(self, name: str) -> _FakeTable:
        return _FakeTable(name, self.calls)


def _article(source_path: str, key: str = "1") -> ParsedArticle:
    return ParsedArticle(
        article_key=key,
        article_number=key,
        heading=f"Art {key}",
        body="cuerpo",
        full_text=f"# Art {key}\ncuerpo",
        status="vigente",
        source_path=source_path,
        paragraph_markers=(),
        reform_references=(),
        annotations=(),
    )


def _doc(
    rel: str,
    source: str,
    *,
    knowledge_class: str,
    topic_key: str = "renta",
    provider_labels: list[str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "relative_path": rel,
        "source_path": source,
        "title_hint": rel,
        "markdown": "# doc\n",
        "family": "normativa",
        "knowledge_class": knowledge_class,
        "source_type": "article_collection",
        "authority_level": "dian",
        "topic_key": topic_key,
        "subtopic_key": None,
        "requires_subtopic_review": False,
        "document_archetype": "article_collection",
        "pais": "colombia",
    }
    if provider_labels is not None:
        payload["provider_labels"] = provider_labels
    return payload


def _chunk_rows(client: _FakeClient) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for call in client.calls:
        if call.table == "document_chunks" and call.op == "upsert":
            rows.extend(call.payload)
    return rows


def test_chunk_inherits_interpretative_guidance_from_parent_doc() -> None:
    """The keystone: a chunk of an interpretative_guidance doc carries
    knowledge_class='interpretative_guidance' on the row, NOT
    'normative_base'.
    """
    client = _FakeClient()
    sink = SupabaseCorpusSink(
        target="wip", generation_id="gen_kc_1", client=client
    )
    sink.write_generation(documents=1, chunks=1)
    doc_ids, _ = sink.write_documents([
        _doc(
            "EXPERTOS/crowe/art_124_2.md",
            "/abs/EXPERTOS/crowe/art_124_2.md",
            knowledge_class="interpretative_guidance",
            topic_key="renta",
        ),
    ])
    sink.write_chunks(
        [_article("/abs/EXPERTOS/crowe/art_124_2.md", key="1")],
        doc_id_by_source_path=doc_ids,
    )
    [chunk] = _chunk_rows(client)
    assert chunk["knowledge_class"] == "interpretative_guidance"


def test_chunk_inherits_practica_erp_from_parent_doc() -> None:
    client = _FakeClient()
    sink = SupabaseCorpusSink(
        target="wip", generation_id="gen_kc_2", client=client
    )
    sink.write_generation(documents=1, chunks=1)
    doc_ids, _ = sink.write_documents([
        _doc(
            "PRACTICA/erp/sap_imp_renta.md",
            "/abs/PRACTICA/erp/sap_imp_renta.md",
            knowledge_class="practica_erp",
            topic_key="renta",
        ),
    ])
    sink.write_chunks(
        [_article("/abs/PRACTICA/erp/sap_imp_renta.md", key="1")],
        doc_id_by_source_path=doc_ids,
    )
    [chunk] = _chunk_rows(client)
    assert chunk["knowledge_class"] == "practica_erp"


def test_chunk_inherits_normative_base_from_parent_doc() -> None:
    """Regression guard: normative_base docs keep their current value."""
    client = _FakeClient()
    sink = SupabaseCorpusSink(
        target="wip", generation_id="gen_kc_3", client=client
    )
    sink.write_generation(documents=1, chunks=1)
    doc_ids, _ = sink.write_documents([
        _doc(
            "ET/art_115.md",
            "/abs/ET/art_115.md",
            knowledge_class="normative_base",
            topic_key="renta",
        ),
    ])
    sink.write_chunks(
        [_article("/abs/ET/art_115.md", key="1")],
        doc_id_by_source_path=doc_ids,
    )
    [chunk] = _chunk_rows(client)
    assert chunk["knowledge_class"] == "normative_base"


def test_chunks_across_mixed_corpus_carry_distinct_knowledge_classes() -> None:
    """Two parents → two chunks with different knowledge_class values
    in a single write_chunks call (production-shaped scenario).
    """
    client = _FakeClient()
    sink = SupabaseCorpusSink(
        target="wip", generation_id="gen_kc_4", client=client
    )
    sink.write_generation(documents=2, chunks=2)
    doc_ids, _ = sink.write_documents([
        _doc(
            "ET/art_115.md",
            "/abs/ET/art_115.md",
            knowledge_class="normative_base",
        ),
        _doc(
            "EXPERTOS/ey/ica_deduccion.md",
            "/abs/EXPERTOS/ey/ica_deduccion.md",
            knowledge_class="interpretative_guidance",
        ),
    ])
    sink.write_chunks(
        [
            _article("/abs/ET/art_115.md", key="1"),
            _article("/abs/EXPERTOS/ey/ica_deduccion.md", key="1"),
        ],
        doc_id_by_source_path=doc_ids,
    )
    chunks = _chunk_rows(client)
    by_doc_id = {c["doc_id"]: c for c in chunks}
    assert len(by_doc_id) == 2
    norm = next(
        c for c in chunks if "art_115" in (c.get("chunk_id") or "")
    )
    interp = next(
        c for c in chunks if "ica_deduccion" in (c.get("chunk_id") or "")
    )
    assert norm["knowledge_class"] == "normative_base"
    assert interp["knowledge_class"] == "interpretative_guidance"


def test_chunk_with_unknown_parent_falls_back_to_normative_base() -> None:
    """Defense-in-depth: a chunk whose parent doc never went through
    write_documents still gets the historical default; nothing is
    skipped or NULL.
    """
    client = _FakeClient()
    sink = SupabaseCorpusSink(
        target="wip", generation_id="gen_kc_5", client=client
    )
    sink.write_generation(documents=1, chunks=1)
    doc_ids, _ = sink.write_documents([
        _doc(
            "ET/art_115.md",
            "/abs/ET/art_115.md",
            knowledge_class="normative_base",
        ),
    ])
    # Manually inject a doc_id mapping for an article whose parent was
    # never recorded — this never happens in production but the
    # default must remain stable.
    doc_ids["/abs/UNREGISTERED/foo.md"] = "doc_unregistered"
    sink.write_chunks(
        [_article("/abs/UNREGISTERED/foo.md", key="1")],
        doc_id_by_source_path=doc_ids,
    )
    [chunk] = _chunk_rows(client)
    assert chunk["knowledge_class"] == "normative_base"


# ---------------------------------------------------------------------------
# fix_v10_may §4.A.4 G2 — sink-level parity guardrail tests.
# ---------------------------------------------------------------------------


def test_g2_default_fallback_increments_counter_and_records_sample() -> None:
    """G2 — when a chunk's parent doc wasn't registered, the sink's
    `chunks_default_class_count` counter must increment so finalize()
    can surface the regression."""
    client = _FakeClient()
    sink = SupabaseCorpusSink(
        target="wip", generation_id="gen_g2_1", client=client
    )
    sink.write_generation(documents=1, chunks=2)
    doc_ids, _ = sink.write_documents([
        _doc(
            "ET/art_115.md",
            "/abs/ET/art_115.md",
            knowledge_class="normative_base",
        ),
    ])
    # Inject 2 chunks whose parents were never registered.
    doc_ids["/abs/MISSING/a.md"] = "doc_missing_a"
    doc_ids["/abs/MISSING/b.md"] = "doc_missing_b"
    sink.write_chunks(
        [
            _article("/abs/MISSING/a.md", key="1"),
            _article("/abs/MISSING/b.md", key="1"),
        ],
        doc_id_by_source_path=doc_ids,
    )
    assert sink._chunks_default_class_count == 2
    assert set(sink._chunks_default_class_sample_doc_ids) == {
        "doc_missing_a",
        "doc_missing_b",
    }


def test_g2_healthy_ingest_keeps_counter_at_zero() -> None:
    """G2 — when every chunk has a registered parent, counter is 0."""
    client = _FakeClient()
    sink = SupabaseCorpusSink(
        target="wip", generation_id="gen_g2_2", client=client
    )
    sink.write_generation(documents=2, chunks=2)
    doc_ids, _ = sink.write_documents([
        _doc(
            "ET/art_115.md",
            "/abs/ET/art_115.md",
            knowledge_class="normative_base",
        ),
        _doc(
            "EXPERTOS/crowe/x.md",
            "/abs/EXPERTOS/crowe/x.md",
            knowledge_class="interpretative_guidance",
        ),
    ])
    sink.write_chunks(
        [
            _article("/abs/ET/art_115.md", key="1"),
            _article("/abs/EXPERTOS/crowe/x.md", key="1"),
        ],
        doc_id_by_source_path=doc_ids,
    )
    assert sink._chunks_default_class_count == 0


def test_g2_finalize_emits_default_used_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """G2 — finalize() emits ingest.sink.chunk_class_default_used so
    heartbeat tooling can pick up the regression in production. Event
    fires unconditionally (even with count=0) so its absence is itself
    a signal that observability broke."""
    captured: list[tuple[str, dict[str, Any]]] = []
    from lia_graph.ingestion import supabase_sink as sink_mod  # noqa: F401
    from lia_graph import instrumentation

    def _capture(event_type: str, payload: dict[str, Any], **kwargs: Any) -> None:
        captured.append((event_type, payload))

    monkeypatch.setattr(instrumentation, "emit_event", _capture)

    client = _FakeClient()
    sink = SupabaseCorpusSink(
        target="wip", generation_id="gen_g2_3", client=client
    )
    sink.write_generation(documents=1, chunks=1)
    doc_ids, _ = sink.write_documents([
        _doc(
            "ET/art_115.md",
            "/abs/ET/art_115.md",
            knowledge_class="normative_base",
        ),
    ])
    doc_ids["/abs/MISSING/foo.md"] = "doc_missing"
    sink.write_chunks(
        [_article("/abs/MISSING/foo.md", key="1")],
        doc_id_by_source_path=doc_ids,
    )
    result = sink.finalize(activate=False)
    names = [n for n, _ in captured]
    assert "ingest.sink.chunk_class_default_used" in names
    payload = dict(
        captured[names.index("ingest.sink.chunk_class_default_used")][1]
    )
    assert payload["chunks_default_class_count"] == 1
    assert payload["sample_doc_ids"] == ["doc_missing"]
    # Also exposed on the public result for harness-level assertions.
    assert result.chunks_default_class_count == 1
    assert result.to_dict()["chunks_default_class_count"] == 1


# ---------------------------------------------------------------------------
# fix_v10_may §4.A.4 G3-equivalent — strong property test exercising the
# end-to-end parity invariant: for every chunk row produced, its
# knowledge_class equals its parent doc's knowledge_class. This is the
# invariant the original sink bug violated for ~2,877 chunks in cloud
# Supabase before fix_v10_may.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# fix_v10_may §9.3 — documents.provider_labels column wire-up tests.
# Verifies that the sink reads `provider_labels` off the document dict and
# writes it to the documents row (migration 20260513000000). Producer side
# — the manifest builder populating this field — lands inside Phase 10B
# proper; the sink must already be tolerant of missing / malformed values.
# ---------------------------------------------------------------------------


def _documents_rows(client: _FakeClient) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for call in client.calls:
        if call.table == "documents" and call.op == "upsert":
            rows.extend(call.payload)
    return rows


def test_provider_labels_default_empty_when_missing_from_doc() -> None:
    """Normative_base docs (the vast majority) carry no providers; the
    sink writes an empty list rather than NULL so the NOT NULL column
    constraint holds."""
    client = _FakeClient()
    sink = SupabaseCorpusSink(
        target="wip", generation_id="gen_prov_1", client=client
    )
    sink.write_generation(documents=1, chunks=0)
    sink.write_documents([
        _doc(
            "ET/art_115.md",
            "/abs/ET/art_115.md",
            knowledge_class="normative_base",
        ),
    ])
    [row] = _documents_rows(client)
    assert row["provider_labels"] == []


def test_provider_labels_populated_from_manifest() -> None:
    """Interpretation docs carry provider_labels on the manifest entry;
    the sink writes the cleaned list verbatim."""
    client = _FakeClient()
    sink = SupabaseCorpusSink(
        target="wip", generation_id="gen_prov_2", client=client
    )
    sink.write_generation(documents=1, chunks=0)
    sink.write_documents([
        _doc(
            "EXPERTOS/crowe-ey/art_124_2.md",
            "/abs/EXPERTOS/crowe-ey/art_124_2.md",
            knowledge_class="interpretative_guidance",
            provider_labels=["Crowe Colombia", "EY", "KPMG"],
        ),
    ])
    [row] = _documents_rows(client)
    assert row["provider_labels"] == ["Crowe Colombia", "EY", "KPMG"]


def test_provider_labels_strips_whitespace_and_drops_empty() -> None:
    """Defense-in-depth — manifest data can be noisy. The sink filters
    out empty strings and trims whitespace before writing."""
    client = _FakeClient()
    sink = SupabaseCorpusSink(
        target="wip", generation_id="gen_prov_3", client=client
    )
    sink.write_generation(documents=1, chunks=0)
    sink.write_documents([
        _doc(
            "EXPERTOS/messy.md",
            "/abs/EXPERTOS/messy.md",
            knowledge_class="interpretative_guidance",
            provider_labels=["  Crowe  ", "", "EY", "   "],
        ),
    ])
    [row] = _documents_rows(client)
    assert row["provider_labels"] == ["Crowe", "EY"]


def test_provider_labels_tolerates_non_list_input() -> None:
    """Defense-in-depth — if upstream (e.g. a botched JSONL parse)
    delivers a string or dict instead of a list, the sink writes an
    empty array rather than crashing or persisting garbage."""
    client = _FakeClient()
    sink = SupabaseCorpusSink(
        target="wip", generation_id="gen_prov_4", client=client
    )
    sink.write_generation(documents=2, chunks=0)
    sink.write_documents([
        _doc(
            "EXPERTOS/string.md",
            "/abs/EXPERTOS/string.md",
            knowledge_class="interpretative_guidance",
            provider_labels="Crowe Colombia",  # type: ignore[arg-type]
        ),
        _doc(
            "EXPERTOS/dict.md",
            "/abs/EXPERTOS/dict.md",
            knowledge_class="interpretative_guidance",
            provider_labels={"name": "Crowe"},  # type: ignore[arg-type]
        ),
    ])
    rows = _documents_rows(client)
    assert all(r["provider_labels"] == [] for r in rows)


def test_parity_invariant_holds_across_realistic_mixed_corpus() -> None:
    """Construct a realistic mixed corpus (5 docs × 3 classes × varying
    chunk fan-out) and assert each chunk row carries the correct
    inherited class."""
    client = _FakeClient()
    sink = SupabaseCorpusSink(
        target="wip", generation_id="gen_parity_1", client=client
    )
    docs = [
        _doc(
            "ET/art_115.md",
            "/abs/ET/art_115.md",
            knowledge_class="normative_base",
        ),
        _doc(
            "ET/art_124_2.md",
            "/abs/ET/art_124_2.md",
            knowledge_class="normative_base",
        ),
        _doc(
            "EXPERTOS/crowe/art_115.md",
            "/abs/EXPERTOS/crowe/art_115.md",
            knowledge_class="interpretative_guidance",
        ),
        _doc(
            "EXPERTOS/ey/art_124_2.md",
            "/abs/EXPERTOS/ey/art_124_2.md",
            knowledge_class="interpretative_guidance",
        ),
        _doc(
            "PRACTICA/erp/siigo_renta.md",
            "/abs/PRACTICA/erp/siigo_renta.md",
            knowledge_class="practica_erp",
        ),
    ]
    sink.write_generation(documents=len(docs), chunks=11)
    doc_ids, _ = sink.write_documents(docs)
    # Varied fan-out: 3, 2, 4, 1, 1 chunks per parent.
    articles = (
        [_article("/abs/ET/art_115.md", key=str(i)) for i in range(1, 4)]
        + [_article("/abs/ET/art_124_2.md", key=str(i)) for i in range(1, 3)]
        + [
            _article("/abs/EXPERTOS/crowe/art_115.md", key=str(i))
            for i in range(1, 5)
        ]
        + [_article("/abs/EXPERTOS/ey/art_124_2.md", key="1")]
        + [_article("/abs/PRACTICA/erp/siigo_renta.md", key="1")]
    )
    sink.write_chunks(articles, doc_id_by_source_path=doc_ids)
    chunks = _chunk_rows(client)
    assert len(chunks) == 11

    # Build the parent-class lookup from the documents we just wrote.
    parent_class_by_doc_id: dict[str, str] = {}
    for call in client.calls:
        if call.table == "documents" and call.op == "upsert":
            for row in call.payload:
                parent_class_by_doc_id[row["doc_id"]] = row["knowledge_class"]

    # Parity invariant: every chunk's class matches its parent doc's class.
    for chunk in chunks:
        parent_class = parent_class_by_doc_id[chunk["doc_id"]]
        assert chunk["knowledge_class"] == parent_class, (
            f"parity violation — chunk for {chunk['doc_id']!r} has "
            f"knowledge_class={chunk['knowledge_class']!r} but parent doc "
            f"has knowledge_class={parent_class!r}"
        )

    # Healthy ingest: no fallbacks fired.
    assert sink._chunks_default_class_count == 0
