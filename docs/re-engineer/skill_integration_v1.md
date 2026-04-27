# Vigencia-checker skill — integration impact report

> **Source:** Expert delivery 2026-04-26 evening, 8 files / ~1,428 LOC, organized as a Claude Code Skill at `.claude/skills/vigencia-checker/`.
> **What it is:** A complete, expert-designed verification protocol for Colombian tax-law vigencia (formal AND fiscal-applicability) — with 7-state taxonomy, primary-source discipline, judicial-pronouncement integration, and audit-LIA tranche output format.
> **What this report does:** Maps every change the skill triggers in `fixplan_v1.md` (Fix 1A through Fix 6 + Activity 1.5), names the work it eliminates, names the work it adds, and surfaces the budget shifts.

---

## §0 — TL;DR

**The expert's skill closes the design gate (Gate 1+2) for Fix 1A entirely** — and is significantly more rigorous than what I had proposed. It also redesigns Fix 1B (extraction) into a "skill-guided per-article verification" pattern that needs scraper infrastructure I had under-budgeted, and gives us the audit-LIA tranche format that should become the spine of Fix 5 (golden answers).

**Net budget impact:** ~$30K of SME design time freed (skill is delivered as expert work) BUT ~$50K of new scraper-and-cache engineering needed because the skill mandates double-primary-source verification per article. Net ≈ $20K higher cost on Fix 1, offset by faster timeline (gate 1+2 already done) and far higher quality ceiling.

**Critical insight the skill formalizes that my plan was missing:** *vigencia formal vs aplicabilidad fiscal are DISTINCT dimensions.* A norm can be derogated today but still apply to AG 2023 by ultractividad. A norm can be vigente today but not apply to AG 2025. My ontology had vigente_desde/hasta as a single timeline; the skill forces us to model `(norm, period_fiscal) → (state, applicability)` as a 2D structure. Without this, we cannot answer historical-context questions correctly.

---

## §1 — What the skill is, in one paragraph

A 7-state taxonomy (V/VM/DE/DT/SP/IE/EC) for any Colombian tax norm, plus a non-negotiable verification flow: identify precisely → consult ≥ 2 primary sources (Secretaría del Senado / DIAN Normograma / SUIN-Juriscol / Corte Constitucional / Consejo de Estado per source-type rules) → verify temporal-fiscal applicability against Art. 363 CP (irretroactividad) and Art. 338 CP (anualidad) → detect tácita derogation and active demands → emit a structured veredicto OR refuse veredicto when verification is incomplete. Includes 3 checklists (artículo-ET, decreto, resolución-DIAN) and a separate audit mode that produces "TRANCHE DE CORRECCIÓN" output evaluating LIA's existing answers with INCORRECTO/INCOMPLETO/OMISIÓN classification + GRAVEDAD (CRÍTICO/MAYOR/MENOR).

---

## §2 — Side-by-side: my proposed Vigencia ontology vs the skill's taxonomy

| Dimension | My proposal (`fixplan_v1.md §2.1`) | Expert skill | Verdict |
|---|---|---|---|
| **State count** | 6 (vigente/derogado/suspendido/transicion/proyecto/desconocida) | 7 (V/VM/DE/DT/SP/IE/EC) | **Adopt skill's.** Mine missed VM (vigente-modified — separate from vigente-original), DT (derogada-tácita — distinct risk profile from DE), IE (inexequible by Constitutional Court — distinct from legislative DE), EC (exequibilidad condicionada — entirely missing). |
| **Vigencia-formal vs aplicabilidad-fiscal** | Conflated into `vigente_desde`/`vigente_hasta` | Modeled as 2 separate dimensions; aplicabilidad evaluated per-period | **Adopt skill's.** This is the single biggest gap in my design. Without it we cannot do ultractividad correctly. |
| **Modification chain** | `modificado_por: list[citation]` | Required cronological chain in every VM veredicto + citation discipline (cite ONLY the vigente text, NEVER mix versions) | **Adopt skill's** — it's the operationalization, not just the data field. |
| **Suspension** | `suspension_actual: citation` | Required: link to T-series for the suspended doc + obligation to present "posición conservadora vs agresiva defendible" | **Adopt skill's.** The "two positions" framing is critical. |
| **Régimen de transición** | `regimen_transicion: citation` | Modeled per-parágrafo (each paragraph can have its own vigencia state — "Inciso 1 → V; Parágrafo 1 → VM desde AG 2023") | **Adopt skill's** — granularity at parágrafo level matters for Art. 290 ET, Art. 147 ET, etc. |
| **Audit trail** | `vigencia_audit: { extraction_method, confidence, reviewed_by }` | Same + log of fuentes-primarias-consultadas (URLs + fechas) + verificación-de-demandas-activas | **Adopt skill's** — auditability is binding for our use case. |
| **Burden of proof** | Implicit (extractor emits with confidence score) | **EXPLICIT: if can't verify with primary sources, NO veredicto.** "Reporting incertidumbre is preferable to affirming erroneously." | **Adopt skill's.** This is the safety contract that prevents the kind of confident-hallucination the SME found in §1.G. |
| **Out-of-scope** | (not addressed) | Skill enumerates: derogatoria-tácita-sustantiva needs human reasoning; conceptos-DIAN reconsidered without clear marking; municipal norms heterogeneous | **Adopt skill's** — explicit boundary is honest. |

