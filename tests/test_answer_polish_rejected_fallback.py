"""Contract tests for the substantive polish-rejected fallback
(fix_v8 §3a + fix_v14_may §6 A4).

Invariants:

1. Empty ``GraphNativeAnswerParts`` → returns ``template_answer``
   unchanged (safety net: never make the answer worse than today).
2. Populated ``recommendations`` → fallback contains a
   "Recomendaciones Prácticas" section with bullets.
3. Populated ``precautions`` → fallback contains "Riesgos y condiciones".
4. Populated ``paperwork`` → fallback contains "Soportes clave".
5. Composer never invokes an LLM — the test imports the module and
   doesn't need any network/adapter shim.
6. fix_v14_may §6 A4 — ``clean`` mode (default):
   * chunk-artifact bullets (A2 patterns) are dropped before render;
   * topic-allowlist mismatches (A1) are dropped before render;
   * sections whose surviving tuple is empty are omitted entirely
     (no headers without bodies);
   * if total substantive evidence chars < ``_MIN_EVIDENCE_CHARS``
     (300 post-§16 refine; was 500 at landing), the fallback returns
     the honest-abstention text instead
     of surfacing chunk fragments.
7. ``LIA_POLISH_REJECTED_FALLBACK_FILTER=legacy`` restores the
   pre-A4 (fix_v8 §3a) behavior verbatim — needed as a rollback path.

Tests 1-7 exercise rendering shape under ``legacy`` mode (their toy
fixtures were sized below the A4 evidence-chars threshold). The new
A4-specific cases run under the default ``clean`` mode and assert the
v14.2 filter behavior directly.
"""

from __future__ import annotations

import pytest

from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d.answer_polish_rejected_fallback import (
    _HONEST_ABSTENTION_TEXT,
    compose_polish_rejected_fallback,
    fallback_enabled,
    fallback_filter_mode,
)
from lia_graph.pipeline_d.answer_synthesis import GraphNativeAnswerParts


_TEMPLATE = "**Respuestas directas**\n- **¿Qué requisitos exige el Art. 107 ET?**\n"


def _req(topic: str = "costos_deducciones_renta") -> PipelineCRequest:
    return PipelineCRequest(
        message="¿Qué requisitos exige el Art. 107 ET para deducir un gasto?",
        topic=topic,
        requested_topic=topic,
    )


