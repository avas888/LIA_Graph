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

## 0. If you are a fresh agent — read this first

The current state is: **outside experts are actively scouring the web for legal documents**, working from plain-language briefs in `docs/re-engineer/corpus_population_for_experts/`. They will hand you (or your operator) one or more **expert deliverable packets** — folders of text files OR single markdown documents per brief — containing legal articles, court rulings, or DIAN opinions. **Your job is to take a delivered packet and turn it into rows in `artifacts/parsed_articles.jsonl`**, validated against the canonicalizer's grammar, then commit + update the state file. After enough briefs land you (or the operator) re-run the canonicalizer harness for Phases E–K.

You are NOT scraping the web yourself. The experts do that. You ingest what they hand you.

**Read in this order before doing anything else:**

1. `CLAUDE.md` (repo-level operating guide) — already loaded.
2. **This file** — for the strategic picture and the "what to do next" details below.
3. `docs/re-engineer/corpus_population_plan.md` — master plan, especially §5 (canonical id grammar), §6 (deliverables schema), §8 (priority order).
4. `docs/re-engineer/corpus_population_brief_edits.md` — the canonical-id rules every row must obey. Pay attention to §3 caveats about which examples are verified vs illustrative.
5. `docs/re-engineer/corpus_population_sprint_brief.md` — campaign-manager view: per-brief target counts, validation gates, reporting protocol.
6. `docs/re-engineer/corpus_population_reconciliation.md` — historical context on why the briefs and canon agree now (Path A taken 2026-04-28).
7. `docs/re-engineer/state_corpus_population.md` — live progress tracker; you will be updating §4 and §10 as you ingest.
8. The specific **technical brief** in `docs/re-engineer/corpus_population/<NN>_<source>.md` for whichever brief the expert delivered. (The matching plain-language brief in `corpus_population_for_experts/<NN>_<source>.md` is what the expert read; you reference the technical version because it has schema details.)

**Hot facts you should know before touching anything:**

* **canon.py is current.** As of 2026-04-28, four families are supported: cst (`cst.art.<N>`), cco (`cco.art.<N>`), dcin (`dcin.<NUM>.cap.<C>.num.<N>`), oficio (`oficio.<emisor>.<NUM>.<YEAR>`). Plus the pre-existing families (et, ley, decreto, res, concepto, sent.cc, sent.ce, auto.ce). 118/118 canon tests pass. **DO NOT extend canon further** unless an explicit gap is identified and the operator approves.
* **Briefs ↔ canon ↔ batches.yaml are in agreement** as of 2026-04-28 afternoon. Don't re-litigate the reconciliation.
* **0 of 12 briefs ingested today.** State file `state_corpus_population.md` §4 will be all 🟡 when you arrive. Your first ingest will be the first row to flip.
* **`build_extraction_input_set.py` reads body text, not a `norm_id` field.** Each row's body must mention the canonical citation in natural-language form (e.g. "Artículo 22 CST" or "Art. 555-2 ET") so `canon.find_mentions()` picks it up. The `norm_id` field on each row is metadata; it does not drive the input set. This is non-obvious and easy to get wrong — see `corpus_population_reconciliation.md §2` for the full mechanism.
* **Hard URL requirement.** Every row must carry a `source_url` field pointing to the **exact source page** the article came from (not a homepage or master index). Memory `feedback_expert_deliverables_require_url.md` codifies this. Reject expert deliveries that violate it; ask the expert to refetch with proper provenance.
* **No hallucinated examples.** Do not invent article numbers, oficio numbers, or sentencia numbers. Use what the expert delivered or what's verified in `config/canonicalizer_run_v1/batches.yaml` `explicit_list` arrays. Memory `feedback_no_hallucinated_examples.md`.
* **5 scraper gaps documented.** `corpus_population_plan.md §7` lists them: auto.ce URL resolver, oficio.dian URL resolver, decreto.legislativo URL filename rewrite, CST + CCo Senado-style scraper, BanRep scraper. Each affected brief documents a fixture-only path. **You don't need to fix any scraper to ingest expert-delivered packets** — fixture-only is the supported path.

**Your first action when an expert hands you a packet:**

1. Identify the brief number (e.g., "this is brief 11 — pensional/salud/parafiscales").
2. Read `corpus_population_for_experts/<NN>_<source>.md` to see what the expert was told.
3. Read `corpus_population/<NN>_<source>.md` to see the technical schema.
4. Validate the packet's structure: does each item have full text + identifier + URL + date? Does the URL point to an exact source page (not a homepage)?
5. If validation fails, push back on the expert with specific feedback. Do not guess what they meant.
6. If validation passes, follow the §6.B "Quick-start for ingesting expert deliverables" recipe below.

