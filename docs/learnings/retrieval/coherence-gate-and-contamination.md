# Contamination is a retrieval failure, not a classifier failure

**Source:** `docs/next/ingestion_tunningv1.md` §0 I5/I6 findings; commit `60829f0` (v6 phase 3).

## The Q16 biofuel incident

**Question:** "¿Cómo se liquidan las cesantías de un trabajador medio tiempo?" (how are severance payments calculated for a part-time worker — pure labor topic).

**v5 NEW-mode answer:** included a paragraph about **biofuels** sourced from `knowledge_base/CORE ya Arriba/LEYES/OTROS_SECTORIALES/consolidado/Ley-939-2004.md` (Ley 939/2004 Art. 1, "Definición de biocombustibles").

**The naive diagnosis** was "the classifier routed this to the wrong topic." Wrong. The classifier correctly routed Q16 to `laboral` at confidence 1.00. The v5 subtopic override for "trabajador tiempo parcial" even fired correctly.

**The real mechanism** (traced by investigation I5):

1. Classifier routes to `laboral` ✅
2. Primary retriever (falkor/artifacts) returns **zero primary articles** on this query (the graph doesn't have direct article anchors for part-time-labor cesantías)
3. `answer_support.extract_support_doc_insights` falls through to **lexical-overlap chunk scoring with NO topic filter**
4. The Ley 939 biofuel chunk happened to share weak tokens with the query
5. Synthesizer ingested that chunk and dutifully wrote about biofuels

**Root cause:** retrieval fell back silently to a topic-unaware fallback when the graph was empty. Classifier was fine.

## Why a classifier-confidence gate doesn't fix this

Investigation I6 simulated a classifier-confidence refusal gate against all v5 contamination cases:

| Contamination case | Classifier confidence | Would conf-gate catch it? |
|---|---|---|
| Q11 (nota crédito FE → ET 516 timbre) | 1.00 | No |
| Q16 (labor → biofuels) | 1.00 | No |
| Q22 (saldo a favor → cesantías) | 1.00 | No |
| Q27 (SAGRILAFT → ET 148 correction) | 1.00 | No |
| 5th case | 0.67 | Maybe |

Four of five contamination cases had classifier confidence 1.00. A confidence gate catches only the 5th. **The mechanism that catches the real bug must key on evidence composition, not classifier state.**

## The fix: evidence-topic coherence gate

Phase 3 (v6) added `src/lia_graph/pipeline_d/_coherence_gate.py`. Three cases:

- **Case A** — primary articles exist → delegate to the existing `topic_safety.detect_topic_misalignment` (works on primary).
- **Case B** — primary empty, support docs present → score support docs' `topic_key` (first-class metadata) **and** fall back to lexical topic scoring against `title_hint`. Off-topic dominance triggers `reason="chunks_off_topic"`.
- **Case C** — primary empty AND no on-topic support → refuse with `reason="zero_evidence_for_router_topic"`.

Flag-gated via `LIA_EVIDENCE_COHERENCE_GATE={off|shadow|enforce}`, **default `enforce` since 2026-04-25** (was `shadow` until then; flipped per operator's "no off/shadow flags" directive — verification at would-refuse=1/30 is below the [4,12] safe band but still risk-acceptable for internal beta). In `enforce`, the orchestrator short-circuits to a refusal via the shared abstention composer. Watch production refusal-rate; revert to `shadow` if regressions.

Pinned by `tests/test_coherence_gate.py` (7 tests), including the Q16-class case at `test_gate_enforce_chunks_off_topic_refuses`.

## Mental model for which gate you need

| Failure mode | Right gate | Wrong gate |
|---|---|---|
| Classifier confidently picks wrong topic | classifier-confidence gate | evidence-coherence gate (won't fire if retrieval happens to find on-topic content for the wrong topic) |
| Retrieval silently returns off-topic content for right topic | **evidence-coherence gate** | classifier-confidence gate (confidence is 1.00 — gate never fires) |
| Graph missing the domain entirely | both gates fire, composed refusal | partial coverage notice |

## Anti-pattern

"Add a classifier-confidence threshold" — said in response to contamination cases without first auditing what the classifier actually returned. In the v6 cycle this would have shipped a gate that caught 20 % of contamination. Always trace contamination to its source before picking a mechanism.

## See also

- `docs/next/ingestion_tunningv1.md` §0 I5 (trace) and I6 (simulation).
- `src/lia_graph/pipeline_d/_coherence_gate.py` — the primitives.
- `src/lia_graph/pipeline_d/topic_safety.py` — the pre-existing gate this complements.
