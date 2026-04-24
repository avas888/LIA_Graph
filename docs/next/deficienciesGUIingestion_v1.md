# Deficiencies — GUI ingestion path vs. v6 CLI wins (v1)

> **Status:** draft · **Opened:** 2026-04-24 · **Author:** post-v6-execution audit · **Scope:** the admin-facing GUI ingestion flow at `/ingest` and `/ingest/additive`, and the subprocess pipeline it spawns, compared against the scripts/CLI path we hardened in `docs/next/ingestion_tunningv2.md` (v6, commits `7d966ce..602fbb4`). Not scoped: read-only corpus catalog surfaces, retrieval-side work (coherence gate / citation allow-list are post-ingest).
>
> **Purpose.** The v6 cycle delivered 12 commits of improvements to the ingest pipeline — parallelism, diagnostic lift, rate-limit tuning, cloud-sink resilience, observability. Most of those wins propagate to the UI path automatically because the UI spawns the same `lia_graph.ingest` CLI as a subprocess and inherits the new defaults. **But some don't** — and the ones that don't are exactly the ones that cost us hours of debugging during v6 execution. A future admin clicking "Run full ingest" in the UI should not have to re-pay the same tuition. This doc maps each gap, ranks it, and sketches a fix.
>
> **Output of this doc.** Either a v2 doc specifying the remediation plan, or a set of small PRs if the gaps decompose cleanly. Do not ship code from this doc; it's a read-only audit.

---

## §0 Cold-start briefing

### 0.1 What this doc assumes you already know

- The v6 CLI path is in `src/lia_graph/ingest.py` (`python -m lia_graph.ingest`), with the supporting pool in `src/lia_graph/ingest_classifier_pool.py` and the sink in `src/lia_graph/ingestion/supabase_sink.py`.
- Four commits are the "wins" to propagate: `7d966ce` (phase 1 — diagnostic lift), `34f658b` (phase 2a — classifier pool), `602fbb4` (phase 2b — sink pool + `dep_health.py`), and the design rules in `docs/next/ingestion_tunningv2.md §16 Appendix D`.
- The GUI path lives at:
  - **Frontend**: `frontend/src/features/ingest/` + `frontend/src/app/ingest/ingestShell.ts`
  - **Backend controllers**: `src/lia_graph/ui_ingest_run_controllers.py`, `ui_ingest_delta_controllers.py`, `ui_ingestion_controllers.py`, `ui_ingestion_write_controllers.py`
  - **Subprocess wrapper**: `scripts/ingest_run_full.sh` (when `auto_embed` or `auto_promote` is set) or direct `make phase2-graph-artifacts-supabase` call.
- The existing UI-path learnings doc is `docs/next/UI_Ingestion_learnings.md`. It covers frontend-surface concerns (kanban state, retry UI). It does NOT cover the subprocess-pipeline concerns this doc audits.

### 0.2 What "deficiency" means here

Any place where a GUI-triggered ingest is **less safe, less observable, less tunable, or less resilient** than running the same workflow from the CLI after v6. Ranked in §3.

### 0.3 Evidence shape

Each deficiency cites:
- The UI code path that exhibits it (file:line).
- The CLI code path that does it right (file:line).
- The v6 commit or learning doc that motivated the CLI fix.
- The observable failure mode if the deficiency bites.

---

## §1 The GUI ingest surface, in one paragraph

The `/ingest` UI has two primary flows. **Full ingest** (`ui_ingest_run_controllers._spawn_ingest_subprocess`) calls `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=<target>` via `subprocess.run` with a 1-hour hard timeout, captures stdout+stderr to `artifacts/jobs/ingest_runs/ingest_<stamp>.log`, and exposes that log for tail-polling through `/api/ingest/job/{id}/log/tail`. **Additive delta** (`ui_ingest_delta_controllers`) runs in-process by calling `ingestion.delta_runtime.materialize_delta` directly. Both flows share the same `classify_corpus_documents` → `SupabaseCorpusSink` chain as the CLI. Kanban-backed intake (`ui_ingestion_write_controllers`) is a separate workflow for single-document upserts via UI-driven classification; it does not trigger the full pipeline.

