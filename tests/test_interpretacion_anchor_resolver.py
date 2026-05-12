"""fix_v11_may Phase 11B — anchor resolver unit tests.

Exercises the article-ref normalization, the Falkor Cypher path (with a
mocked GraphClient.execute), the LIA_PLANNER_INTERPRETATION_ANCHOR
gate, the per-article LIMIT + total_cap, and the graceful-degrade
behavior on Falkor errors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from lia_graph.graph.client import GraphQueryResult, GraphWriteStatement
from lia_graph.interpretacion.anchor_resolver import (
    AnchorResolution,
    anchor_resolver_enabled,
    resolve_anchor_doc_ids,
)


# ---------------------------------------------------------------------------
# Fake GraphClient — records every executed statement; returns canned
# rows keyed by the `num` parameter.
# ---------------------------------------------------------------------------


@dataclass
class _FakeGraphClient:
    canned: dict[str, list[dict[str, Any]]]
    executed: list[GraphWriteStatement]
    raises_for: set[str]

    def execute(
        self, statement: GraphWriteStatement, *, strict: bool = False
    ) -> GraphQueryResult:
        self.executed.append(statement)
        num = str(statement.parameters.get("num", ""))
        if num in self.raises_for:
            raise RuntimeError(f"fake falkor failure on {num}")
        rows = tuple(self.canned.get(num, ()))
        return GraphQueryResult(
            description=statement.description,
            query=statement.query,
            parameters=statement.parameters,
            rows=rows,
        )


def _make_client(
    canned: dict[str, list[dict[str, Any]]] | None = None,
    *,
    raises_for: set[str] | None = None,
) -> _FakeGraphClient:
    return _FakeGraphClient(
        canned=canned or {},
        executed=[],
        raises_for=raises_for or set(),
    )


@pytest.fixture(autouse=True)
def _enable_anchor(monkeypatch: pytest.MonkeyPatch) -> None:
    """The flag defaults `on`; tests can override with monkeypatch."""
    monkeypatch.setenv("LIA_PLANNER_INTERPRETATION_ANCHOR", "on")


# ---------------------------------------------------------------------------
# Flag gating
# ---------------------------------------------------------------------------


def test_anchor_flag_default_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LIA_PLANNER_INTERPRETATION_ANCHOR", raising=False)
    assert anchor_resolver_enabled() is True


@pytest.mark.parametrize("value", ["off", "0", "false", "no"])
def test_anchor_flag_off_disables(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("LIA_PLANNER_INTERPRETATION_ANCHOR", value)
    assert anchor_resolver_enabled() is False


def test_resolve_returns_skipped_when_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_PLANNER_INTERPRETATION_ANCHOR", "off")
    client = _make_client({"115": [{"doc_id": "x", "trust_tier": "high"}]})
    out = resolve_anchor_doc_ids(("et_art_115",), graph_client=client)
    assert out.doc_ids == ()
    assert out.diagnostic["anchor_source"] == "skipped"
    assert out.diagnostic["reason"] == "flag_off"
    # No Cypher fired
    assert client.executed == []


def test_resolve_returns_skipped_when_no_article_refs() -> None:
    client = _make_client()
    out = resolve_anchor_doc_ids((), graph_client=client)
    assert out.doc_ids == ()
    assert out.diagnostic["anchor_source"] == "skipped"
    assert out.diagnostic["reason"] == "no_article_refs"
    assert client.executed == []


def test_resolve_skips_when_refs_dont_reduce_to_numbers() -> None:
    """Refs that can't be reduced to bare numbers (e.g. prose-only
    article keys) are dropped — no Cypher fires, diagnostic reports
    why."""
    client = _make_client()
    out = resolve_anchor_doc_ids(
        ("whole::path/to/some_doc.md", "not-an-article"),
        graph_client=client,
    )
    assert out.doc_ids == ()
    assert out.diagnostic["reason"] == "no_resolvable_numbers"
    assert client.executed == []


# ---------------------------------------------------------------------------
# Article-ref normalization — accepts the multiple shapes the codebase
# uses for the same article.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ref,expected_number",
    [
        ("et_art_115", "115"),
        ("art_115_et", "115"),
        ("et_art_124_2", "124-2"),
        ("art_124_2_et", "124-2"),
        ("art_124-2", "124-2"),
        ("115", "115"),
        ("124-2", "124-2"),
    ],
)
def test_resolve_normalizes_ref_shapes(ref: str, expected_number: str) -> None:
    client = _make_client(
        {expected_number: [{"doc_id": f"d_{expected_number}", "trust_tier": "high"}]}
    )
    out = resolve_anchor_doc_ids((ref,), graph_client=client)
    assert out.doc_ids == (f"d_{expected_number}",)
    assert out.diagnostic["anchor_source"] == "falkor"
    assert out.diagnostic["matched_articles"] == 1


def test_resolve_dedupes_refs_that_normalize_to_same_number() -> None:
    """When two refs normalize to the same article_number, we issue
    only one Cypher (avoids redundant round-trips)."""
    client = _make_client(
        {"115": [{"doc_id": "d_115_a", "trust_tier": "high"}]}
    )
    out = resolve_anchor_doc_ids(
        ("et_art_115", "art_115_et", "115"),
        graph_client=client,
    )
    assert out.doc_ids == ("d_115_a",)
    # Only one statement executed despite three input refs
    assert len(client.executed) == 1


# ---------------------------------------------------------------------------
# Trust-tier ordering + dedup across articles
# ---------------------------------------------------------------------------


def test_resolve_preserves_cursor_order_across_articles() -> None:
    """The Cypher returns rows ordered by trust_tier DESC per article.
    Across articles, refs are iterated in input order; doc_ids are
    deduped on first occurrence so a high-tier doc that interprets
    BOTH articles surfaces from the first article's match set."""
    client = _make_client(
        {
            "115": [
                {"doc_id": "d_high_1", "trust_tier": "high"},
                {"doc_id": "d_med_1", "trust_tier": "medium"},
            ],
            "124-2": [
                # d_high_1 also interprets 124-2; deduped, original
                # position preserved.
                {"doc_id": "d_high_1", "trust_tier": "high"},
                {"doc_id": "d_high_2", "trust_tier": "high"},
                {"doc_id": "d_low_2", "trust_tier": "low"},
            ],
        }
    )
    out = resolve_anchor_doc_ids(
        ("et_art_115", "et_art_124_2"), graph_client=client
    )
    assert out.doc_ids == ("d_high_1", "d_med_1", "d_high_2", "d_low_2")
    assert out.diagnostic["matched_articles"] == 2
    assert out.diagnostic["matched_doc_ids"] == 4