---

## 1. One-paragraph reality check

The canonicalizer has been **built end-to-end** and **runs autonomously
in production conditions** against local Supabase + Falkor. It has
verified vigencia for **754 unique norms** (Phases A/B/C/D) and laid
**642 structural edges** in Falkor. The pipeline is provider-agnostic
(DeepSeek-v4-pro primary, Gemini fallback). Throttle, retry, parallel
agents, sustained pool maintainer, heartbeat sidecars, and durable
atomic JSON writes all work. The next unlock is **corpus ingestion via
expert deliverables**: roughly 2,650 of the canonicalizer's intended
~3,400 norms are missing from `artifacts/parsed_articles.jsonl` at the
canonical id-shapes the batches expect. The 12 plain-language briefs
in `corpus_population_for_experts/` have been handed to outside experts;
the canonicalizer can't extract what isn't in the corpus, but the
corpus surface is now reconciled (briefs ↔ canon ↔ YAML agree) and
ready to receive expert deliverables.

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

#### 5.1.1 What landed 2026-04-28 (reconciliation closed; expert/engineer streams separated)

**Engineer-side, in repo:**

* `docs/re-engineer/corpus_population/` — 12 technical briefs (one per source family: CST, DUR 1625 renta/IVA/procedimiento, DUR 1072, COVID legislativos, resoluciones DIAN, conceptos unificados, conceptos individuales + oficios, jurisprudencia CC+CE+autos, pensional/salud/parafiscales, cambiario/societario). Each carries the canonical-id rules, scraper status, validation snippet, etc. **Reference for the dev team only.**
* `docs/re-engineer/corpus_population_brief_edits.md` — find/replace spec the brief authors used to align id-shapes to canon + YAML.
* `docs/re-engineer/corpus_population_reconciliation.md` — Path A/B/C analysis closed by going Path A.
* `docs/re-engineer/corpus_population_sprint_brief.md` — campaign-manager view (sprint plan, per-brief target counts, validation gates, reporting protocol).
* `docs/re-engineer/state_corpus_population.md` — live progress tracker with §3 global state, §4 per-brief table, §10 append-only run log. Briefs all 🟡 (not started); per-brief table not advanced because no rows ingested yet.

**Outside-expert-side, in repo (NEW 2026-04-28):**

* `docs/re-engineer/corpus_population_for_experts/` — 12 plain-language briefs + a README. Strictly non-technical: tells experts WHAT documents to find, WHERE to find them online, HOW MANY (target count ±20%), WHAT TO DELIVER (text + identifier + URL + date), HOW TO PACKAGE (folder of text files OR one markdown). No canonical ids, no JSON, no scrapers, no regex, no Python. Per the operator's "don't cross streams" directive — outside experts (legal researchers, contadores, SMEs) get a strictly non-technical handoff; engineer-facing details stay in `corpus_population/`.
* Commitment captured in memory `feedback_expert_questions_no_streams_crossed.md` so future briefs honor the separation.

**Canon extension (engineer-side, shipped):**

* `src/lia_graph/canon.py` extended with `_rule_cst`, `_rule_cco`, `_rule_dcin`, `_rule_oficio` (year-mandatory; runs before `_rule_concepto` to preserve no-year backward compat). 4 new `_NORM_ID_PATTERNS` + 4 new `_MENTION_FINDERS`. `display_label` and `norm_type` updated.
* `tests/test_canon.py` gained 44 new test cases. **Full canon suite: 118/118 passing — zero regression on the 74 pre-existing tests.**

**Hallucination audit (engineer-side, closed):**

* Audit found `decreto.1625.2016.art.1.5.2.125-A` (canon rejects letter-suffix on DUR articles) plus several illustrative concrete article numbers / oficio numbers / sentencia numbers that the original brief-edit spec presented as if real.
* Replaced illustrative examples with verified-real ids from `batches.yaml` explicit_lists where possible, or with explicit `<dotted-decimal>` placeholders + "do not invent — read off the source" instructions.
* Memory `feedback_no_hallucinated_examples.md` written so future expert-facing artifacts cite real-or-flagged.

#### 5.1.2 Reconciliation outcome — Path A taken

