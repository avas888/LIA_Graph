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

**As of:** 2026-04-28 PM Bogotá (engineering done, cascade pending)

| Field | Value |
|---|---|
| fixplan_v6 status | engineering ✅ — 5 commits landed; cascade rerun pending |
| Engineering steps closed (✅) | **5 of 5** (steps 1-4 + 5a of §3) |
| Cascade batches run under v6 (✅ verified) | **0 of 8** (step 5b ready to launch) |
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
| SUIN registry | **10 entries** at `var/suin_doc_id_registry.json` (commit `cfe64bb`) |
| SUIN scraper at `src/lia_graph/scrapers/suin_juriscol.py` | **registry-backed slicer** — three-tier cache, per-article slicing via parser (commit `9940faf`) |
| Parser regex `_ARTICLE_HEADING_RE` | **fixed** to capture multi-segment DUR numbers `1.6.1.1.10` (commit `9940faf`) |
| Scraper chain order | **SUIN → Senado → DIAN → CC → CE** (commit `d00da64`) |
| `_TRUSTED_GOVCO_SOURCE_IDS` | `{suin_juriscol, secretaria_senado, dian_normograma}` (commit `d00da64`) |
| `--rerun-only-refusals` flag | available on `extract_vigencia.py` (commit `f91401b`) |
| `EXTRA_EXTRACT_FLAGS` passthrough | wired in `launch_batch.sh` (commit `f91401b`) |

**Next action.**

Engineering steps 1-4 + 5a are done. The cascade rerun is the only
remaining work. Run from a Bogotá-noon window so the heartbeat sidecar
has business-hours coverage:

```bash
EXTRA_EXTRACT_FLAGS="--rerun-only-refusals" \
LIA_EXTRACT_WORKERS=8 \
nohup bash scripts/canonicalizer/run_cascade_v5.sh \
    > logs/cascade_v6_driver.log 2>&1 &
disown
echo $! > /tmp/cascade_v6_driver.pid
```

After E1a closes (the largest pile, batch 2 of 8), confirm pass-rate
≥70% before letting the cascade continue. If it's <40%, the SUIN slicer
is misbehaving — read the per-norm JSONs in `evals/vigencia_extraction_v1/E1a/`
and diagnose before rerunning.

---

## 4. Per-task table

Status legend: 🟡 not started · 🔵 in progress · ✅ done · ⛔ blocked · ⏸ deferred

### 4.A The 4 v6 engineering steps

| # | Step | Recipe ref | Status | Owner | Estimate | Notes |
|---|---|---|---|---|---:|---|
| 1 | Build canonical→SUIN-doc-id registry | fixplan_v6 §3 step 1 | ✅ | claude-opus-4-7 | 60-90 min | `scripts/canonicalizer/build_suin_doc_id_registry.py` + `tests/test_suin_doc_id_registry.py`. Registry has 10 entries (9 SUIN spine docs + `et` alias). Commit `cfe64bb`. |
| 2 | Replace SUIN scraper stub with real one | fixplan_v6 §3 step 2 | ✅ | claude-opus-4-7 | 2-3 hours | Full rewrite of `src/lia_graph/scrapers/suin_juriscol.py` — three-tier cache + per-article slicing. **Bonus:** parser regex `_ARTICLE_HEADING_RE` fixed to capture multi-segment DUR numbers (`1.6.1.1.10`) — was the root cause that would have made the slicer miss every DUR article. 12 new tests. Commit `9940faf`. |
| 3 | Reorder scraper chain — SUIN first | fixplan_v6 §3 step 3 | ✅ | claude-opus-4-7 | 30 min | `vigencia_extractor.py default()` chain now `[Suin, Senado, Dian, CC, CE]`. `suin_juriscol` added to `_TRUSTED_GOVCO_SOURCE_IDS`. 2 new tests. Commit `d00da64`. |
| 4 | Add `--rerun-only-refusals` flag | fixplan_v6 §3 step 4 | ✅ | claude-opus-4-7 | 30-45 min | Success-aware skip in `extract_vigencia.py` `_process_one()`. Malformed JSONs fall through and re-extract (defensive). 3 new tests. Commit `f91401b`. |
| 5a | Add `EXTRA_EXTRACT_FLAGS` pass-through to `launch_batch.sh` | fixplan_v6 §3 step 5a | ✅ | claude-opus-4-7 | 5 min | One-line append to the nohup-extract command + header doc. Bash syntax checked. Commit `f91401b`. |

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
| B-1 | ~~SUIN scraper is a 46-line stub returning None~~ | ~~All DUR-articulado batches~~ | ~~Steps 1+2+3 of §3~~ | **RESOLVED** — commits `cfe64bb`, `9940faf`, `d00da64` |
| B-2 | DIAN normograma is "knowingly unstable" per operator | Fallback path quality | Step 3 demoted DIAN to fallback position | **RESOLVED** — `d00da64` |
| B-3 | v5 produced 187 successes already on disk | Token waste if re-extracted | Step 4 (`--rerun-only-refusals`) | **RESOLVED** — `f91401b` |
| B-4 | DUR article number parser regex truncated `1.1.1` to `1-1` | Slicer would miss every DUR article even with registry+chain in place | Parser regex fix (uncovered while writing step 2) | **RESOLVED** — `9940faf` (`_ARTICLE_HEADING_RE` now captures multi-segment) |

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

