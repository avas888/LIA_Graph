"""fix_v25_may.md P14 — synthesis-layer year_facts rewrite tests.

Regression suite: locks the canonical UVT values for AG 2024 / 2025 /
2026 against any future drift in either ``config/year_constants.json``
OR the corpus chunks. If a chunk feeds stale UVT values into the
synthesis template, the rewrite must catch and correct them before
polish ever sees the template.
"""

from __future__ import annotations

import pytest

from lia_graph.pipeline_d.year_facts_synthesis_pass import rewrite_year_constants
from lia_graph.year_facts import clear_cache


@pytest.fixture(autouse=True)
def _flush_cache():
    clear_cache()
    yield
    clear_cache()


# Canonical AG → UVT mapping. Pre-baked here so a future config edit that
# accidentally rolls back the canon will surface as a test fail, not as a
# silent regression in production answers.
CANONICAL = {
    2024: 47_065,
    2025: 49_799,
    2026: 52_374,
}


# 4 / 27 UVT precomputed per year (the multi-UVT thresholds the audit caught wrong).
MULTI_UVT_PRECOMPUTED = {
    2024: {4: 188_260, 27: 1_270_755},
    2025: {4: 199_196, 27: 1_344_573},
    2026: {4: 209_496, 27: 1_414_098},
}


def test_rewrites_stale_uvt_in_ag_2026_paragraph():
    text = (
        "Bases mínimas AG 2026: UVT $49.799. La base mínima 4 UVT = $199.196 "
        "para honorarios; 27 UVT = $1.344.573 para servicios."
    )
    out = rewrite_year_constants(text)
    assert "UVT $52.374" in out.text
    assert "$49.799" not in out.text
    assert "$209.496" in out.text
    assert "$1.414.098" in out.text
    # At least 3 rewrites recorded (UVT + 4 UVT + 27 UVT).
    assert len(out.rewrites) >= 3


def test_corpus_q2_pollution_pattern_is_corrected():
    """Locks the exact phrasing from the audit Q2 chunk — a regression test
    against the corpus pollution that v23 P2 missed."""
    text = (
        "Bases mínimas (AG 2025, UVT $47.065): 4 UVT = $188.260; "
        "27 UVT = $1.270.755. AG 2026 (UVT $49.799): 4 UVT = $199.196; "
        "27 UVT = $1.344.573."
    )
    out = rewrite_year_constants(text)
    # AG 2025 + AG 2026 in the same paragraph → ambiguous → NO rewrite.
    # (The window helper deliberately skips multi-year paragraphs.)
    assert out.text == text or len(out.rewrites) == 0, (
        "Multi-year paragraphs must be left untouched — too risky to "
        "rewrite when two different AG cues coexist"
    )


def test_corpus_q2_split_paragraphs_each_gets_rewritten():
    """When the same content is split into separate paragraphs (one per
    year), each paragraph's UVT values must be checked against that year's
    canonical."""
    text = (
        "Bases mínimas AG 2025 (UVT $47.065): 4 UVT = $188.260; "
        "27 UVT = $1.270.755.\n"
        "\n"
        "Bases mínimas AG 2026 (UVT $49.799): 4 UVT = $199.196; "
        "27 UVT = $1.344.573."
    )
    out = rewrite_year_constants(text)
    # AG 2025 paragraph: UVT $47.065 (2024 value mislabeled) must become $49.799.
    assert "UVT $49.799" in out.text
    # AG 2026 paragraph: UVT $49.799 (2025 value mislabeled) must become $52.374.
    assert "UVT $52.374" in out.text
    # Stale-labeled values must be GONE.
    assert "$47.065" not in out.text
    # The 2026-labeled multi-UVT must be canonical.
    assert "$209.496" in out.text
    assert "$1.414.098" in out.text


def test_correct_values_are_not_rewritten():
    """When the chunk already carries canonical UVT, no rewrite fires."""
    text = "AG 2026: UVT $52.374. 4 UVT = $209.496."
    out = rewrite_year_constants(text)
    assert out.text == text
    assert out.rewrites == ()


def test_no_year_cue_no_rewrite():
    text = "La base es UVT $49.799 según la resolución."
    out = rewrite_year_constants(text)
    assert out.text == text
    assert out.rewrites == ()


def test_distant_amounts_not_rewritten():
    """Sanity: the ±20 % tolerance must NOT rewrite genuinely unrelated
    large amounts (e.g. patrimonio facts) that share digit shape."""
    text = "AG 2026: el patrimonio bruto fue de $18.000.000.000."
    out = rewrite_year_constants(text)
    assert out.text == text


@pytest.mark.parametrize("year", [2024, 2025, 2026])
def test_canonical_uvt_locked(year):
    from lia_graph.year_facts import get_year_facts
    facts = get_year_facts(year)
    assert facts is not None
    assert facts.uvt is not None
    assert facts.uvt.verified, f"UVT {year} must stay verified=true"
    assert int(facts.uvt.value_cop or 0) == CANONICAL[year], (
        f"UVT {year} canonical drifted: got {facts.uvt.value_cop}, "
        f"expected {CANONICAL[year]}"
    )


@pytest.mark.parametrize(
    "year,n,expected",
    [
        (2024, 4, 188_260),
        (2024, 27, 1_270_755),
        (2025, 4, 199_196),
        (2025, 27, 1_344_573),
        (2026, 4, 209_496),
        (2026, 27, 1_414_098),
    ],
)
def test_multi_uvt_locked(year, n, expected):
    from lia_graph.year_facts import multi_uvt
    actual = multi_uvt(n, year)
    assert actual == expected, (
        f"multi_uvt({n}, {year}) drifted: got {actual}, expected {expected}"
    )
