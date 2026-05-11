## fix_v9_may.md — close the cross-topic bleed properly + unstick plazos/calendario retrieval

> **Drafted 2026-05-11 PM Bogotá** by claude-opus-4-7 after the fix_v8
> ship cycle (env matrix `v2026-05-11-fix-v8-polish-fallback-prompt-anchor`,
> commit `e492e4b`) cleared the polish-side surface and confirmed two
> remaining content-quality gaps: (a) beneficio-auditoría / RST answers
> still leak pérdidas-fiscales bullets (Q05 / Q06 on the 10-question
> probe) because the topic-norm allowlist expansion was reverted, and
> (b) tax-calendar questions like Q07 ("plazos AG 2025") drift to
> irrelevant ET articles (Art. 100 renta vitalicia) because the planner
> has no calendar case and the corpus answer pattern is decree-driven.
>
> **Audience.** Zero-context fresh LLM or engineer. This doc is
> self-contained. Read `fix_v8_may.md §3c` first if you want the
> archaeology of the topic-filter expansion attempt that got reverted;
> read `fix_v8_may.md §3g` for the parallel ICA-anchor surgery that
> phase 9b mirrors.
>
> **What this is.** Two surgical workstreams, in the order they should
> ship: (9a) re-ship the topic-norm-allowlist expansion that fix_v8 §3c
> deferred, this time built from cloud-chunks probes + real-answer
> citation inventories rather than spec-doc guesses; (9b) close the
> tax-calendar retrieval gap by adding a `_looks_like_calendar_case`
> planner marker + a decreto-anchor that mirrors fix_v8 §3g's ICA
> anchor shape.
>
> **What this is not.** Not a polish-side change. Not a corpus
> ingestion push. Not a six-topic guess-list — every prefix in 9a
> must trace back to a verified cloud-chunk row AND/OR a real served
> answer's citation. Per `feedback_no_hallucinated_examples`,
> `feedback_diagnose_before_intervene`, and the lesson learned from
> fix_v8 §3c's over-fire.
>
> **Scope guard.** The §1.G 36-Q SME panel closing bar is the
> `v2026-05-11-fix-v8-polish-fallback-prompt-anchor` result: 34/36
> acc+, 26 strong, 0 weak (run dir
> `evals/sme_validation_v1/runs/20260511T153120Z_post_fix_v8f_temp0/`).
> Every phase below must re-run the panel **after** landing and confirm
> ≥ 34/36 acc+ with no drop in strong count and zero new weak. The
> §1.G run is gated behind `feedback_sme_panel_explicit_request_only`
> — ask the operator before triggering.

---

## 0. Inheritance from fix_v1..fix_v8 (read once, then this doc)

Everything in `fix_v8_may.md §0` carries forward unchanged. Additional
invariants this doc adds:

- **fix_v8 §3a–§3g are LIVE on production.** Substantive polish-rejected
  fallback (`pipeline_d/answer_polish_rejected_fallback.py`), polish
  trace observability, comparative-regime instrumentation, the polish
  prompt rewrite (DIRECTIVA PRIMARIA + explicit allowlists), gemini-flash
  temperature 0.0, and the ICA-deduction Art. 115 anchor are all
  shipped. The standing baseline this doc must not regress is the
  post-v8f SME panel.
- **The over-fire-blocked status of fix_v8 §3c stays intact until 9a
  fully replaces it.** Today the scaffold ships with two topic entries
  (`perdidas_fiscales_art147`, `regimen_simple`). The reverted draft
  with the 6-topic expansion lives in git history at the pre-revert
  commit and in the `fix_v8_may.md §3c` postmortem.
- **No retrieval-side mechanical change.** Per fix_v7 §3a and the
  operator's standing directive: `filter_topic` stays `None`,
  `boost_topic` stays the routed topic, `LIA_QUERY_EMBEDDINGS_ENABLED=1`
  stays the default. 9a is a content-gate config change; 9b is a
  planner-side anchor addition. Neither touches the hybrid_search RPC
  payload shape.
- **Per-question hand-patches are forbidden.** The temptation to fix
  Q05/Q06 by adding planner anchors for "exclude Art. 147" or to fix
  Q07 by hard-coding "Decreto 2229 de 2024" without a tax-calendar
  classifier is explicitly out of scope. The 9a/9b fixes must
  generalize across the topic class, not the specific question.

---

## 1. The diagnosis (verified 2026-05-11 PM against `dev:staging`)

The post-fix_v8f 10-question probe
(`tracers_and_logs/logs/probe_runs/20260511T152744Z_10q_post_v8f/`) and
the post-fix_v8f SME panel
(`evals/sme_validation_v1/runs/20260511T153120Z_post_fix_v8f_temp0/`)
combine to surface the two remaining content-quality gaps this doc
closes.

### Diagnosis 1 — Off-topic-norm bleed survives on beneficio-auditoría / RST topics

