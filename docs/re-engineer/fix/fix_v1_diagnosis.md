# fix_v1_diagnosis.md — root cause of the §1.G 8/36 regression

> **Drafted 2026-04-29 ~12:30 PM Bogotá** by claude-opus-4-7. This closes
> the diagnostic phase the §6 hand-off asked for. **One sentence:** the
> regression is caused by a single change in `config/llm_runtime.json`
> that put DeepSeek-v4-pro at the head of the provider chain; that
> provider's adapter raises `RuntimeError` on every chat topic-classifier
> call because the v4-pro reasoning model returns an empty `content`
> field. The topic resolver swallows the exception silently and falls
> through to the lexical keyword fallback, which classifies most queries
> as the parent topic `declaracion_renta`. Hypotheses H2 (vigencia
> demotion), H3 (corpus completeness), and H4 (coherence gate) are
> **NOT** the cause.

---

## 0. TL;DR

* Root cause: **`DeepSeek-v4-pro` is a reasoning model that returns
  `reasoning_content` but often empty `message.content`; the adapter
  in `src/lia_graph/llm_runtime.py:198` raises
  `RuntimeError("DeepSeek response missing message content.")` on every
  topic-classifier call.**
* The topic resolver (`_classify_topic_with_llm`,
  `src/lia_graph/topic_router.py:783`) wraps the call in `try/except
  Exception: return None`, so the exception is invisible from the
  outside.
* The keyword-fallback path at `topic_router.py:1019` then fires and
  picks the parent topic (typically `declaracion_renta`) because
  multi-domain SME queries don't have a dominant lexical signal.
* The cure is to flip provider order so Gemini wins for chat
  (canonicalizer can keep DeepSeek via `LIA_VIGENCIA_PROVIDER`).
* Validation: 3-Q A/B isolation test at the same git SHA shows
  **3/3 effective_topic regressions disappear** when Gemini is primary,
  and chat latency drops 60-93%.

---

## 1. How we got here

We arrived at this diagnosis by:

1. Adding a **deep-trace collector** at `tracers_and_logs/pipeline_trace.py`
   that writes one JSONL line per stage to
   `tracers_and_logs/logs/pipeline_trace.jsonl`. Stages instrumented:
   topic resolution (LLM-deferral path with all six silent-None branches),
   planner, retriever (hybrid_search + anchor articles + vigencia v3
   demotion), reranker, coherence gate, citation allow-list, LLM polish.
2. Whitelisting `pipeline_trace` in
   `src/lia_graph/ui_chat_payload.filter_diagnostics_for_public_response`
   so the trace also lands in `response.diagnostics["pipeline_trace"]`
   for the eval harness.
3. Running the 3 representative regressed qids
   (`beneficio_auditoria_P2`, `tarifas_renta_y_ttd_P2`,
   `firmeza_declaraciones_P2`) per fix_v1 §6 step 1 against the live
   `npm run dev:staging` server. Run dir:
   `evals/sme_validation_v1/runs/20260429T170826Z_fix_v1_trace/`.
4. **Identifying the smoking-gun trace event**:
   `topic_router.llm.exception status=error
    error="RuntimeError('DeepSeek response missing message content.')"`,
   firing 6.1-6.9 seconds into every single one of the 3 chat requests.
5. Running an A/B isolation: re-ordered `config/llm_runtime.json` to put
   `gemini-flash` first, restarted the dev server, re-ran the same 3
   qids. Run dir:
   `evals/sme_validation_v1/runs/20260429T171740Z_fix_v1_gemini_first/`.

The instrumentation followed the operator's "fail fast, fix fast"
canon: hypotheses up front, test, read trace, fix or refine, re-test,
compare.

---

## 2. The trace evidence — DeepSeek primary

Per-qid step list (filtered to the topic_router decision path; full
traces in `tracers_and_logs/logs/pipeline_trace.jsonl` and in
`response.diagnostics.pipeline_trace.steps[*]`):

```
=== beneficio_auditoria_P2 (59.0s total) ===
   848.6ms  topic_router.entry                  status=info
   875.4ms  topic_router.rule_route.miss        status=info
   898.8ms  topic_router.llm.attempt            status=info   adapter=DeepSeekChatAdapter model=deepseek-v4-pro
  7306.4ms  topic_router.llm.exception          status=error  error=RuntimeError('DeepSeek response missing message content.')
  7308.6ms  topic_router.llm_route.miss         status=fallback
  7336.1ms  topic_router.keyword_fallback       status=fallback  effective_topic=declaracion_renta confidence=...
```

