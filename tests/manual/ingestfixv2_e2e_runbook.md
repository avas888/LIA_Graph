# Ingest-Fix v2 E2E Runbook

**Plan:** `docs/next/ingestfixv2.md` — subtopic-aware ingestion + retrieval.
**Stakeholder:** avasqueza@gmail.com
**Reviewer:** TBD on execution.

This runbook is the stakeholder-facing checklist that drives the full
production cut for ingest-fix-v2. Code + tests are already green on
branch `feat/suin-ingestion` (Phases 1–8 automated tests all green). The
steps below execute the changes against live infrastructure. **Do not
execute steps 4+ without explicit sign-off.**

Every run produces an evidence bundle under
`tests/manual/ingestfixv2_evidence/<run-ts>/`. Copy the template in that
directory (see §7) and fill it in as you go.

---

## 0. Pre-flight

Run from repo root on a clean `feat/suin-ingestion` checkout:

```bash
PYTHONPATH=src:. uv run --group dev pytest \
  tests/test_subtopic_taxonomy_loader.py \
  tests/test_subtopic_taxonomy_sync.py \
  tests/test_ingest_classifier.py \
  tests/test_supabase_sink_subtopic.py \
  tests/test_graph_schema_subtopic.py \
  tests/test_suin_bridge_subtopic.py \
  tests/test_planner_subtopic_intent.py \
  tests/test_retriever_supabase_subtopic_boost.py \
  tests/test_retriever_falkor_subtopic.py \
  tests/test_backfill_subtopic.py \
  -q
```

Expected: 100% green. If anything is red, STOP and fix before executing.

Also:

```bash
cd frontend && npx vitest run tests/subtopicChip.test.ts tests/atomicDiscipline.test.ts
```

Expected: 10 passing tests, no atomic-discipline regressions.

---

## 1. Classifier smoke probe (3 docs)

Before any database writes, run the classifier on 3 fixture docs to
confirm PASO 4 returns the expected shape:

```bash
PYTHONPATH=src:. uv run python - <<'PY'
from lia_graph.ingestion_classifier import classify_ingestion_document
for fname, body in [
    ("NOM-parafiscales.md", "Este documento explica el aporte obligatorio al ICBF y las reglas de parafiscales en nómina."),
    ("IVA-factura.md", "La factura como título valor requiere aceptación expresa..."),
    ("generic.md", "Documento generico sin subtema identificable."),
]:
    r = classify_ingestion_document(filename=fname, body_text=body)
    print(fname, "→", r.detected_topic, r.subtopic_key, r.subtopic_confidence, r.requires_subtopic_review)
PY
```

Expected: first two docs resolve to a real topic with a `subtopic_key`,
third doc has `subtopic_key=None` and `requires_subtopic_review=False`
or True depending on LLM output. Record actual values in the evidence
bundle.

---

## 2. Apply Supabase migration (wip / local docker first)

**Scope:** local docker Supabase only. Cloud Supabase is step 4.

```bash
make supabase-start   # if not running
supabase db reset     # applies all migrations including 20260421000000_sub_topic_taxonomy.sql
```

Verify the new table exists:

```bash
PYTHONPATH=src:. uv run python - <<'PY'
from lia_graph.supabase_client import create_supabase_client_for_target
c = create_supabase_client_for_target("wip")
resp = c.table("sub_topic_taxonomy").select("count", count="exact").execute()
print("sub_topic_taxonomy rows:", getattr(resp, "count", 0))
PY
```

Expected: 0 rows (table exists, empty).

---

## 3. Sync taxonomy to local Supabase

```bash
make phase2-sync-subtopic-taxonomy TARGET=wip DRY_RUN=1
make phase2-sync-subtopic-taxonomy TARGET=wip
```

Expected: dry-run echoes "would upsert 86 rows"; commit reports 86 rows
upserted + `subtopic.ingest.taxonomy_synced` event in `logs/events.jsonl`.

---

## 4. [STAKEHOLDER GATE] Apply migration to cloud staging Supabase

Requires explicit "go" from stakeholder — this mutates cloud resources.

```bash
# Only after sign-off:
supabase link --project-ref <staging-project-ref>
supabase db push  # applies 20260421000000_sub_topic_taxonomy.sql
```