The 2026-04-28 audit found 7 of 12 briefs proposed canonical id-shapes that either canon's `_NORM_ID_FULL_RE` rejected (cst, cco, dcin, oficio.dian.<NUM>.<YEAR>) or that disagreed with `batches.yaml` (briefs used `libro.X.Y` while YAML expected `art.X.Y`; briefs used `sentencia.cc.c-N.YEAR` while YAML expected `sent.cc.C-N.YEAR`). Second-order finding: `build_extraction_input_set.py` discovers `norm_id`s by running `canon.find_mentions()` over body text, NOT by reading a `norm_id` field per row.

Path A executed: brief authors edited briefs 02–06 + 10 to canon-aligned shapes (no code change); engineer extended canon for cst/cco/dcin/oficio (code change shipped above). All 36 verified-real example ids round-trip cleanly through `canonicalize()`. Briefs ↔ canon ↔ `batches.yaml` are now in agreement.

#### 5.1.3 What's NOT yet done

* **0 of 12 briefs ingested.** `state_corpus_population.md` §4 per-brief table all 🟡 (not started). The corpus-research experts haven't started scraping gov.co yet.
* **5 scraper gaps documented but mostly unaddressed** (master plan §7): auto.ce URL resolver, oficio.dian URL resolver, decreto.legislativo URL filename rewrite, CST + CCo Senado-style scraper, BanRep scraper. Each affected brief documents a fixture-only fallback path; the gaps only block live-fetch ingestion, not the corpus-population work itself.
* **Canonicalizer campaign for E–K not run yet.** Gated on the corpus rows landing.

#### 5.1.4 Sequencing — what unblocks what

1. Outside experts pick briefs from `corpus_population_for_experts/` per the priority order in `corpus_population_sprint_brief.md` §2 (Sprint 1: briefs 11 → 01 → 08 → 07; Sprint 2: 02–05; Sprint 3: 12, 09, 10, 06).
2. Each delivered brief is reviewed by an engineer; raw text is converted to `parsed_articles.jsonl` rows with canonical ids, schema-validated, and committed.
3. After each brief lands, `build_extraction_input_set.py` regenerates `evals/vigencia_extraction_v1/input_set.jsonl`. Slice-size smoke check confirms the new family resolves to ≥80% of target.
4. After Sprint 1 lands (~440 rows), engineer can start running canonicalizer batches incrementally rather than waiting for full corpus.
5. After Sprint 3 lands (~2,650 rows total added), full campaign per `bash scripts/canonicalizer/run_full_campaign.sh --phases E F G H I J K`.

**Wall estimate for the canonicalizer side once corpus is populated:** ~10 hours of DeepSeek-v4-pro time, 6 concurrent workers, autonomous via `run_full_campaign.sh`.

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