---

## §3 — Per-fix integration impact

### Fix 1A — Vigencia ontology (`fixplan_v1.md §2.1`)

**Before skill:** Plan was to spend Week 1 designing the ontology with SME (1 engineer × 1 week + SME × 0.3 week, ~$15K).

**After skill:** Design is done. The `Vigencia` Python dataclass + Pydantic schema implements the skill's taxonomy directly:

```python
# src/lia_graph/vigencia.py
from enum import Enum
from datetime import date
from typing import Literal

class VigenciaState(str, Enum):
    V  = "vigente_sin_modificaciones"
    VM = "vigente_modificada"
    DE = "derogada_expresa"
    DT = "derogada_tacita"
    SP = "suspendida_provisional"
    IE = "inexequible"
    EC = "exequibilidad_condicionada"

@dataclass(frozen=True)
class Citation:
    """Per skill's references/patrones-citacion.md identification conventions."""
    norm_type: str       # 'ley' | 'decreto' | 'resolucion_dian' | 'sentencia_cc' | ...
    norm_id: str         # 'Ley 2277/2022' | 'Sentencia C-489/23' | 'Auto 082/2026'
    article: str | None  # 'Art. 10' | 'numeral 5' | None
    fecha: date | None
    primary_source_url: str | None

@dataclass(frozen=True)
class Vigencia:
    state: VigenciaState
    vigente_desde: date | None
    vigente_hasta: date | None
    derogado_por: Citation | None         # set when DE
    modificado_por: tuple[Citation, ...]  # cronological chain when VM
    suspension: Citation | None           # set when SP — must link to T-series
    inexequibilidad: Citation | None      # set when IE — includes effects timing
    condicionamiento: str | None          # set when EC — LITERAL Court text, not paraphrased
    regimen_transicion: Citation | None
    fuentes_primarias_consultadas: tuple[Citation, ...]   # ≥ 2 for veredicto
    extraction_audit: dict
    # NEW: aplicabilidad fiscal — the 2D dimension my original missed
    def applies_to(self, periodo: 'PeriodoFiscal') -> 'AplicabilidadVerdict':
        """Returns Sí/No/Parcial + justification per skill's reglas-temporales.md."""
        ...
```

**Effort released:** ~1 week of senior engineering + 0.3 SME-week. Roughly **$12K** freed for re-allocation.

**New requirement:** SME signoff on the *implementation* (not the design — the design is theirs). Estimate: 30 minutes.

**Status:** Gate 1+2 closed by the skill itself. Gate 3 (implementation) is a 2-day Python sprint. Gate 4 (test plan) — 12 unit tests covering each state's verification rules + 8 edge cases (parágrafo-level state divergence, IE with diferred effects, EC with literal condicionamiento, etc.). Gate 5 (greenlight) — pass against a 30-question Vigencia-extraction smoke fixture.

### Fix 1B — LLM extraction over 7,883 articles (`fixplan_v1.md §2.2`)

**This is where the skill changes the most.**

**Before skill:** Single LLM extraction pass with a structured-output prompt. ~$60-120 LLM spend, 1 senior engineer × 2 weeks. Implicit assumption: the extractor "just knows" vigencia.

