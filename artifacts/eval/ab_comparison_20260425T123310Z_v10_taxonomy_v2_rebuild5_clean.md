# A/B Evaluation: TEMA-first retrieval vs prior mode

**Run tag.** `v10_taxonomy_v2_rebuild5_clean`  
**Started.**   2026-04-25 7:33:10 AM (Bogotá)  ·  2026-04-25T12:33:10.271947+00:00 (UTC)  
**Completed.** 2026-04-25 7:36:03 AM (Bogotá)  ·  2026-04-25T12:36:03.210568+00:00 (UTC)  
**Git commit.** `2cebf9cd095e46217031909f08c135acf88462e2`

**Falkor baseline (pre-run).** TopicNode 41, TEMA edges 2361, ArticleNode 9160, SubTopicNode 87.

## Panel instructions (read first)

Every question below has TWO answer blocks, clearly labeled 
**[PRIOR MODE]** (legacy v4-era retrieval, baseline) and **[NEW MODE]** (v5 TEMA-first retrieval).

For each question, read both blocks and fill the `verdict:` field with ONE of:

- `new_better` — the NEW-mode answer is materially better for the reader
- `prior_better` — the PRIOR-mode answer is materially better
- `tie` — answers are equivalent in usefulness
- `both_wrong` — neither answers the question correctly
- `need_clarification` — the question is ambiguous / outside scope; no verdict

Add one short paragraph in `notes:` if you want to explain.
Do NOT edit the answer text or diagnostics blocks — the operator
uses those verbatim when aggregating.

---

## Q1 — a_renta_pj — single — S

**Query.** Colega, tengo un cliente SAS comercializadora con ingresos brutos de $3.000 millones en el AG 2025. Todas sus compras están soportadas con factura electrónica validada. ¿Cuánto puede deducir…

**Expected topic:** `declaracion_renta`  **Expected subtopic:** `deduccion_factura_electronica_1pct`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Ruta sugerida**
1. Verifica si el emisor estaba obligado a facturar electrónicamente y si hubo contingencia válida antes de aceptar el soporte (art. 616-1 ET).
2. Haz una revisión operativa del soporte antes de defenderlo fiscalmente (art. 616-1 ET).

**Riesgos y condiciones**
- No sustituyas la factura electrónica por cualquier soporte cuando la obligación sí existía (arts. 616-1 y 416 ET).
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

**Soportes clave**
- Así mismo, hacen parte del sistema de factura todos los documentos electrónicos que sean determinados por la Unid (arts. 616-1 y 416 ET).
- El sistema de facturación comprende la factura de venta y los documentos equivalentes (art. 616-1 ET).

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: facturacion_electronica
- tema_first_anchor_count: 0
- planner_query_mode: computation_chain
- effective_topic: facturacion_electronica
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 1847
- trace_id: 58d11f0f4ccd46c89a4a9c0c64c32aa4
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

**Ruta sugerida**
1. Verifica si el emisor estaba obligado a facturar electrónicamente y si hubo contingencia válida antes de aceptar el soporte (arts. 616-1 y 616 ET).
2. Si hubo contingencia, deja evidencia del evento y de la normalización posterior de la factura (arts. 616-1 y 616 ET).
3. Haz una revisión operativa del soporte antes de defenderlo fiscalmente (arts. 616 y 616-1 ET).

**Riesgos y condiciones**
- No sustituyas la factura electrónica por cualquier soporte cuando la obligación sí existía (arts. 616-1 y 616-2 ET).

**Soportes clave**
- Multa equivalente a hasta el 1% del valor total de la factura por cada mes o fracción de mes de retraso, sin exceder 12 meses (máximo 12% del valor de la factura) (arts. 616 y 2 ET).

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 3
- connected_article_count: 5
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: facturacion_electronica
- tema_first_anchor_count: 3
- planner_query_mode: computation_chain
- effective_topic: facturacion_electronica
- coherence_mode: shadow
- coherence_misaligned: False
- coherence_reason: primary_on_topic
- wall_ms: 6879
- trace_id: fc9320bd6c2b4b9492bd4ffac14dd54f
- seed_article_keys: ['616', '616-1', '616-2']

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q2 — a_renta_pj — multi — M

**Query.** Necesito ayuda con la TTD para un cliente SAS de comercio con las siguientes cifras del AG 2025: utilidad contable antes de impuestos $360 millones, diferencias permanentes (gastos no deducibles)…

**Sub-questions:**
  1. ¿Cómo calculo la TTD paso a paso?
  2. ¿Qué pasa si el resultado queda por debajo del 15%?
  3. ¿En qué renglón del Formulario 110 registro el Impuesto a Adicionar?

**Expected topic:** `declaracion_renta`  **Expected subtopic:** `ttd_tasa_tributacion_depurada`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: costos_deducciones_renta
- tema_first_anchor_count: 0
- planner_query_mode: computation_chain
- effective_topic: costos_deducciones_renta
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 1067
- trace_id: 8a076e3979d84231990d3dda58f142ff
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

Con la evidencia disponible todavía no alcanzo una recomendación operativa suficientemente confiable.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 3
- connected_article_count: 5
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: costos_deducciones_renta
- tema_first_anchor_count: 3
- planner_query_mode: computation_chain
- effective_topic: costos_deducciones_renta
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: primary_off_topic
- wall_ms: 7048
- trace_id: fadfa33028a04751b8489c7fb83de9db
- seed_article_keys: ['121', '122', '123']

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q3 — a_renta_pj — single — S

**Query.** Un cliente PJ tuvo un impuesto neto de renta de $153.000.000 en AG 2024 y estima un impuesto neto de $214.000.000 para AG 2025 (incluyendo el IA de TTD). ¿Puede acogerse al beneficio de auditoría…

