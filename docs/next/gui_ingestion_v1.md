# GUI Ingestion — canonical learnings + v6 gap analysis (v1)

> **Merged 2026-04-24 from** `docs/next/UI_Ingestion_learnings.md` **and** `docs/next/deficienciesGUIingestion_v1.md`. Both are superseded by this file — treat those as redirects.
>
> **Scope.** The **browser-facing ingestion flow** — `frontend/src/features/ingest/` + `src/lia_graph/ui_ingestion_controllers.py` + `ui_ingest_delta_controllers.py` + `ui_ingest_run_controllers.py` — and everything it invokes via `subprocess` (`make phase2-graph-artifacts-supabase`, `scripts/ingest_run_full.sh`) or in-process (`ingestion.delta_runtime.materialize_delta`). Not scoped: the headless pipeline itself (that lives in `docs/next/ingestionfix_v{1..5}.md` + `docs/next/ingestion_tunningv2.md`).
>
> **Why this doc exists.** Between 2026-04-21 and 2026-04-24 we shipped five ingestion-fix waves + a v6 investigation/execution cycle. Each wave resolved a distinct class of failure. The next UI feature that touches ingestion is one careless code review away from bringing any of those failures back — because the fixes live in pipeline code, not in a doc the next contributor will read. **This file is that doc.**
>
> **How to use.**
> 1. Before building a UI that triggers ingest, run through §1 (the pre-flight checklist).
> 2. If you're modifying an existing ingest surface, find the matching § and use its checklist as PR bar.
> 3. If the UI is missing a CLI-side win, check §13 (deficiencies catalog) — the gap is probably already mapped.
> 4. When a new class of mistake surfaces, add a §N here with the rule + the incident that motivated it.

---

## §1 The 15-point pre-flight checklist

Stick this at the top of every PR description that touches UI ingestion. Items marked **[v6]** are additions from the 2026-04-24 post-mortem.

- [ ] **P1 (v2)** — Long-running job launched detached (`nohup + disown + direct redirect`), **never** via a `tee` pipe. UI doesn't assume the process survives CLI close automatically — it checks.
- [ ] **P2 (v2)** — Progress reads from `logs/events.jsonl`, not the `--json` summary log. Summary is buffered and useless mid-run.
- [ ] **P3 (v2)** — Any `.in_()` filter is chunked at ≤200 keys; any `.upsert(...)` is chunked at ≤500 rows.
- [ ] **P4 (v2)** — Every `.upsert(list, on_conflict=...)` deduplicates the list on the conflict key BEFORE the call.
- [ ] **P5 (v2)** — Graph schema `required_fields` are enforced client-side via eligibility filters on BOTH the node and any incoming edge endpoint.
- [ ] **P6 (v2 Phase 11)** — Terminal-banner VM reads the backend slice it actually cares about (e.g., `reportJson.sink_result`, not the envelope). Regression test locks the field path.
- [ ] **P7 (v3)** — UI shows a visible heartbeat (progress + ETA + current phase + running totals) during any ingestion operation that takes >30 s. Spinners alone are a regression.
- [ ] **P8 (v3)** — Operations >200 rows have a `--dry-run` preview the UI shows FIRST, before the real mutation button appears.
- [ ] **P9 (v3)** — Destructive operations (fingerprint bust, `tema` migration, retire-and-replace) write an audit manifest BEFORE the UPDATE fires. UI surfaces the manifest path in its result block.
- [ ] **P10 (v3)** — Long pipelines are batched; per-batch checkpoint is atomic (temp + rename); resume on retry skips completed batches.
- [ ] **P11 [v6]** — Parallel classifier (phase 2a): UI inherits the default 8 workers via argparse, BUT exposes per-run overrides (`LIA_INGEST_CLASSIFIER_WORKERS`, `LIA_INGEST_CLASSIFIER_RPM`) through its "Advanced options" expando. Hard-coded defaults in the UI path are a regression. See §13.4.
- [ ] **P12 [v6]** — Parallel Supabase sink (phase 2b): UI inherits default 4 workers via `LIA_SUPABASE_SINK_WORKERS`. Delta path must also forward `supabase_workers` from deps (see §13.8).
- [ ] **P13 [v6]** — Falkor bulk-load hardening (phase 2c): UI pre-flight must verify Falkor indexes exist before ingest (`GraphClient.stage_indexes_for_merge_labels` is idempotent, ~2s). Never trigger a UI ingest against a fresh Falkor instance without this check. See §13.14.
- [ ] **P14 [v6]** — Diagnostic lift (phase 1): UI progress reads lifted top-level fields (`primary_article_count`, `tema_first_mode`, etc.) — never drill into `evidence_bundle.diagnostics`. Any new retrieval-diagnostic field added to `evidence.diagnostics` must also be lifted to top-level.
- [ ] **P15 [v6]** — `.env.staging` is sourced + `--allow-non-local-env` is passed for any `PHASE2_SUPABASE_TARGET=production` invocation. The Makefile must handle this (see §13.1) — do NOT rely on the web server's boot env happening to have the cloud creds.

---

## §2 Banner / terminal-state rendering

### §2.1 Never trust the envelope — read the slice

**Incident (v2 Phase 11, 2026-04-23).** Every successful additive-delta run rendered `0 / 0 / 0` in the terminal banner because `additiveDeltaController.ts` passed `ev.reportJson` wholesale to the VM. The backend nests per-sink counters under `report_json.sink_result`, so `vm.report.documents_added` was always undefined.

**Rule.** When surfacing counters / counts / identifiers from a job report, read the NESTED slice the backend writes, not the envelope. The envelope is a transport frame; the slice is the data.

**How to prevent the regression.**
- `frontend/tests/additiveDeltaControllerTerminalVm.test.ts` locks the wire contract; any change to the VM shape or the backend `DeltaRunReport` must update both sides + this test.
- `buildAdditiveDeltaTerminalVm()` is the seam — keep it pure + unit-tested.
- For any new banner, add a test that asserts the VM does NOT carry envelope-only fields (belt-and-suspenders — catches the next wholesale-pass bug).