**Symptom (Q05 — "¿Si corrijo mi declaración después de que venció el
término de firmeza anticipada, pierdo el beneficio de auditoría?"):**
the served answer (2700 chars) opens with a paragraph that frames the
question around Art. 147 ET pérdidas-fiscales compensation rules
instead of Art. 689-3 ET / Art. 714 ET firmeza framework. The
fallback assembled correctly because polish rejected, but the
fallback's evidence came from `costos_deducciones_renta`-tagged chunks
(the routed topic per the LLM classifier was wrong on this question,
or correct but with retrieval drifting cross-topic).

**Symptom (Q06 — "¿Un contribuyente del RST puede acceder al
beneficio de auditoría?"):** answer cites "arts. 689-3 y 3 ET" — the
`y 3 ET` is the polish smushing two separate references. Beyond the
typo, the bullets discuss pérdidas-fiscales compensation, off-topic
for a RST + beneficio question that should anchor on Arts. 689-3 +
903–916 ET.

**Why the gate doesn't catch it today:** the topic-gate scaffold only
covers `perdidas_fiscales_art147` and `regimen_simple`. When the
router lands a question on `beneficio_auditoria` (the correct topic
for Q05/Q06), the gate emits `noop_no_topic_entry` and passes
everything. The fix_v8 §3c expansion would have fixed this but was
reverted because the candidate prefix lists for several topics
(`declaracion_renta`, `procedimiento_tributario`,
`costos_deducciones_renta`) did not cover the full set of ET articles
real served answers cite — Arts. 869 (abuso del derecho), 115 (ICA
descuento), 147 (pérdidas), 850 (devolución), 588/589 (correcciones)
were all dropped by the over-narrow allowlists, breaking
`tests/test_phase3_graph_planner_retrieval.py`.

**Root cause:** the spec-doc seed prefixes were a guess. The right
input data is two-fold:
- the union of ET article numbers that appear as citations in real
  served answers across the §1.G SME panel + canonical probe runs
- the set of `chunks.reference_key` rows in cloud Supabase that
  resolve under each topic's `topic` column

A prefix lands in `allowed_prefixes` only if BOTH lists corroborate it
(it's a real article + it actually surfaces in answers).

### Diagnosis 2 — Tax-calendar questions retrieve the wrong article family

**Symptom (Q07 — "¿Cuáles son los plazos para presentar la declaración
de renta AG 2025 de personas jurídicas?"):** the post-fix_v8f run
returns 1956 chars (substantive shape thanks to §3e polish), but the
Anclaje legal section cites Art. 100 ET ("Determinación de la renta
bruta en contratos de renta vitalicia") — adjacent to "renta" by
keyword but irrelevant to plazos.

**Why retrieval lands on Art. 100:** the planner has no calendar-case
marker. `_looks_like_tax_treatment_case` matches "puedo deducir" /
"deducible"; `_looks_like_loss_compensation_case` matches "pérdidas
fiscales" / "compensar". Nothing matches "plazos" / "vencimiento" /
"calendario tributario" / "AG YYYY". So the message lands as
`computation_chain` with `plan_anchor_count=0`, retrieval falls back
to topic-boosted hybrid_search, and the FTS half hits "renta" hard
enough that low-numbered renta articles surface ahead of the actual
plazos decree.

**Why the right answer is a decreto, not an ET article:** Colombian
tax plazos are set by an annual **Decreto reglamentario** issued by
MinHacienda (typical pattern: `Decreto NNNN de YYYY` setting the
plazos for the AG that follows). The ET itself does NOT contain
calendar-of-payments data — Art. 811 ET ("Plazos para declarar") is a
shell that points to the Decreto. The right anchor for "AG 2025
plazos" is the active Decreto for AG 2025 plazos.

**Corpus dependency:** before the planner anchor can pull a decreto,
the decreto must exist as an ingested document with a usable
`reference_key`. The corpus has the prior-year decretos (Decreto 2229
de 2024 for AG 2024 plazos is plausible — **VERIFY against
`knowledge_base/`** before relying on this id). Whether the AG 2025
plazos decreto is in the corpus needs a check.

### What's healthy (do not regress)

- **fix_v7 §3a + §3b + §3c invariants** + **fix_v8 §3a + §3b**
  observability surface — every served chat carries `polish_mode` +
  `polish_skip_reason` + `gate_mode` in diagnostics.
- **Phase3 test suite (43/43 green)** as of `e492e4b`. The 9a allowlist
  expansion must preserve every assertion in those tests — that's the
  hard floor for "didn't break what works."
- **fix_v8 §3g ICA anchor (Art. 115) for `costos_deducciones_renta`
  tax-treatment questions** — Q01 verified, do not regress.
- **The §1.G SME panel closing bar at 34/36 acc+ / 26 strong / 0
  weak** — `evals/sme_validation_v1/runs/20260511T153120Z_post_fix_v8f_temp0/`.
- **Substantive polish-rejected fallback** — the §3a fallback catches
  every rejection cleanly today; 9a must not introduce a new failure
  mode where the gate drops every fallback bullet and leaves the user
  with nothing.

---

## 2. The plan — two surgical phases, ship 9a → 9b

| Phase | Fix | Why this order | Effort |
|---|---|---|---|
| 9a | Topic-norm-allowlist expansion built from real data | Closes the dominant remaining content-quality complaint (off-topic bullets in beneficio / RST answers). Fully blocks on a cloud-chunks probe + real-answer citation inventory; outputs a config-only change once the data lands. The widest blast radius of the two — needs phase3 + 10q + SME panel re-runs to verify. | M — half to one day incl. SME validation |
| 9b | Tax-calendar planner case + decreto anchor | Closes the Q07 retrieval-drift pattern (and the family of plazos / vencimientos / AG-YYYY questions it represents). Same shape as fix_v8 §3g's ICA-anchor surgery — a `_looks_like_calendar_case` marker + an explicit `kind="reform"` (or `kind="article"` for Art. 811) anchor. Smaller surface; can ship in isolation. | M — half a day |

The phases compose:

- 9a alone: closes off-topic-norm bleed on `beneficio_auditoria`,
  `declaracion_renta`, `procedimiento_tributario`,
  `costos_deducciones_renta`, `facturacion_electronica`. Q05 / Q06
  beneficio-auditoría answers stop emitting Art. 147 bullets.
- 9a + 9b: closes Q07 plazos drift. Plazos / calendario answers
  anchor on the active Decreto reglamentario instead of Art. 100.
- 9b alone (skipping 9a): possible if the operator wants to ship the
  Q07 fix first while the cloud-chunks probe for 9a runs in parallel.
  The phases are independent.

---

## 3. Implementation (numbered, copy-paste-ready)

### Phase 9a — topic-norm-allowlist expansion done right (target: half to one day incl. SME panel)

#### 3a.1 — Build the cloud-chunks inventory script

Create `scripts/eval/build_allowlist_inventory.py`:

```python
"""fix_v9 §3a — build a candidate `allowed_prefixes` list per topic
from two sources: (a) cloud Supabase chunks tagged with the topic,
(b) ET article numbers cited as `(art. N ET)` / `Art. N ET` in real
served answers from a §1.G SME panel run dir.

A prefix lands in the candidate list only when BOTH sources corroborate
it — per `feedback_no_hallucinated_examples`, every prefix must be a
real article AND must actually surface in served answers, not a
spec-doc guess.

Output: `evals/topic_norm_allowlist_inventory/<UTC_TS>/`
- per-topic JSON with `(cloud_prefixes, cited_prefixes, intersection,
  union, only_in_chunks, only_in_answers)`
- `summary.md` — human-readable diff of what each topic SHOULD have
  vs. what `config/topic_norm_allowlist.json` has today

Usage:
    PYTHONPATH=src:. uv run python scripts/eval/build_allowlist_inventory.py \\
        --run-dir evals/sme_validation_v1/runs/20260511T153120Z_post_fix_v8f_temp0 \\
        --topics beneficio_auditoria declaracion_renta procedimiento_tributario \\
                 costos_deducciones_renta facturacion_electronica
"""
```

Implementation outline:

1. Connect to cloud Supabase via `lia_graph.supabase_client.get_supabase_client()`.
2. For each topic in `--topics`, query
   `chunks.reference_key LIKE 'art:%' AND topic = <topic>` and collect
   distinct `art:<N>` keys. Normalize: strip trailing hyphenated/
   letter suffixes to the base article number (e.g. `art:689-3` →
   `art:689` is the prefix that matches both `689` and `689-3`).
3. For each `*.json` in `--run-dir`, walk `response.answer_markdown`
   with the same regex `answer_topic_gate._NORM_INLINE_RE` uses,
   collect article keys cited per (qid, topic_routed). Aggregate by
   `topic_routed`.
4. Output per-topic intersection (cloud chunks ∩ cited articles) as
   the **safe candidate** list. Output set differences as **diagnostic
   buckets**:
   - `only_in_chunks` — articles tagged with this topic in the corpus
     but never cited in any answer; either dead corpus content or
     synthesis-side gap.
   - `only_in_answers` — articles cited in answers under this topic
     but tagged in the corpus under a DIFFERENT topic; either
     cross-topic carve-out candidates or retrieval drift.

#### 3a.2 — Run the inventory against the post-v8f SME panel + the 10q probe

```bash
PYTHONPATH=src:. uv run python scripts/eval/build_allowlist_inventory.py \
    --run-dir evals/sme_validation_v1/runs/20260511T153120Z_post_fix_v8f_temp0 \
    --probe-run-dir tracers_and_logs/logs/probe_runs/20260511T152744Z_10q_post_v8f \
    --topics beneficio_auditoria declaracion_renta procedimiento_tributario \
             costos_deducciones_renta facturacion_electronica \
             firmeza_declaraciones dividendos_y_distribucion_utilidades \
             devoluciones_saldos_a_favor regimen_sancionatorio_extemporaneidad \
             descuentos_tributarios_renta tarifas_renta_y_ttd \
             perdidas_fiscales_art147 regimen_simple
```

The output `summary.md` is the input for step 3a.3. Reading time:
~15 minutes for an engineer.

#### 3a.3 — Build `allowed_prefixes` per topic from the inventory

Hard rules:

1. A prefix lands in `allowed_prefixes` IFF it appears in the
   intersection (cloud-chunk AND cited-in-answers) for that topic.
2. A prefix DOES NOT land in `allowed_prefixes` if it only appears in
   `only_in_chunks` — that's corpus content the synthesis isn't
   actually surfacing; including it bloats the allowlist without
   adding gate effectiveness.
3. A prefix from `only_in_answers` is the **important diagnostic**:
   either (a) the article is canonically cross-topic and should be
   listed in `cross_topic_allowed` of the topic doing the citing, or
   (b) the article is retrieval drift and should be IN the allowlist
   of its true topic but EXCLUDED from this one. The decision is per
   article. Default: cross-topic carve-out unless the citation is
   clearly wrong (e.g. Art. 100 renta vitalicia on a plazos question
   is wrong; do not carve out).
4. **Per `feedback_thresholds_no_lower`**: if the inventory shows a
   topic legitimately spans 30+ articles (e.g. `declaracion_renta`),
   list them all. Do not artificially cap the prefix count.

Example expected shape for `costos_deducciones_renta` (placeholder —
**verify via 3a.2 before merging**):

```json
"costos_deducciones_renta": {
  "allowed_prefixes": [
    "art:107", "art:108", "art:115", "art:121", "art:122", "art:123",
    "art:128", "art:131", "art:141", "art:142", "art:143", "art:177",
    "art:771", "art:869"
  ],
  "cross_topic_allowed": ["facturacion_electronica", "ica",
                          "declaracion_renta", "procedimiento_tributario"],
  "_notes": "Generated 2026-05-XX via scripts/eval/build_allowlist_inventory.py from evals/sme_validation_v1/runs/20260511T153120Z_post_fix_v8f_temp0/ + tracers_and_logs/logs/probe_runs/20260511T152744Z_10q_post_v8f/. Every prefix verified against real cloud `chunks.reference_key` rows AND at least one cited article in the SME panel. Cross-topic carve-out covers documento-soporte (771-2 ↔ FE), Art. 115 ICA descuento, Art. 869 abuso when context is renta planning."
}
```

#### 3a.4 — Update `config/topic_norm_allowlist.json` with the verified entries

Edit the file. Keep the existing two entries (`perdidas_fiscales_art147`,
`regimen_simple`) unchanged unless the inventory specifically widens
them. Add the new entries from 3a.3. The `_doc` field must be updated
to record the methodology and the date.

#### 3a.5 — Pre-flight against phase3 test suite

Before declaring the config ready, run:

```bash
PYTHONPATH=src:. uv run pytest tests/test_phase3_graph_planner_retrieval.py -q --tb=line
```

All 43 cases MUST pass. If any fail, the allowlist is over-firing —
inspect which bullets got dropped, decide whether the dropped article
should be in `allowed_prefixes` (real cross-topic interaction) or
whether the test expectation needs amendment (retrieval drift that
shouldn't be the test's responsibility to defend). When in doubt,
WIDEN the allowlist; do not weaken the test. Per
`feedback_thresholds_no_lower`.

#### 3a.6 — End-to-end verification

Run the 10-question post-v8f probe again against the new allowlist:

```bash
PYTHONPATH=src:. uv run python .claude/skills/answer-engine-probe/scripts/stage_run.py \
    --slug 10q_post_v9a \
    --from-jsonl tracers_and_logs/logs/probe_runs/20260511T131027Z_10q_post_fix_v7_hotfix/questions.jsonl
```

Then probe each question. The pass criteria:
- Q05 / Q06 (beneficio-auditoría family) drop Art. 147 / Art. 290
  bullets — verify via `synthesis.topic_gate.applied.dropped_count ≥ 1`
  on those questions.
- Q01–Q04, Q07–Q10 answers do NOT shrink by > 30% chars vs the
  post-v8f baseline. If any do, the allowlist is over-firing on a
  topic and needs widening.
- `polish_mode` distribution stays comparable (post-v8f: 3/10
  rejected; post-9a: 3/10 ± 1).

Then ask the operator to trigger the §1.G panel
(`feedback_sme_panel_explicit_request_only`); the panel must hold
the post-v8f closing bar (≥ 34/36 acc+, ≥ 26 strong, 0 weak).

#### 3a.7 — Update orchestration docs

In `docs/orchestration/orchestration.md` Lane 6.6c (Cross-Topic
Content Gate), update the "Allowlist hygiene" paragraph to record the
v9a expansion: list the now-covered topics, point to the
`scripts/eval/build_allowlist_inventory.py` script as the canonical
way to extend the allowlist, and explicitly retire the fix_v8 §3c
"drafted-but-blocked" status note. Bump the env-matrix version to
`v2026-05-XX-fix-v9a-allowlist-expansion`.

In `docs/re-engineer/fix/fix_v8_may.md §3c`, append a final status
line: "↩ → ✅ Closed by fix_v9 §3a — see
`docs/re-engineer/fix/fix_v9_may.md`."

### Phase 9b — tax-calendar planner case + decreto anchor (target: half a day)

#### 3b.1 — Confirm the corpus has the active plazos decreto

Before any planner change, verify the decreto exists in
`knowledge_base/` and is ingested. Run:

```python
# from a python repl with PYTHONPATH=src
from lia_graph.supabase_client import get_supabase_client
db = get_supabase_client()
res = (
    db.table("documents")
    .select("doc_id, title, family, topic")
    .ilike("title", "%plazos%")
    .ilike("title", "%2025%")
    .execute()
)
for row in res.data or []:
    print(row)
```

Expected hit: a `Decreto NNNN de 2024` (or similar) document with
title containing "plazos" + "2025" — the canonical reference for
AG 2025 plazos. If zero rows, the corpus has a gap and 9b must
short-circuit to a "Cobertura parcial — el decreto de plazos AG 2025
no está indexado todavía" abstention via `answer_policy.py`.
**Per `feedback_no_hallucinated_examples`, do not hard-code "Decreto
2229 de 2024" in the planner — verify the actual `doc_id` first**.

#### 3b.2 — Add `_looks_like_calendar_case` to `planner_query_modes.py`

Following the same pattern as `_looks_like_tax_treatment_case`
(fix_v8 §3g):

```python
def _looks_like_calendar_case(normalized_message: str) -> bool:
    """Detect tax-calendar questions: plazos, vencimientos, calendario
    tributario. These questions are NOT answered by ET articles — the
    canonical anchor is the annual Decreto reglamentario."""
    calendar_markers = (
        "plazos para",
        "plazo para",
        "plazo de",
        "vencimiento",
        "vencimientos",
        "calendario tributario",
        "calendario de",
        "fechas para presentar",
        "fechas de pago",
        "ultimo digito",
        "último dígito",
        "cuando vence",
        "cuándo vence",
        "cuando presentar",
        "cuándo presentar",
    )
    # The calendar case fires only when the question is about an AG
    # year (so we can look up the right decreto). Patterns like
    # "AG 2025", "año gravable 2025", "para 2025", "del 2025".
    has_ag_year = bool(
        re.search(r"\bag\s*\d{4}\b", normalized_message)
        or re.search(r"a[nñ]o\s+gravable\s+\d{4}", normalized_message)
        or re.search(r"para\s+(?:el\s+)?\d{4}", normalized_message)
        or re.search(r"del\s+\d{4}", normalized_message)
    )
    has_calendar_marker = any(
        marker in normalized_message for marker in calendar_markers
    )
    return has_calendar_marker and has_ag_year
```

Export it from `planner_query_modes.py` and import in `planner.py`
alongside `_looks_like_tax_treatment_case`.

#### 3b.3 — Add a calendar case to `_build_article_search_queries`

```python
# fix_v9 §3b — tax-calendar case. Q07 trace showed `plan_anchor_count=0`
# and retrieval drifting to Art. 100 (renta vitalicia, irrelevant) for
# "plazos AG 2025". The canonical anchor for plazos is the annual
# Decreto reglamentario, not an ET article. Art. 811 ET is the shell
# that points to the decreto; we keep it as a fallback anchor.
if _looks_like_calendar_case(normalized_message):
    queries.extend(
        (
            "decreto plazos declaracion renta personas juridicas "
            "calendario tributario MinHacienda",
            "decreto reglamentario plazos pago renta DIAN AG anual",
            "art 811 ET plazos para declarar reglamentacion",
        )
    )
```

#### 3b.4 — Add explicit `kind="reform"` anchor for the active plazos decreto

Following the same pattern as fix_v8 §3g's Art. 115 anchor. After the
inventory in 3b.1 confirms the doc_id of the active decreto, add an
entry-point in `planner.build_graph_retrieval_plan`:

```python
if (
    not article_refs
    and not reform_refs
    and _looks_like_calendar_case(normalized_message)
):
    # Anchor the active plazos decreto. The `doc_id` resolves to a
    # specific `Decreto NNNN de YYYY` per the annual calendar.
    # Verify before merging — do not hard-code; load from
    # config/tax_calendar_anchors.json (new — see 3b.5).
    decreto_doc_id = _resolve_plazos_decreto_for(normalized_message)
    if decreto_doc_id is not None:
        entry_points.append(
            PlannerEntryPoint(
                kind="reform",
                lookup_value=decreto_doc_id,
                source="tax_calendar_anchor",
                confidence=0.9,
                label=_resolve_plazos_decreto_label(normalized_message),
                resolved_key=decreto_doc_id,
            )
        )
    # Always anchor Art. 811 ET as the shell that points to the
    # decreto — even when the specific decreto isn't ingested, the
    # synthesis can still surface "the plazos están en el Decreto
    # reglamentario anual" using Art. 811 as evidence.
    entry_points.append(
        PlannerEntryPoint(
            kind="article",
            lookup_value="811",
            source="tax_calendar_anchor",
            confidence=0.85,
            label="Art. 811",
            resolved_key="811",
        )
    )
```

#### 3b.5 — Add `config/tax_calendar_anchors.json` to map AG year → decreto

```json
{
  "_schema_version": 1,
  "_doc": "fix_v9 §3b — per-AG-year decreto reglamentario de plazos. Maps `ag_year: <int>` to the canonical doc_id of the active plazos decreto. Updated yearly when MinHacienda issues the new calendar (typically December for the following AG). Per `feedback_no_hallucinated_examples`, every doc_id must be verified against `knowledge_base/` AND against cloud Supabase `documents.doc_id`. When a year has no entry, the planner falls back to Art. 811 ET as the shell anchor and synthesis surfaces a Cobertura-parcial notice.",
  "_validation_rule": "every doc_id resolves to a real document; tests/test_tax_calendar_anchors.py enforces this against `knowledge_base/` paths.",
  "entries": {
    "2024": {
      "doc_id": "VERIFY_via_3b.1",
      "label": "Decreto reglamentario AG 2024",
      "_notes": "fill in after running the 3b.1 probe"
    },
    "2025": {
      "doc_id": "VERIFY_via_3b.1",
      "label": "Decreto reglamentario AG 2025",
      "_notes": "fill in after running the 3b.1 probe; if the AG 2025 decreto isn't out yet, leave doc_id=null and the planner will degrade gracefully"
    }
  }
}
```

Helper functions `_resolve_plazos_decreto_for(normalized_message)` and
`_resolve_plazos_decreto_label(normalized_message)` extract the AG year
from the message and look up the entry. Cached via `@lru_cache(maxsize=1)`
on `load_calendar_anchors()`.

#### 3b.6 — Cobertura-parcial notice when the decreto isn't ingested

If `_resolve_plazos_decreto_for` returns `None` (year not in config
OR `doc_id == null`), the synthesis layer should surface an explicit
notice to the user. Add to `pipeline_d/answer_policy.py`:

```python
def calendar_coverage_notice(request_message: str) -> str | None:
    """fix_v9 §3b — when the planner classifies the turn as
    `_looks_like_calendar_case` AND the active plazos decreto isn't
    in the corpus, the answer must explicitly tell the user we're
    pointing at the shell article (Art. 811 ET) without the specific
    plazos table.
    """
    if not _looks_like_calendar_case(normalize_text(request_message)):
        return None
    ag_year = _extract_ag_year(request_message)
    if ag_year is None:
        return None
    anchors = load_calendar_anchors()
    entry = (anchors.get("entries") or {}).get(str(ag_year)) or {}
    if entry.get("doc_id"):
        return None
    return (
        f"Cobertura parcial: el Decreto reglamentario de plazos para "
        f"AG {ag_year} todavía no está indexado en el corpus. Estoy "
        f"apuntando al art. 811 ET (la regla marco que delega la "
        f"definición de plazos al decreto anual). Confirma el "
        f"decreto vigente con la página oficial de la DIAN antes de "
        f"usar la fecha exacta con el cliente."
    )
```

Wire it into `answer_assembly.compose_main_chat_answer` — when the
notice is non-null, prepend it to the assembled answer before polish
runs. The DIRECTIVA PRIMARIA in the polish prompt already forbids
inventing year/period references; this notice survives because it's
in the template the LLM is told to preserve.

#### 3b.7 — Update orchestration docs

In `docs/orchestration/orchestration.md` Lane 4.4 (Planner — Query
Modes), document the new `_looks_like_calendar_case` marker. Add a
sub-bullet under Lane 4.5 (Retrieval) for the `tax_calendar_anchor`
source tag. Bump the env-matrix version to
`v2026-05-XX-fix-v9b-calendar-anchor`.

---

## 4. How to test each implementation worked

### 4a — Topic-norm-allowlist expansion test plan

**Actor**: engineer + operator-triggered SME panel.
**Environment**: `dev:staging`.
**Steps**:

1. Run `scripts/eval/build_allowlist_inventory.py` against the post-v8f
   panel + 10q probe. Inspect the per-topic `summary.md`.
2. Hand-curate the new entries in `config/topic_norm_allowlist.json`
   per 3a.3 rules.
3. Run `pytest tests/test_phase3_graph_planner_retrieval.py` — must
   be 43/43 green.
4. Run `pytest tests/test_topic_norm_allowlist.py` — schema + canonical
   form invariants must hold.
5. Run `LIA_SUPABASE_TEST=1 pytest tests/test_topic_norm_allowlist.py::test_every_prefix_matches_real_chunks`
   — every new prefix must match ≥ 1 real cloud chunk.
6. Restart `dev:staging` server (mandatory per the probe-skill
   precondition).
7. Re-run the 10q post-v8f probe (slug `10q_post_v9a`). Confirm
   on Q05 / Q06: `synthesis.topic_gate.applied.gate_mode = applied`,
   `dropped_count ≥ 1`, `kept_count > 0`. Confirm Q01–Q04 / Q07–Q10
   don't shrink > 30%.
8. Ask the operator to trigger the §1.G panel (slug
   `36q_post_v9a`). Decision rule: ≥ 34/36 acc+, ≥ 26 strong, 0 weak.

**Numeric decision rule**:
- 43/43 phase3 tests green AND
- Q05 + Q06 each drop ≥ 1 off-topic bullet AND
- No question outside the targeted set shrinks > 30% chars AND
- SME panel ≥ 34/36 acc+ with ≥ 26 strong AND 0 weak.

**Regression gate**: §1.G 36-Q SME panel. Operator-triggered.

### 4b — Tax-calendar test plan

**Actor**: engineer + SME spot-check on Q07.
**Environment**: `dev:staging`.
**Steps**:

1. Run the corpus-probe from 3b.1. Capture the `doc_id` of the AG
   2024 + AG 2025 plazos decretos. If AG 2025 not present, leave the
   entry's `doc_id: null` and the Cobertura-parcial notice fires.
2. Fill in `config/tax_calendar_anchors.json` per 3b.5.
3. Land the planner changes (3b.2 + 3b.3 + 3b.4) and the policy
   change (3b.6).
4. Run `pytest tests/test_phase3_graph_planner_retrieval.py` — must
   be 43/43 green; add a new test
   `test_phase3_pipeline_d_plazos_ag2025_anchors_decreto_or_art_811`
   that confirms the planner emits a `tax_calendar_anchor` entry
   point.
5. Restart server.
6. Re-run Q07 alone via the probe. The answer must satisfy:
   - `polish_mode ∈ {llm, rejected}` (not `failed` / `unknown`)
   - If the decreto is in the corpus: cite the decreto by its label
   - If the decreto is NOT in the corpus: the Cobertura-parcial
     notice appears at the top of the answer
   - The Anclaje legal section does NOT cite Art. 100 ET (renta
     vitalicia) anymore.
7. Run a second turn-borrowing the decomposer: ask "y para personas
   naturales?" as a follow-up. Confirm the planner still anchors
   the decreto (state-aware) and doesn't drift.

**Numeric decision rule**:
- 43/43 + 1 new = 44/44 phase3 tests green
- Q07 served chars ≥ 600 AND contains decreto label OR Cobertura
  notice
- Q07 answer does NOT contain "art. 100 ET"

**Regression gate**: §1.G 36-Q SME panel. Plazos questions in the
panel (if any) must not regress.

---

## 5. Drift guardrails (how to prevent each fix from being silently undone)

### 5a — Allowlist expansion

| Guardrail | Mechanism |
|---|---|
| Config schema | `tests/test_topic_norm_allowlist.py` — every topic key in `_TOPIC_KEYWORDS`, every prefix canonical, no duplicates, every `cross_topic_allowed` entry is a real topic. |
| Cloud-chunks contract | `@pytest.mark.requires_supabase` test — every non-empty prefix matches ≥ 1 cloud chunk. Run via `LIA_SUPABASE_TEST=1`. |
| Real-answer corroboration | `scripts/eval/build_allowlist_inventory.py` re-run before any future widening — output stored alongside the allowlist version bump. |
| Over-fire detection | `tests/test_phase3_graph_planner_retrieval.py` (43 cases) must stay green; any case that fails means the new allowlist dropped a bullet a known-correct answer relies on. |
| Operator override | `LIA_TOPIC_GATE_MODE=off` (existing) disables without removing the config. |

### 5b — Tax-calendar

| Guardrail | Mechanism |
|---|---|
| Config validation | `tests/test_tax_calendar_anchors.py` — every non-null `doc_id` resolves to a real document. Schema-version bump bumps the env matrix. |
| Planner contract | `tests/test_phase3_graph_planner_retrieval.py::test_phase3_pipeline_d_plazos_ag2025_anchors_decreto_or_art_811` locks the calendar case + anchor emission. |
| Cobertura-parcial notice | `tests/test_answer_policy_calendar_notice.py` (new) — when `doc_id` is null, the notice text appears in the assembled template. |
| Year-driven invalidation | The config is a per-year map; missing a year → graceful fallback to Art. 811 ET. No drift possible if the operator forgets to update for a new AG until the year actually runs over. |

---

## 6. Automatic test updates (what to add to the existing test suite)

### 6a — `tests/test_topic_norm_allowlist.py` (existing, extended)

- The new topic entries automatically inherit the existing schema tests
  (canonical prefix form, no duplicates, real topic keys).
- The `@pytest.mark.requires_supabase` test from fix_v8 §3c stays;
  every new prefix from 9a is exercised by it.

### 6b — `scripts/eval/build_allowlist_inventory.py` (new tool — not a test)

Not a pytest case; it's an operator/engineer tool that's run before
config bumps. Treat the script's `--dry-run` output as part of the PR
diff so reviewers can see which prefixes are being added/dropped and
on what evidence.

### 6c — `tests/test_tax_calendar_anchors.py` (new file)

```python
"""fix_v9 §3b — schema validation for `config/tax_calendar_anchors.json`."""

def test_config_loads_and_is_well_formed(): ...
def test_every_year_is_4_digits_in_plausible_range(): ...
def test_every_non_null_doc_id_resolves_in_corpus(): ...  # may be `requires_supabase`
def test_every_entry_has_label(): ...
```

### 6d — `tests/test_phase3_graph_planner_retrieval.py` (existing, extended)

Add:

```python
def test_phase3_pipeline_d_plazos_ag2025_anchors_decreto_or_art_811():
    """fix_v9 §3b binding case: a plazos AG 2025 question must (a)
    fire the calendar case, (b) emit a `tax_calendar_anchor` entry
    point, (c) anchor Art. 811 ET at minimum, (d) NOT anchor Art. 100
    ET."""
    ...

def test_phase3_pipeline_d_calendar_case_skips_when_no_ag_year():
    """A question with 'plazos' but no AG year must NOT fire the
    calendar case (we can't pick a decreto without knowing the year);
    fall through to standard computation_chain."""
    ...
```

### 6e — `tests/test_answer_policy_calendar_notice.py` (new file)

```python
"""fix_v9 §3b — Cobertura-parcial notice when the active plazos
decreto isn't in the corpus."""

def test_notice_appears_when_doc_id_null(): ...
def test_notice_does_not_appear_when_decreto_present(): ...
def test_notice_does_not_appear_for_non_calendar_question(): ...
```

---

## 7. Six-gate sign-off per phase

| Gate | 9a (allowlist expansion) | 9b (tax-calendar anchor) |
|---|---|---|
| **1. Idea** | Topic-norm gate must cover the topics that produce off-topic-norm bleed, not just the two scaffold topics. Expansion built from real data, not spec-doc guesses. | Tax-calendar questions anchor on the annual Decreto reglamentario (or Art. 811 ET as shell) instead of drifting to whatever ET article hits "renta" lexically. |
| **2. Plan** | §3a above (inventory script + curate JSON + verify against tests + SME panel). | §3b above (corpus probe + new planner case + reform anchor + Cobertura-parcial notice + per-year config). |
| **3. Measurable criterion** | Q05 + Q06 each drop ≥ 1 off-topic bullet via the gate. No question shrinks > 30% chars. SME panel ≥ 34/36 acc+, ≥ 26 strong, 0 weak. 43/43 phase3 tests green. | Q07 answer does NOT cite Art. 100 ET. Q07 cites the active plazos decreto OR shows the Cobertura-parcial notice. 44/44 phase3 tests green (43 existing + 1 new). |
| **4. Test plan** | §4a above. | §4b above. |
| **5. Greenlight** | Technical tests pass + SME spot-check on Q05 + Q06 + operator-triggered §1.G panel. | Technical tests pass + SME spot-check on Q07 + 1 adversarial follow-up. |
| **6. Refine or discard** | If a topic over-fires (a phase3 test fails OR a non-targeted question shrinks > 30%), WIDEN that topic's allowlist using the inventory's `only_in_answers` bucket; never weaken the test. If the SME panel regresses, set `LIA_TOPIC_GATE_MODE=off` and re-diagnose. | If Q07 still drifts, check whether `_looks_like_calendar_case` actually fired (trace the planner). If the decreto isn't in the corpus and the notice doesn't appear, the wire-up missed something — inspect `compose_main_chat_answer`. |

Per `feedback_verify_fixes_end_to_end`: unit tests green alone is NOT
greenlight. Both phases need an SME-relevant real-data run at gate 5.

---

## 8. What you must NOT do

- Do **not** hand-pick allowlist prefixes from a spec doc. Every
  prefix must trace back to the inventory output (cloud chunks ∩
  cited articles). Per `feedback_no_hallucinated_examples` and the
  lesson from fix_v8 §3c.
- Do **not** narrow the prefix list to "make the gate fire more
  often." The gate is a content filter, not a forcing function. An
  over-narrow allowlist drops legitimate bullets; the user notices
  before the engineer does.
- Do **not** hand-patch Q05 / Q06 / Q07 individually. Add a tax-
  calendar case that GENERALIZES across the family ("plazos AG 2024",
  "plazos AG 2026", "vencimientos IVA", etc.). Per the operator's
  standing note: "if we over-correct for a particular question we
  are damaging the overall effectiveness of the general class
  retriever."
- Do **not** hard-code "Decreto 2229 de 2024" (or any specific
  decreto id) in the planner code. Decreto ids change year to year;
  the per-year config in 3b.5 is the durable shape.
- Do **not** widen the tax-calendar cue regex without also adding the
  AG-year requirement. "Plazos" without a year is ambiguous — fall
  through to standard `computation_chain` rather than guess which
  year.
- Do **not** lower §1.G thresholds (≥ 34 acc+, ≥ 26 strong) per
  `feedback_thresholds_no_lower`. The post-fix_v8f bar is the floor.
- Do **not** auto-run the §1.G panel without asking the operator
  first per `feedback_sme_panel_explicit_request_only`.
- Do **not** quote money in status reports per
  `feedback_no_money_quoting`. Time estimates fine.
- Do **not** ship 9a before the cloud-chunks inventory is in the
  PR description. Reviewers need to see what evidence justified
  each prefix.

---

## 9. Anchor data to compare against

- **Post-fix_v8f baseline (the run this doc is built on):**
  - 10q probe: `tracers_and_logs/logs/probe_runs/20260511T152744Z_10q_post_v8f/`
    (served 10/10, substantive 10/10, polish_rejected 3/10)
  - §1.G SME panel: `evals/sme_validation_v1/runs/20260511T153120Z_post_fix_v8f_temp0/`
    (PASS — 34/36 acc+, 26 strong, 0 weak, 18 polish-rejected)
- **Standing baseline before fix_v8:** `evals/sme_validation_v1/runs/20260430T000527Z_fix_v5_phase6b_rerun/`
  (32 strong / 4 acc / 0 weak / 36 acc+).
- **fix_v8 §3c revert evidence (do not repeat):** the over-fired
  draft was reverted on 2026-05-11 after `tests/test_phase3_graph_planner_retrieval.py`
  showed 3 failing cases (`test_phase3_pipeline_d_tax_planning_prompt_uses_rich_advisory_first_bubble`,
  `test_phase3_pipeline_d_recovers_art_115_for_ica_deduction_prompt`,
  `test_phase3_pipeline_d_end_to_end_smoke_for_accountant_style_refund_prompt`).
  The candidate prefix lists are recoverable via `git log -p config/topic_norm_allowlist.json`
  on the pre-revert commit.
- **fix_v8 §3g ICA-anchor evidence (template for 9b):**
  `tracers_and_logs/logs/probe_runs/20260511T155857Z_q01_ica_anchor/`
  showed `seed_article_keys` `['121','122','123']` → `['115','121','122','123']`
  after the explicit `kind="article"` anchor landed. 9b mirrors this
  shape with `kind="reform"`.

---

## 10. State of the world at hand-off (2026-05-11 PM Bogotá)

- fix_v7 §3a + §3b + §3c LANDED + verified on production
  (`v2026-05-11-fix-v7-retrieval-and-content-gate`).
- fix_v8 §3a + §3b + §3d + §3e + §3f + §3g LANDED + verified on
  production (`v2026-05-11-fix-v8-polish-fallback-prompt-anchor`,
  commit `e492e4b`). Railway auto-deployed from main.
- fix_v8 §3c topic-norm-allowlist expansion drafted but reverted
  (over-fired phase3 tests). This doc closes that gap.
- Migration `20260512000000_topic_filter_soft.sql` applied on cloud
  Supabase + local docker.
- Local docker stack reset + reseeded (10 test users HTTP 200,
  FalkorDB 26,653 nodes).
- Standing SME panel bar: 34/36 acc+, 26 strong, 0 weak. Closing-
  baseline (pre-fix_v8): 32 strong, 36 acc+.
- No SQL migrations pending. No restart pending.
- No other LLM agent is currently working on this seam.

---

## 11. Quick-reference: file map

| Phase | Files touched |
|---|---|
| 9a | `scripts/eval/build_allowlist_inventory.py` (new — inventory builder, ~200 LOC), `config/topic_norm_allowlist.json` (extend with verified per-topic entries), `tests/test_topic_norm_allowlist.py` (existing tests cover new entries; no changes), `docs/orchestration/orchestration.md` (Lane 6.6c hygiene paragraph + env matrix bump), `docs/re-engineer/fix/fix_v8_may.md §3c` (closure note pointing here), `docs/re-engineer/fix/fix_v9_may.md` (this doc — status updates). |
| 9b | `src/lia_graph/pipeline_d/planner_query_modes.py` (+ `_looks_like_calendar_case`), `src/lia_graph/pipeline_d/planner.py` (+ calendar case in `_build_article_search_queries` + explicit tax-calendar anchor entry-point + helper `_resolve_plazos_decreto_for`), `src/lia_graph/pipeline_d/answer_policy.py` (+ `calendar_coverage_notice`), `src/lia_graph/pipeline_d/answer_assembly.py` (+ notice prepend), `config/tax_calendar_anchors.json` (new), `tests/test_phase3_graph_planner_retrieval.py` (+ 2 new cases), `tests/test_tax_calendar_anchors.py` (new — schema), `tests/test_answer_policy_calendar_notice.py` (new — 3 cases), `docs/orchestration/orchestration.md` (Lane 4.4 + Lane 4.5 + env matrix bump). |

---

## 12. After you ship each phase

1. **Commit** with a message ending `Co-Authored-By: Claude
   Opus 4.7 (1M context) <noreply@anthropic.com>`.
2. **Bump the orchestration env matrix version** in the same commit
   per CLAUDE.md non-negotiable. Suggested version slugs:
   - 9a: `v2026-05-XX-fix-v9a-allowlist-expansion`
   - 9b: `v2026-05-XX-fix-v9b-calendar-anchor`
3. **Re-run the 10-Q probe** via the answer-engine-probe skill
   (mandatory server restart preamble per the fix_v8 update),
   slug `<phase>_verification`.
4. **Ask the operator before triggering the §1.G SME panel** per
   `feedback_sme_panel_explicit_request_only`. Land code + tests +
   probe results first; then ask.
5. **Update this doc** with the phase outcome status: 💡 → 🛠 → 🧪 →
   ✅ (or ↩ if discarded).
6. **Suggest the next step** to the operator per
   `feedback_always_suggest_next` (which phase to ship next, what
   it unblocks, and the cost in time).
