# Evaluación del Corpus Contable — 30 Preguntas y Respuestas Modelo

**Propósito:** Benchmark para comparar el desempeño de Lía Contadores (RAG), Lía Graph (RAG) y Claude Sonnet 4.6 contra respuestas modelo derivadas exclusivamente del corpus.

**Fecha de generación:** 19 de abril de 2026
**Corpus de referencia:** Corpus Lia Contador — CORE ya Arriba (producción)
**Parámetros vigentes:** UVT 2025 = $49.799 | UVT 2026 = $52.374 | SMLMV 2026 = $1.750.905

---

## Cobertura temática

Las 30 preguntas se distribuyen en 10 macro-áreas del corpus, asegurando cobertura uniforme:

| # | Macro-área | Preguntas | Carpetas del corpus cubiertas |
|---|-----------|-----------|-------------------------------|
| A | Renta PJ (deducciones, TTD, beneficio auditoría, anticipo, tarifas) | Q1–Q5 | RENTA/ |
| B | IVA (periodicidad, prorrata, saldos a favor) | Q6–Q7 | IVA_COMPLETO/ |
| C | Retención en la fuente | Q8–Q9 | RETENCION_FUENTE_AGENTE/ |
| D | Facturación electrónica | Q10–Q11 | FACTURACION_ELECTRONICA_OPERATIVA/ |
| E | RST (Régimen Simple de Tributación) | Q12–Q13 | RST_REGIMEN_SIMPLE/ |
| F | Nómina, laboral, tiempo parcial, pensiones | Q14–Q17 | NOMINA_SEGURIDAD_SOCIAL/, REFORMA_LABORAL_LEY_2466/, TRABAJO_TIEMPO_PARCIAL/, REFORMA_PENSIONAL/ |
| G | NIIF PYMEs y obligaciones mercantiles | Q18–Q19 | NIIF_PYMES_GRUPO2/, OBLIGACIONES_MERCANTILES/ |
| H | Procedimiento tributario (sanciones, firmeza, devoluciones, exógena) | Q20–Q23 | REGIMEN_SANCIONATORIO/, FIRMEZA_DECLARACIONES_ART714/, DEVOLUCIONES_SALDOS_FAVOR/, INFORMACION_EXOGENA_2026/ |
| I | Impuestos especiales (GMF, ICA, patrimonio, dividendos) | Q24–Q26 | GMF_4X1000/, ICA_INDUSTRIA_COMERCIO/, IMPUESTO_PATRIMONIO_PN/, DIVIDENDOS_UTILIDADES/ |
| J | Compliance y temas especiales (SAGRILAFT, ZOMAC, pérdidas fiscales, obligaciones del contador) | Q27–Q30 | SAGRILAFT_PTEE/, ZOMAC_INCENTIVOS/, PERDIDAS_FISCALES_ART147/, OBLIGACIONES_PROFESIONALES_CONTADOR/, BENEFICIARIO_FINAL_RUB/ |

**Tipo de pregunta:** S = pregunta de punto único | M = pregunta multipunto (2-3 sub-preguntas)
**Distribución:** 15 S + 15 M

---

## Pregunta 1 (S) — Renta: Deducción por factura electrónica

**Pregunta inicial:**
Colega, tengo un cliente SAS comercializadora con ingresos brutos de $3.000 millones en el AG 2025. Todas sus compras están soportadas con factura electrónica validada. ¿Cuánto puede deducir por el beneficio del 1% de facturación electrónica y cómo lo registro en el Formulario 110?

**Respuesta modelo:**
El beneficio está en el Art. 7 de la Ley 2277 de 2022. Su cliente puede tomar como deducción el 1% del total de compras soportadas con factura electrónica validada ante la DIAN durante el año gravable. Sin embargo, esa deducción tiene un tope de 240 UVT.

Hagamos el cálculo: si las compras con factura electrónica son $3.000.000.000, el 1% sería $30.000.000. Pero el tope de 240 UVT para AG 2025 es 240 × $49.799 = $11.951.760. Como $30M excede el tope, la deducción permitida es de $11.951.760.

A tarifa del 35%, eso le genera un ahorro fiscal de $11.951.760 × 35% = $4.183.116. Se incluye en el renglón 63 del Formulario 110.

Requisitos clave: (i) la factura electrónica debe estar validada por la DIAN — no basta con que se haya emitido; (ii) el soporte documental debe cumplir Art. 771-2 ET; y (iii) las compras deben cumplir el test de causalidad, necesidad y proporcionalidad del Art. 107 ET.

**Pregunta de seguimiento:**
¿Y qué pasa si parte de esas compras se pagaron en efectivo? ¿Puedo tomar la deducción del 1% sobre compras que excedieron el límite de pagos en efectivo del Art. 771-5?

**Respuesta modelo (seguimiento):**
Buena pregunta. Son dos filtros independientes. El Art. 771-5 ET limita la deducibilidad de pagos en efectivo a 100 UVT por transacción individual ($4.979.900 para AG 2025). Si una compra se pagó en efectivo y superó ese tope, esa compra pierde su deducibilidad como costo o gasto — independientemente de si tiene factura electrónica.

En la práctica, la deducción del 1% por factura electrónica (Art. 7, Ley 2277/2022) se calcula sobre compras con factura electrónica validada, pero si esas compras no son deducibles por violar el límite de efectivo, usted no debería incluirlas en la base del 1%. La recomendación conservadora es: calcule el 1% solo sobre las compras que cumplen AMBOS requisitos — factura electrónica validada Y pago por medio bancarizado o dentro del límite de efectivo.

Implemente una política interna de no pagar más de $4.500.000 en efectivo por transacción (un tope conservador por debajo de los 100 UVT), y documente el medio de pago en cada registro contable.

---

## Pregunta 2 (M) — Renta: TTD — Tasa de Tributación Depurada

**Pregunta inicial:**
Necesito ayuda con la TTD para un cliente SAS de comercio con las siguientes cifras del AG 2025: utilidad contable antes de impuestos $360 millones, diferencias permanentes (gastos no deducibles) $45 millones, ingresos no constitutivos de renta $5 millones, sin rentas exentas ni compensación de pérdidas. (a) ¿Cómo calculo la TTD paso a paso? (b) ¿Qué pasa si el resultado queda por debajo del 15%? (c) ¿En qué renglón del Formulario 110 registro el Impuesto a Adicionar?

**Respuesta modelo:**
La TTD se rige por el Parágrafo 6 del Art. 240 ET (adicionado por la Ley 2277 de 2022). La fórmula es TTD = ID / UD, donde el piso es 15%.

**(a) Cálculo paso a paso con sus cifras:**

Primero, la Utilidad Depurada (UD):
UD = UC + DPARL – INCRNGO – VIMPP – VNGO – RE + C
UD = $360.000.000 + $45.000.000 – $5.000.000 – $0 – $0 – $0 + $0
UD = $400.000.000

Ahora el Impuesto Depurado (ID):
Con renta líquida gravable de aproximadamente $400M y tarifa del 35%, el impuesto sobre la renta sería $140.000.000. Si tiene descuentos tributarios (DT) de, digamos, $8.000.000 por IVA de activos fijos, entonces:
INR = $140.000.000 – $8.000.000 = $132.000.000
ID = INR + DT – IRP = $132.000.000 + $8.000.000 – $0 = $140.000.000

TTD = $140.000.000 / $400.000.000 = 35,0%

En este caso, 35% es superior al piso de 15%, así que no hay Impuesto a Adicionar (IA = $0).

**(b) Si la TTD queda por debajo del 15%:**
Se calcula el Impuesto a Adicionar (IA) = (UD × 15%) – ID. Ese monto se suma al impuesto neto de renta. Esto ocurre típicamente cuando el contribuyente tiene descuentos tributarios grandes o rentas exentas significativas que reducen el impuesto pero no la utilidad depurada.

**(c) Registro:** El IA se registra en el renglón 95 del Formulario 110. Si no hay IA, se coloca $0.

Importante: según el Concepto DIAN 006483 int. 218/2024 (Numeral 22), el IA se incluye dentro del "impuesto neto de renta" para efectos del cálculo del anticipo (Art. 807 ET) y del beneficio de auditoría (Art. 689-3 ET).

**Pregunta de seguimiento:**
¿Qué hago si mi cliente tiene una pérdida contable (utilidad contable negativa)? ¿La UD puede ser negativa y eso me exime del cálculo de TTD?

**Respuesta modelo (seguimiento):**
Este es uno de los puntos más polémicos de la TTD. Según el Concepto DIAN 100208192-202/2024 (Numeral 12), cuando la utilidad contable (UC) es negativa, la DIAN sostenía que la UD podía resultar negativa y en ese caso no se aplicaba el 15%. Sin embargo, el Consejo de Estado suspendió parcialmente este concepto, y posteriormente mediante Sentencia 28920 del 3 de julio de 2025, revocó la suspensión del numeral 12 — es decir, confirmó que el tratamiento de la DIAN para pérdidas contables es válido.

En la práctica: si el cliente tiene pérdida contable y la UD resulta negativa o cero, matemáticamente no se puede calcular una TTD (no se puede dividir por cero o un denominador negativo). En ese escenario no hay IA.

Lo que sí se mantuvo suspendido fue el numeral 20 del mismo concepto, que trataba sobre la inclusión del IA en el cálculo de dividendos — ese tema sigue en discusión.

Documente bien los papeles de trabajo y soporte con la sentencia del Consejo de Estado por si la DIAN cuestiona la ausencia de IA.

---

## Pregunta 3 (S) — Renta: Beneficio de auditoría

**Pregunta inicial:**
Un cliente PJ tuvo un impuesto neto de renta de $153.000.000 en AG 2024 y estima un impuesto neto de $214.000.000 para AG 2025 (incluyendo el IA de TTD). ¿Puede acogerse al beneficio de auditoría y cuánto tiempo de firmeza ganaría?

**Respuesta modelo:**
Sí puede, si cumple todos los requisitos del Art. 689-3 ET (adicionado por Art. 51, Ley 2155/2021, extendido por Art. 69, Ley 2294/2023).

Verifiquemos cada requisito:

1. **Incremento del INR:** ($214M – $153M) / $153M × 100 = 39,9%. Como 39,9% ≥ 35%, califica para firmeza a 6 meses (el mejor escenario).

2. **INR del año anterior ≥ 71 UVT:** Con UVT 2024 = $47.065, el umbral es 71 × $47.065 = $3.341.615. El INR de $153.000.000 supera ampliamente ese mínimo. Cumple.

3. **Presentación oportuna:** Para PJ no grandes contribuyentes, la ventana de presentación para AG 2025 es del 12 al 26 de mayo de 2026 (dependiendo del último dígito del NIT). Debe presentar dentro de ese plazo. Entre más temprano presente, antes arranca el conteo de los 6 meses.

4. **Pago completo y oportuno:** La primera cuota se paga con la declaración (mayo 2026) y la segunda cuota en julio 2026. Un solo día de atraso en el pago destruye el beneficio.

5. **No estar en zonas con beneficios geográficos:** El cliente NO debe estar en ZOMAC, zona franca ni ZESE. Si está en alguna de esas, el beneficio NO aplica (exclusión expresa del parágrafo del Art. 689-3).

Si cumple todo: la declaración adquiere firmeza 6 meses después de la fecha de presentación. Si presenta el 15 de mayo de 2026, la firmeza sería el 15 de noviembre de 2026 — comparado con los 3 años ordinarios del Art. 714 ET. Es una ventaja enorme.

**Pregunta de seguimiento:**
¿Y si el cliente tiene saldo a favor en esa declaración, el plazo para solicitar la devolución también se acorta?

**Respuesta modelo (seguimiento):**
Exacto. Según el Parágrafo 3 del Art. 689-3 ET, si la declaración acogida al beneficio de auditoría genera un saldo a favor, la solicitud de devolución o compensación debe presentarse dentro del mismo plazo de firmeza — es decir, dentro de los 6 meses (o 12 meses si el incremento fue ≥25% pero <35%).

Esto es crítico: normalmente el plazo para solicitar devolución es de 2 años (Art. 854 ET). Pero con beneficio de auditoría, ese plazo se reduce al período de firmeza. Si presenta el 15 de mayo de 2026 con firmeza a 6 meses, debe solicitar la devolución antes del 15 de noviembre de 2026 o pierde el derecho.

Adicionalmente, tenga en cuenta que el Oficio DIAN 100208192-608 del 22 de diciembre de 2021 aclara que si usted corrige la declaración del AG 2024 después de haberse acogido al beneficio en AG 2025, puede destruir la base de comparación y perder el beneficio. Mucho cuidado con correcciones del período anterior.

---

## Pregunta 4 (M) — Renta: Anticipo del impuesto

**Pregunta inicial:**
Tengo una SAS comercializadora en su tercer año declarando renta. En AG 2024 el INR (incluyendo IA) fue de $164.200.000 y en AG 2025 estimo un INR de $195.000.000. Las retenciones practicadas a favor del contribuyente en AG 2025 suman $42.000.000. (a) ¿Cómo calculo el anticipo por los dos procedimientos del Art. 807? (b) ¿Cuál le conviene más al cliente? (c) ¿Hay alguna forma de reducir el anticipo si el negocio va mal en 2026?

