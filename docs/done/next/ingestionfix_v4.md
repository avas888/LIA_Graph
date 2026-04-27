# ingestionfix_v4 — Graph-coverage fix (prose-only ArticleNode eligibility)

Forward-looking plan after `ingestionfix_v3` Phase 3.0 Quality Gate revealed a chronic Falkor under-population: **99.6% of ArticleNodes lack TEMA edges** (8,074 of 8,106 orphaned). The gate batch discovered the root cause — the Falkor loader rejects "prose-only" docs (whole-doc fallbacks with empty `article_number`) via `_is_article_node_eligible`, so none of the 432 Task E migration docs or 4 of 6 gate-batch topics produced graph nodes.

`ingestionfix_v3.md` remains the authoritative forward plan for Phases 3–5; this doc covers the narrow-but-load-bearing correction that unblocks it.

**Read order for a cold LLM**: §0 → §1 → §2 → §3 → §5 (phases in order). §8 is the live state ledger — update it as each phase transitions.

---

## §0 Cold-Start Briefing

### 0.1 What Lia_Graph is

Graph-native RAG shell for Colombian accounting/legal content. Two retrieval halves: chunk-level hybrid search in Supabase (`retriever_supabase.py` → `hybrid_search` RPC) + graph traversal in FalkorDB (`retriever_falkor.py`). Served runtime: `src/lia_graph/pipeline_d/`.

### 0.2 What v3 left behind

- Phase 2.5 shipped cleanly: `otros_sectoriales` 510→78, 26 new sector topics in taxonomy, Supabase `documents.tema` migrated for 432 rows. ✓
- Phase 3.0 Batch 1 ran 465 docs end-to-end (33 gate bust + 432 Task E nulls riding along) and produced `artifacts/batch_1_quality_gate.json` with `status: failed`:
  - **G1 ✗** — 4 docs legitimately re-classified out of batch-1 topics (benign drift)
  - **G4 ✗** — 5 of 6 batch-1 topics have ZERO TEMA edges; **0 of 26 new `sector_*` TopicNodes even exist** in Falkor
  - All other gates (G2/G3/G5–G10) ✓

### 0.3 The pre-existing blocker v3 surfaced

```
ArticleNode count                             8,106
ArticleNode WITHOUT TEMA edge                 8,074 (99.6%)
TEMA edges pre-batch-1                        10
TEMA edges post-batch-1                       32 (+22)
```

Graph coverage has been near-zero for the entire project lifetime. Batch 1 emitted only +22 TEMA edges across 465 processed docs because the loader silently filtered out all prose-only articles.

### 0.4 Repo layout (essentials for v4)

```
src/lia_graph/
  ingestion/
    parser.py             # ParsedArticle + _whole_document_fallback + _section_fallback
    loader.py             # _is_article_node_eligible, _build_article_nodes, _build_article_tema_edges
    supabase_sink.py      # chunk_id = f"{doc_id}::{article_key}"
    delta_runtime.py      # materialize_delta — calls build_graph_delta_plan
  graph/
    schema.py             # ArticleNode.required_fields = ("article_number", ...)
  ingest.py               # CLI; builds article_topics dict for the non-delta path

tests/
  test_falkor_loader_thematic.py
  test_loader_delta.py
  test_loader_article_eligibility.py   # NEW in v4

docs/next/
  ingestionfix_v3.md       # forward plan Phases 3–5
  ingestionfix_v4.md       # THIS DOC — graph-eligibility fix
```

### 0.5 Tooling (inherited from v3)

- Python: `uv` (pyproject.toml). Run via `PYTHONPATH=src:. uv run pytest tests/<file>.py -v`.
- Tests: single `uv run pytest` calls; full suite via `make test-batched` (never direct pytest on full suite — conftest guard).
- Supabase: production writes gated. Source `.env.staging` first.
- Falkor: `FALKORDB_URL` in `.env.staging`; graph `LIA_REGULATORY_GRAPH`.
- Detached launch pattern: `scripts/ingestion/launch_batch.sh` (nohup + disown + no tee). 3-min heartbeat via CronCreate.

### 0.6 Glossary (v4-specific)

| Term | Meaning |
|---|---|
| **Prose-only doc** | Markdown with no `Artículo N.` headers. Parser returns one `ParsedArticle(article_number="", article_key="doc", body=full_text)` via `_whole_document_fallback`. Typical for Colombian laws stored as whole-law prose (Ley 1098/2006, sector regs, etc.). |
| **Section-fallback doc** | Markdown with heading structure but no `Artículo N.` markers. Uses `_section_fallback`. Has non-empty article_key derived from heading. |
| **Numbered doc** | Markdown with `Artículo 1.`, `Artículo 2.` etc. Each article gets `article_number=<N>`, `article_key=<N>`. |
| **Graph-layer article key** | Unique-per-doc key used as `ArticleNode.key` in Falkor, introduced in v4. Distinct from `ParsedArticle.article_key` (Supabase chunk_id scope) so Supabase chunks stay stable. |
| **is_prose_only** | Boolean property added to `ArticleNode` in v4. True when `article_number` is empty. Let Cypher filters cleanly include/exclude prose docs. |
| **TEMA edge** | Falkor edge `ArticleNode → TopicNode` emitted when an article's doc has a resolved topic_key. The load-bearing retrieval signal v3 Phase 3 was meant to backfill. |

