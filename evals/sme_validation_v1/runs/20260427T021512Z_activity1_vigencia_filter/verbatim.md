# §1.G SME validation — verbatim responses

**Run dir:** `evals/sme_validation_v1/runs/20260427T021512Z_activity1_vigencia_filter`
**Generated:** 2026-04-26 09:24:32 PM Bogotá
**Responses included:** 36 / 36

Every response below is reproduced word-for-word as the chat server
returned it. No truncation, no editing.

---

## beneficio_auditoria

### beneficio_auditoria_P1

- **Class:** 🔴 refused
- **answer_mode:** `topic_safety_abstention`
- **effective_topic:** `beneficio_auditoria` (expected `beneficio_auditoria`)
- **fallback_reason:** `pipeline_d_coherence_chunks_off_topic`
- **citations:** 0
- **answer length:** 276 chars
- **latency:** 7627 ms

**Question:**

> Si una empresa quiere acogerse al beneficio de auditoría este año, ¿cuánto tiene que subir el impuesto frente al año pasado y cuánto se reduce el plazo de firmeza?

**Answer (verbatim):**

No pude ubicar evidencia del tema **beneficio_auditoria** en el grafo. Los documentos de apoyo recuperados pertenecen al tema **precios_de_transferencia**; prefiero no responder con evidencia cruzada. Reformula la consulta o confirma si necesitas orientación de ese otro tema.

---

### beneficio_auditoria_P2

- **Class:** 🟢 served_strong
- **answer_mode:** `graph_native`
- **effective_topic:** `beneficio_auditoria` (expected `beneficio_auditoria`)
- **fallback_reason:** `None`
- **citations:** 5
- **answer length:** 3570 chars
- **latency:** 23854 ms

**Question:**

> Tengo una SAS comercializadora con ingresos de $2.800 millones en 2025 y un impuesto neto de renta de $95 millones. El año pasado pagaron $70 millones. Quieren acogerse a beneficio de auditoría. ¿Califican? ¿Y si más adelante toca corregir la declaración para meter unos ingresos que se omitieron, pierden el beneficio?

**Answer (verbatim):**

**Respuestas directas**
- **Tengo una SAS comercializadora con ingresos de $2.800 millones en 2025 y un impuesto neto de renta de $95 millones. El año pasado pagaron $70 millones. Quieren acogerse a beneficio de auditoría. ¿Califican?**
  - Para calificar al beneficio de auditoría, la SAS debe cumplir con los requisitos del Estatuto Tributario. El beneficio aplica si el impuesto neto de renta se incrementa en los porcentajes establecidos, comparado con el impuesto del año anterior.
  - En este caso, el impuesto neto de renta proyectado para 2025 es de $95 millones, y el pagado en 2024 fue de $70 millones.
  - El incremento es de $25 millones ($95M - $70M), lo que representa un aumento del 35.71% ($25M / $70M).
  - La Ley 2277 de 2022 modificó los requisitos para el beneficio de auditoría. Para declaraciones presentadas en 2025 (correspondientes al año gravable 2024), se requiere un incremento del impuesto neto de renta del 30% para que la firmeza sea de 6 meses, o del 20% para que sea de 12 meses.
  - Dado que el incremento es del 35.71%, la SAS califica para el beneficio de auditoría, obteniendo una firmeza de 6 meses para su declaración de renta de 2025.
- **¿Y si más adelante toca corregir la declaración para meter unos ingresos que se omitieron, pierden el beneficio?**
  - Sí, la corrección de la declaración de renta que disminuya el impuesto a pagar o aumente el saldo a favor, o que implique una modificación de los ingresos declarados, puede llevar a la pérdida del beneficio de auditoría si la corrección no mantiene el incremento porcentual requerido.
  - Si la corrección implica la inclusión de ingresos omitidos, esto aumentaría el impuesto neto de renta. Siempre y cuando la declaración corregida siga cumpliendo con el incremento porcentual mínimo del impuesto neto de renta (30% para 6 meses o 20% para 12 meses) respecto al año anterior, el beneficio de auditoría se mantiene.
  - Es crucial que, después de la corrección, el nuevo impuesto neto de renta siga superando el umbral del 30% (o 20%) sobre el impuesto del año anterior para conservar la firmeza reducida.

**Ruta sugerida**
- **Verificar el cumplimiento de los requisitos formales:** Asegurarse de que la declaración de renta se presente oportunamente y sin errores formales que puedan invalidar el beneficio.
- **Monitorear el incremento del impuesto neto de renta:** Confirmar que el incremento del 35.71% se mantenga en la declaración final.
- **Evaluar el impacto de posibles correcciones:** Antes de realizar cualquier corrección, proyectar el nuevo impuesto neto de renta para asegurar que el beneficio de auditoría no se pierda.

**Riesgos y condiciones**
- **Pérdida del beneficio por correcciones:** Si una corrección posterior reduce el impuesto neto de renta o no mantiene el incremento porcentual requerido, se pierde el beneficio de auditoría y la declaración queda sujeta al término general de firmeza (art. 705 ET).
- **Inconsistencias en la información:** Cualquier inconsistencia detectada por la DIAN podría llevar a la pérdida del beneficio y a una fiscalización (Sección 26).
- **Cambios normativos:** Estar atento a posibles modificaciones en la Ley 2277 de 2022 o en el Estatuto Tributario que puedan afectar las condiciones del beneficio de auditoría.

**Soportes clave**
- Ley 2277 de 2022 (modifica el Estatuto Tributario en relación con el beneficio de auditoría).
- Estatuto Tributario (DECRETO 624 DE 1989 - Colombia | SUIN Juriscol), específicamente los artículos relacionados con el beneficio de auditoría y la firmeza de las declaraciones.

**Citations (verbatim):**

  1. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_09_Libro1_T1_Caps8a11.md'
  2. (no label) — doc_id='CORE_ya_Arriba_RENTA_LOGGRO_seccion-26-fiscalizacion-y-defensa-ante-la-dian.md'
  3. (no label) — doc_id='CORE_ya_Arriba_LEYES_INVERSIONES_INCENTIVOS_consolidado_Ley-1429-2010.md'
  4. (no label) — doc_id='suin_1132325'
  5. (no label) — doc_id='suin_1104445'

---

### beneficio_auditoria_P3

- **Class:** 🟡 served_acceptable
- **answer_mode:** `graph_native_partial`
- **effective_topic:** `beneficio_auditoria` (expected `beneficio_auditoria`)
- **fallback_reason:** `pipeline_d_no_graph_primary_articles`
- **citations:** 6
- **answer length:** 867 chars
- **latency:** 10656 ms

**Question:**

> Mi cliente, una SAS, cerró 2025 con TTD por debajo del 15% y le tocó liquidar Impuesto a Adicionar. Sin el IA el incremento del impuesto neto frente a 2024 quedaría en 22%, pero con el IA sumando llega al 28%. ¿La DIAN me deja contar el IA dentro del impuesto neto para alcanzar el umbral del beneficio? Y aparte de eso, mi cliente está en ZOMAC, ¿eso cambia algo?

**Answer (verbatim):**

**Respuestas directas**
- **¿La DIAN me deja contar el IA dentro del impuesto neto para alcanzar el umbral del beneficio?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.
- **¿eso cambia algo?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

**Ruta sugerida**
1. Confirma si el emisor estaba obligado a facturar electrónicamente y si existió una contingencia válida antes de aceptar el soporte.
2. Realiza una revisión operativa del soporte antes de considerarlo fiscalmente.

**Riesgos y condiciones**
- No uses soportes distintos a la factura electrónica cuando la obligación de facturar electrónicamente existía (art. 808 ET).
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

**Citations (verbatim):**

  1. (no label) — doc_id='CORE_ya_Arriba_LEYES_INVERSIONES_INCENTIVOS_consolidado_Ley-1429-2010.md'
  2. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_18_Libro5_Procedimiento_P1.md'
  3. (no label) — doc_id='suin_1132325'
  4. (no label) — doc_id='suin_1104445'
  5. (no label) — doc_id='CORE_ya_Arriba_Documents_to_branch_and_improve_Regimen_Cambiario_Normativa_Base_cam_normativa_regimen_cambiario.md'
  6. (no label) — doc_id='CORE_ya_Arriba_REGIMEN_CAMBIARIO_PYME_EXPERTOS_E01-regimen-cambiario-pyme-interpretaciones-expertos.md'

---

## firmeza_declaraciones

### firmeza_declaraciones_P1

- **Class:** 🟢 served_strong
- **answer_mode:** `graph_native`
- **effective_topic:** `firmeza_declaraciones` (expected `firmeza_declaraciones`)
- **fallback_reason:** `None`
- **citations:** 4
- **answer length:** 3186 chars
- **latency:** 19449 ms

**Question:**

> ¿Cuánto tiempo tiene la DIAN para revisar y modificar una declaración de renta de una SAS que se presentó normal, sin pérdidas ni beneficio de auditoría?

**Answer (verbatim):**

**Respuestas directas**

*   **¿Cuánto tiempo tiene la DIAN para revisar y modificar una declaración de renta de una SAS que se presentó normal, sin pérdidas ni beneficio de auditoría?**
    *   El término general de firmeza para una declaración de renta es de tres (3) años, contados a partir de la fecha de vencimiento del plazo para declarar, o de la fecha de presentación si fue extemporánea (art. 705 ET).
    *   Si la declaración presenta un saldo a favor, el término de firmeza es de tres (3) años contados a partir de la fecha de presentación de la solicitud de devolución o compensación (art. 705 ET).
    *   Si la declaración de renta compensa pérdidas fiscales, el término de firmeza se extiende a seis (6) años (art. 147 ET).
    *   Si la declaración de renta genera pérdidas fiscales, el término de firmeza es de seis (6) años, contados a partir de la fecha de vencimiento del plazo para declarar (art. 147 ET).
    *   Si la declaración de renta se acoge al beneficio de auditoría, el término de firmeza es de seis (6) o doce (12) meses, dependiendo del incremento del impuesto neto de renta (art. 689-1 ET).
    *   Si la declaración de renta incluye activos omitidos o pasivos inexistentes, el término de firmeza es de cinco (5) años (art. 239-1 ET).
    *   Si la declaración de renta es de un contribuyente con régimen de precios de transferencia, el término de firmeza es de seis (6) años (art. 260-10 ET).

**Ruta sugerida**

1.  La regla principal del art. 147 ET establece que las sociedades compensan las pérdidas fiscales con rentas líquidas ordinarias futuras; no se trasladan a los socios ni se tratan como un saldo a favor.
2.  Para las pérdidas fiscales bajo el régimen actual, el límite es temporal: doce (12) períodos gravables siguientes, sin tope porcentual anual (arts. 147 y 356-1 ET).
3.  La firmeza de la declaración debe evaluarse de forma independiente: una cosa es la mecánica de compensación y otra el término de revisión de esa pérdida (arts. 147 y 260 ET).
4.  Si el saldo de pérdidas proviene de años anteriores a 2017, primero se debe validar el régimen transitorio del art. 290 ET antes de aplicar la regla de los 12 años.

**Riesgos y condiciones**

*   No se debe cerrar la posición solo con el término 'compensación' sin distinguir el tipo: el problema principal aquí son las pérdidas fiscales en renta, no la devolución o compensación de saldos a favor (arts. 147 y 588 ET).
*   No se debe aplicar la regla ordinaria de firmeza de 3 años si la declaración origina o compensa pérdidas fiscales; en esos casos, el expediente debe considerarse a 6 años (arts. 147 y 260 ET).
*   No se debe usar la lógica del art. 588 ET cuando la corrección aumenta el saldo a favor o disminuye el valor a pagar.

**Soportes clave**

| Artículo | Descripción |
| :------- | :---------- |
| Art. 147 ET | COMPENSACIÓN DE PÉRDIDAS FISCALES DE SOCIEDADES |
| Art. 260-10 ET | Los contribuyentes del impuesto sobre la renta y complementarios, cuyo patrimonio bruto en el último día del año o período gravable sea igual o superior al equivalente a cien mil (100.000) UVT |
| Art. 588 ET | CORRECCIONES QUE AUMENTAN EL IMPUESTO O DISMINUYEN EL SALDO A FAVOR |

