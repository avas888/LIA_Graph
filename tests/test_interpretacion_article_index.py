"""fix_v10_may Phase 10C — Article → Interpretation-doc index tests."""

from __future__ import annotations

import pytest

from lia_graph.interpretacion import article_index
from lia_graph.interpretacion.article_index import (
    article_to_doc_ids,
    doc_ids_for_article_refs,
    normalize_article_key,
    reset_cache,
)


# ---------------------------------------------------------------------------
# normalize_article_key — pure helper, covers every shape that bleeds in.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("et_art_115", "art_115"),
        ("art_115_et", "art_115"),
        ("et_art_124_2", "art_124_2"),
        ("art_124_2_et", "art_124_2"),
        ("Art. 115 ET", "art_115"),
        ("art_869", "art_869"),
        ("ET-ART-242", "art_242"),
        ("", ""),
        ("___", ""),
        ("et_art_115_et", "art_115"),
    ],
)
def test_normalize_article_key_canonicalizes_shape_variants(
    raw: str, expected: str
) -> None:
    assert normalize_article_key(raw) == expected


# ---------------------------------------------------------------------------
# Index build — exercise via monkeypatched catalog rows.
# ---------------------------------------------------------------------------


def _patch_rows(monkeypatch: pytest.MonkeyPatch, rows: list[dict]) -> None:
    """Replace the index's manifest+markdown readers with fixtures.

    `rows` is a list of `{"relative_path": str, "normative_refs": tuple}`
    shaped the same way the catalog produced them pre-Phase 10C — we
    translate that into the new `_iter_interpretation_manifest_entries`
    + `_full_markdown_text` pair so existing test cases keep their
    shape.
    """
    reset_cache()
    entries = [
        {"relative_path": r["relative_path"], "manifest_entry": {}}
        for r in rows
        if r.get("relative_path")
    ]

    def _fake_entries():
        return entries

    def _fake_text(relative_path: str) -> str:
        # Build a synthetic markdown body that mentions each declared ref
        # in the canonical `Art. NN ET` form so `extract_article_refs`
        # produces the expected set.
        for r in rows:
            if r.get("relative_path") == relative_path:
                refs = r.get("normative_refs") or ()
                # Convert refs to displayable form
                snippets: list[str] = []
                for ref in refs:
                    # Strip et_ prefix and _et suffix, replace _ with -
                    s = str(ref or "").lower().strip()
                    if s.startswith("et_art_"):
                        s = s[len("et_art_"):]
                    elif s.startswith("art_") and s.endswith("_et"):
                        s = s[len("art_"):-len("_et")]
                    elif s.startswith("art_"):
                        s = s[len("art_"):]
                    s = s.replace("_", "-")
                    snippets.append(f"Art. {s} ET")
                # Add some raw text shapes too so the regex sees variety
                return "Encabezado.\n\n" + " ".join(snippets) + ".\n"
        return ""

    monkeypatch.setattr(
        article_index,
        "_iter_interpretation_manifest_entries",
        _fake_entries,
    )
    monkeypatch.setattr(
        article_index,
        "_full_markdown_text",
        _fake_text,
    )


def test_index_groups_doc_ids_by_normalized_article_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Multiple docs interpret the same article → both doc_ids in the
    same key's set. One doc interprets multiple articles → that doc_id
    appears under every relevant key."""
    _patch_rows(
        monkeypatch,
        [
            {
                "relative_path": "EXPERTOS/crowe/art_115_y_124.md",
                "normative_refs": ("et_art_115", "et_art_124_2"),
            },
            {
                "relative_path": "EXPERTOS/ey/solo_art_115.md",
                "normative_refs": ("et_art_115",),
            },
            {
                "relative_path": "EXPERTOS/kpmg/solo_art_869.md",
                "normative_refs": ("et_art_869",),
            },
        ],
    )
    index = article_to_doc_ids()
    # art_115 has both Crowe + EY
    assert "art_115" in index
    art_115_docs = index["art_115"]
    assert "EXPERTOS_crowe_art_115_y_124.md" in art_115_docs
    assert "EXPERTOS_ey_solo_art_115.md" in art_115_docs
    # art_124_2 only has Crowe
    assert "art_124_2" in index
    assert index["art_124_2"] == frozenset(
        {"EXPERTOS_crowe_art_115_y_124.md"}
    )
    # art_869 only has KPMG
    assert index["art_869"] == frozenset(
        {"EXPERTOS_kpmg_solo_art_869.md"}
    )


def test_index_skips_rows_with_empty_relative_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_rows(
        monkeypatch,
        [
            {"relative_path": "", "normative_refs": ("et_art_115",)},
            {"relative_path": None, "normative_refs": ("et_art_124",)},
            {
                "relative_path": "EXPERTOS/keepme.md",
                "normative_refs": ("et_art_115",),
            },
        ],
    )
    index = article_to_doc_ids()
    assert index["art_115"] == frozenset({"EXPERTOS_keepme.md"})


def test_index_extracts_from_full_text_not_from_truncated_preview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phase 10C invariant — the index reads FULL markdown, not the
    catalog's 12K preview. A doc whose first Art-115 mention sits at
    char 15000 must still land under `art_115` in the index."""
    reset_cache()
    monkeypatch.setattr(
        article_index,
        "_iter_interpretation_manifest_entries",
        lambda: [{"relative_path": "EXPERTOS/longdoc.md", "manifest_entry": {}}],
    )
    # 15 KiB of filler followed by the article mention.
    body = ("Lorem ipsum dolor sit amet. " * 600) + "\n\nVer Art. 115 ET para detalle."
    assert len(body) > 14000
    monkeypatch.setattr(
        article_index,
        "_full_markdown_text",
        lambda _rp: body,
    )
    index = article_to_doc_ids()
    assert "art_115" in index
    assert index["art_115"] == frozenset({"EXPERTOS_longdoc.md"})


def test_doc_ids_for_article_refs_unions_across_refs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_rows(
        monkeypatch,
        [
            {
                "relative_path": "EXPERTOS/a.md",
                "normative_refs": ("et_art_115",),
            },
            {
                "relative_path": "EXPERTOS/b.md",
                "normative_refs": ("et_art_124_2",),
            },
            {
                "relative_path": "EXPERTOS/c.md",
                "normative_refs": ("et_art_242",),
            },
        ],
    )
    # Query with refs that hit a + b — union
    docs = doc_ids_for_article_refs(("et_art_115", "et_art_124_2"))
    assert docs == frozenset({"EXPERTOS_a.md", "EXPERTOS_b.md"})

    # Query with a ref that has no docs → empty set
    assert doc_ids_for_article_refs(("et_art_999",)) == frozenset()

    # Empty input → empty set, not exception
    assert doc_ids_for_article_refs(()) == frozenset()


def test_doc_ids_for_article_refs_canonicalizes_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Caller passing `art_124_2_et` should match index entries built
    from `et_art_124_2`."""
    _patch_rows(
        monkeypatch,
        [
            {
                "relative_path": "EXPERTOS/crowe.md",
                "normative_refs": ("et_art_124_2",),
            },
        ],
    )
    # Caller-style: chunk concept_tags use `art_NNN_et`
    docs_caller_a = doc_ids_for_article_refs(("art_124_2_et",))
    # Dispatcher-style: extract_article_refs() returns `et_art_NNN`
    docs_caller_b = doc_ids_for_article_refs(("et_art_124_2",))
    assert docs_caller_a == frozenset({"EXPERTOS_crowe.md"})
    assert docs_caller_a == docs_caller_b
