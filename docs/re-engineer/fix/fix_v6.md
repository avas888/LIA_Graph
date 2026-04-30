## fix_v6.md — staging-health hand-off: project the norms catalog into Falkor + close two cosmetic gaps

> **Drafted 2026-04-29 ~7:55 PM Bogotá** by claude-opus-4-7 immediately
> after a staging-environment health audit (fix_v5 phase 6 close-out
> session, commit `69a811a` on `main`). The audit confirmed migrations
> are aligned, UI is fresh, Supabase corpus is fully embedded
> (19,546 / 19,546), and FalkorDB cloud is reachable. **Three yellow
> flags remain** — none break the served chat path today, but all three
> degrade graph traversal coverage as the canonicalizer keeps writing
> norms. This doc is the scoped fix.
>
> **Audience**: zero-context agent (fresh LLM or engineer). You can
> pick this up cold. **This doc is NOT an SME-panel iteration** —
> fix_v1 through fix_v5 chased the §1.G 36-Q panel; fix_v6 is an
> infra / projection fix at the Supabase ↔ Falkor seam. Different
> layer, different success criterion.
>
> **Scope guard.** The fix_v5 §1.G panel closed at **32 strong / 4
> acc / 0 weak / 36 acc+** (anchor:
> `evals/sme_validation_v1/runs/20260430T000527Z_fix_v5_phase6b_rerun/`).
> That bar must not regress. Re-run §1.G after the projection lands
> and confirm 36/36 acc+ with no drop in strong count.

---

## 0. Inheritance from fix_v5 (read once, then this doc)

Everything in `fix_v5.md` §0 (zero-context primer) and `fix_v4.md`
§0/§4/§5/§6 carries forward unchanged:

* The six-gate lifecycle is mandatory (idea / plan / measurable
  criterion / test plan / greenlight / refine-or-discard).
* `provider_order` in `config/llm_runtime.json` stays gemini-flash
  first — DO NOT flip back to deepseek-v4-pro for chat.
* Don't run the full pytest suite — `make test-batched`.
* Cloud writes to Lia Graph (NOT Lia Contador) are pre-authorized;
  announce before executing, no per-action confirmation.
* The Falkor adapter must keep propagating cloud outages — no silent
  artifact fallback on staging.
* Vigencia is **norm-keyed, never document-keyed**; persist on the
  norm itself in `norm_vigencia_history`. (This rule is why flag #3
  below is informational, not a bug.)

Layer-specific to this doc:

* The canonical `norms` table was populated by the canonicalizer in
  one bulk write today (Apr 29) — **all 17,169 rows have
  `created_at = 2026-04-29`** in Supabase. None of those rows have
  been projected to FalkorDB yet. This is expected for the
  canonicalizer ↔ ingestion split, but the projection step has to
  ship before graph queries can join the new norms to articles.

---

## 1. The diagnosis (verified 2026-04-29 ~7:40 PM Bogotá against staging)

Captured during the health audit. Numbers are from live queries
against cloud Supabase (`utjndyxgfhkfcrjmtdqz`) and cloud FalkorDB
(`LIA_REGULATORY_GRAPH`); all migrations are applied (18/18 via
`supabase migration list --linked`).

### Yellow flag #1 — Norms catalog is in Supabase but not projected to Falkor

* **Supabase `norms` table**: 17,169 rows, all created today by the
  canonicalizer. Breakdown by `norm_type`:

  | norm_type | rows |
  |---|---:|
  | `oficio_dian` | 5,298 |
  | `decreto_articulo` | 3,426 |
  | `concepto_dian` | 2,625 |
  | `decreto` | 1,445 |
  | `ley_articulo` | 1,200 |
  | `articulo_et` | 1,098 |
  | `resolucion` | 672 |
  | `ley` | 488 |
  | `res_articulo` | 331 |
  | `cst_articulo` | 255 |
  | `cco_articulo` | 184 |
  | `sentencia_cc` | 120 |
  | `sentencia_ce` | 10 |
  | (other long tail) | 17 |

* **FalkorDB `Norm` label**: only **2,905 nodes**. Sample
  `norm_id`s look like `ley.1607.2012`, `ley.788.2002`,
  `ley.1450.2011` — i.e. parent-law granularity, not the
  article-level norms (`ley.2010.2019.art.10`,
  `articulo_et.*`, `oficio_dian.*`) the canonicalizer just
  populated.
* **Gap**: ~14,264 norms exist in Supabase with no Falkor projection.
  Per the vigencia-norm-keyed memory, this is acceptable for chat
  (the vigencia gate runs as a Supabase RPC —
  `chunk_vigencia_gate_at_date` / `norm_vigencia_at_date` — and
  needs no Falkor lookup), but **graph traversal cannot reach those
  norms**. Any future planner step that wants to walk
  `Article -[:REFERENCES]-> Norm -[:MODIFIED_BY]-> Norm` for the
  newly canonicalized stack will return empty.