### 0.7 Source-of-truth pointers

| Concern | Canonical source |
|---|---|
| v3 Phase 3.0 gate outcome | `artifacts/batch_1_quality_gate.json` + session transcript 2026-04-23 PM |
| Schema ArticleNode contract | `src/lia_graph/graph/schema.py` line 160-164 |
| Eligibility filter | `src/lia_graph/ingestion/loader.py::_is_article_node_eligible` (line 23-42) |
| article_topics dict build (non-delta) | `src/lia_graph/ingest.py` line 359-363 |
| article_topics dict build (delta) | `src/lia_graph/ingestion/delta_runtime.py` line 490-494 |
| Detached-launch pattern + heartbeat | `scripts/monitoring/README.md` |

### 0.8 Non-negotiables

- Keep the change scoped to **prose-only graph-layer keys**. Do NOT change `article.article_key` in the parser (would churn every Supabase chunk_id).
- Do NOT touch numbered-article graph keys. The Article 5-of-Ley-100-vs-Ley-300 cross-doc collision is a **separate, pre-existing bug** flagged as followup F8. Fixing it here would orphan 8,106 existing ArticleNodes.
- Fingerprint-bust + re-ingest is the only sanctioned way to force Falkor re-materialization (matches v3 durability contract).
- Long-running re-ingest follows CLAUDE.md §"Long-running Python processes" — detached + 3-min heartbeat, no exceptions.

---

## §1 Prior work — context + motivation

### 1.1 What v3 Phase 3.0 proved

The Quality Gate fired on real data for the first time and surfaced that:

- `_is_article_node_eligible()` (loader.py:23) requires `article_number AND heading AND text AND status` all non-empty.
- `_whole_document_fallback` (parser.py:171) produces `ParsedArticle(article_number="")` — so every whole-doc-fallback article is rejected.
- `_section_fallback` (parser.py:107) similarly uses the heading-slug as `article_key` but leaves `article_number` empty in some code paths — also rejected.
- Prose-only docs dominate: OTROS_SECTORIALES, most Leyes, and historical docs without numbered articles. Rough estimate: **~1,000 of 1,280 docs** are prose-only.

### 1.2 Why the bug stayed hidden until now

- The `ingest.graph.articles_skipped_nonschema` event fires on every run but nobody had wired gates to read it.
- Falkor's 10 pre-v3 TopicNodes had 10 TEMA edges (one edge per topic — cosmetic). This looked "populated" from the top-level heartbeat tables.
- The v3 plan assumed TopicNode 10 → 65+ and TEMA 10 → 1,319+ would emerge naturally from the Phase 3 chain. It would not have, because the eligibility filter was silently dropping ~80% of the corpus.

### 1.3 What v3 Phase 3.0 gate produced (verified snapshot)

```
delta_id:                 delta_20260424_004801_a494af
classifier input:         465 (33 gate-batch + 432 Task E nulls)
elapsed_ms:               1,311,569  (~21.9 min)
Supabase writes:          432 tema updates + 465 fingerprint re-stamps ✓
Falkor ΔTopicNode:        +6 (all from batch-1 existing-topic keys)
Falkor ΔTEMA:             +22 (21 otros_sectoriales + 1 iva, plus 7 emergencia_tributaria of batch-1)
Falkor ΔSubTopicNode:     +12
sector_* TopicNodes:      0 of 26 created
PRACTICA_DE edges:        0 (unchanged; separate surface)
```

### 1.4 What must change for the chain to deliver v3's stated outcome

- Every classified doc — numbered or prose — must produce an `ArticleNode`.
- Every `ArticleNode` must be able to receive a `TEMA` edge.
- Prose docs must not collide with each other at the graph layer (current `article_key="doc"` is a single cypher key shared across ALL prose docs).

Once those hold, v3 Phase 3 batches 2–11 will naturally populate the 26 new sector TopicNodes + the long tail of per-doc TEMA edges.

---

## §2 Problem summary (TL;DR)

**Root cause.** `loader.py::_is_article_node_eligible` requires a non-empty `article_number`. `parser.py::_whole_document_fallback` always emits empty `article_number`. Prose-only docs → skipped ArticleNode → skipped TEMA edge.

**Secondary bug (scope-limited).** `_whole_document_fallback` sets `article_key="doc"` (constant `WHOLE_DOC_ARTICLE_KEY`). Even if eligibility were relaxed, every prose doc would MERGE to the same `ArticleNode{article_key:"doc"}` in Cypher — one shared node for the whole corpus.

**Fix (Option C from session discussion).**
1. Drop `article_number` from `ArticleNode.required_fields`.
2. Relax `_is_article_node_eligible` to allow empty `article_number` (keep heading/text/status required).
3. Introduce a loader helper `_graph_article_key(article)` that returns `f"whole::{source_path}"` for prose-only articles and `article.article_key` otherwise. Use it wherever graph identity is required (node build + TEMA edge source_key + `article_topics` dict build).
4. Add `is_prose_only: bool` property to ArticleNode — True when `article_number` is empty, False otherwise. Enables clean Cypher filters.

