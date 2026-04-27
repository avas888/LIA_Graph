# evaluacion_ingestionfixtask_v1 — A/B evaluation of TEMA-first retrieval vs prior mode

**Purpose.** Run the 30 canonical evaluation questions against production twice — once with the pre-v5 retrieval path (prior mode, `LIA_TEMA_FIRST_RETRIEVAL=off`), once with the new v5 path (new mode, `LIA_TEMA_FIRST_RETRIEVAL=on`). Produce a single side-by-side markdown comparison document with both answers per question, clearly labeled, so an external panel of expert accountants can judge whether the new retrieval path improves, degrades, or leaves answer quality unchanged. The panel's verdict decides whether v5 flips from `shadow` to `on` in staging and production.

**Read order for a cold LLM**: §0 (Cold-Start Briefing) → §1 (Prior work) → §2 (Problem summary) → §3 (Scope + phasing) → §5 (Phases in order). §8 is the live state ledger — update it as each phase transitions.

**Status**: plan-only. **Do not start coding until the operator signs off.**

---

## §0 Cold-Start Briefing

*If you're an LLM or engineer picking this up with zero prior conversation context, this section is enough to orient you and start Phase 1 immediately. Everything below it assumes §0 has been read.*

### 0.1 What Lia_Graph is (30-second orientation)

Lia_Graph is a graph-native RAG product shell for Colombian accounting/legal content. It serves SMB accountants who act as de-facto labor/tax/corporate advisors. The served runtime is `src/lia_graph/pipeline_d/` (the "main chat" surface). Retrieval has two halves: chunk-level hybrid search in Supabase (`retriever_supabase.py` → `hybrid_search` RPC) + graph traversal in FalkorDB (`retriever_falkor.py`). Parallel surfaces — `Normativa`, `Interpretación` — have their own orchestration/synthesis/assembly modules and must **not** be folded into `main chat`.

### 0.2 What v5 did (the reason this eval exists)

v5 added TEMA-first retrieval behind the env flag `LIA_TEMA_FIRST_RETRIEVAL=off|shadow|on`. When the flag is `on`, the Falkor retriever starts at the routed `TopicNode` and fans out to candidate articles via `<-[:TEMA]-(ArticleNode)`. This is the first time the 1,943+ TEMA edges the v4 work populated actually steer retrieval. The flag defaults to `shadow` in dev/staging (runs the new Cypher + emits a `retrieval.tema_first.shadow` event but returns the legacy result) and `off` everywhere else. Flipping to `on` is a user-visible retrieval change — hence this A/B evaluation.

**Clarification on terminology.** "Shadow mode" returns the legacy answer, only logging the new path for diagnostics; it is NOT useful for a user-visible A/B. This document's two modes are therefore:
- **"prior" mode** → `LIA_TEMA_FIRST_RETRIEVAL=off` (pre-v5 behavior, legacy Falkor traversal)
- **"new" mode** → `LIA_TEMA_FIRST_RETRIEVAL=on` (v5 behavior, TEMA-first retrieval actually in the user-visible answer path)

### 0.3 Repo layout (essentials for this task)

```
src/lia_graph/
  pipeline_d/                     # served runtime — hot path
    orchestrator.py               # reads LIA_* env, dispatches
    retriever_falkor.py           # contains _tema_first_mode() + _retrieve_tema_bound_article_keys()
    contracts.py                  # PipelineCRequest, PipelineCResponse, EvidenceBundle shapes
  topic_router.py                 # resolve_chat_topic() — query → topic_key
  pipeline_c/contracts.py         # PipelineCRequest dataclass

scripts/
  eval_retrieval.py               # precedent — retrieval-metric harness (reference implementation)
  eval_citations.py               # precedent — citation-audit eval
  eval_topic_alignment.py         # precedent — topic-router eval
  evaluations/                    # NEW dir — this task creates it
    run_ab_comparison.py          # NEW — launcher (Phase 1)
    render_ab_markdown.py         # NEW — markdown renderer (Phase 2)
    README.md                     # NEW — operator cheat sheet for the panel handoff

evals/
  gold_retrieval_v1.jsonl         # machine-readable 30-question source (one JSON per line)
  100qs_accountant.jsonl          # separate corpus — do NOT use for this task

docs/quality_tests/
  EVALUACION-CORPUS-30-PREGUNTAS-RESPUESTAS.md   # canonical .md version; prose + structured appendix
  evaluacion_ingestionfixtask_v1.md              # THIS DOC

artifacts/eval/                    # NEW output directory — will contain per-run results
  ab_comparison_<ts>.jsonl         # atomic per-question append log (crash survivable)
  ab_comparison_<ts>.md            # rendered side-by-side panel doc (final deliverable)
  ab_comparison_<ts>_manifest.json # run metadata (flag states, Falkor baseline, wall times)

logs/
  evaluations-ab-<ts>.log          # detached-launcher stdout/stderr
```

### 0.4 Tooling

- **Python manager**: `uv` (pyproject.toml + uv.lock). Run anything with `uv run` so it uses the project venv. Dev deps via `uv run --group dev python …`.
- **Task runner**: `make` — notable targets: `test-batched` (the ONLY sanctioned way to run full pytest; conftest guard aborts >20 test files collected without `LIA_BATCHED_RUNNER=1`).
- **Single test**: `PYTHONPATH=src:. uv run pytest tests/<file>.py -v`.
- **Long-running Python**: follow CLAUDE.md §"Long-running Python processes" — detached `nohup + disown + direct redirect` (no tee pipes; SIGHUP has killed prior runs), 3-min heartbeat via `CronCreate`, anchor progress on `logs/events.jsonl`.

### 0.5 Auth + env

- **Env file**: `.env.staging` — confusingly named, holds **production** Supabase URL + service-role key. Source with `set -a; source .env.staging; set +a` before any production read.
- **Falkor**: `FALKORDB_URL` in `.env.staging`. Graph name `LIA_REGULATORY_GRAPH`.
- **Gemini**: `GOOGLE_API_KEY` in `.env.staging` — used by the LLM polish stage inside pipeline_d. The eval launches real queries, so each question triggers a Gemini call. Expect ~2,000–3,000 Gemini tokens/question → ~$0.20–0.40 total for 60 queries.
- **Production reads are not write-gated**, but the Claude Code harness may still prompt-confirm some read paths. The launcher does zero writes to Supabase or Falkor; it only reads (via `run_pipeline_d` → `retriever_supabase` / `retriever_falkor`).

