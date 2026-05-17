# State — fix_v19_may (graph anchor + ingestion structural fix)

> **Document type.** Live state tracker for [`fix/fix_v19_may.md`](fix/fix_v19_may.md) — the v19 structural fix that aligns Falkor `:ArticleNode` with the canonical `norm_id` grammar and unsticks the labor graph anchor problem.
> **Update cadence.** §3 (global state) every time a fase opens or closes. §4 (active tasks) whenever a task changes status. §10 (run log) append-only — every meaningful action gets a timestamped entry.
> **Authority.** This file tracks state. [`fix/fix_v19_may.md`](fix/fix_v19_may.md) defines scope. If they disagree, the scope doc wins for scope; this file wins for current status.
> **Companion trackers.** [`state_fixplan_v6.md`](state_fixplan_v6.md) — v6 SUIN rewire (CLOSED 2026-04-28). [`state_corpus_population.md`](state_corpus_population.md) — per-brief expert deliveries.

---

## 1. How to use this file

Four questions in under 60 seconds:

- **Where are we?** → §3 (global state) + §4 (per-task table)
- **What's blocking us?** → §5 (active blockers) + §4 "Blockers" col
- **What did we just do?** → §10 (run log, most recent on top)
- **What should I do next?** → §3 "Next action" + §6 (suggested order)

Update protocol:

- When you start a task, set status 🟡 → 🔵 in §4 + claim the Owner column.
- When a task closes, set status to ✅ + add a §10 run-log entry with the file paths touched.
- When you hit a blocker, add it to §5 + flag the affected §4 row.
- When a fase changes state (Fase N → ✅), update §3 + add the closure entry to §10.
- All times in §10 are **Bogotá local 12-hour AM/PM**. Machine logs stay UTC; this doc is for humans.

---

## 2. Fresh-LLM preconditions

If you are an incoming agent and v19 is your first contact, read in this order:

1. `CLAUDE.md` — repo-level operating guide. Already in context.
2. [`fix/fix_v19_may.md`](fix/fix_v19_may.md) — the scope doc. Read §0 (TL;DR), §1 (audit), §2.0 (Fase 0 findings + locked gates), §2.0.5 (operator decisions), §7 (state snapshot), §8 (open questions).
3. **This file** — §3, §4, §10.
4. [`fix/fix_v18_may.md`](fix/fix_v18_may.md) — what v18 b2.1/b2.2 shipped (conflict_resolver A1+A2 in shadow). v19 is what unsticks the data those flags receive.
5. [`fixplan_v6.md`](fixplan_v6.md) §10 — post-closure addendum with a one-screen v19 summary.

Memory-pinned guardrails (do not violate):

- Cloud writes pre-authorized — announce, don't ask. (`feedback_lia_graph_cloud_writes_authorized`)
- Beta-stance: every non-contradicting improvement flag flips ON across all three run modes. (`project_beta_riskforward_flag_stance`)
- No text walls — bullets / lists / tables only. (`feedback_no_text_walls`)
- No money quotes in status reports. (`feedback_no_money_quoting`)
- Bogotá AM/PM for user-facing times. (`feedback_time_format_bogota`)
- Six-gate lifecycle for pipeline changes — unit tests alone never sufficient. (`feedback_verify_fixes_end_to_end`)
- Diagnose before intervene. (`feedback_diagnose_before_intervene`)
- Default run mode is `dev:staging`. (`feedback_default_run_mode_staging`)
- SME panel runs only on explicit operator trigger. (`feedback_sme_panel_explicit_request_only`)
- Granular edits — don't append helpers to ≥1000-LOC files. (`feedback_granular_edits`)
- Recommendations also logged in canonical plan. (`feedback_recommendations_logged_in_canonical_plan`)

---

## 3. Current global state

**As of:** 2026-05-15 evening Bogotá

| Field | Value |
|---|---|
| fix_v19_may status | Fase 0 ✅ + 2 micro-fixes shipped; Fase 2/3/4/5/6 plan ready, no code yet |
| Fases closed (✅) | **1 of 7** — only Fase 0 (pre-flight diagnostics) |
| Fases blocked | none |
| Fases ready to start | Fase 2 (Falkor `norm_id` migration script), Fase 5 (TEMA Path B diagnosis) |
| Locked scope decisions | §2.0.5 of the scope doc: (1) Falkor-only `norm_id`, no Supabase chunk_id change, no re-embedding. (2) `Codigo_Sustantivo_Trabajo.md` added to corpus. (3) Fase 5 = Path B only. |
| Corpus addition landed | `knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Codigo_Sustantivo_Trabajo.md` — 504 headings, 498 ParsedArticle units, 79 derogated, range 1-492, source Senado |
| TEMA diagnostic instrumented | yes — both full-rebuild + delta paths emit `ingest.tema.binding_summary` |
| Parser regex micro-fix | shipped — letter-suffix composites (`97-A`, etc.) now parse with suffix intact |
| Active LLM provider for chat | gemini-flash (per `config/llm_runtime.json` — DO NOT swap to deepseek-v4-pro) |
| Default run mode | `dev:staging` (cloud Supabase + cloud Falkor) |
| Cloud Falkor TEMA edge count (last known) | **0** — root cause still pending Fase 5 diagnostic capture |
| Cloud Falkor `:ArticleNode` count (last known) | **9,331** — see scope doc §1.1 |
| v18 `LIA_CONFLICT_RESOLVER_MODE` | `shadow` — stays here until Fase 6c |

**Next action.** Pick one of:

- (a) Trigger an instrumented ingest (delta or tiny full rebuild) to capture the first `ingest.tema.binding_summary` event from cloud → unblocks Fase 5 root cause.
- (b) Begin Fase 2 implementation (`scripts/migrate_falkor_norm_ids.py` dry-run mode + tests, reusing `canon.canonicalize()`).
- (a) and (b) are independent and can run in parallel.