**The same shape repeats for `tarifas_renta_y_ttd_P2` (LLM exception at
6.3s) and `firmeza_declaraciones_P2` (LLM exception at 7.1s).**
Per-call elapsed time reported in the trace's `details.elapsed_ms_call`
field is consistently 6.1-7.0s, well under the 8s timeout.

The other instrumented stages on the same runs are clean — they
**rule out the other hypotheses**:

* **H2 (vigencia gate over-aggressive)** — `retriever.vigencia_v3.applied`
  reports `chunks_seen=24, chunks_kept=23-24, chunks_dropped=0-1,
  chunks_demoted=0-1`. The v3 gate is barely doing anything. **Not the cause.**
* **H3 (corpus completeness gap)** — `retriever.hybrid_search.out`
  returns 24 rows for every qid; `retriever.anchor_articles` and
  `retriever.merge_anchors` show evidence is being gathered. The gap
  is downstream of retrieval, not in the corpus. **Not the cause.**
* **H4 (coherence gate firing harder)** — `coherence.detect` returns
  `misaligned=False` for the misrouted DeepSeek runs (because retrieval
  was forced to a parent topic that *does* match the parent-bucket
  evidence). The gate isn't firing. **Not the cause.**

---

## 3. The A/B test — Gemini-flash primary

Same git SHA. Only change: `config/llm_runtime.json` `provider_order`
flipped from `[deepseek-v4-pro, deepseek-v4-flash, gemini-pro,
gemini-flash]` to `[gemini-flash, gemini-pro, deepseek-v4-flash,
deepseek-v4-pro]`. Server restarted clean. Same 3 qids.

| qid | effective_topic (DeepSeek) | effective_topic (Gemini) | total latency Δ |
|---|---|---|---|
| beneficio_auditoria_P2 | `declaracion_renta` ❌ | **`beneficio_auditoria`** ✅ | 59.0s → 23.1s |
| tarifas_renta_y_ttd_P2 | `declaracion_renta` ❌ | **`tarifas_renta_y_ttd`** ✅ | 129.0s → 8.7s |
| firmeza_declaraciones_P2 | `declaracion_renta` ❌ | **`firmeza_declaraciones`** ✅ | 138.3s → 20.0s |

Trace evidence under Gemini-primary:

```
=== tarifas_renta_y_ttd_P2 (8.7s total) ===
   200.4ms  topic_router.entry              status=info
   247.1ms  topic_router.llm.attempt        status=info   adapter=GeminiChatAdapter model=gemini-2.5-flash
  1970.9ms  topic_router.llm.success        status=ok     llm_primary_topic=tarifas_renta_y_ttd  confidence=0.9
  1971.3ms  topic_router.llm_route.return   status=ok
  5714.0ms  coherence.abstention            status=fallback   <-- v6 abstention path firing as expected
```

Bonus evidence: under Gemini-flash, `tarifas_renta_y_ttd_P2` correctly
reaches the **coherence.abstention** path (the v6 `evidence_coherence_refusal`
mode the 2026-04-27 baseline used). That confirms the broader pipeline
behaves correctly once the topic is routed correctly.

The `topic_adjustment_reason` strings under Gemini-primary match the
2026-04-27 baseline strings character-for-character — substantive LLM-style
explanations like *"La consulta pregunta explícitamente sobre el
beneficio de auditoría y sus condiciones de aplicación..."*. Under
DeepSeek-primary, all three regressed qids carried
`topic_adjustment_reason="fallback:auto_detected_from_keywords"`, which
was already a known smell from the §6 step 1 diff.

---

## 4. The exact code surface

Three lines tell the whole story:

* **`src/lia_graph/llm_runtime.py:197-198`** —
  ```python
  if not isinstance(content, str) or not content.strip():
      raise RuntimeError("DeepSeek response missing message content.")
  ```
  When DeepSeek-v4-pro (a reasoning model) returns
  `{"choices":[{"message":{"reasoning_content":"<chain-of-thought...>",
  "content":""}}]}`, this branch trips. The adapter does not consult
  `reasoning_content` as a fallback.

