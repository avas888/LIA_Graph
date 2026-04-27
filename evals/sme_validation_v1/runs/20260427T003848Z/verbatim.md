# §1.G SME validation — verbatim responses

**Run dir:** `evals/sme_validation_v1/runs/20260427T003848Z`
**Generated:** 2026-04-26 08:00:17 PM Bogotá
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
- **latency:** 7153 ms

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
- **answer length:** 2664 chars
- **latency:** 21703 ms

**Question:**

> Tengo una SAS comercializadora con ingresos de $2.800 millones en 2025 y un impuesto neto de renta de $95 millones. El año pasado pagaron $70 millones. Quieren acogerse a beneficio de auditoría. ¿Califican? ¿Y si más adelante toca corregir la declaración para meter unos ingresos que se omitieron, pierden el beneficio?

**Answer (verbatim):**

**Respuestas directas**
- **Tengo una SAS comercializadora con ingresos de $2.800 millones en 2025 y un impuesto neto de renta de $95 millones. El año pasado pagaron $70 millones. Quieren acogerse a beneficio de auditoría. ¿Califican?**
  - Para calificar al beneficio de auditoría, la SAS debe cumplir con los requisitos del (art. 689-1 ET). Específicamente, el impuesto neto de renta debe incrementarse en un porcentaje mínimo respecto al año anterior.
  - Con un impuesto neto de renta de $95 millones para 2025 y $70 millones pagados en 2024, el incremento es del 35.71% ([$95M - $70M] / $70M).
  - La Ley 2277 de 2022 modificó el (art. 689-1 ET) estableciendo los siguientes porcentajes de incremento para el beneficio de auditoría:

| Incremento del Impuesto Neto de Renta | Término de firmeza de la declaración |
|---|---|
| Igual o superior al 35% | 6 meses |
| Igual o superior al 25% e inferior al 35% | 12 meses |

  - Dado que el incremento del 35.71% es superior al 35%, la SAS califica para el beneficio de auditoría con un término de firmeza de 6 meses.
- **¿Y si más adelante toca corregir la declaración para meter unos ingresos que se omitieron, pierden el beneficio?**
  - Si la declaración inicial se corrige para incluir ingresos omitidos, el beneficio de auditoría se mantiene siempre que la corrección no disminuya el impuesto neto de renta que sirvió de base para obtener el beneficio (art. 689-1 ET, parágrafo 2).
  - Si la corrección aumenta el impuesto neto de renta, el beneficio se mantiene y el término de firmeza se cuenta a partir de la fecha de presentación de la declaración inicial.
  - Si la corrección disminuye el impuesto neto de renta, se pierde el beneficio de auditoría y la declaración queda sujeta al término de firmeza general de 3 años (art. 714 ET).

**Ruta sugerida**
- Presentar la declaración de renta de 2025 asegurando que el impuesto neto de renta refleje el incremento necesario para acogerse al beneficio de auditoría.
- Mantener los soportes que demuestren el cálculo del impuesto neto de renta y su comparación con el año anterior.

**Riesgos y condiciones**
- **Pérdida del beneficio por corrección:** Si se realiza una corrección que disminuya el impuesto neto de renta inicialmente declarado, se pierde el beneficio de auditoría.
- **Fiscalización:** Aunque el beneficio reduce el término de firmeza, la DIAN puede ejercer facultades de fiscalización durante ese periodo.

**Soportes clave**
- Declaración de renta del año gravable 2024.
- Declaración de renta del año gravable 2025.
- (art. 689-1 ET) modificado por la Ley 2277 de 2022.
- (art. 714 ET) sobre la firmeza de las declaraciones tributarias.

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
- **answer length:** 969 chars
- **latency:** 9997 ms

**Question:**

> Mi cliente, una SAS, cerró 2025 con TTD por debajo del 15% y le tocó liquidar Impuesto a Adicionar. Sin el IA el incremento del impuesto neto frente a 2024 quedaría en 22%, pero con el IA sumando llega al 28%. ¿La DIAN me deja contar el IA dentro del impuesto neto para alcanzar el umbral del beneficio? Y aparte de eso, mi cliente está en ZOMAC, ¿eso cambia algo?

**Answer (verbatim):**

**Respuestas directas**
- **¿La DIAN me deja contar el IA dentro del impuesto neto para alcanzar el umbral del beneficio?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.
- **¿eso cambia algo?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

**Ruta sugerida**
1. Confirma si el emisor estaba obligado a facturar electrónicamente (art. 616-1 ET).
2. Revisa si existió una contingencia válida que justificara un soporte diferente a la factura electrónica.
3. Realiza una verificación operativa del soporte antes de considerarlo fiscalmente válido.

**Riesgos y condiciones**
- No aceptes soportes diferentes a la factura electrónica si la obligación de facturar electrónicamente existía y no hubo contingencia válida (art. 616-1 ET).
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

**Citations (verbatim):**

  1. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_18_Libro5_Procedimiento_P1.md'
  2. (no label) — doc_id='CORE_ya_Arriba_LEYES_INVERSIONES_INCENTIVOS_consolidado_Ley-1429-2010.md'
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
- **answer length:** 2646 chars
- **latency:** 17231 ms

**Question:**

> ¿Cuánto tiempo tiene la DIAN para revisar y modificar una declaración de renta de una SAS que se presentó normal, sin pérdidas ni beneficio de auditoría?

**Answer (verbatim):**

**Respuestas directas**

*   **¿Cuánto tiempo tiene la DIAN para revisar y modificar una declaración de renta de una SAS que se presentó normal, sin pérdidas ni beneficio de auditoría?**
    *   La firmeza de la declaración de renta es de tres (3) años contados a partir de la fecha de vencimiento del plazo para declarar, o de la fecha de presentación si fue extemporánea (art. 714 ET).
    *   Si la declaración presenta un saldo a favor, el término de firmeza es de tres (3) años contados a partir de la fecha de solicitud de devolución o compensación (art. 714 ET).
    *   Si la declaración de renta arroja una pérdida fiscal, el término de firmeza es de seis (6) años (art. 147 ET).
    *   Si la declaración de renta es objeto de beneficio de auditoría, el término de firmeza es de seis (6) o doce (12) meses, según el incremento del impuesto neto de renta (art. 689-1 ET).

**Ruta sugerida**

1.  La regla general para la compensación de pérdidas fiscales es que la sociedad las compensa con rentas líquidas ordinarias futuras; no se trasladan a los socios ni se tratan como un saldo a favor (art. 147 ET).
2.  Para pérdidas fiscales generadas bajo el régimen actual, el límite temporal es de doce (12) períodos gravables siguientes, sin un tope porcentual anual (arts. 147 y 356-1 ET).
3.  La firmeza de la declaración que origina o compensa una pérdida fiscal debe evaluarse de forma independiente a la mecánica de compensación (arts. 147 y 260 ET).
4.  Si las pérdidas fiscales provienen de años anteriores a 2017, es necesario validar el régimen de transición establecido en el art. 290 ET antes de aplicar el límite de los doce (12) años.

**Riesgos y condiciones**

*   No confundir la compensación de pérdidas fiscales con la devolución o compensación de saldos a favor. El tratamiento y la normativa aplicable son distintos (arts. 147 y 588 ET).
*   No aplicar el término de firmeza ordinario de tres (3) años si la declaración genera o compensa pérdidas fiscales. En estos casos, el término de firmeza es de seis (6) años (arts. 147 y 260 ET).
*   No aplicar el art. 588 ET si la corrección de la declaración aumenta el saldo a favor o disminuye el valor a pagar, ya que este artículo aplica para correcciones que aumentan el impuesto o disminuyen el saldo a favor.

**Soportes clave**

| Artículo | Descripción |
| :------- | :---------- |
| Art. 147 ET | COMPENSACIÓN DE PÉRDIDAS FISCALES DE SOCIEDADES |
| Art. 260 ET | AJUSTES |
| Art. 588 ET | CORRECCIONES QUE AUMENTAN EL IMPUESTO O DISMINUYEN EL SALDO A FAVOR |
| Art. 714 ET | TÉRMINO PARA NOTIFICAR LA LIQUIDACIÓN DE REVISIÓN |
| Art. 689-1 ET | BENEFICIO DE AUDITORÍA |

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
- **answer length:** 1029 chars
- **latency:** 19455 ms

