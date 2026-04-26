# Coherence-gate calibration diagnostic — thin-corpus topic findings (2026-04-26)

> **Trigger.** v5 §6.3 verification round on 2026-04-26 surfaced a real-user failure: questions about firmeza de declaraciones land on `effective_topic=firmeza_declaraciones` correctly, but the v6 evidence-coherence gate refuses with `pipeline_d_coherence_primary_off_topic` because the canonical articles (Art. 714, 689-3, …) are tagged with adjacent topics. Operator opened v5 §1 calibration diagnostic to measure how widespread this is.

## Phase 1 — thin-corpus topic inventory (1 hour)

For each of 89 registered topics in `config/topic_taxonomy.json`, counted (a) Supabase chunks tagged with the topic, (b) Falkor `:ArticleNode`s whose `source_path` belongs to a doc with that topic.

**Classes (thresholds: chunks ≥ 10 + native_articles < 5 → "thin-corpus"):**

| Class | Count | Reading |
|---|---:|---|
| healthy (≥ 5 native articles) | 60 | the bulk; retrieval works |
| **thin-corpus** | **12** | **the FIRMEZA-class pattern** |
| low-chunk (< 10 chunks) | 6 | not at retrieval risk |
| empty (0 chunks) | 11 | unreachable; corpus gap |

**The 12 thin-corpus topics:**

| Topic | Chunks | Native articles |
|---|---:|---:|
| precios_de_transferencia | 42 | 4 |
| impuesto_patrimonio_personas_naturales | 38 | 4 |
| regimen_cambiario | 34 | 4 |
| perdidas_fiscales_art147 | 32 | 3 |
| beneficio_auditoria | 22 | 2 |
| normas_internacionales_auditoria | 22 | 3 |
| conciliacion_fiscal | 21 | 2 |
| impuestos_saludables | 21 | 2 |
| sector_telecomunicaciones | 21 | 2 |
| dividendos_y_distribucion_utilidades | 17 | 2 |
| parafiscales_seguridad_social | 15 | 1 |
| sector_economia | 12 | 2 |

These are the 12 surfaces where a user's question can land on the right topic but the planner pulls cross-topic primary articles → coherence gate refuses.

## Phase 2 — cross-topic dependency (2 hours)

For each thin-corpus topic, sampled up to 100 chunks, extracted Art. N references via the `linker.py` regex family, and looked up each referenced article's owner topic in Falkor (via `:ArticleNode.source_path → documents.relative_path → documents.topic`).

**Universal finding: 12/12 thin-corpus topics show 100% cross-topic dependency.** Every single thin-corpus topic's primary article references are owned by OTHER topics. None has a canonical article of its own.

**Aggregate cross-topic owners (top 10 across all 12 thin-corpus topics, ranked by mention count):**

| Owner topic | Mentions | % of total |
|---|---:|---:|
| declaracion_renta | 326 | ~40% |
| firmeza_declaraciones | 85 | ~10% |
| procedimiento_tributario | 78 | ~10% |
| cambiario | 62 | ~8% |
| patrimonio_fiscal_renta | 45 | ~6% |
| ingresos_fiscales_renta | 38 | ~5% |
| renta_liquida_gravable | 37 | ~5% |
| regimen_simple | 25 | ~3% |
| laboral | 22 | ~3% |
| rentas_exentas | 19 | ~2% |

**16 distinct cross-topic owners total**, but **top 5 own ~74% of all cross-topic references** (Pareto). The strict-threshold script verdict is "distributed" (16 > 15), but the empirical shape is concentrated enough for a bounded curation effort.

**Top referenced articles per thin-corpus topic (sample):**

| Thin-corpus topic | Top Art. N (mentions) | Owner topic |
|---|---|---|
| beneficio_auditoria | Art. 689-3 (29) | firmeza_declaraciones |
| beneficio_auditoria | Art. 714 (5) | firmeza_declaraciones |
| dividendos_y_distribucion_utilidades | Art. 49 (31) | ingresos_fiscales_renta |
| dividendos_y_distribucion_utilidades | Art. 242, 245 (24) | declaracion_renta |
| sector_telecomunicaciones | Art. 240 (16) | declaracion_renta |
| normas_internacionales_auditoria | Art. 207 (14) | rentas_exentas |
| conciliacion_fiscal | Art. 651, 655, 772-1 (35) | procedimiento_tributario |

The pattern is structural: the ET (and the corpus modeling around it) has umbrella topics like `declaracion_renta` that own most articles, while specific-case topics (beneficio, dividendos, conciliación) reference those same articles from a different angle. Each article naturally lives in MULTIPLE topical contexts — the corpus model only allows ONE.

