"""v15.5 (2026-05-14) — case-anchor registry in `planner.py`.

Replaces the fix_v8 §3g ICA-specific if-block with a generic registry
that ties each case detector (GMF / ICA / predial / intereses / leasing
/ primer empleo) to the ET article numbers that should be anchored when
that case fires.

Validates that:

1. Each case detector causes the planner to emit the correct
   `PlannerEntryPoint` with `kind="article"` and the right
   `resolved_key`.
2. Cases that don't fire emit no case-specific entry points.
3. Registry-driven search queries augment the text-search side so
   retrieval surfaces the right chunks.
4. The previous ICA behavior (Art. 115 anchored for ICA-in-renta) is
   preserved — i.e. the refactor is functionally equivalent for ICA
   and additive for the other five cases.
"""

from __future__ import annotations

from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d.planner import build_graph_retrieval_plan


def _req(message: str, topic: str = "costos_deducciones_renta") -> PipelineCRequest:
    return PipelineCRequest(
        message=message,
        topic=topic,
        requested_topic=topic,
    )


def _planner_anchor_keys(message: str) -> set[str]:
    plan = build_graph_retrieval_plan(_req(message))
    return {
        ep.resolved_key
        for ep in plan.entry_points
        if ep.kind == "article"
    }


def _planner_anchor_sources(message: str) -> set[str]:
    plan = build_graph_retrieval_plan(_req(message))
    return {ep.source for ep in plan.entry_points if ep.kind == "article"}


def _planner_search_queries(message: str) -> set[str]:
    """Return the union of `lookup_value`s for `article_search` entry
    points — that's where the case-search-queries land in the
    `PlannerEntryPoint` shape."""
    plan = build_graph_retrieval_plan(_req(message))
    return {
        str(ep.lookup_value)
        for ep in plan.entry_points
        if ep.kind == "article_search"
    }


# ---------------------------------------------------------------------------
# Each case fires its registered anchor articles.
# ---------------------------------------------------------------------------


def test_gmf_case_anchors_art_115() -> None:
    keys = _planner_anchor_keys(
        "¿qué porcentaje del gmf 4x1000 es deducible en renta?"
    )
    assert "115" in keys
    sources = _planner_anchor_sources(
        "¿qué porcentaje del gmf 4x1000 es deducible en renta?"
    )
    assert "gmf_deduction_anchor" in sources


def test_ica_case_anchors_art_115_and_115_1() -> None:
    keys = _planner_anchor_keys(
        "¿el ica pagado por la pyme es deducible en renta?"
    )
    # Both the deducción rule (115) and the descuento-tributario
    # alternative (115-1) are anchored — the answer needs both.
    assert "115" in keys
    assert "115-1" in keys


def test_predial_case_anchors_art_115() -> None:
    """The probe failure that motivated v15.5: predial cited Art. 121
    instead of Art. 115. After the registry edit, the planner anchors
    Art. 115 directly so retrieval can't miss it."""
    keys = _planner_anchor_keys(
        "¿el predial pagado por la bodega es deducible en renta?"
    )
    assert "115" in keys
    sources = _planner_anchor_sources(
        "¿el predial pagado por la bodega es deducible en renta?"
    )
    assert "predial_deduction_anchor" in sources


def test_intereses_case_anchors_art_117_and_118_1() -> None:
    keys = _planner_anchor_keys(
        "¿son deducibles los intereses del préstamo bancario?"
    )
    assert "117" in keys
    assert "118-1" in keys


def test_leasing_case_anchors_art_127_1() -> None:
    keys = _planner_anchor_keys(
        "¿cómo se deduce el leasing financiero del vehículo?"
    )
    assert "127-1" in keys


def test_primer_empleo_case_anchors_art_108_5() -> None:
    keys = _planner_anchor_keys(
        "¿procede la deducción del 120% por primer empleo?"
    )
    assert "108-5" in keys


def test_depreciacion_case_anchors_art_137() -> None:
    keys = _planner_anchor_keys(
        "¿cuál es la vida útil fiscal de una camioneta?"
    )
    assert "137" in keys
    sources = _planner_anchor_sources(
        "¿cuál es la vida útil fiscal de una camioneta?"
    )
    assert "depreciacion_anchor" in sources


def test_atenciones_case_anchors_art_107_1() -> None:
    keys = _planner_anchor_keys(
        "¿cuánto puedo deducir en regalos a clientes en renta?"
    )
    assert "107-1" in keys
    sources = _planner_anchor_sources(
        "¿cuánto puedo deducir en regalos a clientes en renta?"
    )
    assert "atenciones_anchor" in sources