**Expected topic:** `declaracion_renta`  **Expected subtopic:** `beneficio_auditoria`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: declaracion_renta
- tema_first_anchor_count: 0
- planner_query_mode: obligation_chain
- effective_topic: declaracion_renta
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 1228
- trace_id: d823e8503003498f97dcb43c90ac86c5
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

Con la evidencia disponible todavía no alcanzo una recomendación operativa suficientemente confiable.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 5
- connected_article_count: 5
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: declaracion_renta
- tema_first_anchor_count: 5
- planner_query_mode: obligation_chain
- effective_topic: declaracion_renta
- coherence_mode: shadow
- coherence_misaligned: False
- coherence_reason: primary_on_topic
- wall_ms: 10378
- trace_id: 46470ebd60c84b6fac0d7c2bfe44be8a
- seed_article_keys: ['100', '101', '102', '102-1', '102-2']

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q4 — a_renta_pj — multi — M

**Query.** Tengo una SAS comercializadora en su tercer año declarando renta. En AG 2024 el INR (incluyendo IA) fue de $164.200.000 y en AG 2025 estimo un INR de $195.000.000. Las retenciones practicadas…

**Sub-questions:**
  1. ¿Cómo calculo el anticipo por los dos procedimientos del Art. 807?
  2. ¿Cuál le conviene más al cliente?
  3. ¿Hay alguna forma de reducir el anticipo si el negocio va mal en 2026?

**Expected topic:** `declaracion_renta`  **Expected subtopic:** `anticipo_impuesto_renta`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: declaracion_renta
- tema_first_anchor_count: 0
- planner_query_mode: computation_chain
- effective_topic: declaracion_renta
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 873
- trace_id: d33065131f5141769cf8124a52abd4e8
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

Con la evidencia disponible todavía no alcanzo una recomendación operativa suficientemente confiable.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 3
- connected_article_count: 5
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: declaracion_renta
- tema_first_anchor_count: 3
- planner_query_mode: computation_chain
- effective_topic: declaracion_renta
- coherence_mode: shadow
- coherence_misaligned: False
- coherence_reason: primary_on_topic
- wall_ms: 6989
- trace_id: 0cd14ebec24a4415bfce4dfe8e1e09cd
- seed_article_keys: ['100', '101', '102']

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q5 — a_renta_pj — single — S

**Query.** Un cliente tiene un hotel nuevo en un municipio de menos de 200.000 habitantes, con renta líquida gravable de $150 millones en AG 2025. ¿Qué tarifa de renta le aplica y cuánto se ahorra frente…

**Expected topic:** `declaracion_renta`  **Expected subtopic:** `tarifa_hotelera_art240_par5`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: declaracion_renta
- tema_first_anchor_count: 0
- planner_query_mode: general_graph_research
- effective_topic: declaracion_renta
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 1019
- trace_id: 30668ea7984843b7b516caa46c90e953
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

Con la evidencia disponible todavía no alcanzo una recomendación operativa suficientemente confiable.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 3
- connected_article_count: 4
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: declaracion_renta
- tema_first_anchor_count: 3
- planner_query_mode: general_graph_research
- effective_topic: declaracion_renta
- coherence_mode: shadow
- coherence_misaligned: False
- coherence_reason: primary_on_topic
- wall_ms: 6808
- trace_id: 911fd18488704be5a118a415a8ad2f19
- seed_article_keys: ['100', '101', '102']

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q6 — b_iva — multi — M

**Query.** Tengo una SAS distribuidora de alimentos que vende productos gravados al 19% y también comercializa productos de la canasta familiar (excluidos de IVA). Los ingresos brutos del AG 2024 fueron…

**Sub-questions:**
  1. ¿Cuál es la periodicidad de declaración de IVA para 2026?
  2. ¿Cómo calculo el prorrateo del IVA descontable en los gastos comunes?

**Expected topic:** `iva`  **Expected subtopic:** `periodicidad_y_prorrateo`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: iva
- tema_first_anchor_count: 0
- planner_query_mode: general_graph_research
- effective_topic: iva
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 951
- trace_id: 4c9b7346a23e4a1fa67245cf822184f9
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

Con la evidencia disponible todavía no alcanzo una recomendación operativa suficientemente confiable.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 3
- connected_article_count: 4
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: iva
- tema_first_anchor_count: 3
- planner_query_mode: general_graph_research
- effective_topic: iva
- coherence_mode: shadow
- coherence_misaligned: False
- coherence_reason: primary_on_topic
- wall_ms: 6805
- trace_id: 6a4ff3e5e31645f1b3476bbef434637f
- seed_article_keys: ['420', '420-1', '421']

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q7 — b_iva — single — S

**Query.** Mi cliente PYME le vendió mercancía gravada a un gran contribuyente por $10.000.000 más IVA. ¿Cómo funciona la retención de IVA en esa operación y cuánto recibe efectivamente mi cliente?

**Expected topic:** `iva`  **Expected subtopic:** `reteiva_grandes_contribuyentes`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: iva
- tema_first_anchor_count: 0
- planner_query_mode: computation_chain
- effective_topic: iva
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 1056
- trace_id: 2aabd470d1b145568913d7cfb21b6ae2
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

Con la evidencia disponible todavía no alcanzo una recomendación operativa suficientemente confiable.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 3
- connected_article_count: 5
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: iva
- tema_first_anchor_count: 3
- planner_query_mode: computation_chain
- effective_topic: iva
- coherence_mode: shadow
- coherence_misaligned: False
- coherence_reason: primary_on_topic
- wall_ms: 6969
- trace_id: cb97d67ade994eada878a2e02247fcc5
- seed_article_keys: ['420', '420-1', '421']

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q8 — c_retencion_fuente — multi — M

**Query.** Tengo que calcular la retención en la fuente por salarios para tres empleados con estos sueldos mensuales en 2026: (a) $3.000.000, (b) $12.000.000, y (c) $20.000.000. Todos tienen las deducciones…

