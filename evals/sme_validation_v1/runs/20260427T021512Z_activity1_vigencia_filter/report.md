# §1.G SME validation report

**Run dir:** `evals/sme_validation_v1/runs/20260427T021512Z_activity1_vigencia_filter`
**Generated:** 2026-04-26 09:24:32 PM Bogotá
**Questions classified:** 36 / 36

## Overall

| Class | Count |
|---|---|
| 🟢 served_strong | 9 |
| 🟡 served_acceptable | 12 |
| 🟠 served_weak | 2 |
| 🔵 served_off_topic | 4 |
| 🔴 refused | 9 |
| 💥 server_error | 0 |
| **total** | **36** |

## Per topic (12 × 3 grid)

| Topic | P1 directa | P2 operativa | P3 borde |
|---|---|---|---|
| beneficio_auditoria | 🔴 refused | 🟢 served_strong | 🟡 served_acceptable |
| firmeza_declaraciones | 🟢 served_strong | 🟡 served_acceptable | 🟢 served_strong |
| regimen_sancionatorio_extemporaneidad | 🔵 served_off_topic | 🔴 refused | 🟡 served_acceptable |
| descuentos_tributarios_renta | 🔴 refused | 🔵 served_off_topic | 🟢 served_strong |
| tarifas_renta_y_ttd | 🔴 refused | 🔴 refused | 🔴 refused |
| dividendos_y_distribucion_utilidades | 🟡 served_acceptable | 🟢 served_strong | 🟡 served_acceptable |
| devoluciones_saldos_a_favor | 🟢 served_strong | 🟢 served_strong | 🟢 served_strong |
| perdidas_fiscales_art147 | 🔴 refused | 🟡 served_acceptable | 🟡 served_acceptable |
| precios_de_transferencia | 🟢 served_strong | 🟡 served_acceptable | 🔴 refused |
| impuesto_patrimonio_personas_naturales | 🔴 refused | 🟡 served_acceptable | 🟡 served_acceptable |
| regimen_cambiario | 🟠 served_weak | 🟡 served_acceptable | 🟠 served_weak |
| conciliacion_fiscal | 🟡 served_acceptable | 🔵 served_off_topic | 🔵 served_off_topic |

## Per profile

| Profile | 🟢 served_strong | 🟡 served_acceptable | 🟠 served_weak | 🔵 served_off_topic | 🔴 refused | 💥 server_error |
|---|---|---|---|---|---|---|
| P1 | 3 | 2 | 1 | 1 | 5 | 0 |
| P2 | 3 | 5 | 0 | 2 | 2 | 0 |
| P3 | 3 | 5 | 1 | 1 | 2 | 0 |

## Routing accuracy

- Correct routing: **32/36**
- Wrong routing: **4/36**
- Unknown effective_topic: **0/36**

| qid | expected | actual | class |
|---|---|---|---|
| conciliacion_fiscal_P2 | conciliacion_fiscal | 'patrimonio_fiscal_renta' | 🔵 served_off_topic |
| conciliacion_fiscal_P3 | conciliacion_fiscal | 'patrimonio_fiscal_renta' | 🔵 served_off_topic |
| descuentos_tributarios_renta_P2 | descuentos_tributarios_renta | 'iva' | 🔵 served_off_topic |
| regimen_sancionatorio_extemporaneidad_P1 | regimen_sancionatorio_extemporaneidad | 'declaracion_renta' | 🔵 served_off_topic |

## Cross-checks (binding regardless of overall)

- `impuesto_patrimonio_personas_naturales`: refused 1/3 — ⚠ unexpected mix — investigate
- 11 baseline-SERVED topics with hidden full-refusals: 1 → ⚠ tarifas_renta_y_ttd

## Topics flagged for follow-up

### beneficio_auditoria
- **beneficio_auditoria_P1** — 🔴 refused (mode=`topic_safety_abstention`, cites=0, len=276, effective_topic=`beneficio_auditoria`, fallback_reason=`pipeline_d_coherence_chunks_off_topic`)
  - **Q:** Si una empresa quiere acogerse al beneficio de auditoría este año, ¿cuánto tiene que subir el impuesto frente al año pasado y cuánto se reduce el plazo de firmeza?
  - **A (head):** No pude ubicar evidencia del tema **beneficio_auditoria** en el grafo. Los documentos de apoyo recuperados pertenecen al tema **precios_de_transferencia**; prefiero no responder con evidencia cruzada. Reformula la consulta o confirma si necesitas orientación de ese otro tema.