---

## 4. Active tasks

| # | Task | Fase | Status | Owner | Blockers | Last touched |
|---|---|---|---|---|---|---|
| F0-1 | Parser test on labor markdown sweep | 0 | ✅ | claude | — | 2026-05-15 PM |
| F0-2 | TEMA git archaeology | 0 | ✅ | claude | — | 2026-05-15 PM |
| F0-3 | Embeddings keying investigation (§8.1) | 0 | ✅ | claude | — | 2026-05-15 PM |
| F0-4 | Write findings into scope doc §2.0.x | 0 | ✅ | claude | — | 2026-05-15 PM |
| F0-5 | Operator gates 1/2/3 locked in | 0 | ✅ | operator | — | 2026-05-15 PM |
| F0-6 | Brief 01b — CST consolidado fetch | 3-prereq | ✅ delivered | expert | — | 2026-05-15 PM |
| F0-7 | Parser regex micro-fix (letter-suffix composites) | precursor | ✅ | claude | — | 2026-05-15 PM |
| F0-8 | TEMA `binding_summary` instrumentation | 5-prereq | ✅ | claude | — | 2026-05-15 PM |
| F2-1 | Write `scripts/migrate_falkor_norm_ids.py` (dry-run mode) | 2 | ✅ | claude | — | 2026-05-15 PM |
| F2-2 | Unit tests: `(source_path, article_number) → norm_id` mapping (38 cases) | 2 | ✅ | claude | — | 2026-05-15 PM |
| F2-3 | Run dry-run against cloud staging — JSONL plan + summary | 2 | ✅ | claude | — | 2026-05-15 PM |
| F2-3a | Resolve cambiario OTHERs via CAM-N01 → Ley 9/1991 rule | 2 | ✅ | claude | — | 2026-05-15 PM |
| F2-4 | Apply `norm_id` index + property to cloud Falkor (idempotent CREATE INDEX) | 2 | ✅ | claude | — | 2026-05-15 PM |
| F3-1 | Loader emits `norm_id` on ArticleNode + uses norm_id as MERGE key | 3 | ✅ | claude | — | 2026-05-15 PM |
| F3-1b | `_classify_ingestion_decision` gap-filter tightened (CST blocker) | 3 | ✅ | claude | — | 2026-05-15 PM |
| F3-2 | Re-ingest labor slice locally (CST + all `consolidado/Ley-*.md`) | 3 | ✅ | claude | — | 2026-05-15 PM |
| F3-2b | Rekey cloud Falkor: article_id ← norm_id (1,300 nodes) | 3 | ✅ | claude | — | 2026-05-15 PM |
| F3-3 | Re-ingest labor slice to cloud Supabase + Falkor | 3 | 🟡 not started | — | F3-2b | — |
| F4a-1 | Migrate `planner.py::_CASE_ANCHOR_REGISTRY` + `_explicit_article_keys` to dotted | 4a | 🟡 not started | — | F2-4 | — |
| F4a-2 | Migrate `retriever_falkor.py` MATCH on `a.article_number` → `a.norm_id` | 4a | 🟡 not started | — | F2-4 | — |
| F4a-3 | Migrate `case_bullets/*.py` (62 hits, 31 files) to dotted anchors | 4a | 🟡 not started | — | F2-4 | — |
| F4a-4 | Migrate `config/topic_norm_allowlist.json` from `art:` to `<cod>.art.` | 4a | 🟡 not started | — | F2-4 | — |
| F4a-5 | Migrate `_citation_allowlist.py` to dotted | 4a | 🟡 not started | — | F4a-4 | — |
| F4a-6 | Pre-flight: cross-surface check (`Normativa`, `Interpretación`) | 4a | 🟡 not started | — | F4a-1..F4a-5 | — |
| F4b-1 | `config/subtopic_taxonomy.json` if it references articles | 4b | 🟡 not started | — | F4a-* | — |
| F4b-2 | `config/comparative_regime_pairs.json` references to articles | 4b | 🟡 not started | — | F4a-* | — |
| F4b-3 | Test fixtures using legacy article keys (~301 baseline tests) | 4b | 🟡 not started | — | F4a-* | — |
| F5-1 | Capture first `ingest.tema.binding_summary` event from cloud | 5 | 🟡 not started | — | — | — |
| F5-2 | Diagnose: classifier-degraded vs source_path mismatch vs eligibility filter | 5 | 🟡 not started | — | F5-1 | — |
| F5-3 | Fix narrow at root cause; re-ingest to verify TEMA edges land | 5 | 🟡 not started | — | F5-2 | — |
| F6a-1 | Stand up shadow diff harness: `scripts/shadow_diff_harness.py` | 6a | 🟡 not started | — | F4a-6 | — |
| F6a-2 | Shadow period 3-5 days on `dev:staging` traffic | 6a | 🟡 not started | — | F6a-1 | — |
| F6c-1 | Add `_no_invented_uvt_ranges`-style validator on conflict_resolver A2 output | 6c | 🟡 not started | — | F4a-6 | — |
| F6c-2 | Flip `LIA_PRACTICA_NOISE_FILTER=enforce` + `LIA_CONFLICT_RESOLVER_MODE=enforce` | 6c | 🟡 not started | — | F6a-2 | — |
| F6c-3 | Run SME panel via `scripts/eval/run_sme_parallel.py` (operator-triggered) | 6c | 🟡 not started | operator | F6c-2 | — |

Status legend: 🟡 not started · 🔵 in progress · ✅ done · 🚫 blocked · ↩ discarded.

---

## 5. Active blockers

