# Activity 1.7 — Outcome report

> **Date:** 2026-04-26 evening (Bogotá).
> **Scope:** Run vigencia-checker skill on 3 norms covering states DT (derogada tácita) / SP (suspendida provisional) / EC (exequibilidad condicionada). Save 3 veredicto fixtures. Complete 7-state coverage of the skill eval seed (combined with Activities 1.5 + 1.6).
> **Methodology limitation:** Same as Activity 1.5 — Fix 1B-α scrapers don't exist yet. Walked the skill protocol manually using WebSearch as primary-source proxy.

---

## Headline

The skill protocol completed the **7-state coverage of the v2 skill eval seed** with three real Colombian cases — a unanimous Sentencia de Unificación by Consejo de Estado for DT, a current cautelar measure with partial-lift history for SP, and a literal "en el entendido que..." Court text for EC. Combined with Activities 1.5 + 1.6: **7 of 7 v2 vigencia states (V/VM/DE/DT/SP/IE/EC) validated against real Colombian norms**; skill eval seed at 7/30. v3's four new states (VC/VL/DI/RV) are queued for Activity 1.7b in week 1-2.

## What we ran

Manual walkthroughs of `.claude/skills/vigencia-checker/SKILL.md` flow on three norms picked for clean state-coverage:

1. **DT case** — Arts. 588 y 589 ET (en su aplicación a correcciones de imputación de saldos a favor)
2. **SP case** — Numeral 20 del Concepto DIAN 100208192-202 del 22 de marzo de 2024 (TTD: integración del IA al cálculo de dividendos no constitutivos)
3. **EC case** — Art. 11 Ley 2277/2022 numerales 1, 2, 3 y parágrafo 6 (tarifa renta para usuarios industriales de zona franca)

## What we found

### Finding 1 — DT case requires "DT parcial" expressivity in the schema (CRITICO for v3 design)

Arts. 588 y 589 ET are **vigentes en su redacción literal** for the generality of corrections, BUT their **aplicación a correcciones de imputación de saldos a favor** is desplazada tácitamente by Art. 43 Ley 962/2005 (Ley Antitrámites). The Consejo de Estado (Sección Cuarta, M.P. Julio Roberto Piza Rodríguez) issued **Sentencia de Unificación 2022CE-SUJ-4-002 del 8 de septiembre de 2022** confirming this; DIAN adopted via Oficio/Concepto DIAN 3285/2023.

This is **not "the article is derogated tácitamente"** — that would lose the article's continued applicability for non-imputation corrections. It is **"the article's application to a specific supuesto is desplazada"**. The veredicto captures this via:

- `state = DT` with `state_aclaratorio` field explaining the partial scope
- `change_source.effect_payload.contested = false` (sentencia de unificación = clean pronouncement)
- `applies_to_periodo.norm_version_aplicable` and `regimen_aplicable_en_su_lugar_para_supuesto_DT` carry the dual-track guidance

**Implication for v3 schema:** the `change_source` discriminated union (fixplan_v3 §0.3.3) and `applies_to_payload` JSON shape MUST capture supuesto-specific scope. Sub-unit norm_ids (et.art.588) alone don't capture this — the DT is application-level, not text-level. The skill veredicto JSON shape captures it; the persistence schema must preserve it without flattening.

### Finding 2 — SP case proves partial-lift history is real and persistent (MAYOR — schema test)

Concepto DIAN 100208192-202 del 22 de marzo de 2024 had **two numerales suspended on the same date**:

| Numeral | Initial state | Auto suspension | Subsequent ruling | Final state (as of 2026-04-26) |
|---|---|---|---|---|
| Num. 12 (pérdidas contables) | `V` until 2024-12-15 | `SP` (Auto 28920 del 16-dic-2024) | Sentencia 28920 del 3-jul-2025 — **revoked** the suspension | back to `V` |
| Num. 20 (dividendos no constitutivos) | `V` until 2024-12-15 | `SP` (same Auto 28920 del 16-dic-2024) | Sentencia 28920 del 3-jul-2025 — **maintained** the suspension | still `SP` |

Same Concepto, same auto, same posterior sentencia — **divergent state outcomes per numeral**. This is precisely the case fixplan_v3 §0.5.3 "sub-units are first-class norm_ids" was designed for: `concepto.dian.100208192-202.num.12` flips back to V; `concepto.dian.100208192-202.num.20` stays SP. A whole-concepto record would have to choose between two wrong answers.

