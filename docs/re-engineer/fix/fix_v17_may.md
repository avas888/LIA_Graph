# fix_v17_may.md — Lane B wiring for the 37 new playbooks

> **🛑 STOP. If you are a fresh LLM agent invoked with a prompt like
> "retake v17 where we were," go DIRECTLY to §-1 below. Do not read
> §0–§13 until §-1 has been followed. §-1 walks you through the
> file-system verification dance, the test-sweep baseline, the
> scenario decision tree, and the known traps. It exists to make
> this plan re-entrant. Ignoring it has, in practice, caused
> wasted probes and missed context.**

> **Author context (zero-agent-context protocol).** This plan is
> self-contained. A fresh LLM agent with no prior conversation history
> can execute it from the file system as-is. Every file path, function
> name, env flag, test name, registry entry, and decision rule is
> specified verbatim. Verify every artifact against `git ls-files`
> before acting. If any cited path or function does not exist, STOP
> and report drift — do not invent.

---

## §-1 RESUME HERE — fresh-agent retake protocol

> **You are a fresh LLM agent invoked with a prompt like "retake v17
> where we were." This section is your single entry point. Do not
> skip it. Do not skim. Every step is load-bearing.**

### Step 1 — verify the file system matches what this plan describes

Run these commands in order. Each must succeed before moving on.
If any fails, STOP and report drift — do not invent paths.

```bash
# (a) Confirm this plan + the canonical CLAUDE.md sit where expected.
test -f docs/re-engineer/fix/fix_v17_may.md && \
    test -f CLAUDE.md && \
    test -f AGENTS.md && \
    echo "OK: canonical docs present"

# (b) Confirm the v17 SPEC files for batches 1–3 exist (9 files).
ls src/lia_graph/pipeline_d/case_bullets/liquidacion_mensual_nomina.py \
   src/lia_graph/pipeline_d/case_bullets/prestaciones_sociales.py \
   src/lia_graph/pipeline_d/case_bullets/liquidacion_terminacion.py \
   src/lia_graph/pipeline_d/case_bullets/pila_aportes.py \
   src/lia_graph/pipeline_d/case_bullets/ugpp_fiscalizacion.py \
   src/lia_graph/pipeline_d/case_bullets/nomina_electronica_dspne.py \
   src/lia_graph/pipeline_d/case_bullets/contrato_prestacion_vs_laboral.py \
   src/lia_graph/pipeline_d/case_bullets/contrato_aprendizaje_sena.py \
   src/lia_graph/pipeline_d/case_bullets/salario_integral.py \
   2>&1 | head -20

# (c) Confirm the two follow-on infra changes landed.
grep -q "SUB_BULLET_TOKEN" src/lia_graph/pipeline_d/presentation.py && \
    grep -q "with_sub_bullets" src/lia_graph/pipeline_d/presentation.py && \
    echo "OK: sub-bullet infra present (§0.2.1)"

grep -q "aprendi" src/lia_graph/pipeline_d/case_detectors_b5.py && \
    grep -q "despid\" in normalized_message or \"desped" src/lia_graph/pipeline_d/case_detectors_b5.py && \
    echo "OK: detector widening present (§0.2.2)"

# (d) Confirm the lint test file from §0.2.1 exists.
test -f tests/test_sub_bullet_rendering.py && \
    echo "OK: sub-bullet lint tests present"

# (e) Confirm allowlist edit landed.
grep -q '"art:114-1"' config/topic_norm_allowlist.json && \
    grep -q '"art:617"' config/topic_norm_allowlist.json && \
    echo "OK: laboral allowlist extended (§0.0 follow-on)"
```

If all five `echo OK` lines print, the state matches this plan.
If any does not, STOP and tell the operator what drifted before
taking any further action. Do NOT try to re-derive the plan from
the code.

### Step 2 — run the focused test sweep (gate 4 baseline)

This is the regression baseline. The plan claims 226 / 226 green
as of 2026-05-15 evening (181 pre-v17 baseline + 8 sub-bullet + 30
planner-registry additions for the 9 b1–b3 topics + 7 for the b3+
tail `aportes_proporcionales_tiempo_parcial`). Re-run to confirm
nothing drifted since.

```bash
PYTHONPATH=src:. uv run pytest \
    tests/test_sub_bullet_rendering.py \
    tests/test_planner_case_anchor_registry.py \
    tests/test_case_detectors_purity.py \
    tests/test_classifier_playbook_override.py \
    tests/test_classifier_path_veto.py \
    tests/test_answer_polish_rejected_fallback.py \
    tests/test_answer_synthesis_practica.py -q
```

**Expected:** `226 passed`. If you get fewer, **something landed
out-of-band since this plan was last updated** — investigate before
acting. If you get 226 exactly, you are aligned with the document.

### Step 3 — read these three sections IN THIS ORDER

1. **§0.0** — Status snapshot. Tells you what's ✅ / 🧪 / 🛠 right
   now. The current totals: 1 ✅, 8 🧪, 28 🛠 (out of 37 topics).
2. **§0.2** — The two follow-on infra changes shipped during the
   b1 cycle. **Critical context** — without reading this you will
   not understand why `presentation.py` has a `SUB_BULLET_TOKEN`,
   why some detectors use stems instead of full words, or why the
   polish prompt has a rule 5. Sub-section §0.2.3 carries the
   browser-screenshot evidence.
3. **§13.1** — Nine carry-forward lessons from the b1 cycle. ALL
   future v17 work depends on these. The server-restart drill in
   §13.1 item 1 alone has already caused one wasted probe — don't
   make it two.

### Step 4 — figure out which scenario you are in

The operator's instruction probably maps to ONE of these:

| Operator says… | You are in scenario… | Go to… |
|---|---|---|
| *"retake v17"* / *"continue v17"* / *"keep going on v17"* | A — continuation, scenario depends on what's open | §-1 step 5 below |
| *"probe b1–b3"* / *"now probe"* / *"run the next probe"* | B — operator is about to run probes themselves; you are passive support | §0.1 (probe table) + §13.1 (server-restart drill if needed) |
| *"verdict for topic X is pass/fail"* | C — operator is reporting probe results; you flip §12 status rows + (on fail) route per §7 | §12 + §7 |
| *"start b4"* / *"open batch 4"* | D — greenlight to begin the next batch | §3.1 (per-topic loop) + §13.1 (lessons applied on day one) |
| *"write fix_v18"* / *"chunk-noise plan"* | E — author the fix_v18 mini-plan | §0.3.2 (scope + suggested gates) |
| *"strict vs permissive on SPEC bullets"* | F — operator wants to decide policy | §0.3.3 + §10 residual #6 |
| something else | clarify before acting | (no code change yet) |

### Step 5 — if you are in scenario A ("retake v17"), pick the most pressing open item

Open §0.3 and look at the immediate next actions list. As of the
last update (2026-05-15 afternoon), the open items in priority
order are:

1. **§0.3.1** — Operator-driven probes of the remaining 8 b1–b3
   topics. You (engineer) wait for verdicts; you do not run the
   probes yourself. Tell the operator the probe table from §0.1 is
   ready and ask them to run any they have not yet covered.
2. **§0.3.2** — Author `fix_v18_may.md` for the chunk-noise leak.
   This is the highest-leverage independent action you can take
   without waiting on the operator. If the operator has nothing
   else queued, suggest this.
3. **§0.3.3** — SPEC-sacredness policy decision. Operator's call.
4. **§0.3.4** — Start b4 (requires operator greenlight).

Ask the operator which of these to pick if it's not clear.

### Step 6 — known traps to avoid (read once, internalize)

These are the mistakes already made and documented. Do not repeat:

1. **Server does not hot-reload Python.** Any change to a `.py` file
   under `src/lia_graph/` requires a server restart before the
   operator can probe. See §13.1 item 1 for the exact kill +
   relaunch commands.
2. **Spanish singular/plural under accent-strip splits orthography.**
   `aprendiz` is NOT a substring of `aprendices` (different
   endings); `despedí` is NOT a substring of `despido` (different
   verb roots). See §0.2.2 trap table.
3. **The donaciones detector keys on bare `"esal"`** which collides
   with `"desalarización"`. The §0.1 probe table avoids
   "desalarización" for that reason. See §13.1 item 9.
4. **Polish may drop authored SPEC bullets** under concrete-numbers
   framings even with rule 5 in place. See §10 residual #6.
5. **The chunk-noise leak leads every labor answer.** When operator
   reports probe output that includes corpus-chunk junk above the
   SPEC bullets, judge the SPEC content on its own merits — don't
   mistake the noise for a v17 bug. See §10 residual #5.

### Step 7 — communication rules for this session

Reading from saved user memory (already in your context, but
re-asserted here because they govern THIS work):

- Plain language with the operator by default; engineering depth
  only when asked (`feedback_plain_language_communication`).
- End every status report with a concrete next-step suggestion
  (`feedback_always_suggest_next`).
- Don't quote money in status reports — time + scope + what it
  unblocks (`feedback_no_money_quoting`).
- SME panel runs only on explicit request — never auto-run
  `scripts/eval/run_sme_parallel.py` (`feedback_sme_panel_explicit_request_only`).
- dev:staging is the default run mode — verify
  `retrieval_backend=supabase` on the first response of any probe
  session (`feedback_default_run_mode_staging`).
- Update this very file (`fix_v17_may.md`) IN THE SAME EDIT as the
  code change. The §12 ship-state table and §0.3 next-actions list
  must reflect reality after every action (`feedback_recommendations_logged_in_canonical_plan`).

---

## §0.0 Status snapshot — 2026-05-15 (evening)

