# fix_v18_may.md — Pulido del rendering de respuestas (post-v17)

> **Zero-agent-context protocol.** Este documento es autocontenido.
> Un agente LLM nuevo, sin historial de conversación, puede ejecutarlo
> leyendo el sistema de archivos. Todo path, función, flag, test y
> regla de decisión está escrito verbatim. Antes de actuar, verificá
> cada artefacto contra `git ls-files`. Si algo no existe, STOP y
> reportá drift — no inventes.

---

## §-1 RESUME HERE — fresh-agent retake protocol

> Sos un agente nuevo invocado con un prompt tipo "retake fix_v18" o
> "continúa fix_v18". Esta sección es tu único punto de entrada.
> Cada paso es load-bearing.

### Paso 1 — verificá que el sistema de archivos coincide

```bash
test -f docs/re-engineer/fix/fix_v18_may.md && \
    test -f docs/re-engineer/fix/fix_v17_may.md && \
    test -f CLAUDE.md && echo "OK: canonical docs present"

test -f src/lia_graph/pipeline_d/answer_llm_polish.py && \
    test -f src/lia_graph/pipeline_d/answer_synthesis_practica.py && \
    test -f src/lia_graph/pipeline_d/answer_synthesis_helpers.py && \
    echo "OK: target modules present"

grep -q "LIA_POLISH_UVT_VALIDATOR" src/lia_graph/pipeline_d/answer_llm_polish.py && \
    echo "OK: fix_v15 UVT validator scaffolding still present (the model for v18 validators)"
```

Si alguno falla, STOP. No reconstruyas el plan desde el código.

### Paso 2 — baseline de tests

```bash
PYTHONPATH=src:. uv run pytest \
    tests/test_sub_bullet_rendering.py \
    tests/test_planner_case_anchor_registry.py \
    tests/test_case_detectors_purity.py \
    tests/test_classifier_playbook_override.py \
    tests/test_classifier_path_veto.py \
    tests/test_answer_polish_rejected_fallback.py \
    tests/test_answer_synthesis_practica.py -q
```

**Esperado:** `226 passed`. Si es menor, algo cambió desde el último
commit; investigá antes de actuar.

### Paso 3 — leé estas secciones EN ESTE ORDEN

1. **§0** TL;DR — qué es v18 y por qué existe.
2. **§1** Issues en scope — los 5 ítems iniciales + slot para nuevos.
3. **§2** Six-gate lifecycle (no se salta ninguna gate).
4. **§4** Casos capturados — los fixtures de regresión reales.

### Paso 4 — identificá tu escenario

| Operador dice… | Escenario | Acción |
|---|---|---|
| *"empezá v18"* / *"land v18 Issue A"* | Ejecutás Issue A (chunk-noise) | §1.1 + §2 lifecycle |
| *"shadow promote Issue B"* | Flip shadow → enforce del validator B | §1.2 paso 5 |
| *"agregá un fixture, fallé esta pregunta"* | Capturá failure case nuevo | §4.6 (slot vacío) |
| *"qué sigue después de Issue A"* | Listá residuos abiertos | §1 + §0.1 status |

### Paso 5 — trampas conocidas (leelas una vez)

1. **El servidor no recarga Python en caliente.** Después de
   editar cualquier `.py` bajo `src/lia_graph/`, restart:
   ```
   kill $(pgrep -f "lia_graph.ui_server") 2>/dev/null; \
       pkill -f "scripts/dev-launcher" 2>/dev/null; true
   npm run dev:staging
   ```
2. **Validators de polish van shadow → enforce.** Nunca enforce
   directo. Patrón canónico: fix_v15_may §3 UVT validator. Una
   vuelta shadow + panel + 0 falsos positivos → flip enforce.
3. **No bajes el threshold cuando un validator falla.** Per
   `feedback_thresholds_no_lower` — afinás la heurística, no el bar.