### regimen_sancionatorio_extemporaneidad
- **regimen_sancionatorio_extemporaneidad_P1** — 🔵 served_off_topic (mode=`graph_native`, cites=4, len=2317, effective_topic=`declaracion_renta`, fallback_reason=`None`)
  - **Q:** ¿Cuánto cobra la DIAN por presentar una declaración de renta tarde si no hay impuesto a cargo?
  - **A (head):** ### Respuestas directas ⏎  ⏎ *   **¿Cuánto cobra la DIAN por presentar una declaración de renta tarde si no hay impuesto a cargo?** ⏎     *   La sanción mínima por extemporaneidad es de 10 UVT (art. 639 ET). Para el año 2024, esto equivale a $470.650. ⏎     *   Esta sanción aplica incluso si la declaración 
- **regimen_sancionatorio_extemporaneidad_P2** — 🔴 refused (mode=`topic_safety_abstention`, cites=0, len=294, effective_topic=`regimen_sancionatorio_extemporaneidad`, fallback_reason=`pipeline_d_coherence_chunks_off_topic`)
  - **Q:** Un cliente persona natural se le pasó el plazo y va a presentar la renta del 2024 dos meses tarde. El impuesto a cargo le da $4.500.000. ¿Cuánto le toca pagar de sanción más intereses, y le puedo aplicar alguna reducción si es la primera vez que esto le pasa?
  - **A (head):** No pude ubicar evidencia del tema **regimen_sancionatorio_extemporaneidad** en el grafo. Los documentos de apoyo recuperados pertenecen al tema **precios_de_transferencia**; prefiero no responder con evidencia cruzada. Reformula la consulta o confirma si necesitas orientación de ese otro tema.

### descuentos_tributarios_renta
- **descuentos_tributarios_renta_P1** — 🔴 refused (mode=`topic_safety_abstention`, cites=0, len=285, effective_topic=`descuentos_tributarios_renta`, fallback_reason=`pipeline_d_coherence_chunks_off_topic`)
  - **Q:** Si una PYME compra una máquina nueva para su producción este año, ¿qué puede hacer con el IVA que pagó en esa compra a nivel del impuesto de renta?
  - **A (head):** No pude ubicar evidencia del tema **descuentos_tributarios_renta** en el grafo. Los documentos de apoyo recuperados pertenecen al tema **precios_de_transferencia**; prefiero no responder con evidencia cruzada. Reformula la consulta o confirma si necesitas orientación de ese otro tema.
- **descuentos_tributarios_renta_P2** — 🔵 served_off_topic (mode=`graph_native`, cites=4, len=2371, effective_topic=`iva`, fallback_reason=`None`)
  - **Q:** Mi cliente tiene una panadería SAS, compró un horno industrial en 2025 por $120 millones más IVA del 19%. Quiere saber si puede tomar todo el IVA como descuento en la declaración de este año o si tiene que repartirlo. ¿Qué pasa si el descuento le queda más grande que el impuesto a cargo?
  - **A (head):** ### Respuestas directas ⏎  ⏎ *   **¿Puede tomar todo el IVA como descuento en la declaración de este año o tiene que repartirlo?** ⏎     *   El IVA pagado en la adquisición de activos fijos productivos, como el horno industrial, se puede tratar como descuento tributario en el impuesto sobre la renta (art.

### tarifas_renta_y_ttd
- **tarifas_renta_y_ttd_P1** — 🔴 refused (mode=`topic_safety_abstention`, cites=0, len=170, effective_topic=`tarifas_renta_y_ttd`, fallback_reason=`pipeline_d_coherence_zero_evidence_for_router_topic`)
  - **Q:** ¿Cuál es la tarifa general de renta para una SAS en Colombia para el año gravable 2025?
  - **A (head):** Evidencia insuficiente para responder con respaldo normativo en el tema **tarifas_renta_y_ttd**. Reformula la consulta o revisa manualmente antes de responder al cliente.
