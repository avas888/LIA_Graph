# SME-pending applier — taxonomy v2 spot-review (gate 8)

> **Created 2026-04-25** to pre-stage every conditional engineering edit for the 7 SME spot-review questions in `docs/aa_next/taxonomy_v2_sme_spot_review.md`. When Alejandro replies with letters per qid, run the applier; nothing else.
>
> All edits live as conditional patches in `apply_sme_decisions.py`. Inspecting the script tells you exactly what each SME letter does to the codebase. **No live code is touched until the applier runs.**

## Usage

```bash
# Dry-run preview (always do this first)
PYTHONPATH=src:. uv run python artifacts/sme_pending/apply_sme_decisions.py \
    --decisions q10:A,q13:A,q14:B,q15:A,q16:A,q26:A,q28:A --dry-run

# Apply
PYTHONPATH=src:. uv run python artifacts/sme_pending/apply_sme_decisions.py \
    --decisions q10:A,q13:A,q14:B,q15:A,q16:A,q26:A,q28:A

# Re-measure
make eval-taxonomy-v2
```

If `eval-taxonomy-v2` reports ≥ 27/30 chat-resolver, **§9 gate 8 → ✅** and re-flip is unblocked (gate 9 already qualitative-✅ per `gate_9_threshold_decision.md`).

## What each letter does

Two-table per question — first SME-question summary, then engineering action.

### q10 — `firmeza_declaraciones` default-to-parent

- **A** (recommended): adds `firmeza_declaraciones` to the chat-resolver prompt's "do not collapse to parent" exception list (`src/lia_graph/topic_router.py` `_build_classifier_prompt`).
- **B**: adds `declaracion_renta` to `ambiguous_acceptable` for q10 in `evals/gold_taxonomy_v2_validation.jsonl`.

**Corpus context:** `firmeza_declaraciones` has **0 docs in production** despite being `corpus_coverage=active` in v2. Routing right is correct intent, but downstream retrieval will return empty. This is part of the next_v4 §1 diagnostic measurement set (Q21).

### q13 — renta_presuntiva vs patrimonio ambiguity

- **A** (recommended): adds `impuesto_patrimonio_personas_naturales` to `ambiguous_acceptable` for q13.
- **B**: strengthens mutex rule "renta presuntiva is always renta_presuntiva, never patrimonio" in `config/topic_taxonomy.json`.

### q14 — descuento del IVA en bienes de capital

- **A**: adds a hard mutex "`descuento del IVA en bienes de capital` → always `descuentos_tributarios_renta`".
- **B** (recommended): adds `iva` to `ambiguous_acceptable` for q14.

### q15 — `retencion_en_la_fuente` (v1) vs `retencion_fuente_general` (v2)

**Corpus context (CRITICAL):** Production has **14 docs on `retencion_en_la_fuente`** (v1 key) and **1 doc on `retencion_fuente_general`** (v2 key). SME spec line 184 explicitly says *"Renombrar a `retencion_fuente_general`"* — but the rename was never applied to the corpus binding.

- **A** (recommended): marks v1 key as `status: deprecated, merged_into: ["retencion_fuente_general"]` in `config/topic_taxonomy.json`. **Plus an inevitable follow-up:** the 14 docs currently bound to `retencion_en_la_fuente` need re-classification to `retencion_fuente_general`. Applier flags this as a TODO; doesn't auto-execute (needs a rebuild path-veto rule + workers=4 rebuild).
- **B**: demote `retencion_fuente_general` to subtopic of `retencion_en_la_fuente`. Applier rejects this — large taxonomy refactor, requires explicit re-engineering.
- **C**: add `scope_out` text to each topic naming the other. Applier handles this in-place.

### q16 — `beneficio_auditoria` default-to-parent

- **A** (recommended): bundled with q10 — adds `beneficio_auditoria` to the prompt's "do not collapse to parent" exception list.
- **B**: adds `declaracion_renta` to `ambiguous_acceptable` for q16.

**Corpus context:** `beneficio_auditoria` has **2 docs in production**. Same downstream-empty-retrieval caveat as q10/firmeza.

### q26 — emplazamiento always procedimiento_tributario

- **A** (recommended): strengthens mutex rule 1 (`iva_vs_procedimiento_tributario`) in `config/topic_taxonomy.json` — adds an explicit override clause: *"If query mentions {emplazamiento, requerimiento especial, liquidación oficial, sanción}, ALWAYS procedimiento_tributario, regardless of substantive tax."*
- **B**: adds `iva` to `ambiguous_acceptable` for q26.

### q28 — zona franca tarifa

- **A** (recommended): adds `zonas_francas` to `ambiguous_acceptable` for q28.
- **B**: strengthens mutex "tarifa questions are always `tarifas_renta_y_ttd`, even when scoped to a regime".

## Always-applied (not SME-conditional)

The applier also enforces one always-on edit, regardless of SME decisions:

- `Makefile :: eval-taxonomy-v2` target gets `--use-llm` flag. **Already landed 2026-04-25** — without it, the target measures router-only (15/30) instead of chat-resolver (23/30). The applier idempotently re-asserts this if the line drifts.

## What the applier deliberately does NOT do

- **Re-flip `LIA_TEMA_FIRST_RETRIEVAL`.** Gate 8 closing only unblocks; the operator runs the re-flip per `next_v3 §13.10.7` item 3.
- **Re-route the 14 `retencion_en_la_fuente` docs to `retencion_fuente_general`** (q15:A follow-up). Surfaced as a TODO; needs a path-veto rule update + a workers=4 rebuild.
- **Run `make eval-taxonomy-v2` automatically.** Operator runs it after the applier.
- **Touch any code outside the four files named below.**

## Files the applier touches (full list)

1. `evals/gold_taxonomy_v2_validation.jsonl` — `ambiguous_acceptable` widening for q10/q13/q14/q16/q26/q28 (whichever ones picked B).
2. `src/lia_graph/topic_router.py` — `_build_classifier_prompt` exception list (q10/q16:A bundled).
3. `config/topic_taxonomy.json` — mutex rule 1 strengthening (q26:A); v1 retención deprecation (q15:A); other mutex tweaks if non-recommended options picked.
4. `Makefile` — `--use-llm` flag (idempotent).

Nothing else.

## Reverting

Every applier run also writes `artifacts/sme_pending/<timestamp>_revert.json` describing each edit applied. To revert:

```bash
PYTHONPATH=src:. uv run python artifacts/sme_pending/apply_sme_decisions.py \
    --revert artifacts/sme_pending/<timestamp>_revert.json
```
