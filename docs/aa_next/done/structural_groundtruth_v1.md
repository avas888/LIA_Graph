# structural_groundtruth_v1 — fixing the RAG foundation

> **Opened 2026-04-24** after a comprehensive taxonomy-vs-corpus audit (next_v2.md §J.6) surfaced structural rot across multiple layers — the most striking single finding being that **81 % of the cloud `iva` topic's TEMA edges are wrong-domain content** (RENTA Libro 1 chapters, Procedimiento P1+P2, Libro 7, etc., dumped into `iva` by an uncertain classifier).
>
> **Operator commitment (2026-04-24, escalating directive):** "no stone left unturned to fix corpus, labelling, taxonomy, embeddings, edges. If we find structural weakness or mis-procedures, we can fix or restart from scratch the ingestion. This is the BASE of a good RAG; it has to be very reliable and thorough."
>
> **This plan supersedes** next_v2.md §K (classifier hardening) for the structural layer. Re-flip of `LIA_TEMA_FIRST_RETRIEVAL` is now gated on the hard gates in §6 below, not on §K alone.
>
> **Policy.** Per `docs/learnings/process/investigation-discipline.md`: when an eval is catastrophic, the first week after is **read-only**. No code, no rebuilds. One investigation per open question, each with a method, a deliverable, and a decision impact. Every layer in §3 below carries the mandatory six-gate block from `docs/aa_next/README.md` before any fix lands. Status lifecycle: 💡 idea → 🛠 code landed → 🧪 verified locally → ✅ verified in target env → ↩ regressed-discarded.

---

## §0 First principles — what makes a RAG reliable, and where Lia fails

A RAG (retrieval-augmented generation) system is reliable iff **every layer in its stack satisfies its own first-principles requirement**. The layers compose: a failure at layer N propagates to layer N+1, N+2, … — so a wrong topic verdict (L3) becomes a wrong TEMA edge (L5) becomes a wrong retrieval candidate (L6) becomes a contaminated answer (L7). You can't fix L7 without fixing the upstream cause.

### §0.1 Seven layers and their non-negotiables

| # | Layer | First-principles requirement | What "broken" looks like |
|---|---|---|---|
| L1 | **Corpus** | **complete, current, de-duplicated, authoritative.** Every domain a user can ask about has docs covering it; docs reflect the current law (not stale); no two files contain the same content; sources are canonical (the actual regulation, not third-party summary). | missing domains; outdated articles; parallel-tree duplicates; uncited summaries treated as authoritative. |
| L2 | **Classification / labelling** | **accurate, complete, stable.** Each doc gets the right topic + subtopic; no NULL where a value belongs; re-running on the same input produces the same output. | high mis-classification rate; high `requires_review`; verdict instability across runs. |
| L3 | **Taxonomy** | **exhaustive, mutually exclusive, user-aligned.** Every doc has a place to live (no "misc" bucket large enough to hide things); two topics never reasonably claim the same doc; topic names match how the user (an accountant) would describe a question. | docs with nowhere to go (forced into nearest-sounding wrong topic); two topics overlapping (classifier coin-flips); topic name diverges from user vocabulary. |
| L4 | **Embeddings** | **domain-fit, consistent, complete.** Model trained or fine-tuned for the language + topic of the corpus; same model + version across all chunks; no NULL embeddings. | English-only model on Spanish legal text; mid-run model upgrade; missing rows. |
| L5 | **Graph / edges** | **ontologically faithful, no dangling.** Edges accurately model the regulatory ontology (article cites article, reform modifies article, topic owns article). Every edge endpoint exists. | stale edges from past mis-classifications; dangling edges to nodes that don't exist; redundant edges. |
| L6 | **Retrieval** | **precision-balanced, topic-respecting.** Pulls only chunks that actually answer the query; doesn't surface cross-domain content. | contamination (Q11/Q16/Q22/Q27 cases); over-aggressive abstention; off-by-one ranking. |
| L7 | **Synthesis** | **evidence-grounded, abstention-honest.** Cites what was retrieved; refuses when evidence is insufficient; doesn't hallucinate. | citing articles that weren't retrieved; confidently answering with cross-topic evidence; over-refusing on legitimate queries. |

