# Corpus completeness > retrieval tuning

**Source:** `docs/done/next/ingestion_tunningv1.md` §0 headline findings (2026-04-24); confirmed by `docs/done/next/ingestion_tunningv2.md` §4 phase-2 success criteria.

## The finding

The v5 30Q A/B evaluation was interpreted as "retrieval is broken." A full investigation week (I1–I7) traced the real failure mode back to an **ingestion gap**: ~3,600 curated markdown documents under `knowledge_base/CORE ya Arriba/*/EXPERTOS/` and `*/PRACTICA/` existed on disk but were **not in the ingested corpus**. Specifically:

- `artifacts/parsed_articles.jsonl` pre-v6: **2,118 articles**, 1,865 under `NORMATIVA/` path segments, **zero** under `EXPERTOS/` or `PRACTICA/`.
- Disk inventory: **99 curated directories / ~398 markdown files** invisible to the retriever.
- v6 phase-2 rebuild: **7,883 articles** — 1,391 EXPERTOS + 2,218 PRACTICA + 2,647 NORMATIVA + 1,627 OTHER. 2.7× corpus expansion.

**Every metric downstream shifted after the rebuild**: classifier keyword gaps re-ranked, subtopic bindings grew from 432 → 1,543, typed edges from 20,368 → 30,519.

## Why this matters for future planners

1. **Corpus audit is P0 when eval metrics are bad.** Before tuning retrieval, prove that expected-referenced articles exist in `parsed_articles.jsonl`. The v1 script used:
   ```bash
   grep -cE "NORMATIVA|PRACTICA|EXPERTO" artifacts/parsed_articles.jsonl
   ```
2. **The ingestion pipeline wasn't buggy — the artifact was stale.** `make phase2-graph-artifacts` was the right command; it had just not been re-run since 2026-04-21. A file timestamp check (`stat -f "%Sm" artifacts/parsed_articles.jsonl`) is a 5-second triage.
3. **"Retrieval over-filters Practice content" was the boss's concern.** Answer: moot under a stale artifact (there WAS no Practice content to over-filter). Became valid only after phase-2 added the content. Design the topic-scope gate to account for cross-topic Practice/Expertos from day one of their presence, not retroactively.
4. **Embedded doctrine inside normative articles is a contamination vector.** Normative articles' `full_text` contains sections like "**Doctrina Concordante:**", "**Jurisprudencia:**", "**Concepto DIAN 833 de 2024:**". Lexical retrieval over these subsections surfaces authoritative-looking but topic-mismatched chunks — Q16 biofuel-in-labor is the canonical example. The fix is topic-scope filtering at retrieval time, not at ingest time.

## Anti-pattern to watch for

"We need a better reranker" — said before a corpus audit. In the v6 cycle this would have been 2-3 weeks of misspent effort. Always audit the corpus first.

## See also

- [`artifact-coherence.md`](artifact-coherence.md) — how to not break the artifact set while experimenting.
- [`../retrieval/coherence-gate-and-contamination.md`](../retrieval/coherence-gate-and-contamination.md) — the retrieval-side consequence.
- `docs/done/next/ingestion_tunningv1.md` §0 I1b findings.