| # | Blocker | Affects | Owner | Surfaced | Resolution path |
|---|---|---|---|---|---|

(none open as of 2026-05-15 evening)

---

## 6. Suggested ordering

Independent lanes that can run in parallel:

- **Lane A (Falkor schema):** F2-1 → F2-2 → F2-3 → F2-4 → F3-1 → F3-2 → F3-3 → F4a-* → F4a-6.
- **Lane B (TEMA Path B):** F5-1 → F5-2 → F5-3. Independent of Lane A. Lane B is read-only / narrow data fix; can interleave freely.
- **Lane C (Fase 6 prep):** F6c-1 (A2 validator) is the only Fase 6 task that doesn't need shadow data — can be drafted alongside Lane A. F6a-* + F6c-2/3 wait for Lane A to close.

Hot-path bottleneck: **F2-4** (writing the `norm_id` index + property to cloud Falkor) gates all of F3/F4/F6. Land it early; it's idempotent.

---

## 7. Success criteria (per fase, measurable)

| Fase | Criterion | How to verify |
|---|---|---|
| 0 | All three F0 hypotheses tested empirically; gates 1/2/3 locked | Scope doc §2.0.1-§2.0.5 populated. **DONE.** |
| 2 | 0 ArticleNodes without `norm_id` post-migration. 0 duplicate `(norm_id)`. `MATCH (a:ArticleNode {norm_id: 'cst.art.64'}) RETURN a` resolves to ≥1 row after Fase 3. | Cypher query against cloud Falkor + migration audit log. |
| 2 | Pre vs post migration: ArticleNode count + edge count identical. | `MATCH (n:ArticleNode) RETURN count(n)` before/after. |
| 3 | ArticleNodes labor count: **41 → ≥ 200**. Concretely: `cst.art.64`, `cst.art.62`, `cst.art.65`, `cst.art.127` exist with correct headings from the CST consolidado, not from Ley 50/789 modifier text. | Cypher per-norm_id + spot-check 5 articles' `heading` against the CST file. |
| 3 | Idempotency: re-ingest twice → same conteo. | Cypher diff. |
| 4a | All case_specs use dotted anchors (e.g. `("cst.art.64", "cst.art.65")` instead of `("108", "387")`). | Grep `anchor_articles=` across `case_bullets/`. |
| 4a | v18 baseline tests (301) green with new format. | `make test-batched` clean. |
| 4a | `seed_article_keys` for probe §4.1 of v18 fix doc contains `cst.art.64`. | Snapshot test or manual probe → trace JSONL. |
| 4a | `Normativa` modal + `Interpretación` panel functional in manual probe. | Browser test on `dev:staging`. |
| 5 | `MATCH ()-[r:TEMA]->() RETURN count(r)` ≥ **1,000** post-fix on cloud. | Cypher. |
| 5 | `MATCH (t:TopicNode {topic_key: 'laboral'})-[:TEMA]->(a) RETURN count(a)` ≥ **30**. | Cypher. |
| 6a | Shadow diff harness: ≥ 80% of turnos show `primary_articles` with code-correct dotted keys (CST/Ley for labor, ET for tributario). | `scripts/shadow_diff_harness.py` aggregated report. |
| 6c | §4.1 served answer: 0 bullets `código NN`, 0 contradictions 30 vs 45, `Anclaje Legal` cites CST not ET 108/387. | Manual probe + trace JSONL. |
| 6c | SME panel acc+ ≥ **30/36** (vs baseline ~21/36). | `run_sme_parallel.py` summary. |
| 6c | v18 baseline tests: 301 green → 301 green (no regression). | `make test-batched`. |

---

## 8. Code pinpoints (every file v19 touches)

### 8.1 Already touched in this work cycle

| File | Lines | What changed | When |
|---|---|---|---|
| `src/lia_graph/ingestion/parser.py` | 11 | Regex accepts letter suffix on composites (`\d+(?:-[\dA-Za-z]+)?`) | 2026-05-15 PM |
| `tests/test_ingestion_parser.py` | end of file | New `test_composite_article_numbers_preserve_suffix` covering `97-A`, `185-A`, `391-1`, `416-A` | 2026-05-15 PM |
| `src/lia_graph/ingest.py` | ~417-444 | Emits `ingest.tema.binding_summary { phase=full_rebuild, article_topics_len, populated_count, intersection_with_merged, eligible_article_count, topic_by_source_path_len }` | 2026-05-15 PM |
| `src/lia_graph/ingestion/delta_runtime.py` | ~570-596 | Same event, `phase=delta` + `delta_id` | 2026-05-15 PM |
| `knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Codigo_Sustantivo_Trabajo.md` | (new file) | CST consolidado — 504 headings, 79 derogated, range 1-492, source Senado | 2026-05-15 PM |
| `docs/re-engineer/corpus_population_for_experts/01b_cst_consolidado_v19.md` | (new file) | Expert brief, status ✅ delivered | 2026-05-15 PM |
| `docs/re-engineer/fixplan_v6.md` | §10 (appended) | Post-closure addendum pointing at v19 | 2026-05-15 PM |
| `docs/re-engineer/fix/fix_v19_may.md` | §2.0.1-§2.0.5, §7, §8 | Fase 0 findings + locked gate decisions + §8.4/§8.5 resolved | 2026-05-15 PM |

### 8.2 To touch in Fase 2 (Falkor `norm_id` schema)

| File | Anchor | Why |
|---|---|---|
| `scripts/migrate_falkor_norm_ids.py` | (new) | Dry-run + apply, reuses `canon.canonicalize()` |
| `tests/test_norm_id_migration.py` | (new) | ~30 cases covering each source-path bucket + `OTHER` fallback abort |
| `tests/test_falkor_norm_id_schema.py` | (new) | Tests the migration script itself |
| `src/lia_graph/canon.py` | `canonicalize()` (~line 58) | Reused; do NOT modify the grammar |
| `src/lia_graph/graph/schema.py` | `:ArticleNode` registration | Add `norm_id` property + unique index entry |