**Respuesta modelo:**

**(a) Los dos procedimientos (Art. 807 ET):**

**Procedimiento 1 — Basado en el INR del año actual:**
Base = $195.000.000
× 75% (tercer año en adelante) = $146.250.000
– Retenciones a favor AG 2025: $42.000.000
= Anticipo Procedimiento 1: $104.250.000

**Procedimiento 2 — Promedio de los dos últimos años:**
Promedio = ($195.000.000 + $164.200.000) / 2 = $179.600.000
× 75% = $134.700.000
– Retenciones a favor AG 2025: $42.000.000
= Anticipo Procedimiento 2: $92.700.000

**(b) El Procedimiento 2 es más favorable** — genera un anticipo $11.550.000 menor. El contribuyente tiene derecho a elegir el que más le convenga.

El pago se distribuye así (PJ no grandes contribuyentes):
- 1ª cuota con la declaración (mayo 2026): $46.350.000
- 2ª cuota (julio 2026): $46.350.000

**(c) Reducción del anticipo (Art. 809 ET):**
Si en los primeros 3 meses de 2026 los ingresos caen más de 15% respecto al mismo período de 2025, o en los primeros 6 meses caen más de 25%, el contribuyente puede solicitar una reducción proporcional del anticipo. Se presenta un memorial ante la DIAN con soporte documental (balances, reportes de ventas). La DIAN tiene 2 meses para responder; si guarda silencio, opera el silencio administrativo positivo (Art. 810 ET) y la reducción se entiende aprobada.

**Pregunta de seguimiento:**
Las autorretenciones especiales de renta (Decreto 2201/2016) que mi cliente practica mensualmente, ¿se descuentan del anticipo o del impuesto a cargo? ¿Cómo juegan en el cálculo?

**Respuesta modelo (seguimiento):**
Las autorretenciones especiales del Decreto 2201/2016 (ahora Art. 1.2.6.6 del DUR 1625/2016) son retenciones que la propia empresa se practica y declara mensualmente en el Formulario 350. Estas autorretenciones se suman al total de "retenciones a favor" en la declaración de renta (renglón del Formulario 110 para retenciones).

En el cálculo del anticipo, las autorretenciones SÍ hacen parte de las retenciones que se descuentan de la base. En el ejemplo: si los $42.000.000 de retenciones incluyen autorretenciones, ya están contabilizadas. Si no las incluyó, debe sumarlas a las retenciones de terceros y recalcular — eso reduce aún más el anticipo.

La tarifa de autorretención varía por actividad económica (CIIU), típicamente entre 0,4% y 1,6% sobre los ingresos. Aplica a todas las PJ del régimen ordinario que sean autorretenedoras. Verifique que el cliente esté declarando y pagando cumplidamente la autorretención mensual, porque los pagos extemporáneos generan intereses moratorios y la DIAN puede desconocer retenciones no declaradas oportunamente.

---

## Pregunta 5 (S) — Renta: Tarifas especiales

**Pregunta inicial:**
Un cliente tiene un hotel nuevo en un municipio de menos de 200.000 habitantes, con renta líquida gravable de $150 millones en AG 2025. ¿Qué tarifa de renta le aplica y cuánto se ahorra frente a la tarifa general?

**Respuesta modelo:**
Le aplica la tarifa preferencial del 15%, conforme al Parágrafo 5 del Art. 240 ET. Esta tarifa beneficia a hoteles nuevos o remodelados en municipios de hasta 200.000 habitantes.

El cálculo es directo:
- Impuesto con tarifa preferencial: $150.000.000 × 15% = $22.500.000
- Impuesto con tarifa general: $150.000.000 × 35% = $52.500.000
- Ahorro: $30.000.000 (un 57% menos de impuesto)

Para acceder al beneficio, el hotel debe cumplir los requisitos de inversión y generación de empleo del decreto reglamentario, y el municipio debe tener población certificada por DANE inferior a 200.000 habitantes. Verifique el RUT del contribuyente para confirmar la responsabilidad tributaria correcta.

Ojo: si el hotel tiene ingresos por actividades no hoteleras (por ejemplo, alquiler de salones de eventos como actividad principal separada), esos ingresos podrían quedar gravados a tarifa general del 35%.

**Pregunta de seguimiento:**
¿Y si ese mismo hotel está ubicado en un municipio ZOMAC, puede acumular el beneficio ZOMAC con la tarifa del Parágrafo 5?

**Respuesta modelo (seguimiento):**
No. Los beneficios de tarifa son excluyentes — no se acumulan. Si el hotel está en una ZOMAC, debe elegir el régimen que más le convenga. Las tarifas ZOMAC para AG 2025 según la Ley 1819/2016 (Art. 237) son:
- Micro y pequeña empresa: 17,5% (duplicada desde 8,75% a partir de AG 2025)
- Mediana empresa: 26,25%

En este caso, si el hotel califica como micro o pequeña empresa, la tarifa ZOMAC (17,5%) es MAYOR que la tarifa del Parágrafo 5 (15%). Así que le conviene más la tarifa hotelera del 15%.

Pero ojo: si el hotel es mediana empresa (tarifa ZOMAC 26,25%), obviamente también le conviene el Parágrafo 5 (15%).

Hay una trampa adicional: las empresas ZOMAC están excluidas del beneficio de auditoría del Art. 689-3 ET. Entonces, si el cliente se va por la tarifa ZOMAC, pierde acceso al beneficio de auditoría. Si se va por el Parágrafo 5, puede eventualmente acogerse al beneficio de auditoría (si cumple los demás requisitos). Evalúe el costo-beneficio integral.

---

## Pregunta 6 (M) — IVA: Periodicidad y prorrateo

**Pregunta inicial:**
Tengo una SAS distribuidora de alimentos que vende productos gravados al 19% y también comercializa productos de la canasta familiar (excluidos de IVA). Los ingresos brutos del AG 2024 fueron $4.200 millones. (a) ¿Cuál es la periodicidad de declaración de IVA para 2026? (b) ¿Cómo calculo el prorrateo del IVA descontable en los gastos comunes?

**Respuesta modelo:**

**(a) Periodicidad:**
La periodicidad se determina por los ingresos brutos del año gravable anterior (AG 2024). El umbral es 92.000 UVT. Con UVT 2025 = $49.799, eso equivale a 92.000 × $49.799 = $4.581.508.000.

Los ingresos de $4.200.000.000 son inferiores a $4.581.508.000, entonces la declaración es **cuatrimestral** (3 declaraciones al año: enero-abril, mayo-agosto, septiembre-diciembre). Se usa el Formulario 300.

Si los ingresos hubieran sido ≥ $4.581.508.000, la periodicidad sería **bimestral** (6 declaraciones al año).

**(b) Prorrateo del IVA descontable:**
Cuando un contribuyente realiza operaciones gravadas y excluidas, los gastos comunes (arriendo, servicios públicos, insumos compartidos, etc.) generan un IVA que solo es descontable proporcionalmente a las operaciones gravadas y exentas.

La fórmula del prorrateo es:
% descontable = (Ingresos gravados + Ingresos exentos) / Ingresos totales × 100

Ejemplo: si en el bimestre los ingresos gravados son $800.000.000, los exentos $0, y los excluidos $200.000.000:
% descontable = $800M / ($800M + $200M) × 100 = 80%

Si el IVA pagado en gastos comunes del período es $15.000.000, solo puede descontar $15M × 80% = $12.000.000. Los $3.000.000 restantes son mayor valor del gasto (no descontable).

Note que los ingresos excluidos NO entran en el numerador — solo en el denominador.

**Pregunta de seguimiento:**
¿Y si en un cuatrimestre me queda un saldo a favor de IVA, qué opciones tengo para manejarlo?

**Respuesta modelo (seguimiento):**
Tiene tres opciones según el ET:

1. **Imputación al período siguiente** (la más simple): arrastra el saldo a favor como descontable en la siguiente declaración de IVA. No requiere trámite adicional ante la DIAN.

2. **Compensación contra otros impuestos** (Art. 815 ET): puede solicitar que el saldo a favor se aplique contra deudas de otros impuestos nacionales (retención en la fuente, renta, etc.). Requiere presentar solicitud formal ante la DIAN.

3. **Devolución en efectivo**: solicita la devolución del saldo. Requiere firma de contador público o revisor fiscal (según el caso), y puede requerir garantía bancaria dependiendo del monto. La DIAN tiene 50 días para resolver (o 30 días si presenta garantía bancaria, conforme a la Ley 2277/2022).

El plazo para solicitar la devolución o compensación es de 2 años contados desde la fecha de vencimiento del plazo para declarar, según el Art. 854 ET.

Para PYMEs, la opción más frecuente es la imputación, por simplicidad. Pero si el saldo a favor es recurrente y significativo, evalúe la devolución para mejorar el flujo de caja.

---

## Pregunta 7 (S) — IVA: ReteIVA a grandes contribuyentes

**Pregunta inicial:**
Mi cliente PYME le vendió mercancía gravada a un gran contribuyente por $10.000.000 más IVA. ¿Cómo funciona la retención de IVA en esa operación y cuánto recibe efectivamente mi cliente?

**Respuesta modelo:**
Cuando un responsable de IVA vende a un gran contribuyente designado por la DIAN, el comprador (gran contribuyente) debe practicar retención de IVA (ReteIVA) del 15% sobre el IVA generado.

El cálculo para la venta de $10.000.000 + IVA 19%:
- IVA generado: $10.000.000 × 19% = $1.900.000
- ReteIVA (15% del IVA): $1.900.000 × 15% = $285.000
- Total facturado: $10.000.000 + $1.900.000 = $11.900.000
- Descuento por ReteIVA: –$285.000
- **Monto que recibe su cliente: $11.615.000**

La ReteIVA de $285.000 se convierte en un anticipo del IVA para su cliente. Cuando su cliente prepare su declaración de IVA (Formulario 300), puede descontar esos $285.000 del IVA a pagar del período.

Su cliente debe exigir al gran contribuyente el certificado de retención de IVA como soporte. Sin ese certificado, no puede descontar la retención.

**Pregunta de seguimiento:**
¿Hay una base mínima para que operen la ReteIVA? Es decir, ¿en compras pequeñas también me retienen?

**Respuesta modelo (seguimiento):**
Sí, existe una base mínima. La retención de IVA del 15% opera sobre servicios a partir de 4 UVT ($209.496 para 2026) y sobre compras de bienes a partir de 27 UVT ($1.414.098 para 2026). Si la transacción no alcanza esa base, no se practica ReteIVA.

En el caso de su ejemplo ($10M), supera ampliamente la base mínima, así que la retención opera. Pero si su cliente hace ventas menores a $1.414.098, el gran contribuyente no debería retener IVA.

Recuerde que las bases y tarifas de retención de IVA están consolidadas en la tabla de retención en la fuente que se actualiza con cada UVT. Mantenga la tabla actualizada con el UVT 2026 ($52.374).

---

## Pregunta 8 (M) — Retención en la fuente: Tabla salarial 2026

**Pregunta inicial:**
Tengo que calcular la retención en la fuente por salarios para tres empleados con estos sueldos mensuales en 2026: (a) $3.000.000, (b) $12.000.000, y (c) $20.000.000. Todos tienen las deducciones obligatorias estándar (4% pensión, 4% salud). ¿Cuánto les retengo a cada uno?

**Respuesta modelo:**
La retención salarial se calcula con la tabla del Art. 383 ET, usando UVT 2026 = $52.374. Veamos cada caso considerando las deducciones obligatorias y la renta exenta del 25% (Art. 206 numeral 10 ET, con el tope del 40% del Art. 336 ET):

**(a) Salario $3.000.000:**
- Deducciones obligatorias: pensión 4% ($120.000) + salud 4% ($120.000) = $240.000
- Subtotal: $3.000.000 – $240.000 = $2.760.000
- Renta exenta 25%: $2.760.000 × 25% = $690.000
- Base gravable: $2.070.000
- En UVT: $2.070.000 / $52.374 = 39,5 UVT
- Este valor está por debajo de los 95 UVT donde empieza la tabla progresiva.
- **Retención: $0**

**(b) Salario $12.000.000:**
- Deducciones obligatorias: $480.000 + $480.000 = $960.000
- Subtotal: $11.040.000
- Renta exenta 25%: $2.760.000
- Base gravable: $8.280.000
- En UVT: 158,1 UVT
- Aplicando la tabla progresiva del Art. 383 ET, con las tarifas marginales de 0% a 28%:
- **Retención aproximada: $666.267/mes**

**(c) Salario $20.000.000:**
- Deducciones obligatorias: $800.000 + $800.000 = $1.600.000
- Subtotal: $18.400.000
- Renta exenta 25%: $4.600.000
- Base gravable: $13.800.000
- En UVT: 263,5 UVT
- Aplicando la tabla progresiva con tarifas marginales hasta 33%:
- **Retención aproximada: $2.170.518/mes**

**Pregunta de seguimiento:**
Si uno de esos empleados tiene un crédito hipotecario y aportes voluntarios a pensión, ¿cómo afecta eso la base de retención?

**Respuesta modelo (seguimiento):**
Ambos conceptos reducen la base de retención, dentro de los límites legales:

**Intereses de crédito hipotecario:** Son deducibles hasta 100 UVT mensuales ($5.237.400 para 2026), conforme al Art. 387 ET. El empleado debe certificar los pagos con soporte del banco. Se restan de los ingresos antes de calcular la renta exenta.

**Aportes voluntarios a pensión (AFC o fondo de pensión voluntaria):** Son renta exenta hasta el 30% del ingreso laboral, con tope mensual. Sin embargo, recuerde que existe el tope global del 40% del Art. 336 ET: la sumatoria de todas las rentas exentas y deducciones del empleado no puede exceder el 40% de los ingresos netos (después de INCRNGO).

En la práctica: para el empleado de $12M, si tiene intereses hipotecarios de $1.500.000/mes y aportes voluntarios de $2.000.000/mes, su base gravable bajaría significativamente y la retención podría reducirse a la mitad o menos. Pero debe verificar que no supere el tope del 40%.

El empleado debe entregar el certificado de deducción al inicio del año (o cuando cambie) usando el formato de la empresa. Usted como agente retenedor es responsable de aplicar correctamente las deducciones, y la DIAN puede sancionarlo si aplica deducciones sin soporte (Art. 658-1 ET).

---

## Pregunta 9 (S) — Retención en la fuente: Honorarios y servicios

**Pregunta inicial:**
Voy a contratar a un consultor independiente (persona natural declarante de renta) por honorarios de $8.000.000 mensuales. ¿Cuánto debo retenerle en la fuente por concepto de honorarios?

**Respuesta modelo:**
Para honorarios a personas naturales declarantes de renta, la tarifa de retención en la fuente es del 10% si el beneficiario del pago suscribió el contrato por un monto total superior a 3.300 UVT en el año. Si el beneficiario es declarante y el pago individual supera 27 UVT ($1.414.098 para 2026), se aplica retención.

El cálculo: $8.000.000 × 10% = $800.000 de retención en la fuente.

El monto neto que recibe el consultor: $8.000.000 – $800.000 = $7.200.000.

Adicionalmente, si el consultor es responsable de IVA (régimen común), debe facturar IVA del 19% sobre los honorarios. En ese caso:
- Honorarios: $8.000.000
- IVA 19%: $1.520.000
- Total facturado: $9.520.000
- Retención en la fuente (10% sobre honorarios): –$800.000
- ReteIVA (15% sobre IVA, si usted es agente retenedor de IVA): –$228.000
- ReteICA (según tarifa municipal): varía por municipio
- Neto a pagar: $8.492.000 (sin ICA)

No olvide: el consultor debe emitir factura electrónica si está obligado, o usted debe generar el documento soporte de pago si el consultor no está obligado a facturar.

**Pregunta de seguimiento:**
¿Y si el consultor me dice que no es declarante de renta, cambia la tarifa de retención?

**Respuesta modelo (seguimiento):**
Sí cambia. Para personas naturales NO declarantes de renta, la tarifa de retención por honorarios es del 10% igualmente en la mayoría de los casos, pero hay matices según el monto del contrato.

Lo importante en la práctica es que usted como agente retenedor debe verificar si el consultor es declarante o no, y documentar esa verificación. La forma más segura es solicitarle al consultor su RUT actualizado, donde aparece la responsabilidad "05 - Impuesto de Renta" si es declarante.

Si el consultor no es declarante y los honorarios no superan 3.300 UVT en el año, la retención se aplica con las tablas del Art. 383 ET (la misma que para asalariados), lo que puede resultar en una retención mayor o menor dependiendo de las deducciones que acredite. Si no presenta certificado de deducciones, se retiene al 10% directo.

La recomendación práctica: siempre retenga el 10% sobre honorarios y documente el RUT del contratista. Es la posición más segura.

---

## Pregunta 10 (M) — Facturación electrónica: Habilitación y operación

**Pregunta inicial:**
Un cliente nuevo acaba de constituir una SAS y necesita habilitarse para facturar electrónicamente. (a) ¿Qué opciones tiene para habilitarse? (b) ¿Cuántas resoluciones necesita tener activas? (c) ¿Qué hago si el sistema se cae y no puedo transmitir facturas a la DIAN?

**Respuesta modelo:**

**(a) Opciones de habilitación (3 caminos):**

1. **Proveedor tecnológico** (recomendado para PYMEs): Contratar un proveedor de facturación electrónica autorizado por la DIAN. Costo típico: $40.000–$300.000/mes dependiendo del volumen. El proveedor se encarga de la generación del XML, la firma digital (CUFE), y la transmisión a la DIAN. Es la opción de menor fricción técnica.

2. **Facturador directo**: La empresa desarrolla su propio software de facturación que se conecta directamente al web service de la DIAN. Requiere equipo de desarrollo y certificación. Solo recomendable para empresas con volúmenes altos y capacidad técnica interna.

3. **Sistema gratuito de la DIAN**: La DIAN ofrece un portal gratuito para emitir facturas electrónicas. Solo viable para menos de 50 facturas/mes. Limitaciones significativas en automatización y reportes.

**(b) Resoluciones necesarias (3):**
- Resolución de numeración de facturación (obligatoria para emitir facturas)
- Resolución de facturación de contingencia (para operar cuando falla el sistema principal)
- Resolución de documento soporte (para compras a proveedores no obligados a facturar)

Todas se tramitan en el portal MUISCA de la DIAN.

**(c) Protocolo de contingencia:**
Si el sistema falla, tiene una ventana de 48 horas para transmitir las facturas a la DIAN. Durante la contingencia:
- Emita facturas con la numeración de contingencia (resolución separada)
- Registre cada factura en un libro de contingencia con fecha, hora, valor, cliente y número de factura
- Una vez restablecido el sistema, transmita todas las facturas pendientes dentro de las 48 horas
- Si no transmite en 48 horas, las facturas pierden validez tributaria

**Pregunta de seguimiento:**
¿Y el documento soporte cómo funciona? Compro mercancía a un agricultor que no está obligado a facturar. ¿Qué debo hacer?

**Respuesta modelo (seguimiento):**
El documento soporte en adquisiciones efectuadas a sujetos no obligados a facturar (Resolución DIAN 000167 de 2021) es un documento electrónico que USTED como comprador debe generar cuando adquiere bienes o servicios de personas no obligadas a expedir factura — típicamente agricultores, personas naturales del régimen simplificado, trabajadoras domésticas, etc.

Para su compra al agricultor:
1. Genere el documento soporte electrónico a través de su proveedor tecnológico o del portal DIAN
2. Incluya: NIT/cédula del agricultor, descripción del bien, cantidad, valor, fecha
3. Si la compra es gravada con IVA, usted asume el IVA (mecanismo de asunción del impuesto)
4. Transmita el documento a la DIAN para validación — funciona igual que una factura electrónica
5. El documento soporte validado le da derecho a tomar el costo o gasto como deducible y a descontar el IVA asumido

Sin documento soporte, la compra no es deducible en renta ni da derecho a IVA descontable. Es uno de los errores más frecuentes en PYMEs rurales.

---

## Pregunta 11 (S) — Facturación electrónica: Notas crédito

**Pregunta inicial:**
Un cliente me devolvió mercancía por un defecto de calidad. Ya le había emitido factura electrónica por $5.000.000 + IVA. ¿Cómo manejo la nota crédito electrónica?

**Respuesta modelo:**
Debe emitir una nota crédito electrónica referenciando la factura original. La referencia se hace mediante el CUFE (Código Único de Facturación Electrónica) de la factura original — esto es obligatorio para que la DIAN pueda trazar la operación.

Hay que distinguir dos escenarios:

1. **Devolución parcial**: Si la devolución es solo por parte de la mercancía, la nota crédito debe especificar únicamente los ítems devueltos con sus cantidades y valores. El IVA se ajusta proporcionalmente.

2. **Anulación total por error en datos**: Si la factura tiene errores en datos (NIT del cliente, dirección, descripción del bien), la nota crédito anula el 100% de la factura original y se reemite una factura nueva con los datos correctos.

Para su caso (devolución por defecto de calidad):
- Nota crédito por $5.000.000 + IVA ($950.000) = $5.950.000
- Referencia obligatoria: CUFE de la factura original
- Transmisión a la DIAN para validación (mismo proceso que la factura)
- Efecto contable: reversa el ingreso y el IVA generado
- En la declaración de IVA: reduce el IVA generado del período en $950.000

La nota crédito debe emitirse dentro del mismo período gravable si es posible, para evitar ajustes entre períodos.

**Pregunta de seguimiento:**
¿Y si descubrí el error un mes después de cerrar el período de IVA? ¿Puedo emitir la nota crédito en el período siguiente?

**Respuesta modelo (seguimiento):**
Sí puede emitir la nota crédito en un período posterior. El ajuste al IVA generado se refleja en la declaración de IVA del período en que se emite la nota crédito, no en el período original.

Sin embargo, si el ajuste es significativo y afecta la declaración ya presentada del período anterior, evalúe si conviene corregir esa declaración (Art. 588 ET — corrección voluntaria dentro de los 2 años siguientes al vencimiento). La corrección voluntaria no genera sanción si resulta en un mayor saldo a favor o menor impuesto — pero si resulta en menor saldo a favor, puede generar sanción por corrección del Art. 644 ET (10% de la diferencia si corrige voluntariamente, 20% si la corrección es provocada por la DIAN).

La recomendación práctica es: si la nota crédito se emite en el período siguiente, simplemente inclúyala en la declaración de IVA de ese período. Solo corrija la declaración anterior si el impacto es material y si desea reclamar el saldo a favor generado.

---

## Pregunta 12 (M) — RST: Elegibilidad y comparación

**Pregunta inicial:**
Tengo un cliente SAS de servicios profesionales (consultoría) con 3 socios personas naturales residentes, ingresos brutos de $600 millones en AG 2025, y todos los clientes son diversos (ninguno concentra más del 30% de los ingresos). (a) ¿Puede inscribirse en el RST? (b) ¿Qué tarifa consolidada le aplicaría? (c) ¿Le conviene más que el régimen ordinario?

**Respuesta modelo:**

**(a) Elegibilidad — Las 5 puertas del Art. 905 ET:**

1. ¿Es PJ con todos los socios personas naturales residentes? → SÍ (3 socios PN residentes). Cumple.
2. ¿Ingresos brutos del año anterior < 100.000 UVT? → 100.000 × $52.374 = $5.237.400.000. Sus $600M están muy por debajo. Cumple.
3. ¿Ingresos consolidados con participaciones >10% en otras entidades < 100.000 UVT? → Debe verificar. Si los socios no tienen participaciones significativas en otras empresas, cumple.
4. ¿No está excluido por Art. 906 ET? → Los servicios de consultoría NO están en la lista de exclusiones (que incluye microcrédito, energía, vehículos, IFIs, reciclaje). Cumple.
5. ¿Ingresos no concentrados >80% en un solo cliente en relación de dependencia fija? → Ningún cliente supera 30%. Cumple.

**Resultado: SÍ es elegible para RST.**

Plazo de inscripción: hasta el 27 de febrero de 2026 (inflexible).

**(b) Tarifa consolidada:**
Servicios profesionales caen en el Grupo 3 del Art. 908 ET. Con ingresos brutos de $600.000.000:
- Rango: ≥ $298.794.000 (6.000 UVT) hasta < $746.985.000 (15.000 UVT)
- **Tarifa: 7,3%**
- Impuesto consolidado RST: $600.000.000 × 7,3% = $43.800.000

**(c) Comparación con régimen ordinario:**
En régimen ordinario, asumiendo costos y deducciones del 40% ($240M):
- Renta líquida gravable: $360.000.000
- Impuesto de renta al 35%: $126.000.000
- Más: anticipo, autorretención, ICA, etc.

En RST: $43.800.000 y ese impuesto ya incluye renta + ICA + aportes a pensión de los socios. El RST es significativamente más económico para servicios profesionales con márgenes altos de rentabilidad.

Sin embargo, en RST no se permiten deducciones ni descuentos tributarios (salvo retenciones y anticipos). La tarifa se aplica sobre ingresos brutos, no sobre renta líquida.

**Pregunta de seguimiento:**
¿Qué pasa si uno de los socios tiene participación del 15% en otra SAS que no está en RST? ¿Eso afecta la elegibilidad?

**Respuesta modelo (seguimiento):**
Sí afecta. El Art. 905 ET (numeral 4, adicionado por Ley 2277/2022) establece que si algún socio tiene participación superior al 10% en otra entidad, los ingresos de esa otra entidad se suman a los ingresos de la SAS para verificar el tope de 100.000 UVT.

Si su socio tiene 15% en otra SAS con ingresos de $4.800.000.000, se suman:
$600.000.000 + $4.800.000.000 = $5.400.000.000

$5.400M > $5.237.400.000 (100.000 UVT) → **Supera el tope consolidado → NO es elegible para RST.**

Solución práctica: el socio tendría que reducir su participación en la otra SAS a 10% o menos antes de la inscripción. O la otra SAS tendría que tener ingresos menores para que el consolidado quede por debajo de los 100.000 UVT.

Este es un punto que muchos contadores pasan por alto. Haga la verificación de participaciones cruzadas ANTES de inscribir al cliente.

