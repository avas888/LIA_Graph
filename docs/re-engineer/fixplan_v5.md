# fixplan_v5 — close the 5 scraper / runner blockers, then cascade through phases J + K + G + F + E

> **Status:** drafted 2026-04-28 PM Bogotá right after `fixplan_v4`'s
> next-gate session 1 (commits 1e4f16a → 5dc2069) verified the
> end-to-end pipeline on the populated corpus and surfaced 5 specific
> blockers. v5 is a focused execution plan to close those 5 blockers
> and run the canonicalizer cascade across the remaining batches.
>
> **Replaces:** `fixplan_v4.md` as the active forward plan once a fresh
> agent picks up the work. v4 stays as historical context (it's where
> the corpus-ingestion + canon-extension story lives).
>
> **Authoritative companions:**
>   * `docs/re-engineer/state_fixplan_v5.md` — live progress tracker for v5 work (read this first)
>   * `docs/re-engineer/canonicalizer_runv1.md` — per-batch protocol (still current)
>   * `docs/re-engineer/state_canonicalizer_runv1.md` — live per-batch state (carries forward)
>   * `docs/re-engineer/state_fixplanv4.md` — cumulative state through session 1
>   * `docs/re-engineer/state_corpus_population.md` — per-brief ingestion tracker
>   * `CLAUDE.md` — repo-level operating guide

---

## 0. If you are a fresh agent — read this first

You are picking up a **half-shipped canonicalizer next-gate**. The
corpus is populated (12 305 rows, 4356 from outside-expert deliveries),
the canon grammar is fully extended, and the pipeline runs end-to-end
on DeepSeek-v4-pro. **One norm has already been verified through the
full pipeline** (`ley.100.1993` → state VM since 2003-01-29 by
ley.797.2003, both in Postgres `norm_vigencia_history` and as a
MODIFIED_BY edge in Falkor). What's blocking the rest is **5 concrete
items in §3 below**, all engineering tasks of ~30 min – 1 hour each.

**Read in this order before touching code:**

1. `CLAUDE.md` (loaded automatically) — repo operating guide, especially the "Long-running Python processes" + "Hot Path" sections.
2. **This file** — full read. §3 has the 5 fix recipes; §6 has the cascade plan.
3. `docs/re-engineer/state_fixplan_v5.md` — live state. The §4 per-task table tells you what's done and what's claimed.
4. `docs/re-engineer/fixplan_v4.md` §6.A "Mandatory runner protocol" — non-negotiable; every batch goes through `launch_batch.sh`.
5. `docs/re-engineer/canonicalizer_runv1.md` §0 — what the canonicalizer does per batch.

**Hot facts you should know before touching anything:**

* **DeepSeek-v4-pro is the active LLM.** `config/llm_runtime.json` resolves it via the `DEEPSEEK_API_KEY` env var loaded from `.env.local`. Pre-flight probe: `PYTHONPATH=src:. uv run python -c "from lia_graph.llm_runtime import resolve_llm_adapter; a,i=resolve_llm_adapter(); print(i['selected_provider'])"` should print `deepseek-v4-pro`.
* **Local docker stack must be up.** `docker ps` should show `supabase_db_lia-graph` and `lia-graph-falkor-dev`. If not: `make supabase-start` + the falkor compose file.
* **Project-wide Gemini/DeepSeek throttle is enforced.** Default 80 RPM. File-locked at `var/gemini_throttle_state.json`. Never bypass.
* **Run-once guard is on by default.** Each batch refuses to re-run if `evals/canonicalizer_run_v1/<batch>/run_state.json` shows DONE. Use `--allow-rerun` from operator-typed CLI to override (per fixplan_v4 §6.A rule 8 — never autonomous).
* **Cloud writes for Lia Graph are pre-authorized** (operator memory `feedback_lia_graph_cloud_writes_authorized`). For local-docker batches (target=wip) no announcement needed.
* **Phases A–D are already verified in production (754 norms).** Do NOT re-extract them. Memory: `feedback_extract_once_three_stage_promotion`. Phase D5 has a documented weak result that needs `--allow-rerun` once (see fixplan_v4 §5.3) — that's the only A-D rerun in scope.
* **Postgres count today: 758 distinct verified norms** (754 + 4 from session 1). Falkor: 11 657 norm nodes, 640 edges.
* **The corpus has 12 305 rows.** Each carries a `[CITA: ...]` body prefix that triggers `canon.find_mentions()`. The input set has 18 676 unique norm_ids.
* **3 expert briefs (13/14/15) are drafted but not yet delivered.** They cover the 4 "MISS" smoke-check batches (F1/F3/F4 + I3/I4 + K1/K2). Outside experts haven't started — operator decides timing.