* **`src/lia_graph/topic_router.py:783`** —
  ```python
  except Exception:
      return None
  ```
  Swallows the RuntimeError. No log, no diagnostic — until today's
  trace instrumentation, this was an invisible silent failure.

* **`src/lia_graph/topic_router.py:1019-1037`** — when LLM returns None
  AND `requested_topic` is None AND lexical scoring finds anything at
  all, the keyword fallback fires and emits
  `reason="fallback:auto_detected_from_keywords"`. For the regressed
  qids, the dominant lexical signal points at the parent topic
  (`declaracion_renta`) because the queries mention SAS, ingresos,
  declaración, etc.

---

## 5. Why this only started today

Per `docs/re-engineer/fix/fix_v1.md` §1, the changes that landed
between the 2026-04-27 21/36 baseline and today's 8/36 run were five
migrations and a corpus-promotion. **None of those touched the chat
LLM provider chain.**

The actual change is in `config/llm_runtime.json` — the
`provider_order` was flipped to put DeepSeek first **at some point in
the canonicalizer-cycle work** (`53ce969 chore: sync pending runtime
artifacts, env/config updates`). The intent was operator-driven:
DeepSeek-v4-pro is on a 75%-discount window through 2026-05-05 and was
being used heavily by the canonicalizer cascade. The chat path
inherited the same primary because the config is shared.

The 2026-04-27 baseline ran with `gemini-2.5-flash` as the polish
adapter (visible in the prior eval run's `llm_runtime.adapter_class`
field). The 2026-04-29 run shows `DeepSeekChatAdapter` for both topic
classifier and polish steps. That swap is the single new variable.

---

## 6. Proposed fix shape (NOT yet committed for prod)

Three options, in increasing order of scope:

### Option A — Reorder providers for chat (smallest, narrowest)