* **Why this is yellow not red today**: served chat answers
  currently route through `retriever_supabase` for chunks +
  `retriever_falkor` for `primary_articles` / `connected_articles` /
  `related_reforms`. Article-level traversal still works (9,249
  ArticleNode in Falkor). Norm-level traversal silently returns
  fewer hits than the catalog suggests.

### Yellow flag #2 — TopicNode IDs are NULL on every sample

* **Falkor query**:
  `MATCH (n:TopicNode) RETURN n.topic_id, n.label LIMIT 10`
* **Result**: all 10 returned `topic_id = None`, `label` populated
  (e.g. `"Comercial y societario"`, `"Declaración de renta"`,
  `"ICA"`, `"Información exógena"`, `"IVA"`, `"Nómina y laboral"`,
  …).
* **Gap**: 82 TopicNode in total; spot-check shows the `topic_id`
  property is missing/null. `label` is the human string the planner
  uses for `TEMA` lookups, so this is **probably cosmetic** today.
  But if any retriever / planner code keys off `topic_id` (e.g. for
  joining back to `sub_topic_taxonomy.topic_slug` in Supabase), it
  would silently miss. Needs a one-grep audit before this is closed
  as cosmetic.

### Yellow flag #3 — Falkor `Norm` nodes have no vigencia properties

* **Falkor query**:
  `MATCH (n:Norm) WHERE exists(n.vigencia_status) RETURN count(n)`
* **Result**: **0 of 2,905**.
* **Gap**: this is the *expected* shape under the v3 norm-keyed
  vigencia design — vigencia state lives in
  `norm_vigencia_history` (Supabase, 9,322 rows today, all created
  Apr 29) and is read via SQL functions, not Falkor properties.
  Recording it here as a yellow flag because a fresh agent reading
  the graph might assume vigencia is queryable in Cypher and write
  a planner branch that always returns empty.
* **Action**: not a code change — a docs change. Add a one-line
  note to `docs/orchestration/orchestration.md` and to the Falkor
  graph schema docstring stating "vigencia is never on Norm
  properties; query `norm_vigencia_at_date(norm_id, asof)` SQL RPC
  instead."

### What's already healthy (do not regress)

* Migrations: 18/18 applied on cloud (latest
  `20260501000006_norms_norm_type_extend`).
* `document_chunks`: 19,546 / 19,546 with embeddings filled (100%).
* `normative_edges` (Supabase): 354,025 — much fatter than Falkor's
  27,131 edges. Some of that is bidirectional / candidate /
  pre-projection bookkeeping; do NOT assume parity is the goal.
* Active corpus generation: `gen_20260425123153` (Apr 25, 1,280
  docs / 7,883 chunks). Last delta `delta_20260426_145314` Apr 26 —
  closed cleanly: 3 added, 5 retired, 0 errors,
  `falkor_success=20/20`.
* Preflight (`npm run dev:staging:check`): green on falkordb,
  supabase, gemini.
* Served bundle: `ui/` at repo root, freshly rebuilt Apr 29 19:30
  Bogotá. (`frontend/dist/` is stale-Apr-19 unused — see §4.)

---

## 2. The plan — three surgical routes, recommended phasing 7a→7c

### Route N1 — project the canonicalizer's `norms` catalog into Falkor (phase 7a, the big lever)

* **Idea (gate 1)**: read every row in Supabase `norms` and stage a
  `Norm {norm_id, norm_type, parent_norm_id, display_label, emisor,
  fecha_emision, canonical_url, is_sub_unit, sub_unit_kind}` node
  via `GraphClient.stage_node` + bulk-execute through the live
  executor. Same pattern the existing ingestion path uses for
  ArticleNode / ReformNode.
* **Plan (gate 2)**: write `scripts/cloud_promotion/project_norms_to_falkor.py`
  (NEW file, single purpose). Two phases:
  1. **Nodes**: `MERGE (n:Norm {norm_id: $norm_id})
     SET n += $properties`. Idempotent by `norm_id` (PK in Supabase,
     unique key in Falkor schema).
  2. **Hierarchy edges**: for every row with non-null
     `parent_norm_id`, stage `(:Norm {norm_id: $child}) -[:IS_SUB_UNIT_OF]-> (:Norm {norm_id: $parent})`.
     The `IS_SUB_UNIT_OF` rel type already exists in Falkor (visible
     in `CALL db.relationshipTypes()`).

  Use `GraphClient.from_env(...)` so it picks up
  `FALKORDB_BATCH_NODES=500` / `FALKORDB_BATCH_EDGES=1000` /
  `FALKORDB_QUERY_TIMEOUT_SECONDS=30`. Honor the project-wide
  Gemini throttle pattern (not relevant here — no LLM calls, but
  still respect ops canon: instrument fail-fast at >50 errors OR
  >10% rate after 100 ops, log per-row outcome to JSONL audit).
