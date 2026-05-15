"""fix_v13_may §6 — tests for the práctica artifact-line filter.

The dedicated práctica retrieval lane (Phase 13B) is the first path to
expose certain corpus-build markers in chat answers: editorial source
markers, time stamps, section-heading numerals, truncated mid-thought
endings, dangling footnote-ref parens, and question-shaped bullets.

The 21-Q `21q_retriever_Practica` panel run on 2026-05-13 surfaced
these patterns concretely — every example below is lifted verbatim
from the run's failed-bullet bucket (see fix_v13_may §6).
"""

from __future__ import annotations

from dataclasses import dataclass

from lia_graph.pipeline_d.answer_synthesis_practica import (
    _candidate_lines_from_chunk,
    _is_practica_artifact_line,
    extend_from_practica_chunks,
)


@dataclass
class _StubChunk:
    chunk_text: str = ""
    doc_id: str = "doc_a"
    authority: str = "X"


# ---------------------------------------------------------------------------
# _is_practica_artifact_line — drop classes
# ---------------------------------------------------------------------------


def test_drops_editorial_consolidated_marker() -> None:
    line = "_Material editorial consolidado el 2026-04-15 desde `A-1_PATCH-seccion-09-art-105-realizacion-deducciones.md`._"
    assert _is_practica_artifact_line(line) is True


def test_drops_editorial_marker_case_insensitive() -> None:
    line = "MATERIAL EDITORIAL CONSOLIDADO al cierre"
    assert _is_practica_artifact_line(line) is True


def test_drops_time_stamp_hoy_es() -> None:
    assert _is_practica_artifact_line("Hoy es 23 de marzo. Las obligaciones más críticas.") is True


def test_drops_time_stamp_hoy_estamos() -> None:
    assert _is_practica_artifact_line("Hoy estamos a mitad de mes y conviene revisar.") is True


def test_drops_markdown_section_heading_numeric() -> None:
    assert _is_practica_artifact_line("### 11.8.1") is True
    assert _is_practica_artifact_line("## 6.9 Resumen ejecutivo") is True


def test_drops_question_shaped_bullet() -> None:
    assert _is_practica_artifact_line("¿Tuvo operaciones con vinculados en el año gravable?.") is True
    assert _is_practica_artifact_line("¿Por qué importa esto?") is True


def test_drops_truncation_tail_cuando() -> None:
    assert _is_practica_artifact_line("Un saldo a favor en IVA aparece cuando.") is True


def test_drops_truncation_tail_segun_truncated() -> None:
    assert _is_practica_artifact_line("Presentación y pago mensual de retenciones practicadas en mes anterior, según ú.") is True


def test_drops_truncation_tail_razones() -> None:
    assert _is_practica_artifact_line("La respuesta importa por dos razones.") is True


def test_drops_dangling_paren_numeral() -> None:
    assert _is_practica_artifact_line("El art. 260-5 ET divide la documentación comprobatoria en tres niveles (24).") is True
    assert _is_practica_artifact_line("Aplica el factor a la base (7).") is True


def test_drops_inline_markdown_heading_tail() -> None:
    # v15.1: leaked Checklist line from GMF-4x1000 panel where the
    # chunker joined a `## 27.1.` heading with the `### 27.1.1.` tail.
    line = "Checklist Pre-Cierre Fiscal — Antes del 31 de Diciembre ### 27.1.1."
    assert _is_practica_artifact_line(line) is True


def test_drops_inline_markdown_heading_no_trailing_period() -> None:
    line = "Algo introductorio relevante ### 4.2 Resumen operativo"
    assert _is_practica_artifact_line(line) is True


def test_drops_fragment_leader_de_diciembre() -> None:
    # v15.1: chunker ate the leading "15 " from "15 de diciembre 2025: …"
    line = "de diciembre 2025: PYME recibe factura de consultor por $2.000.000 (servicio ya prestado)."
    assert _is_practica_artifact_line(line) is True


def test_drops_fragment_leader_que_porque_donde() -> None:
    assert _is_practica_artifact_line("que el contribuyente conserve los soportes durante cinco años.") is True
    assert _is_practica_artifact_line("porque se causa en el momento de la enajenación.") is True
    assert _is_practica_artifact_line("donde se reconoce el ingreso en el período en que se devenga.") is True


def test_drops_empty_or_whitespace() -> None:
    assert _is_practica_artifact_line("") is True
    assert _is_practica_artifact_line("   ") is True


# ---------------------------------------------------------------------------
# _is_practica_artifact_line — keep classes
# ---------------------------------------------------------------------------


