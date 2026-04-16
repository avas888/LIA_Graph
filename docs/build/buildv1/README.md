# Build V1 Package

Este directorio contiene el paquete operativo para construir el nuevo RAG con Graph sin perder continuidad entre sesiones.

`docs/build/` contiene solo documentacion. Los archivos de implementacion referenciados en este paquete deben crearse u organizarse en el arbol normal del proyecto segun mejor practica tecnica.

## Reading Order

1. `NEXT.md`
2. `STATE.md`
3. `00-business-purpose-and-success-metrics.md`
4. `01-target-architecture.md`
5. `02-phase-1-runtime-seams-and-contracts.md`
6. `03-phase-2-shared-regulatory-graph.md`
7. `04-phase-3-graph-planner-and-retrieval.md`
8. `05-phase-4-tenant-runtime-context-history-and-access.md`
9. `06-phase-5-composer-verifier-and-cache.md`
10. `07-phase-6-routing-evals-and-shadow-mode.md`
11. `08-phase-7-rollout-ops-and-governance.md`
12. `appendix-a-file-map.md`
13. `appendix-b-test-map.md`
14. `appendix-c-state-template.md`
15. `appendix-d-corpus-audit-and-labeling-policy.md`

## Working Rule

Antes de tocar codigo:

- leer `NEXT.md`
- leer `STATE.md`
- abrir la fase activa
- retomar desde `Checkpoint Log.current_step`
- si la fase toca ingestion, corpus o retrieval, leer tambien `appendix-d-corpus-audit-and-labeling-policy.md`

Regla operativa nueva para ingestion:

- pensar siempre en tres capas: source assets, canonical corpus y reasoning inputs graph-parse-ready
- tratar `NEXT.md` como hoja corta y mutable de "que hacemos ahora", mientras `STATE.md` conserva el ledger mas durable y explicativo

Si una sesion falla, este paquete debe ser suficiente para continuar sin reconstruir contexto externo.
