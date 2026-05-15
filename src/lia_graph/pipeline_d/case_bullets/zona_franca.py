"""v16 (2026-05-14) — doble tarifa zona franca (art. 240-1 ET)."""
from __future__ import annotations

from ..case_detectors import is_zona_franca_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="zona_franca",
    detector=is_zona_franca_case,
    bullets=(
        "Tras la Ley 2277/2022 art. 11, los **usuarios industriales de bienes y servicios (UIB/UIS)** de zona franca aplican un **esquema de doble tarifa**: **20 %** sobre la renta atribuible a **exportaciones** (si cumplen plan de internacionalización) + **35 %** sobre la renta del mercado nacional. **Sin plan o sin cumplir:** **35 %** sobre toda la renta desde AG 2024.",
        "**Tipos de usuarios y tarifa:** UIB (industrial de bienes) y UIS (industrial de servicios) — doble tarifa **20 %/35 %** si cumplen plan. **Usuarios comerciales:** **35 %** (tarifa general PJ). **Usuarios operadores:** **35 %**.",
        "**Plan de internacionalización (Decreto 0049/2024):** el UIB/UIS suscribe ante **MinCIT** un plan con compromiso anual de exportaciones (umbral mínimo según tamaño y antigüedad). **Cumplimiento se verifica anualmente**; incumplir causa **pérdida del beneficio del 20 %** y posibles efectos retroactivos.",
        "**Cálculo de base atribuible a exportaciones:** contabilidad separada o **pro rata** por (ingresos de exportación / ingresos totales) aplicada a la renta líquida. Costos directamente atribuibles se asignan en su totalidad; comunes se distribuyen por pro rata.",
        "**Transición — Sentencia C-384/2023:** la Corte Constitucional declaró exequibilidad condicionada. Usuarios calificados **antes del 13 de diciembre de 2022** mantienen la tarifa del 20 % bajo régimen anterior hasta el vencimiento de su prórroga vigente o duración inicial del régimen.",
        "**Exclusiones del beneficio 20 %:** los UIB/UIS con plan **están exceptuados de la TTD** del 15 % (art. 240 par. 6 ET). Régimen propio para megainversiones (art. 235-3 ET) y CHC.",
        "**Aplicación práctica formulario 110:** renglón de tarifa especial UIB/UIS + anexo conciliatorio. Liquidar dos impuestos: **(renta exportadora × 20 %) + (renta no exportadora × 35 %)**. Soporte: resolución de calificación MinCIT, plan aprobado, contabilidad separada o pro rata, certificaciones DEX/SIE firmadas por revisor fiscal.",
    ),
    keywords=(
        "zona franca", "zonas francas",
        "uib", "uis",
        "usuario industrial", "usuarios industriales",
        "usuario comercial", "usuarios comerciales",
        "usuario operador",
        "240-1", "240",
        "20%", "20 %", "35%", "35 %",
        "exportación", "exportacion", "exportaciones",
        "mercado nacional",
        "plan de internacionalización", "plan de internacionalizacion",
        "mincit",
        "ley 2277", "decreto 0049",
        "c-384 de 2023", "sentencia c-384",
        "ttd",
        "pro rata", "prorata",
        "contabilidad separada",
        "dex", "sie",
        "ley 1004",
    ),
    anchor_articles=("240-1",),
    search_queries=(
        "tarifa zona franca doble 20 35 plan internacionalizacion art 240-1 et",
        "uib uis exportaciones mercado nacional ley 2277 decreto 0049 2024",
    ),
    source_label="zona_franca_anchor",
)
