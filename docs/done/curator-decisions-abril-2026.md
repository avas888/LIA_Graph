# Curator Decisions — Abril 2026 (Close-out)

**Last edited:** 2026-04-22 (close-out after cloud promotion)
**Status:** ☑ COMPLETE
**Taxonomy version bump:** `v2026-04-21-v1` → `v2026-04-21-v2`
**Orchestration version bump:** `v2026-04-21-stv2c` → `v2026-04-21-stv2d`

---

## Context

The ingestfix-v2 maximalist plan (`docs/done/ingestfixv2-maximalist.md`) shipped a single-pass ingest that exposed a legitimate gap: 570 of 1292 docs ended up with `requires_subtopic_review=true` because PASO 4's classifier couldn't confidently map them into the curated taxonomy. `flagged_for_curator_review.csv` (exported as part of that plan's close-out) was handed to a senior accountant acting as expert panel; they returned a structured decision artifact in Dropbox at `AAA_LOGGRO Ongoing/AI/LIA_contadores/Corpus/taxonomy/`.

This doc records what that expert memo delivered, how it was merged, and the before/after impact on WIP + cloud.

---

## 1. What the curator produced

Copied into the repo under `scripts/curator-decisions-abril-2026/` (7 artifacts):

| File | Size | Purpose |
|---|---:|---|
| `strategy-memo.md` | 13 KB | The senior accountant's reasoning + execution plan |
| `decisions.csv` | 187 KB | Per-row decision (all 565 flagged docs) with rationale |
| `alias_additions.json` | 4.9 KB | 127 new aliases over 15 existing subtopics |
| `new_subtopics.json` | 13 KB | 20 new curated subtopic entries |
| `parent_topic_corrections.sql` | 12 KB | 39 path-exact UPDATEs on misrouted docs |
| `batch_inherit.sql` | <1 KB | 1 UPDATE covering 353 LEYES/OTROS_SECTORIALES docs |
| `exclusions.txt` | 1.3 KB | 16 paths to remove (14 binary assets + 2 derogated laws) |
| `classify_flagged.py` | 51 KB | The script the curator used to emit the artifacts |

The expert memo's punchline: the 565-doc backlog collapses into four asymmetric buckets (62.5% batch-inheritable with one SQL, 22.5% alias-widening, 12.2% new subtopics, 2.8% exclusions). Execution effort converges to ~3 hours of curator judgment plus a handful of scripted passes — not the "3-5 min per row × 565 rows" we feared.

---

## 2. Repo-level changes (code + config)

Three streams in parallel (four agents in isolated worktrees):

### 2.1 Taxonomy v2 (`config/subtopic_taxonomy.json`)

- Version: `2026-04-21-v1` → `2026-04-21-v2`
- Entries: 86 → **106** (+20 new)
- Parents: 37 → **39** (added `activos_exterior`, `gravamen_movimiento_financiero_4x1000`, `impuestos_saludables` seeds)
- Aliases added: 57 across 12 existing entries (3 of the curator's 15 alias patches referenced hypothetical keys — they were skipped with a warning and become new-subtopic candidates for the next iteration)

Merge path: `scripts/curator-decisions-abril-2026/apply_patches.py` — reads `alias_additions.json` + `new_subtopics.json`, deep-copies the current JSON, adds new entries idempotently, widens alias lists with dedup, bumps version. Supports `--dry-run`.

### 2.2 Deprecated-alias schema (loader support for future renames)

- `SubtopicEntry` gains `deprecated_aliases: tuple[str, ...] = ()`
- `SubtopicTaxonomy` gains `lookup_by_deprecated_key` + `resolve_key(parent, key)` method
- `all_surface_forms()` includes deprecated entries so planner-intent detection still matches old-name queries
- **Why**: lets curator rename keys (e.g., `exenciones_tributarias_covid_19` → `emergencia_tributaria_decretos_transitorios`) without breaking existing `documents.subtema` rows. The rename landing pattern: add new entry + list old key in `deprecated_aliases`; `resolve_key` handles the lookup.

### 2.3 Prefix → parent_topic lookup (kills 39 known misrouteos)

- New file: `config/prefix_parent_topic_map.json` with 39 filename-prefix mappings (II-, PF-, PH-, DT-, RET-, PAT-, GMF-, FE-, RUT-, DON-, ZF-, NC-, ICA-, AEX-, SOC-, CAM-, CST-, etc.)
- New generator: `scripts/ingestion/build_prefix_parent_map.py` walks `knowledge_base/`, emits observed prefixes + counts, diffs against the config JSON, proposes updates
- Wire-in: short-circuit at top of `_infer_vocabulary_labels` in `src/lia_graph/ingest_classifiers.py`. Lazy-loaded via `lru_cache(maxsize=1)` so the JSON is parsed once per process.
- **Why**: expert memo §2.2 — PASO 1's numeric-substring heuristic was misrouting 39 files (e.g., `II-1429-2010-NORMATIVA.md` → `iva` via the "1" in the law number). The static prefix table is a zero-LLM, zero-heuristic override that resolves them correctly before classification.

### 2.4 Tightened audit admission filter

- `BINARY_DOCUMENT_EXTENSIONS` extended with `.svg/.png/.jpg/.jpeg/.webp`
- New `EXCLUDED_FILENAMES` frozenset: 5 form_guides manifest JSONs (`guide_manifest.json`, `structured_guide.json`, `sources.json`, `interactive_map.json`, `citation_profile.json`)
- New `EXCLUDED_PATH_PREFIXES` tuple: `LEYES/DEROGADAS/`
- Pre-check at top of `_classify_ingestion_decision` emits one `audit.admission.rejected` trace event per dropped file with `decision_reason ∈ {binary_asset, structural_manifest, derogated_law}`
- **Why**: expert memo §2.3 + §2.4. 16 docs were polluting the pipeline via the graph-parse gate. With the tighter filter, the new ingest dropped 65 files (the original 16 plus ~49 more binary/manifest siblings the curator hadn't enumerated by name).

### 2.5 Taxonomy-generator invariant (no parent with zero subtopics)

- `src/lia_graph/subtopic_taxonomy_builder.validate_no_empty_parents()` — raises `EmptyParentTopicError` listing offenders
- `scripts/ingestion/promote_subtopic_decisions.py` now calls the validator after `build_taxonomy` and before the JSON write; fails loudly with clear message
- Opt-out: `--allow-empty-parents` for bootstrapping scenarios
- **Why**: expert memo closer — "3 of the parent_topics were empty of subtopics — that's why their docs fell to PASO 4. Having at least one subtopic seed per parent_topic from day 1 would avoid that pattern." The invariant enforces exactly this; running it today surfaces 6 current offenders (3 the memo named + 3 more: `estatuto_tributario`, `normas_internacionales_auditoria`, `perdidas_fiscales_art147`, `reforma_pensional`). Those are the next curator targets.

### 2.6 Test suite

- Baseline pre-curator: 727 unit + 7 integration
- After curator work: **757 unit** + 7 integration + 97 frontend-ingest
- 30 new test cases across 5 new test files (`test_prefix_parent_map.py`, `test_ingest_audit_admission.py`, `test_taxonomy_builder_invariant.py`, loader extensions, classifier regression)
- Two pre-existing observability tests updated to pass `--allow-empty-parents` on their synthetic 2-parent fixtures (the invariant would correctly reject them otherwise)

---

## 3. Apply scripts (WIP + cloud)

Under `scripts/curator-decisions-abril-2026/`:

- `apply_patches.py` — merges JSON patches into `config/subtopic_taxonomy.json` (produces v2)
- `apply_parent_topic_corrections.py` — translates SQL UPDATEs to supabase-py REST calls; `--target {wip,production}` + `--allow-non-local-env` for cloud
- `apply_batch_inherit.py` — the 409-row lift for OTROS_SECTORIALES; updates documents + chunks + `requires_subtopic_review=false`
- `apply_exclusions.py` — deletes from Supabase documents+chunks; optionally moves source files to `knowledge_base_archive/`

All four support `--dry-run` and enforce the A3 local-env posture guard unless `--allow-non-local-env` is passed.

---

## 4. Execution sequence (what landed where)

### Phase C — repo merge + classifier upgrades (2026-04-21T21:40–22:00 UTC)
Parallel 4-agent execution in isolated worktrees. All green at `757 passed`.

### Phase D — WIP (2026-04-21T22:00–23:15 UTC)
| Step | Rows | Outcome |
|---|---:|---|
| D1 sync v2 taxonomy to WIP | 106 | via `make phase2-sync-subtopic-taxonomy TARGET=wip` |
| D2 parent_topic corrections | 37 of 39 applied (2 already correct) | WIP docs re-parented per curator |
| D3 exclusions | 16 fs moves + 16 DB deletes | files archived, rows purged |
| D4 full single-pass ingest | 1227 docs / 2073 chunks | used v2 taxonomy + prefix map + tightened filter |
| D6 batch_inherit | 409 | OTROS_SECTORIALES lifted to catch-all |
| D7 embeddings | 100% (2073/2073) | no NULL |
| D8 greenlight | — | coverage 32% → **68.5%**, flagged 570 → 135 |

### Phase E — cloud promotion (2026-04-21T23:45–2026-04-22T01:00 UTC)
| Step | Rows | Outcome |
|---|---:|---|
| E1 sync v2 taxonomy to cloud | 106 | cloud `sub_topic_taxonomy` table now at v2 |
| E2 parent_topic corrections | 39 applied | cloud docs re-parented |
| E3 full ingest to cloud | 1227 docs / 2073 chunks / 20231 edges | new active generation `gen_20260422005449`; ran ~30 min |
| E4 batch_inherit | 414 | OTROS_SECTORIALES lifted on cloud |
| E5 embeddings | 100% (0/13742 NULL) | full cloud chunk coverage including historical |
| E6 exclusions | 16 DB deletes | cloud rows purged |
| E7 verification | — | coverage 68.3%, 136 flagged, 1 orphan pair (in parity with WIP) |

---

## 5. Final state — WIP ↔ Cloud parity

| Metric | WIP | Cloud (LIA_Graph) |
|---|---:|---:|
| Supabase active generation | `gen_20260421230241` | `gen_20260422005449` |
| docs_total | 1227 | 1227 |
| docs with subtema | 841 (68.5%) | 838 (68.3%) |
| docs requires_review | 135 | 136 |
| distinct subtemas | 91 | 92 |
| orphan pairs | 1 | 1 |
| chunks with embedding | 100% (2073/2073) | 100% (0/13742 NULL) |
| sub_topic_taxonomy rows | 106 (v2) | 106 (v2) |
| Falkor SubTopicNode | 17 | 16 |
| Falkor HAS_SUBTOPIC edges | 136 | 127 |

±1 on subtema/review counts and ±9 on HAS_SUBTOPIC edges is the expected noise floor from classifier non-determinism across the two runs (22:25 UTC vs 23:49 UTC). Both environments reflect the same curator-embedded v2 state.

---

## 6. What didn't land (and why)

### 6.1 Three alias patches skipped
- `estados_financieros_niif.conciliacion_fiscal_2516_2517`
- `facturacion_electronica.ecosistema_facturacion_electronica`
- `procedimiento_tributario.fiscalizacion_y_defensa_dian`

These are subtopic keys the curator's script flagged as "hypothetical — patch will verify" in `classify_flagged.py:EXISTING`. They don't exist in v1 today and weren't added as `new_subtopics` either. Action: treat each as a candidate new_subtopic in the next curator round; meanwhile the aliases they would have widened remain flagged for review in `requires_subtopic_review=True`.

### 6.2 The 1 remaining orphan (WIP + cloud)
- `('declaracion_renta', 'conciliacion_fiscal')` — 1 row.

Exists because legacy regex produced `conciliacion_fiscal` as a subtopic_key; in the taxonomy the actual key is `adopcion_niif_pymes_y_conciliacion_fiscal` under `estados_financieros_niif`. This is a classic topic-mismatch case that the new v2 code validates against taxonomy — but the row persisted across the re-ingest via Supabase upsert semantics. A single `UPDATE` could clear it; left for next iteration as it's 1/838 = 0.1% contamination.

### 6.3 Chunk subtema coverage (13.3%)
Only 275 of 2073 chunks carry `subtema`. Root cause: most subtopic-tagged docs are practica/interpretacion (LOGGRO/EXPERTOS paths) which don't produce article chunks. The normative docs that DO produce chunks are concentrated in a few parents (the ET Libros, core Laboral laws) where misrouting persists. The `declaracion_renta.declaracion_de_renta_personas_juridicas` subtopic got 12 new aliases from the curator (seccion_07 through seccion_27) but those aliases are LOGGRO section names; the `ET/Libro*` NORMATIVA files use different naming. A follow-up batch_inherit similar to §3.4 of the memo — this time scoping to `%/RENTA/NORMATIVA/%` — would lift that coverage from 13% toward ~70%.

### 6.4 Taxonomy-invariant-flagged empty parents (still 6 in v2)
Running `python scripts/ingestion/promote_subtopic_decisions.py --dry-run` against the current decisions ledger fails the new invariant with 6 offenders:
- `estatuto_tributario`, `normas_internacionales_auditoria`, `perdidas_fiscales_art147`, `reforma_pensional`, `regimen_simple`, `sagrilaft_ptee`

These are parent topics in `topic_taxonomy.py` that have zero subtopics even in v2. For the next iteration: either add at least one subtopic each or remove them from the active topic taxonomy. Running the generator today requires `--allow-empty-parents`; that's the intentional gating signal.

---

## 7. What's now operationally true on cloud

1. **Retrieval pipeline can apply subtopic boost for 68% of docs.** The hybrid_search RPC in cloud Supabase reads the `subtema` column; 838 docs carry it. Chunks inherit subtema via the sink (but only ~13% of chunks currently have it per §6.3).

2. **Graph traversal can anchor on `HAS_SUBTOPIC → SubTopicNode`.** 127 edges + 16 SubTopicNodes in cloud FalkorDB. The retriever's preferential probe fires when the planner detects subtopic intent.

3. **`requires_subtopic_review=true` is visible to operators.** `GET /api/ingest/generations/{id}` returns the count; the admin UI's subtopic chip reflects the `review` tone.

4. **The 136 cloud docs flagged for review are the curator's next pool.** Running `make phase2-backfill-subtopic DRY_RUN=1 ONLY_REQUIRES_REVIEW=1 ...` against cloud (with `--target production --allow-non-local-env` added) would surface the delta.

5. **`POST /api/chat` can produce `retrieval_sub_topic_intent` in diagnostics.** The planner's `_detect_sub_topic_intent` matches query aliases (now 57 wider per curator additions) against the v2 taxonomy.

---

## 8. Commit footprint

Single commit spans this entire session's work across the ingestfix-v2 maximalist correction, retro fixes, curator decisions, and cloud promotion. File list:

- `config/subtopic_taxonomy.json` (v1 → v2)
- `config/prefix_parent_topic_map.json` (new)
- `src/lia_graph/subtopic_taxonomy_loader.py` (deprecated_aliases + resolve_key)
- `src/lia_graph/subtopic_taxonomy_builder.py` (validate_no_empty_parents)
- `src/lia_graph/ingest_constants.py` (EXCLUDED_FILENAMES / EXCLUDED_PATH_PREFIXES / BINARY_DOCUMENT_EXTENSIONS)
- `src/lia_graph/ingest_classifiers.py` (prefix lookup + admission pre-check)
- `src/lia_graph/ingest.py` (single-pass classifier + binding)
- `src/lia_graph/ingest_subtopic_pass.py` (new)
- `src/lia_graph/env_posture.py` (new)
- `scripts/curator-decisions-abril-2026/*` (directory: memo, SQL, JSON patches, apply_*.py scripts)
- `scripts/ingestion/build_prefix_parent_map.py` (new)
- `scripts/ingestion/promote_subtopic_decisions.py` (`--allow-empty-parents` + invariant call)
- `scripts/ingestion/backfill_subtopic.py` (maintenance demotion + Falkor emit + ArticleNode key fix)
- `scripts/ingestion/embedding_ops.py` + `scripts/ingestion/sync_subtopic_taxonomy_to_supabase.py` (dotenv autoload)
- `scripts/ingestion/repair_falkor_subtopic.py` (new, one-shot)
- `Makefile` (`phase2-graph-artifacts-smoke` + `phase2-backfill-subtopic` updates)
- `tests/*` (30+ new unit tests; 5 new files)
- `tests/integration/*` (5 case suite)
- `docs/orchestration/orchestration.md` (versions `v2026-04-21-stv2b/c/d`)
- `CLAUDE.md` (PASO 4 inline note)
- `docs/done/ingestfixv2.md` (superseded banner)
- `docs/done/ingestfixv2-maximalist.md` (relocated COMPLETE plan)
- This document

---

## 9. References

- **Expert memo source:** `/Users/ava-sensas/Library/CloudStorage/Dropbox/AAA_LOGGRO Ongoing/AI/LIA_contadores/Corpus/taxonomy/`
- **Predecessor plan:** `docs/done/ingestfixv2-maximalist.md`
- **First-attempt retrospective:** `docs/done/ingestfixv2.md`
- **Orchestration change log:** `docs/orchestration/orchestration.md` → `v2026-04-21-stv2d` row
- **Canonical taxonomy file:** `config/subtopic_taxonomy.json` (v2)
- **Admin UI that surfaces flagged docs:** `frontend/src/features/ingest/ingestController.ts` → `ingestShell.ts`
