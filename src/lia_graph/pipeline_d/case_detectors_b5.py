"""v16 b5 (2026-05-14) — Tier 2 + NIIF case detectors (10 topics).

Extracted from ``case_detectors_extensions.py`` to keep that file under
the 1000-LOC ceiling per the divide-and-conquer rule. Re-exported by
``case_detectors`` (the facade) so existing call sites continue to use
``from .case_detectors import is_<topic>_case`` unchanged.

Detectors here remain **pure** — only ``re`` and types. Adding imports
from any ``answer_*`` / ``planner`` module reintroduces the circular
import that v15.5 broke.
"""
from __future__ import annotations

import re


def is_inc_consumo_case(normalized_message: str) -> bool:
    """v16 b5 — Impuesto Nacional al Consumo (art. 512-1 ET)."""
    if not normalized_message:
        return False
    markers = (
        "impuesto al consumo",
        "impuesto nacional al consumo",
        "art. 512-1", "art 512-1", "512-1",
        "art. 512-2", "art 512-2",
        "art. 512-4", "art 512-4",
        "art. 512-9", "art 512-9",
        "art. 512-15", "art 512-15",
        "expendio de comidas",
        "restaurantes y bares",
        "bolsas plásticas", "bolsas plasticas",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    if "consumo" in normalized_message and (
        "restaurante" in normalized_message
        or "bar" in normalized_message
        or "8%" in normalized_message
        or "vehiculo" in normalized_message
        or "vehículo" in normalized_message
    ):
        return True
    if re.search(r"\binc\b", normalized_message) and (
        "iva" in normalized_message
        or "costo" in normalized_message
        or "descuent" in normalized_message
        or "tarifa" in normalized_message
        or "restaurante" in normalized_message
        or "expendio" in normalized_message
    ):
        return True
    return False


def is_precios_transferencia_case(normalized_message: str) -> bool:
    """v16 b5 — precios de transferencia (arts. 260-1 a 260-11 ET)."""
    if not normalized_message:
        return False
    markers = (
        "precios de transferencia",
        "art. 260-1", "art 260-1",
        "art. 260-2", "art 260-2",
        "art. 260-3", "art 260-3",
        "art. 260-5", "art 260-5",
        "art. 260-7", "art 260-7",
        "art. 260-9", "art 260-9",
        "art. 260-11", "art 260-11",
        "260-1", "260-3", "260-5",
        "f120", "f1125", "f1729",
        "formato 120", "formato 1125", "formato 1729",
        "jurisdicciones no cooperantes",
        "paraísos fiscales", "paraisos fiscales",
        "vinculados del exterior",
        "informe local", "informe maestro",
    )
    return any(marker in normalized_message for marker in markers)


def is_dividendos_no_gravados_case(normalized_message: str) -> bool:
    """v16 b5 — dividendos no gravados (art. 49 ET)."""
    if not normalized_message:
        return False
    markers = (
        "dividendo no gravado",
        "dividendos no gravados",
        "dividendos gravados",
        "fórmula art. 49", "formula art 49",
        "fórmula del art. 49", "formula del art 49",
        "art. 49 et", "art 49 et",
        "umng",
        "utilidad máxima no gravada", "utilidad maxima no gravada",
        "certificado de dividendos",
        "decreto 1103 de 2023",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    if "dividendo" in normalized_message and (
        "no gravado" in normalized_message
        or "no gravados" in normalized_message
        or "art. 49" in normalized_message
        or "art 49" in normalized_message
        or "fórmula" in normalized_message
        or "formula" in normalized_message
    ):
        return True
    return False


def is_capitalizacion_utilidades_case(normalized_message: str) -> bool:
    """v16 b5 — capitalización de utilidades (art. 36-3 ET)."""
    if not normalized_message:
        return False
    markers = (
        "capitalización de utilidades", "capitalizacion de utilidades",
        "capitalizar utilidades",
        "capitalizar la utilidad",
        "art. 36-3", "art 36-3", "36-3",
        "dividendo en acciones",
        "reserva legal capitalizar",
        "prima en colocación capitalizada", "prima en colocacion capitalizada",
        "revalorización del patrimonio", "revalorizacion del patrimonio",
    )
    return any(marker in normalized_message for marker in markers)


def is_aportes_voluntarios_pension_case(normalized_message: str) -> bool:
    """v16 b5 — aportes voluntarios pensión + AFC (arts. 126-1, 126-4 ET)."""
    if not normalized_message:
        return False
    markers = (
        "aportes voluntarios",
        "aporte voluntario",
        "pensión voluntaria", "pension voluntaria",
        "fvp",
        "fondo de pensiones voluntarias",
        "afc",
        "ahorro fomento construcción", "ahorro fomento construccion",
        "ahorro para fomento de la construcción", "ahorro para fomento de la construccion",
        "avc",
        "ahorro voluntario contractual",
        "art. 126-1", "art 126-1", "126-1",
        "art. 126-4", "art 126-4", "126-4",
        "3.800 uvt", "3800 uvt",
    )
    return any(marker in normalized_message for marker in markers)


def is_renta_cedular_pn_case(normalized_message: str) -> bool:
    """v16 b5 — renta cedular PN (arts. 330 a 343 ET)."""
    if not normalized_message:
        return False
    markers = (
        "renta cedular",
        "cédula general", "cedula general",
        "cédula pensiones", "cedula pensiones",
        "cédula dividendos", "cedula dividendos",
        "cédula de trabajo", "cedula de trabajo",
        "cédula de capital", "cedula de capital",
        "cédula no laboral", "cedula no laboral",
        "art. 330", "art 330",
        "art. 335", "art 335",
        "art. 336", "art 336",
        "art. 337", "art 337",
        "art. 343", "art 343",
        "1.340 uvt", "1340 uvt",
        "5.040 uvt", "5040 uvt",
        "tabla 241", "tabla del 241",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    if ("renta" in normalized_message or "renta líquida" in normalized_message) and (
        "cedular" in normalized_message or "cédula" in normalized_message or "cedula" in normalized_message
    ):
        return True
    return False


def is_rte_esal_case(normalized_message: str) -> bool:
    """v16 b5 — RTE para ESAL (art. 19 ET).

    Veto on "donación / donaciones" — those questions go to the
    donaciones detector (arts. 125 / 257 ET), even when an ESAL is
    mentioned as the beneficiary. Short tokens ("rte", "esal") use
    word-boundary regex to avoid matches inside "soporte", "rotate",
    etc.
    """
    if not normalized_message:
        return False
    if "donaci" in normalized_message or "donar" in normalized_message:
        return False
    long_markers = (
        "régimen tributario especial", "regimen tributario especial",
        "fundación", "fundacion",
        "asociación sin ánimo de lucro", "asociacion sin animo de lucro",
        "entidad sin ánimo de lucro", "entidad sin animo de lucro",
        "corporación sin ánimo de lucro", "corporacion sin animo de lucro",
        "art. 19 et", "art 19 et",
        "art. 356", "art 356", "356-1", "356-3",
        "art. 357", "art 357",
        "art. 358", "art 358",
        "art. 359", "art 359",
        "art. 364-5", "art 364-5",
        "beneficio neto",
        "actividades meritorias",
        "decreto 2150 de 2017",
        "permanencia rte",
        "calificación rte", "calificacion rte",
    )
    if any(marker in normalized_message for marker in long_markers):
        return True
    return bool(re.search(r"\b(rte|esal)\b", normalized_message))


def is_clausula_antiabuso_case(normalized_message: str) -> bool:
    """v16 b5 — cláusula antiabuso (arts. 869, 869-1, 869-2 ET)."""
    if not normalized_message:
        return False
    markers = (
        "cláusula antiabuso", "clausula antiabuso",
        "abuso en materia tributaria",
        "abuso tributario",
        "recaracterización", "recaracterizacion",
        "recaracterizar",
        "art. 869", "art 869",
        "art. 869-1", "art 869-1",
        "art. 869-2", "art 869-2",
        "869-1", "869-2",
        "gaar",
        "comité de fiscalización", "comite de fiscalizacion",
        "negocios artificiosos",
    )
    return any(marker in normalized_message for marker in markers)


def is_impuesto_diferido_case(normalized_message: str) -> bool:
    """v16 b5 — impuesto diferido (NIC 12 / Sección 29)."""
    if not normalized_message:
        return False
    markers = (
        "impuesto diferido",
        "activo por impuesto diferido",
        "pasivo por impuesto diferido",
        "activo diferido",
        "pasivo diferido",
        "nic 12",
        "sección 29 niif", "seccion 29 niif",
        "ias 12",
        "diferencia temporaria imponible",
        "diferencia temporaria deducible",
        "dti ", "dtd ",
        "método del pasivo basado en balance", "metodo del pasivo basado en balance",
    )
    return any(marker in normalized_message for marker in markers)


def is_niif_ingresos_case(normalized_message: str) -> bool:
    """v16 b5 — reconocimiento ingresos NIIF 15 vs art. 28 ET."""
    if not normalized_message:
        return False
    markers = (
        "niif 15",
        "ifrs 15",
        "sección 23 niif", "seccion 23 niif",
        "reconocimiento de ingresos",
        "realización del ingreso", "realizacion del ingreso",
        "realizacion del ingreso niif",
        "art. 28 et", "art 28 et",
        "numerales 1 a 6",
        "numeral 1 al 6",
        "art. 28 par", "art 28 par",
        "modelo de 5 pasos",
        "5 pasos niif",
        "transferencia de control",
        "obligaciones de desempeño", "obligaciones de desempeno",
        "método de avance", "metodo de avance",
        "art. 21-1 et", "art 21-1 et",
    )
    return any(marker in normalized_message for marker in markers)


# ---------------------------------------------------------------------------
# v17 b1 + b2 + b3 (2026-05-15) — labor / nómina detectors.
#
# Per fix_v17_may.md §1, these wire the Lane-A-only playbooks that
# fix_v16_may + corpusfix_v1 already shipped on disk + in cloud Supabase.
# The detectors live here to keep case_detectors_extensions.py below the
# 1000-LOC ceiling (it's at 552 today). When this file crosses ~800 LOC,
# create case_detectors_b6.py per the granular-edits memory.
# ---------------------------------------------------------------------------


def is_salario_integral_case(normalized_message: str) -> bool:
    """v17 b3 — salario integral (art. 132 CST + art. 18 Ley 50/1990).

    Order-sensitive: registered BEFORE liquidacion_mensual_nomina so a
    "salario integral" question doesn't get intercepted by the broader
    nómina-mensual detector.
    """
    if not normalized_message:
        return False
    markers = (
        "salario integral",
        "ibc del 70",
        "ibc 70%", "ibc 70 %",
        "factor prestacional",
        "13 smmlv",
        "10 smmlv",
        "art. 132 cst", "art 132 cst", "132 cst",
        "art. 18 ley 50", "art 18 ley 50",
        "ley 50 de 1990 art 18", "ley 50 de 1990 art. 18",
        "art. 49 ley 789", "art 49 ley 789",
    )
    return any(marker in normalized_message for marker in markers)


def is_nomina_electronica_dspne_case(normalized_message: str) -> bool:
    """v17 b2 — Documento Soporte de Pago de Nómina Electrónica (Res. DIAN 000013/2021).

    Order-sensitive: registered BEFORE liquidacion_mensual_nomina so a
    "nómina electrónica" question doesn't drop into the generic nómina
    detector first.
    """
    if not normalized_message:
        return False
    markers = (
        "nomina electronica", "nómina electrónica",
        "nomina electrónica", "nómina electronica",
        "dspne",
        "documento soporte de pago de nomina",
        "documento soporte de pago de nómina",
        "documento soporte nomina", "documento soporte nómina",
        "resolución 000013 de 2021", "resolucion 000013 de 2021",
        "res. dian 000013", "res dian 000013",
        "000013 de 2021",
        "resolución 000037 de 2021", "resolucion 000037 de 2021",
        "cune",
        "niesn",
        "nota de ajuste de nomina", "nota de ajuste de nómina",
    )
    return any(marker in normalized_message for marker in markers)


def is_pila_aportes_case(normalized_message: str) -> bool:
    """v17 b2 — PILA (Planilla Integrada de Liquidación de Aportes, Decreto 1990/2016)."""
    if not normalized_message:
        return False
    markers = (
        "pila",
        "planilla integrada",
        "planilla integrada de liquidación", "planilla integrada de liquidacion",
        "planilla de aportes",
        "decreto 1990 de 2016", "decreto 1990/2016",
        "resolución 2388 de 2016", "resolucion 2388 de 2016",
        "decreto 1273 de 2018", "decreto 1273/2018",
        "operador pila",
        "operadores pila",
        "soi aportes",
        "mi planilla",
        "suaporte",
        "asopagos",
        "pila asistida",
        "planilla n", "planilla a",
        "ibc independiente",
        "ibc mínimo", "ibc minimo",
        "ibc máximo", "ibc maximo",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    # General-phrasing fallback: "planilla" + "aporte(s)" cue.
    if "planilla" in normalized_message and "aport" in normalized_message:
        return True
    return False


def is_ugpp_fiscalizacion_case(normalized_message: str) -> bool:
    """v17 b2 — UGPP fiscalización aportes (Ley 1607/2012 arts. 178-179)."""
    if not normalized_message:
        return False
    markers = (
        "ugpp",
        "fiscalización ugpp", "fiscalizacion ugpp",
        "requerimiento ugpp",
        "sanción ugpp", "sancion ugpp",
        "desalarización", "desalarizacion",
        "art. 178 ley 1607", "art 178 ley 1607",
        "art. 179 ley 1607", "art 179 ley 1607",
        "decreto 575 de 2013", "decreto 575/2013",
        "decreto 1601 de 2022", "decreto 1601/2022",
        "art. 30 ley 1393", "art 30 ley 1393",
        "ley 1393 de 2010 art 30",
        "40% no salarial", "40 % no salarial",
        "40 por ciento no salarial",
        "presunción de costos", "presuncion de costos",
        "elusión de aportes", "elusion de aportes",
        "evasión de aportes", "evasion de aportes",
    )
    return any(marker in normalized_message for marker in markers)


def is_prestaciones_sociales_case(normalized_message: str) -> bool:
    """v17 b1 — prestaciones sociales (cesantías + intereses + prima + vacaciones).

    Anchored at CST 249 / 306 / 186 (cubiertas vía 108 + 387 en ET para gate).
    """
    if not normalized_message:
        return False
    markers = (
        "cesantías", "cesantias",
        "intereses a las cesantías", "intereses a las cesantias",
        "intereses cesantías", "intereses cesantias",
        "prima de servicios",
        "prima legal",
        "vacaciones",
        "ley 50 de 1990 cesantías", "ley 50 de 1990 cesantias",
        "ley 1788 de 2016", "ley 1788/2016",
        "decreto 116 de 1976", "decreto 116/1976",
        "art. 249 cst", "art 249 cst",
        "art. 250 cst", "art 250 cst",
        "art. 306 cst", "art 306 cst",
        "art. 186 cst", "art 186 cst",
        "art. 189 cst", "art 189 cst",
        "consignación cesantías", "consignacion cesantias",
        "15 de febrero",
        "fondo de cesantías", "fondo de cesantias",
        "auxilio de transporte en prima",
        "auxilio de transporte en cesantías",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    if "cesant" in normalized_message and (
        "consignar" in normalized_message
        or "fondo" in normalized_message
        or "interes" in normalized_message
        or "ley 50" in normalized_message
    ):
        return True
    # General "prestaciones sociales" phrasing.
    if "prestaciones sociales" in normalized_message or "prestacion social" in normalized_message:
        return True
    # Plural "primas" + labor context (avoid colliding with "prima de riesgo"
    # in insurance contexts that don't mention salario/empleado).
    if ("primas" in normalized_message or "prima" in normalized_message) and (
        "servicios" in normalized_message
        or "empleado" in normalized_message
        or "trabajador" in normalized_message
        or "salario" in normalized_message
        or "nomina" in normalized_message
        or "junio" in normalized_message
        or "diciembre" in normalized_message
        # Payment-timing context: questions like "primas a tiempo",
        # "no pago las primas", "sanción por mora en primas".
        or "pago" in normalized_message
        or "pagar" in normalized_message
        or "tarde" in normalized_message
        or "plazo" in normalized_message
        or "mora" in normalized_message
    ):
        return True
    return False


def is_liquidacion_terminacion_case(normalized_message: str) -> bool:
    """v17 b1 — liquidación por terminación contrato laboral (CST 64 + 65)."""
    if not normalized_message:
        return False
    markers = (
        "liquidación final",
        "liquidacion final",
        "indemnización por despido", "indemnizacion por despido",
        "despido sin justa causa",
        "despido con justa causa",
        "art. 64 cst", "art 64 cst",
        "art. 65 cst", "art 65 cst",
        "art. 62 cst", "art 62 cst",
        "indemnización moratoria", "indemnizacion moratoria",
        "sanción moratoria 65", "sancion moratoria 65",
        "art. 401-3", "art 401-3", "401-3",
        "indemnización laboral retención", "indemnizacion laboral retencion",
        "30 días por primer año", "30 dias por primer año",
        "20 días por primer año", "20 dias por primer año",
        "renuncia voluntaria liquidación", "renuncia voluntaria liquidacion",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    # Spanish has two verb roots: "despid-" (despido/despidió/despide)
    # and "desped-" (despedí/despedido/despedida). Cover both.
    if ("despid" in normalized_message or "desped" in normalized_message) and (
        "indemniz" in normalized_message
        or "liquid" in normalized_message
        or "justa causa" in normalized_message
    ):
        return True
    if "terminación" in normalized_message or "terminacion" in normalized_message:
        if "contrato" in normalized_message and (
            "liquid" in normalized_message
            or "indemniz" in normalized_message
            or "anticip" in normalized_message
            or "termino fijo" in normalized_message
            or "término fijo" in normalized_message
            or "obra o labor" in normalized_message
        ):
            return True
    # "Termino fijo / obra o labor terminado anticipadamente" without the
    # noun "terminación".
    if ("termino fijo" in normalized_message or "término fijo" in normalized_message
            or "obra o labor" in normalized_message) and (
        "terminado" in normalized_message
        or "anticip" in normalized_message
        or "liquid" in normalized_message
        or "indemniz" in normalized_message
    ):
        return True
    return False


def is_contrato_prestacion_vs_laboral_case(normalized_message: str) -> bool:
    """v17 b3 — OPS vs contrato laboral / contrato realidad (art. 23 CST).

    Anchored at art. 383 ET (retención salarios para reclasificación).
    """
    if not normalized_message:
        return False
    markers = (
        "contrato realidad",
        "primacía de la realidad", "primacia de la realidad",
        "art. 23 cst", "art 23 cst",
        "art. 24 cst", "art 24 cst",
        "prestación de servicios vs laboral", "prestacion de servicios vs laboral",
        "ops vs laboral",
        "ops vs contrato laboral",
        "reclasificación contrato", "reclasificacion contrato",
        "reclasificación ugpp", "reclasificacion ugpp",
        "subordinación", "subordinacion",
        "test de subordinación", "test de subordinacion",
        "contratista reclasificado",
        "csj sl3771", "sl3771-2022",
        "csj sl2885", "sl2885-2020",
        "c-555 de 1994", "c-555/1994",
        "decreto 723 de 2013", "decreto 723/2013",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    if "prestación de servicios" in normalized_message or "prestacion de servicios" in normalized_message:
        if (
            "laboral" in normalized_message
            or "subordin" in normalized_message
            or "contrato realidad" in normalized_message
            or "reclasific" in normalized_message
            or "contratista" in normalized_message
            or "ugpp" in normalized_message
            or "riesgo" in normalized_message
        ):
            return True
    # "Contratista(s) por prestación de servicios" general framing.
    if "contratista" in normalized_message and (
        "prestación de servicios" in normalized_message
        or "prestacion de servicios" in normalized_message
        or "ops" in normalized_message
        or "honorario" in normalized_message
    ):
        return True
    return False


def is_contrato_aprendizaje_sena_case(normalized_message: str) -> bool:
    """v17 b3 — contrato de aprendizaje SENA (Ley 789/2002 arts. 30-34)."""
    if not normalized_message:
        return False
    markers = (
        "contrato de aprendizaje",
        "contrato aprendizaje",
        "aprendiz sena",
        "aprendices sena",
        "cuota sena",
        "cuota de aprendices",
        "cuota de aprendizaje",
        "monetización sena", "monetizacion sena",
        "monetizar aprendices",
        "apoyo de sostenimiento",
        "etapa lectiva",
        "etapa práctica", "etapa practica",
        "ley 789 de 2002", "ley 789/2002",
        "art. 30 ley 789", "art 30 ley 789",
        "art. 33 ley 789", "art 33 ley 789",
        "art. 34 ley 789", "art 34 ley 789",
        "decreto 933 de 2003", "decreto 933/2003",
        "50% smmlv", "50 % smmlv",
        "75% smmlv", "75 % smmlv",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    # Spanish singular/plural orthography: "aprendiz" (singular) is NOT a
    # substring of "aprendices" (plural — ends in -ices, not -iz). Use the
    # shared stem "aprendi" to catch both forms under accent-strip.
    if "aprendi" in normalized_message and (
        "sena" in normalized_message
        or "monetiz" in normalized_message
        or "lectiva" in normalized_message
        or "práctica" in normalized_message
        or "practica" in normalized_message
        or "cuota" in normalized_message
        or "ley 789" in normalized_message
    ):
        return True
    return False


def is_liquidacion_mensual_nomina_case(normalized_message: str) -> bool:
    """v17 b1 — liquidación mensual de nómina (CST + Ley 100 + art. 114-1 ET).

    Broadest detector of the v17 labor block — must register AFTER the
    specific sub-cases (salario_integral, DSPNE, PILA, UGPP, contratos,
    prestaciones, terminación) so it does not intercept their queries.
    """
    if not normalized_message:
        return False
    if "nomina electronica" in normalized_message or "nómina electrónica" in normalized_message:
        return False
    if "salario integral" in normalized_message:
        return False
    markers = (
        "liquidación de nómina", "liquidacion de nomina",
        "liquidación nómina", "liquidacion nomina",
        "liquidar nómina", "liquidar nomina",
        "nómina mensual", "nomina mensual",
        "auxilio de transporte",
        "recargo nocturno",
        "recargo dominical",
        "recargo dominical y festivo",
        "trabajo nocturno",
        "trabajo dominical",
        "trabajo dominical y festivo",
        "trabajo dominical o festivo",
        "horas extras", "hora extra",
        "horas extras diurnas", "hora extra diurna",
        "horas extras nocturnas", "hora extra nocturna",
        "jornada nocturna",
        "aportes empleado",
        "aportes empleador",
        "aportes a seguridad social",
        "aportes seguridad social",
        "ibc nómina", "ibc nomina",
        "exoneración 114-1", "exoneracion 114-1",
        "art. 114-1 et", "art 114-1 et", "114-1 et",
        "solidaridad pensional",
        "tarifa arl",
        "clase de riesgo arl",
        "art. 127 cst", "art 127 cst",
        "art. 128 cst", "art 128 cst",
        "art. 159 cst", "art 159 cst",
        "art. 168 cst", "art 168 cst",
        "art. 179 cst", "art 179 cst",
        "ley 1393 de 2010 art. 30", "ley 1393 de 2010 art 30",
        "ley 100 de 1993",
        "smmlv 2026",
        "25 smmlv",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    # Generic "nómina" + task verb.
    if "nómina" in normalized_message or "nomina" in normalized_message:
        if (
            "liquid" in normalized_message
            or "pagar" in normalized_message
            or "calcul" in normalized_message
            or "aporte" in normalized_message
            or "recargo" in normalized_message
            or "extras" in normalized_message
            or "smmlv" in normalized_message
            or "auxilio" in normalized_message
        ):
            return True
    # Generic "recargo(s)" + labor context. Avoids matches in non-labor
    # contexts where "recargo" can mean a surcharge / interest charge
    # (ICA, predial, IVA), which carry their own topic anchors.
    if "recargo" in normalized_message and (
        "nocturn" in normalized_message
        or "diurn" in normalized_message
        or "dominic" in normalized_message
        or "festiv" in normalized_message
        or "hora extra" in normalized_message
        or "horas extras" in normalized_message
        or "cst" in normalized_message
        or "art. 159" in normalized_message or "art 159" in normalized_message
        or "art. 168" in normalized_message or "art 168" in normalized_message
        or "art. 179" in normalized_message or "art 179" in normalized_message
        or "ley 2466" in normalized_message
    ):
        return True
    # "Dominical(es)" / "festivo(s)" combined with hora/recargo/jornada.
    if ("dominic" in normalized_message or "festiv" in normalized_message) and (
        "hora" in normalized_message
        or "recargo" in normalized_message
        or "jornada" in normalized_message
        or "trabajo" in normalized_message
        or "cst" in normalized_message
    ):
        return True
    # Generic "aportes" + employer / SGSS context.
    if "aporte" in normalized_message and (
        "empleador" in normalized_message
        or "empleado" in normalized_message
        or "seguridad social" in normalized_message
        or "parafiscales" in normalized_message
        or "sena" in normalized_message
        or "icbf" in normalized_message
        or "caja de compensación" in normalized_message
        or "caja de compensacion" in normalized_message
    ):
        return True
    return False


# NOTE: `is_aportes_proporcionales_tiempo_parcial_case` lives in
# ``case_detectors_b6.py`` — extracted here when this file crossed
# the 800-LOC ceiling (v17 b3+ tail, 2026-05-15). The facade
# (``case_detectors.py``) re-exports it from ``_b6`` so call sites
# stay unchanged.
