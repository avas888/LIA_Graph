# State — fixplan_v4 (corpus + canonicalizer next-gate)

> **Document type.** Live progress tracker for the active workstreams in
> `fixplan_v4.md` — the canonicalizer's transition from "754 verified
> norms (Phases A–D)" to "the full ~3,400 target across A–K, with
> staging promotion + cloud writes ready when SME signs off."
>
> **Update cadence.** §3 (global state) gets touched whenever a major
> milestone closes. §4 (per-task table) is the daily working surface.
> §10 is append-only; every meaningful action gets a timestamped entry.
>
> **Authority.** This file tracks state. `fixplan_v4.md` defines scope.
> Companion trackers cover narrower slices (corpus ingest:
> `state_corpus_population.md`; per-batch: `state_canonicalizer_runv1.md`).
> When in doubt, read this file first.

---

## 1. How to use this file

This file exists so any human or LLM picking up fixplan_v4 work can
answer four questions in under 60 seconds:

1. **Where are we?** — §3 (global state) + §4 (per-task table)
2. **What's blocking us?** — §5 (active blockers) + §4 "Blockers" col
3. **What did we just do?** — §10 (run log, most-recent at top)
4. **What should I do next?** — §3 "Next action" + §6 (suggested order)

Update protocol:

* When you start a task, set status 🟡 → 🔵 in §4.
* When a task closes, set status to ✅ and add a §10 run-log entry.
* When you hit a blocker, add it to §5 + flag the affected §4 row.
* When the global state changes (e.g. a new sprint starts, a phase
  becomes unblocked), update §3.

---

## 2. Fresh-LLM preconditions

If you are an incoming agent and this is your first contact with
fixplan_v4, read in this order:

1. `CLAUDE.md` — repo-level operating guide. Already in context.
2. `docs/re-engineer/fixplan_v4.md` — full plan, especially §0
   fresh-agent on-ramp, §6.A mandatory runner protocol, §6.B ingestion
   recipe, §11 (today's update).
3. **This file** — §3, §4, §10.
4. `docs/re-engineer/state_corpus_population.md` — companion tracker
   covering the 12 expert-deliverable briefs + their per-brief status.
5. `docs/re-engineer/state_canonicalizer_runv1.md` — companion tracker
   covering per-batch canonicalizer state across phases A–K.

Memory-pinned guardrails (do not violate):

* Cloud writes (Lia Graph Supabase + Falkor) are pre-authorized — announce, don't ask. (`feedback_lia_graph_cloud_writes_authorized`)
* Beta-stance: every non-contradicting improvement flag flips ON. (`project_beta_riskforward_flag_stance`)
* Never re-extract Phases A–D — extract once, promote through three stages. (`feedback_extract_once_three_stage_promotion`)
* All canonicalizer runners delegate to `launch_batch.sh`. No re-implementation. (`feedback_runners_full_best_practices`)
* Project-wide token bucket throttle (default 80 RPM) — never bypass. (`feedback_canonicalizer_global_throttle`)
* Autonomous progression on canonicalizer batches — don't ask, just keep running until a stop condition fires. (`feedback_canonicalizer_autonomous_progression`)
* No hallucinated examples in expert-facing artifacts. Verify-or-flag. (`feedback_no_hallucinated_examples`)
* Every expert deliverable carries an exact `URL:` field. (`feedback_expert_deliverables_require_url`)
* Don't cross streams when writing for non-coder experts. (`feedback_expert_questions_no_streams_crossed`)

---

## 3. Current global state

**As of:** 2026-04-28 12:30 PM Bogotá

| Field | Value |
|---|---|
| Verified vigencia rows in Postgres | **754** (Phases A–D, unchanged today) |
| Target after Phases E–K complete | **~3,400** |
| Briefs drafted (engineer + expert versions) | **15 of 15** (12 originals + 3 gap-fills) |
| Briefs ingested into corpus | **12 of 12** (rows 13–15 await expert delivery) |
| Canonicalizer batches PASSing smoke (slice resolution) | **23 of 41** |
| Canonicalizer batches PARTIAL on smoke | **14 of 41** |
| Canonicalizer batches MISS on smoke | **4 of 41** (F1/F3/F4 + I3/I4 + K1/K2 — gap-fill briefs in flight) |
| Canonicalizer extract runs today (next-gate) | **1 of 1 attempted** (J5 — FAIL diagnostic, see §10) |
| `parsed_articles.jsonl` row count | **12 305** (was 7 922 at session start) |
| Input set unique norm_ids | **18 676** (was 12 366 at session start) |
| Active scraper gaps blocking next-gate | **3** (Senado ley fallback, SUIN realization, post-verify UI) |
| Compute budget remaining | DeepSeek-v4-pro 75% discount runs through 2026-05-05 |

**Next action.**

1. Implement Senado ley fallback in `dian_normograma.py` so 3-digit-NUM
   leyes (789/2002, 222/1995, 797/2003, 1258/2008) and recent leyes not
   yet in DIAN (2381/2024) resolve via Senado padded URLs.
2. Add `--skip-post` to `launch_batch.sh` invocations OR start
   `npm run dev` before relaunching, so the score step's chat call
   succeeds.
3. Re-run J5 with `--allow-rerun --skip-post` and confirm 3/3 extract
   PASS.
4. Cascade through priority batches: K4 → J1-J4 → G1 → F2 → K3 →
   E5 → E1a/b/d/E2a/c/E3b/E6b/c/J8b → D5 rerun.
5. Hand briefs 13/14/15 to outside experts; await deliveries.

---

## 4. Per-task table

Status legend: 🟡 not started · 🔵 in progress · ✅ done · ⛔ blocked · ⏸ deferred

### 4.A Corpus ingestion (12 original briefs + 3 gap-fills)

Detailed per-brief tracking in `state_corpus_population.md`. Roll-up:

| Workstream | Status | Owner | Notes |
|---|---|---|---|
| Briefs 01–12 (original 12) | ✅ all ingested | claude-opus-4-7 | 4356 rows, 12 commits, smoke 23 PASS / 14 PARTIAL / 4 MISS |
| Briefs 13/14/15 (gap-fill drafts) | ✅ authored | claude-opus-4-7 (with parallel agent fork) | Plain-language + technical pairs in repo, ready for expert delivery |
| Briefs 13/14/15 (expert deliveries) | 🟡 not started | unassigned | Outside experts to scour gov.co + BanRep |
| Brief 13 ingestion | 🟡 awaiting delivery | future engineer | Re-uses `ingest_expert_packet.py --brief-num 13` once packet lands |
| Brief 14 ingestion | 🟡 awaiting delivery | future engineer | Same |
| Brief 15 ingestion | 🟡 awaiting delivery | future engineer | Same |

### 4.B Canonicalizer runs (per-phase rollup)

| Phase | Slice readiness | Run status | Verdict |
|---|---|---|---|
| A (procedimiento) | ✅ pre-existing | ✅ done in prior session | 122 norms verified |
| B (renta) | ✅ pre-existing | ✅ done in prior session | 310 norms verified |
| C (IVA / retefuente / GMF) | ✅ pre-existing | ✅ done in prior session | 104 norms verified |
| D (reformas Ley) | ✅ pre-existing | ✅ done (D5 weak) in prior session | 219 norms; D5 needs `--allow-rerun` rerun |
| E (decretos / DUR) | ✅ slices populated | 🟡 not yet run | Cascades after J5 pilot rerun passes |
| F (resoluciones DIAN) | ⚠️ F2 PASS, F1/F3/F4 MISS | 🟡 not yet run | F2 ready; F1/F3/F4 await brief 13 OR YAML repair |
| G (conceptos unificados) | ⚠️ G1 PASS, G2-G5 MISS | 🟡 not yet run | G1 + G6 ready; rest await Renta concepto delivery |
| H (conceptos individuales + oficios) | ⚠️ H3a/b + H6 PASS | 🟡 not yet run | H3a/b + H6 ready; H1/H2/H4a/b/H5 keyword-YAML blocked |
| I (jurisprudencia) | ⚠️ I1 PASS, I2/I3/I4 MISS | 🟡 not yet run | I1 ready; I2 keyword-YAML; I3/I4 await brief 14 |
| J (laboral) | ✅ J1-J7 PASS smoke; ⚠️ J8 PARTIAL | 🟡 J5 trial FAIL on scrapers | Awaiting Senado fallback to retry |
| K (cambiario / societario) | ⚠️ K3 + K4 PASS, K1/K2 MISS | 🟡 not yet run | K3 + K4 ready; K1/K2 await brief 15 |
| L (refusal triage) | n/a (SME-led) | ⏸ deferred | Per master plan §10 — runs after A–K close |

### 4.C Engineer-side blockers (canonicalizer side)

| # | Item | Status | Owner | Notes |
|---|---|---|---|---|
| C-1 | DIAN URL padding for `ley.*` / `res.dian.*` | ✅ shipped | claude-opus-4-7 | Commit 1e4f16a (`dian_normograma.py::_resolve_url`) |
| C-2 | Senado fallback for ley.* not in DIAN | 🟡 not started | future engineer | Drop-in addition to scraper chain |
| C-3 | SUIN scraper realization (drop `?canonical=` stub) | 🟡 not started | future engineer | Or remove SUIN from chain entirely |
| C-4 | `--skip-post` flag on `launch_batch.sh` (for autonomous runs without UI) | 🟡 not started | future engineer | OR start `npm run dev` before each batch |
| C-5 | YAML keyword-pattern repair (F1/F3/F4 + H1/H2/H4a/b/H5 + I2) | 🟡 not started | future engineer | Per master plan §12 normally out of scope; G1 placeholder set the precedent |
| C-6 | Pool maintainer batch-id counting fix | 🟡 not started | future engineer | Tracked in fixplan §5.4 |
| C-7 | D5 canonical-id rewrite (rerun w/ tightened prompt) | 🟡 not started | future engineer | Tracked in fixplan §5.3 |
| C-8 | Cosmetic heartbeat Bogotá-date format | 🟡 not started | future engineer | Tracked in fixplan §5.5 |
| C-9 | Regenerate Phase A/B/C JSON dirs (deleted mid-session) | 🟡 not started | future engineer | Tracked in fixplan §5.2 — needed before staging promotion |

### 4.D SME / operator gates

| # | Gate | Status | Notes |
|---|---|---|---|
| O-1 | SME signoff on §1.G fixture (36-question benchmark) | 🟡 not started | Operator + Alejandro; runs against `npm run dev:staging` against local docker |
| O-2 | Approval to promote 754 verified norms to cloud staging | 🟡 not started | Gated on O-1 |
| O-3 | Approval to launch full E–K campaign (autonomous, ~10 hours wall) | 🟡 not started | Gated on C-2 + C-3 + C-4 closing |

---

## 5. Active blockers

| ID | Blocker | Affects | Recovery path |
|---|---|---|---|
| B-1 | DIAN normograma doesn't host every Colombian ley (notably 222/1995, 789/2002, 797/2003, 1258/2008, 2381/2024) | J5/J6/J7 + K4 extract phases | Implement C-2 (Senado fallback). Estimated 1–2 hours engineer time. |
| B-2 | Local UI server (`127.0.0.1:8787`) not running during `launch_batch.sh` post-verify step | Every canonicalizer batch's score gate | Implement C-4 OR run `npm run dev` in parallel terminal before launching batches. |
| B-3 | YAML keyword-based regex patterns in F1/F3/F4 + H1/H2/H4a/b/H5 + I2 require keyword segments in norm ids | Smoke check fails for those batches even with corpus populated | Implement C-5 — replace with explicit_list of real numbers OR prefix patterns. |
| B-4 | Outside experts haven't started on briefs 13/14/15 yet | F1/F3/F4 + I3/I4 + K1/K2 vigencia coverage | Operator hands packets to experts; deliveries flow back through `ingest_expert_packet.py`. |

---

## 6. Suggested next-session sequence

1. **Engineer task block (~2-3 hours):**
   * Implement C-2 (Senado ley fallback in `dian_normograma.py`).
   * Implement C-4 (`--skip-post` flag on `launch_batch.sh`).
   * Re-run J5 with `--allow-rerun --skip-post`. Expect 3/3 PASS extract.

2. **Canonicalizer cascade (~2-3 hours wall, autonomous):**
   * `bash scripts/canonicalizer/run_phase.sh --phase J` (after J5 PASS,
     should sweep J5 → J6 → J7 → J1-J4 → J8a-c).
   * `bash scripts/canonicalizer/launch_batch.sh --batch K4` then
     `K3` then `K1`/`K2` once briefs 15 lands.
   * `--batch G1` then `--batch G6` (acid test).
   * `--batch F2`.
   * `--batch E5` (COVID decretos).
   * `--batch E1a` … cascade through E1a/b/d/E2a/c/E3b/E6b/c/J8b.

3. **D5 rerun (~5 minutes):**
   * `bash scripts/canonicalizer/launch_batch.sh --batch D5
     --allow-rerun` (closes fixplan §5.3).

4. **Expert delivery + ingestion (in parallel, days):**
   * Hand briefs 13/14/15 to outside experts.
   * As packets arrive, ingest via `ingest_expert_packet.py
     --brief-num 13/14/15` per the §6.B recipe.

5. **YAML hygiene (~2 hours):**
   * Implement C-5 (replace keyword regex with explicit_list of real numbers).
   * Re-run smoke check; expect MISSes to flip to PASS.

6. **Promotion gates:**
   * O-1 (SME signoff) → O-2 (cloud promotion) → O-3 (full campaign).

---

## 10. Run log (append-only, most recent on top)

**Format:** `YYYY-MM-DD HH:MM TZ — <area> — <event>`

---

**2026-04-28 12:30 PM Bogotá — canonicalizer next-gate session 1 closed.**
Three batches attempted via the mandatory `launch_batch.sh` runner with
heartbeat sidecar + Monitor + CronCreate per fixplan §6.A:

| Batch | Norms | Verdict | Successes | Notes |
|---|---:|---|---:|---|
| J5 (rerun after fixes) | 3 | FAIL (score-side) | 1 | `ley.100.1993` verified VM since 2003-01-29; `ley.797.2003` + `ley.2381.2024` refused (`missing_double_primary_source` — DIAN 404, only Senado). |
| J6 | 3 | FAIL (score-side; ledger row missing — `--skip-post` + score still tries chat) | 1 | Same `ley.100.1993` (already inserted in J5; rerow). `ley.1438.2011` + `ley.1751.2015` refused (DIAN 404; Senado-only). |
| G6 (acid test) | 5 | FAIL | 0 | All 5 sources 404: `auto.ce.28920.*`, `concepto.dian.100208192-202`, `sent.ce.28920.*`. Scraper coverage gaps surfaced. |

**Net effect on Postgres `norm_vigencia_history`:** 754 → 758 distinct
norms (+4; the new norm rows include `ley.100.1993` + the implicit
parent rows for change-source references like `ley.797.2003`). Falkor
edges: 639 → 640 (+1 MODIFIED_BY).

**Three scraper fixes shipped (commits 1e4f16a, c03655b, d14b6a6):**

* DIAN normograma now pads NUM to 4 digits in `ley.*` and `res.dian.*`
  URLs (`ley_0100_1993.htm`, `resolucion_dian_0165_2023.htm`).
* Senado scraper does the same for ley URLs.
* SUIN stub returning `?canonical=<norm_id>` URL retired (returns
  `None` now). It was 400-then-SSL-fail looping for 10–15 s per norm,
  no chance of success. Per fixplan §5.6 SUIN is a placeholder until a
  real canonical→SUIN-id registry seeds.

**Newly surfaced scraper-coverage gaps (blocking remaining batches):**

1. **Single-source rule blocks Senado-only leyes.** The harness rejects
   norms unless ≥2 primary sources resolve. Many Colombian leyes are
   on Senado but not in DIAN normograma (3-digit-NUM laws + recent
   reforms): 222/1995, 789/2002, 797/2003, 1258/2008, 1438/2011,
   1751/2015, 2381/2024, etc. Either need (a) a third primary source
   (Función Pública), (b) the harness's single-source-acceptance rule
   triggered for `.gov.co` sources, or (c) a fallback path that pairs
   Senado + Función Pública.
2. **CE scrapers (Gap #1).** `auto.ce.<radicado>.<date>` and
   `sent.ce.<radicado>.<date>` resolve to URLs the CE site doesn't
   serve (`auto_ce_28920_2024_12_16.html` 404). Need a real radicado
   resolver or fixture-only path.
3. **Concepto with hyphenated NUM.** DIAN scraper maps
   `concepto.dian.100208192-202` to `concepto_dian_100208192-202.htm`
   which is 404. Real DIAN filename for hyphenated unified conceptos is
   different — needs mapping table or scraper case.
4. **CST + CCo scrapers (Gap #4).** Senado scraper's `_handled_types`
   doesn't include `cst_articulo` or `cco_articulo`. J1-J4 + K3 batches
   blocked.
5. **Score step's chat-replay isn't gated on `--skip-post`.** Score
   tries to read `post_*.json` regardless; errors when
   `--skip-post` skipped step 5. J6 + G6 ledger rows didn't append
   because score step crashed before append.

**Recommended next-session sequence:**

1. Add `--skip-score` flag (or fix score to respect `--skip-post`) so
   ledger rows appear cleanly for partial-source batches.
2. Add Función Pública as third primary source (URL pattern
   `https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=<NNN>`).
   Or relax single-source rule for `.gov.co` Senado.
3. Implement Gap #1 (CE auto/sent scrapers) per fixplan §5.6 + §7.
4. Add `cst_articulo` + `cco_articulo` to Senado scraper's
   `_handled_types` per fixplan §7 Gap #4.
5. Then run the cleanest cascade (J6/J7/K4/G1/F2 → E1a-f → etc.) per
   `state_fixplanv4.md` §6.

**2026-04-28 12:30 PM Bogotá — fixplan_v4 — state file initialized.**
Created this file (`state_fixplanv4.md`). Captures global state across
the corpus-population campaign + canonicalizer next-gate trial. Briefs
13/14/15 added to roll-up. Engineer + operator gates enumerated in §4.

**2026-04-28 12:09 PM Bogotá — canonicalizer J5 — pilot trial FAIL diagnostic.**
First batch run on the populated corpus. Launcher (commit 1e4f16a)
spawned `extract_vigencia.py` detached + heartbeat sidecar + CronCreate
heartbeat per fixplan §6.A. Wall time ~2.5 minutes. All 3 norms refused
at source-fetch:
* `ley.100.1993` → DIAN 404 (URL padding bug — fixed in same commit;
  `ley_100_1993.htm` → `ley_0100_1993.htm`).
* `ley.797.2003` → DIAN 404 (not in normograma — needs Senado fallback).
* `ley.2381.2024` → DIAN 404 (recent law, not yet in normograma).
Post-verify also failed (`Connection refused` on chat at 8787 — UI
server not running). Score: 0 PASS / 1 STILL_FAIL → ❌ batch FAIL.
Ledger row + run_state captured. Next iteration needs `--allow-rerun`
after Senado fallback + `--skip-post` flag land.

**2026-04-28 12:05 PM Bogotá — corpus-population — 12 of 12 briefs ingested. Campaign closed.**
Final commit 9ce3aee. `parsed_articles.jsonl` 7 922 → 12 305; input set
12 366 → 18 676. 4356 unique rows across all 12 briefs. 23 of 41
canonicalizer batches PASS the smoke check (≥80% threshold), 14
PARTIAL, 4 MISS. Per-brief commits 33d18d5 → 9ce3aee. See
`state_corpus_population.md` §10 for per-brief detail.

**2026-04-28 11:45 AM Bogotá — canon — finder regex extension shipped (commit 2bcdb59).**
Diagnosed during brief 08 smoke check: bodies with
`[CITA: Concepto DIAN 0001-2003, Numeral 1] ...` only produced parent id
in the input set because the finder's `\s+num...` group didn't tolerate
the comma. Same gap blocked decreto + resolución article-level
coverage. Extended the decreto + resolución + concepto/oficio mention
finders with the same optional-art / optional-numeral group the ley
finder already had. 118/118 canon tests still passing.

**2026-04-28 (AM) Bogotá — fixplan_v4 — corpus-population scaffolding committed (d6ee2ae).**
Pre-ingestion infrastructure landed by parallel research agents earlier
in the day, surfaced as a prerequisite for the brief-by-brief campaign:
canon ext (cst/cco/dcin/oficio with 44 new tests), 12 technical briefs
in `corpus_population/`, 12 plain-language briefs in
`corpus_population_for_experts/`, master plan + reconciliation +
brief-edits + sprint brief docs.

---

*Drafted 2026-04-28 12:30 PM Bogotá by claude-opus-4-7. Append new
entries above this line in reverse chronological order. The file's
section numbering (§1, §2, §3, §4, §5, §6, §10) intentionally skips §7-§9
to leave room for future "scraper drift", "campaign output", and
"definition of done" sections without renumbering.*
