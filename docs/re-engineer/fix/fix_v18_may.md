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

### Paso 0 — TU PRIMERA RESPUESTA AL OPERATOR (mandatoria)

**Regla:** la primera respuesta del agente al operator al retomar
v18 DEBE seguir exactamente este shape de 3 secciones. No saltees,
no parafrasees, no agregues prosa antes de las secciones.

```markdown
**Dónde estamos:**

- v18 status: <X 🧪 / Y 🛠 / Z ✅> sobre los 5 issues iniciales.
- Último commit shipped: `<sha7>` — <una frase de qué hizo>.
- Branch state: <N> commits ahead of `origin/main`; <pushed | unpushed>.
- Flags actuales: <lista flags v18 + su default + qué hacen en una frase>.
- Lo que ya está en producción (post-merge si aplica): <lista>.
- Lo que está en shadow esperando validación: <lista>.

**Qué necesito de vos:**

- <1 a 3 acciones del operator, ordenadas por bloqueo. Concretas. Cada
  una debe ser ejecutable sin más contexto, e.g.:>
- 1. Reiniciar `dev:staging` y re-probe el §4.1 fixture (texto literal en §4.1).
- 2. Pegarme el trace JSONL de `practica.noise_filter.applied` +
     `synthesis.conflict_resolver.applied` desde
     `tracers_and_logs/logs/pipeline_trace.jsonl`.
- 3. Decidir: ¿flip A + E a `enforce` ahora, o esperás más turnos shadow?

**Próximos pasos en código (engineer queue):**

- <Lista ordenada de lo que YO haré si el operator da greenlight a cada item.>
- 1. Si shadow limpio → editar `scripts/dev-launcher.mjs` defaults
     (`LIA_PRACTICA_NOISE_FILTER=enforce`, `LIA_CONFLICT_RESOLVER_MODE=enforce`)
     + bump env-matrix version + Change Log row. 1 commit.
- 2. Arrancar v18 b3 = Issue B (codigo ET/CST aliasing validator, §1.2).
     Patrón fix_v15 UVT. ~½ día. Independiente de (1).
- 3. v18 b4 = Issue C (SPEC bullet preservation). ~1 día. Después de b3
     para ganar feedback del shadow→enforce loop.
- 4. (Si push pendiente) `git push origin main`.

¿Por dónde empezamos?
```

Llenar cada placeholder `<...>` con el estado real del doc (leés §0.1
+ §7 antes de responder). Si un valor no se puede verificar desde el
filesystem, marcalo `<desconocido — pregunto>` en lugar de inventar.

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
    tests/test_answer_synthesis_practica.py \
    tests/test_chunk_quality_heuristics.py \
    tests/test_answer_conflict_resolver.py -q
