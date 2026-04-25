# next_v4 — forward plan after the 2026-04-25 gate-9 qualitative-pass

> **Opened 2026-04-25** when the operator accepted gate-9 on qualitative basis (see `gate_9_threshold_decision.md` §7). next_v4 inherits one explicitly-scoped item from gate-9's deferred debt and otherwise stays open until next_v3 closes (re-flip ships once gate 8 also clears).
>
> **Policy (carries from next_v3).** Every item below uses the mandatory six-gate lifecycle per `docs/aa_next/README.md`: 💡 idea → 🛠 code landed → 🧪 verified locally → ✅ verified in target env → ↩ regressed-discarded.

---

## §1 Coherence-gate calibration diagnostic (operator-scoped 2026-04-25)

### Idea (operator's words, binding)

> Determine whether the 11 `coherence_misaligned=True` questions concentrate in topics with thin corpus coverage, or distribute across topics evenly. If concentrated → the fix is corpus expansion (free as `corpus_coverage: pending` topics fill in per `next_v3 §10.5`). If distributed → the fix is coherence-gate recalibration (a real engineering intervention). **Diagnose before intervening.**

### Measurement set (binding)

The 11 questions from v10_taxonomy_v2_rebuild5_clean (2026-04-25) where the v6 evidence-coherence gate rejected retrieval despite correct topic routing:

| qid | expected_topic | corpus_coverage flag (taxonomy v2) |
|---|---|---|
| Q12 | regimen_simple | active |
| Q18 | estados_financieros_niif | **deprecated** (v2 split into niif_pymes/plenas/microempresas) |
| Q20 | regimen_sancionatorio | active |
| Q21 | firmeza_declaraciones | active |
| Q22 | devoluciones_saldos_a_favor | active |
| Q23 | informacion_exogena | active |
| Q25 | impuesto_patrimonio_personas_naturales | active |
| Q26 | dividendos_y_distribucion_utilidades | active |
| Q27 | sagrilaft_ptee | active |
| Q28 | zonas_francas | active |
| Q29 | perdidas_fiscales_art147 | active |

Q10 (`facturacion_electronica` routing-fail) is **not in this set** — tracked separately as a vocabulary-gap line item, not a coherence-gate concern.

### Early signal — concentration hypothesis already weakened

10 of 11 measurement-set topics carry `corpus_coverage: active` in the taxonomy. Only Q18 maps to a `deprecated` topic (because v2 split `estados_financieros_niif` into the three NIIF buckets — those rows likely route to one of the splits depending on resolver behavior). **The "concentrate in thin-corpus topics" hypothesis is not supported by the metadata flag alone** — the rejections look distributed across topics that are flagged as actively covered.

But `corpus_coverage: active` is a binary flag, not a density measurement. The diagnostic still has to measure:

- Article/chunk count per topic (Supabase `documents` + `document_chunks` filtered by topic).
- Article-text vs query-text alignment characterization (sample 2-3 of the rejected (query, chunk) pairs per topic and inspect whether the chunks really are off-topic from a contador's perspective, or whether the gate is over-triggering on legitimate matches).
- Coherence-gate scoring distribution per topic (does the gate threshold sit at the same percentile across topics, or does it accidentally cut more strictly in some topics due to embedding-space topology?).

### Plan (when it ships)

1. **Density audit.** Per topic in the measurement set: count documents + chunks in production Supabase. If any topic has < 50 chunks, it functionally has thin coverage regardless of the `active` flag — that's a corpus-expansion problem, not a gate problem.
2. **Sample-pair inspection.** For each of the 11 rejected (qid, retrieved_chunks) pairs in v10's run output, surface 2-3 chunks the gate dropped + 2-3 it admitted (if any). Have engineering + SME read 5-10 minutes per qid and verdict each chunk *as a contador would*: actually-off-topic, marginally-related, or wrongly-rejected. Aggregate.
3. **Gate-score distribution.** Add instrumentation that emits the actual coherence score per chunk (currently we only see the `misaligned/aligned` boolean and the `chunks_off_topic` reason string). Recompute the rejection rate per topic at the current threshold + at threshold ± 0.05 / ± 0.10.

The combination of (1), (2), and (3) is the diagnostic. Only after it lands does the team decide between corpus expansion (per-topic), gate-threshold tuning (per-topic or global), or both.

### Success criterion

Diagnostic produces a per-topic verdict: `{thin_corpus, gate_overstrict, both, neither}` with numeric backing for each. Output is a markdown table the operator can act on.

### What this is NOT

- **Not a generic "retrieval-depth lift"** — the operator explicitly rejected that framing on 2026-04-25.
- **Not gate-loosening** — the gate exists to keep contamination clean (Q22 + Q27 in the contamination-test set are themselves part of the measurement set, both with primary=0 + coh_misaligned=True; aggressive gate-loosening would re-introduce contamination).
- **Not a re-flip prerequisite** — gate 9 is already qualitative-✅ in next_v3. v4 §1 is debt repayment, not a re-flip blocker.

### Effort

Diagnostic: ~1-2 days engineering for instrumentation (chunk-level coherence scores) + ~3-5 hours operator/SME chunk-pair inspection + ~half day for the per-topic verdict aggregation. Intervention (whatever the diagnostic recommends): scoped after the diagnostic lands.

### Six-gate status

💡 idea (operator-scoped 2026-04-25) — code not yet started, awaiting next_v3 close.

---

## §2 Carries from next_v3 §10 (parallel tracks, soft gates)

These do not block re-flip but ship in this cycle when there's bandwidth:

- **§10.1 TokenBudget primitive** — wire `TokenBudget` + `TPMRateLimitError` into `ingest_classifier_pool`. Lets workers default come back to 8 against production. ~4-6 hr code + cloud verify.
- **§10.2 Persistent verdict cache** — SQLite-keyed cache for classifier verdicts (read-before-call, write-after-call). Drops idempotent rebuilds from ~7 min → < 60 s. Critical for fast iteration on next-cycle prompt work. ~2 days.
- **§10.3 Gold v2 expansion** — commission ≥ 10-15 additional questions from SME post-taxonomy-v2 stabilization. ~1-2 weeks SME.
- **§10.4 Subtopic taxonomy refresh** — v2.1 SME pass on subtopics under the new top-level topics (`impuesto_timbre`, `rut_y_responsabilidades_tributarias`). ~0.5 day SME + 0.5 day code.
- **§10.5 Corpus expansion** — fill the 11 `corpus_coverage: pending` top-level topics (proteccion_datos, regimen_cambiario, NIIF splits, etc.) from canonical sources. ~2-4 weeks SME + content team. **Note: §1 above may surface specific measurement-set topics that need expansion regardless of their current `pending`/`active` flag.**

---

## §3 What's NOT here (deliberately)

- Re-flip mechanics — those belong in `next_v3.md §13.10.7` item 3 and ship the moment SME closes gate 8.
- Anything that reopens settled six-gate decisions without new evidence.
- Generic "retrieval-depth lift" framings — the operator scoped v4 §1 specifically; honor the scope.

---

*Opened 2026-04-25 after operator's qualitative-pass on gate 9 with explicit scoping for the deferred debt. See `gate_9_threshold_decision.md` §7 for the binding decision record and `next_v3.md §13.10.8` for the cross-reference.*
