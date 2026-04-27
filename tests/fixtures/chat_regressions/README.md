# Chat regression fixtures — Phase 7 post-activation gate

**⚠️ Product review required before firing Phase 7.** These 10 JSON fixtures
are the regression suite the SUIN production-push orchestrator
(`scripts/ingestion/fire_suin_cloud.sh`) runs after the activation flip. A failure
auto-rolls back the flip.

## Coverage (per `docs/next/suin_harvestv1.md` Phase 0 deliverable #2)

- **3 tax** questions hitting ET articles modified post-2012
  (`tax_et_*_modified.json`)
- **3 labor** questions hitting CST articles changed by Ley 2466/2025
  (`labor_cst_*_reforma_2466.json`)
- **2 cross-domain** questions on parafiscales exoneración (ET art 114-1)
  (`cross_parafiscales_*.json`)
- **2 derogation** questions exercising vigencia flagging
  (`derogated_*.json`)

## Fixture shape

Each JSON carries:
- `id` — stable identifier
- `question` — user-visible prompt in Spanish
- `expected_contains` — list of substrings the answer must contain
- `expected_flags` — structural expectations (e.g. `vigencia_flag_present`,
  `sentencia_cited`)
- `notes` — human context for reviewers

## Runtime contract

`tests/fixtures/chat_regressions/test_regressions.py` loads every `*.json`
in this directory and validates shape at `make test-batched` time. The
actual answer-generation gate runs inside `fire_suin_cloud.sh` and requires
the full cloud stack — do not couple it to the unit-test suite.