**Sub-questions:**
  1. ¿Cuánto le retengo al empleado con salario $3.000.000?
  2. ¿Cuánto le retengo al empleado con salario $12.000.000?
  3. ¿Cuánto le retengo al empleado con salario $20.000.000?

**Expected topic:** `retencion_en_la_fuente`  **Expected subtopic:** `retencion_salarial_tabla_art383`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: retencion_en_la_fuente
- tema_first_anchor_count: 0
- planner_query_mode: computation_chain
- effective_topic: retencion_en_la_fuente
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: zero_evidence_for_router_topic
- wall_ms: 900
- trace_id: 98110fa9e6d54075a9f53c0c29e89160
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

**Ruta sugerida**
1. Toma como punto de partida el texto vigente hoy del art. 115 ET para definir el tratamiento en renta del impuesto pagado.

**Riesgos y condiciones**
- No dupliques el mismo valor como descuento tributario y como costo o gasto dentro de la misma declaración (arts. 368 y 368-1 ET).

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 3
- connected_article_count: 5
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: retencion_en_la_fuente
- tema_first_anchor_count: 3
- planner_query_mode: computation_chain
- effective_topic: retencion_en_la_fuente
- coherence_mode: shadow
- coherence_misaligned: False
- coherence_reason: primary_on_topic
- wall_ms: 6835
- trace_id: 718f981f8e32414e9ffa93720f17ae75
- seed_article_keys: ['368', '368-1', '368-2']

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q9 — c_retencion_fuente — single — S

**Query.** Voy a contratar a un consultor independiente (persona natural declarante de renta) por honorarios de $8.000.000 mensuales. ¿Cuánto debo retenerle en la fuente por concepto de honorarios?

**Expected topic:** `retencion_en_la_fuente`  **Expected subtopic:** `retencion_honorarios`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: declaracion_renta
- tema_first_anchor_count: 0
- planner_query_mode: definition_chain
- effective_topic: declaracion_renta
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 1091
- trace_id: 4e57fd936d1c44af948fa085b423d587
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

Con la evidencia disponible todavía no alcanzo una recomendación operativa suficientemente confiable.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 3
- connected_article_count: 4
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: declaracion_renta
- tema_first_anchor_count: 3
- planner_query_mode: definition_chain
- effective_topic: declaracion_renta
- coherence_mode: shadow
- coherence_misaligned: False
- coherence_reason: primary_on_topic
- wall_ms: 6943
- trace_id: bf701d6c5f4d4c5c89ae8277b1d87973
- seed_article_keys: ['100', '101', '102']

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q10 — d_facturacion_electronica — multi — M

**Query.** Un cliente nuevo acaba de constituir una SAS y necesita habilitarse para facturar electrónicamente. (a) ¿Qué opciones tiene para habilitarse? (b) ¿Cuántas resoluciones necesita tener activas?…

**Sub-questions:**
  1. ¿Qué opciones tiene para habilitarse?
  2. ¿Cuántas resoluciones necesita tener activas?
  3. ¿Qué hago si el sistema se cae y no puedo transmitir facturas a la DIAN?

**Expected topic:** `facturacion_electronica`  **Expected subtopic:** `habilitacion_y_operacion`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

No pude clasificar esta pregunta con confianza dentro del marco normativo que Lia cubre hoy. Revísala manualmente antes de responder al cliente; posibles causas: terminología ambigua, dominio fuera de cobertura, o pregunta multi-tema que requiere desagregar en consultas más específicas.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: None
- coherence_mode: None
- coherence_misaligned: None
- coherence_reason: None
- wall_ms: 0
- trace_id: 94b8d25d00f14587a6e7de3f5540f2f8
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

No pude clasificar esta pregunta con confianza dentro del marco normativo que Lia cubre hoy. Revísala manualmente antes de responder al cliente; posibles causas: terminología ambigua, dominio fuera de cobertura, o pregunta multi-tema que requiere desagregar en consultas más específicas.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: None
- coherence_mode: None
- coherence_misaligned: None
- coherence_reason: None
- wall_ms: 0
- trace_id: d55d699883d0490a86b31719fa3249d5
- seed_article_keys: []

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q11 — d_facturacion_electronica — single — S

**Query.** Un cliente me devolvió mercancía por un defecto de calidad. Ya le había emitido factura electrónica por $5.000.000 + IVA. ¿Cómo manejo la nota crédito electrónica?

**Expected topic:** `facturacion_electronica`  **Expected subtopic:** `notas_credito_electronica`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Ruta sugerida**
1. Verifica si el emisor estaba obligado a facturar electrónicamente y si hubo contingencia válida antes de aceptar el soporte.
2. Haz una revisión operativa del soporte antes de defenderlo fiscalmente.

**Riesgos y condiciones**
- No sustituyas la factura electrónica por cualquier soporte cuando la obligación sí existía (arts. 416 y 879 ET).
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: facturacion_electronica
- tema_first_anchor_count: 0
- planner_query_mode: computation_chain
- effective_topic: facturacion_electronica
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 834
- trace_id: f1d8c149169c421dab53459594df240c
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

**Ruta sugerida**
1. Verifica si el emisor estaba obligado a facturar electrónicamente y si hubo contingencia válida antes de aceptar el soporte (arts. 616-1 y 616 ET).
2. Si hubo contingencia, deja evidencia del evento y de la normalización posterior de la factura (arts. 616-1 y 616 ET).
3. Haz una revisión operativa del soporte antes de defenderlo fiscalmente (arts. 616 y 616-1 ET).

**Riesgos y condiciones**
- No sustituyas la factura electrónica por cualquier soporte cuando la obligación sí existía (arts. 616-1 y 616-2 ET).