---

## Pregunta 13 (S) — RST: Mecánica de anticipos bimestrales

**Pregunta inicial:**
Mi cliente ya está inscrito en el RST (Grupo 2 — actividad comercial mayorista). ¿Cómo funcionan los anticipos bimestrales y con qué formulario los declara?

**Respuesta modelo:**
Los contribuyentes del RST deben presentar 6 declaraciones de anticipo bimestral durante el año usando el Recibo Electrónico de Pago 2593, y al cierre del año presentan la declaración anual consolidada en el Formulario 260.

Los bimestres son:
1. Enero–Febrero (declara en marzo)
2. Marzo–Abril (declara en mayo)
3. Mayo–Junio (declara en julio)
4. Julio–Agosto (declara en septiembre)
5. Septiembre–Octubre (declara en noviembre)
6. Noviembre–Diciembre (declara en enero del año siguiente)

El cálculo de cada anticipo bimestral:
- Totalice los ingresos brutos del bimestre
- Convierta a UVT: ingresos / $52.374
- Ubique en la tabla del Grupo 2 (Art. 908 ET) el rango correspondiente
- Aplique la tarifa correspondiente

Para el Grupo 2 (comercio mayorista, técnico, construcción, manufactura), las tarifas son:
- 0 a 6.000 UVT ($0–$314.244.000): 1,8%
- 6.000 a 15.000 UVT ($314M–$785.610.000): 2,2%
- 15.000 a 30.000 UVT ($785M–$1.571.220.000): 3,9%
- 30.000 a 100.000 UVT ($1.571M–$5.237.400.000): 5,4%

Al cierre del año, en el Formulario 260 se consolidan todos los ingresos anuales, se aplica la tarifa correspondiente al total anual, y se descuentan los 6 anticipos pagados. Si pagó de más, genera saldo a favor; si pagó de menos, paga la diferencia.

Las retenciones que le hayan practicado durante el año también se descuentan en la declaración anual.

**Pregunta de seguimiento:**
¿Y qué pasa si mi cliente quiere retirarse del RST a mitad de año porque le va mal? ¿Puede?

**Respuesta modelo (seguimiento):**
No a mitad de año. El retiro del RST opera a partir del año gravable siguiente. El plazo para notificar el retiro es hasta el 31 de enero del año en que desea salir. Es decir, si quiere salir del RST para el AG 2027, debe notificarlo a más tardar el 31 de enero de 2027.

Si el cliente permanece en el RST todo el AG 2026 y le va mal (ingresos muy bajos o incluso pérdidas), de todas formas debe cumplir con los 6 anticipos bimestrales y la declaración anual. Si los ingresos del bimestre son $0, el anticipo es $0 pero la declaración se debe presentar.

Hay un retiro automático si los ingresos brutos del año superan los 100.000 UVT — en ese caso, el contribuyente queda excluido para el año siguiente y debe volver al régimen ordinario.

La recomendación para clientes que están dudando: haga la proyección financiera completa antes de la fecha límite de inscripción (27 de febrero) o de retiro (31 de enero). Una vez dentro, queda comprometido por todo el año gravable.

---

## Pregunta 14 (M) — Nómina: Liquidación mensual y parafiscales

**Pregunta inicial:**
Tengo una PYME manufacturera con 8 empleados, todos con salarios inferiores a 10 SMLMV. (a) ¿Qué aportes parafiscales debo pagar y cuáles están exonerados? (b) ¿Cuáles son los plazos de pago de la PILA según el NIT?

**Respuesta modelo:**

**(a) Aportes parafiscales y exoneración del Art. 114-1 ET:**

Para empleadores persona jurídica (o persona natural con 2 o más empleados) cuyos trabajadores devenguen menos de 10 SMLMV ($17.509.050 para 2026), están **exonerados** de:
- SENA: 2% → $0
- ICBF: 3% → $0
- Salud (aporte empleador): 8,5% → $0

Aportes que SÍ debe pagar:
- Pensión (empleador): 12% del IBC
- Pensión (empleado, deducido de nómina): 4% del IBC
- ARL: varía según nivel de riesgo (0,522% a 6,96%)
- Caja de Compensación Familiar: 4% del IBC (esta NO está exonerada)

Para una PYME con 8 empleados al SMLMV ($1.750.905):
- IBC mensual por empleado: $1.750.905
- Pensión empleador (12%): $210.109
- ARL (supongamos riesgo II, 1,044%): $18.279
- Caja de Compensación (4%): $70.036
- **Costo patronal mensual por empleado (sin salario):** $298.424
- **Para 8 empleados:** $2.387.392/mes en aportes patronales

Adicionalmente, debe provisionar mensualmente:
- Prima de servicios: 8,33% del salario
- Cesantías: 8,33% del salario
- Intereses sobre cesantías: ~1% del salario
- Vacaciones: 4,17% del salario

**(b) Plazos PILA:**
Los plazos de pago se determinan por los dos últimos dígitos del NIT o cédula del empleador. El pago es mensual, durante los primeros 15 días hábiles del mes siguiente al causado.

Ejemplo: NIT terminado en 00-07 paga en los días hábiles 1-2; terminado en 08-14 en los días 3-4; y así sucesivamente hasta terminado en 93-99 en los días 14-15.

**Pregunta de seguimiento:**
Uno de los empleados trabaja horas extra dominicales. ¿Cómo calculo el recargo y eso afecta el IBC para los aportes?

**Respuesta modelo (seguimiento):**
Los recargos se calculan sobre el valor de la hora ordinaria (salario mensual / 240 horas):

Para un empleado al SMLMV ($1.750.905):
- Hora ordinaria: $1.750.905 / 240 = $7.295,4

Tabla de recargos vigente 2026:
- Hora extra diurna (HED): ×1,25 = $9.119,3
- Hora extra nocturna (HEN): ×1,75 = $12.766,9
- Recargo nocturno (sin extra): +35% = $9.848,8
- Recargo dominical/festivo: +100% = $14.590,8 (ojo: a partir del 1 julio 2026, Ley 2466, el recargo dominical baja de 100% a 90%)
- Hora extra dominical diurna: ×2,00 = $14.590,8 (→ ×1,90 desde julio 2026)
- Hora extra dominical nocturna: ×2,50 = $18.238,5

Sobre el IBC: sí, las horas extra y los recargos nocturnos/dominicales HACEN PARTE del IBC para aportes a seguridad social. Debe sumarlos al salario base del mes para calcular los aportes de pensión, salud, ARL y parafiscales.

Importante: con la Ley 2466 (reforma laboral), a partir del 11 de julio de 2025 la jornada nocturna empieza a las 7:00 p.m. (antes era a las 9:00 p.m.). Esto implica que las horas entre 7 p.m. y 9 p.m. que antes eran diurnas ahora generan recargo nocturno del 35%. Recalcule los costos laborales.

---

## Pregunta 15 (S) — Reforma laboral: Cambios clave para PYMEs

**Pregunta inicial:**
Acabo de escuchar que la Ley 2466 trae cambios importantes en materia laboral. ¿Cuáles son los cambios más críticos que debo implementar en las PYMEs que asesoro y qué fechas límite tengo?

**Respuesta modelo:**
La Ley 2466 de 2025 (reforma laboral) tiene 5 cambios clave que afectan directamente a las PYMEs:

1. **Reducción de jornada laboral**: La jornada máxima legal pasa de 44 horas semanales a 42 horas, efectivo a partir del 15 de julio de 2026. Debe ajustar contratos y recalcular el valor de la hora ordinaria (sube porque el salario mensual se mantiene pero con menos horas). Esto incrementa el costo de horas extra.

2. **Jornada nocturna desde las 7:00 p.m.**: Vigente desde el 11 de julio de 2025 (ya está en efecto). El recargo nocturno del 35% ahora aplica desde las 7 p.m., no desde las 9 p.m. como antes. Impacto directo en restaurantes, comercio con horario extendido, vigilancia y manufactura con turnos nocturnos.

3. **Indemnización por despido sin justa causa**: Aumenta de 30 días a 45 días de salario para el primer año de servicios. Esto encarece significativamente la terminación de contratos — calcule +$1.100.000 adicionales por cada trabajador al SMLMV que despida.

4. **Formalización de trabajadores domésticos**: Los contratos con empleadas domésticas deben ser escritos obligatoriamente (antes bastaba el verbal). Incluya cláusulas de jornada, salario, prestaciones y seguridad social.

5. **Estabilidad laboral reforzada**: Se amplían las protecciones contra despido para trabajadores en situaciones especiales (maternidad, pre-pensionados, discapacidad, fuero de salud). Las PYME deben documentar cuidadosamente las causas de terminación.

**Pregunta de seguimiento:**
Con la reducción de jornada a 42 horas semanales desde julio 2026, ¿debo aumentar el salario de mis trabajadores que ganan más del mínimo?

**Respuesta modelo (seguimiento):**
No necesariamente debe aumentar el salario — lo que cambia es el valor de la hora. El salario mensual pactado se mantiene igual, pero como las horas semanales se reducen de 44 a 42, cada hora ordinaria vale más. Esto tiene dos implicaciones prácticas:

1. **Horas extra más costosas**: La hora ordinaria sube (salario mensual / 224 horas en vez de / 230.67 horas), y como las extras se calculan sobre la hora ordinaria con recargos, el costo de cada hora extra aumenta.

2. **Recálculo de nómina**: Si un trabajador trabaja las mismas horas que antes (44h/semana), las 2 horas adicionales ahora son horas extra diurnas (×1,25) que antes eran ordinarias. Debe ajustar el software de nómina.

Para una PYME tipo restaurante, el impacto estimado es un incremento de aproximadamente 2,1% en el costo total de nómina, considerando el efecto combinado de la jornada reducida y el recargo nocturno desde las 7 p.m.

La recomendación: prepare las adendas a los contratos de trabajo antes del 15 de julio de 2026, actualice la parametrización del software de nómina, y haga una simulación de costos con los nuevos parámetros para presentar al gerente/dueño de la PYME.

---

## Pregunta 16 (M) — Trabajo tiempo parcial: Cotización y costos

**Pregunta inicial:**
Un cliente quiere contratar una recepcionista por medio tiempo (4 horas diarias, 5 días a la semana). (a) ¿Cómo se calcula el salario y las prestaciones? (b) ¿Qué opciones tengo para la cotización a seguridad social? (c) ¿Cuánto le cuesta al empleador en total?

**Respuesta modelo:**

**(a) Salario y prestaciones:**
Para una jornada de 20 horas semanales (4h × 5 días), el salario se paga proporcional:
- Salario mensual: $1.750.905 × (20/42) = aproximadamente $833.764 (basado en la nueva jornada de 42h semanales desde julio 2026; antes del 15 de julio 2026 sería / 44)
- Las prestaciones (prima, cesantías, vacaciones) se liquidan sobre el mismo salario proporcional

Ejemplo con jornada de 20h semanales:
- Salario mensual: ~$1.082.526 (usando las proporciones del corpus)
- Prima de servicios: 8,33% = ~$90.174
- Cesantías: 8,33% = ~$90.174
- Intereses sobre cesantías: 1% = ~$10.825
- Vacaciones: 4,17% = ~$45.141

**(b) Opciones de cotización a seguridad social (3 caminos):**

1. **Ley 2466 Art. 34** (nueva): Permite cotizar sobre el tiempo efectivamente trabajado. Para 20h semanales, el IBC sería proporcional al SMLMV. Es la opción más económica.

2. **Decreto 2616 de 2013**: Para trabajadores con jornada inferior a la máxima legal, permite cotizar por semanas (1 a 3 semanas/mes). Se usa el Tipo Cotizante 51 en la PILA.

3. **Regla general**: Cotizar sobre un IBC de al menos 1 SMLMV, independientemente de las horas trabajadas. Es la opción más costosa para el empleador pero da mayor cobertura al trabajador.

**(c) Costo total para el empleador:**
Usando la opción de Ley 2466 (proporcional):
- Salario: ~$1.082.526
- Aportes patronales (pensión 12%, ARL, CCF 4%): ~$363.627
- **Costo total mensual estimado: ~$1.446.153**

Versus la regla general (IBC = 1 SMLMV):
- Costo significativamente mayor porque los aportes se calculan sobre SMLMV completo

El ahorro anual usando Ley 2466 vs. regla general puede ser de aproximadamente $1.740.000 por trabajador.

**Pregunta de seguimiento:**
¿La UGPP me puede cuestionar si contrato a alguien como medio tiempo pero en la práctica trabaja jornada completa?

**Respuesta modelo (seguimiento):**
Absolutamente. La UGPP (Unidad de Gestión Pensional y Parafiscales) aplica el principio de primacía de la realidad (Art. 53 de la Constitución). Si en la práctica la recepcionista trabaja 8 horas diarias pero usted la tiene registrada como medio tiempo y cotiza proporcionalmente, la UGPP puede:

1. Reliquidar los aportes sobre el IBC de jornada completa
2. Cobrar diferencias con intereses moratorios
3. Imponer sanciones por evasión de aportes

La UGPP cruza información con la DIAN (nómina electrónica, pagos reportados en exógena) y con los horarios reportados en la PILA. Si detecta inconsistencias entre las horas declaradas y los pagos reales, puede iniciar fiscalización.

