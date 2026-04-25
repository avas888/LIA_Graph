# Ingestion & retrieval learnings — index

*Living doc set. One page per theme. Every rule earns its place by naming the incident, investigation, or PR that created it. Adding a new learning? Cite the commit or the §-reference in `docs/next/ingestionfix_v{1..5}.md`, `docs/next/ingestion_tunningv{1,2}.md`, or the relevant architect study.*

**Scope.** The **headless ingest pipeline** (`src/lia_graph/ingest.py`, `ingest_classifier_pool.py`, `ingest_subtopic_pass.py`, `ingestion/`), the **served retrieval path** (`src/lia_graph/pipeline_d/`), and the **process discipline** we use to run both — investigations, monitoring, cloud writes. Not scoped: UI-facing ingestion, which has its own doc at `docs/next/UI_Ingestion_learnings.md`.

**Why this exists.** Between 2026-04-17 and 2026-04-24 we shipped five ingestion-fix waves (`ingestionfix_v1`–`v5`) followed by a v6 investigation+execution cycle (`ingestion_tunningv1` → `ingestion_tunningv2`). Each wave fixed a distinct class of failure. The NEXT PR that touches ingestion or retrieval is one careless code review away from bringing any of those failures back — because the fixes live in code, not in a doc the next contributor will read. These pages are that doc.

**Reading order for a cold engineer.**

1. [`process/investigation-discipline.md`](process/investigation-discipline.md) — why we run a week of read-only investigation before writing code. The v6 cycle would not have landed without this discipline.
2. [`ingestion/corpus-completeness.md`](ingestion/corpus-completeness.md) — the single highest-leverage finding across the entire program: *your retrieval is only as good as the corpus you ingested*.
3. [`ingestion/parallelism-and-rate-limits.md`](ingestion/parallelism-and-rate-limits.md) — how we got from 40 RPM sequential to 300 RPM parallel without introducing non-determinism. Includes the TPM-ceiling gotcha we hit on the cloud sink.
4. [`retrieval/coherence-gate-and-contamination.md`](retrieval/coherence-gate-and-contamination.md) — the biofuel-in-labor contamination case and why an evidence-coherence gate catches it where a classifier-confidence gate cannot.
5. The rest in any order, as the occasion arises.

---

## Index

### Ingestion
- [`ingestion/corpus-completeness.md`](ingestion/corpus-completeness.md) — 2.7× corpus expansion gated every other metric.
- [`ingestion/parallelism-and-rate-limits.md`](ingestion/parallelism-and-rate-limits.md) — `ThreadPoolExecutor`, `TokenBucket`, deterministic indexed output, TPM vs RPM quotas (classifier pool / phase 2a).
- [`ingestion/supabase-sink-parallelization.md`](ingestion/supabase-sink-parallelization.md) — parallelizing 4 sink stages by reusing the classifier pool primitive (phase 2b). Motivated by a 25-min silent stall in `load_existing_tema`.
- [`ingestion/falkor-bulk-load.md`](ingestion/falkor-bulk-load.md) — why our 2026-04-24 Falkor load stalled at 85 / 3,340 ArticleNodes. Four-anti-pattern stack: `socket_timeout=None` + per-node `GRAPH.QUERY` + MERGE-without-index + no per-query `TIMEOUT`. Pre-phase-2c design.
- [`ingestion/artifact-coherence.md`](ingestion/artifact-coherence.md) — `parsed_articles.jsonl`, `typed_edges.jsonl`, `canonical_corpus_manifest.json` are a **set**, produced and consumed together.
- [`ingestion/path-veto-rule-based-classifier-correction.md`](ingestion/path-veto-rule-based-classifier-correction.md) — Option K2: when an LLM classifier ignores in-prompt path-veto clauses on a non-trivial fraction of docs, ship a Python regex layer above the LLM. Includes the 3-rebuild debugging arc that taught us "rule_matched=True even on no-op agreement is critical for downstream propagation."

### Retrieval
- [`retrieval/diagnostic-surface.md`](retrieval/diagnostic-surface.md) — the v5 30Q panel's "0 primary articles everywhere" was a harness-side measurement bug, not a retrieval failure.
- [`retrieval/coherence-gate-and-contamination.md`](retrieval/coherence-gate-and-contamination.md) — evidence-topic coherence catches the case where classifier confidence is 1.00 but retrieval leaked.
- [`retrieval/citation-allowlist-and-gold-alignment.md`](retrieval/citation-allowlist-and-gold-alignment.md) — defensive citation filter (ported from Lia Contadores) + gold-file taxonomy-key alignment.
- [`retrieval/quality-of-results-evaluation.md`](retrieval/quality-of-results-evaluation.md) — the six failure modes a RAG eval can exhibit; how to design an eval you can trust.
- [`retrieval/router-llm-deferral-architecture.md`](retrieval/router-llm-deferral-architecture.md) — when a fast lexical router short-circuits the LLM despite the LLM having the right heuristics in its prompt: the 3-gate `_should_defer_to_llm` pattern (trigger phrase / magnet topic / competing strong). Closed gate-8 of next_v3.
- [`retrieval/operates-not-defines-heuristic.md`](retrieval/operates-not-defines-heuristic.md) — Alejandro's meta-rule for resolving "topic A vs topic B" ambiguities; the single most generalizable insight from the next_v3 cycle. With 5 derived sub-tests.

### Process
- [`process/investigation-discipline.md`](process/investigation-discipline.md) — a week of read-only investigation beats a week of wrong code.
- [`process/observability-patterns.md`](process/observability-patterns.md) — principles: heartbeat cadence, silent-death stop, delta-based error detection, phase-aware silence.
- [`process/heartbeat-monitoring.md`](process/heartbeat-monitoring.md) — tactical field manual: script shape, metric formulas, the five failure modes I actually hit.
- [`process/cloud-sink-execution-notes.md`](process/cloud-sink-execution-notes.md) — env posture, sourcing `.env.staging`, interpreting "failed=0" under LLM backpressure.
- [`process/aspirational-thresholds-and-qualitative-pass.md`](process/aspirational-thresholds-and-qualitative-pass.md) — how to handle a measurement that misses an absolute threshold without normalizing the miss into a new (lower) threshold. Three-rule policy: keep the threshold, document each exception per-case, gates evaluate independently.

---

*Last updated: 2026-04-24 during v6 execution (phase 0 → phase 6 in a single session). Keep entries terse; volume is a signal of poor editing.*