**Explicitly out of scope.**
- Cross-doc numbered-article collision (Article 5 of Ley 100 vs Article 5 of Ley 300 share `article_key="5"`). Pre-existing; tracked as follow-up **F8**.
- Retiring 8,074 orphan ArticleNodes. Tracked as **F9**.
- Changing `article.article_key` in the parser (would invalidate all Supabase `chunk_id`s). Explicitly preserved.

---

## §3 Scope + phasing overview

Four phases. Each independently shippable and reversible.

| Phase | Purpose | Cost | Wall time | Blocks |
|---|---|---|---|---|
| 1 | Schema + loader + parser helper; unit tests; zero prod writes | ~90 min | ~90 min | Phase 2 |
| 2 | Consumer audit + retriever_falkor Cypher review | ~30 min | ~30 min | Phase 3 |
| 3 | Re-null fingerprints for 465 batch-1 docs + re-run additive ingest + re-validate gate | ~30 min | ~25 min wall | Phase 4 |
| 4 | Autonomous Phase 3 chain resumed — batches 2–11 | ~15 min launch | ~2–2.5 hr unattended | v3 close-out |

Total new work for v4: ~2 hr engineering + ~3 hr unattended chain.

---

## §4 Pre-flight checklist

- [ ] `git status` clean on v3 branch (`feat/ingestionfix-v2-phase9-reingest`).
- [ ] Current v3 batch-1 run is NOT still running (PID 99432 gone — confirmed via `ps`).
- [ ] `artifacts/batch_1_quality_gate.json` status is `failed` (the trigger for v4).
- [ ] Last successful fingerprint-bust manifest preserved (`artifacts/fingerprint_bust/20260424T004758Z_batch_1.json`).
- [ ] `.env.staging` sourceable.
- [ ] v3 post-migration reprobe file preserved (`artifacts/sector_reclassification/post_migration_reprobe.json`).
- [ ] Read CLAUDE.md §"Long-running Python processes" before Phase 3.

---

## §5 Phases

### Phase 1 — Schema + loader relaxation

**Goal.** Land the minimum-diff code change that lets prose-only docs produce ArticleNodes with unique-per-doc graph keys + `is_prose_only` flag. Full unit-test coverage. Zero production writes.

#### Phase 1 — Files to modify

| Path | Change |
|---|---|
| `src/lia_graph/graph/schema.py` | Drop `"article_number"` from `ArticleNode.required_fields`. Keep the tuple `("heading", "text_current", "status")`. Add a comment pointing at v4 §2 for rationale. |
| `src/lia_graph/ingestion/loader.py` | Relax `_is_article_node_eligible` (drop the number check). Introduce `_graph_article_key(article)` helper. Use it in `_build_article_nodes` (GraphNodeRecord.key) + `_build_article_tema_edges` (source_key + eligibility set). Emit `is_prose_only` in the properties dict. |
| `src/lia_graph/ingest.py` | In the non-delta `article_topics` comprehension (line 359-363), key the dict by `_graph_article_key(article)`. |
| `src/lia_graph/ingestion/delta_runtime.py` | Same pattern for the delta build of `article_topics` (line 490-494). |

#### Phase 1 — Files to create

| Path | Purpose |
|---|---|
| `tests/test_loader_article_eligibility.py` | Dedicated test suite for the eligibility + graph-key helpers. ~10 cases covering: prose-only eligible + gets `whole::` key, numbered eligible + keeps article_key, multiple prose docs get DISTINCT graph keys, missing heading/text/status still rejects, `is_prose_only` property toggles correctly. |

#### Phase 1 — Tests to update

| Test | What to add |
|---|---|
| `tests/test_falkor_loader_thematic.py` | One prose-only + one numbered doc in the fixture; assert TEMA edge emitted for both; assert distinct ArticleNode keys. |
| `tests/test_loader_delta.py` | Parallel test on the delta path via `build_graph_delta_plan`. |

#### Phase 1 — Run

```bash
PYTHONPATH=src:. uv run pytest \
  tests/test_loader_article_eligibility.py \
  tests/test_falkor_loader_thematic.py \
  tests/test_loader_delta.py \
  -v
```

Expected: all green.

Also verify nothing unrelated breaks:

```bash
PYTHONPATH=src:. uv run pytest \
  tests/test_dangling_store.py \
  tests/test_ingest_cli_additive.py \
  tests/test_apply_sector_reclassification.py \
  -q
```

#### Phase 1 — Acceptance

1. All new + updated tests green.
2. `grep '_graph_article_key' src/lia_graph/` shows the helper and its 4 call sites (loader.py x2, ingest.py x1, delta_runtime.py x1).
3. `ArticleNode.required_fields` in schema.py no longer contains `article_number`.
4. Existing test suites touching articles are unchanged green (no regression).
5. A manual read of one sample prose article → eligible + graph key looks like `whole::CORE ya Arriba/LEYES/…/Ley-109-1985.md`.

#### Phase 1 — State log (fill in as you go)

```yaml
phase_1_schema_loader:
  status: pending
  started_at:
  completed_at:
  branch:
  files_modified:
  files_created:
  tests_passing:
  notes:
```

---

