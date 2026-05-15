"""v17 b2 — DSPNE (Documento Soporte de Pago de Nómina Electrónica).

Anchored at ET art. 617 (FE / sistema técnico de control general). El
régimen sustantivo está en Resolución DIAN 000013/2021 (modificada por
000037/2021 y posteriores), DUR 1625/2016 art. 1.6.1.4.30 ss, citados en
bullets. Soportes adicionales: art. 107 ET (procedencia deducciones) +
art. 771-2 ET (soporte FE).
"""
from __future__ import annotations

from ..case_detectors import is_nomina_electronica_dspne_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="nomina_electronica_dspne",
    detector=is_nomina_electronica_dspne_case,
    bullets=(
        "**Quién está obligado (Resolución DIAN 000013/2021):** todo contribuyente del impuesto sobre la renta que **realice pagos derivados de una relación laboral o legal y reglamentaria** y **pretenda deducirlos** en renta. Incluye sociedades, sucursales, EPs, ESAL contribuyentes, personas naturales declarantes con empleados, y **Régimen Simple** (el SIMPLE no exime del DSPNE si va a deducir).",
        "**Plazo de generación y transmisión:** **dentro de los 10 primeros días calendario del mes siguiente** al período de la nómina pagada. Ej.: nómina pagada el 31 oct → DSPNE transmitido antes del **10 nov**.",
        "**Componentes del DSPNE:** identificación del empleador (NIT) y del empleado (NIT/cédula) + período + conceptos de **devengados** (salarios, auxilios, horas extras, vacaciones, prima, cesantías, comisiones, bonos) + conceptos de **deducciones** (salud, pensión, retención fuente, embargos, libranzas, aportes voluntarios) + total devengado, deducido y a pagar + firma electrónica del empleador.",
        "**Notas de ajuste de nómina electrónica (NIESN):** para **corregir** o **anular** un DSPNE emitido. Vinculadas al **CUNE** (Código Único de Nómina Electrónica) del documento original. Plazo igual de 10 días calendario; pueden emitirse después con justificación, idealmente antes del cierre fiscal del AG.",
        "**Cómo transmitir — dos vías:** (a) servicio gratuito DIAN desde MUISCA (apta para microempleadores) — requiere certificado digital del representante legal vigente; (b) **proveedor tecnológico autorizado** (Aleph, ESign, The Factory HKA, Carvajal, entre otros). Tarifas variables según volumen.",
        "**Pérdida de deducibilidad — consecuencia clave:** si el empleador **no genera el DSPNE** o lo hace fuera de plazo de manera sistemática, la DIAN puede **rechazar la deducción del pago laboral en renta** (art. 771-2 ET + art. 617 ET — sistema técnico de control). Pérdida observada en revisión: ≈ **15 % del costo laboral promedio anual** cuando el incumplimiento es total.",
        "**Sanciones específicas + alcance:** **art. 651 ET** — sanción por no enviar información, hasta **15.000 UVT**, reducible por gravedad y subsanación; **art. 647 ET** — inexactitud si el incumplimiento se mantiene tras requerimiento. **El DSPNE NO reemplaza la PILA** — DSPNE soporta deducción frente a renta; PILA acredita aportes a SGSS y parafiscales (requisito separado del **art. 108 ET**). **Contratistas PN (servicios independientes) NO van por DSPNE** — van por factura electrónica del contratista o documento soporte de adquisiciones a no obligados a facturar.",
    ),
    keywords=(
        "nómina electrónica", "nomina electronica",
        "dspne",
        "documento soporte de pago de nómina", "documento soporte de pago de nomina",
        "resolución 000013 de 2021", "resolucion 000013 de 2021",
        "resolución 000037 de 2021", "resolucion 000037 de 2021",
        "resolución 000063 de 2021", "resolucion 000063 de 2021",
        "resolución 000165 de 2023", "resolucion 000165 de 2023",
        "cune",
        "niesn",
        "nota de ajuste de nómina", "nota de ajuste de nomina",
        "art. 107 et", "art 107 et",
        "art. 617", "art 617",
        "art. 771-2", "art 771-2", "771-2",
        "art. 651", "art 651",
        "art. 647", "art 647",
        "10 días calendario", "10 dias calendario",
        "10 primeros días", "10 primeros dias",
        "dur 1625",
        "decreto único reglamentario", "decreto unico reglamentario",
        "muisca",
        "proveedor tecnológico", "proveedor tecnologico",
        "aleph", "the factory hka", "carvajal", "esign",
        "firma electrónica", "firma electronica",
        "certificado digital",
        "régimen simple", "regimen simple",
        "15.000 uvt", "15000 uvt",
        "anexo técnico", "anexo tecnico",
        "deducción laboral", "deduccion laboral",
        "pérdida deducibilidad", "perdida deducibilidad",
    ),
    anchor_articles=("617",),
    search_queries=(
        "documento soporte pago nomina electronica dspne resolucion 000013 de 2021",
        "art 617 et sistema tecnico control art 771-2 et soporte deducciones laborales",
        "cune niesn nota de ajuste nomina electronica plazo 10 dias",
    ),
    source_label="nomina_electronica_dspne_anchor",
)
