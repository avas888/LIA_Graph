# fix_v19 external peer review — RAG architect (2026-05-15 evening)

> Standalone artifact preserving the external peer review of `fix_v19_may.md`. Run via Agent tool, reviewer profile = "external RAG architecture expert." Raw observations — incorporation decisions live in `fix_v19_may.md`'s revision history (see §0 of that doc for the v0 → v1 delta).

---

## Bottom-line tl;dr (reviewer's)

- The plan invents a brand-new key format (`et:64`, `cst:64`) while the repo already has a canonical norm-id grammar in production (`et.art.64`, `ley.50.1990.art.6`, with `.par.` / `.num.` / `.inciso.` / `.lit.` sub-units), enforced by `src/lia_graph/canon.py` and used by the `public.norms` catalog (`norm_id text PRIMARY KEY`) and `:Norm` Falkor nodes.
- Compound keys are the right idea; choosing a colon-separated format that ignores the existing grammar is a blocking design error.

---

## Observations — by severity

### 🚨 Blocking (must address before Fase 2)

#### 1. Compound-key format collides with existing canonical grammar

| Existing artifact | Format in use | Example |
|---|---|---|
| `public.norms.norm_id` (PK) | dotted grammar | `et.art.64`, `et.art.64.par.1` |
| `:Norm` Falkor node `norm_id` | same grammar | `ley.50.1990.art.6` |
| `canon.canonicalize()` | dotted, slots `.art.` / `.par.` / `.num.` / `.inciso.` / `.lit.` | `src/lia_graph/canon.py:58` |
| `topic_norm_allowlist.json` | `art:<number>` prefix style | `art:147`, `art:903` |
| `:ArticleNode.article_number` (Falkor) | bare numeric string | `"64"`, `"771-5"`, `"124-2"` |
| v19 proposed (v0) | `<codigo>:<numero>` | `cst:64`, `et:64` |

- Repo has THREE keying conventions in flight (`norm_id` dotted, `art:NNN` allowlist, bare `article_number`). v19 adds a fourth without reconciling.
- Canonical answer: **align ArticleNode with `norm_id`** (`et.art.64`), not invent `cst:64`. Benefits:
  - Reuses `canon.canonicalize()` for parsing user mentions → article keys (free).
  - Lets `:ArticleNode` and `:Norm` MERGE on the same key — collapses duplicate-node problem.
  - Works for sub-units the colon form can't express (paragráfos, numerales).
  - Works for `cst 127-132` composite + Ley 1819-renumbered articles via existing grammar slots.

#### 2. The `:` separator breaks on the very examples the plan must support

- §4.1 fixture explicitly cites **CST arts. 127–132** (composite range). `cst:127-132` is parseable, but compound articles like `771-5`, `124-2`, `108-5`, `689-3` already appear in `case_bullets/*.py` as bare strings. Mixing range hyphens, sub-article hyphens, and code-segment colon → round-trip parsing fragile.
- Existing canonical grammar already disambiguates: `et.art.124.par.2` vs `et.art.124-2` is unambiguous, and `parent_norm_id()` in `canon.py:102` walks back through sub-units cleanly.

#### 3. "Why aren't CST articles ingested today?" isn't actually diagnosed

- Plan asserts "ingestion didn't promote them" without diagnosis.
- Reviewer dug into `ingestion/loader.py` + `ingestion/parser.py:213` (`parse_articles`). Parser walks markdown for `Artículo NNN` headings. Eligibility gate (`_is_article_node_eligible` `loader.py:23-40`) requires `heading + body + status` only. **Nothing excludes labor sources.**
- Likely real root cause: CST/Ley 50/Ley 789 markdown files in `knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/` may not have `Artículo NNN` headings in the regex shape `parser.py` expects — may use `ARTÍCULO` (caps), `Art.`, or numbered list shapes — so parser falls through to `_whole_document_fallback`, emits ONE prose-only `whole::source` ArticleNode per doc.
- That explains the 61-docs-but-only-41-nodes gap: most labor docs collapse to prose-only fallbacks instead of per-article nodes.
- **If that's the diagnosis, Fase 3 needs a parser-regex fix, not just a re-ingest.** Plan doesn't mention this; at risk of running a clean re-ingest and getting the same 41 ArticleNodes back.
- Recommendation: 1 hour before greenlighting Fase 2, actually parse one CST markdown file through `parser.parse_articles()` and count the output. If it returns 1 prose-only article instead of ~200, the parser is the bug, not the schema.

#### 4. TEMA-edge seeding ALREADY EXISTS in code; audit didn't ask why it stopped firing