Para protegerse:
- Documente el horario de trabajo en el contrato con detalle (hora de entrada, hora de salida, días de la semana)
- Registre el ingreso y salida del trabajador (biométrico, reloj, libro)
- No le asigne funciones que impliquen presencia fuera del horario contratado
- Si cambian las necesidades y la persona empieza a trabajar más, formalice el cambio con un otrosí al contrato y ajuste el IBC inmediatamente

---

## Pregunta 17 (S) — Pensiones: Fondo de Solidaridad Pensional

**Pregunta inicial:**
¿A partir de qué ingreso debe un empleado aportar al Fondo de Solidaridad Pensional y cuánto le corresponde?

**Respuesta modelo:**
El aporte al Fondo de Solidaridad Pensional (FSP) es obligatorio para empleados con un IBC superior a 4 SMLMV. Con SMLMV 2026 = $1.750.905, el umbral es 4 × $1.750.905 = $7.003.620.

Todo empleado que gane más de $7.003.620 mensuales debe aportar un porcentaje adicional al fondo, que se descuenta de su nómina:

Las tarifas son progresivas según el IBC:
- 4 a 16 SMLMV: 1% adicional
- 16 a 17 SMLMV: 1,2%
- 17 a 18 SMLMV: 1,4%
- 18 a 19 SMLMV: 1,6%
- 19 a 20 SMLMV: 1,8%
- Más de 20 SMLMV: 2%

Este aporte es 100% a cargo del empleado — el empleador solo lo retiene y lo paga en la PILA. No es un costo patronal adicional.

Para el empleador, la responsabilidad es:
1. Identificar a los empleados cuyo IBC supera 4 SMLMV
2. Aplicar la tarifa correcta según el rango
3. Descontar el aporte de la nómina del empleado
4. Reportar y pagar en la PILA bajo el concepto de Fondo de Solidaridad

El pago se hace junto con los demás aportes de seguridad social, dentro de los plazos PILA según el último dígito del NIT.

**Pregunta de seguimiento:**
Con la reforma pensional, ¿hay algún cambio pendiente en los aportes o en la obligatoriedad de migrar empleados a Colpensiones?

**Respuesta modelo (seguimiento):**
A la fecha de este documento, la reforma pensional (Ley 2381 de 2024) fue aprobada pero varios de sus artículos fueron demandados ante la Corte Constitucional. Los cambios principales que estaban previstos incluyen la creación de un pilar contributivo con umbral de cotización obligatoria a Colpensiones hasta 2,3 SMLMV.

Sin embargo, la migración obligatoria de afiliados del RAIS (fondos privados) a Colpensiones NO está vigente aún — los artículos sobre el régimen de transición están pendientes de definición constitucional.

En la práctica para PYMEs: por ahora, mantenga los aportes de pensión como están (16% del IBC: 12% empleador + 4% empleado) y no haga migraciones de fondo de pensiones sin que el empleado lo solicite voluntariamente. Los plazos de PILA no han cambiado.

Esté atento a las sentencias de la Corte Constitucional que definirán el alcance final de la reforma. No anticipe cambios que aún no están en firme.

---

## Pregunta 18 (M) — NIIF: Depreciación fiscal vs. NIIF y conciliación

**Pregunta inicial:**
Tengo un cliente PYME Grupo 2 que compró maquinaria por $120 millones en enero de 2025. (a) ¿Cuáles son las vidas útiles para depreciación fiscal vs. NIIF? (b) ¿Cómo calculo la diferencia temporaria para el impuesto diferido? (c) ¿Dónde registro esta diferencia en el Formato 2516?

**Respuesta modelo:**

**(a) Vidas útiles comparativas:**
Para maquinaria, las vidas útiles son:

| Concepto | Fiscal (Art. 137 ET) | NIIF (Sección 17 NIIF PYMEs) |
|----------|---------------------|-------------------------------|
| Maquinaria | 10 años | Según evaluación técnica (puede ser 8-15 años según uso real) |
| Valor residual fiscal | $0 (no se reconoce) | Sí se estima (ej. 5-10% del costo) |
| Método | Línea recta (default) | El que refleje el patrón de consumo de beneficios |

Supongamos que la evaluación técnica NIIF arroja una vida útil de 8 años con valor residual de $9.000.000 (7,5%).

**(b) Cálculo de la diferencia temporaria:**

Depreciación fiscal anual: $120.000.000 / 10 años = $12.000.000
Depreciación NIIF anual: ($120.000.000 – $9.000.000) / 8 años = $13.875.000

Diferencia anual: $13.875.000 – $12.000.000 = $1.875.000

Como la depreciación NIIF es mayor que la fiscal, la base fiscal del activo es mayor que la base contable al cierre del primer año:
- Base fiscal: $120.000.000 – $12.000.000 = $108.000.000
- Base contable NIIF: $120.000.000 – $13.875.000 = $106.125.000
- Diferencia temporaria deducible: $1.875.000

Impuesto diferido activo (IDA): $1.875.000 × 35% = $656.250

Esto significa que en el futuro la empresa podrá deducir más fiscalmente (cuando la vida fiscal siga corriendo después de que el activo esté totalmente depreciado en NIIF). Es un activo por impuesto diferido.

**(c) Formato 2516 (Conciliación Fiscal):**
La diferencia se reporta en el Formato 2516 (conciliación fiscal para PJ obligadas a llevar contabilidad). Específicamente:
- Sección de diferencias temporarias: registre la diferencia entre la base fiscal y la base contable del activo
- Clasifique como "diferencia temporaria deducible" si genera IDA, o "gravable" si genera pasivo por impuesto diferido (PDP)
- El impuesto diferido se calcula a la tarifa vigente (35%)

En los papeles de trabajo, documente: costo de adquisición, vida útil fiscal y NIIF, método de depreciación, valor residual NIIF, y el cálculo del impuesto diferido por cada activo.

**Pregunta de seguimiento:**
¿Puedo usar depreciación acelerada fiscalmente para esa maquinaria y cómo afectaría el cálculo del impuesto diferido?

**Respuesta modelo (seguimiento):**
Sí, el Art. 140 ET permite depreciación acelerada cuando la maquinaria opera en turnos adicionales. Si la maquinaria trabaja más de 16 horas diarias, puede aplicar un factor de aceleración de ×1,25 sobre la depreciación fiscal.

Con depreciación acelerada:
- Depreciación fiscal: $12.000.000 × 1,25 = $15.000.000/año
- Vida útil fiscal efectiva: $120M / $15M = 8 años
- Depreciación NIIF: $13.875.000/año (no cambia)

En este escenario, la depreciación fiscal es MAYOR que la NIIF ($15M vs. $13.875M):
- Diferencia temporaria gravable: $1.125.000
- Pasivo por impuesto diferido (PDP): $1.125.000 × 35% = $393.750

El efecto se invierte: ahora tiene un pasivo por impuesto diferido porque está deduciendo más rápido fiscalmente. En años futuros, cuando la maquinaria esté totalmente depreciada fiscalmente pero siga depreciándose contablemente, ese pasivo se revertirá.

Documente el uso de la aceleración con evidencia de los turnos de operación (registros de producción, bitácoras de máquina), porque la DIAN puede solicitar prueba de que la maquinaria efectivamente opera más de 16 horas.

---

## Pregunta 19 (S) — Obligaciones mercantiles: Renovación y asamblea

**Pregunta inicial:**
¿Cuáles son las obligaciones mercantiles que una SAS debe cumplir en el primer trimestre del año y qué pasa si no las cumple?

**Respuesta modelo:**
Las principales obligaciones del primer trimestre para una SAS son:

1. **Renovación de la matrícula mercantil (RUES)**: Plazo hasta el 31 de marzo de cada año. Se renueva ante la Cámara de Comercio del domicilio principal. El costo varía según los activos de la empresa. Si no renueva, la Cámara puede cancelar la matrícula, lo que implica perder la publicidad mercantil, no poder expedir certificados de existencia y representación legal, y problemas para contratar con el Estado.

2. **Asamblea General Ordinaria (AGO)**: Debe celebrarse dentro de los 3 primeros meses del año (por estatutos, generalmente antes del 31 de marzo). En la AGO se deben:
   - Aprobar los estados financieros del año anterior
   - Decidir sobre la distribución de utilidades o dividendos
   - Nombrar o ratificar revisor fiscal (si aplica)
   - Aprobar el informe de gestión del representante legal

   La convocatoria debe hacerse con entre 5 y 15 días de anticipación, según lo que digan los estatutos de la SAS. Para SAS con un solo accionista, basta un acta de decisiones del accionista único.

3. **Presentación de estados financieros ante la Supersociedades**: Si la SAS supera los topes de vigilancia (activos o ingresos superiores a 30.000 SMLMV), debe reportar estados financieros a la Superintendencia de Sociedades dentro de los plazos que esta establezca (normalmente abril).

Si la AGO aprueba distribución de dividendos, recuerde que la retención sobre dividendos se calcula según el Art. 242 ET (para personas naturales residentes) o Art. 245 ET (para no residentes — 20%).

**Pregunta de seguimiento:**
Si la SAS no alcanzó a hacer la asamblea antes del 31 de marzo, ¿qué consecuencias tiene y puede hacerla después?

**Respuesta modelo (seguimiento):**
Sí puede hacerla después, pero hay consecuencias:

Los estados financieros deben estar disponibles dentro de los 30 días siguientes al cierre del ejercicio (31 de diciembre), y la asamblea debe celebrarse dentro de los 3 primeros meses. Si no se cumple:

- **Supersociedades** puede imponer multas a los administradores por incumplimiento de sus deberes (Art. 86, Ley 222 de 1995)
- Los estados financieros aprobados extemporáneamente pueden tener problemas de oponibilidad frente a terceros
- Si hay controversia entre socios, la falta de asamblea oportuna puede ser usada como argumento en una acción de responsabilidad contra los administradores

En la práctica, las PYMEs unipersonales o con pocos socios suelen hacer la asamblea tardíamente sin consecuencias graves, pero la recomendación es formalizarla lo antes posible con un acta que indique las razones del retraso.

Para la renovación de matrícula (RUES), el incumplimiento después del 31 de marzo sí genera multas y la pérdida de la publicidad mercantil — esa fecha es más estricta.

---

## Pregunta 20 (M) — Régimen sancionatorio: Extemporaneidad y reducción

**Pregunta inicial:**
Un cliente persona jurídica se atrasó 3 meses en la presentación de la declaración de renta del AG 2024. El impuesto a cargo fue de $45.000.000. (a) ¿Cómo calculo la sanción por extemporaneidad? (b) ¿Puedo reducir la sanción con el Art. 640 ET? (c) ¿Cuál es la sanción mínima?

**Respuesta modelo:**

**(a) Cálculo de la sanción por extemporaneidad (Art. 641 ET):**
La sanción se calcula como el 5% del impuesto a cargo por cada mes o fracción de mes de retardo.

- Impuesto a cargo: $45.000.000
- Meses de retardo: 3
- Sanción = $45.000.000 × 5% × 3 = $6.750.000

Tope máximo: la sanción no puede exceder el 100% del impuesto a cargo ($45.000.000).

$6.750.000 está dentro del tope.

**(b) Reducción con Art. 640 ET:**
El Art. 640 ET establece niveles de reducción de sanciones:

- **Nivel 1 (reducción del 75%)**: Si la declaración se presenta antes de que la DIAN emita emplazamiento o pliego de cargos, y se paga la sanción reducida junto con la declaración.
  - Sanción reducida: $6.750.000 × 25% = $1.687.500

- **Nivel 2 (reducción del 50%)**: Si la declaración se presenta después del emplazamiento pero antes de la resolución sanción.
  - Sanción reducida: $6.750.000 × 50% = $3.375.000

- **Nivel 3 (sin reducción)**: Si la sanción se impone por resolución de la DIAN.
  - Sanción plena: $6.750.000

En este caso, si el cliente presenta voluntariamente (sin emplazamiento previo), aplica el Nivel 1 y la sanción sería $1.687.500.

**(c) Sanción mínima:**
La sanción mínima para 2026 es de 10 UVT = 10 × $52.374 = $523.740. Ninguna sanción puede ser inferior a ese valor. En este caso, $1.687.500 > $523.740, así que se paga la sanción calculada.

Adicionalmente, el cliente debe pagar intereses moratorios sobre el impuesto a cargo desde la fecha de vencimiento hasta la fecha de pago efectivo. La tasa de interés moratoria vigente es aproximadamente del 28,5% efectivo anual (se actualiza trimestralmente por la Superfinanciera).

**Pregunta de seguimiento:**
¿Y si el cliente presentó la declaración a tiempo pero sin pago? ¿Eso también genera sanción por extemporaneidad?

**Respuesta modelo (seguimiento):**
La presentación sin pago es válida — la declaración se entiende presentada en la fecha de su radicación, no en la fecha de pago. El contribuyente NO incurre en sanción por extemporaneidad si presentó dentro del plazo.

Sin embargo, la falta de pago genera:
1. **Intereses moratorios** (Art. 634 ET): sobre el impuesto no pagado desde el día siguiente al vencimiento del plazo para declarar. La tasa es la tasa de usura menos dos puntos, que actualmente ronda el 28,5% EA.