**Citations (verbatim):**

  1. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_09_Libro1_T1_Caps8a11.md'
  2. (no label) — doc_id='CORE_ya_Arriba_LEYES_INVERSIONES_INCENTIVOS_consolidado_Ley-1429-2010.md'
  3. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_20_Libro6_GMF.md'
  4. (no label) — doc_id='suin_1132325'

---

### firmeza_declaraciones_P2

- **Class:** 🟡 served_acceptable
- **answer_mode:** `graph_native`
- **effective_topic:** `firmeza_declaraciones` (expected `firmeza_declaraciones`)
- **fallback_reason:** `None`
- **citations:** 7
- **answer length:** 1034 chars
- **latency:** 20493 ms

**Question:**

> Recibí en febrero de 2026 un cliente nuevo. Presentó la declaración de renta del 2022 en mayo de 2023, no usó beneficio de auditoría, no tuvo pérdidas. ¿Esa declaración ya quedó en firme o todavía la DIAN puede tocarla? El cliente está nervioso porque le llegó un oficio persuasivo y quiere saber si todavía está expuesto.

**Answer (verbatim):**

**Respuestas directas**
- **Recibí en febrero de 2026 un cliente nuevo. Presentó la declaración de renta del 2022 en mayo de 2023, no usó beneficio de auditoría, no tuvo pérdidas. ¿Esa declaración ya quedó en firme o todavía la DIAN puede tocarla?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.
- **El cliente está nervioso porque le llegó un oficio persuasivo y quiere saber si todavía está expuesto?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

**Ruta sugerida**
1. Confirma si el emisor tenía la obligación de facturar electrónicamente y si existió una contingencia válida antes de aceptar el soporte (arts. 100 y 101 ET).
2. Realiza una revisión operativa del soporte antes de proceder con la defensa fiscal (arts. 100 y 101 ET).

**Riesgos y condiciones**
- Evita reemplazar la factura electrónica con otro tipo de soporte cuando la obligación de facturar electrónicamente era aplicable (arts. 100 y 102-2 ET).

**Citations (verbatim):**

  1. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_09_Libro1_T1_Caps8a11.md'
  2. (no label) — doc_id='CORE_ya_Arriba_RENTA_LOGGRO_seccion-26-fiscalizacion-y-defensa-ante-la-dian.md'
  3. (no label) — doc_id='CORE_ya_Arriba_LEYES_INVERSIONES_INCENTIVOS_consolidado_Ley-1429-2010.md'
  4. (no label) — doc_id='suin_1132325'
  5. (no label) — doc_id='suin_1104445'
  6. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_18_Libro5_Procedimiento_P1.md'
  7. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_20_Libro6_GMF.md'

---

### firmeza_declaraciones_P3

- **Class:** 🟢 served_strong
- **answer_mode:** `graph_native`
- **effective_topic:** `firmeza_declaraciones` (expected `firmeza_declaraciones`)
- **fallback_reason:** `None`
- **citations:** 7
- **answer length:** 2635 chars
- **latency:** 19828 ms

**Question:**

> Una SAS compensó en la declaración del 2024 unas pérdidas que generó en 2018. Ya entregamos esa declaración. Ahora me pregunto: ¿la firmeza de la declaración del 2024 es de 3 o de 5 años por haber compensado? ¿Y si encima la DIAN quiere meterse a revisar la pérdida del 2018 que ya está más que vencida en términos generales, lo puede hacer?

**Answer (verbatim):**

**Respuestas directas**
- **¿la firmeza de la declaración del 2024 es de 3 o de 5 años por haber compensado?**
  - La firmeza de la declaración donde se compensan pérdidas fiscales no se rige por el término ordinario de 3 años. En este caso, el término de firmeza es de 6 años (arts. 147 y 260 ET).
  - Si las pérdidas compensadas provienen de años anteriores a 2017, es necesario validar el régimen de transición del art. 290 ET antes de aplicar el límite de 12 años.
  - Es clave tener un inventario detallado de las pérdidas por año de origen, el saldo pendiente y la renta líquida disponible del período para determinar el monto a compensar.
  - Cobertura pendiente para esta sub-pregunta.
- **¿Y si encima la DIAN quiere meterse a revisar la pérdida del 2018 que ya está más que vencida en términos generales, lo puede hacer?**
  - La DIAN puede revisar la pérdida fiscal del 2018 si esta fue compensada en la declaración de renta del 2024, ya que el término de firmeza de la declaración donde se compensa la pérdida es de 6 años (arts. 147 y 260 ET).
  - Si la sociedad volvió a generar renta líquida positiva, la compensación de pérdidas acumuladas debe realizarse dentro del marco legal vigente (art. 147 ET).

**Ruta sugerida**
1.  La regla general del art. 147 ET establece que las sociedades pueden compensar pérdidas fiscales con rentas líquidas ordinarias futuras, sin que estas se trasladen a los socios o se traten como saldo a favor.
2.  Para las pérdidas sujetas al régimen actual, el límite temporal es de doce períodos gravables siguientes, sin un tope porcentual anual (arts. 147 y 647-1 ET).
3.  La firmeza de la declaración donde se compensan pérdidas debe analizarse de forma independiente. El término de revisión para estas pérdidas es de 6 años (arts. 147 y 260 ET).
4.  Si las pérdidas provienen de años anteriores a 2017, es fundamental validar el régimen de transición del art. 290 ET antes de aplicar el límite de 12 años.

**Riesgos y condiciones**
-   No confundir la compensación de pérdidas fiscales con la devolución o compensación de saldos a favor. Son procesos distintos con normativas específicas (arts. 147 y 857 ET).
-   El término de firmeza para declaraciones que originan o compensan pérdidas fiscales no es el ordinario de 3 años; se extiende a 6 años (arts. 147 y 260 ET).
-   Evitar aplicar la lógica del art. 588 ET cuando la corrección implica una disminución del valor a pagar o un aumento del saldo a favor, ya que esto se rige por el art. 589 ET.
-   No solicitar una devolución o compensación si la declaración aún presenta inconsistencias o requiere corrección (arts. 857 y 588 ET).

**Citations (verbatim):**

  1. (no label) — doc_id='to_upload_BRECHAS-SEMANA4-ABRIL-2026_FIRMEZA_DECLARACIONES_EXPERTOS_EXPERTOS_FIR-E01-interpretaciones-firmeza-beneficio-auditoria.md'
  2. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_09_Libro1_T1_Caps8a11.md'
  3. (no label) — doc_id='CORE_ya_Arriba_LEYES_INVERSIONES_INCENTIVOS_consolidado_Ley-1429-2010.md'
  4. (no label) — doc_id='suin_1132325'
  5. (no label) — doc_id='CORE_ya_Arriba_FIRMEZA_DECLARACIONES_ART714_NORMATIVA_FIR-N01-marco-legal-firmeza-declaraciones-tributarias-art-714-ET.md'
  6. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_20_Libro6_GMF.md'
  7. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_18_Libro5_Procedimiento_P1.md'

---

## regimen_sancionatorio_extemporaneidad

### regimen_sancionatorio_extemporaneidad_P1

- **Class:** 🔵 served_off_topic
- **answer_mode:** `graph_native`
- **effective_topic:** `declaracion_renta` (expected `regimen_sancionatorio_extemporaneidad`)
- **fallback_reason:** `None`
- **citations:** 4
- **answer length:** 2317 chars
- **latency:** 16280 ms

**Question:**

> ¿Cuánto cobra la DIAN por presentar una declaración de renta tarde si no hay impuesto a cargo?

**Answer (verbatim):**

### Respuestas directas

*   **¿Cuánto cobra la DIAN por presentar una declaración de renta tarde si no hay impuesto a cargo?**
    *   La sanción mínima por extemporaneidad es de 10 UVT (art. 639 ET). Para el año 2024, esto equivale a $470.650.
    *   Esta sanción aplica incluso si la declaración no arroja impuesto a cargo.

*   **¿Hay alguna forma de reducir esta sanción?**
    *   Sí, la sanción se puede reducir al 50% si la declaración se presenta antes de que la DIAN profiera pliego de cargos o auto de inspección tributaria (art. 640 ET).
    *   También se puede reducir al 75% si la declaración se presenta después de la notificación del pliego de cargos o auto de inspección, pero antes de la notificación de la liquidación de revisión (art. 640 ET).

*   **¿Qué otros costos o consecuencias podría tener la presentación extemporánea?**
    *   Cobertura pendiente para esta sub-pregunta.

### Ruta sugerida

1.  **Calcular la sanción inicial:** Determinar el valor de la sanción por extemporaneidad, que es el 5% del impuesto a cargo por cada mes o fracción de mes de retardo, sin exceder el 100% del impuesto (art. 641 ET). Si no hay impuesto a cargo, la sanción mínima es de 10 UVT (art. 639 ET).
2.  **Evaluar la reducción de la sanción:** Verificar si aplica alguna de las reducciones del artículo 640 ET, dependiendo del momento en que se presente la declaración.
3.  **Presentar la declaración y pagar la sanción:** Realizar la presentación de la declaración de renta y el pago de la sanción correspondiente.

### Riesgos y condiciones

*   **Riesgo de mayor sanción:** Si la DIAN inicia un proceso de fiscalización antes de la presentación de la declaración, la sanción podría ser mayor y las posibilidades de reducción se limitan (art. 640 ET).
*   **Intereses de mora:** Aunque no haya impuesto a cargo, si la declaración se presenta extemporáneamente y posteriormente se determina un impuesto a cargo, se generarán intereses de mora desde la fecha de vencimiento original (art. 634 ET).
*   **Riesgo de no deducibilidad:** La presentación extemporánea de declaraciones tributarias puede afectar la deducibilidad de algunos costos y gastos en periodos futuros, aunque la cobertura quedó parcial.

### Soportes clave

*   Estatuto Tributario, específicamente los artículos 634, 639, 640 y 641.

**Citations (verbatim):**

  1. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_09_Libro1_T1_Caps8a11.md'
  2. (no label) — doc_id='CORE_ya_Arriba_RENTA_LOGGRO_seccion-26-fiscalizacion-y-defensa-ante-la-dian.md'
  3. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_01_Libro1_T1_Sujetos_Pasivos.md'
  4. (no label) — doc_id='CORE_ya_Arriba_LEYES_INVERSIONES_INCENTIVOS_consolidado_Ley-1429-2010.md'

---

### regimen_sancionatorio_extemporaneidad_P2

- **Class:** 🔴 refused
- **answer_mode:** `topic_safety_abstention`
- **effective_topic:** `regimen_sancionatorio_extemporaneidad` (expected `regimen_sancionatorio_extemporaneidad`)
- **fallback_reason:** `pipeline_d_coherence_chunks_off_topic`
- **citations:** 0
- **answer length:** 294 chars
- **latency:** 7655 ms

**Question:**

> Un cliente persona natural se le pasó el plazo y va a presentar la renta del 2024 dos meses tarde. El impuesto a cargo le da $4.500.000. ¿Cuánto le toca pagar de sanción más intereses, y le puedo aplicar alguna reducción si es la primera vez que esto le pasa?

**Answer (verbatim):**

No pude ubicar evidencia del tema **regimen_sancionatorio_extemporaneidad** en el grafo. Los documentos de apoyo recuperados pertenecen al tema **precios_de_transferencia**; prefiero no responder con evidencia cruzada. Reformula la consulta o confirma si necesitas orientación de ese otro tema.

---

### regimen_sancionatorio_extemporaneidad_P3

- **Class:** 🟡 served_acceptable
- **answer_mode:** `graph_native_partial`
- **effective_topic:** `regimen_sancionatorio_extemporaneidad` (expected `regimen_sancionatorio_extemporaneidad`)
- **fallback_reason:** `pipeline_d_no_graph_primary_articles`
- **citations:** 7
- **answer length:** 905 chars
- **latency:** 13768 ms

**Question:**

> Le presenté a un cliente la declaración a tiempo. Tres meses después detectamos que se nos olvidó incluir una venta importante de $80 millones. La DIAN no ha mandado nada. Si corrijo voluntariamente subiendo el impuesto, ¿la sanción es del 10% o me alcanza alguna reducción adicional? ¿Y comparado con esperar a que la DIAN lo encuentre y me cobre inexactitud, qué tan grande es la diferencia en plata?

**Answer (verbatim):**

**Respuestas directas**
- **¿la sanción es del 10% o me alcanza alguna reducción adicional?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.
- **¿Y comparado con esperar a que la DIAN lo encuentre y me cobre inexactitud, qué tan grande es la diferencia en plata?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

