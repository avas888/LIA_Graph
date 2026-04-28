# State — fixplan_v6 (SUIN-first scraper rewire)

> **Document type.** Live progress tracker for `fixplan_v6.md` — the
> focused engineering plan to wire SUIN-Juriscol as the preferred
> primary source in the vigencia harness, replacing the DIAN normograma
> single-source path that proved structurally unable to deliver
> per-article extraction during the v5 cascade.
>
> **Update cadence.** §3 (global state) gets touched whenever a step
> closes or a cascade batch finishes. §4 is the daily working surface.
> §10 is append-only; every meaningful action gets a timestamped entry.
>
> **Authority.** This file tracks state. `fixplan_v6.md` defines scope.
> Companion trackers cover narrower slices
> (`state_fixplan_v5.md` — cumulative through v5 close;
> `state_canonicalizer_runv1.md` — per-batch;
> `state_corpus_population.md` — per-brief).

---

## 1. How to use this file

Four questions in under 60 seconds:

1. **Where are we?** — §3 (global state) + §4 (per-task table)
2. **What's blocking us?** — §5 (active blockers) + §4 "Blockers" col
3. **What did we just do?** — §10 (run log, most recent on top)
4. **What should I do next?** — §3 "Next action" + §6 (suggested order)

Update protocol:

* When you start a step, set status 🟡 → 🔵 in §4 + claim the row in the Owner column.
* When a step closes, set status to ✅ + add a §10 run-log entry.
* When you hit a blocker, add it to §5 + flag the affected §4 row.
* When the global state changes (e.g. all 4 engineering steps ✅, or cascade reaches halfway), update §3.

---

## 2. Fresh-LLM preconditions

If you are an incoming agent and this is your first contact with v6,
read in this order:

1. `CLAUDE.md` — repo-level operating guide. Already in context.
2. `docs/re-engineer/fixplan_v6.md` — full plan, especially §0 fresh-agent on-ramp + §3 the rewire recipe + §4 cascade plan.
3. **This file** — §3, §4, §10.
4. `docs/re-engineer/fixplan_v5.md` §3 — recipes for the 5 already-closed scraper blockers (still load-bearing context).
5. `docs/done/suin_harvestv1.md` + `suin_harvestv2.md` — how SUIN was harvested + what shape the data takes.
6. `docs/learnings/sites/suin-juriscol.md` — SUIN cert / robots / internal-id quirks.
7. `docs/re-engineer/state_fixplan_v5.md` §10 — last entries from the v5 cascade halt.

Memory-pinned guardrails (do not violate — full list in fixplan_v6 §0):

* Cloud writes pre-authorized — announce, don't ask.
* Beta-stance: every non-contradicting improvement flag flips ON.
* Never re-extract Phases A–D — extract once, promote through three stages.
* All canonicalizer runners delegate to `launch_batch.sh`. No re-implementation.
* Project-wide token bucket throttle (default 80 RPM) — never bypass.
* Autonomous progression — don't ask, just keep running until a stop condition fires.
* Diagnose before intervene.
* Six-gate lifecycle for pipeline changes — unit tests alone never sufficient.

---

## 3. Current global state

**As of:** 2026-04-28 PM Bogotá (start of v6, end of v5 cascade)

| Field | Value |
|---|---|
| fixplan_v6 status | drafted, ready to execute |
| Engineering steps closed (✅) | **0 of 4** (steps 1-4 of §3) |
| Cascade batches run under v6 (✅ verified) | **0 of 8** (steps 5-6 of §3 are the cascade) |
| Postgres `norm_vigencia_history` | **783** distinct verified norms (v5 baseline 758 + 25 from cascade) |
| Falkor `(:Norm)` nodes / edges | **~11 700** (TBD precise) |
| `parsed_articles.jsonl` rows | **12 305** |
| Input set unique norm_ids | **18 676** |
| Smoke check across 41 batches | unchanged from v5 (23 PASS / 14 PARTIAL / 4 MISS) |
| Active LLM provider | DeepSeek-v4-pro (75% discount through 2026-05-05) |
| Local docker stack | UP (supabase_db_lia-graph + lia-graph-falkor-dev) |
| Project-wide RPM cap | 80 |
| 8-worker asyncio concurrency | working (commit `4b11cd7`) |
| SUIN HTML cache | **3 387** files at `cache/suin/` |
| SUIN harvested edges | **16 282** across 3 scopes |
| SUIN scraper at `src/lia_graph/scrapers/suin_juriscol.py` | **46-line stub returning None** ← v6's binding constraint |

