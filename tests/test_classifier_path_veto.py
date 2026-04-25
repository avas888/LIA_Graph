"""next_v3 §13.6 — Option K2 path-veto layer above the LLM.

Pins the veto table: every entry in the 5 Cypher flip rows + unchanged row
(next_v3 §8.2) must route through _apply_path_veto to its canonical topic.

Tests also lock:
  - LLM verdict preserved when no path rule fires.
  - LLM verdict preserved (no-op) when the rule's canonical topic already
    matches the LLM verdict — only mis-matches trigger an override.
  - Empty filename is a safe no-op.
  - First-match-wins semantics when path contains multiple needles (the
    rule list order matters).
"""

from __future__ import annotations

import pytest

from lia_graph.ingestion_classifier import (
    _apply_path_veto,
    _PATH_VETO_RULES,
)


# ---------------------------------------------------------------------------
# The 5 Cypher flip rows (next_v3 §8.2) + unchanged row — these MUST all
# route to the SME-canonical topic post-veto.
# ---------------------------------------------------------------------------

CYPHER_FLIP_ROWS = (
    (
        "CORE ya Arriba/RENTA/NORMATIVA/Normativa/06_Libro1_T1_Cap5_Deducciones.md",
        "iva",                             # wrong LLM verdict that Cypher Row 1 caught
        "costos_deducciones_renta",        # expected post-veto
    ),
    (
        "CORE ya Arriba/RENTA/NORMATIVA/Normativa/17_Libro4_Timbre.md",
        "facturacion_electronica",         # pre-taxonomy-v2 mis-routing
        "impuesto_timbre",
    ),
    (
        "CORE ya Arriba/RENTA/NORMATIVA/Normativa/10_Libro1_T2_Patrimonio.md",
        "sector_cultura",                  # Cypher Row 3 actual wrong verdict
        "patrimonio_fiscal_renta",
    ),
    (
        "CORE ya Arriba/RENTA/NORMATIVA/Normativa/02_Libro1_T1_Cap1_Ingresos.md",
        "iva",                             # Cypher Row 4
        "ingresos_fiscales_renta",
    ),
    (
        "CORE ya Arriba/RENTA/NORMATIVA/Normativa/18_Libro5_Procedimiento_P1.md",
        "iva",                             # Cypher Row 5 part A
        "procedimiento_tributario",
    ),
    (
        "CORE ya Arriba/RENTA/NORMATIVA/Normativa/19_Libro5_Procedimiento_P2.md",
        "iva",                             # Cypher Row 5 part B
        "procedimiento_tributario",
    ),
    (
        "CORE ya Arriba/RENTA/NORMATIVA/Normativa/20_Libro6_GMF.md",
        "gravamen_movimiento_financiero_4x1000",  # already correct → no-op
        "gravamen_movimiento_financiero_4x1000",
    ),
)


@pytest.mark.parametrize("path,llm_verdict,expected_final", CYPHER_FLIP_ROWS)
def test_cypher_flip_rows_route_to_canonical(
    path: str, llm_verdict: str, expected_final: str
) -> None:
    final, reason, rule_matched = _apply_path_veto(path, llm_verdict)
    assert final == expected_final
    # Every CYPHER_FLIP_ROWS entry hits a rule, so rule_matched is always True.
    assert rule_matched is True
    if llm_verdict == expected_final:
        # Rule matched but LLM already correct — reason must be None (no
        # event emitted) but rule_matched is still True so the verdict
        # propagates as path_veto-sourced.
        assert reason is None
    else:
        # Actual override — reason string carries needle + canonical.
        assert reason is not None
        assert expected_final in reason
        assert "path_veto:" in reason


# ---------------------------------------------------------------------------
# No-op cases.
# ---------------------------------------------------------------------------

def test_non_renta_path_preserves_llm_verdict() -> None:
    final, reason, rule_matched = _apply_path_veto(
        "CORE ya Arriba/LEYES/COMERCIAL_SOCIETARIO/some_doc.md", "comercial_societario"
    )
    assert final == "comercial_societario"
    assert reason is None
    assert rule_matched is False


def test_empty_filename_is_noop() -> None:
    assert _apply_path_veto("", "iva") == ("iva", None, False)
    assert _apply_path_veto(None, "iva") == ("iva", None, False)  # type: ignore[arg-type]


def test_llm_verdict_preserved_when_no_rule_matches() -> None:
    final, reason, rule_matched = _apply_path_veto(
        "knowledge_base/CORE ya Arriba/LABORAL/reforma_2466.md", "laboral"
    )
    assert final == "laboral"
    assert reason is None
    assert rule_matched is False


def test_no_op_match_still_signals_rule_matched() -> None:
    """Critical bug regression: when LLM verdict already matches the rule's
    canonical topic, the rule still asserted it (rule_matched=True) so the
    document's legacy topic_key gets overridden downstream."""
    path = "CORE ya Arriba/RENTA/NORMATIVA/Normativa/18_Libro5_Procedimiento_P1.md"
    final, reason, rule_matched = _apply_path_veto(path, "procedimiento_tributario")
    assert final == "procedimiento_tributario"
    assert reason is None  # no override → no event
    assert rule_matched is True  # but the rule did fire — signal it


# ---------------------------------------------------------------------------
# Override semantics for the remaining canonical topics in _PATH_VETO_RULES.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("needle,canonical", _PATH_VETO_RULES)
def test_wrong_verdict_always_flips_to_canonical(
    needle: str, canonical: str
) -> None:
    path = f"CORE ya Arriba/RENTA/NORMATIVA/Normativa/{needle}.md"
    wrong_verdict = "sagrilaft_ptee" if canonical != "sagrilaft_ptee" else "iva"
    final, reason, rule_matched = _apply_path_veto(path, wrong_verdict)
    assert final == canonical, f"path {needle!r}: LLM={wrong_verdict!r} expected {canonical!r} got {final!r}"
    assert reason is not None
    assert rule_matched is True
    assert canonical in reason


# ---------------------------------------------------------------------------
# First-match-wins.
# ---------------------------------------------------------------------------

def test_first_match_wins_on_specific_chapter() -> None:
    path = "CORE ya Arriba/RENTA/NORMATIVA/Normativa/06_Libro1_T1_Cap5_Deducciones.md"
    final, reason, rule_matched = _apply_path_veto(path, "sagrilaft_ptee")
    assert final == "costos_deducciones_renta"
    assert rule_matched is True


def test_path_veto_rules_table_has_no_duplicates() -> None:
    needles = [r[0] for r in _PATH_VETO_RULES]
    assert len(needles) == len(set(needles)), "duplicate path needle in _PATH_VETO_RULES"


def test_path_veto_all_targets_are_valid_taxonomy_keys() -> None:
    """Every canonical topic in the veto table must exist in v2 taxonomy."""
    from lia_graph.topic_taxonomy import iter_topic_taxonomy_entries

    valid_keys = {e.key for e in iter_topic_taxonomy_entries()}
    for _, canonical in _PATH_VETO_RULES:
        assert canonical in valid_keys, (
            f"veto target {canonical!r} is not a valid v2 taxonomy key"
        )