**Ruta sugerida**
1. Haz una revisión operativa del soporte antes de defenderlo fiscalmente.
2. Verifica si el emisor estaba obligado a facturar electrónicamente y si hubo contingencia válida antes de aceptar el soporte.

**Riesgos y condiciones**
- No sustituyas la factura electrónica por cualquier soporte cuando la obligación sí existía (art. 808 ET).
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

**Citations (verbatim):**

  1. (no label) — doc_id='CORE_ya_Arriba_LEYES_INVERSIONES_INCENTIVOS_consolidado_Ley-1429-2010.md'
  2. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_09_Libro1_T1_Caps8a11.md'
  3. (no label) — doc_id='suin_1132325'
  4. (no label) — doc_id='suin_1104445'
  5. (no label) — doc_id='suin_30019323'
  6. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_20_Libro6_GMF.md'
  7. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_18_Libro5_Procedimiento_P1.md'

---

## descuentos_tributarios_renta

### descuentos_tributarios_renta_P1

- **Class:** 🔴 refused
- **answer_mode:** `topic_safety_abstention`
- **effective_topic:** `descuentos_tributarios_renta` (expected `descuentos_tributarios_renta`)
- **fallback_reason:** `pipeline_d_coherence_chunks_off_topic`
- **citations:** 0
- **answer length:** 285 chars
- **latency:** 8069 ms

**Question:**

> Si una PYME compra una máquina nueva para su producción este año, ¿qué puede hacer con el IVA que pagó en esa compra a nivel del impuesto de renta?

**Answer (verbatim):**

No pude ubicar evidencia del tema **descuentos_tributarios_renta** en el grafo. Los documentos de apoyo recuperados pertenecen al tema **precios_de_transferencia**; prefiero no responder con evidencia cruzada. Reformula la consulta o confirma si necesitas orientación de ese otro tema.

---

### descuentos_tributarios_renta_P2

- **Class:** 🔵 served_off_topic
- **answer_mode:** `graph_native`
- **effective_topic:** `iva` (expected `descuentos_tributarios_renta`)
- **fallback_reason:** `None`
- **citations:** 4
- **answer length:** 2371 chars
- **latency:** 16432 ms

**Question:**

> Mi cliente tiene una panadería SAS, compró un horno industrial en 2025 por $120 millones más IVA del 19%. Quiere saber si puede tomar todo el IVA como descuento en la declaración de este año o si tiene que repartirlo. ¿Qué pasa si el descuento le queda más grande que el impuesto a cargo?

**Answer (verbatim):**

### Respuestas directas

*   **¿Puede tomar todo el IVA como descuento en la declaración de este año o tiene que repartirlo?**
    *   El IVA pagado en la adquisición de activos fijos productivos, como el horno industrial, se puede tratar como descuento tributario en el impuesto sobre la renta (art. 258-1 ET).
    *   Este descuento se aplica en el año gravable en que se adquiere el activo. No se reparte.
    *   El valor del IVA susceptible de descuento es el 19% de $120 millones, es decir, $22.8 millones.

*   **¿Qué pasa si el descuento le queda más grande que el impuesto a cargo?**
    *   Si el descuento del IVA excede el impuesto sobre la renta a cargo, el excedente se puede solicitar como devolución o compensación (art. 258-1 ET).
    *   Alternativamente, el contribuyente puede optar por imputar el saldo a las declaraciones de renta de los periodos gravables siguientes.

### Ruta sugerida

1.  **Verificar la naturaleza del activo:** Confirmar que el horno industrial califica como activo fijo real productivo. Esto es clave para la aplicación del descuento (art. 258-1 ET).
2.  **Cálculo del descuento:** Determinar el valor exacto del IVA pagado ($22.8 millones).
3.  **Aplicación en la declaración de renta:** Incluir el valor del IVA como descuento tributario en la declaración de renta del año gravable 2025.
4.  **Gestión del excedente:** Si aplica, decidir si se solicita la devolución/compensación del excedente o se imputa a periodos futuros.

### Riesgos y condiciones

*   **Calificación del activo:** El principal riesgo es que la DIAN no considere el horno como un activo fijo real productivo. Esto invalidaría el descuento. Es fundamental que el activo esté directamente relacionado con la actividad productora de renta de la panadería.
*   **Limitación del descuento:** El descuento tributario por IVA en activos fijos productivos no puede exceder el impuesto sobre la renta a cargo del contribuyente (art. 258-1 ET). Cualquier excedente se gestiona vía devolución/compensación o imputación.

### Soportes clave

*   **Factura de compra:** Debe detallar el valor del horno y el IVA discriminado.
*   **Certificación de contador/revisor fiscal:** Que acredite la naturaleza del activo como fijo real productivo y su uso en la actividad generadora de renta.
*   **Declaración de Renta y Complementarios:** Donde se aplicará el descuento.

**Citations (verbatim):**

  1. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_16_Libro3_IVA.md'
  2. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_09_Libro1_T1_Caps8a11.md'
  3. (no label) — doc_id='CORE_ya_Arriba_LEYES_INVERSIONES_INCENTIVOS_consolidado_Ley-1429-2010.md'
  4. (no label) — doc_id='suin_1132325'

---

### descuentos_tributarios_renta_P3

- **Class:** 🟢 served_strong
- **answer_mode:** `graph_native`
- **effective_topic:** `descuentos_tributarios_renta` (expected `descuentos_tributarios_renta`)
- **fallback_reason:** `None`
- **citations:** 6
- **answer length:** 3216 chars
- **latency:** 21298 ms

**Question:**

> Un cliente hizo donaciones a una fundación calificada en el RTE por $20 millones, además compró maquinaria con IVA de $30 millones, e invirtió $50 millones en un proyecto de innovación calificado por el CNBT. Su impuesto a cargo es de $200 millones. ¿Cómo manejo los topes? Entiendo que el del 25% del artículo 258 aplica para algunos pero no para todos, y no tengo claro cuáles entran y cuáles no.

**Answer (verbatim):**

**Respuestas directas**
- **Un cliente hizo donaciones a una fundación calificada en el RTE por $20 millones, además compró maquinaria con IVA de $30 millones, e invirtió $50 millones en un proyecto de innovación calificado por el CNBT. Su impuesto a cargo es de $200 millones. ¿Cómo manejo los topes?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.
- **Entiendo que el del 25% del artículo 258 aplica para algunos pero no para todos, y no tengo claro cuáles entran y cuáles no?**
  - El límite del 25% del impuesto a cargo (art. 258 ET) aplica para los descuentos tributarios de los artículos 255, 256 y 257 del Estatuto Tributario.
  - El descuento por donaciones a entidades del Régimen Tributario Especial (RTE) no está sujeto al límite del 25% del impuesto a cargo del (art. 258 ET).
  - El descuento por IVA pagado en la adquisición de activos fijos productivos no está sujeto al límite del 25% del impuesto a cargo del (art. 258 ET).
  - El descuento por inversiones en investigación, desarrollo tecnológico o innovación (art. 256 ET) sí está sujeto al límite del 25% del impuesto a cargo del (art. 258 ET).

**Ruta sugerida**
1.  Calcula el impuesto a cargo del contribuyente: $200 millones.
2.  Determina el límite del 25% del impuesto a cargo para los descuentos aplicables (art. 258 ET): $200 millones * 25% = $50 millones.
3.  Identifica los descuentos que no están sujetos al límite del 25%:
    *   Donaciones a entidades del RTE: $20 millones.
    *   IVA pagado en la adquisición de maquinaria: $30 millones.
4.  Identifica los descuentos sujetos al límite del 25%:
    *   Inversión en proyecto de innovación calificado por el CNBT (art. 256 ET): $50 millones.
5.  Aplica los descuentos sin límite:
    *   Donaciones: $20 millones.
    *   IVA maquinaria: $30 millones.
6.  Aplica el descuento por innovación, respetando el límite del 25% del impuesto a cargo. En este caso, el descuento de $50 millones por innovación coincide con el límite de $50 millones.
7.  Suma todos los descuentos aplicables para determinar el total de descuentos tributarios.

**Riesgos y condiciones**
*   Asegúrate de que la fundación a la que se hizo la donación esté debidamente calificada en el RTE y que la donación cumpla con los requisitos formales para su deducibilidad y descuento.
*   Verifica que la maquinaria adquirida sea un activo fijo productivo y que el IVA pagado cumpla con las condiciones para ser tratado como descuento.
*   Confirma que el proyecto de innovación esté calificado por el CNBT y que la inversión cumpla con los requisitos del (art. 256 ET) para acceder al descuento.
*   El límite del 25% del impuesto a cargo es un tope máximo. Si la suma de los descuentos de los (arts. 255, 256 y 257 ET) excede este porcentaje, solo se podrá tomar hasta el límite.

**Soportes clave**
*   Certificado de la fundación que acredite su calificación en el RTE y el valor de la donación recibida.
*   Facturas de compra de la maquinaria que soporten el IVA pagado.
*   Certificado del CNBT que acredite la calificación del proyecto de innovación y el valor de la inversión.
*   Declaración de renta del periodo para verificar el impuesto a cargo.

**Citations (verbatim):**

  1. (no label) — doc_id='suin_1132325'
  2. (no label) — doc_id='CORE_ya_Arriba_LEYES_INVERSIONES_INCENTIVOS_consolidado_Ley-1429-2010.md'
  3. (no label) — doc_id='suin_1104445'
  4. (no label) — doc_id='suin_30019323'
  5. (no label) — doc_id='suin_1635955'
  6. (no label) — doc_id='suin_1874133'

---

## tarifas_renta_y_ttd

### tarifas_renta_y_ttd_P1

- **Class:** 🔴 refused
- **answer_mode:** `topic_safety_abstention`
- **effective_topic:** `tarifas_renta_y_ttd` (expected `tarifas_renta_y_ttd`)
- **fallback_reason:** `pipeline_d_coherence_zero_evidence_for_router_topic`
- **citations:** 0
- **answer length:** 170 chars
- **latency:** 7484 ms

**Question:**

> ¿Cuál es la tarifa general de renta para una SAS en Colombia para el año gravable 2025?

**Answer (verbatim):**

Evidencia insuficiente para responder con respaldo normativo en el tema **tarifas_renta_y_ttd**. Reformula la consulta o revisa manualmente antes de responder al cliente.

---

### tarifas_renta_y_ttd_P2

- **Class:** 🔴 refused
- **answer_mode:** `topic_safety_abstention`
- **effective_topic:** `tarifas_renta_y_ttd` (expected `tarifas_renta_y_ttd`)
- **fallback_reason:** `pipeline_d_coherence_chunks_off_topic`
- **citations:** 0
- **answer length:** 276 chars
- **latency:** 7797 ms

**Question:**

> Una SAS de mi cliente factura $4.500 millones, tiene utilidad contable antes de impuestos de $800 millones y renta líquida gravable de $400 millones. Le da impuesto de $140 millones al 35%. Pero me preocupa la TTD porque su tasa efectiva sobre la utilidad contable da apenas 11%. ¿Tengo que liquidar Impuesto a Adicionar y cómo lo calculo?

**Answer (verbatim):**

No pude ubicar evidencia del tema **tarifas_renta_y_ttd** en el grafo. Los documentos de apoyo recuperados pertenecen al tema **precios_de_transferencia**; prefiero no responder con evidencia cruzada. Reformula la consulta o confirma si necesitas orientación de ese otro tema.

---

### tarifas_renta_y_ttd_P3

- **Class:** 🔴 refused
- **answer_mode:** `topic_safety_abstention`
- **effective_topic:** `tarifas_renta_y_ttd` (expected `tarifas_renta_y_ttd`)
- **fallback_reason:** `pipeline_d_coherence_chunks_off_topic`
- **citations:** 0
- **answer length:** 276 chars
- **latency:** 8851 ms

**Question:**

> Tengo un cliente hotel pequeño ubicado en un municipio de 80 mil habitantes que abrió en 2023. Le vienen vendiendo la idea de que tiene tarifa preferencial del 9% o 15%. ¿Cuál de las dos aplica realmente, qué requisitos tiene que cumplir, y queda excluido del cálculo de la TTD?

**Answer (verbatim):**

No pude ubicar evidencia del tema **tarifas_renta_y_ttd** en el grafo. Los documentos de apoyo recuperados pertenecen al tema **precios_de_transferencia**; prefiero no responder con evidencia cruzada. Reformula la consulta o confirma si necesitas orientación de ese otro tema.

