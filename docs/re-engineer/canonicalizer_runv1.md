# Canonicalizer — Run v1 (batched, testable, materialize-one-by-one)

> **Purpose.** Split the full vigencia extraction (~11,400 norms) into ~60 small batches that an engineer can launch one at a time, each finishing in 15–30 minutes, each with focused test questions that exercise *just the norms that batch finalized*. Cumulative coverage grows visibly; if a batch regresses the system, we stop on that batch only — never roll back the whole run.
> **Companion docs.** `fixplan_v3.md` §0.5 (norm-id grammar), §0.11 (skill harness), §1B-β; `state_fixplan_v3.md` §10 latest run-log entry; `docs/aa_next/README.md` (six-gate lifecycle).
> **Scope.** Local environment only (`LIA_SUPABASE_TARGET=wip`). Staging promotion is held until full local-env quality bar is met (operator decision 2026-04-27).
> **Run-once + three-stage promotion (operator directive 2026-04-27).** Gemini extraction fires exactly ONCE per batch, in the engineer's working tree. Veredicto JSONs are the canonical artifact. They flow through three target environments by *replay*, each with an SME gate:
>
> 1. **Local docker** (Supabase :54322 + FalkorDB :6389). Where SME corrections + re-replays happen cheaply.
> 2. **Cloud staging** (after Stage 1 exit gate passes; SME re-validates).
> 3. **Production** (after Stage 2 ≥ 48h soak + operator green-light).
>
> Under no circumstances do we run the Gemini process twice. Stages 2–3 do NOT call the API; they only replay the JSONs. See §9 for the full promotion protocol.
> **Convention.** All times Bogotá AM/PM. All batches resumable. All test questions phrased the way an accountant would ask them.

---

## 0. The shape of one batch

Every batch follows the same protocol. If you understand one, you understand all 60.

```
┌─ Pre-flight (≤ 5 min) ───────────────────────────────────────────┐
│ 1. Define the norm slice (norm_id pattern or list).             │
│ 2. Run the 4–6 test questions against the LOCAL stack.           │
│    Capture verbatim answers + citations + diagnostics.           │
│    This is the "before" baseline.                                │
└──────────────────────────────────────────────────────────────────┘
┌─ Extraction (15–30 min) ─────────────────────────────────────────┐
│ 3. Launch detached (nohup + heartbeat) per batch.                │
│ 4. Skill verifies each norm via 2 primary sources.               │
│ 5. Veredictos land in `evals/vigencia_extraction_v1/<batch_id>/`.│
└──────────────────────────────────────────────────────────────────┘
┌─ Sink (1–3 min) ─────────────────────────────────────────────────┐
│ 6. Sink writes to `norms` + `norm_vigencia_history` (local).     │
│ 7. Falkor mirror sync (incremental, just the new norms).         │
└──────────────────────────────────────────────────────────────────┘
┌─ Verify (≤ 10 min) ──────────────────────────────────────────────┐
│ 8. Re-run the same 4–6 test questions. Capture "after."          │
│ 9. SCORE the batch:                                              │
│    - PASS if every "after" answer correctly reflects vigencia    │
│      (no derogated norm cited as vigente; chips render where     │
│      expected; for_period queries return the right historical    │
│      version). Engineer attestation; SME spot-check on every     │
│      5th batch.                                                  │
│    - FAIL if any answer regresses or claims a wrong state.       │
│ 10. Append to `evals/canonicalizer_run_v1/ledger.jsonl`.         │
└──────────────────────────────────────────────────────────────────┘
┌─ Stop conditions ────────────────────────────────────────────────┐
│ - Batch FAIL → stop the run, triage, fix, re-run THAT batch only.│
│   "Re-run that batch" means: clean up the partial run by run_id  │
│   (R2 rollback), then launch the same batch_id with a NEW run_id │
│   so idempotency keys don't conflict.                            │
│ - Refusal rate > 25% in a batch → pause; SME triages refusals    │
│   before next batch.                                             │
│ - Two consecutive FAILS → escalate; reassess the slicing.        │
│ - **NEVER re-run a batch that already produced veredicto JSONs   │
│   in `evals/vigencia_extraction_v1/<batch_id>/`.** The Gemini    │
│   extraction is a one-time operation per the operator directive  │
│   (§9). Re-running burns budget and breaks determinism. If a     │
│   batch already has output, the next step is `ingest_vigencia_   │
│   veredictos.py`, not `extract_vigencia.py`.                     │
└──────────────────────────────────────────────────────────────────┘
```

**Run command template** (one per batch, materialized via the batch config):
```bash
set -a; . .env.local; set +a
nohup env SUPABASE_URL=$SUPABASE_URL SUPABASE_SERVICE_ROLE_KEY=$SUPABASE_SERVICE_ROLE_KEY \
        LIA_GEMINI_API_KEY=$LIA_GEMINI_API_KEY \
        PYTHONPATH=src:. uv run python scripts/extract_vigencia.py \
        --batch-id A1 \
        --run-id canonicalizer-A1-$(date +%Y%m%dT%H%M%SZ) \
        --output-dir evals/vigencia_extraction_v1/A1 \
        > logs/canonicalizer_A1.log 2>&1 &
disown
```

The heartbeat (per `scripts/monitoring/ingest_heartbeat.py`) prints batch progress every 3 min in Bogotá AM/PM. The `cli.done` event ends the run.