Verify `hybrid_search` RPC accepts the new params:

```bash
PYTHONPATH=src:. uv run python - <<'PY'
from lia_graph.supabase_client import create_supabase_client_for_target
c = create_supabase_client_for_target("wip")
c.rpc("hybrid_search", {
    "query_embedding": [0.0] * 768,
    "query_text": "smoke",
    "filter_pais": "colombia",
    "match_count": 1,
    "filter_subtopic": None,
    "subtopic_boost": 1.5,
}).execute()
print("rpc ok")
PY
```

Expected: no error. Any error here means step 4 did not apply cleanly.

Then sync taxonomy to cloud:

```bash
make phase2-sync-subtopic-taxonomy TARGET=production
```

---

## 5. Backfill dry-run against cloud Supabase

```bash
make phase2-backfill-subtopic DRY_RUN=1 LIMIT=20
```

Expected: output resembles

```
backfill_subtopic: processed=20 updated=<N> failed=<M> elapsed=<T>s (dry_run=True)
```

`updated` should be > 0 for labor/IVA docs. `failed` should be 0.
`logs/events.jsonl` should carry 20 × `subtopic.backfill.doc.processed`.

---

## 6. [STAKEHOLDER GATE] Full backfill against cloud Supabase

Estimated cost: $5–15 one-time (see plan §0.7). Requires explicit go.

```bash
# Pilot: laboral topic only, to validate before full sweep.
make phase2-backfill-subtopic ONLY_TOPIC=laboral RATE_LIMIT_RPM=60

# Full sweep — only after pilot looks good.
make phase2-backfill-subtopic RATE_LIMIT_RPM=60
```

Pass criterion: `docs_with_subtopic / docs_total >= 0.90` after
completion. Measured via:

```sql
SELECT
  COUNT(*) FILTER (WHERE subtema IS NOT NULL) AS with_subtopic,
  COUNT(*) AS total,
  (COUNT(*) FILTER (WHERE subtema IS NOT NULL)::float / COUNT(*)) AS coverage
FROM documents
WHERE sync_generation = (
  SELECT generation_id FROM corpus_generations WHERE is_active LIMIT 1
);
```

---

## 7. Retrieval boost verification (5 canned chat queries)

Pick 5 canonical queries and confirm the boost fires. For each:

1. Submit via chat (or the raw `/api/pipeline_d/retrieve` endpoint).
2. Confirm `response.diagnostics.retrieval_sub_topic_intent` matches the
   expected subtopic key.
3. Confirm the top chunk's `subtema` matches that intent.

| Query | Expected topic | Expected subtopic |
|---|---|---|
| "cómo liquido parafiscales ICBF" | `laboral` | `aporte_parafiscales_icbf` |
| "factura como título valor" | `iva` | `factura_titulo_valor` or equivalent |
| "presunción de costos independientes UGPP" | `ugpp` | (curated entry) |
| "pago de nómina electrónica" | `laboral` or `iva` | `nomina_electronica` |
| "reforma tributaria 2277" | `reforma_tributaria` | (no intent expected) |

Copy each `response.diagnostics` into the evidence bundle.

---

## 8. Evidence bundle template

Copy `tests/manual/ingestfixv2_evidence/TEMPLATE/` to
`tests/manual/ingestfixv2_evidence/<run-ts>/` and fill in:

- `classifier_probe.json` — output from step 1
- `migration_apply.log` — output from steps 2 + 4
- `taxonomy_sync.log` — output from step 3 + step 5 header
- `backfill_summary.json` — output from step 6
- `coverage_query.sql.txt` + result
- `retrieval_5_queries/<n>_<slug>.json` — diagnostics payloads from step 7
- `signoff.txt` — stakeholder sign-off note

---

## 9. Close-out

Once steps 0–8 are green and the evidence bundle is complete, continue
with Phase 10 of `docs/next/ingestfixv2.md`:

- update `docs/orchestration/orchestration.md` change log with `v2026-MM-DD-stv2`
- move this plan to `docs/done/ingestfixv2.md`
- cut the PR off `feat/suin-ingestion`

DoD complete when the plan dashboard (§2 of the plan doc) reads
`COMPLETE`.
