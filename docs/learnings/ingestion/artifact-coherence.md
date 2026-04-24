# Ingestion artifacts are a SET

**Source:** `docs/next/ingestion_tunningv2.md` §16 Appendix D §4; observed during v6 phase 2 execution on 2026-04-24.

## The invariant

These files in `artifacts/` are produced together by `make phase2-graph-artifacts` and **must be consumed together**. Swapping any one of them for a backup from a different run produces internally-inconsistent state that surfaces as `FileNotFoundError`, zero-primary retrieval, or the orchestrator's `compat_stub` fallback path.

| File | Role | Written by |
|---|---|---|
| `parsed_articles.jsonl` | One parsed article per line | `lia_graph.ingest` PASO 3 |
| `typed_edges.jsonl` | Classified edges (MODIFICA, DEROGA, CITA, etc.) | `ingestion.classifier.classify_edge_candidates` |
| `raw_edges.jsonl` | Edge candidates pre-classification | same |
| `canonical_corpus_manifest.json` | Authoritative document registry | `canonical_manifest_builder` |
| `corpus_audit_report.json` | Per-file ingestion decisions | PASO 1 audit |
| `corpus_inventory.json` | Flat inventory for dashboards | PASO 1 |
| `corpus_reconnaissance_report.json` | Topic/subtopic rollups | PASO 2 |
| `graph_load_report.json` | Falkor write counts (only with `--execute-load`) | graph client |
| `subtopic_decisions.jsonl` | Per-doc subtopic binding verdicts | PASO 4 + binding pass |
| `batch_N_quality_gate.json` | Per-batch gate reports (when chunked) | chunked runs only |

## The incident that taught us

During v6 phase-2 execution I ran three sequential rebuilds:
1. Sequential full (killed mid-run)
2. `--skip-llm` (completed in 9 min, parked as `*.skip_llm_interim`)
3. Parallel full (completed in 6.5 min)

While preparing for run #3 I moved the #2 `parsed_articles.jsonl` aside and restored the v5 backup — but only that one file. The other artifacts (`canonical_corpus_manifest.json`, `typed_edges.jsonl`, …) stayed on the #2 state (7,883 articles). The orchestrator's retriever cross-references article keys between `parsed_articles.jsonl` and the manifest; the 5,700-article mismatch caused it to raise `FileNotFoundError` → compat-stub fallback → phase-1 diagnostic lift test failed.

**The code was correct. The artifact set was incoherent.** Test fixed after restoring all `.skip_llm_interim` files together.

## The rule

When backing up or swapping artifact files, **treat `artifacts/` as an atomic unit**:

```bash
# backup BEFORE any rebuild or experiment
STAMP=$(date +%Y%m%d_%H%M)
for f in artifacts/*.json artifacts/*.jsonl; do
  cp "$f" "${f}.${STAMP}_backup"
done

# restore in reverse
for f in artifacts/*.${STAMP}_backup; do
  target="${f%.${STAMP}_backup}"
  cp "$f" "$target"
done
```

Never restore just `parsed_articles.jsonl` from an older backup. Never regenerate `typed_edges.jsonl` against a stale `parsed_articles.jsonl`. If you need to patch a single file, regenerate the full set.

## Diagnostic triage

If the orchestrator returns through the `compat_stub` path (`diagnostics["pipeline_family"] == "pipeline_d"` and `compatibility_mode == True`):

1. Check file timestamps — all artifacts should have the same `mtime`:
   ```bash
   stat -f "%Sm %N" artifacts/parsed_articles.jsonl artifacts/canonical_corpus_manifest.json artifacts/typed_edges.jsonl
   ```
2. If timestamps differ by more than a few seconds, you have a mixed set. Pick one rebuild's set and restore all of it.

## See also

- `docs/next/ingestion_tunningv2.md` §14 Appendix B — full inventory of phase-2 outputs.
- `src/lia_graph/pipeline_d/orchestrator.py:362` — the `FileNotFoundError` catch that masks artifact mismatch as compat-stub.