**Rollback per batch** (R2 per `state_fixplan_v3.md` §5):
```bash
docker exec supabase_db_lia-graph psql -U postgres \
  -c "DELETE FROM norm_vigencia_history WHERE extracted_via->>'run_id' LIKE 'canonicalizer-A1-%'"
```
Norm catalog rows stay (they're cheap; idempotent on re-run).

---

## 1. Why this slicing (not random shards)

Three rules drove the slicing:

1. **Topic coherence.** A batch covers ONE family (e.g. "ET retención en la fuente," "Ley 2277/2022"). The accountant test questions land cleanly because every cited norm in the answer comes from the same slice.
2. **Budget per batch.** Skill latency averages ~5–10 sec/norm (with primary-source caching). 100–200 norms ⇒ 15–30 min wall time. Small batches finish before any operator's attention drifts.
3. **Priority by accountant traffic.** Earliest batches cover what accountants ask about first: declaraciones, sanciones, renta tarifas, IVA. Last batches cover specialized doctrine. If we have to stop early, the system is still usefully gated for the high-traffic surface.

Every batch is self-contained: a fresh engineer can pick up batch B7 with no context other than this doc and the codebase.

---

## 2. Phase index (high-level)

| Phase | Theme | Batches | Cumulative norm coverage | Why this order |
|---|---|---|---|---|
| **A** | Procedimiento tributario foundation | A1–A4 | ~6% | High-cite, low-volatility — proves the pipeline works |
| **B** | ET — Renta (10 batches) | B1–B10 | ~20% | Highest accountant traffic; most-cited subset |
| **C** | ET — IVA + Retefuente + GMF + Patrimonio | C1–C4 | ~25% | Second-highest traffic |
| **D** | Reformas tributarias por ley | D1–D8 | ~38% | Where vigencia mutations actually happen |
| **E** | Decretos reglamentarios (DUR 1625, DUR 1072, decretos legislativos) | E1–E13 | ~58% | Largest individual artifact (DUR) |
| **F** | Resoluciones DIAN clave | F1–F4 | ~62% | UVT, calendario, factura electrónica |
| **G** | Conceptos DIAN unificados | G1–G6 | ~67% | Anchor doctrine for accountants |
| **H** | Conceptos DIAN individuales + Oficios | H1–H8 | ~80% | The long tail of doctrina |
| **I** | Jurisprudencia (CC + CE) | I1–I4 | ~83% | Vigencia-mutation triggers |
| **J** | Régimen laboral (CST + Ley 100 + parafiscales + DUR 1072) | J1–J8 | ~93% | Lia's labor-advisor scope |
| **K** | Cambiario + comercial + societario | K1–K4 | ~97% | Specialized; tail |
| **L** | Refusal triage + cleanup | L1–L3 | ~98%+ | SME-led; closes refusals from prior phases |

**Total: ~60 batches. ~22 hours of wall time, distributed across ~5–7 working days.**

---

## 3. Batch catalog

### Phase A — Procedimiento tributario foundation

#### A1 · ET procedimiento — declaraciones, RUT, plazos
- **Slice:** `et.art.555` through `et.art.580-2` (~28 norms)
- **Wall:** 15 min
- **Test questions** (one per concept; all Bogotá AM/PM phrasing optional):
  1. *"¿En qué fechas vence la declaración de renta de personas naturales para AG 2025?"* — expects calendario reference + Resolución DIAN of the year (deferred to F1; here we just verify Art. 579-2 is cited as vigente).
  2. *"¿Qué obligaciones impone el RUT para una S.A.S.?"* — Art. 555-2 must be cited as vigente.
  3. *"¿Quiénes están obligados a declarar renta este año?"* — Art. 591–595, Art. 598. None should be cited as derogated.
  4. *"¿Qué pasa si presento la declaración después del plazo?"* — Art. 641 (sanción extemporaneidad). Sanction batch (A3) handles the sanction-side; here just confirm the procedural articles surface clean.
- **Pass rule:** every test answer cites only vigente norms; no chips except blue (`VM`) on articles modified by reforms covered in later batches.

#### A2 · ET firmeza, correcciones, beneficio de auditoría
- **Slice:** `et.art.588` through `et.art.605` + `et.art.689-1` + `et.art.689-3` (~22 norms)
- **Wall:** 15 min
- **Test questions:**
  1. *"¿Cuál es el plazo de firmeza de una declaración con pérdidas?"* — must NOT cite "6 años" (the §1.G regression marker). Must reach Art. 147 + Art. 714 (current 5-year rule).
  2. *"¿Cómo corrijo una declaración para aumentar el saldo a pagar?"* — Art. 588 must surface as vigente (or DT-flagged per 1.7 fixture).
  3. *"¿Aplica el beneficio de auditoría en AG 2025?"* — Art. 689-3 must show as **VM** (Ley 2294/2023 prórroga). Must NOT cite Art. 689-1 (derogated).
  4. *"¿Qué término tiene la DIAN para revisar una declaración?"* — Art. 705 + Art. 714.
- **Pass rule:** zero `art. 689-1` citations; zero "6 años firmeza" claims; chip on Art. 689-3 reads "modificada por Ley 2294/2023".

#### A3 · ET sanciones (régimen general)
- **Slice:** `et.art.634` through `et.art.682` (~50 norms)
- **Wall:** 20 min
- **Test questions:**
  1. *"¿Cuánto es la sanción por inexactitud?"* — Art. 647 (200%, gradual reductions per Art. 648).
  2. *"¿Cómo calculo la sanción por extemporaneidad sin requerimiento?"* — Art. 641 + Art. 642.
  3. *"¿Hay reducción por aceptación de la sanción?"* — Art. 709–712.
  4. *"¿Sanción por no enviar información?"* — Art. 651.
- **Pass rule:** every cited sanction article shows current text; modifications by Ley 2277/2022 (where applicable) surface with a blue chip.

#### A4 · ET devoluciones, compensaciones, intereses
- **Slice:** `et.art.815` through `et.art.866` (~32 norms)
- **Wall:** 15 min
- **Test questions:**
  1. *"¿Cómo solicito devolución de saldo a favor de IVA?"* — Art. 815 + Art. 850.
  2. *"¿Qué interés moratorio aplica a un pago tardío de retención?"* — Art. 634 + Art. 635.
  3. *"¿Puedo compensar saldo a favor de renta con IVA por pagar?"* — Art. 815.
- **Pass rule:** intereses cited at the current DIAN-published rate (deferred to F1 for the rate itself; here verify the article framework).

---

### Phase B — ET Renta (the heart of the corpus)

#### B1 · ET renta — sujetos pasivos + residencia
- **Slice:** `et.art.7` through `et.art.25` (~20 norms)
- **Wall:** 15 min
- **Test questions:**
  1. *"¿Cuándo una persona natural extranjera es residente fiscal en Colombia?"* — Art. 10.
  2. *"¿Una sociedad sin domicilio en Colombia paga renta en el país?"* — Art. 12.
  3. *"¿Qué ingresos de fuente extranjera tributan?"* — Art. 24 + Art. 25.
- **Pass rule:** Art. 10 modifications post-Ley 1819/2016 surface with chip; no derogated norms cited.

#### B2 · ET renta — ingresos brutos + INR
- **Slice:** `et.art.26` through `et.art.57` (~32 norms)
- **Wall:** 20 min
- **Test questions:**
  1. *"¿Los dividendos son renta o ganancia ocasional?"* — Art. 30 + Art. 48–49 (dividendos no constitutivos de renta) + Art. 242 (tarifa). **Critical**: this question checks the v3 `for_period` resolver — accountant should NOT see "10% dividendo" claim (the §1.G regression marker).
  2. *"¿Las indemnizaciones laborales tributan?"* — Art. 27 + Art. 36–4.
  3. *"¿La utilidad por venta de activo fijo es ganancia ocasional?"* — Art. 300 (deferred to B6) + Art. 26 framework here.
- **Pass rule:** no "10% dividendo" claim for AG ≥ 2023 (post-Ley 2277). Resolver `for_period('renta', 2023)` returns the post-reform tariff; `for_period('renta', 2018)` returns the pre-reform tariff (Art. 338 CP shift).

#### B3 · ET renta — costos
- **Slice:** `et.art.58` through `et.art.88` (~30 norms)
- **Wall:** 20 min
- **Test questions:**
  1. *"¿Cómo se determina el costo fiscal de inventarios?"* — Art. 62–66.
  2. *"¿Qué costos son deducibles para renta presuntiva?"* — Art. 87–88.
  3. *"¿Costo de venta de acciones?"* — Art. 73–76.

#### B4 · ET renta — deducciones generales
- **Slice:** `et.art.104` through `et.art.131-3` (~30 norms)
- **Wall:** 20 min
- **Test questions:**
  1. *"¿Qué requisitos debe cumplir un gasto para ser deducible?"* — Art. 107.
  2. *"¿Cuánto puedo deducir por intereses sobre préstamos?"* — Art. 117 + reglas de subcapitalización.
  3. *"¿Es deducible el ICA pagado?"* — Art. 115.
- **Pass rule:** Art. 117 modifications by Ley 1819/2016 surface chipped; Art. 115 modifications by Ley 2277/2022 surface chipped.

#### B5 · ET renta — deducciones especiales **(includes DE-validated norm)**
- **Slice:** `et.art.158` through `et.art.178` (~30 norms)
- **Wall:** 20 min
- **Test questions:**
  1. *"¿Puedo deducir inversiones en CTeI bajo Art. 158-1?"* — **Must answer NO for AG ≥ 2023.** Must cite Art. 158-1 as **DE** (derogada por Ley 2277/2022 Art. 96, efectos desde 2023-01-01). Red chip mandatory.
  2. *"¿Hay descuento por inversión en CTeI?"* — Art. 256 (deferred to B8) replaces 158-1; here verify the deduction-side correctly redirects.
  3. *"¿Aún aplica la deducción por donaciones?"* — Art. 125 + Art. 257.
- **Pass rule:** Art. 158-1 cited with red `DE` chip + "derogada por Ley 2277/2022 desde 2023-01-01"; for AG 2022 query, `for_period` returns ultractividad (still applicable).

#### B6 · ET renta líquida especial + ganancias ocasionales
- **Slice:** `et.art.179` through `et.art.318` (~50 norms; renta presuntiva; rentas exentas; ganancias ocasionales)
- **Wall:** 25 min
- **Test questions:**
  1. *"¿Cuál es la renta presuntiva mínima para AG 2025?"* — Art. 188 (note: tarifa = 0% post-Ley 2010/2019; renta presuntiva eliminada efectivamente).
  2. *"¿Qué rentas exentas tienen las personas naturales?"* — Art. 206.
  3. *"¿Cómo calcular ganancia ocasional por herencia?"* — Art. 302–303.
  4. *"¿Tarifa de ganancia ocasional para sucesiones?"* — Art. 313–314.
- **Pass rule:** Art. 188 reflects the 0% rate post-Ley 2010/2019; Art. 206 modifications by Ley 2277/2022 chipped.

#### B7 · ET renta — tarifas **(includes VM-validated norm)**
- **Slice:** `et.art.240` through `et.art.247` + sub-units (~12 norms with sub-units)
- **Wall:** 10 min
- **Test questions:**
  1. *"¿Cuál es la tarifa de renta para una S.A.S. en AG 2025?"* — Art. 240 (35%), with chip indicating modificación por Ley 2277/2022.
  2. *"¿Aplicaba esa tarifa para AG 2022?"* — `for_period('renta', 2022)` must return the **pre-reform** rate (33%) per Art. 338 CP. **The single most important test of v3 resolver-2.**
  3. *"¿Tarifa para zonas francas?"* — Art. 240-1, with `EC` chip (condicionada por C-384/2023).
  4. *"¿Tarifa para usuarios industriales que cumplieron antes del 13-dic-2022?"* — must surface the Court's literal "en el entendido que..." text (interpretive_constraint).
- **Pass rule:** answer to question 2 explicitly says "para AG 2022 aplica la tarifa anterior (33%) por Art. 338 CP"; chip on Art. 240-1 shows `EC` purple with literal text on hover.

#### B8 · ET renta — descuentos tributarios
- **Slice:** `et.art.249` through `et.art.260-11` (~25 norms)
- **Wall:** 15 min
- **Test questions:**
  1. *"¿Hay descuento por inversión en CTeI ahora?"* — Art. 256 (current vehicle, replaces Art. 158-1).
  2. *"¿Descuento por donaciones a entidades sin ánimo de lucro?"* — Art. 257.
  3. *"¿Qué requisitos para el descuento por IVA en bienes de capital?"* — Art. 258-1.

#### B9 · ET renta — régimen de personas jurídicas + ESAL
- **Slice:** `et.art.19` through `et.art.33-5` (~40 norms with sub-units)
- **Wall:** 20 min
- **Test questions:**
  1. *"¿Una fundación tributa como ESAL?"* — Art. 19 + Art. 23.
  2. *"¿Una S.A.S. del régimen simple paga renta?"* — Art. 19-4 (deferred to G5).
  3. *"¿Régimen de transición para entidades del régimen tributario especial?"* — Art. 19-5.

#### B10 · ET — Régimen de transición Art. 290 (V-validated, sub-unit-rich)
- **Slice:** `et.art.290` + 5 numerals (~6 norms — small but high-value)
- **Wall:** 10 min
- **Test questions:**
  1. *"¿Cómo trato pérdidas fiscales acumuladas antes de 2017?"* — Art. 290 numeral 5. **Must answer with V chip + transition rules; this validates the V-state path end-to-end.**
  2. *"¿Régimen de transición de descuentos no aplicados?"* — Art. 290 numeral 6.
- **Pass rule:** Art. 290 numeral 5 cited as `V` (no chip — the default-vigente case); response includes the transition rule text.

---

### Phase C — IVA, Retefuente, GMF, Patrimonio

#### C1 · ET IVA — hechos generadores + bases gravables
- **Slice:** `et.art.420` through `et.art.447` (~30 norms)
- **Wall:** 20 min
- **Test questions:**
  1. *"¿La venta de un activo fijo genera IVA?"* — Art. 420.
  2. *"¿La importación de servicios genera IVA?"* — Art. 420 lit. d + Art. 437-2.
  3. *"¿Base gravable en venta de inmuebles?"* — Art. 447 + Art. 462-1.
- **Pass rule:** Ley 1819/2016 modifications to Art. 420 surface chipped.

#### C2 · ET IVA — tarifas, exclusiones, exenciones
- **Slice:** `et.art.462-1` through `et.art.498` (~40 norms)
- **Wall:** 20 min
- **Test questions:**
  1. *"¿Tarifa de IVA para servicios profesionales?"* — Art. 468 (19% general).
  2. *"¿IVA en alimentos?"* — Art. 477 + Art. 481 (exentos vs excluidos).
  3. *"¿IVA en libros?"* — Art. 478.
  4. *"¿IVA en vehículos eléctricos?"* — modificaciones por Ley 1715/2014 + Ley 2099/2021.

#### C3 · ET — Retención en la fuente
- **Slice:** `et.art.365` through `et.art.419` (~50 norms)
- **Wall:** 25 min
- **Test questions:**
  1. *"¿Tarifa de retefuente para honorarios?"* — Art. 392 + Decreto 1625/2016.
  2. *"¿Quién es agente retenedor?"* — Art. 368 + Art. 368-2.
  3. *"¿Retención en la fuente sobre dividendos para AG 2024?"* — Art. 242 + Art. 245 + Decreto reglamentario.
  4. *"¿Cómo declaro retención mensualmente?"* — Art. 604.

#### C4 · ET — GMF + Patrimonio + Timbre
- **Slice:** `et.art.870` through `et.art.881` (GMF) + `et.art.292` through `et.art.298-8` (Patrimonio) + Timbre articles (~30 norms)
- **Wall:** 20 min
- **Test questions:**
  1. *"¿GMF aplica a transferencias entre cuentas propias?"* — Art. 871 + Art. 879.
  2. *"¿Quién paga impuesto al patrimonio en 2025?"* — Art. 292-3 (Ley 2277/2022). Must show the Ley 2277-introduced rule, not the old transitorio.
  3. *"¿Hay impuesto de timbre en arrendamientos?"* — Art. 519.

---

### Phase D — Reformas tributarias por ley (priorizadas por recencia + impacto)

#### D1 · Ley 2277/2022 (Reforma Tributaria 2022) **(includes EC-validated)**
- **Slice:** `ley.2277.2022.art.*` (~110 articles + sub-units)
- **Wall:** 30 min
- **Test questions:**
  1. *"¿Qué artículo de la Ley 2277 modificó la tarifa renta de S.A.S.?"* — Art. 10 (reforma a Art. 240 ET).
  2. *"¿Art. 11 Ley 2277 sobre zonas francas?"* — must show `EC` chip + literal Court text de C-384/2023.
  3. *"¿Art. 96 Ley 2277 derogó qué artículos del ET?"* — must list Art. 158-1, etc.
  4. *"¿Qué impuesto al patrimonio creó la Ley 2277?"* — Art. 35–43.
- **Pass rule:** EC chip on Art. 11 with the literal "EXEQUIBLES, en el entendido que..." text from sub-fix 1A.

#### D2 · Ley 2155/2021 (Reforma Tributaria 2021)
- **Slice:** `ley.2155.2021.art.*` (~70 articles)
- **Wall:** 25 min
- **Test questions:**
  1. *"¿Qué tarifa renta introdujo Ley 2155?"* — Art. 7 (35% transitorio).
  2. *"¿Régimen simple modificaciones Ley 2155?"* — Art. 33.
  3. *"¿Beneficio de auditoría originalmente?"* — Art. 51 (creó Art. 689-3 ET).

#### D3 · Ley 2010/2019 (Crecimiento Económico)
- **Slice:** `ley.2010.2019.art.*` (~160 articles, but only the tax-relevant; deduplicate with corpus citations)
- **Wall:** 30 min
- **Test questions:**
  1. *"¿Qué de la Ley 1943/2018 retomó Ley 2010?"* — verifies the reviviscencia narrative correctly.
  2. *"¿Régimen simple Ley 2010?"* — Art. 74 (modificó SIMPLE).

#### D4a · Ley 1819/2016 — primera mitad (procedimiento + renta sujetos/ingresos)
- **Slice:** `ley.1819.2016.art.1` through `ley.1819.2016.art.190`
- **Wall:** 30 min
- **Test questions:**
  1. *"¿Ley 1819 cómo modificó residencia fiscal?"* — Art. 25 (modificó Art. 10 ET).
  2. *"¿Régimen ESAL post Ley 1819?"* — Art. 140–148.

#### D4b · Ley 1819/2016 — segunda mitad (IVA + retefuente + sanciones + ICA)
- **Slice:** `ley.1819.2016.art.191` through end (~180 artículos)
- **Wall:** 30 min
- **Test questions:**
  1. *"¿Ley 1819 modificó la sanción por inexactitud?"* — Art. 287.
  2. *"¿Régimen monotributo (creado por Ley 1819)?"* — Art. 165 (deroghado by Ley 1943/2018).

#### D5 · Ley 1943/2018 → IE íntegra **(cascade trigger; revives prior text)**
- **Slice:** `ley.1943.2018.art.*` (~120 articles)
- **Wall:** 25 min
- **Test questions:**
  1. *"¿Ley 1943/2018 está vigente?"* — must answer NO with `IE` chip + sentencia C-481/2019 + reviviscencia note.
  2. *"¿Qué pasó con el monotributo?"* — Art. 165 Ley 1819 derogado por Ley 1943; tras IE, monotributo revivió pero ya estaba reemplazado por SIMPLE (Ley 2010). Must surface the chain coherently.
  3. *"¿Tarifa renta Ley 1943?"* — must show that the post-1943 rates fell with the IE; current rates come from later reforms.
- **Pass rule:** every cited article shows `IE` chip; cascade orchestrator (sub-fix 1F) should have re-verified affected ET articles in this batch's sink phase. Verify cascade queue depth post-batch.

#### D6a · Ley 1607/2012 — primera mitad
- **Slice:** `ley.1607.2012.art.1` through `ley.1607.2012.art.100`
- **Wall:** 25 min
- **Test questions:**
  1. *"¿CREE estaba en Ley 1607?"* — Arts. 20–37 (derogados por Ley 1819).
  2. *"¿Ganancia ocasional pre-Ley 1607?"* — Art. 104 (modificó Art. 313 ET).

#### D6b · Ley 1607/2012 — segunda mitad
- **Slice:** `ley.1607.2012.art.101` through end (~100 articles)
- **Wall:** 25 min

#### D7 · Ley 1739/2014 (mini-reforma)
- **Slice:** `ley.1739.2014.art.*` (~80 articles)
- **Wall:** 25 min

#### D8a–c · Ley 2294/2023 (PND 2022–2026) — 3 sub-batches por capítulo
- **Slice:** PND tax-relevant chapter only (~360 articles total → ~120 per sub-batch)
- **Wall:** 25 min each
- **Test questions per sub-batch:** focused on the chapter (impuestos saludables, beneficio de auditoría prórroga, incentivos verdes).

---

### Phase E — Decretos reglamentarios (DUR is the heaviest artifact)

#### E1a–E1f · DUR 1625/2016 — Libro 1 (renta) en 6 sub-batches
- **Slice:** `decreto.1625.2016.art.1.*` reglamentando renta (~500 articles total → ~85 per sub-batch)
- **Wall:** 25 min each
- **Test questions per sub-batch:** focused on the sub-libro (1.2 ingresos, 1.3 costos, 1.4 deducciones, 1.5 descuentos, 1.6 procedimiento, 1.7 régimen especial).
- **Pass rule per sub-batch:** at least 5 articles cited correctly with state; no contradictions with the ET-side state from Phase B.

#### E2a–E2c · DUR 1625/2016 — Libro 2 (IVA + retefuente) en 3 sub-batches
- **Wall:** 25 min each.

#### E3a–E3b · DUR 1625/2016 — Libro 3 (procedimiento + sanciones) en 2 sub-batches
- **Wall:** 25 min each.

#### E4a · Decreto 1474/2025 + autos relacionados **(IE-validated)**
- **Slice:** `decreto.1474.2025.art.*` + auto.ce.082.2026 + auto.ce.084.2026 (~10 norms)
- **Wall:** 10 min
- **Test questions:**
  1. *"¿Decreto 1474 de 2025 está vigente?"* — must answer NO con `IE` chip + sentencia C-079/2026.
  2. *"¿Qué dispone Decreto 1474 sobre cálculo de dividendos no constitutivos?"* — must show the content + the IE chip; for_period(2025) handles the period when it WAS aplicable.

#### E4b–E4d · Decretos legislativos COVID + emergencia tributaria
- **Wall:** 15 min each.

#### E5a–E5c · DUR 1072/2015 (laboral) — 3 sub-batches
- **Wall:** 25 min each.

---

### Phase F — Resoluciones DIAN clave (parametros + operativos)

#### F1 · Resoluciones UVT + calendario tributario (2018–2026)
- **Slice:** `res.dian.*` resoluciones de UVT + plazos por año
- **Wall:** 15 min
- **Test questions:**
  1. *"¿UVT 2025?"* — current value.
  2. *"¿UVT 2018 para revisar declaración antigua?"* — historical value (validates `for_period`).
  3. *"¿Plazos declaración renta personas jurídicas AG 2025?"* — Resolución de calendario del año.

#### F2 · Resoluciones factura + nómina electrónica
- **Slice:** Resolución 165/2023 + 2275/2023 + nómina electrónica + RADIAN
- **Wall:** 15 min

#### F3 · Resoluciones régimen simple
- **Wall:** 10 min

#### F4 · Resoluciones cambiario + RUT + obligados
- **Wall:** 15 min

---

### Phase G — Conceptos DIAN unificados (anchors doctrinales)

#### G1 · Concepto unificado IVA
- **Wall:** 20 min.

#### G2 · Concepto unificado renta
- **Wall:** 25 min.

#### G3 · Concepto unificado retención en la fuente
- **Wall:** 20 min.

#### G4 · Concepto unificado procedimiento + sanciones
- **Wall:** 20 min.

#### G5 · Concepto unificado régimen simple
- **Wall:** 15 min.

#### G6 · Concepto 100208192-202 (IA en dividendos NCRGO) **(SP-validated)**
- **Slice:** numerales del concepto unificado relevantes + auto.ce.28920.2024.12.16
- **Wall:** 10 min
- **Test questions:**
  1. *"¿Puedo aplicar el numeral 20 del Concepto 100208192-202 sobre IA en dividendos para AG 2025?"* — must answer NO con `SP` chip + auto CE 28920/2024.

---

### Phase H — Conceptos DIAN individuales + Oficios (long tail)

#### H1 · Conceptos régimen simple
- **Wall:** 15 min.

#### H2 · Conceptos retención en la fuente
- **Wall:** 15 min.

#### H3a–H3b · Conceptos renta — 2 sub-batches
- **Wall:** 20 min each.

#### H4a–H4b · Conceptos IVA — 2 sub-batches
- **Wall:** 20 min each.

#### H5 · Conceptos procedimiento (correcciones, firmeza, devoluciones)
- **Wall:** 15 min.

#### H6 · Oficios DIAN recurrentes
- **Wall:** 10 min.

---

### Phase I — Jurisprudencia (CC + CE)

#### I1 · Sentencias CC sobre reformas tributarias **(includes the cascade triggers)**
- **Slice:** C-481/2019, C-079/2026, C-384/2023, C-101/2025, C-540/2023, etc. (~25 norms)
- **Wall:** 15 min
- **Test questions:**
  1. *"¿C-481/2019 declaró inexequible Ley 1943?"* — confirms the IE source-of-truth.
  2. *"¿C-079/2026 sobre Decreto 1474?"* — confirms IE source-of-truth.
  3. *"¿C-384/2023 zonas francas?"* — confirms EC source-of-truth.

#### I2 · Sentencias CC sobre principios constitucionales (Art. 363, Art. 338)
- **Slice:** ~15 sentencias
- **Wall:** 10 min
- **Test questions:**
  1. *"¿Art. 338 CP aplicación a impuestos de período?"* — must surface the principle that `for_period` enforces.

#### I3 · Sentencias CE de unificación (Sección Cuarta) **(includes DT validation)**
- **Slice:** sentencia 2022CE-SUJ-4-002 + ~30 más
- **Wall:** 15 min
- **Test questions:**
  1. *"¿Sentencia de unificación 2022CE-SUJ-4-002 sobre correcciones de imputación?"* — must surface DT for Arts. 588-589 ET in this specific application.

#### I4 · Autos CE de suspensión provisional
- **Slice:** auto 28920/2024 + ~20 más
- **Wall:** 10 min

---

### Phase J — Régimen laboral (Lia es asesor laboral por scope)

#### J1 · CST contratos individuales (Arts. 22–50)
- **Wall:** 15 min
- **Test questions:** *"¿Período de prueba máximo?"*, *"¿Contrato a término fijo renovaciones?"*

#### J2 · CST prestaciones sociales (Arts. 51–101)
- **Wall:** 20 min.

#### J3 · CST jornada + descansos (Arts. 158–200)
- **Wall:** 20 min
- **Test questions:** *"¿Cuántas horas máximas semanales?"* — must reflect Ley 2101/2021 transición a 42h.

#### J4 · CST conflictos colectivos (Arts. 416+)
- **Wall:** 20 min.

#### J5 · Ley 100/1993 régimen pensional + actualizaciones (Ley 100/1993 + Ley 797/2003 + Ley 2381/2024 reforma pensional)
- **Wall:** 20 min
- **Test questions:** *"¿Régimen pensional vigente con la reforma?"* — Ley 2381/2024 transición.

#### J6 · Ley 100/1993 régimen de salud
- **Wall:** 15 min.

#### J7 · Parafiscales + licencias (Ley 789/2002 + Ley 1822/2017 + Ley 2114/2021)
- **Wall:** 20 min
- **Test questions:** *"¿Licencia de paternidad días?"* — Ley 2114/2021.

#### J8a–J8c · DUR 1072/2015 laboral relevante — 3 sub-batches
- **Wall:** 25 min each.

---

### Phase K — Cambiario + comercial + societario

#### K1 · Resolución Externa 1/2018 JDBR
- **Wall:** 20 min.

#### K2 · DCIN-83
- **Wall:** 15 min.

#### K3 · Código de Comercio — sociedades
- **Wall:** 20 min.

#### K4 · Ley 222/1995 + Ley 1258/2008 (S.A.S.)
- **Wall:** 25 min.

---

### Phase L — Refusal triage + cleanup (SME-led)

#### L1 · SME triage of refusals from Phases A–E
- **Wall:** 30 min (SME-driven; engineer wires)
- **What it does:** SME walks through ~50 highest-frequency refusals; either (a) extends canonicalizer rules, (b) flags as content-rewrite need (Fix 6), or (c) accepts as legitimate "out of scope."

#### L2 · SME triage of refusals from Phases F–I
- **Wall:** 30 min.

#### L3 · Re-extract previously-refused norms after canonicalizer rule additions
- **Wall:** 20 min.

---

## 4. Per-batch ledger schema

Every batch landing appends one line to `evals/canonicalizer_run_v1/ledger.jsonl`:

```json
{
  "batch_id": "B7",
  "started_bogota": "2026-04-28 10:35:00 AM Bogotá",
  "ended_bogota": "2026-04-28 10:48:00 AM Bogotá",
  "wall_seconds": 780,
  "norms_targeted": 12,
  "veredictos": 11,
  "refusals": 1,
  "cost_usd": 0.45,
  "pre_test_results": {"q1": "FAIL", "q2": "PASS", "q3": "FAIL", "q4": "PASS"},
  "post_test_results": {"q1": "PASS", "q2": "PASS", "q3": "PASS", "q4": "PASS"},
  "delta": "+2 questions moved from FAIL to PASS",
  "states_observed": {"V": 3, "VM": 6, "EC": 1, "DE": 1},
  "engineer_attest": "claude-opus-4-7",
  "sme_spot_check": null,
  "regressions": [],
  "next_batch_unblocked": true
}
```

The ledger is the source of truth. A daily standup reads the last 5–10 lines.

---

## 5. Cumulative coverage milestones

| After batch | % of corpus citations gated | Topical coverage |
|---|---|---|
| A4 | ~6% | Procedimiento básico |
| B10 | ~20% | Renta (the heart) |
| C4 | ~25% | + IVA + retefuente |
| D4b | ~32% | + reformas mayores |
| D8c | ~40% | + reformas recientes |
| E1f | ~50% | + DUR libro 1 |
| E3b | ~58% | + DUR completo |
| F4 | ~62% | + resoluciones DIAN |
| G6 | ~67% | + conceptos unificados |
| H6 | ~80% | + conceptos individuales |
| I4 | ~83% | + jurisprudencia clave |
| J8c | ~93% | + laboral |
| K4 | ~97% | + cambiario + societario |
| L3 | ~98%+ | + refusal triage |

**Soft-launch readiness floor: ~80% (after H6).** Below 80%, too many real accountant questions hit ungated norms; the v3 vigencia gate's value isn't visible to the user. Above 80%, the gate's behavior dominates the user experience.

---

## 6. Test question authoring rules

When writing test questions for a new batch, follow these rules so the test cleanly isolates *that batch's* behavior:

1. **Each question cites norms from THIS batch only.** Cross-batch dependencies belong to a later cluster test, not to a per-batch test.
2. **One concept per question.** Don't combine "Art. 240 + Art. 290" in one question — separate them.
3. **Phrase as an accountant would.** "¿Aún aplica…?", "¿Cuánto es la sanción por…?", "¿Plazo de firmeza…?", "¿Tarifa renta para…?". Not "what's the vigencia state of Art. X".
4. **One question per state-type the batch is supposed to surface.** If batch B5 is the DE batch, one question targets the DE chip explicitly. If B7 is the EC batch, one question targets the literal Court text.
5. **At least one question is a `for_period` question** when the batch covers impuestos de período. This is what validates the resolver-2 path.
6. **Pre-batch baseline is the same questions, before the batch lands.** The "delta" column in the ledger is what makes coverage gain visible.

---

## 7. Stop conditions + escalation

- **Per-batch FAIL** → stop the run, do not advance. Triage in `evals/canonicalizer_run_v1/<batch_id>/failure_report.md`. Resume only after fix.
- **Refusal rate > 25% in a single batch** → pause; SME triages refusals before the next batch. Likely cause: a primary source went offline OR a corpus quirk the canonicalizer didn't anticipate.
- **Two consecutive batch FAILs** → escalate to the operator. Reassess the slicing — maybe the topic family is bigger / messier than estimated.
- **Cumulative refusal queue depth > 500** → SME session before continuing. The queue is signal, not noise.
- **Cost overrun** *(≥ 20% above budgeted line)* → engineer flags; operator decides continue / pause.

---

## 8. Discipline reminders (do not skip)

- **Run-once invariant.** Gemini extraction fires once per batch in local-env. Veredicto JSONs are the canonical artifact. Promotion to staging/production is a *replay* of those JSONs (see §9), never a re-extraction. If you find yourself about to re-run `extract_vigencia.py` on a batch whose output dir is already populated, STOP and read §9.3.
- All operations on local Supabase + local Falkor only. No staging writes during this run.
- Every long-running batch follows the long-running-job protocol: detached, heartbeat every 3 min, kill-switches, no `tee` pipes.
- Every batch's veredicto JSON files commit to `evals/vigencia_extraction_v1/<batch_id>/` so they're reviewable later.
- Cron orchestrator (sub-fix 1F) re-verifies cascading effects after each batch — but the cron is NOT yet deployed locally; we run cascade synchronously per batch via `scripts/sync_vigencia_to_falkor.py` + manual reviviscencia handler when D5 (Ley 1943/2018 IE) lands.
- Update `state_fixplan_v3.md` §10 run log with one entry per phase (not per batch — too noisy), summarizing batch outcomes + any bugs found + delta on the cumulative coverage projection.
- Capture every bug into `docs/learnings/` as it surfaces, in real time.

---

## 9. Promotion protocol — extract once, replay everywhere (THREE stages, not two)

The Gemini extraction is the **single most expensive and slowest** operation in the v3 plan. It is also a deterministic input → output mapping: norm_id + skill prompt + primary-source content → Vigencia veredicto. Re-running it would (a) burn budget, (b) introduce non-determinism (skills are LLM calls; same input can produce slightly different output), (c) waste days of wall time.

**Therefore: we run it once. The veredicto JSONs are the canonical artifact. They get *replayed* through three target environments in order, each with its own SME gate. No Gemini call ever fires in stages 2–4.**

```
[Engineer's working tree — veredicto JSONs in evals/]
         │  (this is the ONLY place Gemini runs)
         │
         │  Stage 1: ingest_vigencia_veredictos.py --target wip
         ▼
[Local docker — Supabase :54322 + FalkorDB :6389]
         │
         │  ↳ SME validation gate against `npm run dev:staging` pointed at local docker URLs
         │  ↳ correction loop here: refusal triage, fixture corrections, re-replay
         │  ↳ exit gate: SME signs off on §1.G 36-question fixture
         │
         │  Stage 2: ingest_vigencia_veredictos.py --target production  (= staging cloud)
         ▼
[Cloud staging — Supabase staging project + cloud Falkor]
         │
         │  ↳ SME re-validates the same 36 questions against `npm run dev:staging` (cloud-pointing)
         │  ↳ exit gate: numbers match local docker within ±1 question
         │
         │  Stage 3: Railway deploy + same replay against production target
         ▼
[Production]
```

### 9.0 — Why three stages, not two

The earlier draft of this doc went directly from "extraction in local-env" to "promote to staging cloud." That skipped the local-docker validation stage where the SME can correct, re-replay, and reach a clean baseline cheaply. The updated path inserts local docker as a **real intermediate environment**, not just a unit-test target. Three reasons:

1. **Risk-free correction loop.** No external users. SME spots a wrong veredicto, we update the JSON, replay to local docker, re-test. Iterate until clean. No cloud writes during this loop.
2. **Same engine.** Local docker Supabase is the same Postgres image as the cloud project. Local Falkor is the same image. If a query works locally, it works in cloud — promotion is a data move, not a software rebuild.
3. **Catches environment-shift bugs once.** Schema drift, role grants, RPC parameter mismatches surface in local docker first, where they're a 5-minute fix instead of a 30-minute cloud-incident triage. The 11 bugs we caught during the v3 H0→H2 wiring (state_fixplan_v3.md §10) all surfaced in local docker; if we had skipped this stage they would have surfaced in cloud staging instead.

### 9.1 — What is the canonical artifact

After every batch lands locally, the canonical artifact set is:

1. **Per-batch veredicto JSONs.** `evals/vigencia_extraction_v1/<batch_id>/<norm_id>.json` — the full v3 `Vigencia` shape produced by the skill. Committed to the repo.
2. **Per-batch audit log.** `evals/vigencia_extraction_v1/<batch_id>/audit.jsonl` — one line per norm: outcome, sources consulted, wall ms, refusal reason if any. Committed to the repo.
3. **Local Postgres rows in `norm_vigencia_history`.** The materialized form of the JSONs after the sink ran.
4. **Local Falkor `(:Norm)` subgraph.** Mirror of the Postgres rows.
5. **Local `norms` catalog rows.** The norm-id catalog with parent walks.
6. **Refusal queue.** `evals/canonicalizer_refusals_v1/refusals.jsonl` for SME triage.

(1) and (2) are the **source of truth for promotion**. Items (3)–(6) are derived and re-materializable from them.

### 9.2 — Stage 1: Local docker validation (the work surface)

This is where every batch lands first. Already in flight today.

```
Step 1.A — Apply v3 migrations to local Supabase docker (already done 2026-04-27).
        ✓ supabase db reset --local

Step 1.B — Run the batch (the only Gemini call).
        ✓ scripts/extract_vigencia.py --batch-id <X> --run-id canonicalizer-<X>-<ts> ...
        ✓ Veredictos write to evals/vigencia_extraction_v1/<batch_id>/.

Step 1.C — Replay to local docker Supabase + Falkor.
        ✓ scripts/ingest_vigencia_veredictos.py --target wip ...
        ✓ scripts/sync_vigencia_to_falkor.py --target wip
        ✓ "wip" = local docker per supabase_client target config.

Step 1.D — Per-batch verify (4–6 test questions).
        Engineer-driven; same questions, before/after.

Step 1.E — End-of-phase SME validation.
        After every Phase boundary (A → L), SME runs §1.G 36-question fixture
        against `npm run dev:staging` with SUPABASE_URL/FALKORDB_URL pointed
        at local docker. SME notes corrections in
        `evals/canonicalizer_run_v1/local_docker_signoff.md`.

Step 1.F — Correction loop (if SME finds a wrong veredicto).
        Edit the JSON in evals/vigencia_extraction_v1/<batch_id>/<norm_id>.json,
        re-run `ingest_vigencia_veredictos.py` with a new run-id.
        DO NOT re-run extract_vigencia.py — the JSON is the canonical artifact.
```

**Local docker exit gate (binding):** SME §1.G score reaches the agreed threshold (≥ 30/36 served_acceptable+, zero ❌) AND zero pre-existing-regression cases reappear AND refusal queue is triaged.

### 9.3 — Stage 2: Cloud staging promotion

Only after Stage 1 exit gate passes.

```
Step 2.A — Apply v3 migrations to cloud staging.
        ✓ supabase db push --linked
        ✓ Schema only — same migrations that ran locally.

Step 2.B — Replay the canonical veredicto JSONs into cloud staging Supabase.
        ✓ scripts/ingest_vigencia_veredictos.py \
              --target production \              # `production` = staging cloud per supabase_client config
              --run-id canonicalizer-run-v1-promote-cloud-<ts> \
              --extracted-by v2_to_v3_upgrade \   # NOT "ingest@v1" — this is a replay, not a fresh run
              --input-dir evals/vigencia_extraction_v1
        ✓ Idempotent: re-running with the same run-id is a no-op.
        ✓ NO Gemini API call fires here.

Step 2.C — Sync the Falkor :Norm mirror to staging FalkorDB.
        ✓ scripts/sync_vigencia_to_falkor.py --target production --rebuild-from-postgres --confirm

Step 2.D — Re-baseline the SME 36-question validation against cloud staging.
        ✓ `npm run dev:staging` (now reads from cloud, not local docker).
        ✓ Numbers should match local docker baseline within ±1 question.
        ✓ If they diverge, staging deploy regressed something; investigate before opening.
```

**Cloud staging exit gate (binding):** cloud staging §1.G score within ±1 of local docker score; no answer that was 🟨 in local docker drops to ❌ in cloud.

### 9.4 — Stage 3: Production promotion

Only after Stage 2 exit gate passes AND ≥ 48h staging soak.

```
Step 3.A — Apply v3 migrations to production Supabase.
        ✓ Same migrations, third target.

Step 3.B — Replay JSONs to production.
        ✓ Same script, --target=<production-prod-target>.
        ✓ NO Gemini call.

Step 3.C — Sync Falkor :Norm mirror to production Falkor.

Step 3.D — Operator green-light + Railway deploy.
        ✓ Required per CLAUDE.md.
        ✓ Smoke against production via internal-beta cohort.
```

**No Gemini API call fires in Stages 2 or 3.** The promotion is a data-layer replay, not a re-extraction.

### 9.5 — What protects the no-double-extraction invariant

Three layers of protection, in order of strictness:

1. **Process discipline.** `scripts/extract_vigencia.py` writes its `--run-id` into every veredicto. Before launching a batch, the engineer checks `evals/vigencia_extraction_v1/<batch_id>/` exists and is non-empty. If it is, the batch was already run — do NOT launch again. The engineer's launch checklist explicitly asks: "is `evals/vigencia_extraction_v1/<batch_id>/` empty? If no — STOP, this batch already ran."

2. **Idempotency at the writer.** `NormHistoryWriter.bulk_insert_run` uses `(norm_id, run_id, source_norm_id)` as the idempotency key. Re-running the *same* run_id is a no-op. So even if someone accidentally launches a batch twice with the same id, no duplicate rows land.

3. **Cost-side budget alarm.** Total Gemini spend for the full corpus run is bounded; an early-warning trips at 50% spend and a hard stop at 105% of the projected budget for the full run. If extraction is running a second time, the alarm fires at the first batch (because the per-batch cost line item is already 100% from the first run) — alerting the operator before significant double-spend accumulates.

### 9.6 — What the cron does NOT do (clarification)

The Re-Verify Cron (sub-fix 1F) DOES re-invoke the skill on individual norms when:
- A reform trigger lands (e.g. cascade reviviscencia after Ley 1943/2018 → C-481/2019).
- A norm's freshness window expires (default 90 days).
- An SME flags a norm for re-verification.

These are **per-norm, on-demand** re-verifications — they are NOT a re-run of the canonicalizer batch. They consume Gemini budget incrementally for specific norms, with SME or operator approval per-cron-cycle.

The canonicalizer batch (this doc) is the **bulk initialization**. After it completes once, the cron's job is to keep the catalog fresh through targeted updates — not to re-do the bulk pass.

### 9.7 — What invalidates the canonical artifact (and therefore *would* require re-extraction)

Two and only two cases require a re-run for some subset of norms:

1. **The skill prompt revises in a way that changes output structure** (e.g. v2.0 → v2.1 adds new field). The migration ships an upgrade mapper for the affected fields when possible; only when the mapper can't recover the missing data do we re-extract for the affected norms — and only those norms, never the full corpus.
2. **The canonical norm-id grammar changes** (e.g. a §0.5 grammar bump that changes the canonical form of an existing artifact). The canonicalizer's idempotency rule keeps existing ids stable; a grammar change that breaks idempotency is a hard "do not ship" signal — fix the grammar instead of re-extracting.

In both cases, the operator decides explicitly. There is no automatic re-extraction.

---

*v1 drafted 2026-04-27, 2:55 AM Bogotá (Claude). Updated same session with §9 promotion protocol after operator directive: extract once, promote everywhere — never re-run Gemini. Open for amendment by adding numbered sub-sections rather than overwriting; if a batch's slice changes, append a v1.1 row, never edit the existing one — the ledger needs immutable batch-id provenance.*