**Question:**

> Recibí en febrero de 2026 un cliente nuevo. Presentó la declaración de renta del 2022 en mayo de 2023, no usó beneficio de auditoría, no tuvo pérdidas. ¿Esa declaración ya quedó en firme o todavía la DIAN puede tocarla? El cliente está nervioso porque le llegó un oficio persuasivo y quiere saber si todavía está expuesto.

**Answer (verbatim):**

**Respuestas directas**
- **Recibí en febrero de 2026 un cliente nuevo. Presentó la declaración de renta del 2022 en mayo de 2023, no usó beneficio de auditoría, no tuvo pérdidas. ¿Esa declaración ya quedó en firme o todavía la DIAN puede tocarla?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.
- **El cliente está nervioso porque le llegó un oficio persuasivo y quiere saber si todavía está expuesto?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

**Ruta sugerida**
1. Confirma si el emisor estaba obligado a facturar electrónicamente y si existió una contingencia válida antes de aceptar el soporte (arts. 100 y 101 ET).
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
- **answer length:** 2922 chars
- **latency:** 19728 ms

**Question:**

> Una SAS compensó en la declaración del 2024 unas pérdidas que generó en 2018. Ya entregamos esa declaración. Ahora me pregunto: ¿la firmeza de la declaración del 2024 es de 3 o de 5 años por haber compensado? ¿Y si encima la DIAN quiere meterse a revisar la pérdida del 2018 que ya está más que vencida en términos generales, lo puede hacer?

**Answer (verbatim):**

**Respuestas directas**
- **¿la firmeza de la declaración del 2024 es de 3 o de 5 años por haber compensado?**
  - La firmeza de la declaración de renta del 2024, al compensar pérdidas fiscales, no se rige por la regla ordinaria de 3 años. En este caso, el término de firmeza es de 6 años (art. 147 ET).
  - Si las pérdidas compensadas provienen de años anteriores a 2017, es crucial revisar el régimen de transición del art. 290 ET antes de aplicar el límite de 12 años.
  - Antes de compensar, se debe inventariar las pérdidas por año de origen, el saldo pendiente y la renta líquida disponible del período para determinar el monto a absorber.
  - Si se considera una corrección que va en contra del contribuyente, se debe validar si aún se está dentro del término de 3 años y si ya existe un emplazamiento o requerimiento especial.
- **¿Y si encima la DIAN quiere meterse a revisar la pérdida del 2018 que ya está más que vencida en términos generales, lo puede hacer?**
  - Sí, la DIAN puede revisar la pérdida del 2018. Aunque la declaración de 2018 pueda estar en firme bajo la regla general, al compensar esa pérdida en la declaración de 2024, el término de firmeza de la pérdida se extiende. La firmeza de la declaración donde se compensa la pérdida (2024) es de 6 años, y durante este período, la DIAN puede auditar el origen y la validez de la pérdida compensada (art. 147 ET).
  - Si el saldo a favor requiere una corrección previa, esta debe realizarse antes de cualquier solicitud a la DIAN.
  - Si la sociedad vuelve a generar renta líquida positiva, la compensación de pérdidas acumuladas es la norma para reducir la base gravable dentro del marco legal vigente.

**Ruta sugerida**
1.  La regla principal del art. 147 ET establece que las sociedades compensan pérdidas fiscales con rentas líquidas ordinarias futuras; no se trasladan a socios ni se tratan como saldo a favor.
2.  Para pérdidas bajo el régimen vigente, el límite es de doce períodos gravables siguientes, sin tope porcentual anual (arts. 147 y 647-1 ET).
3.  La firmeza de la declaración donde se compensa la pérdida es un aspecto distinto al mecanismo de compensación. El término de revisión de la pérdida se extiende (arts. 147 y 260 ET).
4.  Si las pérdidas provienen de años anteriores a 2017, se debe validar el régimen de transición del art. 290 ET antes de aplicar el límite de 12 años.

**Riesgos y condiciones**
-  No se debe confundir la compensación de pérdidas fiscales en renta con la devolución o compensación de saldos a favor (arts. 147 y 857 ET).
-  La firmeza de una declaración que origina o compensa pérdidas no es de 3 años, sino de 6 años (arts. 147 y 260 ET).
-  No aplicar la lógica del art. 588 ET cuando la corrección disminuye el valor a pagar o aumenta el saldo a favor.
-  Evitar mezclar una solicitud de devolución con una declaración que aún presenta inconsistencias o requiere corrección (arts. 857 y 588 ET).

**Citations (verbatim):**

  1. (no label) — doc_id='to_upload_BRECHAS-SEMANA4-ABRIL-2026_FIRMEZA_DECLARACIONES_EXPERTOS_EXPERTOS_FIR-E01-interpretaciones-firmeza-beneficio-auditoria.md'
  2. (no label) — doc_id='CORE_ya_Arriba_LEYES_INVERSIONES_INCENTIVOS_consolidado_Ley-1429-2010.md'
  3. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_09_Libro1_T1_Caps8a11.md'
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
- **answer length:** 2802 chars
- **latency:** 16007 ms

**Question:**

> ¿Cuánto cobra la DIAN por presentar una declaración de renta tarde si no hay impuesto a cargo?

**Answer (verbatim):**

**Respuestas directas**

*   **¿Cuánto cobra la DIAN por presentar una declaración de renta tarde si no hay impuesto a cargo?**
    *   La sanción mínima aplicable es de 10 UVT (art. 639 ET). Para el año 2024, esto equivale a $471.000.
    *   Esta sanción se aplica incluso si la declaración no arroja impuesto a cargo.

*   **¿Hay alguna forma de reducir esta sanción?**
    *   Sí, la sanción puede reducirse si se cumple alguna de las siguientes condiciones:
        *   **Reducción del 50%:** Si la declaración se presenta antes de que la DIAN profiera pliego de cargos o auto que ordene inspección tributaria, y el contribuyente subsana la infracción voluntariamente (art. 640 ET).
        *   **Reducción del 75%:** Si la declaración se presenta después de que la DIAN profiera pliego de cargos o auto que ordene inspección tributaria, pero antes de que se notifique la liquidación de revisión, y el contribuyente subsana la infracción voluntariamente (art. 640 ET).
        *   **Reducción del 80% (Ley 1429 de 2010):** Para pequeñas empresas que cumplan con los requisitos de la Ley 1429 de 2010, la sanción puede reducirse al 20% del valor inicial durante los primeros años de su constitución.

*   **¿Qué pasa si la DIAN me notifica antes de que yo presente la declaración?**
    *   Si la DIAN notifica un requerimiento antes de la presentación, la sanción por extemporaneidad se incrementa (art. 641 ET).

**Ruta sugerida**

1.  **Presentación inmediata:** Presentar la declaración de renta lo antes posible para evitar mayores incrementos en la sanción.
2.  **Cálculo de la sanción:** Determinar la sanción por extemporaneidad aplicando el 5% del impuesto a cargo por cada mes o fracción de mes de retardo, sin exceder el 100% del impuesto (art. 641 ET). Si no hay impuesto a cargo, aplicar la sanción mínima de 10 UVT (art. 639 ET).
3.  **Evaluación de reducción:** Verificar si se cumplen las condiciones para aplicar alguna de las reducciones de sanción (art. 640 ET o Ley 1429 de 2010).
4.  **Pago:** Realizar el pago de la sanción junto con la declaración.

**Riesgos y condiciones**

*   **Incremento de la sanción:** La sanción aumenta por cada mes o fracción de mes de retardo.
*   **Notificación de la DIAN:** Si la DIAN notifica un requerimiento antes de la presentación, la sanción se incrementa y las posibilidades de reducción disminuyen.
*   **Intereses de mora:** Si hay impuesto a cargo, se generarán intereses de mora desde la fecha de vencimiento hasta la fecha de pago (art. 634 ET).

**Soportes clave**

*   Estatuto Tributario (ET):
    *   Art. 634 ET: Intereses moratorios.
    *   Art. 639 ET: Sanción mínima.
    *   Art. 640 ET: Reducción de sanciones.
    *   Art. 641 ET: Sanción por extemporaneidad.
*   Ley 1429 de 2010: Formalización y Generación de Empleo.

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
- **latency:** 7327 ms

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
- **answer length:** 929 chars
- **latency:** 9862 ms