def test_resolve_respects_total_cap() -> None:
    """The `total_cap` parameter bounds the returned doc_ids regardless
    of how many articles match."""
    client = _make_client(
        {
            "115": [
                {"doc_id": f"d_115_{i}", "trust_tier": "medium"}
                for i in range(10)
            ],
            "124-2": [
                {"doc_id": f"d_124_{i}", "trust_tier": "medium"}
                for i in range(10)
            ],
        }
    )
    out = resolve_anchor_doc_ids(
        ("115", "124-2"),
        graph_client=client,
        total_cap=5,
    )
    assert len(out.doc_ids) == 5
    # First five come from the first article (cursor order)
    assert all(d.startswith("d_115_") for d in out.doc_ids)


def test_resolve_passes_limit_per_article_through_to_cypher() -> None:
    """The per-article LIMIT is baked into the query string so the
    Cypher server stops at LIMIT rows even if the corpus has many
    more interpretations."""
    client = _make_client({"115": [{"doc_id": "d_x", "trust_tier": "high"}]})
    resolve_anchor_doc_ids(
        ("115",),
        graph_client=client,
        limit_per_article=3,
    )
    [stmt] = client.executed
    assert "LIMIT 3" in stmt.query


# ---------------------------------------------------------------------------
# Empty / error degradation — anchor is a ranking signal, not load-bearing.
# ---------------------------------------------------------------------------


def test_resolve_returns_empty_with_diagnostic_when_falkor_returns_nothing() -> None:
    """If the loader hasn't run (or the article truly has no
    interpretations), we return empty + a `falkor_empty` reason. The
    dispatcher will then fall back to the Python article_index."""
    client = _make_client({"115": []})
    out = resolve_anchor_doc_ids(("115",), graph_client=client)
    assert out.doc_ids == ()
    assert out.diagnostic["anchor_source"] == "falkor_empty"
    assert out.diagnostic["reason"] == "no_interprets_edges"


def test_resolve_continues_past_per_article_errors() -> None:
    """A single article's Cypher failing doesn't sink the whole
    resolution — other articles' results still surface."""
    client = _make_client(
        {
            "124-2": [{"doc_id": "d_ok", "trust_tier": "high"}],
        },
        raises_for={"115"},
    )
    out = resolve_anchor_doc_ids(("115", "124-2"), graph_client=client)
    assert out.doc_ids == ("d_ok",)
    assert out.diagnostic["anchor_source"] == "falkor"
    # The error is recorded as a partial failure for operator visibility
    assert "partial_errors" in out.diagnostic
    assert any("115" in e for e in out.diagnostic["partial_errors"])


def test_resolve_returns_error_diagnostic_when_all_articles_fail() -> None:
    """When every article's Cypher fails, return empty + a
    `falkor_error` reason. Dispatcher falls back to the Python index;
    the operator sees the error in the panel diagnostics."""
    client = _make_client(raises_for={"115", "124-2"})
    out = resolve_anchor_doc_ids(("115", "124-2"), graph_client=client)
    assert out.doc_ids == ()
    assert out.diagnostic["anchor_source"] == "falkor_error"
    assert out.diagnostic["reason"] == "cypher_errors_no_results"
    assert len(out.diagnostic["errors"]) == 2


def test_anchor_resolution_dataclass_is_immutable() -> None:
    res = AnchorResolution(doc_ids=("a", "b"), diagnostic={"x": 1})
    with pytest.raises(Exception):
        res.doc_ids = ("c",)  # type: ignore[misc]