## §2 Good news first — wins the UI already inherits

These don't need fixing:

| v6 win | How UI inherits it |
|---|---|
| **Parallel classifier (phase 2a)** | `argparse.default=8` in `--classifier-workers`. Subprocess call via `make` omits the flag; CLI default fires. ✅ |
| **Parallel Supabase sink (phase 2b)** | Same mechanism — `--supabase-workers` defaults to 4 via `argparse`. ✅ |
| **Rate-limit 300 RPM default** | `--rate-limit-rpm` default changed from 60 → 300 in the CLI. UI picks this up. ✅ |
| **Diagnostic lift (phase 1)** | UI progress endpoint reads `response.diagnostics` from the same dict structure as the A/B harness. Lifted fields are at top level now. ✅ (needs verification — see §3.5) |
| **Coherence gate + citation allow-list** | Retrieval-side, not ingest-side. Not applicable. ✅ |
| **Gold-taxonomy alignment** | Ingest doesn't consume gold files. Not applicable. ✅ |
| **Classifier degradation event emission** | Both paths emit `subtopic.ingest.audit_classified` with `status="failed"` / `requires_subtopic_review=True`. Events land in `logs/events.jsonl`. ✅ |

---

## §3 Deficiencies (ranked)

### §3.1 [P0] No `--allow-non-local-env` in the Makefile target

**Deficiency.** `Makefile:139` defines `PHASE2_SUPABASE_SINK_FLAGS = --supabase-sink --supabase-target $(PHASE2_SUPABASE_TARGET) --execute-load --allow-unblessed-load --strict-falkordb`. **No `--allow-non-local-env`.** The CLI's env-posture guard in `src/lia_graph/env_posture.py` aborts any run where `SUPABASE_URL` / `FALKORDB_URL` come from a non-local source unless that flag is passed.

**What this means for the UI.** Whether the UI-triggered ingest succeeds depends entirely on whether the web server's boot env already carries the cloud creds. In `npm run dev:staging` mode, the dev-launcher loads `.env.staging` so the env is present and the guard happily sees "local-sourced env." In production (Railway), the env comes from Railway's secret store, which the posture guard may or may not detect as "local." The first time this surfaces, it'll be mid-run failure with a cryptic "env_posture" message in the UI log tail.

We hit this exact class of failure during v6 cloud-sink execution on 2026-04-24 (the CLI form needed `set -a; source .env.staging; set +a` + `--allow-non-local-env`). See `docs/learnings/process/cloud-sink-execution-notes.md`.

**Fix.** Add `--allow-non-local-env` to `PHASE2_SUPABASE_SINK_FLAGS` when `PHASE2_SUPABASE_TARGET=production`. Scoped via make conditional:

```make
PHASE2_SUPABASE_SINK_FLAGS = --supabase-sink --supabase-target $(PHASE2_SUPABASE_TARGET) \
    --execute-load --allow-unblessed-load --strict-falkordb \
    $(if $(filter production,$(PHASE2_SUPABASE_TARGET)),--allow-non-local-env,)
```

Roughly +1 LOC. Regression-safe: only fires on the `production` target.

---

### §3.2 [P0] UI observability is stdout-log tail, not events.jsonl

**Deficiency.** `ui_ingest_run_controllers._tail_job_log` (line 357) polls `artifacts/jobs/ingest_runs/ingest_<stamp>.log` for progress. That log is `subprocess.run(..., stdout=log_fh, stderr=subprocess.STDOUT)` — a free-text stream.

The CLI path we hardened in v6 learned that stdout tails are the **wrong** source of truth:

- [`docs/learnings/process/observability-patterns.md`](../learnings/process/observability-patterns.md): "Anchor on `logs/events.jsonl`, not on the `--json` summary log. The summary only flushes on termination. Events are append-only."
- [`docs/learnings/process/heartbeat-monitoring.md`](../learnings/process/heartbeat-monitoring.md), failure mode #1: "Spanish legal text matching your error filter" — stdout carries ingested Colombian tax-code articles with "ERRORES" substrings that free-text filters match.
- Failure mode #4 in the same doc: stdout can hide real degradation when the pool catches 429s at the `failed=0` boundary.

**What this means for the UI.** An admin staring at the UI progress panel sees free-text log output, not structured event counts. They can't distinguish "still running" from "stuck on load_existing_tema" without reading stack traces. They can't tell `classifier done but sink hasn't started` from `sink running silently` because the UI has no phase concept.

**Fix.** Replace or supplement the subprocess-log-tail endpoint with an `events.jsonl`-anchored progress endpoint. Query shape:
```
GET /api/ingest/job/{id}/progress
→ {
  "phase": "classifier" | "bindings" | "load_existing_tema" | "sink" | "falkor" | "done",
  "classifier": {"total": 1275, "classified": 830, "failed": 0, "degraded": 114, "rpm": 305},
  "events_stale_seconds": 3,
  "dep_health": {"supabase": {"ok": true, "latency_ms": 142}, "falkor": {...}},
  "last_event_ts_utc": "2026-04-24T17:30:00+00:00"
}
```

The backend reads `logs/events.jsonl` (filtering by `LIA_INGEST_JOB_ID`), aggregates counters, applies phase-aware silence rules, and calls `dep_health.py` on every progress poll (cached at 10s to avoid rate-limiting the probe itself). Roughly +150 LOC in a new controller; the polling frequency matches the frontend's existing SSE or setInterval cadence.

---

### §3.3 [P1] 1-hour subprocess timeout is too tight post-v6

**Deficiency.** `ui_ingest_run_controllers._spawn_ingest_subprocess` line 462: `timeout=60 * 60,  # 1h hard cap`. This was set when a full ingest took 30–40 min. With the v6 corpus (2.7× size, 7,883 articles):

| Phase | v6 measured | Source |
|---|---|---|
| Classifier (parallel 8-worker, 300 RPM) | 6.5 min | Phase 2 rebuild on 2026-04-24 |
| Supabase sink (parallel 4-worker) | 2–3 min est | Phase 2b projection |
| Falkor load (sequential, not parallelized) | 3–8 min est | pre-v6 baseline |
| Embedding pass (if `auto_embed=1`) | 10–20 min | `scripts/embedding_ops.py`, limited by 3K RPM |
| **Total** | **22–37 min** | |

Current 60-min cap has only ~20 min of headroom. A TPM-429 storm (114 tracebacks in one v6 classifier pass) can add retry waits of ~53s per batch — 50 retries = ~45 min added. **The cap fires BEFORE the pipeline can finish**, killing the subprocess mid-sink.

**What this means for the UI.** If a TPM-pressured classifier pass or a slow Supabase upload pushes total wall time past 60 min, the UI subprocess gets killed by `subprocess.TimeoutExpired`. The sink is torn down mid-batch — idempotent upserts mean no lost data, but the user sees a "failed" ingest that's actually 95% complete.

**Fix.** Two changes:
1. Raise `timeout=` to at least `90 * 60` (90 min) for the non-chained path, `120 * 60` (2h) for `scripts/ingest_run_full.sh` (which includes embeddings).
2. Emit `subprocess.TimeoutExpired` into a distinct UI state ("timed out — run may have landed partial cloud writes, click resume") rather than the general failure state.

---

### §3.4 [P1] No UI exposure of the new worker / rate knobs

**Deficiency.** The frontend (`frontend/src/features/ingest/ingestController.ts`) does not pass any of:
- `--classifier-workers N`
- `--supabase-workers N`
- `--rate-limit-rpm N`

And the backend subprocess spawner doesn't accept them either. An admin has no way to say "this run is big, use 16 classifier workers" or "I'm seeing TPM pressure, drop to 4 workers."

