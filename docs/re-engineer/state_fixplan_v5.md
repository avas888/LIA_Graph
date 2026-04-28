# State — fixplan_v5 (close the 5 blockers + cascade)

> **Document type.** Live progress tracker for `fixplan_v5.md` — the
> focused execution plan that closes the 5 blockers surfaced by
> session 1 of the canonicalizer next-gate and runs the cascade
> across J + K + G + F + E batches.
>
> **Update cadence.** §3 (global state) gets touched whenever a
> blocker closes or a cascade batch finishes. §4 is the daily working
> surface. §10 is append-only; every meaningful action gets a
> timestamped entry.
>
> **Authority.** This file tracks state. `fixplan_v5.md` defines
> scope. Companion trackers cover narrower slices
> (`state_fixplanv4.md` — cumulative through v4 close;
> `state_canonicalizer_runv1.md` — per-batch;
> `state_corpus_population.md` — per-brief).

---

## 1. How to use this file

This file exists so any human or LLM picking up v5 can answer four
questions in under 60 seconds:

1. **Where are we?** — §3 (global state) + §4 (per-task table)
2. **What's blocking us?** — §5 (active blockers) + §4 "Blockers" col
3. **What did we just do?** — §10 (run log, most recent on top)
4. **What should I do next?** — §3 "Next action" + §6 (suggested order)

Update protocol:

* When you start a task, set status 🟡 → 🔵 in §4 + claim the row in the Owner column.
* When a task closes, set status to ✅ + add a §10 run-log entry.
* When you hit a blocker, add it to §5 + flag the affected §4 row.
* When the global state changes (e.g. all 5 blockers ✅, or cascade reaches halfway), update §3.

---

## 2. Fresh-LLM preconditions

If you are an incoming agent and this is your first contact with v5,
read in this order:

1. `CLAUDE.md` — repo-level operating guide. Already in context.
2. `docs/re-engineer/fixplan_v5.md` — full plan, especially §0 fresh-agent on-ramp + §3 the 5 fix recipes + §4 cascade plan.
3. **This file** — §3, §4, §10.
4. `docs/re-engineer/fixplan_v4.md` §6.A — mandatory runner protocol. Non-negotiable.
5. `docs/re-engineer/state_fixplanv4.md` §10 — last entries from session 1 (J5 rerun + J6 + G6 outcomes).

Memory-pinned guardrails (do not violate — full list in fixplan_v5
§0):

* Cloud writes pre-authorized — announce, don't ask.
* Beta-stance: every non-contradicting improvement flag flips ON.
* Never re-extract Phases A–D — extract once, promote through three stages.
* All canonicalizer runners delegate to `launch_batch.sh`. No re-implementation.
* Project-wide token bucket throttle (default 80 RPM) — never bypass.
* Autonomous progression — don't ask, just keep running until a stop condition fires.
* Diagnose before intervene.

---

## 3. Current global state

**As of:** 2026-04-28 PM Bogotá (v5 closed; v6 drafted as the active forward plan)

> **v5 → v6 transition:** the cascade halted at E1a (step 2 of 8 trimmed)
> after diagnosing that the article-slicing collapse is a single-root-cause
> problem — the harness queries DIAN normograma master pages (3 MB blobs,
> "knowingly unstable" per operator) when SUIN-Juriscol has the per-article
> data already cached locally. **`docs/re-engineer/fixplan_v6.md` is the
> active forward plan.** This file is now historical; final session
> outcome is recorded in §3 + §10 below.