**After skill:** The extractor MUST follow the skill's protocol per article:
1. Identify precisely (article number, parágrafo)
2. Fetch primary source 1 (Senado / SUIN-Juriscol / DIAN Normograma per type)
3. Fetch primary source 2 (different one)
4. Check Corte Constitucional relatoría for sentencias C- on the article
5. Check Consejo de Estado for autos de suspensión
6. Determine state per the 7-state rules
7. Emit structured veredicto OR refuse

This is **not a single LLM call**. It's a **tool-using agent loop** per article, with double-primary-source web access, judicial-pronouncement search, and abstention discipline.

**Effort revision:**

| Path | Wall time per article | Cost per article | 7,883 articles total |
|---|---|---|---|
| Naive (single LLM call, no web fetch) | ~3 sec | ~$0.01 | ~7 hrs, ~$80 |
| Skill-protocol (full agent loop with web access) | ~30-90 sec | ~$0.05-0.15 | ~80-200 hrs, ~$400-1200 |
| Skill-protocol with cached scrapes | ~5-15 sec | ~$0.02-0.05 | ~10-30 hrs, ~$150-400 |

**The expert's own follow-up suggestion confirms this:** *"Scripts de scraping en una segunda iteración: parser de citas (extract_norm_id), scrapers específicos para Normograma DIAN y Secretaría del Senado, y un comparador de versiones. Estos requieren manejo de estructura HTML cambiante, rate limiting, y caching — vale la pena hacerlos bien aparte."*

**Recommended re-scope of Fix 1B as 3 sub-fixes:**

- **Fix 1B-α — Scraper + cache infrastructure.** Build (a) `scrapers/secretaria_senado.py`, (b) `scrapers/dian_normograma.py`, (c) `scrapers/suin_juriscol.py`, (d) `scrapers/corte_constitucional.py`, (e) `scrapers/consejo_estado.py`. Each is a focused fetcher with rate-limiting, HTML-stable parsing, and a local cache (probably SQLite for the cache). Output: `(norm_id, primary_source) → captured_text + judicial_history`. Effort: 1 senior engineer × 3 weeks. **NEW WORK.**
- **Fix 1B-β — Skill-guided extractor batch runner.** Wraps the vigencia-checker skill as a callable agent loop. Per article: invoke skill → produce veredicto → write to `evals/vigencia_extraction_v1/<article_id>.json`. Resumable, parallelizable. Uses scrapers from 1B-α; falls back to live web fetch when cache miss. Effort: 1 senior engineer × 2 weeks.
- **Fix 1B-γ — Materialization pass.** Reads the extraction outputs, populates Supabase `documents.vigencia*` columns + Falkor `:ArticleNode.vigencia` properties + materializes `DEROGATED_BY / MODIFIED_BY / SUSPENDED_BY / INEXEQUIBLE_BY / CONDITIONALLY_EXEQUIBLE_BY` edges. Effort: 1 senior engineer × 1 week.

**Effort revision summary:** Fix 1B was 1 engineer × 2 weeks ($30K) → now 1.5 engineers × 6 weeks ($120K). **Net new work: $90K.** This is the largest single budget shift.

### Fix 1C — Materialize vigencia in Supabase + Falkor (`fixplan_v1.md §2.3`)

**Folded into Fix 1B-γ.** No separate budget needed; the materialization pass IS Fix 1C in the new shape. Frees ~$15K.

### Fix 1D — Plumb vigencia into retrieval (`fixplan_v1.md §2.4`)

**No change to the plan, but the skill's 2D model (formal × period) means the planner needs a `vigencia_at_date` signal.** This is exactly what I sketched in `fixplan_v1.md §2.4` "Files — Modify" but the skill formalizes WHY:

- Default mode: `vigencia_at_date = today`. Retriever filters to articles whose `applies_to(today)` returns `Sí`.
- Historical mode: `vigencia_at_date = AG2018-12-31` (or whatever year context the planner extracts). Retriever filters to articles whose `applies_to(AG2018)` returns `Sí` — INCLUDES articles now-derogada that were vigente then (ultractividad).

The hybrid_search SQL function gains a `vigencia_at_date` parameter. The new RRF demotion factor is computed from `applies_to(vigencia_at_date)`, not from the binary `vigencia` column. **The Activity 1 surgical fix becomes a special case of Fix 1D** — `vigencia_at_date = today` AND state-in-{DE, IE, SP} → multiplier 0.

**No effort change.** Fix 1D was 1.5 engineers × 2 weeks; same.

### Fix 1E — User-facing vigencia chips (`fixplan_v1.md §2.5`)

