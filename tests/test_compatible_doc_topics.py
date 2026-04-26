"""Tests for `pipeline_d/compatible_doc_topics.py` (v5 §1.B)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lia_graph.pipeline_d import compatible_doc_topics as cdt


@pytest.fixture(autouse=True)
def _reset_cache() -> None:
    cdt.reset_lookup_cache_for_tests()
    yield
    cdt.reset_lookup_cache_for_tests()


def test_missing_config_returns_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "LIA_COMPATIBLE_DOC_TOPICS_PATH", str(tmp_path / "missing.json")
    )
    assert cdt.get_compatible_topics("regimen_cambiario") == frozenset()


def test_well_formed_config_returns_compatible_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Use registered taxonomy keys only (so validation doesn't drop them).
    p = tmp_path / "ok.json"
    p.write_text(
        json.dumps({
            "topics": {
                "regimen_sancionatorio_extemporaneidad": {
                    "compatible_topics": ["procedimiento_tributario"]
                },
                "conciliacion_fiscal": {
                    "compatible_topics": [
                        "procedimiento_tributario", "declaracion_renta",
                    ]
                },
            },
        }),
        encoding="utf-8",
    )
    monkeypatch.setenv("LIA_COMPATIBLE_DOC_TOPICS_PATH", str(p))
    assert cdt.get_compatible_topics(
        "regimen_sancionatorio_extemporaneidad"
    ) == frozenset({"procedimiento_tributario"})
    assert cdt.get_compatible_topics("conciliacion_fiscal") == frozenset(
        {"procedimiento_tributario", "declaracion_renta"}
    )
    assert cdt.get_compatible_topics("unknown_topic") == frozenset()


def test_default_seed_topics_all_in_canonical_taxonomy() -> None:
    """Same discipline as path-veto + secondary_topics — every narrow AND
    every compatible topic in `config/compatible_doc_topics.json` MUST be
    a registered taxonomy key. Operator's binding rule 2026-04-26."""
    from lia_graph.topic_taxonomy import iter_topic_taxonomy_entries

    valid = {e.key for e in iter_topic_taxonomy_entries()}
    cfg = json.loads(
        Path("config/compatible_doc_topics.json").read_text(encoding="utf-8")
    )
    for narrow, entry in cfg.get("topics", {}).items():
        assert narrow in valid, (
            f"narrow topic {narrow!r} is not in topic_taxonomy.json"
        )
        for compat in entry.get("compatible_topics", []):
            assert compat in valid, (
                f"compatible_topic {compat!r} for narrow {narrow!r} is not "
                "in topic_taxonomy.json"
            )


def test_unknown_compatible_dropped_with_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    p = tmp_path / "with_unknown.json"
    p.write_text(
        json.dumps({
            "topics": {
                "conciliacion_fiscal": {
                    "compatible_topics": [
                        "procedimiento_tributario",  # valid
                        "fake_topic_v999",           # bogus
                    ],
                },
            },
        }),
        encoding="utf-8",
    )
    monkeypatch.setenv("LIA_COMPATIBLE_DOC_TOPICS_PATH", str(p))
    result = cdt.get_compatible_topics("conciliacion_fiscal")
    assert result == frozenset({"procedimiento_tributario"})
    err = capsys.readouterr().err
    assert "fake_topic_v999" in err


# ────────────────────────────────────────────────────────────────────────────
# Integration with the coherence gate's _count_support_topic_key_matches.
# ────────────────────────────────────────────────────────────────────────────


def test_coherence_gate_counts_compatible_doc_as_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When a support doc's topic_key is in the router_topic's compatible
    set, it counts as a topic_key match — even if its topic isn't exactly
    the router_topic."""
    p = tmp_path / "test.json"
    p.write_text(
        json.dumps({
            "topics": {
                "conciliacion_fiscal": {
                    "compatible_topics": ["procedimiento_tributario"],
                },
            },
        }),
        encoding="utf-8",
    )
    monkeypatch.setenv("LIA_COMPATIBLE_DOC_TOPICS_PATH", str(p))

    from lia_graph.pipeline_d.contracts import (
        GraphEvidenceBundle, GraphSupportDocument,
    )
    from lia_graph.pipeline_d._coherence_gate import (
        _count_support_topic_key_matches,
    )

    def _doc(topic: str) -> GraphSupportDocument:
        return GraphSupportDocument(
            relative_path="x.md",
            source_path="x.md",
            title_hint="t",
            family="normativa",
            knowledge_class=None,
            topic_key=topic,
            subtopic_key=None,
            canonical_blessing_status=None,
            graph_target=False,
            reason="test",
        )

    bundle = GraphEvidenceBundle(
        primary_articles=(),
        connected_articles=(),
        related_reforms=(),
        support_documents=(
            _doc("procedimiento_tributario"),  # compatible
            _doc("conciliacion_fiscal"),       # exact match
        ),
        citations=(),
        diagnostics={},
    )
    # Pre-§1.B this would return 1 (only the exact match).
    # Post-§1.B it returns 2 (procedimiento_tributario is compatible).
    assert _count_support_topic_key_matches(bundle, "conciliacion_fiscal") == 2


def test_coherence_gate_no_compatible_falls_back_to_strict_match() -> None:
    """For a router topic with no compatible_topics config entry, the
    counting reduces to the pre-§1.B exact-match behavior."""
    from lia_graph.pipeline_d.contracts import (
        GraphEvidenceBundle, GraphSupportDocument,
    )
    from lia_graph.pipeline_d._coherence_gate import (
        _count_support_topic_key_matches,
    )

    def _doc(topic: str) -> GraphSupportDocument:
        return GraphSupportDocument(
            relative_path="x.md",
            source_path="x.md",
            title_hint="t",
            family="normativa",
            knowledge_class=None,
            topic_key=topic,
            subtopic_key=None,
            canonical_blessing_status=None,
            graph_target=False,
            reason="test",
        )

    bundle = GraphEvidenceBundle(
        primary_articles=(),
        connected_articles=(),
        related_reforms=(),
        support_documents=(_doc("declaracion_renta"), _doc("ingresos_fiscales_renta")),
        citations=(),
        diagnostics={},
    )
    # Neither matches `laboral` and `laboral` has no compatible_topics in
    # the seed config → returns 0 (strict pre-§1.B behavior).
    assert _count_support_topic_key_matches(bundle, "laboral") == 0
