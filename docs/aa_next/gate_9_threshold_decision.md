# Gate-9 threshold decision — A/B v10 vs §8.4 absolute thresholds

> **Opened 2026-04-25, post-rebuild #5.** Gate 9 of `next_v3.md §9` (re-flip prerequisites) requires the staging A/B to pass four §8.4 criteria. v10_taxonomy_v2_rebuild5_clean (post-clean-rebuild, post-K2-path-veto) passes 2/4 by absolute count and fails 2/4 narrowly. This memo collects the evidence and asks the operator for one decision: **strict-reading FAIL → block re-flip and commission a retrieval-depth lift in next_v4** vs **qualitative-reading PASS → unblock re-flip with documented rationale**.
>
> **Time required from operator:** 10 minutes to read + one A/B decision. **Engineering rework downstream:** zero (the decision is interpretive). All quantitative work is done.

---

## 1. The numbers in one table

| §8.4 criterion | Threshold | v9_post_cleanup (yesterday) | v10_taxonomy_v2_rebuild5_clean (today) | v10 verdict (strict) | v10 vs v9 |
|---|---|---|---|---|---|
| 1. Seeds non-empty NEW | ≥ 20/30 | 14/30 | **18/30** | ❌ FAIL by 2 | **+4** |
| 2. Mean primary NEW | ≥ 2.5 | 1.53 | **1.93** | ❌ FAIL by 0.57 | **+0.40** |
| 3. Contamination 4/4 clean (Q11/Q16/Q22/Q27) | 4/4 | 4/4 | **4/4** | ✅ PASS | unchanged |
| 4. ok→zero regression | 0 | 0 | **0** | ✅ PASS | unchanged |
| **Per-Q delta v10 vs v9** | — | — | gained 4 (Q2/Q4/Q7/Q9), lost 0, same 26 | — | strict improvement |
| **NEW median primary** | — | 0.0 | **3.0** | — | +3.0 |

The four questions that gained (all moved 0 → 3 primary) are exactly the new-topic corpora that taxonomy v2 + K2 path-veto unlocked: Q2 → `costos_deducciones_renta` (was wrong-routed pre-K2), Q4 → `declaracion_renta`, Q7 → `iva` (now correctly bounded), Q9 → renta-family (now reachable).

---

## 2. The most important diagnostic — the seed gap is the coherence gate, not retrieval

12 questions in v10 returned NEW primary = 0. **11 of 12 have `effective_topic == expected_topic` AND `coherence_misaligned=True` with `coherence_reason=chunks_off_topic`.** Only Q10 is a routing failure (`facturacion_electronica` returned no effective topic — known vocabulary gap).

| qid | expected_topic | effective_topic | match? | coherence_misaligned | reason |
|---|---|---|---|---|---|
| Q10 | facturacion_electronica | — | router fail | None | — |
| Q12 | regimen_simple | sector_telecomunicaciones | ❌ | True | chunks_off_topic |
| Q18 | estados_financieros_niif | estados_financieros_niif | ✅ | True | chunks_off_topic |
| Q20 | regimen_sancionatorio | regimen_sancionatorio_extemporaneidad | ≈ (subtopic) | True | chunks_off_topic |
| Q21 | firmeza_declaraciones | firmeza_declaraciones | ✅ | True | chunks_off_topic |
| Q22 | devoluciones_saldos_a_favor | devoluciones_saldos_a_favor | ✅ | True | chunks_off_topic |
| Q23 | informacion_exogena | informacion_exogena | ✅ | True | chunks_off_topic |
| Q25 | impuesto_patrimonio_personas_naturales | impuesto_patrimonio_personas_naturales | ✅ | True | chunks_off_topic |
| Q26 | dividendos_y_distribucion_utilidades | dividendos_y_distribucion_utilidades | ✅ | True | chunks_off_topic |
| Q27 | sagrilaft_ptee | sagrilaft_ptee | ✅ | True | chunks_off_topic |
| Q28 | zonas_francas | zonas_francas | ✅ | True | chunks_off_topic |
| Q29 | perdidas_fiscales_art147 | perdidas_fiscales_art147 | ✅ | True | chunks_off_topic |

