# 03 — Phase 2: Shared Regulatory Graph

## Status

- `phase_id`: 2
- `status`: COMPLETE
- `owner`: Codex + repo maintainer
- `last_updated`: 2026-04-15T19:01:51-04:00
- `depends_on`: phase 1 complete
- `exit_criteria`:
  - graph schema defined and validated
  - normative unit parsing and link extraction implemented for the graph-targeted layer
  - edge typing and load workflow specified end to end
  - graph integrity can be checked deterministically
  - live FalkorDB load path executes successfully against the current local snapshot in a test environment

## Intent

- objetivo de la fase: construir el grafo regulatorio compartido con vigencia y provenance como datos nativos
- valor de negocio: materializa la capa de source assets y la capa canonica del corpus compartido en una vista operable, y convierte normas, reformas y relaciones de la familia normativa graph-parse-ready en una base reutilizable para todos los tenants sin invisibilizar interpretacion ni practica
- superficies afectadas:
  - discovery e inventory del source-asset surface completo
  - canonical corpus manifest
  - ingestion pipeline sobre la familia normativa
  - graph storage
  - normative provenance
  - corpus validation
  - medicion por familia para normativa, interpretacion y practica

## Implementation Scope

Reference policy: `docs/build/buildv1/appendix-d-corpus-audit-and-labeling-policy.md`

### Entra

- compuerta obligatoria de auditoria de corpus antes de inventario o graphizacion
- distincion explicita entre source assets, canonical corpus y graph-parse-ready inputs
- discovery y clasificacion de documentos del corpus compartido por familia
- inventory artifact del corpus compartido completo
- reconnaissance quality gate before canonical blessing
- canonical manifest para documentos admitidos y revisiones pendientes
- rotulado minimo y seguro para admision de corpus
- schema de nodos y edges
- parser de unidades normativas y subarticulos
- linker de referencias
- tipado de relaciones
- carga y validacion de grafo

### No Entra

- graphizar toda la capa interpretativa o practica
- reducir interpretacion o practica a "later maybe" sin inventario ni visibilidad operativa
- usar topic/subtopic como sustituto plano de relaciones normativas
- planner de preguntas
- runtime multi-tenant
- cache compilado

### Corpus Audit Gate

Phase 2 empieza con una compuerta obligatoria de auditoria del corpus compartido. Ningun archivo entra al inventario o al parse normativo solo por estar debajo del source root.

Cada archivo escaneado debe caer en exactamente una decision:

- `include_corpus`
- `revision_candidate`
- `exclude_internal`

`to upload` entra al mismo gate: no se ignora por defecto, pero tampoco se admite sin pasar las mismas reglas.

### Ingestion Principles

- el corpus compartido entra primero como vista auditada y medible, no como monton de markdown asumido
- `family` y `knowledge_class` son metadata obligatoria; `topic` y `subtopic` son metadata de apoyo cuando aplica
- el vocabulario ratificado es autoridad de nombres, no cuello de botella de admision
- la taxonomia de topics vive versionada en repo config y opera como activo vivo; las keys legacy sobreviven solo como aliases de compatibilidad
- ingestion, guardrails, router, planner y retrieval deben consumir el mismo canon versionado
- un dominio valido fuera del vocabulario actual puede entrar como custom topic pendiente de ratificacion
- reformas, excepciones, dependencias, definiciones y vigencia deben derivarse del grafo, no de rotulos planos

## Files To Create

- `src/lia_graph/graph/schema.py` - nuevo
- `src/lia_graph/graph/client.py` - nuevo
- `src/lia_graph/graph/validators.py` - nuevo
- `src/lia_graph/ingestion/parser.py` - nuevo
- `src/lia_graph/ingestion/linker.py` - nuevo
- `src/lia_graph/ingestion/classifier.py` - nuevo
- `src/lia_graph/ingestion/loader.py` - nuevo
- `artifacts/corpus_audit_report.json` - nuevo artefacto con decision por archivo
- `artifacts/corpus_reconnaissance_report.json` - nuevo artefacto con quality gate por archetype, authority, family, ambiguity y revision linkage
- `artifacts/revision_candidates.json` - nuevo artefacto con patches y updates pendientes de merge
- `artifacts/excluded_files.json` - nuevo artefacto con working files y razones de exclusion
- `artifacts/canonical_corpus_manifest.json` - nuevo artefacto con documentos admitidos, pending revisions y graph-parse readiness
- `artifacts/corpus_inventory.json` - nuevo artefacto para inventariar el corpus compartido por familia
- `artifacts/parsed_articles.jsonl` - nuevo artefacto inicial para unidades normativas parseadas
- `artifacts/raw_edges.jsonl` - nuevo artefacto
- `artifacts/typed_edges.jsonl` - nuevo artefacto
- `artifacts/graph_load_report.json` - nuevo artefacto
- `artifacts/graph_validation_report.json` - nuevo artefacto