**Question:**

> Le presenté a un cliente la declaración a tiempo. Tres meses después detectamos que se nos olvidó incluir una venta importante de $80 millones. La DIAN no ha mandado nada. Si corrijo voluntariamente subiendo el impuesto, ¿la sanción es del 10% o me alcanza alguna reducción adicional? ¿Y comparado con esperar a que la DIAN lo encuentre y me cobre inexactitud, qué tan grande es la diferencia en plata?

**Answer (verbatim):**

**Respuestas directas**
- **¿la sanción es del 10% o me alcanza alguna reducción adicional?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.
- **¿Y comparado con esperar a que la DIAN lo encuentre y me cobre inexactitud, qué tan grande es la diferencia en plata?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

**Ruta sugerida**
1. Revisa el soporte de la venta antes de incluirlo en la declaración.
2. Confirma si el emisor estaba obligado a facturar electrónicamente y si existió una contingencia válida para no hacerlo (art. 657 ET).

**Riesgos y condiciones**
- No aceptes soportes diferentes a la factura electrónica si la obligación de facturar electrónicamente existía (art. 657 ET).
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
- **latency:** 6690 ms

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
- **answer length:** 1962 chars
- **latency:** 15785 ms

**Question:**

> Mi cliente tiene una panadería SAS, compró un horno industrial en 2025 por $120 millones más IVA del 19%. Quiere saber si puede tomar todo el IVA como descuento en la declaración de este año o si tiene que repartirlo. ¿Qué pasa si el descuento le queda más grande que el impuesto a cargo?

**Answer (verbatim):**

### Respuestas directas

*   **¿Puede tomar todo el IVA como descuento en la declaración de este año o tiene que repartirlo?**
    *   El IVA pagado en la adquisición del horno industrial se puede tomar como descuento tributario en el impuesto de renta.
    *   Este descuento se aplica en el año gravable en que se adquiere el activo (2025). No se reparte.
    *   El valor del IVA es de $22.800.000 ($120.000.000 \* 19%).

*   **¿Qué pasa si el descuento le queda más grande que el impuesto a cargo?**
    *   Si el valor del descuento por IVA excede el impuesto de renta a cargo del contribuyente, el excedente no es recuperable ni compensable en periodos futuros. Se pierde.

### Ruta sugerida

1.  **Verificar la naturaleza del activo:** Confirmar que el horno industrial califica como activo fijo real productivo.
2.  **Registro contable:** Asegurar el registro adecuado del IVA pagado como parte del costo del activo o como un mayor valor del mismo, según la política contable de la panadería.
3.  **Cálculo del descuento:** Determinar el valor exacto del IVA pagado que será objeto de descuento.
4.  **Aplicación en la declaración de renta:** Incluir el descuento en la declaración de renta del año gravable 2025.

### Riesgos y condiciones

*   **Calificación del activo:** El principal riesgo es que la DIAN no considere el horno como un activo fijo real productivo, lo que invalidaría el descuento.
*   **Uso exclusivo:** El activo debe ser utilizado exclusivamente en la actividad productora de renta de la panadería.
*   **No simultaneidad:** No se puede tomar el IVA como descuento tributario y, al mismo tiempo, como costo o deducción en el impuesto de renta.

### Soportes clave

*   Factura de compra del horno industrial, donde se discrimine el IVA.
*   Certificación del revisor fiscal o contador público que acredite la adquisición y el uso del activo en la actividad productora de renta.
*   Registro en los libros contables de la panadería.

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
- **answer length:** 3511 chars
- **latency:** 20109 ms

**Question:**

> Un cliente hizo donaciones a una fundación calificada en el RTE por $20 millones, además compró maquinaria con IVA de $30 millones, e invirtió $50 millones en un proyecto de innovación calificado por el CNBT. Su impuesto a cargo es de $200 millones. ¿Cómo manejo los topes? Entiendo que el del 25% del artículo 258 aplica para algunos pero no para todos, y no tengo claro cuáles entran y cuáles no.

**Answer (verbatim):**

**Respuestas directas**
- **Un cliente hizo donaciones a una fundación calificada en el RTE por $20 millones, además compró maquinaria con IVA de $30 millones, e invirtió $50 millones en un proyecto de innovación calificado por el CNBT. Su impuesto a cargo es de $200 millones. ¿Cómo manejo los topes?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.
- **Entiendo que el del 25% del artículo 258 aplica para algunos pero no para todos, y no tengo claro cuáles entran y cuáles no?**
  - El límite del 25% del impuesto a cargo (art. 258 ET) aplica a los descuentos tributarios de los artículos 255, 256 y 257 del Estatuto Tributario.
  - El descuento por donaciones a entidades del Régimen Tributario Especial (RTE) no está sujeto al límite del 25% del impuesto a cargo.
  - El descuento por inversión en proyectos de investigación, desarrollo tecnológico o innovación (art. 256 ET) sí está sujeto al límite del 25% del impuesto a cargo (art. 258 ET).
  - El IVA pagado en la adquisición de maquinaria no es un descuento tributario en sí mismo, sino un costo o deducción, o un IVA descontable según el régimen del contribuyente. No entra en el cálculo del tope del 25%.

**Ruta sugerida**
1.  Calcula el descuento por donaciones: El valor de la donación ($20 millones) es 100% descontable del impuesto sobre la renta, sin el límite del 25% del impuesto a cargo.
2.  Calcula el descuento por inversión en innovación: El valor de la inversión ($50 millones) es un descuento tributario (art. 256 ET) y está sujeto al límite del 25% del impuesto a cargo (art. 258 ET).
3.  Determina el impuesto a cargo inicial: $200 millones.
4.  Aplica el descuento por donaciones:
    *   Impuesto a cargo después de donaciones = $200 millones - $20 millones = $180 millones.
5.  Calcula el límite del 25% sobre el impuesto a cargo restante para los descuentos de los artículos 255, 256 y 257 ET:
    *   Límite = 25% de $180 millones = $45 millones.
6.  Compara el descuento por innovación con el límite:
    *   Descuento por innovación = $50 millones.
    *   Límite aplicable = $45 millones.
    *   El descuento máximo a tomar por innovación es de $45 millones.
7.  Calcula el impuesto a cargo final:
    *   Impuesto a cargo después de donaciones = $180 millones.
    *   Menos descuento por innovación (limitado) = $45 millones.
    *   Impuesto a cargo final = $135 millones.

**Riesgos y condiciones**
*   **Calificación de la fundación:** Asegúrate de que la fundación esté debidamente calificada en el Régimen Tributario Especial (RTE) y que la donación cumpla con los requisitos del artículo 356-2 ET.
*   **Calificación del proyecto de innovación:** Confirma que el proyecto de innovación esté calificado por el Consejo Nacional de Beneficios Tributarios (CNBT) y que la inversión cumpla con los requisitos del artículo 256 ET.
*   **Naturaleza del IVA:** El IVA de la maquinaria debe ser tratado según la actividad económica del cliente y su régimen de IVA. Si es un IVA descontable, se manejará en la declaración de IVA. Si no, será parte del costo del activo. No es un descuento tributario del impuesto de renta.

**Soportes clave**
*   Certificado de la fundación que acredite su pertenencia al RTE y el valor de la donación.
*   Resolución del CNBT que califica el proyecto de innovación y el monto de la inversión.
*   Facturas de compra de la maquinaria con el detalle del IVA.
*   Declaración de Renta del año gravable para verificar el impuesto a cargo.

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
- **latency:** 7579 ms

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
- **latency:** 7667 ms

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
- **latency:** 8504 ms

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
- **answer length:** 3060 chars
- **latency:** 11070 ms

**Question:**

> Cuando una SAS reparte dividendos a su socio persona natural residente, ¿desde qué monto le empiezan a cobrar impuesto sobre los dividendos no gravados?

**Answer (verbatim):**

**Respuestas directas**

*   **¿Desde qué monto se empiezan a cobrar impuestos sobre los dividendos no gravados a una persona natural residente?**
    *   Los dividendos no gravados distribuidos a personas naturales residentes están sujetos a una tarifa del 10% sobre el monto que exceda las 1.090 UVT (art. 242 ET). Para el año 2024, esto equivale a $48.337.000 (1.090 UVT \* $44.769).

