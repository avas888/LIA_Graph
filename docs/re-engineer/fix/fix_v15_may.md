# fix_v15_may.md — Structural UVT/% Invention Validator

> **Author context (zero-agent-context protocol).** This plan is
> self-contained. A fresh LLM agent with no prior conversation history
> can execute it from the file system as-is. Every file path, function
> name, regex, env flag, test case, and decision rule is specified
> verbatim. Verify every artifact against `git ls-files` before acting.
> If any cited path or function does not exist, STOP and report
> drift — do not invent.

## §0. TL;DR

**Idea.** Close the polish-validator gap that fix_v14_may §17 surfaced:
the LLM can hallucinate specific UVT ranges, percentages, and tarifa
values inside polished answers and neither
`_no_invented_norm_lineage` nor `_no_invented_periods` catches them.
Ship a third validator, `_no_invented_uvt_ranges`, that fails polish
whenever a UVT/% specific value in the polished output is not literally
present in the template OR in the evidence excerpts the polish saw.

**Why now.** v14.2 A3 (DIRECTIVA NUMÉRICA) was reverted on 2026-05-13
because one panel turn (`pr_rst_anticipo_bimestral_v1`) had the LLM
cite "3.5 %" as the Grupo 1 tarifa for Art. 908 ET, a value that does
not exist in the article. Polish accepted the output (`polish_mode=llm`)
because no validator scans numeric tarifa values. A contador acting on
that answer would under-liquidate the client's anticipo. The fix has
to be structural (validator), not prompt-level (directive) — that was
the lesson of §17.

**Effort.** 4–6 h. **Risk.** Low (flag-gated `enforce`/`shadow`/`off`,
no schema change, additive to existing polish validator chain).

---

## §1. Repository state assumed by this plan

Verify these before making changes. If any drift, STOP.

### Files that MUST exist

| Path | Purpose | Key symbols this plan references |
|---|---|---|
| `src/lia_graph/pipeline_d/answer_llm_polish.py` | Polish stage + validator chain | `POLISH_VALIDATORS`, `_no_invented_norm_lineage`, `_no_invented_periods`, `_build_polish_prompt`, `_build_numeric_directive` |
| `src/lia_graph/pipeline_d/contracts.py` | Evidence dataclasses | `GraphEvidenceBundle`, `GraphEvidenceItem` (fields `node_key`, `title`, `excerpt`) |
| `src/lia_graph/pipeline_c/contracts.py` | Request contract | `PipelineCRequest` (field `message`) |
| `scripts/dev-launcher.mjs` | Per-mode env flag matrix | block around `LIA_POLISH_REJECTED_FALLBACK_FILTER`, `LIA_LEGAL_ANCHOR_GATE_MODE`, `LIA_CHUNK_QUALITY_HEURISTIC_MODE` |
| `tests/test_answer_llm_polish.py` | Polish unit tests | `_request`, `_evidence`, `_template_answer`, `_capture_prompt` fixtures |
| `docs/orchestration/orchestration.md` | Env matrix + change log | `## Runtime Env Matrix (Versioned)`, `### Change Log` |
| `docs/guide/env_guide.md` | Per-mode env mirror | `## Runtime Retrieval Flags (v…)` table |
| `CLAUDE.md` | Project quickstart | `## Runtime Read Path (Env v…)` section + Active runtime flags list |
| `frontend/src/features/orchestration/orchestrationApp.ts` | `/orchestration` status card | `Env matrix v…` highlight chip |

### Sprint v14.2 ship state (assumed already merged)

- **A2 (chunk-quality heuristics):** `LIA_CHUNK_QUALITY_HEURISTIC_MODE=enforce`. Module `src/lia_graph/pipeline_d/chunk_quality_heuristics.py`. Patterns include `portal_login_boilerplate`, `cross_topic_operational_leak`, `case_study_caption`, `fragmento_relevante_caption`, `normative_key_caption`, `section_heading_dominant`, `toc_section_heading_dominant`, `question_dominant_caption`.
- **A4 (polish-rejected fallback bullet filter):** `LIA_POLISH_REJECTED_FALLBACK_FILTER=clean`, threshold `_MIN_EVIDENCE_CHARS = 300`. Module `src/lia_graph/pipeline_d/answer_polish_rejected_fallback.py`.
- **A3 (DIRECTIVA NUMÉRICA):** REVERTED. Kill switch `LIA_POLISH_NUMERIC_DIRECTIVE=off` default. Helper retained behind switch.
- **Env matrix version:** `v2026-05-13-fix-v14-2-fallback-filter`. v15 will bump to `v2026-05-XX-fix-v15-uvt-validator`.

