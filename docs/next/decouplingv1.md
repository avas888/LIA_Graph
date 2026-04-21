# Decoupling v1 — Executable State-Aware Plan

**Last edited:** 2026-04-20 (plan authored)
**Execution owner:** autonomous Claude session (post-approval)
**Goal:** graduate the final two files above 1000 LOC — `src/lia_graph/ui_server.py` (1669 → ~150 LOC) and `frontend/src/features/ops/opsIngestionController.ts` (2327 → ~100 LOC) — without regressing the served runtime.

> This document is both a **plan** and a **work ledger**. Every phase has a status block that MUST be updated in-place as work progresses. If execution is interrupted, the state of this file is the resumption pointer — read the dashboard, find the first non-`DONE` phase, inspect its `State Notes`, and resume from the last checkmark.

---

## 1. Executive Summary

**Problem.** Two files still sit above the repo's informal 1000-LOC graduation threshold. Both are the HTTP and UI edge of the served runtime (`ui_server.py` is the Python edge; `opsIngestionController.ts` is the frontend Ops console). The rest of the granularize-v2 campaign graduated 11 of 13 files across rounds `v2026-04-20-ui2` through `v2026-04-20-ui13`; these two were deferred because they're genuinely hard — `ui_server.py` because the 1019-LOC handler class references ~150 module-level names, and `opsIngestionController.ts` because a single 620-LOC `bindEvents` closure entangles every inner function.

**Strategy.** Split each host into focused siblings along natural concern boundaries, preserving the public entrypoints (`lia_graph.ui_server:main` and `createOpsIngestionController`). For the Python side, **extract constants and module-level helpers first** — this eliminates the circular-import problem the original diagnostic tried to solve with a lazy `_h()` accessor (see §4 Architectural Decisions). For the TypeScript side, fix the 11 pre-existing ops test failures first to restore a green baseline, then peel factories off one at a time.

**Order.** Python first (5 phases), then TS stabilization (1 phase) + TS refactor (6 phases), then final verification (1 phase). Python-first because the baseline is green, the surface is smaller, and the architectural pattern is cleaner once locked in.

**Non-goals.** No behavior changes. No new features. No env-flag changes. No changes to `pyproject.toml [project.scripts]` entries. No changes to the public signature of `createOpsIngestionController`. The refactor is pure mechanical decomposition.

---

## 2. State Dashboard (update in-place during execution)

**Meta**

| Field | Value |
|---|---|
| Plan status | ☐ DRAFT · ☐ APPROVED · ☐ EXECUTING · ☐ COMPLETE |
| Current phase | *(updated at each phase entry)* |
| Last completed phase | *(updated at each phase exit)* |
| Blockers | *(free text; blank when green)* |
| Working tree | *(clean / dirty — update before each phase)* |

**Progress (update LOC on exit of every phase)**

| File | Baseline LOC | Current LOC | Target LOC |
|---|---|---|---|
| `src/lia_graph/ui_server.py` | 1669 | 1669 | ≤ 300 |
| `frontend/src/features/ops/opsIngestionController.ts` | 2327 | 2327 | ≤ 150 |

**Test baseline (update after Phase 0)**

| Suite | Baseline | Current |
|---|---|---|
| Python (`make test-batched`) | 401 pass / 2 pre-squash fail | *(set in Phase 0)* |
| Frontend health (`npm test`) | 10 pass | *(set in Phase 0)* |
| Frontend ops (`npm run test:all src/features/ops`) | 85 pass / 11 fail | *(set in Phase 0)* |

**Phase ledger** — tick each box as it happens. Allowed statuses: `NOT_STARTED`, `IN_PROGRESS`, `PASSED_TESTS`, `COMMITTED`, `DONE`, `BLOCKED`.

| # | Phase | Status | Host LOC after | Commit SHA |
|---|---|---|---|---|
| 0 | Pre-flight baseline capture | NOT_STARTED | — | — |
| 1 | `ui_server`: extract constants + module helpers | NOT_STARTED | 1669 → ≤1300 | — |
| 2 | `ui_server`: extract handler base (plumbing/auth/send/rate-limit) | NOT_STARTED | ≤1300 → ≤800 | — |
| 3 | `ui_server`: extract handler dispatch (GET/POST/PATCH/etc.) | NOT_STARTED | ≤800 → ≤300 | — |
| 4 | `ui_server`: extract CLI (`run_server`/`parser`/`main`) | NOT_STARTED | ≤300 → ≤200 | — |
| 5 | `ui_server`: graduation verification (smoke all three run modes) | NOT_STARTED | unchanged | — |
| 6 | `ops`: stabilize 11 pre-existing test failures (prereq) | NOT_STARTED | unchanged | — |
| 7 | `ops`: extract API factory | NOT_STARTED | 2327 → ≤2100 | — |
| 8 | `ops`: extract Upload factory | NOT_STARTED | ≤2100 → ≤1800 | — |
| 9 | `ops`: extract Intake factory (owns local state) | NOT_STARTED | ≤1800 → ≤1500 | — |
| 10 | `ops`: extract AutoPilot factory | NOT_STARTED | ≤1500 → ≤1300 | — |
| 11 | `ops`: extract Renderers factory (graduation) | NOT_STARTED | ≤1300 → ≤700 | — |
| 12 | `ops`: extract Events binder + Context object | NOT_STARTED | ≤700 → ≤150 | — |
| 13 | Final verification + orchestration changelog publish | NOT_STARTED | unchanged | — |

---

## 3. Execution Protocol (rules for updating this file during work)

These rules make the doc self-healing. Every autonomous run reads them before doing anything.

1. **Before starting a phase**: edit the phase's Status block to `IN_PROGRESS`, stamp the `Entered at` timestamp, and confirm all Pre-conditions are ticked. If any pre-condition is unticked, STOP and report.
2. **As work progresses within a phase**: tick each Work item as it completes; append a short line to `State Notes` for anything non-obvious (unexpected test failure, file not found, a different LOC than predicted, etc.).
3. **Before committing**: all Tests in the phase must be green. Record exact test-run output summaries (e.g., `401 passed, 2 failed (pre-existing)`) in `State Notes`.
4. **On commit**: record the commit SHA in the phase ledger row and in the phase's own `Commit SHA` field. Transition to `COMMITTED`.
5. **On phase exit**: run the Post-conditions check, add the orchestration changelog entry (Phase 13 batches all entries if preferred, but each phase writes its draft entry in `Changelog Draft`), update the Progress table's `Current LOC` values, set Status to `DONE`, stamp `Exited at`.
6. **On blocker**: set Status to `BLOCKED`, write the blocker summary in `State Notes`, update the dashboard's `Blockers` field. Do NOT proceed to the next phase.
7. **On resume (new session)**: first action is to read this doc top-to-bottom, find the first phase with Status `IN_PROGRESS` or `BLOCKED`, read its State Notes, `git status` and `git log -5`, then continue from the first unticked Work item.
8. **Commit hygiene**: one commit per phase. Commit message template is in each phase. Never amend. Never force-push.
9. **Test hygiene**: run targeted (phase-specific) tests first to fail fast; only run full suite at phase exit.
10. **Do not batch phases**: if a phase completes faster than expected, still commit and close it before starting the next. The state-aware protocol depends on per-phase atomicity.

---

## 4. Architectural Decisions (recorded)

### 4.1 Python: constants-first extraction, not lazy-host mixin

The original diagnostic (Appendix A §1.6) proposed splitting `LiaUIHandler` into mixins and using a lazy `_h()` accessor to reach ~150 module-level names. That approach works but introduces two problems: (a) AST-rewrite tooling is required to safely prefix names without corrupting dict keys and dotted accesses, and (b) every new module-level name added after the split risks `NameError` at request time unless an allowlist is maintained.

**Chosen alternative — constants-first.** Extract the ~50 locally-defined names (paths, flags, regex, frozen data, module helpers) to two new modules **before** splitting the handler:

- `src/lia_graph/ui_server_constants.py` — paths, public-mode flags, regex, frozen data (~250 LOC, no logic).
- `src/lia_graph/ui_server_helpers.py` — `_env_truthy`, `_emit_audit_event`, `_emit_chat_verbose_event`, `_best_effort_git_commit`, `_build_info_payload`, `_build_reload_snapshot`, `_start_reload_watcher` (~150 LOC, imports constants).

Once these exist, the handler-splitting siblings can simply `from .ui_server_constants import *` and `from .ui_server_helpers import *`, plus import the ~44 original dependency modules directly (same way `ui_server.py` does today). **No lazy imports. No AST rewrites. No allowlist.** Circular imports are impossible because neither new module imports `ui_server`.

The ~60 "import-from-dependency" callables (e.g., `save_feedback`, `run_pipeline_c`, `AuthContext`) are imported identically in each handler sibling — explicit, obvious, greppable. Some duplication of import lines across `ui_server_handler_base.py` and `ui_server_handler_dispatch.py`, but each file only imports what *its* methods actually use.

Trade-offs:
- **Pro:** clean, explicit, no magic. New names added to any sibling follow the normal Python import contract.
- **Pro:** each phase is a self-contained extraction testable in isolation.
- **Con:** one extra phase (constants extraction) vs. the 5-round plan in the original diagnostic.
- **Con:** import lines duplicated across 2-3 sibling files (~40 lines each).

The con is cosmetic; the pro is structural.

### 4.2 Python: inheritance chain for the split handler class

Even with constants-first, the handler class itself still needs to be split. The chosen chain is:

```
BaseHTTPRequestHandler (stdlib)
    └── LiaUIHandlerBase  (ui_server_handler_base.py)       — plumbing/auth/send/rate-limit (~500 LOC, ~40 methods)
            └── LiaUIHandler  (ui_server_handler_dispatch.py) — verbs + handlers (~500 LOC, ~17 methods)
```

`ui_server.py` after the split just re-exports `LiaUIHandler` for back-compat: `from .ui_server_handler_dispatch import LiaUIHandler`. The MRO resolves correctly (Python C3 linearization handles single-inheritance chains trivially). Pickle-safety is preserved because both classes are module-level.

### 4.3 TypeScript: factory composition with a shared `ctx` object

Follows the existing diagnostic (Appendix B §2.5–2.6). A single `OpsControllerCtx` object carries `dom`, `i18n`, `state`, `stateController`, `withThinkingWheel`, `setFlash`, and `toast`. Each factory (`createOpsApi`, `createOpsUpload`, `createOpsIntake`, `createOpsAutoPilot`, `createOpsRenderers`, plus the `bindOpsEvents` binder) takes `ctx` plus its peer factories.

Controller-local mutable state (`intakeEntries`, `preflightDebounce`, etc.) lives inside `createOpsIntake`'s closure; other factories read via `intake.getIntakeEntries()` getters. No shared mutable reference across factories.

`createOpsIngestionController(options)` becomes a ~100-LOC composer that builds `ctx`, instantiates factories in dependency order, calls `bindOpsEvents`, and returns the same public API the caller (`opsApp.ts`) uses today.

### 4.4 Ordering rationale (Python first, then TS)

- **Python has a green baseline** (401 passing, 2 pre-squash fails that are unrelated). TS has 11 pre-existing fails that must be fixed before regression detection is trustworthy.
- **Python surface is smaller** (5 phases vs. 6 for TS post-stabilization). Finishing Python first lets us retire a changelog entry set (`v2026-04-20-ui14` through `-ui18`) before taking on the bigger TS lift.
- **Confidence compound**: the state-aware protocol is new; shaking it down on the simpler Python work reduces the risk of discovering protocol bugs mid-TS-refactor.

