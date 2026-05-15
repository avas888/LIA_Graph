"""v16 b5 — renta cedular PN (arts. 330 a 343 ET)."""
from __future__ import annotations

from ..case_detectors import is_renta_cedular_pn_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="renta_cedular_pn",
    detector=is_renta_cedular_pn_case,
    bullets=(
        "**Tres cédulas (arts. 330 a 343 ET):** **Cédula general** (art. 335) = laboral + capital + no laboral. **Cédula pensiones** (art. 337) = jubilación, invalidez, vejez, sobrevivientes — hasta **1.000 UVT mensuales** renta exenta (art. 206 num. 5). **Cédula dividendos y participaciones** (art. 343) = dividendos no gravados y gravados.",
        "**Depuración cédula general:** ingresos brutos → menos **INCRNGO** (aportes obligatorios salud y pensión del trabajador, apoyos educativos arts. 46 y 46-1) → ingreso neto → menos costos y gastos procedentes (especialmente honorarios) → menos **rentas exentas + deducciones imputables**, sujetas al **límite del 40 % del ingreso neto y 1.340 UVT anuales** (Ley 2277/2022 art. 7).",
        "**Topes de rentas exentas / deducciones (sujetos al global 40 %/1.340 UVT):** **25 % renta exenta laboral** → tope **790 UVT** ($37.181.350 AG 2025) (art. 206 num. 10). **Aportes voluntarios pensiones + AFC** → tope **30 % ingreso / 3.800 UVT** ($178.847.000). **Intereses préstamo vivienda** → tope **1.200 UVT** ($56.478.000) (art. 119). **Salud prepagada** → **16 UVT/mes** ($752.700). **Dependientes** → 10 % ingreso, tope **32 UVT/mes** ($1.505.480) y 384 UVT anuales. **Deducción 1 % compras con FE** pagadas electrónicamente → **240 UVT** (art. 336 num. 5 Ley 2277/2022).",
        "**Límite global Ley 2277/2022 (art. 336 ET):** suma rentas exentas + deducciones ≤ **min (40 % ingreso neto ; 1.340 UVT)** = min (40 % ; **$63.067.100 AG 2025**). El antiguo tope de 5.040 UVT fue **reducido a 1.340 UVT** desde AG 2023.",
        "**Cédula pensiones:** ingresos brutos − aportes a salud sobre la pensión − **renta exenta hasta 1.000 UVT mensuales** ($47.065.000/mes AG 2025). Resultado → tabla **art. 241 ET**.",
        "**Cédula dividendos:** no gravados → tabla art. 242 ET (tarifa marginal cédula general post Ley 2277/2022, descuento art. 254-1 ET = 19 %); gravados → primero **35 %**, remanente sigue regla anterior.",
        "**Suma impuesto de las tres cédulas → impuesto a cargo → menos descuentos tributarios** (art. 254 impuestos exterior, 254-1 dividendos, 256 donaciones) → impuesto neto. Reste retenciones del año y anticipo del año anterior; determine saldo a pagar o a favor.",
    ),
    keywords=(
        "renta cedular",
        "cédula", "cedula",
        "cédula general", "cedula general",
        "cédula pensiones", "cedula pensiones",
        "cédula dividendos", "cedula dividendos",
        "subcédula",
        "330", "335", "336", "337", "343",
        "241", "242", "254-1",
        "206 num. 10",
        "126-1", "126-4",
        "387", "119",
        "rentas exentas",
        "deducciones imputables",
        "40%", "40 %",
        "1.340 uvt", "1340 uvt",
        "5.040 uvt", "5040 uvt",
        "790 uvt",
        "3.800 uvt", "3800 uvt",
        "1.200 uvt", "1200 uvt",
        "16 uvt", "32 uvt",
        "1.000 uvt mensuales", "1000 uvt mensuales",
        "ley 2277",
        "incr", "incrngo",
        "intereses vivienda",
        "salud prepagada",
        "dependientes",
        "formulario 210",
        "25%", "25 %",
        "deducción 1%", "deduccion 1%",
    ),
    anchor_articles=("336",),
    search_queries=(
        "renta cedular personas naturales art 330 343 et cedula general pensiones dividendos",
        "tope cedula general 40 1340 uvt ley 2277 art 336 et rentas exentas deducciones",
    ),
    source_label="renta_cedular_pn_anchor",
)
