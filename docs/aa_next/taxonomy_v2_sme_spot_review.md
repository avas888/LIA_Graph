# Taxonomy v2 — SME spot-review (7 questions to clear gate 8)

> **Opened 2026-04-25.** Follow-up to `taxonomy_v2_sme_response.md`. After landing taxonomy v2 + the taxonomy-aware classifier prompt + the path-veto layer (K2), the SME 30-question validation suite scored **23/30**. The re-flip threshold is **≥ 27/30** (next_v3.md §6). Of the 7 failures, **all seven are router/query-side decisions** — they don't require another classifier rebuild. Five of them need a single SME yes/no; two are gold-file boundary clarifications.
>
> **Time required from SME:** ~30 minutes. **Engineering rework after SME reply:** ~1 hour (gold edits + one prompt patch + a re-run of `make eval-taxonomy-v2`). If the answers come back as recommended, **23/30 → 28/30** and §9 gate 8 clears.

---

## 1. Context for the SME

The 30-question validation suite is engineering's way of asking *"would a contador asking these questions land on the right topic in Lia?"* For each question, we measure the topic the resolver picks against the topic the SME originally said was correct. 23 hit. 7 missed. The 7 misses fall into three categories:

| Category | Count | What's broken |
|---|---|---|
| **Default-to-parent over-correction** | 2 (q10, q16) | The classifier prompt has a "if multiple subtopics under one parent could match, return the parent" rule. For two highly distinctive subtopics (`firmeza_declaraciones`, `beneficio_auditoria`), the rule fires when it shouldn't. |
| **v1/v2 topic collision** | 1 (q15) | The SME spec renamed `anticipos_retenciones_a_favor` → `retencion_fuente_general`, but the v1 topic `retencion_en_la_fuente` was never explicitly deprecated. Both are still active and both plausibly match the same query. |
| **Mutex rule wording** | 1 (q26) | The SME's mutex rule "IVA → never if procedimiento" is in the prompt as a hard constraint, but the LLM didn't apply it on a query that named "declaración de IVA" + "emplazamiento". Stronger wording may fix it. |
| **Genuinely ambiguous** | 3 (q13, q14, q28) | The questions sit on real topic boundaries the v2 spec didn't explicitly resolve. The fix is to widen the gold's `ambiguous_acceptable` field so either answer counts. |

For each question below: the SME picks the option (A, B, or C) that best matches contador-practice intent. Engineering applies the choice mechanically.

---

## 2. The 7 questions

Each subsection has the same shape: query verbatim → expected vs got → category → SME decision needed → recommended option.

### q10 · Default-to-parent over-correction

> **Q (verbatim):** *"¿Cuándo prescribe la facultad de la DIAN de cuestionar mi declaración de renta?"*

| | |
|---|---|
| Expected topic | `firmeza_declaraciones` |
| Got | `declaracion_renta` |
| Why it failed | The default-to-parent rule fired — `firmeza_declaraciones` and `declaracion_renta` are both renta-family, and the LLM defaulted to the parent. |

**SME decision needed:** Is `firmeza_declaraciones` a topic that contadores ask about *by name* (i.e., they say "firmeza" or "prescribe"), or is it a sub-concept they'd reach by browsing inside `declaracion_renta`?

| Option | Engineering action |
|---|---|
| **A. Yes — `firmeza` is a stand-alone contador concern.** *(recommended — query uses "prescribe", which is firmeza vocabulary)* | Add `firmeza_declaraciones` to the prompt's "do not collapse to parent" exception list. Re-run 30Q. |
| B. No — `declaracion_renta` parent is fine. | Add `declaracion_renta` to `ambiguous_acceptable` for q10 in the gold file. Counts as a hit on re-run. |

---

### q13 · Genuinely ambiguous (renta presuntiva vs patrimonio)

> **Q (verbatim):** *"El patrimonio líquido es muy alto pero la operación dio pérdida, ¿qué pasa con la renta presuntiva?"*

| | |
|---|---|
| Expected topic | `renta_presuntiva` |
| Got | `impuesto_patrimonio_personas_naturales` |
| Why it failed | The query names "patrimonio líquido" prominently; the classifier latched onto the patrimonio topic. Both topics legitimately touch this question. |

**SME decision needed:** When a contador asks "patrimonio líquido alto + pérdida → renta presuntiva", is the answer they need primarily in `renta_presuntiva` doctrine, or do they also need patrimonio context?

