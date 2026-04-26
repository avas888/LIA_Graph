# Next v1 — what we do after v6, why, and how we know it worked

> **Opened 2026-04-24** after v6's PR #8 merged to main. This folder is the **executable forward plan** — each step has a *what*, a *why* (with cited evidence), and a *success criterion* (measurable, not vibes).
>
> **Relation to other docs.**
> - `docs/next/ingestion_tunningv2.md` — the v6 plan that just shipped (phases 0–6).
> - `docs/next/ingestionfix_v6.md` — the forward **backlog** (30+ ideas ranked). That's the inventory; this folder is the **next-10 execution plan**.
> - `docs/learnings/` — the non-obvious invariants every step below must respect.
>
> **Why the `aa_next/` prefix.** Sorts above `next/` alphabetically — "active-active" reading order. If this folder exists and isn't empty, it's what engineers work on next.

---

## §1 The principle behind the ordering

**Diagnostic plumbing first, then quality lifts.** Phase 6 on 2026-04-24 landed a clean contamination-gate pass (4/4 non-negotiable) but several measurement fields (`seed_article_keys=0/30`, mean `primary_article_count=1.6`) are either wrong or under-recorded. Until we can *measure* retrieval depth honestly, every subsequent quality-lift PR would be flying blind. So: **steps 1–3 close measurement + corpus gaps. Steps 4–10 improve quality on top of that.** Do not parallelize the two groups until step 3 is done.

---

## §2 The ten steps

### Step 01 — [P0 · ~1 hr] Fix the `seed_article_keys=0/30` diagnostic gap — ✅ **done 2026-04-24**

**What.** Phase 1 (commit `7d966ce`) lifted `seed_article_keys` from `evidence.diagnostics` to top-level `response.diagnostics`. Post-phase-6 panel shows 0/30 rows populate this field. Either the retriever path doesn't emit it in `falkor_live` mode, or the harness reads it wrong. Investigate + fix.

**Why.** Without this field we can't tell which articles the planner actually anchored BFS on — blocks every downstream retrieval-depth investigation (step 02). Cited evidence: phase 6 scorecard in `docs/next/ingestionfix_v6.md §1`.

**Success.** Next A/B re-run shows `seed_article_keys` non-empty in ≥ 20/30 rows. Specifically measurable: `len(seed_article_keys) >= 1` for every row with `primary_article_count >= 1`.

**Deep dive:** [`01-seed-article-keys-debug.md`](./01-seed-article-keys-debug.md).

**Outcome (2026-04-24).** Root cause: `retriever_falkor.py:171` emitted `list(explicit_article_keys)` — only the planner's entry_points — but in v6 NEW mode *every* non-zero row's BFS seeds come from TEMA-first expansion merged into `effective_article_keys`, which the field never saw. 15/30 rows had `primary_article_count >= 1`; all 15 had `primary_article_count == tema_first_anchor_count`, confirming TEMA-first is the real anchor source. Fix: emit `list(effective_article_keys)` in `retriever_falkor.py`; also surface the analogous seed set from `retriever.py` (artifacts path) so the invariant is uniform across both retrievers and testable in artifact mode. Two new regression tests (`tests/test_retriever_falkor_tema_first.py` + `tests/test_orchestrator_diagnostic_surface.py`) pin the stronger invariant: `primary_article_count >= 1 ⇒ seed_article_keys non-empty`. 24/24 targeted tests green.

**End-to-end verification (2026-04-24, local artifact mode).** Ran all 30 gold questions through `run_pipeline_d` with `LIA_CORPUS_SOURCE=artifacts` / `LIA_GRAPH_MODE=artifacts` / `LIA_TEMA_FIRST_RETRIEVAL=on`:
- **Invariant satisfied 30/30** — every row with `primary_article_count >= 1` produced a non-empty `seed_article_keys`. **Zero violations.**
- **21/30 rows have non-empty `seed_article_keys`** — **exceeds the ≥ 20/30 step-01 target**. Baseline was 0/30 before the fix.
- The 9 empty-seed rows all have `primary_article_count == 0` (correct — no BFS anchors means no seeds to report).

**Flag promotion (2026-04-24 · reverted same day).** Per user directive ("make PERMANENT in the code as ACTIVE for all envs"), `LIA_TEMA_FIRST_RETRIEVAL` launcher default was flipped from `shadow` to `on` across all three modes (`scripts/dev-launcher.mjs`) and the env-matrix version was bumped to `v2026-04-24-temafirston` across all four mirror surfaces. **↩ Reverted same day** after the staging A/B (§7 action A) showed a non-negotiable contamination regression on Q27 caused by TEMA-first=on. See **§8 revert runbook** for the exact files + lines reverted and the new env-matrix version `v2026-04-24-temafirst-revert`.

**Cloud verification result (2026-04-24 · 04:39 PM Bogotá).** 🧪 → ↩ **partially verified — diagnostic wire works in cloud, but the entangled flag flip is reverted.**
- **What the cloud A/B proved works (retained).** The step-01 code fix (`retriever_falkor.py:171` + `retriever.py` seed_article_keys emission) is confirmed operating correctly in cloud: Q27 NEW surfaced `seed_article_keys=['148']`, faithfully reporting the anchor the Falkor retriever used. 15/30 NEW rows had non-empty seeds — matching `primary_article_count >= 1` in 15/30 rows (invariant holds in cloud). The diagnostic wire end-to-end is verified; these code changes stay.
- **What the cloud A/B exposed (reverted).** The TEMA-first=on behavior introduces a cross-topic anchor leak on Q27 (`art. 148 ET` cited in a SAGRILAFT answer) that doesn't exist in shadow mode. Since the launcher flip was entangled with this step's Outcome, the flip is reverted per §8 and the diagnostic code fix is retained independently.
- **Future re-flip gated on §7.H + §7.I.** Q27 leak root-cause + Q24 regression root-cause must both close ✅ before `LIA_TEMA_FIRST_RETRIEVAL` launcher default flips back to `on`. Until then step 01 stays at **🧪 verified locally + diagnostic-in-cloud**; full ✅ (flag active by default) waits.

---

### Step 02 — [P0 · ~1 day] Investigate why mean `primary_article_count` is 1.6 (target 3.0) — ✅ **investigated 2026-04-24 · no code change · absorbed into step 03**

**What.** Phase 6 showed 15/30 rows have `primary_article_count >= 1` but the mean is 1.6 — meaning the non-zero rows only average ~3.2 articles. The v5-era bet was that TEMA-first retrieval + graph BFS would return 3–5 anchor articles per answer. Read-only investigation of the 15 zero-primary rows + the 15 low-count rows. Fix the dominant cause.

**Why.** Retrieval depth is the upstream input to answer quality. Thin evidence → thin answers. Cited evidence: phase 6 measured 1.6 mean vs plan §1.5 target 3.0. Plan §2.2 in `ingestionfix_v6.md`.

**Success.** Post-fix A/B re-run: mean `primary_article_count` in NEW mode ≥ 3.0 AND `primary_article_count >= 1` rate ≥ 20/30 (target) AND `tema_first_anchor_count >= 1` rate ≥ 20/30.

**Deep dive:** [`02-retrieval-depth-investigation.md`](./02-retrieval-depth-investigation.md).

**Outcome (2026-04-24).** Partitioning the phase-6 jsonl (using the confirmed invariant `primary_article_count == tema_first_anchor_count` on every NEW non-zero row): 15/30 "ok", 11/30 H3/H4 (topic routed but 0 TEMA anchors), 4/30 router-abstained. Cross-referencing the 11 H3/H4 failures against `canonical_corpus_manifest.json` + `graph_load_report.json`:

| Topic | Docs classified | Plan TEMA edges | qid |
|---|---|---|---|
| `regimen_sancionatorio_extemporaneidad` | **0** | **0** | Q20 |
| `firmeza_declaraciones` | **0** | **0** | Q21 |
| `devoluciones_saldos_a_favor` | **0** | **0** | Q22 |
| `costos_deducciones_renta` | 0 | 5 | Q2 |
| `sector_medio_ambiente` | 0 | 2 | Q12 |
| `zonas_francas` | 2 | 10 | Q28 |
| `perdidas_fiscales_art147` | 3 | 3 | Q29 |
| `impuesto_patrimonio_personas_naturales` | 3 | 5 | Q25 |
| `dividendos_utilidades` | 6 | 5 | Q26 |
| `informacion_exogena` | 14 | 16 | Q23 |
| `estados_financieros_niif` | 30 | 25 | Q18 |