**Soportes clave**
- Multa equivalente a hasta el 1% del valor total de la factura por cada mes o fracción de mes de retraso, sin exceder 12 meses (máximo 12% del valor de la factura) (arts. 616 y 2 ET).

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 3
- connected_article_count: 5
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: facturacion_electronica
- tema_first_anchor_count: 3
- planner_query_mode: computation_chain
- effective_topic: facturacion_electronica
- coherence_mode: shadow
- coherence_misaligned: False
- coherence_reason: primary_on_topic
- wall_ms: 6669
- trace_id: fb83710937a8498295b81187ba2421e8
- seed_article_keys: ['616', '616-1', '616-2']

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q12 — e_rst — multi — M

**Query.** Tengo un cliente SAS de servicios profesionales (consultoría) con 3 socios personas naturales residentes, ingresos brutos de $600 millones en AG 2025, y todos los clientes son diversos…

**Sub-questions:**
  1. ¿Puede inscribirse en el RST?
  2. ¿Qué tarifa consolidada le aplicaría?
  3. ¿Le conviene más que el régimen ordinario?

**Expected topic:** `regimen_simple`  **Expected subtopic:** `elegibilidad_y_tarifa`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: sector_telecomunicaciones
- tema_first_anchor_count: 0
- planner_query_mode: general_graph_research
- effective_topic: sector_telecomunicaciones
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 1029
- trace_id: 0e6a660611f54a11a71e2b87c86cc45d
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: sector_telecomunicaciones
- tema_first_anchor_count: 0
- planner_query_mode: general_graph_research
- effective_topic: sector_telecomunicaciones
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 1179
- trace_id: b439e04d0a64439db2d990e2ffad6091
- seed_article_keys: []

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q13 — e_rst — single — S

**Query.** Mi cliente ya está inscrito en el RST (Grupo 2 — actividad comercial mayorista). ¿Cómo funcionan los anticipos bimestrales y con qué formulario los declara?

**Expected topic:** `regimen_simple`  **Expected subtopic:** `anticipos_bimestrales_rst`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: regimen_simple
- tema_first_anchor_count: 0
- planner_query_mode: general_graph_research
- effective_topic: regimen_simple
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 850
- trace_id: b5f6c3dde8b9460c968a454739f5b15e
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

Con la evidencia disponible todavía no alcanzo una recomendación operativa suficientemente confiable.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 3
- connected_article_count: 4
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: regimen_simple
- tema_first_anchor_count: 3
- planner_query_mode: general_graph_research
- effective_topic: regimen_simple
- coherence_mode: shadow
- coherence_misaligned: False
- coherence_reason: primary_on_topic
- wall_ms: 6710
- trace_id: 6f5b53293aa344abab878a8d82a11600
- seed_article_keys: ['903', '904', '905']

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q14 — f_nomina_laboral — multi — M

**Query.** Tengo una PYME manufacturera con 8 empleados, todos con salarios inferiores a 10 SMLMV. (a) ¿Qué aportes parafiscales debo pagar y cuáles están exonerados? (b) ¿Cuáles son los plazos de pago…

**Sub-questions:**
  1. ¿Qué aportes parafiscales debo pagar y cuáles están exonerados?
  2. ¿Cuáles son los plazos de pago de la PILA según el NIT?

**Expected topic:** `laboral`  **Expected subtopic:** `parafiscales_exoneracion_art114_1`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Respuestas directas**
- **Tengo una PYME manufacturera con 8 empleados, todos con salarios inferiores a 10 SMLMV. (a) ¿Qué aportes parafiscales debo pagar y cuáles están exonerados?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.
- **(b) ¿Cuáles son los plazos de pago…?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: laboral
- tema_first_anchor_count: 0
- planner_query_mode: general_graph_research
- effective_topic: laboral
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 1051
- trace_id: 3285b46601274615b5ed5f3611b1fe67
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

**Respuestas directas**
- **Tengo una PYME manufacturera con 8 empleados, todos con salarios inferiores a 10 SMLMV. (a) ¿Qué aportes parafiscales debo pagar y cuáles están exonerados?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.
- **(b) ¿Cuáles son los plazos de pago…?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 3
- connected_article_count: 4
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: laboral
- tema_first_anchor_count: 3
- planner_query_mode: general_graph_research
- effective_topic: laboral
- coherence_mode: shadow
- coherence_misaligned: False
- coherence_reason: primary_on_topic
- wall_ms: 6708
- trace_id: 75e51554b97d4389933d6609f1356462
- seed_article_keys: ['127-132', '16-19', '186']

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q15 — f_nomina_laboral — single — S

**Query.** Acabo de escuchar que la Ley 2466 trae cambios importantes en materia laboral. ¿Cuáles son los cambios más críticos que debo implementar en las PYMEs que asesoro y qué fechas límite tengo?

**Expected topic:** `laboral`  **Expected subtopic:** `reforma_laboral_ley_2466`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: laboral
- tema_first_anchor_count: 0
- planner_query_mode: reform_chain
- effective_topic: laboral
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 972
- trace_id: 29711a45eb50487b9ff193379d30bbd0
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

Con la evidencia disponible todavía no alcanzo una recomendación operativa suficientemente confiable.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 3
- connected_article_count: 4
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: laboral
- tema_first_anchor_count: 3
- planner_query_mode: reform_chain
- effective_topic: laboral
- coherence_mode: shadow
- coherence_misaligned: False
- coherence_reason: primary_on_topic
- wall_ms: 6652
- trace_id: ef112a2db2d5468c9b5f79387b8c1fa3
- seed_article_keys: ['127-132', '16-19', '186']

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q16 — f_nomina_laboral — multi — M

**Query.** Un cliente quiere contratar una recepcionista por medio tiempo (4 horas diarias, 5 días a la semana). (a) ¿Cómo se calcula el salario y las prestaciones? (b) ¿Qué opciones tengo para la cotización…

