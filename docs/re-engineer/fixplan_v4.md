# fixplan_v4 — canonicalizer shipped + corpus-coverage gap is the next gate

> **Status:** drafted 2026-04-28 morning Bogotá after the autonomous DeepSeek-v4-pro
> campaign halted on Phase E + F empty-slice cluster. Read this once if you're a
> fresh LLM or a new engineer picking up the canonicalizer work cold.
>
> **Replaces:** `fixplan_v3.md` as the active forward plan. v3 covered the
> "build the canonicalizer" arc; v4 covers "extend coverage + promote to staging."
> v3 stays in the repo as historical context — closed sub-fixes there are
> still load-bearing.
>
> **Authoritative companions:**
>   * `docs/re-engineer/canonicalizer_runv1.md` — per-batch protocol (still current)
>   * `docs/re-engineer/state_canonicalizer_runv1.md` — live per-batch state
>   * `docs/re-engineer/corpus_population_plan.md` — what the corpus-ingestion expert needs to deliver to unblock Phases E–K
>   * `CLAUDE.md` — repo-level operating guide (unchanged)

---

## 1. One-paragraph reality check

The canonicalizer has been **built end-to-end** and **runs autonomously
in production conditions** against local Supabase + Falkor. It has
verified vigencia for **754 unique norms** (Phases A/B/C/D) and laid
**642 structural edges** in Falkor. The pipeline is provider-agnostic
(DeepSeek-v4-pro primary, Gemini fallback). Throttle, retry, parallel
agents, sustained pool maintainer, heartbeat sidecars, and durable
atomic JSON writes all work. The next unlock is **corpus ingestion**:
roughly 1,690 of the canonicalizer's intended ~3,400 norms are missing
from `artifacts/parsed_articles.jsonl` at the canonical id-shapes the
batches expect. The canonicalizer can't extract what isn't in the
corpus.

## 2. What we accomplished (yesterday + this morning)

### 2.1 Pipeline built

Code shipped during the v3 → v4 transition:

| Component | Lives in | Function |
|---|---|---|
| Per-batch launcher | `scripts/canonicalizer/launch_batch.sh` | full pipeline driver: pre-baseline → detached extract → ingest → falkor sync → post-verify → score → ledger row |
| Phase-level driver | `scripts/canonicalizer/run_phase.sh` | runs all batches in a phase in dep order, stops on per-batch FAIL |
| Parallel orchestrator | `scripts/canonicalizer/run_parallel_extract.sh` | extract phase parallel (default 2 concurrent, configurable), post phase serialized |
| Full-campaign runner | `scripts/canonicalizer/run_full_campaign.sh` | drives Phase B-rerun → K end-to-end with auto-stop on quota exhaustion |
| Sustained-pool maintainer | embedded Monitor pattern | keeps N workers active, launches next batch from queue when slots open (used yesterday at 6–7 concurrent) |
| Verbose 3-min heartbeat | `scripts/canonicalizer/heartbeat.py` + sidecar in `launch_batch.sh` | mandatory per-batch live state with STATE=… first line, ASCII progress bar, state breakdown, kill-switch checks; sidecar auto-arms on extract launch |
| Site index builder | `scripts/canonicalizer/build_senado_et_index.py` | sweeps Senado pr-segments, builds `var/senado_et_pr_index.json` (887 ET articles) |
| Project-wide token-bucket throttle | `src/lia_graph/gemini_throttle.py` (vendor-neutral despite the name) | file-locked cross-process Gemini/DeepSeek RPM cap, default 80 RPM |
| Adapter retry on 5xx/429 | `src/lia_graph/gemini_runtime.py::_request` | 4 attempts at 0/4/12/30 s back-off, applies to both Gemini and DeepSeek paths |
| Provider-agnostic harness | `src/lia_graph/vigencia_extractor.py::_default_adapter` | reads `config/llm_runtime.json` via `resolve_llm_adapter()`; switching providers is a one-line config change |
| Atomic per-norm JSON write | `vigencia_extractor.py::write_result` | temp + rename + fsync — power-loss-safe |
| Article-scoped slicing | `src/lia_graph/scrapers/{secretaria_senado,dian_normograma}.py` | `[[ART:N]]` markers injected at `<a name="N">` anchors; per-article slice at fetch time so prompt doesn't see the wrong chunk |

### 2.2 Operational tools shipped

