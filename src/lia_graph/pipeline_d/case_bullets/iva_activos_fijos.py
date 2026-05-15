"""v16 (2026-05-14) — descuento del IVA en activos fijos productivos (art. 258-1 ET)."""
from __future__ import annotations

from ..case_detectors import is_iva_activos_fijos_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="iva_activos_fijos",
    detector=is_iva_activos_fijos_case,
    bullets=(
        "El **100 % del IVA pagado** en la adquisición, construcción, formación o importación de **activos fijos reales productivos** (incluido el IVA en servicios necesarios para ponerlos en marcha) se toma como **descuento del impuesto sobre la renta** (art. 258-1 ET) en el AG de adquisición o en cualquier periodo siguiente sin caducidad.",
        "**Quién puede usarlo:** contribuyentes del régimen ordinario (PJ y PN obligadas a llevar contabilidad). **Los del RST NO** — el art. 258-1 ET no es compatible con el régimen simple.",
        "**Qué califica como activo fijo real productivo (Decreto 1089/2020):** (a) propiedad del contribuyente, (b) **tangible**, (c) **depreciable o amortizable**, (d) participación **directa y permanente** en la actividad productora de renta. Maquinaria, equipos industriales, vehículos de carga, equipos de cómputo afectos a producción. **Software y licencias intangibles NO aplican.**",
        "**Qué IVA específicamente aplica:** el IVA del bien + el IVA de servicios necesarios para ponerlo en condiciones de operación (transporte, instalación, montaje, pruebas técnicas). **No aplica** IVA de mantenimientos posteriores ni repuestos rutinarios.",
        "**Leasing financiero:** el descuento procede para el **locatario** desde el momento del contrato (Decreto 1089/2020), aunque la opción de compra se ejerza después. **Leasing operativo NO aplica.**",
        "**Tratamiento contable:** el IVA tomado como descuento **NO** entra al costo del activo. Se registra en cuenta puente y se lleva al renglón de descuentos del formulario 110.",
        "**Doble beneficio prohibido:** si toma el IVA como descuento del 258-1, **no puede tomarlo simultáneamente como IVA descontable** en la declaración de IVA, ni como mayor costo del activo para depreciación. **Límite del art. 259 ET:** el descuento no puede dejar el impuesto neto por debajo del **75 %** del impuesto sin descuentos; el exceso queda con arrastre indefinido.",
    ),
    keywords=(
        "iva", "activo fijo", "activos fijos",
        "activo fijo real productivo", "activos fijos reales productivos",
        "258-1", "491", "259", "60",
        "decreto 1089",
        "descuento", "descontar", "descontable",
        "maquinaria", "equipo", "equipos",
        "tangible", "intangible",
        "depreciable", "amortizable",
        "leasing financiero", "leasing operativo",
        "instalación", "instalacion", "montaje",
        "renglón", "renglon",
        "formulario 110",
        "límite", "limite", "75%",
    ),
    anchor_articles=("258-1",),
    search_queries=(
        "descuento iva activos fijos reales productivos art 258-1 et",
        "100% iva maquinaria descontar renta art 258-1 decreto 1089 2020",
    ),
    source_label="iva_activos_fijos_anchor",
)
