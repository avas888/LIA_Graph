# Ingest Fix v2 — Sub-topic Tagging in AUTOGENERAR (Stub / Future Plan)

**Status:** STUB — not started, not approved. Authored 2026-04-20 alongside `ingestfixv1.md` Decision G2 ratification.
**Trigger:** ship `ingestfixv1.md` Phase 8 to production, accumulate ≥4 weeks of real ingest data + retrieval queries against the topic-tagged corpus, then evaluate whether sub-topics would meaningfully improve retrieval precision.
**Owner:** future session (read this doc cold and pick up; everything load-bearing is captured here).

---

## 1. Why this is v2 and not v1

User wants topics + sub-topics + synonyms in AUTOGENERAR. v1 ships topics + synonyms (Lia_contadores parity). Sub-topics were deferred for one specific reason: **without a curated seed sub-topic list per parent topic, the LLM would mint inconsistent sub-topic slugs across documents** (e.g. one doc tagged `presuncion_costos_independientes`, another `presuncion_costos`, a third `costos_presuntos_indep`). Topic-level synonym detection works in Lia_contadores because the canonical topic list is fixed (~40 keys); sub-topics have no equivalent canonical seed yet.

v2 closes that gap: seed first, tag second.

---

## 2. What "maximalist" means here

The maximalist sub-topic implementation has **five** components, each non-trivial:

### 2.a Curated sub-topic seed registry

For every parent topic in `topic_taxonomy.py` (`laboral`, `iva`, `declaracion_renta`, `ica`, …), enumerate the **5–15 most operationally meaningful sub-topics** that a senior accountant would think in.

Example for `laboral`:
- `jornada_maxima_legal`
- `vacaciones_compensacion`
- `prestaciones_sociales_cesantias`
- `auxilio_transporte`
- `parafiscales_sena_icbf_caja`
- `pila_cotizaciones`
- `presuncion_costos_independientes` *(the UGPP 532 case)*
- `aportes_seguridad_social_independientes`
- `dotacion`
- `salario_integral`
- `terminacion_contrato_indemnizacion`
- `liquidacion_laboral`
- `reforma_laboral_ley_2466`
- `trabajo_tiempo_parcial`
- `ugpp_fiscalizacion`