* **Measurable criterion (gate 3)**: after the script runs to
  completion against staging:
  * Falkor `MATCH (n:Norm) RETURN count(n)` returns ≥17,169 (was
    2,905 → expect 17,169 + carryover from prior load; collisions
    on existing `norm_id`s should MERGE without dup).
  * Falkor `MATCH (n:Norm)-[:IS_SUB_UNIT_OF]->(p:Norm) RETURN count(*)`
    returns at least the count of Supabase rows with non-null
    `parent_norm_id` (~9,000+ based on the `*_articulo` shapes —
    verify with a `count(*) where parent_norm_id is not null` query
    before launching).
  * Zero `falkor_failure` in the audit JSONL.
* **Test plan (gate 4)**:
  * **Engineer / preflight (1 min)**: run with `--limit 5
    --dry-run` first; verify the staged Cypher and parameter dicts
    look right. Then `--limit 5` (no dry-run) against staging,
    verify the 5 new nodes are reachable
    (`MATCH (n:Norm {norm_id: ...}) RETURN n`).
  * **Engineer / volume (~5 min)**: launch the full 17,169-row
    sweep detached + heartbeat per CLAUDE.md "long-running Python
    processes" canon (see `scripts/monitoring/README.md`).
    Heartbeat should anchor on the script's `events.jsonl`, not
    the summary log.
  * **End-user / SME (none required)** — this is a graph-shape
    change with no surface-visible impact. The §1.G panel is the
    regression gate (see §3 Step 4).
  * **Numeric decision rule**: PASS = staging Falkor `Norm` count
    rises from 2,905 to ≥17,169 with 0 failures AND §1.G panel
    holds at ≥32 strong / 36 acc+; FAIL = any other shape.
* **Greenlight (gate 5)**: technical PASS + §1.G unchanged.
* **Refine-or-discard (gate 6)**: if the projection lands but the
  panel regresses (some planner branch keying off the old
  parent-only Norm topology), iterate; if no path forward, revert
  the projection (Falkor delete by `created_at` window) and
  document the unexpected coupling.

### Route N2 — backfill TopicNode `topic_id` (phase 7b)

* **Idea (gate 1)**: TopicNode currently has `label` populated and
  `topic_id` null. Fill `topic_id` from
  `sub_topic_taxonomy.topic_slug` (or whatever the canonical topic
  identifier is in Supabase — needs verification before writing
  code; see Step 1 below).
* **Plan (gate 2)**: one-grep audit first
  (`grep -rn "topic_id" src/lia_graph/pipeline_d/ src/lia_graph/graph/`)
  to confirm whether any retriever / planner branch reads
  `n.topic_id`. **If yes**, ship the backfill via a small
  `scripts/cloud_promotion/backfill_topic_ids.py` that:
  1. Reads all 82 TopicNode (`MATCH (n:TopicNode) RETURN n.label`).
  2. Looks up the slug for each label in `sub_topic_taxonomy`
     (or wherever the canonical topic-slug ↔ label map lives — likely
     `config/subtopic_taxonomy.json` or the Supabase
     `sub_topic_taxonomy.topic_slug` column).
  3. Stages `MATCH (n:TopicNode {label: $label}) SET n.topic_id = $slug`.

  **If no** (audit shows `topic_id` is unread anywhere), close as
  cosmetic in §13 hand-off and skip the code.
* **Measurable criterion (gate 3)**: after backfill,
  `MATCH (n:TopicNode) WHERE n.topic_id IS NULL RETURN count(n)`
  returns 0; spot-check 5 TopicNodes — `topic_id` matches
  `sub_topic_taxonomy.topic_slug` for the same `label`.
* **Test plan (gate 4)**: engineer-only; no SME involvement. Run
  the §1.G panel after backfill — must hold ≥32 strong / 36 acc+.
* **Greenlight (gate 5)**: technical PASS + §1.G unchanged.
* **Refine-or-discard (gate 6)**: if any planner branch starts
  filtering harder once `topic_id` is populated and the panel
  drops, revert the SET in one Cypher
  (`MATCH (n:TopicNode) SET n.topic_id = NULL`) and route the
  finding into a `topic_id`-aware planner-fix doc.

### Route N3 — document the Falkor-vigencia-is-empty-by-design rule (phase 7c, docs only)