**Code pointer.** `frontend/src/features/ingest/additiveDeltaController.ts` seam.

---

## §3 Progress / heartbeat surfaces

### §3.1 Read `logs/events.jsonl`, not `--json`

**Incident (v2 9.A attempt #1).** The launcher's stdout was piped through `tee`; SIGHUP killed tee; the Python process got SIGPIPE mid-classification; no summary was written. The UI was waiting on the `--json` summary that never arrived.

**Rule for UI.** Progress indicators must read `logs/events.jsonl` (one event per line, flushed per-event). The summary JSON is for post-mortems, not for live progress.

**Code pointer.** `scripts/monitoring/ingest_heartbeat.py` is the canonical event-anchored progress reader. Any UI heartbeat should follow the same event-schema contract (ts_utc, event_type, payload).

### §3.2 Silence is phase-aware, not a stall signal

**Incident (v2 + v6).** During `sink_writing` and `falkor_writing`, the pipeline emits no per-item events — only a single `start/done` pair. A UI that assumed "no events for 3 minutes = stalled" would show a false positive for 5+ minutes on every run.

**v6 addendum (2026-04-24).** Post-phase-2c, the `falkor_writing` phase SHOULD emit `graph.batch_written` events per batch (one every 3-10s). Pre-phase-2c it's silent. Adjust stall thresholds per-phase per `docs/learnings/process/heartbeat-monitoring.md §8`:

| Phase | Expected event cadence | Stall threshold |
|---|---|---|
| `classifier` | per-doc (`subtopic.ingest.classified`) | 180s |
| `bindings` | per-binding (`subtopic.graph.binding_built`) | 120s |
| `load_existing_tema` (phase 2b) | per batch | 60s |
| `sink_writing` (phase 2b) | per batch upsert | 60s |
| `falkor_writing` (phase 2c) | per `graph.batch_written` | 120s |

**Rule.** Phase-aware stall detection. The UI should show the phase name + verdict alongside the heartbeat, not just "no events recently."

**Code pointer.** `scripts/monitoring/ingest_heartbeat.py::infer_phase` + the per-phase verdict strings in `render()`.

### §3.3 Heartbeat during chain mode — chain progress + total ETA

**Incident (v3 Phase 2).** The autonomous chain (batches 2-8) was silent mid-batch. Operator had no visibility into total chain progress.

**Rule.** When a UI surfaces a chain of batches, the heartbeat prepends **Chain progress** (N/M done) + **Total ETA** (derived from average completed-batch wall time) rows above per-batch details.

**Code pointer.** `scripts/monitoring/ingest_heartbeat.py::ChainState` (reads `artifacts/backfill_state.json`).

### §3.4 Dep-health probes validated, not assumed

**Incident (2026-04-24 cloud-sink stall).** `scripts/monitoring/dep_health.py`'s Falkor probe returned `ok=False` because of a `ModuleNotFoundError` — wrong module path (`lia_graph.graph_client` instead of `lia_graph.graph.client`) and wrong API (`run_query(str)` doesn't exist). The probe reported Falkor red even while Falkor was at 779 ms latency.

**Rule.** Every monitoring probe needs its own regression test. Even a 3-line smoke (`assert dep_health.probe_falkor()["ok"] is True` when env is set) would have caught this.

**Code pointer.** `scripts/monitoring/dep_health.py` — fixed 2026-04-24 commit `2c477c5`.

---

## §4 Destructive operations

### §4.1 Always `--dry-run` first

**Incident (v3 Phase 2.1).** The shipped `plan.json` estimated batch 1 at 20 docs. A dry-run against production Supabase reported 552. Running without a dry-run would have wasted 30+ min of classifier wall time + locked 552 docs' fingerprints we didn't intend to touch.

**Rule for UI.** Any production-mutating action has a **two-step flow**:
1. `--dry-run` (button: "Previsualizar"): SELECT-only, renders the affected-row count + sample rows.
2. `--confirm` (button: "Ejecutar"): locked behind the dry-run, only unlocks after the operator sees the preview.

**Code pointer.** `fingerprint_bust.py` models this; the additive-delta "Previsualizar → Aplicar" flow in `additiveDeltaController.ts` is the UI pattern.

### §4.2 Row-count threshold — visible warning

**Rule.** If an operation would mutate >200 rows, the UI shows a yellow warning with the exact count ("Mutarás 552 documentos") and requires an additional checkbox confirm.

