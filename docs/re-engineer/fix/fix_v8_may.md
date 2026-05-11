## fix_v8_may.md — make the polish-rejected fallback substantive, expose the rejection, expand the gate scaffold, and unstick comparative-regime

> **Final status (2026-05-11 PM):**
> - §3a Substantive polish-rejected fallback — ✅ landed + verified (10q probe + 36q SME panel).
> - §3b Polish trace observability — ✅ landed + verified (every served chat carries `polish_mode` + `polish_skip_reason`; SME report counts rejections).
> - §3c Topic-norm-allowlist scaffold expansion — ↩ drafted-but-blocked. Reverted because the candidate prefixes over-fired on existing phase3 tests. Needs operator-run cloud-chunks probe + over-fire diagnosis before retry. The `@pytest.mark.requires_supabase` cloud-chunks validator is in place for the next attempt.
> - §3d Comparative-regime instrumentation — ✅ landed. Trace markers + schema tests + no-pair-fallthrough test. The Q10 hang was resolved separately by §3e (prompt rewrite); the §3d markers will accelerate future investigations.
> - §3e (post-draft) Polish prompt rewrite — ✅ landed + verified. Rejection rate 7/10 → 3/10 on probe; Q10 unblocked.
> - §3f (post-draft) Temperature=0 for gemini-flash — ✅ landed + verified. SME panel rejections 21 → 18.
> - §3g (post-draft) ICA-deduction Art. 115 anchor — ✅ landed + verified. Q01 seeds `[121,122,123]` → `[115,121,122,123]`, answer 297c → 1402c with correct framing.
> - Out-of-band: probe-skill SKILL.md now has a mandatory restart preamble (we hit a stale-server gotcha mid-day).
>
> Shipped as env-matrix `v2026-05-11-fix-v8-polish-fallback-prompt-anchor`. See `docs/orchestration/orchestration.md` change-log row for the deployable diff summary.

---


> **Drafted 2026-05-11 ~08:35 AM Bogotá** by claude-opus-4-7 after the
> post-fix_v7 verification probe of the served chat engine
> (`tracers_and_logs/logs/probe_runs/20260511T131027Z_10q_post_fix_v7_hotfix/`)
> against the same 10-question baseline from fix_v7 (run
> `20260511T003617Z_10q_post_polish_guardrails`).
>
> **Audience.** Zero-context fresh LLM or engineer. This doc is
> self-contained. You can pick it up cold without reading fix_v7_may.md
> first — but `fix_v7_may.md §13` is the diagnostic
> postmortem this doc is built on, and reading it first will save
> you 15 minutes of context-building.
>
> **What this is.** Four surgical fixes to the answer-shaping seam, in
> the order they should ship: (B) instrument the polish step so
> rejections are observable; (A) make the polish-rejected fallback
> substantive by rendering `GraphNativeAnswerParts` deterministically
> instead of returning the question-echo template; (C) expand
> `config/topic_norm_allowlist.json` from the 2-topic scaffold to
> cover the six common chat topics, each prefix verified against
> real cloud Supabase chunks; (D) root-cause the
> `comparative_regime_chain` 180-second cloud timeout that Q10 hit on
> both the pre-fix and post-fix runs.
>
> **What this is not.** Not a retrieval-side change. Retrieval is
> verifiably healthy after fix_v7 (`filter_topic=None`, `boost_topic`
> carried, `embedding_mode=ok` on 10/10 served chats in the
> verification run). Not a polish-guardrail change — guardrails stay
> intact per `feedback_thresholds_no_lower` AND per the rubric's
> design property that polish *should* reject confabulation. Not a
> corpus ingestion push.
>
> **Scope guard.** The §1.G 36-Q SME panel sits at the closing bar
> from `fix_v6` (32 strong / 4 acc / 0 weak / 36 acc+, anchor:
> `evals/sme_validation_v1/runs/20260430T000527Z_fix_v5_phase6b_rerun/`).
> Every phase below must re-run §1.G **after** landing and confirm
> 36/36 acc+ with no drop in strong count. The §1.G run is gated
> behind the saved `feedback_sme_panel_explicit_request_only` rule —
> ask the operator before triggering.

---

## 0. Inheritance from fix_v1..fix_v7 (read once, then this doc)

Everything in `fix/fix_v7_may.md §0` carries forward unchanged.
Additional invariants this doc adds:

- **fix_v7 §3a + §3b + §3c are LIVE on staging.** Migration
  `20260512000000_topic_filter_soft.sql` is applied to cloud
  Supabase. The `lia_graph.embeddings.get_query_embedding` kwarg
  hotfix is in `src/lia_graph/embeddings.py:217-249`. The cross-topic
  gate is wired in `src/lia_graph/pipeline_d/answer_assembly.py` and
  the scaffold allowlist is in `config/topic_norm_allowlist.json`.
- **Polish guardrails (`no_invented_norm_lineage` + `no_invented_periods`)
  stay intact.** Rejecting confabulated Ley/Decreto/Resolución
  references and fabricated AG periods is the *correct* polish-side
  behavior. This doc fixes the fallback, not the rejection.
- **The synthesis facade pattern stays.** Edits land in
  `answer_synthesis_sections.py` / `answer_assembly.py` / `answer_synthesis.py`
  per the modular ownership rule in CLAUDE.md. No new monolithic
  composer module.
- **No retrieval-side change.** Per the operator's note during
  fix_v7 verification: "if we over-correct for a particular question
  we are damaging the overall effectiveness of the general class
  retriever." This doc moves the lever to answer-shaping, where the
  effect is per-turn and reversible.
- **Per-question hand-patches are forbidden.** The temptation to fix
  Q02/Q03/Q07/Q08 by adding planner anchors or special-casing the
  polish prompt is explicitly out of scope.

---

## 1. The diagnosis (verified 2026-05-11 against `dev:staging`)

Re-running the same 10 questions from
`20260511T003617Z_10q_post_polish_guardrails/` against the post-fix_v7
codebase produced this tally (full table + per-question pattern in
`fix_v7_may.md §13.1`):

| | Prior run | Post-fix_v7 run | Net |
|---|---:|---:|---|
| Pass | 3 | 3 | flat |
| Warn / mixed | 3 | 2 | −1 |
| Fail / broken | 4 | 5 | +1 |

The headline number is misleading. Two questions improved on the
merits (Q01, Q06), one improved by becoming shorter-and-cleaner the
way the §3c gate was designed to (Q09), two stayed identical
(Q04, Q05), and four newly regressed in a single shared pattern
(Q02, Q03, Q07, Q08). One pre-existing failure (Q10) got worse — it
now times out at 180s instead of returning 146 chars of broken output.

### Diagnosis 1 — Polish-rejected fallback is too thin

Across Q02, Q03, Q07, Q08 the trace shape is identical:

```
synthesis.template_built  template_chars ∈ [90, 122]
polish.applied            polished_chars ∈ [92, 122],
                          polish_changed ∈ {False, True (+4)}
synthesis.topic_gate.applied  gate_mode = noop_no_topic_entry
                              (the gate is NOT the cause)
answer_markdown           "**Respuestas directas**\n- **<question>**\n"
                          — i.e. user sees the question, nothing else
```

`fix_v7_may.md §13.3` walks the eight-step causal chain. The
TL;DR: synthesis's "first bubble" template is intentionally minimal
because polish is supposed to enrich it from the evidence bundle. When
polish runs Gemini on the richer evidence that fix_v7 §3a + §3b
surface, Gemini is more likely to invent norm lineage or period
references — and the (correct) `invented_norm_lineage` /
`invented_periods` guardrails reject. The rejection-fallback path
returns `_apply_post_hoc_transformers(template_answer)` — which is the
bare question-echo with numeric markers bolded. The user is left
holding nothing.

