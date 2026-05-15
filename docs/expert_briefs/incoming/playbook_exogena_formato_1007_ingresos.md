---
playbook_id: exogena-formato-1007-ingresos
categoria: informacion-exogena
playbook_tipo: estandar
aplicabilidad_regimen: ambos
aplicabilidad_tamano: ambos
fecha_corte: 2026-05-14
ag_aplicable: AG2025
---

# Formato 1007 — Ingresos recibidos

> Quien esté obligado a reportar exógena debe presentar el Formato 1007 con los ingresos recibidos durante el AG, identificando comprador/usuario, concepto y valor recibido. El total del 1007 debe cuadrar con los ingresos brutos de la declaración de renta y con el 300 de IVA.

## Cómo lo pregunta un contador

- ¿Qué reporto en el 1007?
- ¿Reporto ingresos no operacionales y rendimientos en el 1007?
- ¿Cómo manejo los anticipos de clientes en el 1007?
- ¿Reporto ingresos en especie o solo en efectivo?
- ¿Cómo cruzan los ingresos del 1007 con la declaración de renta?
- ¿Reporto al cliente persona natural sin NIT?
- ¿Qué hago con devoluciones en ventas — van en negativo?
- ¿Los ingresos del exterior van en el 1007?
- Formato 1007 conceptos AG 2025
- ¿Reporto ingresos exentos y no gravados en el 1007?

## Norma principal

- **Resolución DIAN 000162 de 2023 — art. 23** (Formato 1007 — Versión 9)
- URL oficial: <https://www.dian.gov.co/normatividad/Normatividad/Resoluci%C3%B3n%20000162%20de%2025-10-2023.pdf>
- Reporta ingresos recibidos durante el AG por todo concepto (operacionales y no operacionales), identificando contraparte.

## Normas relacionadas

| Norma | Para qué se cita | URL oficial |
|---|---|---|
| Art. 631 ET | Facultad DIAN de exigir información | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr026.htm#631> |
| Art. 26 ET | Renta líquida e ingresos | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr001.htm#26> |
| Art. 27 ET | Realización del ingreso | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr001.htm#27> |
| Art. 28 ET | Realización del ingreso para obligados a llevar contabilidad | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr001.htm#28> |
| Art. 651 ET | Sanción por inconsistencias | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr026.htm#651> |
| Formato 1001 (proveedor) | Cruce del lado del pagador | Res. DIAN 000162 de 2023 art. 17 |

## Respuesta operativa

1. **Sujetos obligados:** PJ y PN con ingresos brutos del AG anterior superiores al umbral fijado en la resolución vigente (regla general AG 2025: PJ ≥ 100.000 UVT, PN ≥ 500.000.000), agentes de retención, consorcios, fiducias, etc.
2. **Qué se reporta por cada ingreso:**
   - NIT/cédula del comprador o usuario.
   - Apellidos, nombres o razón social.
   - **Concepto** (4xxx según anexo técnico).
   - **Valor del ingreso bruto recibido** durante el AG.
   - **Devoluciones, rebajas y descuentos** asociados.
   - **Ingreso no gravado** asociado (si aplica).
3. **Conceptos típicos (anexo técnico Res. 000162/2023):**
   - **4001** — Ingresos por operaciones de ventas.
   - **4002** — Ingresos por servicios.
   - **4003** — Ingresos por honorarios.
   - **4004** — Ingresos por comisiones.
   - **4005** — Ingresos por intereses y rendimientos financieros.
   - **4006** — Ingresos por arrendamientos.
   - **4007** — Ingresos por dividendos y participaciones.
   - **4008** — Ingresos por enajenación de activos fijos.
   - **4009** — Ingresos por indemnizaciones.
   - **4010** — Otros ingresos no operacionales.
   - **4012** — Ingresos no constitutivos de renta ni ganancia ocasional.
4. **Cuantías mínimas:** se reportan ingresos cuando el acumulado anual con un mismo comprador/usuario sea **≥ $500.000** (verificar pesos exactos en resolución vigente). Por debajo, se acumulan con NIT genérico **222222222**.
5. **Ingresos en especie:** se reportan al valor de mercado en la fecha de realización.
6. **Devoluciones, rebajas y descuentos:** se reportan en columna separada por cada NIT en el mismo concepto, NO se restan del valor bruto del ingreso. El total devoluciones del 1007 debe cuadrar con devoluciones de la declaración de renta y del 300 IVA.
7. **Anticipos de clientes:** no son ingreso fiscal hasta su realización (art. 28 ET); se reportan cuando se cause el ingreso, no cuando se reciba el anticipo (salvo si la realización fiscal coincide con la caja).
8. **Cruce obligatorio:**
   - 1007 total ingresos = ingresos brutos formulario 110 / 210 (renglón total ingresos brutos).
   - 1007 por NIT de cliente ↔ 1001 del cliente (sus pagos).
   - 1007 ingresos operacionales gravados con IVA ↔ ingresos del 300 + 1006.
9. **Ingresos del exterior:** se reportan con NIT genérico **444444001** (o el asignado por la resolución) y código país del cliente.
10. **Ingresos exentos y no gravados:** se reportan en el 1007 separando el componente gravado y el componente no constitutivo (columna específica del formato). No omitir.

## Errores comunes en revisión DIAN

| Error | Severidad | Cómo evitarlo |
|---|---|---|
| Total ingresos 1007 ≠ ingresos brutos formulario 110/210 | ALTO | Conciliar mensualmente ingresos contables vs facturados vs reportables antes del cierre |
| Restar devoluciones del valor bruto en vez de reportarlas en columna separada | ALTO | Respetar campos del anexo técnico — devoluciones tienen su propia columna |
| Omitir ingresos no operacionales (rendimientos financieros, dividendos, ganancia en venta de activos) | ALTO | Revisar cuenta 42 PUC completa, no solo 41 |
| Reportar anticipos de clientes como ingreso del AG | MEDIO | Aplicar art. 28 ET — realización fiscal del ingreso |
| Olvidar ingresos del exterior por considerarlos "no aplica" | ALTO | Sí aplica — código país + NIT 444444001 |
| Discriminar mal ingreso gravado vs no constitutivo | MEDIO | Llevar trazabilidad en software por concepto y por naturaleza fiscal |

## Qué NO cubre este playbook

- Formato 1001 (lado del comprador) — playbook hermano.
- Formato 1006 (IVA generado) — playbook hermano.
- Realización fiscal del ingreso art. 27 y 28 ET → playbook independiente.
- Ingreso no constitutivo de renta ni ganancia ocasional (INCRNGO) → playbook independiente.

## Vigencia / Zona gris

- ¿Norma modificada recientemente? **Sí**. Res. DIAN 000162/2023 vigente para AG 2024 en adelante; verificar modificaciones posteriores.
- Zona gris: anticipos con factura emitida — la factura electrónica realiza el ingreso para efectos del 1007 aunque contablemente sea anticipo. Documentar política y cuadrar manualmente.
- URL versión vigente: <https://www.dian.gov.co/normatividad/Paginas/Resoluciones.aspx>

## Fuentes secundarias consultadas

- Actualícese — *Formato 1007: cómo reportar ingresos y cruzar con renta* — <https://actualicese.com/categoria/impuestos/informacion-exogena/>
- Gerencie.com — *Información exógena ingresos* — <https://www.gerencie.com/informacion-exogena.html>
- Accounter — *Errores en el formato 1007 que detecta la DIAN* — <https://accounter.co/>
- DIAN — *Anexo técnico Formato 1007 V9* — <https://www.dian.gov.co/impuestos/Servicios/Documents/>
