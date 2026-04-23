# ingestionfix_v3 — Close the Topic-map gap + resumable reingest

Forward-looking plan for the remaining ingestion work after `ingestionfix_v2` shipped on 2026-04-23. `ingestionfix_v2.md` remains the authoritative historical record (today's triage + all scaffolding we landed). This doc is the operator/LLM instruction sheet for the next wave: filling the Falkor Topic map from 10 of 39 to full coverage, with a **chunked, resumable, quality-gated** process so no single crash costs more than one batch (~10–15 minutes) of rework.

**Read order for a cold LLM**: §0 (Cold-Start Briefing) → §1 (Prior work) → §2 (Problem) → §3 (Scope) → §4 (Pre-flight) → §5 (Phases in order). `§8` is the live state ledger — update it as each phase transitions.

---

## §0 Cold-Start Briefing

*If you're an LLM or engineer picking this up with no conversation context, this section is enough to orient yourself and start Phase 1 immediately. Everything later in the doc assumes you've read this.*

### 0.1 What Lia_Graph is (30-second orientation)

Lia_Graph is a graph-native RAG product shell for Colombian accounting/legal content. It serves SMB accountants who act as de-facto labor/tax/corporate advisors. The served runtime is `src/lia_graph/pipeline_d/` (the "main chat" surface). Retrieval has two halves: chunk-level hybrid search in Supabase (`retriever_supabase.py` → `hybrid_search` RPC) + graph traversal in FalkorDB (`retriever_falkor.py`). Parallel surfaces — `Normativa`, `Interpretación` — have their own orchestration/synthesis/assembly modules and must **not** be folded into `main chat`.

### 0.2 Repo layout (essentials only)

```
src/lia_graph/
  pipeline_d/             # served runtime — the main chat hot path
  ingestion/              # build-time corpus ingestion
    parser.py             # markdown → ParsedArticle
    classifier.py         # LLM subtopic classification (Gemini)
    delta_planner.py      # diffs on-disk corpus against cloud baseline
    delta_runtime.py      # materialize_delta entry point
    supabase_sink.py      # writes documents/chunks/edges to Supabase
    dangling_store.py     # persistence for unresolved edge targets (v2 patched here)
    loader.py             # builds Falkor node/edge plan (v2 patched here)
  graph/
    client.py             # Falkor GraphClient + GraphWriteStatement
    schema.py             # node_types + required_fields (strict)
  supabase_client.py      # production/staging auth + client factory
  ingest.py               # CLI entry point — has --force-full-classify

scripts/
  launch_phase9a.sh           # detached full-corpus reingest (nohup + disown + direct redirect)
  launch_phase9a_force.sh     # same + --force-full-classify
  launch_phase9b.sh           # detached embedding backfill
  launch_batch.sh             # v3: per-batch detached launcher (fingerprint_bust + ingest)
  embedding_ops.py            # 9.B CLI
  monitoring/
    README.md                 # top-level navigation index
    ingest_heartbeat.py       # reusable 3-min cron heartbeat renderer
    batch_pipeline/           # v3 topic-backfill tools
      README.md               # canonical v3 flow diagram + safety rails
      fingerprint_bust.py     # null doc_fingerprint for a topic slice
      validate_batch.py       # G1-G10 Quality Gate validator
      run_topic_backfill_chain.sh    # gate-enforced chain supervisor

tests/
  test_dangling_store.py      # 20 tests (12 added by v2)
  test_loader_delta.py        # 19+ tests (11 added by v2)
  test_falkor_loader_thematic.py
  test_ingest_cli_additive.py

docs/next/
  ingestionfix_v2.md          # HISTORICAL RECORD (today's triage)
  ingestionfix_v3.md          # THIS DOC (forward-looking plan)

artifacts/                    # filesystem corpus bundle + run manifests
knowledge_base/               # on-disk corpus (1,280 docs)
logs/
  events.jsonl                # the TRUTH — anchor monitoring here
  reingest-*.log              # 9.A run logs
  embed-*.log                 # 9.B run logs
```

### 0.3 Tooling

- **Python package manager**: `uv` (pyproject.toml + uv.lock). Run anything with `uv run` so it uses the project venv. Dev deps via `uv run --group dev python ...`.
- **Node**: npm for the frontend only. `npm --prefix frontend run build:public` for build artifacts.
- **Task runner**: `make` — notable targets: `test-batched` (the ONLY sanctioned way to run full pytest; has a conftest guard that aborts if >20 files collected without `LIA_BATCHED_RUNNER=1`), `eval-c-gold`.
- **Single test**: `PYTHONPATH=src:. uv run pytest tests/<file>.py -v` (or `-k <pattern>`).
- **Supabase CLI**: `2.90.0+` required (upgrade via `brew upgrade supabase`). Used for `db push`, local stack, migrations.
- **Cron scheduling**: Claude Code's `CronCreate` tool, session-scoped, 7-day auto-expire. Used for 3-min heartbeats.

### 0.4 Auth + env

- **Env file**: `.env.staging` — confusingly named, it holds the **production** Supabase URL + service-role key for the `lia-graph-prod` project (ref `utjndyxgfhkfcrjmtdqz`). Source it with `set -a; source .env.staging; set +a` before any production read/write.
- **Production writes are gated**: the Claude Code harness will prompt-block on any command that hits production. Expected flow: operator sees the prompt, approves once per session; alternatively, grant a narrow permission rule like `Bash(nohup bash -c * > logs/reingest-*.log*)` in `.claude/settings.local.json`.
- **Falkor**: cloud FalkorDB URL via `FALKORDB_URL` (set in `.env.staging`). Graph name `LIA_REGULATORY_GRAPH`.
- **Gemini**: `GOOGLE_API_KEY` in `.env.staging` for classifier + embedding calls.

### 0.5 Test data + fixtures

- **Golden health**: `npm run test:health` (builds public UI + focused backend smokes + frontend vitest + Playwright e2e).
- **Faster variant**: `npm run test:health:fast` (no Playwright).
- **Ingestion-specific**: `tests/test_dangling_store.py`, `tests/test_loader_delta.py`, `tests/test_ingest_cli_additive.py`, `tests/test_delta_planner.py`, `tests/test_delta_worker.py` — the v2 regression fence.
- **Local Supabase seed**: after `make supabase-reset`, run `PYTHONPATH=src:. uv run python scripts/seed_local_passwords.py` (every `@lia.dev` user → password `Test123!`).
- **Test accounts for browser smokes**: any `@lia.dev` email + `Test123!`. See `supabase/migrations/20260417000001_seed_users.sql`.

### 0.6 Glossary

| Term | Meaning |
|---|---|
| **Additive delta** | The non-full-rebuild ingestion path. Diffs on-disk corpus vs cloud baseline; only processes added/modified/retired docs. See `ingestion/delta_planner.py`. |
| **Fingerprint** | `documents.doc_fingerprint` — hash of content + classifier output. If it matches on-disk parse, doc is "unchanged" and skipped. **Busting this column is how v3 forces controlled rework.** |
| **gen_active_rolling** | The logical generation ID the additive path writes to. Resolves to the currently-active snapshot (today: `gen_20260422005449`). No atomic flip needed — writes land directly. |
| **Dangling candidate** | An extracted edge whose target ArticleNode doesn't exist yet at extraction time. Persisted in `normative_edge_candidates_dangling`; promoted to `normative_edges` when the target arrives in a later delta. |
| **TEMA edge** | Falkor edge from ArticleNode to TopicNode (thematic classification). |
| **PRACTICA_DE edge** | Falkor edge linking a practice doc to a normative doc. Currently `0` in Falkor; Phase 3 aims to populate. |
| **Quality Gate** | The checkpoint in Phase 3.0 that blocks the autonomous chain from proceeding past batch 1 until validation passes. |
| **STOP_BACKFILL sentinel** | `artifacts/STOP_BACKFILL` — touching this file halts the chain cleanly at the next batch boundary. |
| **Ultra-test** | The belt-and-suspenders validation tier (U1-U4) that runs after automated + manual checks on batch 1. Prevents the "discover systemic bug at batch 7" failure mode. |
| **force_full_classify** | CLI flag on `lia_graph.ingest` that bypasses the fingerprint shortcut. Expensive (re-runs classifier on all 1,280 docs). Alternative is fingerprint-busting specific subsets, which v3 introduces. |

### 0.7 Source-of-truth pointers

| Concern | Canonical source |
|---|---|
| v2's historical triage (3 crashes, their fixes, lessons) | `docs/next/ingestionfix_v2.md §7 run_log_2026_04_23` |
| Repo-level operating guide | `AGENTS.md` + `CLAUDE.md` (top of repo) |
| Runtime env matrix (LIA_* flags, run modes) | `docs/guide/orchestration.md` (versioned; env matrix v2026-04-22-ac1 at time of writing) |
| Detached-launch pattern + heartbeat cron recipe | `scripts/monitoring/README.md` |
| Long-running Python process default pattern | `CLAUDE.md §"Long-running Python processes"` |
| Graph schema required_fields | `src/lia_graph/graph/schema.py` (search `required_fields`) |
| Bogotá AM/PM time policy | User memory `feedback_time_format_bogota.md` + applied repo-wide |
| Production Supabase reads/writes gate | User must approve each session OR grant a narrow permission rule in `.claude/settings.local.json` |

### 0.8 Design-skill invocation pattern

- **Expert code review before shipping a non-trivial patch**: spawn a subagent via the `Agent` tool (subagent_type: `general-purpose`) framed as a senior reviewer. Give it the patched file + tests + crash context; ask for edge cases the existing tests don't cover. v2 used this pattern twice (dangling_store patch, loader patch) — both times it surfaced real bugs. See §9 carry-forward learnings.
- **Broad codebase exploration** (>3 queries): spawn `Explore` subagent. Otherwise use `grep`/`find` directly.
- **Security review**: the `/security-review` skill when touching auth or write paths.
- **Do NOT delegate understanding**: write prompts that prove you understood the problem; include file paths and line numbers; don't ask the agent to "based on your findings, fix the bug."

### 0.9 Git conventions

- **Commit prefix format** (match recent log via `git log --oneline | head -20`):
  - `feat(ingestionfix-v3-phase-N): <short description>` — for new phases
  - `fix(ingestionfix-v3-phase-N): <short description>` — for bug fixes
  - `docs(ingestionfix-v3-phase-N): <short description>` — for doc updates
- **Branch**: `feat/ingestionfix-v3-phase-N-<slug>` — one branch per phase where practical.
- **Commit cadence**: commit + push after each phase's acceptance criteria pass. The embedded state log in each phase (§5.x.State log) must be updated in the same commit.
- **Never skip hooks** (`--no-verify`). If a pre-commit hook fails, fix the root cause and create a NEW commit.
- **Never amend merged/pushed commits.** Always create new commits.

### 0.10 Non-negotiables

From `CLAUDE.md` + v2 hard rules:

1. **Never run `make phase2-graph-artifacts-supabase` or `python -m lia_graph.ingest --supabase-sink --supabase-target production` without explicit authorization**. Production Supabase writes are destructive-to-history.
2. **Never run `make phase2-promote-snapshot`** — not needed for additive mode (Phase 9.C is a no-op).
3. **Never run the full pytest suite in one process** — use `make test-batched`. The conftest guard aborts without `LIA_BATCHED_RUNNER=1`.
4. **Falkor adapter MUST propagate cloud outages** — no silent artifact fallback on staging/production. If Falkor is unreachable, retrieval must error, not degrade.
5. **`PipelineCResponse.diagnostics` must always carry `retrieval_backend` and `graph_backend`** — operators need to confirm which adapters served a given turn.
6. **All user-facing times in Bogotá AM/PM** (UTC-5, no DST). Machine-readable logs stay UTC ISO.
7. **Long-running Python processes default to detached (`nohup + disown`) + 3-min heartbeat cron** — no exceptions. See CLAUDE.md.
8. **Never touch `docs/next/ingestionfix_v2.md §7` state ledger without user approval.** v3's state ledger (§8 of this doc) is owned by v3 and freely mutable as the implementation proceeds.

---

## §1 Prior work — context + motivation

### 1.1 What `ingestionfix_v2` shipped (2026-04-23)

A twelve-phase plan ran to near-completion in a single day. Final status:

| v2 Phase | Summary | Status |
|---|---|---|
| 1 | Parser fallback + unit coverage | ✓ shipped |
| 2 | Chunk `source_type` semantics | ✓ shipped |
| 3 | Topic null coercion from path | ✓ shipped |
| 4 | Edge extraction gating + typed edges | ✓ shipped |
| 5 | Thematic graph edges (TEMA / SUBTEMA) | ✓ shipped |
| 6 | `doc_fingerprint` persistence on sink | ✓ shipped |
| 7a | Tags admin backend endpoints | ✓ shipped |
| 7b | Tags admin frontend tab | 🟡 deferred |
| 8 | Subtopic-miner (partial: `laboral` mined; 38 topics punted) | 🟡 partial |
| **9.A** | Full cloud reingest | ✓ shipped after 3 crashes + fixes |
| **9.B** | Embedding backfill (5,765 NULL → 0) | ✓ shipped |
| 9.C | Promotion | N/A (no-op for additive) |
| 10 | Verification smokes | 🟡 partial (10.1/10.2/10.3 run; 10.4/10.5 browser-only) |
| 11 | UI terminal-banner field-path fix | ⏸ not started |
| 12 | Close-out docs | ⏸ not started |

### 1.2 Why today hurt — the 4×40-min reingest lesson

The 9.A reingest crashed three times before landing on attempt #4. **Each crash cost ~40 minutes of classifier wall-time** because `--force-full-classify` bypasses the fingerprint checkpoint.

| Attempt | Crashed at | Root cause | Fix (all shipped) |
|---|---|---|---|
| 1 | `dangling_store.load_for_target_keys` | httpx `InvalidURL: URL component 'query' too long` on unbounded `.in_()` filter | Chunk into 200-key batches (`_LOAD_BATCH_SIZE=200`) |
| 2 | `dangling_store.upsert_candidates` | PostgREST SQLSTATE 21000 — intra-batch duplicates on `ON CONFLICT` | Dedupe payloads by `(source_key, target_key, relation)` + last-observation-wins coalescing + write-batching at `_UPSERT_BATCH_SIZE=500` |
| 3 | `graph/schema.validate_node_record` via `loader.stage_node` | Parser fallback docs have `article_number=""`; Falkor schema requires it | `_is_article_node_eligible()` filter + sibling predicates for SubTopicNode / ReformNode; edge-endpoint filter |
| 4 | **Completed** | — | — |

**The lesson baked into v3**: fingerprint checkpointing exists and works; what was missing was **controlled fingerprint invalidation** so the operator can force re-work on a specific subset without reclassifying the whole corpus. v3 introduces this via `scripts/monitoring/monitor_ingest_topic_batches/fingerprint_bust.py` + a per-batch quality gate.

### 1.3 What's left as of 2026-04-23 close

1. **Topic coverage gap** — Falkor has `TopicNode=10, TEMA=10, PRACTICA_DE=0`. Expected: `Topic≥39, PRACTICA_DE>0`. Today's 57-doc additive delta only seeded topics those docs touched.
2. **Orphan docs** — 1,523 of 6,730 live docs have no chunks (down from 2,610 at start of day). Pre-existing gaps from older ingests; today's delta didn't target them.
3. **Operator smokes** — v2 Phase 10.4 (E2E main chat) + 10.5 (Tags tab queue) need a browser.
4. **v2 paperwork** — v2 Phase 11 cosmetic banner fix + Phase 12 doc close-out.

### 1.4 Cloud state at v3 start (2026-04-23 ~3:10 PM Bogotá)

| Backend | Metric | Value |
|---|---|---|
| Supabase | `documents` (live) | 6,730 |
| Supabase | `document_chunks` | 19,507 |
| Supabase | `embedding IS NULL` | **0** ✓ |
| Supabase | orphan docs (no chunks) | 1,523 |
| Supabase | active generation | `gen_20260422005449` |
| Falkor | ArticleNode | 8,106 |
| Falkor | TopicNode | 10 (target ≥39) |
| Falkor | SubTopicNode | 24 |
| Falkor | TEMA edges | 10 |
| Falkor | PRACTICA_DE edges | **0** (target >0) |

---

## §2 Problem summary (TL;DR)

> **The Falkor graph database has 10 of 39 expected Topic nodes and 0 PRACTICA_DE edges.** A broader reingest would fill it. Naive "run the whole thing again" risks another 40-minute classifier pass with crash exposure. The fix: **bust fingerprints per topic, re-run additive per topic, commit between topics, quality-gate batch 1 before letting batches 2–8 run autonomously.** If any single batch crashes, only that batch (~10–15 min) is redone — prior batches are written in stone.

> ⚠ **Read §2.1 before planning a rehearsal.** A 2026-04-23 pre-rehearsal probe revealed the v3.0 seed plan.json underestimates actual per-batch doc counts by 2-27×. Total corpus to process is 1,319 docs (not 340). Batch 1 as-written in plan.json is 552 docs (not 20) because `otros_sectoriales` alone is 510. A rebalanced v3.1 proposal is in §2.1.5; execute that **before** running batch 1 for real.

---

## §2.1 2026-04-23 pre-rehearsal probe — critical findings

*Added after the Phase-2 code landed. A dry-run probe of batch 1 revealed that the seed plan's per-batch doc-count estimates are **2-27× too low** because the initial taxonomy-only sizing missed that one catch-all topic owns 39% of the classified corpus. These numbers are the TRUE starting state; every estimate below ≤ §5 needs to be read against this table, not the §5 Phase 3 seed.*

### 2.1.1 Actual per-topic doc counts (production, live, `retired_at IS NULL`)

Source: `scripts/monitoring/monitor_ingest_topic_batches/fingerprint_bust.py --topic <k> --dry-run` × 39 top-level topics + one `is_('tema','null')` probe. Executed 2026-04-23 PM (Bogotá).

```
   510  otros_sectoriales           ← 39% of classified corpus; wrecking ball
    83  reformas_tributarias
    80  declaracion_renta
    75  laboral
    71  comercial_societario
    50  procedimiento_tributario
    39  inversiones_incentivos
    37  presupuesto_hacienda
    32  datos_tecnologia
    28  estados_financieros_niif
    26  iva
    25  leyes_derogadas
    23  ica
    23  cambiario
    21  facturacion_electronica
    15  retencion_en_la_fuente
    15  regimen_simple
    15  contratacion_estatal
    15  obligaciones_profesionales_contador
    14  informacion_exogena
    13  beneficiario_final_rub
    11  regimen_sancionatorio
    11  emergencia_tributaria
    10  zonas_francas
     8  calendario_obligaciones
     8  economia_digital_criptoactivos
     8  impuesto_nacional_consumo
     7  sagrilaft_ptee
     7  regimen_tributario_especial
     6  gravamen_movimiento_financiero_4x1000
     6  dividendos_utilidades
     6  activos_exterior
     5  precios_de_transferencia
     4  impuesto_patrimonio_personas_naturales
     3  perdidas_fiscales_art147
     3  reforma_pensional
     3  normas_internacionales_auditoria
     2  impuestos_saludables
     1  estatuto_tributario       ← ET rows mostly live under subtopic keys
     2  (NULL tema)
------
  1319  TOTAL classified (top-level tema)
```

### 2.1.2 Planned vs actual batch sizes (v3.0 seed plan.json)

| Batch | Planned docs | Actual docs | Drift | Notes |
|---|---|---|---|---|
| 1 (gate) | 20 | **552** | **27×** | `otros_sectoriales` (510) dominates |
| 2 | 25 | 52 | 2× | — |
| 3 | 30 | 41 | 1.4× | — |
| 4 | 35 | 45 | 1.3× | — |
| 5 | 40 | **211** | **5×** | `reformas_tributarias` (83) bloats it |
| 6 | 50 | 129 | 2.6× | `comercial_societario` (71) dominates |
| 7 | 60 | 107 | 1.8× | `procedimiento_tributario` (50) dominates |
| 8 | 80 | 182 | 2.3× | `declaracion_renta` + `laboral` (155) dominate |

Total: **1,319 docs** across all 8 batches (the plan said 340). Total wall time at the historical ~30 docs/min classifier rate ≈ **44 min pure classify + sink/Falkor per-batch overhead ≈ 2.5-3.5 hr unattended**, not the 70-105 min quoted in §5 Phase 3.

### 2.1.3 `tema` column semantics — follow-up worth checking

Classified total (1,319) + NULL (2) = 1,321 rows, far below the 6,730 live-docs headline in §1.4. Implication: the `tema` column probably holds subtopic keys for ~5,400 rows, not just the 39 top-level keys. This does NOT block v3 Phase 3 (the bust + additive path filters by whatever key is in `tema`, and re-classification restamps), but it means:

* The Falkor `TopicNode` population story may need an additional backfill pass over the rows whose `tema` is a subtopic — those don't currently trigger a TEMA edge to a top-level TopicNode.
* Actual docs-touched per batch could be higher than the tallies above if the classifier promotes subtopic-keyed docs to top-level topic attribution during re-sink.

Parked as follow-up **F6** in §8 `followups_for_later`.

### 2.1.4 Critical risk: `otros_sectoriales` as gate batch

`otros_sectoriales` is a taxonomy catch-all with no domain boundary. 510 docs is 17-25 min of pure classifier wall time at ~30 docs/min — exceeding the upper end of G9's 5-25 min window for a batch. Beyond wall time: a catch-all has the highest per-doc classifier variance, so it's the **worst possible choice** for a Quality Gate batch (which should have low blast radius + tight topical cohesion to surface systemic bugs cleanly).

### 2.1.5 Recommended plan.json v3.1 rebalance

Proposed to land before the Phase-2 rehearsal runs for real. Not yet committed — operator call.

| Batch | Topics | Docs | Wall est. |
|---|---|---|---|
| 1 (gate) | `activos_exterior (6) + emergencia_tributaria (11) + impuestos_saludables (2) + normas_internacionales_auditoria (3) + perdidas_fiscales_art147 (3) + reforma_pensional (3)` | **28** | ~5-8 min |
| 2 | `leyes_derogadas + beneficiario_final_rub + economia_digital_criptoactivos + sagrilaft_ptee + obligaciones_profesionales_contador + zonas_francas + impuesto_patrimonio_personas_naturales` | ~83 | ~10 min |
| 3 | `regimen_tributario_especial + regimen_simple + regimen_sancionatorio + impuesto_nacional_consumo + gravamen_movimiento_financiero_4x1000 + dividendos_utilidades + calendario_obligaciones + precios_de_transferencia + cambiario` | ~94 | ~12 min |
| 4 | `ica + facturacion_electronica + retencion_en_la_fuente + contratacion_estatal + informacion_exogena + datos_tecnologia` | ~120 | ~14 min |
| 5 | `inversiones_incentivos + presupuesto_hacienda + estados_financieros_niif + procedimiento_tributario + estatuto_tributario` | ~155 | ~17 min |
| 6 | `reformas_tributarias` | ~83 | ~10 min |
| 7 | `comercial_societario + declaracion_renta` | ~151 | ~17 min |
| 8 | `iva + laboral` | ~101 | ~12 min |
| 9 | `otros_sectoriales` (quarantined) | ~510 | ~30-40 min |

Total: 1,319 docs across 9 batches. Gate batch is 28 docs (small enough to iterate cheaply on if Quality-Gate finds something). Batch 9 (`otros_sectoriales`) is explicitly quarantined so it can be run last and doesn't gate the rest. Every other batch lands in the 10-17 min window — below G9's 25-min upper threshold.

### 2.1.6 What to do with this

1. Operator reviews the v3.1 proposal above.
2. If accepted, update `artifacts/fingerprint_bust/plan.json` + the `est_wall_minutes` / `est_doc_count` fields + add a `plan_version: v3.1` marker + a `revisions_log` block documenting this probe.
3. Re-run `bash scripts/launch_batch.sh --batch 1 --dry-run` against the new batch 1 composition; expect `row_count: 28`.
4. Proceed to real-run Phase-2 rehearsal — **but see §2.2 first**: subsequent inspection of `otros_sectoriales` content showed the catch-all is really a mix of misclassified rows + 12-15 genuine sectors, so Phase 2.5 (sector reclassification) should land BEFORE Phase 3 chain runs, otherwise the 510-doc quarantine batch permanently encodes bad taxonomy.

---

## §2.2 `otros_sectoriales` deep-dive — the 510-doc catch-all is really 3 things

*Added after §2.1 probe. Manual inspection of 40 sample files + 4 subfolder analysis revealed that the "miscellaneous" bucket is not genuinely miscellaneous; it's a dumping ground produced by taxonomy under-coverage + classifier misrouting. Treating it as one batch (even as a quarantined batch 9) bakes that under-coverage permanently into TopicNode/TEMA graph state.*

### 2.2.1 Structural finding — 4 editorial layers, not 4 sectors

The 510 docs are stored in four subfolders:

| Folder | Docs | What it is |
|---|---|---|
| `NORMATIVA/` | 119 | Raw uncurated law stubs (bare metadata — ~30 lines typical) |
| `consolidado/` | 121 | **Curated practical digest for SMB accountants** (~168 lines typical; structured "Objeto y alcance" / "Temas clave para PYMEs" / article-level commentary) |
| `EXPERTOS/EXPERTOS/` | 120 | Expert-reviewed curator pass |
| `LOGGRO/PRACTICA/` | 123 | Practice-focused, case-oriented |
| `Ley*` (root orphans) | 10 | One-offs at the OTROS_SECTORIALES root |

Sample-verified on Ley 1712 de 2014 (Transparencia): `NORMATIVA/Ley-1712-2014.md` = 30 lines (stub), `consolidado/Ley-1712-2014.md` = 168 lines (curated commentary). These are **editorial layers of the same underlying law**, not semantic duplicates. All four layers are valuable — they give retrieval different tonal registers to draw from. Deduplication here would destroy signal.

### 2.2.2 Sector content is rich but hidden inside titles

Title sampling of 40 `consolidado/` files surfaces at least a dozen clean sector clusters:

| Sector cluster | Sample laws |
|---|---|
| Health | Ley 10/1990 (Sistema Nacional de Salud), Ley 1122/2007 (Seguridad Social en Salud) |
| Education | Ley 115/1994 (Ley General de Educación), Ley 1064/2006 (Educación para el trabajo), Ley 1014/2006 (cultura emprendimiento) |
| Agriculture | Ley 101/1993 (Desarrollo Agropecuario y Pesquero) |
| Utilities / energy | Ley 142/1994 (servicios públicos domiciliarios), Ley 143/1994 (sector eléctrico) |
| Culture / heritage | Ley 1185/2008 (patrimonio cultural), Ley 1379/2010 (bibliotecas), Ley 1493/2011 (artes escénicas) |
| Tourism | Ley 1101/2006 (contribución turismo), Ley 1558/2012 (reforma turismo) |
| Housing | Ley 1537/2012 (vivienda de interés social) |
| Social / childhood / gender | Ley 1098/2006 (Infancia y Adolescencia), Ley 1257/2008 (violencia contra la mujer) |
| Zonas francas | Ley 109/1985 |
| Science & tech | Ley 1286/2009 (Colciencias) |
| Electoral / political | Ley 130/1994 (partidos políticos), Ley 1475/2011 (código electoral) |
| Public finance / APP | Ley 141/1994 (regalías), Ley 1508/2012 (APP) |

### 2.2.3 Several "miscellaneous" laws are misclassified into named topics

Inspection surfaces laws that clearly belong in existing top-level taxonomy but landed in `otros_sectoriales`:

| Law | Currently `tema` | Should be |
|---|---|---|
| Ley 1066/2006 (cartera pública) | otros_sectoriales | `procedimiento_tributario` |
| Ley 1175/2007 (cartera tributaria) | otros_sectoriales | `procedimiento_tributario` |
| Ley 1111/2006 (modifica ET) | otros_sectoriales | `reformas_tributarias` |
| Ley 1121/2006 (anti-terrorism financing) | otros_sectoriales | `sagrilaft_ptee` |
| Ley 1328/2009 (consumer financial protection) | otros_sectoriales | `comercial_societario` |
| Ley 1527/2012 (libranzas / payroll deductions) | otros_sectoriales | `laboral` |
| Ley 109/1985 (zonas francas) | otros_sectoriales | `zonas_francas` |

Order-of-magnitude estimate: **30-60 of the 510 docs** are misclassified into existing named topics. The classifier's prefix/alias map doesn't cover these cases yet.

### 2.2.4 The three pieces otros_sectoriales is hiding

1. **~30-60 docs** — misclassified; belong in existing named topics (should migrate into `procedimiento_tributario`, `laboral`, `sagrilaft_ptee`, `zonas_francas`, etc.).
2. **~400-450 docs** — genuinely sectoral; fall into ~12-15 clean new sector topics (`sector_salud`, `sector_educacion`, `sector_utilities`, `sector_cultura`, `sector_vivienda`, etc.) that don't exist in the taxonomy yet.
3. **~10 docs** — true miscellaneous orphans that no existing or proposed new topic catches.

### 2.2.5 Why this matters for v3 close-out

Running the v3.1 proposal as-is (batch 9 = `otros_sectoriales` quarantine) creates one giant `TopicNode{topic_key:"otros_sectoriales"}` in Falkor with 510 TEMA edges pointing at it. Accountants asking "what does Ley 142 say about public utility billing?" get retrieval that routes through "otros_sectoriales" — a meaningless generic bucket — instead of a focused `sector_utilities` TopicNode with ~10 TEMA edges. That's a retrieval-quality regression vs the ~39-clean-topics goal v3 was written to achieve.

**Implication:** Phase 2.5 (below in §5) inserts the sector-reclassification work BEFORE the Phase 3 chain runs, so the batch that lands `otros_sectoriales` + its replacement sector topics into Falkor does so with the right structure the first time.

---

## §3 Scope + phasing overview

Six phases. Each is **independently shippable and resumable**. Phase 3.0 (Quality Gate) physically blocks Phase 3 from advancing until batch 1 is validated clean.

| Phase | Purpose | Active cost | Wall time | Blocks what |
|---|---|---|---|---|
| 1 | Close v2 paperwork (10.3 amendment, Phase 11 banner, Phase 12 docs) | ~1 hr | ~1 hr | — |
| 2 | Build + unit-test `fingerprint_bust.py`, chain runner skeleton, batch plan; rehearse on `laboral` | ~2 hrs | ~2.5 hrs | Phase 2.5 |
| **2.5** | **Sector reclassification of `otros_sectoriales`** — LLM title pass → operator review → taxonomy update → plan.json v3.1 → `tema` migration → re-probe | ~3-4 hrs | ~4-5 hrs (mostly operator review) | Phase 3.0 |
| 3.0 | **Batch 1 Quality Gate** — run batch 1, execute G1-G10/M1-M3/U1-U4 checks, operator approves | ~1 hr | ~1.5 hrs | Phase 3 batches 2–8 |
| 3 | Phased topic-coverage backfill — batches 2–8 via autonomous chain | ~15 min launch | ~2.5–3.5 hr unattended (revised 2026-04-23 per §2.1) | — |
| 4 | Orphan-doc backfill (stretch; deferred) | TBD | TBD | — |
| 5 | Operator browser smokes (10.4 main chat, 10.5 Tags tab) | ~20 min | ~20 min | v3 close-out |

Phases 1, 2, 2.5, 3.0, 3, 5 close v3. Phase 4 is tracked separately.

---

## §4 Pre-flight checklist (run before Phase 1)

- [ ] Read `docs/next/ingestionfix_v2.md §0` (cold start) and §7 (state ledger). Understand what shipped.
- [ ] Read §0 of THIS doc. Understand the v3 architecture.
- [ ] `git status` is clean on a fresh branch. Create `feat/ingestionfix-v3-phase-1-paperwork` (first phase).
- [ ] `.env.staging` is present and sourceable (`set -a; source .env.staging; set +a`).
- [ ] Production auth verified: `PYTHONPATH=src:. uv run --group dev python -c "from lia_graph.supabase_client import create_supabase_client_for_target; print(create_supabase_client_for_target('production').table('documents').select('doc_id', count='exact').execute().count)"` returns `6730`.
- [ ] Falkor auth verified: a one-liner Cypher count runs (use `scripts/monitoring/ingest_heartbeat.py` with `--skip-supabase` as the probe).
- [ ] v2 regression suite green: `PYTHONPATH=src:. uv run pytest tests/test_dangling_store.py tests/test_loader_delta.py tests/test_falkor_loader_thematic.py tests/test_ingest_cli_additive.py -q` returns `90+ passed`.
- [ ] Cold backup of cloud Supabase taken (Supabase dashboard → backup point in time). Phase 3 fingerprint-busting is destructive-to-metadata.
- [ ] Current baseline captured into §8 state ledger `cloud_state_at_v3_start_*` (copy from §1.4).

---

## §5 Phases

### Phase 1 — Close v2 paperwork

**Goal.** Finish the three v2 items that never shipped: amend Phase 10.3 acceptance to reflect additive-delta reality, land the cosmetic admin-banner fix (v2 Phase 11), refresh doc surfaces (v2 Phase 12). Unblocks closing v2 as formally done.

#### Phase 1 — Files to modify

| Path | Change |
|---|---|
| `docs/next/ingestionfix_v2.md §4 Phase 10` | Replace hard thresholds `Topic ≥ 39, PRACTICA_DE > 0` with additive-aware wording (see 1a below) |
| `docs/next/ingestionfix_v2.md §7 phase_10_verification.graph_smoke_result` | Remove "will NOT pass" framing; point to v3 §2 as the resolution path |
| `docs/next/ingestionfix_v2.md §7 plan_version` | Bump to `2.5` with a note: "Phase 10.3 acceptance amended; v3 covers the coverage gap" |
| `docs/next/ingestionfix_v2.md §7` | Add `closed_out_at: 2026-04-<NN>` stamp once Phase 12 finishes |
| `docs/guide/orchestration.md` env matrix | Bump version per matrix change-log convention (only if v3 introduces new flags — likely none; confirm) |
| `docs/guide/env_guide.md` env matrix mirror | Mirror orchestration.md |
| `CLAUDE.md` env matrix mirror (top of repo) | Mirror (already partially updated in v2 for long-running-process guidance) |
| `frontend/src/app/orchestration/shell.ts` | Update `/orchestration` HTML map status card |
| `frontend/src/features/orchestration/orchestrationApp.ts` | Mirror shell.ts status-card update |
| **EITHER** `frontend/src/features/ingest/additiveDeltaController.ts` (~line 593) | Pass `ev.reportJson?.sink_result` (flattened) instead of `ev.reportJson` wholesale when building the terminal VM |
| **OR** `frontend/src/shared/ui/molecules/additiveDeltaTerminalBanner.ts` (~lines 57-64) | Read `vm.report.sink_result.documents_added` etc. directly |

(Pick ONE of the two frontend locations; v2 §4 Phase 11 recommends the controller for pure-data banners.)

#### Phase 1 — Files to create

None.

#### Phase 1 — Tests (on the specific surface)

| Test | Where | How to run just this test |
|---|---|---|
| Admin banner VM shape regression | Modify `frontend/tests/additiveDeltaControllerTerminalVm.test.ts` — assert the VM now carries flattened `sink_result` fields | `npm run test:frontend -- additiveDeltaControllerTerminalVm` |
| `/orchestration` page renders without console errors | Manual — open `npm run dev` local app → navigate to `/orchestration` → open DevTools console | Manual |
| Docs consistency | No automated test; enforce via PR review | — |

#### Phase 1 — Run

```bash
# 1a — amend v2 Phase 10.3 wording
$EDITOR docs/next/ingestionfix_v2.md   # see exact wording in v3 §5 Phase 1 Acceptance

# 1b — frontend fix
$EDITOR frontend/src/features/ingest/additiveDeltaController.ts
$EDITOR frontend/tests/additiveDeltaControllerTerminalVm.test.ts
npm run test:frontend -- additiveDeltaControllerTerminalVm

# 1c — doc mirrors
$EDITOR docs/guide/orchestration.md
$EDITOR docs/guide/env_guide.md
$EDITOR CLAUDE.md
$EDITOR frontend/src/app/orchestration/shell.ts
$EDITOR frontend/src/features/orchestration/orchestrationApp.ts

# Verify build + local render
npm run frontend:build
npm run dev   # open localhost:3000/orchestration in browser, check console

# Stamp v2 closed
$EDITOR docs/next/ingestionfix_v2.md  # add closed_out_at + plan_version=2.5

# Commit
git add -A
git commit -m "docs+feat(ingestionfix-v3-phase-1): close v2 paperwork — 10.3 amendment, banner fix, docs refresh"
```

#### Phase 1 — Acceptance

1. Phase 10.3 wording in v2 now reads: *"Topic coverage is seeded proportional to the delta's topic breadth. Acceptance: ≥1 TEMA edge per topic touched by the delta, zero Falkor write failures. Full 39-entry taxonomy coverage is the target of `ingestionfix_v3` Phase 3."*
2. `npm run test:frontend -- additiveDeltaControllerTerminalVm` green.
3. `/orchestration` page renders with no console errors; status card shows current v3 state.
4. `docs/next/ingestionfix_v2.md §7 plan_version: 2.5` and `closed_out_at` stamped.
5. Commit pushed to `feat/ingestionfix-v3-phase-1-paperwork`; PR open (optional: can be merged as part of v3 close PR).

#### Phase 1 — State log (fill in as you go)

```yaml
phase_1_paperwork:
  status: pending                   # pending | in_progress | completed | failed | blocked
  started_at:                       # Bogotá AM/PM
  completed_at:
  branch: feat/ingestionfix-v3-phase-1-paperwork
  commit:                           # SHA of the final commit
  files_modified: []                # actually modified (truth, not plan)
  files_created: []
  tests_passing:
    - additiveDeltaControllerTerminalVm
  notes: ""
  resumption_hint: ""               # if status=failed, what to do next time
```

---

### Phase 2 — `fingerprint_bust.py` tool + chain runner skeleton + rehearsal

**Goal.** Build the three primitives Phase 3 depends on and rehearse the full flow on one topic (`laboral`) before attempting the real batch 1.

#### Phase 2 — Files to modify

| Path | Change |
|---|---|
| `scripts/monitoring/ingest_heartbeat.py` | Add optional `--chain-state-file <path>` flag; when set, reads `artifacts/backfill_state.json` and prepends two rows to the output table showing `Chain progress` + `Total ETA` |
| `scripts/monitoring/README.md` | Document chain mode with an example cron prompt |

#### Phase 2 — Files to create

| Path | Purpose |
|---|---|
| `scripts/monitoring/monitor_ingest_topic_batches/fingerprint_bust.py` | CLI: `--topic <key>` or `--topics a,b,c`; `--dry-run`; `--confirm` (required for >0 real rows); `--force-multi` (required for >1 topic); writes `artifacts/fingerprint_bust/<ts>_<batch_or_topic>.json` manifest |
| `scripts/monitoring/monitor_ingest_topic_batches/run_topic_backfill_chain.sh` | Bash supervisor loop — skeleton in Phase 2, full implementation in Phase 3. Must include `--gate-only` mode that runs ONLY batch 1 + pauses |
| `artifacts/fingerprint_bust/plan.json` | Canonical 8-batch plan (JSON). See §5 Phase 3 "Batch plan" table for seed groupings |
| `artifacts/fingerprint_bust/.gitkeep` | Ensure the directory is tracked |
| `tests/test_fingerprint_bust.py` | Unit tests for `fingerprint_bust.py` using the `_FakeClient` pattern from `test_dangling_store.py` |

#### Phase 2 — Tests (on the specific surface)

| Test name | File | What it locks | Run command |
|---|---|---|---|
| `test_dry_run_reports_count_does_not_mutate` | tests/test_fingerprint_bust.py | `--dry-run` returns expected row count and does NOT issue UPDATE | `PYTHONPATH=src:. uv run pytest tests/test_fingerprint_bust.py -k dry_run -v` |
| `test_single_topic_bust_sets_fingerprint_null` | tests/test_fingerprint_bust.py | After execute, target rows have `doc_fingerprint IS NULL`; non-target rows untouched | `PYTHONPATH=src:. uv run pytest tests/test_fingerprint_bust.py -k single_topic -v` |
| `test_multi_topic_requires_force_multi_flag` | tests/test_fingerprint_bust.py | `--topics a,b` without `--force-multi` raises | `PYTHONPATH=src:. uv run pytest tests/test_fingerprint_bust.py -k force_multi -v` |
| `test_safety_threshold_rejects_huge_count` | tests/test_fingerprint_bust.py | Row count > 200 without `--confirm` raises | `PYTHONPATH=src:. uv run pytest tests/test_fingerprint_bust.py -k safety_threshold -v` |
| `test_manifest_written_before_execute` | tests/test_fingerprint_bust.py | If UPDATE crashes, manifest exists for audit | `PYTHONPATH=src:. uv run pytest tests/test_fingerprint_bust.py -k manifest -v` |
| `test_heartbeat_chain_state_enrichment` | tests/test_ingest_heartbeat.py (new or extend) | When `--chain-state-file` present, output includes `Chain progress` + `Total ETA` rows | `PYTHONPATH=src:. uv run pytest tests/test_ingest_heartbeat.py -k chain_state -v` |
| Rehearsal end-to-end | Manual | Bust `laboral`, run `scripts/launch_phase9a.sh` (additive), verify Falkor `TopicNode{topic_key:"laboral"}` + TEMA edges appear | Manual (~30 min wall) |

#### Phase 2 — Run

```bash
# Create the tool + tests
$EDITOR scripts/monitoring/monitor_ingest_topic_batches/fingerprint_bust.py
$EDITOR tests/test_fingerprint_bust.py

# Run just these tests — should all pass before moving on
PYTHONPATH=src:. uv run pytest tests/test_fingerprint_bust.py -v

# Create the chain runner skeleton
$EDITOR scripts/monitoring/monitor_ingest_topic_batches/run_topic_backfill_chain.sh
chmod +x scripts/monitoring/monitor_ingest_topic_batches/run_topic_backfill_chain.sh

# Create the batch plan JSON (see §5 Phase 3 seed groupings)
$EDITOR artifacts/fingerprint_bust/plan.json

# Extend heartbeat for chain mode
$EDITOR scripts/monitoring/ingest_heartbeat.py
$EDITOR tests/test_ingest_heartbeat.py   # new test file if needed
PYTHONPATH=src:. uv run pytest tests/test_ingest_heartbeat.py -k chain_state -v

# Rehearsal — CAUTION, touches production Supabase
set -a; source .env.staging; set +a
python scripts/monitoring/monitor_ingest_topic_batches/fingerprint_bust.py --topic laboral --dry-run
python scripts/monitoring/monitor_ingest_topic_batches/fingerprint_bust.py --topic laboral --confirm
bash scripts/launch_phase9a.sh
# arm heartbeat cron (3m) with --chain-state-file=artifacts/backfill_state.json

# Verify Falkor growth
PYTHONPATH=src:. uv run --group dev python -c "
from lia_graph.graph.client import GraphClient, GraphWriteStatement
c = GraphClient.from_env()
s = GraphWriteStatement(description='q', query='MATCH (t:TopicNode {topic_key: \"laboral\"}) RETURN count(t) AS n', parameters={})
print('laboral topic node count:', list(c.execute(s, strict=True).rows)[0]['n'])
"

git add -A
git commit -m "feat(ingestionfix-v3-phase-2): fingerprint_bust tool + chain runner skeleton + heartbeat chain-mode"
```

#### Phase 2 — Acceptance

1. All unit tests in `tests/test_fingerprint_bust.py` green (≥5 tests).
2. `scripts/monitoring/monitor_ingest_topic_batches/fingerprint_bust.py --help` prints usage with `--dry-run`, `--confirm`, `--force-multi`, `--topics`, `--topic` flags.
3. Rehearsal on `laboral` produces Falkor `TopicNode{topic_key:"laboral"}` count=1 and `TEMA` edges >0.
4. Heartbeat rendered with `--chain-state-file` shows `Chain progress` + `Total ETA` rows.
5. `artifacts/fingerprint_bust/plan.json` is valid JSON covering all 39 topics in 8 batches.

#### Phase 2 — State log

```yaml
phase_2_tool_and_rehearsal:
  status: pending
  started_at:
  completed_at:
  branch: feat/ingestionfix-v3-phase-2-tool
  commit:
  files_modified: []
  files_created: []
  tests_passing: []
  rehearsal_result:
    topic: laboral
    bust_row_count:
    falkor_topic_node_after:
    falkor_tema_edges_after:
  notes: ""
  resumption_hint: ""
```

---

### Phase 2.5 — Sector reclassification of `otros_sectoriales`

**Goal.** Turn the 510-doc catch-all bucket into ~12-15 clean sector topics + migrate ~30-60 misclassified docs into existing named topics, BEFORE the Phase 3 chain permanently encodes the bad taxonomy into Falkor TopicNode/TEMA state. See §2.2 for the investigation that motivated this phase.

**Why before Phase 3, not after.** Phase 3 is the step that materializes TopicNodes + TEMA edges into Falkor. Running it with `otros_sectoriales` intact creates one giant misleading TopicNode with 510 edges; splitting it afterwards means tearing down Falkor state + re-materializing — a much bigger blast-radius operation than just getting it right the first time.

**Six sub-tasks (A → F), sequential, operator-gated at B and D.**

#### Phase 2.5 — Files to create

| Path | Purpose |
|---|---|
| `scripts/monitoring/monitor_sector_reclassification/sector_classify.py` | LLM-assisted title classifier. Reads the 510 `otros_sectoriales` doc titles + first ~2 paragraphs, asks Gemini to bucket each into one of: existing top-level topic (migration), proposed new sector topic, or `otros_sectoriales_true` (genuinely orphan). Emits `artifacts/sector_reclassification_proposal.json`. |
| `artifacts/sector_reclassification_proposal.json` | Proposed per-doc map: `{doc_id → {proposed_topic, confidence, reasoning, current_tema}}`. Operator reviews + adjusts before anything mutates. |
| `scripts/monitoring/monitor_sector_reclassification/apply_sector_reclassification.py` | Applies the operator-approved proposal. Two writes per doc: (1) update `documents.tema`, (2) null `documents.doc_fingerprint` (so additive reingest regenerates chunks + edges with the new topic). Same safety rails as `fingerprint_bust.py` (dry-run default, `--confirm` required, manifest-before-execute). |
| `tests/test_sector_classify.py` | Unit tests on pure classifier helpers (prompt construction, response parsing, bucket-validation). |
| `tests/test_apply_sector_reclassification.py` | Unit tests on the migration writer (dry-run safety, confirm-required, manifest integrity). |

#### Phase 2.5 — Files to modify

| Path | Change |
|---|---|
| `config/topic_taxonomy.json` | Add new top-level sector entries (one per approved new sector; version bumped `v2026-04-21-v2` → `v2026-04-NN-v3`). |
| `config/subtopic_taxonomy.json` | If operator chooses to model some new sectors with subtopics, mirror there. |
| `artifacts/fingerprint_bust/plan.json` | Bump `plan_version` → `v3.1`. Replace the single `otros_sectoriales` batch with the new per-sector topic breakdown; add `revisions_log` entry citing §2.1 + §2.2. |

#### Phase 2.5 — Sub-tasks

**A — LLM title classification pass** *(`sector_classify.py`; ~30 min wall; ~$0.50 Gemini cost)*

* Input: 510 `doc_id`s from the `otros_sectoriales` probe manifest.
* For each doc: read `knowledge_base/<path>` (prefer `consolidado/` version if it exists since it's the richest), take the first heading line + first ~2 paragraphs as the classification signal.
* Prompt Gemini with a 3-bucket decision tree: (a) **migrate to existing topic X** (list the 39 names); (b) **new sector topic** (free-form label); (c) **true orphan**.
* For (b), cluster the free-form labels post-hoc into ~12-15 canonical sector names.
* Emit `artifacts/sector_reclassification_proposal.json`. No writes to Supabase.

**B — Operator review of proposal** *(operator-driven; ~1-2 hrs)*

* Operator reads the proposal, adjusts bucket assignments, consolidates free-form sector labels.
* Particularly important: confirm the `confidence: low` rows and the `migrate to existing topic` rows, since those directly move docs between topic_keys (harder to undo cleanly than staying in otros_sectoriales).
* Output: `artifacts/sector_reclassification_proposal.approved.json` with a checksum and `approved_by` field.

**C — Taxonomy update** *(operator-driven; ~20 min)*

* Add each new approved sector as a top-level entry in `config/topic_taxonomy.json` (with aliases, `vocabulary_status: "ratified_v3_0"`).
* Bump taxonomy version; run `PYTHONPATH=src:. uv run pytest tests/test_subtopic_taxonomy_loader.py` to lock.

**D — plan.json v3.1 rewrite** *(operator-driven; ~15 min)*

* Replace `otros_sectoriales` batch 9 entry with new per-sector batches.
* Recompute batch sizes using the approved proposal.
* Add `plan_version: v3.1` + `revisions_log` citing §2.1 + §2.2.
* Re-run `bash scripts/launch_batch.sh --batch 1 --dry-run` to confirm counts still match expectations.

**E — `tema` migration** *(`apply_sector_reclassification.py`; ~5 min wall; production write — gated by `--confirm`)*

* For each doc in the approved proposal: `UPDATE documents SET tema=<new_topic>, doc_fingerprint=NULL WHERE doc_id=?`
* Null-fingerprinting ensures the next additive run regenerates chunks/edges with the new topic classification.
* Writes a per-run manifest to `artifacts/sector_reclassification/<ts>.json`.

**F — Re-probe** *(~2 min wall; read-only)*

* Re-run the per-topic tally from §2.1.1. Expect `otros_sectoriales` to drop from 510 to ~10 (the true orphans), new sector topics to match the approved proposal, and existing topics (e.g. `laboral`, `procedimiento_tributario`) to have absorbed their migration docs.
* Record the post-migration tally in `§8 phase_2_5_sector_reclassification.post_migration_tally`.

#### Phase 2.5 — Tests

| Test | File | Locks |
|---|---|---|
| `test_classify_response_parses_valid_json` | tests/test_sector_classify.py | Gemini response parser handles well-formed output |
| `test_classify_response_handles_malformed_json` | tests/test_sector_classify.py | Falls back to `needs_review` bucket, doesn't crash |
| `test_classify_prompt_includes_all_existing_topics` | tests/test_sector_classify.py | Prompt lists all 39 current taxonomy keys so LLM can migrate |
| `test_classify_skips_docs_without_readable_content` | tests/test_sector_classify.py | A zero-byte file or parser-fallback stub gets routed to `needs_review`, not silently lost |
| `test_proposal_shape_validates` | tests/test_sector_classify.py | Output JSON has expected shape + required fields |
| `test_apply_dry_run_performs_no_writes` | tests/test_apply_sector_reclassification.py | `--dry-run` default; no UPDATE issued |
| `test_apply_requires_approved_proposal_file` | tests/test_apply_sector_reclassification.py | Refuses a raw (non-approved) proposal; requires `.approved.json` extension + checksum |
| `test_apply_writes_manifest_before_mutation` | tests/test_apply_sector_reclassification.py | Manifest-before-execute invariant (mirrors fingerprint_bust) |

#### Phase 2.5 — Acceptance

1. `artifacts/sector_reclassification_proposal.json` exists with entries for all 510 `otros_sectoriales` doc_ids.
2. Operator-approved `artifacts/sector_reclassification_proposal.approved.json` exists with `approved_by` + `approved_at` (Bogotá AM/PM).
3. `config/topic_taxonomy.json` version bumped; new sector topics present; taxonomy loader tests green.
4. `artifacts/fingerprint_bust/plan.json` bumped to `plan_version: v3.1` with new per-sector batches.
5. Post-migration re-probe shows `otros_sectoriales` doc count drops from 510 to ≤~10 (true orphans only).
6. Unit tests green on both new scripts.

#### Phase 2.5 — State log

```yaml
phase_2_5_sector_reclassification:
  status: pending
  started_at:
  completed_at:
  branch: feat/ingestionfix-v3-phase-2-5-sectors   # suggested
  sub_task_A_llm_pass:
    status:
    proposal_path: artifacts/sector_reclassification_proposal.json
    doc_count_classified:
    new_sector_labels_proposed: []
    migration_candidate_count:
    true_orphan_count:
    gemini_cost_usd:
  sub_task_B_operator_review:
    status:
    approved_proposal_path: artifacts/sector_reclassification_proposal.approved.json
    approved_by:
    approved_at:
    operator_overrides_count:        # how many LLM assignments the operator changed
  sub_task_C_taxonomy_update:
    status:
    new_topics_added: []
    taxonomy_version_bumped_to:
  sub_task_D_planjson_v3_1:
    status:
    plan_version: v3.1
    new_batch_count:
  sub_task_E_tema_migration:
    status:
    rows_updated:
    migration_manifest:
  sub_task_F_reprobe:
    status:
    otros_sectoriales_after:
    new_topic_tallies: {}
  notes: ""
  resumption_hint: ""
```

---

### Phase 3.0 — Batch 1 Quality Gate (MANDATORY before Phase 3)

**Goal.** Run ONLY batch 1 from the 8-batch plan, then validate it exhaustively before the autonomous chain is allowed to proceed. Physically blocks batches 2–8 until `artifacts/batch_1_quality_gate.json` shows `status=passed`.

#### Phase 3.0 — Files to modify

| Path | Change |
|---|---|
| `scripts/monitoring/monitor_ingest_topic_batches/run_topic_backfill_chain.sh` | Add: at startup, read `artifacts/batch_1_quality_gate.json`; if missing or `status!=passed`, exit 2 with a message telling the operator what to do. Also add `--gate-only` mode that runs batch 1 and stops. |

#### Phase 3.0 — Files to create

| Path | Purpose |
|---|---|
| `scripts/monitoring/monitor_ingest_topic_batches/validate_batch.py` | Runs G1–G10 automated checks + G-summary writes `artifacts/batch_<N>_quality_gate.json` |
| `artifacts/batch_1_quality_gate.json` | Written by `validate_batch.py --batch 1 --gate`; operator manually fills M1–M3 + U1–U4 results |
| `tests/test_validate_batch.py` | Unit tests for each G-check against mock client data |

#### Phase 3.0 — The check inventory

**Automated checks (G1–G10)** — run by `scripts/monitoring/monitor_ingest_topic_batches/validate_batch.py --batch 1 --gate`:

| ID | Check | How verified |
|---|---|---|
| G1 | Fingerprint-bust applied | `count documents WHERE tema IN batch1_topics AND retired_at IS NULL` == bust manifest `row_count` |
| G2 | Bust-targeted docs got fresh chunks | `count DISTINCT doc_id FROM document_chunks WHERE doc_id IN manifest.doc_ids` == `row_count` |
| G3 | Per-topic Falkor Topic node populated | For each topic in batch 1: Cypher `MATCH (t:TopicNode {topic_key: $key}) RETURN count(t)` returns 1 |
| G4 | Per-topic TEMA edges > 0 | For each topic: `MATCH ()-[e:TEMA]->(t:TopicNode {topic_key: $key}) RETURN count(e)` > 0 |
| G5 | No unexpected failure events | `grep -E 'delta_<batch_1_delta_id>.*(error\|failed\|exception)' logs/events.jsonl` returns empty |
| G6 | Sink idempotency | Re-run `fingerprint_bust --topics batch_1_topics --dry-run` → reports `0 rows would be affected` (all fingerprints re-persisted) |
| G7 | Cross-batch isolation | `fingerprint_bust --topics batch_2_topics --dry-run` → zero overlap with `manifest.doc_ids` from batch 1 |
| G8 | `embedding IS NULL` = 0 post-batch | Supabase count query (assumes 9.B ran after the batch) |
| G9 | Reingest wall time in expected range | Batch 1 `delta_run.elapsed_ms` between 5 and 25 minutes |
| G10 | Zero data-shape anomalies | `count document_chunks WHERE doc_id IN manifest.doc_ids AND (chunk_text IS NULL OR chunk_text = '')` == 0 |

**Manual smokes (M1–M3)** — operator runs, records result in the gate file:

| ID | Check |
|---|---|
| M1 | Pick one topic from batch 1; run representative query through `hybrid_search` RPC; ≥1 chunk from a batch-1-modified doc in top-10; record query + top-3 chunk_ids |
| M2 | `npm run dev:staging`; ask a batch-1-topic question; confirm `response.diagnostics.retrieval_backend == "supabase"` AND citations include a batch 1 doc |
| M3 | `make eval-c-gold`; score must not regress by more than 2 points vs pre-batch-1 baseline |

**Ultra-tests (U1–U4)** — belt-and-suspenders; run after G+M pass:

| ID | Check |
|---|---|
| U1 | Row-level materialization audit — for every `doc_id` in manifest: (a) `documents` row exists with non-NULL `doc_fingerprint`, (b) `document_chunks` count > 0, (c) ≥1 `normative_edges` row prefixed by the doc's article keys, (d) Falkor ArticleNode exists for every article key. Emits `artifacts/batch_1_ultra_audit.jsonl` |
| U2 | Re-run idempotency — `scripts/launch_phase9a.sh` again; expected `touched_total ≤ 5`, `chunks_written == 0` |
| U3 | Regression suite replay — `PYTHONPATH=src:. uv run pytest tests/test_dangling_store.py tests/test_loader_delta.py tests/test_falkor_loader_thematic.py tests/test_ingest_cli_additive.py -v` → 90+ tests, 0 failures |
| U4 | Heartbeat + chain stop-resume integration — `touch artifacts/STOP_BACKFILL` during a 30s yield window; chain halts; state file shows `done_batches_log[0].batch==1`; resume via `rm STOP_BACKFILL && bash scripts/monitoring/monitor_ingest_topic_batches/run_topic_backfill_chain.sh` advances to batch 2 |

#### Phase 3.0 — Tests (on the validator itself)

| Test name | File | What it locks |
|---|---|---|
| `test_G1_fingerprint_applied_mock` | tests/test_validate_batch.py | Given mock manifest + mock Supabase count, G1 returns passed/failed correctly |
| `test_G3_per_topic_falkor_missing` | tests/test_validate_batch.py | If a topic in batch 1 has no TopicNode, G3 fails with useful message |
| `test_G6_idempotency_dryrun_nonzero_fails` | tests/test_validate_batch.py | If re-running bust dry-run reports >0 rows, G6 marks failed |
| `test_G7_cross_batch_overlap_detected` | tests/test_validate_batch.py | Synthetic overlap scenario is caught |
| `test_gate_file_written_on_completion` | tests/test_validate_batch.py | `--gate` flag writes valid JSON with all fields |
| `test_gate_refuses_run_if_status_not_passed` | tests/test_run_topic_backfill_chain.py (new, minimal) | Shell-out harness asserts chain runner exits 2 when gate file missing or status!=passed |

Run just these:
```bash
PYTHONPATH=src:. uv run pytest tests/test_validate_batch.py -v
PYTHONPATH=src:. uv run pytest tests/test_run_topic_backfill_chain.py -k gate -v
```

#### Phase 3.0 — Run

```bash
# Create validator + tests
$EDITOR scripts/monitoring/monitor_ingest_topic_batches/validate_batch.py
$EDITOR tests/test_validate_batch.py
PYTHONPATH=src:. uv run pytest tests/test_validate_batch.py -v   # must pass

# Extend chain runner to enforce the gate
$EDITOR scripts/monitoring/monitor_ingest_topic_batches/run_topic_backfill_chain.sh
$EDITOR tests/test_run_topic_backfill_chain.py
PYTHONPATH=src:. uv run pytest tests/test_run_topic_backfill_chain.py -k gate -v

# Run batch 1 only (via chain runner's --gate-only mode)
bash scripts/monitoring/monitor_ingest_topic_batches/run_topic_backfill_chain.sh --gate-only
# ... wait ~10-15 min, heartbeat shows progress

# After batch 1 completes, run the validator
python scripts/monitoring/monitor_ingest_topic_batches/validate_batch.py --batch 1 --gate

# Operator performs M1-M3 manually; fills M1-M3 + U1-U4 results in
# artifacts/batch_1_quality_gate.json; sets status=passed once all green.
# Then commits the gate artifact (plus any code changes) to the branch.

git add -A
git commit -m "feat(ingestionfix-v3-phase-3-0): Batch 1 Quality Gate — validator + gate enforcement"
```

#### Phase 3.0 — Acceptance

1. `scripts/monitoring/monitor_ingest_topic_batches/validate_batch.py --batch 1 --gate` exits 0 (all G1–G10 green).
2. `artifacts/batch_1_quality_gate.json` exists with `status: passed`, operator initials in `approved_by`, approved_at timestamp in Bogotá AM/PM.
3. All M1–M3 recorded with supporting data (query, top-3 chunk_ids, retrieval_backend, score delta).
4. All U1–U4 passed; `artifacts/batch_1_ultra_audit.jsonl` written and non-empty.
5. v2 regression suite (90+ tests) all green.
6. `scripts/monitoring/monitor_ingest_topic_batches/run_topic_backfill_chain.sh` (without `--gate-only`) on a missing/failing gate file exits 2 with an instructive message.

#### Phase 3.0 — State log

```yaml
phase_3_0_quality_gate:
  status: pending
  started_at:
  completed_at:
  branch: feat/ingestionfix-v3-phase-3-0-gate
  commit:
  files_modified: []
  files_created: []
  tests_passing: []
  batch_1_delta_id:
  gate_file: artifacts/batch_1_quality_gate.json
  ultra_audit_file: artifacts/batch_1_ultra_audit.jsonl
  auto_checks:
    G1_fingerprint_bust_applied:
    G2_docs_got_chunks:
    G3_per_topic_falkor_populated:
    G4_per_topic_tema_edges:
    G5_no_failure_events:
    G6_sink_idempotency:
    G7_cross_batch_isolation:
    G8_null_embed_zero:
    G9_walltime_in_range:
    G10_no_data_shape_anomalies:
  manual_smokes:
    M1_retrieval_spot_check:
    M2_main_chat_e2e:
    M3_eval_c_gold_delta:
  ultra_tests:
    U1_row_level_audit:
    U2_idempotency_rerun:
    U3_regression_suite:
    U4_chain_stop_resume:
  operator_approved_by:
  operator_approved_at:
  notes: ""
  resumption_hint: ""
```

---

### Phase 3 — Phased topic coverage backfill (autonomous chain)

**Goal.** Populate all 39 TopicNode entries + their TEMA edges (and PRACTICA_DE where applicable) in Falkor via 8 sequential batches. Batches 2–8 run autonomously (30-second yield window between batches); each commits independently; a crash costs only that batch.

**Only runs if Phase 3.0 gate is `passed`.** Enforced by `scripts/monitoring/monitor_ingest_topic_batches/run_topic_backfill_chain.sh`.

#### Phase 3 — Batch plan

> ⚠ **SUPERSEDED by §2.1.5 (2026-04-23 probe).** The table below is the original v3.0 seed plan; it underestimated per-batch doc counts by 2-27×. See §2.1 for the actual per-topic tally (1,319 docs total) and §2.1.5 for the rebalanced v3.1 proposal (9 batches, 28-doc gate batch, `otros_sectoriales` quarantined). Treat the table below as **historical context**; `artifacts/fingerprint_bust/plan.json` will be bumped to v3.1 before the Phase-2 rehearsal runs for real.

<details><summary>Original v3.0 seed batch plan (historical — do NOT execute)</summary>

| Batch | Topics (example grouping) | Est. docs (seed) | Est. wall (seed) | Actual docs (2026-04-23 probe) |
|---|---|---|---|---|
| 3.1 | `cambiario`, `activos_exterior`, `beneficio_auditoria`, `emergencia_tributaria`, `impuestos_saludables` | ~20 | ~10 min | **552** (otros_sectoriales substituted for beneficio_auditoria in shipped plan.json) |
| 3.2 | `leyes_derogadas`, `normas_internacionales_auditoria`, `beneficiario_final_rub`, `reforma_pensional`, `economia_digital_criptoactivos` | ~25 | ~10 min | 52 |
| 3.3 | `sagrilaft_ptee`, `obligaciones_profesionales_contador`, `perdidas_fiscales_art147`, `zonas_francas`, `gravamen_movimiento_financiero_4x1000` | ~30 | ~10 min | 41 |
| 3.4 | `regimen_tributario_especial`, `regimen_simple`, `regimen_sancionatorio`, `impuesto_nacional_consumo`, `impuesto_patrimonio_personas_naturales` | ~35 | ~12 min | 45 |
| 3.5 | `precios_de_transferencia`, `contratacion_estatal`, `datos_tecnologia`, `inversiones_incentivos`, `presupuesto_hacienda`, `reformas_tributarias` | ~40 | ~13 min | 211 |
| 3.6 | `comercial_societario`, `ica`, `facturacion_electronica`, `calendario_obligaciones`, `dividendos_utilidades` | ~50 | ~15 min | 129 |
| 3.7 | `informacion_exogena`, `estados_financieros_niif`, `procedimiento_tributario`, `retencion_en_la_fuente` | ~60 | ~18 min | 107 |
| 3.8 | `declaracion_renta`, `iva`, `laboral`, `estatuto_tributario` | ~80 | ~22 min | 182 |
| | **TOTAL** | **~340** | **~110 min** | **1,319 → ~2.5-3.5 hr** |

</details>

**Use the §2.1.5 v3.1 proposal** for the actual rehearsal. Gate batch in v3.1 is `activos_exterior + emergencia_tributaria + impuestos_saludables + normas_internacionales_auditoria + perdidas_fiscales_art147 + reforma_pensional` = 28 docs.

#### Phase 3 — Autonomous chain mechanics

**30-second yield window** between batches. After a batch commits:

```
[batch 3/8 complete]
  Topic: 18 (+5)   TEMA: 23 (+7)   PRACTICA_DE: 3 (+3)
  Next batch in 30s. Touch artifacts/STOP_BACKFILL to halt.
  Polling for STOP file every 3s...
```

Polls for `artifacts/STOP_BACKFILL` every 3 seconds. If present, exits with `final_state=operator_halted`.

**Resume is trivial**: `rm artifacts/STOP_BACKFILL && bash scripts/monitoring/monitor_ingest_topic_batches/run_topic_backfill_chain.sh`. Chain reads `artifacts/backfill_state.json` → `done_batches_log[]` → skips completed batches → resumes at the next one.

#### Phase 3 — Durability contract (prior batches written in stone)

| Scenario | What happens | On resume |
|---|---|---|
| **Clean stop** (STOP_BACKFILL between batches) | Chain exits after last completed batch. `backfill_state.json` has `done_batches_log[]` through batch N. | Chain starts at N+1; completed batches skipped. |
| **Mid-batch crash** (reingest dies, OOM, reboot) | Current batch tagged `in_flight=true` in state file BEFORE destructive work. All Supabase/Falkor writes are idempotent (upsert on unique keys, MERGE). | Chain sees batch N as `in_flight`, re-runs it from top. `fingerprint_bust` on already-NULL fingerprint is a no-op. Sink writes UPDATE existing rows. Prior batches untouched. |
| **Operator nuke** (`pkill -f lia_graph.ingest`) | Same as mid-batch crash. | Same recovery path. |

**Three invariants that make this work**:

1. State-file checkpoint BEFORE destructive step (atomic temp-file + rename; no partial-write risk).
2. Row-level idempotency in every write layer (`documents.doc_id`, `document_chunks.chunk_id`, `normative_edges.(source_key,target_key,relation,generation_id)`; Falkor `MERGE`).
3. `done_batches_log[]` append-only — a batch enters it only after all downstream phases report `ok`.

#### Phase 3 — Files to modify

| Path | Change |
|---|---|
| `scripts/monitoring/monitor_ingest_topic_batches/run_topic_backfill_chain.sh` | Implement the full chain loop: read `plan.json`, for each batch {checkpoint state → bust → 9.A → verify → 30s yield with STOP poll → commit to done_batches_log}. Includes atomic state-file writes. |

#### Phase 3 — Files to create

| Path | Purpose |
|---|---|
| `artifacts/backfill_state.json` | Live state file; atomically rewritten before each batch boundary |
| `artifacts/fingerprint_bust/<ts>_batch_<N>.json` | Per-batch bust manifests |
| `artifacts/STOP_BACKFILL` | Sentinel — only created by operator |

#### Phase 3 — Tests (on the chain runner)

| Test name | File | What it locks |
|---|---|---|
| `test_chain_reads_gate_before_running` | tests/test_run_topic_backfill_chain.py | Without `batch_1_quality_gate.json status=passed`, chain exits 2 |
| `test_chain_advances_after_successful_batch` | tests/test_run_topic_backfill_chain.py | Given a fake batch that "succeeds", chain writes to `done_batches_log[]` and advances |
| `test_chain_halts_on_stop_sentinel` | tests/test_run_topic_backfill_chain.py | Creating `STOP_BACKFILL` during yield window halts cleanly |
| `test_chain_resumes_at_next_unlogged_batch` | tests/test_run_topic_backfill_chain.py | Given `done_batches_log[]=[1,2,3]`, chain starts at batch 4 |
| `test_state_file_atomic_write` | tests/test_run_topic_backfill_chain.py | State file writes use temp + rename (kill mid-write doesn't corrupt) |

Run:
```bash
PYTHONPATH=src:. uv run pytest tests/test_run_topic_backfill_chain.py -v
```

#### Phase 3 — Run

```bash
# Verify the gate is passed
jq -r .status artifacts/batch_1_quality_gate.json   # must be "passed"

# Kick off the chain (runs batches 2-8 autonomously)
bash scripts/monitoring/monitor_ingest_topic_batches/run_topic_backfill_chain.sh

# Monitor via heartbeat cron — chain writes to artifacts/backfill_state.json
# so heartbeat shows Chain progress + Total ETA

# If you need to stop between batches:
touch artifacts/STOP_BACKFILL
# chain halts cleanly after the currently-running batch commits

# Resume later:
rm artifacts/STOP_BACKFILL
bash scripts/monitoring/monitor_ingest_topic_batches/run_topic_backfill_chain.sh

# Inspect state at any time:
cat artifacts/backfill_state.json | jq
```

#### Phase 3 — Acceptance

1. All 8 batches in `artifacts/backfill_state.json` `done_batches_log[]` with `ok` status.
2. Falkor `TopicNode` count = 39 (full taxonomy).
3. Falkor `TEMA` edges count > 0 for every topic in the 39-entry taxonomy (at least one per topic).
4. Falkor `PRACTICA_DE` edges count > 0 (batches 3.7/3.8 cover práctica-heavy topics).
5. Supabase `embedding IS NULL` = 0 after final batch (9.B ran or was bundled per-batch).
6. No `.failed` events in `logs/events.jsonl` for any of the 8 batch delta_ids.
7. `test_run_topic_backfill_chain.py` green on both pre-run and post-run.

#### Phase 3 — State log

```yaml
phase_3_autonomous_chain:
  status: pending
  started_at:
  completed_at:
  branch: feat/ingestionfix-v3-phase-3-chain
  commit:
  files_modified: []
  files_created: []
  tests_passing: []
  chain_state_file: artifacts/backfill_state.json
  stop_sentinel: artifacts/STOP_BACKFILL
  batches_planned: 8
  batches_complete: 0
  batch_results:
    - batch: 1
      topics: []
      delta_id:
      falkor_topic_growth:
      falkor_tema_growth:
      falkor_practica_growth:
      wall_minutes:
    # ... one entry per batch as it completes
  final_cloud_state:
    falkor:
      TopicNode:
      TEMA_edges:
      PRACTICA_DE_edges:
  notes: ""
  resumption_hint: ""
```

---

### Phase 4 — Orphan-doc backfill (stretch; deferred)

**Goal.** Reduce the 1,523 orphan docs in Supabase (docs with no chunks). Not required for v3 close-out.

#### Phase 4 — Scope decision

The orphans are cloud-only rows from older ingests whose chunk/edge phase never landed. They're invisible to the additive path because they have no on-disk counterparts in `knowledge_base/`. Three options (pick later):

| Option | Approach | Cost |
|---|---|---|
| 4a | Write a Supabase-sourced Falkor loader — rebuild from cloud state | ~1–2 days of code + tests |
| 4b | Reimport via SUIN pipeline (`scripts/verify_suin_merge.py` + friends) | ~1 day |
| 4c | Accept the orphan count; revisit when orphan % breaches threshold (e.g. >25%) | ~0 (just doc update) |

**Recommendation**: defer to follow-up ticket. Orphans don't block users (search works on the 5,207 docs with chunks).

#### Phase 4 — Files to modify / create

TBD based on chosen option.

#### Phase 4 — Tests

TBD.

#### Phase 4 — Run

TBD.

#### Phase 4 — Acceptance

Option 4c (accept + document): v3 state ledger §8 records `phase_4_orphan_backfill.status: accepted_as_known_limitation` with a follow-up ticket ID.

#### Phase 4 — State log

```yaml
phase_4_orphan_backfill:
  status: deferred
  chosen_option:                   # 4a | 4b | 4c
  followup_ticket_id:
  notes: "Evaluated 2026-04-<NN>. Docs don't block retrieval; parking behind a threshold trigger."
```

---

### Phase 5 — Operator browser smokes (v2 Phase 10.4 + 10.5)

**Goal.** Close the two verification smokes from v2 Phase 10 that require a browser + UI navigation.

#### Phase 5 — Files to modify

| Path | Change |
|---|---|
| `docs/next/ingestionfix_v3.md §8` | Record 10.4 + 10.5 results in the v3 state ledger |
| `docs/next/ingestionfix_v2.md §7 phase_10_verification` | Mirror 10.4 + 10.5 results |

#### Phase 5 — Files to create

None.

#### Phase 5 — Tests

These are manual smokes; no automated tests.

#### Phase 5 — Run

```bash
# 10.4 — E2E main chat
npm run dev:staging &
# Open http://localhost:3000
# Login with @lia.dev test account
# Ask a práctica-heavy question (e.g. "¿cómo tramito un recurso contra sanción por no presentar exógena?")
# Check browser DevTools → Network → the /chat response JSON → diagnostics.retrieval_backend == "supabase"
# Confirm citations include at least one doc from the fresh reingest

# 10.5 — Tags tab queue
# Navigate to Ops → Tags in the same browser session
# Confirm queue shows docs with requires_subtopic_review=true from the fresh reingest
# Generate one LLM report; apply one override; re-query to verify it sticks
```

#### Phase 5 — Acceptance

1. `retrieval_backend == "supabase"` confirmed in main chat response.
2. ≥1 citation in the main-chat response is from a v3-era reingest (doc modified within the last N days).
3. Tags tab shows non-zero queue.
4. One LLM report generated successfully.
5. One override applied successfully.
6. Both results recorded in v3 §8 state ledger.

#### Phase 5 — State log

```yaml
phase_5_operator_smokes:
  status: pending
  started_at:
  completed_at:
  performed_by:                    # operator initials
  10_4_e2e_main_chat:
    result:                        # passed | failed
    retrieval_backend:
    sample_citation_doc_id:
    notes:
  10_5_tags_tab:
    result:
    queue_count:
    llm_report_doc_id:
    override_applied_doc_id:
    notes:
```

---

## §6 End-to-end execution recipe

Once Phase 2 has shipped the tools, the full v3 execution is:

```bash
# --- Phase 1: paperwork (~1 hr, manual review + frontend test) ---
git checkout -b feat/ingestionfix-v3-phase-1-paperwork
# Do the edits per §5 Phase 1
git commit -am "docs+feat(ingestionfix-v3-phase-1): close v2 paperwork"

# --- Phase 2: build tools + rehearse ---
git checkout -b feat/ingestionfix-v3-phase-2-tool
# Create scripts + tests per §5 Phase 2
PYTHONPATH=src:. uv run pytest tests/test_fingerprint_bust.py tests/test_ingest_heartbeat.py -v
# Rehearse on laboral
set -a; source .env.staging; set +a
python scripts/monitoring/monitor_ingest_topic_batches/fingerprint_bust.py --topic laboral --confirm
bash scripts/launch_phase9a.sh
# arm heartbeat cron per scripts/monitoring/README.md
# Verify Falkor growth
git commit -am "feat(ingestionfix-v3-phase-2): fingerprint_bust tool + chain skeleton + heartbeat chain-mode"

# --- Phase 3.0: Batch 1 Quality Gate ---
git checkout -b feat/ingestionfix-v3-phase-3-0-gate
# Create validator + tests
PYTHONPATH=src:. uv run pytest tests/test_validate_batch.py -v
# Run batch 1 via chain runner --gate-only
bash scripts/monitoring/monitor_ingest_topic_batches/run_topic_backfill_chain.sh --gate-only
# heartbeat cron shows batch 1 progress
# When done: validate
python scripts/monitoring/monitor_ingest_topic_batches/validate_batch.py --batch 1 --gate
# Operator: M1-M3 + U1-U4 manually, fill gate file
# Set status=passed + approved_by + approved_at
git commit -am "feat(ingestionfix-v3-phase-3-0): Batch 1 Quality Gate + validator"

# --- Phase 3: autonomous chain for batches 2-8 ---
git checkout -b feat/ingestionfix-v3-phase-3-chain
# Implement full chain runner loop
PYTHONPATH=src:. uv run pytest tests/test_run_topic_backfill_chain.py -v
bash scripts/monitoring/monitor_ingest_topic_batches/run_topic_backfill_chain.sh
# Unattended ~70-105 min; heartbeat cron every 3 min
# Inspect progress: cat artifacts/backfill_state.json | jq
# Stop cleanly if needed: touch artifacts/STOP_BACKFILL
# Resume: rm STOP_BACKFILL && bash scripts/monitoring/monitor_ingest_topic_batches/run_topic_backfill_chain.sh
git commit -am "feat(ingestionfix-v3-phase-3): autonomous chain for batches 2-8"

# --- Phase 5: operator browser smokes ---
# 10.4 + 10.5 per §5 Phase 5

# --- Final close-out ---
# Update v3 §8 state ledger with plan_version: 3.1, closed_out_at
git commit -am "docs(ingestionfix-v3): close-out — all phases green"
```

Heartbeat cron prompt pattern — same as v2's, parameterized per phase. See `scripts/monitoring/README.md`.

---

## §7 Rollback + recovery procedures

**v3 writes are idempotent.** There is no destructive rollback; recovery is always "roll forward with a fix":

- **If `fingerprint_bust` misfires (busted wrong topic)**: the busted docs get re-sink'd in the next additive run with the (same) on-disk content. Net effect: wasted classifier cycles, no data corruption.
- **If a batch writes bad data** (e.g., chunks with empty text): rare since sink already validates; if it somehow happens, re-bust the same topics with a fixed build, re-run the batch. Sink UPDATEs existing rows.
- **If the Quality Gate fails**: DO NOT advance. Diagnose from gate file detail, fix, re-run batch 1 (write idempotent), re-validate.
- **If the chain runner itself crashes mid-batch**: re-launch; state file resumes at the `in_flight` batch.
- **If `artifacts/backfill_state.json` is corrupted**: manual recovery required. Inspect `artifacts/fingerprint_bust/*.json` manifests to reconstruct `done_batches_log[]` by hand. File is small; operator edit is feasible.
- **If Supabase cloud state is catastrophically damaged** (not caused by v3; hypothetical): restore from the cold backup taken in the Pre-flight checklist (§4).

**What v3 never does**:

- Never drops tables or deletes rows in bulk.
- Never runs `make phase2-promote-snapshot` (additive mode; 9.C is no-op).
- Never modifies `corpus_generations.is_active`.
- Never deletes `normative_edges` rows on generations other than `gen_active_rolling`.

---

## §8 Global state ledger

*This section is the source-of-truth for v3 implementation status. Update at every phase transition. Commit each update.*

```yaml
plan_version: 3.0
plan_last_updated: 2026-04-23
plan_supersedes: docs/next/ingestionfix_v2.md (for forward-looking phases)
plan_signed_off_by:               # operator fills
plan_signed_off_at:               # Bogotá AM/PM

inherits_from_v2:
  shipped:
    - "Phases 1-6 (parser, source_type, topic coercion, edge typing, thematic edges, fingerprint)"
    - "Phase 7a (Tags admin backend)"
    - "Phase 9.A (reingest; final delta delta_20260423_185848_b357ed after 4 attempts)"
    - "Phase 9.B (embedding backfill; null_embed 5765 → 0)"
  outstanding_from_v2:
    - "Phase 7b: Tags admin frontend tab (deferred in v2)"
    - "Phase 8: 38 punted subtopic-miner topics (not required for v3)"
    - "Phase 10.3: Topic≥39 acceptance gap — addressed by v3 Phase 3"
    - "Phases 10.4, 10.5: browser smokes (v3 Phase 5)"
    - "Phases 11, 12: paperwork (v3 Phase 1)"

cloud_state_at_v3_start_2026_04_23:
  supabase:
    docs_live: 6730
    chunks: 19507
    embedding_null: 0
    orphan_docs_no_chunks: 1523
  falkor:
    ArticleNode: 8106
    TopicNode: 10                 # target: ≥39 after Phase 3
    SubTopicNode: 24
    TEMA_edges: 10
    PRACTICA_DE_edges: 0          # target: >0 after Phase 3

phase_1_paperwork:
  status: completed
  started_at: 2026-04-23 (Bogotá)
  completed_at: 2026-04-23 (Bogotá)
  branch: feat/ingestionfix-v2-phase9-reingest   # v3 phases riding on v2's feat branch per operator call
  commit:                                        # filled by post-commit hook / manual stamp
  files_modified:
    - docs/next/ingestionfix_v2.md               # §10.3 wording amended; plan_version 2.4 → 2.5; closed_out_at stamped
    - frontend/src/features/ingest/additiveDeltaController.ts  # buildAdditiveDeltaTerminalVm extracted; reads reportJson.sink_result
  files_created:
    - frontend/tests/additiveDeltaControllerTerminalVm.test.ts # 5 vitest cases lock the sink_result wire contract
  tests_passing:
    - additiveDeltaControllerTerminalVm            # 5 cases green; aggregated with chat/thinking/orchestration smokes (15 total)
  notes: >
    v3 introduces zero runtime env changes, so `docs/guide/orchestration.md`,
    `docs/guide/env_guide.md`, `CLAUDE.md`, `frontend/src/app/orchestration/shell.ts`,
    and `frontend/src/features/orchestration/orchestrationApp.ts` env-matrix mirrors
    are untouched (per §5 Phase 1 guidance — matrix bump only required when new flags land).
    v2 plan_version bumped to 2.5 with closed_out_at: 2026-04-23.
  resumption_hint: ""

phase_2_tool_and_rehearsal:
  status: code_complete_awaiting_rehearsal  # code + tests shipped; laboral rehearsal is operator-gated
  started_at: 2026-04-23 (Bogotá)
  code_completed_at: 2026-04-23 (Bogotá)
  branch: feat/ingestionfix-v2-phase9-reingest    # riding on v2 feat branch
  commit:                                         # stamped at commit time
  files_created:
    - scripts/monitoring/monitor_ingest_topic_batches/fingerprint_bust.py
    - scripts/monitoring/monitor_ingest_topic_batches/validate_batch.py
    - scripts/monitoring/monitor_ingest_topic_batches/run_topic_backfill_chain.sh
    - scripts/monitoring/monitor_ingest_topic_batches/README.md
    - scripts/launch_batch.sh                     # per-batch detached launcher (no more 1200+ docs per run)
    - artifacts/fingerprint_bust/plan.json        # 8-batch plan covering all 39 top-level topics
    - artifacts/fingerprint_bust/.gitkeep
    - tests/test_fingerprint_bust.py              # 9 cases
    - tests/test_validate_batch.py                # 19 cases
    - tests/test_run_topic_backfill_chain.py      # 7 cases (gate refusal / exit codes)
    - tests/test_ingest_heartbeat.py              # 7 cases (chain-state enrichment)
  files_modified:
    - scripts/monitoring/ingest_heartbeat.py      # +ChainState.from_file + --chain-state-file flag
    - scripts/monitoring/README.md                # rewritten as top-level navigation index
    - docs/next/ingestionfix_v3.md                # §0.2 repo-layout snapshot refreshed; paths bumped to new subfolder
  tests_passing:
    - test_fingerprint_bust (9/9)
    - test_validate_batch (19/19)
    - test_run_topic_backfill_chain (7/7)
    - test_ingest_heartbeat (7/7)
  pre_rehearsal_probe_2026_04_23:
    status: completed
    method: "Per-topic --dry-run SELECT across all 39 top-level taxonomy keys + one NULL-tema probe."
    total_classified_docs: 1319
    null_tema_docs: 2
    live_doc_headline_from_v1_4: 6730             # gap = 5411 rows likely under subtopic keys in tema column (F6)
    batch_1_actual_vs_planned:
      planned: 20
      actual: 552
      culprit: "otros_sectoriales (510 docs = 39% of classified corpus; taxonomy catch-all)"
    batch_5_actual_vs_planned:
      planned: 40
      actual: 211
      culprit: "reformas_tributarias (83 docs)"
    total_wall_time_revised: "2.5-3.5 hr unattended (vs 70-105 min in v3.0 seed)"
    findings_captured_in: "docs/next/ingestionfix_v3.md §2.1 + §2.1.5 rebalance proposal"
    pending_operator_action: "Apply §2.1.5 v3.1 rebalance to artifacts/fingerprint_bust/plan.json before Phase-2 rehearsal runs for real."
  rehearsal_result:
    topic: laboral
    bust_row_count:                                # operator fills during Phase 2 rehearsal
    falkor_topic_node_after:
    falkor_tema_edges_after:
    note: "Rehearsal is operator-gated (production Supabase write). Code is ready; plan.json needs v3.1 rebalance first."
  notes: >
    Sub-folder structure landed at scripts/monitoring/monitor_ingest_topic_batches/ (verbose
    name per operator preference). launch_batch.sh at scripts/ root so it sits next to
    launch_phase9a.sh for easy comparison. Durability contract (prior batches written in
    stone) baked into launch_batch.sh header + README mirror. Bundled a smoke dry-run of
    batch 1 during the rename fix: reports 552 docs in the 5 batch-1 topics (vs the
    20-doc estimate in plan.json — update estimate before rehearsal runs for real).
  resumption_hint: "Operator runs scripts/launch_batch.sh --batch 1 --dry-run first, then --batch 1 to execute."

phase_2_5_sector_reclassification:
  status: pending                                # §2.2 deep-dive found otros_sectoriales is really 3 things; this phase untangles it before Phase 3 materializes Falkor state
  added_to_plan_at: 2026-04-23 (Bogotá)
  rationale: "See §2.2: 510 otros_sectoriales docs decompose into ~30-60 misclassified rows (belong in existing named topics), ~400-450 genuinely-sectoral rows (need ~12-15 new sector topics), and ~10 true orphans. Running Phase 3 without this split would encode the catch-all permanently into Falkor TopicNode/TEMA state."
  blocks: phase_3_0_quality_gate                 # not physically enforced; operator judgment. Plan text explains why.
  sub_task_A_llm_pass:
    status: pending
  sub_task_B_operator_review:
    status: pending
  sub_task_C_taxonomy_update:
    status: pending
  sub_task_D_planjson_v3_1:
    status: pending
  sub_task_E_tema_migration:
    status: pending
  sub_task_F_reprobe:
    status: pending
  notes: "Next step: run Task A (LLM title classification). Writes no production mutations — produces artifacts/sector_reclassification_proposal.json for operator review (Task B)."

phase_3_0_quality_gate:
  status: code_complete_awaiting_operator
  code_completed_at: 2026-04-23 (Bogotá)
  files_created:
    - scripts/monitoring/monitor_ingest_topic_batches/validate_batch.py  # G1-G10
    - tests/test_validate_batch.py
  notes: "Validator + unit tests shipped. Live Phase 3.0 gate run is operator-driven once Phase 2 rehearsal completes."

phase_3_autonomous_chain:
  status: scaffolded                             # gate-enforcement skeleton shipped; full batch loop lands in Phase 3 proper
  files_created:
    - scripts/monitoring/monitor_ingest_topic_batches/run_topic_backfill_chain.sh  # skeleton + --gate-only + gate refusal
  notes: "Exit-code contract (0/1/2/3) locked by tests. Full STOP_BACKFILL poll + state-file atomic rewrites deferred to Phase 3 proper."

phase_4_orphan_backfill:
  status: deferred
  # See §5 Phase 4 State log template.

phase_5_operator_smokes:
  status: pending
  # See §5 Phase 5 State log template.

blockers_log: []

risks_log:
  - risk: "A batch fingerprint-bust succeeds but reingest crashes after sink writes."
    mitigation: "Additive sink is idempotent on doc_id; re-run just that batch. Covered by §5 Phase 3 durability contract."
  - risk: "Topic taxonomy grouping doesn't cover all docs if some have NULL tema."
    mitigation: "Phase 2 rehearsal + Phase 3.0 dry-run sanity query for NULL/unknown tema counts."
  - risk: "Fingerprint-bust via UPDATE is a Supabase production write."
    mitigation: "Operator approves once per batch per existing Production Writes gate. --dry-run always runs first."
  - risk: "Chain state file corrupted (partial JSON write, disk full)."
    mitigation: "Atomic temp-file + rename. Malformed file triggers refusal-to-auto-resume; operator must verify done_batches_log manually."
  - risk: "Topic grouping in plan.json doesn't match the tema column values in Supabase (e.g., case drift, whitespace)."
    mitigation: "Phase 2 rehearsal validates against live tema distinct values before batches run."

followups_for_later:
  - id: F1
    source: v2
    description: "Phase 7a tag_review_skeleton_flush_failed timeout — best-effort HTTPS write sometimes times out. Not blocking; investigate when flake becomes noticeable."
  - id: F2
    source: v2
    description: "Phase 8 overnight miner batch for 38 punted topics. Not required for v3."
  - id: F3
    source: v2
    description: "Second-tier expert-review items from v2 9.A triage: _load_exact N+1 read amp, case drift policy, _dedupe_nodes conflicting-duplicate semantics, validate_graph_records vs stage_node divergence. Tech-debt, not crash risks."
  - id: F4
    source: v2
    description: "Write scripts/monitoring/embedding_heartbeat.py as a proper sibling to ingest_heartbeat.py for future 9.B runs (today's 9.B used inline-python cron)."
  - id: F5
    source: v3
    description: "Orphan-doc backfill — the 1,523 cloud-only docs without chunks. See §5 Phase 4."
  - id: F6
    source: v3 (§2.1 probe)
    description: >
      `documents.tema` column likely holds subtopic keys for ~5,400 rows (classified
      1,319 vs live 6,730 — the 5,411 delta suggests subtopic-keyed rows dominate).
      Implication: TopicNode + TEMA edge population may need a second pass over rows
      whose tema is a subtopic key, not a top-level taxonomy key. Not blocking v3
      Phase 3 (the bust filter already matches whatever key is in tema), but
      materially changes what "39 TopicNodes populated" means for the full corpus.
      Verify with `SELECT tema, count(*) FROM documents WHERE retired_at IS NULL
      GROUP BY tema ORDER BY count DESC LIMIT 50;` and cross-check against
      config/topic_taxonomy.json top-level keys.
  - id: F7
    source: v3 (§2.2 otros_sectoriales deep-dive)
    description: >
      Classifier prefix/alias map (config/prefix_parent_topic_map.json +
      src/lia_graph/ingest_classifiers.py) should be audited for gaps that caused the
      §2.2 misclassification set (Ley 1066/1175 → procedimiento_tributario, Ley 1111
      → reformas_tributarias, Ley 1121 → sagrilaft_ptee, Ley 1328 → comercial_societario,
      Ley 1527 → laboral, Ley 109 → zonas_francas). Phase 2.5 migrates specific docs,
      but the classifier that put them in otros_sectoriales will keep routing similar
      future laws to the same wrong bucket unless the alias map is extended. Cheapest
      fix: add title-prefix rules for ~20 common Colombian-law-naming patterns.
```

---

## §9 Carry-forward learnings from v2

Preserved so v3 doesn't re-discover them. Full writeup in `docs/next/ingestionfix_v2.md §7 run_log_2026_04_23.lessons_learned`.

1. **Always launch detached.** `nohup + disown + >log 2>&1`. No `tee` pipes (SIGHUP cascade killed attempt #1 of 9.A).
2. **Anchor monitoring on `logs/events.jsonl`**, not the `--json` summary log (it buffers until termination).
3. **PostgREST has TWO size limits**: URL length (filter args; ~200 keys safe) and body size (upsert payloads; ~500 rows safe). Every `.in_()` and `.upsert()` needs batching.
4. **PostgREST `ON CONFLICT DO UPDATE` rejects intra-payload duplicates** (SQLSTATE 21000). Every `.upsert(list, on_conflict=...)` needs producer-side dedupe.
5. **Test mocks that are too lenient hide real bugs.** `_FakeClient` simulates SQLSTATE 21000 so regressions surface at test time.
6. **Graph schema `required_fields` are strict**: every `*_kind` needs an eligibility filter at build time AND on incoming edges (source + target).
7. **Partial completion is the worst failure mode.** Fingerprints persist before downstream phases; a crash leaves "unchanged" on the next run. `--force-full-classify` = expensive escape; **fingerprint-bust = cheaper escape** v3 introduces.
8. **Bogotá AM/PM** for all user-facing times. Machine logs stay UTC ISO.
9. **Long-running Python processes default to detached + 3-min heartbeat** per CLAUDE.md. No exceptions.
10. **Delegate code review to a subagent before shipping.** Today's expert-review loops caught real edge cases in both dangling_store and loader patches.

---

## §10 Operator cheat-sheet

Once Phase 2 has shipped the tools:

```bash
# STEP 1: gate batch 1 (MANDATORY before STEP 2)
bash scripts/monitoring/monitor_ingest_topic_batches/run_topic_backfill_chain.sh --gate-only
python scripts/monitoring/monitor_ingest_topic_batches/validate_batch.py --batch 1 --gate
# ... operator completes M1-M3 + U1-U4, marks status=passed in the gate file

# STEP 2: let the chain finish the rest (refuses to run until step 1 passes)
bash scripts/monitoring/monitor_ingest_topic_batches/run_topic_backfill_chain.sh

# During the chain: heartbeat cron every 3 min shows current batch + chain ETA
# To stop between batches (safe):
touch artifacts/STOP_BACKFILL

# To resume:
rm artifacts/STOP_BACKFILL
bash scripts/monitoring/monitor_ingest_topic_batches/run_topic_backfill_chain.sh

# Inspect state:
cat artifacts/backfill_state.json | jq
cat artifacts/batch_1_quality_gate.json | jq .status

# Phase 5 (browser smokes):
npm run dev:staging   # → http://localhost:3000 → login → main chat + Ops/Tags

# After everything green, bump plan_version to 3.1, stamp closed_out_at:
$EDITOR docs/next/ingestionfix_v3.md
git commit -am "docs(ingestionfix-v3): close-out — all phases green"
```

---

## §11 Connections to adjacent work

- **v2 triage history** — `docs/next/ingestionfix_v2.md §7 run_log_2026_04_23` is the authoritative record of the 4×40-min pain that motivated v3's chunked, gated, resumable design. Do not duplicate content; link.
- **SUIN import pipeline** — `scripts/fire_suin_cloud.sh`, `scripts/verify_suin_merge.py`. Phase 4 (orphan backfill) may need to wire against SUIN if option 4b is chosen.
- **Env matrix versioning** — `docs/guide/orchestration.md`. If v3 introduces any new `LIA_*` env or launcher flag, bump the matrix version and mirror to `docs/guide/env_guide.md` + `CLAUDE.md` per repo convention.
- **Long-running process pattern** — `CLAUDE.md` §"Long-running Python processes" (landed in v2 today). v3 builds on this; no new conventions expected.
- **Frontend tests** — `frontend/tests/additiveDeltaControllerTerminalVm.test.ts` for the Phase 1 banner fix.

---

*End of document. Operator/LLM: proceed to §4 Pre-flight checklist. If you hit any ambiguity while executing, update §8 state ledger `blockers_log[]` and surface to the user.*