**Memory-pinned guardrails (do not violate):**

* Cloud writes pre-authorized — announce, don't ask. (`feedback_lia_graph_cloud_writes_authorized`)
* Beta-stance: every non-contradicting improvement flag flips ON. (`project_beta_riskforward_flag_stance`)
* Never re-extract Phases A–D — extract once, promote through three stages. (`feedback_extract_once_three_stage_promotion`)
* All canonicalizer runners delegate to `launch_batch.sh`. No re-implementation. (`feedback_runners_full_best_practices`)
* Project-wide token bucket throttle (default 80 RPM) — never bypass. (`feedback_canonicalizer_global_throttle`)
* Autonomous progression on canonicalizer batches — don't ask, just keep running until a stop condition fires. (`feedback_canonicalizer_autonomous_progression`)
* No hallucinated examples in expert-facing artifacts. Verify-or-flag. (`feedback_no_hallucinated_examples`)
* Every expert deliverable carries an exact `URL:` field. (`feedback_expert_deliverables_require_url`)
* Don't cross streams when writing for non-coder experts. (`feedback_expert_questions_no_streams_crossed`)
* Pipeline_d organization is deliberately modular — granularize, don't collapse. (`feedback_respect_pipeline_organization`)
* Edit granularly — don't append to ≥1000-LOC files. (`feedback_granular_edits`)
* Diagnose before intervene — measure failure distribution before proposing fixes. (`feedback_diagnose_before_intervene`)

---

## 1. One-paragraph reality check

The canonicalizer pipeline works end-to-end on the populated corpus —
session 1 (2026-04-28 PM) verified `ley.100.1993` through extract →
ingest → Falkor sync. Of 11 norms attempted across 3 batches (J5
rerun + J6 + G6), only 2 succeeded — the rest hit five distinct
scraper / runner gaps that block the cascade. v5 closes those 5 gaps
in one focused engineering session (~3 hours), then runs the cleanest
batches end-to-end (J5/J6/J7/K4 + K3 CCo + J1-J4 CST + G1 IVA + F2 FE).
Estimated session-2 outcome: ≥1500 verified norms in Postgres (vs.
758 today). The remaining 4 MISS batches (F1/F3/F4 + I3/I4 + K1/K2)
need outside-expert deliveries (briefs 13/14/15) which are drafted
and ready to hand out.

## 2. What v4 accomplished

| Workstream | Outcome | Reference |
|---|---|---|
| Corpus population | 12 expert briefs ingested, 4356 rows, all round-trip-validated | `state_corpus_population.md` |
| Canon extension | cst, cco, dcin, oficio rules + finders + 44 new tests; 118/118 passing | commit d6ee2ae + 2bcdb59 |
| Canonicalizer next-gate session 1 | 1 norm verified end-to-end; 5 blockers surfaced; 3 scraper fixes shipped | commits 1e4f16a, c03655b, d14b6a6, 5dc2069 |
| Gap-fill expert briefs (13/14/15) | Drafted as plain-language + technical pairs; ready for outside experts | commit 1e4f16a |
| Live state docs | `state_fixplanv4.md` + `state_corpus_population.md` + `state_canonicalizer_runv1.md` | commits 7883256 + 5dc2069 |

