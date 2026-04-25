# subtopic_generationv1 — E2E runbook

> This runbook drives the **full-corpus** run of Phases 2–6 against real
> `knowledge_base/` + the live Gemini Flash adapter. It is the
> stakeholder-facing recipe that produces the first curated
> `config/subtopic_taxonomy.json`. Capture evidence at each step under
> `tests/manual/subtopicv1_evidence/<run-timestamp>/`.

## 0. Pre-flight

- [ ] Working tree on `feat/suin-ingestion`, clean of unrelated staged edits.
- [ ] Phase 1–7 tests green:
  ```bash
  PYTHONPATH=src:. uv run --group dev pytest \
    tests/test_ingest_classifier.py \
    tests/test_corpus_walk.py \
    tests/test_collect_subtopic_candidates.py \
    tests/test_mine_subtopic_candidates.py \
    tests/test_ui_subtopic_controllers.py \
    tests/test_promote_subtopic_decisions.py \
    tests/test_subtopic_observability.py -q
  ```
  Expected: 105+/105+ green.
- [ ] Frontend vitest for the curation surface:
  ```bash
  cd frontend && npx vitest run tests/subtopicCuration.test.ts tests/atomicDiscipline.test.ts
  ```
- [ ] `GEMINI_API_KEY` exported in the shell — collection pass is LLM-driven.
- [ ] Cost budget approved (§0.7 of the plan: ~$6–16 one-time; 2× guardrail kicks in per §0.5 item 4).
- [ ] Stakeholder sign-off obtained for Phase 6 promotion — curated taxonomy
      lands in `config/` only with explicit approval (plan §0.11).

Create the evidence directory:
```bash
RUN_TS=$(date -u +%Y%m%dT%H%M%SZ)
EVIDENCE=tests/manual/subtopicv1_evidence/${RUN_TS}
mkdir -p "${EVIDENCE}"
```

## 1. Phase 2 — corpus-wide collection pass

**Scoped pilot first.** The plan's open Question 10 defers the "full 1246 docs
vs subset" call to this runbook. Pilot with `--only-topic laboral` to validate
the flow end-to-end cheaply (~80 docs × $0.004 = ~$0.35):

```bash
make phase2-collect-subtopic-candidates ONLY_TOPIC=laboral
```

Expected output:
- `artifacts/subtopic_candidates/collection_<UTC>.jsonl` with ~80 rows, each
  carrying `autogenerar_label` + `autogenerar_rationale`.
- `artifacts/subtopic_candidates/_latest.json` pointer.
- Terse stdout summary: `collect: docs=N failed=0 llm_calls=N elapsed=Ns`.

**Capture:**
- [ ] `cp artifacts/subtopic_candidates/collection_*.jsonl ${EVIDENCE}/phase2-pilot-collection.jsonl`
- [ ] `cp artifacts/subtopic_candidates/_latest.json ${EVIDENCE}/phase2-pilot-latest.json`
- [ ] Sample 5 rows; confirm labels look like accountant mental models
      (`"presuncion_costos_independientes"`, not `"laboral"`).
- [ ] If labels look degenerate (empty strings, `"null"`, the prompt text
      verbatim), STOP and open an issue — do not burn the full-corpus budget.

**Full corpus (after pilot validates):**
```bash
make phase2-collect-subtopic-candidates
```

This runs ~1246 docs at ≤60 rpm → ~21 min serial, plan for ~35 min with retries.
If it's interrupted, resume with:
```bash
make phase2-collect-subtopic-candidates RESUME_FROM=artifacts/subtopic_candidates/collection_<UTC>.jsonl
```

**Capture:**
- [ ] `cp artifacts/subtopic_candidates/collection_*.jsonl ${EVIDENCE}/phase2-full-collection.jsonl`
- [ ] Row count == `docs_processed` from `_latest.json`.
- [ ] Record total LLM cost (from Gemini console) → `${EVIDENCE}/cost_report.md`.

## 2. Phase 3 — mine collection JSONL(s)

```bash
make phase3-mine-subtopic-candidates INPUT='artifacts/subtopic_candidates/collection_*.jsonl'
```

Expected output:
- `artifacts/subtopic_proposals_<UTC>.json` with `proposals`, `singletons`,
  and `summary` blocks.
- Terse `mine: proposals=N singletons=N output=<path>`.

**Capture:**
- [ ] `cp artifacts/subtopic_proposals_*.json ${EVIDENCE}/phase3-proposals.json`
- [ ] Assert: every parent_topic with ≥ 5 docs in the collection JSONL produces
      at least one proposal. Grep:
      ```bash
      jq '.summary' artifacts/subtopic_proposals_*.json
      jq '.proposals | keys' artifacts/subtopic_proposals_*.json
      ```
