# 04 — Phase 3: Graph Planner and Retrieval

## Status

- `phase_id`: 3
- `status`: PLANNED
- `owner`: Codex + repo maintainer
- `last_updated`: 2026-04-14T00:00:00-04:00
- `depends_on`: phases 1 and 2 complete
- `exit_criteria`:
  - planner outputs query mode, entry points and budgets
  - retriever returns graph-aware evidence bundle
  - time-scope and vigencia filters influence retrieval decisions
  - fallback semantic path defined for weak anchors

## Intent

- objetivo de la fase: convertir preguntas reales de contador en entry points, traversal plans y evidence bundles
- valor de negocio: evita retrieval plano y recupera cadenas normativas utiles para responder
- superficies afectadas:
  - intake/planning
  - graph retrieval
  - topic bridge
  - evidence assembly
  - lane coordination across normativa, interpretacion y practica
  - consumo del corpus auditado y rotulado sin volver topic/subtopic la capa load-bearing
  - consumo de la capa canonica, no de source assets crudos

## Implementation Scope

### Entra

- planner de modos de consulta
- seleccion de entry points
- traversal budgets
- graph retrieval y subgraph assembly
- semantic fallback controlado

### No Entra

- composer final
- runtime history and access controls
- compiled cache

## Files To Create

- `src/lia_graph/pipeline_d/planner.py` - nuevo
- `src/lia_graph/pipeline_d/retriever.py` - nuevo
- `src/lia_graph/pipeline_d/contracts.py` - nuevo
- `src/lia_graph/pipeline_d/evidence_bundle.py` - nuevo opcional

## Files To Modify

- `src/lia_graph/topic_router.py` - existente
- `src/lia_graph/pipeline_c/intake.py` - existente
- `src/lia_graph/pipeline_c/norm_topic_index.py` - existente
- `src/lia_graph/pipeline_d/orchestrator.py` - existente o nuevo segun phase 1

## Tests For This Surface

### Unitarias

- resolucion de entry points desde articulo, concepto, workflow y company cues
- query mode selection
- traversal budgets y edge filters
- vigencia/time-scope correctness
- semantic fallback cuando faltan anchors

### Integracion

- planner + retriever sobre subgrafo real
- handoff correcto desde intake compartido
- bundle consistente para preguntas multi-hop
- mezcla controlada de backbone normativo con support evidence interpretativo/practico cuando aplique
- preservacion de labels canonicos como hints, sin reemplazar entry points y traversal graph-based
- respeto por `graph_parse_ready` y `parse_strategy` al decidir que evidencia entra por grafo y cual entra por retrieval support

### Smoke/Eval

- retrieval quality en preguntas multi-hop de normativa, con ET como slice importante pero no unico
- comparacion baseline vs graph bundle en casos seleccionados

## Execution Steps

1. Definir el planner output contract.
2. Mapear señales desde `topic_router` e intake compartido sin volver `topic/subtopic` la unica puerta de entrada.
3. Resolver entry points normativos y contextuales.
4. Ejecutar traversal con vigencia y budget.
5. Empaquetar el evidence bundle con provenance suficiente para composer, respetando la frontera entre canonical corpus y source assets.

## Checkpoint Log

- `current_step`: 0
- `completed_steps`: []
- `blocked_by`: ["phase 2 no ejecutada"]
- `artifacts_created`: ["docs/build/buildv1/04-phase-3-graph-planner-and-retrieval.md"]
- `notes`: "Esta fase debe evitar que todo query entre por el mismo path caro; query modes son obligatorios."

## Failure Recovery

- como retomar:
  - verificar el ultimo planner contract aprobado
  - revisar si ya existe `evidence_bundle.py`
  - inspeccionar si fallback semantic se disparaba por ausencia de anchors o por bug de planner
- que verificar antes de continuar:
  - existencia del graph schema
  - existencia de audit outputs e inventario del corpus compartido
  - normalizacion de topics sin depender solo de ellos para narrowing
  - filtros temporales disponibles

## Open Questions

- si `global_pattern` vive en esta fase o se deja solo documentado para implementacion posterior
- si el bridge con `norm_topic_index.py` debe quedarse o retirarse cuando FalkorDB asuma el rol principal

## Decision Log

- retrieval sera mode-aware
- semantic fallback existe, pero no domina el path cuando el grafo tiene buenos anchors
- labels y vocabulario ayudan con entry hints y compatibilidad, pero el razonamiento normativo debe descansar en graph anchors, traversal y provenance
