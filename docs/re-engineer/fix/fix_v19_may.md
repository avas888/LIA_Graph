# fix_v19_may.md — Graph anchor disambiguation + ingestion gap (estructural)

> **Zero-agent-context protocol.** Documento autocontenido. Un agente
> nuevo, sin historial de conversación, puede ejecutarlo leyendo el
> filesystem. Verificá cada artefacto contra `git ls-files`. Si algo no
> existe, STOP y reportá drift.

---

## §0. TL;DR

- **Qué es v19.** Arreglo estructural del grafo + ingestión que destraba todos los problemas que v18 estaba parchando a nivel de polish/respuesta.
- **Por qué ahora.** v18 b2.1 + b2.2 expusieron que el conflict_resolver, el polish, y el citation allow-list TODOS están funcionando bien — pero reciben datos malos. La causa raíz es estructural y vive en el grafo + en la ingesta.
- **Alcance.** 4 problemas que se atacan juntos como una sola pieza estructural (ninguno se puede arreglar sin tocar los otros).
- **Riesgo.** Pre-producción → re-ingesta limpia sin migrar datos en vivo. Bajo riesgo operativo.
- **Esfuerzo.** ~5-6 días eng + 1 día de validación + SME panel.
- **Estado al 2026-05-15 evening:** Fase 1 ✅ (auditoría completa, este documento). Fase 2+ 🛠.

---

## §1. Audit findings (Fase 1 — 2026-05-15 evening)

### §1.1 Grafo Falkor (cloud staging) — inventario

| Métrica | Valor |
|---|---|
| Total ArticleNodes | **9,331** |
| ArticleNodes con `article_id` único | **9,331** (cero colisiones aparentes) |
| ArticleNodes desde RENTA/NORMATIVA (ET tributario) | **1,233** (13.2 %) |
| ArticleNodes desde Labor (CST + Leyes laborales) | **41** (0.4 %) |
| ArticleNodes desde SUIN/Leyes-otras (legislación general) | **7,398** (79.3 %) |
| ArticleNodes desde IVA/INC, Reforma Tributaria, CCo, Decreto | **259** (2.8 %) |
| TopicNodes totales | **87** |
| TopicNodes con `:TEMA → ArticleNode` edges | **0 (CERO)** |
| TopicNodes que matchean términos laborales | **2 de 87** (`laboral`, `renta_liquida_gravable` — el segundo es tangencial) |

### §1.2 Corpus Supabase (cloud staging) — inventario

| Métrica | Valor |
|---|---|
| Total `documents` | **6,818** |
| Total `document_chunks` | **20,154** |
| Docs con `topic=laboral` | **104** |
| Docs en paths de Labor (CST + Leyes labor) | **61** |
| Docs en paths de ET RENTA/NORMATIVA | **27** (el resto es chunks promovidos) |
| Docs en SUIN/Leyes-otras | **6,005** (88 %) |

### §1.3 Diagnóstico — los 4 problemas estructurales

1. **`article_id` sin código origen.** El grafo guarda `article_id="64"` como string puro sin discriminar si es ET 64, CST 64 o Ley 50/1990 art. 64. **Hoy no hay colisión** porque solo uno de los tres está ingestado por número, pero la falta de discriminación es lo que hace que CST 64 NO PUEDA ser ingestado sin pisar a ET 64.
2. **CST y Leyes laborales NO están en el grafo como ArticleNodes.** Solo **41 de 9,331** ArticleNodes son de fuentes laborales (0.4 %). El contenido del CST + Ley 50/1990 + Ley 789/2002 + Ley 100/1993 + Ley 1010/2006 + Ley 2466 EXISTE en el corpus como chunks (61 docs + sus chunks), pero la ingestion no los promueve a ArticleNode. Por eso el planner no puede anclar en CST 64 — el nodo no existe.
3. **TopicNodes están huérfanos.** Los 87 TopicNodes no tienen ningún `:TEMA` edge hacia ArticleNodes. El código del retriever (`retriever_falkor.py:103-138`) hace TEMA-first retrieval, pero el grafo no tiene los datos. Es feature-sin-datos.
4. **Taxonomía de topics muy gruesa para labor.** Solo `laboral` existe como TopicNode laboral. No hay `liquidacion_terminacion`, `nomina_mensual`, `prestaciones_sociales`, `pila_aportes` como TopicNodes — todos los temas laborales colapsan a `laboral`, lo cual diluye cualquier anchor por tema.

### §1.4 Confirmación del impacto

