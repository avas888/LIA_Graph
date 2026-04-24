# A/B Evaluation: TEMA-first retrieval vs prior mode

**Run tag.** `v5_tema_first_vs_prior_live`  
**Started.**   2026-04-24 7:33:05 AM (Bogotá)  ·  2026-04-24T12:33:05.861689+00:00 (UTC)  
**Completed.** 2026-04-24 7:35:28 AM (Bogotá)  ·  2026-04-24T12:35:28.169887+00:00 (UTC)  
**Git commit.** `3bfe686eb4a77be1ce582a6eda51b4b257df1135`

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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: costos_deducciones_renta
- wall_ms: 1011
- trace_id: 05d614604caf4c55a002cd8f37bf9464
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: costos_deducciones_renta
- wall_ms: 961
- trace_id: 6892483ec5f74a4a9735ad29dad4249c
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
- trace_id: 7cf1d87b084d433794178526d2eca43d
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
- trace_id: 4a1b3234cf154bb3b920997fcf1dccf7
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: sector_medio_ambiente
- wall_ms: 962
- trace_id: f4259b566b7d4304b4450caf7d09c708
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: sector_medio_ambiente
- wall_ms: 2210
- trace_id: 3094759cc8f2452aa2c9188d7a09fcff
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: estados_financieros_niif
- wall_ms: 865
- trace_id: 8c35c4f2afe1442db0e372128887dfdc
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: estados_financieros_niif
- wall_ms: 940
- trace_id: 1a6a50948b924dbda3b5ccb79eb67e2a
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

**Expected topic:** `obligaciones_mercantiles`  **Expected subtopic:** `renovacion_rues_y_asamblea`

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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: comercial_societario
- wall_ms: 713
- trace_id: e1827d9e80a74f059cc221dba6fc8f2c
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: comercial_societario
- wall_ms: 868
- trace_id: d68dd147c95f4f778cadcd6d705cf636
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: informacion_exogena
- wall_ms: 827
- trace_id: de2a1147fa894a80ab46fe9a9ef51c2b
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: informacion_exogena
- wall_ms: 2328
- trace_id: 393ca472a3574da1a91666879dd6da33
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

**Expected topic:** `impuesto_patrimonio`  **Expected subtopic:** `umbral_y_tarifas_patrimonio_pn`

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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: impuesto_patrimonio_personas_naturales
- wall_ms: 1011
- trace_id: 93f051d7bc0e49a09ddf159826b6a1ab
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: impuesto_patrimonio_personas_naturales
- wall_ms: 946
- trace_id: c3c47c49c9a2456d82c744be225d48ab
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

**Expected topic:** `dividendos`  **Expected subtopic:** `depuracion_y_retencion_dividendos`

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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: dividendos_utilidades
- wall_ms: 668
- trace_id: 3f8a35ee6ab04409a3c55d59e86adff4
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: dividendos_utilidades
- wall_ms: 854
- trace_id: 486a9bd952ea4dabb4e9feb19618df0c
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: sagrilaft_ptee
- wall_ms: 546
- trace_id: 17f3c7fb1ac94a79bd7d73506dce2b6e
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

**Ruta sugerida**
1. Antes de corregir, define si el ajuste aumenta el impuesto o reduce el saldo a favor, porque eso cambia el mecanismo, el plazo y la sanción (art. 148 ET).

**Riesgos y condiciones**
- No uses la lógica del art. 588 cuando en realidad la corrección aumenta el saldo a favor o disminuye el valor a pagar.

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
- effective_topic: sagrilaft_ptee
- wall_ms: 2996
- trace_id: ec58e5ced4324ccf994b4b75aafb5f87
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: zonas_francas
- wall_ms: 1056
- trace_id: b217dce7ee6f42faa0e363c9df6c0b6d
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: zonas_francas
- wall_ms: 998
- trace_id: d709f3f48127474d88cdfd0b02d5e182
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

**Expected topic:** `perdidas_fiscales`  **Expected subtopic:** `compensacion_art147_y_ttd`

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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: perdidas_fiscales_art147
- wall_ms: 661
- trace_id: 2b0807262deb4ce489d4f64bd016f950
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: perdidas_fiscales_art147
- wall_ms: 863
- trace_id: 148001537f074df4885b5d8ddcdde106
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: obligaciones_profesionales_contador
- wall_ms: 672
- trace_id: 759672fc9c114e2bab39eafe269fee14
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

**Ruta sugerida**
1. Si el cliente está usando beneficio de auditoría, mide ese impacto antes de firmar cualquier corrección (art. 689-3 ET).
2. Calcula la firmeza como una decisión del caso, no como una nota final de compliance (arts. 714-1 y 714 ET).

