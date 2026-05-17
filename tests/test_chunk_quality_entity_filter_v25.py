"""fix_v25_may.md §3.8 — Phase 8 / G15 tests."""

from __future__ import annotations

from lia_graph.pipeline_d.chunk_quality_heuristics import (
    PENALTY_HEAVY,
    PENALTY_LIGHT,
    PENALTY_MEDIUM,
    score_entity_pollution,
    score_topic_aware_pollution,
)


def test_audit_verbatim_pollution_strings_fire_heavy():
    txt = "El acta de DISTRIBUIDORA EL SOL SAS firmada por ALEJANDRO VASQUEZ ARANGO."
    penalty, reason = score_entity_pollution(txt)
    assert penalty == PENALTY_HEAVY
    assert reason == "audit_verbatim_pollution_string"


def test_innovalab_invented_company_pattern_fires():
    txt = "El caso de InnovaLab para AG 2025 ilustra la compensación de pérdidas."
    penalty, reason = score_entity_pollution(txt)
    assert reason == "audit_verbatim_pollution_string"


def test_carlos_moreno_perez_pattern_fires():
    txt = "Carlos Moreno Pérez aparece reportado como beneficiario final."
    penalty, reason = score_entity_pollution(txt)
    assert reason == "audit_verbatim_pollution_string"


def test_concepto_depreciacion_offtopic_fires_for_cartera():
    txt = (
        "Concepto DIAN 191 de 2025 sobre la depreciación de activos fijos según el "
        "art. 137 ET."
    )
    penalty, reason = score_topic_aware_pollution(txt, routed_topic="cartera")
    assert reason == "concepto_dian_depreciacion_offtopic"
    assert penalty == PENALTY_MEDIUM


def test_concepto_depreciacion_allowed_for_costos_deducciones():
    txt = "Concepto DIAN 191 de 2025 sobre la depreciación del art. 137."
    penalty, reason = score_topic_aware_pollution(
        txt, routed_topic="costos_deducciones_renta"
    )
    assert reason is None


def test_inc_vehicle_offtopic_fires_for_restaurant():
    txt = "Aplica el art. 512-3 ET para vehículos automotores y motocicletas."
    penalty, reason = score_topic_aware_pollution(txt, routed_topic="regimen_simple")
    assert reason == "inc_vehicle_offtopic"


def test_inc_vehicle_allowed_for_vehiculos_topic():
    txt = "Aplica el art. 512-4 ET."
    penalty, reason = score_topic_aware_pollution(txt, routed_topic="vehiculos")
    assert reason is None


def test_incrngo_donations_offtopic_fires_for_dividends():
    txt = "Las INCRNGO incluyen donaciones a entidades sin ánimo de lucro."
    penalty, reason = score_topic_aware_pollution(txt, routed_topic="dividendos")
    assert reason == "incrngo_donations_offtopic"