```

**Esperado (post-v18-b2):** `299 passed`. Si es menor, algo cambió
desde el último commit; investigá antes de actuar. Si es 226 estás
mirando un checkout anterior a b1 — `git pull` y vuelve a contar.

### Paso 3 — leé estas secciones EN ESTE ORDEN

1. **§0** TL;DR — qué es v18 y por qué existe.
2. **§0.1** Status snapshot — qué ya shipped vs qué falta.
3. **§1** Issues en scope — los 5 ítems (A/B/C/D/E) + slot para nuevos.
4. **§2** Six-gate lifecycle (no se salta ninguna gate).
5. **§3** Batch order — qué batch sigue.
6. **§4** Fixtures de regresión.
7. **§7** Ship-state + landing records — qué exactamente quedó en cada commit.
8. `docs/re-engineer/fix/fix_locos.md` — ideas ambiciosas catalogadas;
   leer ANTES de proponer un fix grande, NO es plan ejecutable.

### Paso 4 — identificá tu escenario

| Operador dice… | Escenario | Acción |
|---|---|---|
| *"retomá v18"* / *"continúa v18"* | Estado actual + próximo paso | Leé §0.1 + §7 + §3; respondé con próximo batch (b3 = Issue B) |
| *"shadow probe trae estos resultados"* | Operator pegó un trace del trace JSONL | Diagnose con la guía de §7.2 / §7.3 (operator-side probe). Si limpio → flip enforce |
| *"flip A a enforce"* / *"flip E a enforce"* | Operator validó shadow | Edit `scripts/dev-launcher.mjs`: el default que toque (A: `LIA_PRACTICA_NOISE_FILTER`; E: `LIA_CONFLICT_RESOLVER_MODE`). Commit + bump env-matrix |
| *"empezá b3"* / *"land Issue B"* | Validator ET/CST aliasing | §1.2 + §2 lifecycle. Patrón fix_v15 UVT validator. ~½ día |
| *"empezá Issue C"* | SPEC bullet preservation | §1.3 + §2 lifecycle. El más invasivo (toca polish prompt) |
| *"agregá un fixture, fallé esta pregunta"* | Capturá failure case nuevo | §4.5 slot. Si necesita módulo nuevo → §1.6 slot Issue F |
| *"qué sigue después de v18"* | Lookup F+ residuos / próximas ideas | `fix_locos.md` + §1.6 slot |

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
5. **Issue A NO atrapa la regla derogada sin marcador.** El filtro
   per-line (`pre_ley_lead` / `software_code_tail` / `orphan_numeric_calc`)
   catches bullets con marcadores explícitos. La regla pre-Ley-789
   "45 días" del §4.1 NO matchea ninguno de esos patrones — la
   catches Issue E (conflict resolver) que compara contra el
   excerpt del artículo vigente.
6. **Vigencia v3 opera a nivel norma, no a nivel valor dentro del
   chunk.** Cuando CST 64 está VM (vigente modificada), el gate
   deja pasar el chunk completo incluso si el texto adentro
   menciona la regla pre-2002. Por eso necesitamos Issue E como
   capa post-template. Ver §1.5 para la explicación arquitectural.
7. **El conflict resolver corre EN TODO TURNO**, no solo cuando
   hay conflicto. En shadow mode con cero conflictos el `outcome`
   es `no_conflicts` (no `shadow_hit`). Eso es esperado, no es
   un bug.
8. **`resolve_llm_adapter` puede devolver `None`** en tests sin
   `GEMINI_API_KEY`. El conflict resolver maneja eso como
   `a2_no_adapter` → ambos bullets sobreviven. Safe-default.

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

**Alcance.** 5 issues (A/B/C/D/E). A + D shipped en b1 (commit
`26bf04b`); E shipped en b2 (commit `bdc6adf`). B + C pendientes
(plan listo, sin código). Slot abierto para F+ si el operator
captura nuevas fallas. Cada uno es un fix narrow + un validator/filtro
nuevo. Sin cambios de schema, sin cambios de retrieval.

**Riesgo.** Bajo. Todos los validators arrancan en `shadow`
(telemetría sin efecto). Issue D es surgical y sin flag (anti-test
guarda la regresión).

**Esfuerzo.** Issue A (~1 día) ✅. Issue D (~30 min) ✅. Issue E
(~½ día reactivo) ✅. Issue B (~½ día) 🛠. Issue C (~1 día) 🛠.
Restante para cerrar v18: ~1.5 días eng + operator shadow probes.

**Estado al 2026-05-15 evening:** 3 🧪 (A/D/E shipped, pending
operator validation), 2 🛠 (B/C plan ready). 0 ✅ aún. Próximo
batch: b3 = Issue B (codigo ET/CST aliasing validator).

---

## §0.1 Status snapshot — 2026-05-15 (evening, post-b2 + cleanup)

| Issue | Estado | Commit | Capturado por | Plan / Landing record |
|---|---|---|---|---|
| A — práctica chunk-noise filter | 🧪 shadow default; pending operator validation | `26bf04b` | probe `liquidacion_terminacion` (2026-05-15 PM) + probe `aportes_proporcionales_tiempo_parcial` (2026-05-15 PM) | §1.1 plan + §7.1 landing |
| B — codigo ET/CST aliasing validator | 🛠 plan ready, no code | — | mismas probes (`Art. 127-132 ET` debería ser CST) | §1.2 plan |
| C — SPEC bullet preservation | 🛠 plan ready, no code | — | `liquidacion_terminacion` probe (CST 65 moratoria intermitente — dropped en una corrida, presente en la siguiente; confirma que es estocástico) | §1.3 plan |
| D — donaciones substring fix | 🧪 surgical, pending operator re-probe | `26bf04b` | observado durante v17 b2 — `is_donaciones_case` keys on bare `esal` → colisiona con `desalarizacion` | §1.4 plan + §7.1 landing |
| E — conflict resolver (A+A1+A2) | 🧪 shadow default; b2.1 wiring refine + b2.2 A2 prompt strengthen landed; pending operator re-probe | `bdc6adf` + `cea1337` + b2.2 | b2 shadow trace returned `no_conflicts` (wiring wrong) → b2.1 fixed wiring, shadow now detects but A2 returns NINGUNA on ambiguous excerpts → b2.2 strengthens A2 prompt to allow LLM training-knowledge fallback for known reformas (Ley 50/789/1010/1429/1607/1819/2010/2277) | §1.5 plan + §7.2 + §7.5 + §7.6 |

**Aggregate counts:** 3 🧪 + 2 🛠 + 0 ✅. Próximo batch = **v18 b3 = Issue B** (validator only, patrón fix_v15).

Status legend (heredado de fix_v17_may §12):
- 🛠 — idea + plan, sin código
- 🧪 — código + tests verdes locales, shadow no corrido aún por operator
- 🛡 — shadow telemetría corriendo en `dev:staging`, panel pendiente
- ✅ — enforce + operator-validated en `dev:staging`
- ↩ — regresó y se descartó con razón en `docs/aa_next/playbook_regressions.md`

**Commits shipped en v18 (en orden):**
- `26bf04b` — v18 b1: Issue A (práctica noise filter, shadow) + Issue D (donaciones substring fix, surgical)
- `bdc6adf` — v18 b2: Issue E (conflict resolver A+A1+A2, shadow)
- `4487c33` — orchestration.md cleanup (retire predecessor banner pile-up + collapse April LOC-refactor rows)
- `cea1337` — v18 b2.1: Issue E refine — resolver wiring moved pre-polish → post-polish after §4.1 shadow miss (300 tests verdes)
- `abd3292` — v18 b2.2: Issue E refine — A2 prompt strengthen authorizing LLM training-knowledge fallback when corpus excerpts are ambiguous (301 tests verdes)

Reference doc creado en el mismo ciclo: `docs/re-engineer/fix/fix_locos.md` (catálogo de ideas ambiciosas, NO plan ejecutable).

**Operator-side TODOs pendientes (no son código):**
1. Re-probe §4.1 fixture en `dev:staging` shadow → verificar trace de `practica.noise_filter.applied` + `synthesis.conflict_resolver.applied`.
2. Si shadow limpio → flip A + E a `enforce` (un commit; ver §7.4).
3. Re-probe Issue D fixture (`¿qué es la desalarización UGPP?`) → verificar `donaciones_anchor` NO aparece en sources.
4. Decidir si arrancar v18 b3 (Issue B) ahora o después de validar A/D/E en producción.
5. Push del branch a `origin/main` (4 commits ahead al cierre de v18 b2).

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

### §1.5 Issue E — value-conflict resolver (A + A1 + A2 fallback)

**Síntoma para el contador.** Dos viñetas con el mismo predicado
afirman valores numéricos distintos. Ejemplo de la §4.1 (probe
2026-05-15 PM):

```
- Despido injustificado en AÑO 1: 30 días de salario.   ← regla vigente
- Despido injustificado en AÑO 1: 45 días de salario.   ← pre-Ley 789/2002, derogada
```

Issue A no atrapa el caso porque ninguno de los dos bullets tiene
marcador `Antes:`, `código NN` ni shape de calc-orphan. La vigencia
v3 tampoco lo atrapa porque CST art. 64 está VM (vigente modificada)
— el gate ve el ancla como vigente y deja pasar el chunk; el texto
adentro del chunk no se audita.

**Root cause arquitectural.** El gate de vigencia opera a nivel
**norma**, no a nivel **valor dentro del párrafo de un chunk**.
Una práctica chunk puede legítimamente citar CST 64 (vigente) y
en el mismo párrafo describir el régimen anterior a 2002 con sus
cifras propias — el sistema no distingue cuál cifra es la vigente
porque el chunk no está etiquetado a ese nivel de granularidad.

**Decisión de operador (2026-05-15).** Implementar **Enfoque A
(detector) + A1 (article-match) con fallback a A2 (LLM)**, NO
Enfoque B (SPEC-as-truth) — A funciona en cualquier topic con
artículos vigentes en el bundle de evidencia, sin requerir SPECs
pre-escritos.

**Module donde aterriza el fix.**

| File | Cambio |
|---|---|
| `pipeline_d/answer_conflict_resolver.py` | **Nuevo módulo.** ~360 LOC. Detector + A1 (article-match) + A2 (LLM fallback) + apply_resolutions. |
| `pipeline_d/orchestrator.py` | Llamada a `resolve_answer_conflicts(answer, evidence, runtime_config_path)` **después** de `polish_graph_native_answer` + del `polish_rejected fallback` block, antes de `on_llm_delta`. (Refined post-polish en b2.1, 2026-05-15 evening; ver §7.5 para el rationale.) Try/except envuelve la llamada — el resolver nunca bloquea el pipeline. |
| `scripts/dev-launcher.mjs` | Default `LIA_CONFLICT_RESOLVER_MODE=shadow` para los 3 modos. |

**Algoritmo.**

1. **Detector.** Parsea cada bullet line (regex `^\s*[\-\*•]\s+`).
   Extrae predicado = texto antes del primer `:`, normalizado
   (strip markdown, lowercase, strip acentos, collapse whitespace).
   Skip predicados de < 2 palabras (demasiado genéricos). Extrae
   valor numérico = primer match de `{currency, UVT, SMMLV, %, días/meses/años}`
   en el texto después del `:`. Agrupa bullets por predicado. Un
   grupo es conflicto si tiene ≥ 2 bullets con `value_norm` distintos.
2. **A1 — article-match.** Concatena `evidence.primary_articles[*].title + .excerpt`,
   normaliza. Para cada valor candidato, busca su forma normalizada
   en el blob. Si **exactamente uno** aparece → ese gana, el otro se
   descarta. Si 0 o ≥ 2 aparecen → `a1_ambiguous`, intenta A2.
3. **A2 — LLM fallback.** Prompt acotado: "Tenés dos afirmaciones
   sobre la misma regla. Cuál es la vigente hoy? Respondé A o B o
   NINGUNA". Usa el mismo adapter que polish (`resolve_llm_adapter`).
   Errores del LLM se capturan como `a2_error` — pipeline continúa
   sin modificar el answer.
4. **Apply.** Solo en `enforce`: drop loser bullet lines del markdown.
   En `shadow`: telemetría únicamente.

**Flag.** `LIA_CONFLICT_RESOLVER_MODE ∈ {off, shadow, enforce}`.
Default `shadow` al merge. `legacy` es alias de `off`.

**Trace step.** `synthesis.conflict_resolver.applied` con
`mode`, `outcome ∈ {off, no_conflicts, shadow_hit, applied, applied_no_drops, unresolved, noop_empty_input}`,
`groups_detected`, `groups_resolved_a1`, `groups_resolved_a2`,
`groups_unresolved`, `lines_dropped`, `decisions[]` (por grupo:
`predicate`, `path`, `winner_line_index`, `loser_count`,
`a2_response_preview`).

**Gate 3 — success criterion.**

| Métrica | Antes (probe §4.1 / 2026-05-15) | Meta `enforce` |
|---|---|---|
| Bullets contradictorios al SPEC en `Recomendaciones Prácticas` | 1 (45 días vs 30 días) | 0 |
| Casos resueltos por A1 vs A2 sobre 50 probes shadow | n/a | A1 ≥ 70 %, A2 ≤ 30 %, unresolved ≤ 10 % |
| Falsos positivos (SPEC bullet legítimo dropeado) | n/a | 0 en 50 probes |
| Latencia adicional por turno | 0 | ≤ +500 ms cuando A2 corre; 0 ms cuando solo A1 |

**Gate 4 — test plan.**

| Stage | Actor | Environment | Pass condition |
|---|---|---|---|
| 1. Unit tests | Engineer | local | 28 cases verdes en `tests/test_answer_conflict_resolver.py` (detector + A1 + A2 + modes + §4.1 fixture e2e) |
| 2. Shadow telemetría 1-2 días | Operator | dev:staging | Trace step `synthesis.conflict_resolver.applied` con `outcome ∈ {shadow_hit, no_conflicts}` ≥ 30 turnos |
| 3. Análisis de FP | Engineer | local sobre traces | < 5 % decisiones de A1 marcan un SPEC bullet legítimo como loser |
| 4. Operator re-probe | Operator | dev:staging enforce | Misma §4.1 sale con 30 días + sin 45 días |
| 5. Sign-off | Operator | dev:staging | "lo mandaría a un contador as-is" |

**Gate 5 — greenlight.** Operator re-pregunta §4.1 con
`LIA_CONFLICT_RESOLVER_MODE=enforce` → un solo bullet de
indemnización año 1 (30 días), CST 65 moratoria intacto, SPEC
tables intactas.

**Gate 6 — refine-or-discard.**
- Refine: si shadow muestra FP > 5 %, afinar `_extract_value` o
  `_normalize_predicate` (qué shape colisiona indebidamente).
- Discard: si después de 2 iteraciones la tasa de FP no baja del 5 %
  → revertir a `LIA_CONFLICT_RESOLVER_MODE=off` y promover Enfoque B
  (SPEC-as-truth, Issue E v2) como reemplazo.

**Rollback.** `LIA_CONFLICT_RESOLVER_MODE=off` (o `=legacy`)
revierte al comportamiento pre-Issue-E. El módulo + tests quedan
en el repo behind the flag.

**Notas arquitectónicas.**

- A1 reusa `primary_articles` que ya están en el bundle de
  evidencia — cero queries Falkor extra.
- A2 reusa el mismo adapter LLM que polish — cero infra nueva.
- Wiring point está DESPUÉS de polish (refined en b2.1, 2026-05-15
  evening; antes era pre-polish). Polish normaliza el phrasing de
  los predicados, así que las contradicciones recién convergen a
  predicado idéntico post-render. El §4.1 shadow probe expuso el
  bug del wiring original (`outcome: no_conflicts` con bullets
  contradictorios visibles); el fix está en §7.5.
- El resolver nunca raises hacia arriba — try/except en el caller
  garantiza que un bug aquí no rompe el chat.
- Por qué NO Enfoque B (SPEC-as-truth) ahora: B solo cubre los ~40
  topics con SPECs escritos. A cubre cualquier topic con artículos
  vigentes en el grafo — más generalizable. B queda registrado en
  `fix_locos.md` como path forward si A no rinde.

---

### §1.6+ Issues F, G… — slot for next-discovered

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

Slots reservados §1.6, §1.7, §1.8. Si se necesita §1.9+,
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

## §3. Batch order — historial y plan restante

| Batch | Issues | Estado | Commit | Razón / notas |
|---|---|---|---|---|
| v18 b1 | A (chunk-noise filter) + D (donaciones substring fix) | ✅ shipped 2026-05-15 evening | `26bf04b` | A más visible para el contador; D trivial e independiente colado en el mismo commit. Shadow validation pendiente. |
| v18 b2 | E (conflict resolver A+A1+A2) | ✅ shipped 2026-05-15 evening | `bdc6adf` | Surgió reactivo durante validación de b1: el §4.1 fixture mostró que A no cubre la regla pre-Ley-789. Operador ordenó "implementa YA" Enfoque A + A1 + A2 sobre Enfoque B (SPEC-as-truth). |
| v18 b2.1 | E refine — wiring post-polish | ✅ shipped 2026-05-15 evening | `cea1337` | §4.1 shadow probe regresó `no_conflicts` aunque el answer servido mostraba 30 vs 45 días bullets. Diagnóstico: el resolver corría pre-polish; polish es el productor que normaliza los predicados a la misma forma. Fix: mover llamada a post-polish + 1 test pinning la shape polished. Plan en §7.5. |
| v18 b2.2 | E refine — A2 prompt strengthen | ✅ shipped 2026-05-15 evening | `abd3292` | Re-probe post-b2.1 mostró que el detector ya funciona (`groups_detected: 1`) pero A2 LLM responde `NINGUNA` porque los excerpts mencionan ambas cifras (30 y 45 días) sin marcador explícito de cuál es la vigente. Fix: reescribir A2 prompt para autorizar al LLM a usar su conocimiento de derecho colombiano vigente cuando los excerpts son ambiguos; nombra las reformas conocidas (Ley 50/789/1010/1429/1607/1819/2010/2277). Plan en §7.6. |
| v18 b3 | B (codigo ET/CST aliasing validator) | 🛠 next | — | Validator-only, patrón fix_v15 UVT ya probado. ~½ día. Plan en §1.2. Independiente de A/D/E. |
| v18 b4 | C (SPEC bullet preservation) | 🛠 después de b3 | — | El más invasivo (toca polish prompt + nuevo validator). Última en el orden para tener feedback de A+B+E en shadow→enforce loop. ~1 día. Plan en §1.3. |
| v18 b5+ | F, G… si surgen | reserva | — | Cada nuevo issue se evalúa con §2 lifecycle antes de batch. |

**Estimado restante:** ~1.5 días eng (b3 + b4) + operator shadow
validation por batch.

**Orchestration cleanup pass** (no es batch v18 pero shipeó en la
misma sesión, commit `4487c33`): retiró 200+ líneas de banner
pile-up en `docs/orchestration/orchestration.md` (predecessor
sections duplicaban el Change Log) y colapsó 13 rows de
LOC-refactor de abril en una row summary. File de 1233 → 1019
líneas. Acción mecánica de housekeeping; cero impacto runtime.

---

## §4. Captured failure cases (regression fixtures)

Cada fixture es una pregunta literal del operador que reprodujo un
issue. Sirven como tests de regresión cada vez que un fix se
candidatea a flip a `enforce`.

### §4.1 Fixture A — chunk-noise leak (Issue A) + value-conflict (Issue E)

Esta pregunta única ejercita TRES issues a la vez: A (códigos + Antes:),
E (30 vs 45 días), B (Art. 127-132 ET → CST). Es la fixture canónica
de v18.

- **Pregunta literal:** *"¿Cómo liquido a un empleado que despedí
  sin justa causa, salario $4.000.000, 4 años de antigüedad,
  contrato indefinido?"*
- **Topic:** `liquidacion_terminacion` (v17 b1)
- **Fecha de captura:** 2026-05-15 PM
- **Fecha de probe shadow más reciente:** 2026-05-15 evening
  (operator pegó el output completo; bullets noise + contradicción
  + Art. 127-132 ET todos presentes — esperado en shadow).
- **Bullets noise observados (verbatim):**
  1. "Despido sin justa causa (...): código 55." → atrapa Issue A `software_code_tail`
  2. "Despido con justa causa (...): código 56." → atrapa Issue A `software_code_tail`
  3. "Despido injustificado en AÑO 1: 30 días de salario." → SPEC correcto (no se toca)
  4. "Despido injustificado en AÑO 1: 45 días de salario." → atrapa Issue E (mismo predicado que #3, valor diferente)
  5. "Antes: 30 días × ($2.200.000 ÷ 30) = $2.200.000." → atrapa Issue A `pre_ley_lead` + `orphan_numeric_calc`
- **Anclaje Legal observado:**
  - "Art. 127-132 ET — Definición de salario." → atrapa Issue B (deberían ser CST 127-132)
  - "Art. 186 ET — Derecho al descanso." → atrapa Issue B (debería ser CST 186)
- **Criterio pass post-fix (enforce de A + E + B):**
  - 0 bullets `código NN` en `Recomendaciones Prácticas`
  - 0 bullets que empiecen con `Antes:` / orphan-calc
  - 0 contradicciones con el SPEC (solo "30 días" sobrevive, no "45 días")
  - 0 referencias `Art. <N> ET` en Anclaje Legal que en realidad sean CST
- **Estado actual (2026-05-15 evening):**
  - Issue A: 🧪 shadow — bullets noise siguen visibles, trace debe mostrar `shadow_hit`
  - Issue E: 🧪 shadow — contradicción 30 vs 45 días sigue visible, trace debe mostrar `groups_detected ≥ 1` + `groups_resolved_a1 ≥ 1`
  - Issue B: 🛠 — bullet ET/CST sigue visible, sin código aún

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
| A | `LIA_PRACTICA_NOISE_FILTER=off` (o `=legacy`) | Filtro no corre; bullets pasan tal cual al draft. |
| A | `LIA_PRACTICA_NOISE_FILTER=shadow` | Filtro corre + telemetría; output no cambia. |
| B | `LIA_POLISH_CODIGO_VALIDATOR=off` (planeado) | Validator no corre; polish output pasa sin chequear. |
| B | `LIA_POLISH_CODIGO_VALIDATOR=shadow` (planeado) | Validator corre + telemetría; polish output no se rechaza. |
| C | `LIA_POLISH_SPEC_PRESERVATION=off` (planeado) | Polish permissive — puede drop bullets. |
| C | `LIA_POLISH_SPEC_PRESERVATION=shadow` (planeado) | Validator corre + telemetría; polish output no se rechaza. |
| D | `git revert 26bf04b` | Restaura la substring `"esal"` original. Anti-tests desaparecen con el revert. |
| E | `LIA_CONFLICT_RESOLVER_MODE=off` (o `=legacy`) | Conflict resolver no corre; ambos bullets sobreviven. |
| E | `LIA_CONFLICT_RESOLVER_MODE=shadow` | Detect + log + run A1/A2 telemetría; output no cambia. |

**Full v18 rollback** (improbable): `git revert bdc6adf 26bf04b`
revierte b2 + b1 sin efectos colaterales en v17 ni en versiones
anteriores. Conservar `4487c33` (cleanup) — es cosmético del doc.

---

## §6. Mirror surfaces (qué actualizar al merge)

Cada batch de v18 requiere actualizar:

1. **`docs/orchestration/orchestration.md`** — bump del env-matrix
   version (`v2026-MM-DD-fix-v18-...`) + entry corto en `### Change Log`
   (bullets, NO wall-of-text — el row de v18 b2 ya es el modelo).
   También bumpear "Current version:" header del Env Matrix section.
