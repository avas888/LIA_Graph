# Vigencia is 2D: formal state × applicability per period

**Source:** Expert vigencia-checker skill (`.claude/skills/vigencia-checker/references/reglas-temporales.md`). Implementation in `fixplan_v2.md §2.1` (Vigencia dataclass + `applies_to(periodo)` method). Validated by all 4 Activity 1.5 + 1.6 veredictos in `evals/activity_1_5/`.

## The mistake my v1 design made

In `fixplan_v1.md §2.1` I drafted a Vigencia ontology with a single timeline:

```python
@dataclass
class Vigencia:
    state: VigenciaState         # vigente | derogado | ...
    vigente_desde: date | None
    vigente_hasta: date | None
    derogado_por: Citation | None
    ...
```

This conflates "is this norm vigente in the legal system today?" with "does this norm apply to the period the user is asking about?" — two distinct questions that produce four cases, not two:

| Vigente today? | Applicable to period queried? | Example |
|---|---|---|
| Sí | Sí | Trivial case: current law for current period |
| Sí | No | Norma nueva con vigencia futura ("Ley 2277/2022 doesn't apply to AG 2022 per Art. 338 CP") |
| No | Sí | **Ultractividad**: norma derogada que sigue rigiendo hechos pasados ("Art. 158-1 ET applies to AG 2022 hechos económicos even though it was derogated for AG 2023+") |
| No | No | Norma derogada antes del período + sin ultractividad |

A single-timeline model can express cases (Yes/Yes) and (No/No) but mangles the asymmetric cases (Yes/No) and (No/Yes). The asymmetric cases are exactly the ones contadores ask about — "what was the rule in 2018?", "is the new beneficio retroactive?", "can I still use this deduction for the AG I'm declaring now?".

## The corrected model

```python
@dataclass(frozen=True)
class Vigencia:
    """Formal state — global, point-in-time."""
    state: VigenciaState  # V | VM | DE | DT | SP | IE | EC
    vigente_desde: date | None
    vigente_hasta: date | None
    # ... structured citations per state ...

    def applies_to(self, periodo: PeriodoFiscal) -> AplicabilidadVerdict:
        """Per-period applicability — derived from state + temporal rules."""
        ...

@dataclass(frozen=True)
class PeriodoFiscal:
    """A specific evaluation period (year for renta; bimestre for IVA; etc.)."""
    impuesto: str
    year: int
    period_label: str
    period_start: date
    period_end: date

@dataclass(frozen=True)
class AplicabilidadVerdict:
    aplica: str  # 'Sí' | 'No' | 'Parcial'
    justificacion: str  # 'Art. 338 CP' | 'ultractividad' | 'régimen de transición' | etc.
    norm_version_aplicable: str | None  # for VM: which version's text applies
```

## The constitutional rules `applies_to` must encode

Per `.claude/skills/vigencia-checker/references/reglas-temporales.md`:

**Art. 363 CP (Irretroactividad tributaria):** *"Las leyes tributarias no se aplicarán con retroactividad."* A norm that creates or increases tax burden cannot apply to economic events before its entry into vigor — even if it's vigente today.

**Art. 338 CP (Anualidad):** for impuestos de período (renta, ICA), a law promulgated in year Y applies starting AG Y+1 — not the current AG Y. Exception: if the norm is favorable to the contribuyente, can apply to AG Y by favorabilidad.

**Ultractividad de la norma derogada:** a derogated norm continues to govern economic events that occurred while it was vigente. Hechos generated in AG 2022 → governed by 2022 norms even if derogated in 2023.

These rules are encoded in `applies_to` per impuesto type:

- `renta` (impuesto de período anual): per period, with Art. 338 CP for promulgation-during-period and ultractividad for pre-period derogation.
- `iva` (período bimestral o cuatrimestral): finer-grained — tarifa changes mid-period prorrate by hecho generador.
- `retencion_fuente` (mensual): tarifa at moment of pago o abono en cuenta (lo primero que ocurra).
- `ica` (variable per municipio): per municipio's período + Art. 338 CP.
- `patrimonio`: norma vigente al corte (1 enero del año en que se causa).

## Why this matters in retrieval

The retriever needs a `vigencia_at_date` planner signal (added in `fixplan_v2.md §2.5` Fix 1C). When the user asks about AG 2018, the planner extracts `vigencia_at_date = 2018-12-31` and the retriever filters to articles whose `applies_to(AG 2018)` returns `Sí` — including derogated articles that were vigente in 2018 (ultractividad).

Without the 2D model, the retriever can only filter on "vigente today" — which means historical questions either get current law (wrong by retroactividad) or get refused (no available evidence).

## Worked examples (from Activity 1.5 + 1.6)

| Norm | State today | Aplica AG 2025? | Aplica AG 2022? | Why |
|---|---|---|---|---|
| Decreto 1474/2025 | IE (C-079/2026) | No | No | Inexequible total + retroactivo (DIAN devolución) |
| Art. 689-3 ET | VM | Sí | Sí (en versión Ley 2155/2021 original) | Vigente desde 2021; modificación 2294/2023 prorroga AG 2024-2026 |
| Art. 158-1 ET | DE (Ley 2277/2022) | No | Sí | Derogada efectos 2023-01-01; ultractividad para AG 2022 hechos |
| Art. 290 #5 ET | V (con régimen_transición) | Sí (para pérdidas pre-2017) | Sí | Régimen de transición vigente desde 2017-01-01 |

**Read this table carefully.** Three of the four norms produce different `aplica` answers depending on the period. The 1D model can capture at most one of those answers correctly per row; the 2D model captures both.

## The rule that survives

**Vigencia is never expressed as `(norm, state)`. It is expressed as `(norm, periodo, state, applicability)`.** Code that asserts "this article is derogated, don't use it" without naming a período is making a category error — the assertion is meaningless without temporal context.

The retriever's vigencia filter operates on `applies_to(planner.vigencia_at_date)`, not on `state`. The composer's vigencia chip displays both: the state (red "DEROGADA") AND the period qualifier ("para AG 2025; aplicable a AG 2022 por ultractividad").

The Fix 5 golden judge tests both dimensions — every golden answer's `must_cite` and `must_not_cite` are scoped to a specific período, and the judge runs the harness with that período to compute `applies_to` before grading.

## What this motivates downstream

- The retriever's RRF demotion factor is computed from `applies_to(vigencia_at_date)`, not from a static `state`. Same chunk, different period query → different demotion. (`fixplan_v2.md §2.5`)
- The planner gains `vigencia_at_date` extraction from user-message cues ("para 2018", "antes de 2017", "este año", "AG 2025"). (`fixplan_v2.md §2.5` Files — Modify section.)
- The vigencia chip in the UI surfaces both dimensions. (`fixplan_v2.md §2.6`)
- The skill eval set includes at least one (norm, multiple period) pairs to test the asymmetric cases — not just (norm, today). (`fixplan_v2.md §0.8.4`)