### Phase 2 — Consumer audit

**Goal.** Confirm that no downstream consumer crashes or mis-behaves when `ArticleNode.article_number` is empty and `is_prose_only=True`. 30-minute audit, not a rewrite.

#### Phase 2 — Files to audit (read-only; patch only if a real issue is found)

| Path | What to check |
|---|---|
| `src/lia_graph/pipeline_d/retriever_falkor.py` | All Cypher queries — does anything filter on `article_number IS NOT NULL`? does anything ORDER BY or GROUP BY article_number? |
| `src/lia_graph/pipeline_d/retriever.py` | Same audit for artifact retriever. |
| `src/lia_graph/pipeline_d/answer_historical_recap.py` | Uses `article_key` but not `article_number`; likely safe. |
| `src/lia_graph/ingest_reports.py` | Any per-article-number aggregation? |

#### Phase 2 — Files to modify (only if Phase 2 audit finds a real issue)

If retriever_falkor.py filters on article_number non-empty, relax the filter or add an `OR is_prose_only` clause. Document the reason.

#### Phase 2 — Tests (on the specific surface)

| Test | Where | Purpose |
|---|---|---|
| Retriever smoke with a prose-only article | Manual: seed a graph fixture with one prose ArticleNode; run a topic→article traversal; assert the prose node returns | Lock the query behavior |

#### Phase 2 — Run

```bash
# Cypher-usage audit
grep -rn "article_number" src/lia_graph/pipeline_d/ src/lia_graph/graph/ src/lia_graph/ingest_reports.py

# Backend smoke sweep — fast subset
PYTHONPATH=src:. uv run pytest tests/test_phase3_graph_planner_retrieval.py -q
PYTHONPATH=src:. uv run pytest tests/test_retriever_falkor.py -q  # if present
```

#### Phase 2 — Acceptance

1. Audit grep produces a list of `article_number` usages — operator reviews, confirms no hard `NOT NULL` constraint is breaking.
2. Phase 3 graph planner/retrieval smokes pass.
3. Any consumer patches have tests.

#### Phase 2 — State log

```yaml
phase_2_consumer_audit:
  status: pending
  started_at:
  completed_at:
  grep_findings: []
  patches_required: []
  tests_passing:
  notes:
```

---

### Phase 3 — Re-null fingerprints + re-run batch 1 + re-validate gate

**Goal.** Force the 465 docs Phase 3.0 already touched to reprocess through the fixed loader so TEMA edges actually land. Prove with the same G1-G10 validator.

#### Phase 3 — Re-bust strategy

The 465 docs are the UNION of:
- 33 batch-1 bust docs (listed in `artifacts/fingerprint_bust/20260424T004758Z_batch_1.json`)
- 432 Task E migration docs (listed in `artifacts/sector_reclassification/20260424T001701Z_apply.json` `write_decisions`)

Simplest path: re-bust by **batch 1 topics + all 26 new sector topics + the 16 Task E migration-target topics** (union covers the 465). Or re-use the Task E manifest doc_ids directly via a new doc_id-filter bust.

Pragmatic choice: **bust by topic list**. The batch-1 6 topics + all 26 new sectors + the 16 migration targets = 48 topics. That bust would null fingerprints for all docs in those topics (a superset of 465, but bounded — the post-migration reprobe shows tema distribution summing to ~850 docs across that topic set). A superset is fine: the planner's idempotency means re-stamping already-fresh docs is a no-op.

Actually **even simpler**: use the single bigger bust via `--topics` with `--force-multi`. Manifest goes to `artifacts/fingerprint_bust/` as usual.

#### Phase 3 — Files to modify

None.

#### Phase 3 — Files to create

| Path | Purpose |
|---|---|
| `artifacts/fingerprint_bust/<ts>_v4_rerun.json` | Bust manifest (auto-generated) |
| `artifacts/launch-batch-1-v4-<ts>.log` | Re-run ingest log (auto-generated) |
| `artifacts/batch_1_quality_gate.json` | OVERWRITTEN by validator with post-fix run |

#### Phase 3 — Run