**Cumulative numbers (start of session 2):**

* `parsed_articles.jsonl`: 12 305 rows
* `evals/vigencia_extraction_v1/input_set.jsonl`: 18 676 unique norm_ids
* Postgres `norm_vigencia_history`: 758 distinct verified norms
* Falkor `(:Norm)`: 11 657 nodes, 640 edges
* Smoke check across 41 batches: 23 PASS, 14 PARTIAL, 4 MISS (F1/F3/F4, I3/I4, K1/K2)

## 3. The 5 blockers — fix recipes

Each blocker has: **what** (the gap), **where** (file:line to edit),
**how** (the fix), **why** (the reason), **test** (regression coverage),
and **estimate** (rough wall-time for a focused agent).

### Blocker #1 — Single-source rule rejects Senado-only leyes

**What.** The harness's pre-LLM source-fetch check requires ≥2 primary
sources to return valid content; otherwise it refuses with
`refusal_reason: "missing_double_primary_source"`. Many Colombian
leyes live on `secretariasenado.gov.co` but NOT on
`normograma.dian.gov.co`:

* 3-digit-NUM laws: 222/1995, 789/2002, 797/2003
* 4-digit-NUM laws: 1258/2008, 1438/2011, 1751/2015, 2381/2024
* Reform pensional and recent SAS / cambio leyes generally

For these the chain produces 1 valid source (Senado) + 0–1 errors
(DIAN 404 + SUIN disabled) → refused. Without this fix, J5/J6/J7/K4
explicit-list batches max out at 1/3 success (the lone DIAN-hosted
ley.100.1993).

**Where.** Two viable approaches; pick one:

* **Approach A (preferred)** — extend the primary-source chain with
  Función Pública. Edit `src/lia_graph/scrapers/` to add a new
  `funcion_publica.py` scraper. URL pattern observed in the expert
  deliveries: `https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=<NNN>`
  where `<NNN>` is the gestor-normativo internal id (NOT the canonical
  norm id). Look up `i=<NNN>` from a seed table you maintain at
  `var/funcion_publica_lookup.json` keyed by canonical norm_id. The
  expert briefs 11 + 12 already gave us several anchors (e.g.
  `ley.789.2002 → i=6778`, `ley.2381.2024 → i=246356`,
  `ley.222.1995 → i=funcion_publica_id_for_ley_222`). Register the new
  scraper in the harness's primary-source chain (look at
  `src/lia_graph/vigencia_extractor.py` for the chain wiring).
* **Approach B (faster, lower confidence)** — relax the harness's
  double-source rule to single-source acceptance for `.gov.co` Senado
  pages. Edit `src/lia_graph/vigencia_extractor.py` (or wherever
  `missing_double_primary_source` is raised; grep for it). Add a
  branch: if the lone-passing source is `secretaria_senado` AND the
  fetched content is non-empty AND contains the article number
  pattern, allow the LLM call. This widens the harness's risk surface
  but matches the existing prompt rule for "single-source acceptance
  for `.gov.co` primary sources" (per fixplan_v4 §2.3 bug fix #14).

**Why.** This is the #1 unlock — without it, ~half of the remaining
batches' explicit_lists never reach 2/2 success regardless of any
other fix. With it, J5/J6/J7/K4 should hit 100% on next attempt.

**Test.** Add a smoke test in `tests/test_vigencia_extractor.py`:
launch a live extract for `ley.789.2002` against fixtures, expect
either (a) Función Pública URL fetched OR (b) Senado-only acceptance
with a non-empty veredicto returned.

**Estimate.** 60–90 min for Approach A (new scraper + lookup table +
chain wiring + 1 test). 20–30 min for Approach B (edit one branch +
1 test). Operator preference TBD — Approach A is cleaner, B is
faster.