**Sub-questions:**
  1. ¿Cómo se calcula el salario y las prestaciones?
  2. ¿Qué opciones tengo para la cotización a seguridad social?
  3. ¿Cuánto le cuesta al empleador en total?

**Expected topic:** `laboral`  **Expected subtopic:** `trabajo_tiempo_parcial`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Respuestas directas**
- **Un cliente quiere contratar una recepcionista por medio tiempo (4 horas diarias, 5 días a la semana). (a) ¿Cómo se calcula el salario y las prestaciones?**
  - La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.
- **(b) ¿Qué opciones tengo para la cotización…?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: laboral
- tema_first_anchor_count: 0
- planner_query_mode: general_graph_research
- effective_topic: laboral
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 883
- trace_id: f81d9afa521747adad147f5d36bbffe2
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

**Respuestas directas**
- **Un cliente quiere contratar una recepcionista por medio tiempo (4 horas diarias, 5 días a la semana). (a) ¿Cómo se calcula el salario y las prestaciones?**
  - "Todo trabajador tiene derecho a que anualmente se le conceda un período mínimo de descanso remunerado de quince días hábiles, que puede ser disfrutado por el trabajador en los términos.
  - "Medidas para el uso adecuado de la tercerización y la intermediación laboral" Cambios principales introducidos por Ley 2466.
  - Los contribuyentes que lleven libros de contabilidad por el sistema de causación, deducen las cesantías consolidadas que dentro del año o período gravable se hayan causado.
- **(b) ¿Qué opciones tengo para la cotización…?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 3
- connected_article_count: 4
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: laboral
- tema_first_anchor_count: 3
- planner_query_mode: general_graph_research
- effective_topic: laboral
- coherence_mode: shadow
- coherence_misaligned: False
- coherence_reason: primary_on_topic
- wall_ms: 6467
- trace_id: 9ef0a99083014d528065829afff47559
- seed_article_keys: ['127-132', '16-19', '186']

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q17 — f_nomina_laboral — single — S

**Query.** ¿A partir de qué ingreso debe un empleado aportar al Fondo de Solidaridad Pensional y cuánto le corresponde?

**Expected topic:** `laboral`  **Expected subtopic:** `fondo_solidaridad_pensional`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: laboral
- tema_first_anchor_count: 0
- planner_query_mode: obligation_chain
- effective_topic: laboral
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 964
- trace_id: 3749e45b37804743860cea6e33e03feb
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

Con la evidencia disponible todavía no alcanzo una recomendación operativa suficientemente confiable.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 5
- connected_article_count: 5
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: laboral
- tema_first_anchor_count: 5
- planner_query_mode: obligation_chain
- effective_topic: laboral
- coherence_mode: shadow
- coherence_misaligned: False
- coherence_reason: primary_on_topic
- wall_ms: 9681
- trace_id: 81991ec196974d72ba6315af09b49467
- seed_article_keys: ['127-132', '16-19', '186', '187', '192']

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q18 — g_niif_mercantil — multi — M

**Query.** Tengo un cliente PYME Grupo 2 que compró maquinaria por $120 millones en enero de 2025. (a) ¿Cuáles son las vidas útiles para depreciación fiscal vs. NIIF? (b) ¿Cómo calculo la diferencia…

**Sub-questions:**
  1. ¿Cuáles son las vidas útiles para depreciación fiscal vs. NIIF?
  2. ¿Cómo calculo la diferencia temporaria para el impuesto diferido?
  3. ¿Dónde registro esta diferencia en el Formato 2516?

**Expected topic:** `estados_financieros_niif`  **Expected subtopic:** `depreciacion_fiscal_vs_niif`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Respuestas directas**
- **Tengo un cliente PYME Grupo 2 que compró maquinaria por $120 millones en enero de 2025. (a) ¿Cuáles son las vidas útiles para depreciación fiscal vs. NIIF?**
  - La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.
  - Los contratos de arrendamiento que se celebren a partir del 1° de enero de 2017, se someten a la.
- **(b) ¿Cómo calculo la diferencia…?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: estados_financieros_niif
- tema_first_anchor_count: 0
- planner_query_mode: computation_chain
- effective_topic: estados_financieros_niif
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 963
- trace_id: 6ceb47d142c84eefb1f3d593d3b63ac6
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

**Respuestas directas**
- **Tengo un cliente PYME Grupo 2 que compró maquinaria por $120 millones en enero de 2025. (a) ¿Cuáles son las vidas útiles para depreciación fiscal vs. NIIF?**
  - La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.
  - Los contratos de arrendamiento que se celebren a partir del 1° de enero de 2017, se someten a la.
- **(b) ¿Cómo calculo la diferencia…?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: estados_financieros_niif
- tema_first_anchor_count: 0
- planner_query_mode: computation_chain
- effective_topic: estados_financieros_niif
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 1113
- trace_id: 2dc4700788a04135bc5d6b2c5bfa3f4f
- seed_article_keys: []

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q19 — g_niif_mercantil — single — S

**Query.** ¿Cuáles son las obligaciones mercantiles que una SAS debe cumplir en el primer trimestre del año y qué pasa si no las cumple?

**Expected topic:** `comercial_societario`  **Expected subtopic:** `renovacion_rues_y_asamblea`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: comercial_societario
- tema_first_anchor_count: 0
- planner_query_mode: obligation_chain
- effective_topic: comercial_societario
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 927
- trace_id: 312871e922d049a39a9440c02e65605a
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

Con la evidencia disponible todavía no alcanzo una recomendación operativa suficientemente confiable.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 5
- connected_article_count: 5
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: comercial_societario
- tema_first_anchor_count: 5
- planner_query_mode: obligation_chain
- effective_topic: comercial_societario
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: primary_off_topic
- wall_ms: 9856
- trace_id: 63f88dfab7be4da3b9d8b7d709c94645
- seed_article_keys: ['10', '12', '167', '170', '178']

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q20 — h_procedimiento_tributario — multi — M