2. **`docs/guide/env_guide.md`** — banner top + section
   "Runtime Retrieval Flags" — añadir la flag nueva con su default
   `shadow` y descripción de qué hace.
3. **`CLAUDE.md`** — bumpear `## Runtime Read Path (Env vXXX)` header
   + agregar bullet a "Active runtime flags" con la flag nueva.
4. **`frontend/src/app/orchestration/shell.ts` +
   `frontend/src/features/orchestration/orchestrationApp.ts`** —
   sin cambios necesarios para Issues A/B/C/D/E (no afectan
   env-matrix render). Solo bumpear si agregás un query_mode nuevo.
5. **Este documento** (`fix_v18_may.md`):
   - §0.1 status snapshot — flip issue status + commit ref
   - §3 batch order — marcar batch como ✅ shipped con commit
   - §7 ship-state table — flip status + agregar §7.N landing record
   - §-1 Paso 2 — bumpear count esperado si cambia
   - §-1 Paso 4 — ajustar el escenario table si cambia el "next batch"

**Mirror-surfaces shipping status para los commits ya en main:**

- `26bf04b` (b1 = A+D) — ✅ todos los mirrors actualizados.
- `bdc6adf` (b2 = E) — ✅ todos los mirrors actualizados.
- `4487c33` (cleanup) — N/A (cosmético del doc).

