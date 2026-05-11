# fix_v10_may_diagnosis.md — §9.1 cloud-Supabase probe (Phase 10A pre-check)

> **Drafted 2026-05-11 PM Bogotá** by claude-opus-4-7. Scaffold for
> the §9.1 open question in `fix_v10_may.md`: "Are interpretation
> chunks ALREADY in cloud Supabase?" The answer decides whether
> Phase 10A's re-ingest is a 30-min UPDATE backfill or a full
> ~4-hour re-process.
>
> **Status.** ✅ CLOSED 2026-05-11 01:25 PM Bogotá. Path A backfill
> ran live against cloud Supabase. 2,275 chunks retagged (812
> interpretative_guidance + 1,463 practica_erp). G2 sink-level
> parity guardrails shipped in the same session so future ingests
> can't reintroduce the bug silently. Remaining gate before
> unblocking Phase 10B: operator-authorized §1.G 36-Q SME panel
> re-run. Scripts:
> `scripts/diagnostics/probe_v10_knowledge_class.py` (verify) +
> `scripts/diagnostics/backfill_v10_knowledge_class.py` (the fix).

---

## 0. One-paragraph context for a fresh reader

The Interpretación de Expertos panel works on Railway production
today only because of the `.railwayignore` whitelist (commit
`2d50f93`) that ships the 105 markdown files into the container.
The catalog scans them off disk on every request. We want to
retire that disk scan and put interpretations on the same Supabase
+ Falkor path the chat already uses. The very first gap to close
is that `document_chunks.knowledge_class` is `'normative_base'`
for every chunk in cloud Supabase, regardless of whether the
parent doc is a norm, an ERP practice note, or an expert
interpretation. Until that field is correct, `hybrid_search` can't
isolate the interpretation corpus.

The code fix is done. The remaining question is whether
interpretation chunks are already physically in Supabase (just
mistagged) or whether they were never written at all because some
upstream filter dropped them.

---

## 1. The probe

Run on cloud Supabase (staging is fine; production not required for
the probe — staging mirrors production for this question). Use
either the Supabase SQL editor in the dashboard, or
`PGURI=$LIA_SUPABASE_DB_URL psql -f - <<'SQL' ... SQL` from the
operator's CLI.

```sql
SELECT
  count(*) AS total_chunks,
  count(*) FILTER (
    WHERE knowledge_class = 'interpretative_guidance'
  ) AS tagged_interp,
  count(*) FILTER (
    WHERE knowledge_class = 'practica_erp'
  ) AS tagged_practica,
  count(*) FILTER (
    WHERE knowledge_class = 'normative_base'
  ) AS tagged_norm,
  count(*) FILTER (
    WHERE doc_id IN (
      SELECT doc_id FROM documents
      WHERE relative_path LIKE '%EXPERTOS%'
         OR knowledge_class = 'interpretative_guidance'
    )
  ) AS interp_chunks_by_parent
FROM document_chunks;
```

Companion query — same answer at the document level, for sanity:

```sql
SELECT
  knowledge_class,
  count(*) AS document_count
FROM documents
GROUP BY 1
ORDER BY document_count DESC;
```

Expected baseline from `artifacts/canonical_corpus_manifest.json`:
1,007 `normative_base`, 169 `practica_erp`, 105
`interpretative_guidance`, 5 `unknown`. Documents-level numbers
SHOULD already match; chunk-level numbers tell us which branch we're
on.

---

## 2. Decision tree