**Riesgos y condiciones**
- Una corrección que baja el incremento exigido puede hacer que el cliente pierda el beneficio de auditoría y vuelva a una firmeza más larga (art. 689-3 ET).
- No confundas plazo para corregir con término de firmeza: que la declaración siga abierta a revisión no siempre significa que todavía puedas corregir voluntariamente (arts. 714 y 714-1 ET).

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
- effective_topic: obligaciones_profesionales_contador
- wall_ms: 3277
- trace_id: ede932c58b6d4f4aaa77402a7fc30a38
- seed_article_keys: []

</details>

---

**Panel verdict block**

```yaml
verdict:          # new_better | prior_better | tie | both_wrong | need_clarification
notes:            # free text, one paragraph max
```

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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: facturacion_electronica
- wall_ms: 1544
- trace_id: f97f5a3aa3a24fdab3ef6f3d45e0db16
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

Con la evidencia disponible todavía no alcanzo una recomendación operativa suficientemente confiable.

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
- effective_topic: facturacion_electronica
- wall_ms: 6138
- trace_id: d846f730e1cc40ba8215490f47a2a208
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: declaracion_renta
- wall_ms: 1357
- trace_id: a138fe48ec7840fa943993fdcc9731f2
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

Con la evidencia disponible todavía no alcanzo una recomendación operativa suficientemente confiable.

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
- wall_ms: 9304
- trace_id: d1318612fcbe4795b56d9c6e20371e8b
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: declaracion_renta
- wall_ms: 952
- trace_id: 5dafd3b6e7af4c78a64abe5aebaaeca8
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
- wall_ms: 6116
- trace_id: de1dfee2ede7479da7259b9bddb7fc9f
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: declaracion_renta
- wall_ms: 1041
- trace_id: 3f98a2a2f814489f8539f85913b3b99d
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

Con la evidencia disponible todavía no alcanzo una recomendación operativa suficientemente confiable.

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
- wall_ms: 6259
- trace_id: 8b474db8ddc9494896d30f13fcc6b6e0
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: iva
- wall_ms: 888
- trace_id: 926b83bb80f14127a8dcef3204f45b78
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

Con la evidencia disponible todavía no alcanzo una recomendación operativa suficientemente confiable.

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
- wall_ms: 5895
- trace_id: 152459724ccd453eb78922946ff62eb6
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: iva
- wall_ms: 1019
- trace_id: d79f0b30b0d74b75a08fbe078fa1c8e0
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
- wall_ms: 6336
- trace_id: fc1dfe28e78e438aafaffc29be4fa2e2
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: retencion_en_la_fuente
- wall_ms: 838
- trace_id: b3b2fa4f6a304e71ad0c99cd1dfdb2de
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

Con la evidencia disponible todavía no alcanzo una recomendación operativa suficientemente confiable.

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
- effective_topic: retencion_en_la_fuente
- wall_ms: 6095
- trace_id: 093d28681a734fc8aa077f070408b0f1
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: declaracion_renta
- wall_ms: 1075
- trace_id: 284429ed03d94ef1acd679653c821961
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
- wall_ms: 6013
- trace_id: f3e36fd67cc1411e9e8ebe7532495f05
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: facturacion_electronica
- wall_ms: 835
- trace_id: 3368bc0163c9413aa5d31b5c803e25a9
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

**Riesgos y condiciones**
- Son responsables por el impuesto y las sanciones todos los agentes de retención, incluidos aquellos, que aún sin tener el carácter de contribuyen (arts. 516 y 514 ET).

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
- effective_topic: facturacion_electronica
- wall_ms: 5926
- trace_id: 06340a9fd1364d808ca65e10579f752b
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: regimen_simple
- wall_ms: 831
- trace_id: 9983aa20a8d44140b4ab5f23f530d4df
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

Con la evidencia disponible todavía no alcanzo una recomendación operativa suficientemente confiable.

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
- effective_topic: regimen_simple
- wall_ms: 6230
- trace_id: 99430d7690e24e15bd043f48d418e1d4
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: laboral
- wall_ms: 1023
- trace_id: c9c022fce7eb41c1859bae3619868260
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
- primary_article_count: 0
- connected_article_count: 0
- related_reform_count: 0
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: laboral
- wall_ms: 6012
- trace_id: f5a3fb8454384dc3bc632f1d3c1b1537
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: laboral
- wall_ms: 1068
- trace_id: 181dcd8b5d124947a8989040c7055cc9
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