Si retomás y ves discrepancia entre `CLAUDE.md` / `orchestration.md` /
`env_guide.md`, **`orchestration.md` gana** per CLAUDE.md
Non-Negotiables. Reconciliar los otros dos hacia él.

---

## §7. Ship-state table (update as fixes land)

| Issue | Status | Probe verdict | Notas |
|---|---|---|---|
| A — chunk-noise filter | 🧪 | pending shadow run on dev:staging | Code landed 2026-05-15 evening. `LIA_PRACTICA_NOISE_FILTER=shadow` default. 14 new unit tests verdes. Chunk-level patterns also landed en `chunk_quality_heuristics.py` (3 nuevos motivos: `pre_ley_marker_dominant`, `orphan_numeric_example_dominant`, `software_code_isolated_dominant`). |
| B — codigo aliasing validator | 🛠 | — | Captured 2026-05-15 PM same probe. Plan ready. |
| C — SPEC bullet preservation | 🛠 | — | Captured 2026-05-15 PM same probe + §0.2.1 v17 reference. Plan ready. Intermitencia confirmada — CST 65 moratoria presente en probe del 2026-05-15 evening. |
| D — donaciones substring | 🧪 | pending operator re-probe | Code landed 2026-05-15 evening. `is_donaciones_case`: bare `"esal"` substring → word-boundary regex (`\besal\b`). 2 anti-tests verdes (`test_donaciones_does_not_fire_on_desalarizacion_ugpp`, `test_donaciones_still_fires_on_bare_esal_token`). Patrón hereda fix_v16 `is_rte_esal_case`. |
| E — conflict resolver (A+A1+A2) | 🧪 | pending shadow re-probe on dev:staging post-b2.1 | Code landed 2026-05-15 evening (b2 batch); wiring refined post-polish in b2.1 same evening after §4.1 shadow miss (see §7.5). `LIA_CONFLICT_RESOLVER_MODE=shadow` default. 29 unit tests verdes. Nuevo módulo `pipeline_d/answer_conflict_resolver.py` (~360 LOC). Wired post-polish (después del polish-rejected fallback block, antes del `on_llm_delta` callback) — polish normaliza predicados así que las contradicciones recién convergen a misma forma post-render. A1 reusa primary_articles (cero queries Falkor extra); A2 reusa adapter polish (cero infra nueva). |

