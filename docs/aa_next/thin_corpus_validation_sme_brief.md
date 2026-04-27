# Brief para el SME — preguntas de validación de los 12 temas thin-corpus

> **Para qué necesitamos estas preguntas.** Acabamos de desbloquear 10 de 12 temas problemáticos en el chat de Lia. Antes de declarar éxito, necesitamos verificar que las respuestas son **realmente útiles para un contador**, no solo que el sistema "responde algo". Las preguntas que ya usé para verificar fueron escritas por mí (Claude) y son sintéticas — un experto humano puede formular consultas más reales.
>
> **Tiempo estimado:** ~45-60 min para los 12 temas (3 preguntas cada uno = 36 preguntas).
>
> **Formato esperado:** Un párrafo por pregunta, en español natural, como las recibirías de un contador de PYME por WhatsApp o email. Sin formalismos, sin redacción jurídica, sin citas explícitas a artículos (a menos que el contador realmente las cite).

---

## Estructura por tema — 3 preguntas con perfiles distintos

Para CADA uno de los 12 temas, queremos las siguientes 3 preguntas. La idea: ejercitar el sistema desde 3 ángulos distintos.

### Pregunta tipo 1 — **Directa / factual**

Una pregunta simple sobre un dato concreto: tarifa, plazo, umbral, fórmula, fecha. La respuesta debería ser un número o una regla corta.

**Ejemplo (firmeza):** "¿Cuántos meses tiene la DIAN para revisar mi declaración de renta de 2024?"

### Pregunta tipo 2 — **Operativa / situacional**

Un caso práctico de un cliente PYME concreto, donde el contador necesita saber **qué hacer paso a paso**. Debe incluir contexto realista (tipo de empresa, ingresos, periodo, etc.).

**Ejemplo (firmeza):** "Tengo un cliente, una SAS con ingresos de $1.500M en 2024, que quiere tomar el beneficio de auditoría. ¿Qué tasa de incremento del impuesto necesita y a qué riesgos lo expone si DIAN encuentra inconsistencias después?"

### Pregunta tipo 3 — **Borde / interpretativa**

Un caso de frontera donde la respuesta no es obvia: una excepción, una interacción entre normas, un escenario que pondría a dudar incluso a un experto. Debe forzar al sistema a razonar más allá de la lectura literal de un artículo.

**Ejemplo (firmeza):** "Mi cliente compensó pérdidas fiscales del 2018 en su declaración del 2024. ¿La firmeza de esa declaración del 2024 sigue siendo de 3 años o se extiende? ¿Qué pasa si aplicó beneficio de auditoría sobre esa misma declaración?"

---

## Los 12 temas — qué cubre cada uno + bibliografía rápida

Para cada tema te doy: (a) **alcance** (qué cubre), (b) **artículos canónicos** (los más importantes), (c) **audiencia** (qué tipo de PYME haría esta consulta).

### 1. `beneficio_auditoria` ✅ (confirmar)

- **Alcance:** Beneficio del Art. 689-3 ET. Tasas de incremento del impuesto, requisitos, plazos, riesgos.
- **Canónicos:** Art. 689-3 ET, Ley 2277/2022, Decreto 0625/2024.
- **Audiencia:** PYMEs con utilidad estable que quieren reducir el riesgo de fiscalización.

### 2. `firmeza_declaraciones` ✅ (confirmar)

- **Alcance:** Plazos de firmeza generales (Art. 714 ET) y especiales (pérdidas fiscales, precios de transferencia, beneficio auditoría).
- **Canónicos:** Art. 714, 689-3, 705, 705-1, 706, 117 Ley 2010/2019.
- **Audiencia:** Contadores que quieren saber cuándo cierra el periodo de fiscalización para una declaración específica.

### 3. `regimen_sancionatorio_extemporaneidad` ✅ (confirmar)

- **Alcance:** Sanción por extemporaneidad (Art. 641, 642), por corrección (Art. 644), por inexactitud (Art. 647, 648), reducción del Art. 640.
- **Canónicos:** ET Arts. 640, 641, 642, 644, 647, 648.
- **Audiencia:** Contadores que ya presentaron una declaración tarde o necesitan corregir una declaración ya presentada.

### 4. `descuentos_tributarios_renta` ✅ (confirmar)

- **Alcance:** Descuentos de la base del impuesto sobre la renta. CTeI (Art. 256), donaciones a ESAL (Art. 257), descuento del IVA por bienes de capital (Art. 258-1), límite de los descuentos (Art. 260).
- **Canónicos:** ET Arts. 254, 255, 256, 257, 258, 258-1, 259, 260.
- **Audiencia:** Empresas que invirtieron en innovación, donaron a fundaciones, o compraron maquinaria.

### 5. `tarifas_renta_y_ttd` ✅ (confirmar)

