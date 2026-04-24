# `scripts/monitoring/monitor_sector_reclassification/` — v3 Phase 2.5 tools

Isolated folder for the **sector reclassification work** documented in
`docs/next/ingestionfix_v3.md` §2.2 and §5 Phase 2.5.

Scoped to one job: turning the 510-doc `otros_sectoriales` catch-all into
~12-15 clean sector topics (+ migrating ~30-60 misclassified docs into
existing named topics) BEFORE the Phase 3 chain runs and permanently
encodes the bad taxonomy into Falkor graph state.

## Files in this folder

| File | Phase 2.5 task | Role |
|---|---|---|
| `sector_classify.py` | **Task A** | LLM-assisted title classification. Batches of 20, atomic per-batch checkpoint, resumable, visible heartbeat. No Supabase/Falkor writes. |
| `apply_sector_reclassification.py` | **Task E** (not yet built) | Applies operator-approved proposal: updates `documents.tema` + nulls `doc_fingerprint` so the next additive run regenerates chunks/edges with the new topic. |
| `README.md` | — | This file. |

## Output locations (per Phase 2.5 spec)

```
artifacts/sector_classification/
├── index.json                                ← per-batch status tracker
├── batches/
│   ├── batch_001.json                        ← one file per 20-doc batch
│   ├── batch_002.json
│   └── ...
└── sector_reclassification_proposal.json     ← final aggregated output
                                                 (for operator review, Task B)
```

After operator review (Task B), a second file is produced:

```
artifacts/sector_reclassification_proposal.approved.json
```

with checksum + `approved_by` + `approved_at` fields, which gates
the real write step (`apply_sector_reclassification.py`).

## Durability contract

Same philosophy as `scripts/launch_batch.sh` (see v3 §5 Phase 3):

1. **Per-batch atomic checkpoint** before any external call — temp+rename.
2. **Resume-aware** — on restart, skip batches already marked `status=done`.
3. **SIGINT-safe** — interrupt flips in-flight batch to `status=interrupted`
   so a resume run retries it cleanly.
4. **Failed batch doesn't block others** — a failure records `status=failed`
   and the loop continues; operator re-runs to retry.

If a batch fails, only that ~20-doc slice replays. Prior batches are
written in stone and their results are preserved in
`artifacts/sector_classification/batches/batch_NNN.json`.

## Typical session

```bash
set -a; source .env.local; set +a      # GEMINI_API_KEY

PYTHONPATH=src:. uv run python \
  scripts/monitoring/monitor_sector_reclassification/sector_classify.py \
  --manifest artifacts/fingerprint_bust/<latest>_probe_otros_sectoriales.json

# Stdout shows a heartbeat block after every batch:
#   ────────────────────────────────────────────────────────────────
#   [sector_classify] batch 12/26 finished · 3:47:12 PM Bogotá
#     ██████████████░░░░░░░░░░░░░░░░  46.2%   240/510 docs
#     avg/batch: 18.3s   ETA: 4.3 min → 3:51 PM
#     running cost estimate: $0.042 USD
#     errors so far: 0
#     top proposed new sectors:   sector_salud=23, sector_educacion=19, sector_utilities=15, …
#     top migrate-to targets:     laboral=8, procedimiento_tributario=6, sagrilaft_ptee=4, …
#   ────────────────────────────────────────────────────────────────

# If interrupted (Ctrl-C, network blip, box reboot):
#   same command above — skips done batches, retries the rest.
```

## Not in this folder

These live elsewhere because they serve different jobs:

- **Detached launchers** (`launch_batch.sh`, `launch_phase9a.sh`, …) → `scripts/`
- **Heartbeat renderer** (`ingest_heartbeat.py`) → `scripts/monitoring/`
- **Topic-batch pipeline** (`fingerprint_bust.py`, `validate_batch.py`,
  `run_topic_backfill_chain.sh`) → `scripts/monitoring/monitor_ingest_topic_batches/`
