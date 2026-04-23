# UI Ingestion Learnings — don't re-commit v1/v2/v3 mistakes

*Living doc. One page per surface. Every rule earns its place by naming
the incident that created it. Adding a new learning? Cite the commit or
the §-reference in `docs/next/ingestionfix_v{1,2,3}.md` that produced it.*

**Scope.** The **browser-facing ingestion flow** — `frontend/src/features/ingest/` +
`src/lia_graph/ui_ingestion_controllers.py` + the admin surfaces on
`/ingest` that trigger long-running reingest jobs — and every UI we'll
build in the future that invokes `src/lia_graph/ingestion/*`. Not
scoped: the headless pipeline itself (that's covered inside each
ingestionfix plan).

**Why this doc exists.** Between 2026-04-21 and 2026-04-23 we shipped
three ingestion-fix waves. Each wave resolved a distinct class of
failure. The next UI feature that touches ingestion is one careless
code review away from bringing any of those failures back — because
the fixes live in pipeline code, not in a doc the next contributor
will read. This file is that doc.

**How to use.**
1. Before building a UI that triggers ingest, skim §1 (the one-pagers).
2. If you're modifying an existing ingest surface, find the matching §
   and use its checklist as PR bar.
3. When a new class of mistake surfaces, add a §N here with the rule +
   the incident that motivated it.

---

## §1 The 10-point pre-flight checklist

Stick this at the top of every PR description that touches UI ingestion.

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

---

## §2 Banner / terminal-state rendering

### §2.1 Never trust the envelope — read the slice

**Incident (v2 Phase 11, 2026-04-23).** Every successful additive-delta
run rendered `0 / 0 / 0` in the terminal banner because
`additiveDeltaController.ts` passed `ev.reportJson` wholesale to the VM.
The backend nests per-sink counters under `report_json.sink_result`, so
`vm.report.documents_added` was always undefined.

**Rule.** When surfacing counters / counts / identifiers from a job
report, read the NESTED slice the backend writes, not the envelope.
The envelope is a transport frame; the slice is the data.

**How to prevent the regression.** 
* `frontend/tests/additiveDeltaControllerTerminalVm.test.ts` locks the
  wire contract; any change to the VM shape or the backend
  `DeltaRunReport` must update both sides + this test.
* `buildAdditiveDeltaTerminalVm()` is the seam — keep it pure + unit-tested.
* For any new banner, add a test that asserts the VM does NOT carry
  envelope-only fields (belt-and-suspenders — catches the next wholesale-pass bug).

**Code pointer.** `frontend/src/features/ingest/additiveDeltaController.ts` seam.

---

## §3 Progress / heartbeat surfaces

### §3.1 Read `logs/events.jsonl`, not `--json`