## Files To Modify

- `src/lia_graph/ingest.py` - existente
- `src/lia_graph/corpus_ops.py` - existente
- `Makefile` - existente
- `supabase/migrations/*` - existentes o nuevas segun metadata requerida

## Tests For This Surface

### Unitarias

- audit decision tests para `include_corpus`, `revision_candidate` y `exclude_internal`
- all-file audit coverage para markdown, text y assets no-markdown
- discovery y family classification para `normativa`, `interpretacion`, `practica`
- labeling tests para `family`, `knowledge_class`, `source_type`, `vocabulary_status`, `parse_strategy`, `document_archetype`
- parsing de articulos y subarticulos
- deteccion de referencias normativas
- edge classification con taxonomia fija
- resolucion de vigencia y status del articulo

### Integracion

- exclusion de `state.md`, working `README.md`, `.DS_Store`, crawler helpers y `deprecated/`
- inventario consistente del corpus compartido completo antes del parse normativo
- reconnaissance gate que marque `ready_for_canonical_blessing`, `review_required` o `blocked`
- tratamiento de `PATCH` y `UPSERT` como `revision_candidate` y no como corpus standalone
- manifest canonico consistente con base docs y pending revisions adjuntas
- assets no-markdown inventariados sin ser enviados al parser por accidente
- load completo a FalkorDB en entorno de prueba
- validadores de node count, edge count y orphan check
- consistencia entre corpus fuente normativo y graph nodes

### Smoke/Eval

- comparacion de audit outputs vs inventory outputs antes de cualquier interpretacion del corpus
- visibilidad estable de las tres familias del corpus desde el mismo pass de materializacion
- canarios multi-hop del ET y otras cadenas normativas prioritarias
- smoke de consultas de reforma y excepcion

## Execution Steps

1. Descubrir todos los archivos candidatos del corpus compartido, incluyendo source roots principales y `to upload`.
2. Ejecutar la auditoria obligatoria y clasificar cada archivo como `include_corpus`, `revision_candidate` o `exclude_internal`.
3. Asignar metadata de shape y operacion por archivo: `extension`, `text_extractable`, `parse_strategy` y `document_archetype`.
4. Materializar reportes de auditoria, revision y exclusion antes de cualquier parse normativo.
5. Materializar un reconnaissance report que revise archetype, authority, family, ambiguity y revision linkage antes de bendecir estado canonico.
6. Materializar el manifiesto canonico del corpus admitido, adjuntando `revision_candidate` a sus base docs cuando haya target resoluble y exponiendo blessing state.
7. Materializar inventario y metricas del corpus compartido usando solo archivos `include_corpus`.
8. Rotular los documentos admitidos con `family`, `knowledge_class`, `source_type` y estado de vocabulario.
9. Aplicar el canon ratificado como naming authority; conservar aliases viejos solo para compatibilidad.
10. Definir o ajustar node types y edge taxonomy para el backbone regulatorio.
11. Construir parser solo sobre documentos normativos graph-parse-ready admitidos por la auditoria.
12. Extraer referencias y reformas con contexto.
13. Clasificar edges con pipeline deterministico + asistido.
14. Cargar el grafo y ejecutar validadores.
15. Guardar artefactos y reportes en `artifacts/`.
16. Validar conectividad FalkorDB del entorno real y repetir el live load hasta que `graph_load_report.executed = true` y `failure_count = 0`.

## Checkpoint Log

