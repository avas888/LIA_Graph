# Router-LLM deferral architecture

> **Captured 2026-04-25** at the close of the next_v3 cycle, after a session that moved gate-8 from 23/30 → 30/30 and surfaced the structural pattern below. Code lives in `src/lia_graph/topic_router.py` (`_should_defer_to_llm` + `_LLM_DEFERRAL_PHRASES` + `_MAGNET_TOPICS`).

## The problem this solves

A RAG topic resolver typically has two layers: a **fast lexical router** (keyword-bucket scoring) and a **slow LLM classifier** with rich heuristics (mutex rules, scope_in/scope_out, meta-rules like "operates not defines"). The natural design is "router runs first; LLM only when router is uncertain". That design has a failure mode that's invisible until you look for it:

**The router returns a "dominant" lexical match for a query whose right answer requires the LLM's heuristics. The LLM never runs. Wrong topic ships.**

We hit this on 6 of 7 SME spot-review failures. In every case the router's lexical signal was strong, but Alejandro's domain heuristics said the answer was elsewhere. The LLM had the right rules in its prompt; it just wasn't being called.

## The pattern this generalizes

Three failure classes that all share the shape *"router has lexical confidence but the right answer needs LLM reasoning"*:

| Class | Pattern | Mitigation |
|---|---|---|
| **Magnet-topic capture** | Query mentions a topic verbatim; answer operates elsewhere ("descuento del IVA en bienes de capital" → renta-side, not IVA) | `_MAGNET_TOPICS` set + relaxed competing-strong check |
| **Subtopic-by-name vs parent-as-default** | Query uses distinctive subtopic vocabulary; router prefers parent ("prescribe la facultad" → firmeza, router went to declaracion_renta) | Either extend the subtopic's keyword bucket OR use trigger-phrase deferral |
| **Comparative-tension** | Two quantities in tension; answer operates on the comparison ("patrimonio alto pero pérdida → presuntiva") | Trigger-phrase deferral on " pero ", " aunque ", etc. |

## The intervention

Three independent gates in `_should_defer_to_llm`. Each fires on a different signal; any True forces LLM deferral *even when the router would otherwise have returned a dominant match*.

| Gate | Signal | When to use |
|---|---|---|
| 1. Trigger phrase | Curated `_LLM_DEFERRAL_PHRASES` list — Spanish (or your domain language) phrases that signal "the LLM heuristic should arbitrate" | Add a phrase only when a new failure class surfaces. Per-question fixes go in keyword buckets, not here. |
| 2. Magnet + competing strong | Top topic ∈ `_MAGNET_TOPICS` AND second bucket has any strong hit | Add a topic to MAGNET only after post-hoc analysis shows it over-attracts in production logs |
| 3. Competing dominantly | Second bucket has score≥3 AND strong hits | The structural-ambiguity safety net — fires when 2+ buckets compete on lexical strength |

Both registries are intentionally short (~25 phrases, ~7 magnet topics). The goal is to capture **classes**, not enumerate every phrase.

## Why this is better than the alternatives

| Alternative | Why we didn't pick it |
|---|---|
| Just call LLM for every query | Cost + latency on every chat. Defeats the point of the router. |
| Per-question keyword fixes (extend the bucket each time) | Doesn't generalize. Ships SME-bandwidth-bound work that compounds with corpus growth. |
| Lower router dominance threshold | Knock-on effects on every other query. Hard to reason about. |
| Move heuristics into the router (mutex rules in keyword scoring) | Embeds slow-changing domain knowledge in fast-changing infrastructure. The LLM is the right home for "operates not defines" type reasoning. |

The deferral approach keeps the router fast on the easy cases (most queries) and routes the hard cases to the LLM with full context. Marginal cost: ~10-20% extra LLM calls in production based on phrase frequency. With Gemini Flash that's negligible.

## Extension policy

When you hit a new SME spot-review failure:

1. **First instinct should NOT be `_LLM_DEFERRAL_PHRASES`.** Most question-specific failures are best fixed by extending the matching keyword bucket — that's surgical and cheap.
2. **Trigger-phrase deferral is for failure CLASSES.** If you can describe the failure in one sentence that covers ≥3 plausible queries (not just the one that failed), it's a class — add to `_LLM_DEFERRAL_PHRASES`.
3. **`_MAGNET_TOPICS` requires evidence.** Don't add a topic to MAGNET on a single failure. Look at production logs (or the eval set) and confirm the topic over-attracts on multiple distinct queries.

Both registries should stay below ~50 entries. If you find yourself needing a longer list, the right move is probably an LLM-driven topic classifier as the primary path with the router as a hot-cache, not bigger registries.

## Cross-references

- `src/lia_graph/topic_router.py` — `_should_defer_to_llm` docstring + the registries
- `src/lia_graph/topic_router_keywords.py` — bucket-level keyword config (per-question fixes go here)
- `docs/learnings/retrieval/operates-not-defines-heuristic.md` — the meta-rule the LLM applies once it gets a chance
- `docs/aa_next/done/next_v3.md §13.11.1` — the close-out execution log + cost analysis
