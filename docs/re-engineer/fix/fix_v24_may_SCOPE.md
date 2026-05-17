# fix_v24_may_SCOPE.md — cloud-corpus pollution cleanup (initial scope)

> **Status.** Scope ticket only — opened by v23 P4-T5. v24 fix doc is drafted from this scaffold AFTER v23 closes (per `feedback_recommendations_logged_in_canonical_plan` v23 stays the canonical plan until closed).

## What v24 closes

- Retire / re-chunk every cloud Supabase `public.document_chunks` row surfaced by `scripts/corpus_audit/pollution_scan.py` (v23 P4-T1) as either `retire` or `re-chunk` severity.
- Promote `LIA_CHUNK_QUALITY_ENTITY_FILTER` from `shadow` → `enforce` after the source-of-pollution chunks are retired (otherwise the runtime filter would just keep masking the underlying data bug).

## v23 P4 hand-off

- Pollution report (latest run): `tracers_and_logs/corpus_audit/<UTC>_pollution_report.md`
- Counts to fill before v24 opens:
  - Retire candidates: TBD
  - Re-chunk candidates: TBD
  - Keep (false-positive) candidates: TBD

## Verbatim audit pollution strings (must retire 100 %)

- `DISTRIBUIDORA EL SOL SAS`
- `ALEJANDRO VASQUEZ ARANGO`
- `Formulario 7` (when bundled with the above)

## Likely workstreams

1. **Retire**. CLI-explicit retirement per CLAUDE.md non-negotiable — `lia-graph-artifacts --additive --allow-retirements` typed by operator.
2. **Re-chunk**. Where the pollution is wrapped around legitimate normative content, rerun chunker with anonymisation pre-pass.
3. **Promote runtime filter**. Once retire+re-chunk is complete, flip `LIA_CHUNK_QUALITY_ENTITY_FILTER=enforce` across the three modes in `dev-launcher.mjs`.
4. **Add ingestion guard**. Extend `chunk_quality_heuristics.score_entity_pollution` (or its ingest-time twin) so future ingests cannot reintroduce the same patterns.

## Pre-conditions

- v23 closes (P8 SME re-run pass).
- `tracers_and_logs/corpus_audit/<UTC>_pollution_report.md` exists.

## Not in scope (defer)

- Cloud Falkor topology cleanup — only chunks change in v24; the graph stays intact.
- Production rebuilds for unrelated topic drift.

## Status

- 💡 idea opened 2026-05-17 by fix_v23_may.md P4-T5.
- 🟡 not started (gated on v23 closing + pollution report).
