"""v16 (2026-05-14) — Case-bullet registry package.

Each topic gets its own sibling file declaring a single
:class:`CaseSpec` instance. ``CASE_REGISTRY`` is the ordered tuple
the synthesis layer (``answer_synthesis_sections.build_recommendations``
+ ``_active_case_keywords``) and the planner layer
(``planner._CASE_ANCHOR_REGISTRY`` + ``planner._CASE_SEARCH_QUERIES``)
both iterate.

Why a registry: prior to fix_v16 the same six topics were duplicated
across three locations (detector list in ``case_detectors.py``,
case-branch ``if`` chains + whitelists in ``answer_synthesis_sections.py``,
and two parallel registry tuples in ``planner.py``). Adding one topic
required four parallel edits. fix_v16 §13 also warned that
``answer_synthesis_sections.py`` was already at 1254 LOC, and the
plan calls for ~50 more topics. A single-row-per-topic registry caps
the per-topic edit at one new file plus one import line in
``__init__.py``.

Ordering of ``CASE_REGISTRY`` matches the historical case-branch order
in ``build_recommendations`` (v15.5 baseline) so the off-topic-filter
union semantics and the planner anchor-merge order are unchanged.
"""
from __future__ import annotations

from ._registry import CaseSpec
from .anticipo_renta import SPEC as _ANTICIPO_RENTA_SPEC
from .aportes_proporcionales_tiempo_parcial import SPEC as _APORTES_PROPORCIONALES_TIEMPO_PARCIAL_SPEC
from .aportes_voluntarios_pension import SPEC as _APORTES_VOLUNTARIOS_PENSION_SPEC
from .atenciones import SPEC as _ATENCIONES_SPEC
from .contrato_aprendizaje_sena import SPEC as _CONTRATO_APRENDIZAJE_SENA_SPEC
from .contrato_prestacion_vs_laboral import SPEC as _CONTRATO_PRESTACION_VS_LABORAL_SPEC
from .liquidacion_mensual_nomina import SPEC as _LIQUIDACION_MENSUAL_NOMINA_SPEC
from .liquidacion_terminacion import SPEC as _LIQUIDACION_TERMINACION_SPEC
from .nomina_electronica_dspne import SPEC as _NOMINA_ELECTRONICA_DSPNE_SPEC
from .pila_aportes import SPEC as _PILA_APORTES_SPEC
from .prestaciones_sociales import SPEC as _PRESTACIONES_SOCIALES_SPEC
from .salario_integral import SPEC as _SALARIO_INTEGRAL_SPEC
from .ugpp_fiscalizacion import SPEC as _UGPP_FISCALIZACION_SPEC
from .beneficio_auditoria import SPEC as _BENEFICIO_AUDITORIA_SPEC
from .capitalizacion_utilidades import SPEC as _CAPITALIZACION_UTILIDADES_SPEC
from .cartera_dificil_recaudo import SPEC as _CARTERA_SPEC
from .clausula_antiabuso import SPEC as _CLAUSULA_ANTIABUSO_SPEC
from .compensacion_perdidas import SPEC as _COMPENSACION_PERDIDAS_SPEC
from .ctei_descuento import SPEC as _CTEI_DESCUENTO_SPEC
from .depreciacion import SPEC as _DEPRECIACION_SPEC
from .devolucion_saldos_favor import SPEC as _DEVOLUCION_SALDOS_SPEC
from .dividendos_no_gravados import SPEC as _DIVIDENDOS_NO_GRAVADOS_SPEC
from .dividendos_pn import SPEC as _DIVIDENDOS_PN_SPEC
from .donaciones import SPEC as _DONACIONES_SPEC
from .exogena_1001 import SPEC as _EXOGENA_1001_SPEC
from .exogena_1003 import SPEC as _EXOGENA_1003_SPEC
from .exogena_1005 import SPEC as _EXOGENA_1005_SPEC
from .exogena_1007 import SPEC as _EXOGENA_1007_SPEC
from .exogena_umbrales import SPEC as _EXOGENA_UMBRALES_SPEC
from .exoneracion_parafiscales import SPEC as _EXONERACION_PARAFISCALES_SPEC
from .firmeza_declaraciones import SPEC as _FIRMEZA_DECLARACIONES_SPEC
from .gmf import SPEC as _GMF_SPEC
from .ica import SPEC as _ICA_SPEC
from .impuesto_diferido import SPEC as _IMPUESTO_DIFERIDO_SPEC
from .inc_consumo import SPEC as _INC_CONSUMO_SPEC
from .intereses import SPEC as _INTERESES_SPEC
from .iva_activos_fijos import SPEC as _IVA_ACTIVOS_FIJOS_SPEC
from .iva_descontable import SPEC as _IVA_DESCONTABLE_SPEC
from .iva_devolucion import SPEC as _IVA_DEVOLUCION_SPEC
from .iva_excluidos_exentos import SPEC as _IVA_EXCLUIDOS_EXENTOS_SPEC
from .iva_hecho_generador import SPEC as _IVA_HECHO_GENERADOR_SPEC
from .iva_responsables import SPEC as _IVA_RESPONSABLES_SPEC
from .leasing import SPEC as _LEASING_SPEC
from .niif_conciliacion_fiscal import SPEC as _NIIF_CONCILIACION_FISCAL_SPEC
from .niif_ingresos import SPEC as _NIIF_INGRESOS_SPEC
from .notificaciones_electronicas import SPEC as _NOTIFICACIONES_ELECTRONICAS_SPEC
from .pagos_efectivo import SPEC as _PAGOS_EFECTIVO_SPEC
from .precios_transferencia import SPEC as _PRECIOS_TRANSFERENCIA_SPEC
from .predial import SPEC as _PREDIAL_SPEC
from .primer_empleo import SPEC as _PRIMER_EMPLEO_SPEC
from .renta_cedular_pn import SPEC as _RENTA_CEDULAR_PN_SPEC
from .retencion_salarios import SPEC as _RETENCION_SALARIOS_SPEC
from .retencion_servicios import SPEC as _RETENCION_SERVICIOS_SPEC
from .rst_tarifas import SPEC as _RST_TARIFAS_SPEC
from .rte_esal import SPEC as _RTE_ESAL_SPEC
from .sancion_correccion import SPEC as _SANCION_CORRECCION_SPEC
from .sancion_extemporaneidad import SPEC as _SANCION_EXTEMPORANEIDAD_SPEC
from .sancion_inexactitud import SPEC as _SANCION_INEXACTITUD_SPEC
from .soporte_factura import SPEC as _SOPORTE_FACTURA_SPEC
from .tarifa_general_pj import SPEC as _TARIFA_GENERAL_PJ_SPEC
from .zona_franca import SPEC as _ZONA_FRANCA_SPEC