Source for the seed: existing chat-run logs (`logs/chat_verbose.jsonl`) that show what users ACTUALLY ask about per topic, plus the `subtopic-overrides` already captured in `topic_router_keywords.py:571` (`_SUBTOPIC_OVERRIDE_PATTERNS` already names GMF / impuesto_consumo / patrimonio_fiscal_renta / costos_deducciones_renta / laboral-colloquial as runtime sub-topic signals — that's a starter set).

**Schema add:**
- New table `sub_topic_taxonomy(parent_topic_key TEXT, sub_topic_key TEXT, label TEXT, aliases TEXT[], description TEXT, seeded_at TIMESTAMP, created_via TEXT CHECK (created_via IN ('seed', 'autogenerar_promotion')))`.
- `documents.sub_topic` column (TEXT NULL).
- `document_chunks.sub_topic` column (denormalized for retrieval boost speed).

### 2.b AUTOGENERAR prompt extension (PASO 4)

Extend the LLM prompt at `src/lia_graph/ingestion_classifier.py` (Phase 1 of v1) to add:

```
PASO 4: Dado que el tema principal es {resolved_topic_or_generated_label},
identifica el sub-tema operativo MAS especifico que aplica.
Compara contra esta lista de sub-temas existentes para {resolved_topic_or_generated_label}:
{sub_topic_list_with_labels}

Si tu sub-tema candidato es sinonimo o subconjunto de uno existente, mapea a ese sub-tema.
Si es genuinamente distinto de TODOS los existentes, declara "sub_tema_nuevo".

Anade al JSON:
"sub_topic_resolved_to_existing": "sub_topic_key_o_null",
"sub_topic_synonym_confidence": 0.0,
"sub_topic_is_new": false,
"sub_topic_suggested_key": "slug_si_es_nuevo_o_null",
"sub_topic_label": "etiqueta_legible_si_es_nuevo"
```

The list of sub-topics passed in `{sub_topic_list_with_labels}` comes from `sub_topic_taxonomy` filtered by `parent_topic_key = <resolved_or_generated_topic>`.

### 2.c Sub-topic confidence fusion

Mirror the topic-level fusion (`_fuse_autogenerar_confidence` from Lia_contadores `ingestion_classifier.py:460-493`):
- new sub-topic → 0.70
- synonym ≥ 0.80 → base 0.85 + 0.10 if N1 keyword agreement + 0.05 if synonym ≥ 0.90
- synonym 0.50-0.79 → 0.0 (forces manual review at sub-topic level)
- synonym < 0.50 → 0.0

A doc with topic-confidence 0.95 and sub-topic-confidence 0.60 should land with `sub_topic = NULL` and a `requires_subtopic_review = true` flag rather than commit a low-quality sub-topic.

### 2.d FalkorDB schema additions

New node type: `SubTopic` (key, label, parent_topic_key).
New edge types in `src/lia_graph/graph/schema.py`:
- `Topic -[HAS_SUBTOPIC]-> SubTopic`
- `Document -[HAS_SUBTOPIC]-> SubTopic` (denormalized for fast topic+sub-topic queries)
- `SubTopic -[SUBTOPIC_NEIGHBOR]-> SubTopic` (semantic neighbor edge populated post-embed by k-NN over sub-topic centroids — feeds relationship source #4 from `ingestfixv1.md` §3.5)

### 2.e Retrieval boost

Extend `pipeline_d/retriever_supabase.py` and `retriever_falkor.py`:
- When the planner detects a sub-topic intent (extend `planner_query_modes.py` to surface a `sub_topic_intent` field), boost chunks with `chunk.sub_topic = <intent>` by 1.5x in the hybrid_search RPC.
- When no sub-topic intent is detected, retrieval works as today (topic-only).

---

## 3. Pre-conditions before v2 starts

In order, all must be true:

1. ✅ **`ingestfixv1.md` Phase 8 complete** — drag-to-ingest UX working end-to-end with topic + synonym tagging in production.
2. ✅ **≥4 weeks of production runs** so we have real misclassification rates AND real chat-query distributions per topic.
3. ✅ **`logs/chat_verbose.jsonl` analysis run** that buckets the last N user queries by detected topic + extracts the most common semantic sub-clusters per topic. Output: a candidate sub-topic list per major topic.
4. ✅ **Curated seed list reviewed by a senior accountant** (the user) — sub-topics are operational mental models, not technical taxonomy. Without expert curation, this becomes garbage-in-garbage-out.
   - **Source:** `config/subtopic_taxonomy.json`, produced by the
     `docs/next/subtopic_generationv1.md` pipeline (Phases 1–6 shipped as
     `v2026-04-21-stv1`). The file carries a version stamp + evidence_count
     per entry; use whichever version the stakeholder last signed off on.
     The underlying audit trail is `artifacts/subtopic_decisions.jsonl`
     and the mining output is `artifacts/subtopic_proposals_<UTC>.json`.
5. ✅ **Decision F2 shipped** (`ingestfixv1.md` Phase 6.5 — per-doc accept/edit modal). Without a per-doc gate, low-confidence sub-topics auto-commit and pollute the corpus faster than topics did. F2 has to land first.

---

## 4. Phase ledger (sketch — to be filled when v2 starts)

| # | Phase | Pre-condition |
|---|---|---|
| 0 | Verify all 5 pre-conditions above | manual checklist |
| 1 | ~~Author curated sub-topic seed registry~~ → now consumed from `config/subtopic_taxonomy.json` (produced by `subtopic_generationv1.md`). Phase 1 becomes a validation step: assert the file exists, version-stamp matches stakeholder sign-off, ≥1 entry per parent_topic that has ≥5 docs. | `subtopic_generationv1.md` Phase 9 close-out complete |
| 2 | Schema migrations: `sub_topic_taxonomy` table + `documents.sub_topic` + `document_chunks.sub_topic` columns. The table seed comes from `config/subtopic_taxonomy.json`. | supabase migration |
| 3 | Extend `ingestion_classifier.py` with PASO 4 + sub-topic fusion + tests | parser changes |
| 4 | FalkorDB schema additions (SubTopic node + 3 edge types) + bridge updates | graph/schema.py + suin/bridge.py |
| 5 | Retrieval boost in `retriever_supabase.py` + `retriever_falkor.py` + planner intent extraction | pipeline_d updates |
| 6 | Backfill: re-classify the entire corpus for sub-topics (one-time pass, ~1246 LLM calls) | regrandfather pattern from v1 |
| 7 | UI: surface sub-topic in the intake preview row + Generaciones list + per-doc detail | extends ingestController |
| 8 | E2E verification: drop a UGPP doc, confirm `topic=laboral` AND `sub_topic=presuncion_costos_independientes` AND retrieval boost fires for a query about presuncion costos | manual |

---

## 5. Risks specific to sub-topics

| Risk | Mitigation |
|---|---|
| LLM mints inconsistent sub-topic slugs over time even with seed list | Pre-condition #4 + the synonym detection at sub-topic level (PASO 4 returns `sub_topic_resolved_to_existing` for established slugs). |
| Sub-topic registry sprawl (LLM keeps minting "new" sub-topics for slight variations) | Hard cap on `sub_topic_is_new=true` rate per generation; threshold > 5% of files in a single batch triggers a review block. |
| Sub-topic boost in retriever surfaces irrelevant chunks when planner intent detection is wrong | Boost factor configurable; A/B-style audit comparing answer quality with boost on/off for the first 100 production queries. |
| Sub-topic schema add forces a corpus_generations bump | Acceptable — sub-topics ARE a semantic enrichment that warrants its own generation marker. |

---

## 6. References

- `docs/next/ingestfixv1.md` §3.5 (relationship sources — sub-topics extend source #3 AUTOGENERAR)
- `docs/next/ingestfixv1.md` §3.6 (current AUTOGENERAR prompt — PASO 4 appended in v2)
- `docs/guide/orchestration.md` Lane 0
- `src/lia_graph/topic_router_keywords.py:571` `_SUBTOPIC_OVERRIDE_PATTERNS` (starter sub-topic seeds already in the runtime)
- `src/lia_graph/topic_taxonomy.py` (topic taxonomy infrastructure to extend with `parent_topic_key`)
- `src/lia_graph/graph/schema.py` (edge type registry to extend)

---

## 7. Open questions for v2 kickoff

1. Should sub-topic resolution happen in the SAME LLM call as topic resolution (one call, four PASO steps), or a SECOND LLM call after topic is locked in (sequential, lower per-call cost, higher latency)?
2. Should `Document -[HAS_SUBTOPIC]-> SubTopic` be the only document↔sub-topic edge, or should we also add per-chunk edges (`Chunk -[ABOUT_SUBTOPIC]-> SubTopic`) for finer-grained graph traversal? Trade-off: precision vs graph size.
3. When a sub-topic gets minted as new, should it be auto-promoted to the registry, or queued for accountant review first? F2 modal handles this for documents; sub-topics need their own gate.

---

*End of stub. To resume: read pre-conditions §3, verify all 5, then start Phase 0.*