| Option | Engineering action |
|---|---|
| **A. Both are acceptable — accept either topic.** *(recommended)* | Add `impuesto_patrimonio_personas_naturales` to `ambiguous_acceptable` for q13. |
| B. Only `renta_presuntiva` is correct. | Strengthen the mutex rule: "renta presuntiva is always renta_presuntiva, never patrimonio". Re-test. |

---

### q14 · Genuinely ambiguous (descuento del IVA vs descuentos renta)

> **Q (verbatim):** *"Mi cliente compró maquinaria nueva en 2025, ¿le sirve el descuento del IVA en bienes de capital?"*

| | |
|---|---|
| Expected topic | `descuentos_tributarios_renta` |
| Got | `iva` |
| Why it failed | The query literally says "descuento del IVA". The classifier sees "IVA" as a magnet. SME's intent: this is a renta-side descuento mechanism (ET art. 258-1). |

**SME decision needed:** "Descuento del IVA en bienes de capital" — when a contador asks this, are they expecting (a) IVA mechanics, (b) renta-discount mechanics, or (c) both?

| Option | Engineering action |
|---|---|
| **A. Renta-discount only — `iva` is wrong.** | Add a mutex rule: "`descuento del IVA en bienes de capital` is always `descuentos_tributarios_renta`, never `iva`". |
| **B. Both topics are acceptable** *(recommended — the contador may need both halves)* | Add `iva` to `ambiguous_acceptable` for q14. |

---

### q15 · v1/v2 topic collision

> **Q (verbatim):** *"Soy nuevo agente retenedor en la fuente, ¿cómo presento mi primer formulario?"*

| | |
|---|---|
| Expected topic | `retencion_fuente_general` (v2 rename of `anticipos_retenciones_a_favor`) |
| Got | `retencion_en_la_fuente` (v1 topic — never deprecated by SME spec) |
| Why it failed | Both topics are active and both legitimately cover ET arts. 365–419. SME spec didn't explicitly say which to keep. |

**SME decision needed:** This is the one question that needs a structural call. Two topic keys both claim "retención en la fuente":

- **`retencion_en_la_fuente`** — original v1 topic. Broader scope.
- **`retencion_fuente_general`** — v2 rename of `anticipos_retenciones_a_favor`. Narrower (ET 365–419 retenciones from the agent's perspective).

| Option | Engineering action |
|---|---|
| **A. Deprecate `retencion_en_la_fuente`; keep `retencion_fuente_general` as canonical.** *(recommended — narrower scope is more usable for retrieval)* | Mark v1 key `status: deprecated`, `merged_into: ["retencion_fuente_general"]`. Update gold accordingly. |
| B. Keep `retencion_en_la_fuente`; treat `retencion_fuente_general` as a subtopic of it. | Demote the v2 key to subtopic; update gold accordingly. |
| C. Keep both with a clear scope_out boundary. | Add `scope_out` text to each topic naming the other; SME drafts the boundary in 1–2 sentences. |

---

### q16 · Default-to-parent over-correction

> **Q (verbatim):** *"¿Le aplica el beneficio de auditoría a un cliente con pérdida fiscal?"*

| | |
|---|---|
| Expected topic | `beneficio_auditoria` |
| Got | `declaracion_renta` |
| Why it failed | Same pattern as q10 — `beneficio_auditoria` is a subtopic-style concept under renta; the parent default fired. The query uses the topic name verbatim ("beneficio de auditoría"), so the contador clearly asked for it by name. |

**SME decision needed:** Same as q10. Is `beneficio_auditoria` a stand-alone contador concern?

| Option | Engineering action |
|---|---|
| **A. Yes — `beneficio_auditoria` is asked by name.** *(recommended — query is verbatim)* | Add to the prompt's "do not collapse to parent" exception list (combined with q10's). |
| B. No — `declaracion_renta` parent is fine. | Add to `ambiguous_acceptable` for q16. |

---

### q26 · Mutex rule wording (IVA-vs-procedimiento)

> **Q (verbatim):** *"Llegó un emplazamiento para corregir la declaración de IVA, ¿qué hago?"*

| | |
|---|---|
| Expected topic | `procedimiento_tributario` |
| Got | `iva` |
| Why it failed | The SME's mutex rule "IVA → never if procedimiento" is in the prompt as a HARD constraint, but the LLM saw "declaración de IVA" and overrode the rule with substantive bias. The classifier needs stronger wording. |

