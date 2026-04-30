# Chat-runtime hardening — fix_v1 → fix_v6 distilled

> **Captured 2026-04-29 → 2026-04-30** at the close of a single-day chat-runtime ship that took the §1.G 36-Q SME panel from a fresh **8/36 acc+ regression** through to **32 strong / 4 acc / 0 weak / 36 acc+** under the post-fix_v3 fairer grader. Six fix-cycles, ~12 hours wall, 7 commits on `main`. Anchor run: `evals/sme_validation_v1/runs/20260430T000527Z_fix_v5_phase6b_rerun/`. Full close-records: `docs/re-engineer/fix/{fix_v1_diagnosis,fix_v1,fix_v2,fix_v3,fix_v4,fix_v5,fix_v6}.md`.
>
> This doc is the consolidated learning index. Each row is one distinct lesson, the incident that created it, the rule it generalizes to, and where the code lives. Read this file once; reach into the close-records only when you need the gate-by-gate mechanics.

## Headline metrics

| Cycle | Panel result | Δ | Anti-pattern surfaced |
|---|---|---|---|
| pre-fix_v1 baseline | 21/36 acc+ | — | — |
| 2026-04-29 morning regression | **8/36** | −13 | DeepSeek-v4-pro reasoning model on strict-JSON topic-classifier prompt |
| fix_v1 phase 1 (provider revert + trace) | 22/36 | +14 | `try/except: return None` swallows LLM failures invisibly |
| fix_v1 phase 2 (sub-Q LLM threading) | 16/36 — DISCARDED | — | "Wider LLM coverage = better routing" was wrong |
| fix_v2 phase 3 (5-signal primary classifier) | 29/36 | +7 | One-signal "primary evidence" definition kept failing broad-style queries |
| fix_v3 phase 4 (polish prompt + splitter + grader) | 34/36 (new grader) | +5 | Markdown-shaped chunks collapse to single bullets; grader unfair to substantive on-adjacent answers |
| fix_v3 slug-cleanup attempt | 36/36 acc+ but **23 strong (−5)** — DISCARDED | — | **Polish-prompt rule additions tilt the LLM globally** |
| fix_v4 phase 5 (polish trigger + empty-section fallback) | **36/36** | +2 | LLM-judged trigger conditions ("is this multi-step?") are unreliable; trigger on observable structural counts instead |
| fix_v5 phase 6a (heading reject) | 36/36, 29 strong | +1 strong | Practica/expertos chunk headers leak through markdown-aware splitter |
| fix_v5 phase 6b (sub-Q parent-topic carry-over) | **36/36, 32 strong** | +3 strong | Sub-Q topic drift on `mode == "fallback"` resolves; multi-domain hits must stay respected |
| fix_v5 phase 6c (numeric directive) | −1 strong — DISCARDED same-commit | — | **Polish-prompt blast radius pattern recurred** (2nd incident) |
| fix_v6 (Norms catalog Supabase→Falkor projection) | not regression-touched | — | Canonicalizer Supabase writes don't auto-project to Falkor |
| fix_v7a (truncated-tail filter, L13) | not yet panel-measured | — | Auto-period on mid-word abbreviation tails surfaces "fra." bullets |
| fix_v7b (canonical question shapes, L14) | not yet panel-measured | — | L8 parent-inheritance steamrolls correct sub-Q classifications when they have no own-keyword-rule hit |

Of the 11 distinct interventions attempted, **3 were discarded** (sub-Q LLM threading, slug-cleanup, numeric directive) and 8 landed. The discards taught more than several of the wins.

## L1 — Reasoning models ≠ structured-output models

**Incident.** `provider_order=[deepseek-v4-pro, ...]` flipped chat from 21 → 8/36 acc+ overnight. DeepSeek-v4-pro returns `reasoning_content` (chain-of-thought) plus empty `message.content` on the strict-JSON topic-classifier prompt; `llm_runtime.py:198` raises `RuntimeError("DeepSeek response missing message content.")`; `topic_router._classify_topic_with_llm` swallows it via `try/except: return None`; keyword fallback mis-routes everything to the parent topic.

**Rule.** Per-prompt provider selection: chat (low-latency, schema-bound) vs canonicalizer (long-context, batch). The `config/llm_runtime.json` default serves chat; canonicalizer pins `LIA_VIGENCIA_PROVIDER=deepseek-v4-flash` explicitly in every launcher script. Mandatory: any new canonicalizer entry-point sets the env in the launcher, never relies on the default.

**Detection.** Run `scripts/eval/run_sme_parallel.py --workers 4` (~5 min) on every `config/llm_runtime.json` change before merging. Trace `topic_router.llm.attempt → topic_router.llm.success` latency on chat — > 6 s consistently means the model is wrong for the prompt shape even if it parses.

**Code.** `config/llm_runtime.json`, `src/lia_graph/llm_runtime.py:198`, `src/lia_graph/topic_router.py:783`, `scripts/canonicalizer/launch_batch.sh`, `scripts/cloud_promotion/run.sh`.

## L2 — Silent exceptions need trace events at the swallow site

**Incident.** L1's RuntimeError was invisible until we added `tracers_and_logs/pipeline_trace.py` and instrumented every `return None` branch in `_classify_topic_with_llm`. The trace surfaced the smoking gun in 7 min on a 3-Q probe; a week of empirical A/B testing wouldn't have isolated it.