*   **¿Cómo se calcula la base gravable para los dividendos no gravados?**
    *   La base gravable se determina restando las 1.090 UVT del valor total de los dividendos no gravados recibidos. Sobre el excedente se aplica la tarifa del 10%.

*   **¿Qué retención en la fuente aplica a estos dividendos?**
    *   Aplica una retención en la fuente del 10% sobre el monto que exceda las 1.090 UVT (art. 242 ET).

**Ruta sugerida**

1.  **Identificar la naturaleza del dividendo:** Confirmar si el dividendo es gravado o no gravado, según lo certificado por la sociedad que lo distribuye (art. 48 ET).
2.  **Determinar el monto total de dividendos no gravados:** Sumar todos los dividendos no gravados recibidos por la persona natural residente en el periodo.
3.  **Calcular el umbral exento:** Multiplicar 1.090 UVT por el valor de la UVT del año gravable correspondiente.
4.  **Establecer la base gravable:** Restar el umbral exento del monto total de dividendos no gravados. Si el resultado es negativo o cero, no hay impuesto.
5.  **Calcular el impuesto:** Aplicar la tarifa del 10% a la base gravable obtenida.
6.  **Verificar la retención en la fuente:** Asegurarse de que la sociedad distribuidora haya practicado la retención en la fuente correctamente, si aplica.

**Riesgos y condiciones**

*   La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.
*   **Cambios normativos:** Las tarifas y umbrales pueden modificarse con futuras reformas tributarias. Es crucial validar la normativa vigente al momento de la distribución.
*   **Clasificación errónea del dividendo:** Si la sociedad distribuidora clasifica incorrectamente el dividendo como no gravado, cuando en realidad es gravado, esto puede generar ajustes y sanciones para el socio.
*   **Residencia fiscal:** La aplicación de estas reglas depende de que el socio sea considerado persona natural residente fiscal en Colombia. Las reglas para no residentes son diferentes (art. 247 ET).

**Soportes clave**

*   **Certificado de dividendos:** Emitido por la SAS, debe especificar el monto de dividendos gravados y no gravados (art. 378 ET).
*   **Declaración de renta de la SAS:** Para verificar la utilidad gravada y no gravada que soporta la distribución.
*   **Estatuto Tributario (ET):**
    *   Art. 48 ET: "Dividendos y participaciones no gravados".
    *   Art. 49 ET: "Determinación de los dividendos y participaciones no gravados".
    *   Art. 242 ET: "Tarifa especial para dividendos y participaciones recibidos por personas naturales residentes".
    *   Art. 387-1 ET: "Retención en la fuente para dividendos y participaciones".

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
- **answer length:** 2602 chars
- **latency:** 24154 ms

**Question:**

> Mi cliente es socio único de una SAS que cerró 2025 con utilidad contable de $300 millones y pagó impuesto de renta de $80 millones. Quiere repartirse $200 millones en 2026 como dividendos. ¿Cuánto de eso le queda como no gravado y cuánto va a pagar el socio cuando lo declare en su renta personal? ¿La SAS le tiene que practicar retención al momento de pagar?

**Answer (verbatim):**

**Respuestas directas**
- **¿Cuánto de eso le queda como no gravado y cuánto va a pagar el socio cuando lo declare en su renta personal?**
  - La utilidad contable de $300 millones y el impuesto de renta pagado de $80 millones resultan en una utilidad líquida de $220 millones.
  - De los $200 millones que el socio desea repartir, el monto no gravado se determina por la proporción de la utilidad que ya pagó impuesto a nivel de la SAS.
  - Para calcular la parte no gravada, se aplica la siguiente fórmula: (Utilidad Líquida / Utilidad Contable) * Dividendos a Repartir.
  - En este caso: ($220 millones / $300 millones) * $200 millones = $146.67 millones. Este valor es el dividendo no gravado para el socio.
  - El dividendo gravado será la diferencia: $200 millones - $146.67 millones = $53.33 millones.
  - El socio deberá incluir los $53.33 millones como ingreso gravado en su declaración de renta personal. La tarifa aplicable dependerá de su tabla de ingresos.
- **¿La SAS le tiene que practicar retención al momento de pagar?**
  - Sí, la SAS debe practicar retención en la fuente sobre la porción gravada de los dividendos al momento del pago o abono en cuenta (art. 366-1 ET).
  - La tarifa de retención en la fuente para dividendos gravados distribuidos a personas naturales residentes es del 10% (art. 242-1 ET).
  - Por lo tanto, la retención a practicar sería sobre los $53.33 millones gravados, lo que equivale a $5.33 millones.

**Ruta sugerida**
- Calcular la utilidad líquida de la SAS después de impuestos.
- Determinar la proporción de la utilidad que ya fue gravada a nivel de la SAS.
- Aplicar esta proporción a los dividendos a distribuir para establecer la parte gravada y no gravada.
- Informar al socio sobre el monto gravado que deberá declarar en su renta personal.
- Instruir a la SAS para que practique la retención en la fuente correspondiente sobre la porción gravada de los dividendos.

**Riesgos y condiciones**
- La correcta determinación de la utilidad líquida y la aplicación de la proporción son clave para evitar errores en la retención y en la declaración del socio.
- Cualquier ajuste posterior en la declaración de renta de la SAS podría afectar la proporción de dividendos gravados y no gravados.
- Es fundamental que la SAS cumpla con la retención en la fuente y su posterior declaración y pago para evitar sanciones.

**Soportes clave**
- Estados financieros de la SAS al 31 de diciembre de 2025.
- Declaración de renta de la SAS del año gravable 2025.
- Acta de la asamblea de accionistas o del socio único donde se aprueba la distribución de dividendos.

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
- **answer length:** 1347 chars
- **latency:** 18146 ms

**Question:**

> A mi cliente persona jurídica le tocó liquidar Impuesto a Adicionar por TTD el año pasado. Para efectos del cálculo del artículo 49 y determinar cuántos dividendos puede repartir como no gravados, ¿el IA cuenta como impuesto pagado o no? Escuché que hubo una suspensión del Consejo de Estado sobre un concepto DIAN que decía algo de eso, y no tengo claro cómo está la cosa hoy.

**Answer (verbatim):**

**Respuestas directas**
- **A mi cliente persona jurídica le tocó liquidar Impuesto a Adicionar por TTD el año pasado. Para efectos del cálculo del artículo 49 y determinar cuántos dividendos puede repartir como no gravados, ¿el IA cuenta como impuesto pagado o no?**
  - Para determinar los dividendos no gravados según el (art. 49 ET), el Impuesto a Adicionar por TTD no se considera un impuesto pagado. El (art. 49 ET) establece la metodología para calcular la utilidad no gravada, y el Impuesto a Adicionar no encaja en las categorías de impuestos que reducen la utilidad comercial para este fin.
- **Escuché que hubo una suspensión del Consejo de Estado sobre un concepto DIAN que decía algo de eso, y no tengo claro cómo está la cosa hoy?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

**Ruta sugerida**
1.  Para el cálculo de dividendos no gravados, aplica directamente el (art. 49 ET) sin considerar el Impuesto a Adicionar como un impuesto pagado que disminuya la utilidad comercial.

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
- **answer length:** 2440 chars
- **latency:** 15820 ms

**Question:**

> ¿Cuánto tiempo tiene la DIAN para resolver una solicitud de devolución de saldo a favor en renta cuando la pides sin garantía?

**Answer (verbatim):**

**Respuestas directas**

*   **¿Cuánto tiempo tiene la DIAN para resolver una solicitud de devolución de saldo a favor en renta cuando la pides sin garantía?**
    *   La DIAN tiene un término general de 50 días hábiles para resolver las solicitudes de devolución de saldos a favor (art. 850 ET).
    *   Este término puede reducirse a 30 días hábiles si el 85% o más de los costos o gastos y de los impuestos descontables provienen de facturación electrónica.
    *   Para contribuyentes de riesgo bajo, el término puede ser de 20 días hábiles, siempre que el 100% de los costos o gastos y de los impuestos descontables provengan de facturación electrónica.

**Ruta sugerida**

