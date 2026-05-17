# fix_v23_may.md — 6-generic-weakness response to external SME audit (1.85 / 5 → ≥ 4.0 / 5)

> **Zero-agent-context protocol.** Self-contained. A fresh agent with no prior conversation can execute it by reading this file + the filesystem. Verify every artifact against `git ls-files`. If something doesn't exist, STOP and report drift.
>
> **Scope.** External Colombian-accountant audit of production (`https://liagraph-production.up.railway.app`) on 2026-05-17 scored LIA **1.85 / 5** across 10 representative questions. v23 is the mega-doc response, organized around the **6 generic weaknesses** the audit exposed, not patch-per-question. Closing gate = same SME re-runs the same 10 Qs and scores ≥ 4.0 / 5 average with zero "1 = Failed" scores.
>
> **Companion docs.** [`fix_v22_may.md`](fix_v22_may.md) — predecessor (labor anchor CST/ET; **MUST close first**). [`fix_v21_may.md`](fix_v21_may.md) — answer-shape regression closure (closed ✅ 2026-05-17 ~11:25 AM Bogotá). Plan brief: `/root/.claude/plans/here-is-a-draft-partitioned-babbage.md` (approved 2026-05-17 ~1:00 PM Bogotá).

---

## §⏯ Crash-resume pointer (update this block after EVERY step)

**Read order if you are a fresh agent resuming after a crash:** §⏯ (here) → §-1 → §11.1 preconditions → the "Next step" pointer below.

| Field | Value |
|---|---|
| Last completed step | **v23 doc scaffolded (initial)** — plan + state-tracker + 6 phases + 12 file deltas captured. No code edits yet. v22 status: 🟡 P1 not started. |
| Last touched UTC | 2026-05-17T18:00:00Z (2026-05-17 ~1:00 PM Bogotá) |
| Next step | **Wait for v22 to close** (verify `git tag --list fix_v22_closed` returns the tag). Then start v23 P1 — read `pipeline_d/_coherence_gate.py:119-141` + `pipeline_d/orchestrator.py:880-963` to confirm the existing per-sub-question coherence pattern is the right pattern to lift for decomposition. |
| Working artifact | External SME audit (verbal, 2026-05-17 ~12:30 PM Bogotá). 10 Qs scored 1.85 / 5 average. No artifact file yet — operator should drop the audit rubric at `docs/re-engineer/audits/2026-05-17_v22_external_audit.md` before P1 starts. |
| Cloud state | v20 active: cloud Supabase `gen_v20_20260516_172203` is_active=true; cloud Falkor 10,217 ArticleNodes (3,410 with norm_id), 3,401 TEMA edges. **v23 P4 will rewrite ONE knowledge_base file** (`MER-L01-guia-practica-renovacion-asamblea-EEFF-2026.md`) + run `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` (operator-gated). |
| Local state | Worktree `fix-v23-may` not yet created. v23 doc scaffolded on `claude/refine-local-plan-fNSZH` branch as the initial deliverable. Engineer should spin a real worktree via `EnterWorktree` before code work begins. |
| Uncommitted code changes | None expected at v23 start. v22 closing commits TBD. |
| Heartbeat / monitor state | None active. |
| If crashing now, resume with | (1) `git log --oneline -10` — verify v22 closing commits present (look for `ship(v22 P3-T4)` ref). (2) `git tag --list fix_v22_closed` — must exist before v23 P3 starts. (3) `git status` — should show only v23 doc work uncommitted. (4) `curl 127.0.0.1:8787 → 200` (dev:staging running). (5) Continue at "Next step" above. |
| Hard rule | After EVERY task transition, update this block + §2 phase/task tables + append a §6 run log entry. Do not batch updates. |

---

## §-1. If you are a fresh agent — read this first

