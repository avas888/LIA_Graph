---
playbook_id: exogena-formato-1003-retenciones
categoria: informacion-exogena
playbook_tipo: estandar
aplicabilidad_regimen: ordinario
aplicabilidad_tamano: ambos
fecha_corte: 2026-05-14
ag_aplicable: AG2025
---

# Formato 1003 — Retenciones en la fuente practicadas

> Los agentes de retención obligados a reportar exógena deben presentar el Formato 1003 con todas las retenciones en la fuente practicadas durante el AG, discriminadas por sujeto retenido, concepto y valor. Es el espejo del 1001 (pagos) y cuadra con la sumatoria anual de los formularios 350.

## Cómo lo pregunta un contador

- ¿Qué retenciones reporto en el 1003?
- ¿Reporto autorretenciones en el 1003?
- ¿Cómo cuadra el 1003 con las declaraciones mensuales 350?
- ¿Reporto retenciones de IVA y de ICA en el 1003?
- ¿Y la autorretención especial de renta del Decreto 2201 / 0261?
- ¿Reporto al sujeto retenido con NIT o cédula?
- ¿Qué hago si emití un certificado de retención con error después de presentar el 1003?
- ¿Diferencia entre retención asociada al 1001 y el 1003?
- Conceptos formato 1003 AG 2025
- ¿Reporto retenciones a beneficiarios del exterior en el 1003?

## Norma principal

- **Resolución DIAN 000162 de 2023 — art. 19** (Formato 1003 — Versión 7)
- URL oficial: <https://www.dian.gov.co/normatividad/Normatividad/Resoluci%C3%B3n%20000162%20de%2025-10-2023.pdf>
- Reporta cada retención en la fuente practicada por el agente retenedor durante el AG.

## Normas relacionadas

| Norma | Para qué se cita | URL oficial |
|---|---|---|
| Art. 365 a 419 ET | Marco de retención en la fuente | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr014.htm> |
| Art. 437-1 y 437-2 ET | Retención de IVA | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr015.htm#437-1> |
| Decreto 0261 de 2023 | Autorretención especial de renta — sustituye art. 1.2.6.6 a 1.2.6.11 DUR 1625/2016 | <https://www.suin-juriscol.gov.co/viewDocument.asp?id=30048220> |
| Decreto 572 de 2025 | Modificaciones tarifas y bases de retención AG 2025+ | <https://www.suin-juriscol.gov.co/> |
| Art. 651 ET | Sanción por errores en información | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr026.htm#651> |
| Formato 350 | Declaración mensual de retenciones (cruce con 1003) | <https://www.dian.gov.co/impuestos/Personas/Personas-Juridicas/Formularios-Retencion/Paginas/default.aspx> |

## Respuesta operativa

1. **Sujetos obligados:** todos los agentes de retención que cumplan el umbral general de exógena de la Res. 000162/2023 (PJ ≥ 100.000 UVT del AG anterior; PN ≥ 500.000.000) y los específicamente obligados por el art. 1 de la resolución (consorcios, fiducias, sociedades fiduciarias, etc.).
2. **Qué se reporta por registro:**
   - NIT/cédula del sujeto retenido.
   - Apellidos, nombres o razón social.
   - **Concepto de retención** (1xxx).
   - **Base sometida a retención** del pago.
   - **Valor de la retención practicada**.
3. **Conceptos típicos (anexo técnico):**
   - **1301** — Retención por salarios.
   - **1302** — Retención por honorarios.
   - **1303** — Retención por comisiones.
   - **1304** — Retención por servicios.
   - **1305** — Retención por arrendamientos.
   - **1306** — Retención por rendimientos financieros.
   - **1307** — Retención por compras.
   - **1308** — Retención por dividendos.
   - **1309** — Retención a no residentes (pagos al exterior).
   - **1310** — Retención por enajenación de activos fijos.
   - **1312** — Autorretención por venta de bienes y servicios.
   - **1320** — Retención de IVA.
   - **1331** — Autorretención especial de renta (Decreto 0261/2023).