> **Pick the right starting point:**
> * **You are a fresh agent who just received an expert deliverable packet** → skip directly to **§6.B** (ingestion recipe). Come back to §6 only if you also need to run the canonicalizer harness afterwards.
> * **You are continuing an in-flight canonicalizer campaign** (mid-batch, after a process death, etc.) → use the 4 commands below to resume context, then follow **§6.A** (mandatory runner protocol).
> * **You are starting a NEW canonicalizer batch run from scratch** → §6 below to pre-flight + §6.A's pre-launch checklist.

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
# Full E-K sweep (will take ~10 hours):
bash scripts/canonicalizer/run_full_campaign.sh --phases E F G H I J K
```

## 6.B Quick-start for ingesting an expert deliverable packet

Use this when the operator hands you a packet from an outside expert (per the §0 fresh-agent on-ramp). Each packet corresponds to **one brief** (e.g. brief 11 = pensional/salud/parafiscales). Process one packet at a time. Do not interleave packets from multiple briefs in the same commit.

### Step 1 — Receive and validate the packet structure

The expert delivers either:

* **Option A** — a folder of `.txt` files, one per article/document.
* **Option B** — a single `.md` file with a header per article.

Either way, every article must carry these four pieces of information (per `corpus_population_for_experts/README.md`):

1. Full text of the article.
2. Article number / document identifier (e.g. "Artículo 22", "Sentencia C-481/2019", "Oficio DIAN 018424 de 2024").
3. **URL pointing to the exact source page** — hard requirement, never a homepage or master index. Reject the packet and ask the expert to refetch if URLs are missing or wrong.
4. Issue date if visible.

If the packet is missing any of the four for any item, push back to the expert with specific feedback. Do not invent missing data.

### Step 2 — Read the matching technical brief

Open `docs/re-engineer/corpus_population/<NN>_<source>.md` for the brief number the packet covers. That doc has:

* The exact canonical id-shape for this family (e.g. `cst.art.<N>`, `decreto.1625.2016.art.<dotted-decimal>`, `sent.cc.<TYPE>-<NUM>.<YEAR>`).
* The expected `parsed_articles.jsonl` row schema (full schema at master plan `corpus_population_plan.md §6.1`).
* The smoke-verification snippet specific to this brief's batches.

### Step 3 — Convert each delivered article to a `parsed_articles.jsonl` row

For each article in the packet, build a row matching the master §6.1 schema:

```json
{
  "norm_id": "<canonical-id-from-canonicalize>",
  "norm_type": "<see canon.norm_type for the family>",
  "article_key": "<short label, e.g. 'Art. 22 CST'>",
  "body": "<full text from expert, including title heading, and ensuring the body text contains the natural-language citation form (e.g. 'Artículo 22 CST') so canon.find_mentions picks it up>",
  "source_url": "<the EXACT URL from the expert delivery>",
  "fecha_emision": "<YYYY-MM-DD or null>",
  "emisor": "<Congreso, DIAN, CC, CE, BanRep, MinTrabajo, etc.>",
  "tema": "<thematic tag from the brief>"
}
```

The `norm_id` field comes from running `canonicalize()` on the article's natural-language identifier. For example, the expert delivers "Artículo 22 of the Código Sustantivo del Trabajo" → you call `canonicalize("Art. 22 CST")` → you get `cst.art.22` → that's the row's `norm_id`.

**Critical:** ensure the `body` field contains the natural-language citation form somewhere in its text. The input-set builder (`build_extraction_input_set.py`) reads the body and extracts mentions — if the body says "El presente artículo establece..." without ever naming the article, the row won't be picked up. Most legal source material does include the heading ("ARTÍCULO 22. DEFINICIÓN..."), so this is usually automatic, but verify on a sample.

### Step 4 — Round-trip-validate every row before appending

Before appending to `artifacts/parsed_articles.jsonl`, run this gate. Replace `<your-staging-file>` with whatever you wrote your candidate rows to (e.g. `/tmp/brief_11_staging.jsonl`):

```bash
PYTHONPATH=src:. uv run python -c "
import json, sys
from lia_graph.canon import canonicalize
bad = []
total = 0
with open('<your-staging-file>') as f:
    for i, line in enumerate(f, 1):
        if not line.strip(): continue
        row = json.loads(line)
        nid = row.get('norm_id')
        if not nid:
            bad.append((i, 'missing_norm_id', None)); continue
        if not row.get('source_url'):
            bad.append((i, 'missing_source_url', nid)); continue
        if canonicalize(nid) != nid:
            bad.append((i, 'non_canonical', nid))
        total += 1
if bad:
    print(f'FAIL — {len(bad)} of {total} rows failed:')
    for line, kind, nid in bad[:30]:
        print(f'  line {line}: {kind} {nid!r}')
    sys.exit(1)
print(f'OK — all {total} rows validated.')
"
```

If FAIL, fix the offending rows (typo in the canonical id, missing URL, non-existent article number you accidentally invented) and re-run. Do not proceed past FAIL.

### Step 5 — Append to the corpus and rebuild the input set

```bash
# Append staged rows to the corpus (use cat, not move — preserve existing rows)
cat <your-staging-file> >> artifacts/parsed_articles.jsonl