| | |
|---|---|
| Site learnings | `docs/learnings/sites/{secretariasenado,normograma-dian,suin-juriscol,corte-constitucional,consejo-de-estado}.md` — per-site quirks, recovery playbooks |
| Canonicalizer learnings | `docs/learnings/canonicalizer/A1_first_real_run_2026-04-27.md` — refusal taxonomy + fix history |
| Failure catalog (auto-generated) | `evals/canonicalizer_run_v1/phase_B_failure_catalog.md` — per-norm refusal table, re-run recommendations |
| Campaign log | `evals/canonicalizer_run_v1/campaign_log.md` — one row per phase with verdict |
| Per-batch ledger | `evals/canonicalizer_run_v1/ledger.jsonl` — append-only batch verdicts, §4 schema |

### 2.3 Bug fixes that landed (in order discovered)

1. **Env var name** — harness was reading `LIA_GEMINI_API_KEY`; the repo (and `.env.local`) uses `GEMINI_API_KEY`. Patched repo-wide with legacy alias fallback.
2. **`run_batch_tests.py` ROOT path** — `Path(__file__).parent.parent` resolved to `scripts/` after the canonicalizer-folder move. Fixed to `parents[2]`.
3. **3-second false-crash detection** — fast-finishing extracts (refusal cascades) were misreported as crashes. Now distinguishes via `cli.done` event grep.
4. **Senado HTTPS port 443 unreachable** — switched scraper to HTTP. Documented in `docs/learnings/sites/secretariasenado.md`.
5. **Senado URL pattern wrong** — removed `/codigo/` segment from path; `_pr_section` formula `n // 10` was wrong; replaced with index lookup.
6. **DIAN normograma had no ET handler** — added; full-ET page (~3.9 MB) used as second primary source for every `et.*` norm.
7. **DIAN normograma had no ley handler** — added `ley_NUM_YEAR.htm` URL pattern + per-article slicing; unblocked Phase D entirely.
8. **certifi-backed SSL context** — fixes SUIN's Sectigo cert that macOS Python's default trust store doesn't accept.
9. **Adapter retries** — added 4-attempt 5xx/429 retry with exponential backoff. Fixed Gemini's "model overloaded" cluster on cohort 1.
10. **Project-wide token bucket** — file-locked RPM cap shared across all parallel processes. Default 80 RPM (under 1M TPM cap given ~12K-token calls).
11. **Parser tolerance for list-shape Citations** — `vigencia.py::_first_citation()` accepts dict, list (takes first), or None for `derogado_por`/`inexequibilidad`/`suspension`/`regimen_transicion`. Recovered the §1.G regression marker (Art. 689-1 = DE).
12. **Senado index nearest-neighbor fallback** — when an ET article isn't in the index (anchor format quirk), falls back to the nearest enumerated article's pr-segment.
13. **Partial-ingest tolerance** — launcher's "bail on any ingest error" replaced with "log warning and continue if at least one row inserted."
14. **Skill prompt — 11 explicit rules** — including literal Vigencia JSON example, ChangeSourceType enum, applies_to_kind enum, V-state-no-change_source, Citation shape, interpretive_constraint shape, single-source acceptance for `.gov.co` primary sources.

### 2.4 Provider migration complete

Migrated from Gemini-2.5-pro to **DeepSeek-v4-pro** mid-day after Gemini hit
its 1,000 RPD daily quota. DeepSeek-v4-pro:

- Accepted via the existing `LLMAdapter` protocol — zero code changes to the harness
- Same Vigencia veredicto shape as Gemini
- 0 retries, 0 final-429 refusals across **5 hours and up to 7 concurrent agents** in the autonomous campaign
- Currently 75% off through 2026-05-05 → cheaper than Gemini even with the discount inverted

## 3. Durable state right now

```
Postgres `norm_vigencia_history`:
  Phase A (procedimiento)          122 unique norms
  Phase B (renta)                  310 unique norms
  Phase C (IVA / retefuente / GMF) 104 unique norms
  Phase D (reformas Ley)           219 unique norms
  TOTAL                            754 unique norms / 1,051 history rows

Falkor `(:Norm)` mirror:
  11,657 nodes
  642 structural edges (453 MODIFIED_BY, 183 DEROGATED_BY, 3 REVIVED_BY,
                        1 SUSPENDED_BY, 1 INEXEQUIBLE_BY, 1 CONDITIONALLY_EXEQUIBLE_BY)

JSON veredictos on disk:
  evals/vigencia_extraction_v1/<batch>/*.json  (only D dirs survived; A/B/C
  dirs were inadvertently deleted mid-session — Postgres data is intact but
  the JSONs need regeneration if cloud staging promotion needs them)

Ledger:
  evals/canonicalizer_run_v1/ledger.jsonl — 30 batches with rich §4 rows
```