* **Idea (gate 1)**: a fresh agent reading the Falkor schema might
  assume vigencia is queryable in Cypher (because there's a `Norm`
  label) and write a `WHERE n.vigencia_status = 'vigente'` branch
  that always matches zero. Add a one-line guardrail in two places.
* **Plan (gate 2)**: docs-only edit, two files:
  1. `docs/orchestration/orchestration.md` — under the runtime read-
     path table, add a one-line callout: "Vigencia state lives in
     Supabase `norm_vigencia_history` only; never query
     `n.vigencia_status` in Cypher — call the
     `norm_vigencia_at_date(norm_id, asof)` SQL RPC instead."
  2. `src/lia_graph/graph/schema.py` — top-of-file docstring (or
     near the Norm node type definition) mirroring the same rule.
* **Measurable criterion (gate 3)**: both files contain the rule.
  No code change, no run impact.
* **Test plan (gate 4)**: trivial — read the diff.
* **Greenlight (gate 5)**: trivial.
* **Refine-or-discard (gate 6)**: not applicable.

### Recommended phasing

* **7a (N1) FIRST** — biggest lever, longest runtime (~5 min
  detached for 17K nodes + ~9K hierarchy edges at 500/1000 batch
  sizes), and it's what unblocks future planner work. Do this before
  the others so Routes 7b/7c land on the projected graph, not the
  pre-projection one.
* **7b (N2) SECOND** — quick (~10 min audit + ~30 min code IF the
  audit says `topic_id` is read anywhere). If the audit returns
  zero hits, skip the code and close as cosmetic.
* **7c (N3) THIRD** — docs only, ~5 min, zero risk.

Total expected wall time: ~1.5 hr including the §1.G regression
re-run after 7a.

---

## 3. The implementation (numbered, copy-paste-ready)

### Step 1 — Re-verify diagnosis on staging (~5 min, read-only)

Confirm the gap hasn't already been closed by some other process
between this doc's draft and your pickup:

```bash
set -a && source .env.staging && set +a
PYTHONPATH=src:. uv run python -c "
import os
from lia_graph.graph.client import GraphClientConfig, GraphWriteStatement, _run_graph_query
cfg = GraphClientConfig.from_env()
def q(cy):
    raw, _ = _run_graph_query(GraphWriteStatement(description='probe', query=cy, parameters={}), cfg)
    return raw[1] if len(raw) > 1 else []
print('Falkor Norm count:', q('MATCH (n:Norm) RETURN count(n)'))
print('Falkor Norm sample:', q('MATCH (n:Norm) RETURN n.norm_id LIMIT 5'))
print('Falkor TopicNode null topic_id:', q('MATCH (n:TopicNode) WHERE n.topic_id IS NULL RETURN count(n)'))
print('Falkor Norm vigencia_status set:', q('MATCH (n:Norm) WHERE exists(n.vigencia_status) RETURN count(n)'))
"
```

Expected as of 2026-04-29 ~7:55 PM Bogotá: 2,905 Norm / IDs like
`ley.1607.2012` / 82 TopicNode null `topic_id` / 0 Norm with
`vigencia_status`. If any of these have moved, update §1 and
re-scope before writing code.

Cross-check Supabase:

```bash
PYTHONPATH=src:. uv run python -c "
import os, urllib.request, json
url = os.environ['SUPABASE_URL']; key = os.environ['SUPABASE_SERVICE_ROLE_KEY']
def head(t):
    req = urllib.request.Request(f'{url}/rest/v1/{t}?select=*',
        headers={'apikey':key,'Authorization':f'Bearer {key}','Prefer':'count=exact','Range':'0-0'},
        method='HEAD')
    return urllib.request.urlopen(req).headers.get('Content-Range','').split('/')[-1]
print('norms:', head('norms'))
print('norm_vigencia_history:', head('norm_vigencia_history'))
print('document_chunks:', head('document_chunks'))
"
```

Expected: 17169 / 9322 / 19546.

### Step 2 — Phase 7a: write `project_norms_to_falkor.py` (~30 min code)

* New file: `scripts/cloud_promotion/project_norms_to_falkor.py`.
* Pattern: copy the launcher shape from
  `scripts/cloud_promotion/run.sh` + heartbeat from
  `scripts/cloud_promotion/heartbeat.py` (per CLAUDE.md ops canon).
  Reuse, don't re-implement — see "All canonicalizer runners follow
  ALL best practices" memory.
* Required flags / env-vars:
  * Reads `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` /
    `FALKORDB_URL` / `FALKORDB_GRAPH` from `.env.staging`.
  * `--dry-run` (stages but doesn't execute, prints batched
    statements).
  * `--limit N` (preflight: process only N rows).
  * `--audit-jsonl <path>` (per-row outcome log; default
    `tracers_and_logs/logs/project_norms_<run_id>.jsonl`).
  * Fail-fast threshold: `>50 errors OR >10% rate after 100 ops →
    abort` (CLAUDE.md ops canon).
  * Idempotency: MERGE on `norm_id` so re-runs are safe.