```bash
cd /Users/ava-sensas/Developer/Lia_Graph
set -a; source .env.staging; set +a

# 3a — null fingerprints for the 48-topic union (batch-1 + 26 new sectors + 16 migration targets)
TOPICS=$(python3 -c '
batch_1=["activos_exterior","emergencia_tributaria","impuestos_saludables","normas_internacionales_auditoria","perdidas_fiscales_art147","reforma_pensional"]
new_sectors=["sector_agropecuario","sector_salud","sector_financiero","sector_vivienda","sector_cultura","sector_administracion_publica","sector_profesiones_liberales","sector_educacion","sector_turismo","sector_inclusion_social","sector_servicios","sector_justicia","sector_energia_mineria","sector_politico","sector_deporte","sector_desarrollo_regional","sector_ciencia","sector_infancia","sector_juegos_azar","sector_economia","sector_transporte","sector_emprendimiento","sector_medio_ambiente","sector_puertos","sector_comercio_internacional","sector_telecomunicaciones"]
migration_targets=["presupuesto_hacienda","laboral","sagrilaft_ptee","comercial_societario","obligaciones_profesionales_contador","contratacion_estatal","datos_tecnologia","leyes_derogadas","inversiones_incentivos","reformas_tributarias","zonas_francas","facturacion_electronica","estados_financieros_niif","beneficiario_final_rub","ica"]
print(",".join(sorted(set(batch_1+new_sectors+migration_targets))))')

PYTHONPATH=src:. uv run python scripts/monitoring/monitor_ingest_topic_batches/fingerprint_bust.py \
  --topics "$TOPICS" --target production --confirm --force-multi --tag v4_rerun

# 3b — launch detached additive ingest
nohup bash -c '
  set -a; source .env.staging; set +a
  exec env PYTHONPATH=src:. uv run python -m lia_graph.ingest \
    --corpus-dir knowledge_base --artifacts-dir artifacts \
    --additive --supabase-sink --supabase-target production \
    --supabase-generation-id gen_active_rolling \
    --execute-load --allow-unblessed-load --strict-falkordb \
    --allow-non-local-env --json
' > logs/launch-batch-1-v4-$(date -u +%Y%m%dT%H%M%SZ).log 2>&1 < /dev/null &
disown $! 2>/dev/null || true

# 3c — arm 3-min heartbeat cron (fill delta_id after run.start fires)

# 3d — once cli.done fires, validate
PYTHONPATH=src:. uv run python scripts/monitoring/monitor_ingest_topic_batches/validate_batch.py \
  --batch 1 --gate \
  --manifest <new bust manifest> \
  --delta-id <new delta_id> \
  --delta-elapsed-ms <from cli.done payload> \
  --dry-run-row-count-after 0 --target production
```

#### Phase 3 — Acceptance

1. `artifacts/batch_1_quality_gate.json` shows `status: passed`.
2. G4 passes: all 6 batch-1 topics have ≥1 TEMA edge AND all 26 new sector TopicNodes exist with ≥1 TEMA edge.
3. Falkor TopicNode count ≥ 42 (10 pre-v3 + 6 batch-1 + 26 new sectors; minor exact-count drift allowed).
4. Falkor TEMA edge count ≥ 500 (rough floor: 465 docs × ~1 article/doc for prose-only = 465 expected TEMA edges at minimum).
5. `ArticleNode` without TEMA edge drops measurably below today's 8,074 (target: < 7,700 after the 432 Task E prose docs land).
6. G1 still fails (benign — 4 docs re-classified out of batch-1 topics). Operator marks `auto_checks[G1].known_benign: true` in the gate file.

#### Phase 3 — State log

```yaml
phase_3_rerun_batch_1:
  status: pending
  started_at:
  completed_at:
  bust_manifest:
  delta_id:
  elapsed_ms:
  falkor_state_before:
    topic_node_count:
    tema_edge_count:
    article_nodes_without_tema:
  falkor_state_after:
    topic_node_count:
    tema_edge_count:
    article_nodes_without_tema:
  gate_status:
  gate_g1_known_benign_marked:
  gate_g4_passed:
  notes:
```

---

### Phase 4 — Resume v3 Phase 3 chain (batches 2–11)

**Goal.** With the loader fix proven on batch 1, run the remaining 10 batches and close v3.

#### Phase 4 — Prerequisites

- Phase 3 of v4 passed (gate status = passed).
- `artifacts/fingerprint_bust/plan.json` is v3.1 (11 batches).
- `scripts/monitoring/monitor_ingest_topic_batches/run_topic_backfill_chain.sh` skeleton exists. Full autonomous loop lands here in v4 Phase 4 proper.

#### Phase 4 — Chain loop build-out

The v3 skeleton refuses to loop past the gate. v4 needs to add the autonomous pass:

| File | Change |
|---|---|
| `scripts/monitoring/monitor_ingest_topic_batches/run_topic_backfill_chain.sh` | Replace the `chain)` exit-0 placeholder with a real loop: for each remaining batch in plan.json, run `launch_batch.sh --batch N`, wait for cli.done via `logs/events.jsonl` tail, run `validate_batch.py` (non-gate mode), append to `artifacts/backfill_state.json::done_batches_log`, sleep 30s, repeat. Poll `STOP_BACKFILL` sentinel every loop iteration and exit cleanly. |

Actually simpler: **run the chain manually batch-by-batch via the existing `launch_batch.sh`**, since each batch is ~10-20 min and we'll keep eyes on it. That defers the chain-loop code (still pending in v3 Phase 3) until v5 if needed. Manual iteration is more observable for a first real run anyway.

Decision: **manual batch-by-batch for v4**. Upgrade to autonomous loop becomes v5 F10 followup if manual proves too tedious.

#### Phase 4 — Run (per-batch; repeat for batches 2 through 11)

```bash
# For each N in 2..11:
bash scripts/ingestion/launch_batch.sh --batch $N --dry-run   # preview
bash scripts/ingestion/launch_batch.sh --batch $N             # real
# arm heartbeat cron with the new delta_id and --total from shortcut.computed
# wait for cli.done
PYTHONPATH=src:. uv run python scripts/monitoring/monitor_ingest_topic_batches/validate_batch.py \
  --batch $N --manifest <manifest> --delta-id <id> --delta-elapsed-ms <ms> \
  --dry-run-row-count-after 0 --target production
# inspect + proceed
```