## The FIRMEZA anomaly — chunk-level cross-topic mix

A separate finding from Phase 1+2: `firmeza_declaraciones` is itself **healthy** in the thin-corpus measurement (12 native articles after the 2026-04-26 ingest of FIR-N02 collapsed Art. 714, 689-3, etc. onto Falkor nodes whose source_path now points at FIR-N02's path). Yet the chat STILL refuses with `pipeline_d_coherence_primary_off_topic` for firmeza questions.

Direct probe confirmed: in Falkor, Art. 714 has `source_path = '...BRECHAS-SEMANA4.../NORMATIVA_FIR-N02...md'` and that path's `documents.topic = firmeza_declaraciones`. **The article-level mapping IS correct.**

So the FIRMEZA refusal isn't an article-owner-topic problem; it's something else — most likely **chunk-level cross-topic mix** in the hybrid_search pull. Old chunks from `09_Libro1_T1_Caps8a11.md` (topic=`declaracion_renta`) that cover Art. 714 still exist in Supabase and surface in semantic search alongside the new firmeza chunks. The planner sees a mixed evidence set and the gate refuses.

Two implications:
1. The thin-corpus pattern (Phase 1+2) is necessary but not sufficient — even healthy topics can refuse when pre-existing chunks dilute the evidence.
2. The fix space is broader than a single ArticleNode metadata change.

## Decision (Gate-3 binding)

**HYBRID — multi-topic metadata + coherence-gate refinement.**

The strict threshold reading is "distributed" (16 cross-topic owners > 15), suggesting recalibration. But the empirical shape (top 5 own 74%) plus the FIRMEZA anomaly (healthy topic still refusing) points to two complementary fixes:

### Fix A — Multi-topic ArticleNode metadata (structural)

Add `secondary_topics: text[]` to `:ArticleNode` schema. Each canonical article can belong to its primary topic AND list secondary topics it serves.

- Curation pass: SME maps ~30-50 high-traffic articles to their secondary topics. Bounded by the 12 thin-corpus topics × top 5-8 articles each.
- Coherence-gate code: when comparing query topic to primary article topic, accept if `query_topic ∈ {primary.topic} ∪ primary.secondary_topics`.
- Effort: 3-5 days (schema migration + loader writes + coherence gate edit + SME curation + verification).

### Fix B — Chunk-deduplication or topic-precedence on hybrid_search (FIRMEZA case)

When new chunks arrive for an article that already has chunks under a different topic, decide which set takes precedence in retrieval. Options:
- Prefer chunks tagged with the user's effective_topic.
- Soft-deprecate older-topic chunks for the same article when a more-specific topic now owns the article.
- Add a topic-precedence config that says "for articles in topic firmeza_declaraciones, prefer firmeza_declaraciones chunks over declaracion_renta chunks".

Effort: 1-2 days investigation + ~2 days implementation depending on chosen path.

### What this rules OUT

- Pure curation without metadata changes (would be unbounded — 16 cross-topic owners spanning the ET).
- Lowering the coherence-gate threshold (`feedback_thresholds_no_lower`).
- Disabling cross-topic refusal entirely (re-introduces Q1-class contamination per next_v3 §13).

## Numbers for the scoreboard

- 89 registered topics
- 12 thin-corpus (chunks ≥ 10, native_articles < 5) → **13.5%** of all topics at structural retrieval risk
- 78 topics with ≥ 1 chunks → 12 thin-corpus = **15.4% of in-use topics** at risk
- 100% of thin-corpus topics show cross-topic dependency
- Top-5 cross-topic owners cover 74% of mentions
- 16 distinct cross-topic owners across all 12 thin-corpus topics

## v5 §1.A implementation — lessons (same day, 2026-04-26)

After the diagnostic settled, §1.A landed the structural code change: multi-topic ArticleNode metadata + coherence-gate update. Lessons extracted that generalize beyond this specific fix — saved here so a future engineer reading the diagnostic doesn't have to relearn them.

### L1 — Multi-topic metadata at the node level (not chunk, not doc)

When the corpus has umbrella topics (`declaracion_renta`) and specific-context topics (`beneficio_auditoria`) that legitimately reference the same article, single-topic-per-node fails. Tagging at the document level over-broadens (whole doc tagged with N topics); at the chunk level under-targets (chunks vary wildly per article). The right granularity is the **article node itself** — same level the coherence gate uses to compare.

### L2 — Config-file-driven curation beats schema migration

For SME-owned curation surfaces that change weekly, a `config/article_secondary_topics.json` file beats a Supabase column or Falkor schema field:

- Reviewable in git diff / PR (no schema-replay).
- SME edits without engineer help.
- Tests can pin the contract directly (e.g., "every entry's topic must be a valid taxonomy key").
- No DB migration needed; the loader picks up the config on next ingest.

The same lesson powered the v3 path-veto rule pattern (`path-veto-rule-based-classifier-correction.md`). When you find yourself thinking "let me add a column to ArticleNode for this curation," consider a JSON config first.

### L3 — Validate every config value against the canonical taxonomy

Operator's binding rule (2026-04-26): "todo mapee a nuestra taxonomy base principal". Without validation, typos in a curation file silently match nothing OR worse, accidentally route to a bogus topic. Two layers of defense:

- **Runtime drop + warn**: `_load_lookup` in `ingestion/article_secondary_topics.py` drops unknown topic keys with a stderr warning so the typo is visible during ingest.
- **Test-time pin**: `tests/test_article_secondary_topics.py::test_default_seed_topics_all_in_canonical_taxonomy` asserts the committed config validates. Mirrors the existing `test_path_veto_all_targets_are_valid_taxonomy_keys` — same discipline, different config surface.

### L4 — Short-circuit BEFORE lexical scoring, not after

`detect_topic_misalignment` originally only used lexical scoring on the article text. Adding the `secondary_topics` check BEFORE the lexical path (rather than as a post-filter) gives:

- One curated entry beats any number of lexical false-positives.
- Pre-§1.A behavior preserved for un-curated articles (Q1 contamination guard intact for the long tail).
- The fix is bounded — only SME-approved entries get the override.

### L5 — Uniformise return-value contracts when adding branches

`detect_topic_misalignment` had 5 return paths pre-§1.A; only 3 set a `reason` key. Adding `secondary_topic_match` would have made it 4-of-6. I added `reason` to the lexical paths too (`lexical_aligned` / `lexical_misaligned`), making it always-present. Saves callers from defensive `.get("reason")` everywhere and gives observability tools a clean histogram of branch frequencies. Generalizes: when adding a new branch to a multi-branch return contract, walk the existing branches and bring missing fields up to parity.

### L6 — SME-validated mappings already exist; reuse them

The §1.A seed config could have been speculative. But `docs/aa_next/taxonomy_v2_expert_brief.md §5.2` and `docs/aa_next/taxonomy_v2_sme_response.md §1.4` already had **explicit SME-validated `allowed_et_articles` per empty topic slot** (e.g., line 769 of the SME response: `firmeza_declaraciones.allowed_et_articles = ["705", "705-1", "706", "714", "147", "689-3", "260-5"]`). Future expansion of `article_secondary_topics.json` should pull from those documented mappings before asking the SME again. Avoids re-litigation of decisions that were already made.

## Cross-references

- Plan: `docs/aa_next/next_v5.md §1` (calibration diagnostic — this fulfills its measurement gate).
- Diagnostic scripts (read-only): `scripts/diag_thin_corpus_topics.py` (Phase 1), `scripts/diag_thin_corpus_xref.py` (Phase 2).
- JSON output: `artifacts/diag_thin_corpus_xref.json` (full per-topic detail).
- The §6.3 fix that surfaced this: `docs/learnings/ingestion/falkor-edge-undercount-and-resultset-cap-2026-04-26.md`.
- §1.A code surface: `src/lia_graph/ingestion/article_secondary_topics.py` (lookup), `src/lia_graph/graph/schema.py` (schema field), `src/lia_graph/ingestion/loader.py` (write to Falkor), `src/lia_graph/pipeline_d/retriever_falkor.py` (read from Falkor), `src/lia_graph/pipeline_d/topic_safety.py` (gate consumes it).
- §1.A config: `config/article_secondary_topics.json`.
- §1.A tests: `tests/test_article_secondary_topics.py`, `tests/test_topic_safety_secondary_topics.py`.
- SME-validated allowed-articles mappings (curation source-of-truth): `docs/aa_next/taxonomy_v2_expert_brief.md §5.2` + `docs/aa_next/taxonomy_v2_sme_response.md §1.4`.
- Sibling pattern (config-driven LLM/lexical override): `docs/learnings/ingestion/path-veto-rule-based-classifier-correction.md`.
- Related: `docs/aa_next/done/next_v3.md §13` (coherence-gate Q1 contamination guard — the right behavior we don't want to break).