@pytest.fixture
def legacy_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the fix_v8 §3a render-everything behavior. Used for the
    pre-A4 shape tests whose toy fixtures fall below the new
    evidence-chars threshold by design."""
    monkeypatch.setenv("LIA_POLISH_REJECTED_FALLBACK_FILTER", "legacy")


# ---------------------------------------------------------------------------
# Shape tests (legacy mode — preserve pre-A4 contracts).
# ---------------------------------------------------------------------------


def test_empty_parts_returns_template_unchanged() -> None:
    parts = GraphNativeAnswerParts()
    out = compose_polish_rejected_fallback(
        request=_req(),
        template_answer=_TEMPLATE,
        answer_parts=parts,
    )
    assert out == _TEMPLATE


def test_recommendations_render_as_recomendaciones_practicas(legacy_mode: None) -> None:
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


def test_procedure_renders_when_recommendations_empty(legacy_mode: None) -> None:
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


def test_precautions_render_as_riesgos(legacy_mode: None) -> None:
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


def test_paperwork_renders_as_soportes(legacy_mode: None) -> None:
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


def test_legal_anchor_renders_as_anclaje_legal(legacy_mode: None) -> None:
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


def test_fallback_preserves_template_question_echo_header(legacy_mode: None) -> None:
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


def test_fallback_grows_template_substantively(legacy_mode: None) -> None:
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


def test_fallback_enabled_default_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LIA_POLISH_REJECTED_FALLBACK_MODE", raising=False)
    assert fallback_enabled() is True


def test_fallback_enabled_off_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_POLISH_REJECTED_FALLBACK_MODE", "off")
    assert fallback_enabled() is False


# ---------------------------------------------------------------------------
# fix_v14_may §6 A4 — clean-mode filter + honest-abstention threshold.
# ---------------------------------------------------------------------------


def test_filter_mode_default_clean(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LIA_POLISH_REJECTED_FALLBACK_FILTER", raising=False)
    assert fallback_filter_mode() == "clean"


def test_filter_mode_legacy_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_POLISH_REJECTED_FALLBACK_FILTER", "legacy")
    assert fallback_filter_mode() == "legacy"


def test_clean_mode_drops_chunk_artifact_bullets() -> None:
    """A4 — bullets matching A2 chunk-quality patterns must be dropped
    before render so the user never sees portal-login boilerplate or
    chunk captions in the polish-rejected fallback."""
    parts = GraphNativeAnswerParts(
        recommendations=(
            # Clean substantive bullets, must survive.
            "Verifica necesidad, causalidad y proporcionalidad del gasto frente a la actividad generadora de renta del contribuyente (art. 107 ET).",
            "Conserva los soportes documentales que prueben la operación durante todo el plazo de firmeza de la declaración (art. 771-2 ET).",
            "Asegura que los soportes coincidan en NIT, fecha, valor y descripción exactos con la operación facturada por el proveedor.",
            # Portal-login boilerplate leaked into a recommendation — must drop.
            "Inicie sesión con su número de cédula y contraseña para continuar.",
            # Caso de estudio chunk caption — must drop.
            "Caso de estudio: empresa PYME del sector comercio del año 2024.",
        ),
        paperwork=(
            "Factura electrónica con identificación completa del proveedor (NIT, razón social, dirección) y descripción precisa del bien o servicio.",
            "Contrato o cotización firmada por las partes que respalde el acuerdo comercial entre proveedor y contribuyente.",
            # Fragmento relevante caption — must drop.
            "Texto normativo clave — art. 107 ET (fragmento relevante).",
        ),
        precautions=(
            "Sin causalidad probada, el gasto se rechaza en revisión por la DIAN y genera mayor impuesto a cargo más sanción por inexactitud.",
            "Los soportes obtenidos después del cierre del periodo pierden valor probatorio frente a la administración tributaria.",
        ),
        legal_anchor=(
            "Art. 107 ET — requisitos generales de deducción del gasto en renta del contribuyente.",
            "Art. 771-2 ET — soportes documentales que prueban costos y deducciones declarados.",
        ),
    )
    out = compose_polish_rejected_fallback(
        request=_req(),
        template_answer=_TEMPLATE,
        answer_parts=parts,
    )
    # Dropped strings must NOT appear.
    assert "Inicie sesión" not in out
    assert "Caso de estudio" not in out
    assert "fragmento relevante" not in out
    # Clean bullets must survive.
    assert "necesidad, causalidad y proporcionalidad" in out
    assert "Factura electrónica" in out
    # Section headers present where bullets survived.
    assert "Recomendaciones Prácticas" in out
    assert "Soportes clave" in out
    assert "Anclaje legal" in out
    # Substantive path fired (not abstention).
    assert _HONEST_ABSTENTION_TEXT not in out


def test_clean_mode_emits_honest_abstention_below_threshold() -> None:
    """A4 — when the surviving evidence is less than
    ``_MIN_EVIDENCE_CHARS`` of substantive content, the fallback must
    return the honest-abstention text rather than surface chunk
    fragments. Two short clean bullets are well under the 300-char
    threshold."""
    parts = GraphNativeAnswerParts(
        recommendations=("Valida el gasto (art. 107 ET).",),
        precautions=("Sin causalidad se rechaza.",),
    )
    out = compose_polish_rejected_fallback(
        request=_req(),
        template_answer=_TEMPLATE,
        answer_parts=parts,
    )
    assert _HONEST_ABSTENTION_TEXT in out
    # Question-echo header must still be at the top so the surface
    # matches the polish-success path.
    assert out.startswith("**Respuestas directas**")
    # The substantive bullets must NOT be rendered when we abstained.
    assert "Recomendaciones Prácticas" not in out
    assert "Riesgos y condiciones" not in out


def test_clean_mode_mixed_dirty_and_clean_keeps_clean_surface() -> None:
    """A4 — when the evidence is a MIX of clean substantive bullets and
    chunk artifacts, the fallback must render the clean side and drop
    the artifacts. Total surviving evidence exceeds the 300-char
    threshold so the substantive (non-abstention) path fires."""
    parts = GraphNativeAnswerParts(
        recommendations=(
            "Documenta la necesidad, causalidad y proporcionalidad del gasto frente a la actividad generadora de renta (art. 107 ET).",
            "Conserva los soportes documentales que prueben la operación durante el plazo de firmeza (art. 771-2 ET).",
            # Portal-login boilerplate — must drop, doesn't pollute the rest.
            "Inicie sesión con su cédula y contraseña en el portal DIAN para continuar.",
        ),
        procedure=(
            "Identifica el vínculo del gasto con la actividad generadora de renta del contribuyente.",
            "Cuantifica la proporcionalidad del gasto respecto del ingreso ordinario del periodo gravable.",
            "Reúne los soportes documentales — factura electrónica, contrato, comprobante de pago.",
        ),
        precautions=(
            "Un gasto sin necesidad, causalidad o proporcionalidad probada se rechaza en revisión por la DIAN.",
            "Los soportes que se obtienen después del cierre del periodo pierden valor probatorio frente a la administración.",
        ),
        legal_anchor=(
            "Art. 107 ET — requisitos generales de deducción del gasto en renta.",
            "Art. 771-2 ET — soportes documentales que prueban costos y deducciones.",
        ),
    )
    out = compose_polish_rejected_fallback(
        request=_req(),
        template_answer=_TEMPLATE,
        answer_parts=parts,
    )
    # Dropped artifact must NOT appear.
    assert "Inicie sesión" not in out
    # Honest-abstention path did NOT fire — substantive sections rendered.
    assert _HONEST_ABSTENTION_TEXT not in out
    assert "Recomendaciones Prácticas" in out
    assert "Riesgos y condiciones" in out
    assert "Anclaje legal" in out
    # Clean substantive content is present.
    assert "necesidad, causalidad" in out or "proporcionalidad del gasto" in out
    assert "valor probatorio" in out


def test_clean_mode_omits_empty_sections() -> None:
    """A4 — a section whose every bullet was dropped by the filter
    must NOT render its header. No empty ``**Procedimiento Sugerido**``
    blocks reach the user."""
    parts = GraphNativeAnswerParts(
        recommendations=(
            "Documenta la necesidad, causalidad y proporcionalidad del gasto frente a la actividad generadora de renta (art. 107 ET).",
            "Conserva los soportes documentales que prueben la operación durante el plazo de firmeza (art. 771-2 ET).",
            "Verifica que los soportes coincidan en NIT, fecha, valor y descripción con la operación facturada.",
        ),
        procedure=(
            # Every procedure bullet is a chunk artifact — section must be omitted.
            "Inicie sesión con su número de cédula y contraseña en el portal DIAN.",
            "Caso de estudio: contribuyente PYME del año gravable 2024.",
            "Texto normativo clave — art. 107 ET (fragmento relevante).",
        ),
        paperwork=(
            "Factura electrónica con identificación completa del proveedor y descripción del bien o servicio.",
            "Contrato o cotización firmada por las partes que respalde el acuerdo comercial.",
            "Comprobante de pago bancario que evidencie la transferencia de recursos.",
        ),
        precautions=(
            "Un gasto sin necesidad, causalidad o proporcionalidad probada se rechaza en revisión DIAN.",
        ),
    )
    out = compose_polish_rejected_fallback(
        request=_req(),
        template_answer=_TEMPLATE,
        answer_parts=parts,
    )
    # All procedure bullets were artifacts — section must NOT render.
    assert "Procedimiento sugerido" not in out
    assert "Inicie sesión" not in out
    assert "Caso de estudio" not in out
    # Clean sections must render.
    assert "Recomendaciones Prácticas" in out
    assert "Soportes clave" in out
    assert "Riesgos y condiciones" in out


def test_legacy_mode_renders_dirty_bullets_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A4 rollback — ``legacy`` mode must reproduce the fix_v8 §3a
    behavior verbatim: every bullet renders, including chunk artifacts.
    This is the rollback path; we keep it tested so an incident
    rollback is a one-flag flip, not a code change."""
    monkeypatch.setenv("LIA_POLISH_REJECTED_FALLBACK_FILTER", "legacy")
    parts = GraphNativeAnswerParts(
        recommendations=(
            "Valida el gasto (art. 107 ET).",
            # Artifact that A4 would drop in clean mode.
            "Inicie sesión con su número de cédula y contraseña.",
        ),
    )
    out = compose_polish_rejected_fallback(
        request=_req(),
        template_answer=_TEMPLATE,
        answer_parts=parts,
    )
    # Legacy mode renders both bullets — no filter, no abstention.
    assert "Valida el gasto" in out
    assert "Inicie sesión" in out
    assert _HONEST_ABSTENTION_TEXT not in out


