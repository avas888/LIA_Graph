"""v15.5 (2026-05-14) — case detectors for case-bullet topics.

Each `is_<topic>_deduction_case` function takes a *normalized* request
message (lowercased, accent-stripped, whitespace-collapsed) and returns
True when the request is about that topic.

Extracted from `answer_synthesis_helpers.py` so `planner.py` can
consume them without creating a circular import
(`planner → helpers → support → planner`). The detectors here are
pure — no imports from the answer-* / support-* modules — which keeps
them safe to use from both the planner layer and the synthesis layer.

Adding a new case-bullet topic:
1. Add `is_<topic>_case` here.
2. Add 5+ case bullets in `answer_synthesis_sections.build_recommendations`.
3. Add a row in `planner._CASE_ANCHOR_REGISTRY` + (optionally)
   `planner._CASE_SEARCH_QUERIES`.
4. Add a whitelist in `answer_synthesis_sections._<topic>_CASE_KEYWORDS`
   and append it to `_active_case_keywords`.
"""

from __future__ import annotations

import re


def is_gmf_deduction_case(normalized_message: str) -> bool:
    """Detect GMF / 4×1000 / cuatro-por-mil queries."""
    if not normalized_message:
        return False
    markers = (
        "gmf",
        "4x1000",
        "4 x 1000",
        "cuatro por mil",
        "gravamen a los movimientos financieros",
        "gravamen movimientos financieros",
    )
    return any(marker in normalized_message for marker in markers)


def is_ica_deduction_case(normalized_message: str) -> bool:
    """Detect ICA / industria y comercio queries.

    Uses word-boundary check on the bare `ica` token to avoid matching
    `indica` / `publicar` / `indicador` etc.
    """
    if not normalized_message:
        return False
    if any(
        marker in normalized_message
        for marker in (
            "industria y comercio",
            "avisos y tableros",
            "impuesto de industria",
        )
    ):
        return True
    return bool(re.search(r"\bica\b", normalized_message))


def is_predial_deduction_case(normalized_message: str) -> bool:
    """Detect predial deduction queries."""
    if not normalized_message:
        return False
    markers = (
        "predial",
        "impuesto predial",
        "impuesto sobre el predio",
    )
    return any(marker in normalized_message for marker in markers)