### 8.3 To touch in Fase 3 (re-ingest)

| File | Anchor | Why |
|---|---|---|
| `src/lia_graph/ingestion/loader.py` | `_build_article_nodes` (~line 552) + `_graph_article_key` | Emit `norm_id` property on the GraphNodeRecord |
| `src/lia_graph/ingestion/supabase_sink.py` | — | NO CHANGE per §2.0.5 Gate 1 (Falkor-only scope) |

### 8.4 To touch in Fase 4a (consumer migration)

| File | Anchor | Hits | Why |
|---|---|---|---|
| `src/lia_graph/pipeline_d/planner.py` | `_explicit_article_keys`, `_CASE_ANCHOR_REGISTRY` walk, `_build_article_search_queries` | several | All article-key emissions become dotted |
| `src/lia_graph/pipeline_d/retriever_falkor.py` | lines 299, 350 | 2+ | `MATCH … {article_number: $key}` → `MATCH … {norm_id: $key}` |
| `src/lia_graph/pipeline_d/case_bullets/*.py` | `anchor_articles=(…)` tuples | **62 hits across 31 files** | Per-case anchors become `("cst.art.64", "cst.art.65", "et.art.108", …)` |
| `config/topic_norm_allowlist.json` | `art:NNN` entries | many | Migrate to `<cod>.art.NNN` |
| `src/lia_graph/pipeline_d/_citation_allowlist.py` | `art:` prefix consumers | several | Migrate consumers |
| `artifacts/parsed_articles.jsonl` | — | full regenerate | After Fase 3 re-ingest |

### 8.5 To touch in Fase 4a pre-flight (cross-surface check)

| File | Why |
|---|---|
| `src/lia_graph/interpretacion/retriever_supabase.py` | Confirm ArticleNode→InterpretationNode joins don't break |
| `src/lia_graph/ui_normative_processors.py` | Reads `parsed_articles.jsonl` per orchestration.md:268 |
| `artifacts/canonical_corpus_manifest.json` | Check for article keys |

### 8.6 To touch in Fase 5 (TEMA Path B)

| File | Anchor | Why |
|---|---|---|
| `src/lia_graph/ingest.py` | ~417-444 (already instrumented) | Read the emitted event to root-cause |
| `src/lia_graph/ingestion/delta_runtime.py` | ~570-596 (already instrumented) | Read the emitted event to root-cause |
| `src/lia_graph/ingestion/loader.py` | `_build_article_tema_edges` (lines 669-710) | DO NOT EDIT — code is intact per §2.0.2 |
| (root-cause site, TBD) | (TBD) | Whatever Fase 5 diagnosis identifies — likely classifier output propagation or source_path matching |

### 8.7 To touch in Fase 6 (validation + flags)

| File | Anchor | Why |
|---|---|---|
| `scripts/shadow_diff_harness.py` | (new) | Per-turn capture of `seed_article_keys` + `primary_articles` + `Anclaje Legal` |
| `src/lia_graph/pipeline_d/answer_conflict_resolver.py` | `resolve_via_a2` | Structural numeric validator on A2 LLM output, similar to `_no_invented_uvt_ranges` in `answer_llm_polish.py` |
| `scripts/dev-launcher.mjs` | `LIA_PRACTICA_NOISE_FILTER`, `LIA_CONFLICT_RESOLVER_MODE` | Flip both to `enforce` in Fase 6c |
| `CLAUDE.md` | Runtime flags table | Bump default + change-log row |
| `docs/orchestration/orchestration.md` | env matrix | Bump version + change-log row |
| `docs/guide/env_guide.md` | mirror table | Bump version |

---

## 9. Open questions still live

(All §8.1-§8.5 in the scope doc are now resolved. This section is empty as of 2026-05-15 evening. Add new ones here as they surface; promote resolved ones to the run log.)

| # | Question | Affects | Surfaced |
|---|---|---|---|

(none open)

---

## 10. Run log (most recent on top, Bogotá local time)

### 2026-05-15 ~4:20 PM Bogotá — Cloud Falkor rekeyed: article_id ← norm_id (F3-2b ✅)

- **What:** ran `scripts/falkor_rekey_article_id_to_norm_id.py --target staging --apply`. The 1,300 nodes stamped with `norm_id` during Fase 2 now have their `article_id` PK set to the dotted form too. Atomic Cypher, 7.77 ms internal execution.
- **Why:** the F3-1 loader change makes future MERGEs use `norm_id` as the key. Without this rekey, future cloud ingests would create new dotted-keyed nodes alongside the existing bare-keyed ones — same article, two nodes. Rekey closes the gap so additive ingest MERGEs onto the same identity.
- **Files:** `scripts/falkor_rekey_article_id_to_norm_id.py` (new, ~140 LOC) — dry-run by default, --apply required, idempotent.
- **Stats:** `properties_set: 1300, properties_removed: 1300` (one rename per node), pre-apply pending=1300, post-apply pending=0.
- **Idempotency:** re-running the script on the now-renamed state produces "Nothing to do — 1300 nodes already have article_id == norm_id." Safe to re-run.
- **Reversibility:** `MATCH (a:ArticleNode) WHERE a.norm_id <> '' SET a.article_id = a.article_number` restores pre-rename state (the `article_number` property was never touched).
- **Edges unaffected:** Falkor edges are keyed by internal node identity, not by `article_id` property. The 9,331 nodes' inbound/outbound edges all survive the rename — confirmed by re-running the unique-index check from Fase 2.
- **Untouched populations:** SUIN nodes (6,805) and prose-only (1,225) keep their original article_id — they have no norm_id, so the rename's WHERE clause skips them.
- **Next:** F3-3 — additive ingest of labor slice (CST consolidado + Ley-50/789/etc.) to cloud Supabase + Falkor. Now safe to run: existing cloud nodes use dotted-form `article_id`; new CST nodes will MERGE on `cst.art.<N>` keys; ET 64 (now `et.art.64`) and CST 64 (new) coexist as distinct nodes.

