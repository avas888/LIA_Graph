# The corpus contains hallucinated content with verification stamps

**Source:** Activity 1.5 outcome (`docs/re-engineer/activity_1_5_outcome.md`) — vigencia-checker skill protocol applied manually to Decreto 1474/2025 on 2026-04-26 evening. Veredicto fixture at `evals/activity_1_5/decreto_1474_2025_veredicto.json`.

## What we found

The corpus document `knowledge_base/CORE ya Arriba/EMERGENCIA_TRIBUTARIA_2026/NORMATIVA/EME-A01-addendum-estado-actual-decretos-1474-240-2026.md` claims:

- Decreto 1474/2025 was expedited **"julio 2025"**
- It was modified by **"Sentencia C-077/2025"** of November 2025
- 18 articles were declared inexequible; 23 remain vigente (PARTIAL state)

**Three independent primary-source verifications confirm:**

- Decreto Legislativo 1474/2025 was issued **December 29, 2025**, not July 2025.
- **"Sentencia C-077/2025" does not exist.** Not in the Corte Constitucional relatoría. The actual ruling is **C-079/2026** (April 15, 2026).
- The "18 IE / 23 V mix" claim is fabricated. The real outcome (per C-079/2026) is **wholesale inexequibilidad** with retroactive DIAN refund order.

**The hallucination has a verification stamp.** The EME-A01 file's header includes:

```
**Fecha de última verificación**: 20 de marzo de 2026
**Fuente de verificación vigencia**: Normograma DIAN (https://normograma.dian.gov.co),
   Relatoría Corte Constitucional (https://www.corteconstitucional.gov.co), comunicados DIAN 2026.
```

The verification was either (a) never done, (b) done against a hallucinated answer, or (c) done by an LLM that fabricated the result. Either way: a self-attested verification stamp in the corpus is meaningless without external audit.

## How the skill protocol caught it

The vigencia-checker skill mandates **≥ 2 primary sources** per veredicto. In Activity 1.5:

1. **First corpus source (EME-A01)** said "C-077/2025, July 2025 expedido, partial state."
2. **Second corpus source (T-I)** said "Auto 082/084 of 2026, December 29 2025 expedido, wholesale SP."

Two corpus sources directly contradicting each other → per skill's `patrones-citacion.md` §"Cuándo NO emitir veredicto" rule 2: **report the discrepancy, do NOT elegir una posición.** Move to external primary verification.

3. **External verification** (WebSearch on Corte Constitucional + INCP + Pérez-Llorca) confirmed T-I was correct on dates + suspension, and revealed both corpus sources are now stale (C-079/2026 escalated SP → IE on April 15, 2026).

A wholesale-flag pipeline (no dual-source check) would have either:
- Trusted EME-A01 → marked Decreto 1474 as `parcial` based on a fabricated sentencia → user gets confidently-wrong answer
- Trusted T-I → marked Decreto 1474 as `suspendida` → user gets stale answer (correct in March, wrong in late April)

Either way: bad outcome. The skill's discipline of "verify with ≥ 2 primary sources before emitting" caught both failure modes.

## The pattern to look for

Other corpus files likely have similar issues. Recommended audit grep:

```bash
# Files claiming verification:
grep -rl "verificación\|verificado\|fuentes verificadas\|URLs verificadas" knowledge_base/

# Files with internal citation of specific sentencias / autos:
grep -rE "Sentencia C-[0-9]{3}/(20[0-9]{2})|Auto [0-9]+/(20[0-9]{2})" knowledge_base/

# Files with addendum / estado actual / post-suspension naming:
find knowledge_base -name "*addendum*" -o -name "*estado-actual*" -o -name "*post-suspension*"
```

Each match is a Fix 6 audit candidate. Cross-check the cited sentencia / auto against Corte Constitucional or Consejo de Estado relatoría. If it doesn't exist OR the date doesn't match: flag as hallucinated content.

## The rule that survives

**A self-attested verification stamp is a marketing claim, not evidence.** No corpus document's own "verified on date X against URL Y" line counts as verification. Verification means: an EXTERNAL party (the skill, the SME, a CI gate) reads the cited primary source and confirms it matches the corpus claim.

The vigencia-checker skill's burden-of-proof inversion ("no veredicto without ≥ 2 primary sources, refuse if they contradict") is the operational expression of this rule. Apply it any time the corpus asserts a fact about a specific sentencia, auto, decreto, ruling number, or vigencia state.

## What this motivates downstream

1. **Fix 6 (corpus consistency editorial pass) gains a corpus-wide hallucination audit subscope** — not just reconciling internal contradictions, but auditing every cited sentencia / auto against the relatoría.
2. **Re-Verify Cron** (originally week-13 placement) becomes urgent — a corpus document that captured a fact on date X may be stale by date X+30 if a sentencia of fondo lands. Move to week 4.
3. **The Fix 5 golden judge gains a new TRANCHE-format test case shape**: "LIA cited a sentencia number that does not exist" → CRITICO / INCORRECTO.
4. **Future corpus ingestion** must run new documents through the skill before they enter the active corpus — corpus-edit-time verification, not retrieval-time damage control.