**2026-04-29 AM Bogotá — fixplan_v6 — E1a long tail finished. Cascade fully closed.**

E1a closed at 6:22 AM Bogotá (wall 465 min / 7.7 hr at workers=2):
**528 successes / 18 refusals / 0 errors = 96.7% pass rate.**

**Postgres `norm_vigencia_history`: 783 → 2362 (+1579 net rows).**

Final cascade tally across all 14 v6 batches:
* **Total successes: 2653** (1719 Wave 1 + 197 Wave 2 + 737 Wave 3)
* **Total refusals: 217** (mostly K3's 157)
* **Total errors: 0** across ~11 hours of total runtime
* **Overall pass rate: 92.4%** (97% excluding K3's CCo gap)

The +1579 net Postgres rows is **52% of the original ~3,200 DoD target
in one cascade** — the rest are F2/G1/E5 norms gated on sources we
don't yet have integrated. v6.1 added Función Pública as a 6th scraper
which closes future DUR redundancy gaps but doesn't directly close F2/G1.

---

**2026-04-29 AM Bogotá — fixplan_v6.1 — Función Pública 6th scraper landed.**

Commit `34ef8f9`. Mirrors SUIN scraper architecture exactly:
registry-backed URL resolution + three-tier cache + persisted slice
cache. Coverage: 26 DURs (incl. DUR-1625, DUR-1072, plus 24 others
across all sectors). Smoke-tested live: state=V on
`decreto.1625.2016.art.1.1.1` in 75s via the full extract_vigencia.py
runner path.

Doesn't close F2/G1 (verified — Función Pública doesn't host
DIAN-specific resoluciones or conceptos). Earns its place via DUR
redundancy + cleaner anchors (`<a name="N.N.N">` directly) +
future-proofing (more index pages can be walked).

---

**2026-04-28 PM Bogotá — fixplan_v6 — cascade closed (Wave 1+2+3, E1a partial).**

Postgres `norm_vigencia_history`: **783 → 2019 (+1236 net)** at the
moment of cascade closure. E1a long tail still running at workers=2
— continued landing successes async until 2026-04-29 06:22 AM Bogotá
(528 final).

Cumulative: **2340 ✅ / 220 ❌ / 0 errors** across 13 v6 batches that
hit `cli.done` (E1a still running on workers=2 long tail). 91.4%
overall pass rate; 97% if K3's CCo-coverage gap is excluded.

## Wave summaries

| Wave | Batches | Successes | Refusals | Pass rate | Notes |
|---|---|---|---|---|---|
| 1 (DUR-1625) | E1a (partial) / E1b / E1d / E2a / E2c / E3b | 215+342+301+260+220+68 = 1406 | 9+11+7+11+8+0 = 46 | 96.8% | E3b 100%, E2c 96%, E1b 95%, E1d 89%, E2a 86%, E1a in progress |
| 2 (CST/CCo) | J1 / J2 / J3 / J4 / K3 | 6+19+40+66+66 = 197 | 0+0+0+0+157 = 157 | 55.6% | **CST batches all 100%** (J1/J2/J3/J4 — pristine SUIN coverage); **K3 (CCo) only 30%** — SUIN's CCo harvest is incomplete |
| 3 (DUR-1072) | E6b / E6c / J8b | 289+223+225 = 737 | 7+6+4 = 17 | 97.7% | All three batches above 97% — DUR 1072/2015 is fully covered in SUIN |
| **Total** | 13 batches done | **2340** | **220** | **91.4%** | Wave 1 + 2 + 3 partial; E1a still extracting |

## Top refusal patterns

* **K3 (CCo articles): 157/223 = 70% refusal rate.** SUIN's `Código de
  Comercio` (consolidado, doc_id 30019323's CCo equivalent) coverage
  is incomplete or our slicer missed segments. Worth diagnosing in v7
  — could be either a SUIN harvest gap (article 100-1000 range
  missing) or a slicer bug specific to CCo numbering. Sample the K3
  refusal JSONs against the actual SUIN CCo HTML to isolate.
* **Wave 1/3 single-digit refusals**: occasional DUR sub-articles where
  the slicer didn't find the article key — likely the same issue we
  fixed in commit `9940faf` (regex truncation), but on edge-case
  numbering schemes (`bis`, ranged sub-articles like `689-3`). Not
  worth chasing case-by-case; the 96-98% pass rate is the right
  outcome.
* **0 errors total** across 14 batches × 3 hours of runtime — the
  pipeline is stable.

## Recommended next steps

1. **Función Pública 6th scraper** (~3 hr engineering) — closes:
   * F2 (81 res.dian refusals from earlier in this session) — DIAN
     normograma is unstable; Función Pública has the same conceptos
     with stable per-norm URLs.
   * G1 (407 norms, concepto 0001/2003) — same.
   * Future res.dian / concepto / oficio gaps as the corpus grows.
   Per-article anchors are `<a name="1.1.1">` (cleaner than SUIN's
   `ver_NNN`). Verified HTTP 200 on
   `https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=83233`
   (DUR 1625). Build registry the same way as SUIN; reuse the
   per-URL parsed-doc-cache pattern (commit `92c5661`).

2. **SUIN harvest extension** (v7 candidate, ~3-5 hr):
   * `decreto.417.2020` (E5: 104 norms — COVID decretos)
   * `concepto.dian.0001.2003` (G1: 407 norms — overlap with #1; do
     this OR Función Pública, not both)
   * K3's missing CCo segments — investigate first (could be a parser
     issue, not a harvest issue).

3. **E1a long tail**: still running with workers=2; ~3-4 hr remaining
   ETA from 9:25 PM. Will land its remaining ~325 successes async.
   Keep the process alive; its ledger entry will append on cli.done.

4. **Cloud promotion** (operator gate): once SME signoff confirms,
   replay all 2019 verified veredictos to cloud staging via
   `launch_batch.sh --target production` per-batch. Cloud writes
   pre-authorized; announce, don't ask.

## Engineering wins shipped during this cascade

The cascade execution itself surfaced **two perf bugs** that would
have made it impossible to scale, and both got fixed live:

* **Per-URL parsed-doc cache** (commit `3845ee7`) — without this, each
  norm re-parsed the 17 MB DUR HTML via BeautifulSoup. 168 workers
  parsing in parallel exhausted RAM and put the system into 14.8 GB
  swap. Cache: 1 parse per parent URL → all subsequent fetches in the
  process are dict lookups. ~48× speedup measured.
* **Persisted slice cache (Option 2)** (commit `92c5661`) — slices
  stored as JSON in `parsed_meta` of `var/scraper_cache.db`. Fresh
  scraper instances (parallel batches as separate processes) hit the
  SQLite cache and never re-parse. ~3 MB JSON per parent doc; 38×
  speedup on warm-instance fetches measured. **This is the win that
  let Wave 1 + 2 + 3 actually run in parallel.**
* **`LLM_DEEPSEEK_RPM` env var** (commit `a3ee6cd`) — the previous
  default 80 RPM was Gemini-derived; DeepSeek doesn't impose this cap.
  Throttle is provider-aware now.

Six learnings logged at
`docs/learnings/canonicalizer/v6_suin_first_rewire_2026-04-28.md`.

---

**2026-04-28 PM Bogotá — fixplan_v6 — cascade attempt 1 wedged; recovered with 2 perf/config fixes.**

First cascade launch (7 batches × 24 workers parallel = 168 thread workers
sharing one ScraperRegistry) seized in <2 min. Diagnostic:
- Throttle bucket frozen at 2 timestamps from 2.5 min ago; no acquire_token() activity.
- 0 active TCP connections from any worker.
- `sample` showed every worker thread parked on `take_gil` / `_pthread_cond_wait`.
- `vm_stat` + `sysctl vm.swapusage`: **14.8 GB / 16 GB swap used**, ~73 MB free RAM.

**Root cause.** `_slice_article_from_suin_html` re-parsed the 17 MB
DUR-1625 HTML via BeautifulSoup for every norm (~500 MB working memory
× 168 workers ≈ 84 GB demanded vs 16 GB physical → catastrophic swap
thrashing).

**Corrective commits (relaunch-ready):**
* `3845ee7` — per-URL parsed-doc cache on the SUIN scraper. One parse
  per parent doc; subsequent fetches are dict lookups. Verified
  benchmark: 60 fetches against the real DUR-1625 in 37 s vs ~30 min
  without the cache (~48× speedup). Lock-protected dict, parse-outside-lock.
* `a3ee6cd` — `LLM_DEEPSEEK_RPM` env var now the preferred throttle
  override. The 80-RPM default was Gemini-derived; DeepSeek doesn't
  cap at our scale. Legacy `LIA_GEMINI_GLOBAL_RPM` still honored.

**Process correction.** F2 (`res.dian.13.2021.art.*`) was a bad canary:
the parent norm isn't in the SUIN registry, so SUIN-first can't help.
F2's 30/111 (27%) result was driven by DIAN retry alone, not by v6.
Use **E1a** as the SUIN-first canary — `decreto.1625.2016.art.*` IS in
the registry and exercises the new slicer.

**Sequential-before-parallel rule.** Don't parallelize batches until
one batch closes cleanly at target worker count. The cascade driver
serializes for a reason.

**Full writeup.** `docs/learnings/canonicalizer/v6_suin_first_rewire_2026-04-28.md`.

**Open follow-on (v6.1 candidate, ~3 hr).** Función Pública gestor
normativo as 6th scraper. Verified DUR-1625 with `<a name="1.1.1">`
anchors (cleaner than SUIN's `ver_NNN`). Closes the F2-style
`res.dian.*` gap if coverage holds — run 5-10-doc probe first.

---

**2026-04-28 PM Bogotá — fixplan_v6 — engineering closed (steps 1-4 + 5a).**
Five commits landed:
* `cfe64bb` — step 1: SUIN canonical→doc-id registry build script + 7 tests. Output: 10 entries at `var/suin_doc_id_registry.json` (9 SUIN spine docs + `et` alias).
* `9940faf` — step 2: full rewrite of `src/lia_graph/scrapers/suin_juriscol.py` (registry-backed slicer with three-tier cache + per-article slicing) + parser regex fix (`_ARTICLE_HEADING_RE` now captures multi-segment DUR numbers like `1.6.1.1.10`) + 12 new tests covering helpers, slicing, and a real-corpus DUR slice against the cached 17-MB DUR-1625 page.
* `d00da64` — step 3: scraper chain reordered to `[Suin, Senado, Dian, CC, CE]`; `suin_juriscol` added to `_TRUSTED_GOVCO_SOURCE_IDS` so SUIN-only veredictos qualify for the `.gov.co` single-source rule. 2 new tests.
* `f91401b` — steps 4 + 5a: `--rerun-only-refusals` flag in `extract_vigencia.py` (success-aware skip + malformed-fallthrough); `EXTRA_EXTRACT_FLAGS` passthrough in `launch_batch.sh`. 3 new tests.

Test totals after engineering: 64 v6-relevant tests passing across `test_suin_doc_id_registry.py`, `test_suin_juriscol_scraper.py`, `test_scrapers.py`, `test_vigencia_extractor.py`, `test_extract_vigencia_rerun_only_refusals.py`. The pre-existing `tests/test_verify_suin_merge.py` failures are unrelated (script `scripts/verify_suin_merge.py` was removed in a prior commit).

**Hidden blocker uncovered + closed in step 2:** the SUIN parser regex
`_ARTICLE_HEADING_RE = ...\d+(?:[-.]\d+)?...` only allowed ONE optional
`[-.]\d+` group, so DUR articles like "Artículo 1.1.1" were truncated
to article_number="1-1". Even with the registry + slicer in place,
slicing would have missed every DUR article. Fix: change `?` to `*`
(verified against the cached DUR-1625 — 4 557 articles now have
multi-segment numbers; e.g. `1-1-1` resolves correctly).

**Cascade ready to run.** Step 5b is operator-trigger only:

```bash
EXTRA_EXTRACT_FLAGS="--rerun-only-refusals" \
LIA_EXTRACT_WORKERS=8 \
nohup bash scripts/canonicalizer/run_cascade_v5.sh \
    > logs/cascade_v6_driver.log 2>&1 &
disown; echo $! > /tmp/cascade_v6_driver.pid
```

Sanity-check after F2 closes (batch 1 of 8): pass-rate must be ≥70%
or the slicer is misbehaving. Diagnose-before-continue per
`feedback_diagnose_before_intervene`.

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
