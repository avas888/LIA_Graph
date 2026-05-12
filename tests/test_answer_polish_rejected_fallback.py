"""Contract tests for the substantive polish-rejected fallback
(fix_v8 §3a).

Five invariants:

1. Empty ``GraphNativeAnswerParts`` → returns ``template_answer``
   unchanged (safety net: never make the answer worse than today).
2. Populated ``recommendations`` → fallback contains a "Recomendaciones Prácticas"
   section with bullets from recommendations.
3. Populated ``precautions`` → fallback contains "Riesgos y condiciones".
4. Populated ``paperwork`` → fallback contains "Soportes clave".
5. Composer never invokes an LLM — the test imports the module and
   doesn't need any network/adapter shim.
"""

from __future__ import annotations

from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d.answer_polish_rejected_fallback import (
    compose_polish_rejected_fallback,
    fallback_enabled,
)
from lia_graph.pipeline_d.answer_synthesis import GraphNativeAnswerParts


_TEMPLATE = "**Respuestas directas**\n- **¿Qué requisitos exige el Art. 107 ET?**\n"


def _req() -> PipelineCRequest:
    return PipelineCRequest(
        message="¿Qué requisitos exige el Art. 107 ET para deducir un gasto?",
        topic="costos_deducciones_renta",
        requested_topic="costos_deducciones_renta",
    )


def test_empty_parts_returns_template_unchanged() -> None:
    parts = GraphNativeAnswerParts()
    out = compose_polish_rejected_fallback(
        request=_req(),
        template_answer=_TEMPLATE,
        answer_parts=parts,
    )
    assert out == _TEMPLATE


def test_recommendations_render_as_recomendaciones_practicas() -> None:
    parts = GraphNativeAnswerParts(
        recommendations=(
            "Verifica necesidad y causalidad del gasto (art. 107 ET).",
            "Conserva el soporte documental (art. 771-2 ET).",
        ),
    )
    out = compose_polish_rejected_fallback(
        request=_req(),
        template_answer=_TEMPLATE,
        answer_parts=parts,
    )
    assert "Recomendaciones Prácticas" in out
    assert "necesidad y causalidad" in out
    assert "soporte documental" in out


def test_procedure_renders_when_recommendations_empty() -> None:
    parts = GraphNativeAnswerParts(
        procedure=(
            "Documenta el vínculo del gasto con la actividad generadora.",
            "Cuantifica proporcionalidad respecto del ingreso del periodo.",
        ),
    )
    out = compose_polish_rejected_fallback(
        request=_req(),
        template_answer=_TEMPLATE,
        answer_parts=parts,
    )
    assert "Procedimiento sugerido" in out
    assert "vínculo del gasto" in out


def test_precautions_render_as_riesgos() -> None:
    parts = GraphNativeAnswerParts(
        recommendations=("Verifica el soporte.",),
        precautions=(
            "Un gasto sin causalidad probada se rechaza en revisión DIAN.",
        ),
    )
    out = compose_polish_rejected_fallback(
        request=_req(),
        template_answer=_TEMPLATE,
        answer_parts=parts,
    )
    assert "Riesgos y condiciones" in out
    assert "causalidad probada" in out


def test_paperwork_renders_as_soportes() -> None:
    parts = GraphNativeAnswerParts(
        recommendations=("Verifica el soporte.",),
        paperwork=(
            "Factura electrónica con NIT del proveedor.",
            "Contrato o cotización firmada.",
        ),
    )
    out = compose_polish_rejected_fallback(
        request=_req(),
        template_answer=_TEMPLATE,
        answer_parts=parts,
    )
    assert "Soportes clave" in out
    assert "Factura electrónica" in out


def test_legal_anchor_renders_as_anclaje_legal() -> None:
    parts = GraphNativeAnswerParts(
        recommendations=("Lo primero, valida la deducibilidad.",),
        legal_anchor=("Art. 107 ET — requisitos generales de deducción.",),
    )
    out = compose_polish_rejected_fallback(
        request=_req(),
        template_answer=_TEMPLATE,
        answer_parts=parts,
    )
    assert "Anclaje legal" in out
    assert "Art. 107 ET" in out


def test_fallback_preserves_template_question_echo_header() -> None:
    parts = GraphNativeAnswerParts(
        recommendations=("Valida la deducibilidad antes de cerrar el periodo.",),
    )
    out = compose_polish_rejected_fallback(
        request=_req(),
        template_answer=_TEMPLATE,
        answer_parts=parts,
    )
    # The original question-echo header must remain at the top of the
    # fallback so the visible structure matches the polish-success path.
    assert out.startswith("**Respuestas directas**")


def test_fallback_grows_template_substantively() -> None:
    """The fallback's whole point: when polish rejects, the user sees
    substantially more content than the bare template echo."""
    parts = GraphNativeAnswerParts(
        recommendations=(
            "Verifica necesidad, causalidad y proporcionalidad del gasto (art. 107 ET).",
            "Documenta la relación con la actividad generadora de renta.",
            "Conserva los soportes que prueben la operación (art. 771-2 ET).",
        ),
        precautions=(
            "Sin causalidad probada el gasto se rechaza en revisión.",
            "Soportes posteriores al cierre pierden valor probatorio.",
        ),
        paperwork=(
            "Factura electrónica con identificación del proveedor.",
            "Contrato o cotización firmada por las partes.",
        ),
    )
    out = compose_polish_rejected_fallback(
        request=_req(),
        template_answer=_TEMPLATE,
        answer_parts=parts,
    )
    assert len(out) > len(_TEMPLATE) * 4


def test_fallback_enabled_default_on(monkeypatch) -> None:
    monkeypatch.delenv("LIA_POLISH_REJECTED_FALLBACK_MODE", raising=False)
    assert fallback_enabled() is True


def test_fallback_enabled_off_switch(monkeypatch) -> None:
    monkeypatch.setenv("LIA_POLISH_REJECTED_FALLBACK_MODE", "off")
    assert fallback_enabled() is False
