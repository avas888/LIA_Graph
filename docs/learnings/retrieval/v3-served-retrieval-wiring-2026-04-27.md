# Wiring the v3 vigencia gate through the served retrieval path

**Source:** End-to-end smoke against local Supabase + local FalkorDB on
2026-04-27 night, after fixplan_v3 sub-fixes 1A→1F shipped at H0 and the
local stack was populated (corpus + 7 fixture veredictos + 11K-row
norm catalog + 41 (:Norm) graph edges).

## What we actually wired

The served retrieval path (`retriever_supabase.retrieve_graph_evidence`)
now calls `_apply_v3_vigencia_demotion` immediately after `hybrid_search`
+ anchor merge. The pass:

1. Pulls `chunk_vigencia_gate_at_date(chunk_ids, as_of)` — a SQL function
   layered on top of `hybrid_search` (rather than rewriting it). Returns
   one row per (chunk, anchor citation) tuple with the resolver's state
   + demotion factor.
2. Filters out chunks whose anchor is `DE / SP / IE / VL` (factor 0.0)
   and demotes contested-DT (factor 0.3).
3. Annotates the kept chunks with a `vigencia_v3` block that propagates
   through `GraphEvidenceItem.vigencia_v3` and (most-restrictive
   per-doc) `Citation.vigencia_v3`.
4. Surfaces a per-turn diagnostic (`vigencia_v3_demotion`) so the chat
   payload's diagnostics tells you exactly how many chunks were seen,
   demoted, and dropped, plus the RPC kind (`at_date` vs `for_period`).

## Three real bugs caught only at the served-retrieval horizon

H0 fakes pass; H1 live integration tests against Postgres + Falkor pass;
the FIRST e2e through `retrieve_graph_evidence` against the populated
local stack found three issues that neither earlier horizon could see:

### 1. `LEFT JOIN` returns null state, demotion treats it as anchor

`chunk_vigencia_gate_at_date` `LEFT JOIN`s `norm_vigencia_at_date(D)`.
When a chunk cites a norm that has a `norm_citations` row but no
`norm_vigencia_history` row yet (the common case during ramp-up — only
7 of 11K norms have history), the gate returns the citation row with
`state = NULL` and `demotion_factor = NULL`.

The Python demotion pass treated `demotion_factor = None` as 1.0 and
attached the annotation anyway, so chunks ended up with
`vigencia_v3 = {anchor_state: None, anchor_norm_id: <real id>, ...}`.
That polluted doc-level aggregation and broke chip rendering downstream.

**Fix:** Filter `state is not None` in the anchor list AND skip
annotation entirely when `anchor_state is None or anchor_norm_id is None`.
The chunk passes through with no annotation, exactly like a chunk that
had no citations at all.

### 2. Doc-level aggregation needs to skip "passthrough" annotations too

`_collect_support` aggregates the most-restrictive `vigencia_v3` across
the doc's chunks. Before the fix above, passthrough rows were polluting
the aggregation. After the fix, the doc only carries an annotation when
at least one of its chunks has a real (non-None) anchor state.

### 3. Existing test fakes need to tolerate the new RPC names

`tests/test_retriever_supabase.py`'s `_FakeClient.rpc()` asserted
`name == "hybrid_search"`. After the demotion pass calls
`chunk_vigencia_gate_at_date`, the assertion blew up. Fix: extend the
fake to accept the v3 RPC names and return empty rows (no demotion in
unit tests). The existing `last_rpc_payload` field still records the
hybrid_search payload so older assertions keep working.

## Process learning

When wiring a sub-fix that adds a new RPC call inside a frequently-
exercised function, every test that uses a fake of that function's
client needs to know the new RPC name. A 2-line allowlist in the fake's
`rpc()` method is the cheapest possible mitigation; the alternative is
test-suite-wide updates after every contract change.

## Diagnostic value

`response.diagnostics.vigencia_v3_demotion` gives the operator a
per-turn answer to "did the v3 gate fire?" without reading code:

```jsonc
{
  "status": "ok",
  "rpc_kind": "for_period",
  "rpc_payload": {"impuesto": "renta", "periodo_year": 2018},
  "chunks_seen": 24,
  "chunks_kept": 22,
  "chunks_dropped": 2,
  "chunks_demoted": 1
}
```

When this block is missing or `status != "ok"`, the gate was a no-op for
that turn — useful when investigating why a derogated norm slipped
through.

## What this enables next

- The chat citation chip (sub-fix 1D) now has a populated annotation to
  read; `frontend/src/shared/ui/atoms/vigenciaChip.ts` reads
  `citation.vigencia_v3` and renders one of the 11 chip variants.
- The `for_period` resolver path is reachable from the planner cue
  (`extract_vigencia_cue("AG 2018")`); the served end-to-end test
  proves the wiring through to `chunk_vigencia_gate_for_period`.
- The Re-Verify Cron's cascade orchestrator can now write to
  `norm_vigencia_history` and the next retrieval turn will see the
  updated state without a code restart.
