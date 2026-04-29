# fix_v1.md — phase 2 hand-off: sub-query LLM-skipped path (22 → 24/36 stretch)

> **Drafted 2026-04-29 ~12:35 PM Bogotá** by claude-opus-4-7 immediately after
> closing phase 1 of fix_v1. **Audience: any zero-context agent (fresh LLM or
> engineer) who picks up this work next. You can pick this up cold.**
>
> **Phase 1 status — CLOSED.** The 21 → 8/36 acc+ regression of 2026-04-29 was
> fully diagnosed and fixed by flipping `config/llm_runtime.json` `provider_order`
> back to `gemini-flash` first. Result: 22/36 acc+ with zero ok→zero
> regressions. Full write-up: `docs/re-engineer/fix/fix_v1_diagnosis.md`. The
> regression was caused by a DeepSeek-v4-pro reasoning-model behavior (returns
> empty `message.content`) that the topic resolver swallowed silently.
>
> **Phase 2 — OPEN.** The current panel result is **22/36 acc+**, which beats
> the 04-27 baseline by 1 but misses the v3-plan stretch target of **≥24/36**
> by 2. Today's deep trace surfaced the exact reason: when the query
> decomposer fans the parent message into ≥2 sub-questions, each sub-query
> calls `resolve_chat_topic` **without `runtime_config_path` or
> `conversation_state`**. The LLM topic-classifier is therefore skipped on
> every sub-query, and routing collapses to lexical-keyword fallback or
> `no_topic_detected`. This loses signal on multi-domain queries where the
> second `¿…?` is the more specific one.
>
> **What this doc is**: the diagnostic + fix hand-off for closing the gap
> from 22 → ≥24/36. Read §0 first if you have no context.

---

## 0. Zero-context primer

You are working in `/Users/ava-sensas/Developer/Lia_Graph/`, a graph-native RAG
product for Colombian accountants ("Lia Graph", branched from Lia Contador).

**Read these in order, total ~15 minutes:**

1. **`CLAUDE.md`** — repo-level operating guide. Pay attention to:
   * "Hot Path (main chat)" — the served chat code path.
   * "LLM provider split — chat vs canonicalizer (2026-04-29)" section that
     was added in phase 1 of this fix.
   * "Retrieval-stage deep trace (2026-04-29)" section explaining the
     `tracers_and_logs/` package.
   * "Fail Fast, Fix Fast — operations canon".
   * "Idea vs verified improvement — mandatory six-gate lifecycle" — every
     pipeline change passes six gates before being declared an improvement.
2. **`AGENTS.md`** — repo operating guide; read alongside CLAUDE.md.
3. **`docs/re-engineer/fix/fix_v1_diagnosis.md`** — phase 1 of this fix.
   Especially §2 (the trace evidence) and §10 (next concrete steps); §10.3
   ("sub-query LLM-skipped trace") is the work this doc continues.
4. **`tracers_and_logs/README.md`** — how to read the deep trace.
5. **`evals/sme_validation_v1/runs/20260429T172422Z_gemini_primary_full/classified.jsonl`**
   — current §1.G panel scoreboard. 22/36 acc+. The 14 non-acc+ qids are
   your target surface.
6. **`docs/aa_next/gate_9_threshold_decision.md`** — closest prior precedent
   for "is this regression real or measurement strictness?", including the
   §8.4 four-criteria gate that may apply to your fix's verification.

**Memory-pinned guardrails (do NOT violate, see `~/.claude/projects/.../memory/MEMORY.md`):**

* **Don't lower aspirational thresholds.** 24/36 stays as the §1.G gate.
  Document any qualitative-pass exception per case.
* **Diagnose before intervene.** Measure whether failures concentrate on a
  pattern before proposing a fix.
* **Lia Graph cloud writes are pre-authorized** (Supabase + Falkor only).
  Announce before writing; don't ask per-action.
* **Plain-language status reports.** No money quoting; action + effort + what
  it unblocks. Bogotá AM/PM for human-facing timestamps; UTC ISO for machine
  fields.
* **Six-gate lifecycle on every pipeline change.** Idea → plan → measurable
  criterion → test plan with actors + run env → greenlight (technical AND
  end-user) → refine-or-discard.

---

## 1. The exact bug surface

`src/lia_graph/pipeline_d/orchestrator.py:381` (current, post-phase-1 commit):