Current totals (2026-05-15 evening): **0 ✅, 3 🧪, 2 🛠** (de 5
ítems; slot para F+ abierto).

### §7.1 v18 b1 landing record — commit `26bf04b` (2026-05-15 evening)

- **Files touched (4 + 3 test):**
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
- **Próximo paso (operator):** ver §7.4.

### §7.2 v18 b2 landing record — commit `bdc6adf` (2026-05-15 evening, después de §4.1 probe)

- **Files touched (3 + 1 test):**
  - `src/lia_graph/pipeline_d/answer_conflict_resolver.py` — Issue E, **NUEVO** módulo (~360 LOC)
  - `src/lia_graph/pipeline_d/orchestrator.py` — wiring + módulo-level `LOGGER`, ~20 LOC
  - `scripts/dev-launcher.mjs` — default `LIA_CONFLICT_RESOLVER_MODE=shadow`
  - `tests/test_answer_conflict_resolver.py` — **NUEVO**, 28 tests
- **Flags introduced:**
  - `LIA_CONFLICT_RESOLVER_MODE` (`off | shadow | enforce`, default `shadow`). `legacy` alias de `off`.
- **Algoritmo (referencia rápida — el detalle vive en §1.5):**
  1. Detector: bullets con mismo predicado normalizado pero distinto `value_norm` → conflict group.
  2. A1: chequear cada valor contra `evidence.primary_articles[*].title+.excerpt` blob normalizado; si exactamente 1 matches → ese gana.
  3. A2: si A1 ambiguo (0 o ≥ 2 matches), llamar al adapter LLM polish-grade con prompt `A | B | NINGUNA`. Errores wrapped, nunca crash el pipeline.
