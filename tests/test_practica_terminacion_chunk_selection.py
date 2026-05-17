"""fix_v21_may §3.2 P2-T2 — práctica off-topic bullets on labor article-lookup.

The v20 closing probe q01 ("¿Qué dice el artículo 64 del CST sobre la
terminación sin justa causa del contrato de trabajo?") surfaced bullets
from ``playbook_laboral_liquidacion_terminacion.md`` that were
topically unrelated to the question (cesación codes 54-58, recargos
jornada nocturna, valor hora ordinaria) — instead of the indemnización
day-count formula the article actually answers.

Root cause (P1-T2 diagnosis in ``fix_v21_may.md`` §6): the case detector
``is_liquidacion_terminacion_case`` requires operational-form markers
(``despido sin justa causa``, ``indemnización por despido``, etc.) and
misses the article-lookup form (``¿Qué dice el artículo 64 del CST
sobre la terminación sin justa causa?``). When no case fires,
``answer_synthesis_sections._active_case_keywords`` returns an empty
tuple and ``_filter_offtopic_bullets_for_case`` becomes a no-op — every
chunk bullet survives, including the cesación-code + jornada-nocturna
fragments from the same playbook doc.

This file locks: the detector MUST fire on the article-lookup form so
the existing off-topic filter kicks in.
"""

from __future__ import annotations

from lia_graph.pipeline_d.answer_shared import normalize_text
from lia_graph.pipeline_d.case_detectors import is_liquidacion_terminacion_case


def _normalize(question: str) -> str:
    return normalize_text(question)


def test_detector_fires_on_article_lookup_cst_64() -> None:
    """v20-q01 regression: the article-lookup form ('¿Qué dice el
    artículo 64 del CST?') must trigger the liquidación-terminación
    case so its keywords feed the off-topic filter at
    ``build_recommendations`` tail."""
    q = (
        "¿Qué dice el artículo 64 del CST sobre la terminación sin "
        "justa causa del contrato de trabajo?"
    )
    assert is_liquidacion_terminacion_case(_normalize(q)) is True


def test_detector_fires_on_article_lookup_cst_65() -> None:
    """CST 65 = indemnización moratoria; article-lookup must also bind."""
    q = "¿Qué establece el artículo 65 del CST?"
    assert is_liquidacion_terminacion_case(_normalize(q)) is True


def test_detector_fires_on_article_lookup_cst_62() -> None:
    """CST 62 = justa causa; article-lookup must bind."""
    q = "Explícame el artículo 62 del Código Sustantivo del Trabajo."
    assert is_liquidacion_terminacion_case(_normalize(q)) is True


def test_detector_fires_on_operational_form_q02() -> None:
    """v20-q02 regression guard: the operational form was already
    firing pre-v21; do not regress it."""
    q = (
        "¿Cuáles son los días que tengo que pagar de indemnización si "
        "despido sin justa causa a un trabajador con contrato a término "
        "indefinido y 5 años de antigüedad?"
    )
    assert is_liquidacion_terminacion_case(_normalize(q)) is True


def test_detector_does_not_fire_on_unrelated_labor_query() -> None:
    """Widening must stay narrow: an unrelated labor question — e.g.
    payroll mechanics with no terminación/indemnización vocabulary —
    must NOT fire this case."""
    q = "¿Cuál es el porcentaje de aportes a salud y pensión en 2026?"
    assert is_liquidacion_terminacion_case(_normalize(q)) is False


def test_detector_does_not_fire_on_unrelated_cst_article() -> None:
    """An article-lookup for an unrelated CST article (e.g. art. 127
    salary definition) must NOT fire the terminación case — the bind
    is specific to arts. 62 / 64 / 65."""
    q = "¿Qué dice el artículo 127 del CST?"
    assert is_liquidacion_terminacion_case(_normalize(q)) is False