2. **Cobro coactivo**: Si no paga, la DIAN puede iniciar proceso de cobro coactivo (Art. 823 ET y siguientes), que incluye embargo de cuentas bancarias, bienes y retención de devoluciones de otros impuestos.

3. **Pérdida del beneficio de auditoría**: Si el contribuyente se acogió al beneficio de auditoría (Art. 689-3 ET) y no pagó la totalidad del impuesto dentro del plazo, pierde automáticamente el beneficio. La declaración vuelve al término de firmeza ordinario de 3 años.

La recomendación: siempre presente a tiempo, aunque no pueda pagar. Luego negocie el pago con la DIAN mediante facilidades de pago (Art. 814 ET), que permiten pagos a plazos con garantía.

---

## Pregunta 21 (S) — Firmeza de declaraciones

**Pregunta inicial:**
¿En qué fecha queda en firme la declaración de renta del AG 2022 para una persona jurídica que la presentó oportunamente el 10 de mayo de 2023, sin beneficio de auditoría?

**Respuesta modelo:**
La firmeza ordinaria de las declaraciones tributarias es de 3 años contados a partir de la fecha de vencimiento del plazo para declarar o de la fecha de presentación, la que sea posterior (Art. 714 ET).

Si el contribuyente presentó el 10 de mayo de 2023 y esa fecha estaba dentro del plazo (o era exactamente el vencimiento), la firmeza opera 3 años después del vencimiento del plazo para declarar.

Asumiendo que el vencimiento era alrededor del 10-26 de mayo de 2023 (según el calendario tributario AG 2022), la declaración quedaría en firme aproximadamente entre el 10 y el 26 de mayo de 2026.

Esto significa que la DIAN tiene hasta esa fecha para notificar requerimiento especial o emplazamiento para declarar. Si la fecha ya pasó o está próxima, la declaración está a punto de quedar en firme — es un momento crítico para documentación y archivos.

Excepción importante: si el contribuyente compensó pérdidas fiscales en esa declaración, el término de firmeza se extiende a 6 años (Art. 147, parágrafo 1 ET) para los ítems relacionados con la pérdida. Y si la declaración generó un saldo a favor que fue solicitado en devolución, el término de firmeza es de 5 años.

**Pregunta de seguimiento:**
Tengo un cliente con más de 130 declaraciones anuales entre renta, IVA, retención y GMF. ¿Hay alguna forma práctica de llevar el control de la firmeza de todas?

**Respuesta modelo (seguimiento):**
Sí. La recomendación del corpus es implementar una matriz de firmeza que rastree todas las declaraciones por tipo, período, fecha de presentación, y fecha estimada de firmeza. La distribución típica para una PJ es:

- Renta: 1 declaración anual → firmeza 3 años (o 6 si hay pérdidas, 5 si hay devolución, 6/12 meses si hay beneficio de auditoría)
- IVA: 3-6 declaraciones/año (cuatrimestral o bimestral) → firmeza 3 años cada una
- Retención en la fuente: 12 declaraciones/año (mensuales) → firmeza 3 años cada una
- GMF: 4 declaraciones/año (semanales agrupadas) → firmeza 3 años cada una

La matriz debe incluir:
- Columna de alerta: estado verde (>12 meses para firmeza), amarillo (6-12 meses), rojo (<6 meses)
- Columna de corrección: si alguna declaración fue corregida, anotar la fecha de corrección y recalcular firmeza
- Columna de documentación: verificar que todos los soportes están archivados y completos ANTES de que se acerque la firmeza

Esto es especialmente importante porque una vez que la declaración queda en firme, los soportes pueden archivarse con un nivel de resguardo menor. Antes de firmeza, deben estar listos para cualquier requerimiento de la DIAN.

La retención de documentos debe ser de mínimo 5 años como regla general (Art. 632 ET), independientemente de la firmeza.

---

## Pregunta 22 (M) — Devoluciones y saldos a favor

**Pregunta inicial:**
Un cliente PJ tiene un saldo a favor de $85.000.000 en su declaración de renta del AG 2025 (originado por exceso de retenciones). (a) ¿Qué opciones tiene para manejar ese saldo? (b) ¿Cuánto tiempo toma la devolución? (c) ¿Necesita garantía bancaria?

**Respuesta modelo:**

**(a) Tres opciones para el saldo a favor:**

1. **Imputación** al período siguiente: arrastra el saldo como anticipo en la declaración de renta del AG 2026. No requiere trámite ante DIAN. Es la opción más simple pero congela el efectivo por un año.

2. **Compensación** (Art. 815 ET): solicita que el saldo se aplique contra deudas de otros impuestos nacionales (IVA, retención, GMF). Requiere solicitud formal ante la DIAN. Útil si el contribuyente tiene obligaciones pendientes.

3. **Devolución en efectivo**: solicita la transferencia del saldo a la cuenta bancaria del contribuyente. Requiere presentar solicitud ante la DIAN con todos los soportes.

**(b) Tiempos de la devolución:**
Conforme a la Ley 2277 de 2022:
- **Sin garantía bancaria**: La DIAN tiene 50 días hábiles para resolver la solicitud
- **Con garantía bancaria**: El plazo se reduce a 30 días hábiles

El plazo para solicitar la devolución es de 2 años contados desde la fecha de vencimiento del plazo para declarar (Art. 854 ET). Si se acogió al beneficio de auditoría, el plazo se reduce al período de firmeza (6 o 12 meses).

**(c) Garantía bancaria:**
Para un saldo de $85.000.000, la decisión sobre la garantía depende del análisis costo-beneficio:

- **Montos hasta ~$20M**: Generalmente se tramitan sin garantía (50 días)
- **Montos entre $20M y $100M**: Evalúe el costo de la garantía vs. el beneficio de tener el dinero 20 días antes
- **Montos superiores a $100M**: La DIAN puede exigir garantía si detecta indicios de riesgo

La garantía bancaria tiene un costo (comisión bancaria, generalmente entre 1,5% y 3% anual del monto garantizado). Para $85M, el costo de la garantía podría ser entre $1.275.000 y $2.550.000.

Antes de solicitar, realice un checklist de validación de 10 puntos: verificar que las retenciones coincidan con los certificados, que los certificados estén vigentes, que la declaración no tenga errores aritméticos, que no haya inconsistencias con la información exógena, etc.

La tasa de rechazo de devoluciones es aproximadamente del 22%, principalmente por problemas documentales. Haga la tarea antes de solicitar.

**Pregunta de seguimiento:**
¿La DIAN puede abrir una fiscalización después de aprobar la devolución?

**Respuesta modelo (seguimiento):**
Sí, absolutamente. La aprobación de la devolución NO cierra la posibilidad de fiscalización. La DIAN puede:

1. **Investigación previa**: Dentro de los 90 días siguientes a la solicitud, la DIAN puede abrir investigación previa para verificar la procedencia del saldo.

2. **Fiscalización posterior**: Después de autorizar la devolución, la DIAN conserva la facultad de fiscalizar la declaración dentro del término de firmeza (3 años normalmente, o el plazo que aplique).

3. **Reintegro**: Si como resultado de la fiscalización la DIAN determina que el saldo a favor era improcedente (total o parcialmente), el contribuyente deberá reintegrar el monto devuelto más intereses moratorios, más una sanción del 50% del monto devuelto improcedentemente (Art. 670 ET).

Por eso es tan importante la validación previa de la documentación. Si las retenciones no están bien soportadas, si hay retenciones inexistentes, o si la declaración tiene errores de depuración, la devolución puede convertirse en un problema mayor.

La recomendación: construya un expediente sólido con certificados de retención originales, declaraciones del agente retenedor (Form 350), cruce con información exógena, y papeles de trabajo firmados. Ese expediente es su defensa ante una posible fiscalización post-devolución.

---

## Pregunta 23 (S) — Información exógena: Formatos y plazos

**Pregunta inicial:**
¿Cuáles son los umbrales para estar obligado a presentar información exógena del AG 2025 y cuáles son los plazos de vencimiento para 2026?

**Respuesta modelo:**
La obligación de reportar información exógena está regulada por la Resolución DIAN 000233. Los principales umbrales para el AG 2025 son:

**Obligados principales:**
- Personas jurídicas y naturales con ingresos brutos superiores a 2.400 UVT ($119.517.600 con UVT 2025 = $49.799)
- Grandes contribuyentes: obligados sin importar el monto de ingresos
- Entidades del sector financiero: obligadas sin importar monto
- Agentes de retención: obligados en los formatos correspondientes

**Formatos clave (AG 2025):**
- **Formato 1001** (Pagos y abonos — el más importante): Detalla cada pago a terceros con NIT, concepto, monto. ATENCIÓN: para AG 2025 se usa la **versión 11** del formato, no la versión 10. Este cambio es crítico — si envía la versión incorrecta, la DIAN rechaza el archivo.
- Formato 1003 (Retenciones practicadas)
- Formato 1005 (IVA descontable)
- Formato 1006 (IVA generado)
- Formato 1007 (Ingresos recibidos)
- Formato 1008 (Saldos de cuentas por cobrar)
- Formato 1009 (Saldos de cuentas por pagar)
- Formato 1010 (Información de socios)
- Formato 1011 (Información de deducciones)
- Formato 5101 (GMF — nuevo formato específico)

**Plazos de vencimiento (2026):**
Los plazos van del 28 de abril al 12 de junio de 2026, escalonados por los últimos dígitos del NIT. La fecha específica depende de su NIT.

Las sanciones por presentación extemporánea o con errores oscilan entre el 0,7% y el 1% de las sumas no reportadas o reportadas erróneamente.

**Pregunta de seguimiento:**
Se me pasó un proveedor en el Formato 1001 del año pasado y la DIAN me notificó. ¿Cómo corrijo y qué sanción me aplican?

**Respuesta modelo (seguimiento):**
Debe presentar una corrección del formato con la información completa. El proceso es:

1. Genere el archivo XML corregido con TODOS los registros (no solo el faltante — el archivo de corrección reemplaza al original)
2. Valide el archivo con el prevalidador de la DIAN (disponible en el portal MUISCA)
3. Presente a través de la opción "Corrección" en el servicio informático de exógena

La sanción por información exógena no reportada (Art. 651 ET) es:
- 5% de las sumas no reportadas o reportadas erróneamente, o
- 0,7% de las sumas reportadas (si la información es la correcta pero fue extemporánea)

La sanción se puede reducir con el Art. 640 ET:
- Si corrige voluntariamente antes de emplazamiento: reducción del 75% → paga solo el 25% de la sanción
- Si corrige después del emplazamiento pero antes de resolución: reducción del 50%

La sanción mínima aplica ($523.740 para 2026).

La recomendación para evitar este problema: antes de enviar la exógena, cruce los pagos del Formato 1001 contra la contabilidad (balance de comprobación por tercero) y contra las declaraciones de retención (Formulario 350). Cualquier diferencia significativa debe investigarse y documentarse.

---

## Pregunta 24 (M) — GMF e ICA: Optimización y deducción

**Pregunta inicial:**
Un cliente PYME tiene movimientos bancarios mensuales de $200 millones y opera en Bogotá en actividad comercial. (a) ¿Cómo puede optimizar el GMF (4×1000)? (b) ¿El ICA de Bogotá es deducible en renta? (c) ¿Cuánto vale la tarifa de ICA para comercio en Bogotá?

**Respuesta modelo:**

**(a) Optimización del GMF:**
El GMF grava a tarifa del 0,4% (4 por mil) cada transacción financiera. Con $200M mensuales, el costo bruto es $200.000.000 × 0,4% = $800.000/mes = $9.600.000/año.

Estrategias de optimización:

1. **Cuenta de ahorro exenta (Art. 879 ET):** El titular puede designar UNA cuenta de ahorro o corriente como exenta de GMF. Los retiros de esa cuenta hasta 350 UVT mensuales ($18.331.500 para 2026) no causan GMF. Use esta cuenta para los pagos más frecuentes.

2. **Tarjeta de crédito corporativa:** Los pagos con tarjeta de crédito no generan GMF en el momento del consumo — solo cuando paga la tarjeta. Si paga la tarjeta desde la cuenta exenta, optimiza el flujo.

3. **Transferencias internas entre cuentas del mismo titular:** Las transferencias entre cuentas del mismo titular en el mismo banco están exentas de GMF. Concentre fondos antes de hacer pagos grandes.

Ahorro estimado con las 3 estrategias combinadas: hasta $205.000/mes (depende del perfil de transacciones).

Además, el 50% del GMF pagado es deducible en la declaración de renta (Art. 115 ET). Entonces, de los ~$9.600.000 anuales de GMF, $4.800.000 son deducibles, generando un ahorro fiscal adicional de $4.800.000 × 35% = $1.680.000.

**(b) Deducibilidad del ICA en renta:**
Sí. Conforme al Art. 115 ET, el 50% del ICA efectivamente pagado durante el año gravable es deducible en la declaración de renta (no como descuento tributario, sino como deducción). Esto aplica siempre que el ICA se haya pagado dentro del período gravable.