Con la evidencia disponible todavía no alcanzo una recomendación operativa suficientemente confiable.

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
- effective_topic: laboral
- wall_ms: 5992
- trace_id: 61f8b8cfaf444e22b155df79bf85289a
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: laboral
- wall_ms: 857
- trace_id: 50c7b007166842a6a8f3239fd999ebe7
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

**Respuestas directas**
- **Un cliente quiere contratar una recepcionista por medio tiempo (4 horas diarias, 5 días a la semana). (a) ¿Cómo se calcula el salario y las prestaciones?**
  - "Todo trabajador tiene derecho a que anualmente se le conceda un período mínimo de descanso remunerado de quince días hábiles, que puede ser disfrutado por el trabajador en los términos.
  - "Medidas para el uso adecuado de la tercerización y la intermediación laboral" Cambios principales introducidos por Ley 2466.
  - Artículo derogado por el artículo 376 de la Ley 1819 de 2016.
  - Para los propósitos de esta ley se entiende por biocombustibles de origen vegetal o animal para uso en motores diesel aquel combustible líquido o gaseoso que ha sido obtenido de un vegetal o animal que se puede emplear e.
- **(b) ¿Qué opciones tengo para la cotización…?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

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
- effective_topic: laboral
- wall_ms: 6078
- trace_id: e31f85ae666642e98ce4c3355fe3aa02
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: laboral
- wall_ms: 979
- trace_id: 192afa4a29ce41959e5b053faedb7ac9
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

Con la evidencia disponible todavía no alcanzo una recomendación operativa suficientemente confiable.

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
- effective_topic: laboral
- wall_ms: 9122
- trace_id: 2f3d7ff7ed09474bb187ecac979decc5
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: declaracion_renta
- wall_ms: 1076
- trace_id: 3d50b45cfcca49f29f1a838e5075660a
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

Con la evidencia disponible todavía no alcanzo una recomendación operativa suficientemente confiable.

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
- wall_ms: 9058
- trace_id: 6a363a8596a94e1bb163b1d5a6b96bc7
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: declaracion_renta
- wall_ms: 1507
- trace_id: 394d30469f6d46f1847ec59a5aad9580
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

**Ruta sugerida**
1. Trabaja el caso sobre AG 2022; valida que base, porcentaje y soportes correspondan a esa vigencia (arts. 109 y 113 ET).

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
- wall_ms: 9568
- trace_id: 76fcac5ed0ef4ba695bcf04ce9d5f4bb
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: declaracion_renta
- wall_ms: 1129
- trace_id: ce97e8535cd840e79e21b678af912769
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

**Respuestas directas**
- **Un cliente PJ tiene un saldo a favor de $85.000.000 en su declaración de renta del AG 2025 (originado por exceso de retenciones). (a) ¿Qué opciones tiene para manejar ese saldo?**
  - El caso viene planteado para AG 2025; valida que plazos, declaración base y soportes correspondan exactamente a ese período.
  - Los contribuyentes que lleven libros de contabilidad por el sistema de causación, deducen las cesantías consolidadas que dentro del año o período gravable se hayan causado y reconocido irrevo.
  - Son deducibles, siempre y cuando cumplan con los requisitos previstos en la ley, los intereses por deudas durante el respectivo período gravab.
- **(b) ¿Cuánto tiempo…?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

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
- wall_ms: 6294
- trace_id: b05a7a44df9a448f8daa3869058ee49f
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
- tema_first_mode: None
- tema_first_topic_key: None
- tema_first_anchor_count: None
- planner_query_mode: None
- effective_topic: gravamen_movimiento_financiero_4x1000
- wall_ms: 1026
- trace_id: 6fdb8f96eb32433eb0ddfd23a99371fd
- seed_article_keys: []

</details>

---

### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`

**Respuestas directas**
- **Un cliente PYME tiene movimientos bancarios mensuales de $200 millones y opera en Bogotá en actividad comercial. (a) ¿Cómo puede optimizar el GMF (4×1000)?**
  - Créase como un nuevo impuesto, a partir del primero (1o.) de enero del año 2001, el Gravamen a los Movimientos Financieros, a cargo de los usuar.
  - El hecho generador del Gravamen a los Movimientos Financieros lo constituye la realización de las transacciones financieras, mediante las cuales.
  - Para los propósitos de esta ley se entiende por biocombustibles de origen vegetal o animal para uso en motores diesel aquel combustible líquido o gaseoso que ha sido obtenido de un vegetal o animal que se puede emplear en procesos de combus.
- **(b) ¿El ICA de Bogotá es deducible…?**
  - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente.

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
- effective_topic: gravamen_movimiento_financiero_4x1000
- wall_ms: 6125
- trace_id: 008121044a3d4c8185235293151cc143
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

