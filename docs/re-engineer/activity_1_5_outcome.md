# Activity 1.5 — Outcome report

> **Date:** 2026-04-26 evening (Bogotá).
> **Scope:** Run vigencia-checker skill on Decreto 1474/2025 (cleanest test case from SME inventory). Save veredicto fixture; apply UPDATE if appropriate; document findings.
> **Methodology limitation:** Fix 1B-α scrapers don't exist yet. Walked the skill protocol manually using WebSearch as primary-source proxy. The Fix 1B-β harness (production extractor) replays this same protocol at scale once scrapers exist.

---

## Headline

The skill protocol caught **three issues a wholesale-flagging approach would have hidden** and **prevented an UPDATE that would have damaged retrieval**. The protocol's burden-of-proof discipline — "no veredicto without ≥ 2 primary sources" + "when sources contradict, refuse and report" — earned its budget on the first invocation.

## What we ran

Manual walkthrough of `.claude/skills/vigencia-checker/SKILL.md` flow on **Decreto Legislativo 1474/2025**, the only unambiguous SP candidate from `sme_corpus_inventory_2026-04-26.md`.

## What we found

### Finding 1 — Corpus internal contradiction (CRITICO)

Two corpus documents describe **directly contradictory facts** about the same Decreto:

| Document | Decreto issued | Ruling | State claimed |
|---|---|---|---|
| `EME-A01-addendum-estado-actual-decretos-1474-240-2026.md` (NORMATIVA, Mar 2026) | **July 2025** | **Sentencia C-077/2025** (Nov 2025) | 18 IE / 23 V (PARTIAL) |
| `T-I-decreto-1474-2025-estado-post-suspension-corte-constitucional.md` (EXPERTOS, Mar 2026, "v2.0 URLs verificadas") | **Dec 29, 2025** | **Auto 082+084 of 2026** (Jan 29 2026) | Wholesale SP |

These cannot both be true. Different dates, different rulings, different effects.

### Finding 2 — EME-A01 contains hallucinated content (CRITICO)

Per WebSearch verification against Corte Constitucional + INCP + Pérez-Llorca:

- **Decreto Legislativo 1474/2025 was issued December 29, 2025**, not July 2025.
- **"Sentencia C-077/2025" does not exist.** It is not in the Corte Constitucional relatoría. The actual relevant sentence is **C-079/2026** (April 15, 2026).
- The "18 IE / 23 V mix" claim is fabricated.

EME-A01's date stamp says "verificación: 20 marzo 2026" — but the content is wrong. Most likely source: hallucinated during ingestion or autoría inicial; never verified against primary sources.

**This is the strongest possible argument for the skill's burden-of-proof discipline.** The corpus was lying with full confidence + a verification timestamp. The skill caught it.

### Finding 3 — T-I is correct-at-time-of-writing but stale (MAYOR)

The T-I file (Mar 20 2026) correctly captured:
- Decreto issued Dec 29, 2025
- Auto 082+084 of 2026 (Jan 29) → wholesale SP

But the T-I doesn't reflect what happened on **April 9 + April 15, 2026**:
- **C-075/2026** (Apr 9): Decreto 1390/2025 (the underlying emergencia) declared INEXEQUIBLE.
- **C-079/2026** (Apr 15): Decreto 1474/2025 declared INEXEQUIBLE in its entirety + DIAN ordered to refund collected taxes.

T-I is ~6 weeks stale on a high-impact ruling. This is exactly the case the **Re-Verify Cron** workstream (`fixplan_v2.md §11` — $8K) exists to catch.

## What the skill veredicto says

Full structured veredicto saved at `evals/activity_1_5/decreto_1474_2025_veredicto.json`. Headline:

```
NORMA: Decreto Legislativo 1474 de 2025
ESTADO: IE (Inexequible)
PERÍODO FISCAL: cualquier — no aplica para ningún período
APLICABILIDAD: No
JUSTIFICACIÓN: Sentencia C-079/2026 (Sala Plena, 15 abril 2026) declaró
   inexequible el Decreto en su totalidad, con efectos inmediatos +
   retroactivos. DIAN ordenada a devolver los impuestos recaudados durante
   la vigencia efectiva (dic 30 2025 — ene 29 2026).
SUSPENSIÓN PREVIA: Auto 082/2026 + Auto 084/2026 (29 enero 2026), Sala Plena 6-2
SENTENCIA CONEXA: C-075/2026 (9 abril 2026) — inexequible Decreto 1390/2025 (emergencia)
RIESGO DE ERROR: Bajo
RECOMENDACIÓN: NO citar como vigente. Si cliente pagó bajo este Decreto,
   tiene derecho a devolución (radicar dentro 30 días post-notificación).
```

## What we did NOT do (and why)

**No Supabase UPDATE was applied this round.** Reasoning:

The corpus does not contain the **text of Decreto 1474/2025 itself**. It contains **documents that interpret** the Decreto's state (EME-A01, T-I, IVA-E02-interpretaciones-proporcionalidad-decreto-1474, etc.). Marking these interpretation documents as `vigencia = 'derogada'` would:

1. ❌ Hide them from retrieval (we lose the ability to explain the IE state to users).
2. ❌ Penalize correct content (T-I is materially correct on the SP path; just needs a March → April update).
3. ❌ Conflate "the Decreto is inexequible" with "the documents about it are inexequible" — these are different.

The right action is **editorial (Fix 6)**, not **metadata-flag (Activity 1.5)**:
- Reescribir EME-A01 with verified facts (replace fabricated C-077/2025 content with real C-079/2026).
- Update T-I to add the April 2026 transition (SP → IE) as a §X.
- Mark deprecated T-I as `superseded_by` the new T-I version.

**This is itself a major finding**: Activity 1.5 was originally scoped as "wholesale flag the document and re-run §1.G." The skill protocol's discrimination ("interpretation documents ≠ source norm documents") prevented a damaging UPDATE.

## Tranches de corrección for Fix 5 (golden answers)

When Fix 5 ships its TRANCHE-format judge, two test cases are pre-validated by this Activity 1.5:

```yaml
case: lia_says_decreto_1474_suspendido_in_2026_post_april
classification: INCOMPLETO
severity: MAYOR
correction: "Citar Sentencia C-079/2026 + DIAN devolución, no solo Auto 082/084 SP"

case: lia_says_decreto_1474_inexequible_partially
classification: INCORRECTO
severity: CRITICO
correction: "Inexequible EN SU TOTALIDAD por C-079/2026 — la versión 'parcial' proviene de contenido corpus fabricado en EME-A01"
```

## Activity 1.5 success-criteria check (against `fixplan_v2.md §8.2`)

| Original criterion | Met? | Note |
|---|---|---|
| Skill emits SP veredicto for Decreto 1474/2025 | ⚠️ partially | Skill emitted IE — even more current than the SP the SME inventory expected. Reflects post-April-2026 reality. |
| Veredicto cites Auto 082/2026 + T-I link | ✅ | Auto 082 + T-I path both in fixture |
| Per-article veredictos for Ley 1429 | 🚫 deferred | Skill protocol on Ley 1429 not run this round; needs Fix 1B-α scrapers (Senado + DIAN Normograma fetches) for 30+ articles |
| Re-run §1.G; `Ley 1429` mentions drop substantially | 🚫 deferred | No UPDATE applied this round; §1.G unchanged |
| No new auto-rubric regressions | ✅ trivially | No UPDATE → no regressions possible |

**Net Activity 1.5 result:** the skill protocol executed end-to-end, validated the toolchain works, and discovered three corpus issues worth more than the §1.G citation drop we were originally targeting. **The "dry run" is more valuable than the "wet run" would have been at this stage.**

## What this changes for the next 14 weeks

1. **Fix 6 (corpus consistency editorial pass)** is now bigger than `fixplan_v2.md §7` scoped — we have evidence of fabricated content in `EME-A01`, and probably similar issues in other "addendum" / "estado-actual" files. Recommend a corpus-wide grep for `(verificación|verificado|fuentes verificadas)` claims and audit each.
2. **Re-Verify Cron** (`fixplan_v2.md §11`, $8K) is more critical than I weighted. The T-I `SP → IE` lag is exactly what this cron exists to catch. Recommend it ships earlier (week 4 instead of week 13).
3. **Fix 5 golden judge** has two pre-validated test cases from Activity 1.5 — these become the first 2 of the 30-case skill eval set.
4. **Fix 1B-α scrapers** budget is validated. Without scrapers we can't run the skill on Ley 1429's 30+ articles in any reasonable time (manual WebSearch-walkthrough doesn't scale beyond ~3 norms/hour).

## Suggested next ship (Activity 1.6 candidate)

Run the skill manually on **3 more high-impact norms** before Fix 1B-α scrapers exist:

1. **Art. 689-3 ET** (beneficio de auditoría — already directly tested in §1.G). Expected: VM (modificado por Ley 2294/2023). Validates the skill on a clean VM case.
2. **Art. 158-1 ET** (CTeI deduction — SME inventory called out as derogated by Ley 2277/2022). Expected: DE. Validates on a clean DE case.
3. **Art. 290 #5 ET** (régimen de transición pérdidas pre-2017). Expected: V with regimen_transicion. Validates on a clean transition case.

Effort: ~2 hours total via WebSearch + corpus cross-check. Output: 3 more veredicto fixtures + 3 more pre-validated Fix 5 judge cases. Builds the seed of the skill eval set without waiting for Fix 1B-α.

---

*Activity 1.5 complete. Veredicto fixture committed; outcome documented. No Supabase UPDATE applied (correct decision per skill discrimination). Next: operator decides whether to (a) ship the suggested Activity 1.6 manual run on 3 more norms, (b) start Fix 1B-α scrapers immediately, (c) prioritize Fix 6 editorial correction of EME-A01 + T-I.*
