"""Contract tests for `graph/client.py` result coercion.

Regression guard for a silent-failure incident:

FalkorDB's `GRAPH.QUERY` can return its header either in *compact mode*
(`[type_code, column_name]` pairs) or in *plain mode* (bare column-name
strings). The client used by the served runtime does not request compact
mode, so production responses arrive as bare strings. Prior to the fix,
`_header_name` only handled the compact shape and fell back to
`column_{index}` for everything else — which meant every `RETURN x AS y`
in the retriever's Cypher silently became `column_1, column_2, ...`
downstream. `row.get("article_key")` / `.get("heading")` always returned
`None`, and every graph-native answer quietly fell back to template mode.

These tests lock the invariant: regardless of header shape, the driver
must surface user-declared column names so downstream retrievers can read
by alias.
"""

from __future__ import annotations

from lia_graph.graph.client import _coerce_query_rows, _header_name


def test_header_name_handles_compact_header() -> None:
    # Compact mode: header element is [type_code, column_name]
    assert _header_name([1, "article_key"], index=0) == "article_key"
    assert _header_name([4, "heading"], index=1) == "heading"


def test_header_name_handles_plain_string_header() -> None:
    # This is the production shape — without this, the retriever was blind.
    assert _header_name("article_key", index=0) == "article_key"
    assert _header_name("heading", index=1) == "heading"
    assert _header_name("text_current", index=2) == "text_current"


def test_header_name_handles_bytes_header() -> None:
    # RESP2 may deliver string headers as bytes depending on the socket driver.
    assert _header_name(b"article_key", index=0) == "article_key"


def test_header_name_falls_back_to_positional_for_unknown_shape() -> None:
    assert _header_name(None, index=3) == "column_3"
    assert _header_name(42, index=5) == "column_5"
    assert _header_name([], index=7) == "column_7"
    assert _header_name("", index=2) == "column_2"  # empty string is not a name


def test_coerce_query_rows_aliases_preserved_with_plain_header() -> None:
    header = ["article_key", "heading", "text_current"]
    raw_rows = [
        ["147", "COMPENSACIÓN DE PÉRDIDAS FISCALES DE SOCIEDADES.", "Las sociedades podrán compensar..."],
        ["290", "RÉGIMEN DE TRANSICIÓN", "Para los bienes depreciables..."],
    ]
    rows = _coerce_query_rows(header, raw_rows)
    assert len(rows) == 2
    # Downstream retrievers read by these names — this is the invariant.
    assert rows[0]["article_key"] == "147"
    assert rows[0]["heading"].startswith("COMPENSACIÓN")
    assert rows[1]["article_key"] == "290"
    # And crucially: `column_1` must NOT be what downstream gets.
    assert "column_1" not in rows[0]


def test_coerce_query_rows_aliases_preserved_with_compact_header() -> None:
    header = [[1, "article_key"], [4, "heading"]]
    raw_rows = [["147", "COMPENSACIÓN DE PÉRDIDAS FISCALES DE SOCIEDADES."]]
    rows = _coerce_query_rows(header, raw_rows)
    assert rows[0]["article_key"] == "147"
    assert rows[0]["heading"].startswith("COMPENSACIÓN")


def test_coerce_query_rows_empty_when_header_malformed() -> None:
    # Safety: don't crash on garbage from the wire
    assert _coerce_query_rows(None, [[1]]) == ()
    assert _coerce_query_rows(["x"], None) == ()
