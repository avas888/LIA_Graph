# fix_v3.md — phase 4 hand-off: synthesis layer trips on non-ET-article primary chunks

> **Drafted 2026-04-29 ~2:50 PM Bogotá** by claude-opus-4-7 immediately
> after fix_v2 phase 3 closed (commit `5c266d6`, panel 22 → 29/36).
> **Audience: any zero-context agent (fresh LLM or engineer) who picks
> up this work next. You can pick this up cold.**
>
> **Preceding state (READ FIRST):**
> * `docs/re-engineer/fix/fix_v1.md` + `fix_v1_diagnosis.md` —
>   provider-order flip restored 8/36 → 22/36.
> * `docs/re-engineer/fix/fix_v2.md` §A — generalized
>   `_classify_article_rows` to accept 5 structural signals; 22/36 →
>   29/36 acc+, **0 ok→zero regressions** but **1 acc→weak downgrade**
>   (`regimen_cambiario_P3`) caused by the fix itself (see §1 below).
> * Phase-4 panel goal: **29 → ≥32/36 acc+ without losing any of the
>   8 newly-passing qids from fix_v2.**
>
> **What this doc is**: a self-contained operating plan for the next
> agent. Read §0 first if you have no context.

---

## 0. Zero-context primer

You are working in `/Users/ava-sensas/Developer/Lia_Graph/`, a graph-native
RAG product for Colombian accountants ("Lia Graph", branched from
Lia Contador).

**Read these in order, ~25 minutes:**

1. **`CLAUDE.md`** — repo operating guide. Critical sections for this
   work: "Hot Path (main chat)", "Retrieval-stage deep trace
   (2026-04-29)", "Idea vs verified improvement — mandatory six-gate
   lifecycle", "Long-running Python processes — always detached +
   heartbeat".
2. **`AGENTS.md`** — companion to CLAUDE.md.
3. **`docs/re-engineer/fix/fix_v2.md`** §A — what landed in phase 3 and
   why. The fix_v3 work BUILDS ON fix_v2, doesn't replace it.
4. **`config/article_secondary_topics.json`** + **`config/compatible_doc_topics.json`**
   — SME-curated topic adjacency configs that fix_v2 wired into the
   classifier.
5. **`src/lia_graph/pipeline_d/retriever_supabase.py::_classify_article_rows`**
   and **`src/lia_graph/pipeline_d/retriever_supabase.py::_fetch_anchor_article_rows`**
   — the two functions fix_v2 modified. Read top-to-bottom; the comment
   blocks lay out the 5-signal definition of "primary evidence".
6. **`src/lia_graph/pipeline_d/answer_synthesis.py`** + the
   `answer_synthesis_*` and `answer_assembly_*` modules listed in
   CLAUDE.md "Hot Path" — the synthesis-layer modules this fix touches.

**Memory-pinned guardrails (non-negotiable):**

* Don't lower the aspirational threshold (29/36 stays as the floor;
  ≥32/36 is the next gate).
* Diagnose before intervene.
* Cloud writes pre-authorized for Lia Graph (none expected here — this
  is a code-only fix).
* Plain-language status. No money quoting.
* Six-gate lifecycle on every pipeline change.
* Don't run the full pytest suite in one process — `make test-batched`.

---

## 1. The diagnosis (verified 2026-04-29 from
`evals/sme_validation_v1/runs/20260429T192350Z_fix_v2_evidence_classifier_v3/`)

The 7 qids that did NOT reach acc+ in the fix_v2 panel split into two
distinct downstream symptoms. Both are **synthesis/assembly-layer**
issues; the coherence gate now passes correctly for 6 of 7 of them
(`reason=primary_on_topic`).

### Symptom A — broken/truncated answer (3 qids: `served_weak`)