- **tarifas_renta_y_ttd_P2** — 🔴 refused (mode=`topic_safety_abstention`, cites=0, len=276, effective_topic=`tarifas_renta_y_ttd`, fallback_reason=`pipeline_d_coherence_chunks_off_topic`)
  - **Q:** Una SAS de mi cliente factura $4.500 millones, tiene utilidad contable antes de impuestos de $800 millones y renta líquida gravable de $400 millones. Le da impuesto de $140 millones al 35%. Pero me preocupa la TTD porque su tasa efectiva sobre la utilidad contable da apenas 11%. ¿Tengo que liquidar Impuesto a Adicionar y cómo lo calculo?
  - **A (head):** No pude ubicar evidencia del tema **tarifas_renta_y_ttd** en el grafo. Los documentos de apoyo recuperados pertenecen al tema **precios_de_transferencia**; prefiero no responder con evidencia cruzada. Reformula la consulta o confirma si necesitas orientación de ese otro tema.
- **tarifas_renta_y_ttd_P3** — 🔴 refused (mode=`topic_safety_abstention`, cites=0, len=276, effective_topic=`tarifas_renta_y_ttd`, fallback_reason=`pipeline_d_coherence_chunks_off_topic`)
  - **Q:** Tengo un cliente hotel pequeño ubicado en un municipio de 80 mil habitantes que abrió en 2023. Le vienen vendiendo la idea de que tiene tarifa preferencial del 9% o 15%. ¿Cuál de las dos aplica realmente, qué requisitos tiene que cumplir, y queda excluido del cálculo de la TTD?
  - **A (head):** No pude ubicar evidencia del tema **tarifas_renta_y_ttd** en el grafo. Los documentos de apoyo recuperados pertenecen al tema **precios_de_transferencia**; prefiero no responder con evidencia cruzada. Reformula la consulta o confirma si necesitas orientación de ese otro tema.

### perdidas_fiscales_art147
- **perdidas_fiscales_art147_P1** — 🔴 refused (mode=`topic_safety_abstention`, cites=0, len=175, effective_topic=`perdidas_fiscales_art147`, fallback_reason=`pipeline_d_coherence_zero_evidence_for_router_topic`)
  - **Q:** ¿Cuántos años hacia adelante puedo arrastrar una pérdida fiscal generada por una SAS para compensarla con utilidades futuras?
  - **A (head):** Evidencia insuficiente para responder con respaldo normativo en el tema **perdidas_fiscales_art147**. Reformula la consulta o revisa manualmente antes de responder al cliente.

### precios_de_transferencia
- **precios_de_transferencia_P3** — 🔴 refused (mode=`topic_safety_abstention`, cites=0, len=175, effective_topic=`precios_de_transferencia`, fallback_reason=`pipeline_d_coherence_zero_evidence_for_router_topic`)
  - **Q:** Mi cliente, una PYME de $1.500 millones en ingresos, le compró mercancía durante 2025 a un proveedor en Hong Kong por $400 millones. Hasta donde tenía entendido Hong Kong era jurisdicción no cooperante y eso lo metía en precios de transferencia sin importar montos. ¿Sigue siendo así para la declaración que voy a presentar este año?
  - **A (head):** Evidencia insuficiente para responder con respaldo normativo en el tema **precios_de_transferencia**. Reformula la consulta o revisa manualmente antes de responder al cliente.

### impuesto_patrimonio_personas_naturales
- **impuesto_patrimonio_personas_naturales_P1** — 🔴 refused (mode=`topic_safety_abstention`, cites=0, len=189, effective_topic=`impuesto_patrimonio_personas_naturales`, fallback_reason=`pipeline_d_coherence_zero_evidence_for_router_topic`)
  - **Q:** ¿A partir de qué patrimonio una persona natural en Colombia tiene que pagar impuesto al patrimonio?
  - **A (head):** Evidencia insuficiente para responder con respaldo normativo en el tema **impuesto_patrimonio_personas_naturales**. Reformula la consulta o revisa manualmente antes de responder al cliente.

