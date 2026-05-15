# fix_locos.md — ideas ambiciosas (catálogo de referencia)

> **Qué es esto.** Catálogo de ideas grandes que **podrían ser muy
> buenas O podrían explotar**. NO son un plan. NO tienen owner. NO
> tienen fecha. Se documentan acá para que cuando alguien (humano o
> LLM) diga "deberíamos hacer X", se pueda preguntar primero: "¿ya
> está en fix_locos.md? ¿qué tradeoff registramos?"
>
> **Cuándo promover una idea de acá a `fix_vN_may.md`:**
> 1. Aparece un caso real que SOLO esa idea resuelve.
> 2. El tradeoff del "podría backfire" se puede mitigar con un MVP narrow.
> 3. Hay greenlight del operador para gastar 2+ semanas de ingeniería.
>
> Si no se cumplen los tres, la idea se queda acá.

---

## §1. Ideas catalogadas

### §1.1 Vigencia anotada a nivel valor numérico (no solo a nivel norma)

- **Sketch.** Hoy `norm_vigencia_history` registra el estado de la **norma** (V/VM/DE/SP/IE). La idea ambiciosa: durante canonicalización, cada **valor numérico** en un chunk de practica recibe una etiqueta temporal — "45 días" → `valid_until=2002-12-28` + `superseded_by=ley_789_2002`. La synthesis filtra valores cuya ventana de validez no contiene la fecha "as of" del usuario.
- **Por qué podría ser buena.** Cierra estructuralmente la familia entera de bugs "regla anterior se cuela como bullet". Resuelve 30-vs-45-días, ICA antes de 1983, RST antes de Ley 2277, etc.
- **Por qué podría backfire.**
  - Requiere re-canonicalizar TODOS los chunks de practica (~1.463 cloud). Costo Gemini/DeepSeek significativo.
  - El LLM tiene que distinguir "esta cifra es la regla vigente" vs "esta cifra es contexto histórico" — no trivial; falsos positivos arruinan SPECs vigentes legítimos.
  - Schema expansion: nueva tabla `chunk_value_annotations` o columna JSONB. Requiere migration, indexación, backfill.
  - El paciente puede morir en la mesa: 6 meses de trabajo para resolver lo que Issue E (gate de conflicto de valores) probablemente resuelve en ½ día con 80 % del beneficio.
- **Prerequisito.** SPEC value conflict gate (Issue E) en producción + telemetría que demuestre que el caso NO está cubierto por SPECs (sea recurrente y diverso, no solo CST 64).
- **Scope estimado si se ejecutara.** 4-6 semanas: 1 semana plan + extractor; 2 semanas re-canon + validación; 1 semana sink + retriever; 1 semana panel SME.

---

### §1.2 Detector semántico de contradicciones por embeddings

- **Sketch.** Después del template assembly, calcular embedding por bullet. Para cada par de bullets dentro de un `query_mode` (ej. todos los de "Recomendaciones Prácticas"), si la similitud semántica es **muy alta** PERO un campo numérico difiere → flag como conflicto.
- **Por qué podría ser buena.** No requiere conocer la respuesta correcta de antemano; solo detecta que dos bullets están "hablando de lo mismo con números distintos".
- **Por qué podría backfire.**
  - Embeddings no entienden números bien (`30 días` y `45 días` parecen casi idénticos al embedding — el detector siempre marca conflicto).
  - Falsos positivos en pares legítimos: "Régimen general: 30 % impuesto" y "Régimen SIMPLE: 5.4 % impuesto" son MUY similares pero NO contradicen.
  - Requiere infra de embeddings en tiempo real (latencia + costo).
- **Prerequisito.** Que Issue E (gate determinístico por SPEC) no cubra ≥ 80 % de los casos.
- **Scope estimado.** 1 semana POC + 2 semanas tuning + paneles. Alto riesgo de descarte.

---

### §1.3 LLM-juez sobre la respuesta final (post-polish)

- **Sketch.** Después del polish, llamar a un LLM con prompt "Acá hay una respuesta. ¿Dos afirmaciones se contradicen entre sí? Lista los pares contradictorios". Si hay → rechazar la respuesta y re-sintetizar.
- **Por qué podría ser buena.** Captura contradicciones que ningún regex puede detectar; trabaja a nivel semántico.
- **Por qué podría backfire.**
  - Doble latencia LLM (polish + judge). El usuario espera el doble.
  - El juez puede inventar contradicciones que no existen (hallucination).
  - El juez puede no detectar contradicciones reales si están sutilmente fraseadas.
  - Loop infinito si el re-synthesis vuelve a producir el conflicto.