**Implication for v3 schema validation:** the `norms` catalog must accept these as two separate rows with `parent_norm_id = concepto.dian.100208192-202`. The `norm_vigencia_history` for num. 12 has 3 rows (V → SP → V); for num. 20 has 2 rows (V → SP, with `state_until` still null).

### Finding 3 — EC case exposes "literal text required, no paraphrase" as a hard constraint (MAYOR — synthesis discipline)

Sentencia C-384/2023 (Corte Constitucional, M.P. Diana Fajardo Rivera + Alejandro Linares Cantillo) declared Art. 11 Ley 2277/2022 (numerales 1, 2, 3 y parágrafo 6 — tarifa renta zona franca):

> "EXEQUIBLES, en el entendido que el régimen tarifario establecido en el artículo 101 de la Ley 1819 de 2016 continuará rigiendo para los contribuyentes que hubieran cumplido las condiciones para acceder a este antes del 13 de diciembre de 2022, fecha en la que entró en vigor la Ley 2277 de 2022."

This text is **the operational rule**: the difference between "Art. 11 está vigente" (false; could mislead a contador whose client qualified pre-13-dic-2022) and "Art. 11 está vigente con condicionamiento literal" (true; surfaces the cohort distinction) is the literal Court wording. **Paraphrase corrupts the answer.**

The veredicto's `interpretive_constraint.texto_literal` field captures this verbatim. **The Pydantic model must reject any save that paraphrases or trims the literal text** when `state ∈ {EC, VC}`. fixplan_v3 §0.11.3 contract 1 enforces via `InterpretiveConstraint` dataclass + a Pydantic validator.

**Limitation acknowledged in fixture:** the literal Court text was reconstructed from convergence across 6 secondary sources (AmCham, Deloitte, ConsultorContable, AsuntosLegales, Nexia Montes, DIAN Normograma sumilla); direct fetch from Corte Constitucional comunicado PDF was deferred (binary content, proxy could not extract verbatim). The fixture flags this via `interpretive_constraint.fuente_verificada_directo: false` — Fix 1B-α DIAN + Corte Constitucional scrapers must re-verify before this seed becomes a production veredicto.

## What the skill veredictos say

Three structured veredictos saved at `evals/activity_1_5/`. Headlines:

### DT veredicto — `arts_588_589_ET_correcciones_imputacion_AG2025_veredicto.json`

```
NORMA: Arts. 588 y 589 ET (en su aplicación a correcciones de imputación de saldos a favor)
ESTADO: DT (parcial)
PERÍODO FISCAL: AG 2025
APLICABILIDAD: Sí en redacción literal — pero NO al supuesto específico de correcciones de imputación
PRONUNCIAMIENTO OFICIAL: Sentencia de Unificación 2022CE-SUJ-4-002 (8-sep-2022) Consejo de Estado Sección Cuarta
ADOPCIÓN DIAN: Oficio/Concepto DIAN 3285/2023
RÉGIMEN APLICABLE: Art. 43 Ley 962/2005 (procedimiento autónomo, sin límite temporal de Arts. 588-589 ET)
RIESGO DE ERROR: Medio
RECOMENDACIÓN: NO citar Arts. 588-589 ET como impedimento para correcciones de imputación; aplicar Art. 43 Ley 962/2005
```

### SP veredicto — `concepto_dian_100208192_202_num20_AG2026_veredicto.json`

```
NORMA: Numeral 20 del Concepto DIAN 100208192-202 del 22 de marzo de 2024
ESTADO: SP (suspendida provisional)
PERÍODO FISCAL: AG 2026
APLICABILIDAD: No
SUSPENSIÓN: Auto/Sentencia 28920 del 16-dic-2024 — Consejo de Estado Sección Cuarta (Consejero Milton Chaves García)
PARTIAL-LIFT HISTORY: Sentencia 28920 del 3-jul-2025 — REVOCÓ suspensión del num. 12; MANTUVO suspensión del num. 20
ESTADO ACTUAL: suspensión del num. 20 sigue vigente (no hay sentencia de fondo)
RIESGO DE ERROR: Bajo
RECOMENDACIÓN: NO sumar el IA-TTD al Impuesto Básico de Renta para cálculo de dividendos no constitutivos del Art. 49 ET; aplicar la interpretación que mantiene CE mientras dura la cautelar
```

### EC veredicto — `art_11_ley_2277_2022_zonas_francas_AG2023_veredicto.json`

