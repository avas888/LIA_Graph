"""v16 b4 — exógena umbrales y plazos AG (Res. DIAN 000162/2023)."""
from __future__ import annotations

from ..case_detectors import is_exogena_umbrales_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="exogena_umbrales",
    detector=is_exogena_umbrales_case,
    bullets=(
        "**Sujetos obligados — regla general AG 2025 (Res. 000162/2023 art. 1):** **PJ** con ingresos brutos del AG 2023 **> 100.000 UVT** (≈ **$4.241.200.000**). **PN** con ingresos brutos del AG 2023 **> $500.000.000**. Adicionalmente: agentes de retención, consorcios, fiducias, cámaras de comercio, notarios, operadores de juegos — sin importar ingresos.",
        "**Formatos típicos PYME:** comercial estándar (≥ 100.000 UVT) presenta **1001, 1003, 1005, 1006, 1007, 1008, 1009, 1010, 1011, 1012, 1647, 2276**. Pequeña agente de retención (no supera umbral): 1001 + 1003 + 2276 parcial. PN profesional ≥ $500M: 1001, 1003 (si retiene), 1005, 1006, 1007, 1008, 1009, 2276.",
        "**Plazos AG 2025 — vencimientos abril–junio 2026** por último dígito del NIT: **1-2** → semana 4 de abril 2026; **3-4** → semana 1 de mayo; **5-6** → semana 2 de mayo; **7-8** → semana 3 de mayo; **9-0** → semana 4 de mayo. Grandes contribuyentes en abril 2026 según calendario específico.",
        "**Sanción por no presentar (art. 651 ET modificado por Ley 2277/2022 art. 80):** **5 %** del valor de información no suministrada; **4 %** información con errores; **3 %** extemporánea. **Tope máximo 7.500 UVT** (UVT 2026 → ~$373.492.500). Sin base establecible: **0,5 %** de ingresos netos del AG anterior. Mínimo 1 UVT.",
        "**Reducciones (art. 651 ET — Ley 2277/2022):** subsanación **antes del pliego de cargos** → **80 %** de reducción. Después del pliego, antes de resolución sancionatoria → **50 %**. Subsanación voluntaria + acuerdo de pago → **70 %**.",
        "**Procedimiento operativo:** **enero–febrero** levantar archivo plano cuadrado contra contabilidad y declaraciones; **marzo** validar en prevalidador DIAN; **3 semanas antes del vencimiento** prueba de envío; **vencimiento − 5 días hábiles** envío definitivo con acuse; **post-envío** archivar 5 años.",
        "**Errores comunes:** revisar el umbral del AG equivocado (es ingresos del AG **anterior** al que se reporta); olvidar obligados sin importar umbral (consorcios, agentes retención); presentar tarde sin acogerse al **80 %** de reducción. Firmeza de exógena: **5 años** desde el vencimiento.",
    ),
    keywords=(
        "exógena", "exogena",
        "información exógena", "informacion exogena",
        "umbral", "umbrales",
        "plazos", "vencimiento", "vencimientos",
        "obligado", "obligados",
        "100.000 uvt",
        "500.000.000",
        "ag 2023", "ag 2024", "ag 2025",
        "abril 2026", "mayo 2026", "junio 2026",
        "dígito nit", "digito nit",
        "art. 651", "art 651",
        "art. 631", "art 631",
        "art. 631-3", "art 631-3",
        "art. 640", "art 640",
        "5%", "4%", "3%",
        "7.500 uvt", "7500 uvt",
        "0,5%",
        "80%", "70%", "50%",
        "pliego de cargos",
        "ley 2277",
        "res. dian 000162", "resolucion 000162",
        "1001", "1003", "1005", "1006", "1007", "1008", "1009", "1010", "1011", "1012", "1647", "2276",
        "firmeza",
        "5 años",
    ),
    anchor_articles=("631",),
    search_queries=(
        "exogena umbrales plazos ag 2025 res dian 000162 2023 sujetos obligados",
        "sancion exogena art 651 et ley 2277 reducciones 80 50 70 por ciento pliego cargos",
    ),
    source_label="exogena_umbrales_anchor",
)
