---
playbook_id: iva-descontable-proporcionalidad
categoria: iva
playbook_tipo: extendido
aplicabilidad_regimen: ordinario
aplicabilidad_tamano: ambos
fecha_corte: 2026-05-14
ag_aplicable: AG2025
---

# IVA descontable y prorrateo (arts. 488 a 491 ET)

> El IVA descontable se rige por la regla de **vinculación con operaciones gravadas o exentas** (art. 488 ET). Cuando hay operaciones gravadas + exentas + excluidas, debe aplicarse **prorrateo** (art. 490 ET). Oportunidad para descontar: el **mismo bimestre** o los **3 bimestres siguientes** (art. 496 ET).

## Cómo lo pregunta un contador

- ¿Cuándo es descontable el IVA pagado en compras?
- ¿Cómo se calcula la proporcionalidad del IVA descontable?
- ¿Qué pasa si tengo operaciones gravadas y excluidas?
- ¿Puedo descontar el IVA de un gasto de administración general?
- ¿Cuál es el plazo para descontar el IVA?
- ¿La proporcionalidad se recalcula al cierre?
- Art. 488 ET — IVA descontable
- Art. 490 ET — proporcionalidad cuando hay operaciones de varios tipos
- Art. 496 ET — oportunidad para el IVA descontable
- ¿El IVA en activos fijos se descuenta o se capitaliza?

## Norma principal

- **Art. 488 ET — Sólo son descontables los impuestos originados en operaciones que constituyan costo o gasto**
- URL oficial: <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr018.htm#488>
- URL espejo: <https://estatuto.co/488>
- Regla general de descontabilidad: el IVA debe corresponder a operaciones que constituyan costo o gasto del responsable según el ET y estar **directamente relacionado** con operaciones gravadas o exentas. Modificado por reformas posteriores; lectura conjunta con art. 489 ET (IVA descontable por exportadores) y art. 490 ET (prorrateo).

## Normas relacionadas

| Norma | Para qué se cita | URL oficial |
|---|---|---|
| Art. 485 ET | Impuestos descontables — regla general | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr018.htm#485> |
| Art. 489 ET | IVA descontable para exportadores | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr018.htm#489> |
| Art. 490 ET | Proporcionalidad — operaciones gravadas, exentas y excluidas | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr018.htm#490> |
| Art. 491 ET | IVA en compras de activos fijos — no descontable como regla general | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr018.htm#491> |
| Art. 496 ET | Oportunidad — bimestre de causación o 3 siguientes | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr019.htm#496> |
| Art. 771-5 ET | Medios de pago para procedencia de costos y descontables | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr030.htm#771-5> |

## Fórmula de proporcionalidad (art. 490 ET)

Cuando los bienes o servicios adquiridos **se destinen indistintamente** a operaciones gravadas, exentas y excluidas y **no sea posible identificar la destinación** específica, el IVA descontable se calcula así:

```
IVA descontable proporcional = IVA pagado × (Ingresos gravados + Ingresos exentos) / Total de ingresos
```

Donde:
- **Numerador** = ingresos por operaciones **gravadas** (cualquier tarifa) + ingresos por operaciones **exentas** (tarifa 0 % con derecho a descuento).
- **Denominador** = **total** de ingresos del responsable en el período (gravadas + exentas + **excluidas** + no gravadas).
- Si el resultado da un porcentaje **< 100 %**, parte del IVA pagado pasa a mayor valor del costo o gasto (no es descontable).

### Ejemplo numérico

PYME comercializadora con operaciones mixtas en el bimestre:
- Venta de bienes gravados al 19 %: **$200.000.000**
- Venta de bienes exentos (art. 477 ET, p. ej. exportaciones): **$50.000.000**
- Venta de bienes excluidos (art. 424 ET): **$50.000.000**
- **Total ingresos:** **$300.000.000**

IVA pagado en gastos comunes (arriendo, energía, papelería, asesoría) del bimestre: **$5.700.000** (sobre base $30.000.000 al 19 %).

Aplicación del prorrateo:
- Proporción descontable = ($200.000.000 + $50.000.000) / $300.000.000 = **83,33 %**
- IVA descontable = $5.700.000 × 83,33 % = **$4.750.000**
- IVA NO descontable (pasa a costo o gasto) = $5.700.000 × 16,67 % = **$950.000**

Para gastos **directamente identificables** con una sola línea (por ejemplo, comisión sobre venta de bien excluido), NO se aplica prorrateo: se asigna 100 % a esa línea. Si la línea es excluida, el IVA es 100 % no descontable.

## Respuesta operativa

1. **Requisitos sustanciales para descontar (art. 488 ET):**
   - La compra constituye **costo o gasto** según el ET.
   - Está **vinculada** con operaciones gravadas o exentas.
   - El IVA está soportado en **factura electrónica de venta válida** (con NIT del vendedor, descripción, IVA discriminado).
   - El pago se hizo por **medios bancarizados** (art. 771-5 ET) en los topes legales.
   - Se descuenta dentro del **bimestre de causación** o en los **3 bimestres siguientes** (art. 496 ET).