**Incident (v2 9.A attempt #1).** The launcher's stdout was piped
through `tee`; SIGHUP killed tee; the Python process got SIGPIPE
mid-classification; no summary was written. The UI was waiting on the
`--json` summary that never arrived.

**Rule for UI.** Progress indicators must read `logs/events.jsonl` (one
event per line, flushed per-event). The summary JSON is for post-mortems,
not for live progress.

**Code pointer.** `scripts/monitoring/ingest_heartbeat.py` is the
canonical event-anchored progress reader. Any UI heartbeat should
follow the same event-schema contract (ts_utc, event_type, payload).

### §3.2 Silence is phase-aware, not a stall signal

**Incident (v2).** During `sink_writing` and `falkor_writing`, the
classifier emits no per-item events — only a single `start/done` pair.
A UI that assumed "no events for 3 minutes = stalled" would show a
false positive for 5+ minutes on every run.

**Rule.** Phase-aware stall detection. Only `classifying` ticks
continuously; `sink_writing`, `falkor_writing`, `post_sink`,
`finalizing` all have legitimately quiet phases. The UI should show
the phase name + verdict alongside the heartbeat, not just "no events
recently."

**Code pointer.** `scripts/monitoring/ingest_heartbeat.py::infer_phase`
+ the per-phase verdict strings in `render()`.

### §3.3 Heartbeat during chain mode — chain progress + total ETA

**Incident (v3 Phase 2).** The autonomous chain (batches 2-8) was
silent mid-batch. Operator had no visibility into total chain progress.

**Rule.** When a UI surfaces a chain of batches, the heartbeat prepends
**Chain progress** (N/M done) + **Total ETA** (derived from average
completed-batch wall time) rows above per-batch details.

**Code pointer.** `scripts/monitoring/ingest_heartbeat.py::ChainState`
(reads `artifacts/backfill_state.json`).

---

## §4 Destructive operations

### §4.1 Always `--dry-run` first

**Incident (v3 Phase 2.1).** The shipped `plan.json` estimated batch 1
at 20 docs. A dry-run against production Supabase reported 552. Running
without a dry-run would have wasted 30+ min of classifier wall time +
locked 552 docs' fingerprints we didn't intend to touch.

**Rule for UI.** Any production-mutating action has a **two-step flow**:
1. `--dry-run` (button: "Previsualizar"): SELECT-only, renders the
   affected-row count + sample rows.
2. `--confirm` (button: "Ejecutar"): locked behind the dry-run, only
   unlocks after the operator sees the preview.

**Code pointer.** `fingerprint_bust.py` models this; the additive-delta
"Previsualizar → Aplicar" flow in `additiveDeltaController.ts` is the
UI pattern.

### §4.2 Row-count threshold — visible warning

**Rule.** If an operation would mutate >200 rows, the UI shows a
yellow warning with the exact count ("Mutarás 552 documentos") and
requires an additional checkbox confirm.

**Why 200.** PostgREST `.in_()` URL-length limit (v2 Phase 9.A crash #1)
+ the soft threshold codified in `fingerprint_bust.py::DEFAULT_SAFETY_THRESHOLD`.

### §4.3 Manifest-before-execute

**Rule.** Every destructive action writes an audit manifest
(`artifacts/<op>/<ts>_<tag>.json` — doc_ids, topics, timestamps,
flags used) BEFORE the UPDATE / DELETE fires. The UI surfaces the
manifest path in the result block so the operator can audit after a
crash.

**Why.** v2 Phase 9.A crash #2 left the sink half-written; we had no
audit trail of what was attempted. Manifest-before-execute is the
invariant that made retry safe.

---

## §5 Reclassification + fingerprint work

### §5.1 Never `--force-full-classify` from the UI

**Incident (v2 9.A).** Each `--force-full-classify` pass is ~40 min of
classifier wall time on 1,280 docs. We paid that cost 4× on 2026-04-23
because the flag bypasses the fingerprint shortcut.

**Rule for UI.** `--force-full-classify` is NEVER offered as a button.
The UI offers topic-scoped `fingerprint_bust` instead. If the operator
genuinely wants a full reclassify, they run it from the CLI with all
the attention costs that entails — not one misclick from a UI button.

**Code pointer.** `scripts/monitoring/monitor_ingest_topic_batches/fingerprint_bust.py`
+ `scripts/launch_batch.sh`.

### §5.2 Cross-batch isolation is the default, not an option

**Rule.** Any UI reclassify action filters by the topic / sector / tag
the operator selected. It is STRUCTURALLY INCAPABLE of touching rows
outside that filter. No "apply to all" override ships; if one is ever
needed, it's a CLI-only escape hatch.

**Why.** v3's durability contract depends on prior batches being
untouchable once committed. An "apply to all" UI button breaks that
contract.

### §5.3 Fingerprint bust is a `NULL` UPDATE — not a DELETE

**Rule.** When the UI exposes a "retry this doc" action, under the
hood it nulls `doc_fingerprint`; the next additive run does the actual
reclassify + re-sink. UI must NEVER directly delete `documents` /
`document_chunks` / `normative_edges` rows.

**Why.** v2 established that the additive path is idempotent on
doc_id. A mid-stream DELETE breaks downstream edge-reattachment logic
(dangling_store promotion depends on target article keys being
stable).

---

## §6 Batch / chain semantics

### §6.1 Estimates from static config lie — probe live

**Incident (v3 §2.1).** The v3.0 seed `plan.json` sized batches from
the taxonomy file. A live probe showed 2-27× drift. Batch 1's
`otros_sectoriales` was 510 docs, not the 20 estimated.

**Rule.** Any UI that shows "this will affect ~N documents" derives N
from a live SELECT against Supabase at render time, NOT from a static
config / cached count / plan file. Show both the estimate and the
source ("live probe at 3:42 PM").

### §6.2 Catch-all buckets are booby traps

**Rule.** If a UI lets the operator pick a topic filter, dynamically
warn when the selected topic has >5% of the total corpus ("Este topic
cubre el 39% del corpus; considera dividirlo"). Prevents
`otros_sectoriales`-class accidents.

### §6.3 Durability contract surfaced in UI

**Rule.** Any UI that kicks off a multi-batch operation displays the
durability contract in the "what will happen" copy:

> Si un lote falla, los anteriores permanecen guardados. Solo el
> lote fallido debe reintentarse.

This is user-facing trust-building — accountants stop panicking when
they see this and a batch fails.

**Code pointer.** `scripts/launch_batch.sh` header + the batch_pipeline
README mirror this contract verbatim; UI should reuse the same wording.

---

## §7 Testing bar

### §7.1 Fakes must be strict, not lenient

**Incident (v2 Phase 9.A crash #2).** The `_FakeClient` in
`test_dangling_store.py` silently accepted duplicate upsert payloads,
masking the SQLSTATE 21000 bug that later crashed production.

**Rule.** Fakes in ingestion tests reject the exact failure modes
production rejects:

* Upsert with intra-payload duplicates on the conflict key → raise
  `RuntimeError("SQLSTATE 21000")`.
* `.in_()` with >200 keys → raise a URL-length error.
* `.upsert()` with >500 rows → raise a body-size error.

### §7.2 Wire-contract tests lock backend↔UI field paths

**Rule.** For every piece of backend data the UI consumes, a test
locks the shape. The contract can evolve; the test forces both sides
to change together.

**Canonical examples.** 
* `frontend/tests/additiveDeltaControllerTerminalVm.test.ts`
  (backend `DeltaRunReport.sink_result` ↔ UI `vm.report`).
* `tests/test_supabase_sink_delta.py` (sink result shape).

### §7.3 Shell-script ingestion helpers get shell-out tests

**Rule.** Every `.sh` supervisor / launcher has a pytest-harnessed test
that asserts exit codes + stderr wording for the main error paths.
Plain-language error messages to operators are load-bearing and drift
silently otherwise.

**Canonical example.** `tests/test_run_topic_backfill_chain.py`.

---

## §8 Observability / follow-up surfaces

### §8.1 `PipelineCResponse.diagnostics` must always carry backend identifiers

**Rule (from CLAUDE.md non-negotiable #5).** Every answered turn
surfaces `retrieval_backend` and `graph_backend` in diagnostics. If you
add an ingestion-related backend, wire it here too. Operators debug
runtime drift by reading this field; if it's absent, we lose a full
debugging channel.

### §8.2 Every ingestion job emits `ingest.delta.*` events

**Rule.** Any server-side endpoint that kicks off ingest work emits
the canonical event schema (`ingest.delta.run.start`,
`ingest.delta.sink.start/done`, `ingest.delta.falkor.start/done`,
`ingest.delta.cli.done` or `.run.failed`) to `logs/events.jsonl`. The
heartbeat + any new UI depends on this.

### §8.3 `doc_fingerprint` is the partial-completion guard

**Incident (v2 §7).** A sink crash after the fingerprint was stamped
but before Falkor edges landed left docs "unchanged" on the next run —
the edges would never catch up without `--force-full-classify`.

**Rule.** The fingerprint is stamped by the SINK as the LAST step of
its phase. Any new write-layer that persists before the sink must
NOT stamp the fingerprint. Verify the order in any PR that touches
`supabase_sink.py` or adds a new write phase.

---

## §9 Cross-cutting conventions

### §9.1 Bogotá AM/PM for user-facing time

**Rule.** Every timestamp the operator sees is rendered as
`America/Bogota` (UTC-5, no DST) 12-hour with AM/PM. Machine logs
(events.jsonl, DB columns) stay UTC ISO.

**Code pointer.** `scripts/monitoring/ingest_heartbeat.py::bog_time`.

### §9.2 Verbose folder / file names

**Rule.** Sub-folders holding tools get **descriptive** names
(`monitor_ingest_topic_batches/`, `monitor_sector_reclassification/`)
rather than generic ones (`batch_pipeline/`, `classifier/`). Scripts
live in the folder whose name matches their job. The next contributor
should find the right file without a tour.

**Context.** The user explicitly called out "finding a needle in a
haystack" as a recurring pain point during v3. Verbose names traded
keystrokes for discoverability; the trade stays.

### §9.3 Every non-trivial script has a sibling README

**Rule.** If a script does more than 50 lines of orchestration, its
folder carries a README explaining:
* What the script is for.
* How it fails and how to retry.
* Where its inputs come from and where its outputs go.
* What NOT to do (anti-patterns captured from past incidents).

### §9.4 Stage files explicitly, never `git add -A`

**Rule.** Commit specific file paths. `-A` has twice (v2 cleanup +
v3 reorg drafts) nearly staged `.env.local` backups, runtime logs
the gitignore didn't match, and local Supabase cache files. Not
worth the keystrokes.

**Exception.** Fresh repos have no history worth protecting; `-A` is
acceptable on the very first commit of a greenfield folder.

---

## §10 Pointers into the authoritative incident records

These files are where the raw triage + decisions were captured in real
time. If a learning above feels abstract, the corresponding § in the
source file has the full story.

| Learning theme | Canonical source |
|---|---|
| Detached-launch + tee-pipe SIGHUP | `docs/next/ingestionfix_v2.md §7 run_log_2026_04_23` (attempts 1-3) |
| PostgREST size limits + SQLSTATE 21000 | `docs/next/ingestionfix_v2.md §7` + `tests/test_dangling_store.py` lessons |
| Graph schema required_fields | `docs/next/ingestionfix_v2.md §7` + `src/lia_graph/graph/schema.py` |
| Banner VM field path | `docs/next/ingestionfix_v2.md §4 Phase 11` + v3 Phase 1 fix |
| Size estimates vs live probes | `docs/next/ingestionfix_v3.md §2.1` |
| Catch-all bucket hazards | `docs/next/ingestionfix_v3.md §2.2` |
| Durability contract / resumable batches | `docs/next/ingestionfix_v3.md §5 Phase 3` + `scripts/launch_batch.sh` header |
| Heartbeat design | `scripts/monitoring/README.md` + `scripts/monitoring/ingest_heartbeat.py` |
| Fingerprint as partial-completion guard | `docs/next/ingestionfix_v2.md §7 run_log_2026_04_23.lessons_learned` |

---

## §11 When to update this file

* After any ingestion bug that bites us in production. Add §N with the
  incident + the rule that prevents it.
* After any PR review where a reviewer had to re-explain one of the
  rules above (signals the rule needs a stronger test or docs presence).
* After any architecture decision that narrows or broadens the scope of
  UI ingestion.

**Do NOT** update this file to capture temporary state of an in-progress
fix. That belongs in the fix's plan doc (`docs/next/ingestionfix_vN.md`).
This file is for learnings that have **earned their place by surviving
a full triage cycle**.

---

*Last major update: 2026-04-23 (after ingestionfix_v3 Phase 2 code +
Phase 2.5 tooling landed, pre-rehearsal).*
