# Phase 8 — E2E acceptance runbook (ingestfixv1)

> **Run twice per Decision Env-A:**
> 1. First against `npm run dev` (local docker Supabase + local docker FalkorDB)
> 2. Then against `npm run dev:staging` (cloud Supabase + cloud FalkorDB)
>
> Capture evidence for each run under `tests/manual/phase8_evidence/<env>-<run-timestamp>/`.

## 0. Pre-flight

- [ ] On `feat/suin-ingestion`, working tree clean of unrelated edits.
- [ ] Local docker Supabase stack running (`supabase_*_lia-contador`). Verify: `supabase status`.
- [ ] Local docker FalkorDB running (`lia-graph-falkor-dev`). The launcher starts this.
- [ ] Admin credentials ready: `admin@lia.dev` / `Test123!`.
- [ ] Dropbox test docs staged at:
  ```
  /Users/ava-sensas/Library/CloudStorage/Dropbox/AAA_LOGGRO Ongoing/AI/LIA_contadores/Corpus/to_upload_graph/LEYES/LABORAL_SEGURIDAD_SOCIAL/
    ├── NORMATIVA/Resolucion-532-2024.md
    ├── EXPERTOS/EXPERTOS_Resolucion-532-2024.md
    └── LOGGRO/PRACTICA_Resolucion-532-2024.md
  ```

## 1. Start the server (local mode)

```bash
npm run dev
```

Server at `http://127.0.0.1:8787/`. Login via the Sesiones admin surface at `/admin/ingest`.

## 2. Drop the 3 UGPP docs

- [ ] Open the Sesiones tab. The new "Intake" zone is visible.
- [ ] Drag the `LABORAL_SEGURIDAD_SOCIAL/` folder onto the drop zone.
- [ ] **Expected within 5s:** 3 `intakeFileRow`s render with classifications:
  - `Resolucion-532-2024.md` → `topic=laboral, type=normative_base, conf≥0.95, requires_review=false`
  - `EXPERTOS_Resolucion-532-2024.md` → `topic=laboral, type=interpretative_guidance, conf≥0.85`
  - `PRACTICA_Resolucion-532-2024.md` → `topic=laboral, type=practica_erp, conf≥0.85`
- [ ] Save intake response JSON to `phase8_evidence/<env>-<ts>/intake_response.json`.

## 3. Click "Aprobar e ingerir"

- [ ] Target = `wip`, `auto_embed` = on (default), `auto_promote` = off.
- [ ] Capture `job_id` from the 200 response.

## 4. Watch progress timeline

- [ ] The 6-stage timeline animates: `coerce → audit → chunk → sink → falkor → embeddings`.
- [ ] Each stage transitions `pending → running → done` with counts shown.
- [ ] Log tail console shows the subprocess output.
- [ ] Capture progress responses at 3 moments (early / mid / post) and embedded-count delta.
- [ ] Total elapsed: 60–180 s locally.

## 5. Verify local WIP state (post-run)

```bash
PYTHONPATH=src:. uv run python -c "
from lia_graph.supabase_client import create_supabase_client_for_target
c = create_supabase_client_for_target('wip')
docs = c.table('documents').select('*', count='exact').in_('filename', [
    'Resolucion-532-2024.md',
    'EXPERTOS_Resolucion-532-2024.md',
    'PRACTICA_Resolucion-532-2024.md',
]).execute()
print({'docs_found': len(docs.data or []), 'rows': [(r['doc_id'], r['topic']) for r in (docs.data or [])]})
"
```
- [ ] Expect 3 rows, all `topic='laboral'`.
- [ ] `document_chunks` has rows with `chunk_section_type` populated.
- [ ] `embedding` column non-NULL for those rows.

```bash
PYTHONPATH=src:. uv run python scripts/ingestion/verify_suin_merge.py --target wip --generation <gen_id> --json | jq .
```

## 6. Switch to cloud (dev:staging) pass

- [ ] Stop the dev server. Start cloud mode:
  ```bash
  npm run dev:staging
  ```
- [ ] Repeat steps 2–4 but with `auto_promote=true` (target stays `wip`, promote to production at the end OR toggle target=production for the final press).
- [ ] Verify cloud Supabase + cloud FalkorDB reflect the new generation.

## 7. Chat probe

In the authenticated chat:
> ¿Qué cambió con la Resolución UGPP 532 de 2024 sobre la presunción de costos para independientes?

- [ ] Answer cites the 3 newly-ingested docs by filename.
- [ ] If edge parsing worked, the answer traverses the `Decreto 0379/2026` modification edge.

Save transcript to `phase8_evidence/<env>-<ts>/chat_probe.md`.

## 8. Capture evidence

For each run the following artifacts MUST exist under `tests/manual/phase8_evidence/<env>-<ts>/`:
- `intake_response.json`
- `run_request.json` + `run_response.json`
- `progress_early.json`, `progress_mid.json`, `progress_done.json`
- `log_tail_sample.txt`
- `verify_suin_merge.json`
- `chat_probe.md`
- at least 1 UI screenshot per stage transition (optional but recommended)

## 9. Rollback / cleanup (after cloud run)

If any issue surfaces during cloud run, invoke Promoción → Rollback to restore the prior active generation. The plan's Risk Register requires an explicit second confirmation for production writes; honor that.