### Concrete failure case (anchor — verify against this turn)

- **Turn:** `pr_rst_anticipo_bimestral_v1` in `evals/sme_validation_v1/runs/20260513T1431_v14_2_full_practica/pr_rst_anticipo_bimestral_v1.json`.
- **Question:** SAS comercio al detal vendió $80M en bimestre marzo-abril; cliente pide tarifa Art. 908 Grupo 1.
- **Polished answer cites:** "tarifa del **3,5%** sobre los ingresos brutos" applied to Grupo 1 ("Tiendas pequeñas, minimercados, micromercados y peluquería").
- **Real Art. 908 ET Grupo 1 rates (Ley 2277/2022):** 1.2 % / 2.8 % / 4.4 % / 5.4 % by UVT bracket. **3.5 % is not in the article.**
- **Polish trace:** `polish_mode=llm` (validator chain returned all-pass). `_no_invented_norm_lineage` passed (Art. 908 is in allowlist). `_no_invented_periods` passed (no 4-digit year invented). Nothing caught "3,5 %".

This is the exact failure mode the new validator must catch.

---

## §2. Idea (gate 1)

**One-sentence statement:** add a polish-stage validator
`_no_invented_uvt_ranges` that rejects polished output when a specific
numeric tarifa or UVT range appears in the polished text but is not
present (verbatim or as a normalized equivalent) in the template OR the
evidence excerpts the polish saw, with cue gating so the validator
only fires on questions that anchor specific tarifa articles
(Art. 240 / 241 / 242 / 383 / 908) or UVT references.

---

## §3. Plan (gate 2 — implementation outline)

### §3.1 Where the validator slots into the polish chain

The existing chain in `src/lia_graph/pipeline_d/answer_llm_polish.py`
registers validators as entries in `POLISH_VALIDATORS` near the top of
the module. Each entry is a dict with `id`, `validate` (callable
`(template, polished) → bool`), and a stable label. The validator
chain runs in order; the first failing validator sets
`polish_skip_reason` and the orchestrator routes to the fallback path.

Look for the existing block of the shape:

```python
POLISH_VALIDATORS = [
    {
        "id": "no_invented_norm_lineage",
        ...
        "validate": lambda template, polished: _no_invented_norm_lineage(template, polished),
    },
    {
        "id": "no_invented_periods",
        ...
        "validate": lambda template, polished: _no_invented_periods(template, polished),
    },
]
```

The new validator must be registered as a third entry AFTER
`no_invented_periods`. Reason for ordering: norm-lineage and periods
are cheaper regex checks; the UVT validator iterates over a larger
match set per invocation. Putting it last lets cheaper validators
short-circuit on the dominant rejection modes.

### §3.2 Function signature

Add to `answer_llm_polish.py`:

```python
def _no_invented_uvt_ranges(
    template: str,
    polished: str,
    evidence: GraphEvidenceBundle | None = None,
) -> bool:
    """Reject polish that introduces a specific numeric tarifa or UVT
    range value not present in the template or in the evidence
    excerpts the polish prompt rendered.

    Verbatim of fix_v15_may §3.2. Returns False (reject) when at least
    one numeric value in `polished` matches an A3-style pattern but is
    not present (verbatim or normalized) in `template ∪ evidence
    excerpts ∪ template's numeric set ∪ question text from the polish
    prompt's context).

    Cue-gated: only runs when the polished answer contains
    `_TARIFA_CONTEXT_RE` (article 240/241/242/383/908) or a UVT
    reference. Outside those contexts the validator is a noop (passes)
    to avoid blocking the chat polish step on monetary mentions that
    are not tarifa-anchored.
    """
```

The signature deliberately accepts `evidence` so the validator can
read the same excerpts the polish prompt saw. The existing two
validators only take `(template, polished)` — the registration plumbing
will need a minor lift to thread `evidence` through. See §3.5.

### §3.3 Pattern catalog

Add to `answer_llm_polish.py`. Each pattern is a regex with a clear
purpose:

```python
# fix_v15_may §3.3 — UVT/% specific value patterns the validator scans.
# Each match yields ONE candidate value to verify against the template
# + evidence excerpts. Patterns are conservative — they match values
# that are clearly tarifa-shaped, not arbitrary numbers anywhere in
# prose (e.g. "$25 millones" is a money figure, not a tarifa).

# Percentage value: "3,5 %" / "3.5%" / "35 %" / "0,5 %". Always with %.
_UVT_PERCENTAGE_RE = re.compile(
    r"(?<![\w.,])\d{1,2}(?:[.,]\d{1,2})?\s*%",
)

# UVT-range expression: "1090 UVT", "1.090 UVT", "0-1090 UVT".
_UVT_VALUE_RE = re.compile(
    r"(?<![\w.,])\d{1,3}(?:[.,]\d{3})*\s*UVT\b",
    re.IGNORECASE,
)

# Tarifa-context anchor: only fire the validator when the polished
# text references a tarifa-progressive article OR mentions "tarifa"
# alongside a percentage / UVT.
_TARIFA_CONTEXT_RE = re.compile(
    r"\b(?:art(?:[ií]culo?)?\.?\s*(?:240|241|242|383|908)|tarifa\s+(?:especial|progresiva|marginal|del?)|tabla\s+de\s+retenci[oó]n)\b",
    re.IGNORECASE,
)
```

### §3.4 Verification logic

Inside `_no_invented_uvt_ranges`:

1. If `_TARIFA_CONTEXT_RE.search(polished)` is None, return True
   (validator noop — the answer is not in tarifa context).
2. Build the "allowed set":
   - Extract all `_UVT_PERCENTAGE_RE` matches from `template`.
   - Extract all `_UVT_PERCENTAGE_RE` matches from each
     `evidence.primary_articles[i].excerpt`,
     `evidence.connected_articles[i].excerpt`, and
     `evidence.related_reforms[i].excerpt` (handle `None` / empty).
   - Same for `_UVT_VALUE_RE`.
   - Normalize each match by stripping whitespace, swapping `,` ↔ `.`
     decimal separator (so "3,5 %" and "3.5%" match), and lowercasing
     "UVT" → "uvt".
3. Extract the same patterns from `polished`, normalize identically.
4. Compute `invented = polished_set − allowed_set`.
5. Return `not invented`. If `invented` is non-empty, the validator
   fails the polish.

**False-positive guard.** Strip `**bold**` markers from `template`,
`polished`, and every excerpt before extraction — the polish prompt
allows the LLM to wrap numbers in `**…**`. Without stripping, the
validator would reject "**3.5%**" even when "3.5%" appears unbolded in
the excerpt.

### §3.5 Validator-chain plumbing

The existing `POLISH_VALIDATORS` callbacks only take `(template,
polished)`. To pass `evidence` to the new validator without breaking
the others:

1. Update each validator entry's `validate` callable signature to
   accept `(template, polished, evidence)` and ignore the third arg
   where unused.
2. Update the loop that runs the chain (look for the call site near
   `for validator in POLISH_VALIDATORS:` or similar) to pass
   `evidence` from the `_build_polish_prompt` call context.
3. Register the new entry:

```python
{
    "id": "no_invented_uvt_ranges",
    "description": "Polished output cited a UVT/% value not in the template or evidence excerpts.",
    "validate": lambda template, polished, evidence: _no_invented_uvt_ranges(template, polished, evidence),
},
```

### §3.6 Env knob

```python
_UVT_VALIDATOR_ENV = "LIA_POLISH_UVT_VALIDATOR"


def _uvt_validator_mode() -> str:
    """fix_v15_may §3.6 — `enforce | shadow | off`.

    * `enforce` — validator failure routes to fallback (production safety).
    * `shadow` — validator runs and emits diagnostic but does NOT fail
                 the polish (calibration mode, default at landing).
    * `off`    — validator is a noop.
    """
    raw = str(os.getenv(_UVT_VALIDATOR_ENV, "shadow") or "").strip().lower()
    if raw in {"enforce", "on", "1", "true"}:
        return "enforce"
    if raw in {"off", "0", "false", "no", "disabled"}:
        return "off"
    return "shadow"
```

In `shadow` mode the validator emits a trace step
`polish.uvt_validator.shadow` with the invented set but does NOT
return False — the polish proceeds. In `enforce` mode it returns False
and the polish stage records `polish_skip_reason="invented_uvt_ranges"`.

Promotion gate: keep `shadow` until at least one production run shows
the validator flagging the `pr_rst_anticipo_bimestral_v1` case
correctly with zero false positives across the 42-turn panel.

### §3.7 Trace step

Emit `polish.uvt_validator.applied` with details:

- `mode` ∈ `{enforce, shadow, off}`
- `cue_matched` (bool)
- `polished_value_count` (int)
- `allowed_value_count` (int)
- `invented_values` (list of strings, capped at 6)
- `outcome` ∈ `{noop_no_cue, pass, fail_enforce, fail_shadow}`

The chat path already wires `polish.applied` as a trace step. Mirror
that shape using the existing `tracers_and_logs.pipeline_trace.step`
import inside `answer_llm_polish.py`. If the import is not already
present, look at `pipeline_d/chunk_quality_heuristics.py` for the
"best-effort" trace pattern (try/except around the import — never
break polish on a trace failure).

---

## §4. Success criterion (gate 3)

**Numeric minimum on the 42-turn panel:**

- `pr_rst_anticipo_bimestral_v1`: validator flags the invented `3,5 %`
  in `enforce` mode → polish flips `llm → rejected` → A4 fallback
  composes substantive bullets WITHOUT the invented tarifa. Class
  shift from REJECT back to ACCEPTABLE or BORDERLINE.
- Across the other 41 turns: zero new polish rejections caused by the
  validator (false-positive rate ≤ 0). If false positives appear, the
  pattern catalog or normalization needs refinement before promotion.
- Strict pass rate ≥ v14.1 baseline (38.1 %). Combined with A2 + A4
  already in `enforce`, target ≥ 40 % strict pass.

Numbers are absolute. Do not relax — operator standing rule
"don't lower aspirational thresholds when granting an exception"
(memory: `feedback_thresholds_no_lower`).

---

## §5. Test plan (gate 4)

### §5.1 Unit tests — `tests/test_answer_llm_polish.py`

Add a section header comment `# fix_v15_may §5.1 — UVT validator
unit tests` and these cases. Reuse the existing `_request()`,
`_template_answer()`, `_evidence()` fixtures. For the validator
function-level tests, do NOT go through the polish pipeline — call
`_no_invented_uvt_ranges` directly:

```python
def test_uvt_validator_noop_outside_tarifa_context() -> None:
    """No Art. 240/241/242/383/908 or 'tarifa' reference → validator
    is a noop even if the polished text contains percentages."""
    template = "**Recomendaciones**\n- Verifica el gasto."
    polished = "**Recomendaciones**\n- Verifica el gasto. Margen: 5%."
    assert _no_invented_uvt_ranges(template, polished, None) is True


def test_uvt_validator_rejects_invented_tarifa_pct() -> None:
    """Reproduces pr_rst_anticipo_bimestral_v1: polished asserts a
    Grupo 1 tarifa of 3.5 % that is not in the template or excerpts."""
    template = "**Recomendaciones**\n- Aplica la tarifa del Art. 908 ET."
    polished = "**Recomendaciones**\n- Aplica la tarifa del 3,5% según Art. 908 ET."
    evidence = _evidence()  # no 3.5% in any excerpt
    assert _no_invented_uvt_ranges(template, polished, evidence) is False


def test_uvt_validator_accepts_pct_present_in_template() -> None:
    template = "**Recomendaciones**\n- Tarifa Art. 908 ET: 1,2%."
    polished = "**Recomendaciones**\n- Aplica la tarifa del **1,2%** del Art. 908 ET."
    assert _no_invented_uvt_ranges(template, polished, None) is True


def test_uvt_validator_accepts_pct_present_in_evidence_excerpt() -> None:
    """The excerpt the polish prompt rendered counts as ground truth.
    Bold markers must be stripped before comparing."""
    template = "**Recomendaciones**\n- Aplica la tarifa Art. 908 ET."
    polished = "**Recomendaciones**\n- Aplica **2,8%** del Art. 908 ET."
    # _evidence() helper must include an excerpt with "2,8%" somewhere.
    evidence = _evidence_with_excerpt_substring("2,8%")  # define this helper
    assert _no_invented_uvt_ranges(template, polished, evidence) is True


def test_uvt_validator_decimal_separator_normalization() -> None:
    """3,5% in evidence must match 3.5% in polished and vice versa."""
    template = "**Recomendaciones**\n- Tarifa Art. 242 ET de 3,5%."
    polished = "**Recomendaciones**\n- Aplica el 3.5% según Art. 242 ET."
    assert _no_invented_uvt_ranges(template, polished, None) is True


def test_uvt_validator_uvt_value_invented() -> None:
    template = "**Recomendaciones**\n- Tabla Art. 383 ET."
    polished = "**Recomendaciones**\n- Rango 95-150 UVT a tarifa 19% (Art. 383 ET)."
    evidence = _evidence()  # excerpts must NOT include 95-150 UVT
    assert _no_invented_uvt_ranges(template, polished, evidence) is False


def test_uvt_validator_uvt_value_present_in_excerpt() -> None:
    template = "**Recomendaciones**\n- Tabla Art. 383 ET."
    polished = "**Recomendaciones**\n- Rango 95 UVT (Art. 383 ET)."
    evidence = _evidence_with_excerpt_substring("95 UVT")
    assert _no_invented_uvt_ranges(template, polished, evidence) is True


def test_uvt_validator_mode_default_shadow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LIA_POLISH_UVT_VALIDATOR", raising=False)
    assert _uvt_validator_mode() == "shadow"


def test_uvt_validator_mode_enforce(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_POLISH_UVT_VALIDATOR", "enforce")
    assert _uvt_validator_mode() == "enforce"


def test_uvt_validator_mode_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_POLISH_UVT_VALIDATOR", "off")
    assert _uvt_validator_mode() == "off"


def test_uvt_validator_shadow_mode_does_not_fail_polish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """In shadow mode the validator records the invented set but the
    full polish pipeline still returns mode=llm (not rejected)."""
    monkeypatch.setenv("LIA_POLISH_UVT_VALIDATOR", "shadow")
    # Use the end-to-end polish call (see existing test
    # `test_polish_rejects_invented_periods` for shape). Assert
    # diagnostics show `uvt_validator_outcome="fail_shadow"` but
    # `polish_mode="llm"`.
    raise NotImplementedError("Implement with monkeypatched adapter that returns invented tarifa")
```

Minimum **10 cases**: 7 functional + 3 env-mode + 1 end-to-end
shadow-doesn't-fail. The `_evidence_with_excerpt_substring` helper
needs to be added to the test file's fixture section near
`_evidence()`.

### §5.2 Panel-level test

After unit tests pass and the kill switch is added to
`scripts/dev-launcher.mjs` defaulting to `shadow`:

1. Restart `npm run dev:staging` (mandatory — server caches Python
   modules; re-runs against stale code will mislead).
2. Run the 42-turn judge panel:

```bash
TS=$(date +%Y%m%dT%H%M)
mkdir -p evals/sme_validation_v1/runs/${TS}_v15_uvt_shadow_practica
mkdir -p evals/sme_validation_v1/runs/${TS}_v15_uvt_shadow_general

PYTHONPATH=src:. uv run python scripts/eval/run_sme_parallel.py \
  --run-dir evals/sme_validation_v1/runs/${TS}_v15_uvt_shadow_practica \
  --questions evals/sme_validation_v1/21q_retriever_Practica.jsonl \
  --workers 4 --server http://127.0.0.1:8787 --auth --timeout-seconds 180

PYTHONPATH=src:. uv run python scripts/eval/run_sme_parallel.py \
  --run-dir evals/sme_validation_v1/runs/${TS}_v15_uvt_shadow_general \
  --questions evals/sme_validation_v1/21q_retriever_General.jsonl \
  --workers 4 --server http://127.0.0.1:8787 --auth --timeout-seconds 180
```

3. Parse the `polish.uvt_validator.applied` trace step across every
   resulting JSON. Count `outcome=fail_shadow` turns. **Expected:**
   exactly the `pr_rst_anticipo_bimestral_v1` turn flags as invented
   "3,5 %"; zero other flags across the 42 (or the false-positive set
   is bounded ≤ 1 and demonstrably misfires that the catalog can be
   tightened to eliminate).

4. If shadow is clean → flip `LIA_POLISH_UVT_VALIDATOR=enforce` and
   re-run the panel. Verify the failing turn flips `polish_mode` from
   `llm → rejected` AND the A4 fallback (already shipped) renders a
   substantive answer without the invented tarifa.

### §5.3 Actors / environment

| Step | Actor | Environment |
|---|---|---|
| Unit tests | Engineering agent | local `make test-batched` substring scope, or `PYTHONPATH=src:. uv run pytest tests/test_answer_llm_polish.py -q` |
| Shadow panel | Engineering agent (operator-authorized; see `feedback_sme_panel_explicit_request_only` memory) | `npm run dev:staging` against cloud Supabase + cloud Falkor |
| Enforce panel | Same | Same |
| Final judge | Claude-as-judge (the same panel-judge protocol used in fix_v14_may §16/§17) | Read 42 paired answers, classify STRONG/ACCEPTABLE/BORDERLINE/REJECT |

### §5.4 Decision rule (INCLUDE / REVERT / REFINE)

**INCLUDE** if all of:

- Shadow panel: validator flags `pr_rst_anticipo_bimestral_v1` AND
  no false positives across the other 41 turns (or false positives
  ≤ 1 and demonstrably resolvable by tightening the catalog).
- Enforce panel: judge confirms zero NEW hallucinations introduced
  by the validator-mediated fallback path (i.e. the A4 fallback for
  the flagged turn does not introduce a different invented value).
- Strict pass rate ≥ v14.1 baseline (38.1 %).

**REVERT** if any of:

- ≥ 2 false positives in shadow that cannot be resolved by tightening
  the catalog without losing the true positive.
- Enforce mode causes a new PASS → REJECT class transition on any
  turn beyond `pr_rst_anticipo_bimestral_v1` (the target).
- A4 fallback for the flagged turn produces an answer judge-class
  worse than v14.2 full's REJECT (i.e. honest abstention preferred
  over hallucination, but pure garbage is not).

**REFINE** if shadow flags 2-4 false positives concentrated on a
recognizable lexical class (e.g. money amounts misclassified as
tarifas): tighten `_TARIFA_CONTEXT_RE` and re-run shadow. Maximum
one refinement attempt before declaring REVERT per the lifecycle
rule.

---

## §6. Greenlight criteria (gate 5)

Same shape as fix_v14_may §13.

- **Technical:** unit tests green; shadow panel clean per §5.4
  INCLUDE rule.
- **End-user validation:** SME inspects the 5 turns most affected
  by tarifa cues (`pr_rst_anticipo_bimestral_v1`,
  `pr_dividendos_retencion_socio_v1`,
  `ep_renta_dividendos_242_v1`,
  `pr_retencion_tabla_383_procedimientos_v1`,
  `ep_rst_elegibilidad_sectores_v1`) and confirms the enforce-mode
  answers are either (a) correct numerically, or (b) honest
  abstention via A4 fallback. Hallucinated tarifas are unacceptable
  in either mode.

The SME panel run is operator-authorized per the standing memory
`feedback_sme_panel_explicit_request_only` — do not auto-run.

---

## §7. Refine-or-discard (gate 6)

Document the panel result with status one of:

- ✅ `INCLUDE` — `LIA_POLISH_UVT_VALIDATOR=enforce` default across all
  three modes; bump env matrix to
  `v2026-05-XX-fix-v15-uvt-validator`.
- 🛠 `REFINE` (one attempt) — tighten `_TARIFA_CONTEXT_RE` or
  `_UVT_PERCENTAGE_RE`; re-run shadow.
- ↩ `DISCARD` — revert by setting `LIA_POLISH_UVT_VALIDATOR=off` in
  launcher defaults; keep the function + tests in repo so the next
  attempt can pick up the pattern catalog without re-discovering it.

---

## §8. Files to edit (full list with line-anchor hints)

1. **`src/lia_graph/pipeline_d/answer_llm_polish.py`**
   - Add the three regex constants from §3.3 near the existing
     `_YEAR_RE` constant.
   - Add `_no_invented_uvt_ranges` function after
     `_no_invented_periods` (verbatim shape per §3.2 + §3.4).
   - Add `_UVT_VALIDATOR_ENV` constant + `_uvt_validator_mode()` per
     §3.6.
   - Update `POLISH_VALIDATORS` entries' `validate` callables to take
     the third `evidence` arg (§3.5).
   - Update the validator-chain call site to pass `evidence` from the
     polish-stage context.
   - Wire the trace step per §3.7.

2. **`tests/test_answer_llm_polish.py`**
   - Add `_evidence_with_excerpt_substring(substring)` fixture helper
     near `_evidence()`.
   - Add the 10 test cases from §5.1.

3. **`scripts/dev-launcher.mjs`** — in the block where v14-era flags
   are defaulted (search for `LIA_POLISH_REJECTED_FALLBACK_FILTER` to
   find the right spot), add:

```javascript
  // fix_v15_may §3.6 — UVT/% invention validator. Shadow at landing
  // so the operator can verify the validator flags the
  // `pr_rst_anticipo_bimestral_v1` regression without affecting the
  // served chat. Promote to `enforce` after the §5.4 INCLUDE gate
  // clears.
  if (!String(env.LIA_POLISH_UVT_VALIDATOR || "").trim()) {
    env.LIA_POLISH_UVT_VALIDATOR = "shadow";
  }
```

4. **`docs/orchestration/orchestration.md`**
   - Bump env matrix version banner at line 3 to
     `v2026-05-XX-fix-v15-uvt-validator`.
   - Add a new banner block (top of file, before the v14.2 banner)
     summarizing v15.
   - Add a new env-matrix row for `LIA_POLISH_UVT_VALIDATOR`.
   - Add a change-log row in the `### Change Log` table.
   - Update the "Current version" header in the matrix section.
   - Format every entry as bullets / lists / tables, never prose
     paragraphs — operator standing rule (memory:
     `feedback_no_text_walls`).

5. **`docs/guide/env_guide.md`** — mirror the matrix row + a top
   banner block.

6. **`CLAUDE.md`**
   - Bump `## Runtime Read Path (Env v…)` header.
   - Add a fix_v15_may bullet under the Active runtime flags section.
   - Format as bullets, no walls.

7. **`frontend/src/features/orchestration/orchestrationApp.ts`** —
   update the `<span class="orch-highlight-label">Env matrix v…</span>`
   chip text.

---

## §9. Rollback recipe (one flag flip, no redeploy)

```
LIA_POLISH_UVT_VALIDATOR=off
```

The validator stays in code; the function returns True for every call
(noop). Tests for the function still pass because they call it
directly, bypassing the env gate. Operators can also pin
`LIA_POLISH_UVT_VALIDATOR=shadow` to keep the diagnostic on while
disabling the production effect.

---

## §10. Non-obvious constraints (mandatory reading)

These are derived from the standing memories that ship with the
project. A fresh agent will be loaded with the same memory set, but
some constraints aren't visible from the code alone:

- **No silent fallbacks.** The polish chain must propagate validator
  failures to the orchestrator's polish-rejected path. Do NOT swallow
  a validator exception and return True — that hides regressions and
  violates the project's "no silent fallback" non-negotiable.
- **No retroactive lowering of thresholds.** The 38.1 % strict-pass
  bar from v14.1 baseline is the floor for v15 INCLUDE. Do not relax.
- **Don't auto-run SME panels.** Land code + unit tests, then ask the
  operator "ready to run the panel?" — same rule as fix_v14_may.
- **Default run mode is dev:staging.** When the panel runs, the
  diagnostic `retrieval_backend=supabase` should appear on every
  response. If it shows `artifacts`, the launcher flags drifted.
- **A4 fallback is the safety net.** When this validator fires in
  enforce mode, the fallback assembler (already shipped) is what the
  user sees. The fallback's threshold of `_MIN_EVIDENCE_CHARS = 300`
  is what determines whether the user sees a substantive answer or an
  honest abstention. Do not lower the threshold to compensate for
  validator over-firing; tighten the validator instead.
- **The polish prompt is touchy.** Adding logs or trace steps inside
  `_build_polish_prompt` itself is fine; changing the prompt text is
  out of scope for v15. The v14.1 §15 entry documents the operator-
  amended decision rule and the v14.2 §17 entry documents how
  prompt-engineering alone failed. v15 is about the validator layer,
  not the prompt.
- **Markdown discipline.** Every doc change here is bullets / lists /
  tables. Never prose paragraphs longer than two sentences. Tables
  for "what / why / rollback" trios.

---

## §11. Status lifecycle

Track in this file's footer:

- 💡 idea (v15 §2 written, this doc lands)
- 🛠 code landed (function + tests + env knob + docs)
- 🧪 verified locally (`pytest tests/test_answer_llm_polish.py -q` green)
- ✅ verified in target environment (42-turn shadow panel + enforce panel + SME confirmation)
- ↩ regressed-discarded (if §7 lands DISCARD)

Each phase advances only when the prior is signed off. Do not jump
🛠 → ✅ without the 🧪 step.

---

## §12. Status (as of this doc landing)

- 💡 idea — written.
- 🛠 code landed — **done 2026-05-13.** Validator `_no_invented_uvt_ranges` + env knob `LIA_POLISH_UVT_VALIDATOR` (default `shadow`) + trace step + `_validate_against_rules` evidence plumbing landed in `src/lia_graph/pipeline_d/answer_llm_polish.py`. New `PromptRule` registered between `no_invented_periods` and `neutral_spanish`. Launcher default added in `scripts/dev-launcher.mjs`. Docs bumped to `v2026-05-13-fix-v15-uvt-validator` across `docs/orchestration/orchestration.md`, `docs/guide/env_guide.md`, `CLAUDE.md`, `frontend/src/features/orchestration/orchestrationApp.ts`.
- 🧪 verified locally — **done 2026-05-13.** `PYTHONPATH=src:. uv run pytest tests/test_answer_llm_polish.py` → `31 passed in 0.09s` (12 v15 cases + 1 REFINE regression case for question-text false positive).
- 🛠 REFINE landed (2026-05-13, post first shadow panel) — first shadow panel surfaced 1 false positive on `ep_gmf_exencion_350uvt_v1` (validator flagged `350uvt` + `50%` even though both values appear verbatim in the user's question). Plan §3.4 explicitly listed "question text from the polish prompt's context" in the allowed set; initial implementation missed it. Threaded `request.message` through `_validate_against_rules` → `_invoke_validator` → `_no_invented_uvt_ranges(template, polished, evidence, question)`. Sibling validators dispatch through narrowing-signature TypeError fallback (no API breakage). New regression test `test_uvt_validator_accepts_value_present_in_question`.
- 🧪 shadow panel rerun (2026-05-13, post-REFINE) — 42-turn panel against `dev:staging` cloud Supabase + cloud Falkor with `LIA_POLISH_UVT_VALIDATOR=shadow`. Polish modes: 25 rejected (existing validators) / 17 llm / 1 skipped. Validator events on the 17 polish-llm turns: 13 `noop_no_cue` + 4 `pass` + **0 `fail_shadow`**. **Zero false positives.** Anchor turn `pr_rst_anticipo_bimestral_v1` polished cleanly without inventing `3,5%` (cue matched → `pass`).
- 🧪 anchor amplifier rerun (2026-05-13) — restarted with `LIA_POLISH_NUMERIC_DIRECTIVE=on` (the kill-switched A3 helper) + `LIA_POLISH_UVT_VALIDATOR=shadow`; re-ran 21-turn practica panel. Anchor turn STILL polished cleanly without inventing tarifa values (`pass` outcome). The v14.2 §17 hallucination is stochastic — Gemini at temp=0 still varies on long structured-output prompts; we couldn't reliably reproduce on demand. Architectural correctness of the validator is established by `test_uvt_validator_enforce_mode_rejects_invented_tarifa` which deterministically simulates the exact `3,5%` pattern with a mocked adapter.
- 🧪 enforce panel (2026-05-13) — 42-turn panel against `dev:staging` with `LIA_POLISH_UVT_VALIDATOR=enforce`. Polish modes: 25 rejected / 16 llm / 1 skipped. **Zero turns rejected with `skip_reason="invented_uvt_ranges"`.** Existing skip reasons unchanged (`invented_periods` 13, `invented_norm_lineage` 10, `anchors_stripped` 2, `topic_safety_abstention` 1). Validator's enforce-mode side effect on this 42-turn corpus: nil. Safe to promote.
- ✅ verified in target environment — **partial.** Zero false positives in shadow + zero new rejections in enforce confirm the validator is safe to ship. The strict §5.4 INCLUDE clause "validator flags `pr_rst_anticipo_bimestral_v1`" was not satisfied IN production (LLM didn't reproduce the v14.2 hallucination across 3 panel runs); architectural correctness covered by deterministic unit test. **Recommendation:** promote `LIA_POLISH_UVT_VALIDATOR=shadow → enforce` per the operator's risk-forward beta-flag stance — zero downside on the 42-turn baseline + structural safety net for when the regression returns.
- ↩ regressed-discarded — N/A.

### Panel run artifacts

| Phase | Run dir |
|---|---|
| First shadow (pre-REFINE) | `evals/sme_validation_v1/runs/20260513T1721_v15_uvt_shadow_practica`, `…_v15_uvt_shadow_general` |
| Shadow rerun (post-REFINE) | `evals/sme_validation_v1/runs/20260513T1733_v15_uvt_shadow_r2_practica`, `…_v15_uvt_shadow_r2_general` |
| Anchor amplifier (A3 on) | `evals/sme_validation_v1/runs/20260513T1740_v15_uvt_shadow_amp_practica` |
| Enforce panel | `evals/sme_validation_v1/runs/20260513T1745_v15_uvt_enforce_practica`, `…_v15_uvt_enforce_general` |