**Skill enriches the chip semantics.** The 7 states map to 7 chip variants:

- V → no chip (default)
- VM → blue "modificada por X" chip
- DE → red "derogada por X desde fecha" chip
- DT → orange "derogada tácitamente — verificar" chip (NEW per skill)
- SP → yellow "suspendida por auto X — ver T-Y" chip with mandatory T-series link
- IE → red "inexequible — sentencia C-X" chip
- EC → purple "exequibilidad condicionada — ver condicionamiento" chip with expandable text (NEW per skill)

**Effort change:** ~+0.25 engineer-week to handle 7 variants instead of 4. ~$4K.

### Fix 5 — Golden-answer regression suite (`fixplan_v1.md §6`)

**Skill provides the AUDIT-LIA TRANCHE format that becomes the judge schema.**

The skill's `patrones-citacion.md §"Integración con flujo de auditoría a LIA"` defines exactly the structure my golden-answer judge should produce:

```yaml
output_evaluado: "..."
clasificacion_hallazgo: INCORRECTO | INCOMPLETO | OMISION_COMPLETA
descripcion_error: "..."
norma_real_aplicable: <Vigencia veredicto>
gravedad: CRITICO | MAYOR | MENOR
correccion_propuesta: "..."
evidencia_fuente_primaria: [<URLs>]
articulo_norma_afectada: "Art. X ET"
```

This replaces the PASS/SOFT_FAIL/HARD_FAIL judge I had sketched. CRITICO maps to HARD_FAIL (blocks merge); MAYOR maps to SOFT_FAIL (warns); MENOR maps to NO_FAIL (logs).

**Effort change:** Replaces my judge prompt design (~3 days) with skill-protocol invocation (~1 day). Frees ~$3K. More importantly, the judge becomes consistent with the rest of the system — same vigencia model, same source discipline.

### Fix 4 — Ghost-topic kill (`fixplan_v1.md §5`)

**Skill informs the populate work.** When SME populates `tarifas_renta_y_ttd` with the canonical articles, each article runs through the vigencia-checker skill at ingest time. So instead of "add 5 docs and hope," it's "add 5 docs that have been verified against ≥ 2 primary sources, with full vigencia veredicto attached." Higher quality bar; same effort because the skill does the verification.

### Fix 6 — Internal corpus consistency editorial pass (`fixplan_v1.md §7`)

**Skill is the diagnostic tool.** When the SME finds the 3 versions of art. 242 num. 1, the skill's veredicto on art. 242 num. 1 produces the canonical answer (which version is the vigente text, what modificaciones it had, when each version applied). Replaces SME judgment-by-memory with skill-verified-against-primaries.

### Activity 1.5 — Document-level flagging (current next ship)

**Skill validates the flagging.** Before any UPDATE on `documents.vigencia`:
1. Run vigencia-checker on the document's anchor norm (e.g., for `Decreto-1474-2025.md` → run on `D. 1474/2025`).
2. Skill emits SP veredicto with auto reference + T-series link.
3. UPDATE proceeds with the skill's verdict as the audit trail.
4. Same for Ley-1429-2010 — skill emits per-article verdict (mostly DE with some surviving articles); flagging is per-article-precise rather than wholesale.

**Effort change:** Activity 1.5 was 30 minutes ("just UPDATE Ley 1429 → derogada"); now becomes a 4-hour task because we run the skill on the document first to get the per-article granularity. **But the result is much better** — instead of wholesale-flagging and losing 1-2 vigente articles, we flag only what's actually derogada.

---

## §4 — New work the skill creates (that wasn't in `fixplan_v1.md`)