**Next action.**

1. Pick step #1 from §4.A (recommended order: #1 → #2 → #3 → #4).
2. Edit the relevant file per `fixplan_v6.md` §3 recipe.
3. Run `PYTHONPATH=src:. uv run pytest tests/test_suin_juriscol_scraper.py tests/test_vigencia_extractor.py tests/test_scrapers.py -q` to confirm no regression.
4. Commit. Mark §4.A row ✅.
5. After all 4 steps close, run the §6 cascade with `--rerun-only-refusals`.

**Recommended first step:** #1 (build the SUIN doc_id registry, ~60-90 min).
Tiny, isolated, makes step #2 trivial.

---

## 4. Per-task table

Status legend: 🟡 not started · 🔵 in progress · ✅ done · ⛔ blocked · ⏸ deferred

### 4.A The 4 v6 engineering steps

| # | Step | Recipe ref | Status | Owner | Estimate | Notes |
|---|---|---|---|---|---:|---|
| 1 | Build canonical→SUIN-doc-id registry | fixplan_v6 §3 step 1 | 🟡 | unassigned | 60-90 min | New file `var/suin_doc_id_registry.json`; new script `scripts/canonicalizer/build_suin_doc_id_registry.py`. Walks all `artifacts/suin/*/documents.jsonl`. |
| 2 | Replace SUIN scraper stub with real one | fixplan_v6 §3 step 2 | 🟡 | unassigned | 2-3 hours | Full rewrite of `src/lia_graph/scrapers/suin_juriscol.py`. Reuse helpers from `src/lia_graph/ingestion/suin/parser.py`. Most-impactful step. |
| 3 | Reorder scraper chain — SUIN first | fixplan_v6 §3 step 3 | 🟡 | unassigned | 30 min | Edit `vigencia_extractor.py:144-152`. Add `suin_juriscol` to `_TRUSTED_GOVCO_SOURCE_IDS`. |
| 4 | Add `--rerun-only-refusals` flag | fixplan_v6 §3 step 4 | 🟡 | unassigned | 30-45 min | Edit `extract_vigencia.py` `_process_one()`. Saves 25% wall-time on v6 cascade by preserving v5's 187 successes. |

### 4.B Cascade — Wave 1 (DIAN-routed reruns; SUIN-first directly fixes)

Per operator directive: **rerun failed norms first**, biggest pile of v5
refusals at the front. `--rerun-only-refusals` keeps the 187 v5 successes.

| Order | Batch | v5 outcome | Refusals to retry | Expected new ver. | Status |
|---:|---|---|---:|---:|---|
| 1 | **E1a** (rerun) | 13 ✅ / 572 🛑 | **572** | ~460 | 🟡 — largest pile, validates SUIN slicing at scale |
| 2 | F2 (rerun) | 17 ✅ / 94 🛑 | 94 | ~75 | 🟡 — half-validated already |
| 3 | E1b | never run | 95 | ~75 | 🟡 |
| 4 | E1d | never run | 337 | ~270 | 🟡 |
| 5 | E2a | never run | 304 | ~245 | 🟡 |
| 6 | E2c | never run | 228 | ~180 | 🟡 |
| 7 | E3b | never run | 68 | ~55 | 🟡 |
| 8 | D5 | never run | 39 | ~30 | 🟡 |

Wave 1 sub-total: **~1 390** new veredictos.

### 4.B-2 Cascade — Wave 2 (Senado-routed CST/CCo reruns; gated on SUIN CST+CCo coverage)

Run only if `grep -i 'codigo sustantivo\|codigo de comercio' artifacts/suin/*/documents.jsonl` returns hits.