- `current_step`: 16
- `completed_steps`: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
- `blocked_by`: []
- `artifacts_created`: [
  "docs/build/buildv1/03-phase-2-shared-regulatory-graph.md",
  "src/lia_graph/graph/schema.py",
  "src/lia_graph/graph/client.py",
  "src/lia_graph/graph/validators.py",
  "src/lia_graph/ingestion/parser.py",
  "src/lia_graph/ingestion/linker.py",
  "src/lia_graph/ingestion/classifier.py",
  "src/lia_graph/ingestion/loader.py",
  "tests/test_phase2_graph_scaffolds.py",
  "scripts/sync_corpus_snapshot.sh",
  "docs/guide/corpus.md"
]
- `notes`: "La fase ya tiene schema, parser, linker, classifier, loader y validadores scaffolded, mas un materializador de artefactos en `python -m lia_graph.ingest`, `make phase2-graph-artifacts` y un sync reproducible en `scripts/sync_corpus_snapshot.sh` para traer un snapshot filtrado de Dropbox a `knowledge_base/`. En esta iteracion se completo la costura entre la taxonomia versionada y la ingestión: `src/lia_graph/ingest.py` ahora materializa `taxonomy_version`, `topic_key`, `subtopic_key` y cobertura parent-child desde `config/topic_taxonomy.json`, y ademas ya usa `allowed_path_prefixes` como parte del scoring de matching. El tranche completo de `revision_candidate` adjuntos se fusiono de forma conservadora dentro de sus base docs y los archivos de parche se retiraron a rutas `deprecated/`. Despues, la taxonomia se expandio a `draft_v1_2026_04_15b` para cubrir clusters reales del corpus compartido, con lo cual el rerun real sobre el snapshot escaneo 1276 archivos, admitio 1222, marco 0 `revision_candidate`, excluyo 54, dejo `manual_review_queue_count = 0` y llevo el manifiesto canonico a `canonical_ready_count = 1222` con `review_required_count = 0`. El manifiesto canonico sigue con `documents_with_pending_revisions = 0` y `unresolved_revision_candidate_count = 0`, y `graph_validation_report.json` sigue consistente sobre 1010 documentos normativos graph-parse-ready. El load live cloud revelo primero un problema de DNS/lifecycle del host, pero el hallazgo implementable del repo fue otro: el loader estaba abriendo una conexion TCP por sentencia. Se corrigio `src/lia_graph/graph/client.py` para reutilizar una sola conexion FalkorDB autenticada durante todo el batch, `src/lia_graph/ingestion/loader.py` ahora usa esa via batched, y `tests/test_phase2_graph_scaffolds.py` cubre la regresion. Con esa correccion, un run estricto contra `falkordb/falkordb:latest` en Docker (`redis://127.0.0.1:6389`) ejecuto `22466` sentencias con `success_count = 22466`, `failure_count = 0`, `skipped_count = 0`, y el grafo resultante quedo sano (`LIA_REGULATORY_GRAPH`, `node_count = 2568`, `edge_count = 19898`). Luego, sobre la instancia cloud recreada, `dependency_smoke` quedo en `ok`, `redis-cli` devolvio `PONG`, `GRAPH.LIST` mostro `LIA_REGULATORY_GRAPH`, y el run estricto contra `artifacts/` tambien ejecuto `22466` sentencias con `success_count = 22466`, `failure_count = 0`, `skipped_count = 0`, dejando el grafo cloud en `node_count = 2568` y `edge_count = 19898`. Finalmente, el snapshot local canonicamente limpio se preservo en una carpeta Dropbox separada (`.../Lia_Graph_Working_Snapshots/knowledge_base_snapshot_2026-04-15_19-01-13`) con un marker file explicito, sin escribir de vuelta en el arbol `Corpus`. Con eso, la fase 2 queda completa y el siguiente paso real pasa a ser la fase 3."

## Failure Recovery

