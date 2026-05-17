"""fix_v25_may.md §3.7 — Phase 7 / G14 tests."""

from __future__ import annotations

from lia_graph.pipeline_d.user_numerics_capture import (
    extract_user_numerics,
    format_datos_del_caso,
)


def test_extracts_single_peso_amount():
    extract = extract_user_numerics(
        "Una empresa compra un computador portátil de $3.000.000 más IVA"
    )
    assert "$3.000.000" in " ".join(extract.amounts)


def test_extracts_multiple_amounts():
    extract = extract_user_numerics(
        "Patrimonio bruto $18.000 millones y operaciones $6.000 millones"
    )
    joined = " ".join(extract.amounts)
    assert "18.000" in joined and "6.000" in joined


def test_extracts_uvt_counts():
    extract = extract_user_numerics(
        "Regla de 92.000 UVT; el contribuyente alcanza 3.300 UVT al mes."
    )
    joined = " ".join(extract.uvt_counts)
    assert "92.000 UVT" in joined
    assert "3.300 UVT" in joined


def test_extracts_percentage():
    extract = extract_user_numerics("Aplica retención del 4% sobre el pago")
    assert "4%" in " ".join(extract.percentages)


def test_format_datos_del_caso_returns_block_when_amounts_present():
    extract = extract_user_numerics("La compra fue de $3.000.000")
    block = format_datos_del_caso(extract)
    assert "Datos del caso" in block
    assert "$3.000.000" in block


def test_format_empty_when_no_numerics():
    extract = extract_user_numerics("Cómo liquido la prima de servicios")
    assert format_datos_del_caso(extract) == ""


def test_dedupes_repeated_amounts():
    extract = extract_user_numerics(
        "El equipo de $3.000.000 — la base $3.000.000 — total $3.000.000"
    )
    assert len(extract.amounts) == 1


def test_long_block_truncated():
    msg = " ".join([f"${i:03d}.000.000" for i in range(1, 30)])
    extract = extract_user_numerics(msg)
    block = format_datos_del_caso(extract)
    assert len(block) <= 290  # header (~42) + capped body (~240) + slack