```python
for _sq_idx, sq in enumerate(sub_queries):
    sq_routing = _resolve(message=sq, requested_topic=None, pais=request.pais)
```

Compare this with the parent-message call in
`src/lia_graph/ui_chat_payload.py:381`:

```python
topic_routing = deps["resolve_chat_topic"](
    message=message,
    requested_topic=requested_topic_raw,
    pais=normalized_pais,
    runtime_config_path=deps.get("llm_runtime_config_path"),
    preserve_requested_topic_as_secondary=requested_topic_raw is not None,
    conversation_state=prior_conversation_state,
)
```

**The parent call passes `runtime_config_path` and `conversation_state`. The
sub-query call does not.** Because of this, the sub-query call hits the
LLM-deferral guard at `src/lia_graph/topic_router.py:868`:

```python
if runtime_config_path is not None and _should_attempt_llm(message, normalized_requested):
    llm_result = _classify_topic_with_llm(...)
```

…and the `if` is false on every sub-query (`runtime_config_path is None`).
The function falls through to lexical keyword scoring or `no_topic_detected`.

Trace evidence from the current run (`evals/sme_validation_v1/runs/
20260429T172422Z_gemini_primary_full/beneficio_auditoria_P2.json`,
`response.diagnostics.pipeline_trace.steps[*]`):

```
   2195.0ms  topic_router.llm_route.return     status=ok       effective_topic=beneficio_auditoria  confidence=0.9    <-- parent OK
   3709.5ms  topic_router.entry                status=info     <-- sub-query 1
   3734.7ms  topic_router.llm.skipped          status=info     <-- LLM skipped because runtime_config_path is None
   3752.9ms  topic_router.keyword_fallback     status=fallback effective_topic=declaracion_renta    confidence=0.55  <-- bad fallback
  12985.9ms  topic_router.entry                status=info     <-- sub-query 2
  13025.4ms  topic_router.no_topic_detected    status=fallback <-- worse: no topic at all
```

The trace step that names the failure is **`topic_router.llm.skipped`** with
`message="LLM path skipped — runtime_config_path missing or _should_attempt_llm=False."`

You can reproduce the trace surface by reading `tracers_and_logs/logs/
pipeline_trace.jsonl` for any sub-query qid in the current run dir.

---

## 2. Hypothesis (likely correct, but verify with §3 instrumentation pass)

**H1 (primary).** Threading `runtime_config_path` (and `conversation_state`)
through to the sub-query `_resolve(...)` call will let the LLM topic
classifier run on each sub-question. With the right topic per sub-query,
the planner's per-sub-query retrieval gathers more on-topic chunks; the
coherence gate stops misfiring or correctly abstains; some of the 14
currently-non-acc+ qids will flip to served_strong/acceptable.

**Plausibility:** very high. The trace event matches exactly the same
`topic_router.llm.skipped` shape that mis-routed parent queries during
phase 1. We have a working A/B framework (LLM provider toggle) to confirm.

