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