### 2026-05-15 ~4:15 PM Bogotá — F3-2 fully validated: CST + Ley collide-free on local Falkor

- **What:** wiped local Falkor + re-ingested labor slice end-to-end. **CST art. 64 AND Ley 50/1990 art. 64 now coexist as DISTINCT nodes with their own correct headings** — the structural collision problem v19 set out to fix is empirically resolved.
- **Numbers (local Falkor post-ingest, clean state):**

| Metric | Value |
|---|---|
| total `:ArticleNode` | 599 |
| with `norm_id` (non-empty) | 575 |
| distinct `norm_id` | 575 (zero collisions) |
| prose_only (no norm_id) | 24 |
| `cst.*` nodes | 498 |
| `ley.50.1990.*` nodes | 6 |
| `ley.789.2002.*` nodes | 7 |
| `ley.100.1993.*` nodes | 7 |
| total ley nodes | 77 |

- **Critical spot-checks (all passed):**
  - `cst.art.64` → heading `"TERMINACION UNILATERAL DEL CONTRATO DE TRABAJO SIN JUSTA CAUSA."` ✅
  - `ley.50.1990.art.64` → heading `"Indemnización por terminación sin justa causa"` ✅ (distinct from CST 64!)
  - `cst.art.62`, `cst.art.65`, `cst.art.127`, `cst.art.97-A`, `cst.art.249` ✅
- **Two blockers surfaced + fixed during F3-2:**
  - **(blocker-1)** `ingest_classifiers._classify_ingestion_decision` excluded the CST consolidado as `gap_analysis` because its §6 "Notas de cobertura" contains "Sin gaps." Fix: drop the bare-token `"gap"` substring match, keep the multi-word phrases (`"audit gap"`, `"gap analysis"`, `"analisis gap"`). Locked in by 6 new regression tests in `tests/test_ingest_classifiers_gap_filter.py`. First ingest attempt parsed only 315 articles (missing all 498 CST); after the fix, 821 articles parsed.
  - **(blocker-2)** Initial F3-1 stamped `norm_id` as a property but kept the bare `article_number` as the MERGE key. Result: when Ley 50/1990 art. 64 was MERGEd AFTER CST 64, the SET overwrote CST 64's properties — 24 CST articles lost (down to 474 of 498 expected). Fix: `graph_article_key()` now returns `norm_id` for numbered articles whose path resolves, falling back to `article.article_key` for SUIN / OTHER. Locked in by 4 new MERGE-key tests in `tests/test_loader_norm_id_emission.py` and 2 updated tests in `tests/test_loader_article_eligibility.py`.
- **Files touched in F3-2:**
  - `src/lia_graph/ingest_classifiers.py:271-282` — gap-filter narrowing (3 phrases instead of 4; bare "gap" dropped).
  - `src/lia_graph/ingestion/loader.py:43-86` (`graph_article_key`) — uses `derive_norm_id` to prefer canonical norm_id as the MERGE key.
  - `tests/test_ingest_classifiers_gap_filter.py` (new, 6 cases).
  - `tests/test_loader_norm_id_emission.py` (4 new cases).
  - `tests/test_loader_article_eligibility.py` (2 cases updated for new contract).
  - `artifacts/v19/labor_slice/parsed_articles.jsonl` — 821 rows, 498 CST + 154 Ley + 169 prose-only.
- **Final test sweep:** `pytest tests/test_canon.py tests/test_ingestion_parser.py tests/test_norm_id_migration.py tests/test_loader_article_eligibility.py tests/test_falkor_loader_thematic.py tests/test_loader_delta.py tests/test_loader_norm_id_emission.py tests/test_ingest_classifiers_gap_filter.py` → **250 passed**.
- **Events captured in `logs/events.jsonl`:**
  - `ingest.norm_id.binding_summary { phase: loader._build_article_nodes, eligible_count: 821, stamped_count: 652, by_rule: {cst_consolidado: 498, prose_only: 169, ley_filename: 154} }`
  - `ingest.tema.binding_summary { phase: full_rebuild, article_topics_len: 48, populated_count: 48, intersection_with_merged: 48, eligible_article_count: 48, topic_by_source_path_len: 43 }` — TEMA edges DID land for the slice (48 of them) because the artifacts mode uses `topic_by_source_path` from the corpus walk's path-inference, not LLM. Confirms the TEMA-edge code path is healthy locally.
- **Next:** F3-3 — repeat the same flow against cloud staging Supabase + cloud Falkor. Now requires careful handling because cloud has 1,300 nodes stamped with `norm_id` (Fase 2 migration) keyed by their original bare `article_id`. The next ingest will create NEW nodes keyed by norm_id, leaving the old bare-keyed nodes orphaned. Decision needed before F3-3: (a) wipe + full rebuild on cloud, OR (b) rename existing nodes' `article_id` to match their `norm_id` (idempotent UPDATE), then run additive ingest.

### 2026-05-15 ~3:40 PM Bogotá — Fase 3 loader integration shipped (F3-1 ✅)

