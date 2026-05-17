# fix_v19_may.md — Graph anchor alignment + ingestion gap (estructural) — v1

> **Zero-agent-context protocol.** Documento autocontenido. Un agente
> nuevo, sin historial de conversación, puede ejecutarlo leyendo el
> filesystem. Verificá cada artefacto contra `git ls-files`. Si algo no
> existe, STOP y reportá drift.

> **v1 changelog (2026-05-15 evening).** Esta es la revisión que
> incorpora la peer-review externa archivada en
> `docs/re-engineer/fix/fix_v19_review_external.md`. Cambios mayores
> vs v0:
>
> - Fase 0 **NUEVA** — pre-flight diagnostics (parser test + git
>   archaeology) ANTES de tocar schema. Puede cambiar el plan entero
>   si el bug raíz es del parser y no del schema.
> - Fase 2 retitulada: "alinear ArticleNode con la grammar canónica
>   `norm_id` existente" (`et.art.64`) en vez de inventar el formato
>   `et:64`. Reusa `canon.canonicalize()`.
> - Fase 4 LOC corregido (31 files, 62 hits) + bumped a 1.5-2 días +
>   split 4a (critical) / 4b (cleanup).
> - Fase 5 reescrita: recuperar la regresión del TEMA-seeding
>   (la feature YA EXISTE en código, está rota) ANTES de considerar
>   JSON-config hand-curated.
> - Fase 4 pre-flight: chequeo explícito de surfaces `Normativa` +
>   `Interpretación`.
> - Fase 6: 3-5 día shadow + diff harness + validator numérico sobre
>   output A2 del conflict resolver.
> - Nuevo §3.1: orden explícito de unwind para rollback de la
>   ensamblada.
> - Nuevo §8: preguntas abiertas (embeddings, dual-key `:Norm` vs
>   `:ArticleNode`).

---

## §0. TL;DR

- **Qué es v19.** Arreglo estructural del grafo + ingestión que destraba todos los problemas que v18 estaba parchando a nivel de polish/respuesta.
- **Por qué ahora.** v18 b2.1 + b2.2 expusieron que el conflict_resolver, el polish, y el citation allow-list TODOS están funcionando bien — pero reciben datos malos. La causa raíz es estructural y vive en el grafo + en la ingesta.
- **Alcance.** 4 problemas que se atacan juntos como una sola pieza estructural (ninguno se puede arreglar sin tocar los otros).
- **Riesgo.** Pre-producción → re-ingesta limpia sin migrar datos en vivo. Bajo riesgo operativo.
- **Esfuerzo (v1, post-review).** ~6-8 días eng + shadow 3-5 días + SME panel. (v0 había estimado 5-6 días — la diferencia viene del shadow period agregado + Fase 0 + Fase 4 corregida.)
- **Estado al 2026-05-15 evening:** Fase 1 ✅ (auditoría completa). Fase 0 🛠 next.

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
| TopicNodes con `:TEMA → ArticleNode` edges | **0 (CERO)** — feature regresada, no faltante |
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

1. **`article_id` sin código origen.** El grafo guarda `article_id="64"` como string puro sin discriminar si es ET 64, CST 64 o Ley 50/1990 art. 64. Hoy no hay colisión observada porque solo uno de los tres está ingestado por número.
2. **CST y Leyes laborales casi no están en el grafo como ArticleNodes.** Solo **41 de 9,331** (0.4 %). Los 61 docs labor en Supabase deberían producir ≥ 200 ArticleNodes. **Falta diagnóstico de POR QUÉ (Fase 0).** Hipótesis principal: parser regex (`parser.py:213`) no matchea los headings de los markdown laborales — probablemente `ARTÍCULO` mayúscula vs `Artículo`, o `Art.`, o listas numeradas — y los docs caen al `_whole_document_fallback` (`parser.py:171`) que emite **un** ArticleNode prose-only por documento.
3. **TopicNodes huérfanos por regresión.** Los 87 TopicNodes no tienen ningún `:TEMA` edge. PERO la feature existe en código (`loader.py:673-710` `_build_tema_edges`) y un comment histórico habla de "1,943 TEMA edges v4 populated". Es regresión, **no** missing feature. Hay que investigar git history.
4. **Taxonomía de topics gruesa para labor.** Solo `laboral` como TopicNode laboral. Sin sub-topics dedicados (`liquidacion_terminacion`, `nomina_mensual`, `prestaciones_sociales`, `pila_aportes`).

### §1.4 Confirmación del impacto

Probando §4.1 de fix_v18_may.md ("¿Cómo liquido a un empleado despedido sin justa causa..."):
- Topic router → `laboral` ✅.
- Case detector `is_liquidacion_terminacion_case` fire ✅.
- Case spec emite `anchor_articles=("108", "387")` — ET tributarios. ❌
- TEMA-first contribuye 0 articles.
- `seed_article_keys`: `["108", "387", "127-132", "16-19", "186"]` — TODOS ET tributarios.
- Conflict resolver A1 falla porque CST 64 NO está en `primary_articles`.
- Conflict resolver A2 responde `NINGUNA` (5/5 consistente).