# ---------------------------------------------------------------------------
# v15.1 (2026-05-14) — first-bubble template dedupe.
# ---------------------------------------------------------------------------


_FIRST_BUBBLE_TEMPLATE = (
    "**Respuestas directas**\n"
    "- **¿Cuál es el tratamiento fiscal del GMF (4×1000)?**\n"
    "  - Bullet uno con contenido sustantivo de la primera sub-pregunta.\n"
    "\n"
    "**Recomendaciones Prácticas**\n"
    "1. Débito: 530505 — Gravamen a los movimientos financieros (arts. 870 y 872 ET).\n"
    "\n"
    "**Riesgos y condiciones**\n"
    "- No dupliques el mismo valor como descuento tributario y gasto deducible (arts. 870 y 871 ET).\n"
    "\n"
    "**Anclaje legal**\n"
    "- Art. 870 — Gravamen a los movimientos financieros, GMF\n"
    "- Art. 871 — Hecho generador del GMF\n"
    "- Art. 872 — Tarifa del gravamen a los movimientos financieros\n"
)


def test_skips_recomendaciones_when_template_already_has_it() -> None:
    # The first-bubble path emits a complete answer as the polish
    # template. When polish is rejected on that template, naive
    # appending duplicates every section. v15.1 skips appends whose
    # heading already exists in the template.
    parts = GraphNativeAnswerParts(
        recommendations=(
            "Verifica el soporte bancario del GMF antes de incluir la deducción.",
            "Aplica el 50% del gravamen pagado al renglón de deducciones, no como descuento.",
        ),
        precautions=(
            "El art. 115 ET limita la deducción al 50% del GMF efectivamente pagado.",
        ),
        legal_anchor=(
            "Art. 115 — Deducción de impuestos pagados",
        ),
    )
    out = compose_polish_rejected_fallback(
        request=_req(),
        template_answer=_FIRST_BUBBLE_TEMPLATE,
        answer_parts=parts,
    )
    # Each section heading appears exactly once.
    assert out.count("**Recomendaciones Prácticas**") == 1
    assert out.count("**Riesgos y condiciones**") == 1
    assert out.count("**Anclaje legal**") == 1
    # And the template's original Recomendaciones content survived.
    assert "Débito: 530505" in out