## 4. Why the campaign halted

Phases E–K resolve to **0 norms** in the current corpus. Specifically:

| Phase | Slice size today | Slice size if corpus were complete |
|---|---:|---:|
| E (decretos / DUR) | 6 (E4 acid test only) | ~500 |
| F (resoluciones DIAN) | 2 | ~140 |
| G (conceptos unificados) | 7 (G6 acid test only) | ~390 |
| H (conceptos individuales) | 0 (regex over-matches but corpus actually empty) | ~430 |
| I (jurisprudencia) | 5 (I1 acid test) | ~70 |
| J (laboral) | 9 (J5/J6/J7 acid tests) | ~430 |
| K (cambiario) | 2 (K4 acid test) | ~150 |
| **Missing** | | **~1,690 norms** |

The canonicalizer's batch YAML's prefix patterns (e.g.
`decreto.1625.2016.libro.1.5.*`) don't match anything in
`artifacts/parsed_articles.jsonl`. The canonicalizer can't extract what
the corpus doesn't have at the canonical id-shape it expects.

This is **not a canonicalizer bug**. The harness, scrapers, prompts,
parser, throttle, retry, and Vigencia schema are all working.

## 5. What comes next (in priority order)

### 5.1 Corpus population for Phases E–K

**Authoritative spec:** `docs/re-engineer/corpus_population_plan.md`.

Twelve source briefs (one per family — CST, DUR 1625, DUR 1072, COVID
legislativos, resoluciones DIAN, conceptos unificados, conceptos
individuales, jurisprudencia, pensional/parafiscales, cambiario/
societario) need to be drafted by the corpus-ingestion expert(s) per
the layout in §9 of that doc. The output is rows appended to
`artifacts/parsed_articles.jsonl` plus the three small scraper gaps
documented in §5.4 of the population plan (`auto.ce.*`,
`cst.art.*`, `decreto.legislativo.*`).

**Wall estimate for the canonicalizer side after corpus is populated:**
~10 hours of DeepSeek-v4-pro time, ~$6 in API spend, 6 concurrent
workers, autonomous via `bash scripts/canonicalizer/run_full_campaign.sh`.

### 5.2 Cloud staging promotion of the 754 already-verified norms

Per `canonicalizer_runv1.md` §9 (3-stage promotion): once Stage 1
(local docker) is at quality bar, replay the JSONs to cloud staging
via `scripts/canonicalizer/ingest_vigencia_veredictos.py --target production`.
Two prerequisites before staging is safe:

1. **SME signoff on §1.G fixture** against local docker — the 36-question
   benchmark in `state_fixplan_v3.md` §1.G. Operator + SME (Alejandro)
   need to run this end-to-end against `npm run dev:staging` pointed at
   local docker URLs and sign off in
   `evals/canonicalizer_run_v1/local_docker_signoff.md`.
2. **Regenerate JSON dirs for Phases A/B/C** — they were inadvertently
   deleted during a cleanup. Postgres data survives but the canonical
   artifact for promotion is the JSONs. Two paths: (a) re-extract A/B/C
   on DeepSeek-v4-pro (~1.5 hours, ~$1, gets cleaner data + JSONs in
   one shot — recommended); (b) write a Postgres → JSON regeneration
   tool.

### 5.3 D5 canonical-id rewrite

D5 (Ley 1943/2018 — IE cascade trigger) had 36/39 norms reject at
insert because Gemini emitted `sentencia.C-481.2019` instead of
the canonical `sentencia.cc.c-481.2019`. Three norms inserted; the
other 36 are sitting as failed inserts.

Two paths to recover:
- (a) re-extract D5 with the latest prompt (which has the canonical-id
  enforcement rule); ~$0.05 on DeepSeek; 2 minutes wall.
- (b) write a one-shot fixer that reads D5's debug JSONs, normalizes
  the source_norm_id field, re-ingests.

Pick (a) for cleanliness. Add to the campaign's "rerun-weak" list with
threshold 50 and it self-heals.