- [ ] If a parent_topic is missing, rerun with a lower threshold:
      `make phase3-mine-subtopic-candidates INPUT=... CLUSTER_THRESHOLD=0.70`

## 3. Phase 4 + 5 — curate via the admin UI

**Start local server:**
```bash
npm run dev
```

**Navigate:** `http://127.0.0.1:8787/` → Ingesta → **Sub-temas** tab.

**Login:** `admin@lia.dev` / `Test123!`.

**Per-column workflow (one parent_topic at a time):**
1. For each proposal card in `laboral`:
   - [ ] Click **Ver evidencia** to confirm the doc set matches the proposed label.
   - [ ] If the label is a clean subtopic → **Aceptar**.
   - [ ] If label is correct but shaped wrong → **Renombrar** (set new label and/or key).
   - [ ] If this duplicates another proposal within the same parent → **Fusionar**.
   - [ ] If this cluster conflates two distinct concepts → **Dividir** (comma-separated aliases).
   - [ ] If this is noise / garbage → **Rechazar** (reason required).
2. After each decision:
   - Card visually dims + banner shows the action.
   - `artifacts/subtopic_decisions.jsonl` gains a row.
   - Sidebar "Taxonomía actual" is unchanged (sidebar reflects the promoted file, not decisions).

**Target:** decide every proposal with `evidence_count ≥ 3`. Singletons can
be left for a later pass.

**Capture:**
- [ ] `cp artifacts/subtopic_decisions.jsonl ${EVIDENCE}/phase4-decisions.jsonl`
- [ ] Record time spent + decision counts: accept/reject/merge/rename/split.

## 4. Phase 6 — promote to taxonomy

**Dry-run first:**
```bash
make phase2-promote-subtopic-taxonomy DRY_RUN=1 VERSION=$(date -u +%Y-%m-%d)-v1
```

Review the diff printed to stdout. If it matches your decisions, continue.

**Commit (real write to `config/`):**
```bash
make phase2-promote-subtopic-taxonomy VERSION=$(date -u +%Y-%m-%d)-v1
```

Expected: `config/subtopic_taxonomy.json` lands with the curated entries,
sorted alphabetically per parent_topic, then by `evidence_count` desc then
`key` asc.

**Capture:**
- [ ] `cp config/subtopic_taxonomy.json ${EVIDENCE}/phase6-taxonomy.json`
- [ ] `jq '.subtopics | to_entries | map({parent: .key, n: (.value | length)})' config/subtopic_taxonomy.json > ${EVIDENCE}/phase6-summary.json`

## 5. Phase 7 — trace audit

Confirm the observability test still asserts every documented event fired:
```bash
PYTHONPATH=src:. uv run --group dev pytest tests/test_subtopic_observability.py -v
```

Spot-check the real log:
```bash
grep -c '"event_type": "subtopic.' logs/events.jsonl
```

**Capture:**
- [ ] `tail -300 logs/events.jsonl | grep '"subtopic.' > ${EVIDENCE}/phase7-trace-tail.jsonl`

## 6. Close-out

- [ ] Commit `config/subtopic_taxonomy.json` with message
      `feat(subtopic-v1): promote taxonomy v<date>`.
- [ ] Flip `docs/done/next/subtopic_generationv1.md` §2 status from `EXECUTING` to `COMPLETE`.
- [ ] Move the plan doc to `docs/done/subtopic_generationv1.md`.
- [ ] Follow-up `ingestfixv2.md` pre-conditions now satisfied — schedule its kickoff.

## Failure modes

- **Gemini rate limit (`429`)**: the collection script honors `--rate-limit-rpm`.
  If the default 60 is still too aggressive, drop it via `RATE_LIMIT_RPM=30`.
- **Label cardinality explosion** (> 300 unique normalized slugs in one parent):
  tighten the threshold (`CLUSTER_THRESHOLD=0.70`) or raise `MIN_CLUSTER_SIZE` to 5.
- **Curator fatigue**: decisions JSONL is append-only; resume curation
  mid-flow. Phase 6 promotion works on whatever has been decided.
- **Wrong taxonomy shipped**: `config/subtopic_taxonomy.json` is regenerated
  from the decisions JSONL. Edit/append decisions, re-run Phase 6.

## Success criteria (minimum)

Per plan §14:
1. `config/subtopic_taxonomy.json` — committed, version-stamped.
2. `artifacts/subtopic_candidates/collection_<UTC>.jsonl` — one row per processed doc.
3. `artifacts/subtopic_proposals_<UTC>.json` — mining output.
4. `artifacts/subtopic_decisions.jsonl` — full audit trail.
5. `tests/manual/subtopicv1_evidence/<run>/` — evidence bundle.
6. Change-log entry in `docs/guide/orchestration.md`.
7. `docs/next/ingestfixv2.md` updated to cite the seed file.