**Query.** Un cliente persona jurídica se atrasó 3 meses en la presentación de la declaración de renta del AG 2024. El impuesto a cargo fue de $45.000.000. (a) ¿Cómo calculo la sanción por extemporaneidad?…

**Sub-questions:**
  1. ¿Cómo calculo la sanción por extemporaneidad?
  2. ¿Puedo reducir la sanción con el Art. 640 ET?
  3. ¿Cuál es la sanción mínima?

**Expected topic:** `regimen_sancionatorio`  **Expected subtopic:** `extemporaneidad_y_reduccion`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: regimen_sancionatorio_extemporaneidad
- tema_first_anchor_count: 0
- planner_query_mode: obligation_chain
- effective_topic: regimen_sancionatorio_extemporaneidad
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 1041
- trace_id: f04afbc6bd38425aa9638a88d674699b
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: regimen_sancionatorio_extemporaneidad
- tema_first_anchor_count: 0
- planner_query_mode: obligation_chain
- effective_topic: regimen_sancionatorio_extemporaneidad
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 1250
- trace_id: c53bc79d43dc41a999036d19819fcdbd
- seed_article_keys: []

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q21 — h_procedimiento_tributario — single — S

**Query.** ¿En qué fecha queda en firme la declaración de renta del AG 2022 para una persona jurídica que la presentó oportunamente el 10 de mayo de 2023, sin beneficio de auditoría?

**Expected topic:** `firmeza_declaraciones`  **Expected subtopic:** `firmeza_ordinaria_art714`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Ruta sugerida**
1. Trabaja el caso sobre AG 2022; valida que base, porcentaje y soportes correspondan a esa vigencia (art. 416 ET).

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: firmeza_declaraciones
- tema_first_anchor_count: 0
- planner_query_mode: obligation_chain
- effective_topic: firmeza_declaraciones
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 1479
- trace_id: 47024f0a773f4436aca8a7a596a408b9
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

**Ruta sugerida**
1. Trabaja el caso sobre AG 2022; valida que base, porcentaje y soportes correspondan a esa vigencia (art. 416 ET).

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: firmeza_declaraciones
- tema_first_anchor_count: 0
- planner_query_mode: obligation_chain
- effective_topic: firmeza_declaraciones
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 1744
- trace_id: 80cbadce6dec41de9444de7cb75a0018
- seed_article_keys: []

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q22 — h_procedimiento_tributario — multi — M

**Query.** Un cliente PJ tiene un saldo a favor de $85.000.000 en su declaración de renta del AG 2025 (originado por exceso de retenciones). (a) ¿Qué opciones tiene para manejar ese saldo? (b) ¿Cuánto tiempo…

**Sub-questions:**
  1. ¿Qué opciones tiene para manejar ese saldo?
  2. ¿Cuánto tiempo toma la devolución?
  3. ¿Necesita garantía bancaria?

**Expected topic:** `devoluciones_saldos_a_favor`  **Expected subtopic:** `procedimiento_devolucion`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Respuestas directas**
- **Un cliente PJ tiene un saldo a favor de $85.000.000 en su declaración de renta del AG 2025 (originado por exceso de retenciones). (a) ¿Qué opciones tiene para manejar ese saldo?**
  - La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.
  - El caso viene planteado para AG 2025; valida que plazos, declaración base y soportes correspondan exactamente a ese período.
  - Artículo corregido por el artículo 3 del Decreto 939 de 2017.
- **(b) ¿Cuánto tiempo…?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: devoluciones_saldos_a_favor
- tema_first_anchor_count: 0
- planner_query_mode: computation_chain
- effective_topic: devoluciones_saldos_a_favor
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 1056
- trace_id: fb2d052d32274b9ca24691ddfad9b5ea
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

**Respuestas directas**
- **Un cliente PJ tiene un saldo a favor de $85.000.000 en su declaración de renta del AG 2025 (originado por exceso de retenciones). (a) ¿Qué opciones tiene para manejar ese saldo?**
  - La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.
  - El caso viene planteado para AG 2025; valida que plazos, declaración base y soportes correspondan exactamente a ese período.
  - Artículo corregido por el artículo 3 del Decreto 939 de 2017.
- **(b) ¿Cuánto tiempo…?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: devoluciones_saldos_a_favor
- tema_first_anchor_count: 0
- planner_query_mode: computation_chain
- effective_topic: devoluciones_saldos_a_favor
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 1263
- trace_id: 3aca21efeb4b4492a51a4cbce4e84da5
- seed_article_keys: []

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q23 — h_procedimiento_tributario — single — S

**Query.** ¿Cuáles son los umbrales para estar obligado a presentar información exógena del AG 2025 y cuáles son los plazos de vencimiento para 2026?

**Expected topic:** `informacion_exogena`  **Expected subtopic:** `umbrales_y_plazos_exogena`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Riesgos y condiciones**
- Fortalece el expediente con pruebas del negocio real, no solo con el documento principal.
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: informacion_exogena
- tema_first_anchor_count: 0
- planner_query_mode: obligation_chain
- effective_topic: informacion_exogena
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 841
- trace_id: 4e5ee190b89c4968b5d03043e28cb6f8
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

**Riesgos y condiciones**
- Fortalece el expediente con pruebas del negocio real, no solo con el documento principal.
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: informacion_exogena
- tema_first_anchor_count: 0
- planner_query_mode: obligation_chain
- effective_topic: informacion_exogena
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 1058
- trace_id: 819d987766f445f595309f6bf3257ac0
- seed_article_keys: []

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q24 — i_impuestos_especiales — multi+cross_topic — M

**Query.** Un cliente PYME tiene movimientos bancarios mensuales de $200 millones y opera en Bogotá en actividad comercial. (a) ¿Cómo puede optimizar el GMF (4×1000)? (b) ¿El ICA de Bogotá es deducible…

