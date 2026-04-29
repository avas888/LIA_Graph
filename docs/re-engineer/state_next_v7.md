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

## 2. Global state (2026-04-29 ~9:10 AM Bogotá)

* **P1 — cloud promotion.** 4th attempt in flight as
  `v6-cloud-promotion-20260429T134852Z`. ~50% through (1,932 of
  ~3,250 expected inserts; 0 errors at row 1,932). Three earlier
  attempts each failed-fast on different root causes; all root
  causes fixed and committed before the next attempt.
* **P2 — DIAN PDF scraper.** ✅ Complete + committed. F2 unblocked
  for next rerun. Live verification: `res.dian.13.2021.art.5` →
  3,157 chars sliced clean.
* **P3 — K3 CCo gap close.** ✅ Complete + committed. 1,967 CCo
  articles indexed across 63 segments; Senado scraper resolves
  per-pr URL. Step 3a (FP probe) ruled out; step 3c (slicer tuning)
  not needed.
* **P4 / P5 / P6 — gated on P1 cli.done.** Launcher staged at
  `scripts/cloud_promotion/launch_post_p1.sh`: P5 synchronous
  (Falkor sync, 5 min), then P4 + P6 detached in parallel
  (embedding backfill ~1-2 hr; refusal rerun ~3 hr).
* **P7 — SUIN harvest extension.** Fork agent investigating doc-ids
  for the 6 COVID decretos (decreto.{417,444,535,568,573,772}.2020).
  Awaiting return.

---

## 3. Per-task table

| ID | Task | Status | Owner | Effort | Notes |
|---|---|---|---|---|---|
| **P1** | Cloud promotion (audit + reconcile + push) | 🔵 in-flight | claude-opus | 1-2 hr | 4th attempt; fail-fast doctrine fixed 3 prior root causes (frozen-dataclass mutate, cst/cco grammar, norm_type CHECK) |
| **P2** | DIAN PDF scraper (7th source) | ✅ done | claude-opus | shipped | commits `3b09719` + per-source notes |
| **P3** | K3 CCo gap close | ✅ done | claude-opus | shipped | commits `c0f3d3d` + `95e1eb9`; segment index path |
| **P4** | Embedding backfill on cloud | 🟡 staged | — | 1-2 hr compute | gated on P1 done; in `launch_post_p1.sh` |
| **P5** | Falkor edge sync verification | 🟡 staged | — | 5 min | gated on P1 done; in `launch_post_p1.sh` |
| **P6** | Refusal rerun w/ --max-source-chars 32000 | 🟡 staged | — | 3 hr | gated on P1 done; flag wired in commit `3b09719` |
| **P7** | SUIN harvest extension (E5 COVID decretos) | 🔍 investigating | fork-agent | 3-5 hr | doc-id discovery in flight |

Status legend: 💡 idea / 🟡 staged / 🔵 in-flight / ✅ done / ↩ regressed-discarded / 🔍 investigating.

---

## 4. Run log (append-only, most recent first)

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

None. P4/P5/P6/P7 all have either staged launchers or fork agents
in motion.

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