def test_cartera_dificil_recaudo_case_anchors_arts_145_and_146() -> None:
    keys = _planner_anchor_keys(
        "¿qué porcentaje puedo provisionar de la cartera vencida?"
    )
    assert "145" in keys
    assert "146" in keys


def test_donaciones_case_anchors_arts_257_and_125() -> None:
    keys = _planner_anchor_keys(
        "¿la donación a una fundación calificada en RTE da descuento?"
    )
    assert "257" in keys
    assert "125" in keys


def test_exoneracion_parafiscales_case_anchors_art_114_1() -> None:
    # Phrase WITHOUT explicit "art 114-1" so the explicit-reference path
    # doesn't preempt the case-anchor path.
    keys = _planner_anchor_keys(
        "¿mi empresa califica para la exoneración de parafiscales del 13,5%?"
    )
    assert "114-1" in keys
    sources = _planner_anchor_sources(
        "¿mi empresa califica para la exoneración de parafiscales del 13,5%?"
    )
    assert "exoneracion_parafiscales_anchor" in sources


def test_iva_activos_fijos_case_anchors_art_258_1() -> None:
    keys = _planner_anchor_keys(
        "¿cómo recupero el iva de la maquinaria como descuento de renta?"
    )
    assert "258-1" in keys


def test_ctei_descuento_case_anchors_art_256() -> None:
    keys = _planner_anchor_keys(
        "¿qué porcentaje de la inversion en ctei puedo descontar en renta?"
    )
    assert "256" in keys


def test_tarifa_general_pj_case_anchors_art_240() -> None:
    keys = _planner_anchor_keys(
        "¿cual es la tarifa general de renta para una sas ag 2025?"
    )
    assert "240" in keys


def test_dividendos_pn_case_anchors_art_242() -> None:
    keys = _planner_anchor_keys(
        "¿como se gravan los dividendos a una pn residente con la reforma 2022?"
    )
    assert "242" in keys


def test_rst_tarifas_case_anchors_art_908() -> None:
    keys = _planner_anchor_keys(
        "¿que tarifas tiene el regimen simple para ag 2025?"
    )
    assert "908" in keys


def test_zona_franca_case_anchors_art_240_1() -> None:
    keys = _planner_anchor_keys(
        "¿cual es la tarifa de renta de un usuario industrial de zona franca?"
    )
    assert "240-1" in keys


def test_beneficio_auditoria_case_anchors_art_689_3() -> None:
    keys = _planner_anchor_keys(
        "¿cuando aplica el beneficio de auditoria en renta?"
    )
    assert "689-3" in keys


def test_firmeza_declaraciones_case_anchors_art_714() -> None:
    keys = _planner_anchor_keys(
        "¿en cuantos anos queda en firme la declaracion de renta?"
    )
    assert "714" in keys


def test_devolucion_saldos_favor_case_anchors_art_850() -> None:
    keys = _planner_anchor_keys(
        "¿como solicito la devolucion del saldo a favor en renta?"
    )
    assert "850" in keys


def test_sancion_extemporaneidad_case_anchors_art_641() -> None:
    keys = _planner_anchor_keys(
        "¿cuánto cuesta presentar tarde la declaración de renta?"
    )
    assert "641" in keys


def test_sancion_correccion_case_anchors_art_644() -> None:
    keys = _planner_anchor_keys(
        "¿cuánto cuesta corregir la declaración de renta voluntariamente?"
    )
    assert "644" in keys


def test_sancion_inexactitud_case_anchors_art_647() -> None:
    keys = _planner_anchor_keys(
        "¿qué porcentaje es la sanción por inexactitud en renta?"
    )
    assert "647" in keys


def test_notificaciones_electronicas_case_anchors_art_566_1() -> None:
    keys = _planner_anchor_keys(
        "¿cómo me notifica la DIAN por buzón electrónico hoy?"
    )
    assert "566-1" in keys


def test_iva_hecho_generador_case_anchors_art_420() -> None:
    keys = _planner_anchor_keys(
        "¿cuáles son los hechos generadores del IVA en colombia?"
    )
    assert "420" in keys


def test_iva_responsables_case_anchors_art_437() -> None:
    keys = _planner_anchor_keys(
        "¿cuándo se es responsable de IVA y cuál es el tope de no responsable?"
    )
    assert "437" in keys