### §1.5 Sistemas relacionados ya en producción (no inventamos formato nuevo)

| Sistema | Key format | Pinpoint |
|---|---|---|
| `public.norms` table | `norm_id text PK`, dotted grammar | `supabase/migrations/20260501000000_norms_catalog.sql` |
| `:Norm` Falkor node | `norm_id` dotted | `scripts/canonicalizer/sync_vigencia_to_falkor.py:154-211` |
| `canon.canonicalize()` | dotted, slots `.art.` / `.par.` / `.num.` / `.inciso.` / `.lit.` | `src/lia_graph/canon.py:58` |
| `topic_norm_allowlist.json` | `art:<number>` prefix | `config/topic_norm_allowlist.json` |
| `:ArticleNode.article_number` | bare numeric string | Falkor schema |

v19 **alinea ArticleNode al `norm_id` dotted** — NO inventa un cuarto formato.

---

## §2. Plan estructural — 7 fases (incluye Fase 0 pre-flight)

### §2.0 Fase 0 — Pre-flight diagnostics (1.5-2 horas) 🛠 next

**Idea.** Antes de tocar schema, validar empíricamente las dos hipótesis principales — el plan completo depende de esto.

**Plan narrow.**
1. **Parser test (1 hora).** Tomar un markdown CST real (`knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/...consolidado_Ley-50-1990.md` o `Codigo_Sustantivo_Trabajo.md` si existe) y correr `parse_articles()` directo. Output esperado: ≥ 50 articles. Si retorna 1 prose-only fallback → diagnóstico confirmado: el bug es del parser regex, **NO** del schema. En ese caso Fase 3 también necesita un fix de regex previo (low-risk, ~1 hora).
2. **TEMA git archaeology (30 min).** `git log -p -S "TEMA edge" -- src/lia_graph/ingestion/` y `git log --follow src/lia_graph/ingestion/loader.py | grep -i tema`. Identificar cuándo se cayeron los 1,943 edges. Si hay un commit reciente identificable → Fase 5 cambia de "hand-curate config" a "git revert + re-ingest". Si no hay regression identificable → mantener Fase 5 con seeding programático (NO hand-curated JSON).

**Success criterion (medible).**
- Parser test reporta count de articles parseados para 1 CST markdown.
- Git archaeology identifica (o descarta) commit responsable de la regresión TEMA.
- Output documentado en este doc como §2.0.x findings.

**Test plan.** Manual, engineer. Output verbatim pegado en este doc + commit del doc.

**Rollback.** N/A — solo lectura.

**Gate criteria para avanzar a Fase 2.**
- Si parser bug confirmado → arreglar regex primero (puede ser un quick patch en `parser.py`).
- Si TEMA regression identificable → planificar el revert antes de Fase 5.
- En ambos casos: actualizar este doc con findings antes de Fase 2.

---

#### §2.0.1 Fase 0 findings — parser test (2026-05-15 evening, sin pares editoriales)

- **Hipótesis del doc**: el regex de `parser.py:213` no matchea los headings CST/Ley laborales y los docs caen al `_whole_document_fallback`.
- **Resultado empírico**: HIPÓTESIS REFUTADA.
- **Cómo se midió**: ejecuté `parse_articles()` directo sobre los 10 markdowns de `knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/` + barrido completo del folder labor.
- **Tabla (10 markdowns consolidados):**

| Markdown | Articles parseados | Fallback? | Sample keys |
|---|---|---|---|
| Ley-50-1990.md | 6 | no | 23, 64, 249, 250, 251, 127-132 |
| Ley-789-2002.md | 7 | no | 1, 2, 3, 8, 14, 20, 22 |
| Ley-100-1993.md | 7 | no | 1, 2, 8, 9, 12, 15, 47 |
| Ley-2466-2025.md | 8 | **sí (section)** | datos-generales, objeto-y-alcance, art-culos-del-et-... |
| Ley-1822-2017.md | 9 | no | 1, 2, 3, 4, 5, 6, 7, 8 |
| Ley-1010-2006.md | 9 | no | 2, 3, 4, 7, 9, 12, 13, 14 |
| Ley-1468-2011.md | 8 | no | 1, 2, 3, 4, 5, 6, 7, 8 |
| Ley-797-2003.md | 9 | no | 1, 9, 11, 12, 13, 14, 15, 16 |
| Ley-2101-2021.md | 5 | no | 1, 2, 3, 4, 5 |
| Ley-27-1974.md | 9 | no | 1, 2, 3, 4, 6, 7, 9, 10 |