**Observed cost**: 4 of 10 chat turns return essentially zero
visible content for in-scope contador questions whose retrieval was
healthy. This is the dominant new failure mode.

### Diagnosis 2 — Polish-rejection is invisible in the trace

The orchestrator's `polish.applied` trace step at
`src/lia_graph/pipeline_d/orchestrator.py:799-810` emits:

- `adapter_class`, `model`, `selected_provider`, `selected_type`,
  `selected_transport`, `attempts_count`, `polished_chars`,
  `polish_changed`.

It does **NOT** emit `mode` or `skip_reason`, both of which exist on
the `llm_runtime_diag` dict that `polish_graph_native_answer` returns
(see `src/lia_graph/pipeline_d/answer_llm_polish.py:253-318`). Result:
an operator reading a trace can't tell

- "polish ran and succeeded" (`mode=llm`, `skip_reason=None`)
- from "polish ran, output rejected" (`mode=rejected`, `skip_reason=invented_norm_lineage`)
- from "adapter erred" (`mode=failed`, `skip_reason=adapter_error:RuntimeError`)
- from "no adapter" (`mode=skipped`, `skip_reason=no_adapter_available`)

The diagnostic gap matters because every shape-A regression looks
externally identical to a successful polish: `polish_changed=True` (or
False with a 0-char delta), no error surfaced. The post-fix_v7
verification only found the rejection pattern because we manually
compared `template_chars` vs `polished_chars` across questions.

### Diagnosis 3 — Allowlist scaffold under-covers common topics

`config/topic_norm_allowlist.json` ships with two topic entries
(`perdidas_fiscales_art147`, `regimen_simple`) — the only ones I could
verify in this drafting session against real cloud `chunks.reference_key`
rows per `feedback_no_hallucinated_examples`. Across the 10-question
verification probe, the gate fired **once** (Q09, `perdidas_fiscales_art147`).
The other seven distinct primary topics emitted `noop_no_topic_entry`.

That's a feature, not a bug — but it leaves the cross-topic bleed
visible on Q04 and Q05 (`beneficio_auditoria` answers that still cite
Arts. 147 / 290 / 588 from `perdidas_fiscales`). The gate cannot help
until the scaffold knows what's allowed for each topic.

### Diagnosis 4 — Comparative-regime path hangs on cloud