4. **El polish-LLM tiene latitud creativa explícita** ("podés
   reescribir la prosa"). Las reglas del prompt no son hard rules
   para él. Los validators son la red de seguridad.

### Paso 6 — reglas de comunicación

- Lenguaje plano con el operador. Profundidad técnica solo cuando lo pida.
- Terminá cada reporte con una sugerencia concreta de próximo paso.
- Sin montos en dólares en reportes de estado (tiempo + alcance, OK).
- SME panel solo on-demand. Nunca auto-corras `run_sme_parallel.py`.
- Default run mode: `dev:staging`. Verificá `retrieval_backend=supabase`
  en la primera respuesta.
- Actualizá este documento EN EL MISMO COMMIT que cualquier cambio.

---

## §0. TL;DR

**Qué es v18.** Pulido del rendering de respuestas — TODOS los ítems
son post-procesamiento de polish + practica-chunk extraction. Ningún
ítem aquí afecta retrieval, planner ni la calidad de los SPECs v17.

**Por qué ahora.** v17 cerró la cobertura de temas (cada pregunta
laboral típica tiene un SPEC anchor); v18 cierra la última milla:
hacer que la respuesta que ve el contador en pantalla **se vea
limpia** y **no tenga fragmentos contradictorios** mezclados con el
contenido autoritativo.

**Alcance.** 4 issues iniciales (A-D) + slot para issues nuevos
(E+) que aparezcan a medida que el operador siga probando. Cada uno
es un fix narrow + un validator nuevo o un filtro narrow. Sin
cambios de schema, sin cambios de retrieval.

**Riesgo.** Bajo. Validators arrancan en `shadow` (telemetría sin
efecto). El filter de practica corre detrás de un flag con default
`legacy` hasta que el panel valide.

**Esfuerzo.** Issue A (~1 día). Issue B (~½ día). Issue C (~1 día).
Issue D (~30 min). Total ~3 días si se hacen serial; ~2 días si se
paraleliza.

---

## §0.1 Status snapshot — 2026-05-15 (evening)

| Issue | Estado | Capturado por | Plan |
|---|---|---|---|
| A | 🧪 código + unit tests verdes (shadow default) | probe `liquidacion_terminacion` (2026-05-15 PM) + probe `aportes_proporcionales_tiempo_parcial` (2026-05-15 PM) | §1.1 |
| B | 🛠 idea | mismas probes | §1.2 |
| C | 🛠 idea | probe `liquidacion_terminacion` (CST 65 moratoria bullet dropped) | §1.3 |
| D | 🧪 código + anti-test verde (sin flag, surgical) | observado durante v17 b2 — `is_donaciones_case` keys on bare `esal` → colisiona con `desalarizacion` | §1.4 |

Status legend (heredado de fix_v17_may §12):
- 🛠 — idea + plan, sin código
- 🧪 — código + tests verdes locales
- ✅ — verificado en dev:staging con probe del operador
- ↩ — regresó y se descartó con razón

---

## §1. Issues en scope

### §1.1 Issue A — chunk-noise leak en `Recomendaciones Prácticas`

**Síntoma para el contador.** Las primeras 5-8 viñetas de la sección
`Recomendaciones Prácticas` son fragmentos de corpus sin contexto:
ejemplos numéricos huérfanos, reglas viejas mezcladas con las
actuales, códigos de software desconectados, marketing forward-dated.

**Ejemplo capturado (probe del 2026-05-15 PM, `liquidacion_terminacion`).**
El contador preguntó *"¿Cómo liquido a un empleado despedido sin
justa causa, $4M, 4 años?"*. La respuesta empezó con:

```
1. Despido sin justa causa (...): código 55.    ← noise (DSPNE)
2. Despido con justa causa (...): código 56.    ← noise (DSPNE)
3. Despido injustificado en AÑO 1: 30 días.     ← SPEC correcto
4. Despido injustificado en AÑO 1: 45 días.     ← noise (regla pre-Ley 789, derogada 2002)
5. Antes: 30 días × ($2.200.000 ÷ 30) = $2.200.000.   ← noise (ejemplo de otra persona)
```

El bullet 4 contradice al 3. El contador no puede saber cuál es
correcta sin leer la norma. Es **el riesgo más alto** de los 4
issues (un contador podría citar la regla derogada).

**Root cause.** `pipeline_d/answer_synthesis_practica.py::extend_from_practica_chunks`
+ `_candidate_lines_from_chunk` extraen líneas de los chunks
`practica_erp` sin filtrar por:
- relevancia al detector activo
- presencia de ancla legal en la línea
- ausencia de marcadores temporales tipo "antes", "anteriormente",
  "pre-ley", "histórico", "derogado"
- ausencia de ejemplos numéricos huérfanos (valor + moneda sin
  pregunta-referencia)

También se filtra mal `answer_synthesis_helpers.py::extend_from_support_insights`
(llamado en `build_recommendations` línea 70) — llama a
`clean_support_line_for_answer` pero no filtra por tópico-relevance.

**Module donde aterriza el fix (más narrow).**

| File | Cambio |
|---|---|
| `pipeline_d/answer_synthesis_practica.py` | Añadir filtro pre-`append_unique`: rechazar líneas (a) sin marcador de tema activo, (b) con red-flag temporal, (c) ejemplos numéricos huérfanos. |
| `pipeline_d/chunk_quality_heuristics.py` | Añadir nuevos motivos `pre_ley_marker_dominant`, `orphan_numeric_example_dominant`, `software_code_isolated_dominant` con `PENALTY_LIGHT`. |
| `config/llm_runtime.json` | (nada) |

**Flag.** `LIA_PRACTICA_NOISE_FILTER ∈ {off, shadow, enforce}`.
Default `shadow` al merge → flip a `enforce` después del panel.

**Gate 3 — success criterion (numérico, medible).**

| Métrica | Antes (probe terminación) | Meta `enforce` |
|---|---|---|
| Bullets noise antes del primer SPEC bullet | 5 | ≤ 1 |
| Bullets que contradicen al SPEC (ej. "45 días" + "30 días") | 1 | 0 |
| Bullets SPEC perdidos por sobrefiltrado | 0 (no fired) | 0 |
| Re-probe de la pregunta original | confusing | clean |

**Gate 4 — test plan.**

| Stage | Actor | Environment | Pass condition |
|---|---|---|---|
| 1. Unit tests para el filtro | Engineer | local | Filtro descarta los 5 noise bullets capturados + preserva los 7 SPEC bullets |
| 2. Shadow telemetría 24-48h | Engineer | dev:staging | Trace step `practica.noise_filter.applied` con `outcome` ∈ {pass, suppressed, noop} ≥ 100 turnos |
| 3. Análisis de falsos positivos | Engineer | local sobre traces | < 5 % de SPEC bullets legítimos marcados como noise |
| 4. Operator re-probe | Operator | dev:staging | Misma pregunta del fixture (§4.1) sale limpia |
| 5. Sign-off | Operator | dev:staging | "lo enviaría a un contador as-is" |

**Gate 5 — greenlight.** Operator re-asks `liquidacion_terminacion`
fixture → ≤ 1 noise bullet, 0 contradicciones, 7 SPEC bullets surface.

**Gate 6 — refine-or-discard.**
- Refine: ajustar la heurística específica (qué bullet sobró, qué se
  perdió), re-shadow, re-probe.
- Discard: si después de 2 iteraciones sigue rompiendo SPEC bullets
  legítimos → revertir a `legacy` y registrar en
  `docs/aa_next/playbook_regressions.md` con la causa.

**Rollback.** `LIA_PRACTICA_NOISE_FILTER=legacy` (o `off`) revierte
al comportamiento actual.

---

### §1.2 Issue B — polish hallucina `ET` en artículos CST / Ley / Decreto

**Síntoma para el contador.** Polish toma artículos del CST (Código
Sustantivo del Trabajo) y los rotula como ET (Estatuto Tributario).
Ej.: "art. 127-132 ET" cuando son CST. CST 127-132 = pagos no
constitutivos de salario; ET 127-132 no existe.

**Ejemplo capturado (probe del 2026-05-15 PM, ambos topics laborales).**

```
Anclaje Legal
• Art. 127-132 ET — Definición de salario.    ← son CST, no ET
• Art. 186 ET — Derecho al descanso remunerado. ← CST, no ET
```

Aparecen también en bullets corridos: "(arts. 127-132 ET)",
"(art. 186 ET)". El usuario que conoce las normas las identifica
como CST y nota la inconsistencia.

**Root cause.** El prompt de polish no constraina las etiquetas de
código. Cuando ve "art. 127" en el draft, le pone "ET" por default
porque ET es el código más mencionado en su training implícito.
La validación de fix_v15 (`_no_invented_uvt_ranges`) atrapa
**números inventados** pero no **etiquetas de código inventadas**.

**Module donde aterriza el fix.**

| File | Cambio |
|---|---|
| `pipeline_d/answer_llm_polish.py` | Nueva función `_no_cross_codigo_article_aliasing(polished, allowed_pairs)`. Misma forma que `_no_invented_uvt_ranges` (§3 fix_v15_may). |
| `pipeline_d/answer_llm_polish.py::_build_polish_prompt` | Añadir DIRECTIVA: "JAMÁS asumas que un artículo es ET. Si la fuente cita 'CST art. 127-132', tu polish DEBE decir 'CST art. 127-132'." |
| (sin schema change) | El validator infiere `(num, codigo)` pairs del template + evidence + question text. |

**Cue-gating (igual que fix_v15 §3).** El validator solo corre cuando
la pregunta o el template menciona artículos de los códigos
confundibles: CST 64, 65, 127-132, 186, 197, 230-234, 249, 306,
387 (sí, ET 387 sí existe pero CST también tiene ambigüedades);
Ley 50/1990, Ley 789/2002, Ley 100/1993; Decreto 2616/2013,
Decreto 1990/2016.

**Flag.** `LIA_POLISH_CODIGO_VALIDATOR ∈ {off, shadow, enforce}`.
Default `shadow` al merge.

**Gate 3 — success criterion.**

| Métrica | Antes | Meta `enforce` |
|---|---|---|
| Respuestas con `art. <CST-num> ET` falso | observado en 2 de 2 probes laborales | 0 |
| Falsos positivos (CST legítimo rechazado) | n/a | 0 en 50 turnos shadow |
| Re-probe del fixture (§4.2) | "art. 127-132 ET" | "CST art. 127-132" o "(arts. 127-132 CST)" |

**Gate 4 — test plan.** Igual al patrón fix_v15 §3:
1. Unit tests del validator
2. Shadow #1 ≥ 30 turnos
3. Si > 0 FP → refine + shadow #2
4. Si shadow #2 = 0 FP → flip enforce
5. Operator re-probe

**Rollback.** `LIA_POLISH_CODIGO_VALIDATOR=off`.

---

### §1.3 Issue C — polish drops SPEC bullets on concrete-numbers framing

**Síntoma para el contador.** Cuando la pregunta tiene números
concretos (salario, días, fecha), polish a veces **omite** una o
dos viñetas del template (que tienen tablas estáticas o reglas
generales) y las reemplaza por un worked-example en
`Procedimiento Sugerido`. La regla general queda invisible.

**Ejemplos capturados.**

- `liquidacion_terminacion` probe (2026-05-15 PM): bullet 5 del SPEC
  ("**CST art. 65** moratoria — 1 día de salario por cada día de
  mora") **no aparece** en la respuesta servida. Polish entregó la
  tabla de indemnización CST 64 pero dropped el bullet de moratoria.
- (residual de fix_v17_may §0.2.1) `liquidacion_mensual_nomina` con
  pregunta "$3M + 10 horas extras" dropped la tabla estática de
  porcentajes de recargo y mostró solo el cálculo del caso.

**Decisión de política (heredada de fix_v17_may §0.3.3 / residual #6).**
Operator definió en v17: **strict** — los SPEC bullets son sacred,
polish puede reescribir la prosa pero NO puede omitir un bullet
entero. v18 lo implementa.

**Module donde aterriza el fix.**

| File | Cambio |
|---|---|
| `pipeline_d/answer_llm_polish.py::_build_polish_prompt` | Fortalecer rule 5: "DEBÉS preservar TODAS las viñetas del BORRADOR. Podés reescribir la prosa pero NO podés OMITIR una viñeta entera del BORRADOR." |
| `pipeline_d/answer_llm_polish.py` | Nueva función `_no_dropped_spec_bullets(polished, template_bullets)`. Cuenta SPEC bullets en template; cuenta bullets identificables en polish; si polish < template − 1 → reject. |

**Detección de "bullet identificable".** Heurística simple: línea
que arranca con `**` (bold lead) o que cita un `art:<num>`. Margen
de 1 bullet para tolerar combinaciones legítimas (polish puede
fusionar 2 micro-bullets en uno).

**Flag.** `LIA_POLISH_SPEC_PRESERVATION ∈ {off, shadow, enforce}`.
Default `shadow`.

**Gate 3 — success criterion.**

| Métrica | Antes (probe terminación) | Meta `enforce` |
|---|---|---|
| SPEC bullets surfaced / SPEC bullets en template | 6/7 (= 86 %) | ≥ 95 % (= 7/7 o 7/8 con margen 1) |
| Falsos positivos (polish legítimo rechazado por fusión razonable) | n/a | 0 |
| Re-probe del fixture (§4.3) | falta CST 65 | CST 65 aparece |

**Riesgo de UX.** Si polish entrega TANTO el worked example COMO la
tabla estática, la respuesta se vuelve verbosa. Mitigación: el
prompt instruye preferir bullets de la tabla referenciados
explícitamente en el ejemplo (en lugar de duplicar).

**Rollback.** `LIA_POLISH_SPEC_PRESERVATION=off` revierte al
comportamiento permissivo.

---

### §1.4 Issue D — `is_donaciones_case` substring collision

**Síntoma para el contador.** Preguntas sobre **UGPP +
desalarización** caen en el detector de **donaciones** porque ese
detector keys on bare substring `"esal"` (intended for ESAL, el
tipo de entidad) y `desalarizacion` contains `esal`.

**Ejemplo capturado.** Fix_v17_may §13.1 item 9: la tabla de probes
v17 b2 evita la palabra "desalarización" precisamente porque trip
este bug.

**Root cause.** `case_detectors.py::is_donaciones_case` o
`case_bullets/donaciones.py` (verificar cuál tiene el marker)
usa el string `"esal"` sin word-boundary regex. Mismo patrón que
fix_v16 ya arregló para `rte_esal`.

**Module donde aterriza el fix.**

| File | Cambio |
|---|---|
| Donde viva el marker `"esal"` del detector de donaciones | Cambiar a regex con `\besal\b` (word-boundary). |

**Verificación previa.**
```bash
grep -n '"esal"' src/lia_graph/pipeline_d/case_detectors*.py \
    src/lia_graph/pipeline_d/case_bullets/donaciones.py
```

**Flag.** Ninguno — fix puramente surgical. Anti-test en
`test_planner_case_anchor_registry.py` que asegure que
"desalarización" / "desalarizacion" NO fire donaciones.

**Gate 3 — success criterion.**
- "qué es la desalarización UGPP" → NO fire donaciones
- "qué es una ESAL" → SÍ fire donaciones (regresión check)

**Esfuerzo.** ~30 minutos. Test + edit + re-probe.

---

### §1.5+ Issues E, F, G… — slot for next-discovered

A medida que el operador siga probando y aparezcan nuevos
síntomas, registrar aquí ANTES de editar código. Plantilla:

```
### §1.N Issue X — <nombre corto>
**Síntoma para el contador.** <una frase>
**Ejemplo capturado.** <fecha + topic + pregunta literal + qué falló>
**Root cause.** <módulo + por qué>
**Module donde aterriza el fix.** <tabla file/cambio>
**Flag.** <nombre + default>
**Gate 3 — success criterion.** <tabla métrica antes / meta>
**Rollback.** <recipe>
```

Slots reservados §1.5, §1.6, §1.7, §1.8. Si se necesita §1.9+,
considerar si v18 está sobrecargado y abrir fix_v19.

---

## §2. Six-gate lifecycle (mandatory per issue)

Heredado de CLAUDE.md Non-Negotiables y `feedback_verify_fixes_end_to_end`.
Ningún issue salta gates. Ningún issue mezcla gates (qualitative-pass
en una NO baja el bar de la siguiente, per
`feedback_gates_evaluate_independently`).

| Gate | Qué es | Quién la cierra | Pass condition |
|---|---|---|---|
| 1. Idea | One-sentence statement de la mejora | Engineer | claro y narrow |
| 2. Plan | Módulo más narrow + diff esperado | Engineer | <500 LOC tocadas |
| 3. Success criterion | Métrica numérica medible | Engineer + Operator | escrita verbatim en §1.N |
| 4. Test plan | Actores + environment + decision rule | Engineer + Operator | tabla en §1.N |
| 5. Greenlight | Operator re-asks fixture en dev:staging | Operator | "lo mandaría as-is" |
| 6. Refine-or-discard | Si gate 5 falla, iterar o discard explícito | Engineer + Operator | registrado en `docs/aa_next/playbook_regressions.md` |

**Lifecycle de status para cada issue:**

```
🛠 idea → 🛠 plan → 🧪 código + unit tests verdes → 
shadow telemetría → análisis FP → 🧪 panel-validated → 
✅ enforce + operator greenlight → end of line
```

Si en cualquier paso el operator falla el sign-off → 🛠 refine →
back to shadow. Después de 2 iteraciones sin convergencia →
↩ discard explícito.

---

## §3. Suggested batch order

| Batch | Issues | Razón |
|---|---|---|
| v18 b1 | A (chunk-noise) + D (donaciones substring) | A es el más visible para el contador. D es trivial pero independiente — se puede colar en el mismo PR. |
| v18 b2 | B (codigo aliasing validator) | Validator-only, patrón fix_v15 ya probado. Independiente de A. |
| v18 b3 | C (SPEC bullet preservation) | El más invasivo (toca polish prompt + nuevo validator). Última en el orden para tener ya feedback de A + B sobre el shadow→enforce loop. |
| v18 b4+ | E, F, G… si surgen | Cada nuevo issue se evalúa con §2 lifecycle antes de batch. |

Estimado total: ~3 días engineer + ~2 horas operator probes
(re-asks de los fixtures + sign-off).

---

## §4. Captured failure cases (regression fixtures)

Cada fixture es una pregunta literal del operador que reprodujo un
issue. Sirven como tests de regresión cada vez que un fix se
candidatea a flip a `enforce`.

### §4.1 Fixture A — chunk-noise leak (Issue A)

- **Pregunta literal:** *"¿Cómo liquido a un empleado que despedí
  sin justa causa, salario $4.000.000, 4 años de antigüedad,
  contrato indefinido?"*
- **Topic:** `liquidacion_terminacion` (v17 b1)
- **Fecha de captura:** 2026-05-15 PM
- **Bullets noise observados (verbatim):**
  1. "Despido sin justa causa (...): código 55."
  2. "Despido con justa causa (...): código 56."
  3. "Despido injustificado en AÑO 1: 45 días de salario." (regla
     pre-Ley 789, derogada 2002 — contradice al SPEC)
  4. "Antes: 30 días × ($2.200.000 ÷ 30) = $2.200.000."
  5. (más fragmentos según el día)
- **Criterio pass post-fix:** ≤ 1 bullet noise antes del primer
  SPEC bullet; cero contradicciones con el SPEC.

### §4.2 Fixture B — codigo ET/CST aliasing (Issue B)

- **Pregunta literal:** *"¿Cómo liquido a un empleado que despedí
  sin justa causa, salario $4.000.000, 4 años de antigüedad,
  contrato indefinido?"* (misma pregunta — surfaces ambos issues)
- **Topic:** `liquidacion_terminacion`
- **Fecha:** 2026-05-15 PM
- **Output literal observado:**
  ```
  Anclaje Legal
  • Art. 127-132 ET — Definición de salario.   ← son CST
  • Art. 186 ET — Derecho al descanso.         ← es CST
  ```
- **Criterio pass post-fix:** ningún `art:<num>` listado con código
  ET que en realidad sea de otro código (CST / Ley / Decreto), en
  Anclaje Legal Y en bullets corridos.

### §4.3 Fixture C — SPEC bullet dropped (Issue C)

- **Pregunta:** misma que §4.1 (la concreción de números es lo que
  trip polish-drop)
- **Topic:** `liquidacion_terminacion`
- **Fecha:** 2026-05-15 PM
- **Bullet SPEC perdido:**
  > "**Indemnización moratoria — CST art. 65:** durante los
  > **primeros 24 meses** después del retiro = **1 día de salario
  > por cada día de mora**. A partir del **mes 25** = intereses
  > moratorios a tasa máxima legal (DTF + sobretasa). Procede solo
  > si el empleador no demuestra buena fe (Sentencia C-892/2009 —
  > modulación). No es automática — el trabajador debe demandar."
- **Criterio pass post-fix:** los 7 bullets del SPEC aparecen en la
  respuesta servida (con margen de 1 para fusiones razonables).

### §4.4 Fixture D — donaciones substring collision (Issue D)

- **Pregunta:** *"¿qué es la desalarización en una fiscalización
  UGPP?"*
- **Topic esperado:** `ugpp_fiscalizacion`
- **Comportamiento previo:** `is_donaciones_case` fires por
  contener `"esal"` substring → answer cita Art. 257 ET
  (descuento donaciones) en lugar de Art. 178 Ley 1607 (UGPP).
- **Criterio pass post-fix:** sources NO contienen
  `donaciones_anchor`; sources SÍ contienen
  `ugpp_fiscalizacion_anchor`.

### §4.5 — Fixture E — (placeholder)

Cuando el operator capture una nueva falla, agregar aquí con la
misma plantilla:

```
- Pregunta literal:
- Topic:
- Fecha de captura:
- Output literal observado:
- Issue al que aplica (A / B / C / D / nuevo):
- Criterio pass post-fix:
```

---

## §5. Rollback per fix

Todos los fixes de v18 son rollback-en-un-flag (excepto Issue D que
es surgical y se revierte con `git revert`).

| Issue | Flag rollback | Efecto |
|---|---|---|
| A | `LIA_PRACTICA_NOISE_FILTER=off` | Filtro no corre; bullets pasan tal cual al draft. |
| A | `LIA_PRACTICA_NOISE_FILTER=shadow` | Filtro corre + telemetría; output no cambia. |
| B | `LIA_POLISH_CODIGO_VALIDATOR=off` | Validator no corre; polish output pasa sin chequear. |
| B | `LIA_POLISH_CODIGO_VALIDATOR=shadow` | Validator corre + telemetría; polish output no se rechaza. |
| C | `LIA_POLISH_SPEC_PRESERVATION=off` | Polish permissive — puede drop bullets. |
| C | `LIA_POLISH_SPEC_PRESERVATION=shadow` | Validator corre + telemetría; polish output no se rechaza. |
| D | `git revert <sha>` | Restaura la substring `"esal"` original. Anti-test desaparece con el revert. |

**Full v18 rollback** (improbable): `git revert` de los commits de
v18 — sin efectos colaterales en v17 ni en versiones anteriores.

---

## §6. Mirror surfaces (qué actualizar al merge)

Cada batch de v18 requiere actualizar:

1. **`docs/orchestration/orchestration.md`** — bump del env-matrix
   version (`v2026-MM-DD-fix-v18-...`) + entry en `### Change Log`.
2. **`docs/guide/env_guide.md`** sección "Runtime Retrieval Flags"
   — añadir las nuevas flags A/B/C con su default `shadow`.
3. **`CLAUDE.md`** sección "Active runtime flags" — añadir las
   3 flags nuevas + su semántica.
4. **`frontend/src/app/orchestration/shell.ts` +
   `orchestrationApp.ts`** — sin cambios (no afecta env-matrix
   render, solo es content polish).
5. **Este documento** (§0.1 status snapshot + §7 ship-state).

---

## §7. Ship-state table (update as fixes land)

| Issue | Status | Probe verdict | Notas |
|---|---|---|---|
| A — chunk-noise filter | 🧪 | pending shadow run on dev:staging | Code landed 2026-05-15 evening. `LIA_PRACTICA_NOISE_FILTER=shadow` default. 14 new unit tests verdes. Chunk-level patterns also landed en `chunk_quality_heuristics.py` (3 nuevos motivos: `pre_ley_marker_dominant`, `orphan_numeric_example_dominant`, `software_code_isolated_dominant`). |
| B — codigo aliasing validator | 🛠 | — | Captured 2026-05-15 PM same probe. Plan ready. |
| C — SPEC bullet preservation | 🛠 | — | Captured 2026-05-15 PM same probe + §0.2.1 v17 reference. Plan ready. |
| D — donaciones substring | 🧪 | pending operator re-probe | Code landed 2026-05-15 evening. `is_donaciones_case`: bare `"esal"` substring → word-boundary regex (`\besal\b`). 2 anti-tests verdes (`test_donaciones_does_not_fire_on_desalarizacion_ugpp`, `test_donaciones_still_fires_on_bare_esal_token`). Patrón hereda fix_v16 `is_rte_esal_case`. |

Current totals (2026-05-15 evening): **0 ✅, 2 🧪, 2 🛠** (de 4
ítems iniciales; slot para E+ abierto).

### §7.1 v18 b1 landing record (2026-05-15 evening)

- **Files touched (4):**
  - `src/lia_graph/pipeline_d/case_detectors.py` — Issue D, ~15 LOC
  - `src/lia_graph/pipeline_d/answer_synthesis_practica.py` — Issue A per-line filter, ~110 LOC
  - `src/lia_graph/pipeline_d/chunk_quality_heuristics.py` — Issue A chunk-level patterns, ~50 LOC
  - `tests/test_planner_case_anchor_registry.py` + `tests/test_answer_synthesis_practica.py` + `tests/test_chunk_quality_heuristics.py` — 21 new tests
- **Flags introduced:**
  - `LIA_PRACTICA_NOISE_FILTER` (`off | shadow | enforce`, default `shadow`). `legacy` también acepta como alias de `off`.
- **Test deltas:**
  - `tests/test_planner_case_anchor_registry.py`: +2 (`test_donaciones_does_not_fire_on_desalarizacion_ugpp` + `test_donaciones_still_fires_on_bare_esal_token`)
  - `tests/test_answer_synthesis_practica.py`: +14 (modo + per-line + integración con stubs)
  - `tests/test_chunk_quality_heuristics.py`: +4 (3 patrones nuevos + 1 negative-control para pre-ley)
- **Trace step nuevo:** `practica.noise_filter.applied` con `filter_mode`, `outcome ∈ {pass, shadow_hit, suppressed, noop}`, `dropped_total`, `dropped_reasons`, `shadow_total`, `shadow_reasons`.
- **Próximo paso (operator):** restart `dev:staging`, re-probe el fixture §4.1 (mismo texto literal), verificar:
  - `retrieval_backend=supabase` en first response
  - `pipeline_trace.steps[*].name == "practica.noise_filter.applied"` con `outcome ∈ {pass, shadow_hit}`
  - Si shadow registra drops sin falsos positivos → flip `LIA_PRACTICA_NOISE_FILTER=enforce` y re-probe.

Lifecycle (heredado de fix_v17_may §12):
- 🛠 — plan + idea, sin código
- 🧪 — código + unit tests verdes, shadow no corrido aún
- 🛡 — shadow telemetría corriendo, panel pendiente
- ✅ — enforce + operator-validated en dev:staging
- ↩ — regresó y se descartó con razón en
  `docs/aa_next/playbook_regressions.md`

---

## §8. Author notes para el agente que ejecuta

- **Granularity.** Por `feedback_granular_edits`, no apilar fixes en
  módulos ≥ 1000 LOC. `answer_llm_polish.py` está en ~700 LOC; los
  nuevos validators caben. Si crece >1000 LOC, extraé los validators
  a `pipeline_d/answer_polish_validators.py` sibling.
- **No money in status reports** (`feedback_no_money_quoting`).
  Tiempo + alcance + qué desbloquea — no dólares.
- **No text walls** (CLAUDE.md Non-Negotiable). Bullets, listas,
  tablas — nunca párrafos de prosa.
- **Update este doc en el MISMO commit que el código**
  (`feedback_recommendations_logged_in_canonical_plan`).
- **Default run mode dev:staging** (`feedback_default_run_mode_staging`).
  Verificá `retrieval_backend=supabase` en la primera respuesta de
  cualquier probe.
- **SME panel solo on-demand** (`feedback_sme_panel_explicit_request_only`).
  No auto-corras `scripts/eval/run_sme_parallel.py`.
- **Validators heredados del patrón fix_v15.** Leé
  `_no_invented_uvt_ranges` en `answer_llm_polish.py` antes de
  escribir el primer validator nuevo — la forma se copia 1:1
  (cue-gating + trace step + shadow/enforce ramp).

---

*End of fix_v18_may.md.*