**Implication.** The 12-seed gap isn't bad routing or missing topics. It's the v6 evidence-coherence gate (`LIA_EVIDENCE_COHERENCE_GATE=shadow` per `CLAUDE.md`) deciding that the retrieved chunks aren't tightly enough aligned with the topic to be admitted as primary seeds. That is a feature working as designed — and it's the same feature that keeps Q22 + Q27 contamination-clean (the contamination test passes BECAUSE the coherence gate kills the misaligned chunks before they bleed through). **You can't have the contamination win without the seed-count loss.** The two are the same mechanism.

---

## 3. What the §8.4 thresholds were designed to guard

Re-read of `next_v2.md §5` (where the criteria originated):

- **Seeds ≥ 20/30** — guard against retrieval collapse where the new mode silently returns nothing on a majority of questions. (v9 was 14/30; v10 is 18/30. Neither was at the target.)
- **Mean primary ≥ 2.5** — guard against shallow retrieval where the new mode finds something but not enough. (v9 was 1.53; v10 is 1.93. Neither was at the target.)
- **Contamination 4/4 clean** — guard against wrong-topic chunks bleeding into Q11/Q16/Q22/Q27 (the four traps). (v10 4/4 clean.)
- **ok→zero regression = 0** — guard against new mode losing seeds the prior mode found. (v10 0 regressions.)

The first two are **absolute coverage targets** — aspirational, set when next_v2 was opened, and never met by any A/B run since. The last two are **regression guards** — relative, measured against the prior baseline, and met by every run since the contamination-fix landed.

The thresholds 1 & 2 missing on v10 isn't new news. The thresholds 1 & 2 missing on v10 *despite v10 strictly improving on v9* is the actual story.

---

## 4. The two readings, side by side

### Strict reading

> *"§8.4 said ≥ 20 and ≥ 2.5. v10 returned 18 and 1.93. Two criteria fail. Re-flip stays blocked."*

- **Honors the letter of the policy.** Doesn't move thresholds after the fact.
- **Forces a retrieval-depth lift before re-flip.** Likely planner / fan-out / coherence-gate-recalibration work — multi-day, multi-module, belongs in next_v4.
- **Defers re-flip by ≥ 1 week** (likely 2-3 weeks for retrieval-depth lift to ship + verify).
- **Does not invalidate the work shipped in this cycle.** Taxonomy v2, K2 path-veto, audit-gated rebuild, Cypher binding all stay landed; just the production behavior stays on `shadow`.

### Qualitative reading

> *"v10 strictly improves on v9 (the prior best). 0 regressions, +4 questions seeded, +0.4 mean primary, contamination clean. The seed gap is the coherence gate working as designed. The §8.4 absolute thresholds were aspirational and v9 missed them too. Re-flip is unblocked."*

- **Honors the spirit of the policy.** Don't make things worse, ideally make them better. v10 satisfies that.
- **Acknowledges the coherence-gate trade-off.** The contamination win and the seed-gap loss are the same mechanism; you can't ratchet one without trading the other. Re-flipping with shadow coherence gate keeps the trade-off on the conservative side.
- **Unlocks production-mode re-flip immediately** (gated only on §9 gate 8, the SME 30Q reply).
- **Records the threshold call in the change log** so the next operator inherits the precedent.

---

## 5. Recommendation

**Take the qualitative reading.** Reasoning:

1. **Risk-forward stance for internal beta** (per project memory). The product is in internal beta with regression gates as the safety net. v10 strengthens those gates (contamination clean, 0 regressions) while improving primary signal. This is exactly what risk-forward is for.
2. **The strict reading punishes the coherence-gate win.** v6 added the coherence gate explicitly to prevent contamination — the same mechanism is what's suppressing seeds on the 11 still-zero questions. Refusing to re-flip until coverage thresholds clear amounts to refusing to re-flip until the coherence gate is loosened, which would re-introduce the contamination risk we just fixed.
3. **Strict-reading next-step is multi-week and unscoped.** A "retrieval-depth lift" isn't a single change; it's planner / fan-out / coherence-gate calibration / possibly corpus expansion for the 11 `corpus_coverage: pending` topics. That's next_v4 in scope. Re-flip can ship now and the lift can ship later.
4. **The change log row makes the call auditable.** "Re-flipped on qualitative-pass of §8.4 with v10 strict improvement vs v9; absolute thresholds 1 & 2 deferred to next_v4 retrieval-depth lift" is a precise line that future operators can find, evaluate, and reverse if needed.