### regimen_cambiario
- **regimen_cambiario_P1** — 🟠 served_weak (mode=`graph_native_partial`, cites=4, len=399, effective_topic=`regimen_cambiario`, fallback_reason=`pipeline_d_no_graph_primary_articles`)
  - **Q:** Cuando una PYME importa mercancía y le paga al proveedor del exterior, ¿esa operación se tiene que canalizar a través del mercado cambiario regulado o la puede pagar como quiera?
  - **A (head):** **Ruta sugerida** ⏎ 1. **Paso 1: Identificar si la PYME requiere canalización obligatoria.** Esto se determina según la naturaleza de la operación y los montos involucrados (arts. paso-a-paso-pr-ctico y posiciones-de-expertos ET). ⏎  ⏎ **Riesgos y condiciones** ⏎ - La cobertura de esta respuesta es parcial.
- **regimen_cambiario_P3** — 🟠 served_weak (mode=`graph_native_partial`, cites=4, len=255, effective_topic=`regimen_cambiario`, fallback_reason=`pipeline_d_no_graph_primary_articles`)
  - **Q:** Mi cliente recibió en 2025 una inversión extranjera directa de $500.000 USD de un fondo en Países Bajos para capitalización de la SAS. Hicieron la transferencia pero nadie se acordó de hacer el registro ante el Banco de la República. Estamos en marzo de 2026. ¿Qué riesgo hay, todavía se puede regularizar, y qué pasa con los dividendos que eventualmente quieran girarle al inversionista si nunca se registró la inversión?
  - **A (head):** **Ruta sugerida** ⏎ 1. PYME Importadora — Qué hacer paso a paso Situación (art. paso-a-paso-pr-ctico ET). ⏎  ⏎ **Riesgos y condiciones** ⏎ - La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.

### conciliacion_fiscal
- **conciliacion_fiscal_P2** — 🔵 served_off_topic (mode=`graph_native`, cites=5, len=3104, effective_topic=`patrimonio_fiscal_renta`, fallback_reason=`None`)
  - **Q:** Mi cliente es una SAS Grupo 2 NIIF para PYMES con ingresos de $3.800 millones que aplica el modelo de revaluación en sus inmuebles. La revaluación contable subió el valor del edificio en $400 millones en 2025. ¿Cómo manejo eso en el 2516? ¿Es diferencia permanente o temporaria, qué efecto tiene en el patrimonio fiscal versus contable, y me toca registrar impuesto diferido?
  - **A (head):** **Respuestas directas** ⏎ - **¿Cómo manejo eso en el 2516?** ⏎   - Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente. ⏎ - **¿Es diferencia permanente o temporaria, qué efecto tiene en el patrimonio fiscal versus contable, y me toca registrar impuesto diferid
- **conciliacion_fiscal_P3** — 🔵 served_off_topic (mode=`graph_native`, cites=4, len=3490, effective_topic=`patrimonio_fiscal_renta`, fallback_reason=`None`)
  - **Q:** Una clienta tiene un contrato de arrendamiento de bodega que bajo NIIF 16 reconoció como activo por derecho de uso de $300 millones y un pasivo por arrendamiento de $290 millones. Fiscalmente entiendo que esas figuras no existen y que solo se deduce el canon pagado en el año. ¿Cómo concilio eso en el 2516, cómo afecta el patrimonio fiscal, y si más adelante la DIAN me hace comparación patrimonial cómo justifico la diferencia?
  - **A (head):** **Respuestas directas** ⏎  ⏎ *   **¿Cómo concilio el reconocimiento del activo por derecho de uso y el pasivo por arrendamiento bajo NIIF 16 con la normativa fiscal en el formato 2516?** ⏎  ⏎     *   Fiscalmente, el activo por derecho de uso y el pasivo por arrendamiento no se reconocen. Para efectos tribut

## Decision

**STATE: PARTIAL** — 21/36 served_acceptable+ in [14, 21] band

- PASS = ≥22/36 served_acceptable+
- PARTIAL = 14–21/36 served_acceptable+
- FAIL = ≤13/36 served_acceptable+