**SME decision needed:** Is the LLM's call defensible (the question is about an IVA declaration, after all), or is the procedural-tax classification non-negotiable?

| Option | Engineering action |
|---|---|
| **A. Non-negotiable — emplazamiento is always `procedimiento_tributario`.** *(recommended — emplazamiento is SME's named procedural artifact)* | Strengthen the prompt: "If the query mentions any of {emplazamiento, requerimiento especial, liquidación oficial, sanción}, the topic is **ALWAYS** `procedimiento_tributario`, regardless of which substantive tax (renta/IVA/ICA) is being corrected." Re-test. |
| B. IVA is acceptable here too. | Add `iva` to `ambiguous_acceptable` for q26. |

---

### q28 · Genuinely ambiguous (zona franca tariff vs general renta tariff)

> **Q (verbatim):** *"¿Cuál es la tarifa del impuesto si la sociedad está en zona franca?"*

| | |
|---|---|
| Expected topic | `tarifas_renta_y_ttd` |
| Got | `zonas_francas` |
| Why it failed | The query is a tarifa question scoped to zona franca. Both topics legitimately apply — `zonas_francas` is the regime, `tarifas_renta_y_ttd` is the rate. |

**SME decision needed:** When a contador asks "tarifa de zona franca", do they get more value from regime context or rate context?

| Option | Engineering action |
|---|---|
| **A. Both acceptable — accept either.** *(recommended)* | Add `zonas_francas` to `ambiguous_acceptable` for q28. |
| B. Only `tarifas_renta_y_ttd` (the rate is what they need). | Strengthen mutex: "tarifa questions are always `tarifas_renta_y_ttd`, even when scoped to a regime". |

---

## 3. Summary of decisions needed

| qid | Decision | Recommended | Effort to apply |
|---|---|---|---|
| q10 | Should `firmeza_declaraciones` resist default-to-parent? | A (yes) | 1 prompt edit |
| q13 | Is `impuesto_patrimonio_personas_naturales` acceptable for the renta-presuntiva-with-patrimonio question? | A (yes, both acceptable) | 1 gold edit |
| q14 | Are both `descuentos_tributarios_renta` and `iva` acceptable for "descuento del IVA en bienes de capital"? | B (yes, both acceptable) | 1 gold edit |
| q15 | What's the canonical key for "retención en la fuente"? | A (keep `retencion_fuente_general`, deprecate v1) | 1 taxonomy edit + 1 gold edit |
| q16 | Should `beneficio_auditoria` resist default-to-parent? | A (yes) | bundled with q10 |
| q26 | Is "emplazamiento" always `procedimiento_tributario`? | A (yes) | 1 prompt edit |
| q28 | Is `zonas_francas` acceptable for the zona-franca-tariff question? | A (yes) | 1 gold edit |

If the SME picks all the **recommended** options, the projected scoreboard is **28/30** (gold widening for q13/q14/q28 + prompt patches for q10/q16/q26 + taxonomy decision for q15). That clears the ≥ 27/30 threshold and unblocks §9 gate 8 — the last remaining hard gate before TEMA-first re-flip.

---

## 4. What happens after the SME replies

1. Engineering applies the 7 decisions mechanically — no SME re-validation needed for the application step itself.
2. Re-run `make eval-taxonomy-v2`. Decision rule: ≥ 27/30 chat-resolver = greenlight; < 25 = back to prompt iteration; 25–26 = one more SME spot-review on whatever's still failing.
3. If greenlight: bump §9 gate 8 to ✅, run the post-clean-rebuild Cypher verify (expected 6/6 — already passing post-K2), re-run the 30-question A/B against the clean rebuild, then re-flip `LIA_TEMA_FIRST_RETRIEVAL` to `on` if A/B passes the four criteria (next_v3 §8.4).

The taxonomy v2 + path-veto + (this) SME spot-review is the entire remaining critical path. After this, next_v4 becomes about retrieval-depth lift + corpus expansion for the 11 `corpus_coverage: pending` topics — not foundation fixes.

---

*Reply format suggestion:* a single message naming each qid and a letter (e.g. *"q10:A, q13:A, q14:B, q15:A, q16:A, q26:A, q28:A"*) is enough. Free-text caveats welcome on any item.