**(c) Tarifa de ICA para comercio en Bogotá:**
La tarifa de ICA en Bogotá para actividades comerciales es de 4,14 por mil (0,414%) sobre los ingresos brutos ordinarios y extraordinarios obtenidos en la jurisdicción. Para servicios, la tarifa sube a 9,66 por mil (0,966%).

Adicionalmente, Bogotá cobra una sobretasa de bomberos del 15% sobre el ICA liquidado.

Para su cliente con $200M mensuales de ingresos en comercio en Bogotá:
- ICA anual estimado: $2.400.000.000 × 4,14‰ = $9.936.000
- Sobretasa bomberos (15%): $1.490.400
- Total ICA + sobretasa: $11.426.400

Declaración: bimestral en Bogotá. Plazos según el calendario de la Secretaría de Hacienda Distrital.

**Pregunta de seguimiento:**
¿Si mi cliente opera en Bogotá y también tiene una sucursal en Medellín, cómo distribuyo los ingresos para ICA entre las dos ciudades?

**Respuesta modelo (seguimiento):**
La distribución de ingresos para ICA cuando hay operación en múltiples municipios se rige por las reglas de territorialidad del impuesto. El principio general es que el ICA se causa donde se realiza la actividad económica:

1. **Actividades comerciales**: Los ingresos se asignan al municipio donde se encuentra ubicado el establecimiento de comercio desde donde se realizan las ventas. Si tiene un punto de venta en Bogotá y otro en Medellín, los ingresos de cada punto se declaran en su respectivo municipio.

2. **Actividades de servicios**: Se causan en el municipio donde se presta el servicio. Si el servicio se presta en Medellín (aunque el contrato se firme en Bogotá), el ICA se declara en Medellín.

3. **Actividades industriales**: Los ingresos se declaran en el municipio donde está la planta de producción, independientemente de dónde se vendan los productos.

Si la asignación no es clara (por ejemplo, ventas por internet), aplique el domicilio del establecimiento desde donde se despacha o se gestiona la venta.

Cada municipio tiene sus propias tarifas y calendarios. Medellín maneja tarifas diferentes a Bogotá para las mismas actividades. Debe verificar la tabla de tarifas de cada municipio y presentar declaraciones separadas.

La deducción del 50% en renta (Art. 115 ET) aplica para el ICA pagado en TODOS los municipios — se suman todos los ICA pagados y se deduce el 50% del total.

---

## Pregunta 25 (S) — Impuesto al patrimonio personas naturales

**Pregunta inicial:**
Un socio de una PYME que asesoro tiene un patrimonio líquido de $4.000 millones al 1 de enero de 2026. ¿Está obligado a declarar impuesto al patrimonio y cuánto le correspondería pagar?

**Respuesta modelo:**
Sí está obligado. El impuesto al patrimonio (Arts. 292-3 y 295-3 ET) aplica a personas naturales y sucesiones ilíquidas cuyo patrimonio líquido al 1 de enero del año sea igual o superior a 72.000 UVT.

Con UVT 2026 = $52.374:
- Umbral: 72.000 × $52.374 = $3.770.928.000
- Su patrimonio de $4.000.000.000 supera el umbral → SÍ es sujeto pasivo

**Exclusión por vivienda:** Puede excluir el valor de la vivienda de habitación hasta 12.000 UVT ($628.488.000). Si la vivienda vale $800M, solo excluye $628.488.000; el excedente se incluye en la base.

**Cálculo con tarifas marginales (Art. 295-3 ET):**
Las tarifas son progresivas:
- 0 a 72.000 UVT: 0%
- 72.000 a 122.000 UVT: 0,5%
- 122.000 a 239.000 UVT: 1,0%
- Más de 239.000 UVT: 1,5%

Base gravable estimada: $4.000.000.000 – $628.488.000 (vivienda) = $3.371.512.000

Convertido a UVT: $3.371.512.000 / $52.374 = 64.380 UVT

Como 64.380 UVT < 72.000 UVT → después de la exclusión de vivienda, la base queda por debajo del umbral.

**Resultado: NO paga impuesto al patrimonio** después de aplicar la exclusión de vivienda (asumiendo que la vivienda vale al menos el tope de 12.000 UVT).

Si no tuviera vivienda para excluir (o si la vivienda vale poco), la base sería $4.000M completos (76.381 UVT), y el impuesto sería:
- Sobre 72.000 a 76.381 UVT (4.381 UVT): 0,5% = 21,9 UVT = $1.147.034

Se declara en el Formulario 420, con pago en dos cuotas según el calendario tributario.

**Pregunta de seguimiento:**
¿Los bienes que tiene en la PYME (acciones o participaciones) cómo se valoran para el impuesto al patrimonio?

**Respuesta modelo (seguimiento):**
Las acciones o participaciones en sociedades se valoran para efectos del impuesto al patrimonio según el valor intrínseco fiscal — es decir, el patrimonio líquido de la sociedad (según estados financieros con base fiscal) dividido por el número de acciones en circulación. No se usa el valor comercial ni el valor NIIF.

El cálculo:
- Patrimonio líquido fiscal de la SAS: activos fiscales – pasivos fiscales
- Número de acciones en circulación: según el libro de accionistas
- Valor intrínseco por acción = Patrimonio líquido fiscal / Número de acciones
- Valor de la participación = Valor intrínseco × Número de acciones del socio

Si la SAS tiene un patrimonio líquido fiscal de $2.000.000.000 y el socio tiene el 100% de las acciones, su participación se valora en $2.000.000.000 para efectos del impuesto al patrimonio.

Esto es importante porque el valor comercial de las acciones podría ser muy diferente (mayor o menor) que el valor intrínseco fiscal. Para el impuesto al patrimonio, solo importa el fiscal.

Si el socio tiene inversiones en el exterior (cuentas bancarias, propiedades, acciones en empresas extranjeras), esas también se incluyen en la base del patrimonio. Colombia grava el patrimonio mundial de sus residentes fiscales.

---

## Pregunta 26 (M) — Dividendos: Depuración y retención

**Pregunta inicial:**
Una SAS con utilidad contable de $500 millones en AG 2025 quiere distribuir dividendos a sus 2 socios personas naturales residentes (50% cada uno). (a) ¿Cómo depuro la utilidad para determinar la parte gravada y no gravada? (b) ¿Cuánto le retengo a cada socio?

**Respuesta modelo:**

**(a) Depuración del Art. 49 ET:**
La depuración es obligatoria para determinar qué porción de los dividendos es gravada y cuál es no gravada. El cálculo es:

1. Tome la renta líquida gravable de la sociedad (no la utilidad contable — la fiscal): supongamos $450.000.000
2. Reste el impuesto de renta del ejercicio: $450M × 35% = $157.500.000
3. Sume los ingresos no constitutivos de renta que hayan afectado la utilidad contable
4. Sume las rentas exentas que hayan afectado la utilidad contable

Resultado simplificado:
- Utilidad máxima no gravada = Renta líquida – Impuesto + INCRNGO + Rentas exentas
- Utilidad máxima no gravada = $450M – $157,5M = $292.500.000

Si la utilidad contable distribuible es $500M:
- Parte no gravada (Art. 49): $292.500.000 (el menor entre la utilidad contable y el cálculo del Art. 49)
- Parte gravada: $500.000.000 – $292.500.000 = $207.500.000

Por socio (50%):
- Dividendo no gravado: $146.250.000
- Dividendo gravado: $103.750.000

**(b) Retención sobre dividendos (Art. 242 ET para PN residentes):**

**Sobre la parte NO gravada** ($146.250.000 por socio):
Se aplica la tabla escalonada del Art. 242:
- 0 a 1.090 UVT ($54.280.910): 0%
- 1.090 a 2.000 UVT ($99.598.000): 15%
- Más de 2.000 UVT: 20% (si aplica, verificar tabla vigente)

$146.250.000 = 2.938 UVT
- Sobre los primeros 1.090 UVT: $0
- Sobre 1.090 a 2.000 UVT (910 UVT = $45.317.090): 15% = $6.797.564
- Sobre 2.000 a 2.938 UVT (938 UVT = $46.726.812): 20% = $9.345.362

Retención sobre parte no gravada: ~$16.142.926

**Sobre la parte GRAVADA** ($103.750.000 por socio):
Se aplica primero el 35% (tarifa general PJ) y luego la tabla escalonada sobre el remanente.
- 35% × $103.750.000 = $36.312.500
- Remanente: $103.750.000 – $36.312.500 = $67.437.500
- Sobre el remanente se aplica nuevamente la tabla del Art. 242

**Retención total estimada por socio:** En el rango de $50-55 millones (dependiendo del cálculo exacto de la tabla escalonada sobre el remanente gravado).

La empresa debe practicar y declarar estas retenciones en el mes de pago del dividendo, usando el Formulario 350.

**Pregunta de seguimiento:**
¿Puedo distribuir los dividendos como abono en cuenta (cuenta 2505 — Dividendos por pagar) sin pagar efectivamente, y la retención se causa igual?

**Respuesta modelo (seguimiento):**
Sí. La retención sobre dividendos se causa en el momento del pago O abono en cuenta, lo que ocurra primero (Art. 369 ET). El abono en cuenta 2505 (Dividendos por pagar) constituye el hecho generador de la retención, aunque el dinero no se haya desembolsado.

Esto es un error muy frecuente en PYMEs: la asamblea decreta dividendos, el contador hace el abono en la cuenta 2505, y nadie practica la retención hasta que se hace el giro efectivo meses después. Eso genera extemporaneidad en la retención y puede acarrear sanción.

La recomendación es:
1. Al momento de decretar dividendos en la asamblea, determine inmediatamente la depuración Art. 49
2. Cuando contabilice el abono en cuenta 2505, practique la retención en ese mismo momento
3. Declare y pague la retención en el Formulario 350 del mes correspondiente al abono
4. Si el pago efectivo es posterior, la retención ya quedó causada y declarada

Si los dividendos no se van a pagar en el corto plazo, evalúe si conviene diferir el decreto de dividendos en la asamblea (dejar como "utilidades retenidas" y no decretar) para no generar la obligación de retención prematuramente.

---

## Pregunta 27 (S) — SAGRILAFT: Clasificación de PYMEs

**Pregunta inicial:**
¿Mi cliente PYME de comercio con activos de $3.000 millones está obligado a implementar SAGRILAFT o PTEE?

**Respuesta modelo:**
Para determinar la obligación, hay que verificar los umbrales de clasificación:

**SAGRILAFT (Sistema de Autocontrol y Gestión del Riesgo Integral):**
Obligatorio para empresas con activos totales superiores a 40.000 SMLMV. Con SMLMV 2026 = $1.750.905:
- Umbral SAGRILAFT: 40.000 × $1.750.905 = $70.036.200.000

Con activos de $3.000M, su cliente está MUY por debajo del umbral SAGRILAFT. No está obligado al SAGRILAFT completo.

**PTEE (Programa de Transparencia y Ética Empresarial):**
Obligatorio para empresas con activos entre 5.000 y 40.000 SMLMV:
- Umbral inferior PTEE: 5.000 × $1.750.905 = $8.754.525.000
- Umbral superior: $70.036.200.000

Con activos de $3.000M ($3.000.000.000), su cliente también está por debajo del umbral PTEE. No está obligado al PTEE.

**Excepciones por sector:** Independientemente del tamaño, las empresas en sectores de riesgo inherente (minería, joyería, servicios contables, inmobiliarias, casinos, cambio de divisas) pueden ser obligadas al SAGRILAFT por su actividad, sin importar los activos.

Si su cliente es una comercializadora regular de bienes de consumo, con activos de $3.000M, **NO está obligado ni al SAGRILAFT ni al PTEE**.

Sin embargo, es buena práctica que toda empresa, incluso las no obligadas, implemente medidas básicas de conocimiento del cliente (KYC) y reporte cualquier operación sospechosa a la UIAF. Esto protege al contador y a la empresa.

**Pregunta de seguimiento:**
¿Y si el año que viene los activos superan los $8.754 millones por una valorización de inventarios, entra automáticamente al PTEE?

**Respuesta modelo (seguimiento):**
Sí. La obligación de implementar PTEE se activa cuando los activos totales al cierre del ejercicio superan los 5.000 SMLMV vigentes. Si por valorización de inventarios, revaluaciones o crecimiento del negocio los activos superan $8.754.525.000 (con SMLMV 2026), la empresa queda obligada a implementar el PTEE para el año siguiente.

La implementación incluye:
1. Designar un Oficial de Cumplimiento (puede ser el representante legal en empresas pequeñas)
2. Elaborar una matriz de riesgos de lavado de activos y financiación del terrorismo
3. Implementar procedimientos de debida diligencia para clientes y proveedores
4. Establecer un canal interno de reporte de operaciones sospechosas
5. Reportar a la UIAF cuando corresponda (ROS — Reporte de Operación Sospechosa)

El plazo para implementar depende de la regulación de la Supersociedades. Generalmente se otorgan entre 6 y 12 meses desde que nace la obligación.

La recomendación: monitoree los activos al cierre de cada año y, si se acercan al umbral, comience a preparar la infraestructura de PTEE antes de que sea obligatorio. Implementar reactivamente bajo presión de la Supersociedades es más costoso y riesgoso.

---

## Pregunta 28 (M) — ZOMAC: Incentivos y requisitos