1.  Enfoca el caso como una solicitud de devolución o compensación de saldo a favor, no como un problema de facturación electrónica (arts. 589 y 850 ET).
2.  Antes de radicar, revisa la declaración que generó el saldo a favor y asegura la coherencia de soportes, anexos y datos del contribuyente (arts. 589 y 850 ET).
3.  Confirma que el saldo a favor esté correctamente determinado en la declaración base antes de proceder con la solicitud de devolución (arts. 589 y 850 ET).
4.  Si el expediente está completo, considera los términos de 50, 30 o 20 días hábiles como referencia operativa, según el tipo de soporte documental que acompañe la solicitud (arts. 850 y 589 ET).

**Riesgos y condiciones**

*   Evita radicar solicitudes con cifras o soportes inconsistentes, ya que esto puede resultar en inadmisiones o revisiones posteriores (arts. 850 y 589 ET).
*   No presentes una solicitud de devolución si la declaración aún presenta inconsistencias o requiere corrección (arts. 850 y 589 ET).
*   Ten presente que una corrección que aumente el saldo a favor reinicia el término de firmeza de la declaración para la DIAN desde la fecha de la corrección (arts. 850 y 589 ET).
*   El cumplimiento del cliente en facturación electrónica es una condición complementaria; no altera la naturaleza del trámite de devolución, pero puede influir en los plazos de resolución (arts. 850 y 589 ET).

**Soportes clave**

| Tipo de Soporte | Plazo de Resolución (Días Hábiles) |
| :-------------- | :--------------------------------- |
| General         | 50                                 |
| Facturación electrónica (85% o más) | 30                                 |
| Facturación electrónica (100%) y contribuyente de riesgo bajo | 20                                 |

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
- **answer length:** 2230 chars
- **latency:** 16177 ms

**Question:**

> Mi cliente, una SAS exportadora, cerró 2025 con un saldo a favor en renta de $180 millones por exceso de retenciones. Le presenté la declaración la semana pasada y necesita la plata cuanto antes para capital de trabajo. ¿Le conviene meter garantía bancaria para acelerar la devolución? ¿Y si no, le devuelven en plata o en TIDIS?

**Answer (verbatim):**

**Respuestas directas**
- **¿Le conviene meter garantía bancaria para acelerar la devolución?**
  - La decisión de presentar garantía bancaria para acelerar la devolución debe evaluarse considerando el costo de la garantía frente al beneficio de la liquidez anticipada.
  - El trámite de devolución se rige por el Libro Séptimo del ET (arts. 815–865).
  - Si el cliente tiene obligaciones tributarias pendientes, primero se debe analizar la opción de compensación del saldo a favor, según el art. 815 ET, antes de solicitar la devolución en efectivo.
- **¿Y si no, le devuelven en plata o en TIDIS?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

**Ruta sugerida**
1. Confirma que el cliente cumple con los requisitos formales para solicitar la devolución o compensación de saldos a favor, incluyendo la actualización del RUT (art. 555-2 ET) y la representación legal (art. 555 ET).
2. Evalúa la conveniencia de presentar una garantía bancaria para acelerar el proceso de devolución, considerando los plazos establecidos en el Estatuto Tributario y el costo financiero de la garantía.
3. Si se opta por la devolución sin garantía, el proceso seguirá los plazos ordinarios de la DIAN.

**Riesgos y condiciones**
- El cumplimiento de las obligaciones de facturación electrónica es un requisito general para los contribuyentes, pero no altera la naturaleza del trámite de devolución de saldos a favor, que se rige por sus propias normas (arts. 555 y 555-1 ET).
- La DIAN puede rechazar la solicitud de devolución si encuentra inconsistencias o incumplimientos de requisitos formales o sustanciales.

**Soportes clave**
| Tipo de Soporte | Descripción |
|---|---|
| Declaración de Renta | Formulario 110 del año gravable 2025, donde se evidencia el saldo a favor de $180 millones. |
| Certificado de Existencia y Representación Legal | Documento que acredite la existencia de la SAS y la representación legal para actuar ante la DIAN (art. 555 ET). |
| RUT actualizado | Registro Único Tributario con la información del cliente al día (art. 555-2 ET). |
| Certificados de Retención en la Fuente | Documentos que soporten el exceso de retenciones que generó el saldo a favor. |

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
- **answer length:** 2502 chars
- **latency:** 19773 ms

**Question:**

> Una SAS presentó la declaración del 2025 con beneficio de auditoría incremento del 36% (firmeza a 6 meses) y saldo a favor de $50 millones. El gerente está ocupado y dice que tramita la devolución "más adelante en el año". ¿Hasta cuándo puede esperar para pedirla? ¿Le aplica el plazo general de 2 años o algo distinto por estar bajo beneficio de auditoría?

**Answer (verbatim):**

**Respuestas directas**
- **¿Hasta cuándo puede esperar para pedirla?**
  - El plazo para solicitar la devolución de saldos a favor es de dos años, contados a partir de la fecha de vencimiento del término para declarar o desde la fecha de presentación de la declaración, lo que ocurra último (art. 854 ET).
  - En este caso, la declaración del 2025 se presentó con beneficio de auditoría. Si la declaración se presentó antes del vencimiento, el plazo de dos años para solicitar la devolución empezaría a correr desde la fecha de vencimiento original para declarar el periodo 2025. Si se presentó después del vencimiento, el plazo iniciaría desde la fecha de presentación.
- **¿Le aplica el plazo general de 2 años o algo distinto por estar bajo beneficio de auditoría?**
  - Sí, le aplica el plazo general de dos años establecido en el (art. 854 ET). El beneficio de auditoría (art. 689-3 ET) reduce el término de firmeza de la declaración, pero no modifica el plazo para solicitar la devolución de saldos a favor.

**Ruta sugerida**
1.  **Verificar fecha de presentación y vencimiento:** Confirmar la fecha exacta de presentación de la declaración del 2025 y la fecha de vencimiento original para ese periodo. Esto es clave para determinar el inicio del plazo de dos años para la solicitud de devolución.
2.  **Preparar solicitud de devolución:** Iniciar la preparación de los documentos y soportes necesarios para la solicitud de devolución del saldo a favor. No hay razón para demorar este proceso.
3.  **Presentar solicitud:** Presentar la solicitud de devolución ante la DIAN dentro del plazo de dos años.

**Riesgos y condiciones**
*   **Vencimiento del plazo:** El principal riesgo es que el gerente demore la solicitud y se venza el plazo de dos años, perdiendo el derecho a la devolución del saldo a favor.
*   **Firmeza de la declaración:** Aunque la declaración esté en firme por beneficio de auditoría (art. 689-3 ET), la DIAN puede revisar la solicitud de devolución para verificar la procedencia del saldo a favor.
*   **Requisitos de la solicitud:** La solicitud debe cumplir con todos los requisitos formales y sustanciales exigidos por la DIAN para evitar rechazos o requerimientos adicionales.

**Soportes clave**
*   Copia de la declaración de renta del año gravable 2025.
*   Certificado de existencia y representación legal de la SAS.
*   Poder especial, si la solicitud la presenta un apoderado.
*   Soportes contables que demuestren la existencia y procedencia del saldo a favor.

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
- **latency:** 7379 ms

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
- **answer length:** 1393 chars
- **latency:** 10746 ms

**Question:**

> Mi cliente tiene pérdidas acumuladas de $400 millones generadas en 2020, 2021 y 2022. En 2025 finalmente tuvo utilidad fiscal de $250 millones. ¿Puedo compensarle todo o hay algún límite porcentual anual? ¿Y debo compensar primero las más antiguas?

**Answer (verbatim):**

**Respuestas directas**
- **¿Puedo compensarle todo o hay algún límite porcentual anual?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.
- **¿Y debo compensar primero las más antiguas?**
  - Las sociedades pueden compensar las pérdidas fiscales con las rentas líquidas ordinarias que obtengan en los doce (12) períodos gravables siguientes (art. 147 ET).

**Ruta sugerida**
1. La sociedad compensa las pérdidas fiscales contra rentas líquidas ordinarias futuras. No se trasladan a los socios ni se tratan como un saldo a favor (art. 147 ET).
2. Las pérdidas fiscales se pueden compensar con las rentas líquidas ordinarias obtenidas en los doce (12) períodos gravables siguientes (arts. 147 y 808 ET).
3. La firmeza de la declaración que origina o compensa la pérdida fiscal debe medirse aparte, ya que es un término de revisión distinto a la mecánica de compensación (art. 147 ET).

