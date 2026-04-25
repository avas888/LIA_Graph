# Path-veto: rule-based correction layer above an LLM ingest classifier

> **Captured 2026-04-25** at the close of the next_v3 cycle. Pattern lives in `src/lia_graph/ingestion_classifier.py` (`_apply_path_veto` + `PATH_VETO_RULES`). Validated through 4 production rebuilds (Cypher 2/6 → 5/6 → 6/6).

## The problem this solves

A taxonomy-aware LLM classifier with mutex rules + meta-heuristics + path-veto clauses *in the prompt* can still ignore those instructions on a non-trivial fraction of documents. Specifically: an instruction like "if `source_path` matches `RENTA/NORMATIVA/Normativa/.*Libro1_T1_Cap5_Deducciones`, return `costos_deducciones_renta`" gets treated as guidance, not a hard constraint. The classifier returns `iva` or `sector_cultura` based on content drift, despite the path being unambiguous.

This was Alejandro's prediction (the SME called it "Option K2"): **taxonomy + prompt rewrite alone wouldn't fix the wrong-routing on the canonical RENTA/Libro1 paths. A hard rule-based override above the LLM would be needed.**

He was right. The Cypher verification on rebuild #2 showed 2/6 pass — the LLM was correctly handling brand-new topics (impuesto_timbre via Libro 4) but failing to override its own pre-existing wrong verdicts on the 4 classic RENTA-Libro-1 mis-routings.

## The pattern

A **post-classification sanity check** in pure Python that runs after the LLM verdict is settled:

```python
PATH_VETO_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"RENTA/NORMATIVA/Normativa/.*Libro1_T1_Cap5_Deducciones"), "costos_deducciones_renta"),
    (re.compile(r"RENTA/NORMATIVA/Normativa/.*Libro1_T2_Patrimonio"),       "patrimonio_fiscal_renta"),
    (re.compile(r"RENTA/NORMATIVA/Normativa/.*Libro1_T1_Cap1_Ingresos"),    "ingresos_fiscales_renta"),
    (re.compile(r"RENTA/NORMATIVA/Normativa/.*Libro5_Procedimiento"),       "procedimiento_tributario"),
    (re.compile(r"RENTA/NORMATIVA/Normativa/.*Libro4_Timbre"),              "impuesto_timbre"),
    (re.compile(r"RENTA/NORMATIVA/Normativa/.*Libro6_GMF"),                 "gravamen_movimiento_financiero_4x1000"),
    # ... extend per file as the corpus grows
)

def _apply_path_veto(
    filename: str, llm_verdict: str
) -> tuple[str, str | None, bool]:
    """Returns (final_topic, reason, rule_matched).

    rule_matched=True even when the LLM verdict already agrees with the rule —
    this is critical for downstream propagation (see "Three rebuilds" below).
    """
    for rx, canonical_topic in PATH_VETO_RULES:
        if rx.search(filename):
            if llm_verdict != canonical_topic:
                return canonical_topic, f"path_veto:{canonical_topic}", True
            return llm_verdict, None, True  # rule_matched=True even on agreement
    return llm_verdict, None, False
```

Wired into `classify_ingestion_document` after the LLM verdict, before subtopic resolution. When a rule matches, mark the verdict as `classification_source = "path_veto"` so downstream propagation honors it.

## Three rebuilds before this hit 6/6 — the debugging arc that taught us the pattern

This is worth preserving in detail because the bugs were subtle.

| Rebuild | Cypher result | Bug discovered |
|---|---|---|
| #2 | 2/6 pass | Path-veto fired 13× and emitted events, but the corrected topic didn't reach Supabase. The propagation gate in `evaluate_doc_verdict` (in `ingest_subtopic_pass.py`) was confidence-gated and dropped path-veto'd verdicts when the subtopic verdict was weak. |
| #3 | 5/6 pass | Honoring `classification_source == "path_veto"` in `evaluate_doc_verdict` fixed propagation for the 4 obvious flips. But row 5 (Libro 5 Procedimiento) still failed because the doc's INITIAL `topic_key` (path-inferred to `iva`) survived all the way to Supabase — the LLM verdict happened to match the path-veto rule (`procedimiento_tributario`), so the rule was a no-op and didn't mark the verdict as path-veto-sourced. The original wrong `topic_key` from earlier in the pipeline survived. |
| #4 | **6/6 pass** | Split `_apply_path_veto`'s return into `(final, reason, rule_matched)`. **`rule_matched=True` whenever the rule matches — even on a no-op agreement.** This always flips `classification_source` to `path_veto`, ensuring the canonical topic propagates to Supabase regardless of whether the LLM was right or wrong. |

The lesson: **a rule-based correction layer must mark its verdicts as authoritative even when it agrees with the LLM**, otherwise upstream pipeline state can leak through.

## When to use this pattern

Path-veto is the right tool when **all three** are true:

1. **The document path encodes ground truth.** If `RENTA/NORMATIVA/Normativa/Libro1_T1_Cap5_Deducciones.md` is by-construction always about deductions in renta, the path is the truth.
2. **The LLM keeps getting it wrong despite prompt engineering.** Repeated mis-routings across rebuilds with different prompt variants → no further LLM-side intervention will fix it.
3. **The override doesn't depend on document content.** Path is a sufficient signal on its own. (If you need content + path to decide, you need a different pattern — usually a multi-pass classifier.)

When **not** to use it:

- The path is noisy (mixed-content directories, drag-and-drop uploads). Override would mis-route legitimate edge cases.
- The override would need to inspect content. Encode the rule in the LLM prompt; don't try to re-implement classification in regex.
- The set of rules is unbounded (>100 patterns). At that scale you're re-building a classifier in Python; either bite the bullet on a separate ML classifier or invest more in the LLM prompt.

## Extension policy

- **One regex per canonical-content directory.** Don't merge multiple paths into one regex — keep each rule auditable.
- **Test-first.** `tests/test_classifier_path_veto.py` pins every rule + the `rule_matched`-on-no-op regression case. Add a test before adding a rule.
- **Emit telemetry on every override.** `classifier.path_veto_applied` event so production logs surface when the override is firing and on what.
- **Verify in Cypher after every rebuild.** `scripts/diagnostics/probe_taxonomy_v2.py` is the gate. If a new rule lands and Cypher doesn't move, the rule isn't actually firing — debug the propagation, not the rule.

## Cross-references

- `src/lia_graph/ingestion_classifier.py` — `_apply_path_veto` + `PATH_VETO_RULES` + `_TAXONOMY_AWARE_FLAG`
- `src/lia_graph/ingest_subtopic_pass.py` — `evaluate_doc_verdict` honoring `classification_source == "path_veto"`
- `tests/test_classifier_path_veto.py` — 36 tests
- `scripts/diagnostics/probe_taxonomy_v2.py` — Cypher verification gate
- `docs/aa_next/done/next_v3.md §13.7` — the full debugging arc captured in real time