def test_keeps_normal_operational_bullet() -> None:
    line = "Liquida la retención del Art. 383 ET antes del día 15 de cada mes y guarda el certificado en el expediente del empleado."
    assert _is_practica_artifact_line(line) is False


def test_keeps_bullet_with_legitimate_paren_text() -> None:
    line = "Verifica el saldo a favor exigible (Art. 850 ET) antes de radicar la solicitud."
    assert _is_practica_artifact_line(line) is False


def test_keeps_bullet_ending_in_full_word_period() -> None:
    line = "Aplica el descuento al cierre del bimestre y soporta cada operación con su factura."
    assert _is_practica_artifact_line(line) is False


def test_keeps_bullet_with_question_inside_not_at_start() -> None:
    line = "Revisa si aplica la deducción, considera siempre el soporte documental."
    assert _is_practica_artifact_line(line) is False


# ---------------------------------------------------------------------------
# _candidate_lines_from_chunk — filters applied
# ---------------------------------------------------------------------------


def test_candidate_extraction_drops_artifact_bullets() -> None:
    chunk_text = (
        "- _Material editorial consolidado el 2026-04-15 desde `A-1_PATCH-x.md`._\n"
        "- Liquida la retención mensual antes del día 15 y guarda el certificado del banco.\n"
        "- ¿Tuvo operaciones con vinculados en el año gravable?\n"
        "- Aplica la tarifa marginal del Art. 908 ET sobre los ingresos brutos bimestrales del comercio.\n"
    )
    candidates = _candidate_lines_from_chunk(_StubChunk(chunk_text=chunk_text))
    joined = "\n".join(candidates).lower()
    assert "material editorial" not in joined
    assert "operaciones con vinculados" not in joined
    assert any("retención mensual" in c for c in candidates)
    assert any("tarifa marginal" in c for c in candidates)


def test_candidate_extraction_empty_chunk() -> None:
    assert _candidate_lines_from_chunk(_StubChunk(chunk_text="")) == ()


# ---------------------------------------------------------------------------
# extend_from_practica_chunks — end-to-end with artifacts in chunks
# ---------------------------------------------------------------------------


def test_extend_skips_artifact_lines_end_to_end() -> None:
    chunk_a = _StubChunk(
        chunk_text=(
            "- _Material editorial consolidado el 2026-04-15 desde `X.md`._\n"
            "- Liquida la retención antes del 15 del mes y archiva el certificado bancario.\n"
        ),
        doc_id="doc_a",
    )
    chunk_b = _StubChunk(
        chunk_text=(
            "- ¿Tuvo operaciones con vinculados en el año gravable?\n"
            "- Presenta el Informe Local antes del vencimiento del Form. 120 ante la DIAN.\n"
        ),
        doc_id="doc_b",
    )
    bucket: list[str] = []
    extend_from_practica_chunks(bucket, (chunk_a, chunk_b))
    joined = "\n".join(bucket).lower()
    assert "material editorial" not in joined
    assert "operaciones con vinculados en el año gravable" not in joined
    assert any("retención" in line for line in bucket)
    assert any("informe local" in line.lower() for line in bucket)


def test_extend_empty_chunks_no_crash() -> None:
    bucket: list[str] = []
    extend_from_practica_chunks(bucket, ())
    assert bucket == []


def test_extend_respects_explicit_per_chunk_cap() -> None:
    chunk = _StubChunk(
        chunk_text=(
            "- Primera línea operativa concreta del cierre fiscal antes del vencimiento mensual.\n"
            "- Segunda línea con detalle del paso siguiente del procedimiento operativo del cliente.\n"
            "- Tercera línea con el soporte documental que se debe archivar siempre por seis años.\n"
        ),
        doc_id="doc_a",
    )
    bucket: list[str] = []
    extend_from_practica_chunks(bucket, (chunk,), max_bullets_per_chunk=1)
    assert len(bucket) == 1


def test_extend_default_lets_chunk_emit_multiple_bullets() -> None:
    chunk = _StubChunk(
        chunk_text=(
            "- Primera línea operativa concreta del cierre fiscal antes del vencimiento mensual.\n"
            "- Segunda línea con detalle del paso siguiente del procedimiento operativo del cliente.\n"
            "- Tercera línea con el soporte documental que se debe archivar siempre por seis años.\n"
        ),
        doc_id="doc_a",
    )
    bucket: list[str] = []
    extend_from_practica_chunks(bucket, (chunk,))
    # v15.1: default per-chunk cap raised from 1 → 6; this chunk emits 3.
    assert len(bucket) == 3