```
NORMA: Art. 11 Ley 2277/2022 (numerales 1, 2, 3 y parágrafo 6 — tarifa renta zona franca)
ESTADO: EC (exequibilidad condicionada)
PERÍODO FISCAL: AG 2023 en adelante
APLICABILIDAD: Sí, con condicionamiento literal
CONDICIONAMIENTO: Sentencia C-384/2023 (M.P. Diana Fajardo Rivera + Alejandro Linares Cantillo)
TEXTO LITERAL: "EXEQUIBLES, en el entendido que el régimen tarifario establecido en el artículo 101 de la Ley 1819 de 2016 continuará rigiendo para los contribuyentes que hubieran cumplido las condiciones para acceder a este antes del 13 de diciembre de 2022, fecha en la que entró en vigor la Ley 2277 de 2022."
COHORTE A: usuarios industriales calificados antes del 13-dic-2022 → Art. 101 Ley 1819/2016 (20% sin requisito de exportación)
COHORTE B: usuarios calificados desde el 13-dic-2022 → Art. 11 Ley 2277/2022 (con requisito de ingresos por exportación)
RIESGO DE ERROR: Medio
RECOMENDACIÓN: Determinar fecha de calificación del cliente; aplicar régimen aplicable a la cohorte; citar Sentencia C-384/2023 como fundamento del régimen pre-13-dic-2022
```

## What we did NOT do (and why)

**No Supabase UPDATE was applied this round.** Reasoning carries forward from Activity 1.5: the corpus does not contain the **norms themselves** as canonical artifacts — it contains **documents that interpret** the norms. Marking them as `vigencia = 'X'` would either misrepresent or hide.

**Specifically for the SP case:** the Concepto DIAN 100208192-202 num. 20 lives entirely in the cloud DIAN Normograma (where it is a footnote/annotation in the source artifact); the Lia Graph corpus may or may not cite it. The veredicto goes into `evals/activity_1_5/` as fixture data; persistence to staging Supabase is deferred to v3's Fix 1B-γ which will land the canonical `norms` catalog and `norm_vigencia_history`.

**Specifically for the EC case:** the literal Court text constraint requires the v3 schema's `interpretive_constraint` field. Writing this to the v2 `documents.vigencia_basis` free-text would lose the structure. Better to wait for Fix 1B-γ.

**Specifically for the DT case:** the application-level scope (parcial DT) requires the v3 `change_source.effect_payload.contested` shape and the `applies_to_payload` discriminator. Same reasoning.

**This is itself a finding:** Activity 1.7 reinforces v3's persistence redesign — the column-shaped storage of v2 cannot represent the three veredictos faithfully. The 4 Activity 1.5b rows in staging Supabase already strain the v2 enum (no `EC`, no `DT`, no `IE`-vs-`DE` distinction — Activity 1.5b coerced to `vigente|derogada|suspendida`). Activity 1.7's veredictos push this further.

## Tranches de corrección for Fix 5 (golden answers)

When Fix 5 ships its TRANCHE-format judge, six test cases are pre-validated by Activities 1.5 + 1.6 + 1.7 (combined seed 7/30):

```yaml
case: lia_says_arts_588_589_ET_block_correccion_imputacion
classification: INCORRECTO
severity: MAYOR
correction: "Citar Art. 43 Ley 962/2005 + Sentencia de Unificación 2022CE-SUJ-4-002. Arts. 588-589 ET no aplican al supuesto."

case: lia_says_concepto_DIAN_100208192_202_aplica_plenamente
classification: INCORRECTO
severity: CRITICO
correction: "Numeral 20 está suspendido provisionalmente desde 16-dic-2024 (Auto 28920 CE Sección Cuarta). NO sumar el IA al Impuesto Básico de Renta."

case: lia_says_art_11_ley_2277_aplica_a_todos_usuarios_zona_franca
classification: INCOMPLETO
severity: MAYOR
correction: "Sentencia C-384/2023 condicionó la exequibilidad: usuarios calificados antes del 13-dic-2022 conservan régimen Art. 101 Ley 1819/2016. Citar el condicionamiento literal."

case: lia_paraphrases_condicionamiento_C384_2023
classification: INCORRECTO
severity: CRITICO
correction: "Reproducir LITERALMENTE el texto 'en el entendido que...' de la Corte. Paráfrasis altera el alcance — fix_5 enforces exact-substring match."

case: lia_omits_partial_lift_concepto_DIAN_100208192_202_num20
classification: INCOMPLETO
severity: MAYOR
correction: "Mencionar que num. 12 fue levantado (3-jul-2025) pero num. 20 sigue suspendido. Cohorte-aware advertencia."
```