### Blocker #2 — Consejo de Estado auto/sent scrapers (Gap #1)

**What.** `auto.ce.<radicado>.<YYYY>.<MM>.<DD>` and
`sent.ce.<radicado>.<YYYY>.<MM>.<DD>` resolve to URLs the CE site
doesn't actually serve. Session 1's G6 acid test hit 404 on
`auto_ce_28920_2024_12_16.html` and `sent_ce_28920_2025_07_03.html`.
The CE site (consejodeestado.gov.co) is a JS-rendered SPA — direct
URL access by radicado isn't supported.

**Where.** `src/lia_graph/scrapers/consejo_estado.py` —
`_resolve_url()` method. Currently returns the 404 URL pattern.

**How.** Two paths (master plan §7 documents both):

* **Live-fetch path** — implement `_resolve_url` to hit CE's
  search-by-radicado RPC. The CE search endpoint is at
  `https://www.consejodeestado.gov.co/decisiones_u/` (or a backend
  JSON endpoint discovered via browser devtools). Likely needs
  Selenium / playwright to render the SPA. Significant effort.
* **Fixture-only path (recommended for v5)** — drop in HTML fixtures
  at `tests/fixtures/scrapers/consejo_estado/autos/<radicado>.<YYYY>.<MM>.<DD>.html`
  and `.../sentencias/<radicado>.<YYYY>.<MM>.<DD>.html`. Configure the
  scraper's cache layer to check fixtures first. The brief 14 expert
  delivery (when it lands) will provide the texts. For now, fixture
  the 5 acid-test ids by hand from the auto/sent text already
  available in `evals/canonicalizer_run_v1/E4/` (Decreto 1474/2025
  autos).

**Why.** Unblocks G6 acid test + I3/I4 batches (after brief 14 lands).

**Test.** Update `tests/test_scrapers.py::test_consejo_estado_url`
to assert fixture-only path returns a fixture URL OR `None`.

**Estimate.** 30–45 min for fixture-only path (5 acid-test fixtures +
scraper case). 4–6 hours for live-fetch path (Selenium / playwright
infra). Recommend fixture-only for v5.

### Blocker #3 — Concepto with hyphenated NUM filename mapping unknown

**What.** DIAN scraper maps `concepto.dian.100208192-202` →
`concepto_dian_100208192-202.htm` (404). DIAN's actual filename for
hyphenated unified conceptos uses a different pattern. Session 1's G6
test hit 404 three times on this URL pattern (parent + 2 numerals all
fetch the parent doc).

**Where.** `src/lia_graph/scrapers/dian_normograma.py` —
`_resolve_url()`, the `concepto.dian.<NUM>-<SUFFIX>` branch.

**How.** Discover the real DIAN URL pattern empirically:

```bash
# The unified Renta concepto with suffix 202 — what does DIAN serve?
for path in \
  "concepto_dian_100208192_202.htm" \
  "concepto_general_100208192-202.htm" \
  "concepto_unificado_100208192-202.htm" \
  "concepto_tributario_dian_100208192-202.htm" \
  "concepto_100208192-202.htm" \
  "100208192-202.htm" ; do
    code=$(curl -sI "https://normograma.dian.gov.co/dian/compilacion/docs/$path" | head -1 | grep -oE '[0-9]{3}')
    echo "$code  $path"
done
```

Once a 200 is found, update `_resolve_url`:

```python
if norm_id.startswith("concepto.dian.") and "-" in norm_id.split(".")[2]:
    # hyphenated unified concepto (e.g., concepto.dian.100208192-202)
    parts = norm_id.split(".")
    num_with_suffix = parts[2]  # "100208192-202"
    return f"{_BASE_URL}/<the-real-pattern>_{num_with_suffix}.htm"
```

