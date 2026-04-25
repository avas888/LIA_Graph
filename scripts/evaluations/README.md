# A/B retrieval evaluation — panel handoff

## What this is

We changed how the graph half of Lia's retrieval works (v5 TEMA-first —
`docs/next/ingestionfix_v5.md`). This evaluation compares 30 answers
produced with the old path vs the new path so an external panel of
accountants can judge whether the change is a win.

The decision outcome drives whether `LIA_TEMA_FIRST_RETRIEVAL` flips from
`shadow` (default in dev/staging, no user-visible change) to `on`
(TEMA-first actually steers the served answer).

See `docs/done/quality_tests/evaluacion_ingestionfixtask_v1.md` for the full
plan (§0 cold-start briefing onward) and state ledger.

## What's in `artifacts/eval/`

| File | Purpose |
|---|---|
| `ab_comparison_<ts>_<tag>.jsonl` | One JSON row per question, carrying both mode answers + diagnostics. Source of truth. |
| `ab_comparison_<ts>_<tag>_manifest.json` | Run metadata — start/end times (Bogotá + UTC), git sha, question counts, pre-run Falkor baseline. |
| `ab_comparison_<ts>_<tag>.md` | **Panel-reviewable markdown.** Render of the JSONL. This is the file the panel scores. |
| `falkor_baseline_v5.json` | Falkor state captured just before the run — used by the manifest for deterministic comparison. |

## How the panel scores

1. Open the `.md` file.
2. Skim the **Panel instructions** block at the top.
3. For each of the 30 questions:
   - Read the question + sub-questions (if `type: M`).
   - Read the **`[PRIOR MODE]`** answer block (legacy retrieval baseline).
   - Read the **`[NEW MODE]`** answer block (TEMA-first retrieval).
   - Fill the `verdict:` YAML line with ONE of:
     - `new_better` — new-mode answer is materially better
     - `prior_better` — prior-mode answer is materially better
     - `tie` — equivalent in usefulness
     - `both_wrong` — neither answers correctly
     - `need_clarification` — question ambiguous / out of scope
   - Optionally add a one-paragraph `notes:`.

**Do NOT edit** the answer blocks, diagnostics, or question headers. The
operator aggregates verdicts verbatim.

## How to return the scored file

Save the edited `.md`, commit it back (same filename OR a
`*_scored.md` copy), or email/share it to the operator who launched the
run. Operator fills the `## Aggregate` block at the bottom and applies
the go/no-go rule.

## Go/no-go rule (operator reference)

Aggregated across all 30 verdicts:

- **Flip to `on`**: `new_better + tie ≥ 24/30` AND `prior_better ≤ 3/30` AND `both_wrong ≤ 3/30`.
- **Hold**: `prior_better` between 4–8, OR `both_wrong > 3`. Investigate specific losing qids; patch retriever before re-running.
- **Rollback**: `prior_better ≥ 9/30`. Revert `scripts/dev-launcher.mjs` default from `shadow` to `off`.

## How to re-run a question (operator)

If the panel flags `need_clarification` on multiple questions, or a
question's answer looks like it came from a transient network error,
re-run just that subset:

```bash
cd /Users/ava-sensas/Developer/Lia_Graph
# Drop the bad qid rows from the .jsonl (hand-edit or python one-liner),
# then resume:
set -a; source .env.staging; set +a
export FALKORDB_TIMEOUT_SECONDS=15   # gives large-TEMA topics (iva/laboral) headroom
PYTHONPATH=src:. uv run --group dev python \
  scripts/evaluations/run_ab_comparison.py \
  --gold evals/gold_retrieval_v1.jsonl \
  --output-dir artifacts/eval \
  --manifest-tag <same-tag-as-original> \
  --target production \
  --falkor-baseline artifacts/eval/falkor_baseline_v5.json \
  --resume <path to existing .jsonl>
```

Then re-render the `.md`:

```bash
PYTHONPATH=src:. uv run python scripts/evaluations/render_ab_markdown.py \
  --jsonl <.jsonl> --manifest <_manifest.json> --output <.md>
```

## How to run the harness from scratch (engineer)

```bash
cd /Users/ava-sensas/Developer/Lia_Graph
set -a; source .env.staging; set +a
export FALKORDB_TIMEOUT_SECONDS=15
# (optional) capture a fresh Falkor baseline — see §4 pre-flight in the plan doc.
PYTHONPATH=src:. uv run --group dev python \
  scripts/evaluations/run_ab_comparison.py \
  --gold evals/gold_retrieval_v1.jsonl \
  --output-dir artifacts/eval \
  --manifest-tag v5_tema_first_vs_prior_live \
  --target production \
  --falkor-baseline artifacts/eval/falkor_baseline_v5.json
```

Detached + heartbeat recipe: see
`docs/done/quality_tests/evaluacion_ingestionfixtask_v1.md §5 Phase 4`.

## Known caveats

- Answers can be byte-identical for some questions even when TEMA-first
  fires, because LLM polish is stochastic AND because some queries route
  to subtopics that Falkor doesn't carry TEMA edges for (top-level only
  today). Panel should focus on answers that materially differ; ties are
  fine.
- `retriever_falkor.py` emits `tema_first_mode` + `tema_first_anchor_count`
  in its local diagnostics, but the orchestrator curates the final
  response.diagnostics to a fixed key set that doesn't carry these. The
  JSONL row's `env_flag_value` is the authoritative per-row signal of
  which mode ran. `logs/events.jsonl` entries named
  `retrieval.tema_first.live` / `retrieval.tema_first.shadow` are the
  richer audit source.
- Falkor default socket timeout is 3s, tight for large TEMA fan-outs
  like iva (949 edges) or laboral (64 edges). Set
  `FALKORDB_TIMEOUT_SECONDS=15` before launching to avoid transport
  timeouts on the TEMA-first Cypher.

## Contact

- Engineer who ran the harness: see `git_commit_sha` in the manifest +
  `git log` on `feat/evaluacion-ingestionfixtask-v1-ab-harness`.
- Plan doc: `docs/done/quality_tests/evaluacion_ingestionfixtask_v1.md`.
