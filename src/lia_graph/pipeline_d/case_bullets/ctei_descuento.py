"""v16 (2026-05-14) — descuento CTeI Minciencias (art. 256 ET)."""
from __future__ import annotations

from ..case_detectors import is_ctei_descuento_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="ctei_descuento",
    detector=is_ctei_descuento_case,
    bullets=(
        "Las **inversiones y donaciones en proyectos de CTeI** calificados por el **CNBT — Minciencias** dan derecho a un **descuento tributario equivalente al 50 %** del valor invertido o donado sobre el impuesto sobre la renta del AG (art. 256 ET, modificado por Ley 2277/2022 art. 21).",
        "**Quién aplica:** contribuyentes del régimen ordinario (PJ y PN obligadas a llevar contabilidad). **RST no aplica.** El proyecto puede ejecutarse directamente por el contribuyente o por un actor del SNCTeI calificado por Minciencias.",
        "**Cálculo:** **50 %** del valor de la inversión o donación. Ejemplo: inversión calificada de **$200.000.000** → descuento de **$100.000.000**. Antes de la Ley 2277/2022 (AG 2022 y anteriores) el descuento era del **25 %**.",
        "**Modalidades aceptadas:** inversiones directas en proyectos calificados; donaciones a programas de doctorado en universidades reconocidas; **vinculación de capital humano** de alto nivel (PhD con dedicación al proyecto); donaciones para becas pregrado/posgrado vía ICETEX o entidades habilitadas.",
        "**Calificación previa obligatoria:** el proyecto **debe ser calificado por el CNBT — Minciencias** antes de aplicar el descuento. Convocatoria anual; **sin calificación el descuento no procede**.",
        "**Límite individual (art. 256 par.):** el descuento por CTeI no puede exceder el **25 % del impuesto sobre la renta a cargo** del AG. El excedente se arrastra a los **cuatro periodos gravables siguientes**. **Límite agregado (art. 259 ET):** la suma de todos los descuentos no puede dejar el impuesto neto por debajo del **75 %** del impuesto sin descuentos.",
        "**Doble beneficio — atención:** la Ley 2277/2022 restringió el uso simultáneo de la deducción del art. 158-1 + descuento del art. 256. Posición conservadora: **optar por una sola vía** y documentar la elección.",
    ),
    keywords=(
        "ctei", "i+d", "i+d+i",
        "ciencia tecnología", "ciencia tecnologia",
        "innovación", "innovacion",
        "investigación", "investigacion",
        "256", "158-1", "259",
        "minciencias", "cnbt", "snctei",
        "descuento", "descuentos", "descontar",
        "50%", "50 %", "25%",
        "calificación", "calificacion",
        "phd", "doctorado",
        "icetex",
        "becas",
        "donación", "donacion", "donaciones",
        "inversión", "inversion",
        "renglón", "renglon",
        "arrastre",
    ),
    anchor_articles=("256",),
    search_queries=(
        "descuento ctei 50% minciencias cnbt art 256 et ley 2277 2022",
        "inversiones donaciones ciencia tecnologia innovacion art 256 et art 259",
    ),
    source_label="ctei_descuento_anchor",
)