def test_returns_template_when_every_section_duplicated() -> None:
    # All three populated sections already exist in the template —
    # nothing left to append. The fallback should return the template
    # unchanged rather than dropping to honest-abstention (the template
    # IS the substantive answer in this case).
    parts = GraphNativeAnswerParts(
        recommendations=("Verifica el soporte bancario del GMF.",),
        precautions=("Limita la deducción al 50% del GMF.",),
        legal_anchor=("Art. 115 — Deducción de impuestos pagados",),
    )
    out = compose_polish_rejected_fallback(
        request=_req(),
        template_answer=_FIRST_BUBBLE_TEMPLATE,
        answer_parts=parts,
    )
    # Template (stripped) flows through verbatim — fallback didn't
    # append anything because every section it would have rendered is
    # already in the template.
    assert out == _FIRST_BUBBLE_TEMPLATE.strip()
    assert _HONEST_ABSTENTION_TEXT not in out
    assert out.count("**Recomendaciones Prácticas**") == 1
    assert out.count("**Riesgos y condiciones**") == 1
    assert out.count("**Anclaje legal**") == 1


def test_appends_sections_missing_from_template() -> None:
    # `Soportes clave` is NOT in the first-bubble template; only the
    # other four sections are. The fallback should still append Soportes
    # even though the others get deduped.
    parts = GraphNativeAnswerParts(
        recommendations=("Ya está en plantilla, debe omitirse.",),
        paperwork=(
            "Conserva el extracto bancario que demuestre el pago efectivo del GMF.",
            "Archiva el certificado de retención emitido por la entidad bancaria.",
        ),
    )
    out = compose_polish_rejected_fallback(
        request=_req(),
        template_answer=_FIRST_BUBBLE_TEMPLATE,
        answer_parts=parts,
    )
    assert out.count("**Recomendaciones Prácticas**") == 1
    assert "**Soportes clave**" in out
    assert "extracto bancario" in out