### 0.6 Test data + fixtures

- **30-question gold source**:
  - `evals/gold_retrieval_v1.jsonl` (one JSON per line — machine read). Fields: `qid`, `type` (S=single / M=multi), `query_shape`, `macro_area`, `initial_question_es`, `expected_topic`, `expected_subtopic`, `expected_article_keys`, `followup_question_es`, `sub_questions` (list for M-type).
  - `docs/quality_tests/EVALUACION-CORPUS-30-PREGUNTAS-RESPUESTAS.md` (prose version with reference answers + follow-ups). Informational; the JSONL is canonical.
- **Unit-test fixtures** live alongside their tests. The launcher gets its own `tests/test_run_ab_comparison.py` with a tiny in-memory fake pipeline_d.

### 0.7 Glossary

| Term | Meaning |
|---|---|
| **Prior mode** | `LIA_TEMA_FIRST_RETRIEVAL=off` — the v4-era retrieval path (legacy article_number lookup + ANY-edge traversal). Baseline for this eval. |
| **New mode** | `LIA_TEMA_FIRST_RETRIEVAL=on` — the v5 path. Retriever starts at `TopicNode` and fans out via `<-[:TEMA]-` before article lookup. |
| **Shadow mode** | `LIA_TEMA_FIRST_RETRIEVAL=shadow` — diagnostic-only; runs the new Cypher + emits events but returns the legacy result. Explicitly NOT used in this eval. |
| **AB run** | One execution of the launcher: 30 questions × 2 modes = 60 pipeline_d calls; one output .md + .jsonl + manifest. Self-contained. |
| **Expert panel** | External accountant reviewers who read the side-by-side .md and pick a verdict per question: `new_better`, `prior_better`, `tie`, `both_wrong`, `need_clarification`. |
| **Go/no-go gate** | Operator reads the panel's aggregated verdicts. If `new_better + tie >= 24/30` AND `prior_better <= 3/30`, flip `LIA_TEMA_FIRST_RETRIEVAL` to `on` in staging + production. Thresholds are operator-proposed; see §2.3. |

### 0.8 Source-of-truth pointers

| Concern | Canonical source |
|---|---|
| Pipeline entry point for one query | `scripts/eval_retrieval.py:310-340` — shows the `resolve_chat_topic` → `PipelineCRequest` → `run_pipeline_d` pattern |
| Feature flag parsing | `src/lia_graph/pipeline_d/retriever_falkor.py::_tema_first_mode()` |
| Env matrix | `docs/orchestration/orchestration.md` (versioned; current v2026-04-22-ac1+) |
| Detached-launcher template | `scripts/ingestion/launch_phase9a.sh` (shell) + CLAUDE.md §"Long-running Python processes" |
| Heartbeat renderer | `scripts/monitoring/ingest_heartbeat.py` |
| Bogotá AM/PM convention | user memory `feedback_time_format_bogota.md` + applied repo-wide |
| v5 Phase 3 background | `docs/next/ingestionfix_v5.md §5 Phase 3` — TEMA-first design + rollout plan |

### 0.9 Design-skill invocation pattern

Two skills are relevant and should be used when applicable:

- **`simplify`** — after Phase 2 renderer lands, invoke it on the new launcher+renderer code to prune any duplicated formatting logic or overly defensive try/except.
- **`security-review`** — invoke before the live Phase 4 run. Confirms no secrets leak into the output .md (the answer text is user-visible; confirm Supabase service-role tokens, Gemini API keys, doc_ids, etc. never get echoed). Zero prod writes means the surface is narrow but a review pass keeps it honest.

Do NOT invoke `reconstructor` or `incremental-architect` — this task is narrow and time-bounded; architecture guidance is overkill.

### 0.10 Git conventions

- Work on branch `feat/evaluacion-ingestionfixtask-v1-ab-harness` off `main` (NOT off any v4/v5 branch).
- Commits: `feat(evaluacion-ingestionfixtask-v1-phase-N): <what>` with a body that cites specific §5 Phase N acceptance items it closes.
- Never amend a pre-existing commit; never `push --force` to any shared branch.
- PR title: `feat(evaluacion-v1): A/B harness for TEMA-first retrieval vs prior mode`.

### 0.11 Non-negotiables

- **Production read-only.** The launcher calls `run_pipeline_d` which in production mode reads from Supabase + Falkor. It must NOT write anything to those backends. If any code path you're modifying would emit a write event, stop and surface it.
- **Reproducible from disk.** After a run, every .md in the output is reproducible from the companion .jsonl. The renderer is pure: `jsonl → md` with no network calls.
- **Crash survival.** Appending per-question rows to the .jsonl must be atomic (open in append mode, flush after each write). A kill -9 mid-run leaves a partial file that can be rendered for whatever completed.
- **Clear labeling.** In the .md, mode labels are bold and appear in the answer block heading itself (`**[PRIOR MODE]**` / `**[NEW MODE]**`). A skimming reader must never confuse which mode produced which answer.
- **Env matrix unchanged.** This task does not introduce new `LIA_*` flags. It uses the existing `LIA_TEMA_FIRST_RETRIEVAL`. No `orchestration.md` bump needed.
- **Never run the full pytest in one process.** Use `make test-batched` or single-file `uv run pytest`. Conftest guard applies.
- **Bogotá AM/PM** for all user-facing times (run start/end in the .md manifest + rendered header). Machine logs stay UTC ISO (events.jsonl, .jsonl output rows).

---

## §1 Prior work — context + motivation

### 1.1 What v5 left for this task

- `LIA_TEMA_FIRST_RETRIEVAL` flag shipped (`src/lia_graph/pipeline_d/retriever_falkor.py`).
- Default is `shadow` in dev/staging, `off` in production. Flipping production to `on` is gated on evidence of quality improvement — this eval produces that evidence.
- Falkor state as of v5 close-out: 65+ TopicNodes, ~2,400+ TEMA edges (after F15 re-ingest), ~84 SubTopicNodes, 339 HAS_SUBTOPIC edges.

### 1.2 Why 30 questions from `gold_retrieval_v1.jsonl`