**Sub-questions:**
  1. ¿Cómo puede optimizar el GMF (4×1000)?
  2. ¿El ICA de Bogotá es deducible en renta?
  3. ¿Cuánto vale la tarifa de ICA para comercio en Bogotá?

**Expected topic:** `gravamen_movimiento_financiero_4x1000`  **Expected subtopic:** `optimizacion_gmf_y_deduccion_ica`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Respuestas directas**
- **Un cliente PYME tiene movimientos bancarios mensuales de $200 millones y opera en Bogotá en actividad comercial. (a) ¿Cómo puede optimizar el GMF (4×1000)?**
  - La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.
- **(b) ¿El ICA de Bogotá es deducible…?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: gravamen_movimiento_financiero_4x1000
- tema_first_anchor_count: 0
- planner_query_mode: computation_chain
- effective_topic: gravamen_movimiento_financiero_4x1000
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 1012
- trace_id: 98b39f00841042fcb5cd3b5be3ac0569
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

**Respuestas directas**
- **Un cliente PYME tiene movimientos bancarios mensuales de $200 millones y opera en Bogotá en actividad comercial. (a) ¿Cómo puede optimizar el GMF (4×1000)?**
  - Créase como un nuevo impuesto, a partir del primero (1o.) de enero del año 2001, el Gravamen a los Movimientos Financieros, a cargo de los usuar.
  - El hecho generador del Gravamen a los Movimientos Financieros lo constituye la realización de las transacciones financieras, mediante las cuales.
- **(b) ¿El ICA de Bogotá es deducible…?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

**Ruta sugerida**
1. Toma como punto de partida el texto vigente hoy del art. 115 ET para definir el tratamiento en renta del impuesto pagado.

**Riesgos y condiciones**
- No dupliques el mismo valor como descuento tributario y como costo o gasto dentro de la misma declaración (arts. 870 y 871 ET).

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 3
- connected_article_count: 5
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: gravamen_movimiento_financiero_4x1000
- tema_first_anchor_count: 3
- planner_query_mode: computation_chain
- effective_topic: gravamen_movimiento_financiero_4x1000
- coherence_mode: shadow
- coherence_misaligned: False
- coherence_reason: primary_on_topic
- wall_ms: 7105
- trace_id: 35621414c9674752ba684bafa256f3f6
- seed_article_keys: ['870', '871', '872']

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q25 — i_impuestos_especiales — single — S

**Query.** Un socio de una PYME que asesoro tiene un patrimonio líquido de $4.000 millones al 1 de enero de 2026. ¿Está obligado a declarar impuesto al patrimonio y cuánto le correspondería pagar?

**Expected topic:** `impuesto_patrimonio_personas_naturales`  **Expected subtopic:** `umbral_y_tarifas_patrimonio_pn`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: impuesto_patrimonio_personas_naturales
- tema_first_anchor_count: 0
- planner_query_mode: obligation_chain
- effective_topic: impuesto_patrimonio_personas_naturales
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 1062
- trace_id: 78f2cb37a3ff4bf58432569c7b96317a
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: impuesto_patrimonio_personas_naturales
- tema_first_anchor_count: 0
- planner_query_mode: obligation_chain
- effective_topic: impuesto_patrimonio_personas_naturales
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 1224
- trace_id: 97c8a4698a5747a9992439a6eea8e99f
- seed_article_keys: []

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q26 — i_impuestos_especiales — multi — M

**Query.** Una SAS con utilidad contable de $500 millones en AG 2025 quiere distribuir dividendos a sus 2 socios personas naturales residentes (50% cada uno). (a) ¿Cómo depuro la utilidad para determinar…

**Sub-questions:**
  1. ¿Cómo depuro la utilidad para determinar la parte gravada y no gravada?
  2. ¿Cuánto le retengo a cada socio?

**Expected topic:** `dividendos_y_distribucion_utilidades`  **Expected subtopic:** `depuracion_y_retencion_dividendos`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: dividendos_y_distribucion_utilidades
- tema_first_anchor_count: 0
- planner_query_mode: general_graph_research
- effective_topic: dividendos_y_distribucion_utilidades
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 866
- trace_id: d25b04ba3d7b4342997a1cafc9aa792d
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: dividendos_y_distribucion_utilidades
- tema_first_anchor_count: 0
- planner_query_mode: general_graph_research
- effective_topic: dividendos_y_distribucion_utilidades
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 1086
- trace_id: ead5aa7c421f45969a5154c53f1db49c
- seed_article_keys: []

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q27 — j_compliance_especiales — single — S

**Query.** ¿Mi cliente PYME de comercio con activos de $3.000 millones está obligado a implementar SAGRILAFT o PTEE?

**Expected topic:** `sagrilaft_ptee`  **Expected subtopic:** `clasificacion_umbrales_pyme`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: sagrilaft_ptee
- tema_first_anchor_count: 0
- planner_query_mode: obligation_chain
- effective_topic: sagrilaft_ptee
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 772
- trace_id: 706aa6ada87642bb8626af0ec9074f32
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: sagrilaft_ptee
- tema_first_anchor_count: 0
- planner_query_mode: obligation_chain
- effective_topic: sagrilaft_ptee
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 985
- trace_id: 60eacccc1bb44a8b8820545e4700ea9c
- seed_article_keys: []

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q28 — j_compliance_especiales — multi — M

**Query.** Un cliente quiere montar una empresa nueva en un municipio ZOMAC. (a) ¿Qué tarifas de renta le aplican y por cuánto tiempo? (b) ¿Qué requisitos de inversión y empleo debe cumplir? (c) ¿Cuándo…

**Sub-questions:**
  1. ¿Qué tarifas de renta le aplican y por cuánto tiempo?
  2. ¿Qué requisitos de inversión y empleo debe cumplir?
  3. ¿Cuándo se acaba el beneficio?