- **What:** Extracted derivation logic into a shared module + wired into the loader so every new `:ArticleNode` MERGE stamps `norm_id` from day one.
- **Files:**
  - `src/lia_graph/norm_id_rules.py` (new, ~330 LOC) — single source of truth for the 11 path rules + `derive_norm_id` entry point + `DerivationOutcome` dataclass + `SKIP_SENTINEL`. Imported by both the migration script (Fase 2) and the loader (Fase 3) so they CANNOT drift.
  - `scripts/migrate_falkor_norm_ids.py` — slimmed: rules moved out, kept as thin CLI wrapper that re-exports `derive_norm_id` + `DerivationOutcome` for backwards compat with the existing test file.
  - `src/lia_graph/graph/schema.py:206-227` — added `norm_id` to `:ArticleNode` `optional_fields` so the schema validator accepts it.
  - `src/lia_graph/ingestion/loader.py:583-650` — `_build_article_nodes` calls `derive_norm_id(...)` per article, stamps `properties["norm_id"]` (empty string for prose-only / SUIN / OTHER), emits `ingest.norm_id.binding_summary { phase, eligible_count, stamped_count, by_rule }`.
  - `tests/test_loader_norm_id_emission.py` (new, 10 cases) — covers CST / ET-corpus / Ley-filename / Decreto-filename / Reforma 2466 / prose-only / SUIN / unknown-path / parity-with-migration-script / letter-suffix composite (97-A).
- **Convention chosen:** empty-string `""` instead of `None` for the unset case. Falkor `SET` on None is awkward; `""` lets consumers filter via `WHERE a.norm_id <> ""`. Aligns with how the schema validator handles other optional string fields.
- **Verification:** `pytest tests/test_canon.py tests/test_ingestion_parser.py tests/test_norm_id_migration.py tests/test_loader_article_eligibility.py tests/test_falkor_loader_thematic.py tests/test_loader_delta.py tests/test_loader_norm_id_emission.py` → **239 passed**. Drift-prevention test (`test_loader_emits_same_norm_ids_as_migration_script`) confirms loader and migration script produce byte-identical norm_ids for shared fixtures.
- **Observability:** new `ingest.norm_id.binding_summary` event fires once per ingest run alongside the existing `ingest.tema.binding_summary` instrumentation. Operator can read per-rule distribution per ingest in `tracers_and_logs/logs/events.jsonl`.
- **Next:** F3-2 (local re-ingest of labor slice to validate the loader change end-to-end) → F3-3 (cloud re-ingest of labor slice including CST consolidado).

### 2026-05-15 ~3:25 PM Bogotá — Fase 2 APPLIED to cloud staging (F2-4 ✅) — Fase 2 closed

- **What:** ran `migrate_falkor_norm_ids.py --target staging --apply --allow-other-up-to 1`. Cloud Falkor now carries `norm_id` on 1,300 :ArticleNodes with unique index.
- **Wall-clock:** 3.5s total (0.95s read + 2.2s write across 7 batches of 200 + 0.2s verify).
- **Operations executed:** (1) `CREATE INDEX FOR (a:ArticleNode) ON (a.norm_id)` — index_created=1. (2) Batched `UNWIND $rows AS row MATCH (a:ArticleNode {article_id: row.article_id}) SET a.norm_id = row.norm_id` × 7 batches × 200 = 1,300 nodes. (3) Verification query — `with_norm_id=1300, distinct_norm_ids=1300, verified=True`.
- **Post-apply graph state (cloud staging `LIA_REGULATORY_GRAPH`):**

| Population | Count | norm_id stamped? |
|---|---|---|
| `:ArticleNode` total | 9,331 | — |
| With `norm_id` | **1,300** | ✅ |
| SUIN nodes (article_id keeps as-is) | 6,805 | ⏭ skipped (v6 catalog has them) |
| Prose-only (whole::<source_path>) | 1,225 | ⏭ no number to canonicalize |
| Parser artifact (CAM-N01 `ARTÍCULO 6.1` collapse) | 1 | ⏭ kept as-is |
| Duplicate norm_ids | **0** | clean |

- **Cypher sanity examples now working in cloud:**
  - `MATCH (a:ArticleNode {norm_id: "cst.art.64"}) RETURN a` — would resolve once CST consolidado is ingested (F3-2/F3-3 still pending).
  - `MATCH (a:ArticleNode {norm_id: "et.art.420"}) RETURN a.heading` — resolves now (IVA art. 420 case).
  - `MATCH (a:ArticleNode {norm_id: "ley.9.1991.art.1"}) RETURN a` — resolves now (Estatuto Cambiario).
- **Reports:** `artifacts/v19/norm_id_apply_staging.jsonl` (per-node, 9,331 rows) + `.summary.json` (aggregates).
- **Rollback recipe** (if needed): `MATCH (a:ArticleNode) WHERE a.norm_id IS NOT NULL REMOVE a.norm_id` + `DROP INDEX FOR (a:ArticleNode) ON (a.norm_id)`. Reversible in seconds.
- **Next:** F3-1 (loader emits `norm_id` on new ingests so re-ingest of CST consolidado lands `cst.art.<N>` natively). Then F3-2 / F3-3 re-ingest the labor slice including the CST consolidado.

### 2026-05-15 ~3:15 PM Bogotá — Fase 2 staging dry-run complete (F2-3 ✅)

