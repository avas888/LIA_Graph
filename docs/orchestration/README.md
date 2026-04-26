# Orchestration docs — index

This folder is the **single home** for every doc that describes how Lia Graph's runtime + ingestion + assembly actually executes. Two depth-levels:

| Doc | Audience | Purpose |
|---|---|---|
| [`orchestration.md`](orchestration.md) | New engineers, returning agents, anyone onboarding | Architecture-level guide. Lanes 0-7. Module names + invariants + decisions. |
| [`retrieval-runbook.md`](retrieval-runbook.md) | Anyone debugging "why did Lia refuse / mis-rank" | Line-level execution flow of `pipeline_d/retriever_supabase.py` + `retriever_falkor.py`. Includes RRF formula, hybrid_search SQL, support_document selection logic, anchor fetch, every threshold. |
| [`coherence-gate-runbook.md`](coherence-gate-runbook.md) | Anyone diagnosing a `topic_safety_abstention` answer | Decision tree from `fallback_reason` value → exact code path → fix candidates. Every `pipeline_d_*` reason explained with line refs. |

**Companion docs (in adjacent folders):**

- [`docs/guide/chat-response-architecture.md`](../guide/chat-response-architecture.md) — visible-answer shaping policy. Covers ASSEMBLY shape decisions; references this folder for retrieval/synthesis depth.
- [`docs/guide/env_guide.md`](../guide/env_guide.md) — per-mode env flags + run modes.
- [`docs/learnings/ingestion/`](../learnings/ingestion/) — captured lessons from past incidents. Falkor wire-format quirks, sink parallelization, parity probe pitfalls, etc.
- [`docs/aa_next/next_v5.md`](../aa_next/next_v5.md) — current forward plan + open difficulties (e.g. §1.C catalogues the 4 thin-corpus topics still refusing as of 2026-04-26 evening).

## Reading order recommendations

**Onboarding from scratch.** `orchestration.md` first (~30 min read). Then come back to this folder when you hit a specific problem.

**Debugging a chat refusal.** Start with `coherence-gate-runbook.md` → grep for the exact `fallback_reason` from the API response → follow its decision-tree branch → land in the relevant section of `retrieval-runbook.md` or `chat-response-architecture.md`.

**Tracing a "why did this question return X chunks?" question.** `retrieval-runbook.md` end-to-end — it walks every transformation between user message and `GraphEvidenceBundle`.

**Adding new ingest/retrieve/assemble code.** Update `orchestration.md` (architecture map) AND the appropriate runbook (line-level detail) **in the same task as the code change**. Per the non-negotiable in `CLAUDE.md`: docs and code must stay aligned.

## Versioning

Runbooks evolve with the code. Every PR that changes module behavior should bump the relevant runbook section. The architecture-level doc (`orchestration.md`) carries a versioned env matrix at the bottom; runbooks don't have a version stamp but should cite line numbers + commit refs in their content so a stale section is recognizable.