**Where we are.** Batches **v17 b1 + b2 + b3 (9 topics) + b3+ tail
(1 topic) = 10 topics landed code-side**; **2 topics are ✅** verified
in dev:staging via operator probe (`liquidacion_mensual_nomina` and
`aportes_proporcionales_tiempo_parcial`); the other 8 topics are 🧪
(unit tests green, dev:staging probe still pending). Batches b4 – b12
(28 topics) are **not started**. **Total scope is now 38 topics**
(original 37 v17 candidates + b3+ tail addition surfaced by an
operator probe gap, see residual #7).

**Two follow-on changes shipped during the b1–b3 probe cycle**
(documented fully in §0.2 below; both are landed code-side):

1. **Sub-bullet rendering capability** — SPEC authors can now nest
   recommendation bullets via `presentation.with_sub_bullets`. The
   feature is generic — works across all 60+ existing SPECs.
   Verified in dev:staging via screenshot on
   `liquidacion_mensual_nomina`.
2. **Detector widening pass** — the 9 v17 detectors were too narrow
   on plural / general phrasings (e.g. "recargos de horas extras y
   dominicales según el CST" missed `liquidacion_mensual_nomina`,
   "aprendices del SENA" missed `contrato_aprendizaje_sena`).
   Widened with anti-tests to prevent over-broadening.

**Ship lifecycle per topic.** 🛠 idea → **🧪 verified locally** →
**✅ verified in dev:staging via operator probe** → end-of-line.
The 🧪 → ✅ jump is operator-driven (screenshot of the rendered
answer in dev:staging chat).

### What landed in code on 2026-05-15

- **9 detectors** added to `src/lia_graph/pipeline_d/case_detectors_b5.py`
  during b1–b3 (file grew from 555 → 718 LOC).
- **1 detector** added later the same day in NEW
  `src/lia_graph/pipeline_d/case_detectors_b6.py` (108 LOC) when
  `_b5` crossed the 800-LOC ceiling — `is_aportes_proporcionales_tiempo_parcial_case`.
  Created per `feedback_granular_edits` + §3.1 step 2. Future labor /
  nómina detectors that don't fit `_b5`'s existing groupings land here.
- **10 `CaseSpec` files** in `src/lia_graph/pipeline_d/case_bullets/`:
  `liquidacion_mensual_nomina.py`, `prestaciones_sociales.py`,
  `liquidacion_terminacion.py`, `pila_aportes.py`,
  `ugpp_fiscalizacion.py`, `nomina_electronica_dspne.py`,
  `contrato_prestacion_vs_laboral.py`,
  `contrato_aprendizaje_sena.py`, `salario_integral.py`,
  `aportes_proporcionales_tiempo_parcial.py` (b3+ tail).
- **Registry order** in `case_bullets/__init__.py::CASE_REGISTRY`:
  `_APORTES_PROPORCIONALES_TIEMPO_PARCIAL_SPEC` is registered FIRST in
  the v17 block (most niche labor case — empleada doméstica por días);
  then the 8 specific labor specs; then the broad
  `_LIQUIDACION_MENSUAL_NOMINA_SPEC` at the registry tail.
  `_SALARIO_INTEGRAL_SPEC` precedes the mensual-nómina spec so a
  query mentioning both routes to salario_integral first.
- **Facade re-exports** updated in `case_detectors.py` (imports + `__all__`)
  and **synthesis-helper re-exports** in `answer_synthesis_helpers.py`.
- **Allowlist extension** in `config/topic_norm_allowlist.json` under
  the `laboral` topic key: added `art:114-1 / 387 / 388 / 401-3 /
  617 / 651 / 771-2` to `allowed_prefixes` + `facturacion_electronica`
  to `cross_topic_allowed`. Needed so the topic-gate does not strip
  v17 anchors out of bullets at synthesis time.
- **30 new tests** appended to `tests/test_planner_case_anchor_registry.py`
  during b1–b3 (one anchor + one search-queries test per topic for
  the 9 b1–b3 topics = 18; one precedence test for salario_integral
  vs liquidacion_mensual_nomina; 11 widening / anti-tests from §0.2.2
  locking in plural + general phrasings and pinning the
  `recargo de mora ICA` / `prima de riesgo en seguros` boundaries).
- **7 additional tests** for the b3+ tail
  `aportes_proporcionales_tiempo_parcial`: verbatim operator probe,
  plural / general variants, SISBÉN-only path, two anti-tests
  (full-time nómina + pure renta), and a precedence test vs
  `pila_aportes`.

### Test sweep result (gate 4)

- Command run: `PYTHONPATH=src:. uv run pytest
  tests/test_planner_case_anchor_registry.py
  tests/test_case_detectors_purity.py
  tests/test_classifier_playbook_override.py
  tests/test_classifier_path_veto.py
  tests/test_answer_polish_rejected_fallback.py
  tests/test_answer_synthesis_practica.py -q`
- Result: **218 passed, 0 failed** (181 baseline + 30 new for the
  9 v17 b1–b3 topics + widening anti-tests + 7 for the b3+ tail
  `aportes_proporcionales_tiempo_parcial`). Per
  `feedback_verify_fixes_end_to_end`, this is gate 4 only.
  `liquidacion_mensual_nomina` AND
  `aportes_proporcionales_tiempo_parcial` have ALSO cleared gates 5
  + 6 via operator-driven dev:staging probes (the latter on the
  evening of 2026-05-15 — see residual #7 and §12 ship-state).

### Two detector-engineering notes from this batch (carry forward)

1. **Spanish verb roots split under accent-strip normalization.**
   `unicodedata.normalize("NFKD", ...).encode("ascii", "ignore")`
   maps `despedí → despedi` (no `despid` substring) but
   `despido → despido` (yes `despid` substring). Spanish verbs
   often have **two roots** that survive accent-stripping
   differently (e.g. despid- vs desped-, sirvi- vs servi-, pidi- vs
   pedi-). Future detectors must enumerate both roots in the
   combined-keyword path. The terminación detector at
   `case_detectors_b5.py::is_liquidacion_terminacion_case` is the
   reference shape: `if ("despid" in nm or "desped" in nm) and (…)`.
2. **Pre-existing detector substring collisions to avoid in probes.**
   The legacy `is_donaciones_case` keys on the bare `"esal"`
   substring (intended to catch "ESAL" the entity), which collides
   with `"desalarización" → "desalarizacion"` (contains `esal`).
   This intercepts UGPP-desalarización questions before the v17
   UGPP detector runs. **Out of scope to fix in v17** — but operator
   probes for `ugpp_fiscalizacion` must avoid the word
   "desalarización" (use "pagos no salariales" instead). A future
   fix should switch the donaciones detector's `esal` marker to a
   word-boundary regex (same pattern fix_v16 applied to rte_esal).

### What comes next, in priority order

1. **Operator probes b1–b3 (this is the immediate next action).**
   See §0.1 below for the verbatim 9 probe questions + the
   pass/fail rubric. Expected effort: ~15 min/topic, ~2 hours total.
   On every pass → topic flips to ✅ in the ship-state table at §12.
   On every fail → diagnose per §7, fix, re-probe, then ✅.
2. **Greenlight to start v17 b4.** Engineer waits for operator's
   `"b1–b3 done"` before opening b4. b4 closes the labor block
   (4 topics: `embargos_salario`, `smmlv_aux_transporte_anual`,
   `subsidios_transporte_alimentacion`, `teletrabajo_trabajo_casa`).
   Same code pattern; no new infrastructure needed. Effort ~1.5 h
   engineer + ~1 h operator probes.
3. **b5 – b12 (28 remaining topics).** Same per-topic pattern,
   batched per §9. Total residual engineering ≈ **10–11 hours**,
   total residual operator probes ≈ **7 hours** (15 min × 28).
4. **No SME panel run until all 37 topics ✅.** Per
   `feedback_sme_panel_explicit_request_only`, the 36-Q panel is
   the post-merge regression check, not a per-batch probe.

### Status legend — current values

- 🛠 — code landed, not yet probed (**0 topics in this state**).
- 🧪 — verified locally, unit tests green (**9 topics — b1–b3**).
- ✅ — verified in dev:staging (**0 topics — pending operator probes**).
- ↩ — regressed and discarded (**0 topics**).

---

## §0.1 Operator probe script for v17 b1 + b2 + b3

**Run mode.** dev:staging (per `feedback_default_run_mode_staging`).
Confirm `response.diagnostics.retrieval_backend == "supabase"` on
the first answer to make sure cloud is wired.

**One probe per topic, paste verbatim.** Each question is calibrated
to (a) trigger the case detector cleanly and (b) read like a real
contador question.

| # | Batch | Topic | Probe question |
|---|---|---|---|
| 1 | b1 | `liquidacion_mensual_nomina` | ¿Cómo liquido la nómina mensual de un empleado que gana $3.000.000, hizo 10 horas extras diurnas y trabajó 1 dominical? |
| 2 | b1 | `prestaciones_sociales` | ¿Cuándo debo consignar las cesantías al fondo y cómo calculo la prima de servicios de un empleado con salario $2.000.000 más auxilio de transporte? |
| 3 | b1 | `liquidacion_terminacion` | ¿Cómo liquido a un empleado que despedí sin justa causa, salario $4.000.000, 4 años de antigüedad, contrato indefinido? |
| 4 | b2 | `pila_aportes` | ¿Cuándo debo pagar la PILA según el último dígito del NIT y cuál es el IBC mínimo de un independiente? |
| 5 | b2 | `ugpp_fiscalizacion` | Me llegó un requerimiento UGPP, ¿qué revisan y cuáles son las sanciones por inexactitud en aportes? *(NO usar la palabra "desalarización" — colisiona con el detector legacy de donaciones; usar "pagos no salariales" si se necesita el concepto)* |
| 6 | b2 | `nomina_electronica_dspne` | ¿Estoy obligado a generar el DSPNE de nómina electrónica y qué pasa con la deducción si lo envío tarde? |
| 7 | b3 | `contrato_prestacion_vs_laboral` | ¿Cuándo un contrato de prestación de servicios se convierte en laboral y qué riesgos tengo con la UGPP si me reclasifican a un contratista? |
| 8 | b3 | `contrato_aprendizaje_sena` | ¿Cuántos aprendices SENA debo tener si tengo 30 empleados, cuánto les pago en etapa práctica y cómo se monetiza la cuota? |
| 9 | b3 | `salario_integral` | ¿Cuánto debe ganar mínimo un empleado para pactar salario integral y sobre qué base se calculan los aportes a seguridad social? |

### Per-answer rubric (operator side)

For each answer, the operator checks **three layers** before deciding:

1. **Citation layer.** Does the answer cite the expected anchor
   article in the rendered text + the Anclaje Legal block?
   - Topic → expected anchor: liquidacion_mensual_nomina → 108 + 387;
     prestaciones_sociales → 108 + 387; liquidacion_terminacion →
     108 + 387; pila_aportes → 108 + 114-1; ugpp_fiscalizacion →
     108 + 114-1; nomina_electronica_dspne → 617;
     contrato_prestacion_vs_laboral → 383; contrato_aprendizaje_sena
     → 108; salario_integral → 108 + 387.
2. **Substance layer.** Does the answer cover the operative how-to,
   not just the legal citation? An accountant should be able to
   *act* on the answer.
3. **Hallucination layer.** Are all UVT / % / SMMLV figures real
   (from the playbook brief or the question) — never invented? The
   polish UVT validator now catches most inventions (fix_v15_may §3
   enforce), but operator review is the final guardrail per
   `feedback_no_hallucinated_examples`.

### Decision rule per probe

- All three layers clean → **`#N pass`**.
- Citation wrong / substance thin / hallucination → **`#N fail —
  <one-line root cause>`**.
- Borderline ("would forward with a comma fix") → **`#N warn`** with
  the comma fix written out; engineer applies and re-probes.

### What the engineer does with the report

| Verdict | Engineer action |
|---|---|
| `pass` | Flip the topic to ✅ in §12 ship-state table. No code change. |
| `warn` | Apply the comma fix (bullet text, detector marker, allowlist entry); re-probe; flip to ✅. |
| `fail — citation` | Per §7.1: check `_CASE_ANCHOR_REGISTRY` row anchor list + allowlist coverage; refine. |
| `fail — substance` | Per §7.1: re-read brief; verify bullets transferred verbatim; widen if needed. |
| `fail — hallucination` | Per §7.1: surface the invented value; validator should have caught — if not, file a v15-style validator gap. |
| `fail — detector miss` | Per §7.1: detector marker too narrow; widen + re-test. |

If two of three topics in a single batch hit `fail`, **pause the
batch** and run a retrospective per
`feedback_diagnose_before_intervene` (corpus problem vs detector
problem vs allowlist problem); do NOT relax the per-topic decision
rule per `feedback_thresholds_no_lower`.

---

## §0.2 Follow-on shipped during b1 probe cycle (2026-05-15)

Two generic infrastructure improvements landed while probing
`liquidacion_mensual_nomina`. Both are kept in v17 scope because
they directly affect every v17 SPEC. Both are landed code-side and
unit-test-green.

### §0.2.1 Sub-bullet rendering for recommendation bullets

**Problem (root cause).** `answer_shared.append_unique` (line 248)
and `neutralize_non_imputative_language` (line 256) both run
`re.sub(r"\\s+", " ", ...)` on every recommendation bullet. Embedded
newlines in a SPEC bullet die at insert-time, long before
`render_bullet_section` formats them — so the obvious "just put `\\n
  - sub` in the bullet string" doesn't work.

**Operator-visible symptom.** Long bullets like the recargos table
rendered as a wall of semicolons. Hard to scan for a contador.

**Fix (one-point change, generic).** Use a non-whitespace sentinel
token that survives the whitespace collapse, then expand it to
proper nested markdown at the final render step. No schema change,
no callsite audit, works across all 60+ existing SPECs.

**Files touched:**

| File | Change |
|---|---|
| `src/lia_graph/pipeline_d/presentation.py` | Added `SUB_BULLET_TOKEN = "\|⏵\|"`, `with_sub_bullets(lead, items)` helper, `expand_sub_bullets(line)` post-processor. Updated `render_bullet_section` to call `expand_sub_bullets` on each bullet line before joining. Re-exported via `__all__`. |
| `src/lia_graph/pipeline_d/case_bullets/_registry.py` | Docstring section "Authoring sub-bullets" with the usage example. |
| `src/lia_graph/pipeline_d/case_bullets/liquidacion_mensual_nomina.py` | Refactored 3 bullets (`Recargos y horas extras`, `Aportes empleado`, `Aportes empleador`) using `with_sub_bullets` as the demo. |
| `src/lia_graph/pipeline_d/answer_llm_polish.py` | Added rule 5 to `_build_polish_prompt`'s DIRECTIVA PRIMARIA: "PRESERVÁ la estructura de listas anidadas tal cual aparezca en el BORRADOR." |
| `tests/test_sub_bullet_rendering.py` | NEW: 8 tests. Sentinel survives `append_unique` + `neutralize_non_imputative_language`; renderer expands correctly; flat bullets render unchanged (regression); `expand_sub_bullets` is idempotent on flat lines; end-to-end append + render preserves nesting; lint that SPEC bullets contain no literal newlines; lint that SPEC bullets contain no URL / `Actualícese:` caption noise. |

**Authoring API for the executing agent.** Write nested bullets
like this:

```python
from ..presentation import with_sub_bullets
from ._registry import CaseSpec

SPEC = CaseSpec(
    ...,
    bullets=(
        "Plain flat bullet — stays a string.",
        with_sub_bullets(
            "**Lead line in bold (parent of the children):**",
            (
                "first child bullet",
                "second child bullet",
                "third child bullet",
            ),
        ),
    ),
    ...,
)
```

The lead is wrapped in `**bold**` by convention; each child is the
plain operative content. The renderer produces:

```
- **Lead line in bold (parent of the children):**
  - first child bullet
  - second child bullet
  - third child bullet
```

**Lint enforcement.** `tests/test_sub_bullet_rendering.py` rejects:

- SPEC bullets containing literal `\\n` (use `with_sub_bullets`
  instead — newlines die at the whitespace collapse).
- SPEC bullets containing URLs (`https?://`) — those are
  chunk-extraction noise that SPEC authors should never produce.
- SPEC bullets starting with a secondary-source caption prefix
  (`Actualícese:`, `Gerencie.com:`, `DIAN:` — the legacy
  `clean_support_line_for_answer` stripped these from chunk text;
  SPEC bullets bypass that cleaner so the lint is the safety net).
- The `→` / `➜` filter from the legacy cleaner is **intentionally
  not enforced** on SPEC bullets — Spanish authors legitimately use
  `→` as a "leads to" operator (e.g. `"00–07 → día 2"`).

**Polish-LLM behavior note (empirical, 2026-05-15).** With the new
rule 5 in place, polish preserved the nested structure verbatim on
the `liquidacion_mensual_nomina` probe — 6 sub-bullets under the
recargos lead, 4 under aportes empleado, 6 under aportes empleador,
all bold preserved. **However:** polish has broad creative latitude
("podés reescribir la prosa del BORRADOR para que suene como un
contador colombiano senior"); on a previous probe of the SAME topic
with a CONCRETE-NUMBERS question ("liquidar nómina de un empleado
que gana $3.000.000…"), polish dropped the static percentage table
entirely and computed the math in `Procedimiento Sugerido`. This is
**arguably correct behavior** (the contador got the worked answer),
but it means **SPEC sub-bullets are not guaranteed to render on
every question**. A future v18-class fix should consider whether
SPEC bullets should be sacred (polish can rewrite wording but cannot
drop them); out of scope for v17.

### §0.2.2 v17 detector widening for plural / general phrasings

**Problem (root cause).** Several v17 detectors used singular-form
markers (`"recargo nocturno"`, `"hora extra diurna"`, `"cesantías"`)
and assumed the user would phrase the question identically. Real
operator probes use plurals (`"recargos"`, `"horas extras"`,
`"primas"`) and general framings (`"según el CST"`,
`"prestaciones sociales obligatorias"`). The detectors missed them
silently, the planner did not emit the SPEC's anchor articles, and
the rendered answer fell back to chunk-derived noise (e.g. Anclaje
Legal cited `Art. 127-132` and `Art. 186` instead of the SPEC's
`Art. 108 + 387`).

**Two Spanish-language orthography traps surfaced during the
widening:**

| Trap | Example | Why bare substring fails | Fix |
|---|---|---|---|
| Verb-root split under accent-strip | `despedí → despedi` (no `despid` substring); `despido → despido` (has `despid` substring) | Spanish verbs split into two roots after `unicodedata.normalize("NFKD", …).encode("ascii", "ignore")` | Use BOTH roots in the combined-keyword path: `("despid" in nm or "desped" in nm)`. Reference shape: `case_detectors_b5.py::is_liquidacion_terminacion_case`. |
| Plural orthography change | `aprendiz` (-iz) is NOT a substring of `aprendices` (-ices, plural ends differently) | Singular `-z` becomes plural `-ces`; bare substring of the singular won't match the plural | Use the shared stem (`"aprendi"` catches both). Reference shape: `case_detectors_b5.py::is_contrato_aprendizaje_sena_case`. |

**Other Spanish stem traps to watch for in future detectors
(non-exhaustive — verify each before writing markers):**

| Singular | Plural | Shared stem |
|---|---|---|
| `aprendiz` | `aprendices` | `aprendi` |
| `vez` | `veces` | `vec` (after normalize) — verify |
| `feliz` | `felices` | `feli` |
| `lápiz` | `lápices` | `lapi` |
| `juez` | `jueces` | `jue` — verify |
| Verb (1st person past `-í`) | Verb (3rd person past `-ió`) | Often diverge under accent-strip — verify both endings |

**Files touched:**

| File | Change |
|---|---|
| `src/lia_graph/pipeline_d/case_detectors_b5.py` | Widened 6 detectors: `liquidacion_mensual_nomina` (added plural markers + 3 contextual fallback branches: `recargo` + labor-context, `dominical/festivo` + labor-context, `aporte` + employer-context), `prestaciones_sociales` (added `prestaciones sociales` phrase + `primas`-plural fallback with payment-timing context), `liquidacion_terminacion` (added `término fijo` / `obra o labor` + termination-context fallback), `contrato_prestacion_vs_laboral` (added `contratista` + `prestación de servicios` general framing), `contrato_aprendizaje_sena` (switched fallback stem from `aprendiz` to `aprendi` to catch the plural), `pila_aportes` (added `planilla de aportes` marker + `planilla` + `aport` fallback). Three detectors left alone (`nomina_electronica_dspne`, `ugpp_fiscalizacion`, `salario_integral`) — already fired on their probes. |
| `tests/test_planner_case_anchor_registry.py` | Added 11 tests: 9 lock in plural / general phrasings; 2 anti-tests (`recargo de mora ICA` must NOT fire `liquidacion_mensual_nomina`, `prima de riesgo en seguros` must NOT fire `prestaciones_sociales`). |

**Anti-test coverage matters — without it, the widening risks
intercepting non-labor queries.** Specifically: `recargo` outside
labor context can mean ICA / IVA / predial mora surcharges;
`prima` outside labor context can mean insurance premiums or
financial put/call options. The anti-tests pin the boundary.

**Test sweep result after the widening:**

```
PYTHONPATH=src:. uv run pytest \\
    tests/test_sub_bullet_rendering.py \\
    tests/test_planner_case_anchor_registry.py \\
    tests/test_case_detectors_purity.py \\
    tests/test_classifier_playbook_override.py \\
    tests/test_classifier_path_veto.py \\
    tests/test_answer_polish_rejected_fallback.py \\
    tests/test_answer_synthesis_practica.py -q
```

→ **226 passed, 0 failed** (181 pre-v17 baseline + 8 sub-bullet +
30 in test_planner_case_anchor_registry.py for the 9 v17 b1–b3
topics + widening anti-tests + 7 for the b3+ tail
`aportes_proporcionales_tiempo_parcial`).

### §0.2.3 Operator screenshot evidence (`liquidacion_mensual_nomina`)

The 2026-05-15 dev:staging probe of *"¿Cuáles son los recargos de
horas extras y dominicales según el CST?"* returned (after both
follow-ons landed + server restart):

- Anclaje Legal includes `Art. 108` + `Art. 387` (the SPEC's
  anchors) ✓
- All 7 SPEC bullets rendered verbatim (no polish paraphrase) ✓
- The 3 refactored bullets rendered as nested markdown with
  **visual indentation** in the browser ✓ (screenshot retained by
  operator)
- Bold formatting preserved through polish on every percentage ✓

That's the gate-5 + gate-6 evidence per
`feedback_verify_fixes_end_to_end`. `liquidacion_mensual_nomina`
flips 🧪 → ✅.

---

## §0.3 Immediate next actions for the executing agent

Listed in execution order. Each action is independently runnable;
none depends on a prior action's verdict except where noted.

### §0.3.1 Operator probe the remaining 8 b1–b3 topics

**What.** Run the 8 probe questions from §0.1 table (rows 2–9
inclusive) in dev:staging. Capture for each: pass / warn / fail
verdict + (on warn/fail) one-line root cause.

**Who.** Operator-driven. Engineer waits for the verdict report.

**Expected cost.** ~15 min/topic × 8 topics = ~2 hours of operator
time. Engineer is idle during this stage.

**Decision rule.** Per topic: all clean → flip 🧪 → ✅ in §12. Any
fail → §7 routing. **If ≥ 2 fails in any single batch (b1, b2, or
b3), PAUSE** and run a retrospective per
`feedback_diagnose_before_intervene` before continuing.

### §0.3.2 Land fix_v18 mini-plan for the chunk-noise leak

**What.** The first 7–8 bullets of the `Recomendaciones Prácticas`
section on every labor answer are corpus-chunk noise that leads the
authored SPEC content. Examples from the 2026-05-15 probes:

- `"R: SÍ, se acumulan. Son recargos de diferente naturaleza..."`
  (orphaned Q&A snippet)
- `"Usted tiene 3 meses para prepararse: El 1 de julio de 2026, el
  recargo sube del 80% al 90%..."` (forward-dated marketing text
  from a secondary source)
- `"Total horas dominicales/mes: 32 horas."` (orphaned number)
- `"Trabajador con salario de $1.750.905 (SMMLV)"` (stale AG 2025
  reference value)
- `"Recargo nocturno (Art. 168 CST, modificado Ley 2466/2025)..."`
  (cites a reform whose vigencia for AG 2026 must be verified per
  `feedback_vigencia_norm_keyed`)

**Why this matters.** Independent of v17 wiring — the noise lands
above the authored SPEC content even when the detector fires
correctly. Contadores have to scroll past 8 lines of noise before
the authoritative answer starts. Affects every v17 labor topic
and likely every existing topic too.

**Likely surface.** Two functions in `pipeline_d/`:

- `answer_synthesis_practica.py` — `extend_from_practica_chunks`
  and the `_candidate_lines_from_chunk` extractor in particular.
- `answer_synthesis_helpers.py::extend_from_support_insights` (line
  151–158) — calls `clean_support_line_for_answer` but doesn't
  filter for vigencia or topic-relevance.

**Recommended approach.** Write `docs/re-engineer/fix/fix_v18_may.md`
as a small mini-plan following the six-gate template. **Out of
scope for v17.** Suggested gates:

- §1 — idea: filter chunk-derived recommendation lines for
  (a) topic relevance to the active case detector's keywords,
  (b) absence of forward-dated marketing language, (c) absence of
  orphaned numeric values without article anchors.
- §2 — plan: narrowest module is
  `answer_synthesis_helpers.extend_from_support_insights` (called
  pre-SPEC bullet append at `answer_synthesis_sections::build_recommendations`
  line 70). Add a filter pass before `append_unique`.
- §3 — success: ≥ 4 of the 5 noise patterns above suppressed in
  re-probe of the same question, with no SPEC bullets lost.

### §0.3.3 Decide on SPEC-bullet-sacredness policy

**What.** Empirical finding from the 2026-05-15 probe cycle: polish
sometimes preserves SPEC bullets verbatim (general questions, as in
the §0.2.3 evidence) and sometimes paraphrases/drops them (concrete
calculation questions). See §0.2.1 for the empirical observation.

**Two possible policies, each defensible:**

1. **Permissive (current behavior).** Polish optimizes per question;
   for concrete cases it computes math and may drop the static
   percentage table. Sometimes loses authored detail.
2. **Strict.** SPEC bullets are sacred — polish can rewrite wording
   but cannot drop them. Always renders the authored table even
   when the question is concrete. Risk: a contador asking
   "$3M + 10 horas" might see a worked calculation **AND** a
   static reference table, which is verbose but never wrong.

**Action.** Operator decision, not engineer's. Engineer flags the
trade-off and waits.

### §0.3.4 Greenlight to start v17 b4

**What.** b4 closes the labor block (4 topics:
`embargos_salario`, `smmlv_aux_transporte_anual`,
`subsidios_transporte_alimentacion`, `teletrabajo_trabajo_casa`).
Same per-topic pattern as b1–b3.

**Improvements available from b1–b3 lessons (apply on day one):**

1. Use `with_sub_bullets` for any bullet that has > 2 enumerated
   sub-items (per §0.2.1).
2. For every detector marker, check the Spanish singular/plural
   form (per §0.2.2 traps). If the marker has `-z`, `-í`, `-ió`,
   `-és`, or any accent, audit the bare-substring behavior under
   accent-strip BEFORE writing the marker tuple.
3. Run the audit-probe loop locally (per the script structure in
   the 2026-05-15 widening) BEFORE merging — catch plural gaps
   before they ship.

**Effort.** ~1.5 hours engineer + ~1 hour operator probe.

**Trigger.** Engineer waits for operator's
`"b1–b3 done — start b4"` signal before opening b4.

### §0.3.5 No SME panel run until all 37 topics ✅

Per `feedback_sme_panel_explicit_request_only`. The 36-Q panel is
the post-merge regression check, not a per-batch probe.

---

## §0. TL;DR

**Idea.** Take the **37 new playbooks** that fix_v16_may + corpusfix_v1
landed as **Lane A only** (cloud chunks tagged correctly, retrievable
via `hybrid_search`) and add their **Lane B wiring** so the planner
emits a **deterministic anchor** for each topic instead of relying on
hybrid_search ranking.

**Why now.** As of 2026-05-15 the chat engine answers all 7 corpusfix
probe questions, but the new playbooks only surface when retrieval
ranking happens to put them top-K. Lane B closes that loop: detector
fires → planner emits explicit `art:<num>` anchor → retriever fetches
the playbook chunk regardless of FTS/vector ranking → polish surfaces
the correct article in the answer.

**Effort.** ~20 min per topic — playbook already exists, ingestion
override already exists, cloud chunks already exist. The remaining
work is **mechanical wiring** in 4 narrow modules. **37 × 20 min ≈
12 hours** total engineering. Recommend batches of ~3 topics per
session with operator-reviewed probe per topic.

**Risk.** Low. Additive registry rows; rollback is removing the row.
Per-topic precision is operator-validated via the
`answer-engine-probe` skill before merge.

---

## §1. Repository state assumed by this plan

Verify these before changing the runtime:

| Path | Purpose |
|---|---|
| `src/lia_graph/pipeline_d/case_detectors.py` | Pure detector facade. Re-exports detectors from `case_detectors_extensions.py` + `case_detectors_b5.py`. |
| `src/lia_graph/pipeline_d/case_detectors_extensions.py` | b3 + b4 detectors. |
| `src/lia_graph/pipeline_d/case_detectors_b5.py` | b5 detectors (currently last sibling; b6 should be created here when this file reaches ~1000 LOC). |
| `src/lia_graph/pipeline_d/case_bullets/` | Per-topic `CaseSpec` instances. One file per topic. |
| `src/lia_graph/pipeline_d/case_bullets/__init__.py` | `CASE_REGISTRY` tuple. Order determines first-match anchor precedence. |
| `src/lia_graph/pipeline_d/case_bullets/_registry.py` | `CaseSpec` dataclass — see fields used by `planner.py` + polish + fallback. |
| `src/lia_graph/pipeline_d/planner.py` | Reads `CASE_REGISTRY` into `_CASE_ANCHOR_REGISTRY` + `_CASE_SEARCH_QUERIES`. |
| `src/lia_graph/pipeline_d/answer_synthesis_helpers.py` | Re-exports every detector so the synthesis layer iterates them. |
| `src/lia_graph/pipeline_d/answer_synthesis_sections.py` | Owns `build_recommendations` + `_active_case_keywords`. |
| `src/lia_graph/pipeline_d/answer_llm_polish.py` | Polish UVT validator auto-derives cue list from `CASE_REGISTRY.anchor_articles`. |
| `src/lia_graph/pipeline_d/answer_polish_rejected_fallback.py` | A4 substantive fallback — seeds bullets from `CASE_REGISTRY` when polish rejects. |
| `tests/test_planner_case_anchor_registry.py` | Registry membership + anchor emission per topic. Add one test per new topic. |
| `tests/test_case_detectors_purity.py` | Guard: detector module imports stay pure. |
| `.claude/skills/answer-engine-probe/` | Probe skill used at gate 7. |
| `config/article_secondary_topics.json` | Cross-domain anchor map — extend when a topic's anchor lives in a different libro than its router topic. |
| `config/topic_norm_allowlist.json` | Per-topic article allowlist. Extend with the anchor article when the topic key is present in this file. |
| `knowledge_base/.../PLAYBOOKS/playbook_<topic>.md` | Source-of-truth content. Already shipped in fix_v16 + corpusfix_v1. |

### Shipped through fix_v16 + corpusfix_v1 (do NOT re-implement)

- **51 topics** wired in `CASE_REGISTRY` (Lane A + Lane B).
- **45 + 37 = 82 playbook `.md` files** in `knowledge_base/`.
- **82 playbook stems** mapped in `_PLAYBOOK_FILENAME_TO_TOPIC`
  (`src/lia_graph/ingestion_classifier_playbook.py`).
- Cloud Supabase + Falkor carry all 82 playbook docs with correct
  `tema` and `topic` columns.
- Cross-domain abstention fix landed: `config/article_secondary_topics.json`
  has entries for 28, 240, 555, 555-1, 555-2, 565, 566-1, 568, 631,
  631-1, 631-2, 631-3, 631-4, 631-5, 632, 633, 634, 807, 809, 869,
  869-1, 869-2.

### The 37 Lane B candidates

These topics have **playbook .md on disk + cloud chunks tagged + ingestion
override** but **no `CaseSpec` row in `CASE_REGISTRY`**. Listed in
suggested priority order (highest probe traffic / clearest anchor first):

#### Group A — Labor / Nómina (12 topics)

| # | Slug | Anchor | Topic key | Brief on disk |
|---|---|---|---|---|
| 1 | `liquidacion_mensual_nomina` | CST + Ley 100 | `laboral` | `knowledge_base/CORE ya Arriba/LABORAL_NOMINA/PLAYBOOKS/playbook_laboral_liquidacion_mensual_nomina.md` |
| 2 | `prestaciones_sociales` | CST 249 + 306 + 186 | `laboral` | `…/playbook_laboral_prestaciones_sociales.md` |
| 3 | `liquidacion_terminacion` | CST 64 | `laboral` | `…/playbook_laboral_liquidacion_terminacion.md` |
| 4 | `pila_aportes` | Decreto 1990/2016 | `parafiscales_seguridad_social` | `…/playbook_laboral_pila_aportes.md` |
| 5 | `ugpp_fiscalizacion` | Ley 1607 art. 178 | `parafiscales_seguridad_social` | `…/playbook_laboral_ugpp_fiscalizacion.md` |
| 6 | `nomina_electronica_dspne` | Res. DIAN 000013/2021 | `laboral` | `…/playbook_laboral_nomina_electronica_dspne.md` |
| 7 | `contrato_prestacion_vs_laboral` | CST 23 | `laboral` | `…/playbook_laboral_contrato_prestacion_vs_laboral.md` |
| 8 | `contrato_aprendizaje_sena` | Ley 789 art. 30-31 | `laboral` | `…/playbook_laboral_contrato_aprendizaje_sena.md` |
| 9 | `embargos_salario` | CST 154-156 | `laboral` | `…/playbook_laboral_embargos_salario.md` |
| 10 | `smmlv_aux_transporte_anual` | Decreto SMMLV anual | `laboral` | `…/playbook_laboral_smmlv_aux_transporte_anual.md` |
| 11 | `subsidios_transporte_alimentacion` | CST 230 + Ley 1393 art. 30 | `laboral` | `…/playbook_laboral_subsidios_transporte_alimentacion.md` |
| 12 | `teletrabajo_trabajo_casa` | Ley 2088/2021 | `laboral` | `…/playbook_laboral_teletrabajo_trabajo_casa.md` |

#### Group B — Renta descuentos (6 topics)

| # | Slug | Anchor | Topic key | Brief on disk |
|---|---|---|---|---|
| 13 | `discapacidad_200` | Ley 361/1997 art. 31 | `descuentos_tributarios_renta` | `…/RENTA/PLAYBOOKS/playbook_renta_discapacidad_200.md` |
| 14 | `donaciones_descuento` | Art. 257 ET | `descuentos_tributarios_renta` | `…/playbook_renta_donaciones_descuento.md` |
| 15 | `energias_renovables` | Ley 1715/2014 art. 11 | `descuentos_tributarios_renta` | `…/playbook_renta_energias_renovables.md` |
| 16 | `factura_electronica_1` | Ley 2277/2022 art. 7 | `descuentos_tributarios_renta` | `…/playbook_renta_factura_electronica_1.md` |
| 17 | `ica_descuento_50` | Art. 115 par. ET | `descuentos_tributarios_renta` | `…/playbook_renta_ica_descuento_50.md` |
| 18 | `mujeres_violencia_200` | Ley 1257/2008 art. 23 | `descuentos_tributarios_renta` | `…/playbook_renta_mujeres_violencia_200.md` |

#### Group C — Retención fuente (3 topics)

| # | Slug | Anchor | Topic key | Brief on disk |
|---|---|---|---|---|
| 19 | `retencion_autoretencion` | Decreto 2201/2016 | `retencion_en_la_fuente` | `…/RETENCION_FUENTE/PLAYBOOKS/playbook_retencion_autoretencion.md` |
| 20 | `retencion_bases_minimas` | Decreto 572/2025 | `retencion_en_la_fuente` | `…/playbook_retencion_bases_minimas.md` |
| 21 | `retencion_tablas_ag_2025_2026` | Art. 383 ET + tablas DIAN | `retencion_en_la_fuente` | `…/playbook_retencion_tablas_ag_2025_2026.md` |

#### Group D — Renta deducciones extras (3 topics)

| # | Slug | Anchor | Topic key | Brief on disk |
|---|---|---|---|---|
| 22 | `aportes_parafiscales_seguridad_social` | Art. 108 ET | `costos_deducciones_renta` | `…/RENTA/PLAYBOOKS/playbook_renta_aportes_parafiscales_seguridad_social.md` |
| 23 | `pagos_no_constitutivos_salario` | CST 128 + Ley 1393 art. 30 | `costos_deducciones_renta` | `…/playbook_renta_pagos_no_constitutivos_salario.md` |
| 24 | `salario_integral` | CST 132 + Ley 50 art. 18 | `laboral` | `…/playbook_renta_salario_integral.md` |

#### Group E — Renta tarifas (2 topics)

| # | Slug | Anchor | Topic key | Brief on disk |
|---|---|---|---|---|
| 25 | `ttd_tasa_minima` | Art. 240 par. 6 ET | `tarifas_renta_y_ttd` | `…/playbook_renta_ttd_tasa_minima.md` |
| 26 | `zomac_zese` | Ley 1819 arts. 235-237 + Ley 2238/2022 | `zomac_zese_incentivos_geograficos` | `…/playbook_renta_zomac_zese.md` |

#### Group F — Panel adiciones (4 topics)

| # | Slug | Anchor | Topic key | Brief on disk |
|---|---|---|---|---|
| 27 | `panel_cierre_fiscal_anual_checklist` | (transversal) | `declaracion_renta` | `…/PANEL_ADICIONES/PLAYBOOKS/playbook_panel_cierre_fiscal_anual_checklist.md` |
| 28 | `panel_ica_territorial` | Ley 14/1983 + Decreto 1333/1986 | `ica` | `…/playbook_panel_ica_territorial.md` |
| 29 | `panel_migracion_rst_ordinario` | Art. 909 ET | `regimen_simple` | `…/playbook_panel_migracion_rst_ordinario.md` |
| 30 | `panel_reteica_municipal` | Acuerdos municipales | `ica` | `…/playbook_panel_reteica_municipal.md` |

#### Group G — NIIF (1 topic)

| # | Slug | Anchor | Topic key | Brief on disk |
|---|---|---|---|---|
| 31 | `niif_depreciacion_niif_vs_fiscal` | Art. 137 ET + Sección 17 PYMES | `estados_financieros_niif` | `knowledge_base/estados_financieros_niif/PLAYBOOKS/playbook_niif_depreciacion_niif_vs_fiscal.md` |

#### Group H — Tier 2 extras (6 topics)

| # | Slug | Anchor | Topic key | Brief on disk |
|---|---|---|---|---|
| 32 | `tier2_doc_comprobatoria_f1125_f1729` | Art. 260-5 ET + Decreto 1496/2024 | `precios_de_transferencia` | `…/RENTA/PLAYBOOKS/playbook_tier2_doc_comprobatoria_f1125_f1729.md` |
| 33 | `tier2_impuesto_patrimonio` | Arts. 292-296 ET | `impuesto_patrimonio_personas_naturales` | `…/playbook_tier2_impuesto_patrimonio.md` |
| 34 | `tier2_omision_activos_434a` | Art. 434-A ET | `regimen_sancionatorio` | `…/playbook_tier2_omision_activos_434a.md` |
| 35 | `tier2_precios_transferencia_umbrales` | Art. 260-5 ET | `precios_de_transferencia` | `…/playbook_tier2_precios_transferencia_umbrales.md` |
| 36 | `tier2_recursos_dian` | Arts. 720-732 ET | `procedimiento_tributario` | `…/playbook_tier2_recursos_dian.md` |
| 37 | `tier2_renta_presuntiva_historico` | Art. 188 ET | `renta_presuntiva` | `…/playbook_tier2_renta_presuntiva_historico.md` |

**Total: 37 topics**. Spot-check the file paths with
`ls "knowledge_base/CORE ya Arriba"/LABORAL_NOMINA/PLAYBOOKS/`
etc. before starting any batch.

---

## §2. Idea (gate 1)

**One-sentence statement:** for each of the 37 candidate topics, add a
`CaseSpec` row (detector + bullets + keyword whitelist + anchor
articles + search queries) so the planner emits a deterministic anchor
when the case fires, ensuring the playbook content reaches the answer
regardless of hybrid_search ranking.

**Why this matters even though answers already work:**

- Today's behavior: hybrid_search ranks the playbook chunk in top-K,
  polish surfaces it correctly **most of the time**. Failure modes:
  ranking drifts to adjacent chunks (e.g., the broader CST page
  outranks the specific liquidación chunk), polish picks wrong
  article number.
- With Lane B: detector fires → `_CASE_ANCHOR_REGISTRY` walk emits
  `kind="article"` entry point → `retriever._fetch_anchor_article_rows`
  pulls the exact chunk → `_merge_rows_prefer_anchors` puts it in
  primary → polish prompt receives the right article in
  `ARTÍCULOS PERMITIDOS` → answer cites the correct anchor in 100 %
  of probes.

---

## §3. Plan (gate 2 — implementation outline)

### §3.1 Per-topic wiring (the mechanical 20-min loop)

For each of the 37 topics, follow this exact sequence. The pattern
is identical to fix_v16_may §3.3 — read that file's §3.3.1–§3.3.5
**verbatim** before starting; this section assumes that pattern as
given.

**Step-by-step, per topic:**

1. **Read the playbook brief.** Path is in §1's table. Extract:
   - H1 title + one-line summary (for the detector docstring).
   - `## Cómo lo pregunta un contador` phrases (detector markers).
   - `## Norma principal` anchor article number(s).
   - `## Normas relacionadas` for search-query enrichment.
   - `## Respuesta operativa` numbered bullets (case bullets).
2. **Write the detector.** Choose the right sibling file:
   - If `case_detectors_b5.py` is < 800 LOC, append there.
   - Else create `case_detectors_b6.py` and re-export from
     `case_detectors.py` facade. Apply the engineering rules from
     fix_v16_may §3.3.1: word-boundary regex for tokens ≤ 4 chars,
     combined-keyword paths for verb forms, no imports from
     `answer_*` modules, append to `__all__`.
3. **Re-export.** Add the detector name to:
   - `case_detectors.py` facade.
   - `answer_synthesis_helpers.py` import block.
4. **Create `case_bullets/<slug>.py`.** Pattern (copy from an
   existing sibling — `notificaciones_electronicas.py` is the
   cleanest reference):
   - `SPEC = CaseSpec(name=..., detector=<fn>, bullets=tuple(...),
     keywords=tuple(...), anchor_articles=tuple(...),
     search_queries=tuple(...), source_label="<slug>_anchor")`.
   - Bullets **verbatim from the playbook's `## Respuesta operativa`**
     — do NOT paraphrase. Each bullet ≤ 280 chars. Bold UVT
     thresholds + article numbers with `**…**`. Never invent UVT/%
     values outside what the brief provides (the polish UVT validator
     will reject inventions per fix_v15_may §3).
5. **Register in `CASE_REGISTRY`.** Edit
   `case_bullets/__init__.py`:
   - Add the import line at the top.
   - Append the SPEC to the `CASE_REGISTRY` tuple.
   - **Order matters.** Put **specific-anchor topics BEFORE broader
     anchors**. Concrete examples:
     - `salario_integral` BEFORE `liquidacion_mensual_nomina` (the
       latter's markers would otherwise intercept).
     - `panel_reteica_municipal` BEFORE `panel_ica_territorial`
       (reteica is a sub-case of territorial ICA).
     - `tier2_precios_transferencia_umbrales` BEFORE
       `tier2_doc_comprobatoria_f1125_f1729` (umbrales decide if doc
       comprobatoria applies).
6. **Test row.** Add one block to
   `tests/test_planner_case_anchor_registry.py`:
   - `test_<slug>_case_anchors_art_<X>` — asserts planner emits the
     anchor.
   - `test_<slug>_case_adds_search_queries` — asserts the
     search-queries row was registered.
7. **Run focused tests:**
   ```
   PYTHONPATH=src:. uv run pytest \
       tests/test_planner_case_anchor_registry.py \
       tests/test_case_detectors_purity.py -q
   ```
   All green or STOP and diagnose.

### §3.2 Cross-domain anchor cross-check (per topic)

Topics whose anchor article lives in a **different libro** than the
router's natural topic require an entry in
`config/article_secondary_topics.json`. From §1's table, these are
the topics needing pre-add:

| Topic | Anchor | Lives in | Router likely picks | Add secondary_topic |
|---|---|---|---|---|
| `panel_migracion_rst_ordinario` | art. 909 ET | renta (libro 1) | `regimen_simple` | `regimen_simple` |
| `tier2_omision_activos_434a` | art. 434-A ET | sanciones (libro 5) | `regimen_sancionatorio` | already covered |
| `tier2_recursos_dian` | arts. 720-732 ET | libro 5 | `procedimiento_tributario` | already covered |
| `tier2_doc_comprobatoria_f1125_f1729` | art. 260-5 ET | renta (libro 1) | `precios_de_transferencia` | already covered |
| `tier2_renta_presuntiva_historico` | art. 188 ET | renta | `renta_presuntiva` | add `renta_presuntiva` |

Add the missing entries **before** running the staging probe for
that topic. Don't relax the coherence-gate threshold (per
`feedback_thresholds_no_lower`).

### §3.3 Non-ET anchor handling (Option A only, no schema change)

The current `_CASE_ANCHOR_REGISTRY` schema is `(detector,
tuple[article_id, ...], source_label)`. Article IDs are ET-only
strings. For the 12 labor topics + 4 panel + 3 retención + 1 NIIF
whose anchor is CST / Ley / Decreto / Resolución:

**Option A (this plan).** Anchor on the **closest ET tie-in** when
one exists; cite the non-ET norm in the body bullets. Concrete:

| Topic | Anchor used in registry | Non-ET norm cited in bullets |
|---|---|---|
| `salario_integral` | `108` (deducción salarios) + `387` (retención) | CST 132 + Ley 50/1990 art. 18 |
| `pila_aportes` | `108` (parafiscales requisito) + `114-1` | Decreto 1990/2016 |
| `ugpp_fiscalizacion` | `108` + `114-1` | Ley 1607 art. 178 |
| `nomina_electronica_dspne` | `617` (FE general) | Res. DIAN 000013/2021 |
| `liquidacion_mensual_nomina` | `108` + `387` | CST + Ley 100 |
| `prestaciones_sociales` | `108` + `387` | CST 249-306 |
| `liquidacion_terminacion` | `108` + `387` | CST 64 |
| `contrato_prestacion_vs_laboral` | `383` (retención salarios) | CST 23 |
| `contrato_aprendizaje_sena` | `108` (deducción) | Ley 789 art. 30-31 |
| `embargos_salario` | `108` | CST 154-156 |
| `smmlv_aux_transporte_anual` | `108` + `387` | Decreto SMMLV anual |
| `subsidios_transporte_alimentacion` | `108` + `387` | CST 230 + Ley 1393 art. 30 |
| `teletrabajo_trabajo_casa` | `108` | Ley 2088/2021 |
| `panel_cierre_fiscal_anual_checklist` | `26` + `588` + `714` | (transversal — keep generic) |
| `panel_ica_territorial` | `115` + `115-1` | Ley 14/1983 + Decreto 1333/1986 |
| `panel_migracion_rst_ordinario` | `909` | (anchor is ET) |
| `panel_reteica_municipal` | `115` + `115-1` | Acuerdos municipales |
| `niif_depreciacion_niif_vs_fiscal` | `137` (depreciación fiscal) | Sección 17 PYMES + NIC 16 |
| `discapacidad_200` | `255` (descuento) | Ley 361/1997 art. 31 |
| `energias_renovables` | `255` | Ley 1715/2014 art. 11 + Decreto 829/2020 |
| `factura_electronica_1` | `255` | Ley 2277/2022 art. 7 |
| `mujeres_violencia_200` | `255` | Ley 1257/2008 art. 23 |
| `retencion_autoretencion` | `365` (causación) | Decreto 2201/2016 |
| `retencion_bases_minimas` | `383` (tabla) + `392` | Decreto 572/2025 |
| `retencion_tablas_ag_2025_2026` | `383` + `387` | (anchor is ET) |

**Option B (schema change to support `kind="ley"` / `kind="decreto"`)
is OUT OF SCOPE for v17.** Document the deferral in the change-log
row and let v18+ revisit when more non-ET topics ship.

---

## §4. Success criterion (gate 3 — measurable minimum)

A topic is SHIPPED when ALL of the following hold:

1. The `CaseSpec` row exists in `case_bullets/<slug>.py` and is
   imported in `case_bullets/__init__.py::CASE_REGISTRY`.
2. The detector function exists in
   `case_detectors_b5.py` (or `_b6.py` if created) and is re-exported
   in both `case_detectors.py` and `answer_synthesis_helpers.py`.
3. `tests/test_planner_case_anchor_registry.py` carries two new
   tests for the topic; full suite green.
4. `tests/test_case_detectors_purity.py` still green (no
   `answer_*` import leaks in detector modules).
5. The full related sweep passes:
   ```
   PYTHONPATH=src:. uv run pytest \
       tests/test_planner_case_anchor_registry.py \
       tests/test_case_detectors_purity.py \
       tests/test_classifier_playbook_override.py \
       tests/test_classifier_path_veto.py \
       tests/test_answer_polish_rejected_fallback.py \
       tests/test_answer_synthesis_practica.py -q
   ```
6. Probe via `answer-engine-probe` skill against dev:staging returns
   `pass` or `warn` (never `fail`) for one representative question
   per topic.
7. The answer cites the registered anchor article in the rendered
   answer (visible inline anchor + Anclaje Legal section).

**Batch-level criterion:** ≥ 90 % of attempted topics in a batch
reach SHIPPED on first probe. Below 90 %, pause the batch and
diagnose the playbook template / engineer intake (per fix_v16_may §4
and `feedback_diagnose_before_intervene`).

---

## §5. Test plan (gate 4 — how to test, who runs what)

| Stage | Actor | Environment | What runs | Pass condition |
|---|---|---|---|---|
| 1. Read brief | Engineer | shell | `cat <brief_path>` | Has all 6 named sections from fix_v16_may §3.1 |
| 2. Wire detector + bullets + spec + registry | Engineer | local editor | Per §3.1 of this plan | All 7 sub-steps complete |
| 3. Cross-domain check | Engineer | grep | Confirm anchor article is in `config/article_secondary_topics.json` OR primary_topic matches router | Either present or not needed |
| 4. Unit tests | Engineer | local | Sweep from §4 step 5 | All green |
| 5. Restart server | Engineer + operator | dev:staging | `kill $(pgrep -f lia_graph.ui_server) && npm run dev:staging` | Health endpoint 200 |
| 6. Staging probe | Engineer + operator | dev:staging via `answer-engine-probe` | One probe per topic | `pass` or `warn`; cited anchor matches `anchor_articles` |
| 7. Operator review | Operator | browser | Read rendered answer | Would forward to paying SMB-contador as-is? |

**Decision rule per topic.** Stages 1–7 all clean → topic SHIPPED.
Any `fail` at stage 6 → blocking; diagnose layer per §6 below.

**Decision rule per batch (~3 topics).** If ≥ 1 of 3 topics fails at
stage 6, pause the batch, run a retrospective, do NOT relax the
per-topic decision rule (per `feedback_thresholds_no_lower`).

---

## §6. Greenlight (gate 5 — end-user validation)

Per `feedback_verify_fixes_end_to_end`, unit tests alone are not
sufficient.

- **Per topic:** operator opens dev:staging in a browser, types a
  representative question for the topic, reads the rendered answer.
- **Sign-off question:** would the operator forward this answer to a
  paying SMB-contador customer **as-is**? If yes → greenlight. If
  no → record the specific drag (citation, tone, missing detail) and
  route back per §7.

Greenlight is what separates "tests are green" from "contador-ready."
Do not skip.

---

## §7. Refine-or-discard (gate 6 — what to do if a topic regresses)

Per `feedback_diagnose_before_intervene`:

1. **Pinpoint the layer.**
   - Bullet missing → Lane B bullet extraction (re-read brief, verify
     verbatim transfer).
   - Anchor wrong → `_CASE_ANCHOR_REGISTRY` row anchor list edit.
   - Detector fires on wrong query → tighten markers / add veto guard
     for adjacent topic.
   - Coherence-gate abstains despite correct retrieval → add
     `article_secondary_topics.json` entry for the anchor.
   - Polish strips bullet → A4 fallback should catch it; if not,
     bullet > 280 chars or contains invented UVT.
2. **Refine vs discard.**
   - Refine: keep the row, fix the narrow issue, re-probe.
   - Discard: explicit `↩ regressed-discarded` status in the
     ship-state table at the bottom of this file; remove the row
     from `CASE_REGISTRY`; keep the case_bullets/<slug>.py file in
     the repo with a comment explaining the discard reason.
3. **Record the regression** in
   `docs/aa_next/playbook_regressions.md` (create if absent) with:
   topic, layer, fix applied or "discarded with reason."

A topic moves 🛠 → 🧪 → ✅ via §4 + §6; demotes to ↩ if §7 cannot
recover it in one iteration. Never silently roll back.

---

## §8. Rollback

**Per-topic rollback.**
1. Delete the import + registry row in
   `case_bullets/__init__.py`.
2. Delete `case_bullets/<slug>.py`.
3. Remove the detector from `case_detectors_b5.py` (or `_b6.py`).
4. Remove the re-exports in `case_detectors.py` +
   `answer_synthesis_helpers.py`.
5. Remove the test rows from
   `tests/test_planner_case_anchor_registry.py`.

No corpus or cloud rollback needed — chunks stay tagged correctly.
The answer just falls back to retrieval-only ranking for that topic.

**Full v17 rollback** (unlikely): `git revert` of the v17 commits.

---

## §9. Suggested batching schedule

| Batch | Topics | Effort | Recommended order rationale |
|---|---|---|---|
| v17 b1 | `liquidacion_mensual_nomina`, `prestaciones_sociales`, `liquidacion_terminacion` | ~1 h | Highest-traffic nómina core. Same anchor cluster (108 + 387). |
| v17 b2 | `pila_aportes`, `ugpp_fiscalizacion`, `nomina_electronica_dspne` | ~1 h | Compliance + nómina electrónica — also tightly clustered. |
| v17 b3 | `contrato_prestacion_vs_laboral`, `contrato_aprendizaje_sena`, `salario_integral` | ~1 h | Common contador questions; salario_integral order-sensitive vs nómina. |
| v17 b4 | `embargos_salario`, `smmlv_aux_transporte_anual`, `subsidios_transporte_alimentacion`, `teletrabajo_trabajo_casa` | ~1.5 h | Closes the labor block. |
| v17 b5 | `discapacidad_200`, `donaciones_descuento`, `energias_renovables` | ~1 h | Renta descuentos batch 1. |
| v17 b6 | `factura_electronica_1`, `ica_descuento_50`, `mujeres_violencia_200` | ~1 h | Renta descuentos batch 2. |
| v17 b7 | `retencion_autoretencion`, `retencion_bases_minimas`, `retencion_tablas_ag_2025_2026` | ~1 h | Retención block. |
| v17 b8 | `aportes_parafiscales_seguridad_social`, `pagos_no_constitutivos_salario` | ~45 min | Renta deducciones extras. |
| v17 b9 | `ttd_tasa_minima`, `zomac_zese`, `niif_depreciacion_niif_vs_fiscal` | ~1 h | Tarifas + NIIF. |
| v17 b10 | `panel_cierre_fiscal_anual_checklist`, `panel_ica_territorial`, `panel_migracion_rst_ordinario`, `panel_reteica_municipal` | ~1.5 h | Panel adiciones — heavy on cross-topic guards. |
| v17 b11 | `tier2_doc_comprobatoria_f1125_f1729`, `tier2_impuesto_patrimonio`, `tier2_omision_activos_434a` | ~1 h | Tier 2 batch 1. |
| v17 b12 | `tier2_precios_transferencia_umbrales`, `tier2_recursos_dian`, `tier2_renta_presuntiva_historico` | ~1 h | Tier 2 batch 2. |

**Total: ~12 hours engineering** across 12 batches. Operator review
adds ~15 min per topic.

Per `feedback_canonicalizer_autonomous_progression`, an autonomous
operator session may proceed b1 → b12 without per-batch check-ins as
long as the §4 + §6 criteria fire green. Stop only when a batch hits
the §5 "≥ 1 fail per batch" pause condition.

---

## §10. Known residuals (NOT in v17 scope)

1. **Non-ET-anchor schema change.** Many labor / panel / Ley
   anchors are still mapped to the closest ET tie-in (§3.3 Option A).
   A future fix should extend `_CASE_ANCHOR_REGISTRY` to support
   `kind="ley"` / `kind="decreto"` / `kind="sentencia"` and migrate
   these topics. Out of scope here.
2. **Polish UVT validator cue extension.** New anchors flow into
   `_no_invented_uvt_ranges` via `CASE_REGISTRY.anchor_articles`
   automatically (fix_v15_may §3). No flag change.
3. **A4 substantive fallback bullet quality.** When polish rejects,
   A4 builds the answer from `CaseSpec.bullets`. Verify each new
   topic's bullets render cleanly in the fallback shape (no broken
   tables, no orphaned `**bold**` sections). Track residuals in
   `docs/aa_next/playbook_regressions.md`.
4. **Latency 23-32 s** is consistent across all probes. Within the
   system's normal range; tracked separately if/when SLA matters.
5. **Chunk-noise leak in Recomendaciones Prácticas (NEW —
   surfaced 2026-05-15 by §0.3.2).** First 7–8 bullets of every
   labor answer are corpus-chunk noise (orphaned Q&A, forward-dated
   marketing, stale SMMLV values, unverified-vigencia reform
   references) that lead the authored SPEC content. Independent of
   v17 wiring; affects every answer. Tracked as `fix_v18_may` —
   see §0.3.2 for the suggested mini-plan structure.
6. **Polish may drop authored SPEC bullets on concrete-numbers
   questions (NEW — observed 2026-05-15 by §0.2.1).** Two probes
   of the same topic (`liquidacion_mensual_nomina`) yielded
   different polish behavior: general framing preserved all SPEC
   bullets verbatim; concrete-numbers framing replaced them with a
   computed worked answer in `Procedimiento Sugerido`. Both
   outcomes are defensible. **Decision deferred to operator**
   (§0.3.3): permissive (current) vs strict (SPEC bullets are
   sacred). No code change pending; if operator chooses "strict,"
   the fix would land in `_build_polish_prompt` as a stronger
   preservation rule + a polish-side validator that rejects polish
   output missing > N SPEC bullets that were present in the template.
7. **Missing playbook — aportes proporcionales / cotizante tipo 51 /
   trabajador por días (NEW — surfaced 2026-05-15 by operator
   probe).** Question: *"tengo una empleada a tiempo parcial (labora
   3 días con salario mínimo por días) — ¿cómo le pago la EPS, es
   proporcional?"*. NO v17 detector fired (all 9 b1–b3 detectors
   returned False). With no anchor, retrieval ranked an
   incapacidad-themed chunk top-K; the practica extractor pulled
   `Recomendaciones Prácticas` + `Procedimiento Sugerido` entirely
   from off-topic incapacidad content.
   **Resolution (2026-05-15):**
   - Corpus check showed all 50 `to upload/` markdown files (including
     TPR-L02) are ALREADY in cloud Supabase since
     `gen_20260425123153` (April 25). TPR-L02 has 16 chunks with
     embeddings populated, tagged `tema=laboral, topic=laboral,
     knowledge_class=practica_erp`. Upload was a no-op — the gap was
     SPEC/detector coverage, not corpus.
   - **38th SPEC landed (🧪):** `aportes_proporcionales_tiempo_parcial`
     in `case_bullets/aportes_proporcionales_tiempo_parcial.py`,
     anchored at ET arts. 108 + 114-1 (Option A per §3.3). 8 bullets
     covering: salario proporcional (CST 197), auxilio transporte
     proporcional, árbol de decisión Decreto 2616 vs Ley 2466 Art. 34
     vs regla general, tipo cotizante PILA 02, hogar persona natural
     SIN exoneración 114-1, prestaciones también proporcionales.
   - **Detector lives in new `case_detectors_b6.py`** (108 LOC). `_b5`
     crossed the 800-LOC ceiling so a sibling was created per
     `feedback_granular_edits` + §3.1 step 2. Future labor / nómina
     detectors that don't fit `_b5`'s existing groupings land here.
   - **Registry order:** `_APORTES_PROPORCIONALES_TIEMPO_PARCIAL_SPEC`
     is registered FIRST in the v17 block (line 175 of
     `case_bullets/__init__.py`), ahead of salario_integral / PILA /
     mensual_nomina. Empleada-doméstica-por-días is the most niche
     case and must win over the broader detectors when a tiempo-parcial
     / por-días / SISBÉN marker fires.
   - **7 new tests** in `test_planner_case_anchor_registry.py`:
     verbatim operator probe + plural variants + SISBÉN-only path +
     two anti-tests (full-time nómina + pure renta) + a precedence
     test vs pila_aportes. Sweep 226/226 green.
   - Status: **✅ verified in dev:staging 2026-05-15 evening.** Operator
     re-asked the verbatim probe; rendered answer cites Art. 108 +
     Art. 114-1 in Anclaje Legal; all 8 SPEC bullets surface
     (salario proporcional table, auxilio table, Opciones A/B/C
     decision tree, tipo cotizante 02 in PILA, hogar persona natural
     sin exoneración 114-1, prestaciones también proporcionales,
     dotación 3×/año). Residuals #5 + #8 still visible in 2 leading
     practica lines ("art. 127-132 ET" + "art. 186 ET" — both CST
     articles wrongly tagged ET; chunk-noise extractor leak) but the
     SPEC content stands on its own merits. **Operator verdict: pass.**