- **Barrido completo labor (44 archivos):** 323 unidades `ParsedArticle`, 50 pares únicos `(subdir, article_number)`, **0 docs caen a `_whole_document_fallback`**, 24 docs caen a `_section_fallback` (EXPERTOS / PRACTICA / NOMINA — comportamiento esperado y correcto: estos son guías sin `## Artículo N`).
- **El regex actual ya cubre** `re.IGNORECASE` (matchea `ARTÍCULO`), composites con guion (`127-132`), y los formatos `### ARTÍCULO 64. Título`. No hay fix de parser necesario.
- **El bug real es estructural, no de parser.** Dos problemas distintos:
  1. **No existe un markdown del CST consolidado en `knowledge_base/`.** Las "CST art. 64", "CST art. 62", "CST art. 65" sólo aparecen dentro de `Ley-50-1990.md`, `Ley-789-2002.md` etc. — leyes que MODIFICAN al CST. Cuando el parser ve `### ARTÍCULO 64. Indemnización...` dentro de Ley-50, emite `article_key="64"` y `article_number="64"` — **sin provenance del código origen**. El graph hereda esa ambigüedad: `:ArticleNode {article_id: "64"}` puede ser CST 64, ET 64, o Ley 50/1990 art. 64 sin distinción. Esto valida §1.3.1 del doc pero invalida la hipótesis "parser bug".
  2. **Los EXPERTOS / NORMATIVA / NOMINA / PLAYBOOKS labor son chunkeables pero no son `:ArticleNode`-able.** 24 de 44 archivos labor producen chunks slug-keyed que `_is_article_node_eligible()` filtra fuera del grafo (válido — son guías, no estatutos).

- **Implicación para el plan:**
  - **Fase 3 NO necesita un parser fix.** Su scope se reduce a "emit `norm_id` desde la ingesta y re-ingestar".
  - **Pero abre un problema nuevo, NO listado en §1.3**: la fuente CST consolidado falta en el corpus. v19 no puede producir `:ArticleNode {norm_id: "cst.art.64"}` correctamente sin: (a) sumar `Codigo_Sustantivo_Trabajo.md` al `knowledge_base/`, o (b) cambiar la lógica de ingestión para que cuando Ley 50 art. 64 se vea, también emita un ArticleNode `cst.art.64` con `IS_MODIFIED_BY` apuntando a Ley 50. Opción (a) es más limpia; opción (b) abre una superficie de derivación nueva.
  - Este descubrimiento **debe consolidarse en §8 (preguntas abiertas) como §8.4** antes de tocar Fase 2.

#### §2.0.2 Fase 0 findings — TEMA git archaeology

- **Hipótesis del doc**: hubo un commit que removió o rompió la emisión de TEMA edges.
- **Resultado empírico**: HIPÓTESIS REFUTADA.
- **Cómo se midió**:
  - `git log -p -S "_build_article_tema_edges" -- src/lia_graph/ingestion/loader.py` → solo `6e5e842` (introducción) lo toca.
  - `git log -p -S "EdgeKind.TEMA" -- src/lia_graph/ingestion/` → `6e5e842` (creación) + `eb3e901` (re-flip de flags, no toca TEMA en ingesta).
  - `git log -p -S "article_topics" -- src/lia_graph/ingestion/` → un solo commit relevante (`6e5e842`).
  - Grep global `DELETE.*TEMA` en `src/` y `scripts/` → solo aparece en `loader.py:487-504`, **per-article-key scoped** (no global wipe).
- **El código de TEMA está intacto en ambos paths**:
  - Full-rebuild: `ingest.py:421-433` → `build_graph_load_plan(article_topics=…)` → `loader.py:243` → `_build_article_tema_edges()` emite los edges.
  - Delta: `delta_runtime.py:564-583` → `build_graph_delta_plan(article_topics=…)` → `loader.py:398` → mismo `_build_article_tema_edges()`.
- **El única operación que borra TEMA edges**: `loader.py:487-504` (`stage_delete_outbound_edges_batch(NodeKind.ARTICLE, article_keys_being_merged, relation=EdgeKind.TEMA)`). Es **scoped** a los ArticleNodes que se están re-MERGEando en el run — no es un wipe global.
- **Causa real del 0-count en cloud (mejor inferencia disponible sin examinar el último run log de cloud)**:
  - El path full-rebuild reconstruye `article_topics` a partir de `_topic_by_source_path[article.source_path]` (`ingest.py:417-427`). Si el último full-rebuild de cloud corrió con classifier output donde la mayoría de docs salieron con `topic_key=None` (clasificador degradado, TPM backpressure, o cambio de taxonomía), la cleanup pass borró todos los TEMA edges existentes y la emisión nueva fue 0.
  - Alternativa: el `article.source_path` no matcheó con la key de `_topic_by_source_path` (ej. paths cambiaron entre fingerprint y classifier output).
  - No es un commit a revertir — es **un problema de datos de un run específico de ingesta**.
- **Implicación para el plan:**
  - **Fase 5 NO es Path A (`git revert`). Es Path B**: instrumentar el call site (`ingest.py:421-427` + `delta_runtime.py:564-574`) para que emita un evento con `len(article_topics)`, `len([v for v in values if v])`, y `len(article_topics & article_keys_being_merged)` ANTES de que la cleanup pass corra. Re-correr una ingesta de prueba sobre un subset de cloud. Si la causa es classifier-degraded, regenerar classifier output ANTES de ingestar. Si la causa es path-mismatch, fix narrow en el join.
  - El target "≥ 1,000 TEMA edges, ≥ 30 para `laboral`" del §2.5 sigue válido como success criterion, pero el camino para llegar es diagnostic-first, no revert-first.

