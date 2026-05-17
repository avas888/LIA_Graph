"""fix_v22_may §9c P2-T-Orphan — truncated chunk-tail filter (L13).

Revived from the orphan ``fix_v7-truncated-tail-and-canonical-shapes``
branch (HEAD ``4b953ca``, 2026-04-30). Locks:

  1. ``_TRUNCATED_TAIL_TOKEN_RE`` matches lines ending in known Spanish
     abbreviations / word-fragments (``art``, ``núm``, ``fra``, etc.).
  2. ``_merge_abbreviation_splits`` rejoins ``art.`` / ``núm.`` /
     ``pág.`` splits but preserves real sentence boundaries.
  3. ``_evidence_candidate_lines`` drops the bad fragment instead of
     auto-adding a trailing period.
"""

from __future__ import annotations

from lia_graph.pipeline_d.answer_support import (
    _ABBREVIATION_BEFORE_PERIOD_RE,
    _TRUNCATED_TAIL_TOKEN_RE,
    _evidence_candidate_lines,
    _merge_abbreviation_splits,
)


def test_truncated_tail_re_matches_known_abbreviations() -> None:
    assert _TRUNCATED_TAIL_TOKEN_RE.search("...por cada mes o fra")
    assert _TRUNCATED_TAIL_TOKEN_RE.search("ver el art")
    assert _TRUNCATED_TAIL_TOKEN_RE.search("según el núm")
    # Real-prose endings should NOT match.
    assert not _TRUNCATED_TAIL_TOKEN_RE.search("debe pagar una indemnización al trabajador")


def test_abbreviation_before_period_re_matches_known_abbrevs() -> None:
    assert _ABBREVIATION_BEFORE_PERIOD_RE.search("Según el art.")
    assert _ABBREVIATION_BEFORE_PERIOD_RE.search("Ver núm.")
    # Real sentence end is NOT an abbreviation split.
    assert not _ABBREVIATION_BEFORE_PERIOD_RE.search("debe pagar.")


def test_merge_abbreviation_splits_rejoins_art_period() -> None:
    parts = ["Según el art.", "64 del CST cuando un empleador termina."]
    merged = _merge_abbreviation_splits(parts)
    assert len(merged) == 1
    assert merged[0].startswith("Según el art. 64 del CST")


def test_merge_abbreviation_splits_preserves_real_boundaries() -> None:
    # A new sentence (uppercase first char) should NOT be merged.
    parts = ["Según el artículo.", "El empleador debe pagar."]
    merged = _merge_abbreviation_splits(parts)
    assert len(merged) == 2


def test_evidence_candidate_lines_drops_truncated_tail_fragment() -> None:
    text = (
        "Según el art. 64 del CST cuando un empleador termina "
        "unilateralmente el contrato sin justa causa debe pagar una "
        "indemnización al trabajador. Esto se aplica también para los "
        "contratos a término indefinido por cada mes o fra"
    )
    lines = _evidence_candidate_lines(text)
    # The good first sentence survives; the truncated tail is dropped.
    joined = " || ".join(lines)
    assert "indemnización al trabajador" in joined
    assert "por cada mes o fra." not in joined
    assert "o fra." not in joined
