"""corpusfix_v1 (2026-05-14) — explicit playbook → topic map.

Path-based topic inference (RENTA/, IVA_COMPLETO/, etc.) misclassifies
playbooks whose subject differs from the path. Example: every file under
RENTA/PLAYBOOKS/ defaults to ``declaracion_renta``, but
``playbook_renta_notificaciones_electronicas`` is really
``procedimiento_tributario``. Causes the coherence gate to abstain on
correct retrievals at runtime.

Authoritative table below; keys are filename stems (no extension), values
are canonical topic keys from ``config/topic_taxonomy.json`` (verified
against ``get_supported_topics()`` in
``tests/test_classifier_playbook_override.py``).

The override is consumed in two places:

1. ``ingestion_classifier.classify_ingestion_document`` — applied BEFORE
   the broader ``_PATH_VETO_RULES`` so the stem table wins on match. The
   shared call site marks ``classification_source="path_veto"`` so the
   topic_override propagation in
   ``ingest_subtopic_pass._assemble_doc_from_verdict`` fires.

2. ``ingest_classifiers._infer_vocabulary_labels`` — applied before the
   prefix/alias heuristics so playbook files whose path implies the wrong
   topic get the correct topic even on ``--skip-llm`` runs.

Module split per ``feedback_granular_edits``: this table grows whenever a
new playbook ships, so it lives in its own sibling rather than bloating
``ingestion_classifier.py`` (already > 1200 LOC and a hot orchestrator).
"""

from __future__ import annotations


