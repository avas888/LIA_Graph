# State — next_v7 (post-v6 forward plan)

> **Document type.** Live progress tracker for `next_v7.md` — the
> 7-step forward plan after fixplan_v6 close. P1 = comprehensive
> cloud promotion; P2-P7 = gap-closing extensions ordered by
> next_v7 §3.
>
> **Update cadence.** §3 (per-task table) on every status change;
> §4 (run log) append-only.
>
> **Authority.** This file tracks state. `next_v7.md` defines scope.

---

## 1. Fresh-LLM preconditions

If you are an incoming agent and this is your first contact with v7,
read in this order:

1. `CLAUDE.md` + `AGENTS.md` — repo-level operating guides. Read the
   "Fail Fast, Fix Fast — operations canon" section first; it codifies
   how the v7 P1 cycle ran (instrument, fail fast, diagnose root cause,
   re-run until stable).
2. `docs/re-engineer/next_v7.md` — full plan with §0 fresh-agent
   on-ramp + §3 ordered task list + §6 file index.
3. **This file** — §3 (task table), §4 (run log).
4. `docs/re-engineer/state_fixplan_v6.md` — v6 closure + the cascade
   ledger that produced 2,653 verified veredictos (the input to P1).

Memory-pinned guardrails (do not violate):

* Cloud writes pre-authorized — announce, don't ask.
* Fail-fast / fix-fast lifecycle on any op ≥100 records (CLAUDE.md
  "operations canon" section).
* Idempotent re-launches — never raise the threshold or
  `--continue-on-error`.
* All canonicalizer runners delegate to `launch_batch.sh`.
* Autonomous progression — proceed without check-ins; stop only on
  real kill-switches.

---

## 2. Global state (2026-04-29 ~10:15 AM Bogotá)

* **P1 — cloud promotion.** ✅ Complete (4th attempt). Final:
  3,264 inserts / 873 refusals / 3 errors (0.07%) across 39
  batches. Cloud `norm_vigencia_history`: 0 → 9,322 rows
  (with attempt-1/2/3 partial accumulation included; idempotency
  is run-id-scoped). Distinct norm_ids: 2,349 (vs 2,362 local).
* **P2 — DIAN PDF scraper.** ✅ Complete. F2 unblocked.
* **P3 — K3 CCo gap close.** ✅ Complete. 1,967-article index.
* **P4 — embedding backfill.** ✅ Complete (no-op). Cloud already
  had 19,546/19,546 chunks embedded from prior corpus syncs; P1
  added vigencia rows but no new chunks. The 4-shard launcher
  staged earlier is unused for this cycle but stays for future
  embedding-backfill needs.
* **P5 — Falkor sync.** ✅ Complete. 2,905 norm nodes + ~2,548
  vigencia edges (MODIFIED_BY/DEROGATED_BY/INEXEQUIBLE_BY/etc.)
  written to cloud Falkor. Took 20 min for ~5,500 sequential
  cypher round-trips — see §7 perf follow-up below.
* **P6 — refusal rerun w/ --max-source-chars 32000.** 🔵 In flight.
  Cascade step 1/8 (batch F2). ETA ~3 hr.
* **P7 — Senado decreto resolver extension.** ✅ Complete (fork
  agent commit `1592832`). Pivoted from the SUIN-harvest path
  (next_v7 §3.7 original proposal) after the SUIN doc-id-discovery
  fork found the 6 COVID decretos NOT on SUIN but ALL on Senado at
  `decreto_<NUM4>_<YEAR>.html`. Closes E5 when P6 reaches it.

---

## 3. Per-task table