- como retomar:
  - leer `src/lia_graph/graph/*.py` y `src/lia_graph/ingestion/*.py` para retomar desde el scaffold vigente
  - correr `PYTHONPATH=src:. uv run --group dev pytest tests/test_phase2_graph_scaffolds.py`
  - leer `docs/build/buildv1/appendix-d-corpus-audit-and-labeling-policy.md` antes de tocar discovery o labeling
  - reconstruir el snapshot con `scripts/sync_corpus_snapshot.sh` cuando cambie Dropbox
  - correr `make phase2-graph-artifacts PHASE2_CORPUS_DIR=knowledge_base`
  - si se quiere un baseline Falkor local reproducible, usar `falkordb/falkordb:latest` en Docker sobre `redis://127.0.0.1:6389`
  - cargar `.env.local` antes de cualquier probe live de FalkorDB
  - correr `PYTHONPATH=src:. uv run python -m lia_graph.dependency_smoke --json` para distinguir DNS/auth/query failures
  - rerun `PYTHONPATH=src:. uv run python -m lia_graph.ingest --corpus-dir knowledge_base --artifacts-dir artifacts --execute-load --json` solo sobre el snapshot local
  - revisar `corpus_audit_report.json`, `corpus_reconnaissance_report.json`, `revision_candidates.json`, `excluded_files.json` y `canonical_corpus_manifest.json` antes de interpretar el inventario
  - revisar `corpus_inventory.json` antes de interpretar el resto de artefactos
  - revisar `parsed_articles.jsonl` y `raw_edges.jsonl` si existen
  - verificar el ultimo reporte de graph validation
  - confirmar si el parser quedo detenido antes o despues del load
- que verificar antes de continuar:
  - si el snapshot local sigue alineado con Dropbox y conserva solo `CORE ya Arriba` + `to upload`
  - si la auditoria esta separando bien corpus, revision candidates y working files
  - si el reconnaissance gate marca `ready_for_canonical_blessing`, `review_required` o `blocked`, y por que
  - si el manifiesto canonico esta adjuntando revisions a base docs correctos
  - si el manifiesto canonico mantiene `documents_with_pending_revisions = 0` y `unresolved_revision_candidate_count = 0`
  - conteos por familia razonables para normativa, interpretacion y practica
  - cobertura de `topic_key`, `subtopic_key` y `taxonomy_version` razonable en `corpus_inventory.json`, `corpus_reconnaissance_report.json` y `canonical_corpus_manifest.json`
  - conteos de graph-parse-ready razonables dentro de la familia normativa
  - cobertura de articulos parseados
  - si el `graph_validation_report.json` sigue en `ok: true` y si los warnings de edges omitidos u orphans cambiaron materialmente
  - si el destino cloud de `FALKORDB_URL` ya esta recreado y estable cuando se quiera revalidar ese entorno

## Open Questions

- si vigencia se modela solo en nodos versionados o tambien en edges de reforma
- si el tipado de edges mezcla reglas y LLM o usa LLM solo para casos ambiguos
- cuanto de la doctrina oficial entra al grafo como nodo/edge y cuanto queda solo como retrieval support enlazado

## Decision Log

- el shared graph es la autoridad normativa compartida
- vigencia y provenance no son metadata secundaria; son parte del modelo
- el primer corte de phase 2 se implementa como scaffold deterministico y dependency-light antes de conectar el cliente FalkorDB real
- la materializacion inicial de artefactos vive en `python -m lia_graph.ingest` para no depender de un directorio `scripts/` que aun no existe en este repo
- phase 2 materializa el corpus compartido completo en un solo pass y graphiza primero la familia normativa porque su estructura si cabe naturalmente en el grafo; interpretacion y practica siguen visibles y medibles desde day 1
- phase 2 no puede asumir que todo markdown bajo los source roots es corpus; primero debe ejecutar una compuerta de auditoria
- la audit surface es mas amplia que la parse surface; assets no-markdown pueden inventariarse sin ser parseados ni graphizados todavia
- phase 2 requiere un reconnaissance gate antes de tratar el canonical manifest como estado durable; admision de corpus y blessing canonico no son la misma cosa
- los revision candidates viven adjuntos a base docs dentro del manifiesto canonico, no como corpus standalone
- el vocabulario ratificado es autoridad de nombres para topic y subtopic, pero no reemplaza relaciones legales ni bloquea la admision de dominios validos
- phase 2 corre el primer materializador real desde un snapshot local filtrado y reproducible, no directamente contra el arbol Dropbox completo
- el rerun real con taxonomia materializada confirmo que el siguiente cuello de botella ya no es setup sino triage canonico: review queue, cobertura de canon y merge review de revisiones adjuntas
- la taxonomia es un activo operativo vivo y versionado en repo config; las keys legacy sobreviven solo como aliases y todas las superficies runtime deben consumir el mismo canon