Probando §4.1 de fix_v18_may.md ("¿Cómo liquido a un empleado despedido sin justa causa..."):
- Topic router clasifica a `laboral` ✅ (correcto dado la granularidad).
- Case detector `is_liquidacion_terminacion_case` fire ✅.
- Case spec emite `anchor_articles=("108", "387")` — son ET tributarios. ❌ Los anchors CST 64/65/62 NO están en el spec porque el autor sabía que `"64"` resolvería a ET 64.
- TEMA-first retrieval contribuye 0 articles (los 87 topics están vacíos).
- `seed_article_keys` final: `["108", "387", "127-132", "16-19", "186"]` — TODOS ET tributarios.
- Conflict resolver A1 falla porque CST 64 (que tiene el "30 días") no está en `primary_articles`.
- Conflict resolver A2 LLM responde `NINGUNA` (consistente 5/5) porque las excerpts ET tributarias no aplican a la pregunta laboral.

---

## §2. Plan estructural — 6 fases

### §2.1 Fase 1 — Auditoría (½ día) ✅

- Inventariar ArticleNodes por código origen.
- Confirmar el gap de ingestión labor.
- Documentar TEMA edges vacíos.
- **Output**: §1 de este doc. **STATUS**: ✅ done 2026-05-15.

### §2.2 Fase 2 — Schema migration: compound keys (1-2 días) 🛠

**Idea.** Cambiar la clave de ArticleNode de `article_id="64"` a `node_key="cst:64"` / `"et:64"` / `"ley_50_1990:64"`.

**Plan narrow.**
- Definir taxonomía de códigos en config: `config/article_codigos.json` (lista cerrada: ET, CST, CCo, Ley_NNN_AAAA, Decreto_NNN_AAAA, ResolucionDIAN_NNN_AAAA, Sentencia_TT_NNN_AAAA).
- Migrar todos los ArticleNodes existentes — inferir código del `source_path` actual (RENTA/NORMATIVA → ET; LABORAL_SEGURIDAD_S → CST o Ley_50/789/100/1010; etc.).
- Agregar prop `codigo` + actualizar `article_id` a la forma compuesta.
- Migrar todos los edges (:TEMA, :MODIFIED_BY, :DEROGATED_BY, :IS_SUB_UNIT_OF, :CITES) — son edges por endpoint, así que solo el `node_key` cambia.

**Success criterion (medible).**
- 0 ArticleNodes sin `codigo` populated.
- 0 duplicaciones de `(codigo, article_id)`.
- Migración audita ANTES y DESPUÉS — count de nodes + edges idénticos.

**Test plan.**
- Unit tests del mapeo `source_path → codigo` (~30 casos cubriendo cada bucket conocido + un "OTHER" fallback que abort si no clasifica).
- Migration script con `--dry-run` que dumpea el plan sin escribir.
- Validación: query random de 20 ArticleNodes pre + post → headings idénticos.

**Rollback.** Backup completo del grafo antes de migrar (`docker exec falkor ... save dump`). Si la migración falla → restore.

### §2.3 Fase 3 — Re-ingesta limpia + promoción de CST/Ley labor (1-2 días) 🛠

**Idea.** Re-ingestar el corpus para que los 61 docs labor + sus chunks generen ArticleNodes correctos con `codigo=cst` o `codigo=ley_NNN_AAAA`.

**Plan narrow.**
- Actualizar `lia_graph/ingestion/falkor_sink.py` para que el código origen se infiera del `source_path` durante la ingesta + se persista como prop + entre en el `node_key`.
- Pre-producción → borrar el grafo + re-ingestar from scratch usando los veredictos Gemini que YA están cacheados (no re-corre la parte cara, solo la promoción a grafo).
- Verificar que CST 62, 64, 65 ahora existen como ArticleNodes distintos con `node_key="cst:64"` (NO colisiona con `"et:64"`).

**Success criterion.**
- ArticleNode `cst:64` existe + heading correcto (terminación unilateral con justa causa).
- ArticleNode `et:64` existe + heading correcto (disminución de inventario).
- ArticleNode `ley_50_1990:64` existe (si el corpus tiene ese artículo).
- Conteo total de ArticleNodes laborales sube de **41 → ≥ 200** (estimado).

**Test plan.**
- 5 probes manuales contra el grafo: cypher queries por `(codigo, numero)` para artículos CST conocidos.
- Idempotency: re-correr la ingesta 2 veces → mismo conteo.
- Comparar conteos por bucket vs auditoría Fase 1 — explicar deltas.

**Rollback.** Backup pre-Fase-3 → restore + flag de feature `LIA_INGESTION_COMPOUND_KEYS=off` que fuerza el formato viejo.

### §2.4 Fase 4 — Actualizar consumidores (1 día) 🛠

**Idea.** Todo lo que referencia `article_id` por número pelado pasa a usar `node_key` compuesto.

