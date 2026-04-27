# Persistence granularity: pick the right level for each fact

**Source:** Activity 1.5b (`scripts/persist_veredictos_to_staging.py`) — manual veredicto persistence to staging Supabase + Falkor, executed 2026-04-26 evening. Audit log at `evals/activity_1_5/persistence_audit.jsonl`. Companion to `docs/learnings/process/activity-as-surgical-precursor.md`.

## What we discovered

Activity 1.5 produced 4 veredicto JSON fixtures. Activity 1.5b's job was to make them "real" in staging DBs. The naive plan was "wholesale-flag the corresponding documents" — but that fell apart immediately on contact with the actual schema. We had to discriminate **per-fact** between three persistence levels:

| Level | Schema target | Right when... |
|---|---|---|
| **Document-level** | `documents.vigencia` enum | The whole document IS the norm and the norm has a uniform vigencia state. Rare for our corpus — most docs are interpretations or compilations. |
| **Chunk-level** | `document_chunks.vigencia` + `vigencia_basis` (LIKE-pattern on `chunk_id`) | The fact is article-scoped AND the article appears as ≥ 1 chunk(s). Targeted via `chunk_id LIKE '%::<article_key>'`. This is the right level for "Art. 689-3 ET is VM" — the ET as a whole isn't VM, but its 689-3 chunks are. |
| **Falkor edge-level** | `MERGE (a:ArticleNode)-[r:DEROGATES\|MODIFIES\|STRUCK_DOWN_BY]->(:ReformNode)` with edge properties | The fact is a structured RELATIONSHIP between norms (one law derogates another; a sentencia strikes down a decreto). Falkor schema natively supports this; Supabase columns flatten it. |

**The right persistence target is fact-shaped, not target-shaped.** "Vigencia state of an article" → chunk-level. "This sentencia struck down that decreto" → edge-level. "The whole document is derogated" (rare) → document-level.

## What Activity 1.5b actually did

For 4 veredictos, we used 3 different persistence patterns:

| Veredicto | State | Document-level? | Chunk-level? | Edge-level? |
|---|---|---|---|---|
| Decreto 1474/2025 → IE | IE | ❌ (interpretation docs ≠ the Decreto; per Activity 1.5 discrimination) | ❌ (no ET chunks for Decretos) | ✅ `Decreto-1474-2025 STRUCK_DOWN_BY Sentencia-C-079-2026` with `fecha + alcance + efectos` properties |
| Art. 689-3 ET → VM | VM | ❌ (ET is mixed-state) | ✅ `chunk_id LIKE '%::689-3'` → 2 rows updated | ✅ `Ley-2294-2023 MODIFIES Art-689-3` with `articulo_modificador + fecha + scope` |
| Art. 158-1 ET → DE | DE | ❌ (same) | ✅ `chunk_id LIKE '%::158-1'` → 1 row updated | ✅ `Ley-2277-2022 DEROGATES Art-158-1` with `articulo_derogador + fecha_efectos` |
| Art. 290 #5 ET → V | V | ❌ (no change to vigencia state) | ❌ (chunk vigencia already correct) | ✅ Property-only update: `art.regimen_transicion_origen + alcance + constitucionalidad_confirmada_por` |

3 chunks updated in Supabase. 7 nodes created in Falkor. 3 structured edges. 1 property-only article update. The right persistence per fact, not "wholesale flag every doc that mentions 1474."

## What would have happened with naive wholesale-flagging

The original Activity 1.5b plan said "UPDATE `documents` SET vigencia=... WHERE relative_path LIKE '%1474%'." This would have:

- Hit `Ley 1474/2011` files (anti-corruption law — completely unrelated to Decreto 1474/2025; vigente). Marked them `derogada`. **Production-grade error.**
- Marked the SME-curated interpretation docs about Decreto 1474/2025 as `derogada`. They would no longer surface in retrieval. Users would lose the system's ability to explain the IE state. **Per Activity 1.5's reasoning, this is the wrong target entirely.**

Discriminating per fact eliminated both errors before they shipped.

## The rule that survives

**Before persisting any structured fact: name the fact's grain (which entity is it about?), name the schema's grain (which table/edge type carries that grain?), and match them.** A mismatch produces either:
- **Too coarse** (wholesale-flag one doc to express a fact that's actually article-scoped) → loss of useful content
- **Too fine** (try to use chunk-level when the fact is a relationship between norms) → fact never materializes; gets re-discovered every retrieval

For the vigencia 7-state taxonomy specifically:

| State | Natural persistence grain |
|---|---|
| V (no modifications) | Article property (or implicit — no record needed) |
| VM (modified) | Edge: `MODIFIES` with `fecha + scope` properties + chunk-level `vigencia` stays `vigente` (text is current) |
| DE (derogated express) | Edge: `DEROGATES` + chunk-level `vigencia` = `derogada` |
| DT (derogated tácita) | Edge: `DEROGATES` with `tipo='tácita'` + chunk-level `vigencia` = `parcial` (uncertain) |
| SP (suspended) | Edge: `SUSPENDS` + chunk-level `vigencia` = `suspendida` |
| IE (inexequible) | Edge: `STRUCK_DOWN_BY` + chunk-level `vigencia` = `derogada` (effect-equivalent) |
| EC (exequibilidad condicionada) | Article property: `condicionamiento_literal` text + chunk-level `vigencia` = `vigente` |

This table is the contract Fix 1B-γ implements at corpus scale. Activity 1.5b validated it on 4 cases first.

## What this enables downstream

- **Fix 1B-γ scope is now precise.** The materialization step knows exactly which schema target to write to per skill state. No second design round needed.
- **Fix 1C retrieval** can compute its 2D vigencia demotion factor by joining chunk-level `vigencia` with Falkor edge-level temporal data — both sources agree per the granularity discipline.
- **Fix 5 golden judge** can audit either side: "is the chunk vigencia consistent with the Falkor edges?" If they disagree, that's a Fix 6 audit candidate.

## Anti-pattern to avoid

**"Just put it in Supabase columns; we can always add Falkor later."** Tempting because Supabase writes are simpler. Wrong because:

1. Edge-level facts (one norm → another) flatten into JSON-in-a-text-column — un-queryable without parsing.
2. Cross-norm queries become full-table scans instead of graph traversals.
3. Future fact additions (e.g. concept reconsideration chains) duplicate the flattening pain.

The Falkor schema exists for relationships. Use it. The fact that the project stayed on the binary `documents.vigencia` flag for so long is the cost-side evidence — every query that wanted "what derogated this article?" had to parse text instead of traverse an edge.