| Order | Batch | v5 outcome | Refusals to retry | Expected new ver. | Status |
|---:|---|---|---:|---:|---|
| 9 | K3 (rerun) | 92 ✅ / 223 🛑 | 223 | ~180 | ⏸ — gated on SUIN CCo presence |
| 10 | J4 (rerun) | 11 ✅ / 66 🛑 | 66 | ~55 | ⏸ — gated on SUIN CST |
| 11 | J3 (rerun) | 4 ✅ / 40 🛑 | 40 | ~30 | ⏸ |
| 12 | J2 (rerun) | 32 ✅ / 19 🛑 | 19 | ~15 | ⏸ |
| 13 | J1 (rerun) | 23 ✅ / 6 🛑 | 6 | ~5 | ⏸ |

Wave 2 sub-total: **~285** new veredictos if SUIN has CST/CCo.

### 4.C Cascade — Wave 3 (gated on §3 step 6 SUIN coverage check)

| Order | Batch | Slice | Expected | Status | Gate |
|---:|---|---:|---:|---|---|
| 14 | E5 | 104 | ~80 | ⏸ | grep for decreto 417/2020 |
| 15 | E6b | 296 | ~235 | ⏸ | grep for decreto 1072/2015 |
| 16 | E6c | 229 | ~180 | ⏸ | same |
| 17 | J8b | 229 | ~0 | ⏸ | shared with E6 — likely cache-hit fast |
| 18 | G1 | 407 | ~325 | ⏸ | grep for concepto 0001/2003 |

### 4.D Out-of-v6 backlog (carried forward from v5)

| Item | Where tracked | Why out of v6 |
|---|---|---|
| Live-fetch path for CE auto/sent SPA | fixplan_v5 §3 #2 | Fixture-only path is in place; live SPA scraping needs Selenium/playwright. v7. |
| Función Pública scraper | fixplan_v5 §3 #1 Approach A | Superseded by SUIN-first. Defer indefinitely. |
| Outside-expert deliveries 13/14/15 | `state_corpus_population.md` §4 | Operator timing. |
| DIAN concepto lookup table | `state_fixplan_v5.md` §4.C | Superseded by SUIN-first IF SUIN has concepto coverage. |
| Senado CCo segment index | `state_fixplan_v5.md` §4.C | Superseded by SUIN-first IF SUIN has CCo article coverage. |
| Article-slicing improvements for DIAN scraper | this file | Superseded by SUIN-first. |
| Pool maintainer counter bug | fixplan_v4 §5.4 | Asyncio in extract_vigencia.py is fine. |
| Phase A/B/C JSON regeneration | fixplan_v4 §5.2 | Needed for staging promotion only. |
| Cosmetic heartbeat Bogotá-date format | fixplan_v4 §5.5 | Fix opportunistically. |
| SME signoff (O-1) → cloud promotion (O-2) | `state_fixplanv4.md` §4.D | Operator + Alejandro gate; not engineering. |
| SUIN harvest extension to cover decreto 1072 / 417 / concepto 0001-2003 | this file §4.C gates | If §3 step 6 finds SUIN missing these, harvest them via `src/lia_graph/ingestion/suin/harvest.py`. v7. |

---

## 5. Active blockers

| ID | Blocker | Affects | Recovery path | Severity |
|---|---|---|---|---|
| B-1 | SUIN scraper is a 46-line stub returning None | All DUR-articulado batches; ~3 000 norms in cascade | Steps 1+2+3 of §3 | CRITICAL — single root cause for v5 cascade collapse |
| B-2 | DIAN normograma is "knowingly unstable" per operator | Fallback path quality | Step 3 demotes DIAN to fallback | MEDIUM (handled by step 3) |
| B-3 | v5 produced 187 successes already on disk | Token waste if re-extracted | Step 4 (`--rerun-only-refusals`) | LOW (handled by step 4) |

---

## 6. Suggested next-session sequence (canonical fixplan_v6 execution)

1. **Step #1** (~60-90 min) — build canonical→SUIN-doc-id registry. Walk
   all `artifacts/suin/*/documents.jsonl`, write
   `var/suin_doc_id_registry.json`, write `tests/test_suin_doc_id_registry.py`.