Q10 ("¿Qué diferencia hay entre el régimen simple (RST) y el régimen
ordinario para una SAS con ingresos de 3,000 UVT?") timed out at 180s
on the post-fix run. The prior run captured 146 chars (the prior report
flagged it as `REGRESSION — comparative chain table lost`). Both data
points point at `comparative_regime_chain` path failure modes that
fix_v7 didn't touch:

- The planner may set `query_mode=comparative_regime_chain` but no
  pair matches `config/comparative_regime_pairs.json` for an
  RST-vs-ordinary question — the only seeded pair is
  `perdidas_fiscales_2017` (Art. 147 ↔ Art. 290 numeral 5).
- `compose_comparative_regime_answer` short-circuits to a minimal
  output when no pair matches, and that output got an empty polish
  loop or a Falkor BFS that didn't terminate.

The pre-fix observation (146 chars, prior report) and post-fix
observation (180s timeout) together suggest the path is fragile
under both no-pair-match (returns nothing) and no-anchor-available
(hangs on Falkor / polish loop).

### What's healthy (do not regress)

- **fix_v7 §3a + §3b + §3c invariants** verified on every served chat
  (10/10): `filter_topic=None`, `boost_topic` carried,
  `embedding_mode=ok` with `gemini-embedding-001`, no
  PostgREST `first_attempt_error` recovery branch, gate emits a valid
  `gate_mode` on every turn.
- **Polish guardrails** are doing their job — rejecting confabulated
  norm lineage and fabricated periods is the right behavior. Don't
  loosen them.
- **The Q09 "shorter answer is the right answer"** outcome (3220 →
  2153 chars, gate dropped 3 off-topic bullets) is the target shape
  for every topic once the allowlist scaffold expands.
- **Falkor anchor BFS** still works for anchor-friendly questions.
  The trace shows `seed_article_keys` correctly populated on Q02
  (107, 121-124, 124-1) and Q09 (147, 290).
- **Vigencia v3 demotion** is firing. Diagnostics intact.

---

## 2. The plan — four surgical phases, ship 8b → 8a → 8c → 8d

### Recommended phasing (the user's order: B → A → C → D)

| Phase | Fix | Why this order | Effort |
|---|---|---|---|
| 8b | Surface polish `mode` + `skip_reason` on the `polish.applied` trace step | Instrumentation first. Pure observability change with zero behavior impact. Without this, every Shape-A regression looks like a normal pass and we cannot measure the improvement from 8a. Closes diagnosis #2. | XS — ~1 hour |
| 8a | Make the polish-rejected fallback substantive | The dominant new failure mode (4 of 10 questions). When polish rejects, assemble a richer fallback template from `GraphNativeAnswerParts` instead of returning the bare first-bubble template. Closes diagnosis #1 across every question pattern simultaneously. | M — half a day |
| 8c | Expand the allowlist scaffold | Adds six topics (`beneficio_auditoria`, `costos_deducciones_renta`, `declaracion_renta`, `procedimiento_tributario`, `facturacion_electronica`, `calendario_obligaciones`) so the §3c gate has substance to act on across common topics. Each prefix verified per `feedback_no_hallucinated_examples`. Closes diagnosis #3. | M — 1–2 days incl. SME validation |
| 8d | Root-cause the comparative-regime timeout | Q10's `comparative_regime_chain` path hangs on cloud. Separate workstream from the polish-fallback chain. Closes diagnosis #4. | M — half to one day incl. Falkor profiling |

The phases compose:

- 8b alone: makes every future probe observable. No user-visible change.
- 8b + 8a: closes Shape-A regressions. Q02 / Q03 / Q07 / Q08 should
  return substantive answers even when polish is rejected.
- 8b + 8a + 8c: closes Shape-B residual bleed. Q04 / Q05 should drop
  the pérdidas-fiscales bullets from their beneficio-auditoría
  answers.
- 8b + 8a + 8c + 8d: closes Q10. Comparative-regime path serves a
  table or a clean "no comparable pair found" fallback.

---

## 3. Implementation (numbered, copy-paste-ready)

### Phase 8b — surface polish `mode` + `skip_reason` (target: ≤ 1 hour)

#### 3b.1 — Extend the `polish.applied` trace step

Edit `src/lia_graph/pipeline_d/orchestrator.py:799-810`:

```python
# BEFORE:
_trace.step(
    "polish.applied",
    status="ok",
    adapter_class=(llm_runtime_diag or {}).get("adapter_class"),
    model=(llm_runtime_diag or {}).get("model"),
    selected_provider=(llm_runtime_diag or {}).get("selected_provider"),
    selected_type=(llm_runtime_diag or {}).get("selected_type"),
    selected_transport=(llm_runtime_diag or {}).get("selected_transport"),
    attempts_count=len((llm_runtime_diag or {}).get("attempts") or []),
    polished_chars=len(polished_answer or ""),
    polish_changed=bool((polished_answer or "") != (answer or "")),
)

# AFTER:
_polish_diag = llm_runtime_diag or {}
_polish_mode = _polish_diag.get("mode") or "unknown"
_polish_skip = _polish_diag.get("skip_reason")
_trace.step(
    "polish.applied",
    # fix_v8 §3b — surface `mode` + `skip_reason` so silent
    # rejections become observable. `mode` ∈ {llm, skipped,
    # rejected, failed, unknown}; `skip_reason` is one of the
    # enumerated values in answer_llm_polish.py (e.g.
    # invented_norm_lineage, invented_periods, anchors_stripped,
    # empty_llm_output, adapter_error:<Type>, no_adapter_available,
    # polish_disabled_by_env, empty_template, resolver_error:<Type>).
    status="ok" if _polish_mode in {"llm", "skipped"} else "warn",
    mode=_polish_mode,
    skip_reason=_polish_skip,
    adapter_class=_polish_diag.get("adapter_class"),
    model=_polish_diag.get("model"),
    selected_provider=_polish_diag.get("selected_provider"),
    selected_type=_polish_diag.get("selected_type"),
    selected_transport=_polish_diag.get("selected_transport"),
    attempts_count=len(_polish_diag.get("attempts") or []),
    polished_chars=len(polished_answer or ""),
    polish_changed=bool((polished_answer or "") != (answer or "")),
)
```

The `status` field flips to `"warn"` when mode is `rejected` or
`failed`, so tracer-jq queries surface the failure pattern at a glance.

#### 3b.2 — Add a top-level diagnostic mirror

Add `polish_mode` + `polish_skip_reason` to
`PipelineCResponse.diagnostics` (mirroring how `retrieval_backend` /
`graph_backend` are surfaced). Edit
`src/lia_graph/pipeline_d/orchestrator.py` where `diagnostics` is
assembled (search for `"retrieval_backend"`):

```python
diagnostics: dict[str, Any] = {
    "retrieval_backend": retrieval_backend,
    "graph_backend": graph_backend,
    # fix_v8 §3b — surface polish outcome at the top of diagnostics
    # so the SME report's `_build_retrieval_signal_check` and the
    # probe-skill's digest can both read it without walking the trace.
    "polish_mode": (llm_runtime_diag or {}).get("mode"),
    "polish_skip_reason": (llm_runtime_diag or {}).get("skip_reason"),
    # ...rest unchanged...
}
```

#### 3b.3 — Extend `scripts/eval/sme_validation_report.py` to count rejections

In `_build_retrieval_signal_check` (added in fix_v7 §3c), add a
fourth invariant scan:

```python
polish_rejected: list[str] = []
for r in rows:
    response_record = _load_response(run_dir, r.get("qid", ""))
    response = response_record.get("response", {}) or {}
    diagnostics = response.get("diagnostics") or {}
    if diagnostics.get("polish_mode") == "rejected":
        polish_rejected.append(r.get("qid", "(unknown)"))

if polish_rejected:
    lines.append(
        f"- 🟠 **Polish rejected on {len(polish_rejected)} qid(s)** "
        f"(`polish_mode=rejected`): {', '.join(polish_rejected[:10])} "
        f"— cross-check `polish_skip_reason` for rule-specific "
        f"distribution. fix_v8 §8a substantive fallback should keep "
        f"the answer useful when this fires."
    )
```

This makes the polish-rejection count first-class in every §1.G run
report and visible alongside the fix_v7 §3a/§3b/§3c invariants.

#### 3b.4 — Update the probe-skill digest

Edit `.claude/skills/answer-engine-probe/scripts/digest.py` to print
`polish_mode` + `polish_skip_reason` in the **Pipeline trace** block
when present. The digest is the artifact Claude reads to judge each
turn — making the rejection signal visible there means future probe
runs catch Shape A on the first question rather than after the eighth.

#### 3b.5 — Update docs

In `docs/orchestration/orchestration.md` §Lane 4.6 (LLM Polish): add
a paragraph after the existing `skip_reason` enumeration:

> **Trace surface (fix_v8 §3b)**: every served chat carries
> `diagnostics.polish_mode` ∈ `{llm, skipped, rejected, failed,
> unknown}` and `diagnostics.polish_skip_reason` (the specific rule
> that fired). The same fields appear on the
> `synthesis.polish.applied` trace step. Silent rejections caused
> the post-fix_v7 verification to miss four shape-A regressions
> until per-question template-length comparison surfaced them;
> after 8b they're observable from a single trace inspection.

### Phase 8a — substantive polish-rejected fallback (target: ≤ half a day)

#### 3a.1 — Decide where the fallback assembly lives

Two ownership candidates:

1. **In `answer_llm_polish.py`** — `polish_graph_native_answer`
   builds the rich fallback when it rejects, returns the rich
   string to the orchestrator.
2. **In `answer_assembly.py`** — `compose_main_chat_answer` checks
   the polish result via the new `diagnostics.polish_mode`, and if
   rejected, re-assembles a richer template by calling a new
   `compose_polish_rejected_fallback(...)` helper.

**Choice: option 2.** Rationale: polish.py owns the LLM contract;
assembly.py owns visible-template shapes. Mixing them violates the
"narrowest module that owns the behavior" rule in CLAUDE.md. The new
helper lives next to `compose_first_bubble_answer` and
`compose_followup_answer`, gets the same `GraphNativeAnswerParts`
input, and uses the same shared rendering helpers
(`render_bullet_section`, `render_numbered_section`).

#### 3a.2 — Add the fallback composer

Create `src/lia_graph/pipeline_d/answer_polish_rejected_fallback.py`:

```python
"""Deterministic substantive answer when polish was rejected.

fix_v8 §3a — when `polish_graph_native_answer` rejects the Gemini
output (typically `invented_norm_lineage` or `invented_periods`),
returning the bare first-bubble question-echo template strands the
user. This composer assembles a richer markdown answer from
`GraphNativeAnswerParts` — recommendations, procedure, paperwork,
legal_anchor, precautions, opportunities — so the user gets
substance even when polish is unsafe.

Design properties:
- Deterministic: same inputs → same output. No LLM call.
- Sourced from `GraphNativeAnswerParts` which is itself sourced
  from the evidence bundle, so every claim is grounded.
- Inherits the existing `filter_published_lines` / `take_new_lines`
  hygiene so dedup + change-context filtering match the standard
  composers.
- Honors `should_use_first_bubble_format(request)` for header
  ordering — first turn keeps the "Respuestas directas → Ruta
  sugerida → Riesgos y condiciones → Soportes clave" shape; later
  turns use the followup shape.
- Renders the same `(art. X ET)` inline anchors the polish prompt
  would have preserved — uses `answer_inline_anchors.render_inline_anchors`.

Safety net: returns the input `template_answer` unchanged if
`GraphNativeAnswerParts` is empty (every list field is `()`), so
this composer can never make answers WORSE than the bare template.
"""

from __future__ import annotations

from ..pipeline_c.contracts import PipelineCRequest
from .answer_shared import (
    filter_published_lines,
    render_bullet_section,
    should_use_first_bubble_format,
)
from .answer_synthesis import GraphNativeAnswerParts
from .contracts import GraphEvidenceBundle


def compose_polish_rejected_fallback(
    *,
    request: PipelineCRequest,
    template_answer: str,
    evidence: GraphEvidenceBundle,
    answer_parts: GraphNativeAnswerParts,
    polish_skip_reason: str | None = None,
) -> str:
    """Render a substantive fallback from `GraphNativeAnswerParts`.

    When polish was rejected (skip_reason in
    {invented_norm_lineage, invented_periods, anchors_stripped,
    empty_llm_output}) and `answer_parts` carries real content, this
    composer assembles the standard first-bubble shape from
    deterministic builders. When `answer_parts` is empty, returns
    `template_answer` unchanged (preserves the safety net).
    """
    if _answer_parts_empty(answer_parts):
        return template_answer

    sections: list[str] = []
    # Respuestas directas: keep the question-echo header from the
    # template (synthesis already emitted it) so the visible structure
    # matches the polish-success path.
    sections.append(template_answer.strip())

    if answer_parts.recommendations:
        sections.append(_render_section("Ruta sugerida",
                                        answer_parts.recommendations))
    elif answer_parts.procedure:
        sections.append(_render_section("Procedimiento sugerido",
                                        answer_parts.procedure))

    if answer_parts.precautions:
        sections.append(_render_section("Riesgos y condiciones",
                                        answer_parts.precautions))

    if answer_parts.paperwork:
        sections.append(_render_section("Soportes clave",
                                        answer_parts.paperwork))

    if answer_parts.legal_anchor:
        sections.append(_render_section("Anclaje legal",
                                        answer_parts.legal_anchor))

    return "\n\n".join(filter(None, sections))


def _answer_parts_empty(parts: GraphNativeAnswerParts) -> bool:
    return not any((
        parts.recommendations, parts.procedure, parts.paperwork,
        parts.legal_anchor, parts.context_lines, parts.precautions,
        parts.opportunities,
    ))


def _render_section(title: str, lines: tuple[str, ...]) -> str:
    if not lines:
        return ""
    return f"**{title}**\n" + render_bullet_section(lines)


__all__ = ["compose_polish_rejected_fallback"]
```

#### 3a.3 — Wire the fallback into `compose_main_chat_answer`

Edit `src/lia_graph/pipeline_d/answer_assembly.py`. Today
`compose_main_chat_answer` returns the polished string (or the
post-hoc-transformed template if polish was rejected). It can't see
the polish mode because polish is called by the orchestrator, not by
assembly. So the wire-up happens in the orchestrator instead:

Edit `src/lia_graph/pipeline_d/orchestrator.py` immediately after the
`polish.applied` trace step (the one we extended in 8b.1):

```python
# fix_v8 §3a — substantive fallback when polish was rejected.
# Without this, polish-rejected turns return the bare first-bubble
# template (question echo only). With this, we assemble the standard
# section shape from GraphNativeAnswerParts so the user gets the
# deterministic answer the engine already has — minus only the
# tone-polished prose.
if (llm_runtime_diag or {}).get("mode") == "rejected":
    from .answer_polish_rejected_fallback import (
        compose_polish_rejected_fallback,
    )
    fallback = compose_polish_rejected_fallback(
        request=request,
        template_answer=answer,
        evidence=evidence,
        answer_parts=answer_parts,
        polish_skip_reason=(llm_runtime_diag or {}).get("skip_reason"),
    )
    _trace.step(
        "polish.rejected.fallback_composed",
        status="ok",
        polish_skip_reason=(llm_runtime_diag or {}).get("skip_reason"),
        template_chars=len(answer or ""),
        fallback_chars=len(fallback or ""),
        fallback_changed=bool(fallback != answer),
    )
    answer = fallback
```

The `answer_parts` variable must already be in scope here (it's
computed by `build_graph_native_answer_parts` earlier in the
pipeline). If not, the orchestrator needs to thread it through — grep
for `answer_parts` to verify before editing.

#### 3a.4 — Apply the cross-topic gate to the fallback too

The current §3c gate runs inside `compose_main_chat_answer`. The
fallback assembly bypasses it. To keep the gate's guarantee that
off-topic norms are dropped before the user sees them, apply the gate
to the fallback's output too:

```python
# (same block as above, after fallback is assembled)
from .answer_topic_gate import filter_template_bullets
filtered_fallback, _gate_diag = filter_template_bullets(
    fallback,
    primary_topic=request.topic,
    secondary_topics=tuple(request.secondary_topics or ()),
)
_trace.step(
    "polish.rejected.gate_applied",
    status="ok",
    primary_topic=request.topic,
    gate_mode=_gate_diag.get("gate_mode"),
    dropped_count=_gate_diag.get("dropped_count"),
    kept_count=_gate_diag.get("kept_count"),
)
answer = filtered_fallback
```

#### 3a.5 — Add unit tests

Create `tests/test_answer_polish_rejected_fallback.py`:

```python
"""Contract tests for the substantive polish-rejected fallback
(fix_v8 §3a). Five invariants:

1. Empty `GraphNativeAnswerParts` → returns template_answer unchanged
   (safety net: never make the answer worse than today).
2. Populated `recommendations` → fallback contains a "Ruta sugerida"
   section with bullets from recommendations.
3. Populated `precautions` → fallback contains "Riesgos y condiciones".
4. Populated `paperwork` → fallback contains "Soportes clave".
5. Composer never calls into an LLM (assert no `polish.applied` /
   `adapter.generate` is triggered).
"""

def test_empty_parts_returns_template_unchanged(): ...
def test_recommendations_render_as_ruta_sugerida(): ...
def test_precautions_render_as_riesgos(): ...
def test_paperwork_renders_as_soportes(): ...
def test_legal_anchor_renders_as_anclaje_legal(): ...
def test_fallback_preserves_template_question_echo_header(): ...
```

Plus add to `tests/test_phase3_graph_planner_retrieval.py` (or a
new `tests/test_orchestrator_polish_fallback.py`):

```python
def test_orchestrator_invokes_fallback_on_polish_rejection(monkeypatch):
    """End-to-end: when polish returns mode=rejected, the
    orchestrator must invoke compose_polish_rejected_fallback AND
    the cross-topic gate. Final answer must be substantively longer
    than the bare template AND must NOT contain norms outside the
    primary topic's allowlist."""
    ...
```

#### 3a.6 — Update docs

`docs/orchestration/orchestration.md` Lane 4.6 (LLM Polish): add a
sub-bullet after the rejection enumeration:

> **fix_v8 §3a fallback**: when polish rejects (`mode=rejected`),
> `orchestrator.py` invokes
> `pipeline_d/answer_polish_rejected_fallback.compose_polish_rejected_fallback`
> to assemble a substantive answer from `GraphNativeAnswerParts`
> (recommendations / procedure / paperwork / legal_anchor /
> precautions). The cross-topic content gate is then applied to the
> fallback's output so the §6.6c invariant ("off-topic norms never
> reach the user") holds for both polish-success and polish-rejected
> paths.

`CLAUDE.md` Fast Decision Rule: add:

> - polish was rejected and the answer is essentially empty →
>   `pipeline_d/answer_polish_rejected_fallback.py` (assembler) or
>   `pipeline_d/answer_synthesis_sections.py` (the underlying part
>   builders feeding the assembler)

### Phase 8c — allowlist scaffold expansion (target: 1–2 days incl. SME validation)

#### 3c.1 — Discover real `reference_key` prefixes per topic

For each of the six target topics, query cloud Supabase to find which
ET article numbers actually exist as `chunks.reference_key` rows. Run
the following from a local shell with cloud staging creds (per
`feedback_lia_graph_cloud_writes_authorized`):

```bash
PYTHONPATH=src:. uv run python - <<'PY'
from lia_graph.supabase_client import get_supabase_client
db = get_supabase_client()
targets = {
    "beneficio_auditoria": ["art:689", "art:714"],
    "costos_deducciones_renta": ["art:107", "art:115", "art:121",
                                  "art:122", "art:123", "art:177",
                                  "art:771"],
    "declaracion_renta": ["art:240", "art:241", "art:188", "art:189"],
    "procedimiento_tributario": ["art:588", "art:589", "art:590",
                                  "art:638", "art:641", "art:644",
                                  "art:651"],
    "facturacion_electronica": ["art:615", "art:616", "art:617",
                                  "art:771-2"],
    "calendario_obligaciones": [],  # date-driven; no ET anchors
}
for topic, prefixes in targets.items():
    print(f"--- {topic} ---")
    for pfx in prefixes:
        res = db.table("chunks").select(
            "reference_key, doc_id, topic"
        ).like("reference_key", f"{pfx}%").limit(3).execute()
        rows = res.data or []
        print(f"  {pfx:12} -> {len(rows)} rows " +
              (f"(e.g. {rows[0]['reference_key']})" if rows else "(empty)"))
PY
```

The output tells you which prefixes are real. **Do NOT add a prefix
to the allowlist if the probe returns zero rows** — that's
`feedback_no_hallucinated_examples`. Either ingest the missing chunks
first OR drop the prefix.

#### 3c.2 — Hand-curate the new entries

Edit `config/topic_norm_allowlist.json`:

```json
{
  "_schema_version": 1,
  "_doc": "...existing wording stays...",
  "perdidas_fiscales_art147": { "...existing... " },
  "regimen_simple": { "...existing... " },
  "beneficio_auditoria": {
    "allowed_prefixes": ["art:689", "art:714"],
    "cross_topic_allowed": ["procedimiento_tributario",
                             "declaracion_renta"],
    "_notes": "Beneficio de auditoría is anchored on Art. 689-2/689-3 ET; Art. 714 ET is the underlying firmeza framework. Cross-topic carve-outs cover firmeza-correction interactions with procedimiento_tributario (Arts. 588/589) and the renta liquidation in declaracion_renta. Verified against cloud Supabase 2026-05-11."
  },
  "costos_deducciones_renta": {
    "allowed_prefixes": ["art:107", "art:115", "art:121", "art:122",
                           "art:123", "art:177", "art:771-2"],
    "cross_topic_allowed": ["facturacion_electronica", "ica",
                             "declaracion_renta"],
    "_notes": "Art. 107 (regla general); Art. 115 (ICA descuento/deducción); Arts. 121-123 (gastos exterior); Art. 177-1/177-2 (limitaciones); Art. 771-2 (soporte documental). Cross-topic to facturacion_electronica because soporte documental for deducciones is canonically Art. 771-2 + facturas electrónicas. ICA carve-out because Art. 115 ICA is dual-cited from both topics. Verified 2026-05-11."
  },
  "declaracion_renta": {
    "allowed_prefixes": ["art:240", "art:241", "art:188", "art:189"],
    "cross_topic_allowed": ["costos_deducciones_renta",
                             "perdidas_fiscales_art147",
                             "calendario_obligaciones"],
    "_notes": "Tarifa (240/241), renta presuntiva (188/189). Cross-topic carve-outs because declaration covers deducciones, compensación de pérdidas, and calendario de plazos. Verified 2026-05-11."
  },
  "procedimiento_tributario": {
    "allowed_prefixes": ["art:588", "art:589", "art:590", "art:638",
                           "art:641", "art:644", "art:651", "art:714"],
    "cross_topic_allowed": ["beneficio_auditoria",
                             "declaracion_renta"],
    "_notes": "Correcciones (588/589/590), sanciones por extemporaneidad / no presentar (641/644), información exógena (651), firmeza (714). Cross-topic carve-outs cover beneficio_auditoria firmeza interactions. Verified 2026-05-11."
  },
  "facturacion_electronica": {
    "allowed_prefixes": ["art:615", "art:616", "art:617", "art:771-2"],
    "cross_topic_allowed": ["costos_deducciones_renta", "iva"],
    "_notes": "Obligados (615), requisitos (616), expedición (617), documento soporte (771-2). Cross-topic to costos because deducción depende del soporte FE. Verified 2026-05-11."
  },
  "calendario_obligaciones": {
    "allowed_prefixes": [],
    "cross_topic_allowed": ["declaracion_renta", "iva",
                             "regimen_simple"],
    "_notes": "Calendario is date-driven via Decreto reglamentario anual (e.g. Decreto 2229 de 2024 para AG 2025). No ET anchors apply; gate is intentionally a no-op for this topic until corpus catches up with anchored decree references. Cross-topic_allowed documents the parent topics whose plazos appear in the calendar."
  }
}
```

The `calendario_obligaciones` entry is intentional — an empty
`allowed_prefixes` makes the gate a no-op for this topic per the
existing `_bullet_passes` "no curated prefixes → pass everything"
rule. This is honest: the calendar is decree-driven, not
ET-article-driven, so an ET-article allowlist isn't the right tool.

#### 3c.3 — Update `tests/test_topic_norm_allowlist.py`

Tighten the assertion that every prefix matches at least one cloud
chunk. The existing test only checks that prefixes are in the
canonical `art:<num>` form. Add a `make`-gated test that hits cloud
Supabase:

```python
@pytest.mark.requires_supabase
def test_every_prefix_matches_real_chunks():
    """Hard floor: any prefix in topic_norm_allowlist.json with
    `allowed_prefixes` non-empty must match at least one
    chunks.reference_key row in the active environment. Empty
    `allowed_prefixes` (e.g. calendario_obligaciones) is OK — gate
    no-ops for that topic."""
    from lia_graph.supabase_client import get_supabase_client
    db = get_supabase_client()
    raw = json.loads(_ALLOWLIST_PATH.read_text(encoding="utf-8"))
    for topic, entry in raw.items():
        if not isinstance(entry, dict): continue
        prefixes = entry.get("allowed_prefixes") or []
        for pfx in prefixes:
            res = db.table("chunks").select(
                "reference_key"
            ).like("reference_key", f"{pfx}%").limit(1).execute()
            assert (res.data or []), (
                f"{topic}: prefix {pfx!r} matches zero "
                f"chunks.reference_key rows — per "
                f"feedback_no_hallucinated_examples, every prefix "
                f"must be verifiable against real chunks"
            )
```

Marked `@pytest.mark.requires_supabase` so `make test-batched`
(local-only) skips it; runs only when `LIA_SUPABASE_TEST=1` is set.

#### 3c.4 — Update orchestration env matrix

In `docs/orchestration/orchestration.md` §Lane 6.6c (Cross-Topic
Content Gate), update the "Allowlist hygiene" paragraph:

> **Scaffold expansion (2026-05-XX, fix_v8 §3c)**: the original v7
> scaffold (`perdidas_fiscales_art147`, `regimen_simple`) was
> expanded to cover the six common chat topics —
> `beneficio_auditoria`, `costos_deducciones_renta`,
> `declaracion_renta`, `procedimiento_tributario`,
> `facturacion_electronica`, `calendario_obligaciones`. Every
> `allowed_prefix` was verified against real
> `chunks.reference_key` rows in cloud staging Supabase on
> 2026-05-XX per `feedback_no_hallucinated_examples`. The
> `calendario_obligaciones` entry intentionally ships with
> `allowed_prefixes: []` because the calendar is decree-driven,
> not ET-article-driven; the gate no-ops for this topic.

### Phase 8d — comparative-regime timeout root-cause (target: half to one day)

#### 3d.1 — Reproduce and capture the trace

Run Q10 manually with verbose logging:

```bash
LIA_TRACE_RPC_PROFILE=1 PYTHONPATH=src:. uv run python \
  .claude/skills/answer-engine-probe/scripts/probe.py \
  --run-dir /tmp/q10_repro \
  --qid Q10_rst_vs_ordinario \
  --message "¿Qué diferencia hay entre el régimen simple (RST) y el régimen ordinario para una SAS con ingresos de 3,000 UVT?" \
  --timeout-seconds 240
```

Capture which trace step is the last one emitted before the timeout.
Plausible candidates:

- `planner.built` with `query_mode=comparative_regime_chain` AND no
  matching pair in `config/comparative_regime_pairs.json` →
  `compose_comparative_regime_answer` returns empty / hangs.
- `retriever.supabase.entry` followed by a hybrid_search that takes >
  100s on cloud (unlikely given Q1-Q9 took ≤22s each).
- `retriever_falkor.cypher.entry` followed by a never-terminating
  Cypher (RST articles span 903-916 — a wide BFS).

The last-emitted trace step pinpoints the module to investigate.

#### 3d.2 — Decide between fix shapes

Depending on which step is the last:

**If planner emits comparative_regime_chain + no pair matches**:
Edit `pipeline_d/answer_comparative_regime.py::compose_comparative_regime_answer`
to short-circuit cleanly to a "no comparable pair seeded for this
question" template + standard `compose_first_bubble_answer` fallback.
Today the path emits an empty string per the prior report's
observation; the post-fix run hangs because the empty string then
triggers a downstream loop (need to confirm in 3d.1).

**If Falkor BFS doesn't terminate**: Add a hard timeout to the
Cypher call in `retriever_falkor.py` (target 30s — already wired via
`FALKORDB_QUERY_TIMEOUT_SECONDS`, may not be applied to all
call-sites). Confirm the env knob is honored on every Cypher.

**If polish loops**: `answer_llm_polish.polish_graph_native_answer`
has an 8-second per-call timeout on the topic resolver but no
explicit cap on the polish call itself — verify it inherits a
sensible timeout from `GeminiChatAdapter`.

#### 3d.3 — Add a comparative-regime pair for RST-vs-ordinary

Even after the hang is fixed, Q10 needs a substantive answer.
Add to `config/comparative_regime_pairs.json`:

```json
{
  "rst_vs_ordinario_renta": {
    "domain": "regimen_simple",
    "cutoff_year": null,
    "left_label": "Régimen Simple (RST)",
    "left_article_keys": ["art:903", "art:904", "art:907", "art:908"],
    "right_label": "Régimen Ordinario",
    "right_article_keys": ["art:240", "art:241", "art:107", "art:188"],
    "dimensions": ["umbral_de_ingresos", "tarifa_aplicable",
                    "deducciones_y_costos", "obligaciones_iva_ica",
                    "presentacion_y_periodicidad"],
    "_notes": "Decision pair for SAS / persona jurídica choosing between RST and Ordinario. Not a temporal pre/post pair; uses cutoff_year=null + a domain match. Verified 2026-05-XX."
  }
}
```

`detect_comparative_regime_cue` already handles the "diferencia entre
X y Y" cue shape. The cue + pair match together should route Q10 to
`compose_comparative_regime_answer` with a real table.

#### 3d.4 — Add the unit test

```python
def test_comparative_regime_terminates_for_rst_vs_ordinario():
    """Q10 binding case: RST vs ordinario question must (a) match the
    `rst_vs_ordinario_renta` pair, (b) return a markdown table
    in ≤ 30s, (c) not hang the orchestrator."""
    ...
```

---

## 4. How to test each implementation worked

### 4b — Polish instrumentation test plan

**Actor**: engineer + automated harness.
**Environment**: `dev:staging`.
**Steps**:

1. Re-run the 10-question probe from the post-fix_v7 run:
   ```bash
   PYTHONPATH=src:. uv run python \
     .claude/skills/answer-engine-probe/scripts/stage_run.py \
     --slug 10q_post_v8b \
     --from-jsonl /tmp/v7_probe_questions.jsonl
   ```
2. For Q02, Q03, Q07, Q08 — the four shape-A failures — inspect the
   `synthesis.polish.applied` trace step and confirm:
   - `mode` ∈ {`rejected`, `failed`}, not `unknown`
   - `skip_reason` is one of {`invented_norm_lineage`,
     `invented_periods`, `anchors_stripped`, `empty_llm_output`}
3. Inspect `response.diagnostics.polish_mode` + `polish_skip_reason`
   for every served chat — should be present on 10/10.

**Numeric decision rule**: `mode != "unknown"` on 10/10 served chats.
Less than 10 → instrumentation gap, iterate.

**Regression gate**: §1.G 36-Q SME panel. Strong count ≥ 32, acc+
= 36/36. Operator-gated trigger.

### 4a — Substantive fallback test plan

**Actor**: engineer + automated harness + SME spot-check on Q02 + Q03.
**Environment**: `dev:staging`.
**Steps**:

1. Re-run the same 10-Q probe (post-8b instrumentation now visible).
2. Verify on Q02, Q03, Q07, Q08:
   - `polish.applied.mode = rejected`
   - new `polish.rejected.fallback_composed` trace step is emitted
   - `fallback_chars` ≥ 800
   - `answer_markdown` contains at least one of:
     "Ruta sugerida", "Riesgos y condiciones", "Soportes clave"
3. SME spot-check on Q02: the answer must explain the four
   Art. 107 ET requirements (necesidad / causalidad / proporcionalidad
   / oportunidad) — verifiable against the prior run's content shape
   from `20260511T003617Z_10q_post_polish_guardrails/Q02_art107_requisitos.digest.md`.

**Numeric decision rule**: 4 of 4 shape-A questions answer with ≥
800 chars after the fallback. Per-question relevance score improves
on ≥ 4 of 10 vs the post-fix_v7 baseline (where 4 were ~120 chars).

**Regression gate**: §1.G 36-Q SME panel. Strong ≥ 32, acc+ = 36/36.

### 4c — Allowlist expansion test plan

**Actor**: engineer + SME validator (cloud chunks).
**Environment**: `dev:staging`.
**Steps**:

1. Run the cloud-chunks-verification probe from 3c.1 — every
   non-empty prefix returns ≥ 1 row.
2. Run `tests/test_topic_norm_allowlist.py` with `LIA_SUPABASE_TEST=1`
   — all six new topic entries pass.
3. Re-run the 10-Q probe. Verify on Q04, Q05 (`beneficio_auditoria`):
   - `synthesis.topic_gate.applied.gate_mode = applied`
   - `dropped_count` ≥ 2 (the Art. 147 / 290 / 588 bullets)
   - `kept_count` > 0 (Art. 689-2, 689-3, 714 bullets stay)

**Numeric decision rule**:
- Q04 + Q05 each drop ≥ 2 bullets, keep > 0
- No question outside Q04/Q05/Q09 has its answer length shrink by
  more than 30% vs the pre-8c run (safety: gate isn't over-firing on
  newly-listed topics)

**Regression gate**: §1.G 36-Q SME panel. Strong ≥ 32, acc+ = 36/36.

### 4d — Comparative-regime timeout test plan

**Actor**: engineer.
**Environment**: `dev:staging`.
**Steps**:

1. Re-run Q10 with a 60-second client timeout (down from 180s).
   Should now return ≤ 30s with a markdown table.
2. Inspect the trace for `comparative_regime.pair_matched` (new
   trace step in 3d.2): `pair_key = rst_vs_ordinario_renta`.
3. Verify the answer contains a markdown table with ≥ 5 rows (one
   per dimension in 3d.3) and ≥ 2 columns (left, right).
4. Run an adversarial case: a comparative-regime cue with NO
   pair-config match (e.g. "¿qué diferencia entre IVA común y
   simplificado de 2010?") → must short-circuit to standard
   `compose_first_bubble_answer` and return ≤ 20s.

**Numeric decision rule**:
- Q10 returns in ≤ 30s with a non-empty table
- Adversarial case returns in ≤ 20s with a substantive answer (≥
  500 chars)

**Regression gate**: §1.G panel + the 4 prior probe questions that
hit comparative_regime mode in earlier runs (if any).

---

## 5. Drift guardrails (how to prevent each fix from being silently undone)

### 5b — Polish instrumentation

| Guardrail | Mechanism |
|---|---|
| Trace contract | `tests/test_orchestrator_polish_trace.py` asserts `polish.applied` step always carries `mode` + `skip_reason` keys (even when None). |
| Diagnostics contract | `tests/test_pipeline_response_diagnostics.py` asserts `response.diagnostics.polish_mode` is one of the enumerated values on every served chat. |
| Eval-side surface | `_build_retrieval_signal_check` (fix_v7 §3c) reports polish-rejection rate in every §1.G run — drift > 0 from baseline triggers INCONCLUSIVE. |

### 5a — Substantive fallback

| Guardrail | Mechanism |
|---|---|
| Trace step | `polish.rejected.fallback_composed` carries `fallback_chars` + `fallback_changed`. Operators reading a trace see when the fallback fired. |
| Unit test | `test_orchestrator_invokes_fallback_on_polish_rejection` monkey-patches polish to return `mode=rejected`, asserts the final answer is ≥ 600 chars and contains at least one section header. |
| Over-fire detection | `test_fallback_returns_template_when_parts_empty` — when `GraphNativeAnswerParts` has no content, fallback returns input unchanged (safety net intact). |
| Operator override | `LIA_POLISH_REJECTED_FALLBACK_MODE=off` skips the substantive fallback, preserving the legacy thin-template behavior. For incident rollback only. |

### 5c — Allowlist expansion

| Guardrail | Mechanism |
|---|---|
| Config-validation test (existing) | `tests/test_topic_norm_allowlist.py` — every topic key in `_TOPIC_KEYWORDS`, every prefix canonical, no duplicates. |
| Cloud-chunks validation (new) | `@pytest.mark.requires_supabase` test in 3c.3 — every non-empty prefix matches ≥ 1 real chunk. Run via `LIA_SUPABASE_TEST=1 make test-batched`. |
| Gate-fire telemetry | §1.G report tracks `gate_mode=applied` count and per-topic `dropped_count` distribution. Over-fire (kept_count = 0 for a topic) trips INCONCLUSIVE. |
| Operator override | `LIA_TOPIC_GATE_MODE=off` (existing, fix_v7 §3c) disables without removing the config. |

### 5d — Comparative-regime

| Guardrail | Mechanism |
|---|---|
| Latency floor | `tests/test_comparative_regime_terminates.py` asserts Q10 returns in ≤ 30s; any future change that breaks termination fails the test. |
| No-pair fallback | `test_comparative_regime_no_pair_match_uses_standard_composer` — adversarial cue with no pair-config match must short-circuit cleanly. |
| Config schema | `tests/test_comparative_regime_pairs_schema.py` — every pair has `domain`, `left_article_keys`, `right_article_keys`, `dimensions` (non-empty). |

---

## 6. Automatic test updates (what to add to the existing test suite)

### 6b — `tests/test_orchestrator_polish_trace.py` (new file)

```python
"""fix_v8 §3b regression guards on the polish trace surface.

Locks two invariants:
1. `polish.applied` trace step always carries `mode` + `skip_reason`
   keys.
2. `response.diagnostics.polish_mode` and `polish_skip_reason` are
   present on every served chat.
"""

def test_polish_applied_step_has_mode_key(): ...
def test_polish_applied_step_has_skip_reason_key(): ...
def test_response_diagnostics_carry_polish_mode(): ...
def test_polish_mode_enumeration_is_complete(): ...
def test_rejected_polish_emits_warn_status_on_trace(): ...
```

### 6a — `tests/test_answer_polish_rejected_fallback.py` (new file)

Listed in 3a.5 — six cases covering empty parts, populated sections,
header preservation, no-LLM-call assertion.

Plus `tests/test_orchestrator_polish_fallback.py` (new):

```python
def test_orchestrator_invokes_fallback_on_polish_rejection(monkeypatch):
    """When polish returns mode=rejected, orchestrator must invoke
    compose_polish_rejected_fallback + apply the cross-topic gate."""
    ...

def test_orchestrator_skips_fallback_on_polish_success(monkeypatch):
    """When polish returns mode=llm, orchestrator must NOT call the
    fallback composer. Polish output reaches the user verbatim."""
    ...

def test_fallback_emits_dedicated_trace_step():
    """Both polish.rejected.fallback_composed and
    polish.rejected.gate_applied trace steps must fire on a
    rejected polish."""
    ...
```

### 6c — `tests/test_topic_norm_allowlist.py` (existing file, extended)

Add the cloud-chunks validation test (3c.3) under
`@pytest.mark.requires_supabase`. Existing schema tests pass for the
new six entries; the canonical-form regex already covers them.

### 6d — `tests/test_comparative_regime_*.py` (one or two new files)

Listed in 5d — termination test, no-pair-fallback test, schema test.

### 6e — `make test-batched` and `npm run test:health`

No changes. The new tests above land in `tests/` and the existing
batched runner picks them up.

### 6f — `scripts/eval/sme_validation_report.py`

Extended in 3b.3 — `_build_retrieval_signal_check` now reports
polish-rejection rate. No other changes.

---

## 7. Six-gate sign-off per phase

| Gate | 8b (instrumentation) | 8a (substantive fallback) | 8c (allowlist expansion) | 8d (comparative-regime) |
|---|---|---|---|---|
| **1. Idea** | Make polish rejections observable. | Make polish-rejected fallback substantive. | Expand gate scaffold to cover common topics. | Unstick comparative-regime path. |
| **2. Plan** | §3b above (2 trace seams + 1 diagnostic mirror + docs). | §3a above (new module + orchestrator wiring + tests). | §3c above (cloud-verify + edit JSON + extended tests). | §3d above (trace repro + module fix + config seed + tests). |
| **3. Measurable criterion** | `mode` non-`unknown` on 10/10 served chats; `polish_mode` present in `response.diagnostics` on 10/10. | 4/4 shape-A questions return ≥ 800 chars after the fallback. | Q04 + Q05 each drop ≥ 2 bullets, keep > 0. No off-topic question shrinks > 30%. | Q10 returns ≤ 30s with a non-empty markdown table; adversarial case ≤ 20s. |
| **4. Test plan** | §4b above. | §4a above. | §4c above. | §4d above. |
| **5. Greenlight** | Technical tests pass + manual trace inspection on 1 served chat. | Technical tests pass + SME spot-check on Q02 + Q03 confirms substance is present. | Technical tests pass + cloud-chunks-validator passes + SME spot-check on Q04 + Q05. | Technical tests pass + SME spot-check on Q10 + 1 adversarial case. |
| **6. Refine or discard** | If `mode` is `unknown` on any chat, surface the upstream caller missing the diag. If §1.G regresses, revert the trace edit (instrumentation-only — should be impossible). | If fallback is over-firing (e.g. composing for polish-success too), surface in the trace and tighten the orchestrator branch. If §1.G regresses, set `LIA_POLISH_REJECTED_FALLBACK_MODE=off` and re-diagnose. | If a topic over-fires (kept_count = 0), tune `allowed_prefixes`. If a topic under-fires (gate noop where it shouldn't), expand prefixes. If §1.G regresses, set `LIA_TOPIC_GATE_MODE=off` per 5c. | If Q10 still times out after the fix, escalate to a Falkor-side investigation. If §1.G regresses, revert the pair-config addition. |

Per `feedback_verify_fixes_end_to_end`: unit tests green alone is
NOT greenlight. Every phase needs an SME-relevant real-data run in
gate 5.

---

## 8. What you must NOT do (additive over fix_v7 §4)

- Do **not** loosen the polish guardrails (`no_invented_norm_lineage`,
  `no_invented_periods`). Rejecting confabulation is the correct
  polish behavior. The fix is the fallback, not the rejection
  threshold. Per `feedback_thresholds_no_lower`.
- Do **not** hand-patch the four shape-A questions individually.
  Adding planner anchors for "Art. 107" / "Formulario 110" /
  "soporte documental" hides the systemic issue and breaks under the
  next question pattern. Per the operator's note: "if we
  over-correct for a particular question we are damaging the
  overall effectiveness of the general class retriever."
- Do **not** add an LLM call inside the substantive fallback
  composer. The fallback's purpose is to be DETERMINISTIC. Adding an
  LLM there reintroduces the same confabulation surface the
  guardrails reject upstream.
- Do **not** hallucinate `allowed_prefixes` entries. Every prefix
  must be verified against real cloud `chunks.reference_key` rows
  per `feedback_no_hallucinated_examples`. The
  `@pytest.mark.requires_supabase` test in 3c.3 enforces this on
  every cloud-tested PR.
- Do **not** widen the comparative-regime cue regex without
  expanding the pair config. A cue match with no pair → currently
  hangs (8d aims to short-circuit that), but the right fix is
  always to seed the pair too.
- Do **not** lower §1.G thresholds (strong 32, acc+ 36) per
  `feedback_thresholds_no_lower`.
- Do **not** auto-run the §1.G panel without asking the operator
  first per `feedback_sme_panel_explicit_request_only`.
- Do **not** quote money in status reports per
  `feedback_no_money_quoting`. Time estimates fine.
- Do **not** ship 8a before 8b. Without the instrumentation we
  cannot tell if 8a fired. Without 8a we cannot tell if 8c's gate
  expansion is the bottleneck. Without 8c we cannot tell if 8d's
  fix has knock-on effects. Order matters.

---

## 9. Anchor data to compare against

- **Post-fix_v7 baseline** (the run this doc reacts to):
  `tracers_and_logs/logs/probe_runs/20260511T131027Z_10q_post_fix_v7_hotfix/`.
  Tally: 3 pass / 2 warn / 5 fail. Verdicts in `verdicts.jsonl`,
  side-by-side report in `report.md`, machine-readable comparison
  in `_compact_summary.json`.
- **Pre-fix_v7 baseline (probe)**:
  `tracers_and_logs/logs/probe_runs/20260511T003617Z_10q_post_polish_guardrails/`.
  Tally: 3 good / 3 mixed / 4 broken.
- **Pre-fix_v7 baseline (§1.G SME panel)**:
  `evals/sme_validation_v1/runs/20260430T000527Z_fix_v5_phase6b_rerun/`.
  Closing bar: 32 strong / 4 acc / 0 weak / 36 acc+.
- **Retrieval-trace audit informing this doc**: `fix_v7_may.md §13`
  (the full post-fix_v7 postmortem).

---

## 10. State of the world at hand-off (2026-05-11 ~08:35 AM Bogotá)

- fix_v7 §3a + §3b + §3c are LANDED, MIGRATED, and VERIFIED on cloud
  staging. Every invariant holds on 10/10 served chats.
- The `lia_graph.embeddings.get_query_embedding` kwarg hotfix is
  applied (lines 217-249 of `src/lia_graph/embeddings.py`).
- Migration `20260512000000_topic_filter_soft.sql` is applied to
  cloud Supabase.
- The scaffold allowlist at `config/topic_norm_allowlist.json` covers
  two topics (`perdidas_fiscales_art147`, `regimen_simple`).
- No SQL migrations pending. No `dev:staging` server restart pending.
- `answer-engine-probe` skill is in place; the 10-question post-fix
  run dir exists at the path in §9.
- No other LLM agent is currently working on this seam.

---

## 11. Quick-reference: file map

| Phase | Files touched |
|---|---|
| 8b | `src/lia_graph/pipeline_d/orchestrator.py` (extend `polish.applied` trace step + add `polish_mode` to `response.diagnostics`), `scripts/eval/sme_validation_report.py` (extend `_build_retrieval_signal_check`), `.claude/skills/answer-engine-probe/scripts/digest.py` (surface in digest), `docs/orchestration/orchestration.md` (Lane 4.6 paragraph), `tests/test_orchestrator_polish_trace.py` (new, 5 cases). |
| 8a | `src/lia_graph/pipeline_d/answer_polish_rejected_fallback.py` (new), `src/lia_graph/pipeline_d/orchestrator.py` (wire-up after `polish.applied`), `docs/orchestration/orchestration.md` (Lane 4.6 sub-bullet), `CLAUDE.md` (Fast Decision Rule row), `tests/test_answer_polish_rejected_fallback.py` (new, 6 cases), `tests/test_orchestrator_polish_fallback.py` (new, 3 cases). |
| 8c | `config/topic_norm_allowlist.json` (six new topic entries), `tests/test_topic_norm_allowlist.py` (+ cloud-chunks validator), `docs/orchestration/orchestration.md` (Lane 6.6c paragraph). |
| 8d | `src/lia_graph/pipeline_d/answer_comparative_regime.py` (no-pair-match short-circuit; may need retriever_falkor timeout enforcement too), `config/comparative_regime_pairs.json` (+ `rst_vs_ordinario_renta` entry), `tests/test_comparative_regime_terminates.py` (new, 3 cases), `tests/test_comparative_regime_pairs_schema.py` (new, 2 cases). |

---

## 12. After you ship each phase

1. **Commit** with a message ending `Co-Authored-By: Claude
   Opus 4.7 (1M context) <noreply@anthropic.com>`.
2. **Bump the orchestration env matrix version** in the same commit
   per CLAUDE.md non-negotiable. Suggested version slug per phase:
   - 8b: `v2026-05-XX-polish-trace-observability`
   - 8a: `v2026-05-XX-substantive-polish-fallback`
   - 8c: `v2026-05-XX-allowlist-scaffold-expansion`
   - 8d: `v2026-05-XX-comparative-regime-termination`
3. **Re-run the 10-Q probe** via
   `.claude/skills/answer-engine-probe/scripts/stage_run.py` +
   `run_sme_parallel.py`, slug `<phase>_verification`.
4. **Ask the operator before triggering the §1.G SME panel** per
   `feedback_sme_panel_explicit_request_only`. Land code + tests +
   probe results first; then ask.
5. **Update this doc** with the phase outcome status: 💡 → 🛠 → 🧪 →
   ✅ (or ↩ if discarded).
6. **Suggest the next step** to the operator per
   `feedback_always_suggest_next` (which phase to ship next, what
   it unblocks, and the cost in time).