You are picking up an **external-audit-driven multi-phase fix project**. v22 closes the labor-anchor mislabel (surgical, half-day). v23 closes the SIX generic weaknesses the SME audit exposed — multi-week, multi-phase. **v23 P3 cannot start until v22 closes** (P3 generalizes v22's anchor work).

**Read in this order before touching anything (max 30 min):**

1. `CLAUDE.md` (repo root) — repo operating guide. "Fast Decision Rule" + the `LIA_*` flag rows are load-bearing.
2. `AGENTS.md` (repo root) — layer ownership (surface boundaries).
3. **This file** §0 → §1 → §2 → §3 → §4.
4. [`fix_v22_may.md`](fix_v22_may.md) — predecessor, hot-fact rules and §9b hygiene canon apply.
5. [`fix_v21_may.md`](fix_v21_may.md) §6 closing entry — context on the v21 fix that exposed the v22 anchor issue.
6. Brief: `/root/.claude/plans/here-is-a-draft-partitioned-babbage.md` — the approved plan this doc was scaffolded from.

**Hot facts you must know before touching anything:**

- **Default run mode is `dev:staging`** — cloud Supabase + cloud Falkor (`LIA_REGULATORY_GRAPH`). Assume staging.
- **Cloud writes for Lia Graph are pre-authorized** — announce in chat before executing, no per-action confirmation needed. v23 P4 writes to cloud once.
- **MANDATORY server restart before EVERY probe.** Same rule as v22.
- **SME panel is OFF-LIMITS** — use `answer-engine-probe` skill for self-audit (per `feedback_sme_panel_explicit_request_only`).
- **Beta-stance applies** — every non-contradicting improvement flag flips ON (`enforce`). v23 introduces 6 new flags; 5 default `enforce`, 1 (P4 example-block filter) defaults `shadow`.
- **No text walls in docs.** Bullets/lists/tables only.

**Operator's intent (boss directive, 2026-05-17 ~12:30 PM Bogotá):**

- Quote: "Pass this test with flying colors." + "One mega-doc covering all 6 generic weaknesses, same SME re-runs same 10 Qs, target ≥ 4.0 / 5, no 1s."
- Translation: v23 is the mega-fix. Stage-gated phases. External SME closing gate replaces internal-only verdicts.

**Memory-pinned guardrails (do not violate):**

- Diagnose before intervene — every G-weakness root cause was verified by reading code, not by inference.
- Granular edits — one new module per concern (`answer_topic_decomposition.py`, `article_namespaces.py`, `year_facts.py`); don't append to the 1,407-LOC orchestrator or 1,139-LOC polish module.
- No text walls; no money quoting; no SME panel auto-run.
- Recommendations live in this canonical plan, not just chat.
- Default run mode = dev:staging.
- Thresholds NEVER lowered; new validators sit ALONGSIDE existing ones.

**The big picture in three sentences:**

- The audit surfaced 6 *generic* failure modes (G1–G6 below), not 10 isolated bugs — fixing the modes lifts every question that hits them.
- P1 (topic decomposition) alone unblocks 4/10 audit refusals; P2 + P3 fix correctness on stale-year + wrong-code citations across the remaining 6.
- P4 fixes a corpus-design issue (worked examples leaking as authoritative content) in ONE local knowledge_base file + a runtime safety net regex; P5 + P6 add small polish-time validators.

---

## §0. TL;DR

- **The gap v23 closes.** External SME audit on 2026-05-17 of `https://liagraph-production.up.railway.app` produced 1.85 / 5 average across 10 Qs. Six *generic* weaknesses identified — topic-gate refusal, stale year constants, wrong code suffix on citations, worked-example corpus leakage, user-numeric mutation, voseo-style output.
- **Why v23 exists.** A 1.85 / 5 production score is a confidence-destroying result for the accountant audience. Per-question patches don't scale — generic fixes do. Closing gate = same SME re-runs same 10 Qs, target ≥ 4.0 / 5 + zero 1s.
- **6 phases.** P1 topic-decomposition (G1; Q1/Q3/Q6/Q8). P2 year-constants (G2; Q2/Q10). P3 source-code-aware citations (G3; Q4/Q5/Q9; subsumes v22). P4 worked-example corpus + runtime filter (G4; Q5/Q9 leak). P5 input-preservation polish (G5; Q10). P6 Colombian-Spanish style (G6; Q7).
- **Time budget.** P1: 2–3 days. P2: 1–2 days. P3: 2 days. P4: 1 day. P5: 1 day. P6: 0.5 day. SME re-run + iteration: 2–5 days. Total: ~2 weeks serial; ~1 week with P2–P6 parallel after v22 closes + P1 lands.
- **Risk.** Each phase behind its own `LIA_*` flag (5 `enforce`, 1 `shadow` for P4). All flags rollback `=off` restores prior behavior. Existing 326+ test baseline must stay green; new `tests/test_audit_regression_q01_q10.py` becomes the permanent regression suite.
- **Estado al 2026-05-17 ~1:00 PM Bogotá.** v23 doc scaffolded. All 6 phases 🟡 not started. Blocked on v22 close for P3.

---

## §1. Where we are right now (post-v22 close-state expected)

### §1.1 What v22 lands (do not re-do — v23 P3 subsumes only the generalization)

- ✅ **(Expected)** Polish prompt widened to honor `(art. X CST)` form when topic = laboral.
- ✅ **(Expected)** Frontend `extractArticleRefs` emits code-aware refs (`art_cst_64` vs `art_et_115`).
- ✅ **(Expected)** Soporte Normativo panel renders CST not "Estatuto Tributario" + counter matches list length.

### §1.2 What v22 leaves undone (this is v23's mandate, 6 generic-weakness fixes)

| G | Audit failure shape | Affected Qs | Module path / root cause |
|---|---|---|---|
| **G1** | Topic-gate refusal on multi-domain Qs (e.g. "preguntas que tocan IVA + retención + laboral") | Q1, Q3, Q6, Q8 (4/10) | `src/lia_graph/pipeline_d/_coherence_gate.py:119-141` `should_refuse` + `refusal_text`; triggered at `orchestrator.py:934-963`. Per-sq fanout at `orchestrator.py:880-898` already does "accept if any coherent" — pattern to lift for decomposition. |
| **G2** | Stale year-aware constants (UVT 2025 quoted for AG 2026 Qs) | Q2, Q10 | NO year-constants registry exists. 13+ `case_bullets/*.py` hardcode `UVT 2025 $47.065`. Files: `retencion_salarios.py:12`, `depreciacion.py:22`, `inc_consumo.py:18`, `sancion_correccion.py:15`, `renta_cedular_pn.py:16`, `exogena_umbrales.py:15`, `pagos_efectivo.py:20`, `iva_responsables.py:13`, `retencion_servicios.py:17`, `niif_conciliacion_fiscal.py:12`, `sancion_extemporaneidad.py:13,15`, `dividendos_pn.py:16`, `aportes_voluntarios_pension.py:13`. `_no_invented_uvt_ranges` (`answer_llm_polish.py:737-862`) only checks vs evidence — stale evidence ⇒ stale answer. |
| **G3** | Wrong code suffix on citations beyond labor (e.g. C.Co. articles cited as ET; Ley 43/1990 not formatted properly) | Q4 (overlap v22), Q5, Q9 | `answer_inline_anchors.py:173-181` hardcodes `art. X ET`. `GraphEvidenceItem` (`contracts.py:156-203`) has no `source_code` field. Retrievers already split on dotted-`norm_id` prefix (`retriever_falkor.py:543-574`) — reuse that. v22 surgical-patches CST/ET for labor; v23 generalizes to ALL dotted prefixes. |
| **G4** | Production answer contained named-entity / acta-template strings (`DISTRIBUIDORA EL SOL SAS`, `ALEJANDRO VASQUEZ ARANGO`, `ACTA No. 8`) | Q5, Q9 fragment | **NOT cloud pollution.** Verified at `artifacts/parsed_articles.jsonl:5103` — strings live in LOCAL `knowledge_base/CORE ya Arriba/OBLIGACIONES_MERCANTILES/LOGGRO/MER-L01-guia-practica-renovacion-asamblea-EEFF-2026.md` as deliberately-authored "Ejemplo Práctico" subsection. Fix: re-chunk + anonymize the example block + add runtime safety-net regex in `chunk_quality_heuristics.py`. |
| **G5** | User-input numerics not preserved (Q10: user said `$3,000,000`, answer used `$2,000,000`); cross-year UVT mixed in one answer | Q10 | No "user input preservation" validator. Polish prompt at `answer_llm_polish.py:1113` injects `request.message` verbatim but doesn't check round-trip. No same-answer year-contradiction detector. Plug into existing chain at `answer_llm_polish.py:279-298`. |
| **G6** | Voseo in answers ("Verificá", "Tené" instead of "Verifique", "Tenga") | Q7 | No locale validator. Polish prompt at `answer_llm_polish.py:1042-1132` ITSELF uses voseo internal-instruction style (`Actuás`, `Podés`, `Devolvé`, `Quedate`) — models echo that style into output. Two-pronged: rewrite prompt voice to Colombian neutral usted + add `_no_voseo` validator. |

### §1.3 The non-negotiable invariants v23 must preserve

- **v21 + v22 substance stays.** All q01..q03 v21/v22 closing-probe verdicts must continue to pass.
- **Tax-side `(art. X ET)` form is correct and must NOT regress.** Renta, IVA, retención articles ARE ET — v23 P3 cannot break this.
- **No new corpus retirements** (CLAUDE.md non-negotiable). v23 P4 rewrites ONE file (MER-L01) + runs `phase2-graph-artifacts-supabase` — that's a sync, not a retirement.
- **No SME panel auto-run** (`feedback_sme_panel_explicit_request_only`).
- **Beta-stance applies.** New flags default `enforce` except P4 (defaults `shadow`).
- **Thresholds NEVER lowered.** New validators sit alongside existing ones.

---

## §2. State tracker (live — update this section as work progresses)

### §2.1 Phase status

| Phase | Description | Status | Owner | Last touched |
|---|---|---|---|---|
| P1 | Topic-Gate Decomposition (G1) | 🟡 not started | — | — |
| P2 | Year-Constants Service (G2) | 🟡 not started | — | — |
| P3 | Citation Source-Code Awareness (G3) | 🚫 blocked on v22 close | — | — |
| P4 | Worked-Example Corpus Fix (G4) | 🟡 not started | — | — |
| P5 | Input Preservation + Cross-Year (G5) | 🟡 not started | — | — |
| P6 | Colombian-Spanish Style (G6) | 🟡 not started | — | — |
| Closing | External SME re-run + iteration | 🚫 blocked on P1–P6 close | operator | — |

Status legend: 🟡 not started · 🔵 in progress · ✅ done · 🚫 blocked · ↩ discarded.

### §2.2 Active blockers

| # | Blocker | Affects | Owner | Surfaced |
|---|---|---|---|---|
| 1 | v22 must close (P1-P3 of v22) before v23 P3 starts | v23 P3 | operator | 2026-05-17 ~1:00 PM |
| 2 | External SME audit rubric not yet captured as a file in repo | Closing gate + permanent regression suite | operator | 2026-05-17 ~12:30 PM |

### §2.3 Active tasks (rolls up from §3 phases)

| ID | Task | Phase | Status | Owner | Blockers | Last touched |
|---|---|---|---|---|---|---|
| P0-T0 | Operator: capture SME audit rubric at `docs/re-engineer/audits/2026-05-17_v22_external_audit.md` (10 Qs verbatim + per-Q score + verdict text) | pre-P1 | 🟡 | operator | — | — |
| P1-T1 | Read `_coherence_gate.py` (119–141) + `orchestrator.py:880-963`. Confirm per-sq pattern is correct blueprint. Document decision in §9. | 1 | 🟡 | — | P0-T0 | — |
| P1-T2 | Implement `topic_safety.group_primary_articles_by_topic(primary_articles, router_topic) → list[(topic, items)]`. Reuse `_score_topic_keywords` + `_TOPIC_KEYWORDS` + `secondary_topics` from `GraphEvidenceItem`. | 1 | 🟡 | — | P1-T1 | — |
| P1-T3 | NEW `pipeline_d/answer_topic_decomposition.py` (~200 LOC). Per-group orchestrator: build sub-bundle → `answer_synthesis_sections.build_section_bullets` → polish per-section → concatenate with `## {topic}` headers + leading framing line. Cap at 3 sections. | 1 | 🟡 | — | P1-T2 | — |
| P1-T4 | Swap `_coherence_gate.refusal_text` direct branch with `decompose_groups` helper. Orchestrator narrow branch at `orchestrator.py:934-963`. | 1 | 🟡 | — | P1-T3 | — |
| P1-T5 | Add flag `LIA_TOPIC_DECOMPOSITION_MODE` to `scripts/dev-launcher.mjs` defaulting `enforce`. Mirror in CLAUDE.md + env_guide.md + orchestration.md. | 1 | 🟡 | — | P1-T4 | — |
| P1-T6 | NEW `tests/test_topic_decomposition.py` — fixture bundle with cross-topic primaries. | 1 | 🟡 | — | P1-T3 | — |
| P1-T7 | Operator: restart dev:staging server. Re-probe Q1/Q3/Q6/Q8 via `answer-engine-probe`. SME confirms each section's citations are correctly attributed. | 1 | 🟡 | operator | P1-T6 | — |
| P2-T1 | NEW `src/lia_graph/year_facts.py` (~150 LOC). `YearFacts` dataclass + `get_year_facts(year)` + `extract_fiscal_year(question, conversation_state)`. NO `date.today().year` fallback. | 2 | 🟡 | — | P0-T0 | — |
| P2-T2 | NEW `config/year_constants.json`. Seed 2024/2025/2026. Each value verified against DIAN resolution citation IN the JSON itself. | 2 | 🟡 | — | P2-T1 | — |
| P2-T3 | NEW `pipeline_d/case_bullets/_year_constants.py` — helper `render_uvt_value(uvt_count, year)`. Refactor 13 case_bullets files to use it. | 2 | 🟡 | — | P2-T2 | — |
| P2-T4 | Extend `_build_polish_prompt` (`answer_llm_polish.py:1100-1132`) with `_build_year_constants_directive`. Extend `_no_invented_uvt_ranges` (`answer_llm_polish.py:737-862`) to allow registry values + reject cross-year contradictions for detected year. | 2 | 🟡 | — | P2-T2 | — |
| P2-T5 | Flag `LIA_YEAR_CONSTANTS_INJECTION` to launcher + docs. NEW `tests/test_year_facts_integration.py`. | 2 | 🟡 | — | P2-T4 | — |
| P2-T6 | Operator: re-probe Q2 + Q10. SME confirms UVT 2026 = COP 52,374. | 2 | 🟡 | operator | P2-T5 | — |
| P3-T1 | Verify `git tag --list fix_v22_closed` exists. If not, STOP and wait. | 3 | 🚫 | — | v22 close | — |
| P3-T2 | NEW `pipeline_d/article_namespaces.py` (~80 LOC). `SourceCode` enum + `resolve_source_code(node_key)` + `format_anchor(source, articles)`. | 3 | 🚫 | — | P3-T1 | — |
| P3-T3 | Extend `GraphEvidenceItem` (`contracts.py:156-203`) with `source_code: str \| None = None`. | 3 | 🚫 | — | P3-T2 | — |
| P3-T4 | Populate `source_code` in all 3 retrievers (`retriever.py`, `retriever_supabase.py`, `retriever_falkor.py`). Reuse `_split_lookup_keys_by_property` (`retriever_falkor.py:543-574`). | 3 | 🚫 | — | P3-T3 | — |
| P3-T5 | Refactor `render_article_anchor_phrase` (`answer_inline_anchors.py:173-181`) to accept `tuple[(article, source_code), ...]`. Per-source dispatch. | 3 | 🚫 | — | P3-T4 | — |
| P3-T6 | Flag `LIA_CITATION_SOURCE_CODE_AWARENESS` + docs + `tests/test_article_namespaces.py`. | 3 | 🚫 | — | P3-T5 | — |
| P3-T7 | Operator: re-probe Q4/Q5/Q9. SME confirms code suffix correctness. Tax regression Q2/Q3 ET stays green. | 3 | 🚫 | operator | P3-T6 | — |
| P4-T1 | Edit `knowledge_base/CORE ya Arriba/OBLIGACIONES_MERCANTILES/LOGGRO/MER-L01-guia-practica-renovacion-asamblea-EEFF-2026.md`. Fence "Ejemplo Práctico" with `<!-- example-block:start -->` / `<!-- example-block:end -->`. Anonymize all 3 strings. | 4 | 🟡 | — | — | — |
| P4-T2 | Add `_EXAMPLE_BLOCK_RE` to `chunk_quality_heuristics.py`. Demote (not drop) matching chunks. | 4 | 🟡 | — | — | — |
| P4-T3 | NEW `scripts/corpus_audit/example_block_scan.py` (read-only). Outputs `tracers_and_logs/corpus_audit/<UTC>_example_block_report.md`. | 4 | 🟡 | — | — | — |
| P4-T4 | Operator: run `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` (cloud-write authorized, announce in chat). | 4 | 🟡 | operator | P4-T1, P4-T2 | — |
| P4-T5 | Flag `LIA_CHUNK_QUALITY_EXAMPLE_BLOCK_FILTER=shadow` (default shadow per design). Re-probe Q5. | 4 | 🟡 | — | P4-T4 | — |
| P5-T1 | NEW validators `_preserves_user_numerics` + `_no_inconsistent_year_constants` in `answer_llm_polish.py`. Append to `POLISH_RULES` tuple. | 5 | 🟡 | — | — | — |
| P5-T2 | Flag `LIA_POLISH_INPUT_PRESERVATION` + docs + `tests/test_polish_input_preservation.py`. | 5 | 🟡 | — | P5-T1 | — |
| P5-T3 | Operator: re-probe Q10. SME confirms numerics preserved + single-year UVT. | 5 | 🟡 | operator | P5-T2 | — |
| P6-T1 | Rewrite polish prompt internal voice at `answer_llm_polish.py:1042-1132` from voseo (`Actuás`, `Podés`, `Devolvé`) to Colombian neutral usted. | 6 | 🟡 | — | — | — |
| P6-T2 | NEW `_no_voseo` validator with regex + allowlist. Append to `POLISH_RULES`. | 6 | 🟡 | — | P6-T1 | — |
| P6-T3 | Flag `LIA_POLISH_LOCALE_STYLE_COLOMBIAN` + docs + `tests/test_polish_locale_voseo.py`. | 6 | 🟡 | — | P6-T2 | — |
| P6-T4 | Operator: re-probe Q7 + all 10 audit Qs. Voseo clean across all. | 6 | 🟡 | operator | P6-T3 | — |
| Closing-T1 | NEW `tests/test_audit_regression_q01_q10.py` — permanent regression suite. All 10 Qs must pass `answer-engine-probe` verdict = `pass`. | Closing | 🟡 | — | P1..P6 ✅ | — |
| Closing-T2 | Operator: coordinate external SME re-run of same 10 Qs on production. Store verdict at `docs/re-engineer/audits/<UTC>_v23_closing_sme_verdict.md`. | Closing | 🟡 | operator | Closing-T1 | — |
| Closing-T3 | Verify ≥ 4.0 / 5 average + zero 1s. If fails, iterate ≤ 2 cycles per affected phase. | Closing | 🟡 | operator | Closing-T2 | — |
| Closing-T4 | Tag `git tag fix_v23_closed`. Update §⏯ "Last completed step" to "v23 closed ✅". | Closing | 🟡 | operator | Closing-T3 | — |

---

## §3. The plan — 6 phases

### §3.1 Phase 1 — Topic-Gate Decomposition (G1; ~2–3 days)

**Idea.** When the coherence gate would refuse with "reformula la consulta", partition `evidence.primary_articles` by detected topic and synthesize ONE section per non-empty group. Per `feedback_multiquestion_answer_shape`: lead with framing line, headers per topic, max 3 sections.

**Plan narrow.**

1. **P1-T1**: read `pipeline_d/_coherence_gate.py:119-141` (`should_refuse` + `refusal_text`) and `pipeline_d/orchestrator.py:880-898` (per-sq fanout coherence — "accept if any coherent" pattern). Document blueprint decision in §9.
2. **P1-T2**: implement `topic_safety.group_primary_articles_by_topic(primary_articles, router_topic) → list[(topic, items)]`. Use `secondary_topics` field on `GraphEvidenceItem` + `_score_topic_keywords` lexical fallback. Already-on-topic items group under `router_topic`; rest go to their dominant topic.
3. **P1-T3**: NEW `pipeline_d/answer_topic_decomposition.py` (~200 LOC). Per-group orchestrator. Reuses existing `answer_synthesis_sections.build_section_bullets` + polish chain per section.
4. **P1-T4**: swap `_coherence_gate.refusal_text` direct branch with `decompose_groups` helper. Refusal stays as fallback if `len(groups) < 1`.
5. **P1-T5**: flag `LIA_TOPIC_DECOMPOSITION_MODE` to launcher + docs.
6. **P1-T6**: tests.
7. **P1-T7**: operator probe Q1/Q3/Q6/Q8.

**Answer-shape contract.**

```
La consulta toca {N} ámbitos: {T1}, {T2}. Respondo cada uno con su evidencia propia.

## {Topic 1 display name}
- [substantive bullet]
- [substantive bullet]

## {Topic 2 display name}
- [substantive bullet]
```

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P1-SC1 | Q1/Q3/Q6/Q8 produce sectioned substantive answers (not refusal text) | answer-engine-probe verdicts |
| P1-SC2 | `diagnostics.topic_decomposition_applied=True` | response inspection |
| P1-SC3 | `diagnostics.section_count` ∈ {2,3} | response inspection |
| P1-SC4 | No regression on Q2/Q3 ET tax regression | answer-engine-probe |
| P1-SC5 | New test `tests/test_topic_decomposition.py` green | `make test-batched` |

### §3.2 Phase 2 — Year-Constants Service (G2; ~1–2 days)

**Idea.** Inject canonical per-year fiscal constants into polish prompt + validator. Refactor 13 case_bullets files to use year-aware lookup.

**Plan narrow.**

1. **P2-T1**: NEW `src/lia_graph/year_facts.py`. `YearFacts` frozen dataclass; `get_year_facts(year)` raises if unknown; `extract_fiscal_year` regex-based, returns None on no match (NO `date.today()` fallback — see Q-Open-3).
2. **P2-T2**: NEW `config/year_constants.json`. Seed 2024/2025/2026. Each value carries its DIAN resolution citation IN the JSON.
3. **P2-T3**: NEW `pipeline_d/case_bullets/_year_constants.py` helper. Refactor 13 files (see §1.2 G2 row for the list).
4. **P2-T4**: extend `_build_polish_prompt` with `DIRECTIVA DE VALORES CANÓNICOS` block. Extend `_no_invented_uvt_ranges` to accept registry + reject contradictions.
5. **P2-T5**: flag + tests.
6. **P2-T6**: operator probe Q2 + Q10.

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P2-SC1 | Q2 quotes UVT 2026 = COP 52,374 (not 49,799 or 47,065) | answer-engine-probe |
| P2-SC2 | Q10 uses single-year UVT throughout | answer-engine-probe |
| P2-SC3 | `diagnostics.year_constants_injected.year=2026` (or whichever year detected) | response inspection |
| P2-SC4 | All 13 refactored case_bullets tests pin per-year values | `make test-batched` |

### §3.3 Phase 3 — Citation Source-Code Awareness (G3; ~2 days, BLOCKED on v22 close)

**Idea.** Stop hardcoding `ET`. Resolve every cited article via dotted-`norm_id` prefix the retrievers ALREADY split on. Generalizes v22's surgical CST/ET patch to all source codes.

**Prereq.** `git tag --list fix_v22_closed` must return the tag.

**Plan narrow.**

1. **P3-T1**: verify v22 close.
2. **P3-T2**: NEW `pipeline_d/article_namespaces.py`. Prefix table: `ET, CST, CCO, LEY_{NNNN}_{YYYY}, DEC_{NNNN}_{YYYY}, RES_DIAN_{NNN}_{YYYY}`. Display formatter.
3. **P3-T3**: extend `GraphEvidenceItem` with `source_code: str | None`.
4. **P3-T4**: populate `source_code` in all 3 retrievers. Reuse the dotted-norm_id split logic at `retriever_falkor.py:543-574`.
5. **P3-T5**: refactor `render_article_anchor_phrase` to accept `(article, source_code)` tuples. Per-source dispatch.
6. **P3-T6**: flag + tests.
7. **P3-T7**: operator probe Q4/Q5/Q9 + tax regression Q2/Q3.

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P3-SC1 | Q4 cites labor uniformly as `(art. N CST)` | answer-engine-probe |
| P3-SC2 | Q5 cites `(C.Co. art. 203)` + `(Ley 43/1990 art. 13)` | answer-engine-probe |
| P3-SC3 | Q9 has no pseudo-citations (`art. notas-y-fuentes ET`) | answer-engine-probe |
| P3-SC4 | Tax regression Q2/Q3 ET stays correct | answer-engine-probe |
| P3-SC5 | `diagnostics.citation_source_codes_used` lists distinct codes per response | response inspection |

### §3.4 Phase 4 — Worked-Example Corpus Fix (G4; ~1 day)

**Idea (CORRECTED from initial diagnosis).** "DISTRIBUIDORA EL SOL SAS" / "ALEJANDRO VASQUEZ ARANGO" / "ACTA No. 8" are NOT cloud pollution. Verified at `artifacts/parsed_articles.jsonl:5103` — they live in LOCAL `knowledge_base/CORE ya Arriba/OBLIGACIONES_MERCANTILES/LOGGRO/MER-L01-guia-practica-renovacion-asamblea-EEFF-2026.md` as a deliberately-authored "Ejemplo Práctico" subsection. Fix corpus + runtime safety net.

**Plan narrow.**

1. **P4-T1**: edit MER-L01. Fence "Ejemplo Práctico" + "PYME: Distribuidora El Sol SAS" block with `<!-- example-block:start -->` / `<!-- example-block:end -->`. Anonymize: `Distribuidora El Sol SAS` → `[Razón social]`, `Alejandro Vásquez Arango` → `[Nombre del accionista]`, `ACTA No. 8` → `ACTA No. [N]`.
2. **P4-T2**: add `_EXAMPLE_BLOCK_RE` to `chunk_quality_heuristics.py`. Demote (not drop) matching chunks. Patterns: `ACTA No\.\s*\d+`, `En Bogotá, a los \d+ días`, `[Distribuidora|SAS\b]` co-occurring with proper-name pattern.
3. **P4-T3**: NEW `scripts/corpus_audit/example_block_scan.py`. Read-only audit; outputs report at `tracers_and_logs/corpus_audit/<UTC>_example_block_report.md`.
4. **P4-T4**: operator runs `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` (cloud-write authorized).
5. **P4-T5**: flag `LIA_CHUNK_QUALITY_EXAMPLE_BLOCK_FILTER=shadow` (default shadow). Re-probe Q5.

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P4-SC1 | Q5 re-probe shows no `Distribuidora` / `Alejandro Vásquez` / `ACTA No. 8` strings | answer-engine-probe |
| P4-SC2 | `example_block_scan.py` report lists ≥ all known findings | inspect report |
| P4-SC3 | Cloud sync completes; `gen_v23_*` becomes is_active=true | Supabase query |
| P4-SC4 | Safety-net filter ships in shadow; promoted to enforce only after report reviewed | operator review |

### §3.5 Phase 5 — Input Preservation + Cross-Year Detection (G5; ~1 day)

**Idea.** Two new validators wired into existing chain at `answer_llm_polish.py:279-298`.

**Plan narrow.**

1. **P5-T1**: NEW `_preserves_user_numerics(template, polished, evidence, question)`. Extract from question: pesos, UVT counts, %. Assert each survives in polished (or clearly-equivalent form).
2. **P5-T1b**: NEW `_no_inconsistent_year_constants(polished)`. If polished mentions UVT, scan distinct values within ±5%; ≥2 ⇒ reject. Same for SMLMV.
3. **P5-T2**: flag + tests.
4. **P5-T3**: operator probe Q10.

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P5-SC1 | Q10: user's `$3,000,000` survives in polished output | answer-engine-probe |
| P5-SC2 | Q10: no two different UVT values (e.g. 47,065 + 49,799) appear in same answer | answer-engine-probe |
| P5-SC3 | Comparative-across-years answers (legitimate multi-period) stay green | regression tests |

### §3.6 Phase 6 — Colombian-Spanish Style (G6; ~0.5 day)

**Idea.** Validator + prompt directive enforce neutral Colombian Spanish (form usted). Also rewrite the polish prompt's INTERNAL voice — currently uses Argentine voseo (`Actuás`, `Podés`, `Devolvé`) which the model echoes.

**Plan narrow.**

1. **P6-T1**: rewrite polish prompt internal voice at `answer_llm_polish.py:1042-1132` to Colombian neutral usted (`Actúe`, `Puede`, `Devuelva`, `Quédese`, `Reescriba`).
2. **P6-T2**: add directive block to prompt: `"Use español colombiano neutro, forma 'usted' ... PROHIBIDO: voseo (...)"`. NEW `_no_voseo(template, polished)` validator with regex + Spanish-word allowlist (`ojalá`, `quizá`, `está`, `acá`, `allá`, `después`, `también`, etc.).
3. **P6-T3**: flag + tests.
4. **P6-T4**: operator probe Q7 + voseo-scan on all 10 Qs.

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P6-SC1 | Q7 uses 'verifique' / 'tenga presente' / 'controle' | answer-engine-probe |
| P6-SC2 | Voseo validator clean on all 10 audit Qs | answer-engine-probe |
| P6-SC3 | `diagnostics.locale_style_status=pass` | response inspection |

### §3.7 Closing Phase — External SME Re-run

1. **Closing-T1**: NEW `tests/test_audit_regression_q01_q10.py` — permanent regression suite over 10 Qs.
2. **Closing-T2**: operator coordinates same external accountant for re-run (same 10 Qs, same rubric, production deployment).
3. **Closing-T3**: verify ≥ 4.0 / 5 average + zero 1s. Iterate ≤ 2 cycles per affected phase if fails.
4. **Closing-T4**: `git tag fix_v23_closed`.

---

## §4. Files to touch (consolidated)

### §4.1 New (13)

| Path | Purpose | Phase |
|---|---|---|
| `docs/re-engineer/fix/fix_v23_may.md` | THIS FILE | scaffold |
| `src/lia_graph/year_facts.py` | YearFacts dataclass + extractor (~150 LOC) | P2 |
| `config/year_constants.json` | Per-year UVT/SMLMV/auxilio/sancion-min seeded values | P2 |
| `src/lia_graph/pipeline_d/answer_topic_decomposition.py` | Per-group synthesis orchestrator (~200 LOC) | P1 |
| `src/lia_graph/pipeline_d/article_namespaces.py` | norm_id → SourceCode resolver (~80 LOC) | P3 |
| `src/lia_graph/pipeline_d/case_bullets/_year_constants.py` | `render_uvt_value(uvt_count, year)` helper | P2 |
| `scripts/corpus_audit/example_block_scan.py` | Read-only corpus audit (G4 diagnose) | P4 |
| `tests/test_topic_decomposition.py` | P1 |
| `tests/test_year_facts_integration.py` | P2 (extractor + injection + validator) | P2 |
| `tests/test_article_namespaces.py` | P3 |
| `tests/test_polish_input_preservation.py` | P5 |
| `tests/test_polish_locale_voseo.py` | P6 |
| `tests/test_audit_regression_q01_q10.py` | Permanent regression suite — 10 audit Qs | Closing |

### §4.2 Modified

| Path | Phase | Change |
|---|---|---|
| `src/lia_graph/pipeline_d/_coherence_gate.py:119-141` | P1 | Swap refusal branch for decomposition |
| `src/lia_graph/pipeline_d/topic_safety.py` | P1 | Export `group_primary_articles_by_topic` |
| `src/lia_graph/pipeline_d/orchestrator.py:934-963` | P1 | Narrow branch into decomposition module |
| `src/lia_graph/pipeline_d/contracts.py:156-203` | P3 | `GraphEvidenceItem.source_code: str \| None` |
| `src/lia_graph/pipeline_d/retriever.py` | P3 | Populate `source_code` (artifact path) |
| `src/lia_graph/pipeline_d/retriever_supabase.py` | P3 | Populate `source_code` (Supabase path) |
| `src/lia_graph/pipeline_d/retriever_falkor.py` | P3 | Populate `source_code` (Falkor path); reuse `_split_lookup_keys_by_property` |
| `src/lia_graph/pipeline_d/answer_inline_anchors.py:173-181` | P3 | Source-code-aware formatter |
| `src/lia_graph/pipeline_d/answer_llm_polish.py:737-1132` | P2/P5/P6 | Year-constants directive + 3 new validators + voseo cleanup |
| `src/lia_graph/pipeline_d/chunk_quality_heuristics.py` | P4 | Example-block regex |
| 13 × `src/lia_graph/pipeline_d/case_bullets/*.py` (see §1.2 G2 row) | P2 | UVT/SMLMV lookup via year_facts |
| `knowledge_base/CORE ya Arriba/OBLIGACIONES_MERCANTILES/LOGGRO/MER-L01-guia-practica-renovacion-asamblea-EEFF-2026.md` | P4 | Fence + anonymize Ejemplo Práctico block |
| `scripts/dev-launcher.mjs` | all | 6 new flag defaults (5 `enforce` + 1 `shadow` for P4) |
| `CLAUDE.md` | all | 6 new flag rows; 6 new "Fast Decision Rule" entries |
| `docs/orchestration/orchestration.md` | all | Env-matrix version bump to `v2026-05-NN-fix-v23` + change log |
| `docs/guide/env_guide.md` | all | Flag mirror |

### §4.3 Touched but no change (verify only)

| Path | Verify |
|---|---|
| `src/lia_graph/pipeline_d/answer_synthesis_sections.py` | `build_section_bullets` is reusable from P1's decomposition module (no new dependency) |
| `frontend/src/features/chat/expertPanelRefs.ts` | v22's code-aware refs change is sufficient — v23 P3 backend change doesn't require frontend re-touch |
| `src/lia_graph/ui_chat_payload.py::filter_diagnostics_for_public_response` | Whitelist 6 new diagnostic keys |

---

## §5. Risks + mitigations

| Risk | P × I | Mitigation |
|---|---|---|
| Decomposition produces overly long sectioned answers | M × M | Cap 3 sections; per-section length cap; merge smallest into dominant if >3 |
| Year-constants JSON drifts (new Resolución, registry not updated) | M × H | `make verify-year-facts` CI smoke target; December annual UVT publication = operator reminder |
| Article→source-code resolver miscategorizes ambiguous numbers (CCo art. 64 vs CST art. 64) | L × M | Topic hint disambiguates; ambiguous defaults to no-citation rather than wrong-citation (see Q-Open-1) |
| Cross-year contradiction validator false-positives on legitimate multi-period answers | M × M | Validator fires only when UVT values differ by ≤ 5% (catches stale-year leakage, not comparative-across-years) |
| Example-block fix breaks anchors that depended on the chunk shape | L × M | P4 chunk-quality filter ships shadow first; corpus edit lands in same commit; rebuild + probe before promoting |
| Voseo validator over-fires on normal Spanish accented words (`está`, `acá`, `quizá`) | M × L | Explicit allowlist; validator shadow-gateable |
| External SME surfaces NEW failures outside the 10 Qs | M × M | v23 scope = the 10 Qs only; new failures captured in verdict but roll to v24 backlog |
| v22 not closed before v23 P3 starts | H × H | §-1 + §11.1 precondition checks for `git tag fix_v22_closed`; v23 P3 explicitly subsumes v22 work; P1/P2/P4/P5/P6 unblocked |

---

## §6. Run log (append-only, most recent on top, Bogotá local time)

### 2026-05-17 ~1:00 PM Bogotá — v23 doc scaffolded

- Drafted by claude-opus-4-7 on branch `claude/refine-local-plan-fNSZH` in response to operator approval of the refined plan brief at `/root/.claude/plans/here-is-a-draft-partitioned-babbage.md`.
- All 6 phases captured. P3 marked blocked on v22 close. P1/P2/P4/P5/P6 unblocked.
- 13 new files + 18 modified files documented in §4.
- 6 new `LIA_*` flags: `TOPIC_DECOMPOSITION_MODE`, `YEAR_CONSTANTS_INJECTION`, `CITATION_SOURCE_CODE_AWARENESS`, `CHUNK_QUALITY_EXAMPLE_BLOCK_FILTER` (shadow default), `POLISH_INPUT_PRESERVATION`, `POLISH_LOCALE_STYLE_COLOMBIAN`.
- G4 corrected from "cloud pollution" (initial draft) to "local worked-example block leakage" (verified at `artifacts/parsed_articles.jsonl:5103`) — fix is corpus-design, not corpus-retirement.
- No code edits in this session.

---

## §7. Six-gate lifecycle per phase

Per `CLAUDE.md` non-negotiable. Every phase below closes only when all 6 gates clear.

| Phase | Idea | Plan narrow | Success criterion | Test plan | Greenlight | Refine-or-discard |
|---|---|---|---|---|---|---|
| P1 | ✓ §3.1 | ✓ §3.1 | §3.1 P1-SC1..SC5 | New `tests/test_topic_decomposition.py` + operator probe Q1/Q3/Q6/Q8 + SME confirms ≥ 4/5 per affected Q | SME confirmation | ≤ 2 iterations; else flip `=shadow` + re-scope |
| P2 | ✓ §3.2 | ✓ §3.2 | §3.2 P2-SC1..SC4 | New `tests/test_year_facts_integration.py` + operator probe Q2/Q10 + SME confirms registry values | SME confirmation | ≤ 2 iterations |
| P3 | ✓ §3.3 | ✓ §3.3 | §3.3 P3-SC1..SC5 | New `tests/test_article_namespaces.py` + operator probe Q4/Q5/Q9 + tax-regression Q2/Q3 + SME | SME confirmation | ≤ 2 iterations |
| P4 | ✓ §3.4 | ✓ §3.4 | §3.4 P4-SC1..SC4 | Report at `tracers_and_logs/corpus_audit/<UTC>_example_block_report.md` + operator probe Q5 | Operator review of report | Flip filter to enforce only after operator confirms findings safe |
| P5 | ✓ §3.5 | ✓ §3.5 | §3.5 P5-SC1..SC3 | New `tests/test_polish_input_preservation.py` + operator probe Q10 + comparative-period regression | SME confirmation | ≤ 2 iterations |
| P6 | ✓ §3.6 | ✓ §3.6 | §3.6 P6-SC1..SC3 | New `tests/test_polish_locale_voseo.py` + operator probe Q7 + voseo-scan on all 10 | SME confirmation | ≤ 2 iterations |
| Closing | External SME re-run | §3.7 | ≥ 4.0 / 5 average + zero 1s | `tests/test_audit_regression_q01_q10.py` green + external SME verdict | Operator + SME | If fails: ≤ 2 cycles per affected phase; else snapshot + v23.1 or v24 punt |

---

## §8. Open questions (needs operator before that phase starts)

| ID | Question | Surfaces in | Notes |
|---|---|---|---|
| Q-Open-1 | For ambiguous article numbers (CCo art. 64 vs CST art. 64), should v23 silently drop the citation or render with topic-hint suffix `(art. 64 — verificar código)`? | P3-T2 | Plan prefers silent-drop with diagnostic — wrong citation worse than no citation |
| Q-Open-2 | Should P4 example-block filter demote-and-keep or hard-drop matching chunks? | P4-T2 | Plan defaults demote-and-keep + shadow flag; operator promotes after report review |
| Q-Open-3 | Should `extract_fiscal_year` fall back to `date.today().year` when no fiscal year detected? | P2-T1 | Plan defaults to None (no fallback) — risk of silent current-year injection too high |
| Q-Open-4 | What's the SME's preferred channel for the closing-gate re-run (chat dump, email, structured Form, etc.)? | Closing-T2 | Operator coordinates |

---

## §9. Decisions locked in (do not re-litigate without operator sign-off)

| # | Decision | Source | Date |
|---|---|---|---|
| D-S1 | One mega-doc covering all 6 generic weaknesses (not split v23/v24/v25) | Operator | 2026-05-17 ~12:30 PM Bogotá |
| D-S2 | Closing gate REQUIRES same external accountant + same 10 Qs; target ≥ 4.0 / 5 + zero 1s | Operator | 2026-05-17 ~12:30 PM Bogotá |
| D-S3 | G4 cloud-corpus issue: diagnose + ship runtime safety net in shadow; promote to enforce after audit findings reviewed | Operator | 2026-05-17 ~12:30 PM Bogotá |
| D-S4 | G4 root cause is LOCAL knowledge_base authoring (worked-example block in MER-L01), NOT cloud pollution. Fix corpus + runtime safety net in one phase. | Refined-plan exploration | 2026-05-17 ~1:00 PM Bogotá |
| D-S5 | Per `feedback_granular_edits`: P1 lifts decomposition into NEW `answer_topic_decomposition.py` (~200 LOC), NOT appended to 1,407-LOC orchestrator | Refined-plan exploration | 2026-05-17 ~1:00 PM Bogotá |
| D-S6 | P3 reuses dotted-norm_id split logic from `retriever_falkor.py:543-574` instead of inventing a new resolver | Refined-plan exploration | 2026-05-17 ~1:00 PM Bogotá |
| D-S7 | P2 13-file case_bullets sweep happens IN P2 (not deferred); the scope is unavoidable | Refined-plan exploration | 2026-05-17 ~1:00 PM Bogotá |
| D-S8 | P6 rewrites the polish prompt's INTERNAL voice (Argentine voseo → Colombian usted) ALONGSIDE adding the `_no_voseo` validator — instruction style leaks into output | Refined-plan exploration | 2026-05-17 ~1:00 PM Bogotá |

---

## §10. What v23 explicitly does NOT do

- Does NOT clean OTHER corpus issues beyond MER-L01 (other findings roll to v24 from P4 audit report).
- Does NOT add CGP / Decreto Único Reglamentario or other Colombian codes beyond ET / CST / CCo / Ley 43/1990 / Res. DIAN (added case-by-case as future audit re-runs surface them).
- Does NOT auto-run the SME panel (`feedback_sme_panel_explicit_request_only`).
- Does NOT raise thresholds on existing gates (`feedback_thresholds_no_lower`); only adds new validators alongside existing ones.
- Does NOT touch the canonicalizer or vigencia layer (separate concerns; v18 b2 + fix_v15 own them).
- Does NOT re-implement v22's surgical CST/ET anchor fix — v23 P3 generalizes ON TOP of v22's commits.
- Does NOT introduce a `date.today().year` fallback for year extraction (Q-Open-3 — too risky without explicit operator decision).

---

## §11. Resuming work — preconditions + first-action recipe

A fresh agent should be able to start P1 immediately after the preconditions below pass.

### §11.1 Preconditions (run all six, all must pass)

```bash
# 1. v22 closing commits landed.
git log --oneline -20 | grep -E "v22|ship(v22" && echo "OK v22 landed" || echo "MISSING — operator must close v22 first"

# 2. v22 close tag exists.
git tag --list fix_v22_closed | grep -q . && echo "OK v22 tagged closed" || echo "MISSING — v23 P3 blocked"

# 3. Local docker stack — Supabase + Falkor must be up.
docker ps --filter "name=supabase_db_lia-graph" --filter "name=lia-graph-falkor-dev" --format "table {{.Names}}\t{{.Status}}"

# 4. .env.staging exists.
test -f .env.staging && grep -q "^FALKORDB_URL=redis" .env.staging && echo "OK staging env" || echo "MISSING"

# 5. dev:staging server up + answering.
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8787/

# 6. External SME audit rubric captured.
test -f docs/re-engineer/audits/2026-05-17_v22_external_audit.md && echo "OK audit captured" || echo "MISSING — operator must capture rubric"
```

If any precondition fails, STOP and consult the relevant file (`fix_v22_may.md` for v22 state, `docs/guide/env_guide.md` for env state).

### §11.2 Phase 1 first action (after preconditions pass)

Announce in chat: "Starting v23 P1 — Topic-Gate Decomposition. Reading `_coherence_gate.py:119-141` + `orchestrator.py:880-963` to confirm per-sq pattern is the right blueprint. Expected ~30 min."

Then run:

```bash
# P1-T1a: read the coherence-gate refusal branch
grep -n "should_refuse\|refusal_text" src/lia_graph/pipeline_d/_coherence_gate.py | head

# P1-T1b: read the per-sq fanout pattern at the orchestrator
sed -n '880,898p' src/lia_graph/pipeline_d/orchestrator.py

# P1-T1c: confirm topic_safety has the building blocks
grep -n "_score_topic_keywords\|secondary_topics" src/lia_graph/pipeline_d/topic_safety.py | head
```

Document findings in §6 run log (append entry under today's date). Then move to P1-T2 (implement `group_primary_articles_by_topic`).

### §11.3 What to do after P1 closes

- Append §6 run log entry with decomposition module path + section-count diagnostic.
- Set §2.1 P1 row to ✅, P2 row to 🔵 (or start P2 in parallel since it's independent).
- Announce in chat: "v23 P1 closed — topic decomposition shipping. Ready to start P2 (year constants) in parallel with P3 prep (P3 still blocked on v22). Operator greenlight?"

### §11.4 What to do after P3 closes

- v22's surgical anchor work becomes formally subsumed. Update v22 §⏯ pointer to "subsumed by v23 P3 ✅".
- Update CLAUDE.md runtime flags table with `LIA_CITATION_SOURCE_CODE_AWARENESS`.

### §11.5 What to do after Closing gate passes

- §⏯ "Last completed step" → "v23 closed ✅"
- `git tag fix_v23_closed`.
- Update CLAUDE.md runtime flags table for all 6 new flags.
- Propose commit shape to operator: 6 phase-commits + 1 closing commit (or merge phase-commits onto a single v23 merge commit).
- Update `docs/orchestration/orchestration.md` env-matrix version + change log.
- Archive SME closing verdict at `docs/re-engineer/audits/<UTC>_v23_closing_sme_verdict.md`.

---

*Drafted 2026-05-17 ~1:00 PM Bogotá by claude-opus-4-7 in response to operator directive: "Pass this test with flying colors. One mega-doc covering all 6 generic weaknesses." Refined-plan brief: [`/root/.claude/plans/here-is-a-draft-partitioned-babbage.md`](../../../../root/.claude/plans/here-is-a-draft-partitioned-babbage.md). Companion to [fix_v22_may.md](fix_v22_may.md) (predecessor; **must close first**). Update §⏯ + §2 + §6 as work progresses.*
