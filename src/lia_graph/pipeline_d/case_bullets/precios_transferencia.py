"""v16 b5 — precios de transferencia (arts. 260-1 a 260-11 ET)."""
from __future__ import annotations

from ..case_detectors import is_precios_transferencia_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="precios_transferencia",
    detector=is_precios_transferencia_case,
    bullets=(
        "**Sujetos al régimen (arts. 260-1 y 260-2 ET):** contribuyentes del impuesto de renta que realicen operaciones con (a) **vinculados del exterior**; (b) **vinculados en zonas francas** (incluso entre colombianos, art. 260-2 par.); (c) sujetos en **jurisdicciones no cooperantes** o regímenes preferenciales (art. 260-7 ET + Decreto 1103/2024).",
        "**Umbrales para obligación formal (art. 260-9 ET):** **F120 Declaración Informativa + F1125 Informe Local** se activan cuando **patrimonio bruto al cierre del AG ≥ 100.000 UVT** ($4.706.500.000 AG 2025) **o** ingresos brutos del AG **≥ 61.000 UVT** ($2.870.965.000), Y operaciones por tipo **> 45.000 UVT** ($2.117.925.000). **Operaciones con jurisdicciones no cooperantes: siempre obligado a F120**, sin importar montos.",
        "**Informe Maestro F1729 (art. 260-5 par. ET):** grupos multinacionales con ingresos consolidados **≥ 81.000.000 UVT** del año anterior (umbral OCDE BEPS Acción 13).",
        "**Métodos de comparabilidad (art. 260-3 ET):** **PC** (precio comparable no controlado) para commodities; **PR** (precio de reventa) para distribuidores; **CA** (costo adicionado) para fabricantes/servicios; **TU** (margen transaccional de utilidad operativa) el más usado en práctica; **PU** (partición de utilidades) para integradas o intangibles únicos. Decreto 1357/2024 ajustó reglas para commodities.",
        "**Plazos AG 2025:** **F120 + F1125** en **septiembre** del año siguiente según último dígito NIT; **F1729** en **diciembre**.",
        "**Régimen sancionatorio (art. 260-11 ET):** **documentación comprobatoria** — extemporaneidad **0,05 %/mes** antes de emplazamiento, **0,1 %/mes** después; inconsistencias **1 %**; no presentar **4 %** (máx. 25.000 UVT). **Declaración informativa** — extemporaneidad **0,02 %/mes**; no presentar **10 %** (máx. 15.000 UVT).",
        "**Diagnóstico paso a paso:** identificar vinculados (control accionario, gerencia, capital común); identificar jurisdicción de contraparte vs lista vigente; cuantificar operaciones por tipo (importación de bienes, exportación, servicios técnicos, regalías, intereses, dividendos); comparar con umbrales; decidir si contrata estudio + presenta F120 + F1125; análisis funcional + selección de comparables (SUFRT, RoyaltyStat, Bloomberg); conclusión sobre principio de plena competencia.",
    ),
    keywords=(
        "precios de transferencia",
        "260-1", "260-2", "260-3", "260-5", "260-7", "260-9", "260-11",
        "f120", "f1125", "f1729",
        "formato 120", "formato 1125", "formato 1729",
        "declaración informativa", "declaracion informativa",
        "informe local", "informe maestro",
        "vinculados del exterior",
        "vinculados",
        "zona franca", "zonas francas",
        "jurisdicciones no cooperantes",
        "paraísos fiscales", "paraisos fiscales",
        "regímenes preferenciales", "regimenes preferenciales",
        "principio de plena competencia",
        "análisis funcional", "analisis funcional",
        "pc ", "pr ", "ca ", "tu ", "pu ",
        "commodities",
        "100.000 uvt", "61.000 uvt", "45.000 uvt", "81.000.000 uvt",
        "decreto 1357",
        "decreto 1103",
        "ley 2277",
    ),
    anchor_articles=("260-1",),
    search_queries=(
        "precios de transferencia art 260-1 260-9 et f120 f1125 vinculados exterior",
        "jurisdicciones no cooperantes paraisos fiscales art 260-7 et decreto 1103 2024",
    ),
    source_label="precios_transferencia_anchor",
)
