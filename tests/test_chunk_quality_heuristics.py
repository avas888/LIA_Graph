"""fix_v14_may §4 (A2) — tests for the unified chunk-quality heuristics.

Catalog covers the off-topic chunk-text leak patterns observed in 10+
turns of the 2026-05-13 panel-judge:

* portal-login boilerplate ("Inicie sesión con su número de cédula y
  contraseña")
* cross-topic operational fragments ("Matrícula Mercantil", "Jornada
  nocturna 35%") leaking outside their natural topic
* chunk captions ("Texto normativo clave —", "(fragmento relevante)",
  "Caso de estudio:")
* section-numeral headings as dominant content
* question-dominant pure-interrogative text

Plus false-positive guards: legit bullets that contain a trigger token
but in the proper operational context must pass.
"""

from __future__ import annotations

import pytest

from lia_graph.pipeline_d.chunk_quality_heuristics import (
    apply_heuristics,
    heuristic_mode,
    score_chunk_quality,
    PENALTY_HEAVY,
    PENALTY_MEDIUM,
    PENALTY_LIGHT,
)


# ---------------------------------------------------------------------------
# Mode resolution
# ---------------------------------------------------------------------------


def test_default_mode_is_shadow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LIA_CHUNK_QUALITY_HEURISTIC_MODE", raising=False)
    assert heuristic_mode() == "shadow"


def test_enforce_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_CHUNK_QUALITY_HEURISTIC_MODE", "enforce")
    assert heuristic_mode() == "enforce"


def test_off_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_CHUNK_QUALITY_HEURISTIC_MODE", "off")
    assert heuristic_mode() == "off"


def test_unknown_mode_defaults_shadow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_CHUNK_QUALITY_HEURISTIC_MODE", "potato")
    assert heuristic_mode() == "shadow"


# ---------------------------------------------------------------------------
# Pattern: portal-login boilerplate (verbatim panel-leak)
# ---------------------------------------------------------------------------


def test_drops_portal_login_with_cedula() -> None:
    """Panel cases Práctica Q10 GMF, Práctica Q16 PT, G12 PT, G19
    autorretención: 'Inicie sesión con su número de cédula y contraseña...'
    """
    row = {
        "chunk_text": "Inicie sesión con su número de cédula y contraseña asociada a su registro. Si olvidó la contraseña, use la opción Recuperar contraseña en el portal.",
        "rrf_score": 0.8,
    }
    penalty, reason = score_chunk_quality(row)
    assert penalty == PENALTY_HEAVY
    assert reason == "portal_login_boilerplate"


def test_drops_portal_login_lowercase_variant() -> None:
    row = {
        "chunk_text": "para acceder, inicie sesion con su cedula y contrasena",
        "rrf_score": 0.5,
    }
    penalty, reason = score_chunk_quality(row)
    assert penalty == PENALTY_HEAVY
    assert reason == "portal_login_boilerplate"


# ---------------------------------------------------------------------------
# Pattern: chunk captions
# ---------------------------------------------------------------------------


def test_drops_texto_normativo_clave_caption() -> None:
    """Panel case G18 TTD par. 6: 'Texto normativo clave — par. 6,
    art. 240 ET (fragmento relevante)' surfaced as guidance."""
    row = {
        "chunk_text": "Texto normativo clave — par. 6, art. 240 ET (fragmento relevante)",
        "rrf_score": 0.7,
    }
    penalty, reason = score_chunk_quality(row)
    assert penalty == PENALTY_HEAVY
    assert reason == "normative_key_caption"


def test_drops_fragmento_relevante_caption() -> None:
    row = {
        "chunk_text": "Artículo 240 ET (fragmento relevante)",
        "rrf_score": 0.6,
    }
    penalty, reason = score_chunk_quality(row)
    assert penalty == PENALTY_HEAVY
    assert reason == "fragmento_relevante_caption"


def test_drops_case_study_caption() -> None:
    """Panel cases G18 TTD, Práctica Q9 firmeza: 'Caso de estudio:
    Tienda de abarrotes, ventas $180M anuales, Bogotá'."""
    row = {
        "chunk_text": "Caso de estudio: Tienda de abarrotes, ventas $180M anuales, Bogotá",
        "rrf_score": 0.5,
    }
    penalty, reason = score_chunk_quality(row)
    assert penalty == PENALTY_HEAVY
    assert reason == "case_study_caption"


# ---------------------------------------------------------------------------
# Pattern: cross-topic operational leaks
# ---------------------------------------------------------------------------