---

## dividendos_y_distribucion_utilidades

### dividendos_y_distribucion_utilidades_P1

- **Class:** 🟡 served_acceptable
- **answer_mode:** `graph_native_partial`
- **effective_topic:** `dividendos_y_distribucion_utilidades` (expected `dividendos_y_distribucion_utilidades`)
- **fallback_reason:** `pipeline_d_no_graph_primary_articles`
- **citations:** 4
- **answer length:** 1549 chars
- **latency:** 9319 ms

**Question:**

> Cuando una SAS reparte dividendos a su socio persona natural residente, ¿desde qué monto le empiezan a cobrar impuesto sobre los dividendos no gravados?

**Answer (verbatim):**

**Respuestas directas**

*   **¿Desde qué monto le empiezan a cobrar impuesto sobre los dividendos no gravados a una persona natural residente?**
    *   Los dividendos no gravados distribuidos a personas naturales residentes están sujetos a una tarifa del 10% sobre el monto que exceda las 1.090 UVT (art. 242 ET). Para 2024, este umbral es de $48.210.000 (1.090 UVT \* $44.769).

**Ruta sugerida**

1.  **Determinar la naturaleza del dividendo:**
    *   Identificar si el dividendo proviene de utilidades gravadas o no gravadas a nivel de la sociedad (art. 48 ET).
    *   Para dividendos no gravados, verificar que la sociedad haya cumplido con los requisitos de depuración de utilidades.
2.  **Calcular el monto sujeto a retención:**
    *   Restar el umbral de 1.090 UVT al valor total de los dividendos no gravados recibidos por la persona natural residente.
    *   Aplicar la tarifa del 10% al excedente (art. 242 ET).
3.  **Aplicar la retención en la fuente:**
    *   La sociedad que distribuye los dividendos debe practicar la retención en la fuente correspondiente.

**Riesgos y condiciones**

*   La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

**Soportes clave**

*   **Estatuto Tributario (ET):**
    *   Art. 48 ET: "Dividendos y participaciones no gravados".
    *   Art. 242 ET: "Tarifa especial para dividendos y participaciones recibidos por personas naturales residentes".
*   **Unidad de Valor Tributario (UVT):** Valor anual establecido por la DIAN.

**Citations (verbatim):**

  1. (no label) — doc_id='CORE_ya_Arriba_Documents_to_branch_and_improve_Tributacion_Dividendos_Practica_LOGGRO_div_practica_dividendos.md'
  2. (no label) — doc_id='CORE_ya_Arriba_Documents_to_branch_and_improve_Tributacion_Dividendos_Normativa_Base_div_normativa_dividendos.md'
  3. (no label) — doc_id='CORE_ya_Arriba_LEYES_INVERSIONES_INCENTIVOS_consolidado_Ley-1429-2010.md'
  4. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_09_Libro1_T1_Caps8a11.md'

---

### dividendos_y_distribucion_utilidades_P2

- **Class:** 🟢 served_strong
- **answer_mode:** `graph_native`
- **effective_topic:** `dividendos_y_distribucion_utilidades` (expected `dividendos_y_distribucion_utilidades`)
- **fallback_reason:** `None`
- **citations:** 8
- **answer length:** 3049 chars
- **latency:** 25199 ms

**Question:**

> Mi cliente es socio único de una SAS que cerró 2025 con utilidad contable de $300 millones y pagó impuesto de renta de $80 millones. Quiere repartirse $200 millones en 2026 como dividendos. ¿Cuánto de eso le queda como no gravado y cuánto va a pagar el socio cuando lo declare en su renta personal? ¿La SAS le tiene que practicar retención al momento de pagar?

**Answer (verbatim):**

**Respuestas directas**
- **¿Cuánto de eso le queda como no gravado y cuánto va a pagar el socio cuando lo declare en su renta personal?**
  - La utilidad contable de $300 millones y el impuesto de renta pagado de $80 millones resultan en una utilidad líquida de $220 millones ($300M - $80M).
  - De los $200 millones que el socio desea repartir, el monto no gravado se calcula con la siguiente fórmula:
    $$ \text{Dividendo no gravado} = \text{Dividendo total} \times \frac{\text{Utilidad líquida después de impuestos}}{\text{Utilidad contable antes de impuestos}} $$
    $$ \text{Dividendo no gravado} = \$200 \text{M} \times \frac{\$220 \text{M}}{\$300 \text{M}} = \$146.67 \text{M} $$
  - El dividendo gravado sería la diferencia: $\$200 \text{M} - \$146.67 \text{M} = \$53.33 \text{M}$.
  - El socio deberá incluir los $53.33 millones como ingreso gravado en su declaración de renta personal. La tarifa aplicable dependerá de su tabla de ingresos y demás deducciones.
- **¿La SAS le tiene que practicar retención al momento de pagar?**
  - Sí, la SAS debe practicar retención en la fuente sobre la porción gravada de los dividendos al momento del pago o abono en cuenta (art. 366-1 ET).
  - La tarifa de retención aplicable a los dividendos gravados será del 10% para personas naturales residentes (Capítulos VIII-XI).
  - Retención a practicar: $\$53.33 \text{M} \times 10\% = \$5.33 \text{M}$.

**Ruta sugerida**
- **Cálculo de la porción gravada y no gravada:**
  - Confirmar la utilidad contable y el impuesto de renta de la SAS para el año 2025.
  - Aplicar la fórmula para determinar la proporción de dividendos gravados y no gravados.
- **Retención en la fuente:**
  - La SAS debe calcular y practicar la retención en la fuente sobre la porción gravada de los dividendos al momento del pago.
  - Expedir el certificado de retenciones al socio.
- **Declaración de renta del socio:**
  - El socio debe incluir la porción gravada de los dividendos en su declaración de renta personal del año gravable 2026.
  - La retención practicada por la SAS será un anticipo del impuesto de renta del socio.

**Riesgos y condiciones**
- **Riesgo de inexactitud en la declaración de renta de la SAS:** Si la utilidad contable o el impuesto de renta declarado por la SAS son ajustados por la DIAN, la proporción de dividendos gravados y no gravados podría variar, afectando la declaración del socio.
- **Cambios normativos:** Las tarifas de retención y la tributación de dividendos pueden ser modificadas por futuras reformas tributarias.
- **Residencia fiscal del socio:** La tarifa de retención y el tratamiento en la declaración de renta personal pueden variar si el socio no es residente fiscal en Colombia.

**Soportes clave**
- Estados financieros de la SAS al 31 de diciembre de 2025.
- Declaración de renta de la SAS del año gravable 2025.
- Acta de la asamblea de accionistas donde se aprueba la distribución de dividendos.
- Comprobante de pago de los dividendos al socio.
- Certificado de retención en la fuente expedido por la SAS al socio.

**Citations (verbatim):**

  1. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_09_Libro1_T1_Caps8a11.md'
  2. (no label) — doc_id='CORE_ya_Arriba_RENTA_LOGGRO_seccion-26-fiscalizacion-y-defensa-ante-la-dian.md'
  3. (no label) — doc_id='CORE_ya_Arriba_RENTA_LOGGRO_seccion-09-costos-y-deducciones.md'
  4. (no label) — doc_id='CORE_ya_Arriba_LEYES_INVERSIONES_INCENTIVOS_consolidado_Ley-1429-2010.md'
  5. (no label) — doc_id='suin_1132325'
  6. (no label) — doc_id='suin_1104445'
  7. (no label) — doc_id='suin_30019323'
  8. (no label) — doc_id='suin_30036488'

---

### dividendos_y_distribucion_utilidades_P3

- **Class:** 🟡 served_acceptable
- **answer_mode:** `graph_native`
- **effective_topic:** `dividendos_y_distribucion_utilidades` (expected `dividendos_y_distribucion_utilidades`)
- **fallback_reason:** `None`
- **citations:** 7
- **answer length:** 1398 chars
- **latency:** 19975 ms

**Question:**

> A mi cliente persona jurídica le tocó liquidar Impuesto a Adicionar por TTD el año pasado. Para efectos del cálculo del artículo 49 y determinar cuántos dividendos puede repartir como no gravados, ¿el IA cuenta como impuesto pagado o no? Escuché que hubo una suspensión del Consejo de Estado sobre un concepto DIAN que decía algo de eso, y no tengo claro cómo está la cosa hoy.

**Answer (verbatim):**

**Respuestas directas**
- **A mi cliente persona jurídica le tocó liquidar Impuesto a Adicionar por TTD el año pasado. Para efectos del cálculo del artículo 49 y determinar cuántos dividendos puede repartir como no gravados, ¿el IA cuenta como impuesto pagado o no?**
  - Para determinar los dividendos no gravados según el (art. 49 ET), el Impuesto a Adicionar (IA) por TTD no se considera un impuesto pagado. El (art. 49 ET) establece la metodología para calcular la parte no gravada de los dividendos, y el IA no encaja en las categorías de impuestos que reducen la utilidad comercial para este fin.
- **Escuché que hubo una suspensión del Consejo de Estado sobre un concepto DIAN que decía algo de eso, y no tengo claro cómo está la cosa hoy?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

**Ruta sugerida**
1.  Para el cálculo de dividendos no gravados, aplica estrictamente la fórmula del (art. 49 ET), que considera la utilidad comercial menos el impuesto de renta y complementarios. El Impuesto a Adicionar no es parte de este cálculo.

**Recap histórico**
- Art. 49 ET: la última modificación relevante detectada en esta ruta es Ley 1607 de 2012.
- Art. 100 ET: la última modificación relevante detectada en esta ruta es Ley 1607 de 2012.
- Art. 101 ET: la última modificación relevante detectada en esta ruta es Ley 1607 de 2012.

**Citations (verbatim):**

  1. (no label) — doc_id='suin_1635955'
  2. (no label) — doc_id='suin_30031794'
  3. (no label) — doc_id='suin_30055086'
  4. (no label) — doc_id='suin_1132325'
  5. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_02_Libro1_T1_Cap1_Ingresos.md'
  6. (no label) — doc_id='CORE_ya_Arriba_LEYES_INVERSIONES_INCENTIVOS_consolidado_Ley-1429-2010.md'
  7. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_20_Libro6_GMF.md'

---

## devoluciones_saldos_a_favor

### devoluciones_saldos_a_favor_P1

- **Class:** 🟢 served_strong
- **answer_mode:** `graph_native`
- **effective_topic:** `devoluciones_saldos_a_favor` (expected `devoluciones_saldos_a_favor`)
- **fallback_reason:** `None`
- **citations:** 4
- **answer length:** 2372 chars
- **latency:** 15395 ms

**Question:**

> ¿Cuánto tiempo tiene la DIAN para resolver una solicitud de devolución de saldo a favor en renta cuando la pides sin garantía?

**Answer (verbatim):**

**Respuestas directas**

*   **¿Cuánto tiempo tiene la DIAN para resolver una solicitud de devolución de saldo a favor en renta cuando la pides sin garantía?**
    *   La DIAN tiene 50 días hábiles para resolver la solicitud de devolución de saldos a favor (art. 850 ET). Este término aplica para solicitudes sin garantía.
    *   Si la solicitud se presenta con garantía, el término se reduce a 20 días hábiles (art. 850 ET).
    *   En caso de contribuyentes que cumplan con los requisitos para el régimen especial de devoluciones automáticas, el término es de 30 días hábiles (art. 850 ET).
    *   La cobertura quedó parcial.

**Ruta sugerida**
1.  Enfoca el caso como una solicitud de devolución o compensación de saldo a favor, no como un problema de facturación electrónica (arts. 589 y 850 ET).
2.  Antes de radicar, verifica la declaración que origina el saldo a favor y asegura la coherencia de soportes, anexos y datos del contribuyente (arts. 589 y 850 ET).
3.  Confirma que el saldo a favor esté correctamente determinado en la declaración base antes de proceder con la solicitud de devolución (arts. 589 y 850 ET).
4.  Si el expediente está completo, considera los términos de 50, 30 o 20 días hábiles como referencia operativa, según el tipo de solicitud y los soportes presentados (arts. 850 y 589 ET).