**Rule.** Any code path that swallows exceptions silently (`try/except: return None`, `try/except: pass`, defensive default-on-error) gets a trace event at the swallow site naming the swallowed exception type and the fall-through path it took. PII-safe by design — no chunk text, no answer text, only stage names + counts + truncated decision details.

**Implementation.** `tracers_and_logs/pipeline_trace.py` is a context-local collector that writes one JSONL line per pipeline stage to `tracers_and_logs/logs/pipeline_trace.jsonl` AND attaches the snapshot to `response.diagnostics["pipeline_trace"]`. Whitelisted in `ui_chat_payload.filter_diagnostics_for_public_response` so eval traces survive the public-response strip. Read with `jq` against the JSONL or directly in `<run>/<qid>.json::response.diagnostics.pipeline_trace.steps[*]`.

**Highest-signal events** (out of ~30): `topic_router.llm.{attempt,success,exception,skipped}`, `topic_router.subquery_inherited_parent`, `retriever.evidence` (carries `primary_count` / `connected_count` / `support_count` / `planner_query_mode`), `coherence.detect.reason`, `polish.applied.polish_changed`.

**Anti-pattern.** Don't ship a defensive default-on-error without a trace event. The cost of one log line per swallow site is far less than one panel-debug session.

## L3 — Five-signal primary-evidence model (vs single-signal anchor-only)

**Incident.** Pre-fix_v2, `_classify_article_rows` only promoted a chunk to primary on `article_key ∈ explicit_set` (planner anchor). For "broad" questions where the planner emitted no articles (`general_graph_research`, `plan_anchor_count=0`), `primary_count` was structurally always 0 and the v6 coherence gate refused every such question. 9 of 36 §1.G qids refused on this. The fix shipped 5 SME-curated structural signals.

**Rule.** "Primary evidence" is a **classification problem with multiple sufficient conditions**, not a single-key lookup. The five signals (any sufficient):

| # | Signal | Source of truth |
|---|---|---|
| 1 | Planner anchor — `article_key ∈ explicit_set` | `plan.entry_points[kind=article]` |
| 2 | Chunk-level topic — `chunk.topic == router_topic` | `document_chunks.topic` |
| 3 | Document-level topic — `document.topic == router_topic` | `documents.topic` |
| 4 | Compatible doc-topics — `document.topic ∈ compatible_doc_topics[router_topic]` | `config/compatible_doc_topics.json` |
| 5 | Article rescue — `article_id ∈ rescue_index[router_topic]` | `config/article_secondary_topics.json` |

Items promoted via signals (2)–(5) get `secondary_topics=(router_topic,)` so the misalignment detector accepts them via `secondary_topic_match` without falling back to the lexical scorer (which gives false-positive misalignment between sibling sub-topics like `tarifas_renta_y_ttd` vs `declaracion_renta`).

**Recall-side companion.** `_fetch_anchor_article_rows` was extended to fetch SME-curated rescue articles when no explicit anchors exist (cap 10, synthetic `rrf_score=0.95`). Without this, FTS+vector ranking buries rescue articles below umbrella-topic chunks (e.g. art 689-3 for `beneficio_auditoria`).

**Result.** §1.G 22 → 29/36 acc+; 9 refusals → 0; 8 newly-passing qids verified end-to-end. Generalizes across all 89 router topics — signals (3) and (4) carry the bulk for non-curated topics, signal (5) catches the curated long tail.

**Curation discipline.** `config/article_secondary_topics.json` and `config/compatible_doc_topics.json` are SME-curated. Don't add entries on a single failure; require the SME to confirm the adjacency. Sync to Falkor with `scripts/ingestion/sync_article_secondary_topics_to_falkor.py`.

**Code.** `src/lia_graph/pipeline_d/retriever_supabase.py::_classify_article_rows`, `_fetch_anchor_article_rows`, `_load_article_topic_index`. Close-record: `docs/re-engineer/fix/fix_v2.md` §A.

## L4 — Polish-prompt blast radius is the master anti-pattern

**Incidents (2 in this campaign).** Both attempted to fix LLM-emitted artifacts by adding rules to the polish prompt. Both regressed unrelated qids. Both reverted same-day.

| Incident | Intent | Result |
|---|---|---|
| Slug-cleanup (between fix_v3 and fix_v5) | Suppress `(art. paso-a-paso-pr-ctico ET)` template leaks via prompt rule | 36/36 acc+ but **23 strong (−5)**; 0 compensating gains |
| fix_v5 phase 6c numeric directive | Force calc on numeric questions ("$120M × 19% = $22.8M") via prompt rule | −1 strong (`beneficio_auditoria_P1` flipped strong → acc); 0 numeric targets flipped |

**Mechanism.** Polish-prompt rule additions tilt the LLM **globally**: even with a narrow trigger ("if numeric tokens in question"), the additional clause makes the LLM more conservative across every answer it polishes. The targeted gain is small; the un-targeted demotion is large. The LLM doesn't have a "narrow rule" mental model — it has a single prompt that biases its entire output distribution.

**Rule.** **Don't add more rules to `answer_llm_polish._build_polish_prompt` to suppress LLM-emitted artifacts.** Use renderer-layer deterministic fixes instead:

| Artifact class | Right layer | Example |
|---|---|---|
| Slug-shaped article anchors | Renderer regex strip | `answer_inline_anchors._anchor_label_for_item` returns `""` when neither `_ARTICLE_NUMBER_RX` nor `_TITLE_ARTICLE_RX` matches (fix_v3 phase 4 Route B) |
| Markdown headings as bullet text | Splitter post-cleanup rejection | `answer_support._HEADING_REJECT_PATTERNS` (fix_v5 phase 6a) |
| Stub-shaped sections | Synthesis-layer fallback | `answer_first_bubble.compose_first_bubble_answer` empty-section fallback (fix_v4 phase 5 Route B; see L6) |
| Numeric calc on numeric questions | Defer to fix_v6+ — needs a separate prompt step or post-polish numeric extractor, NOT a polish-prompt clause |

**Existing polish-prompt clauses that ARE keep-state.**

- **REGLA DE EXPANSIÓN** (fix_v3 phase 4 added; fix_v4 phase 5 Route A replaced its trigger): expand single-bullet sections when there are ≥2 anchor articles or ≥3 support docs in the evidence. Trigger is **structural** (counts), not LLM-judged. See L5.
- **No-invention guardrail** (mandatory, never weaken): "no inventés normas, artículos, ni cifras que no estén en la evidencia abajo o en el borrador. Si la evidencia no alcanza para 2-3 bullets reales, dejá el bullet original solo." Both gate-3 spot-checks across fix_v3/v4/v5 confirmed zero invented norms in any flipped qid.

The two existing clauses survived because they enable expansion (additive behavior the LLM was already capable of); they don't suppress artifacts (subtractive behavior the LLM has to learn from prompt language).

**Detection.** Diff `served_strong` counts before/after any polish-prompt edit on the §1.G panel. The slug-cleanup discard regressed strong by 5 with 36/36 acc+ held — the acc+ count was deceptively flat. **`served_strong` is the early-warning metric for polish blast radius**, not `acc+`.

## L5 — Structural triggers beat LLM-judged triggers

**Incident.** fix_v3 phase 4 polish-prompt expansion clause initially triggered on "if any section has only one bullet AND the question requires multi-step operational guidance." `regimen_cambiario_P1` (a yes/no-shaped question with 137 chars of evidence) refused to expand because the LLM judged "yes/no" as binary, not multi-step. The right answer was multi-step (yes + legal framework + steps + consequences) but the LLM couldn't read the evidence's potential through the trigger condition.

**Rule.** **Trigger conditions for prompt clauses should be observable structural counts, not LLM judgments about meta-properties of the question.** fix_v4 phase 5 Route A replaced "Y la pregunta requiere guía operativa multi-paso" with "Y hay al menos 2 ARTÍCULOS ANCLA o 3 DOCUMENTOS DE SOPORTE en la evidencia abajo." Same guardrail, structural trigger, panel 34 → 35/36.

| Property | LLM-judged | Structural |
|---|---|---|
| Reliability | Variable per question framing | Deterministic |
| Explainability | "The LLM thought..." | "There were N articles" |
| Test coverage | Hard (need broad question set) | Trivial (count assertions) |
| Iteration cost | Each prompt edit needs full panel | Each edit is a unit-test diff |

**Generalizes to.** Any prompt clause that says "if X, do Y" where X is meta-cognitive ("if the question is technical", "if the user needs a calculation", "if the answer is complete enough"). Replace with observable counts of evidence, conditions on the draft template, or pre-computed signals from upstream.

**Code.** `src/lia_graph/pipeline_d/answer_llm_polish.py::_build_polish_prompt`. Close-record: `docs/re-engineer/fix/fix_v4.md` §11.

## L6 — Question-reformulation shape is the most reliable expansion path

**Incident.** fix_v4 phase 5 Route B diagnosis: `regimen_sancionatorio_extemporaneidad_P2` had `primary_count=3, primary_on_topic, polish_changed=False`, 239-char single-section template. The synthesis builder emitted only `**Riesgos y condiciones**` because `recommendations` and `procedure` came back empty from the practical-enrichment extraction; only `precautions` was populated. Polish faithfully preserved the 1-section template at 239 chars.

**Pattern across the panel.** 12 of 36 panel qids hit a 101-char `### Respuestas directas\n*   **<question>**` template upstream (the question-reformulation shape). All 12 polish-expand into substantive answers (1500-4500 chars) with citations preserved. **The 101-char shape is the most reliable expansion path in the entire pipeline.**

**Rule.** When upstream extraction comes back sparse, **route through the proven-good shape instead of preserving the thin section**. Concrete: in `answer_first_bubble.compose_first_bubble_answer`, after section assembly, if `len(substantive_sections) < 2 AND len(primary_articles) >= 2 AND not direct_answers AND answer_mode == "graph_native"`, replace the assembled output with the question-reformulation shape enumerating the user's `¿…?` sub-questions (or the full message).

**Result.** Panel 35 → 36/36 acc+; `regimen_sancionatorio_extemporaneidad_P2` 239 → 3345 chars with the actual sanction calculation `$4.500.000 × 5% × 2 meses = $450.000` (50% reduction → $225,000), legal framework (arts. 641, 640, 635, 642 ET), procedure, and risk warnings. All citations real, no invention.

**Why the joint condition matters.** False-positive risk: multi-section answers that are intentionally brief (e.g. "Riesgos y condiciones" is the right primary output for some risk-only queries). Mitigated by `len(substantive_sections) < 2` AND `primary_count >= 2` AND `not direct_answers` — three signals all have to align before the fallback fires.