def test_drops_matricula_mercantil_outside_comercial_societario() -> None:
    """Panel cases Práctica Q1 calendario, Práctica Q19 retención F.350:
    'Matrícula Mercantil (Renovación) — Vence: 31 de marzo' bleeds into
    calendario / retención when it should be comercial_societario."""
    row = {
        "chunk_text": "Matrícula Mercantil (Renovación) — Vence: 31 de marzo. Renueve antes del cierre del primer trimestre.",
        "rrf_score": 0.5,
    }
    # Routed to retencion_fuente_general — Matrícula Mercantil leaks here.
    penalty, reason = score_chunk_quality(row, routed_topic="retencion_fuente_general")
    assert penalty == PENALTY_MEDIUM
    assert reason == "cross_topic_operational_leak"


def test_keeps_matricula_mercantil_inside_comercial_societario() -> None:
    """Same content in its natural topic must NOT be penalized."""
    row = {
        "chunk_text": "Matrícula Mercantil (Renovación) — Vence: 31 de marzo según calendario.",
        "rrf_score": 0.5,
    }
    penalty, reason = score_chunk_quality(row, routed_topic="comercial_societario")
    assert penalty == 1.0
    assert reason is None


def test_drops_jornada_nocturna_recargo_outside_laboral() -> None:
    """Panel cases Práctica Q14 PILA, Práctica Q20 tabla 383, G9 UGPP:
    jornada nocturna 7:00 p.m. 35% recargo leaks into PILA, retención
    tables, UGPP desalarización."""
    row = {
        "chunk_text": "La jornada nocturna comienza a las 7:00 p.m. y se extiende hasta las 6:00 a.m. Todo trabajo en este horario genera un recargo del 35% sobre el salario ordinario.",
        "rrf_score": 0.6,
    }
    # Routed to retencion_fuente_general — Jornada nocturna leaks here.
    penalty, reason = score_chunk_quality(row, routed_topic="retencion_fuente_general")
    assert penalty == PENALTY_MEDIUM
    assert reason == "cross_topic_operational_leak"


def test_keeps_jornada_nocturna_inside_laboral() -> None:
    row = {
        "chunk_text": "La jornada nocturna comienza a las 7:00 p.m. y se extiende hasta las 6:00 a.m. Todo trabajo en este horario genera un recargo del 35% sobre el salario ordinario.",
        "rrf_score": 0.6,
    }
    for topic in ("laboral", "reforma_laboral_ley_2466", "parafiscales_seguridad_social"):
        penalty, reason = score_chunk_quality(row, routed_topic=topic)
        assert penalty == 1.0, f"laboral-adjacent topic {topic!r} should NOT penalize"
        assert reason is None


# ---------------------------------------------------------------------------
# Pattern: section-heading numerals as dominant content
# ---------------------------------------------------------------------------


def test_drops_section_heading_dominant_chunk() -> None:
    """Panel case G14 conciliación 2516: '### 11.8.1' as bullet."""
    row = {
        "chunk_text": "### 11.8.1\n### 11.8.2\n### 11.8.3",
        "rrf_score": 0.4,
    }
    penalty, reason = score_chunk_quality(row)
    assert penalty == PENALTY_LIGHT
    assert reason == "section_heading_dominant"


# ---------------------------------------------------------------------------
# Pattern: question-dominant chunk
# ---------------------------------------------------------------------------


def test_drops_question_dominant_chunk() -> None:
    row = {
        "chunk_text": "¿Quiénes deben practicar la autorretención especial? ¿Cómo se calcula? ¿Cuándo se presenta?",
        "rrf_score": 0.5,
    }
    penalty, reason = score_chunk_quality(row)
    assert penalty == PENALTY_LIGHT
    assert reason == "question_dominant_caption"


# ---------------------------------------------------------------------------
# False-positive guards
# ---------------------------------------------------------------------------


def test_keeps_normal_operational_bullet() -> None:
    row = {
        "chunk_text": "Liquida la retención del Art. 383 ET antes del día 15 de cada mes y guarda el certificado en el expediente del empleado para defender ante una eventual fiscalización.",
        "rrf_score": 0.7,
    }
    penalty, reason = score_chunk_quality(row, routed_topic="retencion_fuente_general")
    assert penalty == 1.0
    assert reason is None


def test_keeps_bullet_with_legitimate_question_in_prose() -> None:
    """A long bullet that happens to contain ONE rhetorical question
    is not question-dominant."""
    row = {
        "chunk_text": (
            "El contador debe verificar si la sociedad cumple con los requisitos para "
            "acceder al beneficio de auditoría. ¿La declaración fue presentada oportunamente? "
            "Verifique también que el pago se haya hecho dentro del término. Los "
            "porcentajes de incremento exigidos son del 25% para firmeza en 12 meses y "
            "del 35% para firmeza en 6 meses, conforme al Art. 689-3 ET."
        ),
        "rrf_score": 0.8,
    }
    penalty, reason = score_chunk_quality(row, routed_topic="beneficio_auditoria")
    assert penalty == 1.0
    assert reason is None