### 5.4 Pool maintainer counting bug

The maintainer in yesterday's session counted raw `extract_vigencia.py`
processes (which is 2 per active batch — the `uv run` wrapper + the
python child) and divided implicitly. Result: at slot-opening it
overshot, launching 11 batches in a 60-second burst. Most landed on
empty slices so it was harmless, but this should be fixed before the
next pool-maintainer arming.

Fix: replace the count with `ps -ef | grep extract_vigencia.py |
grep -v grep | grep -oE "batch-id [A-Za-z0-9]+" | sort -u | wc -l`.

### 5.5 Cosmetic heartbeat timestamp

Heartbeat sidecar's Bogotá date format string had `%C3%A1` URL-encoded
that bash `date` interprets as `%C` (century, partial) → produces
"Bogot203Monday1" instead of "Bogotá". Patched mid-session in
`launch_batch.sh` — verify on next run.

### 5.6 SUIN-Juriscol functional integration

Currently a placeholder. The scraper claims `articulo_et` and `ley_*`
support but `_resolve_url` returns a `?canonical=...` stub URL that
isn't a real SUIN view URL. Building this would unlock SUIN as a real
second source, removing our reliance on the "single .gov.co source is
acceptable" rule for ley.* late-numbered articles. Tracked under
`fixplan_v3.md §0.11.3` backlog. Not blocking — just nice-to-have.

## 6. Quick-start for resuming the canonicalizer

Resume in 4 commands:

```bash
# 1. Source env (DEEPSEEK_API_KEY + GEMINI_API_KEY are in .env.local)
set -a; . .env.local; set +a

# 2. Confirm provider resolves to DeepSeek-v4-pro
PYTHONPATH=src:. uv run python -c "
from lia_graph.llm_runtime import resolve_llm_adapter
adapter, info = resolve_llm_adapter()
print(f'{info[\"selected_provider\"]} ({info[\"adapter_class\"]}, {info[\"model\"]})')
"
# Expected: deepseek-v4-pro (DeepSeekChatAdapter, deepseek-v4-pro)

# 3. Confirm local docker stack is up (Supabase :54322, Falkor :6389)
docker ps --format '{{.Names}}' | grep -E "(supabase_db_lia-graph|lia-graph-falkor-dev)"

# 4. Re-launch the campaign for whatever phases need rerunning (corpus-gated)
bash scripts/canonicalizer/run_full_campaign.sh --phases <X> <Y> <Z>
```

For the planned next runs once corpus is populated:

```bash
# Full E-K sweep (will take ~10 hours, ~$6 DeepSeek):
bash scripts/canonicalizer/run_full_campaign.sh --phases E F G H I J K
```

## 6.A Mandatory runner protocol — DO NOT SHORTCUT

The autonomous campaign succeeded because every batch went through the same
hardened launcher with the same heartbeat + kill-switches. **Any future
canonicalizer run must follow this protocol.** Skipping it is how you lose
hours of API spend and end up with corrupted state.

### Rules (non-negotiable)

1. **Always launch via `scripts/canonicalizer/launch_batch.sh`** — never call
   `extract_vigencia.py` directly. The launcher owns: pre-baseline snapshot,
   detached extract via `nohup … >log 2>&1 & disown` (NO `| tee` — tee dies
   on SIGHUP and crashed a run), heartbeat sidecar arming, ingest, Falkor
   sync, post-verify, scoring, ledger row append. Deviating skips state
   recovery.
2. **Heartbeat sidecar is mandatory and auto-arms.** `launch_batch.sh`
   spawns `while kill -0 $EXTRACT_PID; do heartbeat.py …; sleep 180; done`
   in the same shell. Output lands in `logs/heartbeat_<batch>_<ts>.md`
   with a STATE=… first line, ASCII progress bar, state breakdown, and
   kill-switch triggers. **Every 3 minutes, no exceptions** — per CLAUDE.md
   long-running-job protocol.
3. **For multi-batch / multi-hour runs, ALSO arm a `CronCreate` heartbeat**
   that invokes `scripts/monitoring/ingest_heartbeat.py` (or the
   canonicalizer-specific equivalent) on a 3-minute cron. Sidecar dies if
   the launcher dies; CronCreate survives. Belt + suspenders.
4. **Atomic JSON writes only.** `vigencia_extractor.py::write_result` does
   temp + rename + fsync. Never write veredicto JSONs through any other
   code path — power loss / OOM mid-write would corrupt the canonical
   artifact.