**Code.** `src/lia_graph/pipeline_d/answer_first_bubble.py::compose_first_bubble_answer`. Close-record: `docs/re-engineer/fix/fix_v4.md` §12.

## L7 — Markdown-aware line splitter + heading rejection

**Incident.** Pre-fix_v3, `_evidence_candidate_lines` only split on `[.;:]\s+`. Practica/expertos chunks shaped like `## Paso a Paso Práctico\n### PASO 1 — Identificar canalización obligatoria\nPregunta clave: ¿…?` collapsed into a single run-on string that hit the >240-char drop. Then post-fix_v3, residual cases shipped the heading text verbatim as bullets (`regimen_cambiario_P2` rendered `## ARTÍCULO 26-35 — PROCEDIMIENTO DE DECLARACIÓN DE CAMBIO #### Contenido Mínimo La declaración debe contener.`).

**Rule (two layers).**

1. **Splitter shape** (fix_v3 phase 4 Fix 2): split on `\n+` first; strip leading markdown markers (`#`, `*`, `-`, `•`); THEN split each paragraph on sentence boundaries. Generalizes for any markdown-shaped chunk in any corpus family.
2. **Post-split heading rejection** (fix_v5 phase 6a): module constant `_HEADING_REJECT_PATTERNS` of 5 compiled regexes (`^#{2,4}\s`, `^\s*ARTÍCULO\s+\d+`, `^\s*PASO\s+\d+\b`, `^\s*>\s*Pregunta\s+clave`, `####`); reject any line matching any pattern. Patterns are intentionally narrow (don't match generic short lines); the §1.G panel acts as the regression check.

**Anti-pattern.** Don't replace the splitter with an LLM-routed alternative. Both layers are deterministic, reversible, renderer-layer fixes — the right place per L4. Don't tighten the patterns either; the §1.G post-fix_v5 panel hits 36/36 even with the current narrow patterns.

**Code.** `src/lia_graph/pipeline_d/answer_support.py::_evidence_candidate_lines`, `_HEADING_REJECT_PATTERNS`. Close-records: `docs/re-engineer/fix/fix_v3.md` §13.1 (Fix 2) + `fix_v5.md` §10.

## L8 — Sub-Q topic carry-over from parent on fallback resolves

**Incident.** With `LIA_QUERY_DECOMPOSE=on`, parent messages with multi-`¿…?` get fanned out into N sub-queries; each sub-Q runs through its own topic_router → planner → retriever cycle. Short sub-Qs ("¿eso cambia algo?", "¿la sanción es del 10%?") often lose enough signal for both rule-route AND LLM-route to miss. The keyword fallback then picks an off-topic anchor (commonly `factura_electronica` from incidental keywords) and the sibling sub-bullet drifts to the wrong corpus slice. 4 of 8 acc qids in the post-fix_v5-phase-5 panel showed this drift.

**Wrong fix attempted (fix_v1 phase 2 H1, DISCARDED).** "Thread `runtime_config_path` + `conversation_state` through the sub-query `_resolve` call so the LLM classifier always runs." Panel 22 → 16/36 — regressed by 6. The LLM running on every sub-Q overshot: short sub-Qs with weak signal pulled topic-confident hallucinations out of the LLM that the keyword fallback (with low confidence) wouldn't have produced.

**Right fix (fix_v5 phase 6b).** At orchestrator level, when a sub-Q resolves to `mode == "fallback"` AND `effective_topic` differs from the parent's resolved topic, build a synthesized `TopicRoutingResult` inheriting the parent topic + secondary topics with `mode="subquery_parent_inheritance"`, `confidence=0.6`, `reason="fix_v5_phase6b:subquery_inherited_parent"`. **Confident rule-route hits on a different topic stay respected** (multi-domain integrity preserved). Panel 29 → 32 strong; 4 acc qids flipped.

**Rule.** Inheritance is not symmetric with override. The right inheritance trigger is **the failure mode of the alternative** (`mode == "fallback"`), not a confidence threshold or a key-presence test. Multi-domain hits where the rule-route confidently picks a different topic are legitimate — don't blanket-inherit.

**Diagnostic.** Trace step `topic_router.subquery_inherited_parent` records every inheritance event. Read it from `<run>/<qid>.json::response.diagnostics.pipeline_trace.steps[*]` to confirm the parent topic was inherited rather than lost. If you see it on confidently-different rule-route hits, the precondition logic broke.

**LLM-noise vs systematic regression caveat.** First fix_v5 phase 6b run flipped `firmeza_declaraciones_P1` strong → acc; trace inspection showed the qid took the single-query path (no fan-out), so the fix couldn't have caused it. Polish_changed flipped True → False on a non-deterministic gemini-flash call. The rerun recovered it. **Always rerun a panel before declaring a non-target qid regression real**; gemini-flash polish is stochastic on a small fraction of qids.

**Code.** `src/lia_graph/pipeline_d/orchestrator.py` (sub-query fan-out block). Close-record: `docs/re-engineer/fix/fix_v5.md` §11.

## L9 — Find the binary success signal in the trace before debating fixes

**Incident.** fix_v3 §13.2 cross-question pattern analysis. The deep dive (operator's "exercise the special verbose loggers we have") tabulated all 36 qids in the Route B baseline by trace stage. The dominant pattern fell out immediately:

| `polish_changed` | qid count | served_strong | served_acceptable | served_weak | served_off_topic (old grader) |
|---|---|---|---|---|---|
| **True** (LLM expanded) | 32 | 21 | 7 | 0 | 4 |
| **False** (LLM left as-is) | 4 | 0 | 1 | 3 | 0 |

`polish_changed` was the binary success signal. 32/32 polish-fired qids landed acc+; 0/4 polish-refused qids landed acc+. **All four interventions in fix_v3 phase 4 + fix_v4 phase 5 + fix_v5 phase 6 derived directly from this binary breakdown** — they each targeted a different failure mode of the polish refusal (thin draft / single bullet / missing structural condition / heading-text leak / sparse extraction).

**Rule.** Before debating which fix to apply, find the binary signal in the trace. Tabulate every qid by the candidate signal; if the signal partitions cleanly (e.g. 32/32 vs 0/4), every downstream fix can target one side of the split. If it doesn't partition cleanly, the signal isn't binary and you need a different one.

**Generalizes to.** Any debugging flow on a panel of N samples where the ground-truth label exists. Pick a candidate trace field; tabulate; see if the contingency table is degenerate. If the field doesn't separate, try another field. The traversal is much cheaper than empirical A/B testing.

**Code/data.** `polish.applied.polish_changed` in the pipeline_trace. The §13.2 tabulation script lives inline in `docs/re-engineer/fix/fix_v3.md` §13.2.

## L10 — The wrong-layer fix detection rule

**Incident.** fix_v3 phase 4 Route A (DISCARDED): "tighten primary-promotion at `_classify_article_rows` to require a numeric-looking article_key for non-anchor signals." Reasoning: practica/expertos chunks have slug article_keys; demoting them from primary should fix the slug-anchor template leak. Result: -1 acc+, 1 hard regression (`beneficio_auditoria_P2` strong 3537 chars → weak 561 chars), 0 Symptom-A flips.

**Why it failed.** `_classify_article_rows` only has two buckets: `primary` and `connected`. Items dropped from primary land in `connected`, not in `support_documents`. The synthesis layer at `answer_inline_anchors.py:115` reads `candidate_rows = (*primary_articles[:5], *connected_articles[:3])` — so chunks that were demoted from primary to connected were STILL fed into `_anchor_label_for_item` and STILL fell back to rendering the raw slug. Net behavior change: same 109-char stub, same slug-prefixed citation. The retriever-level "fix" couldn't possibly fix the synthesis-level rendering bug, because both buckets feed the same renderer.

**Rule.** **The right layer for a fix is the layer that owns the visible artifact, not the layer that produces the input to it.** Concrete checks before committing to a layer:

1. **Trace which buckets the synthesis layer reads from.** If multiple bucket → same renderer, you can't fix the renderer's output by re-bucketing.
2. **Spot-check the canonical broken example.** If your proposed fix can't explain why `<qid>` stops emitting `<artifact>`, the layer is wrong.
3. **Look for two-pass selection in the synthesis path.** If the synthesis layer makes its own filtering decisions on what the retriever returned, the retriever-level fix has limited reach.

**The real fix (fix_v3 phase 4 Route B).** `_anchor_label_for_item` final fallback returns `""` instead of the raw slug; both call sites in `select_inline_anchors` already filter empty labels. The bug was in the renderer; the fix lives in the renderer.

**Code.** `src/lia_graph/pipeline_d/retriever_supabase.py::_classify_article_rows` (Route A discard); `src/lia_graph/pipeline_d/answer_inline_anchors.py::_anchor_label_for_item` (Route B keep). Close-record: `docs/re-engineer/fix/fix_v3.md` §11.

## L11 — Eval-grader fairness rules belong in the eval, not in the runtime

**Incident.** Pre-fix_v3 phase 4, `scripts/eval/run_sme_validation.py::classify` rule was: `actual_topic ≠ expected_topic → served_off_topic` regardless of answer substance. A 3,300-char substantive answer that the router resolved to an adjacent topic (e.g. `iva` for an IVA-en-activos-fijos question that the panel labelled `descuentos_tributarios_renta` — art 258-1 ET genuinely sits in both topics) bucketed the same as a thin off-topic stub. 4 panel qids hit this; the system was producing useful answers, the grader was scoring them as failures.

**Rule.** Grader fairness is a separate problem from runtime correctness. Don't tune the runtime to satisfy a strict grader; tune the grader to distinguish "system produced nothing useful" from "system produced something useful but tagged a different topic." fix_v3 phase 4 Fix 3:

- `served_off_topic = wrong_topic AND thin_answer (n < 600 OR cites < 1)` — system produced nothing.
- `served_acceptable = substantive (n ≥ 600 AND cites ≥ 1)` regardless of topic-key match — partial credit, useful to the accountant.
- `served_strong = right_topic AND n ≥ 1500 AND cites ≥ 3 AND graph_native` — strict; unchanged.

Net effect on the post-fix_v3 baseline: 4 grader-strict off_topic flags → 0; panel +4 from fairness alone (+1 from pipeline = 5 total in the phase-4 close).

**Detection.** When tuning a grader, run BOTH the old grader and the new grader on the same baseline run dir. If the new grader changes acc+ count by Δ ≥ N qids, hand-audit each Δ qid to confirm the new bucket is fairer. fix_v3 §13.3 shipped that table.

**Anti-pattern.** Don't tune the grader to make a specific run pass. Tune it on the principle ("substantive on-adjacent should count differently from substantive on-topic"); accept whatever Δ falls out. The grader change is a one-time fairness fix; it should never recur per-panel.

**Code.** `scripts/eval/run_sme_validation.py::classify`. Close-record: `docs/re-engineer/fix/fix_v3.md` §13.1 Fix 3.

## L12 — Canonicalizer Supabase writes don't auto-project to Falkor

**Incident (fix_v6).** After fix_v5 close, a staging-environment health audit found Supabase `norms` table at 17,169 rows (all created Apr 29 by the canonicalizer) but Falkor `Norm` label at only 2,905 nodes. `norm_id` shapes in Falkor look like `ley.1607.2012` (parent-law granularity) — no article-level entries (`ley.2010.2019.art.10`, `articulo_et.*`, `oficio_dian.*`). Gap: ~14,264 norms exist in Supabase with no Falkor projection.

**Why it's not a red flag for chat today.** Vigencia is **norm-keyed in Supabase only** (per `feedback_vigencia_norm_keyed.md` memory). The vigencia gate runs as a Supabase RPC (`chunk_vigencia_gate_at_date` / `norm_vigencia_at_date`) and needs no Falkor lookup. Article-level traversal still works (9,249 ArticleNode in Falkor). The canonicalizer's new norms are reachable for chunk-vigencia checking; they're just not graph-traversable.

**Rule.** Canonicalizer pipeline lanes write to Supabase as the source of truth; Falkor projection is a **separate, idempotent step** that runs after the canonicalizer cycle settles. Do not couple canonicalizer batches to Falkor projection — that re-introduces the slow-LLM-call-blocks-cloud-write coupling we engineered out in `ingestion/parallelism-and-rate-limits.md`. The right shape is `scripts/cloud_promotion/project_norms_to_falkor.py` (NEW per fix_v6 §3): MERGE-by-norm_id idempotent; runs detached + heartbeat per the long-running Python process canon.

**Companion rule (vigencia is Supabase-only).** Falkor `Norm` nodes don't carry vigencia properties. A fresh agent reading the schema might assume vigencia is queryable in Cypher (because there's a `Norm` label) and write a `WHERE n.vigencia_status = 'vigente'` branch that always matches zero. fix_v6 phase 7c added a one-line callout in the Falkor schema docstring: "Vigencia state lives in Supabase `norm_vigencia_history` only; never query `n.vigencia_status` in Cypher — call the `norm_vigencia_at_date(norm_id, asof)` SQL RPC instead."

**Code.** `scripts/cloud_promotion/project_norms_to_falkor.py` (per fix_v6 §3 Step 2 — NEW), `src/lia_graph/graph/schema.py` (vigencia callout per fix_v6 §3 Step 6). Close-record: `docs/re-engineer/fix/fix_v6.md`.

## L13 — Truncated chunk tails: don't auto-add periods to mid-word fragments

**Incident (2026-04-30, post-fix_v6).** SME query `¿Cuáles son las fechas límite ... NIT? ¿Dónde encuentro el decreto de plazos vigente y qué consecuencias tiene la presentación extemporánea?` rendered a bullet `Las personas o entidades obligadas a declarar, que presenten las declaraciones tributarias en forma extemporánea, deberán liquidar y pagar una sanción por cada mes o fra (arts. 641 y 640 ET).` The cloud Supabase chunk for art. 641 was literally truncated mid-word at `…o fra` (no trailing punctuation). The splitter at `_evidence_candidate_lines` then auto-appended a period (line 777-778 `if cleaned[-1] not in ".!?": cleaned += "."`) producing a 170-char "sentence" ending in `fra.`, which passed the 45-240 length filter and reached the renderer, which then stripped the `.` to append `(arts. … ET)` — so the bullet visibly read `…o fra (arts. 641 y 640 ET)`.

**Diagnosis ladder.** First hypothesis (stray `.`/`:`/`;` mid-word in cloud chunk + splitter mid-word fracture) fixed half the failure shapes but missed THIS one because the chunk has NO trailing punctuation at all — the chunk text ends literally at `fra`. Confirmed by writing a one-shot stderr probe to `/tmp/lia_fra_debug.log` that captured the actual paragraph: `'Artículo 641 . EXTEMPORANEIDAD EN LA PRESENTACIÓN. Las personas... por cada mes o fra'`.

**Rule.** **Don't auto-append a sentence terminator to a fragment whose last whitespace-separated token is in the abbreviation/word-fragment whitelist** (`art`, `arts`, `núm`, `pág`, `inc`, `par`, `lit`, `ord`, `cap`, `vol`, `ed`, `cf`, `etc`, `sr`, `dr`, `fig`, `nt`, `op`, `cit`, `fr`, `fra`, `frac`, `fracc`, plus `articulo`/`artículo` long forms). Drop the candidate instead. Real Spanish prose ending without a period is rare enough that a short trailing token in this list is much more likely a cut chunk than valid copy.

**Why an upstream-only fix is insufficient.** The canonicalizer normalizer pass (planned per next_v4 §10.x) cleans hyphenation/whitespace artifacts but cannot fix chunks that simply end early because the source PDF/scrape stopped mid-line. The runtime guard is the durable defense; the upstream cleanup reduces frequency.

**Detection.** Trace event `synthesis.compose_template` carries `template_chars`; a 240-char filter pass with downstream short-bullet emission is the signature. Probe the actual chunk text with a temporary stderr write at `_evidence_candidate_lines` when the bullet appears suspect — the splitter is otherwise opaque.

**Anti-pattern.** Don't tighten `_HEADING_REJECT_PATTERNS` to catch this — the heading regex shouldn't carry sentence-validity logic. Don't add a polish-prompt clause to "skip truncated bullets" (L4 blast radius). The right layer is the sentence-builder itself, where the auto-period decision is made.

**Code.** `src/lia_graph/pipeline_d/answer_support.py::_TRUNCATED_TAIL_TOKEN_RE`, `_evidence_candidate_lines` (the conditional drop before `cleaned += "."`), companion `_ABBREVIATION_BEFORE_PERIOD_RE` + `_merge_abbreviation_splits` for the related stray-punctuation-mid-word case. Both regexes share `_ABBREVIATION_TOKENS` so synonyms grow in one place.

**Generalizes to.** Any sentence-builder that defensively appends terminators. The decision "should this fragment get a period" is a classification problem — needs a stop-list of suspicious tail tokens, not blind appending.

## L14 — Canonical question shapes: a config-driven escape hatch from L8

**Incident (2026-04-30, post-fix_v6).** Same SME query as L13. Sub-question #0 ("¿Cuáles son las fechas límite ... NIT?") was correctly classified by keyword fallback as `declaracion_renta` (top score 7) but L8's parent-inheritance rule (`fix_v5_phase6b:subquery_inherited_parent`) overrode it to the parent's `regimen_sancionatorio_extemporaneidad` — because the parent rule-routed at confidence 0.98 on the word "extemporánea" present only in sub-question #1. Retrieval ran against the sanctions corpus, no calendar/plazos chunks present, sub-question #0 rendered `Cobertura pendiente para esta sub-pregunta`.

**Trade-off the L8 rule sits on.** Last week's fix_v5 phase 6b parent-inheritance was a +3-strong win because short sub-Qs ("¿eso cambia algo?") that the keyword fallback couldn't classify confidently benefited from inheriting the parent. The straightforward rollback (don't inherit) would re-break those 4 cases. The straightforward "don't inherit when sub-Q has its own anchor" couldn't be implemented from the L8 fix's own data — needed new structure.

**Rule.** Add a **config-driven canonical-shape table** that fires BEFORE the parent-inheritance check. When a sub-Q (or a parent message) matches a curated shape, the keyword-fallback result is promoted from `mode=fallback` to `mode=canonical_shape` (confidence 0.9). The inheritance branch only fires on `mode=fallback`, so the promoted result passes through untouched. Last week's win stays intact for everything the shape table doesn't cover.

**Shape definition (config/canonical_question_shapes.json).** Each shape is a trio of trigger groups — `question_words_any`, `subject_phrases_any`, `qualifier_phrases_any` — plus `topic` (the keyword classifier's effective_topic the shape applies to) and `evidence_shape_override`. A shape matches when every non-empty trigger group has at least one phrase present in the normalized message AND the classifier's topic equals the shape's topic. The classifier-topic gate makes the canonical match a **confidence boost on a correct classification, not an override of any classification** — exactly the behavior that lets it coexist with rule-route, LLM-route, and parent-inheritance without conflict.

**Companion: `tabular_reference` evidence budget.** Many canonical-shape questions need *more text* than the default snippet truncation gives (NIT-digit calendars, UVT tables, retention-rate matrices fit poorly in 220-260 chars). The shape carries an `evidence_shape_override.query_mode = "tabular_reference"` hint that the planner reads to swap in the high-limit budget (`snippet_char_limit=600`, `primary_article_limit=5`, `support_document_limit=6`). LLM polish (gemini-flash) renders tables natively when fed table-shaped chunk text; no polish-prompt edit needed (L4-compliant).

**Why this dodges L8's regression risk.** The escape hatch is *additive* and *gated*. A shape only fires when (a) the keyword classifier already picked the shape's topic and (b) every trigger group is satisfied. Sub-Qs not matching any shape go through the existing path unchanged. Last week's 4 wins (short sub-Qs without their own keyword anchor) continue to inherit the parent topic because they don't match any shape. Each new shape is a one-row JSON addition; no code change, no panel re-run beyond the targeted shape's regression check.

**SME curation discipline (mirrors L3).** Like `compatible_doc_topics.json` and `article_secondary_topics.json`, shapes are SME-curated. Don't add a shape on a single failure; require the SME to confirm: (a) the question shape is unambiguous, (b) the corpus actually has the answer, (c) the response wants more space than 220 chars. Each shape carries a `description` field intended for the SME reviewer.

**Detection.** Trace event `topic_router.canonical_shape.hit` records every shape match with `shape_id`, `original_mode`, `original_confidence`, `promoted_to_mode`, `subtopic_hint`. Read it from `<run>/<qid>.json::response.diagnostics.pipeline_trace.steps[*]` to confirm a shape fired and to audit unintended matches.

**Anti-pattern.** Don't expand `subject_phrases_any` so broadly that the shape catches semantically-different questions sharing keywords. The keyword classifier is doing real work — the shape is supposed to be a *narrow* boost on cases where the classifier was right but inheritance steamrolled it. If a shape fires on the wrong topic, the topic gate failed; tighten the shape's `qualifier_phrases_any` to add specificity.

**Generalizes to.** Any router with a high-confidence override path that occasionally clobbers a correct low-confidence classification. The pattern: identify the failure shape, encode it as a deterministic match table, gate the override on the classifier already agreeing — so the table promotes correctness, never invents it.

**Code.** `config/canonical_question_shapes.json` (the table — grows here), `src/lia_graph/canonical_question_shapes.py` (loader + matcher), `src/lia_graph/pipeline_d/orchestrator.py` (sub-Q hookup before `subquery_inherited_parent`), `src/lia_graph/pipeline_d/planner.py::_BUDGETS["tabular_reference"]` + the override after `_classify_query_mode`. CLAUDE.md "Canonical question shapes" section carries the operating instructions for adding new shapes.

**Companion: `compatible_doc_topics.json` adjacency wiring (L3 §extension).** Routing the sub-Q to `declaracion_renta` via the canonical shape isn't sufficient on its own — the answer's source document (`seccion-06-calendario-tributario.md`) carries `topic_key=calendario_obligaciones`. Without compat wiring, the L3 5-signal classifier has no path to promote it (signal 3 mismatch, signal 4 had no entry for `declaracion_renta`). The 2026-04-30 round added three mutual-compatibility entries: `declaracion_renta ↔ calendario_obligaciones ↔ regimen_sancionatorio_extemporaneidad`. Calendar docs now surface as primary evidence under any of those router topics. **Pattern**: every canonical shape that routes to a topic different from where its answer lives needs a corresponding compat entry — they're a paired construct.

## Cross-cutting meta-rules

These showed up across multiple fix cycles and deserve a sentence each:

| Meta-rule | Where it surfaced |
|---|---|
| **Keep historical anchor runs** as evidence for discarded routes (six-gate gate 6: never silently rolled back). | fix_v1 phase 2 H1 discard, fix_v3 Route A discard, slug-cleanup discard, fix_v5 phase 6c discard. Each kept its run dir. |
| **Iteration ladder per phase**: max 3 iterations before operator escalation. Each iteration is ~7 min wall (5 min code/restart + 2 min panel + classifier). | Fix_v3, fix_v4, fix_v5 each capped at 3 iterations. Phase 6c hit the cap and escalated to fix_v6. |
| **A panel re-run is mandatory after a same-day code change** even if "it's just a one-line fix" — gemini-flash polish is stochastic; non-target qid noise is real. | fix_v5 phase 6b first run flipped firmeza_P1 strong → acc on a non-decomposed qid. Rerun recovered it. |
| **LLM polish refusal vs LLM polish expansion is the binary signal**, not the underlying question complexity. Most "thin answer" failures are polish-refusal failures, not retrieval failures. | fix_v3 §13.2; fix_v4 phase 5 Route A; fix_v5 phase 6c (same pattern, polish-prompt blast radius). |
| **Each phase ships its own commit + its own §1.G regression re-run.** Don't bundle for "efficiency." Bundling makes regressions un-bisectable. | fix_v3, v4, v5 all shipped per-phase commits. |
| **`served_strong` is the early-warning metric**, not `acc+`. Polish blast radius can hold acc+ flat while crashing strong by 5+. | Slug-cleanup discard (-5 strong, 36/36 acc+ held). |

## What WASN'T fixed in this campaign

The post-fix_v5 anchor leaves 4 served_acceptable qids with content-quality gaps that are **not surgical-route-shaped**:

| qid | gap | Layer |
|---|---|---|
| `conciliacion_fiscal_P2` | sub-Q calc on $400M revaluación → impuesto diferido not run | numeric-calc enforcement (deferred to fix_v6+) |
| `conciliacion_fiscal_P3` | borderline strong vs acc; substantive but SME-grader called it acc | grader strictness OR topic-specific evidence-extraction gap |
| `descuentos_tributarios_renta_P2` | $120M × 19% calc not run; norm cited | numeric-calc enforcement |
| `regimen_sancionatorio_extemporaneidad_P1` | borderline; specific UVT calc present | borderline; possibly grader-strict |

Numeric-calc enforcement is the thread connecting 3 of 4. The natural next layer is a **deterministic post-polish numeric extractor** (detects user-message numeric tokens; verifies the answer contains a calculation string) OR a **dedicated calc-prompt step** that runs ONLY when numeric tokens are present. NOT a polish-prompt clause (per L4).

## Cross-references

- `docs/re-engineer/fix/fix_v1_diagnosis.md` — the canonical diagnostic write-up shape; new agents reading the campaign should start here.
- `docs/re-engineer/fix/fix_v{1,2,3,4,5,6}.md` — close-records with gate-by-gate mechanics and per-phase panel deltas.
- `docs/orchestration/orchestration.md` — env matrix `v2026-04-29-chat-runtime-hardening` carries the change-log rows for every landed phase.
- `docs/guide/chat-response-architecture.md` — synthesis-layer + polish-layer module map updated with fix attribution.
- `tracers_and_logs/README.md` — pipeline-stage deep trace contract.
- `docs/learnings/process/deep-trace-before-hypothesis-debate.md` — companion meta-rule from next_v4 about code-anchored traces beating empirical A/B for ruling out hypotheses.
- `docs/learnings/retrieval/coherence-gate-and-contamination.md` — the v6 coherence gate that fix_v2's 5-signal model dropped 9-of-9 false-positive refusals on.
- `docs/learnings/retrieval/conversational-memory-staircase.md` — the next_v4 §3 fix for cross-turn topic carry-over; complementary to L8's intra-turn sub-Q carry-over.