**Riesgos y condiciones**
- El enfoque debe ser en la compensación de pérdidas fiscales en renta, no en la devolución o compensación de saldos a favor (art. 147 ET).
- El término de firmeza para declaraciones que originen o compensen pérdidas fiscales es de seis (6) años, no el término ordinario de tres (3) años (art. 147 ET).
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
- **answer length:** 1852 chars
- **latency:** 11040 ms

**Question:**

> Tengo un cliente que arrastra una pérdida del año 2014 que todavía no ha podido compensar. Adicional, en 2018 hubo una fusión donde mi cliente fue la sociedad absorbente. ¿Las pérdidas del 2014 sobreviven la fusión? ¿Y siguen siendo compensables hoy o ya se vencieron por el plazo? Hay reglas distintas para pérdidas pre-2017 y post-2017 y me genera dudas la transición.

**Answer (verbatim):**

**Respuestas directas**
- **¿Las pérdidas del 2014 sobreviven la fusión?**
  - La sociedad absorbente o resultante de un proceso de fusión puede compensar las pérdidas fiscales de la sociedad absorbida (art. 147 ET).
  - La compensación se realiza con las rentas líquidas ordinarias que obtenga la sociedad absorbente o resultante.
  - Es importante diferenciar la compensación de pérdidas fiscales en renta de la devolución o compensación de saldos a favor.
  - El término de firmeza para declaraciones que originen o compensen pérdidas fiscales es de seis años, no el término ordinario de tres años (art. 147 ET).
- **¿Y siguen siendo compensables hoy o ya se vencieron por el plazo?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

**Ruta sugerida**
1. La sociedad absorbente puede compensar las pérdidas fiscales de la sociedad absorbida (art. 147 ET).
2. Las pérdidas fiscales se compensan con las rentas líquidas ordinarias obtenidas en los doce períodos gravables siguientes (art. 147 ET).
3. El término de firmeza para la declaración que origina o compensa la pérdida fiscal es de seis años (art. 147 ET).

**Riesgos y condiciones**
- La compensación de pérdidas fiscales es un concepto distinto a la devolución o compensación de saldos a favor (art. 147 ET).
- El término de firmeza para declaraciones que originen o compensen pérdidas fiscales es de seis años, no de tres (art. 147 ET).
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
- **answer length:** 3635 chars
- **latency:** 15649 ms

**Question:**

> ¿Cuáles son los umbrales de patrimonio o ingresos a partir de los cuales una empresa colombiana queda obligada al régimen de precios de transferencia?

**Answer (verbatim):**

Aquí tienes el análisis sobre los umbrales de precios de transferencia:

### Respuestas directas

*   **¿Cuáles son los umbrales de patrimonio o ingresos a partir de los cuales una empresa colombiana queda obligada al régimen de precios de transferencia?**
    *   La obligación de aplicar el régimen de precios de transferencia se activa para contribuyentes del impuesto sobre la renta y complementarios que realicen operaciones con vinculados económicos del exterior o ubicados en zonas francas, siempre que cumplan con los siguientes umbrales:
        *   Patrimonio bruto fiscal a 31 de diciembre del año gravable anterior igual o superior a 100.000 UVT.
        *   Ingresos brutos fiscales del año gravable anterior iguales o superiores a 60.000 UVT.
        *   Operaciones con vinculados económicos del exterior o zonas francas que superen los 45.000 UVT en el año gravable.
        *   Operaciones con vinculados económicos del exterior o zonas francas que superen los 15.000 UVT en el año gravable, si se trata de operaciones de compraventa de bienes corporales, servicios, o cualquier otro tipo de operación.
    *   La cobertura quedó parcial.

### Ruta sugerida

1.  **Verificar umbrales:** Confirmar si la empresa cumple con los umbrales de patrimonio bruto e ingresos brutos fiscales del año gravable anterior.
2.  **Identificar operaciones:** Determinar si la empresa realizó operaciones con vinculados económicos del exterior o ubicados en zonas francas.
3.  **Cuantificar operaciones:** Sumar el valor de las operaciones con vinculados económicos del exterior o zonas francas para verificar si superan los umbrales específicos (45.000 UVT o 15.000 UVT según el tipo de operación).
4.  **Evaluar vinculación:** Confirmar la existencia de vinculación económica según lo establecido en el (art. 260-1 ET).
5.  **Preparar documentación:** En caso de cumplir los requisitos, preparar la documentación comprobatoria y el informe local de precios de transferencia.

### Riesgos y condiciones

*   **Sanciones por incumplimiento:** El incumplimiento de las obligaciones de precios de transferencia puede acarrear sanciones significativas por parte de la DIAN, incluyendo multas por no presentar la documentación o presentarla con errores (art. 260-10 ET).
*   **Ajustes de precios:** La DIAN puede realizar ajustes a los precios de las operaciones si considera que no se ajustan al principio de plena competencia, lo que podría generar mayores impuestos a pagar (art. 260-1 ET).
*   **Cambios normativos:** Es crucial estar al tanto de las actualizaciones en la normativa de precios de transferencia, ya que los umbrales y requisitos pueden modificarse anualmente.

### Soportes clave

*   **Estatuto Tributario (ET):**
    *   (art. 260-1 ET): Principio de plena competencia.
    *   (art. 260-2 ET): Ámbito de aplicación.
    *   (art. 260-3 ET): Criterios de vinculación.
    *   (art. 260-4 ET): Métodos para determinar el precio o margen de utilidad.
    *   (art. 260-5 ET): Documentación comprobatoria.
    *   (art. 260-9 ET): Declaración informativa.
    *   (art. 260-10 ET): Sanciones.
*   **Decreto Reglamentario:** Consultar el decreto reglamentario vigente que especifica los umbrales en UVT para cada año gravable.

| Requisito                                     | Umbral (UVT) |
| :-------------------------------------------- | :----------- |
| Patrimonio bruto fiscal (año gravable anterior) | >= 100.000   |
| Ingresos brutos fiscales (año gravable anterior) | >= 60.000    |
| Operaciones con vinculados (total)            | >= 45.000    |
| Operaciones con vinculados (tipo específico)  | >= 15.000    |

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
- **latency:** 18000 ms

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
- **latency:** 6347 ms

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
- **latency:** 7051 ms

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
- **answer length:** 2851 chars
- **latency:** 14082 ms

**Question:**

> Mi cliente persona natural tiene a 1 de enero de 2026: una casa donde vive avaluada en $1.800 millones, un apartamento que arrienda valorado en $900 millones, acciones en su SAS por $1.500 millones, vehículos por $200 millones y efectivo en bancos por $150 millones. ¿Tiene que declarar y pagar impuesto al patrimonio? ¿Qué se le excluye y a qué tarifa?

**Answer (verbatim):**

**Respuestas directas**
- **¿Tiene que declarar y pagar impuesto al patrimonio?**
  - El cliente debe declarar y pagar el impuesto al patrimonio si su patrimonio líquido a 1 de enero de 2026 supera las 72.000 UVT (art. 292-3 ET).
  - Para 2026, si la UVT se mantiene en $47.065 (valor 2024), el umbral sería de $3.400.680.000.
  - El patrimonio bruto del cliente es de $4.550 millones ($1.800M casa + $900M apartamento + $1.500M acciones + $200M vehículos + $150M efectivo).
  - Asumiendo que no tiene pasivos significativos que reduzcan el patrimonio líquido por debajo del umbral, el cliente estaría obligado a declarar y pagar el impuesto al patrimonio.

- **¿Qué se le excluye y a qué tarifa?**
  - **Exclusiones:**
    - La casa de habitación del contribuyente está excluida hasta 12.000 UVT (art. 295-1 ET). Para 2026, si la UVT se mantiene en $47.065, esto equivale a $564.780.000.
    - El valor de la casa de $1.800 millones excede este límite, por lo que la exclusión aplica solo hasta el tope.
  - **Base gravable y tarifa:**
    - La base gravable se determina restando las exclusiones del patrimonio líquido (art. 295-1 ET).
    - La tarifa aplicable es progresiva (art. 296 ET):
      | Patrimonio Líquido (UVT) | Tarifa Marginal | Impuesto |
      |---|---|---|
      | Desde | Hasta | | |
      | 72.000 | 122.000 | 0,5% | (Patrimonio Líquido en UVT - 72.000 UVT) * 0,5% |
      | 122.000 | En adelante | 1,0% | Impuesto calculado en el rango anterior + (Patrimonio Líquido en UVT - 122.000 UVT) * 1,0% |