5. **Pre-flight the throttle.** Before any extract launches, confirm
   `var/gemini_throttle_state.json` is current and `LIA_GEMINI_GLOBAL_RPM`
   resolves to the expected cap (default 80). The bucket is shared across
   ALL processes — DeepSeek runs share Gemini's bucket via the same lock.
6. **Pre-flight provider resolution.** Run the 4-line `resolve_llm_adapter`
   probe from §6 step 2 BEFORE launching. If it doesn't print
   `deepseek-v4-pro (DeepSeekChatAdapter, deepseek-v4-pro)`, stop and
   debug — don't let a misconfigured adapter silently fall back to an
   exhausted Gemini quota.
7. **Adapter retries are project-wide.** `gemini_runtime.py::_request`
   retries 5xx/429 at 0/4/12/30 s exponential back-off, 4 attempts max.
   Don't add per-call retry loops — you'll stack retries and burn quota.
8. **Run-once guard.** Each batch refuses to re-run if its
   `evals/canonicalizer_run_v1/<batch>/run_state.json` shows DONE.
   Override only with `--allow-rerun` from an operator-typed CLI.
   Re-runs are NEVER autonomous.
9. **Cloud writes are pre-authorized.** Per the operator's standing
   directive, Lia Graph cloud Supabase + Falkor writes don't need
   per-action approval. Announce before executing; never silently mutate
   LIA_contadores resources (different repo).
10. **Kill-switches** the operator (or the parent agent) MUST enforce:
    - Process gone + no `cli.done` event in last 5 min → silent death →
      STOP loop, surface log, do NOT auto-retry.
    - `run.failed` event OR `ERRORS > 0` in heartbeat → STOP, surface,
      diagnose root cause before any retry.
    - `cli.done` event → STOP, mark batch DONE, move on.
    - 2 consecutive phases scoring <50% → halt the campaign
      (`run_full_campaign.sh::QUOTA_HALT_THRESHOLD`).

### Pool maintainer rules

If you arm the sustained-pool maintainer for parallelism (yesterday: 6–7
concurrent workers), the count must use **unique batch ids**, not raw
process count:

```bash
ACTIVE=$(ps -ef | grep extract_vigencia.py | grep -v grep \
         | grep -oE 'batch-id [A-Za-z0-9]+' | sort -u | wc -l)
```

Yesterday's bug: counted `uv run` wrappers + python children separately
(2 per batch), then divided implicitly → at slot-opening the maintainer
overshot, launched 11 batches in a 60-second burst. Most landed on
empty slices so it was harmless THIS time. Fix before the next pool
arming. Tracked under §5.4.

### Pre-launch checklist (paste this before every campaign)

```
[ ] .env.local sourced; DEEPSEEK_API_KEY + GEMINI_API_KEY both set
[ ] resolve_llm_adapter probe prints deepseek-v4-pro
[ ] supabase_db_lia-graph + lia-graph-falkor-dev containers UP
[ ] var/scraper_cache.db exists and is WAL-mode
[ ] var/senado_et_pr_index.json exists (887 entries) — rebuild if stale
[ ] var/gemini_throttle_state.json present (created on first call if absent)
[ ] LIA_LIVE_SCRAPER_TESTS=1 exported (launch_batch.sh exports it; verify if calling extract directly)
[ ] LIA_BATCHED_RUNNER=1 NOT needed for canonicalizer — that's pytest-only
[ ] CronCreate heartbeat armed (separate from sidecar, for multi-hour runs)
[ ] Operator notified before any cloud (Supabase / Falkor) write
```

### What "live verbose heartbeat" looks like

```
STATE=classifying
============================================================
Batch B3 (renta cap 4) — 2026-04-28 06:42 AM Bogota
Progress: 27/40 (67%)  [█████████████░░░░░░░░░░░░░░░]
States so far: V=18 VM=6 DE=2 SP=1
Last event: 2026-04-28T11:42:11Z norm.veredicto.written ley.1819.2016.art.123
Freshness: FRESH (last event 38s ago)
Throttle: bucket 72/80 RPM, 0 retries, 0 final-429
Kill-switches: cli.done? NO  ERRORS? 0  run.failed? NO
============================================================
```

A heartbeat that prints any other shape is broken — fix it before
launching the next batch.