### §0.2 Where Lia fails today, ranked by severity

**🔥 Severe — L3 Taxonomy is NOT exhaustive AND NOT mutually exclusive.** This is the root cause of most other failures.

- *Not exhaustive.* `impuesto_timbre` missing → all 30+ articles of ET Libro 4 (Timbre) get the nearest-sounding wrong answer (`facturacion_electronica`). `rut_responsabilidades` missing → RUT-registry content gets bucketed into `beneficiario_final_rub` (a different registry). At least 5 more candidate gaps pending SME (renta_presuntiva, proteccion_datos, parafiscales, zomac, reforma_laboral_2466).
- *Not mutually exclusive.* `iva` and `procedimiento_tributario` both reasonably claim ET Libro 5 (Procedimiento) → the classifier coin-flips → 435 procedimiento edges land in `iva`. `comercial_societario` vs `obligaciones_mercantiles` boundary unclear (the gold-file alignment learning already noted Q19 confusion). `costos_deducciones_renta` empty in cloud while RENTA Libro 1 Cap 5 (Deducciones) ends up in `iva`.

**🔥 Severe — L2 Classification is path-blind, taxonomy-blind, and uncertainty-prone.**

- *Path-blind.* The classifier ignores `source_path` as a sanity check. A doc whose path screams `RENTA/NORMATIVA/Normativa/` can be labeled `facturacion_electronica` without any veto.
- *Taxonomy-blind.* (To be confirmed by I9.) If the classifier prompt doesn't include the FULL current taxonomy as the candidate set, free-form generation produces drift. Pick-from-list is more reliable.
- *Uncertainty-prone.* 30 % `requires_subtopic_review=true` at workers=4 + clean run. The system has no human-review queue draining; uncertain verdicts ship.

**⚠️ Moderate — L1 Corpus has parallel trees + staging clutter.**

- Parallel `CORE ya Arriba/<DIR>/` and lowercase `<dir>/` paths (e.g. `CORE ya Arriba/SAGRILAFT_PTEE/` and `knowledge_base/facturacion_electronica/`) likely overlap. Need dedup.
- `to upload/`, `Documents to branch and improve/`, `to update/`, `NUEVOS-DATOS-BRECHAS-MARZO-2026/` are operational staging that pollutes the canonical retrieval set.
- Less severe than L2/L3 but adds classifier difficulty and retrieval noise.

**❓ Unknown — L4 Embeddings have not been audited.**

- Completeness, model consistency, and Spanish-legal-text fitness are all open questions. Could be a hidden bottleneck — investigations I10–I12.

**🩹 Inherited — L5 Edges are 81% wrong on `iva`, but that's an L2 symptom.**

- §J's TEMA cleanup proves L5 itself is fine: it produces correct edges from whatever L2 hands it. The cleanup mechanic works. The bad edges are downstream of the L2 classifier dumping content into wrong topics.

**✅ OK — L6 Retrieval and L7 Synthesis behave correctly given clean upstream data.**

- Q27 case: once §J wiped the stale TEMA edge in cloud, retrieval and synthesis BOTH stopped surfacing art. 148 in SAGRILAFT answers. The defenses (topic-safety, coherence gate, citation allow-list) work — they just shouldn't have to fire as often as they do today, and they can't catch every L2 mistake.

### §0.3 The leverage point

**The single highest-leverage intervention is fixing L3 (Taxonomy).**

- It's small in scope (JSON config edit + SME ratification + keyword-bucket update — not thousands of LOC).
- It's upstream of L2: a taxonomy-aware classifier with an exhaustive + mutually-exclusive list to pick from will produce dramatically better verdicts.
- It's upstream of L5: correct L2 verdicts produce correct TEMA edges; the §J cleanup mechanic handles the historical wash.
- The fix shape is well-known: add `impuesto_timbre`, `rut_responsabilidades`, audit the rest with the SME, define mutual-exclusivity rules between overlapping topics, document each topic's user-vocabulary anchor.

