"""Schema-consistency invariant: every ``documents.subtema`` written by
single-pass ingest must appear as a ``(parent_topic_key, sub_topic_key)``
pair in the curated taxonomy.

Phase A10 of ingestfix-v2-maximalist (see ``docs/next/ingestfixv2.md``).

Orphan subtemas — keys produced by the classifier that do NOT exist in
``config/subtopic_taxonomy.json`` — have historically been a silent
retrieval-quality degrader: chunks tagged with a subtema that planner
intent detection will never match. This test turns that drift into a
test failure.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.integration


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "mini_corpus"


# Reuse the same fake recorder + factory + classifier stub used by the A9
# integration test — local imports keep the fixture module self-contained.
from .test_single_pass_ingest import (  # noqa: E402
    _FakeSupabaseClient,
    _fake_classifier,
    _falkor_client,
    _purge_subtopic_state,
    _sink_factory,
)


@pytest.fixture
def mini_corpus() -> Path:
    return FIXTURE_ROOT


@pytest.fixture
def falkor_client():
    client = _falkor_client()
    _purge_subtopic_state(client)
    return client


def _collect_written_subtemas(calls) -> set[str]:
    """All non-None documents.subtema values observed in upsert calls."""
    seen: set[str] = set()
    for call in calls:
        if call.table != "documents" or call.op != "upsert":
            continue
        for row in call.payload or []:
            value = row.get("subtema")
            if isinstance(value, str) and value.strip():
                seen.add(value.strip())
    return seen


def test_every_written_subtema_exists_in_taxonomy(
    mini_corpus: Path, falkor_client, tmp_path: Path, monkeypatch
) -> None:
    """After a single-pass ingest, every written ``subtema`` is a curated key."""
    from lia_graph.ingest import materialize_graph_artifacts
    from lia_graph.subtopic_taxonomy_loader import load_taxonomy

    monkeypatch.setattr(
        "lia_graph.ingestion_classifier.classify_ingestion_document",
        _fake_classifier,
    )

    supabase = _FakeSupabaseClient()
    materialize_graph_artifacts(
        corpus_dir=mini_corpus,
        artifacts_dir=tmp_path / "artifacts",
        execute_load=True,
        allow_unblessed_load=True,
        supabase_sink=True,
        supabase_target="wip",
        supabase_sink_factory=_sink_factory(supabase),
        graph_client=falkor_client,
        skip_llm=False,
        rate_limit_rpm=0,
        strict_falkordb=True,
    )
    written = _collect_written_subtemas(supabase.calls)

    taxonomy = load_taxonomy()
    curated_sub_keys = {
        sub_key for (_parent, sub_key) in taxonomy.lookup_by_key.keys()
    }
    orphans = written - curated_sub_keys
    assert not orphans, (
        f"single-pass ingest wrote subtemas not in the curated taxonomy "
        f"({taxonomy.version}): {sorted(orphans)}"
    )


def test_orphan_classifier_verdict_is_not_written_as_subtema(
    mini_corpus: Path, falkor_client, tmp_path: Path, monkeypatch
) -> None:
    """When the classifier returns a subtopic_key not in the taxonomy, the
    ingest must NOT write it into ``documents.subtema`` — instead the doc
    should be flagged ``requires_subtopic_review=True``."""
    from lia_graph.ingest import materialize_graph_artifacts

    def _orphan_classifier(*, filename: str, body_text: str):
        @dataclass
        class _V:
            subtopic_key: str | None
            subtopic_label: str | None = None
            subtopic_confidence: float = 0.99
            requires_subtopic_review: bool = False
            detected_topic: str | None = "laboral"

        return _V(subtopic_key="never_in_taxonomy_zzz")

    monkeypatch.setattr(
        "lia_graph.ingestion_classifier.classify_ingestion_document",
        _orphan_classifier,
    )
    supabase = _FakeSupabaseClient()
    materialize_graph_artifacts(
        corpus_dir=mini_corpus,
        artifacts_dir=tmp_path / "artifacts",
        execute_load=True,
        allow_unblessed_load=True,
        supabase_sink=True,
        supabase_target="wip",
        supabase_sink_factory=_sink_factory(supabase),
        graph_client=falkor_client,
        skip_llm=False,
        rate_limit_rpm=0,
        strict_falkordb=True,
    )
    written = _collect_written_subtemas(supabase.calls)
    assert "never_in_taxonomy_zzz" not in written