8. **Polish hallucinates `ET` namespace on CST article numbers
   (NEW — surfaced 2026-05-15 same probe).** Polished answer cited
   "(arts. 127-132 ET)" and "(art. 186 ET)". CST 127-132 = pagos no
   constitutivos de salario, CST 186 = vacaciones. ET 186 was renta
   presuntiva (derogated). The `_no_invented_uvt_ranges` validator
   (fix_v15_may §3) catches invented numbers, not invented
   *namespaces*. Suggested fix: a sibling validator
   `_no_cross_codigo_article_aliasing` that rejects polish output
   pairing an `art:<num>` token with a `codigo` label (ET / CST /
   Ley / Decreto) when the same `(num, codigo)` pair is absent from
   the polish prompt's evidence + template + question text. Same
   shadow → enforce cycle as fix_v15_may §3.

---

## §11. Change log entry (to be appended after merge)

Two-stage change log because v17 is being shipped in **partial
batches** with operator-probe gates between batches; the row text
must reflect WHICH batches actually landed at each merge so the
orchestration history is honest.

### §11.1 Pre-merge state (current, 2026-05-15 evening)

- **10 of 38 topics landed code-side** (batches b1 + b2 + b3 = 9,
  plus the b3+ tail addition `aportes_proporcionales_tiempo_parcial`
  surfaced by an operator probe gap — see residual #7).
- **2 of 10 topics are ✅** verified in dev:staging via operator
  probe: `liquidacion_mensual_nomina` (afternoon screenshot, §0.2.3)
  and `aportes_proporcionales_tiempo_parcial` (evening probe, §12).
- 8 of 10 topics are 🧪 awaiting operator probe per §0.3.1.
- Generic sub-bullet rendering infrastructure landed (§0.2.1).
- v17 detector widening pass landed (§0.2.2).
- **NEW `case_detectors_b6.py`** sibling created (108 LOC) when
  `_b5` crossed the 800-LOC ceiling — houses the b3+ tail detector
  `is_aportes_proporcionales_tiempo_parcial_case`. Per
  `feedback_granular_edits` + §3.1 step 2. Future labor / nómina
  detectors land here.
- Unit-test sweep: **226 / 226 green** (181 pre-v17 baseline + 8
  sub-bullet + 30 planner-registry additions for the 9 b1–b3 topics
  including widening anti-tests + 7 for the b3+ tail, latest run
  2026-05-15 evening).
- **No orchestration change-log row written yet** — wait for the
  full b1–b3 batch to reach ✅ before appending.

### §11.2 Row to append once b1–b3 are all ✅

Append to `docs/orchestration/orchestration.md` under `### Change Log`:

```
- v2026-MM-DD-fix-v17-lane-b-wiring-batches-1-3-labor-block
  - Adds 9 CaseSpec rows to case_bullets/CASE_REGISTRY for the
    v17 b1+b2+b3 labor / nómina block: liquidacion_mensual_nomina,
    prestaciones_sociales, liquidacion_terminacion, pila_aportes,
    ugpp_fiscalizacion, nomina_electronica_dspne,
    contrato_prestacion_vs_laboral, contrato_aprendizaje_sena,
    salario_integral.
  - Allowlist edit: config/topic_norm_allowlist.json `laboral` key
    gains art:114-1 / 387 / 388 / 401-3 / 617 / 651 / 771-2 to
    allowed_prefixes + facturacion_electronica to cross_topic_allowed.
  - Generic sub-bullet rendering capability: SPEC authors can nest
    bullets via presentation.with_sub_bullets; renderer expands a
    non-whitespace sentinel token at the final step. Polish prompt
    rule 5 instructs the LLM to preserve nested structure.
  - Detector widening pass: 6 of 9 v17 detectors widened for plural
    forms and general phrasings. Two Spanish-orthography traps
    documented inline: verb-root split under accent-strip
    (despid- vs desped-) and singular/plural ending change
    (aprendiz → aprendices, shared stem aprendi).
  - No env flag changes; no schema changes.
  - Rollback: per-topic via row + sibling-file removal (see §8).
  - Sub-bullet rollback: revert presentation.py SUB_BULLET_TOKEN /
    with_sub_bullets / expand_sub_bullets and the render_bullet_section
    update; revert _build_polish_prompt rule 5; revert
    case_bullets/liquidacion_mensual_nomina.py to flat strings.
```

### §11.3 Subsequent rows (b4 → b12)

Append one row per batch as it lands and is ✅. **Do not bundle
b4–b12 into a single row** even if they land in fast succession —
batched change-log rows make per-topic rollback harder to trace.

### §11.4 Mirror surfaces

- `docs/guide/env_guide.md` `## Runtime Retrieval Flags` — append:
  "no flag delta, content-only batch (CaseSpec + allowlist edits
  + sub-bullet rendering infrastructure)".