# Regenerate the deduplicated input set
PYTHONPATH=src:. uv run python scripts/canonicalizer/build_extraction_input_set.py
# Confirm output exists and mtime advanced
ls -la evals/vigencia_extraction_v1/input_set.jsonl
```

### Step 6 — Smoke-check the affected batches

For each batch the brief covers (look at the brief's "Phase batches affected" header), confirm the batch slice resolves to ≥80% of the target count from `corpus_population_plan.md` Appendix A. The brief's "Smoke verification" section has the exact snippet; copy-paste and run.

For example, brief 11 covers J5/J6/J7. Targets: J5≥24, J6≥20, J7≥16. If any batch comes in below threshold, investigate before committing — usually the body text doesn't mention the canonical citation in a form `find_mentions` recognizes.

### Step 7 — Commit and update state

Per master plan §10.5: one commit per brief.

```bash
git add artifacts/parsed_articles.jsonl evals/vigencia_extraction_v1/input_set.jsonl docs/re-engineer/state_corpus_population.md
git commit -m "corpus(<source>): ingest <N> rows for brief <NN>"
```

Update `state_corpus_population.md`:

* §4 per-brief table: status 🟡 → ✅, set Owner to whoever did the work, update Last update date.
* §10 run log: append `YYYY-MM-DD HH:MM Bogotá — brief NN — ingested <N> rows; smoke check OK; <count> batches at ≥80% target.`
* §3 global state: increment "Briefs ingested (✅)" counter; update "Verified vigencia rows" only after canonicalizer harness has actually run on the new norms (not at ingest time — that's later).

### Step 8 — When the operator says "run the canonicalizer for these batches"

Only after the operator's go-ahead, run the canonicalizer harness for whichever phase batches the brief unlocked. **Use the mandatory runner protocol in §6.A** — never call `extract_vigencia.py` directly; always go through `scripts/canonicalizer/launch_batch.sh`. Heartbeat is mandatory. CronCreate heartbeat for multi-batch runs is also mandatory.

```bash
# Example: ingest a single batch via the hardened launcher (replace J5 with the batch id)
bash scripts/canonicalizer/launch_batch.sh --batch-id J5
```

For multi-batch runs, prefer `run_phase.sh` over manual loops — it handles dep order and stops on per-batch FAIL.

### What NOT to do (per operator memories)

* Never re-extract Phases A–D — they are already verified in production. Operator memory: extract once, promote through three stages.
* Never run the full pytest suite in one process — use `make test-batched`. The conftest guard aborts without `LIA_BATCHED_RUNNER=1`.
* Never bypass the project-wide token bucket throttle. Default 80 RPM is shared across all parallel processes.
* Never silently fall back from cloud Falkor to artifacts in staging — the adapter must propagate cloud outages.
* Never invent article numbers or URLs to fill a target count — better to under-deliver than to corrupt the audit trail. Memory `feedback_no_hallucinated_examples.md`.
* Never quote dollar amounts in status reports — operator handles budget. Time estimates OK; $/cost not. Memory `feedback_no_money_quoting.md`.

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

**Canonicalizer (Phases A–D, in production):**
- **754 unique norms** verified
- **642 structural edges** in Falkor (~5× the pre-campaign baseline)
- **1,051 vigencia history rows** in Postgres (append-only)
- **0 retries, 0 final-429s** across the 5-hour autonomous campaign
- **6–7 concurrent workers** sustained without API pushback
- **80 RPM** project-wide throttle (used ~6 RPM peak — 7.5% of cap)

**Phase E–K corpus campaign (queued):**
- **~2,650 rows** still to add to `parsed_articles.jsonl` per the 12 briefs
- **0 of 12 briefs** ingested — outside experts haven't started yet
- **~10 hours** canonicalizer wall to verify the new norms after corpus lands
- **Target final state:** ~3,400 verified norms (754 + ~2,650)

**Canon extension (shipped 2026-04-28):**
- **4 new families** supported: cst, cco, dcin, oficio.<emisor>.<NUM>.<YEAR>
- **118/118 canon tests passing** (74 pre-existing + 44 new) — zero regression
- **36 verified-real example ids** round-trip cleanly through `canonicalize()`

## 10. Decision history + current path

The 2026-04-28 morning v4 draft posed two paths:

(a) **Populate the corpus.** ~3,400 verified norms, 7–10 days of corpus work + ~10 hours of canonicalizer wall.

(b) **Mark canonicalizer "done for what we have."** Skip corpus work, promote 754 norms to staging now.

**Path chosen 2026-04-28 afternoon: Path (a), executed in parallel with §5.2 staging promotion.**

Path (a) progress so far:

* 12 engineer-side technical briefs: ✅ landed in `corpus_population/`.
* 12 outside-expert plain-language briefs: ✅ landed in `corpus_population_for_experts/`.
* Canon ↔ briefs ↔ YAML reconciliation: ✅ closed; canon extended for cst/cco/dcin/oficio; tests green.
* Hallucinated example audit: ✅ closed; verified-real or `<placeholder>` everywhere expert-facing.
* Expert ingestion: ✅ **closed 2026-04-28 PM.** All 12 briefs ingested; 4356 unique rows landed in `parsed_articles.jsonl` (7922 → 12 305). 23 of 41 batches PASS smoke check, 14 PARTIAL, 4 MISS. Per-brief commits 33d18d5 → 9ce3aee.
* Canonicalizer next-gate (J5 pilot trial): 🟡 ran 2026-04-28 PM; FAIL diagnostic — see §11 below.
* Expert briefs 13/14/15 (gap-fill): ✅ authored; ready for outside-expert delivery. Cover F1/F3/F4 + I3/I4 + K1/K2 MISS gaps.

Path (b) — staging promotion of the 754 — proceeds in parallel per §5.2 (SME signoff + JSON regeneration prerequisites). The two paths are no longer mutually exclusive.

**Live tracker:** `docs/re-engineer/state_fixplanv4.md` is the canonical
status file from 2026-04-28 PM forward — read it BEFORE picking a task.
The corpus-side state tracker stays at `state_corpus_population.md`.

---

## 11. Where we are (2026-04-28 PM update)

### 11.1 What landed (final state of the day)

Twelve commits on `main` between 33d18d5 and 9ce3aee:

| Commit | Brief / fix | Rows added |
|---|---|---:|
| 33d18d5 | brief 11 + ingester scaffolding | 442 |
| d6ee2ae | corpus-population scaffolding (canon + briefs + plan) | n/a |
| b667001 | brief 01 (CST) | 200 |
| 2bcdb59 | brief 08 (G1 IVA Unificado) + canon finder fix | 408 |
| c06a2cc | brief 07 (F2 PASS) | 455 |
| 6492149 | brief 02 (DUR 1625 renta) | 834 |
| bb542c2 | brief 03 (DUR 1625 IVA + retf) | 499 |
| 0480be4 | brief 04 (DUR 1625 procedimiento) | 104 |
| c6fbdd7 | brief 05 (DUR 1072 laboral) | 297 |
| ed0268f | brief 12 (cambiario + societario) | 930 |
| 1870428 | brief 09 (oficios + conceptos individuales) | 92 |
| 79a825f | brief 10 (CC sentencias) | 16 |
| 9ce3aee | brief 06 (decretos COVID) — closes Sprint 3 | 104 |
| 1e4f16a | DIAN URL padding fix + briefs 13/14/15 + J5 pilot | n/a |
| 7883256 | fixplan_v4 §11 + state_fixplanv4.md tracker | n/a |
| c03655b | Senado ley URL padding fix | n/a |
| d14b6a6 | J5 verifies ley.100.1993 + SUIN stub disabled | n/a |
| 5dc2069 | next-gate session 1: J6 + G6 + 5 blockers surfaced | n/a |

`parsed_articles.jsonl`: 7 922 → 12 305 rows. Input set: 12 366 → 18 676
unique norm_ids. All 4356 rows round-trip-validate cleanly through
`canonicalize()`. Postgres `norm_vigencia_history`: 754 → **758** distinct
norms verified. Falkor edges: 639 → **640**.

### 11.2 J5 pilot trial — diagnostic FAIL

J5 (`explicit_list: ley.100.1993, ley.797.2003, ley.2381.2024`) launched
via the mandatory `launch_batch.sh` runner with auto-armed heartbeat
sidecar + `CronCreate` heartbeat per §6.A rules 2-3. Outcome: all 3
norms refused at the source-fetch step.

| Norm | Cause |
|---|---|
| `ley.100.1993` | DIAN 404 — scraper mapped to `ley_100_1993.htm` but DIAN serves `ley_0100_1993.htm` (4-digit-padded). **Fixed in commit 1e4f16a** — `dian_normograma._resolve_url` now zero-pads NUM to 4 digits for `ley.*` and `res.dian.*` ids. |
| `ley.797.2003` | NOT in DIAN normograma at all; needs Senado/SUIN fallback (Senado URL pattern is `ley_0797_2003.html` — also padded). |
| `ley.2381.2024` | Recent reform pensional, not yet ingested by DIAN. Available on Senado + Función Pública (`norma.php?i=246356`). |

Post-verify chat call also failed (`Connection refused` on port 8787 —
the local UI server wasn't running). The score step ran anyway; ledger
row + run_state captured.

The DIAN padding fix unblocks ley.100.1993 + every 1xxx-2xxx reform ley
(those already worked because their NUM is 4-digit by nature). Senado
fallback for 3-digit NUMs not in DIAN is the next code change required
to unblock J5/J6/J7 fully. **This is in scope for the next session.**

### 11.3 Session 1 outcomes — three batches run, five blockers surfaced

After commit 1e4f16a (DIAN padding + briefs 13/14/15 + J5 trial 1
diagnostic FAIL), the operator's "do next gate" directive triggered an
autonomous-progression cascade. Three batches ran via the mandatory
`launch_batch.sh` runner with auto-armed heartbeat sidecar + `Monitor`
+ `CronCreate` 3-min heartbeat per §6.A rules 2-3, all on
DeepSeek-v4-pro:

| Batch | Norms | Verdict | Successes | Notes |
|---|---:|---|---:|---|
| **J5 rerun** (commit d14b6a6) | 3 | FAIL (score) | **1** ✓ | `ley.100.1993` verified VM since 2003-01-29 by `ley.797.2003` (DIAN serves padded URL after fix). `ley.797.2003` + `ley.2381.2024` refused `missing_double_primary_source` — only Senado has them, harness needs ≥2. |
| **J6** (commit 5dc2069) | 3 | FAIL (score) | **1** ✓ | Same `ley.100.1993` re-extracted (deduped). `ley.1438.2011` + `ley.1751.2015` refused — both 4-digit-NUM but not in DIAN normograma; only Senado serves them. |
| **G6 acid test** (commit 5dc2069) | 5 | FAIL | 0 | All 5 ids 404: `auto.ce.28920.*` + `concepto.dian.100208192-202` + numerals + `sent.ce.28920.*`. Multiple new scraper gaps. |

**Net Postgres growth:** `norm_vigencia_history` 754 → 758 distinct
norms (+4; the new norms include `ley.100.1993` itself + the implicit
parent rows the writer creates for change-source references). Falkor
edges: 639 → 640 (+1 `MODIFIED_BY` from ley.100→ley.797).

**Three scraper fixes shipped during the cascade:**

* commit 1e4f16a — `dian_normograma._resolve_url` zero-pads NUM to 4
  digits for `ley.*` and `res.dian.*` (`ley_0100_1993.htm`,
  `resolucion_dian_0165_2023.htm`). Verified: `ley_0100_1993.htm` 200,
  `ley_2155_2021.htm` 200, plus 6 other reform leyes confirmed.
* commit c03655b — `secretaria_senado._resolve_url` does the same for
  ley URLs (`ley_0100_1993.html` 200 confirmed).
* commit d14b6a6 — `suin_juriscol._resolve_url` retired the
  `?canonical=<norm_id>` stub URL that was 400-then-SSL-fail looping
  for 10–15 s per norm with no chance of success. Returns `None` now
  so the harness's primary-source chain falls through to DIAN +
  Senado without the SUIN penalty. Per fixplan §5.6 SUIN remains a
  placeholder until a canonical→SUIN-id registry seeds.

**Five new blockers surfaced (live in `state_fixplanv4.md` §10):**

1. **Single-source rule blocks Senado-only leyes (biggest blocker).**
   The harness's `missing_double_primary_source` rule rejects any norm
   where <2 primary sources resolve. Many Colombian leyes are on
   Senado only, NOT in DIAN normograma:
   - 3-digit-NUM laws: 222/1995, 789/2002, 797/2003
   - 4-digit-NUM laws: 1258/2008, 1438/2011, 1751/2015, 2381/2024
   For any explicit_list batch covering these, only `ley.100.1993` (in
   both DIAN + Senado) currently passes. The fix is one of:
   (a) add Función Pública (`funcionpublica.gov.co/eva/gestornormativo/norma.php?i=<NNN>`) as a third primary source;
   (b) relax the harness rule to single-source acceptance for `.gov.co` Senado pages (per the prompt's existing rule for `.gov.co` primary sources);
   (c) add Senado/Función Pública as a paired-fallback chain when DIAN 404s.
   This is the **#1 priority** for the next session — without it, J5/J6/J7/K4 can never reach >1/3 success.
2. **CE auto/sent scrapers (Gap #1, fixplan §7).** `auto.ce.<radicado>.<date>` + `sent.ce.<radicado>.<date>` resolve to URLs the CE site doesn't serve (`auto_ce_28920_2024_12_16.html` 404 — CE uses a different path scheme, likely radicado-keyed search RPC). Fixture-only path documented as fallback.
3. **Concepto with hyphenated NUM filename mapping unknown.** DIAN scraper maps `concepto.dian.100208192-202` → `concepto_dian_100208192-202.htm` (404). DIAN's actual filename for hyphenated unified conceptos differs — needs lookup table or scraper case.
4. **CST + CCo not in Senado scraper's `_handled_types` (Gap #4, fixplan §7).** Senado scraper's set is `{"ley", "ley_articulo", "estatuto", "articulo_et"}`. J1-J4 (CST) + K3 (CCo) batches blocked at scraper level. Add `cst_articulo` + `cco_articulo` + URL patterns for each.
5. **Score step crashes on `--skip-post`.** Score reads `post_*.json` regardless; errors when `--skip-post` skipped step 5. J6 + G6 ledger rows didn't append because score step crashed before append. Fix: gate the score's chat-replay on `--skip-post`, or default it to "no post — emit ledger row with `post_test_results: null`."

**Data-side (outside experts) — unchanged from prior version:**

6. **Brief 13 delivery** (UVT + RST + RUT/exógena resoluciones) — unblocks F1/F3/F4 once canon ids land.
7. **Brief 14 delivery** (CE Sección Cuarta unificación + autos suspensión) — unblocks I3/I4.
8. **Brief 15 delivery** (BanRep Res Externa 1/2018 + DCIN-83) — unblocks K1/K2.

**Medium-priority (no longer blocking session 2 but still pending):**

9. **YAML keyword-pattern repair.** F1/F3/F4 + H1/H2/H4a/b/H5 + I2 use regex requiring keyword segments in canonical ids that canon doesn't allow. Replace with explicit-list of real numbers OR prefix patterns. The G1 placeholder fix (commit 2bcdb59) set the precedent.

### 11.4 Suggested session-2 sequence

1. **Engineer task block (~3 hours):**
   * Add Función Pública as third primary source OR relax single-source rule for `.gov.co` Senado (resolves blocker #1 — biggest unlock).
   * Fix score step to gate chat-replay on `--skip-post` (resolves blocker #5).
   * Add `cst_articulo` + `cco_articulo` to Senado scraper `_handled_types` + URL patterns (resolves blocker #4).
   * Optionally: implement Gap #1 CE scrapers OR mark fixture-only.
2. **Re-run cascade (~3-4 hours wall, autonomous):**
   * J5 + J6 + J7 with `--allow-rerun --skip-post` — expect ~9/9 success (3 leyes × 3 batches, all in DIAN+Senado pair after fix).
   * K4 (`ley.222.1995`, `ley.1258.2008`) — expect 2/2 PASS.
   * J1-J4 (CST ranges) — expect ~170 norms PASS after Senado CST scraper.
   * G1 (IVA Concepto Unificado) — 407 numerals; expect bulk PASS with parent-fetch + slice.
   * F2 (4 res.dian regex) — 111 ids; expect bulk PASS.
   * K3 (CCo articles) — 315 norms; expect PASS after Senado CCo scraper.
   * E1a/b/d/E2a/c/E3b/E6b/c/J8b — DUR cascade.
   * E5 (decretos COVID).
3. **D5 rerun (~5 minutes):**
   * `bash scripts/canonicalizer/launch_batch.sh --batch D5 --allow-rerun` (closes fixplan §5.3 D5 weak-result follow-up).
4. **Expert delivery + ingestion (in parallel, days):**
   * Hand briefs 13/14/15 to outside experts.
   * As packets arrive, ingest via `ingest_expert_packet.py --brief-num 13/14/15` per the §6.B recipe.
5. **YAML hygiene (~2 hours):**
   * Replace keyword regex with explicit_list of real numbers — F1/F3/F4 + H1/H2/H4a/b/H5 + I2 (blocker #9).
6. **Promotion gates (operator + SME):**
   * `local_docker_signoff.md` — SME runs the §1.G 36-question fixture against `npm run dev` and signs off.
   * Cloud staging promotion via `ingest_vigencia_veredictos.py --target production`.
   * Full E–K autonomous campaign (`run_full_campaign.sh`).

Estimate after session 2: ≥1500 verified norms in Postgres (J + G1 +
F2 + K3 + K4 alone → ~1100 net new). Expert deliveries 13/14/15
through sessions 3-4 should close the F1/F3/F4 + I3/I4 + K1/K2 gaps,
reaching the ~3000-norm DoD.

---

*Drafted 2026-04-28 morning by claude-opus-4-7 after the autonomous DeepSeek-v4-pro
campaign halted on Phase E + F empty-slice cluster. Updated 2026-04-28 afternoon
to reflect Path A reconciliation closure + canon extension + expert/engineer
brief separation. Updated again 2026-04-28 evening with §0 fresh-agent on-ramp
and §6.B ingestion recipe so a fresh agent spawned with an expert deliverable
packet can pick up the work without losing context. §11 added 2026-04-28
afternoon to capture the corpus-ingestion campaign close (12 briefs landed,
4356 rows, 23 batches PASS smoke). §11.3/§11.4 rewritten 2026-04-28 PM after
the canonicalizer next-gate session 1 (J5 rerun + J6 + G6) surfaced 5 new
blockers and verified `ley.100.1993` end-to-end through the full pipeline
(extract → ingest → Falkor sync). v4 supersedes v3 as the active forward
plan; v3 stays as historical context.*