**Expected topic:** `zonas_francas`  **Expected subtopic:** `zomac_incentivos_tarifas`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Respuestas directas**
- **¿Qué tarifas de renta le aplican y por cuánto tiempo?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.
- **¿Qué requisitos de inversión y empleo debe cumplir?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: zonas_francas
- tema_first_anchor_count: 0
- planner_query_mode: obligation_chain
- effective_topic: zonas_francas
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 1114
- trace_id: 64c2e6bdcd964d3e97f5e625af7796cc
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

**Respuestas directas**
- **¿Qué tarifas de renta le aplican y por cuánto tiempo?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.
- **¿Qué requisitos de inversión y empleo debe cumplir?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

**Riesgos y condiciones**
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: zonas_francas
- tema_first_anchor_count: 0
- planner_query_mode: obligation_chain
- effective_topic: zonas_francas
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 1314
- trace_id: 82346b9389034a25a0dc1e9c75e5cc88
- seed_article_keys: []

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q29 — j_compliance_especiales — single — S

**Query.** Mi cliente PJ tiene pérdidas fiscales acumuladas de $200 millones originadas en el AG 2020. ¿Hasta cuándo puede compensarlas y cómo afecta eso la TTD?

**Expected topic:** `perdidas_fiscales_art147`  **Expected subtopic:** `compensacion_art147_y_ttd`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Ruta sugerida**
1. Trabaja el caso sobre AG 2020; valida que base, porcentaje y soportes correspondan a esa vigencia (art. 240 ET).

**Riesgos y condiciones**
- REMISIÓN DE DEUDAS TRIBUTARIAS "Se autoriza la remisión total de capital, intereses y sanciones de deudas tributarias generadas hasta el 31 de diciembre de 2019 para contribuyentes clasificados en sector (arts. 17 y 260-11 ET).
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: perdidas_fiscales_art147
- tema_first_anchor_count: 0
- planner_query_mode: general_graph_research
- effective_topic: perdidas_fiscales_art147
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 868
- trace_id: c93340b844714db5a7a07caa773db7e1
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

**Ruta sugerida**
1. Trabaja el caso sobre AG 2020; valida que base, porcentaje y soportes correspondan a esa vigencia (art. 240 ET).

**Riesgos y condiciones**
- REMISIÓN DE DEUDAS TRIBUTARIAS "Se autoriza la remisión total de capital, intereses y sanciones de deudas tributarias generadas hasta el 31 de diciembre de 2019 para contribuyentes clasificados en sector (arts. 17 y 260-11 ET).
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: perdidas_fiscales_art147
- tema_first_anchor_count: 0
- planner_query_mode: general_graph_research
- effective_topic: perdidas_fiscales_art147
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 1143
- trace_id: 37462301b0a040e48c20a36a9cdc3118
- seed_article_keys: []

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Q30 — j_compliance_especiales — multi — M

**Query.** Un colega me pregunta en qué casos la firma del contador es obligatoria en las declaraciones tributarias de una PJ y qué responsabilidades asumo al firmar. (a) ¿Cuándo es obligatoria mi firma?…

**Sub-questions:**
  1. ¿Cuándo es obligatoria mi firma?
  2. ¿Qué certifico implícitamente al firmar?
  3. ¿Qué sanciones me pueden imponer?

**Expected topic:** `obligaciones_profesionales_contador`  **Expected subtopic:** `firma_contador_y_responsabilidad`

---

### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`

**Riesgos y condiciones**
- REMISIÓN DE DEUDAS TRIBUTARIAS "Se autoriza la remisión total de capital, intereses y sanciones de deudas tributarias generadas hasta el 31 de diciembre de 2019 para contribuyentes clasificados en sectores de economía campe (arts. 17 y 641 ET).
- La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente (art. 641 ET).

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: off
- tema_first_topic_key: obligaciones_profesionales_contador
- tema_first_anchor_count: 0
- planner_query_mode: obligation_chain
- effective_topic: obligaciones_profesionales_contador
- coherence_mode: shadow
- coherence_misaligned: True
- coherence_reason: chunks_off_topic
- wall_ms: 884
- trace_id: f16eecada60047ebbba7e0c159026f4d
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

**Ruta sugerida**
1. Antes de corregir, define si el ajuste aumenta el impuesto o reduce el saldo a favor, porque eso cambia el mecanismo, el plazo y la sanción (arts. 588 y 714-1 ET).
2. Si el saldo a favor cambia por ajustes, corrige primero la declaración antes de mover el trámite frente a la DIAN (arts. 50 y 588 ET).
3. Si el cliente está usando beneficio de auditoría, mide ese impacto antes de firmar cualquier corrección (art. 714-1 ET).

**Riesgos y condiciones**
- No uses la lógica del art. 588 cuando en realidad la corrección aumenta el saldo a favor o disminuye el valor a pagar.
- No mezcles una devolución con una declaración todavía inconsistente o pendiente de corregir (art. 714-1 ET).
- Recuerda que una corrección a favor reinicia el término de revisión de la DIAN desde la fecha de la corrección (arts. 714-1 y 588 ET).

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 1
- connected_article_count: 5
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: obligaciones_profesionales_contador
- tema_first_anchor_count: 1
- planner_query_mode: obligation_chain
- effective_topic: obligaciones_profesionales_contador
- coherence_mode: shadow
- coherence_misaligned: False
- coherence_reason: primary_on_topic
- wall_ms: 3478
- trace_id: 3bad20f21e10421a9b57814d5ac871a9
- seed_article_keys: ['714-1']

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

## Aggregate (filled by operator after panel review)

```yaml
totals:
  new_better:
  prior_better:
  tie:
  both_wrong:
  need_clarification:
decision:           # flip_to_on | hold | rollback
decision_reason:    # one-paragraph justification citing specific qids
signed_off_by:
signed_off_at_bogota:
```

