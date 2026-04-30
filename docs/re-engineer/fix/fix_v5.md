# fix_v5.md — phase 6 hand-off: lift acc → strong on 8 served_acceptable qids

> **Phase 6 — SUBSTANTIVELY CLOSED 2026-04-29 ~7:25 PM Bogotá.**
> §1.G panel at **32 strong / 4 acc / 0 weak / 36 acc+** (canonical
> anchor: `evals/sme_validation_v1/runs/20260430T000527Z_fix_v5_phase6b_rerun/`).
> Net +4 strong vs phase-5 close (28 → 32). Two routes kept: Q4
> heading-reject (phase 6a, commit `8f839a8`), Q1 sub-Q topic
> carry-over (phase 6b, commit `51b1939`). One route discarded: Q2
> numeric directive (phase 6c, commit `ccf236c` — reverted same-
> commit because the new clause hit the slug-cleanup blast-radius
> pattern documented in §0). Phase 6d (Q3 sub-Q evidence fallback)
> skipped because the 4 remaining acc qids are borderline content-
> quality cases without "Cobertura pendiente" stubs (Q3's trigger).
> Phase records in §10 (6a), §11 (6b), §12 (6c discard).
>
> **Drafted 2026-04-29 ~5:35 PM Bogotá** by claude-opus-4-7 immediately
> after fix_v4 phase 5 closed (commits `6af9f22` + `0ac1a70`, panel
> 34/36 → **36/36** with 28 served_strong + 8 served_acceptable + 0
> served_weak, pushed to `origin/main`).
>
> **Audience**: zero-context agent (fresh LLM or engineer). You can
> pick this up cold, but **read fix_v4.md first** for the operating-
> mode banner, zero-context primer, ops canon, and "what you must NOT
> do" list — those carry forward unchanged. This doc layers on top.
>
> **Phase 5 — CLOSED.** §1.G panel at **36/36**. Run dir:
> `evals/sme_validation_v1/runs/20260429T215918Z_fix_v5_synthesis_fallback/`.
> Two routes shipped: Route A (polish-prompt structural-condition
> expansion at `answer_llm_polish.py:213`), Route B (synthesis empty-
> section fallback to question-reformulation shape at
> `answer_first_bubble.py:113`). Full record in fix_v4.md §11+§12.
>
> **Phase 6 — OPEN, this doc.** 36/36 is the gate; the goal now is
> **quality**: lift the 8 served_acceptable qids toward served_strong
> (and don't lose any of the 28 strong qids in the process). Five
> candidate routes Q1–Q5 below; recommended phasing 6a→6b→6c→6d.
>
> **Pre-existing learning (read this carefully)**: a slug-anchor
> cleanup attempt was tried 2026-04-29 ~5:15 PM and **discarded** per
> six-gate refine-or-discard. The change added a polish-prompt rule
> against `(art. <slug>)` patterns; outcome: slugs still leaked in 2
> qids AND 5 strong qids regressed to acceptable with 0 compensating
> promotions. Failed run dir:
> `evals/sme_validation_v1/runs/20260429T221514Z_fix_v5_slug_cleanup/`.
> **Lesson**: more polish-prompt rules don't fix this; the right layer
> for slug-anchor cleanup is the inline-anchor renderer (post-polish
> regex strip), not the prompt. Q4 below applies that learning.

---

## 0. Inheritance from fix_v4 (read once, then this doc)

Everything in fix_v4.md §0 (zero-context primer), §4 (ops canon —
fail fast, fix fast), §5 (what you must NOT do), and §6 (anchor runs)
carries forward unchanged. Specifically:

* The six-gate lifecycle is mandatory (idea / plan / measurable
  criterion / test plan / greenlight / refine-or-discard).
* `provider_order` in `config/llm_runtime.json` stays gemini-flash first.
* Don't run the full pytest suite — `make test-batched`.
* Don't write to cloud Supabase / FalkorDB.
* The phase-4 fairer-grader rule, the markdown line splitter, the
  v6 coherence gate, the v3 vigencia demotion — all keep-state.
* `LIA_*` flag matrix unchanged.

**New entry to the do-NOT list (from slug-cleanup discard)**: do NOT
add more rules to the polish-prompt to suppress LLM-emitted artifacts.
Adding text to that prompt makes it more conservative globally and
demotes other answers. Use a post-polish renderer-layer fix (regex,
deterministic) instead.

---

## 1. The diagnosis (verified 2026-04-29 against committed run dir)

The phase-5-close panel
(`evals/sme_validation_v1/runs/20260429T215918Z_fix_v5_synthesis_fallback/`,
36/36 acc+, breakdown 28/8/0/0) leaves **8 served_acceptable qids**
that the SME-grader marks as "answer is on-topic and useful but
incomplete". Read each qid's answer in
`<RUN_DIR>/<qid>.json::response.answer_markdown` to verify before
implementing — the diagnosis below is current as of the commit.

| qid | chars | polish_changed | category | the gap |
|---|---|---|---|---|
| `beneficio_auditoria_P3` | 1537 | True | A+B | both sub-Qs stubbed; answer drifted to facturación electrónica (TTD/IA/ZOMAC question) |
| `conciliacion_fiscal_P2` | 1946 | True | A+C | "¿Cómo manejo eso en el 2516?" stubbed; no math on $400M revaluación → impuesto diferido |
| `conciliacion_fiscal_P3` | 4105 | True | — | borderline strong (long, well-cited); SME grader called it acceptable; review for what it lacks |
| `descuentos_tributarios_renta_P2` | 2276 | True | C | $120M × 19% = $22.8M descuento; answer cites norms but doesn't run the calc |
| `perdidas_fiscales_art147_P2` | 2865 | True | A+C | "¿Hay límite porcentual?" stubbed; no math on $400M losses + $250M utility |
| `regimen_cambiario_P2` | 636 | False | D | bullet renders raw heading: "ARTÍCULO 26-35 — PROCEDIMIENTO #### Contenido Mínimo La declaración debe contener." |
| `regimen_sancionatorio_extemporaneidad_P1` | 1738 | True | — | borderline strong; specific UVT calc present (10 UVT = $471k); review what's missing |
| `regimen_sancionatorio_extemporaneidad_P3` | 905 | False | A+B | both sub-Qs stubbed; answer drifted to facturación electrónica (corrección voluntaria question) |

### Failure-mode categories

**A. "Cobertura pendiente" sub-Q stub leak (4 qids)**.
The decomposer fans out a multi-`¿…?` turn into N sub-queries; each
sub-Q runs through its own topic_router → planner → retriever cycle.
When one sub-Q's per-sub-Q evidence is empty, the synthesis layer
emits a stub bullet "Cobertura pendiente para esta sub-pregunta;
valida el expediente antes de cerrarla con el cliente." The 4 qids
above show this in 1 or both sub-bullets. Per the trace
(`<qid>.json::response.diagnostics.pipeline_trace.steps[*]`), the
underlying cause is per-sub-Q **topic resolution failure** — the
short sub-Q ("¿eso cambia algo?") doesn't carry enough signal for
either rule-route hit or LLM-route success, falls into
`topic_router.no_topic_detected`, and the keyword fallback either
hits nothing or hits the wrong topic.

**B. Topic hijacking on multi-domain questions (2 qids)**.
`beneficio_auditoria_P3` (TTD + IA + ZOMAC) and
`regimen_sancionatorio_extemporaneidad_P3` (corrección voluntaria +
sanción inexactitud comparison) both have answers that **drifted to
"facturación electrónica" content** — completely off-topic. The trace
shows the keyword fallback for the failing sub-Q hit
`factura_electronica` based on incidental keywords. The downstream
synthesis still found `primary_articles` (3+ chunks) but they were
all from the wrong topic, so the "Ruta sugerida" / "Riesgos" content
is about facturas, not about the actual question.

**C. Missing math on numeric questions (3 qids)**.
The question contains explicit numeric tokens ($120M IVA, $400M
revaluación, $400M losses + $250M utility) but the answer cites the
governing norms without executing the calculation. The
`regimen_sancionatorio_extemporaneidad_P2` qid (which we successfully
flipped in fix_v4 phase 5 Route B) DID get the math:
`$4.500.000 × 5% × 2 = $450.000`. The 3 acc qids in this category
have similar arithmetic potential but the polish LLM didn't run it.

**D. Synthesis raw-heading leak (1 qid)**.
`regimen_cambiario_P2` rendered a bullet that's literally the chunk's
markdown heading: "ARTÍCULO 26-35 — PROCEDIMIENTO DE DECLARACIÓN DE
CAMBIO #### Contenido Mínimo La declaración de cambio debe contener."
This is the practica chunk's section header text, surfacing through
the line splitter unchanged. `polish_changed=False` — polish refused
to expand because the trigger conditions weren't met (only 1
substantive bullet but maybe primary_count or evidence-text-quality
didn't hit the structural threshold).

### Why fix_v4 phase 5 Routes A+B didn't address these

Route A (polish-prompt structural condition) and Route B (synthesis
empty-section fallback) target the **served_weak → acc+** transition
(empty templates and refused expansions). The 8 acc qids are past
that transition: they have substantive content; what they lack is
**per-sub-Q completeness**, **calculations**, **topic-aligned
evidence**, or **synthesis-text quality**. Different layers, different
fixes.

---

## 2. The plan — five surgical routes, recommended phasing 6a→6d

### Route Q4 — synthesis line splitter rejects markdown headings (phase 6a, ship first)

**What**: in `src/lia_graph/pipeline_d/answer_support.py`, in the
`_evidence_candidate_lines` function, after splitting on `\n+` and
stripping markdown markers, **reject** lines that match the markdown-
heading pattern: `^##\s*ARTÍCULO\s+`, `####`, `^>\s*Pregunta\s*clave`,
or that are pure heading-numbering like `### PASO N`. These are
practica/expertos chunk section headers leaking through.

**Why**: `regimen_cambiario_P2`'s 636-char output IS the heading text
verbatim. The same chunk content fed to a question that triggered
the question-reformulation shape (Route B from phase 5) would be
expanded by polish into substantive content; here it slipped through
as the only candidate line and rendered raw.

**Reversibility**: revert the diff. Single function edit.

**Risk**: over-rejection of legit content. Mitigated by (1) only
matching very-specific markdown-heading patterns (not generic short
lines) and (2) the phase-5 panel is the regression check.

**Smallest diff** (~10 lines, modify `_evidence_candidate_lines`):

```python
# answer_support.py inside _evidence_candidate_lines, AFTER existing
# markdown-marker strip and BEFORE returning candidates:
_HEADING_PATTERNS = (
    re.compile(r"^#{2,4}\s"),                  # ## / ### / #### prefix
    re.compile(r"^\s*ARTÍCULO\s+\d+", re.IGNORECASE),
    re.compile(r"^\s*PASO\s+\d+\b", re.IGNORECASE),
    re.compile(r"^\s*>\s*Pregunta\s+clave", re.IGNORECASE),
    re.compile(r"####"),                       # any embedded #### marker
)
candidates = [
    line for line in candidates
    if not any(rx.search(line) for rx in _HEADING_PATTERNS)
]
```

**Expected**: regimen_cambiario_P2 → strong (or at least higher-quality
acc). 0 phase-5-passing qids regress.

**Test plan**: full §1.G panel; spot-check that the 28 strong qids
hold, that regimen_cambiario_P2's bullets no longer include heading
text, and that no other qid lost a critical bullet because its
practica chunk had a leading heading.

### Route Q1 — sub-Q topic carry-over (phase 6b, the big lever)

**What**: in `src/lia_graph/pipeline_d/decomposer.py` (or wherever the
fan-out happens — verify with `grep "decomposer.fanout" src/lia_graph/
-r`), when a sub-Q's topic resolution returns `no_topic_detected` or
`keyword_fallback` with low confidence, **inherit the parent turn's
resolved topic** instead of falling through. The parent topic is
already known from the first `topic_router.llm.success` step.

**Why**: the dominant failure pattern in the 8 acc qids is sub-Q
hijacking. Short sub-Qs ("¿eso cambia algo?", "¿la sanción es del
10%?") lose the parent context after the fan-out and get random
topics. Carrying over the parent's topic stabilizes the per-sub-Q
retrieval onto the right corpus slice.

**Reversibility**: revert the diff. No state change.

**Risk**: false-positive carry-over. If a multi-domain question has
sub-Qs that GENUINELY span different topics (e.g., a renta sub-Q +
a régimen cambiario sub-Q), forcing parent inheritance would
mis-route one of them. Mitigated by inheriting only when sub-Q
resolution returns NO topic — when sub-Q resolution gives a confident
different topic, respect that.

**Smallest diff** (~30 lines): in the sub-Q topic-resolution path,
after rule_route + LLM both miss, check if the parent turn has a
resolved topic; if so, return it instead of `no_topic_detected`. Add
a trace step `topic_router.subquery_inherited_parent` so the
diagnostic is visible in `pipeline_trace`.

**Expected**: 4 qids flip — `beneficio_auditoria_P3` (parent topic
`beneficio_auditoria`), `regimen_sancionatorio_extemporaneidad_P3`
(parent `regimen_sancionatorio_extemporaneidad`),
`conciliacion_fiscal_P2` (parent `conciliacion_fiscal`),
`perdidas_fiscales_art147_P2` (parent `perdidas_fiscales_art147`).

**Test plan**: full §1.G panel; spot-check that the 4 target qids no
longer emit "Cobertura pendiente"; verify the trace shows
`topic_router.subquery_inherited_parent` for the corresponding sub-Qs;
ensure no phase-5-passing multi-Q qid regresses by having a
genuinely-different-topic sub-Q force-inherited.

### Route Q2 — numeric-computation directive (phase 6c)

**What**: in `src/lia_graph/pipeline_d/answer_llm_polish.py`'s prompt,
add a clause AFTER the existing REGLA DE EXPANSIÓN: *"REGLA DE
CÁLCULO: si la PREGUNTA DEL USUARIO contiene cifras explícitas
(montos en pesos / dólares, porcentajes, plazos en años o meses), la
respuesta DEBE incluir el cálculo numérico aplicado a esas cifras.
Mostrá la fórmula y el resultado (e.g., '$4.500.000 × 5% × 2 meses
= $450.000'). Si la evidencia no aporta la fórmula, dejá la cifra del
usuario citada y advertí que el cálculo requiere validación con la
norma específica — no inventés tasas, topes ni porcentajes."*

**Why**: 3 acc qids have numbers in the question and no calc in the
answer. The successful Route B flip on
`regimen_sancionatorio_extemporaneidad_P2` showed the polish LLM
WILL run math when the prompt allows; right now it's not explicitly
asked for. The successful P2 example used art. 641 ET's 5%/month
formula × 2 months × $4.5M = $450k; the same shape applies to
`descuentos_tributarios_renta_P2` ($120M × 19% = $22.8M),
`perdidas_fiscales_art147_P2` ($250M offset against $400M → $150M
residual), `conciliacion_fiscal_P2` ($400M revaluation → impuesto
diferido depending on tax rate).

**Reversibility**: revert the prompt diff.

**Risk**: hallucinated math (LLM invents tax rates or formulas not in
the evidence). Mitigated by the existing no-invention guardrail
("No inventés normas, artículos, ni cifras...") and the new clause's
fallback ("Si la evidencia no aporta la fórmula, dejá la cifra del
usuario citada y advertí..."). The slug-cleanup discard cautions
against bloating the prompt — this clause is small and additive,
applies only when numeric tokens are detected in the user message.

**Smallest diff** (~5-8 lines added to the prompt). See Q4 in the
implementation §3.

**Expected**: 3 acc qids → strong (the 3 with explicit numerics).

**Test plan**: full §1.G panel; spot-check the 3 target qids show the
calculation (formula + result); verify no phase-5-passing qid
regressed quality (especially the 28 strong qids — confirm the new
clause doesn't trigger spurious math attempts on non-numeric
questions).

### Route Q3 — sub-Q evidence fallback to parent (phase 6d, only if 6a-6c don't close)

**What**: in `src/lia_graph/pipeline_d/answer_synthesis_helpers.py`
(or wherever the sub-Q rendering produces "Cobertura pendiente"),
when a sub-Q has fewer than N (say N=2) per-sub-Q evidence chunks,
**reuse the parent turn's full evidence pool** for that bullet's
content extraction instead of emitting the stub.

**Why**: even with Q1 fixing topic resolution, some sub-Qs may
still come back evidence-thin (sparse retrieval). The "Cobertura
pendiente" stub is a worst-case UX: the sibling sub-Q's chunks often
contain the answer to the stubbed sub-Q (e.g., `perdidas_fiscales_P2`
where the second sub-Q's answer says "no establece un límite
porcentual anual" — the answer to the stubbed first sub-Q).

**Reversibility**: revert the diff.

**Risk**: cross-contamination — a sibling sub-Q's evidence may be
about a different aspect, leading to an answer that's plausible but
wrong for the stubbed sub-Q. Mitigated by the polish step (which
sees both sub-Q's bullets and would catch obvious mismatches), and
by limiting the fallback to graph_native (not partial) mode.

**Smallest diff** (~25 lines): wrap the "Cobertura pendiente" emission
with a check; if `parent_evidence_pool` has chunks AND
`sub_q_evidence_count < 2`, swap in lines extracted from the parent
pool for that bullet.

**Expected**: 1-2 acc qids that Q1 didn't fully close.

### Route Q5 — multi-domain decomposer (phase 6d-extended, deeper surgery, defer)

**What**: at the decomposer step, if the user message contains ≥2
distinct topic-keywords from `config/topic_taxonomy.json`, fan out a
SEPARATE retrieval per topic and merge the evidence pool BEFORE
sub-Q topic resolution.

**Why**: Q1 fixes the symptom (sub-Q drift); Q5 fixes the root cause
(multi-domain questions need multi-domain retrieval). For
`beneficio_auditoria_P3` specifically (TTD + IA + ZOMAC), Q1 alone
will pin all sub-Qs to `beneficio_auditoria` — but the question
needs ZOMAC content too. Q5 retrieves both upfront.

**Reversibility**: revert the diff.

**Risk**: bigger surgery. Touches the orchestrator's evidence-bundle
construction. Higher chance of regressing phase-5-passing qids.

**Smallest diff**: ~50 lines + careful regression testing. **Defer
this to phase 7** unless 6a-6d leave a substantive gap.

**Expected**: deeper acc-strong shifts on multi-domain questions
(specifically the ZOMAC-cross-cuts).

### Recommended phasing

| Phase | Route(s) | Effort | Expected outcome | Stop condition |
|---|---|---|---|---|
| **6a** | Q4 (heading reject) | ½ day | regimen_cambiario_P2 → strong; 28→29 strong | Panel ≥36/36, ≥1 acc→strong, 0 strong→acc regressions, no other qid lost a critical bullet |
| **6b** | Q1 (sub-Q topic carry-over) | ½ day | 4 acc qids → strong; 29→33 strong | Same shape as 6a, larger gain expected |
| **6c** | Q2 (numeric directive) | ½ day | 3 acc qids → strong (overlaps 6b); 33→34-35 strong | Same |
| **6d** | Q3 (sub-Q evidence fallback) only if remaining acc qids | ½ day | residual acc qids → strong | Same |
| **7** (deferred) | Q5 (multi-domain decomposer) | 1-2 days | depth on ZOMAC-style multi-domain | Open new doc fix_v6.md |

**Realistic ceiling after 6a–6c**: 32-34 strong / 2-4 acceptable.
36/36 acc+ holds throughout. Each phase is its own commit, its own
6-gate sign-off, its own panel run. Three commits expected; ~1.5 days
of work end-to-end at iteration-1 success rates.

---

## 3. The implementation (numbered, copy-paste-ready)

### Step 1 — Re-verify diagnosis on all 8 acc qids (~10 min, read-only)

```bash
PYTHONPATH=src:. uv run python - <<'PY'
import json
from pathlib import Path
RUN = Path("evals/sme_validation_v1/runs/20260429T215918Z_fix_v5_synthesis_fallback")
acc_qids = ["beneficio_auditoria_P3","conciliacion_fiscal_P2","conciliacion_fiscal_P3",
            "descuentos_tributarios_renta_P2","perdidas_fiscales_art147_P2","regimen_cambiario_P2",
            "regimen_sancionatorio_extemporaneidad_P1","regimen_sancionatorio_extemporaneidad_P3"]
for qid in acc_qids:
    r = json.loads((RUN/f"{qid}.json").read_text())
    ans = r["response"].get("answer_markdown") or ""
    steps = (r["response"]["diagnostics"].get("pipeline_trace") or {}).get("steps") or []
    pol = next((s for s in steps if s.get("step") == "polish.applied"), {}).get("details") or {}
    has_stub = "Cobertura pendiente" in ans
    print(f"{qid}: chars={len(ans)}  polish_changed={pol.get('polish_changed')}  has_stub={has_stub}")
PY
```

**Expected match to §1's table**. If chars / polish_changed / has_stub
don't match per qid, the corpus or codebase changed since this doc
was written — STOP and write up the new finding.

### Step 2 — Phase 6a: implement Q4 (heading reject) (~15 min code)

```bash
grep -n "_evidence_candidate_lines\|def \|HEADING\|markdown" src/lia_graph/pipeline_d/answer_support.py | head -30
```

Locate `_evidence_candidate_lines`. Read the current splitter
(fix_v3 phase 4 Fix 2 territory — DON'T touch the splitting logic
itself; only ADD a post-split rejection of heading-shaped lines).

Apply the diff from §2 Q4. Verify `import re` is at file head; add if
missing.

Then: smoke + restart + panel + compare. Reuse the launch shape from
fix_v4.md §3 Step 4 with `RUN_DIR=...phase6a_heading_reject`.

```bash
PYTHONPATH=src:. uv run pytest tests/test_retriever_falkor.py tests/test_phase3_graph_planner_retrieval.py -q --no-header
```

Expected: 45 passed.

```bash
pkill -KILL -f "python.*lia_graph|node.*dev-launcher|npm.*dev:staging" 2>/dev/null
sleep 4
nohup npm run dev:staging </dev/null > /tmp/devstaging_v6a.log 2>&1 &
disown
until curl -s -o /dev/null -w "%{http_code}" --max-time 2 http://127.0.0.1:8787/api/health 2>/dev/null | grep -q 200; do sleep 3; done
RUN_DIR=evals/sme_validation_v1/runs/$(date -u +%Y%m%dT%H%M%SZ)_fix_v5_phase6a_heading_reject
mkdir -p "$RUN_DIR"
echo "$RUN_DIR" > /tmp/fix_v5_6a_rundir.txt
nohup bash -c "
PYTHONPATH=src:. uv run python scripts/eval/run_sme_parallel.py --run-dir '$RUN_DIR' --workers 4 --timeout-seconds 240 \
  && PYTHONPATH=src:. uv run python scripts/eval/run_sme_validation.py --classify-only '$RUN_DIR' \
  && echo PANEL_DONE
" > /tmp/fix_v5_6a_panel.log 2>&1 &
disown
```

Wait via Monitor; compare via the same script as fix_v4.md §3 Step 5
but with anchor = phase-5-close run dir
(`20260429T215918Z_fix_v5_synthesis_fallback`).

**Stop condition for 6a**: `served_acceptable+ ≥ 36/36`, `served_strong
≥ 28` (no demotions), `regimen_cambiario_P2` → either strong OR
clearly-improved acceptable (no raw heading text in bullets).

If 6a passes: commit + push, then 6b. If 6a regresses (any phase-5
strong qid demotes), revert and refine the heading regex (likely
over-matching); re-run.

### Step 3 — Phase 6b: implement Q1 (sub-Q topic carry-over) (~30 min code)

```bash
# Locate the decomposer fan-out and sub-Q topic resolution.
grep -rn "decomposer\.fanout\|subquery_resolved\|no_topic_detected" src/lia_graph/ --include="*.py" | head -20
grep -rn "def.*decompose\|def.*fanout" src/lia_graph/pipeline_d/ src/lia_graph/ --include="*.py" | head -10
```

Read the actual function bodies BEFORE writing the diff. The §2 plan
sketches the shape but the exact site needs verification — the
`topic_router` module owns the sub-Q resolution per-call, the
`decomposer` owns the fan-out, and the orchestrator wires them.
Determine which layer owns "what was the parent topic" — likely the
orchestrator passes it as `prior_topic` already (per
`docs/aa_next/next_v4 §3+§4` conversational-memory staircase), and the
sub-Q resolution can read it.

The smallest diff: in `topic_router._classify_topic_with_llm` (or its
caller), when both rule-route and LLM-route miss for a sub-Q, check if
`prior_topic` was passed; if so, return it as the resolved topic and
emit a trace step `topic_router.subquery_inherited_parent`.

Smoke + restart + panel + compare per Step 2's shape, with
`RUN_DIR=...phase6b_subq_topic_carryover`.

**Stop condition for 6b**: same as 6a + at least 2 of the 4
"Cobertura pendiente" qids flip to strong (or clearly-improved
acceptable with both sub-bullets answered).

### Step 4 — Phase 6c: implement Q2 (numeric directive) (~10 min code)

In `src/lia_graph/pipeline_d/answer_llm_polish.py`'s `_build_polish_prompt`,
AFTER the existing REGLA DE EXPANSIÓN clause (lines 215-220 as of
phase-5-close commit `0ac1a70`), ADD a new line:

```python
"REGLA DE CÁLCULO: si la PREGUNTA DEL USUARIO contiene cifras explícitas "
"(montos en pesos o dólares, porcentajes, plazos en meses o años), la respuesta DEBE "
"incluir el cálculo numérico aplicado a esas cifras. Mostrá la fórmula y el resultado "
"(e.g., '$4.500.000 × 5% × 2 meses = $450.000'). Si la evidencia no aporta la fórmula "
"explícita, dejá la cifra del usuario citada y advertí que el cálculo requiere validación "
"contra la norma específica — no inventés tasas, topes ni porcentajes que no estén en la "
"evidencia abajo.\n"
```

The discard learning from the slug-cleanup attempt applies here: this
is **one** additive clause, not a paragraph of new rules. Keep it
short. If panel regresses, REVERT — don't refine by adding more text.

Smoke + restart + panel + compare per Step 2's shape, with
`RUN_DIR=...phase6c_numeric_directive`.

**Stop condition for 6c**: `served_strong` net positive vs phase-6b
anchor; the 3 numeric-question qids show the calculation in their
answer markdown; no strong qid regressed.

### Step 5 — Phase 6d: Q3 only if 6a-6c residuals warrant

After 6c, recount acc qids. If 1-2 remain AND they show the
"Cobertura pendiente" pattern despite Q1, implement Q3 (sub-Q
evidence fallback to parent pool). If only borderline-acc qids
remain (like `conciliacion_fiscal_P3` which is already 4105 chars
of well-cited content), surface to operator before trying more
routes — at that point the SME-grader's "acceptable" judgment may
be content-quality territory beyond what these surgical routes
address, and fix_v6 should re-scope.

### Step 6 — Six-gate sign-off + commit + push (per phase)

Each phase (6a, 6b, 6c, 6d) is its own commit. The commit message
template:

```
fix_v5 phase 6X — <route name> (<prior strong>→<new strong>/36 strong)

<one-paragraph mechanism>

§1.G panel result (run dir <RUN_DIR>):
phase-<prior> anchor: <prior strong>/<prior acc>/<weak>
fix_v5 phase 6X:      <new strong>/<new acc>/<weak>
DELTA: +<acc→strong shifts>, -<strong→acc regressions> (must be 0)
<flipped qid list with brief one-line mechanism>

Six-gate record:
1. Idea: <route name>.
2. Plan: §2 Q<N> from fix_v5.md.
3. Criterion: ≥36/36 acc+ retained, served_strong net positive vs prior anchor, 0 strong→acc regressions, target qid quality verified.
4. Test plan: 45 backend smoke + 36-Q panel + spot-check target qids + N-qid no-regression spot-check.
5. Greenlight: PASS — <narrative>.
6. Keep — <residual gap or "phase 6X closed">.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

## 4. What you must NOT do (additive over fix_v4.md §5)

All entries from fix_v4.md §5 carry forward. New entries:

15. **Don't add more rules to the polish-prompt to suppress LLM-emitted
    artifacts.** Slug-cleanup discard learning. Polish-prompt rules
    have global blast radius; adding text demotes other answers
    without fixing the targeted artifact. Use renderer-layer
    deterministic fixes (regex strip, line splitter rejection)
    instead.
16. **Don't bypass the parent-topic check in Q1 by force-inheriting
    on every sub-Q.** Parent inheritance fires ONLY when sub-Q
    resolution returned `no_topic_detected` (or low-confidence
    keyword fallback). A confidently-different sub-Q topic must be
    respected — that's how multi-domain questions stay multi-domain.
17. **Don't lower the served_strong floor.** 28 strong is the phase-5
    close baseline. Any phase-6X commit must preserve `served_strong
    ≥ 28`. Net-positive on strong is required for 6b/6c/6d (because
    those phases target acc→strong); for 6a it's enough to maintain
    if the only target (regimen_cambiario_P2) flips quality even
    without flipping class.
18. **Don't combine multiple routes into one commit.** Each of Q4,
    Q1, Q2, Q3 ships separately so per-route attribution is clear in
    git history and so a regression can be isolated to a single
    diff.
19. **Don't run the panel without restarting staging** between code
    changes. The Python server caches the polish prompt + module
    state; a restart is mandatory after any `src/lia_graph/` edit.

---

## 5. Anchor runs to compare against

| Run | Date | Acc+ | Strong | Notes |
|---|---|---|---|---|
| post-fix_v3 phase-4 close | 04-29 | 34/36 | — | new fairer grader baseline |
| post-fix_v4 Route A | 04-29 | 35/36 | 25 | `20260429T214337Z_fix_v4_polish_unconditional/` |
| **post-fix_v4 Route B (phase-5 close)** | **04-29** | **36/36** | **28** | **THIS is your anchor** — `20260429T215918Z_fix_v5_synthesis_fallback/` |
| **discard: slug-cleanup attempt** | **04-29** | 36/36 | **23 (-5!)** | `20260429T221514Z_fix_v5_slug_cleanup/` — example of polish-prompt rule blast radius |
| post-fix_v5 phase 6a | TBD | target ≥36/36 | target ≥28 (29+ ideal) | this phase |
| post-fix_v5 phase 6b | TBD | target ≥36/36 | target ≥30 | this phase |
| post-fix_v5 phase 6c | TBD | target ≥36/36 | target ≥32 | this phase |

Use `20260429T215918Z_fix_v5_synthesis_fallback/` as the comparison
anchor for 6a. After 6a closes, that becomes the 6b anchor. And so on.

---

## 6. State of the world at hand-off (2026-04-29 ~5:35 PM Bogotá)

* Latest commits on `main` (pushed):
  * `0ac1a70 fix_v4 phase 5 — Route B synthesis empty-section fallback (35 → 36/36)`
  * `6af9f22 fix_v4 phase 5 — polish-trigger structural condition (34 → 35/36)`
  * `b6ea646 fix_v4.md — phase 5 hand-off for residual 2 served_weak qids (34 → ≥35/36)`
* Working tree: clean (slug-cleanup attempt reverted; no uncommitted
  changes from that attempt).
* `config/llm_runtime.json` `provider_order`: gemini-flash first.
  UNCHANGED.
* `LIA_*` flag matrix unchanged from phase-5 close (see fix_v4.md §7
  snapshot).
* `_evidence_candidate_lines` in `answer_support.py` still has the
  fix_v3 phase-4 markdown-aware splitter. UNCHANGED.
  **YOUR Q4 job: ADD a post-split heading-rejection step to it.**
* `polish_graph_native_answer` prompt in `answer_llm_polish.py` has
  the phase-5 Route A structural-condition expansion clause.
  UNCHANGED. **YOUR Q2 job: ADD a small REGLA DE CÁLCULO clause
  AFTER it (don't replace).**
* `compose_first_bubble_answer` in `answer_first_bubble.py` has the
  phase-5 Route B substantive-section fallback. UNCHANGED.
* Decomposer + sub-Q topic resolution: read first; site for Q1.
  **UNCHANGED at hand-off.**
* `tracers_and_logs/` package live; pipeline_trace step set is the
  diagnostic surface — read `<qid>.json::response.diagnostics.pipeline_trace.steps[*]`
  for any qid you need to re-diagnose.
* Cloud Supabase + cloud Falkor in-sync; no migration drift.
* Dev server: NOT running at hand-off (you'll restart in Step 2/3/4).
* `make test-batched` is the only sanctioned full-pytest path.

---

## 7. Quick-reference: file map

```
src/lia_graph/pipeline_d/
├── answer_support.py
│   └── _evidence_candidate_lines         ← MODIFY for Q4 (phase 6a, ADD heading-reject)
├── answer_llm_polish.py
│   └── _build_polish_prompt              ← MODIFY for Q2 (phase 6c, ADD REGLA DE CÁLCULO)
├── decomposer.py (or wherever fan-out lives)
│   └── fanout                            ← READ for Q1; the site is here OR in the orchestrator
├── topic_router.py
│   └── _classify_topic_with_llm          ← MODIFY for Q1 (phase 6b, ADD parent-inherit fallback)
├── answer_synthesis_helpers.py
│   └── (sub-Q rendering)                 ← MODIFY for Q3 (phase 6d, only if needed)
├── answer_first_bubble.py
│   └── compose_first_bubble_answer       ← DO NOT MODIFY (phase 5 Route B territory)
├── answer_inline_anchors.py
│   └── _anchor_label_for_item            ← DO NOT MODIFY (phase 4 territory; slug cleanup
│                                            is post-polish renderer territory if you ever
│                                            attempt it again — see lesson in §0)
├── retriever_supabase.py                 ← DO NOT MODIFY
├── _coherence_gate.py                    ← DO NOT MODIFY
└── topic_safety.py                       ← DO NOT MODIFY

config/
├── llm_runtime.json                      ← DO NOT MODIFY
└── topic_taxonomy.json                   ← READ for Q5 (deferred)

scripts/eval/
├── run_sme_parallel.py                   ← invoke; DO NOT MODIFY
└── run_sme_validation.py                 ← invoke; DO NOT MODIFY (phase-4 grader is keep-state)

scripts/dev-launcher.mjs                  ← DO NOT MODIFY

evals/sme_validation_v1/runs/
├── 20260429T215918Z_fix_v5_synthesis_fallback/  ← phase-5-close anchor (28/8/0)
└── 20260429T221514Z_fix_v5_slug_cleanup/        ← discard example (23/13/0) — read to understand
                                                    the blast radius of polish-prompt rule additions

docs/re-engineer/fix/
├── fix_v1.md, fix_v1_diagnosis.md        ← READ for history
├── fix_v2.md                             ← READ §A for context
├── fix_v3.md                             ← READ §13 for phase-4 close
├── fix_v4.md                             ← READ §0 + §5 (do-not-do list) before any code
└── fix_v5.md                             ← THIS FILE (update at end of each phase)
```

---

## 8. After you ship each phase

1. **Append a §N close-record to this file** (`docs/re-engineer/fix/fix_v5.md`)
   matching fix_v4.md §11/§12's shape — panel result, run dir, route used,
   six-gate record, residual gaps. Use the "ARCHIVED — discarded" pattern
   for any route you tried and dropped (the slug-cleanup pattern in §0
   is the template).
2. **Update the header banner** to reflect the latest phase status.
3. After phase 6c: if `served_strong ≥ 32`, fix_v5 phase 6 is
   substantively closed; phase 6d is optional polish.
4. After phase 6d (or if 6c closed enough): if you want to attempt
   Q5 (multi-domain decomposer), open `fix_v6.md` as the forward
   plan — Q5 is bigger surgery and needs its own zero-context doc.
5. **Suggest /schedule a regression-check agent** in 1 week to re-run
   §1.G and confirm the new strong/acc breakdown holds.

---

## 9. Minimum information from operator (none)

This hand-off is fully self-contained. Do NOT ask the operator unless:

* Step 1's diagnosis spot-check fails (corpus or codebase changed
  since this doc was written). Then write up the new finding before
  changing code.
* A phase regresses `served_strong < 28` and the diff is non-obvious.
  Surface with run dir + per-qid delta + a proposal for refinement OR
  discard.
* A target qid's expanded answer contains an invented norm (a
  citation to "art. X ET" where X doesn't appear in any
  `retriever.hybrid_search.out` chunk_id AND doesn't appear verbatim
  in any evidence excerpt). Then the prompt change is broken;
  surfacing is mandatory. Don't tighten "just enough to skip
  detection" — invention is binary.
* You're about to commit a change that affects
  `config/llm_runtime.json`, canonicalizer scripts, the markdown-
  splitter logic itself (vs ADDING a heading-reject post-step), or
  the v6 coherence gate. (Don't.)

---

## 10. Phase 6a close-record (Q4 heading-reject — KEPT)

**Closed 2026-04-29 ~6:05 PM Bogotá. Commit `8f839a8`. Run dir
`evals/sme_validation_v1/runs/20260429T225605Z_fix_v5_phase6a_heading_reject/`.**

Implementation: `src/lia_graph/pipeline_d/answer_support.py`.
Added `_HEADING_REJECT_PATTERNS` module constant
(post-`_ARTICLE_BUCKET_LIMITS`) with 5 compiled regexes:
`^#{2,4}\s`, `^\s*ARTÍCULO\s+\d+`, `^\s*PASO\s+\d+\b`,
`^\s*>\s*Pregunta\s+clave`, `####`. Inside `_evidence_candidate_lines`
(post-cleanup, pre-append), reject any line matching any pattern.

Smoke (45 tests): green.

| | phase-5 close anchor | phase 6a (this) | Δ |
|---|---|---|---|
| served_strong | 28 | **29** | **+1** |
| served_acceptable | 8 | 7 | -1 |
| served_weak | 0 | 0 | 0 |
| **served_acceptable+** | **36/36** | **36/36** | held |
| acc+ regressions | — | 0 | — |

**Flipped qid**: `regimen_cambiario_P2` (acc → **strong**),
636 → 3360 chars, all 4 sections present, real ET cites
(art. 26, 26-35, 260-11), no raw heading text in any bullet,
operationally substantive content (Formulario No. 1, IMC mechanism,
TRM warning, supporting docs).

**No-regression spot-check on 3 strong qids** (tarifas_renta_y_ttd_P1,
firmeza_declaraciones_P1, conciliacion_fiscal_P3): all held class;
char counts fluctuated within normal LLM polish noise.

**Six-gate sign-off**:
1. ✅ Idea: post-cleanup heading-shape rejection in evidence splitter.
2. ✅ Plan: §2 Q4 — narrow function edit + module-level constant.
3. ✅ Criterion: ≥36/36 acc+; ≥1 acc→strong; 0 strong→acc regressions
   — all met.
4. ✅ Test plan: 45 backend smoke + 36-Q panel + spot-check + delta
   verification.
5. ✅ Greenlight: PASS — clean technical pass + spot-check.
6. ✅ Keep — phase 6a closed.

---

## 11. Phase 6b close-record (Q1 sub-Q topic carry-over — KEPT)

**Closed 2026-04-29 ~7:10 PM Bogotá. Commit `51b1939`. Canonical run
dir `evals/sme_validation_v1/runs/20260430T000527Z_fix_v5_phase6b_rerun/`.
First-attempt run dir
`evals/sme_validation_v1/runs/20260429T235823Z_fix_v5_phase6b_subq_topic_carryover/`
preserved as evidence of LLM-noise-vs-systematic-regression
diagnosis.**

Implementation: `src/lia_graph/pipeline_d/orchestrator.py` inside the
`if sub_queries:` fan-out block, post-`_resolve` call. After each
sub-Q resolves, when its `mode == "fallback"` AND its
`effective_topic` differs from the parent's resolved topic
(`request.topic`), build a synthesized `TopicRoutingResult`
inheriting the parent topic + its secondary topics, with
`mode="subquery_parent_inheritance"`, `confidence=0.6`, `reason=
"fix_v5_phase6b:subquery_inherited_parent"`. Confident rule-route
hits on a different topic stay respected (multi-domain integrity
per §4 #16). Trace step `topic_router.subquery_inherited_parent`
records every inheritance for diagnostics.

Smoke (45 tests): green both runs.

| | phase-6a anchor | phase 6b first run | phase 6b rerun (canonical) | Δ vs 6a |
|---|---|---|---|---|
| served_strong | 29 | 31 | **32** | **+3** |
| served_acceptable | 7 | 5 | 4 | -3 |
| served_weak | 0 | 0 | 0 | 0 |
| **served_acceptable+** | **36/36** | **36/36** | **36/36** | held |
| strong→acc regressions | — | 1 (firmeza, polish noise) | 0 | — |

**Q1 targets** (4):

| qid | anchor (6a) | new (6b rerun) | chars | inheritances |
|---|---|---|---|---|
| `beneficio_auditoria_P3` | acc | **strong** | 3367 | 2 |
| `perdidas_fiscales_art147_P2` | acc | **strong** | 3082 | 2 |
| `regimen_sancionatorio_extemporaneidad_P3` | acc | **strong** | 3288 | 2 |
| `conciliacion_fiscal_P2` | acc | acc (held; stub eliminated) | 2752 | 1 |

**LLM-noise-vs-systematic diagnosis** (the iteration that made the
rerun necessary): the first 6b run flipped
`firmeza_declaraciones_P1` strong → acc. Trace inspection showed
the qid took the SINGLE-query path (no `decomposer.fanout` step),
so Q1 cannot have caused the regression. Synthesis template was
identical (1159 chars in both runs); polish_changed flipped
True → False on a non-deterministic gemini-flash call. The rerun
re-ran the whole panel and `firmeza_declaraciones_P1` recovered to
served_strong (2579 chars), confirming the first-run regression as
polish-LLM stochasticity, not Q1-induced. Canonical 6b result is
the rerun.

**Six-gate sign-off**:
1. ✅ Idea: orchestrator-scoped sub-Q topic carry-over from parent
   on fallback-mode resolves only.
2. ✅ Plan: §2 Q1 — orchestrator-only edit; preserves multi-domain
   sub-Qs that hit rule-route on a different topic.
3. ✅ Criterion: ≥36/36 acc+; strong net positive; 0 strong→acc
   regressions; ≥2 of 4 Q1 targets flip to strong; no invented norms
   — all met (rerun).
4. ✅ Test plan: 45 backend smoke + 36-Q panel + delta + per-qid
   trace verification of inheritance events + recovery rerun for
   noise diagnosis.
5. ✅ Greenlight: PASS — rerun confirms 32/4/0/36 with 3 acc→strong
   on target qids, 0 strong→acc regressions, 1 within-class
   improvement (conciliacion_fiscal_P2 stub eliminated).
6. ✅ Keep — phase 6b closed.

---

## 12. Phase 6c close-record (Q2 numeric directive — DISCARDED)

**Closed (discarded) 2026-04-29 ~7:25 PM Bogotá. Commit `ccf236c`
(includes BOTH the Q2 attempt and its same-commit revert; only the
run dir is preserved as discard evidence — the polish prompt
returns to the phase-5-close shape). Run dir
`evals/sme_validation_v1/runs/20260430T001426Z_fix_v5_phase6c_numeric_directive/`.**

Implementation attempted: `src/lia_graph/pipeline_d/answer_llm_polish.py`,
`_build_polish_prompt`. Added a single REGLA DE CÁLCULO clause
immediately after the existing REGLA DE EXPANSIÓN clause (per
fix_v5.md §3 Step 4). Smoke + restart + panel: clean.

| | phase-6b rerun anchor | phase 6c | Δ |
|---|---|---|---|
| served_strong | 32 | **31** | **-1** |
| served_acceptable | 4 | 5 | +1 |
| served_weak | 0 | 0 | 0 |
| **served_acceptable+** | **36/36** | **36/36** | held |

**Q2 numeric targets** (4): all acquired calc markers in their
answer_markdown but **0 flipped class**. `descuentos_tributarios_renta_P2`
and `conciliacion_fiscal_P2` stayed acc; `perdidas_fiscales_art147_P2`
and `regimen_sancionatorio_extemporaneidad_P2` were already strong
and held.

**Regression**: `beneficio_auditoria_P1` (NOT a Q2 target) flipped
strong → acc with identical synthesis template (448 chars in both
runs), polish_changed=True in both, but polished_chars dropped
2584 → 811. The new clause's "no inventés tasas, topes ni
porcentajes" wording made polish more conservative globally,
shrinking expansions on non-numeric questions. **Same blast-radius
pattern as the slug-cleanup discard** (§0): polish-prompt rule
additions tilt the LLM globally, demoting unrelated qids without
the targeted gain.

Per fix_v5.md §3 Step 4 explicit directive — *"If panel regresses,
REVERT — don't refine by adding more text"* — and §4 do-not-do #15
(*"Don't add more rules to the polish-prompt to suppress LLM-emitted
artifacts"*), Q2 was reverted same-commit.

**Phase 6d (Q3 sub-Q evidence fallback) also skipped.** Per §3
Step 5: the 4 remaining acc qids after phase 6b are all borderline
content-quality cases (`conciliacion_fiscal_P2`, `conciliacion_fiscal_P3`,
`descuentos_tributarios_renta_P2`, `regimen_sancionatorio_extemporaneidad_P1`),
none with the "Cobertura pendiente" stub pattern Q3 targets.
Implementing Q3 would change nothing on these qids. Surface to
operator for fix_v6 re-scope (content-quality territory beyond
surgical retrieval/synthesis routes).

**Six-gate sign-off (DISCARDED)**:
1. ✅ Idea: REGLA DE CÁLCULO additive clause in polish prompt.
2. ✅ Plan: §2 Q2 — single additive clause; reversible.
3. ❌ Criterion: ≥36/36 acc+ (met); strong net positive (NOT met:
   -1); ≥2 numeric targets flip to strong (NOT met: 0 flips).
4. ✅ Test plan: ran 45 smoke + 36-Q panel + per-target calc-marker
   spot-check + delta vs 6b rerun.
5. ❌ Greenlight: FAIL on criterion 3 sub-clauses.
6. ⏪ Discard — run dir kept as evidence; polish prompt reverted;
   phase 6d skipped; surface to operator for fix_v6.

---

## 13. End-of-fix_v5 state + fix_v6 hand-off

**Final §1.G panel result**: 32 served_strong / 4 served_acceptable /
0 served_weak / 0 refused / **36 served_acceptable+** under the
phase-4 fairer grader. Net +4 strong vs phase-5 close (28 → 32),
0 acc+ regressions throughout, 0 weak qids throughout, 0 invented
norms in any flipped qid.

**Canonical anchor for fix_v6**:
`evals/sme_validation_v1/runs/20260430T000527Z_fix_v5_phase6b_rerun/`.

**Residual 4 acc qids** (content-quality territory — what fix_v6
should re-scope):

| qid | chars (anchor) | polish_changed | has_stub | inheritances | likely gap |
|---|---|---|---|---|---|
| `conciliacion_fiscal_P2` | 2752 | True | False | 1 | borderline strong-vs-acc; sub-Q calc on $400M revaluación not run |
| `conciliacion_fiscal_P3` | 2994 | True | False | 0 | borderline; substantive content, SME grader called it acc |
| `descuentos_tributarios_renta_P2` | 2199 | True | False | 0 | $120M × 19% calc not run; norm cited |
| `regimen_sancionatorio_extemporaneidad_P1` | 1989 | True | False | 0 | borderline; specific UVT calc present |

**Layers fix_v6 should consider**:
- Numeric calc enforcement at a layer OTHER than the polish prompt
  (the prompt-blast-radius pattern is established, twice now —
  slug-cleanup + Q2). Possibly a deterministic post-polish
  numeric-extraction + format step that detects user-message
  numeric tokens and verifies the answer contains a calculation
  string for them; or a new dedicated calc-prompt step that runs
  ONLY when numeric tokens are present (not part of the global
  polish system prompt).
- Deeper retrieval / synthesis for `conciliacion_fiscal` (P2 + P3
  both still acc — possibly a topic-specific evidence-extraction
  gap).
- Optionally Q5 (multi-domain decomposer) from §2 if `beneficio_auditoria_P3`
  and similar drift again on future panel runs.

**State of the world at fix_v5 close**:
* Latest commits on `main` (pushed):
  * `8f839a8 fix_v5 phase 6a — Q4 heading-reject in evidence line splitter (28 → 29/36 strong)`
  * `51b1939 fix_v5 phase 6b — Q1 sub-Q topic carry-over from parent (29 → 32/36 strong)`
  * `ccf236c fix_v5 phase 6c — Q2 numeric directive DISCARDED (32 → 31 strong; reverted)`
* Working tree: clean.
* `config/llm_runtime.json` `provider_order`: gemini-flash first. UNCHANGED.
* `LIA_*` flag matrix: UNCHANGED.
* Polish prompt: phase-5-close shape (Route A REGLA DE EXPANSIÓN
  only; Q2 reverted).
* Evidence line splitter: now rejects markdown headings
  (`_HEADING_REJECT_PATTERNS` in `answer_support.py`).
* Sub-query fan-out: now inherits parent topic on fallback-mode
  sub-Q resolves (orchestrator.py).
* Cloud Supabase + cloud Falkor: in-sync; no migration drift.
* Dev server running at fix_v5 close (port 8787, dev:staging).
  Stop it via `pkill -KILL -f "python.*lia_graph|node.*dev-launcher|npm.*dev:staging"`.

---

*Drafted 2026-04-29 ~5:35 PM Bogotá by claude-opus-4-7 immediately
after fix_v4 phase 5 close (commits `6af9f22` + `0ac1a70` pushed to
`origin/main`) and the slug-cleanup discard. The diagnosis cited in
§1 is from this session's per-qid trace inspection of the phase-5-
close run dir
(`evals/sme_validation_v1/runs/20260429T215918Z_fix_v5_synthesis_fallback/<qid>.json
.response.diagnostics.pipeline_trace.steps[*]`). The slug-cleanup
discard learning underpinning the §0 cautionary banner and the §4
do-not-do entry #15 is in the failed run dir
`evals/sme_validation_v1/runs/20260429T221514Z_fix_v5_slug_cleanup/`
— compare it against the phase-5 anchor to see the -5 strong
demotion pattern firsthand. §10/§11/§12/§13 close-records added
2026-04-29 ~7:30 PM Bogotá by claude-opus-4-7 after phase 6a/6b
landed and 6c was discarded same-session.*