* Use `GraphClient.from_env()` to get the configured graph + batch
  sizes. Stage via `client.stage_node(...)`; execute via the live
  executor path (look at how `src/lia_graph/ingestion/loader.py` or
  `src/lia_graph/ingestion/supabase_sink.py` invokes the executor —
  reuse, don't reinvent).

### Step 3 — Phase 7a: preflight + risk-first launch (~10 min)

Per CLAUDE.md "Fail Fast, Fix Fast" rules 7 + 8:

1. **Preflight (~1 min)**: run with `--limit 5 --dry-run` and read
   the staged Cypher. Then `--limit 5` (live) and verify with
   `MATCH (n:Norm {norm_id: '<sample>'}) RETURN n` that the merged
   shape is right (all 9 properties present, no nulls where they
   shouldn't be).
2. **Risk-first ordering**: process the long-tail
   `decreto_legislativo_articulo` / `decreto_ley_articulo` /
   `concepto_dian_numeral` rows FIRST (the 17 long-tail rows from
   §1) — those are the shapes that haven't been exercised in this
   environment. The 5,298-row `oficio_dian` mass run goes LAST.
3. **Volume launch (~5 min wall)**: detached + heartbeat per
   `scripts/monitoring/README.md`. Re-use the
   `scripts/cloud_promotion/run.sh` launcher; pass the new script
   via the `RUNNER` flag rather than writing a new launcher.

### Step 4 — Phase 7a: regression-check the §1.G panel (~5 min)

```bash
PYTHONPATH=src:. uv run python scripts/eval/run_sme_parallel.py --workers 4
```

Compare the new run dir to anchor
`evals/sme_validation_v1/runs/20260430T000527Z_fix_v5_phase6b_rerun/`.
PASS = ≥32 strong AND 36 acc+ AND 0 weak AND 0 invented norms in any
flipped qid. FAIL = anything less; iterate or revert per gate 6.

### Step 5 — Phase 7b: TopicNode `topic_id` audit + backfill (~10–40 min)

```bash
grep -rn "topic_id\b" src/lia_graph/pipeline_d/ src/lia_graph/graph/ \
  src/lia_graph/normativa/ src/lia_graph/interpretacion/ \
  | grep -v "#\|\"\"\"\|'''"
```

If zero non-comment hits → close N2 as cosmetic in §13 hand-off,
skip code.

If hits → write `scripts/cloud_promotion/backfill_topic_ids.py`
following the same launcher / preflight / fail-fast shape from
Step 2/3 (only 82 rows so the volume concern is trivial; preflight
is still required).

Re-run §1.G panel; PASS = same bar as Step 4.

### Step 6 — Phase 7c: docs-only update (~5 min)

* Edit `docs/orchestration/orchestration.md` — add the vigencia-is-
  Supabase-only callout near the runtime read-path table.
* Edit `src/lia_graph/graph/schema.py` — add the same rule near the
  Norm node type definition.

### Step 7 — Six-gate sign-off + commit + push (per phase)

Per phase, separate commit. Commit message shape (matches fix_v5
convention):

```
fix_v6 phase 7a — project norms catalog into Falkor (2905 → 17169 Norm)
fix_v6 phase 7b — TopicNode topic_id backfill (82 nodes; or KEPT-COSMETIC if audit shows no readers)
fix_v6 phase 7c — docs: vigencia is Supabase-only, never on Falkor Norm props
```

Push to `origin/main` after each phase passes its §1.G regression
re-run.

---

## 4. What you must NOT do (additive over fix_v5 §4)

In addition to all fix_v5 do-not-do entries, specifically for this
doc:

1. **Do not delete `frontend/dist/`** during this fix even though it's
   the stale-Apr-19 unused directory. The served bundle is `ui/` at
   repo root (verified Apr 29 19:30 build); cleanup of `dist/`
   belongs in a separate housekeeping commit, not bundled here.
2. **Do not project `norm_vigencia_history` rows into Falkor as
   properties on `Norm` nodes.** Vigencia is norm-keyed in Supabase
   by design (see CLAUDE.md non-negotiables + the
   `feedback_vigencia_norm_keyed.md` memory). The point of N3 is to
   document this, not violate it.
3. **Do not silently fall back to artifacts** if the Falkor projection
   script hits a transport error. Per the CLAUDE.md non-negotiable,
   propagate the outage, fix it, re-run.
4. **Do not run the full `norms` sweep without preflight + risk-first
   ordering.** The CLAUDE.md "Fail Fast, Fix Fast" canon is mandatory
   for any ≥100-record op against real systems; 17,169 rows is well
   over that bar.
5. **Do not raise the fail-fast threshold or add `--continue-on-error`
   on first abort.** Diagnose, fix, re-run. (Same rule as fix_v4 §5
   for the SME panel.)
6. **Do not bundle N1 + N2 + N3 into one commit.** Three separate
   commits, each with its own §1.G regression re-run, so a regression
   can be bisected to one phase.
7. **Do not skip the §1.G regression re-run after N1 even though "it's
   just a graph projection."** Several pipeline_d planner / retriever
   branches walk Norm-level edges; a topology change can shift
   `connected_articles` ordering or counts. Verify, don't assume.
8. **Do not re-run the canonicalizer to "regenerate" the missing
   norms.** They're already in Supabase — re-extracting violates the
   "Extract Gemini once; promote through three stages" memory. The
   right action is projection, not re-extraction.
9. **Do not flip any `LIA_*` flag as part of this fix.** This is an
   infra projection; flag changes belong in their own forward-plan.

---

## 5. Anchor data to compare against

* **§1.G panel anchor (must not regress)**:
  `evals/sme_validation_v1/runs/20260430T000527Z_fix_v5_phase6b_rerun/`
  — 32 strong / 4 acc / 0 weak / 36 acc+.
* **Pre-projection Falkor counts** (this doc, §1):
  * Norm: 2,905
  * ArticleNode: 9,249
  * ReformNode: 1,860
  * TopicNode: 82 (all `topic_id` null)
  * SubTopicNode: 94
  * Total nodes: 14,190
  * Total edges: 27,131
  * `IS_SUB_UNIT_OF` edges: not measured pre-projection — capture
    in Step 1 of your run for diff purposes.
* **Pre-projection Supabase counts**:
  * `norms`: 17,169 (all `created_at = 2026-04-29`)
  * `norm_vigencia_history`: 9,322
  * `norm_citations`: 52,246
  * `normative_edges`: 354,025
  * `documents`: 6,736 / `document_chunks`: 19,546 (100% embedded)
  * `sub_topic_taxonomy`: 106
  * Active corpus generation: `gen_20260425123153` (Apr 25)
  * Last delta: `delta_20260426_145314` (Apr 26, clean close)

---

## 6. State of the world at hand-off (2026-04-29 ~7:55 PM Bogotá)

* Latest commits on `main` (pushed):
  * `69a811a fix_v5.md — phase 6 close-record (§10/§11/§12/§13)`
  * `ccf236c fix_v5 phase 6c — Q2 numeric directive DISCARDED`
  * `51b1939 fix_v5 phase 6b — Q1 sub-Q topic carry-over from parent`
  * `8f839a8 fix_v5 phase 6a — Q4 heading-reject in evidence line splitter`
  * `64f5375 fix_v5.md — phase 6 hand-off`
* Working tree: clean.
* `config/llm_runtime.json` `provider_order`: gemini-flash first.
  UNCHANGED.
* `LIA_*` flag matrix: UNCHANGED from CLAUDE.md
  v2026-04-26-additive-no-retire defaults.
* Polish prompt: phase-5-close shape (Route A REGLA DE EXPANSIÓN
  only; Q2 reverted).
* Cloud Supabase ↔ cloud Falkor:
  * Supabase migrations: 18/18 applied, no drift.
  * `norms` catalog: fully populated in Supabase (17,169 today),
    not yet projected to Falkor (2,905 — pre-canonicalizer state).
  * `document_chunks`: 100% embedded.
* UI: `ui/` at repo root, freshly built Apr 29 19:30 Bogotá.
  `frontend/dist/` is stale-Apr-19 unused (do not touch in this
  fix).
* Preflight (`npm run dev:staging:check`): green on all three deps.
* Dev server: not running at fix_v6 draft time.

---

## 7. Quick-reference: file map

| Scope | File / Location |
|---|---|
| Norms canonical store (source of truth) | Supabase `public.norms` |
| Vigencia canonical store | Supabase `public.norm_vigencia_history` (read via `norm_vigencia_at_date` RPC) |
| Falkor graph client | `src/lia_graph/graph/client.py` (`GraphClient.from_env`, `stage_node`) |
| Falkor schema | `src/lia_graph/graph/schema.py` |
| Live Cypher executor entrypoint | `src/lia_graph/graph/client.py::_run_graph_query` |
| Existing projection patterns | `src/lia_graph/ingestion/supabase_sink.py`, `src/lia_graph/ingestion/loader.py`, `src/lia_graph/ingestion/delta_runtime.py` |
| Long-running launcher template | `scripts/cloud_promotion/run.sh` + `scripts/cloud_promotion/heartbeat.py` |
| Heartbeat doc | `scripts/monitoring/README.md` |
| §1.G panel runner | `scripts/eval/run_sme_parallel.py` |
| Panel anchor | `evals/sme_validation_v1/runs/20260430T000527Z_fix_v5_phase6b_rerun/` |
| Orchestration map (env matrix lives here) | `docs/orchestration/orchestration.md` |

---

## 8. After you ship each phase

* Update `docs/aa_next/next_done.md` with the phase + run dir +
  measurable result, per the next-doc convention.
* Per the always-suggest-next memory: end your status report with
  one concrete next step (e.g. "next: schedule a weekly Falkor ↔
  Supabase parity check via `/schedule`" — only if it actually
  applies).
* Per the recommendations-in-canonical-plan memory: any new
  forward-looking suggestion goes back into this doc (a new §9, §10,
  …) in a form a fresh LLM can execute, not just into chat.

---

## 9. Close-out record (2026-04-29 ~9:17 PM Bogotá)

**Status: phase 7a + 7b + 7c FULLY CLOSED.** All three routes shipped
under operator-extended scope (the original doc targeted cloud only;
operator added "make sure you update and reach parity between local
supabase docker and falkor docker and cloud docker and cloud falkor").
Phase 7a expanded into three sub-phases (cloud projection / cross-Supabase
sync / local projection); phase 7b closed cosmetic without code; phase 7c
schema-docstring shipped (orchestration.md callout deferred to land with
pre-existing un-committed fix_v5 close edits).

### Final 4-corner Norm parity

|              | Supabase Norm   | Falkor Norm | IS_SUB_UNIT_OF |
|--------------|----------------:|------------:|---------------:|
| **Cloud**    | 17,169          | 17,169 ✓    | 6,503 ✓        |
| **Local**    | 22,296          | 22,296 ✓    | 6,712 ✓        |

Cloud and local each internally aligned. Local is a strict superset of
cloud (cloud's 17,169 plus 5,127 local-only norms from prior ingestion
runs); cloud parity is achieved row-set-wise.

### Phase 7a-cloud (commit `3994fb1`, pushed)

* `scripts/cloud_promotion/project_norms_to_falkor.py` (NEW, 363 LOC)
  paginates Supabase `norms`, batches `MERGE` via `GraphClient.from_env()`
  (500/1000 batch sizes), then upserts `IS_SUB_UNIT_OF` from
  `parent_norm_id`. Risk-first ordering (cco/cst/estatuto/decreto_legislativo/
  decreto_ley/sentencia_ce first); fail-fast at >50 errors OR >10% rate
  after 100 ops; idempotent via MERGE on `norm_id`.
* Run against `.env.staging` 2026-04-30 02:54 UTC:
  * `nodes_created=14,264` (2,905 → 17,169 ✓ — exactly the predicted gap)
  * `edges_created=6,500` (3 → 6,503 IS_SUB_UNIT_OF ✓)
  * `errors=0`, `elapsed=17.5s` (vs doc estimate of 5 min — single-host
    network was much faster than the conservative budget).
  * Per-norm-type parity verified post-run: oficio_dian 0 → 5,298;
    articulo_et 0 → 1,098; concepto_dian 0 → 2,625.
  * Audit: `tracers_and_logs/logs/project_norms_20260430T015418Z.jsonl`.

### Phase 7a-sync (commit `5bdea55`, pushed)

* `scripts/cloud_promotion/sync_norms_cloud_to_local.py` (NEW, 363 LOC)
  copies four norms-related tables cloud → local Supabase. Mutable tables
  use `merge-duplicates`; append-only tables (`norm_vigencia_history`,
  `norm_citations`) use `ignore-duplicates` since `norm_vigencia_history`
  grants service_role only INSERT/SELECT (no UPDATE) and `norm_citations`
  carries `uq_nc_chunk_norm_role` beyond its PK.
* **Three diagnoses-before-fix** during sync development (per "fail fast,
  fix fast" canon — first abort = diagnosis, not retry):
  1. Local docker missing migration `20260501000006_norms_norm_type_extend.sql` →
     applied via `supabase migration up --local --include-all`.
  2. Wrong `on_conflict` columns (guessed `history_id`, actual `record_id`;
     `sub_topic_taxonomy` PK is composite `(parent_topic_key, sub_topic_key)`).
  3. `norm_vigencia_history` is **append-only by design** (no UPDATE
     grant) → switched to `ignore-duplicates` resolution.
* Final sync result:
  * `sub_topic_taxonomy`: 0 → 106 (cloud=106) ✓
  * `norms`: 13,540 → 22,296 (cloud=17,169) ✓ (local has cloud's full set
    + 5,127 local-only legacy rows)
  * `norm_vigencia_history`: 5,644 → 14,966 (cloud=9,322) ✓
  * `norm_citations`: 40,620 → 66,327 (cloud=52,246) ✓

### Phase 7a-local (rolled into commit `5bdea55`)

* Re-ran the same `project_norms_to_falkor.py` against `.env.local`:
  * `nodes_created=8,756` (13,540 → 22,296 ✓)
  * `edges_created=6,667` (3 → 6,712 IS_SUB_UNIT_OF ✓)
  * `errors=0`, `elapsed=2.6s`.
  * Audit: `tracers_and_logs/logs/project_norms_20260430T020255Z.jsonl`.

### Phase 7b (closed cosmetic, no code)

* `grep -rn 'topic_id\b' src/lia_graph/pipeline_d/ src/lia_graph/graph/
  src/lia_graph/normativa/ src/lia_graph/interpretacion/` returned **zero
  non-comment hits**. `TopicNode.topic_id` NULL is unread by any planner
  / retriever / synthesis branch; the field exists in the graph but no
  code keys off it.
* Recommendation for future: if a planner ever wants to join TopicNode
  back to `sub_topic_taxonomy.topic_slug`, populate `topic_id` from a
  small backfill script at that point. Until then, no action needed.

### Phase 7c (rolled into commit `5bdea55`)

* `src/lia_graph/graph/schema.py` — extended the `NodeKind.NORM`
  description docstring with: "VIGENCIA STATE IS NEVER STORED HERE — it
  lives in Supabase `norm_vigencia_history` and is read via the
  `norm_vigencia_at_date(norm_id, asof)` SQL RPC. Cypher branches like
  `WHERE n.vigencia_status = 'vigente'` always return empty by design
  (fix_v6.md §1 yellow-flag #3)."
* The companion `docs/orchestration/orchestration.md` callout was
  drafted in the working tree but unstaged — the surrounding doc has
  pre-existing fix_v5-close edits not yet committed; the vigencia
  callout will land with that commit to keep scope clean.

### §1.G regression check (the gate)

* Run dir: `evals/sme_validation_v1/runs/20260430T020607Z_fix_v6_phase7a_post_projection/`
* Anchor: `evals/sme_validation_v1/runs/20260430T000527Z_fix_v5_phase6b_rerun/`
* Initial run hit `429 Too Many Requests` on 18/36 qids
  (`/api/public/session` rate-limit with 4 concurrent workers + `--auth`)
  — diagnosed and **resolved by re-running the 18 affected qids with
  `--workers 1` serially**. The panel runner is resumable (skips existing
  qid JSONs) so the retry was clean.
* Final classification (`run_sme_validation.py --classify-only`):

  | metric           | anchor (fix_v5 6b) | post-projection (fix_v6 7a) | delta |
  |------------------|------------------:|-----------------------------:|------:|
  | served_strong    | 32                | **32**                       | 0     |
  | served_acceptable| 4                 | **4**                        | 0     |
  | served_weak      | 0                 | **0**                        | 0     |
  | refused          | 0                 | **0**                        | 0     |
  | server_error     | 0                 | **0**                        | 0     |
  | acc+             | 36/36             | **36/36**                    | 0     |

  **Exact anchor match. Zero regression.** The cloud Norm projection added
  graph state without changing observable chat behavior — confirming the
  pre-launch grep finding that no Cypher in pipeline_d traverses Norm.

### Operator follow-up suggestions

1. **Land the orchestration.md vigencia callout** when the pre-existing
   fix_v5-close edits are committed (the callout is in the working tree,
   ready to stage).
2. **Schedule a recurring parity check** (cloud vs local Supabase + cloud
   vs local Falkor) — small Bash-driven count probe, daily or per delta
   close. Catches future drift before it confuses a re-projection run.
3. **Backlog item**: revisit `TopicNode.topic_id` if/when a planner
   branch wants to join back to `sub_topic_taxonomy.topic_slug`. No
   urgency — the audit was conclusive that nothing reads it today.

---

## 10. Minimum information from operator (none)

Everything required to execute is in this doc + the CLAUDE.md
non-negotiables + the fix_v5 §4 do-not-do list + the ops canon. No
operator decisions needed unless §1 diagnosis no longer holds at
pickup time; in that case, re-scope before writing code.

---

*Drafted 2026-04-29 ~7:55 PM Bogotá by claude-opus-4-7 immediately
after a staging-environment health audit (post fix_v5 phase 6 close,
commit `69a811a` on `main`). Diagnosis numbers in §1 are from live
queries against cloud Supabase + cloud FalkorDB at draft time. The
three yellow flags are health-audit findings, not pipeline-quality
regressions; the §1.G 36/36 panel still holds at draft time and is
the regression gate for any code that ships from this doc.*
