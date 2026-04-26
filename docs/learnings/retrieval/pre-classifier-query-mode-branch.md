# Pre-classifier query-mode branch — when a generic classifier dilutes a domain shape

> **Captured 2026-04-25** from `docs/aa_next/next_v4.md §5`. Code lives in `src/lia_graph/pipeline_d/answer_comparative_regime.py`, `src/lia_graph/pipeline_d/planner.py:128,279-319`, `src/lia_graph/pipeline_d/orchestrator.py:322-326`, `config/comparative_regime_pairs.json`.

## The symptom

A live three-turn session pasted by the operator on 2026-04-25. The third turn — "cuanto cambia esto si alguna parte del saldo es de pre 2017?" — returned an evasive answer:

> "Sí cambia. Debes validar el régimen de transición del art. 290 ET antes de aplicar la regla de los 12 años."

…plus a single-line Ruta, one Riesgo, and a Soportes section that **hallucinated a description for Art. 290 ET** ("Régimen de transición para la depreciación de activos"). Two distinct problems stacked:

1. **Content gap** — `ARTICLE_GUIDANCE` had no entry for `"290"`, so synthesis had nothing operative to say beyond "validate the transition regime."
2. **Structural gap** — even with content, the system lacked a planner mode that recognizes the question pattern "what specifically changes pre-X vs vigente" and renders a side-by-side comparison. A senior contador answers this with a 3-row table (plazo, fórmula, reajuste); the generic `article_lookup` synthesis tries to merge two regimes into one prose block and the comparative structure dissolves.

The content gap was patched same-day. The structural gap is what this learning covers.

## The pattern

A generic query-mode classifier that picks one mode by lexical heuristics is fine for the body of queries. But some question classes have a **distinctive cue + a fundamentally different rendering shape** (table vs prose, side-by-side vs sequential, two-anchor vs one-anchor). Forcing those through the generic classifier produces an answer that's technically correct but operatively useless.

The fix: **detect the cue in the planner, BEFORE the standard query-mode classifier runs**, and override `query_mode` when (a) the cue matches AND (b) the system has the data to render the special shape.

```
build_graph_retrieval_plan(request):
  ...
  # Pre-classifier branch — runs BEFORE the standard query_mode classifier
  if comparative_cue_matched AND conversation_state has anchors AND pair lookup hits:
    query_mode = "comparative_regime_chain"
    add comparative_regime_anchor entry_points
  else:
    query_mode = standard_classifier(...)
  ...
```

## The five pieces

1. **Cue detection.** A pure function (`detect_comparative_regime_cue` in `answer_comparative_regime.py`) tests the message against narrow regex patterns: `\b(antes de|anterior a|pre-?)(\d{4})\b`, "qué cambió con la reforma", "régimen de transición". Returns `(matched, cutoff_year)`.

2. **Config-driven pair lookup.** `config/comparative_regime_pairs.json` maps `(domain, cutoff_year) → (current_article, transition_article, transition_numeral, dimensions, verdict, action, risks, supports)`. Adding a new pair is a **config-only change** once the structure is validated by SME. Initial entry: `perdidas_fiscales_2017` (147 ↔ 290 #5, 4 dimensions).

3. **Planner override.** `planner.py:279-319` — when cue matches AND `conversation_state.normative_anchors` has entries AND a pair matches, override `query_mode` to `comparative_regime_chain` and emit two `entry_points` with `source="comparative_regime_anchor"` (current + transition article).

4. **Decomposer-fanout suppression.** `orchestrator.py` — when the parent message itself is comparative, the decomposer should NOT split it across sub-queries (only one would carry the cue). Sets `decomposer_diag["fanout_suppressed_reason"] = "comparative_regime_parent"`. Without this, `LIA_QUERY_DECOMPOSE=on` would split the comparative cue and the special rendering would fire on only one branch.

5. **Assembly route.** `compose_main_chat_answer` short-circuits to `compose_comparative_regime_answer` when `planner_query_mode == "comparative_regime_chain"`. Output: verdict line ("Sí cambia" / "No cambia") + side-by-side markdown table (≥3 rows) + Riesgos + Soportes wrapping below.

## Anti-hallucination companions

A side-by-side table that confidently states wrong things in either column is worse than no table. Two changes shipped alongside the structural fix:

- **`ARTICLE_GUIDANCE["290"]` entry** for numeral 5 (and adjacent numerals as scope expanded). The deterministic synthesis layer now has the right content — the polish layer doesn't get to invent it.
- **Polish prompt rule** in `answer_llm_polish.py`: "preserve markdown tables verbatim, do not reflow into prose; do not invent article descriptions absent from `ARTICLE_GUIDANCE`." The polish layer was the source of the hallucinated "Régimen de transición para la depreciación de activos" line.

**Generalization:** when a deterministic synthesis layer has the right facts, the polish layer must be constrained from inventing context. Add to the polish prompt every time a hallucination is observed.

## When this pattern is the right move

- The question class has a **distinctive lexical cue** that's rare in non-matching queries (false-positive rate < ~5% on the gold).
- The rendering shape is **fundamentally different** from the generic mode (e.g., table vs prose). If a few tweaks to `answer_first_bubble.py` could produce the desired shape, do that instead.
- The data is **deterministically available** when the cue matches — config-driven pair lookup, not an LLM-extracted relationship.
- The cost is **bounded**: a new module, a config file, a planner branch, an assembly route. ~2-3 days end-to-end.

## When this is the wrong move

- The cue is broad and matches many queries that don't need the special shape — false-positive rate dilutes the gain. Either narrow the cue or stay on the generic classifier.
- The data isn't config-driven (e.g., requires runtime LLM extraction). Then it's not really pre-classifier; it's a different planner mode.
- The "fundamentally different shape" turns out to be a section-level tweak. Fix the section, not the mode.

## Future candidate cases (config-only adds when SME validates the structure)

- Depreciación 137-140 ↔ 290 #1-2 (already mentioned in §5; just config + ARTICLE_GUIDANCE)
- Tarifa renta 240 ↔ Ley 2277/2022 transitions
- Pre/post any future tax reform that introduces a transition regime for an existing article

Each is a `config/comparative_regime_pairs.json` entry once SME reviews the dimension set.

## Anti-patterns

- **"Add a new query_mode through the standard classifier."** Defeats the point — the classifier is what dilutes the shape. The pre-classifier branch IS the architecture.
- **"Detect the cue in the synthesizer."** Too late — by then the planner has already anchored the wrong articles and the budget shape is wrong.
- **"Ship the structural fix without ARTICLE_GUIDANCE."** A confident table with hallucinated content is worse than the evasive prose it replaced. Content + structural fixes ship together or not at all.
- **"Forget to suppress decomposer fan-out."** A comparative cue split across sub-queries means one branch fires the special rendering and the other doesn't — the merged answer is incoherent.

## See also

- `docs/aa_next/next_v4.md §5` — the binding case + plan + status
- `docs/orchestration/orchestration.md §3.1` — query mode list with `comparative_regime_chain` at the top
- `docs/orchestration/orchestration.md §6.6b` — the renderer
- `config/comparative_regime_pairs.json` — the pair config; current version `v2026-04-25-v1` with one entry
- `tests/test_phase3_graph_planner_retrieval.py::test_phase3_pipeline_d_comparative_regime_pre2017_followup_renders_table` — the binding regression test