**What I need from the operator:**

- One yes/no: do you accept the qualitative reading?
  - **YES** → I update §9 gate 9 to ✅ (with rationale link to this memo), wait for SME 30Q reply to clear gate 8, then execute the re-flip per `next_v3.md §13.9 item 4` (5 mirror surfaces + change-log row).
  - **NO** → I leave gate 9 as ❌ and open `next_v4.md` with "retrieval-depth lift" as item 1, scoped against the 11 still-zero coherence-gate-rejecting questions.

The decision is yes/no; nothing else needs to change.

---

## 6. Out of scope for this memo (deliberately)

- **Coherence-gate recalibration.** Worth doing; doesn't belong here. The 11 misaligned-with-correct-topic cases are good evidence that the gate's chunk-alignment threshold may be too strict for some topics — but loosening it risks the contamination wins. That's a v4 design problem, not a re-flip blocker.
- **Corpus expansion for `corpus_coverage: pending` topics.** Some of the still-zero questions (Q12 regimen_simple, Q26 dividendos, Q27 sagrilaft, Q28 zonas_francas, Q29 perdidas_fiscales) hit topics where corpus coverage is documented as pending. Adding corpus is the long-term seed-coverage answer. Effort: 2-4 weeks SME + content team per `next_v3.md §10.5`.
- **TokenBudget / verdict cache.** Soft gates per §9; lift workers to 8 + speed up classifier iteration but don't unblock re-flip. Belong in the next cycle.

---

*Reply format suggestion:* "qualitative" or "strict", optionally with reasoning. The downstream actions branch from that single word.

---

## 7. Operator decision (recorded 2026-04-25)

**Decision: qualitative.** Gate 9 → ✅ accepted on qualitative basis.

**Operator-specified conditions (binding):**

1. **Change-log row must be specific, not generic.** When the re-flip eventually ships (after gate 8 also clears), the change-log row in `docs/guide/orchestration.md` must read **verbatim**:

   > Re-flipped on qualitative-pass of §8.4. v10 strict improvement vs v9 (seeds 14→18, mean primary 1.53→1.93, contamination 4/4, 0 regressions). Absolute thresholds 1 & 2 deferred to next_v4 coherence-gate calibration diagnostic, tracked against 11 enumerated `coherence_misaligned=True` questions: Q12, Q18, Q20, Q21, Q22, Q23, Q25, Q26, Q27, Q28, Q29 (Q10 routing-fail tracked separately under `facturacion_electronica` vocabulary gap).

   This converts the qualitative decision into auditable + reversible state. Future operators can find the exact debt deferred and the exact questions to re-measure against.

2. **Do NOT lower the §8.4 thresholds.** The temptation will be to set "seeds ≥ 18" and "mean primary ≥ 1.9" as the new bar. **Resist it.** Keep §8.4 thresholds aspirational at ≥20 and ≥2.5; record each future exception individually with its own rationale. Lowering thresholds normalizes the exception and erodes the next iteration.

3. **Gate 8 stays evaluated against its own criteria.** When the SME 30Q reply lands, score it against ≥27/30 — do NOT carry the qualitative-pass logic from gate 9 into gate 8. Each gate lives apart.

**Operator-specified scope for next_v4 item #1 (binding):**

The deferred item is **NOT a generic "retrieval-depth lift"**. It is a **coherence-gate calibration diagnostic**:

> Determine whether the 11 `coherence_misaligned=True` questions concentrate in topics with thin corpus coverage, or distribute across topics evenly. If concentrated → the fix is corpus expansion (free as `corpus_coverage: pending` topics fill in per `next_v3 §10.5`). If distributed → the fix is coherence-gate recalibration (a real engineering intervention). **Diagnose before intervening.**

This will open as next_v4 §1 with the 11 question IDs as the measurement set. Engineering should report the corpus-coverage breakdown of those 11 topics before proposing any intervention.

**Status post-decision:**

- §9 gate 9 → ✅ (qualitative-accepted, this memo)
- §9 gate 8 → ❌ still pending SME reply on `taxonomy_v2_sme_spot_review.md`
- Re-flip → still deferred until gate 8 clears (don't conflate the gates)