4. **Cuándo se reporta el 1003 sin importar cuantía:** todas las retenciones practicadas durante el AG, sin tope mínimo. El umbral por cuantía solo aplica al 1001 (pago), no al 1003 (retención).
5. **Autorretención:** se reporta en el 1003 con el NIT del propio reportante como sujeto retenido (concepto 1312 venta + 1331 especial renta), reflejando que el agente actuó simultáneamente como retenido y como retenedor.
6. **Cruce obligatorio:**
   - Total retenciones 1003 por concepto = sumatoria anual del **renglón equivalente del Formulario 350** de los 12 meses.
   - 1003 por sujeto retenido ↔ retención asociada al 1001 del mismo NIT.
   - 1003 por sujeto retenido ↔ certificados de retención emitidos (art. 381 ET).
   - Total retenciones IVA 1003 ↔ retenciones IVA pagadas en 350 + 300.
7. **Certificados de retención:** el certificado anual emitido al sujeto retenido (formato 220 — rentas de trabajo; certificado libre — otros conceptos) debe coincidir con lo reportado en el 1003. Diferencias generan reclamos del retenido y cartas DIAN.
8. **Retenciones a beneficiarios del exterior:** se reportan en el 1003 con NIT **444444001** y código país, concepto 1309. La tarifa aplicada (15 %, 20 %, etc.) debe corresponder al art. 408 ET o al CDI aplicable.
9. **Reversión de retención:** si se reversa una retención por anulación de la operación, se reporta con valor negativo en el período correspondiente del AG. Si la reversión es en el AG siguiente, se gestiona como reintegro art. 1.2.4.16 DUR 1625/2016.

## Errores comunes en revisión DIAN

| Error | Severidad | Cómo evitarlo |
|---|---|---|
| Total retenciones 1003 ≠ sumatoria de las declaraciones 350 del AG | ALTO | Conciliar mes a mes antes de presentar; usar archivo de cuadre por concepto |
| Concepto de retención incorrecto (honorarios vs servicios) | ALTO | Validar contra naturaleza del pago y tarifa aplicada — la inconsistencia se ve en el cruce con el 1001 |
| Omitir autorretención especial de renta del Decreto 0261/2023 | ALTO | Concepto 1331 — se reporta como retenido y como agente simultáneamente |
| Reportar la base sin discriminar pago gravado vs no gravado | MEDIO | Solo va la base sometida a retención, no el bruto |
| No reportar retenciones a beneficiarios del exterior | ALTO | Concepto 1309 + NIT 444444001 + código país |
| Certificado del retenido no cuadra con el 1003 | MEDIO | Antes de emitir certificados anuales, validar contra el archivo del 1003 |

## Qué NO cubre este playbook

- Tablas de retención AG 2025/2026 → `playbook_retencion_tablas_ag_2025_2026.md`.
- Autorretención especial de renta Decreto 0261/2023 → playbook independiente.
- Retención de ICA (territorial) → no va en el 1003; se reporta a las secretarías de hacienda municipales según norma local.
- Formato 1001 (pagos) — playbook hermano.

## Vigencia / Zona gris

- ¿Norma modificada recientemente? **Sí**. Res. DIAN 000162/2023 + Decreto 572/2025 (tarifas) + Decreto 0261/2023 (autorretención).
- Zona gris: pagos del exterior con CDI — la retención reducida exige certificado de residencia fiscal del beneficiario; sin él, aplica tarifa plena del art. 408 ET y la diferencia no se puede reportar como retenida.
- URL versión vigente: <https://www.dian.gov.co/normatividad/Paginas/Resoluciones.aspx>

## Fuentes secundarias consultadas

- Actualícese — *Formato 1003: cómo cuadrar retenciones del 350 con la exógena* — <https://actualicese.com/categoria/impuestos/informacion-exogena/>
- Gerencie.com — *Información exógena retenciones en la fuente* — <https://www.gerencie.com/informacion-exogena.html>
- Accounter — *Cruce 1003 ↔ 350 ↔ certificados de retención* — <https://accounter.co/>
- DIAN — *Anexo técnico Formato 1003 V7* — <https://www.dian.gov.co/impuestos/Servicios/Documents/>