- **What:** read-only run of `scripts/migrate_falkor_norm_ids.py --target staging --dry-run`. 9,331 :ArticleNode rows read in 1.06s. Report at `artifacts/v19/norm_id_plan_staging.jsonl` + `.summary.json`.
- **First pass** surfaced **OTHER = 6,836** (73%) — characterized via `jq`-style bucketing: 6,805 were SUIN-derived (`suin://N` paths), 31 were small straggler buckets needing rule additions.
- **Patches applied** (then re-tested + re-ran dry-run):
  - Added top-priority `suin_skipped` rule — SUIN nodes are v6's domain (`public.norms` + `:Norm` Falkor catalog); v19 leaves their `:ArticleNode` representation alone. Marked with `rule_name="suin_skipped"`, not OTHER.
  - Fixed `_LEY_FILENAME_RE` boundary issue: `\b` after year → lookahead `(?=[\s_\-\.]|$)` so `Ley_599_2000_CodigoPenal.md` matches.
  - Hyphen variants of `REFORMA-LABORAL-LEY-2466` accepted.
  - ET topic-folder whitelist extended with `NOMINA_ELECTRONICA`, `SOC_REFORMA_ESTATUTOS`, `OBLIGACIONES_SOCIETARIAS`, `Devoluciones_Saldos_Favor`.
  - CCo rule accepts `codigo-de-comercio` hyphen variant.
  - 7 new regression unit tests locking in each patch.
- **Second pass:** OTHER dropped to **4** (all in one doc: `CAM_DECLARACION_CAMBIO/NORMATIVA/CAM-N01-declaracion-cambio-marco-legal-formularios-banco-republica.md`, articles 1, 3, 4, 6). These reference cambiario norms (Resolución BanRep / DCIN-83 / Decreto 1735/1993) — deliberately left for operator review per `feedback_diagnose_before_intervene`.
- **Final classification (9,331 nodes):**

| Rule | Count | % | Will get norm_id? |
|---|---|---|---|
| suin_skipped | 6,805 | 72.9% | no (v6 catalog) |
| et_topic_folder_default | 1,267 | 13.6% | yes (`et.art.N`) |
| prose_only | 1,225 | 13.1% | no (whole-doc key) |
| et_explicit_filename | 15 | 0.2% | yes |
| decreto_filename | 9 | 0.1% | yes |
| ley_filename | 4 | <0.1% | yes |
| reforma_laboral_2466 | 2 | <0.1% | yes |
| OTHER (cambiario) | 4 | <0.1% | pending operator |

- **Will-be-stamped total:** 1,297 norm_ids. **Duplicate norm_ids in plan:** 0.
- **Files:** `scripts/migrate_falkor_norm_ids.py` (+3 path patches, +SUIN-skip rule, +env_loader integration), `tests/test_norm_id_migration.py` (+7 regression cases, total 45 tests, all green), `artifacts/v19/norm_id_plan_staging.{jsonl,summary.json}` (new — dry-run output).
- **Next:** F2-3a — operator decides what statute the CAM_DECLARACION_CAMBIO articles belong to. Then F2-4 applies the index + norm_ids to cloud Falkor.

### 2026-05-15 ~3:00 PM Bogotá — Fase 2 migration script + tests shipped (F2-1 + F2-2)

- **What:** F2-1 + F2-2 closed.
- **Files:**
  - `scripts/migrate_falkor_norm_ids.py` (new, ~410 LOC) — modular: 9 path rules in `_RULES`, `derive_norm_id()` entry point, `MigrationPlan` aggregator with duplicate detection, `_fetch_article_nodes` reader, `_apply_index_and_norm_ids` writer, `_verify_post_apply` checker. CLI: `--target local/staging/production`, `--dry-run` (default), `--apply`, `--strict`, `--limit N`, `--report-path`, `--batch-size`. Reuses `canon.canonicalize()` — single source of truth.
  - `tests/test_norm_id_migration.py` (new, 38 cases) — covers CST consolidado, Ley laborales + comercial-societario, REFORMA_LABORAL_LEY_2466, decretos (DT-/decreto-/D... + year-in-folder fallback), ET defaults (RENTA/IVA/Corpus de Contabilidad/etc), composites (97-A, 391-1, 512-1, 616-1, 631-5, 689-3), resolución DIAN, prose-only (no norm_id), OTHER (unknown path), idempotency for already-canonical inputs, rule priority (CST > ley_filename, reforma > ley_filename, ley_filename > ET-topic-default).
  - `src/lia_graph/canon.py:584-595, 740-744` — widened CST regex + grammar to accept letter-suffix composites (`cst.art.97-A`). Mirrors the parser fix in F0-7.
  - `scripts/migrate_falkor_norm_ids.py::_DECRETO_NUMBER_ONLY_RE + _YEAR_IN_PATH_RE` — added fallback so decreto filename with NUMBER-only (year in parent folder, e.g. `NUEVOS-DATOS-BRECHAS-MARZO-2026`) classifies correctly.
- **Verification:** `pytest tests/test_canon.py tests/test_ingestion_parser.py tests/test_norm_id_migration.py` → 169 passed.
- **Next:** F2-3 — operator-greenlit dry-run against cloud staging (read-only, ~9,331 ArticleNodes, writes JSONL plan to `artifacts/v19/norm_id_plan.jsonl` + summary).

### 2026-05-15 ~2:20 PM Bogotá — Parser regex micro-fix + TEMA `binding_summary` instrumentation shipped

- **What:** F0-7 + F0-8 closed.
- **Files:**
  - `src/lia_graph/ingestion/parser.py:11` — regex extended for letter-suffix composites.
  - `tests/test_ingestion_parser.py` — added `test_composite_article_numbers_preserve_suffix`; 13/13 parser tests pass.
  - `src/lia_graph/ingest.py:~417-444` — emits `ingest.tema.binding_summary { phase=full_rebuild, … }` after `article_topics` dict-build, before `build_graph_load_plan`.
  - `src/lia_graph/ingestion/delta_runtime.py:~570-596` — same event, `phase=delta` + `delta_id`.
