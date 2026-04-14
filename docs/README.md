# LIA_Graph Docs Map

This is the active reading order for the repo.

If you are reorienting after an interruption, read these in order:

1. `docs/state/STATE.md`
2. `docs/build/buildV1.md`
3. `docs/build/buildv1/STATE.md`
4. `docs/architecture/FORK-BOUNDARY.md`
5. `docs/build/buildv1/appendix-d-corpus-audit-and-labeling-policy.md`
6. `docs/state/TASK-01-corpus-ingestion.md`
7. `docs/state/TASK-02-pipeline-d-core.md`
8. `docs/state/TASK-03-integration-eval.md`
9. `docs/state/TASK-04-deploy.md`
10. `docs/DEPENDENCIES.md`

## Purpose of Each Doc

- `docs/state/STATE.md`: current phase, steering kernel, and what is shared versus fresh design
- `docs/build/buildV1.md`: executive Build V1 plan for the new purpose-led GraphRAG
- `docs/build/buildv1/STATE.md`: resumable implementation state for Build V1
- `docs/architecture/FORK-BOUNDARY.md`: the main architectural steering rule for this repo
- `docs/build/buildv1/appendix-d-corpus-audit-and-labeling-policy.md`: active policy for corpus admission, labeling, and keeping graph structure load-bearing
- the Build V1 package now assumes a three-layer ingestion view: source assets, canonical corpus, and graph-parse-ready reasoning inputs
- `docs/state/TASK-01-corpus-ingestion.md`: graph ingestion and graph-build plan
- `docs/state/TASK-02-pipeline-d-core.md`: graph-native retrieval and composition plan
- `docs/state/TASK-03-integration-eval.md`: routing and comparison plan
- `docs/state/TASK-04-deploy.md`: rollout and deployment plan
- `docs/DEPENDENCIES.md`: external services and credentials needed

## Build V1 Package

The new architecture and implementation package for the GraphRAG direction lives under:

- `docs/build/buildV1.md`
- `docs/build/buildv1/`

If the work touches corpus ingestion or retrieval narrowing, read `docs/build/buildv1/appendix-d-corpus-audit-and-labeling-policy.md` together with the active phase doc. It records the reset away from label-heavy RAG toward graph-anchored normative reasoning.

Use that package when preparing or resuming the implementation of the new RAG engine. The Build V1 package assumes a shared corpus for all tenants and a multi-tenant runtime layer for history, permissions and context. Use `docs/state/TASK-*.md` for the older phase tracker already present in the repo.

## Deprecated Material

Historical material that still carries old-RAG framing lives under:

`docs/deprecated/old-RAG/`

Read those only for migration archaeology or compatibility work.
