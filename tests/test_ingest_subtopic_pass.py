"""Tests for the PASO 4 classifier pass over corpus documents (Phase A4).

Also covers Phase A5: ``build_article_subtopic_bindings`` (mapping
``article_key → SubtopicBinding`` for the loader).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from lia_graph.ingest_constants import CorpusDocument
from lia_graph.ingest_subtopic_pass import (
    build_article_subtopic_bindings,
    classify_corpus_documents,
)
from lia_graph.ingestion.loader import SubtopicBinding


def _make_doc(
    *,
    source_path: str,
    topic_key: str | None = "laboral",
    subtopic_key: str | None = None,
    markdown: str = "# Doc\nbody text",
) -> CorpusDocument:
    return CorpusDocument(
        source_origin="knowledge_base",
        source_path=source_path,
        relative_path=source_path,
        title_hint=source_path,
        extension=".md",
        text_extractable=True,
        parse_strategy="markdown_graph_parse",
        document_archetype="normative_base",
        taxonomy_version="test",
        family="normativa",
        knowledge_class="normative_base",
        source_type="doctrina",
        source_tier="tier_a",
        authority_level="high",
        graph_target=True,
        graph_parse_ready=True,
        topic_key=topic_key,
        subtopic_key=subtopic_key,
        vocabulary_status="assigned",
        ambiguity_flags=(),
        review_priority="none",
        needs_manual_review=False,
        markdown=markdown,
    )


@dataclass
class _FakeVerdict:
    subtopic_key: str | None = None
    subtopic_confidence: float = 0.0
    requires_subtopic_review: bool = False
    detected_topic: str | None = None


class _FakeTaxonomy:
    def __init__(self, keys: set[tuple[str, str]]):
        self.lookup_by_key = {k: object() for k in keys}


def test_happy_path_overrides_legacy_with_high_conf_paso4() -> None:
    docs = (
        _make_doc(source_path="laboral/a.md", subtopic_key="legacy_a"),
        _make_doc(source_path="laboral/b.md", subtopic_key="legacy_b"),
        # legacy_c is a taxonomy-valid key; preserved when PASO 4 returns nothing
        _make_doc(source_path="laboral/c.md", subtopic_key="legacy_preserved"),
    )
    verdicts_by_filename = {
        "laboral/a.md": _FakeVerdict(
            subtopic_key="aporte_parafiscales_icbf",
            subtopic_confidence=0.95,
            detected_topic="laboral",
        ),
        "laboral/b.md": _FakeVerdict(
            subtopic_key="liquidacion_cesantias",
            subtopic_confidence=0.90,
            detected_topic="laboral",
        ),
        "laboral/c.md": _FakeVerdict(
            subtopic_key=None,
            subtopic_confidence=0.0,
            detected_topic="laboral",
        ),
    }

    def classifier(*, filename: str, body_text: str) -> _FakeVerdict:
        return verdicts_by_filename[filename]

    taxonomy = _FakeTaxonomy(
        {
            ("laboral", "aporte_parafiscales_icbf"),
            ("laboral", "liquidacion_cesantias"),
            ("laboral", "legacy_preserved"),  # curated — legacy survives validation
        }
    )
    out = classify_corpus_documents(
        docs,
        rate_limit_rpm=0,
        classifier=classifier,
        taxonomy_loader=lambda: taxonomy,
    )
    assert out[0].subtopic_key == "aporte_parafiscales_icbf"
    assert out[0].requires_subtopic_review is False
    assert out[1].subtopic_key == "liquidacion_cesantias"
    assert out[2].subtopic_key == "legacy_preserved"  # curated legacy survives
    assert out[2].requires_subtopic_review is False


def test_skip_llm_preserves_legacy_no_classifier_call() -> None:
    docs = (_make_doc(source_path="a.md", subtopic_key="legacy"),)
    calls: list[str] = []

    def classifier(*, filename: str, body_text: str) -> _FakeVerdict:
        calls.append(filename)
        return _FakeVerdict()

    out = classify_corpus_documents(
        docs,
        skip_llm=True,
        classifier=classifier,
        taxonomy_loader=lambda: _FakeTaxonomy(set()),
    )
    assert out == docs
    assert calls == []
    # Frozen dataclass equality: returned unchanged.
    assert out[0].subtopic_key == "legacy"
    assert out[0].requires_subtopic_review is False


def test_classifier_raises_on_one_doc_others_still_classified() -> None:
    docs = (
        _make_doc(source_path="ok.md", subtopic_key="legacy_ok"),
        # legacy_bad is a curated key — it survives validation and is
        # preserved when the classifier raises.
        _make_doc(source_path="bad.md", subtopic_key="legacy_bad"),
        _make_doc(source_path="also_ok.md", subtopic_key=None),
    )
    taxonomy = _FakeTaxonomy(
        {("laboral", "sometopic"), ("laboral", "legacy_bad")}
    )

    def classifier(*, filename: str, body_text: str) -> _FakeVerdict:
        if filename == "bad.md":
            raise RuntimeError("LLM timeout")
        return _FakeVerdict(
            subtopic_key="sometopic",
            subtopic_confidence=0.95,
            detected_topic="laboral",
        )

    out = classify_corpus_documents(
        docs,
        rate_limit_rpm=0,
        classifier=classifier,
        taxonomy_loader=lambda: taxonomy,
    )
    assert out[0].subtopic_key == "sometopic"
    assert out[0].requires_subtopic_review is False
    assert out[1].subtopic_key == "legacy_bad"  # curated legacy preserved
    assert out[1].requires_subtopic_review is True  # flagged
    assert out[2].subtopic_key == "sometopic"


def test_rate_limit_triggers_sleeps(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(
        "lia_graph.ingest_subtopic_pass.time.sleep",
        lambda s: sleeps.append(s),
    )
    docs = tuple(
        _make_doc(source_path=f"d{i}.md", subtopic_key=None) for i in range(4)
    )
    taxonomy = _FakeTaxonomy(set())

    def classifier(*, filename: str, body_text: str) -> _FakeVerdict:
        return _FakeVerdict()

    classify_corpus_documents(
        docs,
        rate_limit_rpm=60,
        classifier=classifier,
        taxonomy_loader=lambda: taxonomy,
    )
    # First doc never sleeps; subsequent docs may sleep (up to N-1 times).
    assert 0 <= len(sleeps) <= len(docs) - 1


def test_taxonomy_loaded_once(monkeypatch: pytest.MonkeyPatch) -> None:
    docs = tuple(
        _make_doc(source_path=f"d{i}.md", subtopic_key=None) for i in range(5)
    )
    loader_calls = {"n": 0}

    def loader() -> Any:
        loader_calls["n"] += 1
        return _FakeTaxonomy(set())

    def classifier(*, filename: str, body_text: str) -> _FakeVerdict:
        return _FakeVerdict()

    classify_corpus_documents(
        docs,
        rate_limit_rpm=0,
        classifier=classifier,
        taxonomy_loader=loader,
    )
    assert loader_calls["n"] == 1


def test_orphan_subtopic_key_dropped_and_flagged() -> None:
    # legacy_curated is in the taxonomy (survives validation); hallucinated
    # classifier verdict is NOT — so we preserve the curated legacy key and
    # flag the doc for review.
    docs = (_make_doc(source_path="a.md", subtopic_key="legacy_curated"),)
    taxonomy = _FakeTaxonomy(
        {("laboral", "exists"), ("laboral", "legacy_curated")}
    )

    def classifier(*, filename: str, body_text: str) -> _FakeVerdict:
        return _FakeVerdict(
            subtopic_key="hallucinated",
            subtopic_confidence=0.99,
            detected_topic="laboral",
        )

    out = classify_corpus_documents(
        docs,
        rate_limit_rpm=0,
        classifier=classifier,
        taxonomy_loader=lambda: taxonomy,
    )
    assert out[0].subtopic_key == "legacy_curated"
    assert out[0].requires_subtopic_review is True


def test_low_confidence_paso4_flags_review_and_keeps_legacy() -> None:
    docs = (_make_doc(source_path="a.md", subtopic_key="legacy_key"),)
    taxonomy = _FakeTaxonomy(
        {("laboral", "real_subtopic"), ("laboral", "legacy_key")}
    )

    def classifier(*, filename: str, body_text: str) -> _FakeVerdict:
        return _FakeVerdict(
            subtopic_key="real_subtopic",
            subtopic_confidence=0.40,
            detected_topic="laboral",
        )

    out = classify_corpus_documents(
        docs,
        rate_limit_rpm=0,
        classifier=classifier,
        taxonomy_loader=lambda: taxonomy,
    )
    assert out[0].subtopic_key == "legacy_key"
    assert out[0].requires_subtopic_review is True


def test_legacy_subtopic_not_in_taxonomy_dropped() -> None:
    """When the legacy regex verdict isn't in the curated taxonomy, drop
    it — preserves the A10 invariant that every written subtema exists in
    ``config/subtopic_taxonomy.json``."""
    docs = (_make_doc(source_path="a.md", subtopic_key="stale_legacy_key"),)
    taxonomy = _FakeTaxonomy({("laboral", "curated_only")})

    def classifier(*, filename: str, body_text: str) -> _FakeVerdict:
        return _FakeVerdict(subtopic_key=None)

    out = classify_corpus_documents(
        docs,
        rate_limit_rpm=0,
        classifier=classifier,
        taxonomy_loader=lambda: taxonomy,
    )
    # Stale legacy key must NOT leak to the sink.
    assert out[0].subtopic_key is None


def test_classifier_override_updates_topic_key_when_detected_topic_differs() -> None:
    """Data-boundary invariant: when PASO 4 overrides subtopic_key with a
    high-confidence verdict, topic_key must be updated to detected_topic
    so ``(topic_key, subtopic_key)`` resolves in the taxonomy.

    Regression for the B3 bug — the initial implementation only updated
    subtopic_key, leaving topic_key at the legacy regex value. The binding
    pass then silently skipped 217 bindings because (legacy_topic, paso4_sub)
    wasn't a valid taxonomy pair.
    """
    docs = (
        # legacy regex tagged this under "contratacion_estatal", but PASO 4
        # correctly identifies the subtopic under "retencion_en_la_fuente".
        _make_doc(
            source_path="a.md",
            topic_key="contratacion_estatal",
            subtopic_key=None,
        ),
    )
    taxonomy = _FakeTaxonomy(
        {("retencion_en_la_fuente", "implementacion_retencion_en_la_fuente_pyme")}
    )

    def classifier(*, filename: str, body_text: str) -> _FakeVerdict:
        return _FakeVerdict(
            subtopic_key="implementacion_retencion_en_la_fuente_pyme",
            subtopic_confidence=0.95,
            detected_topic="retencion_en_la_fuente",
        )

    out = classify_corpus_documents(
        docs,
        rate_limit_rpm=0,
        classifier=classifier,
        taxonomy_loader=lambda: taxonomy,
    )
    # BOTH fields must reflect the classifier verdict so the pair
    # resolves in taxonomy.
    assert out[0].subtopic_key == "implementacion_retencion_en_la_fuente_pyme"
    assert out[0].topic_key == "retencion_en_la_fuente"
    # Data-boundary invariant — the whole point of the fix.
    assert (out[0].topic_key, out[0].subtopic_key) in taxonomy.lookup_by_key


def test_every_classified_doc_satisfies_topic_subtopic_invariant() -> None:
    """Shape invariant: for every doc returned by ``classify_corpus_documents``,
    if ``subtopic_key`` is non-null, then ``(topic_key, subtopic_key)`` MUST
    resolve in the curated taxonomy. Property test — runs against 6 synthetic
    docs with mixed verdicts.
    """
    docs = tuple(
        _make_doc(
            source_path=f"d{i}.md",
            topic_key=(
                "laboral" if i % 3 == 0 else (None if i % 3 == 1 else "wrong_parent")
            ),
            subtopic_key=(
                "legacy_curated" if i < 3 else ("stale_legacy_key" if i < 5 else None)
            ),
        )
        for i in range(6)
    )
    taxonomy = _FakeTaxonomy(
        {
            ("laboral", "legacy_curated"),
            ("laboral", "aporte_parafiscales_icbf"),
        }
    )

    def classifier(*, filename: str, body_text: str) -> _FakeVerdict:
        return _FakeVerdict(
            subtopic_key=(
                "aporte_parafiscales_icbf" if "d0" in filename else None
            ),
            subtopic_confidence=0.95 if "d0" in filename else 0.0,
            detected_topic="laboral",
        )

    out = classify_corpus_documents(
        docs,
        rate_limit_rpm=0,
        classifier=classifier,
        taxonomy_loader=lambda: taxonomy,
    )
    orphans = [
        (doc.topic_key, doc.subtopic_key)
        for doc in out
        if doc.subtopic_key
        and (doc.topic_key, doc.subtopic_key) not in taxonomy.lookup_by_key
    ]
    assert orphans == [], (
        f"classifier left {len(orphans)} docs in a taxonomy-violating state: "
        f"{orphans[:5]}"
    )


# ---------------------------------------------------------------------------
# Phase A5: build_article_subtopic_bindings
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _FakeArticle:
    article_key: str
    source_path: str
    # v4: _graph_article_key reads article_number to decide the graph MERGE key.
    # Numbered articles (non-empty) keep their article_key as the graph key;
    # prose-only (empty) remap to `whole::{source_path}`. Tests below rely on
    # the numbered behavior, so default to a non-empty placeholder.
    article_number: str = "1"


@dataclass
class _FakeTaxonomyEntry:
    label: str


class _FakeRichTaxonomy:
    def __init__(self, entries: dict[tuple[str, str], str]):
        self.lookup_by_key = {
            key: _FakeTaxonomyEntry(label=label) for key, label in entries.items()
        }


def _doc(
    source_path: str,
    *,
    topic_key: str = "laboral",
    subtopic_key: str | None = None,
) -> CorpusDocument:
    return _make_doc(
        source_path=source_path, topic_key=topic_key, subtopic_key=subtopic_key
    )


def test_bindings_cover_docs_with_valid_subtopic_and_skip_others() -> None:
    docs = (
        _doc("a.md", topic_key="laboral", subtopic_key="aporte_parafiscales_icbf"),
        _doc("b.md", topic_key="laboral", subtopic_key="hallucinated"),
        _doc("c.md", topic_key="laboral", subtopic_key=None),
    )
    articles = (
        _FakeArticle(article_key="ART_A", source_path="a.md"),
        _FakeArticle(article_key="ART_B", source_path="b.md"),
        _FakeArticle(article_key="ART_C", source_path="c.md"),
    )
    taxonomy = _FakeRichTaxonomy(
        {("laboral", "aporte_parafiscales_icbf"): "Aporte Parafiscales ICBF"}
    )
    bindings = build_article_subtopic_bindings(
        classified_documents=docs,
        articles=articles,
        taxonomy=taxonomy,
    )
    assert set(bindings.keys()) == {"ART_A"}
    binding = bindings["ART_A"]
    assert binding.sub_topic_key == "aporte_parafiscales_icbf"
    assert binding.parent_topic == "laboral"
    assert binding.label == "Aporte Parafiscales ICBF"


def test_bindings_dedupe_two_articles_share_same_subtopic() -> None:
    docs = (
        _doc("a.md", topic_key="laboral", subtopic_key="liquidacion_cesantias"),
        _doc("b.md", topic_key="laboral", subtopic_key="liquidacion_cesantias"),
    )
    articles = (
        _FakeArticle(article_key="ART_A", source_path="a.md"),
        _FakeArticle(article_key="ART_B", source_path="b.md"),
    )
    taxonomy = _FakeRichTaxonomy(
        {("laboral", "liquidacion_cesantias"): "Liquidacion Cesantias"}
    )
    bindings = build_article_subtopic_bindings(
        classified_documents=docs,
        articles=articles,
        taxonomy=taxonomy,
    )
    assert set(bindings.keys()) == {"ART_A", "ART_B"}
    # Both point at the same SubtopicBinding triplet (same sub_topic_key).
    assert bindings["ART_A"].sub_topic_key == bindings["ART_B"].sub_topic_key


def test_bindings_skip_orphan_subtopic_not_in_taxonomy() -> None:
    docs = (_doc("a.md", topic_key="laboral", subtopic_key="not_in_taxonomy"),)
    articles = (_FakeArticle(article_key="ART_A", source_path="a.md"),)
    taxonomy = _FakeRichTaxonomy({("laboral", "something_else"): "x"})
    bindings = build_article_subtopic_bindings(
        classified_documents=docs,
        articles=articles,
        taxonomy=taxonomy,
    )
    assert bindings == {}


def test_bindings_empty_when_no_subtopic_docs() -> None:
    docs = (_doc("a.md", subtopic_key=None),)
    articles = (_FakeArticle(article_key="ART_A", source_path="a.md"),)
    taxonomy = _FakeRichTaxonomy({})
    bindings = build_article_subtopic_bindings(
        classified_documents=docs,
        articles=articles,
        taxonomy=taxonomy,
    )
    assert bindings == {}


def test_build_graph_load_plan_emits_subtopic_nodes_and_edges() -> None:
    """End-to-end: classified docs → bindings → loader emits Falkor structure."""
    from lia_graph.graph.schema import EdgeKind, NodeKind
    from lia_graph.ingestion import build_graph_load_plan
    from lia_graph.ingestion.parser import ParsedArticle

    articles = (
        ParsedArticle(
            article_key="1",
            article_number="1",
            heading="Articulo 1",
            body="body",
            full_text="Articulo 1\nbody",
            status="active",
            source_path="a.md",
        ),
        ParsedArticle(
            article_key="2",
            article_number="2",
            heading="Articulo 2",
            body="body",
            full_text="Articulo 2\nbody",
            status="active",
            source_path="b.md",
        ),
    )
    docs = (
        _doc("a.md", topic_key="laboral", subtopic_key="aporte_parafiscales_icbf"),
        _doc("b.md", topic_key="laboral", subtopic_key="aporte_parafiscales_icbf"),
    )
    taxonomy = _FakeRichTaxonomy(
        {("laboral", "aporte_parafiscales_icbf"): "Aporte Parafiscales ICBF"}
    )
    bindings = build_article_subtopic_bindings(
        classified_documents=docs,
        articles=articles,
        taxonomy=taxonomy,
    )
    plan = build_graph_load_plan(articles, (), article_subtopics=bindings)
    subtopic_nodes = [n for n in plan.nodes if n.kind is NodeKind.SUBTOPIC]
    subtopic_edges = [e for e in plan.edges if e.kind is EdgeKind.HAS_SUBTOPIC]
    assert len(subtopic_nodes) == 1  # deduplicated
    assert len(subtopic_edges) == 2  # one per article


def test_build_graph_load_plan_skip_llm_path_emits_zero_subtopic_structure() -> None:
    """When A4's ``skip_llm`` returns legacy tuple, no doc has a curated
    subtopic_key that resolves in taxonomy, so bindings is empty and the
    loader emits no SubTopic nodes/edges. Regression guard for Phase A4 §(b)."""
    from lia_graph.graph.schema import EdgeKind, NodeKind
    from lia_graph.ingestion import build_graph_load_plan
    from lia_graph.ingestion.parser import ParsedArticle

    articles = (
        ParsedArticle(
            article_key="1",
            article_number="1",
            heading="A",
            body="b",
            full_text="A\nb",
            status="active",
            source_path="a.md",
        ),
    )
    # Simulate skip_llm — docs keep the legacy key which is not in taxonomy.
    docs = (_doc("a.md", topic_key="laboral", subtopic_key="legacy_regex_guess"),)
    taxonomy = _FakeRichTaxonomy(
        {("laboral", "curated_only_key"): "Curated"}
    )
    bindings = build_article_subtopic_bindings(
        classified_documents=docs,
        articles=articles,
        taxonomy=taxonomy,
    )
    plan = build_graph_load_plan(articles, (), article_subtopics=bindings)
    assert bindings == {}
    assert not [n for n in plan.nodes if n.kind is NodeKind.SUBTOPIC]
    assert not [e for e in plan.edges if e.kind is EdgeKind.HAS_SUBTOPIC]