| qid | answer chars | preview |
|---|---|---|
| `regimen_cambiario_P1` | 184 | `**Ruta sugerida** / 1. ## Paso a Paso Práctico ### PASO 1 — Identificar si PYME Requiere Canalización Obligatoria Pregunta clave (arts. paso-a-paso-pr-ctico y posiciones-de-expertos ET).` |
| `regimen_cambiario_P3` | 109 | `**Ruta sugerida** / 1. PYME Importadora — Qué hacer paso a paso Situación (arts. paso-a-paso-pr-ctico y 26 ET).` |
| `regimen_sancionatorio_extemporaneidad_P2` | 239 | `**Riesgos y condiciones** / - Las personas o entidades obligadas a declarar...` |

**Root cause** (verified by inspecting `top_chunk_ids` in the trace):
fix_v2's signal (3) (`document.topic == router_topic`) promotes
practica/expertos chunks from docs like
`CORE_ya_Arriba_Documents_to_branch_and_improve_Regimen_Cambiario_Practica_LOGGRO`
and `CORE_ya_Arriba_REGIMEN_CAMBIARIO_PYME_EXPERTOS_E01-regimen-cambiario-pyme-interp`.
These docs are correctly tagged `topic=regimen_cambiario` at the document
level, so they pass signal (3). BUT their chunks have `chunk_id` like
`<doc>::paso-a-paso-pr-ctico` (slugified section heading), so
`_derive_article_key` returns `paso-a-paso-pr-ctico` as the article_key.
The synthesis layer then renders citations as
`(arts. paso-a-paso-pr-ctico y posiciones-de-expertos ET)` — a literal
template leak, not a real article reference. The full answer composition
collapses because the assembly module couldn't bind a coherent
`Respuestas directas` block to non-numeric primary articles.

**Why this is fix_v2's fault, not pre-existing:** in the anchor
(20260429T172422Z_gemini_primary_full), `regimen_cambiario_P3` was
`served_acceptable` because none of those practica chunks were in
`primary` — they were in `support_documents` (different rendering
path). After fix_v2 promoted them, the synthesis layer is the limiting
factor. The latent bug always existed; fix_v2 uncovered it.

### Symptom B — answer composes but classifier says off-topic (4 qids: `served_off_topic`)

| qid | gate verdict | answer chars | citations | likely cause |
|---|---|---|---|---|
| `conciliacion_fiscal_P2` | `no_router_topic` | 2122 | 5 | topic_router didn't resolve a router topic → coherence gate skips → answer composes from raw retrieval. Classifier sees off-topic relative to expected `conciliacion_fiscal`. **Different bug — router-side, not synthesis.** |
| `conciliacion_fiscal_P3` | `primary_on_topic` | 2700 | 4 | Substantive answer about NIIF 16 + formato 2516. Drifts toward leasing technique rather than pure conciliación. |
| `descuentos_tributarios_renta_P2` | `primary_on_topic` | 2572 | 4 | Substantive answer about IVA pagado en activos fijos / art 258-1 ET. Classifier looks for descuentos_tributarios_renta keywords; answer reads as IVA-mechanics. |
| `regimen_sancionatorio_extemporaneidad_P1` | `primary_on_topic` | 2114 | 4 | Substantive answer about art 639 ET sanción mínima. Probably classifier wants extemporaneidad-specific keywords. |

**Root cause hypothesis**: the SME-classifier rules in
`scripts/eval/run_sme_validation.py` are stricter than the panel's
intent. The answers in 3 of the 4 are substantive and grounded; only
`conciliacion_fiscal_P2` has a real underlying bug (router didn't
resolve a topic, so the coherence gate skipped).

---

## 2. The plan — two routes, run them in this order

### Route A (primary, highest leverage) — tighten the primary-promotion gate

**Problem**: fix_v2's signal (3) (`document.topic == router_topic`)
admits practica/expertos chunks whose `article_key` is a slugified
section heading, not an ET article number. The synthesis layer can't
render these as `Art. <key>` cleanly.

**Fix**: in `_classify_article_rows`, when the promotion was triggered
by a signal OTHER than (1) explicit anchor, also require the
`article_key` to look like a real ET article identifier (regex
`^\d+(?:-\d+)?$`). Non-numeric article_keys go to `connected` /
`support_documents` instead, where they used to live pre-fix_v2.