Edit `config/llm_runtime.json` to put `gemini-flash` first. The
canonicalizer already explicitly forces its provider via
`LIA_VIGENCIA_PROVIDER=deepseek-v4-flash` (per the file's `_comment`),
so this only flips the chat path. Risk: the canonicalizer would also
default to Gemini-flash if it ever runs WITHOUT the env override —
which today's launch scripts always supply, but that's an implicit
contract worth tightening in the same PR.

### Option B — Fix the DeepSeek adapter to handle reasoning-mode responses

In `src/lia_graph/llm_runtime.py`, when `content` is empty AND
`reasoning_content` is non-empty, return `reasoning_content` (or a
stripped/parsed form). This makes DeepSeek-v4-pro usable for
non-reasoning prompts like the topic classifier without forcing it into
empty-content land. Risk: surfaces chain-of-thought into the response
body in cases where we don't want it; needs care.

### Option C — Per-stage provider override

Add `LIA_CHAT_TOPIC_PROVIDER`, `LIA_CHAT_POLISH_PROVIDER`,
`LIA_CHAT_PLAN_PROVIDER` env knobs and have each stage call
`resolve_llm_adapter(requested_provider=...)` accordingly. Decouples
chat LLM choice from canonicalizer LLM choice cleanly. Bigger change;
right long-term shape.

**Recommendation**: Option A immediately (one-line config change,
fully reversible, restores 04-27 behavior). Option C as a follow-up
when there's headroom.

---

## 7. Six-gate criteria for the proposed fix

Per `CLAUDE.md` "Idea vs verified improvement":

1. **Idea**: chat path uses Gemini-flash for the LLM topic classifier
   and polish step; canonicalizer keeps DeepSeek via explicit override.
2. **Plan**: edit `config/llm_runtime.json` `provider_order` to
   `[gemini-flash, gemini-pro, deepseek-v4-flash, deepseek-v4-pro]`.
   Single-line change in one file. Fully reversible by reverting.
3. **Measurable success criterion**: `§1.G 36-question SME panel
   reaches ≥ 24/36 served_acceptable+ with zero ok→zero regressions`,
   matching the v3 plan's gate. Stretch: recover the 21/36 baseline,
   then exceed it.
4. **Test plan**: re-run the parallel SME runner against the same 36
   questions on the same git SHA, with the config flip as the only
   variable. Engineer launches; eval harness scores; SME (operator)
   spot-checks the 13 previously-regressed qids for substantive
   answers. Decision rule: ≥24/36 acc+ AND zero ok→zero regressions.
5. **Greenlight**: technical pass (24/36) + operator's qualitative
   review of the 13 previously-regressed qids confirms substantive
   answers, not boilerplate "Cobertura pendiente".
6. **Refine-or-discard**: if the panel falls short, three follow-ups
   in order: (a) check whether the DeepSeek polish step was ALSO
   contributing to regressions (it took 35-115s in our traces; very
   slow even when it succeeded); (b) inspect the sub-query LLM-skipped
   path which today fires `topic_router.llm.skipped` for fan-out
   sub-queries, possibly losing topic resolution for the secondary
   ¿…?; (c) consider Option B/C above.

---

## 8. State of the repo right now

I left the config in the **A/B test state**: `gemini-flash` first.
The original DeepSeek-first config is backed up at
`/tmp/llm_runtime_deepseek_primary.json.bak`. **The operator can
choose to keep this state, revert it, or commit it as the persistent
fix once the §1.G panel re-runs to ≥ 24/36.**

The instrumentation (`tracers_and_logs/`) is now part of the served
runtime. It survives debug_mode being off (the trace is PII-safe by
design — no chunk text, no answer text, only stage names + counts +
truncated decision details). It can stay in production without harm.

---

## 9. Files touched in this diagnosis cycle

* **New:** `tracers_and_logs/__init__.py`,
  `tracers_and_logs/pipeline_trace.py`,
  `tracers_and_logs/README.md`,
  `tracers_and_logs/logs/.gitkeep`.
* **Edit:** `.gitignore` (ignore `tracers_and_logs/logs/*.jsonl`).
* **Edit:** `src/lia_graph/pipeline_d/orchestrator.py` (trace install at
  entry, step events at every stage, snapshot into diagnostics, finish
  on each return path).
* **Edit:** `src/lia_graph/topic_router.py` (deep-trace at every silent
  return-None branch in `_classify_topic_with_llm`, plus full
  decision-path coverage in `resolve_chat_topic`).
* **Edit:** `src/lia_graph/pipeline_d/retriever_supabase.py` (trace
  events around `hybrid_search`, anchor merge, vigencia_v3 demotion,
  client-side subtopic boost recovery).
* **Edit:** `src/lia_graph/ui_chat_payload.py` (install trace at chat
  entry so topic_router events land in the same trace; whitelist
  `pipeline_trace` in `filter_diagnostics_for_public_response`).
* **A/B-test only (NOT yet committed):**
  `config/llm_runtime.json` `provider_order` flipped to put
  `gemini-flash` first.

---

## 10. Next concrete steps

In order, smallest first:

1. **Re-run the §1.G 36-question SME panel against the Gemini-primary
   config** (parallel runner, `--workers 4`, ~10 min). If it lands
   ≥24/36 acc+ and recovers the 21/36 baseline, commit the config
   flip as the durable fix.
2. **Investigate the slow polish step.** Even with Gemini, polish took
   16-20s on the 3 worst Qs; under DeepSeek it took 35-115s. There may
   be a separate calibration issue with `polish_graph_native_answer`'s
   prompt size or temperature.
3. **Sub-query LLM-skipped trace.** The decomposer's fan-out
   sub-queries hit `topic_router.llm.skipped`
   (`_should_attempt_llm=False`) and fall to keyword fallback. For
   multi-question parents this means the SECOND ¿…? often gets the
   wrong topic. Worth a separate diagnostic cycle.
4. **Re-promote the 78 P6-recovered veredictos to cloud** (per fix_v1
   §8.1, deferred until diagnosis lands — now done).
5. **Commit the trace instrumentation as a durable observability
   contract.** Once the operator approves the shape, the README in
   `tracers_and_logs/` becomes the canonical doc for retrieval-stage
   debugging.

---

*Drafted 2026-04-29 ~12:30 PM Bogotá by claude-opus-4-7 immediately
after the A/B test landed clean. All trace data is in
`tracers_and_logs/logs/pipeline_trace.jsonl` and the two run dirs
named in §1. The smoking-gun event is
`topic_router.llm.exception` with
`error=RuntimeError('DeepSeek response missing message content.')`.*