**Ruta sugerida**
- Calcular el patrimonio líquido exacto a 1 de enero de 2026, considerando todos los activos y pasivos.
- Determinar el valor de la UVT para el año 2026, una vez sea publicada por la DIAN.
- Aplicar la exclusión de la casa de habitación hasta el límite de 12.000 UVT (art. 295-1 ET).
- Calcular la base gravable del impuesto al patrimonio.
- Aplicar la tarifa progresiva según el rango de patrimonio líquido (art. 296 ET) para determinar el impuesto a pagar.

**Riesgos y condiciones**
- La valoración de los activos debe ser precisa a 1 de enero de 2026. Para bienes inmuebles, se considera el costo fiscal (art. 277 ET). Para acciones, el costo fiscal (art. 272 ET).
- La existencia de pasivos puede reducir el patrimonio líquido y, por ende, la base gravable o incluso la obligación de declarar. Es crucial tener el detalle de los pasivos.
- La UVT para 2026 es una estimación basada en el valor de 2024. El valor definitivo puede variar y afectar los umbrales y cálculos.

**Soportes clave**
- Estatuto Tributario (ET):
  - Art. 292-3 ET: Sujetos pasivos del impuesto al patrimonio.
  - Art. 295-1 ET: Base gravable del impuesto al patrimonio.
  - Art. 296 ET: Tarifa del impuesto al patrimonio.
  - Art. 272 ET: Valor patrimonial de las acciones.
  - Art. 277 ET: Valor patrimonial de los bienes inmuebles.

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
- **answer length:** 3578 chars
- **latency:** 13787 ms

**Question:**

> Una clienta persona natural tiene patrimonio líquido de $4.200 millones, casi todo en acciones de una SAS productiva donde es socia mayoritaria. Me dice que escuchó que las acciones de empresas operativas se excluyen de la base. ¿Es cierto, parcial o totalmente? ¿Y qué pasa si parte de esas acciones las tiene a través de una sociedad de inversión personal en lugar de directamente?

**Answer (verbatim):**

**Respuestas directas**
- **¿Es cierto, parcial o totalmente?**
  - Las acciones en sociedades productivas no se excluyen de la base gravable del impuesto al patrimonio. El impuesto al patrimonio se calcula sobre el patrimonio líquido del contribuyente, sin que exista una exclusión específica para acciones de empresas operativas (art. 290 ET).
  - La base gravable del impuesto al patrimonio para personas naturales es el patrimonio líquido poseído al 1 de enero de cada año, que exceda las 72.000 UVT (art. 295-3 ET).
  - El valor patrimonial de las acciones se determina por su costo fiscal, ajustado por inflación cuando aplique, o por el valor intrínseco o de mercado, según las reglas del Estatuto Tributario (arts. 271 y 272 ET).

- **¿Y qué pasa si parte de esas acciones las tiene a través de una sociedad de inversión personal en lugar de directamente?**
  - Si las acciones se poseen a través de una sociedad de inversión personal, la persona natural no es la titular directa de las acciones. En este caso, el patrimonio de la persona natural incluiría la participación en la sociedad de inversión, no las acciones subyacentes.
  - La sociedad de inversión, si es una entidad diferente a la persona natural, sería la propietaria de las acciones y, por ende, la responsable de incluir su patrimonio en su propia declaración, si le aplica.
  - Es crucial determinar la naturaleza jurídica de la "sociedad de inversión personal" (e.g., sociedad anónima, SAS, fondo de inversión) y su régimen fiscal para establecer cómo afecta el patrimonio de la persona natural.

**Ruta sugerida**
1.  **Confirmar el valor patrimonial de las acciones:** Determinar el costo fiscal de las acciones de la SAS al 1 de enero del año gravable, según lo establecido en los artículos 271 y 272 del ET.
2.  **Calcular el patrimonio líquido:** Sumar todos los activos poseídos por la clienta al 1 de enero, incluyendo el valor patrimonial de las acciones, y restar los pasivos a la misma fecha (art. 290 ET).
3.  **Verificar el umbral:** Comparar el patrimonio líquido resultante con el umbral de 72.000 UVT para determinar si la clienta es sujeto pasivo del impuesto al patrimonio (art. 295-3 ET).
4.  **Analizar la estructura de la sociedad de inversión:** Si aplica, revisar los estatutos y la contabilidad de la sociedad de inversión para determinar la participación de la clienta y cómo se valora fiscalmente esa participación en su patrimonio.

**Riesgos y condiciones**
-   **Valoración de acciones:** La correcta valoración de las acciones es fundamental. Errores en el costo fiscal o en la aplicación de los ajustes pueden llevar a una base gravable incorrecta.
-   **Estructura de la sociedad de inversión:** La interposición de una sociedad de inversión puede generar complejidades adicionales en la determinación del patrimonio, especialmente si existen reglas de transparencia fiscal o si la sociedad es considerada una entidad controlada del exterior (ECE) para efectos de la tributación de la persona natural.
-   **Cambios normativos:** El impuesto al patrimonio ha sido objeto de modificaciones recientes. Es importante asegurar que se aplique la normativa vigente para el período gravable correspondiente.

**Soportes clave**
-   Certificado de existencia y representación legal de la SAS.
-   Extractos bancarios y demás soportes de activos y pasivos al 1 de enero del año gravable.
-   Declaraciones de renta de años anteriores de la clienta.
-   Escrituras de constitución y reformas de la SAS.
-   Si aplica, estatutos y contabilidad de la sociedad de inversión personal.

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
- **answer length:** 437 chars
- **latency:** 8753 ms

**Question:**

> Cuando una PYME importa mercancía y le paga al proveedor del exterior, ¿esa operación se tiene que canalizar a través del mercado cambiario regulado o la puede pagar como quiera?

**Answer (verbatim):**

**Ruta sugerida**
1.  **PASO 1 — Identificar si la PYME Requiere Canalización Obligatoria:** Determinar si la operación de importación y pago al proveedor del exterior debe canalizarse a través del mercado cambiario regulado. (arts. paso-a-paso-pr-ctico y posiciones-de-expertos ET).

**Riesgos y condiciones**
-   La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

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
- **answer length:** 666 chars
- **latency:** 10130 ms

**Question:**

> Mi cliente, una SAS importadora, le va a pagar $80.000 USD a un proveedor en Alemania por una máquina que importó. ¿Qué declaración de cambio le toca presentar, en qué momento y a través de quién? ¿Necesita abrir cuenta de compensación o puede hacerlo a través de su banco habitual?

**Answer (verbatim):**

**Respuestas directas**
- **¿Qué declaración de cambio le toca presentar, en qué momento y a través de quién?**
  - La declaración de cambio debe contener la información mínima establecida en el (art. 26-35 ET).
- **¿Necesita abrir cuenta de compensación o puede hacerlo a través de su banco habitual?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

**Ruta sugerida**
1. Presentar la declaración de cambio con el contenido mínimo requerido (art. 26-35 ET).

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

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
- **latency:** 12315 ms

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
- **answer length:** 1758 chars
- **latency:** 9825 ms

**Question:**

> ¿Qué empresas están obligadas a presentar el formato 2516 de conciliación fiscal y cuándo se entrega?

**Answer (verbatim):**

**Respuestas directas**

*   **¿Qué empresas están obligadas a presentar el formato 2516 de conciliación fiscal?**
    *   Están obligados los contribuyentes del impuesto sobre la renta y complementarios que, durante el año gravable, cumplan con los siguientes requisitos:
        *   Personas jurídicas y asimiladas.
        *   Personas naturales y asimiladas, así como los regímenes especiales, que en el año gravable anterior o en el año gravable en curso hayan obtenido ingresos brutos fiscales iguales o superiores a 45.000 UVT (Sección 11).

*   **¿Cuándo se entrega el formato 2516?**
    *   El formato 2516 se debe presentar en las mismas fechas de vencimiento establecidas para la declaración del impuesto sobre la renta y complementarios (Sección 11).

**Ruta sugerida**

