"""corpusfix_v1 (2026-05-14) — playbook filename → topic override.

Pins the playbook stem-to-topic table that the ingestion classifier consults
before the broader path-veto rules. Every entry in
``_PLAYBOOK_FILENAME_TO_TOPIC`` must resolve to a canonical key registered in
``get_supported_topics()``; the helper must accept bare stems, stems with
extensions, and full relative paths.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lia_graph.ingest_classifiers import _infer_vocabulary_labels
from lia_graph.ingestion_classifier import (
    _PLAYBOOK_FILENAME_TO_TOPIC,
    _playbook_filename_topic_override,
)
from lia_graph.topic_guardrails import get_supported_topics


def test_every_override_topic_is_a_canonical_taxonomy_key() -> None:
    supported = set(get_supported_topics())
    invalid = {
        stem: topic
        for stem, topic in _PLAYBOOK_FILENAME_TO_TOPIC.items()
        if topic not in supported
    }
    assert not invalid, f"Invalid topic keys in playbook override map: {invalid}"


@pytest.mark.parametrize(
    "stem, expected_topic",
    [
        # Procedimiento / firmeza / sanciones
        ("playbook_renta_notificaciones_electronicas", "procedimiento_tributario"),
        ("playbook_renta_sancion_extemporaneidad", "regimen_sancionatorio_extemporaneidad"),
        ("playbook_renta_sancion_correccion", "regimen_sancionatorio"),
        ("playbook_renta_sancion_inexactitud", "regimen_sancionatorio"),
        ("playbook_renta_firmeza_declaraciones", "firmeza_declaraciones"),
        ("playbook_renta_beneficio_auditoria", "beneficio_auditoria"),
        ("playbook_renta_devolucion_saldos_favor", "devoluciones_saldos_a_favor"),
        ("playbook_renta_anticipo_renta", "procedimiento_tributario"),
        # Deducciones / descuentos
        ("playbook_renta_depreciacion_fiscal", "costos_deducciones_renta"),
        ("playbook_renta_iva_activos_fijos_productivos", "descuentos_tributarios_renta"),
        ("playbook_renta_ctei_descuento", "descuentos_tributarios_renta"),
        # Tarifas / régimen
        ("playbook_renta_tarifa_general_pj_35", "tarifas_renta_y_ttd"),
        ("playbook_renta_rst_tarifas", "regimen_simple"),
        ("playbook_renta_zona_franca_doble_tarifa", "zonas_francas"),
        # Compensación / facturación
        ("playbook_renta_compensacion_perdidas_fiscales", "perdidas_fiscales_art147"),
        ("playbook_renta_soporte_factura_electronica", "facturacion_electronica"),
        # Tier 2
        ("playbook_tier2_clausula_antiabuso", "procedimiento_tributario"),
        ("playbook_tier2_inc_consumo", "impuesto_nacional_consumo"),
        ("playbook_tier2_precios_transferencia", "precios_de_transferencia"),
        ("playbook_tier2_rte_esal", "regimen_tributario_especial_esal"),
        # IVA + exógena + retención + NIIF
        ("playbook_iva_responsables", "iva"),
        ("playbook_iva_excluidos_vs_exentos", "iva"),
        ("playbook_exogena_formato_1001_pagos_terceros", "informacion_exogena"),
        ("playbook_exogena_umbrales_plazos_ag_2025", "informacion_exogena"),
        ("playbook_retencion_salarios_383", "retencion_en_la_fuente"),
        ("playbook_retencion_servicios_392", "retencion_en_la_fuente"),
        ("playbook_niif_conciliacion_fiscal_f2516_f2517", "conciliacion_fiscal"),
        ("playbook_niif_impuesto_diferido", "estados_financieros_niif"),
        ("playbook_niif_ingresos_15_vs_28", "estados_financieros_niif"),
    ],
)
def test_playbook_override_returns_expected_topic(stem: str, expected_topic: str) -> None:
    assert _playbook_filename_topic_override(stem) == expected_topic
    assert _playbook_filename_topic_override(f"{stem}.md") == expected_topic
    assert _playbook_filename_topic_override(f"a/b/{stem}.md") == expected_topic


def test_non_playbook_files_pass_through_unchanged() -> None:
    assert _playbook_filename_topic_override("ET_art_115.md") is None
    assert _playbook_filename_topic_override("DUR_1625_2016.pdf") is None
    assert _playbook_filename_topic_override("") is None
    assert _playbook_filename_topic_override("/unrelated/folder/document.md") is None


def test_vocabulary_inference_prefers_playbook_override_over_path() -> None:
    """The Path inference layer also consults the override map (covers
    --skip-llm runs)."""
    # notificaciones electrónicas sits under RENTA/ on disk, but is really
    # a procedimiento-tributario topic. Path inference must return the
    # override value, not declaracion_renta.
    p = Path(
        "knowledge_base/CORE ya Arriba/RENTA/PLAYBOOKS/"
        "playbook_renta_notificaciones_electronicas.md"
    )
    topic, _sub, _status, _ver = _infer_vocabulary_labels(p, markdown="")
    assert topic == "procedimiento_tributario"

    # Exógena under INFORMACION_EXOGENA_FORMATOS/ — path inference already
    # leans this way, but verify the override still asserts the canonical key.
    p2 = Path(
        "knowledge_base/CORE ya Arriba/INFORMACION_EXOGENA_FORMATOS/PLAYBOOKS/"
        "playbook_exogena_formato_1001_pagos_terceros.md"
    )
    topic2, _, _, _ = _infer_vocabulary_labels(p2, markdown="")
    assert topic2 == "informacion_exogena"
