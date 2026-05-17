"""fix_v25_may.md §3.6 — Phase 6 / G13 tests."""

from __future__ import annotations

import pytest

from lia_graph.year_facts import (
    build_deadline_directive,
    clear_cache,
    get_deadlines_for_topic,
    multi_uvt,
)


@pytest.fixture(autouse=True)
def _flush_cache():
    clear_cache()
    yield
    clear_cache()


def test_rte_annual_deadline_is_march_31():
    facts = get_deadlines_for_topic("regimen_tributario_especial_esal")
    labels = [f.deadline_label for f in facts]
    assert any("31 de marzo" in label for label in labels)


def test_no_deadlines_for_unrelated_topic():
    assert get_deadlines_for_topic("ica") == []


def test_build_deadline_directive_for_rte_topic():
    block = build_deadline_directive("rte")
    assert block is not None
    assert "31 de marzo" in block
    assert "PLAZOS CANÓNICOS" in block


def test_build_deadline_directive_none_for_topicless():
    assert build_deadline_directive(None) is None


def test_multi_uvt_4_2026_is_209_496():
    assert multi_uvt(4, 2026) == 209_496


def test_multi_uvt_27_2026_is_1_414_098():
    assert multi_uvt(27, 2026) == 1_414_098


def test_multi_uvt_fallback_when_not_precomputed():
    # 5 UVT 2026 not in helper table — fallback to 5 * 52,374 = 261,870
    assert multi_uvt(5, 2026) == 5 * 52_374


def test_unverified_deadline_is_skipped():
    facts = get_deadlines_for_topic("informacion_exogena")
    # exogena window has verified=false in registry — must not surface.
    assert all(f.key != "exogena_ag_2025_window" for f in facts)
