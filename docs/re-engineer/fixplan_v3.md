# Fix plan v3 — Lia Graph re-engineering (norm-keyed persistence)

> **Status:** complete (drafted in 12 chapters 2026-04-27 Bogotá). Open for amendment by adding numbered sub-sections rather than overwriting.
> **Funded:** USD 525K (carried forward from v2; line-item reallocation for the 1B-γ redesign pending re-estimate — see §11).
> **Timeline target:** 14 weeks to soft-launch readiness (carried forward; week 6 critical-path gate now lands on the new persistence shape, not column writes).
> **Companion docs:** `makeorbreak_v1.md`, `exec_summary_v1.md`, `skill_integration_v1.md`, `sme_corpus_inventory_2026-04-26.md`, `vigencia-checker` skill at `.claude/skills/vigencia-checker/`, `fixplan_v2.md` (superseded but preserved as record of the column-shaped persistence approach v3 replaces).
> **Reader assumption:** **none.** A fresh engineer or fresh LLM with zero project context can start at §0 and execute. If you read v2: skim §0–§0.1 to absorb what changed, then jump to §0.2 (mutation surface) and §0.3 (persistence model) — those are the load-bearing new content.
> **Supersedes:** `fixplan_v2.md` (preserved as historical record of the per-document vigencia-as-column approach).

---

## §0 — Honest diagnosis (re-stated for v3)

Code-level audit done 2026-04-26 evening (carried forward from v1/v2) and re-audited against the persistence layer 2026-04-27 morning. The v2 diagnosis was right at the architectural layer; v3 corrects a deeper modeling error one rung below.

**v1/v2's framing (still valid).** The architecture was designed *with* vigencia in mind — `:ArticleNode.status`, edge types `MODIFIES / SUPERSEDES / DEROGATES / SUSPENDS / STRUCK_DOWN_BY / ANULA / DECLARES_EXEQUIBLE`, Supabase columns `vigencia / vigencia_basis / vigencia_ruling_id`. **The engineers built the right house and never plumbed it.** The five specific breaks:

1. The classifier (`ingestion_classifier.py:279-298`) emits zero vigencia metadata. Only the `parser.py:151,196,234` regex (`status = "derogado" if "derogado" appears in text`) writes anything.
2. The sink (`supabase_sink.py:639,646`) writes the binary `vigente|derogada` flag but `vigencia_basis` and `vigencia_ruling_id` stay NULL forever.
3. The retriever's vigencia filter was silently bypassed when `filter_effective_date_max` was passed (the common case). Activity 1 (2026-04-29) fixed this — but the binary flag's coverage is too sparse to bite at scale (`docs/learnings/retrieval/vigencia-binary-flag-too-coarse.md`).
4. The user-visible historical features (`answer_historical_recap.py`, `answer_comparative_regime.py`) are post-retrieval narrative formatters; they cannot prevent retrieval from surfacing a derogated article in the first place.
5. The corpus's source documents (ET, normograma, Mintic normograma) contain vigencia info as PROSE ("Derogado por Ley 1819/2016 Art. 5"), not extractable structured data.

**Break 6 (new in v3).** Even if breaks 1–5 are closed, the persistence target itself is wrong: `documents.vigencia` (and the chunk mirror) ties vigencia to the *corpus document*, not to the *norm*. Concrete failures this guarantees:

- **Norms span many documents.** Art. 158-1 ET appears in ≥ 12 corpus docs (the article text, the EME-A01 addendum, T-I, T-II, multiple expert analyses, blogs). Today every doc carries its own `vigencia` flag; they drift; nothing reconciles them.
- **No `Norm` entity exists as a row.** There is no record of "who is Art. 689-3 ET" — only "documents that mention Art. 689-3 ET." Vigencia state has nothing to attach to.
- **No state history.** `documents.vigencia` is a single column. When Decreto 1474/2025 flipped from SP → IE on 2026-04-15, the prior SP value is gone. The schema cannot answer *"what did we say about this norm on 2026-03-20?"* — the state of the world before the flip is unrecoverable.
- **No reproducibility.** `vigencia_basis` is free-text. Sources cited in the basis cannot be replayed; the extractor's audit trail is lost the moment the cell is overwritten.
- **No place to model cascading effects.** When Ley 1943/2018 was declared inexequible by C-481/2019, the dozens of ET articles it had modified should have flipped from VM back to V (reviviscencia) by operation of constitutional doctrine. There is no schema element where that cascade can be expressed.
- **Free-text `vigencia_basis` cannot be queried.** "Find every norm whose vigencia changed because of Ley 2277/2022" requires NLP on prose. With structured `change_source.source_norm_id`, it is one SQL query.

**v3 closes break 6 via the norm-keyed persistence model in §0.3.** Breaks 1–5 are closed by sub-fixes 1A through 1B-ε exactly as v2 framed them — only the persistence *target* changes (norm-keyed tables instead of document columns).

## §0.1 — What v3 changes vs v2

v2 was drafted 2026-04-26 evening. The redesign drivers — listed in chronological order — are:

| When | Trigger | Resulting v3 change |
|---|---|---|
| 2026-04-26 evening | Activity 1.5 (Decreto 1474/2025) found two corpus docs with contradictory facts about the same Decreto. v2 framed this as a *content* problem (Fix 6 editorial pass). | v3 reframes: the contradiction is a *schema* problem — there's no canonical place for Decreto 1474/2025's vigencia, so each doc invents its own. Fix 6 stays scoped to *content* hallucinations (EME-A01's fabricated C-077/2025); vigencia reconciliation moves to 1B-γ. |
| 2026-04-26 evening | Activities 1.5 + 1.6 produced 4 veredictos in JSON fixtures only. v2's "Activity 1.5b" planned to write them to `documents.vigencia`. | v3 keeps 1.5b as shipped (4 rows in staging), but flags those 4 rows for **re-persistence to `norm_vigencia_history`** when 1B-γ lands. The audit log makes the re-persist clean. |
| 2026-04-26 evening | v2 §0.7 SP candidate (Decreto 1474/2025) flipped to IE between SME inventory delivery (2026-04-26 morning) and Activity 1.5 verification (2026-04-26 evening) due to C-079/2026 ruling on 2026-04-15. | v3 takes this as evidence that **append-only history is mandatory** — without it, the SP→IE transition is unrecoverable. Append-only constraints enforced at DB level in 1B-γ. |
| 2026-04-27 04:15 UTC | Activity 1.5b shipped. Persistence audit log shows the v2 enum (`vigente / derogada / proyecto / desconocida / suspendida / parcial`) cannot represent VM (had to fall back to `vigente`), DT, EC, IE (had to fall back to `derogada`), VC, VL, DI, or RV. The smoke proves the write path works AND that the column shape is too narrow. | v3 introduces the 11-state enum (§0.4) as a real type, not a column constraint, plus structured `change_source` (§0.3). |
| 2026-04-27 morning | Operator pushback on persistence shape: *"vigencia for each legal artifact and a trace of its changes, highly persisted"*. | v3 §0.3: three append-only tables (`norms` / `norm_vigencia_history` / `norm_citations`) replace `documents.vigencia` columns. Falkor mirror via `(:Norm)` first-class node. |
| 2026-04-27 morning | Operator audit of Colombian mutation surface enumerated 12 modes the schema must encode (modificación / sub-unit modification / derogación expresa / derogación tácita / inexequibilidad pro-futuro vs retroactiva vs diferida / modulación condicionada / suspensión CE / nulidad CE / reviviscencia / vacatio legis / ultractividad Art. 338 CP / conceptos DIAN). | v3 §0.2: the 12-mode table becomes binding empirical content. Each mode mapped to its persistence shape. v2's 7-state enum is insufficient (vacatio legis, diferida, reviviscencia each fall outside it). v3 enriches to 11 states. |
| 2026-04-27 morning | Operator flagged Art. 338 CP — a reforma vigente desde diciembre 2022 may not aplicar al AG 2022 even though `state_from <= today`. | v3 §0.6: two resolver functions (`norm_vigencia_at_date` for instantaneous taxes; `norm_vigencia_for_period` for impuestos de período). Retriever picks based on planner-extracted query intent. |
| 2026-04-27 morning | Operator flagged Ley 1943/2018 → C-481/2019 → reviviscencia as the canonical cascading-effect case. | v3 §0.7 + new sub-fix **1F**: cascade orchestrator. Cron-driven (not Postgres trigger). When a row with `change_source.type = sentencia_cc` and `state IN (IE, VC, RV)` lands, enqueue re-verify for every norm previously modified by the inexequible source. |
| 2026-04-27 morning | Operator flagged conceptos DIAN as a special case (doctrina, not norma). | v3 §0.4: VC state captures conceptos DIAN under nulidad partial or modulación by CE. §0.11: anchor-strength field on `norm_citations` distinguishes Ley anchor (strong) from concepto-DIAN anchor (weak). |
| 2026-04-27 morning | Operator flagged sub-unit modification as the case that breaks "column on document": Ley 2277 modifying *only* parágrafo 2 of Art. 240 must not re-version the whole article. | v3 §0.5: sub-unit norm-ids are first-class (`et.art.240.par.2`), not a `sub_unit` column. Catalog-write cost is one-time; granularity is permanent. |

**Net shape change.** Same 14-week timeline, same $525K envelope (line-item reallocation pending re-estimate, see §11), same six-gate discipline. The structural fix surface grows by two sub-fixes (1B-δ citations link backfill; 1F cascade orchestrator) and the v2 sub-fix 1C is renamed 1B-ε to reflect that it now joins through `norm_citations` rather than reading a flag column. Effort consumed by the redesign sits within v2's reserve allocation.

**What does NOT change.** The vigencia-checker skill design (SME-delivered 2026-04-26) is unchanged — its structured veredicto already maps cleanly to the new `Vigencia` value object. Activities 1.5 / 1.6 / 1.7 fixtures are unchanged — they remain the seed for Fix 5's golden eval set. The kill-switch metric at week-6 midpoint (zero `art. 689-1` / `6 años` / `10% dividendo` leaks) is unchanged — added requirement is that veredictos land in `norm_vigencia_history`, not `documents.vigencia`. The Re-Verify Cron infra (week 4-5 deploy) absorbs the new 1F cascade orchestrator without a separate hosting line.

## §0.2 — The Colombian mutation surface (the empirical table)

The schema either encodes these modes upfront or collapses under the first reforma tributaria. Off-the-shelf "norm versioning" patterns assume modificación and derogación expresa are the universe; Colombian legal practice has at least twelve distinct modes plus two meta-rules. Each row below is a real mode the persistence model must represent without information loss.

### §0.2.1 — Twelve mutation modes

| # | Mode | Resulting `state` | `change_source.type` | Sub-unit aware? | Worked example |
|---|---|---|---|---|---|
| 1 | **Modificación de articulo** (whole-text replacement) | `VM` | `reforma` | optional | Ley 2277/2022 Art. 10 reescribe Art. 240 ET (tarifa renta PJ). norm_id `et.art.240` keeps id; new history row with `state_from = 2023-01-01` (Art. 338 CP). Prior row `state_until = 2022-12-31`. |
| 2 | **Sub-unit modification** (one parágrafo / inciso / numeral) | `VM` on the sub-unit, untouched on siblings | `reforma` | **mandatory** | Ley 2277/2022 modifies only parágrafo 2 of Art. 240. `et.art.240.par.2` flips to `VM`; `et.art.240.par.1`, `et.art.240.par.3` stay `V`. The contador question "¿el inciso que me importa cambió?" is answerable. |
| 3 | **Derogación expresa** ("Deróguese el artículo X") | `DE` | `derogacion_expresa` | optional | Ley 2277/2022 Art. 96: "Deróguese el Art. 158-1 ET." `et.art.158-1` → `DE` with `state_from = 2023-01-01`, `change_source.source_norm_id = ley.2277.2022.art.96`. Skill veredicto in `evals/activity_1_5/art_158_1_ET_AG2025_veredicto.json`. |
| 4 | **Derogación tácita / orgánica** (silent displacement by posterior norm) | `DT` (contested = true unless pronouncement oficial) | `derogacion_tacita` | optional | Sentencia de Unificación 2022CE-SUJ-4-002 (Consejo de Estado, Sección Cuarta) declaró que el procedimiento del Art. 43 Ley 962/2005 desplaza la aplicación de Arts. 588-589 ET para correcciones de imputación. Skill veredicto in `evals/activity_1_5/arts_588_589_ET_correcciones_imputacion_AG2025_veredicto.json`. **Canonicalizer must not flip DT silently — flag for SME when no pronouncement is found.** |
| 5 | **Inexequibilidad — pro futuro** (norm cae desde la sentencia) | `IE` | `sentencia_cc` | optional | C-079/2026 declaró Decreto 1474/2025 inexequible con efectos desde 2026-04-15. norm_id `decreto.1474.2025`: history row with `state = IE`, `state_from = 2026-04-15`. Prior `SP` row gets `state_until = 2026-04-14`. Skill veredicto in `evals/activity_1_5/decreto_1474_2025_veredicto.json`. |
| 6 | **Inexequibilidad — retroactiva** (norm cae desde su origen — invalidates everything in between) | `IE` | `sentencia_cc` with `effect_type = retroactivo` | optional | Hipotético: CC declara una norma inexequible "con efectos retroactivos al 2020-01-01". Row inserts with `state_from = 2020-01-01`, NOT with `state_from = sentencia_date`. **Operational rule: `state_from` is the legal effective date, never the row's `extracted_at`.** Resolver queries between origen and sentencia must now return `IE`. |
| 7 | **Inexequibilidad — diferida** (CC le da plazo al Congreso) | `DI` now, then `IE` later | `sentencia_cc` with `effect_type = diferido` | optional | CC declara una norma "exequible con plazo al Congreso para corregir hasta 2026-12-31; vencido el plazo, queda inexequible." Row 1: `state = DI`, `state_from = sentencia_date`, `state_until = 2026-12-31`. Row 2 (future-dated): `state = IE`, `state_from = 2027-01-01`. Cron must honor future-dated states (§0.7). |
| 8 | **Modulación / condicionamiento** (CC u otro órgano constriñe el sentido sin tumbar el texto) | `EC` if formal CC operative ("EXEQUIBLE en el entendido que..."); `VC` for non-CC modulación o doctrina condicionante | `sentencia_cc` o `doctrina_modulatoria` | optional | C-384/2023 condicionó Art. 11 Ley 2277/2022 (zonas francas) "en el entendido que el régimen del Art. 101 Ley 1819/2016 continúa rigiendo para usuarios calificados antes del 13-dic-2022." Skill veredicto in `evals/activity_1_5/art_11_ley_2277_2022_zonas_francas_AG2023_veredicto.json`. **`veredicto.interpretive_constraint` must capture the literal Court text — no paraphrase.** |
| 9 | **Suspensión provisional CE** (medida cautelar pendiente nulidad de fondo) | `SP` | `auto_ce_suspension` | mandatory (CE often suspende un numeral específico) | Auto 28920/2024 (CE Sección Cuarta, M.P. Milton Chaves) suspendió numerales 12 y 20 del Concepto DIAN 100208192-202. Sentencia 28920/2025-07-03 levantó num. 12; mantuvo num. 20. norm_id `concepto.dian.100208192-202.num.20` history shows: `SP` with `state_from = 2024-12-16`, `state_until = null` (sigue suspendido). Skill veredicto in `evals/activity_1_5/concepto_dian_100208192_202_num20_AG2026_veredicto.json`. |
| 10 | **Nulidad / anulación parcial CE** (CE anula un parágrafo de un decreto reglamentario) | `IE` if anulación con efectos retroactivos; `DE` si pro futuro; whole-norm or sub-unit per the ruling | `sentencia_ce_nulidad` | mandatory | CE anula sólo el parágrafo 3 de un decreto reglamentario; `decreto.XXXX.YYYY.par.3` flips, los siblings no. `effect_type` distingue retroactivo vs pro futuro. |
| 11 | **Reviviscencia normativa** (norma derogante cae → norma anterior revive) | `RV` (or `V` with `change_source.type = reviviscencia` for cascade-aware queries) | `reviviscencia` con `triggering_norm_id` apuntando a la sentencia que tumbó la derogante | optional | Ley 1943/2018 modificó decenas de Arts. ET. C-481/2019 declaró Ley 1943/2018 inexequible íntegramente → CC dijo que las redacciones anteriores reviven. Cuando `ley.1943.2018` history flipped to `IE`, the cascade orchestrator (§0.7, sub-fix 1F) must enqueue re-verify for every norm whose prior history references `ley.1943.2018` as `change_source.source_norm_id`. The cron writes new `RV`/`V` rows on each affected norm. |
| 12 | **Vacatio legis** (publicada pero "rige desde fecha futura") | `VL` now, `V` later | `vacatio` | optional | Ley publicada el 2026-08-01, "rige desde el 2027-01-01." Row 1: `state = VL`, `state_from = 2026-08-01`, `state_until = 2026-12-31`. Row 2 (future-dated): `state = V`, `state_from = 2027-01-01`, `state_until = null`. Resolver `norm_vigencia_at_date(2026-10-01)` returns the `VL` row; `at_date(2027-02-01)` returns the `V` row. |

### §0.2.2 — Two meta-rules (not modes, but they shape resolver design)

**Meta-rule A — Ultractividad / Art. 338 CP.** For impuestos de período (renta principalmente), una reforma vigente en diciembre de año N no aplica al período fiscal en curso si modifica el tributo; aplica desde el período N+1. Concretamente:

- Ley 2277/2022 promulgated 2022-12-13, vigente desde la sanción.
- BUT modifications to renta apply desde AG 2023, not desde diciembre 2022.
- A query "is Art. 240 ET (modificado por Ley 2277) applicable to AG 2022?" must return **no**, even though `state = VM` and `state_from = 2022-12-13`.

This is what `applies_to_kind = per_period` and `applies_to_payload` capture. The resolver function `norm_vigencia_at_date(D)` is insufficient — for impuestos de período we need `norm_vigencia_for_period(periodo, tipo_impuesto)`. **Two resolver functions, not one.** Detail in §0.6.

**Meta-rule B — Conceptos DIAN as weak anchors.** Conceptos and oficios DIAN son doctrina, not norma (Sentencia C-1114/2003: no son vinculantes para el contribuyente, sí para DIAN). They have their own vigencia state machinery — vigente / modificado por concepto posterior / retirado / unificado / tesis declarada nula por CE — and are persisted with the same `norm_vigencia_history` infrastructure. **But:** at retrieval time, a citation whose source is a concepto DIAN is a weaker anchor than a Ley/Decreto citation. The `norm_citations` link table carries an `anchor_strength` column; the synthesis policy gates on it. Detail in §0.11.

### §0.2.3 — What this table does for the schema

Every persistence design decision in §0.3 onward traces back to a row above. If a future mode appears that isn't covered by these twelve + two meta-rules (e.g., a new bilateral-treaty interaction with domestic norms), append a row here first; only then change the schema. This table is the binding empirical content the schema serves.

## §0.3 — Persistence model (three append-only tables + Falkor mirror)

The persistence target is a norm, not a document. A norm has a stable identity (canonical `norm_id`) and a state-transition history (append-only `norm_vigencia_history`). Documents *cite* norms; that link is what the retriever joins through, not a flag on the document itself.

### §0.3.1 — Three Supabase tables

#### Table 1: `norms` — catalog (one row per legal artifact ever)

```sql
CREATE TABLE norms (
    norm_id          text PRIMARY KEY,           -- canonical, per §0.5 grammar
    norm_type        text NOT NULL,              -- articulo_et | ley | ley_articulo |
                                                 --   decreto | decreto_articulo |
                                                 --   res_dian | res_dian_articulo |
                                                 --   concepto_dian | concepto_dian_numeral |
                                                 --   sentencia_cc | auto_ce | sentencia_ce
    parent_norm_id   text REFERENCES norms,      -- e.g. et.art.689-3 -> et;
                                                 --      ley.2277.2022.art.96 -> ley.2277.2022;
                                                 --      et.art.240.par.2 -> et.art.240
    display_label    text NOT NULL,              -- "Art. 689-3 ET — Beneficio de auditoría"
    emisor           text NOT NULL,              -- Congreso | Presidencia | DIAN | CC | CE | …
    fecha_emision    date,                       -- nullable for compiled artifacts (ET as a whole)
    canonical_url    text,                       -- official primary source (Senado / SUIN / DIAN /
                                                 --   relatoría CC / relatoría CE)
    is_sub_unit      boolean NOT NULL DEFAULT false,
    sub_unit_kind    text,                       -- 'parágrafo' | 'inciso' | 'numeral' | 'literal'
                                                 --   when is_sub_unit = true
    created_at       timestamptz NOT NULL DEFAULT now(),
    notes            text                        -- SME notes; not for retrieval
);
CREATE INDEX idx_norms_parent ON norms(parent_norm_id);
CREATE INDEX idx_norms_type   ON norms(norm_type);
```

This is the catalog. Insert-only at ingest time; rows are never deleted (a norm that disappears legally still has a history). Sub-units are first-class rows (see §0.5).

#### Table 2: `norm_vigencia_history` — append-only state transitions

```sql
CREATE TABLE norm_vigencia_history (
    record_id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    norm_id                text NOT NULL REFERENCES norms,
    state                  text NOT NULL,        -- V|VM|DE|DT|SP|IE|EC|VC|VL|DI|RV (§0.4)
    state_from             date NOT NULL,        -- LEGAL effective date (NOT extracted_at)
    state_until            date,                 -- nullable; set when superseded by next row
    applies_to_kind        text NOT NULL,        -- always | per_year | per_period
    applies_to_payload     jsonb NOT NULL,       -- per-period rules (Art. 338 CP, ultractividad)
    change_source          jsonb NOT NULL,       -- structured per §0.3.3 — never free-text
    veredicto              jsonb NOT NULL,       -- full Vigencia value object (§0.11)
    fuentes_primarias      jsonb NOT NULL,       -- [{url, level, fecha_consulta, sha256}]
    interpretive_constraint jsonb,                -- non-null for VC / EC; literal Court text
    extracted_via          jsonb NOT NULL,       -- {skill_version, model, run_id, sources_hash}
    extracted_at           timestamptz NOT NULL DEFAULT now(),
    extracted_by           text NOT NULL,        -- 'cron@v1' | 'ingest@v1' | 'manual_sme:<email>'
    superseded_by_record   uuid REFERENCES norm_vigencia_history,
    supersede_reason       text,                 -- 'periodic_reverify' | 'reform_trigger' |
                                                 --   'cascade_reviviscencia' | 'sme_correction' |
                                                 --   'contradiction_detected'
    -- Append-only enforcement at DB level:
    CONSTRAINT no_state_until_in_future
      CHECK (state_until IS NULL OR state_until >= state_from)
);

-- Block UPDATE / DELETE on this table at the role level. Migrations run as superuser;
-- application role has INSERT-only grants.
REVOKE UPDATE, DELETE ON norm_vigencia_history FROM service_role;
GRANT INSERT, SELECT ON norm_vigencia_history TO service_role;

-- Resolver-supporting indexes (see §0.6 for the resolver functions).
CREATE INDEX idx_nvh_norm_state_from   ON norm_vigencia_history(norm_id, state_from DESC);
CREATE INDEX idx_nvh_supersede         ON norm_vigencia_history(superseded_by_record)
                                                                WHERE superseded_by_record IS NOT NULL;
CREATE INDEX idx_nvh_change_source_id  ON norm_vigencia_history((change_source->>'source_norm_id'))
                                                                WHERE change_source ? 'source_norm_id';
```

**Append-only is non-negotiable.** Corrections never UPDATE; they INSERT a new row that supersedes. The `superseded_by_record` chain plus `supersede_reason` make every state transition queryable. `state_from` is the *legal* effective date — for retroactive inexequibilidades, this can be earlier than `extracted_at` (mode 6 in §0.2.1).

#### Table 3: `norm_citations` — link from corpus chunks to cited norms

```sql
CREATE TABLE norm_citations (
    citation_id    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id       text NOT NULL REFERENCES document_chunks(chunk_id),
    norm_id        text NOT NULL REFERENCES norms,
    mention_span   int4range,                    -- byte range in chunk_text (nullable for inferred)
    role           text NOT NULL,                -- anchor | reference | comparator | historical
    anchor_strength text NOT NULL,               -- ley | decreto | res_dian | concepto_dian | jurisprudencia
                                                 --   ley = strongest; concepto_dian = weakest
    extracted_at   timestamptz NOT NULL DEFAULT now(),
    extracted_via  text NOT NULL                 -- 'canonicalizer@v1' | 'manual_sme'
);
CREATE INDEX idx_nc_chunk ON norm_citations(chunk_id);
CREATE INDEX idx_nc_norm  ON norm_citations(norm_id, role);
```

This replaces the chunk-level `vigencia` column entirely. Retrieval-time vigencia gating becomes:

```sql
-- Concept; full SQL in §0.6:
WHERE NOT EXISTS (
  SELECT 1 FROM norm_citations nc
   JOIN norm_vigencia_at_date(:as_of_date) v USING (norm_id)
  WHERE nc.chunk_id = dc.chunk_id
    AND nc.role = 'anchor'
    AND v.state IN ('DE','SP','IE','VL','DI')   -- and demote VC, EC, DT, RV
)
```

### §0.3.2 — Falkor mirror

`(:Norm {norm_id, norm_type, display_label, parent_norm_id, is_sub_unit})` becomes a first-class node. The state-transition machinery is mirrored as edges between `(:Norm)` and the source artifacts:

```cypher
(:Norm {norm_id: "et.art.158-1"})-[:DEROGATED_BY {
    record_id, state_from, state_until, source_record_id,
    effect_type
}]->(:Norm {norm_id: "ley.2277.2022.art.96"})

(:Norm {norm_id: "et.art.240"})-[:MODIFIED_BY {
    record_id, state_from, state_until, source_record_id,
    affects_sub_units: ["et.art.240.par.2"]
}]->(:Norm {norm_id: "ley.2277.2022.art.10"})

(:Norm {norm_id: "decreto.1474.2025"})-[:STRUCK_DOWN_BY {
    record_id, state_from, effect_type: "pro_futuro"
}]->(:Norm {norm_id: "sent.cc.C-079.2026"})

(:Norm {norm_id: "concepto.dian.100208192-202.num.20"})-[:SUSPENDED_BY {
    record_id, state_from, state_until: null,
    autoridad: "CE Sección Cuarta", auto_id: "auto.ce.28920.2024.12.16"
}]->(:Norm {norm_id: "auto.ce.28920.2024.12.16"})

(:DocumentChunk {chunk_id})-[:CITES {role, anchor_strength, mention_span}]->(:Norm)
```

Edge label set is the v3-extended version of `EdgeKind` from `src/lia_graph/graph/schema.py:23-44`:

| Existing in v2 | New in v3 |
|---|---|
| `MODIFIES`, `SUPERSEDES`, `DEROGATES`, `STRUCK_DOWN_BY`, `SUSPENDS`, `DECLARES_EXEQUIBLE`, `ANULA` | `MODIFIED_BY`, `DEROGATED_BY`, `SUSPENDED_BY`, `INEXEQUIBLE_BY`, `CONDITIONALLY_EXEQUIBLE_BY`, `MODULATED_BY`, `REVIVED_BY`, `CITES`, `IS_SUB_UNIT_OF` |

The Falkor side is rebuilt from `norms` + `norm_vigencia_history` + `norm_citations` by the existing `scripts/sync_*_to_falkor.py` pattern — the back-fill happens in sub-fix 1B-δ.

### §0.3.3 — Structured `change_source`

The single most important deviation from v2: `vigencia_basis` was free-text. Free-text is exactly what made "find every norm whose vigencia changed because of Ley 2277/2022" require NLP. v3 makes it structured.

```typescript
type ChangeSource =
  | { type: 'reforma',                source_norm_id: string,
      effect_type: 'pro_futuro' | 'per_period',
      effect_payload: { tipo_impuesto?: string, period_start?: string, period_end?: string } }
  | { type: 'derogacion_expresa',     source_norm_id: string,
      effect_type: 'pro_futuro' | 'retroactivo',
      effect_payload: { fecha_efectos: string } }
  | { type: 'derogacion_tacita',      source_norm_id: string,
      effect_type: 'pro_futuro',
      effect_payload: {
          contested: boolean,
          official_pronouncement_norm_id?: string,    // sentencia / concepto that confirmed DT
          argumentos_pro?: string,
          argumentos_contra?: string
      } }
  | { type: 'sentencia_cc',           source_norm_id: string,    // C-XXX/AAAA
      effect_type: 'pro_futuro' | 'retroactivo' | 'diferido',
      effect_payload: {
          fecha_sentencia: string,
          plazo_diferido?: string,                    // for DI: when state flips to IE
          condicionamiento_literal?: string           // for EC: literal Court text
      } }
  | { type: 'auto_ce_suspension',     source_norm_id: string,    // auto.ce.NNN.YYYY.MM.DD
      effect_type: 'pro_futuro',
      effect_payload: {
          autoridad: string,                          // 'CE Sección Cuarta' | 'CE Sección Primera'
          consejero_ponente?: string,
          alcance: string,                            // human-readable scope
          numerales_afectados?: string[]              // for partial suspensions
      } }
  | { type: 'sentencia_ce_nulidad',   source_norm_id: string,    // sent.ce.NNN.YYYY.MM.DD
      effect_type: 'pro_futuro' | 'retroactivo',
      effect_payload: { fecha_sentencia: string, alcance: string } }
  | { type: 'reviviscencia',          source_norm_id: string,    // norm that was inexequible
      effect_type: 'pro_futuro' | 'retroactivo',
      effect_payload: {
          triggering_sentencia_norm_id: string,       // C-481/2019
          revives_text_version: string                // e.g. "redacción anterior a Ley 1943/2018"
      } }
  | { type: 'vacatio',                source_norm_id: string,
      effect_type: 'pro_futuro',
      effect_payload: { rige_desde: string } }
  | { type: 'concepto_dian_modificatorio', source_norm_id: string,
      effect_type: 'pro_futuro',
      effect_payload: { fecha_concepto: string, alcance: string } }
  | { type: 'modulacion_doctrinaria',  source_norm_id: string,   // for VC (non-CC)
      effect_type: 'pro_futuro',
      effect_payload: { fuente: string, interpretive_constraint: string } };
```

The discriminated union is enforced at the application layer (`src/lia_graph/vigencia.py` Pydantic model) and stored as JSONB in `norm_vigencia_history.change_source`. JSONB `?` operator + a CHECK constraint on the `type` field enforces shape at the DB level too.

`source_norm_id` is the load-bearing field. Once it's structured, queries like *"every norm affected by Ley 2277/2022"* become:

```sql
SELECT DISTINCT norm_id FROM norm_vigencia_history
 WHERE change_source->>'source_norm_id' LIKE 'ley.2277.2022%';
```

### §0.3.4 — Migration choreography

Sub-fix 1B-γ (§2.4) ships in this order:
1. Migration `20260YYYY000000_norms_catalog.sql` — `norms` table, no data yet.
2. Migration `20260YYYY000001_norm_vigencia_history.sql` — table + INSERT-only role grant + indexes.
3. Migration `20260YYYY000002_norm_citations.sql` — table + indexes.
4. Migration `20260YYYY000003_resolver_functions.sql` — `norm_vigencia_at_date` + `norm_vigencia_for_period` (§0.6).
5. Sub-fix 1B-δ — back-fill `norm_citations` for every existing chunk (§2.5).
6. Sub-fix 1B-ε — rewire `hybrid_search` + `fts_scored_prefilter` to join through `norm_citations` (§2.6).
7. Migration `20260YYYY000004_documents_vigencia_deprecated_view.sql` — `documents.vigencia` becomes a read-only view computed from `norm_vigencia_history` for a one-release deprecation window.
8. Migration `20260YYYY000005_drop_documents_vigencia.sql` — only after all callers migrated.

Each migration includes the explicit `DROP FUNCTION IF EXISTS` dance per `docs/learnings/retrieval/hybrid_search-overload-2026-04-27.md`. No silent overloads.

## §0.4 — Eleven-state enum (V/VM/DE/DT/SP/IE/EC/VC/VL/DI/RV)

The skill ships with seven states. The Colombian mutation surface (§0.2) requires four more. Each state has (a) a citation rule the synthesizer enforces, (b) a retrieval-time demotion factor the resolver returns, and (c) a UI chip variant the frontend renders.

### §0.4.1 — Full state table

| Code | Name | Citation rule | Default demotion | Period-aware? | Chip color | Source mode (§0.2) |
|---|---|---|---|---|---|---|
| **V** | Vigente sin modificaciones | Cite freely | 1.0 | yes (Art. 338 CP for renta) | none (default) | resting state |
| **VM** | Vigente modificada | Cite ONLY current text + chain | 1.0 | yes | blue | mode 1, 2 |
| **DE** | Derogada expresa | Never as vigente; historical only | 0.0 | yes (ultractividad) | red | mode 3 |
| **DT** | Derogada tácita | Only with official pronouncement; flag if contested | 0.3 (uncertain) | yes | orange | mode 4 |
| **SP** | Suspendida provisional CE | Never apply; advertencia + T-series link | 0.0 | yes | yellow | mode 9 |
| **IE** | Inexequible (CC) | Never (unless effects diferidos) | 0.0 | yes (3 sub-modes) | red | modes 5, 6, 7 |
| **EC** | Exequibilidad condicionada (CC formal) | Cite WITH literal Court text | 1.0 | yes | purple | mode 8 (CC formal) |
| **VC** | Vigente condicionada (modulación non-CC) | Cite WITH the modulating constraint (literal text required) | 1.0 | yes | purple-light | mode 8 (non-CC) |
| **VL** | Vacatio legis (publicada, no rige aún) | Never as vigente; flag "rige desde [fecha]" | 0.0 (until rige_desde) | yes (period-bound) | gray | mode 12 |
| **DI** | Diferida (CC le dio plazo al Congreso) | Cite as vigente con plazo de expiración explícito | 1.0 (until plazo) | yes | yellow-stripe | mode 7 (sub-mode) |
| **RV** | Revivida (resucitada por inexequibilidad de la norma derogante) | Cite WITH the reviviscencia chain | 1.0 | yes (the `revives_text_version` matters) | green-stripe | mode 11 |

### §0.4.2 — State transitions are append-only rows, not mutations

Every transition is a new `norm_vigencia_history` row. The prior row's `state_until` gets set in the same transaction; the prior row's `superseded_by_record` points to the new row. Examples:

- **V → VM** (Art. 240 modified by Ley 2277): two rows. Row 1 (`V`, state_from=2017-01-01, state_until=2022-12-31, superseded_by=record_2). Row 2 (`VM`, state_from=2023-01-01, state_until=null, change_source.source_norm_id=ley.2277.2022.art.10).
- **SP → IE** (Decreto 1474/2025 → C-079/2026): two rows. Row 1 (`SP`, state_from=2025-XX-XX, state_until=2026-04-14, superseded_by=record_2). Row 2 (`IE`, state_from=2026-04-15, change_source=sentencia_cc with effect_type=pro_futuro).
- **V → DI → IE** (CC declares inexequible diferido): three rows. Row 1 (`V` until plazo announcement). Row 2 (`DI`, state_from=plazo announcement, state_until=plazo deadline). Row 3 (`IE`, future-dated state_from=plazo deadline+1, written at announcement time).
- **VM → RV** (Ley 1943 modifies Art. 240; C-481/2019 declares Ley 1943 inexequible; reviviscencia revives prior text): three rows on `et.art.240`. Row 1 (`V` until 2018-12-28). Row 2 (`VM`, state_from=2019-01-01, change_source=reforma source=ley.1943.2018). Row 3 (`RV`, state_from=2019-10-XX, change_source=reviviscencia with triggering_sentencia=sent.cc.C-481.2019).

### §0.4.3 — Demotion factor lives with the resolver, not the state

The default demotion factor in §0.4.1 is what the resolver returns. The retriever multiplies a chunk's RRF score by `demotion_factor` for every anchor citation it carries. A chunk citing only `V` norms keeps full score; a chunk citing one `DT` anchor gets multiplied by 0.3; a chunk citing any `DE/SP/IE/VL` anchor is filtered (factor 0). Per-period queries use the period-aware factor (§0.6).

## §0.5 — Norm-id grammar (six artifact types, sub-units first-class)

The canonical `norm_id` is the single most important schema decision in v3. It must (a) round-trip from how Colombian legal practice cites norms, (b) hierarchically capture sub-units without column rot, (c) cover the six artifact types, (d) be deterministic so the canonicalizer never produces two different ids for the same norm.

### §0.5.1 — Grammar

```
norm_id        := artifact_id ('.' sub_unit)*
artifact_id    := et_id | ley_id | decreto_id | resolucion_id | concepto_id | jurisprudencia_id

et_id          := 'et' [ '.art.' article_number ]
                  -- 'et' alone = the ET as a whole; 'et.art.689-3' = an article;
                  -- 'et.art.689-3.par.2' = a parágrafo

ley_id         := 'ley.' year '.' number [ '.art.' article_number ]
                  -- 'ley.2277.2022' = the law; 'ley.2277.2022.art.96' = an article

decreto_id     := 'decreto.' number '.' year [ '.art.' article_number ]
                  -- 'decreto.1474.2025'; 'decreto.1625.2016.art.1.2.1.2.1' = DUR sub-numbering

resolucion_id  := 'res.' emisor '.' number '.' year [ '.art.' article_number ]
                  -- emisor ∈ {dian, mintic, supersociedades, ugpp, ...};
                  -- 'res.dian.165.2023'; 'res.dian.165.2023.art.5'

concepto_id    := 'concepto.' emisor '.' number [ '.num.' numeral ]
                  -- 'concepto.dian.100208192-202';
                  -- 'concepto.dian.100208192-202.num.20'

jurisprudencia_id :=
                | 'sent.cc.' citation                        -- 'sent.cc.C-481.2019'
                | 'sent.ce.' citation_with_date              -- 'sent.ce.28920.2025.07.03'
                | 'auto.ce.' citation_with_date              -- 'auto.ce.28920.2024.12.16'

sub_unit       := ('art.' n) | ('par.' n) | ('inciso.' n) | ('num.' n) | ('lit.' letter)
                  -- 'par.2', 'par.transitorio.1', 'inciso.3', 'num.20', 'lit.b'

year           := 4-digit
number         := digit+ ('-' digit+)?              -- handles ET '689-3', concepto '100208192-202'
article_number := digit+ ('-' digit+)?
n              := digit+ | identifier              -- 'transitorio', 'unico'
citation       := identifier '-' digit+ '.' year   -- 'C-481.2019', 'T-077.2022'
citation_with_date := digit+ '.' year '.' MM '.' DD
emisor         := lowercase identifier              -- canonicalizer normalizes
identifier     := [a-z][a-z0-9_]*
```

### §0.5.2 — Six artifact types, with quirks

1. **Estatuto Tributario** — special prefix `et` because the ET is the most-cited artifact in the corpus by an order of magnitude. Article numbers can have dashes (`689-3`, `158-1`); sub-units are `par.N`, `inciso.N`, `num.N`, `lit.X`. The ET has no year in its id (it's compiled by Decreto 624/1989; that's metadata in the catalog, not in the id).
2. **Leyes** — `ley.NUMBER.YEAR`. Article references append `.art.NUMBER`. **Year-after-number** is the canonical form to match how Colombian legal practice writes it ("Ley 2277 de 2022" → `ley.2277.2022`).
3. **Decretos** — `decreto.NUMBER.YEAR`. The DUR (Decreto Único Reglamentario 1625/2016) has the worst case: hierarchical sub-numbering like Art. 1.2.1.2.1.2. **Decision: flatten with dots into `decreto.1625.2016.art.1.2.1.2.1.2`.** The `.` separator is already conventional in DUR and doesn't collide with the grammar's structural delimiters because DUR sub-numbering only ever appears after `.art.`. Reserved.
4. **Resoluciones** — `res.EMISOR.NUMBER.YEAR`. The `EMISOR` slot is enumerated (DIAN, MinTIC, SuperSociedades, UGPP, etc.). The canonicalizer keeps a registry; new emisores require an entry but no schema change.
5. **Conceptos / oficios DIAN** — `concepto.dian.NUMBER` (no year — DIAN concept numbers are unique without it). Numerales appended as `.num.N`. **Concepto numbers can include dashes** (`100208192-202`), already handled by the `number` rule.
6. **Jurisprudencia** — three sub-types because Colombian courts use different citation conventions:
    - **Corte Constitucional** (`sent.cc.`): citation has a letter prefix (C, T, SU, A) and a year (`C-481.2019`, `T-077.2022`). Date is metadata.
    - **Consejo de Estado sentencias** (`sent.ce.`): cited by expediente number plus date. Use `NNNNN.YYYY.MM.DD` to disambiguate (CE issues multiple sentencias per expediente).
    - **Consejo de Estado autos** (`auto.ce.`): same shape as sentencias; date is the auto date. SP cases (mode 9) use this.

### §0.5.3 — Sub-units are first-class rows

The canonicalizer creates a row in `norms` for every sub-unit cited anywhere in the corpus. `et.art.689-3` and `et.art.689-3.par.2` are two separate rows; `parent_norm_id` links them. **This is non-negotiable per the operator's mutation surface audit:** Colombian reformas modify at sub-unit level constantly. A `sub_unit` text column on a single row would force a choice between re-versioning the whole article on every parágrafo change (loses granularity) or letting the column rot into free text (loses queryability).

### §0.5.4 — Canonicalizer obligations

The canonicalizer module (`src/lia_graph/canon.py`, new in v3) takes a free-text mention from corpus prose and returns a canonical `norm_id`, or refuses if the mention is ambiguous.

Worked round-trips:

| Free-text mention | Canonical norm_id |
|---|---|
| "Art. 689-3 ET" | `et.art.689-3` |
| "art 689-3 et" | `et.art.689-3` |
| "el artículo 689-3 del Estatuto Tributario" | `et.art.689-3` |
| "Estatuto Tributario, articulo 689-3" | `et.art.689-3` |
| "Art. 689-3 ET parágrafo 2" | `et.art.689-3.par.2` |
| "Art. 689-3, par. 2 ET" | `et.art.689-3.par.2` |
| "Ley 2277 de 2022, Art. 96" | `ley.2277.2022.art.96` |
| "art 96 ley 2277/2022" | `ley.2277.2022.art.96` |
| "Decreto 1474 de 2025" | `decreto.1474.2025` |
| "Concepto DIAN 100208192-202 numeral 20" | `concepto.dian.100208192-202.num.20` |
| "Sentencia C-481 de 2019" | `sent.cc.C-481.2019` |
| "Auto del 16 de diciembre de 2024 (CE Sección Cuarta, expediente 28920)" | `auto.ce.28920.2024.12.16` |

**Refusal cases the canonicalizer must enforce:**

- "Decreto 1474" without year → ambiguous (multiple Decretos 1474 across years exist) → refuse.
- "Art. 240" without ET prefix → ambiguous (could be Art. 240 of any law) → refuse unless context is locked.
- "Sentencia de la Corte sobre zonas francas" → not a citation → refuse.
- "según la DIAN..." with no concepto number → not a citation → refuse.

Refusal returns `None` plus a structured `CanonicalizerRefusal` reason; the caller decides whether to log + skip or escalate to SME.

### §0.5.5 — Migration of pre-v3 free-text references

Sub-fix 1B-δ (§2.5) walks every existing `document_chunks.chunk_text` and `documents.vigencia_basis` value, runs the canonicalizer, and populates `norm_citations`. Mentions the canonicalizer refuses are logged to `evals/canonicalizer_refusals_v1/refusals.jsonl` for SME review. The refusal queue is itself a useful artifact — it surfaces ambiguous citation patterns the SME can disambiguate once and bake into the canonicalizer's rules.

## §0.6 — Two resolver functions (Art. 338 CP rationale)

A single resolver `norm_vigencia_at_date(D)` is sufficient for instantaneous taxes (IVA, retención en la fuente, GMF, timbre) and for procedimiento (firmeza, plazos, sanciones). It is **not** sufficient for impuestos de período because Art. 338 CP introduces a per-period applicability rule that diverges from the legal `state_from`. Two resolvers, one query intent each, picked by the planner.

### §0.6.1 — Why one resolver isn't enough

Worked example. Ley 2277/2022 was promulgated 2022-12-13 and is *legally vigente* desde la sanción. By Art. 338 CP, las modificaciones que la Ley introdujo a impuestos de período (renta) only apply desde el período fiscal *siguiente* a la promulgación — AG 2023, not AG 2022. So:

| Question | Correct answer | What `norm_vigencia_at_date` returns | What `norm_vigencia_for_period` returns |
|---|---|---|---|
| "Today (2026-04-27), is Art. 240 ET (modified by Ley 2277) vigente?" | yes (`VM`) | `VM`, demotion 1.0 ✅ | `VM`, demotion 1.0 ✅ |
| "Did Art. 240 ET (modified by Ley 2277) apply to AG 2023 renta?" | yes | `VM`, demotion 1.0 ✅ | `VM`, demotion 1.0 ✅ |
| "Did Art. 240 ET (modified by Ley 2277) apply to AG 2022 renta?" | **no** (Art. 338 CP — modification doesn't reach AG 2022) | would return `VM` ❌ wrong | returns `V` (prior version), demotion 1.0 ✅ |
| "Did Art. 240 ET (modified by Ley 2277) apply to retención en la fuente del 2022-12-15?" | yes (instantaneous, post-promulgación) | `VM`, demotion 1.0 ✅ | n/a — wrong resolver for an instantaneous tax |

The first resolver answers "what did the legal record say on date D?" The second answers "what norm version applies to a fiscal period of impuesto X?" These are different questions.

### §0.6.2 — Resolver function signatures

```sql
-- Resolver 1: instantaneous-tax / procedimiento queries.
-- Returns the row whose state_from <= as_of_date < state_until (or state_until IS NULL).
CREATE FUNCTION norm_vigencia_at_date(as_of_date date)
RETURNS TABLE (
    norm_id          text,
    state            text,
    state_from       date,
    state_until      date,
    record_id        uuid,
    change_source    jsonb,
    interpretive_constraint jsonb,
    demotion_factor  numeric             -- per §0.4.3
) ...;

-- Resolver 2: impuestos de período (renta primarily; expand as needed).
-- Honors Art. 338 CP: a reforma vigente in year N applies to AG N+1, not AG N.
CREATE FUNCTION norm_vigencia_for_period(
    impuesto         text,                -- 'renta' | 'iva' | 'retefuente' | 'ica' | 'patrimonio'
    periodo_year     int,                 -- AG 2025
    periodo_label    text DEFAULT NULL    -- nullable; carries 'AG 2025' or 'bimestre 3-4 2026'
)
RETURNS TABLE (
    norm_id          text,
    state            text,
    state_from       date,
    state_until      date,
    record_id        uuid,
    change_source    jsonb,
    interpretive_constraint jsonb,
    norm_version_aplicable text,         -- e.g. "redacción anterior a Ley 2277/2022"
    demotion_factor  numeric,
    art_338_cp_applied boolean           -- true when the per-period rule shifted the result
) ...;
```

`norm_vigencia_for_period` consults `applies_to_kind` and `applies_to_payload` per row. The skill emits these fields in the veredicto (§0.11). For renta with a row whose `applies_to_kind = 'per_period'`, the function picks the row whose payload `period_start` <= `(periodo_year + 1)-01-01` <= `period_end`, falling back to the most recent prior row whose payload covers the period. The exact algorithm is in `src/lia_graph/pipeline_d/vigencia_resolver.py` — language-level, not SQL — because the period-arithmetic is messy enough that an SQL function would be unmaintainable.

### §0.6.3 — Retriever consumption

The planner already extracts a date or year hint when a query mentions a period ("para 2018", "AG 2024", "el dividendo del año pasado"). v3 extends the planner contract (`pipeline_d/contracts.py`) with two fields:

```python
@dataclass(frozen=True)
class GraphRetrievalPlan:
    # ... existing fields ...
    vigencia_query_kind: Literal['at_date', 'for_period'] | None
    vigencia_query_payload: dict | None  # {'as_of_date': date} | {'impuesto': str, 'periodo_year': int}
```

When `vigencia_query_kind` is `at_date`, the retriever joins through `norm_vigencia_at_date(:as_of_date)`. When `for_period`, it joins through `norm_vigencia_for_period(:impuesto, :periodo_year)`. When `None` (most queries that don't have a period cue), default to `at_date(today)`.

Falkor traversal symmetrical: Cypher predicates call out to a server-side function or compute the period-aware factor in the retriever's Python wrapper (`pipeline_d/retriever_falkor.py`). The Falkor side does NOT replicate the SQL function — it joins to property-bag data emitted at sync time, then the wrapper computes period-applicability in Python. Cleaner than coupling Falkor to PostgreSQL.

### §0.6.4 — Test surface

For 1B-ε ship gate (week 9), the resolver must pass on 30 SME-curated `(norm_id, query_kind, payload)` test pairs covering:
- 8 pairs on `at_date` semantics (V/VM/DE/SP/IE/EC at varying dates).
- 12 pairs on `for_period` semantics (Art. 338 CP shift cases — 4 per impuesto × 3 impuestos).
- 4 pairs on ultractividad (DE norm continues to apply to past hechos económicos).
- 4 pairs on future-dated states (VL queried during vacatio; DI queried after plazo).
- 2 pairs on EC/VC (literal interpretive_constraint surfaces in the result).

Test fixtures live at `evals/resolver_v1/<case_id>.yaml`; runner is `scripts/eval/run_resolver_eval.py` reusing the existing `scripts/eval/engine.py` plumbing.

## §0.7 — Cascade orchestration (reviviscencia + future-dated states)

Two operational rules force an orchestration layer above the resolver: (a) reviviscencia — a single new history row can require dozens of cascade rows on other norms; (b) future-dated states — a row written today with `state_from > today` must trigger a state flip on its own at the right moment without an explicit re-verify. Postgres trigger functions could implement both. v3 explicitly rejects them in favor of cron-driven orchestration.

### §0.7.1 — Reviviscencia handler

The canonical case: Ley 1943/2018 modified dozens of ET articles. C-481/2019 declared Ley 1943/2018 inexequible íntegramente, with reviviscencia of the prior text per CC doctrine. When the row that flips `ley.1943.2018` to `IE` lands, the system must:

1. Identify every norm whose `norm_vigencia_history` references `ley.1943.2018` as `change_source.source_norm_id`.
2. For each, queue a re-verify task with `supersede_reason = 'cascade_reviviscencia'` and `triggering_norm_id = sent.cc.C-481.2019`.
3. The cron picks up the queue, runs the skill on each, and inserts new rows. The new rows will typically have `state = RV` (revivida) or `state = V` (re-vigente con texto anterior), with `change_source.type = 'reviviscencia'` and the `revives_text_version` field populated.

The orchestration code lives in `src/lia_graph/pipeline_d/vigencia_cascade.py` (sub-fix 1F, §2.8). It is a pure read-from-Postgres + write-to-job-queue module; no Postgres triggers.

**Why not Postgres triggers.** Triggers feel clever (zero-latency cascade, no external coordinator) and become invisible operational tax: they're hard to test, hard to disable for backfills, hard to reason about under transaction interleaving, and they couple the schema to a specific DB engine. v3's writer is an explicit cron tick; the cascade is one of its responsibilities. This matches the rest of the project (Re-Verify Cron at week 4-5 is already cron-driven; vigencia cascades inherit that same operational shape).

### §0.7.2 — Future-dated states

VL (vacatio legis) and DI (diferida) both write rows where `state_from > today`. The resolver functions naturally honor this: queries for a date earlier than `state_from` return the prior row; queries on or after `state_from` return the future row. No transition is needed.

But cascade orchestration must be aware of three operational facts:

1. **DI rows ship in pairs** with a future-dated IE companion. When a DI row lands with `state_until = D` and a future-dated IE row exists with `state_from = D+1`, the cascade orchestrator schedules a "state flip notification" at `D+1` that re-runs any cited-elsewhere norms. The flip itself is automatic (resolvers honor it); the *re-verification* of cascading effects is what's scheduled.
2. **VL → V** (publicación → entrada en vigor) is similar: at `rige_desde`, the cascade orchestrator triggers re-verify of any norm the new V references via `parent_norm_id` or via earlier `change_source` chains.
3. **Re-Verify Cron periodically scans for "soon-to-flip" rows** (`state_until` within next 30 days OR future-dated rows with `state_from` within next 30 days). Operator gets a heads-up via the heartbeat pattern (`scripts/monitoring/ingest_heartbeat.py` shape, per CLAUDE.md long-running-job convention) — "5 norms about to flip state in the next 30 days; re-verification queued."

### §0.7.3 — Retrieval-time contradiction detection (refusal, never silent fix)

When `pipeline_d/answer_synthesis.py` (via the resolver and `vigencia_cascade.detect_inconsistency`) sees:

- Two anchor citations on the same norm whose retrieved chunks predate different history rows, OR
- An answer that would cite a norm whose current state is `DE/SP/IE/VL/DI` without the chip, OR
- A `for_period` query whose result contradicts an `at_date` query result on the same norm at the period midpoint,

the orchestrator does NOT mid-turn-research. It (a) refuses the offending citation via the existing coherence gate (`fallback_reason = vigencia_inconsistency`), (b) enqueues a re-verify task on the relevant norm with `supersede_reason = 'contradiction_detected'`, and (c) the next cron tick picks it up. The user gets an honest "no encontré evidencia consistente sobre X — verificación en curso"; the cron writes the corrected row; subsequent queries return clean.

**Why not mid-turn research.** Three reasons:

1. **Latency.** Skill invocation with scrapers is 60–300 seconds. Mid-turn budget is 5–15 seconds.
2. **Determinism.** Mid-turn research means the same query at two different times returns different evidence. Reproducibility breaks.
3. **Feedback loop.** Mid-turn writes from retrieval back to `norm_vigencia_history` would mean retrieval triggers writes that change retrieval. Unbounded loop unless rate-limited; rate-limiting recreates the cron with extra steps.

The cron is the single-writer; refusal is the user-facing contract. This is a strict subset of v2's framing — v2 implied mid-turn was possible; v3 rules it out.

### §0.7.4 — Cascade orchestrator API

```python
# src/lia_graph/pipeline_d/vigencia_cascade.py — sub-fix 1F

class VigenciaCascadeOrchestrator:
    """Sole consumer of NEW INSERTs into norm_vigencia_history.
    Cron-invoked; never invoked from retrieval path."""

    def on_history_row_inserted(self, record: NormVigenciaHistoryRow) -> CascadeResult:
        """Inspect the new row; enqueue re-verify tasks for cascading effects.
        Idempotent: re-running on the same record produces the same queue."""

    def on_periodic_tick(self, now: datetime) -> CascadeResult:
        """Periodic sweep: detect (a) state_until expirations within 30d,
        (b) future-dated rows with state_from within 30d, (c) reform-trigger
        norms whose extracted_at is older than freshness window."""

    def detect_inconsistency(
        self, citations: Sequence[Citation], as_of: date
    ) -> InconsistencyReport | None:
        """Read-only consumer used from retrieval. Returns the inconsistency
        signature for the coherence gate to refuse on. Never writes."""
```

The cron's job runner calls `on_history_row_inserted` after every INSERT (the cron also owns the writes, so it has the record handy) and `on_periodic_tick` on a 6-hour cadence. `detect_inconsistency` is the read-side method retrieval uses.

### §0.7.5 — Cron deployment

The Re-Verify Cron (sub-fix in v2 §1, week 4-5) becomes the host for vigencia-cascade in v3. Same deployment shape (Railway scheduled job; nohup-detached worker on staging), same heartbeat pattern. Functional split:

- `cron/reverify_periodic.py` — periodic norm freshness checks (the v2-planned scope).
- `cron/cascade_consumer.py` — consumes the re-verify queue from `on_history_row_inserted` and `on_periodic_tick`.
- `cron/state_flip_notifier.py` — DI → IE / VL → V notifications.

Single binary, three entry points. Detail in sub-fix 1F (§2.8).

## §0.8 — Required reading before you write any code (90 min, in this order)

Carries v2's reading list forward; the order matters because v3's persistence redesign rests on understanding why v2's column-shaped approach was insufficient.

1. **`CLAUDE.md`** (repo root, ~6 KB) — non-negotiables, run modes, hot path, decision rules. Pay attention to the six-gate lifecycle policy + the long-running-job convention. Mandatory.
2. **`AGENTS.md`** (repo root) — layer ownership and surface boundaries (`main chat` vs `Normativa` vs `Interpretación` are distinct surfaces).
3. **`docs/orchestration/orchestration.md`** (~30 KB) — full architecture. The versioned env matrix at the bottom is authoritative.
4. **`docs/orchestration/retrieval-runbook.md`** — line-level walkthrough of `pipeline_d/retriever_supabase.py` + `retriever_falkor.py`. Sub-fix 1B-ε rewrites the join surface here.
5. **`docs/orchestration/coherence-gate-runbook.md`** — every refusal mode (`fallback_reason`) mapped to its origin file:line. Sub-fix 1F adds `vigencia_inconsistency` here.
6. **`docs/learnings/README.md`** + scan the file list under `docs/learnings/{retrieval,ingestion,process}/` — closed-fix lessons. Read fully any whose title sounds adjacent to your fix. Especially: `vigencia-binary-flag-too-coarse.md`, `vigencia-2d-model.md`, `corpus-hallucinated-content-EME-A01.md`, `skill-as-verification-engine.md`, `re-verify-cron-criticality.md`.
7. **`docs/re-engineer/makeorbreak_v1.md`** §0 + §2 (~15 min — the founder's view of what was broken).
8. **`docs/re-engineer/skill_integration_v1.md`** — the change-driver behind v2 (the skill design). Its data shapes are the seed for v3's contracts.
9. **`docs/re-engineer/sme_corpus_inventory_2026-04-26.md`** — the SME's 24-law authoritative inventory; binding for any "is this doc safe to flag?" question.
10. **`.claude/skills/vigencia-checker/SKILL.md`** + scan of references and checklists (~20 min). The skill IS the verification protocol. v3's persistence model is the storage half of the equation; the skill is the production half.
11. **`docs/re-engineer/fixplan_v2.md`** §0–§0.8 (~30 min — the previous design). Read **specifically** to understand the per-document column approach v3 replaces. The breaks in v2's persistence target are the ones v3 §0 break 6 enumerates.
12. **`docs/re-engineer/fixplan_v3.md`** — this document. §0.2 (mutation surface), §0.3 (persistence model), §0.5 (norm-id grammar), §0.6 (resolvers), §0.7 (cascade) are all load-bearing for any sub-fix.
13. **The 4 already-extracted veredictos** in `evals/activity_1_5/*.json` (~10 min — see what the skill output looks like on real norms).
14. **The 3 Activity 1.7 veredictos** in `evals/activity_1_5/{concepto_dian_100208192_202_num20,art_11_ley_2277_2022_zonas_francas,arts_588_589_ET_correcciones_imputacion}*_veredicto.json` (~10 min — DT/SP/EC validated cases).
15. **`evals/activity_1_5/persistence_audit.jsonl`** (~5 min — the Activity 1.5b audit log; shows the exact write paths and what shape the smoke set took).

If you read nothing else: this document §0–§0.7, `CLAUDE.md`, the two runbooks, the skill's `SKILL.md`, and the 7 veredicto fixtures. Everything else is reference.

## §0.9 — Project conventions every fix must follow

These are not preferences; they are mandatory. Items marked **(NEW v3)** are the persistence-redesign deltas vs v2.

| Convention | Where it lives | What it means for your fix |
|---|---|---|
| **Six-gate lifecycle** | `docs/aa_next/README.md` + `CLAUDE.md` | Every pipeline change passes idea → plan → measurable success criterion → test plan → greenlight → refine-or-discard. Unit tests green ≠ improvement. |
| **Tests via `make test-batched`** | `Makefile` + `tests/conftest.py` guard | Conftest aborts unless `LIA_BATCHED_RUNNER=1`. Single tests: `PYTHONPATH=src:. uv run pytest tests/test_X.py -q`. |
| **Migrations apply via `supabase db push --linked`** | per Activity 1 + v5 §1.D workflow | Cloud writes pre-authorized for Lia Graph (NOT LIA_contadores). Announce in one line, then execute. |
| **`CREATE OR REPLACE FUNCTION` requires explicit `DROP FUNCTION IF EXISTS` first when changing parameter list** | `docs/learnings/retrieval/hybrid_search-overload-2026-04-27.md` | Verified the hard way 2026-04-27. Do NOT relearn. |
| **Env matrix bump on any launcher / `LIA_*` / `query_mode` change** | `docs/orchestration/orchestration.md` | Bump version + change-log row + mirror tables in `env_guide.md` + `CLAUDE.md` + `/orchestration` HTML. |
| **Time format: Bogotá AM/PM for user surfaces; UTC ISO for machine logs** | `feedback_time_format_bogota.md` | Helpers in `scripts/eval/engine.py:bogota_now_human()`. |
| **Reuse `scripts/eval/engine.py` for any new chat-based eval** | (extracted 2026-04-27 §1.G) | `ChatClient`, `post_json`, `append_jsonl`, `completed_ids`, `git_sha`, `write_manifest`. Do not write a third copy. |
| **Atomic-design first for any UI** | `feedback_atomic_design_first.md` | Read `frontend/src/shared/ui/atoms+molecules` BEFORE writing UI. v3 sub-fix 1D's 11 chips mirror `subtopicChip.ts`. |
| **Plain-language reports to operator** | `feedback_plain_language_communication.md` | Status reports default to short, jargon-free. |
| **No threshold lowering on missed gates** | `feedback_thresholds_no_lower.md` | Document exception per case; do NOT relax. |
| **Long-running Python jobs: detached + heartbeat** | `CLAUDE.md` last section | `nohup + disown + > log 2>&1` (NO tee). 1B-β extractor batch + cascade worker hit this. |
| **`pyproject.toml` entry points + run modes** | repo root + `scripts/dev-launcher.mjs` | `lia-ui`, `lia-graph-artifacts`, `lia-deps-check`. v3 may add `lia-cascade` or fold cascade into `lia-graph-artifacts`. |
| **Vigencia veredicto requires skill invocation** | `.claude/skills/vigencia-checker/SKILL.md` | Any code or content that asserts vigencia/derogación MUST consume the skill's veredicto. No code path may write a `Vigencia` value object that wasn't produced by the skill or by an SME-signed manual override (with audit trail). |
| **Burden-of-proof inversion** | Skill's principio rector | Extractor / classifier MUST refuse to emit a veredicto if double-primary-source verification is incomplete. Refusing is success; guessing is failure. |
| **Per-parágrafo granularity** | Skill's `tipologia-modificaciones.md` | Vigencia state is per-parágrafo, not just per-article. v3 promotes this from "implementations must accept" to "sub-units are first-class norm-ids" (§0.5). |
| **Audit-LIA TRANCHE as judge schema** | Skill's `patrones-citacion.md` §"Integración" | Fix 5 golden judge MUST emit INCORRECTO/INCOMPLETO/OMISIÓN + GRAVEDAD CRÍTICO/MAYOR/MENOR. |
| **(NEW v3) Vigencia is norm-keyed, never doc-keyed** | This document §0 break 6 + §0.3 | No code path may write vigencia state to `documents.vigencia` after sub-fix 1B-γ ships. The deprecation view exists for one release; subsequent writes go to `norm_vigencia_history`. |
| **(NEW v3) `change_source` MUST be the §0.3.3 discriminated union** | This document §0.3.3 | Free-text `vigencia_basis` is gone. Every history row has structured `change_source` with a fixed `type` enum; `source_norm_id` references a real `norms.norm_id` that exists in the catalog. |
| **(NEW v3) Sub-units are first-class norm_ids** | This document §0.5.3 | When ingesting / extracting / refusing on a parágrafo or numeral, use `et.art.240.par.2` — never re-version the whole `et.art.240` for a sub-unit change. The `norms` catalog INSERT is one-time; the granularity is permanent. |
| **(NEW v3) Append-only history; corrections are new rows** | This document §0.3.1 | `norm_vigencia_history` rejects UPDATE and DELETE at the role grant level. Corrections INSERT a new row that supersedes via `superseded_by_record`. Rolling back = inserting a "correction" row, never editing. |
| **(NEW v3) Cascade is cron-driven; no Postgres triggers; no mid-turn research** | This document §0.7 | Reviviscencia, future-dated state flips, and contradiction-detection ALL flow through the cron. Retrieval refuses on inconsistency; the cron writes the fix. No code path may invoke the skill from inside a request handler. |
| **(NEW v3) Two resolver functions; planner picks** | This document §0.6 | Retrieval calls `norm_vigencia_at_date(D)` for instantaneous tax / procedimiento queries; `norm_vigencia_for_period(impuesto, year)` for impuestos de período. Planner extracts the cue; default is `at_date(today)`. |
| **(NEW v3) Canonicalizer refusal is success, not failure** | This document §0.5.4 | When a free-text mention is ambiguous ("Decreto 1474" without year), the canonicalizer returns refusal + reason. Refusals are logged for SME triage; never silently guessed. |
| **(NEW v3) Local-docker-first validation** | `state_fixplan_v3.md` §7.8 | Every migration / batch / sink / cron MUST validate in `npm run dev` (local Supabase docker + local FalkorDB docker) before any staging cloud write. Engineer runs sub-fix's H0 + H1 tests + a single-fixture smoke locally first; updates §7.7 dev cell to ✅; then `supabase db push --linked` for staging; smokes in staging; updates §7.7 staging cell. Production deploys additionally require ≥ 48h staging soak + operator green-light. |
| **(NEW v3) Reversibility before gate-3** | `state_fixplan_v3.md` §5 | Every action of class R2/R3/R4/R5 must have a row in the reversibility matrix BEFORE the sub-fix can advance to gate-3. R3 actions ship UP + DOWN scripts together; R4 actions ship with snapshot procedure; R5 actions require operator green-light per action. PR review enforces. |
| **(NEW v3) Test horizon discipline** | `state_fixplan_v3.md` §6 | Engineers consult §6.2 BEFORE running tests. Sub-fixes marked "DO NOT test at H0" produce false-fail noise if tested prematurely. Skipped tests get logged in §10 run log with the reason; failed tests treated as noise unless engineer can prove the sub-fix is at the right horizon. |
| **(NEW v3) State file is the operational ledger** | `state_fixplan_v3.md` §1 | Engineers update `state_fixplan_v3.md` on every gate crossing (§3, §4, §10), every deploy (§7), every failure (§10 + §9), every SME signoff (§4 + §10). Cron heartbeats append every 6h. Operator reads §3 + §10 first when something breaks. |

## §0.10 — The vigencia-checker skill (15-min skim, unchanged from v2)

**What it is.** A complete verification protocol for Colombian tax-law vigencia, delivered by SME 2026-04-26 evening, installed at `.claude/skills/vigencia-checker/`. 8 files, 1428 LOC. Acts as both:

1. **A reference taxonomy + procedure** that engineers and the LLM consult when reasoning about vigencia.
2. **An invocable agent loop** that produces structured veredictos for any specific norm + period.

**The 7 states the skill ships with.** All vigencia analysis collapses into exactly one of V/VM/DE/DT/SP/IE/EC per the skill. v3 extends this to 11 states (§0.4) by adding VC/VL/DI/RV — these are produced by the same skill protocol but require the skill prompt + reference docs to be updated. The update is part of sub-fix 1A (§2.1).

**The 2D model** (formal × period). A norm's veredicto is `(state, applicability_to_period)`. State is global; applicability is per-period. A norm can be DE today but apply to AG 2023 by ultractividad. A norm can be V today but not apply to AG 2025 by Art. 338 CP. v3 §0.6's two resolvers are the persistence-side expression of this 2D model.

**The 5-step flow** (mandatory): Identification → ≥ 2 primary sources → Temporal-fiscal verification → Tácita-derogation + active-demands check → Structured veredicto OR refusal-with-incertidumbre. Unchanged from v2.

**When to invoke.** Skill activates automatically when LLM activity touches: artículo / decreto / ley / resolución number; verbs *aplica / rige / vigente / fue modificado / fue derogado*; questions like *¿puedo aplicar X para AG 2024?*; or any mention of recent reformas. Does NOT activate for abstract conceptual questions or pure aritmética.

**When the skill refuses.** No primary source available; primary sources contradict; demanda activa without sentencia o medida cautelar; speculative future reformas; municipal norms without gaceta digital. **Refusing IS the correct output in those cases.**

**v3 update needed (sub-fix 1A scope):** the skill prompt + `references/tipologia-modificaciones.md` + `patrones-citacion.md` need extensions for VC/VL/DI/RV plus the structured `change_source` output format. SME-led; engineer integrates the updated skill into the harness.

## §0.11 — Skill invocation mechanics + data contracts (v3 update)

The skill's invocation mechanics are unchanged from v2 §0.8.1–§0.8.2: Gemini 2.5 Pro via the project's existing OpenAI-compatible adapter, tool-use loop wrapping the 5 scrapers, `temperature=0.1`. The data **contracts** evolve to encode the persistence model — v2's `Vigencia` JSON shape was sufficient for column writes; v3's must support 11 states, structured `change_source`, sub-unit norm_ids, future-dated rows, and anchor-strength.

### §0.11.1 — Invocation mechanism (carries forward from v2)

**Choice (unchanged):** Gemini 2.5 Pro via `src/lia_graph/gemini_runtime.py`. Same rationale as v2 §0.8.1 — pure stdlib, OpenAI-compat tools parameter, no new SDK.

**Model selection (unchanged):** `gemini-2.5-pro` for all skill invocations. The accuracy-vs-cost trade is unchanged; the operator's risk-forward stance for internal beta still applies.

**Per-article extraction cost (re-estimate for v3):** ~$0.045 with Gemini 2.5 Pro. Slightly higher than v2's $0.039 because the v3 veredicto schema is wider (more fields, longer output). For 7,883 articles: ~$355 total. For sub-units (every parágrafo / numeral cited in the corpus, conservatively ~3× article count): ~$1,065 incremental. Total Fix 1B-β LLM spend: ~$1,420 — still trivial against the envelope; reserve absorbs.

**API key (unchanged):** `LIA_GEMINI_API_KEY` per existing convention.

### §0.11.2 — Harness API (extended for v3)

The single Python entry point `VigenciaSkillHarness` keeps its v2 shape; the changes are in the return type:

```python
# src/lia_graph/vigencia_extractor.py — v3

class VigenciaSkillHarness:
    """Single entry point for invoking vigencia-checker from Python.

    v2 shape carries forward; verify_norm now returns a v3 VigenciaResult
    whose veredicto field is the v3 Vigencia value object."""

    def __init__(
        self,
        *,
        scrapers: ScraperRegistry,
        canonicalizer: NormCanonicalizer,        # NEW v3 — needed for source_norm_id resolution
        model: str = "gemini-2.5-pro",
        api_key: str,
        base_url: str = DEFAULT_GEMINI_OPENAI_BASE_URL,
        max_tool_iterations: int = 12,            # v3: bumped from 10 to handle wider source pulls
        timeout_seconds: float = 90.0,            # v3: bumped from 60 to handle DI / RV cascades
        temperature: float = 0.1,
    ): ...

    def verify_norm(
        self,
        *,
        norm_id: str,                             # v3: canonical norm_id, not free-form
        sub_unit: str | None = None,              # v3: optional override (e.g. par.2)
        periodo: PeriodoFiscal,
        as_of: date | None = None,                # v3: defaults to today
    ) -> "VigenciaResult": ...
```

**Internal canonicalizer step (new in v3):** `verify_norm` always runs the input through `NormCanonicalizer` first. If the input doesn't match the §0.5 grammar, the harness raises `InvalidNormIdError` rather than calling Gemini — keeps the skill from doing free-text disambiguation that the canonicalizer should own.

### §0.11.3 — Data contracts (v3 shapes)

#### Contract 1: `Vigencia` value object (Python + JSONB serialization)

```python
# src/lia_graph/vigencia.py — v3

VigenciaState = Literal[
    'V', 'VM', 'DE', 'DT', 'SP', 'IE', 'EC',     # v2 7 states
    'VC', 'VL', 'DI', 'RV'                         # v3 4 new states
]

AppliesToKind = Literal['always', 'per_year', 'per_period']

@dataclass(frozen=True)
class Citation:
    norm_id: str                                   # canonical per §0.5
    norm_type: str
    article: str | None
    fecha: date | None
    primary_source_url: str | None

@dataclass(frozen=True)
class InterpretiveConstraint:
    """Set when state ∈ {EC, VC}. Literal Court text — no paraphrase."""
    sentencia_norm_id: str                         # 'sent.cc.C-384.2023'
    fecha_sentencia: date
    texto_literal: str                             # the "en el entendido que..." passage
    fuente_verificada_directo: bool                # True iff fetched from Nivel 1 source

@dataclass(frozen=True)
class ChangeSource:
    """Discriminated union per §0.3.3."""
    type: Literal[
        'reforma', 'derogacion_expresa', 'derogacion_tacita',
        'sentencia_cc', 'auto_ce_suspension', 'sentencia_ce_nulidad',
        'reviviscencia', 'vacatio',
        'concepto_dian_modificatorio', 'modulacion_doctrinaria'
    ]
    source_norm_id: str                            # canonical id of the source artifact
    effect_type: Literal['pro_futuro', 'retroactivo', 'diferido', 'per_period']
    effect_payload: dict                           # type-specific; see §0.3.3 schema

@dataclass(frozen=True)
class AppliesToPayload:
    """Shape varies with applies_to_kind."""
    # When kind == 'always': empty.
    # When kind == 'per_year':
    year_start: int | None
    year_end: int | None
    # When kind == 'per_period':
    impuesto: str | None                            # 'renta' | 'iva' | 'retefuente' | ...
    period_start: date | None
    period_end: date | None
    art_338_cp_shift: bool                          # True if Art. 338 CP shifted the period

@dataclass(frozen=True)
class Vigencia:
    """v3 — the value object the skill produces and the schema persists."""
    state: VigenciaState
    state_from: date                                # legal effective date (NOT extracted_at)
    state_until: date | None                        # nullable; set when superseded
    applies_to_kind: AppliesToKind
    applies_to_payload: AppliesToPayload
    change_source: ChangeSource | None              # None for the inaugural V row of a norm
    interpretive_constraint: InterpretiveConstraint | None  # required when state ∈ {EC, VC}

    derogado_por: Citation | None                   # set when state == DE
    modificado_por: tuple[Citation, ...]            # cronological chain when state == VM
    suspension: Citation | None                     # set when state == SP — must link to T-series
    inexequibilidad: Citation | None                # set when state == IE
    regimen_transicion: Citation | None             # set when transition regime exists
    revives_text_version: str | None                # set when state == RV
    rige_desde: date | None                         # set when state == VL or DI

    fuentes_primarias_consultadas: tuple[Citation, ...]  # ≥ 2 for non-refusal veredicto
    extraction_audit: ExtractionAudit

    # Resolver-helper methods
    def applies_to_date(self, d: date) -> bool: ...
    def applies_to_period(self, impuesto: str, year: int) -> AplicabilidadVerdict: ...

@dataclass(frozen=True)
class VigenciaResult:
    """Either a successful veredicto OR a documented refusal — never an unverified guess."""
    veredicto: Vigencia | None                      # None ↔ refusal
    refusal_reason: str | None                      # set when veredicto is None
    missing_sources: tuple[str, ...]                # sources the skill needed but couldn't reach
    canonicalizer_refusals: tuple[CanonicalizerRefusal, ...]  # ambiguous mentions encountered
    audit: ExtractionAudit
```

JSONB serialization (what lands in `norm_vigencia_history.veredicto`):

```json
{
  "state": "EC",
  "state_from": "2023-10-02",
  "state_until": null,
  "applies_to_kind": "per_period",
  "applies_to_payload": {
    "impuesto": "renta",
    "period_start": "2023-01-01",
    "period_end": null,
    "art_338_cp_shift": true
  },
  "change_source": {
    "type": "sentencia_cc",
    "source_norm_id": "sent.cc.C-384.2023",
    "effect_type": "pro_futuro",
    "effect_payload": {
      "fecha_sentencia": "2023-10-02",
      "condicionamiento_literal": "EXEQUIBLES, en el entendido que el régimen tarifario establecido en el artículo 101 de la Ley 1819 de 2016 continuará rigiendo para los contribuyentes que hubieran cumplido las condiciones para acceder a este antes del 13 de diciembre de 2022, fecha en la que entró en vigor la Ley 2277 de 2022."
    }
  },
  "interpretive_constraint": {
    "sentencia_norm_id": "sent.cc.C-384.2023",
    "fecha_sentencia": "2023-10-02",
    "texto_literal": "EXEQUIBLES, en el entendido que el régimen tarifario establecido en el artículo 101 de la Ley 1819 de 2016 continuará rigiendo para los contribuyentes que hubieran cumplido las condiciones para acceder a este antes del 13 de diciembre de 2022.",
    "fuente_verificada_directo": false
  },
  "fuentes_primarias_consultadas": [
    {"norm_type": "url", "norm_id": "corte_constitucional_relatoria_C384_23",
     "primary_source_url": "https://www.corteconstitucional.gov.co/relatoria/2023/c-384-23.htm",
     "fecha_consulta": "2026-04-26"},
    {"norm_type": "url", "norm_id": "dian_normograma_C384_2023",
     "primary_source_url": "https://normograma.dian.gov.co/dian/compilacion/docs/c-384_2023.htm",
     "fecha_consulta": "2026-04-26"}
  ],
  "extraction_audit": {
    "skill_version": "vigencia-checker@2.0",
    "model": "gemini-2.5-pro",
    "tool_iterations": 5,
    "wall_ms": 360000,
    "cost_usd_estimate": 0.062
  }
}
```

#### Contract 2: Per-norm extraction file (`evals/vigencia_extraction_v1/<norm_id>.json`)

v2's per-article shape carries forward, with two changes:

1. Filename keys on `norm_id` (canonical) instead of `article_id` (free-form). Sub-units get their own files: `evals/vigencia_extraction_v1/et.art.689-3.par.2.json`.
2. Output payload includes the v3 `Vigencia` shape (above) as the `result.veredicto` field.

```json
{
  "norm_id": "et.art.689-3",
  "norm_type": "articulo_et",
  "display_label": "Art. 689-3 ET — Beneficio de auditoría",
  "parent_norm_id": "et",
  "is_sub_unit": false,
  "periodo": {"impuesto": "renta", "year": 2026, "period_label": "AG 2026"},
  "extraction_run_id": "20260501T120000Z",
  "extracted_at_utc": "2026-05-01T12:00:00Z",
  "result": {
    "veredicto": { /* v3 Vigencia JSON from §0.11.3 contract 1 */ },
    "refusal_reason": null,
    "missing_sources": [],
    "canonicalizer_refusals": []
  }
}
```

#### Contract 3: Scraper cache schema (unchanged from v2)

`var/scraper_cache.db` (SQLite). Schema in v2 §0.8.3 contract 3. v3 adds one column:

```sql
ALTER TABLE scraper_cache ADD COLUMN canonical_norm_id text;
CREATE INDEX idx_scraper_cache_canonical ON scraper_cache(canonical_norm_id);
```

This lets the cache be queried by canonical `norm_id` directly during 1B-β extraction, which removes a free-text join the v2 plan had implicit.

#### Contract 4: Skill Eval case fixture (extended for v3)

v2's YAML shape carries forward; v3 adds fields for the new states and contracts. Example for the EC case from Activity 1.7:

```yaml
case_id: art_11_ley_2277_2022_zonas_francas_AG2023
norm_id: ley.2277.2022.art.11
sub_unit: null                                     # whole article — numerales 1, 2, 3 + parágrafo 6
periodo: {impuesto: renta, year: 2023, period_label: "AG 2023"}
expected_state: EC
expected_change_source:
  type: sentencia_cc
  source_norm_id: sent.cc.C-384.2023
  effect_type: pro_futuro
expected_interpretive_constraint_substr:
  - "en el entendido que el régimen tarifario establecido en el artículo 101 de la Ley 1819 de 2016"
expected_min_primary_sources: 2
expected_applies_to_periodo:
  aplica: "Sí, con condicionamiento literal"
  art_338_cp_applied: true
sme_signoff: alejandro_2026-04-26
fixture_seed_from: evals/activity_1_5/art_11_ley_2277_2022_zonas_francas_AG2023_veredicto.json
notes: |
  Caso canónico EC. La Corte exigió mantener el régimen anterior para usuarios
  calificados pre-13-dic-2022. Skill debe NO parafrasear el condicionamiento.
```

**Gate criterion (binding for sub-fix 1B-β go-ahead, week 6):**
- ≥ 90% PASS on hard checks (state match, change_source.source_norm_id match, ≥ 2 primary sources, interpretive_constraint exact-substring for EC/VC).
- 0 false-positive veredictos (skill emitting a state when expected refusal).
- Soft-check median score ≥ 8.0 on `applies_to_periodo.justificacion` semantic similarity.

### §0.11.4 — Skill version bump (v1 → v2)

The v2-shipped skill is `vigencia-checker@1.0` (7 states, plain Vigencia output). v3 ships `vigencia-checker@2.0` with:

- 11-state taxonomy in `references/tipologia-modificaciones.md` (adds VC/VL/DI/RV).
- Structured `change_source` output requirement in `patrones-citacion.md`.
- Sub-unit awareness in `references/fuentes-primarias.md` selection rules.
- Refusal contract for ambiguous citations (canonicalizer-equivalent in skill space).

The skill update is part of sub-fix 1A (§2.1). SME-led; engineer integrates.

### §0.11.5 — Backwards compatibility for the 7 already-extracted veredictos

The 7 veredictos in `evals/activity_1_5/*.json` (Activity 1.5 + 1.6 + 1.7) are in the v2 shape. The 1B-γ migration includes a one-shot upgrade script that:

1. Reads each v2 veredicto JSON.
2. Maps it to the v3 `Vigencia` shape (filling `change_source` from the existing `derogado_por` / `modificado_por` / `suspension` / `inexequibilidad` / `condicionamiento` fields; setting `applies_to_kind` from `applies_to_periodo`).
3. Inserts a `norm_vigencia_history` row with `extracted_via.method = 'v2_to_v3_upgrade'` and `superseded_by_record = null`.
4. The 4 Activity 1.5b rows in `documents.vigencia` (the v2 staging persistence) are NOT touched; they get superseded automatically when the new norm-keyed rows take over via the deprecation view.

This makes the 7 veredictos the smoke set for the new persistence layer — same content, new shape, both layers populated for one release.

---

## §1 — Fix overview (v3)

The v3 fix surface is the v2 surface plus three deltas: (a) sub-fix 1B-γ split into 1B-γ (catalog + history), 1B-δ (citations link backfill), 1B-ε (retriever rewire — was 1C in v2); (b) new sub-fix 1F (cascade orchestrator); (c) sub-fix 1D extended from 7 to 11 chip variants. Net effort fits the $525K envelope; line-item reallocation in §11.

### §1.1 — The fix table

| Fix | Title | Weeks | Engineers | Status gate | Notes |
|---|---|---|---|---|---|
| **Activity 1** ✅ | SQL-only vigencia filter ship (DONE 2026-04-29) | — | — | shipped | learnings folded; superseded by 1B-ε |
| **Activity 1.5** ✅ | Skill verification — Decreto 1474/2025 (DONE 2026-04-26 ev) | — | — | shipped | IE veredicto + corpus hallucination found → Fix 6 expansion |
| **Activity 1.6** ✅ | Skill verification — 3 V/VM/DE norms (DONE 2026-04-26 ev) | — | — | shipped | seeds skill eval set |
| **Activity 1.5b** ✅ | Manual veredicto persistence to staging (DONE 2026-04-27 04:15 UTC) | — | — | shipped | 4 rows in staging Supabase + Falkor; audit log preserved for v3 re-persist |
| **Activity 1.7** ✅ | Skill verification — DT/SP/EC norms (DONE 2026-04-26 ev) | — | — | shipped | 3 fixtures complete 7-state coverage of skill eval set seed (7/30 of Fix 5) |
| **Activity 1.8** | Per-article skill verification on Ley 1429 articles | post-1B-α | 0.5 | week-5 | needs scrapers operational |
| **Fix 1A** | Vigencia ontology Python implementation (v3: 11 states + ChangeSource discriminated union + sub-unit-first-class dataclass + canonicalizer protocol) | 1–2 | 0.5 | week-2 | **expanded scope vs v2 §2.1** — adds `src/lia_graph/canon.py` for §0.5 grammar |
| **Fix 1B-α** | Scraper + cache infra (Senado / SUIN / DIAN / Corte / CE) | 1–4 | 1.0 | week-4 | unchanged from v2 §2.2 |
| **Fix 1B-β** | Skill-guided extractor batch over articles AND sub-units cited in corpus | 4–6 | 1.0 | week-6 | **expanded scope vs v2 §2.3** — extracts at sub-unit granularity; produces v3 Vigencia JSON |
| **Fix 1B-γ** | **NEW shape v3** — norms catalog + norm_vigencia_history + Falkor `(:Norm)` mirror | 6–7 | 1.0 | week-7 | replaces v2 §2.4's column-add migration; structural redesign |
| **Fix 1B-δ** | **NEW v3** — norm_citations link backfill via canonicalizer over existing chunks | 6–7 | 0.5 | week-7 | one-shot script + audit; refusal queue for SME |
| **Fix 1B-ε** | Plumb 2D vigencia model into retrieval via resolver functions (was Fix 1C in v2; renamed for v3 because the join surface changes) | 7–9 | 1.5 | week-9 | reads `norm_vigencia_at_date` / `norm_vigencia_for_period`, NOT `documents.vigencia` |
| **Fix 1D** | User-facing **11-variant** vigencia chips (was 7 in v2) | 9–10 | 0.5 frontend | week-10 | adds VC/VL/DI/RV variants |
| **Fix 1F** | **NEW v3** — cascade orchestrator (reviviscencia + future-dated state flips + retrieval-time inconsistency detection) | 4–10 | 0.5 | week-10 | hosted by Re-Verify Cron; consumes `norm_vigencia_history` writes |
| **Fix 2** | Parámetros móviles map (UVT/SMMLV/IPC/topical thresholds) + runtime injection | 2–6 | 1.0 | week-6 | unchanged in scope; composes with v3 resolvers (§3) |
| **Fix 3** | Anti-hallucination guard on partial mode | 7–10 | 1.0 | week-10 | hook reads from `norm_vigencia_history`, not docs |
| **Fix 4** | Ghost-topic kill + corpus completeness audit | 8–13 | 0.5 + SME | week-13 | ingest-time skill hook writes per-norm rows |
| **Fix 5** | Golden-answer regression suite (TRANCHE schema, skill-as-judge) | 1–14 | 0.5 + SME | week-14 | 7/30 cases pre-seeded by Activities 1.5/1.6/1.7 |
| **Fix 6** | Internal corpus consistency editorial pass + corpus-wide hallucination audit | 11–13 | 0.5 + SME | week-13 | scope narrows in v3 — vigencia reconciliation moves to 1B-γ; Fix 6 stays on content hallucinations |
| **Skill Eval** | 30-case eval set for vigencia-checker itself (7 pre-seeded; 23 to author) | 4–6 | 0.5 + SME | week-6 | extended to cover VC/VL/DI/RV per §0.4 |
| **Re-Verify Cron** | Periodic re-verification + cascade orchestration host | 4–5 | 0.5 | week-5 | hosts Fix 1F's cascade consumer |
| **Norm canonicalizer (Fix 1A subscope)** | `src/lia_graph/canon.py` per §0.5 grammar | 1–2 | 0.5 (within 1A) | week-2 | called from extractor + backfill + retrieval planner |
| | **Total** | 14 wks | 5–6 FTE-weeks/wk avg | | |

### §1.2 — What's preserved unchanged from v2

- Six-gate lifecycle policy (gate 1 idea / gate 2 plan / gate 3 measurable criterion / gate 4 test plan / gate 5 greenlight / gate 6 refine-or-discard).
- The vigencia-checker skill design (SME-delivered).
- Test discipline (`make test-batched`, append-only learning docs, env matrix bumps).
- Surface boundaries (`main chat` vs `Normativa` vs `Interpretación` parallel orchestration).
- Operator's beta risk-forward stance (every non-contradicting flag ON across all three modes).
- The kill-switch metric at week-6 midpoint (zero `art. 689-1` / `6 años` / `10% dividendo` leaks).
- The week-14 launch readiness gate.

### §1.3 — What's deleted from v2

- Sub-fix 1C (v2's filter-mode RPC parameter approach) — superseded by 1B-ε's resolver-function join. The v2 `LIA_VIGENCIA_FILTER_MODE` flag is gone; resolver default is enforced unconditionally.
- v2's plan to write to `documents.vigencia` columns post-extraction — the columns become a deprecation view and then drop.
- v2's free-text `vigencia_basis` — replaced by structured `change_source`.

### §1.4 — Critical-path dependencies (v3)

```
1A (ontology + canonicalizer) → 1B-α (scrapers) → 1B-β (extraction)
   ↓                                                  ↓
1B-γ (catalog + history)  ←───────────────────  veredicto JSONs
   ↓
1B-δ (citations backfill)
   ↓
1B-ε (retriever rewire) ── 1F (cascade orchestrator) ── Re-Verify Cron
   ↓                          ↓
1D (chips) ←───────── synthesis policy
```

Hard ordering: `1A → 1B-α → 1B-β → 1B-γ → 1B-δ → 1B-ε`. 1F can start as soon as `norm_vigencia_history` exists (week 7), so it overlaps `1B-ε` development. 1D is gated on the chat-response payload carrying the v3 vigencia fields, which is a 1B-ε deliverable.

### §1.5 — Fix-numbering map (v2 → v3)

| v2 sub-fix | v3 sub-fix | Status |
|---|---|---|
| 1A — Vigencia ontology (7 states) | 1A — Vigencia ontology (11 states + ChangeSource + canonicalizer) | scope expanded |
| 1B-α — Scrapers | 1B-α — Scrapers | unchanged |
| 1B-β — Extractor batch | 1B-β — Extractor batch (sub-unit aware) | scope expanded |
| 1B-γ — Materialize columns on documents | 1B-γ — `norms` + `norm_vigencia_history` tables | shape replaced |
| (none) | 1B-δ — `norm_citations` backfill | new |
| 1C — Plumb 2D vigencia into retrieval | 1B-ε — Retriever via resolver functions | renamed + reshaped |
| 1D — 7-variant chips | 1D — 11-variant chips | extended |
| (none) | 1F — Cascade orchestrator | new |

---

## §2 — Fix 1 (vigencia structural)

The biggest fix. Decomposed into eight sub-fixes (was six in v2, five in v1). Skill-guided throughout. Sub-fixes 1A through 1B-ε are sequential on the critical path; 1F overlaps 1B-ε.

### 2.1 Sub-fix 1A — Vigencia ontology + canonicalizer (v3 expanded scope)

**What.** v2's §2.1 produced a Python `Vigencia` dataclass for the 7 skill states. v3 extends this to:

1. The 11-state taxonomy (§0.4) — VigenciaState enum + per-state validation.
2. The structured `ChangeSource` discriminated union (§0.3.3) — Pydantic models per type, with JSONB serialization round-trip.
3. The `NormCanonicalizer` module (`src/lia_graph/canon.py`) — implements the §0.5 grammar with refusal contract.
4. Sub-unit-first-class methods on the dataclass (`is_sub_unit`, `parent_norm_id`, `walk_ancestors`).
5. Future-dated state validation (allow `state_from > today` for VL / DI / cascade-pre-writes; forbid for V/VM/DE without explicit override).
6. The skill prompt update (`vigencia-checker@2.0`) — SME-led, engineer integrates.

**Files.**
- *Read first:* `.claude/skills/vigencia-checker/references/tipologia-modificaciones.md` + `reglas-temporales.md` + `patrones-citacion.md` (the v2 design); `src/lia_graph/graph/schema.py:23-44` (existing edge kinds to extend); `supabase/migrations/20260417000000_baseline.sql:108-115` (the existing 6-value `vigencia_status` ENUM that gets superseded); `src/lia_graph/ingestion_classifier.py:279-298` (extend `AutogenerarResult` shape to emit canonical norm_ids); the 7 veredicto fixtures in `evals/activity_1_5/`.
- *Create:* `src/lia_graph/vigencia.py` (the v3 `Vigencia`, `ChangeSource`, `Citation`, `InterpretiveConstraint` dataclasses + Pydantic models + JSONB serializers); `src/lia_graph/canon.py` (the canonicalizer with §0.5 grammar + refusal types); `tests/test_vigencia_v3_ontology.py` (12 patterns × 11 states = 132+ tests, plus 8 `applies_to_*` integration tests); `tests/test_canon.py` (round-trip table from §0.5.4 + refusal cases); `docs/re-engineer/vigencia_ontology_implementation.md` (engineer notes, with worked examples for each state); `.claude/skills/vigencia-checker/references/tipologia-modificaciones-v2.md` (SME-edited; adds VC/VL/DI/RV); `.claude/skills/vigencia-checker/references/patrones-citacion-v2.md` (SME-edited; structured change_source in skill output).
- *Modify:* none in upstream code yet (the existing `parser.py` regex flag stays operational until 1B-γ's deprecation view ships).

**Success criteria.**
- 132+ unit tests across the 11 states pass; round-trip serialize / deserialize identity.
- Canonicalizer round-trips the 12 examples in §0.5.4 deterministically.
- Canonicalizer refuses the 4 ambiguous cases in §0.5.4 with structured reasons.
- 7 existing veredictos in `evals/activity_1_5/` upgrade cleanly to v3 shape via the upgrade script (smoke for the v2-to-v3 mapper in §0.11.5).
- SME walkthrough: implementer presents the 11-state ontology + 8 worked examples (one per state with at least one new state covered); SME signs off in writing that the skill prompt update faithfully renders the schema's intent.
- Skill v2.0 produces structurally-valid `change_source` blocks on the 7 already-extracted norms when re-run (validation of the prompt update; no behavioral regression).

**How to test.**
- `tests/test_vigencia_v3_ontology.py` for the dataclass + 11-state surface.
- `tests/test_canon.py` for grammar conformance.
- `tests/test_vigencia_v2_to_v3_upgrade.py` — runs the migration on the 7 fixtures; asserts every required field landed.
- Skill smoke: `scripts/eval/run_skill_smoke.py` re-runs the skill on the 7 known cases against v2.0 prompt; expected state matches.

**Effort.** 0.5 senior engineer × 2 weeks (week 1–2). SME × 0.3 week for the skill prompt update.

### 2.2 Sub-fix 1B-α — Scraper + cache infrastructure (carries forward from v2 §2.2)

**What.** Unchanged from v2. The skill mandates double-primary-source verification per norm. At corpus scale (7,883 articles + an estimated ~22,000 sub-units cited), live web fetch per call is too slow + rate-limited. Build cached scrapers for the 5 primary sources.

The 5 scrapers (unchanged):

| Module | Source | Coverage |
|---|---|---|
| `scrapers/secretaria_senado.py` | https://www.secretariasenado.gov.co/senado/basedoc/ | Leyes (incluye ET); modification notes per artículo |
| `scrapers/dian_normograma.py` | https://normograma.dian.gov.co/ | Decretos tributarios + resoluciones DIAN + conceptos DIAN |
| `scrapers/suin_juriscol.py` | https://www.suin-juriscol.gov.co/ | Toda la legislación nacional con histórico |
| `scrapers/corte_constitucional.py` | https://www.corteconstitucional.gov.co/relatoria/ | Sentencias C-, autos de suspensión |
| `scrapers/consejo_estado.py` | https://www.consejodeestado.gov.co/ | Sentencias de nulidad, autos de suspensión |

**v3 delta vs v2.** One additive change to the SQLite cache schema (per §0.11.3 contract 3): adds `canonical_norm_id` column + index. This lets 1B-β query the cache by canonical id directly, removing one free-text join.

**Success criteria.** Carries forward from v2 §2.2: all 5 scrapers fetch + parse + cache ≥ 30 known-vigente norms with 100% success rate; cache hit rate ≥ 70% post-1B-β; rate-limited ≤ 2 req/sec per source; smoke fixtures detect source restructure.

**How to test.** Carries forward from v2 §2.2: per-scraper smoke fixture + 3 live-fetch tests gated behind `LIA_LIVE_SCRAPER_TESTS=1`; `scripts/scrapers/probe_all.py` runs the 30-norm fetch.

**Effort.** Carries forward from v2: 1 senior engineer × 3 weeks (week 1–4, overlaps Fix 1A weeks 1–2). The `canonical_norm_id` column add is a half-day delta absorbed into the same envelope.

**Files.** Carries forward from v2 §2.2 verbatim; only delta is `src/lia_graph/scrapers/cache.py` gets a `canonical_norm_id` column add + index; tests get one extension case.

**Hosting.** Cache lives at `var/scraper_cache.db` locally; in production deploy, mount a persistent volume. Size estimate: ~7,883 articles × 5 sources × ~50 KB avg = ~2 GB primary; sub-units add ~30%; total ~2.6 GB. Fits comfortably.

### 2.3 Sub-fix 1B-β — Skill-guided extractor batch (v3 expanded for sub-units)

**What.** Wraps `vigencia-checker@2.0` skill as a callable agent loop. Per **norm_id** (article OR sub-unit) cited anywhere in the corpus: invoke skill (which reads scrapers via 1B-α), produce v3 `Vigencia` JSON, write to `evals/vigencia_extraction_v1/<norm_id>.json`. Resumable, parallelizable.

**Critical v3 expansion vs v2 §2.3.** The extractor now operates at sub-unit granularity. The corpus citation extractor (the canonicalizer running over `document_chunks.chunk_text`) produces a deduplicated set of norm_ids — articles AND sub-units. The extractor processes the union. Estimated ~7,883 articles + ~22,000 sub-units ≈ 30,000 extractions total. With a 70% cache hit on scrapers and ~$0.045 per extraction: ~$1,350 LLM spend. Budget envelope absorbs.

The agent loop per norm_id:
1. **Identify** — derive `(norm_type, norm_id, parent_norm_id, sub_unit_kind)` from the canonicalized id.
2. **Invoke skill** — pass identification + period (default: `today` for current vigencia) + canonicalizer-resolved primary-source URLs from cache.
3. **Skill flow** — ≥ 2 primary sources via 1B-α scrapers → judicial check → state classification → v3 veredicto OR refusal.
4. **Validate output** — Pydantic round-trip of the `Vigencia` shape; refuse-and-log if shape invalid.
5. **Write output** — structured v3 `Vigencia` JSON if veredicto; `null` + reason if refusal.
6. **Log** — `evals/vigencia_extraction_v1/audit.jsonl`: per-norm `(norm_id, state | null, sources_consulted, time_ms, cost_estimate, sub_unit_count_emitted)`.

**Cost target.** Per-norm: ~$0.045 with 70% cache hit. Total batch ~$1,350 (well within Fix 1 budget envelope's reserve).

**Success criteria (binding for the week-6 kill-switch gate).**
- ≥ 95% of articles AND sub-units produce a v3 `Vigencia` record OR documented refusal (no silent crashes).
- ≥ 80% of norms have `extraction_confidence ≥ 0.7` (skill emitted veredicto, not refusal).
- 100% of `DE` extractions cite the deroganting norm with full Citation (canonical `source_norm_id` resolved).
- 100% of `IE` extractions cite the sentencia C- with effects timing AND `effect_type` (pro_futuro / retroactivo / diferido).
- 100% of `EC` extractions include the `interpretive_constraint.texto_literal` (verified by exact-match against the Corte source).
- 100% of `VC` extractions identify the modulating source (`change_source.type = 'modulacion_doctrinaria'` with `effect_payload.fuente`).
- 100% of `RV` extractions identify the triggering inexequibilidad (`change_source.effect_payload.triggering_sentencia_norm_id`).
- 100% of `VL` extractions populate `rige_desde` and have `state_from > today` OR a paired future-dated `V` row.
- A 100-norm SME spot-check shows ≥ 95 correct extractions.
- Skill audit log shows ≥ 2 primary sources consulted per non-refusal veredicto.
- Sub-unit extractions produce sibling-consistent results (e.g., extracting `et.art.240.par.2` does not corrupt or override `et.art.240.par.1` independently produced state).

**How to test.**
- After extraction completes: `scripts/audit_vigencia_extraction.py` reports the % at each confidence/state bucket, broken out by article vs sub-unit.
- SME spot-check: 10 norms per state × 11 states + 10 random + 30 sub-unit-specific = 150 norms, SME marks correct/incorrect.
- Per-state minimum tests: 3 known-V, 3 known-VM, 3 known-DE, 3 known-DT, 3 known-SP, 3 known-IE, 3 known-EC, 3 known-VC, 3 known-VL, 3 known-DI, 3 known-RV (the 33 cases come from the Skill Eval set's seeded fixtures + author cases).
- Sibling-consistency test: pick 10 articles known to have differential parágrafo states (e.g., Art. 240 ET sub-units modified by Ley 2277 only in par.2); assert sibling state divergence is captured.
- **Kill switch:** if SME spot-check < 95%, the prompt or skill invocation is wrong; iterate before proceeding to 1B-γ materialization. Per `feedback_thresholds_no_lower`, the 95% bar does NOT relax — failure means more iteration, not a softer gate.

**Effort.** 1 senior engineer × 2 weeks (week 4–6).

**Files.**
- *Read first:* `.claude/skills/vigencia-checker/SKILL.md` + all checklists; `src/lia_graph/ingestion_classifier.py` (precedent for LLM-call-with-structured-output discipline); `scripts/launch_phase9a.sh` + `scripts/monitoring/ingest_heartbeat.py` (the long-running-job launcher pattern); `artifacts/parsed_articles.jsonl` (the corpus to iterate over); `src/lia_graph/scrapers/` (1B-α infrastructure); `src/lia_graph/canon.py` (1A canonicalizer — produces the input set).
- *Create:* `src/lia_graph/vigencia_extractor.py` (the agent loop module, v3 shape); `scripts/extract_vigencia.py` (the batch driver — launched detached per long-running-job convention); `scripts/build_extraction_input_set.py` (walks corpus chunks, runs canonicalizer, produces deduplicated norm_id list); `evals/vigencia_extraction_v1/` (output dir); `scripts/audit_vigencia_extraction.py` (the bucket reporter, broken out by article vs sub-unit); `Makefile` target `phase2-extract-vigencia`.
- *Modify:* `src/lia_graph/scrapers/cache.py` (already touched in 1B-α for the canonical_norm_id column).

**Long-running-job protocol.** The 30,000-norm batch runs ~12-18 hours wall time. Per `CLAUDE.md`'s long-running-job section: `nohup` + `disown` + direct `>log 2>&1` (NO tee), 3-minute heartbeat via `scripts/monitoring/ingest_heartbeat.py` template, anchor progress to `logs/events.jsonl`, render in Bogotá AM/PM. The `cli.done` event signals completion; absent it after process death = silent failure → STOP loop, do NOT retry.

### 2.4 Sub-fix 1B-γ — Norm catalog + vigencia history (replaces v2 §2.4)

**What.** Build the three tables of §0.3 — `norms`, `norm_vigencia_history`, `norm_citations` — as Supabase migrations, plus the Falkor mirror via `(:Norm)` node and structured edges. Idempotent ingest of all extracted veredictos from 1B-β. `documents.vigencia` becomes a deprecation view.

**The five migrations** (sequential, per §0.3.4 choreography):

1. `20260YYYY000000_norms_catalog.sql` — `norms` table + indexes. Empty.
2. `20260YYYY000001_norm_vigencia_history.sql` — table + INSERT-only role grant + indexes + CHECK constraints (`state_until >= state_from`).
3. `20260YYYY000002_norm_citations.sql` — table + indexes.
4. `20260YYYY000003_resolver_functions.sql` — `norm_vigencia_at_date` + `norm_vigencia_for_period` per §0.6.
5. `20260YYYY000004_documents_vigencia_deprecated_view.sql` — replaces `documents.vigencia` and `document_chunks.vigencia` with views computed from `norm_vigencia_history`. Keeps the column-readers happy for one release window.

A sixth migration drops the old columns once 1B-ε ships and the deprecation window closes (target: week 11).

**Idempotent veredicto ingest.** The 1B-β output (`evals/vigencia_extraction_v1/<norm_id>.json`) feeds a sink (`scripts/ingest_vigencia_veredictos.py`) that:

1. Upserts `norms` rows for every norm_id (and parent norm_ids walked recursively).
2. INSERT (never UPDATE) into `norm_vigencia_history` — even on re-runs. Idempotency comes from a deterministic `extracted_via.run_id` check: if a row exists with the same `(norm_id, run_id, change_source.source_norm_id)`, skip the insert.
3. Mirrors to Falkor: upsert `(:Norm)` node + structured edges (DEROGATED_BY / MODIFIED_BY / SUSPENDED_BY / INEXEQUIBLE_BY / CONDITIONALLY_EXEQUIBLE_BY / MODULATED_BY / REVIVED_BY) with full property bags.

**Smoke set: re-persist the 7 already-extracted veredictos.** Activity 1.5b wrote 4 docs to `documents.vigencia`; Activities 1.5/1.6/1.7 produced 7 veredictos as JSON only. The first 1B-γ run takes those 7 fixtures, runs them through the v2-to-v3 upgrade mapper (§0.11.5), and lands them in `norm_vigencia_history`. This is the smallest end-to-end smoke for the new path. Activity 1.5b's 4 staging-Supabase rows stay intact; the deprecation view shows them as the legacy values until the v3 rows take over.

**Falkor edge schema (extends `src/lia_graph/graph/schema.py` EdgeKind enum).** v2's enum has 14 entries; v3 adds:

```python
class EdgeKind(str, Enum):
    # ... v2 entries: REFERENCES, MODIFIES, SUPERSEDES, DEROGATES, ANULA,
    #     STRUCK_DOWN_BY, SUSPENDS, DECLARES_EXEQUIBLE, REGLAMENTA, ... ...

    # v3 additions — directional, norm-to-source:
    MODIFIED_BY = "MODIFIED_BY"
    DEROGATED_BY = "DEROGATED_BY"
    SUSPENDED_BY = "SUSPENDED_BY"
    INEXEQUIBLE_BY = "INEXEQUIBLE_BY"
    CONDITIONALLY_EXEQUIBLE_BY = "CONDITIONALLY_EXEQUIBLE_BY"
    MODULATED_BY = "MODULATED_BY"        # for VC state
    REVIVED_BY = "REVIVED_BY"             # for RV state
    CITES = "CITES"                       # chunk → norm
    IS_SUB_UNIT_OF = "IS_SUB_UNIT_OF"     # parágrafo → article
```

The directional pair (e.g., MODIFIES / MODIFIED_BY) is intentional: `MODIFIES` (v2) is article-as-source-of-edit; `MODIFIED_BY` (v3) is norm-as-affected-by-source. Both populated; queries pick the direction that suits the question.

**Success criteria.**
- The 5 migrations apply cleanly to local + staging Supabase.
- `SELECT COUNT(*) FROM norms` matches the canonicalizer's deduplicated input-set count from 1B-β.
- `SELECT COUNT(*) FROM norm_vigencia_history` ≥ count of non-refusal veredictos from 1B-β.
- `MATCH (n:Norm) RETURN COUNT(n)` matches `norms` row count.
- INSERT-only grants verified: a write attempt as the application role with UPDATE or DELETE returns permission denied.
- The 7 Activity 1.5/1.6/1.7 veredictos round-trip: `Vigencia` JSON → INSERT → SELECT → identity preserved on 100% of fields.
- The deprecation view returns the same values as the v2 `documents.vigencia` column did for the 4 Activity 1.5b docs.
- No regression on §1.G SME fixture: served_acceptable+ stays at the post-Activity-1 baseline (≥ 21/36).

**How to test.**
- Migration tests against local Supabase docker (`supabase db reset` + apply).
- `tests/test_norms_catalog.py` for catalog upsert idempotency.
- `tests/test_norm_vigencia_history_append_only.py` for grant enforcement.
- `tests/test_falkor_norm_mirror.py` for `(:Norm)` node + edge correctness against the local docker FalkorDB.
- Round-trip test on the 7 fixtures: `tests/test_v2_to_v3_veredicto_upgrade.py`.

**Effort.** 1 senior engineer × 1 week (week 6–7).

**Files.**
- *Read first:* `src/lia_graph/ingestion/supabase_sink.py:639,646` (where binary vigencia is written today — to be deprecated); `src/lia_graph/ingestion/loader.py` (Falkor loader); `src/lia_graph/graph/client.py` (`stage_detach_delete` + `stage_delete_outbound_edges` patterns from v5 §6.5); `scripts/sync_article_secondary_topics_to_falkor.py` (precedent for "back-fill a property to existing Falkor nodes via Cypher MERGE without re-ingest"); `evals/activity_1_5/persistence_audit.jsonl` (the Activity 1.5b write log — the v3 sink upgrades these via the audit).
- *Create:* the 5 migrations listed above; `scripts/ingest_vigencia_veredictos.py` (the sink); `src/lia_graph/persistence/norm_history_writer.py` (the in-process API used by the sink and by the cron); `scripts/sync_vigencia_to_falkor.py` (Falkor mirror — extends existing sync pattern); `tests/test_norms_catalog.py`, `tests/test_norm_vigencia_history_append_only.py`, `tests/test_falkor_norm_mirror.py`, `tests/test_v2_to_v3_veredicto_upgrade.py`.
- *Modify:* `src/lia_graph/graph/schema.py` (extend `EdgeKind` enum); `src/lia_graph/ingestion/supabase_sink.py` (the existing per-doc vigencia write becomes a no-op once the deprecation view ships, but stays in place for one release).
- **Convention reminder:** explicit `DROP FUNCTION IF EXISTS` before any SQL function change; per `hybrid_search-overload-2026-04-27.md`.

### 2.5 Sub-fix 1B-δ — Citations link backfill (NEW v3)

**What.** The bridge sub-fix. Walks every row in `document_chunks` (cloud staging Supabase) and `documents.vigencia_basis` (the legacy free-text field), runs the canonicalizer (`src/lia_graph/canon.py`) over the chunk_text and basis prose, and populates `norm_citations` with the resolved `(chunk_id, norm_id, role, anchor_strength)` tuples. Refusals from the canonicalizer log to a SME-triage queue.

**The backfill loop.**

```python
for chunk in document_chunks:
    mentions = extract_norm_mentions(chunk.chunk_text)  # regex pre-pass
    for mention in mentions:
        norm_id = canonicalize(mention)                 # Optional[str]
        if norm_id is None:
            log_canonicalizer_refusal(chunk.chunk_id, mention)
            continue
        upsert_norms_row_if_missing(norm_id)
        upsert_norm_citations_row(
            chunk_id = chunk.chunk_id,
            norm_id = norm_id,
            mention_span = mention.span,
            role = infer_role(chunk, mention),          # anchor | reference | comparator | historical
            anchor_strength = infer_strength(norm_id),  # ley | decreto | ... | concepto_dian
        )
```

**Role inference.** A norm cited in the chunk_text's heading or first paragraph = anchor. A norm cited in a comparative table = comparator. A norm cited in a "régimen anterior" or "antiguamente" passage = historical. Otherwise = reference. The inference is regex-based and intentionally conservative — when in doubt, mark as `reference` (lowest gate impact). SME spot-check after backfill validates a sample.

**Anchor-strength inference.** Mechanical from `norm_type`:
- `ley` / `et_articulo` / `decreto` → `ley` (strongest)
- `decreto_articulo` → `decreto`
- `res_dian` / `res_dian_articulo` → `res_dian`
- `concepto_dian` / `concepto_dian_numeral` → `concepto_dian` (weakest)
- `sentencia_cc` / `auto_ce` / `sentencia_ce` → `jurisprudencia`

The retriever's synthesis policy gates on `anchor_strength`: a chunk anchored only on `concepto_dian` is treated as supporting, not establishing — the answer must surface a stronger anchor before claiming the position.

**Refusal queue.** Ambiguous mentions log to `evals/canonicalizer_refusals_v1/refusals.jsonl`:

```json
{"chunk_id": "...", "mention": "Decreto 1474", "context": "...20 chars before/after...",
 "reason": "missing_year", "extracted_at_utc": "..."}
```

SME triages weekly; resolved patterns are baked into the canonicalizer's rules. Each baked-in rule is a small unit test added to `tests/test_canon.py`.

**Success criteria.**
- ≥ 95% of `document_chunks` rows have ≥ 1 row in `norm_citations` (the 5% slack handles purely operational chunks — diagrams, definitions of concepts, no norm cited).
- 0 rows in `norm_citations` reference a `norm_id` that doesn't exist in `norms` (FK enforced).
- Canonicalizer refusal rate < 5% across the corpus (if higher: the canonicalizer rules need extension; iterate, don't accept).
- SME spot-check: 50 random `norm_citations` rows; ≥ 47 correctly identified.

**How to test.**
- `scripts/audit_norm_citations.py` reports: total chunks, % with ≥ 1 citation, % refused, anchor-strength distribution.
- `tests/test_role_inference.py` over a curated 20-chunk sample.

**Effort.** 0.5 senior engineer × 1 week (week 6–7, parallel with 1B-γ).

**Files.**
- *Read first:* `src/lia_graph/canon.py` (1A); `artifacts/parsed_articles.jsonl` (corpus structure); `src/lia_graph/ingestion/supabase_sink.py` (chunk-write site for sample chunk_text shape).
- *Create:* `scripts/backfill_norm_citations.py` (the backfill loop); `src/lia_graph/citations.py` (role + anchor-strength inference); `scripts/audit_norm_citations.py`; `tests/test_role_inference.py`; `evals/canonicalizer_refusals_v1/` (output dir).
- *Modify:* `src/lia_graph/canon.py` (gets new rules from SME triage as backfill progresses).

### 2.6 Sub-fix 1B-ε — Retriever rewire to resolver functions (was Fix 1C in v2)

**What.** The retriever's vigencia gate stops reading `document_chunks.vigencia` and starts reading the resolver functions via `norm_citations`. Two changes:

1. **`hybrid_search` RPC rewrites** — drops the v2 §1.D 15-arg + Activity 1 16-arg form; recreates with explicit `vigencia_query_kind` + `vigencia_query_payload` parameters per §0.6.3.
2. **Falkor traversal symmetrical** — Cypher predicates compute period-aware factors via the `pipeline_d/retriever_falkor.py` Python wrapper, calling out to the resolver-equivalent on read. The Falkor side does not duplicate Postgres function definitions — it joins to property-bag data emitted at sync time and computes period-applicability in Python.

**Demotion rules** (per §0.4.1 + §0.6 resolver output):

| State | `at_date` factor | `for_period` factor (when period applies) | Notes |
|---|---|---|---|
| V | 1.0 | 1.0 | resting state |
| VM | 1.0 | 1.0 (current text) | for past periods, resolver returns the prior V row |
| DE | 0.0 | 1.0 if ultractividad applies (period predates derogación) else 0.0 | |
| DT | 0.3 | 0.3 | uncertain; resolver flags `contested = true` so chip surfaces |
| SP | 0.0 | 0.0 | partial-mode escalation may surface via Fix 4 |
| IE | 0.0 | 1.0 if effects diferidos active for the period else 0.0 | |
| EC | 1.0 | 1.0 | citation must include `interpretive_constraint.texto_literal` |
| VC | 1.0 | 1.0 | same as EC; chip variant differs |
| VL | 0.0 | 1.0 if period >= rige_desde else 0.0 | |
| DI | 1.0 | 1.0 if period < state_until else 0.0 | flips to IE at deadline |
| RV | 1.0 | 1.0 | citation must explain the reviviscencia chain |

**Planner cue extraction** (`pipeline_d/planner.py` extension):

```python
# Already-existing cues: tipo_de_consulta, tipo_de_riesgo, period hints (year context).
# v3 additions:
plan.vigencia_query_kind: Literal['at_date', 'for_period'] | None = None
plan.vigencia_query_payload: dict | None = None

# Cue rules (regex + heuristics):
if matches(query, r'\b(AG|año gravable|período|periodo)\s+(\d{4})\b'):
    plan.vigencia_query_kind = 'for_period'
    plan.vigencia_query_payload = {'impuesto': infer_impuesto(query) or 'renta',
                                    'periodo_year': extracted_year}
elif matches(query, r'\b(en|a|al|para)\s+(20\d{2})'):
    plan.vigencia_query_kind = 'at_date'
    plan.vigencia_query_payload = {'as_of_date': date(extracted_year, 12, 31)}
# Default (no cue): at_date(today)
```

**Success criteria.**
- For 30 canonical "vigente law" questions (default mode): **0 derogated articles** in top-5 primaries.
- For 10 canonical "historical law" questions ("¿Qué decía art. 147 ET antes de Ley 1819?"): the derogated article is correctly retrieved AND the chunk carries the historical chip.
- For 8 Art. 338 CP questions ("¿aplicaba Art. 240 ET (modificado por Ley 2277) al AG 2022?"): resolver returns the prior V row, NOT the post-Ley-2277 VM row.
- For 4 ultractividad questions: the DE norm correctly retrieved with explanation.
- Re-run §1.G SME 36-question fixture: zero `art. 689-1` citations (currently 2 after Activity 1; binary fix can't catch the rest), zero "6 años firmeza" claims, zero pre-Ley-2277 dividend tariffs.
- §1.G `served_acceptable+` count moves from 21/36 (post-Activity-1 baseline) to ≥ 24/36.
- Resolver test set (30 SME-curated `(norm_id, query_kind, payload)` pairs from §0.6.4) passes ≥ 28/30.

**How to test.**
- 30+10+8+4 = 52-question regression set in `evals/vigencia_v1/`.
- Re-run §1.G via `scripts/eval/run_sme_validation.py` (delete cached responses first).
- A/B harness on the same 30-question default-mode set: pre-1B-ε vs post-1B-ε; compare derogated-article appearance rate.

**Effort.** 1.5 senior engineers × 2 weeks (week 7–9).

**Files.**
- *Read first:* `src/lia_graph/pipeline_d/retriever_supabase.py:47-189`; `src/lia_graph/pipeline_d/retriever_falkor.py`; `supabase/migrations/20260427000000_topic_boost.sql` (precedent for adding RPC parameter); `supabase/migrations/20260428000000_drop_legacy_hybrid_search.sql` + `20260429000000_vigencia_filter_unconditional.sql` (Activity 1's surgical precursors); `src/lia_graph/pipeline_d/contracts.py` (planner contract — `vigencia_query_kind` field is new); `src/lia_graph/pipeline_d/answer_comparative_regime.py` (precedent for cue-detection in planner).
- *Create:* `supabase/migrations/20260YYYY000005_hybrid_search_v3.sql` (drops v2 form; recreates with `vigencia_query_kind` + `vigencia_query_payload` parameters); `src/lia_graph/pipeline_d/vigencia_resolver.py` (Python wrapper that calls the right SQL resolver based on plan); `evals/vigencia_v1/` (52-question regression set); `tests/test_retriever_vigencia_v3.py`.
- *Modify:* `src/lia_graph/pipeline_d/retriever_supabase.py` (call new RPC); `src/lia_graph/pipeline_d/retriever_falkor.py` (analogous Cypher predicates + Python period-factor computation); `src/lia_graph/pipeline_d/planner.py` (cue extraction); `src/lia_graph/pipeline_d/contracts.py` (new fields on `GraphRetrievalPlan`).
- **Env matrix bump required:** new RPC parameters change retrieval shape → version bump + change-log row in `docs/orchestration/orchestration.md` + mirror updates in `docs/guide/env_guide.md`, `CLAUDE.md`, `/orchestration` HTML status card.

### 2.7 Sub-fix 1D — User-facing 11-variant vigencia chips (extends v2 §2.6)

**What.** Extends v2's 7 chip atom to 11. New variants: VC (modulación non-CC), VL (vacatio legis with countdown), DI (diferida with countdown to expiration), RV (revivida — explains the chain).

| State | Chip | Tone | Hover/expand content |
|---|---|---|---|
| V | (no chip — default) | — | — |
| VM | "modificada por X" | blue | modification chain summary |
| DE | "derogada por X desde fecha" | red | deroganting norm + fecha de efectos |
| DT | "derogada tácitamente — verificar" | orange | pronouncement oficial + alcance OR "contested" warning |
| SP | "suspendida por auto X — ver T-Y" | yellow | mandatory T-series link + autoridad + consejero |
| IE | "inexequible — sentencia C-X" | red | sentencia + effect_type (pro_futuro / retroactivo / diferido) |
| EC | "exequibilidad condicionada — ver condicionamiento" | purple | literal Court text (no paraphrase) |
| **VC** | "vigente con modulación — ver detalle" | purple-light | source of modulación + literal constraint text |
| **VL** | "vacatio legis — rige desde [fecha]" | gray | rige_desde + countdown days remaining |
| **DI** | "exequibilidad diferida — vence el [fecha]" | yellow-stripe | plazo Congreso + countdown |
| **RV** | "revivida tras inexequibilidad de [norma]" | green-stripe | reviviscencia chain + revives_text_version |

**Composer policy** (`pipeline_d/answer_policy.py` extension):
- Any answer that cites a norm whose state ∈ {DE, DT, SP, IE, VC, VL, DI, RV} MUST include the chip.
- Any answer about historical regimes MUST display the comparative-regime table.
- EC + VC chips MUST display the literal constraint on hover/expand (no paraphrase).
- VL chips show "rige desde [fecha]" — never as vigente without that prefix.
- DI chips include a countdown: "vence el [fecha]" + days remaining.
- RV chips name the triggering inexequibilidad: "revivida tras [sent.cc.X-NNN.YYYY]".

**Success criteria.**
- 100% of cited DE/DT/SP/IE/EC/VC/VL/DI/RV articles in test answers carry a chip.
- The chip styling mirrors the existing `subtopicChip.ts` atomic pattern (per atomic-design memory).
- Component tests pass for all 11 variants.

**How to test.**
- `frontend/tests/vigenciaChip.test.ts` — 11 variants, hover/expand states, accessibility (aria-labels).
- E2E: the 10 historical questions from §2.6 produce answers with vigencia chips visible in rendered HTML.
- Visual regression: screenshot snapshots for each chip variant.

**Effort.** 0.5 frontend engineer × 2 weeks (week 9–10).

**Files.**
- *Read first:* `frontend/src/shared/ui/atoms/subtopicChip.ts` (mirror exactly); `frontend/src/shared/ui/molecules/intakeFileRow.ts`; the atomic-design memory.
- *Create:* `frontend/src/shared/ui/atoms/vigenciaChip.ts` (11 variants); `frontend/tests/vigenciaChip.test.ts`.
- *Modify:* whichever existing molecule renders citation labels in `frontend/src/features/chat/`.
- *Backend contract:* the chat response payload's `citations[].vigencia` field must be populated by 1B-ε's retriever changes; verify the JSON shape before touching frontend.

### 2.8 Sub-fix 1F — Cascade orchestrator (NEW v3)

**What.** Implements §0.7's cascade orchestration. Lives in `src/lia_graph/pipeline_d/vigencia_cascade.py` and runs as part of the Re-Verify Cron (week 4-5 host). Three responsibilities:

1. **Reviviscencia handler.** When a `norm_vigencia_history` row lands with `change_source.type = 'sentencia_cc'` and `state IN (IE)`, scan for every norm previously modified by the now-inexequible source and enqueue re-verify tasks.
2. **Future-dated state flip notifier.** Periodic sweep for rows with `state_from` or `state_until` within the next 30 days; emit operator notifications and enqueue re-verify on dependent norms.
3. **Retrieval-time inconsistency detector.** Read-only consumer used from `pipeline_d/answer_synthesis.py`; returns inconsistency signatures the coherence gate refuses on. Never writes from this path; queues to cron via `vigencia_cascade.queue_reverify(norm_id, reason)`.

**Concrete walk-through — Ley 1943/2018 reviviscencia.** When the historical row landed, here's what should happen:

```
Step 1: cron writes norm_vigencia_history row
   norm_id = ley.1943.2018
   state = IE
   state_from = 2019-10-XX  (C-481/2019 effective date)
   change_source = {type: sentencia_cc, source_norm_id: sent.cc.C-481.2019,
                     effect_type: pro_futuro,
                     effect_payload: {fecha_sentencia: 2019-10-XX,
                                      reviviscencia_implied: true}}

Step 2: VigenciaCascadeOrchestrator.on_history_row_inserted fires
   - Detects: change_source.type = sentencia_cc AND state = IE
   - Queries: SELECT DISTINCT norm_id FROM norm_vigencia_history
              WHERE change_source->>'source_norm_id' = 'ley.1943.2018'
   - Returns ~30 ET articles (the ones Ley 1943 had modified)
   - For each: enqueues re-verify task with supersede_reason = 'cascade_reviviscencia'
                                          triggering_norm_id = sent.cc.C-481.2019

Step 3: cron processes the queue (next tick, 6h cadence default)
   - For each queued norm: invokes VigenciaSkillHarness.verify_norm()
   - Skill checks: is reviviscencia of prior text the canonical interpretation?
   - Most cases: yes → veredicto state = RV with revives_text_version populated
                       change_source = {type: reviviscencia,
                                        source_norm_id: ley.1943.2018,
                                        effect_payload: {triggering_sentencia_norm_id: sent.cc.C-481.2019,
                                                          revives_text_version: 'redacción anterior a Ley 1943/2018'}}
   - Cron INSERTs new norm_vigencia_history row per affected norm
   - Prior VM row gets state_until = state_from of the new RV row, superseded_by_record set

Step 4: retrieval automatically picks up the change on next query
   - norm_vigencia_at_date / for_period both honor the new rows
   - Chips render RV variant on the affected articles
```

**No mid-turn writes.** Steps 2 and 3 are cron-driven. Retrieval at any moment returns the freshest committed state; if a question lands during a cascade-in-progress, retrieval may refuse with `vigencia_inconsistency` (the inconsistency detector's signature). The user gets honest "verificación en curso"; the next query (after cron commits) returns clean.

**Success criteria.**
- The Ley 1943/2018 → C-481/2019 reviviscencia case (the canonical) processes end-to-end: 1 IE row triggers ≥ 20 RV rows (the affected articles); cascade completes within 1 cron tick (default 6h, configurable).
- 0 mid-turn writes to `norm_vigencia_history` from the retrieval path (auditable via the `extracted_by` field — only `cron@v1` and `manual_sme` are valid; never `synthesis@v1` or `retrieval@v1`).
- Inconsistency detector catches the 5 SME-authored test cases (e.g., a question that would cite both a now-RV norm and a chunk written before the cascade landed).
- Future-dated state flip notifier emits operator alerts ≥ 30 days before any flip; alerts include the affected norm count.
- Idempotent: re-running `on_history_row_inserted` on the same record produces the same queue (no duplicate re-verify tasks).

**How to test.**
- `tests/test_vigencia_cascade_reviviscencia.py` — fixture-driven Ley 1943/2018 simulation.
- `tests/test_vigencia_cascade_inconsistency.py` — 5 SME test cases.
- `tests/test_vigencia_cascade_idempotency.py` — re-run safety.
- Integration smoke: deploy cron to staging; insert the Ley 1943 fixture; assert cascade landed.

**Effort.** 0.5 senior engineer × 6 weeks intermittent (weeks 4–10), cumulative ~3 FTE-weeks. Hosted by Re-Verify Cron infrastructure (no separate hosting line).

**Files.**
- *Read first:* `scripts/monitoring/ingest_heartbeat.py` (the cron / heartbeat shape); `scripts/sync_article_secondary_topics_to_falkor.py` (precedent for cron-driven Falkor writes); `src/lia_graph/pipeline_d/answer_synthesis.py` (where `detect_inconsistency` is consumed); `docs/orchestration/coherence-gate-runbook.md` (where `vigencia_inconsistency` fallback_reason gets registered).
- *Create:* `src/lia_graph/pipeline_d/vigencia_cascade.py` (the orchestrator class); `cron/cascade_consumer.py` (cron entry point for re-verify queue consumption); `cron/state_flip_notifier.py` (future-dated alerts); `tests/test_vigencia_cascade_*.py`; `docs/orchestration/cascade-runbook.md` (operator-facing).
- *Modify:* `src/lia_graph/pipeline_d/answer_synthesis.py` (detection-only consumer); `src/lia_graph/pipeline_d/answer_policy.py` (refusal mode for `vigencia_inconsistency`); `docs/orchestration/coherence-gate-runbook.md` (new fallback_reason).

### 2.9 Fix 1 — kill-switch metric (week 6 midpoint, v3 update)

After Sub-fix 1B-β ships (end of week 6), re-run the §1.G SME questions. v3 required result:

- **Zero** citations of `art. 689-1` (currently 2 after Activity 1).
- **Zero** "6 años" claims for firmeza con pérdidas.
- **Zero** dividend tariff claims at 10%.
- **Skill audit log shows ≥ 2 primary sources consulted** for every veredicto fed into retrieval.
- **Every veredicto landed in `norm_vigencia_history` row(s), not in `documents.vigencia` cells.** Auditable via row counts + `extracted_via.run_id` matching the 1B-β batch.
- **`norm_citations` populated for every chunk in the §1.G fixture.** Auditable via SQL on the chunk_ids cited in the eval.
- **All 11 vigencia states present** in the populated `norm_vigencia_history` (V/VM/DE present from the existing 7 fixtures; VC/VL/DI/RV may be sparse but at least one each must be produced by the batch — if absent, the skill prompt's coverage is wrong).

If any of those persist after week 6 (or if skill audit shows shortcuts), **the project is in trouble**. Per `makeorbreak_v1.md`, this triggers the brand/risk perspective: pause and reassess. Per `feedback_thresholds_no_lower`, the 95% spot-check bar does NOT relax to accommodate timing pressure.

---

## §3 — Fix 2 — Parámetros móviles map (UVT/SMMLV/IPC + topical thresholds)

Largely unchanged from v1/v2. Colombia-specific annual amounts (UVT, SMMLV, IPC, plus topical thresholds the SME identified) live in per-year YAML; resolver injects current-year values; composer-side rewrite pass replaces stale values with canonical current ones.

**v3 enrichment:** parameter resolution composes with the two-resolver vigencia model (§0.6). When LIA answers a question about AG 2018, the parameter resolver returns 2018 UVT (not 2026 UVT) — and the planner's `vigencia_query_kind = 'for_period'` cue is the same cue that drives the parameter year-context. One cue, two consumers.

```python
# Conceptual flow:
plan = planner.plan(query)
if plan.vigencia_query_kind == 'for_period':
    period_year = plan.vigencia_query_payload['periodo_year']
    uvt_value = parametros.uvt_for_year(period_year)        # 2018 UVT
    vigencia_rows = norm_vigencia_for_period(plan.vigencia_query_payload['impuesto'], period_year)
else:
    uvt_value = parametros.uvt_for_year(today.year)         # 2026 UVT (default)
    vigencia_rows = norm_vigencia_at_date(plan.vigencia_query_payload['as_of_date'])
```

**Success criteria.** Same as v2 §3: 8 SME questions whose right answer requires a 2026 parameter all produce 2026 values; 0% false rewrites in 50-answer regression; 8 Art. 338 CP questions correctly use the period's UVT (e.g., AG 2018 question → 2018 UVT, even if asked today).

**Effort.** 1 senior engineer × 4 weeks (week 2–6, parallel with Fix 1).

**Files.**
- *Read first:* `src/lia_graph/ui_text_utilities.py:_UVT_REF_RE`; `src/lia_graph/pipeline_d/answer_synthesis.py` (stable facade — do NOT edit; identify implementation module); `src/lia_graph/pipeline_d/answer_synthesis_helpers.py`; `src/lia_graph/pipeline_d/answer_llm_polish.py`; `config/subtopic_taxonomy.json` (precedent JSON-config loader); v3 §0.6 + §0.11 for the planner cue contract.
- *Create:* `config/parametros_moviles/{2020,2021,2022,2023,2024,2025,2026}.yaml`, `src/lia_graph/parametros.py` (resolver), `src/lia_graph/parametros_schema.py` (Pydantic model), `tests/test_parametros_resolver.py`, `tests/test_parametros_year_detection.py`, `evals/parametros_v1/8_uvt_questions.jsonl`, `evals/parametros_v1/8_art338cp_uvt_questions.jsonl` (the new period-aware set), `scripts/audit_parametros_yaml.py`.
- *Modify:* `src/lia_graph/pipeline_d/answer_synthesis_helpers.py` (insert rewrite pass after retrieval, before polish); `src/lia_graph/pipeline_d/answer_llm_polish.py` (extend polish prompt with parameter-protection rule); `src/lia_graph/pipeline_d/planner.py` (the cue extraction is shared with 1B-ε so this is a coordinated change).

---

## §4 — Fix 3 — Anti-hallucination guard on partial mode

Unchanged in goal from v2 §4: `Cobertura pendiente` strings must propagate as a typed `PartialCoverage` value object; composer can never wrap them in fabricated "Ruta sugerida" / "Riesgos" templates; LLM polish prompt forbidden from synthesizing content for partial sub-questions; post-polish regex strip fires if fabricated article references slip through.

**v3 enrichment:** integrates with the v3 persistence model. When retriever fires `PartialCoverage`, the composer can optionally invoke the `vigencia-checker@2.0` skill on the user's specific question — but only via the cron path, not mid-turn (per §0.7.3's no-mid-turn-research policy). Concretely:

1. Retrieval returns partial coverage.
2. Composer renders the partial-coverage block with the existing `Cobertura pendiente` shape.
3. Composer enqueues a `vigencia_cascade.queue_reverify(implied_norm_id, reason='partial_coverage_followup')` task.
4. Next cron tick processes the queue; the new veredicto lands in `norm_vigencia_history`.
5. The user's *next* query hits the populated record → no longer partial.

This is a strict subset of v2's framing. v2 implied a synchronous skill invocation could fill the partial sub-question mid-turn; v3 rules that out. The user gets honest "no encontré evidencia primaria — verificación queued"; the cron does the work.

**Success criteria.** Same as v2 §4: zero fabricated article refs in 12-question fixture; LLM polish never invents content for partial sub-questions; `vigencia_inconsistency` refusals from §0.7.3 mapped to coherence-gate handling.

**Effort.** 1 senior engineer × 4 weeks (week 7–10).

**Files.** As v2 §4 + skill-queue invocation hook (NOT skill-call hook) in `pipeline_d/answer_synthesis_helpers.py`.

---

## §5 — Fix 4 — Ghost-topic kill + corpus completeness audit

Unchanged in goal from v2 §5: every registered topic has ≥ 5 docs OR is de-registered. `tarifas_renta_y_ttd` populate, `regimen_cambiario` promote from `to_upload/`, preflight gate.

**v3 enrichment:** every populated doc runs through `vigencia-checker@2.0` skill at ingest time. The doc's *cited norms* land as `norm_vigencia_history` rows AND `norm_citations` rows in the same transaction. So instead of "add 5 docs and hope," it's "add 5 docs whose every cited norm has been verified against ≥ 2 primary sources, with full v3 vigencia veredicto attached." The doc's own `documents.vigencia` (deprecation view) reflects the most-restrictive state of its anchors — but the load-bearing data is in the norm tables.

Higher quality bar; same wall-time effort because the skill does the verification once per norm and the canonicalizer does the citation extraction once per chunk — both are Fix 1 infrastructure.

**Success criteria.** Same as v2 §5 + new: every newly-populated doc has ≥ 90% of cited norms with non-refusal `norm_vigencia_history` rows; refusals logged for SME triage.

**Effort.** 0.5 SME FTE × 5 weeks (week 8–13) + 0.5 engineer for index, retrieval validation, skill-at-ingest hook.

**Files.** As v2 §5 + a new ingest-time hook `src/lia_graph/ingestion/vigencia_at_ingest.py` that consumes 1B-α scrapers + invokes the skill harness + writes via `src/lia_graph/persistence/norm_history_writer.py` (1B-γ deliverable).

---

## §6 — Fix 5 — Golden-answer regression suite (TRANCHE schema, skill as judge)

**Major v3 update vs v2 §6:** the judge invokes the v3 resolvers at the period the question implies, and the seed is now 7/30 (not 4/30 as v2 noted) thanks to Activity 1.7's three additional fixtures.

**Pre-existing seed (DONE 2026-04-26).** Activities 1.5 + 1.6 + 1.7 produced **7 pre-validated test cases** covering vigencia states V (Art. 290 #5 ET), VM (Art. 689-3 ET), DE (Art. 158-1 ET), IE (Decreto 1474/2025), DT (Arts. 588-589 ET correcciones imputación), SP (Concepto DIAN 100208192-202 num. 20), EC (Art. 11 Ley 2277/2022 zonas francas). Each fixture's `fix_5_skill_eval_seed` block includes `expected_state`, `expected_must_cite`, `expected_must_not_say`. These 7 cover the v2 7-state taxonomy completely.

**v3 expansion: 4 more states to seed.** VC, VL, DI, RV are not yet seeded — SME authors them in week 1 alongside the gate-1 ontology session. Total: 30 cases by week 6 (the Skill Eval gate); 7 pre-seeded + 23 to author of which 4 cover the new v3 states.

**Plus 2 pre-validated TRANCHE test cases** from Activity 1.5's `tranches_de_correccion_pendientes` block — these become the first golden-answer regressions for the corpus's Decreto 1474/2025 content.

**The judge** (unchanged from v2 §6 in mechanics):
1. Posts the question to LIA.
2. Captures LIA's answer.
3. Invokes `vigencia-checker@2.0` skill on each citation in LIA's answer (now reading the v3 `norm_vigencia_history` rows).
4. **v3 addition:** judge calls the appropriate resolver (`norm_vigencia_at_date` OR `norm_vigencia_for_period`) at the date/period the question implies — handles AG 2018 questions correctly via `for_period`.
5. Emits a TRANCHE per skill's `patrones-citacion-v2.md`:

```yaml
output_evaluado: <LIA's verbatim answer>
clasificacion_hallazgo: INCORRECTO | INCOMPLETO | OMISION_COMPLETA | OK
descripcion_error: <if not OK, what's wrong>
norma_real_aplicable: <skill's vigencia veredicto for the relevant norm at the question's period>
norma_real_record_id: <UUID of the norm_vigencia_history row used>     # NEW v3
gravedad: CRITICO | MAYOR | MENOR | NONE
correccion_propuesta: <what LIA should have said>
evidencia_fuente_primaria: [<primary source URLs>]
articulo_norma_afectada: <canonical norm_id>                            # NEW v3 (was free-text "Art. 689-3 ET")
```

CI gate mapping (unchanged):
- CRITICO → blocks merge
- MAYOR → warns + flags for human review
- MENOR → logs only
- OK → passes

**Success criteria.** ≥ 100 golden questions by week 14; ≥ 90% OK; zero CRITICO. Suite runs in < 15 min (parallel via the engine's `ChatClient`). v3 addition: ≥ 95% of TRANCHE rows include a valid `norma_real_record_id` (proves the judge is reading from `norm_vigencia_history`, not heuristics).

**Effort.** SME × 0.5 FTE for authoring (week 1–14) + 0.5 engineer for judge + CI wiring (week 1–4).

**Files.**
- *Read first:* `scripts/eval/engine.py` (reuse — do NOT write a 3rd copy); `scripts/eval/run_sme_validation.py`; `scripts/eval/sme_validation_report.py`; `scripts/judge_100qs.py`; `evals/100qs_accountant.jsonl`; `Makefile` (`eval-c-gold`/`eval-c-full` patterns); `.claude/skills/vigencia-checker/references/patrones-citacion.md` (v1.0); the v2.0 update from sub-fix 1A.
- *Create:* `evals/golden_answers_v1/questions/<qid>.yaml` (one per golden question); `scripts/eval/run_golden.py` (chat runner — thin wrapper over `engine.ChatClient`); `scripts/eval/judge_golden.py` (TRANCHE-emitting judge that invokes v3 resolvers + vigencia-checker); `scripts/eval/golden_report.py` (CRITICO/MAYOR/MENOR/OK dashboard); `.github/workflows/golden_ci.yml` (merge-blocking on CRITICO); `Makefile` target `eval-golden`.
- *Modify:* root `CLAUDE.md` Commands section.

---

## §7 — Fix 6 — Internal corpus consistency editorial pass + corpus-wide hallucination audit

Scope **narrows in v3** vs v2 §7: vigencia reconciliation across docs becomes redundant once `norm_citations` is populated (the retriever filters at norm-level, not doc-level — two docs disagreeing about a norm's vigencia is now resolved by reading the canonical `norm_vigencia_history` row, not by editorial rewrite). Fix 6 stays scoped to *content* hallucinations (EME-A01 fabricated C-077/2025) which are orthogonal to vigencia.

**v3 enrichment 1 — skill as diagnostic tool (carries from v2).** SME runs the skill on each topic's anchor norms; the skill produces the canonical veredicto in `norm_vigencia_history`; the SME marks displaced *content* (not vigencia) sections with `superseded_by: <doc_id>` frontmatter. Vigencia is not in scope for this frontmatter — the norm tables own that.

**v3 enrichment 2 — corpus-wide hallucination audit (carries from v2).** Activity 1.5 found `EME-A01-addendum-estado-actual-decretos-1474-240-2026.md` cites a non-existent `Sentencia C-077/2025` despite a "verificación: 20 marzo 2026" header. Per `docs/learnings/ingestion/corpus-hallucinated-content-EME-A01.md`, run this audit (unchanged grep recipes from v2):

```bash
# Files claiming verification:
grep -rl "verificación\|verificado\|fuentes verificadas\|URLs verificadas" knowledge_base/

# Files with internal citation of specific sentencias / autos:
grep -rE "Sentencia C-[0-9]{3}/(20[0-9]{2})|Auto [0-9]+/(20[0-9]{2})" knowledge_base/

# Files with addendum / estado actual / post-suspension naming:
find knowledge_base -name "*addendum*" -o -name "*estado-actual*" -o -name "*post-suspension*"
```

For each match, run the `vigencia-checker@2.0` skill on the cited sentencia/auto. If the cited ruling does not exist OR its date doesn't match: flag as hallucinated content; corpus document needs editorial rewrite or deprecation.

**v3 enrichment 3 (NEW) — refusal-queue review.** The 1B-δ canonicalizer refusal queue (`evals/canonicalizer_refusals_v1/refusals.jsonl`) is itself a Fix 6 input — ambiguous citations in corpus prose are signals that the prose was sloppy. SME triage produces both canonicalizer rule additions AND content rewrites where citations need disambiguation.

**Success criteria.**
- Re-run a 30-question subset of golden answers: zero contradictions detected at content level (vigencia contradictions are now schema-prevented).
- Each touched document has a clear "canonical | superseded | historical" classification at content level.
- Corpus-wide hallucination audit completes; each "verificación" claim is either re-verified by the skill or the document is flagged for editorial rewrite.
- At minimum: EME-A01 is rewritten with verified facts (replace fabricated C-077/2025 with real C-079/2026); T-I is updated to reflect SP→IE transition (Apr 15 2026); deprecated T-I marked as `superseded_by` the new T-I.
- Canonicalizer refusal queue's high-frequency patterns (≥ 5 occurrences) all triaged by SME and either resolved as canonicalizer rules OR flagged as content-rewrite needs.

**How to test.**
- The judge from §6 detects internal contradictions when LIA's answer cites two values that disagree.
- SME spot-check on the 20 reviewed topics.
- Hallucination audit script (`scripts/audit_corpus_hallucinations.py`) reports: total `verificación` claims found, % verified, % flagged.
- Refusal-queue audit (`scripts/audit_canonicalizer_refusals.py`) reports: total refusals, top patterns, triage status per pattern.

**Effort.** SME × 0.5 FTE × 5 weeks (week 11–13) + 0.5 engineer for the `superseded_by` retrieval support + the corpus-wide hallucination audit script + the refusal-queue triage tooling (~3 days incremental over v2's 2 days).

**Files.**
- *Read first:* the docs flagged in `evals/activity_1_5/decreto_1474_2025_veredicto.json` `fix_6_findings` block (EME-A01 + T-I); `docs/learnings/ingestion/corpus-hallucinated-content-EME-A01.md`; `docs/learnings/process/skill-as-verification-engine.md`.
- *Create:* `docs/re-engineer/corpus_consistency_audit.md` (SME's per-topic findings + reconciliation decisions); `scripts/audit_corpus_hallucinations.py` (greps + skill invocations against `norm_vigencia_history`); per-document frontmatter additions (`superseded_by: <doc_id>`); `evals/corpus_consistency_v1/30q_subset.jsonl`; `scripts/audit_canonicalizer_refusals.py` (NEW v3).
- *Modify:* knowledge_base files flagged for supersession; `src/lia_graph/pipeline_d/retriever_supabase.py` + `retriever_falkor.py` (extend 1B-ε to also demote on `superseded_by` content marker — orthogonal to vigencia); `src/lia_graph/ingestion/parser.py` (read the new `superseded_by` frontmatter field); `src/lia_graph/canon.py` (rules baked from refusal-queue triage).

---

## §8 — Activity series (surgical pre-cursors)

Activities are small, isolated, measurable ships that prove a structural fix's hypothesis before the full fix lands. They are not throwaway — they integrate cleanly into the corresponding Fix.

### Activity 1 ✅ — SQL-only vigencia filter (DONE 2026-04-29 — pre-dates v2/v3)

Migration `20260429000000_vigencia_filter_unconditional.sql` removes the silent bypass that disabled the existing `vigencia NOT IN ('derogada', ...)` filter when `filter_effective_date_max` was passed.

**Measured outcome (clean before/after on §1.G fixture, captured 2026-04-29):**
- `art. 689-1` mentions: 13 → 2 (−85% — the binary flag DOES catch this case).
- `Ley 1429` mentions: 303 → 286 (essentially unchanged — flag too sparse).
- `6 años firmeza`: 13 → 19 (regression — chunk reshuffle let stale "6-año" patterns through).
- §1.G `served_acceptable+`: 21/36 unchanged.

**Learning embedded in v3:** the binary flag's coverage is too sparse to be useful at scale. Real impact comes when 1B-β + 1B-γ populate structured `norm_vigencia_history` for every cited norm, at which point the resolver functions fire correctly across 100% of the corpus.

**Status:** ✅ shipped to staging cloud; remains correct; will be superseded by 1B-ε's resolver-based retrieval.

### Activity 1.5 ✅ — Skill-guided verification of Decreto 1474/2025 (DONE 2026-04-26 ev)

Walked the `vigencia-checker` skill protocol manually on Decreto 1474/2025 (cleanest SP candidate from SME inventory) using WebSearch as primary-source proxy. Produced structured veredicto.

**Outcomes** (full report at `docs/re-engineer/activity_1_5_outcome.md`):
1. ✅ Veredicto produced: state IE (inexequible per Sentencia C-079/2026 of April 15, 2026), NOT the SP the SME inventory expected. Saved at `evals/activity_1_5/decreto_1474_2025_veredicto.json`.
2. ✅ Corpus internal contradiction surfaced: EME-A01 contradicts T-I on dates AND ruling.
3. ✅ Hallucinated corpus content discovered: EME-A01 cites a non-existent "Sentencia C-077/2025"; the real ruling is C-079/2026. **Highest-value finding of the round.**
4. ✅ No Supabase UPDATE applied: the corpus contains *interpretation docs* about the Decreto, not the Decreto's text itself. Right action is editorial (Fix 6), not metadata-flag.

**Lesson** captured in `docs/learnings/ingestion/corpus-hallucinated-content-EME-A01.md` + `docs/learnings/process/skill-as-verification-engine.md`.

**Downstream impacts (already reflected in v3):**
- Fix 6 gains corpus-wide hallucination audit subscope.
- Re-Verify Cron moved week 13 → week 5 per `re-verify-cron-criticality.md`.
- 2 pre-validated TRANCHE test cases for Fix 5.

### Activity 1.6 ✅ — Skill on 3 canonical norms covering V / VM / DE (DONE 2026-04-26 ev)

Manual skill protocol on three high-coverage norms to validate canonical states.

| Fixture | Norm | State produced | Validates |
|---|---|---|---|
| `art_689_3_ET_AG2025_veredicto.json` | Art. 689-3 ET (beneficio de auditoría) | **VM** (Ley 2155/2021 → Ley 2294/2023 prórroga) | Clean modification chain |
| `art_158_1_ET_AG2025_veredicto.json` | Art. 158-1 ET (CTeI deduction) | **DE** (Art. 96 Ley 2277/2022, efectos 2023-01-01) | Clean derogación expresa; ultractividad note for AG 2022 |
| `art_290_num5_ET_AG2025_veredicto.json` | Art. 290 #5 ET (régimen transición pérdidas pre-2017) | **V** with `regimen_transicion` populated | Vigente sin modificaciones; transition regime distinct from a modification |

Combined with Activity 1.5's Decreto 1474/2025 → IE: **4 of 7 v2 vigencia states (V / VM / DE / IE) validated.** Each fixture includes a `fix_5_skill_eval_seed` block.

**Lesson** captured in `docs/learnings/process/activity-as-surgical-precursor.md` and `docs/learnings/retrieval/vigencia-2d-model.md` (worked-examples table).

### Activity 1.5b ✅ — Manual veredicto persistence to staging (DONE 2026-04-27 04:15 UTC)

**Why this existed.** Round 3 (2026-04-26 evening): the 4 veredictos produced by Activities 1.5 + 1.6 lived ONLY as JSON fixtures. Staging cloud Supabase had columns but they were NULL. Activity 1.5b bridged that gap.

**What shipped:**
1. `scripts/persist_veredictos_to_staging.py` (one-shot script, 16,477 bytes).
2. 6 audit log lines in `evals/activity_1_5/persistence_audit.jsonl` (2026-04-27 04:15 UTC):
   - 4 staging-Supabase UPDATEs to `documents.vigencia` + `vigencia_basis` + `vigencia_ruling_id` (4 rows affected total).
   - 2 staging-Falkor MERGE operations creating new norm-source edges with property bags.
3. No regressions: §1.G auto-rubric stays ≥ 21/36 served_acceptable+.

**v3-relevant note.** 1.5b wrote to `documents.vigencia` (the v2 shape). When 1B-γ ships, the 4 rows get re-persisted to `norm_vigencia_history` cleanly via the audit log — no manual reconciliation needed. The Falkor edges similarly get re-emitted with the v3 `(:Norm)` node + property-bag conventions.

**What 1.5b deliberately did NOT do** (binding scope, preserved in v3):
- Did NOT touch local Supabase docker.
- Did NOT touch production (Railway).
- Did NOT apply per-article granularity (4 doc-level updates only).
- Did NOT correct corpus content (EME-A01 hallucination, T-I staleness — those are Fix 6).

### Activity 1.7 ✅ — Skill on 3 norms covering DT / SP / EC (DONE 2026-04-26 evening)

Three skill walkthroughs to complete the v2 7-state coverage of the skill eval seed.

| Fixture | Norm | State produced | Source ruling |
|---|---|---|---|
| `arts_588_589_ET_correcciones_imputacion_AG2025_veredicto.json` | Arts. 588-589 ET (en aplicación a correcciones de imputación de saldos a favor) | **DT** (parcial — desplazada por Art. 43 Ley 962/2005) | Sentencia de Unificación 2022CE-SUJ-4-002 (CE Sección Cuarta, M.P. Julio Roberto Piza Rodríguez) — adoptada por DIAN vía Oficio 3285/2023 |
| `concepto_dian_100208192_202_num20_AG2026_veredicto.json` | Numeral 20 del Concepto DIAN 100208192-202 (TTD: IA en cálculo de dividendos no constitutivos de renta) | **SP** | Auto/Sentencia 28920 del 16-dic-2024 (CE Sección Cuarta, Consejero Milton Chaves García); mantenido por Sentencia 28920 del 3-jul-2025 (numeral 12 levantado, numeral 20 sigue suspendido) |
| `art_11_ley_2277_2022_zonas_francas_AG2023_veredicto.json` | Art. 11 Ley 2277/2022 (numerales 1, 2, 3 y parágrafo 6 — tarifa renta zonas francas) | **EC** | Sentencia C-384/2023 (CC, M.P. Diana Fajardo Rivera + Alejandro Linares Cantillo) — "EXEQUIBLES, en el entendido que el régimen tarifario establecido en el artículo 101 de la Ley 1819 de 2016 continuará rigiendo para los contribuyentes que hubieran cumplido las condiciones para acceder a este antes del 13 de diciembre de 2022" |

Combined with Activities 1.5 + 1.6: **7 of 7 v2 vigencia states (V / VM / DE / DT / SP / IE / EC) validated against real Colombian norms.** Each fixture includes a `fix_5_skill_eval_seed` block. Skill eval set seeded 7/30; 23 cases remain to author (4 of which must cover the v3 new states VC/VL/DI/RV per §0.4).

**Lesson:** SP candidates from SME inventory go stale fast — the Decreto 1474/2025 case flipped SP→IE between SME inventory delivery (morning) and Activity 1.5 (evening). Re-Verify Cron criticality re-affirmed.

**Downstream impacts (reflected in v3):**
- Fix 5 skill eval set design (§0.11.3 contract 4) — 7 of 30 cases pre-seeded.
- 1B-β extractor's expected output distribution: 7-state coverage proven feasible at small scale; 11-state coverage is the v3 target (4 new states need similar fixtures by week 6).
- Sub-unit-first-class (§0.5) is necessary: the SP fixture is on `concepto.dian.100208192-202.num.20` — the whole concepto would lose granularity (numeral 12 was levantado; numeral 20 sigue suspendido).

### Activity 1.7b — VC / VL / DI / RV state-coverage seeding (queued, week 1-2)

**What.** Skill walkthroughs on 4 more norms covering the v3 new states. SME picks canonical candidates in the gate-1 ontology session of sub-fix 1A.

| State | Candidate type | Picking criterion |
|---|---|---|
| **VC** (vigente condicionada — non-CC modulación) | A norm under judicial modulación by CE OR a concepto DIAN whose interpretation is constrained by a posterior concepto without nulidad | SME picks |
| **VL** (vacatio legis) | A recently-published Ley with deferred entry into force (rige desde fecha futura) | SME picks per current legislative pipeline |
| **DI** (diferida — CC le dio plazo al Congreso) | A recent C- sentencia declaring inexequibilidad with plazo al Congreso | SME picks per current judicial calendar |
| **RV** (revivida) | Canonical: any ET article that flipped V→VM via Ley 1943/2018 then back to V/RV via C-481/2019 | SME picks specific article |

**Effort.** 0.5 engineer × 1.5 days (week 1–2) + ~15 min SME consultation per case for canonical-pick.

**Files.** Same shape as Activity 1.7: 4 new JSON fixtures in `evals/activity_1_5/`. No code changes.

**Pre-validates:** Fix 1A skill v2.0 prompt update (proves the 4 new states produce structurally-valid veredictos); Fix 1B-β extractor coverage of the 11-state surface.

### Activity 1.8 — Per-article skill on Ley 1429 (queued, week 5)

Carries v2 §8 forward. Once Fix 1B-α scrapers are operational (week 4), run the skill against ~30 Ley 1429/2010 articles to produce per-article veredictos. UPDATE based on per-article state.

**v3 update:** writes go to `norm_vigencia_history` (via the 1B-γ writer if the catalog is up by week 5) OR are held as JSON fixtures and re-persisted by 1B-γ when it lands. Either path works; the audit log is the canonical record.

**Success criteria.** Per-article veredictos for ≥ 30 Ley 1429 articles in `evals/activity_1_8/ley_1429_veredictos.jsonl`; ≥ 80% flagged DE; vigente articles preserved; §1.G `Ley 1429` mentions drop from 303 → < 50.

**Effort.** 0.5 engineer × 1 day (week 5).

### Activity 6 — Sub-unit canonicalizer pilot (queued, week 2)

**NEW v3.** Validates the §0.5 norm-id grammar before 1B-δ runs at full corpus scale. Pick 50 corpus chunks (mix of high-citation and edge-case prose); run the canonicalizer; SME reviews every output. Iterate until ≥ 95% accuracy on the 50-chunk sample.

**Why this is needed.** The canonicalizer is the load-bearing component of v3 — every downstream sub-fix consumes its output. A 1B-δ run with a buggy canonicalizer corrupts `norm_citations` for the entire corpus. Better to catch the bugs on 50 chunks than 30,000.

**Effort.** 0.5 engineer × 2 days (week 2) + 0.2 SME × 2 days.

**Files.** `tests/test_canon_pilot_50.py` + `evals/canon_pilot_v1/sample_50.jsonl` + an SME-reviewed gold version of expected outputs.

### Future activities (queued, post-launch)

- **Activity 2 — Surgical: drop `Ley-1429-2010.md` chunks from vector index** if Fix 1B-β's results show those chunks are still bleeding into retrieval despite the structured citations.
- **Activity 3 — Surgical: planner-side `vigencia_query_kind` cue extraction** as standalone ship if 1B-ε is delayed.
- **Activity 4 — Skill on labor norms (CST, Ley 50/1990, Ley 789/2002)** — same pattern as tax-law skill; new source hierarchy (MinTrabajo + Cortes laborales). Out of v1 launch scope per §12.
- **Activity 5 — Skill on cambiario (Resolución Externa 1/2018 JDBR + DCIN-83)** — Banco de la República as primary source. Out of v1 launch scope.
- **Activity 7 (NEW v3) — Reviviscencia smoke** — Run the cascade orchestrator (1F) on the historical Ley 1943/2018 → C-481/2019 case as a soak test before launch readiness review.

---

## §9 — Cross-fix dependencies (v3 update)

```
Week:    1  2  3  4  5  6  7  8  9 10 11 12 13 14
A1.5:    ✅  (DONE 2026-04-26 ev — Decreto 1474/2025 → IE; corpus hallucination found)
A1.6:    ✅  (DONE 2026-04-26 ev — 3 norms VM/DE/V; skill eval seed 4/30)
A1.5b:   ✅  (DONE 2026-04-27 04:15 UTC — 4 veredictos persisted to staging)
A1.7:    ✅  (DONE 2026-04-26 ev — DT/SP/EC; skill eval seed 7/30)
A1.7b:   ██  (VC/VL/DI/RV state-coverage seed; week 1-2)
A1.8:                ██  (Ley 1429 per-article; needs scrapers; week 5)
A6:        ██  (canonicalizer 50-chunk pilot; week 2)
F1A:     ██████  (ontology + ChangeSource + canonicalizer; v3-expanded)
F1B-α:   ████████████  (scrapers; CRITICAL PATH)
F1B-β:               ██████████  (extractor batch — articles + sub-units)
F1B-γ:                        ██████  (norms catalog + history; STRUCTURAL REDESIGN)
F1B-δ:                        ██████  (citations link backfill; parallel with γ)
F1B-ε:                                ██████████  (retriever rewire to resolvers)
F1D:                                          ██████  (UI chips, 11 variants)
F1F:                       ██████████████████████  (cascade orchestrator; long tail)
F2:        ████████████   (parámetros móviles, parallel)
F3:                              ████████████  (anti-hallucination + queue-not-mid-turn)
F4:                              █████████████████  (ghost topic + populate)
F5:      █████████████████████████████  (TRANCHE judge — 7 cases pre-seeded; 23 to author)
F6:                                    ████████████  (corpus consistency + hallucination audit)
SkillEval:               ██████████  (30 SME cases — 7 pre-seeded; 23 to author of which 4 cover v3 new states)
ReVerifyCron:        ████  (deploys week 4-5; hosts 1F + periodic refresh)
                       ↑                                         ↑
                       wk-4 KILL                            wk-14 LAUNCH
                       SWITCH                                 GATE
```

**Hard ordering constraints (v3):**
- 1A canonicalizer is on 1B-α and 1B-β's input set generation; A6 pilot validates 1A before 1B-δ.
- 1B-α (scrapers) is the critical path — without scrapers, 1B-β cannot run at acceptable cost.
- 1B-β cannot start until 1A ontology + canonicalizer land AND 1B-α scrapers exist.
- **1B-γ + 1B-δ run in parallel weeks 6–7.** Both depend on 1A + 1B-β. 1B-γ creates the tables; 1B-δ populates the citations link.
- **1B-ε cannot start until BOTH 1B-γ and 1B-δ are complete.** The retriever rewire requires both the resolver functions (1B-γ) AND the citations link (1B-δ).
- **1F can start as soon as 1B-γ ships.** It overlaps 1B-ε.
- 1D requires 1B-ε's chat-response payload changes (chip variants need vigencia state in the citation payload).
- Fix 2 needs 1A's `applies_to_kind` for year-aware parameter resolution → finalizes after 1A but ships parameters incrementally.
- Fix 3 finalizes after 1B-ε (so partial-mode escalation can use the v3 inconsistency detection + cron queue path).
- Fix 6 needs Fix 4's SME bandwidth (weeks 11-13 overlap is tight — SME must split focus).

**Re-Verify Cron is the single-host for cascade.** The week 4-5 deploy carries:
- `cron/reverify_periodic.py` (v2-planned scope: periodic norm freshness).
- `cron/cascade_consumer.py` (v3 1F: re-verify queue from history-row inserts).
- `cron/state_flip_notifier.py` (v3: future-dated state flip alerts).

Single binary, three entry points.

---

## §10 — Decision checkpoints (v3 update)

| Week | Gate | Pass criterion | Fail action |
|---|---|---|---|
| **0** ✅ | Activities 1.5 + 1.6 + 1.7 + 1.5b (DONE) | 7 of 7 v2 vigencia states validated; corpus hallucination found; skill eval set seeded 7/30; staging persistence smoke shipped | Reflected in plan; no further action |
| **1** | Activity 1.7b — VC/VL/DI/RV state-coverage seed | 4 more veredicto fixtures saved; skill eval set at 11/30 | Iterate; not project-threatening |
| **2** | Fix 1A ontology + canonicalizer | 132+ unit tests pass; canonicalizer round-trips §0.5.4 cases; SME signs off on 11-state ontology + skill v2.0 prompt update | Fast iterate; not project-threatening |
| **2** | Activity 6 — canonicalizer 50-chunk pilot | ≥ 95% canonicalizer accuracy on SME-reviewed 50-chunk sample | Iterate canonicalizer rules before 1B-δ at full scale |
| **4** | Fix 1B-α scraper integration | All 5 scrapers fetch ≥ 30 known norms; cache hit rate measured | If any scraper structurally broken: pause; redesign cache key or selector strategy |
| **5** | Re-Verify Cron deployment (v3 — hosts cascade orchestrator) | Cron operational; first re-verification pass over the 7 already-extracted veredictos detects the T-I staleness (SP→IE) and re-emits IE | Engineering iteration on cron triggers |
| **5** | Activity 1.8 — Ley 1429 per-article | ≥ 30 articles classified; UPDATE applied OR held as JSON; §1.G `Ley 1429` mentions < 50 | Pre-Fix-1B-β validation of the extraction pattern at small scale |
| **6** | **Fix 1B-β kill switch** (the critical one) | Zero `art. 689-1`/`6 años`/`10% dividendo` citations in §1.G re-run; skill audit shows ≥ 2 primary sources per veredicto; veredictos in v3 shape (structured `change_source`); all 11 states represented in extraction output | **Project in trouble.** Pause to reassess per `makeorbreak_v1.md`. Per `feedback_thresholds_no_lower`, the 95% bar does NOT relax. |
| **6** | Skill-eval set | 30-case eval shows skill ≥ 90% correct on hard checks across 11 states; 0 false-positive veredictos | Iterate skill prompt before Fix 1B-β at scale |
| **7** | **NEW v3 gate — Norm catalog + citations link populated** | `norms` row count matches canonicalized input set; `norm_vigencia_history` has rows for every non-refusal extraction; `norm_citations` populated for ≥ 95% of `document_chunks`; resolver functions pass ≥ 28/30 SME pairs | If any < target: pause; the persistence layer must be solid before 1B-ε joins through it |
| **9** | Fix 1B-ε retriever rewire | 30 vigente questions: 0 derogated leaks; 10 historical questions: ultractividad correct; 8 Art. 338 CP questions correct | Engineer-level fix; not project-threatening |
| **10** | Anti-hallucination + 11-chip UI + cascade orchestrator end-to-end | 0 fabricated article refs in 12-question fixture; all 11 chip variants render; Ley 1943 reviviscencia smoke processes end-to-end (≥ 20 RV rows produced from 1 IE row) | Engineer-level fix |
| **13** | Topic-completeness + corpus-wide hallucination audit + canonicalizer refusal triage | Every registered topic ≥ 5 docs OR de-registered; every "verificación" claim re-verified or flagged; high-frequency canonicalizer refusal patterns triaged | SME backlog overflow; defer 3+ topics to v2 launch |
| **14** | Final pre-launch gate | §1.G ≥ 24/36 in 🟨 or better; zero ❌; golden suite ≥ 90% OK, zero CRITICO; skill audit log clean; resolver-function correctness ≥ 28/30; no mid-turn writes to `norm_vigencia_history` (auditable via `extracted_by` field) | Soft-launch denied; data-driven extend-or-liquidate decision |

---

## §11 — Budget allocation ($525K, v2 envelope preserved)

The v3 redesign sits within v2's funded envelope. The reserve and contingency lines absorb the line-item shifts; no incremental funding needed.

### §11.1 — Carries forward from v2

The v2 §11 budget table is preserved as the binding allocation. Engineering FTE counts unchanged; SME bandwidth unchanged; LLM extraction line ($1K) unchanged (re-estimated cost in §0.11.1 is $1,420 — within the line's tolerance + cost-reserve absorbs the $420 delta).

### §11.2 — Line-item shifts (v2 → v3)

These are reallocations within the envelope, not new spend:

| v2 line | v3 effect | Direction |
|---|---|---|
| Engineering: 2 senior backend × 14 wks | 1B-γ now writes 3 tables instead of adding columns; 1B-δ is new but parallels 1B-γ; 1F is new but absorbs reserve | broadly unchanged; 1F is the largest net new |
| Frontend: 0.5 FTE × 4 wks | 11 chip variants instead of 7 — same atomic-design pattern, more cases | small upward pressure absorbed by reserve |
| SME: 0.5 FTE × 14 wks | extra ontology session in week 1 (skill v2.0 prompt update); refusal-queue triage in weeks 11-13 | slightly higher SME load weeks 1-2 and 11-13 |
| LLM extraction (1B-β) | $1K line covers ~$1,420 actual; sub-units add ~$300 vs articles-only | within line + reserve |
| QA + CI tooling (Fix 5) | 30 cases × 11 states (was 30 × 7); same eval engine reuse; judge gains period-aware resolver call | unchanged in $; slightly higher SME authoring load |
| Reserve / contingency | Absorbs: the 1B-δ new sub-fix (~3 FTE-weeks), the 1F cascade work (~3 FTE-weeks intermittent), the canonicalizer pilot (~0.5 FTE-week), refusal-queue tooling (~3 days) | reserve deploys; remaining envelope ≥ $4K post-deployment |

Net: same total $525K; reallocations sit entirely within the v2 reserve. The granular per-line table is in v2 §11 — kept there as the canonical record. v3's §11 is interpretive overlay only.

### §11.3 — What might break the envelope

Three risks could push v3 outside v2's funded scope:

1. **Sub-unit volume turns out ≥ 5× larger than estimated.** The corpus-citation extractor produces an estimated ~22,000 sub-unit norm_ids; if reality is ≥ 100,000, the LLM extraction line strains. Mitigation: 1B-β can run articles-only first, sub-units in a second pass, and the second pass can be deferred to post-launch if budget tightens.
2. **Canonicalizer refusal rate stays > 10%.** If the canonicalizer can't disambiguate at the rate v3 assumes, SME triage time balloons. Mitigation: Activity 6 (week 2) is specifically gated to catch this; if pilot shows > 10% refusal, redesign rules before 1B-δ.
3. **Cascade orchestrator generates feedback loops in production.** If 1F's queue grows faster than the cron drains it (e.g., a sentencia triggers cascades that themselves cite norms causing further cascades), operator time increases. Mitigation: cron rate-limit + max-queue-depth alarm; documented in `docs/orchestration/cascade-runbook.md` (1F deliverable).

If any of these breach: v3 §10 week-6 or week-7 gates catch it; pause-and-reassess per `makeorbreak_v1.md`.

---

## §12 — What this plan deliberately does NOT do

Carries v2 §12 forward. Items marked **(NEW v3)** are persistence-redesign deltas.

- **No more incremental gates** (`§1.H`, `§1.I`...) on `next_v5.md`. Chain closed; reopen only after Fix 1+2+3 ship.
- **No threshold relaxation.** Per `feedback_thresholds_no_lower`. The bar stays "safe to send to a client."
- **No soft-launch with disclaimer.** Disclaimers don't transfer the risk.
- **No corpus expansion until Fix 1B-γ + 1B-δ land.** Adding documents without `norm_citations` populated multiplies contamination surface.
- **No retriever rewrite.** Architecture is sound; 1B-ε changes the *join surface* (resolvers + citations link) — not the algorithm.
- **No LLM model upgrade as first-line fix.** Better model fed contradictory or stale evidence still produces wrong answers.
- **No skill-bypass for "convenience" extractions.** The skill's burden-of-proof discipline is the safety contract — engineers may not write code that emits a `Vigencia` value object without skill or SME-signed manual override.
- **No "trust the binary parser flag" for derived decisions.** Activity 1 proved the flag is too sparse. Use Vigencia value objects (skill-emitted) for any retrieval / display / judge decision.
- **No "lite" conversational mode for the skill in v2 launch.** Deferred to v2.
- **No version-comparator scrapers in v2 launch.** Useful future feature; not on critical path.
- **No municipal-norm verification (ICA, predial) at launch.** Skill's `fuentes-primarias.md` notes this is heterogeneous; out of scope.
- **(NEW v3) No vigencia writes to `documents.vigencia` after 1B-γ ships.** The deprecation view exists for one release; subsequent code that writes vigencia state goes through `norm_history_writer.py` to `norm_vigencia_history`. PR review enforces.
- **(NEW v3) No free-text `vigencia_basis`.** Replaced by structured `change_source` discriminated union. Any code writing free-text basis prose to a vigencia-related column is rejected at review.
- **(NEW v3) No Postgres trigger functions for cascade.** The orchestration is cron-driven (§0.7.1). Trigger functions are explicitly rejected as invisible operational tax.
- **(NEW v3) No mid-turn vigencia research.** Retrieval refuses on inconsistency + queues to cron; never invokes the skill from inside a request handler. Auditable via the `extracted_by` field — only `cron@v1` and `manual_sme:<email>` are valid; `synthesis@v1` and `retrieval@v1` are forbidden writers.
- **(NEW v3) No flattening of sub-unit norm_ids to whole-article granularity.** "The parágrafo you care about hasn't changed in 10 years" must stay answerable. The catalog INSERT cost is one-time; the granularity is permanent.
- **(NEW v3) No silent DT classification by canonicalizer.** DT is contested by definition; the canonicalizer never auto-flips a `V`/`VM` row to `DT`. The skill emits DT; SME confirms via the `change_source.effect_payload.contested` field; refusal is the safe default when no official pronouncement exists.
- **(NEW v3) No retroactive write to `state_from` without explicit override.** The `state_from` field is the LEGAL effective date, which can be earlier than `extracted_at`. The writer requires an explicit `is_retroactive=True` flag (passed by the skill's structured output) to accept a `state_from` more than 30 days in the past — protects against accidental retro writes from extraction batch errors.

---

## §13 — What "done" looks like (v3 launch readiness)

At week 14, the operator runs `make eval-launch-readiness`. The output:

```
=== Launch Readiness Report (v3) ===
Vigencia integrity (per Fix 1B-γ + 1B-δ + 1F):
  norms catalog row count:                                  N    ✅ (matches canonicalizer input set)
  norm_vigencia_history row count:                          M    ✅ (≥ N; multiple states per norm tracked)
  norm_citations populated for chunks:                  ≥ 95%    ✅
  Append-only enforcement (UPDATE/DELETE attempts):        0    ✅ (DB-level grants)
  Future-dated rows honored (state_from > today):          ≥ 1    ✅ (at least one VL or DI in production)
  Skill audit log: ≥ 2 primary sources per veredicto:    100%    ✅
  EC + VC veredictos with literal interpretive_constraint: N/N   ✅
  Topics with 0 docs:                                       0    ✅
  Mid-turn writes to norm_vigencia_history (forbidden):     0    ✅ (extracted_by audit)

Retrieval safety (per Fix 1B-ε + Fix 1F):
  Default-mode queries with derogated-article leaks:    0 / 30   ✅
  Historical queries (vigencia_at_date past) — ultract OK: 10/10  ✅
  Art. 338 CP for_period queries correct:                8 / 8   ✅
  Pre-Ley-2277 dividend tariff in vigente queries:      0 / 12   ✅
  6-year firmeza claims in vigente queries:              0 / 8   ✅
  art. 689-1 leaks anywhere:                            0 / 30   ✅
  Resolver-function correctness on SME pairs:          ≥ 28/30   ✅
  Cascade orchestrator processed reviviscencia smoke:    1+      ✅ (Ley 1943 → C-481/2019 → RV cascade end-to-end)

Anti-hallucination (per Fix 3):
  Fabricated article refs in partial-mode answers:      0 / 20   ✅
  Skill refusal rate on poorly-covered queries:    reasonable    ✅
  Vigencia inconsistency refusals (Fix 1F detector):   sane     ✅ (queue depth bounded)

Quality (per Fix 5):
  §1.G SME re-run, 🟨 or better:                       26 / 36   ✅ (≥ 24)
  §1.G SME re-run, ❌:                                  0 / 36   ✅
  Golden answers OK + MENOR:                          96 / 100   ✅ (≥ 90%)
  Golden answers CRITICO:                              0 / 100   ✅
  TRANCHE rows with valid norma_real_record_id:        ≥ 95%    ✅

Skill operational (per Skill Eval + Re-Verify Cron):
  Skill 30-case eval correctness (across 11 states):    ≥ 90%    ✅
  Re-verification cron last 90 days:                  all green  ✅
  Cascade-consumer queue drain rate:                   healthy   ✅

LAUNCH READINESS: GREEN — soft-launch to 10–20 friendly cohort APPROVED.
```

If GREEN: soft-launch with explicit beta framing + instrumented client-incident tracking. If RED on any line: data tells us what's broken; do not relax thresholds per `feedback_thresholds_no_lower`.

---

## §14 — Glossary (v3 extensions)

**Colombian tax law (unchanged from v1/v2):**
- **AG / DIAN / ET / UVT / SMMLV / IPC / vigente / derogado / suspendido / régimen de transición / TTD / IA / INR / RLG / PN / PJ / SAS / ZOMAC / ZESE / Zonas Francas / Concepto DIAN / Consejo de Estado / Sentencia C-/T-/SU-** — see v1 §13.

**Vigencia state codes (v3 — 11 states):**
- **V** — Vigente sin modificaciones; cite freely
- **VM** — Vigente modificada; cite ONLY current text + chain
- **DE** — Derogada expresa; never cite as vigente
- **DT** — Derogada tácita; cite only with official pronouncement; flag if contested
- **SP** — Suspendida provisional CE; advertencia + T-series link mandatory
- **IE** — Inexequible CC; never cite (unless effects diferidos active)
- **EC** — Exequibilidad condicionada CC formal; cite WITH literal Court text
- **VC** — Vigente condicionada (modulación non-CC); cite WITH literal modulating constraint
- **VL** — Vacatio legis (publicada, no rige aún); never cite as vigente; flag rige_desde
- **DI** — Diferida (CC le dio plazo al Congreso); cite as vigente con plazo explícito
- **RV** — Revivida (resucitada por inexequibilidad de la norma derogante); cite WITH reviviscencia chain

**Skill terms (v2, carried forward):**
- **Veredicto** — Skill's structured output for a (norm, period) query.
- **TRANCHE** — Skill's audit-LIA output format (INCORRECTO/INCOMPLETO/OMISIÓN + GRAVEDAD).
- **Burden of proof inversion** — Skill must refuse veredicto without ≥ 2 primary sources.
- **Aplicabilidad fiscal** — The 2D dimension: vigente *for what period*. Not the same as vigente *today*.
- **Doble fuente primaria** — Mandatory pair of authoritative sources per source-type rules.
- **Ultractividad** — Derogated norm continues to apply to past hechos económicos when it was vigente.

**Persistence terms (NEW v3):**
- **Norm-keyed persistence** — Vigencia state is a property of a `norm_id`, not of a corpus document. The norm tables are the canonical record; documents cite norms.
- **`norm_vigencia_history`** — The append-only state-transition table. Corrections are new rows that supersede priors via `superseded_by_record`. UPDATE and DELETE are forbidden at the role grant level.
- **`norm_citations`** — Link table from `document_chunks` to cited `norms`, with role and anchor_strength.
- **`change_source`** — Structured discriminated-union JSONB column on `norm_vigencia_history` capturing the source of each state transition (the type-specific union from §0.3.3).
- **Source norm_id** — The canonical id of the artifact that *caused* the state transition (the modificadora, the derogadora, the sentencia, etc.). Field path: `change_source.source_norm_id`.
- **Anchor strength** — On `norm_citations`: ley | decreto | res_dian | concepto_dian | jurisprudencia. The retriever's synthesis policy gates on this.
- **`norm_vigencia_at_date(D)`** — Resolver function for instantaneous-tax / procedimiento queries. Returns the row whose state_from <= D < state_until.
- **`norm_vigencia_for_period(impuesto, year)`** — Resolver function for impuestos-de-período queries. Honors Art. 338 CP. Returns the row applicable to the period, which may be the predecessor of `at_date(today)`.
- **Norm-id grammar** — The canonical id format from §0.5: `et.art.X[.par.Y] | ley.N.YYYY[.art.X] | decreto.N.YYYY[.art.X] | res.EMISOR.N.YYYY[.art.X] | concepto.dian.N[.num.X] | sent.cc.X-N.YYYY | auto.ce.N.YYYY.MM.DD | sent.ce.N.YYYY.MM.DD`.
- **Sub-unit (first-class)** — A parágrafo / inciso / numeral / literal as a row in `norms` with its own history. Contrast: a `sub_unit` text column on a single article-level row, which v3 explicitly rejects.
- **Cascade orchestration** — The cron-driven flow that propagates state changes across norms. When a sentencia row lands with `state IN (IE, VC, RV)`, the cascade enqueues re-verify on every norm previously affected by the source. Lives in `pipeline_d/vigencia_cascade.py`.
- **Reviviscencia** — Colombian legal doctrine: when a derogating norm is declared inexequible, the prior text revives. Encoded as state `RV` with `change_source.type = 'reviviscencia'`. Canonical case: Ley 1943/2018 → C-481/2019.
- **Future-dated state** — A row with `state_from > today`. Valid for VL (vacatio legis), DI (paired with future IE row), and cascade pre-writes. The resolver naturally honors future-dated rows; the cron emits operator notifications when flips approach.
- **Inconsistency detector** — The read-only consumer in `vigencia_cascade.detect_inconsistency` used from retrieval. Returns signatures the coherence gate refuses on. Never writes; queues to cron.
- **Refusal-queue triage** — Process by which canonicalizer refusals (ambiguous mentions in corpus prose) are reviewed by SME and either resolved as new canonicalizer rules OR flagged as content-rewrite needs (Fix 6 input).
- **`vigencia_query_kind`** — Planner cue field: `'at_date' | 'for_period' | None`. Determines which resolver the retriever calls.

**Project terms (carried from v1/v2):**
- **`pipeline_d` / `main chat` / `Normativa` / `Interpretación` / `graph_native` / `graph_native_partial` / `topic_safety_abstention` / Coherence gate Cases A/B/C / `router_topic` vs `effective_topic` / TEMA-first retrieval / Six-gate lifecycle / Status emoji convention** — see v1 §13.

---

## §15 — First-day playbook for a fresh engineer / LLM (v3)

If you are starting on this fix plan with zero context, follow this exact sequence.

**Hour 1 — orient**
1. Read `CLAUDE.md` end-to-end (~15 min).
2. Read `docs/re-engineer/exec_summary_v1.md` (~5 min — the founder's view).
3. Read `docs/re-engineer/makeorbreak_v1.md` §0 + §2 (~15 min).
4. Read `docs/re-engineer/skill_integration_v1.md` (~15 min — the change-driver behind v2).
5. Skim `.claude/skills/vigencia-checker/SKILL.md` (~10 min — the skill router).

**Hour 2 — orient (continued, v3-specific)**
1. Read this document (`fixplan_v3.md`) §0 + §0.1 (~15 min — the redesign drivers).
2. **Read this document §0.2 (mutation surface) + §0.3 (persistence model) + §0.5 (norm-id grammar) + §0.6 (resolvers) + §0.7 (cascade)** (~30 min — load-bearing).
3. Skim `docs/orchestration/orchestration.md` table of contents + env matrix (~10 min).
4. Read `docs/re-engineer/sme_corpus_inventory_2026-04-26.md` (~10 min — the SME's authoritative law map).
5. **Read the 7 already-extracted veredictos** in `evals/activity_1_5/*.json` (~15 min — see what the skill output looks like in practice; note the v2 shape that will be upgraded to v3 in 1B-γ).
6. **Read `evals/activity_1_5/persistence_audit.jsonl`** (~5 min — the Activity 1.5b audit log; shows the v2 write paths v3 supersedes).
7. Skim the closed learnings (each ~3-5 min): `docs/learnings/retrieval/vigencia-binary-flag-too-coarse.md`, `vigencia-2d-model.md`, `docs/learnings/ingestion/corpus-hallucinated-content-EME-A01.md`, `docs/learnings/process/skill-as-verification-engine.md`, `activity-as-surgical-precursor.md`, `re-verify-cron-criticality.md`.

**Hour 3 — hands on, low-risk**
1. `make supabase-start && make supabase-status` to bring up local Supabase.
2. `npm run dev:check` to verify launcher preflight passes.
3. `PYTHONPATH=src:. uv run pytest tests/test_phase1_runtime_seams.py -q` — should pass; validates environment.
4. Open `evals/sme_validation_v1/runs/20260427T021512Z_activity1_vigencia_filter/verbatim.md` and read 5 of the 36 verbatim answers — the post-Activity-1 ground truth your fix has to improve.
5. **Query staging cloud Supabase** (read-only psql session): `SELECT vigencia, vigencia_basis, vigencia_ruling_id FROM documents WHERE relative_path LIKE '%2277%' LIMIT 10;` — see the v2 column shape currently in production.
6. **(NEW v3)** Open `docs/re-engineer/fixplan_v3.md` §0.3.1 schema — the three new tables. These do not exist yet; they ship in 1B-γ. Reading the SQL helps internalize the shape.

**Hour 4 — locate your fix's anchor files**
1. Find your assigned sub-fix's "Files — Read first" list in §2-§7.
2. Open each. Read enough to orient.
3. Sketch your plan against the gate-1 + gate-2 template in `docs/aa_next/README.md`.
4. Push the gate-1 + gate-2 sketch to your tech lead for sign-off BEFORE writing any code.

**Day 2 onwards — the discipline**
- Every code change: update the relevant runbook in the same PR.
- Every `LIA_*` flag or migration: bump env matrix + change-log row.
- Every ship: produce gate-3 numeric evidence (not just unit tests) before 🧪.
- Every ship: produce gate-5 target-env evidence before ✅.
- Every status report: Bogotá AM/PM time, plain language, end with concrete next-step.
- Any code that touches vigencia, derogación, modificación: invoke `vigencia-checker@2.0` skill. Don't write your own classification logic.
- **(NEW v3) Any vigencia write goes through `src/lia_graph/persistence/norm_history_writer.py`.** Direct INSERT to `norm_vigencia_history` is forbidden in application code; the writer enforces the §0.3.3 `change_source` shape, the canonicalizer for `source_norm_id`, and the append-only invariants.
- **(NEW v3) Any free-text norm mention in code or content goes through `src/lia_graph/canon.py`.** Never invent a norm_id format; never substring-match a citation. The canonicalizer is the single source of truth.

**When you hit something this document doesn't cover**
- Convention question → `CLAUDE.md` first, then `AGENTS.md`.
- Architecture question → `docs/orchestration/orchestration.md` first, then runbook.
- Failure-mode question → `docs/orchestration/coherence-gate-runbook.md` for refusals, `retrieval-runbook.md` for retrieval issues.
- Vigencia question → `.claude/skills/vigencia-checker/` first, NEVER your training-data memory.
- **(NEW v3) Persistence question** → this document §0.3 first, then `docs/orchestration/cascade-runbook.md` (1F deliverable) for cascade questions.
- **(NEW v3) Norm-id question** → this document §0.5 first; if the canonicalizer refuses on a real corpus mention, log it to the refusal queue rather than guessing.
- Lessons from past incidents → `docs/learnings/`. Search before reinvention.
- This document is wrong / incomplete → submit a PR adding the section. Don't work around the gap silently.

---

*v3, drafted 2026-04-27 (Bogotá) immediately after operator pushback on per-document persistence + audit of the Colombian mutation surface. Supersedes `fixplan_v2.md` (preserved as historical record of the column-shaped persistence approach v3 replaces). Open for amendment by adding numbered sub-sections rather than overwriting.*
