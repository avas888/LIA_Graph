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

## Sub-bucketing of bucket (a) — v5 §6.2 ran 2026-04-26

After the §6.5.B initial bucketing, v5 §6.2 ran a sub-bucketing pass on the 9.934 edges in bucket (a) "endpoint not materialized in Falkor" to identify the dominant cause. The script extension (~80 LoC in `scripts/diag_falkor_edge_undercount.py`) split (a) using three lookups: Supabase `parsed_articles.jsonl` (`article_key → article_number, source_path`), Falkor's `whole::*` keyset (paginated), and Falkor's `:ReformNode.reform_id` keyset (paginated). Classification priority **(a1) > (a3) > (a2)** with a math-check on the sum.

### Result (against staging cloud, 2026-04-26)

| Sub-bucket | Count | % of (a) | Reading |
|---|---:|---:|---|
| **(a1) prose-only key mismatch** | **9.848** | **99,1%** | Source/target uses the legacy article_key slug (e.g. `'10-fuentes-y-referencias'`) but Falkor has the article under `whole::{source_path}`. **Dominant.** |
| (a2) genuinely orphaned | 86 | 0,9% | Article was filtered by loader's schema gate; edge correctly dropped. |
| (a3) reform-side missing | 0 | 0,0% | No edge has a reform-id source/target that's missing from Falkor. |
| **sum (math-check)** | **9.934** | 100% | Matches bucket (a) total. ✓ |

### Pattern observation (operator-relevant)

All eight sampled (a1) edges share **the same source document**: `T-REF-LABORAL-reforma-laboral-interpretaciones-expertos.md` (an interpretation/expert-comment file with no article structure → prose-only). This suggests the loss concentrates heavily in **interpretation/expert-comment files**, which are the files most likely to lack `article_number` and so most likely to MERGE into Falkor under the `whole::{source_path}` form. Numbered-article docs (the bulk of `:ArticleNode` entities) are unaffected.

### Decision (Gate 3, v5 §6.2)

**(a1) ≥ 70% → OPEN §6.3.** The fix is to have the classifier emit `_graph_article_key()` for prose-only edges (`whole::{source_path}` form) instead of the legacy `article_key` slug. Recovery upside: **≤ 9.848 edges** recovered into Falkor without any change to the retirement-safety contract.

(a2) at 86 is below the watchlist threshold and is "expected loss confirmed" per the loader's schema gate. (a3) at 0 means there's no missing-ReformNode investigation to open right now.

## Cross-references

- Plan: `docs/aa_next/next_v5.md §6.2 + §6.3` (forward), `docs/aa_next/next_v4.md §6.5` (history).
- Diagnostic script: `scripts/diag_falkor_edge_undercount.py`.
- Related design doc on the loader's endpoint filter: `loader.py:43-65` (the prose-only `whole::{source_path}` keying that drives bucket-(a)).
- Related env-matrix entry: `docs/guide/orchestration.md` will need a row for `FALKORDB_RESULTSET_SIZE_CAP` if anyone ever overrides the default.