#### §2.0.3 Fase 0 findings — embeddings keying (§8.1, operator pidió investigate-first)

- **Pregunta**: ¿los chunk embeddings son content-keyed o anchor-keyed?
- **Resultado**: **content-keyed semánticamente, anchor-keyed posicionalmente.** Match exact: cambiar `article_key` en `parsed_articles.jsonl` SÍ dispara re-embedding completo. Mantener `article_key` y agregar `norm_id` sólo en Falkor NO dispara re-embedding.
- **Cómo se midió**:
  - `embedding_ops.py:348-359` — el texto que se embedea es `f"{summary}\n{chunk_text[:512]}"[:768]`. **Cero metadata de anchor / norm_id / topic en el input.** Pura content.
  - `embedding_ops.py:398` + `:401-411` — `client.table("document_chunks").upsert(batch_updates, on_conflict="id")` — el embedding se guarda en `document_chunks.embedding` keyed por la PK `id` (UUID auto).
  - `supabase_sink.py:275-276` — `chunk_id = f"{doc_id}::{article_key}"`. Es el **business key** (UNIQUE) sobre el que upserta `write_chunks` (`:709-712`, `on_conflict="chunk_id"`).
  - `supabase_sink.py:883-916` — en re-ingesta de modificados, calcula `stale = current_ids - written_chunk_ids` y `delete().eq("chunk_id", stale_id)`. **Si `article_key` cambia de `"64"` a `"cst.art.64"`, todos los chunks legacy se borran y se recrean con NULL embedding.**
- **Implicación arquitectural (decisión nueva que el doc v1 no captura)**:
  - **Opción A (lo que el doc v1 propone)**: cambiar `article_key` en parsed_articles.jsonl + chunk_id de Supabase al formato dotted. Costo: **re-embedding completo del corpus** (~20,154 chunks × Gemini API). Tiempo + costo significativo.
  - **Opción B (recomendada por este finding)**: dejar `article_key="64"` y `chunk_id="<doc>::64"` intactos. Agregar `norm_id` SÓLO como property/index nuevo en `:ArticleNode` (Falkor) y como columna nueva en `documents` (Supabase, no en `document_chunks`). El retrieval traversal cambia (match by `norm_id`), pero los embeddings sobreviven sin recomputar. **Esta opción NO necesita re-embedding.**
- **Esto es una pregunta de scope que afecta toda Fase 2.** Hay que decidir antes de escribir el migration script.

---

#### §2.0.4 Resumen ejecutivo de Fase 0 + revisiones recomendadas

- ✅ **Parser**: no hay bug. Fase 3 ya no necesita un patch de regex.
- ❌ **Parser hipótesis original** ("regex no matchea CST"): refutada.
- 🚨 **Descubrimiento nuevo**: no existe markdown del CST consolidado en el corpus → toda CST art. 64 en el grafo viene transitivamente vía Ley 50/789 etc. **§8.4 (pregunta abierta nueva)**: ¿v19 agrega el CST consolidado al `knowledge_base/` o deriva `:ArticleNode` CST desde edges de modificación?
- ✅ **TEMA**: no es regresión de código. La feature está intacta. Path A (`git revert`) descartado; Path B (instrumentar el call site + reproducir) es el único camino.
- 🚨 **Descubrimiento nuevo**: la causa real del 0-count es un run específico de ingesta que produjo `article_topics` vacío (classifier degraded o source_path mismatch). Necesita diagnóstico ejecutándose sobre cloud, no archeology de código.
- 🚨 **Embeddings (§8.1) tiene una opción C que el doc no contemplaba**: scope reducido — `norm_id` sólo en Falkor `:ArticleNode`, sin tocar `chunk_id` de Supabase. **Evita re-embedding completo.** Recomendación fuerte de adoptar este scope reducido.

**Gate decision para avanzar a Fase 2 (operator):**
- (1) Aceptar el scope reducido (§2.0.3 Opción B) y reformular Fase 2 como "norm_id sólo en Falkor"?
- (2) Resolver §8.4 (CST consolidado) — ¿agregar el markdown o derivar via edges de modificación?
- (3) Confirmar que Fase 5 se aborda como Path B (instrumentar + reproducir) en vez de Path A (revert)?

#### §2.0.5 Operator gate decisions (2026-05-15 evening)

- **Gate 1 — Fase 2 scope**: ✅ **adopted Opción B**. `norm_id` se agrega sólo como property + unique index en Falkor `:ArticleNode`. `parsed_articles.jsonl` y `document_chunks.chunk_id` quedan intactos. **Zero re-embedding.**
- **Gate 2 — §8.4 CST source**: ✅ **agregar `Codigo_Sustantivo_Trabajo.md` al corpus**. Fuente: gov.co (secretariasenado / suin-juriscol). Drop bajo `knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Codigo_Sustantivo_Trabajo.md`. El parser ya soporta el formato (Fase 0 §2.0.1). **Prerequisito de Fase 3**.
- **Gate 3 — Fase 5**: ✅ **Path B confirmed**. Path A (revert) está descartado per §2.0.2. Instrumentación a agregarse en `ingest.py:421` + `delta_runtime.py:564` con evento `ingest.tema.binding_summary { article_topics_len, populated_count, intersection_with_merged }`. Subset re-ingest en cloud para diagnosticar.

