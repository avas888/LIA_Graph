# A/B Evaluation: TEMA-first retrieval vs prior mode

**Run tag.** `v6_rebuild`  
**Started.**   2026-04-24 1:39:02 PM (Bogotá)  ·  2026-04-24T18:39:02.257003+00:00 (UTC)  
**Completed.** 2026-04-24 1:42:20 PM (Bogotá)  ·  2026-04-24T18:42:20.134398+00:00 (UTC)  
**Git commit.** `343f7ee4f67d05fcdeb76d9fb68ac79471d296b9`

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
- wall_ms: 2124
- trace_id: 4fe94a6a5a724f51a24f934ccede2b33
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
- tema_first_topic_key: facturacion_electronica
- tema_first_anchor_count: 3
- planner_query_mode: computation_chain
- effective_topic: facturacion_electronica
- wall_ms: 7722
- trace_id: d01b68f68a224b8fb709bbb14dadcf99
- seed_article_keys: []

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
- wall_ms: 1208
- trace_id: fbe2b697e374475aa19bf29d02bd5c53
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
- tema_first_topic_key: costos_deducciones_renta
- tema_first_anchor_count: 0
- planner_query_mode: computation_chain
- effective_topic: costos_deducciones_renta
- wall_ms: 1293
- trace_id: 5141f74bafc640c7b4b67d3a51d81134
- seed_article_keys: []

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
- wall_ms: 1330
- trace_id: d887ca1fe91d486cb0c1a208e8875520
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
- wall_ms: 11428
- trace_id: a11e76a91827443a8312be5789354e3a
- seed_article_keys: []

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
- wall_ms: 1114
- trace_id: 923d77dfc0f641c0b582d3dbf8871854
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

Detecté un desajuste entre la clasificación de tu pregunta (tema: declaracion_renta) y los artículos que encontré en el grafo (dominan el tema: laboral). Para evitar darte una recomendación autoritativa sobre el tema equivocado, prefiero que confirmes manualmente o reformules la consulta.

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
- effective_topic: declaracion_renta
- wall_ms: 7545
- trace_id: 5bb7949d26de4a189739d1d51ada38c0
- seed_article_keys: []

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
- wall_ms: 1615
- trace_id: 8def5210610845f9b7e933c5527889da
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
- wall_ms: 7797
- trace_id: 447c39136e2d458e9c538e6711096b18
- seed_article_keys: []

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
- wall_ms: 1230
- trace_id: a551f494cf914c74851a43353af0bb3f
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
- wall_ms: 7711
- trace_id: 1cd2015d0739426db93c6d8a8aab9060
- seed_article_keys: []

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
- wall_ms: 1262
- trace_id: 367727e3dfdc422e887cefa840552c17
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

Detecté un desajuste entre la clasificación de tu pregunta (tema: iva) y los artículos que encontré en el grafo (dominan el tema: retencion_en_la_fuente). Para evitar darte una recomendación autoritativa sobre el tema equivocado, prefiero que confirmes manualmente o reformules la consulta.

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
- effective_topic: iva
- wall_ms: 8091
- trace_id: 10de61d520f145b98246713dfc31005a
- seed_article_keys: []

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
- wall_ms: 1183
- trace_id: 789f5d1e12074d018601346eb3176f16
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
- tema_first_topic_key: retencion_en_la_fuente
- tema_first_anchor_count: 3
- planner_query_mode: computation_chain
- effective_topic: retencion_en_la_fuente
- wall_ms: 7673
- trace_id: adabd6715a62420e839b8a7b22149c6b
- seed_article_keys: []

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
- wall_ms: 1354
- trace_id: 39ddaa0ac87a4a62881caecb40819361
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

Detecté un desajuste entre la clasificación de tu pregunta (tema: declaracion_renta) y los artículos que encontré en el grafo (dominan el tema: laboral). Para evitar darte una recomendación autoritativa sobre el tema equivocado, prefiero que confirmes manualmente o reformules la consulta.

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
- effective_topic: declaracion_renta
- wall_ms: 7791
- trace_id: 7b77d8e29a334ee1ad664f1205fd77ce
- seed_article_keys: []

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
- wall_ms: 0
- trace_id: 1b6adc063c1e40218aa1e83e5b734eb7
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
- wall_ms: 0
- trace_id: ed84a8b06cbe4ffa817dc1bbea61b3fe
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
- wall_ms: 1234
- trace_id: bad9dbc2f8e6433e8d1921820f77f49c
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

