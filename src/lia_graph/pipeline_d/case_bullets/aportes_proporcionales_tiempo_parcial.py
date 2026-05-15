"""v17 b3+ — Aportes y salario proporcionales (tiempo parcial / por días).

38th case anchor, landed 2026-05-15 in response to a real operator
probe gap: *"tengo una empleada a tiempo parcial (3 días, salario
mínimo por días). ¿Cómo le pago la EPS? ¿Es proporcional?"* — none
of the 9 v17 b1-b3 detectors fired, so retrieval surfaced a chunk
about incapacidad and the answer drifted off-topic.

Source playbook: ``knowledge_base/.../TRABAJO_TIEMPO_PARCIAL/LOGGRO/
TPR-L02-guia-practica-trabajo-domestico-remunerado-por-dias.md``
(ya en cloud Supabase desde gen_20260425123153 con tema=laboral,
topic=laboral, knowledge_class=practica_erp).

Anchored at ET arts. 108 + 114-1 (Option A per fix_v17_may §3.3). El
régimen sustantivo está en CST Art. 197 (proporcionalidad),
Ley 2466/2025 Arts. 33-34 (formalización + cotización por semanas),
Decreto 2616/2013 (cotización por semanas para IBC < SMLMV con SISBÉN)
y Resolución MinSalud 2388/2016 (tipo cotizante PILA 02 — servicio
doméstico), citados en bullets.
"""
from __future__ import annotations

from ..case_detectors import is_aportes_proporcionales_tiempo_parcial_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="aportes_proporcionales_tiempo_parcial",
    detector=is_aportes_proporcionales_tiempo_parcial_case,
    bullets=(
        "**Quién aplica:** empleada doméstica que va 2–4 días/semana sin residir en el hogar; trabajador a tiempo parcial cuyo IBC quedaría por debajo del SMLMV. Régimen: **CST Art. 197** (proporcionalidad), **Ley 2466/2025 Arts. 33–34**, **Decreto 2616/2013**, **Resolución MinSalud 2388/2016** (tipo cotizante PILA 02).",
        "**Salario proporcional (CST Art. 197):** Salario = (Días trabajados/semana ÷ 6) × SMLMV. **2 días → $583.635 | 3 días → $875.453 | 4 días → $1.167.270** (SMLMV 2026 = $1.750.905). El denominador es **6** (semana laboral lunes-sábado), aunque solo trabaje lunes-viernes.",
        "**Auxilio de transporte proporcional:** se prorratea por los días de desplazamiento (concepto MinTrabajo). **2 días → $83.032 | 3 días → $124.548 | 4 días → $166.063** (auxilio 2026 = $249.095). La posición más segura ante litigio es proporcionalizar, no pagar el auxilio completo.",
        "**Opción A — Decreto 2616/2013 (trabajadora con SISBÉN):** cotiza por semanas, **NO cotiza salud contributiva** (conserva el subsidiado), tipo cotizante PILA **02**. Es la opción más económica para el hogar persona natural — no paga salud patronal.",
        "**Opción B — Ley 2466/2025 Art. 34 (hogar formalizado):** hogar con declaración de renta, libros y contrato escrito registrado → **IBC proporcional al salario real** ($875.453), cotiza salud contributiva, tipo cotizante 02. **Opción C — regla general:** sin SISBÉN ni Art. 34 → **IBC mínimo = 1 SMLMV ($1.750.905)** aunque pague menos.",
        "**PILA — pasos clave:** tipo cotizante **02 — Servicio doméstico** (nunca el 01 dependiente común ni el 51 tiempo parcial general); IBC = salario proporcional si aplica Decreto 2616 o Ley 2466 Art. 34; plazos de pago por los dos últimos dígitos de la cédula (**Decreto 1990/2016**). Operadores: SOI, Aportes en Línea, Mi Planilla.",
        "**Hogar persona natural NO tiene la exoneración del Art. 114-1 ET.** La exoneración aplica a personas jurídicas y PN con ≥ 2 empleados que declaran renta. Un hogar con una sola empleada paga **SENA 2 % + ICBF 3 % + salud patronal 8,5 % + CCF 4 %** sin excepción — por eso la Opción A (Decreto 2616) es la más atractiva si la trabajadora tiene SISBÉN.",
        "**Prestaciones sociales también proporcionales (CST Art. 197):** prima de servicios **8,33 %**, cesantías **8,33 %**, intereses cesantías ~1 %, vacaciones 15 días hábiles/año (**CST Art. 186**). Base = salario + auxilio de transporte (vacaciones excluyen AT). **Dotación** 3 veces/año (**CST Arts. 230–234**) si salario ≤ 2 SMLMV — casi seguro en trabajo por días.",
    ),
    keywords=(
        "tiempo parcial",
        "jornada parcial",
        "media jornada",
        "por días", "por dias", "por dia",
        "días por semana", "dias por semana",
        "días a la semana", "dias a la semana",
        "trabajadora doméstica", "trabajadora domestica",
        "trabajador doméstico", "trabajador domestico",
        "empleada doméstica", "empleada domestica",
        "empleada de hogar", "empleada del hogar",
        "trabajo doméstico", "trabajo domestico",
        "servicio doméstico", "servicio domestico",
        "decreto 2616", "decreto 2616 de 2013", "decreto 2616/2013",
        "ley 2466 art. 33", "ley 2466 art 33",
        "ley 2466 art. 34", "ley 2466 art 34",
        "art. 33 ley 2466", "art 33 ley 2466",
        "art. 34 ley 2466", "art 34 ley 2466",
        "cst art. 197", "cst art 197",
        "art. 197 cst", "art 197 cst",
        "art. 108", "art 108",
        "art. 114-1", "art 114-1", "114-1",
        "tipo cotizante 02", "cotizante tipo 02", "tipo 02 servicio",
        "cotización por semanas", "cotizacion por semanas",
        "ibc proporcional",
        "salario proporcional",
        "auxilio proporcional",
        "auxilio de transporte proporcional",
        "aportes proporcionales",
        "aporte proporcional",
        "eps proporcional",
        "sisben",
        "smmlv", "smlmv",
        "pila",
        "operador pila",
        "soi", "aportes en línea", "aportes en linea", "mi planilla",
        "decreto 1990 de 2016", "decreto 1990/2016",
        "resolución 2388", "resolucion 2388",
        "exoneración 114-1", "exoneracion 114-1",
        "hogar empleador",
        "persona natural empleador",
        "régimen subsidiado", "regimen subsidiado",
    ),
    anchor_articles=("108", "114-1"),
    search_queries=(
        "trabajadora doméstica por días salario proporcional cst 197 ley 2466 art 33",
        "cotización por semanas decreto 2616 de 2013 sisbén ibc menor smlmv",
        "tipo cotizante pila 02 servicio doméstico ley 2466 art 34 hogar empleador",
    ),
    source_label="aportes_proporcionales_tiempo_parcial_anchor",
)