**Code site**: `src/lia_graph/pipeline_d/retriever_supabase.py:874-921`
(the for-loop in `_classify_article_rows` that fix_v2 added).

**Smallest possible diff**:

```python
import re
_NUMERIC_ARTICLE_KEY_RE = re.compile(r"^\d+(?:-\d+)?$")

# inside the for-row loop:
is_numeric_article = bool(_NUMERIC_ARTICLE_KEY_RE.match(article_key))
signals_router_topic = bool(router_topic) and is_numeric_article and (
    chunk_topic == router_topic
    or doc_topic == router_topic
    or (doc_topic != "" and doc_topic in compatible_doc_topics)
    or router_topic in article_topic_index.get(article_key, frozenset())
)
```

(Keep signal (1) explicit-anchor unchanged — explicit anchors stay
primary regardless of key shape, because the planner is asserting
they're real articles by name.)

**Risk**: would lose primary classification for any practica/expertos
content that legitimately is the "primary" answer source. Acceptable
trade-off because (a) those docs go to support_documents which DO get
synthesized into the answer, and (b) they were always in support_documents
pre-fix_v2 and panel was at 22/36 — restoring that path doesn't lose the
8 newly-passing qids, which all have real ET article hits in primary.

### Route B (parallel, smaller leverage) — render non-numeric article keys cleanly in synthesis

**Problem**: even if Route A is rejected, the synthesis layer's
"`art. <slug>`" template leak is independently a bug.

**Fix**: in `answer_synthesis_*` (likely
`answer_synthesis_helpers.py::format_article_citation` or wherever
`Art. {key}` is composed), detect non-numeric keys and render as the
chunk's `summary` or `title_hint` instead, without the `Art.` prefix.

**Risk**: scope creep — synthesis modules are deep and have many
callers. Less surgical than Route A.

### Route C (defer to phase 5) — fix the conciliacion_fiscal_P2
`no_router_topic` resolution

The `topic_router._classify_topic_with_llm` returned None for
`conciliacion_fiscal_P2`. That's a separate router-side bug (likely
prompt-side or keyword-coverage). Out of scope for fix_v3; track in
`fix_v4.md` if not naturally closed.

### Tackle order

1. **§3 Step 1**: read the synthesis citation-rendering site to confirm
   where `Art. <key>` is composed. ~10 min.
2. **§3 Step 2**: implement Route A (4-line change). Reversible.
3. **§3 Step 3**: smoke test with the 45-test backend curated set.
4. **§3 Step 4**: re-run §1.G panel, compare against the fix_v2
   anchor (29/36, run dir `20260429T192350Z_fix_v2_evidence_classifier_v3/`).
5. **§3 Step 5**: gate ≥32/36 with 0 ok→zero regressions. If not met,
   stack Route B; if still not met, refine-or-discard.

---

## 3. The implementation (numbered, copy-paste-ready)

### Step 1 — Read the synthesis citation site (~10 min)

```bash
grep -n "art\.\|Art\.\|article_key\|node_key" src/lia_graph/pipeline_d/answer_synthesis_helpers.py src/lia_graph/pipeline_d/answer_first_bubble.py src/lia_graph/pipeline_d/answer_inline_anchors.py src/lia_graph/pipeline_d/answer_synthesis_sections.py 2>&1 | head -40
```

Find every location that interpolates `article_key` into a citation
string. Note them; if Route A is enough, you don't need to touch any of
them, but the code-reading guarantees you'd recognize a regression.

### Step 2 — Implement Route A (the primary-promotion tightening)

`src/lia_graph/pipeline_d/retriever_supabase.py` — at the top of the
module add:

```python
_NUMERIC_ARTICLE_KEY_RE = re.compile(r"^\d+(?:-\d+)?$")
```

Then in `_classify_article_rows`, modify the signals_router_topic
computation:

```python
is_numeric_article = bool(_NUMERIC_ARTICLE_KEY_RE.match(article_key))
signals_router_topic = bool(router_topic) and is_numeric_article and (
    chunk_topic == router_topic
    or doc_topic == router_topic
    or (doc_topic != "" and doc_topic in compatible_doc_topics)
    or router_topic in article_topic_index.get(article_key, frozenset())
)
```

Explicit anchor classification stays unchanged (line 919:
`if is_explicit_anchor or signals_router_topic`). Explicit anchors with
non-numeric keys still pass — the planner is the source of truth there.

### Step 3 — Smoke test

```bash
PYTHONPATH=src:. uv run pytest tests/test_retriever_falkor.py tests/test_phase3_graph_planner_retrieval.py -q
```

Expected: 45 passed (same as fix_v2 baseline).

### Step 4 — Re-run §1.G panel

```bash
# Restart staging so the new code loads.
pkill -KILL -f "python.*lia_graph|node.*dev-launcher|npm.*dev:staging" 2>/dev/null; sleep 4
nohup npm run dev:staging </dev/null > /tmp/devstaging_v3.log 2>&1 &
disown
until curl -s -o /dev/null -w "%{http_code}" --max-time 2 http://127.0.0.1:8787/api/health 2>/dev/null | grep -q 200; do sleep 3; done
echo READY

RUN_DIR=evals/sme_validation_v1/runs/$(date -u +%Y%m%dT%H%M%SZ)_fix_v3_numeric_article_gate
mkdir -p "$RUN_DIR"
nohup bash -c "
PYTHONPATH=src:. uv run python scripts/eval/run_sme_parallel.py --run-dir '$RUN_DIR' --workers 4 --timeout-seconds 240 \
  && PYTHONPATH=src:. uv run python scripts/eval/run_sme_validation.py --classify-only '$RUN_DIR' \
  && echo 'PANEL_DONE'
" > /tmp/fix_v3_panel.log 2>&1 &
disown
echo "panel pid=$! run_dir=$RUN_DIR"

# Wait, then compare. ~5 min wall.
PYTHONPATH=src:. uv run python /tmp/compare_vs_22.py "$RUN_DIR"
```

Compare ALSO against the fix_v2 anchor:

```bash
# Adjust /tmp/compare_vs_22.py temporarily, OR write a one-liner:
PYTHONPATH=src:. uv run python - <<'PY'
import json
from pathlib import Path
A = Path("evals/sme_validation_v1/runs/20260429T192350Z_fix_v2_evidence_classifier_v3")
B = Path("evals/sme_validation_v1/runs/$RUN_DIR_BASENAME")
load = lambda p: {json.loads(l)["qid"]: json.loads(l)["class"] for l in (p / "classified.jsonl").open()}
a, b = load(A), load(B)
ACC = {"served_strong","served_acceptable"}
print(f"fix_v2 (29/36): {sum(1 for v in a.values() if v in ACC)}/36")
print(f"fix_v3 (new):  {sum(1 for v in b.values() if v in ACC)}/36")
print("DELTA:", sum(1 for q in a if b.get(q) in ACC) - sum(1 for q in a if a.get(q) in ACC))
print("REGRESSED:", [q for q in a if a.get(q) in ACC and b.get(q) not in ACC])
print("IMPROVED:", [q for q in a if a.get(q) not in ACC and b.get(q) in ACC])
PY
```

#### Success criteria (six-gate measurable criterion)

* `served_acceptable+ ≥ 32/36`
* `0 ok→zero regressions vs fix_v2 anchor (29/36)`
* `regimen_cambiario_P1`, `regimen_cambiario_P3`, and
  `regimen_sancionatorio_extemporaneidad_P2` flip from served_weak to
  acc+ (or at minimum, render answer >500 chars without `art. <slug>`
  template leaks).

#### Failure criteria

* Any of the 8 fix_v2-passing qids regress to non-acc+ → STOP, do
  not commit, write up which qid and why.
* Panel still <32/36 → stack Route B (synthesis citation rendering).

