# Expert Package — Is Our Day 1–2 Eval Harness Sound?

**One question, one verdict.** Before we stack weeks of retrieval/reranker/decomposer work on the baseline numbers this harness produces, we want a senior RAG practitioner to tell us whether the harness itself is honest. If it is, we trust the `FAIL` signals and start closing the gap. If it isn't, we fix the harness before anything else.

Scope fence: **we are not asking for a roadmap, a reranker opinion, or a corpus-curation plan.** The senior review baked into `docs/next/structuralwork_v1_SEENOW.md` already gave us that ordering. We are asking one narrow thing: **is `scripts/eval_retrieval.py` (+ the normalizer + the 30-entry gold schema) a trustworthy grading rubric for this product?** A two-paragraph verdict with specific callouts is ideal.

---

## 60-second product context

`Lia_Graph` is a graph-native RAG product for Colombian SMB accountants. They ask messy multi-`¿…?` questions in Spanish about tax, labor, payroll, and compliance (e.g., `"Tengo un cliente SAS comercializadora con ingresos brutos de $3.000 millones... ¿Cuánto puede deducir...?"`). The served runtime is `pipeline_d`: a planner that anchors to an article graph (ET = Estatuto Tributario) + a hybrid chunk retriever on Supabase + a cross-encoder reranker in shadow. Answers must cite real `article_key`s and follow regulated-domain voice. The accountant who reviews the gold is the same domain authority who'd review a production answer.

---

## What the harness does

Code: [`scripts/eval_retrieval.py`](../../scripts/eval_retrieval.py) (single file, ~450 LOC).