**The second-highest leverage is making L2 taxonomy-aware.**

- Pick-from-list classification with the full current taxonomy as candidates.
- Path-based veto for sanity (Option K2 from next_v2.md §K) — the directory tree is a strong domain signal that the classifier currently ignores.
- Confidence threshold + human-review queue for sub-threshold verdicts (Option K3) — `requires_subtopic_review=true` is currently a flag that goes nowhere.

**L4 + L5 are downstream cleanups.** Once L3 + L2 are right, L4 is just a "re-run `embedding_ops.py` on the new chunk set" pass; L5 is just a workers=4 rebuild that lets §J's cleanup wipe the historical contamination.

### §0.4 What this means for the order of operations

The original §1+ plan listed I1–I16 as parallel work. The first-principles analysis re-orders it as a strict dependency chain:

```
L1 audit (I1-I3)        →  decides corpus diff
        ↓
L3 taxonomy v2 (I4-I6)  ←  the centerpiece; SME-blocking but cheap to write
        ↓
L2 classifier (I7-I9)   ←  redesign on top of frozen taxonomy v2
        ↓
re-classify the corpus  ←  one workers=4 rebuild; §J cleanup wipes the historical wash
        ↓
L4 + L5 audit (I10-I16) ←  cleanup passes, not blockers
        ↓
re-run staging A/B; re-flip TEMA-first if all 7 hard gates in §6 hold
```

Ground-truth pass is done when each layer above passes its first-principles requirement, not when each individual investigation closes.

---

## §1 What we already know (evidence base)

From the 2026-04-24 audit recorded in `next_v2.md §J.4–§J.6`:

- `iva` TopicNode: **917 TEMA edges**, only 170 from legitimate IVA sources (Libro 3 IVA + IVA_COMPLETO + IVA_CALENDARIO). The other **747 edges are mis-classifications** — every RENTA Libro 1 chapter (Ingresos, Costos, Deducciones, Sujetos Pasivos, Rentas Especiales, Patrimonio T2 — wait, that's in sector_cultura), Procedimiento P1+P2, Libro 7 ECE/CHC, Régimen Especial, Ajustes Inflación. The Q27 art. 148 case is one symptom of this systemic bug.
- `sector_cultura`: 89 edges, **63 from `10_Libro1_T2_Patrimonio.md`** (income-tax patrimony content labeled as cultural-sector — totally wrong domain).
- `facturacion_electronica`: 67 edges, **49 from `17_Libro4_Timbre.md`** (entire ET Libro 4 = impuesto de timbre, mis-routed because **`impuesto_timbre` doesn't exist as a topic**).
- 12 of 79 taxonomy classes have **zero TEMA edges** in cloud, of which at least 4 have confirmed corpus content stuck in the wrong topic (`ingresos_fiscales_renta`, `patrimonio_fiscal_renta`, `firmeza_declaraciones`, `devoluciones_saldos_a_favor`).
- 7 corpus directories have **no matching taxonomy class**, of which `impuesto_timbre` and `rut_responsabilidades` are confirmed missing classes (RUT and RUB are distinct registries).
- Classifier silent-degradation: workers=8 produced 27.5 % N1-only verdicts under TPM pressure (96 tracebacks, 48 HTTP 429s). Workers=4 produced 30.4 % `requires_subtopic_review=true` cleanly (honest uncertainty, not degradation).
- §J cleanup verified: stale TEMA edges DO get wiped on full rebuild now (Q27 art. 148 → sagrilaft binding gone, Q24 GMF range stable).

The audit data is in:
- `next_v2.md §J.6` — taxonomy-vs-corpus audit + magnet-topic table.
- `scripts/diagnostics/probe_q27_q24.py` and `scripts/diagnostics/probe_q11.py` — the throwaway Cypher probes.
- `artifacts/eval/ab_comparison_20260425T001058Z_v9_post_cleanup.{jsonl,manifest.json}` — the post-cleanup A/B that confirmed Q27 fixed and Q11 still broken.

---

## §2 Five layers, one foundation

The RAG's correctness depends on every layer being right. A bug at layer N propagates to N+1, N+2, ... so the fix order matters.

| # | Layer | Owner | What can be wrong | Today's state |
|---|---|---|---|---|
| L1 | **Corpus** | content team / SME | missing docs, unclassifiable docs, duplicates, stale docs, pollution from `to upload/` `Documents to branch and improve/` | partly mapped; ~7 corpus-dir → no-topic gaps known |
| L2 | **Taxonomy** | engineering + SME | missing classes, redundant classes, ambiguous boundaries between classes, stale gold-file alignment | 79 classes, 12 empty, 2+ missing |
| L3 | **Labelling / classification** | engineering (LLM) | wrong topic verdicts, low-confidence verdicts, verdict instability across runs, taxonomy-aware vs taxonomy-blind | `iva` 81 % wrong, classifier picks nearest-sounding when correct topic missing |
| L4 | **Embeddings** | engineering | stale, partial, wrong model, NULL where expected, drift between runs | **NOT YET AUDITED** — embeddings.py runs as separate pass; status unknown post-rebuild |
| L5 | **Edges (TEMA, SUBTEMA_DE, HAS_SUBTOPIC, REFERENCES, MODIFIES, ...)** | engineering | inherited from L3 (wrong topic → wrong TEMA), stale (pre-§J cleanup), dangling (target node not materialized), redundant | TEMA partly fixed by §J; SUBTEMA_DE/HAS_SUBTOPIC/REFERENCES not yet audited |

**Dependency order.** L1 → L2 → L3 → L4 + L5. Embeddings + edges are downstream of classification. Classification is downstream of taxonomy. Taxonomy is downstream of corpus reality.

The investigations in §3 audit each layer in dependency order; the fix plan in §4 executes in dependency order too.

---

## §3 Investigations to run (read-only, this week)

Every investigation answers ONE specific question with evidence. Deliverable is a short report, not a PR. Decision-impact column says how the result routes into §4's fix plan.

### L1 — Corpus

**I1 — Corpus inventory completeness.** Walk `knowledge_base/`, classify each file as: (a) live canonical (`CORE ya Arriba/<DOMAIN>/`), (b) staging (`to upload/`, `Documents to branch and improve/`, `to update/`), (c) experimental (`NUEVOS-DATOS-BRECHAS-MARZO-2026/`), (d) outside-scope. Cross-reference against `corpus_reconnaissance_report.json`. **Decision:** which staging-area docs should be live? Which experimental ones should be moved? Which should be excluded entirely?

**I2 — Duplicate / near-duplicate detection.** Hash docs by content (sha256 of normalized body). Flag duplicate or near-duplicate doc pairs across `CORE ya Arriba/` vs `knowledge_base/<topic_dir>/` (the lowercase topic-dir trees). **Decision:** which is canonical? Delete the rest. Reduces classifier noise.

**I3 — RENTA Libro coverage map.** For each ET Libro (1–8), list the source file in the corpus + which articles it contains + what topic it's currently bound to in cloud Falkor. This is the ground truth for §J.6's contamination case. **Decision:** for each Libro / chapter, what's the CORRECT taxonomy class? Drives I4's taxonomy work.

### L2 — Taxonomy

**I4 — Taxonomy completeness vs Colombian tax-domain reality.** SME audit. Cross-reference `config/topic_taxonomy.json` against the canonical Colombian tax + labour + accounting domain map. Identify (a) missing classes (start: `impuesto_timbre`, `rut_responsabilidades`; SME may add more), (b) redundant classes that should merge, (c) ambiguous boundaries (e.g. `comercial_societario` vs `obligaciones_mercantiles`). **Decision:** final taxonomy diff for v2 (additions + deletions + renames).

**I5 — Topic-key vs subtopic-key boundary.** For each topic with edge count > 50, audit whether some of its content is actually subtopic-grade (e.g. `parafiscales` as a subtopic of `laboral`). **Decision:** which new classes go to `topic_taxonomy.json` vs `subtopic_taxonomy.json`.

**I6 — Gold-file alignment.** Re-run the citation-allowlist learning's gate: `for row in evals/gold_retrieval_v1.jsonl: assert row.expected_topic in taxonomy_keys`. Patch any drift in the same PR as the taxonomy diff. (Per `docs/learnings/retrieval/citation-allowlist-and-gold-alignment.md` Part 2.)

### L3 — Labelling / classification

**I7 — Classifier verdict stability.** Two consecutive workers=4 rebuilds against the v6+ corpus. Check: does each doc get the same `topic_key` in both runs? `requires_subtopic_review=true` rate stable? **Decision:** is the classifier a stable foundation, or is it inherently noisy and we need a different approach (rules-based path veto, multi-vote ensemble, human-in-loop)?

**I8 — Path-vs-verdict consistency.** For every classified doc, compare its `source_path`'s domain dir to its `topic_key` verdict. Flag mismatches. Build the actual data feeding the §K Option K2 design. **Decision:** is K2's path-based veto a heuristic safety net or a primary classification mechanism?

**I9 — Taxonomy-aware classification.** Verify that the classifier prompt currently includes the FULL taxonomy as the candidate set. If not, that's the bug — classifier pick-from-list is more reliable than free-form. **Decision:** prompt redesign vs. rules-based override vs. both.

### L4 — Embeddings

**I10 — Embedding completeness audit.** For every `document_chunks` row in production Supabase, count how many have `embedding IS NULL` vs populated. Compare against the `gen_active_rolling` generation. **Decision:** is the embedding pass complete and current, or do we need to re-run `embedding_ops.py`?

**I11 — Embedding drift across rebuilds.** If we have any chunk_id that existed pre-§J and post-§J with the same content_hash, do their embeddings match? (They should — same content = same embedding under the same model.) If they don't match, we have a model-version drift bug. **Decision:** is the embedding model stable? Do we need to pin a version?

**I12 — Embedding model fitness.** Sample 30 query-chunk pairs from `evals/gold_retrieval_v1.jsonl` where retrieval failed (per recent A/Bs). For each, compute embedding-cosine-similarity between the query and the expected chunk. Distribution shape tells us whether the embedding model is the bottleneck or just downstream of bad classification. **Decision:** is the embedding model the right model for Spanish legal text? (Currently Gemini text-embedding.)

### L5 — Edges

**I13 — TEMA edge audit (post-§J cleanup baseline).** Per topic, what fraction of TEMA edges come from a corpus-dir that semantically matches the topic? §J.6 already started this; make it exhaustive across all 67 TopicNodes. **Decision:** which topics need reclassification (their existing edges are fine but they're missing edges from currently-mis-routed content) vs. which topics are pure magnets (most existing edges should be deleted).

**I14 — SUBTEMA_DE + HAS_SUBTOPIC audit.** Same shape as I13 but for the subtopic edges. **Decision:** does subtopic routing work as designed, or is it inherited from the same broken classifier?

**I15 — Dangling-edge audit.** Run the existing dangling-edge detector (`ingestion/dangling_store.py`). What's the count of dangling edges? Does the additive-corpus-v1 mechanism resolve them on rebuild? **Decision:** are we accumulating ghost edges, or is the dangling detection working as designed?

**I16 — Other edge types.** REFERENCES, MODIFIES, DEROGA, EMITED_BY — same audit shape. Lower priority than TEMA but in scope.

---

## §4 Decision tree per layer — fix-in-place vs. rebuild-from-scratch

After each investigation closes, route its result into one of these fix patterns:

| Layer | Fix-in-place pattern | Rebuild-from-scratch pattern |
|---|---|---|
| **L1 Corpus** | Add/remove specific docs. Re-classify only modified/added. | Wipe `gen_active_rolling`, re-ingest from a curated whitelist. Cost: ~1 hr cloud + Gemini budget; high blast radius. |
| **L2 Taxonomy** | Patch `config/topic_taxonomy.json` (additive). Run a re-classify pass on docs whose path matches the new class's domain dir. | Burn down to a SME-curated taxonomy v2; full re-classify everything. |
| **L3 Classifier** | Prompt + rules-based path veto (K2). Behind off-by-default flag. | Replace classifier model (Gemini Flash → Gemini Pro / different provider) + re-classify all 1,280 docs. |
| **L4 Embeddings** | Re-run `embedding_ops.py` on NULL rows only. | Wipe `document_chunks.embedding`, regenerate everything. |
| **L5 Edges** | §J's pre-MERGE TEMA cleanup (already landed). Same pattern for SUBTEMA_DE / HAS_SUBTOPIC if I14 surfaces equivalent stale state. | Wipe the cloud graph + re-run loader. |

**The default is fix-in-place** — it's cheaper, smaller blast radius, easier to revert. Rebuild-from-scratch escalates only when fix-in-place is structurally impossible (e.g. taxonomy v2 is so different from v1 that incremental migration isn't worth it).

The operator commitment ("we can fix or restart from scratch") authorizes either path. The investigations in §3 are what tell us which is right per layer.

---

## §5 What we explicitly will NOT do this round

To keep the structural-groundtruth pass tight:

- **No retrieval-side changes** (`retriever.py`, `retriever_supabase.py`, `retriever_falkor.py`). The contamination cases are L3/L5 problems; fixing them at L6 (retrieval) is the wrong layer.
- **No synthesis / answer-policy changes.** Same reason — those are L7+ and inherit whatever L1–L5 produce.
- **No new evals.** Step 08's gold v2 stays SME-blocked. We use the existing 30Q gold to measure each fix's effect; gold v2 is a separate concurrent track.
- **No flag flips.** `LIA_TEMA_FIRST_RETRIEVAL` stays `shadow`. Re-flip is gated on §6.
- **No partial classifier-pool TPM work.** Item D (next_v2 §7 / TokenBudget primitive) is a parallel track. It would help workers=8 stop degrading, but it doesn't fix the structural classifier-verdict-quality problem.

---

## §6 Hard gates for re-flip and "ground-truth done"

Re-flip of `LIA_TEMA_FIRST_RETRIEVAL` to `on` requires ALL of:

1. ✅ §J landed — already done (next_v2.md §J).
2. **L1 corpus inventory clean** — I1 + I2 + I3 closed; corpus is the canonical set we want.
3. **L2 taxonomy v2 frozen** — I4 + I5 + I6 closed; SME has signed off.
4. **L3 classifier stable + correct** — I7 + I8 + I9 closed; classifier verdict-quality on a 30-doc spot-check sample is ≥ 95 % SME-agreement on RENTA-rooted docs (where we've measured the worst contamination), and `iva`'s wrong-domain edge ratio is < 10 % (down from current 81 %).
5. **L4 embeddings complete + current** — I10 + I11 + I12 closed; embedding NULL rate = 0, no model drift.
6. **L5 edges clean** — I13 + I14 + I15 + I16 closed; magnet-topic ratios all under 10 %; dangling count = 0.
7. **Re-run staging A/B** (next_v2 §5 action A semantics) — passes all 4 criteria: seeds ≥ 20/30, mean primary ≥ 2.5, contamination 4/4 clean, no ok→zero regression.

Soft gate: SME spot-check on a sample of 50 chat answers across mixed topics finds zero cross-topic contamination.

---

## §6.5 SME deliverable received (2026-04-25 · ✅ unblocks I4–I6)

Alejandro (contador público / asesor tributario y laboral PYMEs) returned the full v2 design — saved at [`taxonomy_v2_sme_response.md`](./taxonomy_v2_sme_response.md). Top-line decisions:

- **2 confirmed-missing classes accepted** as top-level: `impuesto_timbre`, `rut_y_responsabilidades_tributarias` (renamed from `rut_responsabilidades` for legibility).
- **Of the 7 maybe-missing in the brief: 5 land as new top-level** (`parafiscales_seguridad_social`, `reforma_laboral_ley_2466`, `proteccion_datos_personales`, `niif_pymes`, `niif_plenas`); `renta_presuntiva` becomes a subtopic of `declaracion_renta`; `zomac_incentivos` becomes a subtopic of `inversiones_incentivos` (renamed `zomac_zese_incentivos_geograficos`).
- **3 additional gaps the brief missed, raised by SME:** `regimen_cambiario`, `dividendos_y_distribucion_utilidades`, `regimen_tributario_especial_esal` — all top-level.
- **`estados_financieros_niif` deprecated** — splits into `niif_pymes`, `niif_plenas`, `niif_microempresas` (3 distinct technical frameworks per Decreto 2420/2015 Annexes 1/2/3).
- **`comercial_societario` and `obligaciones_mercantiles` merge** into one (`comercial_societario`).
- **All 12 empty taxonomy slots confirmed** with 2 renames (`anticipos_retenciones_a_favor` → `retencion_fuente_general`; `tarifas_tasa_minima_renta` → `tarifas_renta_y_ttd`) and 5 reassigned to subtopic of `declaracion_renta` or `procedimiento_tributario`.
- **6 mutex rules codified** as `scope_out` pointers — the boundary between `iva` and `procedimiento_tributario`, between `iva` and the RENTA-family, between `facturacion_electronica` and `impuesto_timbre`, between RUB and RUT, between the labor-family pieces.

**Net taxonomy size:** 79 → ~88–90 top-level topics + several new subtopics.

**Engineering implementation guidance from the SME (load-bearing):**
1. Add `allowed_norm_anchors` field for non-ET topics (CST, NIIF, Decretos) — `allowed_et_articles` doesn't fit non-tributary topics.
2. Labeler should default to PARENT topic when a doc spans multiple subtopics; only descend to subtopic on clear specificity.
3. Add `vigencia_window` field per topic — `evergreen`, `transitorio_with_sunset_review`, `vigencia_anual`.
4. Mark non-renta topics with `corpus_coverage: pending` — the corpus today is 100 % renta-centric and the new top-level topics for laboral/cambiario/datos-personales etc. won't have docs until ingestion expands.
5. Encode the 6 mutex rules as **HARD instructions** in the classifier prompt, not suggestions.
6. The 30 user-questions in the SME response §3.2 are the validation suite — post-rebuild, ≥ 27 / 30 must classify correctly to approve taxonomy v2.

**Status of investigations:**

- ✅ I4 (taxonomy completeness vs Colombian tax-domain reality) — **CLOSED** by SME deliverable.
- ✅ I5 (topic vs subtopic boundary) — CLOSED.
- ⚠️ I6 (gold-file alignment) — needs CI gate update once v2 is in `config/topic_taxonomy.json`. Engineering work, ~30 min.
- ➡️ I7 (classifier verdict stability) — runs AFTER taxonomy v2 lands.
- ➡️ I8–I9 (classifier path-veto + taxonomy-aware prompt) — runs AFTER taxonomy v2 lands.

---

## §7 What's next (immediate)

In recommended order:

1. **I3 first** (RENTA Libro coverage map, ~30 min, I can do now). It's the cheapest, highest-info investigation — tells us per-Libro what topic each chapter SHOULD belong to. That data feeds I4 (taxonomy diff with SME) and I8 (path-veto rules).
2. **I1 + I2 in parallel** (corpus inventory + dedup, ~1 hr each, I can do now). Establishes the canonical corpus set so I4's taxonomy decisions aren't muddled by experimental docs.
3. **I10 + I15** (embedding completeness + dangling edges, ~10 min each, I can do now). Cheap probes to confirm L4 + L5 don't have a separate hidden problem.
4. **Schedule the SME design call** for I4 + I9 (taxonomy v2 freeze + classifier prompt redesign). After I1–I3 close, the SME has concrete data to decide on.
5. **I7 (classifier stability)** runs across two sequential workers=4 rebuilds. ~15 min wall time per rebuild. Defer until L1–L2 fixes have landed so the comparison isn't muddied by mid-stream changes.

Investigations I11, I12, I13, I14, I16 are batched after the SME call — they need the taxonomy-v2 baseline to be meaningful.

---

*Opened 2026-04-24. See `next_v2.md §J` for the audit findings that motivated this plan; this doc supersedes next_v2.md §K for the structural layer.*