| Field | Value |
|---|---|
| fixplan_v5 status | **closed** — engineering 5/5 ✅; cascade halted at E1a (step 2 of 8 trimmed) per operator directive to fix root cause first |
| Active forward plan | `docs/re-engineer/fixplan_v6.md` (SUIN-first rewire) |
| Blockers closed (✅) | **5 of 5** |
| Cascade batches run (✅ ledger row written) | **11 of 22 attempted** (J1/J2/J3/J4/K3/K4/J6/J7 + F2/E1a/G1/E5 partial; halt at E1a) |
| Veredictos written this cascade | 187 |
| Net new Postgres rows | **+25** (758 → 783) |
| Postgres `norm_vigencia_history` | **758** distinct verified norms |
| Falkor `(:Norm)` nodes / edges | **11 657 / 640** |
| `parsed_articles.jsonl` rows | **12 305** |
| Input set unique norm_ids | **18 676** |
| Smoke check across 41 batches | 23 PASS / 14 PARTIAL / 4 MISS |
| Active LLM provider | DeepSeek-v4-pro (75% discount through 2026-05-05) |
| Local docker stack | UP (supabase_db_lia-graph + lia-graph-falkor-dev) |
| Project-wide RPM cap | 80 |
| Outside-expert briefs in flight | 13 + 14 + 15 (drafted, awaiting delivery) |

**Next action.**

1. Pick a blocker from §4.A (recommended order: #5 → #1 → #4 → #3 → #2).
2. Edit the relevant file per `fixplan_v5.md` §3 recipe.
3. Run `PYTHONPATH=src:. uv run pytest tests/test_scrapers.py tests/test_canon.py -q` to confirm no regression.
4. Commit. Mark §4.A row ✅.
5. After all 5 close, run the §6 cascade.

**Recommended first blocker:** #5 (score crash on `--skip-post`, ~15
min). Tiny, isolated, makes every subsequent cascade run cleaner.

---

## 4. Per-task table

Status legend: 🟡 not started · 🔵 in progress · ✅ done · ⛔ blocked · ⏸ deferred

### 4.A The 5 v5 blockers (engineering)

