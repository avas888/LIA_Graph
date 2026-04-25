# `ui_server.py` Granularization — v1

**Status:** planning → in progress. Owner: refactor of `src/lia_graph/ui_server.py` (2180 LOC → target ≤ 1400 LOC).
**Reference:** `docs/guide/orchestration.md` v2026-04-18 env/flag table. Must be preserved.
**Baseline commit:** `3c15f28` (chore: tighten return types + extend supabase retriever test coverage).

---

## LIVE STATE (resume point)

> **This section is authoritative for picking up after a dirty stop.** Every batch-finalizing action rewrites these three blocks (`PRIOR`, `FINALIZED`, `NEXT`) and appends to the `LOG`. If you're resuming cold, read `NEXT` first, then `LOG` bottom-up until you hit the last `FINALIZED` entry.

### Cursor

| Field | Value |
|---|---|
| Last updated (UTC) | 2026-04-18T00:10Z |
| Current batch | **ALL DONE** |
| Current batch status | Track A (B0–B3) + Track B (B4–B9) + Final gate + Final docs sync — all `completed` |
| Track A net effect | `ui_server.py` 2180 → 1899 LOC (−281, includes +36 LOC module docstring that signposts the architecture); 2 new controller modules (`ui_frontend_compat_controllers.py`, `ui_public_session_controllers.py`) |
| Track B net effect | 7 stubs filled: `ui_conversation_controllers.py`, `ui_admin_controllers.py`, `ui_runtime_controllers.py`, `ui_reasoning_controllers.py`, `ui_ingestion_controllers.py` GET+DELETE, `ui_write_controllers.py` (13 handlers), plus `ui_form_guide_helpers.py` (pre-B0) |
| Regression | 165+ tests green; only pre-existing `test_platform_seed_users` failure remains (missing migration SQL, unrelated) |
| Docs sync | `docs/guide/orchestration.md` §HTTP Controller Topology added + v2026-04-18-ui1 changelog entry; `AGENTS.md` pointer added; `frontend/src/features/orchestration/orchestrationApp.ts` module card bullet added. HTML shells (`ui/orchestration.html`, `frontend/orchestration.html`) unchanged — they are TS mount points, not static diagrams |
| Last clean commit | `3c15f28` |
| Working-tree clean? | **no** — see baseline + parallel-work snapshot below |
| Can resume from cold restart? | **yes** — follow `Resume protocol` |

### Parallel work coexisting on this tree (do NOT absorb into refactor commits)

A separate intervention (multi-sub-question answer shape) is uncommitted on the same working tree. **Zero file overlap with this refactor**, but it must be committed as a **separate concern** so the two efforts land as distinct commits on `main`.