**Riesgos y condiciones**
*   Evita radicar solicitudes con cifras o soportes inconsistentes, ya que esto puede generar inadmisibilidades o revisiones posteriores (arts. 850 y 589 ET).
*   No tramites una devolución si la declaración aún presenta inconsistencias o requiere corrección (arts. 850 y 589 ET).
*   Ten presente que una corrección que aumente el saldo a favor reinicia el término de revisión de la DIAN desde la fecha de la corrección (arts. 850 y 589 ET).
*   El cumplimiento del cliente en facturación electrónica es una condición complementaria, pero no altera la naturaleza ni los requisitos del trámite de devolución (arts. 850 y 589 ET).

**Soportes clave**
| Tipo de Solicitud | Término de Resolución (Días Hábiles) | Base Legal |
| :---------------- | :------------------------------------ | :--------- |
| Sin garantía      | 50                                    | Art. 850 ET |
| Con garantía      | 20                                    | Art. 850 ET |
| Régimen especial  | 30                                    | Art. 850 ET |

**Citations (verbatim):**

  1. (no label) — doc_id='CORE_ya_Arriba_NUEVOS-DATOS-BRECHAS-MARZO-2026_07-DEVOLUCIONES-SALDOS-A-FAVOR_NORMATIVA_N-DEV-devoluciones-saldos-a-favor.md'
  2. (no label) — doc_id='suin_1132325'
  3. (no label) — doc_id='CORE_ya_Arriba_IVA_COMPLETO_NORMATIVA_IVA-N02-IVA-descontable-proporcionalidad-saldos-favor.md'
  4. (no label) — doc_id='CORE_ya_Arriba_Documents_to_branch_and_improve_Devoluciones_Saldos_Favor_Normativa_Base_dev_normativa_devoluciones.md'

---

### devoluciones_saldos_a_favor_P2

- **Class:** 🟢 served_strong
- **answer_mode:** `graph_native`
- **effective_topic:** `devoluciones_saldos_a_favor` (expected `devoluciones_saldos_a_favor`)
- **fallback_reason:** `None`
- **citations:** 7
- **answer length:** 1608 chars
- **latency:** 15618 ms

**Question:**

> Mi cliente, una SAS exportadora, cerró 2025 con un saldo a favor en renta de $180 millones por exceso de retenciones. Le presenté la declaración la semana pasada y necesita la plata cuanto antes para capital de trabajo. ¿Le conviene meter garantía bancaria para acelerar la devolución? ¿Y si no, le devuelven en plata o en TIDIS?

**Answer (verbatim):**

**Respuestas directas**
- **¿Le conviene meter garantía bancaria para acelerar la devolución?**
  - La decisión de presentar garantía bancaria para acelerar la devolución debe evaluarse en el contexto de un trámite de devolución o compensación de saldo a favor, no como un asunto de facturación electrónica.
  - El cumplimiento del cliente en facturación electrónica es una condición complementaria, pero no altera la naturaleza del proceso de devolución.
  - Si el cliente tiene obligaciones tributarias pendientes, se debe comparar la opción de devolución con la de compensación, según el (art. 815 ET), antes de definir la estrategia de flujo de caja.
- **¿Y si no, le devuelven en plata o en TIDIS?**
  - Cobertura pendiente para esta sub-pregunta; se requiere validar el expediente antes de dar una respuesta definitiva al cliente.

**Ruta sugerida**
1. Enfoque el caso como un proceso de devolución o compensación de saldo a favor, no como un problema de facturación electrónica (arts. 555 y 555-1 ET).
2. Recuerde que los contribuyentes pueden actuar ante la Administración Tributaria directamente o a través de sus representantes o apoderados (arts. 555 y 555-1 ET).

**Riesgos y condiciones**
- El cumplimiento del cliente en facturación electrónica es una condición complementaria, pero no modifica la naturaleza del trámite de devolución (arts. 555 y 555-1 ET).

**Soportes clave**
| Tipo de Soporte | Descripción |
|---|---|
| Normativa | LIBRO SÉPTIMO — Devoluciones, Compensaciones y Saldos a Favor (Arts. 815–865) |
| Práctica | Devoluciones y Saldos a Favor — Guía Práctica para el Contador |

**Citations (verbatim):**

  1. (no label) — doc_id='CORE_ya_Arriba_NUEVOS-DATOS-BRECHAS-MARZO-2026_07-DEVOLUCIONES-SALDOS-A-FAVOR_NORMATIVA_N-DEV-devoluciones-saldos-a-favor.md'
  2. (no label) — doc_id='CORE_ya_Arriba_Documents_to_branch_and_improve_Devoluciones_Saldos_Favor_Practica_LOGGRO_dev_practica_devoluciones.md'
  3. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_18_Libro5_Procedimiento_P1.md'
  4. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_19_Libro5_Procedimiento_P2.md'
  5. (no label) — doc_id='CORE_ya_Arriba_DEVOLUCIONES_SALDOS_FAVOR_LOGGRO_DEV-L01-guia-practica-devoluciones-saldos-favor-cross-impuesto.md'
  6. (no label) — doc_id='CORE_ya_Arriba_LEYES_INVERSIONES_INCENTIVOS_consolidado_Ley-1429-2010.md'
  7. (no label) — doc_id='suin_1132325'

---

### devoluciones_saldos_a_favor_P3

- **Class:** 🟢 served_strong
- **answer_mode:** `graph_native`
- **effective_topic:** `devoluciones_saldos_a_favor` (expected `devoluciones_saldos_a_favor`)
- **fallback_reason:** `None`
- **citations:** 7
- **answer length:** 2281 chars
- **latency:** 19834 ms

**Question:**

> Una SAS presentó la declaración del 2025 con beneficio de auditoría incremento del 36% (firmeza a 6 meses) y saldo a favor de $50 millones. El gerente está ocupado y dice que tramita la devolución "más adelante en el año". ¿Hasta cuándo puede esperar para pedirla? ¿Le aplica el plazo general de 2 años o algo distinto por estar bajo beneficio de auditoría?

**Answer (verbatim):**

**Respuestas directas**
- **¿Hasta cuándo puede esperar para pedirla?**
  - El plazo para solicitar la devolución de saldos a favor es de dos años, contados a partir de la fecha de vencimiento del término para declarar o desde la fecha de presentación de la declaración, si fue extemporánea (art. 854 ET).
  - En este caso, la declaración del 2025 se presentó con beneficio de auditoría. La firmeza de la declaración se da a los 6 meses, pero esto no altera el plazo de dos años para solicitar la devolución del saldo a favor.
- **¿Le aplica el plazo general de 2 años o algo distinto por estar bajo beneficio de auditoría?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

**Ruta sugerida**
1.  **Verificar firmeza de la declaración:** Aunque el beneficio de auditoría reduce el término de firmeza a 6 meses, es crucial confirmar que la declaración del 2025 ya está en firme. Esto asegura que no hay riesgo de modificaciones por parte de la DIAN que afecten el saldo a favor.
2.  **Preparar solicitud de devolución:** Recopilar todos los soportes necesarios para la solicitud de devolución, incluyendo la declaración de renta, certificados de retención en la fuente, y cualquier otro documento que respalde el saldo a favor.
3.  **Presentar solicitud:** Radicar la solicitud de devolución ante la DIAN dentro del plazo de dos años.

**Riesgos y condiciones**
*   **Vencimiento del plazo:** El principal riesgo es que el gerente posponga la solicitud más allá de los dos años, perdiendo el derecho a la devolución del saldo a favor (art. 854 ET).
*   **Requerimientos de la DIAN:** La DIAN puede solicitar información adicional o realizar una auditoría previa a la devolución. Es importante tener todos los soportes listos para responder a estos requerimientos.
*   **Compensación de oficio:** Si la SAS tiene deudas pendientes con la DIAN, el saldo a favor podría ser compensado de oficio, total o parcialmente.

**Soportes clave**
*   Copia de la declaración de renta del año gravable 2025.
*   Certificados de retención en la fuente que soporten el saldo a favor.
*   Extractos bancarios y registros contables que evidencien los pagos y retenciones.
*   Cualquier otro documento que justifique el origen del saldo a favor.

**Citations (verbatim):**

  1. (no label) — doc_id='suin_30054528'
  2. (no label) — doc_id='CORE_ya_Arriba_LEYES_INVERSIONES_INCENTIVOS_consolidado_Ley-1429-2010.md'
  3. (no label) — doc_id='CORE_ya_Arriba_NUEVOS-DATOS-BRECHAS-MARZO-2026_09-OBLIGACIONES-PROFESIONALES-JCC_NORMATIVA_N-JCC-obligaciones-profesionales-contador.md'
  4. (no label) — doc_id='suin_1132325'
  5. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_09_Libro1_T1_Caps8a11.md'
  6. (no label) — doc_id='CORE_ya_Arriba_RENTA_LOGGRO_seccion-26-fiscalizacion-y-defensa-ante-la-dian.md'
  7. (no label) — doc_id='suin_1104445'

---

## perdidas_fiscales_art147

### perdidas_fiscales_art147_P1

- **Class:** 🔴 refused
- **answer_mode:** `topic_safety_abstention`
- **effective_topic:** `perdidas_fiscales_art147` (expected `perdidas_fiscales_art147`)
- **fallback_reason:** `pipeline_d_coherence_zero_evidence_for_router_topic`
- **citations:** 0
- **answer length:** 175 chars
- **latency:** 7640 ms

**Question:**

> ¿Cuántos años hacia adelante puedo arrastrar una pérdida fiscal generada por una SAS para compensarla con utilidades futuras?

**Answer (verbatim):**

Evidencia insuficiente para responder con respaldo normativo en el tema **perdidas_fiscales_art147**. Reformula la consulta o revisa manualmente antes de responder al cliente.

---

### perdidas_fiscales_art147_P2

- **Class:** 🟡 served_acceptable
- **answer_mode:** `graph_native_partial`
- **effective_topic:** `perdidas_fiscales_art147` (expected `perdidas_fiscales_art147`)
- **fallback_reason:** `pipeline_d_no_graph_primary_articles`
- **citations:** 5
- **answer length:** 1447 chars
- **latency:** 11315 ms

**Question:**

> Mi cliente tiene pérdidas acumuladas de $400 millones generadas en 2020, 2021 y 2022. En 2025 finalmente tuvo utilidad fiscal de $250 millones. ¿Puedo compensarle todo o hay algún límite porcentual anual? ¿Y debo compensar primero las más antiguas?

**Answer (verbatim):**

**Respuestas directas**
- **¿Puedo compensarle todo o hay algún límite porcentual anual?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.
- **¿Y debo compensar primero las más antiguas?**
  - Las sociedades pueden compensar las pérdidas fiscales con las rentas líquidas ordinarias que obtengan en los doce (12) períodos gravables siguientes (art. 147 ET).

**Ruta sugerida**
1. La regla general del art. 147 ET establece que la sociedad compensa las pérdidas fiscales contra rentas líquidas ordinarias futuras. Estas pérdidas no se trasladan a los socios ni se tratan como un saldo a favor.
2. Las sociedades pueden compensar las pérdidas fiscales con las rentas líquidas ordinarias que obtengan en los doce (12) períodos gravables siguientes (art. 147 ET).
3. En cuanto a la firmeza, es un tema distinto a la mecánica de compensación. El término de revisión de la declaración que origina la pérdida fiscal debe medirse aparte (art. 147 ET).

**Riesgos y condiciones**
- No confundas la compensación de pérdidas fiscales en renta con la devolución o compensación de saldos a favor (art. 147 ET).
- El término de firmeza para declaraciones que originen o compensen pérdidas fiscales no es el ordinario de 3 años; en estos casos, el término es de 6 años (art. 147 ET).
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

**Citations (verbatim):**

  1. (no label) — doc_id='CORE_ya_Arriba_LEYES_INVERSIONES_INCENTIVOS_consolidado_Ley-1429-2010.md'
  2. (no label) — doc_id='suin_1132325'
  3. (no label) — doc_id='CORE_ya_Arriba_RENTA_LOGGRO_seccion-12-determinacion-renta-liquida-gravable.md'
  4. (no label) — doc_id='suin_1104445'
  5. (no label) — doc_id='suin_30019323'

---

### perdidas_fiscales_art147_P3

- **Class:** 🟡 served_acceptable
- **answer_mode:** `graph_native_partial`
- **effective_topic:** `perdidas_fiscales_art147` (expected `perdidas_fiscales_art147`)
- **fallback_reason:** `pipeline_d_no_graph_primary_articles`
- **citations:** 6
- **answer length:** 1861 chars
- **latency:** 12400 ms