- `src/lia_graph/ingestion/loader.py:673-710` defines `_build_tema_edges` emitting `(ArticleNode)-[:TEMA]->(TopicNode)` from `article_topics` map. Wired through `delta_runtime.py:556-568`.
- Comments reference "1,943 TEMA edges v4 populated" (visible in `retriever_falkor.py:102`).
- So the 0-TEMA-edges audit finding is "feature regressed," not "feature missing." Possible causes:
  - `article_topics` map being passed empty by `delta_runtime` path (classifier output not flowing through).
  - TEMA cleanup pass at `loader.py:487-490` DELETEs outbound TEMA edges before re-MERGE; if re-MERGE misconfigured, cleanup leaves graph at zero.
  - Recent fix (v17 or v18) inadvertently disabled the call site.
- **Fase 5 risks repeating the mistake** by hand-curating `config/topic_tema_anchors.json` instead of fixing ingestion-time emission. Hand-curated JSON is brittle (memory `subtopic_aliases_breadth` says wide alias lists are intentional retrieval fuel — TEMA edges have similar shape, should be derived not hand-typed).
- Recommendation: before adding a new config file, run `git log -- src/lia_graph/ingestion/loader.py | grep -i tema` and `git log -p -S "TEMA edge"` to find when 1,943 edges disappeared. Recover via fix, not via re-curation.

### ⚠ Concerns (should address; can defer if documented)

#### 5. Fase 4 LOC scope undercounted

- Plan says "≥ 40 case_bullets files." Actual count: **62 hits across 31 files** (`grep -rn anchor_articles src/lia_graph/pipeline_d/case_bullets/`).
- Plus: `topic_norm_allowlist.json` uses `art:147` prefix shape — parallel migration needed.
- Plus: `_citation_allowlist.py` consumes `art:` prefixes.
- Plus: `config/subtopic_taxonomy.json`, `comparative_regime_pairs.json`.
- Plus: tests with hard-coded article keys (v18 baseline 301 tests likely include some).
- Plus: `retriever_falkor.py:299, 350` MATCH on `a.article_number` — needs codigo filter.
- 1-day estimate looks light. Suggest 1.5-2 days.

#### 6. Conflict resolver wiring is wrong AFTER v19

- `orchestrator.py:1099-1167`:
  1. polish runs
  2. if rejected, `polish_rejected_fallback` replaces `answer` with re-assembled template
  3. citation allowlist runs on `evidence.citations` (NOT on answer markdown)
  4. conflict resolver runs **after** polish, takes `evidence=evidence`
- §4.1 trace shows `polish_mode=rejected, skip_reason=invented_uvt_ranges`. In that path, conflict resolver runs on **fallback markdown** (line 1124 `answer = filtered_fallback`), but A1 relies on `evidence.primary_articles` — which v19 will have CST anchors in. **Good — wiring still works.**
- BUT: A2 (LLM fallback) reuses polish-grade adapter. If polish just rejected for `invented_uvt_ranges`, same model is asked to numeric-tie-break conflicting bullets. Non-trivial risk A2 hallucinates again.
- Plan's Fase 6 flip to `enforce` doesn't add a numeric validator on A2 output. Suggest adding `_no_invented_uvt_ranges`-style structural check on A2's chosen value before applying.

#### 7. Surface-boundary risk: Normativa + Interpretación

- CLAUDE.md is explicit that `Normativa` and `Interpretación` are parallel surfaces with own orchestration. v19 Fase 2 changes `:ArticleNode` shape graph-wide. May silently break:
  - `interpretacion/retriever_supabase.py` — if joins ArticleNode→InterpretationNode via old key, dies.
  - `ui_normative_processors.py` consumes ET-article fallback from `artifacts/parsed_articles.jsonl` (per orchestration.md:268). JSONL keys need parallel rename or back-compat alias.
  - `Normativa` deterministic modal at `artifacts/canonical_corpus_manifest.json`.
- **Plan has no "check non-`main chat` consumers" step.** Add before Fase 4 ships.

#### 8. Validation budget thin for foundational change

- Six-gate lifecycle (CLAUDE.md non-negotiables + `verify_fixes_end_to_end` memory) requires more than "10 fixtures + 1 day operation + SME panel" for foundational schema change. Suggest:
  - **Shadow period (3-5 days)**: new schema in `:ArticleNodeV2` label alongside old; retriever reads both; diagnostics report which key resolved. Flip label rename at end of shadow.
  - **Diff harness**: every served answer in shadow runs both retrieval paths, diffs `seed_article_keys` + `primary_articles`. Operator looks at diff before flipping.
  - Catches "TEMA edges accidentally pointing at orphans" + "Normativa surface using old key" classes *without* rollback event.