def is_intereses_deduction_case(normalized_message: str) -> bool:
    """Detect intereses + subcapitalización queries."""
    if not normalized_message:
        return False
    markers = (
        "subcapitalización",
        "subcapitalizacion",
        "deducción de intereses",
        "deduccion de intereses",
        "intereses deducibles",
        "intereses pagados",
        "límite de intereses",
        "limite de intereses",
        "art. 117",
        "art. 118-1",
        "art 117",
        "art 118-1",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    if "intereses" in normalized_message and any(
        deduct in normalized_message
        for deduct in ("deducible", "deducción", "deduccion", "deducir")
    ):
        return True
    return False


def is_leasing_deduction_case(normalized_message: str) -> bool:
    """Detect leasing deduction queries."""
    if not normalized_message:
        return False
    markers = (
        "leasing",
        "arrendamiento financiero",
        "art. 127-1",
        "art 127-1",
    )
    return any(marker in normalized_message for marker in markers)


def is_primer_empleo_deduction_case(normalized_message: str) -> bool:
    """Detect deducción por primer empleo (art. 108-5 ET)."""
    if not normalized_message:
        return False
    markers = (
        "primer empleo",
        "art. 108-5",
        "art 108-5",
        "deducción del 120%",
        "deduccion del 120%",
        "120% del salario",
        "menores de 28",
        "jóvenes 18",
        "jovenes 18",
    )
    return any(marker in normalized_message for marker in markers)


def is_depreciacion_case(normalized_message: str) -> bool:
    """v16 (2026-05-14) — depreciación fiscal (art. 137 ET).

    Source playbook: knowledge_base/CORE ya Arriba/RENTA/PLAYBOOKS/
    playbook_renta_depreciacion_fiscal.md.
    """
    if not normalized_message:
        return False
    markers = (
        "depreciación",
        "depreciacion",
        "vida util fiscal",
        "vida útil fiscal",
        "vida útil",
        "vida util",
        "tasa de depreciación",
        "tasa de depreciacion",
        "art. 137",
        "art 137",
        "art. 134",
        "art 134",
        "deprecio",
        "deprecia",
        "depreciar",
    )
    return any(marker in normalized_message for marker in markers)


def is_atenciones_case(normalized_message: str) -> bool:
    """v16 (2026-05-14) — atenciones a clientes/proveedores/empleados (art. 107-1 ET).

    Source playbook: knowledge_base/CORE ya Arriba/RENTA/PLAYBOOKS/
    playbook_renta_atenciones_clientes_empleados.md.
    """
    if not normalized_message:
        return False
    markers = (
        "atenciones",
        "atención a clientes",
        "atencion a clientes",
        "art. 107-1",
        "art 107-1",
        "regalos a clientes",
        "regalos a empleados",
        "canastas navideñas",
        "canastas navidenas",
        "fiesta de fin de año",
        "fiesta de fin de ano",
        "aguinaldo",
        "aguinaldos",
        "agasajo",
        "cortesías",
        "cortesias",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    # Phrase pattern: "1% atenciones" / "1 % atenciones" / "tope atenciones"
    if "atencion" in normalized_message or "atención" in normalized_message:
        if any(
            cue in normalized_message
            for cue in ("1%", "1 %", "tope", "limit", "deduc")
        ):
            return True
    return False


def is_cartera_dificil_recaudo_case(normalized_message: str) -> bool:
    """v16 (2026-05-14) — provisión y castigo de cartera (arts. 145 y 146 ET).

    Source playbook: knowledge_base/CORE ya Arriba/RENTA/PLAYBOOKS/
    playbook_renta_cartera_dificil_recaudo.md.
    """
    if not normalized_message:
        return False
    markers = (
        "cartera de difícil",
        "cartera de dificil",
        "cartera difícil",
        "cartera dificil",
        "cartera incobrable",
        "cartera vencida",
        "provisión de cartera",
        "provision de cartera",
        "castigo de cartera",
        "castigar cartera",
        "castigar la cartera",
        "deudas de difícil cobro",
        "deudas de dificil cobro",
        "deudas manifiestamente perdidas",
        "art. 145",
        "art 145",
        "art. 146",
        "art 146",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    if "cartera" in normalized_message and any(
        cue in normalized_message
        for cue in (
            "provis",
            "castig",
            "deteriorad",
            "incobrable",
            "perdid",
            "33%",
            "67%",
            "100%",
        )
    ):
        return True
    return False


def is_donaciones_case(normalized_message: str) -> bool:
    """v16 (2026-05-14) — donaciones a ESAL/RTE (arts. 125 y 257 ET).

    Source playbook: knowledge_base/CORE ya Arriba/RENTA/PLAYBOOKS/
    playbook_renta_donaciones_deducibles.md.

    v18 b1 Issue D (2026-05-15): "esal" demoted to word-boundary
    regex so "desalarización" / "desalarizacion" UGPP-related
    questions stop misfiring this detector (same pattern as
    is_rte_esal_case in case_detectors_b5.py).
    """
    if not normalized_message:
        return False
    long_markers = (
        "donación",
        "donacion",
        "donaciones",
        "donar",
        "donado",
        "donante",
        "art. 125",
        "art 125",
        "art. 257",
        "art 257",
        "art. 125-1",
        "art. 125-2",
        "art. 125-3",
        "régimen tributario especial",
        "regimen tributario especial",
        "entidad sin ánimo de lucro",
        "entidad sin animo de lucro",
        "fundación",
        "fundacion",
    )
    if any(marker in normalized_message for marker in long_markers):
        return True
    return bool(re.search(r"\besal\b", normalized_message))


def is_exoneracion_parafiscales_case(normalized_message: str) -> bool:
    """v16 (2026-05-14) — exoneración de parafiscales (art. 114-1 ET).

    Source playbook: knowledge_base/CORE ya Arriba/RENTA/PLAYBOOKS/
    playbook_renta_exoneracion_parafiscales_114_1.md.
    """
    if not normalized_message:
        return False
    markers = (
        "exoneración de aportes",
        "exoneracion de aportes",
        "exoneración de parafiscales",
        "exoneracion de parafiscales",
        "exonerar parafiscales",
        "exonerar aportes",
        "art. 114-1",
        "art 114-1",
        "114-1",
        "13,5%",
        "13.5%",
        "sena icbf",
        "icbf sena",
        "10 smmlv",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    if "parafiscales" in normalized_message and any(
        cue in normalized_message
        for cue in ("exoner", "no paga", "no pago", "10 smmlv", "<10")
    ):
        return True
    return False


def is_iva_activos_fijos_case(normalized_message: str) -> bool:
    """v16 (2026-05-14) — descuento del IVA en activos fijos productivos (art. 258-1 ET)."""
    if not normalized_message:
        return False
    markers = (
        "art. 258-1",
        "art 258-1",
        "258-1",
        "iva en activos fijos",
        "iva de activos fijos",
        "iva activos fijos",
        "activo fijo real productivo",
        "activos fijos reales productivos",
        "iva maquinaria",
        "iva en maquinaria",
        "descuento del iva",
        "descontar el iva",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    if "iva" in normalized_message and any(
        cue in normalized_message
        for cue in (
            "maquinaria",
            "activo fijo",
            "activos fijos",
            "descuento de renta",
            "descontar en renta",
        )
    ):
        return True
    return False


def is_ctei_descuento_case(normalized_message: str) -> bool:
    """v16 (2026-05-14) — descuento CTeI Minciencias (art. 256 ET)."""
    if not normalized_message:
        return False
    markers = (
        "ctei",
        "i+d",
        "i+d+i",
        "investigación, desarrollo",
        "investigacion, desarrollo",
        "investigación y desarrollo",
        "investigacion y desarrollo",
        "innovación tecnológica",
        "innovacion tecnologica",
        "minciencias",
        "cnbt",
        "art. 256",
        "art 256",
        "ciencia, tecnología",
        "ciencia, tecnologia",
        "ciencia tecnologia e innovacion",
        "ciencia tecnología e innovación",
    )
    return any(marker in normalized_message for marker in markers)


def is_tarifa_general_pj_case(normalized_message: str) -> bool:
    """v16 (2026-05-14) — tarifa general PJ 35 % (art. 240 ET)."""
    if not normalized_message:
        return False
    markers = (
        "tarifa general",
        "tarifa de renta",
        "tarifa del impuesto sobre la renta",
        "art. 240",
        "art 240",
        "sobretasa",
        "tarifa 35%",
        "tarifa 35 %",
        "tarifa del 35%",
        "tarifa del 35 %",
        "35 %",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    if "tarifa" in normalized_message and any(
        cue in normalized_message
        for cue in ("persona juridica", "persona jurídica", "sas", "sociedad", "pj")
    ):
        return True
    return False


def is_dividendos_pn_case(normalized_message: str) -> bool:
    """v16 (2026-05-14) — tarifa dividendos PN residentes (art. 242 ET)."""
    if not normalized_message:
        return False
    markers = (
        "dividendos",
        "dividendo",
        "art. 242",
        "art 242",
        "art. 254-1",
        "art 254-1",
        "254-1",
        "1.090 uvt",
        "1090 uvt",
        "descuento del 19%",
        "descuento del 19 %",
        "participaciones",
    )
    return any(marker in normalized_message for marker in markers)


def is_rst_tarifas_case(normalized_message: str) -> bool:
    """v16 (2026-05-14) — tarifas Régimen Simple (art. 908 ET)."""
    if not normalized_message:
        return False
    markers = (
        "régimen simple",
        "regimen simple",
        "rst",
        "art. 908",
        "art 908",
        "tarifa simple",
        "tarifas del simple",
        "tarifas rst",
        "anticipo bimestral",
        "anticipos bimestrales",
        "grupo 1 rst",
        "grupo 2 rst",
        "grupo 3 rst",
        "grupo 4 rst",
        "formulario 2593",
        "formulario 260",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    if "simple" in normalized_message and any(
        cue in normalized_message
        for cue in ("tarifa", "régimen", "regimen", "tributacion", "tributación")
    ):
        return True
    return False


def is_zona_franca_case(normalized_message: str) -> bool:
    """v16 (2026-05-14) — doble tarifa zona franca (art. 240-1 ET)."""
    if not normalized_message:
        return False
    markers = (
        "zona franca",
        "zonas francas",
        "usuario industrial",
        "usuarios industriales",
        "uib",
        "uis",
        "art. 240-1",
        "art 240-1",
        "240-1",
        "plan de internacionalización",
        "plan de internacionalizacion",
        "tarifa 20%",
        "tarifa del 20%",
    )
    return any(marker in normalized_message for marker in markers)


def is_beneficio_auditoria_case(normalized_message: str) -> bool:
    """v16 (2026-05-14) — beneficio de auditoría (art. 689-3 ET)."""
    if not normalized_message:
        return False
    markers = (
        "beneficio de auditoría",
        "beneficio de auditoria",
        "beneficio auditoría",
        "beneficio auditoria",
        "art. 689-3",
        "art 689-3",
        "689-3",
        "firmeza reducida",
        "firmeza 6 meses",
        "firmeza 12 meses",
        "incremento del 35%",
        "incremento del 25%",
        "incremento del impuesto neto",
    )
    return any(marker in normalized_message for marker in markers)


def is_firmeza_declaraciones_case(normalized_message: str) -> bool:
    """v16 (2026-05-14) — firmeza ordinaria (art. 714 ET)."""
    if not normalized_message:
        return False
    markers = (
        "art. 714",
        "art 714",
        "firmeza ordinaria",
        "firmeza de la declaración",
        "firmeza de la declaracion",
        "firmeza de las declaraciones",
        "firmeza declaración",
        "firmeza declaracion",
        "queda en firme",
        "3 años de firmeza",
        "tres años de firmeza",
        "5 años de firmeza",
        "cinco años de firmeza",
        "requerimiento especial",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    if "firmeza" in normalized_message and any(
        cue in normalized_message
        for cue in ("declar", "renta", "iva", "retención", "retencion", "años", "anos")
    ):
        return True
    return False


def is_devolucion_saldos_favor_case(normalized_message: str) -> bool:
    """v16 (2026-05-14) — devolución de saldos a favor (art. 850 ET)."""
    if not normalized_message:
        return False
    markers = (
        "devolución de saldos",
        "devolucion de saldos",
        "devolución del saldo",
        "devolucion del saldo",
        "saldo a favor",
        "saldos a favor",
        "art. 850",
        "art 850",
        "art. 855",
        "art 855",
        "art. 857",
        "compensación de saldos",
        "compensacion de saldos",
        "formulario 010",
        "devolución automática",
        "devolucion automatica",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    if "saldo" in normalized_message and any(
        cue in normalized_message
        for cue in ("devol", "compens", "favor")
    ):
        return True
    return False


# fix_v16 b3+b4 (2026-05-14) — batch-3 + batch-4 detectors live in a
# sibling module to keep this file under the 1000-LOC ceiling. Re-exported
# below so external call sites (planner, helpers, tests) continue to
# import ``from .case_detectors import is_X_case`` unchanged.
from .case_detectors_extensions import (  # noqa: F401  — b3 + b4 detectors
    is_anticipo_renta_case,
    is_compensacion_perdidas_fiscales_case,
    is_exogena_1001_case,
    is_exogena_1003_case,
    is_exogena_1005_case,
    is_exogena_1007_case,
    is_exogena_umbrales_case,
    is_iva_descontable_case,
    is_iva_devolucion_case,
    is_iva_excluidos_exentos_case,
    is_iva_hecho_generador_case,
    is_iva_responsables_case,
    is_niif_conciliacion_fiscal_case,
    is_notificaciones_electronicas_case,
    is_retencion_salarios_case,
    is_retencion_servicios_case,
    is_sancion_correccion_case,
    is_sancion_extemporaneidad_case,
    is_sancion_inexactitud_case,
    is_soporte_factura_case,
)
from .case_detectors_b5 import (  # noqa: F401  — b5 + v17 b1/b2/b3 detectors
    is_aportes_voluntarios_pension_case,
    is_capitalizacion_utilidades_case,
    is_clausula_antiabuso_case,
    is_contrato_aprendizaje_sena_case,
    is_contrato_prestacion_vs_laboral_case,
    is_dividendos_no_gravados_case,
    is_impuesto_diferido_case,
    is_inc_consumo_case,
    is_liquidacion_mensual_nomina_case,
    is_liquidacion_terminacion_case,
    is_niif_ingresos_case,
    is_nomina_electronica_dspne_case,
    is_pila_aportes_case,
    is_precios_transferencia_case,
    is_prestaciones_sociales_case,
    is_renta_cedular_pn_case,
    is_rte_esal_case,
    is_salario_integral_case,
    is_ugpp_fiscalizacion_case,
)
from .case_detectors_b6 import (  # noqa: F401  — v17 b3+ tail (tiempo parcial)
    is_aportes_proporcionales_tiempo_parcial_case,
)




def is_pagos_efectivo_case(normalized_message: str) -> bool:
    """v16 (2026-05-14) — bancarización / pagos en efectivo (art. 771-5 ET).

    Source playbook: knowledge_base/CORE ya Arriba/RENTA/PLAYBOOKS/
    playbook_renta_limitacion_pagos_efectivo.md.
    """
    if not normalized_message:
        return False
    markers = (
        "bancarización",
        "bancarizacion",
        "bancarizar",
        "bancarizado",
        "pagos en efectivo",
        "pago en efectivo",
        "medios de pago",
        "art. 771-5",
        "art 771-5",
        "771-5",
        "limitación a pagos",
        "limitacion a pagos",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    if "efectivo" in normalized_message and any(
        cue in normalized_message
        for cue in (
            "deduc",
            "deducir",
            "deducible",
            "tope",
            "límite",
            "limite",
            "100 uvt",
            "35%",
            "40%",
        )
    ):
        return True
    return False


__all__ = [
    "is_anticipo_renta_case",
    "is_aportes_proporcionales_tiempo_parcial_case",
    "is_atenciones_case",
    "is_beneficio_auditoria_case",
    "is_cartera_dificil_recaudo_case",
    "is_compensacion_perdidas_fiscales_case",
    "is_contrato_aprendizaje_sena_case",
    "is_contrato_prestacion_vs_laboral_case",
    "is_ctei_descuento_case",
    "is_depreciacion_case",
    "is_devolucion_saldos_favor_case",
    "is_dividendos_pn_case",
    "is_donaciones_case",
    "is_exogena_1001_case",
    "is_exogena_1003_case",
    "is_exogena_1005_case",
    "is_exogena_1007_case",
    "is_exogena_umbrales_case",
    "is_exoneracion_parafiscales_case",
    "is_firmeza_declaraciones_case",
    "is_gmf_deduction_case",
    "is_ica_deduction_case",
    "is_intereses_deduction_case",
    "is_iva_activos_fijos_case",
    "is_iva_descontable_case",
    "is_iva_devolucion_case",
    "is_iva_excluidos_exentos_case",
    "is_iva_hecho_generador_case",
    "is_iva_responsables_case",
    "is_leasing_deduction_case",
    "is_liquidacion_mensual_nomina_case",
    "is_liquidacion_terminacion_case",
    "is_niif_conciliacion_fiscal_case",
    "is_nomina_electronica_dspne_case",
    "is_notificaciones_electronicas_case",
    "is_pagos_efectivo_case",
    "is_pila_aportes_case",
    "is_predial_deduction_case",
    "is_prestaciones_sociales_case",
    "is_primer_empleo_deduction_case",
    "is_retencion_salarios_case",
    "is_retencion_servicios_case",
    "is_rst_tarifas_case",
    "is_salario_integral_case",
    "is_sancion_correccion_case",
    "is_sancion_extemporaneidad_case",
    "is_sancion_inexactitud_case",
    "is_soporte_factura_case",
    "is_tarifa_general_pj_case",
    "is_ugpp_fiscalizacion_case",
    "is_zona_franca_case",
]