# Order matters: the union semantics in `_active_case_keywords`
# and the planner anchor-merge ordering both walk this tuple
# top-down. v15.5 → v16 ordering preserves the v15.5 6 topics
# first, then appends v16 batch-1 (5 RENTA_DEDUCCIONES) topics,
# then v16 batch-2 (10 mixed RENTA_DEDUCCIONES/DESCUENTOS/TARIFAS/
# PROCEDIMIENTO) topics in §9 priority order.
CASE_REGISTRY: tuple[CaseSpec, ...] = (
    # v15.5 baseline (6 topics)
    _GMF_SPEC,
    _ICA_SPEC,
    _PREDIAL_SPEC,
    _INTERESES_SPEC,
    _LEASING_SPEC,
    _PRIMER_EMPLEO_SPEC,
    # v16 batch-1 (RENTA_DEDUCCIONES)
    # NOTE: rte_esal (batch 5) precedes donaciones because the latter's
    # markers ("esal", "fundación", "régimen tributario especial") would
    # otherwise intercept RTE-calification questions.
    _DEPRECIACION_SPEC,
    _ATENCIONES_SPEC,
    _CARTERA_SPEC,
    _RTE_ESAL_SPEC,
    _DONACIONES_SPEC,
    _PAGOS_EFECTIVO_SPEC,
    # v16 batch-2 (10 topics, mixed categories).
    # Order: most-specific tarifa topics (dividendos / RST / zona franca)
    # BEFORE the generic tarifa_general_pj — the first matching row in
    # CASE_REGISTRY wins anchor emission, so a "tarifa de zona franca"
    # question would otherwise be intercepted by the broader 35 % PJ row.
    _EXONERACION_PARAFISCALES_SPEC,
    _IVA_ACTIVOS_FIJOS_SPEC,
    _CTEI_DESCUENTO_SPEC,
    _DIVIDENDOS_PN_SPEC,
    _RST_TARIFAS_SPEC,
    _ZONA_FRANCA_SPEC,
    _TARIFA_GENERAL_PJ_SPEC,
    _BENEFICIO_AUDITORIA_SPEC,
    _FIRMEZA_DECLARACIONES_SPEC,
    _DEVOLUCION_SALDOS_SPEC,
    # v16 batch-3 (10 topics: 3 sanciones + notificaciones + 5 IVA + retención salarios).
    # IVA-specific topics come BEFORE the broader iva_hecho_generador so
    # questions about "responsables", "descontable", "devolución",
    # "excluidos vs exentos" don't get intercepted by the generic 420 cue.
    _SANCION_EXTEMPORANEIDAD_SPEC,
    _SANCION_CORRECCION_SPEC,
    _SANCION_INEXACTITUD_SPEC,
    _NOTIFICACIONES_ELECTRONICAS_SPEC,
    _IVA_RESPONSABLES_SPEC,
    _IVA_DESCONTABLE_SPEC,
    _IVA_DEVOLUCION_SPEC,
    _IVA_EXCLUIDOS_EXENTOS_SPEC,
    _IVA_HECHO_GENERADOR_SPEC,
    _RETENCION_SALARIOS_SPEC,
    # v16 batch-4 (10 topics: retención servicios + procedimiento + soporte FE +
    # compensación pérdidas + exógena 1001/1003/1005/1007/umbrales + NIIF
    # conciliación). Specific-form topics before generic 631 anchor.
    _RETENCION_SERVICIOS_SPEC,
    _ANTICIPO_RENTA_SPEC,
    _SOPORTE_FACTURA_SPEC,
    _COMPENSACION_PERDIDAS_SPEC,
    # impuesto_diferido (batch 5) precedes niif_conciliacion_fiscal because
    # the latter's "impuesto diferido" / "diferencia temporaria" markers
    # would otherwise intercept the dedicated NIC 12 detector.
    _IMPUESTO_DIFERIDO_SPEC,
    _NIIF_CONCILIACION_FISCAL_SPEC,
    _EXOGENA_1001_SPEC,
    _EXOGENA_1003_SPEC,
    _EXOGENA_1005_SPEC,
    _EXOGENA_1007_SPEC,
    _EXOGENA_UMBRALES_SPEC,
    # v16 batch-5 (10 topics: Tier 2 + NIIF). Two specs (_RTE_ESAL_SPEC and
    # _IMPUESTO_DIFERIDO_SPEC) are registered earlier above to win over
    # overlapping batch-1 / batch-4 detectors; the remaining eight live here.
    _INC_CONSUMO_SPEC,
    _PRECIOS_TRANSFERENCIA_SPEC,
    _DIVIDENDOS_NO_GRAVADOS_SPEC,
    _CAPITALIZACION_UTILIDADES_SPEC,
    _APORTES_VOLUNTARIOS_PENSION_SPEC,
    _RENTA_CEDULAR_PN_SPEC,
    _CLAUSULA_ANTIABUSO_SPEC,
    _NIIF_INGRESOS_SPEC,
    # v17 b1+b2+b3 (2026-05-15) — labor / nómina block (9 topics) + b3+
    # tail addition `aportes_proporcionales_tiempo_parcial` (38th topic).
    # Order: specific anchors BEFORE the broad liquidacion_mensual_nomina.
    # Per fix_v17_may §3.1 step 5: salario_integral, DSPNE, PILA, UGPP,
    # contratos, prestaciones, terminación must precede liquidacion_mensual
    # so their queries are not intercepted by the broader nómina detector.
    # `aportes_proporcionales_tiempo_parcial` is the most niche labor case
    # (empleada doméstica por días) and is registered FIRST in the v17 block
    # so it wins over PILA, salario_integral and mensual nómina when a
    # tiempo-parcial / por-días marker fires.
    _APORTES_PROPORCIONALES_TIEMPO_PARCIAL_SPEC,
    _SALARIO_INTEGRAL_SPEC,
    _NOMINA_ELECTRONICA_DSPNE_SPEC,
    _PILA_APORTES_SPEC,
    _UGPP_FISCALIZACION_SPEC,
    _CONTRATO_APRENDIZAJE_SENA_SPEC,
    _CONTRATO_PRESTACION_VS_LABORAL_SPEC,
    _PRESTACIONES_SOCIALES_SPEC,
    _LIQUIDACION_TERMINACION_SPEC,
    _LIQUIDACION_MENSUAL_NOMINA_SPEC,
)


__all__ = ["CaseSpec", "CASE_REGISTRY"]
