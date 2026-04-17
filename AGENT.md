# AGENT.md

Compatibility pointer for agent runtimes that still look for `AGENT.md`.

The canonical repo-level guidance for all agents now lives in:

- `AGENTS.md`

The main critical architecture file every agent should read before changing the served runtime is:

- `docs/guide/orchestration.md`

The companion source of truth for live chat-answer shaping is:

- `docs/guide/chat-response-architecture.md`

If the task touches ingestion, graph build, labeling, routing, retrieval, or FalkorDB integration, also read:

1. `docs/build/buildv1/STATE.md`
2. `docs/build/buildv1/01-target-architecture.md`
3. `docs/build/buildv1/03-phase-2-shared-regulatory-graph.md`
4. `docs/build/buildv1/appendix-d-corpus-audit-and-labeling-policy.md`
5. `docs/architecture/FORK-BOUNDARY.md`

Use `AGENTS.md` as the authoritative operating guide so repo instructions do not drift across agent entry files.