- **Wiring point:** entre `synthesis.template_built` y `polish_graph_native_answer` en `orchestrator.run_pipeline_d`. Polish recibe template saneado de contradicciones en enforce.
- **Trace step nuevo:** `synthesis.conflict_resolver.applied` con `mode`, `outcome ∈ {off, no_conflicts, shadow_hit, applied, applied_no_drops, unresolved, noop_empty_input}`, `groups_detected`, `groups_resolved_a1`, `groups_resolved_a2`, `groups_unresolved`, `lines_dropped`, `decisions[]` (per-group `predicate`, `path ∈ {a1_article_match, a2_llm_choice, a1_ambiguous, a2_no_adapter, a2_no_decision, a2_unparseable, a2_error}`, `winner_line_index`, `loser_count`, `a2_response_preview`).
- **Reuse, not new infra:** A1 reusa el bundle de evidencia existente (cero queries Falkor extra); A2 reusa el mismo `resolve_llm_adapter` que polish (cero infra nueva). Sin schema migration. Sin tabla nueva.
- **Reference doc creado:** `docs/re-engineer/fix/fix_locos.md` — catálogo de Enfoque B (SPEC-as-truth) + 9 ideas ambiciosas más, como referencia de futuro path forward si Enfoque A no rinde.

### §7.3 Orchestration doc cleanup — commit `4487c33` (2026-05-15 evening, post-b2)

- **No es batch v18** — housekeeping mecánico per operator request "do a pass on orchestration.md to erase really old content".
- **`docs/orchestration/orchestration.md`:** 1233 → 1019 líneas (−214).
- **Cortes:**
  - Retirado ~200 líneas de predecessor-banner pile-up al tope del file (todo lo que vivía como "Predecessor: v..." > blocks; duplicaba el Change Log table).
  - Colapsadas 13 rows del Change Log de abril (`ui1-ui13` + `decouplingv1`) en una row summary (`v2026-04-18-thru-22-granularization-campaign`) — eran pure LOC-refactors sin runtime impact. Las rows `ui14` + `ui15` se mantienen separadas (real HTTP/feature work). Original per-round narratives preservadas en git history pre-2026-05-15.
- **Fixed:** stale "Current version:" header del Env Matrix section (decía v15, ahora v18-b2).
- **Cero impacto runtime** — solo docs.

### §7.5 v18 b2.1 refine record — Issue E wiring post-polish (2026-05-15 evening, after §4.1 shadow miss)

- **Trigger.** Operator pegó el §4.1 probe + trace después de b2 merge. Trace mostró:
  - `practica.noise_filter.applied` → `shadow_hit`, `shadow_total: 6`, `shadow_reasons: {software_code_tail: 5, pre_ley_lead: 1}` — Issue A funcionando como diseñado.
  - `synthesis.conflict_resolver.applied` → `outcome: no_conflicts` — Issue E **NO** detectó el caso 30 vs 45 días aunque ambos bullets aparecían en el answer servido.