### Step 5 — Six-gate sign-off and commit

Same shape as fix_v2 §A.4. Document each of the 6 gates in the commit
message. Include run dirs and the per-qid delta vs fix_v2 anchor.

---

## 4. What you must NOT do

1. **Don't revert fix_v2.** The 5-signal classifier is the right
   semantic model. fix_v3 narrows it on key shape, doesn't undo it.
2. **Don't widen primary further.** No new signal (6) without an SME
   curation source.
3. **Don't lower the 32/36 gate.** Document exceptions per qid; never
   relax the threshold.
4. **Don't disable the v6 coherence gate.**
5. **Don't run the full pytest suite in one process** — `make test-batched`.
6. **Don't commit without re-running the panel.** Synthesis-layer
   regressions can hide behind unit-test green.
7. **Don't tackle Symptom B (off_topic) qids in this phase** — they're
   classifier-rule sensitivity issues, not synthesis bugs. Track in
   fix_v4.md.

---

## 5. Anchor runs to compare against

| Run | Date | Acc+ | Notes |
|---|---|---|---|
| pre-DeepSeek-flip baseline | 04-27 | 21/36 | gemini-flash |
| post-DeepSeek-flip regression | 04-29 | 8/36 | DeepSeek primary |
| post-phase-1 (provider revert) | 04-29 | 22/36 | fix_v1 close |
| post-H1 sub-query (DISCARDED) | 04-29 | 16/36 | reverted |
| **post-fix_v2 (current head)** | 04-29 | **29/36** | `20260429T192350Z_fix_v2_evidence_classifier_v3/` — **THIS is your anchor** |

---

## 6. State of the world at hand-off (2026-04-29 ~2:50 PM Bogotá)

* Latest commit on `main`: `5c266d6 fix_v2 phase 3 — generalize "primary
  evidence" definition (22 → 29/36)`. Pushed to `origin/main`.
* `config/llm_runtime.json` `provider_order` =
  `[gemini-flash, gemini-pro, deepseek-v4-flash, deepseek-v4-pro]`.
  UNCHANGED. Don't flip.
* All retrieval flags ON/enforce per launcher
  (`scripts/dev-launcher.mjs`).
* `_classify_article_rows` in `retriever_supabase.py` accepts 5
  structural signals. Modify the signal-eval to add the numeric-key
  guard.
* `_fetch_anchor_article_rows` extends rescue-config articles when no
  explicit anchors. Don't touch.
* Cloud Supabase + cloud Falkor in-sync; no migration drift.

---

## 7. After you ship phase 4

1. Update this file (`docs/re-engineer/fix/fix_v3.md`) to mark phase 4
   closed: panel result, run dir, route(s) used, residual gaps.
2. Update `fix_v2.md` §A to reference `fix_v3.md` as the next-phase
   pointer.
3. If §1.G holds ≥32/36 acc+ across at least one follow-up panel run a
   day or more later, fix_v2 itself can fully close.
4. Open `fix_v4.md` for the residual Symptom B qids
   (off_topic-classifier issues) AND for `conciliacion_fiscal_P2`'s
   `no_router_topic` router miss.

---

## 8. Minimum information you need from the operator (none)

This hand-off is fully self-contained. Don't ask the operator to
clarify unless:

* Step 4's panel regresses ANY of the 8 fix_v2-passing qids to
  non-acc+. Then STOP and write up which one + why.
* You discover the synthesis-layer bug is wider than the citation
  template (e.g. answer-mode `topic_safety_abstention` re-firing for
  fix_v2-passing qids). Then write up the new finding.

---

*Drafted 2026-04-29 ~2:50 PM Bogotá by claude-opus-4-7 immediately
after fix_v2 commit `5c266d6` landed. Trace evidence underlying §1's
verdicts is in
`evals/sme_validation_v1/runs/20260429T192350Z_fix_v2_evidence_classifier_v3/<qid>.json
.response.diagnostics.pipeline_trace.steps[*]`.*