- **Prerequisito.** Caching agresivo de respuestas (para amortizar el costo) + telemetría que muestre que las contradicciones son frecuentes.
- **Scope estimado.** 1 semana + tuning continuo. Riesgo: nunca converge a un prompt que sea preciso y rápido.

---

### §1.4 Grafo de aserciones de valor en Falkor

- **Sketch.** Además de `:ArticleNode` y `:NormNode`, agregar `:ValueAssertion` nodes — cada valor numérico citado en cualquier doc se convierte en un nodo con edges a `:NormNode` (qué norma lo afirma) + `:TimePeriod` (en qué ventana es válido). El retriever consulta el grafo para validar que el valor afirmado por el chunk es coherente con la norma vigente.
- **Por qué podría ser buena.** Estructura el conocimiento legal en su forma natural — "el art. 64 CST afirma 30 días desde 2003 y antes afirmaba 45 días". El grafo se vuelve la fuente de verdad estructurada.
- **Por qué podría backfire.**
  - Explosión combinatoria: ~20.000 chunks × ~5 valores numéricos por chunk = ~100.000 nodos nuevos. Hace falta planificar el sharding.
  - Extracción de "valor + norma + ventana" es difícil para el LLM (puede confundir el contexto).
  - El grafo desactualizado es PEOR que no tener grafo — un valor mal tagged genera mensajes con autoridad inflada.
- **Prerequisito.** Disciplina de gobernanza del grafo (procesos para detectar y corregir tags incorrectos).
- **Scope estimado.** 6-8 semanas. Esto es un proyecto, no un fix.

---

### §1.5 Resolución de conflictos por trust-tier de proveedor

- **Sketch.** Cuando dos bullets afirman valores distintos para el mismo predicado, ganar el que viene del chunk con `trust_tier` más alto en `provider_trust_tiers.json`.
- **Por qué podría ser buena.** No requiere LLM extra ni schema nuevo. Reusa la infra de trust-tiers ya existente (fix_v11A Phase 11A).
- **Por qué podría backfire.**
  - Un proveedor `high` puede tener un párrafo histórico también; ganar por autoridad no es lo mismo que ganar por veracidad.
  - Los SPECs internos (los que escribimos nosotros) no están en el `provider_trust_tiers.json`. Necesitarían un tier propio.
  - Si todos los chunks involucrados son del mismo tier, no desempata.
- **Prerequisito.** SPEC-tier definido + auditoría de coverage del trust-tier en proveedores.
- **Scope estimado.** 1 semana. Bajo costo, beneficio incierto.

---

### §1.6 Ranker aprendido sobre pares "bullet bueno / bullet malo"

- **Sketch.** Fine-tune un modelo pequeño (sentence-transformer) sobre pares etiquetados por SME: "este bullet ES respuesta a esta pregunta", "este bullet NO ES respuesta". Reemplazar las heurísticas de `chunk_quality_heuristics` por el score del modelo.
- **Por qué podría ser buena.** Generaliza a casos nunca vistos sin escribir regex.
- **Por qué podría backfire.**
  - Hace falta ≥ 5.000 pares etiquetados para fine-tuning decente. Hoy tenemos ~50 SME-validated turns total.
  - Modelo opaco — cuando rechaza un bullet legítimo, no hay explicación.
  - Drift: si la corpus cambia, el modelo queda obsoleto.
- **Prerequisito.** Pipeline de etiquetado (SME labeling tool + workflow + presupuesto).
- **Scope estimado.** 8-12 semanas + dataset.

---

### §1.7 Recuperación temporal ("as of date")

- **Sketch.** Cada query del usuario carga implícita o explícitamente una fecha "vigencia at" (por defecto hoy). El retriever filtra chunks cuya norma está derogada/inexequible **a esa fecha**. Permite también consultas tipo "¿cómo se liquidaba antes de 2002?".
- **Por qué podría ser buena.** Soporta análisis histórico legítimo (auditorías, litigios sobre años pasados) sin contaminación entre épocas.
- **Por qué podría backfire.**
  - Las queries de usuario no traen fecha — habría que inferirla (¿por la pregunta? ¿por la fecha actual? ¿por el AG fiscal mencionado?).
  - Riesgo de inferir mal y dar la respuesta de un año equivocado.
  - El gate de vigencia ya soporta `chunk_vigencia_gate_for_period` — la infra está; lo que falta es el UI y la inferencia.
- **Prerequisito.** Diseño de UX para que el contador especifique el período (chip "AG 2024" / "AG 2025") + cobertura ≥ 95 % en `norm_citations`.
- **Scope estimado.** 3-4 semanas (mayormente UX + planner).

---

### §1.8 Extracción de tuplas por bullet (descomposición structured)