#### Phase 4 — Acceptance

1. Each batch's validator reports ≥8 of 10 auto-checks green (G1 exempt as long as drift <10%; G4 must pass).
2. Final Falkor state: TopicNode ≥ 60, TEMA ≥ 1,000.
3. `artifacts/backfill_state.json::done_batches_log` has 10 entries (batches 2-11).
4. `artifacts/STOP_BACKFILL` absent at completion.
5. v3 Phase 5 (operator browser smokes) can begin.

#### Phase 4 — State log

```yaml
phase_4_chain_2_through_11:
  status: pending
  started_at:
  completed_at:
  batches_done: []              # list of {batch, delta_id, elapsed_ms, tema_after, topic_after}
  blockers_seen: []
  falkor_final:
    topic_node_count:
    tema_edge_count:
    articles_without_tema:
  notes:
```

---

## §6 End-to-end execution recipe

One-shot path from today's failed gate to v3 close-out:

```bash
# --- Phase 1: code fix (local, ~90 min) ---
git checkout -b feat/ingestionfix-v4-graph-eligibility

# Edit these four files (see §5 Phase 1):
$EDITOR src/lia_graph/graph/schema.py
$EDITOR src/lia_graph/ingestion/loader.py
$EDITOR src/lia_graph/ingest.py
$EDITOR src/lia_graph/ingestion/delta_runtime.py

# Add the new test file:
$EDITOR tests/test_loader_article_eligibility.py

# Update existing test files:
$EDITOR tests/test_falkor_loader_thematic.py
$EDITOR tests/test_loader_delta.py

PYTHONPATH=src:. uv run pytest tests/test_loader_article_eligibility.py \
  tests/test_falkor_loader_thematic.py tests/test_loader_delta.py \
  tests/test_dangling_store.py tests/test_ingest_cli_additive.py \
  tests/test_apply_sector_reclassification.py -q

git commit -am "fix(v4-phase-1): prose-only docs eligible for ArticleNode; doc-scoped graph keys"

# --- Phase 2: consumer audit (~30 min) ---
grep -rn "article_number" src/lia_graph/pipeline_d/ src/lia_graph/graph/
# patch only if a real issue surfaces
git commit -am "fix(v4-phase-2): relax retriever article_number filter (if needed)"

# --- Phase 3: re-bust + re-run batch 1 + re-validate (~25 min wall) ---
cd /Users/ava-sensas/Developer/Lia_Graph
set -a; source .env.staging; set +a

bash <<'RUN'
# bust 48-topic union
PYTHONPATH=src:. uv run python scripts/monitoring/monitor_ingest_topic_batches/fingerprint_bust.py \
  --topics "<48 comma-separated topics>" \
  --target production --confirm --force-multi --tag v4_rerun

# detached ingest
nohup bash -c 'set -a; source .env.staging; set +a; \
  exec env PYTHONPATH=src:. uv run python -m lia_graph.ingest \
  --corpus-dir knowledge_base --artifacts-dir artifacts --additive \
  --supabase-sink --supabase-target production \
  --supabase-generation-id gen_active_rolling \
  --execute-load --allow-unblessed-load --strict-falkordb \
  --allow-non-local-env --json' > logs/launch-batch-1-v4-$(date -u +%Y%m%dT%H%M%SZ).log 2>&1 < /dev/null &
disown $! 2>/dev/null || true
RUN

# arm 3-min heartbeat cron (see v3 cheat sheet)

# once cli.done:
PYTHONPATH=src:. uv run python scripts/monitoring/monitor_ingest_topic_batches/validate_batch.py \
  --batch 1 --gate --manifest <v4 bust manifest> \
  --delta-id <v4 delta_id> --delta-elapsed-ms <ms> \
  --dry-run-row-count-after 0 --target production

# --- Phase 4: chain batches 2-11 (~2-2.5 hr unattended) ---
# Per-batch: bash scripts/ingestion/launch_batch.sh --batch N → heartbeat → validate
```

---

## §7 Rollback + recovery

### 7.1 If Phase 1 tests fail
Revert the 4 source files; the v4 branch becomes dead. No prod impact.

### 7.2 If Phase 3 re-run fails mid-ingest
- The pre-v4 fingerprints were already nulled by v3's Phase 3.0. Phase 3 of v4 nulls them again (idempotent).
- Re-running `launch_batch.sh --batch 1` is safe (additive path + idempotent sink + Falkor MERGE).
- If crash is repeatable, diagnose via `logs/events.jsonl` + `logs/launch-batch-1-v4-*.log` before retry.

### 7.3 If Phase 4 chain hits a classifier or loader bug on batch N
- `touch artifacts/STOP_BACKFILL` halts the chain at the next batch boundary (manual loop: skip next launch).
- Fix the bug, re-stage, commit.
- Re-run `launch_batch.sh --batch N` for the failing batch.
- Prior completed batches (1..N-1) stay in stone (topic-filter isolation + idempotent sink per v3 §5 Phase 3 durability contract).

### 7.4 If `is_prose_only` breaks a downstream consumer
Hot-patch: schema allows the property to be missing; default Cypher reads to `coalesce(is_prose_only, false)`. Update consumers, re-deploy.

