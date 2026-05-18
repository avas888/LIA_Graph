# fix_v26_may.md — corpus-side cleanup + remaining compat-allowlist gaps — DRAFT

> **Status.** Scope ticket only — opened 2026-05-17 PM Bogotá while v25 was still in P10 internal close. Not yet executable. Promoted to a full fix doc only when v25 closes and operator signs off.
>
> **Why this exists.** v25 surfaced two structural issues the runtime safety-nets can mitigate but not fix at the root:
>
> 1. **Corpus mis-tagging.** Chunks tagged `costos_deducciones_renta` whose body content is actually zona-franca / tarifa-renta-y-ttd. v25 P13 added runtime defense (topic-aware demotion + post-template strip) but the underlying corpus rows are still polluted. Q1 zona-franca leakage is the canonical example.
> 2. **Sectorial compat allowlist coverage.** 52 sectorial / niche topics (`sector_*`, `zomac_zese_*`, `sagrilaft_ptee`, etc.) still have NO `compatible_doc_topics.json` entries. v25 closed the chat-time Tier-1 set (added 27 entries: retención / IVA / laboral / regimen_simple / ICA / RTE / NIIF Pymes / etc.). Tier-2 sectorial topics remain.
>
> **Companion docs.** [`fix_v24_may_SCOPE.md`](fix_v24_may_SCOPE.md) — cloud-corpus pollution retirement (v24's mandate; v26 inherits the retirement results). [`fix_v25_may.md`](fix_v25_may.md) — predecessor; closes G8–G16 runtime weaknesses.

---

## §0 What v26 closes

| ID | Generic weakness | v25 mitigation | v26 fix |
|---|---|---|---|
| C1 | Corpus mis-tag — `document_chunks.topic` lies about the chunk's actual content (zona-franca tagged `costos_deducciones_renta`) | Runtime demote via `score_topic_aware_pollution` + post-template `off_topic_content_strip` regex | Retag affected chunks at ingest (re-classifier sweep), backfill `topic` column on existing rows |
| C2 | 52 sectorial topics without `compatible_doc_topics.json` entries — `allowed = {router_topic}` degenerates the filter | None (filter falls back to single-topic allowlist) | Add SME-validated entries for `sector_*` chat-time routers when needed; revisit which sectorial topics actually route in chat-time |
| C3 | `documents.topic` / `document_chunks.topic` schema names mismatch with internal `topic_key` field in some loader paths (already harmless because v25 audit confirmed graceful fallbacks everywhere) | n/a — confirmed clean in v25 P13 audit | Optional consistency pass: rename internal manifest fields to match the Supabase column names (`topic` / `subtema`) and drop fallback code |
| C4 | Práctica chunks with NULL `topic` in Supabase escape the topic-gate (kept by "no penalty on tagging gaps" rule) | Defense-in-depth `off_topic_content_strip` regex | Ingest pass to backfill `topic` on the práctica-tagged chunks that currently have NULL |

---

## §1 v25 → v26 hand-off (from `fix_v25_may.md` P13)

### §1.1 Verbatim corpus-pollution evidence surfaced by Q1 re-probe

- **Chunk-tag lie.** `topic=costos_deducciones_renta` chunks contained Ley 2277/2022 art. 11 / UIB-UIS / MinCIT / Decreto 0049/2024 prose. These are zona-franca / tarifas_renta_y_ttd content with the wrong tag.
- **Path of escape (pre-v25-P13).** RPC returns `topic="costos_deducciones_renta"` → P11 evidence filter keeps the chunk (allowed set includes router topic) → synthesis composes template → polish rejects on counterfactual_entity → fallback shows the polluted template → user sees zona-franca.
- **v25 mitigation in place.** P11 evidence filter + P13 práctica topic_key plumbing + P13 post-template `off_topic_content_strip` regex catches the four most-leaked families (zona_franca, incrngo_donaciones, dividendos, inc_vehiculos).

### §1.2 The 27 compat entries v25 P13 already added

See `fix_v25_may.md` §6 run log (2026-05-17 ~7:45 PM Bogotá entry) and `git log -p config/compatible_doc_topics.json` for the verbatim list. Covers retención / IVA / procedimiento / laboral / parafiscales / reforma_pensional / comercial_societario / regimen_simple / informacion_exogena / estados_financieros_niif / niif_pymes / niif_plenas / ica / RTE / dividendos / INC / ganancia_ocasional / rentas_exentas / pérdidas / RUB / régimen_cambiario / RUT / patrimonio / RLG / ingresos / descuentos / GMF / zonas_francas / tarifas.

### §1.3 The 52 topics still without compat entries (Tier-2)

```
activos_exterior          beneficio_auditoria       contratacion_estatal
datos_tecnologia          devoluciones_saldos_a_favor  economia_digital_criptoactivos
emergencia_tributaria     estatuto_tributario       firmeza_declaraciones
impuesto_timbre           impuestos_saludables      inversiones_incentivos
leyes_derogadas           niif_microempresas        normas_internacionales_auditoria
obligaciones_profesionales_contador  otros_sectoriales        presupuesto_hacienda
proteccion_datos_personales  regimen_sancionatorio     reformas_tributarias
renta_presuntiva          retencion_fuente_general  sagrilaft_ptee
sector_administracion_publica  sector_agropecuario   sector_ciencia
sector_comercio_internacional  sector_cultura        sector_deporte
sector_desarrollo_regional  sector_economia         sector_educacion
sector_emprendimiento     sector_energia_mineria    sector_financiero
sector_inclusion_social   sector_infancia           sector_juegos_azar
sector_justicia           sector_medio_ambiente     sector_politico
sector_profesiones_liberales  sector_puertos        sector_salud
sector_servicios          sector_telecomunicaciones sector_transporte
sector_turismo            sector_vivienda           zomac_zese_incentivos_geograficos
```

**Curation rule for v26 (per `feedback_thresholds_no_lower`):** every new entry must (a) come from an SME-validated adjacency, (b) cite an evidence_source (audit, SME response, or Phase-2 measurement), (c) preserve the existing 2-doc match threshold.

---

## §2 Likely workstreams

1. **Corpus retag sweep.** Re-classifier pass over chunks tagged `costos_deducciones_renta` to detect zona-franca / RTE / tarifa content. Touchpoint: `ingest_classifiers.py` + a backfill script that rewrites `document_chunks.topic` for false-positive chunks.
2. **Práctica `topic` backfill.** SQL pass: `UPDATE document_chunks SET topic = <inferred> WHERE topic IS NULL AND knowledge_class = 'practica_erp'`. Should be small (~hundreds of rows).
3. **Tier-2 compat curation.** As audit cycles surface specific sectorial questions, add the relevant compat entries with SME sign-off.
4. **Consistency pass on internal `topic_key`.** Optional: rename the few manifest-loader fields to match `topic` / `subtema` so future contributors don't trip on the same dual-naming.
5. **Retire residual zona-franca regex (post-corpus-fix).** Once corpus retagging closes, the `off_topic_content_strip` regex becomes dead code — should retire to avoid silent drift.

---

## §3 Pre-conditions

- v25 internal close (P10) ✅ assumed by promotion time.
- v24 cloud retire ✅ (covers the worst pollution; v26 picks up what remains).
- External SME re-run on combined 20-question superset (v25 D-S2) returns avg ≥ 4.0/5 + zero 1s with v25 fixes — proves the runtime safety-nets work and the corpus retag is the right next layer.

## §4 Not in scope (defer further)

- Full corpus reingest. v26 is targeted retag, not a re-extraction.
- Falkor topology change. Edge structure stays; only `:DocumentNode` / `:ChunkNode` topic properties change.
- Sectorial sub-topic taxonomy redesign. Sub-topic registry is `feedback_subtopic_aliases_breadth`-protected; v26 only adds compat entries, not new sub-topics.

## §5 Status

- 💡 idea opened 2026-05-17 PM Bogotá by `fix_v25_may.md` P13 hand-off.
- 🟡 not started (gated on v25 closing + v24 retirement + external SME verdict).

---

*Drafted 2026-05-17 PM Bogotá by claude-opus-4-7 as part of v25's P13 audit-driven cleanup. Promote to executable plan only when v25 closes and operator signs the v26 mandate.*
