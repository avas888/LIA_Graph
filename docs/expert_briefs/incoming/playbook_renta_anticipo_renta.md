---
playbook_id: renta-anticipo-renta
categoria: renta-procedimiento
playbook_tipo: estandar
aplicabilidad_regimen: ordinario
aplicabilidad_tamano: ambos
fecha_corte: 2026-05-14
ag_aplicable: AG2025
---

# Anticipo del impuesto de renta (arts. 807 y 809 ET)

> El anticipo del impuesto de renta se liquida en la declaración del AG y se imputa al impuesto del año siguiente. La base general es el **75 %** del impuesto neto de renta del AG, con tres métodos de cálculo y reglas especiales para primera declaración (25 %) y segunda (50 %).

## Cómo lo pregunta un contador

- ¿Cómo se calcula el anticipo de renta?
- ¿Cuál de los tres métodos del art. 807 me conviene?
- ¿El anticipo del primer año es del 25 % o del 50 %?
- ¿Puedo solicitar reducción del anticipo si las ventas bajaron?
- ¿Cómo solicito la reducción ante la DIAN?
- ¿El anticipo del año anterior se cruza con el impuesto del año actual?
- ¿Las personas jurídicas del RST liquidan anticipo?
- Art. 807 ET — base y porcentaje del anticipo
- Art. 809 ET — reducción del anticipo
- ¿El anticipo se ajusta si las retenciones del año fueron altas?

## Norma principal

- **Art. 807 ET — Cálculo del anticipo del impuesto de renta**
- URL oficial: <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr032.htm#807>
- URL espejo: <https://estatuto.co/807>
- Establece el **75 %** como porcentaje general del anticipo, con porcentajes reducidos para primera declaración (**25 %**) y segunda declaración (**50 %**), tres métodos de base (impuesto neto del año, promedio de los dos últimos años, o promedio del año declarado y el anterior), y la imputación al año siguiente.

## Normas relacionadas

| Norma | Para qué se cita | URL oficial |
|---|---|---|
| Art. 808 ET | Casos en que no se calcula anticipo | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr032.htm#808> |
| Art. 809 ET | Solicitud de reducción del anticipo | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr032.htm#809> |
| Art. 810 ET | Designación del Ministerio de Hacienda | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr032.htm#810> |
| Art. 911 ET | Anticipo bimestral en RST | <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr034.htm#911> |

## Respuesta operativa

1. **Identifique el porcentaje aplicable al AG según historial del contribuyente:**
   - **Primera declaración de renta:** **25 %** del impuesto neto del AG.
   - **Segunda declaración:** **50 %** del promedio de los impuestos netos de los dos últimos años (o 50 % del impuesto del AG, lo que sea menor).
   - **Tercera declaración en adelante:** **75 %** sobre la base que elija el contribuyente.
2. **Elija la base más favorable entre las tres opciones del art. 807 ET (para 75 %):**
   - **Opción A:** 75 % del impuesto neto del AG declarado.
   - **Opción B:** 75 % del **promedio** del impuesto neto del AG declarado y del AG anterior.
   - El contribuyente elige la **menor**. Documentar la elección en papel de trabajo.
3. **Reste las retenciones en la fuente practicadas durante el AG.** El anticipo final = (porcentaje × base) − retenciones a favor del AG. Si el resultado es negativo, el anticipo es **cero**, no genera saldo a favor por sí solo.
4. **Imputación al año siguiente:** el anticipo liquidado en la declaración del AG se imputa como pago al impuesto de renta del AG siguiente. El contribuyente lo declara en el renglón "Anticipo del año anterior" del formulario 110 del AG siguiente.
5. **Reducción del anticipo (art. 809 ET):** procede solicitud cuando el contribuyente prevé que el impuesto del AG siguiente será inferior. La solicitud se presenta **antes del 31 de julio del año siguiente al que se liquida el anticipo** ante la dirección seccional. Causales típicas: reducción de ingresos ≥ 25 %, terminación de la actividad, factores comprobables. La DIAN debe responder en **2 meses**; silencio administrativo positivo.
6. **Casos sin anticipo (art. 808 ET):**
   - Contribuyentes que dejan de existir (liquidación de la sociedad) en el AG.
   - Personas naturales no obligadas a llevar contabilidad que demuestran que su impuesto del AG siguiente será cero.
   - Contribuyentes del RST: liquidan **anticipos bimestrales** propios del régimen (art. 911 ET) y NO anticipo anual ordinario.
7. **Tratamiento contable:** registrar el anticipo como cuenta por cobrar de impuestos (1355 — "Anticipo de impuestos") al cierre del AG. Al año siguiente se cruza contra la obligación.
8. **Tip:** cuando el AG actual es atípicamente alto (ingreso extraordinario, venta de activos), comparar las dos opciones de base del art. 807 ET. El **promedio** suele ser más favorable porque suaviza el pico.

## Errores comunes en revisión DIAN

| Error | Severidad | Cómo evitarlo |
|---|---|---|
| Aplicar 75 % en primera o segunda declaración | ALTO | Verificar historial del RUT — primera = 25 %, segunda = 50 % |
| Liquidar anticipo en RST en vez de anticipos bimestrales | ALTO | RST tiene mecánica propia (art. 911 ET) |
| No restar retenciones del AG al cálculo del anticipo | MEDIO | El anticipo se neutraliza parcialmente con retenciones |
| Solicitar reducción después del 31 de julio | MEDIO | Plazo legal del art. 809 ET no es prorrogable |
| Olvidar imputar el anticipo del año anterior en el AG actual | ALTO | Revisar renglón "Anticipo del año anterior" del formulario |

## Qué NO cubre este playbook

- Anticipos bimestrales del RST (art. 911 ET) → playbook RST.
- Tratamiento del saldo a favor cuando el anticipo + retenciones supera el impuesto → playbook `playbook_renta_devolucion_saldos_favor.md`.
- Sanciones por no incluir el anticipo en la declaración → sanción por inexactitud, playbook `playbook_renta_sancion_inexactitud.md`.

## Vigencia / Zona gris

- ¿Norma modificada recientemente? **No** sustancialmente. Art. 807 ET vigente con sus modificaciones históricas.
- URL versión vigente: <https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario_pr032.htm#807>
- Zona gris: definición de "primera declaración" cuando hay reorganizaciones empresariales (fusión, escisión) — la posición conservadora es contar desde el RUT del nuevo NIT.

## Fuentes secundarias consultadas

- Actualícese — *Anticipo del impuesto de renta — cómo calcularlo* — <https://actualicese.com/anticipo-renta/>
- Gerencie.com — *Anticipo del impuesto de renta* — <https://www.gerencie.com/anticipo-del-impuesto-de-renta.html>
- INCP — *Reducción del anticipo art. 809 ET*.