## Activity 1.7 success-criteria check (against `fixplan_v2.md §8` Activity 1.7 spec — superseded by `fixplan_v3.md §8`)

| Original criterion | Met? | Note |
|---|---|---|
| 3 veredicto fixtures saved at `evals/activity_1_5/<case_id>_veredicto.json` matching `fixplan_v2.md §0.8.3(2)` shape | ✅ | All 3 in v2 contract shape; the v2-to-v3 upgrade mapper (fixplan_v3 §0.11.5) handles the bump |
| Each fixture includes `fix_5_skill_eval_seed` block with `expected_state`, `expected_must_cite`, `expected_must_not_say` | ✅ | All 3 fixtures include the seed block |
| Skill eval set seeded with 7 of 30 cases (one per state), pre-validated | ✅ | 7/30 seed for v2's 7-state taxonomy; v3's 11-state taxonomy needs 4 more (Activity 1.7b) |

**Net Activity 1.7 result:** 7-state coverage of the v2 skill eval seed complete. Three additional cases for Fix 5 golden judge pre-validated. Three findings above reinforce v3's persistence redesign rationale (sub-units first-class, structured `change_source`, literal interpretive constraints).

## What this changes for the next 14 weeks

1. **v3 plan published.** The combined output of Activities 1.5 + 1.6 + 1.7 + 1.5b is the empirical foundation for `fixplan_v3.md` (2,054 lines) and `state_fixplan_v3.md` (1,054 lines). Per-state findings above informed §0.4 (11-state enum), §0.3.3 (structured change_source), §0.5.3 (sub-units first-class).
2. **Activity 1.7b queued for week 1-2.** Same shape as 1.7 but covers the 4 v3 new states: VC (vigente condicionada non-CC), VL (vacatio legis), DI (diferida), RV (revivida). SME picks canonical norms in week-1 ontology session.
3. **v2-to-v3 fixture upgrade mapper.** All 7 existing fixtures (V/VM/DE/DT/SP/IE/EC) need an upgrade pass to add v3's `change_source` discriminated union + `applies_to_kind` + `interpretive_constraint`. Mapper lives in sub-fix 1A's scope (`fixplan_v3.md §2.1`).
4. **Skill prompt v1.0 → v2.0.** SME-led update to add VC/VL/DI/RV state recognition + structured `change_source` output requirement. Engineer integrates in 1A.
5. **Fix 1B-α scrapers must re-verify the EC case literal text.** The reconstructed condicionamiento text in `art_11_ley_2277_2022_zonas_francas_AG2023_veredicto.json` carries `fuente_verificada_directo: false` — a Nivel-1 fetch from Corte Constitucional + DIAN Normograma is required before the fixture is used as a production veredicto. Adding this as a sub-fix 1B-α smoke target.

## Suggested next ship (Activity 1.7b candidate — VC/VL/DI/RV state coverage)

Run the skill manually on **4 more norms** to complete the v3 11-state coverage of the skill eval seed:

| State | Candidate type | Picking criterion |
|---|---|---|
| **VC** (vigente condicionada non-CC) | A norm under judicial modulación by CE OR a concepto DIAN whose interpretation is constrained by a posterior concepto without nulidad | SME picks |
| **VL** (vacatio legis) | A recently-published Ley with deferred entry into force (rige desde fecha futura) | SME picks per current legislative pipeline |
| **DI** (diferida — CC le dio plazo al Congreso) | A recent C- sentencia declaring inexequibilidad with plazo al Congreso | SME picks per current judicial calendar |
| **RV** (revivida) | Canonical: any ET article that flipped V→VM via Ley 1943/2018 then back to V/RV via C-481/2019 | SME picks specific article |

Effort: ~1.5 days engineer + ~15 min SME consultation per case for canonical-pick. Output: 4 more veredicto fixtures + 4 more pre-validated Fix 5 judge cases. Skill eval seed reaches 11/30 (one per state).

---

*Activity 1.7 complete. 3 veredicto fixtures committed; outcome documented; combined skill eval seed at 7/30 covering all 7 v2 vigencia states. No Supabase UPDATE applied (correct decision — v3 persistence redesign supersedes v2 column-shape; fixtures will be re-persisted to `norm_vigencia_history` cleanly when Fix 1B-γ ships in week 6-7). Next: operator green-light on `fixplan_v3.md` + `state_fixplan_v3.md`, then schedule SME ontology session to greenlight skill v2.0 prompt update + pick Activity 1.7b canonical norms for VC/VL/DI/RV.*