**What this means for the UI.** The CLI defaults (8 / 4 / 300) are sensible for most runs but can't be tuned per-run. When a rebuild hits TPM-429 pressure like the v6 cloud sink did, the operator's only recourse is to edit env vars on the server. The GUI becomes an opaque one-button interface.

**Fix.** Add an "Advanced options" expando in the ingest-trigger dialog exposing the three knobs, all defaulting to their CLI defaults. Pass through to `_spawn_ingest_subprocess` as CLI args:

```python
cmd = ["make", "phase2-graph-artifacts-supabase",
       f"PHASE2_SUPABASE_TARGET={supabase_target}"]
# Future: pass through via env vars the Makefile picks up, OR extend
# the Makefile to forward LIA_INGEST_CLASSIFIER_WORKERS etc.
env["LIA_INGEST_CLASSIFIER_WORKERS"] = str(classifier_workers or 8)
env["LIA_SUPABASE_SINK_WORKERS"] = str(supabase_workers or 4)
env["LIA_INGEST_CLASSIFIER_RPM"] = str(rate_limit_rpm or 300)
```

Env vars are already the override path in the CLI (both phases 2a and 2b resolve env before defaults). This is ~20 LOC backend + a form field in the frontend.

---

### §3.5 [P1] UI doesn't surface degradation count to the operator