---

### §2.1 Fase 1 — Auditoría (½ día) ✅

- Output en §1 de este doc. **STATUS**: ✅ done 2026-05-15.

### §2.2 Fase 2 — Alinear ArticleNode con canonical `norm_id` grammar (1-2 días) 🛠

**Idea.** ArticleNode pasa de `article_id="64"` (bare numeric) a `norm_id="et.art.64"` (mismo formato que `public.norms.norm_id` y `:Norm`). **No inventamos formato — reusamos `canon.canonicalize()`.**

**Plan narrow.**
- Agregar prop `norm_id` a ArticleNode + index único en `(norm_id)`.
- Migrar todos los ArticleNodes existentes: para cada uno, derivar `norm_id` de `source_path + article_number` reusando `canon.canonicalize()` (input: `"ET art. 64"` → output: `"et.art.64"`).
- Sub-unit slots (`.par.1`, `.num.2`, `.inciso.a`, `.lit.b`) ya están en la grammar — manejados gratis.
- Composites (`et.art.124-2`, `cst.art.127-132`) — la grammar acepta hyphens en la posición numérica.
- Migrar edges (:TEMA, :MODIFIED_BY, :DEROGATED_BY, :IS_SUB_UNIT_OF, :CITES) — son edges por endpoint, solo el endpoint id cambia.
- Considerar (decisión §8 abierta) si `:ArticleNode` y `:Norm` deben colapsar en un solo label, ya que ahora compartirían key.

**Success criterion.**
- 0 ArticleNodes sin `norm_id` populated post-migration.
- 0 duplicaciones de `(norm_id)`.
- `MATCH (a:ArticleNode {norm_id: 'cst.art.64'}) RETURN a` resuelve (si Fase 0 + Fase 3 ya generaron el nodo) o retorna 0 rows pero el query es válido.
- Pre vs post migration: count de nodes + edges idénticos.

**Test plan.**
- Unit tests del mapping `(source_path, article_number) → norm_id` (~30 casos cubriendo cada bucket conocido + `OTHER` fallback que abort si no clasifica).
- Migration script con `--dry-run` que dumpea el plan sin escribir.
- Validación: query random de 20 ArticleNodes pre + post → headings idénticos.

**Rollback.** Backup completo del grafo (`scripts/falkor/dump_graph.sh` o equivalente — verificar que existe). Si la migración falla → restore.

### §2.3 Fase 3 — Parser fix (si aplica) + re-ingesta limpia (1-2 días) 🛠

**Idea.** Re-ingestar el corpus con el parser corregido (si Fase 0 lo confirma) + emisión de `norm_id` desde ingestion. Pre-producción → borrar grafo + re-ingestar from scratch.

**Plan narrow.**
- (Condicional a Fase 0.1.) Si parser regex era el bug, parche en `parser.py:213` para tolerar `ARTÍCULO` mayúscula + `Art.` + listas numeradas + variantes vistas en CST/Ley 50/789.
- Actualizar `lia_graph/ingestion/falkor_sink.py` (o `loader.py` _emit_article_node) para que emita `norm_id` además del bare `article_number`.
- Borrar grafo Falkor + re-ingestar usando veredictos Gemini ya cacheados.
- Verificar CST 62, 64, 65 ahora existen como `:ArticleNode {norm_id: 'cst.art.64'}` distintos de `et.art.64`.

**Success criterion.**
- ArticleNode `cst.art.64` existe + heading correcto (terminación unilateral con justa causa).
- ArticleNode `et.art.64` existe + heading correcto (disminución de inventario).
- ArticleNode `ley.50.1990.art.6` existe (si Ley 50/1990 está en corpus).
- ArticleNodes laborales sube de **41 → ≥ 200** (estimado; depende de Fase 0 findings).

**Test plan.**
- Cypher queries por `norm_id` para 5 articles CST conocidos.
- Idempotency: re-correr ingesta 2 veces → mismo conteo.
- Comparar conteos por bucket vs Fase 1 — explicar deltas.

**Rollback.** Backup pre-Fase-3 → restore + flag `LIA_INGESTION_NORM_ID_KEYS=off` que fuerza el formato viejo.

### §2.4 Fase 4 — Actualizar consumidores (1.5-2 días) 🛠

**Idea.** Migrar el grafo de consumidores que referencian articles por bare numeric o `art:NNN` a `norm_id` dotted.

**Scope corregido post-review:** 62 hits en 31 archivos en case_bullets + lista adicional abajo.

**Plan narrow — split en 4a (critical) + 4b (cleanup):**