**Plan narrow — files a tocar (grep audit primero):**
- `src/lia_graph/pipeline_d/planner.py` — `_explicit_article_keys`, `_CASE_ANCHOR_REGISTRY` walk, `_build_article_search_queries`.
- `src/lia_graph/pipeline_d/retriever_falkor.py` — `_retrieve_primary_articles`, `_retrieve_tema_bound_article_keys`.
- `src/lia_graph/pipeline_d/case_bullets/*.py` — todos los specs con `anchor_articles=(...)` (≥ 40 archivos).
- `config/topic_norm_allowlist.json` — claves de articles.
- `config/subtopic_taxonomy.json` — si referencia articles.
- `config/comparative_regime_pairs.json` — referencias a articles.

**Success criterion.**
- Todos los case_specs pasan `anchor_articles=("cst:64", "cst:65", "cst:62", "et:108", "et:387", ...)` (compuestos).
- `topic_norm_allowlist.json` usa el formato compuesto.
- Tests existentes (v18 baseline 301) siguen verdes con la nueva forma de claves.

**Test plan.**
- Grep audit primero — listar TODOS los strings que parecen article keys (regex sobre `["']?\d{1,3}[-]?\d*["']?` en archivos relevantes) + clasificar uno por uno.
- Re-correr v18 baseline (`pytest tests/test_*.py`) post-cambio.
- Snapshot test: probe §4.1 → confirmar `seed_article_keys` ahora contiene `cst:64`.

**Rollback.** Git revert del commit de consumidores. La Fase 3 sigue válida (compound keys en el grafo no daña al planner viejo si fallback to legacy lookup).

### §2.5 Fase 5 — Poblar `:TEMA` edges + refinar taxonomía de topics (½-1 día) 🛠

**Idea.** Conectar cada TopicNode con sus articles anchor vía `:TEMA` edges, así TEMA-first retrieval finalmente steerea.

**Plan narrow.**
- Crear `config/topic_tema_anchors.json` con la forma:
  ```json
  {
    "laboral": ["cst:64", "cst:65", "cst:62", "ley_50_1990:11", "ley_789_2002:6", ...],
    "ica": ["et:115", "ley_14_1983:32", ...],
    "iva": ["et:420", "et:437", "et:476", ...],
    "declaracion_renta": ["et:5", "et:240", "et:241", ...]
  }
  ```
- Script `scripts/seed_topic_tema_edges.py` que lee el config + crea las :TEMA edges en Falkor.
- Subdividir `laboral` en sub-topics si tiene sentido (`liquidacion_terminacion`, `prestaciones_sociales`, `pila_aportes`, `salario_integral`) — o dejar `laboral` como umbrella + mejorar el TopicNode con sub-bucketing via SubTopicNode (que ya existe).

**Success criterion.**
- `MATCH (t:TopicNode {topic_key: 'laboral'})-[:TEMA]->(a) RETURN count(a)` ≥ **30**.
- Cada uno de los 12 topics-grandes (laboral, ica, iva, renta, retencion, etc.) tiene ≥ 10 TEMA edges.
- Probe §4.1 ahora muestra `seed_article_keys` empieza con `["cst:64", "cst:65", "cst:62", ...]` antes de los ET tributarios.

**Test plan.**
- Idempotency: re-correr el seeding 2 veces → mismo conteo.
- Probe §4.1 + 5 más fixtures (uno por código grande) → verificar `:TEMA` contributing.

**Rollback.** `MATCH ()-[r:TEMA]->() DELETE r` borra todos los edges; config sigue intacto para reintentar.

### §2.6 Fase 6 — Validación end-to-end + flip flags v18 a enforce (1 día + SME panel) 🛠

**Idea.** Una vez que primary_articles trae las normas correctas, los filtros de v18 que dejamos dormidos despiertan y funcionan.

**Plan narrow.**
- Re-probar las §4.1 (despido), §4.2 (CST anchor aliasing), §4.3 (CST 65 moratoria), §4.4 (UGPP/desalarización) de fix_v18.
- Re-probar 10 preguntas-caso adicionales — IVA, renta personas naturales, ICA, retención, deducciones, RST, etc.
- Verificar trace: `seed_article_keys` con compound keys, `primary_articles` con códigos correctos.
- Flip `LIA_PRACTICA_NOISE_FILTER=enforce`.
- Flip `LIA_CONFLICT_RESOLVER_MODE=enforce`.
- Correr SME panel.

**Success criterion.**
- §4.1 served answer: 0 bullets con `código NN`, 0 contradicciones 30 vs 45, anchor legal cita CST 64/65/62 (NO ET 108/387).
- SME panel acc+ ≥ 30/36 (vs baseline ~21/36).
- v18 baseline tests 301 → 301 (no regresión).

**Test plan.**
- 14 fixtures (4 de v18 + 10 nuevas), corridas por engineer.
- SME panel via `scripts/eval/run_sme_parallel.py` (operator-triggered, no auto-run).
- 1 día de operación normal con monitoring del trace para falsos positivos.