**Riesgos y condiciones**
- Son responsables por el impuesto y las sanciones todos los agentes de retención, incluidos aquellos, que aún sin tener el carácter de contribuyen (arts. 516 y 514 ET).

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
- wall_ms: 7563
- trace_id: 9aaebf31ca474205b5038e883dd61c17
- seed_article_keys: []

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
- tema_first_topic_key: sector_medio_ambiente
- tema_first_anchor_count: 0
- planner_query_mode: general_graph_research
- effective_topic: sector_medio_ambiente
- wall_ms: 1330
- trace_id: abafb2fd6a3343e89f5ee74eeb096622
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
- tema_first_topic_key: sector_medio_ambiente
- tema_first_anchor_count: 0
- planner_query_mode: general_graph_research
- effective_topic: sector_medio_ambiente
- wall_ms: 1305
- trace_id: 14b10bb45ce045b4be3467f2b5157033
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
- wall_ms: 936
- trace_id: 0280af9412814338b877db432c859d0d
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
- wall_ms: 7631
- trace_id: 7a8230db3944480d958039ba1940d281
- seed_article_keys: []

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
- wall_ms: 1248
- trace_id: 3fdc0b1263bf4943b2fb11cb82b20553
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
- wall_ms: 7541
- trace_id: 12bfd9b3a18642729f15d2eca6bf65ad
- seed_article_keys: []

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
- wall_ms: 1381
- trace_id: 98c188b0fc7d45cd8370fcea17abde12
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
- wall_ms: 7616
- trace_id: 3e469ed9bf364c83a3f5e9414856ef30
- seed_article_keys: []

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
- wall_ms: 1083
- trace_id: e5c4feafa9e64dd29cf0c41fbccefacd
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
- wall_ms: 7308
- trace_id: d0f9877b742b4e488cb6be5df433773c
- seed_article_keys: []

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
- wall_ms: 1579
- trace_id: c91f332cbc10498695271e58a35a0058
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
- wall_ms: 10843
- trace_id: a955aa5cde42420bbc7c4adf9f609744
- seed_article_keys: []

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
- wall_ms: 1226
- trace_id: bb2edefb0d3c4d07b8a14ac658a83ed6
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
- wall_ms: 1205
- trace_id: 807f0ab2a4344a43a90fd846c91d30d0
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
- wall_ms: 1077
- trace_id: 49c8792c15424cec88e676059f54c26a
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
- wall_ms: 11320
- trace_id: b97b33a9cc554cd8887163a0e20d5fce
- seed_article_keys: []

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
- wall_ms: 1292
- trace_id: 0e0515cf62d64042a519e1745d504949
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
- wall_ms: 1462
- trace_id: 1c5040c0791d4e83bde8580778c86d5a
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
- wall_ms: 1657
- trace_id: 7d01b0f4aad849669799bfbb4da3952e
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
- wall_ms: 1933
- trace_id: ecf00666603341c7b37a5e8b44c97b75
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
- wall_ms: 1196
- trace_id: 5eca10cd17624f4496a8d8181e4ff4c6
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
- wall_ms: 1418
- trace_id: 53e12c5aa6de423ba5c82298b7a01fdb
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
- wall_ms: 970
- trace_id: 91bfb537ec88459294fea7b01c4ce2d4
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
- wall_ms: 1193
- trace_id: cb4c68e9c38d4cf2afe3d0f59692859c
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
- wall_ms: 1141
- trace_id: 3a689113564d4862a77c1819f8ed15d2
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
- wall_ms: 7908
- trace_id: 9bfa7010926745b3a1b83d57024dbc9a
- seed_article_keys: []

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
- wall_ms: 1385
- trace_id: 4ee86ec14169401d98bdbca261072b5b
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
- wall_ms: 1434
- trace_id: ead8c8e7bb864fc9bca8a2b40ddff160
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