1. Reads [`evals/gold_retrieval_v1.jsonl`](../../evals/gold_retrieval_v1.jsonl) (30 entries, grown by hand from a larger 30-question accountant evaluation doc).
2. For each entry: calls `resolve_chat_topic(message)` → builds `PipelineCRequest(topic=resolved)` → fires `run_pipeline_d(request)`. This mirrors the `ui_server.py` production routing path (the pipeline itself doesn't route — it echoes `request.topic`).
3. Pulls ranked `node_key`s from `response.diagnostics.evidence_bundle.primary_articles` + `connected_articles` (primary first, connected second, dedup, first-seen order preserved).
4. Pulls `sub_topic_intent` from `response.diagnostics.planner.sub_topic_intent` and `effective_topic` from the resolved routing.
5. For M-type entries, fires each `sub_question.text_es` as its own query and scores its own `expected_article_keys`.
6. Emits six metrics: `retrieval@10`, `nDCG@10` (binary-relevance), `MRR`, `topic_accuracy`, `subtopic_accuracy`, `sub_question_recall@10`.
7. `--fail-under-red-lines` exits non-zero if any gated metric is below its v0 floor: `retrieval@10 ≥ 0.70`, `topic_accuracy ≥ 0.85`, `sub_question_recall@10 ≥ 0.60`. This is the CI gate.

### The normalizer — the most load-bearing piece

The gold uses fully-qualified keys the accountant can read at a glance (`ET_ART_771_2`, `LEY_2277_2022_ART_7`). The retriever emits bare graph keys (`771-2`, `LEY-2277-2022`). We normalize both sides to a small set of canonical surface forms and set-intersect. Explicit rules:

- `ET_ART_X_Y` → also match `X-Y` (ET is the implicit default law; ArticleNode keys are bare).
- `ET_ART_240_PAR_6` → also match `240` (parent article is acceptable when gold specifies a paragraph; a reader finds the paragraph once at the article).
- `LEY_NNNN_YYYY_ART_Z` → also match `LEY-NNNN-YYYY` (reform articles aren't separate nodes in this graph schema today; matching at the law level is the most we can claim).
- Other prefixes (`DECRETO_`, `RES_`, `CONCEPTO_`, `CE_SENT_`) — hyphen-normalized, otherwise verbatim.

No fuzzy matching, no LLM judging. Either a form matches or it doesn't.

---

## Gold schema

Per-entry (30 total, hand-annotated by a practicing Colombian accountant from the 30-question evaluation corpus in `docs/quality_tests/`):

```json
{
  "qid": "Q2",
  "type": "M",
  "query_shape": "multi",
  "macro_area": "a_renta_pj",
  "initial_question_es": "Necesito ayuda con la TTD para un cliente SAS...",
  "expected_topic": "declaracion_renta",
  "expected_subtopic": "ttd_tasa_tributacion_depurada",
  "expected_article_keys": ["ET_ART_240_PAR_6", "CONCEPTO_DIAN_006483_2024", "ET_ART_807", "ET_ART_689_3"],
  "followup_question_es": "...",
  "followup_expected_article_keys": ["CONCEPTO_DIAN_100208192_202_2024", "CE_SENT_28920_2025"],
  "sub_questions": [
    {"text_es": "¿Cómo calculo la TTD paso a paso?", "expected_topic": "declaracion_renta", "expected_subtopic": "ttd_tasa_tributacion_depurada", "expected_article_keys": ["ET_ART_240_PAR_6"]},
    {"text_es": "¿Qué pasa si el resultado queda por debajo del 15%?", "expected_topic": "declaracion_renta", "expected_subtopic": "ttd_tasa_tributacion_depurada", "expected_article_keys": ["ET_ART_240_PAR_6"]},
    {"text_es": "¿En qué renglón del Formulario 110 registro el Impuesto a Adicionar?", "expected_topic": "declaracion_renta", "expected_subtopic": "formulario_110", "expected_article_keys": []}
  ]
}
```

Distribution: 15 S-type (single-shot), 15 M-type (multi-`¿…?`). 2 entries are flagged `expected_topic_uncertain: true` (Q19, Q28) — they're excluded from `topic_accuracy` numerator and denominator until the curator rules. 5 entries have `expected_article_keys: []` (periodicity/tariff lookups with no single anchor) — excluded from retrieval scoring but kept for topic/subtopic.

Known limits we already see:
- 30 is below the 80–120 target. We plan to grow to 50 next week by mining `logs/chat_verbose.jsonl`.
- The accountant's spot-check pass is still pending — one wrong anchor poisons the subdomain.
- `expected_subtopic` slugs were filled in without cross-checking that the planner's `_detect_sub_topic_intent` actually emits those slugs. See "The subtopic_accuracy = 0 anomaly" below.

---

## Baseline numbers (2026-04-22, local artifacts, reranker shadow + sidecar unset)

```
retrieval@10             0.307  (red line ≥ 0.70)   FAIL
nDCG@10                  0.274
MRR                      0.355
topic_accuracy           0.429  (n=28, red line ≥ 0.85)   FAIL
subtopic_accuracy        0.000  (n=30)
sub_question_recall@10   0.307  (n=23, red line ≥ 0.60)   FAIL
```

Per-entry `r@10` ranges from `0.000` to `1.000`. Q5, Q14, Q18, Q24 hit perfect recall; Q1, Q4, Q8, Q13, Q15, Q16, Q19, Q23, Q25, Q26, Q28 hit 0 — roughly the split between queries whose anchor lives in the ET chunk graph vs queries whose anchor is a DIAN concept / resolution / external law (the known three-family asymmetry in the structural doc's item H).

### The `subtopic_accuracy = 0` anomaly

Not a single entry matched on subtopic. Our working hypothesis: the planner's `_detect_sub_topic_intent` emits slugs from `config/subtopic_taxonomy.json` (106 curated subtopics × 39 parent topics), but the gold's `expected_subtopic` values were written by the accountant in the same domain vocabulary *without* being cross-indexed against that taxonomy. So `ttd_tasa_tributacion_depurada` in the gold probably maps to a differently-named slug in `config/subtopic_taxonomy.json`, or isn't in the taxonomy at all. We haven't dug in yet — we'd like your read on whether this is a harness bug (we should drop subtopic_accuracy until the gold is re-indexed) or a real-product signal (the planner genuinely doesn't emit a subtopic on these queries, and that's an item-B finding).

---

## Specific sub-claims we want you to challenge or confirm

1. **Topic routing path.** We call `resolve_chat_topic(message)` in the harness and use its output as `request.topic`. Production (`ui_server.py`) does the same thing. `run_pipeline_d` echoes `request.topic` back as `effective_topic` — it does not route. Is this the right level to measure "topic accuracy"? Or should we score the router's raw output regardless of whether pipeline_d would use it?

2. **Article ranking.** We concatenate `primary_articles` + `connected_articles` in their returned order, dedup, take top-10. Primary = planner-anchored seeds (hop_distance 0); connected = graph neighbours (hop_distance ≥ 1). Is this concatenation honest as "the retrieved top-10"? Or should connected articles be excluded (they're graph-expanded, not retrieved-per-se), which would make `retrieval@10` drop further but be cleaner?

3. **Normalizer strictness.** We explicitly loosen `ET_ART_X_PAR_Y` to also match the parent `X`. The reasoning is that a reader finds a paragraph once at its article. Is that defensible, or does it inflate recall?

4. **Sub-question recall.** For M-type, we fire each `sub_question.text_es` independently and score its own `expected_article_keys`. For S-type, the main query counts as its own sub-question (r@10 folded into the sub-question pool). Is this the right way to aggregate, or would a weighted mean (by `|expected_article_keys|`) be more honest?

5. **Red lines.** `retrieval@10 ≥ 0.70`, `topic_accuracy ≥ 0.85`, `sub_question_recall@10 ≥ 0.60` from the senior review baked into `structuralwork_v1_SEENOW.md` §#1. With 30 entries and ~25 scoring for retrieval, one flaky query swings ~4 percentage points. Is gating non-zero PRs on these thresholds signal or noise at n=30?

6. **nDCG/MRR.** Reported but ungated. Binary relevance (gold has no graded relevance). Is that the right call, or should we gate on nDCG@10 once the gold is bigger?

7. **Missing axes.** Not measured today: answer quality (we stop at retrieval), latency per query, token cost per query, citation faithfulness (does the answer actually cite the articles it retrieved), hallucination rate. Do you see one of these as load-bearing enough that we should build it in before trusting the retrieval metrics?

---

## What to open first (if you want to read code)

- `scripts/eval_retrieval.py` — the harness, single file, ~450 LOC
- `evals/gold_retrieval_v1.jsonl` — all 30 entries, one per line
- `src/lia_graph/pipeline_d/orchestrator.py:164` — `run_pipeline_d` entry
- `src/lia_graph/pipeline_d/contracts.py:197` — `GraphEvidenceBundle` (what the harness pulls ranked keys from)
- `src/lia_graph/topic_router.py:600` — `resolve_chat_topic`
- `docs/next/structuralwork_v1_SEENOW.md` §"Landed state (2026-04-22)" — the baked-in senior review + what shipped this week

## To reproduce locally

```bash
# one-liner; exits 0/1 per red lines
make eval-retrieval

# human-readable report without the gate
make eval-retrieval FAIL_UNDER=0

# JSON payload for a machine diff
make eval-retrieval FAIL_UNDER=0 JSON=1 > /tmp/eval.json
```

The harness is deterministic against the artifacts bundle (no cloud, no LLM). A 30-entry run takes ~90 seconds.

---

## What the answer looks like

Ideal verdict: two paragraphs. Paragraph 1 — "the harness is / is not sound, because..." with a specific pointer to a sub-claim above. Paragraph 2 — "the one thing I'd change before trusting a single number" with a concrete fix path. Anything else is bonus.

If the verdict is "fix X, Y, Z before trusting any number" — that's the best possible outcome; we'd rather redo a day than build a week of work on a dishonest scale.