**Rollback.** Si SME baja → flip back to shadow + diagnose. Las fases 2-5 quedan landed.

---

## §3. Riesgos + mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Migration script malclasifica source_paths a códigos | Media | Alto (ArticleNodes con codigo equivocado) | Dry-run + audit manual de 50 paths random ANTES de aplicar |
| Re-ingesta tarda más de lo esperado | Media | Medio (un día perdido) | Veredictos Gemini cacheados; medible upfront probando ingesta de 100 docs primero |
| Compound key change rompe tests existentes | Alta | Bajo (tests fáciles de actualizar) | Run tests at end of Fase 4 explicitly, gate la Fase 5 en tests verdes |
| TEMA seeding mal puebla edges | Media | Alto (drift de retrieval) | Cap de 50 edges por topic + audit manual del config ANTES de seeding |
| `laboral` topic resulta demasiado coarse incluso post-fix | Baja | Medio (parche residual con sub-topics) | Reservar ½ día en Fase 5 para sub-topic refactor si necesario |
| El operador no confía en los compound keys + quiere otra forma | Baja | Alto (re-trabajo entero) | Acordar nombre exacto y forma del codigo:numero ANTES de Fase 2 |

---

## §4. Dependencies + ordering

- Fase 2 (compound keys) → Fase 3 (re-ingesta) — compound keys deben estar en el código antes de re-ingestar.
- Fase 3 → Fase 4 (consumidores) — los consumidores pueden actualizarse antes pero solo se validan con grafo re-ingestado.
- Fase 5 (TEMA) → Fase 6 — :TEMA edges deben existir para que el flip enforce de Issue E sea útil.
- Las fases 2-5 NO se pueden saltear ni colapsar en una. Cada una tiene su rollback independiente.

---

## §5. Files a crear o modificar

### Nuevos archivos
- `config/article_codigos.json` — taxonomía cerrada de códigos.
- `config/topic_tema_anchors.json` — mapping topic → article keys para sembrar TEMA edges.
- `scripts/migrate_falkor_compound_keys.py` — migration script (dry-run + apply).
- `scripts/seed_topic_tema_edges.py` — seeding script (idempotent).
- `tests/test_article_codigos_taxonomy.py` — tests del mapping source_path → codigo.
- `tests/test_falkor_compound_keys_migration.py` — tests del migration script.
- `tests/test_topic_tema_seeding.py` — tests del seeding.

### Modificados
- `src/lia_graph/ingestion/falkor_sink.py` — emit compound keys.
- `src/lia_graph/pipeline_d/planner.py` — case anchor registry walk uses compound keys.
- `src/lia_graph/pipeline_d/retriever_falkor.py` — primary_articles + tema queries use compound keys.
- `src/lia_graph/pipeline_d/case_bullets/*.py` — ~40 files, each updates `anchor_articles` tuple.
- `config/topic_norm_allowlist.json` — compound keys.
- `scripts/dev-launcher.mjs` — flip `LIA_PRACTICA_NOISE_FILTER=enforce` + `LIA_CONFLICT_RESOLVER_MODE=enforce` en Fase 6.
- `fix_v18_may.md` — close Issues B, E, with "blocked-then-resolved-by-v19".
- `CLAUDE.md` + `docs/orchestration/orchestration.md` + `docs/guide/env_guide.md` — bump env matrix version + add v19 row to Change Log.

---

## §6. Six-gate lifecycle per fase

Cada fase debe pasar los 6 gates de CLAUDE.md antes de ser declarada ✅:

1. **Idea** — Already done in §2.
2. **Plan** — narrow module + diff esperado (already in §2).
3. **Success criterion** — métrica numérica (already in §2).
4. **Test plan** — actores + environment + decision rule (already in §2).
5. **Greenlight** — Operator validates en `dev:staging` con probe relevante.
6. **Refine-or-discard** — Si gate 5 falla, iterar (max 2 vueltas) o discard explícito.

---

## §7. Estado al cierre de Fase 1 (2026-05-15 evening)

- Fase 1: ✅ done. Audit numbers en §1.
- Fase 2: 🛠 plan ready, no code.
- Fase 3: 🛠 plan ready.
- Fase 4: 🛠 plan ready.
- Fase 5: 🛠 plan ready.
- Fase 6: 🛠 plan ready.
- v18 b2.1 + b2.2 (conflict resolver) — keep `LIA_CONFLICT_RESOLVER_MODE=shadow`. Re-evaluate flip-to-enforce at end of Fase 6 when primary_articles flow correctly.

**Próximo paso (operator decision):**

- Greenlight para Fase 2 (compound keys) → empiezo con el migration-script dry-run + audit de 50 source paths random para validar el mapping.
- O bien, modificar el alcance / ordering del plan antes de empezar.

---

*End of fix_v19_may.md.*
