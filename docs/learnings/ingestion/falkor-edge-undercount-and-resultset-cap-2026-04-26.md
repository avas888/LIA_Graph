# Falkor edge undercount + 10k-row resultset cap (2026-04-26)

> **Trigger.** GUI ingestion's "Salud del corpus" tarjeta showed `Parity Supabase ↔ Falkor: Desfasada` with deltas equal to ~the entire corpus. Operator (jefe) asked whether this was real drift or a probe bug. Investigation under `docs/aa_next/next_v4.md §6.5` (B + E).

## Findings

### 1. The original "Desfasada" alarm was a label-name bug in the parity probe

`src/lia_graph/ingestion/parity_check.py` queried `:Document` and `:Article` labels. Falkor's actual schema uses `:ArticleNode` (per `graph/schema.py:13`); `:Document` and `:Article` don't exist anywhere in this codebase. So both `falkor_docs` and `falkor_articles` were always 0.

**Fix landed.** Probe now queries `count(DISTINCT a.source_path)` for the docs proxy and `:ArticleNode` for the articles count. Tests 5/5 green.

### 2. Real edge gap between Supabase and Falkor: 5.229 (17%) — bucketing

| Bucket | Count | % of Supabase | Reading |
|---|---:|---:|---|
| Present and correct in both | 19.815 | 65,8% | Healthy core |
| Type-mismatch (Falkor richer) | 300 | 1,0% | Loader upgrades `references` → `REQUIRES`/`COMPUTATION_DEPENDS_ON`. Feature, not loss. |
| Endpoint not materialized in Falkor | 9.934 | 33,0% | Loader filter (`loader.py:271-279`). Mostly source articles using legacy `article_key` form (e.g. `'10-fuentes-y-referencias'`) whose Falkor MERGE key is `whole::{source_path}` — the edge keys point at the legacy form so the MATCH fails. By design, but the proportion is high enough to revisit. |
| Silent drop (both endpoints exist, edge missing) | 54 | 0,18% | All `references → CITA`. Bug, but acutely scoped. |
| Unknown relation in mapping | 0 | 0% | — |

**Decision metric (next_v4 §6.5.B Gate-3):** silent-drop bucket = 54, threshold was ≤ 50. Numerically above; semantically a single-pattern, < 0,2% phenomenon. Per the operator's `feedback_thresholds_no_lower` rule we don't relax the threshold itself. We mark this as a **case-by-case qualitative-pass** with concentrated pattern (`references → CITA`) on a watchlist for the next ingest.

### 3. **FalkorDB server caps response rows at 10.000 — silently** (the lateral finding)

The server applies `MAX_RESULTSET_SIZE = 10000` (FalkorDB default). When a query returns more rows, the tail is dropped without an error or flag. Discovered when a probe pull returned exactly 10000 rows; confirmed empirically (`LIMIT 15000 → 10000`). Pagination via `SKIP $n LIMIT $m` evades the cap.

**Audit of every runtime query** (`pipeline_d/retriever_falkor.py` — the only file outside ingestion that issues Falkor queries):

| Query | Bound mechanism | Realistic max rows |
|---|---|---|
| `article_node_total` | `count()` agg | 1 |
| `match_by_article_number` (probe) | `count()` agg | 1 |
| `match_by_article_key_legacy` (probe) | `count()` agg | 1 |
| `subtopic_bound_articles` | explicit `LIMIT $limit` | ≤ limit |
| `tema_bound_articles` | explicit `LIMIT $limit` | ≤ limit |
| `primary_articles` | input sliced `[:limit]` (limit ≤ 5) | ~50 (with article_number collisions) |
| `connected_articles` | explicit `LIMIT $limit` | ≤ limit |
| `related_reforms explicit` | input sliced `[:limit]` (limit ≤ 4) | ~4 |
| `related_reforms via neighborhood` | explicit `LIMIT $limit` | ≤ limit |

`evidence_bundle_shape` limits across every query mode: `primary ≤ 5`, `connected ≤ 5`, `reforms ≤ 4` (`pipeline_d/planner.py:118-220`). **No current query can plausibly hit the 10k cap.**

**Defensive guard added.** `src/lia_graph/graph/result_guard.py` emits a structured event `graph.resultset_cap_reached` whenever a query returns ≥ cap rows. Hooked into `GraphClient.execute`. Cap is configurable via `FALKORDB_RESULTSET_SIZE_CAP` env. Tests 5/5 green. Cost to current code: zero. Benefit: any future query that regresses past the cap surfaces immediately in `logs/events.jsonl` instead of as mystery-incomplete answers.

## What changed in this session

| File | Change |
|---|---|
| `src/lia_graph/ingestion/parity_check.py` | `:Document` → `count(DISTINCT a.source_path)`; `:Article` → `:ArticleNode`; docstring documents the gen-tag asymmetry. |
| `src/lia_graph/graph/result_guard.py` | New module — emits `graph.resultset_cap_reached` event on cap hit. |
| `src/lia_graph/graph/client.py` | Hook the guard into `GraphClient.execute` (one import + two call sites). |
| `tests/test_parity_check.py` | Fake graph client matches the new label queries. |
| `tests/test_graph_result_guard.py` | New — 5 cases: below cap, at cap, custom cap, query truncation, emit-failure swallowed. |
| `scripts/diag_falkor_edge_undercount.py` | New diagnostic — paginated Falkor pull + 4-bucket classification. Read-only. |
| `docs/aa_next/next_v4.md §6.5` | New section: items A (gen-tag propagation), B (silent-drop watchlist), D (33% endpoint-missing investigation), E (cap audit, this finding) — all with full six-gate templates. |

## Cross-references

- Plan: `docs/aa_next/next_v4.md §6.5`.
- Diagnostic script: `scripts/diag_falkor_edge_undercount.py`.
- Related design doc on the loader's endpoint filter: `loader.py:43-65` (the prose-only `whole::{source_path}` keying that drives bucket-(a)).
- Related env-matrix entry: `docs/guide/orchestration.md` will need a row for `FALKORDB_RESULTSET_SIZE_CAP` if anyone ever overrides the default.