- **Sketch.** Cada bullet se descompone en tuplas `{sujeto, predicado, valor, norma_fuente, vigente_desde, vigente_hasta}` antes del render. Los gates trabajan sobre tuplas, no sobre líneas de markdown.
- **Por qué podría ser buena.** Análisis estructural completo. Permite gates determinísticos de cualquier dimensión (contradicción, derogación, falta de fuente, etc.).
- **Por qué podría backfire.**
  - Re-arquitectura de TODO el flujo de synthesis (rompe answer_synthesis_practica + answer_synthesis_sections + assembly).
  - LLM extraction de tuplas tiene su propia tasa de error.
  - "Es elegante" rara vez justifica un re-write de 5.000 LOC.
- **Prerequisito.** Demostración (en una rama experimental) de que esto cierra una clase de bugs que ninguna otra idea cierra.
- **Scope estimado.** 12+ semanas. Riesgo arquitectónico máximo.

---

### §1.9 Pipeline de active learning desde probes del operador

- **Sketch.** Cada vez que el operador probe una pregunta y dé un veredicto ("esta respuesta está bien" / "esta está mal, falta X / sobra Y"), grabamos el delta como dato de entrenamiento. Después de N probes, re-entrenamos el ranker / el clasificador / el polish prompt.
- **Por qué podría ser buena.** El sistema mejora con uso real, no solo con sprints planeados.
- **Por qué podría backfire.**
  - "Re-entrenar el polish prompt" no es algo bien definido — los LLMs no se fine-tunean con 50 ejemplos.
  - Riesgo de overfit a las preferencias de UN operador (lo que es claro para él puede ser confuso para otro contador).
  - Requiere disciplina de etiquetado que en práctica nadie sostiene.
- **Prerequisito.** Tooling de etiquetado en el UI + criterios de aceptación claros.
- **Scope estimado.** 4-6 semanas para el tooling + meses de uso para acumular dataset.

---

### §1.10 Disclosure "regla anterior" al usuario

- **Sketch.** En lugar de SUPRIMIR la contradicción, **mostrársela explícitamente al contador con framing histórico**. Si el sistema detecta dos valores conflictivos sobre el mismo predicado:
  > **Atención:** dos cifras aparecen en las fuentes para "indemnización año 1, despido sin justa causa":
  > - **Cifra vigente (post-Ley 789/2002):** 30 días de salario (CST art. 64 reformado).
  > - **Cifra anterior (régimen pre-2002, derogada):** 45 días de salario.
- **Por qué podría ser buena.** Enseña en lugar de ocultar. El contador aprende a distinguir, gana confianza en la herramienta porque ve que el sistema sabe la diferencia.
- **Por qué podría backfire.**
  - Si el sistema se equivoca al etiquetar "vigente" vs "derogada", educa MAL al contador con autoridad inflada.
  - Cargar al usuario con historia normativa cuando solo quería un cálculo → fricción.
- **Prerequisito.** Issue E + clasificador de "cuál de los dos valores es el vigente" (no trivial; nos lleva otra vez a §1.1 o §1.4).
- **Scope estimado.** Una vez que Issue E está, esto son 2-3 días de assembly/UX. Pero su precondición (saber cuál es la vigente) puede ser cara.

---

## §2. Anti-patrones registrados (cosas a NO hacer)

- **No subir el threshold de un gate cuando un caso falla.** Per `feedback_thresholds_no_lower`. Afinás la heurística o aceptás el caso como límite documentado, no relajás el bar.
- **No mezclar surfaces.** El gate de práctica no debe llamar al renderer de normativa. Cada surface tiene su pipeline (CLAUDE.md Surface Boundaries).
- **No re-ingestar cuando el problema es de synthesis/polish.** Re-ingestar 1.463 chunks porque 1 bullet falla en synthesis es overkill. Issue E (½ día) sobre re-canon (4-6 semanas) — siempre Issue E primero.
- **No prometer fix universal con LLM judge.** Hay 4 sprints (`fix_v11` §17, `fix_v14_2` A3, etc.) donde "agregamos un LLM al final" fue peor que la heurística determinística previa.

---

## §3. Cuándo revisar este documento

- Cada `fix_vN_may.md` cierre — agregar las ideas que surgieron y se descartaron explícitamente.
- Cuando un sprint planeado golpee la pared y haya tentación de "rewrite everything" — leer §2 antes de proponer §1.X.
- Cuando aparezca un caso real que SOLO una idea de §1 resuelve — promover a `fix_vN+1` con plan completo (idea / módulo / criterio / test / greenlight / refine-or-discard).

---

*Fin de fix_locos.md.*
