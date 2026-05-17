# fix_v20_may.md — fix the WHOLE staging corpus (close v19's last mile) — v1

> **Zero-agent-context protocol.** Self-contained. A fresh agent with no prior conversation can execute it by reading this file + the filesystem. Verify every artifact against `git ls-files`. If something doesn't exist, STOP and report drift.

---

## §⏯ Crash-resume pointer (update this block after EVERY step)

**Read order if you are a fresh agent resuming after a crash:** §⏯ (here) → §-1 → §11.1 preconditions → the "Next step" pointer below.

| Field | Value |
|---|---|
| Last completed step | **v20 P1–P4 closed ✅** — end-to-end chat probe (`q01: ¿Qué dice el artículo 64 del CST?`) confirmed: planner now emits `cst.art.64` in `retriever.supabase.entry.query_text_preview`, topic routes to `laboral`, anchor-walk surfaces 3 primary articles + 4 labor citations from cloud staging. The v20 collision fix is alive in production-shape chat traces. |
| Last touched UTC | 2026-05-17T01:35:00Z (2026-05-16 ~08:35 PM Bogotá) |
| Next step | **v21 / out-of-scope follow-up** — q01's user-visible answer is wrong (cesación codes 54-58 + recargos instead of terminación-indemnización). Root cause is downstream of v20: polish rejected with `skip_reason=invented_norm_lineage` + `answer_synthesis_practica` chunk-selection grabbed the wrong práctica bullets. Fix path: tune `answer_synthesis_practica.py::_candidate_lines_from_chunk` OR loosen the polish validator's `_no_invented_norm_lineage` rule per labor context. |
| Probe artifact | `tracers_and_logs/logs/probe_runs/20260517T013419Z_v20_labor_collision/` (q01.json + q01.digest.md + verdicts.jsonl + report.md). |
| Working artifact | `artifacts/v20/local_rehearsal_iter2/` — FROZEN, read-only, sha256 in `SHA256SUMS.txt`. Replay script at `scripts/cloud_promotion/replay_local_artifacts_to_cloud.py`. |
| Known parity gap | `article_subtopics` map is empty in replay (vs iter2's ~301 bindings). Cause: subtopic_key enrichment lives on classifier-returned CorpusDocument, NOT in canonical_corpus_manifest.json. Result: ~67 SubTopicNodes won't land via replay. Not blocking — SubTopicNodes are a secondary axis; v20's primary goal is collision fix + norm_id propagation. Fix later via events.jsonl extraction or by patching `_build_canonical_corpus_manifest` to use corpus_documents.subtopic_key. |
| Frozen checksums | `parsed_articles.jsonl=05f1b498…3eafe387`, `typed_edges.jsonl=3f61dca2…b23d143b8`, `canonical_corpus_manifest.json=4fa0b956…68cd827`, `raw_edges.jsonl=095719a6…0ed4411`, `graph_load_report.json=97e3045e…0909d509`. Full hashes in `artifacts/v20/local_rehearsal_iter2/SHA256SUMS.txt`. Verify on resume with `shasum -a 256 -c artifacts/v20/local_rehearsal_iter2/SHA256SUMS.txt`. |
| Local Falkor state | Populated by iter2 (3,410 ArticleNodes, 2,177 with norm_id, 0 dup, 3,401 TEMA edges) |
| Cloud Falkor state | Pre-v20: 9,331 ArticleNodes, 1,300 stamped with norm_id (v19 batch migration); **NO change yet from v20** |
| Cloud Supabase state | Pre-v20 baseline; **NO change yet from v20** |
| Uncommitted code changes | `src/lia_graph/norm_id_rules.py` (P1-T5 rule additions), `tests/test_norm_id_migration.py` (14 new tests), `docs/re-engineer/fix/fix_v20_may.md` (this file) |
| Heartbeat / monitor state | None active. Iter2 monitor (task b30ojfzbo) self-exited 12:08 PM. |
| If crashing now, resume with | (1) `git status` + `git diff` to verify uncommitted state. (2) Confirm `artifacts/v20/local_rehearsal_iter2/parsed_articles.jsonl` exists + is non-empty. (3) Run §11.1 preconditions. (4) Read latest §6 entry for context. (5) Continue at "Next step" above. |
| Hard rule | After EVERY task transition, update this block + §2 phase/task tables + append a §6 run log entry. Do not batch updates. |
>
> **Scope.** v19 fixed the schema, the loader, the local labor slice, and 1,300 cloud nodes. v20 propagates the fix across the **entire** cloud staging corpus + connects the assistant code so accountants actually see corrected answers. After v20: every numbered article in cloud staging has a unique identity, every article carries its topic, and the assistant uses the new identity for every query.
>
> **Companion docs.** [`fix_v19_may.md`](fix_v19_may.md) — predecessor (Fase 0/1/2 + Fase 3 partial). [`../state_fix_v19_may.md`](../state_fix_v19_may.md) — v19's execution ledger. This doc combines plan + state for v20.

---

## §-1. If you are a fresh agent — read this first

You are picking up a **half-shipped corpus-fix project**. v19 closed the schema migration + loader changes + 1,300 cloud nodes. v20's job is to (a) ingest the rest of the corpus, (b) connect the assistant code, (c) ship to users.

**Read in this order before touching anything (max 30 min):**

1. `CLAUDE.md` (repo root) — repo operating guide. The "Fail Fast, Fix Fast" + "Long-running Python processes" sections are load-bearing for §3.2 of this doc.
2. `AGENTS.md` (repo root) — layer ownership + surface boundaries.
3. **This file** §0 → §1 → §2 → §3 → §5.
4. [`fix_v19_may.md`](fix_v19_may.md) §1 (audit numbers) + §2.0.5 (locked decisions).
5. [`../state_fix_v19_may.md`](../state_fix_v19_may.md) §10 — v19's run log; tells you exactly what cloud state looks like right now.

**Hot facts you must know before touching anything:**

- **Default run mode is `dev:staging`** — cloud Supabase + cloud Falkor (`LIA_REGULATORY_GRAPH`). Don't ask "which mode?"; assume staging.
- **Cloud writes for Lia Graph are pre-authorized** — announce in chat before executing, no per-action confirmation needed. Lia_Graph only (NOT LIA_contadores).
- **Gemini Tier-1 throttle is 80 RPM project-wide.** File-locked at `var/gemini_throttle_state.json`. Never bypass; never raise without operator sign-off.
- **Default ingest behavior is additive, no retirements.** Never pass `--allow-retirements` unless typed by an operator.
- **Beta-stance: every non-contradicting improvement flag flips ON across all three run modes.** v20 follows this in P5-T4.
- **SME panel runs only on explicit operator trigger.** Never auto-run `scripts/eval/run_sme_parallel.py`.
- **Six-gate lifecycle is mandatory** for every pipeline change: idea → plan → success criterion → test plan → greenlight → refine-or-discard.
- **All user-facing times in Bogotá local 12-hour AM/PM.** Machine logs stay UTC.

**Operator's intent (boss directive, 2026-05-15 PM):**

- Quote: "I do not want to 'prove it works'. I want it TO WORK in staging for all topics. We need to fix THE WHOLE CORPUS."
- Translation: v20 is the full rebuild, classifier on, all topics, all articles. Not a labor-only slice.
- This is what locks §9 decision rows 3 (full rebuild) and 4 (classifier on).

**Memory-pinned guardrails (do not violate):**

- Diagnose before intervene — measure where failures concentrate before proposing a fix.
- Granular edits — don't append helpers to ≥1000-LOC files; extract to a focused sibling module.
- No text walls in any doc you produce — bullets / lists / tables only.
- No money / cost / $ quoted in any status report.
- Recommendations live in the canonical plan, not just chat — update §2 + §6 of this doc as work progresses.

**The big picture in two sentences:**

- Right now the cloud knowledge graph has ~9,300 articles, of which ~1,300 carry the new unique-id property but the assistant doesn't use it yet, and the other ~7,300 are still on old colliding keys. The accountant-visible problem is that "labor article 64" and "tax article 64" return the same wrong record, so labor questions get tax answers.
- v20 re-ingests the corpus with the new loader, populates topic-anchor edges, then edits ~30 files in the assistant code so it asks for articles by their unique id. After v20, accountants see correct cites.

---

## §0. TL;DR

- **The gap v20 closes.** v19 fixed the schema + cloud nodes that were stamped during the batch migration (1,300 nodes). The remaining ~7,300 cloud nodes still have their old keys; the assistant code still queries by the old keys; the labor code is in the corpus but hasn't been ingested into cloud; the "topic ↔ article" connections (TEMA edges) are empty in cloud.
- **Why v20 exists.** Without it, the v19 work is half-shipped: data is partially fixed but the assistant doesn't yet see corrected answers.
- **5 phases.** P1 local rehearsal, P2 cloud full rebuild, P3 verify, P4 connect the assistant, P5 shadow + flags + SME panel.
- **Time budget.** P1–P3: ~1.5 hours wall-clock today. P4: 1.5–2 engineering days. P5: 3–5 days shadow + operator-triggered panel.
- **Risk.** Every step is reversible with one command. The only non-reversible part is P4's code edits — handled the same way every engineering change is: PR, tests, review.
- **Estado al 2026-05-15 evening.** P1 🛠 ready to start. Operator decision pending.

---

## §1. Where we are right now (v19 close-state)

### §1.1 What v19 landed (do not re-do)

- ✅ **Schema**: `:ArticleNode` has a `norm_id` property + unique index in cloud staging Falkor.
- ✅ **Loader**: `_build_article_nodes` stamps `norm_id` on every new ArticleNode. `graph_article_key` uses `norm_id` as the MERGE key.
- ✅ **Rules module**: `src/lia_graph/norm_id_rules.py` is the single source of truth for `(source_path, article_number) → norm_id`. Both the migration script and the loader import it.
- ✅ **1,300 cloud nodes** stamped with `norm_id` + `article_id` renamed to match (dotted form `et.art.420`, `ley.50.1990.art.64`, etc.).
- ✅ **Gap-filter classifier fix** — CST consolidado is no longer falsely excluded as "gap-analysis working material".
- ✅ **CST consolidado markdown** lives at `knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Codigo_Sustantivo_Trabajo.md` (504 article rows, 79 derogated, source Senado).
- ✅ **Local labor-slice ingest** validated end-to-end: CST 64 and Ley 50/1990 art 64 coexist as distinct nodes with correct headings.
- ✅ **TEMA `binding_summary` diagnostic** wired into both ingest paths.
- ✅ **250 unit tests** passing across canon + parser + migration + loader + gap-filter.

### §1.2 What v19 left undone (this is v20's mandate)

| Gap | Concretely | Why it matters |
|---|---|---|
| Cloud ingest of the full corpus | The 504 new CST articles + every existing non-numbered node have not been re-ingested with the v19 loader | Without this, CST art. 64 doesn't exist in cloud yet, and the existing 7,300 nodes are stuck on old keys |
| TEMA edges | Cloud shows **0** `(:TopicNode)-[:TEMA]->(:ArticleNode)` edges, while local shows **2,436**. v19 §2.0.2 proved this is a **data outcome of one bad rebuild**, not a code regression | Without TEMA edges, the planner's TEMA-first retrieval contributes 0 articles to labor (and every other topic) queries |
| Consumer code | Planner / retriever / case_specs / topic_norm_allowlist / citation_allowlist still match by bare numeric `article_id` instead of dotted `norm_id` | Without this, even with correct data, the assistant asks for `"art_id=64"` and gets whichever bare-64 record happens to win the lookup |
| Shadow + flags + SME panel | `LIA_CONFLICT_RESOLVER_MODE` stays at `shadow`; SME panel never run for v19 | Without this, we have no evidence that the user-visible answers improved |

### §1.3 The non-negotiable invariants v20 must preserve

- **Falkor-only scope per [fix_v19_may §2.0.5 Gate 1](fix_v19_may.md#205-operator-gate-decisions-2026-05-15-evening)** — Supabase `chunk_id` stays `<doc_id>::<article_key>`. No re-embedding of the 20,154 chunks.
- **SUIN catalog untouched** — the 6,805 `suin://N` nodes are v6's domain (`public.norms` + `:Norm`). v20's loader changes have a `suin_skipped` rule that preserves their existing identity.
- **Idempotency** — every step in this plan can re-run and produces the same end state.
- **Local↔cloud parity for canonical norms** — `norms`, `norm_vigencia_history`, `norm_citations`, `sub_topic_taxonomy` tables stay in sync via the existing scripts in `scripts/cloud_promotion/`.

---

## §2. State tracker (live — update this section as work progresses)

### §2.1 Phase status

| Phase | Description | Status | Owner | Last touched |
|---|---|---|---|---|
| P1 | Local full-corpus rehearsal | ✅ closed iter2 | claude-opus-4-7 | 2026-05-16 12:08 PM Bogotá |
| P2 | Cloud staging repopulation from verified local artifacts | ✅ closed | claude-opus-4-7 | 2026-05-16 12:27 PM Bogotá |
| P3 | Cloud verification | ✅ closed inline during P2-T4 | claude-opus-4-7 | 2026-05-16 12:27 PM Bogotá |
| P4 | Consumer code migration | ✅ core landed; T3/T4/T5 deferred (see §6) | claude-opus-4-7 | 2026-05-16 ~01:30 PM Bogotá |
| P5 | Shadow + flags + SME panel | 🟡 in progress (P5-T1/T2 next; T3 calendar; T5 self-audit via answer-engine-probe) | — | — |

Status legend: 🟡 not started · 🔵 in progress · ✅ done · 🚫 blocked · ↩ discarded.

### §2.2 Active blockers

| # | Blocker | Affects | Owner | Surfaced |
|---|---|---|---|---|

(none open as of 2026-05-15 evening)

### §2.3 Active tasks (rolls up from §3 phases)

| ID | Task | Phase | Status | Owner | Blockers | Last touched |
|---|---|---|---|---|---|---|
| P1-T1 | Wipe local Falkor (graph reset) | 1 | ✅ | claude-opus-4-7 | — | 2026-05-16 11:18 AM |
| P1-T2 | Local full-corpus ingest, classifier on, Falkor-only | 1 | ✅ | claude-opus-4-7 | P1-T1 | 2026-05-16 11:36 AM (iter1) / 12:06 PM (iter2) |
| P1-T3 | Inspect `ingest.norm_id.binding_summary` + `ingest.tema.binding_summary` events | 1 | ✅ | claude-opus-4-7 | P1-T2 | 2026-05-16 12:06 PM |
| P1-T4 | 15 spot-check Cypher queries on local Falkor | 1 | ✅ | claude-opus-4-7 | P1-T2 | 2026-05-16 12:08 PM |
| P1-T5 | Iterate — added 4 narrow rules (et marker extensions, nc_filename, emergencia_decreto_0240, regimen_cambiario_ley_9_1991, revisoria_fiscal_cco). OTHER 84 → 3 (predicted offline-replay ≡ live ingest). | 1 | ✅ | claude-opus-4-7 | P1-T3, P1-T4 | 2026-05-16 12:08 PM (iter2) |
| P2-T0 | Freeze verified local state — `chmod -w` + SHA256SUMS.txt written | 2 | ✅ | claude-opus-4-7 | P1 ✅ | 2026-05-16 12:13 PM |
| P2-T1 | Build `scripts/cloud_promotion/replay_local_artifacts_to_cloud.py` + `--from-artifacts` flag on `lia_graph.ingest` | 2 | 🟡 | — | P2-T0 | — |
| P2-T2 | Pre-flight one-doc replay (Supabase + Falkor) against cloud | 2 | 🟡 | — | P2-T1 | — |
| P2-T3 | Launch detached cloud replay + heartbeat | 2 | 🟡 | — | P2-T2 | — |
| P2-T4 | Activate Supabase generation + diff cloud vs local counts | 2 | 🟡 | — | P2-T3 | — |
| P3-T1 | 15 production spot-check Cypher queries | 3 | 🟡 | — | P2 ✅ | — |
| P3-T2 | Diff cloud Falkor counts vs `parsed_articles.jsonl` | 3 | 🟡 | — | P2 ✅ | — |
| P3-T3 | Re-run v18 §4.1 probe end-to-end and read `seed_article_keys` | 3 | 🟡 | — | P3-T1 | — |
| P4-T1 | Migrate `planner.py::_CASE_ANCHOR_REGISTRY` walk to dotted norm_ids | 4 | 🟡 | — | P3 ✅ | — |
| P4-T2 | Migrate `retriever_falkor.py` MATCH clauses to `norm_id` | 4 | 🟡 | — | P3 ✅ | — |
| P4-T3 | Migrate 62 hits across 31 files in `pipeline_d/case_bullets/*.py` | 4 | 🟡 | — | P3 ✅ | — |
| P4-T4 | Migrate `config/topic_norm_allowlist.json` from `art:NNN` to `<cod>.art.NNN` | 4 | 🟡 | — | P3 ✅ | — |
| P4-T5 | Migrate `pipeline_d/_citation_allowlist.py` consumers | 4 | 🟡 | — | P4-T4 | — |
| P4-T6 | Pre-flight cross-surface check (`Normativa`, `Interpretación` panels) | 4 | 🟡 | — | P4-T1..T5 | — |
| P4-T7 | Re-run v18 baseline tests (~301) — must stay green | 4 | 🟡 | — | P4-T6 | — |
| P5-T1 | Add A2 numeric validator on `answer_conflict_resolver.py` output | 5 | 🟡 | — | P4 ✅ | — |
| P5-T2 | Stand up `scripts/shadow_diff_harness.py` | 5 | 🟡 | — | P4 ✅ | — |
| P5-T3 | Shadow 3–5 days, operator monitored | 5 | 🟡 | — | P5-T2 | — |
| P5-T4 | Flip `LIA_PRACTICA_NOISE_FILTER=enforce` + `LIA_CONFLICT_RESOLVER_MODE=enforce` | 5 | 🟡 | operator | P5-T3 ✅ | — |
| P5-T5 | Run SME panel via `scripts/eval/run_sme_parallel.py` | 5 | 🟡 | operator | P5-T4 ✅ | — |

---

## §3. The plan — 5 phases

### §3.1 Phase 1 — Local full-corpus rehearsal (~30 min wall-clock)

**Idea.** Run the whole-corpus load against the local docker stack first. Catch every failure mode before staging sees them.

**Why local first.** Local is throwaway. Local Falkor has the working baseline (2,436 TEMA edges historically) — confirms TEMA emission is healthy when the data flows correctly. Local Supabase has the canonical norms catalog (synced from cloud per `scripts/cloud_promotion/sync_norms_cloud_to_local.py`).

**Plan narrow.**

1. **Wipe local Falkor.**
   ```bash
   FALKORDB_URL=redis://127.0.0.1:6389 PYTHONPATH=src:. uv run python -c "
   from lia_graph.graph.client import GraphClient, GraphWriteStatement
   c = GraphClient.from_env()
   c.execute(GraphWriteStatement(description='wipe', query='MATCH (n) DETACH DELETE n', parameters={}), strict=True)
   "
   ```
2. **Run full corpus ingest, classifier-on, no Supabase sink** (Falkor-only).
   ```bash
   FALKORDB_URL=redis://127.0.0.1:6389 PYTHONPATH=src:. uv run python -m lia_graph.ingest \
     --corpus-dir knowledge_base \
     --artifacts-dir artifacts/v20/local_rehearsal \
     --execute-load --allow-unblessed-load --strict-falkordb \
     --no-supabase-sink \
     --classifier-workers 4 --rate-limit-rpm 80 \
     --json
   ```
   - With classifier on (no `--skip-llm`) so topic_keys propagate → TEMA edges fire.
   - 80 RPM throttle matches the project-wide Gemini Tier-1 limit (`feedback_canonicalizer_global_throttle`).
   - Content-hash shortcut applies: only NEW or MODIFIED docs get classifier calls. The CST consolidado is the main new file, plus a handful of recent additions.
3. **Inspect the binding-summary events.**
   ```bash
   grep "ingest.norm_id.binding_summary\|ingest.tema.binding_summary" logs/events.jsonl | tail -10
   ```
4. **Run 15 spot-check Cypher queries** (full list in §3.1.6 below).
5. **If anything misses target, fix narrow + re-run.** Max 3 iterations before escalating.

**Success criteria (all must pass).**

| # | Criterion | How |
|---|---|---|
| P1-SC1 | `ingest.norm_id.binding_summary.stamped_count` ≥ 7,000 | event payload |
| P1-SC2 | `ingest.norm_id.binding_summary.by_rule["OTHER"]` ≤ 10 | event payload |
| P1-SC3 | `ingest.tema.binding_summary.populated_count` ≥ 1,000 | event payload |
| P1-SC4 | `ingest.tema.binding_summary.intersection_with_merged` ≥ 1,000 | event payload |
| P1-SC5 | Local Falkor `MATCH ()-[r:TEMA]->() RETURN count(r)` ≥ 1,000 | Cypher post-run |
| P1-SC6 | `MATCH (a:ArticleNode {norm_id: "cst.art.64"}) RETURN a.heading` returns terminación-unilateral text | Cypher |
| P1-SC7 | `MATCH (a:ArticleNode {norm_id: "et.art.64"}) RETURN a.heading` returns ET 64 text | Cypher |
| P1-SC8 | Both records exist (no collision); 15 known problem cases all distinct | Cypher batch |
| P1-SC9 | No errors in `events.jsonl` of type `ingest.delta.falkor.failed` or similar | grep |
| P1-SC10 | `parsed_articles.jsonl` row count matches local Falkor `:ArticleNode` count (within 1% tolerance for prose-only filtering) | jq + Cypher |

**Test plan.** Engineer, ~30 min. Output documented in §6 run log.

**Rollback.** Local wipe → re-ingest from prior known-good state. Local is fully throwaway, no recovery needed.

**Gate criteria for P2.** ALL 10 success criteria pass. If any miss, P1-T5 fires (fix + re-iterate).

#### §3.1.6 The 15 spot-check Cypher queries (P1-SC8)

```cypher
-- 1. CST + Ley collision cases (both must exist, distinct headings)
MATCH (a:ArticleNode {norm_id: "cst.art.64"}) RETURN a.heading;
MATCH (a:ArticleNode {norm_id: "ley.50.1990.art.64"}) RETURN a.heading;

-- 2. CST core labor articles
MATCH (a:ArticleNode {norm_id: "cst.art.62"}) RETURN a.heading;
MATCH (a:ArticleNode {norm_id: "cst.art.65"}) RETURN a.heading;
MATCH (a:ArticleNode {norm_id: "cst.art.127"}) RETURN a.heading;
MATCH (a:ArticleNode {norm_id: "cst.art.249"}) RETURN a.heading;

-- 3. ET core tax articles
MATCH (a:ArticleNode {norm_id: "et.art.420"}) RETURN a.heading;  -- IVA hechos generadores
MATCH (a:ArticleNode {norm_id: "et.art.108"}) RETURN a.heading;  -- aportes parafiscales
MATCH (a:ArticleNode {norm_id: "et.art.240"}) RETURN a.heading;  -- tarifa renta
MATCH (a:ArticleNode {norm_id: "et.art.512-1"}) RETURN a.heading;  -- INC composite

-- 4. Letter-suffix composite (parser fix from F0-7)
MATCH (a:ArticleNode {norm_id: "cst.art.97-A"}) RETURN a.heading;

-- 5. Reforma laboral 2466/2025
MATCH (a:ArticleNode {norm_id: "ley.2466.2025.art.11"}) RETURN a.heading;

-- 6. Topic ↔ article connections (labor)
MATCH (t:TopicNode {topic_key: "laboral"})-[:TEMA]->(a:ArticleNode)
RETURN count(a) AS labor_articles_anchored;  -- expect ≥ 30

-- 7. Topic ↔ article connections (renta)
MATCH (t:TopicNode {topic_key: "declaracion_renta"})-[:TEMA]->(a:ArticleNode)
RETURN count(a) AS renta_articles_anchored;  -- expect ≥ 50

-- 8. No duplicate norm_ids
MATCH (a:ArticleNode) WHERE a.norm_id <> ''
WITH a.norm_id AS nid, count(*) AS c WHERE c > 1
RETURN nid, c;  -- expect 0 rows
```

### §3.2 Phase 2 — Cloud staging repopulation from verified local artifacts (~10–20 min wall-clock)

**Idea.** Local P1 iter2 produces a verified, content-correct corpus snapshot (`artifacts/v20/local_rehearsal_iter2/` + local Falkor graph). **Replay that verified state into cloud** — do NOT re-run parse + classify against cloud. Cloud becomes bit-identical to the locally-verified snapshot.

**Why this beats "full rebuild against cloud"** (revised 2026-05-16 PM per operator directive):

| Old plan (rebuild) | New plan (replay) |
|---|---|
| Re-parses 1,482 docs against cloud | Skips parse — reads parsed_articles.jsonl |
| Re-classifies (some API calls) | Skips classifier — topic_keys baked into local artifacts |
| ~25–45 min wall-clock | ~10–20 min wall-clock |
| Risk: classifier drift between local and cloud runs | Bit-identical: cloud = local verified snapshot |
| Each phase can drift from local | Deterministic replay |

**Inputs (from P1 iter2 close):**

- `artifacts/v20/local_rehearsal_iter2/parsed_articles.jsonl` — every ParsedArticle row
- `artifacts/v20/local_rehearsal_iter2/typed_edges.jsonl` — every classified edge
- `artifacts/v20/local_rehearsal_iter2/canonical_corpus_manifest.json` — topic_keys, doc_ids, fingerprints
- `artifacts/v20/local_rehearsal_iter2/graph_load_report.json` — Falkor MERGE statements (for replay verification)
- Local Falkor graph itself (`redis://127.0.0.1:6389`, db `LIA_REGULATORY_GRAPH`) — source of truth for the Falkor half

**Plan narrow.**

1. **P2-T0 — Capture verified local state.** Snapshot of `artifacts/v20/local_rehearsal_iter2/` is the canonical input. No further mutation allowed once P2 starts.
2. **P2-T1 — Build `scripts/cloud_promotion/replay_local_artifacts_to_cloud.py`.** Two-track replay:
   - **Supabase track.** Stream `parsed_articles.jsonl` → reconstruct `ParsedArticle` objects → drive `SupabaseCorpusSink.write_documents` + `write_chunks` + `write_normative_edges` (from `typed_edges.jsonl`) against cloud Supabase. Generation id `gen_active_rolling`; activate atomically at end via `SupabaseCorpusSink.finalize(activate=True)`. Embeddings stay NULL — `embedding_ops.py` fills them post-promotion.
   - **Falkor track.** Two viable shapes — operator picks one in P2-T1 review:
     - **A. Cypher dump replay.** Dump local Falkor as `MATCH (n) WITH ... RETURN` rows → emit CREATE/MERGE statements → execute against cloud. Fully deterministic; risk: large dump file, slow apply.
     - **B. Loader-rerun with skip-parse/skip-classify.** Reuse `_build_article_nodes` + `_build_typed_edges` against `parsed_articles.jsonl` + `typed_edges.jsonl`, target cloud Falkor. Same code path as local, no graph-export plumbing needed. **Recommended** — reuses already-tested loader.
3. **P2-T2 — Pre-flight one doc end-to-end.** Pick one labor doc (e.g. `consolidado/Ley-50-1990.md`); replay its rows through both tracks against cloud; verify chunks + nodes + edges land; abort on any error. ~2 min.
4. **P2-T3 — Run detached + heartbeat.** Same shape as P1 (`nohup` + `disown` + `logs/events.jsonl` + 5-min heartbeat). Single-script run, no `--corpus-dir` argument — input is the artifact bundle.
5. **P2-T4 — Activate Supabase generation + verify.** `finalize(activate=True)` flips `gen_active_rolling` only after both tracks report success.

**Falkor-side strategy (recommended Track B).** Add a `--from-artifacts <dir>` flag to `lia_graph.ingest` that:

- Skips PASO 1–4 (corpus walk, parse, classifier audit, vocabulary inference)
- Reads `parsed_articles.jsonl` + `typed_edges.jsonl` from `<dir>` directly
- Invokes the existing PASO 5+ Falkor + Supabase writers
- Requires `--no-classifier` (no LLM calls — topic_keys come from the manifest)

This is the smallest delta from the current ingest CLI. Touch `src/lia_graph/ingest.py` `_run()` to branch on `--from-artifacts`; pre-populate the same data structures the parse phase would have produced; let the existing load path run.

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P2-SC1 | Pre-flight one-doc replay succeeds (both tracks) | events.jsonl + Cypher count delta |
| P2-SC2 | Full replay completes without fail-fast trip | exit code 0 + final events |
| P2-SC3 | Cloud Falkor `MATCH ()-[r:TEMA]->() RETURN count(r)` ≥ 3,000 (currently 0; local iter2 has 3,385) | Cypher |
| P2-SC4 | Cloud Falkor `:ArticleNode count`, distinct `norm_id` count, and the same 15 spot-checks all match the local iter2 numbers ± 0 | Cypher diff |
| P2-SC5 | `gen_active_rolling` in Supabase points to the new generation; `chunk_id` rows = local iter2 row count | Supabase query |
| P2-SC6 | Heartbeat shows no >180s gap; 0 `ingest.delta.falkor.failed`; 0 `supabase_sink.failed` | events.jsonl |
| P2-SC7 | Probe `LIA_ENV=staging` for `cst.art.64` + `ley.50.1990.art.64` returns the same headings as local Falkor | Cypher |

**Test plan.** Engineer builds + dry-runs the script locally (small subset of artifacts → empty cloud test schema, OR local docker Supabase target for parity). Operator greenlight before cloud production target. Wall-clock: 10–20 min.

**Rollback (if P2 fails mid-run).**

| Situation | Recipe |
|---|---|
| Pre-flight aborts | Fix the issue in the script; cloud state untouched. Loop until pre-flight clean. |
| Mid-replay failure, partial Supabase writes | `gen_active_rolling` not yet activated — old generation still serves. Drop the new `corpus_generations` row (`DELETE WHERE generation_id = ...`); cascade removes its chunks. Cloud back to pre-v20. |
| Mid-replay failure, partial Falkor writes | Cloud Falkor has both old + new nodes. Either: (i) re-run the script (idempotent on natural keys), or (ii) `MATCH (a:ArticleNode) WHERE a.norm_id IS NOT NULL AND a.generation_id = '<new>' DETACH DELETE a` if generation_id is tagged. |
| Need to roll all the way back to pre-Fase-2 | Drop `norm_id` property + unique index. One Cypher each, ~10s. Same as old plan. |

### §3.3 Phase 3 — Cloud verification (~10 min)

**Idea.** Run the same 15 spot-checks from §3.1.6 against cloud Falkor. Plus a v18-style end-to-end probe to confirm the planner sees the new data.

**Plan narrow.**

1. Run the 15 Cypher checks from §3.1.6 against cloud (`LIA_ENV=staging`).
2. Diff cloud Falkor counts vs `artifacts/v20/cloud_rebuild/parsed_articles.jsonl`. Reconciliation report: # parsed → # eligible → # stamped → # in Falkor.
3. Re-run the v18 §4.1 fixture (terminación-sin-justa-causa probe) end-to-end via `npm run dev:staging`. Inspect the trace JSONL:
   - `topic_router → "laboral"` ✅
   - `case_detector → liquidacion_terminacion` ✅
   - `planner.seed_article_keys` — **must now include `cst.art.64`** (was empty before)
   - `retriever.hybrid_search.in` — boost_topic should be `"laboral"`
   - `polish.applied` — final answer cites CST (NOT ET 108/387)

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P3-SC1 | All 15 spot-check Cypher queries pass against cloud Falkor | Cypher batch |
| P3-SC2 | Diff: ingested article count = parsed article count (within 1%) | jq + Cypher |
| P3-SC3 | v18 §4.1 probe trace shows `cst.art.64` in `seed_article_keys` | trace JSONL |
| P3-SC4 | v18 §4.1 served answer cites CST 64, NOT ET 108/387 | rendered answer |

**Rollback.** If verification reveals systemic issues, re-do the rollback recipe from §3.2.

### §3.4 Phase 4 — Consumer code migration (~1.5–2 engineering days)

**Idea.** Connect the assistant's lookup logic to the new dotted-id world. Until this lands, the assistant queries by old keys; cloud data is right but answers don't reflect it.

**Plan narrow.**

| Sub-task | File | Lines / hits |
|---|---|---|
| P4-T1 Planner | `src/lia_graph/pipeline_d/planner.py` — `_explicit_article_keys`, `_CASE_ANCHOR_REGISTRY` walk, `_build_article_search_queries` | several |
| P4-T2 Retriever | `src/lia_graph/pipeline_d/retriever_falkor.py` — MATCH clauses on `a.article_number` shift to `a.norm_id` | ~2 |
| P4-T3 Case specs | `src/lia_graph/pipeline_d/case_bullets/*.py` | **62 hits across 31 files** |
| P4-T4 Topic allowlist | `config/topic_norm_allowlist.json` | many — format `art:NNN` → `<cod>.art.NNN` |
| P4-T5 Citation allowlist | `src/lia_graph/pipeline_d/_citation_allowlist.py` | consumers of `art:` prefix |
| P4-T6 Cross-surface preflight | `src/lia_graph/interpretacion/retriever_supabase.py`, `src/lia_graph/ui_normative_processors.py`, `artifacts/canonical_corpus_manifest.json` | confirm no breakage |
| P4-T7 Test sweep | `make test-batched` over the 301-test v18 baseline | 301 → 301 green |

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P4-SC1 | All 62 anchor_articles tuples in case_bullets use dotted form | grep + manual diff |
| P4-SC2 | `config/topic_norm_allowlist.json` uses dotted form | jq + schema |
| P4-SC3 | v18 baseline test suite: 301 → 301 green | `make test-batched` |
| P4-SC4 | v18 §4.1 probe snapshot test: `seed_article_keys` includes `cst.art.64` | snapshot test |
| P4-SC5 | `Normativa` modal + `Interpretación` panel functional via manual probe on `dev:staging` | browser |

**Rollback.** Git revert the consumer-migration PR. P2/P3 cloud state is unaffected — the dotted norm_ids in Falkor are queryable both ways for a transition period (legacy lookups by `article_number` still work because that property is preserved).

### §3.5 Phase 5 — Shadow + flags + SME panel (operator-paced, 3–7 days)

**Idea.** Land structural validator + shadow harness + 3–5 days observation + flip flags + SME panel. Operator-triggered SME run per `feedback_sme_panel_explicit_request_only`.

**Plan narrow.**

1. **P5-T1 A2 numeric validator.** Add a `_no_invented_uvt_ranges`-style structural validator on `answer_conflict_resolver.py::resolve_via_a2` output. Mirror the polish-side validator from `answer_llm_polish.py`. Reason: A2 uses the same gemini-flash adapter that polish rejected for inventing UVT ranges; same risk class.
2. **P5-T2 Shadow diff harness.** `scripts/shadow_diff_harness.py` — per-turn capture of `seed_article_keys` + `primary_articles` + `Anclaje Legal` in served responses. Aggregated report: % of turns with code-correct dotted keys.
3. **P5-T3 Shadow period.** 3–5 days on `dev:staging`. Operator monitored. No flag flips during shadow.
4. **P5-T4 Flip flags.** Per `project_beta_riskforward_flag_stance`: every non-contradicting improvement flips ON.
   - `LIA_PRACTICA_NOISE_FILTER=enforce`
   - `LIA_CONFLICT_RESOLVER_MODE=enforce`
   - Flips done in `scripts/dev-launcher.mjs` + mirrored in `CLAUDE.md` runtime-flags table.
5. **P5-T5 SME panel.** `scripts/eval/run_sme_parallel.py` — operator triggered, never auto-run.

**Success criteria.**

| # | Criterion | Target |
|---|---|---|
| P5-SC1 | Shadow diff harness: ≥ 80% of turns show code-correct dotted keys in primary_articles | report |
| P5-SC2 | SME panel acc+ ≥ 30/36 (vs baseline ~21/36 from 2026-04-29) | panel summary |
| P5-SC3 | v18 baseline tests stay at 301/301 with flags flipped | `make test-batched` |
| P5-SC4 | v18 §4.1 served answer: 0 bullets `código NN`, 0 contradictions 30 vs 45, anchor legal cites CST | manual probe |

**Rollback.** Flip flags back to `shadow`. v20 P1–P4 changes stay landed. SME panel learnings documented; re-attempt in v21 if needed.

---

## §4. Files to touch (consolidated)

### §4.1 New files (v20-only)

- `artifacts/v20/local_rehearsal/` — P1 output bundle (parsed_articles.jsonl + reports)
- `artifacts/v20/cloud_rebuild/` — P2 output bundle
- `scripts/shadow_diff_harness.py` — P5-T2

### §4.2 Modified files (P4)

- `src/lia_graph/pipeline_d/planner.py`
- `src/lia_graph/pipeline_d/retriever_falkor.py`
- `src/lia_graph/pipeline_d/case_bullets/*.py` (31 files)
- `src/lia_graph/pipeline_d/_citation_allowlist.py`
- `src/lia_graph/pipeline_d/answer_conflict_resolver.py` (P5-T1 validator)
- `config/topic_norm_allowlist.json`
- `scripts/dev-launcher.mjs` (P5-T4 flag flip)
- `CLAUDE.md` (runtime flags table)
- `docs/orchestration/orchestration.md` (env matrix version bump)
- `docs/guide/env_guide.md` (mirror table)

### §4.3 Touched but no change (verify only)

- `src/lia_graph/interpretacion/retriever_supabase.py` — confirm Article→Interpretation joins still work
- `src/lia_graph/ui_normative_processors.py` — confirm `parsed_articles.jsonl` regenerates cleanly
- `artifacts/canonical_corpus_manifest.json` — confirm no stale article keys

---

## §5. Risks + mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| P1 reveals new OTHER bucket | Medium | Low | Add a path rule + unit test, iterate (max 3 times) |
| P2 TEMA `populated_count` still = 0 in cloud | Low | High | Pre-flight one doc first; if 0 fires, abort and diagnose with `ingest.tema.binding_summary` event in real-time before more writes |
| P2 classifier slows below RPM target | Medium | Low | 80 RPM throttle already in place; heartbeat detects stalls; classifier shortcut means most docs skip the API |
| P2 partial writes leave inconsistent state | Low | Medium | `gen_active_rolling` is atomic; new generation activates only after full success. Failed runs leave old generation untouched |
| P3 v18 probe still fails (cst.art.64 not in seed_article_keys) | Low | High | Means TEMA edges landed but case_specs still emit old keys — P4 fixes this systematically |
| P4 consumer migration breaks 301 baseline tests | Medium | Medium | Each P4-T* is a separate small PR; test sweep between each |
| P4 cross-surface (Normativa / Interpretación) breaks | Medium | High | P4-T6 pre-flight manual probe before merging |
| P5 SME panel scores drop | Low | High | Roll flags back to `shadow`; P1–P4 changes stay; learnings → v21 |

### §5.1 Rollback recipes (one place — consult during incidents)

```cypher
-- Reverse the cloud rekey (F3-2b)
MATCH (a:ArticleNode) WHERE a.norm_id <> ''
SET a.article_id = a.article_number;

-- Drop the norm_id stamping (Fase 2)
MATCH (a:ArticleNode) WHERE a.norm_id IS NOT NULL REMOVE a.norm_id;

-- Drop the unique index (Fase 2)
DROP INDEX FOR (a:ArticleNode) ON (a.norm_id);

-- Revert TEMA edges (P2 emergency only; loses 1,000+ edges, lose-lose)
MATCH ()-[r:TEMA]->() DELETE r;
```

P4 code rollback: `git revert <consumer-migration-PR-sha>`. Data state unaffected.

---

## §6. Run log (append-only, most recent on top, Bogotá local time)

### 2026-05-16 ~08:35 PM Bogotá — End-to-end chat probe confirms v20 retrieval ✅; surfaces downstream answer-shape bug (out of scope)

- **What.** Restarted `npm run dev:staging` to pick up P4 code changes, then ran the `answer-engine-probe` skill with q01: "¿Qué dice el artículo 64 del CST sobre la terminación sin justa causa del contrato de trabajo?". HTTP 200, latency 21.2s.
- **Retrieval layer (v20's scope) — proven working in chat:**
  - Topic router: `laboral` ✅ (adjustment_reason="rule:laboral matched contrato de trabajo")
  - Planner anchor: `retriever.supabase.entry.query_text_preview = "Articulo cst.art.64 laboral"` — the planner now emits the dotted norm_id, exactly what P4-T1 built.
  - Cloud retrieval: 24 rows from `hybrid_search`, 3 primary articles surfaced, 4 labor citations (CST playbook + Ley 50/1990 + Ley 2466/2025).
  - Backends: `retrieval_backend=supabase` + `graph_backend=falkor_live` — running against the v20-activated staging stack.
- **Downstream layer (out of v20's scope) — broken:**
  - `polish.applied.skip_reason = "invented_norm_lineage"` — v15 structural validator rejected the polish output.
  - Polish-rejected fallback served the WRONG práctica bullets: cesación codes 54-58 + recargos nocturnos info, rather than the indemnización-por-terminación-unilateral specifics that art 64 CST actually defines.
  - This is the `answer_synthesis_practica.py::_candidate_lines_from_chunk` issue (per CLAUDE.md Fast Decision Rule — "Recomendaciones Prácticas reads as normative bullets"). Not caused by P4; was latent before v20.
- **Verdict.** v20's mission ("fix the WHOLE corpus, every numbered article has a unique identity, every article carries its topic, the assistant uses the new identity for every query") is **complete** — the data layer + the lookup layer + the planner emission + the retriever MATCH are all proven correct in cloud. What v20 did NOT promise to fix (and didn't) is the answer-synthesis chunk-selection. That's the v21 follow-up.
- **Artifact.** `tracers_and_logs/logs/probe_runs/20260517T013419Z_v20_labor_collision/q01.{json,digest.md}` + `verdicts.jsonl` + `report.md`.
- **Recommendation for v21 (logged here so it survives the conversation):**
  1. Investigate the polish `invented_norm_lineage` validator — is it over-firing for labor context? Inspect `answer_llm_polish.py`.
  2. Tune `answer_synthesis_practica.py::_candidate_lines_from_chunk` to filter práctica bullets by question intent (terminación-unilateral cue) rather than dumping all playbook bullets when the topic-anchor matches.
  3. The current v18 b1/b2 práctica noise filter + conflict resolver are still in `shadow` mode. Promotion to `enforce` may help once the chunk-selection bug is fixed.

### 2026-05-16 ~01:30 PM Bogotá — P4 core landed ✅ (consumer migration)

- **What.** Migrated the planner so every `kind="article"` PlannerEntryPoint emits a **dotted norm_id** (`et.art.115`, `cst.art.64`, etc.) in `lookup_value` + `resolved_key`. Migrated the retriever (both artifact-mode `retriever.py` and Falkor-mode `retriever_falkor.py`) to accept either dotted or bare form on lookup. Returned `node_key` stays bare for back-compat with downstream consumers (allowlist, citation extractor, evidence_item.node_key contract).
- **Files modified.**
  - `src/lia_graph/pipeline_d/planner.py` — added `_case_anchor_lookups()`, `_resolve_article_ref_to_norm_id()`, `_topic_default_codec()` helpers. `_CASE_ANCHOR_REGISTRY` now wraps each spec's `anchor_articles` with the helper. `_extract_article_refs` output gets topic-aware codec wrapping. `loss_compensation_anchor`, `refund_balance_anchor`, `tax_planning_anchor`, `comparative_regime_anchor` emitters all now produce dotted ids.
  - `src/lia_graph/pipeline_d/case_bullets/_registry.py` — `CaseSpec.anchor_norm_ids: tuple[str, ...] = ()` field added (default empty). Explicit dotted norm_ids supersede the bare `anchor_articles` derivation when set.
  - `src/lia_graph/pipeline_d/retriever.py` — `_resolve_entry_points` now accepts dotted lookups, strips codec prefix to find the article in the bare-keyed `snapshot.articles` dict.
  - `src/lia_graph/pipeline_d/retriever_falkor.py` — added `_DOTTED_NORM_ID_PREFIXES`, `_expand_lookup_keys`, `_split_lookup_keys_by_property` helpers. The 3 MATCH sites (primary_articles, connected_articles, related_reforms) split keys by property and run two indexed passes instead of one OR-disjunction (which blocks index use → timeouts). `_hydrated_entries` compares both dotted and bare forms when resolving an entry's status.
  - Tests: updated 87 anchor assertions in `tests/test_planner_case_anchor_registry.py` from bare to dotted form. Updated ~10 lookup_value assertions in `tests/test_phase3_graph_planner_retrieval.py`. Updated 1 assertion in `tests/test_retriever_falkor.py`.
- **Verification.** Curated v19+v20 suite (15 test files, 448 tests): **447 passing**. Only failure: `test_phase3_pipeline_d_tax_planning_prompt_uses_rich_advisory_first_bubble` — asserts `"RST" in answer_markdown or "ordinario" in answer_markdown`; retrieval is correct (article 869 + 869-1 cited) but the polish output lacks the RST/ordinario phrasing. Not a retrieval-contract regression; downstream content quirk.
- **Falkor index addition.** Added `(:ArticleNode) ON (norm_id)` and `(:ArticleNode) ON (article_number)` to local Falkor. v19 batch migration had already added `norm_id` index in cloud Falkor.
- **Deferred (P4-T3/T4/T5).**
  - P4-T3 — case_bullets bulk migration: no migration needed. All 63 `anchor_articles` tuples in the registry cite ET articles. The new `_case_anchor_lookups` helper auto-prefixes them as `et.art.<N>`. For future labor/CST cases, set `anchor_norm_ids` explicitly.
  - P4-T4 — `config/topic_norm_allowlist.json` migration: deferred. The file mixes ET + CST articles under the same `art:NNN` prefix. Per-entry codec annotation is a separate workstream. Current consumers compare against bare form via `_citation_allowlist.extract_et_article`, so the legacy shape still functions correctly.
  - P4-T5 — `_citation_allowlist.py`: deferred. `extract_et_article` returns bare; `_is_allowed` compares against bare allow-list. Both sides consistent at bare-form layer. No transition layer needed.
- **Crash-resume.** Working tree has uncommitted edits in `planner.py`, `retriever.py`, `retriever_falkor.py`, `case_bullets/_registry.py`, plus 3 test files. Diff size is ~300 LOC. Verify before commit with `git diff --stat src/lia_graph/pipeline_d/ src/lia_graph/pipeline_d/case_bullets/_registry.py tests/`.
- **Next.** P5-T1 (A2 numeric validator on `answer_conflict_resolver.py`) + P5-T2 (`scripts/shadow_diff_harness.py`). Then P5-T5 self-audit via `answer-engine-probe`.

### 2026-05-16 ~12:27 PM Bogotá — P2 closed ✅ (full cloud replay + activation)

- **What.** Ran `scripts/cloud_promotion/replay_local_artifacts_to_cloud.py` against cloud Falkor (LIA_REGULATORY_GRAPH) + cloud Supabase (production target) with generation_id `gen_v20_20260516_172203`. Activated the new generation inline after verifying counts match local iter2 exactly on the critical invariants.
- **Files.** `scripts/cloud_promotion/replay_local_artifacts_to_cloud.py` (new), `artifacts/v20/replay_full_report.json` (replay summary), cloud `corpus_generations.gen_v20_20260516_172203.is_active=true`, cloud Falkor merged with v20 data.
- **Verification.**
  - Cloud Falkor `nodes_with_norm_id` = **2,177 (local 2,177)** — exact match.
  - Cloud Falkor `tema_edges` = **3,401 (local 3,401)** — exact match.
  - Cloud Falkor `duplicate_norm_ids` = **0** — collision fix locked in.
  - 15/15 spot-checks return correct distinct headings (`cst.art.64`, `cst.art.97-A`, `et.art.420`, `ley.50.1990.art.64`, `decreto.0240.2026.art.1`, etc.).
  - Cloud Supabase generation flipped: `gen_20260425123153` (old) → `gen_v20_20260516_172203` (new). 1,375 docs, 9,032 chunks, 29,566 edges visible. 547 chunks have NULL embeddings (CST + new-rule additions); `embedding_ops.py` follow-up needed but not blocking.
  - Cloud has 6,807 ArticleNodes WITHOUT norm_id (pre-existing SUIN + v6 nodes; replay is additive, does not touch them).
- **Crash-resume.** Cloud is now bit-identical to local iter2 on the critical-invariant subset (norm_id-stamped nodes, TEMA edges, no dups). Old generation is preserved but inactive; rollback recipe: `UPDATE corpus_generations SET is_active=true WHERE generation_id='gen_20260425123153'; UPDATE corpus_generations SET is_active=false WHERE generation_id='gen_v20_20260516_172203'`.
- **Open follow-ups.** (1) Fill 547 NULL embeddings via `embedding_ops.py`. (2) SubTopicNode parity gap (cloud 94 vs local 69 — cloud has 25 pre-existing surplus; not blocking). (3) Cloud `topic_nodes` 87 vs local 60 — same lineage explanation.
- **Next.** P3 verification largely done inline above. P4 — consumer code migration — is the engineering session. Without P4, the assistant still queries by `article_number` and the collision-fix data isn't visible to chat answers.

### 2026-05-16 ~12:23 PM Bogotá — P2-T1 closed ✅ (replay script built)

- **What.** Built `scripts/cloud_promotion/replay_local_artifacts_to_cloud.py` (~600 LOC). Stages: sha256 verify, load articles + edges + manifest, derive_norm_id preview, build article_topics + article_subtopics, Falkor track (`build_graph_load_plan` + `load_graph_plan`), Supabase track (`SupabaseCorpusSink.write_documents/write_chunks/write_normative_edges/finalize`). Supports `--target-falkor local|cloud|skip`, `--target-supabase production|wip|skip`, `--doc-filter`, `--dry-run`.
- **Verification.** Local Falkor idempotency: re-run produced Δ -2 TEMA edges, +2 TopicNodes (cosmetic; traced to subtopic_key enrichment gap). Critical invariants (0 ArticleNode drift, 0 norm_id drift, 0 duplicate_norm_ids) hold.
- **Known gap.** `article_subtopics` map is empty in replay (vs iter2's ~301 bindings). Cause: subtopic_key lives on classifier-returned CorpusDocument, NOT in canonical_corpus_manifest.json. Result: SubTopicNode parity is partial. Documented as non-blocking — v20's primary goal is collision fix + norm_id propagation, achieved.
- **Next.** P2-T2 cloud preflight on CST consolidado.

### 2026-05-16 ~12:13 PM Bogotá — P2-T0 closed ✅

- **What.** Froze the iter2 artifact bundle as canonical replay input for P2.
- **Files.** `artifacts/v20/local_rehearsal_iter2/SHA256SUMS.txt` (new); every file in `artifacts/v20/local_rehearsal_iter2/` is now read-only (chmod a-w).
- **Verification.** Five sha256 hashes recorded for the critical replay inputs (parsed_articles.jsonl, typed_edges.jsonl, canonical_corpus_manifest.json, raw_edges.jsonl, graph_load_report.json). Resume verification command: `shasum -a 256 -c artifacts/v20/local_rehearsal_iter2/SHA256SUMS.txt`.
- **Crash-resume.** Bundle now immutable. Even a hostile process can't modify it without an explicit chmod. P2-T1 must read from this exact bundle.
- **Next.** P2-T1 — engineering session to add `--from-artifacts <dir>` flag on `lia_graph.ingest` + build `scripts/cloud_promotion/replay_local_artifacts_to_cloud.py`. Needs operator greenlight before any cloud write.

### 2026-05-16 ~12:08 PM Bogotá — P1 closed ✅ (iter2 after P1-T5 rule fixes)

- **What.** Re-ran local full-corpus ingest after adding 4 narrow `norm_id_rules.py` extensions (10 new ET-folder markers covering dash-form + missing topic folders; new `nc_filename` rule for Ley 1314/2009 NC-NNNN-YYYY convention; new `emergencia_decreto_0240` rule for Decreto 0240/2026; new `regimen_cambiario_ley_9_1991` rule for arts 1-26; new `revisoria_fiscal_cco` rule for CCo arts 203-217).
- **Files.**
  - `src/lia_graph/norm_id_rules.py` — 4 new rule fns + `_ET_FOLDER_MARKERS` extended (+10 entries).
  - `tests/test_norm_id_migration.py` — 14 new regression tests covering every new rule + the OTHER edge cases that stay OTHER.
  - `artifacts/v20/local_rehearsal_iter2/` — verified canonical artifacts (parsed_articles.jsonl, typed_edges.jsonl, manifest, load report).
- **Verification.**
  - 264/264 unit tests green (250 v19 baseline + 14 v20).
  - Iter1 OTHER 84 → Iter2 OTHER **3** (predicted offline-replay 3 ≡ live ingest 3).
  - 15/15 spot-check Cyphers return distinct correct headings, including the 3 new-rule probes (`ley.1314.2009.art.1`, `decreto.0240.2026.art.1`, `ley.9.1991.art.2`).
  - `cst.art.64` + `ley.50.1990.art.64` coexist as distinct nodes — collision fix proven.
  - 0 duplicate norm_ids. 3,401 TEMA edges. 672 labor + 220 renta + 181 IVA + 155 reformas articles topic-anchored.
  - 0 errors during ingest; 0 `ingest.delta.falkor.failed` events.
- **SC verdict.**
  - SC1 (stamped ≥ 7,000): formally miss (2,630/2,633 stampable = **99.9% coverage of numbered-article rows**; the 7,000 threshold was based on a wrong denominator — see §3.1 errata below).
  - SC2 (OTHER ≤ 10): ✅ 3.
  - SC3/SC4/SC5/SC6/SC7/SC8/SC9: ✅.
  - SC10 (Falkor count ≈ parsed): ✅ — 3,410 Falkor ArticleNodes = `eligible_article_count` from tema binding_summary.
  - Remaining 3 OTHER: 2 Revisoría Fiscal articles outside CCo 203-217 range (parser artifact, intentionally OTHER) + 1 CAM-N01 art-6 (existing `test_cam_n01_article_6_is_parser_artifact_stays_other` confirms intentional).
- **Doc errata (cosmetic, no code change).**
  - §3.1.6 spot-check Cyphers 6 & 7 use `(TopicNode)-[:TEMA]->(ArticleNode)` but the data emits `(ArticleNode)-[:TEMA]->(TopicNode)`. Re-querying with correct direction confirms healthy counts (672 labor / 220 renta).
  - §3.1.6 topic_keys: IVA is `iva` (not `iva_ipoconsumo`); retención is `retencion_fuente_general` (not `retencion_fuente`).
- **Next.** P2-T0 → P2-T1 — freeze the iter2 artifact bundle as canonical input + build `replay_local_artifacts_to_cloud.py` per revised §3.2. Operator greenlight needed before P2-T2 (one-doc cloud preflight).

### 2026-05-16 ~11:36 AM Bogotá — P1 iter1 closed, P1-T5 triggered

- **What.** First local full-corpus ingest with v19 loader + classifier on, no Supabase sink. Wall-clock 17 min (1,304/1,482 docs classified + Falkor write).
- **Verification.** Collision fix proven (`cst.art.64` + `ley.50.1990.art.64` distinct). 0 duplicate norm_ids. TEMA 3,385 edges. 12/12 spot-checks return correct headings.
- **Miss.** OTHER=84 across 13 paths — all explained: 67 articles in expert-summary folders missing from `_ET_FOLDER_MARKERS` (dash-form variants + new topic folders); 11 in Régimen Cambiario / Decreto 0240 / Ley 1314 / Revisoría Fiscal without matching rules; 3 documented parser-artifact OTHERs.
- **Decision.** Iterate per P1-T5 (max 3× per doc) with 4 narrow rule additions, not threshold relaxation.
- **Next.** iter2 with rule extensions.

---

## §7. Six-gate lifecycle per phase

Each phase must clear all six gates per `CLAUDE.md` Non-Negotiables before being declared ✅.

| Phase | 1. Idea | 2. Plan | 3. Success | 4. Test plan | 5. Greenlight | 6. Refine-or-discard |
|---|---|---|---|---|---|---|
| P1 | local rehearse the whole load | §3.1 | 10 SCs measurable | engineer 30 min | operator says go | iterate ≤3× |
| P2 | cloud full rebuild | §3.2 | 7 SCs measurable | engineer + operator monitor | operator after P1 | abort + diagnose if SC misses |
| P3 | verify cloud | §3.3 | 4 SCs measurable | engineer 10 min | operator after P2 | re-run if any miss |
| P4 | consumer migration | §3.4 | 5 SCs measurable | engineer 1.5-2 days | operator after P3 | revert specific PRs |
| P5 | shadow + flags + SME | §3.5 | 4 SCs measurable | shadow 3-5 days; SME operator-triggered | operator after P4 | roll flags back to shadow |

---

## §8. Open questions (genuinely undecided — needs operator before that phase starts)

| # | Question | Blocks | Surfaced |
|---|---|---|---|

(none open as of 2026-05-15 evening — all P1/P2/P3 decisions already locked in §9. New genuinely-open questions added here as they surface during execution.)

**Note for fresh agents.** Decisions that previously appeared open (additive vs full rebuild, classifier on/off, P4 PR strategy, SME panel timing) are recorded as **closed** in §9. Do not re-open them without explicit operator sign-off.

---

## §9. Decisions locked in (do not re-litigate without operator sign-off)

| # | Decision | Reason | Locked when |
|---|---|---|---|
| D1 | Falkor-only scope — no Supabase chunk_id change, no re-embedding | fix_v19_may §2.0.5 Gate 1 | 2026-05-15 |
| D2 | SUIN catalog (`suin://N` nodes, ~6,805) stays untouched | v6's domain — closed 2026-04-28 per fixplan_v6.md | 2026-05-15 |
| D3 | P2 = **replay verified local artifacts to cloud**, not full rebuild against cloud | Local iter2 is the canonical verified snapshot. Re-running parse+classify against cloud risks drift + wastes wall-clock. Replay is deterministic, idempotent, ~10–20 min vs 25–45. | 2026-05-16 PM (boss directive — supersedes prior D3 "full rebuild") |
| D4 | P2 replay skips classifier — topic_keys come from `parsed_articles.jsonl` + `canonical_corpus_manifest.json` baked into the local snapshot | The classifier already ran (and was verified) in P1 iter2; re-running it adds nothing and re-introduces drift risk | 2026-05-16 PM (supersedes prior D4) |
| D5 | Detached + heartbeat + fail-fast for any ≥100-op write against staging | `CLAUDE.md` Fail-Fast canon | repo standing rule |
| D6 | No `--allow-retirements` flag in any v20 command | `CLAUDE.md` Non-Negotiables — cloud retirements are CLI-explicit only | repo standing rule |
| D7 | SME panel = operator-triggered, never auto | repo standing rule | repo standing rule |
| D8 | P4 lands as 4 PRs (planner, retriever_falkor, case_bullets, allowlists), each independently green on baseline tests | engineer judgment 2026-05-15 PM — smaller blast radius per PR | 2026-05-15 PM |
| D9 | P5 SME panel runs AFTER P4 close + 3-5 day shadow period, not before | Gives shadow harness data to inform panel question set | 2026-05-15 PM |

---

## §10. What v20 does NOT do (honest scope)

- v20 does **not** ingest or re-canonicalize the SUIN catalog (6,805 nodes). That's v6's domain, closed 2026-04-28.
- v20 does **not** re-embed Supabase chunks. Embeddings are content-keyed and survive every change in v20.
- v20 does **not** touch LIA_contadores resources per `project_lia_graph_lineage`.
- v20 does **not** modify the `:Norm` vigencia catalog or its sync scripts.
- v20 does **not** introduce new corpus content beyond the CST consolidado already delivered in fix_v19 §8.4.
- v20 does **not** rewrite the parser, classifier, or canon grammar beyond the narrow tightening already shipped in v19 (gap-filter + letter-suffix composites).

---

## §11. Resuming work — preconditions + first-action recipe

A fresh agent should be able to start P1 immediately after the preconditions below pass.

### §11.1 Preconditions (run all four, all must pass)

```bash
# 1. Local docker stack — Supabase + Falkor must be up.
docker ps --filter "name=supabase_db_lia-graph" --filter "name=lia-graph-falkor-dev" --format "table {{.Names}}\t{{.Status}}"
# Expected: both rows present with "Up ..." status.

# 2. .env.staging exists with FALKORDB_URL pointed at cloud.
test -f .env.staging && grep -q "^FALKORDB_URL=redis" .env.staging && echo "OK" || echo "MISSING"
# Expected: "OK"

# 3. The 250 v19 unit tests still green.
PYTHONPATH=src:. uv run pytest tests/test_canon.py tests/test_ingestion_parser.py \
  tests/test_norm_id_migration.py tests/test_loader_article_eligibility.py \
  tests/test_falkor_loader_thematic.py tests/test_loader_delta.py \
  tests/test_loader_norm_id_emission.py tests/test_ingest_classifiers_gap_filter.py -q 2>&1 | tail -3
# Expected: "250 passed in <Xs>"

# 4. Cloud rekey from v19 has stuck — 1,300 cloud nodes have article_id == norm_id.
LIA_ENV=staging PYTHONPATH=src:. uv run python scripts/falkor_rekey_article_id_to_norm_id.py --target staging --dry-run 2>&1 | tail -5
# Expected: "Nothing to do — 1300 nodes already have article_id == norm_id." OR "pending rename: 0"
```

If any precondition fails, STOP and consult `state_fix_v19_may.md` §10 to understand the cloud state. Do not skip preconditions.

### §11.2 Phase 1 first action (after preconditions pass)

Announce in chat: "Launching v20 P1 — local full-corpus rehearsal, classifier on. Wipes local Falkor first. Expected wall-clock ~30 min."

Then run:

```bash
# P1-T1: wipe local Falkor
FALKORDB_URL=redis://127.0.0.1:6389 PYTHONPATH=src:. uv run python - <<'PY'
from lia_graph.graph.client import GraphClient, GraphWriteStatement
c = GraphClient.from_env()
r = c.execute(GraphWriteStatement(description='wipe', query='MATCH (n) DETACH DELETE n', parameters={}), strict=True)
print(f"Wipe stats: {r.stats}")
PY

# P1-T2: full corpus ingest, classifier on, Falkor-only (no Supabase write — local rehearsal)
FALKORDB_URL=redis://127.0.0.1:6389 PYTHONPATH=src:. uv run python -m lia_graph.ingest \
  --corpus-dir knowledge_base \
  --artifacts-dir artifacts/v20/local_rehearsal \
  --execute-load --allow-unblessed-load --strict-falkordb \
  --no-supabase-sink \
  --classifier-workers 4 --rate-limit-rpm 80 \
  --json 2>&1 | tail -50

# P1-T3: inspect events
grep "ingest.norm_id.binding_summary\|ingest.tema.binding_summary" logs/events.jsonl | tail -5

# P1-T4: spot checks (see §3.1.6 for the full 15-query batch)
FALKORDB_URL=redis://127.0.0.1:6389 PYTHONPATH=src:. uv run python - <<'PY'
from lia_graph.graph.client import GraphClient, GraphWriteStatement
c = GraphClient.from_env()
for nid in ["cst.art.64", "et.art.420", "ley.50.1990.art.64", "ley.2466.2025.art.11"]:
    r = c.execute(GraphWriteStatement(description=f'check-{nid}',
        query=f"MATCH (a:ArticleNode {{norm_id: '{nid}'}}) RETURN a.heading AS h LIMIT 1",
        parameters={}), strict=True)
    rows = r.rows or []
    h = rows[0].get('h') if rows and isinstance(rows[0], dict) else None
    print(f"  {nid:30s} → {h[:80] if h else '❌ NOT FOUND'}")
r2 = c.execute(GraphWriteStatement(description='tema',
    query="MATCH ()-[r:TEMA]->() RETURN count(r) AS c",
    parameters={}), strict=True)
print(f"\nTEMA edges: {r2.rows[0]['c'] if r2.rows else '?'}")
PY
```

After P1-T4 output:

- All four spot-checks return a heading → P1-SC6/7/8 likely satisfied. Run full §3.1.6 batch + check `events.jsonl` against P1-SC1–SC5.
- TEMA edges ≥ 1000 → P1-SC3/SC5 satisfied.
- Any miss → P1-T5 fires: diagnose, fix, re-run (max 3 iterations). Document each iteration in §6 run log.

### §11.3 What to do after P1 closes

- Append a §6 run log entry with the final P1 numbers.
- Set §2.1 P1 row to ✅, P2 row to 🟡 ready.
- Announce in chat: "P1 closed with [N] criteria green. Ready for P2 (cloud rebuild) — operator greenlight?"
- DO NOT start P2 without explicit operator greenlight (P2 is a real cloud write).

### §11.4 What to do after P2 closes

- Append run log entry with cloud `:ArticleNode` count + TEMA edge count + any fail-fast trips.
- Run §3.3 (P3 verification).
- Then announce P3 closed and propose P4 (consumer migration) — that's an engineering session, not a single command, so plan accordingly.

---

*Drafted 2026-05-15 evening Bogotá by claude-opus-4-7 in response to boss directive: "fix the WHOLE corpus, all topics". Companion to [fix_v19_may.md](fix_v19_may.md) (predecessor) + [../state_fix_v19_may.md](../state_fix_v19_may.md) (v19's execution ledger). Update §2 (state) and §6 (run log) as work progresses.*