2. **Método general — prorrateo art. 490 ET:** aplicar cuando hay mezcla de gravadas + exentas + excluidas y los gastos no son identificables. Fórmula y ejemplo arriba.
3. **Método especial — separación contable:**
   - Identificar gastos directamente atribuibles a cada línea (gravadas, exentas, excluidas).
   - IVA en compras para operaciones **gravadas o exentas** → descontable 100 %.
   - IVA en compras para operaciones **excluidas** → NO descontable, pasa a costo o gasto.
   - IVA en gastos comunes indivisibles → aplicar prorrateo del art. 490 ET.
   - Este método requiere centros de costo o cuentas analíticas diferenciadas.
4. **Activos fijos (art. 491 ET — regla general):** el IVA pagado en la adquisición de activos fijos **NO es descontable** como regla general. Excepciones donde sí descuenta (verificar reformas vigentes):
   - **Maquinaria industrial** (régimen de descuento en renta, no en IVA — art. 258-1 ET).
   - **Bienes de capital** en casos puntuales por reformas (Ley 2010 de 2019).
   - El IVA no descontable de activos fijos **forma parte del costo** depreciable.
5. **Oportunidad — art. 496 ET:** el IVA descontable puede tomarse en:
   - El **bimestre o cuatrimestre** en que se causó (según periodicidad del responsable).
   - O en uno de los **tres períodos siguientes** (3 bimestres o 3 cuatrimestres).
   - Pasado ese plazo, **se pierde el derecho** al descuento.
6. **Cierre del año fiscal — ajuste opcional:** algunos contribuyentes con operaciones muy variables practican un **ajuste anual de proporcionalidad** comparando la proporción acumulada del año con la aplicada bimestralmente. La DIAN ha aceptado el ajuste por papel de trabajo cuando se documenta.
7. **Tratamiento de devoluciones, rebajas y descuentos:** las notas crédito recibidas por el comprador **reducen** el IVA descontable del período en que se reciben. Si ya se había declarado, se ajusta en el próximo período.
8. **Soporte fiscal:** **factura electrónica de venta** con código QR, CUFE y validación DIAN. Sin factura electrónica válida, no procede el descuento. Documentos equivalentes (POS, tiquetes) NO dan derecho a IVA descontable cuando el comprador es responsable (art. 616-1 ET).
9. **Impuestos descontables no aceptados:** IVA en gastos no deducibles en renta (sin causalidad, lujosos personales, gastos sin soporte), IVA pagado a no responsables (que no debieron cobrarlo), IVA por encima de la tarifa legal, IVA por adquisiciones de personas físicas no inscritas en factura electrónica.

## Errores comunes en revisión DIAN

| Error | Severidad | Cómo evitarlo |
|---|---|---|
| Descontar 100 % cuando hay operaciones excluidas (sin prorrateo) | CRÍTICO | Aplicar art. 490 ET cuando hay mezcla |
| Descontar IVA de activos fijos como regla general | ALTO | Art. 491 ET — no descuento, va al costo del activo |
| Descontar IVA pagado a un "no responsable" | ALTO | Si el proveedor no debió cobrar IVA, descuento improcedente |
| Tomar IVA descontable después del 4° bimestre | ALTO | Plazo art. 496 ET — perentorio |
| Descontar IVA en tiquete POS siendo responsable | ALTO | Solo factura electrónica da derecho |
| No bancarizar pagos sobre topes art. 771-5 ET | ALTO | Rechazo del descuento y del costo |
| Ignorar notas crédito que reducen IVA descontable | MEDIO | Ajustar al período de recepción |

## Qué NO cubre este playbook

- Devolución de saldos a favor de IVA → playbook `playbook_iva_devolucion_saldos_favor.md`.
- IVA en exportaciones (régimen específico art. 479-481 ET) → playbook exportaciones.
- IVA en importaciones (mecánica de pago y descuento) → playbook importaciones.
- IVA en servicios desde el exterior (régimen del art. 437-2 num. 8) → playbook independiente.

## Vigencia / Zona gris

- ¿Norma modificada recientemente? **Sí** — Ley 1819 de 2016, Ley 2010 de 2019. La Ley 2277 de 2022 ajustó descuentos en renta vinculados (art. 258-1 ET).
- URL versión vigente: <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr018.htm#488>
- Zona gris: tratamiento del IVA en gastos de representación, viáticos y atenciones — la DIAN restringe a los que demuestren causalidad y soporte fehaciente. Posición conservadora: no descontar si el gasto no es deducible plenamente en renta.

## Fuentes secundarias consultadas

- DIAN — Concepto Unificado del IVA (vigente).
- Actualícese — *IVA descontable — prorrateo en operaciones mixtas* — <https://actualicese.com/iva-descontable-prorrateo/>
- Gerencie.com — *Proporcionalidad del IVA descontable* — <https://www.gerencie.com/proporcionalidad-iva-descontable.html>
- KPMG Colombia — *IVA — guía práctica AG 2025*.