- **Alcance:** Tarifa general del impuesto de renta (35%), tarifas especiales (zonas francas, agropecuario), tasa de tributación depurada (TTD) del parágrafo 6 del Art. 240.
- **Canónicos:** ET Arts. 240, 240-1, 241, 242, 242-1, 243.
- **Audiencia:** Contadores liquidando el impuesto del año gravable.

### 6. `dividendos_y_distribucion_utilidades` ✅ (confirmar)

- **Alcance:** Tributación de dividendos para personas naturales residentes, sociedades nacionales, no residentes. Procedimiento del Art. 49 (utilidad fiscal vs comercial).
- **Canónicos:** ET Arts. 48, 49, 242, 242-1, 245.
- **Audiencia:** Empresas que reparten utilidades a socios; socios que reciben dividendos.

### 7. `devoluciones_saldos_a_favor` ✅ (confirmar)

- **Alcance:** Procedimiento para solicitar devolución de saldos a favor (de IVA, de renta), plazos DIAN, garantías, intereses a favor del contribuyente.
- **Canónicos:** ET Arts. 850, 855, 857, 859, 860, 861, 862, 863, 864, 865.
- **Audiencia:** Empresas exportadoras o con saldos a favor de IVA recurrentes.

### 8. `perdidas_fiscales_art147` ✅ (confirmar)

- **Alcance:** Compensación de pérdidas fiscales (Art. 147 ET), plazo de 12 años, régimen de transición de la Ley 2010/2019, efecto sobre la firmeza.
- **Canónicos:** ET Art. 147, Ley 2010/2019 Art. 117.
- **Audiencia:** Empresas con pérdidas operacionales acumuladas.

### 9. `precios_de_transferencia` ❌ (todavía no responde — necesitamos las preguntas igual)

- **Alcance:** Régimen de precios de transferencia. Cuándo aplica (umbrales de patrimonio + ingresos + jurisdicciones no cooperantes), método más apropiado, declaración informativa, documentación comprobatoria.
- **Canónicos:** ET Arts. 260-1 a 260-11.
- **Audiencia:** PYMEs con vinculados económicos en el exterior, o que operan con jurisdicciones no cooperantes.

### 10. `impuesto_patrimonio_personas_naturales` ❌ (todavía no responde — necesitamos las preguntas igual)

- **Alcance:** Impuesto al patrimonio para personas naturales. Umbral de 72.000 UVT, base gravable, exclusiones (vivienda primera, acciones), tarifa progresiva, declaración del Formulario 420.
- **Canónicos:** ET Arts. 292-3 a 298-8, Ley 2277/2022.
- **Audiencia:** Socios de PYMEs con patrimonio personal alto.

### 11. `regimen_cambiario` ✅ (confirmar)

- **Alcance:** Régimen cambiario para PYMEs. Operaciones canalizables vs no canalizables, declaración cambiaria ante Banco de la República, cuenta de compensación, IMC.
- **Canónicos:** Ley 9/1991, Decreto 1068/2015, Resolución Externa 1/2018 (Banrep), Circular DCIN-83.
- **Audiencia:** PYMEs importadoras, exportadoras, que reciben inversión extranjera.

### 12. `conciliacion_fiscal` ✅ (confirmar)

- **Alcance:** Formato 2516 (personas jurídicas) y 2517 (personas naturales). Estructura del formato, conciliación de diferencias contables vs fiscales (permanentes y temporarias), Art. 772-1 ET.
- **Canónicos:** ET Art. 772-1, formatos DIAN 2516 y 2517.
- **Audiencia:** Empresas obligadas a llevar contabilidad bajo NIIF.

---

## Formato de entrega

Para cada tema, danos algo así:

```
TEMA: <nombre del tema>
P1 (directa): <pregunta>
P2 (operativa): <pregunta>
P3 (borde): <pregunta>
```

Texto plano, sin markdown ni formato. Si una pregunta cita un artículo específicamente, ponlo. Si NO lo cita (porque el contador no lo sabría de memoria), no lo metas — quiero ver cómo el sistema responde a vocabulario natural.

**Una sola excepción:** si una pregunta presupone un caso concreto (ej. "una SAS con ingresos de $1.500M"), incluí el dato. Eso ejercita la respuesta operativa con números reales.

## Cuando me las entregues

Voy a correr las 36 preguntas contra el chat actual + capturar:
1. ✅ Servida con respuesta de calidad / ✅ Servida pero respuesta floja / ❌ Refusal.
2. Citas que se mostraron.
3. Modo de respuesta (`graph_native` vs `graph_native_partial` vs abstención).

Todo se loggea contra el `thin_corpus_baseline.json` actual + se hace un report tipo "8 confirmadas, 2 mejoraron, 2 deben curarse mejor". Eso te dice cuáles están listos para usuarios reales y cuáles necesitan más trabajo.