- Already curated by the structural-work v1 effort with macro-area coverage: renta PJ / renta PN / IVA / retención / laboral / procedimiento / sectoral / NIIF / sanciones / régimen simple.
- Each record carries `expected_article_keys` so the aggregate retrieval@10 metric can still be computed in parallel to the prose answer. (Optional; this eval's primary output is prose for human review.)
- Mix of `S` (single-point) and `M` (multi-`¿…?`) questions — covers both simple and compound prompts, which is important because TEMA-first adds candidates per sub-question as much as per top-level query.

### 1.3 Why NOT the 100-question accountant set

- `evals/100qs_accountant.jsonl` is a separate corpus, scored with a different rubric. Its reference answers aren't aligned with the TEMA-first change. Conflating the two would muddy the panel's signal. Keep scopes distinct.

### 1.4 Known limitations of the approach

- Two modes in the same process via `os.environ` toggling before each call. The retriever reads the env at call time, so this works, but it means we can't parallelize (toggling env is process-global). Sequential only. ~20–30 min wall time expected.
- The LLM polish stage is non-deterministic — back-to-back runs with identical retrieval candidates can still produce slightly different prose. We accept that; the panel compares "typical answer shape", not byte-for-byte prose.
- Supabase hybrid search is identical in both modes (Supabase side is unchanged by v5). Differences between prior and new answers come entirely from the Falkor side.

---

## §2 Problem summary (TL;DR)

**Goal.** Ship a deterministic, operator-runnable launcher that:
1. Reads `evals/gold_retrieval_v1.jsonl`.
2. For each of 30 questions, runs `run_pipeline_d` twice — once with `LIA_TEMA_FIRST_RETRIEVAL=off` (prior), once with `=on` (new).
3. Appends each result row to a per-run .jsonl in `artifacts/eval/` atomically.
4. Renders the final side-by-side panel .md from the .jsonl at end-of-run.
5. Writes a run manifest with flag states, Falkor baseline metrics, and wall times.

**Expert-panel verdict workflow.** Output .md has a `verdict:` placeholder per question that the panel fills in. After all 30 are scored, operator aggregates verdicts and decides whether to flip the production flag.

**Explicitly out of scope.**
- Automated answer grading (no LLM-judge). Human panel only.
- 100-question eval (`100qs_accountant.jsonl`) — separate task.
- Changes to retrieval logic. This is a measurement harness; it touches no production code.
- `Normativa`/`Interpretación` surfaces. Main chat only.
- Changes to `orchestration.md` env matrix (no new flags introduced).

### 2.3 Operator-proposed go/no-go thresholds

The panel returns one verdict per question (`new_better`, `prior_better`, `tie`, `both_wrong`, `need_clarification`). Operator aggregates and applies:

- **Green-light flip**: `new_better + tie ≥ 24/30` AND `prior_better ≤ 3/30` AND `both_wrong ≤ 3/30`.
- **Hold**: `prior_better` between 4–8 OR `both_wrong > 3`. Investigate specific losing questions; patch retriever before re-running.
- **Rollback**: `prior_better ≥ 9/30`. Something is structurally worse in the new path — revert the default from `shadow` to `off` in `scripts/dev-launcher.mjs`, add a v6 followup to redesign.

These are proposals for the operator to confirm in §8 after seeing the doc. Not hard-coded in the launcher.

---

## §3 Scope + phasing overview

Five phases. Each is independently shippable + reversible. Total: ~6-8 hours of engineering plus one ~20–30 min live run.

| Phase | Purpose | Effort | Wall | Blocks |
|---|---|---|---|---|
| 1 | Launcher scaffold — reads JSONL, runs both modes per question, appends to .jsonl atomically. No rendering yet. | ~2 hr | ~2 hr | Phase 2 |
| 2 | Markdown renderer — pure `.jsonl → .md` transformer with clear mode labels + verdict placeholders. | ~1.5 hr | ~1.5 hr | Phase 3 |
| 3 | Unit tests + dry-run against a 2-question subset; confirms round-trip render fidelity + crash-resume. | ~1.5 hr | ~1.5 hr | Phase 4 |
| 4 | Live production run — detached + heartbeat per CLAUDE.md, 30 questions × 2 modes, ~20–30 min wall. | ~10 min ops | ~30 min unattended | Phase 5 |
| 5 | Handoff: README + panel instructions; operator routes .md to expert reviewers. | ~30 min | async (panel response time) | v5 flag decision |

Total: ~5.5 hr engineering + ~30 min live + async panel response.

---

## §4 Pre-flight checklist (run before Phase 1)

- [ ] `git status` clean on a fresh branch: `feat/evaluacion-ingestionfixtask-v1-ab-harness` off **main**.
- [ ] v5 branch (`feat/ingestionfix-v5-retrieval-graph`) merged to main OR available as base. Check `git log --oneline main | head -5` for v5 commits.
- [ ] `.env.staging` sourceable (`set -a; source .env.staging; set +a`; `echo $SUPABASE_URL` non-empty).
- [ ] Falkor reachable: `PYTHONPATH=src:. uv run python -c "from lia_graph.graph.client import GraphClient; print(GraphClient.from_env().redacted_url)"` prints a non-empty URL.
- [ ] Pipeline dry-run: `PYTHONPATH=src:. uv run python scripts/eval_retrieval.py --help` runs without import errors (confirms `run_pipeline_d` + `resolve_chat_topic` imports still work).
- [ ] `evals/gold_retrieval_v1.jsonl` exists: `wc -l evals/gold_retrieval_v1.jsonl` returns 30 (or whatever N; eval handles variable N).
- [ ] `artifacts/eval/` directory exists or is creatable (the launcher creates it).
- [ ] Current Falkor baseline snapshot captured to `artifacts/eval/falkor_baseline_v5.json` (for the run manifest). One-liner:
  ```bash
  set -a; source .env.staging; set +a
  PYTHONPATH=src:. uv run python -c "
  from lia_graph.graph.client import GraphClient, GraphWriteStatement
  import json, datetime
  g = GraphClient.from_env()
  def q(s):
      stmt = GraphWriteStatement(description=s, query=s, parameters={})
      return list(g.execute(stmt, strict=True).rows)[0]['n']
  snap = {
      'captured_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'TopicNode': q('MATCH (n:TopicNode) RETURN count(n) AS n'),
      'TEMA_edges': q('MATCH ()-[:TEMA]->() RETURN count(*) AS n'),
      'ArticleNode': q('MATCH (a:ArticleNode) RETURN count(a) AS n'),
      'SubTopicNode': q('MATCH (s:SubTopicNode) RETURN count(s) AS n'),
      'HAS_SUBTOPIC': q('MATCH ()-[:HAS_SUBTOPIC]->() RETURN count(*) AS n'),
  }
  import pathlib
  pathlib.Path('artifacts/eval').mkdir(parents=True, exist_ok=True)
  pathlib.Path('artifacts/eval/falkor_baseline_v5.json').write_text(json.dumps(snap, indent=2))
  print(snap)
  "
  ```

---

## §5 Phases

### Phase 1 — Launcher scaffold

**Goal.** Write the core runner. Reads the gold JSONL, for each question invokes `run_pipeline_d` with both flag values, appends a per-question result row to an atomic-append .jsonl. No rendering, no tests yet (Phase 3).

#### Phase 1 — Files to create

| Path | Purpose |
|---|---|
| `scripts/evaluations/__init__.py` | Make the directory a package (empty file). |
| `scripts/evaluations/run_ab_comparison.py` | The launcher. Reads `evals/gold_retrieval_v1.jsonl`, iterates questions, toggles `LIA_TEMA_FIRST_RETRIEVAL` between `off` and `on` per call, captures `PipelineCResponse.answer_markdown` + selected diagnostics, appends to output `.jsonl`. |
| `artifacts/eval/.gitkeep` | Create the output dir so CI + new clones see it. |

#### Phase 1 — Files to modify

None.

#### Phase 1 — run_ab_comparison.py contract (binding for Phase 1)

CLI shape:
```bash
PYTHONPATH=src:. uv run --group dev python scripts/evaluations/run_ab_comparison.py \
  --gold evals/gold_retrieval_v1.jsonl \
  --output-dir artifacts/eval \
  --manifest-tag v5_tema_first_vs_prior \
  [--limit N]                # optional subset (e.g. first 2 for dry-run)
  [--resume <existing_jsonl>] # optional — skip qids already in the partial file
  [--target production]       # default production; accepts wip
```

Behavior:
1. Load gold; iterate in JSONL order.
2. For each question:
   - Set `os.environ["LIA_TEMA_FIRST_RETRIEVAL"] = "off"`; call `run_pipeline_d` via the eval_retrieval.py pattern; capture `answer_markdown` + `diagnostics`.
   - Set `os.environ["LIA_TEMA_FIRST_RETRIEVAL"] = "on"`; call again; capture.
   - Append one JSON row to `<output-dir>/ab_comparison_<ts>.jsonl` with `{qid, query, macro_area, prior: {...}, new: {...}, wall_ms_prior, wall_ms_new, trace_ids}`.
   - Flush + fsync after each write.
3. On process end (or SIGINT), write `<output-dir>/ab_comparison_<ts>_manifest.json` with: `run_started_at_utc`, `run_completed_at_utc`, `run_started_bogota`, `run_completed_bogota`, `gold_path`, `questions_attempted`, `questions_succeeded`, `questions_failed`, `falkor_baseline` (from pre-flight), `git_commit_sha`, `lia_graph_version_if_any`, `env_flag_matrix` (which envs were set).
4. If `--resume` is given: read the existing .jsonl, extract `qid` set, skip those; continue appending to the SAME file (not a new one) with the same timestamp.

Explicit error handling:
- `run_pipeline_d` raises → catch, log to stderr with qid + traceback, append a `{qid, query, error: "…traceback…", mode_failed: "prior"|"new"}` row so the renderer can surface the failure and the run continues.
- `SIGINT` (Ctrl-C) → finish the current question's pair, then exit; manifest written with partial counts.

Diagnostics to capture per mode (trim to these — the others inflate the row for no panel benefit):
```
answer_markdown                       # full
diagnostics.retrieval_backend         # confirms which half served
diagnostics.graph_backend             # confirms Falkor mode
diagnostics.primary_article_count
diagnostics.connected_article_count
diagnostics.related_reform_count
diagnostics.seed_article_keys         # list of anchor ids retrieved
diagnostics.tema_first_mode           # "off" | "shadow" | "on" — for the NEW row confirms it fired
diagnostics.tema_first_topic_key
diagnostics.tema_first_anchor_count   # delta signal: how many articles TEMA-first contributed
diagnostics.planner_query_mode
effective_topic                       # from routing
trace_id                              # for cross-reference to logs/events.jsonl
```

#### Phase 1 — Tests (on the specific surface touched)

None in Phase 1; tests land in Phase 3 against the renderer + a fake pipeline. The Phase 1 launcher calls live pipeline_d — mock at Phase 3.

#### Phase 1 — Run

Local dry-check (import + help only, no network):
```bash
PYTHONPATH=src:. uv run --group dev python scripts/evaluations/run_ab_comparison.py --help
```
Expected: argparse help output, no traceback.

#### Phase 1 — Acceptance

1. File exists with the CLI shape above.
2. Help runs without import errors.
3. Launcher is importable as a module (`python -c "from scripts.evaluations import run_ab_comparison"`).
4. Code uses the `resolve_chat_topic → PipelineCRequest → run_pipeline_d` pattern from `scripts/eval_retrieval.py:310-340`; no copy-paste drift from that reference.

#### Phase 1 — State log (fill in as you go)

```yaml
phase_1_launcher:
  status: pending          # pending | in_progress | completed | blocked
  started_at:              # Bogotá AM/PM
  completed_at:
  branch:                  # feat/evaluacion-ingestionfixtask-v1-ab-harness
  files_created:
    - scripts/evaluations/__init__.py
    - scripts/evaluations/run_ab_comparison.py
    - artifacts/eval/.gitkeep
  acceptance_checks:
    - [ ] CLI shape matches §5 Phase 1 contract
    - [ ] --help runs clean
    - [ ] Module importable
    - [ ] pipeline_d invocation matches eval_retrieval.py:310-340
  blockers: []
  resumption_hint: ""      # fill in if the phase doesn't finish in one sitting
```

---

### Phase 2 — Markdown renderer

**Goal.** Pure transformer: takes the Phase 1 `.jsonl` + manifest, produces one side-by-side `.md` suitable for the expert panel. Offline, deterministic, zero network.

#### Phase 2 — Files to create

| Path | Purpose |
|---|---|
| `scripts/evaluations/render_ab_markdown.py` | Pure renderer. CLI: `--jsonl <path> --manifest <path> --output <.md path>`. |

#### Phase 2 — Rendered document structure

```
# A/B Evaluation: TEMA-first retrieval vs prior mode
Run: <manifest_tag>
Started:   <bogota AM/PM>  (UTC: <iso>)
Completed: <bogota AM/PM>  (UTC: <iso>)
Git:       <sha>   Branch: <branch>

Falkor baseline (pre-run): TopicNode <N>, TEMA <N>, Article <N>, SubTopic <N>
Env flag matrix (per mode): see manifest.json.

---

## Panel instructions (read first)

Every question below contains two answer blocks, clearly labeled
**[PRIOR MODE]** and **[NEW MODE]**. For each question, read both blocks and
fill in the `verdict:` field with ONE of:
  - `new_better`     — the new-mode answer is materially better for the reader
  - `prior_better`   — the prior-mode answer is materially better
  - `tie`            — answers are equivalent in usefulness
  - `both_wrong`     — neither answers the question correctly
  - `need_clarification` — the question is ambiguous / outside scope; no verdict

Add any short free-text commentary in the `notes:` field. Do NOT edit the
answer text or diagnostics blocks.

---

## Q1 — <macro_area> — <query_shape> — <type>

**Query.** <initial_question_es>

<if multi, list sub_questions>

**Expected topic:** <expected_topic>  **Expected subtopic:** <expected_subtopic or "—">

---

### [PRIOR MODE] — `LIA_TEMA_FIRST_RETRIEVAL=off`

<answer_markdown>

<details><summary>Diagnostics</summary>

- retrieval_backend: <…>
- graph_backend: <…>
- primary_article_count: <N>
- seed_article_keys: [<first 10>]
- tema_first_mode (confirm off): off
- wall_ms: <N>
- trace_id: <id>
</details>

---

### [NEW MODE] — `LIA_TEMA_FIRST_RETRIEVAL=on`

<answer_markdown>

<details><summary>Diagnostics</summary>

- retrieval_backend: <…>
- graph_backend: <…>
- primary_article_count: <N>
- seed_article_keys: [<first 10>]
- tema_first_mode: on
- tema_first_topic_key: <…>
- tema_first_anchor_count: <N>
- wall_ms: <N>
- trace_id: <id>
</details>

---

**Panel verdict block**
```yaml
verdict:                  # one of: new_better | prior_better | tie | both_wrong | need_clarification
notes:                    # free text, one paragraph max
```

---

## Q2 — … (repeats per question)

---

## Aggregate (filled by operator after panel review)

```yaml
totals:
  new_better:
  prior_better:
  tie:
  both_wrong:
  need_clarification:
decision:                  # flip_to_on | hold | rollback
decision_reason:           # one-paragraph justification citing specific qids
signed_off_by:
signed_off_at_bogota:
```
```

#### Phase 2 — Files to modify

None.

#### Phase 2 — Tests

| Test | What it locks |
|---|---|
| `test_render_minimal_jsonl` | One-question JSONL + fake manifest renders without error; mode labels appear in bold. |
| `test_render_preserves_answer_markdown_verbatim` | Answer text is not mutated (no markdown escaping added). |
| `test_render_emits_verdict_placeholder` | Each question block ends with a YAML `verdict:` placeholder. |
| `test_render_skips_failed_rows_with_explicit_note` | If a row carries `error:`, the mode block replaces the answer with `**[ERROR]** <traceback excerpt>` instead of crashing. |
| `test_render_aggregate_section_present` | Final "Aggregate" YAML block exists with the expected keys. |

All in `tests/test_render_ab_markdown.py` — new file. Keep fake JSONL small inline; no fixtures directory needed.

#### Phase 2 — Run

```bash
PYTHONPATH=src:. uv run pytest tests/test_render_ab_markdown.py -v
```

#### Phase 2 — Acceptance

1. All 5 renderer tests green.
2. Rendering a hand-written 2-question JSONL produces a byte-for-byte reproducible output (no timestamp drift between runs).
3. Running `diff` between two consecutive render calls on the same input shows zero changes.

#### Phase 2 — State log

```yaml
phase_2_renderer:
  status: pending
  started_at:
  completed_at:
  files_created:
    - scripts/evaluations/render_ab_markdown.py
    - tests/test_render_ab_markdown.py
  tests_passing:
  acceptance_checks:
    - [ ] 5 renderer tests green
    - [ ] Byte-identical re-render on same input
  blockers: []
  resumption_hint: ""
```

---

### Phase 3 — Unit tests + dry-run

**Goal.** Cover the launcher with unit tests using a fake pipeline_d, then do an end-to-end dry-run against a 2-question subset of the real gold.

#### Phase 3 — Files to create

| Path | Purpose |
|---|---|
| `tests/test_run_ab_comparison.py` | Unit tests: arg parsing, resume logic, atomic append, env toggling, failure-row emission, SIGINT handling. ~8 cases. |

#### Phase 3 — Fake pipeline_d strategy

The launcher imports `run_pipeline_d` from `lia_graph.pipeline_d`. In tests, monkey-patch `lia_graph.pipeline_d.run_pipeline_d` to a deterministic fake that reads `os.environ["LIA_TEMA_FIRST_RETRIEVAL"]` and returns a pre-canned `PipelineCResponse` whose `answer_markdown` includes the current env value. This lets tests assert "the launcher set the env before each call" without running real retrieval.

#### Phase 3 — Tests

| Test | What it locks |
|---|---|
| `test_launcher_sets_env_off_before_prior_call` | On first call per question, `LIA_TEMA_FIRST_RETRIEVAL` is `off`. |
| `test_launcher_sets_env_on_before_new_call` | On second call per question, env is `on`. |
| `test_launcher_restores_env_on_exit` | After the run, env is back to whatever the pre-run state was (or unset if it started unset). |
| `test_launcher_appends_one_row_per_question_atomically` | After N questions, JSONL has N lines, each valid JSON. Flushed between writes (force it by killing mid-call in test and verifying partial file is readable). |
| `test_launcher_resume_skips_completed_qids` | Existing JSONL with qids `Q1,Q2` → re-run with `--resume` starts at Q3. |
| `test_launcher_failure_row_emitted_for_pipeline_error` | Fake pipeline raises → launcher writes `{qid, error, mode_failed}` row; next question continues. |
| `test_launcher_manifest_includes_required_fields` | Manifest JSON has all fields from §5 Phase 1 contract. |
| `test_launcher_limit_flag_truncates_input` | `--limit 2` processes only first 2 gold rows. |

#### Phase 3 — Dry-run (live, 2 questions only)

Before Phase 4's full run, verify plumbing end-to-end against production:

```bash
set -a; source .env.staging; set +a
PYTHONPATH=src:. uv run --group dev python scripts/evaluations/run_ab_comparison.py \
  --gold evals/gold_retrieval_v1.jsonl \
  --output-dir artifacts/eval \
  --manifest-tag v5_dry_run \
  --limit 2
```

Expected:
- Wall time ~1–2 min (2 questions × 2 modes × ~20–30s each).
- `artifacts/eval/ab_comparison_<ts>.jsonl` has 2 rows.
- `artifacts/eval/ab_comparison_<ts>_manifest.json` has `questions_succeeded: 2`.
- Render it and eyeball: `PYTHONPATH=src:. uv run python scripts/evaluations/render_ab_markdown.py --jsonl <.jsonl> --manifest <manifest.json> --output /tmp/dry.md`.
- Open `/tmp/dry.md` — confirm the two mode labels + verdict placeholder per question.

#### Phase 3 — Acceptance

1. All 8 launcher tests green.
2. Dry-run produces the expected .jsonl + manifest + rendered .md, no exceptions in logs.
3. Rendered .md passes visual mode-label check (both labels present + bold, distinguishable).
4. The two answers for at least one of the two dry-run questions are NOT byte-identical (confirms the env flag is actually changing retrieval; if they ARE identical, the flag isn't wired through — investigate before Phase 4).

#### Phase 3 — State log

```yaml
phase_3_tests_and_dryrun:
  status: pending
  started_at:
  completed_at:
  files_created:
    - tests/test_run_ab_comparison.py
  tests_passing:
  dry_run_output_jsonl:     # path
  dry_run_output_md:        # path
  dry_run_mode_labels_bold: # bool
  dry_run_answers_differ:   # bool — critical signal
  blockers: []
  resumption_hint: ""
```

---

### Phase 4 — Live production run

**Goal.** Run the full 30 questions × 2 modes × production. Detached + heartbeat per CLAUDE.md.

#### Phase 4 — Pre-flight

- Phase 3 dry-run passed AND the two answers for ≥1 question differ.
- `artifacts/eval/falkor_baseline_v5.json` captured within the last hour (re-run §4 snapshot command if stale).
- No other long-running ingest process currently touching Falkor (queries share the read path but shouldn't collide; err on the side of isolation for a clean A/B).

#### Phase 4 — Run recipe

```bash
cd /Users/ava-sensas/Developer/Lia_Graph
TS=$(date -u +%Y%m%dT%H%M%SZ)
LOG="logs/evaluations-ab-${TS}.log"
MANIFEST_TAG="v5_tema_first_vs_prior_live"

nohup bash -c '
  set -a; source .env.staging; set +a
  exec env PYTHONPATH=src:. uv run --group dev python \
    scripts/evaluations/run_ab_comparison.py \
    --gold evals/gold_retrieval_v1.jsonl \
    --output-dir artifacts/eval \
    --manifest-tag '"$MANIFEST_TAG"' \
    --target production
' > "$LOG" 2>&1 < /dev/null &
BG_PID=$!
disown $BG_PID 2>/dev/null || true
echo "BG_PID=$BG_PID LOG=$LOG"
```

#### Phase 4 — Heartbeat cron

```bash
# Arm a 3-min heartbeat that tails the .jsonl line count + checks PID health.
# Use CronCreate from the Claude Code harness (session-scoped).
# Prompt template (adjust delta_id, start ts, pid):
#
# v5 A/B run heartbeat. Count completed rows:
#   ROWS=$(wc -l < $(ls -t artifacts/eval/ab_comparison_*.jsonl | head -1))
#   PS_ALIVE=$(ps -p <BG_PID> -o pid= 2>/dev/null | tr -d ' ')
#   echo "rows=$ROWS/30 pid_alive=$PS_ALIVE"
#
# Decisions:
#  - ROWS==30 AND pid_alive="": run renderer + surface .md path. CronDelete.
#  - ROWS<30 AND pid_alive="": silent death — surface log tail, STOP.
#  - Otherwise: one-line update + /loop 180s.
#
# All times Bogotá AM/PM.
```

(Create at Phase 4 time using the session's CronCreate tool; the exact prompt will reference the live BG_PID + log path captured above. Do not commit the cron text into the repo — it's session-scoped.)

#### Phase 4 — Render final .md

Once the launcher exits:

```bash
cd /Users/ava-sensas/Developer/Lia_Graph
JSONL=$(ls -t artifacts/eval/ab_comparison_*v5_tema_first_vs_prior_live.jsonl | head -1)
MANIFEST="${JSONL%.jsonl}_manifest.json"
OUT="${JSONL%.jsonl}.md"
PYTHONPATH=src:. uv run python scripts/evaluations/render_ab_markdown.py \
  --jsonl "$JSONL" --manifest "$MANIFEST" --output "$OUT"
echo "Panel doc ready: $OUT"
```

#### Phase 4 — Acceptance

1. .jsonl has exactly 30 rows (or N if gold was resized).
2. Manifest `questions_succeeded >= 28`. Two failures tolerated (network flake / Gemini timeout). Three or more: investigate, re-run the failures with `--resume`.
3. Rendered .md compiles without broken yaml blocks (quick check: `grep -c "^verdict:" panel.md` returns 30).
4. No secrets in the .md: `grep -iE "supabase_service_role|SUPABASE_.*KEY|GOOGLE_API_KEY|sk-" panel.md` returns zero.
5. Wall time ≤ 45 min (upper bound; typical ~20–30).

#### Phase 4 — State log

```yaml
phase_4_live_run:
  status: pending
  started_at_bogota:
  completed_at_bogota:
  started_at_utc:
  completed_at_utc:
  bg_pid:
  log_path:
  output_jsonl:
  output_manifest:
  output_md:
  questions_attempted:
  questions_succeeded:
  questions_failed: []   # list of {qid, mode, error_excerpt}
  wall_minutes:
  falkor_baseline_path: artifacts/eval/falkor_baseline_v5.json
  secrets_leak_check: pending   # pending | passed | failed
  acceptance_checks:
    - [ ] 30 rows in .jsonl
    - [ ] manifest questions_succeeded ≥ 28
    - [ ] 30 verdict placeholders in .md
    - [ ] secrets check clean
    - [ ] wall ≤ 45 min
  blockers: []
  resumption_hint: ""   # e.g. "Q17 failed on Gemini 429; re-run with --resume <jsonl>"
```

---

### Phase 5 — Handoff + panel instructions

**Goal.** Deliver the rendered .md to the expert panel with enough scaffolding that they can score + return verdicts without more engineering help.

#### Phase 5 — Files to create

| Path | Purpose |
|---|---|
| `scripts/evaluations/README.md` | Operator + panel cheat sheet. How to read the .md, how to fill verdicts, how to return the scored file, how operator aggregates. |

#### Phase 5 — README content outline

```
# A/B retrieval evaluation — panel handoff

## What this is
We changed how the graph part of retrieval works (v5 TEMA-first). This
document compares 30 answers from the old path vs the new path so a
panel of accountants can tell us whether the change is a win.

## How to score
Open the rendered .md. For each of 30 questions:
  1. Read the question + both answer blocks.
  2. Fill the `verdict:` line with one of the 5 allowed values (see
     Panel instructions at the top of the .md).
  3. Optionally add a one-paragraph note.
  Do NOT edit anything else.

## How to return
Save the file + email/share it back. Operator takes the completed
verdicts + fills the Aggregate section at the bottom, then decides
whether to flip the production flag.

## Go/no-go rule (operator sees this too)
  - Flip on: new_better + tie ≥ 24/30  AND  prior_better ≤ 3/30
    AND  both_wrong ≤ 3/30
  - Hold:    prior_better between 4–8, or both_wrong > 3
  - Rollback: prior_better ≥ 9/30

## If something looks weird
Reach the engineer who ran it (commit SHA is in the manifest). They can
re-run specific qids via `--resume` without starting from scratch.
```

#### Phase 5 — Acceptance

1. README committed.
2. Rendered .md shared with the panel (out-of-band — email/drive; path in session handoff note).
3. Session handoff note stamped in §8 below with: output .md path, panel contact, expected-verdict-back date.

#### Phase 5 — State log

```yaml
phase_5_handoff:
  status: pending
  started_at_bogota:
  completed_at_bogota:
  readme_committed: pending
  md_shared_with_panel_at_bogota:
  panel_contact:
  expected_verdicts_back_by:
  aggregate_filled_by_operator: pending
  final_decision: pending   # flip_to_on | hold | rollback
  decision_reason:
  signed_off_by:
  signed_off_at_bogota:
  blockers: []
```

---

## §6 End-to-end execution recipe

Single-shot path (after plan sign-off):

```bash
git checkout -b feat/evaluacion-ingestionfixtask-v1-ab-harness main

# --- Phase 1: scaffold
$EDITOR scripts/evaluations/__init__.py
$EDITOR scripts/evaluations/run_ab_comparison.py
mkdir -p artifacts/eval && touch artifacts/eval/.gitkeep
PYTHONPATH=src:. uv run --group dev python scripts/evaluations/run_ab_comparison.py --help
git commit -am "feat(evaluacion-ingestionfixtask-v1-phase-1): launcher scaffold + CLI shape"

# --- Phase 2: renderer
$EDITOR scripts/evaluations/render_ab_markdown.py
$EDITOR tests/test_render_ab_markdown.py
PYTHONPATH=src:. uv run pytest tests/test_render_ab_markdown.py -v
git commit -am "feat(evaluacion-ingestionfixtask-v1-phase-2): markdown renderer + 5 tests"

# --- Phase 3: unit tests + dry-run
$EDITOR tests/test_run_ab_comparison.py
PYTHONPATH=src:. uv run pytest tests/test_run_ab_comparison.py -v
set -a; source .env.staging; set +a
PYTHONPATH=src:. uv run --group dev python scripts/evaluations/run_ab_comparison.py \
  --gold evals/gold_retrieval_v1.jsonl \
  --output-dir artifacts/eval \
  --manifest-tag v5_dry_run \
  --limit 2
# visually inspect dry-run .md (confirm answers differ + labels present)
git commit -am "feat(evaluacion-ingestionfixtask-v1-phase-3): unit tests + 2-question dry-run validated"

# --- Phase 4: live run (detached + heartbeat)
# Capture Falkor baseline (see §4 pre-flight).
# Launch per §5 Phase 4 recipe. Arm heartbeat. Wait for cli exit.
# Render the panel .md.
git commit -am "feat(evaluacion-ingestionfixtask-v1-phase-4): live 30-question run + rendered panel doc"

# --- Phase 5: handoff
$EDITOR scripts/evaluations/README.md
git commit -am "feat(evaluacion-ingestionfixtask-v1-phase-5): panel handoff README"

# Push + PR
git push -u origin feat/evaluacion-ingestionfixtask-v1-ab-harness
gh pr create --title "feat(evaluacion-v1): A/B harness for TEMA-first retrieval vs prior mode" \
  --body-file <summary>
```

---

## §7 Rollback + recovery

- **Phase 1/2/3 code defects**: local branch; `git reset --hard` or `git checkout -- <file>` before pushing. No prod impact.
- **Phase 3 dry-run fails**: launcher bug → fix + re-run. Dry-run artifacts can be discarded (`rm artifacts/eval/ab_comparison_*v5_dry_run*`).
- **Phase 4 mid-run crash**: the .jsonl preserves completed pairs; re-launch with `--resume <existing_jsonl>` to pick up where it stopped.
- **Phase 4 looks wrong**: delete the output artifacts, investigate, re-run. Since this is read-only, no Supabase/Falkor cleanup needed.
- **Panel returns rollback verdict**: flip `scripts/dev-launcher.mjs` default from `shadow` to `off` for `LIA_TEMA_FIRST_RETRIEVAL`, open a v6 followup doc citing which qids failed.

---

## §8 Global state ledger

*Single source of truth for implementation status. Update at every phase transition. Commit after each update.*

```yaml
plan_version: 1.0
plan_last_updated:                # Bogotá AM/PM
plan_signed_off_by:               # operator
plan_signed_off_at:               # Bogotá AM/PM

task_goal: >
  A/B comparison of LIA_TEMA_FIRST_RETRIEVAL=off (prior) vs =on (new) across
  30 canonical evaluation questions, producing a panel-reviewable markdown
  document that decides whether v5 flips to on in production.

task_scope_out: >
  - Automated grading / LLM-as-judge
  - 100-question accountant eval (separate corpus)
  - Any change to production retrieval code
  - Normativa / Interpretación surfaces

production_state_at_task_start:
  falkor_baseline_path: artifacts/eval/falkor_baseline_v5.json
  v5_pr_merged:                   # true | false
  v5_branch:
  lia_tema_first_retrieval_default_staging: shadow
  lia_tema_first_retrieval_default_production: off

phase_1_launcher:
  status: pending
  started_at:
  completed_at:
  branch:
  files_created: []
  tests_passing: []
  notes: ""
  resumption_hint: ""

phase_2_renderer:
  status: pending
  started_at:
  completed_at:
  files_created: []
  tests_passing: []
  notes: ""
  resumption_hint: ""

phase_3_tests_and_dryrun:
  status: pending
  started_at:
  completed_at:
  files_created: []
  tests_passing: []
  dry_run_output_jsonl:
  dry_run_output_md:
  dry_run_mode_labels_bold:
  dry_run_answers_differ:
  notes: ""
  resumption_hint: ""

phase_4_live_run:
  status: pending
  started_at_bogota:
  completed_at_bogota:
  bg_pid:
  log_path:
  output_jsonl:
  output_manifest:
  output_md:
  questions_attempted:
  questions_succeeded:
  questions_failed: []
  wall_minutes:
  secrets_leak_check:
  notes: ""
  resumption_hint: ""

phase_5_handoff:
  status: pending
  started_at_bogota:
  completed_at_bogota:
  readme_committed: false
  md_shared_with_panel_at_bogota:
  panel_contact:
  expected_verdicts_back_by:
  aggregate_filled_by_operator: false
  final_decision:                 # flip_to_on | hold | rollback
  decision_reason:
  signed_off_by:
  signed_off_at_bogota:
  notes: ""

blockers_log: []

risks_log:
  - risk: "LLM polish non-determinism makes byte-diff confusing"
    mitigation: "Panel compares typical shape, not prose; renderer keeps both answers intact."
  - risk: "Sequential 60 queries × production Gemini cost"
    mitigation: "~$0.20–0.40 total; within eval budget."
  - risk: "Panel takes weeks to return verdicts"
    mitigation: "Phase 5 README has go/no-go thresholds; operator can decide as scoring comes in rather than wait for 30/30."
  - risk: "Mid-run network flake fails a subset of questions"
    mitigation: "--resume flag + tolerate ≤2 failures in manifest acceptance."
  - risk: "Secrets leak into rendered .md"
    mitigation: "Acceptance gate: grep check before handoff. Security-review skill pass before Phase 4."

followups_for_later:
  - id: F16
    source: this task
    description: >
      If the panel returns 'hold', build a per-question retrieval-diff tool
      that surfaces exactly which article_keys each mode contributed, not
      just the final prose. Helps localize which retrieval paths to tune.
  - id: F17
    source: this task
    description: >
      Generalize the harness to run any 2 env-flag combinations (not hard-
      coded LIA_TEMA_FIRST_RETRIEVAL). Useful for future A/B evals of
      LIA_RERANKER_MODE, LIA_QUERY_DECOMPOSE, etc.
  - id: F18
    source: this task
    description: >
      Add an automated agreement metric (Fleiss' kappa over panel
      verdicts) to decide when the eval has enough signal to decide.
      Out of scope for v1 which uses a single panel review.
```

---

## §9 Carry-forward learnings from v4/v5

1. **Detached launch + heartbeat every time.** A 30-question × 2-mode run is ~20–30 min. `nohup + disown + >log 2>&1` is the template.
2. **Anchor progress on `logs/events.jsonl` + atomic append files.** Never rely on a `--json` end-of-run summary; mid-run crashes lose everything.
3. **Flag toggles are env-scoped.** `os.environ["LIA_TEMA_FIRST_RETRIEVAL"] = "on"` before the retriever call; the retriever reads at call time. Same-process toggle works because the retriever does `os.getenv` per invocation (see `_tema_first_mode()` in `retriever_falkor.py`).
4. **Bogotá AM/PM** for user-facing times in rendered docs. Machine artifacts stay UTC ISO.
5. **Secrets don't escape into user-visible surfaces.** Every rendered document gets a secrets grep before handoff.

---

## §10 Operator cheat-sheet

```bash
# Phase 1–3 (local)
git checkout -b feat/evaluacion-ingestionfixtask-v1-ab-harness main
$EDITOR scripts/evaluations/run_ab_comparison.py
$EDITOR scripts/evaluations/render_ab_markdown.py
$EDITOR tests/test_render_ab_markdown.py
$EDITOR tests/test_run_ab_comparison.py
PYTHONPATH=src:. uv run pytest tests/test_render_ab_markdown.py tests/test_run_ab_comparison.py -v
# dry-run
set -a; source .env.staging; set +a
PYTHONPATH=src:. uv run --group dev python scripts/evaluations/run_ab_comparison.py \
  --gold evals/gold_retrieval_v1.jsonl --output-dir artifacts/eval \
  --manifest-tag v5_dry_run --limit 2
# render dry-run
PYTHONPATH=src:. uv run python scripts/evaluations/render_ab_markdown.py \
  --jsonl $(ls -t artifacts/eval/ab_comparison_*v5_dry_run*.jsonl | head -1) \
  --manifest $(ls -t artifacts/eval/ab_comparison_*v5_dry_run*_manifest.json | head -1) \
  --output /tmp/ab_dry.md

# Phase 4 (live, detached)
# — see §5 Phase 4 recipe. Capture BG_PID + LOG. Arm heartbeat. Wait.
# Render panel doc at end. Post to handoff.

# Phase 5 — share rendered .md with expert panel + monitor incoming verdicts.
# After aggregation, fill §8 phase_5_handoff + decide flip_to_on | hold | rollback.
```

---

## §11 Connections to adjacent work

- **v5 Phase 3 `LIA_TEMA_FIRST_RETRIEVAL` flag** (`docs/next/ingestionfix_v5.md §5 Phase 3`) — this eval is the user-visible validation gate for flipping that flag.
- **`scripts/eval_retrieval.py`** — precedent pattern for the `resolve_chat_topic → PipelineCRequest → run_pipeline_d` invocation; copy the shape, don't re-invent.
- **`docs/quality_tests/EVALUACION-CORPUS-30-PREGUNTAS-RESPUESTAS.md`** — the human-readable twin of `evals/gold_retrieval_v1.jsonl`. Informational for panel reviewers if they want the reference answers; the launcher reads only the JSONL.
- **CLAUDE.md §"Long-running Python processes"** — detached-launch contract; Phase 4 follows it.
- **`docs/orchestration/orchestration.md` env matrix** — not modified by this task (no new flags introduced).

---

*End of document. Operator: sign off at §8 `plan_signed_off_by` / `plan_signed_off_at`. No code is written until that sign-off lands.*