**What might also be needed (don't pre-commit):**

* **H1a** — the planner's per-sub-query plan may also need to inherit the
  `conversation_state.normative_anchors` so follow-up sub-questions
  ("¿hay límite anual?", "¿cuánto cambia?") can use the parent's resolved
  articles as anchors.
* **H1b** — `_should_attempt_llm` is a separate gate. For very short
  sub-questions ("¿califican?") it may also short-circuit. Verify after
  passing the runtime config.

**Hypotheses to NOT chase first** (rule out only if H1 doesn't deliver):

* Coherence-gate calibration. The current `LIA_EVIDENCE_COHERENCE_GATE=enforce`
  is in place since 2026-04-25; phase 1 of this fix already showed it
  abstains correctly for low-evidence topics like `tarifas_renta_y_ttd`.
  Don't recalibrate unless the panel still fails AFTER H1.
* Vigencia v3 demotion. Phase 1 trace evidence shows it kept 23-24/24 chunks
  on every test query — it's not pruning aggressively. Skip.
* Corpus completeness. Phase 1 ruled this out; hybrid_search returned 24
  rows for every test qid.

---

## 3. The diagnostic + fix sequence (numbered, actionable)

Operate per `CLAUDE.md` "Fail Fast, Fix Fast" canon. **Read trace, change one
thing, verify, compare; do NOT batch multiple fixes.**

### Step 1 — Read the current trace for the 14 non-acc+ qids

Run dir: `evals/sme_validation_v1/runs/20260429T172422Z_gemini_primary_full/`.
The classifier file `classified.jsonl` lists every qid's class. The 14
non-acc+ qids are anything not `served_strong` or `served_acceptable`.

Per qid, extract `response.diagnostics.pipeline_trace.steps`. Look for the
`topic_router.llm.skipped` event and what topic the keyword fallback
landed on. Group qids by failure shape:

```python
# /tmp/triage_non_accplus.py — write this and run it
import json, sys
from pathlib import Path
from collections import defaultdict

RUN = Path("evals/sme_validation_v1/runs/20260429T172422Z_gemini_primary_full")
classified = {json.loads(l)["qid"]: json.loads(l) for l in (RUN / "classified.jsonl").open()}
non_accplus = [qid for qid, r in classified.items()
               if r["class"] not in ("served_strong", "served_acceptable")]

groups = defaultdict(list)
for qid in non_accplus:
    j = json.loads((RUN / f"{qid}.json").read_text())
    steps = ((j["response"].get("diagnostics") or {}).get("pipeline_trace") or {}).get("steps", [])
    skipped_count = sum(1 for s in steps if s["step"] == "topic_router.llm.skipped")
    fallback_topics = [s["details"].get("effective_topic")
                       for s in steps if s["step"] == "topic_router.keyword_fallback"]
    no_topic = sum(1 for s in steps if s["step"] == "topic_router.no_topic_detected")
    key = f"skipped={skipped_count} fallback={fallback_topics} no_topic={no_topic} class={classified[qid]['class']}"
    groups[key].append(qid)

for key, qids in sorted(groups.items(), key=lambda x: -len(x[1])):
    print(f"\n{key}  ({len(qids)} qids)")
    for q in qids: print(f"  {q}")
```

This tells you which qids are bottlenecked on the sub-query LLM-skipped
path vs other shapes (e.g. genuine `served_off_topic` from the parent
resolver, vs `refused` from the coherence gate).

### Step 2 — Make the surgical code change (H1 fix)

Edit `src/lia_graph/pipeline_d/orchestrator.py` at the sub-query loop
(currently around line 381). Change:

```python
sq_routing = _resolve(message=sq, requested_topic=None, pais=request.pais)
```

…to:

```python
sq_routing = _resolve(
    message=sq,
    requested_topic=None,
    pais=request.pais,
    runtime_config_path=runtime_config_path,
    conversation_state=request.conversation_state,
    preserve_requested_topic_as_secondary=False,
)
```

**Important context:**

* `runtime_config_path` is already a parameter of `run_pipeline_d` (line ~256
  in the same file). It's available in scope.
* `request.conversation_state` is an attribute of `PipelineCRequest` (built
  in `ui_chat_payload._build_pipeline_request`). It's available in scope.
* `preserve_requested_topic_as_secondary=False` matches what the parent
  passes when `requested_topic=None` (per `ui_chat_payload.py:386`).

This is a **single-line change** with a clear semantic: sub-queries get the
same LLM-resolution power as the parent.

### Step 3 — Re-run the §1.G panel

Server restart needed to pick up the code change (no env flag involved):

```bash
# Find and kill the dev server, restart cleanly:
pkill -KILL -f "python.*lia_graph\\|node.*dev-launcher\\|npm.*dev:staging" || true
sleep 4
nohup npm run dev:staging </dev/null > /tmp/devstaging.log 2>&1 &
disown
until curl -s -o /dev/null -w "%{http_code}" --max-time 2 http://127.0.0.1:8787/api/health 2>&1 | grep -q 200; do sleep 2; done

# Run the parallel panel against fresh server:
RUN_DIR=evals/sme_validation_v1/runs/$(date -u +%Y%m%dT%H%M%SZ)_subquery_llm_fix
mkdir -p "$RUN_DIR"
rm -f tracers_and_logs/logs/pipeline_trace.jsonl
PYTHONPATH=src:. uv run python scripts/eval/run_sme_parallel.py \
    --run-dir "$RUN_DIR" --workers 4 --timeout-seconds 240

# Classify:
PYTHONPATH=src:. uv run python scripts/eval/run_sme_validation.py --classify-only "$RUN_DIR"
```

Expected wall-time: ~5 min. Expected new acc+ count: **between 22 and 28**;
the H1 fix theoretically makes every fan-out sub-query LLM-resolved. The
exact lift depends on how many of the 14 non-acc+ qids have fan-out paths
where a sub-query topic was lost.

### Step 4 — Compare against current panel

```bash
PYTHONPATH=src:. uv run python /tmp/compare_runs.py "$RUN_DIR"
```

(The script at `/tmp/compare_runs.py` from phase 1 prints a side-by-side
acc+/per-class/per-qid table. If it's gone, write a new one — the
classified.jsonl format is stable.)

**Minimum success criterion (per the v3 plan):**
* `served_acceptable+ ≥ 24/36`
* `ok→zero regressions = 0` (zero qids that were acc+ in the
  04-29 Gemini-primary baseline regress to weak/off_topic/refused/error)

**Failure criterion**: if step 3 yields no improvement OR a regression,
DON'T patch on top — go back to step 1 with the new trace data and
re-evaluate H1a/H1b/coherence-gate calibration.

### Step 5 — Six-gate sign-off and commit

Per `CLAUDE.md` non-negotiable: every pipeline change passes the six gates.
Document each in the commit message:

1. **Idea**: thread `runtime_config_path` + `conversation_state` to
   sub-query topic resolution so the LLM classifier can run.
2. **Plan**: 1-line change at `orchestrator.py:381`. Reversible.
3. **Measurable criterion**: §1.G panel ≥24/36 acc+, 0 regressions.
4. **Test plan**: parallel SME runner against the 36 questions with the
   change as the only variable. Engineer launches; classifier scores;
   operator (you, the agent) compares.
5. **Greenlight**: technical pass + spot-check 3 of the qids that flipped
   from non-acc+ to acc+ to confirm substantive (not boilerplate) answers.
6. **Refine-or-discard**: if criterion not met, either fall back to H1a/H1b
   or explicitly mark the change discarded with the new run dir as
   evidence. Don't silently roll back.

Commit message format (per repo style, see `git log --oneline`):

```
fix_v1 phase 2 — thread runtime_config_path through sub-query routing

Step from 22/36 to <new> acc+ on §1.G panel.
Run dir: <RUN_DIR>.
[gate-by-gate breakdown]

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

## 4. What you must NOT do

1. **Don't change `provider_order` again.** Phase 1 just fixed it; the
   chat path needs Gemini-flash first. If you need DeepSeek anywhere,
   use `LIA_VIGENCIA_PROVIDER` (already in place for canonicalizer).
2. **Don't lower the 24/36 gate.** If the panel passes 23/36 with all 3
   coherence-gate refusals being honest, document the exception per qid;
   don't move the bar.
3. **Don't disable the v6 coherence gate** (`LIA_EVIDENCE_COHERENCE_GATE=enforce`).
   It's correctly refusing low-evidence queries; refusing is honest.
   If you suspect it's mis-firing, run the §6 step 4 toggle test from
   the original (now archived) fix_v1 problem statement.
4. **Don't batch multiple fixes.** This doc is scoped to H1 only. If you
   discover H1a/H1b are needed, ship them as separate commits with their
   own runs and gate sign-offs.
5. **Don't commit without re-running the full panel.** The classifier on
   3 qids is misleading; the panel is the gate.
6. **Don't mutate the canonicalizer launch scripts** in
   `scripts/canonicalizer/` or `scripts/cloud_promotion/`. Those set
   `LIA_VIGENCIA_PROVIDER` explicitly and are correct.

---

## 5. Where the trace and tooling already are

* **Deep trace package:** `tracers_and_logs/`. Already wired into chat path.
  Every served chat appends rows to `tracers_and_logs/logs/pipeline_trace.jsonl`
  AND attaches `response.diagnostics.pipeline_trace.steps[*]` to the
  served response. Trace events you care about for this work:
  * `topic_router.entry` — every resolve_chat_topic call.
  * `topic_router.llm.attempt` / `.success` / `.exception` /
    `.unsupported_topic` / `.low_confidence` / `.no_adapter` — LLM path
    instrumentation.
  * `topic_router.llm.skipped` — **the smoking gun for this work**.
    Fires when `runtime_config_path is None` OR `_should_attempt_llm` is
    False. Today, every sub-query hits this.
  * `topic_router.keyword_fallback` / `topic_router.no_topic_detected` /
    `topic_router.prior_state_fallback` — the three downstream paths after
    the LLM is skipped.
  * `topic_router.subquery_resolved` — orchestrator-side per-sub-query
    record (parent topic, secondary topics, confidence, mode, reason).

* **Eval runner:** `scripts/eval/run_sme_parallel.py` (4 workers, ~5 min
  wall-time on cloud staging).

* **Classifier:** `scripts/eval/run_sme_validation.py --classify-only <dir>`.
  Writes `classified.jsonl` and prints the acc+/weak/refused/error counts.

* **Comparison harness:** the phase-1 script at `/tmp/compare_runs.py`
  (may need to be re-written; format is stable). Compares any new run dir
  against the 04-27 baseline + 04-29 Gemini-primary anchor.

* **Anchor runs to compare against:**
  * 04-27 baseline (Gemini-flash, pre-DeepSeek-flip): 21/36 acc+
    (`evals/sme_validation_v1/runs/20260427T021512Z_activity1_vigencia_filter/`)
  * 04-29 DeepSeek-primary (the regression): 8/36 acc+
    (`evals/sme_validation_v1/runs/20260429T153845Z_post_p1_v3/`)
  * 04-29 Gemini-primary (current; phase 1 fix landed): 22/36 acc+
    (`evals/sme_validation_v1/runs/20260429T172422Z_gemini_primary_full/`)

---

## 6. State of the world right now (2026-04-29 ~12:35 PM Bogotá)

* `config/llm_runtime.json` `provider_order` = `[gemini-flash, gemini-pro,
  deepseek-v4-flash, deepseek-v4-pro]`. Don't change.
* Latest commit on `main`: `173eb9b fix_v1 — restore chat to 22/36 acc+ by
  flipping LLM provider order`. Pushed to GitHub.
* `tracers_and_logs/` package is live in the served runtime. Every served
  chat writes one trace row per stage. PII-safe; whitelisted in the public
  response filter.
* The dev server (`npm run dev:staging`) is hitting cloud Supabase + cloud
  Falkor. Standard env. No special overrides in place.
* No outstanding migrations. Cloud is in-sync with `supabase/migrations/`.
* The §1.G panel runs in ~5 min wall-time at 4 workers.

---

## 7. Tackle order (recommended)

1. Step 1 (triage script) — 10 minutes. **Diagnose before intervene.**
   Confirm the sub-query LLM-skipped pattern is the dominant failure
   shape across the 14 non-acc+ qids.
2. If H1 looks right → Steps 2-5 — 30 minutes total.
3. If H1 alone gets you to 24+/36 → ship + commit + push.
4. If H1 lands at 23/36 → spot-check the one qid that's still missing
   acc+; consider H1a (conversation_state.normative_anchors propagation)
   as a follow-up but ship the H1 win first.
5. If H1 lands below 22/36 (regression) → fall back, re-trace, write up
   what you saw, and either propose H1b/H1a or escalate.

---

## 8. Minimum information you need from the operator (none)

This hand-off is fully self-contained. Don't ask the operator to clarify
unless:

* The §1.G panel cannot complete (e.g. cloud outage, port conflict). Then
  surface the exact failure with logs.
* Your trace data shows H1 is wrong (LLM is being attempted on sub-queries
  but failing differently). Then write the diagnosis up before proposing
  another fix.
* You're about to commit a change that affects the canonicalizer LLM
  pinning (Don't. Per §4 rule 6.)

---

## 9. After you ship phase 2

Update this file (`docs/re-engineer/fix/fix_v1.md`) to mark phase 2 closed
and either close out fix_v1 entirely or set up phase 3 if a residual gap
remains. Mirror the structure of `fix_v1_diagnosis.md` for the close-out.

If you discover that the sub-query path also needs `conversation_state`
propagation OR that H1a (normative_anchors) is required, document each as
its own phase. The bar for declaring fix_v1 done is the §1.G panel
sustaining ≥24/36 acc+ with zero ok→zero regressions across at least one
follow-up panel run a day or more later.

---

*Drafted 2026-04-29 ~12:35 PM Bogotá by claude-opus-4-7 immediately after
phase 1 closed at 22/36 acc+. The trace evidence cited in §1 is in
`evals/sme_validation_v1/runs/20260429T172422Z_gemini_primary_full/<qid>.json
.response.diagnostics.pipeline_trace.steps[*]` and in
`tracers_and_logs/logs/pipeline_trace.jsonl` (which gets overwritten on
each new request, so re-capture if you need a specific trace).*
