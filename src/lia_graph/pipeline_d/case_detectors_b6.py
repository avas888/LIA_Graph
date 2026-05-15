"""v17 b3+ tail (2026-05-15) — Tiempo parcial / por días labor detector.

New sibling created when ``case_detectors_b5.py`` crossed the 800-LOC
ceiling. Future labor / nómina detectors that don't fit cleanly into
``_b5``'s existing groupings should land here.

Detectors here remain **pure** — only ``re`` and types. Adding imports
from any ``answer_*`` / ``planner`` module reintroduces the circular
import that v15.5 broke.
"""
from __future__ import annotations


def is_aportes_proporcionales_tiempo_parcial_case(normalized_message: str) -> bool:
    """v17 b3+ — Aportes y salario proporcionales para trabajo a tiempo parcial / por días.

    Cubre empleadas domésticas que trabajan 2-4 días/semana y trabajadores
    a tiempo parcial cuyo IBC queda por debajo del SMLMV. Anclado en ET
    arts. 108 + 114-1 (Option A per fix_v17_may §3.3). Régimen sustantivo
    en CST Art. 197 (proporcionalidad), Ley 2466/2025 Art. 33 / 34,
    Decreto 2616/2013, Resolución MinSalud 2388/2016 (tipo cotizante 02).
    """
    if not normalized_message:
        return False
    nm = normalized_message
    markers = (
        "decreto 2616 de 2013", "decreto 2616/2013", "decreto 2616",
        "ley 2466 art. 33", "ley 2466 art 33",
        "ley 2466 art. 34", "ley 2466 art 34",
        "art. 33 ley 2466", "art 33 ley 2466",
        "art. 34 ley 2466", "art 34 ley 2466",
        "cotización por semanas", "cotizacion por semanas",
        "tipo cotizante 02", "cotizante tipo 02", "tipo 02 servicio",
        "servicio doméstico", "servicio domestico",
        "trabajadora doméstica", "trabajadora domestica",
        "trabajador doméstico", "trabajador domestico",
        "empleada doméstica", "empleada domestica",
        "empleada de hogar", "empleada del hogar",
        "trabajo doméstico", "trabajo domestico",
        "ibc proporcional",
        "salario proporcional",
        "aportes proporcionales",
        "aporte proporcional",
        "eps proporcional",
        "cst art. 197", "cst art 197",
        "art. 197 cst", "art 197 cst",
        "tiempo parcial",
        "jornada parcial",
        "media jornada",
    )
    if any(marker in nm for marker in markers):
        return True
    # General-phrasing fallback 1: "por dias/días" + labor/aportes context.
    if ("por dias" in nm or "por días" in nm or "por dia" in nm) and (
        "eps" in nm
        or "salud" in nm
        or "ibc" in nm
        or "aporte" in nm
        or "afilia" in nm
        or "pension" in nm or "pensión" in nm
        or "pila" in nm
        or "empleada" in nm
        or "empleado" in nm
        or "trabajador" in nm
        or "salario" in nm
        or "smmlv" in nm or "smlmv" in nm
    ):
        return True
    # General-phrasing fallback 2: "parcial" + EPS/IBC/aportes context.
    if "parcial" in nm and (
        "eps" in nm
        or "ibc" in nm
        or "aporte" in nm
        or "afilia" in nm
        or "salud" in nm
        or "pension" in nm or "pensión" in nm
        or "proporcional" in nm
        or "pila" in nm
    ):
        return True
    # General-phrasing fallback 3: numeric "N días/dias por semana" or
    # "labora/trabaja N días" with labor cue.
    if ("dias por semana" in nm or "días por semana" in nm
            or "dias a la semana" in nm or "días a la semana" in nm) and (
        "salario" in nm
        or "eps" in nm
        or "aporte" in nm
        or "empleada" in nm
        or "empleado" in nm
        or "trabajador" in nm
        or "ibc" in nm
        or "proporcional" in nm
    ):
        return True
    # General-phrasing fallback 4: SISBÉN + EPS/aportes context (the
    # Decreto 2616 path is uniquely keyed on SISBÉN status).
    if "sisben" in nm and (
        "eps" in nm
        or "cotiza" in nm
        or "salud" in nm
        or "afilia" in nm
        or "aporte" in nm
    ):
        return True
    return False


__all__ = ["is_aportes_proporcionales_tiempo_parcial_case"]