**Question:**

> Tengo un cliente que arrastra una pérdida del año 2014 que todavía no ha podido compensar. Adicional, en 2018 hubo una fusión donde mi cliente fue la sociedad absorbente. ¿Las pérdidas del 2014 sobreviven la fusión? ¿Y siguen siendo compensables hoy o ya se vencieron por el plazo? Hay reglas distintas para pérdidas pre-2017 y post-2017 y me genera dudas la transición.

**Answer (verbatim):**

**Respuestas directas**
- **¿Las pérdidas del 2014 sobreviven la fusión?**
  - La sociedad absorbente o resultante de un proceso de fusión puede compensar las pérdidas fiscales de la sociedad absorbida con las rentas líquidas ordinarias que obtenga (art. 147 ET).
  - La compensación de pérdidas fiscales se realiza contra rentas líquidas ordinarias futuras, no se trasladan a los socios ni se tratan como un saldo a favor (art. 147 ET).
  - El término de firmeza para declaraciones que originen o compensen pérdidas fiscales es de seis años, no el término ordinario de tres años (art. 147 ET).
- **¿Y siguen siendo compensables hoy o ya se vencieron por el plazo?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

**Ruta sugerida**
1. La sociedad absorbente puede compensar las pérdidas fiscales de la sociedad absorbida (art. 147 ET).
2. Las pérdidas fiscales se compensan con las rentas líquidas ordinarias obtenidas en los doce períodos gravables siguientes (art. 147 ET).
3. El término de firmeza para declaraciones que originen o compensen pérdidas es de seis años (art. 147 ET).

**Riesgos y condiciones**
- Es importante diferenciar la compensación de pérdidas fiscales en renta de la devolución o compensación de saldos a favor (art. 147 ET).
- El término de firmeza para declaraciones que originen o compensen pérdidas fiscales es de seis años, no el término ordinario de tres años (art. 147 ET).
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

**Soportes clave**
| Tipo de Soporte | Descripción |
|---|---|
| Normativa | DECRETO 624 DE 1989 - Colombia |
| Normativa | Ley 1429 de 2010 — Formalización y Generación de Empleo |
| Normativa | CODIGO SUSTANTIVO DEL TRABAJO - Colombia |
| Normativa | SUIN stub 1104445 |

**Citations (verbatim):**

  1. (no label) — doc_id='suin_1132325'
  2. (no label) — doc_id='CORE_ya_Arriba_LEYES_INVERSIONES_INCENTIVOS_consolidado_Ley-1429-2010.md'
  3. (no label) — doc_id='suin_30019323'
  4. (no label) — doc_id='suin_1104445'
  5. (no label) — doc_id='CORE_ya_Arriba_CALENDARIO_TRIBUTARIO_CONSOLIDADO_LOGGRO_CAL-L01-guia-practica-calendario-tributario-consolidado-2026.md'
  6. (no label) — doc_id='CORE_ya_Arriba_RENTA_EXPERTOS_T01-calendario-tributario-2026-interpretaciones.md'

---

## precios_de_transferencia

### precios_de_transferencia_P1

- **Class:** 🟢 served_strong
- **answer_mode:** `graph_native`
- **effective_topic:** `precios_de_transferencia` (expected `precios_de_transferencia`)
- **fallback_reason:** `None`
- **citations:** 5
- **answer length:** 3391 chars
- **latency:** 16438 ms

**Question:**

> ¿Cuáles son los umbrales de patrimonio o ingresos a partir de los cuales una empresa colombiana queda obligada al régimen de precios de transferencia?

**Answer (verbatim):**

Aquí tienes la revisión de tu borrador:

### Respuestas directas

*   **¿Cuáles son los umbrales de patrimonio o ingresos a partir de los cuales una empresa colombiana queda obligada al régimen de precios de transferencia?**

    La obligación de aplicar el régimen de precios de transferencia se activa para contribuyentes del impuesto sobre la renta y complementarios que realicen operaciones con vinculados económicos o partes relacionadas, y que cumplan con los siguientes umbrales:

    *   **Patrimonio Bruto:** Igual o superior a 100.000 UVT a 31 de diciembre del año gravable.
    *   **Ingresos Brutos:** Igual o superior a 61.000 UVT a 31 de diciembre del año gravable.

    Adicionalmente, si los ingresos brutos por operaciones con vinculados económicos o partes relacionadas superan las 30.000 UVT, también se genera la obligación.

    Es importante recordar que la UVT se ajusta anualmente. Para el año gravable 2023, la UVT es de $42.412.

    **Cobertura pendiente para esta sub-pregunta:** La evidencia disponible no permite determinar si existen otros criterios de vinculación o tipos de operaciones específicas que, independientemente de los umbrales de patrimonio o ingresos, activen la obligación.

*   **¿Qué tipo de operaciones se consideran dentro del régimen de precios de transferencia?**

    Cobertura pendiente para esta sub-pregunta.

*   **¿Cuáles son las sanciones por incumplimiento del régimen de precios de transferencia?**

    Cobertura pendiente para esta sub-pregunta.

### Ruta sugerida

1.  **Verificar Umbrales Anuales:** Confirmar los valores de UVT para el año gravable en cuestión y calcular los umbrales de patrimonio e ingresos brutos.
2.  **Identificar Operaciones con Vinculados:** Realizar un análisis detallado de todas las operaciones (compra/venta de bienes, servicios, préstamos, regalías, etc.) realizadas con vinculados económicos o partes relacionadas.
3.  **Determinar Vinculación Económica:** Establecer si las contrapartes de las operaciones cumplen con los criterios de vinculación económica definidos en la normativa tributaria.
4.  **Evaluar Obligación:** Con base en los umbrales y la identificación de operaciones con vinculados, determinar si la empresa está obligada a aplicar el régimen de precios de transferencia.

### Riesgos y condiciones

*   **Riesgo de Sanciones:** El incumplimiento de las obligaciones de precios de transferencia puede acarrear sanciones significativas por parte de la DIAN.
*   **Complejidad de la Determinación:** La identificación de vinculados económicos y la valoración de operaciones bajo el principio de plena competencia requiere un análisis técnico y especializado.
*   **Actualización Normativa:** La normativa de precios de transferencia puede sufrir modificaciones, por lo que es crucial mantenerse actualizado.

### Soportes clave

*   **Estatuto Tributario (ET):**
    *   (art. 118 ET)
    *   (art. 118-1 ET)
    *   (art. 12 ET)
    *   (art. 262 ET)
    *   (art. 8 ET)
    *   (art. 1 ET)
*   **Decreto 624 de 1989:** Contiene disposiciones relevantes para la aplicación del Estatuto Tributario.
*   **Ley 1429 de 2010:** Puede contener disposiciones que afecten la aplicación de ciertos regímenes tributarios.
*   **Capítulos VIII-XI del ET:** Descuentos Tributarios, Ganancias Ocasionales Exentas, Tarifas del Impuesto y Precios de Transferencia.

La cobertura quedó parcial.

**Citations (verbatim):**

  1. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_09_Libro1_T1_Caps8a11.md'
  2. (no label) — doc_id='CORE_ya_Arriba_LEYES_INVERSIONES_INCENTIVOS_consolidado_Ley-1429-2010.md'
  3. (no label) — doc_id='suin_1132325'
  4. (no label) — doc_id='suin_1104445'
  5. (no label) — doc_id='suin_30019323'

---

### precios_de_transferencia_P2

- **Class:** 🟡 served_acceptable
- **answer_mode:** `graph_native`
- **effective_topic:** `precios_de_transferencia` (expected `precios_de_transferencia`)
- **fallback_reason:** `None`
- **citations:** 6
- **answer length:** 668 chars
- **latency:** 19437 ms

**Question:**

> Mi cliente es una SAS de software con ingresos de $4.200 millones y patrimonio bruto de $1.800 millones. Le paga $250 millones al año a su empresa hermana en México (los mismos socios tienen el 70% allá) por servicios de desarrollo. ¿Está obligada a presentar declaración informativa, documentación comprobatoria o ambas? ¿Y qué plazos tiene para entregarlas?

**Answer (verbatim):**

**Respuestas directas**
- **¿Está obligada a presentar declaración informativa, documentación comprobatoria o ambas?**
  - SANCIONES RESPECTO DE LA DOCUMENTACIÓN COMPROBATORIA Y DE LA DECLARACIÓN INFORMATIVA.
- **¿Y qué plazos tiene para entregarlas?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

**Ruta sugerida**
1. Los contribuyentes pueden actuar ante la Administración Tributaria personalmente o por medio de sus representantes o apoderados (arts. 555 y 555-1 ET).

**Riesgos y condiciones**
- SANCIONES RESPECTO DE LA DOCUMENTACIÓN COMPROBATORIA Y DE LA DECLARACIÓN INFORMATIVA (arts. 260-11 y 555 ET).

**Citations (verbatim):**

  1. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_09_Libro1_T1_Caps8a11.md'
  2. (no label) — doc_id='CORE_ya_Arriba_LEYES_INVERSIONES_INCENTIVOS_consolidado_Ley-1429-2010.md'
  3. (no label) — doc_id='suin_1132325'
  4. (no label) — doc_id='suin_1104445'
  5. (no label) — doc_id='suin_30019323'
  6. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_18_Libro5_Procedimiento_P1.md'

---

### precios_de_transferencia_P3

- **Class:** 🔴 refused
- **answer_mode:** `topic_safety_abstention`
- **effective_topic:** `precios_de_transferencia` (expected `precios_de_transferencia`)
- **fallback_reason:** `pipeline_d_coherence_zero_evidence_for_router_topic`
- **citations:** 0
- **answer length:** 175 chars
- **latency:** 6430 ms

**Question:**

> Mi cliente, una PYME de $1.500 millones en ingresos, le compró mercancía durante 2025 a un proveedor en Hong Kong por $400 millones. Hasta donde tenía entendido Hong Kong era jurisdicción no cooperante y eso lo metía en precios de transferencia sin importar montos. ¿Sigue siendo así para la declaración que voy a presentar este año?

**Answer (verbatim):**

Evidencia insuficiente para responder con respaldo normativo en el tema **precios_de_transferencia**. Reformula la consulta o revisa manualmente antes de responder al cliente.

---

## impuesto_patrimonio_personas_naturales

### impuesto_patrimonio_personas_naturales_P1

- **Class:** 🔴 refused
- **answer_mode:** `topic_safety_abstention`
- **effective_topic:** `impuesto_patrimonio_personas_naturales` (expected `impuesto_patrimonio_personas_naturales`)
- **fallback_reason:** `pipeline_d_coherence_zero_evidence_for_router_topic`
- **citations:** 0
- **answer length:** 189 chars
- **latency:** 7892 ms

**Question:**

> ¿A partir de qué patrimonio una persona natural en Colombia tiene que pagar impuesto al patrimonio?

**Answer (verbatim):**

Evidencia insuficiente para responder con respaldo normativo en el tema **impuesto_patrimonio_personas_naturales**. Reformula la consulta o revisa manualmente antes de responder al cliente.

---

### impuesto_patrimonio_personas_naturales_P2

- **Class:** 🟡 served_acceptable
- **answer_mode:** `graph_native_partial`
- **effective_topic:** `impuesto_patrimonio_personas_naturales` (expected `impuesto_patrimonio_personas_naturales`)
- **fallback_reason:** `pipeline_d_no_graph_primary_articles`
- **citations:** 5
- **answer length:** 2206 chars
- **latency:** 13282 ms

**Question:**

> Mi cliente persona natural tiene a 1 de enero de 2026: una casa donde vive avaluada en $1.800 millones, un apartamento que arrienda valorado en $900 millones, acciones en su SAS por $1.500 millones, vehículos por $200 millones y efectivo en bancos por $150 millones. ¿Tiene que declarar y pagar impuesto al patrimonio? ¿Qué se le excluye y a qué tarifa?

**Answer (verbatim):**

**Respuestas directas**
- **¿Tiene que declarar y pagar impuesto al patrimonio?**
  - El cliente debe declarar y pagar el impuesto al patrimonio si su patrimonio líquido al 1 de enero de 2026 supera las 72.000 UVT.
  - Para el año gravable 2026, el valor de la UVT se determinará a finales de 2025. Tomando como referencia la UVT de 2024 ($47.065), el umbral sería de $3.388.680.000.
  - El patrimonio bruto del cliente es de $4.550 millones ($1.800M casa + $900M apartamento + $1.500M acciones + $200M vehículos + $150M efectivo).
  - Si no tiene pasivos, su patrimonio líquido supera el umbral, por lo que estaría obligado a declarar y pagar el impuesto.