**Why 200.** PostgREST `.in_()` URL-length limit (v2 Phase 9.A crash #1) + the soft threshold codified in `fingerprint_bust.py::DEFAULT_SAFETY_THRESHOLD`.

### §4.3 Manifest-before-execute

**Rule.** Every destructive action writes an audit manifest (`artifacts/<op>/<ts>_<tag>.json` — doc_ids, topics, timestamps, flags used) BEFORE the UPDATE / DELETE fires. The UI surfaces the manifest path in the result block so the operator can audit after a crash.

**Why.** v2 Phase 9.A crash #2 left the sink half-written; we had no audit trail of what was attempted. Manifest-before-execute is the invariant that made retry safe.

---

## §5 Reclassification + fingerprint work

### §5.1 Never `--force-full-classify` from the UI

**Incident (v2 9.A).** Each `--force-full-classify` pass is ~40 min of classifier wall time on 1,280 docs. We paid that cost 4× on 2026-04-23 because the flag bypasses the fingerprint shortcut.

**Rule for UI.** `--force-full-classify` is NEVER offered as a button. The UI offers topic-scoped `fingerprint_bust` instead. If the operator genuinely wants a full reclassify, they run it from the CLI with all the attention costs that entails — not one misclick from a UI button.

**Code pointer.** `scripts/monitoring/monitor_ingest_topic_batches/fingerprint_bust.py` + `scripts/launch_batch.sh`.

### §5.2 Cross-batch isolation is the default, not an option

**Rule.** Any UI reclassify action filters by the topic / sector / tag the operator selected. It is STRUCTURALLY INCAPABLE of touching rows outside that filter. No "apply to all" override ships; if one is ever needed, it's a CLI-only escape hatch.

**Why.** v3's durability contract depends on prior batches being untouchable once committed. An "apply to all" UI button breaks that contract.

### §5.3 Fingerprint bust is a `NULL` UPDATE — not a DELETE

**Rule.** When the UI exposes a "retry this doc" action, under the hood it nulls `doc_fingerprint`; the next additive run does the actual reclassify + re-sink. UI must NEVER directly delete `documents` / `document_chunks` / `normative_edges` rows.

**Why.** v2 established that the additive path is idempotent on doc_id. A mid-stream DELETE breaks downstream edge-reattachment logic (dangling_store promotion depends on target article keys being stable).

---

## §6 Batch / chain semantics

### §6.1 Estimates from static config lie — probe live

**Incident (v3 §2.1).** The v3.0 seed `plan.json` sized batches from the taxonomy file. A live probe showed 2-27× drift. Batch 1's `otros_sectoriales` was 510 docs, not the 20 estimated.

**Rule.** Any UI that shows "this will affect ~N documents" derives N from a live SELECT against Supabase at render time, NOT from a static config / cached count / plan file. Show both the estimate and the source ("live probe at 3:42 PM").

### §6.2 Catch-all buckets are booby traps

**Rule.** If a UI lets the operator pick a topic filter, dynamically warn when the selected topic has >5% of the total corpus ("Este topic cubre el 39% del corpus; considera dividirlo"). Prevents `otros_sectoriales`-class accidents.

### §6.3 Durability contract surfaced in UI

**Rule.** Any UI that kicks off a multi-batch operation displays the durability contract in the "what will happen" copy:

> Si un lote falla, los anteriores permanecen guardados. Solo el lote fallido debe reintentarse.

This is user-facing trust-building — accountants stop panicking when they see this and a batch fails.

**Code pointer.** `scripts/launch_batch.sh` header + the batch_pipeline README mirror this contract verbatim; UI should reuse the same wording.

---

## §7 Testing bar

### §7.1 Fakes must be strict, not lenient

**Incident (v2 Phase 9.A crash #2).** The `_FakeClient` in `test_dangling_store.py` silently accepted duplicate upsert payloads, masking the SQLSTATE 21000 bug that later crashed production.

**Rule.** Fakes in ingestion tests reject the exact failure modes production rejects:

- Upsert with intra-payload duplicates on the conflict key → raise `RuntimeError("SQLSTATE 21000")`.
- `.in_()` with >200 keys → raise a URL-length error.
- `.upsert()` with >500 rows → raise a body-size error.

### §7.2 Wire-contract tests lock backend↔UI field paths

**Rule.** For every piece of backend data the UI consumes, a test locks the shape. The contract can evolve; the test forces both sides to change together.

**Canonical examples.**
- `frontend/tests/additiveDeltaControllerTerminalVm.test.ts` (backend `DeltaRunReport.sink_result` ↔ UI `vm.report`).
- `tests/test_supabase_sink_delta.py` (sink result shape).

### §7.3 Shell-script ingestion helpers get shell-out tests

**Rule.** Every `.sh` supervisor / launcher has a pytest-harnessed test that asserts exit codes + stderr wording for the main error paths. Plain-language error messages to operators are load-bearing and drift silently otherwise.

**Canonical example.** `tests/test_run_topic_backfill_chain.py`.

### §7.4 [v6] Phase-2a/2b/2c pool primitives get determinism tests

**Rule.** Every parallel primitive has tests pinning: output-order invariance (input order = output order), cross-run determinism (same input → same output across worker counts), rate-cap enforcement, per-item failure isolation, retry-on-transient, empty-input no-op.

**Canonical examples.** `tests/test_ingest_classifier_pool.py` (phase 2a, 7 tests), `tests/test_supabase_sink_parallel.py` (phase 2b, 9 tests), `tests/test_graph_client_phase2c.py` (phase 2c, 13 tests).

---

## §8 Observability / follow-up surfaces

### §8.1 `PipelineCResponse.diagnostics` must always carry backend identifiers

**Rule (from CLAUDE.md non-negotiable #5).** Every answered turn surfaces `retrieval_backend` and `graph_backend` in diagnostics. If you add an ingestion-related backend, wire it here too. Operators debug runtime drift by reading this field; if it's absent, we lose a full debugging channel.

### §8.2 Every ingestion job emits `ingest.delta.*` events

**Rule.** Any server-side endpoint that kicks off ingest work emits the canonical event schema (`ingest.delta.run.start`, `ingest.delta.sink.start/done`, `ingest.delta.falkor.start/done`, `ingest.delta.cli.done` or `.run.failed`) to `logs/events.jsonl`. The heartbeat + any new UI depends on this.

### §8.3 `doc_fingerprint` is the partial-completion guard

**Incident (v2 §7).** A sink crash after the fingerprint was stamped but before Falkor edges landed left docs "unchanged" on the next run — the edges would never catch up without `--force-full-classify`.

**Rule.** The fingerprint is stamped by the SINK as the LAST step of its phase. Any new write-layer that persists before the sink must NOT stamp the fingerprint. Verify the order in any PR that touches `supabase_sink.py` or adds a new write phase.

### §8.4 [v6] Retrieval diagnostics are lifted — don't nest

**Rule (phase 1, 2026-04-24).** The nine v6-lifted diagnostic fields (`primary_article_count`, `connected_article_count`, `related_reform_count`, `seed_article_keys`, `planner_query_mode`, `tema_first_mode`, `tema_first_topic_key`, `tema_first_anchor_count`, `retrieval_sub_topic_intent`, `subtopic_anchor_keys`) must stay at the top level of `response.diagnostics`. Any new retrieval-diagnostic field from a retriever (`retriever.py`, `retriever_supabase.py`, `retriever_falkor.py`) must also be lifted, with a matching entry in `tests/test_orchestrator_diagnostic_surface.py::_LIFTED_KEYS`.

**Why.** The v5 30Q A/B panel drew wrong conclusions because the harness read these fields from top-level while they lived nested — `None` everywhere, panel said "retrieval broken." See `docs/learnings/retrieval/diagnostic-surface.md`.

---

## §9 Cross-cutting conventions

### §9.1 Bogotá AM/PM for user-facing time

**Rule.** Every timestamp the operator sees is rendered as `America/Bogota` (UTC-5, no DST) 12-hour with AM/PM. Machine logs (events.jsonl, DB columns) stay UTC ISO.

**Code pointer.** `scripts/monitoring/ingest_heartbeat.py::bog_time`.

### §9.2 Verbose folder / file names

**Rule.** Sub-folders holding tools get **descriptive** names (`monitor_ingest_topic_batches/`, `monitor_sector_reclassification/`) rather than generic ones (`batch_pipeline/`, `classifier/`). Scripts live in the folder whose name matches their job. The next contributor should find the right file without a tour.

**Context.** The user explicitly called out "finding a needle in a haystack" as a recurring pain point during v3. Verbose names traded keystrokes for discoverability; the trade stays.

### §9.3 Every non-trivial script has a sibling README

**Rule.** If a script does more than 50 lines of orchestration, its folder carries a README explaining:
- What the script is for.
- How it fails and how to retry.
- Where its inputs come from and where its outputs go.
- What NOT to do (anti-patterns captured from past incidents).

### §9.4 Stage files explicitly, never `git add -A`

**Rule.** Commit specific file paths. `-A` has twice (v2 cleanup + v3 reorg drafts) nearly staged `.env.local` backups, runtime logs the gitignore didn't match, and local Supabase cache files. Not worth the keystrokes.

**Exception.** Fresh repos have no history worth protecting; `-A` is acceptable on the very first commit of a greenfield folder.

---

## §10 Pointers into the authoritative incident records

These files are where the raw triage + decisions were captured in real time. If a learning above feels abstract, the corresponding § in the source file has the full story.

| Learning theme | Canonical source |
|---|---|
| Detached-launch + tee-pipe SIGHUP | `docs/next/ingestionfix_v2.md §7 run_log_2026_04_23` (attempts 1-3) |
| PostgREST size limits + SQLSTATE 21000 | `docs/next/ingestionfix_v2.md §7` + `tests/test_dangling_store.py` lessons |
| Graph schema required_fields | `docs/next/ingestionfix_v2.md §7` + `src/lia_graph/graph/schema.py` |
| Banner VM field path | `docs/next/ingestionfix_v2.md §4 Phase 11` + v3 Phase 1 fix |
| Size estimates vs live probes | `docs/next/ingestionfix_v3.md §2.1` |
| Catch-all bucket hazards | `docs/next/ingestionfix_v3.md §2.2` |
| Durability contract / resumable batches | `docs/next/ingestionfix_v3.md §5 Phase 3` + `scripts/launch_batch.sh` header |
| Heartbeat design | `scripts/monitoring/README.md` + `scripts/monitoring/ingest_heartbeat.py` + `docs/learnings/process/heartbeat-monitoring.md` |
| Fingerprint as partial-completion guard | `docs/next/ingestionfix_v2.md §7 run_log_2026_04_23.lessons_learned` |
| **[v6]** Parallel classifier design | `docs/learnings/ingestion/parallelism-and-rate-limits.md` + commit `34f658b` |
| **[v6]** Parallel Supabase sink | `docs/learnings/ingestion/supabase-sink-parallelization.md` + commit `602fbb4` |
| **[v6]** Falkor bulk-load hardening | `docs/learnings/ingestion/falkor-bulk-load.md` + commit `deb71d2` |
| **[v6]** Diagnostic lift | `docs/learnings/retrieval/diagnostic-surface.md` + commit `7d966ce` |
| **[v6]** Cloud-sink env posture | `docs/learnings/process/cloud-sink-execution-notes.md` |
| **[v6]** Post-execution retrospective | `docs/next/ingestion_tunningv2.md §16 Appendix D` |

---

## §11 "Rescue-from-Other" playbook — every ingestion, every reingest

**Context.** Colombian legal corpora always produce a catch-all bucket (`otros_sectoriales`, `varios`, `otros`, etc.) because the taxonomy covers the ~40 core accounting topics accountants actually work with. Anything outside that (health, education, agriculture, culture, utilities, etc.) lands in the catch-all. In our 2026-04-23 probe, `otros_sectoriales` ate 39% of the classified corpus (510 of 1,319).

Left alone, that catch-all becomes a permanent `TopicNode` in Falkor with hundreds of generic TEMA edges — useless for retrieval.

**Rule.** Every regular ingestion AND every reingest-from-raw must run the Rescue-from-Other pipeline as a **standard post-sink step**. It is not an opt-in; it is the default. Skipping it requires a written justification in the PR description.

**The three-pass pipeline (battle-tested on 2026-04-23; 216 of 242 noisy docs rescued into real buckets = 89% rescue rate; total Gemini cost $0.037 for 510 docs):**

### §11.1 Trigger conditions

Launch the rescue pipeline when ANY of these is true after a sink completes (either full-rebuild or additive):

| Trigger | Threshold | Why |
|---|---|---|
| **Any single `tema` holds >5% of live corpus** | 5% of `count(documents WHERE retired_at IS NULL)` | Indicates a bucket absorbing taxonomy gaps. 5% chosen because the next-largest named topic historically tops out at 6-7% (`declaracion_renta`). |
| **`tema='otros_sectoriales'` absolute count > 100** | 100 | Hard floor. Regardless of %, a >100-doc catch-all is worth a pass. |
| **New corpus documents added** | any | A reingest that adds content may reveal new sectors the first pass missed. |
| **Taxonomy change that removes a topic** | any | Retired topics leave dangling docs — flush them into proper buckets. |

Automated check to gate ingestion completion (should be wired into the admin UI's post-sink "health check" panel):

```sql
SELECT tema, count(*) AS n,
       round(100.0 * count(*) / (SELECT count(*) FROM documents WHERE retired_at IS NULL), 1) AS pct
FROM documents WHERE retired_at IS NULL
GROUP BY tema HAVING count(*) > 100 OR
       count(*) > 0.05 * (SELECT count(*) FROM documents WHERE retired_at IS NULL)
ORDER BY n DESC;
```

Any row returned ⇒ rescue pass required. UI surfaces a yellow banner: *"Rescue-from-Other pending for topic(s): X (Y docs, Z%). Run the sector-classify pipeline before closing this ingestion."*

### §11.2 Pass 1 — loose prompt (discovery)

Goal: surface the shape of what's in the catch-all. Allow the LLM to pick among three options:

1. Migrate to one of N existing named topics.
2. Propose a new sector (`sector_*` label, free-form).
3. Mark as orphan.

**Batched** at 20 docs/call. **Per-batch atomic checkpoint** so a failure only costs one batch of work. Visible heartbeat after every batch (progress bar, ETA, running cost estimate, top proposed new sectors, top migrate-to targets). **Resumable** on interrupt (SIGINT flips in-flight batch to `status=interrupted`; resume retries only that slice).

**Canonical tool:** `scripts/monitoring/monitor_sector_reclassification/sector_classify.py`

**Expected noise on pass 1:** the loose prompt will often accept "migrate to the catch-all itself" as an answer (the LLM's shortcut for "leave it alone"). In our run that was 47% of outputs. Pass 2 fixes this.

### §11.3 Pass 2 — strict retry on the noise (escalation)

Goal: force the LLM to give a real answer for docs the loose pass dumped back into the catch-all.

**Extract** the doc_ids the loose pass labelled `migrate → <catch-all>`. **Re-run** the same tool with `--exclude-migrate-topics <catch-all>` which:

- Removes the catch-all from the OPCIÓN-1 migrate list the LLM sees.
- Adds a `PROHIBIDO` warning in the prompt.
- Adds `Si dudas entre OPCIÓN 2 y OPCIÓN 3, elige OPCIÓN 2` (prefer new sector over orphan when sectorial content is ambiguous).

**Expected rescue rate:** 85-90% of noisy docs move into real buckets (~42% migrate to existing topics, ~48% propose new sectors, ~5% explicit orphan, ~15-20% disguised `sector_otros*` loophole).

**Output:** a second aggregate proposal at `artifacts/sector_classification_strict/sector_reclassification_proposal.json`.

### §11.4 Pass 3 — rich per-doc rescue for residual orphans

Goal: close out the remaining 10-15% that the strict pass couldn't place (true orphans + disguised-catch-all labels like `sector_otros`).

**Per-doc call**, not batched — each of these docs gets the full proposed taxonomy (39 existing + ~30 newly-proposed sectors from pass 2) as a closed-world list, plus a richer prompt:

> *"¿De qué trata principalmente este documento? ¿Encaja en alguna de las N categorías listadas? Si no encaja en ninguna, ¿cómo lo categorizarías tú?"*

**Model selects** from the closed list OR proposes a final new-sector label with reasoning. Per-doc context makes this more accurate than the batched pass for hard cases.

**Canonical tool** (to build): `scripts/monitoring/monitor_sector_reclassification/classify_orphans.py`.

**Expected cost:** $0.0003-0.0005 per doc × ~80 docs ≈ $0.03-0.05 total. Negligible compared to the retrieval quality we get back.

### §11.5 Operator gates

**Pass 1 + Pass 2 + Pass 3 produce proposals — they do not mutate anything.** Before any `documents.tema` UPDATE fires:

1. **Operator reviews the proposal** in a diff-friendly view (doc_id, current_tema, proposed_tema, confidence, reasoning).
2. **Operator merges raw sector labels into canonical ones.** The LLM produced 187 raw labels in our run; operator collapsed them to ~30 canonical sectors in ~20 minutes. Build a merge-map script that takes the raw proposal + an operator-edited `merge_map.yaml` and emits the canonical proposal.
3. **Operator approves** via signed manifest: checksum + `approved_by` + `approved_at` + `plan_version_expected` fields in the approved-proposal file.
4. **Only the approved file is valid input** to the apply script. Raw proposals refuse at the `.approved.json` extension check.

This pattern mirrors the Phase 3.0 Quality Gate in `ingestionfix_v3`: automation produces the evidence; a human signs the go/no-go.

### §11.6 Apply step — it's a `fingerprint_bust` + `tema` UPDATE

**The apply step is NOT a delete-and-recreate.** Two writes per doc:

```sql
UPDATE documents
   SET tema = '<new_topic>', doc_fingerprint = NULL
 WHERE doc_id = $1;
```

Nulling the fingerprint ensures the next additive reingest regenerates chunks + TEMA edges under the new topic. Same `fingerprint_bust` durability contract applies (safety rails, manifest-before-execute, atomic batched writes).

**Canonical tool** (to build): `scripts/monitoring/monitor_sector_reclassification/apply_sector_reclassification.py`.

### §11.7 Post-rescue validation (required)

After apply completes, run a **post-rescue tema-distribution re-probe**:

```bash
python scripts/monitoring/monitor_sector_reclassification/probe_tema_distribution.py
```

**Acceptance:**
- Catch-all topic count drops from pre-rescue N to ≤5% of corpus OR ≤100 absolute docs — whichever the trigger in §11.1 used.
- No new topic exceeds the 5% threshold (otherwise that topic needs its own rescue pass).
- Every new canonical sector has an entry in `config/topic_taxonomy.json` with `vocabulary_status: ratified_v<N>`.
- No `documents.tema` values reference a key that doesn't exist in the taxonomy (orphan-tema check).

### §11.8 UI surface — where this shows up

For the future admin UI that triggers ingestion:

- **Pre-ingest panel:** shows the current tema histogram (visible warning if any bucket >5% or >100).
- **Post-sink panel:** if trigger hit, yellow banner + "Run Rescue-from-Other" button that fires the three-pass pipeline.
- **Rescue progress panel:** heartbeat from `sector_classify.py` streamed live (progress bar + ETA + sector histogram growing).
- **Review panel:** proposal diff viewer (sortable by confidence, by doc count per proposed topic, by migration target).
- **Apply button:** gated on a signed approved-proposal file; shows the manifest path before + after.

### §11.9 Budget expectations (from 2026-04-23 production run)

| Pass | Docs | Wall time | Gemini cost |
|---|---|---|---|
| Pass 1 (loose, 510-doc catch-all) | 510 | ~10 min | $0.019 |
| Pass 2 (strict, 242 noisy) | 242 | ~5 min | $0.018 |
| Pass 3 (rich per-doc, 80 orphans est.) | ~80 | ~3 min | ~$0.04 |
| **Total** | **510 docs** | **~18 min** | **~$0.08** |

Well under any reasonable budget. The cost scales linearly with catch-all size; a 5,000-doc catch-all would be ~$0.80 — still cheap insurance against a permanent retrieval-quality regression.

### §11.10 What this prevents

The ingestion-time classifier (prefix/alias map in `config/prefix_parent_topic_map.json` + `src/lia_graph/ingest_classifiers.py`) is rule-based and WILL miss edge cases — especially for Colombian laws whose titles don't match any configured prefix pattern. Our 2026-04-23 probe found 106 such misclassifications across 39 topics (Ley 1066 cartera pública, Ley 1527 libranzas, Ley 1121 anti-terrorism financing, etc. — all dumped into the catch-all by the rule-based pass).

Without the Rescue pipeline these stay miscategorized until someone notices an accountant asking a labor question and not getting Ley 1527. The pipeline catches them automatically on every reingest — a **self-healing taxonomy layer** on top of the rule-based classifier.

Follow-up **F7** (see `docs/next/ingestionfix_v3.md §8`) covers extending the classifier's prefix/alias map so future Colombian laws don't keep landing in the catch-all for the same reasons — that's the LONG-term fix; the Rescue pipeline is the SHORT-term always-on net.

---

## §12 Good news — v6 wins the UI already inherits

These CLI-side hardenings automatically propagate to the UI because the UI spawns the same `lia_graph.ingest` CLI as a subprocess and inherits the argparse defaults. Do NOT need remediation; just verify they stay that way.

| v6 win | How UI inherits it |
|---|---|
| **Parallel classifier (phase 2a)** | `argparse.default=8` in `--classifier-workers`. Subprocess call via `make` omits the flag; CLI default fires. ✅ |
| **Parallel Supabase sink (phase 2b)** | Same mechanism — `--supabase-workers` defaults to 4. ✅ |
| **Rate-limit 300 RPM default** | `--rate-limit-rpm` default changed from 60 → 300 in the CLI. UI picks this up. ✅ |
| **Falkor query-timeout + batch sizes (phase 2c)** | `FALKORDB_QUERY_TIMEOUT_SECONDS=30`, `FALKORDB_BATCH_NODES=500`, `FALKORDB_BATCH_EDGES=1000` via env defaults. ✅ |
| **Diagnostic lift (phase 1)** | UI progress endpoint reads `response.diagnostics` from the same dict structure as the A/B harness. Lifted fields are at top level. ✅ (needs verification — see §13.5) |
| **Coherence gate + citation allow-list** | Retrieval-side, not ingest-side. Not applicable. ✅ |

---

## §13 Deficiencies vs. the v6 CLI hardening

**Audit date:** 2026-04-24 · **Scope:** places where GUI-triggered ingest is less safe, less observable, less tunable, or less resilient than the CLI path. Ranked by priority.

### §13.1 [P0] No `--allow-non-local-env` in the Makefile target

**Deficiency.** `Makefile:139` defines `PHASE2_SUPABASE_SINK_FLAGS = --supabase-sink --supabase-target $(PHASE2_SUPABASE_TARGET) --execute-load --allow-unblessed-load --strict-falkordb`. **No `--allow-non-local-env`.** The CLI's env-posture guard in `src/lia_graph/env_posture.py` aborts any run where `SUPABASE_URL` / `FALKORDB_URL` come from a non-local source unless that flag is passed.

**What this means for the UI.** Whether the UI-triggered ingest succeeds depends entirely on whether the web server's boot env already carries the cloud creds. In `npm run dev:staging` mode, the dev-launcher loads `.env.staging` so the env is present and the guard happily sees "local-sourced env." In production (Railway), the env comes from Railway's secret store, which the posture guard may or may not detect as "local." The first time this surfaces, it'll be mid-run failure with a cryptic "env_posture" message in the UI log tail.

We hit this exact class of failure during v6 cloud-sink execution on 2026-04-24 (the CLI form needed `set -a; source .env.staging; set +a` + `--allow-non-local-env`). See `docs/learnings/process/cloud-sink-execution-notes.md`.

**Fix.** Add `--allow-non-local-env` to `PHASE2_SUPABASE_SINK_FLAGS` when `PHASE2_SUPABASE_TARGET=production`:

```make
PHASE2_SUPABASE_SINK_FLAGS = --supabase-sink --supabase-target $(PHASE2_SUPABASE_TARGET) \
    --execute-load --allow-unblessed-load --strict-falkordb \
    $(if $(filter production,$(PHASE2_SUPABASE_TARGET)),--allow-non-local-env,)
```

Roughly +1 LOC. Regression-safe: only fires on the `production` target.

### §13.2 [P0] UI observability is stdout-log tail, not events.jsonl

**Deficiency.** `ui_ingest_run_controllers._tail_job_log` (line 357) polls `artifacts/jobs/ingest_runs/ingest_<stamp>.log` for progress. That log is `subprocess.run(..., stdout=log_fh, stderr=subprocess.STDOUT)` — a free-text stream, subject to all five failure modes in `docs/learnings/process/heartbeat-monitoring.md` (Spanish-legal-text false positives, hidden degradation, etc.).

**Fix.** Replace/supplement with an `events.jsonl`-anchored progress endpoint:

```
GET /api/ingest/job/{id}/progress
→ {
  "phase": "classifier" | "bindings" | "load_existing_tema" | "sink" | "falkor" | "done",
  "classifier": {"total": 1275, "classified": 830, "failed": 0, "degraded": 114, "rpm": 305},
  "events_stale_seconds": 3,
  "dep_health": {"supabase": {...}, "falkor": {...}},
  "last_event_ts_utc": "2026-04-24T17:30:00+00:00"
}
```

+150 LOC in a new controller.

### §13.3 [P1] 1-hour subprocess timeout is too tight post-v6

**Deficiency.** `ui_ingest_run_controllers._spawn_ingest_subprocess` line 462: `timeout=60 * 60`. Post-v6 corpus total wall time is 22–37 min baseline, with TPM-pressure retry waits adding up to 45 min. Kills mid-sink.

**Fix.** Raise `timeout=` to `90 * 60` (90 min) for the non-chained path, `120 * 60` (2h) for `scripts/ingest_run_full.sh` (which includes embeddings). Emit timeout into a distinct UI state ("timed out — run may have landed partial cloud writes, click resume").

+5 LOC.

### §13.4 [P1] No UI exposure of the new worker / rate knobs

**Deficiency.** The frontend does not pass any of `--classifier-workers N`, `--supabase-workers N`, `--rate-limit-rpm N`. Backend spawner doesn't accept them either. Admin has no per-run tuning.

**Fix.** "Advanced options" expando in the ingest-trigger dialog exposing the three knobs, all defaulting to CLI defaults. Backend pass-through:

```python
env["LIA_INGEST_CLASSIFIER_WORKERS"] = str(classifier_workers or 8)
env["LIA_SUPABASE_SINK_WORKERS"] = str(supabase_workers or 4)
env["LIA_INGEST_CLASSIFIER_RPM"] = str(rate_limit_rpm or 300)
```

+20 LOC backend + a form field in the frontend.

### §13.5 [P1] UI doesn't surface degradation count to the operator

**Deficiency.** v6 cloud-sink classifier pass emitted 92–114 tracebacks (TPM-429s caught by inner try/except → N1-only degraded verdicts). Pool reported `failed=0`. UI has no way to tell the operator ~7% of docs landed with `requires_subtopic_review=True`.

See `docs/learnings/process/cloud-sink-execution-notes.md` + heartbeat failure mode #4.

**Fix.** Progress endpoint from §13.2 includes:
```json
"classifier": {
  "total": 1275, "classified": 1275,
  "failed_hard": 0, "degraded_n1_only": 114, "degraded_pct": 8.9
}
```

End-of-run UI toast: "Run complete. 114 of 1,275 docs landed with degraded classification (N1-only). Cause: Gemini TPM backpressure. Re-run to refine." +30 LOC.

### §13.6 [P2] No pre-flight dep health check before spawning

**Deficiency.** `_spawn_ingest_subprocess` goes straight to `subprocess.run` without checking whether Gemini / Supabase / Falkor are reachable. If Supabase is down, ingest burns ~7 min of classifier + binding work before failing at the sink boundary.

**Fix.** Call `scripts/monitoring/dep_health.py` as a pre-flight step:

```python
health = subprocess.run(
    ["uv", "run", "python", "scripts/monitoring/dep_health.py",
     "--probe", "supabase", "--probe", "gemini", "--probe", "falkor"],
    capture_output=True, timeout=30, env=env,
)
if health.returncode != 0:
    return {"ok": False, "error": "dep_unhealthy", "detail": health.stdout.decode()}
```

+15 LOC.

### §13.7 [P2] No artifact-coherence snapshot before rebuild

**Deficiency.** `docs/learnings/ingestion/artifact-coherence.md`: the artifact files are a set, produced and consumed together. A mid-run failure leaves them in an incoherent state (orchestrator falls through to `compat_stub` path with broken diagnostics).

**Fix.** Pre-run, snapshot all `artifacts/*.json` + `artifacts/*.jsonl` into `artifacts/.snapshots/<timestamp>/`. Post-run, if `PHASE2_SINK_EXIT != 0`, offer the UI operator a one-click "restore pre-run snapshot" button. Prune snapshots older than 3 runs.

+50 LOC.

### §13.8 [P2] Additive delta path DOES pass `classifier_workers` but NOT `supabase_workers`

**Deficiency.** Commit `602fbb4` added `classifier_workers=deps.get("classifier_workers")` to `ui_ingest_delta_controllers.py` line 129. It does NOT add `supabase_workers=deps.get("supabase_workers")`. Delta flow silently falls back to the env var or default.

**Fix.** Add one line:

```python
"supabase_workers": deps.get("supabase_workers"),
```

+1 LOC.

### §13.9 [P3] No UI signal that `--skip-llm` was NOT used

**Deficiency.** `ui_ingest_run_controllers` line 920 uses `skip_llm=True` for the **intake-time** classifier. A future contributor might copy that pattern into the full-ingest spawner.

**Fix.** Emit `ingest.llm_mode` event with `{"skip_llm": false, "classifier_rpm_cap": 300, "workers": 8}` at start of each run. UI surfaces it.

+5 LOC.

### §13.10 [P3] Ingest env vars missing from orchestration matrix

**Deficiency.** `docs/guide/orchestration.md` §Env-v2026-04-22-ac1 lists all `LIA_*` flags for the served runtime. Ingest-side flags are not there. Production operators tuning the UI runtime have to grep.

**Fix.** Add an "Ingest-pipeline env vars" subsection including `LIA_INGEST_CLASSIFIER_RPM`, `LIA_INGEST_CLASSIFIER_WORKERS`, `LIA_SUPABASE_SINK_WORKERS`, `FALKORDB_QUERY_TIMEOUT_SECONDS`, `FALKORDB_BATCH_NODES`, `FALKORDB_BATCH_EDGES`.

+30 lines of docs.

### §13.11 [P3] No tests for UI→subprocess env propagation

**Deficiency.** We don't test that env vars on the UI web server are inherited by the spawned `make` subprocess and its Python child. A future refactor could silently drop overrides.

**Fix.** `tests/test_ui_ingest_subprocess_env.py`: monkeypatch `subprocess.run`, assert `env` arg contains all ingest knobs (classifier / supabase / rpm / falkor).

+30 LOC.

### §13.12 [P1] Phase-2c Falkor knobs not exposed to UI

**Deficiency.** Phase 2c added `FALKORDB_QUERY_TIMEOUT_SECONDS`, `FALKORDB_BATCH_NODES`, `FALKORDB_BATCH_EDGES`. No UI override, same gap as §13.4.

**Fix.** Extend the same "Advanced options" expando from §13.4 with the three Falkor knobs. +15 LOC.

### §13.13 [P2] No UI progress signal for `graph.batch_written` events

**Deficiency.** Phase 2c's batched Falkor loader **could** emit `graph.batch_written` events per successful batch. Current code executes batches via `GraphClient.execute` but doesn't yet emit these per-batch events.

**Fix.** +10 LOC in `src/lia_graph/graph/client.py` — emit from `_execute_live_statement` after a successful decode. UI progress aggregator reads it.

### §13.14 [P1] Env posture guard doesn't validate Falkor schema invariants

**Deficiency.** The guard checks env vars are set. It does NOT check that the Falkor graph has the 6 required indexes (from phase 2c) before a bulk load. Without them, the first MERGE does a full label scan → pre-phase-2c stall pattern.

**Fix.** Add pre-flight step to `_spawn_ingest_subprocess`:

```python
# Before ingest: ensure indexes exist (idempotent, ~2s)
GraphClient.from_env().execute_many(
    GraphClient(schema=...).stage_indexes_for_merge_labels(),
    strict=True,
)
```

+20 LOC.

### §13.15 [P2] UI has no "Falkor is stuck — kill it" button

**Deficiency.** During the 2026-04-24 stall, CLI path could `kill <pid>` to abort. UI path has "cancel subprocess" but NO way to send `CLIENT KILL` to Falkor cloud.

**Fix.** "Kill Falkor query" button that opens a sibling Redis connection, runs `CLIENT LIST TYPE normal`, filters `cmd=graph.query`, offers `CLIENT KILL ID <id>`. Phase 2c's TIMEOUT clause should make this rare — still worth having as a recovery path.

+80 LOC.

### §13.16 Summary + sequencing

| # | Priority | Gap | Est. diff |
|---|---|---|---|
| 13.1 | **P0** | Makefile missing `--allow-non-local-env` | +1 LOC |
| 13.2 | **P0** | Stdout-tail is wrong observability surface | +150 LOC |
| 13.3 | P1 | 1h subprocess timeout too tight | +5 LOC |
| 13.4 | P1 | No UI exposure of worker/RPM knobs | +20 LOC |
| 13.5 | P1 | No degradation count surfaced | +30 LOC |
| 13.6 | P2 | No pre-flight dep health check | +15 LOC |
| 13.7 | P2 | No artifact-coherence snapshot | +50 LOC |
| 13.8 | P2 | `supabase_workers` missing from delta deps | +1 LOC |
| 13.9 | P3 | No `ingest.llm_mode` confirmation event | +5 LOC |
| 13.10 | P3 | Ingest env vars missing from orchestration matrix | docs |
| 13.11 | P3 | No UI→subprocess env propagation test | +30 LOC |
| 13.12 | P1 | Phase-2c Falkor knobs not UI-tunable | +15 LOC |
| 13.13 | P2 | `graph.batch_written` events not emitted | +10 LOC |
| 13.14 | P1 | Env posture guard doesn't ensure Falkor indexes | +20 LOC |
| 13.15 | P2 | No UI "kill stuck Falkor query" button | +80 LOC |

**Total: ~510 LOC across ~9 files + docs.** Sequenceable as 3 PRs: P0s together (§13.1 + §13.2), P1s together (§13.3 + §13.4 + §13.5 + §13.12 + §13.14), P2s+P3s as individual small PRs.

### §13.17 Success criteria for a remediation plan (v2 of this doc)

A v2 should prove via a GUI-driven run that:

1. Admin triggers full ingest via UI against production Supabase, inheriting v6 defaults without manual env setup.
2. UI progress panel distinguishes `classifier` / `bindings` / `load_existing_tema` / `sink` / `falkor` phases with per-phase counters + stale-events indicator.
3. UI surfaces degradation count, dep-health status, honest ETA.
4. Mid-run timeout (forced via `sleep 3700` in fake subprocess) reaches user as "timed out, may be partial" not "failed."
5. Post-run, a run with 92+ tracebacks shows as "WARN: 7% degraded, consider re-run" — not silent success.
6. Falkor indexes verified before ingest starts (no quadratic MERGE regressions possible).

---

## §14 When to update this file

- After any ingestion bug that bites us in production. Add §N with the incident + the rule that prevents it.
- After any PR review where a reviewer had to re-explain one of the rules above (signals the rule needs a stronger test or docs presence).
- After any architecture decision that narrows or broadens the scope of UI ingestion.
- When the deficiencies in §13 are remediated — move the closed item into the regular rule sections above and mark it [v6-remediated] with commit SHA.

**Do NOT** update this file to capture temporary state of an in-progress fix. That belongs in the fix's plan doc. This file is for learnings that have **earned their place by surviving a full triage cycle**.

---

*Merged 2026-04-24 from `UI_Ingestion_learnings.md` (v3 Phase 2.5 2026-04-23) + `deficienciesGUIingestion_v1.md` (v6 audit 2026-04-24). Last v6 update: commit `deb71d2` (phase 2c Falkor hardening).*