1. **`CLAUDE.md`** — repo-level operating guide.
2. **This doc** — for the strategic picture. **Read §6.A "Mandatory runner protocol" before launching anything.**
3. **`docs/re-engineer/canonicalizer_runv1.md`** — per-batch protocol.
4. **`docs/re-engineer/state_canonicalizer_runv1.md`** — current per-batch state.
5. **`docs/re-engineer/corpus_population_plan.md`** — if corpus work is in scope.
6. **`docs/learnings/canonicalizer/A1_first_real_run_2026-04-27.md`** — refusal taxonomy and prompt-tightening history.
7. **`docs/learnings/sites/README.md`** + the per-site files — when a scraper looks broken.
8. **`evals/canonicalizer_run_v1/campaign_log.md` + `ledger.jsonl`** — what's actually been run.

What you can SKIP unless directly relevant:
- `fixplan_v3.md` (closed sub-fixes — load-bearing but not active steering)
- `fixplan_v2.md` / `fixplan_v1.md` (archaeological)
- `docs/deprecated/old-RAG/` (old corpus design — ignore)

## 8. File index — where to look

| Concern | File |
|---|---|
| What does the canonicalizer DO per batch? | `canonicalizer_runv1.md` §0 |
| What's a batch's slice / test questions? | `config/canonicalizer_run_v1/batches.yaml` |
| Where are the per-norm veredictos? | `evals/vigencia_extraction_v1/<batch>/*.json` |
| Where's the live state? | `evals/canonicalizer_run_v1/<batch>/run_state.json` (per batch) + `state_canonicalizer_runv1.md` (overall) |
| What did each batch end up scoring? | `evals/canonicalizer_run_v1/ledger.jsonl` |
| What refused and why? | `evals/canonicalizer_run_v1/phase_*_failure_catalog.md` + `evals/vigencia_extraction_v1/_debug/*.json` |
| Heartbeat output? | `logs/heartbeat_<batch>_<ts>.md` |
| API throttle state? | `var/gemini_throttle_state.json` |
| Senado ET pr-segment map? | `var/senado_et_pr_index.json` |
| Scraper cache? | `var/scraper_cache.db` (SQLite, WAL mode) |
| LLM provider config? | `config/llm_runtime.json` |
| Vigencia schema? | `src/lia_graph/vigencia.py` |
| Skill prompt? | `src/lia_graph/vigencia_extractor.py::_build_prompt` |
| Adapter retry policy? | `src/lia_graph/gemini_runtime.py` |
| Token-bucket throttle? | `src/lia_graph/gemini_throttle.py` |
| Provider resolution? | `src/lia_graph/llm_runtime.py::resolve_llm_adapter` |

## 9. Numbers that matter

- **754 unique norms** verified (Phases A+B+C+D)
- **642 structural edges** in Falkor (~5× the pre-campaign baseline)
- **1,051 vigencia history rows** in Postgres (multiple run-ids per norm — append-only)
- **0 retries, 0 final-429s** across the 5-hour autonomous campaign
- **6–7 concurrent workers** sustained without API pushback
- **80 RPM** project-wide throttle (we used ~6 RPM peak — 7.5% of cap)
- **~$3 in API spend** total (Gemini + DeepSeek combined for the full session)
- **~1,690 norms** still missing — corpus-gated
- **~$6 + ~10 hours** estimated to verify the remaining ~1,690 once corpus lands

## 10. Decision pending for the operator

Two paths, named in §0 of `corpus_population_plan.md`:

(a) **Populate the corpus.** Hand the corpus expert the population plan,
    let them run the 12 briefs in §9, then re-run the canonicalizer
    campaign for E–K. Net: ~3,400 verified norms, 7–10 days of corpus
    work, ~10 hours of canonicalizer wall.

(b) **Mark canonicalizer "done for what we have."** Skip corpus work,
    promote the 754 norms to staging now, re-engage canonicalizer when
    corpus catches up. Net: 754 norms in production, accountants can
    use vigencia gating on procedimiento + renta + IVA + reformas-Ley
    surface today.

Both are valid. Path (a) maximizes coverage; path (b) maximizes
time-to-user. Operator decides.

---

*Drafted 2026-04-28 by claude-opus-4-7 after the autonomous DeepSeek-v4-pro
campaign halted on Phase E + F empty-slice cluster. v4 supersedes v3 as
the active forward plan; v3 stays as historical context.*
