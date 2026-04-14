# 07 — Phase 6: Routing, Evals and Shadow Mode

## Status

- `phase_id`: 6
- `status`: PLANNED
- `owner`: Codex + repo maintainer
- `last_updated`: 2026-04-14T00:00:00-04:00
- `depends_on`: phases 1 to 5 complete
- `exit_criteria`:
  - dual-run path is defined
  - comparative eval harness exists
  - shadow mode can observe Pipeline D without user-facing cutover
  - promotion gates are measurable

## Intent

- objetivo de la fase: comparar con baseline y reducir riesgo antes del rollout
- valor de negocio: permite promover la nueva arquitectura con evidencia y rollback facil
- superficies afectadas:
  - runtime routing
  - eval harness
  - shadow logging
  - telemetry and comparison metrics

## Implementation Scope

### Entra

- routing baseline vs graph engine
- dual-run evaluation
- shadow mode instrumentation
- promotion metrics and gates

### No Entra

- default cutover
- product-wide ops dashboards beyond what rollout needs

## Files To Create

- `evals/run_dual_pipeline_eval.py` - nuevo
- `scripts/run_shadow_compare.py` - nuevo opcional
- shadow comparison storage artifacts - nuevos

## Files To Modify

- `src/lia_graph/ui_server.py` - existente
- `src/lia_graph/ui_chat_controller.py` - existente
- `evals/README.md` - existente
- `evals/*` datasets y rubrics - existentes o nuevos

## Tests For This Surface

### Unitarias

- routing selector for single-run and dual-run
- comparison payload structure
- metric aggregation helpers

### Integracion

- dual-run end to end
- shadow logging persistido
- no regression en `/api/chat` y `/api/chat/stream`

### Smoke/Eval

- rubric eval
- pairwise comparison
- regression protection sobre superficies actuales
- metricas de exactitud, vigencia, tenant safety, latency y citation quality

## Execution Steps

1. Definir modos de routing para baseline, graph y dual-run.
2. Extender harness de eval con comparacion lado a lado.
3. Registrar shadow outputs sin servirlos al usuario.
4. Definir promotion gates y thresholds.
5. Ejecutar corridas controladas y priorizar gaps.

## Checkpoint Log

- `current_step`: 0
- `completed_steps`: []
- `blocked_by`: ["phase 5 no ejecutada"]
- `artifacts_created`: ["docs/build/buildv1/07-phase-6-routing-evals-and-shadow-mode.md"]
- `notes`: "Ningun default flip debe ocurrir antes de que shadow mode y evals produzcan evidencia suficiente."

## Failure Recovery

- como retomar:
  - revisar si dual-run ya esta cableado o solo el selector
  - localizar el ultimo artifact de comparison run
  - verificar si shadow logging sigue alineado con chat_run_id
- que verificar antes de continuar:
  - integridad del baseline
  - rubricas vigentes
  - consumo de telemetria

## Open Questions

- si el selector de dual-run se expone por config, header o ambos
- si los outputs de shadow mode deben persistirse en Supabase o en artifacts primero

## Decision Log

- shadow mode es obligatorio antes del cambio de default
- la promocion del nuevo motor requiere evidencia comparativa, no intuicion