#### 9. Rollback is per-phase, not ensemble

- Each fase has rollback line. **What if Fase 6 SME panel fails?** Flipping `LIA_CONFLICT_RESOLVER_MODE=shadow` is fine. But if SME failure traces to bad codigo assignments from Fase 3, must:
  1. Restore Fase 3 backup (Falkor dump).
  2. Revert Fase 4 commits (or live with consumer code referencing non-existent compound keys).
  3. Revert Fase 2 schema migration (or live with migration applied but no data behind).
- Order matters: Fase 4 must revert *before* Fase 3, else live retriever queries non-existent `cst:64` and 500s.
- Document unwind order explicitly.

### 💡 Alternatives (worth considering)

#### 10. Phase ordering can parallelize

- Dependency claim ("Fases 2-5 cannot be parallelized") is over-stated:
  - **Fase 5 (TEMA seeding) can start as soon as Fase 2 ships compound-key schema** — seeding script reads ArticleNode keys, doesn't care if ingestion has re-run.
  - **Fase 4 (consumer updates) can split**:
    - 4a: critical path — planner, retriever_falkor, ~31 case_bullets files, topic_norm_allowlist.json. Blocks Fase 5 validation.
    - 4b: cleanup — comparative_regime_pairs, subtopic_taxonomy if it references articles, test fixtures. Can land in Fase 6 with SME panel.
- Shaves 1 day off wall-clock without breaking idempotency.

#### 11. Reuse `canon.canonicalize()` instead of new mapper

- Reuse for parsing + key construction in Fase 2. Already production-tested.

### ❓ Questions (need more info before forming opinion)

#### 12. Embedding regeneration

- Existing `document_chunks` carry embeddings keyed to chunk content, not article anchor. So compound-key migration likely doesn't need embedding regeneration — but plan doesn't say so.
- Operator should confirm: chunk embeddings are content-keyed, not anchor-keyed, before greenlight.

#### 13. Cloud `norms` / `norm_vigencia_history` / `norm_citations` tables

- These ALREADY use `norm_id` (dotted grammar). Plan touches Falkor only. Relationship between `:ArticleNode.key` (Falkor, post-v19 = `et:64`) and `public.norms.norm_id` (Supabase = `et.art.64`) ends up with TWO key conventions for same logical article.
- This is exactly the kind of accidental complexity Observation 1 warns about.

### 14. Things operator should know that plan doesn't say

- **Test parser on CST markdown BEFORE Fase 2.** One hour; could change entire plan (parser bug vs schema bug).
- **Grep git history for TEMA-edge regression** before adding new seeding config.
- **Reuse `canon.canonicalize()`** instead of writing new `source_path → codigo` mapper for Fase 2. Grammar is production-tested.
- **Audit `artifacts/parsed_articles.jsonl`** — orchestration.md:268 says Normativa fallback reads it. Compound-key migration probably needs parallel artifact regeneration.

---

## Bottom line — what reviewer would do

(a) Spend 1 hour testing `parser.parse_articles()` on a CST markdown file to confirm whether the labor gap is a parser regex bug or a schema bug.
(b) `git log -S "TEMA"` to find when the 1,943-edge feature regressed and recover it instead of hand-curating a config.
(c) Re-key ArticleNode to align with the existing `canon.canonicalize` grammar (`et.art.64`, `cst.art.64`, `ley.50.1990.art.6`) so catalog, graph, and canonicalizer share one truth.
(d) THEN run Fases 4-6 against that aligned schema, with a 3-5 day shadow before the enforce flip.

---

## Key file references

- `src/lia_graph/canon.py:58`
- `supabase/migrations/20260501000000_norms_catalog.sql:11`
- `src/lia_graph/ingestion/loader.py:673-710` (TEMA emit)
- `src/lia_graph/ingestion/loader.py:487-490` (TEMA cleanup pass)
- `src/lia_graph/ingestion/parser.py:213` (parse_articles)
- `src/lia_graph/ingestion/parser.py:171` (_whole_document_fallback)
- `src/lia_graph/pipeline_d/orchestrator.py:1099-1167` (post-polish flow)
- `src/lia_graph/pipeline_d/retriever_falkor.py:299-353` (article queries)
- `scripts/canonicalizer/sync_vigencia_to_falkor.py:154-211`
- `config/topic_norm_allowlist.json` (uses `art:NNN` form)

---

*End of fix_v19_review_external.md.*