1.  **Verificar ingresos brutos:** Determinar si los ingresos brutos fiscales del contribuyente en el año gravable anterior o en el año en curso superan las 45.000 UVT.
2.  **Identificar tipo de contribuyente:** Confirmar si el contribuyente es persona jurídica o asimilada, o persona natural y asimilada con ingresos superiores al tope.
3.  **Preparar formato 2516:** Diligenciar el formato 2516 de conciliación fiscal, asegurando la correcta correspondencia entre la información contable y fiscal.
4.  **Presentar en plazos:** Realizar la presentación del formato 2516 dentro de los plazos establecidos para la declaración de renta.

**Riesgos y condiciones**

*   La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

**Soportes clave**

*   **Sección 11 — Conciliación Fiscal (Formatos 2516 y 2517):** Este documento detalla los requisitos y el proceso para la presentación de la conciliación fiscal.

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
- **answer length:** 2168 chars
- **latency:** 16611 ms

**Question:**

> Mi cliente es una SAS Grupo 2 NIIF para PYMES con ingresos de $3.800 millones que aplica el modelo de revaluación en sus inmuebles. La revaluación contable subió el valor del edificio en $400 millones en 2025. ¿Cómo manejo eso en el 2516? ¿Es diferencia permanente o temporaria, qué efecto tiene en el patrimonio fiscal versus contable, y me toca registrar impuesto diferido?

**Answer (verbatim):**

**Respuestas directas**
- **¿Cómo manejo eso en el 2516?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.
- **¿Es diferencia permanente o temporaria, qué efecto tiene en el patrimonio fiscal versus contable, y me toca registrar impuesto diferido?**
  - La revaluación de inmuebles bajo NIIF para PYMES genera una diferencia temporaria. Fiscalmente, el valor del activo se mantiene al costo histórico o al costo ajustado por inflación (si aplica), sin reconocer la revaluación. Esto crea una diferencia entre el valor contable y el fiscal del activo.
  - El patrimonio bruto fiscal se determina por el total de bienes y derechos apreciables en dinero poseídos al cierre del período gravable (art. 261 ET). La revaluación contable no afecta el patrimonio fiscal, ya que este se basa en el costo fiscal del activo.
  - Sí, se debe registrar impuesto diferido. Al ser una diferencia temporaria, la revaluación contable del inmueble generará una base gravable mayor en el futuro (al momento de la venta o depreciación), lo que implica un impuesto diferido pasivo.

**Ruta sugerida**
- Para el Formato 2516, la diferencia de $400 millones por la revaluación del edificio se reporta como una diferencia temporaria en la sección de activos fijos.
- En la conciliación fiscal, el valor contable del edificio (incluyendo la revaluación) se ajusta para llegar al costo fiscal.
- Se debe calcular y registrar el impuesto diferido pasivo sobre la diferencia temporaria generada por la revaluación.

**Riesgos y condiciones**
- El principal riesgo es no reconocer correctamente la diferencia temporaria y el impuesto diferido, lo que podría llevar a inconsistencias en la declaración de renta y el patrimonio fiscal.
- Es crucial mantener la trazabilidad entre el valor contable y el valor fiscal del activo para futuras declaraciones y en caso de una revisión de la DIAN.

**Soportes clave**
- Dictamen de revaluación del inmueble.
- Registros contables que reflejan la revaluación.
- Cálculos del impuesto diferido.
- Artículos 261, 262 y 263 del Estatuto Tributario, que definen el patrimonio bruto y la posesión de bienes.

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
- **answer length:** 3929 chars
- **latency:** 17353 ms

**Question:**

> Una clienta tiene un contrato de arrendamiento de bodega que bajo NIIF 16 reconoció como activo por derecho de uso de $300 millones y un pasivo por arrendamiento de $290 millones. Fiscalmente entiendo que esas figuras no existen y que solo se deduce el canon pagado en el año. ¿Cómo concilio eso en el 2516, cómo afecta el patrimonio fiscal, y si más adelante la DIAN me hace comparación patrimonial cómo justifico la diferencia?

**Answer (verbatim):**

**Respuestas directas**

*   **¿Cómo concilio el reconocimiento del activo por derecho de uso y el pasivo por arrendamiento bajo NIIF 16 con la normativa fiscal en el formato 2516?**

    *   Fiscalmente, el activo por derecho de uso y el pasivo por arrendamiento no se reconocen. El tratamiento fiscal se limita a la deducción de los cánones de arrendamiento efectivamente pagados en el año gravable (art. 263 ET).
    *   En el formato 2516, la conciliación se realiza ajustando el patrimonio fiscal para eliminar el impacto de estos reconocimientos NIIF.

*   **¿Cómo afecta el patrimonio fiscal la diferencia entre el tratamiento NIIF 16 y el fiscal?**

    *   El patrimonio fiscal se determina por los bienes y derechos apreciables en dinero poseídos al cierre del año gravable (art. 261 ET).
    *   Dado que el activo por derecho de uso no es un bien poseído fiscalmente ni un derecho apreciable en dinero para efectos tributarios (art. 262 ET), no forma parte del patrimonio fiscal.
    *   El pasivo por arrendamiento tampoco se reconoce fiscalmente como una obligación que disminuya el patrimonio.
    *   La diferencia entre el patrimonio contable (NIIF) y el patrimonio fiscal se reflejará en la conciliación fiscal.

*   **Si más adelante la DIAN me hace comparación patrimonial, ¿cómo justifico la diferencia?**

    *   La justificación se basa en la diferencia de marcos normativos: NIIF para contabilidad y Estatuto Tributario para fiscalidad.
    *   Se debe demostrar que la diferencia patrimonial proviene del reconocimiento de activos y pasivos bajo NIIF 16 que no tienen correlato fiscal, y no de rentas no declaradas.
    *   La conciliación fiscal (formato 2516) es la herramienta principal para soportar estas diferencias.

**Ruta sugerida**

1.  **Determinación del Patrimonio Fiscal:**
    *   Para efectos fiscales, el activo por derecho de uso de $300 millones y el pasivo por arrendamiento de $290 millones no se incluyen en el patrimonio.
    *   El patrimonio fiscal se construye exclusivamente con los bienes y derechos apreciables en dinero que cumplen con los criterios del Estatuto Tributario (arts. 261, 262 y 263 ET).
2.  **Conciliación Fiscal (Formato 2516):**
    *   En el formato 2516, se debe realizar un ajuste para eliminar el efecto del activo por derecho de uso y el pasivo por arrendamiento del patrimonio contable para llegar al patrimonio fiscal.
    *   La deducción fiscal se limitará a los cánones de arrendamiento efectivamente pagados durante el periodo gravable.

**Riesgos y condiciones**

*   **Riesgo de desconocimiento de la deducción:** Si se intenta deducir la depreciación del activo por derecho de uso o los intereses implícitos del pasivo, la DIAN desconocerá estas deducciones por no estar soportadas en el ET. La deducción se limita al canon pagado.
*   **Riesgo en comparación patrimonial:** La DIAN podría cuestionar el incremento patrimonial si no se tiene una conciliación fiscal robusta que explique las diferencias entre el patrimonio contable (NIIF) y el fiscal.
*   **Condición clave:** Mantener una documentación clara y detallada de los contratos de arrendamiento y los cálculos NIIF 16, así como la conciliación fiscal, es fundamental para cualquier requerimiento de la DIAN.

**Soportes clave**

*   **Contrato de arrendamiento:** Documento base para el reconocimiento NIIF y la deducción fiscal del canon.
*   **Cálculos NIIF 16:** Detalle del reconocimiento del activo por derecho de uso y el pasivo por arrendamiento.
*   **Extractos bancarios y comprobantes de pago:** Para soportar los cánones de arrendamiento efectivamente pagados y deducidos fiscalmente.
*   **Formato 2516 – Conciliación Fiscal:** Es el soporte principal para justificar las diferencias entre el patrimonio contable y el fiscal.
*   **Estatuto Tributario:** Artículos 261, 262 y 263, que definen el patrimonio bruto, los derechos apreciables en dinero y la posesión fiscal.

**Citations (verbatim):**

  1. (no label) — doc_id='suin_1132325'
  2. (no label) — doc_id='CORE_ya_Arriba_LEYES_INVERSIONES_INCENTIVOS_consolidado_Ley-1429-2010.md'
  3. (no label) — doc_id='suin_1104445'
  4. (no label) — doc_id='CORE_ya_Arriba_RENTA_NORMATIVA_Normativa_20_Libro6_GMF.md'

---
