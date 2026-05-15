"""v17 b3 — contrato OPS vs laboral / contrato realidad (CST art. 23).

Anchored at ET art. 383 (retención salarios — el régimen tributario que
aplicaría tras la reclasificación). El régimen sustantivo está en CST
22-24 + art. 53 Constitución (primacía de la realidad), citados en bullets.
"""
from __future__ import annotations

from ..case_detectors import is_contrato_prestacion_vs_laboral_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="contrato_prestacion_vs_laboral",
    detector=is_contrato_prestacion_vs_laboral_case,
    bullets=(
        "**Test de los tres elementos (CST art. 23):** (a) ¿el contratista presta personalmente el servicio o puede delegar libremente?; (b) ¿recibe órdenes sobre cómo, dónde y cuándo, o solo entrega un resultado?; (c) ¿hay pago periódico por tiempo (honorario fijo mensual) o por entregable concreto? **Si las tres apuntan a relación dependiente → contrato realidad laboral**.",
        "**Presunción art. 24 CST:** se presume que toda relación de trabajo personal está regida por contrato de trabajo. **La carga de la prueba para desvirtuarla recae en quien alega la prestación de servicios**. Refuerza el art. 53 de la Constitución — **primacía de la realidad sobre las formas**. Cláusulas tipo \"las partes manifiestan que no hay subordinación\" **no protegen** si los hechos demuestran lo contrario.",
        "**Indicios de subordinación que pesan en juicio (CSJ SL2885-2020 + SL3771-2022):** horario fijo de oficina, cumplimiento de reglamento interno, supervisor directo de planta, vacaciones autorizadas, dotación entregada por la empresa, correo corporativo, evaluación de desempeño, manuales de funciones, asignación de cuotas. **Una sola circunstancia rara vez basta** — el juez evalúa el conjunto. Antigüedad **3+ años continuos** con exclusividad de facto = bandera roja UGPP.",
        "**Indicios de autonomía que protegen el OPS:** contratista factura electrónicamente, tiene RUT como prestador de servicios, atiende a varios clientes, fija sus propios horarios, asume el riesgo del resultado, aporta sus herramientas, contrata personal propio para ejecutar, contrato pactado por entregables y plazos definidos.",
        "**Aportes seg. social del contratista (OPS genuino):** IBC = **40 % del valor mensualizado del contrato** (Ley 1955/2019 art. 244 + Decreto 1601/2022), mínimo 1 SMMLV. **El contratante DEBE verificar mes a mes** que el contratista esté afiliado y al día — exigencia para deducir el costo en renta (parágrafo 2 del **art. 108 ET**). **ARL siempre por cuenta del contratante** cuando el contrato es > 1 mes y la actividad es **riesgo IV o V** (Decreto 723/2013).",
        "**Riesgo UGPP — recálculo de aportes:** si la UGPP reclasifica el vínculo en fiscalización, recalcula aportes al SGSS + parafiscales sobre el honorario pagado + intereses moratorios. La sanción base por omisión es **5 % por mes de retraso** (Decreto 1990/2016, art. 179 Ley 1607/2012), con tope que puede llegar al **200 %** del valor omitido por inexactitud reiterada.",
        "**Consecuencias económicas de la reclasificación laboral:** reconocer retroactivamente cesantías + intereses 12 % + prima de servicios + vacaciones + dotación + aportes patronales del **20,5 %** (8,5 % salud + 12 % pensión, más ARL y parafiscales según exoneración art. 114-1 ET) + indemnización art. 64 CST si el corte fue unilateral. Factura típica > **45 % del honorario total** pagado durante la vigencia. La retención por salarios pasa al régimen **art. 383 ET + art. 387 ET (depuración)**.",
    ),
    keywords=(
        "contrato realidad",
        "primacía de la realidad", "primacia de la realidad",
        "art. 23 cst", "art 23 cst",
        "art. 24 cst", "art 24 cst",
        "art. 22 cst", "art 22 cst",
        "art. 53 constitución", "art 53 constitucion",
        "subordinación", "subordinacion",
        "test de subordinación", "test de subordinacion",
        "ops",
        "prestación de servicios", "prestacion de servicios",
        "prestación servicios vs laboral", "prestacion servicios vs laboral",
        "reclasificación", "reclasificacion",
        "reclasificación ugpp", "reclasificacion ugpp",
        "csj sl3771", "sl3771-2022",
        "csj sl2885", "sl2885-2020",
        "c-555 de 1994", "c-555/1994",
        "decreto 1601 de 2022",
        "decreto 723 de 2013",
        "decreto 1273 de 2018",
        "ley 1955 de 2019 art 244",
        "ley 1562 de 2012",
        "arl contratista",
        "riesgo iv", "riesgo v",
        "ibc 40 %", "ibc 40%",
        "contratista",
        "honorario",
        "art. 108", "art 108",
        "art. 114-1", "art 114-1",
        "art. 383", "art 383",
        "art. 64 cst", "art 64 cst",
        "200 %", "200%",
        "5 % por mes", "5% por mes",
        "factura electrónica", "factura electronica",
        "indicios de subordinación", "indicios de subordinacion",
        "indicios de autonomía", "indicios de autonomia",
    ),
    anchor_articles=("383",),
    search_queries=(
        "contrato realidad cst art 23 24 primacia realidad subordinacion test",
        "reclasificacion ops ugpp aportes 5 por ciento mes ley 1607 de 2012",
        "ibc contratista 40 por ciento ingresos mensualizados decreto 1601 de 2022",
    ),
    source_label="contrato_prestacion_vs_laboral_anchor",
)