**4a — critical path (bloquea Fase 5 validation):**
- `src/lia_graph/pipeline_d/planner.py` — `_explicit_article_keys`, `_CASE_ANCHOR_REGISTRY` walk, `_build_article_search_queries`.
- `src/lia_graph/pipeline_d/retriever_falkor.py` — incluyendo MATCH en `a.article_number` (`:299, :350`) que pasan a `a.norm_id`.
- `src/lia_graph/pipeline_d/case_bullets/*.py` — **62 hits, 31 files**. Cada `anchor_articles=("108", "387")` pasa a `anchor_articles=("et.art.108", "et.art.387", "cst.art.64", "cst.art.65", "cst.art.62")` etc.
- `config/topic_norm_allowlist.json` — formato `art:NNN` → `<codigo>.art.NNN`.
- `src/lia_graph/pipeline_d/_citation_allowlist.py` — consume `art:` prefixes; migrar.

**4b — cleanup (puede landear en Fase 6):**
- `config/subtopic_taxonomy.json` — si referencia articles.
- `config/comparative_regime_pairs.json` — referencias a articles.
- Test fixtures (v18 baseline 301 tests — algunos probablemente hardcode keys).

**Pre-flight cross-surface check (NUEVO, antes de 4a ship):**
- `src/lia_graph/interpretacion/retriever_supabase.py` — confirmar que joins ArticleNode→InterpretationNode no quemen.
- `src/lia_graph/ui_normative_processors.py` consume `artifacts/parsed_articles.jsonl` per orchestration.md:268 — regenerar JSONL con nuevo formato.
- `artifacts/canonical_corpus_manifest.json` — chequear si tiene keys de articles.

**Success criterion.**
- Todos los case_specs pasan `anchor_articles=("cst.art.64", ...)`.
- `topic_norm_allowlist.json` usa formato dotted.
- v18 baseline tests (301) verdes con el nuevo formato.
- `Normativa` modal + `Interpretación` panel funcionan en probe manual.

**Test plan.**
- Grep audit primero — listar TODOS los strings que parecen article keys + clasificar.
- Re-correr v18 baseline (`pytest tests/test_*.py`) post-cambio.
- Snapshot test: probe §4.1 → confirmar `seed_article_keys` contiene `cst.art.64`.
- Probe manual de `Normativa` + `Interpretación` panels.

**Rollback.** Git revert del commit 4a; Fase 3 sigue válida (norm_id en el grafo no daña al planner viejo si hay fallback to legacy lookup).

### §2.5 Fase 5 — Restaurar TEMA seeding (programático, NO hand-curated) (½-1 día) 🛠

**Idea.** Recuperar la regresión de `:TEMA` edges de `(ArticleNode)-[:TEMA]->(TopicNode)`. La feature existe en `loader.py:673-710 _build_tema_edges` — el bug está en por qué `article_topics` map llega vacío.

**Plan narrow — condicionado a Fase 0 findings:**

**Path A (si Fase 0 identifica el commit responsable de la regresión):**
- `git revert <sha>` del commit que rompió la emisión.
- Re-ingestar (puede combinarse con Fase 3 si timing permite).
- Verificar conteo de TEMA edges post-ingesta vs el "1,943" histórico.

**Path B (si la regresión no se puede recuperar por revert):**
- Investigar `_build_tema_edges` invocation site en `delta_runtime.py:556-568` — qué le pasa `article_topics`.
- Hipótesis principal: el classifier output no se está propagando al map. Fix narrow en el call site, no nuevo config.
- Alternativa de último recurso: seeding programático derivado de `documents.topic` field (que Supabase ya tiene). NO `config/topic_tema_anchors.json` hand-curated.

**Success criterion.**
- `MATCH ()-[r:TEMA]->() RETURN count(r)` ≥ **1,000** (apuntando al baseline histórico de 1,943).
- `MATCH (t:TopicNode {topic_key: 'laboral'})-[:TEMA]->(a) RETURN count(a)` ≥ **30**.
- Probe §4.1 ahora `seed_article_keys` empieza con `["cst.art.64", "cst.art.65", "cst.art.62", ...]`.

**Test plan.**
- Idempotency: re-correr seeding 2 veces → mismo conteo.
- Probe §4.1 + 5 fixtures (uno por código grande) → verificar :TEMA contributing.

**Rollback.** `MATCH ()-[r:TEMA]->() DELETE r` borra todos los edges; ingesta sigue intacta para reintentar.

### §2.6 Fase 6 — Validación end-to-end + shadow period + flip flags (3-7 días) 🛠

**Idea.** Una vez Fases 2-5 landed, validar con shadow period largo ANTES de flipear flags a enforce.

**Plan narrow.**

**Sub-fase 6a — shadow period (3-5 días):**
- Setup diff harness: cada turno servido corre el nuevo schema retrieval + dumpea `seed_article_keys` + `primary_articles` + `Anclaje Legal` cited en logs estructurados.
- Operator opera normalmente, traces se acumulan.
- Output: diff report comparando "antes (v18 b2.2 corriendo)" vs "ahora (post-v19)". Trazas a través de fixtures + queries reales.

**Sub-fase 6b — fix narrow gaps (1-2 días reservados):**
- Cualquier surface que se rompe silenciosamente → fix narrow.
- Cualquier discrepancia esperada vs observada en :TEMA o primary_articles → ajustar.