| ID | Task | Status | Owner | Effort | Notes |
|---|---|---|---|---|---|
| **P1** | Cloud promotion (audit + reconcile + push) | ✅ done | claude-opus | 4 attempts × 25-33 min | Final 4th attempt clean: 3,264 inserts / 3 errors. Three earlier attempts each failed-fast on a different root cause — produced rules 7+8 of the operations canon |
| **P2** | DIAN PDF scraper (7th source) | ✅ done | claude-opus | shipped | commits `3b09719` + per-source notes |
| **P3** | K3 CCo gap close | ✅ done | claude-opus | shipped | commits `c0f3d3d` + `95e1eb9`; segment index path |
| **P4** | Embedding backfill on cloud | ✅ done (no-op) | claude-opus | 15 sec | All 19,546 chunks already embedded; P1 added vigencia rows, not chunks |
| **P5** | Falkor edge sync verification | ✅ done | claude-opus | 20 min | 2,905 nodes + ~2,548 edges written. Sequential cypher round-trips — UNWIND batching follow-up in §7 |
| **P6** | Refusal rerun w/ --max-source-chars 32000 | 🔵 in flight | claude-opus | ~3 hr ETA | step 1/8 (F2); flag wired in commit `3b09719`, will exercise the new DIAN PDF scraper + Senado decreto resolver |
| **P7** | Senado decreto resolver extension | ✅ done | fork-agent | shipped | commit `1592832`; ~5-LOC patch pivoted from the SUIN harvest path after the SUIN doc-id discovery fork found COVID decretos all on Senado |
| **P4-shard** | `--shard X/N` flag for embedding_ops | ✅ done | fork-agent | shipped | commit `9e6bdcf`; stays available for future embedding backfills (this cycle's was a no-op) |

Status legend: 💡 idea / 🟡 staged / 🔵 in-flight / ✅ done / ↩ regressed-discarded / 🔍 investigating.

---

## 4. Run log (append-only, most recent first)

### 2026-04-29 ~10:15 AM Bogotá — Post-P1 launch, 6 of 7 streams done

`launch_post_p1.sh` fired:
* P5 sync 09:46:59 → 10:07:22 (20 min, ~5,500 sequential
  cypher round-trips). Final: 2,905 norm nodes + ~2,548
  vigencia edges (MODIFIED_BY 1,752 / DEROGATED_BY 294 /
  INEXEQUIBLE_BY 165 / COND_EXEQ 21 + others).
* P4 fired 10:07:22 → finished in 15 sec (no-op).
  All 19,546 chunks already embedded.
* P6 fired 10:07:22, in flight on cascade step 1/8 (F2).
  Heartbeat `br2fpnmq6` polling every 3 min.

Two parallel forks shipped:
* `1592832` — Senado decreto resolver (closes E5).
* `9e6bdcf` — `--shard X/N` for embedding_ops (deferred-utility).

### 2026-04-29 ~9:23 AM Bogotá — P1 ✅ DONE

39/39 batches, 33 min elapsed, 3,264 inserts / 873 refusals /
3 errors (0.07%, all known data-edge cases — 2 "None" + 1
unrecoverable sentencia). cli.partial sentinel because some
batch-level rc=1 from the row errors, but well below fail-fast
thresholds.

Cloud cardinalities post-promotion:
* `norm_vigencia_history`: 9,322 rows / 2,349 distinct norm_ids
* `norms`: 2,905 rows
* Cloud Falkor `(:Norm)`: 2,905 (after P5 ran)

### 2026-04-29 ~9:10 AM Bogotá — P1 4th attempt healthy at row 1,932

`v6-cloud-promotion-20260429T134852Z` running clean. Past D5 + E1a +
E1b + E1d + E2a — all the points where prior attempts wobbled. Next
stability gate is J1+J2 (CST batches) at batch 31.

### 2026-04-29 08:48 Bogotá — P1 4th launch

Migration `20260501000006_norms_norm_type_extend.sql` applied via
`supabase db push --linked`. Extends `norms_norm_type_valid` to cover
cst, cco, decreto_legislativo, decreto_ley + their _articulo
variants, plus oficio_dian and dcin_numeral that canon already
returned but were never enumerated.

`canon.norm_type()` updated to map the new prefixes correctly
(decreto_legislativo / decreto_ley branches placed BEFORE plain
decreto. since their prefix is longer).

Commit `5a0ad15`.

### 2026-04-29 08:41 Bogotá — P1 3rd attempt FAIL-FAST

Tripped at batch 31 (J1+J2 CST) with 83 row-errors all of the same
shape: `new row for relation "norms" violates check constraint
norms_norm_type_valid`. Cloud-side schema gap. Halt + diagnose.

### 2026-04-29 08:14 Bogotá — P1 3rd launch (canon cst/cco grammar fix)

`canon.py` extended grammar to accept bare `cst` / `cco` (whole
codigo references) per the existing ET pattern. Commit `10f0fa8`.
Dry-validation: J1 → 29/29 clean.

### 2026-04-29 08:12 Bogotá — P1 2nd attempt FAIL-FAST

Tripped at batch 31 (J1+J2 CST) with 80 errors `Invalid norm_id per
§0.5 grammar: 'cst'` — bare `cst` was being passed as a
source_norm_id but the grammar required `cst.art.<N>`.

### 2026-04-29 ~07:45 Bogotá — P1 2nd launch (writer normalize-then-thread fix)

Restructured `_normalize_source_norm_id()` flow to thread the
normalized id into the change_source dict at construction time
instead of mutating the frozen `ChangeSource` dataclass (which the
1st attempt's "cannot assign to field" error revealed). Commit
`9cebd4b` includes the writer + normalizer + canon
decreto_legislativo/decreto_ley grammar additions + the cloud
promotion orchestrator + heartbeat.

### 2026-04-29 ~07:43 Bogotá — P1 1st attempt FAIL-FAST

Tripped after 350 rows / 46 errors (13% rate). Root cause: writer
tried to mutate frozen ChangeSource dataclass when normalizing
source_norm_id aliases.

### 2026-04-29 ~07:30 Bogotá — P1 1st launch

Initial cloud promotion against `production` target after the
6 missing migrations (`20260501000000`–`005`) were applied via
`supabase db push --linked`. Pre-pass dry-validation found 81 bad
source_norm_ids out of 4,188 veredictos; normalizer reduced this to
3 residual edge cases (2 unparseable "None" + 1 sentencia missing
year suffix).

### 2026-04-29 ~07:25 Bogotá — Cloud schema parity check

Discovered cloud was missing the entire `2026-05-01` migration
batch (norms / norm_vigencia_history / norm_citations / resolver
functions / chunk_vigencia_gate / vigencia_reverify_queue) — all
6 applied via `supabase db push --linked` cleanly.

---

## 5. Active blockers

None.

---

## 7. Fast-follow / next_v8 candidates

### P5 perf — `sync_vigencia_to_falkor.py` should batch via UNWIND

**Observed.** P5 took 20 min to write ~5,500 sequential cypher
queries (~2,905 norm-merge + ~2,548 edge-merge). At ~80-130 ms
per round-trip against cloud Falkor, sequential MERGE is the
bottleneck.

**Fix.** Replace per-row MERGEs with UNWIND-batched inserts:

```cypher
UNWIND $rows AS r
MERGE (a:Norm {norm_id: r.a})
MERGE (b:Norm {norm_id: r.b})
MERGE (a)-[e:DEROGATED_BY {record_id: r.record_id}]->(b)
SET e.state_from = r.state_from, e.state_until = r.state_until,
    e.effect_type = r.effect_type
```

Batch 500-1000 rows per call → 5-10 round-trips total instead of
5,500. Expected 50-100× speedup. The GraphClient already supports
parameter binding (see `parameter_keys` diagnostic). Add an
`execute_unwind` helper. Estimated effort: ~2 hr.

### P5 perf — eliminate write-side overlap with prior runs

Cloud Falkor already had 25,328 edges from prior corpus syncs;
this P5 added ~2,548 vigencia edges on top. Those ARE all
distinct edge types (DEROGATED_BY etc. are vigencia-specific),
but the corpus-level edges (REFERENCES, MODIFIES, etc.) are
unrelated. Worth verifying the two write paths don't ever
overlap on the same edge keyspace — if they do, the second
sync silently no-ops the first and a coverage gap opens.

### Re-run P5 with the batched script post-P6

Once UNWIND batching ships, re-run P5 against the post-P6 cloud
state (P6 will add ~50-150 new history rows from refusal
recoveries). Should take <1 min instead of 20.

---

## 6. Suggested next order (for the agent picking up from cli.done)

1. Confirm P1 finished clean (cli.done sentinel + audit log shows
   all 39 batches with 0 errors). If cli.partial fired instead,
   tally the audit errors by reason — one root cause per fail-fast
   trip, fix once, re-run.
2. Run `bash scripts/cloud_promotion/launch_post_p1.sh`. Watches:
   * P5 finishes synchronously and prints "P5 ok" before P4/P6
     launch; if it fails, halt.
   * P4 detached PID written to `${POST_DIR}/p4.pid`; arm a heartbeat
     reading `p4_embedding_backfill.log` for `pending_count` /
     `filled` markers.
   * P6 detached PID written to `${POST_DIR}/p6.pid`; same heartbeat
     pattern as the v6 cascade driver (read `logs/events.jsonl` not
     the per-batch log buffer).
3. When the P7 fork agent reports back, drop the discovered SUIN
   doc-ids into `SEED_URLS` in `src/lia_graph/ingestion/suin/fetcher.py`
   under a new `tributario_covid` scope, then re-run the harvester
   for that scope only:
   `PYTHONPATH=src:. uv run python -m lia_graph.ingestion.suin.harvest --scope tributario_covid`.
4. Rebuild registry:
   `PYTHONPATH=src:. uv run python scripts/canonicalizer/build_suin_doc_id_registry.py`.
5. Re-run E5 batch with `--rerun-only-refusals --max-source-chars 32000`
   (combined P6 + P7 effect).

---

*Tracker for next_v7.md, drafted 2026-04-29 ~9:10 AM Bogotá by
claude-opus-4-7 mid-P1 cycle. Append-only run log; update §3 + §4
on every status change.*