- `CLAUDE.md` Hot Path section unchanged. (The sub-bullet feature
  is an authoring-surface improvement, not a runtime-shape change;
  the orchestration map does not need a new node.)
- `frontend/src/app/orchestration/shell.ts` / `orchestrationApp.ts` —
  unchanged (no env-matrix change to render).

### §11.5 Rollback recipes for the follow-on changes

**Sub-bullet rendering rollback (one revert):**

```
# Revert the renderer + helper:
git checkout HEAD~ -- src/lia_graph/pipeline_d/presentation.py
# Revert the polish prompt rule 5:
git checkout HEAD~ -- src/lia_graph/pipeline_d/answer_llm_polish.py
# Revert the demo SPEC bullets to flat strings:
git checkout HEAD~ -- src/lia_graph/pipeline_d/case_bullets/liquidacion_mensual_nomina.py
# Optional: drop the lint tests:
git rm tests/test_sub_bullet_rendering.py
```

Post-rollback, SPEC bullets that used `with_sub_bullets` will fail
to import (`ImportError`). Either revert those SPEC files too OR
inline a no-op shim. The first option is cleaner.

**Detector widening rollback (one revert):**

```
git checkout HEAD~ -- src/lia_graph/pipeline_d/case_detectors_b5.py
# Optional: drop the widening tests:
# (the 11 new tests in tests/test_planner_case_anchor_registry.py
# would need to be removed too — they are appended at the bottom of
# the v17 b1+b2+b3 test block).
```