| New work | Why | Effort | Cost |
|---|---|---|---|
| **Skill scraper infrastructure** (`scrapers/{senado,dian,suin,corte_constitucional,consejo_estado}.py`) | Skill mandates double-primary-source verification per article. Live web fetch per call is too slow + rate-limited. Need cached scrapes. | 1 engineer × 3 weeks | ~$45K |
| **Skill invocation harness** | Wraps the vigencia-checker as a callable Python module with `verify_norm(norm_id, periodo) -> Vigencia` API. Used by Fix 1B-β extractor + Fix 4 populate + Fix 6 editorial + Activity 1.5 + Fix 5 judge. | 1 engineer × 1 week | ~$15K |
| **Skill eval set** (the expert's #2 follow-up) | ~30 SME-curated cases with known-correct veredictos: 13 LIA-known errors + T-series cases + clean controls. Tests if the skill captures what it claims. | SME × 1 week + engineer × 0.5 week | ~$15K |
| **Re-verification cadence cron** | Skill's `fuentes-primarias.md §"Caching y frescura"` mandates re-verification after 90 days for current-AG; after every reforma tributaria for all active citations. Need a scheduled job. | 1 engineer × 0.5 week | ~$8K |
| **"Lite" conversational mode** (the expert's #3 follow-up) | Inline use during chat — cheaper output without the full footnote ceremony, same verification rigor. | Defer to v2 — not needed for launch | $0 (this round) |

**New work total: ~$83K.** Within the $60K reserve + the $12K + $15K + $3K freed from Fixes 1A/1C/5 = ~$30K freed → net $53K new.

---

## §5 — Updated 14-week budget (delta vs `fixplan_v1.md §10`)

| Bucket | Original | Updated | Delta |
|---|---:|---:|---:|
| Engineering: 2 senior backend × 14 wks | 200 | 200 | — |
| Engineering: 1 senior backend × 8 wks | 60 | 60 | — |
| Frontend: 0.5 FTE × 4 wks | 25 | 28 | +3 (7 chip variants) |
| SME: 0.5 FTE × 14 wks | 90 | 75 | −15 (skill design done) |
| LLM extraction (Fix 1B) | 1 | 1 | — (cache absorbs cost) |
| Cloud infra delta | 4 | 6 | +2 (scraper hosting + cache storage) |
| QA + CI tooling (Fix 5) | 30 | 27 | −3 (judge schema reused from skill) |
| Tooling: data-eng / ops 0.25 × 14 wks | 30 | 30 | — |
| **Reserve / contingency** | **60** | **8** | **−52 (absorbed)** |
| **NEW: Skill scraper infrastructure** | 0 | 45 | +45 |
| **NEW: Skill invocation harness** | 0 | 15 | +15 |
| **NEW: Skill eval set (30 cases)** | 0 | 15 | +15 |
| **NEW: Re-verification cadence cron** | 0 | 8 | +8 |
| **NEW: Skill smoke + integration tests** | 0 | 7 | +7 |
| **Total** | **500** | **525** | **+25 over budget** |

**$25K over.** Options to close the gap:

- **(a) Defer skill eval set to month 4 (post-launch).** Cuts $15K; risk: launch without independent quality measure.
- **(b) Defer re-verification cron to v2.** Cuts $8K; risk: cited norms go stale silently.
- **(c) Cut frontend chip variants from 7 to 4 (V/VM/DE/SP), defer DT/IE/EC chips to v2.** Cuts $3K; risk: incomplete user signal.
- **(d) Operator approves $25K bump.** No risk; clean execution.

**Panel recommendation: (d).** The skill saves us months of design work and gives us a much higher quality ceiling. $25K is 5% of budget for a > 50% improvement in execution rigor. Don't pinch.

---

## §6 — How Activity 1's data point reads after this analysis

Activity 1 (the SQL-only filter ship) showed:
- art. 689-1 mentions: 13 → 2 (clean win — the binary flag DOES catch this case)
- Ley 1429 mentions: 303 → 286 (essentially unchanged)
- 6-año firmeza: 13 → 19 (got worse — chunk reshuffle)

**The skill explains why.** Activity 1's filter operates on the **binary parser flag**, which catches articles that self-announce derogation in their own text (art. 689-1 has "derogado por art. 51 Ley 2155/2021" in its own body — caught). It does NOT catch:

- Documents that don't self-announce (Ley 1429 article bodies don't say "derogado" in their own text, even though most are repealed) → needs DE/DT classification by the skill.
- Stale "6 años firmeza" claims that pre-date Ley 2010/2019 but don't say "derogado" anywhere → needs the skill's modificación-cronológica chain to detect that the relevant article was modified.

So Activity 1 was a **valid structural fix** (the bypass really was a bug) but its real-world impact is bounded by the binary flag's coverage. **Real impact comes when Fix 1B (skill-guided extraction) populates the structured Vigencia for every article — at which point the same retrieval filter fires correctly across 100% of the corpus, not just the regex-caught subset.**

This is gate-3 of the six-gate lifecycle in action: Activity 1 measured at the gate-3 numeric level and surfaced a real but bounded win. Now we know exactly what the next ship has to do.

---

## §7 — Updated workstream order (replaces `fixplan_v1.md §8`)

```
Week:    1  2  3  4  5  6  7  8  9 10 11 12 13 14
F1A:     ██  (now 2 days — implement skill's ontology in Python)
F1B-α:   ██████████  (3 wks — scraper infra; new)
F1B-β:   ░░░░░░░░██████  (2 wks — skill-guided extractor batch)
F1B-γ:   ░░░░░░░░░░░░██  (1 wk — materialization)
F1D:     ░░░░░░░░░░░░██████  (2 wks — retrieval plumbing)
F1E:     ░░░░░░░░░░░░░░░░░░██████  (2 wks — UI chips, 7 variants)
F2:        ████████████   (parámetros móviles, parallel to F1)
F3:                ██████████   (anti-hallucination)
F4:                   █████████████   (ghost topic + populate)
F5:      █████████████████████████████   (golden answers + skill-judge)
F6:                        ████████████   (corpus consistency)
SkillEval:        ██████  (3 wks — 30 SME cases against the skill)
ReVerifyCron:                                  ██  (1 wk)
                       ↑                                         ↑
                       wk-4 KILL                            wk-14 LAUNCH
                       SWITCH                                 GATE
```

Critical-path change: Fix 1B-α (scrapers) starts immediately week 1 in parallel with Fix 1A implementation. Without scrapers, Fix 1B-β cannot run at acceptable cost.

---

## §8 — Decision required from the operator

| # | Decision | Recommendation | Cost |
|---|---|---|---|
| **D1** | Adopt the skill's 7-state taxonomy + 2D model (formal × period) for Fix 1A wholesale? | **YES** — supersedes my proposed ontology cleanly; nothing in my version is worth preserving over the skill's. | Free (skill is delivered) |
| **D2** | Re-scope Fix 1B into 1B-α (scrapers) + 1B-β (extractor) + 1B-γ (materialize)? | **YES** — without scrapers the skill's protocol is too expensive to run at corpus scale. | +$90K (offset by $30K freed → net +$60K) |
| **D3** | Approve $25K budget bump to cover the new skill-driven work? | **YES** — see §5. The reserve absorbs $52K of it; only $25K is genuinely additional. | +$25K |
| **D4** | Adopt the audit-LIA tranche format as the Fix 5 golden-judge schema? | **YES** — consistent with the rest of the system; replaces my custom schema. | Free (skill is delivered) |
| **D5** | Run the skill on Decreto 1474/2025 + Ley 1429-2010 BEFORE the wholesale UPDATE in Activity 1.5? | **YES** — skill produces per-article granularity instead of wholesale flagging. Eliminates the "lose 1-2 vigente articles" risk. | +3.5 hrs of skill-runtime work |
| **D6** | Defer the "lite conversational mode" + scraper-comparador-de-versiones to v2? | **YES** — out of scope for launch. | Free |

---

## §9 — What I am doing right now (no operator decision needed)

- Skill installed at `.claude/skills/vigencia-checker/` ✅
- Tasks #17 (Activity 1) marked completed; #18 reframed to "integrate skill into fix plan" ✅
- This integration report committed to `docs/re-engineer/skill_integration_v1.md` ✅

## §10 — What I will do next (waiting on operator decisions)

1. **If D1+D2+D3 are YES:** update `fixplan_v1.md` to reflect the 7-state ontology, the Fix 1B re-scope, and the budget bump. Update `exec_summary_v1.md` (the boss-facing one) with the headline ("we got expert help; plan upgraded; +$25K").
2. **If D5 is YES:** kick off the vigencia-checker run on Decreto 1474/2025 first (the cleanest case — single Auto, single article block), then on Ley 1429/2010. Replace Activity 1.5's wholesale UPDATE with skill-guided per-article UPDATE.
3. **Independent of decisions:** start Fix 1B-α (scrapers) week 1 because nothing else moves until those exist.

## §11 — What I will NOT do without operator confirmation

- Modify `supabase/migrations/` further to alter retrieval until Fix 1D's design is locked.
- Run the skill at corpus scale (7,883 articles) until Fix 1B-α is live (would burn ~$1K of LLM spend with no caching).
- Bill against the $25K bump.

---

*v1, drafted 2026-04-26 evening immediately after expert skill delivery. Open for amendment as we learn from the first 3-4 articles run through the skill.*