- **Diagnóstico.** Test directo: `detect_conflicts(answer_post_polish)` retorna 1 group correctamente; pero la wiring del orchestrator llamaba al resolver **entre `synthesis.template_built` y `polish_graph_native_answer`** — es decir, sobre el template pre-polish. Polish reescribe los predicados a una forma normalizada (`Despido injustificado en AÑO 1:` para ambos bullets) que solo converge a misma `predicate` después de rendering. En el template los dos bullets tenían shapes distintas (presumiblemente sub-bullets de chunks distintos con phrasings distintos) → detector no los agrupaba.
- **Fix.** Mover la llamada `resolve_answer_conflicts(...)` en `orchestrator.run_pipeline_d` desde **pre-polish** (post-`synthesis.template_built`) a **post-polish** (después del `polish_rejected fallback` block, antes del `on_llm_delta` callback). Cero cambios al módulo del resolver, cero nuevos flags, cero cambios de schema.
- **Files touched (2 + 1 test):**
  - `src/lia_graph/pipeline_d/orchestrator.py` — remove pre-polish call (-20 LOC), insert post-polish call (+25 LOC con comment explicativo de por qué post-polish). Net: ~+5 LOC.
  - `tests/test_answer_conflict_resolver.py` — `test_resolve_catches_polished_section_4_1_shape` (+45 LOC) pinning el shape post-polish (`•` lead, sin markdown bold, `Predicate: value` simple) → `groups_detected == 1`, `groups_resolved_a1 == 1`, A1 path `a1_article_match`, drop del 45-días bullet.
- **Tests:** v18 baseline 299 → **300** (28 → 29 in `test_answer_conflict_resolver.py`).
- **Trace impact.** Mismo trace step `synthesis.conflict_resolver.applied`, mismo schema de details. Solo cambia el momento en que se emite (después de `polish.applied` en lugar de antes).
- **Riesgo del cambio de wiring.** Mínimo. El resolver sigue siendo idempotente sobre su input; el wrapping `try/except` sigue garantizando que no bloquea el pipeline. El único cambio observable en `enforce` es que ahora puede dropear bullets que polish acabó de escribir — mismo safety profile que en b2.
- **Próximo paso (operator):** re-probe §4.1 en shadow → confirmar `outcome: shadow_hit`, `groups_detected: 1`, `decisions[0].path: a1_article_match`. Si limpio, flip A + E a enforce per §7.4.

### §7.6 v18 b2.2 refine record — A2 prompt strengthen (2026-05-15 evening, after §4.1 post-b2.1 shadow re-probe)

- **Trigger.** Operator re-probó §4.1 después del b2.1 wiring fix. Server restart confirmado (PID nuevo a las 12:36 PM Bogotá, log nuevo a las 12:37 PM). Trace post-restart:
  - `practica.noise_filter.applied` → `shadow_hit` (Issue A funcionando).
  - `synthesis.conflict_resolver.applied` → **`outcome: unresolved`**, `groups_detected: 1`, `groups_resolved_a1: 0`, `groups_resolved_a2: 0`, `groups_unresolved: 1`, `decisions[0]: { predicate: "despido injustificado en año 1", path: "a2_no_decision", a2_response_preview: "NINGUNA" }`.
  - `polish.applied` → `mode: rejected` (segundo issue ortogonal, fuera de scope b2.2).
- **Diagnóstico.** El detector ya funciona post-b2.1 ✅. Pero:
  - A1 falla porque ambos valores (`30 días` y `45 días`) aparecen en los `primary_articles[*].excerpt` blob — el chunk de CST 64 cita la cifra actual Y la histórica derogada → A1 retorna `a1_ambiguous`.
  - A2 corre con el LLM real (no es problema de adapter), pero responde `NINGUNA` porque sigue las reglas del prompt al pie de la letra: "si los excerpts no permiten decidir, NINGUNA". El LLM tiene conocimiento de la reforma Ley 789/2002 pero el prompt no lo autoriza a usarlo.
- **Fix.** Reescribir `_A2_PROMPT_TEMPLATE` para autorizar explícitamente el fallback a conocimiento del LLM cuando los excerpts son ambiguos:
  - Rule 1 (reordenada): elegí la cifra que los excerpts marcan como vigente.
  - Rule 2 (reordenada): si los excerpts muestran una opción modificada/derogada, descartala.
  - **Rule 3 (NUEVA):** si los excerpts son ambiguos PERO el LLM puede identificar con ALTA CONFIANZA cuál cifra rige hoy (especialmente para reformas conocidas — Ley 50/1990, 789/2002, 1010/2006, 1429/2010, 1607/2012, 1819/2016, 2010/2019, 2277/2022), elegí esa.
  - Rule 4 (NUEVA): NINGUNA solo si NI los excerpts NI el conocimiento permiten decidir.
- **Files touched (1 + 1 test):**
  - `src/lia_graph/pipeline_d/answer_conflict_resolver.py` — solo el `_A2_PROMPT_TEMPLATE` literal (~25 LOC), cero cambios al algoritmo, cero cambios a `_parse_a2_response` ni a `resolve_via_a2`.
  - `tests/test_answer_conflict_resolver.py` — `test_a2_prompt_authorizes_llm_knowledge_fallback` (+25 LOC) pin las nuevas reglas (`"ALTA CONFIANZA"`, `"Ley 789/2002"`, `"NI los excerpts NI tu conocimiento"`).
  - Mismo file, fix colateral en `test_resolve_enforce_a1_ambiguous_no_adapter_keeps_both`: monkeypatch explícito de `_resolve_llm_adapter_safe` → `None`. Sin el monkeypatch, el test era flaky — funcionaba "por suerte" porque el LLM real respondía NINGUNA al input ambiguo. Con el nuevo prompt el LLM decide, así que el test ahora declara su intención (no-adapter) en lugar de depender de un side effect del prompt anterior.
