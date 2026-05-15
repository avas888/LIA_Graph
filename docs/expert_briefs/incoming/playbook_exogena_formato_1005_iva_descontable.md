---
playbook_id: exogena-formato-1005-iva-descontable
categoria: informacion-exogena
playbook_tipo: estandar
aplicabilidad_regimen: ordinario
aplicabilidad_tamano: ambos
fecha_corte: 2026-05-14
ag_aplicable: AG2025
---

# Formato 1005 — IVA descontable

> Los responsables del IVA con ingresos del AG anterior por encima del umbral fijado en la Res. DIAN 000162 de 2023 deben reportar en el Formato 1005 cada operación que generó IVA descontable durante el AG, identificando proveedor, base gravable, IVA descontable y tipo de operación.

## Cómo lo pregunta un contador

- ¿Qué umbral aplica para reportar el 1005?
- ¿Reporto el IVA descontable mes a mes o anual?
- ¿Cómo cruza el 1005 con la declaración de IVA (300)?
- ¿Qué hago si me devuelven una factura después de reportar?
- ¿IVA descontable en importaciones va en el 1005?
- ¿Reporto las facturas exentas y excluidas en el 1005?
- ¿Cómo amarro el 1005 mío con el 1006 del proveedor?
- ¿Reverso un IVA descontable y cómo se refleja en exógena?
- IVA descontable proporcional — formato 1005
- Formato 1005 conceptos y discriminación por tipo

## Norma principal

- **Resolución DIAN 000162 de 2023 — art. 21** (Formato 1005 — Versión 7)
- URL oficial: <https://www.dian.gov.co/normatividad/Normatividad/Resoluci%C3%B3n%20000162%20de%2025-10-2023.pdf>
- Reporta IVA descontable por operación, por proveedor, por mes y por concepto (compra de bienes, servicios, importaciones, devoluciones).

## Normas relacionadas

| Norma | Para qué se cita | URL oficial |
|---|---|---|
| Art. 631 ET | Facultad DIAN de exigir información | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr026.htm#631> |
| Art. 488 ET | Procedencia del IVA descontable | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr017.htm#488> |
| Art. 490 ET | IVA descontable proporcional | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr017.htm#490> |
| Art. 651 ET | Sanción por errores en exógena | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr026.htm#651> |
| Formato 1006 | Cruce con IVA generado del proveedor | Res. DIAN 000162 de 2023 art. 22 |
| Formato 300 | Declaración bimestral o cuatrimestral de IVA | <https://www.dian.gov.co/impuestos/Personas/Personas-Juridicas/IVA/Paginas/default.aspx> |

## Respuesta operativa

1. **Sujetos obligados:** responsables del IVA (antes "régimen común") que cumplan el umbral de ingresos brutos del AG anterior fijado en la Res. 000162/2023 (verificar resolución vigente — generalmente PJ ≥ 100.000 UVT y PN ≥ 500.000.000 ingresos brutos).
2. **Qué se reporta por cada operación:**
   - NIT/cédula del proveedor.
   - Apellidos, nombres o razón social.
   - **Base gravable** del IVA descontable.
   - **Valor del IVA descontable**.
   - Tarifa aplicada (5 %, 19 %, etc.).
   - Concepto: bienes, servicios, importaciones, devoluciones, retenciones, etc.
3. **Periodicidad del reporte:** **anual** (consolidado de los 6 bimestres o 3 cuatrimestres del AG), pero el archivo debe permitir identificar el período fiscal al que pertenece cada operación según el anexo técnico vigente.
4. **Cruce obligatorio con declaración 300:**
   - Suma del IVA descontable del 1005 = suma del renglón "Total IVA descontable" de todas las declaraciones 300 del AG.
   - Diferencias > 1 UVT activan validación de inconsistencia y carta DIAN.
5. **IVA descontable en importaciones:** sí se reporta, con el NIT del proveedor del exterior (444444001 o el código que asigne la resolución), valor declarado en la importación + IVA pagado en aduana.
6. **Devoluciones de compras y notas crédito:** se reportan con valor negativo en el período en que se generaron, manteniendo NIT del proveedor original.
7. **IVA descontable proporcional (art. 490 ET):** cuando el responsable tiene operaciones gravadas, exentas y excluidas, debe aplicar la proporcionalidad en la declaración 300 y reportar en 1005 únicamente la porción descontable efectivamente tomada.
8. **Operaciones exentas y excluidas del proveedor:** no generan IVA descontable, no van en el 1005. Su contraparte se reporta en el 1001 sin componente de IVA.

## Errores comunes en revisión DIAN

| Error | Severidad | Cómo evitarlo |
|---|---|---|
| Suma del 1005 distinta a la del 300 | ALTO | Conciliar mensualmente IVA descontable contable vs declarado vs reportable |
| Reportar IVA descontable de facturas no vigentes en facturación electrónica | ALTO | Solo IVA soportado por factura electrónica validada DIAN da derecho a descuento desde AG 2022 |
| Olvidar reversar IVA descontable de operaciones anuladas | MEDIO | Cruzar notas crédito recibidas contra facturas originalmente reportadas |
| Reportar el IVA mayor valor del costo en el 1005 | MEDIO | El IVA no descontable va al 1001 concepto 5060, no al 1005 |
| Cruzar mal con el 1006 del proveedor por usar NIT distinto | MEDIO | Validar NIT del proveedor con su RUT antes de cierre |

## Qué NO cubre este playbook

- Formato 1006 (IVA generado del lado del proveedor) — playbook hermano.
- Proporcionalidad del IVA descontable art. 490 ET → playbook `playbook_iva_descontable_proporcionalidad.md`.
- Régimen Simple SIMPLE: contribuyentes RST no llevan IVA descontable salvo grupo específico — verificar art. 907 ET.

## Vigencia / Zona gris

- ¿Norma modificada recientemente? **Sí**. Res. DIAN 000162/2023 vigente para AG 2024 en adelante.
- Zona gris: facturas electrónicas rechazadas dentro del plazo (art. 771-2 ET) — si el rechazo es posterior al reporte original, se hace corrección con valor negativo en el período correspondiente.
- URL versión vigente: <https://www.dian.gov.co/normatividad/Paginas/Resoluciones.aspx>

## Fuentes secundarias consultadas

- Actualícese — *Formato 1005: cruce con la declaración de IVA* — <https://actualicese.com/categoria/impuestos/informacion-exogena/>
- Gerencie.com — *Información exógena IVA descontable* — <https://www.gerencie.com/informacion-exogena.html>
- DIAN — *Anexo técnico Formato 1005 V7* — <https://www.dian.gov.co/impuestos/Servicios/Documents/>
