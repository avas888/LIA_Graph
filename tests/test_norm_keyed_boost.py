"""fix_v25_may.md §3.1 — Phase 1 / G8: norm-keyed retrieval boost tests."""

from __future__ import annotations

import pytest

from lia_graph.pipeline_d.norm_keyed_boost import (
    NormRef,
    boost_chunks_by_norm_id,
    extract_named_norms,
    norm_keyed_directive,
)


def test_extracts_res_dian_167_2021():
    refs = extract_named_norms(
        "Qué dice la Resolución DIAN 000167 de 2021 sobre documento soporte"
    )
    assert any(r.kind == "res_dian" and r.number == "167" and r.year == 2021 for r in refs)


def test_extracts_res_dian_short_form():
    refs = extract_named_norms("Res. DIAN 233/2025")
    assert any(r.kind == "res_dian" and r.number == "233" and r.year == 2025 for r in refs)


def test_extracts_decreto_and_acuerdo():
    refs = extract_named_norms(
        "Aplican el Acuerdo 65 de 2002 y el Decreto Distrital 352 de 2002 en Bogotá"
    )
    assert any(r.kind == "acuerdo" and r.number == "65" and r.year == 2002 for r in refs)
    assert any(r.kind == "decreto" and r.number == "352" and r.year == 2002 for r in refs)


def test_extracts_multiple_resoluciones_in_one_question():
    refs = extract_named_norms(
        "Cita Resolución 164 de 2021 y Resolución 165 de 2023"
    )
    numbers = {r.number for r in refs if r.kind == "res_dian"}
    assert {"164", "165"} <= numbers


def test_no_false_positive_on_bare_number():
    refs = extract_named_norms("el cliente facturó $167,000 en el AG 2021")
    assert not refs


def test_directive_lists_named_norms():
    refs = [NormRef(kind="res_dian", number="167", year=2021, raw="Resolución DIAN 000167 de 2021")]
    block = norm_keyed_directive(refs)
    assert "Resolución DIAN 167 de 2021" in block
    assert "Anclaje Legal" in block


def test_directive_empty_when_no_refs():
    assert norm_keyed_directive([]) == ""


def test_norm_id_matcher_matches_zero_padded_slug():
    ref = NormRef(kind="res_dian", number="167", year=2021, raw="")
    assert ref.matches_norm_id("res_dian.0167.2021")
    assert ref.matches_norm_id("res_dian.167.2021")
    assert ref.matches_norm_id("resolucion_dian.0167.2021")


def test_norm_id_matcher_rejects_wrong_year():
    ref = NormRef(kind="res_dian", number="167", year=2021, raw="")
    assert not ref.matches_norm_id("res_dian.0167.2024")


def test_boost_promotes_matching_chunk():
    refs = [NormRef(kind="res_dian", number="167", year=2021, raw="")]
    chunks = [
        {"id": "a", "norm_id": "et.art.771-2", "score": 0.9},
        {"id": "b", "norm_id": "res_dian.0167.2021", "score": 0.5},
        {"id": "c", "norm_id": "et.art.617", "score": 0.4},
    ]
    out = boost_chunks_by_norm_id(chunks, refs, factor=2.0)
    assert out[0]["id"] == "b", "boosted Res. DIAN chunk must rank first after 2.0x boost"
    assert out[0]["score"] == pytest.approx(1.0)


def test_boost_noop_on_empty_refs():
    chunks = [{"id": "a", "norm_id": "et.art.392", "score": 0.7}]
    assert boost_chunks_by_norm_id(chunks, [], factor=1.5) == chunks
