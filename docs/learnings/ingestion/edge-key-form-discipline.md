# Edge-key form discipline: write-path and delete-path must mirror

> **Captured 2026-04-26** during v5 §6.3 — the prose-only edge-key fix that recovered 9,848 missing Falkor edges. The linker change was correct but incomplete; only after reading [`supabase-sink-parallelization.md`](supabase-sink-parallelization.md) did the matching delete-path leak surface. This learnings doc generalizes the lesson so future engineers don't re-discover it.

## The rule (binding)

**When a pipeline writes to a key-discriminated table, every code path that DELETEs from that table must use the same key-form the writer would use.** If the writer's key-form changes, every downstream delete must change in lockstep — in the same PR — otherwise the delete becomes a silent no-op and stale rows accumulate.

For Lia Graph specifically: `normative_edges` upserts on `(source_key, target_key, relation, generation_id)` and is cleaned up via `WHERE source_key = …` queries on retire + modify. If you change how `source_key` is computed at write time, you must change every `WHERE source_key = …` clause to use the same computation.

## The incident — how this surfaced

v5 §6.3 changed the linker so that prose-only articles emit edges with `source_key = "whole::{source_path}"` instead of the slug form (`'10-fuentes-y-referencias'`). The loader's Falkor MERGE side already used the `whole::` form for `:ArticleNode {article_id: …}`, so the WRITE-side change was logically correct: now the slug-vs-whole mismatch closes, and the edges land in Falkor.

**But the supabase_sink retire + modify paths kept matching on the slug form.** If a prose-only doc were modified post-fix, the cleanup `DELETE WHERE source_key = '10-fuentes-y-referencias'` would find zero rows (because the new rows live under `whole::…`), the new edges would be UPSERTed correctly, but stale edges from the previous classify would silently linger. If a prose-only doc were retired (CLI `--allow-retirements`), the same mismatch would leave edges in `normative_edges` while the corresponding `:ArticleNode` is `DETACH DELETE`d from Falkor — Supabase / Falkor inconsistency.

The leak doesn't break retrieval (Falkor doesn't see the orphaned rows so they're invisible) but it bloats the table over time and breaks the retire-cleanup invariant.

## Why the leak was easy to miss

The unit tests for the linker change passed cleanly: a prose-only article emits an edge with `source_key='whole::…'`. Green. ✓

The on_conflict for `normative_edges` is `(source_key, target_key, relation, generation_id)` — different `source_key` values are different rows, no conflict resolution catches the duplication. So the writer is happy.

The cleanup happens in a different module (`supabase_sink.py`) the linker change doesn't touch. A grep for "linker.py" in the diff would not surface the cleanup leak. **Only a careful read of the existing supabase_sink + the existing learnings doc on sink parallelization would surface it.**

## The triage checklist (paste into PR template for any normative_edges-touching change)

When changing how any column of `normative_edges` is **written**:

1. **Find every `.eq("<column>", X)` in `supabase_sink.py`** for that column. Each is a delete or update site that may need to mirror the new write-form.
2. **Find every `.eq("<column>", X)` in `delta_runtime.py`** and downstream sinks/promoters.
3. **Find every Falkor `MATCH (… {<column>: $key}) … DETACH DELETE`** in `loader.py` / `delta_runtime.py`. These are the loader-side delete equivalents.
4. **For each match, ask: "After my change, will this query find the rows the new writer just wrote?"** If no, it's a leak waiting to happen. Fix it in the same PR.

Same checklist applies symmetrically for `documents`, `document_chunks`, `normative_anchors`, and any other key-discriminated table.

## Why this lives next to `supabase-sink-parallelization.md`

The parallelization doc rightly emphasizes that "row-level partitioning is safe iff no two partitions can target the same key." This doc is the **other half** of that contract: the table-level safety only holds if every code path that targets the key uses the same key-form. Parallelism is one consideration; key-form parity is the parallel one.

## Anti-patterns to watch for

- **"The fix is just on the write side."** It almost never is when the table has retire/modify cleanup paths.
- **"The unit tests pass."** Unit tests for the writer don't exercise the cleanup. Tests for the cleanup don't see the new write form unless someone updates the fixture. Coverage isn't capturing the contract.
- **"We can clean it up later."** Stale rows compound. After 5 deltas the count is still tractable; after 50 it's not. Fix in-PR.
- **"Just delete based on `chunk_id` / `doc_id` instead of `source_key`."** Sometimes valid — if a higher-level identifier is canonical and the column you changed is derived. But verify by tracing every `.eq()` call site, don't just intuit.

## What this doc is NOT

- **Not a generic database-migration guide.** It's specifically about the Lia Graph pipeline's `normative_edges` write/delete pattern. Apply the principle (write-form parity) to other pipelines but don't copy the specifics.
- **Not a performance concern.** The leak doesn't affect retrieval latency; it just bloats Supabase. Functional correctness is the issue.
- **Not a substitute for thinking through the change.** This checklist is a backstop. The real defense is understanding what your column means and where it's read.

## Cross-references

- The §6.3 incident that taught us this: [`falkor-edge-undercount-and-resultset-cap-2026-04-26.md`](falkor-edge-undercount-and-resultset-cap-2026-04-26.md) — "v5 §6.3 fix — outcome" section.
- Sister discipline on the parallelism side: [`supabase-sink-parallelization.md`](supabase-sink-parallelization.md) — "Why the sink is safe to parallelize" section.
- Code:
  - `src/lia_graph/ingestion/linker.py::_extract_article_edges` (the writer).
  - `src/lia_graph/ingestion/supabase_sink.py:919-927, 937-945` (the delete paths that needed mirroring).
  - `src/lia_graph/ingestion/loader.py::graph_article_key` (the canonical key-form helper — public from v5 §6.3).