- **Tests:** v18 baseline 300 → **301** (29 → 30 in `test_answer_conflict_resolver.py`).
- **Riesgo del cambio.** Medio. Allows LLM training to drive the decision when corpus is ambiguous — there's a real but bounded risk of hallucination. Mitigation:
  - Stays in `shadow` until operator validates ≥30 turns of A2 decisions (trace's `a2_response_preview` makes every call auditable).
  - Per gate-6: if FP rate > 5 % after this iteration → discard Issue E (current arquitectura) y promover Enfoque B (SPEC-as-truth) catalogado en `fix_locos.md`.
- **Próximo paso (operator):** re-probe §4.1 en shadow → confirmar:
  - `outcome: shadow_hit` (no más `unresolved`).
  - `decisions[0].path: "a2_llm_choice"`.
  - `decisions[0].winner_line_index` = índice del bullet de 30 días.
  - `decisions[0].a2_response_preview: "A"` o `"B"` (no `"NINGUNA"`).
  - Si confirmado limpio → flip A + E a enforce per §7.4. Si A2 sigue respondiendo NINGUNA → discard Issue E + promover Enfoque B.
- **Polish-rejected como issue ortogonal.** El `polish.applied mode: rejected` observado en la misma probe es un segundo signal — el answer servido viene del `_compose_polish_rejected_fallback` path. Fuera de scope de b2.2. Si después de b2.2 el A2 decide pero el answer servido no cambia, hay que diagnosticar el `_polish_skip_reason` (registrado en trace `polish.applied.skip_reason`) — eso es Issue G futuro.

### §7.4 Operator probe + flip-to-enforce recipe (próximo paso real)

**Paso 1 — restart staging:**

```bash
kill $(pgrep -f "lia_graph.ui_server") 2>/dev/null
pkill -f "scripts/dev-launcher" 2>/dev/null; true
npm run dev:staging
```

**Paso 2 — re-probe §4.1 (texto literal):**

> ¿Cómo liquido a un empleado que despedí sin justa causa, salario $4.000.000, 4 años de antigüedad, contrato indefinido?

**Paso 3 — verificar trace** (en la sección diagnostics del response, o en `tracers_and_logs/logs/pipeline_trace.jsonl`):

```bash
tail -200 tracers_and_logs/logs/pipeline_trace.jsonl \
    | jq 'select(.step == "practica.noise_filter.applied" or .step == "synthesis.conflict_resolver.applied")'
```

Esperado en shadow:

- `practica.noise_filter.applied` → `outcome: "shadow_hit"`, `shadow_reasons: {"software_code_tail": 2, "pre_ley_lead": 1, "orphan_numeric_calc": 1}` (o subset).
- `synthesis.conflict_resolver.applied` → `outcome: "shadow_hit"`, `groups_detected: 1`, `groups_resolved_a1: 1`, `decisions[0].path: "a1_article_match"`, `winner_line_index = <índice del bullet 30 días>`.

**Paso 4 — flip a enforce (si shadow limpio):**

Editar `scripts/dev-launcher.mjs`, cambiar 2 defaults:

```js
env.LIA_PRACTICA_NOISE_FILTER = "enforce";    // (era "shadow")
env.LIA_CONFLICT_RESOLVER_MODE = "enforce";   // (era "shadow")
```

Después: bump env-matrix version en orchestration.md / env_guide.md / CLAUDE.md a `v2026-MM-DD-fix-v18-enforce-A-E`. Agregar Change Log row corto. Commit. Restart staging. Re-probe.

**Paso 5 — verificar enforce limpia el answer:**

Esperado:

- Bullets `código 55` / `código 56` AUSENTES de Recomendaciones Prácticas.
- Bullet `Antes: 30 días × ...` AUSENTE.
- Bullet `45 días de salario` AUSENTE (Issue E drop).
- Bullet `30 días de salario` PRESENTE (SPEC correcto).
- Bullet CST 65 moratoria PRESENTE si la corrida tiene suerte (Issue C es estocástico, queda pendiente).
- `Art. 127-132 ET — Definición de salario` SIGUE PRESENTE (Issue B no shipped aún → ver §1.2 para arrancar v18 b3).

Si hay falso positivo (un SPEC bullet legítimo se dropeó) → `feedback_thresholds_no_lower`: NO subir el threshold, refinar la heurística específica. Re-shadow, re-probe.

(Status legend completo en §0.1.)

---

## §8. Author notes para el agente que ejecuta

- **Granularity.** Por `feedback_granular_edits`, no apilar fixes en
  módulos ≥ 1000 LOC. `answer_llm_polish.py` está en ~700 LOC; los
  nuevos validators caben. Si crece >1000 LOC, extraé los validators
  a `pipeline_d/answer_polish_validators.py` sibling. El conflict
  resolver de Issue E ya está como sibling (`answer_conflict_resolver.py`,
  ~360 LOC) — patrón a seguir.
- **No money in status reports** (`feedback_no_money_quoting`).
  Tiempo + alcance + qué desbloquea — no dólares.
- **No text walls** (CLAUDE.md Non-Negotiable). Bullets, listas,
  tablas — nunca párrafos de prosa. Aplica a este doc y a cualquier
  Change Log row en `orchestration.md`. Verificá tu output antes de
  commit — un row > 1 línea sin `<br>` o `•` ya es un wall.
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
  (cue-gating + trace step + shadow/enforce ramp). Para v18 b3
  (Issue B) ese es exactamente el patrón.
- **Conflict resolver es estructuralmente distinto.** Issue E no
  vive en `answer_llm_polish.py` porque NO es un polish-validator —
  corre ANTES de polish (entre `synthesis.template_built` y
  `polish_graph_native_answer`). Editar Issue E = editar
  `pipeline_d/answer_conflict_resolver.py`, no `answer_llm_polish.py`.
- **A2 LLM fallback puede fallar silencioso** si `GEMINI_API_KEY` no
  está en el env (tests, local sin keys). El resolver wrapea como
  `a2_no_adapter` y deja ambos bullets sobrevivir. Es safe-default
  intencional — no "arreglar" tratando de propagar el error.
- **Commit references a mano** (no `git log --oneline -1` cada vez):
  - `26bf04b` = v18 b1 = Issue A + D
  - `bdc6adf` = v18 b2 = Issue E
  - `4487c33` = orchestration cleanup
- **`fix_locos.md` no es plan, es referencia.** Si alguien (humano o
  LLM) propone "deberíamos hacer X" y X es ambicioso, primero leé
  `docs/re-engineer/fix/fix_locos.md` — probablemente ya está ahí
  con su tradeoff documentado. No promover ideas de locos sin que
  pasen los 3 criterios del header de ese doc.

---

*End of fix_v18_may.md.*