If no DIAN URL works, fall back to fixture-only (same approach as #2).

**Why.** Unblocks G6 acid test ingestion + future G2-G5 batches when
those expert deliveries land.

**Test.** `tests/test_scrapers.py::test_dian_normograma_concepto_hyphen_url`.

**Estimate.** 20–30 min (URL discovery + regex case + 1 test).

### Blocker #4 — Senado scraper missing CST + CCo support (Gap #4)

**What.** `secretaria_senado.py::_handled_types` is
`{"ley", "ley_articulo", "estatuto", "articulo_et"}` — no
`cst_articulo` or `cco_articulo`. J1-J4 (CST ranges, ~170 norms) +
K3 (CCo articles, ~315 norms) batches blocked at scraper-resolution
level: the chain has no scraper that handles these norm types.

**Where.** `src/lia_graph/scrapers/secretaria_senado.py` —
`_handled_types` set + `_resolve_url()` method.

**How.** Add CST + CCo URL patterns. Both live on Senado at:

* CST: `http://www.secretariasenado.gov.co/senado/basedoc/codigo_sustantivo_trabajo.html`
  + paginated segments `codigo_sustantivo_trabajo_pr00X.html` (per
  `corpus_population/01_cst.md`).
* CCo: `http://www.secretariasenado.gov.co/senado/basedoc/codigo_comercio.html`
  + paginated segments (per `corpus_population/12_cambiario_societario.md`).

```python
# Add to _handled_types
_handled_types = {
    "ley", "ley_articulo", "estatuto", "articulo_et",
    "cst_articulo", "cco_articulo",
}

# Add to _resolve_url
if norm_id.startswith("cst.art."):
    # The full CST is on one page; article-scoped slicing happens
    # in fetch() via <a name="N"> anchors. Pagination segments
    # (pr001..pr016) are fallbacks if a specific anchor isn't on
    # the master page.
    return f"{_BASE_URL}/codigo_sustantivo_trabajo.html"
if norm_id.startswith("cco.art."):
    return f"{_BASE_URL}/codigo_comercio.html"
```

If anchor-based slicing doesn't reliably find articles, paginate
similar to ET (build an index via `scripts/canonicalizer/build_senado_et_index.py`
shape — there's a precedent for that pattern).

**Why.** Unblocks ~485 norms (J1-J4 + K3) — the largest single
unlock after blocker #1.

**Test.** `tests/test_scrapers.py::test_senado_cst_url` +
`test_senado_cco_url`.

**Estimate.** 45–60 min (URL patterns + handled_types + 2 tests +
optional anchor-index build).

### Blocker #5 — Score step crashes on `--skip-post`

**What.** When `launch_batch.sh --skip-post` is passed, step 5
(post-verify) is skipped — but step 6 (score) still tries to read
`evals/canonicalizer_run_v1/<batch>/post_*.json` and errors out:
```
[ERROR] No post_*.json in evals/canonicalizer_run_v1/J6 — run --mode post first.
```
Score errors before appending to `ledger.jsonl`, so J6 + G6 in
session 1 left ledger gaps despite the extracts succeeding/failing.

**Where.** `scripts/canonicalizer/launch_batch.sh` — the score step's
post-json-read OR the score-step CLI invocation in
`scripts/canonicalizer/run_batch_tests.py` (or wherever the score
logic lives — grep for `No post_*.json`).

**How.** Two equally-valid fixes:

* **Option A** — gate the score step itself on `--skip-post`:
  ```bash
  # In launch_batch.sh, around the score step:
  if [[ -n "$SKIP_POST" ]]; then
    SKIP_SCORE=${SKIP_SCORE:-1}  # default skip-score when post is skipped
  fi
  ```
  And/or: when `--skip-post` is passed, the score step emits a
  ledger row with `post_test_results: null` and `verdict:
  "EXTRACT_ONLY"` instead of erroring.
* **Option B** — add a `--skip-score` flag that's independent of
  `--skip-post`. The launcher already has `--skip-score` per its
  arg-parser (`scripts/canonicalizer/launch_batch.sh:64`). Just
  default `SKIP_SCORE=1` when `SKIP_POST=1`, OR document that
  autonomous runs should pass both flags.

**Why.** Without this, every batch run with `--skip-post` (the only
way to run autonomously without the dev UI server) leaves ledger gaps
that confuse the campaign verdict roll-up.

**Test.** Add an end-to-end test that runs `launch_batch.sh --batch
G6 --skip-post --dry-run` and asserts a ledger-row schema is emitted
(or skipped cleanly with documented status).

**Estimate.** 15–20 min.

---

## 4. Cascade plan after the 5 fixes land

**Order (top of `state_fixplan_v5.md` §6 mirrors this).** Run sequentially
via `launch_batch.sh --batch <X> --allow-rerun --skip-post` (or
`--skip-post --skip-score` per blocker #5 outcome). Use `Monitor` +
`CronCreate` heartbeat for each. Per memory
`feedback_canonicalizer_autonomous_progression`, do not ask
between batches — keep going unless a stop condition fires (per
fixplan_v4 §6.A "Kill-switches").

| Order | Batch | Slice size | Expected verified | Why this order |
|---:|---|---:|---:|---|
| 1 | J5 (rerun) | 3 (explicit_list) | 3 | Confirms blocker #1 fix; smallest sanity batch |
| 2 | J6 (rerun) | 3 | 3 | Same — uses ley.100/1438/1751 trio |
| 3 | J7 (rerun) | 3 | 3 | ley.789/1822/2114 — confirms Senado-only fix |
| 4 | K4 (rerun) | 2 | 2 | ley.222/1258 — last small explicit_list |
| 5 | J1 | ~25 | ~25 | First CST batch — confirms blocker #4 |
| 6 | J2 | ~40 | ~40 | CST cont. |
| 7 | J3 | ~35 | ~35 | CST cont. |
| 8 | J4 | ~60 | ~60 | CST collective |
| 9 | K3 | ~315 | ~315 | CCo articles — biggest blocker-#4 unlock |
| 10 | G1 | ~407 | ~407 | IVA Concepto Unificado numerals |
| 11 | G6 (rerun) | 5 | 5 | Acid test — confirms blockers #2 + #3 |
| 12 | F2 | ~111 | ~111 | Resoluciones DIAN factura electrónica |
| 13 | E5 | ~104 | ~104 | Decretos legislativos COVID |
| 14 | E6b | ~296 | ~296 | DUR 1072 riesgos |
| 15 | E6c | ~229 | ~229 | DUR 1072 SST |
| 16 | E1a | ~356 | ~356 | DUR 1625 sub-libros 1.1+1.2 |
| 17 | E1b | ~82 | ~82 | DUR 1625 sub-libros 1.3+1.4 |
| 18 | E1d | ~307 | ~307 | DUR 1625 sub-libro 1.6 |
| 19 | E2a | ~271 | ~271 | DUR 1625 IVA |
| 20 | E2c | ~228 | ~228 | DUR 1625 retefuente |
| 21 | E3b | ~68 | ~68 | DUR 1625 sanciones |
| 22 | J8b | ~229 | ~229 | DUR 1072 (shared with E6) — likely cache-hit fast |
| 23 | D5 (rerun) | ~39 | ~36 | Closes fixplan_v4 §5.3 D5 weak-result follow-up |

**Estimated session-2 wall-time (sequential, DeepSeek 80 RPM throttle):**
~4–5 hours for batches 1–23 above. Total verified-norm growth: 758 →
~3 200 (close to the ~3 400 DoD; remaining gap is the 4 MISS batches
awaiting briefs 13/14/15).

**Pool-maintainer parallelism (optional, ~2× speedup):** Per
fixplan_v4 §5.4 the pool counter has a known overshoot bug — fix that
first OR run sequentially. For v5 recommend sequential to avoid the
bug; revisit parallel after counter fix.

---

## 5. What v5 does NOT cover (carry-forward backlog)

These items are tracked in `state_fixplanv4.md` §4.C / §5 + this
file's §3 but explicitly out of v5 scope:

* **YAML keyword-pattern repair** for F1/F3/F4 + H1/H2/H4a/b/H5 + I2.
  Replace keyword regex with explicit_list of real numbers OR prefix
  patterns. Out of v5 — gates the 4 MISS batches but those need
  expert deliveries (briefs 13/14/15) anyway. Treat as session 3.
* **SUIN scraper realization** (drop the disabled stub; build a real
  canonical→SUIN-id registry). Out of v5 — DIAN + Senado +
  Función Pública (after blocker #1) covers >95% of cases. Backlog.
* **Local UI server permanent solution.** Currently every score step
  needs `npm run dev` running. Long-term either start it
  programmatically or drop the chat-replay from the score gate. Out of
  v5; blocker #5 (the launcher fix) papers over this for autonomous
  runs.
* **Pool maintainer counter bug** (fixplan_v4 §5.4). Out of v5 —
  sequential cascade avoids the issue.
* **Phase A/B/C JSON regeneration** (fixplan_v4 §5.2). Needed before
  cloud-staging promotion (O-2 gate). Out of v5; revisit when SME
  signoff for staging promotion is in motion.
* **Cosmetic heartbeat Bogotá date format bug** (fixplan_v4 §5.5).
  Out of v5; fix opportunistically.
* **Outside-expert deliveries for briefs 13/14/15.** Operator hands
  packets to outside experts; ingestion happens via
  `ingest_expert_packet.py --brief-num 13/14/15`. Schedule
  separately.

---

## 6. Quick-start for resuming

```bash
# 1. Source env
set -a; . .env.local; set +a

# 2. Confirm provider
PYTHONPATH=src:. uv run python -c "
from lia_graph.llm_runtime import resolve_llm_adapter
a, i = resolve_llm_adapter()
print(f'{i[\"selected_provider\"]} ({i[\"adapter_class\"]}, {i[\"model\"]})')"
# Expected: deepseek-v4-pro (DeepSeekChatAdapter, deepseek-v4-pro)

# 3. Confirm docker
docker ps --format '{{.Names}}' | grep -E "(supabase_db_lia-graph|lia-graph-falkor-dev)"

# 4. Read state
cat docs/re-engineer/state_fixplan_v5.md
```

**Then for engineering work on the 5 blockers**, follow each §3
recipe sequentially. Run tests after each:
`PYTHONPATH=src:. uv run pytest tests/test_scrapers.py tests/test_canon.py -q`.

**For the cascade run after fixes land**, follow §4 batch-by-batch
order via `bash scripts/canonicalizer/launch_batch.sh --batch <X>
--allow-rerun --skip-post` (or `--skip-post --skip-score` if blocker
#5 isn't fully closed yet).

**Per fixplan_v4 §6.A — every batch must:**
1. Launch via `launch_batch.sh` (never `extract_vigencia.py` direct).
2. Have an auto-armed heartbeat sidecar (the launcher does this).
3. For multi-batch / multi-hour runs, ALSO arm a `CronCreate` 3-min heartbeat (belt + suspenders).
4. Use `Monitor` to watch for terminal events (extract done, ledger row appears, kill-switch triggers).
5. Atomic JSON writes only (`vigencia_extractor.write_result` is the canonical path).
6. Pre-flight the throttle + provider before launching.
7. Honor the run-once guard; rerun requires explicit `--allow-rerun`.

---

## 7. Numbers that matter

**Today (start of session 2):**

* Postgres `norm_vigencia_history`: **758** distinct verified norms (754 from A–D + 4 from session 1)
* Falkor `(:Norm)`: **11 657** nodes, **640** edges
* `parsed_articles.jsonl`: **12 305** rows
* Input set: **18 676** unique norm_ids
* Smoke check across **41** batches: 23 PASS, 14 PARTIAL, 4 MISS

**Session-2 target (after the 5 blockers + cascade):**

* Postgres: **~3 200** distinct verified norms (close to the ~3 400 DoD)
* Falkor edges: **~3 000+** structural edges
* Smoke check: 38–40 batches PASS (4 MISS still gated on expert deliveries)

**v5 wall-time estimate:**

* Engineering (5 blockers): **~3 hours**
* Cascade run (sequential, 23 batches): **~4–5 hours**
* Total: **1 working day** for v5 to reach session-2 target.

---

## 8. File index — where to look

| Concern | File |
|---|---|
| What does v5 close? | This file §3 |
| Live state for v5 | `docs/re-engineer/state_fixplan_v5.md` |
| Cumulative state through v4 | `docs/re-engineer/state_fixplanv4.md` |
| Per-batch state | `docs/re-engineer/state_canonicalizer_runv1.md` |
| Per-brief corpus state | `docs/re-engineer/state_corpus_population.md` |
| YAML batch defs | `config/canonicalizer_run_v1/batches.yaml` |
| Mandatory runner protocol | `docs/re-engineer/fixplan_v4.md` §6.A |
| Mention finder + rules | `src/lia_graph/canon.py` |
| Scraper registry + chain | `src/lia_graph/scrapers/` (DIAN, Senado, SUIN, CC, CE) |
| Vigencia extractor (where double-source rule lives) | `src/lia_graph/vigencia_extractor.py` |
| LLM provider config | `config/llm_runtime.json` |
| Token-bucket throttle | `src/lia_graph/gemini_throttle.py` |
| Adapter retry policy | `src/lia_graph/gemini_runtime.py` |
| Scraper cache (SQLite, WAL) | `var/scraper_cache.db` |
| API throttle state | `var/gemini_throttle_state.json` |
| Senado ET pr-segment map | `var/senado_et_pr_index.json` |

---

## 9. Decision history + current path

The 2026-04-28 PM v4 closing recap (commit 5dc2069) posed: keep
debugging scrapers in v4 OR scope a clean v5 around the 5 specific
blockers? **v5 chosen** because:

* The 5 blockers are well-understood (each has a fix recipe, file:line, test target).
* Stretching v4 risks losing the closure narrative on the corpus campaign + canon extension (those are clean wins worth preserving as a stable v4 reference).
* A fresh agent picking up v5 has zero context cost — §0 + §3 hand them everything.

**Path chosen 2026-04-28 PM:** v5 closes the 5 blockers in one
engineering session, runs the cascade, and ends with the corpus at
~3 200 verified norms — close enough to the ~3 400 DoD that the
remaining gap is purely waiting on briefs 13/14/15 expert
deliveries.

**What the next agent will be doing:** open
`state_fixplan_v5.md`, claim a blocker from §4, edit the relevant
file per §3 of this doc, run tests, commit, mark task ✅, claim the
next one. After all 5 close, run the §4 cascade sequentially. Update
`state_fixplan_v5.md` §10 run log along the way.

**Recommended first blocker:** #5 (score `--skip-post` crash, ~15
min). Tiny, isolated, makes every subsequent cascade run cleaner.
Then #1 (single-source rule, ~30 min — pick Approach B for v5).
Then #4 (CST + CCo Senado, ~45 min — biggest unlock per norm-count).
Then #3 (concepto-hyphen DIAN URL, ~20 min). Then #2 (CE
fixture-only, ~30 min). Total: ~2.5 hours. Then cascade.

---

*Drafted 2026-04-28 PM Bogotá by claude-opus-4-7 immediately after
fixplan_v4 session 1 (commit 5dc2069). v5 supersedes v4 as the active
forward plan. v4 stays in repo as historical context — its §0
fresh-agent on-ramp + §6.A mandatory runner protocol + §6.B ingestion
recipe are still load-bearing references for the cascade.*