Detector widening rollback narrows the detectors to their initial
b1–b3 form. Affected probes (e.g. "recargos de horas extras y
dominicales según el CST") will miss again.

---

## §12. Ship-state table (update as batches land)

Mark each topic 🛠 / 🧪 / ✅ / ↩ as it progresses. A fresh executing
agent should update this section IN THE SAME COMMIT as the code
change.

| Batch | Topic | Status | Probe verdict | Notes |
|---|---|---|---|---|
| v17 b1 | `liquidacion_mensual_nomina` | ✅ | pass | code landed 2026-05-15; **operator screenshot 2026-05-15 afternoon** confirms Anclaje Legal includes Art. 108 + Art. 387 ✓, all 7 SPEC bullets render verbatim ✓, sub-bullets display with visual indentation in the browser ✓, bold formatting preserved through polish ✓. Detector widened (§0.2.2) to fire on plurals + general "según el CST" phrasing. |
| v17 b1 | `prestaciones_sociales` | 🧪 | — | code landed 2026-05-15; unit tests green. Detector widened (§0.2.2) to fire on "prestaciones sociales obligatorias" + plural `primas` with payment-timing context. Pending dev:staging probe per §0.3.1. |
| v17 b1 | `liquidacion_terminacion` | 🧪 | — | code landed 2026-05-15; unit tests green; detector covers both Spanish verb roots (despid- + desped-) per §0.2.2. Widened to catch `término fijo` / `obra o labor` + termination context. Pending dev:staging probe per §0.3.1. |
| v17 b2 | `pila_aportes` | 🧪 | — | code landed 2026-05-15; unit tests green. Detector widened (§0.2.2) to fire on `planilla de aportes` general phrasing. Pending dev:staging probe per §0.3.1. |
| v17 b2 | `ugpp_fiscalizacion` | 🧪 | — | code landed 2026-05-15; unit tests green (NOTE: avoid "desalarización" in probes — substring "esal" trips the donaciones detector registered earlier; the §0.1 probe table uses "qué revisa la UGPP en una fiscalización" instead). Detector NOT widened — already fired on §0.1 probe text. Pending dev:staging probe per §0.3.1. |
| v17 b2 | `nomina_electronica_dspne` | 🧪 | — | code landed 2026-05-15; unit tests green; anchor at art. 617 ET (FE); laboral allowlist extended with 617/651/771-2 + cross_topic facturacion_electronica. Detector NOT widened — already fired on §0.1 probe text. Pending dev:staging probe per §0.3.1. |
| v17 b3 | `contrato_prestacion_vs_laboral` | 🧪 | — | code landed 2026-05-15; unit tests green; anchor at art. 383 ET (retención salarios). Detector widened (§0.2.2) to fire on `contratista` + `prestación de servicios` general framing. Pending dev:staging probe per §0.3.1. |
| v17 b3 | `contrato_aprendizaje_sena` | 🧪 | — | code landed 2026-05-15; unit tests green; anchor at art. 108 ET (deducción). **CRITICAL FIX (§0.2.2):** detector fallback stem switched from `aprendiz` to `aprendi` because `aprendiz` is NOT a substring of `aprendices` (Spanish plural orthography). Pending dev:staging probe per §0.3.1. |
| v17 b3 | `salario_integral` | 🧪 | — | code landed 2026-05-15; unit tests green; registered BEFORE liquidacion_mensual_nomina; precedence test passes. Detector NOT widened — already fired on §0.1 probe text. Pending dev:staging probe per §0.3.1. |
| v17 b4 | `embargos_salario` | 🛠 | — | |
| v17 b4 | `smmlv_aux_transporte_anual` | 🛠 | — | |
| v17 b4 | `subsidios_transporte_alimentacion` | 🛠 | — | |
| v17 b4 | `teletrabajo_trabajo_casa` | 🛠 | — | |
| v17 b5 | `discapacidad_200` | 🛠 | — | non-ET anchor (Ley 361) |
| v17 b5 | `donaciones_descuento` | 🛠 | — | |
| v17 b5 | `energias_renovables` | 🛠 | — | non-ET anchor (Ley 1715) |
| v17 b6 | `factura_electronica_1` | 🛠 | — | non-ET anchor (Ley 2277) |
| v17 b6 | `ica_descuento_50` | 🛠 | — | order vs ICA deduction case |
| v17 b6 | `mujeres_violencia_200` | 🛠 | — | non-ET anchor (Ley 1257) |
| v17 b7 | `retencion_autoretencion` | 🛠 | — | non-ET anchor (Decreto 2201) |
| v17 b7 | `retencion_bases_minimas` | 🛠 | — | non-ET anchor (Decreto 572/2025) |
| v17 b7 | `retencion_tablas_ag_2025_2026` | 🛠 | — | |
| v17 b8 | `aportes_parafiscales_seguridad_social` | 🛠 | — | |
| v17 b8 | `pagos_no_constitutivos_salario` | 🛠 | — | |
| v17 b9 | `ttd_tasa_minima` | 🛠 | — | order vs tarifa_general_pj |
| v17 b9 | `zomac_zese` | 🛠 | — | dedicated topic key |
| v17 b9 | `niif_depreciacion_niif_vs_fiscal` | 🛠 | — | order vs depreciacion case |
| v17 b10 | `panel_cierre_fiscal_anual_checklist` | 🛠 | — | transversal — careful with veto guards |
| v17 b10 | `panel_ica_territorial` | 🛠 | — | |
| v17 b10 | `panel_migracion_rst_ordinario` | 🛠 | — | |
| v17 b10 | `panel_reteica_municipal` | 🛠 | — | order BEFORE ica_territorial |
| v17 b11 | `tier2_doc_comprobatoria_f1125_f1729` | 🛠 | — | order AFTER umbrales |
| v17 b11 | `tier2_impuesto_patrimonio` | 🛠 | — | |
| v17 b11 | `tier2_omision_activos_434a` | 🛠 | — | |
| v17 b12 | `tier2_precios_transferencia_umbrales` | 🛠 | — | order BEFORE doc_comprobatoria |
| v17 b12 | `tier2_recursos_dian` | 🛠 | — | |
| v17 b12 | `tier2_renta_presuntiva_historico` | 🛠 | — | secondary_topic add needed |
| v17 b3+ tail | `aportes_proporcionales_tiempo_parcial` | ✅ | pass | **38th SPEC.** Landed 2026-05-15 evening after operator probe surfaced the gap (none of the 9 b1–b3 detectors fired on *"empleada a tiempo parcial 3 días — ¿cómo le pago la EPS, es proporcional?"*). Detector lives in NEW `case_detectors_b6.py` (b5 had crossed 800 LOC). Operator probe ✅: Anclaje Legal cites Art. 108 + Art. 114-1; all 8 SPEC bullets render (salario proporcional table, auxilio table, Opciones A/B/C, tipo cotizante 02, hogar PN sin 114-1, prestaciones proporcionales, dotación). Residuals #5 chunk-noise + #8 ET-on-CST aliasing still visible in the answer's leading practica lines but unrelated to v17 SPEC content. |

Status legend:
- 🛠 — code landed, not yet probed.
- 🧪 — verified locally (unit tests green).
- ✅ — verified in dev:staging via operator-driven probe + screenshot
  (the screenshot is the gate-5 / gate-6 evidence per
  `feedback_verify_fixes_end_to_end`).
- ↩ — regressed and discarded with reason (recorded in
  `docs/aa_next/playbook_regressions.md`).

Current totals (2026-05-15 evening): **2 ✅, 8 🧪, 28 🛠** (out of 38 topics — original 37 v17 candidates + the b3+ tail addition `aportes_proporcionales_tiempo_parcial`).

---

## §13. Author notes for the executing agent

- **Idempotency.** Adding a topic is idempotent: re-running the
  intake on the same playbook produces the same code edits. The
  registry is a tuple with a stable order — appending the same
  SPEC twice would just shadow the second; remove duplicates if
  you see them.
- **Granularity.** Per `feedback_granular_edits`, do NOT append to
  any module already ≥ 1000 LOC.
  `case_detectors_b5.py` is the current last sibling; check its
  size before adding the 38th detector and create
  `case_detectors_b6.py` if it crosses 800 LOC. Same rule for
  `answer_synthesis_sections.py` if it ever grows past 1500 LOC.
- **Verification non-negotiable.** Per `feedback_no_hallucinated_examples`,
  every numeric value, article reference, plazo, monto, or registro
  detail you wire into bullets MUST be verifiable against the
  expert's playbook URLs. If the expert wrote it but the URL no
  longer resolves, STOP and flag it before landing.
- **No new env flags.** v17 is registry-content only. If you find
  yourself adding `LIA_*` flags, you are extending scope — stop and
  surface the question.
- **No money in status reports.** Per `feedback_no_money_quoting`,
  report effort in time + scope, not currency.
- **Plain language in operator updates.** Per
  `feedback_plain_language_communication`, end-of-batch reports to
  the operator are plain language by default; engineering depth only
  when asked.
- **Default run mode is dev:staging.** Per
  `feedback_default_run_mode_staging`. Verify via
  `retrieval_backend=supabase` on first response of each probe run.
- **SME panel runs only on explicit request.** Per
  `feedback_sme_panel_explicit_request_only`. Do NOT auto-run
  `scripts/eval/run_sme_parallel.py` after a batch lands — finish
  the code + tests + per-topic probes, then ASK before launching the
  panel.

### §13.1 Lessons learned during b1 probe cycle (carry forward to b4+)

These are concrete, repeatable patterns the executing agent should
apply to every future v17 batch. Documented here so they are not
re-discovered by trial.

1. **Server does not hot-reload Python.** After ANY edit to
   `case_detectors_*.py`, `case_bullets/*.py`, `presentation.py`,
   `answer_*.py`, or `_registry.py`, the operator MUST restart the
   server:

   ```
   kill $(pgrep -f "lia_graph.ui_server") 2>/dev/null; \\
       pkill -f "scripts/dev-launcher" 2>/dev/null; true
   pgrep -fa "lia_graph.ui_server|dev-launcher"  # must print nothing
   npm run dev:staging
   ```

   Without this, probe results reflect the previous code, not the
   edits. The b1 cycle wasted one probe on this exact mistake.

2. **Write the audit probe BEFORE writing the bullets.** Before
   landing a new SPEC, run a 5–10-line python script that calls the
   detector against the §0.1 probe text plus 2–3 plural / general
   variants. If any probe misses, widen BEFORE the unit tests.
   Reference structure used in §0.2.2:

   ```python
   from lia_graph.pipeline_d.case_detectors import is_<topic>_case
   from lia_graph.pipeline_d.planner import _normalize_text
   for msg in ("operator probe text", "plural variant", "general framing"):
       nm = _normalize_text(msg)
       print(f"{'OK' if is_<topic>_case(nm) else 'MISS'} | {msg}")
   ```

3. **Run the anti-test too.** For every widening branch, write at
   least one anti-test (a query that LOOKS related but should NOT
   fire the detector) and confirm it stays MISS. Without the
   anti-test, you'll over-broaden and intercept queries the next
   topic's detector should handle. b1's widening lessons: `recargo`
   alone is ambiguous (ICA / IVA mora vs labor); `prima` alone is
   ambiguous (insurance vs prestaciones); `aporte` alone is
   ambiguous (renta vs labor SGSS).

4. **Spanish singular/plural under accent-strip is a recurring trap.**
   Before using a bare-substring marker like `"aprendiz"`, mentally
   compute what `unicodedata.normalize("NFKD", word).encode("ascii", "ignore")`
   does to BOTH the singular and plural forms. If they diverge,
   use the shared stem (`"aprendi"` covers `aprendiz` + `aprendices`).
   See §0.2.2 trap table.

5. **Spanish verb roots also split under accent-strip.**
   `despedí → despedi` (no `despid` substring) but `despido → despido`
   (has `despid`). Combined-keyword paths must check BOTH roots:
   `if ("despid" in nm or "desped" in nm) and (…)`. See
   `case_detectors_b5.py::is_liquidacion_terminacion_case` for the
   reference shape.

6. **Long enumerations belong in `with_sub_bullets`, not semicolons.**
   Per §0.2.1, any SPEC bullet that lists ≥ 3 enumerated items
   (rates, thresholds, conditions, percentages) should use
   `with_sub_bullets`. Markdown nesting reads in seconds; a
   semicolon paragraph reads in 30 seconds. The renderer expands
   the sentinel correctly; verified in the browser per §0.2.3.

7. **Polish behavior is empirical, not guaranteed.** Even with
   rule 5 in the polish prompt ("preservá la estructura de listas
   anidadas"), polish may still paraphrase or drop SPEC bullets
   under some conditions (§0.2.1 final note). Run TWO probes per
   topic — one general framing and one concrete-numbers framing —
   to surface the variance before declaring a topic ✅.

8. **Chunk-noise leak (residual §10.5) leads every labor answer.**
   The first 7–8 bullets of `Recomendaciones Prácticas` are
   corpus-chunk noise, not authored SPEC content. Independent of
   v17 wiring; affects every answer. Operator probes will see this
   above the SPEC content — judge the SPEC content on its own
   merits and flag the noise separately for fix_v18 per §0.3.2.

9. **The §0.1 probe table avoids the donaciones "esal" substring
   collision.** The legacy `is_donaciones_case` detector keys on
   bare `"esal"` (intended to catch the ESAL entity), which
   collides with `"desalarización" → "desalarizacion"`. The §0.1
   UGPP probe phrasing is "qué revisa la UGPP en una fiscalización"
   to sidestep this. Future v18-class fix should switch the
   donaciones detector to a word-boundary regex.

---

*End of fix_v17_may.md.*