- **5 rows are pure content gap (H3).** The 3 phase-5-new topics (`firmeza_declaraciones` / `regimen_sancionatorio_extemporaneidad` / `devoluciones_saldos_a_favor`) exist in `topic_taxonomy.json` but have **zero documents classified to them** — the corpus hasn't been enriched to match the taxonomy expansion from `ingestion_tunningv2.md §5`. `costos_deducciones_renta` (0 docs / 5 edges) and `sector_medio_ambiente` (0 docs / 2 edges) are similarly thin.
- **6 rows have non-trivial TEMA coverage in the artifact plan but the staging A/B saw 0 anchors.** Most likely staging Falkor is behind the most recent plan (sync lag) — verifies automatically in the next A/B re-run.
- **0 rows fit H2 (planner anchored but BFS returned empty).** The v5 planner→TEMA-first pivot closed H2.

**Per the deep-dive §7 contingency:** *"The fix for H1 shifts rows into H3. That tells us H3 was always the real problem; step 03's scope absorbs it."* Exactly this. There is **no retriever-logic fix that buys us anything** — the retriever is correct, the graph is thin. Step 03 scope expands to include the 3 phase-5-new topic coverage in addition to its original 7 missing reform articles.

**Rollback.** No code change to roll back.

---

### Step 03 — [P0 · ~2–5 days] Ingest late-2024 / 2025 reforms + phase-5 topic content

**What.** Two bundled content gaps.
1. **v1 missing reforms (original scope).** v1 investigation I4 found 7 gold-referenced articles missing from the corpus. Land them: `LEY_2466_2025`, `LEY_1819_2016`, `CONCEPTO_DIAN_006483_2024`, `DECRETO_2616_2013`, `DECRETO_957_2019`, `DECRETO_1650`, `LEY_2277_2022` (some articles). Add to `knowledge_base/`, run additive delta.
2. **Phase-5 topic coverage (absorbed from step 02, 2026-04-24).** 3 topics added to `topic_taxonomy.json` in v6 phase 5 have **0 corpus docs classified to them**: `firmeza_declaraciones`, `regimen_sancionatorio_extemporaneidad`, `devoluciones_saldos_a_favor`. Plus 2 thin-coverage topics (`costos_deducciones_renta` 0 docs / 5 TEMA edges, `sector_medio_ambiente` 0 docs / 2 TEMA edges). Commission practitioner-authored procedural digests for each (starting with the 3 zero-coverage topics) and thread them through the classifier so TEMA edges land.

**Why.** Some phase-6 questions return low primary-article counts specifically because the expected anchor doesn't exist in the corpus. No retrieval tuning helps if the answer isn't in the index. Cited evidence: `ingestion_tunningv1.md §0` I4 findings + phase-6 gold-ref match rate + step 02 partition (5 of 11 zero-primary rows trace to phase-5 topic coverage gap).