def test_keeps_normative_key_caption_when_followed_by_long_prose() -> None:
    """If the caption is followed by substantive content (not just a
    fragment), we should keep it — only short caption-dominated chunks
    are penalized."""
    row = {
        "chunk_text": (
            "Texto normativo clave — Art. 689-3 ET. Este artículo regula el beneficio "
            "de auditoría con dos porcentajes de incremento: 25% para firmeza en 12 "
            "meses y 35% para firmeza en 6 meses. El cliente debe cumplir cinco "
            "requisitos simultáneamente: presentación oportuna, pago oportuno, "
            "incremento mínimo del impuesto neto de renta respecto al año anterior, "
            "ausencia de causales de invalidación, y consistencia con exógena."
        ),
        "rrf_score": 0.9,
    }
    penalty, reason = score_chunk_quality(row, routed_topic="beneficio_auditoria")
    assert penalty == 1.0
    assert reason is None


def test_empty_chunk_passes_through() -> None:
    row = {"chunk_text": "", "rrf_score": 0.5}
    penalty, reason = score_chunk_quality(row)
    assert penalty == 1.0
    assert reason is None


# ---------------------------------------------------------------------------
# apply_heuristics end-to-end
# ---------------------------------------------------------------------------


def test_apply_heuristics_shadow_does_not_mutate_scores(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIA_CHUNK_QUALITY_HEURISTIC_MODE", "shadow")
    rows = [
        {"chunk_id": "c1", "chunk_text": "Inicie sesión con su cédula y contraseña.", "rrf_score": 0.9},
        {"chunk_id": "c2", "chunk_text": "Bullet operativo legitimo sobre Art. 850 ET devolución.", "rrf_score": 0.7},
    ]
    annotated, diag = apply_heuristics(rows)
    assert diag["gate_mode"] == "shadow"
    assert diag["rows_demoted"] == 1
    # In shadow, rrf_score is UNCHANGED but reason is attached.
    c1 = next(r for r in annotated if r["chunk_id"] == "c1")
    assert c1["rrf_score"] == 0.9
    assert c1["chunk_quality_demotion_reason"] == "portal_login_boilerplate"
    c2 = next(r for r in annotated if r["chunk_id"] == "c2")
    assert c2["rrf_score"] == 0.7
    assert "chunk_quality_demotion_reason" not in c2


def test_apply_heuristics_enforce_mutates_scores(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIA_CHUNK_QUALITY_HEURISTIC_MODE", "enforce")
    rows = [
        {"chunk_id": "c1", "chunk_text": "Inicie sesión con su cédula y contraseña.", "rrf_score": 1.0},
    ]
    annotated, diag = apply_heuristics(rows)
    assert diag["gate_mode"] == "enforce"
    assert diag["rows_demoted"] == 1
    c1 = annotated[0]
    # Score should be multiplied by PENALTY_HEAVY (0.2).
    assert c1["rrf_score"] == pytest.approx(PENALTY_HEAVY, rel=1e-6)
    assert c1["chunk_quality_demotion_reason"] == "portal_login_boilerplate"


def test_apply_heuristics_off_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_CHUNK_QUALITY_HEURISTIC_MODE", "off")
    rows = [
        {"chunk_id": "c1", "chunk_text": "Inicie sesión con su cédula y contraseña.", "rrf_score": 0.9},
    ]
    annotated, diag = apply_heuristics(rows)
    assert diag["gate_mode"] == "off"
    assert diag["rows_demoted"] == 0
    assert annotated[0]["rrf_score"] == 0.9
    assert "chunk_quality_demotion_reason" not in annotated[0]


def test_apply_heuristics_emits_diag_with_samples(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIA_CHUNK_QUALITY_HEURISTIC_MODE", "shadow")
    rows = [
        {"chunk_id": "c1", "doc_id": "d1", "chunk_text": "Caso de estudio: Tienda de abarrotes Bogotá.", "rrf_score": 0.5},
        {"chunk_id": "c2", "doc_id": "d2", "chunk_text": "Texto normativo clave — Art. 240 ET (fragmento relevante)", "rrf_score": 0.6},
    ]
    annotated, diag = apply_heuristics(rows)
    assert diag["rows_demoted"] == 2
    assert "case_study_caption" in diag["reasons"]
    assert "normative_key_caption" in diag["reasons"]
    assert len(diag["samples"]) == 2
    sample_reasons = {s["reason"] for s in diag["samples"]}
    assert sample_reasons == {"case_study_caption", "normative_key_caption"}