2. **Step #2** (~2-3 hours) — full rewrite of
   `src/lia_graph/scrapers/suin_juriscol.py`. Use the registry from #1
   plus the existing `parser.py` helpers. Add 4-test suite.
3. **Step #3** (~30 min) — chain reorder + add `suin_juriscol` to
   `_TRUSTED_GOVCO_SOURCE_IDS`. Live test:
   `verify_norm("decreto.1625.2016.art.1.1.1")` returns
   `single_source_accepted == "suin_juriscol"`.
4. **Step #4** (~30-45 min) — add `--rerun-only-refusals` flag.
5. **Engineer commit point** — 4 steps ✅, scraper test suite green, all
   canon + vigencia tests still green.
6. **Cascade run (autonomous, ~3 hours wall):** §4.B order 1-8
   sequentially via the existing trimmed
   `scripts/canonicalizer/run_cascade_v5.sh` with
   `EXTRA_EXTRACT_FLAGS="--rerun-only-refusals"` +
   `LIA_EXTRACT_WORKERS=8`. Heartbeat sidecar auto-arms.
7. **Step #6 (post-cascade)** — grep SUIN cache for the missing-coverage
   docs (decreto 1072, decreto 417, concepto 0001-2003). If present,
   re-add §4.C batches and rerun. If not, log harvest extension as v7.
8. **Post-cascade review:** update §10 run log with per-batch verdicts;
   update §3 global state with new Postgres + Falkor counts.
9. **Hand-off to v7 / session 4:** the 5 §4.C batches still need
   either SUIN coverage extension OR the lookup tables that were the
   v5 backlog. Operator decides.

**Key checkpoints during cascade:**

* After F2 (batch 1) → confirm SUIN actually improves F2 from 17/111 to ≥80/111. If still <40/111, SUIN article slicing isn't producing useful per-article text — diagnose before continuing.
* After E1a (batch 2) → confirm DUR-renta works at scale. ~470 expected. If <100, the slice helper is wrong.
* After every batch → check Postgres count growing; check Falkor edges growing.
* If two consecutive batches score <50% → **HALT cascade** per fixplan_v4 §6.A kill-switches.

---

## 10. Run log (append-only, most recent on top)

**Format:** `YYYY-MM-DD HH:MM TZ — <area> — <event>`

---

**2026-04-28 PM Bogotá — fixplan_v6 — drafted + state file initialized.**
`fixplan_v6.md` written as a focused engineering plan around the
single-source SUIN-first rewire that resolves the v5 cascade's
article-slicing collapse. This file (`state_fixplan_v6.md`) created as
its live tracker. §4.A lists the 4 engineering steps with file:line +
estimate; §4.B lists the 8-batch cascade rerun plan; §4.C lists 5
batches gated on SUIN coverage check; §6 has the recommended execution
sequence. Current verified-norm count: **783**. Cascade target after v6:
**~3 000+**.

Pre-v6 evidence base from the v5 cascade (closed 2026-04-28 PM):
* 187 veredictos written across 11 closed batches (J/K/F/E families)
* +25 distinct norms in Postgres (758 → 783)
* DeepSeek-v4-pro confirmed live throughout
* 8-worker asyncio confirmed working (commit `4b11cd7`)
* SUIN cache audit: **3 387 HTML files** + **16 282 modification edges** across 3 harvested scopes
* SUIN scraper at `src/lia_graph/scrapers/suin_juriscol.py` is a **46-line stub returning None** — single binding constraint

---

*Append new entries above this line in reverse chronological order
(most recent on top — same convention as `state_fixplan_v5.md` and
`state_corpus_population.md`).*

---

*Drafted 2026-04-28 PM Bogotá by claude-opus-4-7 alongside
`fixplan_v6.md`, immediately after the v5 cascade halt at E1a (step 2
of 8 trimmed) on operator directive to "use SUIN first" because "DIAN
normograma is knowingly unstable". The §6 sequence is the canonical
execution path; if a fresh agent has zero context, §3 + §4 + §6 of this
file plus §0 + §3 + §4 of fixplan_v6.md hand them everything.*