**Sub-fase 6c — flip flags + SME panel (1 día):**
- Pre-flip: agregar validator numérico en `answer_conflict_resolver.py::resolve_via_a2` similar a `_no_invented_uvt_ranges` del polish. Razón: el A2 LLM es el mismo modelo que polish acaba de rechazar por UVT inventado — mismo riesgo en A2.
- Flip `LIA_PRACTICA_NOISE_FILTER=enforce`.
- Flip `LIA_CONFLICT_RESOLVER_MODE=enforce`.
- Correr SME panel via `scripts/eval/run_sme_parallel.py` (operator-triggered, no auto-run per `feedback_sme_panel_explicit_request_only`).

**Success criterion.**
- §4.1 served answer: 0 bullets `código NN`, 0 contradicciones 30 vs 45, anchor legal cita CST (NO ET 108/387).
- SME panel acc+ ≥ 30/36 (vs baseline ~21/36).
- v18 baseline tests 301 → 301 (no regresión).
- Shadow diff harness: ≥ 80 % de turnos muestran `primary_articles` con código correcto (CST/Ley para labor, ET para tributario, etc.).

**Test plan.**
- 14 fixtures (4 de v18 + 10 nuevas), engineer.
- Shadow 3-5 días, operator monitorea.
- SME panel via script, operator-triggered.

**Rollback.** Si SME baja → flip back to shadow + diagnose. Fases 2-5 quedan landed.

---

## §3. Riesgos + mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Migration script malclasifica source_paths → norm_ids | Media | Alto (ArticleNodes con codigo equivocado) | Dry-run + audit manual de 50 paths random ANTES de aplicar; reuso de `canon.canonicalize()` minimiza la superficie de error |
| Re-ingesta tarda más de lo esperado | Media | Medio (un día perdido) | Veredictos Gemini cacheados; medible upfront probando ingesta de 100 docs primero |
| `norm_id` change rompe tests existentes | Alta | Bajo (tests fáciles de actualizar) | Gate la Fase 5 en tests verdes |
| TEMA recovery (Path B) introduce nueva drift en retrieval | Media | Alto | Cap de 50 edges por topic + audit manual ANTES de aplicar |
| Surfaces no-`main chat` (Normativa/Interpretación) rompen | Media | Alto | Pre-flight check explícito en Fase 4 |
| A2 LLM hallucina en enforce mode | Media | Alto | Validator numérico estructural en sub-fase 6c |
| Shadow period revela bugs imposibles de fixear en 1-2 días | Baja | Alto | Aceptable rollback to v18 b2.2 state; learnings documented; re-attempt en v20 |

### §3.1 Orden de unwind para rollback de la ensamblada

Si Fase 6 falla y hay que retroceder:

1. **Flag flip back to shadow** — `LIA_CONFLICT_RESOLVER_MODE=shadow` + `LIA_PRACTICA_NOISE_FILTER=shadow`. Instantáneo, sin riesgo.
2. **Revert Fase 4** primero (NO Fase 3 primero). Razón: si revertís Fase 3 con consumers nuevos en producción, el retriever queries `cst.art.64` que ya no existe → 500. Revert 4 primero asegura que los consumers vuelven a queries del formato viejo.
3. **Revert Fase 3** (restaurar backup Falkor).
4. **Revert Fase 2** (drop el `norm_id` index si quedó residual).
5. **Fase 5 TEMA edges** se quedan o se borran independientemente — no son load-bearing para retrieval básico.

---

## §4. Dependencies + ordering

| Fase | Bloquea | Puede paralelizar con |
|---|---|---|
| 0 (pre-flight) | TODO el resto | — |
| 1 (audit) | — (done) | — |
| 2 (norm_id schema) | 3, 4 | — |
| 3 (re-ingesta + parser fix) | 5 validation, 6 | 4a (parcialmente) |
| 4a (critical consumers) | 5 validation, 6 | 5 si schema ya landed |
| 4b (cleanup consumers) | 6c flip | — |
| 5 (TEMA recovery) | 6 | 4a |
| 6a (shadow) | 6c flip | — |
| 6c (flip + SME) | — | — |

---

## §5. Files a crear o modificar

### Nuevos archivos
- `scripts/migrate_falkor_norm_ids.py` — migration script (dry-run + apply), reuso de `canon.canonicalize()`.
- `tests/test_norm_id_migration.py` — tests del mapping `(source_path, article_number) → norm_id`.
- `tests/test_falkor_norm_id_schema.py` — tests del migration script.
- `scripts/shadow_diff_harness.py` — Fase 6a, dumpea seed_article_keys + primary_articles para comparación.