### 4.5 Commit cadence and changelog

- **One commit per phase.** Phase 0 (baseline) and Phase 13 (verification) may produce no code commits if they only update docs.
- **Changelog entries** live in `docs/guide/orchestration.md` under the existing `v<YYYY-MM-DD>-uiN` scheme. Each phase drafts its entry in the phase's `Changelog Draft` block; Phase 13 publishes them in a single docs commit.
- **Mirror updates** required per AGENTS.md: after Phases 5 and 12, update `docs/guide/env_guide.md` (no env change, but LOC references may appear in the mirror table) and `CLAUDE.md` only if architecture changes. No env version bump is required — this refactor is not an env change.

---

## 5. Phases

Each phase uses the template below. Phases reference Appendix A (Python) and Appendix B (TypeScript) for line-level detail — those appendices are the original diagnostic, preserved verbatim.

### Phase template reference

```
Pre-conditions       — checklist of things that must be true before entry
Files to create      — new files with predicted LOC
Files to modify      — existing files with the nature of the change
Work items           — ordered sub-steps to execute
Targeted tests       — fast-feedback tests for this phase's surface
Full-suite tests     — broader sanity tests before commit
LOC target           — expected delta and absolute target for host file
Commit message       — templated
Post-conditions      — checklist for exit
Changelog Draft      — text for orchestration.md
State Notes          — updated live during execution
```

---

### Phase 0 — Pre-flight baseline capture

**Status:** ☐ NOT_STARTED ☐ IN_PROGRESS ☐ PASSED_TESTS ☐ COMMITTED ☐ DONE ☐ BLOCKED
**Entered at:** _________  **Exited at:** _________  **Commit SHA:** _________ (usually none)

**Pre-conditions:**
- [ ] User has approved this plan (Plan status = `APPROVED`)
- [ ] Branch is `feat/suin-ingestion` or a new decoupling branch cut from it
- [ ] Working tree is clean (commit or stash any residual work first)

**Files to modify:** `docs/next/decouplingv1.md` (this file) — update Dashboard baseline numbers.

**Work items:**
- [ ] Run `wc -l src/lia_graph/ui_server.py frontend/src/features/ops/opsIngestionController.ts` → record in Dashboard
- [ ] Run `make test-batched 2>&1 | tail -30` → record pass/fail counts in Dashboard
- [ ] Run `cd frontend && npm test 2>&1 | tail -20` → record pass/fail in Dashboard
- [ ] Run `cd frontend && npx vitest run --config ./vitest.config.ts src/features/ops 2>&1 | tail -30` → record ops pass/fail
- [ ] Record the list of 11 failing ops tests verbatim in Phase 6's `State Notes`
- [ ] `git log -1 --format="%H %s"` → record starting commit SHA in Dashboard

**Targeted tests:** none (read-only baseline).
**Full-suite tests:** see Work items above.
**LOC target:** no change.

**Commit message:** none (no code changes).

**Post-conditions:**
- [ ] Dashboard's `Current LOC` and `Test baseline.Current` cells filled in
- [ ] Phase 6's `State Notes` has the 11-test failure list
- [ ] Dashboard `Last completed phase` = Phase 0

**Changelog Draft:** _(none — Phase 0 is measurement only)_

**State Notes:**
_(fill in during execution — include baseline SHA, exact test numbers, any deltas from the 2026-04-20 diagnostic)_

---

### Phase 1 — `ui_server`: extract constants + module helpers

**Status:** ☐ NOT_STARTED ☐ IN_PROGRESS ☐ PASSED_TESTS ☐ COMMITTED ☐ DONE ☐ BLOCKED
**Entered at:** _________  **Exited at:** _________  **Commit SHA:** _________

**Pre-conditions:**
- [ ] Phase 0 is `DONE`
- [ ] `git status --short` empty
- [ ] Targeted tests green: `uv run pytest tests/test_ui_server_http_smokes.py tests/test_ui_ingestion_controllers.py tests/test_normativa_surface.py -q`

