# Batched test runner with heartbeat (rebuild + protocol)

**Source:** Operator directive 2026-04-27 night during the v3 implementation
session: *"all tests should use a runner with heartbeat and batched (we have
such runners in repo, look for them) enforce this for the totality of the
activity"*. The `Makefile` referenced `scripts/run_tests_batched.py` but the
file was missing. We rebuilt it.

## What the runner does

`scripts/run_tests_batched.py`:

- Discovers all `test_*.py` files under `tests/` (and optionally
  `tests/integration/` when `--include-integration` is set).
- Splits them into N batches (default 120 from the Makefile).
- Runs each batch in its own `pytest` subprocess with
  `LIA_BATCHED_RUNNER=1` exported (the conftest guard envisioned in
  CLAUDE.md will respect this).
- Emits a per-batch heartbeat line in Bogotá AM/PM (per the
  `feedback_time_format_bogota` memory).
- Detects stalled batches (wall > `--max-batch-mult` × median of priors,
  floor 60s) and kills them; the runner re-runs each file individually
  in `--verbose` mode to isolate the culprit.
- Coverage gate: `--cov` enables `--cov=src/lia_graph` with append; final
  `coverage report` parsed for the TOTAL %, gated on `--fail-under`.
- Returns:
  - 0 when every batch passed and coverage ≥ `--fail-under`.
  - 1 when any batch failed.
  - 2 when a batch was killed for stalling.
  - 3 when coverage gated.

## Two pytest gotchas the rebuild had to navigate

### (a) `pytest -q` doesn't print a summary line in non-tty captured mode

The first version of the runner parsed `pytest -q` output to count
passed/failed/skipped. Captured via `subprocess.run(capture_output=True)`,
`-q` mode emits dots + `[100%]` and **nothing else** — no `"X passed in
Ys"` line. Result: every batch reported `passed=0 failed=0 rc=0`.

**Fix:** pass `-r fEs --tb=line -o addopts=` to override the project's
`addopts = "--tb=short -q"` config, which forces a regular summary line
the parser can read.

### (b) The Makefile's `test-batched` target referenced a missing file

`Makefile`:

```make
test-batched:
	PYTHONPATH=src:. uv run python scripts/run_tests_batched.py --batches $(BATCH_COUNT) --cov --fail-under 90
```

But `scripts/run_tests_batched.py` did not exist in the repo. Either
deleted by accident or never landed. The rebuild restored it with the
discipline CLAUDE.md describes (batch + stall + heartbeat).

## Discipline going forward

For every test invocation in an active development session:

- **Single targeted file**: `pytest tests/test_X.py -q` is fine ad-hoc.
- **A sub-fix's full surface** (≥ 5 files, or unit + integration combined):
  `scripts/run_tests_batched.py --batches N --filter <substrings>`.
- **Full project suite (>20 test files)**: `make test-batched`. The
  `LIA_BATCHED_RUNNER=1` guard in the project conftest blocks naïve
  pytest invocations of the full suite to avoid OOM.

## Bogotá AM/PM heartbeat shape (sample)

```
[run_tests_batched] 2026-04-27 02:27:15 AM Bogotá — 12 files in 6 batches (~2 per batch)
[run_tests_batched] 2026-04-27 02:27:15 AM Bogotá — batch   1/6 (2 files,   0.2s) — passed=87 failed=0 skipped=0 rc=0
[run_tests_batched] 2026-04-27 02:27:16 AM Bogotá — batch   2/6 (2 files,   0.2s) — passed=13 failed=0 skipped=0 rc=0
...
[run_tests_batched] DONE 2026-04-27 02:27:16 AM Bogotá — batches=6 passed=239 failed=0 skipped=0 failed_batches=0 coverage=n/a
```

Each batch line is one stdout write (heartbeat-friendly when piped to
`logs/test_run.log`). The final `DONE` line is machine-parseable for
external monitoring.