**Pregunta inicial:**
Un cliente quiere montar una empresa nueva en un municipio ZOMAC. (a) ¿Qué tarifas de renta le aplican y por cuánto tiempo? (b) ¿Qué requisitos de inversión y empleo debe cumplir? (c) ¿Cuándo se acaba el beneficio?

**Respuesta modelo:**

**(a) Tarifas progresivas ZOMAC (Ley 1819/2016, Arts. 235-238):**
Las tarifas dependen del tamaño de la empresa (según Decreto 957/2019) y del año gravable. Para AG 2025–2027:

- **Micro y pequeña empresa**: 17,5% (este tramo duplicó la tarifa — antes era 8,75% hasta AG 2024)
- **Mediana empresa**: 26,25%
- **Grande empresa**: 35% (sin beneficio)

El esquema es de transición progresiva hacia la tarifa general del 35%. Cada tramo de años incrementa la tarifa gradualmente.

**(b) Requisitos de inversión y empleo:**
La empresa debe cumplir requisitos mínimos según su tamaño:

Para micro y pequeña empresa:
- Inversión mínima: entre 40 y 7.800 SMLMV (dependiendo del tamaño exacto)
- Generación de empleo: entre 2 y 49 empleados vinculados directamente en el municipio ZOMAC

El municipio debe estar incluido en la lista de 344 municipios ZOMAC definidos por el Decreto 1650. La empresa debe constituirse y operar efectivamente en el municipio — no basta con tener el domicilio formal allí.

Debe documentar:
- Acta de constitución con domicilio en municipio ZOMAC
- Certificados de empleo generado (contratos laborales, PILA, nómina electrónica)
- Evidencia de inversión efectiva en el municipio
- Certificación de la Cámara de Comercio de operación real

**(c) Vigencia del beneficio:**
El beneficio ZOMAC tiene un horizonte de 10 años desde la constitución de la empresa, con la tarifa aumentando progresivamente. Las empresas constituidas antes del cierre de ventana pueden mantener el beneficio hasta su vencimiento.

Punto crítico: las empresas ZOMAC están **excluidas del beneficio de auditoría** (Art. 689-3 ET). Esto significa que sus declaraciones tienen el término de firmeza ordinario de 3 años — no pueden acortar la ventana de fiscalización.

El beneficio ZOMAC se proyecta vigente hasta el AG 2027 aproximadamente para las empresas de los primeros tramos. Después de esa fecha, la tarifa converge a la tarifa general del 35%.

**Pregunta de seguimiento:**
¿Si el cliente ya tiene una empresa en Bogotá y quiere abrir una sucursal en un municipio ZOMAC, obtiene el beneficio?

**Respuesta modelo (seguimiento):**
No. El beneficio ZOMAC aplica solo a **sociedades nuevas** constituidas exclusivamente para desarrollar actividades en el municipio ZOMAC. Una sucursal de una empresa existente no califica.

La empresa debe:
1. Constituirse como una persona jurídica nueva (SAS, LTDA, etc.)
2. Tener su domicilio principal en el municipio ZOMAC
3. Desarrollar su actividad productiva principal en ese municipio
4. No ser una reorganización, escisión o fusión de una empresa preexistente (anti-abuso)

Si su cliente quiere el beneficio, debe crear una nueva SAS con domicilio en el municipio ZOMAC, con capital propio de los socios, y operar realmente desde allí. Los ingresos deben provenir de la actividad económica desarrollada en la zona.

Si la DIAN determina que la empresa es una fachada (domicilio formal pero operación real en Bogotá), puede desconocer el beneficio y liquidar el impuesto a tarifa general del 35%, más sanciones por inexactitud (Art. 647 ET).

---

## Pregunta 29 (S) — Pérdidas fiscales: Compensación y TTD

**Pregunta inicial:**
Mi cliente PJ tiene pérdidas fiscales acumuladas de $200 millones originadas en el AG 2020. ¿Hasta cuándo puede compensarlas y cómo afecta eso la TTD?

**Respuesta modelo:**
Según el Art. 147 ET (modificado por la Ley 1819 de 2016), las pérdidas fiscales generadas a partir del AG 2017 se pueden compensar en los 12 años siguientes. Las pérdidas del AG 2020 se pueden compensar hasta el AG 2032.

La compensación se aplica contra la renta líquida del ejercicio, sin límite porcentual (puede compensar el 100% de la renta líquida del año). Si no la agota en un año, el saldo se arrastra al siguiente, dentro de la ventana de 12 años.

**Interacción con la TTD:**
Aquí viene lo importante. La compensación de pérdidas fiscales afecta el cálculo de la TTD porque la variable "C" (Compensación) se suma a la Utilidad Depurada (UD):

UD = UC + DPARL – INCRNGO – VIMPP – VNGO – RE + **C**

Cuando compensa pérdidas, la renta líquida gravable baja → el INR baja → el ID baja. Pero la UD se incrementa por la adición de C. Esto puede causar que la TTD caiga por debajo del 15% y active el Impuesto a Adicionar (IA).

Ejemplo: Si la renta líquida antes de compensación es $300M y compensa $200M de pérdidas:
- Renta líquida gravable: $100M
- Impuesto al 35%: $35M
- ID ≈ $35M
- Pero UD incluye el efecto de la compensación ($200M), manteniendo o elevando el denominador

El TTD resultante podría quedar por debajo del 15%, generando un IA que en parte neutraliza el ahorro de la compensación.

La recomendación: antes de compensar, haga una simulación completa del TTD con y sin compensación. En algunos casos, conviene compensar parcialmente para que la TTD quede justo en 15% o ligeramente arriba, optimizando el beneficio.

**Pregunta de seguimiento:**
¿El término de firmeza de la declaración donde se originó la pérdida también cambia?

**Respuesta modelo (seguimiento):**
Sí, y es un punto crítico. El Art. 147, parágrafo 1 ET establece que el término de firmeza para las declaraciones donde se determinan o compensan pérdidas fiscales se extiende a 6 años (no los 3 ordinarios).

Esto significa:
- La declaración del AG 2020 (donde se originó la pérdida): tiene firmeza de 6 años desde el vencimiento para declarar. Si el vencimiento fue en abril 2021, la firmeza sería en abril 2027.
- Cada declaración posterior donde se compense parcialmente la pérdida: también tiene firmeza de 6 años en lo que respecta a la pérdida compensada.

Adicionalmente, la DIAN puede revisar la procedencia de la pérdida (es decir, volver a la declaración del AG 2020) incluso cuando fiscaliza el año en que se compensa. Esto amplía significativamente la ventana de riesgo fiscal.

Para protegerse:
1. Mantenga un inventario detallado de pérdidas con fecha de origen, monto original, compensaciones anuales, y saldo disponible
2. Documente la legitimidad de la pérdida original con papeles de trabajo completos
3. No destruya soportes del AG 2020 hasta que hayan prescrito todas las declaraciones donde se compensó

---

## Pregunta 30 (M) — Obligaciones del contador: Firma y responsabilidades

**Pregunta inicial:**
Un colega me pregunta en qué casos la firma del contador es obligatoria en las declaraciones tributarias de una PJ y qué responsabilidades asumo al firmar. (a) ¿Cuándo es obligatoria mi firma? (b) ¿Qué certifico implícitamente al firmar? (c) ¿Qué sanciones me pueden imponer?

**Respuesta modelo:**

**(a) Cuándo es obligatoria la firma del contador (Arts. 596-597 ET):**
La firma del contador público es obligatoria en las declaraciones tributarias de personas jurídicas cuando:
- El patrimonio bruto del año anterior es igual o superior a 100.000 UVT ($5.237.400.000 para 2026), O
- Los ingresos brutos del año anterior son iguales o superiores a 100.000 UVT

Si la empresa tiene revisor fiscal (por obligación legal o estatutaria), es el revisor fiscal quien firma — no el contador externo.

Para PYMEs con patrimonio e ingresos inferiores a 100.000 UVT, la firma del contador no es obligatoria, pero muchas PYMEs la incluyen voluntariamente como buena práctica.

**(b) Qué certifica implícitamente al firmar (Art. 581 ET):**
Al estampar su firma, usted certifica 5 cosas:

1. Que los libros de contabilidad se llevan conforme a las normas legales y a los principios contables (NIIF)
2. Que los libros reflejan razonablemente la situación financiera de la empresa
3. Que los soportes documentales existen y están a disposición de las autoridades
4. Que las cifras de la declaración son fieles reflejo de los libros de contabilidad
5. Que las retenciones declaradas fueron efectivamente practicadas y los valores corresponden a los certificados expedidos

Esto implica que usted responde solidariamente si alguna de estas certificaciones resulta falsa.

**(c) Sanciones:**

Sanciones tributarias (Art. 658-1 ET):
- Multa de hasta 4.100 UVT ($214.733.400 para 2026) si la información certificada es falsa, inexacta o contiene vicios
- La sanción recae sobre el contador directamente, no sobre la empresa

Sanciones disciplinarias (JCC — Ley 43 de 1990):
- Amonestación
- Multa
- Suspensión de la tarjeta profesional hasta por 2 años
- Cancelación de la tarjeta profesional en casos graves

El contador debe mantener un checklist de verificación antes de firmar (el corpus recomienda 40 puntos de verificación) que documente que cumplió con su deber de diligencia.

**Pregunta de seguimiento:**
¿Hasta cuándo debo conservar los papeles de trabajo que soportan la declaración que firmé?

**Respuesta modelo (seguimiento):**
La obligación de retención documental tiene dos dimensiones:

1. **Obligación tributaria (Art. 632 ET):** Los soportes deben conservarse por un mínimo de 5 años contados desde el 1 de enero del año siguiente a su elaboración, expedición o recibo. Para documentos relacionados con declaraciones que tengan firmeza extendida (pérdidas fiscales: 6 años; devoluciones: 5 años), la retención debe cubrir al menos el período de firmeza.

2. **Obligación profesional (DUR 2420/2015, Ley 43 de 1990):** Los papeles de trabajo del contador deben conservarse por al menos 5 años. La JCC puede solicitar estos papeles en cualquier proceso disciplinario.

La recomendación práctica: conserve todos los papeles de trabajo (incluyendo borradores, cálculos intermedios, comunicaciones con el cliente, y evidencia de las verificaciones realizadas) por un mínimo de 6 años. Si la declaración involucra pérdidas fiscales que se compensarán en años futuros, conserve hasta que la última declaración donde se compense quede en firme — potencialmente hasta 18 años (12 años de compensación + 6 años de firmeza).

Digitalice todo. Un archivo digital bien organizado (con fecha, tipo de soporte, y referencia al contribuyente/período) es la mejor protección ante un proceso disciplinario o una fiscalización de la DIAN.

La actualización de la tarjeta profesional ante la JCC debe hacerse antes del 31 de mayo de cada año. Verifique los requisitos de educación continuada, ya que la JCC puede condicionar la renovación al cumplimiento de horas de actualización profesional.

---

## Resumen de distribución

| Pregunta | Tipo | Macro-área | Tema específico |
|----------|------|-----------|-----------------|
| Q1 | S | Renta | Deducción factura electrónica |
| Q2 | M | Renta | TTD — Tasa de Tributación Depurada |
| Q3 | S | Renta | Beneficio de auditoría |
| Q4 | M | Renta | Anticipo del impuesto |
| Q5 | S | Renta | Tarifas especiales (hotel) |
| Q6 | M | IVA | Periodicidad y prorrateo |
| Q7 | S | IVA | ReteIVA a grandes contribuyentes |
| Q8 | M | Retención | Tabla salarial 2026 |
| Q9 | S | Retención | Honorarios y servicios |
| Q10 | M | Facturación electrónica | Habilitación y operación |
| Q11 | S | Facturación electrónica | Notas crédito |
| Q12 | M | RST | Elegibilidad y comparación |
| Q13 | S | RST | Mecánica anticipos bimestrales |
| Q14 | M | Nómina | Liquidación y parafiscales |
| Q15 | S | Laboral | Reforma laboral Ley 2466 |
| Q16 | M | Laboral | Trabajo tiempo parcial |
| Q17 | S | Pensiones | Fondo de Solidaridad Pensional |
| Q18 | M | NIIF | Depreciación fiscal vs. NIIF |
| Q19 | S | Mercantil | Obligaciones primer trimestre |
| Q20 | M | Sancionatorio | Extemporaneidad y reducción |
| Q21 | S | Firmeza | Término de firmeza declaraciones |
| Q22 | M | Devoluciones | Saldos a favor procedimiento |
| Q23 | S | Exógena | Formatos y plazos |
| Q24 | M | GMF/ICA | Optimización y deducción |
| Q25 | S | Patrimonio | Impuesto patrimonio PN |
| Q26 | M | Dividendos | Depuración y retención |
| Q27 | S | SAGRILAFT | Clasificación PYMEs |
| Q28 | M | ZOMAC | Incentivos y requisitos |
| Q29 | S | Pérdidas fiscales | Compensación y TTD |
| Q30 | M | Contador | Firma y responsabilidades |

---

*Documento generado exclusivamente con base en el Corpus Lia Contador — CORE ya Arriba. No se utilizaron fuentes externas ni conocimiento fuera del corpus para las respuestas modelo.*
