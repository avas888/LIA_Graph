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

import os

import pytest

from lia_graph.pipeline_d.answer_synthesis_practica import (
    _candidate_lines_from_chunk,
    _is_practica_artifact_line,
    _is_practica_noise_line,
    _noise_filter_mode,
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


# ---------------------------------------------------------------------------
# fix_v18 b1 §1.1 Issue A — per-line noise filter
# ---------------------------------------------------------------------------


@pytest.fixture
def _noise_filter_off(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LIA_PRACTICA_NOISE_FILTER", "off")
    yield


@pytest.fixture
def _noise_filter_shadow(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LIA_PRACTICA_NOISE_FILTER", "shadow")
    yield


@pytest.fixture
def _noise_filter_enforce(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LIA_PRACTICA_NOISE_FILTER", "enforce")
    yield


def test_noise_filter_mode_default_is_shadow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LIA_PRACTICA_NOISE_FILTER", raising=False)
    assert _noise_filter_mode() == "shadow"


def test_noise_filter_mode_legacy_alias_is_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_PRACTICA_NOISE_FILTER", "legacy")
    assert _noise_filter_mode() == "off"


def test_noise_filter_drops_pre_ley_antes_lead() -> None:
    # §4.1 fixture bullet 5 (verbatim).
    is_noise, reason = _is_practica_noise_line(
        "Antes: 30 días × ($2.200.000 ÷ 30) = $2.200.000."
    )
    assert is_noise is True
    assert reason == "pre_ley_lead"


def test_noise_filter_drops_anteriormente_lead() -> None:
    is_noise, reason = _is_practica_noise_line(
        "Anteriormente, la indemnización se liquidaba a 45 días."
    )
    assert is_noise is True
    assert reason == "pre_ley_lead"


def test_noise_filter_drops_software_code_tail_55() -> None:
    # §4.1 fixture bullet 1.
    is_noise, reason = _is_practica_noise_line(
        "Despido sin justa causa (terminación unilateral del empleador): código 55."
    )
    assert is_noise is True
    assert reason == "software_code_tail"


def test_noise_filter_drops_software_code_tail_56() -> None:
    # §4.1 fixture bullet 2.
    is_noise, reason = _is_practica_noise_line(
        "Despido con justa causa (incumplimiento del trabajador): código 56."
    )
    assert is_noise is True
    assert reason == "software_code_tail"


def test_noise_filter_drops_orphan_numeric_calc() -> None:
    is_noise, reason = _is_practica_noise_line(
        "30 días × ($2.200.000 ÷ 30) = $2.200.000."
    )
    assert is_noise is True
    assert reason == "orphan_numeric_calc"


def test_noise_filter_preserves_legitimate_spec_bullet() -> None:
    # SPEC bullet from liquidacion_terminacion — must NOT fire as noise.
    spec_bullet = (
        "**Indemnización moratoria — CST art. 65:** durante los primeros "
        "24 meses después del retiro = 1 día de salario por cada día de "
        "mora. A partir del mes 25 = intereses moratorios."
    )
    is_noise, reason = _is_practica_noise_line(spec_bullet)
    assert is_noise is False
    assert reason is None


def test_noise_filter_preserves_calc_inside_operational_context() -> None:
    # A calc embedded in a long operational bullet is NOT noise.
    operational = (
        "Para liquidar la indemnización por años posteriores al primero, "
        "aplica la fórmula del CST art. 64: 20 días × $133.333 = $2.666.660 "
        "por cada año adicional al primero, según la tabla del numeral 2."
    )
    is_noise, reason = _is_practica_noise_line(operational)
    # Long line should not trigger orphan-calc (> 160 chars).
    assert is_noise is False
    assert reason is None


def test_noise_filter_preserves_descuento_25pct_bullet() -> None:
    # Donaciones SPEC bullet uses "25 %" and "Antes:..." would be wrong
    # match — make sure clean phrasing does not regress.
    clean = (
        "Tratamiento general — descuento art. 257 ET: 25 % del valor "
        "donado contra el impuesto sobre la renta."
    )
    is_noise, reason = _is_practica_noise_line(clean)
    assert is_noise is False
    assert reason is None


def test_extend_enforce_drops_noise_bullets(
    _noise_filter_enforce, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Simulate the §4.1 captured chunk: noise interleaved with SPEC.
    chunk = _StubChunk(
        chunk_text=(
            "- Despido sin justa causa (terminación unilateral): código 55.\n"
            "- Despido con justa causa (incumplimiento): código 56.\n"
            "- Antes: 30 días × ($2.200.000 ÷ 30) = $2.200.000.\n"
            "- En terminación sin justa causa, año 1: el empleador "
            "debe pagar 30 días de salario adicionales a las "
            "prestaciones sociales liquidadas al corte.\n"
            "- Conserva los soportes de pago bancarizado y el "
            "paz y salvo firmado por el trabajador durante 10 años.\n"
        ),
        doc_id="doc_terminacion",
    )
    bucket: list[str] = []
    extend_from_practica_chunks(bucket, (chunk,))
    joined = "\n".join(bucket).lower()
    # Noise dropped.
    assert "código 55" not in joined
    assert "código 56" not in joined
    assert not any(line.lstrip().lower().startswith("antes:") for line in bucket)
    # SPEC content preserved.
    assert "30 días de salario adicionales" in joined
    assert "paz y salvo" in joined


def test_extend_shadow_does_not_drop_anything(
    _noise_filter_shadow, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Same chunk as above — under shadow, output is identical to off
    # (bullets surface, telemetry logs separately).
    chunk = _StubChunk(
        chunk_text=(
            "- Despido sin justa causa: código 55.\n"
            "- En terminación sin justa causa, año 1: el empleador "
            "debe pagar 30 días de salario adicionales a las "
            "prestaciones sociales liquidadas al corte.\n"
        ),
        doc_id="doc_terminacion",
    )
    bucket: list[str] = []
    extend_from_practica_chunks(bucket, (chunk,))
    joined = "\n".join(bucket).lower()
    # Shadow mode: noise still appears in output.
    assert "código 55" in joined
    assert "30 días de salario adicionales" in joined


def test_extend_off_mode_emits_everything(
    _noise_filter_off, monkeypatch: pytest.MonkeyPatch
) -> None:
    chunk = _StubChunk(
        chunk_text=(
            "- Despido sin justa causa: código 55.\n"
            "- Antes: 30 días × ($2.200.000 ÷ 30) = $2.200.000.\n"
            "- En terminación sin justa causa, año 1: el empleador "
            "paga 30 días de salario adicionales a las prestaciones.\n"
        ),
        doc_id="doc_terminacion",
    )
    bucket: list[str] = []
    extend_from_practica_chunks(bucket, (chunk,))
    joined = "\n".join(bucket).lower()
    assert "código 55" in joined
    assert "antes:" in joined
    assert "30 días de salario adicionales" in joined