**Success.**
- `parsed_articles.jsonl` grows to include all 7 missing refs (verify via `grep -c "LEY_2466_2025\|ET_ART_147\|..." artifacts/parsed_articles.jsonl`).
- `canonical_corpus_manifest.json` topic counts show ≥ 3 docs for each of `firmeza_declaraciones` / `regimen_sancionatorio_extemporaneidad` / `devoluciones_saldos_a_favor`.
- Next A/B re-run's per-row `expected_article_keys` hit rate lifts by ≥ 10 %.
- Mean `primary_article_count` in NEW mode ≥ 3.0 (absorbs step 02's gate).
- `tema_first_anchor_count >= 1` rate lifts to ≥ 20/30.

**Status (2026-04-24).** ⏸ **Blocked on practitioner content commission** — not a code-only task. Path A (the 3 phase-5-topic digests) overlaps directly with `docs/next/commission_dian_procedure_slate.md` (already authored as a commission brief targeting a "Abogado/contador con 7+ años en procedimiento tributario DIAN"). Path B (7 missing reforms) is fetching + formatting official gazette text — feasible via SUIN ingestion tooling but requires the fetch spec to be authored. Subsequent code-executable steps (04, 05, 07, 10) can run in parallel and don't block on this.

---

### Step 04 — [P1 · 30 min] Flip coherence gate shadow → enforce

**What.** Phase 3 (`60829f0`) added `LIA_EVIDENCE_COHERENCE_GATE`. It's been in shadow mode since ship. Phase 6 shadow-mode telemetry gives us 30 data points on what would-have-refused. If that count is 4–12, flip the launcher default to `enforce`.

**Why.** Shadow → enforce is the point at which the defensive gate actually protects users. Holding it in shadow indefinitely adds code without adding safety. Cited evidence: `ingestion_tunningv2.md §5.6` calibration band.

**Success.** Parse phase 6 jsonl for `topic_safety.coherence.misaligned == True` count. If between 4 and 12, update `scripts/dev-launcher.mjs` to set `LIA_EVIDENCE_COHERENCE_GATE=enforce` for staging + production modes. Next A/B re-run: refusal rate in NEW mode 5–15 %, contamination still 4/4 zero-hits.

**Inline spec (small step, no deep dive).**
```python
# scripts/evaluations/count_would_refuse.py — one-off, don't commit
import json
rows = [json.loads(l) for l in open("artifacts/eval/ab_comparison_20260424T183902Z_v6_rebuild.jsonl")]
count = sum(1 for r in rows
    if ((r.get("new", {}).get("diagnostics", {}).get("topic_safety", {}) or {}).get("coherence") or {})
       .get("misaligned") == True)
print(f"would-refuse: {count}/30")
```
If 4–12: flip the flag in launcher + rerun phase 6. If <4: coherence gate is too permissive, defer. If >12: too aggressive, tune the threshold in `_coherence_gate.py` first.

**Status (2026-04-24).** 🧪 **verified locally — DECISION: defer flip.** Harness extension landed; launcher flip **deferred** because the would-refuse band is out-of-range.

- **🛠 Code landed.** `scripts/evaluations/run_ab_comparison.py` now captures `coherence_mode` / `coherence_misaligned` / `coherence_reason` in each `ModeResult`; `scripts/evaluations/render_ab_markdown.py` surfaces them. 15/15 related tests pass.
- **🧪 Local verification run (2026-04-24, 30 gold questions, artifact mode, `LIA_EVIDENCE_COHERENCE_GATE=shadow`).** Coherence signal does populate end-to-end in `diagnostics.topic_safety.coherence`. **would-refuse count = 1/30** (only Q15, reason `zero_evidence_for_router_topic` on topic `laboral`).
- **→ DECISION: DEFER per inline spec** (band is [4, 12] → enforce · <4 → defer · >12 → tune). 1/30 is below the band — coherence gate would refuse too infrequently to justify promoting to `enforce`. **Do NOT flip the launcher default.** Revisit after step 03 ships new corpus content (which may shift the misalignment distribution).
- **✅ Target-env verification pending.** Falkor-live / staging A/B may produce a different count because the evidence shape differs (chunks from Supabase + graph from Falkor vs. artifact retriever). If staging band lands in [4, 12], re-open the flip decision at that time.

---

### Step 05 — [P1 · ~2 days] GUI P0 remediation — Makefile `--allow-non-local-env` + events.jsonl progress endpoint — ✅ **backend done 2026-04-24 · frontend render is separate UI work**

**What.** Two gaps from `docs/next/gui_ingestion_v1.md §13.1 + §13.2`:
1. Makefile conditional to append `--allow-non-local-env` when `PHASE2_SUPABASE_TARGET=production`.
2. Replace `/api/ingest/job/{id}/log/tail` (stdout-tail) with `/api/ingest/job/{id}/progress` (events.jsonl-aggregated JSON). The monitoring-trace spec in `gui_ingestion_v1.md §13b` is the response shape.

**Why.** The current GUI path will fail its first production-Supabase ingest on the env posture guard, or will surface free-text logs containing Spanish legal content that trips operators' error-filter instincts. Cited evidence: 2026-04-24 cloud sink stall taught us the CLI path lesson; GUI still hasn't inherited it. `heartbeat-monitoring.md` failure mode #1.

**Success.** Admin triggers a full-production UI ingest without manually editing env; the progress panel shows phase-labeled counters (classifier/bindings/sink/falkor) instead of free-text log tail; next UI-triggered phase-2-class rebuild reaches end-to-end with exit 0.

**Deep dive:** none needed; spec already in `gui_ingestion_v1.md §13b`. This step is just an execution PR.

**Outcome (2026-04-24).**
- **Sub-task 1 (Makefile).** `Makefile:139` — `PHASE2_SUPABASE_SINK_FLAGS` now appends `--allow-non-local-env` when `PHASE2_SUPABASE_TARGET=production` via `$(if $(filter production,$(PHASE2_SUPABASE_TARGET)),--allow-non-local-env,)`. Same conditional applied to `PHASE2_ADDITIVE_FLAGS:158`. `make -n phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` now emits the flag; `PHASE2_SUPABASE_TARGET=local` omits it. Regression-safe per §13.1.
- **Sub-task 2 (progress endpoint enrichment).** The `/api/ingest/job/{id}/progress` endpoint already existed and already read `events.jsonl`, but only tracked `ingest.run.stage.*` transitions — none of §13b's per-phase signals. Added `_aggregate_phase_signals(events_path)` in `ui_ingest_run_controllers.py` that surfaces: classifier count + degraded_n1_only count + rolling-1min RPM, bindings summary, sink rowcounts (`corpus.sink_summary`), falkor batch-written count (+ `graph.load_report` payload), `events_stale_seconds`, `last_event_ts_utc`. Wired into the existing progress handler as `body["phase_signals"]`. Two new unit tests pin the contract in `tests/test_ingest_progress_endpoint.py` (15/15 pass). `/log/tail` stays for free-text traceback debugging but is no longer the primary progress surface.
- **🧪 Local verification (2026-04-24)** — ran `_aggregate_phase_signals` against the real 48 MB `logs/events.jsonl` (mixed events from past v6 ingest + A/B runs). Results: `classifier.classified = 18,750` (matches `grep -c "subtopic.ingest.classified"` exactly), `classifier.degraded_n1_only = 5,888` (31.4% of classified — consistent with known v6 TPM-pressure rate), `bindings` summary populated, `sink = None` + `falkor.batch_events = 0` (expected — those events aren't emitted yet, out of step-05 scope), `events_stale_seconds = 2,323` (correct — computed from `last_event_ts_utc` vs. now). Aggregator wall-time 204 ms on 48 MB — acceptable for endpoint latency. **Signal: the aggregator picks up real events correctly.**
- **Out of step-05 scope, reassigned.** Full §13b frontend rendering is separate UI feature work (a new `runProgressTimeline` organism reading the new JSON shape). `corpus.sink_summary` and `graph.batch_written` emission depends on the ingest pipeline actually firing them — step 07 explicitly owns `graph.batch_written`. When those events ship the aggregator picks them up automatically.
- **✅ target-env verification pending** — only a real UI-triggered production ingest proves the endpoint + aggregator survive a full run end-to-end. Requires platform-admin auth + cloud creds.

---

### Step 06 — [P1 · ~3 days] TPM-aware token-budget limiter — 🛠 **primitive landed 2026-04-24 · pool integration + cloud verification pending**

**What.** Add a `TokenBudget` sibling to `TokenBucket` in `ingest_classifier_pool.py`. Estimate input tokens from the prompt + body; debit pre-call; refund on 429. Global budget matches Gemini Flash's 1 M TPM ceiling.

**Why.** Every v6 classifier run (including phase 6) emitted 92–114 TPM-429 tracebacks. Classifier's inner try/except absorbs them as degraded N1-only verdicts (`requires_subtopic_review=True`). Net cost: ~7 % of docs land with degraded classification. Cited evidence: post-phase-6 reported tracebacks + `docs/learnings/ingestion/parallelism-and-rate-limits.md` §"TPM ceiling bit us".

**Success.** Post-fix ingest runs produce **0 Traceback lines** in the classifier phase (vs 92–114 today) AND 0 rows with `requires_subtopic_review=True`. Wall time within 10 % of today's 6m30s (no throughput regression).

**Deep dive:** [`06-tpm-token-budget.md`](./06-tpm-token-budget.md).

**Status (2026-04-24).**
- **🛠 Primitive landed.** `TokenBudget` class + `estimate_input_tokens` helper + `refund` method added to `src/lia_graph/ingest_classifier_pool.py`. Mirrors existing `TokenBucket` shape (10-s burst, lock-sleep pattern, `tpm<=0 → unlimited` sentinel). Exported via `__all__`.
- **🧪 Primitive verified locally.** `tests/test_token_budget.py` — 7/7 pass covering all 5 regression guards from step-06 §4 (default 1M TPM never throttles, low TPM paces sequentially, cost>capacity clamps, refund restores exactly, 8-thread concurrent acquire/refund no deadlock) plus 2 sanity tests (estimator heuristic, tpm=0 unlimited sentinel). Cross-validated 420-ms-pace gap against capacity math: at 600 TPM with 100-token capacity already drained, acquiring 30 tokens took ~2.6s — matches the 10 tokens/s refill rate within expected band.
- **⏸ Pool integration deferred.** Wiring `TokenBudget` into `classify_documents_parallel` requires a new `TPMRateLimitError` exception in `ingestion_classifier.py` + modifying `_run_n2_cascade:720-724` to detect and re-raise Gemini 429s instead of swallowing them. Today `_run_n2_cascade` uses a generic `except Exception` that absorbs the 429 as a degraded N1-only verdict (`requires_subtopic_review=True`) — which is exactly the 31.4% degradation rate we measured in step 05's verification run against real events.jsonl (5,888/18,750). The re-raise change requires inspecting the Gemini adapter's live exception shape (not discoverable from static search alone) to match the correct 429 pattern.
- **↩ Success criterion NOT yet evaluable.** Step 06's hard gate — "0 Tracebacks on a full 1,275-doc classifier pass" — requires a live Gemini Flash classifier run under load (~7 min wall time + cloud cost). Not reachable locally. Greenlight blocks on: (a) pool-integration follow-up, (b) cloud classifier run comparing pre/post traceback counts and degradation rates.

**Test plan (added 2026-04-24 retroactively per six-gate policy):**
- *Development needed:* `TPMRateLimitError` exception class; refactor `_run_n2_cascade` to re-raise matching 429s; extend `classify_documents_parallel` signature with `token_budget_tpm` parameter + refund-on-`TPMRateLimitError` retry loop.
- *Conceptualization:* "0 Tracebacks" = the pool absorbs 429s into its retry budget instead of letting them propagate. "0 degraded rows" = every classifier call either succeeds or explicitly fails, never silently degrades. Both metrics observable in `logs/events.jsonl` after the run.
- *Running environment:* full classifier pass via `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` (or equivalent CLI). Observable via `grep -c Traceback logs/phase2_full_rebuild_*.log` and `grep -c '"requires_subtopic_review": true' logs/events.jsonl` filtered to the run's event window.
- *Actors + interventions:* platform operator with cloud + Gemini credentials; ~7-minute wall time; one engineer to analyze results.
- *Decision rule:* 0 Tracebacks AND 0 degraded rows AND wall-time ∈ [5m54s, 7m11s] (±10% of 6m32s baseline) → ✅ greenlight. Any criterion miss → ↩ refine or discard.

---

### Step 07 — [P1 · ~1 hr] Emit `graph.batch_written` events from the sink writer — ✅ **code landed + 🧪 verified end-to-end 2026-04-24**

**What.** Post-phase-2c, the Falkor writer still runs silently (no per-batch events). Add emission from `src/lia_graph/graph/client.py::_execute_live_statement` — payload `{description, stats, elapsed_ms}` — so the heartbeat can tick during `falkor_writing`.

**Why.** `gui_ingestion_v1.md §13b.4` stall thresholds depend on this signal. Without it the Falkor phase is indistinguishable from "silent 3 min" vs "actually stuck". Cited evidence: 2026-04-24 phase-2c monitors couldn't distinguish the two without manual `ps`/`lsof` triads.

**Success.** During the next production sink, `grep -c graph.batch_written logs/events.jsonl` grows steadily during `falkor_writing`; heartbeat `evt_age` stays < 30 s for the whole phase.

**Inline spec.** In `_execute_live_statement`, after the successful decode, emit:
```python
from ..instrumentation import emit_event
emit_event("graph.batch_written", {
    "description": statement.description,
    "stats": dict(stats),
    "elapsed_ms": elapsed_ms,
})
```
Only for statements where `stats` contains `nodes_created`/`relationships_created`/`properties_set` (filters out probes). Gate behind an env var `LIA_GRAPH_EMIT_BATCH_EVENTS=1` defaulting on.

**Outcome (2026-04-24).**
- **🛠 Code landed.** Added `_BATCH_WRITE_STAT_KEYS` set + `_emit_batch_written_event` helper in `src/lia_graph/graph/client.py`; wired into `_execute_live_statement` after successful decode with elapsed-ms captured via `time.perf_counter` around the socket call. Gated on `LIA_GRAPH_EMIT_BATCH_EVENTS` (default on; accepts `0` / `false` / `off` to mute). Filters out `CreateIndex` / probe statements with no write stats. Emission failures are swallowed — observability never blocks writes.
- **✅ Technical tests (gate 5a).** `tests/test_graph_client_batch_written_event.py` — 5 tests: write stats trigger emission; empty/probe stats don't; env mute works; emit-failure doesn't propagate; write-key set covers all Falkor write stat names. 5/5 pass.
- **🧪 End-user validation (gate 5b) — verified locally.** Wrote 2 `graph.batch_written` events + 1 `subtopic.ingest.classified` event into a tmp `events.jsonl`, ran the step-05b aggregator `_aggregate_phase_signals` against it: **`falkor.batch_events = 2`**, **`classifier.classified = 1`**, `events_stale_seconds = 0.02`. The aggregator picks up the emitted events end-to-end. The `falkor.batch_events = 0` gap that the step-05b verification exposed against real events.jsonl is now closed.
- **✅ Target-env verification pending.** Real Falkor cloud sink run would produce the event stream live; that closes the `✅ verified in target environment` status. No known blocker — happens automatically on the next `make phase2-graph-artifacts-supabase` run.

---

### Step 08 — [P1 · ~3 days] Gold-file extension for procedural tax topics

**What.** Phase 5 added 3 new subtopics (`firmeza_declaraciones`, `regimen_sancionatorio_extemporaneidad`, `devoluciones_saldos_a_favor`). Gold still has only the original 30 questions from v5. Commission 10–20 new questions covering the new subtopics + other under-tested procedural areas (beneficio_auditoria, ganancia_ocasional, rentas_exentas).

**Why.** A fixed 30-question gold at a 2.7× expanded corpus gives a weaker signal each cycle. We need fresh adversarial + procedural questions to exercise the phase-5 additions and the corpus content. Cited evidence: `ingestionfix_v6.md §5.1`.

**Success.** `evals/gold_retrieval_v1.jsonl` → `v2` with ≥ 40 questions; all `expected_topic` values match the taxonomy; the CI gate in `eval-c-gold` passes ≥ 90 on v2. Next A/B re-run operates on v2.

---

### Step 09 — [P2 · ~2 days] Persistent verdict cache for idempotent replays

**What.** SQLite-backed cache at `src/lia_graph/ingestion/verdict_cache.py` keyed on `sha256(prompt_template_version + model_id + content_hash)`. Read-before-call, write-after-call. Invalidate via `prompt_template_version` bump.

**Why.** Classifier verdicts today are deterministic within a run but not across runs (LLM response drift, plus TPM-pressure degradation). A cache makes replays bit-identical and cuts re-ingest wall time from ~7 min to seconds when nothing changed. Cited evidence: research note in `parallelism-and-rate-limits.md` + Stripe idempotency pattern.

**Success.** Re-running a full ingest with no code/config change completes in < 60 s (cache-hit on every classifier call) AND produces byte-identical `parsed_articles.jsonl` vs the first run.

---

### Step 10 — [P2 · 15 min] Auto-source `.env.staging` in Makefile target when production — ✅ **code landed + 🧪 dry-run verified 2026-04-24**

**What.** Add a conditional in `Makefile` that sources `.env.staging` and exports its vars when `PHASE2_SUPABASE_TARGET=production`. Trivial change; blocks no one.

**Why.** Every cloud sink run on 2026-04-24 needed the operator to manually prepend `set -a; source .env.staging; set +a`. Make owns the target; make should own the env load. Cited evidence: `docs/learnings/process/cloud-sink-execution-notes.md`.

**Success.** `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` works in a bare shell with no prefix. Regression test: same command in a subshell with no exported env vars passes the env posture guard.

**Inline spec.**
```make
PHASE2_ENV_LOAD = $(if $(filter production,$(PHASE2_SUPABASE_TARGET)),set -a && source .env.staging && set +a &&,)

phase2-graph-artifacts-supabase:
	$(PHASE2_ENV_LOAD) PYTHONPATH=src:. uv run python -m lia_graph.ingest ... \
	    --allow-non-local-env ...
```

**Outcome (2026-04-24).**
- **🛠 Code landed.** `Makefile` — added `PHASE2_ENV_LOAD = $(if $(filter production,$(PHASE2_SUPABASE_TARGET)),set -a && . ./.env.staging && set +a &&,)` and prefixed both `phase2-graph-artifacts-supabase` and `phase2-corpus-additive` recipes with it. Used `.` (posix-shell `source`) instead of `source` keyword so the recipe works under `/bin/sh` default shell without requiring bash. No-op on non-production targets.
- **🧪 Dry-run verification.** `make -n phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` emits `set -a && . ./.env.staging && set +a && PYTHONPATH=src:. uv run python -m lia_graph.ingest ... --allow-non-local-env ... --json` — env-load prefix present. Same command with `PHASE2_SUPABASE_TARGET=local` emits the baseline command without the prefix. Additive path confirmed the same way. `.env.staging` confirmed present + shell-sourceable.
- **✅ Target-env verification pending.** A real production sink run from a bare shell would confirm the env-posture guard accepts the inline-loaded creds. No known blocker.

---

## §3 Sequencing (wall-clock estimate)

Assuming one engineer:

| Week | Steps | Output |
|---|---|---|
| 1 | 01 + 02 + 03 | diagnostic gaps closed + late reforms ingested |
| 2 | 04 + 05 + 07 + 10 | coherence gate in enforce + GUI P0 shipped + Falkor events + Makefile clean |
| 3 | 06 | TPM limiter ends degradation; re-run gate in enforce mode confirms |
| 4 | 08 + 09 | gold extended + verdict cache lands |

End of week 4 = v7 plan ready for execution-phase-6 analog (a 40-question A/B against production with all improvements). That becomes `ingestion_tunningv3.md`.

---

## §4 Hard stop conditions

Abort this plan and reassess if any of these hit:

- **Step 01 finds retrieval genuinely isn't populating `seed_article_keys`** — not a harness bug. That would mean retriever refactor is needed; re-scope step 02.
- **Step 02 finds the mean 1.6 is actually a graph-sparsity problem** (not a planner/BFS tuning problem) — that means step 03's scope grows to a bigger content/ingest effort.
- **Step 06 shows even a perfect TPM limiter can't prevent degradation on the corpus** — means Gemini Flash is the wrong tier; pivot to Gemini Pro or a different provider for classifier calls.
- **Contamination gate regresses** — any v7 PR that reintroduces forbidden-token hits on Q11/Q16/Q22/Q27 blocks the merge. Non-negotiable stays non-negotiable.

---

## §5 What success looks like at the end of next_v1

**Hard gates.** All of these must be green before closing next_v1:
1. ✅ Contamination still 4/4 zero-hits on Q11/Q16/Q22/Q27 (non-negotiable, regression guard).
2. ✅ `seed_article_keys` non-empty ≥ 20/30 rows.
3. ✅ Mean `primary_article_count` ≥ 3.0 in NEW mode.
4. ✅ Classifier pass emits 0 Tracebacks (TPM limiter working).
5. ✅ UI-triggered production ingest completes without manual env prefix.

**Soft gates.** Lift but not block:
- Refusal rate in enforce mode 5–15 %.
- Gold v2 with ≥ 40 questions passing `eval-c-gold` at ≥ 90.
- `falkor_writing` phase visibly ticks in the heartbeat.
- Replay runs in < 60 s (cache hit).

---

## §6 Deep-dive files in this folder

- [`01-seed-article-keys-debug.md`](./01-seed-article-keys-debug.md) — investigation method, hypotheses to test, fix sketches.
- [`02-retrieval-depth-investigation.md`](./02-retrieval-depth-investigation.md) — how to partition the 30 questions by failure mode, what to measure per bucket, how to pick the highest-leverage fix.
- [`06-tpm-token-budget.md`](./06-tpm-token-budget.md) — `TokenBudget` design, token-estimation heuristic, interaction with existing `TokenBucket`, test strategy.

Everything else is inline above. Small steps (04, 07, 10) don't earn their own file.

---

## §7 Queued actions (six-gate format, awaiting execution)

Opened 2026-04-24. Items not yet code-complete or requiring cross-step coordination. Each carries the six-gate block the `docs/aa_next/README.md` policy requires.

### A. Staging / production A/B re-run to close step 01 → ✅ (and measure the TEMA-first flip end-to-end) — 🏃 **in flight 2026-04-24 21:32 UTC (16:32 Bogotá)**

1. **Idea.** Re-run the phase-6-class A/B harness against staging cloud (Supabase + FalkorDB) now that `LIA_TEMA_FIRST_RETRIEVAL=on` is the launcher default, to close step 01 + step 04 + step 05 + step 07 from 🧪 → ✅ in target env and measure whether the flip actually improved retrieval depth / answer quality on real cloud data.
2. **Plan.** `scripts/evaluations/run_ab_comparison.py --target production --gold evals/gold_retrieval_v1.jsonl --output-dir artifacts/eval --manifest-tag v7_postflip_temafirston`. Prior mode = `LIA_TEMA_FIRST_RETRIEVAL=shadow`, new mode = `on`. Harness already captures `seed_article_keys`, `coherence_misaligned`, `primary_article_count` (step-04 extension).
3. **Success criterion.** All of: `seed_article_keys` non-empty ≥ 20/30 rows (closes step 01 ✅); mean `primary_article_count` in NEW mode ≥ 2.5 (partial credit on step 02 absorbed-into-03 target, since content gap is still open); contamination still 4/4 zero-hits on Q11/Q16/Q22/Q27 (regression guard, non-negotiable); no row regresses from ok → zero-primary relative to the v6 phase-6 jsonl.
4. **How to test.**
   - *Development.* None — harness already extended in step 04.
   - *Conceptualization.* A target-env measurement that the code-path `retriever_falkor → effective_article_keys → seed_article_keys` actually fires in cloud. Seeds non-empty proves the Falkor retriever emits the fix end-to-end; primary_article_count is the retrieval-depth proxy. Regressions would show up as rows that were ok in the 2026-04-24 phase-6 jsonl but are now zero — meaning the flag flip broke something.
   - *Running environment.* `dev:staging` credentials (or Railway production) + real Gemini API calls for the reranker/polish paths. ~30 min wall, ~$ in LLM cost.
   - *Actors.* Platform operator with cloud + LLM credentials. Engineer to diff vs phase-6 baseline.
   - *Decision rule.* All 4 criteria met → step 01 → ✅, flip stays. Any row regresses from ok → zero → ↩ investigate, potentially revert flag. Contamination regression → immediate revert.
5. **Greenlight gates.** 5a: harness unit tests already pass (step 04). 5b: the run itself IS the end-user validation.
6. **Refine-or-discard.** If `seed_article_keys` non-empty < 15/30 in cloud despite 21/30 locally → investigate Falkor-vs-artifact divergence; possibly revert the launcher flip. If contamination regresses → revert immediately.

**Status (2026-04-24 21:39 UTC · 04:39 PM Bogotá).** ↩ **Completed · REGRESSED · revert recommended.** Run took 7m 00s (30/30 questions, exit=0, zero failures). Output at `artifacts/eval/ab_comparison_20260424T213241Z_v7_postflip_temafirston.jsonl` (+ `.md` + `_manifest.json`). Log at `logs/staging_ab_20260424T213241Z.log`.

**Four-criterion analysis vs phase-6 baseline (`artifacts/eval/ab_comparison_20260424T183902Z_v6_rebuild.jsonl`):**

| # | Criterion | Result | Cause |
|---|---|---|---|
| 1 | `seed_article_keys` non-empty ≥ 20/30 in NEW | ❌ **15/30** | Cloud Falkor TEMA coverage thinner than artifact plan — step 02 H4 diagnosis confirmed in target env. Local artifact run gave 21/30; cloud gives 15/30. Not a flag-flip regression — the fix emits correctly, the corpus is thin. |
| 2 | Mean `primary_article_count` ≥ 2.5 in NEW | ❌ **1.63** (15/30 non-zero) | Identical to phase-6's 1.63 baseline — no regression AND no lift vs phase-6. Content gap blocking — step 03 territory. |
| 3 | Contamination 4/4 zero-hits on Q11/Q16/Q22/Q27 | ❌ **Q27 `art. 148` leak in NEW only** | Q27 expects SAGRILAFT (compliance regime). NEW mode anchors on `art. 148 ET` (tax-code deduction article) and the synthesizer cites it confidently. **Postflip PRIOR (TEMA=shadow) has NO `art. 148` hit** — isolates TEMA-first=on as the mechanism. Phase-6 NEW had the same primary=1 anchor but a 101-char stub hid the leak; postflip's 2,243-char answer makes it user-visible. **Non-negotiable per §5 hard gates.** |
| 4 | No row regresses ok → zero vs phase-6 NEW | ❌ **Q24 `3 → 0`** | `gravamen_movimiento_financiero_4x1000` topic. Phase-6 NEW had primary=3, tema_anchor=3. Postflip NEW has primary=0, tema_anchor=0. Same flag config in both runs (NEW=on) — likely cloud-state drift between 13:39 UTC and 21:32 UTC, but the regression is visible only in the TEMA-first=on path. |

**Flag-flip quantified trade-off (cloud-measured):**

| Effect | PRIOR (`shadow`) | NEW (`on`) | Δ |
|---|---|---|---|
| Non-zero primary rate | 0/30 | 15/30 | +15 rows rescued |
| Mean `primary_article_count` | 0.00 | 1.63 | +1.63 |
| `seed_article_keys` non-empty | 0/30 | 15/30 | +15 (diagnostic wire confirmed working) |
| Q27 `art. 148` contamination | none | **present** | –1 user-visible regression |
| Q24 non-zero | — | went 3 → 0 | –1 user-visible regression |

**Decision per six-gate policy gate 6 (refine-or-discard · "contamination regression → immediate revert"):** ↩ **revert the `LIA_TEMA_FIRST_RETRIEVAL` launcher default from `on` back to `shadow`.** The flag flip produces measurable +15 retrieval-rescue lift but simultaneously introduces a confident-and-wrong answer on Q27 (a worse end-user outcome than the pre-flip "coverage pending" stub) and loses Q24 coverage entirely. Per the policy the guardrail is non-negotiable even if the +15 lift looks attractive. **Keep the step-01 code fix** (`seed_article_keys` emission from `effective_article_keys` in `retriever_falkor.py` + analogous in `retriever.py`, plus the two regression tests) — that's diagnostic-only, has no answer-content effect, and was correctly shown working by this run (Q27 NEW `seed_article_keys = ['148']` faithfully reports the bad anchor that was already being retrieved). **See §8 "Revert runbook" below for the exact cold-agent-executable steps.**

---

### D. Step 06 pool integration — wire TokenBudget + TPMRateLimitError into classifier pool

1. **Idea.** Complete step 06 by connecting the landed `TokenBudget` primitive to the classifier call path so TPM-429s are prevented (via pre-debit) or handled cleanly (via refund + retry) instead of being silently swallowed as N1-only degraded verdicts.
2. **Plan.** (a) Add `TPMRateLimitError` exception class in `src/lia_graph/ingestion_classifier.py`. (b) Inspect the live Gemini adapter to identify the exact exception shape emitted on `RESOURCE_EXHAUSTED` + `metric=...input_token_count` (likely `urllib.error.HTTPError` with status 429 + parseable response body). (c) Modify `_run_n2_cascade:720-724` — replace the bare `except Exception` with a narrow catch that detects the 429 pattern and raises `TPMRateLimitError(retry_after_seconds=...)`, letting other exceptions flow through as they do today. (d) Extend `classify_documents_parallel` signature with `token_budget_tpm: int = 0` (0 = unlimited, matches `TokenBucket` sentinel). Create shared `TokenBudget` in the pool. Inside `_worker`: estimate tokens via `estimate_input_tokens`, `budget.acquire()` pre-call, catch `TPMRateLimitError` on each attempt → `budget.refund()` + `_sleep_with_jitter(attempt, base=exc.retry_after_seconds or 1.0)`. (e) Add `LIA_INGEST_CLASSIFIER_TPM=1000000` env default + CLI `--classifier-tpm` passthrough.
3. **Success criterion.** Two hard gates from step-06 §4: zero `Traceback` lines in stderr during a full classifier pass on v6 corpus (1,275 docs, 8 workers) AND zero rows with `requires_subtopic_review=true` in the resulting events.jsonl (vs. 31.4% / 5,888 measured on 2026-04-24 real data). Wall time within ±10 % of today's 6m32s.
4. **How to test.**
   - *Development.* New integration test `tests/test_ingest_classifier_pool.py::test_token_budget_integration`: fake classifier that simulates `TPMRateLimitError` on 1 of 10 docs; verify pool retries with refund + eventual success + total tokens used within budget. Plus `tests/test_ingestion_classifier_429_detection.py`: mock Gemini adapter raising 429, confirm `_run_n2_cascade` raises `TPMRateLimitError` instead of returning N1 degraded.
   - *Conceptualization.* "0 Tracebacks" proves the 429 never escapes worker boundary. "0 degraded rows" proves the classifier either succeeded or returned an explicit (non-swallowed) failure. Wall-time band proves the limiter didn't pessimize throughput.
   - *Running environment.* Full classifier pass via `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` against live Gemini Flash (~7 min wall). Observable via `grep -c Traceback logs/phase2_full_rebuild_*.log` and `grep -c '"requires_subtopic_review": true' logs/events.jsonl` filtered to the run's event window.
   - *Actors.* Engineer (code). Platform operator + Gemini credentials (run). Engineer again (compare pre/post).
   - *Decision rule.* 0 Tracebacks AND 0 degraded AND wall ∈ [5m54s, 7m11s] → ✅ greenlight. Any criterion miss → ↩ refine (tune estimator) or discard (Gemini Flash is wrong tier, escalate to Pro).
5. **Greenlight gates.** 5a: unit + integration tests green. 5b: the full classifier pass is the end-user validation (end-user = accountant getting non-degraded subtopic labels on their docs).
6. **Refine-or-discard.** If limiter perfectly eliminates 429s but degradation rate stays high → root cause is not TPM (discard limiter, investigate elsewhere). If wall-time regresses > 20 % → tune estimator's `max_body_chars` or fall back to actual `countTokens` API with a cache.

---

### E. Step 03 continuation — commission practitioner content for phase-5-new topics

1. **Idea.** Close the content gap step 02 identified: 3 topics exist in `topic_taxonomy.json` but have 0 corpus docs (`firmeza_declaraciones`, `regimen_sancionatorio_extemporaneidad`, `devoluciones_saldos_a_favor`) + 2 thin-coverage topics. Commission practitioner-authored digests so the classifier can label docs under them, TEMA edges land, and retrieval has anchors to return.
2. **Plan.** Use the existing brief at `docs/next/commission_dian_procedure_slate.md` (Abogado/contador with 7+ years DIAN procedure experience; Spanish-Colombian professional register). Deliverables: procedural digests covering each of the 3 zero-coverage topics + the 2 thin ones. Add to `knowledge_base/<topic>/` as markdown. Run `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` to ingest + classify + sink + Falkor-load in one pass.
3. **Success criterion.** `canonical_corpus_manifest.json` topic_key_counts shows ≥ 3 docs for each of the 3 zero-coverage topics. `graph_load_report.json` plan shows ≥ 10 TEMA edges for each. Next A/B re-run's `primary_article_count >= 1` rate on Q20/Q21/Q22 = 3/3 (currently 0/3) + mean `primary_article_count` in NEW mode ≥ 3.0 (closes the step-02-absorbed-into-03 gate).
4. **How to test.**
   - *Development.* None on the code side. Content authoring is the deliverable.
   - *Conceptualization.* Docs under a topic → classifier labels them with that topic → TEMA edges land at ingest time → TEMA-first retrieval finds them → primary articles land in the answer.
   - *Running environment.* `make phase2-graph-artifacts-supabase` ingest + post-ingest A/B re-run.
   - *Actors.* SME practitioner (content authoring, ~weeks). Platform operator (ingest run). Engineer (A/B comparison).
   - *Decision rule.* All 4 criteria above met → step 03 → ✅. If new content lands but TEMA edges still 0 → classifier prompt/keyword tuning needed (enters step 08 territory).
5. **Greenlight gates.** 5a: content passes manual editorial review (SME-owned). 5b: A/B re-run shows the retrieval depth lift.
6. **Refine-or-discard.** If content authored but A/B shows no lift → classifier isn't binding docs to topic → keyword/prompt tuning. If content can't be authored within plan horizon → the 3 phase-5 topics get removed from `topic_taxonomy.json` (explicit discard, topics that don't have content are taxonomy debt).

---

### F. Step 08 continuation — extend gold to v2 with phase-5 + procedural coverage

1. **Idea.** The 30-question `gold_retrieval_v1.jsonl` can't exercise the 3 phase-5-new topics because none of its questions touch them. Extend gold to ≥ 40 questions so the A/B harness tests the expanded corpus honestly.
2. **Plan.** Commission 10–20 new gold questions targeting `firmeza_declaraciones`, `regimen_sancionatorio_extemporaneidad`, `devoluciones_saldos_a_favor`, plus under-tested procedural topics (`beneficio_auditoria`, `ganancia_ocasional`, `rentas_exentas`). Each with `expected_topic`, `expected_article_keys`, `followup_question_es`. Save as `evals/gold_retrieval_v2.jsonl`. Point `eval-c-gold` default at v2.
3. **Success criterion.** ≥ 40 total questions; all `expected_topic` values match current `config/topic_taxonomy.json`; `make eval-c-gold` passes at ≥ 90 on v2 (current threshold on v1); phase-5 topics have ≥ 2 questions each.
4. **How to test.**
   - *Development.* New jsonl fixture. Optional: reformatter script to convert v1 → v2 schema if fields drift.
   - *Conceptualization.* Richer test surface → stronger regression gate → every A/B cycle reveals more. No direct end-user signal; the questions ARE the end-user simulation.
   - *Running environment.* `make eval-c-gold` locally. A/B harness against cloud for retrieval depth.
   - *Actors.* SME practitioner (question authoring + expected-article curation). Engineer (schema check + gate flip).
   - *Decision rule.* CI gate passes at ≥ 90 on v2 → promote v2 as the A/B gold. Coverage of phase-5 topics verified by row count. If gate fails → authored questions are too hard vs. current corpus capability (refine criterion OR accept regression + close coverage via step 03).
5. **Greenlight gates.** 5a: SME editorial review + jsonl schema passes. 5b: CI gate clears on v2.
6. **Refine-or-discard.** Gold v2 is additive. If subset of questions turns out unanswerable given current corpus → mark them `status: aspirational` (track gap) rather than removing.

---

### G. Step 09 — persistent verdict cache for idempotent classifier replays

1. **Idea.** Classifier verdicts are deterministic within a run but not across runs (LLM response drift + TPM-pressure degradation). A SQLite-backed cache keyed on `sha256(prompt_template_version + model_id + content_hash)` would make replays bit-identical and cut re-ingest wall time from ~7 min to seconds when nothing changed.
2. **Plan.** New module `src/lia_graph/ingestion/verdict_cache.py` exposing `VerdictCache(db_path)` with `get(key) -> Verdict | None` / `put(key, verdict)`. Hook into `ingestion_classifier.classify_ingestion_document`: compute key, read-before-call; on adapter success, write-after-call. Invalidate cache by bumping `prompt_template_version` constant. SQLite schema: `CREATE TABLE verdicts (cache_key TEXT PRIMARY KEY, verdict_json TEXT NOT NULL, created_at TEXT NOT NULL)`.
3. **Success criterion.** Re-running a full ingest with no code/config change completes in < 60 s (cache-hit on every classifier call) AND produces byte-identical `parsed_articles.jsonl` vs. the first run. Cache miss rate = 0% on a no-change replay.
4. **How to test.**
   - *Development.* Unit tests: cache hit/miss, invalidation on prompt-version bump, concurrent-safety (sqlite WAL mode), content-hash collision resilience. Integration test: ingest twice with no change, compare wall times + `parsed_articles.jsonl` sha256.
   - *Conceptualization.* Idempotent replays = "ingest is cheap enough to run on every merge" = faster iteration on classifier prompts, taxonomy, corpus curation. End-user is the engineer running `make phase2-graph-artifacts-supabase`, not the accountant.
   - *Running environment.* Two consecutive `make phase2-graph-artifacts-supabase` runs; compare wall times + output hashes.
   - *Actors.* Engineer only.
   - *Decision rule.* Replay < 60 s AND byte-identical output → ✅. Non-identical output on true-no-change replay → cache key misses a determinism-relevant input (refine key shape).
5. **Greenlight gates.** 5a: unit + integration tests pass. 5b: the two-replay timing + hash check.
6. **Refine-or-discard.** If cache-key collisions produce wrong verdicts → add more fields to the key shape. If SQLite contention blocks parallel workers → switch to per-worker read + batched commit, or swap to file-backed JSON lines. If the ~7 min isn't actually a pain point once step 06 TPM limiter lands → discard (cache is premium effort for a now-cheap operation).

---

### H. Q27 TEMA-first `art. 148` contamination investigation — opened 2026-04-24 from action A outcome

1. **Idea.** The 2026-04-24 staging A/B revealed that when `LIA_TEMA_FIRST_RETRIEVAL=on`, Q27 ("¿está obligado a implementar SAGRILAFT o PTEE?" · `expected_topic=sagrilaft_ptee`) retrieves `art. 148 ET` (tax-code asset-loss deduction) as its primary anchor and the synthesizer cites it confidently in a compliance answer where it has no place. The same query in PRIOR mode (`LIA_TEMA_FIRST_RETRIEVAL=shadow`) retrieves nothing and produces a substantive-but-art.148-free answer (2,948 chars, no `art. 148` hit). Investigate the retrieval chain to identify why TEMA-first surfaces `art. 148` for topic `sagrilaft_ptee`.
2. **Plan.** Read-only investigation in three stages. (a) Query FalkorDB directly: `MATCH (t:TopicNode {topic_key: 'sagrilaft_ptee'})<-[:TEMA]-(a:ArticleNode) RETURN a.article_number, a.article_key, a.source_path ORDER BY a.article_number LIMIT 50` — inventory what TEMA edges exist for `sagrilaft_ptee`. (b) If `art.148` is in that list, trace the ingest-time binding: which corpus document did the classifier label as `topic_key=sagrilaft_ptee` AND later matched to `article_number=148`? (c) If `art.148` is NOT in that TEMA result set, the contamination is happening downstream — check `_retrieve_subtopic_bound_article_keys` / BFS expansion in `retriever_falkor.py` to find the code path that surfaces `148` despite no TEMA edge.
3. **Success criterion.** Root cause identified + one of: (i) a one-line bound filter in `retriever_falkor.py` that excludes cross-topic article numbers; OR (ii) an ingest-time classifier correction so `art.148`-containing docs don't get tagged `sagrilaft_ptee`; OR (iii) step-03-scope content addition that dilutes `art.148`'s weight in the SAGRILAFT TEMA set. Post-fix A/B re-run: Q27 NEW `art. 148` hit = 0 (clean) AND Q27 NEW `primary_article_count` ≥ 1 (no regression from the fix itself).
4. **How to test.**
   - *Development.* Cypher probe scripts (throwaway). If fix is code: add a unit test in `tests/test_retriever_falkor_*.py` that feeds a SAGRILAFT query to a mocked client returning `art.148` in the TEMA set and asserts the retriever filters it out.
   - *Conceptualization.* Test measures "does TEMA-first retrieve article X for topic Y?" in isolation from synthesis. The stronger end-user validation is the Q27 substring check in the A/B harness.
   - *Running environment.* Cypher probe needs staging FalkorDB credentials. A/B re-run needs the same environment as action A.
   - *Actors.* Engineer with cloud creds (Cypher inspection + fix). Operator with LLM budget (re-run).
   - *Decision rule.* Q27 NEW `art. 148` hit must = 0 in post-fix A/B AND Q11/Q16/Q22 still clean AND `primary_article_count` for Q27 NEW ≥ 1 (we're fixing contamination, not suppressing answers). Any miss → iterate or defer to step 03 content work.
5. **Greenlight gates.** 5a: unit tests (if code fix). 5b: Q27 clean + other 3 contamination qids still clean + Q27 retains an answer.
6. **Refine-or-discard.** If TEMA edges for `sagrilaft_ptee` turn out to be near-empty and the only available anchors are cross-topic → this converges on step 03 (commission content for `sagrilaft_ptee`). If fix requires ripping out TEMA-first entirely → discard the v5-era TEMA-first approach; the retrieval-depth lift it provided (+15 rows on the 2026-04-24 A/B) becomes a loss we absorb, and we push harder on step 03 content + planner upgrades instead.

---

### I. Q24 `gravamen_movimiento_financiero_4x1000` 3→0 regression investigation — opened 2026-04-24 from action A outcome

1. **Idea.** Q24 (GMF/4×1000 query, `expected_topic=gravamen_movimiento_financiero_4x1000`) regressed from `primary_article_count=3` in the 2026-04-24 13:39 UTC phase-6 NEW run to `primary_article_count=0` in the 2026-04-24 21:32 UTC postflip NEW run. Both runs used identical `LIA_TEMA_FIRST_RETRIEVAL=on` in NEW mode. The regression appears only in the TEMA-first path, suggesting either cloud-state drift in the TEMA edge set for this topic or a latent determinism issue in TEMA-first retrieval.
2. **Plan.** (a) Cypher probe: `MATCH (t:TopicNode {topic_key: 'gravamen_movimiento_financiero_4x1000'})<-[:TEMA]-(a:ArticleNode) RETURN count(a)` and full list. If count < 3, cloud Falkor lost TEMA edges between 13:39 and 21:32 UTC — investigate ingest/write-path concurrency. (b) If count ≥ 3, the TEMA-first retriever Cypher `_retrieve_tema_bound_article_keys` is returning empty in postflip but returned 3 in phase-6 for the same topic — investigate ordering / `LIMIT $limit` semantics / Falkor result pagination. (c) Re-run A/B with just `--limit 30` and `--resume` to see if the regression is deterministic or flaky.
3. **Success criterion.** Post-fix A/B re-run: Q24 NEW `primary_article_count` ≥ 1 (recovering at minimum the single-anchor coverage). Ideally ≥ 3 matching phase-6's observation. Q24 is the only row with a hard ok→zero regression between phase-6 and postflip; fixing it preserves the lift for rows that do benefit from TEMA-first.
4. **How to test.**
   - *Development.* Throwaway Cypher probe scripts (archive in `scripts/diagnostics/` if useful). Possibly a regression test that pins the topic→anchor-count contract if a real determinism bug is found.
   - *Conceptualization.* End-user view: Q24 asks a GMF question and gets zero primary anchors → a coverage-pending stub. Fixing this restores the substantive answer the system demonstrably produced 8 hours earlier.
   - *Running environment.* Same as H — cloud Cypher inspection + A/B re-run.
   - *Actors.* Engineer with cloud creds. Operator for re-run.
   - *Decision rule.* Q24 NEW `primary_article_count` ≥ 1 AND the other 29 rows don't regress.
5. **Greenlight gates.** 5a: unit test if determinism bug isolated. 5b: Q24 non-zero in post-fix A/B.
6. **Refine-or-discard.** If cloud state is the cause and can't be stabilized → the TEMA-first path is too cloud-dependent to be a reliable retrieval strategy; consider falling back to a deterministic TEMA-first implementation that reads from the artifact plan rather than live FalkorDB. If it's flakiness on Falkor's side → add retry+backoff around `_retrieve_tema_bound_article_keys` before giving up.

---

## §8 Revert runbook — `LIA_TEMA_FIRST_RETRIEVAL` shadow → on (2026-04-24) → **revert to shadow**

**Why this runbook exists.** Action A's 2026-04-24 staging A/B measured a non-negotiable contamination regression on Q27 caused by `LIA_TEMA_FIRST_RETRIEVAL=on` (see action A Status block above for full data). The six-gate policy requires an immediate revert. This runbook is a cold-agent-executable sequence that reverts **only** the launcher default flip — everything else from the 2026-04-24 session (step 01 diagnostic fix, step 04 harness extension, step 05 progress endpoint, step 07 graph.batch_written events, step 10 Makefile env auto-source, step 06 TokenBudget primitive) is unrelated and MUST be preserved.

### §8.1 What to keep (DO NOT TOUCH)

The following changes are not causally related to the Q27 regression and MUST remain in place:

1. **`src/lia_graph/pipeline_d/retriever_falkor.py` line 171** — emission of `seed_article_keys` from `list(effective_article_keys)`. This is diagnostic observability only; the retrieval Cypher already used `effective_article_keys` as its BFS seed set before the fix. The fix just made the seeds visible to the harness. **Proof it's not causally related:** Q27 NEW's `primary_article_count` was 1 in BOTH phase-6 (pre-fix) and postflip (post-fix) — the fix didn't change what was retrieved, only what was reported. The `art.148` anchor was present in phase-6 NEW too; phase-6's synthesizer just produced a 101-char stub that hid it.
2. **`src/lia_graph/pipeline_d/retriever.py`** — `seed_article_keys` emission from the artifacts retriever (`seed_articles` variable surfaced + empty-case fallback). Same argument: diagnostic only.
3. **`tests/test_retriever_falkor_tema_first.py`** — two new unit tests pinning the `seed_article_keys` invariant.
4. **`tests/test_orchestrator_diagnostic_surface.py`** — the `test_seed_article_keys_non_empty_when_primary_article_count_positive` test.
5. **`scripts/evaluations/run_ab_comparison.py`** — `coherence_mode` / `coherence_misaligned` / `coherence_reason` capture in `ModeResult`. Harness-only change.
6. **`scripts/evaluations/render_ab_markdown.py`** — added coherence fields to the diagnostics block. Output-only.
7. **`src/lia_graph/ui_ingest_run_controllers.py`** — `_aggregate_phase_signals` helper + wiring into `/api/ingest/job/{id}/progress`. Ingest-side observability only.
8. **`tests/test_ingest_progress_endpoint.py`** — two new tests for the aggregator.
9. **`src/lia_graph/graph/client.py`** — `_BATCH_WRITE_STAT_KEYS` set + `_emit_batch_written_event` + call from `_execute_live_statement`. Pure emission, no behavior change to retrieval/writes.
10. **`tests/test_graph_client_batch_written_event.py`** — 5 tests for the emitter.
11. **`src/lia_graph/ingest_classifier_pool.py`** — `TokenBudget` class + `estimate_input_tokens` helper + `__all__` updates. Unused primitive; not wired into the pool call path yet (step 06 continuation D).
12. **`tests/test_token_budget.py`** — 7 tests for the primitive.
13. **`Makefile`** — `--allow-non-local-env` conditional (step 05 sub-task 1) AND `PHASE2_ENV_LOAD` auto-source (step 10). Neither affects runtime retrieval.

### §8.2 What to revert (EXECUTE THESE, IN ORDER)

**Revert target: `LIA_TEMA_FIRST_RETRIEVAL` launcher default changes from `"on"` back to `"shadow"` everywhere the flip was mirrored.** Five files touch.

**Step 8.2.1 — `scripts/dev-launcher.mjs`.** Find the block starting `// v5 Phase 3 — TEMA-first retrieval.` (around line 273). The current default line reads:
```js
if (!String(env.LIA_TEMA_FIRST_RETRIEVAL || "").trim()) {
  env.LIA_TEMA_FIRST_RETRIEVAL = "on";
}
```
Change `"on"` back to `"shadow"`. Update the comment block to note the revert: replace the "Default flipped from `shadow` to `on` on 2026-04-24" prose with "**Reverted from `on` back to `shadow` on 2026-04-24** per next_v1 §7 action A outcome — staging A/B showed Q27 `art.148` contamination caused by TEMA-first=on (absent in shadow). See §7.H / §7.I follow-up investigations." Preserve the existing invariant that shell / Railway overrides win.

**Step 8.2.2 — `docs/orchestration/orchestration.md`.** Two edits.
- Version bump at line ~732: `### Current version: v2026-04-24-temafirston` → `### Current version: v2026-04-24-temafirst-revert`.
- Matrix row for `LIA_TEMA_FIRST_RETRIEVAL` at line ~747: change the `dev` / `dev:staging` / `dev:production` columns from **`on`** back to **`shadow`**. Replace the current description prose about the 2026-04-24 flip with a description that references both the original flip and the revert: *"Default `shadow` across all three modes. Briefly flipped to `on` on 2026-04-24 per next_v1 step 01 verification (21/30 artifact-mode non-empty seeds); reverted same day after staging A/B (next_v1 §7 action A) showed Q27 contamination (`art. 148 ET` leaking into SAGRILAFT answer when `on`, absent in `shadow`). See next_v1 §7.H / §7.I for the follow-up investigations that gate any future re-flip."*
- Add a new change-log entry at the top of the Change Log table, between the `v2026-04-24-temafirston` row (currently at top) and `v2026-04-22-ac1`:
  ```
  | `v2026-04-24-temafirst-revert` | 2026-04-24 | **Reverted `LIA_TEMA_FIRST_RETRIEVAL` launcher default from `on` back to `shadow`** after the same-day staging A/B (next_v1 §7 action A) showed a contamination regression on Q27 — TEMA-first=on anchors on `art. 148 ET` (tax-code deduction) for a SAGRILAFT (compliance) query, and the synthesizer cites it confidently. Postflip PRIOR (shadow) produced a 2,948-char answer with NO `art. 148` hit; NEW (on) produced a 2,243-char answer WITH `art. 148`. Non-negotiable per §5 hard gates. The +15-row retrieval-rescue lift TEMA-first=on demonstrated (0/30 → 15/30 non-zero primary) is retained as the target once §7.H / §7.I close the cross-topic-anchor leak. Step-01 diagnostic fix (seed_article_keys emission) unchanged — it surfaced the bad anchor correctly (Q27 NEW `seed_article_keys=['148']`), proving the diagnostic wire works; it's not the cause. | `scripts/dev-launcher.mjs`, `docs/orchestration/orchestration.md` (this row + matrix), `docs/guide/env_guide.md`, `CLAUDE.md`, `frontend/src/app/orchestration/shell.ts` |
  ```

**Step 8.2.3 — `docs/guide/env_guide.md`.** Two edits.
- Header version: `> **Env matrix version: v2026-04-24-temafirston.**` → `> **Env matrix version: v2026-04-24-temafirst-revert.**`
- Matrix section header: `## Runtime Retrieval Flags (v2026-04-24-temafirston)` → `## Runtime Retrieval Flags (v2026-04-24-temafirst-revert)`
- In the runtime-retrieval-flags table, change the `LIA_TEMA_FIRST_RETRIEVAL` row's three columns from **`on`** back to **`shadow`**, and update the description prose the same way as orchestration.md matrix row.

**Step 8.2.4 — `CLAUDE.md`.** Two edits.
- Section heading: `## Runtime Read Path (Env v2026-04-24-temafirston)` → `## Runtime Read Path (Env v2026-04-24-temafirst-revert)`
- In the "Additional retrieval-tuning flags" paragraph, remove `, LIA_TEMA_FIRST_RETRIEVAL=on (flipped from shadow on 2026-04-24 ...)` from the "flags the launcher defaults to ON" list. Add a short note below the v6 additions line: *"`LIA_TEMA_FIRST_RETRIEVAL` launcher default stays `shadow` — briefly flipped `on` on 2026-04-24 and reverted same day after staging A/B showed Q27 contamination; see `docs/aa_next/next_v1/README.md` §7 action A."*

**Step 8.2.5 — `frontend/src/app/orchestration/shell.ts`.** Around line 29, `<strong>v2026-04-24-temafirston</strong>` → `<strong>v2026-04-24-temafirst-revert</strong>`.

### §8.3 Post-revert verification (cold agent MUST run all three)

**Step 8.3.1 — static check.** Run `grep -n "LIA_TEMA_FIRST_RETRIEVAL" scripts/dev-launcher.mjs docs/orchestration/orchestration.md docs/guide/env_guide.md CLAUDE.md frontend/src/app/orchestration/shell.ts`. Verify: launcher line says `= "shadow"`, matrix rows say `shadow`, no residual reference to "`on` (flipped from `shadow` on 2026-04-24)" remains unpaired with its revert clause.

**Step 8.3.2 — launcher parse + env confirmation.** Run `node -e "import('./scripts/dev-launcher.mjs').then(() => console.log('ok'))"`. Confirm no syntax errors. (Ignore Docker daemon errors — they're unrelated if the process reaches the preflight stage.)

**Step 8.3.3 — cloud A/B proof-of-revert (OPTIONAL but recommended).** Re-run the staging A/B harness with the reverted default, using same command as action A but this time WITHOUT any manual `LIA_TEMA_FIRST_RETRIEVAL` export in the shell (so the launcher default applies):
```bash
set -a; source .env.staging; source .env.local; set +a
unset LIA_TEMA_FIRST_RETRIEVAL
PYTHONPATH=src:. uv run python scripts/evaluations/run_ab_comparison.py \
  --gold evals/gold_retrieval_v1.jsonl \
  --output-dir artifacts/eval \
  --manifest-tag v7_tema_reverted \
  --target production \
  --limit 5
```
Note: the harness sets `LIA_TEMA_FIRST_RETRIEVAL` explicitly per mode regardless of default — this re-run exists only to confirm no residual drift. The more important verification is that the `npm run dev:staging` server path now defaults to `shadow` again, which §8.3.1 + §8.3.2 already confirm.

### §8.4 Status updates to prior sections (cold agent MUST update these too)

- **Step 01 Outcome block** (around the "Cloud verification 🏃 in flight" line): update the status to ↩ **partially verified · diagnostic wire works · TEMA-first flip reverted.** The seed_article_keys emission fix (retriever_falkor.py:171 + retriever.py) is confirmed working in cloud (Q27 NEW `seed_article_keys=['148']` correctly surfaces the bad anchor). The launcher flip that was entangled with step 01's Outcome block is reverted per §8; the diagnostic fix is retained.
- **Step 04 Outcome block**: no change — the harness coherence capture is unrelated; the decision there (DEFER flip) was already correct.
- **Step 05 / 07 / 10 Outcome blocks**: no change — all unrelated.
- **§7 action A Status block**: already updated (shows 🏃 → ↩ REGRESSED · revert recommended with the full 4-criterion breakdown).

### §8.5 Follow-ups that must happen before any future re-flip of `LIA_TEMA_FIRST_RETRIEVAL` to `on`

Both must close ✅ before the launcher default flips back to `on`:

- **§7.H** — Q27 `art. 148` cross-topic-anchor leak root-caused and fixed (or step-03 content dilutes it below contamination threshold).
- **§7.I** — Q24 `gravamen_movimiento_financiero_4x1000` ok→zero regression root-caused and fixed (or shown to be transient cloud drift with reproducible recovery).

When both close, re-open next_v1 action A with a fresh A/B against production and verify the 4 criteria pass in target env. If they do, flip the launcher default following the same mirror-update pattern as §8.2 in reverse.

---

*Opened 2026-04-24 after v6 shipped (PR #8, commit `6e5e842`). Owner: TBD on assignment. Status: pre-execution — review this file for priority changes before a single line of code is written.*