**Deficiency.** The v6 cloud-sink classifier pass emitted 92–114 tracebacks (all TPM-429s caught by the classifier's inner try/except and converted to N1-only degraded verdicts). The pool reported `failed=0`. **The UI has no way to tell the operator that ~7% of docs landed with `requires_subtopic_review=True`.**

See [`docs/learnings/process/cloud-sink-execution-notes.md`](../learnings/process/cloud-sink-execution-notes.md) §"'failed=0' under LLM backpressure" and [`docs/learnings/process/heartbeat-monitoring.md`](../learnings/process/heartbeat-monitoring.md) failure mode #4.

**What this means for the UI.** Two admins clicking "Run ingest" on the same corpus on different days can get silently different results. One gets clean N2 stamps everywhere; the other gets 7% N1-only because Gemini was under load. Neither is told.

**Fix.** The progress endpoint from §3.2 should include:
```json
"classifier": {
  "total": 1275,
  "classified": 1275,
  "failed_hard": 0,
  "degraded_n1_only": 114,
  "degraded_pct": 8.9
}
```

At end-of-run, UI shows a toast: "Run complete. 114 of 1,275 docs landed with degraded classification (N1-only, marked requires_subtopic_review). Cause: Gemini TPM backpressure. Re-run to refine." The `requires_subtopic_review=true` flag is already stored per-doc; surface the count.

---

### §3.6 [P2] No pre-flight dep health check before spawning

**Deficiency.** `_spawn_ingest_subprocess` goes straight to `subprocess.run` without checking whether Gemini / Supabase / Falkor are reachable. If Supabase is down, the ingest burns ~7 min of classifier + binding work before failing at the sink boundary.

**Fix.** Call `scripts/monitoring/dep_health.py` (shipped in commit `602fbb4`) as a pre-flight step. Fail fast with a friendly error: "Supabase is unreachable (timeout 5s). Start ingest anyway?" or simply "Abort."

```python
# in _spawn_ingest_subprocess, before subprocess.run(cmd, ...):
health = subprocess.run(
    ["uv", "run", "python", "scripts/monitoring/dep_health.py",
     "--probe", "supabase", "--probe", "gemini"],
    capture_output=True, timeout=30, env=env,
)
if health.returncode != 0:
    return {"ok": False, "error": "dep_unhealthy", "detail": health.stdout.decode()}
```

+15 LOC. Saves 7-min-of-wasted-work per down-dep incident.

---

### §3.7 [P2] No artifact-coherence snapshot before rebuild

**Deficiency.** `docs/learnings/ingestion/artifact-coherence.md`: `artifacts/parsed_articles.jsonl`, `typed_edges.jsonl`, `canonical_corpus_manifest.json`, `corpus_audit_report.json`, and several others are produced together and must be consumed together. A mid-run failure leaves them in an incoherent state, which causes the orchestrator to fall through to a `compat_stub` path with broken diagnostics.

The CLI path left this to operator discipline (we used `cp ... .v5_backup` manually). The UI path has no snapshot discipline at all.

**Fix.** Pre-run, snapshot all `artifacts/*.json` + `artifacts/*.jsonl` into `artifacts/.snapshots/<timestamp>/`. Post-run, if `PHASE2_SINK_EXIT != 0`, offer the UI operator a one-click "restore pre-run snapshot" button. Prune snapshots older than 3 runs.

+50 LOC in a new controller + a restore endpoint.

---

### §3.8 [P2] Additive delta path DOES pass `supabase_workers` but doesn't wire it from deps

**Deficiency.** Commit `602fbb4` added `classifier_workers=deps.get("classifier_workers")` to `ui_ingest_delta_controllers.py` line 129. It does NOT add `supabase_workers=deps.get("supabase_workers")`. Delta flow silently falls back to the env var or default.

**Fix.** Add one line:

```python
# in ui_ingest_delta_controllers.py, _build_materialize_kwargs
"classifier_workers": deps.get("classifier_workers"),
"supabase_workers": deps.get("supabase_workers"),
```

1 LOC. Risk: zero.

---

### §3.9 [P3] No UI signal that `--skip-llm` was NOT used

**Deficiency.** `ui_ingest_run_controllers` line 920 uses `skip_llm=True` for the **intake-time** classifier (a different, lighter path). A future contributor might copy that pattern into the full-ingest spawner, silently skipping PASO-4 subtopic stamps. The full ingest should emit a confirmation event: "classifier pass ran with N2 enabled, got N degraded verdicts" so the UI can show it as a checkmark.

**Fix.** Emit a new structured event `ingest.llm_mode` with payload `{"skip_llm": false, "classifier_rpm_cap": 300, "workers": 8}` at the start of each run. UI progress endpoint reads and surfaces it.

+5 LOC.

---

### §3.10 [P3] No documented rollout of `LIA_SUPABASE_SINK_WORKERS` / `LIA_INGEST_CLASSIFIER_WORKERS` in env matrix

**Deficiency.** `docs/guide/orchestration.md` §Env-v2026-04-22-ac1 lists all `LIA_*` flags for the served runtime. Ingest-side flags (`LIA_INGEST_CLASSIFIER_RPM`, `LIA_INGEST_CLASSIFIER_WORKERS`, `LIA_SUPABASE_SINK_WORKERS`) are not there. If a production operator tunes the UI runtime via env, they have to grep the codebase to find the knobs.

**Fix.** Add an "Ingest-pipeline env vars" subsection to the orchestration env matrix. Keep it separate from the served-runtime vars since it only applies during ingest runs.

+30 lines of docs.

---

### §3.11 [P3] No tests covering the UI→subprocess env propagation

**Deficiency.** We don't have a test asserting that `LIA_INGEST_CLASSIFIER_WORKERS=16` set on the UI web server is inherited by the spawned `make` subprocess and by the Python child of that make. A future refactor of `_spawn_ingest_subprocess` that accidentally filters the env could silently drop the override.

**Fix.** Add `tests/test_ui_ingest_subprocess_env.py` with one test that monkeypatches `subprocess.run` and asserts the `env` arg contains `LIA_INGEST_CLASSIFIER_WORKERS`, `LIA_SUPABASE_SINK_WORKERS`, `LIA_INGEST_CLASSIFIER_RPM`.

+30 LOC.

---

## §4 Summary table

| # | Priority | Gap | File | Est. diff |
|---|---|---|---|---|
| 3.1 | P0 | Makefile lacks `--allow-non-local-env` for production target | `Makefile:139` | +1 LOC |
| 3.2 | P0 | Stdout-tail is the wrong observability surface | `ui_ingest_run_controllers.py:357-390` | +150 LOC |
| 3.3 | P1 | 1h subprocess timeout too tight for v6 corpus | `ui_ingest_run_controllers.py:462` | +5 LOC |
| 3.4 | P1 | No UI exposure of worker / RPM knobs | UI + backend spawner | +50 LOC |
| 3.5 | P1 | No degradation count surfaced | progress endpoint | +30 LOC |
| 3.6 | P2 | No pre-flight dep health check | spawner | +15 LOC |
| 3.7 | P2 | No artifact-coherence snapshot | new controller | +50 LOC |
| 3.8 | P2 | `supabase_workers` missing from delta deps | `ui_ingest_delta_controllers.py:129` | +1 LOC |
| 3.9 | P3 | No ingest.llm_mode event | spawner | +5 LOC |
| 3.10 | P3 | Ingest env vars missing from orchestration matrix | docs | +30 LOC docs |
| 3.11 | P3 | No test on UI→subprocess env propagation | new test file | +30 LOC |

**Total estimated diff:** ~370 LOC across ~7 files, plus docs. Small enough to land as a single PR or a P0→P3 stack.

---

## §5 Sequencing recommendation

If this doc becomes a v2 execution plan:

1. **P0s first**, as one PR (§3.1 + §3.2). Makefile fix is trivial; events.jsonl-anchored progress endpoint is the big piece but it's self-contained.
2. **P1s second**, as one PR (§3.3 + §3.4 + §3.5). All touch the subprocess spawner + progress endpoint together.
3. **P2s + P3s** as individual small PRs (§3.6–§3.11).

Estimated engineering effort: 3–5 days for the P0/P1 block; another 2–3 days for the P2/P3 tail.

---

## §6 Success criteria for a v2 remediation plan

A v2 plan's phase 6 (its own validation) should prove, via a GUI-driven run, that:

1. An admin can trigger a full ingest via UI against production Supabase, inheriting the v6 phase-2a/2b defaults without manual env setup.
2. The UI progress panel distinguishes `classifier` / `bindings` / `load_existing_tema` / `sink` / `falkor` phases, with per-phase counters and a "stale events" indicator.
3. The UI surfaces degradation count, dep-health status, and honest ETA.
4. A mid-run timeout (forced via `sleep 3700` in a fake subprocess) reaches the user as "timed out, may be partial" not "failed."
5. Post-run, a run with 92+ tracebacks shows up in UI as "WARN: 7% degraded, consider re-run" — not as a silent success.

---

## §7 What this doc is NOT

- Not a UI redesign. Scope is limited to the invisible gaps between the GUI flow and the CLI flow.
- Not a policy on when/why the UI should run full ingests. That's a product decision.
- Not a Falkor-parallelization proposal (that's a separate v6 follow-up; see `ingestion_tunningv2.md §16 Appendix D §9`).

---

## §8 References

- `docs/next/ingestion_tunningv2.md` — v6 plan.
- `docs/next/ingestion_tunningv2.md §16 Appendix D` — v6 execution learnings.
- `docs/learnings/README.md` — canonical learnings index (12 docs across ingestion / retrieval / process).
- `docs/learnings/ingestion/parallelism-and-rate-limits.md` — phase 2a design.
- `docs/learnings/ingestion/supabase-sink-parallelization.md` — phase 2b design.
- `docs/learnings/process/observability-patterns.md` + `heartbeat-monitoring.md` — observability contracts.
- `docs/learnings/process/cloud-sink-execution-notes.md` — env posture + degradation semantics.
- `docs/next/UI_Ingestion_learnings.md` — pre-existing frontend-surface learnings.
- Commits: `7d966ce` phase 1 · `34f658b` phase 2a · `602fbb4` phase 2b.

---

*End of `deficienciesGUIingestion_v1.md`. Next in this sequence: either a `deficienciesGUIingestion_v2.md` execution plan or individual-PR tickets per §3 entry, depending on operator preference.*