- **¿Qué se le excluye y a qué tarifa?**
  - Se excluye del patrimonio bruto el valor patrimonial de la casa de habitación hasta 12.000 UVT (art. 295-1 ET).
  - Usando la UVT de 2024, el valor a excluir sería de $564.780.000.
  - La base gravable del impuesto al patrimonio se determina restando las exclusiones del patrimonio líquido.
  - Las tarifas aplicables al impuesto al patrimonio para personas naturales residentes son progresivas (art. 295-1 ET):

| Patrimonio Líquido (UVT) | Tarifa Marginal | Impuesto |
| :----------------------- | :-------------- | :------- |
| > 72.000 y <= 122.000    | 0.5%            | (Base gravable en UVT - 72.000 UVT) * 0.5% |
| > 122.000                | 1.0%            | (Base gravable en UVT - 122.000 UVT) * 1.0% + 250 UVT |

**Ruta sugerida**
- Determinar el valor exacto de la UVT para el año 2026 una vez sea publicada por la DIAN.
- Calcular el patrimonio líquido del cliente al 1 de enero de 2026, considerando todos sus activos y pasivos.
- Aplicar la exclusión de la casa de habitación hasta 12.000 UVT (art. 295-1 ET).
- Calcular la base gravable y el impuesto a pagar según las tarifas progresivas (art. 295-1 ET).

**Riesgos y condiciones**
- La valoración de los activos debe ser precisa al 1 de enero de 2026.
- Cualquier pasivo que tenga el cliente debe ser debidamente soportado para su deducción en el cálculo del patrimonio líquido.
- La tarifa del impuesto al patrimonio puede variar si hay cambios legislativos antes de 2026.

**Soportes clave**
- Art. 295-1 ET: Impuesto al patrimonio.

**Citations (verbatim):**

  1. (no label) — doc_id='CORE_ya_Arriba_LEYES_INVERSIONES_INCENTIVOS_consolidado_Ley-1429-2010.md'
  2. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_09_Libro1_T1_Caps8a11.md'
  3. (no label) — doc_id='suin_1132325'
  4. (no label) — doc_id='suin_1104445'
  5. (no label) — doc_id='suin_30019323'

---

### impuesto_patrimonio_personas_naturales_P3

- **Class:** 🟡 served_acceptable
- **answer_mode:** `graph_native_partial`
- **effective_topic:** `impuesto_patrimonio_personas_naturales` (expected `impuesto_patrimonio_personas_naturales`)
- **fallback_reason:** `pipeline_d_no_graph_primary_articles`
- **citations:** 5
- **answer length:** 3136 chars
- **latency:** 14066 ms

**Question:**

> Una clienta persona natural tiene patrimonio líquido de $4.200 millones, casi todo en acciones de una SAS productiva donde es socia mayoritaria. Me dice que escuchó que las acciones de empresas operativas se excluyen de la base. ¿Es cierto, parcial o totalmente? ¿Y qué pasa si parte de esas acciones las tiene a través de una sociedad de inversión personal en lugar de directamente?

**Answer (verbatim):**

**Respuestas directas**
- **¿Es cierto, parcial o totalmente?**
  - Las acciones de sociedades nacionales no cotizadas en bolsa, poseídas directamente por personas naturales, se excluyen de la base gravable del impuesto al patrimonio si cumplen las condiciones del (art. 290 ET).
  - La exclusión aplica si la sociedad es productiva y la persona natural es socia mayoritaria, con una participación igual o superior al 10% del capital social.
  - La exclusión no es automática. Se requiere que la sociedad no sea una entidad dedicada a la tenencia de activos subyacentes o pasivos, sino que desarrolle una actividad económica sustancial.
  - La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.
- **¿Y qué pasa si parte de esas acciones las tiene a través de una sociedad de inversión personal en lugar de directamente?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

**Ruta sugerida**
1.  **Verificar la naturaleza de la SAS:** Confirmar que la SAS es una sociedad productiva y no una entidad de tenencia de activos. Esto implica revisar su objeto social, ingresos operacionales y estructura de activos.
2.  **Determinar la participación de la clienta:** Validar que la clienta posee al menos el 10% del capital social de la SAS (art. 290 ET).
3.  **Evaluar el impacto de la tenencia indirecta:** Si las acciones se poseen a través de una sociedad de inversión personal, analizar la estructura para determinar si la exclusión del (art. 290 ET) aplica o si se configura una interposición que impida el beneficio.
4.  **Preparar la declaración de impuesto al patrimonio:** Incluir las acciones de la SAS en la base gravable y aplicar la exclusión si se cumplen todos los requisitos.

**Riesgos y condiciones**
-   **Riesgo de reclasificación:** Si la DIAN determina que la SAS no es una sociedad productiva o que la participación no cumple el umbral, las acciones podrían ser incluidas en la base gravable, generando un mayor impuesto y posibles sanciones.
-   **Interposición de sociedades:** La tenencia de acciones a través de una sociedad de inversión personal podría ser interpretada como una interposición para eludir el impuesto, lo que podría llevar a la no aplicación de la exclusión y a la inclusión de los activos subyacentes en la base gravable de la persona natural.
-   **Valoración de las acciones:** La valoración de las acciones debe ser consistente con los métodos aceptados fiscalmente para evitar ajustes por parte de la DIAN.
-   La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

**Soportes clave**
-   Certificado de existencia y representación legal de la SAS.
-   Estados financieros de la SAS que demuestren su actividad productiva.
-   Certificado de composición accionaria de la SAS.
-   Declaración de renta de la clienta y de la SAS.
-   Escrituras públicas o documentos que soporten la adquisición de las acciones.
-   Si aplica, documentos de constitución y estatutos de la sociedad de inversión personal.

**Citations (verbatim):**

  1. (no label) — doc_id='CORE_ya_Arriba_LEYES_INVERSIONES_INCENTIVOS_consolidado_Ley-1429-2010.md'
  2. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_09_Libro1_T1_Caps8a11.md'
  3. (no label) — doc_id='suin_1132325'
  4. (no label) — doc_id='suin_1104445'
  5. (no label) — doc_id='suin_30046753'

---

## regimen_cambiario

### regimen_cambiario_P1

- **Class:** 🟠 served_weak
- **answer_mode:** `graph_native_partial`
- **effective_topic:** `regimen_cambiario` (expected `regimen_cambiario`)
- **fallback_reason:** `pipeline_d_no_graph_primary_articles`
- **citations:** 4
- **answer length:** 399 chars
- **latency:** 8956 ms

**Question:**

> Cuando una PYME importa mercancía y le paga al proveedor del exterior, ¿esa operación se tiene que canalizar a través del mercado cambiario regulado o la puede pagar como quiera?

**Answer (verbatim):**

**Ruta sugerida**
1. **Paso 1: Identificar si la PYME requiere canalización obligatoria.** Esto se determina según la naturaleza de la operación y los montos involucrados (arts. paso-a-paso-pr-ctico y posiciones-de-expertos ET).

**Riesgos y condiciones**
- La cobertura de esta respuesta es parcial. Es necesario validar el expediente completo antes de emitir una instrucción definitiva al cliente.

**Citations (verbatim):**

  1. (no label) — doc_id='CORE_ya_Arriba_Documents_to_branch_and_improve_Regimen_Cambiario_Normativa_Base_cam_normativa_regimen_cambiario.md'
  2. (no label) — doc_id='CORE_ya_Arriba_REGIMEN_CAMBIARIO_PYME_LOGGRO_L01-guia-practica-regimen-cambiario-pyme.md'
  3. (no label) — doc_id='CORE_ya_Arriba_Documents_to_branch_and_improve_Regimen_Cambiario_Practica_LOGGRO_cam_practica_regimen_cambiario.md'
  4. (no label) — doc_id='CORE_ya_Arriba_Documents_to_branch_and_improve_Regimen_Cambiario_Interpretacion_Expertos_cam_expertos_regimen_cambiario.md'

---

### regimen_cambiario_P2

- **Class:** 🟡 served_acceptable
- **answer_mode:** `graph_native_partial`
- **effective_topic:** `regimen_cambiario` (expected `regimen_cambiario`)
- **fallback_reason:** `pipeline_d_no_graph_primary_articles`
- **citations:** 4
- **answer length:** 715 chars
- **latency:** 9479 ms

**Question:**

> Mi cliente, una SAS importadora, le va a pagar $80.000 USD a un proveedor en Alemania por una máquina que importó. ¿Qué declaración de cambio le toca presentar, en qué momento y a través de quién? ¿Necesita abrir cuenta de compensación o puede hacerlo a través de su banco habitual?

**Answer (verbatim):**

**Respuestas directas**
- **¿Qué declaración de cambio le toca presentar, en qué momento y a través de quién?**
  - La declaración de cambio debe contener la información mínima establecida en el (art. 26-35 ET).
- **¿Necesita abrir cuenta de compensación o puede hacerlo a través de su banco habitual?**
  - Cobertura pendiente para esta sub-pregunta.

**Ruta sugerida**
1. Presentar la declaración de cambio con el contenido mínimo requerido (art. 26-35 ET).

**Riesgos y condiciones**
- La cobertura quedó parcial.

**Soportes clave**
| Tipo de Soporte | Descripción |
|---|---|
| Normativa | Régimen Cambiario Colombiano — Marco Normativo Integral |
| Normativa | DECRETO 624 DE 1989 - Colombia | SUIN Juriscol |

**Citations (verbatim):**

  1. (no label) — doc_id='CORE_ya_Arriba_Documents_to_branch_and_improve_Regimen_Cambiario_Normativa_Base_cam_normativa_regimen_cambiario.md'
  2. (no label) — doc_id='CORE_ya_Arriba_Documents_to_branch_and_improve_Regimen_Cambiario_Practica_LOGGRO_cam_practica_regimen_cambiario.md'
  3. (no label) — doc_id='CORE_ya_Arriba_REGIMEN_CAMBIARIO_PYME_LOGGRO_L01-guia-practica-regimen-cambiario-pyme.md'
  4. (no label) — doc_id='CORE_ya_Arriba_Documents_to_branch_and_improve_Regimen_Cambiario_Interpretacion_Expertos_cam_expertos_regimen_cambiario.md'

---

### regimen_cambiario_P3

- **Class:** 🟠 served_weak
- **answer_mode:** `graph_native_partial`
- **effective_topic:** `regimen_cambiario` (expected `regimen_cambiario`)
- **fallback_reason:** `pipeline_d_no_graph_primary_articles`
- **citations:** 4
- **answer length:** 255 chars
- **latency:** 13426 ms

**Question:**

> Mi cliente recibió en 2025 una inversión extranjera directa de $500.000 USD de un fondo en Países Bajos para capitalización de la SAS. Hicieron la transferencia pero nadie se acordó de hacer el registro ante el Banco de la República. Estamos en marzo de 2026. ¿Qué riesgo hay, todavía se puede regularizar, y qué pasa con los dividendos que eventualmente quieran girarle al inversionista si nunca se registró la inversión?

**Answer (verbatim):**

**Ruta sugerida**
1. PYME Importadora — Qué hacer paso a paso Situación (art. paso-a-paso-pr-ctico ET).

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

**Citations (verbatim):**

  1. (no label) — doc_id='CORE_ya_Arriba_Documents_to_branch_and_improve_Regimen_Cambiario_Normativa_Base_cam_normativa_regimen_cambiario.md'
  2. (no label) — doc_id='CORE_ya_Arriba_Documents_to_branch_and_improve_Regimen_Cambiario_Practica_LOGGRO_cam_practica_regimen_cambiario.md'
  3. (no label) — doc_id='CORE_ya_Arriba_REGIMEN_CAMBIARIO_PYME_LOGGRO_L01-guia-practica-regimen-cambiario-pyme.md'
  4. (no label) — doc_id='CORE_ya_Arriba_Documents_to_branch_and_improve_Regimen_Cambiario_Interpretacion_Expertos_cam_expertos_regimen_cambiario.md'

---

## conciliacion_fiscal

### conciliacion_fiscal_P1