_PLAYBOOK_FILENAME_TO_TOPIC: dict[str, str] = {
    # --- Renta — Procedimiento (sanciones + firmeza + notificaciones + beneficio
    #     + devolución + anticipo) ---
    "playbook_renta_notificaciones_electronicas": "procedimiento_tributario",
    "playbook_renta_sancion_extemporaneidad": "regimen_sancionatorio_extemporaneidad",
    "playbook_renta_sancion_correccion": "regimen_sancionatorio",
    "playbook_renta_sancion_inexactitud": "regimen_sancionatorio",
    "playbook_renta_firmeza_declaraciones": "firmeza_declaraciones",
    "playbook_renta_beneficio_auditoria": "beneficio_auditoria",
    "playbook_renta_devolucion_saldos_favor": "devoluciones_saldos_a_favor",
    "playbook_renta_anticipo_renta": "procedimiento_tributario",
    # --- Renta — Deducciones (costos_deducciones_renta) ---
    "playbook_renta_depreciacion_fiscal": "costos_deducciones_renta",
    "playbook_renta_atenciones_clientes_empleados": "costos_deducciones_renta",
    "playbook_renta_cartera_dificil_recaudo": "costos_deducciones_renta",
    "playbook_renta_donaciones_deducibles": "costos_deducciones_renta",
    "playbook_renta_limitacion_pagos_efectivo": "costos_deducciones_renta",
    "playbook_renta_exoneracion_parafiscales_114_1": "costos_deducciones_renta",
    # --- Renta — Descuentos tributarios ---
    "playbook_renta_iva_activos_fijos_productivos": "descuentos_tributarios_renta",
    "playbook_renta_ctei_descuento": "descuentos_tributarios_renta",
    # --- Renta — Tarifas y régimen ---
    "playbook_renta_tarifa_general_pj_35": "tarifas_renta_y_ttd",
    "playbook_renta_dividendos_pn_residentes": "tarifas_renta_y_ttd",
    "playbook_renta_rst_tarifas": "regimen_simple",
    "playbook_renta_zona_franca_doble_tarifa": "zonas_francas",
    # --- Renta — Compensación / conciliación / facturación ---
    "playbook_renta_compensacion_perdidas_fiscales": "perdidas_fiscales_art147",
    "playbook_renta_soporte_factura_electronica": "facturacion_electronica",
    # --- Tier 2 (RENTA/PLAYBOOKS/) ---
    "playbook_tier2_aportes_voluntarios_pension_afc": "declaracion_renta",
    "playbook_tier2_capitalizacion_utilidades": "dividendos_y_distribucion_utilidades",
    "playbook_tier2_clausula_antiabuso": "procedimiento_tributario",
    "playbook_tier2_dividendos_no_gravados": "dividendos_y_distribucion_utilidades",
    "playbook_tier2_inc_consumo": "impuesto_nacional_consumo",
    "playbook_tier2_precios_transferencia": "precios_de_transferencia",
    "playbook_tier2_renta_cedular_pn": "declaracion_renta",
    "playbook_tier2_rte_esal": "regimen_tributario_especial_esal",
    # --- IVA (under IVA_COMPLETO/PLAYBOOKS/, topic "iva") ---
    "playbook_iva_hecho_generador": "iva",
    "playbook_iva_responsables": "iva",
    "playbook_iva_descontable_proporcionalidad": "iva",
    "playbook_iva_devolucion_saldos_favor": "iva",
    "playbook_iva_excluidos_vs_exentos": "iva",
    # --- Retención en la fuente ---
    "playbook_retencion_salarios_383": "retencion_en_la_fuente",
    "playbook_retencion_servicios_392": "retencion_en_la_fuente",
    # --- Información exógena ---
    "playbook_exogena_formato_1001_pagos_terceros": "informacion_exogena",
    "playbook_exogena_formato_1003_retenciones": "informacion_exogena",
    "playbook_exogena_formato_1005_iva_descontable": "informacion_exogena",
    "playbook_exogena_formato_1007_ingresos": "informacion_exogena",
    "playbook_exogena_umbrales_plazos_ag_2025": "informacion_exogena",
    # --- NIIF / Estados financieros ---
    "playbook_niif_conciliacion_fiscal_f2516_f2517": "conciliacion_fiscal",
    "playbook_niif_impuesto_diferido": "estados_financieros_niif",
    "playbook_niif_ingresos_15_vs_28": "estados_financieros_niif",
    "playbook_niif_depreciacion_niif_vs_fiscal": "estados_financieros_niif",
    # --- Laboral / Nómina (CST + Ley 50 + parafiscales + UGPP) ---
    "playbook_laboral_contrato_aprendizaje_sena": "laboral",
    "playbook_laboral_contrato_prestacion_vs_laboral": "laboral",
    "playbook_laboral_embargos_salario": "laboral",
    "playbook_laboral_liquidacion_mensual_nomina": "laboral",
    "playbook_laboral_liquidacion_terminacion": "laboral",
    "playbook_laboral_nomina_electronica_dspne": "laboral",
    "playbook_laboral_pila_aportes": "parafiscales_seguridad_social",
    "playbook_laboral_prestaciones_sociales": "laboral",
    "playbook_laboral_smmlv_aux_transporte_anual": "laboral",
    "playbook_laboral_subsidios_transporte_alimentacion": "laboral",
    "playbook_laboral_teletrabajo_trabajo_casa": "laboral",
    "playbook_laboral_ugpp_fiscalizacion": "parafiscales_seguridad_social",
    # --- Panel adiciones (cierre, ICA territorial, RST migracion, reteica) ---
    "playbook_panel_cierre_fiscal_anual_checklist": "declaracion_renta",
    "playbook_panel_ica_territorial": "ica",
    "playbook_panel_migracion_rst_ordinario": "regimen_simple",
    "playbook_panel_reteica_municipal": "ica",
    # --- Renta — deducciones adicionales (parafiscales + pagos no salariales + salario integral) ---
    "playbook_renta_aportes_parafiscales_seguridad_social": "costos_deducciones_renta",
    "playbook_renta_pagos_no_constitutivos_salario": "costos_deducciones_renta",
    "playbook_renta_salario_integral": "laboral",
    # --- Renta — descuentos adicionales (Ley 1715, Ley 361, Ley 1257, Ley 2277, ICA 50 %, donaciones descuento) ---
    "playbook_renta_discapacidad_200": "descuentos_tributarios_renta",
    "playbook_renta_donaciones_descuento": "descuentos_tributarios_renta",
    "playbook_renta_energias_renovables": "descuentos_tributarios_renta",
    "playbook_renta_factura_electronica_1": "descuentos_tributarios_renta",
    "playbook_renta_ica_descuento_50": "descuentos_tributarios_renta",
    "playbook_renta_mujeres_violencia_200": "descuentos_tributarios_renta",
    # --- Renta — tarifas adicionales (TTD + ZOMAC/ZESE) ---
    "playbook_renta_ttd_tasa_minima": "tarifas_renta_y_ttd",
    "playbook_renta_zomac_zese": "zomac_zese_incentivos_geograficos",
    # --- Retención en la fuente — autoret, bases mínimas, tablas AG ---
    "playbook_retencion_autoretencion": "retencion_en_la_fuente",
    "playbook_retencion_bases_minimas": "retencion_en_la_fuente",
    "playbook_retencion_tablas_ag_2025_2026": "retencion_en_la_fuente",
    # --- Tier 2 (doc comprobatoria, patrimonio, omisión activos, precios T, recursos DIAN, presuntiva) ---
    "playbook_tier2_doc_comprobatoria_f1125_f1729": "precios_de_transferencia",
    "playbook_tier2_impuesto_patrimonio": "impuesto_patrimonio_personas_naturales",
    "playbook_tier2_omision_activos_434a": "regimen_sancionatorio",
    "playbook_tier2_precios_transferencia_umbrales": "precios_de_transferencia",
    "playbook_tier2_recursos_dian": "procedimiento_tributario",
    "playbook_tier2_renta_presuntiva_historico": "renta_presuntiva",
}


def _playbook_filename_topic_override(filename: str) -> str | None:
    """corpusfix_v1 — look up authoritative topic by playbook filename stem.

    Returns None for non-playbook files so the path-veto + LLM fallback
    keep running for the rest of the corpus. The lookup tolerates either
    a bare stem (``playbook_iva_responsables``), a stem with extension
    (``playbook_iva_responsables.md``), or a relative path whose final
    segment is one of the above.
    """
    if not filename:
        return None
    # Extract the last path segment, strip extension.
    tail = filename.replace("\\", "/").rsplit("/", 1)[-1]
    if "." in tail:
        tail = tail.rsplit(".", 1)[0]
    return _PLAYBOOK_FILENAME_TO_TOPIC.get(tail)


__all__ = [
    "_PLAYBOOK_FILENAME_TO_TOPIC",
    "_playbook_filename_topic_override",
]