def test_iva_descontable_case_anchors_art_488() -> None:
    keys = _planner_anchor_keys(
        "¿cómo se calcula la proporcionalidad del IVA descontable?"
    )
    assert "488" in keys


def test_iva_devolucion_case_anchors_art_481() -> None:
    keys = _planner_anchor_keys(
        "¿cómo solicito la devolución del IVA para un exportador?"
    )
    assert "481" in keys


def test_iva_excluidos_exentos_case_anchors_art_424() -> None:
    keys = _planner_anchor_keys(
        "¿cuál es la diferencia entre bienes excluidos y exentos del IVA?"
    )
    assert "424" in keys


def test_retencion_salarios_case_anchors_art_383() -> None:
    keys = _planner_anchor_keys(
        "¿procedimiento 1 o 2 para retener al empleado por salarios?"
    )
    assert "383" in keys


# v16 batch 4

def test_retencion_servicios_case_anchors_art_392() -> None:
    # Use literal "retención por honorarios" — the exact marker phrasing.
    # Avoids "tarifa" which would otherwise trip tarifa_general_pj first.
    keys = _planner_anchor_keys(
        "¿retención por honorarios a un consultor declarante?"
    )
    assert "392" in keys


def test_anticipo_renta_case_anchors_art_807() -> None:
    keys = _planner_anchor_keys(
        "¿cómo se calcula el anticipo del impuesto de renta?"
    )
    assert "807" in keys


def test_soporte_factura_case_anchors_art_771_2() -> None:
    keys = _planner_anchor_keys(
        "¿qué soporte necesito para deducir un gasto con factura electrónica?"
    )
    assert "771-2" in keys


def test_compensacion_perdidas_case_anchors_art_147() -> None:
    keys = _planner_anchor_keys(
        "¿cuántos años tengo para compensar pérdidas fiscales?"
    )
    assert "147" in keys


def test_exogena_1001_case_anchors_art_631() -> None:
    keys = _planner_anchor_keys(
        "¿qué reporto en el formato 1001 de pagos a terceros?"
    )
    assert "631" in keys


def test_exogena_1003_case_anchors_art_365() -> None:
    keys = _planner_anchor_keys(
        "¿qué reporto en el formato 1003 de retenciones?"
    )
    assert "365" in keys


def test_exogena_1005_case_anchors_art_488() -> None:
    keys = _planner_anchor_keys(
        "¿cómo cruza el formato 1005 con la declaración 300 de IVA?"
    )
    assert "488" in keys


def test_exogena_1007_case_anchors_art_631() -> None:
    keys = _planner_anchor_keys(
        "¿cómo cruza el formato 1007 con la declaración de renta?"
    )
    assert "631" in keys


def test_niif_conciliacion_fiscal_case_anchors_art_772_1() -> None:
    keys = _planner_anchor_keys(
        "¿quién presenta F2516 y quién F2517 de conciliación fiscal?"
    )
    assert "772-1" in keys


# v16 batch 5

def test_inc_consumo_case_anchors_art_512_1() -> None:
    keys = _planner_anchor_keys(
        "¿el INC se descuenta como IVA o es mayor valor del costo?"
    )
    assert "512-1" in keys


def test_precios_transferencia_case_anchors_art_260_1() -> None:
    keys = _planner_anchor_keys(
        "¿qué umbral activa la declaración informativa F120 de precios de transferencia?"
    )
    assert "260-1" in keys


def test_dividendos_no_gravados_case_anchors_art_49() -> None:
    keys = _planner_anchor_keys(
        "¿cómo calculo el dividendo no gravado del art. 49 ET?"
    )
    assert "49" in keys


def test_capitalizacion_utilidades_case_anchors_art_36_3() -> None:
    keys = _planner_anchor_keys(
        "¿la capitalización de utilidades genera renta para el socio?"
    )
    assert "36-3" in keys


def test_aportes_voluntarios_pension_case_anchors_art_126_1() -> None:
    keys = _planner_anchor_keys(
        "¿qué tope conjunto aplica a aportes voluntarios de pensión y AFC?"
    )
    assert "126-1" in keys


def test_renta_cedular_pn_case_anchors_art_336() -> None:
    keys = _planner_anchor_keys(
        "¿cómo se arma la cédula general de una persona natural?"
    )
    assert "336" in keys


def test_rte_esal_case_anchors_art_19() -> None:
    keys = _planner_anchor_keys(
        "¿cómo califico una fundación al Régimen Tributario Especial?"
    )
    assert "19" in keys