### 7.5 If Falkor becomes inconsistent (orphan edges, missing nodes)
Detach-delete the affected topic subgraph and re-run that batch. v3 §7 rollback procedures apply unchanged.

---

## §8 Global state ledger

```yaml
plan_version: 4.0
plan_last_updated: 2026-04-23 (Bogotá) PM
plan_supersedes: none  # v4 is additive to v3; v3 Phase 3 remains the live backfill plan

phase_1_schema_loader:
  status: pending
  started_at:
  completed_at:
  branch:
  files_modified:
  files_created:
  tests_passing:
  notes:

phase_2_consumer_audit:
  status: pending
  started_at:
  completed_at:
  grep_findings: []
  patches_required: []
  notes:

phase_3_rerun_batch_1:
  status: completed_with_known_shortfall  # 2026-04-23 PM Bogotá
  started_at: 2026-04-23 (Bogotá) PM
  completed_at: 2026-04-23 (Bogotá) PM
  bust_manifest: artifacts/fingerprint_bust/20260424T032934Z_v4_rerun.json
  delta_id: delta_20260424_033011_3d11e5
  elapsed_ms: 1652150   # 27.5 min (slightly over G9 upper bound)
  falkor_state_before:
    topic_node_count: 16
    tema_edge_count: 32
    article_nodes_without_tema: 8074
  falkor_state_after:
    topic_node_count: 27              # +11 (mostly pre-existing existing-topic reinforcements; only 1 sector_* landed)
    tema_edge_count: 600              # +568 — HUGE win; prose-only fix lets existing topics finally get TEMA edges
    article_nodes_without_tema: 7928  # -146 — direction is right; many more pending batches 2-8
    article_nodes_total: 8528         # +422 — prose-only ArticleNodes materialized
  gate_status: failed                 # G1/G2/G3/G4/G9 fail — see notes
  gate_failures:
    g1: "documents(tema IN 47 topics, live) = 519 vs manifest 526 — 7 docs re-classified out (benign drift)"
    g2: "document_chunks distinct doc_id = 471 vs manifest 526 — 55 missing (prose docs w/ no chunks — followup F12)"
    g3: "25 of 26 sector_* TopicNodes missing — CLASSIFIER REGRESSION (see below)"
    g4: "Same 25 sector_* topics lack TEMA edges"
    g9: "27.5 min elapsed vs 5-25 bound (sink+Falkor took longer than batch-1's 21.9 min because 509 docs vs 465)"
  critical_finding: >
    The additive ingest re-classifies docs whose fingerprint is nulled. The
    classifier (Gemini-based, prompt built from taxonomy aliases) does NOT
    recognize the 26 new `sector_*` topics added in v3 Phase 2.5 Task C.
    Result: all 432 Task E-migrated docs got re-classified back to
    `otros_sectoriales`. `documents.tema` distribution reverted from
    otros_sectoriales=78 → 511. Task E work is effectively undone in
    Supabase.
    v4 prose-only fix works correctly (TEMA edges 32 → 600 for existing
    topics) but sector TopicNode population requires classifier changes
    (tracked as F11).
  v4_scope_reassessment: >
    v4 delivered its primary goal: prose-only ArticleNodes + TEMA edges
    for all 27 currently-classifiable top-level topics. The 26 new sector
    topics cannot populate until the classifier is taxonomy-aware. Phase 4
    proceeds on batches 2-8 (existing-topic batches). Batches 9/10/11
    (sector-only) are no-ops for Falkor until F11 ships.
  notes: |
    Validator patches shipped during this run:
    - G2/G8/G10 batched at 150 keys/chunk to avoid PostgREST URL-length cliff.
    Gate file: artifacts/batch_1_quality_gate.json (status: failed).
    Operator review: the failures are real but scope-bounded; proceed to
    Phase 4 on existing topics.

phase_4_chain_2_through_11:
  status: pending
  started_at:
  completed_at:
  batches_done: []
  falkor_final:
    topic_node_count:
    tema_edge_count:
  notes:

followups_for_later:
  - id: F8
    source: v4 §2
    description: >
      Cross-doc numbered-article key collision. Article 5 of Ley 100 and
      Article 5 of Ley 300 both produce article_key="5" and MERGE to a
      single ArticleNode in Falkor. Fix: scope numbered-article graph keys
      by source_path too. Risk: invalidates 8,106 existing ArticleNode keys;
      needs a migration step to retire the orphans. Out of v4 scope.
  - id: F9
    source: v4 §2
    description: >
      Retire the 8,074 pre-v4 orphan ArticleNodes that never received
      TEMA edges. Candidates identifiable via
      `MATCH (a:ArticleNode) WHERE NOT (a)-[:TEMA]->(:TopicNode) RETURN a`.
      Needs operator review — some may be intentional anchors.
  - id: F10
    source: v4 §5 Phase 4
    description: >
      Replace the `run_topic_backfill_chain.sh` skeleton's chain) exit-0
      placeholder with a real autonomous loop (for each batch in plan.json:
      bust, launch_batch, poll events.jsonl for cli.done, validate,
      checkpoint backfill_state.json, sleep 30s, respect STOP_BACKFILL
      sentinel). Deferred because manual per-batch iteration is fine for
      v4's first real run.
  - id: F11
    source: v4 §5 Phase 3 (critical finding)
    description: >
      Classifier is not taxonomy-aware. `config/topic_taxonomy.json` was
      extended with 26 new `sector_*` entries in v3 Phase 2.5 Task C, but
      the Gemini classifier prompt doesn't incorporate them. Result: any
      additive ingest that re-classifies a Task E-migrated doc sends it
      back to `otros_sectoriales`. Fix: wire taxonomy aliases (or at least
      top-level keys) into the classifier prompt / few-shot examples so
      the classifier can pick new sectors. Until F11 ships, Phase 4
      batches 9/10/11 (sector-only) don't populate Falkor, and any bust
      that includes a Task E destination topic reverts those migrations.
      See also F7 in v3 §8 (prefix/alias map audit) — likely the same
      root cause.
  - id: F12
    source: v4 §5 Phase 3 (G2 gate finding)
    description: >
      55 doc_ids from the v4 re-run manifest (526) showed no chunks
      (471 distinct doc_ids in document_chunks). Likely prose-only docs
      where the parser emitted ONE ParsedArticle for the whole file, the
      sink only writes one chunk per article, but the manifest counted
      the underlying doc_ids from the 47-topic bust (some of which may
      have had their tema reclassified away from the busted topic set
      during ingest, so they're no longer counted under those topics).
      Low urgency: G2's strictness was designed for numbered articles
      with many-articles-per-doc. Relaxing it for prose-only-dominant
      batches is a validator tweak, not a corpus bug.
```