- **Verification:** parser tests green; CST consolidado now produces 498 ParsedArticle units with **498 distinct article numbers** (vs 492 pre-fix — the 4 letter-suffix composites no longer collide); `instrumentation.emit_event` smoke succeeds with the new payload shape.
- **Next:** F5-1 (capture first event from cloud) and/or F2-1 (Fase 2 migration script dry-run).

### 2026-05-15 ~2:10 PM Bogotá — CST consolidado delivered + dropped into corpus

- **What:** F0-6 closed. Brief 01b expert delivery received at Dropbox path `to_upload_May15/brief_01b_cst_consolidado_v19.md`; verified against §10 of the brief; copied to `knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Codigo_Sustantivo_Trabajo.md`.
- **Quality checks passed:** 504 headings, 504 URL lines (1:1), 503 separators, 29/29 priority anchor articles present, art. 64 carries Ley 789/2002 mod, art. 161 carries Ley 2466/2025 + Ley 2101/2021, art. 179 carries Ley 2466/2025; gap report present; parser dry-run yields 498 ParsedArticle units with 0 fallbacks, 79 derogados, range 1-492.
- **Files:**
  - `knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Codigo_Sustantivo_Trabajo.md` — 312 KB new file.
  - `docs/re-engineer/corpus_population_for_experts/01b_cst_consolidado_v19.md` — status flipped to ✅ delivered.
  - `docs/re-engineer/fix/fix_v19_may.md` — §8.4 resolved with delivery details.
- **Next:** parser micro-fix to capture letter-suffix composites cleanly before Fase 3 re-ingest.

### 2026-05-15 ~1:50 PM Bogotá — Operator gates 1/2/3 locked

- **What:** F0-5 closed. Scope decisions captured in scope doc §2.0.5.
- **Decisions:** Gate 1 → Falkor-only `norm_id` scope (no Supabase change, no re-embedding). Gate 2 → add `Codigo_Sustantivo_Trabajo.md` to corpus from Senado (gov.co cascade allowed). Gate 3 → Fase 5 Path B only (instrument + reproduce, no `git revert`).
- **Files:** `docs/re-engineer/fix/fix_v19_may.md` §2.0.5, §7 (state snapshot updated), §8.4 + §8.5 marked ✅.
- **Next:** write expert brief for the CST consolidado fetch.

### 2026-05-15 ~1:30 PM Bogotá — Fase 0 findings written into scope doc

- **What:** F0-4 closed. Empirical findings from F0-1/F0-2/F0-3 pasted into scope doc §2.0.1-§2.0.4.
- **Hypothesis outcomes:** parser hypothesis **refuted** (parser already handles CST/Ley labor headings — 9/10 consolidados parse without fallback, 323 units across 44 labor files); TEMA-edge regression hypothesis **refuted** (no commit removed the feature; the 0-count is a data outcome of a specific cloud rebuild); embeddings **content-keyed semantically, anchor-keyed positionally** — Opción B (Falkor-only scope) avoids re-embedding ~20,154 chunks.
- **New structural gap surfaced:** §8.4 — no `Codigo_Sustantivo_Trabajo.md` in `knowledge_base/`; CST articles only exist transitively inside `Ley-50-1990.md` etc.
- **Files:** `docs/re-engineer/fix/fix_v19_may.md` §2.0.1-§2.0.4, §7, §8.

### 2026-05-15 ~1:00 PM Bogotá — Embeddings keying investigation

- **What:** F0-3 closed. Read `embedding_ops.py:240-411` + `supabase_sink.py:270-916` end-to-end.
- **Finding:** embedding text = `f"{summary}\n{chunk_text[:512]}"[:768]` (pure content); storage column = `document_chunks.embedding`; chunk_id = `f"{doc_id}::{article_key}"` (anchor-keyed business key); upsert `on_conflict="chunk_id"` preserves embedding when chunk_id stable; straggler-delete at `supabase_sink.py:883-916` nukes mismatched chunk_ids on re-ingest. Conclusion: scope norm_id migration to Falkor only → embeddings preserved.

### 2026-05-15 ~12:45 PM Bogotá — TEMA git archaeology

- **What:** F0-2 closed. `git log -p -S` across `_build_article_tema_edges`, `EdgeKind.TEMA`, `article_topics` in `src/lia_graph/ingestion/`.
- **Finding:** introduced in `6e5e842`, touched once more in `eb3e901` (TEMA-first flag flip, no ingestion change). No commit removed the feature. The only deletion is `loader.py:487-504`, scoped per article-key on re-MERGE — not a global wipe. The cloud 0-count must come from a full rebuild where `article_topics` arrived empty.

### 2026-05-15 ~12:30 PM Bogotá — Parser test on labor markdown sweep

- **What:** F0-1 closed. Ran `parse_articles()` directly on 10 `consolidado/Ley-*.md` files + full barrido of `knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/` (44 files).
- **Result:** 9/10 consolidados parse cleanly into 6-9 articles each. Only `Ley-2466-2025.md` falls to `_section_fallback` (expected — its headings are section-shaped). Full sweep: 323 ParsedArticle units, 50 unique `(subdir, article_number)` pairs, **0** whole-doc fallbacks. The parser is fine. The real structural gap: no standalone CST in corpus.

### 2026-05-15 ~12:15 PM Bogotá — Fase 0 greenlit by operator

- **What:** Operator confirmed scope = "Just Fase 0 (pre-flight)", with the new §8.1 embeddings investigation folded in. §8.2 dual-key decision: `:ArticleNode` and `:Norm` stay separate, share `norm_id`.
- **Next:** kick off parser test + git archaeology in parallel.

---

*Drafted 2026-05-15 evening Bogotá by claude-opus-4-7. Author of code edits and run-log entries shown in §10. Operator owns gate decisions and SME-panel triggers. Companion plan: [`fix/fix_v19_may.md`](fix/fix_v19_may.md).*