- **Class:** 🟡 served_acceptable
- **answer_mode:** `graph_native_partial`
- **effective_topic:** `conciliacion_fiscal` (expected `conciliacion_fiscal`)
- **fallback_reason:** `pipeline_d_no_graph_primary_articles`
- **citations:** 5
- **answer length:** 2458 chars
- **latency:** 11051 ms

**Question:**

> ¿Qué empresas están obligadas a presentar el formato 2516 de conciliación fiscal y cuándo se entrega?

**Answer (verbatim):**

**Respuestas directas**

*   **¿Qué empresas están obligadas a presentar el formato 2516 de conciliación fiscal?**
    *   Están obligados a presentar el formato 2516 los contribuyentes del impuesto sobre la renta y complementarios que, durante el año gravable, cumplan con los siguientes requisitos:
        *   Personas jurídicas y asimiladas.
        *   Personas naturales y asimiladas, así como los regímenes especiales, que en el año gravable anterior o en el año gravable en curso hayan obtenido ingresos brutos fiscales iguales o superiores a 45.000 UVT (art. 1.7.2. del Decreto 1625 de 2016).
    *   No están obligados a presentar el formato 2516 los contribuyentes que pertenezcan al Régimen Simple de Tributación (SIMPLE) (art. 1.7.2. del Decreto 1625 de 2016).

*   **¿Cuándo se entrega el formato 2516 de conciliación fiscal?**
    *   El formato 2516 se debe presentar en las mismas fechas de vencimiento establecidas para la declaración del impuesto sobre la renta y complementarios, según el último dígito del NIT del contribuyente (art. 1.7.3. del Decreto 1625 de 2016).

**Ruta sugerida**

1.  **Verificar ingresos brutos:** Determinar si los ingresos brutos fiscales del contribuyente en el año gravable anterior o en el año en curso superan las 45.000 UVT.
2.  **Identificar tipo de contribuyente:** Confirmar si el contribuyente es persona jurídica, asimilada, persona natural, o régimen especial.
3.  **Excluir Régimen Simple:** Asegurarse de que el contribuyente no pertenece al Régimen Simple de Tributación.
4.  **Preparar formato 2516:** Diligenciar el formato 2516 de conciliación fiscal, asegurando la correspondencia entre la información contable y fiscal.
5.  **Presentar en plazo:** Presentar el formato 2516 electrónicamente a través de los servicios informáticos de la DIAN, dentro de los plazos establecidos para la declaración de renta.

**Riesgos y condiciones**

*   La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.
*   La no presentación del formato 2516, o su presentación con errores, puede acarrear sanciones por no enviar información o enviarla con errores (art. 651 ET).
*   Es crucial mantener la coherencia entre la contabilidad y la información fiscal para evitar inconsistencias que puedan generar requerimientos de la DIAN.

**Soportes clave**

*   Decreto 1625 de 2016, artículos 1.7.2. y 1.7.3.
*   Estatuto Tributario, artículo 651.

**Citations (verbatim):**

  1. (no label) — doc_id='CORE_ya_Arriba_RENTA_LOGGRO_seccion-11-conciliacion-fiscal.md'
  2. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_09_Libro1_T1_Caps8a11.md'
  3. (no label) — doc_id='CORE_ya_Arriba_LEYES_INVERSIONES_INCENTIVOS_consolidado_Ley-1429-2010.md'
  4. (no label) — doc_id='suin_1132325'
  5. (no label) — doc_id='suin_1104445'

---

### conciliacion_fiscal_P2

- **Class:** 🔵 served_off_topic
- **answer_mode:** `graph_native`
- **effective_topic:** `patrimonio_fiscal_renta` (expected `conciliacion_fiscal`)
- **fallback_reason:** `None`
- **citations:** 5
- **answer length:** 3104 chars
- **latency:** 17071 ms

**Question:**

> Mi cliente es una SAS Grupo 2 NIIF para PYMES con ingresos de $3.800 millones que aplica el modelo de revaluación en sus inmuebles. La revaluación contable subió el valor del edificio en $400 millones en 2025. ¿Cómo manejo eso en el 2516? ¿Es diferencia permanente o temporaria, qué efecto tiene en el patrimonio fiscal versus contable, y me toca registrar impuesto diferido?

**Answer (verbatim):**

**Respuestas directas**
- **¿Cómo manejo eso en el 2516?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.
- **¿Es diferencia permanente o temporaria, qué efecto tiene en el patrimonio fiscal versus contable, y me toca registrar impuesto diferido?**
  - La revaluación de inmuebles bajo NIIF para PYMES genera una diferencia temporaria. Fiscalmente, los activos se valoran por su costo fiscal, no por su valor revaluado contablemente.
  - El patrimonio bruto fiscal se determina por el total de bienes y derechos apreciables en dinero poseídos al cierre del período gravable (art. 261 ET). La revaluación contable de $400 millones no afecta el costo fiscal del edificio.
  - Esto implica que el patrimonio contable será $400 millones mayor que el patrimonio fiscal.
  - Sí, se debe registrar impuesto diferido sobre esta diferencia temporaria, ya que la revaluación contable generará una base gravable fiscal menor en el futuro (por ejemplo, vía mayor depreciación fiscal o menor ganancia en venta si el activo se vende por su valor revaluado).

**Ruta sugerida**
1.  **Identificar el costo fiscal del inmueble:** Mantener el costo de adquisición más mejoras, sin considerar la revaluación contable.
2.  **Determinar la diferencia:** La diferencia entre el valor contable revaluado y el costo fiscal del inmueble constituye una diferencia temporaria.
3.  **Calcular el impuesto diferido:** Aplicar la tarifa del impuesto de renta a la diferencia temporaria para reconocer el pasivo por impuesto diferido.
4.  **Diligenciar el Formato 2516:**
    *   En la sección de patrimonio, el valor fiscal del inmueble debe reflejar el costo fiscal, no el valor revaluado.
    *   La diferencia entre el patrimonio contable (con revaluación) y el patrimonio fiscal (sin revaluación) se reflejará en las conciliaciones.

**Riesgos y condiciones**
*   **Riesgo de inconsistencia:** No conciliar adecuadamente el patrimonio contable y fiscal puede generar inconsistencias en la declaración de renta y el Formato 2516, lo que podría derivar en requerimientos de la DIAN.
*   **Impacto en indicadores financieros:** Aunque la revaluación mejora los indicadores contables, no tiene efecto fiscal inmediato en la base gravable de renta.
*   **Depreciación:** La depreciación fiscal se calculará sobre el costo fiscal del activo, no sobre el valor revaluado.

**Soportes clave**
*   **Estados Financieros:** Donde se evidencie la aplicación del modelo de revaluación y el valor del inmueble.
*   **Anexos contables:** Detalle del cálculo de la revaluación y su impacto en el patrimonio contable.
*   **Cálculo del impuesto diferido:** Documentación del cálculo del pasivo por impuesto diferido asociado a la revaluación.
*   **Conciliación fiscal:** Documento que detalle las diferencias entre la base contable y fiscal del activo y el patrimonio.
*   **Estatuto Tributario:**
    *   (art. 261 ET) para la definición de patrimonio bruto.
    *   (art. 262 ET) para la definición de derechos apreciables en dinero.
    *   (art. 263 ET) para la definición de posesión.

**Citations (verbatim):**

  1. (no label) — doc_id='suin_1132325'
  2. (no label) — doc_id='CORE_ya_Arriba_LEYES_INVERSIONES_INCENTIVOS_consolidado_Ley-1429-2010.md'
  3. (no label) — doc_id='suin_1104445'
  4. (no label) — doc_id='suin_30019323'
  5. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_09_Libro1_T1_Caps8a11.md'

---

### conciliacion_fiscal_P3

- **Class:** 🔵 served_off_topic
- **answer_mode:** `graph_native`
- **effective_topic:** `patrimonio_fiscal_renta` (expected `conciliacion_fiscal`)
- **fallback_reason:** `None`
- **citations:** 4
- **answer length:** 3490 chars
- **latency:** 19185 ms

**Question:**

> Una clienta tiene un contrato de arrendamiento de bodega que bajo NIIF 16 reconoció como activo por derecho de uso de $300 millones y un pasivo por arrendamiento de $290 millones. Fiscalmente entiendo que esas figuras no existen y que solo se deduce el canon pagado en el año. ¿Cómo concilio eso en el 2516, cómo afecta el patrimonio fiscal, y si más adelante la DIAN me hace comparación patrimonial cómo justifico la diferencia?

**Answer (verbatim):**

**Respuestas directas**

*   **¿Cómo concilio el reconocimiento del activo por derecho de uso y el pasivo por arrendamiento bajo NIIF 16 con la normativa fiscal en el formato 2516?**

    *   Fiscalmente, el activo por derecho de uso y el pasivo por arrendamiento no se reconocen. Para efectos tributarios, solo se deduce el canon de arrendamiento efectivamente pagado en el periodo gravable.
    *   En el formato 2516, la conciliación se realiza ajustando el patrimonio fiscal para excluir el activo por derecho de uso y el pasivo por arrendamiento.

*   **¿Cómo afecta el patrimonio fiscal la diferencia entre el tratamiento NIIF 16 y el fiscal?**

    *   El patrimonio fiscal se ve afectado por la no inclusión del activo por derecho de uso y el pasivo por arrendamiento.
    *   El patrimonio bruto fiscal se determina por los bienes y derechos apreciables en dinero poseídos al último día del año (art. 261 ET), entendiendo por posesión el aprovechamiento económico (art. 263 ET). Un activo por derecho de uso bajo NIIF 16 no califica como un bien poseído fiscalmente en los términos del ET.

*   **Si la DIAN realiza una comparación patrimonial, ¿cómo justifico la diferencia?**

    *   La justificación se basa en la diferencia de marcos contables: NIIF 16 para contabilidad financiera y el Estatuto Tributario para fines fiscales.
    *   Se debe demostrar que el activo por derecho de uso y el pasivo por arrendamiento son partidas de naturaleza contable que no tienen correlación fiscal directa, y que el patrimonio fiscal se ha declarado conforme a las normas tributarias.

**Ruta sugerida**

1.  **Identificar las diferencias:** Cuantificar el valor del activo por derecho de uso y el pasivo por arrendamiento reconocidos bajo NIIF 16.
2.  **Ajuste en el formato 2516:**
    *   En la sección de patrimonio, se debe reversar el efecto del activo por derecho de uso y el pasivo por arrendamiento para llegar al patrimonio fiscal.
    *   El patrimonio bruto fiscal se compone de bienes y derechos apreciables en dinero (art. 261 ET), y los derechos apreciables en dinero son aquellos susceptibles de generar renta (art. 262 ET). Un activo por derecho de uso no cumple con la definición de "posesión" fiscal (art. 263 ET).
3.  **Deducción de cánones:** Asegurarse de que solo los cánones de arrendamiento efectivamente pagados sean deducidos en la declaración de renta.

**Riesgos y condiciones**

*   **Riesgo de inconsistencia patrimonial:** Si no se realiza la conciliación adecuada en el formato 2516, la DIAN podría detectar diferencias entre el patrimonio contable y el fiscal, lo que podría derivar en requerimientos.
*   **Justificación documental:** Es crucial mantener la documentación que soporte el reconocimiento NIIF 16 y la conciliación fiscal.
*   **Interpretación de "posesión":** La DIAN podría cuestionar la no inclusión del activo por derecho de uso si interpreta que la entidad tiene un "aprovechamiento económico" (art. 263 ET) que debería reflejarse en el patrimonio. Sin embargo, la jurisprudencia y doctrina han sido claras en que el activo por derecho de uso no es un activo fiscalmente poseído.

**Soportes clave**

*   Contrato de arrendamiento.
*   Estados financieros bajo NIIF 16.
*   Formato 2516 debidamente diligenciado, mostrando la conciliación.
*   Soportes de los pagos de cánones de arrendamiento.
*   Análisis de las diferencias entre NIIF 16 y la normativa fiscal.

**Comparativo NIIF 16 vs. Fiscal**

| Concepto               | NIIF 16

**Citations (verbatim):**

  1. (no label) — doc_id='suin_1132325'
  2. (no label) — doc_id='CORE_ya_Arriba_LEYES_INVERSIONES_INCENTIVOS_consolidado_Ley-1429-2010.md'
  3. (no label) — doc_id='suin_1104445'
  4. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_20_Libro6_GMF.md'

---
