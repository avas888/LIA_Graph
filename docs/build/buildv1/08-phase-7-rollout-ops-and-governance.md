# 08 — Phase 7: Rollout, Ops and Governance

## Status

- `phase_id`: 7
- `status`: PLANNED
- `owner`: Codex + repo maintainer
- `last_updated`: 2026-04-14T00:00:00-04:00
- `depends_on`: phases 1 to 6 complete
- `exit_criteria`:
  - rollout path is reversible
  - graph and cache health are observable
  - deployment and rollback drills are documented
  - architecture docs and operational docs are aligned

## Intent

- objetivo de la fase: dejar el sistema operable, auditado y reversible
- valor de negocio: evita que la nueva arquitectura quede correcta en papel pero insegura en produccion
- superficies afectadas:
  - deployment and smoke
  - ops visibility
  - docs alignment
  - governance and rollback

## Implementation Scope

### Entra

- health checks y smokes
- feature flags o pipeline selection operativa
- rollback plan
- observabilidad minima
- alineacion documental final

### No Entra

- reescritura completa de ops frontend sin necesidad concreta

## Files To Create

- rollout runbooks - nuevos
- graph/cache health artifacts - nuevos

## Files To Modify

- `docs/state/STATE.md` - existente
- `docs/README.md` - existente
- `docs/architecture/FORK-BOUNDARY.md` - existente
- `src/lia_graph/dependency_smoke.py` - existente
- `src/lia_graph/orchestration_settings.py` - existente
- `frontend/src/app/ops/*` - existente si se requiere visibilidad nueva
- `frontend/src/features/ops/*` - existente si se requiere visibilidad nueva

## Tests For This Surface

### Unitarias

- feature flag / pipeline selection helpers
- health check subcomponents

### Integracion

- deployment smoke
- rollback drills
- graph connectivity + cache health checks

### Smoke/Eval

- observabilidad minima para graph health, cache health y eval drift
- post-rollout comparison checks

## Execution Steps

1. Definir rollout stages y rollback triggers.
2. Añadir health checks necesarios para graph y cache.
3. Verificar selecccion operativa del pipeline.
4. Documentar runbooks de rollback y promotion.
5. Alinear docs maestras e inventario final.

## Checkpoint Log

- `current_step`: 0
- `completed_steps`: []
- `blocked_by`: ["phase 6 no ejecutada"]
- `artifacts_created`: ["docs/build/buildv1/08-phase-7-rollout-ops-and-governance.md"]
- `notes`: "El objetivo de esta fase es hacer seguro el cambio de arquitectura, no solo posible."

## Failure Recovery

- como retomar:
  - revisar ultimo estado de feature flags y smokes
  - confirmar la version activa de docs operativas
  - verificar el ultimo baseline comparison post-rollout
- que verificar antes de continuar:
  - conectividad de dependencias
  - rollback trigger documentado
  - dashboards o logs minimos disponibles

## Open Questions

- si rollout visibility necesita UI nueva o basta con logs y runbooks
- si la bandera de activacion vive por tenant, por company o por request mode

## Decision Log

- el cambio de arquitectura debe ser reversible
- la gobernanza del rollout es parte de la implementacion, no un anexo