### Modificados
- `src/lia_graph/ingestion/parser.py` — (condicional Fase 0) regex de heading para CST/Ley markdown.
- `src/lia_graph/ingestion/loader.py` — emit `norm_id` en ArticleNode; verificar `_build_tema_edges` call site.
- `src/lia_graph/ingestion/falkor_sink.py` o `delta_runtime.py` — propagar `article_topics` map correctamente (Fase 5 Path B).
- `src/lia_graph/pipeline_d/planner.py` — `_CASE_ANCHOR_REGISTRY` walk + `_explicit_article_keys` usan `norm_id`.
- `src/lia_graph/pipeline_d/retriever_falkor.py` — MATCH on `norm_id`; `_retrieve_tema_bound_article_keys` también.
- `src/lia_graph/pipeline_d/case_bullets/*.py` — 31 files, ~62 anchor_articles tuples.
- `src/lia_graph/pipeline_d/_citation_allowlist.py` — formato dotted.
- `src/lia_graph/pipeline_d/answer_conflict_resolver.py` — NUEVO validator numérico structural sobre output A2 (Fase 6c).
- `config/topic_norm_allowlist.json` — formato dotted.
- `scripts/dev-launcher.mjs` — flip flags en Fase 6c.
- `fix_v18_may.md` — close Issues B, E with "blocked-then-resolved-by-v19".
- `CLAUDE.md` + `docs/orchestration/orchestration.md` + `docs/guide/env_guide.md` — bump env matrix version + Change Log row.
- `artifacts/parsed_articles.jsonl` — regenerar con nuevo formato (Fase 4 pre-flight).

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

## §7. Estado al cierre de Fase 1 + revisión (2026-05-15 evening)

- Fase 0: ✅ done — findings + revisiones recomendadas en §2.0.1 / §2.0.2 / §2.0.3 / §2.0.4.
- Fase 1: ✅ done. Audit numbers en §1.
- Fase 2: 🟡 plan **needs rework** (scope reducido §2.0.3 Opción B; §8.4 abierto).
- Fase 3: 🟡 simplificada — no necesita parser fix, sólo emit `norm_id` + re-ingesta condicional a §2.0.3.
- Fase 4a / 4b: 🟡 alcance se reduce si scope §2.0.3 Opción B se adopta.
- Fase 5: 🟡 **Path A descartado** — sólo Path B (instrumentar + reproducir) per §2.0.2.
- Fase 6a / 6b / 6c: 🛠 plan ready.
- v18 b2.1 + b2.2 (conflict resolver): keep `LIA_CONFLICT_RESOLVER_MODE=shadow`. Re-evaluate flip-to-enforce en Fase 6c.

**Próximo paso (operator decision)** — tres gates antes de Fase 2:

1. **Adoptar el scope reducido §2.0.3 Opción B** (`norm_id` sólo en Falkor `:ArticleNode`, sin tocar `chunk_id` de Supabase, sin re-embedding)?
2. **Responder §8.4** — ¿v19 agrega `Codigo_Sustantivo_Trabajo.md` al `knowledge_base/` o deriva los ArticleNodes CST vía edges `IS_MODIFIED_BY` desde Ley 50/789/etc.?
3. **Confirmar Fase 5 Path B** — instrumentar `ingest.py:421-427` + `delta_runtime.py:564-574` con un evento que reporte `(len(article_topics), populated_count, intersection_with_merged)`, correr una ingesta de prueba sobre subset de cloud, diagnosticar?

---

## §8. Preguntas abiertas (operator debe responder antes de Fase 2)

| # | Pregunta | Por qué importa |
|---|---|---|
| 8.1 | ¿Embeddings de chunks son content-keyed (no anchor-keyed)? | Si content-keyed → re-ingesta NO requiere re-embedding (ahorra horas). Si anchor-keyed → re-embedding obligatorio (costoso). |
| 8.2 | Relación `:ArticleNode` (Falkor, hoy) vs `:Norm` (Falkor, vigencia) vs `public.norms.norm_id` (Supabase). Hoy son 3 cosas distintas. ¿v19 colapsa `:ArticleNode` y `:Norm` en un solo label compartiendo `norm_id`? | Decisión arquitectural — define el alcance de Fase 2. Si colapsamos, simplifica el grafo a futuro. Si no, mantenemos dos labels que comparten key → más complejidad pero menor riesgo de migración. |
| 8.3 | ¿`artifacts/parsed_articles.jsonl` es regenerable por script o requiere ingestion run? | Define si Fase 4 pre-flight necesita 5 min o 1 hora de wall-clock. |
| 8.4 ✅ | **NUEVA (Fase 0 §2.0.1)** — RESUELTA per §2.0.5 Gate 2 + EJECUTADA 2026-05-15. Delivery via `docs/re-engineer/corpus_population_for_experts/01b_cst_consolidado_v19.md` (Brief 01b). File landed at `knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Codigo_Sustantivo_Trabajo.md` — 504 headings, 498 ParsedArticle units, 79 derogated, range 1-492, source Secretaría del Senado. Parser dry-run: zero whole-doc / section fallbacks. Reform anchors verified (art. 64 = Ley 789/2002, art. 161 = Ley 2466/2025 + Ley 2101/2021, art. 179 = Ley 2466/2025). | Prerequisito de Fase 3 — **cumplido**. |
| 8.5 ✅ | **NUEVA (Fase 0 §2.0.3)** — RESUELTA per §2.0.5 Gate 1. Decisión: Opción B (Falkor sólo, sin tocar `chunk_id`, sin re-embedding). | Define el scope de Fase 2/3/4. |

---

*End of fix_v19_may.md.*
