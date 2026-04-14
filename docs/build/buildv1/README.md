# Build V1 Package

Este directorio contiene el paquete operativo para construir el nuevo RAG con Graph sin perder continuidad entre sesiones.

`docs/build/` contiene solo documentacion. Los archivos de implementacion referenciados en este paquete deben crearse u organizarse en el arbol normal del proyecto segun mejor practica tecnica.

## Reading Order

1. `STATE.md`
2. `00-business-purpose-and-success-metrics.md`
3. `01-target-architecture.md`
4. `02-phase-1-runtime-seams-and-contracts.md`
5. `03-phase-2-shared-regulatory-graph.md`
6. `04-phase-3-graph-planner-and-retrieval.md`
7. `05-phase-4-tenant-runtime-context-history-and-access.md`
8. `06-phase-5-composer-verifier-and-cache.md`
9. `07-phase-6-routing-evals-and-shadow-mode.md`
10. `08-phase-7-rollout-ops-and-governance.md`
11. `appendix-a-file-map.md`
12. `appendix-b-test-map.md`
13. `appendix-c-state-template.md`
14. `appendix-d-corpus-audit-and-labeling-policy.md`

## Working Rule

Antes de tocar codigo:

- leer `STATE.md`
- abrir la fase activa
- retomar desde `Checkpoint Log.current_step`
- si la fase toca ingestion, corpus o retrieval, leer tambien `appendix-d-corpus-audit-and-labeling-policy.md`

Regla operativa nueva para ingestion:

- pensar siempre en tres capas: source assets, canonical corpus y reasoning inputs graph-parse-ready

Si una sesion falla, este paquete debe ser suficiente para continuar sin reconstruir contexto externo.