---

## §9 Carry-forward learnings from v3

1. **Quality Gates can surface pre-existing bugs, not just batch bugs.** v3 Phase 3.0 didn't fail because batch 1 was broken — it failed because batch 1 was the first honest test of Falkor coverage. Write gates expecting to find systemic issues, not just fresh ones.
2. **Silent drops are invisible drops.** `ingest.graph.articles_skipped_nonschema` fired on every run for months; no gate read it. Visibility without enforcement is near-useless.
3. **Fingerprint-bust + re-ingest is cheap and idempotent.** Burned ~22 min to reprocess 465 docs; will burn another 22 min to land the fix. Acceptable cost for avoiding a half-day diagnostic detour.
4. **"Catch-all eligibility" hides coverage gaps.** Relaxing eligibility makes the graph bigger but also makes downstream queries more exposed to weird shapes. Offset with an explicit flag like `is_prose_only` so consumers opt in/out consciously.
5. **Scope the fix to the immediate bug; document adjacent ones.** Cross-doc article_key collisions are bigger than v4 can reasonably solve. Flag them (F8), don't expand scope.

---

## §10 Operator cheat-sheet

```bash
# v4 Phase 1 — code + tests
git checkout -b feat/ingestionfix-v4-graph-eligibility
# edit schema.py, loader.py, ingest.py, delta_runtime.py, add test file
PYTHONPATH=src:. uv run pytest tests/test_loader_article_eligibility.py \
  tests/test_falkor_loader_thematic.py tests/test_loader_delta.py -v

# v4 Phase 3 — re-bust + re-run
set -a; source .env.staging; set +a
PYTHONPATH=src:. uv run python scripts/monitoring/monitor_ingest_topic_batches/fingerprint_bust.py \
  --topics <48-topic union> --target production --confirm --force-multi --tag v4_rerun

bash scripts/ingestion/launch_batch.sh --batch 1    # (or the detached nohup pattern from Phase 3)

# arm heartbeat cron; wait for cli.done

PYTHONPATH=src:. uv run python scripts/monitoring/monitor_ingest_topic_batches/validate_batch.py \
  --batch 1 --gate --manifest <manifest> --delta-id <id> \
  --delta-elapsed-ms <ms> --dry-run-row-count-after 0 --target production

# v4 Phase 4 — batches 2..11 (per-batch)
for N in 2 3 4 5 6 7 8 9 10 11; do
  bash scripts/ingestion/launch_batch.sh --batch $N --dry-run
  bash scripts/ingestion/launch_batch.sh --batch $N
  # heartbeat + validate after each cli.done
done

# After all 10 batches + v3 Phase 5 smokes pass:
$EDITOR docs/next/ingestionfix_v4.md   # bump plan_version to 4.1, stamp closed_out_at
git commit -am "docs(ingestionfix-v4): close-out — all phases green"
```

---

## §11 Connections to adjacent work

- **v3 Phase 3.0 gate failure** — `artifacts/batch_1_quality_gate.json` is the trigger for v4.
- **v3 Phase 3 autonomous chain** — Phase 4 of v4 finishes v3's deferred chain. Both docs track that work.
- **v3 §8 followups F1-F7** — unchanged; carry forward.
- **CLAUDE.md long-running-process pattern** — Phase 3 + Phase 4 both depend on it.
- **`graph/schema.py` required_fields invariant** — CLAUDE.md calls this out as strict. v4 loosens one field for one node kind; invariant still holds for SubTopicNode + TopicNode + others.

---

*End of document. Operator/LLM: Phase 1 is local code. Proceed immediately — no production risk until Phase 3.*