**Expected topic:** `dividendos_utilidades`  **Expected subtopic:** `depuracion_y_retencion_dividendos`

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
- tema_first_topic_key: dividendos_utilidades
- tema_first_anchor_count: 0
- planner_query_mode: general_graph_research
- effective_topic: dividendos_utilidades
- wall_ms: 988
- trace_id: bb12ae7d1d5246d2b0bfea02757b6a02
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
- tema_first_topic_key: dividendos_utilidades
- tema_first_anchor_count: 0
- planner_query_mode: general_graph_research
- effective_topic: dividendos_utilidades
- wall_ms: 1295
- trace_id: 26ede9707ae64ebf8845e833b566162c
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
- wall_ms: 1704
- trace_id: 10c8ce9680be4086b35a3d44c9bdf6bd
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

Con la evidencia disponible todavía no alcanzo una recomendación operativa suficientemente confiable.

<details><summary>Diagnostics</summary>

- retrieval_backend: supabase
- graph_backend: falkor_live
- primary_article_count: 1
- connected_article_count: 5
- related_reform_count: 0
- tema_first_mode: on
- tema_first_topic_key: sagrilaft_ptee
- tema_first_anchor_count: 1
- planner_query_mode: obligation_chain
- effective_topic: sagrilaft_ptee
- wall_ms: 5191
- trace_id: 3f949fa656a34c97a0de4e1a2ec346c5
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
- wall_ms: 1878
- trace_id: 364dc15a4adb4ba89d7637962a5fdd15
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
- wall_ms: 1884
- trace_id: 1316e7d98b0b455e9445262468ea1c79
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
1. Trabaja el caso sobre AG 2020; valida que base, porcentaje y soportes correspondan a esa vigencia (art. 416 ET).
2. La regla matriz del art. 147 ET es que la sociedad compensa pérdidas fiscales contra rentas líquidas ordinarias futuras; no las traslada a los socios ni las trata como un saldo a favor.
3. Si además te preocupa la firmeza, mídela aparte: una cosa es la mecánica de compensación y otra el término de revisión de esa pérdida.

**Riesgos y condiciones**
- No cierres la posición solo con la palabra 'compensación': aquí el problema principal es pérdidas fiscales en renta, no devolución o compensación de saldos a favor.
- No leas la firmeza con la regla ordinaria de 3 años si la declaración origina o compensa pérdidas: en ese frente el expediente debe pensarse a 6 años.
- REMISIÓN DE DEUDAS TRIBUTARIAS "Se autoriza la remisión total de capital, intereses y sanciones de deudas tributarias generadas hasta el 31 de diciembre de 2019 para contribuyentes clasificados en sector (arts. 17 y 260-11 ET).

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
- wall_ms: 1226
- trace_id: da82de2f01284cfba6a328f0619ef54a
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

**Ruta sugerida**
1. Trabaja el caso sobre AG 2020; valida que base, porcentaje y soportes correspondan a esa vigencia (art. 416 ET).
2. La regla matriz del art. 147 ET es que la sociedad compensa pérdidas fiscales contra rentas líquidas ordinarias futuras; no las traslada a los socios ni las trata como un saldo a favor.
3. Si además te preocupa la firmeza, mídela aparte: una cosa es la mecánica de compensación y otra el término de revisión de esa pérdida.

**Riesgos y condiciones**
- No cierres la posición solo con la palabra 'compensación': aquí el problema principal es pérdidas fiscales en renta, no devolución o compensación de saldos a favor.
- No leas la firmeza con la regla ordinaria de 3 años si la declaración origina o compensa pérdidas: en ese frente el expediente debe pensarse a 6 años.
- REMISIÓN DE DEUDAS TRIBUTARIAS "Se autoriza la remisión total de capital, intereses y sanciones de deudas tributarias generadas hasta el 31 de diciembre de 2019 para contribuyentes clasificados en sector (arts. 17 y 260-11 ET).

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
- wall_ms: 1366
- trace_id: 8f1ff5510fe146a8a27916205ea5bfeb
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
- wall_ms: 1224
- trace_id: 4ef9a80a183e41c897a6b351e9fee0b8
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
- wall_ms: 4361
- trace_id: 62e30656c88b4a5d9ae53d99c8ad0335
- seed_article_keys: []

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