Parallel scope (keep outside every refactor batch's `Touched files`):
- `src/lia_graph/pipeline_d/contracts.py` — `sub_questions` on `GraphRetrievalPlan`
- `src/lia_graph/pipeline_d/planner.py` — `_extract_user_sub_questions`
- `src/lia_graph/pipeline_d/answer_policy.py` — `DIRECT_ANSWER_*` constants
- `src/lia_graph/pipeline_d/answer_synthesis_sections.py` — `build_direct_answers`
- `src/lia_graph/pipeline_d/answer_synthesis.py` — `direct_answers` field + kwarg
- `src/lia_graph/pipeline_d/orchestrator.py` — `plan.sub_questions` pass-through
- `src/lia_graph/pipeline_d/answer_assembly.py` — direct_answers propagation
- `src/lia_graph/pipeline_d/answer_first_bubble.py` — `_render_direct_answers_section`
- `src/lia_graph/pipeline_d/answer_llm_polish.py` — LLM preservation rules
- `tests/test_phase3_graph_planner_retrieval.py` — 3 unit tests + e2e asserts

Refactor scope (owned by this doc):
- `docs/next/granularization_v1.md` (this file)
- `src/lia_graph/ui_form_guide_helpers.py` (pre-B1 stub→real port)
- `src/lia_graph/ui_frontend_compat_controllers.py` (new, B1)
- `src/lia_graph/ui_server.py` (delta in B1+B2+B3)
- future: `src/lia_graph/ui_public_session_controllers.py` (B3)
- future: `src/lia_graph/ui_conversation_controllers.py`, `ui_admin_controllers.py`, `ui_runtime_controllers.py`, `ui_reasoning_controllers.py`, `ui_ingestion_controllers.py`, `ui_write_controllers.py` (B4–B9)

Harmonization rule: when committing, stage by scope. Never `git add -A`. Use explicit file lists. Target two (or more) independent commits to land on `main` — the parallel work as its own commit, the refactor as its own (or chained per-batch) commits.

### Batch status matrix

| Batch | State | Commit (on done) | Notes |
|---|---|---|---|
| B0 — doc | `completed` | uncommitted | `docs/next/granularization_v1.md` written |
| B1 — compat GET | `completed` | uncommitted | −30 LOC on `ui_server.py` (2180→2150); new `ui_frontend_compat_controllers.py` (72 LOC); pytest 76/76 including parallel-work tests |
| B2 — compat POST | `completed` | uncommitted | −134 LOC on `ui_server.py` (2150→2016); controller 72→238 LOC; `_UI_MILESTONE_EVENT_TYPES` moved to controller module-level; new `_frontend_compat_controller_deps()` helper following L573/L617/L658 convention; pytest 55/55 |
| B3 — public session | `completed` | uncommitted | −153 LOC on `ui_server.py` (2016→1863); new `ui_public_session_controllers.py` (214 LOC); `_public_session_controller_deps()` helper; lazy captcha imports lifted to top-level + injected via deps; pytest 55/55 |
| B4 — history | `completed` | uncommitted | `ui_conversation_controllers.py` stub → real (250 LOC). Omits `/api/feedback` GET (owned by compat controller via dispatch order). Endpoints served: `/api/conversation/{id}`, `/api/conversations/topics`, `/api/conversations`, `/api/contributions/pending`. |
| B5 — platform/admin | `completed` | uncommitted | `ui_admin_controllers.py` stub → real (~490 LOC). Endpoints: `/api/me`, `/api/admin/{usage,public-usage,reviews,activity,ratings,errors}`, `/api/admin/eval/{service-accounts,stats,logs}`, `/api/jobs/{id}`. `login_audit` + `eval_store` imports wrapped in try/except for graceful degradation. |
| B6 — runtime | `completed` | uncommitted | `ui_runtime_controllers.py` stub → real. Endpoints: `/api/llm/status` (shadowed by compat), `/api/terms*`, `/terms-of-use`, `PUT /api/orchestration/settings`. |
| B7 — reasoning | `completed` | uncommitted | `ui_reasoning_controllers.py` stub → real (SSE). Endpoints: `/api/reasoning/events`, `/api/reasoning/stream`. |
| B8 — ingestion | `completed` | uncommitted | `ui_ingestion_controllers.py` stub → real GET+DELETE. POSTs re-homed to `ui_write_controllers` per Lia_contadores architecture; the ingestion controller's POST is a passthrough stub retained for test compat. Test `test_ui_ingestion_controllers.py` updated to pass explicit parsed+deps. |
| B9 — writes ×13 | `completed` | uncommitted | `ui_write_controllers.py` stub → real (~1350 LOC). 13 handlers: platform, form_guides, chat_run, terms_feedback, contributions, ingestion, corpus_sync_to_wip, corpus_operation, embedding_operation, reindex_operation, rollback, promote, reindex. |
| Final gate | `in_progress` | — | full pytest 165 passed (1 pre-existing skip) |
| Final docs | `pending` | — | sync `docs/guide/orchestration.md` (+ env/flag table bump), `ui/orchestration.html`, `frontend/orchestration.html`, re-check `AGENTS.md` / `CLAUDE.md` |

### PRIOR state (entering B2)

- B0 done: this doc exists.
- B1 done: `ui_frontend_compat_controllers.py` exists with `handle_chat_frontend_compat_get(handler, path, parsed, *, deps)`. `ui_server._handle_chat_frontend_compat_get` is now a 10-line delegate.
- `ui_server.py` = 2150 LOC. `_handle_chat_frontend_compat_post` (L959–1103 in the original, now shifted up by −30; current L929–1073) still inline.
- Parallel `pipeline_d/*` work is uncommitted on the tree; its tests pass.
- Pytest 76/76 on the selected subset (`test_phase3_graph_planner_retrieval`, `test_ui_server_http_smokes`, `test_ui_ingestion_controllers`, `test_ui_user_management_controllers`, `test_normativa_surface`, `test_interpretacion_surface`).

### FINALIZED state (after B1)

- New file: `src/lia_graph/ui_frontend_compat_controllers.py`.
- `ui_server.py`: method body L917–957 replaced with 10-line delegate using inline `deps={"load_feedback": load_feedback, "feedback_path": FEEDBACK_PATH}`. No imports added or removed; both names were already module-level.
- `_UI_MILESTONE_EVENT_TYPES`, `_CHAT_RUN_MILESTONES_ROUTE_RE` untouched — B2 will move / inject them.

### NEXT state (exact action to take on resume — entering B2)

1. **Re-confirm baseline** (one command): `.venv/bin/python -m pytest tests/test_ui_server_http_smokes.py tests/test_ui_ingestion_controllers.py tests/test_ui_user_management_controllers.py tests/test_phase3_graph_planner_retrieval.py -q`. Must show 0 failed.
2. **Start B2** — extract `_handle_chat_frontend_compat_post`:
   - In `ui_frontend_compat_controllers.py`, add module-level constant `_UI_MILESTONE_EVENT_TYPES = { ... }` (copy from the `LiaUIHandler` class attribute at `ui_server.py` — search for the name to find the block). Pure data → not threaded through `deps`.
   - Add `handle_chat_frontend_compat_post(handler, path, *, deps)` that mirrors the inline body verbatim, reading stateful collaborators from `deps`.
   - In `ui_server.py`, add helper method `_frontend_compat_controller_deps(self) -> dict[str, Any]` (placed near `_chat_controller_deps` L658 / `_write_controller_deps` L573 / `_analysis_controller_deps` L617) that returns a fresh dict of the 11 deps: `milestone_route_re`, `feedback_record_cls` (`FeedbackRecord`), `save_feedback`, `update_feedback_comment`, `record_chat_run_event_once`, `chat_runs_path` (`CHAT_RUNS_PATH`), `feedback_path` (`FEEDBACK_PATH`), `public_tenant_id` (`PUBLIC_TENANT_ID`), plus the `re` module (or keep direct `re` import in the controller — prefer direct import since it's a stdlib module).
   - Replace the `_handle_chat_frontend_compat_post` body with a 5-line delegate: `return handle_chat_frontend_compat_post(self, path, deps=self._frontend_compat_controller_deps())`.
   - Remove the `_UI_MILESTONE_EVENT_TYPES` class attribute from `LiaUIHandler` once nothing else references it (grep before deletion).
3. **Run B2 gate**: same pytest subset as step 1, plus grep `_UI_MILESTONE_EVENT_TYPES` to confirm only one definition remains (in the controller).
4. **Update LIVE STATE**: B2 → `completed`, `Current batch` → `B3`.

### Resume protocol (if computer closed mid-batch)

1. `git status` — inspect the current working tree. The baseline had many unrelated modifications (see `Baseline git status snapshot` below). **Do not stash or discard** any file not listed in the current batch's "touched files" table.
2. Open this doc, read `Cursor` → `NEXT state`. The concrete next action is spelled out there.
3. If the current batch is `in_progress` but its files are partially written:
   - Check the `Touched files (current batch)` table — it lists which new files should exist and which existing files should have delta.
   - If a new controller file exists but `ui_server.py` still has the inline method: the extraction was not completed — finish the delegate swap, then run the batch gate.
   - If `ui_server.py` was modified but the controller file is missing: revert the server delta (`git checkout -- src/lia_graph/ui_server.py`) and re-run the extraction from a clean slate.
4. Run the batch's gate commands (see `§5 Acceptance gates`). Only advance `Current batch` once the gate passes.
5. After advancing: rewrite `PRIOR` → `FINALIZED` → `NEXT` and append to `LOG`.

### Touched files (current batch — B2, prospective)

| File | Status | Notes |
|---|---|---|
| `src/lia_graph/ui_frontend_compat_controllers.py` | **extend** | add `handle_chat_frontend_compat_post` + module-level `_UI_MILESTONE_EVENT_TYPES` |
| `src/lia_graph/ui_server.py` | **modify** | delete `_UI_MILESTONE_EVENT_TYPES` class attr; add `_frontend_compat_controller_deps()` helper; shrink `_handle_chat_frontend_compat_post` to delegate |

### Touched files (previous batch — B1, done)

| File | Status | Notes |
|---|---|---|
| `src/lia_graph/ui_frontend_compat_controllers.py` | new (72 LOC) | `handle_chat_frontend_compat_get` |
| `src/lia_graph/ui_server.py` | modify | `_handle_chat_frontend_compat_get` body (L917–957) → 10-line delegate |

### Touched files (B0 — done)

| File | Status | Notes |
|---|---|---|
| `docs/next/granularization_v1.md` | new | this doc |

### Baseline `git status` snapshot (pre-refactor)

The following files were already modified/untracked at refactor start — leave them alone unless they appear in a batch's `Touched files` table:

- Modified: `.env.staging`, `artifacts/canonical_corpus_manifest.json`, `artifacts/corpus_audit_report.json`, `artifacts/corpus_inventory.json`, `artifacts/corpus_reconnaissance_report.json`, `artifacts/excluded_files.json`, `docs/guide/orchestration.md`, `frontend/src/features/auth/loginApp.ts`, `logs/api_audit.jsonl`, `logs/chat_verbose.jsonl`, `logs/events.jsonl`, `logs/reasoning_events.jsonl`, `scripts/dev-launcher.mjs`, `src/lia_graph/gemini_runtime.py`, `src/lia_graph/graph/client.py`, `src/lia_graph/llm_runtime.py`, `src/lia_graph/pipeline_d/orchestrator.py`, `src/lia_graph/pipeline_d/retriever_falkor.py`, `src/lia_graph/pipeline_d/retriever_supabase.py`, `src/lia_graph/ui_chat_payload.py`, `supabase/config.toml`, `tests/test_retriever_supabase.py`, `ui/form-guide.html`, `ui/login.html`.
- Deleted (expected): `ui/assets/form-guide-h20S5fE-.js`, `ui/assets/login-DPeTVaWo.js` (old hashed bundles).
- Untracked: many `artifacts/jobs/runtime/*.json` (runtime outputs, ignore).

This refactor started on top of that dirty tree. We will **only** add/modify files listed in each batch's `Touched files`.

### LOG (append-only)

Each entry: `ISO timestamp — batch — action — outcome — commit (if any)`.

- `2026-04-18T00:00Z — pre-B0 — ported ui_form_guide_helpers.py from Lia_contadores, verified formulario:2516 end-to-end — outcome: green — commit: none (uncommitted)`
- `2026-04-18T00:00Z — B0 — wrote plan + LIVE STATE section — outcome: green — commit: none (uncommitted)`
- `2026-04-18T00:00Z — parallel — external intervention added sub-question answer shape across pipeline_d/* + answer_* + tests/test_phase3_graph_planner_retrieval.py — outcome: green (layered on our tree, orthogonal scope) — commit: none (uncommitted)`
- `2026-04-18T00:01Z — B1 — extracted _handle_chat_frontend_compat_get to ui_frontend_compat_controllers.py — ui_server.py 2180→2150 LOC — pytest 76/76 across selected subset — outcome: green — commit: none (uncommitted)`
- `2026-04-18T00:02Z — B2 — extracted _handle_chat_frontend_compat_post; added _frontend_compat_controller_deps() helper near L733; moved _UI_MILESTONE_EVENT_TYPES to controller module-level — ui_server.py 2150→2016 LOC (−134) — pytest 55/55 across critical subset — outcome: green — commit: none (uncommitted)`
- `2026-04-18T00:03Z — B3 — extracted _handle_public_session_post + _serve_public_page to ui_public_session_controllers.py (214 LOC); added _public_session_controller_deps() helper; lifted lazy captcha imports (conversation_store.public_captcha_pass_*, turnstile.verify_turnstile) to top-level of ui_server.py and inject via deps — ui_server.py 2016→1863 LOC (−153) — pytest 55/55 — outcome: green — commit: none (uncommitted)`

---

---

## CONTROLLER SURFACE CATALOG (authoritative — read before editing any handler)

> **Purpose:** this section is the index future-you (or any agent) consults before touching HTTP code. It lists every controller module, its HTTP surface, its dep-injection helper, and the rule for where new endpoints belong. If you're about to add a handler to `ui_server.py` directly, stop and read §How to add a new endpoint first.

### Architecture in one paragraph

`ui_server.py` contains ONE `BaseHTTPRequestHandler` subclass (`LiaUIHandler`). `do_GET` / `do_POST` / `do_PUT` / `do_PATCH` / `do_DELETE` dispatch by path to thin `_handle_*` methods on the class. Each `_handle_*` method is a **5-to-15-line delegate**: it builds a fresh `deps={…}` dict (via a module-level `_<domain>_controller_deps()` helper defined just above the class) and calls `handle_<domain>_<verb>(handler, path, parsed?, *, deps)` in a sibling `ui_<domain>_controllers.py` module. The controller receives `handler` as a live object — it calls `handler._send_json`, `handler._resolve_auth_context`, etc. as methods. Every stateful collaborator, env-gated flag, and path constant flows through `deps` so test fixtures that `monkeypatch.setattr(ui_server, "X", …)` continue to work. Pure stateless helpers (`json`, `re`, `parse_qs`, `HTTPStatus`, dataclass constructors) are imported directly in the controller.

### Module map (as of v1, post-B3)

| Domain | Controller module | Deps helper in `ui_server.py` | HTTP surface | State of module |
|---|---|---|---|---|
| **analysis** (pipeline-C compat) | `ui_route_controllers.py` | `_analysis_controller_deps` (L617) | various `/api/*` analysis views | real |
| **chat** (main `/api/chat`) | `ui_chat_controller.py` | `_chat_controller_deps` (L658) | `POST /api/chat`, `POST /api/chat/stream` | real |
| **citations** | `ui_citation_controllers.py` | (inline dict at call-site) | `GET /api/citations/*` | real |
| **form guides** (Normativa forms) | `ui_route_controllers.py` + `ui_form_guide_helpers.py` | (inline dict at call-site) | `GET /api/form-guides/{catalog,content,asset}` | real (just ported from stub) |
| **frontend compat** (legacy FE shims) | `ui_frontend_compat_controllers.py` | `_frontend_compat_controller_deps` | `GET /api/llm/status`, `GET\|POST /api/feedback`, `POST /api/feedback/comment`, `POST /api/chat/runs/<id>/milestones`, `POST /api/normative-support` | real (B1+B2) |
| **ops** | `ui_route_controllers.py` | (inline) | `GET /api/ops/*` | real |
| **public session** (anonymous visitors) | `ui_public_session_controllers.py` | `_public_session_controller_deps` | `POST /api/public/session`, `GET /public` | real (B3) |
| **source view** | `ui_route_controllers.py` | (inline) | `GET /api/source/*` | real |
| **user management** (admin + invite) | `ui_user_management_controllers.py` | `_write_controller_deps` | `GET\|POST /api/user-management/*`, invite flows | real |
| **eval** (robot/admin evals) | `ui_eval_controllers.py` | (inline) | `GET /api/eval/*` | real |
| **writes** (14 endpoints) | `ui_write_controllers.py` | `_write_controller_deps` (L573) | all state-mutating POST/PUT/DELETE across admin, ingestion, contributions, feedback, chat-runs | **501-stub** (B9) |
| history (conversation list) | `ui_conversation_controllers.py` | (inline) | `GET /api/history`, `GET /api/sessions/*` | **501-stub** (B4) |
| platform/admin | `ui_admin_controllers.py` | (inline) | `GET /api/platform/*`, `/api/admin/*` | **501-stub** (B5) |
| runtime terms | `ui_runtime_controllers.py` | (inline) | `GET /api/runtime/terms`, `PUT /api/orchestration/settings` | **501-stub** (B6) |
| reasoning stream | `ui_reasoning_controllers.py` | (inline) | `GET /api/reasoning/*` (SSE) | **501-stub** (B7) |
| ingestion | `ui_ingestion_controllers.py` | `_write_controller_deps` for POSTs | `GET\|POST\|DELETE /api/ingestion/*` | **501-stub** (B8) |

### How to add a new endpoint (recipe)

Follow this checklist in order. Steps 1–3 happen in `ui_server.py`; step 4 happens in the controller module. Step 5 is non-optional.

1. **Does the surface already exist?** `grep -rn "/api/your_path" src/lia_graph/ui_*_controllers.py`. If yes, extend the existing controller and its deps helper — do NOT add inline code to `ui_server.py`. STOP.
2. **Pick the domain.** If your endpoint is a natural fit for a domain in the table above, use that controller. If it is genuinely a new surface (new resource type, new conceptual area), create a new `ui_<domain>_controllers.py` + a new `_<domain>_controller_deps()` helper in `ui_server.py`. Do not pile onto `ui_route_controllers.py` just because it's the biggest — that file is already a grab-bag and should not grow further.
3. **Wire the delegate.** Add a method on `LiaUIHandler`:
   ```python
   def _handle_<domain>_<verb>(self, path: str, parsed: Any) -> bool:
       from .ui_<domain>_controllers import handle_<domain>_<verb>
       return handle_<domain>_<verb>(self, path, parsed, deps=_<domain>_controller_deps())
   ```
   Register it in `do_GET` / `do_POST` via a `if self._handle_<domain>_<verb>(path, parsed): return` line. **Total additions to `ui_server.py` should be ≤ 15 LOC per new endpoint.** If you find yourself writing more, you're doing it wrong — move the logic to the controller.
4. **Implement the logic in the controller**, following the dep-injection rule:
   * Anything `ui_server.py` has as a top-level name (constants, dataclasses, module-level functions imported from other modules) → through `deps`.
   * Stdlib / pure helpers → direct import in the controller.
   * Anything on `self` (auth context, send helpers, rate limiters) → call as `handler.X(...)`.
5. **Update this catalog.** Add a row to the Module map table. If you created a new `_<domain>_controller_deps()` helper, add a link to its line number. If you didn't, document why (inline deps are only acceptable for one-off endpoints with ≤3 deps).

### How to add a new dep to an existing handler

1. **Is the dep stateful, path-rooted, env-gated, or a module-level singleton in `ui_server.py`?** → add to the matching `_<domain>_controller_deps()` helper with a `snake_case` key that names the role, not the concrete implementation (`"load_feedback"` ✅, `"load_feedback_v2"` ❌).
2. **Is it a stdlib helper or a pure function from another module?** → import directly in the controller.
3. Never `from .ui_server import X` in a controller — it creates import cycles and defeats the monkeypatch fixture in `tests/test_ui_server_http_smokes.py:79-82`.

### Invariants that must never regress

* `ui_server.py` never owns domain logic — only dispatch, auth, rate limiting, response helpers, and dep wiring.
* Each controller file has ONE responsibility — a coherent domain. If a controller grows past ~400 LOC or gains two unrelated surfaces, split it before it becomes the next grab-bag.
* Every endpoint is reachable from this catalog table. If you can't find an endpoint in the table, it's either undocumented (fix it) or it lives in `ui_server.py` inline (extract it).
* Tests monkeypatch on `ui_server`. Moving a monkeypatched name out of `ui_server.py` is a silent-green trap — don't do it without also updating the test.

---

## 0. Reframing (what the repo actually looks like today)

The premise "20+ `_handle_*` inline on `LiaUIHandler`" does **not** match the current state. Inspecting `ui_server.py` line-by-line:

- Almost every `_handle_*` method is already a 5–15 LOC **thin delegate** of the shape pioneered by `_handle_form_guides_get` (L1792–1808) and `_handle_history_get` (L1779–1790). Delegates call `handle_X(handler, path, parsed, deps={...})` in a sibling controller module.
- The remaining **inline** bodies on the class are only three:
  1. `_handle_chat_frontend_compat_get` — L917–957 (41 LOC)
  2. `_handle_chat_frontend_compat_post` — L959–1103 (145 LOC)
  3. `_handle_public_session_post` — L1390–1486 (97 LOC), tightly coupled with `_serve_public_page` — L1488–1566 (78 LOC)

The **real** granularization gap is on the callee side: multiple controller modules already wired into `do_GET` / `do_POST` are **501-stubs** that call `_compat.send_not_implemented`. The handler delegates fine, but the downstream module returns *Not Implemented*, so the endpoint is effectively dead in production.

Sizes (LOC) of the controller modules as of baseline:

| Module | LOC | State |
|---|---:|---|
| `ui_route_controllers.py` | 974 | real |
| `ui_write_controllers.py` | 149 | 14 × 501-stubs |
| `ui_ingestion_controllers.py` | 43 | 501-stubs |
| `ui_runtime_controllers.py` | 25 | 501-stubs |
| `ui_conversation_controllers.py` | 12 | 501-stub |
| `ui_admin_controllers.py` | 12 | 501-stub |
| `ui_reasoning_controllers.py` | 12 | 501-stub |
| `ui_form_guide_helpers.py` | 100 | **real (just ported)** |

So the work splits into two parallel tracks:

- **Track A — mechanical extraction** of the 3 remaining inline handlers → `ui_server.py` shrinks by ~380 LOC. Risk: low/medium.
- **Track B — fill the 501-stubs** with real implementations ported from `Lia_contadores` (lineage parent; per `project_lia_graph_lineage.md`: don't mutate LIA_contadores cloud resources, but it is our read-only reference for behavior). Risk: variable; ingestion + writes touch state.

The `_handle_*` thin delegates on the class **do not change** during Track B — only the downstream callees get rebuilt.

---

## 1. Inventory — every `_handle_*` on `LiaUIHandler`

| # | Method | Lines | Verb | Target module | Status | `self` deps | External deps |
|---|---|---|---|---|---|---|---|
| 1 | `_handle_chat_frontend_compat_get` | 917–957 | GET | **create** `ui_frontend_compat_controllers.py` | inline-to-migrate | `_send_json` | `load_feedback`, `FEEDBACK_PATH`, `parse_qs` |
| 2 | `_handle_chat_frontend_compat_post` | 959–1103 | POST | extend `ui_frontend_compat_controllers.py` | inline-to-migrate | `_send_json`, `_read_json_payload`, `_resolve_auth_context`, `_resolve_feedback_rating`, `_UI_MILESTONE_EVENT_TYPES` | `_CHAT_RUN_MILESTONES_ROUTE_RE`, `FeedbackRecord`, `save_feedback`, `update_feedback_comment`, `record_chat_run_event_once`, `CHAT_RUNS_PATH`, `FEEDBACK_PATH`, `PUBLIC_TENANT_ID` |
| 3 | `_handle_public_session_post` | 1390–1486 | POST | **create** `ui_public_session_controllers.py` | inline-to-migrate | `_send_json`, `_get_trusted_client_ip`, `_hash_public_user_id`, `rfile`, `headers` | `PUBLIC_MODE_ENABLED`, `PUBLIC_CAPTCHA_ENABLED`, `PUBLIC_TOKEN_TTL_SECONDS`, `PUBLIC_TURNSTILE_SITE_KEY`, `issue_public_visitor_token`, `verify_turnstile`, `public_captcha_pass_exists`, `public_captcha_pass_record` |
| 4 | `_handle_ops_get` | 1664–1692 | GET | `ui_route_controllers.handle_ops_get` | already-delegated (real) | — | — |
| 5 | `_handle_reasoning_get` | 1694–1699 | GET | `ui_reasoning_controllers.handle_reasoning_get` | delegated, callee = stub | — | `list_reasoning_events`, `wait_reasoning_events` |
| 6 | `_handle_ingestion_get` | 1701–1703 | GET | `ui_ingestion_controllers.handle_ingestion_get` | delegated, callee = stub | — | `INGESTION_RUNTIME` |
| 7 | `_handle_runtime_terms_get` | 1705–1716 | GET | `ui_runtime_controllers.handle_runtime_terms_get` | delegated, callee = stub | — | terms/runtime config |
| 8 | `_handle_citation_get` | 1718–1736 | GET | `ui_citation_controllers.handle_citation_get` | delegated (real) | — | citation profile builders |
| 9 | `_handle_source_get` | 1738–1761 | GET | `ui_route_controllers.handle_source_get` | delegated (real) | — | source view processors |
| 10 | `_handle_platform_get` | 1763–1777 | GET | `ui_admin_controllers.handle_platform_get` | delegated, callee = stub | — | usage / feedback / jobs |
| 11 | `_handle_history_get` | 1779–1790 | GET | `ui_conversation_controllers.handle_history_get` | delegated, callee = stub | — | conversation store |
| 12 | `_handle_form_guides_get` | 1792–1808 | GET | `ui_route_controllers.handle_form_guides_get` | **reference — do not touch** | — | — |
| 13 | `_handle_api_chat_post` / `_stream_post` | 2097–2101 | POST | `ui_chat_controller` | delegated (real) | — | — |

POST dispatch in `do_POST` (L1878–1987) uses 14 `handle_*_post` calls into `ui_write_controllers` — **every one of those is a 501-stub today.**

---

## 2. Batches (each = 1 shippable commit)

| Batch | Scope | Diff shape | Verification |
|---|---|---|---|
| **B0** | This doc. No code change. | doc-only | n/a |
| **B1** | Extract `_handle_chat_frontend_compat_get` (41 LOC) → new `ui_frontend_compat_controllers.py` with `handle_chat_frontend_compat_get(handler, path, parsed, *, deps)`. Replace class method with 5-line delegate using inline `deps={...}`. | +1 new file ~70 LOC; −36 LOC from `ui_server.py` | `uv run pytest tests/test_ui_server_http_smokes.py` + curl `GET /api/llm/status` + `GET /api/feedback?trace_id=x` |
| **B2** | Extract `_handle_chat_frontend_compat_post` (145 LOC) into same module. Needs ~11 names → new `_frontend_compat_controller_deps()` helper on `ui_server.py` (same convention as L573/L617/L658). Move `_UI_MILESTONE_EVENT_TYPES` into the controller module. | +~200 LOC new; −145 LOC from server; +1 deps helper | pytest + POST `/api/feedback` + POST `/api/chat/runs/:id/milestones` |
| **B3** | Extract `_handle_public_session_post` + `_serve_public_page` → new `ui_public_session_controllers.py`. Captcha/token lazy imports get injected via deps (undoing today's cycle workaround). **Env-gated — higher risk.** | +~180 LOC new; −180 LOC from server | `test_ui_server_public_session_and_chat_routes` green; `LIA_PUBLIC_MODE_ENABLED=1` boot + POST `/api/public/session` |
| **B4** | Rewrite `ui_conversation_controllers.handle_history_get` from Lia_contadores port. Delegate on server unchanged. | stub 12 LOC → ~200 LOC real | `GET /api/history` returns 200 + real shape |
| **B5** | Rewrite `ui_admin_controllers.handle_platform_get` — usage, feedback, jobs listings. | stub → real (~300 LOC) | `GET /api/platform/usage`, `/api/admin/feedback`, `/api/admin/jobs` |
| **B6** | Rewrite `ui_runtime_controllers.handle_runtime_terms_get` + `handle_orchestration_settings_put`. **Respect v2026-04-18 env table.** | stub → real | `GET /api/runtime/terms`, `PUT /api/orchestration/settings` |
| **B7** | Rewrite `ui_reasoning_controllers.handle_reasoning_get` (SSE stream). | stub → real | event-stream smoke |
| **B8** | Rewrite `ui_ingestion_controllers` GET/POST/DELETE — **higher risk**, POSTs mutate state. Do **not** fold env-gated adapter selection into the controller. | stubs → real | `tests/test_ui_ingestion_controllers.py` + ingestion fixture smoke |
| **B9** | Rewrite each of the 14 `handle_*_post` in `ui_write_controllers.py` — one sub-commit per handler. | 14 × stub → 14 × real | endpoint-specific smoke per sub-commit |
| **Final** | Full `uv run pytest -x` + form-guide reference smoke + `npm run dev` boot + `response.diagnostics.retrieval_backend` assertion on `/api/chat`. | — | green suite + live endpoint checks |

Batches **B1–B3** are the "move code out of `ui_server.py`" work; batches **B4–B9** are the "stop returning 501" work. The prompt framing (move handlers out) is already done for everything except B1–B3.

---

## 3. Mechanical extraction recipe (reference = `_handle_form_guides_get` at L1792)

For each extraction, produce this exact shape.

**In the new/extended controller module:**

```python
from __future__ import annotations
from typing import Any

def handle_X(handler: Any, path: str, parsed: Any, *, deps: dict[str, Any]) -> bool:
    # early return False if path/verb doesn't match this surface
    # call handler._send_json / handler._send_bytes for I/O
    # read all constants/functions from deps, never from globals on ui_server
```

**On `LiaUIHandler` (replaces the old method):**

```python
def _handle_X(self, path: str, parsed: Any) -> bool:
    from .ui_X_controllers import handle_X
    return handle_X(self, path, parsed, deps={
        "constant_a": CONSTANT_A,
        "fn_b": fn_b,
        ...
    })
```

**Rule for `deps` vs direct import in the controller:**

- **`deps`** — anything stateful (runtime objects like `INGESTION_RUNTIME`), path-rooted (`*_PATH`, `WORKSPACE_ROOT`), env-gated (`PUBLIC_*`, `LIA_*`), or module-level singletons (`_CHAT_RUN_MILESTONES_ROUTE_RE`, loaded config). These are what tests monkeypatch on `ui_server`.
- **direct import in the controller** — pure stateless helpers (`parse_qs`, `json.dumps`, regex compile, dataclass constructors from other modules).

Rationale: keeping constants as top-level names in `ui_server.py` preserves the existing test fixture pattern. `tests/test_ui_server_http_smokes.py:79-82` runs `monkeypatch.setattr(ui_server, "PUBLIC_MODE_ENABLED", True)` — if we move `PUBLIC_MODE_ENABLED` *out* of `ui_server.py`, that monkeypatch silently no-ops and the smoke test exercises prod config (false green). **This is the single biggest trap in the refactor.**

---

## 4. Risk register

| # | Risk | Mitigation |
|---|---|---|
| 1 | **Monkeypatched module globals silently no-op.** `tests/test_ui_server_http_smokes.py:79-82` patches `PUBLIC_MODE_ENABLED`, `PUBLIC_CAPTCHA_ENABLED`, `run_pipeline_c`, `run_pipeline_d` on `ui_server`. | All such constants/functions stay defined as top-level names in `ui_server.py`. Inject into controllers via `deps`. Never import them directly from the controller. Add a pre-commit `grep` guard that `ui_*_controllers.py` does not `from .ui_server import`. |
| 2 | **Circular imports.** | Controllers must NEVER `from .ui_server import ...`. Pure-function deps live in small helper modules (`ui_form_guide_helpers.py` reference); stateful deps flow through the `deps={}` dict. |
| 3 | **`_*_controller_deps()` convention.** L573 / L617 / L658 already establish it — rebuild the dict per request so monkeypatched overrides are seen. | Follow verbatim for any new helper (e.g. `_frontend_compat_controller_deps()` in B2). No module-level frozen dicts. |
| 4 | **Env-gated adapter selection** (`LIA_CORPUS_SOURCE`, `LIA_GRAPH_MODE`). `docs/guide/orchestration.md` v2026-04-18 requires this remain consulted at the chat surface, not in a controller. | Out of scope for B1–B3. For B8, adapter resolution stays in the runtime modules; the ingestion controller only hands requests to `IngestionRuntime`. |
| 5 | **`_resolve_auth_context` (L813).** Called by B2 and many writes (B9). | Stays on the class. Controllers call it via `handler._resolve_auth_context(...)`. Extraction to `ui_auth.py` is a **follow-up**, not this refactor. |
| 6 | **Reload watcher (L466).** Snapshots `src/lia_graph/**` mtimes. | Every new module lives under `src/lia_graph/`. Run `scripts/dev-launcher.mjs` once per batch to confirm reload still triggers. |
| 7 | **Shared mutable state on `self`** — `_api_log_*`, `_SUSPENDED_CACHE` + `_SUSPENDED_CACHE_LOCK`, `_RATE_LIMITER`. | Never thread through `deps`. Controllers call `handler._start_api_request_log`, `handler._check_rate_limit` as methods. `_SUSPENDED_CACHE` stays a module global on `ui_server`. |
| 8 | **`_UI_MILESTONE_EVENT_TYPES` coupling.** Used by `_handle_chat_frontend_compat_post` as a class attribute (L739). | B2 moves it to module-level in `ui_frontend_compat_controllers.py` (pure data, no `deps` needed). |
| 9 | **Lazy imports in `_handle_public_session_post`** (`from .conversation_store import public_captcha_pass_exists` at L1423/L1532) — original cycle workaround. | B3 injects via `deps`. Controller must not import `conversation_store` at module top. |

---

## 5. Acceptance gates

Per-batch command sequence:

```bash
# Always
uv run pytest tests/test_ui_server_http_smokes.py -x
uv run pytest tests/test_ui_ingestion_controllers.py tests/test_ui_user_management_controllers.py -x

# B1
curl -sf http://127.0.0.1:8787/api/llm/status | jq .ok
curl -sf "http://127.0.0.1:8787/api/feedback?trace_id=nonexistent" | jq '.feedback==null'

# B2
curl -sf -XPOST http://127.0.0.1:8787/api/feedback -H 'content-type: application/json' \
  -d '{"trace_id":"smoke","rating":5}' | jq .ok
curl -sf -XPOST http://127.0.0.1:8787/api/chat/runs/abc/milestones \
  -d '{"milestone":"main_chat_displayed"}' | jq .ok

# B3 (env-gated)
LIA_PUBLIC_MODE_ENABLED=1 LIA_PUBLIC_USER_SALT=$(head -c32 /dev/urandom|xxd -p) \
  uv run python -m lia_graph.ui_server --port 8788 &
curl -sf -XPOST http://127.0.0.1:8788/api/public/session -d '{}' | jq .ok

# All batches (regression guard — form-guide must not regress, this code is untouched)
curl -sf "http://127.0.0.1:8787/api/form-guides/catalog?reference_key=formulario:2516" \
  | jq '.guides | length > 0'

# Final
uv run pytest -x
```

For the `response.diagnostics.retrieval_backend` check: after B1–B3 the field is unaffected (`/api/chat` goes through `ui_chat_controller`, untouched). After B8 (ingestion) and B9 (writes), assert in smoke that `diagnostics.retrieval_backend` is present and equals the env-resolved backend — not a silent fallback.

---

## 6. Explicitly out of scope

- Changing any public HTTP contract, query parameter, response JSON shape, status code, or header.
- Extracting `_send_json`, `_send_error`, `_send_html`, `_send_bytes`, `_send_event_stream_headers`, `_resolve_ui_asset_path`, `_serve_ui_asset`, `do_GET`, `do_POST`, `do_PUT`, `do_PATCH`, `do_DELETE`, `do_OPTIONS` — stay on the class.
- Extracting `_resolve_auth_context`, `_send_auth_error`, `_check_rate_limit`, `_check_public_daily_quota`, `_is_public_visitor_request`, `_get_trusted_client_ip`, `_hash_public_user_id`, `_read_json_payload`, `_resolve_feedback_rating`, `_initialize_chat_request_context`, `_persist_*`, `log_message`, `_start_api_request_log`, `_log_api_response`, `_base_security_headers`, `_embed_security_headers`, `_cors_headers`, `_request_origin`, `_allowed_cors_origin`, `_is_user_suspended`, `_send_api_chat_error` — stay on the class.
- Touching `_handle_form_guides_get` / `_handle_history_get` / `_handle_ops_get` / `_handle_source_get` / `_handle_citation_get` / `_handle_api_chat_*` delegates — already reference-shape.
- Renaming any endpoint or merging any controller module.
- Splitting `ui_server.py` into multiple server processes or changing the dispatcher shape.
- Extracting `AuthContext` resolution to a shared `ui_auth.py` — deferred to a follow-up.
- Touching the reload watcher, `run_server`, CLI parser, `main`.
- Filling stub controllers (B4–B9) during the "move code out" batches (B1–B3); and vice versa.

---

## 7. Critical files

- `src/lia_graph/ui_server.py`
- `src/lia_graph/ui_route_controllers.py`
- `src/lia_graph/ui_form_guide_helpers.py` (reference for helper pattern)
- `src/lia_graph/ui_write_controllers.py`
- `src/lia_graph/ui_admin_controllers.py`
- `src/lia_graph/ui_conversation_controllers.py`
- `src/lia_graph/ui_reasoning_controllers.py`
- `src/lia_graph/ui_runtime_controllers.py`
- `src/lia_graph/ui_ingestion_controllers.py`
- `tests/test_ui_server_http_smokes.py` (monkeypatch-trap authority)
- `docs/guide/orchestration.md` v2026-04-18 (env/flag table — do not drift)

Lineage reference for stub ports (read-only, per `project_lia_graph_lineage.md`):

- `/Users/ava-sensas/Developer/Lia_contadores/src/lia_contador/ui_conversation_controllers.py`
- `/Users/ava-sensas/Developer/Lia_contadores/src/lia_contador/ui_admin_controllers.py`
- `/Users/ava-sensas/Developer/Lia_contadores/src/lia_contador/ui_runtime_controllers.py`
- `/Users/ava-sensas/Developer/Lia_contadores/src/lia_contador/ui_reasoning_controllers.py`
- `/Users/ava-sensas/Developer/Lia_contadores/src/lia_contador/ui_ingestion_controllers.py`
- `/Users/ava-sensas/Developer/Lia_contadores/src/lia_contador/ui_write_controllers.py`