def test_clausula_antiabuso_case_anchors_art_869() -> None:
    keys = _planner_anchor_keys(
        "¿cuándo la DIAN puede recaracterizar una operación por abuso tributario?"
    )
    assert "869" in keys


def test_impuesto_diferido_case_anchors_via_240() -> None:
    keys = _planner_anchor_keys(
        "¿cómo calculo el impuesto diferido bajo NIC 12?"
    )
    # Anchor for impuesto_diferido = art. 240 (tarifa).
    assert "240" in keys


def test_niif_ingresos_case_anchors_art_28() -> None:
    keys = _planner_anchor_keys(
        "¿cuándo NIIF 15 reconoce ingreso pero el ET no lo grava?"
    )
    assert "28" in keys


def test_pagos_efectivo_case_anchors_art_771_5() -> None:
    # Phrase WITHOUT the explicit "art. 771-5" so the explicit-reference
    # detector doesn't grab the anchor source. We want to assert that
    # the case-detector path adds the anchor on its own.
    keys = _planner_anchor_keys(
        "¿cuánto puedo pagar en efectivo y deducir en renta — tope bancarización?"
    )
    assert "771-5" in keys
    sources = _planner_anchor_sources(
        "¿cuánto puedo pagar en efectivo y deducir en renta — tope bancarización?"
    )
    assert "pagos_efectivo_anchor" in sources


# ---------------------------------------------------------------------------
# Non-case queries don't pick up case anchors.
# ---------------------------------------------------------------------------


def test_unrelated_question_emits_no_case_anchor() -> None:
    sources = _planner_anchor_sources(
        "¿cuáles son los plazos para presentar la declaración de renta?"
    )
    # None of the eleven v15.5 + v16 case-anchor sources should fire on
    # a generic plazos question.
    case_sources = {
        "gmf_deduction_anchor",
        "ica_deduction_anchor",
        "predial_deduction_anchor",
        "intereses_deduction_anchor",
        "leasing_deduction_anchor",
        "primer_empleo_deduction_anchor",
        "depreciacion_anchor",
        "atenciones_anchor",
        "cartera_dificil_recaudo_anchor",
        "donaciones_anchor",
        "pagos_efectivo_anchor",
        "exoneracion_parafiscales_anchor",
        "iva_activos_fijos_anchor",
        "ctei_descuento_anchor",
        "tarifa_general_pj_anchor",
        "dividendos_pn_anchor",
        "rst_tarifas_anchor",
        "zona_franca_anchor",
        "beneficio_auditoria_anchor",
        "firmeza_declaraciones_anchor",
        "devolucion_saldos_favor_anchor",
        "sancion_extemporaneidad_anchor",
        "sancion_correccion_anchor",
        "sancion_inexactitud_anchor",
        "notificaciones_electronicas_anchor",
        "iva_hecho_generador_anchor",
        "iva_responsables_anchor",
        "iva_descontable_anchor",
        "iva_devolucion_anchor",
        "iva_excluidos_exentos_anchor",
        "retencion_salarios_anchor",
    }
    assert sources.isdisjoint(case_sources)


# ---------------------------------------------------------------------------
# Cases are evaluated in registry order — earlier rows precedence.
# ---------------------------------------------------------------------------


def test_multi_keyword_query_picks_first_matching_case() -> None:
    """When a query happens to match two cases, the earlier row in
    `_CASE_ANCHOR_REGISTRY` wins (the `break` after emit). This is a
    deterministic precedence — easier to reason about than scoring."""
    # GMF (row 0) wins over ICA (row 1) when both fire.
    keys = _planner_anchor_keys(
        "tratamiento del gmf y del ica en renta para una pyme"
    )
    assert "115" in keys
    # 115-1 (ICA-specific descuento) should NOT appear because ICA
    # row was skipped in favor of GMF row.
    assert "115-1" not in keys


# ---------------------------------------------------------------------------
# Search queries are added for the matched case.
# ---------------------------------------------------------------------------


def test_predial_case_adds_search_queries() -> None:
    """Surfaces a case-specific search query that mentions Art. 115 +
    predial, so the text-search half of hybrid_search has a chance to
    rank Cap IV chunks above Cap V chunks."""
    queries = _planner_search_queries(
        "¿el predial pagado por la bodega es deducible en renta?"
    )
    joined = " | ".join(queries).lower()
    assert "predial" in joined
    assert "115" in joined
