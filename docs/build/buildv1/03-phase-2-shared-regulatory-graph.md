# 03 — Phase 2: Shared Regulatory Graph

## Status

- `phase_id`: 2
- `status`: IN_PROGRESS
- `owner`: Codex + repo maintainer
- `last_updated`: 2026-04-14T12:35:39-04:00
- `depends_on`: phase 1 complete
- `exit_criteria`:
  - graph schema defined and validated
  - normative unit parsing and link extraction implemented for the graph-targeted layer
  - edge typing and load workflow specified end to end
  - graph integrity can be checked deterministically

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
5. Materializar el manifiesto canonico del corpus admitido, adjuntando `revision_candidate` a sus base docs cuando haya target resoluble.
6. Materializar inventario y metricas del corpus compartido usando solo archivos `include_corpus`.
7. Rotular los documentos admitidos con `family`, `knowledge_class`, `source_type` y estado de vocabulario.
8. Aplicar el canon ratificado como naming authority; conservar aliases viejos solo para compatibilidad.
9. Definir o ajustar node types y edge taxonomy para el backbone regulatorio.
10. Construir parser solo sobre documentos normativos graph-parse-ready admitidos por la auditoria.
11. Extraer referencias y reformas con contexto.
12. Clasificar edges con pipeline deterministico + asistido.
13. Cargar el grafo y ejecutar validadores.
14. Guardar artefactos y reportes en `artifacts/`.

## Checkpoint Log

- `current_step`: 5
- `completed_steps`: [1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12]
- `blocked_by`: ["el corpus compartido completo aun no esta materializado en una ruta local estable", "la auditoria real sobre los Dropbox roots aun no fue ejecutada", "credenciales y entorno FalkorDB no validados"]
- `artifacts_created`: [
  "docs/build/buildv1/03-phase-2-shared-regulatory-graph.md",
  "src/lia_graph/graph/schema.py",
  "src/lia_graph/graph/client.py",
  "src/lia_graph/graph/validators.py",
  "src/lia_graph/ingestion/parser.py",
  "src/lia_graph/ingestion/linker.py",
  "src/lia_graph/ingestion/classifier.py",
  "src/lia_graph/ingestion/loader.py",
  "tests/test_phase2_graph_scaffolds.py"
]
- `notes`: "La fase ya tiene schema, parser, linker, classifier, loader y validadores scaffolded, mas un materializador de artefactos en `python -m lia_graph.ingest` y `make phase2-graph-artifacts`. El flujo de codigo ahora audita todos los source assets por archivo, clasifica `include_corpus` / `revision_candidate` / `exclude_internal`, asigna `extension`, `text_extractable`, `parse_strategy` y `document_archetype`, materializa `corpus_audit_report.json`, `revision_candidates.json`, `excluded_files.json`, `canonical_corpus_manifest.json` y `corpus_inventory.json`, y graphiza solo documentos normativos graph-parse-ready. En Build V1 el grafo debe volverse load-bearing para el razonamiento normativo; `topic` y `subtopic` sobreviven como metadata de apoyo, no como sustituto de relaciones legales. El load sigue staged hasta conectar el cliente FalkorDB real."

## Failure Recovery

- como retomar:
  - leer `src/lia_graph/graph/*.py` y `src/lia_graph/ingestion/*.py` para retomar desde el scaffold vigente
  - correr `uv run --group dev python -m pytest tests/test_phase2_graph_scaffolds.py`
  - leer `docs/build/buildv1/appendix-d-corpus-audit-and-labeling-policy.md` antes de tocar discovery o labeling
  - cuando exista el corpus compartido en ruta estable, correr la auditoria y luego `make phase2-graph-artifacts PHASE2_CORPUS_DIR=knowledge_base`
  - revisar `corpus_audit_report.json`, `revision_candidates.json`, `excluded_files.json` y `canonical_corpus_manifest.json` antes de interpretar el inventario
  - revisar `corpus_inventory.json` antes de interpretar el resto de artefactos
  - revisar `parsed_articles.jsonl` y `raw_edges.jsonl` si existen
  - verificar el ultimo reporte de graph validation
  - confirmar si el parser quedo detenido antes o despues del load
- que verificar antes de continuar:
  - disponibilidad real del corpus compartido completo en una ruta operable
  - si la auditoria esta separando bien corpus, revision candidates y working files
  - si el manifiesto canonico esta adjuntando revisions a base docs correctos
  - conteos por familia razonables para normativa, interpretacion y practica
  - conteos de graph-parse-ready razonables dentro de la familia normativa
  - cobertura de articulos parseados
  - edge taxonomy activa
  - conectividad con FalkorDB

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
- los revision candidates viven adjuntos a base docs dentro del manifiesto canonico, no como corpus standalone
- el vocabulario ratificado es autoridad de nombres para topic y subtopic, pero no reemplaza relaciones legales ni bloquea la admision de dominios validos