**Files to create:**
1. `src/lia_graph/ui_server_constants.py` (~250 LOC)
   - Contents: lines 258-430 of current `ui_server.py` — paths (`WORKSPACE_ROOT`, `UI_DIR`, `FRONTEND_DIR`, `INDEX_FILE_PATH`, `FORM_GUIDES_ROOT`, and 25+ other paths), public-mode flags (`PUBLIC_MODE_ENABLED`, `PUBLIC_TRUST_PROXY`, etc., 9 names), regex (`_CHAT_RUN_ROUTE_RE`, `_ET_ARTICLE_DOC_ID_RE`, etc., 13 regex), frozen data (`_GENERIC_SOURCE_TITLES`, `_SUMMARY_RISK_HINTS`, `_EXPERT_SUMMARY_SKIP_EXACT`, `_DEFAULT_CHAT_LIMITS`, `_ALLOWED_*` ×8, `_RELOAD_WATCH_SUFFIXES`), plus `SERVER_STARTED_AT` and `_SUSPENDED_CACHE` + its lock/TTL.
   - Depends on: stdlib only + `pathlib`, `threading`, `time`, `re`, optionally `os.environ` for flag reads.
   - Note: `_SUSPENDED_CACHE`, `_SUSPENDED_CACHE_LOCK`, `_SUSPENDED_CACHE_TTL` are shared mutable state — confirm single-module ownership (they're only mutated in `_is_user_suspended` at line 1057 which stays on the class; class reads them via `ui_server_constants._SUSPENDED_CACHE`).

2. `src/lia_graph/ui_server_helpers.py` (~150 LOC)
   - Contents: lines 431-514 of current `ui_server.py` — `_env_truthy`, `_emit_audit_event`, `_emit_chat_verbose_event`, `_best_effort_git_commit`, `_build_info_payload`, `_build_reload_snapshot`, `_start_reload_watcher`.
   - Depends on: `ui_server_constants` (for `WORKSPACE_ROOT`, `SERVER_STARTED_AT`, `_RELOAD_WATCH_SUFFIXES`), plus `instrumentation.emit_event`, `instrumentation.emit_reasoning_event` for event emitters.

3. `tests/test_ui_server_constants_helpers.py` (~40 LOC)
   - Identity-guard test: assert every name exported from `ui_server_constants` and `ui_server_helpers` is importable and has the expected type (path objects are `Path`, regex are `re.Pattern`, etc.).
   - Re-export test: `from lia_graph.ui_server import WORKSPACE_ROOT, _emit_audit_event` — confirms `ui_server.py` still exposes them for any downstream consumer.

**Files to modify:**
1. `src/lia_graph/ui_server.py`:
   - Delete lines 258-514 (the constants + helpers blocks).
   - Replace with: `from .ui_server_constants import *  # noqa: F401, F403` and `from .ui_server_helpers import *  # noqa: F401, F403` (wildcard imports preserve downstream `from lia_graph.ui_server import WORKSPACE_ROOT` compatibility).
   - Alternative to wildcard: explicit re-export list — more verbose but greppable. Use wildcard here; the `__all__` in the new modules controls visibility.
   - Expected LOC after: 1669 − (514 − 258 + 1) = **~1412 LOC**.

**Work items:**
- [ ] Draft `ui_server_constants.py` by copy-paste from `ui_server.py:258-430`, plus `_SUSPENDED_CACHE*` from wherever they live. Add `__all__`.
- [ ] Draft `ui_server_helpers.py` by copy-paste from `ui_server.py:431-514`. Replace any bare references to constants (e.g., `WORKSPACE_ROOT` inside `_build_info_payload`) with `from .ui_server_constants import WORKSPACE_ROOT, ...`. Add `__all__`.
- [ ] Update `ui_server.py`: delete the two blocks, add the two wildcard imports.
- [ ] Run `python -c "from lia_graph.ui_server import LiaUIHandler, WORKSPACE_ROOT, _emit_audit_event, main; print('ok')"` — zero-cost import check.
- [ ] Write `tests/test_ui_server_constants_helpers.py`.

**Targeted tests:**
```bash
uv run pytest tests/test_ui_server_constants_helpers.py tests/test_ui_server_http_smokes.py tests/test_ui_ingestion_controllers.py tests/test_normativa_surface.py tests/test_citation_resolution.py tests/test_ui_et_article_extractors.py -q
```

**Full-suite tests:**
```bash
make test-batched
```

**LOC target:** `ui_server.py` ≤ 1420.

**Commit message template:**
```
refactor(ui_server): extract constants + module helpers to siblings

Split ~257 LOC out of ui_server.py into two new modules:
- ui_server_constants.py (paths, flags, regex, frozen data)
- ui_server_helpers.py (emit wrappers, dev-reload wrappers, env reader)

ui_server.py re-exports via wildcard for downstream compat. No behavior
change; this is pure mechanical decomposition to unblock the handler-
class split in the next round.

Host LOC: 1669 → <actual>. See docs/next/decouplingv1.md Phase 1.
```

**Post-conditions:**
- [ ] Both targeted and full suite green
- [ ] `ui_server.py` LOC ≤ 1420
- [ ] Commit created, SHA recorded in ledger
- [ ] `Changelog Draft` filled in below

**Changelog Draft:**
```
| v2026-04-20-ui14 | 2026-04-20 | UI server granularization round 1: extract constants + helpers. Split ui_server.py 1669→1412 via new ui_server_constants.py (paths/flags/regex/frozen data) and ui_server_helpers.py (event emitters + dev-reload wrappers). Re-export via wildcard for downstream compat. NOT an env change. | src/lia_graph/ui_server.py, src/lia_graph/ui_server_constants.py (new), src/lia_graph/ui_server_helpers.py (new), tests/test_ui_server_constants_helpers.py (new) |
```

**State Notes:**
_(fill in during execution — actual LOC count, test pass/fail, any surprises)_

---

### Phase 2 — `ui_server`: extract handler base

**Status:** ☐ NOT_STARTED ☐ IN_PROGRESS ☐ PASSED_TESTS ☐ COMMITTED ☐ DONE ☐ BLOCKED
**Entered at:** _________  **Exited at:** _________  **Commit SHA:** _________

**Pre-conditions:**
- [ ] Phase 1 is `DONE`
- [ ] `ui_server.py` ≤ 1420 confirmed via `wc -l`
- [ ] Working tree clean

**Files to create:**
1. `src/lia_graph/ui_server_handler_base.py` (~550 LOC)
   - Class: `LiaUIHandlerBase(BaseHTTPRequestHandler)` holding the 40 non-dispatch methods from Appendix A §1.2:
     - Request plumbing (7): `_request_origin`, `_allowed_cors_origin`, `_cors_headers`, `_embed_security_headers`, `_start_api_request_log`, `_log_api_response`, `log_message`.
     - Auth + session (7): `_send_auth_error`, `_resolve_auth_context`, `_admin_tenant_scope`, `_resolve_feedback_rating`, `_clarification_scope_key`, `_build_memory_summary`, `_is_user_suspended`.
     - Frontend-compat shims (2): `_handle_chat_frontend_compat_get`, `_handle_chat_frontend_compat_post`.
     - Chat-request lifecycle (4): `_initialize_chat_request_context`, `_persist_user_turn`, `_persist_assistant_turn`, `_persist_usage_events`.
     - HTTP response primitives (7): `_base_security_headers` (staticmethod), `_send_bytes`, `_send_json`, `_send_event_stream_headers`, `_write_sse_event`, `_read_json_payload`.
     - Rate-limit + quotas + public gates (8): `_check_rate_limit`, `_get_trusted_client_ip`, `_hash_public_user_id`, `_check_public_daily_quota`, `_is_public_visitor_request`, `_handle_public_session_post`, `_serve_public_page`.
   - Imports: `from .ui_server_constants import *`, `from .ui_server_helpers import *`, plus the targeted imports from the ~44 original dependency modules (only what this file's methods actually reference — subset of `ui_server.py`'s import block).
   - Sets `server_version = "LIAUI/0.1"` and `protocol_version = "HTTP/1.1"` as class attributes.

2. `tests/test_ui_server_handler_base.py` (~60 LOC)
   - Assert `LiaUIHandlerBase` is importable and subclasses `BaseHTTPRequestHandler`.
   - Assert key methods are present: `_request_origin`, `_resolve_auth_context`, `_send_json`, `_read_json_payload`, `_check_rate_limit`.
   - Assert staticmethod decorator preserved on `_base_security_headers`.
   - Minimal instantiation smoke (may require a dummy socket wrapper — use the same pattern as existing `test_ui_server_http_smokes.py`).

**Files to modify:**
1. `src/lia_graph/ui_server.py`:
   - Delete the 40 methods (lines 576-1085) from the class body.
   - Change class declaration to `class LiaUIHandler(LiaUIHandlerBase):` with `from .ui_server_handler_base import LiaUIHandlerBase` at the imports block.
   - Expected LOC after: ~1412 − 510 (extracted methods) = **~900 LOC**.

**Work items:**
- [ ] Create `ui_server_handler_base.py` with class skeleton + imports.
- [ ] Migrate the 40 methods verbatim (no changes — just move). Confirm no method body references `self.XXX` where `XXX` was on the class and is now missing — if a base method calls a dispatch method it should still work via MRO at runtime.
- [ ] **Manual audit**: grep method bodies for any name that isn't in (stdlib + constants + helpers + the explicit imports). Expected zero hits.
- [ ] Update `ui_server.py` class declaration + import.
- [ ] Run import smoke: `python -c "from lia_graph.ui_server import LiaUIHandler; assert LiaUIHandler.__mro__[1].__name__ == 'LiaUIHandlerBase'; print('ok')"`.
- [ ] Write `tests/test_ui_server_handler_base.py`.

**Targeted tests:**
```bash
uv run pytest tests/test_ui_server_handler_base.py tests/test_ui_server_constants_helpers.py tests/test_ui_server_http_smokes.py tests/test_ui_ingestion_controllers.py tests/test_normativa_surface.py -q
```

**Full-suite tests:**
```bash
make test-batched
```

**Live-server smoke:**
```bash
# In a separate terminal:
LIA_PORT=8787 npm run dev
# Then:
curl -fsS http://127.0.0.1:8787/api/health | jq .
curl -fsS -X OPTIONS http://127.0.0.1:8787/api/chat -o /dev/null -w "%{http_code}\n"
# Expect 200 on health, 204 or 200 on OPTIONS.
```

**LOC target:** `ui_server.py` ≤ 920.

**Commit message template:**
```
refactor(ui_server): extract handler base class

Move 40 non-dispatch methods (request plumbing, auth, response helpers,
rate-limit, quotas, public-mode gates) from LiaUIHandler to a new
LiaUIHandlerBase in ui_server_handler_base.py. LiaUIHandler now
inherits from it; the MRO is
[LiaUIHandler, LiaUIHandlerBase, BaseHTTPRequestHandler, object].

No behavior change. Host LOC: <prev> → <actual>. See
docs/next/decouplingv1.md Phase 2.
```

**Post-conditions:**
- [ ] Targeted + full suite green
- [ ] Live-server smoke passes (health 200, OPTIONS preflight 2xx)
- [ ] `ui_server.py` LOC ≤ 920
- [ ] `LiaUIHandler.__mro__` contains `LiaUIHandlerBase`
- [ ] Commit SHA recorded

**Changelog Draft:**
```
| v2026-04-20-ui15 | 2026-04-20 | UI server granularization round 2: extract handler base class. 40 methods (plumbing/auth/send/rate-limit/quotas/public-gates) move to new ui_server_handler_base.py. LiaUIHandler inherits from LiaUIHandlerBase. Host LOC: 1412→<actual>. NOT an env change. | src/lia_graph/ui_server.py, src/lia_graph/ui_server_handler_base.py (new), tests/test_ui_server_handler_base.py (new) |
```

**State Notes:**
_(fill in during execution)_

---

### Phase 3 — `ui_server`: extract handler dispatch

**Status:** ☐ NOT_STARTED ☐ IN_PROGRESS ☐ PASSED_TESTS ☐ COMMITTED ☐ DONE ☐ BLOCKED
**Entered at:** _________  **Exited at:** _________  **Commit SHA:** _________

**Pre-conditions:**
- [ ] Phase 2 is `DONE`
- [ ] Live-server smoke from Phase 2 is reproducible
- [ ] Working tree clean

**Files to create:**
1. `src/lia_graph/ui_server_handler_dispatch.py` (~550 LOC)
   - Class: `LiaUIHandler(LiaUIHandlerBase)` — this replaces the class of the same name in `ui_server.py` as the canonical export.
   - Methods (17 remaining from Appendix A §1.2):
     - GET handlers (12): `do_GET`, `do_OPTIONS`, `_handle_ops_get`, `_handle_reasoning_get`, `_handle_ingestion_get`, `_handle_runtime_terms_get`, `_handle_citation_get`, `_handle_source_get`, `_handle_platform_get`, `_handle_history_get`, `_handle_form_guides_get`, `_resolve_ui_asset_path`, `_serve_ui_asset`.
     - Verb dispatchers (4): `do_PUT`, `do_POST`, `do_PATCH`, `do_DELETE`.
     - Chat-payload wrappers (6): `_send_api_chat_error`, `_parse_api_chat_request`, `_apply_api_chat_clarification`, `_build_api_chat_success_payload`, `_finalize_api_chat_response`, `_handle_api_chat_post`, `_handle_api_chat_stream_post`.
   - Imports: same pattern as base — `ui_server_constants`, `ui_server_helpers`, plus targeted dep imports needed by *these* methods (e.g., `run_pipeline_c`, `handle_ops_get`, `handle_source_get`, `accept_terms`, etc.), plus `from .ui_server_handler_base import LiaUIHandlerBase`.

2. `tests/test_ui_server_handler_dispatch.py` (~50 LOC)
   - Assert `LiaUIHandler` is importable from `lia_graph.ui_server_handler_dispatch` AND from `lia_graph.ui_server`.
   - Assert `issubclass(LiaUIHandler, LiaUIHandlerBase)`.
   - Assert key dispatch methods are present: `do_GET`, `do_POST`, `do_PATCH`, `do_DELETE`, `do_PUT`, `do_OPTIONS`.

**Files to modify:**
1. `src/lia_graph/ui_server.py`:
   - Delete the remaining class body (the 17 dispatch methods, lines 1087-1591 post-Phase-2).
   - Replace the `class LiaUIHandler(LiaUIHandlerBase):` block with `from .ui_server_handler_dispatch import LiaUIHandler  # noqa: F401` at the bottom of the imports block.
   - Expected LOC after: ~900 − ~510 = **~390 LOC**.

**Work items:**
- [ ] Create `ui_server_handler_dispatch.py` with class skeleton + imports.
- [ ] Migrate the 17 methods verbatim. Pay special attention to `do_POST` (111 LOC) and `_handle_api_chat_stream_post` (80 LOC) — they have the densest name references.
- [ ] **Manual audit**: grep dispatch method bodies for unresolved names. Fix by adding targeted imports.
- [ ] Update `ui_server.py`: delete old class block, add the re-export import.
- [ ] Verify `from lia_graph.ui_server import LiaUIHandler` still works (it MUST — many consumers import this).
- [ ] Run import smoke and method-presence check.
- [ ] Write `tests/test_ui_server_handler_dispatch.py`.

**Targeted tests:**
```bash
uv run pytest tests/test_ui_server_handler_dispatch.py tests/test_ui_server_handler_base.py tests/test_ui_server_constants_helpers.py tests/test_ui_server_http_smokes.py tests/test_ui_ingestion_controllers.py tests/test_ui_ingestion_write_controllers.py tests/test_normativa_surface.py tests/test_citation_resolution.py tests/test_ui_et_article_extractors.py -q
```

**Full-suite tests:**
```bash
make test-batched
```

**Live-server smoke (broader route coverage):**
```bash
LIA_PORT=8787 npm run dev
# In another terminal:
curl -fsS http://127.0.0.1:8787/api/health | jq .
curl -fsS http://127.0.0.1:8787/api/runtime/terms -H 'Authorization: Bearer <test-token>' | head -c 200
curl -fsS -X OPTIONS http://127.0.0.1:8787/api/chat -o /dev/null -w "%{http_code}\n"
curl -fsS http://127.0.0.1:8787/ops | head -c 200  # static asset
# Expect no 5xx. 401/403 on protected routes is acceptable.
```

**LOC target:** `ui_server.py` ≤ 400.

**Commit message template:**
```
refactor(ui_server): extract handler dispatch class

Move 17 dispatch methods (do_GET/do_POST/do_PATCH/do_DELETE/do_PUT,
GET route handlers, chat-payload wrappers) from ui_server.py to new
ui_server_handler_dispatch.py. LiaUIHandler now lives there and is
re-exported from ui_server for back-compat.

No behavior change. All HTTP routes preserve their dispatch paths.
Host LOC: <prev> → <actual>. See docs/next/decouplingv1.md Phase 3.
```

**Post-conditions:**
- [ ] Targeted + full suite green
- [ ] Live-server smoke passes (≥4 route variants)
- [ ] `ui_server.py` LOC ≤ 400
- [ ] `from lia_graph.ui_server import LiaUIHandler` works
- [ ] Commit SHA recorded

**Changelog Draft:**
```
| v2026-04-20-ui16 | 2026-04-20 | UI server granularization round 3: extract handler dispatch. 17 verb dispatchers + GET handlers + chat-payload wrappers move to new ui_server_handler_dispatch.py. LiaUIHandler is re-exported from ui_server for back-compat. Host LOC: <prev>→<actual>. NOT an env change. | src/lia_graph/ui_server.py, src/lia_graph/ui_server_handler_dispatch.py (new), tests/test_ui_server_handler_dispatch.py (new) |
```

**State Notes:**
_(fill in during execution — note any imports that had to be added that weren't in the original ui_server.py)_

---

### Phase 4 — `ui_server`: extract CLI

**Status:** ☐ NOT_STARTED ☐ IN_PROGRESS ☐ PASSED_TESTS ☐ COMMITTED ☐ DONE ☐ BLOCKED
**Entered at:** _________  **Exited at:** _________  **Commit SHA:** _________

**Pre-conditions:**
- [ ] Phase 3 is `DONE`
- [ ] `ui_server.py` ≤ 400 LOC
- [ ] Working tree clean

**Files to create:**
1. `src/lia_graph/ui_server_cli.py` (~100 LOC)
   - Contents: `run_server`, `parser`, `main`, plus `if __name__ == "__main__": main()`.
   - Depends on: `LiaUIHandler` from `ui_server_handler_dispatch`, `ui_server_constants` (for server-level paths and flags).

2. `tests/test_ui_server_cli.py` (~30 LOC)
   - Assert `main`, `run_server`, `parser` are importable from both `lia_graph.ui_server_cli` AND `lia_graph.ui_server`.
   - Assert `parser()` returns an `argparse.ArgumentParser` with the expected flags.
   - Run `main(['--help'])` in a subprocess and check it exits 0 with usage output (if `main` uses `sys.argv`, mock it).

**Files to modify:**
1. `src/lia_graph/ui_server.py`:
   - Delete `run_server`, `parser`, `main`, `__main__` block (lines 1593-1669 post-Phase-3).
   - Add `from .ui_server_cli import main, parser, run_server  # noqa: F401` near the bottom.
   - Keep the `__main__` forwarding block: `if __name__ == "__main__": main()`.
   - Expected LOC after: ~390 − 77 = **~315 LOC** (with imports block + re-exports + `__main__` stub).

2. `pyproject.toml`:
   - **No change required** — `[project.scripts] lia-ui = "lia_graph.ui_server:main"` still resolves because `main` is re-exported from `ui_server`.
   - **Verify** post-change: `uv run lia-ui --help` works.

**Work items:**
- [ ] Create `ui_server_cli.py`, move `run_server` + `parser` + `main`.
- [ ] Update `ui_server.py`: delete, add re-export, keep `__main__` stub.
- [ ] Verify entry point: `uv run lia-ui --help` exits 0.
- [ ] Verify module invocation: `python -m lia_graph.ui_server --help` exits 0.
- [ ] Write `tests/test_ui_server_cli.py`.

**Targeted tests:**
```bash
uv run pytest tests/test_ui_server_cli.py tests/test_ui_server_handler_dispatch.py tests/test_ui_server_handler_base.py tests/test_ui_server_http_smokes.py -q
uv run lia-ui --help  # exit code 0
python -m lia_graph.ui_server --help  # exit code 0
```

**Full-suite tests:**
```bash
make test-batched
```

**Live-server smoke:**
```bash
LIA_PORT=8787 npm run dev
# Should start normally; tail dev-launcher logs for "Preflight passed for local mode."
```

**LOC target:** `ui_server.py` ≤ 320.

**Commit message template:**
```
refactor(ui_server): extract CLI entrypoint

Move run_server / parser / main from ui_server.py to new
ui_server_cli.py. Re-exported from ui_server for back-compat so
pyproject.toml [project.scripts] lia-ui still resolves.

Host LOC: <prev> → <actual>. See docs/next/decouplingv1.md Phase 4.
```

**Post-conditions:**
- [ ] `uv run lia-ui --help` exits 0
- [ ] `python -m lia_graph.ui_server --help` exits 0
- [ ] Targeted + full suite green
- [ ] `ui_server.py` LOC ≤ 320
- [ ] Commit SHA recorded

**Changelog Draft:**
```
| v2026-04-20-ui17 | 2026-04-20 | UI server granularization round 4: extract CLI. run_server/parser/main move to new ui_server_cli.py; re-exported from ui_server so pyproject.toml entry point (lia-ui) still resolves. Host LOC: <prev>→<actual>. NOT an env change. | src/lia_graph/ui_server.py, src/lia_graph/ui_server_cli.py (new), tests/test_ui_server_cli.py (new) |
```

**State Notes:**
_(fill in during execution)_

---

### Phase 5 — `ui_server`: graduation verification

**Status:** ☐ NOT_STARTED ☐ IN_PROGRESS ☐ PASSED_TESTS ☐ COMMITTED ☐ DONE ☐ BLOCKED
**Entered at:** _________  **Exited at:** _________  **Commit SHA:** _________ (may be doc-only)

**Pre-conditions:**
- [ ] Phase 4 is `DONE`
- [ ] `ui_server.py` ≤ 320 LOC
- [ ] Working tree clean

**Files to modify (optional):**
- `docs/guide/orchestration.md` — interim update (Phase 13 does the full publish; this one appends a "pending graduation" note if helpful).

**Work items:**
- [ ] Confirm `wc -l src/lia_graph/ui_server.py` ≤ 320.
- [ ] Confirm the graduation trajectory: `ui_server_constants.py`, `ui_server_helpers.py`, `ui_server_handler_base.py`, `ui_server_handler_dispatch.py`, `ui_server_cli.py` all ≤ 1000 LOC individually.
- [ ] Run `make test-batched` — must be 401 pass / 2 pre-squash fail (exactly the baseline).
- [ ] Start `npm run dev` — verify `diagnostics.retrieval_backend == "artifacts"` via a POST to `/api/chat`.
- [ ] Start `npm run dev:staging` — verify `diagnostics.retrieval_backend == "supabase"` and `diagnostics.graph_backend == "falkor_live"`.
- [ ] `npm run dev:production` — verify it exits locally with code 2 (expected behavior; prod runs on Railway).
- [ ] Commit doc-only if anything in `docs/guide/orchestration.md` or `CLAUDE.md` needs an interim note (otherwise skip).

**Targeted tests:**
```bash
make test-batched
npm run dev:check  2>&1 | tail -5   # "Preflight passed for local mode."
# Optional: npm run dev:staging:check
```

**Full-suite tests:** (covered above)

**LOC target:** unchanged — verification only.

**Commit message template (if any):**
```
docs(ui_server): note interim graduation of ui_server.py <LOC>
```

**Post-conditions:**
- [ ] All 3 run-mode checks report their expected backends
- [ ] Full Python test suite at baseline pass rate
- [ ] Every new sibling file (5 total from Phases 1-4) ≤ 1000 LOC
- [ ] Phase 13's "changelog drafts to publish" list now includes v2026-04-20-ui14 through ui17

**Changelog Draft:** _(none standalone — Phase 13 publishes)_

**State Notes:**
_(record exact LOC of every new sibling + host, plus the diagnostics backends reported from each run mode)_

---

### Phase 6 — `ops`: stabilize 11 pre-existing test failures

**Status:** ☐ NOT_STARTED ☐ IN_PROGRESS ☐ PASSED_TESTS ☐ COMMITTED ☐ DONE ☐ BLOCKED
**Entered at:** _________  **Exited at:** _________  **Commit SHA:** _________

**Why this phase exists.** `opsFolderIngestion.test.ts` has 10 failures and `opsApp.test.ts` has 1 failure. Without a green baseline, the 6-phase TS refactor is flying blind — a regression introduced during extraction would hide among the existing reds. Fix first, refactor second. The failures look environmental (jsdom setup, DOM ID mismatches, missing `Response.body` captures) rather than deep logic bugs.

**Pre-conditions:**
- [ ] Phase 5 is `DONE`
- [ ] Working tree clean
- [ ] Failing-tests list copied from Phase 0's State Notes into this phase's State Notes

**Files to modify (predicted — refine during execution):**
1. `frontend/tests/opsFolderIngestion.test.ts` and/or `frontend/tests/opsApp.test.ts` — possibly the `beforeEach` DOM fixtures, the mocked `fetch` implementations, or the test IDs being queried.
2. `frontend/tests/setup.ts` or similar — vitest environment setup if the issue is config-level.
3. `frontend/src/features/ops/opsIngestionController.ts` — **zero-change if at all possible**. If a test is failing because of a legitimate bug, fix the bug in its own sub-commit and document it in State Notes.

**Files to create:** none expected.

**Work items:**
- [ ] Reproduce each failure locally one at a time: `cd frontend && npx vitest run --config ./vitest.config.ts tests/opsFolderIngestion.test.ts -t '<test name>'`.
- [ ] Triage each failure:
  - (a) test fixture / DOM-setup issue → fix in the test file
  - (b) vitest config / environment issue → fix in setup
  - (c) genuine bug in the controller → fix in controller, document separately
- [ ] For each fix, confirm the specific test passes and the previously-green tests still pass.
- [ ] After all 11 failures fix, run the full ops suite: `cd frontend && npx vitest run --config ./vitest.config.ts src/features/ops` — expect 96 pass / 0 fail.
- [ ] Run the frontend health check: `npm test` — expect 10 pass.

**Targeted tests:**
```bash
cd frontend && npx vitest run --config ./vitest.config.ts src/features/ops
cd frontend && npx vitest run --config ./vitest.config.ts tests/opsApp.test.ts tests/opsFolderIngestion.test.ts
```

**Full-suite tests:**
```bash
cd frontend && npm run test:all
```

**LOC target:** `opsIngestionController.ts` unchanged (2327). If a genuine bug fix needs a controller edit, it's in-scope but must be surgical.

**Commit message template:**
```
test(ops): stabilize 11 pre-existing ops test failures

<one-line summary of root cause — e.g., "jsdom file-input stub missed
the FileList mock"; adjust per actual findings>.

Restores green baseline on src/features/ops before the
opsIngestionController.ts factory-composition refactor begins.
No behavior change. See docs/next/decouplingv1.md Phase 6.
```

**Post-conditions:**
- [ ] `src/features/ops` ops suite: 96/96 pass
- [ ] `npm test` (health check): 10/10 pass
- [ ] `npm run test:all`: green (or same pre-existing greens minus the 11 that are now fixed)
- [ ] Commit SHA recorded

**Changelog Draft:**
```
| v2026-04-20-ui18 | 2026-04-20 | Ops test stabilization: fix 11 pre-existing failures in opsFolderIngestion.test.ts (10) and opsApp.test.ts (1). Root cause: <TBD>. Restores green baseline ahead of opsIngestionController.ts factory split. No runtime behavior change. | frontend/tests/opsFolderIngestion.test.ts, frontend/tests/opsApp.test.ts, frontend/tests/setup.ts (if touched) |
```

**State Notes (populate at Phase 0 entry with the 11 failing test names, then fill with fix notes):**
_(list each failing test and its resolution)_

---

### Phase 7 — `ops`: extract API factory

**Status:** ☐ NOT_STARTED ☐ IN_PROGRESS ☐ PASSED_TESTS ☐ COMMITTED ☐ DONE ☐ BLOCKED
**Entered at:** _________  **Exited at:** _________  **Commit SHA:** _________

**Pre-conditions:**
- [ ] Phase 6 is `DONE`
- [ ] Ops suite 96/96 green
- [ ] Working tree clean

**Files to create:**
1. `frontend/src/features/ops/opsIngestionContext.ts` (~40 LOC)
   - Export `OpsControllerCtx` interface: `{ dom, i18n, state (getter), stateController, withThinkingWheel, setFlash, toast }`.
   - Export `createOpsControllerCtx(options: CreateOpsIngestionControllerOptions): OpsControllerCtx`.

2. `frontend/src/features/ops/opsIngestionApi.ts` (~260 LOC)
   - Export `createOpsApi(ctx: OpsControllerCtx)` returning:
     - `fetchCorpora`, `fetchIngestionSessions`, `fetchIngestionSession`, `createIngestionSession`, `uploadIngestionFile`, `startIngestionProcess`, `validateBatch`, `retryIngestionSession`, `ejectIngestionSession`, `refreshIngestion`, `refreshSelectedSession`, `ensureSelectedSession`, `resolveSessionCorpus`.
   - Uses `requestJson` + `postJsonOrThrow` from the existing `opsIngestionTypes.ts`.

3. `frontend/src/features/ops/opsIngestionApi.test.ts` (~120 LOC)
   - Mock `fetch`, assert each API method hits the expected URL with the expected body/method.

**Files to modify:**
1. `frontend/src/features/ops/opsIngestionController.ts`:
   - Import `createOpsApi`, `createOpsControllerCtx`.
   - Replace the inline API functions with `const api = createOpsApi(ctx);` + delegations where needed.
   - Preserve every existing inner-function signature; the `bindEvents` body calls `api.<method>` instead of the inner fn.
   - Expected LOC after: 2327 − ~230 (API fns) = **~2100 LOC**.

**Work items:**
- [ ] Draft `opsIngestionContext.ts` with the Ctx interface and factory.
- [ ] Draft `opsIngestionApi.ts` — move all `fetch*`/`*IngestionSession`/`refresh*`/`ensureSelectedSession`/`resolveSessionCorpus` functions into the factory closure.
- [ ] Update `opsIngestionController.ts`: create `ctx` at the top of `createOpsIngestionController`, instantiate `api = createOpsApi(ctx)`, rewrite the inner-function references to `api.X` (or keep local aliases: `const { refreshIngestion, refreshSelectedSession, ... } = api;` for minimal-diff).
- [ ] Write `opsIngestionApi.test.ts`.
- [ ] Run targeted tests.

**Targeted tests:**
```bash
cd frontend && npx vitest run --config ./vitest.config.ts src/features/ops/opsIngestionApi.test.ts src/features/ops/opsFolderIngestion.test.ts tests/opsApp.test.ts
```

**Full-suite tests:**
```bash
cd frontend && npm run test:all
```

**LOC target:** `opsIngestionController.ts` ≤ 2120.

**Commit message template:**
```
refactor(ops): extract API factory from opsIngestionController

Move 13 fetch-based API functions (fetchCorpora, fetchIngestionSessions,
createIngestionSession, uploadIngestionFile, start/retry/validate/eject,
refreshIngestion, refreshSelectedSession, ensureSelectedSession,
resolveSessionCorpus) into createOpsApi(ctx) factory in new
opsIngestionApi.ts. New opsIngestionContext.ts defines OpsControllerCtx
shared-context interface.

Host LOC: 2327 → <actual>. See docs/next/decouplingv1.md Phase 7.
```

**Post-conditions:**
- [ ] Ops suite 96/96 green
- [ ] Frontend health check green
- [ ] `opsIngestionController.ts` ≤ 2120
- [ ] Commit SHA recorded

**Changelog Draft:**
```
| v2026-04-20-ui19 | 2026-04-20 | Ops controller granularization round 1: extract API factory. Move 13 fetch-based session/corpora/upload methods into createOpsApi(ctx) in new opsIngestionApi.ts + shared OpsControllerCtx in opsIngestionContext.ts. Host LOC: 2327→<actual>. NOT an env change. | frontend/src/features/ops/opsIngestionController.ts, frontend/src/features/ops/opsIngestionApi.ts (new), frontend/src/features/ops/opsIngestionContext.ts (new), frontend/src/features/ops/opsIngestionApi.test.ts (new) |
```

**State Notes:**
_(fill in during execution)_

---

### Phase 8 — `ops`: extract Upload factory

**Status:** ☐ NOT_STARTED ☐ IN_PROGRESS ☐ PASSED_TESTS ☐ COMMITTED ☐ DONE ☐ BLOCKED
**Entered at:** _________  **Exited at:** _________  **Commit SHA:** _________

**Pre-conditions:**
- [ ] Phase 7 is `DONE`
- [ ] Ops suite 96/96 green

**Files to create:**
1. `frontend/src/features/ops/opsIngestionUpload.ts` (~300 LOC)
   - Export `createOpsUpload(ctx, api)` returning: `resolveFolderFiles`, `readDirectoryHandle`, `uploadFilesWithConcurrency`, `renderUploadProgress`, `renderScanProgress`, `persistFolderPending`, `clearFolderPending`, `getStoredFolderPendingCount`, `directFolderIngest`, `requestPreflight`.
2. `frontend/src/features/ops/opsIngestionUpload.test.ts` (~140 LOC)
   - Mock `state`/`api`, test the concurrency-limited upload loop, folder walk, persist/restore, progress rendering.

**Files to modify:**
1. `frontend/src/features/ops/opsIngestionController.ts`:
   - `const upload = createOpsUpload(ctx, api);` at top of the closure.
   - Replace inner-function references with `upload.X`.
   - Expected LOC after: ~2100 − ~300 = **~1800 LOC**.

**Work items:**
- [ ] Draft `opsIngestionUpload.ts`.
- [ ] Update `opsIngestionController.ts`.
- [ ] Write `opsIngestionUpload.test.ts`.
- [ ] Run targeted tests.

**Targeted tests:** `cd frontend && npx vitest run --config ./vitest.config.ts src/features/ops` — 96/96 + new tests.
**Full-suite tests:** `cd frontend && npm run test:all`.
**LOC target:** `opsIngestionController.ts` ≤ 1820.

**Commit message template:**
```
refactor(ops): extract Upload factory

Move 10 upload/progress/folder-persistence functions into
createOpsUpload(ctx, api) factory in new opsIngestionUpload.ts.

Host LOC: <prev> → <actual>. See docs/next/decouplingv1.md Phase 8.
```

**Post-conditions:** ops suite green, LOC ≤ 1820, commit recorded.

**Changelog Draft:**
```
| v2026-04-20-ui20 | 2026-04-20 | Ops controller granularization round 2: extract Upload factory. 10 upload/progress/folder-persistence functions move to createOpsUpload(ctx, api) in new opsIngestionUpload.ts. Host LOC: <prev>→<actual>. NOT an env change. | frontend/src/features/ops/opsIngestionController.ts, frontend/src/features/ops/opsIngestionUpload.ts (new), frontend/src/features/ops/opsIngestionUpload.test.ts (new) |
```

**State Notes:**
_(fill in during execution)_

---

### Phase 9 — `ops`: extract Intake factory (owns local state)

**Status:** ☐ NOT_STARTED ☐ IN_PROGRESS ☐ PASSED_TESTS ☐ COMMITTED ☐ DONE ☐ BLOCKED
**Entered at:** _________  **Exited at:** _________  **Commit SHA:** _________

**Why this phase is sensitive.** The Intake factory owns the controller-local mutable state: `intakeEntries`, `intakeManifestVersion`, `preflightDebounce`, `intakeError`, and the `PREFLIGHT_DEBOUNCE_MS` constant. After this phase, the host controller must not directly reference those `let`/`const` bindings — all access goes through `intake.getIntakeEntries()`, `intake.getManifestVersion()`, etc.

**Pre-conditions:**
- [ ] Phase 8 is `DONE`
- [ ] Ops suite green

**Files to create:**
1. `frontend/src/features/ops/opsIngestionIntake.ts` (~280 LOC)
   - Export `createOpsIntake(ctx, api, renderers)` — but renderers don't exist yet! Option A: pass a placeholder and wire renderers later. Option B: extract this phase AFTER renderers (reorder). Keeping the planned order, we pass renderers as a lazy `() => Renderers` factory or use an event-bus. Simplest: define an intake-internal `onIntakeChanged` callback the host wires up.
   - Returns: `addFilesToIntake`, `schedulePreflight`, `runIntakePreflight`, `hashIntakeEntries`, `preflightIntake`, `applyManifestToIntake`, `removeIntakeEntry`, `cancelAllWillIngest`, `clearIntake`, `confirmAndIngest`, `getIntakeEntries`, `getManifestVersion`, `setIntakeError`.
2. `frontend/src/features/ops/opsIngestionIntake.test.ts` (~150 LOC)
   - Exercise the addFiles → preflight → confirm pipeline with mocked api + a captured render-callback.

**Files to modify:**
1. `frontend/src/features/ops/opsIngestionController.ts`:
   - Move `let intakeEntries: IntakeEntry[] = []`, `let intakeManifestVersion = 0`, `let preflightDebounce = null`, `let intakeError = false` into the Intake factory.
   - `const intake = createOpsIntake(ctx, api, { onChanged: () => renderers.renderIntake() })` (or an event bus).
   - Replace every direct access to those `let` bindings with getter calls.
   - Expected LOC after: ~1800 − ~300 = **~1500 LOC**.

**Work items:**
- [ ] Draft `opsIngestionIntake.ts` with factory, state, and 10 functions.
- [ ] Decide how Intake notifies renderers (callback param vs. event bus). Recommended: callback `onIntakeChanged()` passed in options.
- [ ] Update `opsIngestionController.ts`.
- [ ] Write `opsIngestionIntake.test.ts`.
- [ ] Run targeted + full-suite tests.

**Targeted tests:** `cd frontend && npx vitest run --config ./vitest.config.ts src/features/ops`.
**Full-suite tests:** `cd frontend && npm run test:all`.
**LOC target:** `opsIngestionController.ts` ≤ 1520.

**Commit message template:**
```
refactor(ops): extract Intake factory (owns local mutable state)

Move 10 intake pipeline functions (addFilesToIntake, schedulePreflight,
runIntakePreflight, preflightIntake, applyManifestToIntake, confirm
AndIngest, remove/cancel/clear, hashIntakeEntries) and their backing
state (intakeEntries, intakeManifestVersion, preflightDebounce,
intakeError) into createOpsIntake(ctx, api) factory.

Host LOC: <prev> → <actual>. See docs/next/decouplingv1.md Phase 9.
```

**Post-conditions:** ops suite green, LOC ≤ 1520, commit recorded. **All** controller-local `let`/`const` state bindings now live inside a factory, not in the host closure.

**Changelog Draft:**
```
| v2026-04-21-ui1 | 2026-04-21 | Ops controller granularization round 3: extract Intake factory. 10 intake-pipeline functions + the backing intakeEntries/manifestVersion/preflightDebounce/intakeError state move to createOpsIntake(ctx, api) in new opsIngestionIntake.ts. Host LOC: <prev>→<actual>. NOT an env change. | frontend/src/features/ops/opsIngestionController.ts, frontend/src/features/ops/opsIngestionIntake.ts (new), frontend/src/features/ops/opsIngestionIntake.test.ts (new) |
```

**State Notes:**
_(fill in during execution — note how the renderer-callback was wired)_

---

### Phase 10 — `ops`: extract AutoPilot factory

**Status:** ☐ NOT_STARTED ☐ IN_PROGRESS ☐ PASSED_TESTS ☐ COMMITTED ☐ DONE ☐ BLOCKED
**Entered at:** _________  **Exited at:** _________  **Commit SHA:** _________

**Pre-conditions:** Phase 9 `DONE`, ops suite green.

**Files to create:**
1. `frontend/src/features/ops/opsIngestionAutoPilot.ts` (~170 LOC)
   - Export `createOpsAutoPilot(ctx, api, renderers)` returning: `startAutoPilot`, `stopAutoPilot`, `updateAutoStatus`, `autoPilotTick`, `countRawDocs`.
2. `frontend/src/features/ops/opsIngestionAutoPilot.test.ts` (~100 LOC)
   - Mock clock (`vi.useFakeTimers`) + api, verify tick logic and the start/stop lifecycle.

**Files to modify:**
1. `frontend/src/features/ops/opsIngestionController.ts`: `const autoPilot = createOpsAutoPilot(ctx, api, renderers)`. Expected LOC after: ~1500 − ~170 = **~1330 LOC**.

**Work items:** as above; same pattern as Phases 7-9.

**Targeted tests:** `cd frontend && npx vitest run --config ./vitest.config.ts src/features/ops`.
**LOC target:** ≤ 1350.

**Commit message template:**
```
refactor(ops): extract AutoPilot factory

Move 5 auto-pilot functions (start/stop, tick, status update, raw-docs
counter) into createOpsAutoPilot(ctx, api, renderers) in new
opsIngestionAutoPilot.ts.

Host LOC: <prev> → <actual>. See docs/next/decouplingv1.md Phase 10.
```

**Changelog Draft:**
```
| v2026-04-21-ui2 | 2026-04-21 | Ops controller granularization round 4: extract AutoPilot factory. 5 auto-pilot functions move to createOpsAutoPilot(ctx, api, renderers) in new opsIngestionAutoPilot.ts. Host LOC: <prev>→<actual>. NOT an env change. | frontend/src/features/ops/opsIngestionController.ts, frontend/src/features/ops/opsIngestionAutoPilot.ts (new), frontend/src/features/ops/opsIngestionAutoPilot.test.ts (new) |
```

**State Notes:**
_(fill in during execution)_

---

### Phase 11 — `ops`: extract Renderers factory (graduation)

**Status:** ☐ NOT_STARTED ☐ IN_PROGRESS ☐ PASSED_TESTS ☐ COMMITTED ☐ DONE ☐ BLOCKED
**Entered at:** _________  **Exited at:** _________  **Commit SHA:** _________

**Why this phase is the graduation.** After Renderers extract, host is predicted ≤ 700 LOC — below the 1000-LOC graduation threshold. Phase 12 (events binder) is pure cleanup.

**Pre-conditions:** Phase 10 `DONE`, ops suite green.

**Files to create:**
1. `frontend/src/features/ops/opsIngestionRenderers.ts` (~600 LOC — biggest single extraction)
   - Export `createOpsRenderers(ctx, api)` returning: `render`, `renderCorpora`, `renderSessions`, `buildSessionLog`, `renderLogAccordion`, `renderSelectedSession`, `buildIntakePanel`, `renderIntakeWindows`, `buildIntakeBanner`, `renderControls`, `appendIntakeRow`, `renderMarkdownContent`, `_hidePreflightBounceLog`, `trace`, `traceClear`.
   - Renderer cross-references resolve within the factory's own closure.
2. `frontend/src/features/ops/opsIngestionRenderers.test.ts` (~120 LOC)
   - Mock DOM + state, verify each renderer produces the expected innerHTML fragments.

**Files to modify:**
1. `frontend/src/features/ops/opsIngestionController.ts`: `const renderers = createOpsRenderers(ctx, api)`. Wire Intake's `onIntakeChanged` callback to `renderers.render`. Expected LOC after: ~1330 − ~600 = **~730 LOC**. **≤ 1000 — graduation achieved.**

**Work items:** as above.

**Targeted tests:** `cd frontend && npx vitest run --config ./vitest.config.ts src/features/ops`.
**LOC target:** ≤ 750. **Graduation milestone.**

**Commit message template:**
```
refactor(ops): extract Renderers factory — graduation milestone

Move 15 render/build functions into createOpsRenderers(ctx, api) in
new opsIngestionRenderers.ts. Host LOC drops below 1000 (<actual>),
graduating opsIngestionController.ts from the >1000 watch list.

See docs/next/decouplingv1.md Phase 11.
```

**Post-conditions:**
- [ ] ops suite green
- [ ] `opsIngestionController.ts` ≤ 1000 (graduation confirmed)
- [ ] Commit SHA recorded

**Changelog Draft:**
```
| v2026-04-21-ui3 | 2026-04-21 | Ops controller granularization round 5 (graduation): extract Renderers factory. 15 render/build functions move to createOpsRenderers(ctx, api) in new opsIngestionRenderers.ts. Host LOC drops below 1000 (<actual>), graduating opsIngestionController.ts. NOT an env change. | frontend/src/features/ops/opsIngestionController.ts, frontend/src/features/ops/opsIngestionRenderers.ts (new), frontend/src/features/ops/opsIngestionRenderers.test.ts (new) |
```

**State Notes:**
_(fill in during execution — record exact host LOC at graduation)_

---

### Phase 12 — `ops`: extract Events binder

**Status:** ☐ NOT_STARTED ☐ IN_PROGRESS ☐ PASSED_TESTS ☐ COMMITTED ☐ DONE ☐ BLOCKED
**Entered at:** _________  **Exited at:** _________  **Commit SHA:** _________

**Pre-conditions:** Phase 11 `DONE`, host ≤ 1000.

**Files to create:**
1. `frontend/src/features/ops/opsIngestionEvents.ts` (~650 LOC)
   - Export `bindOpsEvents(deps: OpsEventDeps): () => void` — returns an unbind function for teardown safety.
   - `OpsEventDeps` interface bundles `ctx`, `api`, `upload`, `intake`, `renderers`, `autoPilot`.
   - Contains the 27 event listeners registered on DOM nodes + storage + custom events + beforeunload.
2. `frontend/src/features/ops/opsIngestionEvents.test.ts` (~180 LOC)
   - Mock all factories, dispatch synthetic events, assert the right factory methods are called.

**Files to modify:**
1. `frontend/src/features/ops/opsIngestionController.ts`:
   - Replace the 620-LOC inline `bindEvents` with `const unbind = bindOpsEvents({ ctx, api, upload, intake, renderers, autoPilot });`.
   - Return surface preserves `bindEvents` for back-compat with `opsApp.ts`: `const bindEvents = () => bindOpsEvents({...})` or split into `bind` + `unbind` on the returned object.
   - **Back-compat-critical**: `opsApp.ts` calls `ingestionController.bindEvents()` today. Preserve that signature or update `opsApp.ts` in the same commit.
   - Expected LOC after: ~730 − ~620 + ~20 wiring = **~130 LOC**.

**Work items:**
- [ ] Draft `opsIngestionEvents.ts` — move the entire `bindEvents` body, threading through the factory references.
- [ ] Decide on back-compat shim strategy (preserve `bindEvents()` method on returned object).
- [ ] Update `opsIngestionController.ts` — now just the composer + `return { bindEvents, refreshIngestion, refreshSelectedSession, render, stopAutoPilot }`.
- [ ] If `opsApp.ts` needs updating, do it in the same commit.
- [ ] Write `opsIngestionEvents.test.ts`.

**Targeted tests:** `cd frontend && npx vitest run --config ./vitest.config.ts src/features/ops`.
**Full-suite tests:** `cd frontend && npm run test:all`.
**LOC target:** `opsIngestionController.ts` ≤ 150. **Primary target achieved.**

**Commit message template:**
```
refactor(ops): extract Events binder — final decomposition

Move the 620-LOC bindEvents body (27 event listeners: DOM, storage,
custom events, beforeunload) into bindOpsEvents(deps) in new
opsIngestionEvents.ts. opsIngestionController.ts is now a ~130-LOC
composer that builds ctx, instantiates 5 factories, wires events,
and returns the public API unchanged (bindEvents, refreshIngestion,
refreshSelectedSession, render, stopAutoPilot).

Host LOC: <prev> → <actual>. See docs/next/decouplingv1.md Phase 12.
```

**Post-conditions:**
- [ ] ops suite green
- [ ] frontend full suite green
- [ ] `opsIngestionController.ts` ≤ 150
- [ ] `opsApp.ts` still calls `ingestionController.bindEvents()` successfully
- [ ] Commit SHA recorded

**Changelog Draft:**
```
| v2026-04-21-ui4 | 2026-04-21 | Ops controller granularization round 6 (final): extract Events binder. 620-LOC bindEvents body (27 event listeners) moves to bindOpsEvents(deps) in new opsIngestionEvents.ts. opsIngestionController.ts shrinks to ~130 LOC composer preserving public API. NOT an env change. | frontend/src/features/ops/opsIngestionController.ts, frontend/src/features/ops/opsIngestionEvents.ts (new), frontend/src/features/ops/opsIngestionEvents.test.ts (new), frontend/src/features/ops/opsApp.ts (if back-compat shim needed) |
```

**State Notes:**
_(fill in during execution — confirm back-compat mechanism chosen)_

---

### Phase 13 — Final verification + orchestration changelog publish

**Status:** ☐ NOT_STARTED ☐ IN_PROGRESS ☐ PASSED_TESTS ☐ COMMITTED ☐ DONE ☐ BLOCKED
**Entered at:** _________  **Exited at:** _________  **Commit SHA:** _________

**Pre-conditions:**
- [ ] Phase 12 is `DONE`
- [ ] Both host files are within target: `ui_server.py` ≤ 320 and `opsIngestionController.ts` ≤ 150

**Files to modify:**
1. `docs/guide/orchestration.md` — append all drafted changelog entries from Phases 1-12 (v2026-04-20-ui14 through v2026-04-21-ui4). Ensure every `<prev>` / `<actual>` placeholder is filled with the real numbers captured in each phase's State Notes.
2. `CLAUDE.md` — no change (no architectural or env change).
3. `docs/guide/env_guide.md` — no change (no env change); if the env-guide has a LOC mirror table, update it.
4. `docs/next/decouplingv1.md` — set plan status to `COMPLETE` in the Dashboard; set Phase 13 status to `DONE`; record final LOC snapshot in a new "Summary of landed changes" section appended at the top.

**Work items:**
- [ ] Verify all phase changelog drafts have real numbers (no remaining `<prev>`/`<actual>` placeholders).
- [ ] Append the changelog block to `docs/guide/orchestration.md` in the correct location (after the existing v2026-04-20-ui13 entry).
- [ ] Run `make test-batched` — expect exactly baseline.
- [ ] Run `cd frontend && npm run test:all` — expect all green.
- [ ] Run the three run-mode smokes again:
  - [ ] `npm run dev:check` → passes
  - [ ] `npm run dev:staging:check` → passes, node_count ≥ 500
  - [ ] `npm run dev:production` → exits code 2 locally (expected)
- [ ] Update this doc's Dashboard: `Plan status = COMPLETE`, final LOC in Progress table.
- [ ] Optional: tag the final commit (`git tag decouplingv1-complete`).

**Targeted tests:**
```bash
make test-batched
cd frontend && npm run test:all
cd /Users/ava-sensas/Developer/Lia_Graph && npm run dev:check
```

**LOC target:** no code changes in this phase; doc-only.

**Commit message template:**
```
docs: publish decouplingv1 changelog + close decoupling campaign

Append v2026-04-20-ui14 through v2026-04-21-ui4 changelog entries to
docs/guide/orchestration.md. Mark docs/next/decouplingv1.md as
COMPLETE. ui_server.py graduated 1669→<actual>; opsIngestion
Controller.ts graduated 2327→<actual>. Both below 1000 LOC.

See docs/next/decouplingv1.md Phase 13.
```

**Post-conditions:**
- [ ] Both host files graduated (≤ 1000 LOC)
- [ ] All 13 new sibling files created, each ≤ 1000 LOC
- [ ] Orchestration changelog has 7+ new entries
- [ ] Python + frontend suites fully green
- [ ] Three run modes smoke-verified
- [ ] This doc's Plan status = COMPLETE

**Changelog Draft:** _(none — Phase 13 publishes the drafts from earlier phases)_

**State Notes:**
_(final summary: exact LOC of host files and each sibling, final test pass counts, timestamps)_

---

## 6. Resumption Runbook

If a session is interrupted, pick up as follows:

1. **Read the Dashboard** — find `Current phase`, `Last completed phase`, `Blockers`.
2. **Inspect working tree** — `git status --short` and `git log -10 --format="%h %s"`. Cross-reference commit SHAs in the ledger.
3. **Locate the first non-`DONE` phase** in the ledger. If its status is `IN_PROGRESS`, read its State Notes to see which Work items were ticked.
4. **Verify pre-conditions** of that phase. If any fail, fix them first.
5. **Continue from the first unticked Work item.**
6. **Do not skip** phases. If a phase is `BLOCKED`, resolve the blocker (may require human input) before proceeding.
7. **If a commit exists but the phase is not marked `COMMITTED`**: the commit succeeded but the ledger wasn't updated. Verify with `git show <SHA>` and update the ledger manually.
8. **If tests fail unexpectedly** during resume: that means a later-committed change introduced a regression that current-phase work depends on. `git bisect` from the phase's entry SHA to HEAD.

---

## 7. Risk Register (compressed)

| Risk | Likelihood | Mitigation | Phase(s) most affected |
|---|---|---|---|
| Circular import when siblings import from `ui_server` | Low (constants-first avoids it) | Siblings import from `ui_server_constants`/`_helpers` + 44 original sources; never from `ui_server` itself | 1, 2, 3 |
| `NameError` in handler methods post-split | Medium | Manual grep audit at each phase; import exactly what each file needs from the original 44 sources | 2, 3 |
| Missed `_REEXPORT_SOURCES` entry → downstream `AttributeError` on `ui_server.X` | Low | Wildcard re-export in `ui_server.py` preserves all names; targeted tests assert re-exports | 1, 4 |
| `pyproject.toml [project.scripts]` breaks | Very Low | Phase 4 explicitly verifies `uv run lia-ui --help` | 4 |
| 11 pre-existing ops fails mask a regression | Mitigated | Phase 6 fixes them before TS extractions start | 6 |
| `bindEvents` back-compat (signature) breaks `opsApp.ts` | Medium | Phase 12 preserves `bindEvents()` method on returned controller; tests cover the call | 12 |
| Intake mutable state accidentally duplicated | Low | Phase 9 moves ALL `let` bindings into the factory; grep audit in that phase | 9 |
| State dashboard drift (ledger out of sync with reality) | Medium | Execution Protocol §3 + mandatory update-before-commit discipline | all |
| Full suite OOM (AGENTS.md warns about this) | Low | `make test-batched` honored everywhere; no bare `pytest` | all Python phases |

---

## 8. Success Criteria (definition of done)

All of the following must be true at Phase 13 exit:

- `wc -l src/lia_graph/ui_server.py` ≤ 300
- `wc -l frontend/src/features/ops/opsIngestionController.ts` ≤ 150
- Every new sibling file (5 Python + 7 TS + 1 context file = 13 total) is ≤ 1000 LOC
- `make test-batched` passes at baseline pass rate (401 pass / 2 pre-squash fail)
- `cd frontend && npm run test:all` passes with all ops tests green (96 + any added)
- `uv run lia-ui --help` exits 0
- `python -m lia_graph.ui_server --help` exits 0
- `npm run dev:check` passes
- `npm run dev:staging:check` passes with node_count ≥ 500
- `docs/guide/orchestration.md` has entries v2026-04-20-ui14 through v2026-04-21-ui4 with real LOC numbers
- `opsApp.ts` continues to call `ingestionController.bindEvents()` without modification (or is updated in Phase 12)
- Plan status in this doc = `COMPLETE`

---

## Appendix A — Original diagnostic: `src/lia_graph/ui_server.py`

_(Preserved verbatim from the 2026-04-20 pre-execution diagnostic. Source of line numbers and method inventories cited in §5.)_

### A.1 Anatomy

Current file layout (line ranges are post-granularize-v2):

```
  1-257    ~250 LOC   Imports block (44 internal + stdlib)
258-314    ~57  LOC   Module-level constants (paths, flags, env reads)
315-430    ~116 LOC   Public-mode config (runtime-side-effect!)
                      + _SUSPENDED_CACHE, route regexes, _GENERIC_SOURCE_TITLES,
                      _SUMMARY_*_HINTS, _NORM_REFERENCE_RE, _ET_ARTICLE_DOC_ID_RE,
                      _EXPERT_SUMMARY_SKIP_EXACT, _DEFAULT_CHAT_LIMITS,
                      _ALLOWED_*, _RELOAD_WATCH_SUFFIXES
431-439    ~9   LOC   _emit_audit_event / _emit_chat_verbose_event
445-463    ~19  LOC   dev-reload wrappers (already delegate to ui_dev_reload)
465-514    ~50  LOC   Misc module-level helpers (_build_public_api_error etc.)
515-548    ~34  LOC   _REEXPORT_SOURCES lazy registry + __getattr__
549-571    ~23  LOC   Deps-factory re-import from ui_server_deps
573-1591  ~1019 LOC   class LiaUIHandler(BaseHTTPRequestHandler)
1593-1693  ~101 LOC   run_server / parser / main / __main__
```

**The class is the problem.** 1019 LOC with **58 methods** (verified: 57) and ~150 module-level name references from inside method bodies.

### A.2 Method inventory (57 methods, organized by concern)

Line numbers are current-file (post-round-21 state). Confirmed by 2026-04-20 survey.

**Class header + dunders:** `server_version`, `protocol_version` class attributes.

**Request plumbing (6–7 methods)** — 576 `_request_origin`, 588 `_allowed_cors_origin`, 602 `_cors_headers`, 615 `_embed_security_headers`, 809 `_start_api_request_log`, 826 `_log_api_response`, 1083 `log_message` (overrides stdlib).

**Auth + session (7 methods)** — 630 `_send_auth_error`, 643 `_resolve_auth_context` (73 LOC — heaviest), 716 `_admin_tenant_scope`, 728 `_resolve_feedback_rating`, 741 `_clarification_scope_key`, 744 `_build_memory_summary`, 1057 `_is_user_suspended` (26 LOC).

**Frontend-compat shims (2 methods)** — 747 `_handle_chat_frontend_compat_get`, 756 `_handle_chat_frontend_compat_post`.

**Chat-request lifecycle (4 methods)** — 764 `_initialize_chat_request_context`, 778 `_persist_user_turn`, 781 `_persist_assistant_turn`, 797 `_persist_usage_events`.

**HTTP response primitives (6 methods)** — 852 `_base_security_headers` (staticmethod), 862 `_send_bytes`, 884 `_send_json`, 898 `_send_event_stream_headers`, 910 `_write_sse_event`, 926 `_read_json_payload` (33 LOC).

**Rate-limit + quotas + public-mode gates (7 methods)** — 959 `_check_rate_limit`, 972 `_get_trusted_client_ip`, 992 `_hash_public_user_id`, 1004 `_check_public_daily_quota` (32 LOC), 1036 `_is_public_visitor_request`, 1049 `_handle_public_session_post`, 1053 `_serve_public_page`.

**GET route handlers (13 methods)** — 1087 `do_GET` (57 LOC dispatcher), 1144 `do_OPTIONS`, 1153 `_handle_ops_get`, 1183 `_handle_reasoning_get`, 1190 `_handle_ingestion_get`, 1194 `_handle_runtime_terms_get`, 1207 `_handle_citation_get`, 1227 `_handle_source_get`, 1252 `_handle_platform_get`, 1268 `_handle_history_get`, 1281 `_handle_form_guides_get`, 1299 `_resolve_ui_asset_path`, 1331 `_serve_ui_asset`.

**POST + modify dispatchers (4 methods)** — 1359 `do_PUT`, 1367 `do_POST` (111 LOC — second heaviest), 1478 `do_PATCH`, 1495 `do_DELETE`.

**Chat-payload wrappers (7 methods)** — 1512 `_send_api_chat_error`, 1541 `_parse_api_chat_request`, 1544 `_apply_api_chat_clarification`, 1557 `_build_api_chat_success_payload`, 1571 `_finalize_api_chat_response`, 1586 `_handle_api_chat_post`, 1589 `_handle_api_chat_stream_post` (80 LOC).

### A.3 The ~150 module-level name references problem (why constants-first)

Method bodies reference names that live in `ui_server.py`'s module scope. A non-exhaustive inventory:

- **Paths / constants (~30 names)** — `WORKSPACE_ROOT`, `UI_DIR`, `FRONTEND_DIR`, `INDEX_FILE_PATH`, `FORM_GUIDES_ROOT`, `CHAT_RUNS_PATH`, `CHAT_SESSION_METRICS_PATH`, `CITATION_GAP_REGISTRY_PATH`, `JOBS_RUNTIME_PATH`, `CORPUS_JOBS_RUNTIME_PATH`, `USAGE_EVENTS_PATH`, `FEEDBACK_PATH`, `CONVERSATIONS_PATH`, `LLM_RUNTIME_CONFIG_PATH`, `TERMS_POLICY_PATH`, `TERMS_STATE_PATH`, `USER_ERROR_LOG_PATH`, `VERBOSE_CHAT_LOG_PATH`, `API_AUDIT_LOG_PATH`, `AUTH_NONCES_PATH`, `HOST_INTEGRATIONS_CONFIG_PATH`, `EXPERT_SUMMARY_OVERRIDES_PATH`, `ORCHESTRATION_SETTINGS_PATH`, `CLARIFICATION_SESSIONS_PATH`, `INGESTION_ARTIFACTS_ROOT`, `INGESTION_PROCESSED_ROOT`, `INGESTION_UPLOADS_ROOT`, `SERVER_STARTED_AT`.
- **Regex + frozen data (~15 names)** — `_CHAT_RUN_ROUTE_RE`, `_CHAT_RUN_MILESTONES_ROUTE_RE`, `_CHAT_SESSION_METRICS_ROUTE_RE`, `_CONVERSATION_SESSION_ROUTE_RE`, `_JOBS_ROUTE_RE`, `_DOC_PART_SUFFIX_RE`, `_INGESTION_*_ROUTE_RE` (×8), `_OPS_RUN_ROUTE_RE`, `_OPS_RUN_TIMELINE_ROUTE_RE`, `_ET_ARTICLE_DOC_ID_RE`, `_NORM_REFERENCE_RE`, `_GENERIC_SOURCE_TITLES`, `_SUMMARY_RISK_HINTS`, `_SUMMARY_ACTION_HINTS`, `_SUMMARY_LOW_RELEVANCE_CONFIDENCE`, `_EXPERT_SUMMARY_SKIP_EXACT`, `_DEFAULT_CHAT_LIMITS`, `_ALLOWED_*` (×8), `_RELOAD_WATCH_SUFFIXES`.
- **Public-mode flags (9 names)** — `PUBLIC_MODE_ENABLED`, `PUBLIC_TRUST_PROXY`, `PUBLIC_USER_SALT`, `PUBLIC_CHAT_BURST_RPM`, `PUBLIC_CHAT_DAILY_CAP`, `PUBLIC_TOKEN_TTL_SECONDS`, `PUBLIC_TURNSTILE_SITE_KEY`, `PUBLIC_TURNSTILE_SECRET`, `PUBLIC_CAPTCHA_ENABLED`.
- **Runtime objects (6 names)** — `INGESTION_RUNTIME`, `SUPPORTED_TOPICS`, `_SUSPENDED_CACHE`, `_SUSPENDED_CACHE_TTL`, `_SUSPENDED_CACHE_LOCK`, `PUBLIC_VISITOR_ROLE`, `PUBLIC_TENANT_ID`.
- **Host-defined helpers (~11)** — `_env_truthy`, `_emit_audit_event`, `_emit_chat_verbose_event`, `_build_info_payload`, `_build_reload_snapshot`, `_start_reload_watcher`, `_build_public_api_error`, `_http_status_from_error_payload`, `_load_runtime_orchestration_settings`, `_write_controller_deps`, `_analysis_controller_deps`, `_chat_controller_deps`, `_frontend_compat_controller_deps`, `_public_session_controller_deps`. (Note: several already live in `ui_chat_payload.py` or `ui_server_deps.py` and are just re-imported.)
- **Import-from-dependency callables (~60)** — `accept_terms`, `approve_contribution`, `exchange_host_grant`, `switch_active_company`, `save_contribution`, `reject_contribution`, `save_feedback`, `update_feedback_comment`, `load_feedback`, `load_session`, `list_sessions`, `list_distinct_topics`, `list_contributions`, `load_chat_run`, `record_chat_run_event_once`, `get_chat_run_coordinator`, `get_chat_run_events`, `get_chat_session_metrics`, `get_pipeline_c_run`, `get_pipeline_c_timeline`, `list_pipeline_c_runs`, `load_job`, `list_citation_gaps`, `register_citation_gaps`, `list_reasoning_events`, `wait_reasoning_events`, `list_available_guides`, `resolve_guide`, `run_guide_chat`, `find_official_form_pdf_source`, `get_terms_status`, `read_terms_text`, `summarize_usage`, `list_feedback`, `list_feedback_for_admin`, `summarize_chat_run_metrics`, `normalize_pais`, `normalize_topic_key`, `resolve_chat_topic`, `resolve_pipeline_route`, `execute_routed_pipeline`, `run_pipeline_c`, `run_pipeline_d`, `generate_llm_strict`, `as_public_error`, `is_semantic_422_error`, `estimate_token_usage_from_text`, `normalize_token_usage`, `save_usage_event`, `read_bearer_token`, `authenticate_access_token`, `emit_event`, `emit_reasoning_event`, `verify_turnstile`, `issue_public_visitor_token`, `public_captcha_pass_exists`, `public_captcha_pass_record`, `resolve_llm_adapter`, `update_orchestration_settings`, `check_and_increment_daily_quota`, `InMemoryRateLimiter`.
- **Class aliases (~15)** — `AuthContext`, `PlatformAuthError`, `FeedbackRecord`, `GuideChatRequest`, `Contribution`, `Citation`, `StoredConversationTurn`, `UsageEvent`, `PipelineCRequest`, `PipelineCInternalError`, `PipelineCStrictError`, `LLMOutputQualityError`, `LLMRuntimeConfigInvalidError`, `OrchestrationSettingsInvalidError`, `IngestionRuntime`.

### A.4 What was previously tried (Plan B fallbacks, not taken)

- **Attempt 1 — wildcard `from .ui_server import *`**: Circular import. Not viable.
- **Attempt 2 — lazy `_host()` accessor with regex-based name prefixing**: regex caught too much (rewrote dict keys, dotted accesses). Not viable.
- **Attempt 3 — lazy import inside each method**: adds 58 import statements; zero-sum LOC. Rejected.
- **Attempt 4 (original diagnostic proposal) — mixin inheritance with lazy `_h()` global + AST-rewrite tooling**: viable but requires maintaining an allowlist of ~150 names; every new name added after the split risks `NameError` at request time. Documented but superseded by the constants-first approach in §4.1 above.

### A.5 HTTP surface of `LiaUIHandler`

(Unchanged; reference for Phase 3 dispatch extraction.)

**GET:** `/api/health`, `/public`, `/public.html`, `/api/chat/runs/{id}`, `/api/chat/runs/{id}/milestones`, `/api/chat/frontend-compat/*`, `/api/eval/*`, `/api/ops/*`, `/api/reasoning/*`, `/api/ingestion/sessions`, `/api/ingestion/sessions/{id}`, `/api/runtime`, `/api/runtime/terms`, `/api/citation-profile`, `/api/normative-analysis`, `/api/source-view`, `/source-view`, `/api/platform/*`, `/api/conversation/*`, `/api/history/*`, `/api/form-guides`, `/api/form-guides/*`, `/form-guide`, `/`, `/index.html`, `/login`, `/invite`, `/ops`, `/embed`, `/admin`, `/form-guide`, `/normative-analysis`, `/orchestration`, `/assets/*`.

**POST:** `/api/chat`, `/api/chat/stream`, `/api/public/session`, `/api/embed/exchange`, `/api/auth/exchange`, `/api/context/switch-company`, `/api/feedback`, `/api/feedback/comment`, `/api/contributions`, `/api/contributions/{id}/approve`, `/api/contributions/{id}/reject`, `/api/terms/accept`, `/api/corpora`, `/api/ingestion/*`, `/api/corpus-ops/*`, `/api/embedding/*`, `/api/reindex/*`, `/api/rollback`, `/api/promote`, `/api/reindex`, `/api/form-guides/chat`, `/api/chat/runs/{id}/milestones`.

**PUT:** `/api/runtime/orchestration-settings`.
**PATCH:** user-management routes.
**DELETE:** `/api/ingestion/sessions/{id}`, user-management routes.
**OPTIONS:** CORS preflight for all API routes.

---

## Appendix B — Original diagnostic: `frontend/src/features/ops/opsIngestionController.ts`

_(Preserved verbatim from the 2026-04-20 pre-execution diagnostic.)_

### B.1 Anatomy

```
  1-23     ~22  LOC   Imports (opsTypes, opsKanbanView, opsState,
                      shared ui, shared api, i18n, toast)
 25-37     ~13  LOC   Imports from the two sibling files already
                      extracted: opsIngestionTypes (types + HTTP
                      helpers) and opsIngestionFormatters (pure helpers)
 39-64     ~26  LOC   createOpsIngestionController export +
                      options destructure + closure-state decls
104-2327  ~2224 LOC   The createOpsIngestionController closure.
                      52 remaining inner functions share the enclosing
                      scope: destructured dom.*, i18n, state,
                      stateController, withThinkingWheel, setFlash,
                      plus closure state (intakeEntries,
                      intakeManifestVersion, preflightDebounce, etc.)
```

### B.2 Inner-function inventory (47 named + 8 nested = 55 functions)

Top 20 LOC-weighted (see original diagnostic for full table):

| LOC | Function | Category |
|---|---|---|
| 620 | `bindEvents` | event binder |
| 128 | `renderSessions` | renderer |
| 101 | `buildSessionLog` | renderer |
| 96 | `autoPilotTick` | autoPilot |
| 76 | `directFolderIngest` | upload |
| 73 | `renderIntakeWindows` | renderer |
| 68 | `renderMarkdownContent` | pure/renderer |
| 62 | `renderControls` | renderer |
| 56 | `buildIntakePanel` | renderer |
| 51 | `appendIntakeRow` | renderer |
| 50 | `refreshIngestion` | api |
| 46 | `uploadFilesWithConcurrency` | upload |
| 46 | `buildIntakeBanner` | renderer |
| 44 | `ensureSelectedSession` | api |
| 42 | `applyManifestToIntake` | intake |
| 42 | `renderSelectedSession` | renderer |
| 41 | `uploadIngestionFile` | api |
| 38 | `updateAutoStatus` | autoPilot |
| 35 | `resolveFolderFiles` | upload |
| 33 | `preflightIntake` | intake |

### B.3 Shared closure state

- **Destructured from `options`**: `i18n`, `stateController`, `withThinkingWheel`, `setFlash`, plus ~35 individual DOM refs destructured from `dom`.
- **Controller-local `let`/`const`**: `intakeEntries: IntakeEntry[]`, `intakeManifestVersion: number`, `preflightDebounce: ReturnType<typeof setTimeout> | null`, `intakeError: boolean`, `PREFLIGHT_DEBOUNCE_MS` constant.
- **Via `stateController`**: `OpsStateData` — `sessions`, `selectedSessionId`, `selectedCorpus`, `folderRelativePaths`, `preflightManifest`, `autoProcessing` flags.

### B.4 The `bindEvents` problem (620 LOC)

27 event listeners registered (validated count from 2026-04-20 survey):
- `ingestionDropzone`: click, keydown, dragenter, dragover, dragleave, drop
- `ingestionFileInput`: change
- `ingestionSelectFilesBtn`: click
- `ingestionSelectFolderBtn`: click (includes `showDirectoryPicker` fallback)
- `ingestionFolderInput`: change
- `ingestionCorpusSelect`: change
- `ingestionBatchTypeSelect`: change
- `ingestionRefreshBtn`: click
- `ingestionCreateSessionBtn`: click
- `ingestionUploadBtn`: click
- `ingestionProcessBtn`: click
- `ingestionAutoProcessBtn`: click
- `ingestionValidateBatchBtn`: click
- `ingestionRetryBtn`: click
- `ingestionDeleteSessionBtn`: click
- `ingestionSessionsList`: delegated click
- `ingestionLogCopyBtn` + `ingestionBounceCopy`: clipboard
- `addCorpusBtn` + `addCorpusDialog`: open/submit
- `storage` listener on `window` for cross-tab sync
- `beforeunload`: autoPilot cleanup
- Custom-event listeners for `ops:session-refresh`, `ops:eject-complete`, `ops:auto-pilot-tick`.

### B.5 HTTP surface touched

All POST/GET unless noted:
- `GET /api/corpora`, `POST /api/corpora`
- `GET /api/ingestion/sessions`, `POST /api/ingestion/sessions`
- `GET /api/ingestion/sessions/{id}`, `DELETE /api/ingestion/sessions/{id}`
- `POST /api/ingestion/sessions/{id}/files` (upload)
- `POST /api/ingestion/sessions/{id}/process|retry|validate-batch|stop|clear-batch|delete-failed`
- `POST /api/ingestion/sessions/{id}/documents/{doc}/classify|retry|resolve-duplicate|accept-autogenerar`
- `POST /api/ingestion/sessions/{id}/auto-process`
- `POST /api/ingestion/sessions/{id}/purge-and-replace`
- `POST /api/ingestion/preflight`

Local storage keys: `lia_folder_pending_{sessionId}` (tab-crash recovery).

Custom events on `window`: `ops:session-refresh`, `ops:eject-complete`, `ops:auto-pilot-tick`.

### B.6 Existing coverage baseline (2026-04-20)

- `opsApp.test.ts`: 4 pass / 1 fail
- `opsFolderIngestion.test.ts`: 5 pass / 9 fail (total 10 listed in triage; actual 9 from survey — reconcile in Phase 6)
- `opsRefreshController.test.ts`: 76 pass / 0 fail
- Overall: 85 pass / 11 fail / 96 total

Phase 6 stabilizes the 11 fails.

---

## Appendix C — Commands quick reference

**Python**

```bash
# Full suite (use this, not bare pytest):
make test-batched

# Targeted subset:
uv run pytest tests/test_ui_server_http_smokes.py tests/test_ui_ingestion_controllers.py tests/test_normativa_surface.py tests/test_citation_resolution.py -q

# Import smoke:
python -c "from lia_graph.ui_server import LiaUIHandler, main; print('ok')"

# Entry point:
uv run lia-ui --help
python -m lia_graph.ui_server --help
```

**Frontend**

```bash
# Health check (default):
cd frontend && npm test

# Full suite:
cd frontend && npm run test:all

# Ops only:
cd frontend && npx vitest run --config ./vitest.config.ts src/features/ops

# Specific test:
cd frontend && npx vitest run --config ./vitest.config.ts tests/opsFolderIngestion.test.ts
```

**Run-mode smokes**

```bash
# Local dev (artifacts + local Falkor):
npm run dev
npm run dev:check       # "Preflight passed for local mode."

# Cloud staging (Supabase + cloud Falkor):
npm run dev:staging
npm run dev:staging:check   # should show node_count ≥ 500

# Production (exits locally code 2; actual prod runs on Railway):
npm run dev:production
```

**Verify retrieval backends**

```bash
# With server running, POST to /api/chat and check response.diagnostics.retrieval_backend and .graph_backend.
# Expected values:
#   dev          → retrieval_backend="artifacts", graph_backend="artifacts"
#   dev:staging  → retrieval_backend="supabase",  graph_backend="falkor_live"
#   production   → (inherits staging on Railway)
```
