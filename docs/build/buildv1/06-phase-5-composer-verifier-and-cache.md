# 06 — Phase 5: Composer, Verifier and Cache

## Status

- `phase_id`: 5
- `status`: PLANNED
- `owner`: Codex + repo maintainer
- `last_updated`: 2026-04-14T00:00:00-04:00
- `depends_on`: phases 1 to 4 complete
- `exit_criteria`:
  - answers are grounded, actionable and citation-complete
  - verifier checks normative and tenant constraints
  - selective compiled cache behaves predictably
  - invalidation strategy is lineage-aware

## Intent

- objetivo de la fase: producir respuestas utiles, accionables, citadas y reusables
- valor de negocio: convierte retrieval correcto en una salida operativa confiable
- superficies afectadas:
  - answer composition
  - grounding verification
  - citation packaging
  - compiled cache

## Implementation Scope

### Entra

- composer graph-aware
- verifier con vigencia, grounding y tenant safety
- selective compiled cache
- invalidation por lineage normativa y temporal

### No Entra

- rollout global
- default switch de pipeline

## Files To Create

- `src/lia_graph/pipeline_d/composer.py` - nuevo
- `src/lia_graph/pipeline_d/verifier.py` - nuevo
- `src/lia_graph/pipeline_d/compiled_cache.py` - nuevo

## Files To Modify

- `src/lia_graph/pipeline_c/safety.py` - existente
- `src/lia_graph/pipeline_c/telemetry.py` - existente
- `src/lia_graph/ui_reference_resolvers.py` - existente
- `src/lia_graph/citation_resolution.py` - existente
- `src/lia_graph/pipeline_d/orchestrator.py` - existente

## Tests For This Surface

### Unitarias

- citation precision and completeness
- answer actionability rubric hooks
- cache hit/miss behavior
- invalidation por cambio normativo, temporal o tenant policy
- verifier flags y warnings

### Integracion

- composer recibe bundle valido y devuelve `PipelineCResponse`
- consistency entre draft streamed y final payload
- verifier bloquea respuestas sin grounding suficiente

### Smoke/Eval

- eval de accionabilidad
- eval de temporal correctness
- eval de compiled cache freshness

## Execution Steps

1. Definir la estructura del context prompt y del answer skeleton.
2. Implementar verifier con checks normativos y tenant-safe.
3. Introducir compiled cache selectivo.
4. Conectar invalidacion a lineage normativa y parametros temporales.
5. Validar salida final con citas y next action.

## Checkpoint Log

- `current_step`: 0
- `completed_steps`: []
- `blocked_by`: ["phase 4 no ejecutada"]
- `artifacts_created`: ["docs/build/buildv1/06-phase-5-composer-verifier-and-cache.md"]
- `notes`: "La cache debe ser selectiva; no todo answer merece compilarse."

## Failure Recovery

- como retomar:
  - revisar si composer ya emite respuesta compatible
  - revisar si verifier opera antes o despues de safety
  - verificar si el cache store ya existe
- que verificar antes de continuar:
  - lineage IDs disponibles
  - consistencia de citas
  - politicas de invalidacion

## Open Questions

- si la accion recomendada debe ser obligatoria en todas las respuestas o solo en rutas decisionales
- si la cache debe incorporar company context como parte del cache key en rutas decisionales

## Decision Log

- respuestas normativas sin citas suficientes no deben pasar
- compiled cache sera selective-by-design