| # | Blocker | Recipe ref | Status | Owner | Estimate | Notes |
|---|---|---|---|---|---:|---|
| 1 | Single-source rule rejects Senado-only leyes | fixplan_v5 §3 #1 | ✅ | claude-opus-4-7 (worktree) | 30 min | Approach B implemented at `vigencia_extractor.py:187-214`; new `single_source_accepted` field on `VigenciaResult`; 4 new tests pass. Commit `e8ffa09`. |
| 2 | CE auto/sent scrapers (Gap #1) | fixplan_v5 §3 #2 | ✅ | claude-opus-4-7 (worktree) | 45 min | Fixture-first path in `consejo_estado.py` + 5 placeholder fixtures under `tests/fixtures/scrapers/consejo_estado/`. Real text TBD from brief 14. 3 new tests pass. Commit `c20b3ce`. |
| 3 | Concepto hyphenated NUM filename | fixplan_v5 §3 #3 | ✅ | claude-opus-4-7 (worktree) | 30 min | Empirical curl probe across 24 candidate URLs returned 404 for every derivable filename — DIAN serves the doc at `oficio_dian_<RADICADO>_<YEAR>.htm`, requiring an external `var/dian_concepto_lookup.json`. New branch returns `None` until that lookup ships. Test pass. Commit `08e73f6`. |
| 4 | CST + CCo Senado scraper support | fixplan_v5 §3 #4 | ✅ | claude-opus-4-7 (worktree) | 45 min | `_handled_types` extended; CST uses coarse pr-segment map from `corpus_population/01_cst.md` with master-page fallback; CCo uses master `codigo_comercio.html`. 3 new tests pass. Commit `b1cde16`. |
| 5 | Score step crashes on `--skip-post` | fixplan_v5 §3 #5 | ✅ | claude-opus-4-7 | 20 min | `--skip-post` implies `--skip-score`; new `append_extract_only_row.py` writes a contiguous `EXTRACT_ONLY` ledger row. Smoke-tested. Commit `38edac3`. |

### 4.B Cascade batches (after the 5 blockers ✅)

Slice sizes are estimates from session-1 smoke check. Actual veredicto
counts will be ≤ slice (some norms may still refuse on edge cases).

| Order | Batch | Slice | Status | Notes |
|---:|---|---:|---|---|
| 1 | J5 (rerun) | 3 | 🟡 | confirms #1 fix; smallest sanity batch; previously 1/3 |
| 2 | J6 (rerun) | 3 | 🟡 | ley.100/1438/1751 — last session 1/3, expected 3/3 |
| 3 | J7 (rerun) | 3 | 🟡 | ley.789/1822/2114 |
| 4 | K4 (rerun) | 2 | 🟡 | ley.222/1258 |
| 5 | J1 | ~25 | 🟡 | first CST batch — confirms #4 |
| 6 | J2 | ~40 | 🟡 | CST cont. |
| 7 | J3 | ~35 | 🟡 | CST cont. |
| 8 | J4 | ~60 | 🟡 | CST collective |
| 9 | K3 | ~315 | 🟡 | CCo articles — biggest #4 unlock |
| 10 | G1 | ~407 | 🟡 | IVA Concepto Unificado numerals |
| 11 | G6 (rerun) | 5 | 🟡 | acid test — confirms #2 + #3 |
| 12 | F2 | ~111 | 🟡 | Resoluciones DIAN factura electrónica |
| 13 | E5 | ~104 | 🟡 | Decretos legislativos COVID |
| 14 | E6b | ~296 | 🟡 | DUR 1072 riesgos |
| 15 | E6c | ~229 | 🟡 | DUR 1072 SST |
| 16 | E1a | ~356 | 🟡 | DUR 1625 sub-libros 1.1+1.2 |
| 17 | E1b | ~82 | 🟡 | DUR 1625 sub-libros 1.3+1.4 |
| 18 | E1d | ~307 | 🟡 | DUR 1625 sub-libro 1.6 |
| 19 | E2a | ~271 | 🟡 | DUR 1625 IVA |
| 20 | E2c | ~228 | 🟡 | DUR 1625 retefuente |
| 21 | E3b | ~68 | 🟡 | DUR 1625 sanciones |
| 22 | J8b | ~229 | 🟡 | DUR 1072 (shared with E6) — likely cache-hit fast |
| 23 | D5 (rerun) | ~39 | 🟡 | closes fixplan_v4 §5.3 D5 weak-result |

### 4.C Out-of-v5 backlog (carried forward)

| Item | Where tracked | Why out of v5 |
|---|---|---|
| YAML keyword-pattern repair (F1/F3/F4 + H1/H2/H4a/b/H5 + I2) | fixplan_v4 §11.3 #9 | Gates 4 MISS batches but those need expert deliveries anyway |
| SUIN scraper realization | fixplan_v4 §5.6 | DIAN + Senado + (after #1) Función Pública covers >95% |
| Local UI server permanent solution | fixplan_v4 §11.3 #3 | Blocker #5 papers over for autonomous runs |
| Pool maintainer counter bug | fixplan_v4 §5.4 | Sequential cascade in §4.B avoids the issue |
| Phase A/B/C JSON regeneration | fixplan_v4 §5.2 | Needed for staging promotion only |
| Cosmetic heartbeat Bogotá-date format | fixplan_v4 §5.5 | Fix opportunistically |
| Outside-expert deliveries 13/14/15 | `state_corpus_population.md` §4 | Operator hands packets; ingest via `ingest_expert_packet.py` when they arrive |
| D5 canonical-id rewrite | fixplan_v4 §5.3 | Done as cascade row 23 above |
| SME signoff (O-1) → cloud promotion (O-2) | `state_fixplanv4.md` §4.D | Operator + Alejandro gate; not engineering |
| `var/dian_concepto_lookup.json` (canonical-suffix → `{radicado, year}`) | This file §10 (2026-04-28 PM entry) | Required for blocker #3 to actually fetch hyphenated unified conceptos. Seed from brief 08 + WebSearch hits. ~30-60 min when scheduled. |
| `var/senado_cco_pr_index.json` build script | This file §10 (2026-04-28 PM entry) | Conditional — only needed if K3 cascade returns weak/empty anchor slices on master `codigo_comercio.html`. Decide after K3 finishes. |
| Función Pública scraper (Approach A for Blocker #1) | fixplan_v5 §3 #1 | Cleaner long-term than Approach B; defer until after the cascade exposes whether Senado-only acceptance covers enough leyes. |

---

## 5. Active blockers

| ID | Blocker | Affects | Recovery path | Severity |
|---|---|---|---|---|
| B-1 | Single-source rule (fixplan_v5 §3 #1) | J5/J6/J7/K4 explicit_lists; ~half remaining batches | Approach A: Función Pública scraper. Approach B: relax rule for `.gov.co`. | HIGH (biggest unlock) |
| B-2 | CE auto/sent scrapers (fixplan_v5 §3 #2) | G6 + I3/I4 (after brief 14 lands) | Fixture-only path; live-fetch deferred | MEDIUM |
| B-3 | Concepto hyphen NUM URL (fixplan_v5 §3 #3) | G6 acid test + future G2-G5 | Empirical URL discovery + scraper case | MEDIUM |
| B-4 | CST + CCo Senado scraper (fixplan_v5 §3 #4) | J1-J4 + K3 (~485 norms) | Add to `_handled_types` + URL patterns | HIGH (biggest norm-count unlock) |
| B-5 | Score `--skip-post` crash (fixplan_v5 §3 #5) | every autonomous batch's ledger row | Gate score's chat-replay on `--skip-post` | LOW (workaround: dual `--skip-post --skip-score`) |

---

## 6. Suggested next-session sequence (canonical fixplan_v5 execution)

1. **Blocker #5** (~15 min) — score `--skip-post` crash. Tiny, isolated, every subsequent batch benefits.
2. **Blocker #1** (~30 min, Approach B) — single-source acceptance for `.gov.co` Senado. Or 90 min for Approach A (Función Pública scraper). Pick B for v5; A is cleaner but session-3+ work.
3. **Blocker #4** (~45 min) — Senado scraper handles CST + CCo. Biggest norm-count unlock.
4. **Blocker #3** (~20 min) — concepto hyphen URL discovery.
5. **Blocker #2** (~30 min, fixture-only) — CE fixture path for the 5 G6 acid-test ids.
6. **Engineer commit point** — 5 blockers ✅, scraper test suite green, all canon tests still green.
7. **Cascade run (autonomous, ~4–5 hours wall):** §4.B order 1–23 sequentially via `launch_batch.sh --batch <X> --allow-rerun --skip-post`. Heartbeat sidecar auto-arms; CronCreate 3-min heartbeat optional but recommended for batches 9–23 (longer slices).
8. **Post-cascade review:** update §10 run log with per-batch verdicts; update §3 global state with new Postgres + Falkor counts.
9. **Hand-off to v6 / session 3:** the 4 MISS batches still need (a) YAML keyword repair OR (b) expert deliveries 13/14/15. Operator decides.

**Key checkpoints during cascade:**

* After J5/J6/J7 (batches 1-3) → confirm blocker #1 fix actually unlocks Senado-only leyes. If still 1/3, the relax-rule-for-`.gov.co` patch missed something — diagnose before continuing.
* After K3 (batch 9) → confirm blocker #4 unlocked CCo. ~315 norms should land. If <100, Senado anchor-slicing needs work.
* After G6 (batch 11) → confirm blockers #2 + #3. 5/5 expected.
* After every batch → check Postgres count growing; check Falkor edges growing.
* If two consecutive batches score <50% → **HALT cascade** per fixplan_v4 §6.A kill-switches. Diagnose root cause.

---

## 10. Run log (append-only, most recent on top)

**Format:** `YYYY-MM-DD HH:MM TZ — <area> — <event>`

---

**2026-04-28 PM Bogotá — fixplan_v5 — closed, superseded by fixplan_v6.**
After the asyncio + harness-fix cascade reran from F2, partial run reached
E1a step 2 of 8 trimmed batches. F2 closed at 17/111 (15%); E1a in flight
showing 13/119 (11%) when the operator called halt to fix root cause
before continuing. **Diagnosis:** the harness routes DUR-articulado
norms to DIAN normograma's 3 MB master pages, asks the LLM to find
deeply-nested articles in those bulk docs, and gets 85% refusals. SUIN
has the per-article text + 16 282 modification edges already harvested
(`cache/suin/` 3 387 HTML files; `artifacts/suin/*/` documents/articles/edges
JSONL), but the SUIN scraper is a 46-line stub returning None. v5 closes
here; **`docs/re-engineer/fixplan_v6.md`** is the next-session plan to
wire SUIN as the preferred primary source. Final v5 numbers: **+25 net
new Postgres rows** (758 → **783** distinct verified norms);
**187 veredictos written** across 11 closed batches; **8-worker asyncio
verified working** at ~10× sequential throughput (commit `4b11cd7`).
Commits this session: `38edac3 b1cde16 e8ffa09 08e73f6 c20b3ce e8a92c7
4b11cd7 59260a0 583e925 af67e56` — all pushed to origin/main.

**2026-04-28 PM Bogotá — fixplan_v5 — all 5 blockers closed, ready for cascade.**
Engineering session ran #5 sequentially in main and #1/#2/#3/#4 as
4 parallel Claude worktree agents. All commits cherry-picked back to
main (`38edac3 → c20b3ce`). Combined regression on
`tests/test_scrapers.py + tests/test_canon.py + tests/test_vigencia_extractor.py`:
**156 passed, 0 failed.** Notable findings:
* **Blocker #3 needs follow-up.** No public DIAN URL is derivable from
  `concepto.dian.NNN-SSS` canonical ids; the doc actually lives at
  `oficio_dian_<RADICADO>_<YEAR>.htm` (verified for
  `concepto.dian.100208192-202` → `oficio_dian_6038_2024.htm`). Branch
  now returns `None` until a `var/dian_concepto_lookup.json` ships.
  Out-of-v5 follow-up logged to §4.C.
* **Blocker #4 caveat.** CCo has no segment map; all 315 K3 norms hit
  the master `codigo_comercio.html` page. If anchor slicing returns
  weak/empty results during the K3 cascade, follow-up = build
  `var/senado_cco_pr_index.json` via a script mirroring
  `build_senado_et_index.py`.
* **Blocker #1 acceptance footprint.** New `single_source_accepted`
  field on `VigenciaResult`; serialized in `to_dict`. Use it to spot
  Senado-only veredictos in the cascade JSONs.

Next: start cascade per §4.B order (J5 rerun first → smallest sanity
check that confirms blocker #1 actually unlocks Senado-only leyes).

**2026-04-28 PM Bogotá — fixplan_v5 — drafted + state file initialized.**
`fixplan_v5.md` written as a focused execution plan around the 5
blockers surfaced by session 1 of the canonicalizer next-gate. This
file (`state_fixplan_v5.md`) created as its live tracker. §4.A lists
the 5 blockers with file:line + estimate; §4.B lists the 23-batch
cascade plan; §6 has the recommended execution sequence. Current
verified-norm count: 758. Cascade target: ~3 200.

---

*Append new entries above this line in reverse chronological order
(most recent on top — same convention as `state_corpus_population.md`
and `state_fixplanv4.md`).*

---

*Drafted 2026-04-28 PM Bogotá by claude-opus-4-7 alongside
`fixplan_v5.md`. The §6 sequence is the canonical execution path; if
a fresh agent has zero context, §3 + §4 + §6 of this file plus §0 +
§3 + §4 of fixplan_v5.md hand them everything.*