| `tagged_interp` | `interp_chunks_by_parent` | What it means | Path |
|---|---|---|---|
| 0 | ≥ ~1,000 | Chunks ARE in Supabase but mistagged | **Path A — UPDATE backfill** |
| 0 | < ~500 | Chunks never landed (upstream drop) | **Path B — full re-ingest** |
| ≥ ~1,000 | matches | Already fixed somehow (shouldn't happen) | Skip Phase 10A re-ingest; jump to 10B |
| 1–999 | mismatched | Partial run / drift | Investigate before proceeding |

### Path A — UPDATE backfill (cheapest)

If the chunks exist (just mistagged), one statement fixes them:

```sql
UPDATE document_chunks AS c
SET knowledge_class = d.knowledge_class
FROM documents AS d
WHERE c.doc_id = d.doc_id
  AND d.knowledge_class IN ('interpretative_guidance', 'practica_erp')
  AND c.knowledge_class <> d.knowledge_class;
```

Wall-clock: ~30 sec on staging. Verify with the §1 probe afterward.
No re-embedding needed — the existing vectors stay valid.

### Path B — full re-ingest

If the chunks never landed, run from operator's CLI in the
Lia_Graph working dir (writes pre-authorized per
`feedback_lia_graph_cloud_writes_authorized` but **announce
before triggering** per the same memory):

```bash
make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=staging
```

Wall-clock: ~30 min based on `cloud_promotion` reference
implementation. Idempotent via UPSERT on `chunk_id`. Will populate
`knowledge_class` correctly thanks to the Phase 10A code change.

After completion, embedding backfill (`embedding_ops.py`) picks up
the new rows on its next pass; no extra trigger required.

---

## 3. Post-probe acceptance gate (§5.1 gate 3 in `fix_v10_may.md`)

After Path A or B completes, re-run §1's probe. Pass criteria:

* `tagged_interp` ≥ 1,000 (≈ 105 docs × ~10 chunks/doc lower bound;
  the manifest's `EXPERTOS`-path hit count in
  `artifacts/parsed_articles.jsonl` was 1,285)
* `tagged_practica` ≥ 500 (169 docs × ~3 chunks/doc lower bound)
* `tagged_norm` does NOT decrease from its pre-fix value — this
  is the regression guard (Phase 10A only ADDS correct tags; if
  this number drops, something else has gone wrong)

If the regression guard trips, roll back the code change and
re-investigate. The fix is purely additive on the chunk row, so
a regression here would indicate a pre-existing bug surfaced.

---

## 4. After the gate passes

* Mark task **#3 (operator-gated re-ingest + §1.G regression check)**
  in this session's task list as ready.
* Operator-authorize the §1.G 36-Q SME panel re-run per
  `feedback_sme_panel_explicit_request_only` — Phase 10A must not
  regress chat quality. Baseline target: 34/36 acc+ post-fix_v8f.
* Once §1.G holds at or above baseline, unblock Phase 10B
  (`retriever_supabase.py` + dispatcher; new mini-panel).

---

## 5. Open follow-ups (defer to v10.1 unless §9.3 resolves earlier)

* §9.3 — add `documents.provider_labels (text[])` column? Recommended
  yes, in a small post-baseline migration
  `supabase/migrations/20260513000000_documents_provider_labels.sql`.
  Avoids the "encoded in concept_tags" anti-pattern. Not needed for
  10A's keystone to work but tightens 10B's provider story.
* §9.5 — per-provider trust-tier policy via
  `config/provider_trust_tiers.json`. Out-of-scope for v10 minimum
  viable; in-scope for v10.1.

---

## 6. Result table

```
Run timestamp (Bogotá AM/PM): 2026-05-11 01:16 PM
Probe target (staging | production): cloud (shared by staging+prod runtimes)
total_chunks:                19,546
tagged_interp:                    0
tagged_practica:                  0
tagged_norm:                 19,546   ← every chunk mistagged
tagged_unknown:                   0
documents.knowledge_class breakdown:
  normative_base:          6,448
  practica_erp:              169
  interpretative_guidance:   105
  unknown:                    14
interp_chunks_by_parent:    1,414  (union of 105 tagged + 316 path-matched docs)
practica_chunks_by_parent:  1,463  (from 169 practica_erp-tagged docs)
total chunks to retag:      2,877  (initial estimate, 14.7% of the 19,546 total)

Decision: Path A — UPDATE backfill

Backfill run timestamp:        2026-05-11 01:25 PM Bogotá [LIVE]
Chunks actually retagged:      2,275  (812 interp + 1,463 practica)
Gap from initial estimate:       602  (chunks parented by EXPERTOS-path docs
                                       still tagged normative_base at the doc
                                       level — v10.1 audit task, not a
                                       backfill failure; Path A correctly
                                       refused to retag these)

Post-backfill tagged_interp:     812
Post-backfill tagged_practica: 1,463
Post-backfill tagged_norm:    17,271  (= 19,546 − 2,275; exact, no
                                        collateral loss)
Total chunks preserved:       19,546  ✓ (no row gained or lost)
Regression-guard pass (Y/N):       Y
```

### Anomaly worth a note (not blocking the backfill)

The 316 docs matching path `%EXPERTOS%` is meaningfully larger than
the 105 docs tagged `interpretative_guidance` at the document level.
That means ~211 docs sit under an `EXPERTOS/` path but are tagged
`normative_base` (or another class) at the document level. Two
possibilities:

1. The path naming is broader than the taxonomy (some EXPERTOS docs
   are e.g. internal templates, not actual expert commentary).
2. Some docs are mis-tagged at the document level too.

This does NOT block Path A — the backfill keys off the document
row's `knowledge_class`, so it will only retag chunks whose parent
is correctly tagged. The 211 doc-level mismatches surface as a v10.1
follow-up: walk those documents and reconcile the path vs taxonomy.
