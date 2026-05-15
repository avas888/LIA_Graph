"""v16 b5 — capitalización de utilidades (art. 36-3 ET)."""
from __future__ import annotations

from ..case_detectors import is_capitalizacion_utilidades_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="capitalizacion_utilidades",
    detector=is_capitalizacion_utilidades_case,
    bullets=(
        "**Regla clave (art. 36-3 ET, Ley 1819/2016 art. 35):** la capitalización de utilidades **susceptibles de distribuirse como no gravadas** (art. 49 ET) **NO constituye renta ni ganancia ocasional** para el socio. La capitalización de utilidades **gravadas SÍ produce ingreso gravado** al socio en el momento de la capitalización.",
        "**Identifique el origen de la utilidad:** antes de proponer la capitalización, **calcule la utilidad máxima susceptible de distribuirse como no gravada** aplicando la fórmula del art. 49 ET. **Solo esa porción capitaliza sin generar renta al socio.**",
        "**Utilidad no gravada (art. 49 ET):** el acta de asamblea ordena la capitalización; **el socio NO declara ingreso** en el año; el **costo fiscal de las nuevas acciones/cuotas es cero** (no incrementa el costo fiscal de la inversión preexistente). El mayor valor nominal aparece en el patrimonio fiscal sin costo asignable contra futura enajenación.",
        "**Utilidad gravada:** la capitalización equivale a un **dividendo gravado en especie**. El socio declara el ingreso al momento de la capitalización; la sociedad practica retención sobre dividendos (art. 242 ET para PN residentes con tarifa marginal + descuento art. 254-1; art. 245 ET para no residentes = **20 %**).",
        "**Reserva del art. 130 ET y revalorización del patrimonio:** **capitalizables sin generar renta al socio** en todos los casos. La cuenta de revalorización fue congelada por Ley 1739/2014 pero los saldos preexistentes siguen capitalizándose libres bajo art. 36-3 ET. **Prima en colocación de acciones** (Ley 1607/2012): forma parte del aporte social — su capitalización no genera ingreso.",
        "**Registro contable:** Dr 360505 Utilidades del ejercicio / 3605 Utilidades acumuladas; Cr 310505 Capital suscrito y pagado (o 3205 Prima en colocación). **Sin efecto en P&L.** Registro societario: acta de asamblea + reforma estatutaria + **registro en Cámara de Comercio dentro de 30 días**.",
        "**Tip de planeación:** capitalizar utilidades no gravadas en lugar de distribuirlas es un vehículo legítimo para retener flujo en la sociedad sin diferir el impuesto del socio — **no hay diferimiento**, simplemente no se genera el hecho gravado. Útil para sociedades familiares que quieren crecer patrimonio sin desembolso de retención de dividendos.",
    ),
    keywords=(
        "capitalización", "capitalizacion",
        "capitalizar",
        "utilidades", "utilidad",
        "36-3", "49", "30", "242", "245", "130",
        "dividendo en acciones",
        "dividendo en especie",
        "no gravada", "no gravadas",
        "gravada", "gravadas",
        "reserva legal",
        "prima en colocación", "prima en colocacion",
        "revalorización del patrimonio", "revalorizacion del patrimonio",
        "patrimonio fiscal",
        "costo fiscal",
        "acta de asamblea",
        "cámara de comercio", "camara de comercio",
        "30 días", "30 dias",
        "ley 1819",
        "ley 1739",
        "ley 1607",
        "socios", "accionistas",
        "incr", "incrngo",
        "360505", "310505", "3205",
    ),
    anchor_articles=("36-3",),
    search_queries=(
        "capitalizacion de utilidades art 36-3 et no constituye renta socio",
        "capitalizar utilidades no gravadas art 49 et ley 1819 reforma estatuto",
    ),
    source_label="capitalizacion_utilidades_anchor",
)
