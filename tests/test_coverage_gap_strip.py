"""fix_v25_may.md §3.5 P5-T3 — coverage-gap stub stripper tests."""

from __future__ import annotations

from lia_graph.pipeline_d.coverage_gap_strip import strip_coverage_gap_lines


def test_strips_cobertura_pendiente_bullet():
    text = (
        "**Respuestas directas**\n"
        "- Explica la regla de 92.000 UVT?\n"
        "  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.\n"
    )
    out, drops = strip_coverage_gap_lines(text)
    assert "Cobertura pendiente" not in out
    assert "valida el expediente" not in out
    assert "[brecha de evidencia]" in out
    assert len(drops) == 1


def test_strips_no_encuentro_evidencia_bullet():
    text = "- No encuentro evidencia para esta sub-pregunta\n"
    out, _ = strip_coverage_gap_lines(text)
    assert "No encuentro" not in out
    assert "[brecha de evidencia]" in out


def test_preserves_substantive_bullets():
    text = (
        "- IVA bimestral si ingresos prior-year > 92,000 UVT (art. 600 ET).\n"
        "- Cuatrimestral en caso contrario.\n"
    )
    out, drops = strip_coverage_gap_lines(text)
    assert out.strip() == text.strip()
    assert drops == []


def test_preserves_question_header_with_brecha_under_it():
    """The sub-question header above the stub stays — so the user knows
    which sub-question wasn't covered — and the stub becomes the compact
    [brecha de evidencia] notice."""
    text = (
        "- **Explica la regla de 92.000 UVT, casos de inicio de actividades y base legal?**\n"
        "  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.\n"
    )
    out, _ = strip_coverage_gap_lines(text)
    assert "Explica la regla de 92.000 UVT" in out
    assert "[brecha de evidencia]" in out
    assert "Cobertura pendiente" not in out


def test_drops_plain_prose_stub():
    """A stub that's not formatted as a bullet should be dropped entirely
    (no [brecha de evidencia] replacement — that's bullet-scoped)."""
    text = "Cobertura pendiente; el contador debe consultar la fuente."
    out, drops = strip_coverage_gap_lines(text)
    assert out == ""
    assert len(drops) == 1
